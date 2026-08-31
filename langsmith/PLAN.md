# Plan: curso de LangSmith

Plan del curso de LangSmith que vive en este directorio, complementario al curso de
LangGraph que está en `langgraph/` (38 notebooks, módulos 0-7).

> **Estado:** en construcción, sobre la rama `claude/langgraph-notebooks-course-nokcof`
> —la única para la que tengo permiso—, en el directorio `langsmith/`. Fase 1 en curso:
> infraestructura lista y verificada, notebooks 00, 01 y 02 escritos.
>
> Este documento se corrige a medida que el SDK desmiente cosas. Las correcciones se
> dejan escritas y marcadas en vez de reescribirse en silencio, porque saber qué se
> creyó y por qué era falso vale tanto como el dato bueno.

---

## 1. La decisión que condiciona todo: qué puedo verificar

El curso de LangGraph tiene una propiedad que lo hace fiable: **cada afirmación técnica se
comprobó ejecutándola**, y las que resultaron falsas están documentadas como tales. Antes de
planificar nada, comprobé si eso se puede sostener con LangSmith.

**No del todo, y conviene decirlo por delante.** `api.smith.langchain.com` está bloqueado
desde mi entorno de trabajo. Pero la frontera no cae donde esperaba:

| Se puede verificar **ejecutándolo** (sin clave ni red) | Solo se puede validar estáticamente |
|---|---|
| `@traceable`: decorar, anidar, tipos de run | `Client()` contra la API |
| `RunTree`: construir el árbol, `dotted_order`, jerarquía | Crear datasets y ejemplos |
| El **anonimizador** (`create_anonymizer`, reglas, recursión) | `evaluate()` y los experimentos |
| `wrap_openai` / `wrap_anthropic` / `wrap_gemini` | Colas de anotación |
| **`openevals` y `agentevals`**: evaluadores con juez local | Paneles, monitores, alertas |
| Los esquemas (`langsmith.schemas`) y el plugin de pytest | Prompt Hub y Playground |
| Diseño de datasets como ficheros, antes de subirlos | Reglas y automatizaciones |

Comprobado ya, en este entorno y sin clave:

```
@traceable sin clave ni red -> 42
RunTree local -> raiz: raiz | hijos: ['modelo'] | dotted_order presente: True
anonimizador -> {'messages': [{'content': 'escribe a [correo]'}], 'meta': {'cc': '[correo]'}}
```

**Consecuencia para el plan**, y es la decisión de diseño más importante:

> Cada notebook se escribe para funcionar en **dos modos**. Sin clave se ejecuta entero y
> enseña todo lo verificable en local. Con tu clave, las celdas marcadas se conectan de
> verdad. Es el mismo patrón que ya usa el notebook 18 del curso de LangGraph con
> `langgraph dev`: si el servicio no está, la celda lo dice y sigue sin fallar.

Eso permite mantener el aparato de verificación (los 38 notebooks se ejecutan en CI sin
gastar cuota) y ser honesto sobre la cobertura: el README llevará el porcentaje real de
celdas verificadas por ejecución frente a las validadas estáticamente. **No voy a afirmar
que he comprobado algo que no he podido comprobar.**

---

## 2. La otra restricción: 5.000 trazas al mes

El plan Developer sin método de pago da **5.000 trazas/mes y un mes de retención**. Un curso
descuidado se lo funde en dos tardes: cada `evaluate()` sobre 50 ejemplos con 3 repeticiones
son 150 trazas, y un agente genera varias trazas por ejecución.

Esto no es un inconveniente: es **material del curso**. El curso de LangGraph ya trata el
coste como una decisión de ingeniería (notebooks 19, 23, 30); aquí se hace lo mismo con el
presupuesto de trazas.

Medidas concretas que entran en el diseño:

- Un helper `presupuesto_de_trazas()` en `utils/`, que estima el consumo **antes** de lanzar
  un experimento y avisa si se pasa de un tope que tú fijas.
- Cada notebook declara en su cabecera su **consumo estimado de trazas**, igual que los del
  curso de LangGraph declaran su coste en euros.
