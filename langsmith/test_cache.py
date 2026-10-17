
import requests, pytest
from langsmith import testing as t

@pytest.mark.langsmith
def test_clasifica():
    r = requests.post("http://127.0.0.1:46733/v1/chat", json={"m": "cobro duplicado"})
    datos = r.json()
    t.log_inputs({"mensaje": "cobro duplicado"})
    t.log_outputs({"categoria": datos["respuesta"]})
    assert datos["respuesta"] == "facturacion"
