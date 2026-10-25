"""Celdas de código del módulo 08 (cadenas). Las usan build_08.py y _a3_proj08.py."""

PIP = "!pip install -q torch torchvision torchaudio numpy matplotlib scikit-learn scipy transformers"

SETUP8 = r'''
import re, io
import matplotlib.pyplot as plt
import torch.nn as nn, torch.nn.functional as F
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": .25,
                     "axes.spines.top": False, "axes.spines.right": False})
AZUL, NARANJA, VERDE, GRIS = "#1F6FEB", "#F28E2B", "#2CA02C", "#6B7280"
'''

# ------------------------------------------------------------------ presupuesto de tokens
TOKEN_BUDGET = r'''
# Tasas de tokens por modalidad. Cada fila = (descripción, tokens, fuente/fórmula). Todo es aritmética sobre cifras de los papers
# o de la arquitectura; las aproximaciones están marcadas con "~".
def tokens_vit(res, p): return (res // p) ** 2
def tokens_video(frames, h, w, ct, cs): return -(-frames // ct) * (h // cs) * (w // cs)          # ~ (T/ct)·(H/cs)·(W/cs)
def tokens_audio(seg, hz, nq): return seg * hz * nq

FILAS = [
    ("Texto: 1 min de habla transcrita (~150 palabras)",           int(150 * 1.3),                     "~1.3 tokens/palabra (orden de magnitud)"),
    ("Imagen ViT-B/16, 224²",                                      tokens_vit(224, 16),                "(224/16)²"),
    ("Imagen ViT-L/14, 336²",                                      tokens_vit(336, 14),                "(336/14)²"),
    ("Imagen Chameleon, 512² (VQ, codebook 8192)",                 1024,                               "Chameleon Team 2024: 512x512 -> 1024 tokens"),
    ("Imagen TiTok (tokenizer 1D)",                                32,                                 "Yu et al. 2024: 'An Image is Worth 32 Tokens'"),
    ("Imagen Cosmos DI16x16, 512² (FSQ 64 000)",                   tokens_vit(512, 16),                "512/16 en cada eje"),
    ("Audio 1 min EnCodec 24 kHz @1.5 kbps (2 codebooks)",         tokens_audio(60, 75, 2),            "75 Hz x 2"),
    ("Audio 1 min EnCodec 24 kHz @6 kbps (8 codebooks)",           tokens_audio(60, 75, 8),            "75 Hz x 8"),
    ("Audio 1 min Mimi (12.5 Hz x 8 codebooks, aplanado)",         tokens_audio(60, 12.5, 8),          "Mimi: 12.5 Hz, 8 x 2048, 1.1 kbps"),
    ("Vídeo 5 s, 24 fps, 720p, Cosmos DV8x16x16 (~)",              tokens_video(120, 720, 1280, 8, 16), "~ (T/8)·(H/16)·(W/16)"),
]
df_tok = [(n, int(t), f) for n, t, f in FILAS]
for n, t, f in df_tok:
    print(f"{n:55s} {t:>9,d} tokens   [{f}]")
print("\n1 h de audio EnCodec@6kbps =", f"{tokens_audio(3600, 75, 8):,}", "tokens | ventana de 128K tokens =", f"{128_000/tokens_audio(1, 75, 8)/60:.1f} min de audio")

fig, ax = plt.subplots(figsize=(9, 4.2)); nom = [n.split(" (")[0] if len(n) > 40 else n for n, _, _ in df_tok]; val = [t for _, t, _ in df_tok]
cols = [GRIS] + [AZUL] * 5 + [NARANJA] * 3 + [VERDE]
ax.barh(range(len(val)), val, color=cols); ax.set_yticks(range(len(val))); ax.set_yticklabels(nom, fontsize=7); ax.invert_yaxis()
ax.axvline(128_000, color="crimson", ls="--", lw=1, label="ventana de contexto de 128K tokens"); ax.set_xscale("log"); ax.set_xlabel("tokens (escala log)")
for i, v in enumerate(val): ax.text(v * 1.1, i, f"{v:,}", va="center", fontsize=7)
ax.set_title("¿Cuánto contexto cuesta cada modalidad?"); ax.legend(fontsize=8); plt.tight_layout(); plt.show()
'''

