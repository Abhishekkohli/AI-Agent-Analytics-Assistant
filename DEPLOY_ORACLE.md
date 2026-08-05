# Deploy on Oracle Cloud (Always Free VM)

This runs the **full app** (React UI + FastAPI + SQLite + Chroma + embeddings) on one VM with **persistent disk**. Nginx serves the built frontend and proxies `/api` to Uvicorn.

## 1. Create the VM

1. Sign in to [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/).
2. Create a **Compute Instance**:
   - **Shape:** Ampere A1 (recommended **2 OCPU / 12 GB RAM** minimum; **4 OCPU / 24 GB** is more comfortable for embedding load)
   - **Image:** Ubuntu 22.04 or 24.04 (aarch64)
   - **Boot volume:** 50–100 GB
   - Assign a **public IPv4**
3. **Networking → Security list** for the subnet: allow inbound **22**, **80**, and **443** (TCP) from `0.0.0.0/0` (tighten to your IP for SSH in production).
4. SSH: `ssh -i your.key ubuntu@<PUBLIC_IP>`

## 2. One-command bootstrap (on the VM)

```bash
curl -fsSL https://raw.githubusercontent.com/Abhishekkohli/AI-Agent-Analytics-Assistant/main/deploy/bootstrap-ubuntu.sh | sudo bash
```

Or clone first and run locally:

```bash
git clone https://github.com/Abhishekkohli/AI-Agent-Analytics-Assistant.git
cd AI-Agent-Analytics-Assistant
sudo bash deploy/bootstrap-ubuntu.sh
```

## 3. Set your Groq key

```bash
sudo nano /etc/analytics-assistant/env
# Set GROQ_API_KEY=gsk_...
sudo systemctl restart analytics-api
```

Watch startup (first boot loads the embedding model):

```bash
sudo journalctl -u analytics-api -f
```

When ready, open `http://<PUBLIC_IP>/` and sign up.

## 4. HTTPS (optional)

With a domain pointing at the VM:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## 5. Updates

On the VM after you push to GitHub:

```bash
sudo bash /opt/analytics-assistant/deploy/update-app.sh
```

## Layout on the server

| Path | Purpose |
|------|---------|
| `/opt/analytics-assistant` | Git clone, venv, `business.db`, `accounts.db`, `.chroma` |
| `/var/www/analytics-assistant` | Built React static files |
| `/etc/analytics-assistant/env` | Secrets (`GROQ_API_KEY`) |
| `analytics-api.service` | Uvicorn on `127.0.0.1:8000` |
| nginx | Port 80 → static + `/api` proxy |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Site loads but “Unavailable” | Set `GROQ_API_KEY` and restart API |
| 502 / timeout on first question | Wait for model load; check `journalctl -u analytics-api` |
| Blank page on refresh | nginx `try_files` — re-run bootstrap nginx step |
| Out of memory | Use a larger Ampere shape or rely on the 2G swap from bootstrap |

## Cost

Oracle **Always Free** Ampere + block storage within free limits; Groq free tier for LLM calls. No paid host required if you stay within those quotas.
