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


def entrena_lm(model, data, steps=600, lr=1e-3, wd=0.0, B=16, T=48, seed=SEED):
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

<details><summary><b>4.</b> (Módulo 04, Cálculo) Pasas de un vocabulario de 32 000 a uno de 128 000 tokens con $d = 2048$. ¿Cuántos parámetros añade la matriz de entrada? ¿Y si la de salida no está atada?</summary>

$(128\,000 - 32\,000)\times 2048 \approx 197$ M por matriz; **≈ 393 M** con entrada y salida desatadas. En el módulo 04 lo viste como «presupuesto del vocabulario»; en la sección 2 verás que esas filas son una fracción grande de un modelo pequeño y en la 5 por qué la de salida, además, cuesta cómputo en cada paso.
</details>

<details><summary><b>5.</b> (Módulo 02, Transferencia) BPE fusiona el par con más frecuencia. Si quisieras añadir 32 palabras de dominio a un vocabulario ya entrenado, ¿qué criterio voraz análogo usarías para elegirlas?</summary>

Frecuencia × tokens ahorrados por aparición, $n_w(\text{piezas}(w) - 1)$: el mismo razonamiento de compresión que un merge, pero a nivel de palabra completa. Es exactamente el criterio del proyecto (TODO 3).
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
data_mini = flujo_ids(tok_mini, random.Random(SEED).sample(textos, len(textos)))  # mezclado: val = mezcla de idiomas
n_val = len(data_mini) // 10
d_train, d_val = data_mini[:-n_val], data_mini[-n_val:]
print(f"vocab={len(tok_mini)} | tokens totales={len(data_mini):,} | tokens/palabra ≈ {len(data_mini) / sum(len(t.split()) for t in textos):.2f}")
STEPS = 600 if FAST_DEV_RUN else 3000

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
> 👀 **Qué debes observar.** El modelo atado tiene menos parámetros (la diferencia es exactamente $V d = 500\times 64 = 32\,000$). Fíjate en si su curva queda **por encima o por debajo** del desatado en *tu* ejecución: a esta escala diminuta y con 600 pasos la diferencia es pequeña y puede ir en cualquiera de los dos sentidos; Press & Wolf reportan mejoras de perplejidad con tying en LMs reales.
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
lr = 1e-3
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

nb.md(r"""
## 4. Geometría de la matriz de embeddings de un LM

Ahora miramos un LM «de verdad». La celda siguiente intenta cargar **GPT-2 small** (124M, atado, $V=50\,257$, $d=768$) desde el hub de Hugging Face.
Si no hay acceso (proxy, sin red), usa como **fallback documentado** el mini-GPT-2 atado que acabas de entrenar con su tokenizer de 500 tokens: todas las celdas funcionan igual, pero las conclusiones cuantitativas sobre «un LM real» requieren GPT-2.
""")

nb.code(r'''
def carga_lm():
    """GPT-2 small si el hub es accesible; si no, el mini-GPT-2 atado de la sección 3 (fallback)."""
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        tok_ = AutoTokenizer.from_pretrained("gpt2")
        lm_ = AutoModelForCausalLM.from_pretrained("gpt2").eval()
        return lm_, tok_, "GPT-2 small (real)"
    except Exception as e:
        print(f"⚠️  GPT-2 no disponible ({type(e).__name__}): uso el mini-GPT-2 atado entrenado arriba (fallback).")
        return res[True]["model"], tok_mini, "mini-GPT-2 (fallback)"


lm, tok, lm_name = carga_lm()
E = lm.get_input_embeddings().weight.detach().float().cpu()
TIED = lm.get_input_embeddings().weight is lm.get_output_embeddings().weight
V, d = E.shape
print(f"{lm_name}: V={V}, d={d}, tied={TIED}")

# Frecuencia de cada token en el corpus Políglota (un PROXY de su frecuencia en el pre-entrenamiento, no la real)
ids_corpus = [i for t in textos for i in tok(t)["input_ids"]]
cnt_lm = Counter(ids_corpus)
freq = np.array([cnt_lm.get(i, 0) for i in range(V)])
norms = E.norm(dim=1).numpy()
print(f"tokens del corpus: {len(ids_corpus):,} | tokens del vocabulario que aparecen: {(freq > 0).sum():,} ({100 * (freq > 0).mean():.1f} %)")
''')

nb.code(r'''
from scipy.stats import spearmanr

vis = freq > 0
rho = spearmanr(norms[vis], np.log1p(freq[vis])).statistic
fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
ax[0].scatter(np.log10(1 + freq[vis]), norms[vis], s=5, alpha=.4, color=PAL["azul"], label="aparece en el corpus")
ax[0].scatter(np.zeros((~vis).sum()) - 0.15 + 0.1 * np.random.rand((~vis).sum()), norms[~vis], s=5, alpha=.3, color=PAL["naranja"], label="no aparece (x≈0)")
ax[0].set(xlabel="log10(1 + frecuencia en el corpus)", ylabel="‖E[token]‖", title=f"Norma vs frecuencia (Spearman ρ = {rho:+.2f}, tokens vistos)")
ax[0].legend(fontsize=8)
ax[1].hist(norms, bins=60, color=PAL["gris"])
ax[1].set(xlabel="‖E[token]‖", ylabel="nº de tokens", title=f"Distribución de normas · {lm_name}")
plt.tight_layout(); plt.show()
print(f"norma media={norms.mean():.3f} | p1={np.percentile(norms, 1):.3f} | p99={np.percentile(norms, 99):.3f}")
''')

nb.md(r"""
> 👀 **Qué debes observar.** La norma de una fila **no es neutra**: está correlacionada con la frecuencia del token (mira el signo y la magnitud de ρ en *tu* modelo; Kobayashi et al., 2023, analizan cómo los LMs codifican la frecuencia en la cabeza de predicción).
> Fíjate en los **extremos** de la distribución de normas: las colas suelen ser tokens raros o especiales. En el modelo de fallback, los tokens que no aparecen en el corpus son justo los que nunca vio al entrenar, así que su comportamiento refleja lo derivado en la sección 3. En GPT-2 la frecuencia del corpus Políglota es solo un *proxy* de la de WebText.
""")

nb.md(r"""
### Anisotropía y espectro
Un conjunto de vectores es **isótropo** si no tiene direcciones privilegiadas (pares aleatorios con coseno ≈ 0). Los embeddings de LMs suelen ser **anisótropos**: una media común grande y pocas direcciones dominantes (Gao et al., 2019; Ethayarajh, 2019, para las representaciones contextuales del módulo 10).
Dos medidas baratas:
- **Coseno medio entre pares aleatorios** (0 = isótropo).
- **Rango efectivo** por *participation ratio*: si $\lambda_k=\sigma_k^2$ son los autovalores de la covarianza, $\;\text{PR}=\dfrac{(\sum_k\lambda_k)^2}{\sum_k\lambda_k^2}\in[1,d]$ (1 = toda la varianza en una dirección; $d$ = varianza repartida por igual).
""")

nb.code(r'''
def anisotropia(X, n=4000, seed=SEED):
    g = torch.Generator().manual_seed(seed)
    i, j = torch.randint(0, len(X), (n,), generator=g), torch.randint(0, len(X), (n,), generator=g)
    Xn = F.normalize(X, dim=-1)
    return (Xn[i] * Xn[j]).sum(-1).mean().item()


def espectro(X):
    Xc = X - X.mean(0)
    s = torch.linalg.svdvals(Xc)
    lam = s ** 2
    return lam / lam.sum(), ((lam.sum() ** 2) / (lam ** 2).sum()).item()


sub = torch.tensor(np.where(vis)[0])                   # tokens que aparecen en el corpus
an_all, an_vis = anisotropia(E), anisotropia(E[sub])
an_cent = anisotropia(E - E.mean(0))
lam, pr = espectro(E)
print(f"coseno medio pares aleatorios: todos={an_all:+.3f} | vistos={an_vis:+.3f} | tras centrar={an_cent:+.3f}")
print(f"rango efectivo (participation ratio) = {pr:.1f} de d = {d}")
print(f"‖media‖ / norma media de las filas = {E.mean(0).norm().item() / E.norm(dim=1).mean().item():.3f}")

fig, ax = plt.subplots(1, 2, figsize=(11, 3.4))
ax[0].semilogy(lam.numpy()[: min(d, 200)], color=PAL["azul"])
ax[0].set(xlabel="componente principal k", ylabel="fracción de varianza (log)", title="Espectro de E centrada")
ax[1].plot(np.cumsum(lam.numpy()), color=PAL["verde"])
ax[1].axhline(.9, ls="--", color=PAL["gris"]); ax[1].set(xlabel="nº de componentes", ylabel="varianza acumulada", title=f"PR = {pr:.1f} / d = {d}")
plt.tight_layout(); plt.show()
''')

nb.md(r"""
> 👀 **Qué debes observar.** Si el coseno medio es claramente > 0 y **cae a ≈ 0 al centrar**, la anisotropía se debe a una **media común** (una dirección compartida por todos los tokens). El espectro muestra cuántas direcciones concentran la varianza: un PR mucho menor que $d$ indica que la tabla usa pocas dimensiones «de verdad».
> Esto importa para retrieval: si usaras directamente filas de $E$ (o estados ocultos) como embeddings, el coseno estaría dominado por esa media; en el módulo 10 veremos centrado, *whitening* y por qué los embedders entrenados contrastivamente lo corrigen.
""")

