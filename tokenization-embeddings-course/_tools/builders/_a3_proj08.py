"""Proyecto del módulo 08: tokenizar una foto real y un clip de audio y medir reconstrucción y compresión."""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from nbbuild import Notebook  # noqa: E402
import a3_common as C  # noqa: E402
import _a3_src08 as S  # noqa: E402

# Umbrales calibrados con lo MEDIDO por la solución de referencia (FAST_DEV_RUN=True; foto real de scikit-learn, voz real FSDD:
# SNR 1.46 -> 2.94 dB de 1 a 4 niveles). Con el respaldo sintético el SNR es mayor (5.7 -> 10.1 dB) y también cumple.
T = {"bpp_1": 0.50, "psnr_img_min": 19.5, "jpeg_ventaja_min": 0.0, "kbps_4": 4.0, "snr_4_min": 2.5, "ganancia_snr_min": 1.0}

IMG_DATA = r'''
im_tr, fuente_tr = foto("china.jpg"); im_te, fuente_te = foto("flower.jpg")
A_TRAIN = torch.from_numpy(np.asarray(im_tr, np.float32) / 255).permute(2, 0, 1).to(device)          # [3,427,640]
TEST_IMG = torch.from_numpy(np.asarray(im_te, np.float32) / 255).permute(2, 0, 1)[:, :424, :640][None].to(device)
print(f"entrenamiento: {fuente_tr} china.jpg {tuple(A_TRAIN.shape)} | test (otra foto): flower.jpg {tuple(TEST_IMG.shape)}")

def recortes(B, s=64, g=None):
    ys = torch.randint(0, A_TRAIN.shape[1] - s, (B,), generator=g); xs = torch.randint(0, A_TRAIN.shape[2] - s, (B,), generator=g)
    return torch.stack([A_TRAIN[:, y:y + s, x:x + s] for y, x in zip(ys.tolist(), xs.tolist())])

class AEFoto(nn.Module):
    """Autoencoder conv RGB con reducción x4 por eje (una rejilla de tokens de H/4 x W/4) y RVQ de 2 niveles de 256 códigos."""
    def __init__(self, d=32, Q=2, K=256):
        super().__init__()
        self.enc = nn.Sequential(nn.Conv2d(3, 64, 4, 2, 1), nn.ReLU(), nn.Conv2d(64, 128, 4, 2, 1), nn.ReLU(), nn.Conv2d(128, d, 1))
        self.quant = RVQ(Q, K, d)
        self.dec = nn.Sequential(nn.Conv2d(d, 128, 3, 1, 1), nn.ReLU(), nn.ConvTranspose2d(128, 64, 4, 2, 1), nn.ReLU(),
                                 nn.ConvTranspose2d(64, 3, 4, 2, 1), nn.Sigmoid())
    def forward(self, x, reinicia=False, n_q=None):
        zq, ql, idx = self.quant(self.enc(x), reinicia, n_q); return self.dec(zq), ql, idx

torch.manual_seed(SEED); AE_F = AEFoto().to(device); opt = torch.optim.Adam(AE_F.parameters(), lr=2e-3); g = torch.Generator().manual_seed(SEED)
PASOS_F = 500 if FAST_DEV_RUN else 5000; t0 = time.time()
for s in range(PASOS_F):
    AE_F.train(); x = recortes(16, g=g); nq = int(torch.randint(1, 3, (1,), generator=g))           # quantizer dropout (1 o 2 niveles)
    xr, ql, _ = AE_F(x, reinicia=(s % 50 == 0 and s > 0), n_q=nq); loss = F.mse_loss(xr, x) + ql; opt.zero_grad(); loss.backward(); opt.step()
print(f"tokenizer de fotos entrenado en {time.time()-t0:.0f}s | pérdida final {loss.item():.4f}")
'''

