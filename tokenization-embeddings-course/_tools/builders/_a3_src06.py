"""Celdas de código del módulo 06 (cadenas). Las usa build_06.py."""

PIP = "!pip install -q torch numpy matplotlib tokenizers transformers datasets"

SETUP_EXTRA = r'''
import re
import matplotlib.pyplot as plt
import torch.nn as nn, torch.nn.functional as F
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": .25,
                     "axes.spines.top": False, "axes.spines.right": False})
AZUL, NARANJA, VERDE, GRIS = "#1F6FEB", "#F28E2B", "#2CA02C", "#6B7280"
'''

DATA = r'''
corp = carga_corpus(FAST_DEV_RUN)
print("fuente del corpus:", corp["source"], "| docs:", len(corp["docs"]))
rng = random.Random(SEED)
docs = corp["docs"][:]; rng.shuffle(docs)
cut = int(0.9 * len(docs))
DOCS_TR, DOCS_VA = docs[:cut], docs[cut:]
MAX_CHARS = 1500 if FAST_DEV_RUN else 6000
LIMITE_BYTES = None if FAST_DEV_RUN else 3_000_000        # el modelo n-grama es Python puro: acota el modo completo

def texto(ds):
    return "\n\n".join(d["text"][:MAX_CHARS] for d in ds)

TXT_TR, TXT_VA = texto(DOCS_TR), texto(DOCS_VA)
TR = np.frombuffer(TXT_TR.encode("utf-8"), dtype=np.uint8).copy()[:LIMITE_BYTES]
VA = np.frombuffer(TXT_VA.encode("utf-8"), dtype=np.uint8).copy()[:LIMITE_BYTES]
print(f"bytes train={len(TR):,} | val={len(VA):,}")
for lang in ["es", "en", "code"]:
    t = "".join(d["text"][:MAX_CHARS] for d in DOCS_TR if d["lang"] == lang)
    print(f"{lang:>4}: {len(t):>8,} chars -> {len(t.encode()):>8,} bytes  ({len(t.encode())/max(1, len(t)):.3f} bytes/char)")
'''

FLOPS = r'''
def flops_capa(d, ctx, ffn=4):
    """FLOPs (forward) de UNA capa transformer por posición: QKVO (4d^2) + FFN (2*ffn*d^2) + atención causal (~ctx/2)."""
    return 2 * (4 * d * d + 2 * ffn * d * d) + 4 * (ctx / 2) * d

def flops_por_byte(modelo, d_g=4096, L_g=32, ctx_bytes=8192, vocab_bpe=128_000, bpt=4.4, ps=4.5,
                   d_l=1024, L_enc=1, L_dec=6, ventana=512):
    """FLOPs de forward POR BYTE de texto. Config ILUSTRATIVA tipo 8B (NO es la del paper)."""
    if modelo == "bpe":      # un paso del transformer grande por token + proyección a un vocabulario grande
        return (L_g * flops_capa(d_g, ctx_bytes / bpt) + 2 * d_g * vocab_bpe) / bpt
    if modelo == "bytes":    # transformer isotrópico: un paso por byte, atención sobre todos los bytes
        return L_g * flops_capa(d_g, ctx_bytes) + 2 * d_g * 256
    if modelo == "blt":      # global (1 paso por parche) + modelos locales (1 paso por byte) + atenciones cruzadas
        glob = L_g * flops_capa(d_g, ctx_bytes / ps) / ps
        local = (L_enc + L_dec) * flops_capa(d_l, ventana) + 2 * d_l * 256
        cross = 4 * d_l * d_g
        return glob + local + cross
    raise ValueError(modelo)

base = flops_por_byte("bpe")
print(f"{'BPE (4.4 B/token, vocab 128K)':38s} {base/1e9:6.2f} GFLOPs/byte  (1.00x)")
print(f"{'Bytes isotrópico (1 B/paso)':38s} {flops_por_byte('bytes')/1e9:6.2f} GFLOPs/byte  ({flops_por_byte('bytes')/base:.2f}x)")
for ps in [4.5, 6, 8]:
    f = flops_por_byte("blt", ps=ps)
    print(f"{'BLT, patch medio %.1f B' % ps:38s} {f/1e9:6.2f} GFLOPs/byte  ({f/base:.2f}x)")

pss = np.linspace(2, 12, 60)
fig, ax = plt.subplots(figsize=(7.5, 4))
ax.plot(pss, [flops_por_byte("blt", ps=p) / 1e9 for p in pss], color=AZUL, lw=2, label="BLT (modelo global fijo)")
ax.axhline(base / 1e9, color=NARANJA, ls="--", label="BPE (4.4 bytes/token)")
ax.axhline(flops_por_byte("bytes") / 1e9, color=GRIS, ls=":", label="Transformer sobre bytes")
ax.set_yscale("log"); ax.set_xlabel("tamaño medio de parche (bytes)"); ax.set_ylabel("GFLOPs por byte (forward)")
ax.set_title("El tamaño de parche es una perilla de cómputo (config. ilustrativa)"); ax.legend(); plt.show()
'''