nb.code(r'''
def vecinos(token_id, k=6, X=E):
    Xn = F.normalize(X, dim=-1)
    s = Xn @ Xn[token_id]
    s[token_id] = -2
    top = s.topk(k)
    return [(tok.convert_ids_to_tokens(int(i)), round(v.item(), 2)) for v, i in zip(top.values, top.indices)]


# Sondas: los tokens de palabra más frecuentes del corpus (con espacio delante y ≥ 4 letras), más algunos dígitos
cand = [i for i, _ in cnt_lm.most_common(3000) if re.fullmatch(r"Ġ[a-zA-Záéíóúñ]{4,}", tok.convert_ids_to_tokens(i) or "")]
sondas = cand[:5] + [i for i in (tok.convert_tokens_to_ids(x) for x in ["1", "2", "8"]) if i is not None and i != tok.unk_token_id][:2]
for i in sondas:
    print(f"{tok.convert_ids_to_tokens(i)!r:16} → {vecinos(i)}")
''')

nb.md(r"""
> 👀 **Qué debes observar.** Los vecinos por coseno en $E$ mezclan **semántica** (sinónimos, misma categoría), **forma** (misma palabra con/sin espacio `Ġ` o mayúscula) y **frecuencia** (tokens de frecuencia similar se agrupan). Es una tabla *para el LM*, no un embedding de búsqueda: por eso Políglota no usará filas de $E$ como vectores de documentos.
""")

nb.code(r'''
# Estructura lineal: proyección PCA 2D de grupos de tokens definidos por su forma
grupos = {
    "dígitos/números": r"Ġ?\d+",
    "Mayúscula inicial": r"Ġ[A-ZÁÉÍÓÚ][a-záéíóú]{2,}",
    "minúsculas con espacio": r"Ġ[a-záéíóúñ]{3,}",
    "fragmento sin espacio": r"[a-záéíóúñ]{2,}",
    "puntuación": r"Ġ?[\.,;:\(\)\[\]\{\}\"'`=]+",
}
ids_vis = [i for i, _ in cnt_lm.most_common(2500)]
etiq = {}
for i in ids_vis:
    t = tok.convert_ids_to_tokens(i) or ""
    for g, pat in grupos.items():
        if re.fullmatch(pat, t):
            etiq[i] = g
            break
sel = torch.tensor(list(etiq))
Xs = E[sel] - E[sel].mean(0)
U_, S_, Vh = torch.linalg.svd(Xs, full_matrices=False)
P2 = (Xs @ Vh[:2].T).numpy()
cols = [PAL["azul"], PAL["naranja"], PAL["verde"], PAL["gris"], "#9467BD"]
fig, ax = plt.subplots(figsize=(6.5, 4.6))
for c, g in zip(cols, grupos):
    m = np.array([etiq[int(i)] == g for i in sel])
    if m.sum():
        ax.scatter(P2[m, 0], P2[m, 1], s=9, alpha=.6, color=c, label=f"{g} ({m.sum()})")
ax.set(xlabel="PC1", ylabel="PC2", title=f"PCA de E por tipo de token · {lm_name}"); ax.legend(fontsize=8)
plt.tight_layout(); plt.show()
''')

nb.md(r"""
> 👀 **Qué debes observar.** Las dos primeras componentes principales separan tipos de token por **forma** (con/sin espacio inicial, números, puntuación) antes que por significado: la información «superficial» del tokenizer es una de las direcciones de mayor varianza de $E$. Con GPT-2 real, los números suelen formar su propia región (prueba a colorear los años 1900–2020 por su valor: aparece una curva ordenada).
""")

nb.md(r"""
## 5. El cuello de botella softmax y el coste de la cabeza

### 📐 Rango
Apila los logits de $N$ contextos en una matriz $Z = H W_U^\top\in\mathbb{R}^{N\times V}$ con $H\in\mathbb{R}^{N\times d}$. Entonces $\operatorname{rank}(Z)\le d$, y $\log P = Z - \log\!\big(\sum_k e^{Z_{:,k}}\big)\mathbf 1^\top$ tiene rango $\le d+1$.
Si la matriz «verdadera» de log-probabilidades del lenguaje $\log P^*$ tiene rango mucho mayor que $d$, **ningún** entrenamiento puede representarla exactamente: es el **cuello de botella softmax** (Yang et al., 2018). Godey et al. (2024) lo relacionan con la saturación de LMs pequeños: modelos con menos de ~1000 dimensiones ocultas tienden a degenerar al final del pre-entrenamiento.

### 🧪 Experimento
Generamos una matriz objetivo $P^*$ ($N=256$ contextos × $V=128$ tokens) de **rango completo** y ajustamos $\text{softmax}(HW^\top)$ con $d$ creciente minimizando $\mathrm{KL}(P^*\,\|\,P)$.
""")

nb.code(r'''
torch.manual_seed(SEED)
N, Vt, r = 256, 128, 8
A = 4 * torch.tanh(torch.randn(N, r) @ torch.randn(Vt, r).T / r ** 0.5 * 2.0)   # bajo rango + no linealidad -> rango alto
P_star = torch.softmax(A, -1); logP_star = torch.log(P_star)
print("rango de log P* =", torch.linalg.matrix_rank(logP_star).item(), "de", Vt)


def ajusta(dim, steps=800):
    torch.manual_seed(0)
    H = torch.nn.Parameter(torch.randn(N, dim) * .3); W = torch.nn.Parameter(torch.randn(Vt, dim) * .3)
    opt = torch.optim.Adam([H, W], lr=.05)
    for _ in range(steps):
        kl = (P_star * (logP_star - torch.log_softmax(H @ W.T, -1))).sum(-1).mean()
        opt.zero_grad(); kl.backward(); opt.step()
    return kl.item()


dims = [1, 2, 4, 8, 16, 32, 64, 128]
kls = [ajusta(k) for k in dims]
fig, ax = plt.subplots(figsize=(6, 3.4))
ax.semilogy(dims, kls, "o-", color=PAL["naranja"])
ax.set_xscale("log", base=2); ax.set(xlabel="dimensión d del modelo", ylabel="KL residual (nats, log)", title="Cuello de botella softmax: error vs d")
plt.tight_layout(); plt.show()
print({k: round(v, 4) for k, v in zip(dims, kls)})
''')

nb.md(r"""
> 👀 **Qué debes observar.** El KL residual cae con $d$ y solo se acerca a 0 cuando $d$ se aproxima al rango de $\log P^*$. Con $d$ pequeño, el modelo **no puede** representar la distribución por bien que se optimice: el error es estructural, no de optimización. En LMs reales $V\gg d$ (50 257 vs 768 en GPT-2), así que la pregunta relevante es cuánto rango necesita realmente el lenguaje en cada contexto.

### Coste de la cabeza y la *cross-entropy* por trozos
Los logits de un batch ocupan $B\cdot T\cdot V$ números: con $B=8$, $T=2048$, $V=128\,000$ en fp32 son $8\cdot2048\cdot128\,000\cdot4\ \text{bytes}\approx 8.4$ GB **solo para los logits** (más su gradiente). Por eso las librerías de entrenamiento calculan la pérdida **por trozos** o fusionan cabeza + pérdida en un kernel sin materializar los logits completos (p. ej. `FusedLinearCrossEntropy` de Liger Kernel; Hsu et al., 2024). La celda comprueba que la versión por trozos es **exactamente** la misma pérdida y el mismo gradiente.
""")

nb.code(r'''
def ce_por_trozos(h, W, y, chunk=256):
    """Cross-entropy de logits h @ W.T calculada por trozos de filas (nunca hay más de chunk×V logits en memoria a la vez).
    Nota: con autograd estándar los trozos se guardan para el backward; los kernels fusionados recalculan en el backward."""
    total = h.new_zeros(())
    for s in range(0, h.shape[0], chunk):
        total = total + F.cross_entropy(h[s:s + chunk] @ W.T, y[s:s + chunk], reduction="sum")
    return total / h.shape[0]


g = torch.Generator().manual_seed(SEED)
h = torch.randn(1024, 64, generator=g, requires_grad=True); W = torch.randn(5000, 64, generator=g, requires_grad=True)
y = torch.randint(0, 5000, (1024,), generator=g)
l_full = F.cross_entropy(h @ W.T, y); gW_full, = torch.autograd.grad(l_full, W)
l_chunk = ce_por_trozos(h, W, y); gW_chunk, = torch.autograd.grad(l_chunk, W)
print(f"pérdida completa={l_full.item():.6f} | por trozos={l_chunk.item():.6f} | max|Δgrad|={(gW_full - gW_chunk).abs().max().item():.2e}")
mem = lambda B, T, Vv, bytes_=4: B * T * Vv * bytes_ / 1e9
print(f"logits fp32 de B=8, T=2048, V=128k: {mem(8, 2048, 128_000):.1f} GB · FLOPs de la cabeza por token ≈ 2·V·d")
''')