- Los proyectos usan conjuntos pequeños (20-30 ejemplos) y explican cómo escalarlos.
- Muestreo en producción como tema de primera clase, no como nota al pie.
- Un proyecto de LangSmith aparte para el curso, para no ensuciar el tuyo.

Estimación total del curso completo: **por debajo de 1.500 trazas**, menos de un tercio de
la cuota mensual.

---

## 3. Qué NO va a estar (y dónde está ya)

Es un complemento, así que lo que ya está cubierto se referencia, no se repite. Esto es
la mitad del valor del plan:

| Tema | Ya está en | Qué haría el curso de LangSmith |
|---|---|---|
| Evaluación de trayectorias con `agentevals` | LangGraph nb 27 | Lo lleva a LangSmith: los mismos evaluadores dentro de `evaluate()` |
| Conjunto dorado y varianza | LangGraph nb 17 | Reutiliza el conjunto; añade versionado y comparación de experimentos |
| OpenTelemetry sin LangSmith | LangGraph nb 17 | Complementa con el camino inverso: OTel **hacia** LangSmith |
| Despliegue, `langgraph.json`, assistants | LangGraph nb 18, 25, 26, 28 | Solo el puente: prompts versionados ↔ assistants |
| Datos personales en las trazas | LangGraph nb 30 (la tercera capa) | Lo desarrolla: anonimizador, `hide_inputs`, retención |
| Coste por cliente | LangGraph nb 30 | Lo conecta con el coste que LangSmith ya calcula por traza |

De las 476 páginas de documentación de LangSmith, unas 92 son de despliegue — y ese bloque
**ya lo cubre el curso de LangGraph**, porque «LangSmith Deployment» es el Agent Server. El
centro de gravedad de esta rama es el otro: trazas (72 páginas), evaluación (66), prompts
(17) y administración (23).

---

## 3 bis. Lo que salió del barrido de documentación y foros

Antes de cerrar el temario hice el mismo ejercicio que dio los mejores notebooks del curso
de LangGraph: leer la documentación entera buscando lo que no se cuenta en los tutoriales, y
contrastarlo con lo que la gente reporta. Fuentes: las 476 páginas de la documentación
oficial (clonadas en local), GitHub Issues de `langchain-ai/langsmith-sdk`, el foro de
LangChain, y comparativas de terceros para la parte económica.

Lo que sigue **ya está comprobado en este entorno, sin clave ni red**, salvo donde se indica.
Esto es lo que va a alimentar la tabla «Detalles que sorprenden» del README del curso.

### Hallazgo 1 · El SDK lee 37 variables de entorno, y la documentación cubre seis

> **Corregido al escribir el notebook 02.** Este documento decía «51». Al convertir el
> recuento en código ejecutable, la cifra no se sostuvo. La buena, medida sobre
> langsmith 0.11.2, es **37 nombres lógicos y 74 grafías** — cada nombre se resuelve
> bajo `LANGSMITH_` y bajo `LANGCHAIN_`. Hay que sumar dos cosas para contarlas: las
> escritas literalmente (`os.environ.get("LANGSMITH_...")`) y las que el SDK construye
> en `get_env_var("NOMBRE")`. El notebook 02 trae el recuento como celda ejecutable,
> así que envejece a la vista en vez de en silencio.

La mayoría no aparecen en ninguna guía, y varias resuelven problemas reales:

| Variable | Para qué | Por qué importa |
|---|---|---|
| `LANGSMITH_TRACING_SAMPLING_RATE` | Muestrear trazas | **La herramienta del presupuesto** (sección 2) |
| `LANGSMITH_TEST_CACHE` | Cachear las respuestas del modelo en las pruebas | Pruebas con LLM **deterministas y gratis** en CI |
| `LANGSMITH_TEST_TRACKING` | Correr las pruebas sin subir nada | Modo local del *plugin* de pytest |
| `LANGSMITH_HIDE_INPUTS` / `_OUTPUTS` / `_METADATA` | Mandar la forma, no el contenido | Cuando los datos no puedan salir (nb 05) |
| `LANGSMITH_FAILED_TRACES_DIR` / `_MAX_MB` | Dónde y cuánto guardar de lo que no se pudo enviar | El arreglo de las trazas perdidas (hallazgo 2) |
| `LANGSMITH_RUNS_ENDPOINTS` | Enviar a varios destinos | Migrar de instancia sin perder cobertura |
| `LANGSMITH_EXCLUDE_INPUTS_ON_PATCH` | No reenviar las entradas al cerrar el run | Ahorra ancho de banda |
| `LANGSMITH_DISABLE_RUN_COMPRESSION` | Desactivar la compresión | Depurar problemas de ingesta |

