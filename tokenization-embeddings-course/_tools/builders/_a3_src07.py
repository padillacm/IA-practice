"""Celdas de código del módulo 07 (cadenas). Las usa build_07.py y _a3_proj07.py."""
from _a3_src06 import SETUP_EXTRA, DATA, BPE_LEN  # reutiliza utilidades de la lección 06

BPE_FN = BPE_LEN.split("VOCABS = ")[0]

PIP = "!pip install -q torch numpy matplotlib tokenizers transformers datasets scipy"

SETUP7 = r'''
import copy, re
from collections import Counter
'''

HNET_UTIL = r'''
def mascara_causal(T, dev):
    return torch.triu(torch.ones(T, T, dtype=torch.bool, device=dev), 1)

def capas(d, L, H=4):
    layer = nn.TransformerEncoderLayer(d, H, 4 * d, dropout=0.0, batch_first=True, norm_first=True, activation="gelu")
    return nn.TransformerEncoder(layer, L, enable_nested_tensor=False)

ES_ESPACIO = torch.tensor([not (48 <= b <= 57 or 65 <= b <= 90 or 97 <= b <= 122 or b >= 0x80) for b in range(256)])

def inicios_espacio_t(x):
    """[B,T] bool: el byte abre palabra (el anterior es 'espacio' y este no). Es la heurística de SpaceByte."""
    prev = F.pad(x, (1, 0), value=32)[:, :-1]
    return ES_ESPACIO[prev] & ~ES_ESPACIO[x]

def lote(data, B, T, g):
    ix = torch.randint(0, len(data) - T - 1, (B,), generator=g)
    x = torch.stack([torch.from_numpy(data[i:i + T].astype(np.int64)) for i in ix])
    y = torch.stack([torch.from_numpy(data[i + 1:i + T + 1].astype(np.int64)) for i in ix])
    return x.to(device), y.to(device)
'''

HNET_MODEL = r'''
class MiniHNet(nn.Module):
    """H-Net de UNA etapa, en miniatura. Sigue el diseño de Hwang, Wang y Gu (2025):
       E (causal) -> routing (coseno entre vecinos) -> selección de bordes -> M (sobre chunks) -> dechunk (suavizado EMA + STE) -> D.
       Simplificación: E y D son transformers causales (el paper usa Mamba-2); modo 'space'/'pool' = chunking NO aprendido."""
    def __init__(self, d=64, d_main=128, Le=1, Lm=3, Ld=2, ctx=128, modo="dc"):
        super().__init__()
        self.d, self.modo = d, modo
        self.emb, self.pos = nn.Embedding(256, d), nn.Embedding(ctx, d)
        self.enc, self.ne = capas(d, Le), nn.LayerNorm(d)
        self.wq, self.wk = nn.Linear(d, d, bias=False), nn.Linear(d, d, bias=False)
        self.pad = nn.Parameter(torch.zeros(d_main - d))              # ensancha d -> d_main con un vector compartido (como SpaceByte/H-Net)
        self.main, self.nm = capas(d_main, Lm), nn.LayerNorm(d_main)
        self.res = nn.Linear(d, d); nn.init.zeros_(self.res.weight); nn.init.zeros_(self.res.bias)   # residual proyectado, init ~0
        self.dec, self.ln, self.head = capas(d, Ld), nn.LayerNorm(d), nn.Linear(d, 256, bias=False)

    def fronteras(self, xh, x):
        B, T, _ = xh.shape
        if self.modo == "dc":                                          # routing module: p_t = (1 - cos(q_t, k_{t-1})) / 2
            cos = F.cosine_similarity(self.wq(xh[:, 1:]), self.wk(xh[:, :-1]), dim=-1)
            p = torch.cat([torch.ones(B, 1, device=xh.device), 0.5 * (1 - cos)], 1).clamp(0, 1)
            return p, p >= 0.5
        b = inicios_espacio_t(x) if self.modo == "space" else (torch.arange(T, device=xh.device) % 4 == 0).expand(B, T)
        b = b.clone(); b[:, 0] = True
        return b.float(), b

    def forward(self, x):
        B, T = x.shape; dev = x.device
        xh = self.ne(self.enc(self.emb(x) + self.pos(torch.arange(T, device=dev)), mask=mascara_causal(T, dev), is_causal=True))
        p, b = self.fronteras(xh, x)
        rank = b.long().cumsum(1) - 1; Lc = int(rank.max()) + 1       # índice de chunk de cada byte
        bi, ti = b.nonzero(as_tuple=True)
        sel = xh.new_zeros(B, Lc, self.d); sel[bi, rank[bi, ti]] = xh[bi, ti]      # downsampler: se queda con los vectores-frontera
        P = xh.new_zeros(B, Lc); P[bi, rank[bi, ti]] = p[bi, ti]
        z = self.nm(self.main(torch.cat([sel, self.pad.expand(B, Lc, -1)], -1), mask=mascara_causal(Lc, dev), is_causal=True))[..., :self.d]
        prev, zb = xh.new_zeros(B, self.d), []
        for j in range(Lc):                                            # suavizado EMA:  z̄_j = P_j z_j + (1 - P_j) z̄_{j-1}
            prev = P[:, j:j + 1] * z[:, j] + (1 - P[:, j:j + 1]) * prev; zb.append(prev)
        zt = torch.stack(zb, 1).gather(1, rank.unsqueeze(-1).expand(-1, -1, self.d))    # upsampler: repite hasta la siguiente frontera
        c = torch.where(b, p, 1 - p); c = c + (1 - c).detach()         # confianza con straight-through (vale 1 en forward)
        out = c.unsqueeze(-1) * zt + self.res(xh)
        logits = self.head(self.ln(self.dec(out, mask=mascara_causal(T, dev), is_causal=True)))
        return logits, {"p": p, "b": b, "F": b.float().mean(), "G": p.mean(), "chunks": Lc}

def perdida_ratio(F_, G, N):
    """Ratio loss de H-Net (Ec. 10): minimiza ~1 cuando F = G = 1/N; el gradiente fluye por G."""
    return N / (N - 1) * ((N - 1) * F_ * G + (1 - F_) * (1 - G))

# prueba de causalidad (mismo test que en el módulo 06)
_m = MiniHNet().eval(); _x = torch.randint(0, 256, (2, 64)); _x2 = _x.clone(); _x2[:, 40] = (_x2[:, 40] + 1) % 256
with torch.no_grad():
    _d = (_m(_x)[0] - _m(_x2)[0]).abs().amax(-1)
print("máx. diferencia en posiciones < 40:", float(_d[:, :40].max()), "(debe ser 0) | en >= 40:", float(_d[:, 40:].max()))
'''

