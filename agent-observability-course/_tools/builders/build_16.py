"""Genera el módulo 16_slos_alertas_incidentes: README, lección, proyecto, dashboard, alertas provisionadas y runbooks.
Ejecutar desde la raíz del repo:  python agent-observability-course/_tools/builders/build_16.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "16_slos_alertas_incidentes"
RUNBOOK_BASE = "https://github.com/padillacm/IA-practice/blob/master/agent-observability-course/16_slos_alertas_incidentes/runbooks"
DASH_UID = "slo-agente"

RUNBOOKS = {
    "slo-availability-fast-burn.md": """# Runbook · SLO de disponibilidad: quema rápida (página)

**Alerta:** `SLO availability · fast-burn (×14.4)` · **Severidad:** page · **Servicio:** `supportops-agent` · **Dashboard:** `16 · SLOs de SupportOps` (uid `slo-agente`)

## Qué significa
Más del 14,4 % de los tickets (con objetivo del 99 %) terminan en `error`, `degraded` o `max_steps` **ahora mismo** (ventana larga) **y** el problema sigue (ventana corta).
A este ritmo el presupuesto de error del periodo se agota en horas, no en semanas. Alguien está esperando una respuesta que no llega.

## Primeros 5 minutos (no diagnostiques, orienta)
1. Abre el dashboard `slo-agente`: ¿qué SLO arde? Si **solo** arde disponibilidad, mira la fila «Contexto».
2. ¿Hay un **despliegue** reciente? (`gen_ai.agent.version`, calendario de cambios). Si sí → **revierte primero, investiga después**.
3. Tipo de error dominante (PromQL): `sum by (error_type) (rate(gen_ai_client_inference_duration_seconds_count{service_name="supportops-agent",error_type!=""}[5m]))`.
4. Una traza con error (TraceQL): `{ resource.service.name = "supportops-agent" && status = error } | select(span.error.type, span.http.response.status_code)`.

## Árbol de diagnóstico
| Si ves… | Probable causa | Acción |
|---|---|---|
| `error.type=server_error`, `http.response.status_code=5xx` en los `chat` | Proveedor LLM degradado | Activar el modelo de reserva / `DowngradeLLM`; abrir caso con el proveedor; comunicar |
| `error.type=rate_limit` (429) | Cuota agotada o tráfico anómalo | Subir cuota, activar límites por cliente, revisar bucles (módulo 13) |
| `execute_tool` con `error.type=timeout`/`upstream_500` | Herramienta o API aguas abajo | Circuit breaker, modo degradado (escalar a humano), avisar al equipo propietario |
| Errores solo en una versión | Regresión de despliegue | Rollback del canario |
| Sin tráfico (`rate=0`) | Fallo aguas arriba o telemetría rota | Comprobar Collector (`otelcol_receiver_accepted_spans`) y balanceador |

## Mitigación
- Objetivo: **reducir el impacto**, no encontrar la causa raíz. Rollback, conmutación a modelo de reserva, escalado a humanos, reducción de carga.
- Anuncia en el canal de incidentes: impacto, hipótesis, siguiente actualización en 15 min.

## Escalado
Si no hay mitigación en **30 min**, escalar al responsable de guardia secundaria. SEV-1 si el impacto supera el 50 % de los tickets durante > 15 min.

## Después
Abrir postmortem sin culpa (`postmortem-template.md`) en 48 h. Revisar si la alerta saltó a tiempo (TTD) y si este runbook fue suficiente.
""",
    "slo-quality-slow-burn.md": """# Runbook · SLO de calidad: quema lenta (ticket)

**Alerta:** `SLO quality · slow-burn (×3)` · **Severidad:** ticket (no despierta a nadie) · **Servicio:** `supportops-agent` / `supportops-evaluator`

## Qué significa
La fracción de respuestas **fundamentadas** (groundedness) evaluadas por el juez baja del objetivo: el presupuesto de calidad se consume al menos 3× más rápido de lo sostenible.
Es el patrón de la **regresión silenciosa** (módulo 15): latencia y errores parecen normales.

## Primeros pasos (horas de trabajo, no minutos)
1. ¿Cambió algo? Compara calidad **por versión** (`gen_ai_agent_version`) en el dashboard `regresion-versiones` (uid): una versión por debajo de otra = regresión de despliegue.
2. ¿Está sano el **juez**? `supportops_eval_errors_total`, cobertura (`sampled/population`) y un cambio de versión del juez. Una caída de calidad sin cambios en el agente suele ser el juez.
3. Huella de comportamiento: herramientas por ticket y `no_tool_rate` (`gen_ai_invoke_agent_tool_calls_*`). Una caída señala que el agente deja de consultar.
4. Trazas culpables (TraceQL): `{ name =~ "invoke_agent.*" && span.supportops.tool_calls = 0 && span.supportops.intent =~ "order_status|refund" }`.

## Acciones
- Regresión de versión → revertir el prompt/modelo (o reducir el canario) y añadir los casos al dataset de oro.
- Drift de entrada (temas nuevos) → ampliar la base de conocimiento; no es un rollback.
- Juez roto → corregir y **recalibrar** antes de confiar en la serie.

## Escalado
Si el SLO de calidad lleva > 24 h por encima de 6× → promover la alerta a página y congelar los despliegues (política de presupuesto agotado).
""",
    "postmortem-template.md": """# Postmortem · <título corto del incidente>

**Estado:** borrador · **Severidad:** SEV-? · **Autores:** <equipo> · **Fecha del incidente:** <fecha>
*Sin culpa: describe sistemas, decisiones y contexto; no señales a personas. La pregunta es «¿por qué tenía sentido hacer eso en ese momento?», no «¿quién lo hizo?».*

## Resumen
Una o dos frases: qué pasó, cuánto duró, a quién afectó.

## Impacto
- Usuarios/tickets afectados (número y %), SLO y presupuesto consumido, coste.

## Cronología
| Hora | Evento (detección, decisión, acción) |
|---|---|

## Causa raíz y factores contribuyentes
Cadena causal (los «5 porqués»), con los factores que la hicieron posible: ¿qué hacía **fácil** que ocurriera y **difícil** detectarlo?

## Qué fue bien / Qué fue mal / Dónde hubo suerte

## Acciones
| Acción | Responsable | Plazo | Tipo (prevenir / detectar / mitigar) |
|---|---|---|---|
Cada acción: concreta, con responsable, plazo y forma de comprobarla.
""",
}


def build_runbooks() -> None:
    d = COURSE / MOD / "runbooks"
    d.mkdir(parents=True, exist_ok=True)
    for name, text in RUNBOOKS.items():
        (d / name).write_text(text, encoding="utf-8")
    print("OK runbooks", list(RUNBOOKS))


# =====================================================================================================================
def _dash():
    sys.path.insert(0, str(COURSE))
    from supportops.dashkit import Dashboard, alertlist, gauge, lint, logs, prom, stat, text, thresholds, timeseries, traces_table
    from supportops.slo import DEFAULT_SLOS, LAB_POLICIES, burn_promql, sli_promql
    d = Dashboard(DASH_UID, "16 · SLOs de SupportOps", tags=["curso", "slo", "alertas"], time_from="now-30m",
                  description="SLIs, SLOs, presupuesto de error y burn rate multiventana de SupportOps (disponibilidad, latencia, calidad y coste). Ventanas COMPRIMIDAS de laboratorio (1-15 min).")
    d.add(text("Cómo leer este dashboard", "SLOs de laboratorio: **disponibilidad 99 %**, **latencia ≤ 5 s 97 %**, **calidad (groundedness) 95 %**, **coste ≤ 0,0005 USD 98 %**. "
               "El *burn rate* = (fracción de eventos malos) / (presupuesto = 1 − objetivo): 1 = ritmo sostenible; 14,4 = presupuesto agotado en 1/14,4 del periodo. "
               "Las alertas son **multiventana**: ventana larga (5 min) Y corta (1 min) por encima del factor (14,4 página; 3 ticket con 15 min y 3 min). En producción las ventanas serían 1 h/5 min y 6 h/30 min (SRE Workbook).", h=3))
    d.row("Estado de los SLO (ventana de 30 min)")
    panels = []
    for name, slo in DEFAULT_SLOS.items():
        panels.append(stat(f"SLI {name} (30 min)", sli_promql(slo.sli, "30m", slo.threshold), unit="percentunit", w=6, h=4, decimals=4, thr=thresholds((None, "red"), (slo.objective, "green")),
                           description=f"Fracción de eventos buenos en 30 min. Objetivo {slo.objective:.2%}. {slo.description}."))
    d.add(*panels)
    panels = []
    for name, slo in DEFAULT_SLOS.items():
        panels.append(gauge(f"Presupuesto restante · {name}", f"1 - (1 - ({sli_promql(slo.sli, '30m', slo.threshold)})) / {slo.budget:.6g}", unit="percentunit", min=-1, max=1, w=6, h=5,
                            description=f"Presupuesto de error restante del periodo de laboratorio (30 min): 1 = intacto, 0 = agotado, <0 = SLO incumplido. Presupuesto = {slo.budget:.2%} de eventos malos."))
    d.add(*panels)
    d.row("Burn rate multiventana (las alertas usan estas mismas consultas)")
    fast, slow = LAB_POLICIES
    for name, slo in DEFAULT_SLOS.items():
        d.add(timeseries(f"Burn rate · {name}", [prom(burn_promql(slo, f"{fast.long_min}m"), f"larga {fast.long_min} min"), prom(burn_promql(slo, f"{fast.short_min}m"), f"corta {fast.short_min} min", ref="B"),
                                                   prom(burn_promql(slo, f"{slow.long_min}m"), f"larga {slow.long_min} min", ref="C")], w=12, h=7, min=0,
                         thr=thresholds((None, "green"), (slow.factor, "orange"), (fast.factor, "red")), thr_style="line+area",
                         description=f"Burn rate del SLO {name}: >{fast.factor:g} con ventana larga Y corta = página; >{slow.factor:g} (15/3 min) = ticket. 1 = ritmo sostenible."))
    d.row("Alertas y contexto")
    d.add(alertlist("Alertas de SLO (estado actual)", w=8, h=8, description="Reglas de Grafana en estado firing/pending/error (provisionadas desde `provisioning/alerting/16-slo-alerts.yaml`).", states=("firing", "pending", "error", "noData")),
          traces_table("Trazas con error (Tempo)", '{ resource.service.name = "supportops-agent" && name =~ "invoke_agent.*" && status = error }', w=8, h=8, description="Tickets del agente que terminaron con error: abre uno para ver qué span falló."),
          logs("Errores del agente (Loki)", '{service_name="supportops-agent"} | detected_level=~"warn|error"', w=8, h=8, description="Logs de aviso/error del agente; cada línea lleva trace_id."))
    return d, lint


def build_dashboard() -> dict[str, int]:
    d, lint = _dash()
    problems = lint(d.to_dict())
    assert not problems, problems
    path = d.save(COURSE / "stack" / "grafana" / "dashboards" / "16-slos.json")
    print("OK dashboard", path.name)
    return {p["title"]: p["id"] for p in d.to_dict()["panels"]}


def build_alerts(panel_ids: dict[str, int]) -> None:
    sys.path.insert(0, str(COURSE))
    from supportops.slo import DEFAULT_SLOS, LAB_POLICIES, grafana_burn_rule, rules_yaml
    rules = []
    for name, slo in DEFAULT_SLOS.items():
        pid = panel_ids[f"Burn rate · {name}"]
        for pol in LAB_POLICIES:
            fn = "slo-availability-fast-burn.md" if (name == "availability" and pol.severity == "page") else ("slo-quality-slow-burn.md" if name == "quality" else "slo-availability-fast-burn.md")
            r = grafana_burn_rule(slo, pol, dashboard_uid=DASH_UID, panel_id=pid, for_="0s" if pol.severity == "page" else "1m", runbook=f"{RUNBOOK_BASE}/{fn}")
            rules.append(r)
    header = ("# Alertas de SLO de SupportOps (módulo 16): burn rate MULTIVENTANA con ventanas comprimidas de laboratorio (larga 5 min + corta 1 min = página; 15 + 3 min = ticket).\n"
              "# Generado por _tools/builders/build_16.py con supportops.slo.grafana_burn_rule. Cada regla: A (burn largo) B (burn corto) -> reduce C/D -> math E ($C > f && $D > f) -> umbral F.\n"
              "# interval: múltiplo de 10 s (tick del planificador de Grafana; 15s hace que NO arranque). El vínculo alerta-panel va en annotations.__dashboardUid__ / __panelId__.\n")
    text = rules_yaml(rules, group="supportops-slo", interval="30s", header=header)
    p = COURSE / "stack" / "grafana" / "provisioning" / "alerting" / "16-slo-alerts.yaml"
    p.write_text(text, encoding="utf-8")
    print("OK alertas", p.name, len(rules), "reglas")



IMPORTS_16 = """
import collections, dataclasses, json, math, re, time, threading
import yaml
from IPython.display import Markdown
from supportops.slo import (BASELINE_FAULTS, DEFAULT_SLOS, GOOGLE_POLICIES, LAB_POLICIES, DayScenario, MultiWindowPolicy, alert_quality, bin_events, budget_report,
                            burn_promql, burn_series, fire_series, grafana_burn_rule, minute_mask, pages_per_week, render_postmortem, rules_yaml, simulate_day,
                            simulate_month, sli_promql, threshold_fire_series, trailing_sum)
