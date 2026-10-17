"""Construye los notebooks del módulo 10_graph.

Ejecutar desde la raíz del repo:  python recsys-course/_tools/builders/build_10.py
"""
import os
import sys

sys.path.insert(0, "recsys-course/_tools")
sys.path.insert(0, "recsys-course/_tools/builders")
from nbbuild import Notebook  # noqa: E402
from _b4_common import UTILS_MD, UTILS_LOAD, UTILS_TOPK  # noqa: E402

MOD = "recsys-course/10_graph"
LESSON = f"{MOD}/10_graph.ipynb"
PROJECT = f"{MOD}/10_proyecto_lightgcn_vs_mf.ipynb"
os.makedirs(MOD, exist_ok=True)

PIP = r"""
# PyTorch Geometric (sin extensiones compiladas: LightGCN sólo necesita el paquete base) + gensim + networkx
!pip install -q torch_geometric gensim networkx
"""

IMPORTS = r"""
import math, time, random, collections
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import seaborn as sns
import torch, torch.nn as nn, torch.nn.functional as F

seed = 42
random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
device = "cuda" if torch.cuda.is_available() else "cpu"
FAST_DEV_RUN = False          # True = pocas épocas para iterar; False = experimento completo en GPU
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3})
print("device:", device, "| torch", torch.__version__)
"""

LOAD = r"""
ratings, movies = load_movielens_1m()
# Feedback implícito: toda valoración es una interacción positiva (protocolo habitual de LightGCN/NGCF)
users_u = np.sort(ratings.user.unique()); items_u = np.sort(ratings.item.unique())
u2i = {u: k for k, u in enumerate(users_u)}; it2i = {it: k for k, it in enumerate(items_u)}
df = pd.DataFrame({"u": ratings.user.map(u2i), "i": ratings.item.map(it2i), "ts": ratings.ts})
n_users, n_items = len(users_u), len(items_u)
train_df, test_df = temporal_user_split(df, test_frac=0.2)
test_df = test_df[test_df.i.isin(set(train_df.i))]                 # ítems nunca vistos en train no son predecibles
R_train, R_test = to_csr(train_df, n_users, n_items), to_csr(test_df, n_users, n_items)
title = dict(zip(movies.item.map(it2i), movies.title)); genre = dict(zip(movies.item.map(it2i), movies.genres.str.split("|").str[0]))
print(f"usuarios={n_users:,} ítems={n_items:,} train={R_train.nnz:,} test={R_test.nnz:,} densidad={R_train.nnz/(n_users*n_items):.3%}")
"""

DRAW = r"""
def box(ax, x, y, w, h, text, fc="#dbeafe", ec="#1e3a8a", fs=9, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, weight=weight)

def arrow(ax, x1, y1, x2, y2, color="#334155", lw=1.2, style="-|>"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle=style, color=color, lw=lw))
"""

LIGHTGCN = r"""
def build_norm_adj(R, device=device):
    '''Â = D^{-1/2} A D^{-1/2} con A = [[0, R], [R^T, 0]] como tensor disperso (n_users+n_items)^2.'''
    nu, ni = R.shape
    coo = R.tocoo()
    rows = np.concatenate([coo.row, coo.col + nu]); cols = np.concatenate([coo.col + nu, coo.row])
    deg = np.bincount(rows, minlength=nu + ni).astype(np.float32)
    vals = 1.0 / np.sqrt(deg[rows] * deg[cols])
    idx = torch.from_numpy(np.vstack([rows, cols])).long()
    return torch.sparse_coo_tensor(idx, torch.from_numpy(vals), (nu + ni, nu + ni)).coalesce().to(device)


class LightGCN(nn.Module):
    '''LightGCN (He et al., SIGIR 2020): sólo propagación lineal + media de capas. n_layers=0 => MF.'''
    def __init__(self, n_users, n_items, adj, d=64, n_layers=3):
        super().__init__()
        self.nu, self.ni, self.adj, self.K = n_users, n_items, adj, n_layers
        self.emb = nn.Embedding(n_users + n_items, d)
        nn.init.normal_(self.emb.weight, std=0.1)

    def propagate(self):
        E = self.emb.weight
        layers = [E]
        for _ in range(self.K):
            E = torch.sparse.mm(self.adj, E)          # E^{(k+1)} = Â E^{(k)}
            layers.append(E)
        out = torch.stack(layers).mean(0)              # α_k = 1/(K+1)
        return out[: self.nu], out[self.nu:]

    def bpr_loss(self, u, i, j, reg=1e-4):
        U, I = self.propagate()
        pos, neg = (U[u] * I[i]).sum(-1), (U[u] * I[j]).sum(-1)
        ego = self.emb.weight
        l2 = (ego[u].pow(2).sum() + ego[self.nu + i].pow(2).sum() + ego[self.nu + j].pow(2).sum()) / len(u)
        return -F.logsigmoid(pos - neg).mean() + reg * l2 / 2
"""

TRAIN = r"""
def train_bpr(model, R_train, R_test, epochs=50, batch_size=8192, lr=2e-3, reg=1e-4, eval_every=10, name="modelo", k=20):
    '''Entrena con BPR (un negativo uniforme por positivo). Devuelve historial de Recall@k/NDCG@k.'''
    model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    coo = R_train.tocoo()
    U_all, I_all = torch.from_numpy(coo.row).long(), torch.from_numpy(coo.col).long()
    hist, t0 = collections.defaultdict(list), time.time()
    for ep in range(1, epochs + 1):
        model.train(); perm = torch.randperm(len(U_all)); tot = 0.0
        for b in range(0, len(perm), batch_size):
            idx = perm[b:b + batch_size]
            u, i = U_all[idx].to(device), I_all[idx].to(device)
            j = torch.randint(0, model.ni, (len(idx),), device=device)   # negativo uniforme
            loss = model.bpr_loss(u, i, j, reg)
            opt.zero_grad(set_to_none=True); loss.backward(); opt.step(); tot += loss.item() * len(idx)
        if ep % eval_every == 0 or ep == epochs:
            m = evaluate_topk(score_fn_of(model), R_train, R_test, k=k)
            hist["epoch"].append(ep); hist["loss"].append(tot / len(perm)); hist[f"Recall@{k}"].append(m[f"Recall@{k}"])
            hist[f"NDCG@{k}"].append(m[f"NDCG@{k}"])
            print(f"[{name}] ep {ep:3d} loss={tot/len(perm):.4f} Recall@{k}={m[f'Recall@{k}']:.4f} NDCG@{k}={m[f'NDCG@{k}']:.4f} ({time.time()-t0:.0f}s)")
    hist["train_time_s"] = time.time() - t0
    return dict(hist)

def score_fn_of(model):
    '''Precalcula los embeddings propagados una vez y devuelve score_fn(users) -> [B, n_items].'''
    model.eval()
    with torch.no_grad():
        U, I = model.propagate()
    return lambda users: U[users.to(U.device)] @ I.T
"""

# ---------------------------------------------------------------------------
# LECCIÓN
# ---------------------------------------------------------------------------
nb = Notebook("Módulo 10 · Recomendación con grafos", colab_path=LESSON, gpu=True)
nb.md(f"""
{nb.badge()}

# Módulo 10 · Recomendación con grafos
### item2vec, DeepWalk/node2vec, GCN, PinSage y LightGCN

| | |
|---|---|
| **Nivel** | 🟠 Avanzado |
| **Duración** | 4 h (lección) + 3 h (proyecto) |
| **GPU recomendada** | T4 basta; L4 para el barrido de capas completo |
| **Unidades Colab estimadas** | ≈ 2–3 unidades (L4) en modo completo; < 1 en `FAST_DEV_RUN` |
| **Prerrequisitos** | 01, 02 (Recall/NDCG), 05 (MF, BPR), 08 (embeddings para retrieval), 09 (secuencias) |
""")
nb.md(r"""
## 🎯 Objetivos de aprendizaje
1. **Representar** las interacciones usuario–ítem como un **grafo bipartito** y razonar sobre caminos de varios saltos (*multi-hop*).
2. **Entrenar** embeddings de ítems con **item2vec** (gensim) y explicar su relación con la factorización de una matriz PMI.
3. **Implementar** paseos aleatorios **DeepWalk** y **node2vec** vectorizados y entender qué significan $p$ y $q$ en un grafo bipartito.
4. **Derivar** la propagación de **LightGCN** desde la GCN de Kipf & Welling y explicar por qué quitar no-linealidades y transformaciones **mejora** la recomendación.
5. **Implementar LightGCN desde cero** con multiplicación dispersa y compararlo con la versión de **PyTorch Geometric** y con **MF-BPR**.
6. **Diagnosticar** el *over-smoothing* y el efecto del grafo en usuarios con poca actividad (*long tail*).
7. **Describir** cómo Pinterest (PinSage), Alibaba (EGES), Twitter (TwHIN) y LinkedIn (LiGNN) despliegan grafos a escala de miles de millones de nodos.

### 🔁 Conexión con módulos anteriores
1. En el módulo 04, RP3β era un «paseo aleatorio de 3 pasos». ¿Qué tres nodos recorre y por qué ya era, sin decirlo, un método de grafos?
2. ¿Con qué pérdida del módulo 05 se entrena LightGCN, y a qué modelo se reduce cuando no hay propagación (K = 0)?
3. En el módulo 08, ¿por qué un modelo que solo tiene una fila de embedding por ID no puede servir a un ítem publicado hace 5 minutos? ¿Qué parte del two-tower lo resolvía?

<details><summary>Respuestas</summary>
1. Ítem → usuario → ítem: desde lo que viste, a quién más lo vio, a qué más vieron. Es difusión sobre el grafo bipartito con penalización de popularidad (β); hoy lo verás como $\hat A^k$.
2. BPR; con K = 0, LightGCN <b>es</b> MF-BPR: es la comparación controlada de la sección 7.
3. Porque el ID nuevo no tiene embedding entrenado (modelo <b>transductivo</b>). En el two-tower, la torre de ítem usaba <i>features</i> de contenido (géneros, año): eso la hace inductiva. PinSage (sección 8) aplica la misma idea a grafos.
</details>
""")
nb.code(PIP)
nb.code(IMPORTS)
nb.md(UTILS_MD.replace("HR@K y NDCG@K con *full ranking*", "Recall@K y NDCG@K con *full ranking* y split temporal por usuario"))
nb.code(UTILS_LOAD)
nb.code(UTILS_TOPK)
nb.code(LOAD)
nb.code(DRAW)

