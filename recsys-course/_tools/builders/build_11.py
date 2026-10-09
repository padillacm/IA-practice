"""Construye los notebooks del módulo 11_generative_recsys.

Ejecutar desde la raíz del repo:  python recsys-course/_tools/builders/build_11.py
"""
import os
import sys

sys.path.insert(0, "recsys-course/_tools")
sys.path.insert(0, "recsys-course/_tools/builders")
from nbbuild import Notebook  # noqa: E402
from _b4_common import UTILS_MD, UTILS_LOAD, UTILS_SEQ, UTILS_EVAL  # noqa: E402

MOD = "recsys-course/11_generative_recsys"
LESSON = f"{MOD}/11_generative_recsys.ipynb"
PROJECT = f"{MOD}/11_proyecto_semantic_ids.ipynb"
os.makedirs(MOD, exist_ok=True)

PIP = r"""
# sentence-transformers (embeddings de texto de ítems) y huggingface_hub (Amazon Reviews 2023)
!pip install -q sentence-transformers huggingface_hub
"""

IMPORTS = r"""
import os, json, math, time, random, collections
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import seaborn as sns
import torch, torch.nn as nn, torch.nn.functional as F

seed = 42
random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
device = "cuda" if torch.cuda.is_available() else "cpu"
USE_AMP = device == "cuda" and torch.cuda.is_bf16_supported()
FAST_DEV_RUN = False          # True = iterar rápido; False = experimento completo (A100/L4)
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3})
print("device:", device, "| bf16:", USE_AMP, "| torch", torch.__version__)
"""

DRAW = r"""
def box(ax, x, y, w, h, text, fc="#dbeafe", ec="#1e3a8a", fs=9, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, weight=weight)

def arrow(ax, x1, y1, x2, y2, color="#334155", lw=1.2, style="-|>"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle=style, color=color, lw=lw))

def blank(ax, xlim=(0, 10), ylim=(0, 5)):
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.axis("off")
"""

DATA_GEN = r"""
AMZ_CATEGORY = "Video_Games"     # otras opciones: "Industrial_and_Scientific", "Musical_Instruments", "Toys_and_Games"...

def load_amazon2023(cat=AMZ_CATEGORY):
    '''Interacciones 5-core (benchmark oficial) + metadatos de Amazon Reviews 2023 (McAuley Lab) desde Hugging Face.'''
    from huggingface_hub import hf_hub_download
    repo = "McAuley-Lab/Amazon-Reviews-2023"
    inter = pd.read_csv(hf_hub_download(repo, f"benchmark/5core/rating_only/{cat}.csv", repo_type="dataset"))
    keep, rows = set(inter["parent_asin"]), []
    with open(hf_hub_download(repo, f"raw/meta_categories/meta_{cat}.jsonl", repo_type="dataset")) as f:
        for line in f:
            d = json.loads(line)
            if d.get("parent_asin") not in keep:
                continue
            cats = d.get("categories") or []
            text = (f"Title: {d.get('title') or ''}. Store: {d.get('store') or ''}. Categories: {', '.join(cats)}. "
                    f"Price: {d.get('price')}. Features: {' '.join((d.get('features') or [])[:3])}")[:1000]
            rows.append({"item": d["parent_asin"], "title": d.get("title") or "", "text": text,
                         "cat": cats[1] if len(cats) > 1 else (cats[0] if cats else "?")})
    meta = pd.DataFrame(rows).drop_duplicates("item")
    r = inter.rename(columns={"user_id": "user", "parent_asin": "item", "timestamp": "ts"})
    return r[r["item"].isin(set(meta["item"]))][["user", "item", "rating", "ts"]], meta

def load_generative_dataset():
    try:
        r, meta = load_amazon2023(); src = f"Amazon Reviews 2023 · {AMZ_CATEGORY} (5-core)"
    except Exception as e:
        print(f"⚠️ Amazon Reviews 2023 no disponible ({type(e).__name__}) → uso MovieLens-1M (título + géneros como texto)")
        r, mv = load_movielens_1m()
        meta = pd.DataFrame({"item": mv["item"], "title": mv["title"], "cat": mv["genres"].str.split("|").str[0],
                             "text": "Title: " + mv["title"] + ". Genres: " + mv["genres"].str.replace("|", ", ")})
        src = "MovieLens-1M"
    return r, meta, src

g_ratings, g_meta, g_src = load_generative_dataset()
g_seqs, g_item2idx, g_idx2item = build_sequences(g_ratings, min_len=5)
gn_items = len(g_item2idx)
g_train, g_valid, g_test = leave_one_out(g_seqs)
meta_idx = g_meta.set_index("item")
item_text = [meta_idx.loc[g_idx2item[i], "text"] for i in range(1, gn_items + 1)]
item_title = ["<pad>"] + [str(meta_idx.loc[g_idx2item[i], "title"])[:40] for i in range(1, gn_items + 1)]
item_cat = np.array(["<pad>"] + [str(meta_idx.loc[g_idx2item[i], "cat"]) for i in range(1, gn_items + 1)])
lens = np.array([len(s) for s in g_seqs])
print(f"{g_src}: usuarios={len(g_seqs):,} ítems={gn_items:,} interacciones={lens.sum():,} long. media={lens.mean():.1f}")
print("Ejemplo de texto de ítem:", item_text[0][:200])
"""

EMBED = r"""
def embed_texts(texts, model_name="sentence-transformers/sentence-t5-base", cache=None):
    '''Embeddings de contenido (TIGER usó Sentence-T5). Fallback offline: TF-IDF + SVD.'''
    if cache and os.path.exists(cache):
        X = np.load(cache)
        if X.shape[0] == len(texts):
            return X
    try:
        from sentence_transformers import SentenceTransformer
        st = SentenceTransformer(model_name, device=device)
        X = st.encode(texts, batch_size=128, show_progress_bar=True, normalize_embeddings=True, convert_to_numpy=True)
    except Exception as e:
        cache = None                                                # nunca cacheamos el fallback
        print(f"⚠️ sentence-transformers no disponible ({type(e).__name__}) → TF-IDF + SVD")
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD
        T = TfidfVectorizer(min_df=1, max_features=50000, ngram_range=(1, 2)).fit_transform(texts)
        X = TruncatedSVD(min(256, T.shape[1] - 1), random_state=seed).fit_transform(T)
        X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)
    X = X.astype(np.float32)
    if cache:
        os.makedirs(os.path.dirname(cache), exist_ok=True); np.save(cache, X)
    return X

X_items = embed_texts(item_text, cache=f"data/emb_{g_src.split(' ')[0]}_{gn_items}.npy")
print("embeddings de ítems:", X_items.shape)
"""

RQVAE = r"""
def kmeans_torch(x, K, iters=25, seed=seed):
    '''k-means sencillo en GPU. Devuelve (centroides [K,d], asignación [N]).'''
    g = torch.Generator(device=x.device).manual_seed(seed)
    idx = (torch.randperm(len(x), generator=g, device=x.device)[:K] if len(x) >= K
           else torch.randint(len(x), (K,), generator=g, device=x.device))
    C = x[idx].clone() + (1e-4 * torch.randn(K, x.size(1), generator=g, device=x.device) if len(x) < K else 0)
    for _ in range(iters):
        a = torch.cdist(x, C).argmin(1)
        S = torch.zeros_like(C).index_add_(0, a, x); cnt = torch.bincount(a, minlength=K).float()
        refill = x[torch.randint(len(x), (K,), generator=g, device=x.device)]
        C = torch.where((cnt == 0)[:, None], refill, S / cnt.clamp(min=1)[:, None])
    return C, torch.cdist(x, C).argmin(1)


class RQVAE(nn.Module):
    '''RQ-VAE (TIGER): encoder MLP -> cuantización residual con L codebooks de K códigos -> decoder MLP.'''
    def __init__(self, in_dim, latent=32, hidden=(512, 256, 128), levels=3, K=256, beta=0.25):
        super().__init__()
        dims, enc, dec = [in_dim, *hidden], [], []
        for a, b in zip(dims[:-1], dims[1:]):
            enc += [nn.Linear(a, b), nn.ReLU()]
        self.encoder = nn.Sequential(*enc, nn.Linear(dims[-1], latent))
        rd = [latent, *dims[::-1]]
        for a, b in zip(rd[:-1], rd[1:]):
            dec += [nn.Linear(a, b), nn.ReLU()]
        self.decoder = nn.Sequential(*dec[:-1])                       # sin ReLU final
        self.codebooks = nn.ParameterList([nn.Parameter(0.1 * torch.randn(K, latent)) for _ in range(levels)])
        self.K, self.L, self.beta = K, levels, beta

    def quantize(self, z):
        r, z_hat, codes, cb_loss = z, torch.zeros_like(z), [], 0.0
        for C in self.codebooks:
            c = torch.cdist(r, C).argmin(1); e = C[c]                     # código más cercano al residuo
            cb_loss = cb_loss + ((e - r.detach()) ** 2).sum(1).mean() + self.beta * ((r - e.detach()) ** 2).sum(1).mean()
            z_hat, r = z_hat + e, r - e.detach()                          # siguiente residuo
            codes.append(c)
        return z_hat, torch.stack(codes, 1), cb_loss

    def forward(self, x):
        z = self.encoder(x)
        z_hat, codes, cb_loss = self.quantize(z)
        x_hat = self.decoder(z + (z_hat - z).detach())                    # straight-through estimator
        return x_hat, codes, ((x_hat - x) ** 2).sum(1).mean(), cb_loss

    @torch.no_grad()
    def init_codebooks(self, x):                                          # k-means por nivel (truco de TIGER)
        r = self.encoder(x)
        for C in self.codebooks:
            cent, a = kmeans_torch(r, self.K); C.data.copy_(cent); r = r - cent[a]

    @torch.no_grad()
    def get_codes(self, x, batch=8192):
        return torch.cat([self.quantize(self.encoder(x[b:b + batch]))[1] for b in range(0, len(x), batch)])
"""

RQVAE_TRAIN = r"""
def collision_rate(codes):
    return 1 - len(np.unique(codes, axis=0)) / len(codes)

def add_dedup_token(codes):
    '''TIGER: añade un último token = índice del ítem dentro de su grupo de colisión -> IDs únicos.'''
    dup = pd.DataFrame(codes).groupby(list(range(codes.shape[1]))).cumcount().values
    return np.concatenate([codes, dup[:, None]], 1)

def train_rqvae(X, K=256, levels=3, latent=32, epochs=300, lr=1e-3, batch=1024, reset_every=20, log_every=25):
    Xt = torch.from_numpy(X).to(device)
    m = RQVAE(X.shape[1], latent, levels=levels, K=K).to(device)
    m.init_codebooks(Xt[torch.randperm(len(Xt), device=device)[:20000]])
    opt = torch.optim.Adam(m.parameters(), lr=lr)
    hist = collections.defaultdict(list)
    for ep in range(1, epochs + 1):
        m.train(); perm = torch.randperm(len(Xt), device=device)
        usage = torch.zeros(levels, K, device=device); rec_t = cb_t = 0.0
        for b in range(0, len(Xt), batch):
            x = Xt[perm[b:b + batch]]
            _, codes, rec, cb = m(x)
            loss = rec + cb
            opt.zero_grad(set_to_none=True); loss.backward(); opt.step()
            for l in range(levels):
                usage[l].index_add_(0, codes[:, l], torch.ones(len(codes), device=device))
            rec_t += rec.item() * len(x); cb_t += cb.item() * len(x)
        if reset_every and ep % reset_every == 0 and ep < epochs:          # reinicia códigos muertos
            with torch.no_grad():
                r = m.encoder(Xt[torch.randint(len(Xt), (4096,), device=device)])
                for l, C in enumerate(m.codebooks):
                    dead = usage[l] == 0
                    if dead.any():
                        C.data[dead] = r[torch.randint(len(r), (int(dead.sum()),), device=device)]
                    r = r - C[torch.cdist(r, C).argmin(1)]
        if ep % log_every == 0 or ep == epochs:
            codes_all = m.get_codes(Xt).cpu().numpy()
            hist["epoch"].append(ep); hist["recon"].append(rec_t / len(Xt)); hist["codebook"].append(cb_t / len(Xt))
            hist["collisions"].append(collision_rate(codes_all))
            for l in range(levels):
                hist[f"uso_nivel{l+1}"].append(len(np.unique(codes_all[:, l])) / K)
            print(f"ep {ep:4d} recon={hist['recon'][-1]:.4f} cb={hist['codebook'][-1]:.4f} "
                  f"colisiones={hist['collisions'][-1]:.2%} uso={[round(hist[f'uso_nivel{l+1}'][-1], 2) for l in range(levels)]}")
    return m, dict(hist)
"""

