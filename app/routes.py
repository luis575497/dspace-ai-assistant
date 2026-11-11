from io import BytesIO

from flask import Blueprint, current_app, jsonify, redirect, render_template, request
from pypdf import PdfReader

from app.ai import AIProviderError, generate
from app.dspace import DSpaceError, repository_stats

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
        return jsonify(repository_stats())
    except DSpaceError as exc:
        return jsonify(connected=False, demo=False, message=str(exc)), 502
