"""Proyecto 17 · SAE sobre embeddings de Políglota y análisis de features interpretables."""
from _a6_common import SYNTH_DATA_SRC, CORPUS_SRC, REAL_SRC
from _a6_src15 import RETRIEVERS_SRC
from _a6_src17 import SAE_SRC, PROBE_SRC

# Medido por la solución de referencia (FAST_DEV_RUN=True, corpus sintético 12 temas x 40 docs/faceta, semilla 42)
REF = {"nmse": 0.045, "activos": 80, "pureza_sae": 0.83, "pureza_pca": 0.72, "estables": 0.46, "git_a0": 0.0, "git_a2": 1.0}

ENCODE_REF = '''    def encode(self, x, k=None):
        pre = self.pre(x); v, i = pre.topk(k or self.k, dim=-1)
        return torch.zeros_like(pre).scatter(-1, i, F.relu(v)), pre'''
ENCODE_STUB = '''    def encode(self, x, k=None):
        """x: (B, d) -> (z, pre). z: (B, n_lat) dispersa con SOLO k valores no nulos (>= 0) por fila; pre: preactivaciones (B, n_lat)."""
        pre = self.pre(x)
        # TODO 1: quédate con las k mayores preactivaciones de cada fila (torch.topk), aplica ReLU a esos valores y
        #         colócalos en un tensor de ceros con scatter. Devuelve (z, pre).
        raise NotImplementedError("TODO 1: TopKSAE.encode")'''


def _hint(a, b):
    return f"""
    <details><summary>🪜 Pista 1 (la idea)</summary>

    {a}
    </details>

    <details><summary>🪜 Pista 2 (casi la API)</summary>

    {b}
    </details>
    """


