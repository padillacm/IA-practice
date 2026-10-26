"""Builder del módulo 11 · Aprendizaje contrastivo para embeddings  (autor A4).

Uso (desde la raíz del repo):  python tokenization-embeddings-course/_tools/builders/build_11.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "_tools"))
sys.path.insert(0, str(ROOT / "_tools" / "builders"))
from nbbuild import Notebook                                   # noqa: E402
from poliglota_utils import SRC_BM25, SRC_METRICS, src_corpus_cells   # noqa: E402
from a4_common import LEXICON_CELL, SYNTH_CELL                 # noqa: E402  (mundo de juguete del laboratorio)

MOD = "11_aprendizaje_contrastivo"
LESSON = f"tokenization-embeddings-course/{MOD}/11_aprendizaje_contrastivo.ipynb"
PROJECT = f"tokenization-embeddings-course/{MOD}/11_proyecto_aprendizaje_contrastivo.ipynb"

SETUP11 = r'''
!pip install -q transformers sentence-transformers peft accelerate tokenizers datasets scipy scikit-learn matplotlib
import copy, json, math, os, random, re, time, warnings, zlib
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

warnings.filterwarnings("ignore")
import transformers
transformers.logging.set_verbosity_error(); transformers.utils.logging.disable_progress_bar()
SEED = 42
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
device = "cuda" if torch.cuda.is_available() else "cpu"
FAST_DEV_RUN = True   # True: CPU, modelos diminutos, ~10 min. False: más pasos/datos (GPU L4/A100 recomendada)
PAL = {"azul": "#1F6FEB", "naranja": "#F28E2B", "verde": "#2CA02C", "gris": "#6B7280", "morado": "#9467BD"}
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.25,
                     "axes.spines.top": False, "axes.spines.right": False})
print(f"device={device} · FAST_DEV_RUN={FAST_DEV_RUN} · torch {torch.__version__}")
'''

CORPUS11 = r'''
corpus = carga_corpus(FAST_DEV_RUN)
docs, queries, qrels = corpus["docs"], corpus["queries"], corpus["qrels"]
doc_ids = [d["id"] for d in docs]
doc_txt = [d["text"] for d in docs]
txt_of = dict(zip(doc_ids, doc_txt))
# partición determinista de las consultas: ~50 % entrenamiento / ~50 % test
split_q = {q["qid"]: ("train" if zlib.crc32(q["qid"].encode()) % 2 == 0 else "test") for q in queries}
q_train = [q for q in queries if split_q[q["qid"]] == "train"]
q_test = [q for q in queries if split_q[q["qid"]] == "test"]
print("fuente:", corpus["source"], "| docs:", len(docs), "| queries train/test:", len(q_train), len(q_test))
'''

ENC11 = r'''
# ── Bi-encoder DESDE CERO: tokenizer BPE + Transformer encoder diminuto + mean pooling + L2 ──
from tokenizers import Tokenizer, models, normalizers, pre_tokenizers, trainers
from transformers import PreTrainedTokenizerFast


def entrena_tokenizer(textos, vocab_size=2000):
    tk = Tokenizer(models.BPE(unk_token="[UNK]"))
    tk.normalizer = normalizers.Sequence([normalizers.NFKC(), normalizers.Lowercase()])
    tk.pre_tokenizer = pre_tokenizers.Sequence([pre_tokenizers.Whitespace(), pre_tokenizers.Digits(individual_digits=True)])
    tk.train_from_iterator(textos, trainers.BpeTrainer(vocab_size=vocab_size, special_tokens=["[PAD]", "[UNK]"]))
    return PreTrainedTokenizerFast(tokenizer_object=tk, pad_token="[PAD]", unk_token="[UNK]")


class BiEncoder(nn.Module):
    """Una sola torre (pesos compartidos para consulta y documento): emb -> Transformer -> media con máscara -> L2."""

    def __init__(self, V, d=128, capas=2, cabezas=4, max_len=64, dropout=0.1):
        super().__init__()
        self.emb, self.pos = nn.Embedding(V, d, padding_idx=0), nn.Embedding(max_len, d)
        capa = nn.TransformerEncoderLayer(d, cabezas, 2 * d, dropout=dropout, batch_first=True, norm_first=True)
        self.enc, self.ln, self.max_len = nn.TransformerEncoder(capa, capas, enable_nested_tensor=False), nn.LayerNorm(d), max_len

    def forward(self, ids, mask):
        x = self.emb(ids) + self.pos(torch.arange(ids.shape[1], device=ids.device))[None]
        h = self.ln(self.enc(x, src_key_padding_mask=~mask.bool()))
        m = mask.unsqueeze(-1).float()
        return F.normalize((h * m).sum(1) / m.sum(1).clamp(min=1), dim=-1)


def tokeniza(tok, textos, max_len=64):
    b = tok(textos, padding=True, truncation=True, max_length=max_len, return_tensors="pt")
    return b["input_ids"].to(device), b["attention_mask"].to(device)


@torch.no_grad()
def codifica(model, tok, textos, bs=128):
    model.eval()
    return torch.cat([model(*tokeniza(tok, textos[i:i + bs])) for i in range(0, len(textos), bs)]).cpu()
'''

LOSS11 = r'''
def info_nce(q, d, tau=0.05, d_extra=None, simetrica=False):
    """InfoNCE con negativos en el lote. q, d: (B, dim) normalizados; el positivo de q[i] es d[i].
    d_extra: (M, dim) negativos adicionales (hard negatives) que se añaden como columnas.
    simetrica=True suma también la dirección documento -> consulta."""
    D = d if d_extra is None else torch.cat([d, d_extra])
    logits = q @ D.T / tau                              # (B, B + M)
    y = torch.arange(q.shape[0], device=q.device)
    loss = F.cross_entropy(logits, y)
    if simetrica:
        loss = (loss + F.cross_entropy(d @ q.T / tau, y)) / 2
    return loss


def alineacion(x, y, alpha=2):
    """L_align = E ||f(x) - f(y)||^alpha sobre pares positivos (Wang & Isola, 2020). Menor = mejor."""
    return (x - y).norm(dim=1).pow(alpha).mean().item()


def uniformidad(x, t=2):
    """L_uniform = log E exp(-t ||f(x) - f(y)||^2) sobre pares aleatorios. Más negativo = más uniforme."""
    return torch.pdist(x, p=2).pow(2).mul(-t).exp().mean().log().item()
'''

TRAIN11 = r'''
def entrena_biencoder(pares, tok, pasos=300, B=32, tau=0.05, lr=2e-3, duros=None, sin_duplicados=True,
                      solo_positivos=False, simetrica=False, seed=SEED, grupo=None, log_cada=50, eval_fn=None, textos=None):
    """pares: lista de (texto_consulta, id_doc_positivo). duros: {índice_par: [ids de docs negativos]}.
    grupo: función par -> clave; sin_duplicados evita dos pares con la misma clave en un lote (falsos negativos).
    textos: dict id_doc -> texto (por defecto, el corpus Políglota)."""
    textos = textos or txt_of
    torch.manual_seed(seed); rng = random.Random(seed)
    model = BiEncoder(len(tok)).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    grupo = grupo or (lambda p: p[1])
    hist = []
    for paso in range(pasos):
        orden = rng.sample(range(len(pares)), len(pares))
        lote, vistos = [], set()
        for i in orden:
            g = grupo(pares[i])
            if sin_duplicados and g in vistos:
                continue
            vistos.add(g); lote.append(i)
            if len(lote) == B:
                break
        q = model(*tokeniza(tok, [pares[i][0] for i in lote]))
        d = model(*tokeniza(tok, [textos[pares[i][1]] for i in lote]))
        extra = None
        if duros is not None:
            neg = [rng.choice(duros[i]) for i in lote if duros.get(i)]
            extra = model(*tokeniza(tok, [textos[n] for n in neg])) if neg else None
        if solo_positivos:
            loss = (q - d).pow(2).sum(1).mean()                 # sin negativos: ¡invita al colapso!
        else:
            loss = info_nce(q, d, tau, extra, simetrica)
        opt.zero_grad(); loss.backward(); opt.step()
        if paso % log_cada == 0 or paso == pasos - 1:
            reg = dict(paso=paso, loss=loss.item(), align=alineacion(q.detach(), d.detach()), unif=uniformidad(d.detach()))
            if eval_fn:
                reg["ndcg"] = eval_fn(model)
            hist.append(reg)
    return model.eval(), hist
'''
TOY11 = r'''
# ── Laboratorio controlado: "mundo de juguete" con verdad conocida (concepto = acción × objeto, ES/EN/código) ──
toy = genera_mundo_juguete(fast_dev=True)
toy_txt = {d["id"]: d["text"] for d in toy["docs"]}
toy_ids = list(toy_txt)
concepto = {d["id"]: d["concept"] for d in toy["docs"]}
por_concepto = defaultdict(list)
for d in toy["docs"]:
    por_concepto[d["concept"]].append(d["id"])
toy_tok = entrena_tokenizer(list(toy_txt.values()) + [q["text"] for q in toy["queries"]], vocab_size=800)
toy_q_train = [q for q in toy["queries"] if q["split"] == "train"]
toy_q_test = [q for q in toy["queries"] if q["split"] == "test"]          # conceptos NO vistos al entrenar
toy_pares = [(q["text"], did) for q in toy_q_train for did in por_concepto[q["concept"]]]


def eval_toy(model, qs=None):
    qs = qs or toy_q_test
    D = codifica(model, toy_tok, [toy_txt[i] for i in toy_ids]); Q = codifica(model, toy_tok, [q["text"] for q in qs])
    run = {q["qid"]: rank_from_scores((Q @ D.T)[k].numpy(), toy_ids, 100) for k, q in enumerate(qs)}
    return evaluate(run, {q["qid"]: toy["qrels"][q["qid"]] for q in qs})["ndcg"]


print(f"docs={len(toy_ids)} | conceptos={len(por_concepto)} | pares de entrenamiento={len(toy_pares)} | queries test={len(toy_q_test)}")
print("ejemplo:", toy_q_train[0]["text"], "→", toy_txt[por_concepto[toy_q_train[0]["concept"]][0]][:80])
'''
GRADCACHE = r'''
def paso_gradcache(model, tok, q_txt, d_txt, tau=0.05, trozo=8):
    """Un paso de Gradient Cache (Gao et al., 2021): gradiente EXACTO de InfoNCE con lote B usando memoria de 'trozo'.
    1) forward SIN grafo de todo el lote -> representaciones; 2) pérdida y gradiente respecto a las representaciones;
    3) re-forward por trozos CON grafo y backward del producto (representación · gradiente cacheado)."""
    with torch.no_grad():
        zq = torch.cat([model(*tokeniza(tok, q_txt[i:i + trozo])) for i in range(0, len(q_txt), trozo)])
        zd = torch.cat([model(*tokeniza(tok, d_txt[i:i + trozo])) for i in range(0, len(d_txt), trozo)])
    zq.requires_grad_(True); zd.requires_grad_(True)
    loss = info_nce(zq, zd, tau)
    loss.backward()                                       # solo llega a zq, zd (no hay grafo del modelo)
    for textos_, g in ((q_txt, zq.grad), (d_txt, zd.grad)):
        for i in range(0, len(textos_), trozo):
            r = model(*tokeniza(tok, textos_[i:i + trozo]))
            (r * g[i:i + trozo]).sum().backward()         # regla de la cadena: dL/dθ = Σ (dL/dz)·(dz/dθ)
    return loss.detach()
'''

GC_TEST = r'''
# Comprobación: el gradiente de GradCache coincide con el del lote completo (modo eval: sin dropout)
torch.manual_seed(SEED)
m_gc = BiEncoder(len(toy_tok)).to(device).eval()
lote = random.Random(SEED).sample(toy_pares, 32)
qs_, ds_ = [p[0] for p in lote], [toy_txt[p[1]] for p in lote]
m_gc.zero_grad()
info_nce(m_gc(*tokeniza(toy_tok, qs_)), m_gc(*tokeniza(toy_tok, ds_))).backward()
g_full = [p.grad.clone() for p in m_gc.parameters() if p.grad is not None]
m_gc.zero_grad()
paso_gradcache(m_gc, toy_tok, qs_, ds_, trozo=8)
g_gc = [p.grad.clone() for p in m_gc.parameters() if p.grad is not None]
dif = max((a - b).abs().max().item() for a, b in zip(g_full, g_gc))
print(f"max |grad lote completo − grad GradCache| = {dif:.2e}  (trozos de 8 para un lote de 32)")
'''

ST11 = r'''
# ── Con la librería de industria: sentence-transformers + MultipleNegativesRankingLoss ──
from datasets import Dataset
from sentence_transformers import SentenceTransformer, SentenceTransformerTrainer, SentenceTransformerTrainingArguments
from sentence_transformers.losses import MultipleNegativesRankingLoss
from sentence_transformers.models import Pooling, Transformer
from sentence_transformers.training_args import BatchSamplers


def modelo_st():
    """Modelo real multilingüe si hay hub; si no, un mini-BERT local SIN preentrenar envuelto en sentence-transformers."""
    try:
        return SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", device=device), "paraphrase-multilingual-MiniLM-L12-v2"
    except Exception as e:
        print(f"⚠️  sin hub ({type(e).__name__}): mini-BERT local aleatorio (fallback)")
    from tokenizers import Tokenizer, models, normalizers, pre_tokenizers, trainers
    from transformers import BertConfig, BertModel, BertTokenizerFast
    os.makedirs("mini_st", exist_ok=True)
    # Vocabulario WordPiece REPRODUCIBLE: el WordPiece trainer de `tokenizers` rompe empates según un HashMap y cambia en
    # cada proceso; Unigram es determinista y lo convertimos a la convención WordPiece ("##" = continuación).
    uni = Tokenizer(models.Unigram()); uni.normalizer = normalizers.BertNormalizer(lowercase=True, strip_accents=False)
    uni.pre_tokenizer = pre_tokenizers.Sequence([pre_tokenizers.BertPreTokenizer(), pre_tokenizers.Metaspace()])
    uni.train_from_iterator(doc_txt, trainers.UnigramTrainer(vocab_size=2000, unk_token="[UNK]", special_tokens=["[UNK]"], show_progress=False))
    chars = sorted({c for t in doc_txt for c in uni.normalizer.normalize_str(t) if not c.isspace()})
    piezas = [p for p, _ in sorted(uni.get_vocab().items(), key=lambda x: x[1]) if p not in ("[UNK]", "▁")]
    vocab = list(dict.fromkeys(["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"] + chars + ["##" + c for c in chars]
                               + [p[1:] if p.startswith("▁") else "##" + p for p in piezas]))
    with open("mini_st/vocab.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(vocab) + "\n")
    BertTokenizerFast("mini_st/vocab.txt", do_lower_case=True, strip_accents=False).save_pretrained("mini_st")
    torch.manual_seed(SEED)
    BertModel(BertConfig(vocab_size=len(vocab), hidden_size=128, num_hidden_layers=2, num_attention_heads=4, intermediate_size=256,
                         max_position_embeddings=128)).save_pretrained("mini_st")
    tr = Transformer("mini_st", max_seq_length=64)
    return SentenceTransformer(modules=[tr, Pooling(tr.get_word_embedding_dimension(), "mean")], device=device), "mini-BERT local (fallback)"


def ndcg_st(model, qs):
    D = model.encode(doc_txt, convert_to_tensor=True, normalize_embeddings=True, batch_size=64)
    Q = model.encode([q["text"] for q in qs], convert_to_tensor=True, normalize_embeddings=True, batch_size=64)
    S = (Q @ D.T).cpu().numpy()
    run = {q["qid"]: rank_from_scores(S[k], doc_ids, 100) for k, q in enumerate(qs)}
    return evaluate(run, {q["qid"]: qrels[q["qid"]] for q in qs})["ndcg"]
'''

ST_RUN = r'''
st_model, st_nombre = modelo_st()
antes = ndcg_st(st_model, q_test)
ds = Dataset.from_dict({"anchor": [p[0] for p in pares_poliglota], "positive": [txt_of[p[1]] for p in pares_poliglota]})
args = SentenceTransformerTrainingArguments(
    output_dir="st_out", num_train_epochs=1, per_device_train_batch_size=32, learning_rate=5e-4 if "fallback" in st_nombre else 2e-5,
    max_steps=150 if FAST_DEV_RUN else -1, batch_sampler=BatchSamplers.NO_DUPLICATES, report_to="none",
    logging_steps=50, save_strategy="no", seed=SEED, use_cpu=(device == "cpu"))
loss_mnrl = MultipleNegativesRankingLoss(st_model, scale=20.0)          # scale = 1/τ  -> τ = 0.05
SentenceTransformerTrainer(model=st_model, args=args, train_dataset=ds, loss=loss_mnrl).train()
despues = ndcg_st(st_model, q_test)
print(f"{st_nombre}: nDCG@10 test antes={antes:.3f} → después de MNRL={despues:.3f}")
'''

LORA11 = r'''
# ── LoRA para embedders: solo entrenamos matrices de rango r en las proyecciones de atención ──
from peft import LoraConfig, get_peft_model

base = st_model[0].auto_model                             # el Transformer dentro del SentenceTransformer
objetivo = [n for n in ("query", "value", "q_lin", "v_lin", "q_proj", "v_proj") if any(n in k for k, _ in base.named_modules())][:2]
cfg_lora = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, target_modules=objetivo)
peft_model = get_peft_model(copy.deepcopy(base), cfg_lora)
entrenables = sum(p.numel() for p in peft_model.parameters() if p.requires_grad)
total = sum(p.numel() for p in peft_model.parameters())
emb = sum(p.numel() for n, p in base.named_parameters() if "embeddings" in n)
print(f"módulos LoRA: {objetivo} | entrenables={entrenables:,} de {total:,} ({100 * entrenables / total:.2f} %) | embeddings del modelo={emb:,}")
'''

nb = Notebook("Módulo 11 · Aprendizaje contrastivo para embeddings", colab_path=LESSON, gpu=True)
nb.md(nb.badge() + r"""
# Módulo 11 · Aprendizaje contrastivo para embeddings

