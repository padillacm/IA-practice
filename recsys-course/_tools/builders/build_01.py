"""Builder del módulo 01 · Datos de interacción, sesgos, splits y baselines."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "recsys-course/_tools")
from _fund_common import Notebook, utils_cell, writefile_chunks  # noqa: E402

MOD = "recsys-course/01_data"
LESSON = f"{MOD}/01_data.ipynb"
PROJECT = f"{MOD}/01_proyecto_pipeline_datos.ipynb"

# =============================================================================
# LECCIÓN
# =============================================================================
nb = Notebook("Módulo 01 · Datos de interacción y baselines", colab_path=LESSON)
M, C = nb.md, nb.code

M(rf"""
{nb.badge()}

# 🗂️ Módulo 01 · Datos de interacción: matrices dispersas, sesgos, splits y baselines

**Curso «Sistemas de Recomendación: de cero a nivel Netflix»** · Bloque I — Fundamentos

| | |
|---|---|
| **Nivel** | 🟢 Básico |
| **Duración estimada** | 3 h (lección) + 2,5 h (proyecto) |
| **GPU** | No necesaria. ≈ 0 unidades de Colab (con `SCALE="full"` y MovieLens-1M, CPU alta RAM opcional) |
| **Prerrequisitos** | Módulo 00 |

> En recomendación, **la mayoría de los errores graves no están en el modelo, sino en los datos y en cómo se parten**. Un split mal hecho puede hacer que un modelo mediocre parezca de estado del arte. Esta lección es la base sobre la que se apoya todo el curso: el pipeline de datos de CineMatch que construyes aquí lo reutilizarán todos los módulos siguientes.
""")

M(r"""
## 🎯 Objetivos de aprendizaje

1. **Representar** interacciones usuario–ítem como matrices dispersas (COO/CSR/CSC) y **estimar** su coste de memoria.
2. **Cuantificar** la *long tail* (curva de Lorenz, Gini, cabeza vs cola) de un dataset.
3. **Explicar y simular** los sesgos principales: popularidad, exposición, selección (MNAR) y posición, y el *feedback loop* que los amplifica.
4. **Construir** señales implícitas (play, % visto, *dwell time*, confianza) a partir de un log de eventos.
5. **Comparar** estrategias de muestreo de negativos y **medir** cuántos "negativos" son en realidad positivos futuros.
6. **Implementar** splits aleatorio, *leave-one-out* y temporal global, y **demostrar** con números el *data leakage* temporal.
7. **Construir y ajustar** baselines fuertes: popularidad global, por segmento y reciente.
8. **Elegir** un dataset público adecuado para cada problema (streaming, e-commerce, noticias, música, CTR, bandits).
""")

C(r'''
!pip install -q pandas pyarrow scipy matplotlib
''')

C(r'''
import time
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.sparse as sp

SEED = 42
rng = np.random.default_rng(SEED)
SCALE = "small"                     # "small" → MovieLens-100K · "full" → MovieLens-1M
SIZE = "100k" if SCALE == "small" else "1m"
warnings.filterwarnings("ignore", category=FutureWarning)
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False})
COL = {"train": "#4C72B0", "val": "#DD8452", "test": "#C44E52", "gris": "#9E9E9E", "verde": "#55A868"}
''')

utils_cell(nb, ["cinematch_data.py"])

C(r'''
import cinematch_data as cd

ratings, items = cd.load_movielens(SIZE)
users = cd.load_users(SIZE)             # demografía (None si no hay red / dataset sin usuarios)
print(ratings.shape, items.shape, None if users is None else users.shape)
ratings.head()
''')

# ---------------------------------------------------------------------------
M(r"""
---
## 1. 💡 Intuición: de un log de eventos a una matriz

Una plataforma no "tiene ratings": tiene un **log de eventos** — una tabla larguísima, ordenada en el tiempo, con filas del tipo `(usuario, ítem, tipo de evento, timestamp, contexto)`. Todo recomendador empieza **agregando** ese log en una matriz usuario × ítem $\mathbf{R} \in \mathbb{R}^{|U| \times |I|}$ y decidiendo:

- **Qué evento cuenta como señal** (¿rating ≥ 4? ¿play? ¿≥ 70 % visto?).
- **Qué valor** poner en la celda (1, el rating, una confianza).
- **Qué pasado** usar para entrenar y **qué futuro** para evaluar.

Las tres decisiones cambian el resultado más que la elección de modelo.
""")

C(r'''
fig, axes = plt.subplots(1, 2, figsize=(12, 3.8), gridspec_kw={"width_ratios": [1.1, 1]})
log = pd.DataFrame({"usuario": ["Ana", "Ana", "Bruno", "Carla", "Ana", "Bruno", "Carla", "Bruno"],
                    "ítem": ["Matrix", "Alien", "Matrix", "Titanic", "Interstellar", "Alien", "Matrix", "Titanic"],
                    "evento": ["play 95%", "play 12%", "play 100%", "rating 5", "play 80%", "play 60%", "impresión", "impresión"],
                    "t": [1, 2, 3, 4, 5, 6, 7, 8]})
axes[0].axis("off")
tabla = axes[0].table(cellText=log.values, colLabels=log.columns, loc="center", cellLoc="center")
tabla.scale(1, 1.4)
axes[0].set_title("Log de eventos (ordenado en el tiempo)")
U, I = ["Ana", "Bruno", "Carla"], ["Matrix", "Alien", "Titanic", "Interstellar"]
M_ = np.full((3, 4), np.nan)
for _, r in log.iterrows():
    if r.evento.startswith("play"):
        M_[U.index(r.usuario), I.index(r["ítem"])] = int(r.evento.split()[1][:-1]) / 100
    elif r.evento.startswith("rating"):
        M_[U.index(r.usuario), I.index(r["ítem"])] = 1.0
axes[1].imshow(np.nan_to_num(M_, nan=-0.3), cmap="Blues", vmin=-0.3, vmax=1)
for a in range(3):
    for b in range(4):
        axes[1].text(b, a, "·" if np.isnan(M_[a, b]) else f"{M_[a, b]:.2f}", ha="center", va="center")
axes[1].set_xticks(range(4), I); axes[1].set_yticks(range(3), U)
axes[1].set_title("→ agregado: matriz usuario × ítem (valor = fracción vista)")
plt.tight_layout(); plt.show()
''')

M(r"""
Fíjate en dos detalles que parecen menores y no lo son:
- Las **impresiones sin play** (Carla–Matrix, Bruno–Titanic) son la mejor fuente de **negativos reales**: se lo enseñaste y no lo quiso. Si no las logueas, no las tendrás nunca. Casi ningún dataset público las trae (MIND, KuaiRand y Open Bandit sí).
- Ana vio *Alien* al 12 %: ¿es positivo o negativo? Definir el umbral es una decisión de producto.
""")

# ---------------------------------------------------------------------------
M(r"""
---
## 2. 📐 Matrices dispersas

Con $|U|$ usuarios y $|I|$ ítems, la matriz densa ocupa $|U|\cdot|I|$ celdas, pero solo hay $\text{nnz}$ (*number of non-zeros*) observadas. La **densidad** $\rho = \text{nnz} / (|U|\cdot|I|)$ suele estar entre $10^{-2}$ y $10^{-6}$.

Formatos de `scipy.sparse` que usarás constantemente:
- **COO** (*coordinate*): tres arrays `row`, `col`, `data`. Ideal para **construir**.
- **CSR** (*compressed sparse row*): `indptr` (longitud $|U|+1$), `indices`, `data`. La fila $u$ son las posiciones `indptr[u]:indptr[u+1]`. Acceso rápido **por usuario** (su historial) y productos matriz-vector.
- **CSC**: lo mismo por columnas → acceso rápido **por ítem**.

