"""Builder del módulo 08 · Deep retrieval (two-tower) y ANN.

Ejecutar desde la raíz del repo:  python recsys-course/_tools/builders/build_08.py
"""
import os
import sys

sys.path.insert(0, "recsys-course/_tools")
sys.path.insert(0, "recsys-course/_tools/builders")
from nbbuild import Notebook  # noqa: E402
from b3_common import header, ML_UTILS_MD, ML_UTILS_CODE, DRAW_CODE, SETUP_CODE  # noqa: E402

MOD = "08_deep_retrieval_ann"
os.makedirs(f"recsys-course/{MOD}", exist_ok=True)

DATA_CODE = r'''
# === Datos para retrieval: secuencias, ejemplos (historia → siguiente ítem) y conjuntos de evaluación
from numpy.lib.stride_tricks import sliding_window_view
ratings, movies, users = load_movielens(SCALE)
movies = movies[movies.item_id.isin(ratings.item_id.unique())].reset_index(drop=True)
imap = {v: i + 1 for i, v in enumerate(movies.item_id)}            # 0 = padding
ratings = ratings[ratings.item_id.isin(imap)].copy(); ratings["iid"] = ratings.item_id.map(imap)
N_ITEMS = len(movies)
GENRES = sorted({g for gs in movies.genres for g in gs.split("|")})
ITEM_G = np.zeros((N_ITEMS + 1, len(GENRES)), np.float32)
for j, g in enumerate(GENRES):
    ITEM_G[1:, j] = movies.genres.str.contains(g, regex=False).values
years = movies.title.str.extract(r"\((\d{4})\)\s*$")[0].astype(float).fillna(1990).values
ITEM_Y = np.zeros(N_ITEMS + 1, np.int64); ITEM_Y[1:] = np.clip((years - 1910) // 5, 0, 22).astype(int) + 1
TITLE = np.array(["<pad>"] + movies.title.tolist(), dtype=object)
MAIN_GENRE = np.array(["<pad>"] + movies.genres.str.split("|").str[0].tolist(), dtype=object)

# Features demográficas (solo existen en ML-1M)
n_users_max = int(ratings.user_id.max()) + 1
UCAT = np.zeros((n_users_max, 3), np.int64)
if users is not None:
    u = users.set_index("user_id")
    UCAT[u.index, 0] = (u.gender == "F").astype(int).values + 1
    UCAT[u.index, 1] = pd.factorize(u.age, sort=True)[0] + 1
    UCAT[u.index, 2] = u.occupation.astype(int).values + 1
UCAT_DIMS = tuple(int(UCAT[:, j].max()) + 1 for j in range(3))

train, val, test = temporal_split(ratings)
H = 50
def sequences(df):
    return df.sort_values(["user_id", "timestamp"]).groupby("user_id").iid.apply(np.array).to_dict()

def train_examples(seqs, max_examples=None, seed=42):
    Hs, T, U = [], [], []
    for u, s in seqs.items():
        if len(s) < 2: continue
        w = sliding_window_view(np.concatenate([np.zeros(H, s.dtype), s]), H)[1:len(s)]   # historia ANTES de cada evento
        Hs.append(w); T.append(s[1:]); U.append(np.full(len(s) - 1, u))
    Hs, T, U = np.concatenate(Hs), np.concatenate(T), np.concatenate(U)
    if max_examples and len(T) > max_examples:
        i = np.random.default_rng(seed).choice(len(T), max_examples, replace=False); Hs, T, U = Hs[i], T[i], U[i]
    return Hs.astype(np.int64), T.astype(np.int64), U.astype(np.int64)

def eval_set(hist_df, target_df, max_users=None, seed=42):
    seqs = sequences(hist_df); truth = target_df.groupby("user_id").iid.agg(set)
    us = [u for u in truth.index if u in seqs]
    if max_users and len(us) > max_users:
        us = list(np.random.default_rng(seed).choice(us, max_users, replace=False))
    hist, seen, tr, uu = [], [], [], []
    for u in us:
        s = seqs[u]; t = truth[u] - set(s)
        if not t: continue
        h = s[-H:]; hist.append(np.pad(h, (H - len(h), 0))); seen.append(np.unique(s)); tr.append(t); uu.append(u)
    return {"hist": np.array(hist, np.int64), "ucat": UCAT[np.array(uu)], "seen": seen, "truth": tr, "users": np.array(uu)}

train_seqs = sequences(train)
Htr, Ttr, Utr = train_examples(train_seqs, max_examples=MAX_EXAMPLES)
EV_val = eval_set(train, val, MAX_EVAL_USERS)
EV_test = eval_set(pd.concat([train, val]), test, MAX_EVAL_USERS)
item_count = np.bincount(train.iid.values, minlength=N_ITEMS + 1).astype(np.float64)
print(f"{N_ITEMS} ítems | {len(Ttr):,} ejemplos de train | usuarios eval: val={len(EV_val['users'])}, test={len(EV_test['users'])}")
'''

MODEL_CODE = r'''
# === Two-tower desde cero ====================================================
class TwoTower(nn.Module):
    def __init__(self, n_items, n_genres, n_years=24, ucat_dims=(3, 8, 22), d=64):
        super().__init__()
        self.item_id = nn.Embedding(n_items + 1, d, padding_idx=0)        # tabla COMPARTIDA (ítem e historia)
        nn.init.normal_(self.item_id.weight, std=0.05)
        self.genre = nn.Linear(n_genres, d, bias=False)
        self.year = nn.Embedding(n_years, d)
        self.item_mlp = nn.Sequential(nn.Linear(d, 256), nn.ReLU(), nn.Linear(256, d))
        self.ucat = nn.ModuleList([nn.Embedding(c, d) for c in ucat_dims])
        self.user_mlp = nn.Sequential(nn.Linear(2 * d, 256), nn.ReLU(), nn.Linear(256, d))
        self.register_buffer("G", torch.as_tensor(ITEM_G)); self.register_buffer("Y", torch.as_tensor(ITEM_Y))

    def item_vec(self, ids):
        x = self.item_id(ids) + self.genre(self.G[ids]) + self.year(self.Y[ids])
        return F.normalize(x + self.item_mlp(x), dim=-1)                  # residual + L2 → coseno

    def user_vec(self, hist, ucat):
        m = (hist > 0).float().unsqueeze(-1)
        h = (self.item_id(hist) * m).sum(1) / m.sum(1).clamp(min=1)       # media de la historia
        demo = sum(e(ucat[:, j]) for j, e in enumerate(self.ucat))
        x = torch.cat([h, demo], -1)
        return F.normalize(self.user_mlp(x), dim=-1)

@torch.no_grad()
def all_item_vecs(model, bs=8192):
    model.eval()
    ids = torch.arange(1, N_ITEMS + 1, device=device)
    V = torch.cat([model.item_vec(ids[i:i + bs]) for i in range(0, len(ids), bs)])
    return torch.cat([torch.zeros(1, V.size(1), device=device), V])     # fila 0 = padding

@torch.no_grad()
def retrieve(model, EV, k=100, V=None, bs=1024):
    V = all_item_vecs(model) if V is None else V
    out = []
    for i in range(0, len(EV["hist"]), bs):
        u = model.user_vec(torch.as_tensor(EV["hist"][i:i + bs], device=device), torch.as_tensor(EV["ucat"][i:i + bs], device=device))
        s = u @ V.T; s[:, 0] = -1e9
        for r, seen in enumerate(EV["seen"][i:i + bs]):
            s[r, torch.as_tensor(seen, device=device)] = -1e9                 # filtrar ya vistos
        out.append(s.topk(k, dim=1).indices.cpu().numpy())
    return np.concatenate(out)

def evaluate(topk, EV):
    return {"Recall@10": recall_at_k(topk, EV["truth"], 10), "Recall@50": recall_at_k(topk, EV["truth"], 50),
            "Recall@100": recall_at_k(topk, EV["truth"], 100), "NDCG@10": ndcg_at_k(topk, EV["truth"], 10)}
'''