STACK = check_stack("core+metrics")
LIVE = not STACK.degraded
"""

DATA_16 = """
DAY = simulate_day(SEED)                                   # 24 h de tráfico REAL del agente (tiempo simulado): incidente de proveedor 10:00-10:45 + regresión de prompt v2 06:00-14:00
ROWS, NB, T0, TRUTH = DAY["rows"], DAY["n_bins"], DAY["t0"], DAY["truth"]
OUT, REG = minute_mask(*TRUTH["outage"], NB), minute_mask(*TRUTH["regression"], NB)
SERIES = {name: bin_events(ROWS, slo, t0=T0, n_bins=NB) for name, slo in DEFAULT_SLOS.items()}       # (buenos, totales) por minuto
print(f"{len(ROWS)} tickets en 24 h · incidente del proveedor: min {TRUTH['outage'][0]:.0f}-{TRUTH['outage'][1]:.0f} · regresión de prompt: min {TRUTH['regression'][0]:.0f}-{TRUTH['regression'][1]:.0f}")
print({n: f"{g.sum() / t.sum():.4f} (objetivo {DEFAULT_SLOS[n].objective:.2%}, {int(t.sum())} eventos)" for n, (g, t) in SERIES.items()})
"""


def build_lesson() -> None:
    nb, out = nb_for(MOD, "16_slos_alertas_incidentes.ipynb", "Módulo 16 · SLOs, alertas e incidentes de agentes de IA")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 16 · SLOs, alertas e incidentes: de «me parece que va mal» a «el presupuesto se agota en 2 horas»

    | | |
    |---|---|
    | **Nivel** | 🟠 Avanzado |
    | **Duración estimada** | ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min) |
    | **Servicios de Compose** | Opcional: `--profile core --profile metrics` (sección 7.1, ≈ 3 min en vivo). Sin Docker todo funciona en **modo degradado** (simulaciones del agente en memoria). Funciona en Colab |
    | **RAM aproximada** | < 500 MB sin stack · ≈ 1,2 GB con `core` + `metrics` |
    | **Prerrequisitos** | Módulos 09 (métricas), 10 (alertas básicas y dashboards), 13 (coste), 14 (calidad online) y 15 (regresión) |
    | **Hilo conductor** | SupportOps ya mide latencia, coste y calidad. Hoy les ponemos **objetivos**, **alertas que despiertan solo cuando importa**, un **runbook** y un **postmortem** |

    > ⚠️ **Honestidad sobre el laboratorio.** El tráfico y los incidentes son **simulados y deterministas** (`mock`): el agente real de SupportOps procesa 24 h de tickets con un fallo masivo
    > del proveedor LLM y una regresión de prompt inyectados, de modo que conocemos la verdad de cada alerta. Las ventanas del laboratorio en vivo están **comprimidas** (minutos en vez de horas); las
    > ventanas de producción (1 h/5 min, 6 h/30 min…) las tratamos con simulaciones y con aritmética.
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar esta lección podrás:

    1. **Definir** SLIs de un agente (disponibilidad, latencia, calidad, coste) como «eventos buenos / eventos válidos» y fijar un SLO realista con la línea base medida.
    2. **Calcular** presupuesto de error, *burn rate* y tiempo hasta agotarlo; derivar el 14,4 de las políticas de la SRE Workbook.
    3. **Implementar** alertas por *burn rate* multiventana (ventana larga **y** corta) y compararlas con un umbral fijo y con una sola ventana en detección, falsos positivos y tiempo de reajuste.
    4. **Dimensionar** ventanas para SLIs de poco volumen (calidad evaluada por muestreo) y entender por qué una regresión de calidad es una quema **lenta**.
    5. **Escribir** reglas de alerta de Grafana **provisionadas como código** (intervalo múltiplo de 10 s, vínculo alerta→panel en `annotations`) y probarlas con un incidente real en el stack.
    6. **Diseñar** una política de presupuesto de error, un runbook con árbol de diagnóstico y un esquema de guardia que no genere fatiga.
    7. **Redactar** un postmortem **sin culpa** con cifras sacadas de la telemetría (TTD, impacto, presupuesto consumido) y acciones comprobables.
    """)

    md("## 🔁 Conexión con módulos anteriores")
    md(details("1 · (Módulo 10) ¿Por qué el intervalo de un grupo de alertas de Grafana debe ser múltiplo de 10 s y cómo se enlaza una alerta con un panel?",
               "Porque el planificador de Grafana evalúa en ticks de 10 s: un intervalo como `15s` hace que Grafana no arranque. El enlace va en `annotations.__dashboardUid__` y `annotations.__panelId__` (el on-call llega a la gráfica que importa)."))
    md(details("2 · (Módulo 09) ¿Qué hace `rate()` sobre un *counter* de Prometheus y por qué el burn rate se calcula con cocientes de `rate()` y no con el valor bruto del contador?",
               "`rate()` convierte un contador monótono en «eventos por segundo» en una ventana; el contador bruto solo crece y no dice nada del ritmo actual. El SLI es `rate(buenos)/rate(totales)` sobre la ventana de la alerta (igual que en ML calculas una tasa por lote, no el acumulado histórico)."))
    md(details("3 · (Módulo 14) ¿Por qué la calidad se mide con una muestra y qué implica para un SLI de calidad?",
               "Porque evaluar cuesta (≈ 9× el coste de atender). Implica **poco volumen** por ventana: el SLI de calidad es ruidoso y necesita ventanas más largas y un mínimo de eventos."))
    md(details("4 · (Módulo 15) ¿Qué señal delató la regresión silenciosa y por qué ninguna alerta de latencia/errores la vio?",
               "La caída de groundedness por versión y la huella de comportamiento (menos herramientas por ticket). Latencia y errores no la ven porque la petición termina bien y más rápido."))

    code(boot("viz,otel"))
    code(IMPORTS + IMPORTS_16)
    code(DATA_16)

    # ------------------------------------------------------------------------------------------------------------- 1
    md("""
    ---
    # 1 · Intuición: el contrato de fiabilidad

    Un **SLO** (*Service Level Objective*) es una promesa interna, medible y revisable: «el 99 % de los tickets termina sin error cada mes». Su gracia no es el número sino lo que habilita:
    **un presupuesto de error** (el 1 % restante) que el equipo puede *gastar* en desplegar, experimentar y fallar, y una **alerta** que salta cuando ese presupuesto se consume a un ritmo peligroso — ni antes (ruido) ni después (clientes quemados).

    | Si vienes de… | Esto es como… | Lo que cambia |
    |---|---|---|
    | **ML** | Un umbral de métrica en producción (p. ej. AUC mínimo) | El umbral es una **tasa de eventos buenos** sobre una ventana y lleva un presupuesto asociado |
    | **Backend** | SLA/SLO de una API (p. ej. 99,9 % de peticiones < 300 ms) | Un agente necesita SLOs de **calidad** y **coste**, no solo de disponibilidad y latencia |
    | **SRE** | Google SRE: SLI → SLO → error budget → alertas por burn rate → postmortem | Es exactamente el mismo ciclo; lo nuevo son los SLIs |
    """)
    code('''
fig, ax = viz.canvas(12.5, 4.4, (0, 125), (0, 44))
P = viz.PALETTE
bs = [viz.box(ax, 1 + i * 20.5, 24, 18, 9, t, c, fontsize=8) for i, (t, c) in enumerate([("SLI\\neventos buenos / válidos", P["metrics"]), ("SLO\\nobjetivo 99 % / 30 d", P["traces"]), ("Presupuesto de error\\n(1 − objetivo)", P["warn"]),
                                                                                    ("Burn rate\\n= ritmo de gasto", P["metrics"]), ("Alerta multiventana\\npágina / ticket", P["error"]), ("Runbook +\\nguardia", P["logs"])])]
for a, b in zip(bs, bs[1:]): viz.arrow(ax, viz.right(a), viz.left(b))
b_pm = viz.box(ax, 41, 5, 40, 9, "Postmortem sin culpa → acciones → revisar SLO, alertas y runbook", P["profiles"], fontsize=9)
viz.arrow(ax, viz.bottom(bs[4]), viz.top(b_pm), "", P["profiles"]); viz.arrow(ax, viz.left(b_pm), (bs[0][0] + 9, 22.5), "", P["profiles"], rad=-0.35, dashed=True)
b_pol = viz.box(ax, 90, 5, 33, 9, "Política: presupuesto agotado\\n→ congelar despliegues", P["neutral"], fc="#f3f4f6", fontsize=8)
viz.arrow(ax, viz.top(bs[2]), (106, 14.3), "", P["neutral"], rad=-0.3, dashed=True)
ax.text(1, 40, "El ciclo SLO: medir → prometer → gastar → alertar → aprender", fontsize=10, fontweight="bold")
plt.show()
''')
    md(observe("""
    - El ciclo es **cerrado**: el postmortem retroalimenta los SLI, el objetivo, las alertas y el runbook. Un SLO que nunca se revisa se convierte en decoración.
    - El presupuesto de error es una **herramienta de negociación** entre producto y fiabilidad: con presupuesto, se despliega; sin presupuesto, se congela y se arregla. Hace objetiva una discusión que suele ser política.
    - En un agente, lo que consume presupuesto no es solo «caída del servicio»: puede ser una **regresión de calidad** o una **explosión de coste**; por eso hay un SLO por dimensión.
    """))

    # ------------------------------------------------------------------------------------------------------------- 2
    md(r"""
    ---
    # 2 · Teoría: SLI, SLO, presupuesto y burn rate

    **SLI** (indicador): \( \text{SLI} = \dfrac{\text{eventos buenos}}{\text{eventos válidos}} \) en una ventana. Dos decisiones de diseño: qué es un evento **válido** (¿cuentan los tickets de prueba?) y cuál es el **bueno**.

    **SLO** (objetivo): \( \text{SLI} \ge \text{objetivo} \) en un periodo \(T\) (típico: 28–30 días, móvil).

    **Presupuesto de error:** \( B = 1-\text{objetivo} \): la fracción de eventos válidos que pueden ser malos en \(T\). Con objetivo 99 % y 1 000 000 de tickets al mes, \(B\) = 10 000 tickets malos.

    **Burn rate** (ritmo de consumo) en una ventana \(w\): \( \text{burn}(w) = \dfrac{1-\text{SLI}(w)}{B} \). Un burn de 1 consume exactamente el presupuesto en \(T\); de 14,4 lo agota en \(T/14{,}4\).

    **Presupuesto consumido** manteniendo un burn \(r\) durante \(w\): \( \dfrac{r\cdot w}{T} \). El 14,4 de la quema rápida sale de fijar **«el 2 % del presupuesto de un mes en 1 hora»**: \( r = 0{,}02\cdot 720\,\text{h}/1\,\text{h} = 14{,}4 \).

    **✏️ Ejemplo resuelto (a mano, antes de ver código).** SupportOps atiende 2 tickets/min ≈ 86 400 al mes y fija un objetivo del 99 %: \(B\) = 1 % → **864 tickets malos al mes** como máximo.
    Una hora con 120 tickets de los que 24 fallan: SLI = 96 / 120 = 0,80 → malos = 20 % → burn = 0,20 / 0,01 = **20** (≥ 14,4). Si ese ritmo se mantuviera, el presupuesto duraría 720 h / 20 = **36 h**, y esa sola hora ya consumió 20 / 720 ≈ **2,8 %** del mes.
    Compruébalo con la tabla de la celda siguiente y repite la cuenta con un objetivo de 99,9 %: el mismo 20 % de fallos sería burn = 200.
    """)
    code('''
rows = []
for pol in GOOGLE_POLICIES:
    rows.append({"política": pol.name, "burn mínimo": pol.factor, "ventana larga": f"{pol.long_min // 60} h" if pol.long_min < 1440 else f"{pol.long_min // 1440} d", "ventana corta": f"{pol.short_min} min" if pol.short_min < 60 else f"{pol.short_min // 60} h",
                 "presupuesto consumido": f"{pol.budget_consumed():.0%}", "severidad": pol.severity, "tiempo hasta agotar todo el presupuesto": f"{30 * 24 / pol.factor:.0f} h"})
display(pd.DataFrame(rows).set_index("política"))
print("Comprobación: 14,4 × 1 h / 720 h =", 14.4 * 1 / 720, "· 6 × 6 h / 720 h =", 6 * 6 / 720, "· 1 × 72 h / 720 h =", 72 / 720)
''')
    md(observe("""
    - Las tres políticas de la SRE Workbook para un SLO a 30 días son: **14,4 / 1 h** (2 % del presupuesto, *página*), **6 / 6 h** (5 %, *página*) y **1 / 3 d** (10 %, *ticket*). Cada ventana corta es ≈ 1/12 de la larga.
    - Un burn alto con ventana corta detecta rápido lo grave; un burn bajo con ventana larga detecta lo lento que, sumado, también agota el presupuesto. **Hacen falta ambas**: una sola nunca cubre los dos extremos.
    - Con un objetivo de 99 %, \\(B\\) = 1 %: un burn de 14,4 equivale a un 14,4 % de tickets malos. Con un objetivo de 99,9 %, el mismo burn es un 1,44 %: el umbral absoluto depende del objetivo, el burn no.
    """))
    md(box("warn", "Cuidado: fórmulas y ventanas del laboratorio", """
    En el laboratorio en vivo (sección 7.1) las ventanas están **comprimidas** (5 min/1 min para la quema rápida, 15 min/3 min para la lenta) porque no podemos esperar una hora. Los **factores** (14,4 y 3) se mantienen:
    la aritmética «consumo = burn × ventana / periodo» sigue valiendo si interpretas el periodo como 30 min. En producción usa las ventanas de la tabla.
    """))

    # ------------------------------------------------------------------------------------------------------------- 3
    md("""
    ---
    # 3 · SLIs específicos de un agente

    | SLI | Evento válido | Evento bueno | Dónde se mide | Por qué es de *agente* |
    |---|---|---|---|---|
    | **Disponibilidad** | Ticket procesado | `status` ∈ {`ok`, `escalated`} (no error, degradado ni `max_steps`) | `supportops_agent_requests_total{supportops_status}` | Un «degradado» responde «problema técnico»: para el cliente es una caída |
    | **Latencia** | Ticket procesado | Duración de `invoke_agent` ≤ 5 s | `gen_ai_invoke_agent_duration_seconds_bucket{le="5.0"}` | Percentil de **extremo a extremo**, incluidas herramientas y reintentos |
    | **Calidad** | Ticket **evaluado** (muestra uniforme del 25 %) | `groundedness` ≥ 0,5 según el juez | `supportops_eval_results_total` (módulo 14) | Una respuesta rápida e inventada es un fallo |
    | **Coste** | Ticket procesado | Coste ≤ 0,0005 USD (precios ilustrativos) | `supportops_agent_request_cost_USD_bucket` (módulo 13) | Un bucle de herramientas es un incidente aunque «funcione» |

    Dos reglas para elegir SLIs: (1) que midan lo que **percibe el usuario**, no una causa interna (CPU del Collector no es un SLI); (2) que sean **expresables como ratio bueno/válido**, para que el burn rate se calcule igual en todos.
    La calidad usa una **muestra uniforme** (no la estratificada del módulo 14) porque el SLI debe ser simple y sin sesgo: la muestra «de caza» (errores, valoraciones negativas) es para investigar, la «de medir» es para el SLO.
    """)
    code('''
def rolling(g, t, w=30):
    gg, tt = trailing_sum(g, w), trailing_sum(t, w)
    with np.errstate(divide="ignore", invalid="ignore"): return np.where(tt >= 5, gg / tt, np.nan)
fig, axes = plt.subplots(2, 2, figsize=(13, 6.4), sharex=True)
hours = np.arange(NB) / 60
for ax, (name, slo) in zip(axes.ravel(), DEFAULT_SLOS.items()):
    g, t = SERIES[name]
    ax.axvspan(*np.array(TRUTH["regression"]) / 60, color=viz.PALETTE["warn"], alpha=0.12); ax.axvspan(*np.array(TRUTH["outage"]) / 60, color=viz.PALETTE["error"], alpha=0.2)
    ax.plot(hours, rolling(g, t), color=viz.PALETTE["traces"], lw=1.3); ax.axhline(slo.objective, color=viz.PALETTE["ok"], ls="--", label=f"objetivo {slo.objective:.0%}")
    ax.set_title(f"SLI {name} (media móvil 30 min)"); ax.set_ylim(max(0.3, min(np.nanmin(rolling(g, t)) - 0.02, slo.objective - 0.05)), 1.005); ax.legend(loc="lower left", fontsize=8)
for ax in axes[1]: ax.set_xlabel("hora del día (simulada)")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - La franja roja (incidente del proveedor 10:00-10:45) hunde la **disponibilidad** muy por debajo del objetivo y, curiosamente, deja la **latencia** igual o mejor (los errores son rápidos). Mirar solo una dimensión da una historia incompleta.
    - La franja amarilla (regresión de prompt, 6:00-14:00) **no toca** disponibilidad ni latencia: solo se ve en el SLI de **calidad**, que cae durante 8 horas por debajo del objetivo. Es el patrón del módulo 15 convertido en SLO.
    - El **coste** apenas se mueve en este día: un SLO que casi nunca se acerca al umbral protege contra algo que *no ha ocurrido hoy* (bucles, cambio de modelo, módulo 13). Tener un SLI «aburrido» es lo normal y deseable.
    """))
    code('''
rows = []
for name, slo in DEFAULT_SLOS.items():
    g, t = SERIES[name]
    month_events = t.sum() * 30                         # el presupuesto del MES: si todos los días fueran como hoy, ¿qué fracción del presupuesto mensual se gasta hoy?
    rep = budget_report(g.sum(), t.sum(), slo.objective)
    rows.append({"SLO": name, "objetivo": f"{slo.objective:.1%}", "SLI del día": g.sum() / t.sum(), "eventos malos": int(rep["bad"]), "presupuesto mensual (eventos malos)": int(slo.budget * month_events),
                 "% del presupuesto MENSUAL gastado hoy": 100 * rep["bad"] / (slo.budget * month_events), "burn medio del día": rep["avg_burn_rate"]})
BR = pd.DataFrame(rows).set_index("SLO"); display(BR.round(3))
''')
    md(observe("""
    - Un solo día malo puede gastar buena parte del presupuesto **mensual**: la disponibilidad se lleva ≈ 12 % del mes en un día con 45 minutos de incidente. Con ocho días así el SLO estaría incumplido.
    - Fíjate en la columna «burn medio del día»: la calidad quema por encima de 1 **todo el día** aunque el valor absoluto parezca pequeño; la disponibilidad lo hace de golpe. Son dos *formas* de gastar presupuesto que piden alertas distintas (secciones 4-5).
    """))

    # ------------------------------------------------------------------------------------------------------------- 4
    md("""
    ---
    # 4 · Alertar por burn rate (a mano) y por qué una ventana no basta

    Implementamos el cálculo (sin librería): suma móvil de buenos y totales en la ventana, ratio de malos y división por el presupuesto. Después comparamos **cuatro estrategias** sobre el mismo día:

    | Estrategia | Regla |
    |---|---|
    | **Umbral fijo** (anti-patrón) | tasa de error en 5 min > 5 % |
    | **Burn corto solo** | burn(5 min) ≥ 14,4 |
    | **Burn largo solo** | burn(1 h) ≥ 14,4 |
    | **Multiventana** | burn(1 h) ≥ 14,4 **y** burn(5 min) ≥ 14,4 |
    """)
    code('''
def burn_by_hand(good, total, width, objective, min_events=5):
    g = np.convolve(good, np.ones(width), "full")[: len(good)]; t = np.convolve(total, np.ones(width), "full")[: len(total)]      # suma móvil (ventana de `width` minutos)
    bad_ratio = np.where(t >= min_events, 1 - g / np.maximum(t, 1), np.nan)
    return bad_ratio / (1 - objective)
g, t = SERIES["availability"]; slo = DEFAULT_SLOS["availability"]
assert np.allclose(np.nan_to_num(burn_by_hand(g, t, 60, slo.objective)), np.nan_to_num(burn_series(g, t, 60, slo.objective)))          # a mano = librería
b5, b60 = burn_by_hand(g, t, 5, slo.objective), burn_by_hand(g, t, 60, slo.objective)
strat = {"Umbral fijo (5 min > 5 %)": threshold_fire_series(g, t, 0.05, 5), "Burn corto solo (5 min)": np.nan_to_num(b5) >= 14.4, "Burn largo solo (1 h)": np.nan_to_num(b60) >= 14.4,
         "Multiventana (1 h y 5 min)": fire_series(g, t, slo.objective, GOOGLE_POLICIES[0])}
inc_end = int(TRUTH["outage"][1]); res = []
for k, f in strat.items():
    q = alert_quality(f, OUT, reset_slack_min=0)
    late = int(f[inc_end:].sum()); outside = int((f & ~OUT).sum())
    res.append({"estrategia": k, "detecta": q["detected"], "TTD (min)": q["ttd_min"], "minutos disparada": q["fired_intervals"], "fuera del incidente (min)": outside, "tras acabar el incidente (min)": late})
display(pd.DataFrame(res).set_index("estrategia"))
fig, ax = plt.subplots(figsize=(11, 3.2))
for i, (k, f) in enumerate(strat.items()):
    ax.fill_between(hours, i, i + 0.8, where=f, color=viz.PALETTE["error"], step="mid"); ax.text(8.55, i + 0.35, k, fontsize=8, va="center")
ax.axvspan(*np.array(TRUTH["outage"]) / 60, color=viz.PALETTE["error"], alpha=0.15); ax.set_yticks([]); ax.set_xlabel("hora"); ax.set_xlim(8.5, 13); ax.set_title("Cuándo dispara cada estrategia (franja = incidente real)")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **Umbral fijo**: detecta al instante, pero con 2-4 tickets por minuto basta un par de fallos seguidos para disparar: ≈ 70 minutos de alerta **fuera** del incidente en un solo día. Es el generador de ruido que acaba con la guardia.
    - **Burn largo solo (1 h)**: detecta a los ≈ 8 min (necesita acumular un 14,4 % de malos en la ventana) y **sigue disparada ≈ 45 min después de que el incidente termine** (la ventana larga recuerda): el on-call recibe una alerta de algo que ya está arreglado.
    - **Burn corto solo (5 min)**: detecta y se reajusta rápido, pero sigue disparando por ráfagas ajenas al incidente (≈ 10 min fuera): sin ventana larga, un blip de 5 minutos dispara igual.
    - **Multiventana**: detecta igual de pronto que la larga (≈ 8 min) y la corta **apaga la alerta en cuanto el problema cesa** (≈ 4 min tras el fin frente a ≈ 45): es la razón de ser del diseño de la SRE Workbook.
    """))
    md("""
    ## 4.1 Monte Carlo: un mes con ruido

    El día de ejemplo es un solo caso. Simulamos **40 meses** (binomial por minuto; el agente completo para 40 × 43 200 min sería demasiado) con 3 incidentes reales por mes de gravedad aleatoria y una **ráfaga corta cada día** (3 min al 50 % de fallos) que un buen sistema de alertas no debe convertir en página.
    """)
    code('''
def month(seed):
    rng = np.random.default_rng(1000 + seed)
    inc = [(int(rng.integers(1, 29)), float(rng.uniform(0, 22)), float(rng.uniform(20, 120)), float(rng.uniform(0.12, 0.7))) for _ in range(3)]
    blips = [(d, float(rng.uniform(0, 23.5)), 3.0, 0.5) for d in range(30)]
    good, total = simulate_month(seed, incidents=inc + blips)
    real = np.zeros(len(good), bool)
    for d, h, dur, r in inc: real[int(d * 1440 + h * 60): int(d * 1440 + h * 60 + dur) + 60] = True               # incidente + 60 min de holgura de reajuste
    return good, total, real, inc
def episodes(mask): idx = np.where(mask)[0]; return [] if not len(idx) else np.split(idx, np.where(np.diff(idx) > 30)[0] + 1)
STRATS = {"umbral fijo (5 min > 5 %)": lambda g, t: threshold_fire_series(g, t, 0.05, 5), "burn 5 min solo": lambda g, t: np.nan_to_num(burn_series(g, t, 5, 0.99)) >= 14.4,
          "burn 1 h solo": lambda g, t: np.nan_to_num(burn_series(g, t, 60, 0.99)) >= 14.4, "multiventana (1 h y 5 min)": lambda g, t: fire_series(g, t, 0.99, GOOGLE_POLICIES[0])}
agg = {k: {"incidentes detectados": 0, "incidentes": 0, "páginas": 0, "páginas falsas": 0, "tarde": 0} for k in STRATS}
for sd in range(40):
    g, t, real, inc = month(sd)
    for k, fn in STRATS.items():
        f = fn(g, t); eps = episodes(f)
        agg[k]["páginas"] += len(eps); agg[k]["páginas falsas"] += sum(not real[e].any() for e in eps)
        for d, h, dur, r in inc:
            agg[k]["incidentes"] += 1; s0 = int(d * 1440 + h * 60); agg[k]["incidentes detectados"] += bool(f[s0: s0 + int(dur) + 5].any()); agg[k]["tarde"] += int(f[s0 + int(dur): s0 + int(dur) + 60].sum())
M = pd.DataFrame(agg).T
M["detección"] = M["incidentes detectados"] / M["incidentes"]; M["páginas/semana"] = M["páginas"] / (40 * 30 / 7); M["% de páginas falsas"] = M["páginas falsas"] / M["páginas"]
M["min. de alerta tras acabar (por incidente)"] = M["tarde"] / M["incidentes"]
display(M[["detección", "páginas/semana", "% de páginas falsas", "min. de alerta tras acabar (por incidente)"]].round(3))
fig, axes = plt.subplots(1, 2, figsize=(12, 3.6))
axes[0].bar(range(4), M["detección"], color=viz.PALETTE["traces"]); axes[0].set_xticks(range(4), [k.replace(" (", "\\n(") for k in M.index], fontsize=7); axes[0].set_ylim(0, 1.05); axes[0].set_title("Incidentes reales detectados")
axes[1].bar(range(4), M["páginas/semana"] * (1 - M["% de páginas falsas"]), color=viz.PALETTE["ok"], label="páginas reales"); axes[1].bar(range(4), M["páginas/semana"] * M["% de páginas falsas"], bottom=M["páginas/semana"] * (1 - M["% de páginas falsas"]), color=viz.PALETTE["error"], label="páginas FALSAS")
axes[1].set_xticks(range(4), [k.replace(" (", "\\n(") for k in M.index], fontsize=7); axes[1].legend(); axes[1].set_title("Páginas por semana de guardia")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - El **umbral fijo** detecta todo, pero **≈ 99 % de sus páginas son falsas** (≈ 66 por semana, con las ráfagas diarias): el camino directo a la fatiga de alertas y a ignorar la siguiente página, que sí era real. El **burn de 5 min solo** mejora pero aún da ≈ 11 páginas/semana, ≈ 93 % falsas.
    - Las dos políticas con ventana larga (1 h solo y multiventana) **eliminan las páginas falsas** (≈ 0,6 páginas/semana, todas reales) y detectan los incidentes que gastan presupuesto de verdad; el ≈ 8 % restante son incidentes tan suaves (≈ 12-14 % de fallos) que el burn no llega a 14,4 y no hace falta despertar a nadie. Detectar un 100 % no es el objetivo: es detectar lo que **agota** el presupuesto.
    - ¿Dónde está entonces la ventaja de la multiventana sobre la ventana larga sola? En la última columna: **sigue disparada muchos menos minutos después de acabar el incidente** (la corta la apaga). El recuento de páginas no ve ese coste; la guardia sí (alertas «fantasma» de algo ya resuelto).
    - Mide siempre tu política con **páginas por semana, % de acciones útiles y tiempo de reajuste** — la métrica de salud de la guardia.
    """))

    # ------------------------------------------------------------------------------------------------------------- 5
    md("""
    ---
    # 5 · La calidad: una quema lenta con poco volumen

    La regresión de prompt (6:00-14:00) consume presupuesto de calidad **sostenidamente** por encima de 1 pero muy por debajo de 14,4. Dos problemas: (a) ¿qué política la ve? y (b) el SLI de calidad se mide en una **muestra** (25 %): pocos eventos por ventana.
    """)
    code('''
gq, tq = SERIES["quality"]; slq = DEFAULT_SLOS["quality"]
vol = [(w, tq[300:300 + w].sum()) for w in (5, 15, 30, 60, 180, 360)]
fig, axes = plt.subplots(1, 2, figsize=(13, 3.8))
axes[0].plot([w for w, _ in vol], [v for _, v in vol], "o-", color=viz.PALETTE["metrics"]); axes[0].axhline(30, color=viz.PALETTE["error"], ls=":"); axes[0].text(6, 33, "≈ 30 eventos: mínimo razonable", fontsize=8)
axes[0].set_xscale("log"); axes[0].set_xlabel("ventana (min)"); axes[0].set_ylabel("evaluaciones en la ventana"); axes[0].set_title("Volumen del SLI de calidad por ventana")
for w, col_ in ((30, viz.PALETTE["traces"]), (180, viz.PALETTE["profiles"]), (360, viz.PALETTE["metrics"])):
    b = burn_series(gq, tq, w, slq.objective, min_events=30); axes[1].plot(hours, b, label=f"ventana {w} min", color=col_)
axes[1].axhline(1, color=viz.PALETTE["ok"], ls="--", label="ritmo sostenible (1×)"); axes[1].axhline(6, color=viz.PALETTE["error"], ls=":", label="6×"); axes[1].axvspan(*np.array(TRUTH["regression"]) / 60, color=viz.PALETTE["warn"], alpha=0.12)
axes[1].set_xlabel("hora"); axes[1].set_ylabel("burn rate de calidad"); axes[1].set_ylim(0, 12); axes[1].legend(fontsize=7); axes[1].set_title("Burn rate de calidad con distintas ventanas")
plt.tight_layout(); plt.show()
reg = slice(int(TRUTH["regression"][0]) + 60, int(TRUTH["regression"][1]))
print(f"durante la regresión: SLI de calidad {gq[reg].sum() / tq[reg].sum():.3f} (objetivo {slq.objective}) -> burn medio {(1 - gq[reg].sum() / tq[reg].sum()) / slq.budget:.1f}× · fuera: {gq[:300].sum() / tq[:300].sum():.3f}")
for pol in GOOGLE_POLICIES:
    f = fire_series(gq, tq, slq.objective, pol); print(f"  {pol.name:12s} (×{pol.factor:g}, {pol.long_min} min / {pol.short_min} min): dispara {int(f.sum())} min" + (f" · primera vez en el minuto {int(np.argmax(f))}" if f.any() else ""))
''')
    md(observe("""
    - Con el 25 % de muestreo y ≈ 2 tickets/min, una ventana de 5 min tiene ≈ 2-3 evaluaciones y una de 30 min, ≈ 15: **el burn de calidad con ventanas cortas es puro ruido** (por eso `min_events`). Para tener ≈ 30 eventos hacen falta ventanas de ≈ 1 h.
    - Durante la regresión el burn de calidad está en ≈ 4×: **muy por encima de 1 pero por debajo de 6 y de 14,4**. Las políticas de página (14,4×/1 h y 6×/6 h) **no disparan nunca**; solo la de ticket (1×) lo detecta, ≈ 45 min después del despliegue (en este día de 24 h la ventana de «3 días» equivale a todo el historial). Es una alerta de **ticket**. Está bien: la regresión consume ≈ 4-5 % del presupuesto mensual en 8 horas y el remedio no es despertar a nadie sino **bloquear el despliegue en canario** (módulo 15) y revisar por la mañana.
    - Moraleja de diseño: la severidad la decide **cuánto presupuesto quema y con qué urgencia puedes actuar**, no lo «grave» que suene la métrica.
    """))
    md(box("exp", "Experimento: SLI sobre una métrica ruidosa", """
    Antes de poner un SLO sobre la calidad del juez, mide la tasa de calidad **en una semana sana**: si el juez tiene un 3 % de falsos positivos (módulo 14) y tu objetivo es 98 %, el SLO se incumple solo por el juez.
    Fija el objetivo **por debajo de la línea base medida** (aquí 95 %, con línea base ≈ 96,7 %) y calibra el juez (Rogan–Gladen) si la precisión importa.
    """))

    # ------------------------------------------------------------------------------------------------------------- 6
    md("""
    ---
    # 6 · Política de presupuesto de error: un mes completo

    El presupuesto se *gasta*: incidentes, despliegues fallidos, mantenimiento. Una **política** acordada de antemano decide qué pasa cuando se agota (típico: congelar despliegues de funcionalidades y dedicar el equipo a fiabilidad). Simulamos un mes con cuatro incidentes.
    """)
    code('''
incs = [(4, 10, 45, 0.5), (13, 2, 90, 0.2), (21, 15, 30, 0.7), (26, 9, 25, 0.35)]
g, t = simulate_month(SEED, incidents=incs)
slo_a = DEFAULT_SLOS["availability"]
bad_cum = np.cumsum(t - g); allowed_total = slo_a.budget * t.sum()
remaining = 1 - bad_cum / allowed_total
days = np.arange(len(g)) / 1440
fig, ax = plt.subplots(figsize=(10, 3.8))
ax.plot(days, remaining * 100, color=viz.PALETTE["traces"], lw=2); ax.axhline(0, color=viz.PALETTE["error"], ls="--"); ax.fill_between(days, remaining * 100, 0, where=remaining < 0, color=viz.PALETTE["error"], alpha=0.2)
for d, h, dur, r in incs: ax.axvline(d + h / 24, color=viz.PALETTE["warn"], ls=":"); ax.text(d + h / 24 + 0.1, 92, f"{dur} min\\n{r:.0%}", fontsize=7)
exhaust = np.argmax(remaining < 0) / 1440 if (remaining < 0).any() else None
if exhaust: ax.axvline(exhaust, color=viz.PALETTE["error"]); ax.text(exhaust + 0.2, -20, f"presupuesto agotado\\n día {exhaust:.1f} → congelar despliegues", fontsize=8, color=viz.PALETTE["error"])
ax.set_xlabel("día del mes"); ax.set_ylabel("presupuesto restante (%)"); ax.set_title("Presupuesto de disponibilidad restante a lo largo del mes")
plt.tight_layout(); plt.show()
rep = budget_report(g.sum(), t.sum(), slo_a.objective)
print(f"SLI del mes {rep['sli']:.4f} (objetivo {slo_a.objective:.2%}) · consumido {rep['consumed']:.0%} del presupuesto · restante {rep['remaining']:.0%}")
for i, (d, h, dur, r) in enumerate(incs):
    s0 = int(d * 1440 + h * 60); bad = (t[s0:s0 + dur] - g[s0:s0 + dur]).sum(); print(f"  incidente {i + 1} (día {d}, {dur} min al {r:.0%}): {bad:.0f} tickets malos = {bad / allowed_total:.1%} del presupuesto del mes")
''')
    md(observe("""
    - Cada incidente es un **escalón** en la curva (entre el 2 % y el 7 % del presupuesto cada uno), pero la pendiente entre incidentes —el consumo de fondo, los fallos «normales»— se lleva **más que los cuatro incidentes juntos** (≈ 41 puntos frente a ≈ 18). Con un fondo del 0,4 % de fallos y un objetivo del 99 %, el 40 % del presupuesto ya está comprometido antes del primer incidente: **mide el fondo** antes de prometer un objetivo.
    - Aquí el mes termina con ≈ 40 % de presupuesto: no se activa la congelación. Con un incidente más grande, o un fondo algo peor, la curva cruzaría el 0 y la política diría «congelar» (la celda dibuja la marca si ocurre).
    - Una política útil es **explícita y escalonada**: <50 % restante → revisar despliegues arriesgados; <25 % → solo cambios de fiabilidad; agotado → congelación y postmortem obligatorio. Se acuerda con producto **antes** del primer incidente.
    """))

    # ------------------------------------------------------------------------------------------------------------- 7
    md("""
    ---
    # 7 · Alertas de Grafana provisionadas como código

    El módulo 10 provisionó alertas de **síntomas** (tasa de error, p95). Hoy provisionamos alertas de **SLO**: 2 políticas × 4 SLOs = 8 reglas, generadas por `supportops.slo.grafana_burn_rule` (el mismo código que prueban las pruebas del paquete) en
    `stack/grafana/provisioning/alerting/16-slo-alerts.yaml`. Estructura de cada regla:

    | Pieza | Qué hace |
    |---|---|
    | `A` y `B` | Dos consultas PromQL **instantáneas**: burn rate con la ventana **larga** y con la **corta** |
    | `C` y `D` | `reduce` (último valor, descartando NaN) de A y B |
    | `E` | `math`: `$C > f && $D > f` — las **dos** ventanas por encima del factor |
    | `F` | `threshold` de E (`> 0`) → **condition** de la regla |
    | `for` | `0s` en página (la multiventana ya amortigua) · `1m` en ticket |
    | `annotations.__dashboardUid__` / `__panelId__` | Enlace alerta → panel del dashboard `slo-agente` |
    | `annotations.runbook_url` | El runbook de la alerta |
    | `labels.severity` | `page` o `ticket`: la política de notificación (módulo 10) enruta por esta etiqueta |
    | `noDataState: OK` | Sin tráfico no hay quema (la alerta de «agente inactivo» es otra) |
    | grupo `interval: 30s` | **Múltiplo de 10 s**: el planificador de Grafana evalúa en ticks de 10 s |
    """)
    code('''
y = yaml.safe_load(open(ROOT / "stack" / "grafana" / "provisioning" / "alerting" / "16-slo-alerts.yaml"))
grp = y["groups"][0]
print("grupo:", grp["name"], "· intervalo:", grp["interval"], "· múltiplo de 10 s:", int(grp["interval"].rstrip("s")) % 10 == 0, "· reglas:", len(grp["rules"]))
display(pd.DataFrame([{"regla": r["title"], "severidad": r["labels"]["severity"], "for": r["for"], "dashboard": r["annotations"]["__dashboardUid__"], "panel": r["annotations"]["__panelId__"]} for r in grp["rules"]]).set_index("regla"))
r0 = grp["rules"][0]
print("\\nConsulta A (burn largo) de", r0["title"], ":\\n ", r0["data"][0]["model"]["expr"], "\\nMath E:", r0["data"][4]["model"]["expression"])
try:
    rules_yaml([r0], interval="15s")
except ValueError as e:
    print("\\nintervalo de 15 s ->", e)
''')
    md(observe("""
    - Las 8 reglas apuntan a los paneles `Burn rate · <slo>` (ids 12-15) del dashboard `16-slos.json`: el on-call llega a la gráfica con las **mismas consultas** que disparan la alerta. Mantener alerta y panel sincronizados se hace con código (`burn_promql`), no a mano.
    - `rules_yaml` rechaza un intervalo que no sea múltiplo de 10 s: es un error clásico (Grafana ni arranca con `15s`; módulo 10).
    - Las ventanas del laboratorio (5 m/1 m y 15 m/3 m) son parámetros de `LAB_POLICIES`; para producción se cambia por `GOOGLE_POLICIES` y se regeneran.
    """))
    md("## 7.1 Probarlas con un incidente real")
    md("""
    Un SLO sin prueba es una creencia. Con el stack arriba, `LivePipeline` envía ≈ 100 s de tráfico a 5 tickets/s con un **fallo masivo del proveedor LLM** entre los 30 s y los 65 s (`Incident("llm_provider_outage", "llm_error", …)`), mientras un hilo consulta el estado de las reglas en Grafana cada 5 s.
    Después esperamos a que el burn de la ventana corta baje y la alerta se **resuelva**. Duración total ≈ 3 min. (Si el stack acaba de arrancar, las reglas necesitan unos segundos para cargarse; si no ves nada, `POST /api/admin/provisioning/alerting/reload`.)
    """)
    code('''
from supportops.regression import LivePipeline
from supportops.quality_eval import RateSampler
from supportops.traffic import Incident
LIVE_S = 100 if FAST_DEV_RUN else 180
OUT_LAB = (30, 65) if FAST_DEV_RUN else (50, 110)
STATES, STOP = [], threading.Event()
def poll_rules(t0):
    while not STOP.is_set():
        try:
            d = backends.grafana_api("/api/prometheus/grafana/api/v1/rules")
            for g_ in d["data"]["groups"]:
                if g_["name"] == "supportops-slo": STATES.append((time.time() - t0, {r["name"]: r["state"] for r in g_["rules"]}))
        except Exception as e: pass
        STOP.wait(5)
if LIVE:
    lp = LivePipeline(("v1",), mode="otlp", sampler=RateSampler(0.3), metric_interval_s=5)
    tk = generate_tickets(LIVE_S * 5, seed=SEED, duration_s=LIVE_S, fault_rates=BASELINE_FAULTS, start_s=0.0,
                          incidents=[Incident("llm_provider_outage", "llm_error", OUT_LAB[0], OUT_LAB[1], prob=0.7, params={"status": 503, "persistent": True})])
    T_START = time.time(); th = threading.Thread(target=poll_rules, args=(T_START,)); th.start()
    lp.run_live(tk, LIVE_S); print(f"tráfico enviado ({LIVE_S}s); esperando a que la alerta se resuelva…")
    time.sleep(75); STOP.set(); th.join(); lp.close()
    first = {}
    for ts, st in STATES:
        for name, s_ in st.items():
            if s_ in ("firing", "pending") and name not in first: first[name] = round(ts)
    print("primera vez en firing/pending (s desde el inicio):", first, "· el incidente empezó en el s", OUT_LAB[0])
else:
    print("Modo degradado: levanta el stack con:", STACK.command)
''')
    code('''
if LIVE:
    from supportops.otel_metrics import prom_range
    fig, axes = plt.subplots(2, 1, figsize=(11, 5.6), sharex=True)
    for name, expr, col_ in (("burn 5 min", burn_promql(DEFAULT_SLOS["availability"], "5m"), viz.PALETTE["traces"]), ("burn 1 min", burn_promql(DEFAULT_SLOS["availability"], "1m"), viz.PALETTE["metrics"])):
        for r in prom_range(expr, minutes=7, step_s=5):
            axes[0].plot([x - T_START for x in r["t"]], r["v"], label=name, color=col_)
    axes[0].axhline(14.4, color=viz.PALETTE["error"], ls=":"); axes[0].axvspan(*OUT_LAB, color=viz.PALETTE["error"], alpha=0.12); axes[0].set_ylabel("burn rate disponibilidad"); axes[0].legend(); axes[0].set_title("Burn rate de disponibilidad (Prometheus) y estado de las alertas (Grafana)")
    names = sorted({n for _, st in STATES for n in st if "availability" in n or "latency" in n})
    for i, n in enumerate(names):
        xs = [ts for ts, st in STATES]; on = [st.get(n) == "firing" for ts, st in STATES]
        axes[1].fill_between(xs, i, i + 0.8, where=on, color=viz.PALETTE["error"], step="mid"); axes[1].text(2, i + 0.35, n, fontsize=7, va="center")
    axes[1].axvspan(*OUT_LAB, color=viz.PALETTE["error"], alpha=0.12); axes[1].set_yticks([]); axes[1].set_xlabel("segundos desde el inicio"); axes[1].set_xlim(0, LIVE_S + 75)
    plt.tight_layout(); plt.show()
    al = backends.grafana_api("/api/alertmanager/grafana/api/v2/alerts")
    print("alertas activas en el Alertmanager de Grafana ahora:", [(a["labels"]["alertname"], a["labels"].get("severity")) for a in al][:6])
''')
    md(observe("""
    - En la gráfica superior el burn de 1 min sube en cuanto empieza el fallo y el de 5 min lo sigue: la alerta de **página** (`fast-burn`) pasa a *firing* cuando **ambos** superan 14,4 y vuelve a *normal* poco después de acabar el incidente, cuando el burn de 1 min cae (la ventana corta apaga la alerta). Los tiempos reales dependen de que Prometheus raspa cada 15 s y Grafana evalúa cada 30 s: detectar en ≈ 1 min en laboratorio equivale a minutos en producción.
    - La alerta de **latencia** no se activa (los errores son rápidos): cada SLO ve lo suyo. La de **disponibilidad lenta** (ticket, ventana de 15 min) dispara más tarde, tras el `for: 1m`, y **tarda más en resolverse**: recuerda 15 min (si repites el experimento antes de que pasen, la verás ya activa al empezar: todavía «recuerda» el incidente anterior).
    - **Notificación:** el punto de contacto del módulo 10 (webhook al endpoint de salud del Collector) recibe las alertas con `severity=page`; en producción sería PagerDuty/Slack. Las alertas activas se ven en el Alertmanager de Grafana (última línea).
    """))
    md("""
    ### El dashboard `16-slos`

    `stack/grafana/dashboards/16-slos.json` (uid `slo-agente`): 4 `stat` con el SLI de cada SLO, 4 `gauge` con el **presupuesto restante**, 4 series de **burn rate** (ventana larga, corta y lenta con umbrales 3 y 14,4), el panel de **alertas** en firing y, de contexto, las trazas con error (Tempo) y los logs de aviso/error (Loki).
    **Qué debes ver:** los SLIs en verde en tráfico sano; durante el incidente, los gauges de disponibilidad caen a negativo y la serie de burn cruza la línea roja; las trazas con error enlazan con el span que falló.
    """)

    # ------------------------------------------------------------------------------------------------------------- 8
    md("""
    ---
    # 8 · Runbooks, guardia y comunicación

    Una alerta sin runbook obliga a pensar a las 3 de la madrugada. Un buen runbook es **corto, ordenado por urgencia y orientado a mitigar** (no a diagnosticar a fondo):

    1. **Qué significa** la alerta y qué impacto tiene (en lenguaje del negocio).
    2. **Primeros 5 minutos**: tres comprobaciones con enlaces/consultas exactas (dashboard, PromQL, TraceQL).
    3. **Árbol de diagnóstico** (síntoma → causa probable → acción).
    4. **Mitigación primero** (rollback, conmutación a reserva, degradar a humano), causa raíz después.
    5. **Escalado**: a quién, cuándo y con qué criterio de severidad.
    """)
    code('''
display(Markdown((ROOT / "16_slos_alertas_incidentes" / "runbooks" / "slo-availability-fast-burn.md").read_text(encoding="utf-8")))
''')
    md("""
    ## 8.1 La guardia sostenible

    | Severidad | Criterio | Respuesta | Canal |
    |---|---|---|---|
    | **SEV-1** | > 50 % de tickets afectados durante > 15 min, o fuga de datos | Todos los implicados, comunicación a clientes | Página + canal de incidentes |
    | **SEV-2** | Quema rápida de un SLO (14,4×) | Guardia primaria, mitigar en < 30 min | Página |
    | **SEV-3** | Quema lenta (calidad, coste) | Siguiente día laborable | Ticket |

    - **Carga**: el libro *Site Reliability Engineering* (Google, cap. 11 «Being On-Call») orienta a que el equipo no gestione muchas más de un par de incidentes por turno; si tus páginas semanales superan lo que la guardia puede *resolver bien*, reduce ruido antes de añadir gente.
    - **Métrica de salud de la guardia**: páginas/semana, **% accionables** (¿hizo falta intervenir?), tiempo de reconocimiento y tiempo de mitigación.
    - **Rotación y secundario**: primaria + secundaria; traspaso escrito; tras un SEV-1 la persona de guardia descansa.
    - **Comunicación**: un canal de incidentes con un/a responsable de coordinación distinto/a de quien arregla, actualizaciones a horas fijas, y mensaje a clientes en lenguaje llano.
    """)

    # ------------------------------------------------------------------------------------------------------------- 9
    md("""
    ---
    # 9 · Simular el incidente y escribir el postmortem

    Con los datos del día (la verdad conocida: incidente del proveedor 10:00-10:45) calculamos las cifras del postmortem **desde la telemetría**: cuándo saltó la alerta, cuántos tickets se perdieron y cuánto presupuesto consumió.
    """)
    code('''
g, t = SERIES["availability"]; sl = DEFAULT_SLOS["availability"]
fire = fire_series(g, t, sl.objective, GOOGLE_POLICIES[0])
o0, o1 = (int(x) for x in TRUTH["outage"])
t_detect = int(np.argmax(fire & (np.arange(NB) >= o0 - 5)))
hh = lambda m: f"{int(m) // 60:02d}:{int(m) % 60:02d}"
bad_inc = int((t[o0:o1] - g[o0:o1]).sum()); tot_inc = int(t[o0:o1].sum())
budget_month = sl.budget * t.sum() * 30
last_fire = int(np.where(fire)[0][-1])
fig, axes = plt.subplots(2, 1, figsize=(11, 5.2), sharex=True)
axes[0].plot(hours, 1 - np.where(t > 0, g / np.maximum(t, 1), np.nan), color=viz.PALETTE["error"], lw=0.8, alpha=0.6); axes[0].set_ylabel("fracción de tickets malos (por minuto)"); axes[0].set_title("Cronología del incidente del proveedor LLM")
axes[1].plot(hours, np.nan_to_num(burn_series(g, t, 60, sl.objective)), label="burn 1 h", color=viz.PALETTE["traces"]); axes[1].plot(hours, np.nan_to_num(burn_series(g, t, 5, sl.objective)), label="burn 5 min", color=viz.PALETTE["metrics"], lw=1)
axes[1].axhline(14.4, color=viz.PALETTE["error"], ls=":"); axes[1].set_ylabel("burn rate"); axes[1].legend(loc="upper right", fontsize=8); axes[1].set_xlabel("hora"); axes[1].set_xlim(9, 13)
for ax in axes:
    ax.axvspan(o0 / 60, o1 / 60, color=viz.PALETTE["error"], alpha=0.1)
    ax.axvline(t_detect / 60, color=viz.PALETTE["ok"], ls="--"); ax.axvline(last_fire / 60, color=viz.PALETTE["neutral"], ls="--")
axes[0].text(t_detect / 60 + 0.02, 0.9, f"alerta {hh(t_detect)}", fontsize=8, color=viz.PALETTE["ok"]); axes[0].text(last_fire / 60 + 0.02, 0.75, f"alerta resuelta {hh(last_fire)}", fontsize=8)
plt.tight_layout(); plt.show()
facts = {"ttd": t_detect - o0, "start": hh(o0), "end": hh(o1), "detect": hh(t_detect), "resolved": hh(last_fire), "bad": bad_inc, "total": tot_inc, "budget_pct": 100 * bad_inc / budget_month}
print(facts)
''')
    md(observe("""
    - **TTD** (tiempo hasta detectar) ≈ 8 min: no es «instantáneo» porque la política exige acumular un 14,4 % de tickets malos en la ventana larga. Si eso es inaceptable para el negocio, la palanca es **bajar el factor o acortar la ventana larga** (a costa de más falsas alarmas) o añadir una sonda sintética que mida cada minuto.
    - Cada minuto de incidente cuesta tickets reales; el postmortem debe traducirlo a **tickets perdidos y a presupuesto consumido** (aquí, ≈ 10 % del presupuesto mensual de disponibilidad en 45 minutos).
    - La alerta se resuelve poco después de que acaba el incidente gracias a la ventana corta: ese es el *tiempo de reajuste*.
    """))
    code('''
pm = {
    "title": "El proveedor de LLM devuelve 503: el 65 % de los tickets fallan durante 45 min",
    "severity": "SEV-2", "status": "borrador", "authors": "equipo de plataforma de SupportOps",
    "summary": f"Entre las {facts['start']} y las {facts['end']} el proveedor del LLM devolvió errores 503 de forma persistente. {facts['bad']} de {facts['total']} tickets ({facts['bad'] / facts['total']:.0%}) terminaron en error o degradados. "
               f"La alerta de quema rápida de disponibilidad saltó a las {facts['detect']} (TTD {facts['ttd']} min) y se resolvió a las {facts['resolved']}. Se consumió el {facts['budget_pct']:.0f} % del presupuesto mensual de disponibilidad.",
    "impact": [f"{facts['bad']} tickets sin resolver ({facts['bad'] / facts['total']:.0%} del tráfico del periodo); los clientes recibieron «problema técnico» o el mensaje de fallback.",
               f"SLO de disponibilidad: {facts['budget_pct']:.0f} % del presupuesto mensual consumido en 45 minutos.", "Latencia y coste sin impacto (los errores fueron rápidos)."],
    "timeline": [(facts["start"], "Empiezan los 503 del proveedor (primer span `chat` con `error.type=server_error`)."), (hh(o0 + 4), "El burn rate de 5 min supera 14,4×; el de 1 h aún no."),
                 (facts["detect"], f"Salta la alerta `SLO availability · fast-burn` (página). TTD = {facts['ttd']} min."), (hh(t_detect + 3), "La guardia reconoce la alerta y abre el dashboard `slo-agente`."),
                 (hh(t_detect + 8), "Las trazas con error muestran `http.response.status_code=503` en todos los `chat`: causa externa al despliegue."), (facts["end"], "El proveedor se recupera; el burn de 5 min cae por debajo de 14,4×."),
                 (facts["resolved"], "La alerta se resuelve (la ventana corta de 5 min deja de superar el umbral; la de 1 h aún lo supera).")],
    "root_cause": "El proveedor de LLM sufrió una degradación regional. SupportOps tenía un único proveedor y un único modelo, sin conmutación automática a reserva, por lo que el fallo se propagó al 100 % de las llamadas.",
    "contributing": ["No existía un modelo/proveedor de reserva ni un modo degradado automático (escalar a humano).", "La política de reintentos (1 reintento) no ayuda cuando el fallo es persistente y alarga la latencia del error.",
                     "El runbook no indicaba cómo conmutar a la reserva ni quién puede hacerlo."],
    "went_well": ["La alerta multiventana saltó sin falsas alarmas previas y se resolvió sola al terminar el incidente.", "El dashboard enlazado desde la alerta permitió descartar un despliegue en < 10 min."],
    "went_wrong": [f"El TTD de {facts['ttd']} min dejó a clientes sin respuesta; no hubo comunicación proactiva.", "No hay un procedimiento escrito para escalar a humanos en masa."],
    "lucky": ["El incidente terminó antes del máximo de tráfico del mediodía (a las 10:00 ya se está al ≈ 95 % del pico): unas horas más tarde habría afectado a más tickets por minuto."],
    "actions": [("Configurar un proveedor/modelo de reserva con conmutación automática y probarla cada mes", "plataforma", "3 semanas", "mitigar"),
                ("Añadir una sonda sintética por minuto del camino LLM para bajar el TTD de la alerta", "observabilidad", "2 semanas", "detectar"),
                ("Actualizar el runbook de disponibilidad con el procedimiento de conmutación y el árbol de decisión", "guardia", "1 semana", "prevenir"),
                ("Plantilla de comunicación a clientes y a soporte humano para degradaciones de proveedor", "soporte", "2 semanas", "mitigar")]}
display(Markdown(render_postmortem(pm)))
''')
    md(observe("""
    - El postmortem **no nombra a ninguna persona**: describe un sistema con un único proveedor y un runbook incompleto. La pregunta que lo guía es «¿qué hizo fácil que ocurriera y difícil detectarlo?», no «¿quién se equivocó?» (cultura *just culture*; Allspaw, 2012).
    - Las cifras salen de la telemetría (TTD, tickets, presupuesto), no de la memoria de nadie.
    - Cada acción tiene **responsable, plazo y tipo** (prevenir / detectar / mitigar) para poder comprobar si se hizo. Una acción como «tener más cuidado» no es una acción.
    """))

    # ------------------------------------------------------------------------------------------------------------- 10
    md("""
    ---
    # 10 · 🏭 En producción

    - **Google (SRE Workbook, cap. 5 «Alerting on SLOs»)** describe la evolución desde el umbral fijo hasta la multiventana y multi-burn-rate que usamos; Grafana Labs publica guías para implementarla con Grafana (reglas de grabación por ventana + alertas), y herramientas de código abierto como Sloth y Pyrra generan las reglas a partir de una definición de SLO.
    - **Reglas de grabación (*recording rules*).** En producción no se calcula el burn con `rate()` sobre 3 días en cada evaluación: se precalcula el ratio de error por ventana (5 m, 30 m, 1 h, 6 h…) como regla de grabación y las alertas leen esas series. En el laboratorio calculamos las consultas en la propia regla por simplicidad.
    - **Dependencias.** Tu disponibilidad está acotada por la de aquello de lo que dependes (proveedor de LLM, herramientas). Un SLO del 99,9 % con un proveedor del 99,5 % necesita una estrategia de reserva.
    - **Sistemas multi-agente (módulo 11).** El SLO de extremo a extremo se descompone por agente; la quema del orquestador suele ser consecuencia de la de un subagente: alerta en el *usuario* (síntoma) y diagnostica por *causa*.
    - **Postmortems como producto.** Se publican, se revisan en una reunión regular y sus acciones entran en el *backlog* con prioridad; las plataformas de gestión de incidentes automatizan cronologías, pero la disciplina es cultural.
    """)

    md("""
    ---
    # 11 · 🧠 Secretos de la élite

    1. **Alerta sobre síntomas del usuario (SLO), diagnostica por causas.** Una página por «CPU alta» es ruido; una por «el presupuesto de disponibilidad se agota en 2 h» es una decisión de negocio. Las alertas de causa (módulo 10) son tickets o paneles, no páginas.
    2. **El burn rate es independiente del objetivo; el umbral absoluto no.** Por eso 14,4 sirve para 99 % y para 99,99 %. Si cambias el objetivo, cambian los umbrales absolutos de error, no la política.
    3. **La ventana corta es un interruptor de apagado, no de encendido.** Existe para que la alerta se apague en cuanto el problema cesa (≈ 1/12 de la larga). Sin ella tendrías páginas de incidentes ya resueltos durante horas.
    4. **Dimensiona las ventanas por el volumen del SLI.** Con pocos eventos (calidad evaluada por muestreo, tráfico nocturno, SLO de un cliente) el burn de una ventana corta es ruido: exige un `min_events` y alarga la ventana, o usa una sonda sintética que genere tráfico de referencia.
    5. **Una regresión de calidad es una quema lenta**: no necesita una página a las 3 h sino un **bloqueo de despliegue** (canario con SPRT, módulo 15) y un ticket. Reserva las páginas para lo que no puede esperar a mañana.
    6. **El SLO de calidad mide también a tu juez.** Si el juez tiene un 3 % de falsos positivos, un objetivo de 98 % se incumple solo por él. Pon el objetivo por debajo de la línea base medida y vigila `supportops_eval_errors_total`: un juez roto es un falso verde.
    7. **SLI de muestra uniforme, muestra de caza aparte.** El SLO usa una muestra simple (sin sesgo, PromQL trivial); la estratificada (errores, valoraciones negativas) sirve para investigar y construir datasets. Mezclarlas obliga a reponderar en cada alerta.
    8. **Mide la guardia, no solo el servicio**: páginas por semana, % accionables, tiempo de reconocimiento. Un SLO bien definido con una guardia quemada es un fracaso de fiabilidad.
    9. **Postmortem sin culpa ≠ sin responsabilidad.** La responsabilidad es sobre las **acciones** (con dueño y plazo); la culpa es sobre las personas. Si tu postmortem tiene un nombre propio en la causa raíz, reescríbelo.
    10. **Congelar con presupuesto agotado solo funciona si se pactó antes.** La política de presupuesto debe estar firmada por producto *antes* del incidente; negociarla en caliente la vacía de contenido. *Plantilla: el Workbook incluye un ejemplo de política de presupuesto de error (apéndice «Example Error Budget Policy»; título según el índice del libro, no abierto desde el sandbox).*
    11. **Cultura de guardia con números: ≥ 50 % ingeniería, ≤ 25 % de guardia y ≤ 2 incidentes por turno.** El libro de SRE fija que al menos la mitad del tiempo del equipo sea ingeniería y, del resto, no más del 25 % guardia; el objetivo es como máximo **dos incidentes por turno de guardia (12 h)** porque cada uno, con diagnóstico, mitigación, postmortem y arreglos, consume del orden de 6 horas. Traduce a tu panel de guardia: páginas por turno y % accionables; si superas el límite durante un par de semanas, el síntoma no es «el equipo es lento», es que el servicio debe frenar funcionalidades y comprar fiabilidad. *Fuente: Google SRE Book, cap. 11 «Being On-Call» y cap. 1; cifras confirmadas por búsqueda web (el sitio no abre desde el sandbox); la paráfrasis «2-3 incidentes» de blogs no es del original.*
    12. **Entrena la guardia con incidentes simulados.** Google SRE describe el ejercicio «Wheel of Misfortune»: un escenario de fallo reproducido con un compañero que hace de sistema y otro que responde en voz alta; sirve para enseñar a leer señales antes de la primera guardia real. La mesa de incidentes del módulo 21 es esa práctica con tu propia telemetría: mide el tiempo hasta la hipótesis correcta y repítelo por rotación. *Fuente: Google SRE Book, cap. 28 «Accelerating SREs to On-Call and Beyond» (título y ejercicio conocidos del libro; no abierto desde el sandbox).*
    """)

    md("""
    ---
    # 12 · ⚠️ Errores comunes

    - SLO del 100 % (no deja presupuesto: es imposible y paraliza los cambios).
    - SLOs que no miden lo que ve el usuario (latencia del Collector, CPU) o sin línea base medida.
    - Alertar con umbrales fijos de tasa de error: despiertan por ráfagas o llegan tarde.
    - Intervalo de grupo de alertas no múltiplo de 10 s (`15s`): Grafana no arranca.
    - Alertas sin `__dashboardUid__`/`__panelId__` ni `runbook_url`: el on-call empieza de cero.
    - Páginas para quemas lentas (la calidad) y tickets para quemas rápidas (disponibilidad): severidad invertida.
    - `noDataState` mal elegido: un SLO sin datos puede ser «OK» (no hay tráfico) o una caída de la telemetría; decide por regla.
    - Postmortems con culpables, sin acciones o con acciones sin dueño ni plazo.
    - Confiar en el SLO de calidad sin vigilar al juez.
    """)

    md("""
    ---
    # 13 · Autoevaluación
    """)
    md(details("1 · (Cálculo) Un SLO de disponibilidad del 99,9 % a 30 días. ¿Cuánto presupuesto de tiempo de indisponibilidad hay? ¿En cuánto tiempo lo agota un burn rate de 14,4 y cuánto presupuesto consume si dura 1 hora?",
               "Presupuesto: 0,1 % de 43 200 min ≈ **43,2 min**. A 14,4× lo agota en 720 h/14,4 = **50 h**; en 1 h consume 14,4/720 = **2 %** del presupuesto (≈ 52 s de indisponibilidad equivalente). De ahí el 2 % por hora de la política de quema rápida."))
    md(details("2 · (Cálculo) Objetivo 99 %. En la última hora hubo 12 000 tickets y 960 malos; en los últimos 5 minutos, 1 000 tickets y 180 malos. ¿Dispara la política 14,4× (1 h y 5 min)?",
               "Ventana larga: 960/12 000 = 8 % → burn 8/1 = **8** < 14,4. Ventana corta: 18 % → burn **18**. Como la larga no llega a 14,4, **no dispara**: el problema reciente es grave pero aún no ha acumulado suficiente en la hora; si continúa, la ventana larga cruzará en pocos minutos."))
    md(details("3 · (Diagnóstico) Tu SLO de calidad se incumple cada lunes por la mañana sin ningún despliegue. ¿Qué sospechas?",
               "Estacionalidad del tráfico: el lunes cambia la **mezcla** (más reembolsos/escalados tras el fin de semana) o el volumen cae y la muestra de calidad es pequeña y ruidosa (`min_events`). También un cambio del juez o de su cobertura. Comprueba la mezcla de intenciones (PSI, módulo 15), el nº de evaluaciones por ventana y la calibración del juez antes de tocar el agente."))
    md(details("4 · (Diagnóstico) La guardia recibió 14 páginas esta semana y 11 se cerraron sin hacer nada. ¿Qué cambias?",
               "Pasa las alertas no accionables a ticket o dashboard, sustituye umbrales fijos por burn rate multiventana, añade `min_events`, revisa `noDataState` y la agrupación de la política de notificación, y mide el % de acciones útiles por regla. Una regla con < 50 % de accionables se arregla o se elimina."))
    md(details("5 · (Transferencia) Defines un SLO de coste («el 98 % de los tickets cuesta ≤ X»). ¿Qué política de presupuesto asocias y qué alerta?",
               "Una quema rápida (bucle de herramientas o cambio a un modelo caro) es de página en horario laboral o de ticket urgente según el riesgo financiero; una lenta (deriva de tokens por ticket) es ticket. La acción de mitigación son los *guards* del módulo 13 (tope por ticket, degradación de modelo). Y el SLO se revisa trimestralmente con finanzas."))
    md(details("6 · (Transferencia) ¿Cómo adaptas la política multiventana a un SLO por cliente enterprise con 20 tickets al día?",
               "Con 20 eventos al día las ventanas de 5 min y 1 h son ruido. Usa ventanas de horas/días, un `min_events` mayor, o un SLI basado en **sondas sintéticas** que generan tráfico de referencia. Alerta además por eventos absolutos (p. ej. ≥ 3 fallos consecutivos) en lugar de ratios."))
    md(details("7 · ¿Qué diferencia hay entre un SLO, un SLA y un objetivo interno de equipo?",
               "El **SLA** es un contrato con clientes (con consecuencias económicas) y suele ser más laxo; el **SLO** es el objetivo interno más estricto que se vigila para no incumplir el SLA; el SLI es la medida. Mantener el SLO por encima del SLA da margen para reaccionar antes de pagar penalizaciones."))

    md("""
    ---
    # 14 · Referencias

    - Beyer, B., Murphy, N. R., Rensin, D. K., Kawahara, K., Thorne, S. (2018). *The Site Reliability Workbook*, cap. 5 «Alerting on SLOs» — https://sre.google/workbook/alerting-on-slos/ (políticas 14,4×/1 h, 6×/6 h, 1×/3 d).
    - Beyer, B., Jones, C., Petoff, J., Murphy, N. R. (2016). *Site Reliability Engineering*, caps. 4 «Service Level Objectives», 11 «Being On-Call» y 15 «Postmortem Culture: Learning from Failure» — https://sre.google/sre-book/table-of-contents/
    - Grafana Labs, *How to implement multi-window, multi-burn-rate alerts with Grafana Cloud* (blog, 2025) — https://grafana.com/blog/2025/02/28/how-to-implement-multi-window-multi-burn-rate-alerts-with-grafana-cloud/
    - Grafana, documentación de *Alerting → Provision alerting resources* (archivos YAML, `interval`, annotations `__dashboardUid__`/`__panelId__`) — https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/
    - Allspaw, J. (2012). *Blameless PostMortems and a Just Culture.* Etsy Code as Craft — https://www.etsy.com/codeascraft/blameless-postmortems/
    - OpenTelemetry, *Semantic conventions for generative AI* — métricas `gen_ai.invoke_agent.duration` y `gen_ai.client.inference.duration` usadas como SLIs (estado *Development*).
    - Hidalgo, A. (2020). *Implementing Service Level Objectives.* O'Reilly — SLOs, presupuestos y políticas en la práctica.
    """)
    nb.save(out)



