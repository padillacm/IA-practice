"""Builder del módulo 04 · Vecindarios y modelos lineales (item-kNN, user-kNN, RP3beta, SLIM, EASE).

Ejecutar desde la raíz del repo:  python recsys-course/_tools/builders/build_04.py
"""
import sys
from pathlib import Path

sys.path.insert(0, "recsys-course/_tools")
sys.path.insert(0, "recsys-course/_tools/builders")
from nbbuild import Notebook  # noqa: E402
from bloque2_common import add_utils  # noqa: E402

MOD = "recsys-course/04_neighborhood_linear"
Path(MOD).mkdir(parents=True, exist_ok=True)

KNN_CODE = r'''
# Item-kNN desde cero con matrices dispersas
from sklearn.preprocessing import normalize


def prune_topk(S, k: int) -> sp.csr_matrix:
    """Conserva, para cada ítem destino i (columna), sus k vecinos j más similares (filas)."""
    S = S.toarray() if sp.issparse(S) else np.asarray(S)
    k = min(k, S.shape[0] - 1)
    rows = np.argpartition(-S, k, axis=0)[:k]                    # k × n_items
    cols = np.broadcast_to(np.arange(S.shape[1]), rows.shape)
    out = sp.csr_matrix((S[rows, cols].ravel(), (rows.ravel(), cols.ravel())), shape=S.shape)
    out.eliminate_zeros()
    return out


def item_knn(X: sp.csr_matrix, k: int = 100, shrink: float = 0.0, alpha: float = 0.5,
             kind: str = "cosine") -> sp.csr_matrix:
    """S[j, i] = similitud usada para puntuar el ítem i desde el ítem j del historial.
    cosine (asimétrico):  c_ij / (n_i^α · n_j^(1-α) + shrink)    (α=0.5 → coseno clásico)
    jaccard:              c_ij / (n_i + n_j − c_ij + shrink)"""
    Co = (X.T @ X).tocoo()                                       # co-ocurrencias c_ij (dispersa)
    n = np.asarray(X.sum(0)).ravel()                             # n_i = nº de usuarios por ítem
    j, i, c = Co.row, Co.col, Co.data.astype(np.float64)
    if kind == "cosine":
        den = np.power(n[i], alpha) * np.power(n[j], 1 - alpha) + shrink
    elif kind == "jaccard":
        den = n[i] + n[j] - c + shrink
    else:
        raise ValueError(kind)
    S = sp.csr_matrix((c / den, (j, i)), shape=Co.shape)
    S.setdiag(0)
    return prune_topk(S, k)


def sparse_score_fn(X: sp.csr_matrix, S):
    """score(u, ·) = x_u · S   (suma de similitudes con lo que el usuario ya vio)."""
    def score(ub):
        out = X[ub] @ S
        return out.toarray() if sp.issparse(out) else np.asarray(out)
    return score
'''

RP3_CODE = r'''
def rp3beta(X: sp.csr_matrix, alpha: float = 1.0, beta: float = 0.5, k: int = 100) -> sp.csr_matrix:
    """RP3β (Paudel et al., 2017): paseo aleatorio ítem→usuario→ítem de 3 pasos,
    con probabilidades elevadas a α y penalización de popularidad pop_i^β del destino."""
    P_ui = normalize(X, norm="l1")                    # usuario → ítem  (filas suman 1)
    P_iu = normalize(X.T.tocsr(), norm="l1")          # ítem → usuario
    P_ui.data **= alpha; P_iu.data **= alpha
    W = (P_iu @ P_ui).tocsr()                         # W[j, i] = P(j → u → i)
    pop = np.asarray(X.sum(0)).ravel()
    W = W @ sp.diags(1.0 / np.power(np.maximum(pop, 1), beta))
    W.setdiag(0)
    return prune_topk(W.T, k).T.tocsr()                # top-k destinos por ítem ORIGEN (como la implementación de Dacrema et al.)
'''

EASE_CODE = r'''
def ease(X: sp.csr_matrix, lam: float = 500.0) -> np.ndarray:
    """EASE^R (Steck, 2019): B = I − P·diagMat(1/diag(P)),  P = (XᵀX + λI)⁻¹,  diag(B)=0.
    En GPU con torch si está disponible (la inversa de I×I es el único coste)."""
    G = torch.tensor((X.T @ X).toarray(), dtype=torch.float32, device=device)
    G += lam * torch.eye(G.shape[0], device=device)
    P = torch.linalg.inv(G)
    B = -P / torch.diag(P)                            # divide cada columna j por P_jj
    B.fill_diagonal_(0.0)
    return B.cpu().numpy()


def dense_score_fn(X: sp.csr_matrix, B: np.ndarray):
    return lambda ub: np.asarray(X[ub] @ B)
'''

SLIM_CODE = r'''
def slim_admm(X: sp.csr_matrix, l1: float = 1.0, l2: float = 500.0, rho: float = None,
              iters: int = 20) -> np.ndarray:
    """SLIM (Ning & Karypis, 2011) resuelto con ADMM (Steck et al., WSDM 2020):
       min ½‖X − XC‖² + ½λ₂‖C‖² + λ₁‖C‖₁   s.a.  diag(C)=0, C ≥ 0
    Todas las operaciones son densas I×I → vectorizado (y rápido en GPU)."""
    rho = rho or l2
    G = torch.tensor((X.T @ X).toarray(), dtype=torch.float32, device=device)
    n = G.shape[0]; I = torch.eye(n, device=device)
    P = torch.linalg.inv(G + (l2 + rho) * I)
    C = torch.zeros_like(G); Gam = torch.zeros_like(G); res = []
    for _ in range(iters):
        B_t = P @ (G + rho * (C - Gam))
        gamma = torch.diag(B_t) / torch.diag(P)
        B = B_t - P * gamma                           # = B_t − P·diagMat(γ) → diag(B)=0
        C = torch.clamp(B + Gam - l1 / rho, min=0.0)  # soft-threshold + no negatividad
        Gam = Gam + B - C
        res.append(float((B - C).abs().max()))
    return C.cpu().numpy(), res
'''

# ---------------------------------------------------------------------------
# LECCIÓN
# ---------------------------------------------------------------------------
LESSON = f"{MOD}/04_neighborhood_linear.ipynb"
nb = Notebook("Módulo 04 · Vecindarios y modelos lineales", colab_path=LESSON, gpu=True)
nb.md(f"""
{nb.badge()}

# Módulo 04 · Filtrado colaborativo por vecindarios y modelos lineales
### user-kNN, item-kNN (Amazon 2003), RP3β, SLIM y EASE — y por qué siguen ganando

| | |
|---|---|
| **Nivel** | 🟡 Intermedio |
| **Duración estimada** | 3–4 h |
| **GPU recomendada** | T4 (solo acelera EASE/SLIM; todo funciona en CPU) |
| **Unidades de Colab** | ≈ 1 |
| **Prerrequisitos** | [01_data](../01_data), [02_evaluation](../02_evaluation), [03_content_based](../03_content_based) |
""")
nb.md("""
## 🎯 Objetivos de aprendizaje

1. **Explicar** el filtrado colaborativo basado en memoria y la diferencia entre user-kNN e item-kNN.
2. **Calcular** similitudes coseno, coseno asimétrico, Jaccard y Pearson, y **aplicar** *shrinkage*.
3. **Implementar desde cero** item-kNN y user-kNN con `scipy.sparse`, RP3β, SLIM (ADMM) y **EASE** en forma cerrada.
4. **Derivar** la solución cerrada de EASE con multiplicadores de Lagrange.
5. **Comparar** con las implementaciones de `implicit` y `Surprise`.
6. **Medir** el efecto de los hiperparámetros (k, shrinkage, α, β, λ) en NDCG y en **coverage/popularidad**.
7. **Argumentar** con evidencia (Dacrema 2019, Anelli 2022) por qué un baseline lineal bien tuneado es obligatorio.
""")
nb.md("## ⚙️ Setup")
nb.code("""
!pip install -q implicit scikit-surprise pyarrow
""")
nb.code(r'''
import os, random, time, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import torch

warnings.filterwarnings("ignore")
seed = 42
random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
device = "cuda" if torch.cuda.is_available() else "cpu"
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3})
FAST_DEV_RUN = True          # True: rejillas pequeñas y SLIM con pocas iteraciones
print("device:", device)
''')
add_utils(nb)