Memoria (float32 + índices int32): denso $= 4\,|U||I|$ bytes; CSR $\approx 8\,\text{nnz} + 4(|U|+1)$ bytes.
""")

C(r'''
# CSR "a mano" para entender la estructura
filas = np.array([0, 0, 1, 1, 1, 2])        # usuario
cols = np.array([0, 3, 0, 1, 2, 2])         # ítem
vals = np.array([1, 1, 1, 1, 1, 1], dtype=np.float32)
X_toy = sp.csr_matrix((vals, (filas, cols)), shape=(3, 4))
print("Densa:\n", X_toy.toarray())
print("indptr :", X_toy.indptr, " ← la fila u ocupa indices[indptr[u]:indptr[u+1]]")
print("indices:", X_toy.indices)
print("data   :", X_toy.data)
print("Historial del usuario 1:", X_toy.indices[X_toy.indptr[1]:X_toy.indptr[2]])
''')

C(r'''
X, u2i, i2i = cd.to_csr(ratings, value_col="rating")
print(f"MovieLens-{SIZE}: {X.shape}, nnz = {X.nnz:,}, densidad = {X.nnz / np.prod(X.shape):.3%}")

# Memoria de cada formato para datasets reales (cifras oficiales de cada dataset)
datasets = {"ML-100K": (943, 1_682, 100_000), "ML-1M": (6_040, 3_706, 1_000_209),
            "ML-25M": (162_541, 59_047, 25_000_095), "ML-32M": (200_948, 87_585, 32_000_204),
            "Netflix Prize": (480_189, 17_770, 100_480_507)}
mem = pd.DataFrame({n: {"densidad": nnz / (u * i), "denso_GB": 4 * u * i / 1e9,
                        "CSR_GB": (8 * nnz + 4 * (u + 1)) / 1e9} for n, (u, i, nnz) in datasets.items()}).T
fig, ax = plt.subplots(figsize=(9, 3.6))
mem[["denso_GB", "CSR_GB"]].plot.bar(ax=ax, logy=True, color=[COL["test"], COL["train"]], rot=0)
ax.set(ylabel="GB (escala log)", title="Memoria: matriz densa vs CSR (float32)")
for k, d in enumerate(mem.densidad):
    ax.text(k, mem.denso_GB.iloc[k] * 1.3, f"ρ={d:.2%}", ha="center", fontsize=8)
plt.tight_layout(); plt.show()
mem.round(4)
''')

M(r"""
La matriz densa del Netflix Prize ocuparía ~34 GB; en CSR, menos de 1 GB. Y una operación clave en recomendación — la **co-ocurrencia ítem-ítem** $\mathbf{X}^\top\mathbf{X}$ ("cuántos usuarios vieron $i$ y $j$") — es un simple producto disperso:
""")

C(r'''
Xb = (X > 0).astype(np.float32)          # binaria
t0 = time.perf_counter()
co = (Xb.T @ Xb).tocsr()                 # ítem × ítem
print(f"Co-ocurrencia {co.shape} en {time.perf_counter() - t0:.3f} s · nnz = {co.nnz:,}")
idx2item = {j: it for it, j in i2i.items()}
top_item = int(np.asarray(Xb.sum(0)).ravel().argmax())
fila = co[top_item].toarray().ravel(); fila[top_item] = 0
vecinos = [idx2item[j] for j in np.argsort(-fila)[:5]]
print("Más co-vistas con", items.set_index("item_id").title.get(idx2item[top_item]), "→",
      items.set_index("item_id").loc[vecinos, "title"].tolist())
''')

# ---------------------------------------------------------------------------
M(r"""
---
## 3. Long tail: cabeza y cola

La popularidad de los ítems sigue aproximadamente una **ley de potencias**: unos pocos ítems (la **cabeza**, *short head*) concentran la mayoría de interacciones y miles (la **cola**, *long tail*) tienen muy pocas. Dos formas de medirlo:

- **Curva de Lorenz**: % acumulado de interacciones frente a % de ítems (de menos a más popular).
- **Índice de Gini**: $G = \frac{\sum_{k=1}^{n}(2k-n-1)\,x_{(k)}}{n\sum_k x_{(k)}}$ con $x_{(k)}$ ordenadas ascendentemente. $G = 0$: todos igual de populares; $G \to 1$: todo en un ítem.

¿Por qué importa? (1) Los modelos aprenden mucho mejor la cabeza (más datos) → tienden a recomendar más de lo mismo. (2) La cola es donde está el **descubrimiento** y el valor para productores de nicho. (3) Las métricas promediadas sobre interacciones las domina la cabeza.
""")

C(r'''
def gini(x) -> float:
    x = np.sort(np.asarray(x, float)); n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum()))

pop = ratings.item_id.value_counts()
cum = pop.cumsum() / pop.sum()
n_head = int((cum <= 0.5).sum()) + 1                      # ítems que acumulan el 50 % de interacciones
fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
rank = np.arange(1, len(pop) + 1)
axes[0].loglog(rank, pop.values, ".", ms=3, color=COL["train"])
axes[0].axvline(n_head, color=COL["test"], ls="--")
axes[0].text(n_head * 1.15, pop.max() / 2, f"cabeza: {n_head} ítems\n({n_head / len(pop):.0%}) = 50 % de eventos",
             color=COL["test"], fontsize=9)
axes[0].set(title="Popularidad por rango (log-log)", xlabel="rango del ítem", ylabel="nº interacciones")
x = np.sort(pop.values)
axes[1].plot(np.linspace(0, 1, len(x)), np.cumsum(x) / x.sum(), color=COL["val"], label=f"Lorenz (Gini={gini(x):.2f})")
axes[1].plot([0, 1], [0, 1], "--", color=COL["gris"], label="igualdad")
axes[1].set(title="Curva de Lorenz de la popularidad", xlabel="fracción de ítems", ylabel="fracción de interacciones")
axes[1].legend(); plt.tight_layout(); plt.show()
''')

# ---------------------------------------------------------------------------
M(r"""
---
## 4. ⚠️ Los sesgos de los datos de recomendación

Tus datos **no son una muestra aleatoria** de las preferencias de los usuarios. Son el resultado de lo que tu sistema enseñó, de lo que la gente eligió mirar y de dónde lo puso. Los cuatro sesgos clásicos (ver la revisión de Chen et al., 2023, *Bias and Debias in Recommender System*):

| Sesgo | Qué pasa | Consecuencia |
|---|---|---|
| **Selección / MNAR** (*missing not at random*) | Los usuarios valoran lo que eligen ver, y eligen lo que creen que les gustará | Los ratings observados están inflados; "no observado" ≠ "valor medio" |
| **Exposición** | Solo puedes interactuar con lo que se te mostró | "No interactuó" mezcla "no le gusta" con "no lo vio" |
| **Posición** | Lo de arriba recibe más clics *porque está arriba* | El clic mezcla relevancia y posición (módulo 07) |
| **Popularidad** | El modelo sobre-recomienda la cabeza | Menos diversidad; se autorrefuerza (*feedback loop*) |

### 🧪 Simulación 1 — MNAR: lo que observas no es lo que hay
Generamos las preferencias "verdaderas" de todos los usuarios para todas las películas y hacemos que la probabilidad de **observar** un rating crezca con el propio rating (la gente ve y valora lo que le gusta). Marlin & Zemel (2009) lo midieron con usuarios reales de Yahoo! Music pidiéndoles valorar canciones **al azar**: la distribución era muy distinta de la de las valoraciones voluntarias.
""")

C(r'''
n_u, n_i, d = 2000, 500, 8
P, Q = rng.normal(size=(n_u, d)), rng.normal(size=(n_i, d))
verdad = np.clip(np.round(3 + 0.55 * (P @ Q.T) / np.sqrt(d) * 2 + rng.normal(0, 0.5, (n_u, n_i))), 1, 5)
p_obs = np.array([0.005, 0.01, 0.03, 0.08, 0.15])[verdad.astype(int) - 1]   # P(observar | rating)
observado = verdad[rng.random(verdad.shape) < p_obs]

fig, ax = plt.subplots(figsize=(7.5, 3.4))
b = np.arange(1, 6)
ax.bar(b - 0.2, [np.mean(verdad == k) for k in b], 0.4, label="todas las preferencias (verdad)", color=COL["gris"])
ax.bar(b + 0.2, [np.mean(observado == k) for k in b], 0.4, label="ratings observados", color=COL["train"])
ax.set(xlabel="rating", ylabel="proporción", title=f"MNAR: media real {verdad.mean():.2f} vs observada {observado.mean():.2f}")
ax.legend(); plt.tight_layout(); plt.show()
''')

M(r"""
### 🧪 Simulación 2 — Sesgo de posición
Ordenamos ítems **al azar** (la relevancia no depende de la posición) y simulamos clics con un modelo de examen: el usuario mira la posición $k$ con probabilidad $P(E=1\mid k) = 1/k^{\eta}$ y clica si la mira y le interesa — el *position-based model* de los trabajos de LTR insesgado (Joachims et al., 2017).
""")

C(r'''
K, n_sesiones, eta = 10, 50_000, 1.0
relevante = rng.random((n_sesiones, K)) < 0.15            # relevancia independiente de la posición
examina = rng.random((n_sesiones, K)) < 1 / np.arange(1, K + 1) ** eta
clic = relevante & examina
fig, ax = plt.subplots(figsize=(7.5, 3.4))
ax.bar(range(1, K + 1), clic.mean(0), color=COL["val"], label="CTR observado")
ax.plot(range(1, K + 1), relevante.mean(0), "k--", label="relevancia real (constante)")
ax.set(xlabel="posición en la lista", ylabel="tasa", title="Sesgo de posición: mismo contenido, CTR muy distinto")
ax.legend(); plt.tight_layout(); plt.show()
''')

M(r"""
### 🧪 Simulación 3 — El *feedback loop* de la popularidad
Un catálogo de 300 ítems con un "atractivo" real casi plano. Cada ronda recomendamos a cada usuario los 10 ítems con más clics acumulados (más un 2 % de exploración aleatoria), los usuarios clican según el atractivo real, y reentrenamos. Mira cómo se dispara la concentración aunque los ítems sean casi iguales.
""")

C(r'''
def simular_bucle(n_items=300, n_users=500, rondas=30, k=10, explora=0.02, seed=SEED):
    r = np.random.default_rng(seed)
    atractivo = r.uniform(0.04, 0.06, n_items)            # ¡casi todos iguales!
    clics = np.ones(n_items)
    ginis = []
    for _ in range(rondas):
        top = np.argsort(-clics)[:k]
        for _u in range(n_users):
            lista = top.copy()
            mask = r.random(k) < explora
            lista[mask] = r.integers(0, n_items, mask.sum())
            clics[lista] += r.random(k) < atractivo[lista]
        ginis.append(gini(clics))
    return np.array(ginis), clics, atractivo

ginis, clics_fin, atractivo = simular_bucle()
fig, axes = plt.subplots(1, 2, figsize=(12, 3.4))
axes[0].plot(ginis, marker="o", color=COL["test"])
axes[0].set(title="Gini de los clics acumulados por ronda", xlabel="ronda de reentreno", ylabel="Gini")
axes[1].scatter(atractivo, clics_fin, s=8, color=COL["train"])
axes[1].set(title="Atractivo real vs clics al final", xlabel="atractivo real", ylabel="clics acumulados", yscale="log")
plt.tight_layout(); plt.show()
''')

M(r"""
Los ganadores no son los mejores ítems: son los que tuvieron suerte al principio. **Tu log de entrenamiento lleva la firma de tu política anterior.** Las respuestas de la industria: exploración explícita (bandits, módulo 14), corrección por propensión (IPS), datasets con exposición aleatoria (KuaiRand, Coat, Yahoo! R3) y re-ranking por diversidad (módulo 13).
""")

# ---------------------------------------------------------------------------
M(r"""
---
## 5. Construir señales implícitas

