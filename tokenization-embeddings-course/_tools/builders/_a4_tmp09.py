"""Builder del módulo 09 · La capa de embedding en LLMs  (autor A4).

Uso (desde la raíz del repo):  python tokenization-embeddings-course/_tools/builders/build_09.py
Genera la lección y el proyecto del módulo 09. Nunca edites los .ipynb a mano.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]            # .../tokenization-embeddings-course
sys.path.insert(0, str(ROOT / "_tools"))
sys.path.insert(0, str(ROOT / "_tools" / "builders"))
from nbbuild import Notebook                                   # noqa: E402
from poliglota_utils import SRC_METRICS, src_corpus_cells      # noqa: E402

MOD = "09_capa_embedding_llm"
LESSON = f"tokenization-embeddings-course/{MOD}/09_capa_embedding_llm.ipynb"
PROJECT = f"tokenization-embeddings-course/{MOD}/09_proyecto_capa_embedding_llm.ipynb"

SETUP = r'''
!pip install -q transformers tokenizers datasets scipy scikit-learn matplotlib tiktoken
import copy, json, math, os, random, re, time, warnings
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
from collections import Counter
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn.functional as F

warnings.filterwarnings("ignore")
SEED = 42
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
device = "cuda" if torch.cuda.is_available() else "cpu"
FAST_DEV_RUN = True   # True: minutos en CPU con modelos diminutos. False: corpus más grande y más pasos
PAL = {"azul": "#1F6FEB", "naranja": "#F28E2B", "verde": "#2CA02C", "gris": "#6B7280"}
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.25,
                     "axes.spines.top": False, "axes.spines.right": False})
print(f"device={device} · FAST_DEV_RUN={FAST_DEV_RUN} · torch {torch.__version__}")
'''

CORPUS_USE = r'''
corpus = carga_corpus(FAST_DEV_RUN)
docs = corpus["docs"]
textos = [d["text"] for d in docs]
print("fuente:", corpus["source"], "| docs por idioma:", dict(Counter(d["lang"] for d in docs)))
print("ejemplo ES:", next(d["text"] for d in docs if d["lang"] == "es")[:160], "...")
'''

MINI_LM = r'''
# ── Mini-LM de laboratorio: tokenizer BPE byte-level + GPT-2 diminuto (misma API de Hugging Face que GPT-2 real) ──
from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers
from transformers import GPT2Config, GPT2LMHeadModel, PreTrainedTokenizerFast


def entrena_tokenizer(textos, vocab_size=500):
    tk = Tokenizer(models.BPE())
    tk.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tk.decoder = decoders.ByteLevel()
    tr = trainers.BpeTrainer(vocab_size=vocab_size, special_tokens=["<|endoftext|>"],
                             initial_alphabet=pre_tokenizers.ByteLevel.alphabet())
    tk.train_from_iterator(textos, tr)
    return PreTrainedTokenizerFast(tokenizer_object=tk, eos_token="<|endoftext|>", pad_token="<|endoftext|>")


def crea_mini_gpt(tok, tie=True, d=64, seed=SEED):
    torch.manual_seed(seed)
    cfg = GPT2Config(vocab_size=len(tok), n_positions=64, n_embd=d, n_layer=2, n_head=2, tie_word_embeddings=tie,
                     bos_token_id=tok.eos_token_id, eos_token_id=tok.eos_token_id)
    return GPT2LMHeadModel(cfg)


def flujo_ids(tok, textos):
    ids = []
    for t in textos:
        ids += tok(t)["input_ids"] + [tok.eos_token_id]
    return torch.tensor(ids)


def entrena_lm(model, data, steps=300, lr=3e-3, wd=0.0, B=16, T=48, seed=SEED):
    """Bucle de entrenamiento mínimo (AdamW). Devuelve la lista de pérdidas por paso."""
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=wd)
    g = torch.Generator().manual_seed(seed)
    model.train(); hist = []
    for _ in range(steps):
        ix = torch.randint(0, len(data) - T - 1, (B,), generator=g)
        x = torch.stack([data[i:i + T] for i in ix])
        loss = model(input_ids=x, labels=x).loss
        opt.zero_grad(); loss.backward(); opt.step(); hist.append(loss.item())
    model.eval()
    return hist


@torch.no_grad()
def val_loss(model, data, T=48, n=64):
    xs = torch.stack([data[i:i + T] for i in range(0, min(len(data) - T - 1, n * T), T)])
    return model(input_ids=xs, labels=xs).loss.item()
'''

# ════════════════════════════════════════════════════════════════════════════════════════
#  LECCIÓN 09
# ════════════════════════════════════════════════════════════════════════════════════════
nb = Notebook("Módulo 09 · La capa de embedding en LLMs", colab_path=LESSON)

nb.md(nb.badge() + r"""
# Módulo 09 · La capa de embedding en LLMs

