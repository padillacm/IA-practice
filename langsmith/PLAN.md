# Plan: curso de LangSmith

Documento de planificación para una rama nueva, complementaria al curso de LangGraph que
ya está en `langgraph/` (38 notebooks, módulos 0-7).

> **Estado:** plan aprobado en lo esencial (cuenta Developer, formato complemento). La rama
> todavía **no está creada** — hace falta tu visto bueno explícito para crearla y empujarla,
> porque mi permiso actual es solo para `claude/langgraph-notebooks-course-nokcof`.

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

## 4. Temario propuesto

**16 notebooks de contenido + 4 de proyecto**, en cinco módulos. Frente a los 38 del curso
de LangGraph, es un complemento proporcionado: unas 22-26 horas.

### Módulo 0 · Punto de partida (1 notebook)

**`00_por_que_langsmith`** — Qué resuelve y qué no. El mapa contra lo que ya sabes: dónde
encaja cada pieza respecto a los notebooks 17, 27 y 30. Cuenta, clave, proyecto, y las
cuatro variables de entorno que gobiernan todo (`LANGSMITH_TRACING`, `_API_KEY`, `_PROJECT`,
`_ENDPOINT`). **El presupuesto de trazas** y cómo trabajar el curso sin agotarlo. El
mecanismo de los dos modos (con clave y sin ella).

### Módulo 1 · Trazas: qué se registra y qué no (4 + 1)

| Notebook | Contenido | Verificación |
|---|---|---|
| `01_anatomia_de_una_traza` | `@traceable`, `RunTree`, `dotted_order`, tipos de run, cómo se construye la jerarquía por dentro | **Ejecutable offline** |
| `02_instrumentar_de_verdad` | Automático en LangChain/LangGraph, `wrap_openai` para el SDK a pelo, metadata, tags, `run_name`, proyecto dinámico. Y qué **no** se instrumenta solo | Mixta |
| `03_hilos_y_realimentacion` | El `thread_id` de LangSmith frente al de LangGraph: no son lo mismo y se relacionan a mano. Feedback del usuario final con tokens prefirmados | Mixta |
| `04_lo_que_no_debe_salir` | El anonimizador con reglas propias, `hide_inputs`/`hide_outputs`, y la decisión explícita de mandar o no el contenido. **Cierra el hueco que deja el notebook 30** | **Ejecutable offline** |
| **`P1 · Instrumentar el agente de soporte`** | Coger el agente del curso de LangGraph y responder con trazas preguntas que sin ellas son adivinar | Mixta |

### Módulo 2 · Datasets y experimentos (4 + 1)

| Notebook | Contenido |
|---|---|
| `05_datasets` | Crear, versionar, *splits*, los tres tipos (kv, chat, llm). Y el bucle que importa: `create_example_from_run` — de una traza de producción a un caso de prueba |
| `06_experimentos` | `evaluate()` a fondo: *target*, `summary_evaluators`, `experiment_prefix`, repeticiones, concurrencia. Comparar dos experimentos |
| `07_evaluadores` | Código frente a juez LLM. `openevals`, rúbricas, `EvaluationResult`, claves de feedback. Los evaluadores del notebook 27 dentro de LangSmith |
| `08_regresion_de_verdad` | Varianza, cuántas repeticiones hacen falta, umbral con tolerancia **medida** (retoma el nb 17), y `evaluate_comparative` para comparaciones por pares |
| **`P2 · Conjunto dorado de tickets`** | Sobre los 400 tickets etiquetados que ya tiene el curso: línea base, experimento y detección de regresión |

### Módulo 3 · El humano en el bucle de la calidad (2 + 1)

| Notebook | Contenido |
|---|---|
| `09_anotacion` | Colas de anotación, `add_runs_to_annotation_queue`, esquemas de feedback, cómo se escribe una rúbrica que dos personas interpreten igual |
| `10_alinear_el_juez` | **El notebook que casi nadie escribe**: medir el acuerdo entre tu juez LLM y tus anotadores humanos, y corregir el juez hasta que valga. Un juez sin alinear es una métrica inventada |
| **`P3 · Un juez que sirve`** | Anotar 30 casos, medir el acuerdo, iterar el prompt del juez, volver a medir |

### Módulo 4 · Producción: mirar y actuar (3 + 1)

| Notebook | Contenido |
|---|---|
| `11_monitorizar` | Paneles, monitores, alertas. Qué métricas para un agente — retoma la discusión del nb 30: tareas completadas, no latencia |
| `12_reglas_y_evaluacion_en_linea` | Automatizaciones: mandar trazas a un dataset o a una cola sin intervención. Evaluar **en producción**, muestreado, y qué cuesta |
| `13_prompts_versionados` | Hub, *commits*, Playground, y el puente con los *assistants* del notebook 18: dónde vive de verdad la versión de un prompt |
| **`P4 · Capstone: el bucle completo`** | Producción → traza → regla → dataset → experimento → mejora → despliegue. Es el ciclo entero, con los tickets del curso |

### Módulo 5 · Gobierno (2)

| Notebook | Contenido |
|---|---|
| `14_organizacion_y_accesos` | Organizaciones, espacios de trabajo, roles, claves y su rotación, registro de auditoría |
| `15_retencion_y_cumplimiento` | Retención por plan, qué se guarda, borrado, y el RGPD sobre trazas. **Cierra del todo el notebook 30**: la capa que su código no borra |

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

Decisión pendiente menor: si `langsmith/` comparte `pyproject.toml` con `langgraph/` o tiene
el suyo. **Recomiendo compartirlo** (un solo lock, un solo entorno, y los notebooks de
LangSmith importan del curso de LangGraph sin acrobacias), con un grupo de dependencias
`langsmith` aparte.

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
| **1** | Infraestructura + módulos 0 y 1 | 6 | Trazas es lo primero que se usa y lo más verificable offline |
| **2** | Módulo 2 | 5 | Evaluación: donde está el grueso del valor |
| **3** | Módulo 3 | 3 | Alinear el juez, que depende de tener experimentos |
| **4** | Módulo 4 | 4 | Producción y el capstone |
| **5** | Módulo 5 + README + CI | 2 | Gobierno y cierre |

Después de la fase 1 tendría sentido que dieras una pasada con tu clave: confirma el
mecanismo de los dos modos y detecta pronto cualquier desajuste de la parte online, antes de
que lo repita en 14 notebooks más.

---

## 9. Lo que necesito de ti para empezar

1. **Permiso para crear la rama.** Propongo `claude/langsmith-notebooks-course`. Mi permiso
   actual es solo para `claude/langgraph-notebooks-course-nokcof`, así que no la creo hasta
   que lo digas.
2. **Nada más.** La clave de LangSmith **no me la des**: no la necesito (escribo para los dos
   modos y verifico el offline) y no quiero que una clave tuya acabe en un entorno efímero.
   La pondrás tú en tu `.env`, que está en `.gitignore`.

Y una pregunta abierta, por si tienes preferencia: **¿empiezo por la fase 1 completa, o
prefieres un notebook piloto** (el `01_anatomia_de_una_traza`) para validar el tono, el
mecanismo de los dos modos y el nivel de profundidad antes de comprometer el resto?
