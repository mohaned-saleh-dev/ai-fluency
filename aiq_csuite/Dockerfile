# AiQ CSuite — production (Gunicorn). Build with context this folder, e.g.:
#   docker build -f aiq_csuite/Dockerfile -t ai-fluency-aiq ./aiq_csuite
#
# Base image sets CMD ["python3"]; we must clear it or it is appended to ENTRYPOINT args.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .
RUN mkdir -p instance \
    && chmod +x /app/docker-entrypoint.sh

ENV PORT=8080
EXPOSE 8080

ENTRYPOINT ["/app/docker-entrypoint.sh"]
# Prevent inheriting python base image CMD ["python3"] as extra argv to ENTRYPOINT
CMD []
