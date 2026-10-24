# Tasks

## 1. Andamiaje, sesiones locales y validación

- [ ] 1.1 Crear `netflix-ml-interview/` con `README.md` (en español: uso, comandos, `lang=es`, aviso de no afiliación y de variabilidad, nota de que la escala es pedagógica) y el árbol de D6; verificar con `find netflix-ml-interview -maxdepth 2` que coincide con D6
- [ ] 1.2 Añadir `netflix-ml-interview/sessions/` al `.gitignore` raíz; verificar que `git check-ignore -q netflix-ml-interview/sessions/x` devuelve 0 y que un archivo de prueba en `sessions/` no aparece en `git status`
- [ ] 1.3 Escribir `catalog.yaml` con las 11 etapas de D4 (fase, duración, variantes por rol, loops por defecto y opcionales, competencias, persona, agente) y `sources.md` a partir de `research.md`; verificar que el script de 1.4 lo carga
- [ ] 1.4 Implementar `scripts/check_simulator.py` (stdlib), que valide: cada etapa tiene `brief.md` (con fuentes), `questions.md`, `rubric.md` y `.claude/agents/netflix-<stage>.md`; rúbricas con 3–6 competencias (una de cultura) × 4 puntos × L4–L6; rutas de `study-map.yaml` existentes; problemas de coding cuyos `tests.py` pasan contra `reference.py`; generadores de take-home deterministas; la entrada del `.gitignore`; y que la skill no contiene `git add`/`commit`/`push` sobre `sessions/`. Verificar que falla con mensajes claros sobre el árbol vacío y que su test (`scripts/test_check_simulator.py`) pasa

## 2. Contenido de las etapas (en inglés, basado en `research.md`)

- [ ] 2.1 Escribir los paquetes de `recruiter-screen` y `hiring-manager` ("Why Netflix", banda de compensación, memo, deep dive de trabajo pasado y encaje con el equipo); verificar con `check_simulator.py`
- [ ] 2.2 Escribir el paquete de `culture`: 8 valores del memo de 2024, keeper test, context not control, informed captain, farming for dissent, persona de director; verificar con `check_simulator.py`
- [ ] 2.3 Escribir el paquete de `technical-screen` con sus 3 variantes (MLE: 20' proyecto + 40' ML coding; RS: stats/ML + coding breve; DS: SQL + caso); verificar con `check_simulator.py`
- [ ] 2.4 Escribir el paquete de `coding` con al menos 4 problemas Python prácticos (p. ej. NDCG@K/Precision@K, CF con coseno sobre una matriz dispersa con cold start, distintos en ventana deslizante sobre eventos, top-K en streaming) y 3 de SQL/pandas (window functions, retención por cohortes, sesionización), cada uno con `problem.md`, `starter.py`, `tests.py` y `reference.py`; verificar que `check_simulator.py` ejecuta los tests contra las referencias y pasan
- [ ] 2.5 Escribir los paquetes de `ml-fundamentals` (con la variante de caso de modelado) y `ml-depth`, con los dominios recsys, causal inference, RL/bandits, CV/NLP/LLM y ads, y contexto del foundation model y de artwork personalization; verificar con `check_simulator.py`
- [ ] 2.6 Escribir el paquete de `ml-system-design`, con al menos 6 prompts (homepage rows, artwork personalization, personalized search, Continue Watching, cold start de títulos nuevos, reentrenamiento diario a escala) y expectativas L4/L5/L6; verificar con `check_simulator.py`
- [ ] 2.7 Escribir el paquete de `experimentation` (diseño, power, peeking, interferencia, efectos heterogéneos, interleaving, CUPED, quasi-experimentos geográficos); verificar con `check_simulator.py`
- [ ] 2.8 Escribir los paquetes de `presentation` (research talk y take-home readout, con al menos 2 take-homes con `generate_data.py` con semilla) y `project-deep-dive`; verificar con `check_simulator.py`, incluido el determinismo de los datasets
- [ ] 2.9 Escribir `study-map.yaml`, que mapee competencias y temas a módulos de `recsys-course/`; verificar que `check_simulator.py` encuentra todas las rutas y que pasa en verde con las 11 etapas

## 3. Agentes

