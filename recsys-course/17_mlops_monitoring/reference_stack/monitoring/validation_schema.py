"""Contratos de datos de las interacciones de CineMatch.

- Pandera: esquema como código, rápido, ideal para CI y para el flow.
- Great Expectations (GX ≥ 1.0): suite equivalente con data docs (ver `gx_suite()`).
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

try:
    import pandera.pandas as pa
except ImportError:  # pandera < 0.24
    import pandera as pa
from pandera import Check

RATINGS = list(np.arange(0.5, 5.01, 0.5))


def interactions_schema(now: int | None = None) -> pa.DataFrameSchema:
    now = now or int(time.time()) + 86400
    return pa.DataFrameSchema(
        {
            "user_id": pa.Column(int, Check.ge(1), nullable=False),
            "item_id": pa.Column(int, Check.ge(1), nullable=False),
            "rating": pa.Column(float, Check.isin(RATINGS), nullable=False),
            "ts": pa.Column(int, [Check.gt(788_918_400), Check.le(now)], nullable=False),
        },
        checks=[
            Check(lambda d: d.duplicated(["user_id", "item_id", "ts"]).mean() <= 0.01, error="duplicados > 1 %"),
            Check(lambda d: len(d) >= 1000, error="volumen anómalo (< 1000 eventos/día)"),
        ],
        coerce=True,
    )


def validate_interactions(df: pd.DataFrame) -> tuple[bool, pd.DataFrame | None]:
    try:
        interactions_schema().validate(df, lazy=True)
        return True, None
    except pa.errors.SchemaErrors as e:
        return False, e.failure_cases[["column", "check", "failure_case"]].drop_duplicates(["column", "check"])


def gx_suite(df: pd.DataFrame):
    """Misma validación con Great Expectations 1.x (API fluida)."""
    import great_expectations as gx

    ctx = gx.get_context(mode="ephemeral")
    batch_def = (ctx.data_sources.add_pandas("cinematch")
                 .add_dataframe_asset("interactions")
                 .add_batch_definition_whole_dataframe("daily"))
    suite = ctx.suites.add(gx.ExpectationSuite(name="interactions"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="user_id"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(column="rating", value_set=RATINGS))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(column="ts", min_value=788_918_400))
    suite.add_expectation(gx.expectations.ExpectCompoundColumnsToBeUnique(column_list=["user_id", "item_id", "ts"]))
    return batch_def.get_batch(batch_parameters={"dataframe": df}).validate(suite)