def build_project() -> None:
    nb, out = nb_for(MOD, "16_proyecto_slos_alertas_incidentes.ipynb", "Proyecto 16 · SLOs, alertas, runbook y postmortem de SupportOps")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Proyecto 16 · SLOs, alertas, runbook y postmortem de SupportOps

    | | |
    |---|---|
    | **Nivel** | 🟠 Avanzado |
    | **Duración estimada** | ≈ 1 h 45 min |
    | **Servicios de Compose** | Ninguno (todo en memoria). Opcional: `core` + `metrics` para ver tus reglas en Grafana (paso final) |
    | **RAM aproximada** | < 500 MB |
    | **Prerrequisitos** | Lección `16_slos_alertas_incidentes`, proyectos 14 y 15 y módulo 10 |
    | **Conexión** | Cierra el bloque de calidad: la telemetría de los módulos 9-15 se convierte en **contrato** (SLO), **alerta** y **aprendizaje** (postmortem) |

    ## Contexto de negocio

    Eres ingeniero/a de plataforma en **SupportOps**. Dirección pide cuatro cosas: (1) SLOs medibles para disponibilidad, latencia, calidad y coste, (2) alertas que despierten solo por lo que agota el presupuesto,
    (3) las reglas de alerta provisionadas como código y (4) tras el incidente de ayer —un fallo del proveedor LLM entre las 10:00 y las 10:45— un **postmortem sin culpa** con cifras reales.

    ## Datos

    Sintéticos y deterministas (semilla 42, `mock`): el **Paso 0** ejecuta el agente real sobre 24 h de tráfico (`simulate_day`) con el incidente del proveedor y una regresión de prompt. Recibes los eventos por ticket (`ROWS`) y los
    contadores por minuto de disponibilidad (`AV_G`, `AV_T`) y calidad (`QU_G`, `QU_T`). La verdad del incidente (`TRUTH`) está en el notebook: úsala solo para validar.

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución; `mock`, semilla 42) |
    |---|---|---|---|
    | R1 | `sli_counts` | Buenos/totales de los 4 SLIs sobre el día completo | exacto |
    | R2 | `budget_math`, `hours_to_exhaustion` | Presupuesto, consumo, burn y tiempo hasta agotar en 5 vectores | 5/5 |
    | R3 | `multiwindow_fire` | Igual que la referencia en disponibilidad y calidad; sin falsos positivos fuera del incidente | exacto / 3/3 |
    | R4 | `alert_rule`, `provision_group` | Estructura de la regla, anotaciones, `for`, y rechazo de intervalos no múltiplos de 10 s | 7/7 |
    | R5 | `incident_report` | TTD, reajuste, tickets perdidos y % del presupuesto mensual | exacto (tol. 1e-9) |
    | R6 | `write_postmortem` | Secciones, cifras coherentes, ≥ 4 acciones con responsable/plazo/tipo y sin lenguaje de culpa | 7/7 |

    > 📏 Los umbrales salen de la solución de referencia con la semilla 42 fija en el notebook; R1, R3 y R5 se comparan con las funciones del paquete `supportops.slo` ejecutadas en vivo.
    """)

    code(boot("viz,otel"))
    code(IMPORTS + IMPORTS_16.replace('STACK = check_stack("core+metrics")', 'STACK = check_stack([])').replace("LIVE = not STACK.degraded", "LIVE = False"))

    md("""
    ## Paso 0 · Los datos (te lo damos hecho)
    """)
    code('''
DAY = simulate_day(SEED)
ROWS, NB, T0, TRUTH = DAY["rows"], DAY["n_bins"], DAY["t0"], DAY["truth"]
AV_G, AV_T = bin_events(ROWS, DEFAULT_SLOS["availability"], t0=T0, n_bins=NB)
QU_G, QU_T = bin_events(ROWS, DEFAULT_SLOS["quality"], t0=T0, n_bins=NB)
O0, O1 = (int(x) for x in TRUTH["outage"])
print(f"{len(ROWS)} tickets · incidente real: minutos {O0}-{O1} · fila de ejemplo: {ROWS[0]}")
print({k: (v.description, v.objective, v.threshold) for k, v in DEFAULT_SLOS.items()})
''')

    # ------------------------------------------------------------------------------ 1
    md("""
    ## Paso 1 · Los SLIs

    **TODO 1.** `sli_counts(rows, slo)` recibe la lista de filas (dicts con `status`, `latency_s`, `cost_usd`, `quality_good`) y un `dict` `slo` con `sli` y `threshold`, y devuelve `(buenos, totales)`:

    - `availability`: bueno si `status` ∈ {`ok`, `escalated`}; todos los tickets son válidos.
    - `latency`: bueno si `latency_s <= threshold`.
    - `cost`: bueno si `cost_usd <= threshold`.
    - `quality`: **válidos** solo los que tienen `quality_good` distinto de `None` (los evaluados); bueno si `quality_good` es `True`.
    """)
    md(hint(1, "Es el mismo patrón en los cuatro casos: construye una lista de booleanos «¿este evento es bueno?» sobre los **eventos válidos** y devuelve `(sum(lista), len(lista))`. Solo cambia qué filas son válidas (en calidad, las evaluadas)."))
    code('''
def sli_counts(rows: list, slo: dict) -> tuple:
    # TODO 1
    raise NotImplementedError("TODO 1")

try:
    print({k: sli_counts(ROWS, {"sli": v.sli, "threshold": v.threshold}) for k, v in DEFAULT_SLOS.items()})
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ------------------------------------------------------------------------------ 2
    md("""
    ## Paso 2 · Presupuesto y burn rate

    **TODO 2a.** `budget_math(good, total, objective)` devuelve `{"sli", "bad", "allowed_bad", "consumed", "burn"}`: `sli = good/total`, `bad = total − good`, `allowed_bad = (1 − objective)·total`, `consumed = bad/allowed_bad` y `burn = (1 − sli)/(1 − objective)`.

    **TODO 2b.** `hours_to_exhaustion(burn, period_h=720)` devuelve las horas hasta agotar **todo** el presupuesto del periodo a ese ritmo: `period_h / burn` (`float("inf")` si `burn <= 0`).
    """)
    code('''
def budget_math(good: float, total: float, objective: float) -> dict:
    # TODO 2a
    raise NotImplementedError("TODO 2a")

def hours_to_exhaustion(burn: float, period_h: float = 720) -> float:
    # TODO 2b
    raise NotImplementedError("TODO 2b")

try:
    print(budget_math(9_900, 10_000, 0.99), hours_to_exhaustion(14.4))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ------------------------------------------------------------------------------ 3
    md("""
    ## Paso 3 · La alerta multiventana

    **TODO 3.** `multiwindow_fire(good, total, objective, factor, long_min, short_min, min_events=5)` recibe arrays por minuto y devuelve un array booleano (uno por minuto): `True` si el burn rate de la ventana **larga** y el de la **corta** son `>= factor`.

    - Cada ventana suma buenos y totales de los **últimos** `w` minutos (incluido el actual; al principio, los que haya).
    - Si en la ventana hay menos de `min_events` eventos, ese burn **no cuenta** (no dispara).
    - `burn = (1 − buenos/totales)/(1 − objective)`.
    """)
    md(hint(1, "Suma móvil con `np.cumsum`: `c = np.cumsum(np.insert(x, 0, 0))`; la suma de los últimos `w` hasta `i` es `c[i+1] - c[max(i+1-w, 0)]`."))
    md(hint(2, "Escribe una función interna `burn(w)` que, para todos los minutos `i = np.arange(len(good))`, calcule `g` y `t` con esa resta, ponga `NaN`/0 donde `t < min_events` y devuelva `(1 - g/t)/(1 - objective)`. El resultado es `(burn(long_min) >= factor) & (burn(short_min) >= factor)`. Compáralo con tu `burn_by_hand` de la lección §4."))
    code('''
def multiwindow_fire(good, total, objective, factor, long_min, short_min, min_events=5):
    # TODO 3
    raise NotImplementedError("TODO 3")

try:
    F = multiwindow_fire(AV_G, AV_T, 0.99, 14.4, 60, 5)
    print("dispara", int(F.sum()), "minutos · primer minuto:", int(np.argmax(F)) if F.any() else None, "· incidente real:", O0)
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ------------------------------------------------------------------------------ 4
    md("""
    ## Paso 4 · La regla de Grafana como código

    **TODO 4a.** `alert_rule(name, objective, threshold_sli, factor, long_w, short_w, severity, dashboard_uid, panel_id)` devuelve el `dict` de una regla de provisioning (formato del módulo 10) para un SLO de **disponibilidad**:

    - `uid` = `f"slo-{name}-{severity}"`, `title` con el nombre, `condition` = `"F"`, `for` = `"0s"` si `severity == "page"` y `"1m"` si no, `noDataState` = `"OK"`, `execErrState` = `"Error"`.
    - `data`: lista con refIds **A** (PromQL instantánea del burn con la ventana `long_w`, datasource `prometheus`), **B** (idem con `short_w`), **C** y **D** (`reduce` `last` con `settings.mode = dropNN` de A y B), **E** (`math`: `$C > f && $D > f`) y **F** (`threshold` `gt 0` sobre E). El burn de availability es `(1 - ratio) / (1 - objective)` con
      `ratio = sum(rate(supportops_agent_requests_total{service_name="supportops-agent",supportops_status=~"ok|escalated"}[W])) / sum(rate(supportops_agent_requests_total{service_name="supportops-agent"}[W]))`.
    - `annotations`: `__dashboardUid__`, `__panelId__` (**cadena**), `summary` y `runbook_url`. `labels`: `severity`, `service="supportops-agent"`, `slo=name`.

    **TODO 4b.** `provision_group(rules, interval)` devuelve `{"apiVersion": 1, "groups": [{"orgId": 1, "name": "supportops-slo", "folder": "Curso observabilidad de agentes", "interval": interval, "rules": rules}]}` y lanza `ValueError` si `interval` no termina en `s` o no es múltiplo de 10 s.
    """)
    md(hint(1, "No inventes la estructura: es la misma regla que la lección imprimió en §7 (`r0[\"data\"]` y la tabla de piezas A-F). Reprodúcela como un `dict` y comprueba con `[d[\"refId\"] for d in R[\"data\"]]`. Escribe antes una función pequeña `expr(w)` que devuelva el PromQL del burn para una ventana `w` y reutilízala para A y B."))
    md(hint(2, "`A` y `B` son consultas (`datasourceUid=\"prometheus\"`, `model` con `expr` e `instant=True`); `C` y `D` son `reduce` con `reducer=\"last\"` sobre A y B; `E` es un `math` con `$C > f && $D > f` y `F` un `threshold` `gt 0` sobre E. Los `dict` de `annotations` y `labels` salen del enunciado tal cual (`__panelId__` es `str(panel_id)`)."))
    code('''
def alert_rule(name, objective, threshold_sli, factor, long_w, short_w, severity, dashboard_uid, panel_id) -> dict:
    # TODO 4a
    raise NotImplementedError("TODO 4a")

def provision_group(rules, interval) -> dict:
    # TODO 4b
    raise NotImplementedError("TODO 4b")

try:
    R = alert_rule("availability", 0.99, None, 14.4, "5m", "1m", "page", "slo-agente", 12)
    print(R["uid"], [d["refId"] for d in R["data"]], R["annotations"]["__panelId__"])
    print(provision_group([R], "30s")["groups"][0]["interval"])
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ------------------------------------------------------------------------------ 5
    md("""
    ## Paso 5 · Las cifras del incidente

    **TODO 5.** `incident_report(good, total, fire, start_min, end_min, objective)` devuelve un `dict` con los arrays por minuto de disponibilidad, el array booleano `fire` de la alerta y la ventana real del incidente:

    - `ttd_min`: minutos desde `start_min` hasta el **primer** minuto `>= start_min` con `fire` verdadero.
    - `reset_min`: minutos desde `end_min` hasta el **último** minuto con `fire` verdadero (puede ser negativo si se apagó antes).
    - `bad_tickets`: tickets malos (`total − good`) en `[start_min, end_min)` (entero).
    - `budget_month_pct`: `100 · bad_tickets / ((1 − objective) · total.sum() · 30)` (el día se repite 30 veces).
    - `false_minutes`: minutos con `fire` verdadero fuera de `[start_min − 5, end_min + 60)`.
    """)
    md(hint(1, "Con `fire` booleano: el primer minuto que dispara dentro del incidente es `np.argmax(fire[start_min:]) `; el último minuto que dispara es `np.where(fire)[0].max()`. Los tickets malos son `int((total - good)[start_min:end_min].sum())`."))
    md(hint(2, "`false_minutes`: `m = np.ones(len(fire), bool); m[max(start_min-5, 0):end_min+60] = False` y cuenta `fire & m`. Es la misma idea de «alertas fuera del incidente» que viste en la comparación de estrategias (§4)."))
    code('''
def incident_report(good, total, fire, start_min, end_min, objective) -> dict:
    # TODO 5
    raise NotImplementedError("TODO 5")

REPORT = {}
try:
    REPORT = incident_report(AV_G, AV_T, multiwindow_fire(AV_G, AV_T, 0.99, 14.4, 60, 5), O0, O1, 0.99)
    print(REPORT)
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ------------------------------------------------------------------------------ 6
    md("""
    ## Paso 6 · El postmortem sin culpa

    **TODO 6.** `write_postmortem(report)` devuelve el `dict` que acepta `render_postmortem` (claves `title, summary, impact, timeline, root_cause, contributing, went_well, went_wrong, lucky, actions`). Requisitos:

    - `summary` e `impact` incluyen las **cifras de `report`**: el TTD (en minutos), los tickets malos y el % del presupuesto mensual (redondeado a entero).
    - `timeline`: ≥ 5 entradas `("HH:MM", "evento")` en **orden cronológico** que incluyan el inicio real del incidente (`10:00`) y la hora de la alerta.
    - `actions`: ≥ 4 tuplas `(acción, responsable, plazo, tipo)` con `tipo` ∈ {`prevenir`, `detectar`, `mitigar`}, **al menos una de cada tipo**, y responsables que sean equipos/roles (no nombres propios).
    - **Sin culpa**: ni `root_cause` ni `contributing` contienen «culpa», «negligen», «error humano», «debería haber» ni «se olvidó».
    """)
    md(hint(1, "Puedes reutilizar la estructura de la lección (§9). Para la hora de alerta usa `f'{(O0 + report[\"ttd_min\"]) // 60:02d}:{(O0 + report[\"ttd_min\"]) % 60:02d}'`."))
    md(hint(2, "Parte del `pm` de la lección: cambia solo lo que depende de `report` (cifras del resumen y la hora de la alerta) y revisa que cada acción tenga la forma `(acción, equipo, plazo, tipo)` y que haya al menos una de `prevenir`, `detectar` y `mitigar`. Evita en causa raíz las palabras prohibidas: describe el **sistema** (un único proveedor, ausencia de reserva), no a una persona."))
    code('''
def write_postmortem(report: dict) -> dict:
    # TODO 6
    raise NotImplementedError("TODO 6")

try:
    PM = write_postmortem(REPORT); print(render_postmortem(PM)[:600])
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ------------------------------------------------------------------------------ rúbrica
    md("""
    ## Paso 7 · Rúbrica
    """)
    code('''
def run_rubric():
    rows = []
    def add(r, d, ok, det=""): rows.append({"criterio": r, "descripción": d, "resultado": "✅ OK" if ok else "❌ FALLA", "detalle": det})
    # R1
    try:
        got = {k: tuple(int(x) for x in sli_counts(ROWS, {"sli": v.sli, "threshold": v.threshold})) for k, v in DEFAULT_SLOS.items()}
        ref = {k: (int(bin_events(ROWS, v, t0=T0, n_bins=NB)[0].sum()), int(bin_events(ROWS, v, t0=T0, n_bins=NB)[1].sum())) for k, v in DEFAULT_SLOS.items()}
        add("R1", "sli_counts: 4 SLIs", got == ref, f"{got}" if got != ref else f"exacto · {got}")
    except Exception as e: add("R1", "sli_counts", False, f"{type(e).__name__}: {e}")
    # R2
    try:
        b = budget_math(9_900, 10_000, 0.99); b2 = budget_math(9_900, 10_000, 0.999); b3 = budget_math(10_000, 10_000, 0.99)
        checks = {"consumo = 1": abs(b["consumed"] - 1) < 1e-9 and abs(b["burn"] - 1) < 1e-9, "allowed_bad": abs(b["allowed_bad"] - 100) < 1e-9 and b["bad"] == 100, "burn 10×": abs(b2["burn"] - 10) < 1e-9 and abs(b2["consumed"] - 10) < 1e-9,
                  "14,4 → 50 h": abs(hours_to_exhaustion(14.4) - 50) < 1e-9, "burn 0 → inf": hours_to_exhaustion(0) == float("inf") and b3["consumed"] == 0}
        add("R2", "budget_math y hours_to_exhaustion: 5 vectores", all(checks.values()), str({k: v for k, v in checks.items() if not v} or "todas OK"))
    except Exception as e: add("R2", "budget_math", False, f"{type(e).__name__}: {e}")
    # R3
    try:
        p = GOOGLE_POLICIES[0]
        f1 = multiwindow_fire(AV_G, AV_T, 0.99, 14.4, 60, 5); r1 = fire_series(AV_G, AV_T, 0.99, p)
        inc = minute_mask(O0, O1, NB)
        checks = {"disponibilidad = referencia": bool((np.asarray(f1) == r1).all()), "dispara dentro del incidente": bool(np.asarray(f1)[inc].any()), "sin falsos positivos fuera (±60 min)": not np.asarray(f1)[: O0 - 5].any() and not np.asarray(f1)[O1 + 60:].any()}
        add("R3", "multiwindow_fire: 3 comprobaciones", all(checks.values()), str({k: v for k, v in checks.items() if not v} or f"todas OK · primer minuto {int(np.argmax(f1))}"))
    except Exception as e: add("R3", "multiwindow_fire", False, f"{type(e).__name__}: {e}")
    # R4
    try:
        r = alert_rule("availability", 0.99, None, 14.4, "5m", "1m", "page", "slo-agente", 12)
        r2 = alert_rule("availability", 0.99, None, 3.0, "15m", "3m", "ticket", "slo-agente", 12)
        ref = grafana_burn_rule(DEFAULT_SLOS["availability"], LAB_POLICIES[0], dashboard_uid="slo-agente", panel_id=12)
        by = {d["refId"]: d for d in r["data"]}
        def raises(iv):
            try: provision_group([r], iv)
            except ValueError: return True
            return False
        checks = {"refIds A-F y condición F": [d["refId"] for d in r["data"]] == list("ABCDEF") and r["condition"] == "F", "burn largo y corto": by["A"]["model"]["expr"] == ref["data"][0]["model"]["expr"] and by["B"]["model"]["expr"] == ref["data"][1]["model"]["expr"],
                  "math y umbral": by["E"]["model"]["expression"].replace(" ", "") == "$C>14.4&&$D>14.4" and by["F"]["model"]["type"] == "threshold",
                  "for según severidad": r["for"] == "0s" and r2["for"] == "1m", "anotaciones": r["annotations"]["__dashboardUid__"] == "slo-agente" and r["annotations"]["__panelId__"] == "12" and "runbook_url" in r["annotations"] and "summary" in r["annotations"],
                  "etiquetas": r["labels"] == {"severity": "page", "service": "supportops-agent", "slo": "availability"} or (r["labels"].get("severity") == "page" and r["labels"].get("slo") == "availability"),
                  "intervalo múltiplo de 10 s": provision_group([r], "30s")["groups"][0]["interval"] == "30s" and raises("15s") and raises("45")}
        add("R4", "alert_rule y provision_group: 7 comprobaciones", all(checks.values()), str({k: v for k, v in checks.items() if not v} or "todas OK"))
    except Exception as e: add("R4", "alert_rule/provision_group", False, f"{type(e).__name__}: {e}")
    # R5
    try:
        f = multiwindow_fire(AV_G, AV_T, 0.99, 14.4, 60, 5); rep = incident_report(AV_G, AV_T, f, O0, O1, 0.99)
        idx = np.where(f)[0]; first = int(idx[idx >= O0][0]); last = int(idx[-1])
        exp = {"ttd_min": first - O0, "reset_min": last - O1, "bad_tickets": int((AV_T[O0:O1] - AV_G[O0:O1]).sum()), "budget_month_pct": 100 * (AV_T[O0:O1] - AV_G[O0:O1]).sum() / (0.01 * AV_T.sum() * 30),
               "false_minutes": int(f[: max(O0 - 5, 0)].sum() + f[O1 + 60:].sum())}
        ok = all(abs(rep[k] - v) < 1e-9 for k, v in exp.items())
        add("R5", "incident_report: 5 cifras", ok, f"{ {k: round(rep[k], 3) for k in exp} } (ref {exp})")
    except Exception as e: add("R5", "incident_report", False, f"{type(e).__name__}: {e}")
    # R6
    try:
        rep = incident_report(AV_G, AV_T, multiwindow_fire(AV_G, AV_T, 0.99, 14.4, 60, 5), O0, O1, 0.99); pm = write_postmortem(rep); md_ = render_postmortem(pm)
        txt = json.dumps(pm, ensure_ascii=False).lower()
        times = [h for h, _ in pm["timeline"]]
        hdet = f"{(O0 + rep['ttd_min']) // 60:02d}:{(O0 + rep['ttd_min']) % 60:02d}"
        types = {a[3] for a in pm["actions"]}
        blame = ["culpa", "negligen", "error humano", "debería haber", "se olvidó"]
        checks = {"secciones": all(h in md_ for h in ("## Resumen", "## Impacto", "## Cronología", "## Acciones")),
                  "cifras coherentes": str(int(rep["ttd_min"])) in pm["summary"] and str(rep["bad_tickets"]) in txt and str(round(rep["budget_month_pct"])) in txt,
                  "cronología ≥ 5, ordenada, con inicio y alerta": len(times) >= 5 and times == sorted(times) and "10:00" in times and hdet in times,
                  "≥ 4 acciones completas": len(pm["actions"]) >= 4 and all(len(a) == 4 and all(str(x).strip() for x in a) for a in pm["actions"]),
                  "los 3 tipos": {"prevenir", "detectar", "mitigar"} <= types,
                  "responsables = equipos": all(not re.search(r"\\b[A-Z][a-z]+ [A-Z][a-z]+\\b", a[1]) for a in pm["actions"]),
                  "sin lenguaje de culpa": not any(b in (pm["root_cause"] + " ".join(pm["contributing"])).lower() for b in blame)}
        add("R6", "write_postmortem: 7 comprobaciones", all(checks.values()), str({k: v for k, v in checks.items() if not v} or "todas OK"))
    except Exception as e: add("R6", "write_postmortem", False, f"{type(e).__name__}: {e}")
    return pd.DataFrame(rows).set_index("criterio")
''')
    code('''
# Ejecuta esta celda cuando hayas terminado los TODO
display(run_rubric())
''')

    md("""
    ---
    ## Paso final (opcional) · Míralo funcionar

    Con el stack: escribe `provision_group(...)` a `stack/grafana/provisioning/alerting/` con `yaml.safe_dump` y recarga con `POST /api/admin/provisioning/alerting/reload`; después reproduce el incidente en vivo con el código de la sección 7.1 de la lección.
    Comprueba que tu regla de página pasa a *firing* y se resuelve sola.

    ## Retos extra (nivel experto)

    1. **Cuatro SLOs, ocho reglas**: genera las reglas de los cuatro SLOs y de ambas políticas con un bucle y compara tu YAML con `16-slo-alerts.yaml`.
    2. **Sensibilidad**: barre `factor` (3-30) y `long_min` (15-240) y dibuja TTD frente a minutos falsos con 40 meses simulados (`simulate_month`); elige el punto de operación y defiéndelo.
    3. **Política escalonada**: implementa «<50 % de presupuesto → revisar despliegues; <25 % → solo fiabilidad; agotado → congelar» como función de `budget_math` sobre un mes simulado.
    4. **SLO de un cliente premium** con 20 tickets/día: diseña ventanas, `min_events` y una sonda sintética que lo hagan alertable.
    5. **Segundo postmortem**: escribe el de la regresión de prompt (6:00-14:00) con las cifras de calidad; ¿qué acciones de *prevenir* cambian respecto al del proveedor?

    ## Reflexión (producción e hilo conductor)

    - Tu TTD es de varios minutos. ¿Qué cuesta acortarlo (falsas alarmas, sondas sintéticas) y quién decide el compromiso?
    - ¿Qué SLO pondrías al proveedor del LLM en el contrato y cómo lo medirías tú, no él?
    - En el capstone (módulo 22) el agente es multi-agente: ¿cómo descompones el SLO de extremo a extremo entre orquestador y subagentes?
    - ¿Qué parte del postmortem sería distinta si el incidente hubiera sido una fuga de PII (módulo 20)?
    """)

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    A continuación, la **solución de referencia** completa y ejecutable (redefine las funciones y vuelve a lanzar la rúbrica).
    """)
    code('''
# ===================== SOLUCIÓN DE REFERENCIA =====================
def sli_counts(rows, slo):
    k = slo["sli"]
    if k == "availability": ok = [r["status"] in ("ok", "escalated") for r in rows]
    elif k == "latency": ok = [r["latency_s"] <= slo["threshold"] for r in rows]
    elif k == "cost": ok = [r["cost_usd"] <= slo["threshold"] for r in rows]
    else: ok = [bool(r["quality_good"]) for r in rows if r["quality_good"] is not None]
    return sum(ok), len(ok)

def budget_math(good, total, objective):
    sli = good / total; bad = total - good; allowed = (1 - objective) * total
    return {"sli": sli, "bad": bad, "allowed_bad": allowed, "consumed": bad / allowed, "burn": (1 - sli) / (1 - objective)}

def hours_to_exhaustion(burn, period_h=720):
    return float("inf") if burn <= 0 else period_h / burn

def multiwindow_fire(good, total, objective, factor, long_min, short_min, min_events=5):
    cg, ct = np.cumsum(np.insert(np.asarray(good, float), 0, 0)), np.cumsum(np.insert(np.asarray(total, float), 0, 0))
    def burn(w):
        i = np.arange(len(good)); lo = np.maximum(i + 1 - w, 0)
        g, t = cg[i + 1] - cg[lo], ct[i + 1] - ct[lo]
        with np.errstate(divide="ignore", invalid="ignore"): return np.where(t >= min_events, (1 - g / np.maximum(t, 1)) / (1 - objective), 0.0)
    return (burn(long_min) >= factor) & (burn(short_min) >= factor)

def alert_rule(name, objective, threshold_sli, factor, long_w, short_w, severity, dashboard_uid, panel_id):
    def expr(w):
        sel = 'service_name="supportops-agent"'
        ratio = f'sum(rate(supportops_agent_requests_total{{{sel},supportops_status=~"ok|escalated"}}[{w}])) / sum(rate(supportops_agent_requests_total{{{sel}}}[{w}]))'
        return f"(1 - ({ratio})) / {1 - objective:.6g}"
    q = lambda ref, w: {"refId": ref, "relativeTimeRange": {"from": 600, "to": 0}, "datasourceUid": "prometheus", "model": {"refId": ref, "expr": expr(w), "instant": True, "intervalMs": 15000, "maxDataPoints": 43200}}
    red = lambda ref, src: {"refId": ref, "datasourceUid": "__expr__", "model": {"refId": ref, "type": "reduce", "expression": src, "reducer": "last", "settings": {"mode": "dropNN"}}}
    return {"uid": f"slo-{name}-{severity}", "title": f"SLO {name} · {severity} (×{factor:g})", "condition": "F", "for": "0s" if severity == "page" else "1m", "noDataState": "OK", "execErrState": "Error", "isPaused": False,
            "data": [q("A", long_w), q("B", short_w), red("C", "A"), red("D", "B"),
                     {"refId": "E", "datasourceUid": "__expr__", "model": {"refId": "E", "type": "math", "expression": f"$C > {factor:g} && $D > {factor:g}"}},
                     {"refId": "F", "datasourceUid": "__expr__", "model": {"refId": "F", "type": "threshold", "expression": "E", "conditions": [{"evaluator": {"type": "gt", "params": [0]}}]}}],
            "annotations": {"__dashboardUid__": dashboard_uid, "__panelId__": str(panel_id), "summary": f"SLO {name}: burn rate >= {factor:g}x en {long_w} y {short_w}", "runbook_url": f"https://example.com/runbooks/slo-{name}"},
            "labels": {"severity": severity, "service": "supportops-agent", "slo": name}}

def provision_group(rules, interval):
    if not interval.endswith("s") or not interval[:-1].isdigit() or int(interval[:-1]) % 10: raise ValueError("el intervalo debe ser múltiplo de 10 s")
    return {"apiVersion": 1, "groups": [{"orgId": 1, "name": "supportops-slo", "folder": "Curso observabilidad de agentes", "interval": interval, "rules": rules}]}

def incident_report(good, total, fire, start_min, end_min, objective):
    idx = np.where(fire)[0]; first = int(idx[idx >= start_min][0]); last = int(idx[-1])
    bad = int((total[start_min:end_min] - good[start_min:end_min]).sum())
    return {"ttd_min": first - start_min, "reset_min": last - end_min, "bad_tickets": bad, "budget_month_pct": 100 * bad / ((1 - objective) * total.sum() * 30),
            "false_minutes": int(fire[: max(start_min - 5, 0)].sum() + fire[end_min + 60:].sum())}

def write_postmortem(report):
    hh = lambda m: f"{int(m) // 60:02d}:{int(m) % 60:02d}"
    det = O0 + report["ttd_min"]; pct = round(report["budget_month_pct"]); bad = report["bad_tickets"]
    return {"title": "El proveedor de LLM devuelve 503 durante 45 minutos", "severity": "SEV-2", "summary": f"Entre las 10:00 y las 10:45 el proveedor del LLM falló de forma persistente. {bad} tickets terminaron mal; la alerta de quema rápida saltó a las {hh(det)} (TTD {report['ttd_min']} min) y se consumió el {pct} % del presupuesto mensual.",
            "impact": [f"{bad} tickets malos en 45 minutos.", f"{pct} % del presupuesto mensual de disponibilidad consumido."],
            "timeline": [("10:00", "Empiezan los 503 del proveedor."), (hh(O0 + 4), "El burn rate de 5 min supera 14,4×."), (hh(det), f"Salta la alerta de quema rápida (TTD {report['ttd_min']} min)."), (hh(det + 3), "La guardia reconoce la alerta y abre el dashboard."),
                         (hh(det + 8), "Las trazas muestran 503 en todos los `chat`: causa externa."), ("10:45", "El proveedor se recupera.")],
            "root_cause": "Degradación del proveedor de LLM sin proveedor de reserva ni modo degradado automático en el sistema.",
            "contributing": ["No existía conmutación a un modelo de reserva.", "El runbook no describía el procedimiento de conmutación."],
            "went_well": ["La alerta multiventana no dio falsas alarmas y se resolvió sola."], "went_wrong": [f"El TTD de {report['ttd_min']} min dejó clientes sin respuesta."], "lucky": ["Terminó antes del máximo de tráfico del mediodía."],
            "actions": [("Proveedor/modelo de reserva con conmutación automática", "plataforma", "3 semanas", "mitigar"), ("Sonda sintética por minuto del camino LLM", "observabilidad", "2 semanas", "detectar"),
                        ("Actualizar el runbook con el procedimiento de conmutación", "guardia", "1 semana", "prevenir"), ("Plantilla de comunicación a clientes", "soporte", "2 semanas", "mitigar")]}

display(run_rubric())
''')
    nb.save(out)