| | |
|---|---|
| **Nivel** | 🟠 Avanzado |
| **Duración** | ≈ 6 h (lección ≈ 3.5 h + proyecto ≈ 2.5 h) |
| **Cómputo** | `FAST_DEV_RUN=True`: CPU o T4, ≈ 10–12 min (modelos diminutos). Modo completo: **L4 o A100 recomendada** (ver la caja «Estimación de cómputo» para calcular unidades de Colab) |
| **Prerrequisitos** | 09 (capa de embedding), 10 (pooling, bi-encoders, anisotropía); softmax y entropía cruzada |
| **Hilo conductor** | Políglota entrena **su propio embedder** ES/EN/código: el *baseline* denso del módulo 10 era un modelo ajeno; hoy construyes el tuyo |

> **Dónde estamos.** En el 10 vimos que un encoder sin entrenar para similitud da embeddings pobres y que el post-procesado no crea señal. La solución industrial es **entrenar** el bi-encoder con un objetivo **contrastivo**: acercar pares relevantes y alejar los no relevantes. Lo implementas desde cero (InfoNCE, bi-encoder, Gradient Cache) y luego con `sentence-transformers`.
""")
nb.md(r"""
## Objetivos de aprendizaje
1. **Escribir** InfoNCE con cada símbolo explicado y **derivar** el papel de la temperatura en el gradiente.
2. **Derivar** por qué InfoNCE es una cota inferior de la información mutua, $I(X;Y)\ge\log K-\mathcal L$, y **comprobarlo numéricamente** (incluida la saturación en $\log K$).
3. **Implementar desde cero** en PyTorch un bi-encoder y su entrenamiento con negativos en el lote, negativos duros y pérdida simétrica.
4. **Diagnosticar** colapso y falsos negativos con las métricas de **alineación y uniformidad** (Wang & Isola, 2020).
5. **Minar** negativos duros con BM25 y **filtrar** falsos negativos (TopK-PercPos, NV-Retriever).
6. **Implementar** Gradient Cache y **verificar** que reproduce el gradiente del lote completo.
7. **Entrenar** con `sentence-transformers` (`MultipleNegativesRankingLoss`) y **calcular** cuántos parámetros entrena LoRA.
""")
nb.md(r"""
## 🔁 Conexión con módulos anteriores
<details><summary><b>1.</b> (10) ¿Por qué el producto escalar entre embeddings normalizados es «indexable» y una puntuación de cross-encoder no?</summary>

Porque $\cos(f(q), f(d))$ factoriza: $f(d)$ se calcula una vez por documento y se indexa; la búsqueda es un producto con todos los vectores (o ANN). Un cross-encoder necesita un forward por par.
</details>

<details><summary><b>2.</b> (09) La cabeza de un LM es $\text{softmax}(W_U\mathbf h)$ sobre $V$ tokens. ¿Qué tiene que ver con recuperar un documento entre $N$?</summary>

Es el mismo problema con «tokens» = documentos: $p(d\mid q)=\text{softmax}_d(f(q)\cdot f(d)/\tau)$. Con $N$ = millones, el softmax completo es imposible y se **muestrea**: los demás documentos del lote hacen de negativos. En el 09 viste también que los ítems que nunca son positivos solo reciben gradiente «de negativo».
</details>

<details><summary><b>3.</b> (10) ¿Por qué un modelo entrenado con *mean pooling* no debe usarse con CLS?</summary>

Porque el entrenamiento ajustó el espacio que produce **ese** pooling; otro pooling es otra función que nunca se optimizó.
</details>
""")
nb.code(SETUP11)
nb.md("### Utilidades del curso: corpus Políglota, métricas y BM25 canónicos (módulo 00)")
for _src in src_corpus_cells():
    nb.code(_src)
nb.code(SRC_METRICS)
nb.code(SRC_BM25)
nb.code(CORPUS11)

nb.md(r"""
## 1. Intuición: recuperar = clasificar entre todos los documentos

Si tuviéramos un único corpus fijo, podríamos entrenar un clasificador «consulta → id de documento» con softmax sobre los $N$ documentos:
$$p(d\mid q)=\frac{\exp\big(s(q,d)/\tau\big)}{\sum_{d'=1}^{N}\exp\big(s(q,d')/\tau\big)},\qquad s(q,d)=f(q)\cdot f(d).$$
Dos problemas: $N$ es enorme y cambia (documentos nuevos). La solución contrastiva: aproximar el denominador con **unos pocos documentos** — el positivo y $K-1$ negativos — y, sobre todo, **reusar como negativos los positivos de las demás consultas del lote** (*in-batch negatives*): $B$ pares dan $B(B-1)$ negativos «gratis» con una sola matriz $B\times B$.