BPE_LEN = r'''
from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders

def entrena_bpe(docs_, vocab_size):
    tk = Tokenizer(models.BPE())
    tk.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tk.decoder = decoders.ByteLevel()
    trn = trainers.BpeTrainer(vocab_size=vocab_size, initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
                              show_progress=False)
    tk.train_from_iterator((d["text"][:MAX_CHARS] for d in docs_), trn)
    return tk

def bytes_por_token(tk, textos):
    n_b = sum(len(t.encode()) for t in textos)
    return n_b / sum(len(tk.encode(t).ids) for t in textos)

VOCABS = [300, 512, 1024, 2048] if FAST_DEV_RUN else [512, 4096, 16384, 32000]
BPE = {v: entrena_bpe(DOCS_TR, v) for v in VOCABS}
TK = BPE[VOCABS[1]]                                   # el BPE "de trabajo" del resto de la lección
res = {lang: [bytes_por_token(BPE[v], [d["text"][:MAX_CHARS] for d in DOCS_VA if d["lang"] == lang]) for v in VOCABS]
       for lang in ["es", "en", "code"]}

fig, ax = plt.subplots(figsize=(7.5, 4))
for lang, col in zip(["es", "en", "code"], [AZUL, NARANJA, VERDE]):
    ax.plot(VOCABS, res[lang], "o-", color=col, label=lang)
ax.axhline(1.0, color=GRIS, ls=":", label="bytes (1 B/unidad)")
ax.set_xscale("log"); ax.set_xlabel("tamaño del vocabulario BPE"); ax.set_ylabel("bytes por token")
ax.set_title("Más vocabulario = tokens más largos (el 'patch size' de BPE)"); ax.legend(); plt.show()
print({l: [round(x, 2) for x in v] for l, v in res.items()})
'''

SCHEMES_TEXT = r'''
MUESTRA = "El servidor procesa las peticiones entrantes si falta la variable de entorno."

def inicios_stride(n, k=4):
    s = np.zeros(n, bool); s[::k] = True; return s

def es_espacio(b):                      # byte "tipo espacio": ni letra latina, ni dígito, ni continuación UTF-8
    return not (48 <= b <= 57 or 65 <= b <= 90 or 97 <= b <= 122 or 0x80 <= b <= 0xBF or b >= 0xC0)

def inicios_espacio(data):             # SpaceByte: parche nuevo tras un byte-espacio (cada parche con >=1 byte no-espacio)
    s = np.zeros(len(data), bool); s[0] = True
    for i in range(1, len(data)):
        s[i] = es_espacio(int(data[i - 1])) and not es_espacio(int(data[i]))
    return s

def inicios_bpe(tk, txt):
    off = np.cumsum([0] + [len(c.encode()) for c in txt])        # offset en caracteres -> en bytes
    s = np.zeros(off[-1], bool)
    for a, _ in tk.encode(txt).offsets:
        s[off[a]] = True
    return s

def marca(txt_bytes, starts):
    return "".join(("|" if s and i else "") + bytes([c]).decode("latin-1") for i, (c, s) in enumerate(zip(txt_bytes, starts)))

mb = MUESTRA.encode()
for nombre, st in [("stride k=4 (MegaByte)", inicios_stride(len(mb), 4)), ("espacios (SpaceByte)", inicios_espacio(mb)),
                   (f"BPE vocab={VOCABS[1]}", inicios_bpe(TK, MUESTRA))]:
    print(f"{nombre:24s} {st.sum():2d} parches | {marca(mb, st)}")
'''

NGRAM = r'''
from collections import defaultdict

class NgramByteLM:
    """Modelo de bytes de orden n con suavizado Witten-Bell: una TABLA de conteos (el 'lookup table' que
    menciona el paper de BLT cuando el campo receptivo del modelo de entropía es pequeño)."""
    def __init__(self, orden=4):
        self.orden = orden
        self.cuentas = [defaultdict(lambda: np.zeros(256, np.int32)) for _ in range(orden + 1)]
    def fit(self, data):
        b = data.tobytes()
        for n in range(self.orden + 1):
            for i in range(n, len(b)):
                self.cuentas[n][b[i - n:i]][b[i]] += 1
        return self
    def probs(self, ctx: bytes):
        p = np.full(256, 1 / 256)
        for n in range(self.orden + 1):
            if n > len(ctx):
                break
            c = self.cuentas[n].get(ctx[len(ctx) - n:] if n else b"")
            if c is None:
                break
            N, T = c.sum(), (c > 0).sum()
            p = (c + T * p) / (N + T)                      # interpolación Witten-Bell con el orden inferior
        return p
    def entropias(self, data):
        """H[i] = entropía (bits) de la distribución del byte i dado x_<i. H[0] = 8 (sin contexto)."""
        b = data.tobytes(); H = np.zeros(len(b), np.float32)
        for i in range(len(b)):
            p = self.probs(b[max(0, i - self.orden):i]); H[i] = -(p * np.log2(p + 1e-12)).sum()
        return H
    def bpb(self, data):
        b = data.tobytes(); tot = 0.0
        for i in range(len(b)):
            tot -= np.log2(self.probs(b[max(0, i - self.orden):i])[b[i]])
        return tot / len(b)

t0 = time.time()
NG = {n: NgramByteLM(n).fit(TR) for n in [0, 1, 2, 3, 4, 5]}
VAL_N = VA[:6000]
bpb_ng = {n: NG[n].bpb(VAL_N) for n in NG}
print(f"ajuste + evaluación n-gramas: {time.time()-t0:.1f}s")
print({f"orden {n}": round(float(v), 3) for n, v in bpb_ng.items()}, "(bits por byte, validación)")
'''

