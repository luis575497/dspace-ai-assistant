import requests
from flask import current_app


class AIProviderError(RuntimeError):
    pass


def generate(prompt: str) -> str:
    """Generate content using the institution-configured provider."""
    provider = current_app.config["AI_PROVIDER"]
    if provider == "demo":
        return "Modo demostración: configura un proveedor de IA para analizar el contenido del documento."
    if provider == "ollama":
        try:
            response = requests.post(
                f"{current_app.config['OLLAMA_BASE_URL'].rstrip('/')}/api/generate",
                json={"model": current_app.config["OLLAMA_MODEL"], "prompt": prompt, "stream": False},
                timeout=180,
            )
            response.raise_for_status()
            return response.json()["response"].strip()
        except (requests.RequestException, KeyError, ValueError) as exc:
            raise AIProviderError("No se pudo obtener respuesta del modelo local.") from exc
    if provider == "openai":
        api_key = current_app.config.get("OPENAI_API_KEY")
        model = current_app.config.get("OPENAI_MODEL")
        if not api_key or not model:
            raise AIProviderError("Configura OPENAI_API_KEY y OPENAI_MODEL en el entorno del servicio.")
        try:
            response = requests.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "input": prompt, "store": False},
                timeout=180,
            )
            response.raise_for_status()
            payload = response.json()
            text = payload.get("output_text")
            if not text:
                text = "\n".join(
                    block.get("text", "")
                    for item in payload.get("output", [])
                    for block in item.get("content", [])
                    if block.get("type") == "output_text"
                ).strip()
            if not text:
                raise KeyError("output_text")
            return text
        except (requests.RequestException, KeyError, ValueError) as exc:
            raise AIProviderError("OpenAI no pudo procesar la solicitud. Revisa el modelo, la clave y los límites de la cuenta.") from exc
    if provider == "anthropic":
        api_key = current_app.config.get("ANTHROPIC_API_KEY")
        model = current_app.config.get("ANTHROPIC_MODEL")
        if not api_key or not model:
            raise AIProviderError("Configura ANTHROPIC_API_KEY y ANTHROPIC_MODEL en el entorno del servicio.")
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1600,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=180,
            )
            response.raise_for_status()
            payload = response.json()
            text = "\n".join(block.get("text", "") for block in payload.get("content", []) if block.get("type") == "text").strip()
            if not text:
                raise KeyError("content")
            return text
        except (requests.RequestException, KeyError, ValueError) as exc:
            raise AIProviderError("Anthropic no pudo procesar la solicitud. Revisa el modelo, la clave y los límites de la cuenta.") from exc
    raise AIProviderError(f"Proveedor no configurado o no compatible: {provider}")