# ------------------------------------------------------------------ datos de imagen
DATA_IMG = r'''
from PIL import Image, ImageDraw

def mnist_sintetico(n, seed=SEED):
    """Respaldo sin red: figuras geométricas 28x28 (círculo, cuadrado, cruz, triángulo) con posición/tamaño aleatorios."""
    r = np.random.RandomState(seed); X = np.zeros((n, 1, 28, 28), np.float32); y = r.randint(0, 4, n)
    for i in range(n):
        im = Image.new("L", (28, 28)); d = ImageDraw.Draw(im); c = r.randint(9, 19, 2); s = r.randint(4, 9)
        box = [c[0] - s, c[1] - s, c[0] + s, c[1] + s]
        if y[i] == 0: d.ellipse(box, outline=255, width=2)
        elif y[i] == 1: d.rectangle(box, outline=255, width=2)
        elif y[i] == 2: d.line([c[0] - s, c[1], c[0] + s, c[1]], fill=255, width=2); d.line([c[0], c[1] - s, c[0], c[1] + s], fill=255, width=2)
        else: d.polygon([(c[0], c[1] - s), (c[0] - s, c[1] + s), (c[0] + s, c[1] + s)], outline=255)
        X[i, 0] = np.asarray(im, np.float32) / 255
    return torch.from_numpy(X), torch.from_numpy(y)

def carga_imagenes(n):
    try:
        from torchvision import datasets
        ds = datasets.MNIST("./data", train=True, download=True)
        return ds.data[:n].float().div(255).unsqueeze(1), ds.targets[:n], "MNIST real"
    except Exception as e:
        print("[aviso] MNIST no disponible (", type(e).__name__, ") -> figuras SINTÉTICAS 28x28")
        X, y = mnist_sintetico(n); return X, y, "sintético (4 clases)"

N_IMG = 6000 if FAST_DEV_RUN else 60000
X_ALL, Y_ALL, FUENTE_IMG = carga_imagenes(N_IMG + 1000)
X_TR, X_TE, Y_TR, Y_TE = X_ALL[:N_IMG].to(device), X_ALL[N_IMG:].to(device), Y_ALL[:N_IMG].to(device), Y_ALL[N_IMG:].to(device)
N_CLASES = int(Y_ALL.max()) + 1
print(f"imágenes: {FUENTE_IMG} | train={tuple(X_TR.shape)} test={tuple(X_TE.shape)} | {N_CLASES} clases")

def foto(nombre="china.jpg"):
    """Foto real que viene EMPAQUETADA con scikit-learn (sin descargas); respaldo sintético si no está."""
    try:
        from sklearn.datasets import load_sample_image
        return Image.fromarray(load_sample_image(nombre)), "foto real (scikit-learn)"
    except Exception:
        r = np.random.RandomState(0); yy, xx = np.mgrid[0:427, 0:640]
        im = np.stack([128 + 100 * np.sin(xx / 40 + k) * np.cos(yy / (30 + 10 * k)) + r.randn(427, 640) * 6 for k in range(3)], -1)
        return Image.fromarray(np.clip(im, 0, 255).astype(np.uint8)), "imagen sintética"
'''

# ------------------------------------------------------------------ ViT patches
VIT = r'''
def patchify(img, p):
    """[B,C,H,W] -> [B, N, C*p*p]: un 'token' continuo por parche p x p (ViT)."""
    B, C, H, W = img.shape
    x = img.unfold(2, p, p).unfold(3, p, p)                        # [B,C,H/p,W/p,p,p]
    return x.permute(0, 2, 3, 1, 4, 5).reshape(B, (H // p) * (W // p), C * p * p)

im, fuente = foto("china.jpg"); im224 = im.resize((224, 224))
x = torch.from_numpy(np.asarray(im224, np.float32) / 255).permute(2, 0, 1)[None]
tok = patchify(x, 16)
D = 192; conv = nn.Conv2d(3, D, 16, stride=16)                      # la 'patch embedding' real de ViT = una convolución
via_conv = conv(x).flatten(2).transpose(1, 2)
via_lineal = tok @ conv.weight.view(D, -1).T + conv.bias
print(f"{fuente} | parches: {tuple(tok.shape)} = (1, {224//16}², 3·16·16) | conv == lineal sobre parches: {torch.allclose(via_conv, via_lineal, atol=1e-5)}")

fig, axs = plt.subplots(1, 3, figsize=(14, 4))
axs[0].imshow(im224); axs[0].set_title("Imagen 224x224 con rejilla de parches 16x16 (196 tokens)", fontsize=9)
for k in range(0, 224, 16): axs[0].axvline(k, color="w", lw=.5); axs[0].axhline(k, color="w", lw=.5)
axs[0].grid(False); axs[0].axis("off")
for j in range(6):
    r, c = divmod(j * 31 + 40, 14); axs[1].imshow(np.asarray(im224)[r*16:(r+1)*16, c*16:(c+1)*16], extent=(j, j + .95, 0, 1));
axs[1].set_xlim(0, 6); axs[1].set_ylim(0, 1); axs[1].set_title("Seis parches = seis 'tokens' (cada uno -> vector de 768 números)", fontsize=9); axs[1].axis("off")
res = np.arange(224, 1281, 32)
for p, col in [(32, VERDE), (16, AZUL), (14, NARANJA), (8, GRIS)]:
    axs[2].plot(res, (res // p) ** 2, color=col, lw=2, label=f"parche {p}")
axs[2].set_yscale("log"); axs[2].set_xlabel("resolución (lado, píxeles)"); axs[2].set_ylabel("tokens por imagen"); axs[2].axhline(128_000 / 100, color="crimson", ls=":", lw=1)
axs[2].set_title("Tokens vs resolución (la atención cuesta ~N²)", fontsize=9); axs[2].legend(fontsize=8); plt.tight_layout(); plt.show()
'''