def build(nb):
    assert ENCODE_REF in SAE_SRC
    nb.md(f"""
    {nb.badge()}

    # Proyecto 17 · SAE sobre embeddings de Políglota

    | | |
    |---|---|
    | **Nivel** | 🔴 Experto |
    | **Duración estimada** | ≈ 2 h |
    | **GPU recomendada** | No necesaria (CPU, ≈ 3–4 min con `FAST_DEV_RUN=True`) |
    | **Prerrequisitos** | Lección 17 (SAE TopK, pureza, estabilidad, steering, inversión) y módulo 15 (estadística) |
    | **Conecta con** | 12 (embedders) · 15 (evaluación) · 18 (privacidad y producción) |

    ## 🏢 Contexto de negocio
    Eres ML engineer en **Políglota Labs**. Soporte pregunta *«¿por qué el buscador cree que estos dos documentos se parecen?»* y Seguridad pregunta *«¿qué se puede reconstruir de los vectores que guardamos?»*. Tu entregable es un **informe de interpretabilidad** sobre los embeddings de Políglota: un **TopK SAE** que descompone cada vector en pocas *features* legibles, con métricas de calidad (reconstrucción, pureza, estabilidad entre semillas), una prueba de **steering** frente a una línea base y una **auditoría de filtración** del embedding.

    ## 📦 Dataset
    Corpus Políglota (`carga_corpus`). Un SAE necesita **miles** de vectores: si el corpus es sintético usamos el generador (12 temas × 36 facetas, ≈ 2 900 docs ES/EN, con etiquetas de faceta/tema/idioma como **verdad terreno**); con datos reales (`source == "real"`) se usa `carga_corpus(fast_dev=False)` y solo el idioma como etiqueta (las métricas de pureza por faceta no aplican).
    Embedder: **LSI-64** (TF-IDF + SVD) por defecto, reproducible en CPU. En Colab puedes sustituirlo por uno real (reto extra).

    ## 🎯 Entregables y criterios
    | # | Entregable | Criterio objetivo |
    |---|---|---|
    | 1 | `TopKSAE.encode` (TODO 1) | Exactamente `k` no nulos por fila, valores ≥ 0, test de igualdad con `topk` |
    | 2 | SAE entrenado | NMSE ≤ 0.07 con L0 = 4 y ≥ 60 latentes activos (de 96) |
    | 3 | `pureza_features` (TODO 2) | Pasa el test; pureza media del SAE ≥ 0.75 y > PCA |
    | 4 | `estabilidad` entre 2 semillas (TODO 3) | Fracción de átomos con cos > 0.9 calculada y reportada (≈ valor de referencia) |
    | 5 | `curva_steering` (TODO 4) | α=0 → ≈ 0 % «git»; α alto → ≥ 90 %; comparación con diferencia de medias |
    | 6 | Auditoría de inversión (TODO 5) | Precisión@10 de términos recuperados sin ruido ≥ 0.8; trade-off con ruido |
    | 7 | Informe con recomendaciones | Cita pureza, estabilidad, baseline y riesgo de privacidad |
    """)
    nb.md("## 0. Preparación (celdas dadas)")
    nb.code("!pip install -q numpy scipy scikit-learn matplotlib pandas torch datasets")
    nb.code(r'''
    import os, re, math, random, time, warnings
    import numpy as np, pandas as pd
    import matplotlib.pyplot as plt
    warnings.filterwarnings("ignore")
    SEED, FAST_DEV_RUN = 42, True
    random.seed(SEED); np.random.seed(SEED)
    import torch
    torch.manual_seed(SEED)
    if FAST_DEV_RUN: torch.set_num_threads(1)
    AZUL, NARANJA, VERDE, GRIS, ROJO = "#1F6FEB", "#F28E2B", "#2CA02C", "#6B7280", "#D62728"
    plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25})
    ''')
    nb.md("Utilidades del corpus Políglota (`carga_corpus`: oficial → espejo → sintético; copia autocontenida del contrato común) y retrievers de CPU.")
    nb.code(SYNTH_DATA_SRC); nb.code(CORPUS_SRC); nb.code(REAL_SRC); nb.code(RETRIEVERS_SRC)
    nb.code(r'''
    corpus = carga_corpus(fast_dev=FAST_DEV_RUN)
    if corpus["source"] == "synthetic":
        corpus = genera_sintetico(n_temas=12, docs_por_faceta=40, seed=SEED)       # un SAE necesita miles de vectores (documentado)
    elif FAST_DEV_RUN:
        corpus = carga_corpus(fast_dev=False)
    docs = [d for d in corpus["docs"] if d["lang"] != "code"]; txt = [d["text"] for d in docs]; ids = [d["id"] for d in docs]
    lang = np.array([d["lang"] for d in docs]); sint = corpus["source"] == "synthetic"
    facet = np.array([d["id"].split("-", 1)[1].rsplit("-", 1)[0] for d in docs]) if sint else lang.copy()
    topic = np.array([f.split(".")[0] for f in facet]) if sint else lang.copy()
    fac_id = np.unique(facet, return_inverse=True)[1]
    lsi = LSI(64, SEED).fit(txt, ids); E = lsi.Z.astype(np.float32)
    print(f"fuente={corpus['source']} · {len(docs)} docs · {len(set(facet))} etiquetas de pureza · embeddings {E.shape}")
    ''')
    nb.md("""
    ## 1. TopK SAE: la activación (TODO 1)
    Te damos la clase `TopKSAE`, el entrenamiento (con inicialización *tied*, decoder normalizado y AuxK) y las utilidades. Falta lo esencial: la **activación TopK** en `encode`. Dado $x$, calcula las preactivaciones $\\mathrm{pre}=W_{enc}(x-b_{dec})+b_{enc}$ (ya está en `self.pre`), conserva **solo las $k$ mayores por fila**, aplica ReLU a esos valores y devuelve `z` (con ceros en el resto) y `pre`.
    """)
    nb.md(_hint("`torch.topk(pre, k, dim=-1)` devuelve valores e índices. Crea `z` de ceros y coloca los valores en esos índices (`scatter`). El ReLU va sobre los valores seleccionados.",
                "`v, i = pre.topk(k or self.k, dim=-1)`; `z = torch.zeros_like(pre).scatter(-1, i, F.relu(v))`; `return z, pre`."))
    nb.code(SAE_SRC.replace(ENCODE_REF, ENCODE_STUB))
    nb.code(r'''
    def test_encode():
        torch.manual_seed(0); s = TopKSAE(8, 20, 3); x = torch.randn(5, 8); z, pre = s.encode(x)
        assert z.shape == (5, 20) and pre.shape == (5, 20) and (z >= 0).all(), "formas / no negatividad"
        assert ((z > 0).sum(1) <= 3).all() and (z > 0).sum() > 0, "como mucho k no nulos por fila"
        v, i = pre.topk(3, dim=-1); assert torch.allclose(z.gather(1, i), F.relu(v)), "los no nulos son los top-k (con ReLU)"
        z2, _ = s.encode(x, k=1); assert ((z2 > 0).sum(1) <= 1).all(), "el argumento k sobreescribe self.k"
        return "✅ test_encode OK"
    def corre(f):
        try: print(f())
        except NotImplementedError as e: print(f"⏳ pendiente: {e}")
        except AssertionError as e: print(f"❌ falló: {e}")
        except Exception as e: print(f"❌ {type(e).__name__}: {e}")
    corre(test_encode)
    ''')
    nb.code(r'''
    pasos = 1500 if FAST_DEV_RUN else 4000
    try:
        t0 = time.time(); sae, hist = entrena_topk(E, n_lat=96, k=4, pasos=pasos, auxk=True, seed=0); Z, Xh = codifica(sae, E); Z = Z.numpy()
        activos = (Z > 0).sum(0) >= 10; RES = {"nmse": nmse(E, Xh), "activos": int(activos.sum()), "l0": float((Z > 0).sum(1).mean())}
        print(f"entrenado en {time.time()-t0:.0f}s · NMSE={RES['nmse']:.3f} · L0={RES['l0']:.1f} · latentes activos {RES['activos']}/96")
    except NotImplementedError as e:
        sae = Z = activos = None; RES = {}; print("⏳ pendiente:", e)
    ''')

    nb.md("""
    ## 2. ¿Son interpretables las features? Pureza (TODO 2)
    **Pureza** de una *feature* = fracción de sus **`top` documentos más activos** (por defecto 20) que comparten la **misma etiqueta** (faceta). Implementa `pureza_features(Z, etiquetas, top=20)` que devuelva un vector con la pureza de cada columna de `Z` (n_docs × n_features). Compararemos con las direcciones de **PCA** y los centroides de **k-means**.
    """)
    nb.md(_hint("Para cada columna: índices de los `top` mayores valores (`np.argsort(-col)[:top]`), cuenta etiquetas con `np.bincount` y divide el máximo por `top`.",
                "`np.array([np.bincount(etiquetas[np.argsort(-Z[:, j])[:top]]).max() / top for j in range(Z.shape[1])])` (etiquetas = enteros)."))
    nb.code(r'''
    def pureza_features(Z: np.ndarray, etiquetas: np.ndarray, top: int = 20) -> np.ndarray:
        # TODO 2
        raise NotImplementedError("TODO 2: pureza_features")

    def test_pureza():
        Z = np.zeros((6, 2)); Z[:3, 0] = [3, 2, 1]; Z[3:, 1] = [3, 2, 1]; et = np.array([0, 0, 0, 1, 1, 0])
        p = pureza_features(Z, et, top=3); assert np.allclose(p, [1.0, 2 / 3]), f"pureza esperada [1, 2/3], obtenida {p}"
        return "✅ test_pureza OK"
    corre(test_pureza)
    ''')
    nb.code(r'''
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    try:
        cols = np.where(activos)[0]; P = {"SAE TopK": pureza_features(Z[:, cols], fac_id)}
        n_f = len(cols); km = KMeans(n_f, n_init=3, random_state=0).fit(E); Ck = km.cluster_centers_
        P["k-means"] = pureza_features(E @ Ck.T / (np.linalg.norm(Ck, axis=1) + 1e-9), fac_id)
        pc = PCA(min(n_f, 64)).fit(E); P["PCA"] = pureza_features(np.abs((E - pc.mean_) @ pc.components_.T), fac_id)
        RES.update({"pureza_sae": float(P["SAE TopK"].mean()), "pureza_pca": float(P["PCA"].mean()), "pureza_km": float(P["k-means"].mean())})
        print({k: round(float(v.mean()), 3) for k, v in P.items()})
    except (NotImplementedError, ValueError, TypeError, AttributeError, NameError) as e:
        print("⏳ pendiente (TODOs 1–2):", type(e).__name__)
    ''')

    nb.md("""
    ## 3. Estabilidad entre semillas (TODO 3)
    Entrena un segundo SAE con otra semilla. Implementa `estabilidad(W_a, W_b, umbral=0.9)`: para cada átomo de `W_a` (filas normalizadas, forma `(n_a, d)`) calcula el **coseno absoluto máximo** con los átomos de `W_b` y devuelve la **fracción con coseno > umbral**.
    """)
    nb.md(_hint("Matriz de cosenos `W_a @ W_b.T` (átomos unitarios), valor absoluto, máximo por fila, y media de `> umbral`.",
                "`C = np.abs(W_a @ W_b.T); return float((C.max(axis=1) > umbral).mean())`."))
    nb.code(r'''
    def estabilidad(W_a: np.ndarray, W_b: np.ndarray, umbral: float = 0.9) -> float:
        # TODO 3
        raise NotImplementedError("TODO 3: estabilidad")

    def test_estabilidad():
        A = np.eye(3); B = np.array([[1, 0, 0], [0, -1, 0], [0.6, 0.0, 0.8]]); assert abs(estabilidad(A, B) - 2 / 3) < 1e-9, "e1 y e2 (signo) coinciden; e3 no"
        return "✅ test_estabilidad OK"
    corre(test_estabilidad)
    try:
        sae_b, _ = entrena_topk(E, n_lat=96, k=4, pasos=pasos, auxk=True, seed=1); Zb, _ = codifica(sae_b, E); act_b = (Zb.numpy() > 0).sum(0) >= 10
        RES["estables"] = estabilidad(sae.W_dec.data.T.numpy()[activos], sae_b.W_dec.data.T.numpy()[act_b]); print(f"fracción de átomos estables entre semillas (cos>0.9): {RES['estables']:.2f}")
    except (NotImplementedError, ValueError, TypeError, AttributeError, NameError) as e:
        print("⏳ pendiente (TODOs 1–3):", type(e).__name__)
    ''')

    nb.md("""
    ## 4. Steering con una feature vs diferencia de medias (TODO 4)
    Elige la *feature* más «git» (la de mayor fracción de documentos de tema «git» entre sus 20 más activos). Implementa `curva_steering(E, consultas, w, alphas, topic, objetivo)`: para cada $\\alpha$ forma $q'=\\mathrm{norm}(q+\\alpha w)$ (con `q` normalizada), busca el top-10 por coseno (excluye el propio documento de la consulta) y devuelve la **fracción de resultados cuyo tema es `objetivo`**.
    """)
    nb.md(_hint("Normaliza `E` por filas; para cada α: `q = En[consultas] + α·w`, renormaliza, `sc = q @ En.T`, pon `-9` en la posición del propio documento y toma `argsort` descendente de los 10 primeros.",
                "`sc[np.arange(len(consultas)), consultas] = -9; top = np.argsort(-sc, axis=1)[:, :10]; float((topic[top] == objetivo).mean())`."))
    nb.code(r'''
    def curva_steering(E, consultas, w, alphas, topic, objetivo):
        # TODO 4
        raise NotImplementedError("TODO 4: curva_steering")

    def test_steering():
        r = np.random.default_rng(0); Et = np.concatenate([np.array([1, 0]) + 0.05 * r.standard_normal((10, 2)), np.array([0, 1]) + 0.05 * r.standard_normal((10, 2))]); tp = np.array(["a"] * 10 + ["b"] * 10)
        c = curva_steering(Et, np.array([0]), np.array([-1., 1.]), [0, 5], tp, "b"); assert c[0] <= 0.2 and c[1] >= 0.9, f"α=0 casi sin «b» y α=5 (dirección (−1,1)) casi todo «b»; obtenido {c}"
        return "✅ test_steering OK"
    corre(test_steering)
    try:
        En = E / np.linalg.norm(E, axis=1, keepdims=True); mu = {t: En[(topic == t) & (lang == "es")].mean(0) for t in ("cache", "git")}
        w_dm = mu["git"] - mu["cache"]; w_dm /= np.linalg.norm(w_dm); qs = np.where((topic == "cache") & (lang == "es"))[0][:100]
        j_git = max(cols, key=lambda j: np.mean(topic[np.argsort(-Z[:, j])[:20]] == "git")); w_sae = sae.W_dec.data[:, j_git].numpy(); alphas = [0, .5, 1, 1.5, 2, 3]
        RES["steer_sae"] = curva_steering(E, qs, w_sae, alphas, topic, "git"); RES["steer_dm"] = curva_steering(E, qs, w_dm, alphas, topic, "git")
        print("átomo SAE:", np.round(RES["steer_sae"], 2), "\ndif. medias:", np.round(RES["steer_dm"], 2))
    except (NotImplementedError, ValueError, TypeError, AttributeError, NameError, KeyError) as e:
        print("⏳ pendiente (TODOs 1–4):", type(e).__name__)
    ''')

    nb.md("""
    ## 5. Auditoría de filtración (TODO 5)
    Como LSI es lineal, el atacante estima los términos del documento como $\\hat x=z\\,V$ (con $V$ = `lsi.svd.components_`). Implementa `precision_inversion(Z_emb, idx, n_top=10)`: para cada documento `i` de `idx`, toma los `n_top` términos con mayor $\\hat x$ y devuelve la **fracción media que aparece realmente en el texto** del documento. Después mide el efecto de **ruido gaussiano** (σ ∈ {0, .05, .1, .2}) sobre inversión y sobre la utilidad (precisión@10 de faceta).
    """)
    nb.md(_hint("`est = Z_emb[i] @ Vk` (vector sobre el vocabulario), `np.argsort(-est)[:n_top]` son los índices de término; `inv_voc[j]` da la palabra; compara con `set(re.findall(r'\\w+', txt[i].lower()))`.",
                "`np.mean([inv_voc[j] in palabras for j in top])` por documento y luego `np.mean` sobre `idx`."))
    nb.code(r'''
    Vk = lsi.svd.components_; inv_voc = {j: t for t, j in lsi.tf.vocabulary_.items()}
    def precision_inversion(Z_emb, idx, n_top=10):
        # TODO 5
        raise NotImplementedError("TODO 5: precision_inversion")

    def test_inversion():
        p = precision_inversion(E, np.arange(20)); assert 0.5 < p <= 1.0, f"sin ruido debería recuperar mayormente términos reales (obtenido {p:.2f})"
        return "✅ test_inversion OK"
    corre(test_inversion)
    try:
        idx_i = np.random.default_rng(0).choice(len(txt), 150, replace=False); qi = np.random.default_rng(2).choice(len(E), 300, replace=False); rn = np.random.default_rng(1)
        RES["inv"], RES["util"] = {}, {}
        for s in (0, .05, .1, .2):
            Zn = E + s * rn.standard_normal(E.shape).astype(np.float32); Zn_n = Zn / np.linalg.norm(Zn, axis=1, keepdims=True); sc = E[qi] @ Zn_n.T; sc[np.arange(300), qi] = -9
            RES["inv"][s] = precision_inversion(Zn, idx_i); RES["util"][s] = float((facet[np.argsort(-sc, axis=1)[:, :10]] == facet[qi][:, None]).mean())
        print({s: (round(RES["inv"][s], 2), round(RES["util"][s], 2)) for s in RES["inv"]}, "(σ: (inversión, utilidad))")
    except (NotImplementedError, ValueError, TypeError, AttributeError, NameError) as e:
        print("⏳ pendiente (TODO 5):", type(e).__name__)
    ''')

    nb.md("""
    ## 6. Rúbrica (autoevaluación)
    Umbrales **calibrados con la solución de referencia** (FAST_DEV_RUN=True, corpus sintético 12 temas, semilla 42) con el margen indicado. Con datos reales solo se exigen los chequeos estructurales.
    """)
    nb.code(f'''
    REF = {REF!r}
    ''' + r'''
    def rubrica(res):
        out = []
        def chk(nombre, f):
            try: out.append((nombre, "✅" if f() else "❌"))
            except Exception: out.append((nombre, "⏳"))
        chk("1. test_encode", lambda: test_encode().startswith("✅")); chk("3. test_pureza", lambda: test_pureza().startswith("✅"))
        chk("4. test_estabilidad", lambda: test_estabilidad().startswith("✅")); chk("5. test_steering", lambda: test_steering().startswith("✅")); chk("6. test_inversion", lambda: test_inversion().startswith("✅"))
        if sint and FAST_DEV_RUN:
            chk(f"2a. NMSE ≤ 0.07 (ref {REF['nmse']})", lambda: res["nmse"] <= 0.07); chk("2b. L0 = 4", lambda: abs(res["l0"] - 4) < 1e-6); chk(f"2c. ≥ 60 latentes activos (ref {REF['activos']})", lambda: res["activos"] >= 60)
            chk(f"3a. pureza SAE ≥ 0.75 (ref {REF['pureza_sae']})", lambda: res["pureza_sae"] >= 0.75); chk("3b. pureza SAE > pureza PCA", lambda: res["pureza_sae"] > res["pureza_pca"])
            chk(f"4. estabilidad entre semillas = {REF['estables']} ± 0.25", lambda: abs(res["estables"] - REF["estables"]) <= 0.25)
            chk("5a. steering α=0 ≈ 0 % «git»", lambda: res["steer_dm"][0] < 0.1); chk("5b. steering diferencia de medias α=3 ≥ 90 %", lambda: res["steer_dm"][-1] >= 0.9)
            chk("5c. átomo SAE empuja hacia «git» (α=3 > α=0 + 0.2)", lambda: res["steer_sae"][-1] > res["steer_sae"][0] + 0.2)
            chk("6a. inversión sin ruido ≥ 0.8", lambda: res["inv"][0] >= 0.8); chk("6b. ruido σ=0.2 reduce la inversión ≥ 0.15", lambda: res["inv"][0] - res["inv"][0.2] >= 0.15)
            chk("6c. el ruido también reduce la utilidad (trade-off)", lambda: res["util"][0] - res["util"][0.2] >= 0.02)
        else: print("ℹ️ Datos reales o FAST_DEV_RUN=False: se omiten umbrales numéricos.")
        for n, e in out: print(e, n)
        print(f"\n{sum(e == '✅' for _, e in out)}/{len(out)} criterios cumplidos")
    rubrica(RES)
    ''')
    nb.md("""
    ## 7. Informe (escribe aquí)
    1. **Calidad del SAE:** NMSE, L0 y latentes activos; ¿qué fracción de las features son interpretables (pureza ≥ 0.8)?
    2. **Frente a las alternativas:** pureza vs k-means y PCA; steering vs diferencia de medias. ¿Qué aporta el SAE que k-means no?
    3. **Fiabilidad:** estabilidad entre semillas. ¿Qué afirmaciones **no** harías sobre «lo que sabe el modelo»?
    4. **Privacidad:** inversión sin ruido y con ruido; ¿qué política propones para Políglota (módulo 18)?
    """)

    # ───────────── SOLUCIÓN ─────────────
    nb.md("""
    # ⛔ SPOILER — intenta resolverlo primero
    Solución de referencia completa y ejecutable. Si te atascas en un TODO, abre antes las pistas 🪜 de ese paso. Al ejecutar se redefinen las funciones y se recalcula `RES`.
    """)
    nb.code(f'''def _encode_ref(self, x, k=None):
    pre = self.pre(x); v, i = pre.topk(k or self.k, dim=-1)
    return torch.zeros_like(pre).scatter(-1, i, F.relu(v)), pre
TopKSAE.encode = _encode_ref
''' + r'''corre(test_encode)
t0 = time.time(); sae, hist = entrena_topk(E, n_lat=96, k=4, pasos=pasos, auxk=True, seed=0); Z, Xh = codifica(sae, E); Z = Z.numpy()
activos = (Z > 0).sum(0) >= 10; RES = {"nmse": nmse(E, Xh), "activos": int(activos.sum()), "l0": float((Z > 0).sum(1).mean())}
print(f"entrenado en {time.time()-t0:.0f}s · NMSE={RES['nmse']:.3f} · L0={RES['l0']:.1f} · latentes activos {RES['activos']}/96")''')
    nb.code(r'''
    def pureza_features(Z, etiquetas, top=20):
        return np.array([np.bincount(etiquetas[np.argsort(-Z[:, j])[:top]]).max() / top for j in range(Z.shape[1])])
    corre(test_pureza)
    cols = np.where(activos)[0]; P = {"SAE TopK": pureza_features(Z[:, cols], fac_id)}; n_f = len(cols); km = KMeans(n_f, n_init=3, random_state=0).fit(E); Ck = km.cluster_centers_
    P["k-means"] = pureza_features(E @ Ck.T / (np.linalg.norm(Ck, axis=1) + 1e-9), fac_id); pc = PCA(min(n_f, 64)).fit(E); P["PCA"] = pureza_features(np.abs((E - pc.mean_) @ pc.components_.T), fac_id)
    RES.update({"pureza_sae": float(P["SAE TopK"].mean()), "pureza_pca": float(P["PCA"].mean()), "pureza_km": float(P["k-means"].mean())}); print({k: round(float(v.mean()), 3) for k, v in P.items()})
    ''')
    nb.code(r'''
    def estabilidad(W_a, W_b, umbral=0.9):
        C = np.abs(W_a @ W_b.T); return float((C.max(axis=1) > umbral).mean())
    corre(test_estabilidad)
    sae_b, _ = entrena_topk(E, n_lat=96, k=4, pasos=pasos, auxk=True, seed=1); Zb, _ = codifica(sae_b, E); act_b = (Zb.numpy() > 0).sum(0) >= 10
    RES["estables"] = estabilidad(sae.W_dec.data.T.numpy()[activos], sae_b.W_dec.data.T.numpy()[act_b]); print(f"fracción estable (cos>0.9): {RES['estables']:.2f}")
    ''')
    nb.code(r'''
    def curva_steering(E, consultas, w, alphas, topic, objetivo):
        En = E / np.linalg.norm(E, axis=1, keepdims=True); out = []
        for a in alphas:
            q = En[consultas] + a * np.asarray(w); q /= np.linalg.norm(q, axis=1, keepdims=True); sc = q @ En.T; sc[np.arange(len(consultas)), consultas] = -9
            out.append(float((topic[np.argsort(-sc, axis=1)[:, :10]] == objetivo).mean()))
        return out
    corre(test_steering)
    En = E / np.linalg.norm(E, axis=1, keepdims=True); mu = {t: En[(topic == t) & (lang == "es")].mean(0) for t in ("cache", "git")}
    w_dm = mu["git"] - mu["cache"]; w_dm /= np.linalg.norm(w_dm); qs = np.where((topic == "cache") & (lang == "es"))[0][:100]
    j_git = max(cols, key=lambda j: np.mean(topic[np.argsort(-Z[:, j])[:20]] == "git")); w_sae = sae.W_dec.data[:, j_git].numpy(); alphas = [0, .5, 1, 1.5, 2, 3]
    RES["steer_sae"] = curva_steering(E, qs, w_sae, alphas, topic, "git"); RES["steer_dm"] = curva_steering(E, qs, w_dm, alphas, topic, "git"); print("átomo SAE:", np.round(RES["steer_sae"], 2), "\ndif. medias:", np.round(RES["steer_dm"], 2))
    ''')
    nb.code(r'''
    def precision_inversion(Z_emb, idx, n_top=10):
        out = []
        for i in idx:
            top = np.argsort(-(Z_emb[i] @ Vk))[:n_top]; palabras = set(re.findall(r"\w+", txt[i].lower())); out.append(np.mean([inv_voc[j] in palabras for j in top]))
        return float(np.mean(out))
    corre(test_inversion)
    idx_i = np.random.default_rng(0).choice(len(txt), 150, replace=False); qi = np.random.default_rng(2).choice(len(E), 300, replace=False); rn = np.random.default_rng(1); RES["inv"], RES["util"] = {}, {}
    for s in (0, .05, .1, .2):
        Zn = E + s * rn.standard_normal(E.shape).astype(np.float32); Zn_n = Zn / np.linalg.norm(Zn, axis=1, keepdims=True); sc = E[qi] @ Zn_n.T; sc[np.arange(300), qi] = -9
        RES["inv"][s] = precision_inversion(Zn, idx_i); RES["util"][s] = float((facet[np.argsort(-sc, axis=1)[:, :10]] == facet[qi][:, None]).mean())
    print({s: (round(RES["inv"][s], 2), round(RES["util"][s], 2)) for s in RES["inv"]}, "(σ: (inversión, utilidad))")
    rubrica(RES)
    ''')
    nb.code(r'''
    fig, ax = plt.subplots(1, 3, figsize=(14, 3.6)); ax[0].bar(list(P), [v.mean() for v in P.values()], color=[VERDE, AZUL, GRIS]); ax[0].set_ylabel("pureza media"); ax[0].set_title("Interpretabilidad medida")
    ax[1].plot(alphas, RES["steer_sae"], "o-", color=VERDE, label="átomo SAE"); ax[1].plot(alphas, RES["steer_dm"], "s--", color=AZUL, label="diferencia de medias"); ax[1].set_xlabel("α"); ax[1].set_ylabel("% «git» en el top-10"); ax[1].legend(frameon=False); ax[1].set_title("Steering")
    s_ = list(RES["inv"]); ax[2].plot(s_, [RES["inv"][s] for s in s_], "o-", color=ROJO, label="inversión"); ax[2].plot(s_, [RES["util"][s] for s in s_], "s-", color=VERDE, label="utilidad"); ax[2].set_xlabel("σ del ruido"); ax[2].legend(frameon=False); ax[2].set_title("Privacidad vs utilidad"); ax[2].set_ylim(0, 1.02)
    plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** (1) Pureza: SAE > PCA, y k-means es competitivo o mejor: el SAE no «gana» en agrupar, sino en **descomponer** (4 átomos por documento). (2) Steering: la diferencia de medias iguala o supera al átomo SAE: no confundas legibilidad con control. (3) Privacidad: sin ruido la inversión es alta; el ruido la baja pero también daña la utilidad: **hay que elegir un punto de operación y medirlo contra un atacante real**.
    """)
    nb.md("""
    ## 🚀 Retos extra (nivel experto)
    1. **Tamaño del diccionario:** entrena SAE con 48, 96, 384 latentes (mismo $k$) y mide pureza, *feature splitting* (¿una faceta se reparte en varias features?) y latentes muertos.
    2. **JumpReLU:** implementa la variante con umbral aprendible (Rajamanoharan et al., 2024) y compara la frontera NMSE–$L_0$ con TopK.
    3. **Auto-interpretabilidad con LLM** (celda opcional protegida con variable de entorno): pide a un LLM una etiqueta por feature a partir de sus 10 documentos más activos y **valida** con la pureza; reporta acuerdo.
    4. **Embedder real:** repite con `paraphrase-multilingual-MiniLM-L12-v2` o `intfloat/multilingual-e5-small` (T4): ¿aparecen features multilingües (un átomo para ES y EN)? ¿Dimensiones dominantes (`diagnostico_dimensiones`)?
    5. **LEACE / borrado:** proyecta fuera la dirección de idioma y mide con IC (módulo 15) si cambia el retrieval; compara con tu proyección de medias.
    6. **Inversión real:** con `vec2text` (corrector para el embedder que uses) reconstruye 50 frases de Políglota y mide similitud/coincidencia exacta.
    7. **Estabilidad con IC:** 5 semillas; reporta la fracción estable con IC bootstrap.

    ## 🧠 Reflexión
    - ¿Qué decisión de producto tomarías con estas features (explicar resultados, auditar sesgos de idioma, dirigir el retrieval…)? ¿Cuál **no**?
    - Si dos semillas dan features distintas, ¿cómo se protege un informe de interpretabilidad frente a «cherry-picking»?
    - ¿Qué cambia en la auditoría de privacidad si Políglota indexa contratos con datos personales? (módulo 18)
    - ¿Qué parte del banco de módulo 15 reutilizarías para evaluar la *utilidad* tras aplicar una defensa de ruido o cuantización?

    ➡️ **Siguiente:** módulo 18 (producción): versionado y migración de embedders, privacidad y monitorización.
    """)