HNET_TRAIN = r'''
PASOS_H = 400 if FAST_DEV_RUN else 4000
N_RATIO, ALPHA, T_B, B_TR = 4.0, 0.03, 128, 16

def entrena_hnet(modo, pasos=PASOS_H, seed=SEED, snaps=(0, 100, 250, 400)):
    torch.manual_seed(seed)
    m = MiniHNet(modo=modo, d=64 if FAST_DEV_RUN else 256, d_main=128 if FAST_DEV_RUN else 512, Lm=3 if FAST_DEV_RUN else 8).to(device)
    opt = torch.optim.AdamW(m.parameters(), lr=2e-3); g = torch.Generator().manual_seed(seed)
    gv = torch.Generator().manual_seed(1); xv, yv = lote(VA, 64, T_B, gv)
    es_txt = next((d["text"] for d in DOCS_VA if d["lang"] == "es"), DOCS_VA[0]["text"]).strip()[:T_B].ljust(T_B).encode()[:T_B]
    xs = torch.from_numpy(np.frombuffer(es_txt, np.uint8).astype(np.int64))[None].to(device)   # ventana fija en español
    log = {"bpb": [], "F": [], "G": [], "snap": {}, "paso_bpb": []}; t0 = time.time()
    for s in range(pasos + 1):
        if s % 50 == 0 or s == pasos:
            m.eval()
            with torch.no_grad():
                lg, info = m(xv); log["bpb"].append(F.cross_entropy(lg.reshape(-1, 256), yv.reshape(-1)).item() / math.log(2)); log["paso_bpb"].append(s)
            m.train()
        if s in snaps:
            m.eval()
            with torch.no_grad(): log["snap"][s] = (m(xs)[1]["p"][0].cpu().numpy(), xs[0].cpu().numpy())
            m.train()
        if s == pasos: break
        x, y = lote(TR, B_TR, T_B, g); lg, info = m(x)
        loss = F.cross_entropy(lg.reshape(-1, 256), y.reshape(-1))
        if modo == "dc": loss = loss + ALPHA * perdida_ratio(info["F"], info["G"], N_RATIO)
        opt.zero_grad(); loss.backward(); opt.step()
        log["F"].append(float(info["F"])); log["G"].append(float(info["G"]))
    m.eval(); log["modelo"] = m
    print(f"H-Net[{modo:5s}] params={sum(p.numel() for p in m.parameters())/1e6:.2f}M | {time.time()-t0:4.0f}s | bpb final={log['bpb'][-1]:.3f}"
          + (f" | F={np.mean(log['F'][-20:]):.3f} (objetivo {1/N_RATIO:.3f})" if modo == "dc" else ""))
    return log

RUNS = {modo: entrena_hnet(modo) for modo in ["dc", "space", "pool"]}
'''