**Dos entradas de la tabla original se han caído porque no existen en el SDK instalado**,
y conviene que quede escrito para no volver a proponerlas:

- `LANGSMITH_TRACING_BACKGROUND` — no existe. Lo que controla el envío síncrono es
  `auto_batch_tracing=False` en el constructor de `Client`.
- `LANGSMITH_REPLICAS` — no es una variable de entorno, sino una clave de la cabecera
  `baggage` del trazado distribuido. Las réplicas se configuran con el parámetro
  `replicas=` de `tracing_context`.

Y aparecieron dos trampas que valen más que la tabla entera, las dos silenciosas:
`LANGSMITH_` gana siempre sobre `LANGCHAIN_`, y `get_env_var` está decorada con
`lru_cache`, así que cambiar una variable en caliente no tiene ningún efecto. Las dos
están en el notebook 02, reproducidas.

### Hallazgo 2 · Las trazas se pierden si el proceso muere antes de vaciar el buffer

Es **el problema número uno** en los foros: *"no me aparecen las trazas"*. La causa casi
siempre es la misma y no es un fallo: por defecto el envío es **en segundo plano** para no
añadir latencia. En un entorno efímero —una función serverless, un script corto, un job de
CI— el proceso termina antes de que el hilo de envío haya salido.

Tres arreglos, con sus contrapartidas, y los tres verificados como API existente:

| Arreglo | Coste |
|---|---|
| `wait_for_all_tracers()` antes de salir | Bloquea al final; es lo correcto en un script |
| `client.flush()` explícito | Control fino, hay que acordarse |
| `Client(auto_batch_tracing=False)` | Envío síncrono: añade latencia a **cada** llamada |
| `Client(tracing_error_callback=...)` | No evita la pérdida, pero **te enteras** — que es lo que hoy no pasa |
| `LANGSMITH_FAILED_TRACES_DIR` | Deja en disco lo que no pudo enviar, para reintentarlo |

Y una comprobación que ya está hecha, no leída: **con la red cortada y el trazado activo,
una función decorada devuelve su resultado con normalidad.** El SDK se traga el fallo de
envío y escribe una línea de log. La traza se pierde y el programa no se entera. Ese es
el punto de partida del notebook.

Conecta directamente con el notebook 28 del curso de LangGraph: un pod que recibe `SIGTERM`
tiene exactamente este problema con sus trazas, y el drenaje que ya diseñamos allí tiene que
incluir el vaciado del buffer. **Ese cruce no lo he visto documentado en ningún sitio.**

### Hallazgo 3 · El muestreo es por traza completa, no por run

Leyendo `_filter_for_sampling` en el cliente: cuando una traza no entra en la muestra, se
registra su `trace_id` y **se descartan también todos sus runs hijos y los parches
posteriores**. No existe el caso de «media traza».

Es la diferencia entre un muestreo que sirve y uno que produce árboles rotos, y es lo que
hace que `LANGSMITH_TRACING_SAMPLING_RATE=0.1` sea utilizable en producción de verdad.
Comprobado además que el valor se valida en el constructor: fuera de `[0, 1]` lanza
`LangSmithUserError`.

### Hallazgo 4 · `hide_inputs` acepta una función, no solo un booleano

La firma real es `Optional[Union[Callable[[dict], dict], bool]]`. Casi todos los ejemplos lo
usan como interruptor, y ahí se pierde lo interesante: puedes **transformar** en vez de
ocultar — redactar el correo y dejar el resto, quedarte con la longitud del documento en vez
del documento.

