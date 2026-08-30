# Curso de LangGraph — de cero al p99

Un curso completo de **LangGraph en español**, en 37 notebooks interactivos, construido y
verificado contra **LangGraph 1.2** y **LangChain 1.3**.

No es una traducción de la documentación. Cada afirmación técnica del material se comprobó
ejecutándola, y varias de las que "todo el mundo sabe" resultaron ser falsas en esta versión
(están documentadas más abajo, en *Detalles que sorprenden*).

El **módulo 7** nació de un barrido de foros —GitHub Issues y Discussions de
`langchain-ai/langgraph`, el foro de LangChain, Stack Overflow y post-mortems publicados— y
cubre lo que rompe *después* de desplegar: serialización del estado, crecimiento de la
persistencia, concurrencia por `thread_id` y control de acceso.

| | |
|---|---|
| **Notebooks** | 37 (30 de contenido + 7 de proyecto) |
| **Módulos** | 8 |
| **Celdas** | 1324 (752 de teoría, 572 de código ejecutable) |
| **Ejercicios** | 2 por notebook de contenido, con solución comentada |
| **Datos** | 4 conjuntos reales + 1 sintético etiquetado + 18 documentos para RAG |
| **Pruebas** | 77 pruebas automáticas que corren en 7 s sin llamar a ningún modelo |
| **Dedicación estimada** | 54-61 horas |
| **Coste en API** | unos 2 € en total con `gpt-4o-mini` |

---

## Empezar

