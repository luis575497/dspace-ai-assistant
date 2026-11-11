#!/usr/bin/env bash
set -euo pipefail

# Generates a small synthetic DSpace 9/10 test repository. It does not modify
# DSpace unless called with --apply. Run it as the operating-system user that
# owns the DSpace installation (usually "dspace"), never as root.

DSPACE_BIN=${DSPACE_BIN:-/dspace/bin/dspace}
ADMIN_EMAIL=${DSPACE_ADMIN_EMAIL:-}
WORK_DIR=${DSPACE_DEMO_DIR:-/tmp/bibliobytes-demo-seed}
COMMUNITY_NAME="Bibliobytes - Datos de prueba"

MODE=${1:---prepare}
if [[ "$MODE" != "--prepare" && "$MODE" != "--apply" ]]; then
  echo "Uso: $0 [--prepare|--apply]"
  exit 2
fi
if [[ "$(id -u)" -eq 0 ]]; then
  echo "Ejecuta este script como el usuario del sistema DSpace, no como root."
  echo "Ejemplo: runuser -u dspace -- env DSPACE_ADMIN_EMAIL=tu-correo $0 $MODE"
  exit 1
fi
if [[ ! -x "$DSPACE_BIN" ]]; then
  echo "No se encuentra el CLI de DSpace en: $DSPACE_BIN"
  echo "Puedes indicar otro con DSPACE_BIN=/ruta/bin/dspace."
  exit 1
fi
if [[ -z "$ADMIN_EMAIL" ]]; then
  read -r -p "Correo de administrador DSpace: " ADMIN_EMAIL
fi
if [[ -z "$ADMIN_EMAIL" ]]; then
  echo "El correo de administrador es obligatorio."
  exit 1
fi

mkdir -p "$WORK_DIR"
chmod 700 "$WORK_DIR"

python3 - "$WORK_DIR" <<'PY'
from pathlib import Path
from xml.etree import ElementTree as ET
import sys

root = Path(sys.argv[1])
collections = [
    ("ciencias", "Pruebas - Ciencias y Ambiente", "Registros sintéticos de ciencias y ambiente."),
    ("ingenieria", "Pruebas - Ingeniería", "Registros sintéticos de ingeniería y tecnología."),
    ("sociales", "Pruebas - Ciencias Sociales", "Registros sintéticos de ciencias sociales."),
]

structure = ET.Element("import_structure")
community = ET.SubElement(structure, "community")
ET.SubElement(community, "name").text = "Bibliobytes - Datos de prueba"
ET.SubElement(community, "description").text = "Comunidad temporal con contenido ficticio para probar estadísticas e IA."
ET.SubElement(community, "intro").text = "Todos los registros y documentos de esta comunidad son sintéticos y de prueba."
for slug, name, description in collections:
    collection = ET.SubElement(community, "collection")
    ET.SubElement(collection, "name").text = name
    ET.SubElement(collection, "description").text = description
    ET.SubElement(collection, "license").text = "Documento sintético generado para pruebas; se publica como CC0 1.0."
ET.indent(structure, space="  ")
ET.ElementTree(structure).write(root / "structure.xml", encoding="utf-8", xml_declaration=True)

def pdf_escape(value):
    value = value.encode("ascii", "replace").decode("ascii")
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