| | |
|---|---|
| **Nivel** | 🟡 Intermedio |
| **Duración** | ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) |
| **Cómputo** | CPU basta (modelos diminutos en `FAST_DEV_RUN`); GPT-2 small (124M) corre en CPU. T4 opcional. **0 unidades de Colab** necesarias |
| **Prerrequisitos** | 02 (BPE), 05 (tokens sub-entrenados), 07 (inicialización de vocabulario nuevo), PyTorch y atención |
| **Hilo conductor** | Políglota Labs: antes de construir *embedders* (10–12) hay que entender la tabla de vectores que usa cualquier modelo de texto: la **capa de embedding** |

> **Dónde estamos.** Los módulos 01–08 respondieron «¿cómo se parte el texto en tokens?». Este módulo abre el bloque B y responde
> **«¿qué pasa con un token id dentro de un modelo?»**: se convierte en un vector (lookup en la matriz $E$), y al final del modelo
> otro producto con una matriz (*unembedding*) lo vuelve a convertir en una distribución sobre el vocabulario.
> Esa matriz es la que luego aparece en glitch tokens (05), en el *tokenizer transfer* (07) y, con otra forma, en los embedders de oraciones (10–12).
""")

nb.md(r"""
## Objetivos de aprendizaje
Al terminar podrás:
1. **Explicar** que `nn.Embedding` equivale a `one_hot @ E` y **deducir** por qué solo las filas de los tokens vistos reciben gradiente de entrada.
2. **Calcular** el peso de la capa de embedding/unembedding en el total de parámetros y **cuantificar** lo que ahorra el *weight tying* (Press & Wolf, 2017).
3. **Derivar** el gradiente de la pérdida respecto a una fila del unembedding y **predecir** qué ocurre con los tokens que casi nunca son objetivo (degeneración de representaciones).
4. **Medir** la geometría de $E$ en un LM: normas vs frecuencia, espectro singular, anisotropía, vecinos y estructura lineal (dígitos/años).
5. **Demostrar** el cuello de botella softmax (rango $\le d$) con un experimento y **cuantificar** el coste de la cabeza de salida.
6. **Extender** el vocabulario de un LM con tokens de dominio, comparar inicializaciones (aleatoria, media, media de sub-tokens) y medirlas con *bits por byte*, fertilidad y masa de probabilidad filtrada.
7. **Ubicar** word2vec/GloVe/PMI como antecedente histórico de la misma tabla $E$.
""")

nb.md(r"""
## 🔁 Conexión con módulos anteriores
Responde antes de seguir (la respuesta está plegada):

<details><summary><b>1.</b> (Módulo 02) Un tokenizer BPE devuelve una lista de ids enteros. ¿Qué información sobre el significado de un token contiene su id por sí solo?</summary>

**Ninguna.** El id es solo un índice en una lista de merges/vocabulario; ids vecinos (p. ej. 1024 y 1025) no tienen relación semántica. Todo el «significado» lo aportará la fila de $E$ que el entrenamiento asocie a ese id.
</details>

<details><summary><b>2.</b> (Módulo 05) ¿Por qué existen tokens «sub-entrenados» y por qué sus embeddings son sospechosos?</summary>

Porque el tokenizer se entrenó con datos distintos de los del modelo: hay tokens en el vocabulario que (casi) nunca aparecen al entrenar el LM, y por tanto su fila de $E$ se quedó cerca de su valor inicial (o derivó por efectos del softmax). En este módulo veremos **la mecánica** que lo causa, sin repetir los detectores del 05.
</details>

<details><summary><b>3.</b> (Módulo 07) Si cambias el tokenizer de un modelo, ¿qué parte del modelo deja de ser válida?</summary>

