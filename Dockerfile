# Contentful article downloader (Flask) — production image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Minimal deps: full tree may include unused packages; this keeps the image buildable
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App + the readable-export script the service imports
COPY contentful_portal/ ./contentful_portal/
COPY scripts/contentful_entries_readable_csv.py ./scripts/

EXPOSE 8080
ENV PORT=8080
# Gunicorn: 1 worker keeps memory down for large JSON; increase on paid tiers
CMD gunicorn -b 0.0.0.0:$PORT -w 1 --threads 2 --timeout 300 "contentful_portal.app:app"