Junto al anonimizador (`create_anonymizer`, que ya comprobé que recorre estructuras anidadas)
son las dos piezas de la sección «lo que no debe salir», y cierran el hueco que el notebook
30 del curso de LangGraph deja abierto a propósito.

### Hallazgo 5 · Hay una forma de tener pruebas con LLM deterministas y gratis

`LANGSMITH_TEST_CACHE` + el extra `langsmith[vcr]` graban las respuestas del modelo en
ficheros que se versionan. A partir de ahí las pruebas **no llaman al modelo**: son
deterministas, gratis y rápidas, y solo cambian cuando cambias el *prompt* o el modelo.

Esto merece decirse claro porque resuelve un problema que el curso de LangGraph deja
planteado: allí la CI usa un modelo falso, que comprueba estructura pero no calidad. Con el
caché de LangSmith se puede tener **calidad en la CI** sin gastar cuota. Es de las cosas que
más cambian la forma de trabajar y está escondida en una página.

Además, `langsmith.expect` da aserciones aproximadas —`edit_distance`,
`embedding_distance`, `score`, `value`— pensadas justo para salidas no deterministas.

### Hallazgo 6 · Los límites que te van a morder

De la documentación, con números concretos:

| Límite | Valor | Síntoma |
|---|---|---|
| Cuota Developer sin método de pago | **5.000 trazas/mes**, retención 1 mes | Deja de ingerir |
| Tamaño de petición | **300 MB** | `413 Request entity too large` |
| Visualización en la interfaz | **20 MB** por traza | Se ve truncada aunque esté completa |
| Buffer de trazas fallidas | 100 MB de RAM por defecto | Consumo de memoria inesperado |

La fila de los 20 MB explica una queja recurrente de los foros: *"la traza está incompleta"*.
No lo está — es la interfaz la que no la pinta entera. Es un ejemplo perfecto de por qué el
curso mide en vez de suponer.

### Hallazgo 7 · «Align Evaluator» existe, y valida el módulo 3

Propuse el notebook `10_alinear_el_juez` por convicción: un juez LLM sin alinear con humanos
es una métrica inventada. Resulta que **LangSmith tiene una funcionalidad dedicada a
exactamente eso**, con un flujo documentado de cuatro pasos: seleccionar ejecuciones →
etiquetar en una cola de anotación → probar el *prompt* del juez contra lo etiquetado →
refinar y repetir.

Que el producto tenga una pieza específica confirma que el problema es real y generalizado.
El notebook pasa de ser una propuesta mía a cubrir una funcionalidad de primera clase.

### Hallazgo 8 · La economía, que el curso tiene que contar

De las comparativas de terceros, y va al notebook 00 en un apartado «cuándo NO usar
LangSmith», igual que el curso de LangGraph hace con su herramienta:

- El plan Plus cuesta **39 $/puesto/mes antes de la primera traza**: un equipo de cinco
  arranca en 195 $/mes.
- A un millón de trazas mensuales, el orden de magnitud citado es **~2.500 $/mes**, frente a
  ~100 $ autoalojando Langfuse.
- LangSmith es **cerrado**, y el autoalojado es de plan Enterprise. Langfuse tiene núcleo
  MIT; Phoenix y Laminar son nativos de OpenTelemetry.

La conclusión honesta no es «no lo uses»: es que **la integración con LangGraph y las
funciones de evaluación son difíciles de igualar**, y que la salida está en OpenTelemetry —
que ya tratamos en el notebook 17. Un curso que no diga esto no es un curso, es un folleto.

---

## 4. Temario propuesto

**18 notebooks de contenido + 4 de proyecto**, en cinco módulos. Subió de 16 a 18 tras el
barrido: dos notebooks nuevos (`03_trazas_que_se_pierden` y `10_pruebas_con_modelo_en_ci`)
salen directamente de los hallazgos 2 y 5, y los dos son de los más valiosos del temario.
Frente a los 38 del curso de LangGraph, es un complemento proporcionado: unas 26-30 horas.

### Módulo 0 · Punto de partida (1 notebook)