La **matriz de embeddings** (y la de salida): sus filas están indexadas por el vocabulario viejo. Hay que construir filas nuevas (inicialización) y reajustar. Aquí estudiamos el caso más sencillo, *añadir* tokens, y medimos qué inicialización pierde menos.
</details>
""")

nb.code(SETUP)

nb.md(r"""
### Utilidades del curso: corpus Políglota (módulo 00)
Las tres celdas siguientes son la implementación canónica de `carga_corpus()` del módulo 00 (cadena **oficial → espejo → sintético**). Cada notebook del curso las copia para ser autocontenido.
Si ves el aviso «SIN acceso a Wikipedia», estás con el corpus **sintético** (mismo esquema): los números absolutos no son comparables con los reales, pero todos los mecanismos funcionan.
""")
for _src in src_corpus_cells():
    nb.code(_src)
nb.code(CORPUS_USE)

nb.md(r"""
## 1. Intuición: un embedding es una tabla de búsqueda

**El problema.** Una red neuronal multiplica matrices de números reales; un tokenizer produce enteros sin estructura (el id 4181 no está «cerca» del 4182).
Necesitamos una función $\text{id} \mapsto \mathbb{R}^d$ **entrenable**. La más simple posible es una tabla con una fila por token: $E \in \mathbb{R}^{V\times d}$.

> 💡 **Intuición (analogía con recsys).** Si trabajaste con el `recsys-course/`, esto es exactamente la **tabla de embeddings de ítems** (`item_id → vector`) de un modelo de filtrado colaborativo o de un *two-tower*:
> el *id* no significa nada, pero cada ítem tiene una fila que se aprende de las interacciones. Aquí los «ítems» son tokens y las «interacciones» son los contextos donde aparecen.
> Los problemas son los mismos: **cola larga** (ítems/tokens raros casi no reciben gradiente), **arranque en frío** (un ítem/token nuevo no tiene fila entrenada) y una **capa de salida** enorme (softmax sobre millones de ítems / decenas de miles de tokens).

Lo que hace `nn.Embedding(V, d)` es *indexar*: devolver la fila $E[\text{id}]$. Matemáticamente es lo mismo que multiplicar un vector *one-hot* por $E$, solo que sin hacer el producto:

