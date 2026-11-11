# DSpace AI Assistant

Servicio abierto e independiente basado en Flask para gestión, analítica y asistencia generativa en repositorios DSpace. Busca que cada institución pueda instalarlo y operarlo por cuenta propia, conservar el control de sus datos y cambiar de proveedor sin quedar atada a una plataforma cerrada. Se integra mediante interfaces de DSpace, sin modificar su núcleo.

## Alcance inicial

- Resumen automático de PDF.
- Extracción de palabras clave y conceptos.
- Preguntas en lenguaje natural con referencias a páginas.
- Interfaz bilingüe (español e inglés) para apoyar a usuarios e investigadores.
- Panel de gestión inspirado en el prototipo DSpace Insights: inventario, ingresos y publicaciones, pendientes de revisión, calidad y acceso, visitas, descargas, tendencias, documentos destacados y actividad por colección.
- Integración desacoplada con DSpace mediante API REST y fuentes de estadísticas disponibles en cada instalación.
- Compatibilidad objetivo con DSpace 9 y 10 mediante adaptadores versionados.
- Despliegue autogestionado, datos exportables y proveedores intercambiables como principios contra el bloqueo tecnológico.

La aplicación tiene una sola vista en `/`: las estadísticas y el asistente IA son secciones internas, sin navegación a otra página. El conector Flask consulta la API REST de DSpace para el inventario y los informes de uso. Define `DSPACE_REST_URL` en `.env`; si la institución requiere autenticación, añade `DSPACE_EMAIL` y `DSPACE_PASSWORD` para una cuenta de lectura. Solr no se expone al navegador. Sin URL configurada, las cifras permanecen claramente marcadas como demostración.

Este primer esqueleto implementa carga de PDF, extracción de texto y proveedor local Ollama, además de la interfaz inicial. La integración de permisos y estadísticas reales de DSpace, persistencia y proveedores adicionales son siguientes etapas. No se debe exponer el servicio sin conectar la verificación de acceso del repositorio.

## Desarrollo

```bash
cd dspace-ai-assistant
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
flask --app run.py run --debug
```

La institución selecciona el proveedor en `.env` con `AI_PROVIDER=ollama`, `AI_PROVIDER=openai` o `AI_PROVIDER=anthropic`. Para Ollama, instala el servicio y configura `OLLAMA_MODEL` y `OLLAMA_BASE_URL`. Para OpenAI, configura `OPENAI_API_KEY` y `OPENAI_MODEL`; para Anthropic, `ANTHROPIC_API_KEY` y `ANTHROPIC_MODEL`. Los identificadores de modelo se dejan a elección y bajo control de la institución. Las claves permanecen en el backend y no deben guardarse en el navegador ni subirse al repositorio. `AI_PROVIDER=demo` permite explorar la interfaz sin enviar contenido a un modelo.

Con OpenAI se usa la Responses API y se solicita que la respuesta no se almacene mediante `store: false`; con Anthropic se usa Messages API. Al elegir cualquiera de estos servicios, el texto extraído del documento se transmite al proveedor configurado. Cada institución debe revisar sus políticas de privacidad, retención y derechos de autor antes de activarlo. El modo local evita esa transmisión a proveedores externos.

## Estadísticas

El panel incluye las métricas del prototipo `dspace-insights.html`: producción e ingresos, cola de revisión, calidad de metadatos y condiciones de acceso, visitas y descargas, principales documentos y colecciones. El backend ya consulta en vivo conteos de ítems y colecciones, reportes de visitas/descargas y pendientes si la cuenta los puede leer. Las métricas que aún no llegan de un conector se mantienen como demostrativas hasta implementarse. Se sumarán métricas de uso de IA con agregación y retención configurables.

Consulta [DESIGN.md](DESIGN.md) para el alcance funcional y los criterios de interoperabilidad.
Para desplegar en un LXC Debian separado y recibir actualizaciones desde una rama Git remota, sigue [deploy/README.md](deploy/README.md).

## Principios

- La institución elige y configura el proveedor de modelos.
- El modo local debe poder operar sin transmitir documentos a terceros.
- Solo procesar documentos que el usuario pueda leer en DSpace.
- Mostrar claramente contenido generado por IA y citar páginas de origen.
- Mantener los resúmenes separados de los metadatos originales.

## Licencia

Pendiente de decisión.
