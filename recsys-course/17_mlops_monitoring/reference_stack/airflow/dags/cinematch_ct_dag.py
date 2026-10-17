"""El mismo pipeline de CT como DAG de Apache Airflow (≥ 2.7, TaskFlow API).

Diferencias con Prefect: el DAG se declara de forma estática y lo ejecuta un scheduler central; los datos entre tareas
viajan por XCom (pequeños) → pasamos RUTAS a parquet/npz, nunca DataFrames.
Ramas: ShortCircuit si el lote no valida; BranchPython si no hay drift.
"""
from __future__ import annotations

import pendulum
from airflow.decorators import dag, task

DATA = "/opt/airflow/data"


@dag(schedule="17 3 * * *", start_date=pendulum.datetime(2024, 1, 1, tz="UTC"), catchup=False,
     default_args={"retries": 2, "retry_delay": pendulum.duration(minutes=5)}, tags=["cinematch", "ct"])
def cinematch_continuous_training():

    @task
    def ingest(ds: str | None = None) -> str:
        import pandas as pd
        df = pd.read_parquet(f"{DATA}/events/date={ds}")
        path = f"{DATA}/staging/{ds}.parquet"
        df.to_parquet(path)
        return path

    @task.short_circuit
    def validate(path: str) -> bool:                # False → se saltan todas las tareas aguas abajo
        import pandas as pd
        from validation_schema import validate_interactions
        ok, _ = validate_interactions(pd.read_parquet(path))
        return ok

    @task.branch
    def drift_gate(path: str) -> str:
        import pandas as pd
        import cinematch_ml as ml
        from evidently_job import drift_metrics, push_metrics
        champ, _ = ml.load_champion("cinematch-retrieval")
        m = drift_metrics(champ, pd.read_parquet(path), pd.read_parquet(f"{DATA}/reference/last_week.parquet"))
        push_metrics(m)
        return "train_and_register" if (m["oov"] > 0.10 or m["js_genre"] > 0.02 or m["emb_auc"] > 0.65) else "skip"

    @task
    def train_and_register(path: str) -> int:
        import mlflow
        import pandas as pd
        import cinematch_ml as ml
        mlflow.set_tracking_uri("http://mlflow:5000")
        hist = pd.read_parquet(f"{DATA}/history/last_3y.parquet")
        champ, _ = ml.load_champion("cinematch-retrieval")
        cand = ml.train_als(hist, init=champ)
        holdout = pd.read_parquet(path)
        v = ml.register_model(cand, "cinematch-retrieval", {"source": "airflow"},
                              {"ndcg_ch": ml.evaluate(cand, holdout), "ndcg_cp": ml.evaluate(champ, holdout)})
        mlflow.tracking.MlflowClient().set_registered_model_alias("cinematch-retrieval", "challenger", v)
        return v

    @task
    def skip() -> None:
        print("Sin drift: no se reentrena")

    p = ingest()
    gate = drift_gate(p)
    validate(p) >> gate
    gate >> [train_and_register(p), skip()]


cinematch_continuous_training()
