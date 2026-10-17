# Imagen de laboratorio de SupportOps (módulo 19). Construcción SIN red de pip si primero descargas las ruedas:
#   pip download -d wheels "opentelemetry-sdk>=1.39" "opentelemetry-exporter-otlp-proto-http>=1.39"
#   docker build -f 19_kubernetes_helm/k8s/image/Dockerfile -t supportops:lab .      (contexto = agent-observability-course/)
#   kind load docker-image supportops:lab --name obs19
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY pyproject.toml ./pyproject.toml
COPY supportops ./supportops
RUN pip install --no-cache-dir ".[otel]"
USER 10001
ENTRYPOINT []
CMD ["python", "-m", "supportops.k8s", "run"]