TODO1 = r'''
def bpp(n_tokens, K, H, W, n_q=1):
    """Bits por píxel de una imagen H x W representada con n_tokens posiciones, n_q niveles de un codebook de K entradas."""
    # TODO 1
    raise NotImplementedError("TODO 1")
'''
SOL1 = r'''
def bpp(n_tokens, K, H, W, n_q=1):
    return n_tokens * n_q * math.log2(K) / (H * W)
'''
TODO2 = r'''
def jpeg_punto(img, calidad):
    """img: tensor [1,3,H,W] en [0,1]. Comprime con JPEG (PIL) a la calidad dada y devuelve (bpp_real, psnr_dB).
    bpp_real = 8 * nº de bytes del archivo JPEG / (H*W)."""
    # TODO 2: pasa a uint8 HxWx3, guarda en io.BytesIO con Image.save(..., format="JPEG", quality=calidad), mide bytes, decodifica y calcula psnr
    raise NotImplementedError("TODO 2")
'''
SOL2 = r'''
def jpeg_punto(img, calidad):
    arr = (img[0].permute(1, 2, 0).clamp(0, 1).cpu().numpy() * 255).round().astype(np.uint8)
    buf = io.BytesIO(); Image.fromarray(arr).save(buf, format="JPEG", quality=calidad); n = buf.tell(); buf.seek(0)
    rec = torch.from_numpy(np.asarray(Image.open(buf), np.float32) / 255).permute(2, 0, 1)[None]
    return 8 * n / (arr.shape[0] * arr.shape[1]), psnr(rec, img.cpu())
'''
TODO3 = r'''
def rvq_codifica(z, capas, n_q):
    """Cuantización residual SOLO con los codebooks (sin módulos): z [B,d,T]; capas = lista de VQ ya entrenados.
    Devuelve (ids [B, n_q, T], z_hat [B,d,T]). Para cada nivel: vecino más cercano del residuo en capa.cb.weight."""
    # TODO 3: r = z; para cada capa en capas[:n_q]: ids = argmin distancia(r, codebook); q = codebook[ids]; r = r - q; acumula q
    raise NotImplementedError("TODO 3")
'''
SOL3 = r'''
def rvq_codifica(z, capas, n_q):
    r = z.movedim(1, -1); zh = torch.zeros_like(r); ids = []
    for capa in capas[:n_q]:
        cb = capa.cb.weight; d = r.pow(2).sum(-1, keepdim=True) - 2 * r @ cb.T + cb.pow(2).sum(1)
        i = d.argmin(-1); q = cb[i]; r = r - q; zh = zh + q; ids.append(i)
    return torch.stack(ids, 1), zh.movedim(-1, 1)
'''
TODO4 = r'''
def kbps_codec(sr, stride, n_q, K):
    """Tasa de un códec RVQ en kbps: (sr/stride) frames/s x n_q niveles x log2(K) bits."""
    # TODO 4
    raise NotImplementedError("TODO 4")
'''
SOL4 = r'''
def kbps_codec(sr, stride, n_q, K):
    return sr / stride * n_q * math.log2(K) / 1000
'''