$$\mathbf{e}_t = E^\top \mathbf{o}_t = E[t,:], \qquad \mathbf{o}_t\in\{0,1\}^V,\ \ (\mathbf{o}_t)_j = \mathbb{1}[j=t].$$
""")

nb.code(r'''
# Ejemplo a mano: vocabulario de 5 tokens, d = 2. Lookup == one-hot @ E, y el gradiente solo llega a las filas usadas.
vocab = ["<pad>", "el", "gato", "come", "pescado"]
E_toy = torch.tensor([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [-1.0, 1.0]], requires_grad=True)
ids = torch.tensor([1, 2, 3, 4])                       # "el gato come pescado"

via_lookup = E_toy[ids]                                # indexación (lo que hace nn.Embedding)
via_onehot = F.one_hot(ids, num_classes=len(vocab)).float() @ E_toy
assert torch.equal(via_lookup, via_onehot)
print("lookup == one_hot @ E :", True)

loss = via_lookup.pow(2).sum()                         # una pérdida cualquiera
loss.backward()
print("gradiente de E:\n", E_toy.grad)                 # la fila 0 (<pad>) NO recibe gradiente: nunca se usó
''')

nb.md(r"""
> 👀 **Qué debes observar.** (1) `lookup` y `one_hot @ E` dan **exactamente** lo mismo: el lookup es una optimización de memoria/cómputo del producto con un one-hot ($O(d)$ en vez de $O(Vd)$).
> (2) El gradiente de la fila 0 es cero: **solo se actualizan las filas de los tokens que aparecen en el batch**. Es la raíz de todos los problemas de cola larga que verás hoy.
""")

nb.gemini(
    "imagen", "M09-IMG-01", "De token id a vector y de vuelta a probabilidades",
    "El recorrido completo de un token por un LM: tokenizer → ids → lookup en E → Transformer → unembedding → softmax. Fija el vocabulario visual (E vs W_U, V×d) que se usa en todo el módulo.",
    """
    Diagrama técnico limpio, fondo blanco, formato 16:9, estilo de infografía de ingeniería (sin ilustraciones decorativas). Paleta: azul #1F6FEB para la entrada, naranja #F28E2B para la salida, verde #2CA02C para el Transformer, gris #6B7280 para texto secundario. Tipografía sans-serif legible.
    Composición de izquierda a derecha en seis bloques unidos por flechas gruesas:
    1) Caja gris «Texto: "El gato come pescado"».
    2) Caja «Tokenizer (BPE)» con salida «ids: [1212, 8745, 5981, 22104]».
    3) Una matriz grande azul rotulada «E  (V × d)» con 6 filas visibles etiquetadas «fila 0», «fila 1», …, «fila V-1»; de los ids salen flechas finas azules que resaltan SOLO las filas 1212, 8745, 5981 y 22104. Debajo: «lookup = one-hot × E».
    4) Cuatro vectores horizontales de d casillas azules, rotulados «e₁ e₂ e₃ e₄ (d = 768)».
    5) Una pila verde rotulada «Transformer (N bloques)» que produce un vector «h (d)» marcado «último estado oculto».
    6) Una matriz naranja rotulada «W_U (V × d)  — unembedding», una caja «logits = h · W_Uᵀ  (V valores)» y una caja «softmax → p(siguiente token)» con un histograma de barras naranjas muy bajas salvo dos altas.
    Entre las matrices azul y naranja dibuja una línea punteada gris de doble flecha con el texto «weight tying: W_U = E (misma matriz)».
    Debajo del diagrama, una franja gris con la leyenda: «Cada fila de E es el vector de un token; V = tamaño del vocabulario, d = dimensión del modelo».
    Evita: texto ilegible, flechas ambiguas, más de seis bloques, elementos decorativos, números inventados distintos de los indicados.
    """,
    "Diagrama del recorrido token id → lookup en E → Transformer → unembedding W_U → softmax, con weight tying.",
    """
    Texto ─► Tokenizer ─► ids [1212, 8745, 5981, 22104]
                              │ lookup (one-hot × E)
                              ▼
        E (V×d)  fila 1212 ─► e1   fila 8745 ─► e2 ...  (solo esas filas)
                              ▼
                     Transformer (N bloques) ─► h (d)
                              ▼
        logits = h · W_Uᵀ   (V valores)   ◄── W_U (V×d)   [weight tying: W_U = E]
                              ▼
                      softmax ─► p(siguiente token)
    """,
)
nb.md(r"""
> 👀 **Qué debes observar.** La misma forma $V\times d$ aparece **dos veces**: una al entrar (como $E$, se *lee* una fila por token) y otra al salir (como $W_U$, se *usa entera* para puntuar los $V$ tokens). Con *weight tying* ambas son la misma matriz: ese reparto de papeles explica casi todo lo que sigue.
""")

nb.md(r"""
## 2. Anatomía: matriz de embeddings, unembedding y coste

Un LM causal (GPT-2, Llama, Gemma, Qwen…) hace, para una secuencia de ids $t_1,\dots,t_T$:

1. **Embedding de entrada:** $\mathbf{x}_i = E[t_i] \;(+\text{posición})$, con $E\in\mathbb{R}^{V\times d}$.
2. **Transformer:** produce estados ocultos $\mathbf{h}_i\in\mathbb{R}^d$ (el último, $\mathbf{h}_i$, resume el contexto $t_{\le i}$).
3. **Unembedding (cabeza del LM):** $\mathbf{z}_i = W_U\,\mathbf{h}_i + \mathbf{b}\in\mathbb{R}^V$, con $W_U\in\mathbb{R}^{V\times d}$ (los GPT suelen omitir el sesgo $\mathbf b$).
4. **Distribución:** $p(t_{i+1}=j\mid t_{\le i}) = \text{softmax}(\mathbf{z}_i)_j = \dfrac{e^{z_{ij}}}{\sum_{k=1}^{V} e^{z_{ik}}}$.

**Símbolos.** $V$ = tamaño del vocabulario; $d$ = dimensión del modelo; $E$ = matriz de embeddings de entrada; $W_U$ = matriz de unembedding (fila $\mathbf w_j$ = «vector de salida» del token $j$);
$\mathbf h_i$ = estado oculto final; $z_{ij}=\mathbf w_j\!\cdot\!\mathbf h_i + b_j$ = *logit* del token $j$.

Cada logit es un **producto escalar** entre el contexto y el vector de salida del token candidato (¡igual que el score de un *two-tower* de recsys!).

