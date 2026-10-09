"""Builder del módulo 07 · Learning to Rank y Multi-Task Learning.

Ejecutar desde la raíz del repo:  python recsys-course/_tools/builders/build_07.py
"""
import os
import sys

sys.path.insert(0, "recsys-course/_tools")
sys.path.insert(0, "recsys-course/_tools/builders")
from nbbuild import Notebook  # noqa: E402
from b3_common import header, ML_UTILS_MD, ML_UTILS_CODE, DRAW_CODE, SETUP_CODE  # noqa: E402

MOD = "07_learning_to_rank_multitask"
os.makedirs(f"recsys-course/{MOD}", exist_ok=True)

KUAI_LOADER = r'''
# === KuaiRand-Pure (Kuaishou, CIKM 2022) con fallback sintético ==============
import tarfile, glob
KUAI_URL = "https://zenodo.org/records/10439422/files/KuaiRand-Pure.tar.gz"   # ~200 MB (md5 0820331067a3784d9691136f772b35a7)
TASKS = ["is_click", "long_view", "is_like"]

def synthetic_kuairand(n_users=1500, n_videos=2000, n_rows=400_000, seed=42):
    """Mismo esquema que KuaiRand-Pure. Tres tareas correlacionadas pero NO idénticas,
    que dependen de IDs (afinidad latente) y de features observables (actividad, tipo, música, duración, tab)."""
    rng = np.random.default_rng(seed)
    d = 8
    U, V = rng.normal(size=(n_users, d)), rng.normal(size=(n_videos, d))
    a_lv, a_like = rng.normal(size=d), rng.normal(size=d)
    act = rng.integers(0, 4, n_users); music = rng.integers(0, 10, n_videos); upl = rng.integers(0, 4, n_videos)
    author = rng.integers(0, 400, n_videos); author_q = rng.normal(0, 0.6, 400)
    vid_pop = rng.zipf(1.3, n_videos).clip(max=200).astype(float); vid_pop /= vid_pop.sum()
    u = rng.integers(0, n_users, n_rows); v = rng.choice(n_videos, n_rows, p=vid_pop)
    dur = rng.lognormal(10.5, 0.8, n_videos)                  # ms
    tab = rng.integers(0, 4, n_rows)
    aff = (U[u] * V[v]).sum(1) / np.sqrt(d)
    z_click = -0.9 + 0.9 * aff + np.array([0.6, 0.3, 0.0, -0.5])[act[u]] + author_q[author[v]] - 0.6 * (tab == 2) + 0.4 * (tab == 0)
    click = rng.random(n_rows) < 1 / (1 + np.exp(-z_click))
    z_lv = -0.3 + 0.7 * aff + 0.8 * (V[v] @ a_lv) / 3 - 0.9 * (np.log(dur[v]) - 10.5) + np.array([0.5, 0.0, -0.3, 0.2])[upl[v]]
    long_view = click & (rng.random(n_rows) < 1 / (1 + np.exp(-z_lv)))
    z_like = -3.0 + 0.5 * aff + 1.0 * ((U[u] * V[v]) @ a_like) / 3 + 0.25 * (music[v] - 4.5) / 2.9 + np.array([0.8, 0.4, 0.0, -0.4])[act[u]]
    like = click & (rng.random(n_rows) < 1 / (1 + np.exp(-z_like)))
    t = np.sort(rng.integers(1_649_376_000_000, 1_649_376_000_000 + 30 * 86_400_000, n_rows))
    logs = pd.DataFrame({"user_id": u, "video_id": v, "time_ms": t, "tab": tab,
                         "hourmin": (t // 3_600_000 % 24) * 100,
                         "is_click": click.astype(int), "long_view": long_view.astype(int), "is_like": like.astype(int)})
    users = pd.DataFrame({"user_id": np.arange(n_users),
                          "user_active_degree": np.array(["full_active", "high_active", "middle_active", "low_active"])[act],
                          "follow_user_num_range": rng.choice(["0", "(0,10]", "(10,50]", "(50,100]"], n_users),
                          "register_days_range": rng.choice(["15-30", "31-60", "61-90", "91-180", "181-365", "366-730", "730+"], n_users)})
    videos = pd.DataFrame({"video_id": np.arange(n_videos), "author_id": author,
                           "video_type": rng.choice(["NORMAL", "AD"], n_videos, p=[0.97, 0.03]),
                           "upload_type": np.array(["ShortImport", "Web", "Kmovie", "FollowShoot"])[upl],
                           "music_type": music, "video_duration": dur})
    return logs, users, videos

def load_kuairand(data_dir="data", max_rows=None):
    os.makedirs(data_dir, exist_ok=True)
    try:
        tgz = os.path.join(data_dir, "KuaiRand-Pure.tar.gz")
        if not glob.glob(os.path.join(data_dir, "**", "log_standard_4_08_to_4_21_pure.csv"), recursive=True):
            if not os.path.exists(tgz):
                print("Descargando KuaiRand-Pure de Zenodo (~200 MB)…")
                urllib.request.urlretrieve(KUAI_URL, tgz)
            with tarfile.open(tgz) as tf:
                tf.extractall(data_dir)
        f = lambda name: glob.glob(os.path.join(data_dir, "**", name), recursive=True)[0]
        logs = pd.concat([pd.read_csv(f("log_standard_4_08_to_4_21_pure.csv")),
                          pd.read_csv(f("log_standard_4_22_to_5_08_pure.csv"))], ignore_index=True)
        users = pd.read_csv(f("user_features_pure.csv"))
        videos = pd.read_csv(f("video_features_basic_pure.csv"))
        print(f"✅ KuaiRand-Pure real: {len(logs):,} impresiones")
    except Exception as e:
        print(f"⚠️ No se pudo cargar KuaiRand ({type(e).__name__}). Uso datos SINTÉTICOS con el mismo esquema.")
        logs, users, videos = synthetic_kuairand()
    logs = logs.sort_values("time_ms").reset_index(drop=True)
    if max_rows and len(logs) > max_rows:
        logs = logs.iloc[-max_rows:].reset_index(drop=True)      # nos quedamos con lo más reciente
    return logs, users, videos

KUAI_CATS = ["user_id", "video_id", "author_id", "tab", "hour", "user_active_degree",
             "follow_user_num_range", "register_days_range", "video_type", "upload_type", "music_type", "dur_bucket"]

def prepare_kuairand(logs, users, videos):
    df = logs.merge(users[["user_id", "user_active_degree", "follow_user_num_range", "register_days_range"]], on="user_id", how="left")
    df = df.merge(videos[["video_id", "author_id", "video_type", "upload_type", "music_type", "video_duration"]], on="video_id", how="left")
    df["hour"] = (df.hourmin // 100).astype(int)
    df["dur_bucket"] = pd.qcut(df.video_duration.fillna(df.video_duration.median()).rank(method="first"), 10, labels=False)
    n = len(df); i1, i2 = int(0.8 * n), int(0.9 * n)
    split = np.array(["train"] * i1 + ["val"] * (i2 - i1) + ["test"] * (n - i2))   # temporal (ordenado por time_ms)
    X, field_dims = [], []
    for c in KUAI_CATS:
        col = df[c].astype(str)
        vocab = pd.Index(col[split == "train"].unique())
        X.append(vocab.get_indexer(col) + 1); field_dims.append(len(vocab) + 1)     # OOV → 0
    X = (np.stack(X, 1) + np.cumsum([0] + field_dims[:-1])).astype(np.int32)
    Y = df[TASKS].values.astype(np.float32)
    return df, X, Y, field_dims, split
'''

MTL_MODELS = r'''
# === Arquitecturas multi-tarea desde cero =====================================
def mlp(dims, dropout=0.0, last_act=True):
    layers = []
    for i, (a, b) in enumerate(zip(dims[:-1], dims[1:])):
        layers.append(nn.Linear(a, b))
        if last_act or i < len(dims) - 2:
            layers += [nn.ReLU(), nn.Dropout(dropout)]
    return nn.Sequential(*layers)

class CatEncoder(nn.Module):
    """Embeddings compartidos por TODAS las tareas (lo habitual en producción)."""
    def __init__(self, field_dims, k=16):
        super().__init__()
        self.emb = nn.Embedding(sum(field_dims), k); nn.init.normal_(self.emb.weight, std=0.01)
        self.d_out = len(field_dims) * k
    def forward(self, x):
        return self.emb(x).flatten(1)

class SharedBottom(nn.Module):
    def __init__(self, d_in, n_tasks, bottom=(256, 128), tower=(64,)):
        super().__init__()
        self.bottom = mlp([d_in, *bottom])
        self.towers = nn.ModuleList([mlp([bottom[-1], *tower, 1], last_act=False) for _ in range(n_tasks)])
    def forward(self, h):
        z = self.bottom(h)
        return torch.cat([t(z) for t in self.towers], 1), None

class MMoE(nn.Module):
    """Ma et al. (KDD 2018): expertos compartidos + una puerta softmax POR TAREA."""
    def __init__(self, d_in, n_tasks, n_experts=6, expert=(256, 128), tower=(64,)):
        super().__init__()
        self.experts = nn.ModuleList([mlp([d_in, *expert]) for _ in range(n_experts)])
        self.gates = nn.ModuleList([nn.Linear(d_in, n_experts) for _ in range(n_tasks)])
        self.towers = nn.ModuleList([mlp([expert[-1], *tower, 1], last_act=False) for _ in range(n_tasks)])
    def forward(self, h):
        E = torch.stack([e(h) for e in self.experts], 1)                # [B, n_exp, d]
        outs, gates = [], []
        for gate, tower in zip(self.gates, self.towers):
            g = torch.softmax(gate(h), -1)                                # [B, n_exp]
            outs.append(tower((g.unsqueeze(-1) * E).sum(1))); gates.append(g)
        return torch.cat(outs, 1), torch.stack(gates, 0)                # gates: [T, B, n_exp]

class CGCLayer(nn.Module):
    """Customized Gate Control (Tang et al., RecSys 2020): expertos ESPECÍFICOS por tarea + compartidos."""
    def __init__(self, d_in, d_out, n_tasks, n_spec=2, n_shared=2, last=False):
        super().__init__()
        self.T, self.n_spec, self.n_shared = n_tasks, n_spec, n_shared
        self.spec = nn.ModuleList([nn.ModuleList([mlp([d_in, d_out]) for _ in range(n_spec)]) for _ in range(n_tasks)])
        self.shared = nn.ModuleList([mlp([d_in, d_out]) for _ in range(n_shared)])
        self.gates = nn.ModuleList([nn.Linear(d_in, n_spec + n_shared) for _ in range(n_tasks)])
        self.shared_gate = None if last else nn.Linear(d_in, n_tasks * n_spec + n_shared)
    def forward(self, xs, x_sh):
        sh = [e(x_sh) for e in self.shared]
        outs, gates, all_spec = [], [], []
        for t in range(self.T):
            sp = [e(xs[t]) for e in self.spec[t]]; all_spec += sp
            E = torch.stack(sp + sh, 1)
            g = torch.softmax(self.gates[t](xs[t]), -1)
            outs.append((g.unsqueeze(-1) * E).sum(1)); gates.append(g)
        new_sh = None
        if self.shared_gate is not None:
            E = torch.stack(all_spec + sh, 1)
            g = torch.softmax(self.shared_gate(x_sh), -1)
            new_sh = (g.unsqueeze(-1) * E).sum(1)
        return outs, new_sh, gates

class PLE(nn.Module):
    """Progressive Layered Extraction: varias capas CGC apiladas."""
    def __init__(self, d_in, n_tasks, levels=2, d_hidden=128, n_spec=2, n_shared=2, tower=(64,)):
        super().__init__()
        self.layers = nn.ModuleList([CGCLayer(d_in if l == 0 else d_hidden, d_hidden, n_tasks, n_spec, n_shared,
                                              last=(l == levels - 1)) for l in range(levels)])
        self.towers = nn.ModuleList([mlp([d_hidden, *tower, 1], last_act=False) for _ in range(n_tasks)])
        self.T = n_tasks
    def forward(self, h):
        xs, x_sh = [h] * self.T, h
        for layer in self.layers:
            xs, x_sh, gates = layer(xs, x_sh)
        return torch.cat([tw(x) for tw, x in zip(self.towers, xs)], 1), torch.stack(gates, 0)

class MTLNet(nn.Module):
    def __init__(self, encoder, core):
        super().__init__(); self.encoder, self.core = encoder, core
    def forward(self, x):
        return self.core(self.encoder(x))

def build_mtl(kind, field_dims, n_tasks, k=16):
    enc = CatEncoder(field_dims, k)
    core = {"Shared-Bottom": lambda: SharedBottom(enc.d_out, n_tasks),
            "MMoE": lambda: MMoE(enc.d_out, n_tasks),
            "PLE": lambda: PLE(enc.d_out, n_tasks)}[kind]()
    return MTLNet(enc, core)
'''