NN_BYTELM = r'''
class TinyGPT(nn.Module):
    """Transformer causal pequeño de vocabulario arbitrario (bytes: 256; tokens BPE: |V|)."""
    def __init__(self, vocab, d=64, L=2, ctx=128, H=4):
        super().__init__()
        self.emb, self.pos = nn.Embedding(vocab, d), nn.Embedding(ctx, d)
        layer = nn.TransformerEncoderLayer(d, H, 4 * d, dropout=0.0, batch_first=True, norm_first=True, activation="gelu")
        self.tr = nn.TransformerEncoder(layer, L, enable_nested_tensor=False)
        self.ln, self.head = nn.LayerNorm(d), nn.Linear(d, vocab, bias=False)
    def forward(self, x):
        T = x.shape[1]
        h = self.emb(x) + self.pos(torch.arange(T, device=x.device))
        mask = torch.triu(torch.ones(T, T, dtype=torch.bool, device=x.device), 1)
        return self.head(self.ln(self.tr(h, mask=mask, is_causal=True)))

def lote(data, B, T, g):
    ix = torch.randint(0, len(data) - T - 1, (B,), generator=g)
    x = torch.stack([torch.from_numpy(data[i:i + T].astype(np.int64)) for i in ix])
    y = torch.stack([torch.from_numpy(data[i + 1:i + T + 1].astype(np.int64)) for i in ix])
    return x.to(device), y.to(device)

def entrena_bytelm(d=64, L=2, ctx=128, pasos=300, B=32, lr=3e-3):
    m = TinyGPT(256, d, L, ctx).to(device); opt = torch.optim.AdamW(m.parameters(), lr=lr)
    g = torch.Generator().manual_seed(SEED)
    for paso in range(pasos):
        x, y = lote(TR, B, ctx, g)
        loss = F.cross_entropy(m(x).reshape(-1, 256), y.reshape(-1))
        opt.zero_grad(); loss.backward(); opt.step()
    return m.eval()

@torch.no_grad()
def entropias_nn(m, data, ctx=128, stride=64):
    """Entropía de cada byte con ventanas deslizantes; cada byte usa el contexto más largo disponible."""
    n = len(data); H = np.zeros(n, np.float32); H[0] = 8.0; hecho = np.zeros(n, bool); hecho[0] = True
    starts = list(range(0, n - ctx + 1, stride)) + [n - ctx]
    for s in starts:
        x = torch.from_numpy(data[s:s + ctx].astype(np.int64))[None].to(device)
        p = F.softmax(m(x)[0], -1); h = -(p * torch.log2(p + 1e-12)).sum(-1).cpu().numpy()   # h[t] -> byte s+t+1
        idx = np.arange(1, ctx) + s
        nuevo = ~hecho[idx]; H[idx[nuevo]] = h[:-1][nuevo]; hecho[idx[nuevo]] = True
    return H

t0 = time.time()
PASOS_LM = 600 if FAST_DEV_RUN else 3000
LM = entrena_bytelm(d=96 if FAST_DEV_RUN else 256, L=2 if FAST_DEV_RUN else 6, pasos=PASOS_LM)
H_va_nn = entropias_nn(LM, VA[:6000])
with torch.no_grad():
    g = torch.Generator().manual_seed(1); x, y = lote(VA, 64, 128, g)
    bpb_nn = F.cross_entropy(LM(x).reshape(-1, 256), y.reshape(-1)).item() / math.log(2)
print(f"transformer de bytes ({sum(p.numel() for p in LM.parameters())/1e6:.2f}M params, {PASOS_LM} pasos, {time.time()-t0:.0f}s): "
      f"{bpb_nn:.3f} bpb val | n-grama orden 4: {bpb_ng[4]:.3f} | orden 0: {bpb_ng[0]:.3f}")
'''

PATCHING = r'''
def inicios_global(H, theta):                    # BLT: nuevo parche si H(x_i) > theta
    s = H > theta; s[0] = True; return s

def inicios_monotono(H, theta_r):                # BLT: nuevo parche si H(x_i) - H(x_{i-1}) > theta_r
    d = np.empty_like(H); d[0] = np.inf; d[1:] = H[1:] - H[:-1]
    s = d > theta_r; s[0] = True; return s

def calibra(H, objetivo, fn, lo=-6.0, hi=9.0):
    """Bisección del umbral para que el tamaño medio de parche (bytes/parche) sea `objetivo`."""
    for _ in range(40):
        mid = (lo + hi) / 2
        if len(H) / fn(H, mid).sum() > objetivo:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2

def longitudes(starts):
    idx = np.flatnonzero(starts); return np.diff(np.r_[idx, len(starts)])

H_TR = NG[4].entropias(TR); H_VA = NG[4].entropias(VA)             # tabla n-grama (orden 4) como modelo de entropía
OBJ = 4.5                                                            # patch medio de BLT-Entropy en su mezcla de entrenamiento
TH_G = calibra(H_TR, OBJ, inicios_global); TH_M = calibra(H_TR, OBJ, inicios_monotono)
for nombre, fn, th in [("global", inicios_global, TH_G), ("monótono", inicios_monotono, TH_M)]:
    print(f"umbral {nombre:9s} θ={th:6.3f} -> tamaño medio val = {len(H_VA)/fn(H_VA, th).sum():.2f} bytes/parche")
'''

