"""Fuentes de código del módulo 16 (CLIP/SigLIP en miniatura, modality gap, ColPali en miniatura)."""

# ───────────────── Dataset de figuras + captions bilingües ─────────────────
SHAPES_SRC = r'''
import numpy as np, torch, torch.nn as nn, torch.nn.functional as F

FORMAS = ["circle", "square", "triangle", "cross"]; COLORES = ["red", "green", "blue", "yellow"]
RGB = {"red": (.9, .1, .1), "green": (.1, .7, .1), "blue": (.1, .2, .9), "yellow": (.95, .85, .1)}
ES_F = {"circle": ("un", "círculo"), "square": ("un", "cuadrado"), "triangle": ("un", "triángulo"), "cross": ("una", "cruz")}
ES_C = {"red": ("rojo", "roja"), "green": ("verde", "verde"), "blue": ("azul", "azul"), "yellow": ("amarillo", "amarilla")}
CONCEPTOS = [(f, c) for f in FORMAS for c in COLORES]          # 16 conceptos

def dibuja(forma: str, color: str, rng, S: int = 32, centro=None) -> np.ndarray:
    """Imagen SxSx3 float32 con una figura de color sobre fondo gris con ruido. Posición y tamaño aleatorios."""
    y, x = np.mgrid[0:S, 0:S]; cx, cy = rng.integers(int(S*.34), int(S*.66), 2) if centro is None else centro; r = rng.integers(max(2, int(S*.19)), int(S*.31))
    if forma == "circle": m = (x - cx)**2 + (y - cy)**2 < r * r
    elif forma == "square": m = (abs(x - cx) < r * .8) & (abs(y - cy) < r * .8)
    elif forma == "triangle": m = (y >= cy - r) & (y <= cy + r) & (abs(x - cx) <= (y - (cy - r)) / 2 + .5)
    else: m = ((abs(x - cx) < max(1, r / 3)) & (abs(y - cy) < r)) | ((abs(y - cy) < max(1, r / 3)) & (abs(x - cx) < r))
    img = np.full((S, S, 3), .5) + rng.normal(0, .04, (S, S, 3)); img[m] = np.array(RGB[color]) + rng.normal(0, .04, (m.sum(), 3))
    return np.clip(img, 0, 1).astype(np.float32)

def caption(forma: str, color: str, lang: str, rng) -> list:
    """Caption como lista de palabras, en ES o EN, con 3 plantillas por idioma (concordancia de género en ES)."""
    if lang == "en":
        return rng.choice(["a {c} {s}", "picture of a {c} {s}", "a photo of a {c} {s}"]).format(c=color, s=forma).split()
    art, s = ES_F[forma]; col = ES_C[color][1 if art == "una" else 0]
    return rng.choice(["{a} {s} {c}", "imagen de {a} {s} {c}", "una foto de {a} {s} {c}"]).format(a=art, s=s, c=col).split()

def make_dataset(n_per: int, seed: int):
    """Devuelve (imágenes, captions, etiqueta de concepto, idioma). Cada imagen lleva UNA caption (ES o EN al azar)."""
    rng = np.random.default_rng(seed); X, T, Y, L = [], [], [], []
    for k, (f, c) in enumerate(CONCEPTOS):
        for _ in range(n_per):
            lang = "es" if rng.random() < .5 else "en"
            X.append(dibuja(f, c, rng)); T.append(caption(f, c, lang, rng)); Y.append(k); L.append(lang)
    return np.stack(X), T, np.array(Y), L
'''.strip("\n")