# ------------------------------------------------------------------ cuantizadores
QUANTIZERS = r'''
class VQ(nn.Module):
    """Cuantizador vectorial (van den Oord et al., 2017). z: [B,d,*] -> zq (con STE), pérdida, índices [B,*]."""
    def __init__(self, K, d, beta=0.25):
        super().__init__(); self.K, self.d, self.beta = K, d, beta
        self.cb = nn.Embedding(K, d); self.cb.weight.data.uniform_(-1 / K, 1 / K)
        self.register_buffer("inicializado", torch.tensor(False)); self.register_buffer("uso", torch.ones(K))
    def forward(self, z, reinicia=False):
        shape = z.shape; zf = z.movedim(1, -1).reshape(-1, self.d)
        if self.training and not bool(self.inicializado):                       # init por datos: codebook = vectores del encoder
            self.cb.weight.data.copy_(zf[torch.randperm(len(zf), device=z.device)[:self.K]].detach()); self.inicializado.fill_(True)
        dist = zf.pow(2).sum(1, keepdim=True) - 2 * zf @ self.cb.weight.T + self.cb.weight.pow(2).sum(1)
        idx = dist.argmin(1); e = self.cb(idx)
        loss = F.mse_loss(e, zf.detach()) + self.beta * F.mse_loss(zf, e.detach())     # ||sg[z]-e||² + β||z-sg[e]||²
        if self.training:
            self.uso.mul_(0.99).add_(torch.bincount(idx, minlength=self.K).float(), alpha=0.01 * 1.0)
            if reinicia:                                                                  # reinicio de códigos muertos
                muertos = self.uso < 1e-3 * len(idx) / self.K
                if muertos.any(): self.cb.weight.data[muertos] = zf[torch.randint(len(zf), (int(muertos.sum()),), device=z.device)].detach()
        zq = zf + (e - zf).detach()                                                       # straight-through estimator
        return zq.reshape(*shape[:1], *shape[2:], self.d).movedim(-1, 1), loss, idx.reshape(shape[0], *shape[2:])

class FSQ(nn.Module):
    """Finite Scalar Quantization (Mentzer et al., 2023): acota cada canal y lo redondea a L_i niveles; sin codebook ni pérdidas extra."""
    def __init__(self, levels):
        super().__init__(); L = torch.tensor(levels); self.register_buffer("L", L); self.d = len(levels)
        self.register_buffer("basis", torch.cumprod(torch.tensor([1] + list(levels[:-1])), 0)); self.K = int(L.prod())
    def forward(self, z, reinicia=False):
        zp = z.movedim(1, -1); half = (self.L - 1) * (1 - 1e-3) / 2; off = torch.where(self.L % 2 == 0, 0.5, 0.0); shift = torch.atanh(off / half)
        b = torch.tanh(zp + shift) * half - off; q = b + (torch.round(b) - b).detach()          # acota + redondea (STE)
        hw = (self.L // 2).float(); idx = ((q + hw) * self.basis).sum(-1).long()
        return (q / hw).movedim(-1, 1), z.new_zeros(()), idx

class RVQ(nn.Module):
    """Cuantización vectorial residual: cada nivel cuantiza lo que el anterior dejó sin explicar."""
    def __init__(self, Q, K, d, beta=0.25):
        super().__init__(); self.Q, self.K = Q, K; self.capas = nn.ModuleList([VQ(K, d, beta) for _ in range(Q)])
    def forward(self, z, reinicia=False, n_q=None):
        res, out, loss, idxs = z, 0, 0, []
        for capa in self.capas[: (n_q or self.Q)]:
            q, l, idx = capa(res, reinicia); res = res - q.detach(); out = out + q; loss = loss + l; idxs.append(idx)
        return out, loss, torch.stack(idxs, 1)

def perplexity(idx, K):
    p = torch.bincount(idx.flatten(), minlength=K).float(); p = p / p.sum()
    return float(torch.exp(-(p[p > 0] * p[p > 0].log()).sum()))

def psnr(x, y, peak=1.0):
    mse = F.mse_loss(x, y).item(); return 10 * math.log10(peak ** 2 / max(mse, 1e-10))
'''

AE_MODEL = r'''
class AE2D(nn.Module):
    """Autoencoder convolucional 28x28 -> 7x7 con un cuantizador enchufable (VQ / FSQ / RVQ)."""
    def __init__(self, quant, d, ch=32):
        super().__init__()
        self.enc = nn.Sequential(nn.Conv2d(1, ch, 4, 2, 1), nn.ReLU(), nn.Conv2d(ch, 2 * ch, 4, 2, 1), nn.ReLU(), nn.Conv2d(2 * ch, d, 1))
        self.quant = quant
        self.dec = nn.Sequential(nn.Conv2d(d, 2 * ch, 3, 1, 1), nn.ReLU(), nn.ConvTranspose2d(2 * ch, ch, 4, 2, 1), nn.ReLU(),
                                 nn.ConvTranspose2d(ch, 1, 4, 2, 1), nn.Sigmoid())
    def forward(self, x, reinicia=False, **kw):
        z = self.enc(x); zq, ql, idx = self.quant(z, reinicia, **kw); return self.dec(zq), ql, idx

def entrena_ae(modelo, pasos, B=128, lr=2e-3, seed=SEED, reinicia_cada=50, **kw):
    g = torch.Generator().manual_seed(seed); opt = torch.optim.Adam(modelo.parameters(), lr=lr); hist = []
    for s in range(pasos):
        modelo.train(); ix = torch.randint(0, len(X_TR), (B,), generator=g).to(device); x = X_TR[ix]
        xr, ql, idx = modelo(x, reinicia=(reinicia_cada and s % reinicia_cada == 0 and s > 0), **kw)
        rec = F.mse_loss(xr, x); loss = rec + ql; opt.zero_grad(); loss.backward(); opt.step()
        if s % 20 == 0: hist.append((s, rec.item(), perplexity(idx[:, 0] if idx.dim() == 4 else idx, modelo.quant.K)))
    return hist

@torch.no_grad()
def evalua_ae(modelo, **kw):
    modelo.eval(); xr, _, idx = modelo(X_TE, **kw)
    return {"psnr": psnr(xr, X_TE), "ppl": perplexity(idx[:, 0] if idx.dim() == 4 else idx, modelo.quant.K), "idx": idx, "xr": xr}
'''