**`00_por_que_langsmith`** — Qué resuelve y qué no. El mapa contra lo que ya sabes: dónde
encaja cada pieza respecto a los notebooks 17, 27 y 30. Cuenta, clave, proyecto y las cuatro
variables que gobiernan todo. **El presupuesto de trazas** y cómo trabajar el curso sin
agotarlo. El mecanismo de los dos modos.

Y una sección **«cuándo NO usar LangSmith»** (hallazgo 8), igual que el notebook 00 del curso
de LangGraph hace con su herramienta: los 39 $/puesto antes de la primera traza, el orden de
magnitud a un millón de trazas frente a autoalojar, que es cerrado, y cuál es la salida
(OpenTelemetry, notebook 17). Un curso que no dice esto es un folleto.

### Módulo 1 · Trazas: qué se registra y qué no (5 + 1)

| Notebook | Contenido | Verificación |
|---|---|---|
| `01_anatomia_de_una_traza` | `@traceable`, `RunTree`, `dotted_order`, tipos de run, cómo se construye la jerarquía por dentro | **Ejecutable offline** |
| `02_instrumentar_de_verdad` | Automático en LangChain/LangGraph, `wrap_openai` para el SDK a pelo, metadata, tags, `run_name`, proyecto dinámico. Y qué **no** se instrumenta solo. **Las 51 variables de entorno** (hallazgo 1): las nueve que resuelven problemas reales, con las demás en una tabla de referencia | Mixta |
| `03_trazas_que_se_pierden` 🆕 | **El problema nº 1 de los foros** (hallazgo 2): envío en segundo plano y procesos efímeros. `wait_for_all_tracers()`, `client.flush()`, `LANGSMITH_TRACING_BACKGROUND`, con sus contrapartidas. Muestreo **por traza completa** (hallazgo 3) y los límites de 300 MB / 20 MB / 5.000 trazas (hallazgo 6). Enlaza con el drenaje del notebook 28: un `SIGTERM` también se lleva tus trazas | **Ejecutable offline** |
| `04_hilos_y_realimentacion` | El `thread_id` de LangSmith frente al de LangGraph: no son lo mismo y se relacionan a mano. Feedback del usuario final con tokens prefirmados | Mixta |
| `05_lo_que_no_debe_salir` | El anonimizador con reglas propias y `hide_inputs` **como función, no como interruptor** (hallazgo 4): transformar en vez de ocultar. La decisión explícita de mandar o no el contenido. **Cierra el hueco que deja el notebook 30** | **Ejecutable offline** |
| **`P1 · Instrumentar el agente de soporte`** | Coger el agente del curso de LangGraph y responder con trazas preguntas que sin ellas son adivinar | Mixta |

### Módulo 2 · Datasets y experimentos (5 + 1)

| Notebook | Contenido |
|---|---|
| `06_datasets` | Crear, versionar, *splits*, los tres tipos (kv, chat, llm). Y el bucle que importa: `create_example_from_run` — de una traza de producción a un caso de prueba |
| `07_experimentos` | `evaluate()` a fondo: *target*, `summary_evaluators`, `experiment_prefix`, repeticiones, concurrencia. Comparar dos experimentos |
| `08_evaluadores` | Código frente a juez LLM. `openevals`, rúbricas, `EvaluationResult`, claves de feedback. Los evaluadores del notebook 27 dentro de LangSmith |
| `09_regresion_de_verdad` | Varianza, cuántas repeticiones hacen falta, umbral con tolerancia **medida** (retoma el nb 17), y `evaluate_comparative` para comparaciones por pares. **Fijar la versión del dataset**: sin eso los experimentos no se comparan entre sí |
| `10_pruebas_con_modelo_en_ci` 🆕 | **El hallazgo 5, que cambia la forma de trabajar.** El *plugin* de pytest, `LANGSMITH_TEST_CACHE` con el extra `vcr` y `langsmith.expect` (`edit_distance`, `embedding_distance`, `score`). Pruebas con LLM **deterministas, gratis y versionadas** — resuelve lo que el curso de LangGraph deja abierto, donde la CI usa un modelo falso que comprueba estructura pero no calidad | Mixta |
| **`P2 · Conjunto dorado de tickets`** | Sobre los 400 tickets etiquetados que ya tiene el curso: línea base, experimento y detección de regresión |

