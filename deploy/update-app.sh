#!/usr/bin/env bash
# Pull latest code, rebuild frontend, restart API. Run on the VM:
#   sudo bash /opt/analytics-assistant/deploy/update-app.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/analytics-assistant}"
WEB_ROOT="${WEB_ROOT:-/var/www/analytics-assistant}"
RUN_USER="${SUDO_USER:-ubuntu}"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Re-run with sudo"
  exit 1
fi

cd "${APP_DIR}"
sudo -u "${RUN_USER}" git pull --ff-only

sudo -u "${RUN_USER}" bash -c "
  cd '${APP_DIR}'
  ./venv/bin/pip install -r requirements.txt
  cd frontend && npm ci && npm run build
"

rsync -a --delete "${APP_DIR}/frontend/dist/" "${WEB_ROOT}/"
chown -R www-data:www-data "${WEB_ROOT}"

systemctl restart analytics-api
echo "Updated and restarted analytics-api."
