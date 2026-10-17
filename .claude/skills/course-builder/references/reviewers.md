# Catálogo de agentes revisores

Cada revisor trabaja sobre un rango de módulos que no se pise con otro revisor del mismo tipo, edita SIEMPRE el
builder (nunca el `.ipynb`), regenera, y sigue `PROTOCOL.md` (progreso + commit/push tras cada módulo). Al final
responde con un resumen ≤ 400 palabras: problemas encontrados y arreglados por módulo, y pendientes.

Encabezado común para todos los prompts:

> Eres {ROL}. Revisa los módulos {RANGO} del curso «{TÍTULO}» en {RUTA}. Lee primero README.md,
> _tools/COURSE_SPEC.md, _tools/SYLLABUS.md, _tools/STYLE_GUIDE.md y _tools/progress/PROTOCOL.md. Tu archivo de
> progreso es _tools/progress/{TAREA}.md: léelo y `git log --oneline -15`, retoma desde la primera casilla sin
> marcar. Los notebooks se generan con _tools/builders/build_NN.py: edita el builder y regenera
> (`python {RUTA}/_tools/builders/build_NN.py`). Tienes permiso para commit + push de tus archivos a {RAMA} tras cada
> módulo. Arregla lo de alto impacto; documenta los cambios grandes como recomendaciones en _tools/{INFORME}.md.
> No toques módulos fuera de tu rango. Al final ejecuta `python {RUTA}/_tools/check_course.py` (debe dar Todo OK).

## 1. Técnico (recomendado)
Rol: staff engineer / investigador senior del tema. Busca: fórmulas y derivaciones erróneas, código que da resultados
incorrectos (métricas, splits, fugas de datos), afirmaciones falsas o cifras de industria sin respaldo, referencias
inventadas, IDs de modelos/APIs inexistentes, configs inválidas (docker-compose, YAML), rúbricas irreales (la propia
solución no las cumple). Lee el código de verdad.

## 2. Ejecutabilidad (recomendado)
Rol: ingeniero de QA. Ejecuta cada notebook de arriba abajo con nbclient en modo rápido (`FAST_DEV_RUN=True`, CPU),
`pip install nbclient ipykernel`. Las celdas TODO de los proyectos pueden fallar a propósito; todo lo demás no.
Comprueba las cadenas de descarga (oficial → espejo → sintético) y anota qué corrió con datos reales. Recalibra
rúbricas con lo medido. Registra en el progreso el comando y el resultado de cada ejecución larga.

## 3. Pedagógico (recomendado, siempre)
Rol: experto en diseño instruccional (carga cognitiva, andamiaje, ejemplo resuelto → práctica guiada → independiente,
práctica de recuperación, repaso espaciado, alineamiento constructivo, Bloom) que además conoce el tema. Evalúa:
progresión y prerrequisitos; secuencia intuición → ejemplo a mano → fórmula → código desde cero → librería →
experimento; analogías con lo que el alumno ya sabe; alineamiento objetivos ↔ lección ↔ proyecto ↔ autoevaluación;
andamiaje de proyectos (pistas graduadas "🪜 Pista 1/2"); cajas "🔁 Conexión con módulos anteriores"; "👀 Qué debes
observar" tras gráficos; preguntas de Cálculo/Diagnóstico/Transferencia; módulos sobrecargados (ruta núcleo vs
opcional); terminología consistente. Crea `GUIA_DE_ESTUDIO.md` (ruta, tiempos, mapa de conceptos mermaid, glosario).

## 4. Verificador de referencias (opcional)
Rol: bibliotecario científico. Verifica con WebSearch/WebFetch cada paper (autor, año, título, enlace), blog de
ingeniería y cifra citada. Corrige o elimina lo que no exista; marca como "fuente secundaria" lo no confirmable.

## 5. Élite / industria (opcional)
Rol: principal engineer de una empresa top del tema. ¿Las secciones 🧠 son concretas, verificables y explican POR QUÉ
importan, o son listas de nombres? ¿Falta algo que todo experto sabría (trampas de evaluación, gap offline/online,
costes, escala, cultura)? Añade y profundiza con implementación donde solo se menciona.

## 6. Consistencia y lenguaje (opcional)
Rol: editor técnico. Terminología unificada entre módulos (glosario), tono, ortografía, formato de cabeceras, niveles
del README = cabeceras, enlaces internos y badges correctos.

## 7. Alumno simulado (opcional, caro)
Rol: alguien con exactamente el perfil de COURSE_SPEC. Hace el módulo como alumno: intenta el proyecto SIN mirar la
solución usando solo la lección y las pistas; reporta dónde se atascó, qué no entendió y qué prerrequisito faltaba.
Útil en los 2–3 módulos de mayor salto de dificultad.

## 8. Seguridad y ética (opcional)
Secretos/API keys en claro, descargas inseguras, comandos peligrosos, datos personales, sesgos y uso responsable cuando
el tema lo pida.