### Módulo 3 · El humano en el bucle de la calidad (2 + 1)

| Notebook | Contenido |
|---|---|
| `11_anotacion` | Colas de anotación, `add_runs_to_annotation_queue`, esquemas de feedback, cómo se escribe una rúbrica que dos personas interpreten igual |
| `12_alinear_el_juez` | Medir el acuerdo entre tu juez LLM y tus anotadores humanos, y corregir el juez hasta que valga. Un juez sin alinear es una métrica inventada. Cubre **Align Evaluator** (hallazgo 7), que resulta ser una funcionalidad de primera clase: seleccionar ejecuciones → etiquetar → probar el *prompt* contra lo etiquetado → refinar |
| **`P3 · Un juez que sirve`** | Anotar 30 casos, medir el acuerdo, iterar el prompt del juez, volver a medir |

### Módulo 4 · Producción: mirar y actuar (3 + 1)

| Notebook | Contenido |
|---|---|
| `13_monitorizar` | Paneles, monitores, alertas. Qué métricas para un agente — retoma la discusión del nb 30: tareas completadas, no latencia |
| `14_reglas_y_evaluacion_en_linea` | Automatizaciones: mandar trazas a un dataset o a una cola sin intervención. Evaluar **en producción**, muestreado, y qué cuesta |
| `15_prompts_versionados` | Hub, *commits*, Playground, y el puente con los *assistants* del notebook 18: dónde vive de verdad la versión de un prompt |
| **`P4 · Capstone: el bucle completo`** | Producción → traza → regla → dataset → experimento → mejora → despliegue. Es el ciclo entero, con los tickets del curso |

### Módulo 5 · Gobierno (2)

| Notebook | Contenido |
|---|---|
| `16_organizacion_y_accesos` | Organizaciones, espacios de trabajo, roles, claves y su rotación, registro de auditoría |
| `17_retencion_y_cumplimiento` | Retención por plan, qué se guarda, borrado, y el RGPD sobre trazas. **Cierra del todo el notebook 30**: la capa que su código no borra |

---

## 5. Qué se reutiliza tal cual

La rama nace con la infraestructura del curso de LangGraph ya hecha, y eso ahorra la mitad
del trabajo:

| Pieza | Uso |
|---|---|
| `_src/*.nbsrc` + `_tools/nbgen.py` | Mismo formato de fuentes en texto plano |
| `_tools/validar.py` | Adaptado para comprobar los símbolos del SDK de `langsmith` |
| `_tools/ejecutar_notebooks.py` + `modelo_falso.py` | Ejecución en CI sin clave ni cuota |
| `_tools/exportar_requisitos.py`, `pyproject.toml`, `uv.lock` | Mismo gestor de paquetes y mismo lock |
| `data/tickets_soporte.csv` (400 etiquetados) | El dominio no cambia: continuidad entre cursos |
| `utils/curso.py` | Extendido con `init_langsmith()` y `presupuesto_de_trazas()` |
| `.github/workflows/verificar.yml` | Una etapa más, con la nueva carpeta |
| Convenciones | Español para la teoría, inglés para el código; dos ejercicios por notebook con solución plegada |

Estructura propuesta, hermana de la existente:

```
langsmith/
├── README.md
├── _src/**/*.nbsrc
├── _tools/            (enlaces o copias adaptadas de los del curso de LangGraph)
├── utils/
├── pruebas/
├── 00_inicio/ 01_trazas/ 02_evaluacion/ 03_humano/ 04_produccion/ 05_gobierno/
└── ejemplos/
```

> **Decidido al montar la infraestructura, y al revés de lo que decía este plan.**
> `langsmith/` es **autocontenido**: su propio `pyproject.toml` y su propio `uv.lock`.
> Compartirlo obligaría a convertir el repositorio en un *workspace* de uv y a mover el
> lock ya verificado del curso de LangGraph; el ahorro sería un `uv sync` y el coste,
> tocar infraestructura verificada y volver a validar 38 notebooks y 83 pruebas. Lo
> único que se comparte son los datos: `ruta_datos()` los busca aquí y luego en
> `../langgraph/data/`.

