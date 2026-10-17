"""Builder del módulo 00 · Introducción y panorama de los sistemas de recomendación."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "recsys-course/_tools")
from _fund_common import Notebook, utils_cell  # noqa: E402

MOD = "recsys-course/00_intro"
LESSON = f"{MOD}/00_intro.ipynb"
PROJECT = f"{MOD}/00_proyecto_eda_popularidad.ipynb"

# =============================================================================
# LECCIÓN
# =============================================================================
nb = Notebook("Módulo 00 · Introducción a los sistemas de recomendación", colab_path=LESSON)
M, C = nb.md, nb.code

M(rf"""
{nb.badge()}

# 🎬 Módulo 00 · ¿Qué es un sistema de recomendación? El mapa completo

**Curso «Sistemas de Recomendación: de cero a nivel Netflix»** · Bloque I — Fundamentos

| | |
|---|---|
| **Nivel** | 🟢 Básico |
| **Duración estimada** | 2–2,5 h (lección) + 2 h (proyecto) |
| **GPU** | No necesaria (CPU). ≈ 0 unidades de Colab |
| **Prerrequisitos** | Python, pandas, NumPy y ML general. **Cero** conocimientos de recomendación |

> Esta es la puerta de entrada del curso. Si solo te quedas con una lección, que sea esta: aquí está el **mapa mental** que vas a ir rellenando durante los 19 módulos siguientes (01–19).
>
> 🧭 Antes de empezar, echa un vistazo a la [guía de estudio](../GUIA_DE_ESTUDIO.md): ruta recomendada, tiempos, mapa de dependencias entre conceptos y glosario ES/EN.
""")

M(r"""
## 🎯 Objetivos de aprendizaje

Al terminar esta lección serás capaz de:

1. **Definir** formalmente el problema de recomendación (predecir una puntuación $s(u, i, c)$ y devolver un top-K) y **distinguirlo** de la clasificación/regresión que ya conoces.
2. **Clasificar** un recomendador como basado en contenido, colaborativo, híbrido o basado en conocimiento, y **calcular a mano** una recomendación de cada uno de los dos primeros tipos.
3. **Diferenciar** feedback explícito e implícito y **enumerar** las señales que registra una plataforma de streaming.
4. **Dibujar** la arquitectura multi-etapa de la industria (*retrieval → ranking → re-ranking*) y **justificar** con números por qué existe.
5. **Describir** el ciclo de vida completo de un recomendador (datos → entrenamiento → evaluación offline → A/B → serving → monitoreo → reentreno) y las capas offline / nearline / online.
6. **Situar** cada herramienta del stack (FAISS, LightGBM, TorchRec, Feast, Kafka, Triton, MLflow…) en su etapa.
7. **Relatar** la historia del campo desde Tapestry (1992) hasta los recomendadores generativos (2024–2026).
8. **Construir** tu primer recomendador (popularidad) sobre MovieLens y **criticarlo**.
""")

C(r'''
# Colab ya trae numpy, pandas y matplotlib. pyarrow para parquet.
!pip install -q pandas matplotlib pyarrow
''')

C(r'''
import time
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

SEED = 42
rng = np.random.default_rng(SEED)
FAST_DEV_RUN = True          # True: tamaños pequeños para iterar rápido
warnings.filterwarnings("ignore", category=FutureWarning)
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 10})

# Paleta común del curso (una por etapa del embudo)
COL = {"retrieval": "#4C72B0", "ranking": "#DD8452", "rerank": "#55A868",
       "datos": "#8172B3", "gris": "#9E9E9E", "rojo": "#C44E52"}
''')

M(r"""
Vamos a dibujar bastantes diagramas. Para no repetir código, definimos dos ayudantes: una **caja** con texto y una **flecha** entre puntos.
""")

C(r'''
def caja(ax, x, y, w, h, texto, color="#4C72B0", fs=9, alpha=0.9, tc="white"):
    """Caja redondeada centrada en (x, y)."""
    p = FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                       fc=color, ec="none", alpha=alpha)
    ax.add_patch(p)
    ax.text(x, y, texto, ha="center", va="center", fontsize=fs, color=tc, wrap=True)


def flecha(ax, p1, p2, color="#555555", texto=None, fs=8, rad=0.0, lw=1.5):
    a = FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=12, color=color, lw=lw,
                        connectionstyle=f"arc3,rad={rad}")
    ax.add_patch(a)
    if texto:
        ax.text((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 + 0.12, texto, ha="center",
                fontsize=fs, color=color)


def lienzo(w=10, h=4, xlim=(0, 10), ylim=(0, 4)):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.axis("off")
    return fig, ax
''')

# ---------------------------------------------------------------------------
M(r"""
---
## 1. 💡 Intuición: el problema de la sobreabundancia

Abres Netflix un viernes a las 22:00. El catálogo tiene miles de títulos, pero tú vas a mirar como mucho unas decenas de carátulas antes de decidir… o de cerrar la app. **El recurso escaso no son las películas: es tu atención.**

Un sistema de recomendación (*recommender system*, *recsys*) es el software que decide **qué subconjunto minúsculo del catálogo te enseña, en qué orden y en qué sitio de la pantalla**. Es probablemente el sistema de ML con más impacto económico directo del mundo:

- Netflix: el recomendador *influye* en la elección de **~80 % de las horas reproducidas** (el resto viene de la búsqueda), y estimaban que personalización + recomendaciones les ahorran **más de 1.000 M$ al año** en retención (Gomez-Uribe & Hunt, 2015).
- YouTube: según su CPO Neal Mohan (CES 2018), **más del 70 % del tiempo de visualización** procede de recomendaciones, no de búsquedas.

### La analogía con lo que ya sabes
Piensa en una **matriz enorme** con una fila por usuario y una columna por película. Cada celda dice cuánto le gustó (o si la vio). Casi todas las celdas están **vacías** — nadie ha visto más que una fracción ínfima del catálogo. Recomendar es, en su forma más simple, **rellenar los huecos** y enseñar a cada usuario las celdas vacías con mayor valor predicho.

Veámoslo con un ejemplo de juguete que usaremos toda la lección: 5 usuarios × 6 películas.
""")

C(r'''
peliculas = ["Toy Story", "Matrix", "Titanic", "Alien", "Notting Hill", "Interstellar"]
usuarios = ["Ana", "Bruno", "Carla", "David", "Elena"]
# Ratings de 1 a 5; NaN = no la ha visto (¡la inmensa mayoría en la vida real!)
R = pd.DataFrame([
    [5, 4, np.nan, np.nan, 1, 5],
    [np.nan, 5, 1, 5, np.nan, 4],
    [4, np.nan, 5, 1, 5, np.nan],
    [np.nan, 4, np.nan, 5, 1, np.nan],
    [5, np.nan, 4, np.nan, 5, 2],
], index=usuarios, columns=peliculas)

fig, ax = plt.subplots(figsize=(7.5, 3.6))
im = ax.imshow(R.values, cmap="YlGnBu", vmin=0.5, vmax=5.5)
for i in range(R.shape[0]):
    for j in range(R.shape[1]):
        v = R.iat[i, j]
        ax.text(j, i, "?" if np.isnan(v) else int(v), ha="center", va="center",
                fontsize=13, color="#C44E52" if np.isnan(v) else "black",
                fontweight="bold" if np.isnan(v) else "normal")
ax.set_xticks(range(6), peliculas, rotation=20); ax.set_yticks(range(5), usuarios)
ax.set_title("Matriz usuario × película: recomendar = predecir los «?» y ordenar")
plt.colorbar(im, ax=ax, label="rating")
plt.tight_layout(); plt.show()
print(f"Celdas observadas: {R.notna().mean().mean():.0%} (en MovieLens-100K ≈ 6 %, en Netflix ≪ 1 %)")
''')

# ---------------------------------------------------------------------------
M(r"""
---
> 👀 **Qué debes observar en la matriz:** (1) hay más «?» que números incluso en un juguete de 5×6; en datos reales la proporción observada es del 6 % o menos, así que **el problema es sobre todo de huecos**; (2) los «?» no son ceros: Ana no ha visto *Titanic*, lo que no significa que la odie; (3) para rellenar un «?» puedes mirar **la fila** (qué más le gustó a Ana → contenido) o **la columna y otras filas** (a quién más le gustó *Titanic* y si se parece a Ana → colaborativo). Son las dos familias de la sección 3.

---
## 2. 📐 Teoría formal: ¿qué predice un recomendador?

Sean $\mathcal{U}$ el conjunto de usuarios, $\mathcal{I}$ el catálogo de ítems y $c$ el **contexto** (hora, dispositivo, país, fila de la página…). Un recomendador aprende una **función de puntuación**

$$s_\theta : \mathcal{U} \times \mathcal{I} \times \mathcal{C} \to \mathbb{R}$$

y, para un usuario $u$ en el contexto $c$, devuelve la lista de los $K$ ítems con mayor puntuación entre los **candidatos elegibles** $\mathcal{I}_{u,c} \subseteq \mathcal{I}$ (no vistos, disponibles en su país, aptos para su perfil…):

$$\text{Top-}K(u, c) = \operatorname*{arg\,top\text{-}K}_{i \in \mathcal{I}_{u,c}} \; s_\theta(u, i, c)$$

Dos formulaciones históricas:

| Formulación | Qué predice $s$ | Pérdida típica | Métrica típica | Cuándo |
|---|---|---|---|---|
| **Predicción de rating** (*rating prediction*) | el rating $\hat r_{ui}$ | MSE sobre las celdas observadas | RMSE / MAE | Netflix Prize (2006–09), feedback explícito |
| **Ranking top-N** (*top-N recommendation*) | una puntuación de preferencia cuyo **orden** importa | BPR, softmax, BCE con negativos | Recall@K, NDCG@K | **La industria hoy**, feedback implícito |

