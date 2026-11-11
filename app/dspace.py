"""Read-only DSpace REST connector for repository analytics."""

import requests
from flask import current_app


class DSpaceError(RuntimeError):
    pass


class DSpaceClient:
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
            counts["pending"] = self.count("workflow/workflowitems")
        except DSpaceError:
            counts["pending"] = None
        return {
            "connected": True,
            "source": "dspace",
            "counts": counts,
            "usage": report_values,
            "monthly": report_months,
            "usage_error": usage_error,
        }


def repository_stats():
    return DSpaceClient().stats()


