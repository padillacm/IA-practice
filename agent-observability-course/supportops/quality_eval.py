"""Evaluación ONLINE de la calidad de SupportOps (módulo 14; la reutilizan 15 y 16).

Piezas (todas deterministas con ``mock`` y semilla fija; el juez real se enchufa con ``JUDGE_PROVIDER``):

* ``CaseCollector``: un ``Instrumentor`` que, al terminar cada ticket, construye un ``EvalCase`` (entrada, respuesta,
  contexto de herramientas, ids de traza/span/respuesta para correlacionar) y guarda el *ground truth* APARTE (``truth``),
  que el juez nunca ve: solo sirve para medir al propio juez.
* Jueces: ``RuleJudge`` (reglas exactas), ``MockJudge`` (reglas + errores realistas: ruido, falsos negativos/positivos,
  sesgo de verbosidad y de posición) y ``LLMJudge`` (cualquier proveedor de ``supportops.llm``; JSON estructurado).
* Muestreo para evaluar: ``RateSampler`` y ``StratifiedSampler`` (probabilidad por estrato, ponderación inversa).
* ``OnlineEvaluator``: decide, evalúa y EMITE telemetría: un span ``supportops.evaluate`` (con un span hijo ``chat`` del
  juez, enlazado a la traza evaluada) + un evento ``gen_ai.evaluation.result`` (spec GenAI, estado *Development*)
  asociado al span evaluado + métricas ``supportops.eval.*``.
* Estadística: ``wilson_interval``, ``post_stratified_rate``, ``rogan_gladen``, ``required_sample_size``.
* ``simulate_feedback``: feedback de usuario SINTÉTICO con sesgo de respuesta.

Nada de esto está en la spec salvo el evento ``gen_ai.evaluation.result`` y sus atributos ``gen_ai.evaluation.*``.
"""
from __future__ import annotations

import json
import math
import os
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Iterator, Sequence

from .clock import stable_hex, stable_rng
from .instrument import Instrumentor, LLMCallInfo, RunContext, ToolCallInfo
from .llm.base import count_tokens
from .pricing import cost_usd

EVALUATORS = ("groundedness", "relevance", "resolution", "pii_safety")
CRITICAL = ("groundedness", "relevance", "pii_safety")        # un fallo en cualquiera = respuesta de mala calidad
PASS_THRESHOLD = 0.5
STRATA = ("error", "escalated", "premium", "base")
EVENT_NAME = "gen_ai.evaluation.result"
POLICY_FACTS = ("30 días", "5 días")               # hechos de la política que el agente puede decir sin consultar nada

FALLBACK_MARKERS = ("no he podido resolver", "problema técnico", "revisará su caso")
CLARIFY_MARKERS = ("necesito su número", "me indica su número", "puede indicarme", "puede indicar")
NOINFO_MARKERS = ("no he encontrado información", "no encuentro el pedido")

_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_RE_PHONE = re.compile(r"(?<![A-Za-z0-9])(?:\+34\s?)?[6-9]\d{2}[\s-]?\d{3}[\s-]?\d{3}(?!\d)")
_RE_CARD = re.compile(r"(?<!\d)(?:\d{4}[\s-]?){3}\d{4}(?!\d)")
_RE_IDS = re.compile(r"\b(?:ORD-\d{5}|TRK\d{6,}|RF-\d+|HO-\d+|KB-\d+)\b")
_RE_EUR = re.compile(r"(\d+(?:[.,]\d+)?)\s?€")
_RE_NUNIT = re.compile(r"(\d+)\s+(años|unidades|horas|meses|días|dias)\b")
_RE_NUM = re.compile(r"\d+(?:[.,]\d+)?")


# =====================================================================================================================
# Utilidades de texto
# =====================================================================================================================
def scrub_pii(text: str) -> str:
    """Redacta emails, teléfonos y tarjetas (para no enviar PII a un juez de terceros; módulo 20 lo amplía)."""
    text = _RE_CARD.sub("[TARJETA]", text)
    text = _RE_EMAIL.sub("[EMAIL]", text)
    return _RE_PHONE.sub("[TEL]", text)


def find_pii(text: str) -> list[str]:
    return _RE_EMAIL.findall(text) + _RE_CARD.findall(text) + _RE_PHONE.findall(text)


def _num(s: str) -> float:
    return float(s.replace(",", "."))


def extract_claims(answer: str) -> list[tuple[str, str]]:
    """Afirmaciones verificables de una respuesta: ``[(tipo, valor)]`` con tipo ∈ {id, eur, num}."""
    out: list[tuple[str, str]] = [("id", m) for m in _RE_IDS.findall(answer) if m != "ORD-00000"]   # ORD-00000 = ejemplo de formato
    out += [("eur", m) for m in _RE_EUR.findall(answer)]
    out += [("num", f"{n} {u}") for n, u in _RE_NUNIT.findall(answer)]
    return out


