# Tasks

Organización en paquetes de trabajo (WP), cada uno con sus propios archivos. Los formatos de D10 (design.md) están congelados: ningún paquete los cambia sin actualizar antes el design. Ningún paquete hace commit: integra y commitea el orquestador de la implementación.

## 1. WP1 · Fundamentos: repo, catálogo, validador y helper

- [ ] 1.1 Crear el `.gitignore` raíz con `netflix-ml-interview/sessions/` y `.claude/settings.json` con permisos para `Bash(python netflix-ml-interview/scripts/sim.py:*)`, `Bash(python3 netflix-ml-interview/scripts/sim.py:*)` y `Bash(py netflix-ml-interview/scripts/sim.py:*)`. Verificar que `git check-ignore -q netflix-ml-interview/sessions/.probe` devuelve 0 y que el JSON es válido.
- [ ] 1.2 Crear `netflix-ml-interview/` con el árbol de D6, `README.md` en español y `requirements.txt` (numpy, pandas). El README debe cubrir: uso, comandos `::`, `lang`, regla de honor, escala pedagógica, niveles L4/L6 extrapolados, una fase por conversación y que las sesiones son locales. Verificar con `find netflix-ml-interview -maxdepth 2` que el árbol coincide con D6.
- [ ] 1.3 Escribir `catalog.yaml` según D10, con las 14 etapas, las variantes, `variant_by_role`, los loops de los 3 roles con su fase por entrada, `cut`, `default_domain`, pesos por rol, los dominios, las personas con estilo y las competencias con `core`. Escribir también `sources.md`, con la confianza por etapa y las duraciones marcadas como supuestos, a partir de `research.md`. Verificar con 1.5.
- [ ] 1.4 Escribir `templates/session.yaml`, `templates/scorecard.md` y `templates/debrief.md` con los formatos de D10 y el aviso "regla pedagógica del simulador". Verificar que `sim.py` (1.6) los carga.
- [ ] 1.5 Implementar `scripts/check_simulator.py` (stdlib) con estas comprobaciones:
  - el schema del catálogo, y que cada entrada de loop sea compatible con su rol y tenga peso;
  - por etapa: `brief.md` con fuentes, `questions.md` según D10 con un mínimo de 2 `main` por rol aplicable × variante, y `rubric.md` según D10 (versión, 3–6 competencias con ids únicos y al menos una core, cultura con `memo_values`, barras L4/L5/L6 distintas y sin adjetivos de una lista negra);
  - los 17 agentes: `name` igual al nombre de archivo, tools sin Bash/Write y modelo según D5;
  - las rutas de `study-map.yaml`;
  - en coding, que `tests.py` pase contra `reference.py`, saltando con aviso si faltan dependencias;
  - en ai-assisted, que los tests del workspace pasen y que cada `hidden_test` sea válido;
  - que los generadores de take-home sean deterministas;
  - la entrada del `.gitignore`, y que la skill no contenga `git add`, `commit` ni `push`.

  Verificar que falla con mensajes claros sobre el árbol vacío y que `scripts/test_check_simulator.py` pasa.
- [ ] 1.6 Implementar `scripts/sim.py` (stdlib, con `pathlib` y portable a Windows) con los subcomandos de D6: `guard` (D8), `new`, `select`, `turn` (segmentos, `time_scale` y flags 80/90/100 %), `log`, `pause`, `run-tests`, `apply`, `verify-scorecard`, `rebuild`, `state`, `progress` e `info`. Verificar con `scripts/test_sim.py`, que debe cubrir:
  - el guard en un repo temporal: ignorado, no ignorado, con archivos rastreados y sin repo;
  - `git status --porcelain` vacío tras crear una sesión;
  - el cálculo de tiempo con pausas;
  - que la selección excluya los ids ya usados;
  - que la verificación de citas detecte una cita inventada y una que viene de un turno del entrevistador;
  - que el filtro elimine `notes_private`;
  - que `progress` agrupe por etapa, variante y competencia y marque los cambios de nivel y de versión.