> 💡 **Recsys.** Es exactamente la *softmax muestreada con negativos en el lote* del *two-tower* (`recsys-course/08_deep_retrieval_ann`), incluido su sesgo: los ítems populares aparecen más como negativos (allí se corrige con **logQ**; en texto es menos habitual porque los documentos positivos están mucho más repartidos). Lo nuevo aquí es el codificador (un Transformer) y el tipo de pares (consulta–pasaje, título–cuerpo, docstring–código…).
""")
nb.gemini(
    "imagen", "M11-IMG-01", "Anatomía de un embedder contrastivo",
    "Muestra el pipeline completo de entrenamiento contrastivo: pares, torre compartida, normalización, matriz de similitud del lote y pérdida InfoNCE.",
    """
    Diagrama técnico limpio, fondo blanco, 16:9, sin decoración. Paleta: azul #1F6FEB (consultas), naranja #F28E2B (documentos), verde #2CA02C (positivos), gris #6B7280 (negativos y texto secundario). Tipografía sans-serif.
    Izquierda: una columna de 4 cajas azules «q₁: cómo configurar la caché», «q₂: what is a hash table», «q₃: limitación de tasa», «q₄: unit tests» y otra columna de 4 cajas naranjas «d₁: La caché es una memoria rápida…», «d₂: A hash table stores key-value pairs…», «d₃: Una política que restringe peticiones…», «d₄: Automatic checks that verify a function…». Líneas verdes finas unen qᵢ con dᵢ con la etiqueta «pares positivos».
    Centro: ambas columnas entran en UNA torre rotulada «Encoder compartido (Transformer + mean pooling)» y salen vectores con la etiqueta «normalizar ‖·‖ = 1».
    Derecha: una matriz 4×4 rotulada «S = Q·Dᵀ / τ» con la diagonal en verde («positivos») y el resto en gris («negativos del lote»). A la derecha de la matriz, una flecha hacia la caja «InfoNCE = entropía cruzada por filas con etiqueta = diagonal».
    Pie: «B pares → B·(B−1) negativos gratis».
    Evita: texto ilegible, flechas ambiguas, números inventados, iconos decorativos.
    """,
    "Pipeline contrastivo: 4 pares consulta-documento pasan por un encoder compartido; la matriz 4×4 de similitudes tiene la diagonal como positivos y la pérdida es entropía cruzada por filas.",
    """
    q1..q4 ─┐                              S = Q·Dᵀ/τ   d1  d2  d3  d4
            ├─► [Encoder compartido] ─► ‖·‖=1 ─► q1 [ +   -   -   - ]
    d1..d4 ─┘                                  q2 [ -   +   -   - ]   InfoNCE = CE por filas
                                               q3 [ -   -   +   - ]   (etiqueta = diagonal)
                                               q4 [ -   -   -   + ]
    """,
)
nb.md(r"""
> 👀 **Qué debes observar.** Una sola torre (pesos compartidos) para consultas y documentos, vectores normalizados, y la pérdida es **solo una entropía cruzada** cuya «clase correcta» es la diagonal: todo el aprendizaje contrastivo de esta lección son variaciones de qué se pone en las columnas.
""")

nb.md(r"""
## 2. 📐 InfoNCE, temperatura e información mutua

### Definición
Para un lote de $B$ pares $(q_i, d_i)$ con embeddings normalizados $\mathbf u_i=f(q_i)$, $\mathbf v_j=f(d_j)$:
$$\mathcal L_{\text{InfoNCE}}=-\frac1B\sum_{i=1}^{B}\log\frac{\exp(\mathbf u_i\cdot\mathbf v_i/\tau)}{\sum_{j=1}^{B}\exp(\mathbf u_i\cdot\mathbf v_j/\tau)}.$$
**Símbolos.** $B$ = tamaño del lote; $\mathbf u_i\cdot\mathbf v_j=\cos(q_i,d_j)\in[-1,1]$; $\tau>0$ = **temperatura**; el numerador es el positivo y el denominador suma el positivo y los $B-1$ negativos del lote. Si se añaden negativos duros $\mathbf v^-_m$, entran como columnas extra del denominador.

### Temperatura: qué hace con el gradiente
Con $p_{ij}=\text{softmax}_j(\mathbf u_i\cdot\mathbf v_j/\tau)$:
$$\frac{\partial\mathcal L_i}{\partial(\mathbf u_i\cdot\mathbf v_j)}=\frac1\tau\big(p_{ij}-\mathbb 1[i=j]\big).$$
Cada negativo empuja con peso $p_{ij}\propto e^{s_{ij}/\tau}$: con $\tau$ **pequeña**, casi todo el peso va al negativo **más parecido** (se concentra en los duros); con $\tau$ **grande**, todos pesan parecido y el modelo apenas distingue (Wang & Liu, 2021). Valores publicados: SimCSE $\tau=0.05$; E5 $\tau=0.01$; en `sentence-transformers`, `MultipleNegativesRankingLoss(scale=20)` equivale a $\tau=1/20=0.05$ (según su documentación: `scale = 1/temperature`).

### InfoNCE como cota de la información mutua
Sea $(x,y)\sim p(x,y)$ un par positivo y $y_2,\dots,y_K\sim p(y)$ negativos independientes. Con un «crítico» $g(x,y)=e^{f(x,y)}$ cualquiera, la pérdida con $K$ candidatos es
$\mathcal L_K=-\mathbb E\big[\log\frac{g(x,y_1)}{\sum_{k=1}^{K}g(x,y_k)}\big]$.
1. **Crítico óptimo.** Clasificar cuál de los $K$ es el positivo es un problema de Bayes: el positivo es $y_k$ con probabilidad $\propto\frac{p(y_k\mid x)}{p(y_k)}$, así que el óptimo es $g^*(x,y)\propto\frac{p(y\mid x)}{p(y)}$ (cociente de densidades).
2. **Sustituir** (Oord et al., 2018): $\mathcal L_K^{*}=\mathbb E\log\Big[1+\frac{p(y_1)}{p(y_1\mid x)}\sum_{k\ge2}\frac{p(y_k\mid x)}{p(y_k)}\Big]$.
3. **Aproximar** la suma por $K-1$ veces su esperanza: $\mathbb E_{y\sim p(y)}\big[\frac{p(y\mid x)}{p(y)}\big]=1$, así que $\mathcal L_K^*\approx\mathbb E\log\big[1+(K-1)\frac{p(y_1)}{p(y_1\mid x)}\big]$.
4. **Acotar**: para el cociente típico de un positivo ($p(y_1\mid x)\ge p(y_1)$), $\;1+(K-1)a\ge K a$ con $a=p(y_1)/p(y_1|x)\le1$, luego $\mathcal L_K^*\gtrsim\mathbb E\log\big[K\frac{p(y_1)}{p(y_1\mid x)}\big]=\log K-I(X;Y)$.

La derivación de Oord et al. es heurística en los pasos 3–4; Poole et al. (2019) demuestran la versión rigurosa: **para cualquier crítico**, $I(X;Y)\ \ge\ \log K-\mathcal L_K$.
**Consecuencias.** (a) Minimizar InfoNCE maximiza una cota inferior de la información mutua entre las dos vistas. (b) La cota **nunca supera $\log K$**: con lotes pequeños no puede «ver» más de $\log B$ nats (McAllester & Stratos, 2020, formalizan este límite). (c) Más negativos = cota más ajustada, una motivación para lotes grandes. (d) Ojo: Tschannen et al. (2020) muestran que maximizar MI **no explica por sí solo** la calidad de las representaciones; la cota es una guía, no la causa.
""")
nb.code(r'''
# Comprobación numérica con una gaussiana bivariante de MI conocida: I = -0.5·log(1 - ρ²)
def infonce_gauss(rho, K, n=4000, seed=SEED):
    """Estima log K - L_K con el crítico ÓPTIMO (log del cociente de densidades), para n anclas y K candidatos."""
    g = np.random.default_rng(seed)
    x = g.standard_normal(n)
    y_pos = rho * x + np.sqrt(1 - rho ** 2) * g.standard_normal(n)
    y = np.concatenate([y_pos[:, None], g.standard_normal((n, K - 1))], 1)       # columna 0 = positivo
    f = -(y - rho * x[:, None]) ** 2 / (2 * (1 - rho ** 2)) + y ** 2 / 2         # log p(y|x) - log p(y)
    L = -(f[:, 0] - np.log(np.exp(f - f.max(1, keepdims=True)).sum(1)) - f.max(1)).mean()
    return np.log(K) - L


rho = 0.99
I_real = -0.5 * np.log(1 - rho ** 2)
Ks = [2, 4, 8, 16, 32, 64, 128, 256, 512]
est = [infonce_gauss(rho, K) for K in Ks]
fig, ax = plt.subplots(figsize=(6.5, 3.6))
ax.plot(Ks, est, "o-", color=PAL["azul"], label="log K − L_InfoNCE (crítico óptimo)")
ax.plot(Ks, np.log(Ks), "--", color=PAL["gris"], label="techo log K")
ax.axhline(I_real, color=PAL["naranja"], label=f"I(X;Y) real = {I_real:.2f} nats")
ax.set_xscale("log", base=2); ax.set(xlabel="K (nº de candidatos = tamaño del lote)", ylabel="nats", title="InfoNCE es una cota inferior saturada en log K")
ax.legend(fontsize=8); plt.tight_layout(); plt.show()
print({K: round(e, 3) for K, e in zip(Ks, est)}, "| I real =", round(I_real, 3))
''')
nb.md(r"""
> 👀 **Qué debes observar.** La estimación sigue al techo $\log K$ (gris) mientras $\log K < I$ y se **satura** por debajo de la MI real (naranja, ≈ 1.96 nats) cuando $K$ es grande: nunca la supera. Con lotes de 8 la cota no puede pasar de $\log 8\approx2.08$ nats, aunque el modelo fuera perfecto. Esa es la razón matemática de que los embedders de producción se entrenen con lotes de miles.
""")

nb.md(r"""
## 3. Implementación desde cero: bi-encoder + InfoNCE
Tres piezas: (1) un tokenizer BPE entrenado en el corpus, (2) una torre `BiEncoder` (embeddings → 2 capas Transformer → media con máscara → L2), (3) `info_nce` con negativos en el lote, negativos duros opcionales y versión simétrica. Además, `alineacion` y `uniformidad` (sección 4).
""")
nb.code(ENC11)
nb.code(LOSS11)
nb.code(r'''
# Test: info_nce == entropía cruzada calculada a mano sobre la matriz de similitudes
torch.manual_seed(SEED)
q_, d_ = F.normalize(torch.randn(4, 8), dim=-1), F.normalize(torch.randn(4, 8), dim=-1)
S_ = q_ @ d_.T / 0.05
manual = -(torch.diag(S_) - torch.logsumexp(S_, dim=1)).mean()
print(f"info_nce={info_nce(q_, d_, 0.05):.6f} | a mano={manual:.6f}")
h_ = F.normalize(torch.randn(3, 8), dim=-1)
print("con 3 negativos duros, la matriz pasa de 4×4 a", tuple((q_ @ torch.cat([d_, h_]).T).shape))
''')
nb.code(TRAIN11)
nb.gemini(
    "video", "M11-VID-01", "La matriz B×B: cómo InfoNCE empuja positivos y negativos",
    "Anima un lote de 4 pares: matriz de similitudes, softmax por filas, efecto de la temperatura y de añadir un negativo duro como columna extra.",
    """
    Video técnico 16:9, 1080p, fondo blanco, estilo de animación de diagramas (sin personajes, sin voz en off, sin música estridente; ritmo calmado). Paleta: verde #2CA02C (positivos/diagonal), gris #6B7280 (negativos), naranja #F28E2B (negativo duro), azul #1F6FEB (texto y ejes). Tipografía sans-serif grande.
    0–5 s: aparece el título «InfoNCE con negativos en el lote» y, debajo, cuatro filas «q1 q2 q3 q4» y cuatro columnas «d1 d2 d3 d4».
    5–12 s: se rellena una matriz 4×4 de similitudes coseno con estos valores exactos (fila por fila): q1: 0.82, 0.31, 0.12, 0.78 · q2: 0.28, 0.77, 0.40, 0.05 · q3: 0.10, 0.35, 0.69, 0.66 · q4: 0.47, 0.02, 0.18, 0.80. La diagonal se colorea en verde; las celdas (q1,d4)=0.78 y (q3,d4)=0.66 parpadean en naranja con el rótulo «negativos difíciles».
    12–20 s: texto en pantalla «softmax por filas con τ = 0.05». Cada fila se transforma en probabilidades exactas: q1: 0.69, 0.00, 0.00, 0.31 · q2: 0.00, 1.00, 0.00, 0.00 · q3: 0.00, 0.00, 0.65, 0.35 · q4: 0.00, 0.00, 0.00, 1.00. Junto a cada fila aparece su pérdida −log p(diagonal): 0.37, 0.00, 0.44, 0.00; abajo «pérdida media = 0.20».
    20–27 s: texto «la misma matriz con τ = 1.0». Las filas se vuelven casi uniformes: q1: 0.33, 0.20, 0.16, 0.31 · q2: 0.22, 0.36, 0.25, 0.17 · q3: 0.17, 0.22, 0.31, 0.30 · q4: 0.26, 0.17, 0.20, 0.37; «pérdida media = 1.08». Rótulo: «τ alta: todos los negativos pesan casi igual».
    27–35 s: flechas animadas sobre una esfera pequeña a la derecha: el punto q1 se acerca a d1 (flecha verde) y se aleja sobre todo de d4 (flecha naranja más gruesa) y poco de d2, d3 (flechas grises finas). Rótulo: «el gradiente se concentra en los negativos difíciles (τ baja)».
    35–42 s: se añade a la derecha de la matriz una quinta columna naranja rotulada «h1 (negativo duro minado con BM25)», la matriz pasa a 4×5; rótulo final: «negativos duros = columnas extra del denominador».
    Evita: texto ilegible, números distintos de los indicados, transiciones rápidas, elementos decorativos.
    """,
    "Animación de una matriz 4×4 de similitudes, su softmax por filas con τ=0.05 y τ=1, el empuje sobre negativos difíciles y la adición de un negativo duro.",
    """
    S (cos)   d1   d2   d3   d4        softmax τ=0.05            τ=1.0
    q1      [0.82 0.31 0.12 0.78]  →  [0.69 0.00 0.00 0.31]   [0.33 0.20 0.16 0.31]
    q2      [0.28 0.77 0.40 0.05]  →  [0.00 1.00 0.00 0.00]   [0.22 0.36 0.25 0.17]
    q3      [0.10 0.35 0.69 0.66]  →  [0.00 0.00 0.65 0.35]   [0.17 0.22 0.31 0.30]
    q4      [0.47 0.02 0.18 0.80]  →  [0.00 0.00 0.00 1.00]   [0.26 0.17 0.20 0.37]
    pérdida media: 0.20 (τ=0.05) · 1.08 (τ=1)   + columna h1 = negativo duro
    """,
    duration="40-45 s",
)
nb.md(r"""
> 👀 **Qué debes observar.** Con $\tau=0.05$ las filas 2 y 4 ya no aportan pérdida (sus negativos son fáciles) y todo el gradiente sale de las filas 1 y 3, por culpa de un único negativo difícil cada una. Con $\tau=1$ la pérdida es alta en todas las filas pero el gradiente apenas distingue difíciles de fáciles. Los números del video salen de aplicar la fórmula de la sección 2 a esa matriz.
""")

nb.md(r"""
## 4. Laboratorio controlado: temperatura, colapso, alineación y uniformidad

