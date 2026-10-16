"""Calidad y regresión (módulo 15): variantes de prompt, datasets desde trazas, comparativas A/B, drift y canarios.

* ``PromptVariantLLM``: versiones del prompt de sistema SIMULADAS sobre el mock. ``v2`` es la «regresión silenciosa»: un cambio de
  redacción bienintencionado («sé conciso, no consultes herramientas si no es imprescindible») que hace que el modelo conteste sin
  consultar y se invente datos en una fracción de los tickets. Es una simulación determinista, no un modelo real.
* ``GoldenCase`` / ``select_golden`` / ``replay`` / ``ReleaseGate``: dataset de regresión construido desde trazas + compuerta de release.
* Estadística de comparación: ``two_proportion_test``, ``mcnemar_exact``, ``required_n_per_arm``, ``bootstrap_diff``.
* Drift: ``psi``, ``psi_categorical``, ``js_divergence``, ``ks_2samp``, ``Cusum``, ``behavior_fingerprint``.
* Canarios: ``canary_route``, ``sprt_bernoulli``, ``peeking_false_positive_rate``.
* Solo telemetría: ``trace_shapes``, ``version_report`` (a partir de spans con el esquema ``SPAN_SCHEMA`` y eventos de evaluación).
"""
from __future__ import annotations

import dataclasses
import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

from .clock import SIM_EPOCH_S, stable_hex, stable_rng
from .faults import _fabricate
from .llm.mock import MockLLM, ORDER_RE
from .models import LLMResponse, Ticket, Usage
from .quality_eval import CaseCollector, EvalCase, MockJudge, Verdict, confusion, scrub_pii, wilson_interval

# =====================================================================================================================
# Variantes de prompt (simuladas)
# =====================================================================================================================
PROMPT_VERSIONS: dict[str, dict[str, Any]] = {
    "v1": {"desc": "Línea base: usa las herramientas y no inventes datos.", "skip_tools": 0.0, "terse": False},
    "v2": {"desc": "«Sé conciso. Responde directamente; consulta herramientas solo si es imprescindible.»", "skip_tools": 0.22, "terse": True},
    "v2.1": {"desc": "Hotfix: v2 + «para pedidos y reembolsos consulta SIEMPRE la herramienta».", "skip_tools": 0.04, "terse": True},
}
TOOL_INTENT_WORDS = ("pedido", "envío", "envio", "seguimiento", "tracking", "reembols", "devol", "dinero", "estado", "stock", "garantía", "politica", "política")


