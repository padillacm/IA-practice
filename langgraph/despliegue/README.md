# Agente de soporte — aplicación desplegable

Generada por el notebook `06_produccion/18_despliegue.ipynb` del curso.

## Ejecutar en local

```bash
pip install "langgraph-cli[inmem]"
cd langgraph/despliegue
langgraph dev
```

Se levanta en `http://127.0.0.1:2024` y la salida incluye el enlace a LangGraph Studio.

## Probar

```bash
curl -s http://127.0.0.1:2024/assistants/search -X POST \
  -H 'Content-Type: application/json' -d '{"limit": 10}'
```