ENTROPY_PLOT = r'''
def traza(ax, snippet, titulo, theta):
    b = snippet.encode()[:90]
    H = entropias_nn(LM, np.frombuffer(snippet.encode(), np.uint8).copy()[:90], ctx=min(128, len(b)), stride=16) \
        if len(b) >= 128 else NG[4].entropias(np.frombuffer(b, np.uint8))
    st = inicios_global(H, theta)
    ax.bar(range(len(b)), H, color=[NARANJA if s else AZUL for s in st], width=.85)
    ax.axhline(theta, color="crimson", ls="--", lw=1, label=f"umbral θ={theta:.2f}")
    for i in np.flatnonzero(st)[1:]:
        ax.axvline(i - .5, color=GRIS, lw=.6)
    ax.set_xticks(range(len(b))); ax.set_xticklabels([("␣" if c == 32 else chr(c) if 32 < c < 127 else "·") for c in b], fontsize=6)
    ax.set_title(titulo, fontsize=9, loc="left"); ax.set_ylabel("H (bits)"); ax.legend(loc="upper right", fontsize=7)

ejemplos = {}
for lang in ["es", "en", "code"]:
    d = next(d for d in DOCS_VA if d["lang"] == lang)
    ejemplos[lang] = d["text"].strip().replace("\n", " ")[:90]
fig, axs = plt.subplots(3, 1, figsize=(11, 7.5))
for ax, (lang, snip) in zip(axs, ejemplos.items()):
    traza(ax, snip, f"{lang}: entropía del siguiente byte (naranja = inicio de parche)", TH_G)
plt.tight_layout(); plt.show()
'''

PATCH_PLOTS = r'''
TKb = TK
def long_bpe(data_docs):
    return np.concatenate([[len(t) for t in TKb.encode(d["text"][:MAX_CHARS]).tokens] for d in data_docs])

L_stride = longitudes(inicios_stride(len(VA), 4)); L_space = longitudes(inicios_espacio(VA))
L_bpe = long_bpe(DOCS_VA)
L_glob = longitudes(inicios_global(H_VA, TH_G)); L_mono = longitudes(inicios_monotono(H_VA, TH_M))

grid = np.linspace(0.2, 4.0, 40)
fig, axs = plt.subplots(1, 2, figsize=(12, 4))
axs[0].plot(grid, [min(30, len(H_TR)/inicios_global(H_TR, t).sum()) for t in grid], color=AZUL, lw=2, label="umbral global")
axs[0].plot(grid, [min(30, len(H_TR)/inicios_monotono(H_TR, t-3).sum()) for t in grid], color=NARANJA, lw=2, label="restricción monótona (θ_r = θ-3)")
axs[0].axhline(OBJ, color=GRIS, ls=":"); axs[0].set_xlabel("umbral θ (bits)"); axs[0].set_ylabel("tamaño medio de parche (bytes)")
axs[0].set_title("Un solo número controla el coste: θ"); axs[0].legend()
bins = np.arange(0.5, 21.5, 1)
for L_, nom, col in [(L_stride, "stride 4", GRIS), (L_space, "espacios", VERDE), (L_bpe, f"BPE {VOCABS[1]}", NARANJA), (L_glob, "entropía (global)", AZUL)]:
    axs[1].hist(np.clip(L_, 1, 20), bins=bins, histtype="step", lw=2, density=True, label=f"{nom} (media {L_.mean():.1f})", color=col)
axs[1].set_xlabel("bytes por parche/token"); axs[1].set_ylabel("densidad"); axs[1].set_title("Distribución de longitudes (val)"); axs[1].legend(fontsize=8)
plt.tight_layout(); plt.show()
print("desv. típica de la longitud -> stride:", L_stride.std().round(2), "| BPE:", L_bpe.std().round(2), "| entropía:", L_glob.std().round(2))
'''

STRIP = r'''
snip = ejemplos["es"] if len(ejemplos["es"]) > 40 else MUESTRA
sb = np.frombuffer(snip.encode(), np.uint8)
Hs = NG[4].entropias(sb)
filas = [("stride k=4", inicios_stride(len(sb), 4)), ("espacios", inicios_espacio(sb)),
         (f"BPE {VOCABS[1]}", inicios_bpe(TK, snip)), ("entropía (global)", inicios_global(Hs, TH_G))]
fig, ax = plt.subplots(figsize=(11, 2.8))
for r, (nom, st) in enumerate(filas):
    idx = np.flatnonzero(st); fin = np.r_[idx[1:], len(sb)]
    for k, (a, b_) in enumerate(zip(idx, fin)):
        ax.barh(r, b_ - a - .08, left=a, color=[AZUL, NARANJA, VERDE][k % 3], height=.7, alpha=.85)
ax.set_yticks(range(len(filas))); ax.set_yticklabels([f for f, _ in filas]); ax.invert_yaxis()
ax.set_xticks(range(len(sb))); ax.set_xticklabels([("␣" if c == 32 else chr(c) if 32 < c < 127 else "·") for c in sb], fontsize=6)
ax.set_title("La misma frase agrupada de cuatro maneras (cada bloque = un paso del transformer grande)", fontsize=10, loc="left")
plt.tight_layout(); plt.show()
'''

