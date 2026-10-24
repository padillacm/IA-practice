# Tasks

## 1. Andamiaje y validación de coherencia

- [ ] 1.1 Crear `netflix-ml-interview/` con `README.md` (uso, comandos, aviso de no afiliación, cómo ignorar `sessions/` en git) y el árbol de D5 vacío; verificar con `find netflix-ml-interview -maxdepth 2` que coincide con D5
- [ ] 1.2 Escribir `netflix-ml-interview/catalog.yaml` con las 9 etapas en orden canónico: duración, roles aplicables, variantes, competencias y nombre del agente; verificar que lo carga `python3 -c "import yaml"`, o el parser mínimo del script si no hay PyYAML
- [ ] 1.3 Implementar `netflix-ml-interview/scripts/check_simulator.py` (stdlib), que valide: cada etapa del catálogo tiene `brief.md`, `questions.md`, `rubric.md` y `.claude/agents/netflix-<stage>.md`; rúbricas con 3–6 competencias × 4 puntos × L4–L6; rutas de `study-map.yaml` existentes en `recsys-course/`; problemas de coding con `tests.py` que pasa contra `reference.py`. Verificar que falla con un mensaje claro sobre el árbol vacío y que tiene un test propio (`scripts/test_check_simulator.py`) que pasa

## 2. Contenido de las etapas

- [ ] 2.1 Investigar el proceso público de entrevistas de ML en Netflix y el memo de cultura y anotar las fuentes en cada `brief.md`; verificar que cada `brief.md` cita al menos una fuente
- [ ] 2.2 Escribir `brief.md`, `questions.md` y `rubric.md` de `recruiter-screen`, `hiring-manager` y `culture` (con preguntas conductuales y keeper test); verificar con `check_simulator.py` para esas etapas
- [ ] 2.3 Escribir los paquetes de `ml-fundamentals`, `ml-depth` y `experimentation`, con preguntas por rol y nivel y repreguntas esperadas; verificar con `check_simulator.py`
- [ ] 2.4 Escribir el paquete de `ml-system-design`, con al menos 4 prompts (homepage ranking, artwork personalization, search, cold start de títulos) y expectativas por nivel L4/L5/L6; verificar con `check_simulator.py`
- [ ] 2.5 Escribir el paquete de `project-deep-dive` (variante de presentación de investigación para Research Scientist); verificar con `check_simulator.py`
- [ ] 2.6 Escribir el paquete de `coding` con al menos 3 problemas de algoritmos/datos en Python y 2 de SQL/pandas, cada uno con `problem.md`, `starter.py`, `tests.py` y `reference.py`; verificar que `check_simulator.py` ejecuta los tests contra las referencias y pasan
- [ ] 2.7 Escribir `study-map.yaml`, que mapee competencias y temas a módulos de `recsys-course/`; verificar que `check_simulator.py` encuentra todas las rutas y que el test completo pasa en verde

## 3. Agentes

- [ ] 3.1 Escribir los 9 agentes `.claude/agents/netflix-<stage>.md`: persona, reglas de realismo sin feedback en vivo, protocolo `<say>`/`<meta>` (D2), reglas de tiempo (D3), idioma, lectura de `brief.md` y `questions.md` (no de la rúbrica) y elección de preguntas no usadas en sesiones previas; verificar que `check_simulator.py` valida el frontmatter y que solo `netflix-coding` declara `Bash`
- [ ] 3.2 Escribir `.claude/agents/netflix-evaluator.md` (scorecard con cita por competencia, "sin evidencia", señal global, calibración de nivel, fortalezas, brechas, de 1 a 3 recomendaciones y plan de estudio enlazado, en español) y una plantilla `netflix-ml-interview/templates/scorecard.md`; verificar evaluando una transcripción de ejemplo en `netflix-ml-interview/examples/` y comprobando que el scorecard cumple la plantilla
- [ ] 3.3 Escribir `.claude/agents/netflix-hiring-committee.md` y la plantilla `templates/committee.md` (Hire/No Hire, nivel, justificación con referencias a los scorecards, riesgos, etapas sin evaluar y plan de estudio); verificar con dos scorecards de ejemplo con señales mixtas

## 4. Skill orquestadora

- [ ] 4.1 Escribir `.claude/skills/netflix-ml-interview/SKILL.md`: configuración (rol, nivel, idioma, etapas, feedback inmediato o diferido) por argumentos o con `AskUserQuestion`, validación contra `catalog.yaml`, resumen y confirmación; verificar con `/netflix-ml-interview etapas=foo` (rechazo) y con un arranque válido que muestra el resumen
- [ ] 4.2 Implementar en la skill el bucle de relevo D1–D3 (lanzar el entrevistador, `SendMessage` por turno, mostrar `<say>` sin cambios, guardar `<meta>` y el turno en la transcripción, cabecera de tiempo y comandos `/tiempo`, `/pausa`, `/terminar-etapa`) y el modo degradado D7; verificar con una etapa `recruiter-screen` real de 3–4 turnos y que la transcripción se escribe tras cada turno
- [ ] 4.3 Implementar transiciones, selección y orden de etapas, evaluación en segundo plano, feedback inmediato o diferido, y la convocatoria del comité con 2 o más etapas o con el loop incompleto; verificar con una sesión de 2 etapas cortas que produce 2 scorecards y `committee.md`
- [ ] 4.4 Implementar `reanudar` y `progreso`, la regeneración de `PROGRESS.md` desde los `session.yaml` y la oferta de commit con confirmación (D8); verificar pausando una sesión, reanudándola en una conversación nueva y comprobando la tendencia en `PROGRESS.md` tras repetir una etapa

## 5. Integración

- [ ] 5.1 Añadir `.github/workflows/verificar-netflix-interview.yml`, que ejecute `check_simulator.py` y su test en los cambios de `netflix-ml-interview/**` y `.claude/agents/netflix-*`; verificar que el workflow pasa en el PR
- [ ] 5.2 Enlazar el simulador desde el `README.md` raíz y desde `recsys-course/README.md` (sección de preparación de entrevistas); verificar que los enlaces relativos resuelven
- [ ] 5.3 Smoke test end-to-end: un loop completo abreviado de Research Scientist L5 en inglés, comprobando el aislamiento entre etapas, que no hay feedback en vivo, el aviso de tiempo, que los scorecards citan la transcripción y el veredicto con enlaces a `recsys-course/`; registrar los hallazgos en `netflix-ml-interview/examples/smoke-test.md`

## Workflow follow-up

- Revisar los artefactos y ejecutar `/opsx:apply` para implementar.
- Al terminar y revisar, ejecutar `/opsx:archive` para promover los specs a `openspec/specs/`.
