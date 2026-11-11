# Alcance del producto

## Objetivo

Crear una alternativa abierta y autogestionable para las instituciones que usan DSpace. El repositorio institucional conserva la autoridad sobre documentos, permisos, estadísticas y configuración de IA. La aplicación se comunica con DSpace por interfaces documentadas y no necesita un fork del núcleo.

## Panel de gestión

Parte del prototipo visual `dspace-insights.html`, ahora accesible en `/insights`:

- **Resumen:** ítems publicados, ingresos del año, pendientes de revisión y descargas.
- **Ingresos y publicaciones:** tendencias mensuales, cola de revisión, antigüedad de pendientes, tiempo medio y distribución por colección.
- **Calidad y acceso:** metadatos faltantes, embargo próximo a vencer, acceso restringido y registros que requieren revisión.
- **Uso del repositorio:** visitas a ítems, descargas, relación descarga/visita, ítems más descargados, visitas y descargas mensuales, uso por colección.
- **Exportación y filtros:** tablas filtrables y exportación a CSV para que la institución conserve y reutilice sus datos.
- **Conexión:** configuración segura del DSpace y de su fuente de estadísticas; credenciales solo en el backend.

Las métricas de ejemplo deben etiquetarse como demostrativas hasta que el adaptador consulte una instalación. La semántica de visitas/descargas, exclusión de bots, periodos y versiones compatibles se documentará por conector.

## Módulo de IA

- Resúmenes automáticos de documentos PDF.
- Palabras clave y conceptos relevantes.
- Preguntas y respuestas en lenguaje natural sobre documentos, con citas de página.
- Ayuda para comprender textos académicos en español e inglés.
- Etiqueta visible de contenido generado por IA y señalamiento de límites de la respuesta.

La institución podrá elegir entre Ollama, OpenAI y Anthropic. La instalación local (por ejemplo, Ollama) será una opción destacada para mantener el procesamiento dentro de su infraestructura y apoyar sus políticas de derechos de autor y privacidad. Al elegir una API externa, el texto extraído se envía a ese proveedor y la institución debe evaluar sus condiciones. Las claves se guardan solo en el backend. Antes de cada operación, el servicio respetará la autorización de lectura que DSpace concede al usuario.

## Interoperabilidad y salida del proveedor

- Servicio Flask desplegable por la propia institución, con configuración documentada.
- DSpace REST como contrato principal para ítems, bitstreams, permisos e inventario.
- Adaptadores separados para estadísticas, porque sus fuentes y versiones pueden variar.
- Proveedores IA detrás de una interfaz común, sin acoplar el producto a una marca o modelo.
- Exportaciones en formatos comunes y configuración versionable; documentar instalación, respaldo, actualización y migración.
- Ninguna modificación al núcleo DSpace ni dependencia obligatoria de un servicio SaaS del proyecto.

## Etapas propuestas

1. Completar la maqueta de gestión y cerrar las métricas priorizadas.
2. Conectar API REST de una versión DSpace objetivo y validar acceso/roles.
3. Conectar la fuente de estadísticas elegida y reemplazar datos demostrativos.
4. Persistir tareas de IA y métricas agregadas sin conservar texto innecesario.
5. Añadir proveedores institucionales seleccionables, despliegue Docker y documentación bilingüe.

### Compatibilidad DSpace

La primera meta de compatibilidad incluye **DSpace 9 y DSpace 10**. El conector usa la API REST desde Flask para conteos de ítems/colecciones y reportes de uso; si hay datos restringidos, admite credenciales de una cuenta de lectura configurada solo en `.env`. La interfaz consulta al backend y nunca habla directamente con Solr. Las funciones comunes del dashboard no deben depender de detalles internos de una sola versión. Se validará cada versión por separado en instalaciones de referencia.

La licencia y la fuente concreta de estadísticas para cada instalación quedan por decidir.