nb.md(r"""
## 💡 1. Intuición: tu matriz de interacciones ya es un grafo

La matriz usuario×ítem $R$ que usamos desde el módulo 01 es la **matriz de incidencia de un grafo bipartito**: un nodo por usuario, un nodo por ítem y una arista por interacción.
Ver los datos así ofrece algo que MF no hace explícitamente: **propagar información por caminos**.

- 1 salto: Ana → *Matrix* (lo que ya vio).
- 2 saltos: Ana → *Matrix* → Bea (usuarios parecidos: CF basado en usuario).
- 3 saltos: Ana → *Matrix* → Bea → *Blade Runner* (**candidato a recomendar**).

💡 **Analogía**: es como el *feature engineering* de «agregados de vecinos» en un modelo de fraude (media de las transacciones de las tarjetas vinculadas a un comerciante), pero **aprendido** y con varios saltos.
Una GNN para recomendación es, en esencia, un *smoothing* de embeddings sobre el grafo.
""")

nb.code(r"""
# 📊 Diagrama 1 — Ejemplo en papel: 5 usuarios × 6 películas como grafo bipartito
import networkx as nx
toy_users = ["Ana", "Bea", "Carlos", "Dani", "Eva"]
toy_items = ["Matrix", "Blade Runner", "Toy Story", "Up", "Alien", "Amélie"]
toy_R = np.array([[1, 0, 0, 0, 1, 0],
                  [1, 1, 0, 0, 1, 0],
                  [0, 0, 1, 1, 0, 0],
                  [0, 0, 1, 1, 0, 1],
                  [0, 1, 0, 0, 1, 1]])
G = nx.Graph()
G.add_nodes_from(toy_users, bipartite=0); G.add_nodes_from(toy_items, bipartite=1)
G.add_edges_from([(toy_users[a], toy_items[b]) for a, b in zip(*np.nonzero(toy_R))])
pos = {**{u: (0, -k) for k, u in enumerate(toy_users)}, **{it: (2, -k * 0.8 + 0.2) for k, it in enumerate(toy_items)}}
fig, ax = plt.subplots(1, 2, figsize=(13, 4.4))
sns.heatmap(toy_R, annot=True, cbar=False, cmap="Blues", xticklabels=toy_items, yticklabels=toy_users, ax=ax[0], linewidths=0.5)
ax[0].set_title("Matriz de interacciones R")
path = [("Ana", "Matrix"), ("Matrix", "Bea"), ("Bea", "Blade Runner")]
nx.draw_networkx_nodes(G, pos, nodelist=toy_users, node_color="#93c5fd", node_size=900, ax=ax[1])
nx.draw_networkx_nodes(G, pos, nodelist=toy_items, node_color="#fde68a", node_size=900, node_shape="s", ax=ax[1])
nx.draw_networkx_edges(G, pos, edge_color="#cbd5e1", ax=ax[1])
nx.draw_networkx_edges(G, pos, edgelist=path, edge_color="#ef4444", width=3, ax=ax[1])
nx.draw_networkx_labels(G, pos, font_size=8, ax=ax[1])
ax[1].set_title("Grafo bipartito: camino de 3 saltos Ana → Matrix → Bea → Blade Runner"); ax[1].axis("off")
plt.tight_layout(); plt.show()
""")

nb.code(r"""
# 📊 Gráfico 2 — Alcance por saltos: potencias de la adyacencia normalizada Â (en el ejemplo de papel)
nu_t, ni_t = toy_R.shape
A = np.block([[np.zeros((nu_t, nu_t)), toy_R], [toy_R.T, np.zeros((ni_t, ni_t))]])
d = A.sum(1); A_hat = A / np.sqrt(np.outer(d, d))
labels = toy_users + toy_items
fig, ax = plt.subplots(1, 3, figsize=(15, 4.4))
P = np.eye(len(A))
for k in range(1, 4):
    P = P @ A_hat
    sns.heatmap(P, ax=ax[k - 1], cmap="viridis", xticklabels=labels, yticklabels=labels, cbar=False)
    ax[k - 1].set_title(f"Â^{k}: quién influye en quién tras {k} salto(s)")
    ax[k - 1].tick_params(labelsize=7)
plt.tight_layout(); plt.show()
print("Puntuación usuario→ítem tras 3 saltos (bloque usuarios×ítems de Â³):")
display(pd.DataFrame(P[:nu_t, nu_t:], index=toy_users, columns=toy_items).round(3))
""")

nb.md(r"""
Observa el bloque usuarios×ítems de $\hat A^3$: **Ana** recibe peso en *Blade Runner* (que no ha visto) gracias a Bea, y casi nada en *Toy Story*.
Eso es *collaborative filtering* expresado como **difusión en un grafo**. LightGCN aprende embeddings que se combinan exactamente con esta difusión.

## 2. Embeddings por co-ocurrencia: item2vec

**item2vec** (Barkan & Koenigstein, 2016) aplica *word2vec skip-gram con negative sampling* (SGNS) tratando el historial de cada usuario como una «frase»:
$$\max\;\sum_{(i,j)\in\mathcal{D}} \Big[\log\sigma(\mathbf{v}_i^\top\mathbf{w}_j) + \sum_{n=1}^{k}\mathbb{E}_{j'\sim P_n}\log\sigma(-\mathbf{v}_i^\top\mathbf{w}_{j'})\Big]$$
- $\mathcal{D}$: pares (ítem, ítem de contexto) que co-ocurren dentro de una ventana.
- $P_n(j)\propto f(j)^{0.75}$: distribución de negativos (frecuencia elevada a 0,75).
- 📐 Levy & Goldberg (2014) demostraron que SGNS factoriza implícitamente la matriz $\mathrm{PMI}(i,j) - \log k$: item2vec es una **factorización de co-ocurrencias**, primo hermano de MF.

En producción esto es **Airbnb** (*listing embeddings* entrenados sobre sesiones de clics, Grbovic & Cheng, KDD 2018) o los *embeddings* de productos de **Alibaba EGES** (paseos sobre el grafo de sesiones + información lateral).
""")
nb.code(r"""
from gensim.models import Word2Vec
# Frases = historial de train ordenado por tiempo
sentences = train_df.sort_values(["u", "ts"]).groupby("u")["i"].apply(lambda x: [str(v) for v in x]).tolist()
t0 = time.time()
w2v = Word2Vec(sentences, vector_size=64, window=10, sg=1, negative=10, ns_exponent=0.75, sample=1e-3,
               min_count=1, epochs=3 if FAST_DEV_RUN else 15, workers=4, seed=seed)
print(f"item2vec entrenado en {time.time()-t0:.1f}s  | vocabulario: {len(w2v.wv):,} ítems")
pop_items = train_df.i.value_counts().index[:3]
for it in pop_items:
    sims = w2v.wv.most_similar(str(it), topn=5)
    print(f"\n«{title[it]}» → ", "; ".join(f"{title[int(j)]} ({s:.2f})" for j, s in sims))
""")
nb.code(r"""
# item2vec como recomendador: usuario = media de los vectores de sus últimos 20 ítems (ponderada por recencia)
I2V = np.zeros((n_items, 64), dtype=np.float32)
for k in w2v.wv.index_to_key:
    I2V[int(k)] = w2v.wv[k]
I2V /= np.linalg.norm(I2V, axis=1, keepdims=True) + 1e-9
last = train_df.sort_values(["u", "ts"]).groupby("u")["i"].apply(lambda x: x.values[-20:])
U2V = np.zeros((n_users, 64), dtype=np.float32)
for u, its in last.items():
    w = np.linspace(0.5, 1.0, len(its))[:, None]
    U2V[u] = (I2V[its] * w).sum(0)
U2V_t, I2V_t = torch.from_numpy(U2V), torch.from_numpy(I2V)
pop_vec = torch.from_numpy(np.asarray(R_train.sum(0)).ravel().astype(np.float32))
results = {"Popularidad": evaluate_topk(lambda u: pop_vec.expand(len(u), -1), R_train, R_test),
           "item2vec (gensim)": evaluate_topk(lambda u: U2V_t[u] @ I2V_t.T, R_train, R_test)}
display(pd.DataFrame(results).T.round(4))
""")

