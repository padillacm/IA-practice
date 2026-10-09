"""CineMatch · servicio de recomendación de referencia (FastAPI + FAISS + LightGBM + Redis + Kafka + Prometheus).

Diferencias con la versión de Colab:
- Redis real (historial del usuario y caché de respuestas).
- `/event` publica en Kafka/Redpanda; el consumidor `nearline/consumer.py` actualiza Redis (desacoplado del request path).
- Métricas con `prometheus_client` (histogramas de latencia por etapa) en `/metrics`.
- Features de ítem desde Feast (online store Redis) si FEAST_REPO está definido; si no, desde parquet en memoria.
- Timeouts por etapa con degradación elegante: si el ranker falla, se devuelve el orden del retrieval.

Arranque local:  ART_DIR=../artifacts REDIS_HOST=localhost uvicorn main:app --port 8000
"""
from __future__ import annotations

import json
import logging
import os
import time
from contextlib import asynccontextmanager

import faiss
import lightgbm as lgb
import numpy as np
import pandas as pd
import redis
from fastapi import FastAPI
from prometheus_client import Counter, Histogram, make_asgi_app
from pydantic import BaseModel

log = logging.getLogger("cinematch")
ART = os.environ.get("ART_DIR", "/artifacts")
TTL = int(os.environ.get("CACHE_TTL", "60"))
TOPIC = os.environ.get("EVENTS_TOPIC", "cinematch.events")

# ---------------------------------------------------------------- métricas Prometheus
REQS = Counter("cinematch_requests_total", "Peticiones de recomendación", ["strategy"])
CACHE_HITS = Counter("cinematch_cache_hits_total", "Aciertos de caché")
DEGRADED = Counter("cinematch_degraded_total", "Respuestas degradadas (sin ranker)", ["reason"])
STAGE = Histogram("cinematch_stage_latency_seconds", "Latencia por etapa", ["stage"],
                  buckets=(0.0005, 0.001, 0.0025, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32))
SCORE = Histogram("cinematch_top1_score", "Score del top-1 (para prediction drift)",
                  buckets=[i / 20 for i in range(21)])

S: dict = {}  # estado global cargado una vez por worker