En streaming casi no hay ratings; hay **reproducciones**. A partir de un log de *plays* puedes construir varias señales:

| Señal | Definición | Pros / contras |
|---|---|---|
| Play binario | $y_{ui} = 1$ si reprodujo | mucha señal, mucho ruido (autoplay, curiosidad) |
| Completado | $y_{ui} = 1$ si % visto $\geq \tau$ (p. ej. 70 %) | más fiable, más escasa; sesgo hacia contenido corto |
| Tiempo visto | minutos, $\log(1+\text{min})$ | favorece contenido largo (normalizar por duración) |
| Confianza (Hu et al., 2008) | $p_{ui} = \mathbb{1}[r_{ui}>0]$, $c_{ui} = 1 + \alpha \log(1 + r_{ui}/\epsilon)$ | separa **preferencia** de **confianza**; base de ALS implícito (módulo 05) |
| Negativo explícito | impresión sin play, "no me interesa", abandono < 5 % | oro puro si lo logueas |

MovieLens solo tiene ratings, así que **simulamos un log de reproducciones** coherente con ellos (con duraciones y % visto que dependen del rating) para practicar.
""")

C(r'''
def simular_log_plays(ratings: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """Un play por rating, con % visto dependiente del rating, + impresiones sin play."""
    r = np.random.default_rng(seed)
    dur = pd.Series(r.integers(80, 180, ratings.item_id.max() + 1))  # minutos por película
    medias = {1: 0.15, 2: 0.35, 3: 0.65, 4: 0.85, 5: 0.95}
    m = ratings.rating.round().astype(int).map(medias).to_numpy()
    frac = np.clip(r.beta(m * 6, (1 - m) * 6), 0.01, 1.0)
    plays = ratings[["user_id", "item_id", "timestamp"]].assign(
        evento="play", frac_vista=frac, minutos=frac * dur.loc[ratings.item_id].to_numpy(),
        rating=ratings.rating.to_numpy())
    imp = ratings.sample(frac=0.5, random_state=seed)[["user_id", "timestamp"]].copy()
    imp["item_id"] = r.integers(1, ratings.item_id.max() + 1, len(imp))
    imp = imp.assign(evento="impresión", frac_vista=0.0, minutos=0.0, rating=np.nan)
    return pd.concat([plays, imp]).sort_values("timestamp").reset_index(drop=True)

eventos = simular_log_plays(ratings)
plays = eventos[eventos.evento == "play"]
fig, axes = plt.subplots(1, 2, figsize=(12, 3.4))
plays.boxplot(column="frac_vista", by="rating", ax=axes[0], grid=False)
axes[0].set(title="% visto según el rating (log simulado)", xlabel="rating", ylabel="fracción vista"); fig.suptitle("")
alpha_ = 2.0
conf = 1 + alpha_ * np.log1p(plays.minutos / 10)
axes[1].hist(conf, bins=40, color=COL["verde"])
axes[1].set(title=r"Confianza $c_{ui} = 1 + \alpha\log(1 + \mathrm{min}/10)$", xlabel="confianza", ylabel="nº plays")
plt.tight_layout(); plt.show()
eventos.evento.value_counts()
''')

C(r'''
# ¿Qué umbral de "completado" se parece más a "le gustó" (rating >= 4)?
gusta = plays.rating >= 4
for tau in [0.05, 0.3, 0.5, 0.7, 0.9]:
    pos = plays.frac_vista >= tau
    prec = (pos & gusta).sum() / pos.sum()
    rec = (pos & gusta).sum() / gusta.sum()
    print(f"τ = {tau:.2f}: positivos = {pos.mean():5.1%}  precisión vs 'le gustó' = {prec:.2f}  recall = {rec:.2f}")
''')

M(r"""
En el resto del curso usaremos la convención estándar en la literatura para MovieLens: **positivo implícito = rating ≥ 4** (`cd.to_implicit(ratings, threshold=4.0)`). Es la opción más común en papers (aunque otros usan "cualquier rating" como positivo: ¡comprueba siempre qué hace un paper antes de comparar números!).
""")

# ---------------------------------------------------------------------------
M(r"""
---
## 6. Limpieza: duplicados, k-core y outliers

- **Duplicados** (re-visionados, doble clic): decide si agregas (contar, último timestamp) o eliminas. `cd.dedup_interactions`.
- **k-core**: quedarse solo con usuarios con $\geq k_u$ interacciones e ítems con $\geq k_i$. Es **iterativo**: quitar ítems raros puede dejar a un usuario por debajo del umbral, y viceversa.
- **Outliers**: cuentas compartidas, bots, usuarios con miles de eventos por día. En producción se filtran con reglas (eventos/min, sesiones imposibles).
""")

C(r'''
def k_core(df: pd.DataFrame, k_user: int, k_item: int) -> pd.DataFrame:
    while True:
        n0 = len(df)
        df = df[df.item_id.map(df.item_id.value_counts()) >= k_item]
        df = df[df.user_id.map(df.user_id.value_counts()) >= k_user]
        if len(df) == n0:
            return df

positivos = cd.to_implicit(ratings, 4.0)
filas_k = []
for k in [1, 2, 5, 10, 20, 30]:
    f = k_core(positivos, k, k)
    filas_k.append({"k": k, "interacciones": len(f), "usuarios": f.user_id.nunique(), "ítems": f.item_id.nunique(),
                    "densidad": len(f) / max(1, f.user_id.nunique() * f.item_id.nunique())})
tabla_k = pd.DataFrame(filas_k).set_index("k")
assert len(k_core(positivos, 5, 5)) == len(cd.filter_k_core(positivos, 5, 5))   # coincide con el módulo
fig, ax = plt.subplots(figsize=(7.5, 3.4))
(tabla_k[["interacciones", "usuarios", "ítems"]] / tabla_k.loc[1, ["interacciones", "usuarios", "ítems"]]).plot(
    ax=ax, marker="o", title="Lo que sobrevive al k-core (fracción respecto a k=1)")
ax.set(xlabel="k (mínimo por usuario y por ítem)", ylabel="fracción"); plt.tight_layout(); plt.show()
tabla_k
''')

M(r"""
> 🧠 El k-core **sube la densidad y las métricas** (los ítems y usuarios difíciles desaparecen), por eso muchos papers usan 10-core o 20-core. Pero en producción **no puedes** quitar a los usuarios nuevos: un modelo evaluado en 20-core está evaluado sobre un mundo más fácil que el real. Y aplicarlo **antes** de partir en train/test usa información del futuro para decidir quién entra. En CineMatch aplicamos el k-core **solo al train**.
""")

# ---------------------------------------------------------------------------
M(r"""
---
## 7. Splits y *data leakage*

Esta es la sección más importante del módulo. Hay tres familias de split:

| Split | Cómo | Usado en | Problema |
|---|---|---|---|
| **Aleatorio** | cada interacción va a test con prob. $p$ | muchos papers antiguos | mezcla futuro y pasado: entrenas con lo que pasó **después** de lo que predices |
| **Leave-one-out (LOO)** | la **última** interacción de cada usuario a test | NCF, SASRec, BERT4Rec… | el corte es distinto para cada usuario: el train de Ana incluye eventos posteriores al test de Bruno (**leakage entre usuarios**) |
| **Temporal global** | un instante $T$: train $= \{t < T\}$, test $= \{t \geq T\}$ | la industria; papers rigurosos | test con usuarios/ítems nuevos (cold start) → hay que decidir qué hacer con ellos |