LOSS_CODE = r'''
# === Pérdida softmax con in-batch negatives, logQ, negativos uniformes (MNS) y hard negatives
LOG_P = torch.as_tensor(np.log((item_count + 1) / (item_count + 1).sum()), dtype=torch.float32)

def retrieval_loss(model, hist, ucat, pos, tau=0.05, logq=False, n_uniform=0, hard=None):
    B = pos.size(0)
    u = model.user_vec(hist, ucat); v = model.item_vec(pos)
    logits = u @ v.T / tau                                              # [B, B]: diagonal = positivos
    if logq:                                                            # Q(j) ≈ B·p_j (frecuencia en el stream)
        logits = logits - (LOG_P.to(pos.device)[pos] + math.log(B))[None, :]
    accidental = (pos[None, :] == pos[:, None]) & ~torch.eye(B, dtype=torch.bool, device=pos.device)
    logits = logits.masked_fill(accidental, -1e9)                       # el mismo ítem en otra fila NO es negativo
    cols = [logits]
    if n_uniform > 0:                                                   # Mixed Negative Sampling (Yang et al. 2020)
        neg = torch.randint(1, N_ITEMS + 1, (n_uniform,), device=pos.device)
        ln = u @ model.item_vec(neg).T / tau
        if logq:
            ln = ln - math.log(n_uniform / N_ITEMS)
        cols.append(ln.masked_fill(neg[None, :] == pos[:, None], -1e9))
    if hard is not None:                                                # un hard negative por fila
        lh = (u * model.item_vec(hard)).sum(-1, keepdim=True) / tau
        if logq:
            lh = lh - (LOG_P.to(pos.device)[hard] + math.log(B))[:, None]
        cols.append(lh.masked_fill((hard == pos)[:, None], -1e9))
    return F.cross_entropy(torch.cat(cols, 1), torch.arange(B, device=pos.device))

@torch.no_grad()
def mine_hard(model, u_hist, u_cat, pos, V, lo=20, hi=100):
    """Hard negatives estilo EBR (Facebook 2020): un ítem al azar entre los puestos [lo, hi) del modelo actual."""
    u = model.user_vec(u_hist, u_cat)
    s = u @ V.T; s[:, 0] = -1e9; s[torch.arange(len(pos)), pos] = -1e9
    top = s.topk(hi, dim=1).indices[:, lo:]
    return top[torch.arange(len(pos)), torch.randint(0, hi - lo, (len(pos),), device=pos.device)]

def train_two_tower(cfg: dict, epochs=None, bs=None, lr=1e-3, verbose=True, eval_on=None):
    epochs = epochs or EPOCHS; bs = bs or BATCH
    torch.manual_seed(seed)
    model = TwoTower(N_ITEMS, len(GENRES), ucat_dims=UCAT_DIMS).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    Hs, Ts = torch.as_tensor(Htr, device=device), torch.as_tensor(Ttr, device=device)
    Uc = torch.as_tensor(UCAT[Utr], device=device)
    hist_log = []
    for ep in range(epochs):
        model.train(); perm = torch.randperm(len(Ts), device=device); run, n = 0.0, 0
        use_hard = cfg.get("hard", False) and ep >= 1                    # warm-up de 1 época sin hard negatives
        V = all_item_vecs(model) if use_hard else None
        model.train()
        for s0 in range(0, len(Ts), bs):
            i = perm[s0:s0 + bs]
            hard = mine_hard(model, Hs[i], Uc[i], Ts[i], V) if use_hard else None
            loss = retrieval_loss(model, Hs[i], Uc[i], Ts[i], tau=cfg.get("tau", 0.05), logq=cfg.get("logq", False),
                                  n_uniform=cfg.get("n_uniform", 0), hard=hard)
            opt.zero_grad(set_to_none=True); loss.backward(); opt.step()
            run += loss.item(); n += 1
        rec = {"época": ep + 1, "loss": run / n}
        if eval_on is not None:
            rec.update(evaluate(retrieve(model, eval_on), eval_on))
        hist_log.append(rec)
        if verbose: print("  ", {k: round(v, 4) if isinstance(v, float) else v for k, v in rec.items()})
    return model, pd.DataFrame(hist_log)
'''