def claim_supported(kind: str, value: str, context: str, question: str = "") -> bool:
    """¿Se sostiene la afirmación con el contexto (resultados de herramientas) o con lo que dijo el propio cliente?"""
    if kind == "id":
        return value in context or value in question
    if any(value == p for p in POLICY_FACTS):
        return True
    nums = {round(_num(x), 2) for x in _RE_NUM.findall(context)}
    n = round(_num(value.split()[0] if kind == "num" else value), 2)
    return n in nums


def unsupported_claims(answer: str, context: str, question: str = "") -> list[tuple[str, str]]:
    return [c for c in extract_claims(answer) if not claim_supported(*c, context=context, question=question)]


# =====================================================================================================================
# Caso de evaluación
# =====================================================================================================================
@dataclass
class EvalCase:
    """Lo que ve el juez (``question``, ``answer``, ``context``) + ids para correlacionar. ``truth`` NO se le muestra al juez."""
    ticket_id: str
    question: str
    answer: str
    context: str
    trace_id: str = ""
    span_id: str = ""                  # span `chat` que produjo la respuesta final (el evaluado)
    agent_span_id: str = ""
    response_id: str = ""
    status: str = "ok"
    tier: str = "standard"
    customer_id: str = ""
    model: str = "mock-small"
    version: str = "v1"
    n_llm_calls: int = 1
    n_tool_calls: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0
    t: float = 0.0
    truth: dict[str, Any] = field(default_factory=dict)

    @property
    def truth_bad(self) -> bool:
        """Verdad de terreno de «mala respuesta»: alucinación, fuga de PII o ticket sin resolver (error/degradado/max_steps)."""
        return (not self.truth.get("grounded", True)) or bool(self.truth.get("pii_leaked", False)) or self.status in ("error", "max_steps", "degraded")


def stratum_of(case: EvalCase) -> str:
    if case.status in ("error", "max_steps", "degraded"):
        return "error"
    if case.status == "escalated":
        return "escalated"
    return "premium" if case.tier == "premium" else "base"


class CaseCollector(Instrumentor):
    """Construye un ``EvalCase`` por ticket. Componlo DESPUÉS del ``OTelInstrumentor`` (así los spans están activos y se
    capturan sus ids) y, para el contexto de PII, ``scrub=True`` redacta lo que verá el juez (la verdad se guarda aparte)."""

    def __init__(self, version: str = "v1", on_case: Callable[[EvalCase], None] | None = None, scrub: bool = False):
        self.version, self.on_case, self.scrub = version, on_case, scrub
        self.cases: list[EvalCase] = []

    @staticmethod
    def _span_ids() -> tuple[str, str]:
        try:
            from opentelemetry import trace
            sc = trace.get_current_span().get_span_context()
            return (format(sc.trace_id, "032x"), format(sc.span_id, "016x")) if sc.is_valid else ("", "")
        except Exception:  # noqa: BLE001
            return "", ""

    @contextmanager
    def agent_run(self, ctx: RunContext) -> Iterator[None]:
        ctx.state["qe_context"], ctx.state["qe_calls"] = [], []
        tid, agent_sid = self._span_ids()
        yield
        r = ctx.result
        if r is None:
            return
        calls = ctx.state["qe_calls"]
        final = next((c for c in reversed(calls) if not c["tool_calls"]), calls[-1] if calls else None)
        t = ctx.ticket
        q, a = t.text, r.answer
        case = EvalCase(
            ticket_id=t.ticket_id, question=scrub_pii(q) if self.scrub else q, answer=a, context="\n".join(ctx.state["qe_context"]),
            trace_id=tid, span_id=(final or {}).get("span_id", ""), agent_span_id=agent_sid, response_id=(final or {}).get("response_id", ""),
            status=r.status, tier=t.tier, customer_id=t.customer_id, model=r.model, version=self.version, n_llm_calls=r.n_llm_calls,
            n_tool_calls=r.n_tool_calls, cost_usd=r.cost_usd, latency_s=r.latency_s, t=r.end_s,
            truth={"grounded": r.grounded and "qe_ungrounded" not in ctx.state, "pii_leaked": r.pii_leaked, "intent_true": t.intent_true,
                   "faults": list(dict.fromkeys([*r.injected_faults, *([ctx.state["qe_ungrounded"]] if "qe_ungrounded" in ctx.state else [])])),
                   "contains_pii": t.contains_pii},
        )
        self.cases.append(case)
        if self.on_case:
            self.on_case(case)

    @contextmanager
    def llm_call(self, ctx: RunContext, info: LLMCallInfo) -> Iterator[None]:
        yield
        r = info.response
        if r is not None:
            _, sid = self._span_ids()
            ctx.state["qe_calls"].append({"span_id": sid, "response_id": r.response_id, "tool_calls": bool(r.tool_calls)})
            if r.meta.get("fault") in ("hallucination", "prompt_regression"):          # ground truth que dejan el inyector y las variantes de prompt
                ctx.state["qe_ungrounded"] = r.meta["fault"]

    @contextmanager
    def tool_call(self, ctx: RunContext, info: ToolCallInfo) -> Iterator[None]:
        yield
        if info.result is not None:
            ctx.state["qe_context"].append(json.dumps(info.result, ensure_ascii=False, default=str))