nb.md(r"""
### 2.1 SGNS desde cero (para ver que no hay magia)
El mismo objetivo en PyTorch: generamos pares (centro, contexto) con ventana aleatoria, muestreamos negativos de $f^{0.75}$ y optimizamos dos tablas de *embeddings* (`V` de entrada, `W` de contexto).
""")
nb.code(r"""
def sgns_pairs(sentences, window=5, max_pairs=2_000_000, rng=np.random.default_rng(seed)):
    c, x = [], []
    for s in sentences:
        s = np.array(s, dtype=np.int64)
        for off in range(1, window + 1):
            if len(s) > off:
                c += [s[:-off], s[off:]]; x += [s[off:], s[:-off]]      # contexto a ambos lados
    c, x = np.concatenate(c), np.concatenate(x)
    sel = rng.choice(len(c), min(max_pairs, len(c)), replace=False)
    return torch.from_numpy(c[sel]), torch.from_numpy(x[sel])

class SGNS(nn.Module):
    def __init__(self, n, d=64):
        super().__init__()
        self.V, self.W = nn.Embedding(n, d), nn.Embedding(n, d)
        nn.init.uniform_(self.V.weight, -0.5 / d, 0.5 / d); nn.init.zeros_(self.W.weight)
    def forward(self, c, x, neg):
        v = self.V(c)
        return -(F.logsigmoid((v * self.W(x)).sum(-1)) + F.logsigmoid(-torch.einsum("bd,bkd->bk", v, self.W(neg))).sum(-1)).mean()

int_sent = [[int(t) for t in s] for s in sentences]
C, X = sgns_pairs(int_sent, max_pairs=200_000 if FAST_DEV_RUN else 3_000_000)
freq = np.bincount(np.concatenate(int_sent), minlength=n_items) ** 0.75
neg_dist = torch.from_numpy(freq / freq.sum()).float()
sg = SGNS(n_items).to(device); opt = torch.optim.Adam(sg.parameters(), lr=3e-3)
for ep in range(1 if FAST_DEV_RUN else 3):
    perm = torch.randperm(len(C)); tot = 0
    for b in range(0, len(C), 4096):
        idx = perm[b:b + 4096]
        neg = torch.multinomial(neg_dist, len(idx) * 10, replacement=True).view(len(idx), 10)
        loss = sg(C[idx].to(device), X[idx].to(device), neg.to(device))
        opt.zero_grad(); loss.backward(); opt.step(); tot += loss.item() * len(idx)
    print(f"época {ep+1}: pérdida SGNS = {tot/len(C):.4f}")
Vs = F.normalize(sg.V.weight.detach().cpu(), dim=1)
it0 = int(pop_items[0]); nn_ = (Vs @ Vs[it0]).topk(6).indices[1:].tolist()
print(f"Vecinos de «{title[it0]}» (SGNS desde cero):", [title[j] for j in nn_])
""")

nb.md(r"""
## 3. Paseos aleatorios: DeepWalk y node2vec

**DeepWalk** (Perozzi et al., 2014): genera paseos aleatorios uniformes sobre el grafo y los trata como frases para word2vec.
**node2vec** (Grover & Leskovec, 2016) sesga el paseo de segundo orden. Si venimos de $t$ y estamos en $v$, el siguiente nodo $x$ se elige con peso
$$\alpha_{pq}(t,x) = \begin{cases} 1/p & d(t,x)=0 \;(\text{volver}) \\ 1 & d(t,x)=1 \\ 1/q & d(t,x)=2\end{cases}$$
$p$ grande → explora (poca vuelta atrás); $q$ grande → paseo «BFS» (local, homofilia); $q$ pequeño → «DFS» (lejos, roles estructurales).

🧠 **Detalle que casi nadie nota**: en un grafo **bipartito** $d(t,x)=1$ es imposible ($t$ y $x$ están en el mismo lado y no hay aristas entre nodos del mismo lado).
Así que node2vec en usuario–ítem sólo tiene **un grado de libertad efectivo**: el cociente entre «volver» ($1/p$) y «avanzar» ($1/q$).

Implementamos los paseos **vectorizados** con la estructura CSR (todos los paseos avanzan a la vez), algo esencial en Python para no tardar horas.
""")
nb.code(r"""
import scipy.sparse as sp
A_bip = sp.bmat([[None, R_train], [R_train.T, None]]).tocsr()          # nodos: [usuarios | ítems]
indptr, indices = A_bip.indptr, A_bip.indices
deg = np.diff(indptr)

def random_walks(starts, length=20, p=1.0, q=1.0, rng=np.random.default_rng(seed)):
    '''Paseos node2vec vectorizados para grafo bipartito (p=q=1 => DeepWalk). Devuelve [n_walks, length].'''
    W = np.zeros((len(starts), length), dtype=np.int64); W[:, 0] = starts
    nxt = lambda cur: indices[indptr[cur] + (rng.random(len(cur)) * deg[cur]).astype(np.int64)]
    W[:, 1] = nxt(W[:, 0])
    w_back, w_fwd = 1 / p, 1 / q; w_max = max(w_back, w_fwd)
    for t in range(2, length):
        cur, prev = W[:, t - 1], W[:, t - 2]
        out = np.full(len(cur), -1)
        todo = np.arange(len(cur))
        while len(todo):                                                # muestreo por rechazo
            cand = nxt(cur[todo])
            w = np.where(cand == prev[todo], w_back, w_fwd)
            acc = rng.random(len(todo)) < w / w_max
            out[todo[acc]] = cand[acc]; todo = todo[~acc]
        W[:, t] = out
    return W

starts = np.repeat(np.arange(A_bip.shape[0])[deg > 0], 2 if FAST_DEV_RUN else 10)
t0 = time.time(); walks = random_walks(starts, length=20, p=1.0, q=1.0)
print(f"{len(walks):,} paseos DeepWalk en {time.time()-t0:.1f}s")
""")
nb.code(r"""
# 📊 Gráfico 3 — Qué hacen p y q: tasa de vuelta atrás y nº de nodos distintos que visitan los paseos
def mean_return_rate(W):
    return (W[:, 2:] == W[:, :-2]).mean()          # fracción de pasos que vuelven al nodo de hace 2 pasos

configs = [(1, 1), (4, 1), (0.25, 1), (1, 4), (1, 0.25)]
sub = np.random.default_rng(1).choice(starts, 3000)
rates = [mean_return_rate(random_walks(sub, 20, p, q)) for p, q in configs]
uniq = [len(np.unique(random_walks(sub, 20, p, q)[:, 1:])) for p, q in configs]
fig, ax = plt.subplots(1, 2, figsize=(12, 3.6))
lbl = [f"p={p}, q={q}" for p, q in configs]
ax[0].bar(lbl, rates, color="#8b5cf6"); ax[0].set(title="Tasa de «vuelta atrás» del paseo", ylabel="fracción")
ax[1].bar(lbl, uniq, color="#14b8a6"); ax[1].set(title="Nodos distintos visitados (3.000 paseos)", ylabel="nº nodos")
for a in ax: a.tick_params(axis="x", rotation=20)
plt.tight_layout(); plt.show()
""")
nb.md(r'''
> 👀 **Qué debes observar:** con $p$ pequeño (0,25) el paseo vuelve atrás muchísimo y visita **pocos nodos distintos** (se queda en el vecindario inmediato); con $p$ grande explora más. Cambiar $q$ mueve las barras en sentido contrario: en un grafo bipartito solo importa el cociente entre «volver» y «avanzar», como anticipaba el 🧠 de arriba. Antes de tunear $p$ y $q$ por separado en un grafo usuario–ítem, recuerda que estás buscando en un espacio de **una** dimensión efectiva.
''')
nb.code(r"""
# DeepWalk -> word2vec sobre los paseos; nos quedamos con los nodos ítem para recomendar
dw = Word2Vec([list(map(str, w)) for w in walks], vector_size=64, window=5, sg=1, negative=5, min_count=1,
              epochs=1 if FAST_DEV_RUN else 3, workers=4, seed=seed)
DW = np.zeros((A_bip.shape[0], 64), dtype=np.float32)
for k in dw.wv.index_to_key:
    DW[int(k)] = dw.wv[k]
DW_t = torch.from_numpy(DW)
results["DeepWalk (usuario·ítem)"] = evaluate_topk(lambda u: DW_t[u] @ DW_t[n_users:].T, R_train, R_test)
display(pd.DataFrame(results).T.round(4))
""")

