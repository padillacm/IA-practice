"""Fuentes de código del módulo 17 (SAE TopK y ReLU+L1 desde cero, probing, diagnóstico de dimensiones)."""

SAE_SRC = r'''
import torch, torch.nn as nn, torch.nn.functional as F

class TopKSAE(nn.Module):
    """SAE con activación TopK (Gao et al., OpenAI 2024; k-sparse AE de Makhzani & Frey 2013).
    z = TopK(W_enc (x - b_dec) + b_enc) ; x_hat = W_dec z + b_dec ; columnas de W_dec de norma 1. L0 = k exacto (sin λ que ajustar)."""
    def __init__(self, d: int, n_lat: int, k: int):
        super().__init__(); self.d, self.n, self.k = d, n_lat, k
        W = F.normalize(torch.randn(d, n_lat), dim=0)
        self.W_dec = nn.Parameter(W.clone()); self.W_enc = nn.Parameter(W.clone().T.contiguous())      # inicialización "tied" (transpuesta)
        self.b_enc = nn.Parameter(torch.zeros(n_lat)); self.b_dec = nn.Parameter(torch.zeros(d))
        self.register_buffer("pasos_sin_activar", torch.zeros(n_lat))
    def pre(self, x): return (x - self.b_dec) @ self.W_enc.T + self.b_enc
    def encode(self, x, k=None):
        pre = self.pre(x); v, i = pre.topk(k or self.k, dim=-1)
        return torch.zeros_like(pre).scatter(-1, i, F.relu(v)), pre
    def decode(self, z): return z @ self.W_dec.T + self.b_dec
    def forward(self, x): z, pre = self.encode(x); return self.decode(z), z, pre
    @torch.no_grad()
    def normaliza_decoder(self): self.W_dec.data = F.normalize(self.W_dec.data, dim=0)

def entrena_topk(X, n_lat=256, k=4, pasos=1500, bs=256, lr=2e-3, auxk=True, k_aux=None, ventana_muerto=200, seed=0):
    """Entrena un TopK SAE. auxk=True añade la pérdida AuxK de Gao et al.: los latentes 'muertos' (sin activarse en `ventana_muerto`
    pasos) reconstruyen el RESIDUO del batch con sus top-k_aux preactivaciones -> los resucita. Devuelve (sae, historial)."""
    torch.manual_seed(seed); X = torch.as_tensor(X, dtype=torch.float32); d = X.shape[1]
    sae = TopKSAE(d, n_lat, k); sae.b_dec.data = X.mean(0).clone()                   # b_dec = media de los datos (centra la reconstrucción)
    opt = torch.optim.Adam(sae.parameters(), lr=lr); k_aux = k_aux or min(d // 2, n_lat // 4); var = ((X - X.mean(0)) ** 2).sum(1).mean()
    hist = {"nmse": [], "muertos": []}
    for t in range(pasos):
        x = X[torch.randint(0, len(X), (bs,))]; xh, z, pre = sae(x); err = x - xh
        loss = (err ** 2).sum(1).mean() / var
        activos = (z > 0).any(0); sae.pasos_sin_activar += 1; sae.pasos_sin_activar[activos] = 0
        muertos = sae.pasos_sin_activar > ventana_muerto
        if auxk and muertos.any():
            pm = pre.masked_fill(~muertos, -1e9); v, i = pm.topk(min(k_aux, int(muertos.sum())), dim=-1)
            za = torch.zeros_like(pre).scatter(-1, i, F.relu(v)); e_hat = za @ sae.W_dec.T
            loss = loss + (1 / 32) * ((err.detach() - e_hat) ** 2).sum(1).mean() / var
        opt.zero_grad(); loss.backward(); opt.step(); sae.normaliza_decoder()
        if t % 25 == 0: hist["nmse"].append(float(((err.detach()) ** 2).sum(1).mean() / var)); hist["muertos"].append(int(muertos.sum()))
    return sae.eval(), hist

def entrena_relu_l1(X, n_lat=256, lam=1e-2, pasos=1500, bs=256, lr=2e-3, seed=0):
    """SAE 'clásico' (Bricken et al., Anthropic 2023; Cunningham et al. 2023): z = ReLU(W_enc(x-b)+b_enc), pérdida = NMSE + λ·||z||_1."""
    torch.manual_seed(seed); X = torch.as_tensor(X, dtype=torch.float32); d = X.shape[1]
    sae = TopKSAE(d, n_lat, k=n_lat); sae.b_dec.data = X.mean(0).clone(); opt = torch.optim.Adam(sae.parameters(), lr=lr); var = ((X - X.mean(0)) ** 2).sum(1).mean()
    for _ in range(pasos):
        x = X[torch.randint(0, len(X), (bs,))]; z = F.relu(sae.pre(x)); xh = sae.decode(z)
        loss = ((x - xh) ** 2).sum(1).mean() / var + lam * z.abs().sum(1).mean()
        opt.zero_grad(); loss.backward(); opt.step(); sae.normaliza_decoder()
    sae.relu_mode = True; return sae.eval()

@torch.no_grad()
def codifica(sae, X, k=None):
    """Latentes (n, n_lat) y reconstrucción. Si el SAE es ReLU+L1 usa ReLU sin TopK."""
    X = torch.as_tensor(X, dtype=torch.float32)
    z = F.relu(sae.pre(X)) if getattr(sae, "relu_mode", False) else sae.encode(X, k)[0]
    return z, sae.decode(z)

def nmse(X, Xh):
    X, Xh = torch.as_tensor(X, dtype=torch.float32), torch.as_tensor(Xh, dtype=torch.float32)
    return float(((X - Xh) ** 2).sum() / ((X - X.mean(0)) ** 2).sum())
'''.strip("\n")

PROBE_SRC = r'''
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split

def sonda(X, y, tipo="lineal", seed=42):
    """Precisión en test de una sonda (clasificador) entrenada sobre embeddings congelados."""
    Xa, Xb, ya, yb = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=None)
    m = LogisticRegression(max_iter=2000) if tipo == "lineal" else MLPClassifier((256,), max_iter=400, random_state=seed)
    return float(m.fit(Xa, ya).score(Xb, yb))

def tarea_control(grupos, n_clases, seed=42):
    """Control task (Hewitt & Liang 2019): etiqueta ALEATORIA fija por cada 'tipo' (aquí: por faceta). Una sonda que memoriza tipos
    saca buena nota sin que el embedding codifique nada lingüístico -> selectividad = acc(tarea real) - acc(control)."""
    rng = np.random.default_rng(seed); tabla = {g: int(rng.integers(0, n_clases)) for g in sorted(set(grupos))}
    return np.array([tabla[g] for g in grupos])

def diagnostico_dimensiones(E):
    """Estadísticos de 'dimensiones dominantes' (Timkey & van Schijndel 2021): fracción de varianza de la dimensión top,
    coseno medio entre pares al azar (anisotropía) y el mismo coseno tras estandarizar cada dimensión."""
    E = np.asarray(E, dtype=np.float64); var = E.var(0); rng = np.random.default_rng(0); i, j = rng.integers(0, len(E), (2, 4000))
    cos = lambda A: float(np.mean(np.sum(A[i] * A[j], 1) / (np.linalg.norm(A[i], axis=1) * np.linalg.norm(A[j], axis=1) + 1e-12)))
    Z = (E - E.mean(0)) / (E.std(0) + 1e-12)
    return {"var_top1": float(var.max() / var.sum()), "var_top3": float(np.sort(var)[-3:].sum() / var.sum()), "coseno_medio": cos(E), "coseno_medio_estandarizado": cos(Z)}
'''.strip("\n")