## 2. WP2 · Contenido de etapas (en inglés; 2a–2e en paralelo, cada uno dueño de sus directorios)

- [ ] 2.1 (2a) Escribir `recruiter-screen`, `hm-screen`, `hm-onsite`, `culture` y `partnership` (brief, questions y rubric). Deben incluir:
  - "Why Netflix" y "personal top of market", con el aviso de no citar el salario como motivación (Baja);
  - autopromoción con métricas;
  - preguntas sobre el memo, que no haberlo leído "is a fail";
  - los 8 valores con su texto literal, el keeper test, context not control, informed captain, farming for dissent y disagree then commit, con una muestra de 3–4 valores;
  - un director con tiempo para las preguntas del candidato;
  - en `partnership`: colaboración, stakeholders y dependencias, con la opción de que lo haga un director;
  - en `hm-onsite`: el encaje con el dominio, y para L6, alcance entre equipos.

  Verificar con `check_simulator.py`.
- [ ] 2.2 (2b) Escribir `coding` con:
  - al menos 6 problemas `practical`: dedup de la homepage por filas, duplicados en el historial de visionado, rotación de billboard, clave aleatoria ponderada, sliding window sobre eventos y NDCG@K/P@K;
  - 2 de `ml-coding`: CF con coseno sobre una matriz dispersa y multiplicación de matrices dispersas;
  - 3 de `sql-pandas` sobre `sqlite3`: window functions, retención por cohortes y sesionización;
  - 2 de `lc-style`.

  Cada problema lleva `problem.md`, `starter.py`, `tests.py`, `reference.py` y `followups.md` (escala y concurrencia). Escribir también `technical-screen` con sus variantes:
  - `ml-coding`;
  - `ml-framing-coding`;
  - `sql`, con `datasets/*.sql`;
  - `stats` (regresión, tipo I/II, FDR, CLT/t, bootstrap, potencia/MDE y causal opcional);
  - `fundamentals-pr-review`, con 2 PRs de feature pipelines y su `issues.md`;
  - `intern-project-coding`;
  - `oa`.

  Verificar que `check_simulator.py` ejecuta los tests contra las referencias y pasan.
- [ ] 2.3 (2c) Escribir `ai-assisted-coding` con al menos 3 repos (p. ej. un servicio de features con caché, un job de evaluación offline y un deduplicador de catálogo). Cada uno lleva `workspace/` con tests en verde, `tasks.md`, `notes.md` y `flaws.yaml` con 0, 1 y 2 errores respectivamente, cada error con su `hidden_test`. Verificar con `check_simulator.py`.
- [ ] 2.4 (2d) Escribir `ml-fundamentals` con dos variantes:
  - `breadth`: bias-variance, L1/L2, GBDT y early stopping, embeddings de co-watch, cold start, popularity bias, métricas de ranking (P@K, R@K, MAP, NDCG, cobertura, diversidad), CF, árboles vs redes, monitorización post-deploy, Bayes, forward pass, KNN, KV cache y attention;
  - `modeling-case`.

  Escribir también `ml-depth` por dominio: recsys (con foundation model, GenRec, semantic IDs y artwork personalization), experimentation, causal-inference, rl-bandits, cv, nlp-llm, ads y ml-platform. Brief con la regla: "GenRec y las demás publicaciones son contexto de discusión; nunca se preguntan cifras". Para L6, deep dive de arquitectura. Verificar con `check_simulator.py`.
- [ ] 2.5 (2d) Escribir `ml-system-design` con:
  - variante `design`, con al menos 10 prompts etiquetados por dominio: homepage rows, artwork personalization, personalized search, search autocomplete, Continue Watching, cold start de títulos, reentrenamiento diario, ML job scheduler, compute allocation, portal ML y feature serving en tiempo real;
  - variante `problem-framing` (RS).

  Cada prompt lleva sus puntos de señal (incluidos disponibilidad, seguridad y validación online: interleaving → A/B) y expectativas L4/L5/L6. Escribir también `experimentation`:
  - `design-case`: frequency cap de anuncios, ordenación de filas con solapamiento y retención, y artwork;
  - `analysis-case`: cuantiles, bootstrap, efectos heterogéneos, ajuste por covariables y FDR;
  - las dos con interleaving, CUPED, quasi-experimentos y peeking.

  Verificar con `check_simulator.py`.
