"""Flow de Continuous Training de CineMatch (Prefect 3).

Ejecución puntual:   python ct_flow.py --run
Programado:          python ct_flow.py --serve      (cron diario 03:17 UTC; ver docker-compose)

Pasos: ingest → validate (Pandera) → drift (Evidently + OOV + embedding drift) → [train → evaluate → register → promote]
La lógica de modelo (train_als, recommend_batch, evaluate) es la del notebook del módulo 17; aquí se importa de
`cinematch_ml.py` (cópiala desde el notebook) para que el flow sea solo orquestación.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import mlflow
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient
from prefect import flow, get_run_logger, task
from prefect.cache_policies import NO_CACHE

sys.path.insert(0, "/monitoring")
from validation_schema import validate_interactions  # noqa: E402
from evidently_job import drift_metrics, push_metrics  # noqa: E402

import cinematch_ml as ml  # noqa: E402  (train_als, evaluate, register_model, load_champion)

MODEL_NAME = os.environ.get("MODEL_NAME", "cinematch-retrieval")
DATA_DIR = os.environ.get("DATA_DIR", "/data")
THRESHOLDS = {"oov": 0.10, "js_genre": 0.02, "emb_auc": 0.65}


@task(retries=3, retry_delay_seconds=60, cache_policy=NO_CACHE)
def ingest(start: datetime, end: datetime) -> pd.DataFrame:
    """Lee las particiones del data lake (aquí parquet diario) del intervalo [start, end)."""
    days = pd.date_range(start, end - timedelta(days=1), freq="D")
    parts = [pd.read_parquet(f"{DATA_DIR}/events/date={d:%Y-%m-%d}") for d in days
             if os.path.exists(f"{DATA_DIR}/events/date={d:%Y-%m-%d}")]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


@task(cache_policy=NO_CACHE)
def validate(batch: pd.DataFrame) -> bool:
    ok, failures = validate_interactions(batch)
    if not ok:
        get_run_logger().error("Lote rechazado:\n%s", failures)
    return ok


@task(cache_policy=NO_CACHE)
def drift(champion: dict, batch: pd.DataFrame, reference: pd.DataFrame) -> dict:
    metrics = drift_metrics(champion, batch, reference)
    push_metrics(metrics, job="cinematch_drift")      # → Pushgateway → Prometheus → alertas/Grafana
    return metrics


@task(cache_policy=NO_CACHE, timeout_seconds=3 * 3600)
def train(train_df: pd.DataFrame, init: dict | None) -> dict:
    return ml.train_als(train_df, init=init)


@task(cache_policy=NO_CACHE)
def evaluate(model: dict, holdout: pd.DataFrame) -> float:
    return ml.evaluate(model, holdout)


@flow(name="cinematch-continuous-training", log_prints=True)
def ct_flow(run_date: str | None = None, window_days: int = 3 * 365, force: bool = False) -> dict:
    log = get_run_logger()
    end = datetime.fromisoformat(run_date) if run_date else datetime.now(timezone.utc).replace(tzinfo=None)
    end = end.replace(hour=0, minute=0, second=0, microsecond=0)
    batch = ingest(end - timedelta(days=1), end)                    # datos de ayer
    if batch.empty or not validate(batch):
        return {"action": "blocked"}

    client = MlflowClient()
    champion, v_champ = ml.load_champion(MODEL_NAME)
    reference = ingest(end - timedelta(days=8), end - timedelta(days=1))   # semana anterior como referencia
    m = drift(champion, batch, reference)
    if not (force or any(m[k] > THRESHOLDS[k] for k in THRESHOLDS)):
        log.info("Sin drift relevante: %s", m)
        return {"action": "no_retrain", **m}

    hist = ingest(end - timedelta(days=window_days), end - timedelta(days=1))
    holdout = batch                                                # validación = el día más reciente
    challenger = train(hist, init=champion)                        # warm start desde el champion
    nd_ch, nd_cp = evaluate(challenger, holdout), evaluate(champion, holdout)
    v = ml.register_model(challenger, MODEL_NAME, params={"window_days": window_days, "run_date": str(end.date())},
                          metrics={"ndcg_holdout_challenger": nd_ch, "ndcg_holdout_champion": nd_cp, **m})
    client.set_registered_model_alias(MODEL_NAME, "challenger", v)
    # La promoción a champion NO es automática aquí: la hace el job de canary tras pasar los guardrails online.
    if nd_ch < nd_cp:
        log.warning("Challenger v%s peor que champion v%s (%.4f < %.4f): no se propone a canary", v, v_champ, nd_ch, nd_cp)
        return {"action": "rejected", "challenger": v}
    return {"action": "challenger_ready_for_canary", "challenger": v, "ndcg": nd_ch}


if __name__ == "__main__":
    if "--serve" in sys.argv:
        mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
        ct_flow.serve(name="cinematch-ct-daily", cron="17 3 * * *", parameters={"window_days": 3 * 365})
    else:
        print(ct_flow())