El curso usa [**uv**](https://docs.astral.sh/uv/). Si no lo tienes:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh     # macOS y Linux
# Windows (PowerShell): irm https://astral.sh/uv/install.ps1 | iex
```

```bash
cd langgraph
uv sync                     # crea .venv e instala exactamente lo que dice uv.lock
cp .env.example .env        # y escribe tu OPENAI_API_KEY
uv run jupyter lab
```

Grupos opcionales, para lo que no hace falta hasta el módulo 6:

```bash
uv sync --group despliegue   # langgraph-cli: servidor local y Studio (notebooks 18, 25, 26)
uv sync --group postgres     # PostgresSaver y psycopg (notebook 23)
uv sync --all-groups         # todo
```

<details>
<summary>Si prefieres pip</summary>

`requirements.txt` se **genera** desde `uv.lock`, así que instala exactamente las mismas
versiones:

```bash
cd langgraph
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
jupyter lab
```

No lo edites a mano: las dependencias se tocan en `pyproject.toml` y luego
`uv lock && uv run _tools/exportar_requisitos.py`.

</details>

Abre `00_inicio/00_bienvenida_y_entorno.ipynb` y sigue el orden.

**`OPENAI_API_KEY` es obligatoria**: los notebooks llaman a modelos de verdad. `LANGSMITH_API_KEY`
es opcional pero muy recomendable — depurar un grafo sin trazas es adivinar.

---

## La ruta

### Módulo 0 · Inicio

| Notebook | Qué aprendes |
|---|---|
| [`00_bienvenida_y_entorno`](00_inicio/00_bienvenida_y_entorno.ipynb) | Qué problema resuelve LangGraph, cuándo **no** usarlo, el modelo mental de Pregel, y tu primer grafo |

### Módulo 1 · Fundamentos

| Notebook | Qué aprendes |
|---|---|
| [`01_grafos_estado_y_nodos`](01_fundamentos/01_grafos_estado_y_nodos.ipynb) | `TypedDict` vs `dataclass` vs Pydantic, contrato de los nodos, estado frente a contexto, y los cinco fallos clásicos |
| [`02_reducers_y_esquemas`](01_fundamentos/02_reducers_y_esquemas.ipynb) | Reducers como **política de concurrencia**, `add_messages`, `Overwrite`, esquemas de entrada/salida y `EphemeralValue` |
| [`03_control_de_flujo`](01_fundamentos/03_control_de_flujo.ipynb) | Aristas condicionales, `Command`, paralelismo real, `defer`, `Send` para map-reduce y límites de recursión |
| [`04_mensajes_y_modelos`](01_fundamentos/04_mensajes_y_modelos.ipynb) | Gestión del historial y su coste cuadrático, recorte, resumen, salida estructurada y streaming de tokens |
| **[`P1 · Triaje de tickets`](01_fundamentos/P1_proyecto_triaje_tickets.ipynb)** | Sistema de triaje medido contra 400 tickets etiquetados, con línea base sin IA |

### Módulo 2 · Agentes y herramientas

| Notebook | Qué aprendes |
|---|---|
| [`05_tools_y_toolnode`](02_agentes/05_tools_y_toolnode.ipynb) | Los seis principios de diseño de herramientas, `ToolNode`, manejo de errores y `ToolRuntime` |
| [`06_agente_react_desde_cero`](02_agentes/06_agente_react_desde_cero.ipynb) | El bucle ReAct escrito a mano, lo que le falta para producción y los tres anti-patrones |
| [`07_create_agent_y_middleware`](02_agentes/07_create_agent_y_middleware.ipynb) | Los seis puntos de enganche del middleware, el de fábrica, el propio y el orden de composición |
| **[`P2 · Agente analista`](02_agentes/P2_proyecto_agente_analista.ipynb)** | Analista de datos evaluado contra respuestas calculadas con pandas |

### Módulo 3 · Estado duradero

| Notebook | Qué aprendes |
|---|---|
| [`08_persistencia_y_checkpointers`](03_estado/08_persistencia_y_checkpointers.ipynb) | Hilos, `get_state_history`, `update_state`, viaje en el tiempo y durabilidad |
| [`09_memoria_largo_plazo`](03_estado/09_memoria_largo_plazo.ipynb) | El `Store`, espacios de nombres, los tres tipos de memoria y búsqueda semántica |
| [`10_human_in_the_loop`](03_estado/10_human_in_the_loop.ipynb) | `interrupt()`, los cuatro patrones de aprobación y cómo se ve desde un servidor web |
| **[`P3 · Asistente persistente`](03_estado/P3_proyecto_asistente_persistente.ipynb)** | Asistente con memoria entre sesiones y bandeja de aprobaciones |

### Módulo 4 · Composición

| Notebook | Qué aprendes |
|---|---|
| [`11_streaming`](04_composicion/11_streaming.ipynb) | Los siete modos, `get_stream_writer`, filtrado de tokens por nodo y subgrafos |
| [`12_subgrafos`](04_composicion/12_subgrafos.ipynb) | Las dos formas de anidar, persistencia a través de subgrafos y `Command.PARENT` |
| [`13_multiagente`](04_composicion/13_multiagente.ipynb) | Cuándo compensa, los cuatro patrones, handoffs y qué contexto compartir |
| **[`P4 · Equipo multiagente`](04_composicion/P4_proyecto_equipo_multiagente.ipynb)** | Un agente único contra un equipo, comparados con una rúbrica explícita |

### Módulo 5 · RAG agéntico

| Notebook | Qué aprendes |
|---|---|
| [`14_rag_agentico`](05_rag/14_rag_agentico.ipynb) | Troceado con criterio, recuperación híbrida con RRF, ciclo CRAG y citas verificables |
| **[`P5 · RAG evaluado`](05_rag/P5_proyecto_rag_evaluado.ipynb)** | Evaluación por capas: recuperación, fidelidad, corrección y abstención |

### Módulo 6 · Producción

| Notebook | Qué aprendes |
|---|---|
| [`15_fiabilidad_y_rendimiento`](06_produccion/15_fiabilidad_y_rendimiento.ipynb) | `RetryPolicy` selectivo, `error_handler`, `CachePolicy`, timeouts y presupuestos |
| [`16_functional_api`](06_produccion/16_functional_api.ipynb) | `@entrypoint` y `@task`, y el criterio para elegir entre las dos APIs |
| [`17_evaluacion_y_observabilidad`](06_produccion/17_evaluacion_y_observabilidad.ipynb) | La pirámide de pruebas, modelos guionizados, umbrales de regresión y LangSmith |
| [`18_despliegue`](06_produccion/18_despliegue.ipynb) | `langgraph.json`, servidor local, assistants y las tres opciones de despliegue |
| [`19_patrones_p99`](06_produccion/19_patrones_p99.ipynb) | Ingeniería de contexto, escalado de herramientas, seguridad e inyección indirecta |
| [`20_mcp_e_integracion`](06_produccion/20_mcp_e_integracion.ipynb) | MCP: servidores propios, seguridad frente a servidores de terceros, límites de ritmo y `as_tool` |
| [`21_agentes_horizonte_largo`](06_produccion/21_agentes_horizonte_largo.ipynb) | Los cinco pilares de los agentes que trabajan durante horas: plan, memoria externa, divulgación progresiva, subagentes y compactación |
| **[`P6 · Capstone`](06_produccion/P6_capstone.ipynb)** | El sistema completo: triaje, RAG, aprobación, memoria, seguridad y evaluación |

### Módulo 7 · Operación real

Lo que rompe cuando el sistema ya funciona y lleva tres semanas en producción. Este módulo
sale de contrastar el resto del curso con los problemas que la gente reporta en los foros.

| Notebook | Qué aprendes |
|---|---|
| [`22_serializacion_del_estado`](07_operacion/22_serializacion_del_estado.ipynb) | Qué tipos sobreviven al checkpoint, la tupla que vuelve como lista, CVE-2026-28277 y el modo estricto de msgpack |
| [`23_persistencia_a_escala`](07_operacion/23_persistencia_a_escala.ipynb) | La fórmula de checkpoints por turno, el efecto real de `durability`, poda del checkpointer y los parámetros de Postgres que nadie documenta |
| [`24_concurrencia_y_servidor`](07_operacion/24_concurrencia_y_servidor.ipynb) | La pérdida de escrituras con dos peticiones al mismo hilo, cerrojos por `thread_id`, *double texting* y un servidor SSE propio |
| [`25_auth_y_multitenencia`](07_operacion/25_auth_y_multitenencia.ipynb) | `langgraph_sdk.Auth`, filtros de metadatos, aislamiento del `Store` y el `langgraph.json` completo |
| [`26_exponer_el_agente`](07_operacion/26_exponer_el_agente.ipynb) | El agente como servicio para otros agentes: endpoint `/mcp`, protocolo A2A, rutas HTTP propias y el diseño del contrato que ve el otro modelo |
| [`27_evaluar_trayectorias`](07_operacion/27_evaluar_trayectorias.ipynb) | Evaluar **cómo** llegó el agente a la respuesta: los cuatro modos de coincidencia de `agentevals`, la trampa de los argumentos en lenguaje natural, trayectorias de grafo con interrupciones y los límites del juez LLM |
| [`28_ciclo_de_vida_del_despliegue`](07_operacion/28_ciclo_de_vida_del_despliegue.ipynb) | La **segunda** vez que despliegas: migración del esquema sobre hilos vivos, los hilos que un renombrado abandona en silencio, la comprobación previa, el apagado ordenado medido, el contenedor real y la CI |
| [`29_limites_colas_e_incidentes`](07_operacion/29_limites_colas_e_incidentes.ipynb) | Los cuatro límites del proveedor y cuál te muerde, `InMemoryRateLimiter` medido, el rebaño atronador, *backpressure* con semáforo, interruptores para degradar sin desplegar y un *runbook* que se ejecuta |
| **[`P7 · Auditoría de producción`](07_operacion/P7_proyecto_endurecer.ipynb)** | Un auditor que aplica los cuatro detectores a una aplicación heredada y a su versión endurecida |

---

## Cómo está construido

### Los datos

| Fichero | Qué es | Origen |
|---|---|---|
| `data/tickets_soporte.csv` | 400 tickets en español con categoría y prioridad **etiquetadas** | Sintético y determinista ([generador](_tools/generar_tickets.py)) |
| `data/ventas_supermercado.csv` | 1.000 ventas de tres supermercados | Real ([plotly/datasets](https://github.com/plotly/datasets)) |
| `data/titanic.csv` | 891 pasajeros con supervivencia | Real ([datasciencedojo](https://github.com/datasciencedojo/datasets)) |
| `data/clima_seattle.csv` | 1.461 días de clima | Real ([vega-datasets](https://github.com/vega/vega-datasets)) |
| `data/propinas.csv` | 244 cuentas de restaurante | Real ([seaborn-data](https://github.com/mwaskom/seaborn-data)) |
| `data/kb/` | 18 páginas de la documentación oficial de LangGraph | Real ([langchain-ai/docs](https://github.com/langchain-ai/docs), MIT) |

Los tickets son sintéticos **a propósito**: los corpus públicos de tickets reales o están en
inglés, o no tienen etiquetas, o no se pueden redistribuir. Sin verdad de terreno no se puede
*medir* un agente de triaje, solo mirarlo. El notebook P1 explica en detalle por qué eso hace
que la línea base sea engañosamente fuerte, que es una lección en sí misma.

```bash
python utils/datos.py                # ver qué hay
python utils/datos.py --descargar    # volver a traer los originales públicos
python _tools/generar_tickets.py     # regenerar los sintéticos (determinista)
```

### Las herramientas del repositorio

```
pyproject.toml             la fuente de verdad de las dependencias (uv)
uv.lock                    el árbol completo resuelto: lo que instala `uv sync`
requirements.txt           GENERADO desde el lock, para la vía de pip
_tools/nbgen.py            genera los .ipynb desde fuentes de texto plano en _src/
_tools/exportar_requisitos.py  regenera requirements.txt desde uv.lock (--check en la CI)
_tools/ejecutar_notebooks.py   ejecuta todos los notebooks con un modelo falso
_tools/modelo_falso.py     BaseChatModel de mentira: bind_tools, structured output, tokens
.github/workflows/         la integración continua del propio curso
_tools/validar.py          valida estructura, compila cada celda y comprueba que todo
                           símbolo importado EXISTE en el entorno instalado
_tools/preparar_kb.py      construye el corpus RAG desde la documentación oficial
_tools/generar_tickets.py  genera los tickets etiquetados
ejemplos/                  servidores MCP de demostración (notebook 20)
utils/curso.py             arranque, fábrica de modelos, visualización, impresión legible
utils/datos.py             carga de los conjuntos de datos
utils/rag.py               troceado, BM25 y fusión de rangos (del notebook 14)
pruebas/                   77 pruebas automáticas, sin llamadas a modelos
despliegue/                aplicación desplegable que genera el notebook 18, con su
                           versión endurecida (auth.py + langgraph.produccion.json)
```

Los notebooks se escriben en `_src/**/*.nbsrc`, un formato de texto plano con celdas separadas
por `#%%md` y `#%%py`, y se compilan a `.ipynb`. Así las revisiones en git son legibles y no
hay que editar JSON a mano.

```bash
uv run _tools/nbgen.py _src/01_fundamentos/*.nbsrc   # regenerar notebooks
uv run _tools/validar.py                             # validar todos
uv run pytest                                        # la batería de pruebas
uv run _tools/exportar_requisitos.py --check         # ¿sigue el requirements.txt al día?
uv run _tools/ejecutar_notebooks.py                  # ejecutarlos todos, sin gastar cuota
```

### Cómo se verificó el material

Cada notebook pasó por siete filtros antes de darse por bueno:

1. **Validación estática** — estructura del `.ipynb`, compilación de cada celda de código, y
   comprobación de que **cada símbolo importado existe** en LangGraph 1.2 / LangChain 1.3. Esto
   es lo que detecta APIs inventadas o renombradas entre versiones.
2. **Ejecución completa** — todos los notebooks se ejecutan de principio a fin con un modelo
   falso que sí es un `BaseChatModel` (soporta `bind_tools`, `with_structured_output` y
   `usage_metadata`), para comprobar que la estructura de los grafos funciona sin gastar cuota.
3. **Verificación de comportamiento** — cada afirmación no trivial sobre cómo se comporta
   LangGraph se comprobó ejecutando el caso.
4. **La aplicación desplegable se levantó de verdad** con `langgraph dev`, y se comprobó por
   HTTP que carga el grafo, expone el assistant y responde en `/threads` y `/runs`. Fue ahí
   donde apareció el fallo de las importaciones relativas: ninguna comprobación estática lo
   detecta, y el material lo documenta precisamente por eso.
5. **Todo lo anterior se repitió en dos entornos vírgenes**, uno creado con `uv sync` desde
   el lock y otro con `pip install -r requirements.txt`, para garantizar que las dos vías de
   instalación dan lo mismo: 37/37 notebooks y 77/77 pruebas en ambos, con versiones idénticas.
6. **La capa de autenticación se ejercitó por HTTP.** `despliegue/langgraph.produccion.json`
   se arrancó con `langgraph dev` y se comprobaron los 401 sin token, los 403 por falta de
   permiso, los 200 con el `owner` escrito en los metadatos, el aislamiento entre usuarios y
   el 404 (que no 403) al pedir un recurso ajeno.
7. **Los endpoints de interoperabilidad se ejercitaron con clientes reales.** Se listaron y
   se llamaron las herramientas del endpoint `/mcp` con el SDK de MCP, se leyó el agent card
   y se creó una tarea por A2A, y se comprobó que las rutas propias de `http.app` devuelven
   401 sin token cuando `enable_custom_route_auth` está activo.

---

## Detalles que sorprenden

Cosas que el material afirma **porque se comprobaron ejecutándolas**, y que contradicen lo que
suele darse por supuesto:

| Afirmación | Dónde |
|---|---|
| Un grafo con cualquier nodo `async def` **no admite `invoke()` síncrono**: lanza `TypeError` | 01 |
| `compile()` **no** detecta nodos huérfanos ni ramas condicionales a nodos inexistentes | 01 |
| Las claves que no existen en el esquema **se descartan sin ningún aviso** | 01 |
| El `recursion_limit` por defecto es **10007**, no 25: ya no te protege de un bucle infinito | 03 |
| Por defecto, una excepción **dentro** de tu herramienta **aborta el grafo**; solo se capturan los errores de invocación | 05 |
| Un `ToolNode` no se puede invocar suelto: necesita el runtime que solo existe dentro de un grafo | 05 |
| En el middleware, **el primero de la lista es el más externo** | 07 |
| Tras un `interrupt()`, el nodo **se reejecuta desde el principio**: los efectos previos ocurren dos veces | 10 |
| Las etiquetas de un namespace del `Store` **no admiten puntos**, lo que descarta usar correos como identificador | 09 |
| Un subgrafo embebido que comparte una clave con reducer acumulador **duplica** lo heredado | 12 |
| Anotar `Command[Literal["nodo_del_padre"]]` con `graph=Command.PARENT` **rompe `compile()`** | 12 |
| Los **timeouts por nodo solo funcionan en nodos `async`**; con uno síncrono, `compile()` falla | 15 |
| Las herramientas MCP son **asíncronas** y devuelven **bloques de contenido**, no cadenas | 20 |
| La **descripción** de una herramienta MCP de terceros **es prompt**: puede llevar instrucciones para tu agente | 20 |
| Reutilizar el mismo objeto `AIMessage` en un guion de pruebas hace que `add_messages` lo **sustituya** en vez de añadirlo | 21 |
| El servidor carga tu grafo **por ruta de fichero**: con importaciones relativas no arranca | 18 |
| Una `tuple` en el estado **vuelve como `list`** tras el checkpoint, sin error ni aviso | 22 |
| El modo estricto de msgpack **no lanza excepción**: degrada el objeto a `dict` y sigue | 22 |
| Con el modo estricto, solo sobreviven los tipos **declarados en el esquema**: lo que viaja dentro de `Any` vuelve como `dict` | 22 |
| Un turno escribe **`superpasos + 2` checkpoints**, cada uno con el estado **completo**; `durability="exit"` lo baja a uno | 23 |
| Los `writes` crecen también con **cuántas claves escribe cada nodo**, no solo con los superpasos | 23 |
| LangGraph **no serializa dos ejecuciones del mismo `thread_id`**: se pierden escrituras en silencio | 24 |
| Una desconexión del cliente **no tira el trabajo hecho**: deja el hilo a medias y reanudable con `ainvoke(None, config)` | 24 |
| El servidor de auth ejecuta **un solo manejador** por petición, el más específico: los `@auth.on` **no se encadenan** | 25 |
| El `Store` no se protege con filtros: hay que **reescribir el `namespace`** | 25 |
| Pedir un recurso ajeno devuelve **404, no 403** (un 403 confirmaría que existe) | 25 |
| `langgraph dev` aborta con `BlockingError` ante cualquier E/S bloqueante dentro de un nodo `async` | 18 |
| Con la caché de prefijo contada, **resumir en cada turno sale más caro que no comprimir nada**: rompe la caché, paga una llamada extra y pierde información | 19 |
| Meter la hora en el system prompt encarece la conversación un **86 %** aunque no cambie ni un token del resto | 19 |
| Si una rama de un fan-out falla, las hermanas que terminaron **quedan persistidas**, y al reanudar **solo se reejecuta la que falló** | 15 |
| Un grafo **sin `input_schema` expone el estado entero** por MCP: los campos internos salen como obligatorios y el otro modelo no puede usarlo | 26 |
| En Python < 3.12, un `typing.TypedDict` hace que el esquema **no se pueda publicar**: el servidor pone `input_schema: null` y la herramienta MCP sale sin campos, sin ningún error | 26 |
| Las rutas propias de `http.app` **no pasan por la autenticación** salvo que actives `enable_custom_route_auth` | 26 |
| Comparar argumentos en modo `exact` sobre una consulta en lenguaje natural **garantiza** una evaluación siempre roja | 27 |
| La trayectoria de grafo registra `__interrupt__` como un paso más: es la única forma de comprobar que **hubo aprobación humana** | 27 |
| **Renombrar un nodo abandona en silencio los hilos parados en él**: no hay excepción, la aprobación se pierde y el hilo queda marcado como terminado | 28 |
| Tras ese despliegue, los hilos abandonados **desaparecen de la bandeja de pendientes**: con el grafo nuevo tienen `next` vacío y cero interrupciones | 28 |
| Quitar un campo del esquema lo hace **invisible** en `values`, aunque siga escrito en el checkpoint. Un `revert` lo resucita con el valor viejo | 28 |
| `InMemoryRateLimiter` **arranca con el cubo vacío**: `max_bucket_size` gobierna la ráfaga tras un reposo, no al arrancar | 29 |
| Un panel de concurrencia **bajo** puede ser la señal de que todo está fallando: rechazar es instantáneo, así que las llamadas fallidas no figuran como "en vuelo" | 29 |

---

## Cómo trabajar el curso

- **Ejecuta cada celda en orden.** Los notebooks tienen estado.
- **Cuando aparezca un bloque `EJERCICIO`, párate e inténtalo** antes de mirar la solución. La
  solución siempre viene justo después, plegada, con el razonamiento explicado.
- **Los proyectos son la parte importante.** La teoría se olvida; el proyecto que depuraste a
  las once de la noche, no.
- **Rompe cosas a propósito.** Cambia un reducer, quita un `defer`, sube la temperatura. Casi
  todo lo que aprenderás de verdad sale de ver por qué algo dejó de funcionar.

## Requisitos previos

Python intermedio (tipos, decoradores, `async` a nivel de lectura). No hace falta experiencia
previa con LangChain ni con agentes.

## Licencia y atribución

El material del curso es de uso libre. Los documentos de `data/kb/` son extractos de la
[documentación oficial de LangChain/LangGraph](https://github.com/langchain-ai/docs)
(licencia MIT, © 2025 LangChain), reformateados para uso didáctico. Los conjuntos de datos
reales conservan la licencia de su origen, enlazado en la tabla de arriba.