nb.md(r"""
## 📐 4. De la GCN a LightGCN

### 4.1 GCN (Kipf & Welling, 2017)
$$H^{(k+1)} = \sigma\!\left(\hat A\, H^{(k)}\, W^{(k)}\right),\qquad \hat A = D^{-1/2} A D^{-1/2}$$
- $A$: adyacencia; $D$: grado; $\hat A$ normaliza para que los nodos con muchos vecinos no exploten.
- $W^{(k)}$: transformación lineal por capa; $\sigma$: no-linealidad (ReLU).

**NGCF** (Wang et al., SIGIR 2019) llevó esto a CF añadiendo interacciones $\mathbf{e}_i\odot\mathbf{e}_u$.

### 4.2 LightGCN (He et al., SIGIR 2020): menos es más
He et al. hicieron la ablación: **quitar** $W^{(k)}$ y $\sigma$ **mejora** la recomendación (~16 % de mejora relativa media frente a NGCF en sus *benchmarks*).
La razón: en CF los nodos sólo tienen un ID (no hay *features* ricas que transformar), y las transformaciones sólo añaden parámetros difíciles de entrenar.
$$\mathbf{e}_u^{(k+1)} = \sum_{i\in\mathcal{N}_u}\frac{1}{\sqrt{|\mathcal{N}_u|}\sqrt{|\mathcal{N}_i|}}\,\mathbf{e}_i^{(k)},\qquad
\mathbf{e}_i^{(k+1)} = \sum_{u\in\mathcal{N}_i}\frac{1}{\sqrt{|\mathcal{N}_i|}\sqrt{|\mathcal{N}_u|}}\,\mathbf{e}_u^{(k)}$$
En forma matricial, con $E^{(0)}$ los **únicos parámetros** del modelo:
$$E^{(k+1)} = \hat A\,E^{(k)},\qquad E = \sum_{k=0}^{K}\alpha_k E^{(k)} = \Big(\sum_{k=0}^{K}\alpha_k \hat A^{k}\Big)E^{(0)},\qquad \hat y_{ui} = \mathbf{e}_u^\top\mathbf{e}_i$$
con $\alpha_k = 1/(K+1)$. Se entrena con **BPR** (módulo 05):
$\mathcal{L} = -\sum_{(u,i,j)}\log\sigma(\hat y_{ui}-\hat y_{uj}) + \lambda\|E^{(0)}\|^2$.

🔑 **Observaciones clave**
1. Con $K = 0$, LightGCN **es exactamente MF-BPR**. Esto nos da una comparación perfectamente controlada.
2. $\sum_k \alpha_k \hat A^k$ es un **filtro paso-bajo** sobre el grafo: suaviza los embeddings entre vecinos (por eso funciona y por eso, con $K$ grande, *over-smoothing*).
3. La combinación de capas evita que el resultado sea sólo $\hat A^K E^{(0)}$, que convergería a un vector casi constante.
""")
nb.code(r"""
# 📊 Diagrama 4 — Propagación de LightGCN (K=3) y combinación de capas
fig, ax = plt.subplots(figsize=(12, 4.2)); ax.set_xlim(0, 12); ax.set_ylim(0, 4.4); ax.axis("off")
for k in range(4):
    x = 0.5 + k * 2.6
    box(ax, x, 2.6, 1.8, 0.9, f"$E^{{({k})}}$" + ("\n(parámetros)" if k == 0 else ""), fc="#c7d2fe" if k == 0 else "#e0e7ff")
    if k < 3:
        arrow(ax, x + 1.8, 3.05, x + 2.6, 3.05, color="#4338ca", lw=2)
        ax.text(x + 2.2, 3.25, "×Â", ha="center", fontsize=10, color="#4338ca")
    arrow(ax, x + 0.9, 2.6, 5.6, 1.45, color="#94a3b8")
box(ax, 4.6, 0.5, 2.4, 0.9, "$E = \\frac{1}{K+1}\\sum_k E^{(k)}$", fc="#fde68a", ec="#b45309")
box(ax, 8.6, 0.5, 3.0, 0.9, "$\\hat y_{ui} = e_u^\\top e_i$  →  BPR", fc="#fef3c7", ec="#b45309")
arrow(ax, 7.0, 0.95, 8.6, 0.95, color="#b45309", lw=2)
ax.set_title("LightGCN: sin pesos por capa ni no-linealidades; sólo difusión lineal y media de capas", fontsize=10)
plt.show()
""")
nb.md(r"""
## 🛠️ 5. LightGCN desde cero (multiplicación dispersa)
Construimos $\hat A$ una vez como tensor disperso de PyTorch y en cada paso hacemos $K$ productos `torch.sparse.mm`.
Coste por paso: $O(K\cdot|\mathcal{E}|\cdot d)$ — barato en GPU para ML-1M (~1,6 M de aristas dirigidas).
""")
nb.code(LIGHTGCN)
nb.code(TRAIN)
nb.code(r"""
adj = build_norm_adj(R_train)
EPOCHS = 3 if FAST_DEV_RUN else 60
hists, models_ = {}, {}
for K, name in [(0, "MF-BPR (LightGCN K=0)"), (3, "LightGCN K=3 (scratch)")]:
    torch.manual_seed(seed)
    models_[name] = LightGCN(n_users, n_items, adj, d=64, n_layers=K)
    hists[name] = train_bpr(models_[name], R_train, R_test, epochs=EPOCHS, eval_every=1 if FAST_DEV_RUN else 10, name=name)
    results[name] = evaluate_topk(score_fn_of(models_[name]), R_train, R_test)
display(pd.DataFrame(results).T.round(4))
""")

nb.md(r"""
## 🏗️ 6. La versión de industria: PyTorch Geometric

`torch_geometric.nn.LightGCN` implementa lo mismo con *message passing* (`LGConv`). Interfaz:
- `model(edge_index, edge_label_index)` → puntuaciones de los pares de `edge_label_index` (la propagación usa `edge_index`).
- `model.recommendation_loss(pos, neg, node_id=...)` → BPR + regularización.
- `model.get_embedding(edge_index)` → embeddings finales para servir con ANN (módulo 08).

PyG trabaja con un grafo **homogéneo** de `n_users + n_items` nodos: los ítems tienen índices desplazados `+ n_users`.
""")
nb.code(r"""
from torch_geometric.nn import LightGCN as PyGLightGCN
coo = R_train.tocoo()
src = torch.from_numpy(coo.row).long(); dst = torch.from_numpy(coo.col).long() + n_users
edge_index = torch.stack([torch.cat([src, dst]), torch.cat([dst, src])]).to(device)   # no dirigido
train_pairs = torch.stack([src, dst]).to(device)

def train_pyg(epochs, batch_size=8192, lr=2e-3, K=3, d=64):
    torch.manual_seed(seed)
    model = PyGLightGCN(num_nodes=n_users + n_items, embedding_dim=d, num_layers=K).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr); t0 = time.time()
    for ep in range(1, epochs + 1):
        perm = torch.randperm(train_pairs.size(1), device=device)
        for b in range(0, len(perm), batch_size):
            pos = train_pairs[:, perm[b:b + batch_size]]
            neg = torch.stack([pos[0], torch.randint(n_users, n_users + n_items, (pos.size(1),), device=device)])
            pos_r, neg_r = model(edge_index, torch.cat([pos, neg], 1)).chunk(2)
            loss = model.recommendation_loss(pos_r, neg_r, node_id=torch.cat([pos, neg], 1).unique())
            opt.zero_grad(); loss.backward(); opt.step()
    print(f"PyG LightGCN entrenado en {time.time()-t0:.0f}s")
    return model

pyg_model = train_pyg(EPOCHS)
with torch.no_grad():
    emb = pyg_model.get_embedding(edge_index)
U_pyg, I_pyg = emb[:n_users], emb[n_users:]
results["LightGCN K=3 (PyG)"] = evaluate_topk(lambda u: U_pyg[u.to(device)] @ I_pyg.T, R_train, R_test)
display(pd.DataFrame(results).T.round(4))
""")
nb.md(r"""
Las dos implementaciones deben quedar cerca (no idénticas: PyG regulariza con `lambda_reg=1e-4` sobre los nodos del *batch* con otra escala e inicializa con Xavier).
La versión *scratch* es más rápida para grafos pequeños (un solo `sparse.mm` por capa); PyG brilla cuando necesitas *neighbor sampling*, grafos heterogéneos o entrenamiento distribuido.
""")