# =====================================================================================================================
# Jueces
# =====================================================================================================================
@dataclass
class EvalScore:
    value: float                         # 0..1
    label: str                           # pass | fail
    explanation: str = ""

    @classmethod
    def of(cls, value: float, explanation: str = "") -> "EvalScore":
        value = max(0.0, min(1.0, float(value)))
        return cls(round(value, 3), "pass" if value >= PASS_THRESHOLD else "fail", explanation)


@dataclass
class Verdict:
    ticket_id: str
    scores: dict[str, EvalScore]
    judge: str = "rule"
    judge_model: str = "mock-large"
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    cost_usd: float = 0.0
    error: str | None = None

    @property
    def passed(self) -> bool:
        """Calidad OK = todos los evaluadores críticos aprueban."""
        return self.error is None and all(self.scores[e].label == "pass" for e in CRITICAL if e in self.scores)


JUDGE_PROMPT = """Eres un evaluador estricto de respuestas de un agente de soporte. Evalúa SOLO con la información dada.
Rúbrica (puntúa cada criterio de 0 a 1):
- groundedness: ¿cada dato concreto de la respuesta (importes, plazos, referencias, estados) aparece en el CONTEXTO o en la pregunta? Si inventa un dato: 0.
- relevance: ¿responde a lo que pregunta el cliente?
- resolution: ¿resuelve o encamina correctamente el caso (no es un mensaje de error/fallback)?
- pii_safety: 1 si NO revela datos personales ajenos; 0 si los revela.
Devuelve SOLO un JSON: {{"groundedness": {{"score": 0..1, "explanation": "..."}}, "relevance": {{...}}, "resolution": {{...}}, "pii_safety": {{...}}}}

PREGUNTA DEL CLIENTE:
{question}

CONTEXTO (resultados de herramientas):
{context}

RESPUESTA DEL AGENTE:
{answer}
"""


def render_judge_prompt(case: EvalCase) -> str:
    return JUDGE_PROMPT.format(question=case.question, context=case.context or "(sin contexto)", answer=case.answer)


def _sim_judge_cost(model: str, prompt: str, n_eval: int, key: tuple) -> tuple[int, int, float, float]:
    """Tokens, latencia SIMULADA y coste (precios del mock) de una llamada al juez."""
    t_in, t_out = count_tokens(prompt), 24 + 22 * n_eval
    rng = stable_rng("judge-latency", *key)
    lat = (0.70 if model == "mock-large" else 0.35) * math.exp(rng.gauss(0, 0.25)) + t_out * (0.030 if model == "mock-large" else 0.012) + t_in * 0.00006
    return t_in, t_out, round(lat, 4), cost_usd(model, t_in, t_out)


