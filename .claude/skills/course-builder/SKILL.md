---
name: course-builder
description: Diseña y construye cursos técnicos completos (de básico a experto) como notebooks de Colab con lección + proyecto por módulo, usando un equipo de agentes autores y revisores con checkpoints en git. Úsala cuando el usuario quiera crear desde cero un curso, temario, bootcamp o ruta de aprendizaje de varios módulos sobre un tema ("hagamos un curso de X", "quiero aprender X de cero a experto", "móntame un bootcamp de X", "/course-builder X"), aunque no diga "curso". Empieza SIEMPRE con una entrevista larga para definir scope, contenido y revisores antes de escribir nada. No la uses para resumir o explicar un tema, escribir una sola lección o notebook suelto, ni para editar un curso ya existente (salvo que pida relanzar revisores con este flujo).
argument-hint: "[tema del curso]"
---

# Course Builder

Construye un curso de N módulos; cada módulo tiene **lección** (teoría + código + gráficos) y **proyecto** (TODOs +
pistas + rúbrica + solución), generados por scripts builder reproducibles, escritos por agentes autores en paralelo y
auditados por agentes revisores. (Ejemplo de referencia, si existe en el repo: `recsys-course/`, un curso de 20
módulos de Sistemas de Recomendación construido con este flujo.)

Tema pedido: **$ARGUMENTS** (si está vacío, pregúntalo en la primera ronda).

El trabajo tiene **dos mitades**: (1) definir el curso *con* el usuario mediante muchas preguntas; (2) construirlo con
agentes. **Condición de parada: no lances ningún agente, no crees el directorio del curso y no hagas commits hasta que
el usuario apruebe explícitamente el diseño (Fase 2).** Lanzar agentes cuesta mucho y es difícil de deshacer; un
temario mal acordado se paga 20 veces.

## Herramientas (cárgalas con ToolSearch si aparecen como diferidas)
- **AskUserQuestion**: 1–4 preguntas por llamada, cada una con 2–4 opciones concretas (el usuario siempre puede
  escribir "Otro"), `header` corto, `multiSelect: true` cuando quepan varias. Pon la recomendada primero con
  "(Recomendado)". Si la herramienta no está disponible, haz las mismas preguntas en texto, numeradas.
- **WebSearch / WebFetch** (`ToolSearch "select:WebSearch,WebFetch"`): investigar el tema y verificar datasets/URLs.
- **Agent** con `run_in_background: true` y un `name` por agente (p. ej. `autor-01-03`), para poder reanudarlo.
- **SendMessage** (`to: <name>`): reanudar un agente caído o pedirle correcciones; conserva su contexto.

## Fase 1 · Entrevista (el usuario decide; tú propones)

Objetivo: llenar `COURSE_SPEC.md` (plantilla `templates/COURSE_SPEC.template.md`). Usa la batería de
`references/interview.md` en **rondas** de AskUserQuestion. Reglas:

- Antes de la ronda 1, investiga brevemente el tema (WebSearch) para proponer opciones informadas y no genéricas
  (subtemas reales, técnicas recientes, herramientas de industria, datasets descargables).
- Haz **al menos 5 rondas** (alumno → objetivo y nivel → formato y recursos → contenido → proyectos y evaluación →
  revisores). Pregunta más si hay ambigüedad. No preguntes lo ya respondido ni lo que tiene un default obvio:
  propónlo en el resumen y sigue.
