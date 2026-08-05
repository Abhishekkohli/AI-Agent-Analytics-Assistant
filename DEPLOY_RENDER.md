# Deploy on Render (free tier, stable URL)

Your public link stays **`https://ai-analytics-assistant.onrender.com`** (or whatever you set as `name` in `render.yaml`) for as long as the service exists — easily **3+ months**. Renaming or deleting the service changes the URL.

## What you get on free Render

| | |
|---|---|
| **Stable HTTPS URL** | Yes — fixed `*.onrender.com` subdomain |
| **Fast setup** | Connect GitHub → Blueprint → add `GROQ_API_KEY` |
| **Persistent sign-ups / history** | **No** — free instances use an **ephemeral disk**. After idle spin-down, redeploy, or restart, new accounts and question history are cleared. The **sample store data** baked into the Docker image remains. |
| **Idle behavior** | Spins down after ~15 min without traffic; first visit wakes it (~1 min). URL is the same. |
| **Monthly hours** | 750 free instance hours per workspace per month — enough for demos; not 24/7 all month every month. |

For durable accounts without managing a VM, use [DEPLOY_ORACLE.md](DEPLOY_ORACLE.md) instead.

---

## Step-by-step

### 1. GitHub

Code should be on GitHub (this repo):

`https://github.com/Abhishekkohli/AI-Agent-Analytics-Assistant`

### 2. Render account

1. Go to [https://render.com](https://render.com) and sign up (GitHub login is fine).
2. Confirm email if asked.

### 3. Create from Blueprint

1. Dashboard → **New** → **Blueprint**.
2. Connect the **Abhishekkohli/AI-Agent-Analytics-Assistant** repository.
3. Render reads **`render.yaml`** at the repo root.
4. When prompted, add **`GROQ_API_KEY`** (secret) — get a key at [Groq Console](https://console.groq.com/keys).
5. Click **Apply**.

First deploy builds the Docker image (npm + pip + `app.py --setup` + embeddings). Expect **15–25 minutes**. Watch **Logs**.

### 4. Open the app

When status is **Live**, open:

**https://ai-analytics-assistant.onrender.com**

(If you changed `name` in `render.yaml`, use that name instead.)

Sign up and test a question. If status shows **starting** in `/api/health`, wait a few minutes for the agent to finish loading.

### 5. Keep the same URL for 3 months

- Do **not** delete the web service.
- Do **not** rename the service (that changes the subdomain).
- Optional: **Settings → Custom Domains** to add your own domain; the Render URL still works.

Redeploys from Git pushes keep the **same** URL.

---

## Updates

Push to `main` on GitHub — Render auto-redeploys if you enabled auto-deploy (default for Blueprint).

---

## Troubleshooting

| Issue | Action |
|--------|--------|
| Build fails / out of memory | Retry deploy; if it keeps failing, upgrade to **Starter** ($7/mo) in service **Settings → Instance type**. |
| **502** after long idle | Normal on free tier — wait ~60s and refresh. |
| **missing_api_key** | Set `GROQ_API_KEY` in **Environment** and redeploy. |
| Health check fails on first deploy | First boot loads embeddings in the Docker build; runtime `/api/health` returns **200** with `"status":"starting"` until the agent finishes. Watch **Logs** for errors. |
| Lost my account after a week | Expected on free tier after spin-down/redeploy — sign up again. |

---

## Files

| File | Role |
|------|------|
| `Dockerfile` | Builds frontend + API; runs `app.py --setup` in the image |
| `render.yaml` | Render Blueprint (service name, env, health check) |
| `SERVE_STATIC=true` | API serves the React app on the same URL as `/api` |
