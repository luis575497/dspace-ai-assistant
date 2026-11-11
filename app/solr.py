"""Read usage event aggregates from DSpace's Solr statistics core."""

from datetime import datetime, timezone

import requests
from flask import current_app


MONTHS_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


class SolrError(RuntimeError):
    pass


def _request(params):
    base_url = (current_app.config.get("SOLR_STATISTICS_URL") or "").rstrip("/")
    if not base_url:
        raise SolrError("Solr statistics todavía no está configurado.")
    auth = None
    user = current_app.config.get("SOLR_USER")
    password = current_app.config.get("SOLR_PASSWORD")
    if user and password:
        auth = (user, password)
    try:
        response = requests.get(f"{base_url}/select", params=params, auth=auth, timeout=12)
        response.raise_for_status()
        payload = response.json()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "desconocido"
        current_app.logger.warning("Solr rechazó la consulta de estadísticas (HTTP %s).", status)
        raise SolrError(f"Solr rechazó la consulta de estadísticas (HTTP {status}).") from exc
    except (requests.RequestException, ValueError) as exc:
        current_app.logger.warning("Falló la consulta de estadísticas a Solr: %s", exc)
        raise SolrError("No se pudieron consultar las estadísticas de Solr.") from exc
    if payload.get("responseHeader", {}).get("status") != 0:
        raise SolrError("Solr devolvió un error al consultar las estadísticas.")
    return payload


def usage_stats(year=None):
    """Return item views and bitstream downloads, excluding events marked as bots."""
    current_year = datetime.now(timezone.utc).year
    all_time = year == "all"
    try:
        selected_year = int(year) if year not in (None, "", "all") else current_year
    except (TypeError, ValueError):
        selected_year = current_year
    if selected_year < 2000 or selected_year > current_year + 1:
        selected_year = current_year

    # DSpace stores ITEM as type 2 and BITSTREAM as type 0 in usage events.
    # Both page views and file downloads are logged as statistics_type:view;
    # the requested object's type distinguishes the event.
    views_query = "statistics_type:view AND type:2 AND -isBot:true"
    downloads_query = "statistics_type:view AND type:0 AND bundleName:ORIGINAL AND -isBot:true"
    events = _request({"q": "*:*", "rows": 0, "wt": "json"})
    start = "2000-01-01T00:00:00Z" if all_time else f"{selected_year}-01-01T00:00:00Z"
    end = f"{current_year + 1}-01-01T00:00:00Z" if all_time else f"{selected_year + 1}-01-01T00:00:00Z"

    def count_and_months(query):
        params = {"q": query, "rows": 0, "wt": "json", "facet": "true", "facet.range": "time",
                  "f.time.facet.range.start": start, "f.time.facet.range.end": end,
                  "f.time.facet.range.gap": "+1MONTH"}
        payload = _request(params)
        total = int(payload.get("response", {}).get("numFound", 0))
        flat_counts = payload.get("facet_counts", {}).get("facet_ranges", {}).get("time", {}).get("counts", [])
        by_month = {}
        for index in range(0, len(flat_counts) - 1, 2):
            label, count = flat_counts[index], flat_counts[index + 1]
            try:
                month = datetime.fromisoformat(label.replace("Z", "+00:00")).month
            except (TypeError, ValueError):
                continue
            by_month[month] = by_month.get(month, 0) + int(count)
        months = [{"month": index + 1, "label": MONTHS_ES[index], "views": by_month.get(index + 1, 0)}
                  for index in range(12)]
        return total, months

    views, monthly_views = count_and_months(views_query)
    downloads, monthly_downloads = count_and_months(downloads_query)
    return {
        "connected": True,
        "year": "all" if all_time else selected_year,
        "events": int(events.get("response", {}).get("numFound", 0)),
        "views": views,
        "downloads": downloads,
        "monthly_views": monthly_views,
        "monthly_downloads": monthly_downloads,
    }