Para ver efectos limpios usamos un **mundo de juguete** con verdad conocida: cada «concepto» es (acción, objeto) — p. ej. *(ordenar, lista)* — descrito en ES, EN y código con **sinónimos** distintos en consultas y documentos, y todos los documentos del concepto son relevantes (también los del otro idioma). Se entrena con 48 conceptos y se evalúa en **12 conceptos nunca vistos** (combinaciones nuevas de palabras conocidas). BM25 aquí falla por la brecha léxica y el cruce de idioma; un embedder puede aprenderlos.

**Alineación y uniformidad** (Wang & Isola, 2020), sobre la hiperesfera:
$$\mathcal L_{\text{align}}=\mathbb E_{(x,y)\sim p_{\text{pos}}}\|f(x)-f(y)\|^{2},\qquad \mathcal L_{\text{unif}}=\log\mathbb E_{x,y\sim p_{\text{data}}}e^{-2\|f(x)-f(y)\|^2}.$$
Alineación baja = los positivos están cerca; uniformidad **muy negativa** = los puntos cubren la esfera. Un **colapso** (todo al mismo punto) tiene alineación perfecta (0) y uniformidad ≈ 0: el peor caso. InfoNCE optimiza asintóticamente ambas a la vez.
""")
nb.code(LEXICON_CELL)
nb.code(SYNTH_CELL)
nb.code(TOY11)
nb.code(r'''
PASOS_LAB = 200 if FAST_DEV_RUN else 1000
grupo_toy = lambda p: concepto[p[1]]                     # evita dos pares del mismo concepto en un lote
lab = {}
t0 = time.time()
for tau in (0.02, 0.05, 0.2, 1.0):
    m, h = entrena_biencoder(toy_pares, toy_tok, pasos=PASOS_LAB, B=32, tau=tau, grupo=grupo_toy, textos=toy_txt)
    lab[f"τ={tau}"] = dict(ndcg=eval_toy(m), align=h[-1]["align"], unif=h[-1]["unif"])
m, h = entrena_biencoder(toy_pares, toy_tok, pasos=PASOS_LAB, B=32, solo_positivos=True, grupo=grupo_toy, textos=toy_txt)
lab["sin negativos (colapso)"] = dict(ndcg=eval_toy(m), align=h[-1]["align"], unif=h[-1]["unif"])
m0 = BiEncoder(len(toy_tok)).to(device)
lab["sin entrenar"] = dict(ndcg=eval_toy(m0), align=float("nan"), unif=float("nan"))
for k, v in lab.items():
    print(f"{k:24s} nDCG@10(test)={v['ndcg']:.3f} | align={v['align']:.3f} | unif={v['unif']:.3f}")
print(f"({time.time() - t0:.0f}s)")
''')
nb.code(r'''
fig, ax = plt.subplots(1, 2, figsize=(11.5, 3.8))
nombres = list(lab)
cols = [PAL["azul"]] * 4 + [PAL["naranja"], PAL["gris"]]
ax[0].bar(range(len(nombres)), [lab[n]["ndcg"] for n in nombres], color=cols)
ax[0].set_xticks(range(len(nombres)), nombres, rotation=25, ha="right"); ax[0].set(ylabel="nDCG@10 en conceptos no vistos", title="Temperatura y colapso")
for n, c in zip(nombres[:5], cols):
    ax[1].scatter(lab[n]["unif"], lab[n]["align"], s=70, color=c)
    ax[1].annotate(n, (lab[n]["unif"], lab[n]["align"]), fontsize=8, xytext=(4, 4), textcoords="offset points")
ax[1].set(xlabel="L_uniform (← más uniforme)", ylabel="L_align (↓ positivos más cerca)", title="Plano alineación–uniformidad (Wang & Isola)")
plt.tight_layout(); plt.show()
''')
nb.md(r"""
> 👀 **Qué debes observar.** (1) Hay un $\tau$ intermedio que gana (en la ejecución de referencia, $\tau=0.2$ ≈ 1.00 de nDCG@10 frente a 0.49 con $\tau=1$); $\tau=1$ no separa bien porque todos los negativos pesan igual. (2) **Sin negativos** el modelo colapsa: alineación ≈ 0 (¡perfecta!) pero uniformidad ≈ 0 y nDCG cercano al de un modelo sin entrenar. Por eso no basta con «acercar positivos»: los negativos (o un regularizador de uniformidad) son los que impiden el colapso.
> (3) En el plano, los buenos modelos están **abajo a la izquierda**: positivos cerca *y* puntos repartidos. El valor óptimo de $\tau$ depende de datos, tamaño de lote y modelo: SimCSE usó 0.05 y E5 0.01; trátalo como hiperparámetro.
""")
nb.gemini(
    "imagen", "M11-IMG-02", "Alineación y uniformidad en la hiperesfera",
    "Tres esferas que ilustran colapso, alineación sin uniformidad y el caso ideal, conectando con L_align y L_uniform.",
    """
    Diagrama técnico limpio, fondo blanco, 16:9, tres círculos grandes (esferas vistas en 2D) en fila con título encima de cada uno. Paleta: cada color es una clase de pares positivos: azul #1F6FEB, naranja #F28E2B, verde #2CA02C; gris #6B7280 para el contorno y texto.
    Esfera 1, título «Colapso»: todos los puntos (de los tres colores) amontonados en un único punto del borde. Debajo: «L_align ≈ 0 · L_uniform ≈ 0 → inútil».
    Esfera 2, título «Alineado pero no uniforme»: tres grupos compactos (azul, naranja, verde) todos apiñados en el mismo cuarto de la esfera, muy cerca unos de otros. Debajo: «positivos cerca, pero las clases se confunden».
    Esfera 3, título «Ideal (InfoNCE)»: tres grupos compactos repartidos alrededor de la esfera, separados ~120°. Debajo: «L_align bajo · L_uniform muy negativo».
    Pie común con las fórmulas: «L_align = E‖f(x) − f(y)‖² (pares positivos)» y «L_uniform = log E exp(−2‖f(x) − f(y)‖²) (pares aleatorios)».
    Evita: texto ilegible, perspectiva 3D confusa, números inventados, decoración.
    """,
    "Tres esferas: colapso en un punto, grupos alineados pero apiñados, y grupos repartidos uniformemente.",
    """
     (1) Colapso          (2) Alineado, no uniforme     (3) Ideal
        ( ●●● )              ( ●● ▲▲ ■■   )              ( ●●      ▲▲ )
     align≈0, unif≈0        positivos cerca, clases      (     ■■      )
                            apiñadas                     align bajo, unif muy negativo
    """,
)
nb.md(r"""
> 👀 **Qué debes observar.** El caso 2 es el que produce un $\tau$ demasiado alto o pocos negativos: la alineación por sí sola no garantiza que clases distintas queden lejos. Relaciónalo con la anisotropía del módulo 10: un espacio «apiñado» es anisótropo.
""")

nb.md(r"""
## 5. Negativos duros y falsos negativos
Los negativos del lote son **aleatorios**: la mayoría son fáciles y dejan de dar gradiente pronto (lo viste en el video). Los **negativos duros** son documentos parecidos a la consulta pero no relevantes; se minan con:
- **BM25** (DPR, Karpukhin et al., 2020: su mejor modelo usaba los positivos del lote + **un** negativo de BM25 por pregunta, con lotes de 128).
- **El propio modelo denso**, refrescando un índice ANN durante el entrenamiento (ANCE, Xiong et al., 2020).
- **Un cross-encoder** para filtrar falsos negativos (RocketQA, Qu et al., 2021) o **destilar** (TAS-B, Hofstätter et al., 2021).