VQ_BASE = r'''
PASOS_AE = 400 if FAST_DEV_RUN else 3000
torch.manual_seed(SEED); t0 = time.time()
K0, D0 = 64, 16
vq = AE2D(VQ(K0, D0), D0).to(device); h_vq = entrena_ae(vq, PASOS_AE); r_vq = evalua_ae(vq)
tokens_por_img = r_vq["idx"].shape[1] * r_vq["idx"].shape[2]
print(f"VQ-VAE K={K0}: {time.time()-t0:.0f}s | PSNR test = {r_vq['psnr']:.2f} dB | perplejidad = {r_vq['ppl']:.1f} de {K0} | "
      f"{tokens_por_img} tokens/img = {tokens_por_img*math.log2(K0):.0f} bits (vs {28*28*8} bits en bruto: {28*28*8/(tokens_por_img*math.log2(K0)):.0f}x menos)")

fig, axs = plt.subplots(3, 8, figsize=(13, 5.6))
for j in range(8):
    axs[0, j].imshow(X_TE[j, 0].cpu(), cmap="gray"); axs[1, j].imshow(r_vq["xr"][j, 0].cpu(), cmap="gray")
    axs[2, j].imshow(r_vq["idx"][j].cpu(), cmap="tab20", vmin=0, vmax=K0)
    for i in range(7):
        for k in range(7): axs[2, j].text(k, i, int(r_vq["idx"][j, i, k]), ha="center", va="center", fontsize=4.5)
    for i in range(3): axs[i, j].axis("off")
for i, t in enumerate(["original", "reconstrucción desde 49 tokens", "mapa de tokens 7x7 (ids)"]): axs[i, 0].set_title(t, fontsize=8, loc="left")
plt.tight_layout(); plt.show()
'''

VQ_SWEEP = r'''
# Barrido de K (tamaño del codebook) + el fenómeno de colapso: sin trucos vs con init por datos + reinicio de códigos muertos
class VQsimple(VQ):
    """VQ SIN los trucos de uso (sin init por datos, sin reinicio): codebook inicial pequeño y aleatorio."""
    def forward(self, z, reinicia=False):
        self.inicializado.fill_(True); return super().forward(z, reinicia=False)

res_K, t0 = {}, time.time()
for K in [4, 16, 64, 256, 1024]:
    torch.manual_seed(SEED); m = AE2D(VQ(K, D0), D0).to(device); entrena_ae(m, PASOS_AE); r = evalua_ae(m); res_K[K] = (r["psnr"], r["ppl"], 49 * math.log2(K))
torch.manual_seed(SEED); m_c = AE2D(VQsimple(256, D0), D0).to(device); entrena_ae(m_c, PASOS_AE, reinicia_cada=0); r_c = evalua_ae(m_c)
print(f"({time.time()-t0:.0f}s)")
for K, (p, pp, b) in res_K.items(): print(f"K={K:5d}: PSNR={p:5.2f} dB | perplejidad={pp:6.1f} ({100*pp/K:5.1f}% del codebook 'efectivo') | {b:6.0f} bits/img")
print(f"K=256 SIN trucos: PSNR={r_c['psnr']:.2f} dB | perplejidad={r_c['ppl']:.1f}")

fig, axs = plt.subplots(1, 3, figsize=(14, 3.8))
Ks = list(res_K); axs[0].plot([res_K[k][2] for k in Ks], [res_K[k][0] for k in Ks], "o-", color=AZUL, lw=2)
for k in Ks: axs[0].annotate(f"K={k}", (res_K[k][2], res_K[k][0]), fontsize=7, xytext=(3, -10), textcoords="offset points")
axs[0].set_xlabel("bits por imagen (49 tokens x log2 K)"); axs[0].set_ylabel("PSNR test (dB)"); axs[0].set_title("Tasa-distorsión del VQ-VAE")
axs[1].bar([str(k) for k in Ks], [res_K[k][1] / k for k in Ks], color=AZUL); axs[1].set_ylabel("perplejidad / K"); axs[1].set_xlabel("K"); axs[1].set_title("Uso efectivo del codebook (1 = uniforme)")
u1 = torch.bincount(r_vq["idx"].flatten(), minlength=K0).cpu().numpy(); u2 = torch.bincount(r_c["idx"].flatten(), minlength=256).cpu().numpy()
axs[2].bar(range(256), np.sort(u2)[::-1], color=NARANJA, label="K=256 sin trucos"); axs[2].set_yscale("log"); axs[2].set_xlabel("códigos ordenados por frecuencia"); axs[2].set_ylabel("usos en test"); axs[2].set_title("Colapso del codebook"); axs[2].legend(fontsize=8)
plt.tight_layout(); plt.show()
'''

