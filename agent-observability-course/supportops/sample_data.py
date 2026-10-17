"""Datos pregrabados (MODO DEGRADADO) y su generador. Mismo esquema que el tráfico/telemetría generados en vivo.

Los ficheros viven en ``supportops/data/`` (JSON Lines) y se regeneran con::

    python -m supportops.sample_data          # semilla 42, 240 tickets, 2 incidentes

Contenido: tickets.jsonl · runs.jsonl · spans.jsonl · logs.jsonl · metrics_1m.jsonl · meta.json
"""
from __future__ import annotations

import json
import pathlib
import statistics
from typing import Any

from .agent import SupportAgent
from .clock import SIM_EPOCH_S
from .llm import MockLLM
from .recording import RecordingInstrumentor
from .traffic import DEFAULT_FAULT_RATES, Incident, generate_tickets, run_tickets, to_rows

DATA_DIR = pathlib.Path(__file__).resolve().parent / "data"
SAMPLE_SEED = 42
SAMPLE_N = 240
SAMPLE_INCIDENTS = [
    Incident("llm_provider_degraded", "llm_error", 1200, 1800, prob=0.7, params={"status": 503, "persistent": True}),
    Incident("tools_slow", "latency_spike", 2400, 2900, prob=0.8, params={"factor": 8.0, "target": "tool"}),
]


def _read(name: str) -> list[dict[str, Any]]:
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"{path} no existe: ejecuta `python -m supportops.sample_data`")
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_tickets() -> list[dict[str, Any]]: return _read("tickets.jsonl")
def load_runs() -> list[dict[str, Any]]: return _read("runs.jsonl")
def load_spans() -> list[dict[str, Any]]: return _read("spans.jsonl")
def load_logs() -> list[dict[str, Any]]: return _read("logs.jsonl")
def load_metrics_1m() -> list[dict[str, Any]]: return _read("metrics_1m.jsonl")


def load_meta() -> dict[str, Any]:
    return json.loads((DATA_DIR / "meta.json").read_text(encoding="utf-8"))


def _pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else 0.0


def metrics_1m(rows: list[dict[str, Any]], start_s: float = SIM_EPOCH_S) -> list[dict[str, Any]]:
    by_min: dict[int, list[dict[str, Any]]] = {}
    for r in rows:
        by_min.setdefault(int((r["created_at"] - start_s) // 60), []).append(r)
    out = []
    for m in range(0, max(by_min) + 1):
        rs = by_min.get(m, [])
        lat = [r["latency_s"] for r in rs]
        out.append({"minute": m, "requests": len(rs), "errors": sum(r["status"] in ("error", "max_steps") for r in rs),
                    "p50_latency_s": round(_pct(lat, 0.5), 3), "p95_latency_s": round(_pct(lat, 0.95), 3),
                    "input_tokens": sum(r["input_tokens"] for r in rs), "output_tokens": sum(r["output_tokens"] for r in rs),
                    "cost_usd": round(sum(r["cost_usd"] for r in rs), 6)})
    return out


def generate(out_dir: pathlib.Path = DATA_DIR, seed: int = SAMPLE_SEED, n: int = SAMPLE_N) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    tickets = generate_tickets(n, seed, fault_rates=DEFAULT_FAULT_RATES, incidents=SAMPLE_INCIDENTS)
    rec = RecordingInstrumentor()
    agent = SupportAgent(llm=MockLLM(seed=seed), instrumentor=rec)
    results = run_tickets(agent, tickets)
    rows = to_rows(tickets, results)

    def dump(name: str, items: list[dict[str, Any]]) -> None:
        with (out_dir / name).open("w", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False, separators=(",", ":")) + "\n")

    dump("tickets.jsonl", [t.to_dict() for t in tickets])
    dump("runs.jsonl", rows)
    dump("spans.jsonl", rec.spans)
    dump("logs.jsonl", rec.logs)
    mets = metrics_1m(rows)
    dump("metrics_1m.jsonl", mets)
    meta = {"seed": seed, "n_tickets": n, "provider": "mock", "model": "mock-small", "start_unix_s": SIM_EPOCH_S,
            "incidents": [vars(i) for i in SAMPLE_INCIDENTS], "fault_rates": DEFAULT_FAULT_RATES,
            "n_spans": len(rec.spans), "n_logs": len(rec.logs),
            "median_latency_s": round(statistics.median(r["latency_s"] for r in rows), 3)}
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2, ensure_ascii=False))