El split temporal global es lo único que **reproduce lo que pasa en producción**: entrenas el lunes con todo lo anterior y sirves el martes. Ji, Sun, Zhang & Li (2023, *A Critical Study on Data Leakage in Recommender System Offline Evaluation*) mostraron que el leakage del LOO/aleatorio puede **cambiar qué modelo gana**.
""")

C(r'''
def dibujar_split(ax, df, es_test, titulo, n_users=12):
    us = df.user_id.drop_duplicates().sample(n_users, random_state=1)
    for k, u in enumerate(us):
        d = df[df.user_id == u]
        t = (d.timestamp - df.timestamp.min()) / 86_400
        m = es_test.loc[d.index]
        ax.scatter(t[~m], np.full((~m).sum(), k), s=9, color=COL["train"])
        ax.scatter(t[m], np.full(m.sum(), k), s=14, color=COL["test"])
    ax.set(title=titulo, xlabel="días desde el inicio", yticks=[])

pos = positivos.copy()
es_rand = pd.Series(rng.random(len(pos)) < 0.2, index=pos.index)
rank_fin = pos.sort_values("timestamp").groupby("user_id").cumcount(ascending=False)
es_loo = (rank_fin == 0).reindex(pos.index)
T = pos.timestamp.quantile(0.8)
es_temp = pos.timestamp >= T
fig, axes = plt.subplots(1, 3, figsize=(15, 3.6), sharey=True)
dibujar_split(axes[0], pos, es_rand, "Aleatorio (20 %)")
dibujar_split(axes[1], pos, es_loo, "Leave-one-out (último por usuario)")
dibujar_split(axes[2], pos, es_temp, "Temporal global (último 20 % del tiempo)")
axes[2].axvline((T - pos.timestamp.min()) / 86_400, color="k", ls="--")
axes[0].set_ylabel("usuarios (muestra)")
fig.legend(handles=[plt.Line2D([], [], marker="o", ls="", color=COL["train"], label="train"),
                    plt.Line2D([], [], marker="o", ls="", color=COL["test"], label="test")], loc="upper right")
plt.tight_layout(); plt.show()
''')

C(r'''
# ¿Cuánto "futuro" hay en el train del leave-one-out?
tr_loo, te_loo = cd.leave_one_out_split(positivos)
t_test_mediano = te_loo.timestamp.median()
print(f"LOO: {np.mean(tr_loo.timestamp > t_test_mediano):.1%} de las interacciones de train son POSTERIORES "
      "al instante mediano de test")
print(f"LOO: {np.mean(tr_loo.timestamp > te_loo.timestamp.min()):.1%} de train es posterior al primer evento de test")
tr_t, va_t, te_t = cd.temporal_split(positivos, val_frac=0.1, test_frac=0.1)
print(f"Temporal: max(train) < min(val) ≤ min(test): {tr_t.timestamp.max() < va_t.timestamp.min() <= te_t.timestamp.min()}")
print(f"Temporal: tamaños train/val/test = {len(tr_t):,} / {len(va_t):,} / {len(te_t):,} · "
      f"usuarios en test: {te_t.user_id.nunique()}")
''')

M(r"""
### 🧪 Experimento: el mismo baseline, cuatro "verdades"
Evaluamos **el mismo** recomendador de popularidad con distintos splits, y una versión con *leakage* descarado: calcular la popularidad con **todo** el dataset (incluido el test). Métrica: **Recall@10** (fracción de los ítems de test del usuario que aparecen en su top-10; la formalizamos en el módulo 02).
""")

C(r'''
def recall_at_k(recs: dict, test: pd.DataFrame, k: int = 10) -> float:
    rel = test.groupby("user_id").item_id.agg(set)
    return float(np.mean([len(r & set(recs.get(u, [])[:k])) / len(r) for u, r in rel.items()]))

def eval_popularidad(train, test, fuente_popularidad=None, k=10):
    fuente = train if fuente_popularidad is None else fuente_popularidad
    ranking = fuente.item_id.value_counts().index.to_numpy()
    vistos = train.groupby("user_id").item_id.agg(set)
    recs = {u: [i for i in ranking[: k + len(vistos.get(u, ()))] if i not in vistos.get(u, set())][:k]
            for u in test.user_id.unique()}
    return recall_at_k(recs, test, k)

tr_r, te_r = cd.random_split(positivos, 0.2)
tr_l, te_l = cd.leave_one_out_split(positivos)
tr_g, _, te_g = cd.temporal_split(positivos, val_frac=0.0, test_frac=0.2)
res_split = {
    "Aleatorio": eval_popularidad(tr_r, te_r),
    "Leave-one-out": eval_popularidad(tr_l, te_l),
    "Temporal global": eval_popularidad(tr_g, te_g),
    "Temporal + LEAKAGE\n(popularidad con test)": eval_popularidad(tr_g, te_g, fuente_popularidad=positivos),
}
fig, ax = plt.subplots(figsize=(8.5, 3.4))
ax.bar(list(res_split), list(res_split.values()), color=[COL["gris"], COL["val"], COL["train"], COL["test"]])
ax.set(ylabel="Recall@10", title="Popularidad: mismo modelo, distinta evaluación")
for k, v in enumerate(res_split.values()):
    ax.text(k, v, f"{v:.3f}", ha="center", va="bottom")
plt.tight_layout(); plt.show()
''')

M(r"""
Cada split mide **una tarea distinta** (y con usuarios distintos), así que los números no son comparables entre sí — esa es justo la lección: **un número de evaluación no significa nada sin su protocolo**. Lo que sí es inequívoco es la comparación entre las dos últimas barras (mismo split, mismos usuarios): usar el test para calcular cualquier cosa del modelo (popularidad, normalizaciones, vocabularios, k-core, estadísticas de *features*) le regala información del futuro. Aquí, con un modelo de una sola "feature", el efecto es pequeño; con cientos de *features* agregadas (p. ej. "nº de vistas totales del ítem" calculada sobre la tabla completa, o el CTR histórico del ítem) es exactamente así como un modelo mediocre parece excelente offline y se hunde online.
""")

# ---------------------------------------------------------------------------
M(r"""
---
## 8. Baselines fuertes

Antes de cualquier modelo, **siempre**:

1. **Aleatorio** — el suelo; si no lo bates por mucho, hay un bug.
2. **Popularidad global** — sorprendentemente difícil de batir en un split temporal.
3. **Popularidad reciente** — popularidad en una ventana de $W$ días, o con decaimiento exponencial $w(e) = 0{,}5^{\,\text{edad}(e)/h}$ con vida media $h$. En catálogos con estrenos (streaming, noticias, moda) suele ganar a la global.
4. **Popularidad por segmento** — por país, edad, dispositivo, género favorito… el primer paso de personalización.

Los hiperparámetros ($W$, $h$) se ajustan en **validación** y se reportan en **test**, como cualquier modelo.
""")

C(r'''
train, val, test = cd.temporal_split(positivos, val_frac=0.1, test_frac=0.1)
ventanas = [3, 7, 14, 30, 60, 120, None]
res_w = {}
for w in ventanas:
    recs = cd.recommend_popular(train, val.user_id.unique(), k=10, window_days=w)
    res_w["todo" if w is None else f"{w} d"] = recall_at_k(recs, val, 10)
mejor_w = max(res_w, key=res_w.get)
fig, ax = plt.subplots(figsize=(7.5, 3.2))
ax.plot(list(res_w), list(res_w.values()), marker="o", color=COL["train"])
ax.set(xlabel="ventana de popularidad", ylabel="Recall@10 (validación)",
       title=f"Ajuste de la ventana en validación (mejor: {mejor_w})")
plt.tight_layout(); plt.show()
''')

C(r'''
W_BEST = None if mejor_w == "todo" else int(mejor_w.split()[0])
train_full = pd.concat([train, val])          # para test: reentrenamos con train + val
usuarios_test = test.user_id.unique()

if users is not None:   # segmento = grupo de edad (MovieLens trae demografía)
    seg = pd.cut(users.set_index("user_id").age, [0, 18, 25, 35, 45, 120], labels=False).to_dict()
else:                   # sin demografía: segmento = nivel de actividad del usuario
    seg = pd.qcut(train_full.user_id.value_counts(), 4, labels=False).to_dict()

baselines = {
    "Aleatorio": cd.recommend_random(train_full, usuarios_test, k=10),
    "Popularidad global": cd.recommend_popular(train_full, usuarios_test, k=10),
    f"Popularidad reciente ({mejor_w})": cd.recommend_popular(train_full, usuarios_test, k=10, window_days=W_BEST),
    "Popularidad decaída (h=30 d)": cd.recommend_popular(train_full, usuarios_test, k=10, half_life_days=30),
    "Popularidad por segmento": cd.recommend_popular_by_segment(train_full, usuarios_test, seg, k=10),
}
res_b = pd.Series({n: recall_at_k(r, test, 10) for n, r in baselines.items()}).sort_values()
ax = res_b.plot.barh(figsize=(8, 3.2), color=COL["train"], title="Baselines en test (split temporal global)")
ax.set_xlabel("Recall@10"); plt.tight_layout(); plt.show()
res_b.round(4)
''')

M(r"""
> 🧪 Con datos reales de MovieLens, la popularidad (global o reciente) multiplica por un orden de magnitud al aleatorio. Este es el listón para **todo** lo que construyas a partir del módulo 03.

