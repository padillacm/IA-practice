"""Pipeline de CT con Metaflow (creado en Netflix).   python ct_flow.py run --run_date 2024-06-01

Cada `self.x` asignado en un step se versiona automáticamente como artefacto (se puede inspeccionar después con
`Flow('CineMatchCT').latest_run`). Con `@batch`/`@kubernetes` + `@resources` el mismo flow corre en la nube, y con
`python ct_flow.py argo-workflows create` (o `step-functions create`) se programa en producción.
"""
from metaflow import FlowSpec, Parameter, current, resources, step


class CineMatchCT(FlowSpec):
    run_date = Parameter("run_date", help="Fecha de corte (YYYY-MM-DD)")
    window_days = Parameter("window_days", default=3 * 365)

    @step
    def start(self):
        import pandas as pd
        self.batch = pd.read_parquet(f"data/events/date={self.run_date}")
        self.next(self.validate)

    @step
    def validate(self):
        from validation_schema import validate_interactions
        self.valid, _ = validate_interactions(self.batch)
        self.next(self.drift)

    @step
    def drift(self):
        import pandas as pd
        import cinematch_ml as ml
        from evidently_job import drift_metrics
        self.champion, self.v_champ = ml.load_champion("cinematch-retrieval")
        self.metrics = drift_metrics(self.champion, self.batch, pd.read_parquet("data/reference/last_week.parquet"))
        self.retrain = self.valid and (self.metrics["oov"] > 0.10 or self.metrics["emb_auc"] > 0.65)
        self.next(self.train)

    @resources(memory=16000, cpu=8)
    @step
    def train(self):
        import pandas as pd
        import cinematch_ml as ml
        if self.retrain:
            hist = pd.read_parquet("data/history/last_3y.parquet")
            self.challenger = ml.train_als(hist, init=self.champion)
            self.ndcg_ch = ml.evaluate(self.challenger, self.batch)
            self.ndcg_cp = ml.evaluate(self.champion, self.batch)
        self.next(self.end)

    @step
    def end(self):
        if self.retrain and self.ndcg_ch >= self.ndcg_cp:
            import cinematch_ml as ml
            v = ml.register_model(self.challenger, "cinematch-retrieval", {"metaflow_run": current.run_id},
                                  {"ndcg_ch": self.ndcg_ch, "ndcg_cp": self.ndcg_cp})
            print(f"Challenger registrado: v{v}")


if __name__ == "__main__":
    CineMatchCT()