---

## 6. Cómo se verifica

Los mismos filtros del curso de LangGraph, más uno nuevo y una renuncia explícita:

1. **Validación estática** — estructura, compilación de cada celda y que cada símbolo
   importado exista en el SDK instalado.
2. **Ejecución completa sin clave** — los 20 notebooks corren de principio a fin con
   `LANGSMITH_TRACING=false` y el modelo falso. Las celdas que necesitan servicio detectan su
   ausencia y lo dicen.
3. **Verificación de comportamiento** — todo lo de la columna izquierda de la sección 1 se
   comprueba ejecutándolo, y los resultados van al material.
4. **Entornos vírgenes** — `uv sync` y `pip install -r requirements.txt`, como ahora.
5. 🆕 **Marcado de cobertura** — cada celda que requiere el servicio va etiquetada, y el
   README publica el recuento: cuántas celdas verificadas por ejecución y cuántas solo
   estáticamente.
6. ⚠️ **Lo que no puedo hacer** — ejecutar contra LangSmith de verdad. Esa comprobación la
   harás tú la primera vez que pases el curso con tu clave. Si algo no cuadra, se corrige;
   pero no lo voy a presentar como verificado.

---

## 7. Riesgos, con su mitigación

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Una API del SDK cambia entre que escribo y ejecutas | Media | El validador comprueba que los símbolos existen; el lock fija la versión |
| Las celdas online tienen un error que no puedo ver | **Media-alta** | Se escriben desde la documentación oficial y la firma real de cada función; van marcadas; la primera pasada tuya las depura |
| Agotar tu cuota de trazas | Baja | Presupuesto declarado por notebook, conjuntos pequeños, proyecto aparte |
| La interfaz web cambia y las capturas envejecen | Media | **Sin capturas de pantalla**: se describe qué buscar, no dónde está el botón |
| Solaparse con el curso de LangGraph | Media | La tabla de la sección 3 es el contrato; cada notebook empieza diciendo qué no repite |

El segundo es el riesgo real y no lo puedo eliminar desde aquí. Por eso el material online se
escribe conservador: menos florituras, más código que se lee de la firma de la función.

---

## 8. Fases de entrega

Pensadas para que puedas parar en cualquier punto con algo completo en la mano:

| Fase | Qué entrega | Notebooks | Por qué este orden |
|---|---|---|---|
| **1** | Infraestructura + módulos 0 y 1 | 7 | Trazas es lo primero que se usa y lo más verificable offline. Incluye los hallazgos 1-4 y 6 |
| **2** | Módulo 2 | 6 | Evaluación: donde está el grueso del valor. Incluye el hallazgo 5 |
| **3** | Módulo 3 | 3 | Alinear el juez, que depende de tener experimentos |
| **4** | Módulo 4 | 4 | Producción y el capstone |
| **5** | Módulo 5 + README + CI | 2 | Gobierno y cierre |

Después de la fase 1 tendría sentido que dieras una pasada con tu clave: confirma el
mecanismo de los dos modos y detecta pronto cualquier desajuste de la parte online, antes de
que lo repita en 14 notebooks más.

---

## 9. Lo que necesito de ti

1. **Nada para seguir.** El curso se está construyendo en `langsmith/`, sobre la rama
   autorizada. No hace falta una rama nueva.
2. **La clave de LangSmith no me la des.** No la necesito —escribo para los dos modos y
   verifico el local entero— y no quiero que una clave tuya acabe en un entorno efímero.
   La pondrás tú en tu `.env`, que está en `.gitignore`.
3. **Cuando quieras, una pasada con tu clave.** Después de la fase 1 tiene sentido que
   ejecutes los notebooks en modo en línea: es lo único que puede depurar las celdas
   `@online`, que están escritas contra la firma real de cada función pero no ejecutadas.
   Cada fallo que encuentres es un error del material, y `@online` te lo señala sin
   romper el notebook.
