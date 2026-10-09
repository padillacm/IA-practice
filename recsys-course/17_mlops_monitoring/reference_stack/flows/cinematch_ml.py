"""Lógica de ML compartida por los orquestadores (Prefect, Airflow, Metaflow, Kubeflow).

Es la misma que en el notebook del módulo 17, empaquetada como módulo importable y testeable.
Mantenerla fuera de los DAGs/flows permite probarla con pytest en CI y reutilizarla en cualquier orquestador.
"""
from __future__ import annotations

import mlflow
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient
from scipy.sparse import csr_matrix

DIM, REG = 32, 20.0


def train_als(df: pd.DataFrame, dim: int = DIM, reg: float = REG, iters: int = 12, init: dict | None = None,
              min_count: int = 3, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    cnt = df.item_id.value_counts()
    items = np.sort(cnt[cnt >= min_count].index.to_numpy())
    imap = pd.Series(np.arange(len(items)), index=items)
    d = df[df.item_id.isin(items)].drop_duplicates(["user_id", "item_id"])
    users, uidx = np.unique(d.user_id.to_numpy(), return_inverse=True)
    R = csr_matrix((np.ones(len(d), np.float32), (uidx, imap[d.item_id].to_numpy())), shape=(len(users), len(items)))
    Y = rng.normal(0, 0.01, (len(items), dim)).astype(np.float32)
    if init is not None:                                   # warm start
        known = np.isin(items, init["items"])
        prev = pd.Series(np.arange(len(init["items"])), index=init["items"])
        Y[known] = init["Y"][prev[items[known]].to_numpy()]
        iters = min(iters, 4)
    eye = reg * np.eye(dim, dtype=np.float32)
    for _ in range(iters):
        X = (R @ Y) @ np.linalg.inv(Y.T @ Y + eye)
        Y = (R.T @ X) @ np.linalg.inv(X.T @ X + eye)
    return {"items": items, "Y": Y.astype(np.float32), "G": np.linalg.inv(Y.T @ Y + eye).astype(np.float32),
            "pop": cnt.reindex(items).to_numpy().astype(np.float32), "trained_until": int(df.ts.max())}


def recommend_batch(model: dict, hists: list[list[int]], k: int = 10) -> np.ndarray:
    imap = pd.Series(np.arange(len(model["items"])), index=model["items"])
    rows, cols = [], []
    for r, h in enumerate(hists):
        idx = imap.reindex(h).dropna().astype(int).to_numpy()
        rows += [r] * len(idx)
        cols += list(idx)
    H = csr_matrix((np.ones(len(rows), np.float32), (rows, cols)), shape=(len(hists), len(model["items"])))
    S = ((H @ model["Y"]) @ model["G"]) @ model["Y"].T + 1e-6 * np.log1p(model["pop"])[None]
    S[H.nonzero()] = -np.inf
    top = np.argpartition(-S, k, axis=1)[:, :k]
    top = np.take_along_axis(top, np.argsort(-np.take_along_axis(S, top, 1), 1), 1)
    return model["items"][top]


def evaluate(model: dict, holdout: pd.DataFrame, k: int = 10, min_inter: int = 10) -> float:
    """NDCG@k con fold-in: primera mitad temporal de cada usuario = historial, segunda = objetivo."""
    disc = 1 / np.log2(np.arange(2, k + 2))
    hists, tgts = [], []
    for _, g in holdout.sort_values("ts").groupby("user_id"):
        if len(g) < min_inter:
            continue
        it = g.item_id.to_numpy()
        h = len(it) // 2
        tg = set(it[h:]) - set(it[:h])
        if tg:
            hists.append(list(it[:h]))
            tgts.append(tg)
    if not hists:
        return 0.0
    recs = recommend_batch(model, hists, k)
    return float(np.mean([(np.isin(r, list(t)) * disc).sum() / disc[: min(k, len(t))].sum() for r, t in zip(recs, tgts)]))


class ALSPyfunc(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        z = np.load(context.artifacts["model"])
        self.m = {k: z[k] for k in z.files}

    def predict(self, context, model_input, params=None):
        return pd.DataFrame({"recs": [list(map(int, r)) for r in recommend_batch(self.m, list(model_input["history"]))]})


def register_model(model: dict, name: str, params: dict, metrics: dict) -> int:
    np.savez("/tmp/model.npz", **{k: model[k] for k in ("items", "Y", "G", "pop", "trained_until")})
    with mlflow.start_run(run_name=f"ct-{params.get('run_date', '')}"):
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        mlflow.pyfunc.log_model(name="model", python_model=ALSPyfunc(), artifacts={"model": "/tmp/model.npz"},
                                registered_model_name=name)
    return max(int(v.version) for v in MlflowClient().search_model_versions(f"name='{name}'"))


def load_champion(name: str) -> tuple[dict, int]:
    info = MlflowClient().get_model_version_by_alias(name, "champion")
    m = mlflow.pyfunc.load_model(f"models:/{name}@champion").unwrap_python_model().m
    return m, int(info.version)
