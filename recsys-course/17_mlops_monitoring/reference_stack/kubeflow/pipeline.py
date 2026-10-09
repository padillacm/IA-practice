"""Pipeline de CT con Kubeflow Pipelines (KFP v2 SDK).  python pipeline.py → cinematch_ct.yaml (subir a KFP)

Cada componente corre en su propio contenedor: aislamiento de dependencias, GPUs por paso y caché de pasos.
Los datos entre pasos viajan como artefactos (Dataset/Model) en el object store del clúster.
"""
from kfp import compiler, dsl
from kfp.dsl import Dataset, Input, Model, Output

IMAGE = "ghcr.io/cinematch/ml:1.4.0"   # imagen con cinematch_ml.py, validation_schema.py, evidently_job.py


@dsl.component(base_image=IMAGE)
def validate(events_uri: str, valid_out: Output[Dataset]) -> bool:
    import pandas as pd
    from validation_schema import validate_interactions
    df = pd.read_parquet(events_uri)
    ok, _ = validate_interactions(df)
    df.to_parquet(valid_out.path)
    return ok


@dsl.component(base_image=IMAGE)
def train(history_uri: str, model_out: Output[Model]):
    import numpy as np
    import pandas as pd
    import cinematch_ml as ml
    m = ml.train_als(pd.read_parquet(history_uri))
    np.savez(model_out.path, **m)


@dsl.component(base_image=IMAGE)
def evaluate_and_register(model_in: Input[Model], holdout: Input[Dataset], mlflow_uri: str) -> float:
    import mlflow
    import numpy as np
    import pandas as pd
    import cinematch_ml as ml
    mlflow.set_tracking_uri(mlflow_uri)
    z = np.load(model_in.path + ".npz" if not model_in.path.endswith(".npz") else model_in.path)
    m = {k: z[k] for k in z.files}
    nd = ml.evaluate(m, pd.read_parquet(holdout.path))
    ml.register_model(m, "cinematch-retrieval", {"source": "kfp"}, {"ndcg_holdout": nd})
    return nd


@dsl.pipeline(name="cinematch-ct")
def cinematch_ct(events_uri: str, history_uri: str, mlflow_uri: str = "http://mlflow.mlops:5000"):
    v = validate(events_uri=events_uri)
    with dsl.If(v.outputs["Output"] == True):  # noqa: E712  (sintaxis de condiciones de KFP)
        t = train(history_uri=history_uri).set_cpu_limit("8").set_memory_limit("32G")
        evaluate_and_register(model_in=t.outputs["model_out"], holdout=v.outputs["valid_out"], mlflow_uri=mlflow_uri)


if __name__ == "__main__":
    compiler.Compiler().compile(cinematch_ct, "cinematch_ct.yaml")
