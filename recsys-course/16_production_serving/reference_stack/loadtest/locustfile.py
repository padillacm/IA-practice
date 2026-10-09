"""Test de carga de CineMatch.

locust -f locustfile.py --host http://localhost:8000 --headless -u 200 -r 20 -t 5m --csv out
Mezcla realista: 10 lecturas de home por cada evento de play. Usuarios Zipf (unos pocos muy activos).
"""
import random

import numpy as np
from locust import HttpUser, between, task

RNG = np.random.default_rng(42)
N_USERS = 943


def zipf_user() -> int:
    return int(min(RNG.zipf(1.2), N_USERS))


class HomeUser(HttpUser):
    wait_time = between(0.5, 2.0)    # think time: no midas QPS máximos con usuarios que no esperan

    @task(10)
    def home(self):
        self.client.get(f"/recommend/{zipf_user()}?k=10", name="/recommend/[user]")

    @task(1)
    def play(self):
        self.client.post("/event", json={"user_id": zipf_user(), "item_id": random.randint(1, 1682)}, name="/event")

    @task(1)
    def new_user(self):
        self.client.get(f"/recommend/{random.randint(10**6, 10**7)}", name="/recommend/[cold]")