TRIE = r"""

class SemanticIDTrie:
    '''Árbol de prefijos de semantic IDs. Versión didáctica (dict) + versión vectorizada en GPU (searchsorted).'''
    def __init__(self, codes):                                   # codes [N, L] (sin offsets), fila i -> ítem i+1
        self.L, self.base = codes.shape[1], int(codes.max()) + 2
        self.children = collections.defaultdict(set)
        for c in codes[: min(len(codes), 200_000)]:
            for l in range(self.L):
                self.children[tuple(int(v) for v in c[:l])].add(int(c[l]))
        self.keys, self.nexts = [], []
        for l in range(self.L):
            pairs = np.unique(np.stack([self._key_np(codes[:, :l]), codes[:, l]], 1), axis=0)   # ordenado por clave
            self.keys.append(torch.from_numpy(pairs[:, 0]).to(device)); self.nexts.append(torch.from_numpy(pairs[:, 1]).to(device))
        full = self._key_np(codes)
        order = np.argsort(full)
        self.item_keys = torch.from_numpy(full[order]).to(device)
        self.item_ids = torch.from_numpy(order + 1).to(device)

    def _key_np(self, P):
        k = np.zeros(len(P), dtype=np.int64)
        for j in range(P.shape[1]):
            k = k * self.base + P[:, j] + 1
        return k

    def _key(self, P):
        k = torch.zeros(P.size(0), dtype=torch.long, device=P.device)
        for j in range(P.size(1)):
            k = k * self.base + P[:, j] + 1
        return k

    def allowed_mask(self, prefixes, level, size):
        '''prefixes [n, level] -> máscara bool [n, size] con los siguientes códigos válidos.'''
        q = self._key(prefixes)
        lo = torch.searchsorted(self.keys[level], q); hi = torch.searchsorted(self.keys[level], q, right=True)
        cnt = hi - lo
        rows = torch.repeat_interleave(torch.arange(len(q), device=q.device), cnt)
        offs = torch.arange(int(cnt.sum()), device=q.device) - torch.repeat_interleave(torch.cumsum(cnt, 0) - cnt, cnt)
        mask = torch.zeros(len(q), size, dtype=torch.bool, device=q.device)
        mask[rows, self.nexts[level][lo[rows] + offs]] = True
        return mask

    def lookup(self, codes):
        '''codes [..., L] -> índice de ítem (0 si el ID no existe).'''
        flat = codes.reshape(-1, self.L); k = self._key(flat)
        pos = torch.searchsorted(self.item_keys, k).clamp(max=len(self.item_keys) - 1)
        found = self.item_keys[pos] == k
        return torch.where(found, self.item_ids[pos], torch.zeros_like(pos)).view(codes.shape[:-1])
"""

TIGER = r"""
class TigerMini(nn.Module):
    '''Encoder-decoder (estilo TIGER): historial como tokens de semantic IDs -> genera el ID del siguiente ítem.'''
    def __init__(self, vocab, level_sizes, offsets, d=128, nhead=4, n_layers=4, ff=1024, dropout=0.1, max_src=80):
        super().__init__()
        self.L, self.vocab, self.bos = len(level_sizes), vocab, vocab - 1
        self.level_sizes, self.offsets = list(level_sizes), list(offsets)
        self.tok = nn.Embedding(vocab, d, padding_idx=0)
        self.src_pos, self.tgt_pos = nn.Embedding(max_src, d), nn.Embedding(self.L + 1, d)
        self.tf = nn.Transformer(d_model=d, nhead=nhead, num_encoder_layers=n_layers, num_decoder_layers=n_layers,
                                 dim_feedforward=ff, dropout=dropout, batch_first=True, norm_first=True)
        self.head = nn.Linear(d, vocab)
        lm = torch.full((self.L, vocab), float("-inf"))
        for l, (o, s) in enumerate(zip(offsets, level_sizes)):
            lm[l, o:o + s] = 0.0                                   # la posición l sólo emite tokens del nivel l
        self.register_buffer("level_mask", lm)

    def encode(self, src):
        pad = src == 0
        x = self.tok(src) + self.src_pos(torch.arange(src.size(1), device=src.device))
        return self.tf.encoder(x, src_key_padding_mask=pad), pad

    def decode(self, tgt_in, memory, pad):
        T = tgt_in.size(1)
        y = self.tok(tgt_in) + self.tgt_pos(torch.arange(T, device=tgt_in.device))
        causal = torch.triu(torch.ones(T, T, dtype=torch.bool, device=tgt_in.device), 1)
        out = self.tf.decoder(y, memory, tgt_mask=causal, memory_key_padding_mask=pad)
        return self.head(out) + self.level_mask[:T]

    def forward(self, src, tgt):                                    # tgt [B, L] tokens con offset
        memory, pad = self.encode(src)
        tgt_in = torch.cat([torch.full_like(tgt[:, :1], self.bos), tgt[:, :-1]], 1)
        logits = self.decode(tgt_in, memory, pad)
        return F.cross_entropy(logits.reshape(-1, self.vocab).float(), tgt.reshape(-1))
"""

TIGER_DATA = r"""
def build_token_tables(sid_codes, K):
    '''sid_codes [n_items, L] -> tabla item -> tokens (con offset por nivel; 0 = padding).'''
    level_sizes = [K] * (sid_codes.shape[1] - 1) + [int(sid_codes[:, -1].max()) + 1]
    offsets = (1 + np.concatenate([[0], np.cumsum(level_sizes)[:-1]])).astype(np.int64)
    vocab = 1 + int(sum(level_sizes)) + 1                          # + PAD + BOS
    tok = np.zeros((len(sid_codes) + 1, sid_codes.shape[1]), dtype=np.int64)
    tok[1:] = sid_codes + offsets
    return torch.from_numpy(tok), level_sizes, offsets, vocab

def make_src(histories, item_tokens, H=20):
    items = pad_left(histories, H)                                  # [B, H]
    return item_tokens[items].reshape(len(histories), -1)          # [B, H*L]; el padding (ítem 0) -> tokens 0

def gen_examples(train_seqs, H=20, max_examples=None, rng=np.random.default_rng(seed)):
    hist, tgt = [], []
    for s in train_seqs:
        for t in range(1, len(s)):
            hist.append(s[max(0, t - H):t]); tgt.append(s[t])
    if max_examples and len(tgt) > max_examples:
        sel = rng.choice(len(tgt), max_examples, replace=False)
        hist, tgt = [hist[i] for i in sel], [tgt[i] for i in sel]
    return hist, np.array(tgt)

def train_tiger(model, hist, tgt, item_tokens, epochs=10, batch_size=512, lr=5e-4, H=20, val=None, eval_fn=None):
    model.to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    total = epochs * math.ceil(len(tgt) / batch_size)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=total, pct_start=0.05)
    log = collections.defaultdict(list); t0 = time.time()
    for ep in range(1, epochs + 1):
        model.train(); perm = np.random.permutation(len(tgt)); tot = 0.0
        for b in range(0, len(perm), batch_size):
            idx = perm[b:b + batch_size]
            src = make_src([hist[i] for i in idx], item_tokens, H).to(device)
            y = item_tokens[tgt[idx]].to(device)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=USE_AMP):
                loss = model(src, y)
            opt.zero_grad(set_to_none=True); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sched.step()
            tot += loss.item() * len(idx)
        log["epoch"].append(ep); log["loss"].append(tot / len(tgt))
        msg = f"ep {ep:2d} loss={tot/len(tgt):.4f} ({time.time()-t0:.0f}s)"
        if eval_fn is not None:
            r = eval_fn(model); log["val_Recall@10"].append(r["Recall@10"]); msg += f"  val Recall@10={r['Recall@10']:.4f}"
        print(msg)
    return dict(log)
"""

BEAM = r"""
@torch.no_grad()
def beam_search(model, src, trie, beam=20, constrained=True):
    '''Beam search autoregresivo sobre semantic IDs. Devuelve códigos [B, beam, L] (sin offset) y log-probs [B, beam].'''
    model.eval()
    B = src.size(0)
    memory, pad = model.encode(src)
    codes = torch.zeros(B, 1, 0, dtype=torch.long, device=src.device)
    scores = torch.zeros(B, 1, device=src.device)
    off = torch.tensor(model.offsets, device=src.device)
    for l in range(model.L):
        nb, size = codes.size(1), model.level_sizes[l]
        prev_tok = codes + off[:l] if l > 0 else codes
        tgt_in = torch.cat([torch.full((B, nb, 1), model.bos, device=src.device), prev_tok], 2).view(B * nb, l + 1)
        logits = model.decode(tgt_in, memory.repeat_interleave(nb, 0), pad.repeat_interleave(nb, 0))[:, -1]
        logp = logits[:, model.offsets[l]:model.offsets[l] + size].float().log_softmax(-1)      # [B*nb, size]
        if constrained:                                                 # sólo continuaciones que existen en el trie
            logp = logp.masked_fill(~trie.allowed_mask(codes.view(B * nb, l), l, size), float("-inf"))
        cand = (scores.view(B * nb, 1) + logp).view(B, nb * size)
        top_s, top_i = cand.topk(min(beam, cand.size(1)), 1)
        bidx, tok = top_i // size, top_i % size
        codes = torch.cat([codes.gather(1, bidx[..., None].expand(-1, -1, l)), tok[..., None]], 2)
        scores = top_s
    return codes, scores

@torch.no_grad()
def eval_generative(model, histories, targets, trie, item_tokens, beam=20, ks=(10, 20), H=20, batch_size=256,
                    constrained=True, return_ranks=False):
    ranks, invalid, total = [], 0, 0
    for b in range(0, len(histories), batch_size):
        Hs = histories[b:b + batch_size]
        codes, scores = beam_search(model, make_src(Hs, item_tokens, H).to(device), trie, beam, constrained)
        items = trie.lookup(codes)                                       # [B, beam] (0 = ID inexistente)
        valid = (items > 0) & torch.isfinite(scores)
        invalid += int((~valid).sum()); total += valid.numel()
        for i, h in enumerate(Hs):                                       # no recomendar lo ya visto (igual que en 09)
            valid[i] &= ~torch.isin(items[i], torch.as_tensor(h[-200:], device=items.device))
        rank_in_valid = valid.long().cumsum(1) - 1                       # posición tras filtrar
        hit = valid & (items == torch.as_tensor(targets[b:b + batch_size], device=items.device)[:, None])
        r = torch.where(hit.any(1), (rank_in_valid * hit).sum(1), torch.full_like(hit[:, 0], 10**6, dtype=torch.long))
        ranks.append(r.cpu())
    ranks = torch.cat(ranks).numpy()
    out = {"invalid_rate": invalid / total}
    for k in ks:
        out[f"Recall@{k}"] = float((ranks < k).mean()); out[f"NDCG@{k}"] = float(((ranks < k) / np.log2(ranks + 2)).mean())
    return (out, ranks) if return_ranks else out
"""

SEQ11 = r"""
# ---- SASRec compacto (del módulo 09) y HSTU mini. Interfaz común: encode(seq, ts) -> [B, L, d] ----
def block_mask(seq, causal=True):
    B, L = seq.shape
    blk = (seq == 0)[:, None, None, :].expand(B, 1, L, L).clone()
    if causal:
        blk |= torch.triu(torch.ones(L, L, dtype=torch.bool, device=seq.device), 1)
    return blk & ~torch.eye(L, dtype=torch.bool, device=seq.device)

class SASRecBlock(nn.Module):
    def __init__(self, d, h, p):
        super().__init__()
        self.h, self.ln1, self.ln2 = h, nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv, self.o = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.ffn = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Dropout(p), nn.Linear(4 * d, d))
        self.drop, self.keep, self.last_attn = nn.Dropout(p), False, None
    def forward(self, x, blk, ts=None):
        B, L, D = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, L, 3, self.h, D // self.h).permute(2, 0, 3, 1, 4)
        a = ((q @ k.transpose(-2, -1)) / math.sqrt(D // self.h)).masked_fill(blk, float("-inf")).softmax(-1)
        if self.keep: self.last_attn = a.detach().float().cpu()
        x = x + self.drop(self.o((self.drop(a) @ v).transpose(1, 2).reshape(B, L, D)))
        return x + self.drop(self.ffn(self.ln2(x)))

class SASRec(nn.Module):
    def __init__(self, n_items, d=64, n_layers=2, n_heads=2, maxlen=200, dropout=0.2):
        super().__init__()
        self.n_items, self.d = n_items, d
        self.item_emb, self.pos_emb = nn.Embedding(n_items + 2, d, padding_idx=0), nn.Embedding(maxlen, d)
        nn.init.normal_(self.item_emb.weight, std=0.02); nn.init.normal_(self.pos_emb.weight, std=0.02)
        self.blocks = nn.ModuleList([SASRecBlock(d, n_heads, dropout) for _ in range(n_layers)])
        self.ln_f, self.drop = nn.LayerNorm(d), nn.Dropout(dropout)
    def encode(self, seq, ts=None):
        x = self.drop(self.item_emb(seq) + self.pos_emb(torch.arange(seq.size(1), device=seq.device))) * (seq > 0).unsqueeze(-1)
        blk = block_mask(seq)
        for b in self.blocks: x = b(x, blk)
        return self.ln_f(x)
"""