nb.md(r"""
## 🧪 7. Experimentos
### 7.1 ¿Cuántas capas? Rendimiento y *over-smoothing*
""")
nb.code(r"""
layer_res = {}
Ks = [0, 1, 2, 3] if FAST_DEV_RUN else [0, 1, 2, 3, 4, 6]
for K in Ks:
    torch.manual_seed(seed)
    m = LightGCN(n_users, n_items, adj, d=64, n_layers=K)
    train_bpr(m, R_train, R_test, epochs=EPOCHS, eval_every=EPOCHS, name=f"K={K}")
    layer_res[K] = evaluate_topk(score_fn_of(m), R_train, R_test)
# Over-smoothing: similitud coseno media entre ítems al propagar MUCHAS capas (sin y con media de capas)
E0 = models_["MF-BPR (LightGCN K=0)"].emb.weight.detach()
samp = torch.randperm(n_items)[:1000] + n_users
cos_last, cos_mean, E, acc = [], [], E0.clone(), [E0.clone()]
for k in range(0, 16):
    if k > 0:
        E = torch.sparse.mm(adj, E); acc.append(E)
    for store, M in [(cos_last, E), (cos_mean, torch.stack(acc).mean(0))]:
        Z = F.normalize(M[samp], dim=1); store.append(((Z @ Z.T).sum() - len(Z)).item() / (len(Z) * (len(Z) - 1)))
fig, ax = plt.subplots(1, 2, figsize=(13, 4))
ax[0].plot(list(layer_res), [v["Recall@20"] for v in layer_res.values()], marker="o", lw=2, label="Recall@20")
ax[0].plot(list(layer_res), [v["NDCG@20"] for v in layer_res.values()], marker="s", lw=2, label="NDCG@20")
ax[0].set(title="LightGCN: calidad vs nº de capas K (K=0 ≡ MF)", xlabel="K"); ax[0].legend()
ax[1].plot(cos_last, lw=2, label="sólo última capa Âᴷ E")
ax[1].plot(cos_mean, lw=2, label="media de capas (LightGCN)")
ax[1].set(title="Over-smoothing: coseno medio entre ítems", xlabel="capas de propagación", ylabel="coseno medio"); ax[1].legend()
plt.tight_layout(); plt.show()
""")
nb.md(r'''
> 👀 **Qué debes observar:** (izquierda) el salto grande está entre K = 0 (MF) y K = 1–2; a partir de 3 capas la mejora se aplana o se invierte. (derecha) si solo usas la última capa, el coseno medio entre ítems sube hacia 1 a medida que propagas: **todos los ítems acaban pareciéndose** (*over-smoothing*, el filtro paso-bajo llevado al extremo). La media de capas de LightGCN crece mucho más despacio porque conserva $E^{(0)}$. Por eso en la práctica K = 2–3 y nunca 10.
''')
nb.md(r"""
### 7.2 ¿A quién ayuda el grafo? Rendimiento por actividad del usuario
La hipótesis: los usuarios con **pocas interacciones** se benefician más de la propagación (toman prestada señal de vecinos a 2–3 saltos).
""")
nb.code(r"""
act = np.diff(R_train.indptr)
buckets = pd.qcut(act, 4, labels=["Q1 (poca actividad)", "Q2", "Q3", "Q4 (mucha)"])
rows = []
for name in ["MF-BPR (LightGCN K=0)", "LightGCN K=3 (scratch)"]:
    fn = score_fn_of(models_[name])
    for bk in buckets.categories:
        mask_u = np.zeros(n_users, bool); mask_u[np.where(buckets == bk)[0]] = True
        R_te_b = R_test.multiply(mask_u[:, None]).tocsr()
        rows.append({"modelo": name, "cuartil": bk, **evaluate_topk(fn, R_train, R_te_b)})
bq = pd.DataFrame(rows)
fig, ax = plt.subplots(figsize=(9, 3.8))
sns.barplot(data=bq, x="cuartil", y="Recall@20", hue="modelo", ax=ax, palette=["#94a3b8", "#6366f1"])
ax.set(title="Recall@20 por cuartil de actividad del usuario (train)", xlabel=""); plt.show()
""")
nb.md(r'''
> 👀 **Qué debes observar:** compara la **diferencia relativa** entre barras de cada cuartil, no la altura absoluta (los usuarios activos tienen más relevantes en test y su recall se comporta distinto). Si la hipótesis es cierta, la ventaja de LightGCN sobre MF es mayor en Q1 (poca actividad): los usuarios con pocas interacciones toman prestada señal de vecinos a 2–3 saltos. Si en tu ejecución no se cumple, es un resultado legítimo: con MF bien regularizado la ventaja del grafo puede ser pequeña (lo dice la rúbrica del proyecto).
''')
nb.code(r"""
# 📊 Gráfico — Comparación final + curvas de entrenamiento + t-SNE de los embeddings LightGCN
from sklearn.manifold import TSNE
fig, ax = plt.subplots(1, 3, figsize=(17, 4.4))
res = pd.DataFrame(results).T.sort_values("Recall@20")
res["Recall@20"].plot.barh(ax=ax[0], color="#6366f1"); ax[0].set(title="Test Recall@20 (split temporal)")
for name, h in hists.items():
    ax[1].plot(h["epoch"], h["Recall@20"], marker="o", ms=3, label=name)
ax[1].set(title="Recall@20 durante el entrenamiento", xlabel="época"); ax[1].legend(fontsize=8)
_, I_lg = models_["LightGCN K=3 (scratch)"].propagate()
top = np.argsort(-np.asarray(R_train.sum(0)).ravel())[:1200]
Z = TSNE(2, init="pca", random_state=seed, perplexity=30).fit_transform(I_lg[top].detach().cpu().numpy())
g = pd.Series([genre.get(int(i), "?") for i in top]); main = g.value_counts().index[:7]
for gg in main:
    msk = (g == gg).values; ax[2].scatter(Z[msk, 0], Z[msk, 1], s=7, label=gg)
ax[2].set(title="t-SNE ítems (LightGCN), por género", xticks=[], yticks=[]); ax[2].legend(fontsize=7, markerscale=2)
plt.tight_layout(); plt.show()
""")

nb.md(r"""
## 🌲 8. PinSage: GNN a escala web (Pinterest, KDD 2018)

LightGCN es **transductivo**: necesita un embedding por nodo y propagar sobre **todo** el grafo en cada paso. A 3.000 M de nodos eso es inviable.
**PinSage** (Ying et al., 2018) lo resuelve con cuatro ideas:
1. **Vecindarios por paseos aleatorios**: los vecinos de un pin son los $T$ nodos más visitados en paseos cortos desde él (*importance-based neighborhoods*), no todos los adyacentes.
2. **Convoluciones locales sobre *features*** (imagen + texto del pin), no sobre IDs → **inductivo**: sirve para pines nuevos.
3. ***Importance pooling***: la agregación pondera a cada vecino por su número de visitas normalizado.
4. **Negativos duros con *curriculum*** y **inferencia con MapReduce** (los embeddings se calculan por lotes para miles de millones de nodos sin repetir cómputo).

Escala reportada: grafo de **3.000 M de nodos y 18.000 M de aristas**, entrenado con 7.500 M de ejemplos.
Implementamos la idea 1 (vecindario por importancia) sobre MovieLens con nuestros paseos vectorizados:
""")
nb.code(r"""
def importance_neighbors(item, n_walks=2000, length=4, T=10, rng=np.random.default_rng(seed)):
    '''Paseos ítem→usuario→ítem desde `item`; devuelve los T ítems más visitados (sin el propio) y su peso normalizado.'''
    W = random_walks(np.full(n_walks, item + n_users), length=length, rng=rng)
    visited = W[:, 2::2].ravel() - n_users                  # posiciones pares = ítems
    cnt = collections.Counter(visited[visited != item])
    top = cnt.most_common(T); tot = sum(c for _, c in top)
    return [(i, c / tot) for i, c in top]

it0 = int(pop_items[0])
neigh = importance_neighbors(it0)
fig, ax = plt.subplots(figsize=(9, 4))
ax.barh([title[i][:35] for i, _ in neigh][::-1], [w for _, w in neigh][::-1], color="#f97316")
ax.set(title=f"PinSage: vecindario por importancia de «{title[it0][:40]}»", xlabel="peso de importance pooling")
plt.tight_layout(); plt.show()
""")
nb.md(r'''
> 👀 **Qué debes observar:** los 10 vecinos por importancia son películas **co-consumidas** con la consulta (no necesariamente del mismo género) y sus pesos decaen rápido: unos pocos vecinos concentran la mayoría de visitas. Eso es lo que permite a PinSage agregar solo $T$ vecinos en vez de los miles de adyacentes de un pin popular, y es pariente directo del item-kNN del módulo 04 (co-ocurrencias a 2 saltos).
''')
nb.code(r"""
# 📊 Diagrama — PinSage: muestreo de vecindario + agregación por importancia (2 capas)
fig, ax = plt.subplots(figsize=(12, 4.6)); ax.set_xlim(0, 12); ax.set_ylim(0, 5); ax.axis("off")
box(ax, 0.3, 2.0, 2.0, 1.0, "pin objetivo\n(imagen+texto)", fc="#fde68a", ec="#b45309")
for k, y in enumerate([0.4, 1.6, 2.8, 4.0]):
    box(ax, 3.2, y, 1.8, 0.7, f"vecino {k+1}\nw={[0.4, 0.3, 0.2, 0.1][k]}", fc="#e0f2fe", fs=8)
    arrow(ax, 3.2, y + 0.35, 2.3, 2.5, color="#0284c7")
    for j in range(2):
        box(ax, 5.8, y + j * 0.38 - 0.05, 1.2, 0.3, "2º salto", fc="#f1f5f9", fs=6)
        arrow(ax, 5.8, y + j * 0.38 + 0.1, 5.0, y + 0.35, color="#94a3b8", lw=0.8)
box(ax, 7.8, 1.6, 3.9, 1.8, "h = ReLU(W·[x_pin ; Σ w_j·h_j])\nnormalizar ‖h‖=1\n(conv. 2 capas, pesos compartidos)", fc="#ede9fe", ec="#6d28d9", fs=8)
arrow(ax, 7.0, 2.5, 7.8, 2.5, color="#6d28d9", lw=2)
ax.set_title("PinSage: vecinos = nodos más visitados por paseos aleatorios; agregación ponderada por visitas", fontsize=10)
plt.show()
""")