nb.md(r"""
## 6. Extender el vocabulario con tokens de dominio

**Escenario Políglota.** El corpus técnico tiene términos (`configuración`, `rendimiento`, `serialización`, nombres de funciones…) que el tokenizer parte en muchos trozos: más tokens = más coste y contexto desperdiciado (módulo 04).
Añadir tokens es barato en el tokenizer (`tokenizer.add_tokens`) y en el modelo (`model.resize_token_embeddings`), pero **las filas nuevas no saben nada**. ¿Cómo inicializarlas?

| Inicialización | Fila nueva $\mathbf e_{\text{new}}$ | Idea |
|---|---|---|
| `random` | $\mathcal N(0, 0.02^2)$ | lo que hace un `nn.Embedding` recién creado (valor de `initializer_range` de GPT-2) |
| `mean` | $\bar{\mathbf e} = \frac1V\sum_j \mathbf e_j$ | Hewitt (2021): mantiene cerca la distribución de los tokens viejos; `resize_token_embeddings(mean_resizing=True)` (por defecto en transformers recientes) muestrea de $\mathcal N(\bar{\mathbf e}, 10^{-9}\Sigma)$, en la práctica $\approx\bar{\mathbf e}$ |
| `subtoken` | $\frac{1}{|S|}\sum_{s\in S}\mathbf e_s$, con $S$ = piezas en que el tokenizer **viejo** partía la palabra | reutiliza lo que el modelo ya sabe de esa secuencia |

✍️ **Ejemplo a mano ($d = 2$).** El tokenizer viejo parte « serialización» en [« serial», «ización»], con filas $(0.8, 0.2)$ y $(0.2, 0.6)$; la media de **todo** el vocabulario es $\bar{\mathbf e} = (0.1, 0.1)$. `subtoken` da $\tfrac12[(0.8,0.2)+(0.2,0.6)] = (0.5, 0.4)$: cerca de lo que el modelo ya «sabe» de la palabra troceada. `mean` da $(0.1, 0.1)$: un token genérico, inofensivo pero sin contenido. `random` da un punto cualquiera de norma ≈ $0.02\sqrt d$, lejos de todo. Es el *cold start* de un ítem nuevo en recsys: inicializarlo con la media de sus atributos (aquí, sus piezas) frente a la media del catálogo frente a ruido. Ojo: en la **salida**, una fila `mean`/`subtoken` hace que el modelo prediga el token nuevo donde predecía sus piezas: de ahí la «masa filtrada» que medimos.

**Cómo medirlo bien.** Al cambiar el tokenizer cambia el número de tokens, así que la pérdida *por token* no es comparable. Usamos **bits por byte**: $\text{bpb} = \dfrac{\sum_t -\log_2 p(t)}{\#\text{bytes del texto}}$ (módulos 04 y 07). Y medimos la **masa filtrada**: probabilidad media que el modelo asigna a los tokens nuevos en posiciones donde el siguiente token **no** es nuevo.

> 🔁 El módulo 07 trató el caso difícil (cambiar *todo* el tokenizer: FOCUS, WECHSEL, ZeTT). Aquí solo **añadimos** filas y medimos qué inicialización pierde menos; es la operación más común en producción (tokens especiales, términos de dominio).
""")

nb.code(r'''
from tokenizers import AddedToken


def selecciona_terminos(tok, textos, k=24, min_len=6):
    """Palabras frecuentes que el tokenizer parte en muchos trozos: ahorro = frecuencia × (nº de piezas − 1)."""
    pal = Counter(w for t in textos for w in re.findall(r"[^\W\d_]{%d,}" % min_len, t))
    sc = [(w, n, len(tok(" " + w, add_special_tokens=False)["input_ids"])) for w, n in pal.items()]
    sc = sorted(sc, key=lambda x: -x[1] * (x[2] - 1))[:k]
    return [" " + w for w, _, _ in sc], sc


def redimensiona(model, n):
    try:
        model.resize_token_embeddings(n, mean_resizing=False)
    except TypeError:                                   # versiones antiguas de transformers
        model.resize_token_embeddings(n)


def extiende(model, tok, nuevos, init):
    tok2, m2 = copy.deepcopy(tok), copy.deepcopy(model)
    old_V = len(tok2)
    piezas = [tok2(w, add_special_tokens=False)["input_ids"] for w in nuevos]   # con el tokenizer VIEJO
    tok2.add_tokens([AddedToken(w, normalized=False) for w in nuevos])
    if init == "hf_default":
        m2.resize_token_embeddings(len(tok2))          # mean_resizing=True en versiones recientes
        return m2, tok2, old_V
    redimensiona(m2, len(tok2))
    mats = {id(m2.get_input_embeddings().weight): m2.get_input_embeddings().weight,
            id(m2.get_output_embeddings().weight): m2.get_output_embeddings().weight}   # 1 matriz si está atado
    with torch.no_grad():
        for W in mats.values():
            old = W[:old_V]
            for j, p in enumerate(piezas):
                if init == "random":
                    W[old_V + j] = torch.randn(W.shape[1]) * 0.02
                elif init == "mean":
                    W[old_V + j] = old.mean(0)
                elif init == "subtoken":
                    W[old_V + j] = old[p].mean(0)
    return m2, tok2, old_V
''')

nb.code(r'''
@torch.no_grad()
def bpb_y_fuga(model, tok, textos, old_V, T=64):
    """bits por byte del texto y masa de probabilidad media puesta en tokens nuevos (ids ≥ old_V) donde el objetivo es viejo."""
    nll, nbytes, fuga, npos = 0.0, 0, 0.0, 0
    model.eval()
    for t in textos:
        ids = tok(t)["input_ids"][:T]
        if len(ids) < 2:
            continue
        x = torch.tensor([ids])
        logp = torch.log_softmax(model(input_ids=x).logits[0, :-1].float(), -1)
        y = x[0, 1:]
        nll += -logp.gather(1, y[:, None]).sum().item()
        nbytes += len(tok.decode(ids[1:]).encode("utf-8"))
        viejo = y < old_V
        if logp.shape[1] > old_V and viejo.any():
            fuga += logp[viejo][:, old_V:].exp().sum(-1).sum().item(); npos += int(viejo.sum())
    return nll / nbytes / math.log(2), (fuga / npos if npos else 0.0)


def ajusta_filas_nuevas(model, tok2, old_V, textos, steps=100, lr=1e-2, B=8, T=48):
    """Entrena SOLO las filas nuevas (máscara de gradiente); comprueba que las viejas no cambian."""
    for p in model.parameters():
        p.requires_grad_(False)
    W = model.get_input_embeddings().weight                  # si no está atado, añade también get_output_embeddings()
    W.requires_grad_(True)
    mask = torch.zeros_like(W); mask[old_V:] = 1
    hook = W.register_hook(lambda g_: g_ * mask)
    antes = W[:old_V].detach().clone()
    hist = entrena_lm(model, flujo_ids(tok2, textos), steps=steps, lr=lr, wd=0.0, B=B, T=T)
    hook.remove()
    assert torch.equal(antes, W[:old_V].detach()), "¡las filas viejas cambiaron!"
    return hist
''')

nb.code(r'''
prosa = [t for t, dd in zip(textos, docs) if dd["lang"] != "code"]
held = prosa[::7][:40]                                   # evaluación
ft_txt = [t for i, t in enumerate(prosa) if i % 7 != 0]  # ajuste (disjunto)
nuevos, tabla = selecciona_terminos(tok, ft_txt, k=24)
print("términos (palabra, frecuencia, piezas):", tabla[:8], "...")
FT_STEPS = 100 if V < 5000 else (25 if device == "cpu" and FAST_DEV_RUN else 200)
fert = lambda tk: np.mean([len(tk(t)["input_ids"]) / len(t.split()) for t in held])
base_bpb, _ = bpb_y_fuga(lm, tok, held, old_V=V)
print(f"BASE: bpb={base_bpb:.3f} | tokens/palabra={fert(tok):.2f}")
resultados = {}
for init in ("random", "mean", "subtoken", "hf_default"):
    m2, tok2, old_V = extiende(lm, tok, nuevos, init)
    b0, f0 = bpb_y_fuga(m2, tok2, held, old_V)
    hist = ajusta_filas_nuevas(m2, tok2, old_V, ft_txt, steps=FT_STEPS)
    b1, f1 = bpb_y_fuga(m2, tok2, held, old_V)
    resultados[init] = dict(bpb0=b0, fuga0=f0, bpb1=b1, fuga1=f1, hist=hist, fert=fert(tok2))
    print(f"{init:10s} | bpb antes={b0:.3f} → tras {FT_STEPS} pasos={b1:.3f} | fuga antes={f0:.4f} | tokens/palabra={resultados[init]['fert']:.2f}")
''')

