"""Ranker ONNX servido con BentoML (API >= 1.2).  bentoml serve service:Ranker

`batchable=True` activa adaptive batching: BentoML agrupa peticiones concurrentes respetando max_latency_ms.
"""
import bentoml
import numpy as np


@bentoml.service(resources={"cpu": "2"}, traffic={"timeout": 5})
class Ranker:
    def __init__(self) -> None:
        import onnxruntime as ort
        self.sess = ort.InferenceSession("artifacts/ranker.onnx", providers=["CPUExecutionProvider"])

    @bentoml.api(batchable=True, max_batch_size=4096, max_latency_ms=10)
    def score(self, x: np.ndarray) -> np.ndarray:
        return self.sess.run(None, {"x": x.astype(np.float32)})[0]
