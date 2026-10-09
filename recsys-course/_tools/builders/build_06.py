"""Builder del módulo 06 · Ranking como predicción de CTR.

Ejecutar desde la raíz del repo:  python recsys-course/_tools/builders/build_06.py
"""
import os
import sys

sys.path.insert(0, "recsys-course/_tools")
sys.path.insert(0, "recsys-course/_tools/builders")
from nbbuild import Notebook  # noqa: E402
from b3_common import header, ML_UTILS_MD, ML_UTILS_CODE, DRAW_CODE, SETUP_CODE  # noqa: E402

MOD = "06_ctr_ranking"
os.makedirs(f"recsys-course/{MOD}", exist_ok=True)

# Código compartido entre lección y proyecto ---------------------------------
CRITEO_LOADER = r'''
# === Carga de Criteo (streaming de una muestra) con fallback sintético =======
import os, gzip, requests

INT_COLS = [f"I{i}" for i in range(1, 14)]
CAT_COLS = [f"C{i}" for i in range(1, 27)]
CRITEO_COLS = ["label"] + INT_COLS + CAT_COLS
# Criteo 1TB Click Logs publicado por Criteo AI Lab en Hugging Face (un fichero por día).
CRITEO_URL = "https://huggingface.co/datasets/criteo/CriteoClickLogs/resolve/main/day_0.gz"

def stream_criteo(n_rows: int, url: str = CRITEO_URL) -> pd.DataFrame:
    """Lee SOLO las primeras n_rows del .gz en streaming (no descarga el día entero)."""
    headers = {}
    if os.environ.get("HF_TOKEN"):  # por si el dataset pide aceptar la licencia
        headers["Authorization"] = f"Bearer {os.environ['HF_TOKEN']}"
    with requests.get(url, stream=True, headers=headers, timeout=60) as r:
        r.raise_for_status()
        gz = gzip.GzipFile(fileobj=r.raw)
        df = pd.read_csv(gz, sep="\t", header=None, names=CRITEO_COLS, nrows=n_rows,
                         dtype={c: "string" for c in CAT_COLS})
    return df

def synthetic_criteo(n: int = 400_000, seed: int = 42) -> pd.DataFrame:
    """Criteo 'de laboratorio': mismo esquema (13 enteros + 26 categóricas) y una
    verdad conocida: efectos de primer orden + interacciones de pares de campos."""
    rng = np.random.default_rng(seed)
    card = rng.integers(4, 3000, 26)
    card[[0, 1, 4, 5, 7, 9, 12, 16, 18, 21]] = rng.integers(6, 60, 10)    # campos "útiles" de cardinalidad baja
    card[[2, 3, 11, 15, 20, 23]] = [60000, 40000, 25000, 50000, 30000, 15000]
    idx = np.stack([(rng.zipf(1.15, n) - 1) % card[f] for f in range(26)], 1)
    logit = np.full(n, -1.6)
    for f in [0, 4, 7, 12, 18]:                              # efectos de primer orden
        w = rng.normal(0, 0.6, card[f]); logit += w[idx[:, f]]
    for a, b in [(0, 1), (2, 5), (7, 9), (3, 12), (16, 21)]:  # interacciones de 2º orden
        va, vb = rng.normal(0, 0.7, (card[a], 4)), rng.normal(0, 0.7, (card[b], 4))
        logit += (va[idx[:, a]] * vb[idx[:, b]]).sum(1)
    ints = rng.lognormal(1.0, 1.5, (n, 13)).round()
    logit += 0.25 * np.log1p(ints[:, 0]) - 0.2 * np.log1p(ints[:, 4])
    y = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    df = pd.DataFrame(ints, columns=INT_COLS)
    df[INT_COLS] = df[INT_COLS].mask(rng.random((n, 13)) < 0.15)   # ~15 % de nulos
    for f, c in enumerate(CAT_COLS):
        s = pd.Series(np.char.add(f"{f:02d}x", idx[:, f].astype(str)), dtype="string")
        df[c] = s.mask(rng.random(n) < 0.05)
    df.insert(0, "label", y)
    return df

def load_ctr_data(n_rows: int) -> tuple:
    try:
        df = stream_criteo(n_rows)
        source = "criteo"
        print(f"✅ Criteo real: {len(df):,} filas")
    except Exception as e:
        print(f"⚠️ No se pudo leer Criteo ({type(e).__name__}: {str(e)[:80]}). Uso Criteo SINTÉTICO.")
        df, source = synthetic_criteo(n_rows), "synthetic"
    return df, source
'''

PREPROC = r'''
# === Preprocesado estilo "ganadores de Kaggle" ================================
def bucketize_int(v: pd.Series) -> pd.Series:
    """Truco del equipo ganador de Criteo-Kaggle (Juan et al.): v>2 → floor(log(v)^2)."""
    x = v.astype("float64")
    b = np.where(x > 2, np.floor(np.log(x.clip(lower=1e-9)) ** 2), x)
    return pd.Series(b, index=v.index).astype("float64").fillna(-999).astype(int).astype(str)

def build_vocab_and_encode(df: pd.DataFrame, train_idx: np.ndarray, min_count: int = 10):
    """Vocabulario por campo SOLO con train (¡nada de mirar el futuro!).
    Valores raros/no vistos → índice 0 (OOV) de su campo. Devuelve índices GLOBALES."""
    fields = INT_COLS + CAT_COLS
    X = np.zeros((len(df), len(fields)), dtype=np.int32)
    field_dims, offset = [], 0
    for j, c in enumerate(fields):
        col = bucketize_int(df[c]) if c in INT_COLS else df[c].fillna("<NA>").astype(str)
        vc = col.iloc[train_idx].value_counts()
        keep = vc[vc >= min_count].index
        mapping = pd.Series(np.arange(1, len(keep) + 1), index=keep)
        local = col.map(mapping).fillna(0).astype(np.int64).values
        X[:, j] = local + offset
        field_dims.append(len(keep) + 1)
        offset += len(keep) + 1
    return X, field_dims
'''

TRAIN_UTILS = r'''
# === Bucle de entrenamiento y métricas comunes para TODOS los modelos CTR =====
from sklearn.metrics import roc_auc_score, log_loss

def normalized_entropy(y, p, base_ctr=None):
    """NE de He et al. (Facebook, 2014): logloss / entropía del CTR medio de train."""
    p = np.clip(p, 1e-7, 1 - 1e-7)
    b = np.mean(y) if base_ctr is None else base_ctr
    h = -(b * np.log(b) + (1 - b) * np.log(1 - b))
    return log_loss(y, p) / h

def ctr_metrics(y, p, base_ctr=None) -> dict:
    p = np.clip(p, 1e-7, 1 - 1e-7)
    return {"logloss": log_loss(y, p), "auc": roc_auc_score(y, p),
            "NE": normalized_entropy(y, p, base_ctr), "calib (Σp/Σy)": p.sum() / max(y.sum(), 1)}

@torch.no_grad()
def predict_proba(model, X: np.ndarray, bs: int = 65536) -> np.ndarray:
    model.eval()
    out = []
    for i in range(0, len(X), bs):
        xb = torch.as_tensor(X[i:i + bs], device=device).long()
        out.append(torch.sigmoid(model(xb)).float().cpu().numpy())
    return np.concatenate(out)

def train_ctr(model, Xtr, ytr, Xva, yva, epochs=2, bs=4096, lr=1e-3, wd=0.0, verbose=True):
    """Entrenamiento estándar CTR: Adam + BCE, evaluación por época, guarda el mejor."""
    model = model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=wd)
    Xt = torch.as_tensor(Xtr, device=device)
    yt = torch.as_tensor(ytr, dtype=torch.float32, device=device)
    hist, best, best_state = [], np.inf, None
    n_steps = math.ceil(len(Xt) / bs)
    for ep in range(epochs):
        model.train()
        perm = torch.randperm(len(Xt), device=device)
        run = 0.0
        for s in range(n_steps):
            idx = perm[s * bs:(s + 1) * bs]
            loss = F.binary_cross_entropy_with_logits(model(Xt[idx].long()), yt[idx])
            opt.zero_grad(set_to_none=True); loss.backward(); opt.step()
            run += loss.item()
            if s % max(1, n_steps // 4) == 0:
                hist.append({"step": ep * n_steps + s, "train_loss": run / (s + 1)})
        pva = predict_proba(model, Xva)
        m = ctr_metrics(yva, pva)
        hist[-1].update({"val_logloss": m["logloss"], "val_auc": m["auc"]})
        if verbose:
            print(f"  época {ep+1}: train {run/n_steps:.4f} | val logloss {m['logloss']:.4f} auc {m['auc']:.4f}")
        if m["logloss"] < best:
            best = m["logloss"]
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    return model, pd.DataFrame(hist)
'''

MODELS = r'''
# === Modelos CTR desde cero en PyTorch =======================================
class FeaturesLinear(nn.Module):
    """Parte 'wide' / regresión logística sobre one-hot: un peso por valor de feature."""
    def __init__(self, n_feats):
        super().__init__()
        self.w = nn.Embedding(n_feats, 1); nn.init.zeros_(self.w.weight)
        self.b = nn.Parameter(torch.zeros(1))
    def forward(self, x):                       # x: [B, F] índices globales
        return self.w(x).sum(dim=(1, 2)) + self.b

class LR(nn.Module):
    def __init__(self, field_dims, **_):
        super().__init__(); self.lin = FeaturesLinear(sum(field_dims))
    def forward(self, x):
        return self.lin(x)

def fm_interaction(e):                          # e: [B, F, k]
    """Truco O(F·k) de Rendle: ½[(Σ v)^2 − Σ v^2]."""
    square_of_sum = e.sum(1).pow(2)
    sum_of_square = e.pow(2).sum(1)
    return 0.5 * (square_of_sum - sum_of_square).sum(1)

class FM(nn.Module):
    def __init__(self, field_dims, k=16, **_):
        super().__init__()
        self.lin = FeaturesLinear(sum(field_dims))
        self.emb = nn.Embedding(sum(field_dims), k); nn.init.normal_(self.emb.weight, std=0.01)
    def forward(self, x):
        return self.lin(x) + fm_interaction(self.emb(x))

class FFM(nn.Module):
    """Field-aware FM: cada valor tiene un embedding DISTINTO por cada campo con el que interactúa."""
    def __init__(self, field_dims, k=4, **_):
        super().__init__()
        self.F, self.k = len(field_dims), k
        self.lin = FeaturesLinear(sum(field_dims))
        self.emb = nn.Embedding(sum(field_dims), self.F * k); nn.init.normal_(self.emb.weight, std=0.01)
        iu = torch.triu_indices(self.F, self.F, offset=1)
        self.register_buffer("i_idx", iu[0]); self.register_buffer("j_idx", iu[1])
    def forward(self, x):
        e = self.emb(x).view(x.size(0), self.F, self.F, self.k)   # [B, campo i, campo destino j, k]
        vi_fj = e[:, self.i_idx, self.j_idx]                        # v_{i, f_j}
        vj_fi = e[:, self.j_idx, self.i_idx]                        # v_{j, f_i}
        return self.lin(x) + (vi_fj * vj_fi).sum((1, 2))

def mlp(dims, dropout=0.0):
    layers = []
    for a, b in zip(dims[:-1], dims[1:]):
        layers += [nn.Linear(a, b), nn.ReLU(), nn.Dropout(dropout)]
    return nn.Sequential(*layers)

class WideDeep(nn.Module):
    def __init__(self, field_dims, k=16, hidden=(400, 400, 400), dropout=0.1, **_):
        super().__init__()
        F_ = len(field_dims)
        self.lin = FeaturesLinear(sum(field_dims))
        self.emb = nn.Embedding(sum(field_dims), k); nn.init.normal_(self.emb.weight, std=0.01)
        self.deep = mlp([F_ * k, *hidden], dropout); self.head = nn.Linear(hidden[-1], 1)
    def forward(self, x):
        h = self.deep(self.emb(x).flatten(1))
        return self.lin(x) + self.head(h).squeeze(1)

class DeepFM(nn.Module):
    """Wide&Deep donde la parte 'wide' es un FM que COMPARTE embeddings con la parte deep."""
    def __init__(self, field_dims, k=16, hidden=(400, 400, 400), dropout=0.1, **_):
        super().__init__()
        F_ = len(field_dims)
        self.lin = FeaturesLinear(sum(field_dims))
        self.emb = nn.Embedding(sum(field_dims), k); nn.init.normal_(self.emb.weight, std=0.01)
        self.deep = mlp([F_ * k, *hidden], dropout); self.head = nn.Linear(hidden[-1], 1)
    def forward(self, x):
        e = self.emb(x)
        return self.lin(x) + fm_interaction(e) + self.head(self.deep(e.flatten(1))).squeeze(1)

class CrossLayerV2(nn.Module):
    """x_{l+1} = x_0 ⊙ (W x_l + b) + x_l, con W = U Vᵀ opcionalmente de bajo rango."""
    def __init__(self, d, rank=None):
        super().__init__()
        self.rank = rank
        if rank is None:
            self.W = nn.Linear(d, d)
        else:
            self.V = nn.Linear(d, rank, bias=False); self.U = nn.Linear(rank, d)
    def full_weight(self):
        return self.W.weight if self.rank is None else self.U.weight @ self.V.weight
    def forward(self, x0, xl):
        z = self.W(xl) if self.rank is None else self.U(self.V(xl))
        return x0 * z + xl

class DCNv2(nn.Module):
    """DCN-v2 (Wang et al., 2021). structure='stacked' (cross → deep) o 'parallel'."""
    def __init__(self, field_dims, k=16, n_cross=3, rank=None, hidden=(400, 400),
                 dropout=0.1, structure="stacked", **_):
        super().__init__()
        d = len(field_dims) * k
        self.emb = nn.Embedding(sum(field_dims), k); nn.init.normal_(self.emb.weight, std=0.01)
        self.cross = nn.ModuleList([CrossLayerV2(d, rank) for _ in range(n_cross)])
        self.structure = structure
        self.deep = mlp([d, *hidden], dropout)
        out_dim = hidden[-1] if structure == "stacked" else d + hidden[-1]
        self.head = nn.Linear(out_dim, 1)
    def forward(self, x):
        x0 = self.emb(x).flatten(1)
        xl = x0
        for layer in self.cross:
            xl = layer(x0, xl)
        if self.structure == "stacked":
            h = self.deep(xl)
        else:
            h = torch.cat([xl, self.deep(x0)], 1)
        return self.head(h).squeeze(1)
'''