def write_pdf(path, title, abstract, number):
    rows = [title, "Documento sintetico para probar DSpace y el asistente Bibliobytes.",
            f"Registro de prueba {number:02d}.", abstract,
            "No representa una investigacion ni contiene datos de personas.",
            "Contenido generado unicamente para validacion tecnica."]
    commands = ["BT", "/F1 12 Tf"]
    y = 740
    for row in rows:
        words = row.split()
        wrapped, line = [], ""
        for word in words:
            if len(line) + len(word) > 82:
                wrapped.append(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        if line:
            wrapped.append(line)
        for text in wrapped:
            commands.append(f"1 0 0 1 72 {y} Tm ({pdf_escape(text)}) Tj")
            y -= 24
    commands.append("ET")
    stream = "\n".join(commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n% Bibliobytes test document\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(data)

topics = {
    "ciencias": ["Biodiversidad urbana y jardines para polinizadores", "Calidad del agua en microcuencas", "Restauracion de bosques andinos", "Observacion de aves en campus universitarios", "Gestion comunitaria de residuos organicos"],
    "ingenieria": ["Uso eficiente de energia en edificios publicos", "Prototipo de riego automatizado de bajo costo", "Analisis de movilidad sostenible", "Sensores abiertos para monitoreo ambiental", "Materiales reciclados para construccion experimental"],
    "sociales": ["Participacion ciudadana en gobiernos locales", "Acceso abierto y comunicacion cientifica", "Practicas de lectura en comunidades rurales", "Memoria oral y patrimonio local", "Servicios digitales para inclusion universitaria"],
}

for slug, _, _ in collections:
    source = root / "items" / slug
    source.mkdir(parents=True, exist_ok=True)
    for index, title in enumerate(topics[slug], 1):
        item = source / f"item_{index:03d}"
        item.mkdir(exist_ok=True)
        abstract = f"Este resumen ficticio describe un ejercicio de prueba sobre {title.lower()}. Los resultados y metodos son inventados para validar la carga, la extraccion de texto y los indicadores del repositorio."
        metadata = ET.Element("dublin_core")
        fields = [
            ("title", "none", title),
            ("creator", "none", f"Autor de prueba {index:02d}"),
            ("date", "issued", f"202{(index % 5) + 1}"),
            ("type", "none", "Artículo de prueba"),
            ("language", "iso", "es"),
            ("description", "abstract", abstract),
            ("subject", "none", "registro de prueba"),
            ("rights", "none", "Contenido sintético de prueba; CC0 1.0."),
        ]
        for element, qualifier, value in fields:
            ET.SubElement(metadata, "dcvalue", {"element": element, "qualifier": qualifier}).text = value
        ET.indent(metadata, space="  ")
        ET.ElementTree(metadata).write(item / "dublin_core.xml", encoding="utf-8", xml_declaration=True)
        (item / "contents").write_text("documento-prueba.pdf\n", encoding="utf-8")
        write_pdf(item / "documento-prueba.pdf", title, abstract, index)

print(f"Paquete SAF preparado en {root}")
PY

echo "Estructura y 15 documentos PDF sintéticos preparados en: $WORK_DIR"
if [[ "$MODE" == "--prepare" ]]; then
  echo "No se modificó DSpace. Revisa los archivos y, para importar, ejecuta: $0 --apply"
  exit 0
fi

if [[ -f "$WORK_DIR/IMPORT_COMPLETED" ]]; then
  echo "La carga ya figura como completada en $WORK_DIR/IMPORT_COMPLETED; se detiene para evitar duplicados."
  exit 1
fi

RESULT="$WORK_DIR/created-structure.xml"
if [[ ! -s "$RESULT" ]]; then
  "$DSPACE_BIN" structure-builder -x -e "$ADMIN_EMAIL" -o "$WORK_DIR/current-structure.xml"
  if grep -Fq "$COMMUNITY_NAME" "$WORK_DIR/current-structure.xml"; then
    echo "Ya existe '$COMMUNITY_NAME'. No se crea otra vez. Revisa la estructura exportada en $WORK_DIR/current-structure.xml."
    exit 1
  fi
  "$DSPACE_BIN" structure-builder -f "$WORK_DIR/structure.xml" -o "$RESULT" -e "$ADMIN_EMAIL"
fi

python3 - "$RESULT" "$WORK_DIR" <<'PY'
from pathlib import Path
from xml.etree import ElementTree as ET
import sys

structure_file, work_dir = Path(sys.argv[1]), Path(sys.argv[2])
handles = {}
for collection in ET.parse(structure_file).getroot().iter("collection"):
    name = collection.findtext("name")
    handle = collection.get("identifier")
    if name and handle:
        handles[name] = handle
for label in ("Ciencias y Ambiente", "Ingeniería", "Ciencias Sociales"):
    expected = f"Pruebas - {label}"
    matches = [value for name, value in handles.items() if name == expected]
    if not matches:
        raise SystemExit(f"No se encontró el handle para la colección {expected!r} en {structure_file}")
    print(f"{label}\t{matches[0]}")
PY

while IFS=$'\t' read -r label handle; do
  slug=$(case "$label" in Ciencias\ y\ Ambiente) echo ciencias;; Ingeniería) echo ingenieria;; Ciencias\ Sociales) echo sociales;; esac)
  mapfile="$WORK_DIR/mapfile-$slug"
  if [[ -s "$mapfile" ]]; then
    echo "Omitiendo $label: ya existe $mapfile"
    continue
  fi
  source="$WORK_DIR/items/$slug"
  echo "Validando $label ($handle)…"
  "$DSPACE_BIN" import --add --eperson="$ADMIN_EMAIL" --collection="$handle" --source="$source" --mapfile="$mapfile" --validate
  echo "Importando $label…"
  "$DSPACE_BIN" import --add --eperson="$ADMIN_EMAIL" --collection="$handle" --source="$source" --mapfile="$mapfile"
done < <(python3 - "$RESULT" <<'PY'
from xml.etree import ElementTree as ET
import sys
for collection in ET.parse(sys.argv[1]).getroot().iter("collection"):
    name, handle = collection.findtext("name"), collection.get("identifier")
    if name and handle and name.startswith("Pruebas - "):
        print(f"{name.removeprefix('Pruebas - ')}\t{handle}")
PY
)

date -Is > "$WORK_DIR/IMPORT_COMPLETED"
echo "Carga terminada. Guarda el directorio $WORK_DIR: contiene los mapfiles para identificar y eventualmente retirar los ítems de prueba."
