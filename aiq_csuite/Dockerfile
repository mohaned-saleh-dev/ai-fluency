# AiQ CSuite — production (Gunicorn). Build from repo root with context this folder, e.g.:
#   docker build -f aiq_csuite/Dockerfile -t ai-fluency-aiq ./aiq_csuite
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .
RUN mkdir -p instance

ENV PORT=8080
EXPOSE 8080

CMD exec gunicorn -b 0.0.0.0:${PORT} -w 1 --threads 4 --timeout 180 --access-logfile - "app:app"