**El peligro: falsos negativos.** El top de BM25 contiene a menudo documentos **relevantes no etiquetados**; tratarlos como negativos enseña al modelo lo contrario de lo que queremos. NV-Retriever (Moreira et al., 2024) propone filtros «conscientes del positivo»; en su configuración principal (*TopK-PercPos*) descartan los candidatos cuyo score supera el **95 % del score del positivo**.
""")
nb.code(r'''
def mina_duros(pares, bm, ids, textos, k=30, n=10, perc=0.95, mismo_grupo=None):
    """Negativos duros con BM25. perc: filtro TopK-PercPos (score < perc · score del positivo; None = sin filtro).
    mismo_grupo(did_pos, did_cand) -> True si el candidato es un falso negativo conocido (solo en el mundo de juguete)."""
    pos_idx = {d: i for i, d in enumerate(ids)}
    duros = {}
    for k_, (qt, did) in enumerate(pares):
        sc = bm.scores(tokenize_simple(qt))
        s_pos = sc[pos_idx[did]]
        cand = [ids[j] for j in np.argsort(-sc)[:k] if ids[j] != did]
        if perc is not None:
            cand = [c for c in cand if sc[pos_idx[c]] < perc * s_pos]
        if mismo_grupo is not None:
            cand = [c for c in cand if not mismo_grupo(did, c)]
        duros[k_] = cand[:n]
    return duros


toy_bm = BM25().fit([tokenize_simple(toy_txt[i]) for i in toy_ids], toy_ids)
duros_crudos = mina_duros(toy_pares, toy_bm, toy_ids, toy_txt, perc=None)
duros_limpios = mina_duros(toy_pares, toy_bm, toy_ids, toy_txt, perc=None, mismo_grupo=lambda a, b: concepto[a] == concepto[b])
fn = np.mean([np.mean([concepto[c] == concepto[toy_pares[k][1]] for c in v]) for k, v in duros_crudos.items() if v])
print(f"fracción de FALSOS negativos en el top-10 de BM25 sin filtrar: {fn:.0%}")
''')
nb.code(r'''
neg = {}
for nombre, du in (("solo en el lote", None), ("+ duros limpios", duros_limpios), ("+ duros sin filtrar", duros_crudos)):
    m, _ = entrena_biencoder(toy_pares, toy_tok, pasos=PASOS_LAB, B=16, tau=0.05, duros=du, grupo=grupo_toy, textos=toy_txt)
    neg[nombre] = eval_toy(m)
fig, ax = plt.subplots(figsize=(6.5, 3.4))
ax.bar(list(neg), list(neg.values()), color=[PAL["gris"], PAL["verde"], PAL["naranja"]])
for i, v in enumerate(neg.values()):
    ax.text(i, v, f"{v:.3f}", ha="center", va="bottom")
ax.set(ylabel="nDCG@10 (conceptos no vistos)", title="Negativos duros: limpios ayudan, falsos negativos dañan (B=16, τ=0.05)")
plt.tight_layout(); plt.show()
print({k: round(v, 3) for k, v in neg.items()})
''')
nb.md(r"""
> 👀 **Qué debes observar.** En el prototipo de referencia (mismo código, 300 pasos): solo lote 0.88 · con duros limpios 0.92 · con duros **sin filtrar** 0.84; tu ejecución imprime sus propios valores (con 200 pasos las diferencias pueden ser menores). El top de BM25 sin filtrar está lleno de documentos del **mismo concepto** (falsos negativos, mira el porcentaje impreso): usarlos como negativos es peor que no usar negativos duros. En datos reales no conoces el concepto: de ahí los filtros por score (TopK-PercPos) o por cross-encoder.
""")
nb.gemini(
    "imagen", "M11-IMG-03", "Minado de negativos duros con filtro de falsos negativos",
    "Pipeline de minado: candidatos BM25/denso, filtro consciente del positivo y negativos que entran en la pérdida.",
    """
    Diagrama técnico limpio, fondo blanco, 16:9, flujo de izquierda a derecha. Paleta: azul #1F6FEB (consulta), verde #2CA02C (positivo), naranja #F28E2B (negativos duros válidos), rojo apagado #C0392B (falsos negativos descartados), gris #6B7280 (texto secundario).
    1) Caja azul «consulta: configurar el balanceador de carga».
    2) Caja «Recuperador (BM25 o modelo denso)» que produce una lista vertical de 6 candidatos con scores exactos: «d+ (positivo) 12.0», «c1 11.8», «c2 10.9», «c3 9.1», «c4 7.5», «c5 6.2».
    3) Caja «Filtro TopK-PercPos: score < 0.95 × 12.0 = 11.4». c1 (11.8) aparece en rojo tachado con la etiqueta «posible falso negativo»; c2 (10.9), c3, c4 en naranja con «negativo duro»; c5 en gris «fácil».
    4) Caja final «InfoNCE: positivo + negativos del lote + c2, c3, c4 como columnas extra».
    Nota al pie: «Alternativas: filtrar con un cross-encoder (RocketQA) o refrescar el índice durante el entrenamiento (ANCE)».
    Evita: texto ilegible, flechas ambiguas, otros números, decoración.
    """,
    "Flujo: consulta → recuperador con 6 candidatos y scores → filtro 95 % del positivo que descarta c1 → negativos duros c2-c4 a la pérdida.",
    """
    consulta → [BM25 / denso] → d+ 12.0 | c1 11.8 | c2 10.9 | c3 9.1 | c4 7.5 | c5 6.2
             → filtro: score < 0.95·12.0 = 11.4 → c1 ✗ (posible falso negativo)
             → negativos duros: c2, c3, c4  → InfoNCE (columnas extra)
    """,
)
nb.md(r"""
> 👀 **Qué debes observar.** El candidato más parecido al positivo es el **más sospechoso**, no el mejor negativo. El umbral relativo (95 % del positivo) se adapta a cada consulta, a diferencia de un umbral absoluto.
""")

nb.md(r"""
## 6. SimCSE, DPR y la receta «débil → supervisado»
- **SimCSE no supervisado** (Gao, Yao & Chen, 2021): el positivo de una frase es **ella misma** pasada dos veces por el encoder con *dropout* distinto; los negativos, las demás frases del lote ($\tau=0.05$). Sin etiquetas. **SimCSE supervisado**: pares de inferencia natural (implicación = positivo, contradicción = negativo duro).
- **DPR** (Karpukhin et al., 2020): dos encoders BERT (pregunta y pasaje), producto escalar sobre `[CLS]`, negativos del lote + BM25.
- **Pre-entrenamiento débilmente supervisado → ajuste fino.** La receta de los embedders modernos (E5, GTE, BGE): primero cientos de millones de **pares ruidosos** extraídos de la web (título–cuerpo, pregunta–respuesta, post–comentario); E5 construyó **CCPairs, ≈ 270M pares**, con $\tau=0.01$ y prefijos `query:`/`passage:` (Wang et al., 2022). Después, un ajuste fino con datos etiquetados y negativos duros. GTE (Li et al., 2023) y BGE / C-Pack (Xiao et al., 2023) describen variantes multi-etapa del mismo esquema.

Probamos SimCSE no supervisado en el mundo de juguete (pares $(x, x)$ con dropout):
""")
nb.code(r'''
textos_s = list(toy_txt.values()) + [q["text"] for q in toy_q_train]
ids_s = {f"s{i}": x for i, x in enumerate(textos_s)}
pares_simcse = [(x, f"s{i}") for i, x in enumerate(textos_s)]            # positivo = la misma frase (dropout distinto)
m_simcse, _ = entrena_biencoder(pares_simcse, toy_tok, pasos=PASOS_LAB, B=32, tau=0.05, textos=ids_s)
print(f"nDCG@10 test · sin entrenar={lab['sin entrenar']['ndcg']:.3f} | SimCSE no supervisado={eval_toy(m_simcse):.3f} | supervisado τ=0.05={lab['τ=0.05']['ndcg']:.3f}")
''')
nb.md(r"""
> 👀 **Qué debes observar.** SimCSE sin etiquetas mejora claramente al modelo sin entrenar (aprende a ignorar ruido y a agrupar textos parecidos), pero queda muy lejos del supervisado: **no puede** aprender que «bajar» = «descargar» = «download» sin señal de pares. Por eso los embedders de producción usan pares débiles a escala web, no solo auto-supervisión.
""")

nb.md(r"""
## 7. Lotes grandes y Gradient Cache
La cota $\log K$ y la práctica dicen lo mismo: **más negativos en el lote ayudan**. Pero la memoria de activaciones crece con $B$. **Gradient Cache** (Gao et al., 2021) desacopla ambas cosas: (1) forward sin grafo de todo el lote para obtener las representaciones; (2) pérdida y gradiente **respecto a las representaciones** (barato: solo vectores); (3) re-forward por trozos con grafo y backward de $\sum_i \mathbf z_i\cdot\partial\mathcal L/\partial\mathbf z_i$. El gradiente es **exacto**; el coste es ≈ un forward extra. En `sentence-transformers` es `CachedMultipleNegativesRankingLoss`.
""")
nb.code(r'''
B_list = [4, 8, 16, 32]
por_B = {}
for B_ in B_list:
    m, _ = entrena_biencoder(toy_pares, toy_tok, pasos=PASOS_LAB, B=B_, tau=0.05, grupo=grupo_toy, textos=toy_txt)
    por_B[B_] = eval_toy(m)
fig, ax = plt.subplots(figsize=(6, 3.4))
ax.plot(B_list, list(por_B.values()), "o-", color=PAL["azul"])
ax.set_xscale("log", base=2); ax.set(xlabel="tamaño de lote B (mismo nº de pasos)", ylabel="nDCG@10 (conceptos no vistos)", title="Más negativos en el lote")
plt.tight_layout(); plt.show()
print(por_B)
''')
nb.md(r"""
> 👀 **Qué debes observar.** Con el mismo número de pasos, lotes mayores dan mejor nDCG (más negativos por paso *y* más ejemplos vistos: ambos efectos se mezclan). En el mundo de juguete el lote está limitado por el nº de conceptos de entrenamiento (48) si exigimos que no se repitan: con datos reales el límite es la **memoria**, y ahí entra Gradient Cache.
""")
nb.code(GRADCACHE)
nb.code(GC_TEST)
nb.md(r"""
> 👀 **Qué debes observar.** Diferencia del orden de $10^{-7}$: error de redondeo en float32. Gradient Cache no es una aproximación. Con *dropout* activo hay que reproducir el mismo estado aleatorio en los dos forwards (la implementación original guarda y restaura el RNG); aquí lo evitamos con `eval()`.
""")

nb.md(r"""
## 8. Políglota: tu primer embedder propio (desde cero)
Pares de entrenamiento:
- **Débiles** (sin etiquetas, como CCPairs en miniatura): primera frase del documento → documento; primera línea (firma) de cada función → función.
- **Etiquetados**: consultas de la partición de entrenamiento → su documento relevante.
Evaluamos en las consultas de **test** contra BM25 (módulo 00) y contra la misma torre sin entrenar.
""")
nb.code(r'''
def pares_debiles(docs):
    out = []
    for d in docs:
        if d["lang"] == "code":
            out.append((d["text"].split("\n")[0], d["id"]))
        else:
            fr = re.split(r"(?<=[.!?])\s+", d["text"].strip())
            if len(fr) >= 3:
                out.append((fr[0], d["id"]))
    return out


pares_poliglota = pares_debiles(docs) + [(q["text"], did) for q in q_train for did in qrels[q["qid"]]] * 5
pol_tok = entrena_tokenizer(doc_txt + [q["text"] for q in queries], vocab_size=2000)
bm25_pol = BM25().fit([tokenize_simple(t) for t in doc_txt], doc_ids)


def ndcg_pol(model, qs=None):
    qs = qs or q_test
    D, Q = codifica(model, pol_tok, doc_txt), codifica(model, pol_tok, [q["text"] for q in qs])
    run = {q["qid"]: rank_from_scores((Q @ D.T)[k].numpy(), doc_ids, 100) for k, q in enumerate(qs)}
    return evaluate(run, {q["qid"]: qrels[q["qid"]] for q in qs})["ndcg"]


ndcg_bm25 = evaluate({q["qid"]: bm25_pol.search(tokenize_simple(q["text"]), 100) for q in q_test}, {q["qid"]: qrels[q["qid"]] for q in q_test})["ndcg"]
PASOS_POL = 300 if FAST_DEV_RUN else 3000
m_pol, hist_pol = entrena_biencoder(pares_poliglota, pol_tok, pasos=PASOS_POL, B=32, tau=0.05, log_cada=50, eval_fn=ndcg_pol)
print(f"pares={len(pares_poliglota)} | BM25={ndcg_bm25:.3f} | sin entrenar={ndcg_pol(BiEncoder(len(pol_tok)).to(device)):.3f} | entrenado={ndcg_pol(m_pol):.3f}")
''')
nb.code(r'''
fig, ax = plt.subplots(1, 2, figsize=(11, 3.4))
pasos = [h["paso"] for h in hist_pol]
ax[0].plot(pasos, [h["loss"] for h in hist_pol], "o-", color=PAL["azul"]); ax[0].set(xlabel="paso", ylabel="InfoNCE", title="Pérdida de entrenamiento")
ax[1].plot(pasos, [h["ndcg"] for h in hist_pol], "o-", color=PAL["verde"], label="bi-encoder propio")
ax[1].axhline(ndcg_bm25, ls="--", color=PAL["naranja"], label=f"BM25 = {ndcg_bm25:.3f}")
ax[1].set(xlabel="paso", ylabel="nDCG@10 (test)", title="Políglota: calidad durante el entrenamiento"); ax[1].legend()
plt.tight_layout(); plt.show()
''')
nb.md(r"""
> 👀 **Qué debes observar.** La pérdida baja de forma continua, pero el nDCG de test **no** tiene por qué hacerlo: con pocas consultas etiquetadas el modelo memoriza pronto. Y en este benchmark de ítem conocido, BM25 sigue muy por encima de una torre de 2 capas entrenada minutos en CPU: lo correcto es **ajustar un modelo preentrenado** (siguiente celda) y combinar denso + BM25 (módulo 13). Construir la torre desde cero sirve para entender cada pieza, no para ganar a BM25.
""")

nb.md(r"""
## 9. Con la librería de industria: `sentence-transformers`
`MultipleNegativesRankingLoss` (MNRL) es exactamente nuestro `info_nce` con negativos en el lote (y, si el dataset trae una tercera columna, negativos duros como columnas extra). Sus piezas habituales: `BatchSamplers.NO_DUPLICATES` (evita textos repetidos en un lote, que serían falsos negativos), `scale=20` (= $1/\tau$), y `CachedMultipleNegativesRankingLoss` para lotes grandes con Gradient Cache.
""")
nb.code(ST11)
nb.code(ST_RUN)
nb.md(r"""
> 👀 **Qué debes observar.** Unos pocos minutos de MNRL suben el nDCG@10 del modelo sobre las consultas de test (en la ejecución de referencia con el mini-BERT local: 0.43 → 0.69). Con `paraphrase-multilingual-MiniLM-L12-v2` real partes de un modelo ya bueno: usa LR baja (2e-5) y vigila que no empeore en otros idiomas (*catastrophic forgetting*).
""")
nb.code(LORA11)
nb.md(r"""
> 👀 **Qué debes observar.** LoRA (Hu et al., 2021) entrena un porcentaje pequeño de parámetros (aquí ≈ 1–2 % con $r=8$ en `query`/`value`). En embedders multilingües pequeños buena parte de los parámetros está en la **tabla de embeddings** (módulo 09), que LoRA no toca: útil cuando quieres adaptar a un dominio sin alterar el vocabulario ni duplicar el modelo por cliente.
""")

nb.md(r"""
## 10. Estimación de cómputo para el modo completo
Colab cobra en **unidades de cómputo por hora** según la GPU; la tarifa vigente aparece en el panel de recursos de tu sesión (cambia con el tiempo, por eso no la fijamos aquí). Estima: **unidades ≈ horas × tarifa de tu GPU**.
""")
nb.code(r'''
def estima_horas(n_pares, epocas, tokens_por_texto, params_no_embedding, tflops_efectivos):
    """FLOPs ≈ 6 · parámetros · tokens (forward + backward), con 2 textos por par (consulta y documento)."""
    tokens = n_pares * epocas * 2 * tokens_por_texto
    return 6 * params_no_embedding * tokens / (tflops_efectivos * 1e12) / 3600


# Ejemplo: 1M de pares, 1 época, 128 tokens, un encoder de ~21M parámetros fuera de la tabla de embeddings,
# y 20 TFLOP/s efectivos (orden de magnitud para una L4 con bf16 y buena utilización; mide el tuyo con el throughput real)
h = estima_horas(1_000_000, 1, 128, 21e6, 20)
print(f"≈ {h:.2f} h de cómputo puro; en la práctica multiplica por 2–3 (carga de datos, evaluación, utilización real).")
print("unidades de Colab ≈ horas_reales × (unidades/hora que muestra tu sesión para esa GPU)")
''')

nb.md(r"""
## Mapa de madurez (a oct-2026)