nb.code(r'''
fig, ax = plt.subplots(1, 2, figsize=(11.5, 3.7))
cols = {"random": PAL["gris"], "mean": PAL["naranja"], "subtoken": PAL["verde"], "hf_default": PAL["azul"]}
for k, r_ in resultados.items():
    ax[0].plot(np.convolve(r_["hist"], np.ones(5) / 5, mode="valid"), color=cols[k], label=k)
ax[0].set(xlabel="paso (solo filas nuevas entrenables)", ylabel="pérdida por token", title="Ajuste de las filas nuevas"); ax[0].legend()
x = np.arange(len(resultados))
ax[1].bar(x - .2, [r_["bpb0"] for r_ in resultados.values()], .4, color=PAL["naranja"], label="antes de ajustar")
ax[1].bar(x + .2, [r_["bpb1"] for r_ in resultados.values()], .4, color=PAL["azul"], label="después")
ax[1].axhline(base_bpb, ls="--", color="k", lw=1, label=f"modelo original ({base_bpb:.3f})")
ax[1].set_xticks(x, list(resultados)); ax[1].set(ylabel="bits por byte (↓ mejor)", title="Calidad medida en texto retenido"); ax[1].legend(fontsize=8)
plt.tight_layout(); plt.show()
''')

nb.md(r"""
> 👀 **Qué debes observar.** (1) **Antes de ajustar**, `subtoken` es la que menos pierde (en la ejecución de referencia con el mini-GPT-2 de fallback: bpb 2.339 frente a 2.346 `random` y 2.352 `mean`; el modelo original daba 2.342): reutiliza lo que el modelo ya sabía de la palabra troceada. `mean` y `hf_default` dan lo mismo porque ambas ponen **la misma fila** a todos los tokens nuevos.
> (2) Tras 100 pasos entrenando **solo** las filas nuevas, todas convergen (≈ 2.31 bpb, algo mejor que el original) **con ≈ 7 % menos tokens por palabra**: menos coste por documento sin perder calidad. La inicialización importa sobre todo **al principio** y con pocos datos de ajuste, justo el caso de los términos raros de dominio. Con GPT-2 real las diferencias entre inicializaciones suelen ser mayores, porque las piezas tienen significado previo: mídelo.
> (3) `subtoken` filtra **más** masa de probabilidad a los tokens nuevos (≈ 0.02 frente a ≈ 0.002 de `mean`): hereda el logit de sus piezas y «compite» con ellas. Es el *trade-off* que motiva la inicialización por media de Hewitt (no perturbar la distribución sobre los tokens viejos).
""")

nb.gemini(
    "imagen", "M09-IMG-03", "Extender el vocabulario: filas nuevas y su inicialización",
    "Resume el procedimiento de extensión de vocabulario: palabra partida en trozos → token nuevo → fila nueva en E inicializada por media de sub-tokens, con las alternativas y cómo se mide (bpb, fuga).",
    """
    Diagrama técnico limpio, fondo blanco, 16:9, sin elementos decorativos. Paleta: azul #1F6FEB (filas existentes), verde #2CA02C (fila nueva bien inicializada), naranja #F28E2B (alternativas), gris #6B7280 (texto secundario). Tipografía sans-serif.
    Arriba a la izquierda: la palabra «serialización» y debajo cuatro fichas azules con el texto «Ġser», «ializ», «ac», «ión» y la etiqueta «tokenizer original: 4 tokens».
    Flecha hacia la derecha con el texto «add_tokens(" serialización")» hasta una única ficha verde «Ġserialización» con la etiqueta «tokenizer extendido: 1 token».
    Centro: una matriz vertical azul «E (V × d)» con 8 filas; debajo se añade una fila verde nueva rotulada «fila V (nueva)». Desde las cuatro filas azules de las piezas salen flechas finas que convergen en la fila verde con el rótulo «media de sub-tokens».
    A la derecha, tres recuadros naranjas apilados con títulos: «random: N(0, 0.02²)», «mean: media de todas las filas (todas las filas nuevas idénticas)», «subtoken: media de las piezas (recomendada)».
    Abajo, una franja con dos indicadores: «Medir con bits por byte (no pérdida por token)» y «Masa filtrada: probabilidad puesta en tokens nuevos donde no tocan».
    Evita: texto ilegible, flechas ambiguas, números inventados, iconos decorativos.
    """,
    "Extensión de vocabulario: palabra en 4 piezas → 1 token nuevo cuya fila se inicializa con la media de las piezas; alternativas random/mean; métricas bpb y masa filtrada.",
    """
    "serialización" ─ tokenizer original ─► [Ġser][ializ][ac][ión]   (4 tokens)
                     add_tokens          ─► [Ġserialización]          (1 token)
    E (V×d) + fila nueva:  e_new = media(e_Ġser, e_ializ, e_ac, e_ión)   ← subtoken
       alternativas: random N(0,0.02²) · mean (todas idénticas)
    medir: bits por byte · masa filtrada en tokens nuevos
    """,
)
nb.md(r"""
> 👀 **Qué debes observar.** La fila nueva no parte de cero: hereda la «media» de cómo el modelo representaba la palabra troceada. Las métricas del pie son las que usaste arriba, no la pérdida por token.
""")

nb.md(r"""
## 7. 📚 Caja histórica: word2vec, GloVe y PMI (solo contexto)

Antes de los Transformers, la tabla $E$ **era** el producto: embeddings *estáticos* (un vector por palabra, sin contexto).
- **word2vec** (Mikolov et al., 2013a; 2013b): skip-gram con *negative sampling* (SGNS) entrena dos tablas (palabra y contexto) para que $\mathbf w\cdot\mathbf c$ sea alto en pares que co-ocurren y bajo en pares aleatorios.
- **GloVe** (Pennington, Socher & Manning, 2014): ajusta $\mathbf w_i\cdot\mathbf c_j + b_i + \tilde b_j \approx \log X_{ij}$ sobre la matriz de co-ocurrencias $X$.
- **Lectura matricial** (Levy & Goldberg, 2014): en el óptimo, SGNS factoriza implícitamente la matriz de *PMI* desplazada: $\mathbf w_i\cdot\mathbf c_j = \mathrm{PMI}(i,j) - \log k$, con $\mathrm{PMI}(i,j)=\log\frac{p(i,j)}{p(i)p(j)}$ y $k$ el nº de negativos.

**El puente con hoy.** (1) Un LM con tying también factoriza: $\log p(j\mid\text{contexto})\approx \mathbf e_j\cdot\mathbf h$ — el «contexto» ya no es una palabra vecina sino el estado oculto de todo el prefijo. (2) El *negative sampling* de word2vec es el antepasado directo de los **negativos** del aprendizaje contrastivo (módulo 11).
(3) Los embeddings estáticos no distinguen «banco (asiento)» de «banco (entidad)»: esa es la motivación de los embeddings **contextuales** del módulo 10. Este curso no los implementa: hoy se usan como *baselines* o en dispositivos muy restringidos.
""")

nb.md(r"""
## 8. Mapa de madurez (a oct-2026)

| Técnica | Madurez | Quién la usa (verificable) | Fuente |
|---|---|---|---|
| Lookup $E$ + cabeza lineal + softmax | 🟢 sólido | Todos los LMs decoder (GPT-2, Gemma, …) | Radford et al. 2019; Gemma Team 2024 |
| Weight tying | 🟢 sólido (no universal) | GPT-2; Gemma («share embeddings across inputs and outputs»); Gemma 2 («Tied embedding: yes»). La config por defecto de `LlamaConfig` en transformers es `tie_word_embeddings=False`: compruébalo por modelo | Press & Wolf 2017; Inan et al. 2016; Gemma Team 2024a/b |
| Embeddings desacoplados / compartidos con gradiente separado | 🟡 emergente | RemBERT; DeBERTaV3 (GDES) | Chung et al. 2021; He et al. 2021 |
| Escalar el embedding de entrada por $\sqrt{d}$ | 🟡 convención de arquitectura | Gemma (`embed_scale = hidden_size**0.5` en la implementación de transformers) | código de `transformers` |
| *Logit soft-capping* en la cabeza | 🟡 emergente | Gemma 2 | Gemma Team 2024b |
| Cross-entropy fusionada / por trozos | 🟢 sólido en entrenamiento | Liger Kernel (`FusedLinearCrossEntropy`) | Hsu et al. 2024 |
| Ampliar vocabulario con init por media / sub-tokens | 🟡 práctica común | `resize_token_embeddings(mean_resizing=True)` en transformers | Hewitt 2021 (blog); docs de transformers |
| Detección de tokens sub-entrenados por pesos | 🟡 emergente | Cohere (análisis de muchos LMs abiertos) | Land & Bartolo 2024 |
| Alternativas al softmax de rango bajo (Mixture of Softmaxes) | 🔴 investigación | Sin adopción amplia en LLMs actuales que conozcamos | Yang et al. 2018 |
| Embeddings estáticos (word2vec/GloVe) | 🟢 maduro, uso residual | *Baselines*, dispositivos restringidos | Mikolov et al. 2013; Pennington et al. 2014 |
""")