FSQ_RVQ = r'''
t0 = time.time(); R = {}
torch.manual_seed(SEED); m = AE2D(VQ(256, D0), D0).to(device); entrena_ae(m, PASOS_AE); r = evalua_ae(m); R["VQ K=256"] = (r["psnr"], r["ppl"], 256, 49 * 8)
torch.manual_seed(SEED); fsq = FSQ([8, 6, 5]); m = AE2D(fsq, 3).to(device); entrena_ae(m, PASOS_AE); r = evalua_ae(m); R["FSQ [8,6,5]"] = (r["psnr"], r["ppl"], fsq.K, 49 * math.log2(fsq.K))
torch.manual_seed(SEED); rvq = RVQ(4, 16, D0); m_rvq = AE2D(rvq, D0).to(device)
def paso_rvq(m, pasos, B=128, lr=2e-3):                         # entrenamiento con 'quantizer dropout': n_q aleatorio por lote
    opt = torch.optim.Adam(m.parameters(), lr=lr); g = torch.Generator().manual_seed(SEED)
    for s in range(pasos):
        m.train(); ix = torch.randint(0, len(X_TR), (B,), generator=g).to(device); x = X_TR[ix]; nq = int(torch.randint(1, 5, (1,), generator=g))
        xr, ql, _ = m(x, reinicia=(s % 50 == 0 and s > 0), n_q=nq); loss = F.mse_loss(xr, x) + ql; opt.zero_grad(); loss.backward(); opt.step()
paso_rvq(m_rvq, PASOS_AE)
RV = {nq: evalua_ae(m_rvq, n_q=nq) for nq in [1, 2, 3, 4]}
for nq, r in RV.items(): print(f"RVQ con {nq} niveles (K=16): PSNR={r['psnr']:.2f} dB | {49*4*nq} bits/img")
print({k: f"PSNR={v[0]:.2f}, perplejidad={v[1]:.0f}/{v[2]}" for k, v in R.items()}, f"({time.time()-t0:.0f}s)")

fig, axs = plt.subplots(1, 3, figsize=(14, 3.8)); b0 = [R[k][3] for k in R]
axs[0].bar(list(R), [R[k][0] for k in R], color=[AZUL, VERDE]); axs[0].set_ylim(min(R[k][0] for k in R) - 2, None); axs[0].set_ylabel("PSNR test (dB)"); axs[0].set_title("VQ vs FSQ (~256 códigos)")
axs[1].bar(list(R), [100 * R[k][1] / R[k][2] for k in R], color=[AZUL, VERDE]); axs[1].set_ylabel("perplejidad / |C| (%)"); axs[1].set_title("Uso del 'vocabulario' de códigos")
axs[2].plot([49 * 4 * nq for nq in RV], [RV[nq]["psnr"] for nq in RV], "o-", color=NARANJA, lw=2, label="RVQ (Q niveles, K=16)")
axs[2].plot([res_K[k][2] for k in [4, 16, 64, 256]], [res_K[k][0] for k in [4, 16, 64, 256]], "s--", color=AZUL, label="VQ simple (barrido de K)")
axs[2].set_xlabel("bits por imagen"); axs[2].set_ylabel("PSNR (dB)"); axs[2].set_title("Un único modelo RVQ cubre varias tasas"); axs[2].legend(fontsize=8)
plt.tight_layout(); plt.show()
'''