**Coste.** Parámetros de la capa: $V d$ (entrada) $+\,V d$ (salida, si no hay tying). FLOPs de la cabeza por token: $\approx 2\,V d$ en el forward (un matmul $V\times d$ por $\mathbf h$), y se paga **en cada posición**, no solo en la última.
""")

nb.code(r'''
from transformers import GPT2Config, AutoModelForCausalLM


def parametros(model_o_cfg):
    """(total de parámetros, V, d, tied) en 'meta device': no gasta memoria. parameters() ya deduplica pesos compartidos."""
    cfg = model_o_cfg if hasattr(model_o_cfg, "vocab_size") else None
    with torch.device("meta"):
        m = AutoModelForCausalLM.from_config(cfg)
    total = sum(p.numel() for p in m.parameters())
    V, d = cfg.vocab_size, cfg.hidden_size
    tied = bool(getattr(cfg, "tie_word_embeddings", False))
    n_emb = V * d * (1 if tied else 2)
    return dict(V=V, d=d, tied=tied, params_M=round(total / 1e6, 1), emb_M=round(n_emb / 1e6, 1), emb_pct=round(100 * n_emb / total, 1))


filas = {"GPT-2 small (config local)": parametros(GPT2Config()),
         "GPT-2 small SIN tying (config local)": parametros(GPT2Config(tie_word_embeddings=False))}
# Configs de modelos reales (solo descargan un JSON; si no hay acceso al hub se omiten sin romper nada)
for nombre in ["facebook/opt-125m", "EleutherAI/pythia-160m", "HuggingFaceTB/SmolLM2-135M", "Qwen/Qwen2.5-0.5B"]:
    try:
        from transformers import AutoConfig
        filas[nombre] = parametros(AutoConfig.from_pretrained(nombre))
    except Exception as e:
        print(f"   (sin acceso a la config de {nombre}: {type(e).__name__})")
print(f"{'modelo':40s} {'V':>7s} {'d':>5s} {'tied':>5s} {'params(M)':>10s} {'emb(M)':>8s} {'emb %':>6s}")
for k, r in filas.items():
    print(f"{k:40s} {r['V']:7d} {r['d']:5d} {str(r['tied']):>5s} {r['params_M']:10.1f} {r['emb_M']:8.1f} {r['emb_pct']:6.1f}")
''')

nb.md(r"""
> 👀 **Qué debes observar.** En GPT-2 small, $V d = 50\,257\times 768 = 38\,597\,376$ parámetros: **≈ 31 %** del modelo (124 439 808 en total) están en la tabla de embeddings. Sin tying serían **163 037 184** parámetros (+31 %).
> En modelos pequeños el peso relativo de $E$ es enorme; en modelos de decenas de miles de millones es una fracción pequeña. Eso cambia las decisiones de diseño (¿vale la pena atarlos? ¿ampliar el vocabulario?).
> Las filas de otros modelos solo aparecen si tu entorno llega al hub; **verifica el flag `tied` en el modelo concreto**: no todos los LMs lo atan.
""")

nb.md(r"""
## 3. Weight tying: una matriz, dos trabajos

**La idea (Press & Wolf, 2017; Inan et al., 2016).** Entrada y salida describen lo mismo —«qué es el token $j$»—, así que se fuerza $W_U = E$:

$$z_{ij} = \mathbf{e}_j\cdot \mathbf{h}_i .$$

**Qué se gana.** (1) Se eliminan $Vd$ parámetros (≈ 31 % de GPT-2 small). (2) Cada fila de $E$ recibe gradiente por **dos vías**: como entrada (solo si el token aparece en el contexto) y como salida (en *todas* las posiciones, porque el softmax puntúa los $V$ tokens). Los tokens raros se benefician de la vía de salida.
**Qué se paga.** Un solo vector debe servir para «ser leído» y para «ser predicho»; con $d$ pequeño o vocabularios grandes esos dos usos pueden entrar en conflicto. Algunos diseños **desacoplan** (RemBERT: Chung et al., 2021) o comparten con gradientes separados (DeBERTaV3: He et al., 2021). Gemma sí ata los embeddings (tabla de arquitectura de Gemma 2: «Tied embedding: yes»).