MTL_TRAIN = r'''
# === Entrenamiento multi-tarea con pesos fijos o "uncertainty weighting" =====
from sklearn.metrics import roc_auc_score

@torch.no_grad()
def predict_mtl(model, X, bs=65536):
    model.eval(); out = []
    for i in range(0, len(X), bs):
        logits, _ = model(torch.as_tensor(X[i:i + bs], device=device).long())
        out.append(torch.sigmoid(logits).cpu().numpy())
    return np.concatenate(out)

def train_mtl(model, Xtr, Ytr, Xva, Yva, task_w=None, epochs=2, bs=4096, lr=1e-3, weighting="fixed", verbose=False):
    T = Ytr.shape[1]
    task_w = torch.tensor(task_w if task_w is not None else [1.0] * T, device=device)
    model = model.to(device)
    log_vars = torch.zeros(T, device=device, requires_grad=True)          # Kendall et al. 2018
    params = list(model.parameters()) + ([log_vars] if weighting == "uncertainty" else [])
    opt = torch.optim.Adam(params, lr=lr)
    Xt = torch.as_tensor(Xtr, device=device); Yt = torch.as_tensor(Ytr, device=device)
    best, best_state = -np.inf, None
    for ep in range(epochs):
        model.train(); perm = torch.randperm(len(Xt), device=device)
        for s in range(0, len(Xt), bs):
            i = perm[s:s + bs]
            logits, _ = model(Xt[i].long())
            l_t = F.binary_cross_entropy_with_logits(logits, Yt[i], reduction="none").mean(0)   # [T]
            loss = (task_w * l_t).sum() if weighting == "fixed" else (torch.exp(-log_vars) * l_t + log_vars).sum()
            opt.zero_grad(set_to_none=True); loss.backward(); opt.step()
        P = predict_mtl(model, Xva)
        aucs = [roc_auc_score(Yva[:, t], P[:, t]) for t in range(T)]
        if verbose: print(f"  época {ep+1}: AUC val", np.round(aucs, 4))
        if np.mean(aucs) > best:
            best = np.mean(aucs); best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    return model
'''


