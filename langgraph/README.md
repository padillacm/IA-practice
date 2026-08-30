# Curso de LangGraph — de cero al p99

Un curso completo de **LangGraph en español**, en 28 notebooks interactivos, construido y
verificado contra **LangGraph 1.2** y **LangChain 1.3**.

No es una traducción de la documentación. Cada afirmación técnica del material se comprobó
ejecutándola, y varias de las que "todo el mundo sabe" resultaron ser falsas en esta versión
(están documentadas más abajo, en *Detalles que sorprenden*).

| | |
|---|---|
| **Notebooks** | 28 (22 de contenido + 6 de proyecto) |
| **Módulos** | 7 |
| **Celdas** | 1000 (557 de teoría, 443 de código ejecutable) |
| **Ejercicios** | 2 por notebook de contenido, con solución comentada |
| **Datos** | 4 conjuntos reales + 1 sintético etiquetado + 18 documentos para RAG |
| **Pruebas** | 25 pruebas automáticas que corren en 0,3 s sin llamar a ningún modelo |
| **Dedicación estimada** | 39-45 horas |
| **Coste en API** | unos 2 € en total con `gpt-4o-mini` |

---

## Empezar

```bash
cd langgraph
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # y escribe tu OPENAI_API_KEY
jupyter lab
```

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
_tools/nbgen.py            genera los .ipynb desde fuentes de texto plano en _src/
_tools/validar.py          valida estructura, compila cada celda y comprueba que todo
                           símbolo importado EXISTE en el entorno instalado
_tools/preparar_kb.py      construye el corpus RAG desde la documentación oficial
_tools/generar_tickets.py  genera los tickets etiquetados
ejemplos/                  servidores MCP de demostración (notebook 20)
utils/curso.py             arranque, fábrica de modelos, visualización, impresión legible
utils/datos.py             carga de los conjuntos de datos
utils/rag.py               troceado, BM25 y fusión de rangos (del notebook 14)
pruebas/                   25 pruebas automáticas, sin llamadas a modelos
despliegue/                aplicación desplegable que genera el notebook 18
```

Los notebooks se escriben en `_src/**/*.nbsrc`, un formato de texto plano con celdas separadas
por `#%%md` y `#%%py`, y se compilan a `.ipynb`. Así las revisiones en git son legibles y no
hay que editar JSON a mano.

```bash
python _tools/nbgen.py _src/01_fundamentos/*.nbsrc   # regenerar notebooks
python _tools/validar.py                             # validar todos
python -m pytest pruebas/ -q                         # la batería de pruebas
```

### Cómo se verificó el material

Cada notebook pasó por tres filtros antes de darse por bueno:

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
5. **Todo lo anterior se repitió en un entorno virgen** creado solo desde `requirements.txt`,
   para garantizar que el fichero de dependencias basta: 28/28 notebooks y 25/25 pruebas.

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
