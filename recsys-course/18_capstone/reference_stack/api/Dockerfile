# API del capstone: copia cinematch_serving.py y capstone_api.py generados por el notebook del proyecto.
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY cinematch_serving.py capstone_api.py ./
EXPOSE 8018
CMD ["uvicorn", "capstone_api:app", "--host", "0.0.0.0", "--port", "8018", "--workers", "2"]