nb.md("""
## 💡 1. Intuición: «la gente que vio esto también vio…»

En el módulo 03 recomendábamos por **parecido de contenido**. Ahora olvidamos el contenido por
completo: solo miramos **quién vio qué**. Es el **filtrado colaborativo** (*collaborative filtering*, CF).

- **user-kNN**: busca los $k$ usuarios más parecidos a ti y recomienda lo que vieron ellos.
  *«Tus gemelos de gusto vieron X»*.
- **item-kNN**: para cada película que viste, busca las $k$ películas que más se co-consumen con
  ella. *«Porque viste Alien»*. Es el algoritmo que Amazon popularizó en 2003 (Linden, Smith & York).

**Analogía ML**: un kNN de toda la vida, pero las «features» de un ítem son **la columna de la
matriz usuario×ítem** (quién lo consumió). Y un modelo **lineal** como EASE es una regresión que
predice cada columna a partir de las demás.

¿Por qué item-kNN ganó en la industria frente a user-kNN?
1. Hay **menos ítems que usuarios** y las relaciones ítem-ítem son **estables** → se precalculan offline.
2. Es **explicable** («porque viste…»).
3. Un usuario nuevo con 1 interacción ya recibe recomendaciones (sin re-entrenar nada).
""")
nb.code(r'''
# Diagrama: user-kNN vs item-kNN sobre el grafo bipartito usuario–ítem
fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
U = ["Ana", "Beto", "Carla", "Dani"]; I = ["Alien", "Aliens", "Toy Story", "Shrek", "Matrix"]
E = [(0, 0), (0, 1), (0, 4), (1, 0), (1, 1), (1, 4), (2, 2), (2, 3), (3, 0), (3, 4), (3, 2)]
for ax, mode in zip(axes, ["user", "item"]):
    ax.axis("off"); ax.set_xlim(-0.5, 3.5); ax.set_ylim(-0.6, 4.6)
    for u, name in enumerate(U):
        ax.add_patch(mpatches.Circle((0.3, 4 - u * 1.2), 0.28, fc="#cfe8ff", ec="k")); ax.text(0.3, 4 - u * 1.2, name, ha="center", va="center", fontsize=8)
    for i, name in enumerate(I):
        ax.add_patch(mpatches.FancyBboxPatch((2.4, 4.1 - i * 1.0 - 0.2), 0.95, 0.4, boxstyle="round,pad=0.05", fc="#fde2c8", ec="k"))
        ax.text(2.87, 4.1 - i * 1.0, name, ha="center", va="center", fontsize=8)
    for u, i in E:
        hl = (mode == "user" and u in (3, 0, 1)) or (mode == "item" and i in (0, 1, 4) and u in (0, 1, 3))
        ax.plot([0.58, 2.4], [4 - u * 1.2, 4.1 - i * 1.0], color="#d62728" if hl else "grey", lw=2 if hl else 0.8, alpha=0.9 if hl else 0.5)
    ax.set_title("user-kNN: Dani se parece a Ana y Beto → les gustó Aliens" if mode == "user"
                 else "item-kNN: Alien y Matrix se co-consumen con Aliens", fontsize=9.5)
plt.suptitle("Filtrado colaborativo = propagar señal por el grafo usuario–ítem", fontsize=12); plt.show()
''')
nb.md("### 🧪 Ejemplo en papel: 5 usuarios × 6 películas")
nb.code(r'''
toy_items = ["Alien", "Aliens", "Matrix", "Toy Story", "Shrek", "Titanic"]
R_toy = np.array([[5, 4, 5, 0, 0, 1],
                  [4, 5, 4, 0, 1, 0],
                  [0, 0, 1, 5, 4, 0],
                  [1, 0, 0, 4, 5, 3],
                  [5, 0, 4, 0, 0, 0]], dtype=float)       # 0 = no visto. Usuario 4 no ha visto «Aliens»
Xt = (R_toy > 0).astype(float)
co = Xt.T @ Xt                                           # co-ocurrencias
nrm = np.sqrt(np.diag(co))
cos_bin = co / np.outer(nrm, nrm)                         # coseno sobre la matriz binaria
Rc = np.where(R_toy > 0, R_toy - R_toy.sum(1, keepdims=True) / Xt.sum(1, keepdims=True), 0)   # centrado por usuario
cos_adj = (Rc.T @ Rc) / np.outer(np.linalg.norm(Rc, axis=0), np.linalg.norm(Rc, axis=0))     # «coseno ajustado»
fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
for ax, M, t in [(axes[0], cos_bin, "Coseno (binario: ¿lo vio?)"), (axes[1], cos_adj, "Coseno ajustado (ratings centrados)")]:
    im = ax.imshow(M, cmap="RdBu_r", vmin=-1, vmax=1); ax.grid(False)
    ax.set_xticks(range(6), toy_items, rotation=40, ha="right"); ax.set_yticks(range(6), toy_items)
    for a in range(6):
        for b in range(6): ax.text(b, a, f"{M[a, b]:.2f}", ha="center", va="center", fontsize=7.5)
    ax.set_title(t)
plt.colorbar(im, ax=axes, fraction=0.025); plt.show()
s = Xt[4] @ np.where(np.eye(6) == 1, 0, cos_bin)
print("Scores item-kNN del usuario 4:", dict(zip(toy_items, s.round(2))), "→ recomendamos", toy_items[np.argmax(np.where(Xt[4] > 0, -np.inf, s))])
''')
nb.md("""
Observa que el coseno **binario** dice que *Titanic* y *Shrek* se parecen (los vio la misma
persona), mientras que el coseno **ajustado** detecta que a ese usuario *Titanic* le gustó menos
que su media. Con feedback implícito (lo habitual en producción) solo tenemos la versión binaria.
""")