PRIOR = r'''
# Mini-Chameleon: un LM sobre tokens de imagen. Secuencia = [token de clase] + 49 tokens VQ; vocabulario unificado (códigos + clases).
class TinyGPT(nn.Module):
    def __init__(self, vocab, d=96, L=3, ctx=64, H=4):
        super().__init__(); self.emb, self.pos = nn.Embedding(vocab, d), nn.Embedding(ctx, d)
        layer = nn.TransformerEncoderLayer(d, H, 4 * d, dropout=0.0, batch_first=True, norm_first=True, activation="gelu")
        self.tr = nn.TransformerEncoder(layer, L, enable_nested_tensor=False); self.ln, self.head = nn.LayerNorm(d), nn.Linear(d, vocab, bias=False)
    def forward(self, x):
        T = x.shape[1]; h = self.emb(x) + self.pos(torch.arange(T, device=x.device)); m = torch.triu(torch.ones(T, T, dtype=torch.bool, device=x.device), 1)
        return self.head(self.ln(self.tr(h, mask=m, is_causal=True)))

with torch.no_grad():
    vq.eval(); idx_tr = torch.cat([vq(X_TR[i:i + 500])[2].flatten(1) for i in range(0, len(X_TR), 500)])        # [N,49] tokens de cada imagen
SEQ = torch.cat([(K0 + Y_TR).unsqueeze(1), idx_tr], 1)                                                         # prefijo = "palabra" de clase
V = K0 + N_CLASES
gpt = TinyGPT(V, ctx=SEQ.shape[1]).to(device); opt = torch.optim.AdamW(gpt.parameters(), lr=2e-3); g = torch.Generator().manual_seed(SEED)
t0 = time.time(); PASOS_P = 400 if FAST_DEV_RUN else 3000
for s in range(PASOS_P):
    b = SEQ[torch.randint(0, len(SEQ), (64,), generator=g).to(device)]; loss = F.cross_entropy(gpt(b[:, :-1]).reshape(-1, V), b[:, 1:].reshape(-1))
    opt.zero_grad(); loss.backward(); opt.step()
print(f"LM sobre tokens de imagen: {time.time()-t0:.0f}s | NLL final = {loss.item():.2f} nats/token (ruido uniforme: {math.log(K0):.2f})")

@torch.no_grad()
def genera(clase, n=8, temp=0.9):
    x = torch.full((n, 1), K0 + clase, device=device)
    for _ in range(49):
        lg = gpt(x)[:, -1, :K0] / temp; x = torch.cat([x, torch.multinomial(F.softmax(lg, -1), 1)], 1)
    z = vq.quant.cb(x[:, 1:]).view(n, 7, 7, D0).permute(0, 3, 1, 2); return vq.dec(z).cpu()

fig, axs = plt.subplots(N_CLASES if N_CLASES <= 4 else 4, 8, figsize=(10, 5.2 if N_CLASES > 3 else 4)); filas = axs if axs.ndim > 1 else axs[None]
for c in range(filas.shape[0]):
    imgs = genera(c)
    for j in range(8): filas[c, j].imshow(imgs[j, 0], cmap="gray"); filas[c, j].axis("off")
    filas[c, 0].set_title(f"clase {c} (token de 'prompt')", fontsize=8, loc="left")
plt.tight_layout(); plt.show()
'''

# ------------------------------------------------------------------ audio
AUDIO_DATA = r'''
from scipy.signal import lfilter
SR = 8000; DUR = 1.0; N_AUD = int(SR * DUR)
VOCALES = {"a": (730, 1090, 2440), "e": (530, 1840, 2480), "i": (270, 2290, 3010), "o": (570, 840, 2410), "u": (300, 870, 2240)}

def resonador(x, f, bw=80):
    """Filtro de 2º orden (formante) a la frecuencia f con ancho de banda bw."""
    r = np.exp(-np.pi * bw / SR); th = 2 * np.pi * f / SR
    return lfilter([1 - r], [1, -2 * r * np.cos(th), r * r], x)

def voz_sintetica(rng, dur=DUR):
    """Clip 'tipo voz': tren de pulsos glotales con f0 variable + formantes de vocales + envolvente silábica + ruido."""
    n = int(SR * dur); t = np.arange(n) / SR
    f0 = rng.uniform(100, 220) * (1 + 0.05 * np.sin(2 * np.pi * rng.uniform(3, 6) * t) + 0.15 * (t / dur - .5))
    fase = np.cumsum(f0) / SR; src = np.sign(np.diff(np.floor(fase), prepend=0)) * 1.0           # pulsos
    src = lfilter([1], [1, -0.97], src)                                                          # espectro -6 dB/oct
    y = np.zeros(n); seg = int(SR * rng.uniform(0.18, 0.3)); i = 0
    while i < n:
        F1, F2, F3 = VOCALES[rng.choice(list(VOCALES))]; j = min(n, i + seg)
        s = src[i:j]; v = resonador(s, F1) + 0.6 * resonador(s, F2, 100) + 0.3 * resonador(s, F3, 120)
        env = np.hanning(len(v)) ** 0.5; y[i:j] += v * env; i = j
    y += rng.randn(n) * 0.01 * np.abs(y).max(); y = y / (np.abs(y).max() + 1e-8) * 0.8
    return y.astype(np.float32)

rng = np.random.RandomState(SEED)
N_TR_A = 192 if FAST_DEV_RUN else 2000
A_TR = torch.from_numpy(np.stack([voz_sintetica(rng) for _ in range(N_TR_A)]))[:, None].to(device)
A_TE = torch.from_numpy(np.stack([voz_sintetica(rng) for _ in range(24)]))[:, None].to(device)
print(f"audio sintético 'tipo voz': train={tuple(A_TR.shape)} test={tuple(A_TE.shape)} a {SR} Hz  (PCM 16 bit = {SR*16/1000:.0f} kbps)")
'''