Todas estas funciones viven en `cinematch_data.py`. El pipeline completo en una sola llamada:
```python
data = cd.prepare_cinematch("100k")   # dict con train / val / test / items / ratings
```
""")

# ---------------------------------------------------------------------------
M(r"""
---
## 9. 📚 Catálogo de datasets del mundo real

| Dataset | Dominio | Escala aprox. | Feedback | Qué lo hace especial | Dónde |
|---|---|---|---|---|---|
| **MovieLens** 100K/1M/25M/32M | películas | 100K – 32M ratings | explícito 1–5 + timestamps (+ tags, géneros) | el estándar; demografía en 100K/1M | <https://grouplens.org/datasets/movielens/> |
| **Netflix Prize** | películas | 100M ratings, 480K usuarios | explícito 1–5 | histórico (2006); retirado oficialmente, circula en Kaggle | <https://www.kaggle.com/datasets/netflix-inc/netflix-prize-data> |
| **Amazon Reviews 2023** | e-commerce | ~571M reseñas, 33 categorías | ratings + texto + metadatos | texto e imágenes ricos; splits oficiales | <https://amazon-reviews-2023.github.io/> |
| **Yelp Open Dataset** | negocios locales | ~7M reseñas | ratings + texto + check-ins | geografía, grafos sociales | <https://www.yelp.com/dataset> |
| **MIND** | noticias | 1M usuarios, 15M impresiones | clics **con impresiones** | negativos reales; cold start extremo | <https://msnews.github.io/> |
| **KuaiRec** | vídeo corto | 1.411 usuarios × 3.327 vídeos **totalmente observada** (submatriz) | watch ratio | permite evaluación sin sesgo de exposición | <https://kuairec.com/> |
| **KuaiRand** | vídeo corto | 12 señales, millones de eventos | multi-señal + **exposición aleatoria** | debiasing, multi-tarea | <https://kuairand.com/> |
| **RetailRocket** | e-commerce | 2,7M eventos | view / add-to-cart / transaction | sesiones, implícito multinivel | <https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset> |
| **Yoochoose** (RecSys Challenge 2015) | e-commerce | 33M clics | clics + compras por sesión | clásico de recomendación por sesión (GRU4Rec) | <https://recsys.acm.org/recsys15/challenge/> |
| **H&M Personalized Fashion** | moda | 31M transacciones | compras + imágenes + metadatos | multimodal, estacionalidad | <https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations> |
| **OTTO** | e-commerce | 12M sesiones, 220M eventos | clicks / carts / orders | multi-objetivo, sesiones largas | <https://github.com/otto-de/recsys-dataset> |
| **Last.fm 1K / 360K** | música | 19M scrobbles (1K) | escuchas implícitas | secuencias de escucha | <http://ocelma.net/MusicRecommendationDataset/> |
| **LFM-2b** | música | 2.000M escuchas | escuchas + demografía | fairness; **retirado** por licencias (CHIIR 2022) | <https://www.cp.jku.at/datasets/LFM-2b/> |
| **Goodbooks-10k** | libros | 6M ratings | explícito 1–5 + "to read" | alternativo a MovieLens | <https://github.com/zygmuntz/goodbooks-10k> |
| **Criteo** (Kaggle DAC / 1TB) | publicidad (CTR) | 45M – 4.000M impresiones | clic sí/no, 13 num. + 26 cat. | estándar de modelos CTR (módulo 06) | <https://ailab.criteo.com/ressources/> |
| **Avazu** | publicidad (CTR) | 40M impresiones | clic sí/no | CTR móvil (módulo 06) | <https://www.kaggle.com/c/avazu-ctr-prediction> |
| **Open Bandit Dataset** (ZOZOTOWN) | moda | 26M impresiones | clic + **propensiones reales** | off-policy evaluation (módulo 14) | <https://research.zozo.com/data.html> |

> ⚠️ Revisa siempre la **licencia** (casi todos son solo para investigación, no comercial) y si el dataset trae **impresiones** (negativos reales) o solo positivos.
""")

# ---------------------------------------------------------------------------
M(r"""
---
## 10. 🧪 Negativos: lo que no viste no es lo que no te gusta

Con feedback implícito solo tienes positivos. Para entrenar (BPR, two-tower, BCE) necesitas **negativos**, y casi siempre se **muestrean** de lo no observado. Pero algunos de esos "negativos" son ítems que el usuario **verá y le gustarán en el futuro** (*falsos negativos*). Midámoslo: muestreamos negativos para los usuarios de train y miramos cuántos aparecen en su test.
""")

C(r'''
def tasa_falsos_negativos(train, test, n_neg=100, modo="uniforme", seed=SEED):
    r = np.random.default_rng(seed)
    catalogo = train.item_id.unique()
    p = None
    if modo == "popularidad":
        cnt = train.item_id.value_counts().reindex(catalogo).to_numpy(float)
        p = cnt ** 0.75 / (cnt ** 0.75).sum()          # como word2vec
    vistos = train.groupby("user_id").item_id.agg(set)
    futuros = test.groupby("user_id").item_id.agg(set)
    fn, total = 0, 0
    for u, fut in futuros.items():
        neg = r.choice(catalogo, size=n_neg, p=p)
        neg = [i for i in neg if i not in vistos.get(u, set())]
        fn += sum(i in fut for i in neg); total += len(neg)
    return fn / total

tasas = {m: tasa_falsos_negativos(tr_t, te_t, modo=m) for m in ["uniforme", "popularidad"]}
ratio_base = te_t.groupby("user_id").size().mean() / tr_t.item_id.nunique()
print({k: f"{v:.3%}" for k, v in tasas.items()}, f"· (referencia: |test_u| / |I| = {ratio_base:.3%})")
pd.Series(tasas).plot.bar(rot=0, color=[COL["train"], COL["val"]], figsize=(6, 3),
                          title="% de negativos muestreados que el usuario consumirá después")
plt.ylabel("tasa de falsos negativos"); plt.tight_layout(); plt.show()
''')

M(r"""
El muestreo por popularidad da negativos **más difíciles** (más informativos) pero con **más falsos negativos**. Es el *trade-off* que reaparecerá en el two-tower (módulo 08: *hard negatives*, corrección logQ) y en las *sampled metrics* (módulo 02).
""")

# ---------------------------------------------------------------------------
M(r"""
---
## 11. 🏭 En producción

- **El log de impresiones es el activo más valioso.** YouTube, Netflix o Meta registran qué se mostró, en qué posición y en qué contexto, no solo lo que se clicó. Sin impresiones no hay negativos fiables, ni corrección de sesgo de posición, ni *off-policy evaluation*.
- **Ventanas de entrenamiento móviles**: en lugar de "todo el histórico", entrenar con los últimos N días, con más peso a lo reciente. Monolith (ByteDance, 2022) lleva esto al extremo con entrenamiento en tiempo real.
- **Point-in-time correctness**: las *features* de cada ejemplo de entrenamiento deben calcularse **con lo que se sabía en ese instante**. Los *feature stores* (Feast, Tecton) existen en buena parte para garantizar esto y evitar el leakage del apartado 7 (módulo 16).
- **Validación de datos en el pipeline**: esquemas y rangos (Pandera / Great Expectations), volumen de eventos por hora, proporción de eventos por tipo… un cambio de logging en el cliente puede romper silenciosamente el modelo (módulo 17).
- **Señales compuestas**: los objetivos de ranking reales son mezclas (clic, play, % visto, like, compartir, retención) — ver MMoE de YouTube (Zhao et al., 2019) en el módulo 07.
""")

M(r"""
## 🧠 Secretos de la élite

1. **El split temporal global es innegociable** para decidir qué modelo va a producción. Ji et al. (2023) muestran que el leakage de los splits aleatorios/LOO cambia el ranking de modelos. Si un paper usa LOO, sus números no son comparables con tu evaluación temporal.
2. **La popularidad reciente es el baseline que más modelos "deep" no consiguen batir** en catálogos con novedades. Ajusta la ventana en validación y ponla siempre en tu tabla.
3. **Toda estadística del pipeline se calcula solo con train**: popularidad, vocabularios de IDs, medias para normalizar, k-core, umbrales. Un `value_counts()` sobre el DataFrame completo es leakage.
4. **El k-core infla las métricas.** Reporta siempre qué filtrado usas; evalúa también en los usuarios con poco historial, que en producción son mayoría.
5. **"Positivo = rating ≥ 4" vs "positivo = cualquier rating"** pueden duplicar o dividir las métricas: muchas discrepancias entre papers vienen solo de aquí.
6. **Los falsos negativos existen**: con muestreo por popularidad, los negativos difíciles a veces son simplemente positivos futuros. Las correcciones (logQ, eliminar negativos accidentales) importan.
7. **Loguea impresiones desde el día 1.** Es imposible reconstruirlas después y son la base de la corrección de sesgos, la exploración y la evaluación off-policy.
""")

M(r"""
## ⚠️ Errores comunes