nb.md(r"""
## 📐 2. Teoría formal

Notación: $\mathbf{X}\in\{0,1\}^{|U|\times|I|}$ matriz de interacciones; $\mathbf{x}_{:i}$ columna del
ítem $i$; $n_i=\|\mathbf{x}_{:i}\|_0$ su popularidad; $c_{ij}=\mathbf{x}_{:i}^\top\mathbf{x}_{:j}$ co-ocurrencias.

### 2.1 Similitudes
| Nombre | Fórmula | Comentario |
|---|---|---|
| Coseno | $\dfrac{c_{ij}}{\sqrt{n_i}\sqrt{n_j}}$ | estándar en implícito |
| Coseno asimétrico (Aiolli, 2013) | $\dfrac{c_{ij}}{n_i^{\alpha}\,n_j^{1-\alpha}}$ | $\alpha$ controla cuánto se penaliza la popularidad del destino |
| Jaccard | $\dfrac{c_{ij}}{n_i+n_j-c_{ij}}$ | intersección / unión |
| Pearson / coseno ajustado | $\dfrac{\sum_u (r_{ui}-\bar r_\cdot)(r_{uj}-\bar r_\cdot)}{\sqrt{\cdot}\sqrt{\cdot}}$ | para ratings explícitos (centrado por ítem o por usuario) |

### 2.2 Shrinkage: no te fíes de similitudes con poco soporte
Si dos películas raras las vio **una sola** persona, su coseno es 1. Koren (2008, 2010) propone
encoger hacia 0 según el soporte $n_{ij}$ (nº de usuarios en común):

$$s^{\text{shrunk}}_{ij}=\frac{n_{ij}}{n_{ij}+\lambda}\,s_{ij}$$

En top-N implícito se usa la variante equivalente en el denominador:
$s_{ij}=\dfrac{c_{ij}}{\sqrt{n_i n_j}+h}$ (la que implementamos). Es un **prior bayesiano**: con
pocos datos, la similitud tiende a 0.

### 2.3 Scoring
- **item-kNN**: $\hat s_{ui}=\sum_{j\in I_u\cap N_k(i)} s_{ji}$, con $N_k(i)$ los $k$ vecinos más similares de $i$. Matricial: $\hat{\mathbf S}=\mathbf X\,\mathbf S_k$.
- **user-kNN**: $\hat s_{ui}=\sum_{v\in N_k(u)} s_{uv}\,x_{vi}$. Matricial: $\hat{\mathbf S}=\mathbf S^{U}_k\,\mathbf X$.
- **Ratings explícitos** (con *baselines* $b_{ui}=\mu+b_u+b_i$): $\hat r_{ui}=b_{ui}+\dfrac{\sum_{j\in N_k(i;u)} s_{ij}(r_{uj}-b_{uj})}{\sum_j |s_{ij}|}$ (lo que hace `KNNBaseline` de Surprise).

### 2.4 RP3β (Paudel et al., 2017)
Paseo aleatorio de 3 pasos ítem → usuario → ítem con probabilidades de transición
$P_{ui}=x_{ui}/|I_u|$, $P_{iu}=x_{ui}/n_i$:
$$W_{ji}=\frac{\big(P^{\alpha}_{IU}P^{\alpha}_{UI}\big)_{ji}}{n_i^{\beta}}$$
$\beta>0$ penaliza destinos populares → más diversidad. Sorprendentemente competitivo (Dacrema et al., 2019).

### 2.5 SLIM (Ning & Karypis, 2011)
Aprende directamente la matriz ítem-ítem como una regresión:
$$\min_{\mathbf C}\ \tfrac12\|\mathbf X-\mathbf X\mathbf C\|_F^2+\tfrac{\lambda_2}{2}\|\mathbf C\|_F^2+\lambda_1\|\mathbf C\|_1\quad\text{s.a. } \operatorname{diag}(\mathbf C)=0,\ \mathbf C\ge 0$$
La restricción $\operatorname{diag}=0$ evita la solución trivial $\mathbf C=\mathbf I$ («predice cada ítem con él mismo»).

### 2.6 EASE (Steck, 2019): SLIM sin L1 ni no-negatividad → **solución cerrada**
$$\min_{\mathbf B}\ \|\mathbf X-\mathbf X\mathbf B\|_F^2+\lambda\|\mathbf B\|_F^2\quad\text{s.a. }\operatorname{diag}(\mathbf B)=0$$

**Derivación** (Lagrangiano con multiplicadores $\boldsymbol\gamma\in\mathbb R^{|I|}$):
$$\mathcal L=\|\mathbf X-\mathbf X\mathbf B\|_F^2+\lambda\|\mathbf B\|_F^2+2\boldsymbol\gamma^\top\operatorname{diag}(\mathbf B)$$
1. $\partial\mathcal L/\partial\mathbf B=0 \Rightarrow (\mathbf X^\top\mathbf X+\lambda\mathbf I)\mathbf B=\mathbf X^\top\mathbf X-\operatorname{diagMat}(\boldsymbol\gamma)$.
2. Con $\mathbf P=(\mathbf X^\top\mathbf X+\lambda\mathbf I)^{-1}$ y $\mathbf X^\top\mathbf X=\mathbf P^{-1}-\lambda\mathbf I$: $\ \mathbf B=\mathbf I-\mathbf P\,(\lambda\mathbf I+\operatorname{diagMat}(\boldsymbol\gamma))$.
3. Imponer $B_{jj}=0$: $1-P_{jj}(\lambda+\gamma_j)=0\Rightarrow \lambda+\gamma_j=1/P_{jj}$.
4. Resultado: $\boxed{\ \mathbf B=\mathbf I-\mathbf P\,\operatorname{diagMat}(1/\operatorname{diag}(\mathbf P))\ }\ \Rightarrow\ B_{ij}=-P_{ij}/P_{jj}\ (i\ne j)$.

Un único hiperparámetro ($\lambda$), una inversión de matriz $|I|\times|I|$ ($O(|I|^3)$, independiente del nº de usuarios) y **pesos negativos** permitidos (ver *X* puede *bajar* la puntuación de *Y*): eso es lo que le da su ventaja.

### 2.7 Complejidad
| Método | Entrenamiento | Memoria | Serving |
|---|---|---|---|
| item-kNN | $O(\text{nnz}\cdot\bar n_u)$ (co-ocurrencias) | $O(|I|k)$ | lookup + suma |
| user-kNN | $O(|U|^2)$ | $O(|U|k)$ | caro (usuarios cambian) |
| RP3β | como item-kNN | $O(|I|k)$ | lookup |
| SLIM | $|I|$ regresiones / ADMM $O(|I|^3)$ | disperso | lookup |
| EASE | $O(|I|^3)$ (inversa) | $O(|I|^2)$ **denso** | $\mathbf x_u\mathbf B$ |
""")

nb.md("## 📦 3. Datos, split temporal y baseline")
nb.code(r'''
ratings, movies, users = load_movielens_1m()
train, test = temporal_split(ratings, test_frac=0.2)
enc = Encoder(train)
tr, te = enc.transform(train), enc.transform(test)
X = enc.csr(tr)                    # implícito: «lo valoró» (cualquier rating) = interacción
rel = test_relevance(te)           # relevante en test = rating ≥ 4
titles = movies.set_index("item_id").title.loc[enc.items].values
pop = np.asarray(X.sum(0)).ravel().astype(np.float32)
results = {"Popularidad": evaluate_topk(lambda ub: np.tile(pop, (len(ub), 1)), X, rel)}

# Validación temporal dentro de train (para elegir hiperparámetros sin mirar el test)
tr_in, val = temporal_split(train, test_frac=0.1)
enc_v = Encoder(tr_in); Xv = enc_v.csr(enc_v.transform(tr_in)); relv = test_relevance(enc_v.transform(val))
print(f"X: {X.shape}, nnz={X.nnz:,}, densidad={X.nnz / np.prod(X.shape):.2%} · usuarios test={len(rel)} · val={len(relv)}")
results["Popularidad"]
''')
nb.code(r'''
# ¿Cuánto cuesta la matriz de co-ocurrencias? Distribución del soporte c_ij
Co = (X.T @ X).tocsr(); Co.setdiag(0); Co.eliminate_zeros()
fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
axes[0].hist(np.log10(Co.data), bins=60, color="#4c72b0")
axes[0].set_xlabel("log10(c_ij)  (usuarios en común)"); axes[0].set_ylabel("pares de ítems")
axes[0].set_title(f"Soporte de los pares: densidad de XᵀX = {Co.nnz / Co.shape[0] ** 2:.1%}")
axes[1].loglog(np.sort(pop)[::-1], color="#c44e52"); axes[1].set_xlabel("rango del ítem"); axes[1].set_ylabel("nº usuarios")
axes[1].set_title("Long tail: popularidad de los ítems"); plt.tight_layout(); plt.show()
''')

