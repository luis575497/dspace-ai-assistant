# Instalar en un LXC de Proxmox

Se recomienda un LXC Debian 12 separado del LXC de DSpace. El asistente consulta DSpace por REST desde el backend Flask y no modifica archivos ni la base de datos de DSpace.

## 1. Crear el LXC en Proxmox

En el shell del nodo Proxmox, revisa primero los nombres reales de almacenamiento:

```bash
pvesm status
pveam update
pveam available --section system | grep debian-12-standard
```

En la salida identifica un storage de plantillas (a menudo `local`), un storage de discos (por ejemplo `local-lvm`) y el nombre de la plantilla Debian 12. Luego crea el contenedor, reemplazando estos valores por los de tu nodo:

```bash
CTID=140
TEMPLATE_STORAGE=local
ROOT_STORAGE=local-lvm
TEMPLATE=debian-12-standard_12.12-1_amd64.tar.zst
pveam download "$TEMPLATE_STORAGE" "$TEMPLATE"
pct create "$CTID" "$TEMPLATE_STORAGE:vztmpl/$TEMPLATE" \
  --hostname dspace-assistant \
  --cores 2 --memory 2048 --swap 512 \
  --rootfs "$ROOT_STORAGE:12" \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --unprivileged 1 --onboot 1
pct start "$CTID"
pct enter "$CTID"
```

Si los nombres de storage o la versión de plantilla no coinciden, usa los mostrados por los dos primeros comandos. Asigna al LXC una IP estable o reserva DHCP para que DSpace y tu equipo puedan encontrarlo.

## 2. Publicar y clonar el código

El actualizador requiere un repositorio Git remoto. Publica el proyecto en un repositorio Git que controles; no subas `.env`, claves de API ni contraseñas. Desde el shell del LXC:

```bash
apt-get update && apt-get install -y git
git clone https://github.com/USUARIO/REPOSITORIO.git /opt/dspace-ai-assistant
cd /opt/dspace-ai-assistant
chmod +x deploy/install.sh deploy/update.sh
./deploy/install.sh
```

El comando de `git clone` es una plantilla: reemplaza la URL por la de tu repositorio. El instalador configura Flask/Gunicorn como servicio systemd y, si detecta `origin`, un timer que revisa `main` cada cinco minutos y reinicia el servicio cuando llega una actualización.

## 3. Conectar con DSpace

Edita el archivo de configuración del servicio:

```bash
nano /etc/dspace-ai-assistant.env
```

Configura la URL de REST usando la IP interna del LXC de DSpace y su contexto real. Por ejemplo:

```dotenv
DSPACE_REST_URL=http://IP_DEL_LXC_DSPACE:8080/server/api
DSPACE_EMAIL=cuenta-de-lectura@institucion.edu
DSPACE_PASSWORD=CAMBIA_ESTA_CLAVE
AI_PROVIDER=demo
```

Si DSpace ofrece HTTPS con certificado válido, úsalo en lugar de HTTP. La cuenta debe tener el acceso mínimo necesario para leer los reportes. Solr no se expone al navegador. Después de guardar:

```bash
chmod 600 /etc/dspace-ai-assistant.env
systemctl restart dspace-ai-assistant
systemctl status dspace-ai-assistant --no-pager
journalctl -u dspace-ai-assistant -n 50 --no-pager
```

Entra a la vista de Conexión del panel y pulsa **Comprobar conexión**. Sin `DSPACE_REST_URL`, el panel indica que muestra estadísticas de demostración.

## 4. Abrir desde tu computadora

El servicio escucha solo en `127.0.0.1` del LXC para no exponer el asistente sin una capa de autenticación. Desde tu computadora abre un túnel SSH:

```bash
ssh -L 5000:127.0.0.1:5000 root@IP_DEL_LXC_ASISTENTE
```

Mientras la sesión SSH siga abierta, navega a `http://127.0.0.1:5000`. Para terminar, pulsa `Ctrl+C` en la terminal del túnel.

## 5. Actualizaciones de código

Cuando el código se publique en la rama `main` del remoto `origin`, el timer lo detectará en un máximo de cinco minutos, instalará requisitos nuevos y reiniciará Flask. Para comprobarlo manualmente:

```bash
systemctl start dspace-ai-update.service
journalctl -u dspace-ai-update.service -n 50 --no-pager
```

Ver estado del timer:

```bash
systemctl list-timers dspace-ai-update.timer
```