HSTU = r"""
class HSTULayer(nn.Module):
    '''Una capa HSTU (Zhai et al., ICML 2024):
       U,V,Q,K = Split(SiLU(f1(X)))                       (proyección pointwise)
       A·V     = SiLU(Q Kᵀ + rab^{p,t}) V / n             (agregación espacial SIN softmax)
       Y       = X + f2(Norm(A·V) ⊙ U)                    (transformación pointwise con puerta U)'''
    def __init__(self, d, n_heads, maxlen, dropout=0.2, n_time_buckets=64):
        super().__init__()
        self.h, self.dh, self.nb = n_heads, d // n_heads, n_time_buckets
        self.norm_in, self.norm_av = nn.LayerNorm(d), nn.LayerNorm(d)
        self.f1, self.f2 = nn.Linear(d, 4 * d), nn.Linear(d, d)
        self.pos_bias = nn.Parameter(torch.zeros(n_heads, maxlen))          # sesgo por distancia relativa
        self.time_bias = nn.Embedding(n_time_buckets, n_heads)             # sesgo por Δt (cubos log)
        nn.init.zeros_(self.time_bias.weight)
        self.drop, self.keep, self.last_attn = nn.Dropout(dropout), False, None

    def forward(self, x, allowed, ts):
        B, L, D = x.shape
        u, v, q, k = F.silu(self.f1(self.norm_in(x))).chunk(4, dim=-1)
        q, k, v = (t.view(B, L, self.h, self.dh).transpose(1, 2) for t in (q, k, v))
        ar = torch.arange(L, device=x.device)
        rel = (ar[:, None] - ar[None, :]).clamp(0, self.pos_bias.size(1) - 1)            # i - j
        dt = (ts[:, :, None] - ts[:, None, :]).abs().clamp(min=1).float()
        bucket = (torch.log(dt) / 0.301).long().clamp(0, self.nb - 1)                     # cubos log2
        rab = self.pos_bias[:, rel][None] + self.time_bias(bucket).permute(0, 3, 1, 2)    # [B, h, L, L]
        a = F.silu((q @ k.transpose(-2, -1)) / math.sqrt(self.dh) + rab) / L
        a = a * allowed                                                                   # causal + padding (sin -inf)
        if self.keep: self.last_attn = a.detach().float().cpu()
        av = (self.drop(a) @ v).transpose(1, 2).reshape(B, L, D)
        return x + self.drop(self.f2(self.norm_av(av) * u))

class HSTU(nn.Module):
    def __init__(self, n_items, d=64, n_layers=2, n_heads=2, maxlen=200, dropout=0.2):
        super().__init__()
        self.n_items, self.d = n_items, d
        self.item_emb = nn.Embedding(n_items + 2, d, padding_idx=0); nn.init.normal_(self.item_emb.weight, std=0.02)
        self.layers = nn.ModuleList([HSTULayer(d, n_heads, maxlen, dropout) for _ in range(n_layers)])
        self.ln_f, self.drop = nn.LayerNorm(d), nn.Dropout(dropout)
    def encode(self, seq, ts):
        valid = (seq > 0)
        x = self.drop(self.item_emb(seq)) * valid.unsqueeze(-1)
        allowed = (~block_mask(seq)).float()                                              # [B,1,L,L]
        for layer in self.layers: x = layer(x, allowed, ts)
        return self.ln_f(x)
"""

SEQ_TRAIN = r"""
def next_item_loss(model, h, tgt, loss="ce", n_neg=128):
    W, n, valid = model.item_emb.weight, model.n_items, tgt > 0
    if loss == "ce":
        return F.cross_entropy(h[valid] @ W[1:n + 1].T, tgt[valid] - 1)
    neg = torch.randint(1, n + 1, (h.size(0), n_neg), device=h.device)                    # sampled softmax uniforme
    pos_l = (h * W[tgt]).sum(-1)[valid]; neg_l = torch.einsum("bld,bkd->blk", h, W[neg])[valid]
    return F.cross_entropy(torch.cat([pos_l[:, None], neg_l], 1), torch.zeros(len(pos_l), dtype=torch.long, device=h.device))

def seq_score_fn(model, maxlen):
    '''Historias como tuplas (items, timestamps) para que HSTU reciba los tiempos.'''
    @torch.no_grad()
    def f(P):
        model.eval()
        seq = pad_left([p[0] for p in P], maxlen).to(device); ts = pad_left([p[1] for p in P], maxlen).to(device)
        return model.encode(seq, ts)[:, -1].float() @ model.item_emb.weight[: model.n_items + 1].float().T
    return f

def train_next_item(model, seqs, tss, val, epochs=50, maxlen=200, batch_size=128, lr=1e-3, loss="ce",
                    eval_every=10, name="modelo", n_val=2000):
    model.to(device); opt = torch.optim.Adam(model.parameters(), lr=lr)
    users = [i for i, s in enumerate(seqs) if len(s) >= 2]
    vsel = np.random.default_rng(0).choice(len(val[0]), min(n_val, len(val[0])), replace=False)
    vH, vT = [val[0][i] for i in vsel], [val[1][i] for i in vsel]
    hist, t0 = collections.defaultdict(list), time.time()
    for ep in range(1, epochs + 1):
        model.train(); perm, tot = np.random.permutation(users), 0.0
        for b in range(0, len(perm), batch_size):
            bi = perm[b:b + batch_size]
            inp = pad_left([seqs[i][:-1] for i in bi], maxlen).to(device); tgt = pad_left([seqs[i][1:] for i in bi], maxlen).to(device)
            ts = pad_left([tss[i][:-1] for i in bi], maxlen).to(device)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=USE_AMP):
                h = model.encode(inp, ts)
            l = next_item_loss(model, h.float(), tgt, loss)
            opt.zero_grad(set_to_none=True); l.backward(); opt.step(); tot += l.item() * len(bi)
        if ep % eval_every == 0 or ep == epochs:
            m = evaluate_next_item(seq_score_fn(model, maxlen), vH, vT, ks=(10,))
            hist["epoch"].append(ep); hist["loss"].append(tot / len(perm)); hist["val_NDCG@10"].append(m["NDCG@10"])
            print(f"[{name}] ep {ep:3d} loss={tot/len(perm):.4f} val NDCG@10={m['NDCG@10']:.4f} ({time.time()-t0:.0f}s)")
    hist["train_time_s"] = time.time() - t0
    return dict(hist)
"""

# ---------------------------------------------------------------------------
# LECCIÓN
# ---------------------------------------------------------------------------
nb = Notebook("Módulo 11 · Recomendadores generativos", colab_path=LESSON, gpu=True)
nb.md(f"""
{nb.badge()}

# Módulo 11 · Recomendadores generativos y *foundation models*
### Semantic IDs (RQ-VAE), TIGER, HSTU, OneRec, el modelo fundacional de Netflix y las *scaling laws*

| | |
|---|---|
| **Nivel** | 🔴 Experto |
| **Duración** | 5–6 h (lección) + 4 h (proyecto) |
| **GPU recomendada** | **A100** (L4 funciona con `FAST_DEV_RUN` o menos épocas) |
| **Unidades Colab estimadas** | ≈ 8–12 unidades en A100 en modo completo (≈ 45–60 min); ≈ 1 en modo rápido |
| **Prerrequisitos** | 08 (two-tower, ANN, sampled softmax), 09 (SASRec, pérdidas), 03 (embeddings de texto) |
""")
nb.md(r"""
## 🎯 Objetivos de aprendizaje
1. **Explicar** el cambio de paradigma *«recommendation as generation»*: de puntuar ítems con un producto escalar a **generar** el identificador del siguiente ítem (o la siguiente acción) token a token.
2. **Construir *semantic IDs*** con un **RQ-VAE** desde cero sobre embeddings de texto de ítems (Amazon Reviews 2023), diagnosticar colisiones y *codebook collapse*, y compararlo con **RQ-KMeans**.
3. **Implementar** un modelo generativo de *retrieval* estilo **TIGER** (encoder-decoder) con **beam search restringido por un trie** de IDs válidos.
4. **Implementar una capa HSTU** (atención *pointwise* con SiLU, sesgos relativos de posición y tiempo, puerta U) y compararla con SASRec.
5. **Medir** curvas de escalado (pérdida vs cómputo/parámetros) y discutir qué dicen realmente las *scaling laws* en recomendación.
6. **Analizar** los sistemas de producción 2024–2026: Meta GR/HSTU, Kuaishou OneRec (V1/V2), Netflix, YouTube (Semantic IDs, PLUM), Pinterest PinRec.
7. **Decidir** cuándo compensa un recomendador generativo frente a un two-tower + ANN y qué riesgos introduce.
""")
nb.code(PIP)
nb.code(IMPORTS)
nb.md(UTILS_MD)
nb.code(UTILS_LOAD)
nb.code(UTILS_SEQ)
nb.code(UTILS_EVAL)
nb.code(DRAW)

