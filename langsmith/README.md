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

**Lo que esto significa para ti, dicho sin adornos:** las celdas `@online` están escritas
desde la documentación y desde la firma real de cada función del SDK instalado —el
validador comprueba que cada símbolo existe—, pero **no las he podido ejecutar**. Las
locales sí, todas, en cada *commit*. El recuento está más abajo. Si una celda en línea
falla, `@online` la señala y el notebook sigue; es un error del material.

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
| 3 · El humano en el bucle de la calidad | 2 + 1 proyecto | 1 de 3 |
| 4 · Producción: mirar y actuar | 3 + 1 proyecto | pendiente |
| 5 · Gobierno | 2 | pendiente |

## Estado de la verificación

| Filtro | Resultado |
|---|---|
| Notebooks escritos | 14 (módulos 0, 1 y 2 completos; módulo 3 en curso) |
| Problemas estáticos | 0 |
| Notebooks que se ejecutan enteros, sin clave y **con la red cortada** | 14 de 14 |
| Intentos de salida a `smith.langchain.com` durante esa ejecución | **0** |
| Pruebas | 113 de 113, con la red cortada también |
| Entornos vírgenes (`uv sync` y `pip install -r requirements.txt`) | los dos pasan |

Celdas marcadas `@online`, escritas contra la firma real del SDK pero **no ejecutadas**:
están en los notebooks 04, 05, 06, 07, 08, 09 y en los dos proyectos, señaladas una a una.

El módulo 2 se ejecuta entero en local gracias a dos mecanismos del SDK que amplían lo
verificable mucho más allá de lo previsto: `tracing_context(enabled="local")` construye
la traza sin enviarla, y `evaluate(..., upload_results=False)` corre el motor de
evaluación completo sobre ejemplos en memoria. Los dos están vigilados por pruebas: si
desaparecen, el curso deja de ser verificable y se sabrá aquí.

## Cómo se verifica

Los mismos filtros del curso de LangGraph, más uno que allí no hacía falta:

```bash
uv run _tools/validar.py              # compila y cada símbolo del SDK existe
uv run pytest                         # invariantes del material
uv run _tools/ejecutar_notebooks.py   # cada notebook, entero, sin clave y SIN RED
```

El tercero corta la resolución de `smith.langchain.com` antes de ejecutar nada. Es la
única forma de demostrar que el modo local es local: si un notebook dependiera del
servicio en silencio, se vería aquí.

## Convenciones

Las del curso de LangGraph: español para la teoría, inglés para el código, los notebooks
se editan en `_src/**/*.nbsrc` (texto plano) y se generan con `_tools/nbgen.py`, dos
ejercicios por notebook con la solución plegada. Los datos —los 400 tickets etiquetados—
se comparten con el otro curso a propósito.