HNET_PLOTS = r'''
cols = {"dc": AZUL, "space": VERDE, "pool": GRIS}
nom = {"dc": "H-Net (chunking aprendido)", "space": "H-Net (espacios, heurística)", "pool": "H-Net (pool fijo k=4)"}
fig, axs = plt.subplots(1, 3, figsize=(14, 3.8))
for k, r in RUNS.items():
    axs[0].plot(r["paso_bpb"], r["bpb"], color=cols[k], lw=2, label=nom[k])
axs[0].set_xlabel("paso"); axs[0].set_ylabel("bpb (validación)"); axs[0].set_title("Calidad: bits por byte"); axs[0].legend(fontsize=8)
ss = lambda v, w=10: np.convolve(v, np.ones(w) / w, mode="valid")
axs[1].plot(ss(RUNS["dc"]["F"]), color=AZUL, lw=2, label="F = fracción de bordes (no diferenciable)")
axs[1].plot(ss(RUNS["dc"]["G"]), color=NARANJA, lw=2, label="G = prob. media de borde (diferenciable)")
axs[1].axhline(1 / N_RATIO, color="crimson", ls="--", label=f"objetivo 1/N = {1/N_RATIO:.2f}"); axs[1].set_xlabel("paso"); axs[1].set_title("La ratio loss lleva F y G hacia 1/N"); axs[1].legend(fontsize=8)
for k in ["dc", "space"]:
    mm = RUNS[k]["modelo"]; xx, _ = lote(VA, 64, T_B, torch.Generator().manual_seed(3))
    with torch.no_grad(): inf_ = mm(xx)[1]
    b_ = inf_["b"].cpu().numpy(); w_ = inicios_espacio_t(xx).cpu().numpy()
    L_ = np.concatenate([np.diff(np.r_[np.flatnonzero(r_), len(r_)]) for r_ in b_])
    axs[2].hist(np.clip(L_, 1, 25), bins=np.arange(.5, 26.5, 1), alpha=.55, color=cols[k], label=f"{nom[k]} (media {L_.mean():.1f})", density=True)
axs[2].set_xlabel("bytes por chunk"); axs[2].set_title("Longitudes de chunk (val)"); axs[2].legend(fontsize=7)
plt.tight_layout(); plt.show()
'''

HNET_BOUNDARIES = r'''
fig, axs = plt.subplots(len(RUNS["dc"]["snap"]), 1, figsize=(12, 1.9 * len(RUNS["dc"]["snap"])), sharex=True)
for ax, (s, (p, xs_)) in zip(axs, RUNS["dc"]["snap"].items()):
    w_ = inicios_espacio_t(torch.from_numpy(xs_)[None])[0].numpy()
    ax.bar(range(len(p)), p, color=[NARANJA if v >= .5 else AZUL for v in p], width=.85)
    for i in np.flatnonzero(w_): ax.axvline(i, color="green", lw=.7, alpha=.5)
    ax.axhline(.5, color="crimson", ls="--", lw=.8); ax.set_ylabel(f"paso {s}\np_t", fontsize=8); ax.set_ylim(0, 1.05)
axs[-1].set_xticks(range(len(xs_))); axs[-1].set_xticklabels([("␣" if c == 32 else chr(c) if 32 < c < 127 else "·") for c in xs_], fontsize=5)
axs[0].set_title("Probabilidad de frontera p_t (naranja = borde; líneas verdes = inicio de palabra real) durante el entrenamiento", fontsize=9, loc="left")
plt.tight_layout(); plt.show()

mm = RUNS["dc"]["modelo"]; xx, _ = lote(VA, 128, T_B, torch.Generator().manual_seed(3))
with torch.no_grad(): b_ = mm(xx)[1]["b"].cpu().numpy()
w_ = inicios_espacio_t(xx).cpu().numpy(); tp = (b_ & w_).sum()
print(f"fronteras aprendidas vs inicios de palabra reales -> precisión={tp/max(1,b_.sum()):.2f} recall={tp/max(1,w_.sum()):.2f} "
      f"(azar con la misma densidad: precisión≈{w_.mean():.2f}, recall≈{b_.mean():.2f})")
'''