### En qué se parece y en qué NO se parece a tu ML de siempre
| ML supervisado clásico | Recomendación |
|---|---|
| Filas i.i.d. con etiqueta | Pares (usuario, ítem) **muy correlacionados**; la "etiqueta" de los no vistos es **desconocida**, no negativa |
| Predices un valor por fila | Lo que importa es el **orden relativo** dentro de la lista de cada usuario |
| Los datos vienen "del mundo" | Los datos los **genera tu propio sistema**: solo ves feedback de lo que recomendaste (*feedback loop*) |
| El test aleatorio es razonable | Hay que respetar el **tiempo**: entrenar con el pasado y evaluar en el futuro (módulo 01) |
| Accuracy / AUC | Métricas **de lista** (NDCG@K) + diversidad, novedad, negocio (módulo 02) |
| Un modelo | Una **cascada** de modelos con presupuestos de latencia distintos (sección 5) |
""")

# ---------------------------------------------------------------------------
M(r"""
---
## 3. Tipos de recomendadores

Hay cuatro grandes familias, según **de dónde sale la señal**:

- **Basado en contenido** (*content-based*): "te gustó *Matrix* (ciencia ficción, acción) → te recomiendo otras de ciencia ficción". Solo usa **tu** historial + atributos del ítem. Módulo 03.
- **Filtrado colaborativo** (*collaborative filtering*, CF): "usuarios que se parecen a ti vieron X". No necesita saber nada del ítem: aprende de los **patrones de co-consumo** de millones de personas. Módulos 04, 05 y casi todo el deep learning posterior.
- **Híbrido**: combina ambos (y casi todo lo que hay en producción lo es). Ejemplo: un *two-tower* cuya torre de ítem usa ID + texto + póster (módulos 08 y 11).
- **Basado en conocimiento / reglas** (*knowledge-based*): restricciones explícitas ("casas con 3 habitaciones bajo 300 k€", "solo contenido infantil"). Útil con compras raras (inmuebles, coches) y como capa de **políticas de negocio**.
""")

C(r'''
fig, ax = lienzo(11, 4.2, (0, 11), (0, 4.2))
caja(ax, 5.5, 3.6, 3.4, 0.6, "Sistemas de recomendación", "#333333", fs=11)
ramas = [
    (1.5, "Basado en contenido\n(atributos del ítem\n+ tu historial)", COL["retrieval"],
     "TF-IDF, BM25, embeddings\nde texto/imagen (CLIP)\n→ Módulo 03"),
    (4.2, "Filtrado colaborativo\n(patrones de\nco-consumo)", COL["ranking"],
     "kNN, EASE, MF/ALS, BPR\ntwo-tower, SASRec, grafos\n→ Módulos 04-05, 08-11"),
    (6.8, "Híbrido\n(contenido + CF\n+ contexto)", COL["rerank"],
     "Wide&Deep, DCN, DIN\nHSTU, foundation models\n→ Módulos 06-07, 11-12"),
    (9.5, "Basado en\nconocimiento / reglas", COL["datos"],
     "Restricciones, filtros,\npolíticas de negocio\n→ Módulos 13-14"),
]
for x, t, c, ej in ramas:
    flecha(ax, (5.5, 3.28), (x, 2.75))
    caja(ax, x, 2.3, 2.3, 0.85, t, c, fs=9)
    ax.text(x, 1.15, ej, ha="center", va="center", fontsize=8.5, color="#333333",
            bbox=dict(boxstyle="round", fc="#F4F4F4", ec="#CCCCCC"))
ax.set_title("Taxonomía de recomendadores (y dónde los verás en el curso)", fontsize=12)
plt.show()
''')

M(r"""
### 🧪 Experimento en papel: recomendar a Ana de dos formas

Ana no ha visto *Titanic* ni *Alien*. ¿Cuál le recomendamos?

**Contenido.** Describimos cada película por sus géneros (vector multi-hot $\mathbf{g}_i$). El perfil de Ana es la media de los géneros de lo que vio, **ponderada** por su rating centrado ($r_{ui} - \bar r_u$): lo que le gustó suma y lo que odió resta. Puntuamos cada película no vista con la similitud coseno:

$$\mathbf{p}_u = \sum_{i \in \mathcal{I}_u} (r_{ui} - \bar r_u)\, \mathbf{g}_i, \qquad s(u,i) = \cos(\mathbf{p}_u, \mathbf{g}_i)$$

**Colaborativo (user-kNN).** Buscamos usuarios parecidos a Ana (coseno entre sus ratings centrados, sobre las películas que ambos vieron) y predecimos su rating como media ponderada de los vecinos:

$$\hat r_{ui} = \bar r_u + \frac{\sum_{v} \text{sim}(u,v)\,(r_{vi} - \bar r_v)}{\sum_{v} |\text{sim}(u,v)|}$$
""")

C(r'''
generos = pd.DataFrame(  # multi-hot: animación, ciencia ficción, romance, terror, acción
    [[1, 0, 0, 0, 0], [0, 1, 0, 0, 1], [0, 0, 1, 0, 0],
     [0, 1, 0, 1, 1], [0, 0, 1, 0, 0], [0, 1, 0, 0, 0]],
    index=peliculas, columns=["animación", "sci-fi", "romance", "terror", "acción"])

def cos(a, b):
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))

u = "Ana"
vistas = R.loc[u].dropna()
no_vistas = R.columns[R.loc[u].isna()]
# --- Contenido ---
perfil = ((vistas - vistas.mean()).values[:, None] * generos.loc[vistas.index].values).sum(0)
s_contenido = {i: cos(perfil, generos.loc[i].values) for i in no_vistas}

# --- Colaborativo (user-kNN) ---
Rc = R.sub(R.mean(axis=1), axis=0)           # centramos por usuario
def sim_usuarios(a, b):
    comunes = R.loc[a].notna() & R.loc[b].notna()
    return cos(Rc.loc[a, comunes].values, Rc.loc[b, comunes].values) if comunes.sum() >= 2 else 0.0
sims = {v: sim_usuarios(u, v) for v in usuarios if v != u}
s_colab = {}
for i in no_vistas:
    vecinos = [v for v in sims if not np.isnan(R.at[v, i])]
    num = sum(sims[v] * Rc.at[v, i] for v in vecinos)
    den = sum(abs(sims[v]) for v in vecinos) + 1e-12
    s_colab[i] = float(np.clip(R.loc[u].mean() + num / den, 1, 5))  # recortamos a la escala 1-5

print("Similitud de Ana con los demás:", {k: round(v, 2) for k, v in sims.items()})
pd.DataFrame({"contenido (coseno)": s_contenido, "colaborativo (rating predicho)": s_colab}).round(2)
''')

M(r"""
Fíjate en lo que ha pasado:
- **Contenido** recomienda *Alien* porque comparte ciencia ficción y acción con *Matrix* e *Interstellar*, que Ana adora. No necesita a nadie más… pero **nunca saldrá de lo que ya conoce** (si solo ves sci-fi, solo te recomendará sci-fi).
- **Colaborativo** llega a la misma conclusión por otro camino: Ana se parece muchísimo a **David** (similitud ≈ 0,98: los dos ponen bien *Matrix* y odian *Notting Hill*) y algo a **Bruno** (≈ 0,38), y a ambos les encantó *Alien*. Fíjate también en **Carla**, de gustos opuestos a Ana (similitud ≈ −0,81): ella odió *Alien*, y con una similitud negativa eso **también suma** a favor de *Alien* (la predicción sale de la escala y la recortamos a 5). En cambio, *Titanic* la adoran Carla y Elena — justo las usuarias con gustos contrarios — y la odió Bruno, así que baja. No ha mirado ni un solo género: solo co-consumo. Su debilidad: un ítem **nuevo**, sin ratings, es invisible (*cold start*).

> ⚠️ Con 5 usuarios todo es frágil: similitudes calculadas sobre 2 películas en común son puro ruido. En el módulo 04 verás el *shrinkage* (penalizar similitudes con poco soporte) y por qué muchos sistemas descartan las similitudes negativas.

Que dos señales independientes coincidan es justo la idea de los **híbridos**. En producción se combinan para cubrir los puntos ciegos de cada una.
""")

# ---------------------------------------------------------------------------
M(r"""
---
## 4. Feedback explícito vs implícito

| | Explícito | Implícito |
|---|---|---|
| Ejemplos | estrellas, 👍/👎, "no me interesa" | impresión, clic, play, % visto, tiempo de permanencia (*dwell time*), búsqueda, añadir a "Mi lista", compartir, saltar intro |
| Volumen | escaso (muy pocos usuarios valoran) | **masivo** (cada sesión genera cientos de eventos) |
| Señal negativa | sí (1 estrella) | **ambigua**: no ver ≠ no gustar (quizá nunca se lo enseñaste) |
| Ruido | sesgo de selección (valoras lo que ya elegiste ver) | ruido (autoplay, el niño cogió el mando) |
| Quién lo usa | Netflix Prize, MovieLens | **toda la industria hoy**; Netflix sustituyó las estrellas por 👍/👎 en 2017 |