AUDIO_MODEL = r'''
class CodecToy(nn.Module):
    """Códec neuronal de juguete (SoundStream/EnCodec en miniatura): encoder conv (stride total 64) -> RVQ -> decoder conv."""
    def __init__(self, d=32, Q=4, K=256):
        super().__init__()
        self.enc = nn.Sequential(nn.Conv1d(1, 16, 7, 1, 3), nn.ELU(), nn.Conv1d(16, 32, 4, 2, 1), nn.ELU(), nn.Conv1d(32, 64, 8, 4, 2), nn.ELU(),
                                 nn.Conv1d(64, d, 16, 8, 4))
        self.rvq = RVQ(Q, K, d)
        self.dec = nn.Sequential(nn.ConvTranspose1d(d, 64, 16, 8, 4), nn.ELU(), nn.ConvTranspose1d(64, 32, 8, 4, 2), nn.ELU(),
                                 nn.ConvTranspose1d(32, 16, 4, 2, 1), nn.ELU(), nn.Conv1d(16, 1, 7, 1, 3))
    def forward(self, x, reinicia=False, n_q=None):
        zq, ql, idx = self.rvq(self.enc(x), reinicia, n_q); return self.dec(zq), ql, idx

def stft_mag(x, n_fft):
    return torch.stft(x.squeeze(1), n_fft, n_fft // 4, window=torch.hann_window(n_fft, device=x.device), return_complex=True).abs()

def perdida_audio(x, xr):
    """L1 en la forma de onda + L1 de log-magnitud STFT multi-escala (la idea de EnCodec/DAC; sin discriminador)."""
    l = F.l1_loss(xr, x)
    for n in (512, 256, 128): l = l + 0.5 * F.l1_loss(torch.log(stft_mag(xr, n) + 1e-5), torch.log(stft_mag(x, n) + 1e-5))
    return l

def snr_db(x, xr): return float(10 * torch.log10(x.pow(2).sum() / (x - xr).pow(2).sum().clamp_min(1e-10)))
def lsd_db(x, xr, n=512):
    a, b = 20 * torch.log10(stft_mag(x, n) + 1e-5), 20 * torch.log10(stft_mag(xr, n) + 1e-5); return float((a - b).pow(2).mean(-2).sqrt().mean())

Q_A, K_A, FRAMES = 4, 256, N_AUD // 64
torch.manual_seed(SEED); cod = CodecToy(Q=Q_A, K=K_A).to(device); opt = torch.optim.Adam(cod.parameters(), lr=1e-3)
PASOS_A = 400 if FAST_DEV_RUN else 4000; g = torch.Generator().manual_seed(SEED); t0 = time.time(); hist_a = []
for s in range(PASOS_A):
    cod.train(); x = A_TR[torch.randint(0, len(A_TR), (16,), generator=g).to(device)]; nq = int(torch.randint(1, Q_A + 1, (1,), generator=g))   # quantizer dropout
    xr, ql, _ = cod(x, reinicia=(s % 50 == 0 and s > 0), n_q=nq); loss = perdida_audio(x, xr) + ql; opt.zero_grad(); loss.backward(); opt.step()
    if s % 25 == 0: hist_a.append((s, loss.item()))
print(f"códec toy: {sum(p.numel() for p in cod.parameters())/1e6:.2f}M params | {time.time()-t0:.0f}s | {FRAMES} frames/s = {SR//64} Hz | pérdida {hist_a[0][1]:.2f} -> {hist_a[-1][1]:.2f}")
'''

AUDIO_EVAL = r'''
cod.eval(); RA = {}
with torch.no_grad():
    for nq in range(1, Q_A + 1):
        xr, _, idx = cod(A_TE, n_q=nq); RA[nq] = {"snr": snr_db(A_TE, xr), "lsd": lsd_db(A_TE, xr), "kbps": (SR // 64) * nq * math.log2(K_A) / 1000, "xr": xr, "idx": idx}
def mulaw_snr(x, bits, mu=255.0):
    y = torch.sign(x) * torch.log1p(mu * x.abs()) / math.log1p(mu); q = torch.round((y + 1) / 2 * (2 ** bits - 1)) / (2 ** bits - 1) * 2 - 1
    return snr_db(x, torch.sign(q) * ((1 + mu) ** q.abs() - 1) / mu)
MU = {b: (mulaw_snr(A_TE, b), SR * b / 1000) for b in [3, 4, 5, 6, 8]}
for nq, r in RA.items(): print(f"toy RVQ n_q={nq}: {r['kbps']:.1f} kbps  ({128/r['kbps']:.0f}x menos que PCM-16) | SNR={r['snr']:5.2f} dB | LSD={r['lsd']:5.2f} dB")
print({f"μ-law {b} bit": f"{v[1]:.0f} kbps, SNR={v[0]:.1f} dB" for b, v in MU.items()})

fig, axs = plt.subplots(2, 3, figsize=(14, 6)); t_ = np.arange(N_AUD) / SR; x0 = A_TE[0, 0].cpu().numpy()
for j, (nom, sig) in enumerate([("original", x0), ("toy codec, 1 nivel (1 kbps)", RA[1]["xr"][0, 0].cpu().numpy()), ("toy codec, 4 niveles (4 kbps)", RA[4]["xr"][0, 0].cpu().numpy())]):
    axs[0, j].plot(t_[:1500], sig[:1500], color=AZUL, lw=.7); axs[0, j].set_title(nom, fontsize=9); axs[0, j].set_ylim(-1, 1)
    axs[1, j].specgram(sig, NFFT=256, Fs=SR, noverlap=192, cmap="magma", vmin=-110); axs[1, j].set_xlabel("tiempo (s)")
axs[1, 0].set_ylabel("frecuencia (Hz)"); plt.tight_layout(); plt.show()

fig, axs = plt.subplots(1, 2, figsize=(12, 3.8))
axs[0].plot([RA[q]["kbps"] for q in RA], [RA[q]["snr"] for q in RA], "o-", color=AZUL, lw=2, label="códec toy (RVQ, 125 Hz x Q x 8 bit)")
axs[0].plot([v[1] for v in MU.values()], [v[0] for v in MU.values()], "s--", color=NARANJA, lw=2, label="μ-law (b bits/muestra)")
axs[0].set_xscale("log"); axs[0].set_xlabel("tasa (kbps, escala log)"); axs[0].set_ylabel("SNR (dB)"); axs[0].set_title("Compresión vs fidelidad en forma de onda"); axs[0].legend(fontsize=8)
axs[1].plot([RA[q]["kbps"] for q in RA], [RA[q]["lsd"] for q in RA], "o-", color=VERDE, lw=2); axs[1].set_xlabel("tasa (kbps)"); axs[1].set_ylabel("distancia log-espectral (dB, menor = mejor)")
axs[1].set_title("Fidelidad espectral del códec toy"); plt.tight_layout(); plt.show()
'''

