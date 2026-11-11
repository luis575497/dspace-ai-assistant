"""Read-only DSpace REST connector for repository analytics."""

import requests
from datetime import datetime, timezone
from flask import current_app


class DSpaceError(RuntimeError):
    pass


class DSpaceClient:
    MONTH_LABELS = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")

    def __init__(self):
        self.base_url = (current_app.config.get("DSPACE_REST_URL") or "").rstrip("/")
        if not self.base_url:
            raise DSpaceError("DSpace REST todavía no está configurado.")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/hal+json, application/json"})
        self._authenticate_if_configured()

    def _authenticate_if_configured(self):
        user = current_app.config.get("DSPACE_EMAIL")
        password = current_app.config.get("DSPACE_PASSWORD")
        if not user and not password:
            return
        if not user or not password:
            raise DSpaceError("Configura ambos valores DSPACE_EMAIL y DSPACE_PASSWORD.")
        try:
            csrf_response = self.session.get(f"{self.base_url}/security/csrf", timeout=15)
            csrf_response.raise_for_status()
            token = csrf_response.headers.get("DSPACE-XSRF-TOKEN") or csrf_response.headers.get("X-XSRF-TOKEN")
            if not token:
                raise DSpaceError("DSpace no devolvió el token CSRF necesario para iniciar sesión.")
            login = self.session.post(
                f"{self.base_url}/authn/login",
                data={"user": user, "password": password},
                headers={"X-XSRF-TOKEN": token},
                timeout=20,
            )
            login.raise_for_status()
            authorization = login.headers.get("Authorization")
            if not authorization:
                raise DSpaceError("DSpace no devolvió el token de sesión esperado.")
            self.session.headers["Authorization"] = authorization
        except requests.RequestException as exc:
            raise DSpaceError("No se pudo iniciar sesión en DSpace. Revisa la URL y la cuenta de lectura.") from exc

    def get(self, path, params=None):
        try:
            response = self.session.get(f"{self.base_url}/{path.lstrip('/')}", params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise DSpaceError("DSpace REST no respondió a una consulta de lectura.") from exc
        except ValueError as exc:
            raise DSpaceError("DSpace REST devolvió una respuesta que no es JSON válido.") from exc

    def count(self, path):
        payload = self.get(path, params={"size": 1, "page": 0})
        return payload.get("page", {}).get("totalElements")

    def collection_item_counts(self):
        payload = self.get("core/collections", params={"size": 100, "page": 0})
        collections = payload.get("_embedded", {}).get("collections", [])
        result = []
        for collection in collections:
            uuid = collection.get("uuid") or collection.get("id")
            if not uuid:
                continue
            metadata = collection.get("metadata", {})
            titles = metadata.get("dc.title", [])
            name = collection.get("name") or (titles[0].get("value") if titles else None) or "Colección sin título"
            try:
                items = self.count(f"core/collections/{uuid}/items")
            except DSpaceError:
                items = None
            result.append({"id": uuid, "name": name, "items": items})
        return sorted(result, key=lambda row: row["items"] or 0, reverse=True)

    def publication_activity(self, months=12):
        """Count archived items by their DSpace accession month, newest first."""
        now = datetime.now(timezone.utc)
        start_month = now.month - months + 1
        start_year = now.year
        while start_month <= 0:
            start_month += 12
            start_year -= 1
        start = datetime(start_year, start_month, 1, tzinfo=timezone.utc)
        buckets = {}
        for offset in range(months):
            month_index = start_month - 1 + offset
            year = start_year + month_index // 12
            month = month_index % 12 + 1
            buckets[(year, month)] = 0

        page = 0
        max_pages = 100
        while page < max_pages:
            payload = self.get("discover/search/objects", params={
                "dsoType": "item", "sort": "dateaccessioned,desc", "page": page, "size": 100,
            })
            result = payload.get("_embedded", {}).get("searchResult", {})
            search_result = self._first_embedded(payload, "searchResults", "searchResult") or result
            items = search_result.get("_embedded", {}).get("objects", [])
            if not items:
                break
            stop = False
            for hit in items:
                item = hit.get("_embedded", {}).get("indexableObject", hit)
                values = item.get("metadata", {}).get("dc.date.accessioned", [])
                raw_date = values[0].get("value") if values else None
                if not raw_date:
                    item_uuid = item.get("uuid") or item.get("id")
                    href = hit.get("_links", {}).get("indexableObject", {}).get("href", "")
                    item_uuid = item_uuid or href.rstrip("/").split("/")[-1]
                    if item_uuid:
                        try:
                            detailed_item = self.get(f"core/items/{item_uuid}")
                            values = detailed_item.get("metadata", {}).get("dc.date.accessioned", [])
                            raw_date = values[0].get("value") if values else None
                        except DSpaceError:
                            pass
                if not raw_date:
                    continue
                try:
                    accessioned = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                    if accessioned.tzinfo is None:
                        accessioned = accessioned.replace(tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    continue
                if accessioned < start:
                    stop = True
                    break
                key = (accessioned.year, accessioned.month)
                if key in buckets:
                    buckets[key] += 1
            if stop or len(items) < 100:
                break
            page += 1

        return [
            {"year": year, "month": month, "label": f"{self.MONTH_LABELS[month - 1]} {year}", "items": count}
            for (year, month), count in buckets.items()
        ]

    def catalog_status(self):
        payload = self.get("contentreport/filteredcollections", params={
            "filters": "has_one_original,has_multiple_originals,has_no_originals,is_discoverable,has_restricted_original",
        })
        summary = payload.get("summary", {}).get("values", {})
        return {
            "with_files": (summary.get("has_one_original", 0) or 0) + (summary.get("has_multiple_originals", 0) or 0),
            "without_files": summary.get("has_no_originals"),
            "discoverable": summary.get("is_discoverable"),
            "restricted_files": summary.get("has_restricted_original"),
        }

    @staticmethod
    def _first_embedded(payload, *keys):
        embedded = payload.get("_embedded", {})
        for key in keys:
            entries = embedded.get(key)
            if isinstance(entries, list) and entries:
                return entries[0]
            if isinstance(entries, dict):
                return entries
        return None

    def site_usage(self):
        sites = self.get("core/sites", params={"size": 1, "page": 0})
        site = self._first_embedded(sites, "site", "sites")
        site_uri = (site or {}).get("_links", {}).get("self", {}).get("href")
        if not site_uri:
            raise DSpaceError("No se pudo localizar el recurso de sitio en la respuesta HAL de DSpace.")
        reports = self.get(
            "statistics/usagereports/search/object",
            params={"uri": site_uri, "page": 0, "size": 100},
        )
        return reports.get("_embedded", {}).get("usagereports", [])

    def stats(self):
        report_values = {}
        report_months = {}
        usage_error = None
        try:
            for report in self.site_usage():
                kind = report.get("report-type")
                points = report.get("points", [])
                if kind == "TotalVisits" and points:
                    report_values["views"] = sum(point.get("values", {}).get("views", 0) for point in points)
                elif kind == "TotalDownloads" and points:
                    report_values["downloads"] = sum(point.get("values", {}).get("downloads", 0) for point in points)
                elif kind == "TotalVisitsPerMonth" and points:
                    report_months["views"] = points[0].get("values", {})
        except DSpaceError as exc:
            usage_error = str(exc)

        counts = {
            "items": self.count("core/items"),
            "collections": self.count("core/collections"),
        }
        try:
            collections_by_items = self.collection_item_counts()
        except DSpaceError:
            collections_by_items = []
        try:
            publication_activity = self.publication_activity(12)
        except DSpaceError:
            publication_activity = None
        current_year = datetime.now(timezone.utc).year
        counts["ingress_this_year"] = (
            sum(row["items"] for row in publication_activity if row["year"] == current_year)
            if publication_activity is not None else None
        )
        try:
            catalog_status = self.catalog_status()
        except DSpaceError:
            catalog_status = None
        try:
            counts["pending"] = self.count("workflow/workflowitems")
        except DSpaceError:
            counts["pending"] = None
        return {
            "connected": True,
            "source": "dspace",
            "counts": counts,
            "collections_by_items": collections_by_items,
            "publication_activity": publication_activity,
            "catalog_status": catalog_status,
            "usage": report_values,
            "monthly": report_months,
            "usage_error": usage_error,
        }


def repository_stats():
    return DSpaceClient().stats()


