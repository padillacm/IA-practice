"""Pipeline retrieval → ranking como grafo de deployments en Ray Serve.  serve run app:app

Cada etapa escala de forma independiente (réplicas, GPUs fraccionales). Útil cuando el pipeline
incluye varios modelos (p. ej. retrieval + ranker + LLM de explicaciones).
"""
import faiss
import numpy as np
import onnxruntime as ort
from ray import serve
from starlette.requests import Request


@serve.deployment(num_replicas=2)
class Retriever:
    def __init__(self):
        self.index = faiss.read_index("artifacts/items.faiss")
        self.emb = np.load("artifacts/item_emb.npy")

    def __call__(self, hist: list[int]) -> np.ndarray:
        v = self.emb[hist].mean(0, keepdims=True).astype("float32")
        v /= np.linalg.norm(v) + 1e-8
        return self.index.search(v, 100)[1][0]


@serve.deployment(num_replicas=1, ray_actor_options={"num_cpus": 2})
class Ranker:
    def __init__(self):
        self.sess = ort.InferenceSession("artifacts/ranker.onnx")

    @serve.batch(max_batch_size=32, batch_wait_timeout_s=0.002)   # batching entre peticiones
    async def __call__(self, feats_list: list[np.ndarray]) -> list[np.ndarray]:
        sizes = [len(f) for f in feats_list]
        out = self.sess.run(None, {"x": np.concatenate(feats_list).astype(np.float32)})[0]
        return np.split(out, np.cumsum(sizes)[:-1])


@serve.deployment
class Recommender:
    def __init__(self, retriever, ranker):
        self.retriever, self.ranker = retriever, ranker

    async def __call__(self, request: Request) -> dict:
        body = await request.json()
        cands = await self.retriever.remote(body["history"])
        feats = np.random.rand(len(cands), 7).astype(np.float32)   # sustituir por el feature builder real
        scores = await self.ranker.remote(feats)
        return {"items": [int(i) for i in cands[np.argsort(-scores)][:10]]}


app = Recommender.bind(Retriever.bind(), Ranker.bind())