- Calcular la popularidad (o cualquier *feature*) sobre el dataset completo antes del split.
- Hacer k-core sobre todo el dataset y luego partir.
- Partir aleatoriamente "porque es lo que hace sklearn".
- Olvidar excluir los ítems ya vistos al recomendar (o, al revés, excluirlos cuando el producto permite re-consumo: música, compras recurrentes).
- No tratar a los usuarios/ítems de test que no existen en train (decide: los excluyes, o los sirves con popularidad, y **dilo**).
- Tratar `NaN` de la matriz como 0 en algoritmos explícitos (asumes que todo lo no visto es un 0 estrellas).
- Comparar números de papers con distinto dataset, filtrado, umbral de positivo y split.
""")

M(r"""
---
## 📝 Autoevaluación

**1.** ¿Por qué CSR y no CSC para obtener el historial de un usuario?
<details><summary>Respuesta</summary>CSR guarda las filas (usuarios) contiguas: el historial de u son indices[indptr[u]:indptr[u+1]], acceso O(longitud del historial). CSC es lo mismo por columnas (ítems).</details>

**2.** Un modelo da Recall@10 = 0,35 con split aleatorio y 0,12 con split temporal. ¿Cuál reportas y por qué?
<details><summary>Respuesta</summary>El temporal: reproduce la situación de producción (entrenar con el pasado, predecir el futuro). El aleatorio deja que el modelo use interacciones posteriores a las que predice y puede incluso cambiar qué modelo gana (Ji et al.).</details>

**3.** ¿Qué es MNAR y qué consecuencia tiene para un modelo que predice ratings?
<details><summary>Respuesta</summary>Missing Not At Random: la probabilidad de que un rating se observe depende de su valor (se valora lo que gusta). El modelo entrenado solo en observados sobreestima los ratings de lo no visto y su RMSE en observados no refleja el error real sobre todo el catálogo.</details>

**4.** ¿Por qué el leave-one-out tiene leakage aunque el test de cada usuario sea su última interacción?
<details><summary>Respuesta</summary>Porque el corte es distinto para cada usuario: el train contiene interacciones de otros usuarios posteriores al instante de test, así que el modelo "conoce" tendencias del futuro (p. ej. una película que se hizo popular después).</details>

**5.** ¿Cómo ajustas la ventana de la popularidad reciente sin hacer trampa?
<details><summary>Respuesta</summary>Split temporal en train/val/test; eliges la ventana que maximiza la métrica en val usando solo train; luego recalculas con train+val y reportas una única vez en test.</details>

**6.** Nombra dos datasets con negativos reales (impresiones) y para qué sirven.
<details><summary>Respuesta</summary>MIND (noticias, impresiones con clic/no clic), KuaiRand (exposición aleatoria) y Open Bandit Dataset (con propensiones). Sirven para entrenar con negativos reales, estudiar sesgos y evaluar off-policy.</details>

**7.** ¿Qué *trade-off* hay entre muestrear negativos uniformemente o por popularidad?
<details><summary>Respuesta</summary>Los negativos populares son más difíciles e informativos (el modelo aprende a no recomendar solo lo popular), pero tienen más probabilidad de ser falsos negativos y sesgan las puntuaciones (requieren corrección, p. ej. logQ).</details>
""")

M(r"""
---
## 📚 Referencias

- Harper & Konstan (2015). *The MovieLens Datasets: History and Context*. ACM TiiS. <https://doi.org/10.1145/2827872>
- Hu, Koren & Volinsky (2008). *Collaborative Filtering for Implicit Feedback Datasets*. ICDM. <https://doi.org/10.1109/ICDM.2008.22>
- Marlin & Zemel (2009). *Collaborative Prediction and Ranking with Non-Random Missing Data*. RecSys. <https://doi.org/10.1145/1639714.1639717>
- Joachims, Swaminathan & Schnabel (2017). *Unbiased Learning-to-Rank with Biased Feedback*. WSDM. <https://arxiv.org/abs/1608.04468>
- Chaney, Stewart & Engelhardt (2018). *How Algorithmic Confounding in Recommendation Systems Increases Homogeneity and Decreases Utility*. RecSys. <https://arxiv.org/abs/1710.11214>
- Chen et al. (2023). *Bias and Debias in Recommender System: A Survey and Future Directions*. ACM TOIS. <https://arxiv.org/abs/2010.03240>
- Ji, Sun, Zhang & Li (2023). *A Critical Study on Data Leakage in Recommender System Offline Evaluation*. ACM TOIS. <https://arxiv.org/abs/2010.11060>
- Sun et al. (2020). *Are We Evaluating Rigorously? Benchmarking Recommendation for Reproducible Evaluation and Fair Comparison*. RecSys. <https://doi.org/10.1145/3383313.3412489>
- Wu et al. (2020). *MIND: A Large-scale Dataset for News Recommendation*. ACL. <https://aclanthology.org/2020.acl-main.331/>
- Gao et al. (2022). *KuaiRec: A Fully-observed Dataset and Insights for Evaluating Recommender Systems*. CIKM. <https://arxiv.org/abs/2202.10842>
- Gao et al. (2022). *KuaiRand: An Unbiased Sequential Recommendation Dataset with Randomly Exposed Videos*. CIKM. <https://arxiv.org/abs/2208.08696>
- Hou et al. (2024). *Bridging Language and Items for Retrieval and Recommendation* (Amazon Reviews 2023). <https://arxiv.org/abs/2403.03952>
- Saito, Aihara, Matsutani & Narita (2021). *Open Bandit Dataset and Pipeline: Towards Realistic and Reproducible Off-Policy Evaluation*. NeurIPS Datasets & Benchmarks. <https://arxiv.org/abs/2008.07146>
- Schedl et al. (2022). *LFM-2b: A Dataset of Enriched Music Listening Events for Recommender Systems Research and Fairness Analysis*. CHIIR. <https://doi.org/10.1145/3498366.3505791>
- Liu et al. (2022). *Monolith: Real Time Recommendation System With Collisionless Embedding Table*. <https://arxiv.org/abs/2209.07663>
- SciPy sparse: <https://docs.scipy.org/doc/scipy/reference/sparse.html>
""")

nb.save(LESSON)

# =============================================================================
# PROYECTO
# =============================================================================
pj = Notebook("Proyecto 01 · Pipeline de datos de CineMatch", colab_path=PROJECT)
M, C = pj.md, pj.code

M(rf"""
{pj.badge()}

# 🛠️ Proyecto 01 · El pipeline de datos reproducible de CineMatch

| | |
|---|---|
| **Nivel** | 🟢 Básico |
| **Duración estimada** | 2,5 h |
| **GPU** | No necesaria. ≈ 0 unidades de Colab |
| **Prerrequisitos** | Lección 01 |

## 🎬 Contexto de negocio
La home de popularidad del proyecto 00 ya está en producción. Ahora el equipo va a empezar a entrenar modelos de verdad y la VP de Data te pide **una única fuente de verdad** para todos los experimentos: un pipeline que, dada una configuración, produzca **siempre los mismos** train/val/test, los guarde en parquet con sus metadatos y verifique que no hay leakage. Si dos científicos de datos comparan modelos, deben hacerlo sobre exactamente los mismos datos.

Este pipeline es el que usarán **todos los módulos siguientes del curso** (`cinematch_data.py`).

## 📦 Dataset
**MovieLens-100K** (`SCALE="small"`) o **MovieLens-1M** (`SCALE="full"`) de GroupLens: <https://files.grouplens.org/datasets/movielens/>. Positivo implícito = rating ≥ 4.

## ✅ Entregables y rúbrica
| # | Entregable | Criterio de aceptación |
|---|---|---|
| 1 | `PipelineConfig` | dataclass con todos los parámetros; el `hash` de la config identifica el dataset |
| 2 | `build_dataset(cfg)` | carga → dedup → implícito → split temporal global → k-core **solo en train** → val/test con usuarios e ítems conocidos |
| 3 | Validaciones | `validar(splits)` pasa: sin solapamiento temporal, sin duplicados, sin usuarios/ítems fríos en val/test, tipos correctos |
| 4 | Persistencia | parquet + `metadata.json` (config, tamaños, rangos temporales, sha256 de cada fichero); dos ejecuciones → mismos hashes |
| 5 | Baselines | aleatorio, popularidad, popularidad reciente (ventana ajustada **en val**), por segmento; Recall@10 y NDCG@10 en test. **Popularidad ≥ 5× aleatorio** |
| 6 | Informe de leakage | misma popularidad evaluada con split aleatorio y con popularidad "contaminada" por el test |
| 7 | Módulo | tu pipeline coincide con `cinematch_data.prepare_cinematch` (mismos tamaños) |
""")

C(r'''
!pip install -q pandas pyarrow scipy matplotlib
''')

C(r'''
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SEED = 42
np.random.seed(SEED)
SCALE = "small"     # "small" → 100k · "full" → 1m
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False})
''')

utils_cell(pj, ["cinematch_data.py"])

M(r"""
Del módulo `cinematch_data` usamos solo el **cargador** (`load_movielens`, con fallback sintético si no hay red). El resto lo construyes tú.
""")

C(r'''
from cinematch_data import load_movielens

ratings, items = load_movielens("100k" if SCALE == "small" else "1m")
ratings.head()
''')

M(r"""
---
### TODO 1 — Configuración
Crea una `dataclass` (congelada) con: `size`, `threshold` (4.0), `min_user` (5), `min_item` (5), `val_frac` (0.1), `test_frac` (0.1), `out_dir` (`"data/cinematch"`). Añade un método `hash()` que devuelva los 10 primeros caracteres del sha256 del JSON de la config (sin `out_dir`).
""")

C(r'''
@dataclass(frozen=True)
class PipelineConfig:
    # TODO: campos con sus valores por defecto
    ...

    def hash(self) -> str:
        # TODO
        raise NotImplementedError

cfg = PipelineConfig(size="100k" if SCALE == "small" else "1m")
cfg
''')

M(r"""
### TODO 2 — Las piezas
Implementa (sin mirar `cinematch_data.py`):
- `dedup(df)`: un único evento por (usuario, ítem), el más reciente.
- `k_core(df, min_user, min_item)`: iterativo hasta converger.
- `temporal_split(df, val_frac, test_frac)`: cortes globales por cuantiles de `timestamp`; devuelve `(train, val, test)` con `train < t_val <= val < t_test <= test`.
- `drop_cold(train, other)`: elimina de `other` usuarios o ítems que no estén en `train`.
""")

C(r'''
def dedup(df: pd.DataFrame) -> pd.DataFrame:
    # TODO
    raise NotImplementedError

def k_core(df: pd.DataFrame, min_user: int, min_item: int) -> pd.DataFrame:
    # TODO
    raise NotImplementedError

def temporal_split(df: pd.DataFrame, val_frac: float, test_frac: float):
    # TODO
    raise NotImplementedError

def drop_cold(train: pd.DataFrame, other: pd.DataFrame) -> pd.DataFrame:
    # TODO
    raise NotImplementedError
''')

M(r"""
### TODO 3 — `build_dataset` y `validar`
`build_dataset(cfg, ratings)` encadena: dedup → filtro implícito (rating ≥ threshold) → split temporal → k-core en train → `drop_cold` de val y test. Devuelve un dict `{"train", "val", "test"}`.

