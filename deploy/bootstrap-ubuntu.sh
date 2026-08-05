#!/usr/bin/env bash
# One-time setup on an Oracle Cloud Ubuntu VM (Ampere/x86).
# Run as a sudo-capable user, e.g. ubuntu:
#   curl -fsSL https://raw.githubusercontent.com/Abhishekkohli/AI-Agent-Analytics-Assistant/main/deploy/bootstrap-ubuntu.sh | bash
# Or from a cloned repo:
#   sudo bash deploy/bootstrap-ubuntu.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/analytics-assistant}"
WEB_ROOT="${WEB_ROOT:-/var/www/analytics-assistant}"
REPO_URL="${REPO_URL:-https://github.com/Abhishekkohli/AI-Agent-Analytics-Assistant.git}"
BRANCH="${BRANCH:-main}"
ENV_FILE="/etc/analytics-assistant/env"
RUN_USER="${SUDO_USER:-ubuntu}"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Re-run with sudo: sudo bash $0"
  exit 1
fi

echo "==> System packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git nginx python3 python3-venv python3-pip curl ca-certificates

if ! command -v node >/dev/null 2>&1 || [[ "$(node -v | cut -d. -f1 | tr -d v)" -lt 20 ]]; then
  echo "==> Node.js 20"
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y -qq nodejs
fi

echo "==> App source at ${APP_DIR}"
if [[ ! -d "${APP_DIR}/.git" ]]; then
  git clone --depth 1 --branch "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
  chown -R "${RUN_USER}:${RUN_USER}" "${APP_DIR}"
else
  echo "    (already cloned — run deploy/update-app.sh to pull latest)"
fi

echo "==> Python venv + dependencies (may take several minutes on first run)"
sudo -u "${RUN_USER}" bash -c "
  cd '${APP_DIR}'
  python3 -m venv venv
  ./venv/bin/pip install -U pip wheel
  ./venv/bin/pip install -r requirements.txt
"

echo "==> Initialise SQLite + Chroma if missing"
sudo -u "${RUN_USER}" bash -c "
  cd '${APP_DIR}'
  if [[ ! -f business.db ]]; then
    ./venv/bin/python app.py --setup
  fi
"

echo "==> Build React frontend"
sudo -u "${RUN_USER}" bash -c "
  cd '${APP_DIR}/frontend'
  npm ci
  npm run build
"

echo "==> Publish static files"
mkdir -p "${WEB_ROOT}"
rsync -a --delete "${APP_DIR}/frontend/dist/" "${WEB_ROOT}/"
chown -R www-data:www-data "${WEB_ROOT}"

echo "==> Environment file"
mkdir -p /etc/analytics-assistant
if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${APP_DIR}/deploy/env.example" "${ENV_FILE}"
  chmod 600 "${ENV_FILE}"
  chown root:root "${ENV_FILE}"
  echo "    Edit ${ENV_FILE} and set GROQ_API_KEY, then: sudo systemctl restart analytics-api"
else
  echo "    ${ENV_FILE} already exists — left unchanged"
fi

echo "==> systemd"
cp "${APP_DIR}/deploy/systemd/analytics-api.service" /etc/systemd/system/analytics-api.service
systemctl daemon-reload
systemctl enable analytics-api

echo "==> nginx"
cp "${APP_DIR}/deploy/nginx/analytics-assistant.conf" /etc/nginx/sites-available/analytics-assistant
ln -sf /etc/nginx/sites-available/analytics-assistant /etc/nginx/sites-enabled/analytics-assistant
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx

echo "==> Optional 2G swap (helps on small VMs during model load)"
if [[ ! -f /swapfile ]]; then
  fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

systemctl restart analytics-api
systemctl restart nginx

PUBLIC_IP="$(curl -fsS -H 'Metadata-Flavor: Oracle' http://169.254.169.254/opc/v1/instance/metadata/publicIp 2>/dev/null || true)"
echo ""
echo "Bootstrap complete."
if [[ -n "${PUBLIC_IP}" ]]; then
  echo "Open http://${PUBLIC_IP}/ in your browser (after setting GROQ_API_KEY in ${ENV_FILE})."
else
  echo "Open http://<your-vm-public-ip>/ after setting GROQ_API_KEY in ${ENV_FILE}."
fi
echo "First API start loads embeddings — allow 2–5 minutes before /api/health returns ok."