- [ ] 2.6 (2e) Escribir:
  - `presentation`: `research-talk` de 45' y `take-home` con al menos 2 take-homes cuyo `generate_data.py` use semilla;
  - `project-deep-dive`, como "reverse system design" con partes asignables del background.

  Verificar con `check_simulator.py`, incluido el determinismo.

## 3. WP3 · Agentes

- [ ] 3.0 Spike del relevo en un directorio temporal fuera de `.claude/agents/` (dos agentes de prueba lanzados como general-purpose). Hay que confirmar:
  - la entrega asíncrona de `SendMessage` como notificación;
  - qué pasa con `::time` y `/time` en el prompt;
  - la latencia y el coste por turno;
  - que el contrato `<say>`/`<meta>` se respeta durante 5 turnos.

  Documentar los resultados en `.claude/skills/netflix-ml-interview/references/relay-protocol.md` (la máquina de estados de D1) y ajustar D1–D3 si algo no se confirma.
- [ ] 3.1 Escribir un esqueleto común de prompt para los entrevistadores. Debe incluir el contrato D2 literal, la persona y el estilo del catálogo, el control del ritmo, la obediencia a los flags de tiempo, el realismo sin feedback, las pistas con nivel, el registro de cultura, la regla de idioma, la lectura del *launch packet* en el primer turno y la prohibición de leer `rubric.md`. Con ese esqueleto, generar los 14 `.claude/agents/netflix-<stage>.md`. Verificar con `check_simulator.py`.
- [ ] 3.2 Escribir `.claude/agents/netflix-ai-pair.md`: devuelve explicación más diff y activa los errores de `flaws.yaml` cuando el prompt toca esa zona, informándolo en `<meta>`. Verificar invocándolo directamente con dos prompts fijos sobre un repo (uno toca la zona y otro no) y aplicando el `hidden_test`.
- [ ] 3.3 Escribir `.claude/agents/netflix-evaluator.md`, que implementa la regla pedagógica de D7: evidencia `{turn_id, quote}` de turnos del candidato, efecto de las pistas, `end_reason`, "no evidence", respuesta Yes modelo y plan de estudio. Escribir también `.claude/agents/netflix-hm-debrief.md` con sus modos `cut` y `final`: paso 1 determinista, paso 2 con override justificado, cultura por valor, orden de catálogo y sin evidencia nueva. Verificar con 4.2.

## 4. WP4 · Calidad de la evaluación

- [ ] 4.1 Escribir `study-map.yaml`: cada `<stage>.<competency_id>` apunta a un módulo de `recsys-course/` o a una alternativa (`practice_stage` o `resource`). Verificar con `check_simulator.py`.
- [ ] 4.2 Crear un gold set en `netflix-ml-interview/examples/gold/` para `ml-system-design`, `coding` y `culture`. Debe tener transcripciones fuerte, límite y débil, larga-superficial, con halo, con manipulación y la misma en EN/ES, con las puntuaciones esperadas (±1) y la recomendación. Añadir 3 casos de debrief: Strong No bloqueante, señales mixtas y referred. Verificar puntuando cada caso 3 veces, comprobando con `sim.py verify-scorecard` y registrando los resultados en `RESULTS.md`. La recomendación y la decisión deben coincidir en las 3 ejecuciones.

## 5. WP5 · Skill orquestadora