| Técnica | Madurez | Quién la usa (verificable) | Fuente |
|---|---|---|---|
| InfoNCE con negativos en el lote | 🟢 sólido | E5, GTE, BGE, Nomic Embed, Qwen3-Embedding (según sus informes técnicos) | Oord et al. 2018; Wang et al. 2022; Li et al. 2023; Xiao et al. 2023; Nussbaum et al. 2024; Zhang et al. 2025 |
| Negativos duros con BM25 / denso | 🟢 sólido | DPR (BM25), ANCE (denso) | Karpukhin et al. 2020; Xiong et al. 2020 |
| Filtros de falsos negativos (cross-encoder, TopK-PercPos) | 🟡 emergente → común | RocketQA; NV-Retriever (NVIDIA) | Qu et al. 2021; Moreira et al. 2024 |
| Pre-entrenamiento débil → ajuste fino | 🟢 sólido | E5 (CCPairs ≈ 270M pares), GTE, BGE | Wang et al. 2022; Li et al. 2023; Xiao et al. 2023 |
| SimCSE no supervisado | 🟡 útil sin etiquetas; superado por pares débiles | — | Gao et al. 2021 |
| Gradient Cache / lotes grandes | 🟢 sólido | `CachedMultipleNegativesRankingLoss` (sentence-transformers) | Gao, Zhang et al. 2021 |
| LoRA para embedders | 🟡 emergente | integración PEFT en sentence-transformers (`add_adapter`) | Hu et al. 2021 |
| Análisis alineación/uniformidad | 🟢 herramienta de diagnóstico estándar | SimCSE lo usa para analizar sus modelos | Wang & Isola 2020; Gao et al. 2021 |
""")
nb.md(r"""
## 🏭 En producción
- **Escala de datos.** E5 entrenó con ≈ 270M pares débiles (CCPairs) antes del ajuste supervisado; la calidad de un embedder moderno depende más de la **curación de pares** y del minado de negativos que de la arquitectura (ver informes de GTE, BGE/C-Pack, Nomic Embed, Qwen3-Embedding).
- **Falsos negativos a escala.** NV-Retriever (NVIDIA) documenta que el minado sin filtro introduce falsos negativos y propone filtros relativos al positivo (95 % en su configuración principal).
- **Memoria.** Los lotes grandes se consiguen con Gradient Cache (o con *data parallel* + reunir embeddings entre GPUs); en sentence-transformers: `CachedMultipleNegativesRankingLoss`.
- **Prefijos e instrucciones** (módulo 10) se fijan **durante** este entrenamiento: qué prefijo usa cada lado es parte del contrato del modelo.
- **Para Políglota:** el plan realista es ajustar un modelo multilingüe preentrenado con MNRL + negativos duros filtrados sobre pares propios (documentación técnica, docstrings↔código), y combinarlo con BM25 (módulo 13). El módulo 12 compara contra embedders comerciales y abiertos.
""")
nb.md(r"""
## 🧠 Secretos de la élite
1. **El candidato más parecido es el más sospechoso.** En nuestro laboratorio, los negativos de BM25 sin filtrar bajaron el nDCG de 0.88 a 0.84 y los filtrados lo subieron a 0.92 (prototipo de 300 pasos); en Políglota real el efecto fue pequeño (proyecto). Filtra siempre (umbral relativo al positivo, cross-encoder o deduplicación).
2. **InfoNCE se satura en $\log B$.** Lo comprobaste numéricamente: con lotes pequeños la señal está acotada; lotes grandes (o Gradient Cache, gradiente exacto) son una palanca de calidad, no solo de velocidad.
3. **Sin negativos hay colapso.** Alineación perfecta + uniformidad nula = modelo inútil; vigila $\mathcal L_{\text{unif}}$ durante el entrenamiento como alarma barata.
4. **$\tau$ es un hiperparámetro de primer orden** (0.05 SimCSE, 0.01 E5, `scale=20` en MNRL): un barrido de 4 valores cambió el nDCG de 0.49 a ≈ 1.00 en el laboratorio.
5. **Evita duplicados en el lote.** Dos pares que comparten documento o concepto se vuelven falsos negativos mutuos: `BatchSamplers.NO_DUPLICATES` o un muestreador por grupo.
6. **La pérdida de entrenamiento no es tu métrica.** En Políglota la pérdida bajaba mientras el nDCG de test se estancaba: evalúa en retrieval real cada pocos pasos.
7. **En benchmarks de ítem conocido, BM25 es durísimo.** Un denso pequeño entrenado desde cero no le gana; ajusta un preentrenado y combina (híbrido), y construye consultas no léxicas en tu *golden set* (módulo 15).
""")
nb.md(r"""
## ⚠️ Errores comunes
- Olvidar normalizar los embeddings cuando la pérdida asume coseno (o normalizar cuando el modelo se entrenó con producto escalar).
- Usar $\tau=1$ «por defecto» con coseno: los logits quedan en $[-1,1]$ y el softmax casi no distingue.
- Minar negativos duros sin filtrar falsos negativos.
- Lotes con duplicados (mismo documento positivo para dos consultas del lote).
- Evaluar con las mismas consultas con que se entrenó o eligió $\tau$.
- Implementar Gradient Cache con *dropout* sin reproducir el estado aleatorio entre los dos forwards.
- Ajustar un modelo preentrenado con LR alta y destruir su multilingüismo (*catastrophic forgetting*).
""")
nb.md(r"""
## Autoevaluación
<details><summary><b>1. (Cálculo)</b> Con un lote de $B=64$ y sin negativos extra, ¿cuál es el máximo de información mutua (en nats) que puede certificar InfoNCE? ¿Y con $B=4096$?</summary>

$\log 64\approx4.16$ nats; $\log 4096\approx8.32$ nats.
</details>
<details><summary><b>2. (Cálculo)</b> Una fila tiene similitudes coseno [0.80 (positivo), 0.78, 0.20] y $\tau=0.05$. ¿Qué probabilidad asigna el softmax al positivo y cuál es su pérdida?</summary>

Logits: 16, 15.6, 4. $p=e^{16}/(e^{16}+e^{15.6}+e^{4})\approx 1/(1+e^{-0.4})\approx0.599$; pérdida $-\log0.599\approx0.51$. Casi todo el gradiente lo genera el negativo de 0.78.
</details>
<details><summary><b>3. (Diagnóstico)</b> Tras entrenar, la pérdida es muy baja, la alineación ≈ 0 y la uniformidad ≈ 0, y el nDCG es pésimo. ¿Qué ha pasado y dónde buscas el bug?</summary>

Colapso: todos los embeddings son (casi) iguales. Con negativos de verdad en el denominador, un modelo colapsado tendría pérdida ≈ $\log B$ (todas las columnas empatan), así que una pérdida **muy baja** indica que los negativos no entran en la pérdida: pérdida solo de positivos (como `solo_positivos`), máscara que anula el denominador, o un lote en el que cada consulta solo «compite» consigo misma (p. ej. $B=1$). Una temperatura enorme también deja mala uniformidad, pero entonces la pérdida se queda cerca de $\log B$, no baja.
</details>
<details><summary><b>4. (Diagnóstico)</b> Al añadir negativos duros de BM25 el nDCG baja. ¿Qué compruebas antes de descartarlos?</summary>