class PromptVariantLLM:
    """Envoltorio del LLM que simula el efecto de una versión de prompt. En ``v2`` una fracción ``skip_tools`` de los tickets que
    necesitarían una herramienta reciben una respuesta INMEDIATA inventada (sin herramienta). El resto del comportamiento es el
    del mock. Marca las respuestas inventadas con ``meta["fault"]="prompt_regression"`` (ground truth para medir detectores)."""

    def __init__(self, inner: Any | None = None, version: str = "v1", seed: int = 42):
        if version not in PROMPT_VERSIONS:
            raise ValueError(f"versión desconocida {version}; usa {list(PROMPT_VERSIONS)}")
        self.inner = inner or MockLLM()
        self.version, self.seed, self.cfg = version, seed, PROMPT_VERSIONS[version]
        self.provider, self.model = self.inner.provider, self.inner.model
        self.regressed: set[str] = set()

    def chat(self, messages, tools=None, **kw) -> LLMResponse:
        resp = self.inner.chat(messages, tools, **kw)
        key = kw.get("call_key", ("", 0))
        p = float(self.cfg["skip_tools"])
        if p > 0 and key[1] == 0 and resp.tool_calls:
            if stable_rng("prompt-variant", self.seed, self.version, key[0]).random() < p:
                text = next((m.content for m in messages if m.role == "user"), "")
                out = _fabricate(text)
                self.regressed.add(key[0])
                return dataclasses.replace(resp, content=out, tool_calls=[], finish_reason="stop",
                                           usage=Usage(resp.usage.input_tokens, max(8, len(out) // 4)),
                                           latency_s=round(resp.latency_s * 0.8, 4), meta={**resp.meta, "fault": "prompt_regression"})
        return resp


def make_agent(version: str = "v1", *, model: str = "mock-small", seed: int = 42, instrumentors: Sequence[Any] = (), collector: CaseCollector | None = None):
    """Agente SupportOps con la versión de prompt indicada. Devuelve ``(agent, collector)``; el colector (versión etiquetada) va el último."""
    from .agent import SupportAgent
    from .instrument import CompositeInstrumentor
    col = collector or CaseCollector(version=version)
    llm = PromptVariantLLM(MockLLM(model, seed=seed), version, seed)
    items = [*instrumentors, col]
    agent = SupportAgent(llm=llm, instrumentor=CompositeInstrumentor(*items) if len(items) > 1 else items[0])
    agent.variant_llm = llm                      # type: ignore[attr-defined]
    return agent, col


def run_version(version: str, tickets: Sequence[Ticket], *, model: str = "mock-small", seed: int = 42, instrumentors: Sequence[Any] = ()):
    """Ejecuta ``tickets`` con una versión; devuelve ``(results, cases)`` con ``truth`` completo (incluida la regresión del prompt)."""
    agent, col = make_agent(version, model=model, seed=seed, instrumentors=instrumentors)
    results = [agent.run(t) for t in tickets]
    return results, col.cases


# =====================================================================================================================
# Estadística de comparación
# =====================================================================================================================
def _phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _phi_inv(p: float) -> float:
    """Inversa de la normal estándar (Acklam, error < 1.2e-9)."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    if p < 0.02425:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > 1 - 0.02425:
        return -_phi_inv(1 - p)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def two_proportion_test(k1: int, n1: int, k2: int, n2: int) -> dict[str, float]:
    """Prueba z de dos proporciones (grupo 1 vs grupo 2). ``diff = p2 − p1``; IC 95 % de Wald de la diferencia."""
    p1, p2 = k1 / n1, k2 / n2
    pp = (k1 + k2) / (n1 + n2)
    se0 = math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2)) or 1e-12
    z = (p2 - p1) / se0
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    d = p2 - p1
    return {"p1": p1, "p2": p2, "diff": d, "z": z, "p_value": 2 * (1 - _phi(abs(z))), "ci_low": d - 1.96 * se, "ci_high": d + 1.96 * se}


def mcnemar_exact(b: int, c: int) -> float:
    """p-valor exacto (binomial bilateral) de McNemar para datos APAREADOS: ``b`` = bien→mal, ``c`` = mal→bien."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def required_n_per_arm(p0: float, p1: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """n por grupo para detectar el paso de ``p0`` a ``p1`` con una prueba z bilateral de dos proporciones."""
    za, zb = _phi_inv(1 - alpha / 2), _phi_inv(power)
    pbar = (p0 + p1) / 2
    num = (za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(p0 * (1 - p0) + p1 * (1 - p1))) ** 2
    return math.ceil(num / (p0 - p1) ** 2)


def min_detectable_drop(n_per_arm: int, p0: float, alpha: float = 0.05, power: float = 0.8) -> float:
    """Caída mínima detectable (aprox.) con ``n`` por grupo partiendo de una tasa ``p0``."""
    z = _phi_inv(1 - alpha / 2) + _phi_inv(power)
    return z * math.sqrt(2 * p0 * (1 - p0) / n_per_arm)


def bootstrap_diff(a: Sequence[float], b: Sequence[float], n_boot: int = 2000, seed: int = 42, paired: bool = False) -> tuple[float, float, float]:
    """Diferencia de medias ``mean(b) − mean(a)`` con IC 95 % por *bootstrap* percentil (apareado si ``paired``)."""
    rng = stable_rng("bootstrap", seed)
    na, nb = len(a), len(b)
    diffs = []
    for _ in range(n_boot):
        if paired:
            idx = [rng.randrange(na) for _ in range(na)]
            diffs.append(sum(b[i] - a[i] for i in idx) / na)
        else:
            diffs.append(sum(b[rng.randrange(nb)] for _ in range(nb)) / nb - sum(a[rng.randrange(na)] for _ in range(na)) / na)
    diffs.sort()
    point = sum(b) / nb - sum(a) / na
    return point, diffs[int(0.025 * n_boot)], diffs[int(0.975 * n_boot) - 1]


# =====================================================================================================================
# Dataset de regresión desde trazas
# =====================================================================================================================
@dataclass
class GoldenCase:
    case_id: str
    question: str
    reason: str                         # por qué entró: judge_fail | thumbs_down | error | escalated | random_pass
    source_trace_id: str
    source_ticket_id: str
    expected_tools: list[str]           # trayectoria esperada (herramientas de la traza aceptada)
    must_not: list[str] = field(default_factory=list)   # p. ej. ["pii", "fabricated_claim"]
    weight: float = 1.0                 # cuántos tickets de producción representa (para re-ponderar)


def normalize_question(text: str) -> str:
    """Clave de deduplicación: minúsculas, sin ids de pedido, sin PII ni espacios extra."""
    from .quality_eval import scrub_pii
    t = scrub_pii(text.lower())
    t = re.sub(r"ord-\d{5}", "ORD", t)
    return re.sub(r"\s+", " ", re.sub(r"mi correo es.*$", "", t)).strip()


def select_golden(cases: Sequence[EvalCase], verdicts: Mapping[str, Verdict], feedback: Mapping[str, int] | None = None, *,
                  n_total: int = 60, seed: int = 42, tools_by_ticket: Mapping[str, list[str]] | None = None) -> list[GoldenCase]:
    """Construye el dataset de regresión desde trazas: primero los casos que FALLARON (juez/feedback/error), luego escalados y una
    muestra aleatoria de los que salieron bien; deduplica por pregunta normalizada y scrub de PII. Peso = nº de tickets que
    representa cada caso. Solo usa lo que está en telemetría (juez, feedback, estado, herramientas de la traza)."""
    feedback = feedback or {}
    rng = stable_rng("golden", seed)
    buckets: dict[str, list[EvalCase]] = {"thumbs_down": [], "judge_fail": [], "error": [], "escalated": [], "random_pass": []}
    for c in cases:
        v = verdicts.get(c.ticket_id)
        if feedback.get(c.ticket_id, 0) < 0:
            buckets["thumbs_down"].append(c)
        elif v is not None and not v.passed:
            buckets["judge_fail"].append(c)
        elif c.status in ("error", "max_steps", "degraded"):
            buckets["error"].append(c)
        elif c.status == "escalated":
            buckets["escalated"].append(c)
        elif v is not None:
            buckets["random_pass"].append(c)
    out: list[GoldenCase] = []
    seen: dict[str, GoldenCase] = {}
    quota = {"thumbs_down": n_total, "judge_fail": n_total, "error": max(n_total // 6, 4), "escalated": max(n_total // 6, 4), "random_pass": n_total}
    for reason in ("thumbs_down", "judge_fail", "error", "escalated", "random_pass"):
        pool = buckets[reason]
        rng.shuffle(pool)
        for c in pool:
            if len(out) >= n_total or quota[reason] <= 0:
                break
            key = normalize_question(c.question)
            if key in seen:
                seen[key].weight += 1
                continue
            quota[reason] -= 1
            tools = list(tools_by_ticket.get(c.ticket_id, [])) if tools_by_ticket else []
            g = GoldenCase(f"G-{len(out) + 1:03d}", re.sub(r"\s*Mi correo es.*$", "", scrub_pii(c.question)),
                           reason, c.trace_id, c.ticket_id, tools, must_not=["pii", "fabricated_claim"])
            seen[key] = g
            out.append(g)
    return out


def golden_to_tickets(golden: Sequence[GoldenCase], source: Mapping[str, Ticket]) -> list[Ticket]:
    """Reconstruye tickets ejecutables desde el dataset (usa el ticket original para ids de pedido; sin faults inyectados)."""
    out = []
    for g in golden:
        t = source[g.source_ticket_id]
        out.append(dataclasses.replace(t, ticket_id=f"{g.case_id}", faults=[], incident=None, contains_pii=False,
                                       text=re.sub(r"\s*Mi correo es.*$", "", t.text)))
    return out


def trajectory_match(expected: Sequence[str], actual: Sequence[str]) -> bool:
    """Coincidencia de trayectoria: las herramientas esperadas aparecen, en orden, como subsecuencia de las usadas."""
    it = iter(actual)
    return all(any(e == a for a in it) for e in expected)


def replay(golden: Sequence[GoldenCase], tickets: Sequence[Ticket], version: str, judge: Any | None = None, *, model: str = "mock-small") -> list[dict[str, Any]]:
    """Repite el dataset con una versión del agente: una fila por caso con veredicto, trayectoria, coste y latencia."""
    judge = judge or MockJudge()
    results, cases = run_version(version, tickets, model=model)
    rows = []
    for g, r, c in zip(golden, results, cases):
        v = judge.evaluate(c)
        rows.append({"case_id": g.case_id, "reason": g.reason, "weight": g.weight, "version": version, "passed": v.passed,
                     "groundedness": v.scores["groundedness"].value, "relevance": v.scores["relevance"].value,
                     "trajectory_ok": trajectory_match(g.expected_tools, r.tools_used), "tools": ",".join(r.tools_used), "status": r.status,
                     "cost_usd": r.cost_usd, "latency_s": r.latency_s, "n_llm_calls": r.n_llm_calls, "truth_bad": c.truth_bad})
    return rows


@dataclass
class ReleaseGate:
    """Compuerta de release: la candidata debe NO empeorar la calidad más que ``margin`` (no inferioridad) y respetar los
    guardarraíles de coste y latencia. Devuelve (decisión, motivos)."""
    quality_margin: float = 0.03
    max_cost_ratio: float = 1.25
    max_latency_ratio: float = 1.25
    min_trajectory: float = 0.90

    def decide(self, base: Sequence[Mapping[str, Any]], cand: Sequence[Mapping[str, Any]]) -> tuple[str, list[str]]:
        def mean(rows, k):
            return sum(float(r[k]) for r in rows) / len(rows)
        reasons = []
        q0, q1 = mean(base, "passed"), mean(cand, "passed")
        k0, k1 = sum(bool(r["passed"]) for r in base), sum(bool(r["passed"]) for r in cand)
        t = two_proportion_test(k0, len(base), k1, len(cand))
        if t["ci_high"] < -self.quality_margin or (q1 < q0 - self.quality_margin and t["p_value"] < 0.05):
            reasons.append(f"calidad {q0:.1%} → {q1:.1%} (IC95 de la diferencia [{t['ci_low']:+.1%}, {t['ci_high']:+.1%}])")
        if mean(cand, "trajectory_ok") < self.min_trajectory:
            reasons.append(f"trayectoria correcta {mean(cand, 'trajectory_ok'):.1%} < {self.min_trajectory:.0%}")
        if mean(cand, "cost_usd") > self.max_cost_ratio * mean(base, "cost_usd"):
            reasons.append("coste por caso por encima del guardarraíl")
        if mean(cand, "latency_s") > self.max_latency_ratio * mean(base, "latency_s"):
            reasons.append("latencia por encima del guardarraíl")
        return ("block" if reasons else "ship"), reasons


# =====================================================================================================================
# Drift
# =====================================================================================================================
def psi(expected: Sequence[float], actual: Sequence[float], bins: int = 10, eps: float = 1e-4) -> float:
    """Population Stability Index con cuantiles de la referencia como cortes. Convención habitual: <0,1 estable · 0,1–0,25 moderado · >0,25 grande."""
    xs = sorted(expected)
    edges = [xs[min(len(xs) - 1, int(len(xs) * i / bins))] for i in range(1, bins)]
    def hist(v):
        c = [0] * bins
        for x in v:
            c[sum(x > e for e in edges)] += 1
        return [max(k / len(v), eps) for k in c]
    e, a = hist(expected), hist(actual)
    return sum((ai - ei) * math.log(ai / ei) for ei, ai in zip(e, a))


def psi_categorical(expected: Mapping[str, float], actual: Mapping[str, float], eps: float = 1e-4) -> float:
    keys = set(expected) | set(actual)
    se, sa = sum(expected.values()) or 1, sum(actual.values()) or 1
    return sum((max(actual.get(k, 0) / sa, eps) - max(expected.get(k, 0) / se, eps)) * math.log(max(actual.get(k, 0) / sa, eps) / max(expected.get(k, 0) / se, eps)) for k in keys)


def js_divergence(p: Mapping[str, float], q: Mapping[str, float]) -> float:
    """Divergencia de Jensen–Shannon (base 2, acotada en [0,1]) entre dos distribuciones categóricas."""
    keys = set(p) | set(q)
    sp, sq = sum(p.values()) or 1, sum(q.values()) or 1
    P = {k: p.get(k, 0) / sp for k in keys}
    Q = {k: q.get(k, 0) / sq for k in keys}
    M = {k: (P[k] + Q[k]) / 2 for k in keys}
    def kl(a, b):
        return sum(a[k] * math.log2(a[k] / b[k]) for k in keys if a[k] > 0)
    return 0.5 * kl(P, M) + 0.5 * kl(Q, M)


def ks_2samp(x: Sequence[float], y: Sequence[float]) -> tuple[float, float]:
    """Estadístico KS de dos muestras y p-valor asintótico."""
    xs, ys = sorted(x), sorted(y)
    i = j = 0
    d = 0.0
    while i < len(xs) and j < len(ys):
        v = min(xs[i], ys[j])
        while i < len(xs) and xs[i] <= v:
            i += 1
        while j < len(ys) and ys[j] <= v:
            j += 1
        d = max(d, abs(i / len(xs) - j / len(ys)))
    en = math.sqrt(len(xs) * len(ys) / (len(xs) + len(ys)))
    lam = (en + 0.12 + 0.11 / en) * d
    p = 2 * sum((-1) ** (k - 1) * math.exp(-2 * k * k * lam * lam) for k in range(1, 101))
    return d, max(0.0, min(1.0, p))


class Cusum:
    """CUSUM unilateral para detectar una CAÍDA de una tasa (calidad) respecto a ``target``: ``S_t = max(0, S_{t-1} + (target − x_t) − k)``;
    alerta si ``S_t > h``. ``k`` = holgura (≈ mitad de la caída que quieres detectar) y ``h`` el umbral."""

    def __init__(self, target: float, k: float = 0.02, h: float = 0.25):
        self.target, self.k, self.h, self.s = target, k, h, 0.0

    def update(self, x: float) -> bool:
        self.s = max(0.0, self.s + (self.target - x) - self.k)
        return self.s > self.h

    def first_alarm(self, series: Iterable[float]) -> int | None:
        self.s = 0.0
        for i, x in enumerate(series):
            if self.update(x):
                return i
        return None


def behavior_fingerprint(rows: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    """Huella de comportamiento de una versión a partir de filas por ticket (``n_llm_calls``, ``n_tool_calls``, ``status``, tokens,
    longitud de la respuesta, coste, latencia). Sirve para comparar versiones SIN juez."""
    n = len(rows)
    def m(k):
        return sum(float(r[k]) for r in rows) / n
    return {"n": n, "llm_calls": m("n_llm_calls"), "tool_calls": m("n_tool_calls"), "no_tool_rate": sum(int(r["n_tool_calls"]) == 0 for r in rows) / n,
            "output_tokens": m("output_tokens"), "input_tokens": m("input_tokens"), "cost_usd": m("cost_usd"), "latency_s": m("latency_s"),
            "error_rate": sum(r["status"] in ("error", "max_steps") for r in rows) / n}


# =====================================================================================================================
# Canarios
# =====================================================================================================================
def canary_route(ticket_id: str, fraction: float = 0.1, salt: str = "canary") -> str:
    """Enrutado determinista por ticket: ``"canary"`` con probabilidad ``fraction`` (el mismo ticket siempre va al mismo lado)."""
    return "canary" if int(stable_hex(8, salt, ticket_id), 16) / 16 ** 8 < fraction else "stable"


def sprt_bernoulli(failures: int, n: int, p0: float, p1: float, alpha: float = 0.05, beta: float = 0.2) -> tuple[str, float]:
    """Prueba secuencial de Wald (SPRT) para una tasa de fallos: H0 ``p = p0`` (sana) vs H1 ``p = p1 > p0`` (regresión).
    Devuelve (``"rollback"`` | ``"promote"`` | ``"continue"``, log-razón de verosimilitud). Se puede mirar tras CADA petición sin
    inflar el error de tipo I (a diferencia de repetir un test de tamaño fijo)."""
    llr = failures * math.log(p1 / p0) + (n - failures) * math.log((1 - p1) / (1 - p0))
    upper, lower = math.log((1 - beta) / alpha), math.log(beta / (1 - alpha))
    return ("rollback" if llr >= upper else "promote" if llr <= lower else "continue"), llr


def peeking_false_positive_rate(p: float = 0.06, n_max: int = 600, looks: int = 20, trials: int = 400, seed: int = 42) -> dict[str, float]:
    """Simula comparar DOS grupos idénticos (misma tasa de fallo ``p``) mirando ``looks`` veces con una prueba z de tamaño fijo al 5 %:
    la tasa real de falsos positivos (si paras en el primer «significativo») y la del SPRT con los mismos datos."""
    rng = stable_rng("peeking", seed)
    fixed_fp = sprt_fp = 0
    marks = [int(n_max * (i + 1) / looks) for i in range(looks)]
    for _ in range(trials):
        a = [rng.random() < p for _ in range(n_max)]
        b = [rng.random() < p for _ in range(n_max)]
        hit = False
        for m in marks:
            ka, kb = sum(a[:m]), sum(b[:m])
            if (ka + kb) and abs(two_proportion_test(ka, m, kb, m)["z"]) > 1.96:
                hit = True
                break
        fixed_fp += hit
        s_hit = False
        fails = 0
        for i, x in enumerate(b, 1):
            fails += x
            if i % (n_max // looks) == 0 and sprt_bernoulli(fails, i, p, p * 2)[0] == "rollback":
                s_hit = True
                break
        sprt_fp += s_hit
    return {"fixed_sample_peeking": fixed_fp / trials, "sprt": sprt_fp / trials, "nominal": 0.05}


# =====================================================================================================================
# Drift de entrada: tickets con temas nuevos (fuera de la base de conocimiento)
# =====================================================================================================================
NOVEL_QUESTIONS = [
    "¿Tienen programa de reciclaje para hardware antiguo?", "¿Hacéis facturas a nombre de una empresa en Portugal?",
    "¿Puedo pagar con criptomonedas?", "¿Ofrecéis financiación a 24 meses sin intereses?", "¿Instaláis los componentes en tienda?",
    "¿Tenéis tienda física en Valencia?", "¿Hay descuento para estudiantes universitarios?", "¿Vendéis impresoras 3D?",
]


def novel_topic_tickets(n: int, seed: int = 7, start_s: float = SIM_EPOCH_S, duration_s: float = 600.0) -> list[Ticket]:
    """Tickets con preguntas de un tema que la base de conocimiento no cubre (deriva de la distribución de entrada)."""
    rng = stable_rng("novel", seed)
    out = []
    for i in range(n):
        out.append(Ticket(f"T-N{seed:02d}{i + 1:05d}", f"C-{rng.randrange(1, 200):04d}", "standard", "chat", rng.choice(NOVEL_QUESTIONS), "kb_question",
                          round(start_s + duration_s * (i + 0.5) / n, 3)))
    return out


# =====================================================================================================================
# Solo telemetría: formas de traza y comparativa de versiones
# =====================================================================================================================
def trace_shapes(spans: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Resume cada traza de ``supportops-agent`` a partir de sus spans: versión, nº de ``chat``, nº de ``execute_tool``, herramientas,
    estado, tokens/coste de las hojas ``chat``, duración del ``invoke_agent``. Es la «huella estructural» de un ticket."""
    out: dict[str, dict[str, Any]] = {}
    for s in spans:
        a = s.get("attributes", {})
        op = a.get("gen_ai.operation.name")
        if op is None:
            continue
        sh = out.setdefault(s["trace_id"], {"trace_id": s["trace_id"], "version": None, "n_chat": 0, "n_tool": 0, "tools": [], "status": None,
                                            "in_tok": 0, "out_tok": 0, "duration_s": None, "ticket": None, "intent": None, "tier": None,
                                            "root_span_id": None, "chat_span_ids": []})
        if op == "invoke_agent":
            sh["version"] = a.get("gen_ai.agent.version")
            sh["status"] = a.get("supportops.status")
            sh["duration_s"] = (s["end_unix_nano"] - s["start_unix_nano"]) / 1e9
            sh["ticket"], sh["intent"], sh["tier"] = a.get("supportops.ticket.id"), a.get("supportops.intent"), a.get("supportops.customer.tier")
            sh["root_span_id"] = s["span_id"]
        elif op == "chat":
            sh["n_chat"] += 1
            sh["in_tok"] += int(a.get("gen_ai.usage.input_tokens", 0) or 0)       # tokens SOLO de las hojas `chat`
            sh["out_tok"] += int(a.get("gen_ai.usage.output_tokens", 0) or 0)
            sh["chat_span_ids"].append(s["span_id"])
        elif op == "execute_tool":
            sh["n_tool"] += 1
            sh["tools"].append(a.get("gen_ai.tool.name"))
    return {k: v for k, v in out.items() if v["root_span_id"]}


def version_report(shapes: Mapping[str, Mapping[str, Any]], eval_events: Sequence[Mapping[str, Any]] = ()) -> list[dict[str, Any]]:
    """Tabla por versión desde telemetría: latencia/coste/errores (lo que mira un dashboard clásico), forma de traza y calidad
    (eventos ``gen_ai.evaluation.result`` agrupados por ``gen_ai.agent.version`` y criterio)."""
    from collections import defaultdict
    by_v: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for sh in shapes.values():
        by_v[sh["version"] or "?"].append(sh)
    qual: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for e in eval_events:
        a = e.get("attributes", {})
        k = (a.get("gen_ai.agent.version", "?"), a.get("gen_ai.evaluation.name", "?"))
        qual[k][1] += 1
        qual[k][0] += int(a.get("gen_ai.evaluation.score.label") == "pass")
    rows = []
    for v, shs in sorted(by_v.items()):
        n = len(shs)
        durs = sorted(s["duration_s"] for s in shs)
        row = {"version": v, "n": n, "p50_s": durs[n // 2], "p95_s": durs[min(n - 1, int(0.95 * n))], "error_rate": sum(s["status"] in ("error", "max_steps") for s in shs) / n,
               "chat_per_ticket": sum(s["n_chat"] for s in shs) / n, "tools_per_ticket": sum(s["n_tool"] for s in shs) / n,
               "no_tool_rate": sum(s["n_tool"] == 0 for s in shs) / n, "tokens_per_ticket": sum(s["in_tok"] + s["out_tok"] for s in shs) / n}
        for name in ("groundedness", "relevance", "resolution", "pii_safety"):
            k, m = qual.get((v, name), [0, 0])
            row[f"{name}_pass"] = k / m if m else float("nan")
            row[f"{name}_n"] = m
        rows.append(row)
    return rows


def event_records(tel: Any, name: str = "gen_ai.evaluation.result") -> list[dict[str, Any]]:
    """Eventos de log con ``event_name`` ``name`` guardados en memoria por un ``TelemetryHandle`` (``log_records()`` no expone el
    nombre del evento, por eso se lee del exportador en memoria). Incluye ``trace_id`` y ``span_id`` del span evaluado."""
    out = []
    for item in (tel._log_mem.get_finished_logs() if getattr(tel, "_log_mem", None) else []):
        r = getattr(item, "log_record", item)
        if getattr(r, "event_name", None) == name:
            tid, sid = r.trace_id, r.span_id
            out.append({"attributes": dict(r.attributes or {}), "trace_id": format(tid, "032x") if tid else None,
                        "span_id": format(sid, "016x") if sid else None, "time_unix_nano": r.timestamp, "body": r.body})
    return out


# =====================================================================================================================
# Pipeline en vivo (stack real): agente(s) + métricas del módulo 09 + evaluador online del módulo 14
# =====================================================================================================================
class LivePipeline:
    """Monta el sistema completo para enviar telemetría REAL al Collector: servicio ``supportops-agent`` (trazas, logs, métricas RED/GenAI
    del módulo 09, etiquetadas con la versión del prompt) y servicio ``supportops-evaluator`` (spans de evaluación, eventos
    ``gen_ai.evaluation.result`` y métricas ``supportops.eval.*``). ``mode="memory"`` lo hace todo sin red (tests, modo degradado)."""

    def __init__(self, versions: Sequence[str] = ("v1",), *, mode: str = "auto", sampler: Any | None = None, judge: Any | None = None, seed: int = 42,
                 metric_interval_s: float = 5.0, feedback: bool = True, emit_events: bool = True, model: str = "mock-small"):
        from .otel_metrics import MetricsInstrumentor
        from .quality_eval import OnlineEvaluator, RateSampler, VersionTagInstrumentor, simulate_feedback
        from .telemetry import OTelInstrumentor, setup_telemetry
        self.tel_a = setup_telemetry("supportops-agent", mode=mode, set_global=False, metric_interval_s=metric_interval_s)
        self.tel_e = setup_telemetry("supportops-evaluator", mode=mode, set_global=False, metric_interval_s=metric_interval_s)
        self.ev = OnlineEvaluator(judge or MockJudge(seed), sampler or RateSampler(0.25), self.tel_e, emit_events=emit_events)
        self.feedback_on, self._simulate_feedback = feedback, simulate_feedback
        self.feedback: list[Any] = []
        self.cases: list[EvalCase] = []
        otel, met = OTelInstrumentor(self.tel_a, emit_metrics=False), MetricsInstrumentor(self.tel_a)
        self.agents: dict[str, Any] = {}
        for v in versions:
            col = CaseCollector(version=v, on_case=self._on_case)
            self.agents[v], _ = make_agent(v, model=model, seed=seed, instrumentors=[otel, met, VersionTagInstrumentor(v)], collector=col)
        self.otel = otel

    def _on_case(self, case: EvalCase) -> None:
        self.cases.append(case)
        self.ev.submit(case)
        if self.feedback_on:
            for fb in self._simulate_feedback([case]):
                self.feedback.append(fb)
                self.ev.record_feedback(fb, case.version)

    def run_ticket(self, ticket: Ticket, version: str = "v1"):
        res = self.agents[version].run(ticket)
        self.ev.run_pending()
        return res

    def run_live(self, tickets: Sequence[Ticket], seconds: float, version_fn: Callable[[Ticket, float], str] = lambda t, el: "v1") -> list[Any]:
        """Reparte los tickets en ``seconds`` de tiempo REAL (como ``otel_metrics.run_live``); ``version_fn(ticket, segundos_transcurridos)``
        elige la versión (despliegue, canario…)."""
        import time as _t
        base, span = tickets[0].created_at, max(tickets[-1].created_at - tickets[0].created_at, 1e-9)
        t0 = _t.time()
        out = []
        for t in tickets:
            wait = t0 + (t.created_at - base) / span * seconds - _t.time()
            if wait > 0:
                _t.sleep(wait)
            out.append(self.run_ticket(dataclasses.replace(t, created_at=round(_t.time(), 3)), version_fn(t, _t.time() - t0)))
        return out

    def close(self) -> None:
        for tel in (self.tel_a, self.tel_e):
            tel.force_flush()
            tel.shutdown()