nb.md(r"""
## 🏭 En producción
- **Memoria y parámetros.** En modelos pequeños la tabla domina: 31 % de GPT-2 small (calculado arriba). Por eso los LMs pequeños tienden a atar embeddings (Gemma, GPT-2) y por eso ampliar $V$ cuesta mucho más en un modelo de 100M que en uno de 70B.
- **Entrenamiento con vocabularios grandes.** Con $V$ de cientos de miles, los logits $B\cdot T\cdot V$ son el mayor tensor de activaciones; los equipos usan cross-entropy por trozos o kernels fusionados (Liger Kernel, Hsu et al., 2024) para no materializarlos.
- **Eficiencia de hardware.** nanoGPT de Karpathy rellena el vocabulario de GPT-2 de 50 257 a **50 304** («padded up to nearest multiple of 64 for efficiency», comentario de `model.py`); `resize_token_embeddings` expone `pad_to_multiple_of` con el mismo fin (Tensor Cores).
- **Tokens especiales y de dominio.** Añadir tokens (roles de chat, herramientas, términos de dominio) es rutina: transformers inicializa por defecto con la media de las filas existentes (`mean_resizing=True`, referencia al blog de Hewitt en su docstring). Las filas nuevas **deben entrenarse** (y en modelos desatados, también las de salida).
- **Auditoría de vocabulario.** Cohere (Land & Bartolo, 2024) publicó métodos basados en pesos para encontrar tokens sub-entrenados en muchos LMs abiertos: la mecánica de la sección 3 es su fundamento.
- **Para Políglota:** el embedder del módulo 11 tendrá su propia tabla $E$; las decisiones de hoy (tamaño de vocabulario, tokens de código, inicialización de tokens nuevos) se pagan allí en memoria y en calidad de la cola larga.
""")

nb.md(r"""
## 🧠 Secretos de la élite
1. **Las filas que nunca son objetivo colapsan.** El gradiente de salida de un token huérfano es $\sum_t p_{tj}\mathbf h_t$: todas se empujan hacia $-\bar{\mathbf h}$. Lo mediste: coseno medio ≈ +0.97 entre esas filas frente a ≈ 0 en las frecuentes (Gao et al., 2019, lo llaman *representation degeneration*).
2. **La norma de entrada detecta tokens sin entrenar solo en modelos desatados.** Con AdamW una fila nunca vista se reduce exactamente como $e^{-\eta\lambda n}$ (verificado al 3.er decimal); en un modelo atado la vía de salida la mueve (su norma creció ~5× en nuestro experimento). Elige el indicador según el tipo de modelo.
3. **Nunca compares pérdida por token entre tokenizers distintos.** Al ampliar el vocabulario, la pérdida por token cambia aunque el modelo no mejore; usa bits por byte (o por carácter) sobre el mismo texto.
4. **`mean_resizing` hace que todos los tokens nuevos nazcan idénticos.** La covarianza se escala por $10^{-9}$ (código de transformers), así que hasta que se entrenan, el modelo no puede distinguir entre ellos; con pocos datos de ajuste, inicializar por media de sub-tokens arranca mejor en bpb, aunque filtró ~10× más probabilidad a los tokens nuevos en nuestra medición.
5. **Gemma escala la entrada por $\sqrt{d}$.** Si comparas normas de $E$ entre familias de modelos, ten en cuenta multiplicadores de entrada (y *soft-capping* de logits en Gemma 2) antes de sacar conclusiones.
6. **Modelos pequeños, cabeza estrecha.** Godey et al. (2024) asocian la saturación de LMs pequeños al cuello de botella softmax (con < ~1000 dimensiones ocultas); antes de escalar datos, pregúntate si $d$ limita.
7. **Rellena $V$ a múltiplos de 64/128.** Es gratis en calidad (filas que nunca se usan) y evita matmuls con dimensiones incómodas para los Tensor Cores; pero esas filas de relleno son, por construcción, «tokens sub-entrenados»: exclúyelas de los análisis.
""")

nb.md(r"""
## ⚠️ Errores comunes
- Comparar la pérdida **por token** de dos tokenizers distintos (usa bpb).
- Añadir tokens al tokenizer y **olvidar** `resize_token_embeddings` (índices fuera de rango) o redimensionar sin entrenar las filas nuevas.
- En modelos **desatados**, inicializar/entrenar solo la fila de entrada y dejar la de salida aleatoria: el modelo nunca predecirá el token nuevo.
- Añadir tokens de dominio **sin espacio inicial** en tokenizers byte-level: `"serialización"` y `" serialización"` son tokens distintos; el texto real casi siempre trae el espacio.
- Usar filas de $E$ (o estados ocultos crudos) como embeddings de búsqueda: son anisótropos y mezclan forma, frecuencia y significado (módulo 10).
- Aplicar *weight decay* a la tabla de embeddings sin pensar en los tokens raros: se encogen aunque nunca se vean.
- Leer «tokens frecuentes del corpus Políglota» como si fuera la frecuencia del pre-entrenamiento: es solo un *proxy*.
""")

nb.md(r"""
## Autoevaluación

<details><summary><b>1. (Cálculo)</b> Un modelo tiene $V=128\,000$, $d=2048$ y 1.2 mil millones de parámetros con embeddings desatados. ¿Cuántos parámetros ahorra el tying y qué fracción del total es?</summary>

$Vd = 128\,000\times2048 = 262\,144\,000$ ≈ 262M, es decir ≈ 21.8 % de 1.2B. Con tying el modelo pasaría a ≈ 0.94B.
</details>

<details><summary><b>2. (Cálculo)</b> Entrenas con AdamW, LR constante $\eta=2\cdot10^{-4}$, $\lambda=0.1$, 50 000 pasos, con decay en $E$ y modelo desatado. ¿Qué norma relativa conserva una fila de entrada nunca vista?</summary>

$e^{-\eta\lambda n}=e^{-2\cdot10^{-4}\cdot0.1\cdot5\cdot10^4}=e^{-1}\approx0.37$.
</details>

<details><summary><b>3. (Diagnóstico)</b> Tras añadir 500 tokens de dominio a un LM desatado y ajustar 1 000 pasos, el modelo nunca genera ninguno de ellos, aunque la pérdida bajó. ¿Qué miras primero?</summary>

Si se entrenó (o se inicializó con sentido) la **matriz de salida**: si solo se ajustó $E$ de entrada, las filas nuevas de $W_U$ siguen aleatorias o en la media y su logit nunca gana. Comprueba también que los tokens se añadieron con el espacio inicial correcto (si el texto nunca los produce, nunca son objetivo).
</details>

<details><summary><b>4. (Diagnóstico)</b> En un LM atado, las filas de 300 tokens tienen coseno > 0.95 entre sí y logits muy negativos en todos los contextos. ¿Qué indica y qué harías antes de servir el modelo?</summary>

Son tokens que (casi) nunca fueron objetivo: colapsaron hacia $-\bar{\mathbf h}$ (sección 3). Son candidatos a glitch tokens (05): verifícalos con prompts, y en producción considera bloquearlos en el muestreo o reentrenar sus filas con datos que los contengan.
</details>

<details><summary><b>5. (Transferencia)</b> En recsys, tu *two-tower* tiene una tabla de ítems con cola larga y un catálogo que crece cada día. ¿Qué dos ideas de este módulo trasladas?</summary>

(a) Los ítems sin interacciones solo reciben el gradiente de «negativo» del softmax: colapsan y su norma no significa nada → usa features de contenido para inicializar ítems nuevos (el análogo de la media de sub-tokens) en vez de vectores aleatorios. (b) El coste de la capa de salida (softmax sobre millones de ítems) se ataca con softmax muestreado / negativos en batch, que es lo que verás en el módulo 11.
</details>

<details><summary><b>6.</b> ¿Por qué el rango de la matriz de log-probabilidades de un LM con cabeza lineal es como mucho $d+1$?</summary>

Porque $Z=HW_U^\top$ tiene rango $\le d$ y el log-softmax resta a cada fila una constante (su log-partición), lo que suma como mucho una dirección más ($\mathbf c\mathbf 1^\top$, de rango 1).
</details>

<details><summary><b>7. (Transferencia)</b> Políglota quiere añadir 2 000 identificadores de código frecuentes al tokenizer de su embedder bidireccional (sin cabeza de LM). ¿Qué cambia respecto a este módulo?</summary>

No hay unembedding ni «masa filtrada»; la inicialización por media de sub-tokens sigue siendo la opción razonable, pero la métrica es de retrieval (nDCG@10 en consultas de código, módulos 10–11 y 15) y el ajuste se hace con la pérdida contrastiva del embedder.
</details>
""")