REPORTED_PLOT = r'''
# Cifras REPORTADAS por Hwang, Wang y Gu (2025), arXiv:2507.07955, Tabla 2 (FLOPs igualados a GPT-3 Large 760M / XL 1.3B, 100B tokens de FineWeb-Edu)
modelos = ["Transformer\n(BPE GPT-2)", "SpaceByte++", "H-Net\n(espacios)", "H-Net\n1 etapa", "H-Net\n2 etapas"]
bpb_L = [0.756, 0.760, 0.755, 0.755, 0.743]; acc_L = [53.3, 53.6, 53.4, 53.6, 55.5]
bpb_XL = [0.730, 0.733, 0.726, 0.728, 0.715]; acc_XL = [55.5, 56.1, 57.1, 56.2, 58.2]
fig, axs = plt.subplots(1, 2, figsize=(12, 3.8)); x = np.arange(5)
axs[0].bar(x - .2, bpb_L, .4, color=NARANJA, label="Large (760M FLOPs)"); axs[0].bar(x + .2, bpb_XL, .4, color=AZUL, label="XL (1.3B FLOPs)")
axs[0].set_ylim(.68, .78); axs[0].set_xticks(x); axs[0].set_xticklabels(modelos, fontsize=8); axs[0].set_ylabel("bpb FineWeb-Edu (menor = mejor)"); axs[0].legend(); axs[0].set_title("Bits por byte (reportado)")
axs[1].bar(x - .2, acc_L, .4, color=NARANJA); axs[1].bar(x + .2, acc_XL, .4, color=AZUL)
axs[1].set_ylim(50, 60); axs[1].set_xticks(x); axs[1].set_xticklabels(modelos, fontsize=8); axs[1].set_ylabel("media de 7 tareas zero-shot (%)"); axs[1].set_title("Precisión media (reportado)")
plt.tight_layout(); plt.show()
'''

# --------------------------------------------------------------------- tokenizer transfer

TT_DATA = r'''
def bytes_to_unicode():
    """Mapa GPT-2 byte -> carácter imprimible (el que usa ByteLevel). 1 carácter == 1 byte en el vocabulario."""
    bs = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256)); cs = bs[:]; n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b); cs.append(256 + n); n += 1
    return dict(zip(bs, map(chr, cs)))
B2U = bytes_to_unicode(); U2B = {v: k for k, v in B2U.items()}
tok_a_bytes = lambda s: bytes(U2B[c] for c in s)

from tokenizers import Tokenizer
SRC = [d for d in DOCS_TR if d["lang"] in ("en", "code")]            # "idioma de origen" del modelo base
TGT = [d for d in DOCS_TR if d["lang"] == "es"]                       # idioma destino de la adaptación
TGT_VA = [d for d in DOCS_VA if d["lang"] == "es"]
V_A, V_B = (512, 768) if FAST_DEV_RUN else (50257, 24000)
TK_A = entrena_bpe(SRC, V_A)                                          # tokenizer original (inglés + código)
TK_B = entrena_bpe(TGT, V_B)                                          # tokenizer nuevo (español)
if not FAST_DEV_RUN:
    try:
        TK_A = Tokenizer.from_pretrained("gpt2")                     # modo completo: GPT-2 de verdad (requiere acceso a Hugging Face)
        V_A = TK_A.get_vocab_size()
    except Exception as e:
        print("(sin acceso al hub; sigo con el BPE entrenado en local)", type(e).__name__)

VA_ES = "\n\n".join(d["text"][:MAX_CHARS] for d in TGT_VA)
def bytes_x_token(tk, txt): return len(txt.encode()) / len(tk.encode(txt).ids)
print(f"vocab A={TK_A.get_vocab_size()} | vocab B={TK_B.get_vocab_size()}")
print(f"bytes/token en ES (val): tokenizer A = {bytes_x_token(TK_A, VA_ES):.2f}  ->  tokenizer B = {bytes_x_token(TK_B, VA_ES):.2f}")
solap = set(TK_A.get_vocab()) & set(TK_B.get_vocab())
print(f"tokens de B que ya existen en A (se copian): {len(solap)} de {TK_B.get_vocab_size()} ({100*len(solap)/TK_B.get_vocab_size():.0f} %)")
'''