nb.md("""
## 🔨 4. Implementación desde cero

### 4.1 item-kNN con `scipy.sparse`
Las co-ocurrencias $\\mathbf X^\\top\\mathbf X$ se calculan con un producto disperso. Después normalizamos,
aplicamos shrinkage, ponemos la diagonal a 0 y nos quedamos con los $k$ mejores vecinos de cada ítem.
""")
nb.code(KNN_CODE)
nb.code(r'''
t0 = time.time()
S_cos = item_knn(X, k=100, shrink=0)
print(f"item-kNN entrenado en {time.time() - t0:.1f}s · nnz(S) = {S_cos.nnz:,}")
results["item-kNN (cos, k=100)"] = evaluate_topk(sparse_score_fn(X, S_cos), X, rel)
results["item-kNN (cos, k=100)"]
''')
nb.code(r'''
# Mapa de similitudes entre las 25 películas más populares (sin shrink vs. Jaccard)
top25 = np.argsort(-pop)[:25]
S_full = item_knn(X, k=X.shape[1] - 1, shrink=0).toarray()
S_jac = item_knn(X, k=X.shape[1] - 1, kind="jaccard").toarray()
fig, axes = plt.subplots(1, 2, figsize=(15, 6.5))
for ax, M, t in [(axes[0], S_full, "Coseno"), (axes[1], S_jac, "Jaccard")]:
    sub = M[np.ix_(top25, top25)]
    im = ax.imshow(sub, cmap="viridis"); ax.grid(False)
    ax.set_xticks(range(25), [t_[:18] for t_ in titles[top25]], rotation=90, fontsize=6.5)
    ax.set_yticks(range(25), [t_[:18] for t_ in titles[top25]], fontsize=6.5); ax.set_title(f"{t} entre las 25 más populares")
    plt.colorbar(im, ax=ax, fraction=0.046)
plt.tight_layout(); plt.show()
''')
nb.code(r'''
def neighbours(title_substr: str, S, k: int = 6):
    i = int(np.flatnonzero(pd.Series(titles).str.contains(title_substr, regex=False))[0])
    col = S[:, i].toarray().ravel() if sp.issparse(S) else S[:, i]
    top = np.argsort(-col)[:k]
    return titles[i], [(titles[j][:35], round(float(col[j]), 3)) for j in top]


for q in ["Star Wars: Episode IV", "Toy Story (1995)", "Pulp Fiction"]:
    t, nn = neighbours(q, S_cos)
    print(f"🎬 {t}\n   ", nn)
''')
nb.md("""
### 4.2 El efecto del shrinkage y de α (normalización por popularidad)

Barremos los hiperparámetros **en validación**. Mira las dos métricas a la vez: NDCG y coverage.
""")
nb.code(r'''
shrinks = [0, 10, 50, 200, 1000] if FAST_DEV_RUN else [0, 5, 10, 25, 50, 100, 200, 500, 1000, 2000]
alphas = [0.3, 0.5, 0.7, 0.9] if FAST_DEV_RUN else [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
ks = [20, 50, 100, 300] if FAST_DEV_RUN else [10, 20, 50, 100, 200, 300, 500, 1000]
sweep = {"shrink": {}, "alpha": {}, "k": {}}
for h in shrinks: sweep["shrink"][h] = evaluate_topk(sparse_score_fn(Xv, item_knn(Xv, 100, shrink=h)), Xv, relv)
for a in alphas:  sweep["alpha"][a] = evaluate_topk(sparse_score_fn(Xv, item_knn(Xv, 100, alpha=a)), Xv, relv)
for k in ks:      sweep["k"][k] = evaluate_topk(sparse_score_fn(Xv, item_knn(Xv, k)), Xv, relv)
fig, axes = plt.subplots(1, 3, figsize=(15, 3.8))
for ax, (name, d) in zip(axes, sweep.items()):
    xs = list(d); ax.plot(xs, [d[x]["NDCG@10"] for x in xs], "o-", color="#4c72b0", label="NDCG@10")
    ax2 = ax.twinx(); ax2.plot(xs, [d[x]["Coverage"] for x in xs], "s--", color="#dd8452", label="Coverage"); ax2.grid(False)
    ax.set_xlabel(name); ax.set_ylabel("NDCG@10 (val)", color="#4c72b0"); ax2.set_ylabel("Coverage", color="#dd8452")
    if name in ("shrink", "k"): ax.set_xscale("symlog")
    ax.set_title(f"item-kNN: efecto de {name}")
plt.tight_layout(); plt.show()
''')
nb.md("""
🧪 Dos lecciones que aparecen en casi cualquier dataset:

- **Shrinkage alto y α > 0,5 suben el NDCG pero bajan la coverage**: ambos empujan hacia ítems
  populares (con más soporte). En un split temporal la popularidad «paga», así que el óptimo de NDCG
  está sesgado hacia lo popular. Por eso siempre reportamos coverage al lado.
- **Más vecinos ayuda** hasta saturar: con 3 700 ítems, $k$ de cientos es razonable.
""")
nb.code(r'''
# Combinación elegida en validación (búsqueda conjunta pequeña) → evaluamos UNA vez en test
grid = {}
for h in [0, 200, 1000]:
    for a in [0.5, 0.7]:
        for k in [100, 300]:
            grid[(h, a, k)] = evaluate_topk(sparse_score_fn(Xv, item_knn(Xv, k, shrink=h, alpha=a)), Xv, relv)["NDCG@10"]
h_b, a_b, k_b = max(grid, key=grid.get)
print(f"Mejor en validación: shrink={h_b}, α={a_b}, k={k_b} (NDCG@10 val = {grid[(h_b, a_b, k_b)]:.4f})")
S_best = item_knn(X, k_b, shrink=h_b, alpha=a_b)
results["item-kNN (tuneado)"] = evaluate_topk(sparse_score_fn(X, S_best), X, rel)
results["item-kNN (Jaccard)"] = evaluate_topk(sparse_score_fn(X, item_knn(X, k_b, kind="jaccard")), X, rel)
''')

nb.md("""
### 4.3 user-kNN
Similitud coseno entre filas de $\\mathbf X$; podamos a los $k$ vecinos de cada usuario. Con 5 400
usuarios la matriz $|U|\\times|U|$ cabe en memoria; con 100 M usuarios, no (y por eso la industria
eligió item-kNN).
""")
nb.code(r'''
def user_knn(X: sp.csr_matrix, k: int = 200) -> sp.csr_matrix:
    Xn = normalize(X)
    Su = (Xn @ Xn.T).toarray(); np.fill_diagonal(Su, 0)
    return prune_topk(Su.T, k).T.tocsr()          # fila u: sus k vecinos más similares


Su = user_knn(X, k=200)
results["user-kNN (k=200)"] = evaluate_topk(lambda ub: (Su[ub] @ X).toarray(), X, rel)
results["user-kNN (k=200)"]
''')
nb.md("### 4.4 RP3β: paseos aleatorios con penalización de popularidad")
nb.code(RP3_CODE)
nb.code(r'''
betas = [0.0, 0.2, 0.4, 0.6, 0.8]
rp_val = {b: evaluate_topk(sparse_score_fn(Xv, rp3beta(Xv, 1.0, b, 100)), Xv, relv) for b in betas}
fig, ax = plt.subplots(figsize=(7, 3.6))
ax.plot(betas, [rp_val[b]["NDCG@10"] for b in betas], "o-", label="NDCG@10 (val)")
ax2 = ax.twinx(); ax2.plot(betas, [rp_val[b]["Coverage"] for b in betas], "s--", color="#dd8452", label="Coverage"); ax2.grid(False)
ax.set_xlabel("β (penalización de popularidad)"); ax.set_ylabel("NDCG@10"); ax2.set_ylabel("Coverage", color="#dd8452")
ax.set_title("RP3β: el trade-off precisión ↔ cobertura en un solo parámetro"); plt.show()
beta_b = max(rp_val, key=lambda b: rp_val[b]["NDCG@10"])
results[f"RP3β (β={beta_b})"] = evaluate_topk(sparse_score_fn(X, rp3beta(X, 1.0, beta_b, 100)), X, rel)
''')

nb.md("""
### 4.5 EASE en 6 líneas

Toda la derivación de la sección 2.6 se reduce a una inversa y una división por la diagonal.
""")
nb.code(EASE_CODE)
nb.code(r'''
lams = [300, 1000, 3000, 10000, 30000] if FAST_DEV_RUN else [100, 300, 1000, 2000, 3000, 5000, 10000, 20000, 30000, 50000]
ease_val = {}
for lam in lams:
    t0 = time.time(); B = ease(Xv, lam)
    ease_val[lam] = evaluate_topk(dense_score_fn(Xv, B), Xv, relv) | {"t": time.time() - t0}
lam_b = max(ease_val, key=lambda l: ease_val[l]["NDCG@10"])
fig, ax = plt.subplots(figsize=(7, 3.6))
ax.semilogx(lams, [ease_val[l]["NDCG@10"] for l in lams], "o-")
ax2 = ax.twinx(); ax2.semilogx(lams, [ease_val[l]["Coverage"] for l in lams], "s--", color="#dd8452"); ax2.grid(False)
ax.axvline(lam_b, color="k", ls=":"); ax.set_xlabel("λ"); ax.set_ylabel("NDCG@10 (val)"); ax2.set_ylabel("Coverage", color="#dd8452")
ax.set_title(f"EASE: efecto de la regularización (mejor λ = {lam_b})"); plt.show()
t0 = time.time(); B_ease = ease(X, lam_b)
print(f"EASE con λ={lam_b}: {time.time() - t0:.2f}s en {device}")
results[f"EASE (λ={lam_b})"] = evaluate_topk(dense_score_fn(X, B_ease), X, rel)
results[f"EASE (λ={lam_b})"]
''')
nb.code(r'''
# Anatomía de B: ¡pesos negativos!
fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
offd = B_ease[~np.eye(len(B_ease), dtype=bool)]
axes[0].hist(offd, bins=200, color="#4c72b0", log=True); axes[0].axvline(0, color="k")
axes[0].set_title(f"Pesos de EASE fuera de la diagonal ({(offd < 0).mean():.0%} negativos)"); axes[0].set_xlabel("B_ij")
sub = B_ease[np.ix_(top25, top25)]; v = np.abs(sub).max()
im = axes[1].imshow(sub, cmap="RdBu_r", vmin=-v, vmax=v); axes[1].grid(False)
axes[1].set_xticks(range(25), [t[:16] for t in titles[top25]], rotation=90, fontsize=6.5)
axes[1].set_yticks(range(25), [t[:16] for t in titles[top25]], fontsize=6.5)
axes[1].set_title("B (EASE) entre las 25 más populares: rojo = «suma», azul = «resta»")
plt.colorbar(im, ax=axes[1], fraction=0.046); plt.tight_layout(); plt.show()
''')
nb.md("""
💡 Un peso negativo $B_{ij}<0$ significa: *«haber visto $i$ hace **menos** probable $j$»* (p. ej.
una película y su versión doblada/remasterizada, o dos títulos que compiten por el mismo público).
Ningún kNN con similitudes ≥ 0 puede expresar eso.

### 4.6 SLIM vía ADMM (para ver qué aporta la dispersión)

⚠️ Cada iteración son dos productos $|I|\times|I|$ densos: segundos en GPU, minutos en CPU. Con
`FAST_DEV_RUN=True` hacemos solo 5 iteraciones.
""")
nb.code(SLIM_CODE)
nb.code(r'''
t0 = time.time()
C_slim, res_hist = slim_admm(X, l1=5.0, l2=lam_b, iters=5 if FAST_DEV_RUN else 40)
print(f"SLIM-ADMM: {time.time() - t0:.1f}s · densidad de C = {(C_slim > 0).mean():.2%} (EASE: 100 %)")
results["SLIM (ADMM)"] = evaluate_topk(dense_score_fn(X, C_slim), X, rel)
fig, ax = plt.subplots(figsize=(6, 3.2)); ax.semilogy(res_hist, "o-"); ax.set_xlabel("iteración ADMM")
ax.set_ylabel("‖B − C‖∞"); ax.set_title("Convergencia del ADMM (residuo primal)"); plt.show()
''')