nb.md(r"""
## 💡 1. Intuición: de *puntuar* a *generar*

Hasta ahora todos los recomendadores eran **discriminativos**: un modelo produce un vector de usuario y **puntuamos** ítems (producto escalar + ANN en el módulo 08; softmax sobre el catálogo en el 09).
Esto tiene dos límites estructurales:
1. **La tabla de embeddings de ítems** crece con el catálogo (miles de millones de filas en YouTube/TikTok) y los ítems nuevos no tienen fila → *cold start*.
2. **La cascada** retrieval → ranking → re-ranking tiene objetivos inconsistentes entre etapas y desperdicia cómputo.

Los LLM sugieren otra vía: **generar la respuesta token a token**. Para eso el ítem necesita un nombre hecho de pocos tokens de un vocabulario pequeño: un **semantic ID**, p. ej. `(17, 203, 5, 0)`,
donde ítems parecidos comparten prefijo (`(17, …)` = «juegos de rol de PlayStation», `(17, 203, …)` = «RPG japonés de PS4»…).

💡 **Analogía**: es como el **código postal**. No necesitas un identificador aleatorio por casa: `28` = Madrid, `280` = Madrid capital, `28013` = Sol. Un modelo que «sabe geografía» puede generar códigos postales plausibles para casas que nunca vio.

Tres familias que veremos:
| Familia | Qué genera | Ejemplo |
|---|---|---|
| **Generative retrieval** con semantic IDs | los tokens del ID del siguiente ítem | TIGER (Google, NeurIPS 2023), PLUM (YouTube 2025), OneRec (Kuaishou 2025) |
| **Generative Recommenders** (transducción secuencial) | el siguiente ítem **y** la siguiente acción sobre él, en una secuencia unificada | HSTU (Meta, ICML 2024) |
| ***Foundation models*** de recomendación | modelo autoregresivo único pre-entrenado sobre todas las interacciones, reutilizado por muchas superficies | Netflix (2025) |
""")
nb.code(r"""
# 📊 Diagrama 1 — Paradigmas: two-tower + ANN vs generative retrieval vs Generative Recommender (HSTU)
fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))
ax = axes[0]; blank(ax, (0, 6), (0, 6)); ax.set_title("Discriminativo: two-tower + ANN", fontsize=10)
box(ax, 0.3, 4.4, 2.2, 0.8, "historial usuario", fc="#f1f5f9"); box(ax, 3.4, 4.4, 2.3, 0.8, "catálogo (N ítems)", fc="#f1f5f9")
box(ax, 0.3, 2.9, 2.2, 0.8, "torre usuario → u", fc="#bfdbfe"); box(ax, 3.4, 2.9, 2.3, 0.8, "tabla N×d → e_i", fc="#bfdbfe")
box(ax, 1.5, 1.2, 3.0, 0.8, "ANN: top-K de uᵀe_i", fc="#fde68a")
for x0, x1 in [(1.4, 1.4), (4.55, 4.55)]: arrow(ax, x0, 4.4, x1, 3.7)
arrow(ax, 1.4, 2.9, 2.5, 2.0); arrow(ax, 4.55, 2.9, 3.6, 2.0)
ax = axes[1]; blank(ax, (0, 6), (0, 6)); ax.set_title("Generative retrieval (TIGER)", fontsize=10)
box(ax, 0.3, 4.5, 5.4, 0.8, "historial como tokens: (3,41,7,0) (3,41,9,0) (12,5,88,1)", fc="#f1f5f9", fs=8)
box(ax, 0.3, 3.0, 5.4, 0.9, "Transformer encoder-decoder", fc="#ddd6fe")
for j, t in enumerate(["c₁=3", "c₂=41", "c₃=12", "c₄=0"]):
    box(ax, 0.4 + j * 1.38, 1.3, 1.15, 0.7, t, fc="#fde68a", fs=8)
    if j < 3: arrow(ax, 1.55 + j * 1.38, 1.65, 1.78 + j * 1.38, 1.65, color="#b45309")
arrow(ax, 3.0, 4.5, 3.0, 3.9); arrow(ax, 3.0, 3.0, 3.0, 2.0)
ax.text(3.0, 0.6, "beam search + trie de IDs válidos", ha="center", fontsize=8, style="italic")
ax = axes[2]; blank(ax, (0, 6), (0, 6)); ax.set_title("Generative Recommender (HSTU)", fontsize=10)
toks = ["Φ₀", "a₀", "Φ₁", "a₁", "Φ₂", "a₂", "Φ₃", "?"]
for j, t in enumerate(toks):
    box(ax, 0.2 + j * 0.71, 4.4, 0.62, 0.7, t, fc="#e0f2fe" if t.startswith("Φ") else "#dcfce7", fs=8)
box(ax, 0.2, 2.8, 5.6, 0.9, "HSTU causal (atención pointwise)", fc="#ddd6fe")
box(ax, 0.2, 1.1, 2.6, 0.9, "retrieval: en aᵢ → Φᵢ₊₁", fc="#fde68a", fs=8); box(ax, 3.2, 1.1, 2.6, 0.9, "ranking: en Φᵢ → aᵢ", fc="#fecaca", fs=8)
arrow(ax, 3.0, 4.4, 3.0, 3.7); arrow(ax, 2.0, 2.8, 1.5, 2.0); arrow(ax, 4.0, 2.8, 4.5, 2.0)
plt.tight_layout(); plt.show()
""")
nb.code(r"""
# 📊 Gráfico 2 — Memoria: tabla de embeddings por ítem vs semantic IDs (L=3 niveles, K=256, d=256, fp32)
N = np.logspace(4, 10, 50); d, L, K = 256, 3, 256
table_gb = N * d * 4 / 1e9
sid_gb = (L * K * d * 4 + N * (L + 1) * 2) / 1e9          # codebooks/embeddings de tokens + 4 códigos uint16 por ítem
fig, ax = plt.subplots(figsize=(8, 4))
ax.loglog(N, table_gb, lw=2.5, label="tabla de IDs (N × d)")
ax.loglog(N, sid_gb, lw=2.5, label="semantic IDs (L·K × d + códigos)")
for n, lbl in [(3.7e3, "ML-1M"), (2.5e4, "Amazon Video Games"), (1e9, "escala YouTube/TikTok")]:
    ax.axvline(n, ls=":", c="gray"); ax.text(n * 1.1, 1e-4, lbl, rotation=90, fontsize=8, va="bottom")
ax.set(xlabel="nº de ítems N", ylabel="memoria (GB)", title="Embeddings por ítem vs vocabulario de semantic IDs"); ax.legend()
plt.show()
""")

nb.md(r"""
## 📐 2. Teoría formal

### 2.1 Semantic IDs por cuantización residual (RQ-VAE)
Partimos de un embedding de **contenido** del ítem $\mathbf{x}\in\mathbb{R}^{D}$ (texto con Sentence-T5 en TIGER). Un *encoder* lo lleva a un latente $\mathbf{z} = E(\mathbf{x})\in\mathbb{R}^{d}$.
Con $L$ *codebooks* $\{\mathbf{e}^{(l)}_k\}_{k=1}^{K}$ cuantizamos el **residuo** de forma iterativa:
$$\mathbf{r}_1 = \mathbf{z},\qquad c_l = \arg\min_k \|\mathbf{r}_l - \mathbf{e}^{(l)}_k\|^2,\qquad \mathbf{r}_{l+1} = \mathbf{r}_l - \mathbf{e}^{(l)}_{c_l}$$
El semantic ID es la tupla $(c_1,\dots,c_L)$ y la reconstrucción del latente es $\hat{\mathbf{z}} = \sum_{l}\mathbf{e}^{(l)}_{c_l}$. Cada nivel refina al anterior: de lo grueso a lo fino (como el código postal).
La pérdida (TIGER, siguiendo a Lee et al. 2022):
$$\mathcal{L} = \underbrace{\|\mathbf{x} - D(\hat{\mathbf{z}})\|^2}_{\text{reconstrucción}} + \sum_{l=1}^{L}\Big(\underbrace{\|\mathrm{sg}[\mathbf{r}_l] - \mathbf{e}^{(l)}_{c_l}\|^2}_{\text{codebook}} + \beta\underbrace{\|\mathbf{r}_l - \mathrm{sg}[\mathbf{e}^{(l)}_{c_l}]\|^2}_{\text{commitment}}\Big)$$
- $\mathrm{sg}[\cdot]$: *stop-gradient*. El $\arg\min$ no es derivable: se usa el **straight-through estimator** $\hat{\mathbf z}_{\text{st}} = \mathbf z + \mathrm{sg}[\hat{\mathbf z}-\mathbf z]$.
- $\beta = 0{,}25$. TIGER usa $L=3$, $K=256$, latente de 32 dimensiones e inicializa los *codebooks* con **k-means** para evitar *codebook collapse*.
- **Colisiones**: dos ítems con la misma tupla. TIGER añade un 4.º token que los desambigua (0, 1, 2…).

### 2.2 Generative retrieval
Con $\mathrm{SID}(i) = (c_1,\dots,c_L)$, el modelo factoriza autoregresivamente:
$$p(i_{t+1}\mid \text{hist}) = \prod_{l=1}^{L} p\big(c_l \mid c_{<l},\; \mathrm{SID}(i_1),\dots,\mathrm{SID}(i_t)\big)$$
Se entrena con *cross-entropy* por token (*teacher forcing*) y se infiere con **beam search**. El vocabulario es $L\cdot K$ (768 tokens) en vez de $N$.
Para no generar IDs inexistentes se restringe cada paso a los hijos válidos del prefijo en un **trie** (*constrained decoding*).

### 2.3 HSTU (Hierarchical Sequential Transduction Unit)
Para una secuencia $X\in\mathbb{R}^{n\times d}$, cada capa HSTU hace (Zhai et al., 2024):
$$U(X),V(X),Q(X),K(X) = \mathrm{Split}\big(\phi_1(f_1(X))\big)$$
$$A(X)V(X) = \frac{\phi_2\big(Q(X)K(X)^\top + \mathrm{rab}^{p,t}\big)}{n}\,V(X)$$
$$Y(X) = f_2\Big(\mathrm{Norm}\big(A(X)V(X)\big)\odot U(X)\Big)$$
- $\phi_1,\phi_2 = \mathrm{SiLU}$; $f_1, f_2$ lineales; $\mathrm{rab}^{p,t}$ = sesgo relativo de **posición** y de **tiempo** (cubos de $\log\Delta t$).
- **Sin softmax**: la atención *pointwise* conserva la **intensidad** (cuántos ítems relevantes hay en el historial), que la softmax normaliza y destruye. Muy importante con vocabularios no estacionarios.
- $U(X)$ actúa como **puerta** (como en *gated* MLPs / interacciones de features de un DLRM).

**Generative Recommenders**: la secuencia intercala ítems y acciones $(\Phi_0, a_0, \Phi_1, a_1, \dots)$. **Retrieval** = predecir $\Phi_{i+1}$; **ranking** = predecir $a_i$ dado $\Phi_i$ (con **M-FALCON** se puntúan miles de candidatos en una pasada reutilizando el KV-cache).

### 2.4 Scaling laws
En LLMs la pérdida sigue $\mathcal{L}(C)\approx a\,C^{-b}$ en el cómputo $C$. En recomendación, Meta reportó que la calidad de GR **escala como ley de potencias en el cómputo de entrenamiento a lo largo de tres órdenes de magnitud**, algo que los DLRM clásicos no conseguían.
Aproximación de cómputo de un Transformer: $C\approx 6\,N_{\text{no-emb}}\,T$ ($N_{\text{no-emb}}$ = parámetros sin contar embeddings, $T$ = tokens procesados).
""")

# ---------------- Datos
nb.md(r"""
## 📦 3. Datos: Amazon Reviews 2023 (McAuley Lab)

Para semantic IDs necesitamos **contenido** de los ítems. Usamos **Amazon Reviews 2023** (Hou et al., 2024): 571 M de reseñas y metadatos ricos (título, tienda, categorías, *features*, precio) de 33 categorías,
alojado en Hugging Face (`McAuley-Lab/Amazon-Reviews-2023`) con *benchmarks* oficiales ya filtrados (5-core) para recomendación secuencial.
Descargamos `benchmark/5core/rating_only/<Categoría>.csv` (user, item, rating, timestamp) y `raw/meta_categories/meta_<Categoría>.jsonl` (metadatos).

- Categoría por defecto: **Video_Games** (decenas de miles de ítems; ~minutos de descarga). Cámbiala en `AMZ_CATEGORY`.
- Fallback automático: MovieLens-1M con título + géneros como texto (y, sin red, datos sintéticos).
- 🔗 CineMatch: la misma tubería se aplica a películas con sinopsis/pósters (módulo 03). Usamos Amazon porque su texto es mucho más rico que el de ML-1M.
""")
nb.code(DATA_GEN)
nb.md(r"""
### 3.1 Embeddings de contenido
Codificamos el texto de cada ítem con **Sentence-T5** (`sentence-transformers/sentence-t5-base`, 768 d), el mismo tipo de *encoder* que usó TIGER. En A100 tarda ~1–2 min para ~25 k ítems.
""")
nb.code(EMBED)

# ---------------- RQ-VAE
nb.md(r"""
## 🛠️ 4. RQ-VAE desde cero
Implementación compacta: MLP $768\to512\to256\to128\to32$, 3 *codebooks* de 256 códigos, inicialización por **k-means** y **reinicio de códigos muertos** (un truco estándar de VQ para combatir el *collapse*).
""")
nb.code(RQVAE)
nb.code(RQVAE_TRAIN)
nb.code(r"""
CODEBOOK_SIZE = 256
RQ_EPOCHS = 30 if FAST_DEV_RUN else 400
torch.manual_seed(seed)
rqvae, rq_hist = train_rqvae(X_items, K=CODEBOOK_SIZE, levels=3, epochs=RQ_EPOCHS, log_every=max(1, RQ_EPOCHS // 10))
codes3 = rqvae.get_codes(torch.from_numpy(X_items).to(device)).cpu().numpy()
print(f"Colisiones (3 niveles): {collision_rate(codes3):.2%} de los ítems comparten tupla con otro")
""")
nb.code(r"""
# 📊 Gráfico 3 — Entrenamiento del RQ-VAE: pérdidas, uso de codebooks y colisiones
fig, ax = plt.subplots(1, 3, figsize=(16, 3.8))
ax[0].plot(rq_hist["epoch"], rq_hist["recon"], lw=2, label="reconstrucción")
ax[0].plot(rq_hist["epoch"], rq_hist["codebook"], lw=2, label="codebook + commitment")
ax[0].set(title="Pérdidas RQ-VAE", xlabel="época", yscale="log"); ax[0].legend()
for l in range(3):
    ax[1].plot(rq_hist["epoch"], rq_hist[f"uso_nivel{l+1}"], lw=2, label=f"nivel {l+1}")
ax[1].set(title="Fracción de códigos usados por nivel", xlabel="época", ylim=(0, 1.05)); ax[1].legend()
ax[2].plot(rq_hist["epoch"], np.array(rq_hist["collisions"]) * 100, lw=2, c="#ef4444")
ax[2].set(title="% de ítems en colisión (3 niveles)", xlabel="época", ylabel="%")
plt.tight_layout(); plt.show()
""")

