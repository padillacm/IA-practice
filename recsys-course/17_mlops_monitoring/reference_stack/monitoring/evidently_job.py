"""Job de monitoreo: drift tabular (Evidently), catalog drift (OOV) y embedding drift → Pushgateway.

Se ejecuta dentro del flow de CT (diario) o como job independiente cada hora sobre los logs del servicio.
"""
from __future__ import annotations

import os
import re

import numpy as np
import pandas as pd
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score


def js_div(a, b) -> float:
    cats = sorted(set(a) | set(b))
    p = pd.Series(a).value_counts(normalize=True).reindex(cats).fillna(0).to_numpy() + 1e-9
    q = pd.Series(b).value_counts(normalize=True).reindex(cats).fillna(0).to_numpy() + 1e-9
    m = (p + q) / 2
    return float(0.5 * np.sum(p * np.log(p / m)) + 0.5 * np.sum(q * np.log(q / m)))


def evidently_share(ref: pd.DataFrame, cur: pd.DataFrame, workspace: str | None = None) -> float:
    from evidently import Report
    from evidently.presets import DataDriftPreset

    snap = Report([DataDriftPreset()]).run(current_data=cur, reference_data=ref)
    flags = []
    for m in snap.dict()["metrics"]:
        name = m["metric_name"]
        if name.startswith("ValueDrift"):
            thr = float(re.search(r"threshold=([\d.]+)", name).group(1))
            v = float(m["value"])
            flags.append(v < thr if "p_value" in name else v >= thr)
    if workspace:  # persistir el snapshot en la UI de Evidently (servicio evidently-ui)
        from evidently.ui.workspace import Workspace
        ws = Workspace.create(workspace)
        proj = ws.search_project("cinematch")[0] if ws.search_project("cinematch") else ws.create_project("cinematch")
        ws.add_run(proj.id, snap, include_data=False)
    return float(np.mean(flags)) if flags else 0.0


def user_vectors(model: dict, df: pd.DataFrame, max_users: int = 500) -> np.ndarray:
    imap = pd.Series(np.arange(len(model["items"])), index=model["items"])
    out = []
    for _, g in list(df.groupby("user_id"))[:max_users]:
        idx = imap.reindex(g.item_id).dropna().astype(int).to_numpy()
        if len(idx):
            out.append(model["Y"][idx].sum(0) @ model["G"])
    return np.array(out)


def drift_metrics(model: dict, cur: pd.DataFrame, ref: pd.DataFrame) -> dict:
    cols = ["rating"] + [c for c in ("item_age", "main_genre") if c in cur.columns]
    A, B = user_vectors(model, ref), user_vectors(model, cur)
    auc = 0.5
    if min(len(A), len(B)) >= 10:
        X, y = np.vstack([A, B]), np.r_[np.zeros(len(A)), np.ones(len(B))]
        auc = float(cross_val_score(LogisticRegression(max_iter=500), X, y, cv=3, scoring="roc_auc").mean())
    return {
        "oov": float((~cur.item_id.isin(model["items"])).mean()),
        "js_genre": js_div(ref.main_genre, cur.main_genre) if "main_genre" in cur else 0.0,
        "evidently_share": evidently_share(ref[cols], cur[cols], os.environ.get("EVIDENTLY_WORKSPACE")),
        "emb_auc": auc,
    }


def push_metrics(metrics: dict, job: str = "cinematch_drift") -> None:
    gw = os.environ.get("PUSHGATEWAY")
    if not gw:
        return
    reg = CollectorRegistry()
    for k, v in metrics.items():
        Gauge(f"cinematch_{k}", f"Métrica de monitoreo {k}", registry=reg).set(v)
    push_to_gateway(gw, job=job, registry=reg)