En CineMatch registraremos una **jerarquía de señales** (un embudo): cada paso es más escaso pero más fiable como señal de preferencia. Elegir **qué evento es el "positivo"** que optimizas es una de las decisiones de producto más importantes (y la verás en los módulos 01, 06 y 07).
""")

C(r'''
etapas = ["Impresión\n(se mostró la carátula)", "Clic / hover\nen la carátula", "Inicio de\nreproducción",
          "Visto ≥ 70 %", "Valoración\nexplícita (like/dislike)"]
volumen = np.array([1000, 120, 45, 25, 2])   # ILUSTRATIVO: orden de magnitud por cada 1000 impresiones
fig, ax = plt.subplots(figsize=(9, 3.6))
colores = plt.cm.viridis(np.linspace(0.15, 0.85, len(etapas)))
for k, (e, v, c) in enumerate(zip(etapas, volumen, colores)):
    w = np.log10(v) + 0.6
    ax.barh(len(etapas) - k, w, left=-w / 2, color=c, height=0.8)
    ax.text(w / 2 + 0.15, len(etapas) - k, f"{e.replace(chr(10), ' ')}  (~{v})", va="center", fontsize=9)
ax.set_xlim(-2.2, 6); ax.axis("off")
ax.annotate("", xy=(-2, 0.7), xytext=(-2, 5.3), arrowprops=dict(arrowstyle="->", lw=2, color="#555555"))
ax.text(-2.1, 3, "más escasa,\nmás fiable", rotation=90, va="center", ha="right", fontsize=9)
ax.set_title("Embudo de señales de un streaming (cifras ilustrativas por cada 1.000 impresiones, escala log)")
plt.show()
''')

# ---------------------------------------------------------------------------
M(r"""
---
> 👀 **Qué debes observar:** cada escalón tiene aproximadamente un orden de magnitud menos eventos que el anterior. Si eliges como positivo la valoración explícita, tendrás ~2 ejemplos por cada 1.000 impresiones; si eliges el clic, 120, pero mucho más ruidosos (*clickbait*). **No hay respuesta gratis**: el módulo 07 entrena varias de estas señales a la vez (multi-tarea) precisamente para no tener que elegir solo una.

---
## 5. 🏭 La arquitectura multi-etapa: el embudo de la industria

Este es **el diagrama más importante del curso**. Imagina que tienes un modelo de ranking buenísimo (un transformer con cientos de *features*). Cuesta, digamos, 20 µs por par (usuario, ítem). Puntuar un catálogo de 10 millones de ítems para **una sola petición** serían 200 s. Tienes ~100–200 ms. **No cabe.**

La solución universal (YouTube, Netflix, Meta, TikTok, Pinterest, Amazon…) es una **cascada**:

1. **Recuperación / generación de candidatos** (*retrieval*, *candidate generation*): modelos **baratos** que, de millones de ítems, sacan **cientos o miles** de candidatos plausibles. Típicamente varias fuentes en paralelo (embeddings + búsqueda ANN, co-visitación, popularidad reciente, "porque viste X"). Optimiza **recall**.
2. **Ranking**: un modelo **caro y preciso** (GBDT, DCN, DIN, multi-tarea) puntúa solo esos candidatos con cientos de *features*. Optimiza la **precisión del orden**.
3. **Re-ranking y políticas**: ajusta la lista final — diversidad, frescura, calibración, reglas de negocio (contenido propio, restricciones legales/parentales), exploración (bandits) — y la compone en la página (filas de la home).

El documento canónico es el paper de YouTube (Covington, Adams & Sargin, RecSys 2016), que describe exactamente dos redes: *candidate generation* y *ranking*.

> 💡 **Ya conoces este patrón si has montado un RAG.** *Retrieval* ≈ el **bi-encoder + base vectorial** que trae los 50 *chunks* más parecidos a la consulta (barato, optimiza recall); *ranking* ≈ el **cross-encoder / reranker** que reordena esos 50 mirando consulta y documento juntos (caro, optimiza precisión); *re-ranking y políticas* ≈ los filtros y la deduplicación que aplicas antes de meter el contexto en el prompt. La diferencia: en recsys la «consulta» es **el usuario y su historia**, no un texto, y el catálogo cambia cada día. Lo verás en detalle en el módulo 08.
""")

C(r'''
fig, ax = lienzo(12, 5.6, (0, 12), (-1.3, 5))
etapas = [
    ("Catálogo\n10⁶ – 10⁹ ítems", COL["gris"], 4.6, "—"),
    ("① Retrieval\n10³ candidatos", COL["retrieval"], 3.4, "~10-30 ms\nANN (FAISS/HNSW), two-tower,\nco-visitación, popularidad\nMód. 04-05, 08-11"),
    ("② Ranking\n10² ítems", COL["ranking"], 2.3, "~20-80 ms\nGBDT, DCN-v2, DIN,\nmulti-tarea (MMoE)\nMód. 06-07"),
    ("③ Re-ranking\n10-50 ítems", COL["rerank"], 1.4, "~5-10 ms\ndiversidad, calibración,\nreglas, bandits\nMód. 13-14"),
]
for k, (txt, c, h, det) in enumerate(etapas):
    xs = 0.3 + k * 2.55
    poly = plt.Polygon([[xs, 2.5 - h / 2], [xs, 2.5 + h / 2], [xs + 2.2, 2.5 + h / 2 - 0.45],
                        [xs + 2.2, 2.5 - h / 2 + 0.45]], fc=c, alpha=0.9)
    ax.add_patch(poly)
    ax.text(xs + 1.1, 2.5, txt, ha="center", va="center", color="white", fontsize=10, fontweight="bold")
    if det != "—":
        ax.text(xs + 1.1, -0.15, det, ha="center", va="top", fontsize=8, color="#333333")
caja(ax, 11.35, 2.5, 1.1, 1.0, "Página\n(home)", "#333333", fs=9)
flecha(ax, (10.0, 2.5), (10.75, 2.5))
ax.text(6, 4.85, "Cada etapa ve ~10× menos ítems y puede gastar ~10× más cómputo por ítem",
        ha="center", fontsize=11)
ax.text(6, 4.45, "(latencias: órdenes de magnitud típicos, no cifras de ninguna empresa concreta)",
        ha="center", fontsize=8, color="#777777")
plt.show()
''')

M(r"""
### 🧪 Experimento: ¿cuánto ahorra la cascada?

Simulemos un catálogo de ítems con *embeddings* aleatorios y comparemos dos estrategias para servir una petición:
- **Fuerza bruta**: pasar el modelo "caro" (una pequeña red con *features* cruzadas) por **todo** el catálogo.
- **Cascada**: producto escalar barato para quedarnos con 500 candidatos → modelo caro solo sobre ellos → re-ranking con una regla de diversidad (máx. 3 ítems por género).
""")

C(r'''
N_ITEMS = 100_000 if FAST_DEV_RUN else 1_000_000
D = 32
item_emb = rng.normal(size=(N_ITEMS, D)).astype(np.float32)
item_gen = rng.integers(0, 12, N_ITEMS)                     # "género" de cada ítem
user_emb = rng.normal(size=D).astype(np.float32)
# Modelo "caro": MLP de 3 capas sobre [usuario, ítem, usuario⊙ítem]
W1 = rng.normal(scale=0.1, size=(3 * D, 256)).astype(np.float32)
W2 = rng.normal(scale=0.1, size=(256, 128)).astype(np.float32)
W3 = rng.normal(scale=0.1, size=(128, 1)).astype(np.float32)

def modelo_caro(u, items):
    x = np.hstack([np.repeat(u[None], len(items), 0), items, u[None] * items])
    h = np.maximum(x @ W1, 0); h = np.maximum(h @ W2, 0)
    return (h @ W3).ravel()

def retrieval(u, k=500):
    s = item_emb @ u                                       # barato: un producto escalar por ítem
    return np.argpartition(-s, k)[:k]

def rerank(cands, scores, k=10, max_por_genero=3):
    final, cuenta = [], {}
    for i in cands[np.argsort(-scores)]:
        g = item_gen[i]
        if cuenta.get(g, 0) < max_por_genero:
            final.append(i); cuenta[g] = cuenta.get(g, 0) + 1
        if len(final) == k:
            break
    return final

t = {}
t0 = time.perf_counter(); s_all = modelo_caro(user_emb, item_emb); t["Fuerza bruta\n(modelo caro × catálogo)"] = time.perf_counter() - t0
t0 = time.perf_counter(); cands = retrieval(user_emb); t1 = time.perf_counter()
s_c = modelo_caro(user_emb, item_emb[cands]); t2 = time.perf_counter()
top = [int(i) for i in rerank(cands, s_c)]; t3 = time.perf_counter()
t["① Retrieval"], t["② Ranking (500)"], t["③ Re-ranking"] = t1 - t0, t2 - t1, t3 - t2
for k_, v in t.items():
    print(f"{k_.replace(chr(10), ' '):45s} {v * 1000:8.2f} ms")
print(f"Cascada total: {(t1 - t0 + t2 - t1 + t3 - t2) * 1000:.2f} ms  ·  top-10 final: {top}")
''')

C(r'''
fig, ax = plt.subplots(figsize=(8, 3.2))
nombres = list(t)
colores = [COL["rojo"], COL["retrieval"], COL["ranking"], COL["rerank"]]
ax.barh(nombres, [v * 1000 for v in t.values()], color=colores)
ax.set_xscale("log"); ax.set_xlabel("milisegundos (escala log)")
ax.invert_yaxis()
ax.set_title(f"Coste de servir 1 petición sobre {N_ITEMS:,} ítems: fuerza bruta vs cascada")
for y, v in enumerate(t.values()):
    ax.text(v * 1000 * 1.1, y, f"{v * 1000:.2f} ms", va="center", fontsize=9)
plt.tight_layout(); plt.show()
''')

M(r"""
Con un modelo de ranking realista (cientos de *features* que hay que **buscar** en un *feature store*, no solo multiplicar) la diferencia es aún mayor. Y la cascada tiene un precio: **lo que el retrieval no trae, el ranking no lo puede arreglar**. Por eso las métricas de cada etapa son distintas: *recall@1000* en retrieval, NDCG en ranking.

> 🏭 **Variante 2D: la home de Netflix.** No es una lista, es una **cuadrícula**: filas temáticas ("Porque viste…", "Tendencias", "Continuar viendo") y dentro de cada fila un orden. Hay que elegir **qué filas**, **en qué orden** y **qué ítems** en cada una, sin repetir. Es optimización a nivel de página (módulo 13).
""")

# ---------------------------------------------------------------------------
M(r"""
---
## 6. El ciclo de vida completo