nb.md(r"""
### 4.1 La alternativa industrial: RQ-KMeans
Kuaishou (OneRec) tokeniza con **RQ-KMeans**: k-means residual directamente sobre los embeddings, **sin red**. Es más simple, estable y garantiza el uso de todos los códigos.
Comparamos ambos en colisiones, uso de códigos y **pureza semántica** (¿los ítems con el mismo primer código comparten categoría?).
""")
nb.code(r"""
def rq_kmeans(X, K=256, levels=3, iters=25):
    r = torch.from_numpy(X).to(device); codes = []
    for l in range(levels):
        C, a = kmeans_torch(r, K, iters=iters, seed=seed + l); codes.append(a); r = r - C[a]
    return torch.stack(codes, 1).cpu().numpy()

codes_km = rq_kmeans(X_items, K=CODEBOOK_SIZE)

def purity(codes_l1, cats, min_size=5):
    df_ = pd.DataFrame({"c": codes_l1, "cat": cats})
    g = df_.groupby("c")["cat"].agg(lambda s: s.value_counts(normalize=True).iloc[0] if len(s) >= min_size else np.nan)
    return g.dropna().values

cats = item_cat[1:]
rng = np.random.default_rng(seed)
cmp = pd.DataFrame({
    "RQ-VAE": [collision_rate(codes3), len(np.unique(codes3[:, 0])) / CODEBOOK_SIZE, np.mean(purity(codes3[:, 0], cats))],
    "RQ-KMeans": [collision_rate(codes_km), len(np.unique(codes_km[:, 0])) / CODEBOOK_SIZE, np.mean(purity(codes_km[:, 0], cats))],
    "Aleatorio": [np.nan, np.nan, np.mean(purity(rng.permutation(codes3[:, 0]), cats))]},
    index=["colisiones", "uso nivel 1", "pureza media nivel 1"]).T
display(cmp.round(3))
fig, ax = plt.subplots(figsize=(8, 3.6))
for name, c in [("RQ-VAE", codes3[:, 0]), ("RQ-KMeans", codes_km[:, 0]), ("Aleatorio", rng.permutation(codes3[:, 0]))]:
    ax.hist(purity(c, cats), bins=20, alpha=0.55, label=name, range=(0, 1))
ax.set(title="📊 Gráfico 4 — Pureza de categoría de cada código de nivel 1", xlabel="fracción de la categoría mayoritaria", ylabel="nº de códigos")
ax.legend(); plt.show()
""")
nb.code(r"""
# Semantic IDs finales: 3 códigos + token de desambiguación (TIGER)
sid_codes = add_dedup_token(codes3)
print("Tamaño de cada nivel:", [CODEBOOK_SIZE] * 3 + [int(sid_codes[:, 3].max()) + 1],
      "| IDs únicos:", len(np.unique(sid_codes, axis=0)) == len(sid_codes))
for i in np.random.default_rng(1).choice(gn_items, 5, replace=False):
    print(tuple(sid_codes[i]), "→", item_title[i + 1], f"[{item_cat[i + 1]}]")
""")
nb.code(r"""
# 📊 Gráfico 5 — El trie de semantic IDs (subárbol de los prefijos más poblados)
def draw_trie(codes, titles, n1=3, n2=2, n3=2):
    fig, ax = plt.subplots(figsize=(15, 5.5)); blank(ax, (0, 1), (-0.15, 3.3))
    df_ = pd.DataFrame(codes[:, :3], columns=["c1", "c2", "c3"]); df_["t"] = titles
    leaves = []
    for c1 in df_.c1.value_counts().index[:n1]:
        d1 = df_[df_.c1 == c1]
        for c2 in d1.c2.value_counts().index[:n2]:
            d2 = d1[d1.c2 == c2]
            for c3 in d2.c3.value_counts().index[:n3]:
                d3 = d2[d2.c3 == c3]; leaves.append((c1, c2, c3, len(d3), d3.t.iloc[0]))
    xs = np.linspace(0.04, 0.96, len(leaves)); root = (0.5, 3.1)
    ax.text(*root, "raíz", ha="center", bbox=dict(fc="#e5e7eb", ec="gray"))
    pos1, pos2 = {}, {}
    for x, (c1, c2, c3, n, t) in zip(xs, leaves):
        pos1.setdefault(c1, []).append(x); pos2.setdefault((c1, c2), []).append(x)
    for c1, v in pos1.items():
        x1 = np.mean(v); ax.plot([root[0], x1], [3.05, 2.25], c="#94a3b8"); ax.text(x1, 2.2, f"c₁={c1}", ha="center", bbox=dict(fc="#bfdbfe", ec="#1d4ed8"))
        for (a, c2), v2 in pos2.items():
            if a != c1: continue
            x2 = np.mean(v2); ax.plot([x1, x2], [2.12, 1.38], c="#94a3b8"); ax.text(x2, 1.32, f"c₂={c2}", ha="center", bbox=dict(fc="#ddd6fe", ec="#6d28d9"))
    for x, (c1, c2, c3, n, t) in zip(xs, leaves):
        ax.plot([np.mean(pos2[(c1, c2)]), x], [1.25, 0.55], c="#94a3b8")
        ax.text(x, 0.5, f"c₃={c3}\n({n} ítems)", ha="center", fontsize=7, bbox=dict(fc="#fde68a", ec="#b45309"))
        ax.text(x, 0.05, t[:18], ha="center", fontsize=6, rotation=20)
    ax.set_title("Trie de semantic IDs: los ítems que comparten prefijo son semánticamente cercanos")
    plt.show()

draw_trie(sid_codes, item_title[1:])
""")

# ---------------- TIGER
nb.md(r"""
## 🧠 5. Generative retrieval estilo TIGER

**Tokens**: cada nivel tiene su propio rango del vocabulario (offset), así el token `5` del nivel 1 y el `5` del nivel 2 son tokens distintos. `0` = *padding*, último token = `BOS`.
**Entrada**: los últimos 20 ítems del historial → 80 tokens. **Salida**: 4 tokens del siguiente ítem.
**Modelo**: `nn.Transformer` encoder-decoder (4+4 capas, $d=128$, FFN 1024), parecido en tamaño al de TIGER (~13 M parámetros), con una máscara que obliga a la posición $l$ a emitir sólo tokens del nivel $l$.
""")
nb.code(TIGER)
nb.code(TIGER_DATA)
nb.code(TRIE)
nb.code(BEAM)
nb.code(r"""
H_HIST = 20
item_tokens, level_sizes, offsets, VOCAB = build_token_tables(sid_codes, CODEBOOK_SIZE)
trie = SemanticIDTrie(sid_codes)
print("vocabulario:", VOCAB, "| niveles:", level_sizes, "| offsets:", offsets.tolist())
print("Hijos válidos de la raíz:", len(trie.children[()]), "| hijos de", (int(sid_codes[0, 0]),), ":",
      sorted(trie.children[(int(sid_codes[0, 0]),)])[:10], "…")
tr_hist, tr_tgt = gen_examples(g_train, H=H_HIST, max_examples=50_000 if FAST_DEV_RUN else 2_000_000)
print(f"ejemplos de entrenamiento: {len(tr_tgt):,}")
vsel = np.random.default_rng(0).choice(len(g_valid[0]), min(2000, len(g_valid[0])), replace=False)
val_small = ([g_valid[0][i] for i in vsel], [g_valid[1][i] for i in vsel])
torch.manual_seed(seed)
tiger = TigerMini(VOCAB, level_sizes, offsets, d=128, nhead=4, n_layers=4, ff=1024, dropout=0.1, max_src=H_HIST * 4)
print(f"parámetros TIGER-mini: {sum(p.numel() for p in tiger.parameters())/1e6:.2f} M")
""")
nb.code(r"""
TIGER_EPOCHS = 2 if FAST_DEV_RUN else 20          # ~1 min/época en A100 con Video_Games
eval_val = lambda m: eval_generative(m, *val_small, trie, item_tokens, beam=10, ks=(10,), H=H_HIST)
tiger_log = train_tiger(tiger, tr_hist, tr_tgt, item_tokens, epochs=TIGER_EPOCHS, batch_size=512, lr=5e-4,
                        H=H_HIST, eval_fn=eval_val)
""")
nb.code(r"""
# Evaluación en test: beam=20, con y sin restricción de trie
N_EVAL = len(g_test[0]) if not FAST_DEV_RUN else min(1000, len(g_test[0]))
ev_sel = np.random.default_rng(1).choice(len(g_test[0]), N_EVAL, replace=False)
test_H, test_T = [g_test[0][i] for i in ev_sel], [g_test[1][i] for i in ev_sel]
gen_res = {}
gen_res["TIGER-mini (trie)"], tiger_ranks = eval_generative(tiger, test_H, test_T, trie, item_tokens, beam=20, H=H_HIST, return_ranks=True)
gen_res["TIGER-mini (sin trie)"] = eval_generative(tiger, test_H, test_T, trie, item_tokens, beam=20, H=H_HIST, constrained=False)
display(pd.DataFrame(gen_res).T.round(4))
""")
nb.md(r"""
### 5.1 Comparación justa con SASRec (embeddings por ID) y popularidad
Mismo *split*, mismos usuarios de test, *full ranking* para SASRec (módulo 09, versión compacta) con CE completa.
""")
nb.code(SEQ11)
nb.code(SEQ_TRAIN)
nb.code(r"""
g_ts = [list(range(len(s))) for s in g_seqs]           # SASRec no usa tiempos: posiciones como relleno
g_train_ts = [t[:-2] for t in g_ts]
G_MAXLEN = 50
torch.manual_seed(seed)
sas_g = SASRec(gn_items, d=64, n_layers=2, n_heads=2, maxlen=G_MAXLEN, dropout=0.3)
g_val_pairs = ([(h, list(range(len(h)))) for h in g_valid[0]], g_valid[1])
train_next_item(sas_g, g_train, g_train_ts, g_val_pairs, epochs=3 if FAST_DEV_RUN else 60, maxlen=G_MAXLEN,
                batch_size=256, eval_every=1 if FAST_DEV_RUN else 10, name="SASRec-Amazon")
test_pairs = [(h, list(range(len(h)))) for h in test_H]
hr2recall = lambda d: {k.replace("HR@", "Recall@"): v for k, v in d.items()}
gen_res["SASRec+ (CE, IDs)"] = hr2recall(evaluate_next_item(seq_score_fn(sas_g, G_MAXLEN), test_pairs, test_T, ks=(10, 20)))
popg = np.bincount(np.concatenate(g_train), minlength=gn_items + 1).astype(np.float32)
gen_res["Popularidad"] = hr2recall(evaluate_next_item(lambda H: torch.from_numpy(np.tile(popg, (len(H), 1))), test_H, test_T, ks=(10, 20)))
gr = pd.DataFrame(gen_res).T; display(gr.round(4))
""")
nb.code(r"""
# 📊 Gráfico 6 — Resultados de retrieval + tasa de IDs inválidos + rendimiento por popularidad del ítem objetivo
fig, ax = plt.subplots(1, 3, figsize=(17, 4))
gr[["Recall@10", "NDCG@10"]].plot.barh(ax=ax[0]); ax[0].set(title=f"Test ({g_src.split('·')[0].strip()})")
inv = gr["invalid_rate"].dropna() * 100
ax[1].bar(inv.index, inv.values, color=["#10b981", "#ef4444"][: len(inv)]); ax[1].set(title="% de IDs generados inexistentes (beam=20)", ylabel="%")
sas_ranks = []
with torch.no_grad():
    fn = seq_score_fn(sas_g, G_MAXLEN)
    for b in range(0, len(test_pairs), 512):
        P, T = test_pairs[b:b + 512], torch.as_tensor(test_T[b:b + 512])
        s = fn(P).cpu(); tg = s.gather(1, T[:, None]).clone(); s[:, 0] = -1e9
        for i, p in enumerate(P): s[i, p[0]] = -1e9
        s.scatter_(1, T[:, None], tg); sas_ranks.append((s > tg).sum(1))
sas_ranks = torch.cat(sas_ranks).numpy()
tpop = popg[np.array(test_T)]
qs = pd.qcut(pd.Series(tpop).rank(method="first"), 4, labels=["Q1 (cola)", "Q2", "Q3", "Q4 (popular)"])
dfq = pd.DataFrame({"q": qs, "TIGER-mini": tiger_ranks < 10, "SASRec+": sas_ranks < 10}).groupby("q", observed=True).mean()
dfq.plot.bar(ax=ax[2], rot=0); ax[2].set(title="Recall@10 según popularidad del ítem objetivo", xlabel="")
plt.tight_layout(); plt.show()
""")
nb.md(r"""
**Qué esperar (y por qué).**
- Con el trie, la tasa de IDs inválidos es **0** por construcción; sin él, una fracción de los *beams* se desperdicia en IDs inexistentes.
- En *benchmarks* académicos TIGER superaba a SASRec **entrenado con BCE** (el SASRec «débil» del módulo 09). Frente a un SASRec con **CE completa**, los modelos generativos con semantic IDs suelen quedar **igual o por debajo** en ítems frecuentes — es lo que observan Yang et al. (LIGER, 2024) — y su ventaja aparece en la **cola larga / cold start** y en **memoria**.
- La comparación honesta es parte del oficio: no te quedes con el titular del paper.
""")