TT_MODEL = r'''
from transformers import GPT2Config, GPT2LMHeadModel
T_TOK = 64

def ids_stream(tk, docs_):
    return np.array(tk.encode("\n\n".join(d["text"][:MAX_CHARS] for d in docs_)).ids, dtype=np.int64)

def lote_ids(ids, B, T, g):
    ix = torch.randint(0, len(ids) - T - 1, (B,), generator=g)
    x = torch.stack([torch.from_numpy(ids[i:i + T]) for i in ix]); y = torch.stack([torch.from_numpy(ids[i + 1:i + T + 1]) for i in ix])
    return x.to(device), y.to(device)

def largo_bytes(tk):                                                   # bytes de cada token (en ByteLevel 1 carácter = 1 byte)
    return np.array([len(tok_a_bytes(t)) if all(c in U2B for c in t) else 1 for t, _ in sorted(tk.get_vocab().items(), key=lambda kv: kv[1])])

@torch.no_grad()
def bpb(model, tk, txt, T=T_TOK):
    """bits por byte sobre un texto (ventanas contiguas sin solape): la métrica comparable entre tokenizers."""
    ids = np.array(tk.encode(txt).ids, dtype=np.int64); LB = largo_bytes(tk); model.eval(); nll = nb = 0.0
    for i in range(0, len(ids) - T - 1, T):
        x = torch.from_numpy(ids[i:i + T])[None].to(device); y = torch.from_numpy(ids[i + 1:i + T + 1])[None].to(device)
        nll += F.cross_entropy(model(input_ids=x).logits[0], y[0], reduction="sum").item(); nb += LB[ids[i + 1:i + T + 1]].sum()
    return nll / math.log(2) / nb

def nuevo_gpt(vocab, d=128, L=3, H=4):
    return GPT2LMHeadModel(GPT2Config(vocab_size=vocab, n_positions=T_TOK, n_embd=d, n_layer=L, n_head=H,
                                      resid_pdrop=0.0, embd_pdrop=0.0, attn_pdrop=0.0, bos_token_id=0, eos_token_id=0)).to(device)

def entrena_lm(model, ids, pasos, lr=2e-3, params=None, log_cada=None, evalfn=None, seed=SEED):
    opt = torch.optim.AdamW(params if params is not None else model.parameters(), lr=lr); g = torch.Generator().manual_seed(seed); curva = []
    for s in range(pasos + 1):
        if log_cada and s % log_cada == 0: curva.append((s, evalfn(model)))
        if s == pasos: break
        model.train(); x, y = lote_ids(ids, 16, T_TOK, g)
        loss = F.cross_entropy(model(input_ids=x).logits.reshape(-1, model.config.vocab_size), y.reshape(-1))
        opt.zero_grad(); loss.backward(); opt.step()
    return curva

# --- Modelo base: preentrenado SOLO con inglés + código y el tokenizer A ---
t0 = time.time(); torch.manual_seed(SEED)
IDS_A_SRC = ids_stream(TK_A, SRC)
if FAST_DEV_RUN or TK_A.get_vocab_size() != 50257:
    BASE = nuevo_gpt(TK_A.get_vocab_size()); entrena_lm(BASE, IDS_A_SRC, 500 if FAST_DEV_RUN else 3000)
else:
    BASE = GPT2LMHeadModel.from_pretrained("gpt2").to(device)         # modo completo: GPT-2 small preentrenado (124M)
VA_SRC = "\n\n".join(d["text"][:MAX_CHARS] for d in DOCS_VA if d["lang"] in ("en", "code"))
print(f"modelo base listo en {time.time()-t0:.0f}s | bpb(val EN+código, tokenizer A) = {bpb(BASE, TK_A, VA_SRC):.3f}")
print(f"bpb(val ES, tokenizer A) ANTES de adaptar = {bpb(BASE, TK_A, VA_ES):.3f}   <- el modelo no ha visto español")
'''