nb.md("""
## 🏭 5. Librerías de industria

### 5.1 `implicit` (Ben Frederickson): item-kNN optimizado en C++/Cython
`implicit.nearest_neighbours` trae `CosineRecommender`, `TFIDFRecommender` y `BM25Recommender`
(BM25 como **pesado de la matriz de interacciones** antes del coseno: reduce el peso de usuarios
que lo ven todo). Comparamos con nuestra implementación.
""")
nb.code(r'''
from implicit.nearest_neighbours import CosineRecommender, BM25Recommender

lib = {}
for name, model in [("implicit Cosine (K=100)", CosineRecommender(K=100)),
                    ("implicit BM25 (K=100)", BM25Recommender(K=100, K1=1.2, B=0.75))]:
    t0 = time.time(); model.fit(X, show_progress=False)
    Sim = model.similarity.tocsr()
    results[name] = evaluate_topk(sparse_score_fn(X, Sim), X, rel); lib[name] = time.time() - t0
    print(f"{name}: {lib[name]:.2f}s · NDCG@10 = {results[name]['NDCG@10']:.4f}")
ids, scores = model.recommend(0, X[0], N=5, filter_already_liked_items=True)
# Nota: en ML-1M el pesado BM25 no ayuda (no hay «usuarios aspiradora» ni bots); en logs de producción suele ser al revés.
print("API de recomendación de implicit para el usuario 0:", titles[ids])
''')
nb.md("""
### 5.2 `Surprise`: kNN para **ratings explícitos** (RMSE) y el shrinkage de Koren

`KNNBaseline` implementa la fórmula de la sección 2.3 con similitud `pearson_baseline`, cuyo
parámetro `shrinkage` es exactamente el $\\lambda$ de Koren. Medimos RMSE en el mismo split temporal.
""")
nb.code(r'''
from surprise import Dataset, Reader, KNNBaseline, BaselineOnly, accuracy

reader = Reader(rating_scale=(1, 5))
tr_s = tr if not FAST_DEV_RUN else tr[tr.iidx.isin(np.argsort(-pop)[:1500])]
trainset = Dataset.load_from_df(tr_s[["user_id", "item_id", "rating"]], reader).build_full_trainset()
testset = list(te[te.item_id.isin(tr_s.item_id) & te.user_id.isin(tr_s.user_id)][["user_id", "item_id", "rating"]].itertuples(index=False, name=None))
rmse = {}
base = BaselineOnly(bsl_options={"method": "als", "n_epochs": 10}, verbose=False).fit(trainset)
rmse["Baseline μ+b_u+b_i"] = accuracy.rmse(base.test(testset), verbose=False)
for shr in [0, 10, 100, 500]:
    algo = KNNBaseline(k=40, sim_options={"name": "pearson_baseline", "user_based": False, "shrinkage": shr}, verbose=False)
    rmse[f"KNNBaseline shrink={shr}"] = accuracy.rmse(algo.fit(trainset).test(testset), verbose=False)
fig, ax = plt.subplots(figsize=(8, 3.4))
pd.Series(rmse).plot.barh(ax=ax, color=["grey"] + ["#55a868"] * 4); ax.set_xlim(min(rmse.values()) - 0.02, max(rmse.values()) + 0.01)
ax.set_xlabel("RMSE (test temporal) ↓"); ax.set_title("Surprise: kNN item-item con baselines y shrinkage"); plt.show()
pd.Series(rmse).round(4)
''')
nb.md("""
💡 Fíjate en el **baseline** $\\mu+b_u+b_i$: ya da un RMSE muy competitivo. En el módulo 05 verás
que los sesgos fueron una de las claves del Netflix Prize.
""")

nb.md("## 🧪 6. Comparativa final y sesgo de popularidad")
nb.code(r'''
def avg_rec_popularity(score_fn, k=10, n_users=500):
    us = np.array(sorted(rel))[:n_users]
    recs = topk_from_scores(score_fn(us), X[us], k)
    return float(np.log10(pop[recs] + 1).mean())


fns = {"Popularidad": lambda ub: np.tile(pop, (len(ub), 1)), "item-kNN (tuneado)": sparse_score_fn(X, S_best),
       "user-kNN (k=200)": lambda ub: (Su[ub] @ X).toarray(), f"EASE (λ={lam_b})": dense_score_fn(X, B_ease),
       "SLIM (ADMM)": dense_score_fn(X, C_slim), f"RP3β (β={beta_b})": sparse_score_fn(X, rp3beta(X, 1.0, beta_b, 100))}
res_df = pd.DataFrame(results).T.drop(columns="n_users").sort_values("NDCG@10")
fig, axes = plt.subplots(1, 2, figsize=(15, 4.6))
res_df["NDCG@10"].plot.barh(ax=axes[0], color=["#c44e52" if "Popularidad" in i else "#4c72b0" for i in res_df.index])
axes[0].set_xlim(res_df["NDCG@10"].min() * 0.9, None); axes[0].set_title("NDCG@10 en test temporal")
for name, f in fns.items():
    axes[1].scatter(avg_rec_popularity(f), results[name]["NDCG@10"], s=80); axes[1].annotate(name, (avg_rec_popularity(f), results[name]["NDCG@10"]), fontsize=8)
axes[1].set_xlabel("log10(popularidad media de lo recomendado)"); axes[1].set_ylabel("NDCG@10")
axes[1].set_title("Precisión vs. sesgo de popularidad"); plt.tight_layout(); plt.show()
res_df.round(4)
''')
nb.md("""
🧪 **Cómo leer esto**: con un split temporal honesto, los métodos lineales/vecindarios bien tuneados
superan a la popularidad en NDCG por poco, pero lo hacen con **2–3× más coverage**. Pequeñas
diferencias de NDCG pueden no ser significativas: en el proyecto calcularás intervalos de confianza
con bootstrap (módulo 02).
""")