def build_lesson():
    nb = Notebook("Módulo 07 · Learning to Rank y Multi-Task", colab_path=f"recsys-course/{MOD}/{MOD}.ipynb", gpu=True)
    header(nb, "07", "Learning to Rank y ranking multi-tarea",
           "🟠 Avanzado", "6 h", "L4 (T4 suficiente; A100 si `FAST_DEV_RUN=False`)",
           "~4 (FAST_DEV_RUN) · ~10–15 (full)",
           "02 (NDCG), 05 (MF), 06 (ranking CTR, DeepFM/DCN)")
    nb.md(r"""
## 🎯 Objetivos de aprendizaje
1. **Distinguir** los enfoques *pointwise*, *pairwise* y *listwise* y **justificar** cuál usar según la métrica de negocio.
2. **Derivar** el gradiente de RankNet y la ponderación $|\Delta \text{NDCG}|$ de LambdaRank, y **explicar** qué hace LambdaMART.
3. **Implementar en PyTorch** las pérdidas pointwise, RankNet, LambdaRank, ListNet y ListMLE, y **compararlas** con LightGBM `lambdarank`.
4. **Simular y corregir** el sesgo de posición con IPS y con PAL (*position-bias aware learning*).
5. **Implementar** Shared-Bottom, MMoE, PLE y ESMM, y **reproducir** el *seesaw phenomenon* y el efecto de la correlación entre tareas.
6. **Trazar** el frente de Pareto entre objetivos y **diseñar** una función de fusión de scores para la home de CineMatch.
""")
    nb.md(r"""
## 💡 1. Intuición

### 1.1 De "predecir un clic" a "ordenar una lista"
En el módulo 06 entrenaste un clasificador pointwise: cada impresión es independiente. Pero el usuario ve una **lista**, y la métrica de negocio (NDCG@10, clics en el top, tiempo de visionado de la sesión) depende **solo del orden** y sobre todo **de lo de arriba**. *Learning to Rank* (LTR) optimiza directamente eso.

Analogía con lo que conoces: pointwise = regresión/clasificación; pairwise = *contrastive learning* de pares (¿cuál de los dos es mejor?); listwise = una softmax sobre la lista (como la última capa de un clasificador multiclase cuyas "clases" son los documentos).

### 1.2 Muchos objetivos a la vez
La home de Netflix/YouTube/TikTok no optimiza "clic": optimiza **clic, tiempo de visionado, completar, like, compartir, no-dislike, satisfacción a largo plazo…** Entrenar un modelo por objetivo es caro (N modelos en serving) y desperdicia datos (los likes son escasos, los clics abundantes). **Multi-task learning (MTL)** comparte representación entre tareas… con el riesgo de que unas tareas perjudiquen a otras (*negative transfer*, *seesaw*).
""")
    nb.code(r'''
!pip install -q lightgbm
''')
    nb.code(SETUP_CODE)
    nb.code(DRAW_CODE)
    nb.code(r'''
# Diagrama 1 — Pointwise vs Pairwise vs Listwise
fig, axes = plt.subplots(1, 3, figsize=(15, 3.8))
docs = ["Alien (rel 3)", "Coco (rel 1)", "Heat (rel 0)"]
for ax, title in zip(axes, ["Pointwise: f(x) ≈ rel", "Pairwise: P(i ≻ j) = σ(sᵢ − sⱼ)", "Listwise: P(permutación | s)"]):
    ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 6); ax.set_title(title, weight="bold")
for i, d in enumerate(docs):
    draw_blocks(axes[0], {d: (0.5, 4.3 - i * 1.6, 4.5, 1.0, d, "in"), f"y{i}": (6.2, 4.3 - i * 1.6, 3.2, 1.0, f"pérdida_{i}\n(BCE / MSE)", "mlp")}, [(d, f"y{i}")])
pairs = {"a": (0.3, 4.2, 3.8, 1, "Alien ≻ Coco", "in"), "b": (0.3, 2.4, 3.8, 1, "Alien ≻ Heat", "in"),
         "c": (0.3, 0.6, 3.8, 1, "Coco ≻ Heat", "in"), "l": (6.0, 2.2, 3.6, 1.6, "log(1+e^{−(sᵢ−sⱼ)})\n× |ΔNDCG| (Lambda)", "inter")}
draw_blocks(axes[1], pairs, [("a", "l"), ("b", "l"), ("c", "l")])
lst = {"L": (0.3, 1.5, 3.8, 3, "lista completa\n[Alien, Coco, Heat]\n(scores s₁, s₂, s₃)", "in"),
       "s": (6.0, 2.2, 3.6, 1.6, "softmax(s) vs\nsoftmax(rel)\n(ListNet / ListMLE)", "out")}
draw_blocks(axes[2], lst, [("L", "s")])
plt.tight_layout(); plt.show()
''')
    nb.code(r'''
# Gráfico 2 — ¿Por qué el top importa? Descuento de NDCG y |ΔNDCG| al intercambiar dos posiciones
k = np.arange(1, 21)
disc = 1 / np.log2(k + 1)
fig, axes = plt.subplots(1, 2, figsize=(12, 3.6))
axes[0].bar(k, disc, color="#4c72b0"); axes[0].set_title("Descuento 1/log₂(1+posición)"); axes[0].set_xlabel("posición")
gain = 2 ** np.array([3, 2, 2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]) - 1
idcg = (np.sort(gain)[::-1] * disc).sum()
M = np.abs(gain[:, None] - gain[None, :]) * np.abs(disc[:, None] - disc[None, :]) / idcg
im = axes[1].imshow(M, cmap="viridis"); plt.colorbar(im, ax=axes[1])
axes[1].set_title("|ΔNDCG| al intercambiar las posiciones i y j"); axes[1].set_xlabel("j"); axes[1].set_ylabel("i")
plt.tight_layout(); plt.show()
''')
    nb.md(r"""
## 📐 2. Teoría formal

### 2.1 Notación
Una **consulta** $q$ (aquí: un usuario en un momento dado) tiene documentos (candidatos) $\{d_1..d_n\}$ con relevancias graduadas $y_i\in\{0,1,2,3\}$ y features $\mathbf x_i$. Un modelo $f$ produce scores $s_i=f(\mathbf x_i)$; ordenamos por $s$.

$$\text{DCG@}K=\sum_{r=1}^{K}\frac{2^{y_{\pi(r)}}-1}{\log_2(1+r)},\qquad \text{NDCG@}K=\frac{\text{DCG@}K}{\text{IDCG@}K}$$

NDCG es **discontinua** en los scores (cambia a saltos al reordenar) → no se puede optimizar con gradiente directamente. Toda la historia de LTR son *surrogates* diferenciables.

### 2.2 RankNet (Burges et al., 2005)
Para cada par con $y_i>y_j$: $P_{ij}=\sigma(s_i-s_j)$ y la pérdida es la entropía cruzada con objetivo 1:
$$\ell_{ij} = \log\big(1+e^{-(s_i-s_j)}\big), \qquad \frac{\partial \ell_{ij}}{\partial s_i} = -\sigma\big(-(s_i-s_j)\big) =: \lambda_{ij}$$
El gradiente total sobre $s_i$ es $\lambda_i=\sum_{j:(i,j)}\lambda_{ij}-\sum_{j:(j,i)}\lambda_{ji}$: una "fuerza" que empuja cada documento hacia arriba o abajo.

### 2.3 LambdaRank y LambdaMART
Problema: RankNet trata igual un error en las posiciones 1–2 que en 50–51. **LambdaRank** reescala cada fuerza por cuánto cambiaría la métrica si se intercambiaran:
$$\lambda_{ij} = -\sigma\big(-(s_i-s_j)\big)\cdot\big|\Delta\text{NDCG}_{ij}\big|,\qquad |\Delta\text{NDCG}_{ij}| = \frac{|2^{y_i}-2^{y_j}|\cdot\big|\frac1{\log_2(1+r_i)}-\frac1{\log_2(1+r_j)}\big|}{\text{IDCG}}$$
donde $r_i$ es la posición actual de $d_i$ según los scores. Empíricamente esto optimiza NDCG casi directamente (y LambdaLoss, Wang et al. 2018, dio después la justificación probabilística).

**LambdaMART** = gradient boosting (MART) donde los *pseudo-residuos* de cada árbol son las $\lambda_i$. Es lo que implementan `LightGBM objective="lambdarank"` y `XGBoost rank:ndcg`. Ganó el Yahoo! LTR Challenge (2010) y sigue siendo el estándar en búsqueda.

### 2.4 Listwise: ListNet y ListMLE
- **ListNet** (Cao et al., 2007), versión *top-1*: $\ell = -\sum_i \text{softmax}(\mathbf y)_i \log \text{softmax}(\mathbf s)_i$.
- **ListMLE** (Xia et al., 2008): verosimilitud Plackett-Luce de la permutación ideal $\pi^*$ (ordenar por $y$):
$$\ell = -\sum_{r=1}^{n}\Big(s_{\pi^*(r)} - \log\sum_{m\ge r} e^{s_{\pi^*(m)}}\Big)$$

### 2.5 Sesgo de posición y *unbiased LTR*
Con logs de clics, $P(\text{clic}) = P(\text{examinado}\mid k)\cdot P(\text{relevante}\mid \mathbf x)=\theta_k\, \gamma(\mathbf x)$ (*position-based model*, PBM). Entrenar con clics crudos aprende $\theta_k\gamma$, es decir, **lo que el sistema anterior puso arriba**.
- **IPS** (Joachims et al., 2017): ponderar cada clic por $1/\theta_k$ hace el estimador insesgado de la pérdida con relevancia real. Para BCE pointwise: $\ell = -\big[\tfrac{c}{\theta_k}\log\sigma(s) + (1-\tfrac{c}{\theta_k})\log(1-\sigma(s))\big]$.
- **PAL** (Guo et al., Huawei, RecSys 2019): modelar $p(\text{clic})= p(\text{visto}\mid k)\cdot p(\text{rel}\mid \mathbf x)$ con dos módulos entrenados juntos; en serving se usa solo $p(\text{rel}\mid\mathbf x)$. YouTube (Zhao et al., 2019) usa la misma idea con un *shallow tower* que recibe la posición.
- ¿Cómo se estima $\theta_k$? Con **intervenciones**: aleatorizar (parte de) el ranking a un % pequeño de tráfico (RandTop-N, *swap* de pares), o con EM (Wang et al., 2018).

### 2.6 Multi-task learning
Con tareas $t=1..T$ y pérdidas $\mathcal L_t$: $\mathcal L = \sum_t w_t\mathcal L_t$.
- **Shared-Bottom**: $\hat y_t = h_t(f(\mathbf x))$. Si las tareas están poco correlacionadas, compiten por $f$ → *negative transfer*.
- **MMoE** (Ma et al., 2018): $n$ expertos $f_e$ y una puerta por tarea $g_t(\mathbf x)=\text{softmax}(W_t\mathbf x)$: $\hat y_t = h_t\big(\sum_e g_{t,e}(\mathbf x) f_e(\mathbf x)\big)$. Cada tarea elige su mezcla.
- **PLE / CGC** (Tang et al., Tencent 2020): además de expertos compartidos, **expertos exclusivos por tarea**, y varias capas (extracción progresiva). Nació para resolver el **seesaw phenomenon**: mejorar una tarea empeorando otra.
- **ESMM** (Ma et al., Alibaba 2018): para CVR (conversión tras clic), en vez de entrenar solo con clics (*sample selection bias*), modela en **todo el espacio**: $p(\text{clic}\wedge\text{conv}) = p(\text{clic})\cdot p(\text{conv}\mid\text{clic})$, supervisando pCTR y pCTCVR.
- **Ponderación de pérdidas**: fija (tuneada), *uncertainty weighting* (Kendall et al., 2018: $\sum_t e^{-s_t}\mathcal L_t + s_t$), GradNorm (Chen et al., 2018), PCGrad (Yu et al., 2020)…
""")

    # ---------------------------- LTR data ----------------------------------
    nb.md(r"""
## 🧪 3. Datos LTR de CineMatch (MovieLens-1M)
Construimos un problema LTR realista y **sin fuga**:
- **Consulta** = un usuario activo en una ventana de tiempo. **Candidatos** = películas que valoró en esa ventana (relevancia $y=\text{clip}(\text{rating}-2,0,3)$) + 30 películas no vistas muestreadas por popularidad (lo que el retrieval habría traído; $y=0$).
- **Features** calculadas **solo con el histórico anterior** a la ventana: popularidad (total y reciente), rating medio suavizado, actividad del usuario, afinidad de géneros, año de la película vs gustos del usuario y un **score de factorización matricial** (SVD truncada del módulo 05).
- **Train LTR**: features con datos < `t_val`, etiquetas en [`t_val`, `t_test`). **Test LTR**: features con datos < `t_test`, etiquetas ≥ `t_test`.
""")
    nb.md(ML_UTILS_MD)
    nb.code(ML_UTILS_CODE)
    nb.code(r'''
FAST_DEV_RUN = True
ratings, movies, users = load_movielens("1m")
movies["year"] = movies.title.str.extract(r"\((\d{4})\)").astype(float).fillna(1990).values.ravel()
GENRES = sorted({g for gs in movies.genres for g in gs.split("|")})
G = np.stack([movies.genres.str.contains(g, regex=False).values for g in GENRES], 1).astype(np.float32)
item_index = pd.Index(movies.item_id); MOVIE_G = pd.DataFrame(G, index=movies.item_id); MOVIE_YEAR = movies.set_index("item_id").year
t_val, t_test = ratings.timestamp.quantile([0.8, 0.9])
print(f"{len(ratings):,} ratings | {len(GENRES)} géneros")
''')
    nb.code(r'''
import scipy.sparse as sp
from scipy.sparse.linalg import svds

def make_ltr(hist: pd.DataFrame, labels: pd.DataFrame, n_neg=30, max_pos=30, seed=42):
    """Devuelve DataFrame (qid, item_id, rel, features…) con features SOLO de `hist`."""
    rng = np.random.default_rng(seed)
    t_end = hist.timestamp.max()
    ist = hist.groupby("item_id").agg(i_cnt=("rating", "size"), i_sum=("rating", "sum"))
    recent = hist[hist.timestamp > t_end - 30 * 86400].groupby("item_id").size().rename("i_recent")
    ist = ist.join(recent).fillna(0)
    mu = hist.rating.mean()
    ist["i_mean"] = (ist.i_sum + 10 * mu) / (ist.i_cnt + 10)
    ust = hist.groupby("user_id").agg(u_cnt=("rating", "size"), u_mean=("rating", "mean"))
    # Perfil de géneros y año medio del usuario (ponderado por rating centrado)
    h = hist.assign(w=hist.rating - 2.5)
    prof = (MOVIE_G.reindex(h.item_id).values * h.w.values[:, None])
    uprof = pd.DataFrame(prof, index=h.user_id.values).groupby(level=0).sum()
    uyear = h.assign(y=MOVIE_YEAR.reindex(h.item_id).values).groupby("user_id").y.mean()
    # MF: SVD truncada de la matriz usuario×ítem centrada (módulo 05)
    uids, iids = pd.Index(hist.user_id.unique()), pd.Index(hist.item_id.unique())
    R = sp.csr_matrix((hist.rating.values - mu, (uids.get_indexer(hist.user_id), iids.get_indexer(hist.item_id))),
                      shape=(len(uids), len(iids)))
    Uf, S, Vt = svds(R, k=32); Uf = Uf * S
    # Candidatos
    pop = ist.i_cnt ** 0.75; pop_items, pop_p = pop.index.values, (pop / pop.sum()).values
    seen = hist.groupby("user_id").item_id.agg(set)
    rows = []
    for qid, (u, g) in enumerate(labels.groupby("user_id")):
        g = g.drop_duplicates("item_id")
        if len(g) > max_pos: g = g.sample(max_pos, random_state=seed)
        pos = dict(zip(g.item_id, np.clip(g.rating - 2, 0, 3)))
        if max(pos.values()) == 0: continue
        excl = seen.get(u, set()) | set(pos)
        negs = [i for i in rng.choice(pop_items, n_neg * 2, p=pop_p) if i not in excl][:n_neg]
        for i, r in list(pos.items()) + [(i, 0) for i in dict.fromkeys(negs)]:
            rows.append((qid, u, i, r))
    d = pd.DataFrame(rows, columns=["qid", "user_id", "item_id", "rel"])
    d = d.join(ist[["i_cnt", "i_recent", "i_mean"]], on="item_id").join(ust, on="user_id").fillna(0)
    for c in ["i_cnt", "i_recent", "u_cnt"]: d[c] = np.log1p(d[c])
    up = uprof.reindex(d.user_id).fillna(0).values; ig = MOVIE_G.reindex(d.item_id).fillna(0).values
    d["genre_aff"] = (up * ig).sum(1) / (np.linalg.norm(up, axis=1) * np.linalg.norm(ig, axis=1) + 1e-9)
    d["year"] = MOVIE_YEAR.reindex(d.item_id).values
    d["year_gap"] = np.abs(d.year - uyear.reindex(d.user_id).fillna(1990).values)
    ui, ii = uids.get_indexer(d.user_id), iids.get_indexer(d.item_id)
    d["mf_score"] = np.where((ui >= 0) & (ii >= 0), (Uf[np.maximum(ui, 0)] * Vt.T[np.maximum(ii, 0)]).sum(1), 0.0)
    d["is_new_item"] = (ii < 0).astype(float)
    return d

FEATS = ["i_cnt", "i_recent", "i_mean", "u_cnt", "u_mean", "genre_aff", "year", "year_gap", "mf_score", "is_new_item"]
t0 = time.time()
ltr_tr = make_ltr(ratings[ratings.timestamp < t_val], ratings[(ratings.timestamp >= t_val) & (ratings.timestamp < t_test)])
ltr_te = make_ltr(ratings[ratings.timestamp < t_test], ratings[ratings.timestamp >= t_test], seed=7)
print(f"train: {ltr_tr.qid.nunique()} consultas, {len(ltr_tr):,} filas | test: {ltr_te.qid.nunique()} consultas | {time.time()-t0:.0f}s")
ltr_tr.groupby("rel").size().rename("nº docs por relevancia")
''')
    nb.code(r'''
# Padding a tensores [Q, L, d] para pérdidas listwise en GPU
mu_f, sd_f = ltr_tr[FEATS].mean(), ltr_tr[FEATS].std() + 1e-6
def to_padded(d: pd.DataFrame, L=None):
    groups = [g for _, g in d.groupby("qid")]
    L = L or max(len(g) for g in groups)
    Q = len(groups)
    X = np.zeros((Q, L, len(FEATS)), np.float32); Y = np.zeros((Q, L), np.float32); M = np.zeros((Q, L), bool)
    for q, g in enumerate(groups):
        n = min(len(g), L)
        X[q, :n] = ((g[FEATS] - mu_f) / sd_f).values[:n]; Y[q, :n] = g.rel.values[:n]; M[q, :n] = True
    return torch.tensor(X), torch.tensor(Y), torch.tensor(M)

Xq_tr, Yq_tr, Mq_tr = to_padded(ltr_tr)
Xq_te, Yq_te, Mq_te = to_padded(ltr_te)
rng_ = np.random.default_rng(seed); perm = rng_.permutation(len(Xq_tr)); nv = len(perm) // 10
va_q, tr_q = perm[:nv], perm[nv:]
print("train", Xq_tr.shape, "test", Xq_te.shape)

def ndcg_at(scores, Y, M, k=10):
    """NDCG@k con ganancias 2^rel−1 (scores, Y, M: tensores [Q, L])."""
    s = scores.masked_fill(~M, -1e9)
    order = s.argsort(1, descending=True)[:, :k]
    gains = (2 ** Y.gather(1, order) - 1) * M.gather(1, order)
    disc = 1 / torch.log2(torch.arange(2, k + 2, dtype=torch.float32))
    ideal = (2 ** Y.masked_fill(~M, 0).sort(1, descending=True).values[:, :k] - 1)
    idcg = (ideal * disc).sum(1)
    return ((gains * disc).sum(1) / idcg.clamp(min=1e-9))[idcg > 0].mean().item()

print(f"NDCG@10 test aleatorio: {ndcg_at(torch.rand_like(Yq_te), Yq_te, Mq_te):.4f} | "
      f"por popularidad: {ndcg_at(Xq_te[..., 0], Yq_te, Mq_te):.4f} | por MF: {ndcg_at(Xq_te[..., FEATS.index('mf_score')], Yq_te, Mq_te):.4f}")
''')

    nb.md(r"""
## 🛠️ 4. Pérdidas de LTR desde cero (PyTorch)
Mismo *scorer* (MLP 10→64→32→1) y mismo presupuesto; solo cambia la pérdida. Detalle clave de LambdaRank: los pesos $|\Delta\text{NDCG}_{ij}|$ se calculan con el ranking actual y se tratan como **constantes** (`detach`): así el gradiente de la pérdida RankNet ponderada es exactamente el $\lambda$ de LambdaRank.
""")
    nb.code(r'''
class Scorer(nn.Module):
    def __init__(self, d):
        super().__init__(); self.net = nn.Sequential(nn.Linear(d, 64), nn.ReLU(), nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 1))
    def forward(self, x):
        return self.net(x).squeeze(-1)

def loss_pointwise(s, y, m):
    return F.binary_cross_entropy_with_logits(s[m], (y[m] / 3.0))

def _pairs(s, y, m):
    diff = s.unsqueeze(2) - s.unsqueeze(1)                              # s_i − s_j  [Q, L, L]
    valid = (y.unsqueeze(2) > y.unsqueeze(1)) & m.unsqueeze(2) & m.unsqueeze(1)
    return diff, valid

def loss_ranknet(s, y, m):
    diff, valid = _pairs(s, y, m)
    return F.softplus(-diff)[valid].mean()

def loss_lambdarank(s, y, m):
    diff, valid = _pairs(s, y, m)
    with torch.no_grad():
        rank = s.masked_fill(~m, -1e9).argsort(1, descending=True).argsort(1).float() + 1
        disc = 1 / torch.log2(1 + rank)
        gain = (2 ** y - 1) * m
        idcg = ((2 ** y.masked_fill(~m, 0).sort(1, descending=True).values - 1) /
                torch.log2(torch.arange(2, y.size(1) + 2, device=y.device).float())).sum(1).clamp(min=1e-9)
        delta = (gain.unsqueeze(2) - gain.unsqueeze(1)).abs() * (disc.unsqueeze(2) - disc.unsqueeze(1)).abs() / idcg[:, None, None]
    return (F.softplus(-diff) * delta)[valid].sum() / valid.sum().clamp(min=1)

def loss_listnet(s, y, m):
    s = s.masked_fill(~m, -1e9); t = y.masked_fill(~m, -1e9)
    return -(torch.softmax(t, 1) * torch.log_softmax(s, 1)).sum(1).mean()

def loss_listmle(s, y, m):
    yy = y + torch.rand_like(y) * 1e-3                                   # desempate aleatorio
    order = yy.masked_fill(~m, -1e9).argsort(1, descending=True)
    s_sorted = s.gather(1, order).masked_fill(~m.gather(1, order), -1e9)
    lse = torch.logcumsumexp(s_sorted.flip(1), 1).flip(1)               # log Σ_{m≥r} e^{s}
    ll = (s_sorted - lse) * m.gather(1, order)
    return -ll.sum(1).mean()

LOSSES = {"Pointwise (BCE)": loss_pointwise, "RankNet": loss_ranknet, "LambdaRank": loss_lambdarank,
          "ListNet": loss_listnet, "ListMLE": loss_listmle}

def train_ltr(loss_fn, epochs=30 if FAST_DEV_RUN else 80, bs=64, lr=2e-3):
    torch.manual_seed(seed)
    model = Scorer(len(FEATS)).to(device); opt = torch.optim.Adam(model.parameters(), lr=lr)
    X, Y, M = Xq_tr.to(device), Yq_tr.to(device), Mq_tr.to(device)
    hist = []
    for ep in range(epochs):
        model.train(); p = np.random.permutation(tr_q)
        for s0 in range(0, len(p), bs):
            i = torch.as_tensor(p[s0:s0 + bs], device=device)
            loss = loss_fn(model(X[i]), Y[i], M[i])
            opt.zero_grad(); loss.backward(); opt.step()
        model.eval()
        with torch.no_grad():
            vi = torch.as_tensor(va_q, device=device)
            hist.append(ndcg_at(model(X[vi]).cpu(), Yq_tr[va_q], Mq_tr[va_q]))
    with torch.no_grad():
        test = ndcg_at(model(Xq_te.to(device)).cpu(), Yq_te, Mq_te)
    return model, hist, test

ltr_res, ltr_hist = {}, {}
for name, fn in LOSSES.items():
    t0 = time.time(); _, ltr_hist[name], ltr_res[name] = train_ltr(fn)
    print(f"{name:16s} NDCG@10 test = {ltr_res[name]:.4f}  ({time.time()-t0:.0f}s)")
''')
    nb.md(r"""
## 🏭 5. LambdaMART con LightGBM (y XGBoost)
`LGBMRanker(objective="lambdarank")` necesita los datos **agrupados por consulta** y el vector `group` con el tamaño de cada grupo. `label_gain` define $2^{y}-1$ por defecto. Alternativas: `objective="rank_xendcg"` (XE-NDCG, Bruch et al. 2019, más rápido) y en XGBoost `objective="rank:ndcg"`.
""")
    nb.code(r'''
import lightgbm as lgb
def lgb_groups(d):
    d = d.sort_values("qid", kind="mergesort")
    return d, d.groupby("qid", sort=False).size().values

tr_qids = np.unique(ltr_tr.qid)[tr_q]; va_qids = np.unique(ltr_tr.qid)[va_q]
dtr, gtr = lgb_groups(ltr_tr[ltr_tr.qid.isin(tr_qids)]); dva, gva = lgb_groups(ltr_tr[ltr_tr.qid.isin(va_qids)])
t0 = time.time()
ranker = lgb.LGBMRanker(objective="lambdarank", n_estimators=1000, learning_rate=0.05, num_leaves=31,
                        min_child_samples=50, subsample=0.8, subsample_freq=1, colsample_bytree=0.9,
                        lambdarank_truncation_level=20, random_state=seed, verbose=-1)
ranker.fit(dtr[FEATS], dtr.rel, group=gtr, eval_set=[(dva[FEATS], dva.rel)], eval_group=[gva],
           eval_at=[10], callbacks=[lgb.early_stopping(50, verbose=False)])
dte, _ = lgb_groups(ltr_te)
s_te = ranker.predict(dte[FEATS])
S = torch.full(Yq_te.shape, -1e9)
pos_in_q = dte.groupby("qid").cumcount().values
q_index = pd.Index(np.unique(ltr_te.qid)).get_indexer(dte.qid)
S[q_index, pos_in_q] = torch.tensor(s_te, dtype=torch.float32)
ltr_res["LambdaMART (LightGBM)"] = ndcg_at(S, Yq_te, Mq_te)
print(f"LambdaMART NDCG@10 test = {ltr_res['LambdaMART (LightGBM)']:.4f} | {ranker.best_iteration_} árboles | {time.time()-t0:.0f}s")
''')
    nb.code(r'''
fig, axes = plt.subplots(1, 3, figsize=(17, 4))
for name, h in ltr_hist.items():
    axes[0].plot(h, label=name)
axes[0].set_title("NDCG@10 de validación por época"); axes[0].set_xlabel("época"); axes[0].legend(fontsize=7)
r = pd.Series(ltr_res).sort_values()
axes[1].barh(r.index, r.values, color=["#dd8452" if "LightGBM" in i else "#4c72b0" for i in r.index])
axes[1].set_xlim(r.min() * 0.95, r.max() * 1.02); axes[1].set_title("NDCG@10 en test temporal")
for i, v in enumerate(r.values): axes[1].text(v, i, f" {v:.4f}", va="center", fontsize=8)
imp = pd.Series(ranker.booster_.feature_importance("gain"), index=FEATS).sort_values()
axes[2].barh(imp.index, imp.values, color="#55a868"); axes[2].set_title("LambdaMART: importancia (gain)")
plt.tight_layout(); plt.show()
''')
    nb.md(r"""
**Lectura típica**: las pérdidas pairwise/listwise suelen superar a la pointwise en NDCG, y **LambdaMART sigue siendo durísimo** con features densas: Qin et al. (ICLR 2021, *Are Neural Rankers still Outperformed by GBDT?*) mostraron que los rankers neuronales necesitan trucos específicos (transformación log1p de features, *self-attention* entre documentos, data augmentation) para empatarle en benchmarks como MSLR-WEB30K. Los modelos profundos ganan cuando hay IDs, texto o secuencias (módulos 06, 09, 11).

## 🎯 6. Sesgo de posición: simulación, IPS y PAL
Simulamos el mundo real: un **sistema anterior** (logging policy) ordenó los candidatos de train por popularidad + ruido; el usuario examina la posición $k$ con probabilidad $\theta_k = k^{-1}$ y hace clic si examina y le parece relevante: $\gamma(y) = 0{,}05 + 0{,}95\cdot\frac{2^y-1}{7}$. Cada consulta se muestra en varias **sesiones** (con ruido distinto en la política) y el 10 % del tráfico se **aleatoriza** (como hacen los equipos serios para estimar $\theta$).
""")
    nb.code(r'''
rng_ = np.random.default_rng(seed)
ETA = 1.0
N_SESSIONS = 10 if FAST_DEV_RUN else 30            # cada consulta se "muestra" varias veces (sesiones)
Lmax = Xq_tr.shape[1]; Q_tr = len(Xq_tr)
theta_true = 1 / np.arange(1, Lmax + 1) ** ETA
qidx = np.tile(np.arange(Q_tr), N_SESSIONS)                              # sesión → consulta
Y_np, M_np = Yq_tr.numpy()[qidx], Mq_tr.numpy()[qidx]
logging_score = Xq_tr[..., 0].numpy()[qidx] + rng_.normal(0, 1.0, Y_np.shape)   # popularidad + ruido
randomized = rng_.random(len(Y_np)) < 0.10
logging_score[randomized] = rng_.random((randomized.sum(), Lmax))
logging_score[~M_np] = -1e9
position = np.argsort(np.argsort(-logging_score, 1), 1)                     # 0 = arriba
gamma = 0.05 + 0.95 * (2 ** Y_np - 1) / 7
clicks = (rng_.random(Y_np.shape) < theta_true[position] * gamma) & M_np

# Estimación de θ_k con el tráfico aleatorizado: CTR(k)/CTR(1), y ajuste de ley de potencias
ctr_k = np.array([clicks[randomized][position[randomized] == k].mean() for k in range(Lmax)])
ks = np.arange(1, Lmax + 1); ok = ctr_k > 0
eta_hat = -np.polyfit(np.log(ks[ok][:20]), np.log(ctr_k[ok][:20] / ctr_k[0]), 1)[0]
theta_hat = 1 / ks ** eta_hat
plt.figure(figsize=(7, 3.6))
plt.plot(ks[:25], theta_true[:25], "k-", label="θ verdadero = 1/k")
plt.plot(ks[:25], (ctr_k / ctr_k[0])[:25], "o", ms=4, label="CTR(k)/CTR(1) en tráfico aleatorizado")
plt.plot(ks[:25], theta_hat[:25], "--", label=f"ajuste potencia (η̂ = {eta_hat:.2f})")
plt.xlabel("posición k"); plt.ylabel("P(examinar | k)"); plt.title("Curva de propensión de examen"); plt.legend(); plt.show()
print(f"CTR global de la simulación: {clicks[M_np].mean():.3f}")
''')
    nb.code(r'''
class PALModel(nn.Module):
    """p(clic) = p(visto | posición) · p(relevante | x). En serving se usa solo el segundo término."""
    def __init__(self, d, Lmax):
        super().__init__(); self.rel = Scorer(d); self.pos = nn.Embedding(Lmax, 1); nn.init.constant_(self.pos.weight, 0.0)
    def forward(self, x, pos=None):
        s = self.rel(x)
        if pos is None:
            return s
        return F.logsigmoid(s) + F.logsigmoid(self.pos(pos).squeeze(-1))     # log p(clic)

def train_click_model(mode, epochs=6 if FAST_DEV_RUN else 15, bs=256):
    torch.manual_seed(seed)
    model = (PALModel(len(FEATS), Lmax) if mode == "PAL" else Scorer(len(FEATS))).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=2e-3)
    X, C, M = Xq_tr[qidx].to(device), torch.tensor(clicks, dtype=torch.float32, device=device), torch.as_tensor(M_np, device=device)
    P = torch.as_tensor(position, device=device)
    W = torch.as_tensor(np.clip(theta_hat, 0.05, 1)[position], dtype=torch.float32, device=device)
    Yrel = torch.as_tensor(Y_np, device=device)
    for ep in range(epochs):
        p = np.random.permutation(len(X))
        for s0 in range(0, len(p), bs):
            i = torch.as_tensor(p[s0:s0 + bs], device=device); m = M[i]
            if mode == "Naive (clics crudos)":
                loss = F.binary_cross_entropy_with_logits(model(X[i])[m], C[i][m])
            elif mode == "IPS":
                s = model(X[i])[m]; c = C[i][m] / W[i][m]                      # c/θ_k (puede ser >1)
                loss = -(c * F.logsigmoid(s) + (1 - c) * F.logsigmoid(-s)).mean()
            elif mode == "PAL":
                logp = model(X[i], P[i])[m]
                loss = -(C[i][m] * logp + (1 - C[i][m]) * torch.log1p(-logp.exp().clamp(max=1 - 1e-6))).mean()
            else:  # oráculo: relevancia verdadera (cota superior)
                loss = loss_pointwise(model(X[i]), Yrel[i], m)
            opt.zero_grad(); loss.backward(); opt.step()
    with torch.no_grad():
        return ndcg_at(model(Xq_te.to(device)).cpu(), Yq_te, Mq_te)

pb_res = {mode: train_click_model(mode) for mode in ["Naive (clics crudos)", "IPS", "PAL", "Oráculo (relevancia real)"]}
s = pd.Series(pb_res)
plt.figure(figsize=(7, 3)); plt.barh(s.index, s.values, color=["#c44e52", "#4c72b0", "#55a868", "#8c8c8c"])
plt.xlim(s.min() * 0.95, s.max() * 1.02); plt.title("NDCG@10 (relevancia real) entrenando con clics sesgados")
for i, v in enumerate(s.values): plt.text(v, i, f" {v:.4f}", va="center", fontsize=8)
plt.show()
''')
    nb.md(r"""
El modelo *naive* aprende en parte "lo que la política anterior puso arriba" (popularidad). IPS corrige en esperanza pero tiene **varianza alta** (pesos $1/\theta_k$ grandes en posiciones bajas; por eso se recortan, *clipping*). PAL suele ser más estable y es lo que se ve en producción (Huawei PAL, *shallow tower* de YouTube).

## 🧩 7. Multi-task: arquitecturas
""")
    nb.code(MTL_MODELS)
    nb.code(r'''
# Diagrama 3 — Shared-Bottom vs MMoE vs PLE (CGC)
fig, axes = plt.subplots(1, 3, figsize=(17, 5.2))
sb = {"x": (2.5, 0.3, 5, 0.9, "embeddings compartidos", "emb"), "b": (2.5, 2.0, 5, 1.2, "Shared bottom (MLP)", "mlp"),
      "t1": (0.5, 4.3, 2.6, 1, "torre clic", "inter"), "t2": (3.7, 4.3, 2.6, 1, "torre long_view", "inter"), "t3": (6.9, 4.3, 2.6, 1, "torre like", "inter")}
draw_blocks(axes[0], sb, [("x", "b"), ("b", "t1"), ("b", "t2"), ("b", "t3")], "Shared-Bottom", ylim=(0, 6))
mm = {"x": (2.5, 0.2, 5, 0.8, "embeddings compartidos", "emb"),
      "e1": (0.3, 1.6, 2.0, 0.9, "experto 1", "mlp"), "e2": (2.7, 1.6, 2.0, 0.9, "experto 2", "mlp"),
      "e3": (5.1, 1.6, 2.0, 0.9, "experto 3", "mlp"), "e4": (7.5, 1.6, 2.0, 0.9, "experto 4", "mlp"),
      "g1": (0.5, 3.2, 2.6, 0.8, "puerta₁ softmax", "gate"), "g2": (3.7, 3.2, 2.6, 0.8, "puerta₂", "gate"), "g3": (6.9, 3.2, 2.6, 0.8, "puerta₃", "gate"),
      "t1": (0.5, 4.6, 2.6, 0.9, "torre clic", "inter"), "t2": (3.7, 4.6, 2.6, 0.9, "torre lv", "inter"), "t3": (6.9, 4.6, 2.6, 0.9, "torre like", "inter")}
arr = [("x", f"e{i}") for i in range(1, 5)] + [(f"e{i}", f"g{j}") for i in range(1, 5) for j in range(1, 4)] + [(f"g{j}", f"t{j}") for j in range(1, 4)]
draw_blocks(axes[1], mm, arr, "MMoE: cada tarea mezcla expertos a su manera", ylim=(0, 6))
pl = {"x": (2.5, 0.2, 5, 0.8, "embeddings compartidos", "emb"),
      "a": (0.2, 1.6, 2.6, 0.9, "expertos\nexclusivos clic", "mlp"), "s": (3.7, 1.6, 2.6, 0.9, "expertos\nCOMPARTIDOS", "out"),
      "c": (7.2, 1.6, 2.6, 0.9, "expertos\nexclusivos like", "mlp"),
      "g1": (0.5, 3.2, 2.6, 0.8, "puerta clic", "gate"), "g3": (6.9, 3.2, 2.6, 0.8, "puerta like", "gate"),
      "t1": (0.5, 4.6, 2.6, 0.9, "torre clic", "inter"), "t3": (6.9, 4.6, 2.6, 0.9, "torre like", "inter")}
draw_blocks(axes[2], pl, [("x", "a"), ("x", "s"), ("x", "c"), ("a", "g1"), ("s", "g1"), ("s", "g3"), ("c", "g3"), ("g1", "t1"), ("g3", "t3")],
            "PLE / CGC: exclusivos + compartidos (×L capas)", ylim=(0, 6))
plt.tight_layout(); plt.show()
''')
    nb.md(r"""
### 🧪 7.1 Experimento controlado: correlación entre tareas y *seesaw*
Reproducimos el experimento sintético del paper de MMoE (Ma et al., 2018): dos tareas de regresión cuya **correlación** controlamos con el coseno $p$ entre sus vectores de pesos:
$$y_t = \mathbf w_t^\top\mathbf x + \sum_{m=1}^{10}\sin(\alpha_m\mathbf w_t^\top\mathbf x+\beta_m)+\varepsilon,\quad \mathbf w_1=c\,\mathbf u_1,\ \mathbf w_2=c\,(p\,\mathbf u_1+\sqrt{1-p^2}\,\mathbf u_2)$$
Con $p=1$ las tareas son la misma; con $p=0$ no comparten nada. Esperamos: Shared-Bottom se degrada al bajar $p$; MMoE/PLE aguantan mejor.
""")
    nb.code(r'''
def mmoe_synthetic(p, n=12000, d=100, c=1.0, seed=0):
    rng_ = np.random.default_rng(seed)
    u1, u2 = np.linalg.qr(rng_.normal(size=(d, 2)))[0].T
    w1, w2 = c * u1, c * (p * u1 + np.sqrt(1 - p ** 2) * u2)
    X = rng_.normal(size=(n, d)).astype(np.float32)
    alpha, beta = rng_.normal(size=10), rng_.normal(size=10)
    f = lambda w: X @ w + np.sin(np.outer(X @ w, alpha) + beta).sum(1)
    Y = np.stack([f(w1), f(w2)], 1) + rng_.normal(0, 0.1, (n, 2))
    return X, Y.astype(np.float32)

class DenseEnc(nn.Module):
    def __init__(self, d): super().__init__(); self.d_out = d
    def forward(self, x): return x

def run_synth(kind, p, seed_=0, epochs=60):
    X, Y = mmoe_synthetic(p, seed=seed_); Xtr, Ytr, Xte, Yte = X[:10000], Y[:10000], X[10000:], Y[10000:]
    torch.manual_seed(seed_)
    core = {"Shared-Bottom": lambda: SharedBottom(100, 2, bottom=(64, 32), tower=(16,)),
            "MMoE": lambda: MMoE(100, 2, n_experts=8, expert=(32, 16), tower=(16,)),
            "PLE": lambda: PLE(100, 2, levels=1, d_hidden=16, n_spec=3, n_shared=3, tower=(16,))}[kind]()
    m = MTLNet(DenseEnc(100), core).to(device); opt = torch.optim.Adam(m.parameters(), lr=1e-3)
    Xt, Yt = torch.tensor(Xtr, device=device), torch.tensor(Ytr, device=device)
    for ep in range(epochs):
        perm = torch.randperm(len(Xt), device=device)
        for s0 in range(0, len(Xt), 128):
            i = perm[s0:s0 + 128]; out, _ = m(Xt[i]); loss = F.mse_loss(out, Yt[i])
            opt.zero_grad(); loss.backward(); opt.step()
    with torch.no_grad():
        out, _ = m(torch.tensor(Xte, device=device))
    return ((out.cpu().numpy() - Yte) ** 2).mean(0)                       # MSE por tarea

corrs = [1.0, 0.9, 0.5, 0.0] if FAST_DEV_RUN else [1.0, 0.9, 0.7, 0.5, 0.3, 0.0]
seeds = [0, 1] if FAST_DEV_RUN else [0, 1, 2, 3, 4]
synth = {k: [] for k in ["Shared-Bottom", "MMoE", "PLE"]}
t0 = time.time()
for p in corrs:
    for k in synth:
        synth[k].append(np.mean([run_synth(k, p, s, epochs=25 if FAST_DEV_RUN else 60) for s in seeds], 0))
print(f"{time.time()-t0:.0f}s")
fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
for t in range(2):
    for k, v in synth.items():
        axes[t].plot(corrs, [x[t] for x in v], "o-", label=k)
    axes[t].set_title(f"Tarea {t+1}: MSE test vs correlación"); axes[t].set_xlabel("correlación p entre tareas"); axes[t].invert_xaxis(); axes[t].legend()
plt.tight_layout(); plt.show()
''')

    nb.md(r"""
## 🧪 8. Multi-task con datos reales: KuaiRand-Pure
**KuaiRand** (Gao et al., CIKM 2022) son logs de la app de vídeo corto Kuaishou con **muchas señales por impresión** (`is_click`, `long_view`, `is_like`, `is_follow`, `is_comment`, `is_forward`, `is_hate`, `play_time_ms`…) y, como rareza valiosa, una parte del tráfico con **exposición aleatoria** (útil para debiasing). Usamos **KuaiRand-Pure** (~200 MB, 27 k usuarios, 7 583 vídeos) y tres tareas: **clic**, **visionado largo** y **like**. Para CineMatch es el análogo de la fila de *trailers/clips* de la home.

Descarga oficial (Zenodo, según el README del repo `chongminggao/KuaiRand`): `https://zenodo.org/records/10439422/files/KuaiRand-Pure.tar.gz`.
""")
    nb.code(r'''
import urllib.request
MAX_ROWS = 600_000 if FAST_DEV_RUN else None
''')
    nb.code(KUAI_LOADER)
    nb.code(r'''
logs, kusers, kvideos = load_kuairand(max_rows=MAX_ROWS)
kdf, KX, KY, kfield_dims, ksplit = prepare_kuairand(logs, kusers, kvideos)
print(KX.shape, "| tasas por tarea:", dict(zip(TASKS, KY.mean(0).round(4))))
print("P(long_view | no clic) =", round(KY[KY[:, 0] == 0, 1].mean(), 4), "| P(like | no clic) =", round(KY[KY[:, 0] == 0, 2].mean(), 4))
Ktr, Kva, Kte = (ksplit == s for s in ["train", "val", "test"])
C = np.corrcoef(KY[Ktr].T)
plt.figure(figsize=(4, 3.4)); plt.imshow(C, cmap="Blues", vmin=0, vmax=1); plt.colorbar()
plt.xticks(range(3), TASKS); plt.yticks(range(3), TASKS)
for i in range(3):
    for j in range(3): plt.text(j, i, f"{C[i,j]:.2f}", ha="center", va="center")
plt.title("Correlación entre etiquetas (train)"); plt.show()
''')
    nb.code(MTL_TRAIN)
    nb.code(r'''
EPOCHS_MTL = 1 if FAST_DEV_RUN else 3
mtl_res, mtl_models = {}, {}
for kind in ["Shared-Bottom", "MMoE", "PLE"]:
    torch.manual_seed(seed); t0 = time.time()
    m = train_mtl(build_mtl(kind, kfield_dims, 3), KX[Ktr], KY[Ktr], KX[Kva], KY[Kva], epochs=EPOCHS_MTL, verbose=True)
    P = predict_mtl(m, KX[Kte])
    mtl_res[kind] = {t: roc_auc_score(KY[Kte][:, i], P[:, i]) for i, t in enumerate(TASKS)} | {"seg": time.time() - t0}
    mtl_models[kind] = m
# Referencia: un modelo independiente por tarea (single-task)
single = {}
for i, t in enumerate(TASKS):
    torch.manual_seed(seed)
    m = train_mtl(build_mtl("Shared-Bottom", kfield_dims, 1), KX[Ktr], KY[Ktr][:, [i]], KX[Kva], KY[Kva][:, [i]], epochs=EPOCHS_MTL)
    single[t] = roc_auc_score(KY[Kte][:, i], predict_mtl(m, KX[Kte])[:, 0])
mtl_res["Single-task (×3 modelos)"] = single
pd.DataFrame(mtl_res).T.round(4)
''')
    nb.code(r'''
# Gráfico — Utilización de expertos por tarea (puertas de MMoE)
with torch.no_grad():
    _, gates = mtl_models["MMoE"](torch.as_tensor(KX[Kte][:20000], device=device).long())
G_mean = gates.mean(1).cpu().numpy()                                   # [T, n_exp]
plt.figure(figsize=(6, 2.6)); plt.imshow(G_mean, cmap="YlOrRd", aspect="auto"); plt.colorbar(label="peso medio de la puerta")
plt.yticks(range(3), TASKS); plt.xlabel("experto"); plt.title("MMoE: ¿qué expertos usa cada tarea?")
for i in range(G_mean.shape[0]):
    for j in range(G_mean.shape[1]): plt.text(j, i, f"{G_mean[i,j]:.2f}", ha="center", va="center", fontsize=7)
plt.show()
''')
    nb.md(r"""
### 🧪 8.1 Frente de Pareto: ¿cuánto clic cuesta un like?
Barremos el peso de la tarea *like* $w_\text{like}$ y medimos (AUC clic, AUC like). Un modelo **domina** a otro si mejora ambas. El *seesaw* se ve como una curva en la que mejorar una tarea empeora la otra; una arquitectura mejor **empuja el frente hacia arriba a la derecha**.
""")
    nb.code(r'''
weights = [0.2, 1.0, 5.0] if FAST_DEV_RUN else [0.1, 0.3, 1.0, 3.0, 10.0]
pareto = []
for kind in ["Shared-Bottom", "MMoE", "PLE"]:
    for w in weights:
        torch.manual_seed(seed)
        m = train_mtl(build_mtl(kind, kfield_dims, 3), KX[Ktr], KY[Ktr], KX[Kva], KY[Kva], task_w=[1.0, 1.0, w], epochs=EPOCHS_MTL)
        P = predict_mtl(m, KX[Kte])
        pareto.append({"modelo": kind, "w_like": w, "auc_click": roc_auc_score(KY[Kte][:, 0], P[:, 0]),
                       "auc_like": roc_auc_score(KY[Kte][:, 2], P[:, 2])})
pf = pd.DataFrame(pareto)
plt.figure(figsize=(6.5, 4.5))
for kind, g in pf.groupby("modelo"):
    g = g.sort_values("w_like"); plt.plot(g.auc_click, g.auc_like, "o-", label=kind)
    for _, r in g.iterrows(): plt.annotate(f"w={r.w_like:g}", (r.auc_click, r.auc_like), fontsize=7, xytext=(3, 3), textcoords="offset points")
plt.xlabel("AUC clic"); plt.ylabel("AUC like"); plt.title("Frente de Pareto clic vs like (test)"); plt.legend(); plt.show()
''')
    nb.md(r"""
### 8.2 ESMM: CVR en todo el espacio
"Conversión" = `long_view` tras clic. Un modelo **CVR naive** se entrena solo con impresiones clicadas → en serving puntúa **todas** las impresiones (sesgo de selección). ESMM entrena en todo el espacio: $p(\text{clic}\wedge\text{lv}) = p(\text{clic})\cdot p(\text{lv}\mid\text{clic})$.
""")
    nb.code(r'''
class ESMM(nn.Module):
    def __init__(self, field_dims, k=16):
        super().__init__()
        self.enc = CatEncoder(field_dims, k)
        self.ctr = mlp([self.enc.d_out, 256, 128, 1], last_act=False)
        self.cvr = mlp([self.enc.d_out, 256, 128, 1], last_act=False)
    def forward(self, x):
        h = self.enc(x)
        return torch.sigmoid(self.ctr(h)).squeeze(1), torch.sigmoid(self.cvr(h)).squeeze(1)

def train_esmm(epochs=EPOCHS_MTL, bs=4096):
    torch.manual_seed(seed); m = ESMM(kfield_dims).to(device); opt = torch.optim.Adam(m.parameters(), lr=1e-3)
    Xt = torch.as_tensor(KX[Ktr], device=device); Yt = torch.as_tensor(KY[Ktr], device=device)
    click, ctcvr = Yt[:, 0], Yt[:, 0] * Yt[:, 1]
    for ep in range(epochs):
        perm = torch.randperm(len(Xt), device=device)
        for s0 in range(0, len(Xt), bs):
            i = perm[s0:s0 + bs]; pctr, pcvr = m(Xt[i].long())
            loss = F.binary_cross_entropy(pctr.clamp(1e-6, 1 - 1e-6), click[i]) + \
                   F.binary_cross_entropy((pctr * pcvr).clamp(1e-6, 1 - 1e-6), ctcvr[i])
            opt.zero_grad(); loss.backward(); opt.step()
    return m

esmm = train_esmm()
clicked_tr = Ktr & (KY[:, 0] == 1)
torch.manual_seed(seed)
naive_cvr = train_mtl(build_mtl("Shared-Bottom", kfield_dims, 1), KX[clicked_tr], KY[clicked_tr][:, [1]],
                      KX[Kva & (KY[:, 0] == 1)], KY[Kva & (KY[:, 0] == 1)][:, [1]], epochs=EPOCHS_MTL)
with torch.no_grad():
    pctr, pcvr = (t.cpu().numpy() for t in esmm(torch.as_tensor(KX[Kte], device=device).long()))
p_naive = predict_mtl(naive_cvr, KX[Kte])[:, 0]
y_ctcvr = KY[Kte][:, 0] * KY[Kte][:, 1]; clk = KY[Kte][:, 0] == 1
print(pd.DataFrame({
    "CVR-AUC (sobre clicados)": [roc_auc_score(KY[Kte][clk, 1], p_naive[clk]), roc_auc_score(KY[Kte][clk, 1], pcvr[clk])],
    "CTCVR-AUC (todas las impresiones)": [roc_auc_score(y_ctcvr, p_naive * pctr), roc_auc_score(y_ctcvr, pcvr * pctr)]},
    index=["CVR naive (+ pCTR de ESMM)", "ESMM"]).round(4))
''')
    nb.md(r"""
## 🎛️ 9. Fusión de objetivos: el score final de la home
El ranker multi-tarea devuelve $(\hat p_\text{clic}, \hat p_\text{lv}, \hat p_\text{like})$. La lista se ordena por una **fórmula de fusión** que decide el producto. Dos familias habituales:
- **Suma ponderada**: $s = \sum_t w_t\,\hat p_t$ (o sobre valores esperados: $\hat p_\text{clic}\cdot E[\text{minutos}]$).
- **Producto de potencias**: $s=\prod_t \hat p_t^{\,w_t}$ (equivale a suma ponderada de log-probabilidades; usado públicamente en descripciones de sistemas de vídeo corto).

Los pesos $w_t$ **no se aprenden offline**: se tunean con A/B tests u optimización bayesiana online (módulo 15) porque representan **trade-offs de negocio**. Offline podemos al menos ver el efecto sobre una métrica proxy: NDCG por usuario con ganancia de negocio $g = 1\cdot\text{clic} + 2\cdot\text{lv} + 4\cdot\text{like}$.
""")
    nb.code(r'''
Pt = predict_mtl(mtl_models["PLE"], KX[Kte])
test_df = kdf.loc[Kte, ["user_id"]].copy()
test_df["gain"] = KY[Kte] @ np.array([1.0, 2.0, 4.0])
def business_ndcg(score, k=10):
    d = test_df.assign(s=score)
    vals = []
    for _, g in d.groupby("user_id"):
        if len(g) < 5 or g.gain.sum() == 0: continue
        top = g.nlargest(k, "s").gain.values; ideal = np.sort(g.gain.values)[::-1][:k]
        disc = 1 / np.log2(np.arange(2, len(top) + 2))
        vals.append((top * disc).sum() / (ideal * disc[:len(ideal)]).sum())
    return np.mean(vals)

grid = [0.0, 0.5, 1.0, 2.0]
Hm = np.zeros((len(grid), len(grid)))
for a, w_lv in enumerate(grid):
    for b, w_like in enumerate(grid):
        Hm[a, b] = business_ndcg(np.log(Pt[:, 0] + 1e-9) + w_lv * np.log(Pt[:, 1] + 1e-9) + w_like * np.log(Pt[:, 2] + 1e-9))
plt.figure(figsize=(5, 4)); plt.imshow(Hm, cmap="viridis", origin="lower"); plt.colorbar(label="NDCG@10 de negocio")
plt.xticks(range(len(grid)), grid); plt.yticks(range(len(grid)), grid); plt.xlabel("w_like"); plt.ylabel("w_long_view")
for a in range(len(grid)):
    for b in range(len(grid)): plt.text(b, a, f"{Hm[a,b]:.3f}", ha="center", va="center", color="w", fontsize=8)
plt.title("Fusión s = p_clic · p_lv^w_lv · p_like^w_like"); plt.show()
print("Solo clic:", round(Hm[0, 0], 4), "| mejor combinación:", round(Hm.max(), 4))
''')
    nb.md(r"""
## 🏭 10. En producción
- **YouTube** (Zhao et al., RecSys 2019, *Recommending What Video to Watch Next*): ranker multi-tarea con **MMoE** que predice objetivos de *engagement* (clics, tiempo) y de *satisfacción* (likes, encuestas), combinados con una fórmula de pesos tuneada manualmente; un **shallow tower** con la posición (y el dispositivo) absorbe el sesgo de selección y se elimina en serving.
- **YouTube 2016** (Covington et al.): para predecir **tiempo de visionado** usaban *weighted logistic regression*: positivos ponderados por el tiempo visto, negativos con peso 1; los *odds* aprendidos aproximan el tiempo esperado.
- **Tencent** (Tang et al., 2020): PLE desplegado en el sistema de recomendación de vídeo de Tencent Video, con mejoras en tiempo de visionado y *view-through rate* reportadas en el paper.
- **Alibaba** (Ma et al., 2018): ESMM en la publicidad de Taobao para CVR.
- **Búsqueda (Bing, Airbnb, Amazon…)**: LambdaMART sigue siendo base o componente. Airbnb (Haldar et al., KDD 2019, *Applying Deep Learning to Airbnb Search*) describe la migración de GBDT a redes y lo difícil que fue superarlo.
- **Netflix**: la home se construye como un problema de ranking de filas y de títulos dentro de filas, con varios objetivos (corto y largo plazo); lo verás en el módulo 13 (*page-level optimization*).

## 🧠 11. Secretos de la élite
1. **El seesaw es la norma, no la excepción.** Añadir una tarea casi siempre mueve otra. Mide **todas** las tareas en cada experimento y reporta el frente de Pareto, no un número.
2. **Las escalas de las pérdidas engañan.** Una tarea rara (like ≈ 1–3 %) tiene una BCE pequeña y gradientes que el clic ahoga. Prueba *uncertainty weighting*, normalizar por la entropía base (NE por tarea) o *loss weighting* tuneado.
3. **Calibra cada cabeza antes de fusionar.** La fusión multiplica probabilidades: si $\hat p_\text{like}$ está inflada ×2, $w_\text{like}$ ya no significa lo que crees y cada reentreno cambia el producto.
4. **Los pesos de fusión son decisiones de producto.** Se tunean online (A/B, Bayesian optimization, bandits), y conviene un *guardrail* para cada objetivo (módulo 15).
5. **El sesgo de posición se cuela por las features**: cualquier feature correlacionada con la posición anterior (CTR histórico del ítem en la home) lo arrastra. Usa *shallow tower*/PAL y estima la propensión con intervenciones aleatorias pequeñas.
6. **GBDT/LambdaMART no está muerto**: con features densas, LambdaMART sigue siendo un rival durísimo (Qin et al., 2021). Muchos equipos lo usan como *ensemble* o como *teacher* de destilación.
7. **Define bien las etiquetas**: "long view" depende de la duración del vídeo (umbral relativo vs absoluto), "like" depende de la UI. Cambiar la definición cambia el modelo más que cualquier arquitectura.
8. **NDCG offline ≠ engagement online.** LTR optimiza una lista estática; el usuario interactúa con una página entera y con su propio feedback loop. Valida con interleaving/A/B (módulo 15).

## ⚠️ 12. Errores comunes
- Mezclar consultas en un *batch* de pérdida listwise sin máscara de padding (los documentos de relleno compiten en la softmax).
- Pasar a LightGBM `group` desordenado respecto a las filas (debe ser contiguo por consulta).
- Evaluar NDCG con *sampled candidates* distintos entre modelos (protocolo del módulo 02).
- Entrenar CVR solo con clics y servirlo sobre todas las impresiones (sesgo de selección → ESMM).
- Pesos IPS sin recorte → varianza enorme y entrenamiento inestable.
- Escoger la arquitectura MTL mirando solo la tarea principal.

## 📝 13. Autoevaluación
1. ¿Por qué no se puede optimizar NDCG directamente con descenso por gradiente?
<details><summary>Respuesta</summary>Porque depende de los scores solo a través del orden (argsort): es constante a trozos y su gradiente es cero casi en todas partes.</details>

2. ¿Qué añade LambdaRank a RankNet?
<details><summary>Respuesta</summary>Multiplica el gradiente de cada par por |ΔNDCG| del intercambio, concentrando el aprendizaje en los errores que afectan al top de la lista.</details>

3. ¿Qué es LambdaMART?
<details><summary>Respuesta</summary>Gradient boosting de árboles (MART) donde cada árbol se ajusta a los gradientes lambda de LambdaRank.</details>

4. En el modelo PBM, ¿por qué entrenar con clics crudos aprende el sesgo de la política anterior?
<details><summary>Respuesta</summary>Porque P(clic)=θ_k·γ(x) y la posición k la decidió la política anterior; los ítems que esa política ponía arriba tienen más clics independientemente de su relevancia.</details>

5. ¿Qué diferencia a PLE de MMoE?
<details><summary>Respuesta</summary>PLE separa expertos exclusivos por tarea y expertos compartidos, con puertas que solo ven su subconjunto, y apila varias capas (extracción progresiva); MMoE comparte todos los expertos entre todas las tareas.</details>

6. ¿Qué problema resuelve ESMM y cómo?
<details><summary>Respuesta</summary>El sesgo de selección y la escasez de datos de CVR: modela pCTCVR = pCTR·pCVR sobre todas las impresiones, supervisando pCTR y pCTCVR, de modo que pCVR se aprende implícitamente en todo el espacio.</details>

7. Te piden "optimizar a la vez clic y like" con un solo número. ¿Qué respondes?
<details><summary>Respuesta</summary>Que es un problema multi-objetivo: hay que mostrar el frente de Pareto, elegir un punto según el trade-off de negocio y validarlo online; el peso de fusión es una decisión de producto.</details>

## 📚 14. Referencias
- Burges, C. et al. (2005). *Learning to Rank using Gradient Descent* (RankNet). ICML.
- Burges, C. (2010). *From RankNet to LambdaRank to LambdaMART: An Overview*. Microsoft Research Tech. Report MSR-TR-2010-82.
- Cao, Z. et al. (2007). *Learning to Rank: From Pairwise Approach to Listwise Approach* (ListNet). ICML.
- Xia, F. et al. (2008). *Listwise Approach to Learning to Rank: Theory and Algorithm* (ListMLE). ICML.
- Wang, X. et al. (2018). *The LambdaLoss Framework for Ranking Metric Optimization*. CIKM.
- Qin, Z. et al. (2021). *Are Neural Rankers still Outperformed by Gradient Boosted Decision Trees?* ICLR. https://openreview.net/forum?id=Ut1vF_q_vC
- Joachims, T., Swaminathan, A., Schnabel, T. (2017). *Unbiased Learning-to-Rank with Biased Feedback*. WSDM. https://arxiv.org/abs/1608.04468
- Wang, X. et al. (2018). *Position Bias Estimation for Unbiased Learning to Rank in Personal Search*. WSDM.
- Guo, H. et al. (2019). *PAL: A Position-bias Aware Learning Framework for CTR Prediction in Live Recommender Systems*. RecSys.
- Ma, J. et al. (2018). *Modeling Task Relationships in Multi-task Learning with Multi-gate Mixture-of-Experts*. KDD.
- Zhao, Z. et al. (2019). *Recommending What Video to Watch Next: A Multitask Ranking System*. RecSys.
- Tang, H. et al. (2020). *Progressive Layered Extraction (PLE): A Novel Multi-Task Learning (MTL) Model for Personalized Recommendations*. RecSys.
- Ma, X. et al. (2018). *Entire Space Multi-Task Model: An Effective Approach for Estimating Post-Click Conversion Rate* (ESMM). SIGIR. https://arxiv.org/abs/1804.07931
- Kendall, A., Gal, Y., Cipolla, R. (2018). *Multi-Task Learning Using Uncertainty to Weigh Losses*. CVPR. https://arxiv.org/abs/1705.07115
- Chen, Z. et al. (2018). *GradNorm*. ICML. https://arxiv.org/abs/1711.02257 · Yu, T. et al. (2020). *Gradient Surgery for Multi-Task Learning* (PCGrad). https://arxiv.org/abs/2001.06782
- Covington, P., Adams, J., Sargin, E. (2016). *Deep Neural Networks for YouTube Recommendations*. RecSys.
- Haldar, M. et al. (2019). *Applying Deep Learning to Airbnb Search*. KDD. https://arxiv.org/abs/1810.09591
- Gao, C. et al. (2022). *KuaiRand: An Unbiased Sequential Recommendation Dataset with Randomly Exposed Videos*. CIKM. https://arxiv.org/abs/2208.08696 · Datos: https://kuairand.com · https://github.com/chongminggao/KuaiRand
- Chen, J. et al. (2020). *Bias and Debias in Recommender System: A Survey and Future Directions*. https://arxiv.org/abs/2010.03240
- Librerías: LightGBM ranking (https://lightgbm.readthedocs.io), XGBoost LTR (https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html), TensorFlow Ranking, allRank (PyTorch, Allegro), FuxiCTR multitask (MMoE/PLE/ESMM).
""")
    nb.save(f"recsys-course/{MOD}/{MOD}.ipynb")


