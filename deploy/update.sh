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
if ! grep -q '^APP_ACCESS_USER=.' /etc/dspace-ai-assistant.env; then
  sed -i '/^APP_ACCESS_USER=/d' /etc/dspace-ai-assistant.env
  echo 'APP_ACCESS_USER=admin' >> /etc/dspace-ai-assistant.env
fi
if ! grep -q '^APP_ACCESS_PASSWORD=.' /etc/dspace-ai-assistant.env; then
  sed -i '/^APP_ACCESS_PASSWORD=/d' /etc/dspace-ai-assistant.env
  ACCESS_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
  echo "APP_ACCESS_PASSWORD=$ACCESS_PASSWORD" >> /etc/dspace-ai-assistant.env
fi
chmod 600 /etc/dspace-ai-assistant.env
install -m 0644 "$APP_DIR/deploy/dspace-ai-assistant.service" /etc/systemd/system/dspace-ai-assistant.service
systemctl daemon-reload
systemctl restart dspace-ai-assistant.service
echo "Actualizado a $REMOTE y servicio reiniciado."