# =====================================================================================================================
def build_readme() -> None:
    readme = """# Módulo 16 · SLOs, alertas e incidentes de agentes de IA

🟠 **Avanzado** · ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min)

> ⚠️ Tráfico e incidentes **simulados y deterministas** (`mock`, semilla 42): el agente real procesa 24 h de tickets con un fallo del proveedor LLM y una regresión de prompt inyectados, así que conocemos la verdad de cada alerta.
> Las ventanas del laboratorio en vivo están **comprimidas** (minutos); las de producción (1 h/5 min, 6 h/30 min, 3 d/6 h) se tratan con simulación y aritmética.

De «creo que va mal» a «el presupuesto se agota en 2 horas»: **SLIs específicos de agentes** (disponibilidad, latencia, calidad, coste), **presupuesto de error** y **burn rate multiventana**, comparado con umbrales fijos en un Monte Carlo de 40 meses;
**alertas de Grafana provisionadas como código** (intervalo múltiplo de 10 s, enlace alerta→panel en `annotations`) probadas con un incidente real en el stack; **runbooks**, guardia sostenible y **postmortem sin culpa** con cifras de la telemetría.

## Objetivos
1. Definir SLIs como «eventos buenos / válidos» y fijar SLOs con la línea base medida.
2. Calcular presupuesto, burn rate y tiempo hasta agotarlo; derivar el 14,4 de la SRE Workbook.
3. Implementar y comparar alertas por burn rate (umbral fijo, una ventana, multiventana).
4. Dimensionar ventanas para SLIs de poco volumen (calidad) y entender las quemas lentas.
5. Provisionar reglas de alerta como código y probarlas en vivo.
6. Redactar runbook y postmortem sin culpa.

## Contenido
| Archivo | Qué es |
|---|---|
| `16_slos_alertas_incidentes.ipynb` | Lección (14 secciones, 9 gráficos, incidente en vivo con alertas reales, 🧠 de élite, autoevaluación) |
| `16_proyecto_slos_alertas_incidentes.ipynb` | Proyecto: SLIs, presupuesto, alerta multiventana, regla de Grafana como código, informe del incidente y postmortem (rúbrica, pistas 🪜, solución tras ⛔ SPOILER) |
| `runbooks/` | Runbooks de las alertas (`slo-availability-fast-burn`, `slo-quality-slow-burn`) y plantilla de postmortem |
| `../supportops/slo.py` | `SLO`, burn rate y políticas (`GOOGLE_POLICIES`, `LAB_POLICIES`), `fire_series`, `alert_quality`, `simulate_day`/`simulate_month`, PromQL, `grafana_burn_rule`, `rules_yaml`, `render_postmortem` |
| `../supportops/tests/test_slo.py` | Pruebas del módulo |
| `../stack/grafana/dashboards/16-slos.json` | Dashboard «16 · SLOs de SupportOps» (uid `slo-agente`) |
| `../stack/grafana/provisioning/alerting/16-slo-alerts.yaml` | 8 reglas de alerta de SLO (grupo `supportops-slo`, intervalo 30 s) |

## Servicios necesarios
- **Sin Docker** (modo degradado): todo salvo la sección 7.1 de la lección y el paso final del proyecto. Funciona en Colab.
- **Con stack** (opcional): `cd stack && docker compose --profile core --profile metrics up -d`. Grafana: http://localhost:3000 (`admin`/`admin`). La sección 7.1 tarda ≈ 3 min.

## Lecturas
- Google, *The Site Reliability Workbook*, cap. 5 «Alerting on SLOs» · *Site Reliability Engineering*, caps. 4, 11 y 15.
- Grafana Labs, alertas multiventana multi-burn-rate · Allspaw (2012), *Blameless PostMortems and a Just Culture*.

## Cómo se conecta
Antes: módulos 09 (métricas), 10 (alertas básicas), 13 (coste), 14 (calidad online), 15 (regresión). Después: el 18 usa el presupuesto para decidir muestreo y retención; el 21 reutiliza los incidentes en la «mesa de incidentes»; el 22 integra SLOs y runbooks en el capstone.
"""
    (COURSE / MOD / "README.md").write_text(readme, encoding="utf-8")
    print("OK README", MOD)


if __name__ == "__main__":
    build_runbooks()
    ids = build_dashboard()
    build_alerts(ids)
    build_lesson()
    build_project()
    build_readme()