def build_lesson():
    nb = Notebook("Módulo 08 · Deep retrieval y ANN", colab_path=f"recsys-course/{MOD}/{MOD}.ipynb", gpu=True)
    header(nb, "08", "Candidate generation profunda: two-tower, negativos y búsqueda ANN con FAISS",
           "🟠 Avanzado", "6 h", "L4 o A100 (T4 suficiente con FAST_DEV_RUN; A100 para ML-25M)",
           "~4 (ML-1M) · ~15–25 (ML-25M, `SCALE='25m'`)",
           "01, 02, 05 (MF/BPR), 06 (embeddings de features)")
    nb.md(r"""
## 🎯 Objetivos de aprendizaje
1. **Explicar** por qué el retrieval necesita modelos *factorizados* (score = producto escalar) y cómo eso habilita la búsqueda aproximada (ANN).
2. **Derivar** la softmax muestreada, el sesgo de los *in-batch negatives* y la **corrección logQ** (Yi et al., 2019).
3. **Implementar en PyTorch** un two-tower con in-batch negatives, logQ, *mixed negative sampling* y *hard negatives*, y **medir** su efecto en Recall@K y en el sesgo de popularidad.
4. **Implementar** el estimador de frecuencias en streaming de Yi et al. (2019).
5. **Construir y comparar** índices FAISS (Flat, IVF, IVF-PQ, HNSW) con curvas **recall vs latencia** y memoria.
6. **Servir** top-K en milisegundos con filtrado de vistos y **elegir** entre FAISS, ScaNN, hnswlib y bases vectoriales (Milvus, Qdrant, Weaviate, pgvector, Vespa).
""")
    nb.md(r"""
## 💡 1. Intuición: ¿por qué un modelo especial para retrieval?
El ranker del módulo 06 mira **cada par** (usuario, ítem) con cruces de features: si el catálogo tiene $10^6$ ítems y el presupuesto es ~10 ms, no hay forma de puntuarlos todos. El retrieval necesita una forma de score que permita **pre-calcular** la mitad del trabajo:

$$s(u, i) = \langle \mathbf q(u), \mathbf v(i)\rangle$$

- $\mathbf v(i)$ (torre de ítem) se calcula **offline** para todo el catálogo y se indexa.
- $\mathbf q(u)$ (torre de usuario) se calcula **una vez por petición**.
- Encontrar los $K$ mayores productos escalares es *Maximum Inner Product Search* (MIPS), que los índices ANN resuelven en **sub-lineal** (ms para $10^6$–$10^9$ vectores).

Es la misma idea que la factorización matricial del módulo 05 ($\hat r_{ui}=\mathbf p_u^\top\mathbf q_i$), pero cada torre es una **red** que puede usar cualquier feature (historia, demografía, géneros, texto, imágenes) → resuelve el *cold start* de ítems con contenido y generaliza a usuarios nuevos.

Analogía con lo que ya conoces de LLMs/agentes: es exactamente un **bi-encoder de RAG** (consulta y documento se codifican por separado y se busca en una base vectorial). El ranker es el **cross-encoder** que reordena.
""")
    nb.code(r'''
!pip install -q faiss-cpu hnswlib   # GPU opcional: faiss-gpu-cu12 (ver sección 5)
''')
    nb.code(SETUP_CODE)
    nb.code(DRAW_CODE)
    nb.code(r'''
# Diagrama 1 — Two-tower vs ranker (cross) y YouTube DNN (2016)
fig, axes = plt.subplots(1, 3, figsize=(17, 5.2))
tt = {"uf": (0.3, 0.3, 4, 1, "features usuario\n(historia, demografía)", "in"), "if": (5.6, 0.3, 4, 1, "features ítem\n(id, géneros, año)", "in"),
      "ut": (0.3, 2.1, 4, 1.4, "Torre usuario\nMLP → q(u)", "mlp"), "it": (5.6, 2.1, 4, 1.4, "Torre ítem\nMLP → v(i)", "mlp"),
      "dot": (3.2, 4.5, 3.6, 1, "⟨q(u), v(i)⟩ / τ", "out"), "ann": (5.6, 6.3, 4, 1, "v(i) pre-calculados\n→ índice ANN", "gate")}
draw_blocks(axes[0], tt, [("uf", "ut"), ("if", "it"), ("ut", "dot"), ("it", "dot"), ("it", "ann")], "Two-tower (retrieval)", ylim=(0, 7.6))
cr = {"x": (1.5, 0.3, 7, 1, "features usuario + ítem + contexto + CRUCES", "in"), "m": (2.5, 2.3, 5, 2, "Red profunda\n(DCN, DIN, MMoE…)", "mlp"),
      "o": (3.5, 5.0, 3, 1, "p̂(clic)", "out")}
draw_blocks(axes[1], cr, [("x", "m"), ("m", "o")], "Ranker (módulos 06-07): O(n) pasadas", ylim=(0, 7.6))
axes[1].text(5, 6.6, "imposible para 10⁶ ítems en 10 ms", ha="center", color="#c44e52", fontsize=9)
yt = {"w": (0.2, 0.3, 3, 1, "media emb.\nvídeos vistos", "emb"), "s": (3.4, 0.3, 3, 1, "media emb.\nbúsquedas", "emb"),
      "g": (6.6, 0.3, 3.2, 1, "geo, edad, género,\n'example age'", "in"),
      "r": (2, 2.2, 6, 1.6, "ReLU → ReLU → ReLU", "mlp"), "u": (3, 4.4, 4, 0.9, "vector usuario u", "out"),
      "sm": (0.2, 6.1, 4.4, 1, "train: softmax\nsobre millones de vídeos", "inter"), "nn": (5.4, 6.1, 4.4, 1, "serving: vecinos\nmás cercanos (ANN)", "gate")}
draw_blocks(axes[2], yt, [("w", "r"), ("s", "r"), ("g", "r"), ("r", "u"), ("u", "sm"), ("u", "nn")], "YouTube DNN (Covington et al., 2016)", ylim=(0, 7.6))
plt.tight_layout(); plt.show()
''')

    nb.md(r"""
## 📐 2. Teoría formal

### 2.1 Retrieval como clasificación extrema
Con $\mathcal I$ el catálogo y temperatura $\tau$:
$$P(i\mid u) = \frac{\exp(s(u,i)/\tau)}{\sum_{j\in\mathcal I}\exp(s(u,j)/\tau)},\qquad \mathcal L = -\log P(i^+\mid u)$$
El denominador cuesta $O(|\mathcal I|)$ por ejemplo → **softmax muestreada**: usar solo un subconjunto de negativos $\mathcal N$ muestreados con una distribución $Q$. El estimador es sesgado salvo que **corrijamos los logits** (Bengio & Senécal, 2008; Jean et al., 2015):
$$s^c(u,j) = s(u,j) - \log Q(j)$$

### 2.2 In-batch negatives y su sesgo
El truco más barato: en un batch de $B$ pares (usuario, ítem positivo), usar los **positivos de los demás** como negativos → matriz $B\times B$, un solo *matmul*. Pero los ítems del batch se muestrean con probabilidad proporcional a su **frecuencia** $p_j$: los populares aparecen como negativos muchísimo más → el modelo aprende a **penalizar la popularidad** de más… o, visto al revés, el logit absorbe $\log p_j$. **Corrección logQ** (Yi et al., Google/YouTube, RecSys 2019):
$$s^c(u,j) = \frac{\langle \mathbf q(u), \mathbf v(j)\rangle}{\tau} - \log(B\,p_j)$$
(aplicada también al positivo). En serving se usa el score **sin** corregir.

**Estimación de $p_j$ en streaming** (Yi et al., 2019, Alg. 2): con dos arrays hasheados $A$ (último paso en que se vio $j$) y $D$ (intervalo medio estimado entre apariciones), en el paso $t$:
$$D[h(j)] \leftarrow (1-\alpha)\,D[h(j)] + \alpha\,(t - A[h(j)]),\qquad A[h(j)]\leftarrow t,\qquad \hat p_j = 1/D[h(j)]\ \text{(por paso)}$$

### 2.3 Mixed Negative Sampling y hard negatives
- **MNS** (Yang et al., Google, WWW 2020): añadir $B'$ negativos **uniformes** del catálogo a los in-batch. Los ítems de la cola larga (o nuevos) casi nunca salen en el batch; sin MNS el modelo no aprende a rechazarlos. Corrección: $-\log(B'/|\mathcal I|)$ para esa parte.
- **Hard negatives** (Huang et al., *Embedding-based Retrieval in Facebook Search*, KDD 2020): negativos que el modelo actual pone **cerca pero no arriba** (p. ej. puestos 101–500). Mezclados con negativos fáciles; usar solo los más duros empeora (muchos son **falsos negativos**: ítems que le gustarían al usuario pero no vio).
- **Temperatura**: con embeddings L2-normalizados, $\tau$ pequeña afila la softmax y enfatiza los negativos duros (Wang & Liu, 2021).
""")
    nb.code(r'''
# Gráfico 2 — Por qué el in-batch sampling sesga: frecuencia de aparición como negativo vs uniforme
rng_ = np.random.default_rng(0)
N = 2000
p = 1 / np.arange(1, N + 1) ** 1.0; p /= p.sum()                       # Zipf: popularidad típica
B = 512
inbatch = np.zeros(N)
for _ in range(400):
    inbatch += np.bincount(rng_.choice(N, B, p=p), minlength=N)
uniform = np.full(N, 400 * B / N)
fig, axes = plt.subplots(1, 2, figsize=(12, 3.6))
axes[0].loglog(np.arange(1, N + 1), inbatch, ".", ms=3, label="in-batch (∝ popularidad)")
axes[0].loglog(np.arange(1, N + 1), uniform, "-", label="uniforme (MNS)"); axes[0].legend()
axes[0].set_xlabel("rango de popularidad del ítem"); axes[0].set_ylabel("veces que es negativo"); axes[0].set_title("¿Quién hace de negativo?")
axes[1].semilogx(np.arange(1, N + 1), -np.log(B * p), color="#c44e52")
axes[1].set_xlabel("rango de popularidad"); axes[1].set_ylabel("−log(B·pⱼ)"); axes[1].set_title("Corrección logQ: más bonus a la cola larga")
plt.tight_layout(); plt.show()
''')

    nb.md(r"""
## 🧪 3. Datos: MovieLens (CineMatch)
- `SCALE = "1m"` (por defecto) o `"25m"` (A100 recomendada; sin demografía).
- **Ejemplos de entrenamiento** = (historia de las últimas $H=50$ películas **antes** del evento, película siguiente) para cada evento del periodo de train → como YouTube DNN, predecimos el *siguiente* visionado usando solo el pasado (evita fuga).
- **Evaluación**: usuarios con actividad en val/test; su estado = historia hasta el corte; relevantes = películas que verán después (no vistas antes). Recall@K y NDCG@K **sobre el catálogo completo** (nada de *sampled metrics*, módulo 02) filtrando vistas.
""")
    nb.md(ML_UTILS_MD)
    nb.code(ML_UTILS_CODE)
    nb.code(r'''
FAST_DEV_RUN = True
SCALE = "1m"                                   # "25m" en A100
MAX_EXAMPLES = 300_000 if FAST_DEV_RUN else None
MAX_EVAL_USERS = 2000 if FAST_DEV_RUN else 20000
EPOCHS = 3 if FAST_DEV_RUN else 8
BATCH = 1024 if FAST_DEV_RUN else 4096         # más batch = más in-batch negatives (y mejor en GPU)
''')
    nb.code(DATA_CODE)
    nb.md(r"""
## 🛠️ 4. Two-tower desde cero
- **Torre de ítem**: embedding de ID + proyección de géneros + embedding de quinquenio → MLP residual → L2.
- **Torre de usuario**: media de los embeddings de ID de su historia (tabla **compartida** con la torre de ítem: ayuda mucho con pocos datos) + demografía → MLP → L2.
- **Pérdida**: softmax sobre in-batch negatives con máscara de *accidental hits* (si el mismo ítem es positivo de dos filas, no puede ser negativo de sí mismo) + opciones logQ / MNS / hard negatives.
""")
    nb.code(MODEL_CODE)
    nb.code(r'''
# Baseline de popularidad (módulo 01) para tener una referencia
pop_rank = np.argsort(-item_count)
def popularity_topk(EV, k=100):
    out = []
    for seen in EV["seen"]:
        s = set(seen); out.append([i for i in pop_rank[:k + len(s) + 1] if i not in s and i != 0][:k])
    return np.array(out)
results = {"Popularidad": evaluate(popularity_topk(EV_test), EV_test)}
results["Popularidad"]
''')
    nb.code(LOSS_CODE)
    nb.code(r'''
VARIANTS = {
    "In-batch": dict(logq=False),
    "In-batch + logQ": dict(logq=True),
    "MNS (in-batch + uniformes) + logQ": dict(logq=True, n_uniform=512),
    "MNS + logQ + hard negatives": dict(logq=True, n_uniform=512, hard=True),
}
tt_models, tt_hist = {}, {}
for name, cfg in VARIANTS.items():
    print("▶", name); t0 = time.time()
    tt_models[name], tt_hist[name] = train_two_tower(cfg, eval_on=EV_val)
    results[name] = evaluate(retrieve(tt_models[name], EV_test), EV_test)
    print(f"   test: { {k: round(v, 4) for k, v in results[name].items()} }  ({time.time()-t0:.0f}s)")
pd.DataFrame(results).T.round(4)
''')
    nb.code(r'''
fig, axes = plt.subplots(1, 3, figsize=(17, 4))
for name, h in tt_hist.items():
    axes[0].plot(h["época"], h["loss"], "o-", label=name); axes[1].plot(h["época"], h["Recall@100"], "o-", label=name)
axes[0].set_title("Pérdida de entrenamiento (no comparable entre variantes: distinto nº de negativos)"); axes[0].legend(fontsize=7)
axes[1].set_title("Recall@100 en validación"); axes[1].set_xlabel("época")
r = pd.DataFrame(results).T
r[["Recall@10", "Recall@50", "Recall@100"]].plot.bar(ax=axes[2], rot=20); axes[2].set_title("Recall@K en test (catálogo completo)")
axes[2].tick_params(axis="x", labelsize=7)
plt.tight_layout(); plt.show()
''')
    nb.md(r"""
### 🧪 4.1 ¿Qué hace logQ con la popularidad?
Dividimos los ítems relevantes de test en **cabeza** (20 % más popular en train), **torso** y **cola**, y medimos el recall en cada grupo, además de la popularidad media de lo que recomienda cada modelo.
""")
    nb.code(r'''
pct = np.argsort(np.argsort(-item_count)) / N_ITEMS                    # 0 = el más popular
bucket = np.where(pct < 0.2, "cabeza", np.where(pct < 0.6, "torso", "cola"))
rows = []
for name in ["Popularidad"] + list(VARIANTS):
    topk = popularity_topk(EV_test) if name == "Popularidad" else retrieve(tt_models[name], EV_test)
    for b in ["cabeza", "torso", "cola"]:
        tr_b = [{i for i in t if bucket[i] == b} for t in EV_test["truth"]]
        rows.append({"modelo": name, "grupo": b, "Recall@100": recall_at_k(topk, tr_b, 100)})
    rows.append({"modelo": name, "grupo": "percentil pop. medio recomendado", "Recall@100": float(pct[topk[:, :10]].mean())})
pb = pd.DataFrame(rows).pivot(index="modelo", columns="grupo", values="Recall@100")
fig, axes = plt.subplots(1, 2, figsize=(14, 4))
pb[["cabeza", "torso", "cola"]].plot.bar(ax=axes[0], rot=15); axes[0].set_title("Recall@100 por grupo de popularidad"); axes[0].tick_params(axis="x", labelsize=7)
pb["percentil pop. medio recomendado"].plot.barh(ax=axes[1], color="#8172b2")
axes[1].set_title("Percentil de popularidad medio del top-10 (0 = más popular)")
plt.tight_layout(); plt.show()
pb.round(4)
''')
    nb.md(r"""
### 🧪 4.2 Estimador de frecuencia en streaming (Yi et al., 2019)
En producción no hay "conteo total": el stream es infinito y el catálogo cambia. Implementamos el estimador con arrays hasheados y lo comparamos con la frecuencia real.
""")
    nb.code(r'''
class StreamingFrequency:
    """Estima p_j a partir del intervalo medio entre apariciones (Yi et al. 2019, Alg. 2)."""
    def __init__(self, n_buckets=2 ** 16, alpha=0.01):
        self.A = np.zeros(n_buckets); self.D = np.full(n_buckets, 1e6); self.alpha, self.n = alpha, n_buckets
    def update(self, ids: np.ndarray, t: int):
        h = ids % self.n                                                 # en producción: hash(id)
        self.D[h] = (1 - self.alpha) * self.D[h] + self.alpha * (t - self.A[h])
        self.A[h] = t
    def prob(self, ids, batch_size):
        return 1.0 / (self.D[ids % self.n] * batch_size)                 # D está en pasos → prob. por ejemplo

est = StreamingFrequency(alpha=0.02)
order = np.argsort(train.timestamp.values); stream = train.iid.values[order]
bs_ = 256
for t, s0 in enumerate(range(0, len(stream), bs_), start=1):
    est.update(np.unique(stream[s0:s0 + bs_]), t)
p_true = item_count[1:] / item_count.sum(); p_hat = est.prob(np.arange(1, N_ITEMS + 1), bs_)
ok = item_count[1:] >= 5
plt.figure(figsize=(5, 4.5)); plt.loglog(p_true[ok], p_hat[ok], ".", ms=3, alpha=0.5); lim = [p_true[ok].min(), p_true[ok].max()]
plt.plot(lim, lim, "k--", lw=0.8); plt.xlabel("frecuencia real pⱼ"); plt.ylabel("estimación streaming p̂ⱼ")
plt.title(f"Estimador streaming (corr. log-log = {np.corrcoef(np.log(p_true[ok]), np.log(p_hat[ok]))[0,1]:.2f})"); plt.show()
''')
    nb.md(r"""
> La estimación es buena para ítems frecuentes y ruidosa en la cola (y sesgada si la popularidad cambia con el tiempo; eso es una *ventaja*: sigue la tendencia). Con IDs **hasheados**, dos ítems que comparten cubo comparten estimación: otro sitio donde aparecen colisiones (módulo 06).

### 🧪 4.3 Temperatura
""")
    nb.code(r'''
taus = [0.02, 0.05, 0.2] if FAST_DEV_RUN else [0.01, 0.02, 0.05, 0.1, 0.2, 0.5]
tau_res = []
for tau in taus:
    m, _ = train_two_tower(dict(logq=True, tau=tau), epochs=max(1, EPOCHS - 1), verbose=False)
    tau_res.append({"tau": tau, **evaluate(retrieve(m, EV_val), EV_val)})
tr_ = pd.DataFrame(tau_res)
plt.figure(figsize=(6, 3.4)); plt.semilogx(tr_.tau, tr_["Recall@100"], "o-"); plt.semilogx(tr_.tau, tr_["Recall@10"], "s-")
plt.legend(["Recall@100", "Recall@10"]); plt.xlabel("temperatura τ"); plt.title("Sensibilidad a la temperatura (validación)"); plt.show()
''')
    nb.code(r'''
# Gráfico — t-SNE de los embeddings de ítem coloreados por género principal
from sklearn.manifold import TSNE
best_name = max(VARIANTS, key=lambda n: results[n]["Recall@100"])
V = all_item_vecs(tt_models[best_name]).cpu().numpy()[1:]
top_items = np.argsort(-item_count[1:])[:1500]
Z = TSNE(n_components=2, perplexity=30, init="pca", random_state=seed).fit_transform(V[top_items])
g = MAIN_GENRE[1:][top_items]; main = pd.Series(g).value_counts().index[:8]
plt.figure(figsize=(8, 6.5))
for gg in main:
    m = g == gg; plt.scatter(Z[m, 0], Z[m, 1], s=6, label=gg)
plt.legend(markerscale=3, fontsize=8); plt.title(f"t-SNE de v(i) — {best_name} (1 500 ítems más populares)"); plt.axis("off"); plt.show()
''')

    # ------------------------------- ANN ---------------------------------
    nb.md(r"""
## 🔎 5. Búsqueda aproximada (ANN) con FAISS

Para servir necesitamos $\text{top-}K_i\langle \mathbf q, \mathbf v_i\rangle$ en milisegundos. Con embeddings L2-normalizados, producto escalar = coseno, y MIPS = vecino más cercano. Familias de índices (Johnson et al., 2017; Douze et al., 2024):

| Índice | Idea | Memoria/vector (d=64) | Cuándo |
|---|---|---|---|
| `IndexFlatIP` | fuerza bruta exacta | 256 B | < ~10⁶ vectores en GPU, *ground truth* |
| `IndexIVFFlat` | k-means en `nlist` celdas; se buscan las `nprobe` más cercanas | 256 B + ids | 10⁶–10⁸, buen equilibrio |
| `IndexIVFPQ` | IVF + **Product Quantization**: el vector se parte en `m` trozos y cada trozo se guarda como el id (8 bits) de su centroide | `m` B (¡16 B!) | 10⁸–10⁹, memoria limitada |
| `IndexHNSWFlat` | grafo navegable de pequeño mundo jerárquico (Malkov & Yashunin) | 256 B + grafo (~2·M·4 B) | latencia mínima en CPU, recall alto |

Los parámetros **de búsqueda** (`nprobe`, `efSearch`) mueven el punto en la curva **recall vs latencia** sin reconstruir el índice: es la palanca operativa del equipo de serving.
""")
    nb.code(r'''
# Diagramas 3 — IVF (celdas de Voronoi + nprobe), PQ y HNSW
from sklearn.cluster import KMeans
rng_ = np.random.default_rng(3)
P2 = np.concatenate([rng_.normal(c, 0.6, (120, 2)) for c in rng_.uniform(-4, 4, (10, 2))])
km = KMeans(12, n_init=3, random_state=0).fit(P2)
xx, yy = np.meshgrid(np.linspace(-6, 6, 300), np.linspace(-6, 6, 300))
cell = km.predict(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)
q = np.array([0.5, 1.0]); probe = np.argsort(((km.cluster_centers_ - q) ** 2).sum(1))[:3]
fig, axes = plt.subplots(1, 3, figsize=(17, 5))
axes[0].contourf(xx, yy, np.isin(cell, probe), levels=[-0.5, 0.5, 1.5], colors=["#f4f4f4", "#fde2b8"])
axes[0].contour(xx, yy, cell, levels=np.arange(13) - 0.5, colors="#999", linewidths=0.5)
axes[0].scatter(P2[:, 0], P2[:, 1], s=3, c="#4c72b0"); axes[0].scatter(*km.cluster_centers_.T, c="k", marker="x")
axes[0].scatter(*q, c="#c44e52", s=120, marker="*"); axes[0].set_title("IVF: solo se exploran nprobe=3 celdas (naranja)"); axes[0].axis("off")
ax = axes[1]; ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 6); ax.set_title("Product Quantization (m=4 sub-vectores)")
cols = ["#dbe9f6", "#c6e2c3", "#fde2b8", "#f6c9c9"]
for j in range(16):
    ax.add_patch(plt.Rectangle((0.5 + j * 0.55, 4.2), 0.5, 0.8, fc=cols[j // 4], ec="#555"))
ax.text(5, 5.3, "vector v ∈ ℝ⁶⁴ (64 floats = 256 bytes)", ha="center")
for s in range(4):
    ax.annotate("", xy=(1.6 + s * 2.2, 2.3), xytext=(1.3 + s * 2.2, 4.1), arrowprops=dict(arrowstyle="->"))
    ax.add_patch(plt.Rectangle((1.0 + s * 2.2, 1.4), 1.4, 0.8, fc=cols[s], ec="#555")); ax.text(1.7 + s * 2.2, 1.8, f"id {rng_.integers(256)}", ha="center", fontsize=9)
ax.text(5, 0.7, "código = 4 bytes · cada id apunta a 1 de 256 centroides del sub-espacio", ha="center", fontsize=9)
ax = axes[2]; ax.axis("off"); ax.set_title("HNSW: búsqueda voraz de capas dispersas a densas")
for layer, (n, yb) in enumerate([(40, 0), (12, 2.2), (4, 4.4)]):
    pts = np.c_[rng_.uniform(0, 10, n), yb + rng_.uniform(0, 1.2, n)]
    for i in range(n):
        for j in np.argsort(((pts - pts[i]) ** 2).sum(1))[1:3]:
            ax.plot(*pts[[i, j]].T, c="#bbb", lw=0.6)
    ax.scatter(*pts.T, s=12, c=["#4c72b0", "#55a868", "#c44e52"][layer]); ax.text(-0.5, yb + 0.5, f"capa {layer}", ha="right", fontsize=8)
ax.set_xlim(-2, 10.5)
plt.tight_layout(); plt.show()
''')
    nb.code(r'''
import faiss
faiss.omp_set_num_threads(1)                    # latencia "por consulta" comparable (1 hilo)
N_CORPUS = 200_000 if FAST_DEV_RUN else 2_000_000
rng_ = np.random.default_rng(seed)
# Corpus grande realista: los vectores de las películas + "variantes" (episodios, ediciones, clips) alrededor
i1, i2 = rng_.integers(0, len(V), N_CORPUS), rng_.integers(0, len(V), N_CORPUS)
w_ = rng_.uniform(0.5, 1.0, (N_CORPUS, 1))                              # mezcla de dos títulos + ruido
corpus = w_ * V[i1] + (1 - w_) * V[i2] + rng_.normal(0, 0.5 / np.sqrt(V.shape[1]), (N_CORPUS, V.shape[1]))
corpus = (corpus / np.linalg.norm(corpus, axis=1, keepdims=True)).astype(np.float32)
with torch.no_grad():
    m_best = tt_models[best_name]
    Q = m_best.user_vec(torch.as_tensor(EV_test["hist"][:1000], device=device), torch.as_tensor(EV_test["ucat"][:1000], device=device)).cpu().numpy().astype(np.float32)
d = corpus.shape[1]; K = 10
flat = faiss.IndexFlatIP(d); flat.add(corpus)
t0 = time.perf_counter(); _, GT = flat.search(Q, K); t_flat = (time.perf_counter() - t0) / len(Q) * 1e3
print(f"Corpus {corpus.shape} · Flat exacto: {t_flat:.3f} ms/consulta (1 hilo)")

def bench(index, param_name, values, label):
    rows = []
    for v in values:
        faiss.ParameterSpace().set_index_parameter(index, param_name, v)
        t0 = time.perf_counter(); _, I = index.search(Q, K); dt = (time.perf_counter() - t0) / len(Q) * 1e3
        rec = np.mean([len(set(a) & set(b)) / K for a, b in zip(I, GT)])
        rows.append({"índice": label, "param": f"{param_name}={v}", "recall@10": rec, "ms/consulta": dt})
    return rows
''')
    nb.code(r'''
bench_rows, build_info = [], {}
nlist = 1024 if FAST_DEV_RUN else 4096
q_ = faiss.IndexFlatIP(d)
t0 = time.time(); ivf = faiss.IndexIVFFlat(q_, d, nlist, faiss.METRIC_INNER_PRODUCT); faiss.omp_set_num_threads(4)
ivf.train(corpus); ivf.add(corpus); faiss.omp_set_num_threads(1)
build_info["IVF-Flat"] = (time.time() - t0, d * 4)
bench_rows += bench(ivf, "nprobe", [1, 2, 4, 8, 16, 32, 64, 128], "IVF-Flat")

q2 = faiss.IndexFlatIP(d)
t0 = time.time(); ivfpq = faiss.IndexIVFPQ(q2, d, nlist, 16, 8, faiss.METRIC_INNER_PRODUCT); faiss.omp_set_num_threads(4)
ivfpq.train(corpus)
# IndexRefineFlat envuelve el IVF-PQ VACÍO; al añadir, guarda los códigos PQ y también los vectores
# completos para re-ordenar exactamente los k·k_factor mejores candidatos (recupera el recall que pierde PQ)
refine = faiss.IndexRefineFlat(ivfpq); refine.k_factor = 8
refine.add(corpus); faiss.omp_set_num_threads(1)
build_info["IVF-PQ (m=16)"] = (time.time() - t0, 16)
bench_rows += bench(ivfpq, "nprobe", [1, 4, 16, 64, 128], "IVF-PQ (m=16)")
bench_rows += bench(refine, "nprobe", [4, 16, 64], "IVF-PQ + refine ×8 (+256 B/vector)")

t0 = time.time(); hnsw = faiss.IndexHNSWFlat(d, 32, faiss.METRIC_INNER_PRODUCT); hnsw.hnsw.efConstruction = 80
faiss.omp_set_num_threads(4); hnsw.add(corpus); faiss.omp_set_num_threads(1)
build_info["HNSW (M=32)"] = (time.time() - t0, d * 4 + 2 * 32 * 4)
bench_rows += bench(hnsw, "efSearch", [16, 32, 64, 128, 256, 512], "HNSW (M=32)")
bdf = pd.DataFrame(bench_rows)
bdf.head(10)
''')
    nb.code(r'''
fig, axes = plt.subplots(1, 2, figsize=(15, 4.6))
for label, g in bdf.groupby("índice"):
    axes[0].plot(g["ms/consulta"], g["recall@10"], "o-", label=label)
    for _, r in g.iterrows():
        axes[0].annotate(r.param.split("=")[1], (r["ms/consulta"], r["recall@10"]), fontsize=6, xytext=(2, 2), textcoords="offset points")
axes[0].axvline(t_flat, ls="--", c="k", lw=0.8); axes[0].text(t_flat, 0.05, " Flat exacto", fontsize=8)
axes[0].set_xscale("log"); axes[0].set_xlabel("latencia (ms/consulta, 1 hilo CPU, escala log)"); axes[0].set_ylabel("recall@10 vs exacto")
axes[0].set_title(f"Recall vs latencia — {N_CORPUS:,} vectores d={d}"); axes[0].legend(fontsize=8); axes[0].set_ylim(0, 1.02)
mem = {"Flat": d * 4, **{k: v[1] for k, v in build_info.items()}}
axes[1].bar(mem.keys(), mem.values(), color=["#8c8c8c", "#4c72b0", "#dd8452", "#55a868"]); axes[1].set_yscale("log")
axes[1].set_ylabel("bytes por vector (log)"); axes[1].set_title("Memoria por vector (aprox.)")
for i, (k, v) in enumerate(mem.items()):
    axes[1].text(i, v, f"{v} B", ha="center", va="bottom", fontsize=8)
plt.tight_layout(); plt.show()
print({k: f"build {v[0]:.1f}s" for k, v in build_info.items()})
''')
    nb.md(r"""
**Cómo leerlo**: cada curva es un índice; moverse a la derecha (más `nprobe`/`efSearch`) compra recall con latencia. HNSW suele dominar en CPU a recall alto; IVF-PQ gana por **memoria** (16 B vs 256 B por vector: 16× más catálogo en la misma RAM) y con *refine* recupera casi todo el recall. Ojo: las **consultas** son vectores de *usuario* y el índice contiene vectores de *ítem*; si ambas distribuciones difieren mucho (lo normal en two-tower), los índices de grafo pierden recall y necesitan `efSearch` mayor (problema *out-of-distribution* de ANN, estudiado p. ej. por RoarGraph, VLDB 2024). Mide siempre el recall **con consultas reales**, no con vectores del propio corpus. En GPU (`faiss-gpu`), Flat e IVF sobre 10⁶–10⁷ vectores procesan miles de consultas por lote en milisegundos: ideal para *batch retrieval* offline.

### GPU y otras librerías
""")
    nb.code(r'''
# FAISS en GPU (si instalaste un wheel con GPU, p. ej. `pip install faiss-gpu-cu12`)
if hasattr(faiss, "StandardGpuResources") and torch.cuda.is_available():
    res = faiss.StandardGpuResources()
    gpu_flat = faiss.index_cpu_to_gpu(res, 0, flat)
    t0 = time.perf_counter(); gpu_flat.search(Q, K); print(f"Flat en GPU: {(time.perf_counter()-t0)/len(Q)*1e3:.4f} ms/consulta (lote de {len(Q)})")
else:
    print("FAISS sin soporte GPU en este entorno (faiss-cpu). En Colab GPU: !pip install faiss-gpu-cu12")

# hnswlib y ScaNN: alternativas populares (opcionales)
try:
    import hnswlib
    p = hnswlib.Index(space="ip", dim=d); p.init_index(max_elements=len(corpus), ef_construction=80, M=32); p.add_items(corpus)
    p.set_ef(128); t0 = time.perf_counter(); lbl, _ = p.knn_query(Q, k=K)
    print(f"hnswlib ef=128: recall@10={np.mean([len(set(a)&set(b))/K for a,b in zip(lbl, GT)]):.3f}, {(time.perf_counter()-t0)/len(Q)*1e3:.3f} ms/consulta")
except ImportError:
    print("hnswlib no instalado (pip install hnswlib)")
''')
    nb.md(r"""
ScaNN (Google, Guo et al., 2020) usa *anisotropic vector quantization* (cuantiza penalizando más el error **paralelo** al vector, que es el que afecta al producto escalar) y está entre los más rápidos en ann-benchmarks para MIPS:
```python
# pip install scann   (solo Linux x86)
import scann
searcher = (scann.scann_ops_pybind.builder(corpus, 10, "dot_product")
            .tree(num_leaves=2000, num_leaves_to_search=100, training_sample_size=250_000)
            .score_ah(2, anisotropic_quantization_threshold=0.2)
            .reorder(100).build())
neighbors, distances = searcher.search_batched(Q)
```

## 🚀 6. Servir top-K en milisegundos
Flujo de una petición: features del usuario → **torre de usuario** (GPU/CPU, ~1 ms) → **ANN** (~1 ms) → **filtrado** (vistos, disponibilidad por país, control parental) → candidatos al ranker (módulo 06/07). Como el índice no sabe filtrar "vistos" por usuario, se piden $K' > K$ y se filtra después (o se usan índices con filtros, como Qdrant/Milvus/Vespa).
""")
    nb.code(r'''
item_index = faiss.IndexHNSWFlat(d, 32, faiss.METRIC_INNER_PRODUCT)
V_items = np.ascontiguousarray(V.astype(np.float32)); item_index.add(V_items); item_index.hnsw.efSearch = 128

def recommend(model, hist_ids: np.ndarray, ucat: np.ndarray, k=10, over_fetch=4):
    with torch.no_grad():
        q = model.user_vec(torch.as_tensor(hist_ids[None], device=device), torch.as_tensor(ucat[None], device=device)).cpu().numpy()
    _, I = item_index.search(q.astype(np.float32), k * over_fetch + len(hist_ids))
    seen = set(hist_ids.tolist())
    return [int(i) + 1 for i in I[0] if (i + 1) not in seen][:k]          # +1: fila 0 de V = ítem 1

lat = []
for j in range(300):
    t0 = time.perf_counter(); recommend(m_best, EV_test["hist"][j], EV_test["ucat"][j]); lat.append((time.perf_counter() - t0) * 1e3)
print(f"Latencia end-to-end (torre usuario + HNSW + filtro): p50={np.percentile(lat,50):.2f} ms · p99={np.percentile(lat,99):.2f} ms ({device})")
j = 0
print("Historia reciente:", [TITLE[i] for i in EV_test["hist"][j][-5:] if i > 0])
print("Recomendado:", [TITLE[i] for i in recommend(m_best, EV_test["hist"][j], EV_test["ucat"][j])])
''')
    nb.md(r"""
### Bases de datos vectoriales (cuándo dejar FAISS "a pelo")
| Sistema | Fuerte en |
|---|---|
| **FAISS / ScaNN / hnswlib** | librerías in-process: máximo control y velocidad; tú gestionas réplica, actualización y filtros |
| **Milvus** | cluster distribuido, muchos tipos de índice (incl. GPU/DiskANN), miles de millones de vectores |
| **Qdrant** | filtros por payload muy eficientes durante la búsqueda HNSW, Rust |
| **Weaviate** | búsqueda híbrida (BM25 + vectores), módulos de vectorización |
| **pgvector** | vectores dentro de Postgres (HNSW/IVF): perfecto si el catálogo es ≤ 10⁷ y ya usas Postgres |
| **Vespa** | retrieval + ranking multi-fase en el mismo motor (lo usan Spotify, Yahoo) |

Frameworks de entrenamiento: **TorchRec** (ejemplo de two-tower en `torchrec/examples/retrieval`, con embeddings sharded entre GPUs) y **NVIDIA Merlin Models** (`TwoTowerModelV2` con in-batch sampling y logQ integrados).

## 🏭 7. En producción
- **YouTube**: Covington et al. (2016) formularon candidate generation como softmax extrema con historial de búsquedas y vistas, *example age* para frescura y serving por vecinos más cercanos; Yi et al. (2019) describen el two-tower con corrección de sesgo de muestreo y estimación de frecuencia en streaming para YouTube.
- **Google Play** (Yang et al., 2020): Mixed Negative Sampling en el two-tower de recomendación de apps.
- **Facebook Search** (Huang et al., 2020): *embedding-based retrieval* con hard negatives (online y offline), ANN con cuantización en Faiss, y la lección de que **los hard negatives solos empeoran**: hay que mezclarlos con fáciles.
- **Pinterest**: PinSage (módulo 10) y PinnerSage (Pal et al., 2020: múltiples embeddings por usuario vía clustering, para capturar intereses diversos); **Airbnb** (Grbovic & Cheng, KDD 2018): embeddings de listings y búsqueda en tiempo real.
- **Escala**: retrieval suele combinar **varias fuentes** de candidatos (two-tower, item-to-item, grafo, populares por región, seguidos) que se unen antes del ranker. Ninguna fuente sola llega al recall necesario.

## 🧠 8. Secretos de la élite
1. **Sin logQ, el two-tower con in-batch negatives está sesgado** contra los ítems populares (los ve como negativos demasiado a menudo) — o, según el caso, el logit absorbe la popularidad y el modelo no aprende personalización. La corrección de Yi et al. es una resta de una línea; olvidarla es el bug más común.
2. **Accidental hits**: cuando el mismo ítem aparece dos veces en el batch, se convierte en negativo de sí mismo. Máscara obligatoria (TensorFlow Recommenders tiene `remove_accidental_hits` por esto).
3. **El producto escalar es una limitación… y una virtud**. Rendle et al. (2020) mostraron que un dot product bien tuneado iguala o supera a un MLP como función de similitud (NCF) — y solo el dot product es indexable. No metas un MLP encima del producto en retrieval.
4. **Batch grande = más negativos = mejor modelo** (hasta saturar). Es una razón real para entrenar en A100: batches de 8–32 k cambian el recall.
5. **Hard negatives con cuidado**: muchos "hard negatives" son **falsos negativos** (el usuario los habría visto). Usa rangos intermedios (p. ej. 101–500 en EBR), mézclalos con fáciles y vigila el recall de validación.
6. **Recall offline ≠ calidad del sistema**: el retrieval solo tiene que poner los buenos en el **top-500/1000**; optimizar NDCG@10 del retrieval no es su trabajo (lo hace el ranker). Mide Recall@K con K del tamaño real de la etapa.
7. **Actualizar el índice** es la mitad del problema: ítems nuevos cada hora, embeddings que cambian en cada reentreno (¡las versiones de torre de usuario e índice deben coincidir!). Versiona índice y modelo juntos (módulo 17).
8. **Sampled metrics engañan**: evaluar Recall contra 100 negativos aleatorios en vez del catálogo completo puede invertir el orden de modelos (Krichene & Rendle, 2020; módulo 02).

## ⚠️ 9. Errores comunes
- Normalizar embeddings y olvidar la temperatura (softmax casi uniforme → no aprende).
- Construir la historia del ejemplo con eventos **posteriores** al target (fuga), o usar el ID de usuario como única feature (no generaliza a usuarios nuevos ni a su futuro).
- Comparar índices ANN con distintos números de hilos o sin *warm-up*.
- No filtrar vistos → el recall se "llena" de lo que el usuario ya vio.
- Usar `METRIC_L2` con vectores no normalizados cuando el modelo se entrenó con producto escalar.

## 📝 10. Autoevaluación
1. ¿Por qué el retrieval exige un score factorizado $\langle q(u), v(i)\rangle$?
<details><summary>Respuesta</summary>Porque permite precalcular v(i) offline e indexarlo; en serving solo se calcula q(u) una vez y la búsqueda del top-K es MIPS sub-lineal con ANN. Un modelo con cruces exigiría una pasada por ítem.</details>

2. Deriva por qué los in-batch negatives necesitan la corrección $-\log(B p_j)$.
<details><summary>Respuesta</summary>Los negativos se muestrean con Q(j) ∝ p_j (frecuencia en los datos). La softmax muestreada solo es un estimador consistente de la completa si se corrigen los logits restando log Q(j); el valor esperado de apariciones de j en el batch es B·p_j.</details>

3. ¿Qué aporta Mixed Negative Sampling?
<details><summary>Respuesta</summary>Negativos uniformes del catálogo: los ítems de la cola larga o nuevos casi nunca aparecen in-batch, así que sin MNS el modelo no aprende a puntuarlos bien (ni a rechazarlos).</details>

4. ¿Por qué no usar solo los negativos más duros?
<details><summary>Respuesta</summary>Muchos son falsos negativos (relevantes no observados) y además el modelo deja de aprender a separar lo obvio; empíricamente (EBR) hay que mezclarlos con negativos fáciles.</details>

5. Tienes 500 M vectores de 128 dims y 64 GB de RAM. ¿Qué índice?
<details><summary>Respuesta</summary>Flat necesita 256 GB (128×4 B×5·10⁸). IVF-PQ con m=32–64 bytes por vector ocupa 16–32 GB y cabe; añadir re-ranking con los vectores en disco o una etapa de refine si hace falta recall.</details>

6. ¿Qué parámetro tocarías en producción si la latencia p99 sube y por qué no hace falta reconstruir el índice?
<details><summary>Respuesta</summary>nprobe (IVF) o efSearch (HNSW): son parámetros de búsqueda, no de construcción, y mueven el punto en la curva recall-latencia en caliente.</details>

## 📚 11. Referencias
- Covington, P., Adams, J., Sargin, E. (2016). *Deep Neural Networks for YouTube Recommendations*. RecSys. https://dl.acm.org/doi/10.1145/2959100.2959190
- Yi, X. et al. (2019). *Sampling-Bias-Corrected Neural Modeling for Large Corpus Item Recommendations*. RecSys. https://dl.acm.org/doi/10.1145/3298689.3346996
- Yang, J. et al. (2020). *Mixed Negative Sampling for Learning Two-tower Neural Networks in Recommendations*. WWW (Companion).
- Huang, J.-T. et al. (2020). *Embedding-based Retrieval in Facebook Search*. KDD. https://arxiv.org/abs/2006.11632
- Bengio, Y., Senécal, J.-S. (2008). *Adaptive Importance Sampling to Accelerate Training of a Neural Probabilistic Language Model*. IEEE TNN. · Jean, S. et al. (2015). *On Using Very Large Target Vocabulary for Neural Machine Translation*. https://arxiv.org/abs/1412.2007
- Wang, F., Liu, H. (2021). *Understanding the Behaviour of Contrastive Loss*. CVPR. https://arxiv.org/abs/2012.09740
- Rendle, S. et al. (2020). *Neural Collaborative Filtering vs. Matrix Factorization Revisited*. RecSys. https://arxiv.org/abs/2005.09683
- Krichene, W., Rendle, S. (2020). *On Sampled Metrics for Item Recommendation*. KDD.
- Johnson, J., Douze, M., Jégou, H. (2017). *Billion-scale similarity search with GPUs*. https://arxiv.org/abs/1702.08734 · Douze, M. et al. (2024). *The Faiss library*. https://arxiv.org/abs/2401.08281
- Jégou, H., Douze, M., Schmid, C. (2011). *Product Quantization for Nearest Neighbor Search*. IEEE TPAMI.
- Malkov, Y., Yashunin, D. (2018). *Efficient and robust approximate nearest neighbor search using HNSW graphs*. https://arxiv.org/abs/1603.09320
- Guo, R. et al. (2020). *Accelerating Large-Scale Inference with Anisotropic Vector Quantization* (ScaNN). ICML. https://arxiv.org/abs/1908.10396
- Subramanya, S. J. et al. (2019). *DiskANN: Fast Accurate Billion-point Nearest Neighbor Search on a Single Node*. NeurIPS.
- Pal, A. et al. (2020). *PinnerSage: Multi-Modal User Embedding Framework for Recommendations at Pinterest*. KDD. https://arxiv.org/abs/2007.03634
- Grbovic, M., Cheng, H. (2018). *Real-time Personalization using Embeddings for Search Ranking at Airbnb*. KDD.
- Aumüller, M. et al. *ANN-Benchmarks*. https://ann-benchmarks.com
- Librerías: FAISS (https://github.com/facebookresearch/faiss), ScaNN (https://github.com/google-research/google-research/tree/master/scann), hnswlib (https://github.com/nmslib/hnswlib), TorchRec (https://github.com/pytorch/torchrec), Merlin Models (https://github.com/NVIDIA-Merlin/models), TensorFlow Recommenders (https://www.tensorflow.org/recommenders), Milvus, Qdrant, Weaviate, pgvector, Vespa.
""")
    nb.save(f"recsys-course/{MOD}/{MOD}.ipynb")