def load_artifacts() -> None:
    S["index"] = faiss.read_index(f"{ART}/items.faiss")
    S["emb"] = np.load(f"{ART}/item_emb.npy")
    S["genre"] = np.load(f"{ART}/genre_mat.npy")
    S["gnorm"] = np.linalg.norm(S["genre"], axis=1) + 1e-8
    S["ranker"] = lgb.Booster(model_file=f"{ART}/ranker.txt")
    itf = pd.read_parquet(f"{ART}/item_feats.parquet")
    S["pop"], S["rmean"] = itf.pop_cum.to_numpy(), itf.rating_mean_cum.to_numpy()
    prof = pd.read_parquet(f"{ART}/user_prof.parquet")
    S["prof"] = {int(u): (float(r.user_n), float(r.user_mean)) for u, r in prof.iterrows()}
    ugen = pd.read_parquet(f"{ART}/user_genre.parquet")
    S["ugen"] = {int(u): row for u, row in zip(ugen.index, ugen.to_numpy())}
    S["meta"] = json.load(open(f"{ART}/meta.json"))
    S["redis"] = redis.Redis(host=os.environ.get("REDIS_HOST", "localhost"), decode_responses=True)
    # Siembra idempotente del historial (en producción lo haría el pipeline batch, no el servicio)
    if not S["redis"].exists("hist:__seeded__"):
        pipe = S["redis"].pipeline()
        for u, h in json.load(open(f"{ART}/user_hist.json")).items():
            pipe.delete(f"hist:{u}")
            pipe.rpush(f"hist:{u}", *h)
        pipe.set("hist:__seeded__", 1)
        pipe.execute()
    try:
        from confluent_kafka import Producer
        S["producer"] = Producer({"bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP", "localhost:19092"),
                                  "linger.ms": 5, "acks": "1"})
    except Exception as e:  # sin Kafka seguimos funcionando: escribimos directo en Redis
        log.warning("Kafka no disponible (%s): /event escribirá directo en Redis", e)
        S["producer"] = None
    S["feast"] = None
    if os.environ.get("FEAST_REPO"):
        try:
            from feast import FeatureStore
            S["feast"] = FeatureStore(repo_path=os.environ["FEAST_REPO"])
        except Exception as e:
            log.warning("Feast no disponible (%s): uso features de ítem en memoria", e)
    # Warm-up: la primera llamada a FAISS/LightGBM es más lenta (páginas de memoria, JIT de hilos)
    S["ranker"].predict(np.zeros((100, len(S["meta"]["rank_feats"]))), num_threads=1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_artifacts()
    yield
    if S.get("producer"):
        S["producer"].flush(2)


app = FastAPI(title="CineMatch Recommender", lifespan=lifespan)
app.mount("/metrics", make_asgi_app())


class Event(BaseModel):
    user_id: int
    item_id: int
    event_type: str = "play"
    ts: float | None = None


def item_features(ids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if S["feast"] is None:
        return S["pop"][ids], S["rmean"][ids]
    d = S["feast"].get_online_features(features=["item_stats:pop_cum", "item_stats:rating_mean_cum"],
                                       entity_rows=[{"item_id": int(i)} for i in ids]).to_dict()
    pop = np.array([v if v is not None else 0 for v in d["pop_cum"]], dtype=float)
    rm = np.array([v if v is not None else 3.0 for v in d["rating_mean_cum"]], dtype=float)
    return pop, rm


def diversify(items, k: int, max_per_genre: int = 3) -> list[int]:
    out, cnt = [], {}
    for i in items:
        g = int(np.argmax(S["genre"][i][1:])) + 1
        if cnt.get(g, 0) < max_per_genre:
            out.append(int(i))
            cnt[g] = cnt.get(g, 0) + 1
        if len(out) == k:
            break
    return out


@app.get("/health")
def health():
    return {"status": "ok", "model_version": S["meta"]["model_version"]}


@app.get("/recommend/{user_id}")
def recommend(user_id: int, k: int = 10, use_cache: bool = True):
    R = S["redis"]
    key = f"recs:{S['meta']['model_version']}:{user_id}:{k}"   # la versión del modelo forma parte de la clave
    if use_cache and (hit := R.get(key)):
        CACHE_HITS.inc()
        return {**json.loads(hit), "cache": True}

    with STAGE.labels("user_features").time():
        hist = [int(x) for x in R.lrange(f"hist:{user_id}", -50, -1)]
    if not hist or user_id not in S["prof"]:
        REQS.labels("popularity_fallback").inc()
        seen = set(hist)
        return {"user_id": user_id, "items": [i for i in S["meta"]["popular"] if i not in seen][:k],
                "strategy": "popularity_fallback", "cache": False}

    with STAGE.labels("retrieval").time():
        v = S["emb"][hist].mean(0)
        v = (v / (np.linalg.norm(v) + 1e-8)).astype("float32")
        sc, ids = S["index"].search(v[None], 100 + len(hist))
        seen = set(hist)
        mask = np.array([(i not in seen) and i > 0 for i in ids[0]])
        ids, sc = ids[0][mask][:100], sc[0][mask][:100]

    strategy = "two_stage"
    try:
        with STAGE.labels("item_features").time():
            pop, rmean = item_features(ids)
            n_u, mean_u = S["prof"][user_id]
            aff = S["genre"][ids] @ S["ugen"][user_id] / S["gnorm"][ids]
            X = np.column_stack([sc, np.arange(len(ids)), pop, rmean, aff,
                                 np.full(len(ids), n_u), np.full(len(ids), mean_u)])
        with STAGE.labels("ranking").time():
            p = S["ranker"].predict(X, num_threads=1)
            order = ids[np.argsort(-p)]
            SCORE.observe(float(np.clip(p.max(), 0, 1)))   # booster binario → probabilidad
    except Exception as e:  # degradación elegante: mejor una lista sin ranker que un 500
        log.exception("ranker falló: %s", e)
        DEGRADED.labels("ranker_error").inc()
        order, strategy = ids, "retrieval_only"

    with STAGE.labels("reranking").time():
        items = diversify(order, k)
    REQS.labels(strategy).inc()
    resp = {"user_id": user_id, "items": items, "strategy": strategy, "model_version": S["meta"]["model_version"]}
    R.setex(key, TTL, json.dumps(resp))
    return {**resp, "cache": False}


@app.post("/event")
def event(e: Event):
    payload = e.model_dump()
    payload["ts"] = payload["ts"] or time.time()
    if S["producer"] is not None:
        # key=user_id → todos los eventos de un usuario van a la misma partición (orden garantizado)
        S["producer"].produce(TOPIC, key=str(e.user_id), value=json.dumps(payload))
        S["producer"].poll(0)
    else:
        R = S["redis"]
        R.rpush(f"hist:{e.user_id}", e.item_id)
        R.ltrim(f"hist:{e.user_id}", -50, -1)
        for k in R.scan_iter(f"recs:*:{e.user_id}:*"):
            R.delete(k)
    return {"ok": True}
