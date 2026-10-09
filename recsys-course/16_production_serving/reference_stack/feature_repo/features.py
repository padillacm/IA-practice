"""Definiciones de features de CineMatch (fuente única de verdad para entrenamiento y serving).

feast apply                                   # registra entidades y feature views
feast materialize-incremental $(date -u +%Y-%m-%dT%H:%M:%S)   # offline → online (cron/Airflow cada hora)
"""
from datetime import timedelta

from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float32, Int64
from feast.value_type import ValueType

item = Entity(name="item", join_keys=["item_id"], value_type=ValueType.INT64, description="Título del catálogo")
user = Entity(name="user", join_keys=["user_id"], value_type=ValueType.INT64, description="Perfil de CineMatch")

# Snapshots diarios publicados al día siguiente: event_timestamp = momento en que el valor EXISTE (no el del cálculo).
item_stats_src = FileSource(path="data/item_stats.parquet", timestamp_field="event_timestamp")
user_stats_src = FileSource(path="data/user_stats.parquet", timestamp_field="event_timestamp")

item_stats = FeatureView(
    name="item_stats",
    entities=[item],
    ttl=timedelta(days=30),           # si un ítem no se actualiza en 30 días, su valor se considera caducado
    schema=[Field(name="pop_cum", dtype=Int64), Field(name="rating_mean_cum", dtype=Float32)],
    source=item_stats_src,
    online=True,
    tags={"owner": "recsys-platform", "freshness_slo": "24h"},
)

user_stats = FeatureView(
    name="user_stats",
    entities=[user],
    ttl=timedelta(days=90),
    schema=[Field(name="user_n", dtype=Int64), Field(name="user_mean", dtype=Float32)],
    source=user_stats_src,
    online=True,
    tags={"owner": "recsys-platform", "freshness_slo": "24h"},
)