LANG = r'''
def por_idioma(lang):
    Hs_ = [NG[4].entropias(np.frombuffer(d["text"][:MAX_CHARS].encode(), np.uint8)) for d in DOCS_VA if d["lang"] == lang]
    H_ = np.concatenate(Hs_)
    ps_ = np.mean([len(h) / inicios_global(h, TH_G).sum() for h in Hs_])
    return H_.mean(), ps_

stats = {lang: por_idioma(lang) for lang in ["es", "en", "code"]}
fig, axs = plt.subplots(1, 2, figsize=(9, 3.6))
langs = list(stats)
axs[0].bar(langs, [stats[l][0] for l in langs], color=[AZUL, NARANJA, VERDE]); axs[0].set_title("Entropía media por byte (bits)")
axs[1].bar(langs, [stats[l][1] for l in langs], color=[AZUL, NARANJA, VERDE]); axs[1].set_title(f"Tamaño medio de parche con θ={TH_G:.2f} fijo")
plt.tight_layout(); plt.show()
print({l: (round(float(a), 2), round(float(b), 2)) for l, (a, b) in stats.items()})
'''

INCREMENTAL = r'''
def prueba_incremental(fn_inicios, items, n_pruebas=300, seed=SEED):
    """fp(x_<i) == fp(x)_<i ? Devuelve la fracción de cortes en los que se cumple."""
    r = random.Random(seed); ok = 0
    for _ in range(n_pruebas):
        it = r.choice(items); n = len(it if isinstance(it, bytes) else it.encode())
        i = r.randrange(5, n - 1)
        full, pref = fn_inicios(it), fn_inicios(it[:i] if isinstance(it, bytes) else it.encode()[:i].decode("utf-8", "ignore"))
        ok += int(np.array_equal(full[:len(pref)], pref))
    return ok / n_pruebas

textos_prueba = [d["text"][:300] for d in DOCS_VA[:60] if d["lang"] != "code"]
bytes_prueba = [t.encode() for t in textos_prueba]
f_ent = lambda b: inicios_global(NG[4].entropias(np.frombuffer(b, np.uint8)), TH_G)
f_bpe = lambda t: inicios_bpe(TK, t)
print(f"parches por entropía : incremental en {prueba_incremental(f_ent, bytes_prueba)*100:5.1f}% de los cortes")
print(f"tokens BPE           : incremental en {prueba_incremental(f_bpe, textos_prueba)*100:5.1f}% de los cortes")
pal = [w for w in re.findall(r"[a-záéíóúñ]{8,}", " ".join(textos_prueba))]
for w in dict.fromkeys(pal):
    full = TK.encode(" " + w).tokens
    for k in range(3, len(w) - 2):
        pref = TK.encode(" " + w[:k]).tokens
        if pref != full[:len(pref)]:
            print(f"palabra completa  ' {w}' -> {full}")
            print(f"solo el prefijo   ' {w[:k]}' -> {pref}   <- NO es un prefijo de la tokenización completa")
            break
    else:
        continue
    break
'''

MINIBLT_1 = r'''
def mascara_causal(T, dev):
    return torch.triu(torch.ones(T, T, dtype=torch.bool, device=dev), 1)

def capas(d, L, H):
    layer = nn.TransformerEncoderLayer(d, H, 4 * d, dropout=0.0, batch_first=True, norm_first=True, activation="gelu")
    return nn.TransformerEncoder(layer, L, enable_nested_tensor=False)

class MiniBLT(nn.Module):
    """BLT en miniatura: codificador local (bytes + hash de n-gramas) -> atención cruzada que agrupa bytes en parches
    -> transformer latente global (sobre parches) -> atención cruzada que vuelve a bytes -> decodificador local."""
    def __init__(self, dl=64, dg=128, Lg=3, Le=1, Ld=2, H=4, ctx=128, ngramas=(3, 4, 5), hsize=4096):
        super().__init__()
        self.dl, self.dg, self.H, self.ngramas, self.hsize = dl, dg, H, ngramas, hsize
        self.emb = nn.Embedding(256, dl); self.hemb = nn.ModuleList([nn.Embedding(hsize, dl) for _ in ngramas])
        self.pos = nn.Embedding(ctx, dl); self.enc = capas(dl, Le, H)
        self.q_e, self.k_e, self.v_e = nn.Linear(dl, dg), nn.Linear(dl, dg), nn.Linear(dl, dg)
        self.o_e, self.pool_e, self.ppos = nn.Linear(dg, dg), nn.Linear(dl, dg), nn.Embedding(ctx, dg)
        self.glob = capas(dg, Lg, H)
        self.bos = nn.Parameter(torch.zeros(1, 1, dg)); self.kv_d = nn.Linear(dg, 2 * dl)
        self.q_d, self.o_d = nn.Linear(dl, dl), nn.Linear(dl, dl)
        self.dec = capas(dl, Ld, H); self.ln, self.head = nn.LayerNorm(dl), nn.Linear(dl, 256, bias=False)

    def hash_ngramas(self, x):
        """Embeddings hash de n-gramas de bytes (rolling hash simplificado) promediados con el embedding del byte."""
        B, T = x.shape; out = 0
        for emb, n in zip(self.hemb, self.ngramas):
            h = torch.zeros(B, T, dtype=torch.long, device=x.device)
            for k in range(n):
                h = h * 257 + (F.pad(x, (k, 0))[:, :T] if k else x) + 1
            out = out + emb(h % self.hsize)
        return out / (len(self.ngramas) + 1)

    def atencion(self, q, k, v, mask):               # q [B,Nq,D]; k,v [B,Nk,D]; mask [B,Nq,Nk] (True = puede atender)
        B, Nq, D = q.shape; Nk = k.shape[1]; H = self.H
        sp = lambda z, N: z.view(B, N, H, D // H).transpose(1, 2)
        o = F.scaled_dot_product_attention(sp(q, Nq), sp(k, Nk), sp(v, Nk), attn_mask=mask.unsqueeze(1))
        return o.transpose(1, 2).reshape(B, Nq, D)
'''