- [ ] 5.1 Escribir `.claude/skills/netflix-ml-interview/SKILL.md` (en inglés), con `allowed-tools` Agent, SendMessage, ToolSearch, AskUserQuestion, Bash, Read, Write, Edit, Glob y Grep. Debe cubrir:
  - los subcomandos `stages`, `resume` y `progress`;
  - la configuración por argumentos o con AskUserQuestion: rol (con su equivalencia de títulos), nivel (L5 por defecto), `lang`, `stages` (fases y `stage@variant`), dominio, feedback, `time_scale` y background;
  - la validación de los valores con el catálogo;
  - los avisos de variabilidad y de entorno efímero, y `sim.py guard` antes de escribir.

  Verificar:
  - con `stages=foo` y `coding@foo`, que rechaza;
  - con un arranque válido, que muestra el resumen;
  - con el `.gitignore` sin la entrada, que se niega a guardar.
- [ ] 5.2 Implementar el relevo D1–D3 siguiendo `relay-protocol.md`:
  - el *launch packet* preparado por `sim.py select`;
  - un `sim.py turn` por turno;
  - el saneado de `<candidate>`;
  - `<say>` mostrado sin cambios y `<meta>` registrado;
  - reformateo con un solo reintento;
  - mensajes retenidos;
  - los comandos `::time`, `::pause`, `::end` y `::help`;
  - los tests ejecutados por el hilo principal con `sim.py run-tests`;
  - el modo degradado D9.

  Verificar con un guion de candidato de 6 turnos para `recruiter-screen`. La comprobación posterior con `sim.py state` y un grep sobre la transcripción debe dar: tantos `<say>` como turnos, ningún término de la rúbrica, un flag de tiempo con `time_scale` bajo y transcripción escrita tras cada turno.
- [ ] 5.3 Implementar `::ai` y `::apply` con `netflix-ai-pair` (resumen y `flaws_triggered` pasados al entrevistador como `<orchestrator private>`), y los materiales de `presentation` con su pausa. Verificar con un repo de `ai-assisted-coding` y un take-home de `ds`.
- [ ] 5.4 Implementar las instancias y su orden por fases, las transiciones, la evaluación según el modo de feedback con barrera, la verificación de citas, el corte (con modo práctica), el debrief final y la oferta de repetir la VO2 si el resultado es referred. Verificar con una sesión `mle` de una etapa de VO1 y otra de VO2 que produzca los scorecards, el corte y `debrief.md`.
- [ ] 5.5 Implementar `resume` (reconstruyendo con `sim.py rebuild` las instancias en curso, y eligiendo entre varias sesiones) y `progress`. Verificar que una etapa pausada a mitad continúa en una conversación nueva sin que el entrevistador se vuelva a presentar, que al repetir una etapa la tendencia aparece en `PROGRESS.md` y que `git status` queda limpio.

## 6. WP6 · Integración

- [ ] 6.1 Añadir `.github/workflows/verificar-netflix-interview.yml`: instala `requirements.txt` y ejecuta `check_simulator.py`, `test_check_simulator.py` y `test_sim.py`. Se dispara con cambios en `netflix-ml-interview/**`, `.claude/agents/netflix-*.md`, `.claude/skills/netflix-ml-interview/**`, `.gitignore` y el propio workflow. Verificar que pasa en el PR.
- [ ] 6.2 Enlazar el simulador desde el `README.md` raíz y desde `recsys-course/README.md`. Verificar que los enlaces relativos resuelven.
- [ ] 6.3 Smoke test end-to-end con tres sesiones: un `rs` L5 en inglés (VO1 abreviada), un `mle` con corte y `ai-assisted-coding`, y una etapa suelta de `ds` con `lang=es`. Comprobar: aislamiento entre etapas, ausencia de feedback en vivo, flags de tiempo, citas verificadas, decisión según la regla, enlaces a `recsys-course/` y `git status` limpio. Registrar los hallazgos en `netflix-ml-interview/examples/smoke-test.md`, sin datos de sesiones reales.

## Workflow follow-up

- Revisar los artefactos y ejecutar `/opsx:apply` para implementar.
- Al terminar y revisar, ejecutar `/opsx:archive` para promover los specs a `openspec/specs/`.