Un recomendador no es un modelo: es un **bucle**. Lo que recomiendas hoy cambia lo que los usuarios ven, eso cambia los logs, y con esos logs entrenas el modelo de mañana. Si vienes de MLOps, esto te sonará — pero con una diferencia crucial: aquí **el modelo genera sus propios datos de entrenamiento** (*feedback loop*).
""")

C(r'''
pasos = [("Logs de eventos\n(Kafka)", COL["datos"]), ("Datos y features\n(feature store)", COL["datos"]),
         ("Entrenamiento\n(GPU, TorchRec)", COL["retrieval"]), ("Evaluación\noffline", COL["retrieval"]),
         ("Test A/B\n(online)", COL["ranking"]), ("Serving\n(retrieval→ranking)", COL["ranking"]),
         ("Monitoreo\n(drift, negocio)", COL["rerank"]), ("Reentreno\n(programado/trigger)", COL["rerank"])]
mods = ["01", "01·16", "03-12", "02", "15", "16", "17", "17"]
fig, ax = lienzo(8, 7.2, (-4, 4), (-3.8, 3.6))
n = len(pasos); R0 = 2.7
ang = np.pi / 2 - np.arange(n) * 2 * np.pi / n
for k in range(n):
    x, y = R0 * np.cos(ang[k]), R0 * np.sin(ang[k])
    caja(ax, x, y, 1.9, 0.8, pasos[k][0], pasos[k][1], fs=8.5)
    ax.text(x, y - 0.55, f"mód. {mods[k]}", ha="center", fontsize=7.5, color="#555555")
    a1, a2 = ang[k] - 0.33, ang[(k + 1) % n] + 0.33
    flecha(ax, (R0 * np.cos(a1), R0 * np.sin(a1)), (R0 * np.cos(a2), R0 * np.sin(a2)), rad=-0.25)
ax.text(0, 0.25, "USUARIOS", ha="center", fontsize=13, fontweight="bold")
ax.text(0, -0.35, "lo que recomiendas\nhoy son los datos\nde mañana", ha="center", fontsize=9, color=COL["rojo"])
ax.set_title("Ciclo de vida de un recomendador en producción", fontsize=12)
plt.show()
''')

M(r"""
### Offline, nearline y online (la arquitectura de Netflix)
Netflix popularizó (Amatriain & Basilico, *Netflix Tech Blog*, 2013) la división del cómputo en tres capas según su **frescura** y su **presupuesto de latencia**:

- **Offline** (batch, horas): entrenar modelos, precalcular *embeddings* y listas de candidatos, generar *features* agregadas. Sin límite de latencia, todo el histórico.
- **Nearline** (segundos–minutos): reaccionar a eventos recientes (acabas de terminar una serie → recalcular "porque viste…") sin bloquear la petición. Streaming con Kafka/Flink.
- **Online** (milisegundos): lo que ocurre durante la petición: retrieval ANN, ranking con *features* en tiempo real, re-ranking. Debe tener **fallbacks** (si el ranker cae, sirves listas precalculadas).
""")

C(r'''
fig, ax = lienzo(11, 4.4, (0, 11), (0, 4.4))
capas = [(3.6, "OFFLINE  (horas)", "Entrenar modelos · precalcular embeddings,\ncandidatos y features agregadas · backfills",
          COL["retrieval"], "Spark · Airflow/Metaflow · GPUs\nMLflow · data warehouse"),
         (2.2, "NEARLINE  (segundos-minutos)", "Reaccionar a eventos recientes · actualizar\nfeatures y listas sin bloquear la petición",
          COL["ranking"], "Kafka · Flink · Redis\nfeature store (Feast)"),
         (0.8, "ONLINE  (milisegundos)", "Retrieval ANN · ranking con features en\ntiempo real · re-ranking · fallbacks",
          COL["rerank"], "FAISS/HNSW · Triton · FastAPI\nRedis · caches")]
for y, titulo, desc, c, herr in capas:
    caja(ax, 1.9, y, 3.3, 1.05, titulo, c, fs=10)
    ax.text(3.9, y, desc, va="center", fontsize=9)
    ax.text(8.4, y, herr, va="center", fontsize=8.5, color="#444444",
            bbox=dict(boxstyle="round", fc="#F4F4F4", ec="#CCCCCC"))
ax.annotate("", xy=(0.12, 0.35), xytext=(0.12, 4.1), arrowprops=dict(arrowstyle="->", lw=2, color="#555"))
ax.text(0.0, 2.2, "más fresco · menos cómputo", rotation=90, va="center", ha="right", fontsize=8)
ax.set_title("Las tres capas de cómputo (Amatriain & Basilico, Netflix 2013)", fontsize=12)
plt.show()
''')

# ---------------------------------------------------------------------------
M(r"""
---
## 7. 🧰 El stack de herramientas, etapa por etapa

No hace falta que memorices esto ahora: es el índice de lo que vas a tocar con las manos durante el curso.