- [ ] 3.1 Escribir los 11 agentes `.claude/agents/netflix-<stage>.md`: persona de D4, realismo sin feedback, protocolo `<say>`/`<meta>`, tiempo, sondeo de cultura, regla de idioma (`en`/`es`), lectura de `brief.md` y `questions.md` (no de `rubric.md`) y preguntas no usadas en sesiones previas; verificar que `check_simulator.py` valida el frontmatter y que solo `netflix-coding` y `netflix-technical-screen` declaran `Bash`
- [ ] 3.2 Escribir `.claude/agents/netflix-evaluator.md` y `templates/scorecard.md` (cita por competencia, "no evidence", pass / no-pass, calibración de nivel, fortalezas, brechas, 1–3 recomendaciones y plan de estudio, en el idioma de la sesión); verificar evaluando una transcripción de ejemplo en `netflix-ml-interview/examples/`, en inglés y en español
- [ ] 3.3 Escribir `.claude/agents/netflix-hm-debrief.md` y `templates/debrief.md` (recomendación de cada entrevistador, consenso alto, decisión del HM como informed captain, nivel, riesgos, etapas pendientes y plan de estudio); verificar con dos casos de ejemplo: un "Strong No" bloqueante y señales mixtas

## 4. Skill orquestadora

- [ ] 4.1 Escribir `.claude/skills/netflix-ml-interview/SKILL.md`: configuración (`role`, `level`, `lang` con `en` por defecto, `stages`, dominio de `ml-depth`, feedback inmediato o diferido) por argumentos o con `AskUserQuestion`; validación contra `catalog.yaml`; loops por rol; aviso de variabilidad y de entorno efímero (`CLAUDE_CODE_REMOTE`); comprobación `git check-ignore` antes de escribir. Verificar con `stages=foo` (rechazo), con un arranque válido que muestra el resumen y con `.gitignore` sin la entrada (se niega a guardar)
- [ ] 4.2 Implementar el bucle de relevo D1–D3 (lanzar el entrevistador, `SendMessage` por turno, mostrar `<say>` sin cambios, guardar `<meta>` y el turno, cabecera de tiempo, `/time`, `/pause`, `/end-stage`) y el modo degradado D9; verificar con un `recruiter-screen` real de 3–4 turnos, comprobando que la transcripción se escribe tras cada turno
- [ ] 4.3 Implementar la entrega de material y la pausa de `presentation` (take-home generado en `sessions/<id>/takehome/`) y el espacio `code/` para coding; verificar con un take-home de Applied/DS que se genera, pausa y se reanuda
- [ ] 4.4 Implementar transiciones, orden de etapas, evaluación en segundo plano, feedback inmediato o diferido y el debrief con 2 o más etapas o con el loop incompleto; verificar con una sesión de 2 etapas cortas que produce 2 scorecards y `debrief.md`
- [ ] 4.5 Implementar `resume` y `progress` y la regeneración de `PROGRESS.md`; verificar pausando y reanudando en una conversación nueva, repitiendo una etapa y comprobando la tendencia, y confirmando con `git status` que nada de `sessions/` está rastreado

## 5. Integración

- [ ] 5.1 Añadir `.github/workflows/verificar-netflix-interview.yml`, que ejecute `check_simulator.py` y su test en los cambios de `netflix-ml-interview/**`, `.claude/agents/netflix-*` y `.claude/skills/netflix-ml-interview/**`; verificar que el workflow pasa en el PR
- [ ] 5.2 Enlazar el simulador desde el `README.md` raíz y desde `recsys-course/README.md`; verificar que los enlaces relativos resuelven
- [ ] 5.3 Smoke test end-to-end: un loop abreviado de Research Scientist L5 en inglés y una etapa suelta de Applied/DS con `lang=es`, comprobando el aislamiento entre etapas, que no hay feedback en vivo, el aviso de tiempo, el sondeo de cultura, citas en los scorecards, el debrief con enlaces a `recsys-course/` y que `git status` queda limpio; registrar los hallazgos en `netflix-ml-interview/examples/smoke-test.md` (sin datos de sesiones reales)

## Workflow follow-up

- Revisar los artefactos y ejecutar `/opsx:apply` para implementar.
- Al terminar y revisar, ejecutar `/opsx:archive` para promover los specs a `openspec/specs/`.