# ---------------- HSTU
nb.md(r"""
## ⚡ 6. HSTU mini en MovieLens-1M

HSTU necesita **tiempos** (sesgo relativo temporal), así que lo probamos en MovieLens-1M, el *benchmark* donde el repositorio oficial de Meta reporta (leave-one-out, *full ranking*, abril 2024):

| Modelo (repo `meta-recsys/generative-recommenders`) | HR@10 | NDCG@10 |
|---|---|---|
| SASRec (*sampled softmax*) | 0,2853 | 0,1603 |
| HSTU | 0,3097 | 0,1720 |
| HSTU-large | 0,3294 | 0,1893 |

Entrenamos SASRec y HSTU con **la misma pérdida** (CE completa), mismo $d$, capas y épocas.
""")
nb.code(HSTU)
nb.code(r"""
ml_r, ml_m = load_movielens_1m()
ml_seqs, ml_i2x, ml_x2i = build_sequences(ml_r, min_len=5)
ml_sorted = ml_r[ml_r.item.isin(list(ml_i2x))].sort_values(["user", "ts"], kind="mergesort")
ml_sorted = ml_sorted[ml_sorted.groupby("user")["item"].transform("size") >= 5]
ml_ts = ml_sorted.groupby("user", sort=True)["ts"].apply(list).tolist()          # alineado con ml_seqs
ml_n = len(ml_i2x)
ml_train, ml_valid, ml_test = leave_one_out(ml_seqs)
pair = lambda H, TS: [(h, t) for h, t in zip(H, TS)]
ml_val = (pair(ml_valid[0], [t[:-2] for t in ml_ts]), ml_valid[1])
ml_tst = (pair(ml_test[0], [t[:-1] for t in ml_ts]), ml_test[1])
ml_train_ts = [t[:-2] for t in ml_ts]
MAXLEN = 200
EP = 3 if FAST_DEV_RUN else 100
hstu_res, hstu_models = {}, {}
for name, ctor in [("SASRec (CE)", lambda: SASRec(ml_n, d=64, n_layers=2, n_heads=2, maxlen=MAXLEN)),
                   ("HSTU (CE)", lambda: HSTU(ml_n, d=64, n_layers=2, n_heads=2, maxlen=MAXLEN))]:
    torch.manual_seed(seed); m = ctor()
    train_next_item(m, ml_train, ml_train_ts, ml_val, epochs=EP, maxlen=MAXLEN, eval_every=1 if FAST_DEV_RUN else 10, name=name)
    hstu_res[name] = evaluate_next_item(seq_score_fn(m, MAXLEN), *ml_tst, ks=(10, 20)); hstu_models[name] = m
display(pd.DataFrame(hstu_res).T.round(4))
""")
nb.code(r"""
# 📊 Gráfico 7 — Atención softmax (SASRec) vs pointwise SiLU (HSTU) para el mismo usuario
u = int(np.argmax([len(h) for h in ml_test[0][:300]]))
H_u, T_u = ml_test[0][u][-30:], ml_ts[u][:-1][-30:]
fig, ax = plt.subplots(1, 2, figsize=(14, 5.5))
for a, (name, m) in zip(ax, hstu_models.items()):
    layers = m.blocks if hasattr(m, "blocks") else m.layers
    layers[-1].keep = True; m.eval()
    with torch.no_grad():
        m.encode(pad_left([H_u], len(H_u)).to(device), pad_left([T_u], len(H_u)).to(device))
    A = layers[-1].last_attn[0].mean(0).numpy(); layers[-1].keep = False
    sns.heatmap(A, ax=a, cmap="magma", cbar=True)
    a.set(title=f"{name}: última capa (media de cabezas)\nfilas suman {A.sum(1)[-1]:.2f} en la última posición", xlabel="clave", ylabel="consulta")
plt.tight_layout(); plt.show()
""")
nb.md(r"""
En SASRec cada fila suma **1** (softmax). En HSTU las filas **no** están normalizadas: un historial con muchos ítems relevantes produce una agregación más **intensa**.
Ese es el argumento de Meta para la atención *pointwise*: en recomendación importa *cuánto* engagement hay, no sólo su distribución relativa.

### 6.1 Lo que no implementamos (y hace a HSTU viable a escala)
- **Jagged tensors** + kernels Triton: nada de *padding*; atención sobre secuencias de longitud variable concatenadas.
- **Stochastic Length (SL)**: sub-muestreo de secuencias largas en entrenamiento para recortar el coste $O(n^2)$ manteniendo calidad.
- **M-FALCON**: en *ranking* se puntúan miles de candidatos en una sola pasada, con máscaras que impiden que los candidatos se vean entre sí y reutilizando el KV-cache del historial.
- El paper reporta HSTU **5,3×–15,2× más rápido** que Transformers con FlashAttention2 en secuencias de 8.192 y un modelo de **1,5 billones de parámetros** con **+12,4 %** en la métrica online de A/B.
""")

# ---------------- Scaling
nb.md(r"""
## 📈 7. Scaling laws: un experimento honesto
Entrenamos SASRec con $d \in \{16, 32, 64, 128, 256\}$ (2 capas) sobre MovieLens-1M con el mismo número de épocas y medimos la **pérdida CE de validación** (último ítem) frente al cómputo $C\approx 6N_{\text{no-emb}}T$.
⚠️ ML-1M (1 M de interacciones) es diminuto: esperamos ver **saturación/sobreajuste** en los modelos grandes. Las leyes de potencia de HSTU/Netflix aparecen con **miles de millones** de eventos. Pon `SCALING_DATA="ml-20m"` en A100 para ver más tramo de la curva.
""")
nb.code(r"""
SCALING_DATA = "ml-1m"            # "ml-20m" en A100 (~20 M de interacciones; ~30–40 min)

def load_ml20m(data_dir="data"):
    import zipfile, urllib.request
    z = os.path.join(data_dir, "ml-20m.zip")
    if not os.path.exists(z):
        urllib.request.urlretrieve("https://files.grouplens.org/datasets/movielens/ml-20m.zip", z)
    r = pd.read_csv(zipfile.ZipFile(z).open("ml-20m/ratings.csv")).rename(columns={"userId": "user", "movieId": "item", "timestamp": "ts"})
    return r

sc_seqs = ml_seqs if SCALING_DATA == "ml-1m" else build_sequences(load_ml20m(), min_len=5)[0]
sc_n = ml_n if SCALING_DATA == "ml-1m" else int(max(max(s) for s in sc_seqs))
sc_train, sc_valid, _ = leave_one_out(sc_seqs)
sc_ts = [list(range(len(s))) for s in sc_train]
vs = np.random.default_rng(0).choice(len(sc_valid[0]), min(5000, len(sc_valid[0])), replace=False)
sc_val = ([(sc_valid[0][i], list(range(len(sc_valid[0][i])))) for i in vs], [sc_valid[1][i] for i in vs])

@torch.no_grad()
def val_ce(model, pairs, targets, maxlen=200):
    s = seq_score_fn(model, maxlen)(pairs)
    return F.cross_entropy(s[:, 1:].float(), torch.as_tensor(targets, device=s.device) - 1).item()
""")
nb.code(r"""
scaling = []
dims = [16, 32, 64] if FAST_DEV_RUN else [16, 32, 64, 128, 256]
SC_EP = 2 if FAST_DEV_RUN else 40
tokens_per_epoch = sum(min(len(s) - 1, MAXLEN) for s in sc_train)
for d_ in dims:
    torch.manual_seed(seed)
    m = SASRec(sc_n, d=d_, n_layers=2, n_heads=2, maxlen=MAXLEN, dropout=0.2)
    n_nonemb = sum(p.numel() for n_, p in m.named_parameters() if "item_emb" not in n_)
    train_next_item(m, sc_train, sc_ts, sc_val, epochs=SC_EP, maxlen=MAXLEN, eval_every=SC_EP, name=f"d={d_}")
    r = evaluate_next_item(seq_score_fn(m, MAXLEN), *sc_val, ks=(10,))
    scaling.append({"d": d_, "params_no_emb": n_nonemb, "params_total": sum(p.numel() for p in m.parameters()),
                    "C (FLOPs)": 6 * n_nonemb * tokens_per_epoch * SC_EP, "val_CE": val_ce(m, *sc_val, maxlen=MAXLEN), **r})
sc_df = pd.DataFrame(scaling); display(sc_df)
""")
nb.code(r"""
# 📊 Gráfico 8 — Curvas de escalado (log-log) + ajuste de ley de potencias
fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
x, y = sc_df["C (FLOPs)"].values, sc_df["val_CE"].values
ax[0].loglog(x, y, "o-", lw=2, ms=7)
k_fit = max(2, len(x) - 2)
b, a = np.polyfit(np.log(x[:k_fit]), np.log(y[:k_fit]), 1)
xx = np.logspace(np.log10(x.min()), np.log10(x.max()), 50)
ax[0].loglog(xx, np.exp(a) * xx ** b, "--", c="gray", label=f"ajuste (primeros {k_fit}): L ∝ C^{b:.3f}")
for xi, yi, d_ in zip(x, y, sc_df["d"]): ax[0].annotate(f"d={d_}", (xi, yi), textcoords="offset points", xytext=(5, 5), fontsize=8)
ax[0].set(xlabel="cómputo de entrenamiento C ≈ 6·N_no-emb·T (FLOPs)", ylabel="CE de validación", title=f"Pérdida vs cómputo ({SCALING_DATA})"); ax[0].legend()
ax[1].semilogx(sc_df["params_total"], sc_df["NDCG@10"], "s-", lw=2, c="#10b981")
ax[1].set(xlabel="parámetros totales (incl. embeddings)", ylabel="NDCG@10 (val)", title="Calidad vs tamaño")
plt.tight_layout(); plt.show()
""")
nb.md(r"""
**Cómo interpretarlo.** Si la pendiente se aplana o la pérdida sube para los $d$ grandes, estás **limitado por datos** (*data-constrained*): el modelo memoriza.
Las *scaling laws* de recomendación reportadas en la industria tienen letra pequeña:
- Meta (HSTU): ley de potencias en cómputo durante **3 órdenes de magnitud**; los DLRM clásicos se estancaban.
- Wukong (Meta, 2024): escalado de modelos de interacción de *features* (FM apiladas) durante dos órdenes de magnitud de complejidad.
- Zhang et al. (2023, RecSys 2024): escalado de modelos secuenciales puramente basados en IDs hasta ~0,8 B parámetros.
- Netflix (2026): de 2 M a 1.000 M de parámetros de *backbone*; algunas tareas se acercan a un techo empírico y otras siguen mejorando.
- Con semantic IDs, un estudio de 2025 observó **saturación** al agrandar *encoder*, *tokenizer* y recomendador: el cuello de botella puede estar en el tokenizador.
""")

