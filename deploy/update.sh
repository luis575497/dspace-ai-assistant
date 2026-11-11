#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/dspace-ai-assistant
BRANCH=${APP_BRANCH:-main}

if ! git -C "$APP_DIR" remote get-url origin >/dev/null 2>&1; then
  echo "Falta configurar el remoto Git origin."
  exit 0
fi

git -C "$APP_DIR" fetch --quiet origin "$BRANCH"
LOCAL=$(git -C "$APP_DIR" rev-parse HEAD)
REMOTE=$(git -C "$APP_DIR" rev-parse "origin/$BRANCH")
if [[ "$LOCAL" == "$REMOTE" ]]; then
  echo "Ya está actualizado ($LOCAL)."
  exit 0
fi
if ! git -C "$APP_DIR" merge-base --is-ancestor "$LOCAL" "$REMOTE"; then
  echo "El remoto no es avance directo de la versión instalada; no se aplicaron cambios."
  exit 1
fi

git -C "$APP_DIR" merge --ff-only "$REMOTE"
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
systemctl restart dspace-ai-assistant.service
echo "Actualizado a $REMOTE y servicio reiniciado."
