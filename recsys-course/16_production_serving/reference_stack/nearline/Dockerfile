FROM python:3.11-slim
# Comillas obligatorias: sin ellas el shell interpreta ">=2.4" como una redirección a un fichero "=2.4"
RUN pip install --no-cache-dir "confluent-kafka>=2.4" "redis>=5.0"
COPY consumer.py /srv/consumer.py
CMD ["python", "/srv/consumer.py"]