### Experimento: atado vs desatado en un mini-GPT-2
Entrenamos dos GPT-2 diminutos (2 capas, $d=64$) idénticos salvo `tie_word_embeddings`, sobre el corpus Políglota tokenizado con un BPE de 500 tokens entrenado aquí.
""")

nb.code(MINI_LM)

nb.code(r'''
# Tokenizer mini (entrenado en el corpus) y flujo de ids; 90 % entrenamiento / 10 % validación
tok_mini = entrena_tokenizer(textos, vocab_size=500)
data_mini = flujo_ids(tok_mini, textos)
n_val = len(data_mini) // 10
d_train, d_val = data_mini[:-n_val], data_mini[-n_val:]
print(f"vocab={len(tok_mini)} | tokens totales={len(data_mini):,} | tokens/palabra ≈ {len(data_mini) / sum(len(t.split()) for t in textos):.2f}")
STEPS = 300 if FAST_DEV_RUN else 1500

res = {}
for tie in (True, False):
    m = crea_mini_gpt(tok_mini, tie=tie)
    t0 = time.time(); hist = entrena_lm(m, d_train, steps=STEPS)
    res[tie] = dict(model=m, hist=hist, val=val_loss(m, d_val), n=sum(p.numel() for p in m.parameters()))
    print(f"tie={tie!s:5s} | parámetros={res[tie]['n']:,} | loss train={np.mean(hist[-20:]):.3f} | loss val={res[tie]['val']:.3f} | {time.time() - t0:.0f}s")
''')

nb.code(r'''
fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
suave = lambda h, k=15: np.convolve(h, np.ones(k) / k, mode="valid")
for tie, col, lab in ((True, PAL["azul"], "atado (tied)"), (False, PAL["naranja"], "desatado")):
    ax[0].plot(suave(res[tie]["hist"]), color=col, label=f"{lab} · {res[tie]['n'] / 1e3:.0f}k params")
ax[0].set(xlabel="paso de entrenamiento", ylabel="pérdida (entrenamiento, suavizada)", title="Curvas de entrenamiento"); ax[0].legend()
ax[1].bar(["atado", "desatado"], [res[True]["val"], res[False]["val"]], color=[PAL["azul"], PAL["naranja"]])
ax[1].set(ylabel="pérdida de validación", title="Validación (10 % retenido)")
for i, v in enumerate([res[True]["val"], res[False]["val"]]):
    ax[1].text(i, v, f"{v:.2f}", ha="center", va="bottom")
plt.tight_layout(); plt.show()
''')

nb.md(r"""
> 👀 **Qué debes observar.** El modelo atado tiene menos parámetros (la diferencia es exactamente $V d = 500\times 64 = 32\,000$). Fíjate en si su curva queda **por encima o por debajo** del desatado en *tu* ejecución: a esta escala diminuta y con 300 pasos la diferencia es pequeña y puede ir en cualquiera de los dos sentidos; Press & Wolf reportan mejoras de perplejidad con tying en LMs reales.
> Lección: *tying* es principalmente una decisión de **parámetros/memoria** con efecto en calidad dependiente de la escala; no es una ley.
""")

nb.md(r"""
### 📐 ¿Qué le hace el softmax a las filas que casi nunca son objetivo?

Para una posición con estado oculto $\mathbf h$, objetivo $y$ y probabilidades $p_j=\text{softmax}(\mathbf z)_j$, la pérdida es $\mathcal L=-\log p_y$. Como $z_j=\mathbf w_j\cdot\mathbf h$:

$$\frac{\partial \mathcal L}{\partial \mathbf w_j} = \big(p_j - \mathbb{1}[j=y]\big)\,\mathbf h .$$

Sumando sobre las posiciones $t$ del batch, para un token $j$ que **nunca** es objetivo: $\;\partial\mathcal L/\partial\mathbf w_j=\sum_t p_{tj}\,\mathbf h_t$ (todos los coeficientes son positivos).
Un paso de descenso hace $\mathbf w_j\leftarrow \mathbf w_j-\eta\sum_t p_{tj}\mathbf h_t$: **cada fila «huérfana» se mueve hacia $-\bar{\mathbf h}$**, la dirección media (negativa) de los estados ocultos. Todas las filas huérfanas acaban **casi paralelas** entre sí: el modelo aprende a no predecirlas bajando su logit, a costa de arruinar su geometría. Es la *representation degeneration* de Gao et al. (2019).