TT_INITS = r'''
def sparsemax(z):
    """Martins & Astudillo (2016): proyección euclídea al simplex; produce pesos EXACTAMENTE cero fuera del soporte."""
    zs, _ = torch.sort(z, descending=True); k = torch.arange(1, len(z) + 1, device=z.device)
    cs = zs.cumsum(0); sop = (1 + k * zs) > cs; kz = int(sop.sum()); tau = (cs[kz - 1] - 1) / kz
    return torch.clamp(z - tau, min=0)

def vocab_ordenado(tk): return [t for t, _ in sorted(tk.get_vocab().items(), key=lambda kv: kv[1])]

def descomposicion(tk_old, token_str):
    """Ids del tokenizer ANTIGUO que componen el texto de un token nuevo (FVT/ZeTT). Si no es UTF-8 válido, usa bytes sueltos."""
    try:
        txt = tok_a_bytes(token_str).decode("utf-8")
        ids = tk_old.encode(txt).ids
        if ids: return ids
    except Exception:
        pass
    v = tk_old.get_vocab(); return [v[c] for c in token_str if c in v]

def base_copia(E_A, tkA, tkB, std=0.02):
    """Matriz [V_B, d] con los tokens compartidos copiados (cadena idéntica) y el resto sin inicializar (ceros)."""
    vA, VB = tkA.get_vocab(), vocab_ordenado(tkB); E = torch.zeros(len(VB), E_A.shape[1]); nuevo = []
    for i, t in enumerate(VB):
        if t in vA: E[i] = E_A[vA[t]]
        else: nuevo.append(i)
    return E, nuevo

def init_aleatoria(E_A, tkA, tkB):
    E, nuevo = base_copia(E_A, tkA, tkB); E[nuevo] = torch.randn(len(nuevo), E_A.shape[1]) * E_A.std(); return E

def init_media(E_A, tkA, tkB):                                         # todos los nuevos = media de los viejos
    E, nuevo = base_copia(E_A, tkA, tkB); E[nuevo] = E_A.mean(0); return E

def init_hewitt(E_A, tkA, tkB, escala=1.0):                            # muestreo de N(media, escala*covarianza) de los viejos
    E, nuevo = base_copia(E_A, tkA, tkB); mu = E_A.mean(0); C = torch.cov((E_A - mu).T) * escala + 1e-6 * torch.eye(E_A.shape[1])
    E[nuevo] = torch.distributions.MultivariateNormal(mu, C).sample((len(nuevo),)); return E

def init_fvt(E_A, tkA, tkB):                                           # Fast Vocabulary Transfer: media de la descomposición
    E, nuevo = base_copia(E_A, tkA, tkB); VB = vocab_ordenado(tkB)
    for i in nuevo: E[i] = E_A[descomposicion(tkA, VB[i])].mean(0)
    return E
'''

TT_AUX = r'''
def aux_embeddings(ids, V, ventana=4, dim=32):
    """Embeddings estáticos baratos (PPMI + SVD) de tokens: el 'fastText de juguete' que usan WECHSEL/FOCUS como espacio auxiliar."""
    C = np.zeros((V, V), np.float32)
    for k in range(1, ventana + 1):
        np.add.at(C, (ids[:-k], ids[k:]), 1.0); np.add.at(C, (ids[k:], ids[:-k]), 1.0)
    pr = C.sum(1, keepdims=True) / C.sum(); pmi = np.log((C / C.sum() + 1e-12) / (pr @ pr.T + 1e-12)); ppmi = np.maximum(pmi, 0)
    U, S, _ = np.linalg.svd(ppmi, full_matrices=False); W = U[:, :dim] * np.sqrt(S[:dim])
    return torch.from_numpy(W / (np.linalg.norm(W, axis=1, keepdims=True) + 1e-8)).float()

def init_focus(E_A, tkA, tkB, aux_B):
    """FOCUS (Dobler & de Melo, 2023): cada token NUEVO = combinación sparsemax de los tokens COMPARTIDOS, con pesos por similitud
    coseno en un espacio auxiliar entrenado sobre el idioma destino."""
    E, nuevo = base_copia(E_A, tkA, tkB); vA, VB = tkA.get_vocab(), vocab_ordenado(tkB)
    comp = [i for i, t in enumerate(VB) if t in vA]; Ec = E[comp]; Ac = aux_B[comp]
    for i in nuevo:
        w = sparsemax(Ac @ aux_B[i]); E[i] = (w[:, None] * Ec).sum(0) if w.sum() > 0 else E_A.mean(0)
    return E

def init_wechsel(E_A, tkA, tkB, aux_A, aux_B, k=10, tau=0.1):
    """WECHSEL (Minixhofer et al., 2022): espacio auxiliar de A y de B alineado con Procrustes (diccionario = tokens compartidos);
    cada token nuevo = media ponderada (softmax(cos/tau)) de los k tokens de A más parecidos."""
    from scipy.linalg import orthogonal_procrustes
    E, nuevo = base_copia(E_A, tkA, tkB); vA, VB = tkA.get_vocab(), vocab_ordenado(tkB)
    par = [(vA[t], i) for i, t in enumerate(VB) if t in vA]
    R, _ = orthogonal_procrustes(aux_B[[i for _, i in par]].numpy(), aux_A[[a for a, _ in par]].numpy()); R = torch.from_numpy(R).float()
    S = (aux_B[nuevo] @ R) @ aux_A.T                                    # similitud coseno (filas ya normalizadas)
    top = S.topk(k, dim=1); W = F.softmax(top.values / tau, dim=1)
    E[nuevo] = torch.einsum("nk,nkd->nd", W, E_A[top.indices]); return E
'''

