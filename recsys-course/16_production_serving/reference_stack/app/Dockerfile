# Imagen del servicio de recomendación. Multi-stage no es necesario: las wheels de faiss-cpu/lightgbm son binarias.
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
# Usuario sin privilegios
RUN useradd -m app && chown -R app /srv
USER app
EXPOSE 8000
# Varios workers: cada uno carga los artefactos en memoria (cuenta RAM = workers × tamaño del índice).
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-2}"]
