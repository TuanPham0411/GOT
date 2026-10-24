# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm
ARG APP_REVISION=development
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 THIENHA_DATA_DIR=/data APP_REVISION=$APP_REVISION
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home app && mkdir /data && chown app:app /data
COPY requirements.txt ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install --no-cache-dir -r requirements.txt
COPY --chown=app:app app.py xiaozhi_tools.py seed.py ./
COPY --chown=app:app templates/ templates/
COPY --chown=app:app static/ static/
COPY --chown=app:app catalog/ catalog/
USER app
EXPOSE 5050
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=4 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5050/healthz',timeout=3)"
CMD ["gunicorn", "--bind", "0.0.0.0:5050", "--workers", "1", "--threads", "4", "--preload", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