FLOW_IMG = r'''
RES = {}
try:
    AE_F.eval(); H_, W_ = TEST_IMG.shape[2:]
    for nq in [1, 2]:
        with torch.no_grad(): xr, _, idx = AE_F(TEST_IMG, n_q=nq)
        RES[f"img_{nq}"] = {"bpp": bpp(idx.shape[2] * idx.shape[3], 256, H_, W_, nq), "psnr": psnr(xr, TEST_IMG), "xr": xr.cpu()}
    RES["jpeg"] = [jpeg_punto(TEST_IMG, q) for q in [5, 10, 20, 35, 50, 75, 90]]
    for nq in [1, 2]: print(f"VQ-RVQ {nq} nivel(es): {RES[f'img_{nq}']['bpp']:.3f} bpp | PSNR {RES[f'img_{nq}']['psnr']:.2f} dB")
    print("JPEG (bpp, PSNR):", [(round(b, 3), round(p, 2)) for b, p in RES["jpeg"]])
    jb = np.array([b for b, _ in RES["jpeg"]]); jp = np.array([p for _, p in RES["jpeg"]]); o = np.argsort(jb)
    RES["jpeg_a_mismo_bpp"] = float(np.interp(RES["img_1"]["bpp"], jb[o], jp[o]))
    print(f"JPEG interpolado a {RES['img_1']['bpp']:.2f} bpp: {RES['jpeg_a_mismo_bpp']:.2f} dB")
except NotImplementedError as e:
    print("Pendiente:", e)
'''
FLOW_AUD = r'''
try:
    cod.eval(); RES["aud"] = {}
    with torch.no_grad():
        z = cod.enc(A_TE)
        for nq in range(1, Q_A + 1):
            ids, zh = rvq_codifica(z, list(cod.rvq.capas), nq); xr = cod.dec(zh)
            RES["aud"][nq] = {"kbps": kbps_codec(SR, 64, nq, K_A), "snr": snr_db(A_TE, xr), "lsd": lsd_db(A_TE, xr), "ids": tuple(ids.shape)}
    for nq, r in RES["aud"].items(): print(f"audio n_q={nq}: {r['kbps']:.1f} kbps | SNR {r['snr']:.2f} dB | LSD {r['lsd']:.2f} dB | ids {r['ids']}")
    RES["mulaw"] = {b: (mulaw_snr(A_TE, b), SR * b / 1000) for b in [3, 4, 5, 6, 8]}
except (NotImplementedError, NameError) as e:
    print("Pendiente:", e)
'''
PLOT = r'''
if "img_1" in RES and "aud" in RES:
    fig, axs = plt.subplots(1, 4, figsize=(17, 3.8))
    axs[0].imshow(TEST_IMG[0].permute(1, 2, 0).cpu()); axs[0].set_title("original (flower.jpg, no vista)", fontsize=9)
    axs[1].imshow(RES["img_1"]["xr"][0].permute(1, 2, 0).clamp(0, 1)); axs[1].set_title(f"tokens VQ, {RES['img_1']['bpp']:.2f} bpp, {RES['img_1']['psnr']:.1f} dB", fontsize=9)
    for a in axs[:2]: a.axis("off"); a.grid(False)
    axs[2].plot([b for b, _ in RES["jpeg"]], [p for _, p in RES["jpeg"]], "s--", color=NARANJA, label="JPEG")
    axs[2].plot([RES[f"img_{q}"]["bpp"] for q in [1, 2]], [RES[f"img_{q}"]["psnr"] for q in [1, 2]], "o-", color=AZUL, lw=2, label="VQ-RVQ (1-2 niveles)")
    axs[2].set_xlabel("bits por píxel"); axs[2].set_ylabel("PSNR (dB)"); axs[2].set_title("Imagen: tasa-distorsión"); axs[2].legend(fontsize=8)
    axs[3].plot([r["kbps"] for r in RES["aud"].values()], [r["snr"] for r in RES["aud"].values()], "o-", color=AZUL, lw=2, label="códec RVQ")
    axs[3].plot([v[1] for v in RES["mulaw"].values()], [v[0] for v in RES["mulaw"].values()], "s--", color=NARANJA, label="μ-law")
    axs[3].set_xscale("log"); axs[3].set_xlabel("kbps"); axs[3].set_ylabel("SNR (dB)"); axs[3].set_title("Audio: tasa-fidelidad"); axs[3].legend(fontsize=8)
    plt.tight_layout(); plt.show()
else:
    print("Completa los TODO 1-4 para ver la figura.")
'''
RUBRIC = r'''
def rubrica(RES, th=THR):
    filas = []; chk = lambda n, ok, d: filas.append((n, ok, d))
    i1 = RES.get("img_1", {}); a = RES.get("aud", {})
    chk("R1 bpp de la imagen con 1 nivel = %.2f (tu fórmula)" % th["bpp_1"], abs(i1.get("bpp", -1) - th["bpp_1"]) < 1e-6, f"{i1.get('bpp')}")
    chk("R2 PSNR en la foto NO vista con 1 nivel >= %.1f dB" % th["psnr_img_min"], i1.get("psnr", 0) >= th["psnr_img_min"], f"{i1.get('psnr')}")
    chk("R3 tu curva JPEG está bien medida (PSNR crece con la calidad)", len(RES.get("jpeg", [])) == 7 and RES["jpeg"][-1][1] > RES["jpeg"][0][1], f"{RES.get('jpeg')}")
    chk("R4 tasa del códec con 4 niveles = %.1f kbps" % th["kbps_4"], abs(a.get(4, {}).get("kbps", -1) - th["kbps_4"]) < 1e-6, f"{a.get(4, {}).get('kbps')}")
    chk("R5 SNR con 4 niveles >= %.1f dB y mejora >= %.1f dB sobre 1 nivel" % (th["snr_4_min"], th["ganancia_snr_min"]),
        4 in a and a[4]["snr"] >= th["snr_4_min"] and a[4]["snr"] - a[1]["snr"] >= th["ganancia_snr_min"], f"{[round(a[q]['snr'], 2) for q in a] if a else None}")
    chk("R6 conclusión escrita (>= 300 caracteres) en CONCLUSION", len(globals().get("CONCLUSION", "")) >= 300, f"{len(globals().get('CONCLUSION', ''))} caracteres")
    for n, ok, d in filas: print(("✅" if ok else "❌"), n, "|", d)
    print(f"\n{sum(o for _, o, _ in filas)}/{len(filas)} criterios")
'''


