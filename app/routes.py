from io import BytesIO
import json
import os
import requests
from pathlib import Path
from urllib.parse import urlparse

from flask import Blueprint, current_app, jsonify, redirect, render_template, request
from pypdf import PdfReader

from app.ai import AIProviderError, generate
from app.dspace import DSpaceError, repository_stats
from app.solr import SolrError, usage_stats

bp = Blueprint("main", __name__)


@bp.get("/")
def dashboard():
    return render_template("insights.html")


@bp.get("/insights")
def insights():
    return redirect("/#usage")


@bp.post("/api/analyze")
def analyze():
    uploaded = request.files.get("document")
    if not uploaded or not uploaded.filename:
        return jsonify(error="Selecciona un archivo PDF."), 400
    if not uploaded.filename.lower().endswith(".pdf"):
        return jsonify(error="Por ahora solo se admiten archivos PDF."), 415
    try:
        reader = PdfReader(BytesIO(uploaded.read()))
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
    except Exception:
        return jsonify(error="No se pudo leer el PDF. Comprueba que no esté dañado o protegido."), 422
    text = "\n".join(f"[Página {i + 1}] {content}" for i, content in enumerate(pages) if content)
    if not text:
        return jsonify(error="El PDF no contiene texto extraíble."), 422
    try:
        result = generate(
            "Responde en español. Analiza este documento académico. Devuelve un resumen breve, "
            "palabras clave y conceptos relevantes. Sustenta afirmaciones con números de página. "
            "Indica si falta información.\n\n" + text[:60000]
        )
    except AIProviderError as exc:
        return jsonify(error=str(exc)), 503
    return jsonify(result=result, pages=len(pages), provider=request.environ.get("AI_PROVIDER", "configured"))


@bp.post("/api/ask")
def ask():
    uploaded = request.files.get("document")
    question = request.form.get("question", "").strip()
    if not uploaded or not uploaded.filename or not question:
        return jsonify(error="Selecciona un PDF y escribe una pregunta."), 400
    try:
        reader = PdfReader(BytesIO(uploaded.read()))
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
    except Exception:
        return jsonify(error="No se pudo leer el PDF."), 422
    context = "\n".join(f"[Página {i + 1}] {content}" for i, content in enumerate(pages) if content)
    if not context:
        return jsonify(error="El PDF no contiene texto extraíble."), 422
    try:
        answer = generate(
            "Responde en el mismo idioma que la pregunta, usando solo el documento. "
            "Si no hay evidencia suficiente, dilo claramente. Incluye referencias a página "
            "entre corchetes, por ejemplo [p. 3].\nPregunta: " + question + "\nDocumento:\n" + context[:60000]
        )
    except AIProviderError as exc:
        return jsonify(error=str(exc)), 503
    return jsonify(answer=answer, pages=len(pages))


@bp.get("/api/stats")
def stats():
    return jsonify({"illustrative": True, "documents": 1284, "queries": 8932, "avg_seconds": 4.8,
                    "languages": {"es": 68, "en": 32}, "monthly": [42, 55, 49, 73, 68, 91, 84, 106, 98, 121, 137, 154]})


@bp.get("/api/repository-stats")
def repository_stats_api():
    if not current_app.config.get("DSPACE_REST_URL"):
        return jsonify(connected=False, demo=True, message="Configura DSPACE_REST_URL en .env para consultar estadísticas reales.")
    try:
        data = repository_stats()
    except DSpaceError as exc:
        return jsonify(connected=False, demo=False, message=str(exc)), 502
    try:
        data["solr_usage"] = usage_stats(request.args.get("year"))
    except SolrError as exc:
        data["solr_usage"] = {"connected": False, "message": str(exc)}
    return jsonify(data)


@bp.get("/api/config/dspace")
def get_dspace_config():
    return jsonify(
        url=current_app.config.get("DSPACE_REST_URL", ""),
        email=current_app.config.get("DSPACE_EMAIL") or "",
        has_credentials=bool(current_app.config.get("DSPACE_EMAIL") and current_app.config.get("DSPACE_PASSWORD")),
    )