def build_project():
    path = f"recsys-course/{MOD}/07_proyecto_ranker_multiobjetivo.ipynb"
    nb = Notebook("Proyecto 07 · Ranker multi-objetivo de CineMatch", colab_path=path, gpu=True)
    header(nb, "07", "Proyecto: ranker multi-objetivo para la home de CineMatch",
           "🟠 Avanzado → 🔴 Experto", "5–6 h", "L4 / A100 (T4 vale con FAST_DEV_RUN)", "~6–12",
           "Lección 07 (y 06)", tipo="Proyecto")
    nb.md(r"""
## 🏢 Contexto de negocio
CineMatch lanza **CineMatch Clips**: una fila de trailers y clips cortos en la home. Producto tiene tres objetivos:
- 🖱️ **clic** (abrir el clip) — engagement inmediato,
- ⏱️ **long view** (verlo entero o casi) — señal de interés real, la que mejor predice que luego se vea la película,
- ❤️ **like** — satisfacción explícita, escasa pero valiosa.

Hasta ahora había un modelo de CTR (módulo 06). Tu misión: un **ranker multi-tarea** y una **fórmula de fusión** que maximice una métrica de negocio sin hundir ningún objetivo, más un **baseline LambdaMART**. Como CineMatch aún no tiene logs de clips, usamos los logs públicos de **KuaiRand-Pure** (Kuaishou), que tienen exactamente estas señales.

## 📦 Dataset
KuaiRand-Pure (Gao et al., CIKM 2022; Zenodo `records/10439422`). Logs estándar del 8-abr al 8-may-2022 con `is_click`, `long_view`, `is_like`, features de usuario y de vídeo. Split temporal 80/10/10 por `time_ms`. Fallback sintético si no hay red.

## ✅ Entregables y rúbrica
| # | Entregable | Criterio |
|---|---|---|
| 1 | MMoE y PLE implementados (forward con puertas) | Tests de forma incluidos pasan |
| 2 | Tabla AUC por tarea: Single-task, Shared-Bottom, MMoE, PLE | MMoE o PLE ≥ Shared-Bottom en ≥ 2 de 3 tareas |
| 3 | Frente de Pareto clic–like (≥ 3 pesos) | Gráfico + comentario sobre el *seesaw* |
| 4 | LambdaMART (LightGBM) con etiqueta graduada de negocio | NDCG@10 de negocio reportado |
| 5 | Fusión de scores tuneada en **validación** y evaluada en **test** | NDCG@10 de negocio ≥ mejor tarea individual |
| 6 | Nota de decisión (≤ 10 líneas) para Producto | Pesos elegidos, trade-offs, plan de A/B |
""")
    nb.code(r'''
!pip install -q lightgbm
''')
    nb.code(SETUP_CODE)
    nb.code(r'''
import os, urllib.request
FAST_DEV_RUN = True
MAX_ROWS = 600_000 if FAST_DEV_RUN else None
EPOCHS_MTL = 1 if FAST_DEV_RUN else 3
''')
    nb.code(KUAI_LOADER)
    nb.code(r'''
logs, kusers, kvideos = load_kuairand(max_rows=MAX_ROWS)
kdf, KX, KY, kfield_dims, ksplit = prepare_kuairand(logs, kusers, kvideos)
Ktr, Kva, Kte = (ksplit == s for s in ["train", "val", "test"])
GAIN_W = np.array([1.0, 2.0, 4.0])          # ganancia de negocio: clic + 2·long_view + 4·like
print(KX.shape, dict(zip(TASKS, KY.mean(0).round(4))))
''')
    nb.md(r"""
## Paso 1 — Implementa MMoE y PLE
Te damos `mlp`, `CatEncoder`, `SharedBottom` y `MTLNet`. Completa `MMoE.forward` y `CGCLayer.forward`. Ambos deben devolver `(logits [B, T], gates)`.
""")
    nb.code(r'''
def mlp(dims, dropout=0.0, last_act=True):
    layers = []
    for i, (a, b) in enumerate(zip(dims[:-1], dims[1:])):
        layers.append(nn.Linear(a, b))
        if last_act or i < len(dims) - 2:
            layers += [nn.ReLU(), nn.Dropout(dropout)]
    return nn.Sequential(*layers)

class CatEncoder(nn.Module):
    def __init__(self, field_dims, k=16):
        super().__init__()
        self.emb = nn.Embedding(sum(field_dims), k); nn.init.normal_(self.emb.weight, std=0.01)
        self.d_out = len(field_dims) * k
    def forward(self, x):
        return self.emb(x).flatten(1)

class SharedBottom(nn.Module):
    def __init__(self, d_in, n_tasks, bottom=(256, 128), tower=(64,)):
        super().__init__()
        self.bottom = mlp([d_in, *bottom])
        self.towers = nn.ModuleList([mlp([bottom[-1], *tower, 1], last_act=False) for _ in range(n_tasks)])
    def forward(self, h):
        z = self.bottom(h)
        return torch.cat([t(z) for t in self.towers], 1), None

class MTLNet(nn.Module):
    def __init__(self, encoder, core):
        super().__init__(); self.encoder, self.core = encoder, core
    def forward(self, x):
        return self.core(self.encoder(x))

class MMoE(nn.Module):
    def __init__(self, d_in, n_tasks, n_experts=6, expert=(256, 128), tower=(64,)):
        super().__init__()
        self.experts = nn.ModuleList([mlp([d_in, *expert]) for _ in range(n_experts)])
        self.gates = nn.ModuleList([nn.Linear(d_in, n_experts) for _ in range(n_tasks)])
        self.towers = nn.ModuleList([mlp([expert[-1], *tower, 1], last_act=False) for _ in range(n_tasks)])
    def forward(self, h):
        # TODO: apila expertos [B, E, d]; para cada tarea, softmax de su puerta, mezcla y torre
        raise NotImplementedError

class CGCLayer(nn.Module):
    def __init__(self, d_in, d_out, n_tasks, n_spec=2, n_shared=2, last=False):
        super().__init__()
        self.T = n_tasks
        self.spec = nn.ModuleList([nn.ModuleList([mlp([d_in, d_out]) for _ in range(n_spec)]) for _ in range(n_tasks)])
        self.shared = nn.ModuleList([mlp([d_in, d_out]) for _ in range(n_shared)])
        self.gates = nn.ModuleList([nn.Linear(d_in, n_spec + n_shared) for _ in range(n_tasks)])
        self.shared_gate = None if last else nn.Linear(d_in, n_tasks * n_spec + n_shared)
    def forward(self, xs, x_sh):
        # TODO: devuelve (salidas por tarea, nueva entrada compartida o None, puertas)
        raise NotImplementedError

class PLE(nn.Module):
    def __init__(self, d_in, n_tasks, levels=2, d_hidden=128, n_spec=2, n_shared=2, tower=(64,)):
        super().__init__()
        self.layers = nn.ModuleList([CGCLayer(d_in if l == 0 else d_hidden, d_hidden, n_tasks, n_spec, n_shared,
                                              last=(l == levels - 1)) for l in range(levels)])
        self.towers = nn.ModuleList([mlp([d_hidden, *tower, 1], last_act=False) for _ in range(n_tasks)])
        self.T = n_tasks
    def forward(self, h):
        xs, x_sh = [h] * self.T, h
        for layer in self.layers:
            xs, x_sh, gates = layer(xs, x_sh)
        return torch.cat([tw(x) for tw, x in zip(self.towers, xs)], 1), torch.stack(gates, 0)

def build_mtl(kind, field_dims, n_tasks, k=16):
    enc = CatEncoder(field_dims, k)
    core = {"Shared-Bottom": lambda: SharedBottom(enc.d_out, n_tasks), "MMoE": lambda: MMoE(enc.d_out, n_tasks),
            "PLE": lambda: PLE(enc.d_out, n_tasks)}[kind]()
    return MTLNet(enc, core)

def _test_shapes():
    x = torch.randn(4, 32)
    for core in [MMoE(32, 3), PLE(32, 3)]:
        out, g = core(x)
        assert out.shape == (4, 3) and g.shape[0] == 3 and torch.allclose(g.sum(-1), torch.ones_like(g.sum(-1)), atol=1e-5)
    print("✅ formas y puertas OK")
try:
    _test_shapes()
except NotImplementedError:
    print("⏳ Implementa MMoE.forward y CGCLayer.forward")
''')
    nb.md(r"""
## Paso 2 — Entrenamiento y evaluación por tarea
Usa `train_mtl` (dado) y calcula AUC por tarea en test para Single-task, Shared-Bottom, MMoE y PLE.
""")
    nb.code(MTL_TRAIN)
    nb.code(r'''
# TODO: entrena los 4 enfoques y construye la tabla de AUC por tarea
''')
    nb.md(r"""
## Paso 3 — Frente de Pareto (clic vs like)
Barre `task_w=[1, 1, w]` con ≥ 3 valores de `w` para al menos dos arquitecturas. Grafica AUC clic vs AUC like.
""")
    nb.code(r'''
# TODO
''')
    nb.md(r"""
## Paso 4 — Baseline LambdaMART
Cada **usuario en un día** es una consulta; la etiqueta graduada es la ganancia de negocio entera `clic + 2·lv + 4·like` (0–7). Features para LightGBM: las categóricas de `KUAI_CATS` (como `category`) + **features de conteo point-in-time** que tú construyas (p. ej. CTR previo del vídeo y del autor con suavizado; ver proyecto 06).
""")
    nb.code(r'''
import lightgbm as lgb
def business_ndcg(df_scores: pd.DataFrame, score_col: str, k=10) -> float:
    """df_scores con columnas qid, gain y score_col. NDCG@k de negocio promedio por consulta."""
    # TODO
    raise NotImplementedError
''')
    nb.md(r"""
## Paso 5 — Fusión tuneada en validación
Busca en una rejilla los pesos de $s=\log\hat p_\text{clic} + w_\text{lv}\log\hat p_\text{lv} + w_\text{like}\log\hat p_\text{like}$ **en validación**, y reporta el resultado en **test** (¡no tunees en test!). Compara con ordenar solo por cada tarea y con LambdaMART.
""")
    nb.code(r'''
# TODO
''')

    nb.md(r"""
---
# ⛔ SPOILER — Solución de referencia
Intenta resolverlo primero.
""")
    nb.code(r'''
class MMoE(nn.Module):
    def __init__(self, d_in, n_tasks, n_experts=6, expert=(256, 128), tower=(64,)):
        super().__init__()
        self.experts = nn.ModuleList([mlp([d_in, *expert]) for _ in range(n_experts)])
        self.gates = nn.ModuleList([nn.Linear(d_in, n_experts) for _ in range(n_tasks)])
        self.towers = nn.ModuleList([mlp([expert[-1], *tower, 1], last_act=False) for _ in range(n_tasks)])
    def forward(self, h):
        E = torch.stack([e(h) for e in self.experts], 1)
        outs, gates = [], []
        for gate, tower in zip(self.gates, self.towers):
            g = torch.softmax(gate(h), -1)
            outs.append(tower((g.unsqueeze(-1) * E).sum(1))); gates.append(g)
        return torch.cat(outs, 1), torch.stack(gates, 0)

class CGCLayer(nn.Module):
    def __init__(self, d_in, d_out, n_tasks, n_spec=2, n_shared=2, last=False):
        super().__init__()
        self.T = n_tasks
        self.spec = nn.ModuleList([nn.ModuleList([mlp([d_in, d_out]) for _ in range(n_spec)]) for _ in range(n_tasks)])
        self.shared = nn.ModuleList([mlp([d_in, d_out]) for _ in range(n_shared)])
        self.gates = nn.ModuleList([nn.Linear(d_in, n_spec + n_shared) for _ in range(n_tasks)])
        self.shared_gate = None if last else nn.Linear(d_in, n_tasks * n_spec + n_shared)
    def forward(self, xs, x_sh):
        sh = [e(x_sh) for e in self.shared]
        outs, gates, all_spec = [], [], []
        for t in range(self.T):
            sp = [e(xs[t]) for e in self.spec[t]]; all_spec += sp
            g = torch.softmax(self.gates[t](xs[t]), -1)
            outs.append((g.unsqueeze(-1) * torch.stack(sp + sh, 1)).sum(1)); gates.append(g)
        new_sh = None
        if self.shared_gate is not None:
            g = torch.softmax(self.shared_gate(x_sh), -1)
            new_sh = (g.unsqueeze(-1) * torch.stack(all_spec + sh, 1)).sum(1)
        return outs, new_sh, gates

_test_shapes()
''')
    nb.code(r'''
res, models, preds = {}, {}, {}
for kind in ["Shared-Bottom", "MMoE", "PLE"]:
    torch.manual_seed(seed)
    models[kind] = train_mtl(build_mtl(kind, kfield_dims, 3), KX[Ktr], KY[Ktr], KX[Kva], KY[Kva], epochs=EPOCHS_MTL)
    preds[kind] = {s: predict_mtl(models[kind], KX[m]) for s, m in [("val", Kva), ("test", Kte)]}
    res[kind] = {t: roc_auc_score(KY[Kte][:, i], preds[kind]["test"][:, i]) for i, t in enumerate(TASKS)}
single_val, single_test = np.zeros((Kva.sum(), 3)), np.zeros((Kte.sum(), 3))
for i, t in enumerate(TASKS):
    torch.manual_seed(seed)
    m = train_mtl(build_mtl("Shared-Bottom", kfield_dims, 1), KX[Ktr], KY[Ktr][:, [i]], KX[Kva], KY[Kva][:, [i]], epochs=EPOCHS_MTL)
    single_val[:, i] = predict_mtl(m, KX[Kva])[:, 0]; single_test[:, i] = predict_mtl(m, KX[Kte])[:, 0]
res["Single-task"] = {t: roc_auc_score(KY[Kte][:, i], single_test[:, i]) for i, t in enumerate(TASKS)}
preds["Single-task"] = {"val": single_val, "test": single_test}
auc_table = pd.DataFrame(res).T
display(auc_table.round(4))
wins = {k: int((auc_table.loc[k] >= auc_table.loc["Shared-Bottom"]).sum()) for k in ["MMoE", "PLE"]}
print("Tareas en las que igualan o superan a Shared-Bottom:", wins)
''')
    nb.code(r'''
pareto = []
for kind in ["Shared-Bottom", "PLE"]:
    for w in ([0.3, 1.0, 5.0] if FAST_DEV_RUN else [0.1, 0.3, 1.0, 3.0, 10.0]):
        torch.manual_seed(seed)
        m = train_mtl(build_mtl(kind, kfield_dims, 3), KX[Ktr], KY[Ktr], KX[Kva], KY[Kva], task_w=[1, 1, w], epochs=EPOCHS_MTL)
        P = predict_mtl(m, KX[Kte])
        pareto.append((kind, w, roc_auc_score(KY[Kte][:, 0], P[:, 0]), roc_auc_score(KY[Kte][:, 2], P[:, 2])))
pf = pd.DataFrame(pareto, columns=["modelo", "w_like", "auc_click", "auc_like"])
plt.figure(figsize=(6, 4.2))
for kind, g in pf.groupby("modelo"):
    plt.plot(g.auc_click, g.auc_like, "o-", label=kind)
    for _, r in g.iterrows(): plt.annotate(f"w={r.w_like:g}", (r.auc_click, r.auc_like), fontsize=7)
plt.xlabel("AUC clic"); plt.ylabel("AUC like"); plt.legend(); plt.title("Frente de Pareto"); plt.show()
''')
    nb.code(r'''
# LambdaMART: consulta = usuario × día; features categóricas + conteos point-in-time
kdf["day"] = (kdf.time_ms // 86_400_000).astype(int)
kdf["gain"] = KY @ GAIN_W
kdf["qid"] = kdf.groupby(["user_id", "day"]).ngroup()
for key in ["video_id", "author_id"]:                           # CTR previo suavizado (solo pasado)
    g = kdf.groupby(key)
    cnt = g.cumcount(); clk = g.is_click.cumsum() - kdf.is_click
    prior = kdf.is_click[Ktr].mean()
    kdf[f"{key}_cnt_pit"] = np.log1p(cnt); kdf[f"{key}_ctr_pit"] = (clk + 20 * prior) / (cnt + 20)
LGB_FEATS = KUAI_CATS + [c for c in kdf.columns if c.endswith("_pit")]
Xl = kdf[LGB_FEATS].copy()
for c in KUAI_CATS:
    Xl[c] = pd.Categorical(pd.Index(Xl.loc[Ktr, c].astype(str).unique()).get_indexer(Xl[c].astype(str)) + 1)

def grouped(mask):
    idx = np.where(mask)[0]; idx = idx[np.argsort(kdf.qid.values[idx], kind="mergesort")]
    return idx, kdf.qid.values[idx]

itr, qtr = grouped(Ktr); iva, qva = grouped(Kva)
ranker = lgb.LGBMRanker(objective="lambdarank", n_estimators=600, learning_rate=0.05, num_leaves=63,
                        min_child_samples=100, label_gain=[2 ** i - 1 for i in range(8)],
                        random_state=seed, verbose=-1)
ranker.fit(Xl.iloc[itr], kdf.gain.values[itr].astype(int), group=np.unique(qtr, return_counts=True)[1],
           eval_set=[(Xl.iloc[iva], kdf.gain.values[iva].astype(int))], eval_group=[np.unique(qva, return_counts=True)[1]],
           eval_at=[10], callbacks=[lgb.early_stopping(50, verbose=False)])

def business_ndcg(df_scores: pd.DataFrame, score_col: str, k=10) -> float:
    vals = []
    for _, g in df_scores.groupby("qid"):
        if len(g) < 3 or g.gain.sum() == 0: continue
        top = g.nlargest(k, score_col).gain.values
        ideal = np.sort(g.gain.values)[::-1][:k]
        disc = 1 / np.log2(np.arange(2, k + 2))
        vals.append(((2 ** top - 1) * disc[:len(top)]).sum() / ((2 ** ideal - 1) * disc[:len(ideal)]).sum())
    return float(np.mean(vals))

ev = {s: kdf.loc[m, ["qid", "gain"]].copy() for s, m in [("val", Kva), ("test", Kte)]}
ev["test"]["lambdamart"] = ranker.predict(Xl[Kte]); ev["val"]["lambdamart"] = ranker.predict(Xl[Kva])
print("LambdaMART NDCG@10 de negocio (test):", round(business_ndcg(ev["test"], "lambdamart"), 4))
''')
    nb.code(r'''
# Fusión: rejilla en VALIDACIÓN, evaluación final en TEST
grid = [0.0, 0.5, 1.0, 2.0, 4.0]
P_val, P_test = preds["PLE"]["val"], preds["PLE"]["test"]
fuse = lambda P, a, b: np.log(P[:, 0] + 1e-9) + a * np.log(P[:, 1] + 1e-9) + b * np.log(P[:, 2] + 1e-9)
best = max(((a, b) for a in grid for b in grid),
           key=lambda ab: business_ndcg(ev["val"].assign(s=fuse(P_val, *ab)), "s"))
print("Pesos elegidos en validación (w_lv, w_like):", best)
final = {}
for i, t in enumerate(TASKS):
    final[f"solo {t} (PLE)"] = business_ndcg(ev["test"].assign(s=P_test[:, i]), "s")
final["LambdaMART"] = business_ndcg(ev["test"], "lambdamart")
final[f"Fusión PLE w={best}"] = business_ndcg(ev["test"].assign(s=fuse(P_test, *best)), "s")
final[f"Fusión Single-task w={best}"] = business_ndcg(ev["test"].assign(s=fuse(preds['Single-task']['test'], *best)), "s")
s = pd.Series(final).sort_values()
s.plot.barh(figsize=(7, 3.5), color="#4c72b0", title="NDCG@10 de negocio en test"); plt.xlim(s.min() * 0.97, s.max() * 1.01); plt.show()
print(s.round(4))
''')
    nb.md(r"""
### Nota de decisión (ejemplo)
> Recomendamos servir **PLE** (una sola red, 3 cabezas) con fusión $\log p_\text{clic} + w_\text{lv}\log p_\text{lv} + w_\text{like}\log p_\text{like}$ con los pesos elegidos en validación. Frente a ordenar por clic, mejora la NDCG de negocio offline sin empeorar de forma relevante el AUC de clic (ver frente de Pareto). LambdaMART es un baseline sólido y barato; lo mantenemos como *fallback*. Plan: A/B con 3 brazos (solo-clic, fusión elegida, fusión con w_like×2), métrica principal = minutos vistos de películas tras ver un clip, *guardrails*: CTR de la fila y tasa de `is_hate`. Monitorizar calibración por cabeza.

## 🚀 Retos extra
1. Añade `is_follow`, `is_comment`, `is_forward` y la regresión de `play_time_ms` (pérdida MSE sobre log1p) como tareas. ¿Aparece *seesaw*?
2. Implementa **uncertainty weighting** y **PCGrad** y compáralos en el frente de Pareto.
3. Usa el log **aleatorio** de KuaiRand (`log_random_4_22_to_5_08_pure.csv`) como test **insesgado**: ¿cambia el ranking de modelos?
4. Añade un *shallow tower* de posición/`tab` estilo YouTube 2019 que se apague en serving.
5. Destila LambdaMART en la red (usa sus scores como *soft labels* de una tarea extra).

## 🤔 Reflexión (producción / MLOps)
- ¿Cómo versionarías la **fórmula de fusión** (pesos) separada del modelo, para cambiarla sin reentrenar? (Config en un registry, módulo 17).
- ¿Qué monitorizarías por cabeza (calibración, distribución de scores) y qué alerta dispararía un rollback?
- Si una tarea (like) cambia de definición en la app, ¿cómo evitas que el reentreno rompa la fusión?
""")
    nb.save(path)


if __name__ == "__main__":
    build_lesson()
    build_project()