MINIBLT_2 = r'''
def forward_blt(self, x, inicios):
    """x [B,T] bytes; inicios [B,T] bool (True = el byte abre un parche; inicios[:,0] = True)."""
    B, T = x.shape; dev = x.device
    pid = inicios.long().cumsum(1) - 1                                   # [B,T] parche de cada byte
    P = int(pid.max()) + 1
    h = self.emb(x) + self.hash_ngramas(x) + self.pos(torch.arange(T, device=dev))
    h = self.enc(h, mask=mascara_causal(T, dev), is_causal=True)         # 1) codificador local (bytes)
    M = pid.unsqueeze(1) == torch.arange(P, device=dev).view(1, P, 1)    # [B,P,T] bytes de cada parche
    pool = h.unsqueeze(1).masked_fill(~M.unsqueeze(-1), -1e4).amax(2)    # consulta inicial = max-pool del parche
    vacio = ~M.any(2); pool = pool.masked_fill(vacio.unsqueeze(-1), 0.)
    M2 = M.clone(); M2[..., 0] |= vacio                                  # (parches de relleno: evita filas sin claves)
    p = self.pool_e(pool) + self.o_e(self.atencion(self.q_e(pool), self.k_e(h), self.v_e(h), M2))   # 2) bytes -> parches
    o = self.glob(p + self.ppos(torch.arange(P, device=dev)), mask=mascara_causal(P, dev), is_causal=True)  # 3) global
    o = torch.cat([self.bos.expand(B, -1, -1), o], 1)                    # o_{-1} = BOS aprendido
    k, v = self.kv_d(o).chunk(2, -1)
    Md = pid.unsqueeze(2) == torch.arange(P + 1, device=dev).view(1, 1, P + 1)   # el byte del parche j atiende a o_{j-1}
    d = h + self.o_d(self.atencion(self.q_d(h), k, v, Md))               # 4) parches -> bytes
    d = self.dec(d, mask=mascara_causal(T, dev), is_causal=True)         # 5) decodificador local
    return self.head(self.ln(d))

MiniBLT.forward = forward_blt

# prueba de causalidad: cambiar el byte t NO debe alterar las predicciones de posiciones < t
m_test = MiniBLT().eval(); xt = torch.randint(0, 256, (2, 64)); st = torch.zeros(2, 64, dtype=torch.bool); st[:, ::5] = True
x2 = xt.clone(); x2[:, 40] = (x2[:, 40] + 1) % 256
with torch.no_grad():
    d_ = (m_test(xt, st) - m_test(x2, st)).abs().amax(-1)
print("máx. diferencia en posiciones < 40 :", float(d_[:, :40].max()), "(debe ser 0)")
print("máx. diferencia en posiciones >= 40:", float(d_[:, 40:].max()), "(debe ser > 0)")
'''

BASELINES = r'''
# --- Datos del baseline BPE: flujo de ids y longitud en bytes de cada token ---
IDS_TR = np.array(TK.encode(TXT_TR).ids, dtype=np.int64)
IDS_VA = np.array(TK.encode(TXT_VA).ids, dtype=np.int64)
TOK_B = np.array([len(TK.id_to_token(i)) for i in range(TK.get_vocab_size())])     # en ByteLevel: 1 carácter = 1 byte
BPT = len(TXT_TR.encode()) / len(IDS_TR)
T_BYTES, T_TOK = 128, int(round(128 / BPT))                                          # misma ventana en bytes
print(f"bytes/token (train) = {BPT:.2f} -> ventana de {T_TOK} tokens ~ {T_BYTES} bytes")

def lote_ids(ids, B, T, g):
    ix = torch.randint(0, len(ids) - T - 1, (B,), generator=g)
    x = torch.stack([torch.from_numpy(ids[i:i + T]) for i in ix]); y = torch.stack([torch.from_numpy(ids[i + 1:i + T + 1]) for i in ix])
    return x.to(device), y.to(device)

@torch.no_grad()
def bpb_bpe(m, n=64):
    g = torch.Generator().manual_seed(1); ix = torch.randint(0, len(IDS_VA) - T_TOK - 1, (n,), generator=g)
    x = torch.stack([torch.from_numpy(IDS_VA[i:i + T_TOK]) for i in ix]).to(device)
    y = torch.stack([torch.from_numpy(IDS_VA[i + 1:i + T_TOK + 1]) for i in ix]).to(device)
    nll = F.cross_entropy(m(x).reshape(-1, m.head.out_features), y.reshape(-1), reduction="sum").item()
    return nll / math.log(2) / TOK_B[y.cpu().numpy()].sum()               # NLL total / bytes totales cubiertos por los targets
'''