nb.md("""
## 🏭 7. En producción

- **Amazon** (Linden, Smith & York, 2003): item-to-item CF sobre co-compras; la tabla de vecinos se
  precalcula offline y el serving es un *lookup* → escala a catálogos de millones. Smith & Linden
  (2017) cuentan dos décadas de evolución del mismo principio.
- **YouTube** (Davidson et al., RecSys 2010): los «vídeos relacionados» se calculaban con
  **co-visitas** en una ventana de 24 h, normalizadas por la popularidad de ambos vídeos — es un
  coseno con normalización por popularidad. Luego expandían el grafo desde los vídeos semilla del usuario.
- **Pinterest Pixie** (Eksombatchai et al., WWW 2018): paseos aleatorios en tiempo real sobre un
  grafo bipartito pin–board de miles de millones de aristas, sesgados por usuario. Es la versión
  industrial de RP3β.
- **Twitter WTF** (Gupta et al., WWW 2013): «Who to Follow» con paseos aleatorios (SALSA) sobre el grafo.
- **Netflix**: filas tipo «Porque viste X» son, conceptualmente, vecinos ítem-ítem. Los métodos de
  vecindario + factores latentes formaron el núcleo del Netflix Prize (Koren, 2008).

**Patrón de serving**: tabla `item_id → [(vecino, peso)] × k` en un KV store (Redis/Cassandra), se
regenera cada noche (o *nearline* con Flink/Kafka). En la petición: tomar los últimos N ítems del
usuario, unir sus listas de vecinos, sumar pesos, filtrar vistos → candidatos en < 5 ms. EASE se sirve
igual si **podas** $\\mathbf B$ a los top-k por columna.
""")
nb.md("""
## 🧠 8. Secretos de la élite

1. **Los modelos lineales siguen ganando a muchos deep.** Dacrema, Cremonesi & Jannach (RecSys 2019)
   reprodujeron 18 algoritmos neuronales de conferencias top: solo 7 se pudieron reproducir y 6 de
   ellos perdían contra item-kNN/user-kNN/RP3β/SLIM bien tuneados. Anelli et al. (UMAP 2022)
   compararon 10 algoritmos en 3 datasets: RP3β y EASE^R estaban entre los mejores, por delante de
   NeuMF o MultVAE. **Nunca publiques ni despliegues un modelo deep sin un EASE/RP3β tuneado al lado.**
2. **EASE es imbatible en catálogos de hasta ~50–100 k ítems**, pero su $\\mathbf B$ es **denso**
   ($|I|^2$ floats: 100 k ítems = 40 GB en float32). Para más ítems: podar $\\mathbf B$, restringir a
   los ítems más populares, o variantes dispersas como SANSA (Spišák et al., RecSys 2023).
3. **El shrinkage y la normalización por popularidad son los hiperparámetros que más mueven las
   métricas**, más que la elección de la similitud. Tunea `shrink`, `α` (o `β` en RP3β) siempre.
4. **BM25/TF-IDF sobre la matriz de interacciones** (lo que hace `BM25Recommender`) baja el peso de
   usuarios «aspiradora» que lo consumen todo; en datos de producción con bots o *heavy users* marca diferencia.
5. **λ de EASE grande ⇒ más popularidad.** Con λ→∞, $\\mathbf B\\propto \\mathbf X^\\top\\mathbf X$ (co-ocurrencias
   crudas) → recomienda lo popular. El λ óptimo en splits temporales suele ser mayor que en splits aleatorios.
6. **Item-kNN es el rey del tiempo real**: añadir una interacción al historial no requiere re-entrenar
   nada; las recomendaciones cambian al instante. Por eso es el motor típico de recomendaciones de sesión.
7. **Desconfía de diferencias de NDCG del 1 %** sin intervalo de confianza: en ML-1M con ~1 000 usuarios
   de test, el ruido es de ese orden.
""")
nb.md("""
## ⚠️ 9. Errores comunes

- **No poner la diagonal a 0**: el ítem se recomienda a sí mismo (o domina el score) y las métricas se desploman.
- **Calcular similitudes con todo el dataset** (incluido test): fuga clásica. La matriz se aprende *solo* con train.
- **Olvidar el shrinkage** con ítems raros: vecinos con coseno 1 basados en un único usuario.
- **Densificar $\\mathbf X^\\top\\mathbf X$ sin pensar**: con 1 M ítems no cabe; usa productos dispersos y poda.
- **Usar user-kNN en producción con millones de usuarios**: la matriz usuario-usuario es inviable y cambia constantemente.
- Comparar con un baseline **sin tunear** (el «baseline de paja»): es la causa nº 1 de falsos avances en papers.
""")
nb.md(r"""
## ✅ 10. Autoevaluación

1. ¿Por qué item-kNN escala mejor que user-kNN en una tienda con 300 M usuarios y 10 M productos?
<details><summary>Respuesta</summary>Porque la matriz ítem-ítem es más pequeña y estable (se precalcula offline y se sirve con un lookup), mientras que la usuario-usuario es enorme y cambia con cada interacción.</details>

2. Escribe la fórmula de EASE y explica el papel de la restricción diag(B)=0.
<details><summary>Respuesta</summary>$\mathbf B=\mathbf I-\mathbf P\,\mathrm{diagMat}(1/\mathrm{diag}(\mathbf P))$ con $\mathbf P=(\mathbf X^\top\mathbf X+\lambda\mathbf I)^{-1}$. La restricción evita la solución trivial B=I (predecir cada ítem con él mismo).</details>

3. ¿Qué hace el shrinkage con un par de ítems con solo 2 usuarios en común?
<details><summary>Respuesta</summary>Multiplica su similitud por 2/(2+λ), acercándola a 0: no nos fiamos de similitudes con poco soporte.</details>

4. ¿Qué efecto tiene aumentar β en RP3β?
<details><summary>Respuesta</summary>Penaliza más a los ítems destino populares: aumenta la coverage y la novedad, y normalmente baja algo la precisión a partir de cierto punto.</details>

5. ¿Por qué EASE puede superar a SLIM aunque SLIM tenga más flexibilidad (L1)?
<details><summary>Respuesta</summary>EASE permite pesos negativos (SLIM los prohíbe) y tiene solución exacta global con un solo hiperparámetro; la no-negatividad y L1 de SLIM limitan lo que puede expresar y su optimización es aproximada.</details>

6. ¿Cuánta memoria necesita B de EASE para 200 000 ítems en float32? ¿Qué harías?
<details><summary>Respuesta</summary>200k² × 4 B = 160 GB. Restringir a los ítems más populares, podar a top-k por columna, o usar una variante dispersa/aproximada (SANSA, factorizaciones de bajo rango).</details>

7. ¿Por qué el λ óptimo de EASE suele ser mayor en un split temporal?
<details><summary>Respuesta</summary>Porque λ grande sesga hacia la popularidad (co-ocurrencias crudas), y en el futuro la popularidad reciente es muy predictiva; además el desplazamiento temporal pide más regularización.</details>
""")
nb.md("""
## 📚 11. Referencias

**Papers**
- Sarwar, Karypis, Konstan & Riedl (2001). *Item-based Collaborative Filtering Recommendation Algorithms*. WWW.
- Linden, Smith & York (2003). *Amazon.com Recommendations: Item-to-Item Collaborative Filtering*. IEEE Internet Computing.
- Smith & Linden (2017). *Two Decades of Recommender Systems at Amazon.com*. IEEE Internet Computing.
- Koren (2008). *Factorization Meets the Neighborhood: a Multifaceted Collaborative Filtering Model*. KDD.
- Koren (2010). *Factor in the Neighbors: Scalable and Accurate Collaborative Filtering*. ACM TKDD.
- Davidson et al. (2010). *The YouTube Video Recommendation System*. RecSys.
- Ning & Karypis (2011). *SLIM: Sparse Linear Methods for Top-N Recommender Systems*. ICDM.
- Aiolli (2013). *Efficient Top-N Recommendation for Very Large Scale Binary Rated Datasets*. RecSys.
- Gupta et al. (2013). *WTF: The Who to Follow Service at Twitter*. WWW.
- Paudel, Christoffel, Newell & Bernstein (2017). *Updatable, Accurate, Diverse, and Scalable Recommendations for Interactive Applications*. ACM TiiS (RP3β).
- Eksombatchai et al. (2018). *Pixie: A System for Recommending 3+ Billion Items to 200+ Million Users in Real-Time*. WWW. [arXiv:1711.07601](https://arxiv.org/abs/1711.07601)
- Steck (2019). *Embarrassingly Shallow Autoencoders for Sparse Data*. WWW. [arXiv:1905.03375](https://arxiv.org/abs/1905.03375)
- Steck, Dimakopoulou, Riabov & Jebara (2020). *ADMM SLIM: Sparse Recommendations for Many Users*. WSDM.
- Dacrema, Cremonesi & Jannach (2019). *Are We Really Making Much Progress? A Worrying Analysis of Recent Neural Recommendation Approaches*. RecSys. [arXiv:1907.06902](https://arxiv.org/abs/1907.06902)
- Anelli, Bellogín, Di Noia, Jannach & Pomo (2022). *Top-N Recommendation Algorithms: A Quest for the State-of-the-Art*. UMAP. [arXiv:2203.01155](https://arxiv.org/abs/2203.01155)
- Spišák, Bartyzal, Hoskovec, Peska & Tůma (2023). *Scalable Approximate NonSymmetric Autoencoder for Collaborative Filtering* (SANSA). RecSys.

**Librerías**: [implicit](https://github.com/benfred/implicit) · [Surprise](https://surpriselib.com) · [RecBole](https://recbole.io) · [Elliot](https://github.com/sisinflab/elliot) · [RecSys2019_DeepLearning_Evaluation](https://github.com/MaurizioFD/RecSys2019_DeepLearning_Evaluation) (implementaciones de referencia de Dacrema et al.)
""")
nb.save(LESSON)

