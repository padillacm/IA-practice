---
name: course-builder
description: Diseña y construye cursos técnicos completos (de básico a experto) como notebooks de Colab con lección + proyecto por sesión, usando un equipo de agentes autores y revisores con checkpoints. Úsala cuando el usuario quiera crear un curso, temario, bootcamp o ruta de aprendizaje sobre un tema ("hagamos un curso de X", "quiero aprender X de cero a experto", "/course-builder X"). Empieza SIEMPRE con una entrevista larga para definir scope, contenido y revisores antes de escribir nada.
---

# Course Builder

Construye cursos como el de `recsys-course/` (Sistemas de Recomendación: de cero a nivel Netflix): N módulos, cada uno con
**lección** (teoría + código + gráficos) y **proyecto** (TODOs + rúbrica + solución), generados por scripts
reproducibles, escritos por agentes expertos en paralelo y auditados por agentes revisores.

El trabajo tiene **dos mitades**: (1) definir el curso *con* el usuario mediante muchas preguntas; (2) construirlo con
agentes. **No lances ningún agente ni escribas contenido hasta que el usuario apruebe el documento de diseño.**

## Fase 1 · Entrevista (el usuario decide; tú propones)

Objetivo: llenar `COURSE_SPEC.md` (plantilla en `templates/COURSE_SPEC.template.md`). Usa la batería de preguntas de
`references/interview.md`, en **rondas** con la herramienta AskUserQuestion (≤ 4 preguntas por llamada, opciones
concretas, la recomendada primero con "(Recomendado)"). Reglas:

- Antes de la ronda 1, investiga brevemente el tema (WebSearch) para proponer opciones informadas y no genéricas
  (subtemas reales, técnicas recientes, herramientas de industria, datasets disponibles).
- Haz **al menos 5 rondas** (perfil del alumno → objetivo y nivel → formato y recursos → contenido → proyectos y
  evaluación → revisores). Pregunta más si hay ambigüedad. No preguntes lo que ya se respondió ni lo que tiene un
  default obvio: propónlo y sigue.
- Tras cada ronda, resume en 3–5 líneas lo que quedó decidido.
- Si el usuario no sabe nada del tema (como pasó con recsys), tú propones el temario completo y él lo ajusta; las
  preguntas de contenido pasan a ser "¿añado / quito / profundizo X?".

## Fase 2 · Diseño del curso (para aprobar)

Con las respuestas, escribe en el directorio del curso (`<slug>-course/_tools/`):
1. `COURSE_SPEC.md` — perfil del alumno, objetivo, formato, recursos de cómputo, idioma, criterios de éxito **literales
   del usuario** (se usarán en el informe final).
2. `SYLLABUS.md` — temario por bloques y módulos: alcance de cada módulo (qué entra y qué NO, para que los autores no se
   solapen), nivel 🟢🟡🟠🔴, proyecto, datasets. Incluye el **hilo conductor** (un producto ficticio que se construye
   a lo largo del curso, como CineMatch) y un módulo final de "élite" + capstone si el usuario quiere destacar.
3. `STYLE_GUIDE.md` — desde `templates/STYLE_GUIDE.template.md`, adaptado (alumno, idioma, emojis, mínimos de gráficos).
4. Plan de agentes: qué autores (2–3 módulos por agente, agrupados por afinidad) y qué revisores (de
   `references/reviewers.md`) con su orden.

Presenta un resumen (tabla de módulos + plan de agentes + coste aproximado en agentes) y **pide aprobación explícita**.
Itera hasta que diga que sí.

## Fase 3 · Andamiaje

```bash
COURSE=<slug>-course
mkdir -p $COURSE/_tools/{builders,progress}
cp .claude/skills/course-builder/scripts/nbbuild.py      $COURSE/_tools/
cp .claude/skills/course-builder/scripts/check_course.py $COURSE/_tools/
cp .claude/skills/course-builder/templates/PROTOCOL.md   $COURSE/_tools/progress/
printf '__pycache__/\n*.pyc\n.ipynb_checkpoints/\ndata/\n' > $COURSE/.gitignore
```
- Ajusta `REPO`/`BRANCH` en `nbbuild.py` (badge de Colab) y `REQUIRED_*` en `check_course.py` si cambiaste la plantilla.
- Crea un archivo de progreso por agente en `_tools/progress/<tarea>.md` (plantilla `templates/progress.template.md`)
  **antes** de lanzarlo.
- Escribe el `README.md` del curso (mapa mermaid, tabla de módulos, stack, datasets, presupuesto de cómputo, cómo
  estudiar) y haz commit + push del andamiaje.

## Fase 4 · Autores en paralelo

Lanza los agentes autores en segundo plano con el prompt de `references/agent_prompts.md` (sección "Autor"),
rellenando módulos, alcance y notas específicas del SYLLABUS. Cada agente:
- lee COURSE_SPEC, SYLLABUS, STYLE_GUIDE, PROTOCOL y su archivo de progreso;
- escribe `build_NN.py` por módulo (nunca edita `.ipynb` a mano) y lo ejecuta hasta OK;
- **hace commit + push de sus archivos tras cada módulo** (permiso explícito en el prompt desde el inicio).

Mientras trabajan: cuando llegue cada informe, ejecuta `check_course.py`, revisa que el commit esté en remoto y
**reporta al usuario en 3–6 líneas** (qué hay, qué se probó, qué NO se pudo probar). Si un agente cae (límite de API,
reinicio), reanúdalo con SendMessage indicándole que lea su progreso y siga desde la primera casilla sin marcar.

## Fase 5 · Revisores

Con todo el contenido escrito, lanza los revisores elegidos (prompts en `references/reviewers.md`), repartidos por
rangos de módulos que no se pisen. Mismo protocolo de checkpoints. Orden recomendado: técnico → ejecutabilidad →
pedagógico → (opcionales) referencias, élite, consistencia de lenguaje. Los revisores **arreglan** lo de alto impacto
en los builders y **documentan** los cambios grandes como recomendaciones.

## Fase 6 · Cierre

1. `check_course.py` → Todo OK; regenera todos los builders; commit + push.
2. Actualiza `_tools/CHECKPOINT.md` con el estado final y lo pendiente de validar (GPU, datos reales, etc.).
3. Informe final al usuario **criterio por criterio** usando los criterios literales de COURSE_SPEC (tabla), lo que lo
   hace destacar, lo que corrigieron los revisores y lo que queda por validar. Sé honesto con lo no probado.
4. Ofrece abrir el PR (no lo abras sin que lo pida).

## Lecciones aprendidas (léelas antes de la Fase 3)

`references/lessons_learned.md` resume los fallos reales del primer curso y cómo evitarlos. Las críticas:
- **Checkpoints desde el minuto 0.** Los agentes caen por límites de API y el contenedor se reinicia: lo no commiteado
  se pierde. Commit + push tras cada subtarea, por cada agente, solo de sus rutas.
- **Da permiso de commit en el primer prompt.** Si dices "no commitees" y luego cambias de idea, el agente puede
  quedar bloqueado por permisos.
- **El proxy bloquea datasets** (GroupLens, Hugging Face, Kaggle…): exige cadena de descarga oficial → espejo → datos
  sintéticos con el mismo esquema, y que se diga en el informe qué se probó con datos reales.
- **Calibra las rúbricas con lo medido**, nunca con lo deseado; y repite la calibración con datos reales.
- **El revisor pedagógico encuentra lo que el técnico no**: repaso espaciado, gráficos sin lectura, proyectos sin
  pistas graduadas, autoevaluación de solo recuerdo. Inclúyelo siempre.