# ---------------- Producción
nb.md(r"""
## 🏭 8. En producción (2024–2026)

| Empresa | Sistema | Qué hace | Resultado reportado |
|---|---|---|---|
| **Meta** | Generative Recommenders (HSTU) | Sustituye DLRM por un transductor secuencial sobre la historia completa de acciones; retrieval y ranking generativos | Modelos de 1,5 billones (*1.5 trillion*) de parámetros, +12,4 % en la métrica online de A/B, desplegado en varias superficies (ICML 2024) |
| **Kuaishou** | OneRec (V1, feb 2025) | Encoder-decoder con MoE que genera la **sesión** de vídeos completa + alineamiento de preferencias (DPO iterativo) | +1,6 % de watch-time en la escena principal |
| **Kuaishou** | OneRec Technical Report (jun 2025) | Generación *end-to-end* sustituyendo la cascada; RL con recompensas | 25 % del QPS de Kuaishou/Kuaishou Lite; coste operativo ≈ 10,6 % del pipeline tradicional; MFU 23,7 %/28,8 % (train/inferencia) |
| **Kuaishou** | OneRec-V2 (ago 2025) | Arquitectura *lazy decoder-only* (−94 % cómputo), escala a 8 B; RL con feedback real de usuario | +0,467 %/+0,741 % App Stay Time; **caída fuerte de vistas de vídeos cold-start** (trade-off reportado) |
| **Netflix** | *Foundation model* de recomendación (blog, mar 2025) | Un único Transformer autoregresivo sobre interacciones de todos los usuarios; **predicción multi-token**; IDs + metadatos para *cold start*; se consume vía embeddings, como subgrafo o con *fine-tuning* | El blog describe mejoras al escalar datos y parámetros; paper 2026: *backbone* de 2 M → 1 B parámetros, +22,5 % MRR relativo en una tarea en *shadow* |
| **YouTube / Google** | Semantic IDs en ranking (RecSys 2024); **PLUM** (2025) | SIDs en lugar de IDs aleatorios para generalizar en cola larga; PLUM adapta un LLM pre-entrenado (tokenización SID-v2, pre-entrenamiento continuo, *fine-tuning*) | PLUM en producción para retrieval de vídeos largos y Shorts |
| **Pinterest** | PinRec (2025) | Generative retrieval **condicionado al resultado** (pesos de guardar/clicar) y generación multi-token para diversidad | Ganancias online en clics y *repins* |

**Trade-offs que hay que poner sobre la mesa.**
- **Latencia de decodificación**: beam search = $L$ pasos secuenciales × *beam*. Se mitiga con KV-cache, multi-token prediction (Netflix, PinRec) y *batching* agresivo.
- **Catálogo dinámico**: los ítems nuevos necesitan un SID (inferencia del tokenizador) y el trie se actualiza; si reentrenas el tokenizador, **todos los IDs cambian**.
- **Coste**: OneRec demostró que *con buen MFU* el coste puede bajar frente a la cascada; sin esa ingeniería, un generativo es más caro que un two-tower + ANN.
""")
nb.md(r"""
## 🧠 9. Secretos de la élite
1. **El tokenizador es el modelo.** La calidad de los semantic IDs (colisiones, uso del *codebook*, alineamiento con el comportamiento) limita todo lo demás. Inicializa con k-means, reinicia códigos muertos y mide pureza; RQ-KMeans (OneRec) es un *baseline* durísimo de batir. PLUM (SID-v2) y OneRec mezclan **señal colaborativa** en el tokenizador, no sólo texto.
2. **Siempre *constrained decoding*.** Sin trie, parte del *beam* se gasta en IDs que no existen y el Recall@K cae; además, el trie permite aplicar **filtros de negocio** (disponibilidad, país, edad) *durante* la decodificación, no después.
3. **El *beam* acota tu Recall@K**: con beam=20 no puedes medir Recall@50. Y un beam grande multiplica la latencia. Evalúa siempre con el mismo protocolo de *full ranking* que tu *baseline* discriminativo.
4. **SIDs + IDs, no SIDs en vez de IDs.** Singh et al. (RecSys 2024) muestran que los SIDs generalizan en la cola larga pero pierden capacidad de **memorización** frente a IDs aleatorios en ítems populares; combinarlos (o *SentencePiece* sobre SIDs) recupera lo mejor de ambos. LIGER (2024) hace híbrido generativo + denso por la misma razón.
5. **La ganancia de HSTU no es sólo la arquitectura**: es reformular el problema (historia completa de acciones como secuencia, mismo modelo para retrieval y ranking, *features* de tiempo) y la ingeniería de kernels que permite escalar. Un HSTU pequeño en ML-1M sólo gana unos puntos.
6. **Las *scaling laws* requieren datos frescos y muchos**: con un dataset fijo, agrandar el modelo sobreajusta. En producción el «dato infinito» existe (streams de eventos), pero obliga a reentrenos frecuentes: Netflix señala el coste de entrenamiento/decodificación por reentreno y la **obsolescencia** de predicciones cacheadas.
7. **Alinear con RL/preferencias cambia la distribución de exposición.** OneRec-V2 reporta mejoras de engagement acompañadas de una caída fuerte de las vistas de contenido *cold-start*: vigila métricas de ecosistema (módulo 13) cuando optimices recompensas.
8. **Multi-token prediction** (Netflix) no es sólo eficiencia: evita la miopía de predecir sólo el siguiente evento y se alinea mejor con objetivos de largo plazo — la misma idea del *dense all-action loss* de PinnerFormer (módulo 09).
""")
nb.md(r"""
## ⚠️ 10. Errores comunes
- Entrenar el tokenizador con ítems de **test** o con información del futuro (p. ej., señales colaborativas calculadas sobre todo el periodo).
- Olvidar el **token de desambiguación**: dos ítems con el mismo SID son indistinguibles y el Recall se calcula mal.
- Comparar TIGER con un SASRec-BCE de 1 negativo y concluir que «lo generativo gana»: compáralo con SASRec-CE (módulo 09).
- Usar el mismo rango de tokens para todos los niveles (sin *offsets*): el modelo confunde el código 5 del nivel 1 con el del nivel 3.
- Medir *scaling laws* con un solo dataset pequeño y extrapolar a producción.
- Reentrenar el RQ-VAE y servir con el trie antiguo (IDs desalineados): versiona tokenizador, trie y modelo **juntos** (módulo 17).
- En HSTU, aplicar softmax «por costumbre» o no enmascarar el padding a cero (sin softmax, $-\infty$ no sirve: hay que multiplicar por la máscara).
""")
nb.md(r"""
## ✅ 11. Autoevaluación
1. ¿Por qué el residuo $\mathbf r_{l+1} = \mathbf r_l - \mathbf e_{c_l}$ hace que los semantic IDs sean jerárquicos?
<details><summary>Respuesta</summary>El primer código captura la mayor parte de la varianza (lo grueso), y cada nivel sólo codifica lo que queda sin explicar. Ítems con el mismo c₁ están cerca en el espacio latente; compartir (c₁, c₂) implica aún más cercanía. Por eso el trie agrupa ítems semánticamente.</details>

2. ¿Para qué sirve el *straight-through estimator* en el RQ-VAE?
<details><summary>Respuesta</summary>El argmin de la cuantización no es derivable. El STE usa el valor cuantizado en el forward pero copia el gradiente del decoder directamente a z (ẑ_st = z + sg[ẑ − z]), permitiendo entrenar el encoder con la pérdida de reconstrucción.</details>

3. Con $L=3$ niveles y $K=256$, ¿cuántos IDs distintos pueden representarse? ¿Y cuál es el tamaño del vocabulario de salida?
<details><summary>Respuesta</summary>256³ ≈ 16,8 millones de tuplas; el vocabulario de salida es sólo 3·256 = 768 tokens (más el token de desambiguación). La softmax por paso es diminuta comparada con N.</details>

4. ¿Qué dos diferencias clave tiene la atención de HSTU respecto a la de SASRec?
<details><summary>Respuesta</summary>(1) Sustituye la softmax por SiLU pointwise (sin normalizar por fila), preservando la intensidad de las preferencias; (2) añade sesgos relativos de posición y tiempo y una puerta U(X) que modula la salida (Norm(AV) ⊙ U).</details>

5. ¿Qué es *constrained decoding* y qué problema de negocio adicional resuelve?
<details><summary>Respuesta</summary>Restringir en cada paso del beam search los tokens a los hijos válidos del prefijo en un trie de IDs existentes. Evita IDs inexistentes y permite filtrar en la propia decodificación (sólo ítems disponibles en el país, aptos por edad, en stock...).</details>

6. Tu curva pérdida–cómputo se aplana con $d=256$ en ML-1M. ¿Contradice las *scaling laws*?
<details><summary>Respuesta</summary>No: las scaling laws asumen datos suficientes (o crecientes con el modelo). Con 1 M de interacciones el modelo grande está limitado por datos y sobreajusta. Hace falta escalar datos y cómputo a la vez.</details>

7. Nombra dos razones por las que una empresa podría preferir seguir con two-tower + ANN.
<details><summary>Respuesta</summary>Latencia/coste de decodificación autoregresiva frente a un único producto escalar + ANN; catálogos muy dinámicos (re-tokenizar e invalidar tries); madurez del stack; en ítems populares un modelo con IDs y CE completa puede ser igual o mejor; menos riesgo operativo.</details>
""")
nb.md(r"""
## 📚 12. Referencias
**Generative retrieval y semantic IDs**
- Rajput et al. (2023). *Recommender Systems with Generative Retrieval* (TIGER). NeurIPS. https://arxiv.org/abs/2305.05065
- Lee et al. (2022). *Autoregressive Image Generation using Residual Quantization* (RQ-VAE). CVPR. https://arxiv.org/abs/2203.01941
- Singh et al. (2024). *Better Generalization with Semantic IDs: A Case Study in Ranking for Recommendations*. RecSys. https://arxiv.org/abs/2306.08121
- Yang et al. (2024). *Unifying Generative and Dense Retrieval for Sequential Recommendation* (LIGER). https://arxiv.org/abs/2411.18814
- Hou et al. (2025). *ActionPiece: Contextually Tokenizing Action Sequences for Generative Recommendation*. ICML. https://arxiv.org/abs/2502.13581
- Ju et al. (2025). *Generative Recommendation with Semantic IDs: A Practitioner's Handbook* (GRID, Snap). CIKM. https://arxiv.org/abs/2507.22224
- He et al. (2025). *PLUM: Adapting Pre-trained Language Models for Industrial-scale Generative Recommendations* (YouTube). https://arxiv.org/abs/2510.07784
- Badrinath, Agarwal et al. (2025). *PinRec: Outcome-Conditioned, Multi-Token Generative Retrieval for Industry-Scale Recommendation Systems* (Pinterest). https://arxiv.org/abs/2504.10507

**Generative Recommenders, OneRec y foundation models**
- Zhai et al. (2024). *Actions Speak Louder than Words: Trillion-Parameter Sequential Transducers for Generative Recommendations* (HSTU). ICML. https://arxiv.org/abs/2402.17152 — código: https://github.com/meta-recsys/generative-recommenders
- Deng et al. (2025). *OneRec: Unifying Retrieve and Rank with Generative Recommender and Iterative Preference Alignment*. https://arxiv.org/abs/2502.18965
- OneRec Team (2025). *OneRec Technical Report*. https://arxiv.org/abs/2506.13695
- OneRec Team (2025). *OneRec-V2 Technical Report*. https://arxiv.org/abs/2508.20900
- Hsiao, Feng & Lamkhede (2025, marzo). *Foundation Model for Personalized Recommendation*. Netflix Tech Blog — https://netflixtechblog.com (busca el título)
- Xu, Hsiao & Bhattacharya (2026). *Towards Generalizable and Efficient Large-Scale Generative Recommenders* (Netflix). https://arxiv.org/abs/2605.23312

**Scaling laws**
- Zhang et al. (2023). *Scaling Law of Large Sequential Recommendation Models*. RecSys 2024. https://arxiv.org/abs/2311.11351
- Zhang et al. (2024). *Wukong: Towards a Scaling Law for Large-Scale Recommendation*. ICML. https://arxiv.org/abs/2403.02545
- Kaplan et al. (2020). *Scaling Laws for Neural Language Models*. https://arxiv.org/abs/2001.08361

**Datos y herramientas**
- Hou et al. (2024). *Bridging Language and Items for Retrieval and Recommendation* (Amazon Reviews 2023, BLaIR). https://arxiv.org/abs/2403.03952 — https://amazon-reviews-2023.github.io/ — HF: `McAuley-Lab/Amazon-Reviews-2023`
- Sentence-T5: Ni et al. (2022). *Sentence-T5: Scalable Sentence Encoders from Pre-trained Text-to-Text Models*. https://arxiv.org/abs/2108.08877
- RecTools (incluye HSTU): https://github.com/MobileTeleSystems/RecTools
""")
nb.save(LESSON)