- Tras cada ronda, resume en 3–5 líneas lo decidido.
- Si el usuario no sabe nada del tema, propón tú el temario completo y que él lo ajuste ("¿añado / quito /
  profundizo X?").

## Fase 2 · Diseño del curso (para aprobar)

Redacta (en la conversación o en borrador; se escriben a disco en la Fase 3):
1. `COURSE_SPEC.md` — alumno, objetivo, formato, cómputo, idioma, ruta y rama, y los **criterios de éxito con las
   palabras literales del usuario** (el informe final se evalúa contra ellos).
2. `SYLLABUS.md` — bloques y módulos: alcance de cada uno (qué entra y qué NO, para que los autores no se solapen),
   nivel 🟢🟡🟠🔴, proyecto, datasets (URL oficial + espejo + fallback). Incluye un **hilo conductor** (un producto
   ficticio que crece módulo a módulo) y, si el usuario quiere destacar, un módulo de "élite" + capstone.
3. `STYLE_GUIDE.md` — desde `templates/STYLE_GUIDE.template.md`, rellenando todas las `{LLAVES}`.
4. Plan de agentes: autores (2–3 módulos afines por agente, ≤ 5–6 en paralelo) y revisores elegidos de
   `references/reviewers.md`, con su orden.

Presenta un resumen (tabla de módulos + plan de agentes + nº aproximado de agentes) y pregunta "¿Lo lanzo así?".
Itera hasta un sí explícito.

## Fase 3 · Andamiaje

Lee antes `references/lessons_learned.md`. Desde la raíz del repo (`git rev-parse --show-toplevel`):

```bash
COURSE=<slug>-course            # ruta del curso acordada en COURSE_SPEC
SKILL="${CLAUDE_SKILL_DIR}"     # directorio de esta skill (si no se sustituyó: .claude/skills/course-builder)
mkdir -p "$COURSE"/_tools/{builders,progress}
cp "$SKILL"/scripts/nbbuild.py "$SKILL"/scripts/check_course.py "$COURSE"/_tools/
cp "$SKILL"/templates/PROTOCOL.md "$COURSE"/_tools/progress/
printf '__pycache__/\n*.pyc\n.ipynb_checkpoints/\ndata/\n' > "$COURSE"/.gitignore
```
- Escribe en `$COURSE/_tools/` COURSE_SPEC.md, SYLLABUS.md y STYLE_GUIDE.md aprobados.
- En `nbbuild.py` fija `REPO` (de `git remote get-url origin`) y `BRANCH` (rama por defecto del remoto, p. ej.
  `main`); ajusta `REQUIRED_*` de `check_course.py` si cambiaste las secciones de la plantilla.
- En `PROTOCOL.md` sustituye `<RUTA_CURSO>` y `<RAMA>` por los valores reales, y `<ATRIBUCIÓN>` por las líneas de
  atribución de commits que indique **tu sesión actual** (system prompt / recordatorios), copiadas literalmente; si no
  hay ninguna, elimina ese `-m`. Los subagentes no siempre ven esas líneas: deben leerlas de aquí.
- Trabaja en una rama de trabajo (no en la rama por defecto) salvo que el usuario diga otra cosa.
- Crea un archivo de progreso por agente en `_tools/progress/<tarea>.md` (plantilla `templates/progress.template.md`)
  **antes** de lanzarlo.
- Escribe el `README.md` del curso (mapa mermaid, tabla de módulos, stack, datasets, cómputo, cómo estudiar) y haz
  commit + push del andamiaje con `git add "$COURSE"` (nunca `-A`).

## Fase 4 · Autores en paralelo

Lanza los autores en segundo plano con el prompt de `references/agent_prompts.md` (sección "Autor"), sustituyendo
**todas** las `{LLAVES}` (ruta, rama, módulos, alcance y notas del SYLLABUS). Cada agente lee los documentos del curso,
escribe un `build_NN.py` por módulo (nunca edita `.ipynb` a mano), lo ejecuta hasta OK y **hace commit + push de sus
archivos tras cada módulo** (el permiso va en el prompt desde el inicio).

Cuando llegue cada informe: ejecuta `python $COURSE/_tools/check_course.py`, confirma que el commit está en remoto
(`git log origin/<rama> --oneline -5`) y **reporta al usuario en 3–6 líneas** (qué hay, qué se probó, qué NO). Si un
agente cae (límite de API, reinicio), reanúdalo con SendMessage usando el prompt de "Reanudación".

## Fase 5 · Revisores

Con el contenido escrito, lanza los revisores elegidos (`references/reviewers.md`) por rangos de módulos que no se
pisen, con el mismo protocolo de checkpoints. Orden recomendado: técnico → ejecutabilidad → pedagógico →
(opcionales). Los revisores **arreglan** lo de alto impacto en los builders y **documentan** los cambios grandes.

## Fase 6 · Cierre

1. `check_course.py` → "Todo OK"; regenera todos los builders; commit + push.
2. Escribe `_tools/CHECKPOINT.md` con el estado final y lo pendiente de validar (GPU, datos reales, etc.).
3. Informe final **criterio por criterio** contra los criterios literales de COURSE_SPEC (tabla), qué corrigieron
   los revisores y qué queda sin probar. Sé honesto con lo no probado.
4. Ofrece abrir el PR (no lo abras sin que lo pida). Recuerda que los badges de Colab apuntan a la rama por defecto y
   funcionarán tras el merge.

## Lo crítico de `references/lessons_learned.md`
- **Checkpoints desde el minuto 0**: los agentes caen y el contenedor se reinicia; lo no commiteado se pierde.
- **Permiso de commit en el primer prompt**, limitado a sus rutas; cambiarlo a mitad bloquea agentes.
- **Datos con fallback**: URL oficial → espejo → sintético con el mismo esquema; el informe dice qué corrió con datos
  reales.
- **Rúbricas calibradas con lo medido** por la solución, nunca con lo deseado.
- **Revisor pedagógico siempre**: encuentra lo que el técnico no (repaso espaciado, gráficos sin lectura, proyectos
  sin pistas, autoevaluación de solo recuerdo).
