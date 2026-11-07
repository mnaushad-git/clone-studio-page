# Production image for the API, Celery worker and Celery Beat.
# Build from the repository root (the seed script needs data/catalogue):
#   docker build -f deploy/backend.Dockerfile -t terrific-bites-api:<git-sha> .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY backend/alembic.ini ./
RUN pip install --upgrade pip && pip install .

# app/scripts resolve the catalogue as <repo root>/data, which is /data in this image.
COPY data/catalogue /data/catalogue

# A named volume mounted on /app/media inherits this ownership on first use.
RUN useradd --system --uid 10001 --no-create-home appuser \
    && mkdir -p /app/media \
    && chown -R appuser:appuser /app/media
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