`validar(splits)` debe lanzar `AssertionError` con un mensaje claro si algo falla:
1. `train.timestamp.max() < val.timestamp.min()` y `val.timestamp.max() <= test.timestamp.min()`.
2. Ningún par (usuario, ítem) duplicado dentro de un split ni entre splits.
3. Todo usuario e ítem de val/test existe en train.
4. En train todo usuario tiene ≥ `min_user` e ítem ≥ `min_item` interacciones.
5. Columnas `user_id, item_id, rating, timestamp` con tipos enteros/float.
""")

C(r'''
def build_dataset(cfg: PipelineConfig, ratings: pd.DataFrame) -> dict:
    # TODO
    raise NotImplementedError

def validar(splits: dict, cfg: PipelineConfig) -> None:
    # TODO
    raise NotImplementedError

splits = build_dataset(cfg, ratings)
validar(splits, cfg)
{k: v.shape for k, v in splits.items()}
''')

M(r"""
### TODO 4 — Persistencia reproducible
`guardar(splits, cfg)` escribe `train/val/test/items.parquet` en `cfg.out_dir / cfg.hash()` y un `metadata.json` con: la config, nº de filas/usuarios/ítems por split, rango temporal (ISO) por split y el sha256 de cada parquet. Comprueba que **dos ejecuciones** producen los mismos hashes.
""")

C(r'''
def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def guardar(splits: dict, items: pd.DataFrame, cfg: PipelineConfig) -> dict:
    # TODO: devuelve el dict de metadatos
    raise NotImplementedError

meta1 = guardar(splits, items, cfg)
meta2 = guardar(build_dataset(cfg, ratings), items, cfg)
assert meta1["sha256"] == meta2["sha256"], "¡El pipeline no es determinista!"
print(json.dumps(meta1, indent=2, ensure_ascii=False)[:800])
''')

M(r"""
### TODO 5 — Baselines y evaluación
Implementa `recall_at_k` y `ndcg_at_k` (binario; $\text{DCG}=\sum_{p=1}^{K} \frac{\mathbb{1}[\text{rel}]}{\log_2(p+1)}$, normalizado por el ideal) promediados sobre los usuarios de test, y los recomendadores:
- `rec_aleatorio`, `rec_popular(train, users, k, window_days=None)`, `rec_segmento(train, users, segmento_de, k)`.

Protocolo: ajusta `window_days ∈ {7, 14, 30, 60, 90, None}` maximizando Recall@10 en **val** entrenando con train; después **reentrena con train+val** y evalúa todos en **test**. Excluye siempre lo ya visto.
""")

C(r'''
def recall_at_k(recs: dict, test: pd.DataFrame, k: int = 10) -> float:
    # TODO
    raise NotImplementedError

def ndcg_at_k(recs: dict, test: pd.DataFrame, k: int = 10) -> float:
    # TODO
    raise NotImplementedError

def rec_aleatorio(train, users, k=10, seed=SEED) -> dict:
    # TODO
    raise NotImplementedError

def rec_popular(train, users, k=10, window_days=None) -> dict:
    # TODO
    raise NotImplementedError

def rec_segmento(train, users, segmento_de: dict, k=10) -> dict:
    # TODO
    raise NotImplementedError
''')

C(r'''
# TODO: ajuste de ventana en val, tabla final en test (DataFrame: filas = baseline, columnas = Recall@10, NDCG@10)
tabla = ...
tabla
''')

M(r"""
### TODO 6 — Informe de leakage
Evalúa `rec_popular` (sin ventana) en tres escenarios con Recall@10: (a) tu split temporal, (b) un split **aleatorio** 80/20 sobre las mismas interacciones implícitas, (c) split temporal pero con la popularidad calculada sobre **train + test**. Dibuja un gráfico de barras y explica en 3 frases qué ves.
""")

C(r'''
# TODO
''')

M(r"""
---
## ⛔ SPOILER — Solución de referencia