TT_RUN = r'''
E_A = BASE.get_input_embeddings().weight.detach().cpu().float()
IDS_B_TGT = ids_stream(TK_B, TGT); IDS_A_TGT = ids_stream(TK_A, TGT)
aux_B = aux_embeddings(IDS_B_TGT, TK_B.get_vocab_size()); aux_A = aux_embeddings(IDS_A_SRC, TK_A.get_vocab_size())
torch.manual_seed(SEED)
INITS = {"aleatoria": init_aleatoria(E_A, TK_A, TK_B), "media": init_media(E_A, TK_A, TK_B),
         "Hewitt (N(μ,Σ))": init_hewitt(E_A, TK_A, TK_B), "FVT (media de subtokens)": init_fvt(E_A, TK_A, TK_B),
         "FOCUS-lite": init_focus(E_A, TK_A, TK_B, aux_B), "WECHSEL-lite": init_wechsel(E_A, TK_A, TK_B, aux_A, aux_B)}

def instala_vocab(base, E_new):
    m = copy.deepcopy(base); m.resize_token_embeddings(E_new.shape[0], mean_resizing=False)
    m.get_input_embeddings().weight.data.copy_(E_new.to(device)); m.tie_weights(); return m

K1, K2 = (100, 200) if FAST_DEV_RUN else (500, 2000)
eval_B = lambda m: bpb(m, TK_B, VA_ES)
CURVAS, CEROSHOT = {}, {}
t0 = time.time()
for nombre, E_new in INITS.items():
    m = instala_vocab(BASE, E_new); CEROSHOT[nombre] = eval_B(m)
    for p_ in m.parameters(): p_.requires_grad = False
    m.get_input_embeddings().weight.requires_grad = True              # fase 1: SOLO embeddings (la cabeza está atada)
    c1 = entrena_lm(m, IDS_B_TGT, K1, lr=3e-3, params=[m.get_input_embeddings().weight], log_cada=25, evalfn=eval_B)
    for p_ in m.parameters(): p_.requires_grad = True                  # fase 2: todo el modelo
    c2 = entrena_lm(m, IDS_B_TGT, K2, lr=1e-3, log_cada=25, evalfn=eval_B)
    CURVAS[nombre] = c1[:-1] + [(s + K1, v) for s, v in c2]
    print(f"{nombre:26s} bpb 0-shot={CEROSHOT[nombre]:.3f} | tras {K1} pasos (emb) = {c1[-1][1]:.3f} | final = {c2[-1][1]:.3f}")
print(f"({time.time()-t0:.0f}s)")
'''

TT_CONTROLS = r'''
# Controles: (a) seguir con el tokenizer A (solo ajuste fino en español) y (b) entrenar desde cero con el tokenizer B
t0 = time.time(); ev_A = lambda m: bpb(m, TK_A, VA_ES)
mA = copy.deepcopy(BASE); cA = entrena_lm(mA, IDS_A_TGT, K1 + K2, lr=1e-3, log_cada=25, evalfn=ev_A)
torch.manual_seed(SEED); mS = nuevo_gpt(TK_B.get_vocab_size()); cS = entrena_lm(mS, IDS_B_TGT, K1 + K2, lr=2e-3, log_cada=25, evalfn=eval_B)
CURVAS["control: seguir con A"] = cA; CURVAS["control: desde cero con B"] = cS
print(f"control A: {cA[0][1]:.3f} -> {cA[-1][1]:.3f} | desde cero con B: {cS[0][1]:.3f} -> {cS[-1][1]:.3f} ({time.time()-t0:.0f}s)")
'''