# ---------------------------------------------------------------------------
# PROYECTO
# ---------------------------------------------------------------------------
PROJ = f"{MOD}/04_proyecto_knn_vs_ease.ipynb"
pj = Notebook("Proyecto 04 · item-kNN vs EASE en CineMatch", colab_path=PROJ, gpu=True)
pj.md(f"""
{pj.badge()}

# Proyecto 04 · item-kNN vs EASE para la home de CineMatch
| | |
|---|---|
| **Nivel** | 🟡 Intermedio |
| **Duración** | 3–4 h |
| **GPU** | Opcional (T4 acelera EASE); ≈ 0,5–1 unidad |
| **Prerrequisitos** | Lección 04 y evaluador del módulo 02 |

## 🏢 Contexto de negocio
El equipo de CineMatch tiene en producción un **item-kNN** heredado (coseno, sin tunear) para la
fila «Recomendado para ti». Un *paper* dice que **EASE** es mejor. Tu jefa te pide un informe
riguroso: *¿merece la pena cambiar?* — con métricas de precisión, **cobertura**, **intervalos de
confianza** y coste de memoria/latencia.

## 📦 Dataset
MovieLens 1M, split temporal global 80/20 (utilidades del curso), validación temporal dentro de train.

## 📋 Entregables y rúbrica
| # | Entregable | Criterio |
|---|---|---|
| 1 | `item_knn()` con shrinkage, α y poda top-k | Tests unitarios de la celda pasan |
| 2 | `ease()` en forma cerrada | Diagonal exactamente 0; test de la celda pasa |
| 3 | Tuning **en validación** (grid u Optuna) de ambos | Sin tocar el test hasta el final |
| 4 | Tabla final en test: NDCG@10, Recall@10, Coverage | **EASE ≥ 0,215** y **item-kNN tuneado ≥ 0,205** NDCG@10 (popularidad ≈ 0,214) |
| 5 | **IC 95 % por bootstrap pareado** de ΔNDCG (EASE − kNN) y (EASE − popularidad) | Conclusión explícita: ¿es significativo? |
| 6 | Análisis de coste: memoria de B vs S y latencia por usuario | Extrapolación a 50 k y 500 k ítems |
""")
pj.code("""
!pip install -q pyarrow optuna
""")
pj.code(r'''
import os, random, time, warnings
import numpy as np, pandas as pd, matplotlib.pyplot as plt, torch
warnings.filterwarnings("ignore")
seed = 42; random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
device = "cuda" if torch.cuda.is_available() else "cpu"
FAST_DEV_RUN = True
''')
add_utils(pj)
pj.code(r'''
ratings, movies, users = load_movielens_1m()
train, test = temporal_split(ratings)
enc = Encoder(train); X = enc.csr(enc.transform(train)); rel = test_relevance(enc.transform(test))
tr_in, val = temporal_split(train, test_frac=0.1)
enc_v = Encoder(tr_in); Xv = enc_v.csr(enc_v.transform(tr_in)); relv = test_relevance(enc_v.transform(val))
pop = np.asarray(X.sum(0)).ravel().astype(np.float32)
print(X.shape, len(rel), "usuarios test ·", len(relv), "usuarios val")
''')
pj.md("""
## Paso 1 · item-kNN  ✏️ TODO
Implementa `item_knn(X, k, shrink, alpha)` que devuelva una matriz dispersa `S` (ítems × ítems) con
`S[j, i]` = similitud coseno asimétrica con shrinkage, diagonal 0 y solo los `k` mayores valores de
cada **columna**. 💡 Pistas: `X.T @ X` disperso → `.tocoo()`; `np.argpartition` por columnas.
""")
pj.code(r'''
from sklearn.preprocessing import normalize


def item_knn(X: sp.csr_matrix, k: int = 100, shrink: float = 0.0, alpha: float = 0.5) -> sp.csr_matrix:
    # TODO
    raise NotImplementedError


def ease(X: sp.csr_matrix, lam: float = 500.0) -> np.ndarray:
    # TODO: B = I − P · diagMat(1/diag(P)),  P = (XᵀX + λI)⁻¹
    raise NotImplementedError
''')
pj.code(r'''
# Tests unitarios (ejecútalos tras implementar)
def run_tests():
    Xt = sp.csr_matrix(np.array([[1, 1, 0], [1, 1, 1], [0, 1, 1], [1, 0, 0]], dtype=np.float32))
    S = item_knn(Xt, k=2, shrink=0, alpha=0.5).toarray()
    assert np.allclose(np.diag(S), 0), "la diagonal debe ser 0"
    assert np.isclose(S[0, 1], 2 / np.sqrt(3 * 3)), f"coseno(0,1) esperado 0.667, obtenido {S[0, 1]:.3f}"
    assert (S > 0).sum(0).max() <= 2, "máximo k vecinos por columna"
    B = ease(Xt, lam=1.0)
    assert np.allclose(np.diag(B), 0), "diag(B) debe ser 0"
    G = (Xt.T @ Xt).toarray(); Bref = np.linalg.inv(G + np.eye(3)); Bref = -Bref / np.diag(Bref); np.fill_diagonal(Bref, 0)
    assert np.allclose(B, Bref, atol=1e-4), "EASE no coincide con la referencia"
    print("✅ tests OK")
''')
pj.md("""
## Paso 2 · Tuning en validación  ✏️ TODO
Usa Optuna (o un grid) para `k ∈ [20, 1000]`, `shrink ∈ [0, 2000]`, `alpha ∈ [0.3, 1.0]` del kNN y
`λ ∈ [50, 50 000]` (log) de EASE, maximizando NDCG@10 en `(Xv, relv)`. Guarda el historial y dibuja
NDCG vs cada hiperparámetro.
""")
pj.code(r'''
# TODO: tuning
''')
pj.md("""
## Paso 3 · Evaluación final + bootstrap  ✏️ TODO
Re-entrena con `X` (todo train) usando los mejores hiperparámetros y evalúa **una vez** en test.
Para el bootstrap necesitas NDCG **por usuario**: usa `topk_from_scores` + `ndcg_recall_at_k`.
Remuestrea usuarios con reemplazo (B = 2 000) y calcula el percentil 2,5–97,5 de la diferencia.
""")
pj.code(r'''
# TODO: evaluación final, bootstrap pareado y tabla
''')
pj.md("""
## Paso 4 · Coste  ✏️ TODO
Mide memoria (`S.data.nbytes + …` vs `B.nbytes`) y latencia media de `score_fn` por usuario. Extrapola
la memoria a 50 k y 500 k ítems (EASE: $|I|^2\\cdot 4$ bytes; kNN: $|I|\\cdot k\\cdot 8$ bytes aprox.).
""")
pj.code(r'''
# TODO: análisis de coste
''')
pj.md("""
---
# ⛔ SPOILER — intenta resolverlo primero
Solución de referencia completa.
""")
pj.code(r'''
def prune_topk(S, k):
    S = S.toarray() if sp.issparse(S) else np.asarray(S)
    k = min(k, S.shape[0] - 1)
    rows = np.argpartition(-S, k, axis=0)[:k]
    cols = np.broadcast_to(np.arange(S.shape[1]), rows.shape)
    out = sp.csr_matrix((S[rows, cols].ravel(), (rows.ravel(), cols.ravel())), shape=S.shape)
    out.eliminate_zeros()
    return out


def item_knn(X, k=100, shrink=0.0, alpha=0.5):
    Co = (X.T @ X).tocoo(); n = np.asarray(X.sum(0)).ravel()
    j, i, c = Co.row, Co.col, Co.data.astype(np.float64)
    S = sp.csr_matrix((c / (n[i] ** alpha * n[j] ** (1 - alpha) + shrink), (j, i)), shape=Co.shape)
    S.setdiag(0)
    return prune_topk(S, k)


def ease(X, lam=500.0):
    G = torch.tensor((X.T @ X).toarray(), dtype=torch.float32, device=device)
    P = torch.linalg.inv(G + lam * torch.eye(G.shape[0], device=device))
    B = -P / torch.diag(P); B.fill_diagonal_(0.0)
    return B.cpu().numpy()


knn_fn = lambda Xm, S: (lambda ub: (Xm[ub] @ S).toarray())
ease_fn = lambda Xm, B: (lambda ub: np.asarray(Xm[ub] @ B))
run_tests()
''')
pj.code(r'''
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)
n_trials = 15 if FAST_DEV_RUN else 60


def obj_knn(trial):
    k = trial.suggest_int("k", 20, 1000, log=True)
    shrink = trial.suggest_float("shrink", 0.0, 2000.0)
    alpha = trial.suggest_float("alpha", 0.3, 1.0)
    return evaluate_topk(knn_fn(Xv, item_knn(Xv, k, shrink, alpha)), Xv, relv)["NDCG@10"]


def obj_ease(trial):
    lam = trial.suggest_float("lam", 50.0, 50000.0, log=True)
    return evaluate_topk(ease_fn(Xv, ease(Xv, lam)), Xv, relv)["NDCG@10"]


st_knn = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=seed))
st_knn.enqueue_trial({"k": 100, "shrink": 0.0, "alpha": 0.5})          # el kNN «heredado» de producción
st_knn.optimize(obj_knn, n_trials=n_trials)
st_ease = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=seed))
st_ease.optimize(obj_ease, n_trials=max(8, n_trials // 2))
print("kNN :", st_knn.best_params, round(st_knn.best_value, 4))
print("EASE:", st_ease.best_params, round(st_ease.best_value, 4))
''')
pj.code(r'''
dk = st_knn.trials_dataframe(); de = st_ease.trials_dataframe()
fig, axes = plt.subplots(1, 4, figsize=(17, 3.5))
for ax, col in zip(axes[:3], ["params_k", "params_shrink", "params_alpha"]):
    ax.scatter(dk[col], dk.value, c=dk.number, cmap="viridis"); ax.set_xlabel(col.replace("params_", "")); ax.set_ylabel("NDCG@10 val")
axes[0].set_xscale("log"); axes[3].scatter(de.params_lam, de.value, color="#c44e52"); axes[3].set_xscale("log"); axes[3].set_xlabel("λ (EASE)")
plt.suptitle("Tuning en validación (color = nº de trial)"); plt.tight_layout(); plt.show()
''')
pj.code(r'''
def per_user_ndcg(score_fn, Xm, relevance, k=10, batch=512):
    us = np.array(sorted(relevance)); out = []
    for s in range(0, len(us), batch):
        ub = us[s:s + batch]; out.append(topk_from_scores(score_fn(ub), Xm[ub], k))
    nd, _ = ndcg_recall_at_k(np.vstack(out), [relevance[u] for u in us], k)
    return nd


bp_k, bp_e = st_knn.best_params, st_ease.best_params
S_legacy = item_knn(X, 100, 0.0, 0.5)
S_best = item_knn(X, bp_k["k"], bp_k["shrink"], bp_k["alpha"])
B_best = ease(X, bp_e["lam"])
models = {"Popularidad": lambda ub: np.tile(pop, (len(ub), 1)), "item-kNN heredado": knn_fn(X, S_legacy),
          "item-kNN tuneado": knn_fn(X, S_best), "EASE tuneado": ease_fn(X, B_best)}
final = pd.DataFrame({m: evaluate_topk(f, X, rel) for m, f in models.items()}).T.drop(columns="n_users")
per_user = {m: per_user_ndcg(f, X, rel) for m, f in models.items()}
final.round(4)
''')
pj.code(r'''
rng = np.random.default_rng(seed)
n = len(next(iter(per_user.values()))); B_boot = 2000
idx = rng.integers(0, n, size=(B_boot, n))
cis = {}
for a, b in [("EASE tuneado", "item-kNN tuneado"), ("EASE tuneado", "Popularidad"), ("item-kNN tuneado", "item-kNN heredado")]:
    d = per_user[a] - per_user[b]
    boots = d[idx].mean(1)
    cis[f"{a} − {b}"] = (d.mean(), *np.percentile(boots, [2.5, 97.5]))
ci_df = pd.DataFrame(cis, index=["ΔNDCG@10", "IC 2,5 %", "IC 97,5 %"]).T
ci_df["¿significativo?"] = (ci_df["IC 2,5 %"] > 0) | (ci_df["IC 97,5 %"] < 0)
fig, ax = plt.subplots(figsize=(8, 2.8))
ax.errorbar(ci_df["ΔNDCG@10"], range(len(ci_df)), xerr=[ci_df["ΔNDCG@10"] - ci_df["IC 2,5 %"], ci_df["IC 97,5 %"] - ci_df["ΔNDCG@10"]], fmt="o", capsize=5)
ax.axvline(0, color="k", ls="--"); ax.set_yticks(range(len(ci_df)), ci_df.index); ax.set_xlabel("ΔNDCG@10 (IC 95 % bootstrap pareado)")
plt.tight_layout(); plt.show()
ci_df.round(4)
''')
pj.code(r'''
def latency_ms(f, n_users=256):
    ub = np.array(sorted(rel))[:n_users]; t0 = time.time(); f(ub)
    return (time.time() - t0) / n_users * 1000


mem = {"item-kNN tuneado": S_best.data.nbytes + S_best.indices.nbytes + S_best.indptr.nbytes, "EASE tuneado": B_best.nbytes}
cost = pd.DataFrame({"memoria (MB)": {m: v / 1e6 for m, v in mem.items()},
                     "latencia (ms/usuario, batch)": {m: latency_ms(models[m]) for m in mem}})
k_b = bp_k["k"]
for n_items in [50_000, 500_000]:
    cost.loc["item-kNN tuneado", f"memoria @ {n_items // 1000}k ítems (GB)"] = n_items * k_b * 8 / 1e9
    cost.loc["EASE tuneado", f"memoria @ {n_items // 1000}k ítems (GB)"] = n_items ** 2 * 4 / 1e9
cost.round(3)
''')
pj.md("""
### 📝 Informe (solución de referencia)

- En el split temporal, **EASE tuneado y el item-kNN tuneado quedan muy cerca** y ambos rozan o superan
  ligeramente a la popularidad en NDCG@10, con **mucha más coverage**. Revisa la tabla de IC: si el
  intervalo de una diferencia contiene 0, **no** puedes afirmar que un modelo es mejor.
- **Tunear el kNN heredado** suele dar más mejora que cambiar de algoritmo (lección clásica de Dacrema et al.).
- **Coste**: con 3,7 k ítems EASE ocupa ~50 MB y es trivial; a 500 k ítems necesitaría ~1 TB → inviable
  sin poda/aproximación. El kNN escala linealmente en el nº de ítems.
- **Recomendación**: desplegar el kNN tuneado ya (riesgo bajo) y llevar EASE a un **A/B test**
  (módulo 15) solo si el IC frente al kNN tuneado es positivo.

## 🚀 Retos extra
1. Añade **RP3β** y un **ensemble** lineal EASE + kNN (pesos en validación). ¿Gana a ambos con IC > 0?
2. Implementa EASE con **poda** de B a top-k por columna: ¿cuánto NDCG pierdes con k = 100?
3. Repite todo con un split **por usuario** (leave-last-20 %) y compara conclusiones: ¿cambia el ganador?
4. Prueba `BM25Recommender` de `implicit` (pesado BM25 de X) y explica por qué ayuda o no.

## 🤔 Reflexión (producción / MLOps)
- ¿Cada cuánto re-entrenarías EASE? ¿Y el kNN? ¿Qué cambia si quieres reaccionar a la última película vista?
- ¿Qué *guardrails* pondrías en el A/B (coverage, % de estrenos, popularidad media)?
- ¿Cómo registrarías en MLflow los hiperparámetros, la matriz (artefacto) y las métricas con IC?
""")
pj.save(PROJ)