# ───────────────── Dos torres + pérdidas CLIP / SigLIP + modality gap ─────────────────
CLIP_SRC = r'''
class TorreImagen(nn.Module):
    """CNN diminuta -> vector L2-normalizado (el análogo de un ViT en miniatura)."""
    def __init__(self, D: int = 32):
        super().__init__()
        self.c = nn.Sequential(nn.Conv2d(3, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2), nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                               nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Linear(64, D))
    def forward(self, x): return F.normalize(self.c(x.permute(0, 3, 1, 2)), dim=-1)

class TorreTexto(nn.Module):
    """Bolsa de palabras (media de embeddings) + capa lineal -> vector L2-normalizado."""
    def __init__(self, V: int, D: int = 32):
        super().__init__(); self.e = nn.EmbeddingBag(V + 1, D, mode="mean"); self.l = nn.Linear(D, D)
    def forward(self, ids, off): return F.normalize(self.l(self.e(ids, off)), dim=-1)

def codifica_textos(T, w2i):
    ids = [torch.tensor([w2i[w] for w in t]) for t in T]
    return torch.cat(ids), torch.tensor([0] + [len(i) for i in ids[:-1]]).cumsum(0)

def perdida_clip(zi, zt, escala):
    """InfoNCE simétrica: entropía cruzada fila a fila y columna a columna sobre la matriz N x N de logits."""
    lg = escala * zi @ zt.T; lab = torch.arange(len(zi))
    return (F.cross_entropy(lg, lab) + F.cross_entropy(lg.T, lab)) / 2

def perdida_siglip(zi, zt, escala, sesgo):
    """Sigmoide por PAR (sin softmax): +1 en la diagonal, -1 fuera. Suma sobre todos los pares / N (Zhai et al. 2023)."""
    lg = escala * zi @ zt.T + sesgo; lab = 2 * torch.eye(len(zi)) - 1
    return -F.logsigmoid(lab * lg).sum() / len(zi)

def entrena_clip(Xtr, Ttr, w2i, tipo="infonce", tau=None, epochs=60, bs=128, seed=0, D=32, lr=3e-3):
    """tau=None -> temperatura APRENDIDA (init 1/0.07 en infonce, t=10 y b=-10 en sigmoid). tau=float -> temperatura FIJA."""
    torch.manual_seed(seed); I, Tx = TorreImagen(D), TorreTexto(len(w2i), D)
    logt = nn.Parameter(torch.tensor(float(np.log(1 / 0.07 if tipo == "infonce" else 10.0)))); b = nn.Parameter(torch.tensor(-10.0))
    params = list(I.parameters()) + list(Tx.parameters()) + ([logt] if tau is None else []) + ([b] if tipo == "sigmoid" else [])
    opt = torch.optim.Adam(params, lr=lr); X = torch.tensor(Xtr); n = len(X); hist = []
    for _ in range(epochs):
        perm = torch.randperm(n)
        for i in range(0, n - bs + 1, bs):
            idx = perm[i:i + bs]; ids, off = codifica_textos([Ttr[j] for j in idx], w2i); zi, zt = I(X[idx]), Tx(ids, off)
            escala = logt.exp() if tau is None else torch.tensor(1.0 / tau)
            loss = perdida_clip(zi, zt, escala) if tipo == "infonce" else perdida_siglip(zi, zt, escala, b)
            opt.zero_grad(); loss.backward(); opt.step()
        hist.append(loss.item())
    return I, Tx, hist

@torch.no_grad()
def embebe(I, Tx, X, T, w2i):
    ids, off = codifica_textos(T, w2i); return I(torch.tensor(X)), Tx(ids, off)

def modality_gap(zi, zt) -> float:
    """Distancia entre los centroides de las dos modalidades (Liang et al. 2022), con embeddings L2-normalizados."""
    return float((zi.mean(0) - zt.mean(0)).norm())

def metricas_clip(zi, zt, Y) -> dict:
    """Precisión imagen->concepto del texto más cercano, R@1 texto->imagen (mismo concepto) y gap."""
    Y = torch.as_tensor(Y); S = zi @ zt.T
    return {"acc_i2t": float((Y[S.argmax(1)] == Y).float().mean()), "acc_t2i": float((Y[S.argmax(0)] == Y).float().mean()), "gap": modality_gap(zi, zt)}
'''.strip("\n")