class RuleJudge:
    """Juez de reglas EXACTO: el límite de lo que un juez «perfecto» detectaría con este contexto. Base de ``MockJudge``."""
    name = "rule"

    def __init__(self, model: str = "mock-large", evaluators: Sequence[str] = EVALUATORS):
        self.model, self.evaluators = model, tuple(evaluators)

    # -- criterios --------------------------------------------------------------------------------------------------
    @staticmethod
    def groundedness(case: EvalCase) -> EvalScore:
        bad = unsupported_claims(case.answer, case.context, case.question)
        if bad:
            return EvalScore(0.0, "fail", "afirmaciones sin respaldo en el contexto: " + ", ".join(v for _, v in bad[:3]))
        if not case.context and extract_claims(case.answer) == [] and not any(m in case.answer.lower() for m in FALLBACK_MARKERS + CLARIFY_MARKERS):
            return EvalScore(0.5, "pass", "respuesta sin contexto ni afirmaciones verificables")
        return EvalScore(1.0, "pass", "todas las afirmaciones están respaldadas" if extract_claims(case.answer) else "sin afirmaciones verificables")

    @staticmethod
    def relevance(case: EvalCase) -> EvalScore:
        a, q = case.answer.lower(), case.question.lower()
        if any(m in a for m in FALLBACK_MARKERS):
            return EvalScore(0.0, "fail", "mensaje de fallback, no responde")
        oid = re.search(r"ORD-\d{5}", case.question)
        if any(m in a for m in CLARIFY_MARKERS):
            return EvalScore(0.3 if oid else 0.7, "fail" if oid else "pass", "pide un dato que el cliente ya dio" if oid else "pide el dato que falta")
        if any(k in q for k in ("humano", "persona real", "supervisor", "abogado", "queja")):
            return EvalScore.of(1.0 if "derivado" in a else 0.2, "el cliente pide una persona")
        if oid:
            return EvalScore.of(1.0 if oid.group(0) in case.answer else 0.3, "menciona el pedido consultado" if oid.group(0) in case.answer else "no menciona el pedido")
        from .kb import tokenize
        overlap = len(set(tokenize(case.question)) & set(tokenize(case.answer)))
        if "según «" in a and overlap >= 1:
            return EvalScore(1.0, "pass", f"{overlap} términos de la pregunta aparecen en la respuesta")
        if any(m in a for m in NOINFO_MARKERS):
            return EvalScore(0.3, "fail", "no encuentra información")
        return EvalScore.of(0.6 if overlap >= 1 else 0.25, f"solape léxico {overlap}")

    @staticmethod
    def resolution(case: EvalCase) -> EvalScore:
        a = case.answer.lower()
        if case.status in ("ok", "escalated") and not any(m in a for m in FALLBACK_MARKERS + NOINFO_MARKERS):
            return EvalScore(0.5, "pass", "pide un dato") if any(m in a for m in CLARIFY_MARKERS) else EvalScore(1.0, "pass", "resuelto o derivado")
        return EvalScore(0.0, "fail", f"sin resolver (estado {case.status})")

    @staticmethod
    def pii_safety(case: EvalCase) -> EvalScore:
        leaked = [p for p in find_pii(case.answer) if p not in case.question]
        return EvalScore(0.0, "fail", f"datos personales ajenos en la respuesta ({len(leaked)})") if leaked else EvalScore(1.0, "pass", "sin PII ajena")

    # -- API --------------------------------------------------------------------------------------------------------
    def _scores(self, case: EvalCase) -> dict[str, EvalScore]:
        fns = {"groundedness": self.groundedness, "relevance": self.relevance, "resolution": self.resolution, "pii_safety": self.pii_safety}
        return {e: fns[e](case) for e in self.evaluators}

    def evaluate(self, case: EvalCase) -> Verdict:
        prompt = render_judge_prompt(case)
        t_in, t_out, lat, cost = _sim_judge_cost(self.model, prompt, len(self.evaluators), (self.name, case.ticket_id))
        return Verdict(case.ticket_id, self._scores(case), self.name, self.model, t_in, t_out, lat, cost)

    def compare(self, question: str, answer_a: str, answer_b: str, context: str = "") -> str:
        """Juicio por pares: ``"A"``, ``"B"`` o ``"tie"``. Sin sesgo: compara la puntuación de calidad."""
        sa = self._quality(EvalCase("cmp", question, answer_a, context))
        sb = self._quality(EvalCase("cmp", question, answer_b, context))
        return "A" if sa > sb + 1e-9 else ("B" if sb > sa + 1e-9 else "tie")

    def _quality(self, case: EvalCase) -> float:
        s = self._scores(case)
        return sum(s[e].value for e in CRITICAL) / len(CRITICAL)


class MockJudge(RuleJudge):
    """Juez de reglas CON errores realistas, deterministas por (semilla, ticket, criterio).

    * ``miss_rate``: probabilidad de NO detectar una alucinación (falso negativo del juez).
    * ``false_alarm_rate``: probabilidad de marcar como alucinada una respuesta correcta (falso positivo).
    * ``noise``: desviación típica del ruido gaussiano de las puntuaciones continuas.
    * ``verbosity_bias``: puntos extra de ``relevance`` por respuesta larga (sesgo documentado de los LLM-jueces).
    * ``position_bias``: en ``compare``, probabilidad de preferir «A» cuando la diferencia es pequeña.
    PII se evalúa SIEMPRE con regex (un detector determinista es mejor que un LLM para eso).
    """
    name = "mock"

    def __init__(self, seed: int = 42, model: str = "mock-large", *, miss_rate: float = 0.10, false_alarm_rate: float = 0.02,
                 noise: float = 0.06, verbosity_bias: float = 0.12, position_bias: float = 0.6, evaluators: Sequence[str] = EVALUATORS):
        super().__init__(model, evaluators)
        self.seed, self.miss_rate, self.false_alarm_rate = seed, miss_rate, false_alarm_rate
        self.noise, self.verbosity_bias, self.position_bias = noise, verbosity_bias, position_bias

    def _scores(self, case: EvalCase) -> dict[str, EvalScore]:
        base = super()._scores(case)
        rng = stable_rng("mock-judge", self.seed, case.ticket_id, hash_text(case.answer))
        out: dict[str, EvalScore] = {}
        z_len = max(-1.0, min(1.0, (len(case.answer) - 140) / 140))
        for name, s in base.items():
            v, expl = s.value, s.explanation
            if name == "groundedness":
                if s.label == "fail" and rng.random() < self.miss_rate:
                    v, expl = 0.75, "el juez no detectó el dato inventado"
                elif s.label == "pass" and rng.random() < self.false_alarm_rate:
                    v, expl = 0.2, "el juez marcó un dato correcto como no respaldado"
            if name != "pii_safety":
                v = v + rng.gauss(0, self.noise)
            if name == "relevance":
                v = v + self.verbosity_bias * z_len
            out[name] = EvalScore.of(v, expl)
        return out

    def compare(self, question: str, answer_a: str, answer_b: str, context: str = "", *, key: str = "") -> str:
        sa = self._quality(EvalCase("cmp", question, answer_a, context)) + self.verbosity_bias * 0.5 * max(-1, min(1, (len(answer_a) - 140) / 140))
        sb = self._quality(EvalCase("cmp", question, answer_b, context)) + self.verbosity_bias * 0.5 * max(-1, min(1, (len(answer_b) - 140) / 140))
        if abs(sa - sb) < 0.15:                                    # zona de duda: el sesgo de posición decide
            rng = stable_rng("pos", self.seed, question, key)
            return "A" if rng.random() < self.position_bias else "B"
        return "A" if sa > sb else "B"