Path(f"{MOD}/README.md").write_text("""# 04 · Vecindarios y modelos lineales

🟡 · 3–4 h (lección) + 3–4 h (proyecto) · GPU opcional (T4 acelera EASE/SLIM, ≈ 1 unidad)

Filtrado colaborativo **basado en memoria** y **modelos lineales ítem-ítem**: los baselines que todo
modelo deep debe batir — y que muchas veces no bate.

## Contenido
| Notebook | Qué hay dentro |
|---|---|
| [`04_neighborhood_linear.ipynb`](04_neighborhood_linear.ipynb) | user-kNN e item-kNN desde cero con `scipy.sparse` · coseno, coseno asimétrico, Jaccard, coseno ajustado · shrinkage · RP3β · SLIM (ADMM) · **EASE** con derivación · `implicit` (Cosine/BM25) · `Surprise` (KNNBaseline, RMSE) · sesgo de popularidad |
| [`04_proyecto_knn_vs_ease.ipynb`](04_proyecto_knn_vs_ease.ipynb) | Informe «¿cambiamos a EASE?»: tuning con Optuna en validación, IC por bootstrap pareado, coste de memoria/latencia |

## Objetivos
- Implementar y tunear item-kNN, user-kNN, RP3β, SLIM y EASE.
- Entender shrinkage y normalización por popularidad como palancas precisión ↔ cobertura.
- Evaluar con rigor (split temporal, validación, IC) y razonar costes de producción.

## Datasets
- **MovieLens 1M** (GroupLens; espejo en GitHub como fallback). Implícito = cualquier rating; relevante en test = rating ≥ 4.

## Lecturas clave
- Linden, Smith & York (2003), *Amazon.com Recommendations: Item-to-Item CF*.
- Steck (2019), *Embarrassingly Shallow Autoencoders for Sparse Data* (EASE).
- Dacrema, Cremonesi & Jannach (2019), *Are We Really Making Much Progress?*
- Anelli et al. (2022), *Top-N Recommendation Algorithms: A Quest for the State-of-the-Art*.

## Conexión con CineMatch
Fila «Recomendado para ti» v1 y fuente de candidatos en tiempo real («Porque viste…»). En 05 lo
compararemos con factorización matricial (iALS/BPR).

Generado con `python recsys-course/_tools/builders/build_04.py`.
""", encoding="utf-8")
print("README OK")