nb.md(r"""
## Referencias
**Papers**
- Press, O., & Wolf, L. (2017). *Using the Output Embedding to Improve Language Models.* EACL. [arXiv:1608.05859](https://arxiv.org/abs/1608.05859)
- Inan, H., Khosravi, K., & Socher, R. (2016). *Tying Word Vectors and Word Classifiers: A Loss Framework for Language Modeling.* [arXiv:1611.01462](https://arxiv.org/abs/1611.01462)
- Yang, Z., Dai, Z., Salakhutdinov, R., et al. (2018). *Breaking the Softmax Bottleneck: A High-Rank RNN Language Model.* ICLR. [arXiv:1711.03953](https://arxiv.org/abs/1711.03953)
- Gao, J., He, D., Tan, X., et al. (2019). *Representation Degeneration Problem in Training Natural Language Generation Models.* ICLR. [arXiv:1907.12009](https://arxiv.org/abs/1907.12009)
- Godey, N., de la Clergerie, É., & Sagot, B. (2024). *Why do small language models underperform? Studying LM Saturation via the Softmax Bottleneck.* [arXiv:2404.07647](https://arxiv.org/abs/2404.07647)
- Kobayashi, G., Kuribayashi, T., Yokoi, S., et al. (2023). *Transformer Language Models Handle Word Frequency in Prediction Head.* [arXiv:2305.18294](https://arxiv.org/abs/2305.18294)
- Land, S., & Bartolo, M. (2024). *Fishing for Magikarp: Automatically Detecting Under-trained Tokens in Large Language Models.* [arXiv:2405.05417](https://arxiv.org/abs/2405.05417)
- Chung, H. W., Févry, T., Tsai, H., et al. (2021). *Rethinking Embedding Coupling in Pre-trained Language Models.* ICLR. [arXiv:2010.12821](https://arxiv.org/abs/2010.12821)
- He, P., Gao, J., Chen, W. (2021). *DeBERTaV3: Improving DeBERTa using ELECTRA-Style Pre-Training with Gradient-Disentangled Embedding Sharing.* [arXiv:2111.09543](https://arxiv.org/abs/2111.09543)
- Gemma Team (2024a). *Gemma: Open Models Based on Gemini Research and Technology.* [arXiv:2403.08295](https://arxiv.org/abs/2403.08295) · Gemma Team (2024b). *Gemma 2: Improving Open Language Models at a Practical Size.* [arXiv:2408.00118](https://arxiv.org/abs/2408.00118)
- Hsu, P.-L., Dai, Y., Kothapalli, V., et al. (2024). *Liger Kernel: Efficient Triton Kernels for LLM Training.* [arXiv:2410.10989](https://arxiv.org/abs/2410.10989)
- Takase, S., Kiyono, S., Kobayashi, S., et al. (2023). *Spike No More: Stabilizing the Pre-training of Large Language Models.* [arXiv:2312.16903](https://arxiv.org/abs/2312.16903)
- Mikolov, T., Chen, K., Corrado, G., & Dean, J. (2013a). *Efficient Estimation of Word Representations in Vector Space.* [arXiv:1301.3781](https://arxiv.org/abs/1301.3781) · Mikolov et al. (2013b). *Distributed Representations of Words and Phrases and their Compositionality.* [arXiv:1310.4546](https://arxiv.org/abs/1310.4546)
- Pennington, J., Socher, R., & Manning, C. D. (2014). *GloVe: Global Vectors for Word Representation.* EMNLP.
- Levy, O., & Goldberg, Y. (2014). *Neural Word Embedding as Implicit Matrix Factorization.* NeurIPS.

**Blogs, código y documentación**
- Hewitt, J. (2021). *Initializing New Word Embeddings for Pretrained Language Models* (blog, enlazado desde el docstring de `resize_token_embeddings`): https://nlp.stanford.edu/~johnhew/vocab-expansion.html
- Karpathy, A. *nanoGPT* (`model.py`, relleno del vocabulario a 50 304): https://github.com/karpathy/nanoGPT
- Hugging Face `transformers`: `PreTrainedModel.resize_token_embeddings` (`mean_resizing`, `pad_to_multiple_of`) y `GemmaTextScaledWordEmbedding`.
- Liger Kernel: https://github.com/linkedin/Liger-Kernel

## Siguiente módulo
**10 · Embeddings contextuales y de oraciones**: de la tabla $E$ (un vector por token, sin contexto) a los estados ocultos de BERT (un vector por token *en contexto*) y a cómo resumirlos en **un vector por frase** (pooling, SBERT, anisotropía, whitening) para buscar en Políglota.
""")

nb.save(LESSON)

# ════════════════════════════════════════════════════════════════════════════════════════
#  PROYECTO 09
# ════════════════════════════════════════════════════════════════════════════════════════
pj = Notebook("Proyecto 09 · Auditoría de la capa de embedding y vocabulario de dominio", colab_path=PROJECT)

pj.md(pj.badge() + r"""
# Proyecto 09 · Auditoría de la capa de embedding y extensión con vocabulario de dominio

| | |
|---|---|
| **Nivel** | 🟡 Intermedio |
| **Duración** | ≈ 2 h |
| **Cómputo** | CPU (≈ 3–5 min en `FAST_DEV_RUN`); GPT-2 small si hay acceso al hub. 0 unidades de Colab |
| **Requisitos** | Lección 09 completa |

## Contexto de negocio
Eres ML engineer en **Políglota Labs**. El equipo va a ajustar un LM pequeño para generar *snippets* y consultas sintéticas sobre la documentación técnica (las usarás para entrenar el embedder en el módulo 11).
Antes de tocarlo, tu *tech lead* te pide dos cosas:
1. **Auditoría de la capa de embedding**: ¿qué tokens del vocabulario nunca aparecen en nuestro corpus?, ¿están sus filas «sanas»?, ¿cómo se relaciona la norma con la frecuencia?
2. **Vocabulario de dominio**: el tokenizer trocea mucho nuestros términos técnicos. Propón $K=32$ tokens nuevos, añádelos, inicialízalos con criterio y demuestra con números que **reduces tokens por palabra sin empeorar la calidad** (bits por byte).

**Conexión.** Viene del módulo 05 (tokens sub-entrenados) y 07 (inicialización de vocabulario nuevo); el resultado (tokenizer extendido + LM ajustado) alimenta la generación de datos del módulo 11.

## Dataset
Corpus Políglota (`carga_corpus`, módulo 00): Wikipedia ES/EN + funciones Python (CodeSearchNet o, sin red, la stdlib); si no hay red, texto sintético con el mismo esquema (el notebook avisa).

## Entregables y rúbrica
Los umbrales están **calibrados con la solución de referencia** (semilla 42, `FAST_DEV_RUN=True`, modelo de *fallback* mini-GPT-2 y corpus sintético, que es lo que pudo ejecutarse al construir el curso). Si corres con GPT-2 real y datos reales, ejecuta la solución y usa *sus* números menos el margen indicado.

| # | Entregable | Criterio (umbral) |
|---|---|---|
| R1 | `auditoria` con normas, frecuencias, ρ de Spearman y nº de tokens no vistos | claves presentes; `n_no_vistos` > 0; ρ es un número finito |
| R2 | Coseno medio entre filas de tokens **no vistos** vs vistos frecuentes | `cos_no_vistos − cos_frecuentes ≥ 0.5` (referencia mide ≈ 0.9). Solo con el modelo de *fallback*: con GPT-2 real «no visto en Políglota» no significa «no visto al entrenar» y R2 solo se informa |
| R3 | Lista de $K=32$ términos con ahorro = frecuencia × (piezas − 1) | 32 términos únicos, cada uno con ≥ 2 piezas en el tokenizer original |
| R4 | Extensión + init por media de sub-tokens; filas viejas **intactas** tras ajustar | `assert` de filas viejas pasa |
| R5 | Fertilidad (tokens/palabra) en el texto retenido | reducción ≥ 5 % (referencia ≈ 8–9 %) |
| R6 | Calidad tras ajustar solo las filas nuevas | `bpb_final ≤ bpb_base + 0.05` |

*(Los valores de referencia exactos se imprimen al ejecutar la solución.)*
""")

pj.code(SETUP)
pj.md("### Utilidades (corpus Políglota canónico y mini-LM de laboratorio). No hace falta modificarlas.")
for _src in src_corpus_cells():
    pj.code(_src)
pj.code(CORPUS_USE)
pj.code(MINI_LM)
pj.code(r'''
from tokenizers import AddedToken


def carga_lm():
    """GPT-2 small si el hub es accesible; si no, mini-GPT-2 ATADO entrenado aquí (fallback documentado)."""
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        return AutoModelForCausalLM.from_pretrained("gpt2").eval(), AutoTokenizer.from_pretrained("gpt2"), "GPT-2 small (real)"
    except Exception as e:
        print(f"⚠️  GPT-2 no disponible ({type(e).__name__}): entreno un mini-GPT-2 atado (fallback, ~30 s en CPU)")
    tk = entrena_tokenizer(textos, vocab_size=500)
    m = crea_mini_gpt(tk, tie=True)
    entrena_lm(m, flujo_ids(tk, random.Random(SEED).sample(textos, len(textos))), steps=600 if FAST_DEV_RUN else 3000)
    return m, tk, "mini-GPT-2 (fallback)"


@torch.no_grad()
def bpb_y_fuga(model, tok, textos, old_V, T=64):
    """(bits por byte, masa media en tokens nuevos donde el objetivo es viejo). Igual que en la lección."""
    nll, nbytes, fuga, npos = 0.0, 0, 0.0, 0
    for t in textos:
        ids = tok(t)["input_ids"][:T]
        if len(ids) < 2:
            continue
        x = torch.tensor([ids]); y = x[0, 1:]
        logp = torch.log_softmax(model(input_ids=x).logits[0, :-1].float(), -1)
        nll += -logp.gather(1, y[:, None]).sum().item(); nbytes += len(tok.decode(ids[1:]).encode("utf-8"))
        viejo = y < old_V
        if logp.shape[1] > old_V and viejo.any():
            fuga += logp[viejo][:, old_V:].exp().sum(-1).sum().item(); npos += int(viejo.sum())
    return nll / nbytes / math.log(2), (fuga / npos if npos else 0.0)


lm, tok, lm_name = carga_lm()
V = len(tok)
prosa = [d["text"] for d in docs if d["lang"] != "code"]
held = prosa[::7][:40]
ft_txt = [t for i, t in enumerate(prosa) if i % 7 != 0]
K = 32
print(lm_name, "| V =", V, "| tied =", lm.get_input_embeddings().weight is lm.get_output_embeddings().weight)
''')