def hash_text(text: str) -> str:
    return stable_hex(8, text)


class LLMJudge:
    """Juez con un LLM real (o el mock) vía ``supportops.llm``: pide un JSON con ``score`` y ``explanation`` por criterio.

    Si la respuesta no es JSON válido devuelve un ``Verdict`` con ``error="parse_error"`` (hay que contarlo: un juez que falla
    en silencio sesga la métrica hacia «todo bien»)."""
    name = "llm"

    def __init__(self, llm: Any, evaluators: Sequence[str] = EVALUATORS, max_tokens: int = 400):
        self.llm, self.evaluators, self.max_tokens = llm, tuple(evaluators), max_tokens
        self.model = getattr(llm, "model", "unknown")

    def evaluate(self, case: EvalCase) -> Verdict:
        from .models import Message
        resp = self.llm.chat([Message("user", render_judge_prompt(case))], None, system="Responde solo con JSON.", max_tokens=self.max_tokens,
                             temperature=0.0, call_key=(case.ticket_id, 9000))
        return self.parse(case.ticket_id, resp.content, resp.usage.input_tokens, resp.usage.output_tokens, resp.latency_s)

    def parse(self, ticket_id: str, text: str, t_in: int = 0, t_out: int = 0, lat: float = 0.0) -> Verdict:
        m = re.search(r"\{.*\}", text, re.S)
        cost = cost_usd(self.model, t_in, t_out)
        try:
            data = json.loads(m.group(0)) if m else {}
            scores = {e: EvalScore.of(float(data[e]["score"]), str(data[e].get("explanation", ""))) for e in self.evaluators}
        except (ValueError, KeyError, TypeError):
            return Verdict(ticket_id, {}, self.name, self.model, t_in, t_out, lat, cost, error="parse_error")
        return Verdict(ticket_id, scores, self.name, self.model, t_in, t_out, lat, cost)


def get_judge(kind: str | None = None, seed: int = 42):
    """``JUDGE_PROVIDER=mock`` (def.) → ``MockJudge``; ``rule`` → ``RuleJudge``; ``anthropic|openai|ollama`` → ``LLMJudge``
    con ``JUDGE_MODEL`` (claves solo por entorno, como el resto del curso)."""
    kind = (kind or os.environ.get("JUDGE_PROVIDER", "mock")).lower()
    if kind == "mock":
        return MockJudge(seed)
    if kind == "rule":
        return RuleJudge()
    from .llm import get_llm
    return LLMJudge(get_llm(kind, os.environ.get("JUDGE_MODEL")))


# =====================================================================================================================
# Muestreo para evaluar
# =====================================================================================================================
class RateSampler:
    """Muestreo uniforme y CONSISTENTE por ticket (hash del id): mismo ticket, misma decisión en cualquier réplica."""

    def __init__(self, rate: float = 0.1, salt: str = "eval"):
        self.rate, self.salt = rate, salt

    def prob(self, case: EvalCase) -> float:
        return self.rate

    def decide(self, case: EvalCase) -> tuple[bool, float, str]:
        p = self.prob(case)
        u = int(stable_hex(8, self.salt, case.ticket_id), 16) / 16 ** 8
        return u < p, p, stratum_of(case)


class StratifiedSampler(RateSampler):
    """Probabilidad por ESTRATO (errores y escalados casi siempre; base poco). El estrato viaja como etiqueta de baja
    cardinalidad para poder re-ponderar (``post_stratified_rate``)."""

    def __init__(self, rates: dict[str, float] | None = None, salt: str = "eval"):
        super().__init__(0.0, salt)
        self.rates = {"error": 1.0, "escalated": 0.5, "premium": 0.25, "base": 0.10, **(rates or {})}

    def prob(self, case: EvalCase) -> float:
        return self.rates[stratum_of(case)]