# ---------------------------------------------------------------------------
# PROYECTO
# ---------------------------------------------------------------------------
pj = Notebook("Proyecto 11 · Semantic IDs + retrieval generativo", colab_path=PROJECT, gpu=True)
pj.md(f"""
{pj.badge()}

# Proyecto 11 · Semantic IDs (RQ-VAE) + un pequeño modelo generativo de *retrieval*

| | |
|---|---|
| **Nivel** | 🔴 Experto |
| **Duración** | 4 h |
| **GPU** | A100 recomendada (L4 con menos épocas) |
| **Unidades Colab** | ≈ 5–8 (A100) |
| **Prerrequisitos** | Lección 11 |
""")
pj.md(r"""
## 🏢 Contexto de negocio
CineMatch va a lanzar una **tienda de videojuegos y merchandising** dentro de la app. El catálogo cambia cada semana (≈ 25 k productos, cientos de altas semanales) y el
two-tower actual sufre con los productos nuevos (no tienen fila en la tabla de embeddings). El equipo de investigación propone un piloto de **generative retrieval con semantic IDs**:
los productos nuevos reciben un ID a partir de su **texto**, sin reentrenar el recomendador.

Tu misión: construir el tokenizador (RQ-VAE → semantic IDs), el modelo generativo (encoder-decoder) con decodificación restringida, y una comparación honesta con popularidad y con SASRec.

## 📦 Dataset
**Amazon Reviews 2023** (McAuley Lab), categoría `Video_Games`, *benchmark* 5-core (`McAuley-Lab/Amazon-Reviews-2023` en Hugging Face) + metadatos de producto.
Protocolo *leave-one-out*. Fallback automático a MovieLens-1M si no hay acceso a Hugging Face.

## ✅ Entregables y rúbrica
| Criterio | Objetivo |
|---|---|
| RQ-VAE: uso del codebook de nivel 1 | ≥ 90 % de los 256 códigos usados |
| Colisiones antes del token de desambiguación | < 15 % de los ítems |
| Pureza de categoría de nivel 1 | claramente > asignación aleatoria |
| Beam search con trie | 0 % de IDs inválidos |
| Recall@10 del modelo generativo en test | ≥ 2× popularidad; reporta la distancia a SASRec y analiza por popularidad del ítem |
| Experimento de *cold start* (reto guiado) | Recall@10 sobre ítems retirados del entrenamiento > 0 |
""")
pj.code(PIP)
pj.code(IMPORTS)
pj.md(UTILS_MD)
pj.code(UTILS_LOAD)
pj.code(UTILS_SEQ)
pj.code(UTILS_EVAL)
pj.code(DATA_GEN)
pj.code(EMBED)
pj.md(r"""
## Paso 1 · Cuantización residual
Completa `quantize`: para cada *codebook*, código más cercano al residuo, pérdida de codebook + β·commitment, acumula $\hat z$ y actualiza el residuo.
El resto del RQ-VAE (encoder/decoder, STE, k-means) está dado.
""")
pj.code(r"""
def kmeans_torch(x, K, iters=25, seed=seed):
    g = torch.Generator(device=x.device).manual_seed(seed)
    idx = torch.randperm(len(x), generator=g, device=x.device)[:K] if len(x) >= K else torch.randint(len(x), (K,), generator=g, device=x.device)
    C = x[idx].clone()
    for _ in range(iters):
        a = torch.cdist(x, C).argmin(1)
        S = torch.zeros_like(C).index_add_(0, a, x); cnt = torch.bincount(a, minlength=K).float()
        C = torch.where((cnt == 0)[:, None], x[torch.randint(len(x), (K,), generator=g, device=x.device)], S / cnt.clamp(min=1)[:, None])
    return C, torch.cdist(x, C).argmin(1)

class RQVAE(nn.Module):
    def __init__(self, in_dim, latent=32, hidden=(512, 256, 128), levels=3, K=256, beta=0.25):
        super().__init__()
        dims, enc, dec = [in_dim, *hidden], [], []
        for a, b in zip(dims[:-1], dims[1:]): enc += [nn.Linear(a, b), nn.ReLU()]
        self.encoder = nn.Sequential(*enc, nn.Linear(dims[-1], latent))
        rd = [latent, *dims[::-1]]
        for a, b in zip(rd[:-1], rd[1:]): dec += [nn.Linear(a, b), nn.ReLU()]
        self.decoder = nn.Sequential(*dec[:-1])
        self.codebooks = nn.ParameterList([nn.Parameter(0.1 * torch.randn(K, latent)) for _ in range(levels)])
        self.K, self.L, self.beta = K, levels, beta

    def quantize(self, z):
        # TODO: devuelve (z_hat [B,d], codes [B,L], cb_loss escalar)
        raise NotImplementedError

    def forward(self, x):
        z = self.encoder(x); z_hat, codes, cb = self.quantize(z)
        x_hat = self.decoder(z + (z_hat - z).detach())
        return x_hat, codes, ((x_hat - x) ** 2).sum(1).mean(), cb

    @torch.no_grad()
    def init_codebooks(self, x):
        r = self.encoder(x)
        for C in self.codebooks:
            cent, a = kmeans_torch(r, self.K); C.data.copy_(cent); r = r - cent[a]

    @torch.no_grad()
    def get_codes(self, x, batch=8192):
        return torch.cat([self.quantize(self.encoder(x[b:b + batch]))[1] for b in range(0, len(x), batch)])
""")
pj.md(r"""
## Paso 2 · Entrenar el tokenizador y diagnosticarlo
Escribe el bucle de entrenamiento (Adam, *batches* de 1024, ~300–400 épocas en GPU), con **reinicio de códigos muertos** cada 20 épocas, y reporta: uso por nivel, % de colisiones y pureza de categoría del nivel 1 vs aleatorio.
""")
pj.code(r"""
def train_rqvae(X, K=256, levels=3, latent=32, epochs=300, lr=1e-3, batch=1024, reset_every=20, log_every=25):
    # TODO: devuelve (modelo, historial)
    raise NotImplementedError
""")
pj.md(r"""
## Paso 3 · IDs únicos y trie
1. Añade el token de desambiguación. 2. Implementa `allowed_mask(prefixes, level, size)` del trie (puedes empezar con la versión de diccionario y luego vectorizarla).
""")
pj.code(r"""
def add_dedup_token(codes):
    # TODO
    raise NotImplementedError

class SemanticIDTrie:
    def __init__(self, codes):
        # TODO: estructura que permita (a) hijos válidos de un prefijo y (b) traducir un ID completo a índice de ítem
        raise NotImplementedError
    def allowed_mask(self, prefixes, level, size):
        raise NotImplementedError
    def lookup(self, codes):
        raise NotImplementedError
""")
pj.md(r"""
## Paso 4 · Modelo generativo y beam search restringido
Se da la clase `TigerMini` (lección). Implementa `beam_search` con el trie y el bucle de entrenamiento; evalúa Recall@10/NDCG@10 con beam = 20.
""")
pj.code(TIGER)
pj.code(r"""
@torch.no_grad()
def beam_search(model, src, trie, beam=20, constrained=True):
    # TODO: devuelve (codes [B, beam, L], scores [B, beam])
    raise NotImplementedError
""")
pj.md(r"""
## Paso 5 · *Cold start* (reto guiado)
Retira del entrenamiento del modelo generativo el 5 % de los ítems (todas sus apariciones como objetivo **y** en historiales), pero mantenlos en el tokenizador y en el trie.
Mide el Recall@10 en los usuarios de test cuyo objetivo es uno de esos ítems. Un modelo con IDs aleatorios (SASRec) tendría Recall@10 = 0 en ellos.
""")
pj.code(r"""
# TODO: experimento de cold start
...
""")

pj.md(r"""
---
# ⛔ SPOILER — Solución de referencia
""")
pj.code(RQVAE)
pj.code(RQVAE_TRAIN)
pj.code(TRIE)
pj.code(TIGER_DATA)
pj.code(BEAM)
pj.code(r"""
CODEBOOK_SIZE = 256
torch.manual_seed(seed)
rqvae, rq_hist = train_rqvae(X_items, K=CODEBOOK_SIZE, epochs=30 if FAST_DEV_RUN else 400, log_every=10 if FAST_DEV_RUN else 50)
codes3 = rqvae.get_codes(torch.from_numpy(X_items).to(device)).cpu().numpy()
cats = item_cat[1:]
def purity(c1, cats, min_size=5):
    g = pd.DataFrame({"c": c1, "cat": cats}).groupby("c")["cat"].agg(lambda s: s.value_counts(normalize=True).iloc[0] if len(s) >= min_size else np.nan)
    return g.dropna().values
print(f"uso nivel 1: {len(np.unique(codes3[:, 0])) / CODEBOOK_SIZE:.1%} | colisiones: {collision_rate(codes3):.2%} | "
      f"pureza: {purity(codes3[:, 0], cats).mean():.3f} vs aleatorio {purity(np.random.default_rng(0).permutation(codes3[:, 0]), cats).mean():.3f}")
sid_codes = add_dedup_token(codes3)
item_tokens, level_sizes, offsets, VOCAB = build_token_tables(sid_codes, CODEBOOK_SIZE)
trie = SemanticIDTrie(sid_codes)
""")
pj.code(r"""
# Cold start: retiramos el 5 % de los ítems del entrenamiento del modelo generativo
H_HIST = 20
rng = np.random.default_rng(seed)
cold = set(rng.choice(np.arange(1, gn_items + 1), max(1, gn_items // 20), replace=False).tolist())
warm_train = [[i for i in s if i not in cold] for s in g_train]
tr_hist, tr_tgt = gen_examples(warm_train, H=H_HIST, max_examples=50_000 if FAST_DEV_RUN else 2_000_000)
torch.manual_seed(seed)
tiger = TigerMini(VOCAB, level_sizes, offsets, d=128, nhead=4, n_layers=4, ff=1024, dropout=0.1, max_src=H_HIST * 4)
vsel = rng.choice(len(g_valid[0]), min(2000, len(g_valid[0])), replace=False)
val_small = ([g_valid[0][i] for i in vsel], [g_valid[1][i] for i in vsel])
log = train_tiger(tiger, tr_hist, tr_tgt, item_tokens, epochs=2 if FAST_DEV_RUN else 20, batch_size=512, lr=5e-4, H=H_HIST,
                  eval_fn=lambda m: eval_generative(m, *val_small, trie, item_tokens, beam=10, ks=(10,), H=H_HIST))
""")
pj.code(r"""
N_EVAL = min(len(g_test[0]), 1000 if FAST_DEV_RUN else 20000)
sel = rng.choice(len(g_test[0]), N_EVAL, replace=False)
tH, tT = [g_test[0][i] for i in sel], [g_test[1][i] for i in sel]
res = {"TIGER-mini (trie)": eval_generative(tiger, tH, tT, trie, item_tokens, beam=20, H=H_HIST),
       "TIGER-mini (sin trie)": eval_generative(tiger, tH, tT, trie, item_tokens, beam=20, H=H_HIST, constrained=False)}
popg = np.bincount(np.concatenate(g_train), minlength=gn_items + 1).astype(np.float32)
res["Popularidad"] = {k.replace("HR@", "Recall@"): v for k, v in
                      evaluate_next_item(lambda H: torch.from_numpy(np.tile(popg, (len(H), 1))), tH, tT, ks=(10, 20)).items()}
cold_idx = [k for k, t in enumerate(g_test[1]) if t in cold]
if cold_idx:
    res["TIGER-mini · sólo objetivos cold"] = eval_generative(tiger, [g_test[0][k] for k in cold_idx], [g_test[1][k] for k in cold_idx],
                                                              trie, item_tokens, beam=20, H=H_HIST)
display(pd.DataFrame(res).T.round(4))
fig, ax = plt.subplots(1, 2, figsize=(12, 3.8))
ax[0].plot(log["epoch"], log["loss"], "o-"); ax[0].set(title="Pérdida TIGER-mini", xlabel="época")
pd.DataFrame(res).T["Recall@10"].plot.barh(ax=ax[1], color="#6366f1"); ax[1].set(title="Recall@10 (test)")
plt.tight_layout(); plt.show()
""")
pj.md(r"""
**Lectura esperada.** El trie lleva los IDs inválidos a 0 %. El Recall@10 generativo debería superar con holgura a popularidad; frente a SASRec-CE (lección) puede quedar por debajo en ítems populares.
Lo interesante para negocio es la fila *cold*: los ítems que el generador **nunca vio como objetivo** siguen siendo recuperables porque su SID comparte prefijos con ítems parecidos
— algo imposible para un modelo con tabla de IDs.

## 🚀 Retos extra (nivel experto)
1. **RQ-KMeans vs RQ-VAE** como tokenizador del mismo modelo: ¿qué tokenizador da mejor Recall@10 y mejor *cold start*?
2. **Señal colaborativa en el tokenizador**: concatena al embedding de texto el embedding de ítem de un SASRec/MF entrenado (normalizado) antes del RQ-VAE (idea de SID-v2/OneRec). ¿Mejora la pureza *conductual*?
3. **Token de usuario** (TIGER hashea el ID de usuario en 2.000 tokens) y **features de contexto** en el encoder.
4. **Híbrido LIGER**: usa los top-50 del beam como candidatos y re-puntúalos con el producto escalar de SASRec.
5. **Filtro de negocio en el trie**: excluye en decodificación los productos «sin stock» (máscara aleatoria del 20 %) y compara con filtrar *después* del beam.
6. **Escala**: `Books` o `Clothing_Shoes_and_Jewelry` (cientos de miles de ítems) en A100: ¿cómo crecen colisiones, tamaño del trie y latencia del beam?

## 🤔 Reflexión (producción / MLOps)
- Si reentrenas el RQ-VAE cada mes, todos los SIDs cambian: ¿cómo versionas tokenizador + trie + modelo y haces *rollback* (módulo 17)?
- ¿Qué latencia p99 tiene tu beam search para beam = 20 y cómo la reducirías (KV-cache, multi-token, *distillation* a two-tower)?
- ¿Qué métricas de ecosistema vigilarías al desplegar (exposición de productos nuevos, diversidad, módulo 13)?
""")
pj.save(PROJECT)
