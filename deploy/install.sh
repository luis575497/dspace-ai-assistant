#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/dspace-ai-assistant

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Ejecuta este script como root dentro del LXC."
  exit 1
fi
if [[ ! -f "$APP_DIR/run.py" ]]; then
  echo "No encuentro $APP_DIR/run.py. Clona el repositorio allí antes de instalar."
  exit 1
fi

apt-get update
apt-get install -y python3 python3-venv python3-pip git ca-certificates
if ! id dspace-ai >/dev/null 2>&1; then
  useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin dspace-ai
fi
install -d -o dspace-ai -g dspace-ai "$APP_DIR/instance"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

if [[ ! -f /etc/dspace-ai-assistant.env ]]; then
  install -m 0600 "$APP_DIR/.env.example" /etc/dspace-ai-assistant.env
  SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')
  sed -i "s/^FLASK_SECRET_KEY=.*/FLASK_SECRET_KEY=$SECRET_KEY/" /etc/dspace-ai-assistant.env
fi
if ! grep -q '^APP_ACCESS_USER=.' /etc/dspace-ai-assistant.env; then
  sed -i '/^APP_ACCESS_USER=/d' /etc/dspace-ai-assistant.env
  echo 'APP_ACCESS_USER=admin' >> /etc/dspace-ai-assistant.env
fi
if ! grep -q '^APP_ACCESS_PASSWORD=.' /etc/dspace-ai-assistant.env; then
  sed -i '/^APP_ACCESS_PASSWORD=/d' /etc/dspace-ai-assistant.env
  ACCESS_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
  echo "APP_ACCESS_PASSWORD=$ACCESS_PASSWORD" >> /etc/dspace-ai-assistant.env
fi
install -m 0644 "$APP_DIR/deploy/dspace-ai-assistant.service" /etc/systemd/system/
install -m 0644 "$APP_DIR/deploy/dspace-ai-update.service" /etc/systemd/system/
install -m 0644 "$APP_DIR/deploy/dspace-ai-update.timer" /etc/systemd/system/
chown -R root:root "$APP_DIR"
chown dspace-ai:dspace-ai "$APP_DIR/instance"
systemctl daemon-reload
systemctl enable --now dspace-ai-assistant.service

if git -C "$APP_DIR" remote get-url origin >/dev/null 2>&1; then
  systemctl enable --now dspace-ai-update.timer
  echo "Actualización automática habilitada: revisa origin cada 5 minutos."
else
  echo "No hay remoto Git 'origin'; la actualización automática se habilitará al configurar uno."
fi
echo "Servicio iniciado. Configura /etc/dspace-ai-assistant.env y reinicia con: systemctl restart dspace-ai-assistant"
echo "URL: http://$(hostname -I | awk '{print $1}'):5000/"
echo "Usuario de acceso: $(sed -n 's/^APP_ACCESS_USER=//p' /etc/dspace-ai-assistant.env | tail -n1)"
echo "Contraseña de acceso: consulta /etc/dspace-ai-assistant.env (permisos 600)."
