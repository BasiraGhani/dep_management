# Backend image: FastAPI on Uvicorn. Migrations run on every start (docker-entrypoint.sh).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so code changes don't reinstall them.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini docker-entrypoint.sh ./
COPY alembic ./alembic
COPY app ./app

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 app && chmod +x docker-entrypoint.sh
USER app

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=2)"

ENTRYPOINT ["./docker-entrypoint.sh"]