TRAIN = r'''
D_G, L_G = (128, 3) if FAST_DEV_RUN else (512, 8)
PASOS = 400 if FAST_DEV_RUN else 4000
B_TR = 16
H_TR_BLT, H_VA_BLT = H_TR, H_VA                                      # entropías (tabla n-grama) precalculadas = como en BLT

def lote_blt(data, Hs, B, T, g):
    ix = torch.randint(0, len(data) - T - 1, (B,), generator=g)
    x = torch.stack([torch.from_numpy(data[i:i + T].astype(np.int64)) for i in ix])
    y = torch.stack([torch.from_numpy(data[i + 1:i + T + 1].astype(np.int64)) for i in ix])
    st = torch.stack([torch.from_numpy(inicios_global(Hs[i:i + T].copy(), TH_G)) for i in ix])
    return x.to(device), y.to(device), st.to(device)

def entrena(nombre, modelo, paso_fn, eval_fn, pasos=PASOS, lr=2e-3, cada=50):
    opt = torch.optim.AdamW(modelo.parameters(), lr=lr); g = torch.Generator().manual_seed(SEED)
    curva, t0 = [], time.time()
    for s in range(pasos + 1):
        if s % cada == 0:
            modelo.eval(); curva.append((s, eval_fn(modelo))); modelo.train()
        if s == pasos:
            break
        loss = paso_fn(modelo, g); opt.zero_grad(); loss.backward(); opt.step()
    print(f"{nombre:22s} params={sum(p.numel() for p in modelo.parameters())/1e6:5.2f}M | {time.time()-t0:5.0f}s | bpb final = {curva[-1][1]:.3f}")
    return curva

RES = {}
# (a) transformer isotrópico sobre bytes
m_b = TinyGPT(256, D_G, L_G, T_BYTES).to(device)
def paso_b(m, g):
    x, y = lote(TR, B_TR, T_BYTES, g); return F.cross_entropy(m(x).reshape(-1, 256), y.reshape(-1))
def eval_b(m):
    g = torch.Generator().manual_seed(1); x, y = lote(VA, 64, T_BYTES, g)
    with torch.no_grad(): return F.cross_entropy(m(x).reshape(-1, 256), y.reshape(-1)).item() / math.log(2)
RES["bytes"] = entrena("bytes isotrópico", m_b, paso_b, eval_b)
# (b) transformer sobre tokens BPE (mismo tamaño global)
m_t = TinyGPT(TK.get_vocab_size(), D_G, L_G, T_TOK + 1).to(device)
def paso_t(m, g):
    x, y = lote_ids(IDS_TR, B_TR, T_TOK, g); return F.cross_entropy(m(x).reshape(-1, m.head.out_features), y.reshape(-1))
RES["bpe"] = entrena("BPE (tokens)", m_t, paso_t, bpb_bpe)
# (c) MiniBLT con parches por entropía
m_blt = MiniBLT(dl=64 if FAST_DEV_RUN else 256, dg=D_G, Lg=L_G).to(device)
def paso_blt(m, g):
    x, y, st = lote_blt(TR, H_TR_BLT, B_TR, T_BYTES, g); return F.cross_entropy(m(x, st).reshape(-1, 256), y.reshape(-1))
def eval_blt(m):
    g = torch.Generator().manual_seed(1); x, y, st = lote_blt(VA, H_VA_BLT, 64, T_BYTES, g)
    with torch.no_grad(): return F.cross_entropy(m(x, st).reshape(-1, 256), y.reshape(-1)).item() / math.log(2)
RES["blt"] = entrena("MiniBLT (entropía)", m_blt, paso_blt, eval_blt)
'''

RESULTS_PLOT = r'''
ps_real = len(H_VA) / inicios_global(H_VA, TH_G).sum()
dl_ = 64 if FAST_DEV_RUN else 256
fl = {"bytes": L_G * flops_capa(D_G, T_BYTES) + 2 * D_G * 256,
      "bpe": (L_G * flops_capa(D_G, T_TOK) + 2 * D_G * TK.get_vocab_size()) / BPT,
      "blt": L_G * flops_capa(D_G, T_BYTES / ps_real) / ps_real + (1 + 2) * flops_capa(dl_, T_BYTES) + 2 * dl_ * 256 + 4 * dl_ * D_G}
etq = {"bytes": "bytes isotrópico", "bpe": f"BPE-{VOCABS[1]}", "blt": f"MiniBLT (ps={ps_real:.1f})"}
cols = {"bytes": GRIS, "bpe": NARANJA, "blt": AZUL}
fig, axs = plt.subplots(1, 2, figsize=(12, 4))
for k, c in RES.items():
    axs[0].plot([s for s, _ in c], [v for _, v in c], color=cols[k], lw=2, label=etq[k])
axs[0].set_xlabel("paso de entrenamiento"); axs[0].set_ylabel("bits por byte (validación)"); axs[0].set_title("Curvas de validación (escala diminuta)")
axs[0].legend()
for k in RES:
    axs[1].scatter(fl[k] / 1e6, RES[k][-1][1], s=120, color=cols[k], label=etq[k])
axs[1].set_xlabel("MFLOPs por byte (forward, fórmula)"); axs[1].set_ylabel("bpb final (val)"); axs[1].set_title("Calidad vs. cómputo por byte")
axs[1].legend(); plt.tight_layout(); plt.show()
print({etq[k]: f"{fl[k]/1e6:.1f} MFLOPs/B | bpb={RES[k][-1][1]:.3f}" for k in RES})
'''