Intenta resolverlo primero.
""")

C(r'''
@dataclass(frozen=True)
class PipelineConfig:
    size: str = "100k"
    threshold: float = 4.0
    min_user: int = 5
    min_item: int = 5
    val_frac: float = 0.1
    test_frac: float = 0.1
    out_dir: str = "data/cinematch"

    def hash(self) -> str:
        d = {k: v for k, v in asdict(self).items() if k != "out_dir"}
        return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:10]

cfg = PipelineConfig(size="100k" if SCALE == "small" else "1m")
print(cfg, "→ hash", cfg.hash())
''')

C(r'''
def dedup(df: pd.DataFrame) -> pd.DataFrame:
    return (df.sort_values("timestamp", kind="stable")
              .drop_duplicates(["user_id", "item_id"], keep="last").reset_index(drop=True))

def k_core(df: pd.DataFrame, min_user: int, min_item: int) -> pd.DataFrame:
    while True:
        n0 = len(df)
        df = df[df.item_id.map(df.item_id.value_counts()) >= min_item]
        df = df[df.user_id.map(df.user_id.value_counts()) >= min_user]
        if len(df) == n0:
            return df.reset_index(drop=True)

def temporal_split(df: pd.DataFrame, val_frac: float, test_frac: float):
    t_test = df.timestamp.quantile(1 - test_frac)
    t_val = df.timestamp.quantile(1 - test_frac - val_frac)
    train = df[df.timestamp < t_val]
    val = df[(df.timestamp >= t_val) & (df.timestamp < t_test)]
    test = df[df.timestamp >= t_test]
    return train.reset_index(drop=True), val.reset_index(drop=True), test.reset_index(drop=True)

def drop_cold(train: pd.DataFrame, other: pd.DataFrame) -> pd.DataFrame:
    ok = other.user_id.isin(train.user_id.unique()) & other.item_id.isin(train.item_id.unique())
    return other[ok].reset_index(drop=True)
''')

C(r'''
def build_dataset(cfg: PipelineConfig, ratings: pd.DataFrame) -> dict:
    inter = dedup(ratings)
    inter = inter[inter.rating >= cfg.threshold]
    train, val, test = temporal_split(inter, cfg.val_frac, cfg.test_frac)
    train = k_core(train, cfg.min_user, cfg.min_item)
    return {"train": train, "val": drop_cold(train, val), "test": drop_cold(train, test)}

def validar(splits: dict, cfg: PipelineConfig) -> None:
    tr, va, te = splits["train"], splits["val"], splits["test"]
    assert tr.timestamp.max() < va.timestamp.min(), "train y val se solapan en el tiempo"
    assert va.timestamp.max() <= te.timestamp.min(), "val y test se solapan en el tiempo"
    todos = pd.concat([tr, va, te])
    assert not todos.duplicated(["user_id", "item_id"]).any(), "pares (usuario, ítem) duplicados"
    for nombre, d in [("val", va), ("test", te)]:
        assert d.user_id.isin(tr.user_id).all(), f"usuarios fríos en {nombre}"
        assert d.item_id.isin(tr.item_id).all(), f"ítems fríos en {nombre}"
    assert tr.user_id.value_counts().min() >= cfg.min_user, "k-core de usuarios no cumplido"
    assert tr.item_id.value_counts().min() >= cfg.min_item, "k-core de ítems no cumplido"
    for d in (tr, va, te):
        assert list(d.columns[:4]) == ["user_id", "item_id", "rating", "timestamp"]
        assert pd.api.types.is_integer_dtype(d.user_id) and pd.api.types.is_integer_dtype(d.timestamp)
    print("✔ validación superada")

splits = build_dataset(cfg, ratings)
validar(splits, cfg)
{k: v.shape for k, v in splits.items()}
''')

C(r'''
def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def guardar(splits: dict, items: pd.DataFrame, cfg: PipelineConfig) -> dict:
    out = Path(cfg.out_dir) / cfg.hash()
    out.mkdir(parents=True, exist_ok=True)
    meta = {"config": asdict(cfg), "hash": cfg.hash(), "splits": {}, "sha256": {}}
    for nombre, d in {**splits, "items": items}.items():
        path = out / f"{nombre}.parquet"
        d.to_parquet(path, index=False)
        meta["sha256"][nombre] = sha256(path)
        if "timestamp" in d:
            meta["splits"][nombre] = {
                "filas": len(d), "usuarios": int(d.user_id.nunique()), "items": int(d.item_id.nunique()),
                "desde": pd.to_datetime(d.timestamp.min(), unit="s").isoformat(),
                "hasta": pd.to_datetime(d.timestamp.max(), unit="s").isoformat()}
    (out / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return meta

meta1 = guardar(splits, items, cfg)
meta2 = guardar(build_dataset(cfg, ratings), items, cfg)
assert meta1["sha256"] == meta2["sha256"], "¡El pipeline no es determinista!"
print(json.dumps(meta1["splits"], indent=2, ensure_ascii=False))
''')

C(r'''
def _rel(test):
    return test.groupby("user_id").item_id.agg(set)

def recall_at_k(recs: dict, test: pd.DataFrame, k: int = 10) -> float:
    return float(np.mean([len(r & set(recs.get(u, [])[:k])) / len(r) for u, r in _rel(test).items()]))

def ndcg_at_k(recs: dict, test: pd.DataFrame, k: int = 10) -> float:
    vals = []
    for u, r in _rel(test).items():
        rec = recs.get(u, [])[:k]
        dcg = sum(1 / np.log2(p + 2) for p, i in enumerate(rec) if i in r)
        idcg = sum(1 / np.log2(p + 2) for p in range(min(k, len(r))))
        vals.append(dcg / idcg)
    return float(np.mean(vals))

def _topk(ranking, vistos, k):
    return [int(i) for i in ranking[: k + len(vistos)] if i not in vistos][:k]

def rec_aleatorio(train, users, k=10, seed=SEED) -> dict:
    r = np.random.default_rng(seed); cat = train.item_id.unique()
    vistos = train.groupby("user_id").item_id.agg(set)
    return {u: _topk(r.permutation(cat), vistos.get(u, set()), k) for u in users}

def rec_popular(train, users, k=10, window_days=None) -> dict:
    d = train if window_days is None else train[train.timestamp >= train.timestamp.max() - window_days * 86_400]
    ranking = np.concatenate([d.item_id.value_counts().index.to_numpy(),
                              train.item_id.value_counts().index.to_numpy()])   # relleno con la global
    ranking = pd.unique(ranking)
    vistos = train.groupby("user_id").item_id.agg(set)
    return {u: _topk(ranking, vistos.get(u, set()), k) for u in users}

def rec_segmento(train, users, segmento_de: dict, k=10) -> dict:
    glob = train.item_id.value_counts().index.to_numpy()
    seg = train.user_id.map(segmento_de)
    rank_seg = {s: pd.unique(np.concatenate([g.item_id.value_counts().index.to_numpy(), glob]))
                for s, g in train.groupby(seg)}
    vistos = train.groupby("user_id").item_id.agg(set)
    return {u: _topk(rank_seg.get(segmento_de.get(u), glob), vistos.get(u, set()), k) for u in users}
''')

C(r'''
from cinematch_data import load_users

tr, va, te = splits["train"], splits["val"], splits["test"]
ventanas = [7, 14, 30, 60, 90, None]
res_val = {w: recall_at_k(rec_popular(tr, va.user_id.unique(), 10, w), va) for w in ventanas}
w_best = max(res_val, key=res_val.get)
print("Recall@10 en val por ventana:", {str(k): round(v, 4) for k, v in res_val.items()}, "→ mejor", w_best)

tr_full = pd.concat([tr, va]); us = te.user_id.unique()
usuarios = load_users(cfg.size)
if usuarios is not None:
    segmento = pd.cut(usuarios.set_index("user_id").age, [0, 18, 25, 35, 45, 120], labels=False).to_dict()
else:
    segmento = pd.qcut(tr_full.user_id.value_counts(), 4, labels=False).to_dict()
recs = {"aleatorio": rec_aleatorio(tr_full, us), "popularidad": rec_popular(tr_full, us),
        f"popularidad reciente ({'todo el histórico' if w_best is None else f'{w_best} d'})":
            rec_popular(tr_full, us, window_days=w_best),
        "popularidad por segmento": rec_segmento(tr_full, us, segmento)}
tabla = pd.DataFrame({n: {"Recall@10": recall_at_k(r, te), "NDCG@10": ndcg_at_k(r, te)} for n, r in recs.items()}).T
assert tabla.loc["popularidad", "Recall@10"] >= 5 * tabla.loc["aleatorio", "Recall@10"], "popularidad < 5× aleatorio"
tabla.round(4)
''')

C(r'''
inter = dedup(ratings); inter = inter[inter.rating >= cfg.threshold]
msk = np.random.default_rng(SEED).random(len(inter)) < 0.2
tr_a, te_a = inter[~msk], drop_cold(inter[~msk], inter[msk])
contaminado = pd.concat([tr, te])
rank_c = contaminado.item_id.value_counts().index.to_numpy()
vistos = tr.groupby("user_id").item_id.agg(set)
recs_c = {u: _topk(rank_c, vistos.get(u, set()), 10) for u in te.user_id.unique()}
leak = {"temporal (correcto)": recall_at_k(rec_popular(tr, te.user_id.unique()), te),
        "aleatorio 80/20": recall_at_k(rec_popular(tr_a, te_a.user_id.unique()), te_a),
        "temporal + popularidad\ncon test (leakage)": recall_at_k(recs_c, te)}
pd.Series(leak).plot.bar(rot=0, color=["#4C72B0", "#9E9E9E", "#C44E52"], figsize=(7, 3.2),
                         title="Popularidad: Recall@10 según el protocolo")
plt.ylabel("Recall@10"); plt.tight_layout(); plt.show()
leak
''')

M(r"""
**Lectura**: usar el test para calcular la popularidad le da al modelo información de lo que se va a ver (el efecto aquí es pequeño porque la "feature" es una sola; con muchas *features* agregadas es enorme). El split aleatorio mide una tarea distinta (rellenar huecos del pasado) con usuarios y distribución distintos, así que su número no es comparable con el temporal — y no dice nada de cómo funcionará el modelo mañana. Moraleja: **el protocolo forma parte del resultado**.

### Empaquetar el pipeline como módulo
La versión canónica del curso es `cinematch_data.py`. La escribimos en disco (celdas `%%writefile`) para que el resto del curso la importe, y comprobamos que **tu pipeline y el canónico producen exactamente los mismos splits**.
""")

writefile_chunks(pj, "cinematch_data.py")

C(r'''
import importlib

import cinematch_data
importlib.reload(cinematch_data)
canon = cinematch_data.prepare_cinematch(cfg.size, cfg.threshold, cfg.min_user, cfg.min_item,
                                         cfg.val_frac, cfg.test_frac)
for k in ["train", "val", "test"]:
    a = splits[k].sort_values(["user_id", "item_id"]).reset_index(drop=True)
    b = canon[k][a.columns].sort_values(["user_id", "item_id"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b, check_dtype=False)
print("✔ tu pipeline == cinematch_data.prepare_cinematch")
''')

M(r"""
---
## 🚀 Retos extra
1. **Escala**: ejecuta con `SCALE="full"` (MovieLens-1M) y luego adapta el cargador a **MovieLens-25M/32M** usando `pyarrow` o **Polars**. Mide tiempo y memoria.
2. **Validación declarativa**: reescribe `validar` con **Pandera** (esquemas + checks) y hazla fallar a propósito con datos corruptos.
3. **Señal implícita realista**: genera un log de plays con `% visto` (como en la lección) y construye un positivo "visto ≥ 70 %". ¿Cuánto cambian los baselines?
4. **Split por ventanas deslizantes** (*rolling origin*): 4 cortes temporales consecutivos; reporta media y desviación de Recall@10. ¿Es estable el ranking de baselines?
5. **Versionado**: registra el dataset como artefacto en **MLflow** o **DVC** usando el `hash` de la config como versión.

## 🤔 Reflexión (producción / MLOps)
- ¿Qué parte de este pipeline correría en *batch* cada noche y cuál debería ser *streaming*?
- Si mañana el equipo de cliente cambia el evento `play` para que se dispare a los 2 segundos en vez de a los 30, ¿qué validación lo detectaría? ¿Cómo afectaría al modelo?
- ¿Cómo garantizarías *point-in-time correctness* si añadieras *features* de usuario (p. ej. "nº de películas vistas en los últimos 7 días")?
""")

pj.save(PROJECT)