Con la vía de entrada ocurre algo distinto: una fila de $E$ solo recibe gradiente de entrada si su token aparece en el contexto.
Si además se usa **weight decay desacoplado** (AdamW), cada paso multiplica *todas* las filas por $(1-\eta\lambda)$ aunque no reciban gradiente, así que tras $n$ pasos una fila nunca vista queda en $\approx e^{-\eta\lambda n}$ de su norma inicial.
""")

nb.code(r'''
# Verificación experimental de las dos predicciones, en el modelo DESATADO (para separar entrada y salida)
cnt = Counter(d_train.tolist())
freq_mini = np.array([cnt.get(i, 0) for i in range(len(tok_mini))])
huerfanos = np.where(freq_mini == 0)[0]                      # tokens que NUNCA se ven en el entrenamiento
frecuentes = np.argsort(-freq_mini)[:100]
print(f"tokens nunca vistos: {len(huerfanos)} de {len(tok_mini)}")


def cos_pares(W, idx):
    X = F.normalize(W[idx].detach(), dim=-1)
    S = X @ X.T
    n = len(idx)
    return S[~torch.eye(n, dtype=bool)].numpy()


mdl = res[False]["model"]
W_out, W_in = mdl.get_output_embeddings().weight, mdl.get_input_embeddings().weight
c_out_h, c_out_f = cos_pares(W_out, huerfanos), cos_pares(W_out, frecuentes)
c_in_h = cos_pares(W_in, huerfanos)
print(f"coseno medio entre FILAS DE SALIDA: huérfanos={c_out_h.mean():+.3f} | frecuentes={c_out_f.mean():+.3f}")
print(f"coseno medio entre FILAS DE ENTRADA de huérfanos: {c_in_h.mean():+.3f}")

fig, ax = plt.subplots(figsize=(6.2, 3.4))
bins = np.linspace(-1, 1, 41)
ax.hist(c_out_f, bins=bins, alpha=.7, color=PAL["azul"], label="tokens frecuentes (salida)", density=True)
ax.hist(c_out_h, bins=bins, alpha=.7, color=PAL["naranja"], label="tokens nunca vistos (salida)", density=True)
ax.hist(c_in_h, bins=bins, alpha=.5, color=PAL["gris"], label="nunca vistos (entrada)", density=True)
ax.set(xlabel="coseno entre pares de filas", ylabel="densidad", title="Filas huérfanas del unembedding colapsan en una dirección"); ax.legend(fontsize=8)
plt.tight_layout(); plt.show()
''')

nb.md(r"""
> 👀 **Qué debes observar.** Las filas de **salida** de los tokens nunca vistos tienen coseno medio ≈ +1 entre sí (pico a la derecha): están todas en la misma dirección, tal como predice la derivación. Las de los tokens frecuentes se reparten alrededor de 0.
> Las filas de **entrada** de esos mismos tokens siguen siendo ruido aleatorio de la inicialización (coseno ≈ 0): nadie las tocó. En un modelo *atado* ambas vías comparten matriz, así que las filas huérfanas heredan el colapso de la salida (lo comprobamos abajo).
""")

nb.code(r'''
# Weight decay sobre filas de ENTRADA nunca vistas (modelo desatado) y qué pasa en un modelo ATADO
lr = 3e-3
rows = []
for wd in (0.0, 0.1, 1.0):
    m = crea_mini_gpt(tok_mini, tie=False)
    E0 = m.get_input_embeddings().weight.detach().clone()
    entrena_lm(m, d_train, steps=STEPS, lr=lr, wd=wd)
    E1 = m.get_input_embeddings().weight.detach()
    rows.append((wd, (E1[huerfanos].norm(dim=1) / E0[huerfanos].norm(dim=1)).mean().item(), math.exp(-lr * wd * STEPS)))
mt = crea_mini_gpt(tok_mini, tie=True)
Et0 = mt.get_input_embeddings().weight.detach().clone()
entrena_lm(mt, d_train, steps=STEPS, lr=lr)
Et1 = mt.get_input_embeddings().weight.detach()
ratio_tied = (Et1[huerfanos].norm(dim=1) / Et0[huerfanos].norm(dim=1)).mean().item()
cos_tied = cos_pares(Et1, huerfanos).mean()
for wd, medido, pred in rows:
    print(f"wd={wd:<4} | norma(final)/norma(inicial) de filas de entrada nunca vistas: medido={medido:.3f} · predicho exp(-lr·wd·pasos)={pred:.3f}")
print(f"MODELO ATADO (wd=0): norma final/inicial de filas huérfanas = {ratio_tied:.2f} · coseno medio entre ellas = {cos_tied:+.2f}")

fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.4))
w = np.arange(len(rows))
ax[0].bar(w - .18, [r[1] for r in rows], .36, color=PAL["azul"], label="medido")
ax[0].bar(w + .18, [r[2] for r in rows], .36, color=PAL["naranja"], label="predicho: exp(−η·λ·n)")
ax[0].set_xticks(w, [f"λ={r[0]}" for r in rows]); ax[0].set(ylabel="norma final / inicial", title="Entrada: solo decae el weight decay"); ax[0].legend()
ax[1].bar(["desatado\n(entrada)", "atado"], [1.0, ratio_tied], color=[PAL["gris"], PAL["verde"]])
ax[1].set(ylabel="norma final / inicial (filas nunca vistas)", title="Atado: el gradiente de salida las arrastra")
plt.tight_layout(); plt.show()
''')

nb.md(r"""
> 👀 **Qué debes observar.** (Izquierda) Sin *weight decay* las filas de entrada nunca vistas **no cambian** (cociente = 1.000): el valor medido coincide con la predicción $e^{-\eta\lambda n}$ para $\lambda>0$. (Derecha) En el modelo **atado** esas mismas filas **sí cambian** (su norma crece varias veces y quedan paralelas, coseno ≈ +1): la vía de salida las empuja.
> **Consecuencia práctica.** «Mirar la norma de la fila de entrada» detecta tokens sub-entrenados en modelos *desatados* con weight decay, pero **no** en modelos atados; por eso los detectores del módulo 05 usan la matriz de unembedding.
> Orden de magnitud real (cálculo, no medición): con $\eta=3\cdot10^{-4}$, $\lambda=0.1$ y $10^5$ pasos a LR constante, $e^{-\eta\lambda n}=e^{-3}\approx 0.05$; con un *schedule* que decae el efecto es menor.
""")

nb.gemini(
    "imagen", "M09-IMG-02", "Weight tying: una matriz, dos gradientes",
    "Muestra gráficamente que, con weight tying, la matriz recibe gradiente disperso por la vía de entrada y gradiente denso por la vía de salida, y que las filas huérfanas se arrastran hacia −h̄.",
    """
    Diagrama técnico limpio, fondo blanco, 16:9, estilo de infografía de ingeniería sin elementos decorativos. Paleta: azul #1F6FEB (vía de entrada), naranja #F28E2B (vía de salida), verde #2CA02C (filas bien entrenadas), gris #6B7280 (texto secundario).
    Centro: una matriz vertical grande rotulada «E = W_U  (V × d)» con 10 filas horizontales; las filas 2 y 7 están coloreadas en verde y rotuladas «token frecuente»; las filas 4, 5 y 9 están en gris y rotuladas «token casi nunca visto».
    Panel izquierdo (azul), título «Vía de entrada (dispersa)»: una flecha azul desde la caja «contexto: token 2, token 7» hacia SOLO las filas 2 y 7 con el texto «gradiente solo en filas usadas».
    Panel derecho (naranja), título «Vía de salida (densa)»: una caja «h (estado oculto)» con flechas naranjas hacia TODAS las filas, con grosor mayor en las filas frecuentes; sobre las filas grises, un pequeño vector naranja apuntando hacia la izquierda rotulado «−h̄ (todas se empujan en la misma dirección)».
    Parte inferior: dos mini-gráficos de esferas: izquierda «filas bien repartidas» (puntos dispersos), derecha «filas huérfanas colapsadas» (puntos agrupados en un casquete) con la leyenda «coseno medio ≈ +1».
    Fórmula centrada abajo: «∂L/∂w_j = (p_j − 1[j = y]) · h».
    Evita: texto ilegible, flechas ambiguas, añadir números inventados, decoración innecesaria.
    """,
    "Matriz E=W_U con gradiente disperso de entrada (filas usadas) y denso de salida (todas las filas), y colapso de filas huérfanas.",
    """
       entrada (azul)              E = W_U (V×d)               salida (naranja)
    contexto: tok2, tok7 ──►  fila 2  [verde, frecuente]  ◄──┐
                              fila 4  [gris, huérfana]  ◄─── h (todas las filas)
                              fila 7  [verde, frecuente]  ◄──┤   ∂L/∂w_j = (p_j − 1[j=y]) h
                              fila 9  [gris, huérfana]  ◄───┘   huérfanas → dirección −h̄
    """,
)
nb.md(r"""
> 👀 **Qué debes observar.** La vía azul toca pocas filas; la naranja, todas. Las filas grises solo reciben la naranja, y siempre empuja igual: de ahí el colapso medido arriba.
""")
nb.save(LESSON)
