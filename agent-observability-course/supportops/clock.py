"""Reloj simulado (tiempo virtual) y generador de aleatoriedad estable.

Todas las latencias del laboratorio son *simuladas*: el agente avanza un ``SimClock`` en lugar de dormir. Así las
trazas tienen duraciones realistas y **deterministas** aunque el notebook se ejecute en milisegundos.
"""
from __future__ import annotations

import hashlib
import random
import time

# 2026-09-01T09:00:00Z : origen del tiempo simulado por defecto
SIM_EPOCH_S = 1_788_253_200.0


def stable_rng(*keys: object) -> random.Random:
    """RNG determinista a partir de una clave (p. ej. semilla + ticket_id + paso).

    Usar ``hash()`` de Python no sirve (cambia entre procesos); aquí se usa SHA-256.
    """
    digest = hashlib.sha256("|".join(str(k) for k in keys).encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def stable_hex(n_hex: int, *keys: object) -> str:
    """Identificador hexadecimal determinista (para trace_id/span_id de datos pregrabados)."""
    return hashlib.sha256("|".join(str(k) for k in keys).encode()).hexdigest()[:n_hex]


class SimClock:
    """Reloj virtual. ``advance(s)`` suma segundos simulados; ``sleep_scale`` > 0 duerme de verdad ``s*sleep_scale``.

    >>> c = SimClock(start_s=1000.0); c.advance(0.5); round(c.now_s() - 1000, 3)
    0.5
    """

    def __init__(self, start_s: float = SIM_EPOCH_S, sleep_scale: float = 0.0):
        self._t = float(start_s)
        self.start_s = float(start_s)
        self.sleep_scale = float(sleep_scale)

    def now_s(self) -> float:
        return self._t

    def now_ns(self) -> int:
        return int(round(self._t * 1e9))

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("no se puede retroceder el reloj")
        self._t += seconds
        if self.sleep_scale > 0:
            time.sleep(seconds * self.sleep_scale)

    @property
    def elapsed_s(self) -> float:
        return self._t - self.start_s