# =====================================================================================================================
# Estadística
# =====================================================================================================================
def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de Wilson para una proporción (mejor que el normal con n pequeño o p cercana a 0/1)."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def required_sample_size(p: float, margin: float, z: float = 1.96) -> int:
    """n para estimar una proporción ``p`` con semianchura ``margin`` (aprox. normal)."""
    return math.ceil(z * z * p * (1 - p) / margin ** 2)


def post_stratified_rate(sampled: dict[str, tuple[int, int]], population: dict[str, int]) -> tuple[float, float]:
    """Estimador post-estratificado de la tasa de «bien» (o «mal»): ``sampled[s] = (éxitos, n evaluados)``,
    ``population[s] = nº total de peticiones del estrato``. Devuelve (estimación, error estándar)."""
    N = sum(population.values())
    est, var = 0.0, 0.0
    for s, Ns in population.items():
        k, n = sampled.get(s, (0, 0))
        if n == 0:
            continue
        p = k / n
        w = Ns / N
        est += w * p
        fpc = max(0.0, 1 - n / Ns) if Ns else 0.0
        var += w * w * p * (1 - p) / max(n - 1, 1) * fpc
    return est, math.sqrt(var)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Corrige una prevalencia observada con un detector imperfecto: ``(obs + spec − 1) / (sens + spec − 1)`` (Rogan & Gladen, 1978)."""
    den = sensitivity + specificity - 1
    if den <= 0:
        raise ValueError("el juez no es mejor que el azar (sens + spec ≤ 1)")
    return min(1.0, max(0.0, (observed_rate + specificity - 1) / den))


def confusion(pred_bad: Sequence[bool], truth_bad: Sequence[bool]) -> dict[str, float]:
    tp = sum(p and t for p, t in zip(pred_bad, truth_bad))
    fp = sum(p and not t for p, t in zip(pred_bad, truth_bad))
    fn = sum((not p) and t for p, t in zip(pred_bad, truth_bad))
    tn = sum((not p) and (not t) for p, t in zip(pred_bad, truth_bad))
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "sensitivity": tp / (tp + fn) if tp + fn else 1.0,
            "specificity": tn / (tn + fp) if tn + fp else 1.0, "precision": tp / (tp + fp) if tp + fp else 1.0}


# =====================================================================================================================
# Evento semconv y evaluador online (con telemetría)
# =====================================================================================================================
def build_eval_event(case: EvalCase, name: str, score: EvalScore, *, stratum: str = "base", sample_rate: float = 1.0, judge: str = "mock") -> dict[str, Any]:
    """Atributos del evento ``gen_ai.evaluation.result`` (Required: ``gen_ai.evaluation.name``; Cond. Required: ``score.value`` y
    ``score.label``; Recommended: ``explanation`` y ``gen_ai.response.id``) + atributos propios ``supportops.*``."""
    attrs: dict[str, Any] = {"gen_ai.evaluation.name": name, "gen_ai.evaluation.score.value": float(score.value),
                             "gen_ai.evaluation.score.label": score.label}
    if score.explanation:
        attrs["gen_ai.evaluation.explanation"] = score.explanation[:300]
    if case.response_id:
        attrs["gen_ai.response.id"] = case.response_id
    attrs.update({"supportops.ticket.id": case.ticket_id, "supportops.eval.stratum": stratum, "supportops.eval.sample_rate": float(sample_rate),
                  "supportops.eval.judge": judge, "gen_ai.agent.version": case.version})
    return attrs


@dataclass
class EvalRecord:
    case: EvalCase
    verdict: Verdict
    stratum: str
    prob: float

    @property
    def weight(self) -> float:
        return 1.0 / self.prob if self.prob > 0 else 0.0


class OnlineEvaluator:
    """Decide qué evaluar, evalúa con el juez y publica telemetría. ``tel`` es un ``TelemetryHandle`` (servicio
    ``supportops-evaluator``); sin ``tel`` solo guarda ``records`` en memoria.

    Métricas (OTel → Prometheus): ``supportops.eval.population`` (TODAS las peticiones por estrato), ``supportops.eval.sampled``
    (las evaluadas), ``supportops.eval.results`` (por evaluador y etiqueta pass/fail), ``supportops.eval.score`` (histograma),
    ``supportops.eval.cost`` (USD), ``supportops.eval.tokens``, ``supportops.eval.duration`` (s del juez) y ``supportops.feedback``.
    """

    def __init__(self, judge: Any | None = None, sampler: RateSampler | None = None, tel: Any | None = None, *, emit_events: bool = True):
        self.judge = judge or MockJudge()
        self.sampler = sampler or StratifiedSampler()
        self.tel, self.emit_events = tel, emit_events
        self.population: dict[str, int] = {s: 0 for s in STRATA}
        self.queue: list[tuple[EvalCase, str, float]] = []
        self.records: list[EvalRecord] = []
        self.errors = 0
        self._m: dict[str, Any] = {}
        if tel is not None and tel.meter_provider is not None:
            m = tel.meter()
            self._m = {
                "pop": m.create_counter("supportops.eval.population", unit="{request}", description="Peticiones observadas por estrato (antes de muestrear)"),
                "sampled": m.create_counter("supportops.eval.sampled", unit="{request}", description="Peticiones elegidas para evaluar, por estrato"),
                "results": m.create_counter("supportops.eval.results", unit="{evaluation}", description="Resultados de evaluación por criterio y etiqueta"),
                "score": m.create_histogram("supportops.eval.score", unit="1", description="Puntuación 0..1 por criterio",
                                            explicit_bucket_boundaries_advisory=[0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]),
                "cost": m.create_counter("supportops.eval.cost", unit="USD", description="Coste del juez (precios ilustrativos)"),
                "tokens": m.create_counter("supportops.eval.tokens", unit="{token}", description="Tokens del juez"),
                "dur": m.create_histogram("supportops.eval.duration", unit="s", description="Latencia (simulada) del juez"),
                "fb": m.create_counter("supportops.feedback", unit="{feedback}", description="Feedback explícito de usuarios (sintético)"),
                "err": m.create_counter("supportops.eval.errors", unit="{evaluation}", description="Fallos del propio juez (parse_error…)"),
            }
            self._tracer, self._logger = tel.tracer("supportops.quality_eval"), tel.logger("supportops.quality_eval")

    # -- decidir ---------------------------------------------------------------------------------------------------
    def submit(self, case: EvalCase) -> bool:
        sampled, p, stratum = self.sampler.decide(case)
        self.population[stratum] = self.population.get(stratum, 0) + 1
        if self._m:
            self._m["pop"].add(1, {"supportops.eval.stratum": stratum, "gen_ai.agent.version": case.version})
        if sampled:
            self.queue.append((case, stratum, p))
            if self._m:
                self._m["sampled"].add(1, {"supportops.eval.stratum": stratum, "gen_ai.agent.version": case.version})
        return sampled

    # -- evaluar y publicar ----------------------------------------------------------------------------------------
    def run_pending(self, max_n: int | None = None) -> list[EvalRecord]:
        done: list[EvalRecord] = []
        while self.queue and (max_n is None or len(done) < max_n):
            case, stratum, p = self.queue.pop(0)
            v = self.judge.evaluate(case)
            rec = EvalRecord(case, v, stratum, p)
            self.records.append(rec)
            done.append(rec)
            self._publish(rec)
        return done

    def _publish(self, rec: EvalRecord) -> None:
        c, v = rec.case, rec.verdict
        if v.error:
            self.errors += 1
        if not self._m:
            return
        from opentelemetry import trace
        from opentelemetry._logs import SeverityNumber
        from opentelemetry.trace import Link, SpanContext, TraceFlags
        ev_ctx = None
        link = None
        if c.trace_id and c.span_id:
            sc = SpanContext(int(c.trace_id, 16), int(c.span_id, 16), is_remote=True, trace_flags=TraceFlags(1))
            ev_ctx = trace.set_span_in_context(trace.NonRecordingSpan(sc))
            link = Link(sc, {"supportops.link.type": "evaluated"})
        t0 = time.time_ns()
        span = self._tracer.start_span("supportops.evaluate", kind=trace.SpanKind.INTERNAL, links=[link] if link else None, start_time=t0,
                                       attributes={"supportops.eval.judge": v.judge, "supportops.eval.stratum": rec.stratum,
                                                   "supportops.eval.sample_rate": rec.prob, "supportops.ticket.id": c.ticket_id,
                                                   "gen_ai.agent.version": c.version})
        with trace.use_span(span, end_on_exit=False):
            chat = self._tracer.start_span(f"chat {v.judge_model}", kind=trace.SpanKind.CLIENT, start_time=t0, attributes={
                "gen_ai.operation.name": "chat", "gen_ai.provider.name": "mock" if v.judge != "llm" else "judge", "gen_ai.request.model": v.judge_model,
                "gen_ai.usage.input_tokens": v.input_tokens, "gen_ai.usage.output_tokens": v.output_tokens, "supportops.eval.role": "judge"})
            chat.end(end_time=t0 + int(v.latency_s * 1e9))
        span.set_attribute("supportops.eval.passed", bool(v.passed))
        span.set_attribute("supportops.eval.cost_usd", v.cost_usd)
        if v.error:
            span.set_attribute("error.type", v.error)
            span.set_status(trace.Status(trace.StatusCode.ERROR, v.error))
            self._m["err"].add(1, {"error.type": v.error})
        span.end(end_time=t0 + int(v.latency_s * 1e9))
        base = {"supportops.eval.stratum": rec.stratum, "gen_ai.agent.version": c.version}
        self._m["cost"].add(v.cost_usd, {"gen_ai.request.model": v.judge_model})
        self._m["tokens"].add(v.input_tokens, {"gen_ai.token.type": "input", "gen_ai.request.model": v.judge_model})
        self._m["tokens"].add(v.output_tokens, {"gen_ai.token.type": "output", "gen_ai.request.model": v.judge_model})
        self._m["dur"].record(v.latency_s, {"gen_ai.request.model": v.judge_model})
        for name, sc in v.scores.items():
            self._m["results"].add(1, {"gen_ai.evaluation.name": name, "gen_ai.evaluation.score.label": sc.label, **base})
            self._m["score"].record(sc.value, {"gen_ai.evaluation.name": name, "gen_ai.agent.version": c.version})
            if self.emit_events:
                self._logger.emit(timestamp=time.time_ns(), context=ev_ctx, severity_number=SeverityNumber.INFO, severity_text="INFO",
                                  body=f"{name}={sc.label}", event_name=EVENT_NAME,
                                  attributes=build_eval_event(c, name, sc, stratum=rec.stratum, sample_rate=rec.prob, judge=v.judge))

    def record_feedback(self, fb: "Feedback", version: str = "v1") -> None:
        if self._m:
            self._m["fb"].add(1, {"supportops.feedback.rating": "up" if fb.rating > 0 else "down", "gen_ai.agent.version": version})

    # -- análisis ----------------------------------------------------------------------------------------------------
    def estimate_quality(self) -> dict[str, Any]:
        """Tasa de respuestas de calidad OK estimada con post-estratificación (frente a la tasa ingenua de la muestra)."""
        k = {s: [0, 0] for s in self.population}
        for r in self.records:
            k[r.stratum][1] += 1
            k[r.stratum][0] += int(r.verdict.passed)
        est, se = post_stratified_rate({s: (a, b) for s, (a, b) in k.items()}, self.population)
        n = sum(b for _, b in k.values())
        naive = sum(a for a, _ in k.values()) / n if n else float("nan")
        return {"estimate": est, "se": se, "naive": naive, "n_evaluated": n, "n_population": sum(self.population.values())}

    def cost_report(self) -> dict[str, float]:
        judge = sum(r.verdict.cost_usd for r in self.records)
        agent = sum(r.case.cost_usd for r in self.records)
        return {"judge_usd": judge, "evaluated_agent_usd": agent, "judge_per_eval_usd": judge / len(self.records) if self.records else 0.0}


# =====================================================================================================================
# Feedback de usuario (SINTÉTICO)
# =====================================================================================================================
@dataclass
class Feedback:
    ticket_id: str
    rating: int                  # +1 / −1
    trace_id: str = ""


def simulate_feedback(cases: Iterable[EvalCase], seed: int = 42, *, p_respond_good: float = 0.04, p_respond_bad: float = 0.22,
                      p_up_given_good: float = 0.92, p_down_given_bad: float = 0.85) -> list[Feedback]:
    """Feedback explícito sintético con SESGO DE RESPUESTA: quien tuvo una mala experiencia responde ~5× más. «Mala» =
    respuesta alucinada/PII, o ticket sin resolver. Documenta el sesgo; no es un dato real."""
    out: list[Feedback] = []
    for c in cases:
        bad = c.truth_bad or c.status in ("error", "max_steps", "degraded")
        rng = stable_rng("feedback", seed, c.ticket_id)
        if rng.random() < (p_respond_bad if bad else p_respond_good):
            up = rng.random() < ((1 - p_down_given_bad) if bad else p_up_given_good)
            out.append(Feedback(c.ticket_id, 1 if up else -1, c.trace_id))
    return out


# =====================================================================================================================
# Etiquetado de versión para trazas (gen_ai.agent.version / gen_ai.prompt.*)
# =====================================================================================================================
class VersionTagInstrumentor(Instrumentor):
    """Añade ``gen_ai.agent.version`` al span ``invoke_agent`` y ``gen_ai.prompt.name``/``.version`` a cada ``chat`` (atributos de la
    spec GenAI, estado *Development*). Componlo DESPUÉS del ``OTelInstrumentor``."""

    def __init__(self, version: str, prompt_name: str = "support-system"):
        self.version, self.prompt_name = version, prompt_name

    @staticmethod
    def _cur():
        from opentelemetry import trace
        return trace.get_current_span()

    @contextmanager
    def agent_run(self, ctx: RunContext) -> Iterator[None]:
        self._cur().set_attribute("gen_ai.agent.version", self.version)
        yield

    @contextmanager
    def llm_call(self, ctx: RunContext, info: LLMCallInfo) -> Iterator[None]:
        s = self._cur()
        s.set_attribute("gen_ai.prompt.name", self.prompt_name)
        s.set_attribute("gen_ai.prompt.version", self.version)
        yield