def build_lesson():
    nb = Notebook("Módulo 06 · Ranking como predicción de CTR", colab_path=f"recsys-course/{MOD}/{MOD}.ipynb", gpu=True)
    header(nb, "06", "Ranking como predicción de CTR: de LR+hashing a DCN-v2 y DIN",
           "🟡 Intermedio → 🟠 Avanzado", "5–6 h", "L4 (T4 suficiente; A100 para `SCALE='full'`)",
           "~4 (FAST_DEV_RUN) · ~12–20 (full con 10M filas)",
           "01 (datos y split temporal), 02 (métricas), 05 (factorización matricial)")

    nb.md(r"""
## 🎯 Objetivos de aprendizaje
Al terminar este módulo serás capaz de:
1. **Formular** la etapa de *ranking* de un recomendador como un problema de predicción de probabilidad de clic/engagement (pCTR) y **explicar** por qué la probabilidad (y no solo el orden) importa.
2. **Construir** features para ranking a partir de logs: categóricas de alta cardinalidad, *bucketización* de numéricas, vocabularios con OOV y *hashing trick*.
3. **Implementar desde cero en PyTorch** LR, FM, FFM, Wide & Deep, DeepFM, DCN-v2 y DIN, y **derivar** el truco $O(kn)$ de las Factorization Machines.
4. **Comparar** estos modelos con LightGBM y GBDT+LR (Facebook 2014) usando *logloss*, AUC y **Normalized Entropy**.
5. **Diagnosticar y corregir** la calibración (reliability diagrams, corrección por *negative downsampling*, isotónica).
6. **Medir** el efecto de las colisiones de *hashing* y del tamaño de las tablas de embeddings.
7. **Reconocer** las librerías de industria (TorchRec, NVIDIA Merlin, FuxiCTR, DeepCTR-Torch) y cuándo usar cada una.
""")

    nb.md(r"""
## 💡 1. Intuición: ¿qué hace la etapa de *ranking*?

En el módulo 00 viste la arquitectura multi-etapa. El **retrieval** (módulos 04, 05 y 08) reduce millones de ítems a unos cientos o miles de candidatos *baratos de calcular*. El **ranking** recibe esos candidatos y les pone una nota fina usando **todas las features que quieras**: del usuario, del ítem, del contexto (hora, dispositivo, posición) y, sobre todo, **cruces** entre ellas.

Ese "poner nota" casi siempre se formula como un **clasificador binario probabilístico**:

$$\hat p = P(\text{clic} = 1 \mid \text{usuario}, \text{ítem}, \text{contexto})$$

Ya sabes entrenar clasificadores binarios. Lo que cambia en recsys/ads:

| Lo que conoces (tabular "normal") | Ranking CTR a escala |
|---|---|
| Decenas de columnas numéricas | 20–1000 campos, casi todos **categóricos** con 10⁶–10⁹ valores (IDs) |
| Interacciones las encuentra el árbol | Las interacciones (*user × ítem*, *anuncio × web*) **son** la señal |
| Métrica: accuracy/AUC | **Logloss / NE** (necesitamos probabilidades calibradas), AUC, GAUC |
| Datos estáticos | Flujo continuo, distribución que cambia cada hora → reentrenos frecuentes |
| Un modelo | Un modelo que sirve **10⁵–10⁷ predicciones/segundo** con < 10–50 ms |

¿Por qué una **probabilidad** y no solo un orden? Porque el score se **combina** con otras cosas: en anuncios `puja × pCTR` (subasta), en Netflix/YouTube `w₁·p(clic) + w₂·E[tiempo] + …` (módulo 07). Si $\hat p$ está mal calibrada, la mezcla se rompe aunque el AUC sea perfecto.
""")
    nb.code(r'''
!pip install -q lightgbm requests scikit-learn
''')
    nb.code(SETUP_CODE)
    nb.code(DRAW_CODE)
    nb.code(r'''
# Diagrama 1 — El embudo multi-etapa y dónde vive este módulo
fig, ax = plt.subplots(figsize=(11, 3.6))
stages = [("Catálogo\n10⁶–10⁹ ítems", "grey"), ("Retrieval\n(mód. 04-05-08)\n~10³ candidatos", "in"),
          ("RANKING\n(este módulo)\n~10² puntuados", "inter"), ("Re-ranking\n(mód. 13)\n10–50 mostrados", "out")]
boxes = {}
for i, (txt, col) in enumerate(stages):
    h = 3.2 - i * 0.55
    boxes[i] = (0.3 + i * 2.5, 2.0 - h / 2 + 1.5, 2.0, h, txt, col)
draw_blocks(ax, boxes, [(0, 1), (1, 2), (2, 3)], "Embudo de recomendación: el ranking ve pocos ítems pero con MUCHAS features", (0, 10.3), (0, 5))
ax.text(5.8, 0.3, "modelo pesado: features de usuario×ítem×contexto, cruces, secuencias",
        ha="center", fontsize=9, style="italic", color="#a0522d")
plt.show()
''')

    nb.md(r"""
### Un ejemplo de 5 impresiones en papel
Cada fila de un log de ranking es una **impresión**: "le mostramos el ítem *i* al usuario *u* en el contexto *c*; ¿hizo clic?".

| impresión | usuario | país | dispositivo | película | género | hora | clic |
|---|---|---|---|---|---|---|---|
| 1 | u_17 | ES | móvil | *Alien* | Sci-Fi | 23h | 1 |
| 2 | u_17 | ES | móvil | *Notting Hill* | Romance | 23h | 0 |
| 3 | u_08 | MX | TV | *Alien* | Sci-Fi | 21h | 0 |
| 4 | u_08 | MX | TV | *Coco* | Animación | 18h | 1 |
| 5 | u_42 | ES | TV | *Coco* | Animación | 18h | 1 |

Un modelo lineal sobre one-hot aprende "Sci-Fi sube un poco", "TV baja un poco". Pero la señal real está en **cruces**: *(TV, 18h, Animación)* = "familia viendo con niños". La historia de los modelos de este módulo es la historia de **cómo aprender cruces de features de forma automática y que generalice a combinaciones nunca vistas**:

```
LR + cruces a mano (2010-14) → FM/FFM (cruces de 2º orden factorizados) → GBDT+LR (cruces por árboles)
   → Wide&Deep / DeepFM (MLP + FM) → DCN / DCN-v2 (cruces explícitos de orden alto)
   → DIN / DIEN / SIM (cruces con la SECUENCIA del usuario, atención) → HSTU (mód. 11)
```
""")
    nb.code(r'''
# Diagrama 2 — La fila de entrenamiento como vector one-hot ultra-disperso
fields = ["usuario\n(10⁸)", "país\n(200)", "dispositivo\n(5)", "película\n(10⁵)", "género\n(20)", "hora\n(24)"]
widths = np.array([40, 6, 3, 25, 5, 6])
fig, ax = plt.subplots(figsize=(11, 2.4))
x = 0
rng_ = np.random.default_rng(0)
for f, w in zip(fields, widths):
    ax.add_patch(plt.Rectangle((x, 0), w, 1, fc="#f4f4f4", ec="#777"))
    hot = x + rng_.integers(0, w)
    ax.add_patch(plt.Rectangle((hot, 0), 1, 1, fc="#d62728"))
    ax.text(x + w / 2, 1.25, f, ha="center", va="bottom", fontsize=8)
    x += w + 1
ax.set_xlim(-1, x); ax.set_ylim(-0.3, 2.4); ax.axis("off")
ax.set_title("x = concatenación de one-hots: millones de dimensiones, 1 solo '1' por campo (rojo)", fontsize=10)
plt.show()
''')

    nb.md(r"""
## 📐 2. Teoría formal

### 2.1 Pérdida y métricas
Con etiquetas $y_i \in \{0,1\}$ y predicciones $\hat p_i$, minimizamos la **log-loss** (entropía cruzada binaria):

$$\mathcal{L} = -\frac{1}{N}\sum_{i=1}^N \big[y_i \log \hat p_i + (1-y_i)\log(1-\hat p_i)\big]$$

**Normalized Entropy** (He et al., Facebook 2014): divide la log-loss por la entropía de un predictor que siempre dice el CTR medio $p$ de train:

$$NE = \frac{\mathcal{L}}{-\big(p\log p + (1-p)\log(1-p)\big)}$$

$NE<1$ significa "mejor que predecir la media". Es la métrica estándar en Meta porque es **comparable entre campañas con CTR base distinto** (un logloss de 0,10 es buenísimo si el CTR es 50 % y malo si es 3 %).

**AUC** mide solo el orden (probabilidad de que un positivo aleatorio puntúe más que un negativo). **GAUC** = AUC calculado por usuario y promediado (ponderado por impresiones): mide lo que importa en recomendación, ordenar *los ítems de cada usuario*.

### 2.2 Regresión logística con *hashing trick*
$$\hat p = \sigma\Big(w_0 + \sum_{j} w_{h(j)}\, x_j\Big), \qquad h(j) = \text{hash}(\text{campo}_j \,\|\, \text{valor}_j) \bmod B$$

En vez de mantener un diccionario de 10⁹ valores, se proyecta cada `campo=valor` a uno de $B$ cubos (Weinberger et al., 2009). Coste: **colisiones** (dos valores comparten peso). Ventaja: memoria fija, sin vocabulario, maneja valores nuevos al vuelo. Las interacciones se añaden a mano: `hash("pais=ES|genero=SciFi")`.

### 2.3 Factorization Machines (Rendle, 2010)
Un modelo de 2º orden con un peso libre por par $w_{ij}$ tendría $O(n^2)$ parámetros y **no podría estimar pares nunca vistos**. FM factoriza $w_{ij} = \langle \mathbf v_i, \mathbf v_j\rangle$ con $\mathbf v_i \in \mathbb R^k$:

$$\hat y(\mathbf x) = w_0 + \sum_{i=1}^n w_i x_i + \sum_{i=1}^n\sum_{j=i+1}^n \langle \mathbf v_i, \mathbf v_j\rangle x_i x_j$$

- $n$: número total de features (one-hot), $k$: dimensión del embedding, $\mathbf v_i$: embedding de la feature $i$.
- Generaliza a pares no vistos: si *(TV, Animación)* nunca co-ocurrió, $\mathbf v_{TV}$ y $\mathbf v_{Anim}$ se aprendieron por separado con otros pares.
- **Conexión con el módulo 05**: si las únicas features son `user_id` y `item_id`, FM **es** factorización matricial con sesgos.

**Derivación del truco $O(kn)$** (clave para entender todo lo que viene):

$$\sum_{i<j}\langle \mathbf v_i,\mathbf v_j\rangle x_i x_j
= \frac12\Big[\sum_{i}\sum_{j}\langle \mathbf v_i,\mathbf v_j\rangle x_i x_j - \sum_i \langle \mathbf v_i,\mathbf v_i\rangle x_i^2\Big]
= \frac12\sum_{f=1}^{k}\Big[\Big(\sum_i v_{i,f}x_i\Big)^2 - \sum_i v_{i,f}^2 x_i^2\Big]$$

Paso 1: la suma sobre $i<j$ es la mitad de la suma sobre todos los pares menos la diagonal. Paso 2: $\sum_i\sum_j \langle \mathbf v_i,\mathbf v_j\rangle x_ix_j = \|\sum_i \mathbf v_i x_i\|^2$. Coste: $O(k\cdot \text{nnz}(\mathbf x))$, y con one-hot nnz = número de campos $F$.

### 2.4 Field-aware FM (Juan et al., 2016)
Cada feature tiene un embedding **por cada campo** con el que interactúa: $\langle \mathbf v_{i,f_j}, \mathbf v_{j,f_i}\rangle$. Más expresivo (ganó Criteo y Avazu en Kaggle) pero con $F$ veces más parámetros y sin el truco $O(kn)$: coste $O(kF^2)$.

### 2.5 Wide & Deep (Google, 2016) y DeepFM (Huawei, 2017)
$$\hat p = \sigma\big(\underbrace{\mathbf w^\top[\mathbf x, \phi(\mathbf x)]}_{\text{wide: memoriza}} + \underbrace{\mathbf w_d^\top \text{MLP}([\mathbf e_1,\dots,\mathbf e_F])}_{\text{deep: generaliza}}\big)$$
Wide & Deep usa cruces a mano $\phi(\mathbf x)$ en la parte lineal. **DeepFM** sustituye la parte wide por un FM que **comparte los embeddings** con el MLP → sin ingeniería manual.

### 2.6 DCN-v2 (Wang et al., Google 2021)
Un MLP aprende cruces multiplicativos de forma muy ineficiente (Beutel et al., 2018 lo mostraron para *latent cross*). DCN añade **capas de cruce explícito**. Con $\mathbf x_0 = [\mathbf e_1;\dots;\mathbf e_F]\in\mathbb R^d$:

$$\mathbf x_{l+1} = \mathbf x_0 \odot (W_l\,\mathbf x_l + \mathbf b_l) + \mathbf x_l$$

- $\odot$: producto elemento a elemento; $W_l\in\mathbb R^{d\times d}$; el término $+\mathbf x_l$ es residual.
- Tras $L$ capas el modelo contiene **todos los cruces polinómicos hasta grado $L+1$** de las features.
- El bloque $(i,j)$ de $W$ (de tamaño $k\times k$) mide cuánto interactúan los campos $i$ y $j$ → **interpretabilidad gratis**.
- Versión de bajo rango: $W = U V^\top$, $U,V\in \mathbb R^{d\times r}$ (en producción en Google, con mezcla de expertos de bajo rango).

### 2.7 DIN (Alibaba, 2018): cruces con la historia del usuario
Representar al usuario como la **media** de los ítems que vio pierde información: tu interés relevante *depende del candidato*. DIN pondera la historia $\{\mathbf e_1..\mathbf e_H\}$ con una atención condicionada al candidato $\mathbf e_a$:

$$\mathbf v_U(a) = \sum_{h=1}^H g(\mathbf e_h, \mathbf e_a)\,\mathbf e_h,\qquad g = \text{MLP}([\mathbf e_h, \mathbf e_a, \mathbf e_h-\mathbf e_a, \mathbf e_h\odot\mathbf e_a])$$

Sin softmax a propósito: la suma de pesos codifica la **intensidad** del interés. DIEN (2019) añade una GRU con atención (AUGRU) para modelar la evolución del interés; SIM (2020) y TWIN (Kuaishou, 2023) escalan a historias de 10⁴–10⁵ eventos con búsqueda en dos etapas.
""")

    nb.code(r'''
# Diagrama 3 — Por qué FM generaliza: W completa (n×n, casi vacía) vs W ≈ V Vᵀ (rango k)
rng_ = np.random.default_rng(1)
n, k = 30, 3
V = rng_.normal(size=(n, k))
W_full = V @ V.T
observed = rng_.random((n, n)) < 0.08                  # solo vemos el 8 % de los pares
fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
axes[0].imshow(np.where(observed, W_full, np.nan), cmap="coolwarm", vmin=-4, vmax=4)
axes[0].set_title("Pesos por par w_ij observables\n(el 92 % de pares nunca co-ocurre)")
axes[1].imshow(V, cmap="coolwarm", aspect=0.3); axes[1].set_title("V  (n × k): un embedding\npor feature")
axes[2].imshow(W_full, cmap="coolwarm", vmin=-4, vmax=4); axes[2].set_title("⟨v_i, v_j⟩ para TODOS los pares\n(incluidos los no vistos)")
for a in axes: a.set_xticks([]); a.set_yticks([])
plt.suptitle("FM = factorización de la matriz de interacciones entre features", weight="bold")
plt.tight_layout(); plt.show()
''')

    nb.md(r"""
## 🧪 3. Datos: muestra de Criteo (con fallback)

**Criteo** es el benchmark canónico de CTR: logs reales de anuncios *display*, cada fila = impresión, `label` = clic, **13 features enteras** (`I1..I13`, contadores anonimizados) y **26 categóricas** (`C1..C26`, *hashes* de 32 bits anonimizados). Hay dos versiones:

- **Criteo Display Advertising Challenge (Kaggle 2014)**: ~45 M filas, 7 días. Las versiones preprocesadas de BARS/FuxiCTR (`reczoo/Criteo_x1` en Hugging Face) son la referencia para comparar papers.
- **Criteo 1TB Click Logs**: 24 días, ~4 000 M filas, publicado por Criteo AI Lab en Hugging Face (`criteo/CriteoClickLogs`, un `.gz` por día, licencia CC BY-NC-SA 4.0).

Aquí **leemos en streaming solo las primeras N filas de `day_0.gz`** (no hace falta descargar GBs). Si Hugging Face pide aceptar la licencia, inicia sesión en la web del dataset, acepta, y define `HF_TOKEN` en los *secrets* de Colab. Si no hay red, usamos un **Criteo sintético** con el mismo esquema y con interacciones de pares **conocidas** (útil para ver si los modelos las encuentran).

> ⚠️ En Criteo 1TB los positivos y negativos se submuestrearon a tasas distintas (lo dice la ficha del dataset): el CTR de la muestra no es el CTR real del negocio. Perfecto para aprender a **corregir la calibración** (sección 8).
""")
    nb.code(r'''
FAST_DEV_RUN = True          # True: ~300k filas (CPU/T4). False: 5M+ filas (L4/A100)
N_ROWS = 300_000 if FAST_DEV_RUN else 5_000_000
EPOCHS = 2 if FAST_DEV_RUN else 3
BATCH = 4096
''')
    nb.code(CRITEO_LOADER)
    nb.code(r'''
df, SOURCE = load_ctr_data(N_ROWS)
print(df.shape, "| CTR medio:", round(df.label.mean(), 4))
df.head()
''')
    nb.code(r'''
# Split "temporal": usamos el ORDEN del fichero (los logs se escriben en orden de llegada)
n = len(df)
tr_idx = np.arange(0, int(0.8 * n)); va_idx = np.arange(int(0.8 * n), int(0.9 * n)); te_idx = np.arange(int(0.9 * n), n)
y = df.label.values.astype(np.float32)

# Gráfico — cardinalidad de cada campo y distribución de frecuencia (cola larga)
card = df[CAT_COLS].nunique()
fig, axes = plt.subplots(1, 2, figsize=(13, 3.8))
axes[0].bar(CAT_COLS, card.values, color="#4c72b0"); axes[0].set_yscale("log")
axes[0].set_title("Cardinalidad de los 26 campos categóricos (escala log)"); axes[0].tick_params(axis="x", rotation=90)
big = card.idxmax()
freq = df[big].value_counts().values
axes[1].loglog(np.arange(1, len(freq) + 1), freq, ".", ms=3)
axes[1].set_title(f"Frecuencia de valores de {big}: ley de potencias"); axes[1].set_xlabel("rango del valor"); axes[1].set_ylabel("nº de apariciones")
plt.tight_layout(); plt.show()
print(f"Valores de {big} que aparecen 1 sola vez: {(freq == 1).mean():.1%}  ← sus embeddings serían ruido")
''')
    nb.md(r"""
### Preprocesado: vocabulario con OOV + bucketización de enteros
- **Enteros**: el equipo ganador de Kaggle-Criteo (Juan et al., FFM) transformaba $v>2 \mapsto \lfloor \log(v)^2 \rfloor$ y trataba el resultado como categoría. Así **todo es categórico** y todos los modelos comparten la misma entrada `x ∈ ℕ^{39}`.
- **Categóricas**: vocabulario **calculado solo con train**; los valores con < `min_count` apariciones van a un índice OOV por campo. Esto es *regularización* (un embedding visto 2 veces es ruido) y evita **fuga de información** del futuro.
- Índices **globales**: el campo *j* ocupa el rango `[offset_j, offset_j + dim_j)` de una única tabla de embeddings.
""")
    nb.code(PREPROC)
    nb.code(r'''
t0 = time.time()
X, field_dims = build_vocab_and_encode(df, tr_idx, min_count=10)
print(f"X: {X.shape}, features totales (tamaño de la tabla): {sum(field_dims):,} | {time.time()-t0:.1f}s")
Xtr, Xva, Xte = X[tr_idx], X[va_idx], X[te_idx]
ytr, yva, yte = y[tr_idx], y[va_idx], y[te_idx]
BASE_CTR = ytr.mean()
oov_rate = (np.isin(Xte, np.cumsum([0] + field_dims[:-1]))).mean()
print(f"CTR train={BASE_CTR:.4f} | % de celdas OOV en test: {oov_rate:.1%}")
''')

    nb.md(r"""
## 🛠️ 4. Implementación desde cero (PyTorch)

Todos los modelos reciben `x: LongTensor [B, F]` con índices globales y devuelven **logits** `[B]`. Primero comprobamos numéricamente el truco $O(kn)$ de FM contra la suma ingenua sobre pares.
""")
    nb.code(TRAIN_UTILS)
    nb.code(MODELS)
    nb.code(r'''
# Verificación: truco O(kn) == suma explícita sobre pares i<j
e = torch.randn(5, 7, 4)
naive = sum((e[:, i] * e[:, j]).sum(1) for i in range(7) for j in range(i + 1, 7))
print("máx. diferencia:", (naive - fm_interaction(e)).abs().max().item())
for name, cls in [("LR", LR), ("FM", FM), ("FFM", FFM), ("Wide&Deep", WideDeep), ("DeepFM", DeepFM), ("DCN-v2", DCNv2)]:
    m = cls(field_dims)
    print(f"{name:10s} parámetros: {sum(p.numel() for p in m.parameters()):>12,}")
''')
    nb.code(r'''
# Diagrama 4 — Arquitecturas: DeepFM y DCN-v2 (stacked)
fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
b = {"x": (1, 0.3, 8, 1, "campos categóricos  x₁ … x_F (one-hot)", "in"),
     "e": (1, 2.0, 8, 1, "Embeddings compartidos  e₁ … e_F  (k dims)", "emb"),
     "lin": (0.2, 4.0, 2.4, 1.2, "Lineal\nΣ wᵢxᵢ", "inter"),
     "fm": (3.0, 4.0, 2.6, 1.2, "FM\n½[(Σe)² − Σe²]", "inter"),
     "mlp": (6.0, 3.6, 3.4, 2.4, "MLP\n400-400-400\nReLU + dropout", "mlp"),
     "sum": (3.6, 7.0, 2.6, 1.0, "Σ  →  σ(·) = p̂", "out")}
draw_blocks(axes[0], b, [("x", "e"), ("x", "lin"), ("e", "fm"), ("e", "mlp"), ("lin", "sum"), ("fm", "sum"), ("mlp", "sum")],
            "DeepFM: FM (memoriza pares) + MLP (orden alto), MISMOS embeddings")
b2 = {"e": (1, 0.3, 8, 1, "x₀ = [e₁; …; e_F]   (d = F·k)", "emb"),
      "c1": (2.5, 2.0, 5, 0.9, "Cross 1: x₀ ⊙ (W₁x₀ + b₁) + x₀", "inter"),
      "c2": (2.5, 3.3, 5, 0.9, "Cross 2: x₀ ⊙ (W₂x₁ + b₂) + x₁", "inter"),
      "c3": (2.5, 4.6, 5, 0.9, "Cross 3: x₀ ⊙ (W₃x₂ + b₃) + x₂", "inter"),
      "mlp": (2.5, 6.0, 5, 1.0, "Deep: MLP 400-400", "mlp"),
      "out": (3.5, 7.6, 3, 0.9, "logit → σ → p̂", "out")}
draw_blocks(axes[1], b2, [("e", "c1"), ("c1", "c2"), ("c2", "c3"), ("c3", "mlp"), ("mlp", "out")],
            "DCN-v2 (stacked): cruces explícitos de grado ≤ L+1")
axes[1].annotate("x₀ se re-inyecta\nen cada capa", xy=(2.5, 3.7), xytext=(0.0, 2.6), fontsize=8,
                 arrowprops=dict(arrowstyle="->", color="#a0522d"), color="#a0522d")
plt.tight_layout(); plt.show()
''')

    nb.md(r"""
### 🧪 Experimento: entrenar la familia completa
Mismo presupuesto para todos (épocas, batch, lr). En CTR es habitual que el mejor punto llegue tras **1–2 épocas**: muchos modelos sobreajustan a partir de la segunda (*one-epoch phenomenon*, Zhang et al., 2022), por eso evaluamos y guardamos el mejor por época.
""")
    nb.code(r'''
CONFIGS = {
    "LR": (LR, dict(), 1e-3),
    "FM": (FM, dict(k=16), 1e-3),
    "FFM": (FFM, dict(k=4), 1e-3),
    "Wide&Deep": (WideDeep, dict(k=16), 1e-3),
    "DeepFM": (DeepFM, dict(k=16), 1e-3),
    "DCN-v2": (DCNv2, dict(k=16, n_cross=3), 1e-3),
}
results, histories, preds, models = {}, {}, {}, {}
for name, (cls, kw, lr) in CONFIGS.items():
    print(f"▶ {name}")
    torch.manual_seed(seed)
    t0 = time.time()
    model, hist = train_ctr(cls(field_dims, **kw), Xtr, ytr, Xva, yva, epochs=EPOCHS, bs=BATCH, lr=lr)
    p = predict_proba(model, Xte)
    results[name] = {**ctr_metrics(yte, p, BASE_CTR), "seg": time.time() - t0}
    histories[name], preds[name], models[name] = hist, p, model
res_df = pd.DataFrame(results).T.sort_values("logloss")
res_df.style.format("{:.4f}")
''')

    nb.md(r"""
## 🏭 5. Librerías de industria: LightGBM y GBDT+LR (Facebook 2014)

Antes de celebrar el deep learning, **el baseline obligatorio**: un GBDT. En tabular con features densas bien construidas sigue siendo durísimo de batir (Grinsztajn et al., 2022), y en recsys los GBDT siguen en producción en muchas etapas (p. ej. *learning to rank* en búsqueda, módulo 07).

LightGBM maneja categóricas nativamente; con alta cardinalidad hay que regularizar (`min_data_per_group`, `cat_smooth`, `max_cat_threshold`) o convertirlas a **count encoding** (cuántas veces aparece el valor *en train*).
""")
    nb.code(r'''
import lightgbm as lgb

def lgb_frame(idx_rows):
    out = pd.DataFrame(index=np.arange(len(idx_rows)))
    for c in INT_COLS:
        out[c] = df[c].iloc[idx_rows].astype("float64").values
    for j, c in enumerate(CAT_COLS):                      # índice local del vocab (OOV=0) como categoría
        off = sum(field_dims[:13 + j])
        out[c] = (X[idx_rows, 13 + j] - off).astype(np.int32)
        out[c + "_cnt"] = cnt_maps[j][out[c].values]      # count encoding calculado SOLO en train
    return out

cnt_maps = []
for j in range(26):
    off = sum(field_dims[:13 + j])
    cnt_maps.append(np.bincount(X[tr_idx, 13 + j] - off, minlength=field_dims[13 + j]).astype(np.float32))
Ltr, Lva, Lte = lgb_frame(tr_idx), lgb_frame(va_idx), lgb_frame(te_idx)
params = dict(objective="binary", learning_rate=0.05, num_leaves=127, min_data_in_leaf=200,
              feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0,
              cat_smooth=50, min_data_per_group=200, max_cat_threshold=64, verbose=-1, seed=seed)
evals = {}
t0 = time.time()
gbm = lgb.train(params, lgb.Dataset(Ltr, ytr, categorical_feature=CAT_COLS),
                num_boost_round=300 if FAST_DEV_RUN else 1500,
                valid_sets=[lgb.Dataset(Lva, yva, categorical_feature=CAT_COLS)], valid_names=["val"],
                callbacks=[lgb.early_stopping(50, verbose=False), lgb.record_evaluation(evals)])
p = gbm.predict(Lte, num_iteration=gbm.best_iteration)
results["LightGBM"] = {**ctr_metrics(yte, p, BASE_CTR), "seg": time.time() - t0}; preds["LightGBM"] = p
print(f"LightGBM: {gbm.best_iteration} árboles |", {k: round(v, 4) for k, v in results['LightGBM'].items()})
''')
    nb.md(r"""
**GBDT + LR** (He et al., 2014): cada árbol actúa como un *transformador de features*: la hoja en la que cae un ejemplo es una feature categórica que codifica un **cruce no lineal** aprendido. Se concatenan los one-hot de las hojas y se entrena una LR encima. Facebook reportó que la combinación mejora la NE >3 % frente a cualquiera de los dos por separado, y lo usaban porque la LR se podía **reentrenar casi en tiempo real** mientras los árboles se reentrenaban con menos frecuencia.
""")
    nb.code(r'''
import scipy.sparse as sp
from sklearn.linear_model import LogisticRegression

N_TREES_LR = min(100, gbm.best_iteration)
def leaves_onehot(frame):
    leaves = gbm.predict(frame, num_iteration=N_TREES_LR, pred_leaf=True)        # [N, T]
    n_leaves = params["num_leaves"]
    cols = (leaves + np.arange(leaves.shape[1]) * n_leaves).ravel()
    rows = np.repeat(np.arange(len(frame)), leaves.shape[1])
    return sp.csr_matrix((np.ones_like(cols, dtype=np.float32), (rows, cols)),
                         shape=(len(frame), n_leaves * leaves.shape[1]))
sub = np.random.default_rng(seed).choice(len(Ltr), min(len(Ltr), 400_000), replace=False)
t0 = time.time()
lr_leaf = LogisticRegression(C=0.05, max_iter=300).fit(leaves_onehot(Ltr.iloc[sub]), ytr[sub])
p = lr_leaf.predict_proba(leaves_onehot(Lte))[:, 1]
results["GBDT+LR"] = {**ctr_metrics(yte, p, BASE_CTR), "seg": time.time() - t0}; preds["GBDT+LR"] = p
res_df = pd.DataFrame(results).T.sort_values("logloss")
res_df.style.format("{:.4f}").background_gradient(subset=["logloss", "NE"], cmap="RdYlGn_r")
''')

    nb.md(r"""
### 🧪 Gráficos de resultados: curvas de entrenamiento, ROC y comparación
""")
    nb.code(r'''
from sklearn.metrics import roc_curve
fig, axes = plt.subplots(1, 3, figsize=(16, 4.3))
for name, h in histories.items():
    axes[0].plot(h["step"], h["train_loss"], label=name)
    v = h.dropna(subset=["val_logloss"]) if "val_logloss" in h else h.iloc[0:0]
    axes[0].scatter(v["step"], v["val_logloss"], marker="x")
axes[0].set_title("Logloss train (línea) y val (×) por paso"); axes[0].set_xlabel("paso"); axes[0].legend(fontsize=7)
for name, p in preds.items():
    fpr, tpr, _ = roc_curve(yte, p)
    axes[1].plot(fpr, tpr, label=f"{name} ({results[name]['auc']:.3f})", lw=1.2)
axes[1].plot([0, 1], [0, 1], "k--", lw=0.8); axes[1].set_title("Curvas ROC (test)")
axes[1].set_xlabel("FPR"); axes[1].set_ylabel("TPR"); axes[1].legend(fontsize=7)
r = pd.DataFrame(results).T.sort_values("logloss")
axes[2].barh(r.index, r["logloss"], color="#dd8452"); axes[2].set_xlim(r["logloss"].min() * 0.98, r["logloss"].max() * 1.005)
axes[2].set_title("Logloss en test (menor es mejor)")
for i, v in enumerate(r["logloss"]):
    axes[2].text(v, i, f" {v:.4f}", va="center", fontsize=8)
plt.tight_layout(); plt.show()
''')
    nb.code(r'''
# Curva de LightGBM: logloss de validación vs nº de árboles
plt.figure(figsize=(6, 3.2))
plt.plot(evals["val"]["binary_logloss"]); plt.axvline(gbm.best_iteration, ls="--", c="k", lw=0.8)
plt.title("LightGBM: logloss de validación por árbol (early stopping)"); plt.xlabel("árboles"); plt.ylabel("logloss")
plt.show()
best = r.index[0]; worst = r.index[-1]
print(f"Mejor: {best}. Mejora relativa de logloss vs LR: {(1 - r.loc[best,'logloss']/r.loc['LR','logloss']):.2%}")
''')
    nb.md(r"""
> 🧠 **¿Cuánto es "mucho"?** En el paper de DCN (Wang et al., 2017) los autores escriben que una mejora de **0,001 en logloss** se considera *prácticamente significativa* en Criteo. A la escala de Google/Meta, un 0,1 % de NE se traduce en un % medible de ingresos o engagement. Por eso estas comparaciones necesitan **varias semillas** y un test grande: diferencias de 0,0005 entre dos runs pueden ser solo ruido de inicialización.
""")

    nb.md(r"""
## 🔍 6. Visualizar las interacciones aprendidas

Dos formas de abrir la caja:
- **FM**: la fuerza media de interacción del par de campos $(i,j)$ es $\mathbb E\,|\langle \mathbf e_i, \mathbf e_j\rangle|$ sobre los ejemplos.
- **DCN-v2**: la norma de Frobenius del bloque $(i,j)$ de $W_1$ (figura 5 del paper de DCN-v2).

Si los datos son sintéticos, sabemos la verdad: hay interacciones plantadas entre los campos categóricos (C1,C2), (C3,C6), (C8,C10), (C4,C13) y (C17,C22).
""")
    nb.code(r'''
@torch.no_grad()
def fm_pair_strength(model, Xs):
    e = model.emb(torch.as_tensor(Xs, device=device).long())            # [B, F, k]
    return torch.einsum("bik,bjk->bij", e, e).abs().mean(0).cpu().numpy()

@torch.no_grad()
def dcn_block_norms(model, k=16):
    W = model.cross[0].full_weight().detach().cpu().numpy()
    Fn = W.shape[0] // k
    return np.array([[np.linalg.norm(W[i*k:(i+1)*k, j*k:(j+1)*k]) for j in range(Fn)] for i in range(Fn)])

names = INT_COLS + CAT_COLS
S_fm = fm_pair_strength(models["FM"], Xva[:20000]); np.fill_diagonal(S_fm, 0)
S_dcn = dcn_block_norms(models["DCN-v2"]); np.fill_diagonal(S_dcn, 0)
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
for ax, S, t in [(axes[0], S_fm, "FM: E|⟨eᵢ,eⱼ⟩| por par de campos"), (axes[1], S_dcn, "DCN-v2: ‖W₁[i,j]‖_F por bloque")]:
    im = ax.imshow(S, cmap="magma"); ax.set_title(t)
    ax.set_xticks(range(39)); ax.set_xticklabels(names, rotation=90, fontsize=6)
    ax.set_yticks(range(39)); ax.set_yticklabels(names, fontsize=6); plt.colorbar(im, ax=ax, fraction=0.046)
plt.tight_layout(); plt.show()
top = np.dstack(np.unravel_index(np.argsort(-np.triu(S_fm, 1), axis=None)[:6], S_fm.shape))[0]
print("Pares más fuertes según FM:", [(names[i], names[j]) for i, j in top])
''')

    nb.md(r"""
## #️⃣ 7. Hashing trick y colisiones de embeddings

En producción no siempre hay vocabulario: IDs nuevos aparecen cada segundo. Con *hashing* cada `campo=valor` va a `hash(...) mod B`. ¿Cuánto daño hacen las colisiones? Medimos, para varios tamaños de tabla $B$, (a) la fracción de valores de train que comparten cubo con otro valor y (b) la logloss de un FM entrenado con esos índices.

Con $m$ valores distintos y $B$ cubos, la fracción esperada de valores que colisionan es $\approx 1 - e^{-m/B}$ (problema del cumpleaños).
""")
    nb.code(r'''
def hash_encode(df_, B: int) -> np.ndarray:
    """Índice = hash(campo || valor) mod B, estable (pandas usa SipHash con clave fija)."""
    cols = []
    for c in INT_COLS + CAT_COLS:
        v = bucketize_int(df_[c]) if c in INT_COLS else df_[c].fillna("<NA>").astype(str)
        cols.append((pd.util.hash_pandas_object(c + "=" + v, index=False).values % np.uint64(B)).astype(np.int64))
    return np.stack(cols, 1).astype(np.int32)

raw_vals = sum(df[c].iloc[tr_idx].nunique() for c in CAT_COLS)
hash_rows = []
for logB in ([12, 14, 16, 18, 20] if FAST_DEV_RUN else [14, 16, 18, 20, 22, 24]):
    B = 2 ** logB
    H = hash_encode(df, B)
    uniq_vals = sum(df[c].iloc[tr_idx].nunique() for c in CAT_COLS)
    used = len(np.unique(H[tr_idx, 13:]))
    torch.manual_seed(seed)
    m, _ = train_ctr(FM([B], k=16), H[tr_idx], ytr, H[va_idx], yva, epochs=1, bs=BATCH, verbose=False)
    ll = ctr_metrics(yte, predict_proba(m, H[te_idx]))["logloss"]
    hash_rows.append({"B": B, "colisión (1-usados/distintos)": 1 - used / uniq_vals, "logloss": ll})
    print(f"B=2^{logB}: colisión ≈ {1-used/uniq_vals:.1%} | logloss {ll:.4f}")
hr = pd.DataFrame(hash_rows)
fig, ax1 = plt.subplots(figsize=(7, 3.6))
ax1.semilogx(hr.B, hr.logloss, "o-", base=2, color="#c44e52"); ax1.set_xlabel("cubos B (log₂)"); ax1.set_ylabel("logloss test", color="#c44e52")
ax2 = ax1.twinx(); ax2.semilogx(hr.B, hr.iloc[:, 1], "s--", base=2, color="#4c72b0"); ax2.set_ylabel("fracción colisionada", color="#4c72b0")
plt.title("Hashing trick: más cubos → menos colisiones → menor logloss (hasta saturar)"); plt.show()
''')
    nb.md(r"""
**Lectura**: la logloss baja al crecer $B$ y luego **satura** (o incluso empeora un poco por sobreajuste de valores raros). Trucos reales para escapar al compromiso memoria/colisiones:
- **Tablas sin colisiones con hash dinámico** (Monolith de ByteDance, 2022: *cuckoo hashmap* + expiración de IDs inactivos + filtro por frecuencia).
- **Multi-hash / QR trick** (Shi et al., Meta 2020, *Compositional Embeddings Using Complementary Partitions*): combinar 2 tablas pequeñas con cociente y resto.
- **DHE** (Kang et al., Google 2021): sustituir la tabla por un MLP sobre múltiples hashes.
- **Dimensión variable por frecuencia** (más dims a IDs frecuentes) y **semantic IDs** (módulo 11).
""")

    nb.md(r"""
## 🎯 8. Calibración: que $\hat p$ signifique lo que dice

Un modelo está **calibrado** si, entre todos los ejemplos con $\hat p\approx 0{,}2$, el 20 % hace clic. AUC no lo mide (es invariante a transformaciones monótonas); la logloss sí lo penaliza. Herramientas:
- **Reliability diagram**: agrupar por cuantiles de $\hat p$ y pintar CTR observado vs predicho.
- **Ratio de calibración** $\sum \hat p / \sum y$ (Meta lo monitoriza en tiempo real; ≠1 dispara alertas).
- **ECE** (*expected calibration error*): media ponderada de $|\text{CTR}_\text{bin} - \hat p_\text{bin}|$.

### Negative downsampling y su corrección exacta
Para abaratar el entrenamiento se queda solo una fracción $w$ de negativos (Facebook usaba tasas muy bajas). El modelo entrenado predice $p$ en el espacio submuestreado; la probabilidad real es (He et al., 2014):

$$q = \frac{p}{p + (1-p)/w}$$

**Derivación** (Bayes): con submuestreo, los *odds* se inflan por $1/w$: $\frac{p}{1-p} = \frac{1}{w}\cdot\frac{q}{1-q}$. Despejando $q$ sale la fórmula. Equivalente en logits: $\text{logit}(q) = \text{logit}(p) + \log w$.
""")
    nb.code(r'''
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression

def ece(y_, p_, bins=15):
    q = np.quantile(p_, np.linspace(0, 1, bins + 1)); b = np.clip(np.digitize(p_, q[1:-1]), 0, bins - 1)
    return sum(abs(y_[b == i].mean() - p_[b == i].mean()) * (b == i).mean() for i in range(bins) if (b == i).any())

# Downsampling de negativos al 10 % y entrenamiento de DeepFM sobre los datos submuestreados
w = 0.10
rng_ = np.random.default_rng(seed)
keep = (ytr == 1) | (rng_.random(len(ytr)) < w)
torch.manual_seed(seed)
m_ds, _ = train_ctr(DeepFM(field_dims), Xtr[keep], ytr[keep], Xva, yva, epochs=1, bs=BATCH, verbose=False)
p_raw = predict_proba(m_ds, Xte)
p_cor = p_raw / (p_raw + (1 - p_raw) / w)                         # corrección de He et al. 2014
iso = IsotonicRegression(out_of_bounds="clip").fit(predict_proba(m_ds, Xva), yva)   # alternativa: isotónica en val
p_iso = iso.predict(p_raw)
cands = {"DeepFM (sin downsampling)": preds["DeepFM"], "LightGBM": preds["LightGBM"],
         f"DeepFM downsampled w={w} (crudo)": p_raw, "… + corrección q=p/(p+(1-p)/w)": p_cor, "… + isotónica": p_iso}
fig, ax = plt.subplots(1, 2, figsize=(13, 4.8))
for name, p in cands.items():
    fr, mp = calibration_curve(yte, p, n_bins=15, strategy="quantile")
    ax[0].plot(mp, fr, "o-", ms=3, label=f"{name} | ECE={ece(yte, p):.4f}")
    ax[1].hist(p, bins=60, histtype="step", density=True, label=name)
lim = max(yte.mean() * 4, 0.3)
ax[0].plot([0, 1], [0, 1], "k--", lw=0.8); ax[0].set_xlim(0, lim); ax[0].set_ylim(0, lim)
ax[0].set_xlabel("p̂ media del bin"); ax[0].set_ylabel("CTR observado"); ax[0].set_title("Reliability diagram (test)"); ax[0].legend(fontsize=7)
ax[1].set_title("Distribución de p̂"); ax[1].set_yscale("log"); ax[1].legend(fontsize=6)
plt.tight_layout(); plt.show()
print(pd.DataFrame({k: ctr_metrics(yte, v, BASE_CTR) for k, v in cands.items()}).T.round(4))
''')
    nb.md(r"""
Observa que el modelo submuestreado tiene **AUC casi idéntico** (el orden no cambia: la corrección es monótona) pero una logloss/NE desastrosa antes de corregir. Moraleja: **monitoriza logloss/NE y ratio de calibración, no solo AUC.**
""")

    nb.md(r"""
## 🧬 9. DIN: atención sobre la historia del usuario (en CineMatch)

Criteo está anonimizado y no tiene secuencias. Para DIN volvemos a **CineMatch / MovieLens-1M**:
- Cada valoración es un evento "el usuario vio la película" (positivo); por cada positivo muestreamos **una película aleatoria** como negativo (exposición simulada).
- Features: candidato (película + género principal) e **historia**: las últimas $H=20$ películas vistas *antes* del evento.
- Split **temporal global**: el test son los eventos más recientes.

Comparamos **Embedding&MLP con media de la historia** (estilo YouTube DNN) vs **DIN**.
""")
    nb.md(ML_UTILS_MD)
    nb.code(ML_UTILS_CODE)
    nb.code(r'''
ratings, movies, users = load_movielens("1m")
ratings = ratings.sort_values(["user_id", "timestamp"]).reset_index(drop=True)
item_ids = np.sort(ratings.item_id.unique()); item_map = {v: i + 1 for i, v in enumerate(item_ids)}   # 0 = padding
ratings["iid"] = ratings.item_id.map(item_map)
movies["iid"] = movies.item_id.map(item_map)
movies = movies.dropna(subset=["iid"]).astype({"iid": int})
movies["g0"] = movies.genres.str.split("|").str[0]
genre_map = {g: i + 1 for i, g in enumerate(sorted(movies.g0.unique()))}
item_genre = np.zeros(len(item_ids) + 1, dtype=np.int64); item_genre[movies.iid.values] = movies.g0.map(genre_map).values
title_of = dict(zip(movies.iid, movies.title))
H = 20

def build_din_samples(r: pd.DataFrame, n_neg=1, seed=42):
    rng_ = np.random.default_rng(seed)
    hist_l, tgt_l, lab_l, uid_l, ts_l = [], [], [], [], []
    for uid, g in r.groupby("user_id", sort=False):
        seq, ts = g.iid.values, g.timestamp.values
        for t in range(5, len(seq)):
            h = seq[max(0, t - H):t]; h = np.pad(h, (H - len(h), 0))
            for tgt, lab in [(seq[t], 1)] + [(rng_.integers(1, len(item_ids) + 1), 0) for _ in range(n_neg)]:
                hist_l.append(h); tgt_l.append(tgt); lab_l.append(lab); uid_l.append(uid); ts_l.append(ts[t])
    return (np.array(hist_l), np.array(tgt_l), np.array(lab_l, dtype=np.float32), np.array(uid_l), np.array(ts_l))

t0 = time.time()
Hh, Tt, Yy, Uu, TS = build_din_samples(ratings)
t_val, t_test = np.quantile(TS, [0.8, 0.9])
splits = {"train": TS < t_val, "val": (TS >= t_val) & (TS < t_test), "test": TS >= t_test}
print(f"{len(Yy):,} ejemplos en {time.time()-t0:.0f}s |", {k: int(v.sum()) for k, v in splits.items()})
''')
    nb.code(r'''
class SeqCTR(nn.Module):
    """Embedding&MLP con pooling de la historia: 'mean' (baseline) o 'din' (atención local)."""
    def __init__(self, n_items, n_genres, d_item=32, d_genre=8, pooling="din"):
        super().__init__()
        self.item = nn.Embedding(n_items + 1, d_item, padding_idx=0)
        self.genre = nn.Embedding(n_genres + 1, d_genre, padding_idx=0)
        self.register_buffer("item_genre", torch.as_tensor(item_genre))
        d = d_item + d_genre
        self.pooling = pooling
        self.att = nn.Sequential(nn.Linear(4 * d, 64), nn.PReLU(), nn.Linear(64, 16), nn.PReLU(), nn.Linear(16, 1))
        self.mlp = nn.Sequential(nn.Linear(3 * d, 200), nn.PReLU(), nn.Linear(200, 80), nn.PReLU(), nn.Linear(80, 1))
    def embed(self, ids):
        return torch.cat([self.item(ids), self.genre(self.item_genre[ids])], -1)
    def forward(self, hist, tgt, return_att=False):
        eh, et = self.embed(hist), self.embed(tgt)                      # [B,H,d], [B,d]
        mask = (hist > 0).float().unsqueeze(-1)
        if self.pooling == "mean":
            w = mask / mask.sum(1, keepdim=True).clamp(min=1)
        else:
            q = et.unsqueeze(1).expand_as(eh)
            w = self.att(torch.cat([eh, q, eh - q, eh * q], -1)) * mask   # SIN softmax (como en el paper)
        u = (w * eh).sum(1)
        logit = self.mlp(torch.cat([u, et, u * et], -1)).squeeze(-1)
        return (logit, w.squeeze(-1)) if return_att else logit

def gauc(y_, p_, groups):
    d = pd.DataFrame({"y": y_, "p": p_, "g": groups})
    tot, wsum = 0.0, 0
    for _, g in d.groupby("g"):
        if 0 < g.y.sum() < len(g):
            tot += roc_auc_score(g.y, g.p) * len(g); wsum += len(g)
    return tot / wsum

def run_seq(pooling, epochs=2 if FAST_DEV_RUN else 4, bs=1024):
    torch.manual_seed(seed)
    m = SeqCTR(len(item_ids), len(genre_map), pooling=pooling).to(device)
    opt = torch.optim.Adam(m.parameters(), lr=1e-3)
    tr = np.where(splits["train"])[0]
    if FAST_DEV_RUN: tr = np.random.default_rng(seed).choice(tr, min(len(tr), 600_000), replace=False)
    Ht, Tt_, Yt = (torch.as_tensor(a[tr], device=device) for a in (Hh, Tt, Yy))
    for ep in range(epochs):
        m.train(); perm = torch.randperm(len(tr), device=device)
        for s in range(0, len(tr), bs):
            i = perm[s:s + bs]
            loss = F.binary_cross_entropy_with_logits(m(Ht[i].long(), Tt_[i].long()), Yt[i])
            opt.zero_grad(); loss.backward(); opt.step()
    te = np.where(splits["test"])[0]
    m.eval()
    with torch.no_grad():
        p = np.concatenate([torch.sigmoid(m(torch.as_tensor(Hh[te[s:s+8192]], device=device).long(),
                                            torch.as_tensor(Tt[te[s:s+8192]], device=device).long())).cpu().numpy()
                            for s in range(0, len(te), 8192)])
    return m, {"auc": roc_auc_score(Yy[te], p), "gauc": gauc(Yy[te], p, Uu[te]), "logloss": log_loss(Yy[te], p)}

seq_res = {}
for pool in ["mean", "din"]:
    t0 = time.time(); mdl, seq_res[pool] = run_seq(pool); print(pool, {k: round(v, 4) for k, v in seq_res[pool].items()}, f"{time.time()-t0:.0f}s")
    if pool == "din": din_model = mdl
pd.DataFrame(seq_res).T
''')
    nb.code(r'''
# Diagrama 5 + gráfico — Arquitectura DIN y pesos de atención para DOS candidatos distintos
fig = plt.figure(figsize=(15, 5))
ax0 = fig.add_subplot(1, 3, 1)
b = {"h": (0.2, 0.3, 4.6, 1, "historia e₁ … e_H", "emb"), "a": (5.4, 0.3, 4.2, 1, "candidato e_a", "emb"),
     "att": (0.4, 2.3, 4.2, 1.5, "activation unit\nMLP([eₕ, eₐ, eₕ−eₐ, eₕ⊙eₐ])\n→ peso gₕ", "gate"),
     "pool": (0.4, 4.6, 4.2, 1, "v_U = Σ gₕ·eₕ", "inter"),
     "mlp": (2.5, 6.6, 5, 1.2, "MLP([v_U, eₐ, v_U⊙eₐ])", "mlp"), "out": (3.5, 8.6, 3, 0.9, "p̂(clic)", "out")}
draw_blocks(ax0, b, [("h", "att"), ("a", "att"), ("att", "pool"), ("pool", "mlp"), ("a", "mlp"), ("mlp", "out")], "DIN (Zhou et al., 2018)")
# Elegimos un usuario de test y dos candidatos de géneros distintos
i0 = np.where(splits["test"] & (Yy == 1))[0][0]
hist = Hh[i0]
cands = [Tt[i0]] + [c for c in np.random.default_rng(1).integers(1, len(item_ids) + 1, 200) if item_genre[c] != item_genre[Tt[i0]]][:1]
for j, c in enumerate(cands):
    with torch.no_grad():
        _, w = din_model(torch.as_tensor(hist[None], device=device).long(), torch.as_tensor([c], device=device).long(), return_att=True)
    w = w[0].cpu().numpy(); valid = hist > 0
    ax = fig.add_subplot(1, 3, 2 + j)
    labels = [title_of.get(h, str(h))[:28] for h in hist[valid]]
    ax.barh(range(valid.sum()), w[valid], color="#55a868"); ax.set_yticks(range(valid.sum())); ax.set_yticklabels(labels, fontsize=6)
    ax.set_title(f"Candidato: {title_of.get(c, c)[:30]}\n({movies.set_index('iid').g0.get(c, '?')})", fontsize=9); ax.set_xlabel("peso de atención g_h")
plt.tight_layout(); plt.show()
''')
    nb.md(r"""
Lo importante del gráfico: **la misma historia** recibe pesos distintos según el candidato (*local activation*). Con un usuario que ha visto 2 000 películas, la media diluye la señal; la atención la recupera. En producción (Alibaba, Kuaishou, Meta) esta idea escala a historias larguísimas con **búsqueda en dos etapas** (SIM, TWIN) o se sustituye por transformers generativos (HSTU, módulo 11).

## 🏭 10. Librerías de industria: TorchRec, NVIDIA Merlin, FuxiCTR, DeepCTR-Torch

| Librería | Qué aporta | Cuándo usarla |
|---|---|---|
| **TorchRec** (Meta) | `EmbeddingBagCollection`, `KeyedJaggedTensor` (features de longitud variable), **sharding** de tablas entre GPUs (table/row/column-wise), kernels FBGEMM, DLRM de referencia | Tablas de embeddings que no caben en una GPU; entrenamiento distribuido a escala Meta |
| **NVIDIA Merlin** (NVTabular, HugeCTR, Merlin Models, Transformers4Rec) | Preprocesado en GPU, embeddings en GPU/CPU jerárquicos, serving con Triton | Pipelines end-to-end en GPU NVIDIA (mód. 16) |
| **FuxiCTR / BARS** (Huawei Noah's Ark + academia) | +50 modelos CTR con configuración YAML y **benchmarks reproducibles** (Criteo_x1, Avazu_x1…) | Comparar tu modelo contra el estado del arte de forma justa |
| **DeepCTR-Torch** | API Keras-like de DeepFM, DCN, DIN, DIEN… | Prototipos rápidos (mantenimiento menos activo) |

Ejemplo mínimo de TorchRec (la instalación requiere versiones de `torch`/`fbgemm-gpu` compatibles; por eso va protegido):
""")
    nb.code(r'''
INSTALL_TORCHREC = False   # pon True en Colab GPU para probarlo (instala torchrec + fbgemm-gpu)
if INSTALL_TORCHREC:
    import subprocess; subprocess.run("pip install -q torchrec", shell=True)
try:
    import torchrec
    from torchrec.sparse.jagged_tensor import KeyedJaggedTensor
    ebc = torchrec.EmbeddingBagCollection(device="cpu", tables=[
        torchrec.EmbeddingBagConfig(name="t_pelicula", embedding_dim=16, num_embeddings=4000,
                                    feature_names=["historia_peliculas"], pooling=torchrec.PoolingType.MEAN),
        torchrec.EmbeddingBagConfig(name="t_pais", embedding_dim=16, num_embeddings=250,
                                    feature_names=["pais"], pooling=torchrec.PoolingType.SUM)])
    # Batch de 2 usuarios: historias de longitud 3 y 1 (¡jagged!) y un país cada uno
    kjt = KeyedJaggedTensor.from_lengths_sync(keys=["historia_peliculas", "pais"],
            values=torch.tensor([10, 25, 31, 7, 3, 44]), lengths=torch.tensor([3, 1, 1, 1]))
    out = ebc(kjt).to_dict()
    print({k: v.shape for k, v in out.items()})
except Exception as e:
    print("TorchRec no disponible aquí:", type(e).__name__, "→ el resto del notebook no lo necesita.")
''')
    nb.md(r"""
Configuración típica en **FuxiCTR** (no se ejecuta; ilustra el estilo declarativo, que en MLOps encaja con *config as code*):
```yaml
DCNv2_criteo:
  model: DCNv2
  dataset_id: criteo_x1
  model_structure: parallel   # crossnet_only | stacked | parallel | stacked_parallel
  num_cross_layers: 4
  low_rank: 32
  embedding_dim: 16
  stacked_dnn_hidden_units: [500, 500, 500]
  batch_size: 4096
  learning_rate: 1.0e-3
```

## 🏭 11. En producción
- **Meta / Facebook Ads (He et al., 2014)**: GBDT + LR, NE como métrica, *data freshness* (reentrenar a diario mejoraba NE de forma clara frente a semanal), *negative downsampling* + recalibración, y LR online. Hoy: **DLRM** (Naumov et al., 2019) y sucesores (DHEN 2022, Wukong 2024 con *scaling laws* para recsys), entrenados con TorchRec en miles de GPUs.
- **Google**: Wide & Deep en Google Play (2016, +3,9 % de adquisiciones de apps en A/B frente al wide-only); **DCN-v2** desplegado en muchos sistemas de ranking de Google (lo afirman Wang et al., 2021). El paper *On the Factory Floor* (Anil et al., 2022) cuenta la cara B: irreproducibilidad entre runs, coste de inferencia, calibración y *loss engineering* en Google Ads.
- **Alibaba**: DIN/DIEN/SIM en la publicidad de Taobao; ESMM (módulo 07) para CVR.
- **Netflix / YouTube**: el ranking de la home y del *watch next* son modelos profundos multi-tarea (módulo 07) que combinan probabilidades de distintas acciones; la calibración de cada cabeza es lo que permite mezclarlas.
- **Latencia**: el ranker puntúa 10²–10³ candidatos por petición en ~10–50 ms; el cuello de botella típico son los *lookups* de embeddings (memoria) y el *feature fetching* (feature store, módulo 16), no los FLOPs del MLP.

## 🧠 12. Secretos de la élite
1. **Un 0,1 % de logloss/NE es mucho dinero.** A escala, mejoras de 0,001 en logloss son "prácticamente significativas" (Wang et al., 2017). Exige varias semillas, intervalos de confianza y tests grandes antes de creerte una mejora de 0,05 %.
2. **Mira NE y ratio de calibración, no solo AUC.** AUC no ve la calibración; en subastas y en fusión multi-objetivo una pCTR inflada un 10 % cambia el orden final. Meta monitoriza $\sum\hat p/\sum y$ por segmento en tiempo real.
3. **GBDT sigue siendo un baseline brutal** en features densas/agregadas (contadores, ratios, recencias). Los deep ganan cuando dominan los **IDs de alta cardinalidad** y las secuencias. Muchos sistemas híbridos alimentan el ranker profundo con features que antes usaba el GBDT.
4. **Fuga de información en features de conteo** (*label leakage*): un "CTR histórico del anuncio" calculado con **todo** el dataset (incluido el futuro y la propia fila) da AUC espectaculares offline y fracasa online. Las features de conteo deben calcularse **point-in-time** (solo con eventos anteriores al timestamp de la impresión), como hace un feature store con *time-travel* (Feast, mód. 16). Lo practicarás en el proyecto.
5. **El "one-epoch phenomenon"**: los modelos CTR profundos con embeddings grandes suelen sobreajustar bruscamente al empezar la 2ª época (Zhang et al., 2022). En producción se entrena en *streaming* con **una sola pasada** por los datos.
6. **Colisiones de hashing y frecuencia de IDs**: un ID visto 3 veces tiene un embedding ruidoso que daña más de lo que ayuda. Umbral de frecuencia (`min_count`), OOV compartido, *expiración* de IDs (Monolith) y *mixed-dimension embeddings* son higiene básica.
7. **Position bias**: el ítem en la posición 1 recibe clics por estar arriba. Si entrenas con la posición como feature, en serving fíjala a un valor constante (o usa un *shallow tower*/PAL, módulo 07). Si no, el modelo aprende "lo que antes se puso arriba".
8. **Reproducibilidad**: dos entrenamientos idénticos con distinta semilla pueden diferir en predicciones individuales de forma notable (*prediction churn*, Anil et al., 2022) aunque la logloss media sea la misma; esto rompe experimentos A/B si no se controla (ensembles, warm-start, *smooth activations*).

## ⚠️ 13. Errores comunes
- Hacer **split aleatorio** en datos de logs: el modelo ve el futuro (popularidad, IDs nuevos) y la métrica offline es optimista. Usa split temporal.
- Construir el vocabulario o los contadores con train+test.
- Comparar modelos con distinto **presupuesto de tuning** (el baseline sin tunear siempre "pierde"). FuxiCTR/BARS mostró que muchas mejoras publicadas desaparecen con tuning justo (Zhu et al., 2021).
- Olvidar recalibrar tras *negative downsampling* o tras cambiar la distribución de entrenamiento.
- Reportar solo AUC global en recomendación: usa también **GAUC** (por usuario).
- Embeddings demasiado grandes sin regularización → explotan en la 2ª época.
- Usar *softmax* en la atención de DIN "porque sí": se pierde la intensidad del interés (los autores lo descartan a propósito).

## 📝 14. Autoevaluación
1. ¿Por qué en ranking se optimiza logloss y no solo AUC?
<details><summary>Respuesta</summary>Porque el score se combina con otras magnitudes (pujas, otras cabezas, reglas de negocio) y necesita ser una probabilidad calibrada. AUC solo mide el orden y es invariante a transformaciones monótonas.</details>

2. Deriva el coste del término de interacción de FM y explica por qué es $O(kF)$ con entradas one-hot.
<details><summary>Respuesta</summary>$\sum_{i<j}\langle v_i,v_j\rangle x_ix_j = \tfrac12\sum_f[(\sum_i v_{if}x_i)^2-\sum_i v_{if}^2x_i^2]$. Solo hay $F$ entradas no nulas, así que cada suma interna cuesta $O(F)$ y hay $k$ dimensiones.</details>

3. Tras entrenar con el 5 % de negativos, el modelo predice $p=0{,}5$. ¿Cuál es la probabilidad real?
<details><summary>Respuesta</summary>$q = 0{,}5/(0{,}5 + 0{,}5/0{,}05) = 0{,}5/10{,}5 \approx 0{,}048$.</details>

4. ¿Qué diferencia hay entre una capa de cruce de DCN-v2 y una capa densa de un MLP?
<details><summary>Respuesta</summary>La capa de cruce multiplica elemento a elemento por $x_0$, creando términos polinómicos explícitos (grado +1 por capa) con conexión residual; un MLP con ReLU solo puede aproximar productos de forma ineficiente.</details>

5. ¿Por qué DIN no normaliza los pesos de atención con softmax?
<details><summary>Respuesta</summary>Para conservar la intensidad: si muchos ítems de la historia son relevantes para el candidato, la suma de pesos (y la norma de $v_U$) debe ser mayor que si solo uno lo es.</details>

6. Tienes un "CTR histórico del ítem" que da +5 puntos de AUC offline y 0 online. ¿Qué sospechas y cómo lo compruebas?
<details><summary>Respuesta</summary>Fuga: se calculó con datos posteriores a la impresión (o incluyendo su propia etiqueta). Comprobación: recalcularlo point-in-time (solo eventos con timestamp anterior) y ver si la ganancia offline desaparece.</details>

7. ¿Qué compromiso controla el número de cubos $B$ del hashing trick?
<details><summary>Respuesta</summary>Memoria y latencia frente a colisiones: con $m$ valores, la fracción colisionada ≈ $1-e^{-m/B}$. Demasiado grande además sobreajusta en IDs raros si no hay umbral de frecuencia.</details>

## 📚 15. Referencias
**Papers**
- He, X. et al. (2014). *Practical Lessons from Predicting Clicks on Ads at Facebook*. ADKDD. https://dl.acm.org/doi/10.1145/2648584.2648589
- McMahan, H. B. et al. (2013). *Ad Click Prediction: a View from the Trenches*. KDD. https://dl.acm.org/doi/10.1145/2487575.2488200
- Weinberger, K. et al. (2009). *Feature Hashing for Large Scale Multitask Learning*. ICML. https://arxiv.org/abs/0902.2206
- Rendle, S. (2010). *Factorization Machines*. ICDM.
- Juan, Y. et al. (2016). *Field-aware Factorization Machines for CTR Prediction*. RecSys.
- Cheng, H.-T. et al. (2016). *Wide & Deep Learning for Recommender Systems*. https://arxiv.org/abs/1606.07792
- Guo, H. et al. (2017). *DeepFM: A Factorization-Machine based Neural Network for CTR Prediction*. IJCAI. https://arxiv.org/abs/1703.04247
- Wang, R. et al. (2017). *Deep & Cross Network for Ad Click Predictions*. https://arxiv.org/abs/1708.05123
- Wang, R. et al. (2021). *DCN V2: Improved Deep & Cross Network and Practical Lessons for Web-scale Learning to Rank Systems*. WWW. https://arxiv.org/abs/2008.13535
- Zhou, G. et al. (2018). *Deep Interest Network for Click-Through Rate Prediction*. KDD. https://arxiv.org/abs/1706.06978
- Zhou, G. et al. (2019). *Deep Interest Evolution Network for CTR Prediction*. AAAI. https://arxiv.org/abs/1809.03672
- Naumov, M. et al. (2019). *Deep Learning Recommendation Model for Personalization and Recommendation Systems* (DLRM). https://arxiv.org/abs/1906.00091
- Zhu, J. et al. (2021). *Open Benchmarking for Click-Through Rate Prediction* (FuxiCTR/BARS). CIKM. https://arxiv.org/abs/2009.05794
- Zhang, Z. et al. (2022). *Towards Understanding the Overfitting Phenomenon of Deep Click-Through Rate Prediction Models*. CIKM. https://arxiv.org/abs/2209.06053
- Anil, R. et al. (2022). *On the Factory Floor: ML Engineering for Industrial-Scale Ads Recommendation Models*. https://arxiv.org/abs/2209.05310
- Liu, Z. et al. (2022). *Monolith: Real Time Recommendation System With Collisionless Embedding Table*. https://arxiv.org/abs/2209.07663
- Kang, W.-C. et al. (2021). *Learning to Embed Categorical Features without Embedding Tables for Recommendation* (DHE). KDD. https://arxiv.org/abs/2010.10784
- Grinsztajn, L. et al. (2022). *Why do tree-based models still outperform deep learning on tabular data?* NeurIPS. https://arxiv.org/abs/2207.08815
- Guo, C. et al. (2017). *On Calibration of Modern Neural Networks*. ICML. https://arxiv.org/abs/1706.04599
- Zhang, B. et al. (2024). *Wukong: Towards a Scaling Law for Large-Scale Recommendation*. https://arxiv.org/abs/2403.02545

**Librerías y datos**
- TorchRec: https://github.com/pytorch/torchrec · NVIDIA Merlin: https://github.com/NVIDIA-Merlin/Merlin · FuxiCTR: https://github.com/reczoo/FuxiCTR · BARS: https://github.com/reczoo/BARS · DeepCTR-Torch: https://github.com/shenweichen/DeepCTR-Torch · LightGBM: https://lightgbm.readthedocs.io
- Criteo 1TB en Hugging Face: https://huggingface.co/datasets/criteo/CriteoClickLogs · Datasets preprocesados de reczoo (Criteo_x1, Avazu_x1…): https://github.com/reczoo/Datasets
""")
    nb.save(f"recsys-course/{MOD}/{MOD}.ipynb")