nb.md(r"""
## 🕸️ 9. Grafos heterogéneos y *knowledge graphs*
En la realidad hay varios tipos de nodo y relación: usuario, película, género, actor, director; *vio*, *puntuó*, *pertenece a*, *actúa en*.
- **KGAT** (Wang et al., KDD 2019): atención sobre el grafo colaborativo + *knowledge graph*.
- **R-GCN / HGT**: pesos por tipo de relación. En PyG: `HeteroData` + `to_hetero`.
- **TwHIN** (Twitter, KDD 2022): embeddings de un grafo heterogéneo con miles de millones de nodos (usuarios, tweets, anunciantes) usados en *ads*, *follow recommendation* y búsqueda.

Construimos el `HeteroData` de CineMatch (usuario–película–género). Es la base del reto extra del proyecto (añadir nodos género para ayudar a los ítems fríos).
""")
nb.code(r"""
from torch_geometric.data import HeteroData
genres_all = sorted({g for gs in movies.genres.str.split("|") for g in gs})
g2i = {g: k for k, g in enumerate(genres_all)}
mg = [(it2i[it], g2i[g]) for it, gs in zip(movies.item, movies.genres.str.split("|")) if it in it2i for g in gs]
data = HeteroData()
data["user"].num_nodes, data["movie"].num_nodes, data["genre"].num_nodes = n_users, n_items, len(genres_all)
data["user", "rates", "movie"].edge_index = torch.stack([torch.from_numpy(coo.row), torch.from_numpy(coo.col)]).long()
data["movie", "has", "genre"].edge_index = torch.tensor(mg).T.long()
print(data)
fig, ax = plt.subplots(figsize=(8, 2.6)); ax.set_xlim(0, 10); ax.set_ylim(0, 2.4); ax.axis("off")
box(ax, 0.3, 0.8, 2.0, 0.8, f"user\n{n_users:,}", fc="#93c5fd"); box(ax, 4.0, 0.8, 2.0, 0.8, f"movie\n{n_items:,}", fc="#fde68a")
box(ax, 7.7, 0.8, 2.0, 0.8, f"genre\n{len(genres_all)}", fc="#bbf7d0")
arrow(ax, 2.3, 1.2, 4.0, 1.2, lw=2); ax.text(3.15, 1.4, "rates", ha="center")
arrow(ax, 6.0, 1.2, 7.7, 1.2, lw=2); ax.text(6.85, 1.4, "has", ha="center")
ax.set_title("Esquema del grafo heterogéneo de CineMatch"); plt.show()
""")

nb.md(r"""
## 🏭 10. En producción
| Empresa | Sistema | Qué hace | Referencia |
|---|---|---|---|
| **Pinterest** | PinSage → PinnerSage → PinnerFormer | Embeddings de pines con GCN inductiva (2018), múltiples embeddings por usuario (2020), modelos secuenciales sobre embeddings PinSage (2022) | Ying et al. KDD 2018; Pal et al. KDD 2020; Pancha et al. KDD 2022 |
| **Alibaba** | EGES | Grafo de ítems a partir de sesiones + paseos + *side information* (marca, categoría) para *cold start* | Wang et al. KDD 2018 (arXiv:1803.02349) |
| **Airbnb** | *Listing embeddings* | Skip-gram sobre sesiones de clics con la reserva como contexto global | Grbovic & Cheng, KDD 2018 |
| **Twitter/X** | TwHIN | Embeddings de grafo heterogéneo (usuarios, tweets, anunciantes) | El-Kishky et al. KDD 2022 (arXiv:2202.05387) |
| **LinkedIn** | LiGNN | GNN a gran escala con grafos temporales, densificación para *cold start* y *multi-hop sampling* | Borisyuk et al. KDD 2024 (arXiv:2402.11139) |
| **Uber Eats** | GNN para platos/restaurantes | GraphSAGE sobre el grafo usuario–plato–restaurante como *feature* del ranker | Blog de ingeniería de Uber (2019) |

**Patrón común de despliegue.** Casi nadie sirve una GNN *online*. Los embeddings se calculan **por lotes** (diario/horario), se indexan en un ANN (FAISS/ScaNN, módulo 08) y se usan como (a) generador de candidatos o (b) *features* del ranker.
El cuello de botella no es el modelo sino el **pipeline de grafo**: construir, muestrear y particionar miles de millones de aristas.
""")
nb.md(r"""
## 🧠 11. Secretos de la élite
1. **Un MF bien tuneado es un rival muy serio.** Rendle et al. (2020, *Neural Collaborative Filtering vs. Matrix Factorization Revisited*) y la crisis de reproducibilidad (Dacrema et al. 2019, módulo 02) muestran que muchos modelos neuronales pierden contra MF/EASE bien ajustados. Compara siempre contra LightGCN con $K=0$ (MF) con el mismo presupuesto de *tuning*.
2. **LightGCN es un filtro paso-bajo.** Shen et al. (CIKM 2021, *How Powerful is Graph Convolution for Recommendation?*) mostraron que filtros espectrales **sin entrenamiento** (GF-CF) son competitivos con LightGCN. Si tienes poco tiempo, un filtro sobre la matriz de similitud de ítems normalizada es un *baseline* fortísimo.
3. **Hiperparámetros de word2vec ≠ NLP.** Caselles-Dupré et al. (RecSys 2018) reportan mejoras de hasta **10×** en la métrica de recomendación ajustando cuatro hiperparámetros que se suelen dejar por defecto: la distribución de negativos (`ns_exponent`, ¡a veces negativo, que favorece la cola!), las épocas, el *subsampling* y la ventana. No uses los valores por defecto de gensim: haz un barrido con el split temporal.
4. **La regularización va sobre $E^{(0)}$**, no sobre los embeddings propagados (así lo hace el código oficial de LightGCN), y **la normalización es un hiperparámetro de sesgo de popularidad**: $D^{-1/2}AD^{-1/2}$ reparte la masa de forma simétrica; variantes como $D^{-1}A$ o exponentes asimétricos $D_u^{-\alpha}AD_i^{-(1-\alpha)}$ desplazan el peso hacia ítems populares o de cola. Trabajos posteriores (p. ej. GF-CF, Shen et al. 2021) ajustan precisamente estos exponentes y ganan puntos sin tocar el modelo.
5. **Transductivo vs inductivo.** LightGCN no sabe qué hacer con un ítem nuevo; PinSage sí (usa *features*). En catálogos con mucha rotación (noticias, vídeo corto) eso decide la arquitectura.
6. **El coste está en la propagación completa por paso.** Para grafos grandes: *neighbor sampling* (GraphSAGE/PinSage), precomputar $\hat A^k X$ (SIGN/SGC) o entrenar MF y propagar **una sola vez** al final (una «LightGCN post-hoc» barata que a menudo recupera parte de la ganancia).
7. **Muestreo negativo uniforme en BPR** deja de aprender pronto: negativos duros (por popularidad o del propio modelo, como el *curriculum* de PinSage) suelen dar más que añadir capas.
""")
nb.md(r"""
## ⚠️ 12. Errores comunes
- **Fuga en el grafo**: construir $\hat A$ con interacciones de **test**. El grafo de propagación debe contener sólo train.
- Olvidar enmascarar los ítems de train al evaluar (Recall inflado por recomendar lo ya visto).
- Usar el mismo índice para usuarios e ítems en un grafo homogéneo (en PyG los ítems van desplazados `+ n_users`).
- Comparar con un MF sin regularizar o con menos épocas: la «mejora de la GNN» desaparece al tunear el *baseline*.
- Apilar muchas capas «porque es *deep*» → *over-smoothing*; 2–3 capas suelen ser óptimas.
- Para item2vec, barajar los ítems de la frase (se pierde la señal de orden/ventana) o usar ventanas diminutas con historiales largos.
""")
nb.md(r"""
## ✅ 13. Autoevaluación
1. ¿Qué modelo obtienes con LightGCN y $K=0$? ¿Por qué es útil para experimentar?
<details><summary>Respuesta</summary>MF entrenado con BPR: el embedding final es E⁽⁰⁾. Permite aislar el efecto de la propagación con exactamente la misma pérdida, parámetros e hiperparámetros.</details>

2. Escribe la fórmula de $\hat A$ y explica qué pasaría sin normalizar.
<details><summary>Respuesta</summary>Â = D^{-1/2} A D^{-1/2}. Sin normalizar, la norma de los embeddings crecería con el grado y en cada capa (explosión numérica), y los nodos muy conectados dominarían todas las puntuaciones.</details>

3. ¿Por qué quitar las no-linealidades mejora LightGCN frente a NGCF?
<details><summary>Respuesta</summary>Los nodos sólo tienen IDs, no features ricas: las matrices W y la ReLU añaden parámetros y dificultan la optimización sin aportar capacidad útil. La ablación de He et al. mostró que la versión lineal entrena mejor y generaliza mejor.</details>

4. En un grafo bipartito, ¿qué efecto tiene el parámetro $q$ de node2vec?
<details><summary>Respuesta</summary>Como d(t,x)=1 es imposible, sólo compiten «volver» (1/p) y «avanzar» (1/q): q actúa sólo a través del cociente p/q que controla la tasa de vuelta atrás. No hay distinción BFS/DFS a un salto.</details>

5. ¿Qué es el *over-smoothing* y cómo lo mitiga LightGCN?
<details><summary>Respuesta</summary>Al aplicar Â muchas veces, los embeddings convergen al autovector dominante y todos se parecen (coseno → 1). LightGCN promedia las capas 0..K, conservando la componente original E⁽⁰⁾ y las de bajo orden.</details>

6. ¿Por qué PinSage puede generar embeddings para un pin publicado hace 5 minutos y LightGCN no?
<details><summary>Respuesta</summary>PinSage es inductivo: calcula el embedding a partir de las features visuales/textuales del pin y de las de sus vecinos con pesos compartidos. LightGCN sólo tiene una fila de embedding por nodo visto en entrenamiento.</details>

7. ¿Qué relación hay entre item2vec y la factorización matricial?
<details><summary>Respuesta</summary>SGNS factoriza implícitamente la matriz PMI desplazada (PMI − log k) de co-ocurrencias ítem-ítem (Levy & Goldberg 2014): es una factorización de una matriz de co-ocurrencia transformada.</details>

8. **(Razonamiento)** Escribe la puntuación de LightGCN con K = 1 y $\alpha_0=\alpha_1=\tfrac12$ como función de $E^{(0)}$. ¿Qué término nuevo aparece frente a MF y qué significa?
<details><summary>Respuesta</summary>E = ½(I + Â)E⁽⁰⁾, así que ŷ<sub>ui</sub> = ¼ (e<sub>u</sub> + Σ<sub>j∈N(u)</sub> c<sub>uj</sub> e<sub>j</sub>)ᵀ(e<sub>i</sub> + Σ<sub>v∈N(i)</sub> c<sub>iv</sub> e<sub>v</sub>), con c los coeficientes normalizados 1/√(|N<sub>u</sub>||N<sub>j</sub>|). Además del término MF e<sub>u</sub>ᵀe<sub>i</sub>, aparecen productos «usuario con los usuarios que vieron i» y «los ítems que vio u con i»: es un híbrido de MF, user-kNN e item-kNN aprendido de una vez.</details>

9. **(Transferencia)** CineMatch quiere añadir nodos de **actor** y **director** al grafo para ayudar a los estrenos. ¿LightGCN tal cual lo resuelve? ¿Qué cambiarías?
<details><summary>Respuesta</summary>Solo en parte: un estreno conectado a actores conocidos recibe señal por propagación, pero LightGCN sigue siendo transductivo (el estreno necesita su fila de embedding y reentrenar). Opciones: grafo heterogéneo con pesos por relación (R-GCN/HGT, <code>HeteroData</code>), o un enfoque inductivo tipo PinSage cuyo embedding se calcule a partir de <i>features</i> y vecinos sin reentrenar.</details>
""")
nb.md(r"""
## 📚 14. Referencias
- Barkan & Koenigstein (2016). *Item2Vec: Neural Item Embedding for Collaborative Filtering*. MLSP. https://arxiv.org/abs/1603.04259
- Levy & Goldberg (2014). *Neural Word Embedding as Implicit Matrix Factorization*. NeurIPS.
- Perozzi, Al-Rfou & Skiena (2014). *DeepWalk: Online Learning of Social Representations*. KDD. https://arxiv.org/abs/1403.6652
- Grover & Leskovec (2016). *node2vec: Scalable Feature Learning for Networks*. KDD. https://arxiv.org/abs/1607.00653
- Kipf & Welling (2017). *Semi-Supervised Classification with Graph Convolutional Networks*. ICLR. https://arxiv.org/abs/1609.02907
- Hamilton, Ying & Leskovec (2017). *Inductive Representation Learning on Large Graphs* (GraphSAGE). NeurIPS. https://arxiv.org/abs/1706.02216
- Ying et al. (2018). *Graph Convolutional Neural Networks for Web-Scale Recommender Systems* (PinSage). KDD. https://arxiv.org/abs/1806.01973
- Wang, He, Wang, Feng & Chua (2019). *Neural Graph Collaborative Filtering* (NGCF). SIGIR. https://arxiv.org/abs/1905.08108
- Wang et al. (2019). *KGAT: Knowledge Graph Attention Network for Recommendation*. KDD. https://arxiv.org/abs/1905.07854
- He et al. (2020). *LightGCN: Simplifying and Powering Graph Convolution Network for Recommendation*. SIGIR. https://arxiv.org/abs/2002.02126
- Rendle, Krichene, Zhang & Anderson (2020). *Neural Collaborative Filtering vs. Matrix Factorization Revisited*. RecSys. https://arxiv.org/abs/2005.09683
- Shen et al. (2021). *How Powerful is Graph Convolution for Recommendation?* CIKM. https://arxiv.org/abs/2108.07567
- Caselles-Dupré, Lesaint & Royo-Letelier (2018). *Word2Vec applied to Recommendation: Hyperparameters Matter*. RecSys. https://arxiv.org/abs/1804.04212
- Wang et al. (2018). *Billion-scale Commodity Embedding for E-commerce Recommendation in Alibaba* (EGES). KDD. https://arxiv.org/abs/1803.02349
- Grbovic & Cheng (2018). *Real-time Personalization using Embeddings for Search Ranking at Airbnb*. KDD. https://doi.org/10.1145/3219819.3219885
- Pal et al. (2020). *PinnerSage: Multi-Modal User Embedding Framework for Recommendations at Pinterest*. KDD. https://arxiv.org/abs/2007.03634
- El-Kishky et al. (2022). *TwHIN: Embedding the Twitter Heterogeneous Information Network for Personalized Recommendation*. KDD. https://arxiv.org/abs/2202.05387
- Borisyuk et al. (2024). *LiGNN: Graph Neural Networks at LinkedIn*. KDD. https://arxiv.org/abs/2402.11139
- PyTorch Geometric — `LightGCN`: https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.nn.models.LightGCN.html y ejemplo `examples/lightgcn.py`.
- gensim Word2Vec: https://radimrehurek.com/gensim/models/word2vec.html
""")
nb.save(LESSON)