pj.md(r"""
## Parte A · Auditoría de la capa de embedding

### TODO 1 · `auditoria(model, tok, textos)`
Devuelve un `dict` con: `normas` (np.array V), `freq` (np.array V, conteo de cada id en `textos` tokenizados con `tok`), `rho` (Spearman entre norma y $\log(1+f)$ **solo en tokens vistos**), `n_no_vistos`, `cos_no_vistos` y `cos_frecuentes` (coseno medio entre pares distintos de filas de la matriz de **salida**, para los no vistos y para los 100 más frecuentes).

<details><summary>🪜 Pista 1</summary>

Cuenta con `Counter` sobre `tok(t)["input_ids"]`. Para el coseno medio entre pares: normaliza las filas, haz `X @ X.T` y promedia fuera de la diagonal.
</details>
<details><summary>🪜 Pista 2</summary>

`W = model.get_output_embeddings().weight.detach().float()`; `X = F.normalize(W[idx], dim=-1)`; `S = X @ X.T`; `S[~torch.eye(len(idx), dtype=bool)].mean()`. Spearman: `scipy.stats.spearmanr(a, b).statistic`.
</details>
""")
pj.code(r'''
from scipy.stats import spearmanr


def auditoria(model, tok, textos):
    # TODO 1: calcula normas, frecuencias, rho, n_no_vistos, cos_no_vistos, cos_frecuentes
    raise NotImplementedError


try:
    aud = auditoria(lm, tok, textos)
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in aud.items() if k not in ("normas", "freq")})
except NotImplementedError:
    print("⏳ TODO 1 pendiente")
''')

pj.md(r"""
### TODO 2 · Interpreta (texto)
Escribe en una celda markdown 3–4 frases: ¿la diferencia `cos_no_vistos − cos_frecuentes` confirma la derivación de la lección? ¿Por qué con GPT-2 real los «no vistos en Políglota» **no** son necesariamente tokens sub-entrenados?

<details><summary>🪜 Pista 1</summary>

Vuelve al 👀 de la sección 3 de la lección (filas de salida que nunca son objetivo): ¿hacia dónde las empuja el gradiente y por qué eso las hace parecidas entre sí? Después distingue dos corpus: el de **entrenamiento** del modelo y el de **Políglota**.
</details>

## Parte B · Vocabulario de dominio

### TODO 3 · `selecciona_terminos(tok, textos, k)`
Devuelve una lista de `k` cadenas **con espacio inicial** (`" palabra"`) ordenadas por ahorro = frecuencia × (nº de piezas − 1), considerando palabras alfabéticas de ≥ 6 caracteres.

<details><summary>🪜 Pista 1</summary>

`re.findall(r"[^\W\d_]{6,}", texto)` extrae palabras alfabéticas (con tildes). Piezas = `len(tok(" " + w, add_special_tokens=False)["input_ids"])`.
</details>
<details><summary>🪜 Pista 2</summary>

Cuenta con un `Counter` sobre todas las palabras de todos los textos; para cada `(w, n)` calcula `n * (piezas(w) - 1)` (una palabra que ya es un token no ahorra nada); ordena de mayor a menor y devuelve `" " + w` de las `k` primeras. Es el mismo criterio voraz que un merge de BPE (módulo 02): frecuencia × tokens ahorrados.
</details>

### TODO 4 · `extiende_subtoken(model, tok, nuevos)`
Copia modelo y tokenizer, añade los tokens (`AddedToken(w, normalized=False)`), redimensiona y **inicializa cada fila nueva con la media de las filas de sus piezas en el tokenizer original** (en todas las matrices distintas: entrada y, si no está atado, salida). Devuelve `(modelo, tokenizer, old_V)`.

<details><summary>🪜 Pista 1</summary>

Calcula las piezas **antes** de `add_tokens`. Recorre `{id(W): W for W in (entrada, salida)}.values()` para no inicializar dos veces la misma matriz atada.
</details>
<details><summary>🪜 Pista 2</summary>

`model.resize_token_embeddings(n, mean_resizing=False)` (envuelto en `try/except TypeError` para versiones antiguas); luego, dentro de `torch.no_grad()`, `W[old_V + j] = W[:old_V][piezas[j]].mean(0)`.
</details>

### TODO 5 · `ajusta_solo_nuevas(model, tok2, old_V, textos, steps)`
Congela todo salvo la(s) matriz(ces) de embeddings, enmascara el gradiente de las filas viejas con un *hook* y entrena con `entrena_lm(..., wd=0.0, lr=1e-2)`. Comprueba con `assert` que las filas viejas no cambian.

<details><summary>🪜 Pista 1</summary>

`hook = W.register_hook(lambda g: g * mask)` con `mask[old_V:] = 1`. ¿Por qué `wd=0.0` es imprescindible para que el `assert` pase? (Pista: lección, sección 3.)
</details>
<details><summary>🪜 Pista 2</summary>

1) `p.requires_grad_(False)` para todos los parámetros; 2) para cada matriz distinta de `{id(W): W for W in (entrada, salida)}`: `W.requires_grad_(True)`, `mask = torch.zeros_like(W); mask[old_V:] = 1`, guarda el hook y una copia `W[:old_V].detach().clone()`; 3) `entrena_lm(model, flujo_ids(tok2, textos), steps=steps, lr=1e-2, wd=0.0)`; 4) quita los hooks y `assert torch.equal(copia, W[:old_V])`. Ojo con el *closure*: `lambda g, m_=mask: g * m_` fija la máscara de **esa** matriz.
</details>
""")
pj.code(r'''
def selecciona_terminos(tok, textos, k=32):
    # TODO 3
    raise NotImplementedError


def extiende_subtoken(model, tok, nuevos):
    # TODO 4
    raise NotImplementedError


def ajusta_solo_nuevas(model, tok2, old_V, textos, steps=100):
    # TODO 5
    raise NotImplementedError
''')

pj.md(r"""
### TODO 6 · Ejecuta el pipeline y evalúa la rúbrica
La celda siguiente ya está escrita: usa tus funciones, mide fertilidad y bpb antes/después y comprueba la rúbrica.
""")
pj.code(r'''
def pipeline_y_rubrica():
    aud = auditoria(lm, tok, textos)
    nuevos = selecciona_terminos(tok, ft_txt, K)
    fert = lambda tk: float(np.mean([len(tk(t)["input_ids"]) / len(t.split()) for t in held]))
    bpb_base, _ = bpb_y_fuga(lm, tok, held, V)
    m2, tok2, old_V = extiende_subtoken(lm, tok, nuevos)
    bpb0, fuga0 = bpb_y_fuga(m2, tok2, held, old_V)
    steps = 100 if V < 5000 else (25 if device == "cpu" and FAST_DEV_RUN else 200)
    ajusta_solo_nuevas(m2, tok2, old_V, ft_txt, steps=steps)
    bpb1, fuga1 = bpb_y_fuga(m2, tok2, held, old_V)
    r = dict(rho=aud["rho"], n_no_vistos=aud["n_no_vistos"], gap_cos=aud["cos_no_vistos"] - aud["cos_frecuentes"],
             fert_base=fert(tok), fert_ext=fert(tok2), bpb_base=bpb_base, bpb_init=bpb0, bpb_final=bpb1, fuga_init=fuga0, fuga_final=fuga1)
    r["reduccion_fert"] = 1 - r["fert_ext"] / r["fert_base"]
    piezas_ok = all(len(tok(w, add_special_tokens=False)["input_ids"]) >= 2 for w in nuevos)
    checks = {
        "R1 auditoría": r["n_no_vistos"] > 0 and np.isfinite(r["rho"]),
        # R2 solo es un test válido en el fallback: allí «no visto en el corpus» = «nunca visto al entrenar».
        # Con GPT-2 real, un token ausente de Políglota sí se vio en WebText: no se espera colapso (solo se informa).
        "R2 colapso de filas no vistas (gap ≥ 0.5)" + ("" if "fallback" in lm_name else " [no aplica con GPT-2 real]"):
            r["gap_cos"] >= 0.5 or "fallback" not in lm_name,
        "R3 32 términos únicos con ≥ 2 piezas": len(set(nuevos)) == K and piezas_ok,
        "R4 filas viejas intactas": True,                       # el assert de TODO 5 habría fallado antes
        "R5 reducción de fertilidad ≥ 5 %": r["reduccion_fert"] >= 0.05,
        "R6 bpb_final ≤ bpb_base + 0.05": r["bpb_final"] <= r["bpb_base"] + 0.05,
    }
    for k_, v_ in r.items():
        print(f"{k_:16s} {v_:.4f}" if isinstance(v_, float) else f"{k_:16s} {v_}")
    print()
    for k_, ok in checks.items():
        print(("✅ " if ok else "❌ ") + k_)
    return r, nuevos


try:
    resultado, nuevos = pipeline_y_rubrica()
except NotImplementedError:
    print("⏳ Completa los TODO 1, 3, 4 y 5 para ejecutar el pipeline.")
''')

