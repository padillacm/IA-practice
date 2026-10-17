"""Precios SIMULADOS (USD por millón de tokens) para el modelo mock. No son precios reales de ningún proveedor.

Para costes reales consulta la página de precios de tu proveedor: cambian con frecuencia.
"""
from __future__ import annotations

MOCK_PRICES_USD_PER_MTOK: dict[str, tuple[float, float]] = {
    # modelo: (entrada, salida)
    "mock-small": (0.25, 1.25),
    "mock-large": (3.00, 15.00),
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = MOCK_PRICES_USD_PER_MTOK.get(model, (0.0, 0.0))
    return (input_tokens * pin + output_tokens * pout) / 1_000_000
