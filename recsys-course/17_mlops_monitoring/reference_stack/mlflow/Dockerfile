# Imagen común para MLflow server, worker de Prefect y Evidently UI.
FROM python:3.11-slim
RUN pip install --no-cache-dir "mlflow>=2.16" psycopg2-binary boto3 "prefect>=3.0" "evidently>=0.7" \
    "pandera>=0.20" prometheus-client scipy scikit-learn pandas pyarrow
WORKDIR /srv