TT_PLOTS = r'''
nombres = list(INITS)
fig, axs = plt.subplots(1, 3, figsize=(15, 4))
bars = axs[0].bar(range(len(nombres)), [CEROSHOT[n] for n in nombres], color=[GRIS, GRIS, GRIS, NARANJA, AZUL, VERDE])
axs[0].axhline(bpb(BASE, TK_A, VA_ES), color="crimson", ls="--", label="base con tokenizer A (no adaptado)")
axs[0].set_xticks(range(len(nombres))); axs[0].set_xticklabels([n.replace(" (", "\n(") for n in nombres], fontsize=7, rotation=0)
axs[0].set_ylabel("bpb en ES (cero-shot, justo tras cambiar de tokenizer)"); axs[0].set_title("Antes de entrenar: ¿qué init sobrevive?"); axs[0].legend(fontsize=8)
paleta = {"aleatoria": "#9aa0a6", "media": "#6B7280", "Hewitt (N(μ,Σ))": "#b6a37a", "FVT (media de subtokens)": NARANJA, "FOCUS-lite": AZUL, "WECHSEL-lite": VERDE,
          "control: seguir con A": "crimson", "control: desde cero con B": "black"}
for n, c in CURVAS.items():
    axs[1].plot([s for s, _ in c], [v for _, v in c], color=paleta[n], lw=2, ls="--" if n.startswith("control") else "-", label=n)
axs[1].axvline(K1, color="k", lw=.6, ls=":"); axs[1].set_ylim(top=min(axs[1].get_ylim()[1], 6)); axs[1].set_xlabel("pasos (a la izquierda de la línea punteada: solo embeddings)")
axs[1].set_ylabel("bpb en ES (validación)"); axs[1].set_title("Adaptación corta"); axs[1].legend(fontsize=6)
axs[2].bar(range(len(nombres)), [dict(CURVAS[n])[K1] for n in nombres], color=[paleta[n] for n in nombres])
axs[2].set_xticks(range(len(nombres))); axs[2].set_xticklabels([n.replace(" (", "\n(") for n in nombres], fontsize=7)
axs[2].set_title(f"bpb tras {K1} pasos (solo embeddings)"); plt.tight_layout(); plt.show()
'''

TT_PCA = r'''
fig, axs = plt.subplots(2, 3, figsize=(12, 7)); P0 = torch.pca_lowrank(E_A - E_A.mean(0), q=2)[2]
vA = TK_A.get_vocab(); VB = vocab_ordenado(TK_B); es_nuevo = np.array([t not in vA for t in VB])
for ax, (n, E) in zip(axs.ravel(), INITS.items()):
    old = ((E_A - E_A.mean(0)) @ P0).numpy(); new = ((E - E_A.mean(0)) @ P0).numpy()
    ax.scatter(old[:, 0], old[:, 1], s=6, color=GRIS, alpha=.4, label="viejos (A)")
    ax.scatter(new[es_nuevo, 0], new[es_nuevo, 1], s=8, color=NARANJA, alpha=.7, label="nuevos (B∖A)")
    ax.set_title(f"{n}\nvar. nuevos / var. viejos = {E[es_nuevo].var(0).sum()/E_A.var(0).sum():.2f}", fontsize=8); ax.legend(fontsize=6)
plt.suptitle("Proyección PCA de los embeddings: dónde coloca cada método a los tokens nuevos", y=1.0); plt.tight_layout(); plt.show()
'''

TT_FERT = r'''
fig, ax = plt.subplots(figsize=(7, 3.6)); langs = ["es", "en", "code"]
for k, (tk, nombre, col) in enumerate([(TK_A, "tokenizer A (EN+código)", NARANJA), (TK_B, "tokenizer B (ES)", AZUL)]):
    vals = [np.mean([bytes_x_token(tk, d["text"][:MAX_CHARS]) for d in DOCS_VA if d["lang"] == l]) for l in langs]
    ax.bar(np.arange(3) + (k - .5) * .38, vals, .38, color=col, label=nombre)
ax.set_xticks(range(3)); ax.set_xticklabels(langs); ax.set_ylabel("bytes por token (más = menos tokens)"); ax.set_title("Lo que ganas al cambiar de tokenizer"); ax.legend(); plt.show()
'''

TT_MEAN_RESIZE = r'''
# Lo que hace Hugging Face por defecto al ampliar el vocabulario: resize_token_embeddings(mean_resizing=True)
m_hf = copy.deepcopy(BASE); n0 = m_hf.get_input_embeddings().weight.shape[0]
m_hf.resize_token_embeddings(n0 + 50, mean_resizing=True)
W = m_hf.get_input_embeddings().weight.detach().cpu()
old_mu, old_sd = W[:n0].mean(0), W[:n0].std(0).mean()
print("¿los 50 tokens nuevos están en la media de los viejos? distancia media a la media:",
      float((W[n0:] - old_mu).norm(dim=1).mean()), "| norma media de un embedding viejo:", float(W[:n0].norm(dim=1).mean()))
print("=> con mean_resizing=True los nuevos son casi idénticos entre sí (la covarianza se escala por 1e-9 en el código fuente de transformers).")
'''