# ============================================================================
# PROYECTO
# ============================================================================
def build_project():
    path = f"recsys-course/{MOD}/06_proyecto_ranker_ctr.ipynb"
    nb = Notebook("Proyecto 06 · Ranker CTR de CineMatch", colab_path=path, gpu=True)
    header(nb, "06", "Proyecto: ranker de la home de CineMatch — DCN-v2 vs LightGBM",
           "🟠 Avanzado", "4–6 h", "L4 o A100 (T4 vale con FAST_DEV_RUN)", "~5–10",
           "Lección 06 (y 01, 02, 05)", tipo="Proyecto")
    nb.md(r"""
## 🏢 Contexto de negocio
Eres ML engineer del equipo de **Ranking de la Home de CineMatch**. El retrieval (módulos 04–05, y pronto el two-tower del 08) ya entrega ~500 candidatos por usuario. Hoy se ordenan por popularidad. Producto quiere un **ranker** que estime $P(\text{el usuario valora bien la película} \mid \text{se la mostramos})$ y lo necesita **calibrado**, porque el equipo de la home (módulo 07 y 13) va a mezclar esta probabilidad con otros objetivos.

El *tech lead* tiene dos dudas que resolverás con datos:
1. ¿Merece la pena un **DCN-v2** en GPU frente a un **LightGBM** (que ya sabe operar el equipo)?
2. Un compañero propone la feature "rating medio de la película" calculada con **todo** el histórico. ¿Es una buena idea?

## 📦 Dataset
**MovieLens-1M** (GroupLens): 1 M valoraciones, 6 040 usuarios con demografía (sexo, edad, ocupación, código postal), 3 706 películas con géneros y año. Lo convertimos en un problema de CTR:
- Cada valoración = una **impresión** que el usuario aceptó ver; etiqueta $y = 1$ si `rating ≥ 4` ("le gustó") y 0 si no.
- Features: usuario (id, sexo, edad, ocupación, prefijo postal), película (id, géneros multi-hot, década), contexto (hora, día de la semana) y **features de conteo point-in-time**.
- Split **temporal global** 80/10/10 (utilidades de los módulos 01/02).

## ✅ Entregables y rúbrica
| # | Entregable | Criterio |
|---|---|---|
| 1 | Pipeline de features **sin fuga** (point-in-time) | Test unitario incluido pasa |
| 2 | Demostración cuantitativa de la fuga con la feature "leaky" | Tabla offline con ambas versiones y explicación |
| 3 | LightGBM bien tuneado (early stopping en val) | AUC test ≥ baseline de popularidad + 0,04 (referencia `FAST_DEV_RUN`: 0,733 → 0,779) |
| 4 | DCN-v2 en PyTorch (embeddings de todos los campos) | Logloss test ≤ 1,03 × la de LightGBM (referencia: 0,572 vs 0,561; el mejor punto llega en la 1.ª época) |
| 5 | Calibración: reliability diagram + ECE + NE para ambos | ECE < 0,02 tras calibrar (si hace falta) |
| 6 | Recomendación razonada al *tech lead* (5–10 líneas) | Considera métricas, coste, operación, latencia |

Referencias orientativas (MovieLens-1M real, `FAST_DEV_RUN=False`): AUC ≈ 0,75–0,82 y logloss ≈ 0,50–0,56 son valores típicos para este planteamiento; con datos sintéticos los números serán distintos.
""")
    nb.code(r'''
!pip install -q lightgbm
''')
    nb.code(SETUP_CODE)
    nb.code(r'''
FAST_DEV_RUN = True   # False en GPU para más épocas y LightGBM más grande
''')
    nb.md(ML_UTILS_MD)
    nb.code(ML_UTILS_CODE)
    nb.code(TRAIN_UTILS)
    nb.code(r'''
ratings, movies, users = load_movielens("1m")
df = (ratings.merge(users, on="user_id", how="left").merge(movies, on="item_id", how="left")
      .sort_values("timestamp").reset_index(drop=True))
df["y"] = (df.rating >= 4).astype(np.float32)
dt = pd.to_datetime(df.timestamp, unit="s")
df["hour"], df["dow"] = dt.dt.hour, dt.dt.dayofweek
df["year"] = df.title.str.extract(r"\((\d{4})\)").astype(float).fillna(1990)
df["decade"] = (df.year // 10 * 10).astype(int)
df["zip1"] = df.zip.astype(str).str[:1]
train, val, test = temporal_split(df)
print(len(train), len(val), len(test), "| tasa de positivos:", round(df.y.mean(), 3))
''')
    nb.md(r"""
## Paso 1 — Features de conteo *point-in-time* (y la versión con fuga)
Implementa `point_in_time_item_stats(df)` que, para cada fila, calcule con **solo eventos anteriores** (por timestamp, sin incluir la propia fila):
- `item_cnt_pit`: nº de valoraciones previas de la película,
- `item_pos_rate_pit`: tasa de positivos previa con suavizado bayesiano $\frac{\text{pos} + \alpha\, \bar y}{\text{cnt} + \alpha}$ ($\alpha=20$, $\bar y$ = tasa global de **train**),
- lo mismo para el usuario (`user_cnt_pit`, `user_pos_rate_pit`).

La versión con fuga (`item_pos_rate_leaky`) usa todo el dataset (ya la damos hecha).

💡 Pista: ordena por `timestamp`, usa `groupby(...).cumsum()` y resta la propia fila (`shift`).
""")
    nb.code(r'''
ALPHA = 20.0
PRIOR = float(train.y.mean())

def point_in_time_item_stats(df: pd.DataFrame) -> pd.DataFrame:
    # TODO: devuelve un DataFrame (mismo índice que df) con columnas
    #       item_cnt_pit, item_pos_rate_pit, user_cnt_pit, user_pos_rate_pit
    raise NotImplementedError

# Feature con FUGA (no la uses en el modelo final): tasa de positivos con TODO el histórico
df["item_pos_rate_leaky"] = df.groupby("item_id").y.transform("mean")
df["user_pos_rate_leaky"] = df.groupby("user_id").y.transform("mean")
''')
    nb.code(r'''
# Test unitario (no lo modifiques): la feature de un evento NO puede depender de eventos futuros ni de sí mismo
def _test_pit(fn):
    toy = pd.DataFrame({"user_id": [1, 2, 1, 3], "item_id": [7, 7, 7, 8],
                        "timestamp": [1, 2, 3, 4], "y": [1.0, 0.0, 1.0, 1.0]})
    out = fn(toy)
    assert np.allclose(out.item_cnt_pit.values, [0, 1, 2, 0]), out
    expected_rate_3rd = (1 + 0 + ALPHA * PRIOR) / (2 + ALPHA)
    assert abs(out.item_pos_rate_pit.values[2] - expected_rate_3rd) < 1e-9
    assert abs(out.item_pos_rate_pit.values[0] - PRIOR) < 1e-9
    print("✅ point-in-time OK")
try:
    _test_pit(point_in_time_item_stats)
except NotImplementedError:
    print("⏳ Implementa point_in_time_item_stats")
''')
    nb.md(r"""
## Paso 2 — Codificación de features para LightGBM y para el modelo profundo
- `CAT_FEATS` → índices enteros (vocabulario **de train**, OOV=0) y, para el deep, índices **globales** con *offsets*.
- `NUM_FEATS` → para LightGBM tal cual; para el deep, **bucketiza** en cuantiles de train (20 bins) y trátalas como categóricas.
- Géneros: multi-hot (18 columnas binarias) → para el deep, cada género es un campo binario (0/1).
""")
    nb.code(r'''
CAT_FEATS = ["user_id", "item_id", "gender", "age", "occupation", "zip1", "decade", "hour", "dow"]
NUM_FEATS = ["item_cnt_pit", "item_pos_rate_pit", "user_cnt_pit", "user_pos_rate_pit"]
GENRES = sorted({g for gs in movies.genres for g in gs.split("|")})

def encode(df: pd.DataFrame, train_mask: np.ndarray, num_feats: list):
    """Devuelve (X_lgb: DataFrame, X_deep: int array [N, F], field_dims)."""
    # TODO 1: añade columnas multi-hot de género 'g_<Genero>' a df
    # TODO 2: X_lgb = categóricas codificadas (vocab train, OOV=0, dtype 'category') + numéricas + géneros
    # TODO 3: X_deep = categóricas + numéricas bucketizadas (20 cuantiles de train) + géneros (0/1), con offsets globales
    raise NotImplementedError
''')
    nb.md(r"""
## Paso 3 — Baseline de popularidad y LightGBM
Baseline: `item_pos_rate_pit` como score directamente. Luego entrena LightGBM con early stopping (pista: `num_leaves` 63–255, `learning_rate` 0,05, `min_data_in_leaf` ≥ 100).
""")
    nb.code(r'''
import lightgbm as lgb

def train_lgb(Xtr, ytr, Xva, yva):
    # TODO: entrena con early stopping y devuelve el booster
    raise NotImplementedError
''')
    nb.md(r"""
## Paso 4 — DCN-v2 (reutiliza tu implementación de la lección)
Implementa `DCNv2` con capas de cruce `x_{l+1} = x0 * (W x_l + b) + x_l` y la parte deep *stacked* o *parallel*. Entrena con `train_ctr` (incluida arriba).
""")
    nb.code(r'''
class DCNv2(nn.Module):
    def __init__(self, field_dims, k=16, n_cross=3, hidden=(256, 256), dropout=0.1):
        super().__init__()
        # TODO
        raise NotImplementedError
    def forward(self, x):
        raise NotImplementedError
''')
    nb.md(r"""
## Paso 5 — Fuga, calibración y recomendación final
1. Entrena LightGBM **con** `item_pos_rate_leaky` y compara offline (val/test) con la versión point-in-time. ¿Por qué parece mejor? ¿Qué pasaría en producción?
2. Reliability diagrams + ECE + NE para LightGBM y DCN-v2 (y una calibración isotónica en val si hace falta).
3. Escribe tu recomendación al *tech lead*.
""")
    nb.code(r'''
# TODO: tu análisis final aquí
''')

    # ------------------------------- SOLUCIÓN --------------------------------
    nb.md(r"""
---
# ⛔ SPOILER — Solución de referencia
Intenta resolverlo primero. Lo que sigue es una solución completa y ejecutable.
""")
    nb.code(r'''
def point_in_time_item_stats(df: pd.DataFrame) -> pd.DataFrame:
    d = df[["user_id", "item_id", "timestamp", "y"]].copy()
    d["_ord"] = np.arange(len(d))
    d = d.sort_values(["timestamp", "_ord"], kind="mergesort")
    out = pd.DataFrame(index=d.index)
    for key, pref in [("item_id", "item"), ("user_id", "user")]:
        g = d.groupby(key)
        cnt = g.cumcount().astype(float)                  # nº de eventos ANTERIORES
        pos = g.y.cumsum() - d.y                          # positivos anteriores (excluye la fila)
        out[f"{pref}_cnt_pit"] = cnt
        out[f"{pref}_pos_rate_pit"] = (pos + ALPHA * PRIOR) / (cnt + ALPHA)
    return out.loc[df.index]
# Nota: eventos con el MISMO timestamp se ordenan por orden de llegada; en producción
# se usaría además un retardo (los contadores llegan con minutos de latencia).

_test_pit(point_in_time_item_stats)
df = df.join(point_in_time_item_stats(df))
train, val, test = temporal_split(df)
tr_m = df.index.isin(train.index); va_m = df.index.isin(val.index); te_m = df.index.isin(test.index)
''')
    nb.code(r'''
def encode(df: pd.DataFrame, train_mask: np.ndarray, num_feats: list):
    df = df.copy()
    for g in GENRES:
        df["g_" + g] = df.genres.fillna("").str.contains(g, regex=False).astype(np.int8)
    gcols = ["g_" + g for g in GENRES]
    X_lgb = pd.DataFrame(index=df.index)
    deep_cols, field_dims = [], []
    for c in CAT_FEATS:
        vocab = pd.Index(df.loc[train_mask, c].astype(str).unique())
        codes = vocab.get_indexer(df[c].astype(str)) + 1               # -1 (OOV) → 0
        X_lgb[c] = pd.Categorical(codes)
        deep_cols.append(codes); field_dims.append(len(vocab) + 1)
    for c in num_feats:
        X_lgb[c] = df[c].values
        qs = np.unique(np.quantile(df.loc[train_mask, c], np.linspace(0, 1, 21)[1:-1]))
        deep_cols.append(np.digitize(df[c].values, qs)); field_dims.append(len(qs) + 1)
    for c in gcols:
        X_lgb[c] = df[c].values
        deep_cols.append(df[c].values.astype(int)); field_dims.append(2)
    offsets = np.cumsum([0] + field_dims[:-1])
    X_deep = (np.stack(deep_cols, 1) + offsets).astype(np.int32)
    return X_lgb, X_deep, field_dims

X_lgb, X_deep, field_dims = encode(df, tr_m, NUM_FEATS)
y = df.y.values.astype(np.float32)
print(X_lgb.shape, X_deep.shape, "tabla de embeddings:", sum(field_dims))
''')
    nb.code(r'''
pop_auc = roc_auc_score(y[te_m], df.item_pos_rate_pit.values[te_m])
print(f"Baseline popularidad point-in-time · AUC test = {pop_auc:.4f}")

def train_lgb(Xtr, ytr, Xva, yva):
    params = dict(objective="binary", learning_rate=0.05, num_leaves=127, min_data_in_leaf=200,
                  feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0,
                  cat_smooth=20, min_data_per_group=100, verbose=-1, seed=seed)
    return lgb.train(params, lgb.Dataset(Xtr, ytr), num_boost_round=400 if FAST_DEV_RUN else 3000,
                     valid_sets=[lgb.Dataset(Xva, yva)], callbacks=[lgb.early_stopping(50, verbose=False)])

t0 = time.time()
gbm = train_lgb(X_lgb[tr_m], y[tr_m], X_lgb[va_m], y[va_m])
p_lgb = gbm.predict(X_lgb[te_m], num_iteration=gbm.best_iteration)
BASE = y[tr_m].mean()
R = {"Popularidad PIT": {**ctr_metrics(y[te_m], np.clip(df.item_pos_rate_pit.values[te_m], 1e-4, 1-1e-4), BASE)},
     "LightGBM": {**ctr_metrics(y[te_m], p_lgb, BASE), "seg": time.time() - t0}}
print(pd.DataFrame(R).T.round(4))
''')
    nb.code(r'''
class CrossLayerV2(nn.Module):
    def __init__(self, d):
        super().__init__(); self.W = nn.Linear(d, d)
    def forward(self, x0, xl):
        return x0 * self.W(xl) + xl

class DCNv2(nn.Module):
    def __init__(self, field_dims, k=16, n_cross=3, hidden=(256, 256), dropout=0.1):
        super().__init__()
        d = len(field_dims) * k
        self.emb = nn.Embedding(sum(field_dims), k); nn.init.normal_(self.emb.weight, std=0.01)
        self.cross = nn.ModuleList([CrossLayerV2(d) for _ in range(n_cross)])
        layers, a = [], d
        for h in hidden:
            layers += [nn.Linear(a, h), nn.ReLU(), nn.Dropout(dropout)]; a = h
        self.deep = nn.Sequential(*layers)
        self.head = nn.Linear(d + hidden[-1], 1)                        # estructura 'parallel'
    def forward(self, x):
        x0 = self.emb(x).flatten(1); xl = x0
        for c in self.cross:
            xl = c(x0, xl)
        return self.head(torch.cat([xl, self.deep(x0)], 1)).squeeze(1)

torch.manual_seed(seed); t0 = time.time()
dcn, hist = train_ctr(DCNv2(field_dims), X_deep[tr_m], y[tr_m], X_deep[va_m], y[va_m],
                      epochs=3 if FAST_DEV_RUN else 6, bs=2048, lr=1e-3, wd=1e-6)
p_dcn = predict_proba(dcn, X_deep[te_m])
R["DCN-v2"] = {**ctr_metrics(y[te_m], p_dcn, BASE), "seg": time.time() - t0}
pd.DataFrame(R).T.round(4)
''')
    nb.code(r'''
# Fuga: la misma LightGBM pero con la feature calculada con TODO el histórico
X_leak = X_lgb.copy()
X_leak["item_pos_rate_leaky"] = df.item_pos_rate_leaky.values; X_leak["user_pos_rate_leaky"] = df.user_pos_rate_leaky.values
gbm_leak = train_lgb(X_leak[tr_m], y[tr_m], X_leak[va_m], y[va_m])
p_leak = gbm_leak.predict(X_leak[te_m], num_iteration=gbm_leak.best_iteration)
R["LightGBM + feature con FUGA"] = ctr_metrics(y[te_m], p_leak, BASE)
display(pd.DataFrame(R).T.round(4))
imp = pd.Series(gbm_leak.feature_importance("gain"), index=X_leak.columns).sort_values()[-12:]
imp.plot.barh(figsize=(6, 4), title="Importancia (gain) con la feature con fuga"); plt.show()
''')
    nb.md(r"""
**Interpretación de la fuga**: las features `*_leaky` incluyen la etiqueta de la propia fila y valoraciones **futuras**. El tamaño del efecto depende de **cuántos eventos tiene cada entidad**: para una película con miles de valoraciones, la media completa casi coincide con la point-in-time (la fuga del ítem sola apenas mueve el AUC: en la ejecución de referencia 0,779 → 0,781), pero un usuario tiene decenas o pocos cientos de valoraciones y su media «del futuro» sí delata su propia etiqueta. Compara la tabla y la importancia: la feature de usuario con fuga infla el AUC offline. En producción ese valor no existe al servir (solo conoces el pasado), así que el modelo se apoya en una señal que desaparece. Es el error #1 en features de conteo, y es más grave cuanto más «de cola» es la entidad (usuarios nuevos, anuncios recién creados).
""")
    nb.code(r'''
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression
def ece(y_, p_, bins=15):
    q = np.quantile(p_, np.linspace(0, 1, bins + 1)); b = np.clip(np.digitize(p_, q[1:-1]), 0, bins - 1)
    return sum(abs(y_[b == i].mean() - p_[b == i].mean()) * (b == i).mean() for i in range(bins) if (b == i).any())

iso = IsotonicRegression(out_of_bounds="clip").fit(predict_proba(dcn, X_deep[va_m]), y[va_m])
cands = {"LightGBM": p_lgb, "DCN-v2": p_dcn, "DCN-v2 + isotónica": iso.predict(p_dcn)}
plt.figure(figsize=(5.5, 5))
for k, p in cands.items():
    fr, mp = calibration_curve(y[te_m], p, n_bins=15, strategy="quantile")
    plt.plot(mp, fr, "o-", ms=3, label=f"{k} · ECE={ece(y[te_m], p):.4f} · NE={normalized_entropy(y[te_m], p, BASE):.3f}")
plt.plot([0, 1], [0, 1], "k--", lw=0.8); plt.legend(fontsize=7); plt.xlabel("p̂"); plt.ylabel("tasa observada")
plt.title("Reliability diagram — test temporal"); plt.show()
print({k: round(ece(y[te_m], p), 4) for k, p in cands.items()})
''')
    nb.code(r'''
# Coste de inferencia aproximado (CPU/GPU actual) para 500 candidatos
Xc_lgb, Xc_deep = X_lgb[te_m].iloc[:500], X_deep[te_m][:500]
t0 = time.perf_counter(); [gbm.predict(Xc_lgb, num_iteration=gbm.best_iteration) for _ in range(20)]; t_lgb = (time.perf_counter() - t0) / 20
t0 = time.perf_counter(); [predict_proba(dcn, Xc_deep) for _ in range(20)]; t_dcn = (time.perf_counter() - t0) / 20
print(f"Latencia por petición (500 candidatos): LightGBM {t_lgb*1e3:.1f} ms | DCN-v2 {t_dcn*1e3:.1f} ms ({device})")
''')
    nb.md(r"""
### Recomendación modelo al *tech lead* (ejemplo de respuesta)
> En el split temporal, LightGBM y DCN-v2 quedan muy cerca en logloss/AUC sobre MovieLens-1M: con pocas features de ID y muchas agregadas, el GBDT es un rival durísimo. DCN-v2 gana cuando aumentan los IDs y las secuencias (historia del usuario), y comparte embeddings con el two-tower del módulo 08. Propongo: (1) poner en producción **LightGBM** ya (operación conocida, latencia de ~ms en CPU), con las features **point-in-time** (la versión "leaky" infla el AUC offline y fallaría online); (2) A/B de DCN-v2 cuando añadamos la historia del usuario (DIN) y multi-tarea (módulo 07); (3) monitorizar ECE/NE y el ratio Σp/Σy por segmento, y recalibrar con isotónica en cada reentreno.

## 🚀 Retos extra
1. **Criteo real**: corre la lección con `FAST_DEV_RUN=False` (5 M filas) y compara DCN-v2 *stacked* vs *parallel* vs low-rank (`rank=64`). ¿Cuánta logloss pierdes con bajo rango y cuánta memoria ganas?
2. **DIN en CineMatch**: añade la historia de las últimas 50 películas como feature secuencial al ranker de este proyecto.
3. **Mixed negative sampling y exposure**: MovieLens solo tiene ítems valorados. Añade negativos muestreados (no vistos) y estudia cómo cambia la calibración.
4. **TorchRec**: reescribe la tabla de embeddings con `EmbeddingBagCollection` y una tabla por campo.
5. **5 semillas**: repite LightGBM y DCN-v2 con 5 semillas y reporta media ± desviación. ¿Es significativa la diferencia?

## 🤔 Reflexión (producción / MLOps)
- ¿Cómo garantizarías en un **feature store** (Feast, módulo 16) que las features de conteo del entrenamiento son exactamente las que verá el modelo al servir (*training-serving skew*)?
- ¿Con qué frecuencia reentrenarías? ¿Qué métrica de monitoreo dispararía un reentreno (módulo 17)?
- Si el modelo se usa para mezclar objetivos en la home, ¿qué alerta pondrías sobre la calibración?
""")
    nb.save(path)


if __name__ == "__main__":
    build_lesson()
    build_project()