# ───────────────── Documentos como imágenes: palabras + iconos, ColPali en miniatura ─────────────────
PAGES_SRC = r'''
import math, unicodedata
from PIL import Image, ImageDraw, ImageFont

try: FUENTE = ImageFont.load_default(size=11)      # Pillow >= 10.1 trae una fuente escalable
except TypeError: FUENTE = ImageFont.load_default()
CH, CW, FILAS, COLS = 16, 96, 3, 4                  # celda de 16x96 px; página = 3x4 celdas = 12 "patches"

def plano(s: str) -> str:
    """La fuente por defecto no tiene tildes: las plegamos (la limitación es de la FUENTE, no del enfoque)."""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def celda_palabra(w: str, rng=None) -> np.ndarray:
    img = Image.new("L", (CW, CH), 255); dx = int(rng.integers(0, 6)) if rng is not None else 0; dy = int(rng.integers(0, 3)) if rng is not None else 0
    ImageDraw.Draw(img).text((2 + dx, 1 + dy), w, font=FUENTE, fill=0); return np.asarray(img, dtype=np.float32) / 255.

def celda_icono(k: int, rng) -> np.ndarray:
    """Icono (forma de color) 16x16 sobre una celda blanca: contenido NO textual (como un logo o una figura de la página)."""
    f, c = CONCEPTOS[k]; ic = dibuja(f, c, rng, S=16); lum = {"red": .35, "green": .6, "blue": .1, "yellow": .85}[c]   # el color -> nivel de gris
    mask = np.abs(ic - .5).max(-1) > .25; cel = np.ones((CH, CW), np.float32); x0 = int(rng.integers(0, CW - 16))
    cel[:, x0:x0 + 16] = np.where(mask, lum, 1.0); return cel

def celda_vacia() -> np.ndarray: return np.ones((CH, CW), np.float32)

def pagina_a_imagen(celdas, ruido: float, rng) -> np.ndarray:
    """Une 12 celdas en una imagen de 48x384 px y añade ruido gaussiano de píxel (escaneo/compresión)."""
    a = np.stack(celdas).reshape(FILAS, COLS, CH, CW).transpose(0, 2, 1, 3).reshape(FILAS * CH, COLS * CW)
    return a + rng.normal(0, ruido, a.shape).astype(np.float32)

def parchea(pagina: np.ndarray) -> np.ndarray:
    """Imagen de página -> (12, 16, 96): los 'patches' (celdas). Un ViT real usa cuadrados de 14-16 px; aquí cada patch es una celda."""
    return pagina.reshape(FILAS, CH, COLS, CW).transpose(0, 2, 1, 3).reshape(FILAS * COLS, CH, CW)

class RedPatch(nn.Module):
    """Codificador de patch: CNN -> vector L2-normalizado de dimensión D (como la proyección a 128-d de ColPali, en pequeño)."""
    def __init__(self, D: int = 32):
        super().__init__()
        self.c = nn.Sequential(nn.Conv2d(1, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2), nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                               nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool2d((2, 6)), nn.Flatten(), nn.Linear(64 * 12, D))
    def forward(self, x): return F.normalize(self.c(x.unsqueeze(1)), dim=-1)

def maxsim(Q: np.ndarray, P: np.ndarray) -> np.ndarray:
    """Late interaction (ColBERT/ColPali): score(q, pág) = sum_i max_j <q_i, p_j>.
    Q: (nq, D) tokens de la query; P: (n_págs, n_patches, D). Devuelve (n_págs,). Vectorizado con einsum."""
    return np.einsum("qd,npd->nqp", Q, P).max(axis=2).sum(axis=1)

def ocr_plantillas(palabras, rng_seed=0):
    """OCR 'clásico' por correlación: plantillas de cada palabra en TODOS los desplazamientos (dx, dy). Es un filtro adaptado,
    casi óptimo contra ruido gaussiano para texto renderizado con esta fuente. Devuelve (T, etiqueta de cada plantilla)."""
    T, lab = [celda_vacia().ravel()], [0]
    for k, w in enumerate(palabras, 1):
        for dx in range(6):
            for dy in range(3):
                img = Image.new("L", (CW, CH), 255); ImageDraw.Draw(img).text((2 + dx, 1 + dy), w, font=FUENTE, fill=0)
                T.append(np.asarray(img, dtype=np.float32).ravel() / 255.); lab.append(k)
    return np.stack(T), np.array(lab)

def ocr_pagina(parches: np.ndarray, T: np.ndarray, lab: np.ndarray) -> np.ndarray:
    """Reconoce cada patch como la palabra de la plantilla más cercana (L2). Los iconos se 'leen' mal: no son texto."""
    d = torch.cdist(torch.tensor(parches.reshape(len(parches), -1)), torch.tensor(T)); return lab[d.argmin(1).numpy()]
'''.strip("\n")