La tasa de falsos negativos: revisa a mano una muestra del top de BM25 y aplica un filtro relativo al positivo (TopK-PercPos) o un cross-encoder; prueba también a introducirlos después de un calentamiento con negativos aleatorios.
</details>
<details><summary><b>5. (Transferencia)</b> En tu *two-tower* de recsys con negativos en el lote, los ítems populares salen demasiado poco recomendados. ¿Qué tiene que ver con este módulo y qué corrección aplicas?</summary>

Los populares aparecen más a menudo como negativos en el lote y se penalizan de más (sesgo de muestreo). Corrección logQ: restar $\log Q(\text{ítem})$ (probabilidad de muestreo) al logit, como en `recsys-course/08_deep_retrieval_ann`.
</details>
<details><summary><b>6.</b> ¿Por qué Gradient Cache da el gradiente exacto y no una aproximación?</summary>

Porque la pérdida solo depende de los parámetros a través de las representaciones: $\partial\mathcal L/\partial\theta=\sum_i(\partial\mathcal L/\partial\mathbf z_i)(\partial\mathbf z_i/\partial\theta)$. El primer factor se calcula con todo el lote; el segundo, por trozos.
</details>
<details><summary><b>7. (Transferencia)</b> Políglota quiere añadir búsqueda «docstring → código». ¿Qué pares débiles y qué negativos duros usarías?</summary>