# ---------------------------------------------------------------------------
# PROYECTO
# ---------------------------------------------------------------------------
pj = Notebook("Proyecto 10 · LightGCN vs MF", colab_path=PROJECT, gpu=True)
pj.md(f"""
{pj.badge()}

# Proyecto 10 · Candidatos por grafo para CineMatch: LightGCN (PyG) vs MF

| | |
|---|---|
| **Nivel** | 🟠 Avanzado |
| **Duración** | 3 h |
| **GPU** | T4/L4 |
| **Unidades Colab** | ≈ 1–3 |
| **Prerrequisitos** | Lección 10 (y 05 para BPR) |
""")
pj.md(r"""
## 🏢 Contexto de negocio
El generador de candidatos de CineMatch es hoy un MF-BPR (módulo 05). El equipo de *growth* sospecha que los **usuarios nuevos o poco activos** reciben candidatos pobres.
Te piden evaluar si un **LightGCN** (propagación en grafo) mejora el *recall* de candidatos, sobre todo en la cola de usuarios poco activos, **sin** aumentar el coste de serving
(los embeddings se precalculan y se sirven con el mismo índice FAISS del módulo 08).

## 📦 Dataset
MovieLens-1M como feedback implícito. **Split temporal por usuario**: el último 20 % de las interacciones de cada usuario es test; del train, el último 10 % se usa como validación para elegir épocas/capas.

## ✅ Entregables y rúbrica
| Criterio | Objetivo |
|---|---|
| MF-BPR y LightGCN (PyG) entrenados con el **mismo** bucle, pérdida y presupuesto | obligatorio |
| Selección de K ∈ {1,2,3,4} y épocas por validación (no por test) | obligatorio |
| Mejora relativa de Recall@20 de LightGCN sobre MF en test | ≥ +3 % (orientativo; con MF bien regularizado puede ser menor: repórtalo honestamente) |
| Análisis por cuartil de actividad | gráfico + conclusión |
| Exportación de embeddings a un índice FAISS y latencia de top-100 | p50 < 5 ms por consulta en CPU |
""")
pj.code(PIP + "\n!pip install -q faiss-cpu")
pj.code(IMPORTS)
pj.md(UTILS_MD.replace("HR@K y NDCG@K con *full ranking*", "Recall@K y NDCG@K con *full ranking* y split temporal por usuario"))
pj.code(UTILS_LOAD)
pj.code(UTILS_TOPK)
pj.code(LOAD)
pj.code(r"""
# Validación: último 10 % del train de cada usuario
fit_df, val_df = temporal_user_split(train_df, test_frac=0.1)
val_df = val_df[val_df.i.isin(set(fit_df.i))]
R_fit, R_val = to_csr(fit_df, n_users, n_items), to_csr(val_df, n_users, n_items)
print(f"fit={R_fit.nnz:,}  val={R_val.nnz:,}  test={R_test.nnz:,}")
""")
pj.md(r"""
## Paso 1 · Grafo para PyG
Construye `edge_index` **no dirigido** (usuarios `0..n_users-1`, ítems desplazados `+ n_users`) a partir de una matriz CSR de entrenamiento.

<details><summary>🪜 Pista</summary><code>u, i = R.nonzero()</code>; las aristas usuario→ítem son <code>(u, i + n_users)</code>; para hacerlo no dirigido concatena también <code>(i + n_users, u)</code>. Devuelve además los pares positivos usuario→ítem por separado: los necesitarás para muestrear lotes de BPR.</details>
""")
pj.code(r"""
def build_edge_index(R):
    # TODO: devuelve (edge_index [2, 2*nnz] no dirigido, train_pairs [2, nnz] usuario->ítem desplazado)
    raise NotImplementedError
""")
pj.md(r"""
## Paso 2 · Entrenamiento común (MF y LightGCN)
Truco: **MF = LightGCN de PyG con `num_layers=0`**. Escribe una única función `fit(K, R_train, R_eval, epochs)` que entrene con `recommendation_loss` y devuelva el modelo y su historial de Recall@20 en `R_eval`.

<details><summary>🪜 Pista</summary>Por lote: toma pares positivos <code>pos</code> (2 × B), crea <code>neg</code> con el mismo usuario y un ítem aleatorio en <code>[n_users, n_users + n_items)</code>, puntúa ambos con <code>model(edge_index, torch.cat([pos, neg], 1)).chunk(2)</code> y llama a <code>model.recommendation_loss(pos_rank, neg_rank, node_id=...)</code> pasando los nodos del lote (<code>unique()</code>) para la regularización. Para evaluar, <code>model.get_embedding(edge_index)</code> y separa usuarios e ítems por el desplazamiento.</details>
""")
pj.code(r"""
def fit(K, R_train, R_eval, epochs=60, d=64, lr=2e-3, batch_size=8192, eval_every=10):
    # TODO
    raise NotImplementedError
""")
pj.md(r"""
## Paso 3 · Selección por validación, evaluación en test y análisis por actividad
1. Para K ∈ {0 (MF), 1, 2, 3, 4} entrena en `R_fit` y evalúa en `R_val`. 2. Elige K* y reentrena en `R_train` completo. 3. Evalúa en test MF vs LightGCN-K*. 4. Desglosa por cuartil de actividad.
""")
pj.code(r"""
# TODO: bucle de selección de K y tabla de resultados
...
""")
pj.md(r"""
## Paso 4 · Serving con FAISS
Exporta los embeddings de ítems a un `faiss.IndexFlatIP` y mide la latencia de top-100 para 1.000 usuarios (consulta a consulta).
""")
pj.code(r"""
# TODO: índice FAISS + medición de latencia p50/p99
...
""")