pj.md(r"""
## Retos extra (nivel experto)
1. **Modelo desatado.** Repite con un mini-GPT-2 desatado (`tie=False`): inicializa también la matriz de salida y comprueba qué pasa si **no** lo haces (¿llega a predecirse algún token nuevo?).
2. **Init de Hewitt vs sub-tokens con pocos datos.** Repite el ajuste con 10, 30 y 100 pasos y grafica bpb vs pasos para `mean`, `subtoken` y `hf_default`.
3. **Relleno a múltiplo de 64.** Usa `pad_to_multiple_of=64` y verifica que las filas de relleno aparecen como «no vistas» en tu auditoría: exclúyelas.
4. **bpb por idioma.** Separa `held` en ES y EN: ¿la extensión ayuda por igual a ambos idiomas? Relaciónalo con la paridad de tokens del módulo 04.

## Reflexión
- ¿Qué indicador usarías en producción para vigilar tokens sub-entrenados si el modelo está atado? ¿Y si está desatado?
- Si Políglota añadiera 5 000 identificadores de código, ¿cuánta memoria extra supone en GPT-2 small ($d=768$, fp16)? ¿Y en el cómputo de la cabeza?
- ¿Cómo cambia este análisis para un embedder bidireccional (sin cabeza de LM) como el que entrenarás en el módulo 11?
""")

pj.md(r"""
---
## ⛔ SPOILER — intenta resolverlo primero
Debajo está la **solución de referencia** completa. Ejecutarla redefine las funciones y vuelve a correr el pipeline y la rúbrica.
""")
pj.code(r'''
def auditoria(model, tok, textos):
    cnt = Counter(i for t in textos for i in tok(t)["input_ids"])
    Vv = model.get_input_embeddings().weight.shape[0]
    freq = np.array([cnt.get(i, 0) for i in range(Vv)])
    normas = model.get_input_embeddings().weight.detach().float().norm(dim=1).numpy()
    vis = freq > 0
    rho = float(spearmanr(normas[vis], np.log1p(freq[vis])).statistic)
    W = model.get_output_embeddings().weight.detach().float()

    def cos_medio(idx):
        X = F.normalize(W[torch.as_tensor(idx)], dim=-1)
        S = X @ X.T
        return float(S[~torch.eye(len(idx), dtype=bool)].mean())

    no_vistos = np.where(~vis)[0]
    return dict(normas=normas, freq=freq, rho=rho, n_no_vistos=int(len(no_vistos)),
                cos_no_vistos=cos_medio(no_vistos) if len(no_vistos) > 1 else float("nan"),
                cos_frecuentes=cos_medio(np.argsort(-freq)[:100]))


def selecciona_terminos(tok, textos, k=32):
    pal = Counter(w for t in textos for w in re.findall(r"[^\W\d_]{6,}", t))
    sc = [(w, n * (len(tok(" " + w, add_special_tokens=False)["input_ids"]) - 1)) for w, n in pal.items()]
    return [" " + w for w, _ in sorted(sc, key=lambda x: -x[1])[:k]]


def extiende_subtoken(model, tok, nuevos):
    tok2, m2 = copy.deepcopy(tok), copy.deepcopy(model)
    old_V = len(tok2)
    piezas = [tok2(w, add_special_tokens=False)["input_ids"] for w in nuevos]
    tok2.add_tokens([AddedToken(w, normalized=False) for w in nuevos])
    try:
        m2.resize_token_embeddings(len(tok2), mean_resizing=False)
    except TypeError:
        m2.resize_token_embeddings(len(tok2))
    mats = {id(W): W for W in (m2.get_input_embeddings().weight, m2.get_output_embeddings().weight)}
    with torch.no_grad():
        for W in mats.values():
            for j, p in enumerate(piezas):
                W[old_V + j] = W[:old_V][p].mean(0)
    return m2, tok2, old_V


def ajusta_solo_nuevas(model, tok2, old_V, textos, steps=100):
    for p in model.parameters():
        p.requires_grad_(False)
    mats = {id(W): W for W in (model.get_input_embeddings().weight, model.get_output_embeddings().weight)}
    hooks, antes = [], []
    for W in mats.values():
        W.requires_grad_(True)
        mask = torch.zeros_like(W); mask[old_V:] = 1
        hooks.append(W.register_hook(lambda g, m_=mask: g * m_))
        antes.append(W[:old_V].detach().clone())
    hist = entrena_lm(model, flujo_ids(tok2, textos), steps=steps, lr=1e-2, wd=0.0, B=8, T=48)
    for h_ in hooks:
        h_.remove()
    for W, a in zip(mats.values(), antes):
        assert torch.equal(a, W[:old_V].detach()), "¡las filas viejas cambiaron!"
    return hist


resultado, nuevos = pipeline_y_rubrica()
print("\nprimeros términos:", nuevos[:10])
''')

pj.save(PROJECT)

README = r"""# Módulo 09 · La capa de embedding en LLMs

**Nivel:** 🟡 Intermedio · **Duración:** ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) · **Cómputo:** CPU (0 unidades de Colab; GPT-2 small corre en CPU, T4 opcional)

| Archivo | Contenido |
|---|---|
| [`09_capa_embedding_llm.ipynb`](09_capa_embedding_llm.ipynb) | Lección: lookup = one-hot × E · anatomía E / W_U y coste en parámetros (GPT-2: 31 %) · weight tying atado vs desatado · derivación del gradiente del unembedding y colapso de filas huérfanas (medido) · weight decay en filas nunca vistas (medido vs predicho) · geometría de E: norma vs frecuencia, anisotropía, espectro y rango efectivo, vecinos, PCA · cuello de botella softmax (experimento) y cross-entropy por trozos · extensión de vocabulario con 4 inicializaciones medidas en bits por byte, fertilidad y masa filtrada · caja histórica word2vec/GloVe/PMI |
| [`09_proyecto_capa_embedding_llm.ipynb`](09_proyecto_capa_embedding_llm.ipynb) | Proyecto Políglota: auditoría de la capa de embedding (normas, frecuencias, colapso de filas no vistas) y extensión con 32 tokens de dominio inicializados por media de sub-tokens, con rúbrica automática |
| `assets/` | Imágenes de Gemini: `M09-IMG-01.png`, `M09-IMG-02.png`, `M09-IMG-03.png` |

## Objetivos
1. Explicar el lookup como producto one-hot y por qué solo las filas vistas reciben gradiente de entrada.
2. Cuantificar el peso de E/W_U y el ahorro del weight tying.
3. Derivar el gradiente del unembedding y predecir el colapso de los tokens que nunca son objetivo.
4. Medir la geometría de E (normas, frecuencia, anisotropía, espectro, vecinos).
5. Demostrar el cuello de botella softmax y el coste de la cabeza.
6. Extender el vocabulario y comparar inicializaciones con métricas correctas (bpb).

## Datasets y modelos
- Corpus Políglota canónico (`carga_corpus`, módulo 00): Wikipedia ES/EN + CodeSearchNet (o stdlib) → sintético si no hay red.
- GPT-2 small (`gpt2`, Hugging Face). **Fallback documentado:** mini-GPT-2 atado (2 capas, d = 64, BPE de 500 tokens) entrenado en el propio notebook.

## Estado de pruebas (entorno de autoría)
Hugging Face estaba **bloqueado** por el proxy: los dos notebooks se ejecutaron completos con el corpus **sintético** + stdlib y el **mini-GPT-2 de fallback** (CPU, ≈ 3.5 min la lección, ≈ 1.5 min el proyecto). Las celdas con GPT-2 real y configs de otros modelos **no** pudieron ejecutarse; están protegidas con `try/except`. Los umbrales de la rúbrica están calibrados con esa ejecución.

## Lecturas clave
Press & Wolf 2017 (arXiv:1608.05859) · Inan et al. 2016 (arXiv:1611.01462) · Yang et al. 2018 (arXiv:1711.03953) · Gao et al. 2019 (arXiv:1907.12009) · Godey et al. 2024 (arXiv:2404.07647) · Land & Bartolo 2024 (arXiv:2405.05417) · Hewitt 2021 (blog de inicialización de vocabulario).

## Conexión con Políglota
Fija cómo se representa cada token dentro de un modelo. El módulo 10 pasa de vectores por token a vectores por frase; el 11 entrena el embedder propio de Políglota.

Los notebooks se generan con `python tokenization-embeddings-course/_tools/builders/build_09.py` (desde la raíz del repo).
"""
(ROOT / MOD / "README.md").write_text(README, encoding="utf-8")
(ROOT / MOD / "assets").mkdir(exist_ok=True)
(ROOT / MOD / "assets" / ".gitkeep").touch()
print("OK README y assets/")
