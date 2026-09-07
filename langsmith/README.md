# Curso de LangSmith

Complemento del [curso de LangGraph](../langgraph/) que vive en este mismo repositorio.
Aquel enseña a **construir** aplicaciones con LLM; este enseña a **saber si funcionan**:
trazas, evaluación, anotación humana y operación.

Da por supuesto el otro curso. No repite lo que allí ya está — la tabla de
[qué no está aquí](PLAN.md#3-qué-no-va-a-estar-y-dónde-está-ya) es el contrato.

---

## Los dos modos, y por qué

LangSmith es un servicio en la nube. Este curso se escribió en un entorno que **no lo
alcanza**, y eso condiciona el diseño entero en vez de esconderse en una nota al pie:

- **Modo local** (sin clave). El notebook se ejecuta de principio a fin. Todo lo que no
  necesita el servicio —que es más de lo que parece: `@traceable`, `RunTree`, el
  anonimizador, los evaluadores, el muestreo, los envoltorios de SDK— funciona de verdad.
  Las celdas que sí necesitan servicio se saltan y **dicen qué habrían hecho**.
- **Modo en línea** (con tu clave en `.env`). Las mismas celdas se conectan.

La frontera es explícita en el código, no en la prosa:

```python
@online("Crear el dataset de tickets", trazas=0)
def _():
    ds = cliente().create_dataset(dataset_name="tickets-curso")
    print(ds.id)
```

**Lo que esto significa para ti, dicho sin adornos:** las celdas `@online` no se han
ejecutado nunca contra el servicio real, porque el curso se escribió sin clave. Lo que
sí se hace es ejecutarlas **contra un LangSmith simulado** (`utils/langsmith_de_mentira.py`),
que implementa las rutas HTTP que el SDK usa y guarda estado entre llamadas.

Eso demuestra que ese código **corre**: que los argumentos son los que el SDK acepta, que
las respuestas se consumen bien y que el encadenado de llamadas se sostiene. **No**
demuestra la semántica del servidor real. La diferencia importa y por eso está escrita
aquí y no en una nota al pie.

Cuando se montó esa pasada aparecieron **cinco errores reales** que ninguna validación
estática podía ver, porque los símbolos existían y los nombres de los argumentos eran
correctos —lo que estaba mal era el tipo o la forma del objeto devuelto—. Están
arreglados y cada uno tiene su prueba en `pruebas/test_simulacion.py`.

## Preparación

```bash
cd langsmith
uv sync                       # o: pip install -r requirements.txt
cp .env.example .env          # opcional: solo para el modo en línea
jupyter lab
```

Sin `.env` el curso funciona. Es el modo por defecto.

## El presupuesto de trazas

El plan Developer sin método de pago da **5.000 trazas al mes y un mes de retención**.
Un experimento descuidado se lleva el 10 % en una celda, así que el presupuesto es
material del curso y no una advertencia:

```python
presupuesto_de_trazas(ejemplos=50, repeticiones=3, evaluadores_llm=2, etiqueta="regresión")
# 50 ejemplos × 3 repetición(es) × 3 traza(s) por ejemplo
# = 450 trazas  (9.0 % de las 5,000 del plan Developer)
```

Cada notebook declara su consumo estimado en la cabecera. El curso entero, en modo en
línea y de principio a fin, está presupuestado por debajo de **1.500 trazas**.

## Temario

Ver [`PLAN.md`](PLAN.md) para el detalle y la justificación de cada notebook.

| Módulo | Notebooks | Estado |
|---|---|---|
| 0 · Punto de partida | 1 | **listo** |
| 1 · Trazas: qué se registra y qué no | 5 + 1 proyecto | **listo** |
| 2 · Datasets y experimentos | 5 + 1 proyecto | **listo** |
| 3 · El humano en el bucle de la calidad | 2 + 1 proyecto | **listo** |
| 4 · Producción: mirar y actuar | 3 + 1 proyecto | **listo** |
| 5 · Gobierno | 2 | **listo** |

## El mapa de la superficie

Un curso completo no es el que toca todos los métodos del SDK: es el que te deja saber
**dónde estás**. Esto es la superficie de LangSmith repartida en tres montones, medida
sobre los 144 miembros públicos de `Client`.

**Lo que el curso enseña y ejecuta** (módulos 0-5): trazado automático y manual, `RunTree`
y trazas distribuidas, la API de ingesta a pelo, **OpenTelemetry en los dos sentidos**
(`tracing_mode`, el procesador para una instalación que ya existe, y la salida con la
convención `gen_ai.*` — ejecutado con un exportador en memoria, sin red), envío por lotes y sus cuatro formas de
perder trazas, anonimización, hilos y realimentación, datasets con versiones y *splits*,
experimentos con sus parámetros y sus dos trampas de puntuación, evaluadores de código y
de LLM, jueces alineados con kappa, colas de anotación y configuración de rúbricas,
coste y tokens leídos de la ejecución con la trampa de `ls_model_name`,
pruebas con modelo en CI con caché, monitorización, reglas y evaluación en línea, prompts
versionados, y el gobierno: espacios, claves, compartición, retención y borrado.

**Lo que el curso nombra sin desarrollar**, porque queda fuera del plan Developer o del
alcance del complemento:

| Superficie | Dónde se nombra | Por qué no más |
|---|---|---|
| **Insights** (agrupación automática de conversaciones) | P4, apartado 8 bis | Plan Plus o superior, y cuesta por conversación |
| **Agentes y habilidades en el Hub** | nb 15 | Mismo mecanismo que los prompts; lo que cambia es el riesgo, y ese sí se cuenta |
| **Cajas de arena (`sandboxes`)** | nb 16 | Superficie muy nueva; se enseña **qué es y por qué es de gobierno**, no cómo usarla |
| **Fórmulas de realimentación** | nb 11 | Ya no existen: el SDK levanta `NotImplementedError` y remite a la interfaz |
| **Exportar para afinar un modelo** | nb 06 | Una línea: `read_dataset_openai_finetuning` |
| **LangSmith autoalojado** | nb 17 | El curso asume la nube, pero sí enseña la trampa: por debajo de 0.16 las cosas degradan con un `warning` |

**Lo que no está y es deliberado**: los métodos obsoletos (19 de ellos, retirada anunciada
para el 31 de enero de 2027), las variantes `*_multipart` que el SDK ya desaconseja, y los
atributos internos del cliente. El notebook 16 enseña a detectar los avisos de
obsolescencia, que es lo que hace falta cuando esto cambie.

## Estado de la verificación

| Filtro | Resultado |
|---|---|
| Notebooks escritos | 22 (el curso entero: módulos 0 a 5) |
| Problemas estáticos | 0 |
| Notebooks que se ejecutan enteros, sin clave y **con la red cortada** | 22 de 22 |
| Intentos de salida a `smith.langchain.com` durante esa ejecución | **0** |
| Bloques `@online` que se ejecutan contra el LangSmith simulado | 37 de 40 |
| Bloques `@online` que no se pueden simular (llaman a un modelo, no a LangSmith) | 3, marcados `necesita_modelo=True` |
| Errores reales que destapó esa pasada | **5**, todos arreglados y con prueba |
| Pruebas | 184 de 184, con la red cortada también |
| Entornos vírgenes (`uv sync` **sin grupos** y `pip install -r requirements.txt`) | los dos pasan |

Celdas marcadas `@online`, escritas contra la firma real del SDK pero **no ejecutadas**:
están en los notebooks 00, 02, 03, 04, 05, 06, 07, 08, 09, 11, 12, 13, 14, 15, 16, 17 y
en los cuatro proyectos, señaladas una a una. Desde la pasada simulada, «no ejecutadas»
solo se aplica ya a las **tres** que necesitan un proveedor de modelos.

El módulo 2 se ejecuta entero en local gracias a dos mecanismos del SDK que amplían lo
verificable mucho más allá de lo previsto: `tracing_context(enabled="local")` construye
la traza sin enviarla, y `evaluate(..., upload_results=False)` corre el motor de
evaluación completo sobre ejemplos en memoria. Los dos están vigilados por pruebas: si
desaparecen, el curso deja de ser verificable y se sabrá aquí.

## Cómo se verifica

Los mismos filtros del curso de LangGraph, más uno que allí no hacía falta:

```bash
uv run _tools/validar.py                        # compila y cada símbolo del SDK existe
uv run pytest                                   # invariantes del material
uv run _tools/ejecutar_notebooks.py             # cada notebook, entero, sin clave y SIN RED
uv run _tools/ejecutar_notebooks.py --simulado  # y las celdas @online, contra un LangSmith de mentira
```

El tercero corta la resolución de `smith.langchain.com` antes de ejecutar nada. Es la
única forma de demostrar que el modo local es local: si un notebook dependiera del
servicio en silencio, se vería aquí.

## Convenciones

Las del curso de LangGraph: español para la teoría, inglés para el código, los notebooks
se editan en `_src/**/*.nbsrc` (texto plano) y se generan con `_tools/nbgen.py`, dos
ejercicios por notebook con la solución plegada. Los datos —los 400 tickets etiquetados—
se comparten con el otro curso a propósito.