| Etapa | Qué resuelve | Herramientas de industria (y open source) | Módulo |
|---|---|---|---|
| Logging y datos | eventos de usuario, joins, splits | Kafka / Redpanda, Spark, pandas/Polars, Parquet, Pandera / Great Expectations | 01, 16, 17 |
| Features | *features* consistentes en entrenamiento y serving | **Feast**, Redis, Tecton | 16 |
| Retrieval | millones → miles en ms | EASE/ALS (`implicit`), **two-tower** (PyTorch/TorchRec), **FAISS**, ScaNN, hnswlib, Milvus/Qdrant/pgvector/Vespa | 04, 05, 08 |
| Ranking | orden preciso de cientos de candidatos | **LightGBM**/XGBoost (lambdarank), DCN-v2, DIN, MMoE/PLE (PyTorch, TorchRec, NVIDIA Merlin) | 06, 07 |
| Secuencial / generativo | historia del usuario como secuencia | SASRec, BERT4Rec, HSTU, semantic IDs (RQ-VAE) | 09, 11 |
| Re-ranking | diversidad, calibración, exploración | MMR, DPP, bandits (Vowpal Wabbit, Open Bandit Pipeline) | 13, 14 |
| LLMs y agentes | cold start, explicaciones, conversación | sentence-transformers, LLMs, **LangGraph** | 03, 12 |
| Evaluación | offline rigurosa | **ranx**, RecBole, Elliot, Microsoft Recommenders, recpack | 02 |
| Experimentación | A/B, interleaving | plataformas internas; statsmodels/scipy | 15 |
| Serving | latencia y escala | FastAPI, **NVIDIA Triton**, BentoML, Ray Serve, ONNX | 16 |
| MLOps | tracking, orquestación, monitoreo | **MLflow**, Airflow/Prefect/**Metaflow** (creado en Netflix), **Evidently**, Prometheus+Grafana | 17 |
""")

# ---------------------------------------------------------------------------
M(r"""
---
## 8. 📜 Treinta y cinco años en una línea temporal

- **1992 — Tapestry** (Xerox PARC, Goldberg et al.): acuñan *collaborative filtering*; los usuarios anotaban correos y filtraban por las anotaciones de otros.
- **1994 — GroupLens** (Resnick et al.): CF automático para noticias de Usenet. El grupo de Minnesota publicará después **MovieLens** (1997–hoy).
- **2003 — Amazon item-to-item CF** (Linden, Smith & York): en vez de buscar usuarios parecidos, precalcula ítems parecidos → escala a decenas de millones de clientes.
- **2006–2009 — Netflix Prize**: 1 M$ a quien mejorase un 10 % el RMSE de Cinematch. Lo ganó *BellKor's Pragmatic Chaos* (2009). Legado: factorización matricial, *ensembles*… y la lección de que el RMSE no era lo que importaba (módulo 02).
- **2008 — ALS para feedback implícito** (Hu, Koren & Volinsky). **2009 — BPR** (Rendle et al.): el giro hacia el ranking con señales implícitas.
- **2010 — Factorization Machines** (Rendle). **2014 — GBDT+LR** en Facebook Ads (He et al.).
- **2016 — YouTube DNN** (Covington et al.): la arquitectura de dos etapas con redes profundas. **Wide & Deep** (Google Play, Cheng et al.).
- **2018 — PinSage** (Pinterest, grafos a escala web), **SASRec** (Kang & McAuley, self-attention secuencial), **DIN** (Alibaba).
- **2019 — Two-tower con corrección de sesgo de muestreo** (Yi et al., YouTube) y la **crisis de reproducibilidad** (Ferrari Dacrema et al.): muchos modelos neuronales no superaban a baselines bien ajustados.
- **2023 — TIGER / semantic IDs** (Rajput et al., Google): recuperación **generativa**.
- **2024 — HSTU / Generative Recommenders** (Zhai et al., Meta): transformers de billones de parámetros, *scaling laws* en recomendación.
- **2025 — Foundation model de recomendación de Netflix** (Netflix Tech Blog) y **OneRec** (Kuaishou): un modelo grande y unificado sustituye a muchos modelos pequeños.
""")

C(r'''
hitos = [(1992, "Tapestry\n(CF)", 0), (1994, "GroupLens", 1), (1997, "MovieLens", 2),
         (2003, "Amazon\nitem-to-item", 0), (2006, "Netflix Prize\n(arranca)", 1), (2008, "ALS implícito", 2),
         (2009, "BPR · fin del\nNetflix Prize", 0), (2010, "Factorization\nMachines", 1),
         (2016, "YouTube DNN ·\nWide&Deep", 2), (2018, "PinSage ·\nSASRec · DIN", 0),
         (2019, "Two-tower logQ ·\ncrisis reproducib.", 1), (2023, "TIGER\n(semantic IDs)", 2),
         (2024, "HSTU\n(Meta)", 0), (2025, "Foundation model\nNetflix · OneRec", 1)]
eras = [(1990, 2005, "Memoria y vecinos", COL["datos"]), (2005, 2015, "Factorización latente", COL["retrieval"]),
        (2015, 2022, "Deep learning", COL["ranking"]), (2022, 2027, "Transformers\ny generativos", COL["rerank"])]
fig, ax = plt.subplots(figsize=(13, 4.6))
for a, b, nombre, c in eras:
    ax.add_patch(plt.Rectangle((a, -0.18), b - a, 0.36, color=c, alpha=0.9))
    ax.text((a + b) / 2, 0, nombre, ha="center", va="center", color="white", fontsize=8.5, fontweight="bold")
for k, (año, txt, nivel) in enumerate(hitos):
    signo = 1 if k % 2 == 0 else -1
    y = signo * [0.6, 1.1, 1.6][nivel]
    ax.plot([año, año], [0.18 * signo, y - 0.2 * signo], color="#777777", lw=0.8)
    ax.plot(año, 0.18 * signo, "o", color="#555555", ms=3)
    ax.text(año, y, f"{año}\n{txt}", ha="center", va="center", fontsize=7.5)
ax.set_xlim(1989, 2027.5); ax.set_ylim(-2.0, 2.0); ax.axis("off")
ax.set_title("Historia de los sistemas de recomendación", fontsize=12)
plt.tight_layout(); plt.show()
''')

# ---------------------------------------------------------------------------
M(r"""
---
## 9. 🧪 Primer contacto con datos reales: MovieLens

**MovieLens** (GroupLens, Universidad de Minnesota; Harper & Konstan, 2015) es el "MNIST" de la recomendación: ratings de 1 a 5 estrellas de usuarios reales de [movielens.org](https://movielens.org). Hay varias versiones en <https://files.grouplens.org/datasets/movielens/>: **100K** (943 usuarios, 1.682 películas), **1M**, **latest-small**, **25M** y **32M**. Será el dataset de CineMatch durante todo el curso.

La celda siguiente escribe en tu sesión el módulo `cinematch_data.py`, el pipeline de datos del curso (lo construirás tú en el módulo 01). Si no hay red, `load_movielens` genera **datos sintéticos** con el mismo esquema para que el notebook nunca se bloquee.
""")

utils_cell(nb, ["cinematch_data.py"])

C(r'''
from cinematch_data import load_movielens

ratings, items = load_movielens("100k")
n_u, n_i = ratings.user_id.nunique(), ratings.item_id.nunique()
print(f"{len(ratings):,} ratings · {n_u:,} usuarios · {n_i:,} películas")
print(f"Densidad de la matriz: {len(ratings) / (n_u * n_i):.2%}  →  dispersión {1 - len(ratings) / (n_u * n_i):.2%}")
print(f"Periodo: {pd.to_datetime(ratings.timestamp.min(), unit='s'):%Y-%m-%d} → "
      f"{pd.to_datetime(ratings.timestamp.max(), unit='s'):%Y-%m-%d}")
ratings.merge(items, on="item_id").head()
''')

C(r'''
fig, axes = plt.subplots(1, 3, figsize=(14, 3.6))
ratings.rating.value_counts().sort_index().plot.bar(ax=axes[0], color=COL["retrieval"])
axes[0].set(title="Distribución de ratings", xlabel="estrellas", ylabel="nº de ratings")
axes[0].tick_params(axis="x", rotation=0)

pop = ratings.item_id.value_counts().values
axes[1].plot(np.arange(1, len(pop) + 1), pop, color=COL["ranking"])
corte = int(0.2 * len(pop))
axes[1].fill_between(np.arange(1, corte + 1), pop[:corte], color=COL["ranking"], alpha=0.3)
axes[1].set(title=f"Long tail: el 20 % más popular acapara el {pop[:corte].sum() / pop.sum():.0%} de ratings",
            xlabel="película (ordenada por popularidad)", ylabel="nº de ratings")

act = ratings.user_id.value_counts().values
axes[2].hist(act, bins=50, color=COL["rerank"])
axes[2].set(title="Actividad por usuario", xlabel="nº de ratings del usuario", ylabel="nº de usuarios", yscale="log")
plt.tight_layout(); plt.show()
''')

M(r"""
Tres hechos que verás en **todos** los datasets de recomendación:
1. **Ratings sesgados al alto**: la gente valora lo que eligió ver, y elige lo que cree que le gustará (sesgo de selección, módulo 01).
2. **Long tail**: unas pocas películas concentran la mayoría de las interacciones; miles tienen un puñado.
3. **Actividad muy desigual**: unos pocos usuarios aportan muchísimos datos; la mayoría, pocos.

### Tu primer recomendador: popularidad
El recomendador más simple que existe: a todo el mundo, las películas más vistas que aún no ha visto. Parece una broma, pero es **el baseline que hay que batir siempre**, y a menudo cuesta.
""")

C(r'''
def recomendar_populares(ratings: pd.DataFrame, user_id: int, k: int = 10) -> pd.DataFrame:
    vistas = set(ratings.loc[ratings.user_id == user_id, "item_id"])
    ranking = ratings.item_id.value_counts()
    top = [i for i in ranking.index if i not in vistas][:k]
    return items.set_index("item_id").loc[top, ["title", "year", "genres"]].assign(
        n_ratings=ranking.loc[top].values)

recomendar_populares(ratings, user_id=1)
''')

M(r"""
¿Qué le pasa a este recomendador?
- **No es personal**: cualquier usuario recibe casi la misma lista (solo cambia lo que ya ha visto).
- **Cobertura ridícula**: de 1.682 películas solo muestra unas pocas decenas en todo el sistema → la cola larga nunca se descubre.
- **Se autorrefuerza** (*rich get richer*): lo popular se muestra más → se ve más → es más popular.
- **Ignora el tiempo**: "lo más visto desde 1997" no es "lo que se está viendo esta semana".

…y aun así, en el proyecto de esta sesión verás que bate a una alternativa aparentemente más "inteligente". En el módulo 02 aprenderás a medir todo esto con rigor.
""")

# ---------------------------------------------------------------------------
M(r"""
---
## 10. 🏭 En producción

- **Netflix**: la home es una cuadrícula de filas personalizadas; cada fila la genera un algoritmo distinto (PVR — *personalized video ranker*, *Top-N*, *trending*, *continue watching*, *because you watched*) y otra capa elige y ordena las filas (Gomez-Uribe & Hunt, 2015). Incluso la **carátula** que ves se personaliza con bandits (Netflix Tech Blog, *Artwork Personalization at Netflix*, 2017; módulo 14). En 2025 describieron un **foundation model** de recomendación entrenado sobre el historial de interacciones a escala de LLM que alimenta a muchos modelos aguas abajo.
- **YouTube**: arquitectura de dos etapas con redes profundas (Covington et al., 2016); el objetivo del ranker es el **tiempo de visualización esperado**, no el clic. Después: two-tower con corrección logQ (Yi et al., 2019), multi-tarea MMoE (Zhao et al., 2019).
- **Amazon**: item-to-item CF precalculado offline (Linden et al., 2003) — "los clientes que compraron esto también compraron…". Sigue siendo un generador de candidatos muy potente.
- **Pinterest**: PinSage, GCN sobre un grafo de miles de millones de nodos (Ying et al., 2018).
- **TikTok (ByteDance)**: *Monolith* (Liu et al., 2022), entrenamiento en tiempo real con tablas de *embeddings* sin colisiones: el modelo se actualiza en minutos con lo que acabas de ver.
- **Meta**: HSTU (Zhai et al., 2024) — un transformer generativo para ranking y retrieval que sustituye *features* hechas a mano por la secuencia cruda de acciones.
""")

M(r"""
---
## 11. 🧠 Secretos de la élite

1. **La popularidad es un baseline brutalmente fuerte.** En muchos datasets públicos, un recomendador de "lo más popular (reciente)" bate a modelos personalizados mal ajustados. Si tu modelo nuevo no gana con claridad a popularidad en un split temporal, no tienes modelo. Ferrari Dacrema et al. (2019) intentaron reproducir 18 modelos neuronales de conferencias top: solo 7 eran reproducibles y **6 de esos 7 perdían frente a baselines simples bien ajustados** (kNN, grafos, popularidad en algunos casos).
2. **La métrica offline no es el negocio.** Los equipos de élite usan la evaluación offline para **filtrar** ideas y el test A/B como **juez final**: mejoras offline que no se trasladan online (*offline-online gap*) son lo normal, no la excepción. Netflix lo explica en Gomez-Uribe & Hunt (2015).
3. **El objetivo importa más que la arquitectura.** YouTube anunció en 2012 que pasaba a optimizar **tiempo de visualización** en lugar de clics, para premiar vídeos que la gente realmente ve y no *clickbait*. Elegir el "positivo" (clic, play, 70 % visto, retención a 30 días) cambia el producto más que cambiar de modelo.
4. **El retrieval pone el techo.** Los equipos dedican tanto esfuerzo a la generación de candidatos (varias fuentes, *recall@1000*) como al ranker, porque un ítem que no entra en el embudo no existe.
5. **Tu sistema contamina sus propios datos.** Solo observas feedback de lo que mostraste. Entrenar ingenuamente sobre esos logs amplifica sesgos y homogeneiza el consumo (Chaney, Stewart & Engelhardt, RecSys 2018). Por eso los grandes reservan tráfico de **exploración** o inserciones aleatorias (KuaiRand, 2022, se construyó así).
6. **La frescura es una *feature*, no un detalle.** Un modelo entrenado con logs históricos aprende la popularidad *media* del pasado y infravalora lo recién llegado. YouTube lo resolvió con una sola *feature*, la **edad del ejemplo de entrenamiento** (*example age*), que se pone a 0 en serving: el modelo aprende la dependencia temporal de la popularidad y deja de penalizar el contenido nuevo (Covington et al., 2016, sección 3.3). TikTok lleva la idea al extremo actualizando el modelo en minutos (Monolith, Liu et al., 2022).
7. **La página es el producto, no la lista.** Optimizar cada fila por separado produce una home repetitiva; los sistemas maduros optimizan la página entera (diversidad entre filas, deduplicación, posición).
""")

M(r"""
## ⚠️ Errores comunes

- Tratar los ítems no vistos como **negativos** ("no la vio → no le gusta"). Lo más probable es que **nunca se la enseñaste**.
- Evaluar con un **split aleatorio** y creerte el número: mezclas futuro y pasado (*leakage*, módulo 01).
- Optimizar RMSE cuando tu producto muestra una **lista top-K** (módulo 02).
- Empezar por un modelo profundo sin haber medido antes **popularidad, popularidad reciente e item-kNN**.
- Olvidar las **reglas de negocio** (contenido no disponible en el país, restricciones parentales, ítems ya vistos) y descubrirlas en producción.
- Diseñar solo el modelo y no el **bucle**: logging de impresiones, monitoreo y reentreno (módulos 16–17).
""")

M(r"""
---
## 📝 Autoevaluación

**1.** ¿Por qué no se puede usar directamente el mejor modelo de ranking sobre todo el catálogo?
<details><summary>Respuesta</summary>Por latencia y coste: puntuar millones de ítems con un modelo caro por cada petición no cabe en ~100 ms. Se usa una cascada: retrieval barato (miles de candidatos) → ranking caro (cientos) → re-ranking (decenas).</details>

**2.** Un usuario no ha visto *Alien*. ¿Es un ejemplo negativo?
<details><summary>Respuesta</summary>No necesariamente. En feedback implícito, "no visto" mezcla "no le interesa" con "nunca se le mostró" o "no lo conoce". Por eso se habla de datos <i>missing not at random</i> y se usan negativos muestreados o ponderados (módulos 01 y 05).</details>

**3.** ¿Qué ventaja tiene el filtrado colaborativo sobre el basado en contenido, y qué desventaja?
<details><summary>Respuesta</summary>Ventaja: descubre relaciones que los atributos no capturan (gustos "raros" compartidos) y produce serendipia. Desventaja: no puede recomendar ítems nuevos sin interacciones (cold start de ítem) ni servir bien a usuarios nuevos.</details>

**4.** Asigna cada herramienta a su etapa: FAISS, LightGBM-lambdarank, MMR, Feast, Kafka.
<details><summary>Respuesta</summary>FAISS → retrieval (búsqueda ANN). LightGBM-lambdarank → ranking. MMR → re-ranking (diversidad). Feast → features (offline/online). Kafka → logging/streaming de eventos (nearline).</details>

**5.** ¿Qué diferencia hay entre las capas offline, nearline y online?
<details><summary>Respuesta</summary>Frescura y presupuesto de latencia: offline = batch de horas con todo el histórico (entrenar, precalcular); nearline = reaccionar en segundos/minutos a eventos sin bloquear la petición; online = milisegundos durante la petición, con fallbacks.</details>

**6.** ¿Qué lección dejó el Netflix Prize además de la factorización matricial?
<details><summary>Respuesta</summary>Que optimizar RMSE sobre ratings no es lo mismo que mejorar el producto: Netflix no llevó a producción el ensemble ganador completo porque la ganancia no compensaba el coste de ingeniería, y su negocio había migrado al streaming con señales implícitas y listas top-K.</details>

**7.** ¿Por qué es peligroso entrenar cada día con los logs del recomendador actual sin más?
<details><summary>Respuesta</summary>Porque solo contienen feedback de lo que el sistema eligió mostrar (sesgo de exposición). El modelo nuevo aprende a imitar al viejo y los sesgos se amplifican (feedback loop, homogeneización). Se mitiga con exploración, corrección por propensión (IPS) y datos aleatorizados.</details>

**8. (Razonamiento)** CineMatch tiene 50.000 títulos y un ranker que tarda 50 µs por par. Quieres responder en 100 ms y dedicar como mucho 40 ms al ranking. ¿Cuántos candidatos debe traer, como máximo, el *retrieval*? ¿Qué le pasa al sistema si el retrieval no incluye la película que el usuario habría visto?
<details><summary>Respuesta</summary>40 ms / 50 µs = 800 candidatos (en la práctica menos, por el coste de buscar <i>features</i>). Puntuar los 50.000 costaría 2,5 s. Si el retrieval no trae la película correcta, <b>ningún ranker puede recuperarla</b>: el recall del retrieval es el techo de todo el embudo (por eso se mide <i>recall@1000</i> en esa etapa).</details>

**9. (Transferencia)** Tu equipo propone evaluar el primer modelo personalizado con un split aleatorio 80/20 de las valoraciones, «como en cualquier clasificador». Da dos razones de la tabla de la sección 2 por las que eso puede engañar.
<details><summary>Respuesta</summary>(1) Las interacciones no son i.i.d.: un split aleatorio mete en train valoraciones <b>posteriores</b> a las de test (el modelo «ve el futuro», p. ej. la popularidad final de una película). (2) Lo que importa es el orden de la lista de cada usuario en el futuro, no el error por fila; un split temporal simula mejor lo que pasará al desplegar. Lo medirás con números en los módulos 01 y 02.</details>
""")

M(r"""
---
## 📚 Referencias

**Papers**
- Goldberg, Nichols, Oki & Terry (1992). *Using collaborative filtering to weave an information tapestry*. Communications of the ACM 35(12). <https://doi.org/10.1145/138859.138867>
- Resnick, Iacovou, Suchak, Bergstrom & Riedl (1994). *GroupLens: an open architecture for collaborative filtering of netnews*. CSCW. <https://doi.org/10.1145/192844.192905>
- Linden, Smith & York (2003). *Amazon.com recommendations: item-to-item collaborative filtering*. IEEE Internet Computing 7(1). <https://doi.org/10.1109/MIC.2003.1167344>
- Hu, Koren & Volinsky (2008). *Collaborative Filtering for Implicit Feedback Datasets*. ICDM. <https://doi.org/10.1109/ICDM.2008.22>
- Rendle, Freudenthaler, Gantner & Schmidt-Thieme (2009). *BPR: Bayesian Personalized Ranking from Implicit Feedback*. UAI. <https://arxiv.org/abs/1205.2618>
- Harper & Konstan (2015). *The MovieLens Datasets: History and Context*. ACM TiiS 5(4). <https://doi.org/10.1145/2827872>
- Gomez-Uribe & Hunt (2015). *The Netflix Recommender System: Algorithms, Business Value, and Innovation*. ACM TMIS 6(4). <https://doi.org/10.1145/2843948>
- Covington, Adams & Sargin (2016). *Deep Neural Networks for YouTube Recommendations*. RecSys. <https://doi.org/10.1145/2959100.2959190>
- Chaney, Stewart & Engelhardt (2018). *How Algorithmic Confounding in Recommendation Systems Increases Homogeneity and Decreases Utility*. RecSys. <https://arxiv.org/abs/1710.11214>
- Ferrari Dacrema, Cremonesi & Jannach (2019). *Are We Really Making Much Progress? A Worrying Analysis of Recent Neural Recommendation Approaches*. RecSys. <https://arxiv.org/abs/1907.06902>
- Yi et al. (2019). *Sampling-Bias-Corrected Neural Modeling for Large Corpus Item Recommendations*. RecSys. <https://doi.org/10.1145/3298689.3346996>
- Liu et al. (2022). *Monolith: Real Time Recommendation System With Collisionless Embedding Table*. <https://arxiv.org/abs/2209.07663>
- Rajput et al. (2023). *Recommender Systems with Generative Retrieval* (TIGER). NeurIPS. <https://arxiv.org/abs/2305.05065>
- Zhai et al. (2024). *Actions Speak Louder than Words: Trillion-Parameter Sequential Transducers for Generative Recommendations* (HSTU). ICML. <https://arxiv.org/abs/2402.17152>

**Blogs de ingeniería**
- Amatriain & Basilico (2012). *Netflix Recommendations: Beyond the 5 stars*. Netflix Tech Blog. <https://netflixtechblog.com/netflix-recommendations-beyond-the-5-stars-part-1-55838468f429>
- Amatriain & Basilico (2013). *System Architectures for Personalization and Recommendation*. Netflix Tech Blog. <https://netflixtechblog.com/system-architectures-for-personalization-and-recommendation-e081aa94b5d8>
- Chandrashekar, Amat, Basilico & Jebara (2017). *Artwork Personalization at Netflix*. Netflix Tech Blog. <https://netflixtechblog.com/artwork-personalization-c589f074ad76>
- Netflix (2025). *Foundation Model for Personalized Recommendation*. Netflix Tech Blog (<https://netflixtechblog.com>).
- YouTube Creator Blog (2012). *YouTube Now: Why We Focus on Watch Time*.

**Libros y cursos**
- Aggarwal (2016). *Recommender Systems: The Textbook*. Springer.
- Ricci, Rokach & Shapira (eds.) (2022). *Recommender Systems Handbook*, 3.ª ed. Springer.
- Falk (2019). *Practical Recommender Systems*. Manning.
""")

nb.save(LESSON)

# =============================================================================
# PROYECTO
# =============================================================================
pj = Notebook("Proyecto 00 · EDA de MovieLens y primer recomendador", colab_path=PROJECT)
M, C = pj.md, pj.code

M(rf"""
{pj.badge()}

# 🛠️ Proyecto 00 · EDA de MovieLens y la primera home de CineMatch

| | |
|---|---|
| **Nivel** | 🟢 Básico |
| **Duración estimada** | 2 h |
| **GPU** | No necesaria. ≈ 0 unidades de Colab |
| **Prerrequisitos** | Lección 00 |

## 🎬 Contexto de negocio
Acabas de incorporarte como **primera ML engineer de CineMatch**, una plataforma de streaming que se lanza en dos semanas. La CEO quiere que la home **no sea un catálogo alfabético**. Tienes un volcado de valoraciones de una beta (usaremos **MovieLens-100K**) y te pide:

1. Un **análisis exploratorio** que el equipo de producto pueda entender (¿cuánto sabemos de cada usuario? ¿qué películas mueven la plataforma?).
2. Una **primera home**: fila "Top 10 en CineMatch" + filas por género.
3. Una **crítica honesta**: ¿qué tal funciona? ¿qué le falta? ¿qué harías en el siguiente sprint?

## 📦 Dataset
**MovieLens-100K** (GroupLens): 100.000 ratings (1–5) de 943 usuarios sobre 1.682 películas, 1997–1998, con géneros. Descarga oficial: <https://files.grouplens.org/datasets/movielens/ml-100k.zip>. Si no hay red, el cargador genera datos sintéticos con el mismo esquema.

## ✅ Entregables y rúbrica
| Entregable | Criterio |
|---|---|
| EDA (6 gráficos) | distribución de ratings, long tail con curva de Lorenz, actividad por usuario, ratings en el tiempo, géneros, nota media vs popularidad |
| 3 recomendadores no personalizados | popularidad, mejor nota media, **media bayesiana** (nota media "amortiguada") |
| Home por filas | `home(user_id)` devuelve un dict `fila → lista de títulos` sin repetir películas ni mostrar las ya vistas |
| Mini-evaluación temporal | HitRate@10 de cada recomendador ocultando las últimas 5 valoraciones (≥ 4★) de cada usuario. **Objetivo: HitRate@10 de la popularidad ≥ 3× el de "mejor nota media"** |
| Crítica | 5 limitaciones concretas con una propuesta para cada una |
""")

C(r'''
!pip install -q pandas matplotlib pyarrow
''')

C(r'''
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SEED = 42
np.random.seed(SEED)
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False})
''')

utils_cell(pj, ["cinematch_data.py"])

C(r'''
from cinematch_data import load_movielens

ratings, items = load_movielens("100k")
df = ratings.merge(items, on="item_id")
df["fecha"] = pd.to_datetime(df.timestamp, unit="s")
df.head()
''')

M(r"""
---
## Parte 1 · EDA

### TODO 1 — Cifras clave
Calcula y muestra: nº de usuarios, películas, ratings, **densidad** de la matriz ($|\text{ratings}| / (|U|\cdot|I|)$), rating medio, mediana de ratings por usuario y por película, y % de películas con menos de 5 ratings.
""")

C(r'''
def cifras_clave(df: pd.DataFrame) -> pd.Series:
    # TODO: devuelve una pd.Series con las cifras pedidas (nombres en español)
    raise NotImplementedError

cifras_clave(df)
''')

M(r"""
### TODO 2 — Seis gráficos
1. Distribución de ratings (barras).
2. **Curva de Lorenz** de la popularidad de películas (eje x: % de películas de menos a más populares; eje y: % acumulado de ratings) + índice de Gini.
3. Histograma de ratings por usuario (escala log).
4. Nº de ratings por semana a lo largo del tiempo.
5. Nº de películas y nº de ratings por género (un ítem con varios géneros cuenta en cada uno; pista: `str.split("|")` + `explode`).
6. Dispersión **nota media vs nº de ratings** por película (eje x log). ¿Qué ves en la zona de pocos ratings?

<details><summary>🪜 Pista 1 (Lorenz)</summary>Cuenta ratings por película con <code>value_counts()</code>, ordénalos de menor a mayor y usa <code>np.cumsum(x) / x.sum()</code> para el eje y; el eje x es <code>np.arange(1, n+1) / n</code>. Dibuja también la diagonal (igualdad perfecta) como referencia.</details>
<details><summary>🪜 Pista 2 (semana)</summary><code>pd.to_datetime(df.timestamp, unit="s").dt.to_period("W")</code> y luego <code>groupby(...).size()</code>.</details>

> 💡 Pista Gini: con las popularidades ordenadas de menor a mayor $x_{(1)} \le \dots \le x_{(n)}$, $G = \frac{\sum_{k=1}^{n} (2k - n - 1)\, x_{(k)}}{n \sum_k x_{(k)}}$.
""")

C(r'''
def gini(x: np.ndarray) -> float:
    # TODO
    raise NotImplementedError

def graficos_eda(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    # TODO: los 6 gráficos, uno en cada eje de `axes.ravel()`, con títulos y ejes en español
    raise NotImplementedError

graficos_eda(df)
''')

M(r"""
---
## Parte 2 · Tres recomendadores no personalizados

### TODO 3 — Popularidad, nota media y media bayesiana
La nota media "cruda" premia películas con **un solo** rating de 5★. La **media bayesiana** (la que usaba el Top 250 de IMDb) mezcla la media de la película con la media global $\mu$, con un peso $m$ (nº de "votos virtuales"):

$$\text{WR}_i = \frac{n_i}{n_i + m}\,\bar r_i + \frac{m}{n_i + m}\,\mu$$

Implementa tres funciones que devuelvan una `pd.Series` `item_id → puntuación` ordenada de mayor a menor. Prueba $m$ = percentil 75 del nº de ratings por película (pista: en ML-100K sale $m = 80$).
""")

C(r'''
def score_popularidad(train: pd.DataFrame) -> pd.Series:
    # TODO: nº de ratings por película, de mayor a menor
    raise NotImplementedError

def score_media(train: pd.DataFrame) -> pd.Series:
    # TODO: nota media por película, de mayor a menor
    raise NotImplementedError

def score_bayesiano(train: pd.DataFrame, m: float | None = None) -> pd.Series:
    # TODO: media bayesiana; si m es None usa el percentil 75 de n_i
    raise NotImplementedError

for nombre, f in [("popularidad", score_popularidad), ("media", score_media), ("bayesiana", score_bayesiano)]:
    top = f(df).head(5).index
    print(f"{nombre:12s}", items.set_index("item_id").loc[top, "title"].tolist())
''')

M(r"""
### TODO 4 — La home por filas
Implementa `home(user_id, train, score_fn, generos, k)` que devuelva un `dict` con:
- `"Top 10 en CineMatch"`: los $k$ mejores según `score_fn`, excluyendo lo ya visto.
- Una fila por cada género de `generos` (los $k$ mejores de ese género según la misma puntuación).
- **Sin repetir** películas entre filas (la primera fila que la reclama se la queda) y **sin mostrar lo ya visto**.

<details><summary>🪜 Pista 1</summary>Mantén un <code>set</code> <code>usados</code> que empiece con lo que el usuario ya vio en <code>train</code>. Recorre la puntuación ordenada y añade a la fila solo ítems que no estén en <code>usados</code>; al añadir, mételos en el set.</details>
<details><summary>🪜 Pista 2</summary>Precalcula <code>generos_de = items.set_index("item_id")["genres"].str.split("|")</code>. Para la fila de un género, recorre los candidatos (ya ordenados por <code>score</code>) quedándote con los que tienen ese género en <code>generos_de[i]</code>, y aplica la misma lógica de <code>usados</code>. Una función interna <code>llenar(pool)</code> evita repetir código.</details>
""")

C(r'''
GENEROS_HOME = ["Comedy", "Drama", "Action", "Thriller", "Sci-Fi"]

def home(user_id: int, train: pd.DataFrame, score_fn=None, generos=GENEROS_HOME, k: int = 10) -> dict:
    # TODO
    raise NotImplementedError

for fila, titulos in home(1, df, score_bayesiano).items():
    print(f"{fila}: {titulos[:4]} ...")
''')

M(r"""
---
## Parte 3 · ¿Funciona? Mini-evaluación temporal

Simulamos el futuro: para cada usuario ocultamos sus **5 últimas** valoraciones en el tiempo y nos quedamos como "relevantes" las que tienen ≥ 4★. Entrenamos con el resto y medimos **HitRate@10**: fracción de usuarios con al menos un relevante en su top-10 (excluyendo lo ya visto en train). En el módulo 02 verás métricas más finas.

### TODO 5 — Split y HitRate@10

<details><summary>🪜 Pista 1 (split)</summary>Ordena por <code>["user_id", "timestamp"]</code> y usa <code>groupby("user_id").cumcount(ascending=False) &lt; n</code> para marcar las n últimas de cada usuario.</details>
<details><summary>🪜 Pista 2 (HitRate)</summary>Para cada usuario: toma los relevantes de test (rating ≥ 4), recorre <code>score.index</code> saltando lo visto en train hasta tener k ítems y comprueba si la intersección con los relevantes es no vacía. Promedia sobre los usuarios con al menos un relevante.</details>
""")

C(r'''
def split_ultimas(df: pd.DataFrame, n: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    # TODO: las n últimas interacciones de cada usuario (por timestamp) a test
    raise NotImplementedError

def hit_rate_at_k(score: pd.Series, train: pd.DataFrame, test: pd.DataFrame, k: int = 10) -> float:
    # TODO: relevantes = test con rating >= 4; recomienda top-k no vistos en train
    raise NotImplementedError

train, test = split_ultimas(df)
resultados = {n: hit_rate_at_k(f(train), train, test) for n, f in
              [("popularidad", score_popularidad), ("media", score_media), ("bayesiana", score_bayesiano)]}
resultados
''')

M(r"""
### TODO 6 — Crítica (markdown)
Escribe 5 limitaciones concretas de esta home y una propuesta para cada una (piensa en: personalización, cobertura/long tail, tiempo/frescura, usuarios nuevos, bucle de retroalimentación, métricas).

*Tu respuesta aquí.*
""")

M(r"""
---
## ⛔ SPOILER — Solución de referencia

Intenta resolverlo primero. Lo que sigue es una solución completa y ejecutable.
""")

C(r'''
def cifras_clave(df: pd.DataFrame) -> pd.Series:
    n_u, n_i, n_r = df.user_id.nunique(), df.item_id.nunique(), len(df)
    por_item = df.item_id.value_counts()
    return pd.Series({
        "usuarios": n_u, "películas": n_i, "ratings": n_r,
        "densidad": round(n_r / (n_u * n_i), 4),
        "rating medio": round(df.rating.mean(), 3),
        "mediana ratings/usuario": df.user_id.value_counts().median(),
        "mediana ratings/película": por_item.median(),
        "% películas con <5 ratings": round(100 * (por_item < 5).mean(), 1),
    })

cifras_clave(df)
''')

C(r'''
def gini(x: np.ndarray) -> float:
    x = np.sort(np.asarray(x, float))
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum()))

def graficos_eda(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    a = axes.ravel()
    df.rating.value_counts().sort_index().plot.bar(ax=a[0], color="#4C72B0", rot=0)
    a[0].set(title="1 · Distribución de ratings", xlabel="estrellas", ylabel="nº ratings")
    pop = np.sort(df.item_id.value_counts().values)
    a[1].plot(np.linspace(0, 100, len(pop)), 100 * np.cumsum(pop) / pop.sum(), color="#DD8452", label="Lorenz")
    a[1].plot([0, 100], [0, 100], "--", color="gray", label="igualdad perfecta")
    a[1].set(title=f"2 · Curva de Lorenz (Gini = {gini(pop):.2f})", xlabel="% películas (menos → más populares)",
             ylabel="% acumulado de ratings"); a[1].legend()
    a[2].hist(df.user_id.value_counts().values, bins=50, color="#55A868")
    a[2].set(title="3 · Ratings por usuario", xlabel="nº ratings", ylabel="nº usuarios", yscale="log")
    df.set_index("fecha").rating.resample("W").size().plot(ax=a[3], color="#8172B3")
    a[3].set(title="4 · Ratings por semana", xlabel="fecha", ylabel="nº ratings")
    g = df[["item_id", "genres"]].assign(genero=df.genres.str.split("|")).explode("genero")
    resumen = g.groupby("genero").agg(ratings=("item_id", "size"), peliculas=("item_id", "nunique"))
    resumen.sort_values("ratings").plot.barh(ax=a[4], color=["#4C72B0", "#DD8452"])
    a[4].legend(loc="lower right")
    a[4].set(title="5 · Ratings y películas por género", xlabel="cantidad", ylabel=""); a[4].set_xscale("log")
    st = df.groupby("item_id").rating.agg(["mean", "size"])
    a[5].scatter(st["size"], st["mean"], s=6, alpha=0.4, color="#C44E52")
    a[5].set(xscale="log", title="6 · Nota media vs popularidad", xlabel="nº ratings (log)", ylabel="nota media")
    plt.tight_layout(); plt.show()

graficos_eda(df)
''')

M(r"""
**Lectura del gráfico 6**: a la izquierda (pocos ratings) la nota media se dispersa entre 1 y 5 — es **ruido**: una película con un único 5★ no es "la mejor del catálogo". A la derecha la varianza se estrecha. Es la razón de la media bayesiana.
""")

C(r'''
def score_popularidad(train: pd.DataFrame) -> pd.Series:
    return train.item_id.value_counts().sort_values(ascending=False, kind="stable")

def score_media(train: pd.DataFrame) -> pd.Series:
    return train.groupby("item_id").rating.mean().sort_values(ascending=False, kind="stable")

def score_bayesiano(train: pd.DataFrame, m: float | None = None) -> pd.Series:
    st = train.groupby("item_id").rating.agg(["mean", "size"])
    m = st["size"].quantile(0.75) if m is None else m
    mu = train.rating.mean()
    wr = st["size"] / (st["size"] + m) * st["mean"] + m / (st["size"] + m) * mu
    return wr.sort_values(ascending=False, kind="stable")

for nombre, f in [("popularidad", score_popularidad), ("media", score_media), ("bayesiana", score_bayesiano)]:
    top = f(df).head(5).index
    print(f"{nombre:12s}", items.set_index("item_id").loc[top, "title"].tolist())
''')

C(r'''
GENEROS_HOME = ["Comedy", "Drama", "Action", "Thriller", "Sci-Fi"]
titulo = items.set_index("item_id")["title"]
generos_de = items.set_index("item_id")["genres"].str.split("|")

def home(user_id: int, train: pd.DataFrame, score_fn=score_popularidad, generos=GENEROS_HOME, k: int = 10) -> dict:
    score = score_fn(train)
    vistas = set(train.loc[train.user_id == user_id, "item_id"])
    usadas: set = set()
    filas = {}
    candidatos = [i for i in score.index if i not in vistas]
    def llenar(pool):
        sel = [i for i in pool if i not in usadas][:k]
        usadas.update(sel)
        return [titulo[i] for i in sel]
    filas["Top 10 en CineMatch"] = llenar(candidatos)
    for g in generos:
        filas[f"Lo mejor de {g}"] = llenar([i for i in candidatos if g in generos_de.get(i, [])])
    return filas

for fila, titulos in home(1, df, score_bayesiano).items():
    print(f"{fila}: {titulos[:4]} ...")
''')

C(r'''
def split_ultimas(df: pd.DataFrame, n: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.sort_values(["user_id", "timestamp"], kind="stable")
    desde_final = df.groupby("user_id").cumcount(ascending=False)
    return df[desde_final >= n], df[desde_final < n]

def hit_rate_at_k(score: pd.Series, train: pd.DataFrame, test: pd.DataFrame, k: int = 10) -> float:
    relevantes = test[test.rating >= 4].groupby("user_id").item_id.agg(set)
    vistas = train.groupby("user_id").item_id.agg(set)
    orden = score.index.to_numpy()
    hits = []
    for u, rel in relevantes.items():
        vis = vistas.get(u, set())
        top = [i for i in orden[: k + len(vis)] if i not in vis][:k]
        hits.append(len(rel.intersection(top)) > 0)
    return float(np.mean(hits))

train, test = split_ultimas(df)
resultados = {n: hit_rate_at_k(f(train), train, test) for n, f in
              [("popularidad", score_popularidad), ("media", score_media), ("bayesiana", score_bayesiano)]}
pd.Series(resultados).plot.bar(color=["#4C72B0", "#C44E52", "#55A868"], rot=0,
                               title="HitRate@10 (últimas 5 valoraciones de cada usuario)")
plt.ylabel("HitRate@10"); plt.show()
resultados
''')

C(r'''
# Cobertura: ¿qué fracción del catálogo llega a enseñarse a algún usuario?
def cobertura(score: pd.Series, train: pd.DataFrame, k: int = 10) -> float:
    vistas = train.groupby("user_id").item_id.agg(set)
    orden = score.index.to_numpy()
    mostradas = set()
    for u, vis in vistas.items():
        mostradas.update([i for i in orden[: k + len(vis)] if i not in vis][:k])
    return len(mostradas) / train.item_id.nunique()

{n: round(cobertura(f(train), train), 3) for n, f in
 [("popularidad", score_popularidad), ("media", score_media), ("bayesiana", score_bayesiano)]}
''')

M(r"""
### Crítica de referencia
1. **No es personal**: todos los usuarios ven la misma home (salvo lo ya visto). → Siguiente sprint: item-kNN / EASE (módulo 04), "porque viste X".
2. **Cobertura mínima** (unas decenas de películas de 1.682): la cola larga nunca se descubre y los productores de nicho no reciben exposición. → Métricas de cobertura y re-ranking por diversidad (módulos 02 y 13).
3. **Ignora el tiempo**: la popularidad "de siempre" no es la de esta semana. → Popularidad con ventana o decaimiento (módulo 01).
4. **Bucle de retroalimentación**: lo que mostramos es lo que se ve y lo que se ve es lo que mostramos. → Loguear impresiones, reservar exploración (módulo 14).
5. **"Mejor nota media" es engañosa**: favorece películas con 1–2 ratings; la media bayesiana lo corrige pero sigue sin personalizar. Y **HitRate** con un único corte por usuario es una evaluación pobre: falta un split temporal global, NDCG, intervalos de confianza (módulos 01 y 02).

Observa el resultado clave: el recomendador "más inteligente" (nota media) **pierde por goleada** frente a la popularidad. La popularidad captura algo real: la probabilidad *a priori* de que alguien vea algo. Es el primer "secreto de la élite": **nunca subestimes a la popularidad.**
""")

M(r"""
---
## 🚀 Retos extra
1. **Popularidad reciente**: puntúa con los ratings de los últimos 30 días del train o con decaimiento exponencial. ¿Mejora el HitRate@10?
2. **Popularidad por segmento**: usa `load_users("100k")` (edad, género, ocupación) y calcula popularidad dentro de cada grupo de edad. ¿Gana a la global?
3. **Filas personalizadas**: ordena las filas de género según el género favorito de cada usuario.
4. **Intervalos de confianza**: bootstrap sobre usuarios del HitRate@10. ¿Es significativa la diferencia entre popularidad y media bayesiana?

## 🤔 Reflexión (producción / MLOps)
- Si esta home se despliega mañana, ¿qué eventos necesitas **loguear** desde el día 1 para poder entrenar algo mejor dentro de un mes? (Pista: **impresiones**, no solo clics.)
- ¿Cómo detectarías que la fila "Top 10" se ha quedado obsoleta? ¿Con qué frecuencia la recalcularías?
- ¿Qué *fallback* sirve tu API si el futuro modelo personalizado no responde a tiempo?
""")

pj.save(PROJECT)