def build(lesson_rel, proj_rel, mod_dir, slug):
    nb = Notebook("Proyecto 08 · Tokeniza una foto y un clip de audio", colab_path=proj_rel, gpu=True)
    hint, obs = C.hint, C.observe
    nb.md(nb.badge() + r"""

# Proyecto 08 · Tokeniza una foto real y un clip de audio: ¿cuánto comprimes y cuánto pierdes?

| | |
|---|---|
| **Nivel** | 🟠 Avanzado |
| **Duración estimada** | ≈ 2.5 h |
| **GPU recomendada** | `FAST_DEV_RUN=True`: CPU (≈ 4-6 min). Modo completo: T4 (≈ 2-4 unidades, estimación) |
| **Prerrequisitos** | Lección 08 (VQ, RVQ, quantizer dropout, tasa-distorsión, μ-law) |

## Contexto de negocio
En **Políglota Labs** alguien propone guardar las capturas de los PDFs y los audios de soporte como **tokens discretos** «para que un LLM los lea después». Antes de decidir, el CTO quiere números:
¿**cuántos bits** cuesta cada imagen/segundo de audio y **cuánta calidad** se pierde frente a los códecs clásicos (JPEG, μ-law)? Construyes y evalúas los dos tokenizers (imagen y audio) con datos que **no** vio el entrenamiento.

**Conexión.** Lección 08 (VQ-VAE/RVQ/códec toy) → este proyecto; módulo 16: retrieval multimodal con embeddings **continuos** (verás por qué no usar estos tokens para buscar).

## Dataset
* **Imagen:** dos fotos reales empaquetadas con scikit-learn: entrenas con recortes de `china.jpg` y evalúas en `flower.jpg` completa (generalización a otra foto). Respaldo: imagen sintética.
* **Audio:** voz **real** de la lección: *Free Spoken Digit Dataset* (dígitos hablados en inglés, 6 hablantes, 8 kHz, CC BY-SA 4.0) desde su repositorio oficial en GitHub, concatenado en clips de 1 s; el test usa otras grabaciones. Respaldo sin red: voz sintética «tipo voz» (con aviso). LibriSpeech queda como extensión.

## Entregables y criterios de evaluación
| Criterio | Umbral (calibrado con la solución de referencia) |
|---|---|
| R1 · bpp con 1 nivel (fórmula correcta) | = """ + f"{T['bpp_1']}" + r""" (106x160 tokens x 8 bits / 424x640 px) |
| R2 · PSNR en la foto no vista (1 nivel) | ≥ """ + f"{T['psnr_img_min']}" + r""" dB (medido: 20.45 dB; JPEG al mismo bpp: 32.9 dB) |
| R3 · curva JPEG medida con 7 calidades | PSNR creciente |
| R4 · tasa del códec con 4 niveles | = """ + f"{T['kbps_4']}" + r""" kbps |
| R5 · SNR de audio con 4 niveles y ganancia sobre 1 nivel | ≥ """ + f"{T['snr_4_min']}" + r""" dB y ≥ +""" + f"{T['ganancia_snr_min']}" + r""" dB (medido con voz real FSDD: 2.94 dB con 4 niveles vs 1.46 con 1; con el respaldo sintético, 10.1 vs 5.7) |
| R6 · conclusión escrita en `CONCLUSION` | ≥ 300 caracteres |
""")
    nb.code(S.PIP)
    nb.code(C.SETUP_COMMON + S.SETUP8)
    nb.md("## Paso 0 · Utilidades y modelos (dados)\n\nCuantizadores de la lección, la foto, y el entrenamiento de los dos tokenizers (imagen: reducción x4 + RVQ 2x256; audio: códec toy de la lección). Tardan unos minutos en CPU.")
    nb.code(S.QUANTIZERS)
    nb.code(S.DATA_IMG.split("N_IMG = ")[0] + "def foto" + S.DATA_IMG.split("def foto")[1])
    nb.code(IMG_DATA)
    nb.code(S.AUDIO_DATA)
    nb.code(S.AUDIO_MODEL)
    nb.code(S.AUDIO_EVAL.split("MU = ")[0].split("cod.eval(); RA = {}")[0] + "\ndef mulaw_snr(x, bits, mu=255.0):\n" + S.AUDIO_EVAL.split("def mulaw_snr(x, bits, mu=255.0):\n")[1].split("MU = ")[0])
    nb.md("## Paso 1 · TODO 1-2: medir la imagen\n\n$\\text{bpp} = \\dfrac{N_{\\text{tokens}}\\cdot n_q\\cdot\\log_2 K}{H\\cdot W}$. Para JPEG, mide los **bytes reales** del archivo.")
    nb.code(TODO1)
    nb.code(TODO2)
    nb.md(hint(1, "`io.BytesIO()` como archivo en memoria; tras `save`, `buf.tell()` da el nº de bytes. Vuelve al inicio con `buf.seek(0)` y abre con `Image.open(buf)`.") + "\n\n" +
          hint(2, "`arr = (img[0].permute(1,2,0).clamp(0,1).cpu().numpy()*255).round().astype(np.uint8)`; reconstrucción: `torch.from_numpy(np.asarray(Image.open(buf), np.float32)/255).permute(2,0,1)[None]`; usa `psnr(rec, img.cpu())`."))
    nb.code(FLOW_IMG)
    nb.md("## Paso 2 · TODO 3-4: tokenizar el audio con los codebooks entrenados\n\nReimplementa la **codificación RVQ** usando solo las matrices `capa.cb.weight` (esto es lo que haría un servidor que guarda los ids) y calcula la tasa.")
    nb.code(TODO3)
    nb.md(hint(1, "Trabaja con `r = z.movedim(1, -1)` ([B,T,d]) para que la distancia a la matriz `cb` [K,d] sea `r.pow(2).sum(-1,keepdim=True) - 2*r@cb.T + cb.pow(2).sum(1)`.") + "\n\n" +
          hint(2, "Por nivel: `i = d.argmin(-1); q = cb[i]; r = r - q; zh = zh + q; ids.append(i)`. Al final `torch.stack(ids, 1)` y `zh.movedim(-1, 1)`."))
    nb.code(TODO4)
    nb.code(FLOW_AUD)
    nb.code(PLOT)
    nb.md(C.observe("**Paneles 1–2:** la reconstrucción con tokens VQ pierde detalle fino (bordes, textura) pero conserva la estructura; su título da los bpp y el PSNR. **Panel 3 (imagen):** compara las dos curvas a igual bpp; si JPEG queda por encima, no es un fallo tuyo: un códec diseñado durante décadas para el ojo puede comprimir mejor que un tokenizer diminuto entrenado en minutos. **Panel 4 (audio):** cada nivel RVQ extra sube los kbps y el SNR; μ-law es la referencia clásica. La conclusión que debes poder defender: estos tokens no se diseñan para ganar a JPEG o μ-law, sino para que un **transformer** pueda modelar imágenes y audio como secuencias discretas (lección, §8)."))
    nb.md("## Paso 3 · Conclusión y rúbrica\n\nEscribe en `CONCLUSION` (≥ 300 caracteres): ¿le ganan tus tokens a JPEG/μ-law? ¿para qué sirven entonces? ¿qué recomendarías a Políglota y qué **no** puedes concluir?")
    nb.code('CONCLUSION = ""   # TODO 5\n')
    nb.code("THR = " + repr(T) + "\n" + RUBRIC + "\nrubrica(RES)")
    nb.md("---\n## ⛔ SPOILER — intenta resolverlo primero\n\nSolución de referencia completa y ejecutable.")
    for s_ in [SOL1, SOL2, SOL3, SOL4]:
        nb.code(s_)
    nb.code(FLOW_IMG + "\n" + FLOW_AUD)
    nb.code(PLOT)
    nb.code(r'''CONCLUSION = (
    f"Imagen: con 1 nivel ({RES['img_1']['bpp']:.2f} bpp) nuestro tokenizer da {RES['img_1']['psnr']:.1f} dB en una foto no vista, frente a ~{RES['jpeg_a_mismo_bpp']:.1f} dB de JPEG al mismo bpp: "
    "un tokenizer diminuto entrenado con una sola foto NO compite con JPEG en fidelidad. "
    f"Audio: el códec toy con 4 niveles ({RES['aud'][4]['kbps']:.0f} kbps, 32x menos que PCM-16) logra {RES['aud'][4]['snr']:.1f} dB de SNR frente a {RES['aud'][1]['snr']:.1f} dB con 1 nivel; μ-law necesita decenas de kbps para SNR parecidos. "
    "El valor de los tokens discretos no es la compresión sino que un LM puede predecirlos y mezclarlos con texto. Recomendación para Políglota: para BUSCAR, embeddings continuos (módulo 16); "
    "tokens discretos solo si hay generación. Límites: una semilla, modelos diminutos sin pérdidas perceptuales/GAN, pocos segundos de voz (dígitos en inglés); PSNR/SNR no son calidad perceptual."
)
rubrica(RES)''')
    nb.md("""## Retos extra (nivel experto)
1. Añade una pérdida **perceptual** sencilla (diferencias de gradiente o LPIPS si tienes acceso) y mide si el PSNR baja pero la imagen *se ve* mejor.
2. Sustituye el RVQ de la imagen por **FSQ** con niveles [8,6,5] y compara uso del codebook y PSNR.
3. Entrena con **más fotos** (p. ej. un subconjunto de COCO si tienes red) y mide la generalización.
4. Prueba **LibriSpeech** real (`openslr/librispeech_asr`) o EnCodec real (`facebook/encodec_24khz`) y compara su SNR/LSD con tu códec.
5. Calcula cuántos **tokens por minuto** generaría tu códec y cuánto ocuparían 1 000 horas de llamadas en almacenamiento y en contexto.

## Reflexión
* ¿Por qué el paper de Chameleon acepta perder calidad al discretizar imágenes?
* ¿Qué métrica perceptual usarías para decidir un códec de audio para Políglota?
* ¿Qué parte de este análisis cambia si el objetivo es *retrieval* (módulo 16) y no generación?
""")
    nb.save(os.path.join(mod_dir, "08_proyecto_tokens_multimodales_audio.ipynb"))
