"""Consumidor nearline de CineMatch: Kafka/Redpanda → Redis.

- Lee `cinematch.events` en el consumer group GROUP_ID (varias réplicas se reparten las particiones).
- Actualiza `hist:{user}` (lista acotada a 50) e invalida `recs:*:{user}:*`.
- Commit manual del offset DESPUÉS de procesar ⇒ semántica at-least-once. Para que los duplicados
  no corrompan el estado, deduplicamos por (user, item, ts) con un SET con TTL (idempotencia).
"""
import json
import os
import signal

import redis
from confluent_kafka import Consumer, KafkaError

R = redis.Redis(host=os.environ.get("REDIS_HOST", "localhost"), decode_responses=True)
C = Consumer({
    "bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP", "localhost:19092"),
    "group.id": os.environ.get("GROUP_ID", "nearline-user-history"),
    "auto.offset.reset": "latest",       # al crear el grupo, empezamos por lo nuevo (el histórico lo cubre el batch)
    "enable.auto.commit": False,
})
C.subscribe([os.environ.get("EVENTS_TOPIC", "cinematch.events")])
RUNNING = True
signal.signal(signal.SIGTERM, lambda *_: globals().update(RUNNING=False))


def handle(ev: dict) -> None:
    dedup_key = f"seen:{ev['user_id']}:{ev['item_id']}:{ev['ts']}"
    if not R.set(dedup_key, 1, nx=True, ex=3600):   # ya procesado (reentrega tras un fallo)
        return
    pipe = R.pipeline()
    pipe.rpush(f"hist:{ev['user_id']}", ev["item_id"])
    pipe.ltrim(f"hist:{ev['user_id']}", -50, -1)
    pipe.execute()
    for k in R.scan_iter(f"recs:*:{ev['user_id']}:*"):
        R.delete(k)


while RUNNING:
    msgs = C.consume(num_messages=500, timeout=0.5)   # micro-batches: más throughput, latencia ~cientos de ms
    for m in msgs:
        if m.error():
            if m.error().code() != KafkaError._PARTITION_EOF:
                print("error:", m.error())
            continue
        handle(json.loads(m.value()))
    if msgs:
        C.commit(asynchronous=False)
C.close()