def build_project():
    path = f"recsys-course/{MOD}/08_proyecto_two_tower_faiss.ipynb"
    nb = Notebook("Proyecto 08 · Two-tower + FAISS para CineMatch", colab_path=path, gpu=True)
    header(nb, "08", "Proyecto: retrieval two-tower + índice FAISS sirviendo top-K en milisegundos",
           "🟠 Avanzado", "4–6 h", "L4 / A100 (T4 vale para ML-1M)", "~4 (ML-1M) · ~20 (ML-25M)",
           "Lección 08 (y 01, 02, 05)", tipo="Proyecto")
    nb.md(r"""
## 🏢 Contexto de negocio
El ranker de CineMatch (proyectos 06–07) es bueno, pero solo ordena lo que le llega: hoy los candidatos salen de "populares + item-kNN" y el equipo sospecha que **faltan películas de nicho** relevantes. Te encargan la nueva **fuente de candidatos principal**: un two-tower que, dada la historia del usuario, devuelva **300 candidatos en < 10 ms p99 en CPU**.

## 📦 Dataset
MovieLens-1M (o **ML-25M** con `SCALE="25m"` en A100) con split temporal global (utilidades de módulos 01/02). Se evalúa sobre el **catálogo completo** filtrando vistos.

## ✅ Entregables y rúbrica
| # | Entregable | Criterio |
|---|---|---|
| 1 | `TwoTower` (torre usuario con historia + demografía; torre ítem con id + géneros + año) | Tests de forma/normalización pasan |
| 2 | Pérdida in-batch con **logQ** y máscara de *accidental hits* | Test incluido pasa |
| 3 | Recall@100 en test | > baseline de popularidad (en split temporal la popularidad es un rival fuerte; con ML-1M real y `FAST_DEV_RUN=False` apunta a ≥ 1,2×) |
| 4 | Ablación: sin logQ / con logQ / + MNS | Tabla + análisis cabeza/cola |
| 5 | Índice FAISS (HNSW o IVF) | Recall@100 ≥ 0,95 respecto a búsqueda exacta (catálogo real, consultas = usuarios reales) |
| 6 | Servicio `recommend(user)` con filtrado de vistos | p99 < 10 ms en CPU (1 hilo, máquina sin otras cargas) para 300 candidatos |
""")
    nb.code(r'''
!pip install -q faiss-cpu
''')
    nb.code(SETUP_CODE)
    nb.md(ML_UTILS_MD)
    nb.code(ML_UTILS_CODE)
    nb.code(r'''
FAST_DEV_RUN = True
SCALE = "1m"
MAX_EXAMPLES = 300_000 if FAST_DEV_RUN else None
MAX_EVAL_USERS = 2000 if FAST_DEV_RUN else 20000
EPOCHS = 3 if FAST_DEV_RUN else 10
BATCH = 1024 if FAST_DEV_RUN else 8192
''')
    nb.code(DATA_CODE)
    nb.code(r'''
pop_rank = np.argsort(-item_count)
def popularity_topk(EV, k=100):
    out = []
    for seen in EV["seen"]:
        s = set(seen); out.append([i for i in pop_rank[:k + len(s) + 1] if i not in s and i != 0][:k])
    return np.array(out)
def evaluate(topk, EV):
    return {"Recall@10": recall_at_k(topk, EV["truth"], 10), "Recall@100": recall_at_k(topk, EV["truth"], 100),
            "NDCG@10": ndcg_at_k(topk, EV["truth"], 10)}
POP = evaluate(popularity_topk(EV_test), EV_test); print("Popularidad:", POP)
''')
    nb.md(r"""
## Paso 1 — Las dos torres
Requisitos: salida L2-normalizada de dimensión `d`; la torre de usuario usa la **media enmascarada** (padding = 0) de los embeddings de la historia y las 3 features demográficas `UCAT`; la torre de ítem usa `ITEM_G` (multi-hot de géneros) y `ITEM_Y` (quinquenio).
""")
    nb.code(r'''
class TwoTower(nn.Module):
    def __init__(self, n_items, n_genres, n_years=24, ucat_dims=(3, 8, 22), d=64):
        super().__init__()
        # TODO
        raise NotImplementedError
    def item_vec(self, ids):
        raise NotImplementedError
    def user_vec(self, hist, ucat):
        raise NotImplementedError

def _test_towers():
    m = TwoTower(N_ITEMS, len(GENRES), ucat_dims=UCAT_DIMS)
    v = m.item_vec(torch.tensor([1, 2, 3])); u = m.user_vec(torch.as_tensor(Htr[:4]), torch.as_tensor(UCAT[Utr[:4]]))
    assert v.shape == (3, 64) and u.shape == (4, 64)
    assert torch.allclose(v.norm(dim=-1), torch.ones(3), atol=1e-4) and torch.allclose(u.norm(dim=-1), torch.ones(4), atol=1e-4)
    print("✅ torres OK")
try:
    _test_towers()
except NotImplementedError:
    print("⏳ Implementa TwoTower")
''')
    nb.md(r"""
## Paso 2 — La pérdida
`retrieval_loss(u, v, pos, log_p, tau, logq)` recibe ya los vectores de usuario `u [B,d]` y de ítem positivo `v [B,d]`, los ids `pos [B]` y `log_p` (log-frecuencia de cada ítem). Debe:
1. calcular `logits = u @ v.T / tau`,
2. si `logq`, restar `log(B · p_j)` a cada **columna**,
3. enmascarar *accidental hits* (mismo id en otra fila),
4. devolver la cross-entropy con la diagonal como etiqueta.
""")
    nb.code(r'''
def retrieval_loss(u, v, pos, log_p, tau=0.05, logq=True):
    # TODO
    raise NotImplementedError

def _test_loss():
    torch.manual_seed(0)
    u = F.normalize(torch.randn(4, 8), dim=-1); pos = torch.tensor([5, 5, 7, 9]); v = u.clone()
    lp = torch.log(torch.full((10,), 0.1))
    l1 = retrieval_loss(u, v, pos, lp, tau=0.1, logq=False)
    # filas 0 y 1 tienen el mismo positivo: con la máscara, su pérdida no incluye al "gemelo"
    logits = u @ v.T / 0.1; logits[0, 1] = logits[1, 0] = -1e9
    assert torch.allclose(l1, F.cross_entropy(logits, torch.arange(4)), atol=1e-5)
    l2 = retrieval_loss(u, v, pos, lp, tau=0.1, logq=True)                 # p uniforme → logQ no cambia la CE
    assert torch.allclose(l1, l2, atol=1e-5)
    print("✅ pérdida OK")
try:
    _test_loss()
except NotImplementedError:
    print("⏳ Implementa retrieval_loss")
''')
    nb.md(r"""
## Paso 3 — Entrenamiento, evaluación y ablación
Entrena 3 variantes (sin logQ, con logQ, con logQ + 512 negativos uniformes) y compara Recall@100 total y por grupos de popularidad (cabeza 20 % / cola 40 %).
""")
    nb.code(r'''
# TODO: bucle de entrenamiento + retrieve() + evaluate() + tabla de ablación
''')
    nb.md(r"""
## Paso 4 — Índice FAISS y servicio
Construye un índice sobre los vectores de ítem (y, para estresarlo, sobre un corpus aumentado de ≥ 200 k vectores), mide recall@100 vs exacto y latencia p50/p99 de `recommend()` con 1 hilo.
""")
    nb.code(r'''
import faiss
# TODO
''')

    nb.md(r"""
---
# ⛔ SPOILER — Solución de referencia
""")
    nb.code(MODEL_CODE)
    nb.code(r'''
_test_towers()
LOG_P = torch.as_tensor(np.log((item_count + 1) / (item_count + 1).sum()), dtype=torch.float32, device=device)

def retrieval_loss(u, v, pos, log_p, tau=0.05, logq=True):
    B = pos.size(0)
    logits = u @ v.T / tau
    if logq:
        logits = logits - (log_p[pos] + math.log(B))[None, :]
    accidental = (pos[None, :] == pos[:, None]) & ~torch.eye(B, dtype=torch.bool, device=pos.device)
    logits = logits.masked_fill(accidental, -1e9)
    return F.cross_entropy(logits, torch.arange(B, device=pos.device))

_test_loss()

def train_tt(logq=True, n_uniform=0, tau=0.05, epochs=EPOCHS, bs=BATCH):
    torch.manual_seed(seed)
    model = TwoTower(N_ITEMS, len(GENRES), ucat_dims=UCAT_DIMS).to(device); opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    Hs, Ts, Uc = (torch.as_tensor(a, device=device) for a in (Htr, Ttr, UCAT[Utr]))
    for ep in range(epochs):
        model.train(); perm = torch.randperm(len(Ts), device=device)
        for s0 in range(0, len(Ts), bs):
            i = perm[s0:s0 + bs]
            u, v = model.user_vec(Hs[i], Uc[i]), model.item_vec(Ts[i])
            loss = retrieval_loss(u, v, Ts[i], LOG_P, tau, logq)
            if n_uniform:                                                   # MNS: columnas extra uniformes
                neg = torch.randint(1, N_ITEMS + 1, (n_uniform,), device=device)
                ln = u @ model.item_vec(neg).T / tau - (math.log(n_uniform / N_ITEMS) if logq else 0.0)
                logits = u @ v.T / tau
                if logq: logits = logits - (LOG_P[Ts[i]] + math.log(len(i)))[None, :]
                acc = (Ts[i][None, :] == Ts[i][:, None]) & ~torch.eye(len(i), dtype=torch.bool, device=device)
                allp = torch.cat([logits.masked_fill(acc, -1e9), ln.masked_fill(neg[None, :] == Ts[i][:, None], -1e9)], 1)
                loss = F.cross_entropy(allp, torch.arange(len(i), device=device))
            opt.zero_grad(); loss.backward(); opt.step()
        print(f"  época {ep+1}: Recall@100 val = {evaluate(retrieve(model, EV_val), EV_val)['Recall@100']:.4f}")
    return model

abl, models = {"Popularidad": POP}, {}
for name, kw in {"sin logQ": dict(logq=False), "logQ": dict(logq=True), "logQ + MNS": dict(logq=True, n_uniform=512)}.items():
    print("▶", name); models[name] = train_tt(**kw); abl[name] = evaluate(retrieve(models[name], EV_test), EV_test)
pd.DataFrame(abl).T.round(4)
''')
    nb.code(r'''
pct = np.argsort(np.argsort(-item_count)) / N_ITEMS
grp = {"cabeza": pct < 0.2, "cola": pct >= 0.6}
rows = {}
for name, m in models.items():
    tk = retrieve(m, EV_test)
    rows[name] = {g: recall_at_k(tk, [{i for i in t if mask[i]} for t in EV_test["truth"]], 100) for g, mask in grp.items()}
display(pd.DataFrame(rows).T.round(4))
best = max(models, key=lambda n: abl[n]["Recall@100"]); model = models[best]
print(f"Mejor: {best} · Recall@100 = {abl[best]['Recall@100']:.4f} · ratio vs popularidad = {abl[best]['Recall@100']/POP['Recall@100']:.2f}×")
''')
    nb.code(r'''
faiss.omp_set_num_threads(1)
V = all_item_vecs(model).cpu().numpy()[1:].astype(np.float32)
d = V.shape[1]
# 1) Índice sobre el catálogo real
index = faiss.IndexHNSWFlat(d, 32, faiss.METRIC_INNER_PRODUCT); index.hnsw.efConstruction = 100; index.add(V); index.hnsw.efSearch = 256
with torch.no_grad():
    Q = model.user_vec(torch.as_tensor(EV_test["hist"][:1000], device=device), torch.as_tensor(EV_test["ucat"][:1000], device=device)).cpu().numpy()
exact = faiss.IndexFlatIP(d); exact.add(V)
_, GT = exact.search(Q, 100); _, I = index.search(Q, 100)
print("Catálogo real · recall@100 HNSW vs exacto:", np.mean([len(set(a) & set(b)) / 100 for a, b in zip(I, GT)]).round(4))
# 2) Estrés: corpus aumentado
rng_ = np.random.default_rng(seed); NC = 200_000 if FAST_DEV_RUN else 2_000_000
i1, i2, w_ = rng_.integers(0, len(V), NC), rng_.integers(0, len(V), NC), rng_.uniform(0.5, 1.0, (NC, 1))
C = w_ * V[i1] + (1 - w_) * V[i2] + rng_.normal(0, 0.5 / np.sqrt(d), (NC, d)); C = (C / np.linalg.norm(C, axis=1, keepdims=True)).astype(np.float32)
big = faiss.IndexHNSWFlat(d, 32, faiss.METRIC_INNER_PRODUCT); big.hnsw.efConstruction = 80
faiss.omp_set_num_threads(4); big.add(C); faiss.omp_set_num_threads(1)
ex_big = faiss.IndexFlatIP(d); ex_big.add(C); _, GTb = ex_big.search(Q[:300], 100)
for ef in [64, 128, 256, 512]:
    big.hnsw.efSearch = ef
    t0 = time.perf_counter(); _, Ib = big.search(Q[:300], 100); dt = (time.perf_counter() - t0) / 300 * 1e3
    print(f"Corpus {NC:,} · efSearch={ef}: recall@100={np.mean([len(set(a)&set(b))/100 for a,b in zip(Ib, GTb)]):.4f} · {dt:.2f} ms/consulta")
''')
    nb.code(r'''
def recommend(user_hist: np.ndarray, ucat: np.ndarray, k=300, over_fetch=1.5):
    with torch.no_grad():
        q = model.user_vec(torch.as_tensor(user_hist[None], device=device), torch.as_tensor(ucat[None], device=device)).cpu().numpy()
    seen = set(user_hist[user_hist > 0].tolist())
    _, I = index.search(q.astype(np.float32), int(k * over_fetch) + len(seen))
    return [int(i) + 1 for i in I[0] if i >= 0 and (i + 1) not in seen][:k]

index.hnsw.efSearch = 256
lat = []
for j in range(min(500, len(EV_test["hist"]))):
    t0 = time.perf_counter(); recommend(EV_test["hist"][j], EV_test["ucat"][j]); lat.append((time.perf_counter() - t0) * 1e3)
p50, p99 = np.percentile(lat, [50, 99])
print(f"recommend(): p50 = {p50:.2f} ms · p99 = {p99:.2f} ms  → {'✅' if p99 < 10 else '❌'} objetivo p99 < 10 ms")
plt.figure(figsize=(6, 3)); plt.hist(lat, bins=40); plt.axvline(p99, c="r", ls="--", label=f"p99={p99:.2f} ms"); plt.legend()
plt.xlabel("ms por petición"); plt.title("Latencia del servicio de candidatos"); plt.show()
print([TITLE[i] for i in recommend(EV_test["hist"][0], EV_test["ucat"][0], k=10)])
''')
    nb.md(r"""
## 🚀 Retos extra
1. **ML-25M en A100** con `BATCH=16384`: ¿cuánto sube el recall al crecer el batch? (in-batch negatives "gratis").
2. **Hard negatives** (puestos 20–100 del modelo actual tras 1 época de warm-up) mezclados con MNS.
3. **Estimador de frecuencia en streaming** en lugar de la frecuencia exacta para logQ.
4. **Multi-interés**: varios vectores por usuario (clustering de su historia, PinnerSage) y unión de resultados.
5. **IVF-PQ + refine** a 2 M vectores: compara memoria y p99 con HNSW.
6. **Qdrant o pgvector** en Docker con filtro "solo títulos disponibles en el país del usuario".

## 🤔 Reflexión (producción / MLOps)
- ¿Cómo despliegas un nuevo modelo si la torre de usuario y el índice de ítems deben ser **de la misma versión**? (blue/green del índice, módulo 16-17).
- ¿Cada cuánto re-indexas? ¿Qué pasa con los estrenos que llegan entre reentrenos? (torre de ítem con features de contenido → embeddings para ítems nuevos sin reentrenar).
- ¿Qué métricas online monitorizarías del retrieval (recall respecto a lo que el ranker acaba eligiendo, diversidad de fuentes, latencia p99)?
""")
    nb.save(path)


if __name__ == "__main__":
    build_lesson()
    build_project()