pj.md(r"""
---
# ⛔ SPOILER — Solución de referencia
""")
pj.code(r"""
from torch_geometric.nn import LightGCN as PyGLightGCN

def build_edge_index(R):
    coo = R.tocoo()
    src = torch.from_numpy(coo.row).long(); dst = torch.from_numpy(coo.col).long() + n_users
    return torch.stack([torch.cat([src, dst]), torch.cat([dst, src])]).to(device), torch.stack([src, dst]).to(device)

def pyg_score_fn(model, edge_index):
    with torch.no_grad():
        emb = model.get_embedding(edge_index)
    U, I = emb[:n_users], emb[n_users:]
    return (lambda u: U[u.to(device)] @ I.T), U, I

def fit(K, R_train, R_eval, epochs=60, d=64, lr=2e-3, batch_size=8192, eval_every=10):
    torch.manual_seed(seed)
    ei, pairs = build_edge_index(R_train)
    model = PyGLightGCN(num_nodes=n_users + n_items, embedding_dim=d, num_layers=K).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr); hist = collections.defaultdict(list)
    for ep in range(1, epochs + 1):
        model.train(); perm = torch.randperm(pairs.size(1), device=device)
        for b in range(0, len(perm), batch_size):
            pos = pairs[:, perm[b:b + batch_size]]
            neg = torch.stack([pos[0], torch.randint(n_users, n_users + n_items, (pos.size(1),), device=device)])
            pr, nr = model(ei, torch.cat([pos, neg], 1)).chunk(2)
            loss = model.recommendation_loss(pr, nr, node_id=torch.cat([pos, neg], 1).unique())
            opt.zero_grad(); loss.backward(); opt.step()
        if ep % eval_every == 0 or ep == epochs:
            model.eval(); r = evaluate_topk(pyg_score_fn(model, ei)[0], R_train, R_eval)
            hist["epoch"].append(ep); hist["Recall@20"].append(r["Recall@20"])
    return model, ei, dict(hist)
""")
pj.code(r"""
EPOCHS = 3 if FAST_DEV_RUN else 60
EVAL_EVERY = 1 if FAST_DEV_RUN else 10
sel = {}
for K in [0, 1, 2, 3, 4]:
    _, _, h = fit(K, R_fit, R_val, epochs=EPOCHS, eval_every=EVAL_EVERY)
    best = int(np.argmax(h["Recall@20"]))
    sel[K] = {"best_epoch": h["epoch"][best], "val_Recall@20": h["Recall@20"][best]}
    print(K, sel[K])
sel_df = pd.DataFrame(sel).T; display(sel_df)
K_star = int(sel_df.loc[1:, "val_Recall@20"].idxmax())
print("K* =", K_star)
""")
pj.code(r"""
final, fitted = {}, {}
for name, K in [("MF-BPR", 0), (f"LightGCN K={K_star}", K_star)]:
    ep = int(sel_df.loc[K, "best_epoch"])
    model, ei, _ = fit(K, R_train, R_test, epochs=ep, eval_every=ep)
    fn, U, I = pyg_score_fn(model, ei)
    fitted[name] = (fn, U, I)
    final[name] = evaluate_topk(fn, R_train, R_test)
fd = pd.DataFrame(final).T; display(fd.round(4))
mf, lg = fd.iloc[0]["Recall@20"], fd.iloc[1]["Recall@20"]
print(f"Mejora relativa Recall@20: {100*(lg-mf)/mf:+.2f} %")
""")
pj.code(r"""
act = np.diff(R_train.indptr)
buckets = pd.qcut(act, 4, labels=["Q1 (poca)", "Q2", "Q3", "Q4 (mucha)"])
rows = []
for name, (fn, _, _) in fitted.items():
    for bk in buckets.categories:
        m = np.zeros(n_users, bool); m[np.where(buckets == bk)[0]] = True
        rows.append({"modelo": name, "cuartil": bk, **evaluate_topk(fn, R_train, R_test.multiply(m[:, None]).tocsr())})
bq = pd.DataFrame(rows)
piv = bq.pivot(index="cuartil", columns="modelo", values="Recall@20")
lg_name = [c for c in piv.columns if c.startswith("LightGCN")][0]
piv["mejora_%"] = 100 * (piv[lg_name] - piv["MF-BPR"]) / piv["MF-BPR"]
display(piv.round(4))
fig, ax = plt.subplots(figsize=(8, 3.6))
sns.barplot(data=bq, x="cuartil", y="Recall@20", hue="modelo", ax=ax); ax.set(title="Recall@20 por actividad"); plt.show()
""")
pj.code(r"""
import faiss
name_lg = [k for k in fitted if k.startswith("LightGCN")][0]
_, U, I = fitted[name_lg]
I_np = I.detach().float().cpu().numpy().astype("float32"); U_np = U.detach().float().cpu().numpy().astype("float32")
index = faiss.IndexFlatIP(I_np.shape[1]); index.add(I_np)
lat = []
for u in np.random.default_rng(seed).choice(n_users, 1000):
    t0 = time.perf_counter(); index.search(U_np[u:u + 1], 100); lat.append((time.perf_counter() - t0) * 1e3)
print(f"FAISS top-100: p50 = {np.percentile(lat, 50):.3f} ms   p99 = {np.percentile(lat, 99):.3f} ms  (ítems={len(I_np):,})")
""")
pj.md(r"""
**Lectura esperada.** LightGCN suele mejorar más en los cuartiles de **poca actividad** (Q1–Q2), que toman prestada señal de vecinos a 2–3 saltos; en Q4 la diferencia es pequeña.
El coste de serving no cambia: siguen siendo dos tablas de embeddings y un producto escalar en FAISS. El coste extra está **offline** (propagación en el entrenamiento).

## 🚀 Retos extra
1. **Nodos de género** (grafo heterogéneo plano): añade los géneros como nodos extra conectados a sus películas y vuelve a medir Recall@20 en ítems poco populares.
2. **LightGCN post-hoc**: entrena MF y aplica la propagación $\frac{1}{K+1}\sum_k \hat A^k E$ **sólo en inferencia**. ¿Cuánta ganancia recupera sin coste de entrenamiento?
3. **GF-CF** (Shen et al. 2021): implementa el filtro lineal sin entrenamiento sobre $\tilde R^\top \tilde R$ y compáralo.
4. **Negativos duros**: muestrea la mitad de los negativos del top-100 del propio modelo (estilo *curriculum* de PinSage).
5. **Escala**: MovieLens-32M en A100 con `torch_geometric` + `NeighborLoader` en lugar de propagación completa.

## 🤔 Reflexión (producción / MLOps)
- Los embeddings de LightGCN dependen de **todo el grafo**: si reentrenas cada noche, ¿cómo evitas que el índice FAISS «salte» y cambien los candidatos de todos los usuarios (*embedding drift*, módulo 17)?
- ¿Qué harías con un usuario que se registró hace 10 minutos? (pista: DeepWalk/item2vec sobre su sesión, módulo 09, o features inductivas tipo PinSage).
""")
pj.save(PROJECT)