PAPER_PLOT = r'''
# Cifras REPORTADAS por Pagnoni et al. (2024), arXiv:2412.09871 (tablas 1, 3 y 4). NO las hemos reproducido.
fig, axs = plt.subplots(1, 3, figsize=(13, 3.8))
n1, v1 = ["Llama 3\n(BPE, 1T tok)", "BLT-Space\n(6.1 B/parche)", "BLT-Entropy\n(4.5 B/parche)"], [60.0, 58.0, 61.1]
axs[0].bar(n1, v1, color=[NARANJA, GRIS, AZUL]); axs[0].set_ylim(50, 64); axs[0].set_title("Media de 7 benchmarks, 8B (Tabla 1)", fontsize=9)
for i, v in enumerate(v1): axs[0].text(i, v + .2, f"{v}", ha="center")
n2, v2 = ["Llama 3\n(1T tok)", "Llama 3.1\n(16T tok)", "BLT\n(1T tok)"], [27.5, 20.0, 54.1]
axs[1].bar(n2, v2, color=[NARANJA, "#d9b38c", AZUL]); axs[1].set_title("CUTE (manipulación de caracteres), 8B (Tabla 3)", fontsize=9)
for i, v in enumerate(v2): axs[1].text(i, v + .8, f"{v}", ha="center")
n3 = ["Ruido en\nHellaSwag (media)", "FLORES-101\nX→En (media)", "FLORES-101\nEn→X (media)"]
l3, b3 = [56.9, 12.1, 5.9], [64.3, 14.0, 6.4]
x = np.arange(3); axs[2].bar(x - .2, l3, .4, color=NARANJA, label="Llama 3"); axs[2].bar(x + .2, b3, .4, color=AZUL, label="BLT")
axs[2].set_xticks(x); axs[2].set_xticklabels(n3, fontsize=8); axs[2].legend(); axs[2].set_title("Robustez y traducción (Tablas 3-4)", fontsize=9)
plt.tight_layout(); plt.show()
'''

LIBS = r'''
from transformers import ByT5Tokenizer, CanineTokenizer
bt5, can = ByT5Tokenizer(), CanineTokenizer()          # ambos funcionan SIN descargar nada: no hay vocabulario que aprender
frases = {"es": "Canción de cuna para el ñandú",
          "en": "A lullaby for the rhea",
          "code": "def f(x): return x ** 2  # 🙂"}
print(f"{'texto':32s} {'chars':>5s} {'bytes':>5s} {'ByT5':>5s} {'CANINE':>6s} {'BPE-'+str(VOCABS[1]):>8s}")
for l, t in frases.items():
    print(f"{t[:30]:32s} {len(t):5d} {len(t.encode()):5d} {len(bt5(t).input_ids)-1:5d} {len(can(t).input_ids)-2:6d} {len(TK.encode(t).ids):8d}")
print("ByT5 ids de 'ñ':", bt5("ñ").input_ids[:-1], "= bytes UTF-8", list("ñ".encode()), "+ 3 (ids 0-2 reservados: pad/eos/unk)")
print("CANINE ids de 'ñ🙂':", can("ñ🙂").input_ids[1:-1], "= code points", [ord(c) for c in "ñ🙂"])
try:                                                    # BLT oficial (requiere aceptar la licencia en HF y bajar ~GB)
    from transformers import BltForCausalLM
    print("transformers incluye BltForCausalLM; los pesos oficiales están en el hub (p. ej. facebook/blt-1b, con acceso aprobado).")
except Exception as e:
    print("Tu versión de transformers no incluye BLT:", type(e).__name__, "-> usa el repo facebookresearch/blt")
'''


ACUERDO = r"""
# ¿Coinciden las fronteras de los dos modelos de entropía (tabla n-grama vs transformer)? F1 sobre una muestra de validación
N_AC = 6000
Hn, Hg = H_va_nn[:N_AC], H_VA[:N_AC]
a = inicios_global(Hn, calibra(Hn, OBJ, inicios_global)); b = inicios_global(Hg, calibra(Hg, OBJ, inicios_global))
tp = (a & b).sum(); prec, rec = tp / a.sum(), tp / b.sum()
print(f"acuerdo de fronteras tabla n-grama vs transformer: precisión={prec:.2f} recall={rec:.2f} F1={2*prec*rec/(prec+rec):.2f}")
print(f"(azar: dos segmentaciones independientes con ps={OBJ} coincidirían en ~{100/OBJ:.0f}% de las fronteras)")
"""