@bp.post("/api/config/dspace")
def save_dspace_config():
    origin = request.headers.get("Origin")
    if origin and urlparse(origin).netloc != request.host:
        return jsonify(error="Origen de solicitud no válido."), 403

    payload = request.get_json(silent=True) or {}
    url = str(payload.get("url", "")).strip().rstrip("/")
    email = str(payload.get("email", "")).strip()
    password = str(payload.get("password", ""))
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        return jsonify(error="Ingresa una URL completa de DSpace, por ejemplo http://servidor:8080/server/api."), 400
    if bool(email) != bool(password) and not (email and not password):
        return jsonify(error="Para actualizar las credenciales, ingresa usuario y contraseña."), 400

    config_path = Path(current_app.config["DSPACE_CONFIG_PATH"])
    previous = {}
    try:
        previous = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if email and not password:
        password = previous.get("password") or current_app.config.get("DSPACE_PASSWORD") or ""
        if not password:
            return jsonify(error="Ingresa la contraseña de la cuenta o deja ambos campos vacíos para usar acceso público."), 400
    if not email:
        password = ""

    settings = {
        **previous,
        "url": url,
        "email": email,
        "password": password,
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = config_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(settings), encoding="utf-8")
    os.chmod(temp_path, 0o600)
    os.replace(temp_path, config_path)
    current_app.config["DSPACE_REST_URL"] = url
    current_app.config["DSPACE_EMAIL"] = email or None
    current_app.config["DSPACE_PASSWORD"] = password or None
    return jsonify(saved=True, url=url, email=email, has_credentials=bool(email and password))


@bp.get("/api/config/solr")
def get_solr_config():
    return jsonify(
        url=current_app.config.get("SOLR_STATISTICS_URL", ""),
        user=current_app.config.get("SOLR_USER") or "",
        has_credentials=bool(current_app.config.get("SOLR_USER") and current_app.config.get("SOLR_PASSWORD")),
    )


@bp.post("/api/config/solr")
def save_solr_config():
    origin = request.headers.get("Origin")
    if origin and urlparse(origin).netloc != request.host:
        return jsonify(error="Origen de solicitud no válido."), 403
    payload = request.get_json(silent=True) or {}
    url = str(payload.get("url", "")).strip().rstrip("/")
    user = str(payload.get("user", "")).strip()
    password = str(payload.get("password", ""))
    parsed = urlparse(url)
    if not url:
        config_path = Path(current_app.config["DSPACE_CONFIG_PATH"])
        try:
            settings = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            settings = {}
        settings.update(solr_url="", solr_user="", solr_password="")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = config_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(settings), encoding="utf-8")
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, config_path)
        current_app.config["SOLR_STATISTICS_URL"] = ""
        current_app.config["SOLR_USER"] = None
        current_app.config["SOLR_PASSWORD"] = None
        return jsonify(saved=True, url="", user="", has_credentials=False)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        return jsonify(error="Ingresa la URL base del núcleo statistics de Solr."), 400
    path = parsed.path.rstrip("/")
    if not path.endswith("/statistics"):
        return jsonify(error="La URL debe terminar en /solr/statistics."), 400
    if bool(user) != bool(password) and not (user and not password):
        return jsonify(error="Ingresa usuario y contraseña de Solr, o deja ambos vacíos."), 400

    config_path = Path(current_app.config["DSPACE_CONFIG_PATH"])
    try:
        previous = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    if user and not password:
        password = previous.get("solr_password") or current_app.config.get("SOLR_PASSWORD") or ""
        if not password:
            return jsonify(error="Ingresa la contraseña de Solr o borra el usuario si no usa autenticación."), 400
    if not user:
        password = ""
    settings = {
        "url": previous.get("url", current_app.config.get("DSPACE_REST_URL", "")),
        "email": previous.get("email", current_app.config.get("DSPACE_EMAIL") or ""),
        "password": previous.get("password", current_app.config.get("DSPACE_PASSWORD") or ""),
        "solr_url": url,
        "solr_user": user,
        "solr_password": password,
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = config_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(settings), encoding="utf-8")
    os.chmod(temp_path, 0o600)
    os.replace(temp_path, config_path)
    current_app.config["SOLR_STATISTICS_URL"] = url
    current_app.config["SOLR_USER"] = user or None
    current_app.config["SOLR_PASSWORD"] = password or None
    return jsonify(saved=True, url=url, user=user, has_credentials=bool(user and password))


@bp.post("/api/config/solr/test")
def test_solr_config():
    url = current_app.config.get("SOLR_STATISTICS_URL", "").rstrip("/")
    if not url:
        return jsonify(connected=False, message="Guarda primero la URL de Solr."), 400
    try:
        auth = None
        if current_app.config.get("SOLR_USER") and current_app.config.get("SOLR_PASSWORD"):
            auth = (current_app.config["SOLR_USER"], current_app.config["SOLR_PASSWORD"])
        response = requests.get(f"{url}/select", params={"q": "*:*", "rows": 0, "wt": "json"}, auth=auth, timeout=8)
        response.raise_for_status()
        result = response.json()
        count = result.get("response", {}).get("numFound")
        if count is None:
            return jsonify(connected=False, message="Solr respondió, pero no devolvió numFound."), 502
        return jsonify(connected=True, indexed_events=count)
    except (requests.RequestException, ValueError):
        return jsonify(connected=False, message="No se pudo consultar Solr. Verifica la URL, autenticación y acceso desde el LXC del asistente."), 502