Pares: (primera frase del docstring, función sin docstring) y (nombre de la función partido en palabras, cuerpo). Negativos duros: funciones del mismo módulo/repositorio con identificadores parecidos, filtradas para no incluir duplicados o *forks* del mismo código.
</details>
""")
nb.md(r"""
## Referencias
- van den Oord, A., Li, Y., & Vinyals, O. (2018). *Representation Learning with Contrastive Predictive Coding.* [arXiv:1807.03748](https://arxiv.org/abs/1807.03748)
- Poole, B., Ozair, S., van den Oord, A., et al. (2019). *On Variational Bounds of Mutual Information.* ICML. [arXiv:1905.06922](https://arxiv.org/abs/1905.06922)
- McAllester, D., & Stratos, K. (2020). *Formal Limitations on the Measurement of Mutual Information.* AISTATS. [arXiv:1811.04251](https://arxiv.org/abs/1811.04251)
- Tschannen, M., Djolonga, J., Rubenstein, P. K., et al. (2020). *On Mutual Information Maximization for Representation Learning.* ICLR. [arXiv:1907.13625](https://arxiv.org/abs/1907.13625)
- Wang, T., & Isola, P. (2020). *Understanding Contrastive Representation Learning through Alignment and Uniformity on the Hypersphere.* ICML. [arXiv:2005.10242](https://arxiv.org/abs/2005.10242)
- Wang, F., & Liu, H. (2021). *Understanding the Behaviour of Contrastive Loss.* CVPR. [arXiv:2012.09740](https://arxiv.org/abs/2012.09740)
- Chen, T., Kornblith, S., Norouzi, M., & Hinton, G. (2020). *A Simple Framework for Contrastive Learning of Visual Representations* (SimCLR). [arXiv:2002.05709](https://arxiv.org/abs/2002.05709)
- Henderson, M., Al-Rfou, R., Strope, B., et al. (2017). *Efficient Natural Language Response Suggestion for Smart Reply.* [arXiv:1705.00652](https://arxiv.org/abs/1705.00652)
- Gao, T., Yao, X., & Chen, D. (2021). *SimCSE: Simple Contrastive Learning of Sentence Embeddings.* EMNLP. [arXiv:2104.08821](https://arxiv.org/abs/2104.08821)
- Karpukhin, V., Oğuz, B., Min, S., et al. (2020). *Dense Passage Retrieval for Open-Domain Question Answering.* EMNLP. [arXiv:2004.04906](https://arxiv.org/abs/2004.04906)
- Xiong, L., Xiong, C., Li, Y., et al. (2020). *Approximate Nearest Neighbor Negative Contrastive Learning for Dense Text Retrieval* (ANCE). [arXiv:2007.00808](https://arxiv.org/abs/2007.00808)
- Qu, Y., Ding, Y., Liu, J., et al. (2021). *RocketQA.* NAACL. [arXiv:2010.08191](https://arxiv.org/abs/2010.08191)
- Hofstätter, S., Lin, S.-C., Yang, J.-H., et al. (2021). *Efficiently Teaching an Effective Dense Retriever with Balanced Topic Aware Sampling* (TAS-B). [arXiv:2104.06967](https://arxiv.org/abs/2104.06967)
- Moreira, G. de S. P., Osmulski, R., Xu, M., et al. (2024). *NV-Retriever: Improving text embedding models with effective hard-negative mining.* [arXiv:2407.15831](https://arxiv.org/abs/2407.15831)
- Robinson, J., Chuang, C.-Y., Sra, S., & Jegelka, S. (2021). *Contrastive Learning with Hard Negative Samples.* ICLR. [arXiv:2010.04592](https://arxiv.org/abs/2010.04592)
- Gao, L., Zhang, Y., Han, J., & Callan, J. (2021). *Scaling Deep Contrastive Learning Batch Size under Memory Limited Setup* (Gradient Cache). [arXiv:2101.06983](https://arxiv.org/abs/2101.06983)
- Wang, L., Yang, N., Huang, X., et al. (2022). *Text Embeddings by Weakly-Supervised Contrastive Pre-training* (E5). [arXiv:2212.03533](https://arxiv.org/abs/2212.03533)
- Li, Z., Zhang, X., Zhang, Y., et al. (2023). *Towards General Text Embeddings with Multi-stage Contrastive Learning* (GTE). [arXiv:2308.03281](https://arxiv.org/abs/2308.03281)
- Xiao, S., Liu, Z., Zhang, P., et al. (2023). *C-Pack: Packed Resources For General Chinese Embeddings* (BGE). [arXiv:2309.07597](https://arxiv.org/abs/2309.07597)
- Nussbaum, Z., Morris, J. X., Duderstadt, B., et al. (2024). *Nomic Embed: Training a Reproducible Long Context Text Embedder.* [arXiv:2402.01613](https://arxiv.org/abs/2402.01613)
- Zhang, Y., Li, M., Long, D., et al. (2025). *Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models.* [arXiv:2506.05176](https://arxiv.org/abs/2506.05176)
- Hu, E. J., Shen, Y., Wallis, P., et al. (2021). *LoRA: Low-Rank Adaptation of Large Language Models.* [arXiv:2106.09685](https://arxiv.org/abs/2106.09685)
- Librería: sentence-transformers (`MultipleNegativesRankingLoss`, `CachedMultipleNegativesRankingLoss`, `BatchSamplers.NO_DUPLICATES`, `mine_hard_negatives`): https://pypi.org/project/sentence-transformers/

## Siguiente módulo
**12 · Embedders modernos**: familias E5/BGE/GTE/Qwen3-Embedding/EmbeddingGemma, LLMs como embedders, Matryoshka y cuantización, y cómo elegir uno para Políglota frente al que acabas de entrenar.
""")
nb.save(LESSON)

# ════════════════════════════════════════════════════════════════════════════════════════
#  PROYECTO 11
# ════════════════════════════════════════════════════════════════════════════════════════
pj = Notebook("Proyecto 11 · Tu embedder ES/EN con negativos duros", colab_path=PROJECT, gpu=True)
pj.md(pj.badge() + r"""
# Proyecto 11 · Entrena el embedder de Políglota con negativos duros y mídelo contra baselines

| | |
|---|---|
| **Nivel** | 🟠 Avanzado |
| **Duración** | ≈ 2.5 h |
| **Cómputo** | `FAST_DEV_RUN=True`: CPU/T4, ≈ 5 min. Modo completo (`FAST_DEV_RUN=False`, 10× pasos y corpus mayor): L4 recomendada; unidades ≈ horas reales × tarifa de tu sesión |
| **Requisitos** | Lección 11 |

## Contexto de negocio
Producto quiere que **Políglota Labs** deje de depender de embedders ajenos. Tu *tech lead* te pide un primer embedder propio ES/EN/código, entrenado desde cero con InfoNCE, **pares débiles** extraídos del corpus y las consultas etiquetadas de entrenamiento, y una ablación honesta: ¿ayudan los **negativos duros** minados con BM25 (con filtro de falsos negativos)? ¿Cómo queda frente a BM25 y frente a la torre sin entrenar?

**Conexión.** Usa el corpus/métricas del 00 y el pooling del 10; el embedder resultante se compara en el 12 con embedders modernos y se combina con BM25 en el 13.

## Dataset
Corpus Políglota (`carga_corpus`); consultas partidas ~50/50 en entrenamiento y test de forma determinista.

## Entregables y rúbrica
Umbrales calibrados con la solución de referencia (semilla 42, `FAST_DEV_RUN=True`, corpus sintético + stdlib: lo que pudo ejecutarse al construir el curso). Con datos reales, ejecuta la solución y usa sus números menos el margen.

| # | Entregable | Criterio |
|---|---|---|
| R1 | `info_nce(q, d, tau, d_extra, simetrica)` | coincide con la entropía cruzada calculada a mano (< 1e-5), con y sin negativos extra |
| R2 | `pares_entrenamiento(docs, q_train)` | ≥ 90 % de los documentos producen un par débil; incluye todos los pares etiquetados |
| R3 | `mina_duros(pares, perc=0.95)` | ningún negativo con score BM25 ≥ 0.95 × score del positivo; ≥ 50 % de los pares con ≥ 1 negativo |
| R4 | Embedder entrenado (solo negativos del lote) | nDCG@10 test ≥ torre sin entrenar + 0.10 |
| R5 | Variante con negativos duros | reportada; nDCG@10 test ≥ la de solo-lote − 0.15 (ver nota de calibración tras la solución) |
| R6 | Tabla final BM25 / sin entrenar / solo lote / + duros, y 4–5 frases de análisis | impresa |
""")
pj.code(SETUP11)
pj.md("### Utilidades (corpus, métricas, BM25 y bi-encoder de la lección). No hace falta modificarlas.")
for _src in src_corpus_cells():
    pj.code(_src)
pj.code(SRC_METRICS)
pj.code(SRC_BM25)
pj.code(CORPUS11)
pj.code(ENC11)
pj.code(r'''
def alineacion(x, y, alpha=2):
    return (x - y).norm(dim=1).pow(alpha).mean().item()


def uniformidad(x, t=2):
    return torch.pdist(x, p=2).pow(2).mul(-t).exp().mean().log().item()
''')
pj.code(TRAIN11)
pj.code(r'''
pol_tok = entrena_tokenizer(doc_txt + [q["text"] for q in queries], vocab_size=2000)
bm25_pol = BM25().fit([tokenize_simple(t) for t in doc_txt], doc_ids)
PASOS = 300 if FAST_DEV_RUN else 3000


def ndcg_test(model):
    D, Q = codifica(model, pol_tok, doc_txt), codifica(model, pol_tok, [q["text"] for q in q_test])
    run = {q["qid"]: rank_from_scores((Q @ D.T)[k].numpy(), doc_ids, 100) for k, q in enumerate(q_test)}
    return evaluate(run, {q["qid"]: qrels[q["qid"]] for q in q_test})["ndcg"]
''')

pj.md(r"""
## TODO 1 · `info_nce`
Positivo de `q[i]` = `d[i]`; los demás `d[j]` del lote son negativos; `d_extra` (M, dim) se añade como columnas; `simetrica=True` promedia con la dirección documento→consulta. `q` y `d` llegan ya normalizados.

<details><summary>🪜 Pista 1</summary>Es una entropía cruzada sobre la matriz de similitudes `q @ D.T / tau`, con etiquetas `0..B-1`.</details>
<details><summary>🪜 Pista 2</summary>`D = torch.cat([d, d_extra])`; `F.cross_entropy(q @ D.T / tau, torch.arange(B))`; para la simétrica, `F.cross_entropy(d @ q.T / tau, y)` (sin los extra).</details>
""")
pj.code(r'''
def info_nce(q, d, tau=0.05, d_extra=None, simetrica=False):
    # TODO 1
    raise NotImplementedError


def test_info_nce():
    torch.manual_seed(0)
    q, d, h = (F.normalize(torch.randn(n, 8), dim=-1) for n in (4, 4, 3))
    S = q @ torch.cat([d, h]).T / 0.05
    manual = -(S[torch.arange(4), torch.arange(4)] - torch.logsumexp(S, 1)).mean()
    assert abs(info_nce(q, d, 0.05, h) - manual) < 1e-5
    S2 = q @ d.T / 0.05
    assert abs(info_nce(q, d, 0.05) + (torch.diag(S2) - torch.logsumexp(S2, 1)).mean()) < 1e-5
    return True


try:
    R1 = test_info_nce(); print("✅ R1")
except NotImplementedError:
    R1 = False; print("⏳ TODO 1 pendiente")
''')

pj.md(r"""
## TODO 2 · Pares de entrenamiento
- **Débiles**: para prosa, (primera frase, id del documento) si el documento tiene ≥ 3 frases; para código, (primera línea, id).
- **Etiquetados**: (texto de la consulta, id relevante) para cada consulta de `q_train`, **repetidos 5 veces** (son pocos y valiosos).

<details><summary>🪜 Pista 1</summary>`re.split(r"(?<=[.!?])\s+", texto)` parte en frases. Es la misma idea que CCPairs (título → cuerpo) a escala diminuta.</details>
""")
pj.code(r'''
def pares_entrenamiento(docs, q_train):
    # TODO 2: devuelve (pares, n_debiles)
    raise NotImplementedError
''')

pj.md(r"""
## TODO 3 · Negativos duros con filtro TopK-PercPos
Para cada par, toma el top-30 de BM25 de su texto, quita el positivo, quita los candidatos con score ≥ `perc` × score del positivo (posibles falsos negativos) y quédate con hasta 10. Devuelve `{índice_del_par: [ids]}`.

<details><summary>🪜 Pista 1</summary>`sc = bm25_pol.scores(tokenize_simple(texto))`; el score del positivo es `sc[doc_ids.index(did)]` (precalcula un dict id → posición).</details>
""")
pj.code(r'''
def mina_duros(pares, perc=0.95, k=30, n=10):
    # TODO 3
    raise NotImplementedError
''')

pj.md(r"""
## TODO 4 · Entrena, compara y comprueba la rúbrica
La celda está escrita: entrena la variante solo-lote y la variante con negativos duros (mismos pasos, $\tau=0.05$, $B=32$), mide nDCG@10 en test y evalúa la rúbrica. Después escribe tu análisis (4–5 frases): ¿por qué crees que los negativos duros ayudan o no en este corpus? Mira cuántos negativos por par sobreviven al filtro y qué tipo de documentos son.
""")
pj.code(r'''
def experimento():
    pares, n_deb = pares_entrenamiento(docs, q_train)
    duros = mina_duros(pares)
    base = ndcg_test(BiEncoder(len(pol_tok)).to(device))
    bm = evaluate({q["qid"]: bm25_pol.search(tokenize_simple(q["text"]), 100) for q in q_test}, {q["qid"]: qrels[q["qid"]] for q in q_test})["ndcg"]
    m1, h1 = entrena_biencoder(pares, pol_tok, pasos=PASOS, B=32, tau=0.05)
    m2, h2 = entrena_biencoder(pares, pol_tok, pasos=PASOS, B=32, tau=0.05, duros=duros)
    r = dict(bm25=bm, sin_entrenar=base, solo_lote=ndcg_test(m1), con_duros=ndcg_test(m2),
             unif_lote=h1[-1]["unif"], unif_duros=h2[-1]["unif"])
    pos_of = {d: i for i, d in enumerate(doc_ids)}
    viol = 0
    for k_, cand in duros.items():
        sc = bm25_pol.scores(tokenize_simple(pares[k_][0]))
        viol += sum(sc[pos_of[c]] >= 0.95 * sc[pos_of[pares[k_][1]]] for c in cand)
    etiquetados = {(q["text"], did) for q in q_train for did in qrels[q["qid"]]}
    checks = {"R1 info_nce": R1,
              "R2 pares": n_deb >= 0.9 * len(docs) and etiquetados <= set(pares),
              "R3 duros filtrados": viol == 0 and np.mean([len(v) > 0 for v in duros.values()]) >= 0.5,
              "R4 entrenado ≥ sin entrenar + 0.10": r["solo_lote"] >= r["sin_entrenar"] + 0.10,
              "R5 con duros ≥ solo lote − 0.15": r["con_duros"] >= r["solo_lote"] - 0.15,
              "R6 tabla": True}
    print(f"pares={len(pares)} (débiles={n_deb}) | pares con ≥1 duro={np.mean([len(v) > 0 for v in duros.values()]):.0%}")
    for k_, v_ in r.items():
        print(f"   {k_:14s} {v_:.3f}")
    for k_, ok in checks.items():
        print(("✅ " if ok else "❌ ") + k_)
    return r


try:
    resultado = experimento()
except NotImplementedError:
    print("⏳ Completa los TODO 1–3.")
''')
pj.md(r"""
## Retos extra
1. **Curriculum**: entrena 150 pasos solo-lote y después 150 con negativos duros. ¿Cambia la conclusión?
2. **Negativos duros densos (ANCE)**: mina con tu propio modelo tras 150 pasos y re-entrena.
3. **Barrido de τ** ∈ {0.02, 0.05, 0.1, 0.2} y pérdida simétrica.
4. **sentence-transformers**: repite con `MultipleNegativesRankingLoss` sobre un modelo preentrenado (si tienes hub) usando un dataset `(anchor, positive, negative)` con tus negativos duros, y `CachedMultipleNegativesRankingLoss` con lote 256.
5. **Intervalos de confianza** (módulo 15): bootstrap por consulta de la diferencia solo-lote vs + duros.

## Reflexión
- ¿Qué parte de tu resultado se debe al tipo de benchmark (ítem conocido con fuerte solapamiento léxico)?
- ¿Cómo construirías consultas no léxicas para que el *golden set* premie lo que un embedder hace mejor que BM25?
- ¿Qué cambiarías para entrenar con millones de pares (muestreo, deduplicación, filtros, cómputo)?
""")
pj.md(r"""
---
## ⛔ SPOILER — intenta resolverlo primero
Solución de referencia completa.
""")
pj.code(r'''
def info_nce(q, d, tau=0.05, d_extra=None, simetrica=False):
    D = d if d_extra is None else torch.cat([d, d_extra])
    y = torch.arange(q.shape[0], device=q.device)
    loss = F.cross_entropy(q @ D.T / tau, y)
    if simetrica:
        loss = (loss + F.cross_entropy(d @ q.T / tau, y)) / 2
    return loss


def pares_entrenamiento(docs, q_train):
    debiles = []
    for d in docs:
        if d["lang"] == "code":
            debiles.append((d["text"].split("\n")[0], d["id"]))
        else:
            fr = re.split(r"(?<=[.!?])\s+", d["text"].strip())
            if len(fr) >= 3:
                debiles.append((fr[0], d["id"]))
    etiquetados = [(q["text"], did) for q in q_train for did in qrels[q["qid"]]]
    return debiles + etiquetados * 5, len(debiles)


def mina_duros(pares, perc=0.95, k=30, n=10):
    pos_of = {d: i for i, d in enumerate(doc_ids)}
    duros = {}
    for i, (texto, did) in enumerate(pares):
        sc = bm25_pol.scores(tokenize_simple(texto))
        umbral = perc * sc[pos_of[did]]
        duros[i] = [doc_ids[j] for j in np.argsort(-sc)[:k] if doc_ids[j] != did and sc[j] < umbral][:n]
    return duros


R1 = test_info_nce()
resultado = experimento()
''')
pj.md(r"""
> **Nota de calibración.** Ejecución de referencia (fallback sintético + stdlib, 300 pasos en CPU): BM25 0.866 · sin entrenar 0.342 · solo lote 0.502 · con duros 0.524 (nDCG@10 test). En un prototipo con 400 pasos los duros quedaron, en cambio, 0.09 por **debajo**: el efecto es pequeño e inestable en este corpus, por eso R5 solo exige no perder más de 0.15. Hipótesis para tu análisis: los documentos sintéticos comparten plantillas y los «duros» que sobreviven al filtro son casi paráfrasis del positivo con otra herramienta o aspecto; con pocos pasos el modelo aún no domina los negativos fáciles; y la evaluación de ítem conocido premia el solapamiento léxico (BM25 sigue muy por encima). El umbral refleja lo medido, no lo deseado.
""")
pj.save(PROJECT)

README = r"""# Módulo 11 · Aprendizaje contrastivo para embeddings

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 6 h (lección ≈ 3.5 h + proyecto ≈ 2.5 h) · **Cómputo:** `FAST_DEV_RUN` en CPU/T4 (≈ 10–12 min la lección); modo completo con L4/A100 (unidades ≈ horas reales × tarifa de tu sesión de Colab; la lección incluye un estimador de horas por FLOPs)

| Archivo | Contenido |
|---|---|
| [`11_aprendizaje_contrastivo.ipynb`](11_aprendizaje_contrastivo.ipynb) | Lección: InfoNCE y temperatura (gradiente) · derivación de la cota de información mutua y comprobación numérica con gaussianas (saturación en log K) · bi-encoder e InfoNCE desde cero (negativos en el lote, duros, simétrica) · laboratorio controlado (mundo de juguete ES/EN/código): barrido de τ, colapso, alineación/uniformidad, negativos duros limpios vs falsos negativos, tamaño de lote · SimCSE, DPR, débil → supervisado (E5/GTE/BGE) · Gradient Cache desde cero con verificación del gradiente · embedder propio de Políglota · sentence-transformers con MNRL y NO_DUPLICATES · LoRA con PEFT · estimación de cómputo |
| [`11_proyecto_aprendizaje_contrastivo.ipynb`](11_proyecto_aprendizaje_contrastivo.ipynb) | Proyecto Políglota: embedder propio entrenado con pares débiles + etiquetados y negativos duros BM25 filtrados (TopK-PercPos), comparado con BM25 y con la torre sin entrenar |
| `assets/` | Recursos de Gemini: `M11-IMG-01`, `M11-IMG-02`, `M11-IMG-03` y el video `M11-VID-01` |

## Datos y modelos
Corpus Políglota canónico (módulo 00) + «mundo de juguete» sintético con verdad conocida para los experimentos controlados (`_tools/builders/a4_common.py`). sentence-transformers sobre `paraphrase-multilingual-MiniLM-L12-v2` si hay hub; si no, un mini-BERT local sin preentrenar (fallback).

## Estado de pruebas (entorno de autoría)
Hugging Face bloqueado: lección y proyecto ejecutados completos con el corpus sintético + stdlib, el mundo de juguete y el fallback local de sentence-transformers. No se probó con modelos ni datos reales, ni en GPU. Umbrales de la rúbrica calibrados con esa ejecución.

## Lecturas clave
Oord et al. 2018 · Poole et al. 2019 · Wang & Isola 2020 · Gao, Yao & Chen 2021 (SimCSE) · Karpukhin et al. 2020 (DPR) · Wang et al. 2022 (E5) · Moreira et al. 2024 (NV-Retriever) · Gao et al. 2021 (Gradient Cache).

Los notebooks se generan con `python tokenization-embeddings-course/_tools/builders/build_11.py` (desde la raíz del repo).
"""
(ROOT / MOD / "README.md").write_text(README, encoding="utf-8")
(ROOT / MOD / "assets").mkdir(exist_ok=True)
(ROOT / MOD / "assets" / ".gitkeep").touch()
print("OK README y assets/")