ENCODEC_TRY = r'''
# EnCodec real (Défossez et al., 2022) con Hugging Face: pesos oficiales 'facebook/encodec_24khz' (requiere acceso al hub).
import torchaudio
try:
    from transformers import EncodecModel
    try:
        enc_m = EncodecModel.from_pretrained("facebook/encodec_24khz").eval(); real = True
    except Exception as e:
        from transformers import EncodecConfig
        enc_m = EncodecModel(EncodecConfig()).eval(); real = False            # pesos ALEATORIOS: solo para ver formas y tasas de tokens
        print("[aviso] sin acceso al hub: EnCodec con pesos aleatorios (las formas y la tasa de tokens son reales; el audio decodificado NO).")
    x24 = torchaudio.functional.resample(A_TE[:1].cpu(), SR, 24000)
    with torch.no_grad():
        out = enc_m.encode(x24, bandwidth=6.0)
    codes = out.audio_codes                                                   # [chunks, B, n_q, T]
    print("audio_codes:", tuple(codes.shape), "-> n_q =", codes.shape[2], "| frames por segundo =", round(codes.shape[-1] * (codes.shape[0]) / 1.0, 1))
    print(f"tokens por segundo (aplanado) = {75 * codes.shape[2]} | tasa = {75 * codes.shape[2] * 10 / 1000} kbps (1024 entradas = 10 bits)  | pesos reales: {real}")
except Exception as e:
    print("transformers/torchaudio no disponibles:", type(e).__name__, str(e)[:100])
'''

CODES_PLOT = r'''
# ¿Qué "dicen" los tokens del códec toy? Mapa de códigos (niveles x tiempo) para un clip y su perplejidad por nivel
idx = RA[4]["idx"][0].cpu().numpy()                                          # [Q, frames]
fig, axs = plt.subplots(1, 2, figsize=(13, 3.2), gridspec_kw={"width_ratios": [3, 1]})
axs[0].imshow(idx, aspect="auto", cmap="tab20", interpolation="nearest"); axs[0].set_xlabel("frame (125 por segundo)"); axs[0].set_ylabel("nivel RVQ")
axs[0].set_yticks(range(Q_A)); axs[0].set_title("Tokens del códec toy: 4 niveles x 125 frames (cada celda = un id de 0 a 255)", fontsize=9); axs[0].grid(False)
pp = [perplexity(torch.from_numpy(idx[q]), K_A) for q in range(Q_A)]
axs[1].bar([f"nivel {q+1}" for q in range(Q_A)], pp, color=AZUL); axs[1].set_ylabel("perplejidad (de 256)"); axs[1].set_title("Uso del codebook por nivel", fontsize=9)
plt.tight_layout(); plt.show()
'''

VIDEO_CALC = r'''
# Costo de contexto de vídeo con un tokenizer 3D (compresión temporal ct x espacial cs x cs)
def tokens_clip(seg, fps, h, w, ct, cs): return -(-int(seg * fps) // ct) * (h // cs) * (w // cs)
configs = {"4x8x8": (4, 8), "8x8x8": (8, 8), "8x16x16": (8, 16)}
dur = np.array([1, 2, 5, 10, 30])
fig, ax = plt.subplots(figsize=(8, 3.8))
for (nom, (ct, cs)), col in zip(configs.items(), [AZUL, NARANJA, VERDE]):
    ax.plot(dur, [tokens_clip(d, 24, 720, 1280, ct, cs) for d in dur], "o-", color=col, label=f"Cosmos DV{nom}")
ax.axhline(128_000, color="crimson", ls="--", lw=1, label="128K tokens"); ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("duración del clip (s), 24 fps, 720p"); ax.set_ylabel("tokens (aprox.)"); ax.set_title("Vídeo: la compresión espacio-temporal decide el contexto"); ax.legend(fontsize=8); plt.show()
for nom, (ct, cs) in configs.items(): print(f"DV{nom}: clip de 5 s -> {tokens_clip(5, 24, 720, 1280, ct, cs):,} tokens")
'''
