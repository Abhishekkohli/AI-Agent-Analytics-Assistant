# Single container: React static build + FastAPI (Render free tier).
FROM node:20-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim-bookworm
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    TOKENIZERS_PARALLELISM=false \
    SERVE_STATIC=true

# Chroma / sentence-transformers may need a compiler on slim images
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /build/frontend/dist ./frontend/dist

# Bake sample store + Chroma into the image (survives restarts; not runtime writes)
RUN python app.py --setup

EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
