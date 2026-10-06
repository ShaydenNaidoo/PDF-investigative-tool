FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash qpdf poppler-utils gawk bsdextrautils coreutils findutils \
       grep sed diffutils file unzip ca-certificates rclone \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 lab \
    && mkdir -p /workspace/home /workspace/environment/observations /workspace/dataset \
    && chown -R lab:lab /workspace

WORKDIR /app
COPY pdf-analyzer/ ./pdf-analyzer/
COPY environment_set/environment/observations/ /opt/pdf-analyzer/seed/environment/observations/
RUN find /opt/pdf-analyzer/seed -type d -exec chmod 755 {} + \
    && find /opt/pdf-analyzer/seed -type f -exec chmod a+r {} +

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PDF_LAB_CONTAINER=1 \
    PDF_OBSERVATIONS_DIR=/workspace/environment/observations \
    PDF_DATASET_DIR=/workspace/dataset \
    PDF_SEED_ENVIRONMENT=/opt/pdf-analyzer/seed/environment \
    PDF_ANALYZER_HOME=/app/pdf-analyzer \
    HOME=/workspace/home

ARG LAB_RUNTIME_USER=lab
USER ${LAB_RUNTIME_USER}
EXPOSE 8766
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=4 \
    CMD python3 -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8766') + '/api/health', timeout=3).read()"
ENTRYPOINT ["python3", "pdf-analyzer/container_entrypoint.py"]
CMD ["--host", "0.0.0.0"]
