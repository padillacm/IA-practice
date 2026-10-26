"""Genera el módulo 14 (lección + proyecto + README): Indexación y ANN.

Ejecutar desde la raíz del repo:  python tokenization-embeddings-course/_tools/builders/build_14.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from nbbuild import Notebook  # noqa: E402
import _a5_common as C  # noqa: E402
from poliglota_utils import SRC_METRICS, src_corpus_cells  # noqa: E402  (utilidades canónicas del módulo 00)

COURSE = "tokenization-embeddings-course"
MOD = f"{COURSE}/14_indexacion_ann"
LESSON = f"{MOD}/14_indexacion_ann.ipynb"
PROJECT = f"{MOD}/14_proyecto_indexacion_ann.ipynb"
os.makedirs(f"{MOD}/assets", exist_ok=True)
open(f"{MOD}/assets/.gitkeep", "a").close()

CODE_PIP = r'''
!pip install -q faiss-cpu numpy scipy scikit-learn matplotlib pandas sentence-transformers
'''

CODE_ANN_BASE = r'''
import faiss
faiss.omp_set_num_threads(N_THREADS)         # medición justa: un hilo (la latencia de UNA query es lo que importa)
import pandas as pd
import matplotlib.pyplot as plt

def exacto_topk(Q, X, k=10):
    """Fuerza bruta: el 'oráculo' para medir recall. Q (nq,d), X (n,d) normalizados -> índices (nq,k)."""
    out = np.empty((len(Q), k), dtype=np.int64)
    for s in range(0, len(Q), 64):
        S = Q[s:s + 64] @ X.T
        idx = np.argpartition(-S, k, axis=1)[:, :k]
        out[s:s + 64] = np.take_along_axis(idx, np.take_along_axis(S, idx, 1).argsort(1)[:, ::-1], 1)
    return out

def recall_vs_gt(idx, gt):
    """Neighbor recall@k: fracción del top-k exacto que devuelve el índice aproximado (ignora los -1 de FAISS)."""
    return float(np.mean([len(set(a[a >= 0].tolist()) & set(b.tolist())) / len(b) for a, b in zip(idx, gt)]))

def mide_latencia(fn, Q, calentamiento=10, repeticiones=1):
    """Latencia por query con batch=1 (así se sirve en producción). fn(q: (d,)) -> cualquier cosa. Devuelve p50, p99 (ms) y QPS."""
    for q in Q[:calentamiento]:
        fn(q)
    t = []
    for _ in range(repeticiones):
        for q in Q:
            t0 = time.perf_counter(); fn(q); t.append(time.perf_counter() - t0)
    t = np.array(t) * 1e3
    return float(np.percentile(t, 50)), float(np.percentile(t, 99)), float(1e3 / t.mean())

def tam_indice_MB(index):
    """Tamaño real serializado del índice FAISS en MB (incluye vectores, listas y grafo)."""
    return faiss.serialize_index(index).nbytes / 1e6
'''

CODE_ANN_GEN = r'''
def genera_vectores(n, d, nc=30, nq=200, decay=0.2, sep=0.5, seed=0):
    """Vectores sintéticos 'tipo embedding': mezcla de nc clusters con espectro decreciente (unas direcciones dominan),
    normalizados a norma 1. decay=0 -> casi isótropo (difícil para ANN); decay alto -> muy anisótropo (IVF/HNSW lo separan mejor, pero la PQ pierde recall porque las diferencias entre vecinos son pequeñas frente a su error de cuantización)."""
    rng = np.random.default_rng(seed)
    spec = 1.0 / (1 + np.arange(d)) ** decay
    spec /= spec.max()
    centros = rng.normal(size=(nc, d)) * spec * sep
    a = rng.integers(0, nc, size=n + nq)
    V = centros[a] + rng.normal(size=(n + nq, d)) * spec
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    return V[:n].astype(np.float32), V[n:].astype(np.float32)

N = 20000 if FAST_DEV_RUN else 200000
D = 64 if FAST_DEV_RUN else 128
X, Q = genera_vectores(N, D)
t0 = time.perf_counter(); GT = exacto_topk(Q, X, 10); t_gt = time.perf_counter() - t0
print(f"N={N:,} · d={D} · {len(Q)} queries · fuerza bruta de todas: {t_gt:.2f}s · {t_gt/len(Q)*1e3:.2f} ms/query (batch)")
'''


def lesson() -> None:
    nb = Notebook("Módulo 14 · Indexación y ANN", colab_path=LESSON, gpu=False)

    # ───────────────────────────── Cabecera ─────────────────────────────
    nb.md(nb.badge() + r'''

# Módulo 14 · Indexación y búsqueda aproximada de vecinos (ANN)

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) · **GPU:** no necesaria (CPU; todo en `FAST_DEV_RUN` en minutos) ·
**Cómputo estimado:** 0 unidades de Colab (CPU); con `FAST_DEV_RUN = False` conviene un runtime con más RAM, pero no GPU.

> 🧭 **Ruta núcleo vs ampliación.** Núcleo (≈ 3 h): secciones 1–5 (fuerza bruta, métricas, IVF, PQ, HNSW) y 10 (FAISS en uso real). Ampliación (≈ 1–2 h): Vamana/DiskANN (6), ScaNN (7), RaBitQ (8) y búsqueda filtrada (9).

**Prerrequisitos:** módulo 12 (dimensión, Matryoshka, cuantización int8/binaria) y 13 (qué vectores indexas: densos, multi-vector).
**Puente con recsys:** el módulo [`recsys-course/08_deep_retrieval_ann`](../../recsys-course/08_deep_retrieval_ann/README.md) ya enseña FAISS (Flat/IVF/IVF-PQ/HNSW) con curvas recall-latencia sobre vectores de *two-tower*. Aquí **no lo repetimos**: construimos los algoritmos desde cero (mini-HNSW, PQ/OPQ, Vamana, RaBitQ), tratamos el recall como métrica de ingeniería y añadimos lo que allí no está: **grafos en disco, cuantización con garantías y búsqueda filtrada**.

**Hilo conductor — Políglota.** Con 10 M de fragmentos, la búsqueda exacta cuesta ~40 GB de lecturas por consulta. El CTO pide una *ficha técnica* del índice: **recall@10 ≥ 0.95, p99 ≤ 20 ms, memoria ≤ X GB**. Hoy aprendes a construirla con datos.

> **Estado del arte a octubre de 2026.** Los algoritmos clásicos son 🟢; cualquier cifra de adopción por empresas o de rendimiento relativo está fechada y con fuente. La operación de bases vectoriales (sharding, réplicas, actualizaciones) es el módulo 18.
''')
    nb.md(r'''## 🎯 Objetivos de aprendizaje
1. **Medir** un índice ANN con el protocolo correcto: neighbor recall@k contra fuerza bruta, latencia p50/p99 con batch=1 y memoria real.
2. **Implementar desde cero** IVF (k-means + listas invertidas), PQ/OPQ (cuantización de producto con ADC) y comparar con FAISS.
3. **Implementar un mini-HNSW** (capas, `efConstruction`, heurística de selección de vecinos, búsqueda voraz por capas) y razonar sobre sus parámetros `M`, `ef`.
4. **Implementar Vamana** (la base de DiskANN) con `RobustPrune` y explicar por qué el grafo se diseña para leer pocas páginas de SSD.
5. **Derivar la idea de ScaNN** (cuantización anisótropa) y la de **RaBitQ** (estimador insesgado con cota de error) e implementar una versión mini de RaBitQ.
6. **Resolver búsqueda filtrada**: pre-filtro, post-filtro y filtro dentro del grafo, y medir cómo se rompe el recall.
7. **Construir y comparar índices FAISS reales** y elegir la configuración que cumple un SLA (recall, latencia, memoria).
''')
    nb.md(r'''## 🔁 Conexión con módulos anteriores
<details><summary><b>1 · (M12)</b> ¿Qué memoria ocupan 10 M de vectores de 1024 dims en float32, int8 y binario?</summary>

40.96 GB, 10.24 GB y 1.28 GB. La cuantización de *vectores* (módulo 12) es un caso particular de lo que hoy hacemos *dentro del índice*: PQ y RaBitQ son cuantizaciones **diseñadas para que la distancia aproximada se calcule sin descomprimir**.
</details>
<details><summary><b>2 · (M12)</b> ¿Por qué se renormaliza tras truncar y qué métrica de similitud usan casi todos los embedders?</summary>

Para volver a la esfera unidad; así producto interno = coseno = (monótona de) distancia L2. Usaremos vectores normalizados, de modo que MIPS, coseno y L2 dan el **mismo ranking**.
</details>
<details><summary><b>3 · (M13)</b> ¿Qué es lo más caro de almacenar en late interaction y cómo lo mitiga MUVERA?</summary>

Un vector por token. MUVERA construye un único vector de dimensión fija por documento (FDE) para poder usar **un índice ANN estándar** (este módulo) como generador de candidatos y re-puntuar con MaxSim exacto.
</details>
<details><summary><b>4 · (recsys 08)</b> ¿Qué métrica compara un índice aproximado con el exacto?</summary>

El *recall* del top-K aproximado respecto al top-K exacto (neighbor recall). Es distinto del recall de la **tarea** (¿está el documento relevante?): el primero mide solo el error del índice.
</details>
<details><summary><b>5 · (M08, Cálculo)</b> Un codebook VQ de $K = 256$ centroides en 2D, ¿cuántos bits cuesta por vector? ¿Y si cuantizas un vector de 768 dimensiones en 96 trozos de 8 dimensiones, cada uno con su codebook de 256?</summary>

$\log_2 256 = 8$ bits = 1 byte por vector; troceado: 96 trozos × 1 byte = **96 B** (frente a 3 072 B en float32). Es **PQ** (sección 4): la VQ del módulo 08 aplicada por subespacios, con $256^{96}$ combinaciones posibles sin tener que entrenar un codebook gigante. Los centroides se aprenden con k-means, igual que en VQ e IVF.
</details>
<details><summary><b>6 · (M00, Transferencia)</b> El índice invertido del módulo 00 guarda, por término, la lista de documentos que lo contienen. ¿Qué haría de «término» en un índice vectorial?</summary>

Un **centroide**: IVF (*inverted file*, sección 3) asigna cada vector a su centroide más cercano y guarda una lista por centroide; en la consulta solo se recorren las `nprobe` listas más cercanas, igual que BM25 solo recorre las listas de los términos de la query. La diferencia: un vector cerca de la frontera entre dos celdas puede quedar fuera, y de ahí el recall < 1.
</details>
''')

    # ───────────────────────────── Setup ─────────────────────────────
    nb.md(r'''## 0 · Preparación
Esta lección usa **vectores sintéticos "tipo embedding"** (mezcla de clusters con espectro decreciente, normalizados) para poder generar cientos de miles de vectores sin descargar nada, y al final repite una medición con **vectores reales de Políglota** (módulo 12) si hay un embedder disponible. Todos los experimentos usan **un hilo**: la latencia de una query es lo que importa.
''')
    nb.code(CODE_PIP)
    nb.code(C.CODE_SETUP_COMMON)
    nb.code(CODE_ANN_BASE)
    nb.code(CODE_ANN_GEN)

    # ───────────────────────────── 1. Intuición ─────────────────────────────
    nb.md(r'''## 1 · Intuición: por qué existe el ANN y cuándo NO usarlo

Buscar los $k$ vectores más parecidos a una query entre $N$ vectores de dimensión $d$ cuesta $O(N d)$ operaciones y, sobre todo, **leer $4Nd$ bytes de memoria** por consulta: es un problema limitado por el ancho de banda. Con $N=10^7$ y $d=1024$ son **41 GB por consulta**. Los índices ANN cambian exactitud por velocidad con tres ideas ortogonales:

| Idea | Familia | Qué evita |
|---|---|---|
| **Particionar** el espacio y mirar pocas particiones | IVF | leer todos los vectores |
| **Navegar un grafo** de proximidad | HNSW, Vamana/DiskANN | comparar con todos los vectores |
| **Comprimir** los vectores y calcular distancias aproximadas sobre los códigos | PQ, ScaNN, RaBitQ, binaria | leer y multiplicar vectores completos |

Se combinan (IVF-PQ, HNSW+PQ, DiskANN con PQ en RAM). Y el triángulo de siempre: **recall – latencia – memoria**; mejorar dos suele empeorar el tercero.

> 💡 **Analogía con IR y recsys.** IVF ≈ un índice invertido sobre "celdas" en vez de términos. HNSW ≈ "seis grados de separación" con autopistas (capas altas) y calles locales (capa 0). PQ ≈ compresión con pérdida tipo JPEG: guarda códigos y reconstruye aproximadamente. En recsys (módulo 08) el índice de ítems es la misma pieza.

> ⚠️ **Cuándo NO usar ANN.** Hasta ~$10^5$ vectores, la **fuerza bruta** exacta (BLAS/SIMD) suele ser igual de rápida y sin pérdida de recall. Empieza siempre por medirla.
''')
    nb.gemini(
        "imagen", "M14-IMG-01", "Mapa de familias de índices ANN",
        "Las tres ideas (particionar, navegar un grafo, comprimir) y cómo se combinan en los índices que se usan en producción.",
        """
        Diagrama técnico limpio, fondo blanco, formato 16:9. Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Tipografía sans-serif legible. Sin ilustraciones decorativas ni texto inventado.

        Título arriba: "Tres ideas para buscar vecinos sin mirar todo".
        Tres columnas con encabezado coloreado:
        1) Azul "Particionar": dibujo 2D de un plano dividido en celdas de Voronoi con puntos; una consulta marcada con una estrella cae en una celda, y se resaltan 2 celdas vecinas (nprobe = 2). Etiqueta: "IVF".
        2) Naranja "Navegar un grafo": tres capas horizontales apiladas (capa 2 arriba con pocos nodos, capa 1, capa 0 abajo con muchos nodos), una flecha que baja saltando entre nodos hacia la estrella. Etiquetas: "HNSW" y "Vamana / DiskANN".
        3) Verde "Comprimir": un vector de 8 cuadros de colores que se parte en 4 pares y cada par se sustituye por un número de código (por ejemplo 17, 203, 5, 88). Etiquetas: "PQ", "ScaNN", "RaBitQ (1 bit por dimensión)".
        Debajo de las columnas, una barra horizontal gris con flechas que unen las columnas, y el texto: "Combinaciones habituales: IVF-PQ · HNSW + PQ · DiskANN (grafo en SSD + PQ en RAM)".
        Pie de figura pequeño: "Triángulo de diseño: recall · latencia · memoria".

        Evita: texto ilegible, más de tres columnas, flechas cruzadas confusas, logos de empresas, decoración.
        """,
        "Tres columnas: particionar con celdas, navegar un grafo por capas y comprimir vectores con códigos",
        """
        PARTICIONAR (IVF)      NAVEGAR (HNSW / Vamana)       COMPRIMIR (PQ / ScaNN / RaBitQ)
        ┌──┬──┬──┐ ★ nprobe=2  capa2:  o       o              [■■□□▪▪▫▫] -> [17|203|5|88]
        ├──┼──┼──┤             capa1:  o  o  o  o                    códigos de 1 byte
        └──┴──┴──┘             capa0:  o o o o o o o ★
        Combinaciones: IVF-PQ · HNSW+PQ · DiskANN (grafo en SSD + PQ en RAM)
        """,
    )
    nb.md(r'''> 👀 **Qué debes observar.** Las tres columnas atacan costes distintos: **cuántos vectores se tocan** (IVF), **cuántas comparaciones se hacen** (grafo) y **cuántos bytes ocupa y se lee cada vector** (compresión). Los sistemas reales combinan una de cada tipo.

## 2 · Fuerza bruta y el protocolo de medición

Antes de cualquier índice hace falta (a) el **oráculo** (top-$k$ exacto), (b) la métrica y (c) un protocolo de latencia honesto:

- **Neighbor recall@$k$** $=\frac{|\text{ANN}_k\cap\text{Exacto}_k|}{k}$, promediado sobre queries. Mide el error del índice, no la calidad de la tarea (para eso, nDCG, módulos 12–13 y 15).
- **Latencia con batch=1** y percentiles **p50/p99** (la media esconde las colas). Calienta antes; un hilo; mismo hardware para todas las configuraciones.
- **Memoria real** del índice (bytes serializados), no la estimada a ojo.
''')
    nb.code(r'''
rng = np.random.default_rng(SEED)
tamanos = [int(x) for x in np.geomspace(1000, N, 6)]
filas = []
for n_ in tamanos:
    Xn = X[:n_]
    flat = faiss.IndexFlatIP(D); flat.add(Xn)
    p50_np, _, _ = mide_latencia(lambda q: Xn @ q, Q[:100])                  # NumPy: producto matriz-vector (BLAS)
    p50_fa, p99_fa, _ = mide_latencia(lambda q: flat.search(q[None], 10), Q[:100])
    filas.append((n_, p50_np, p50_fa, p99_fa))
bf = pd.DataFrame(filas, columns=["N", "numpy p50 (ms)", "faiss Flat p50 (ms)", "faiss Flat p99 (ms)"])
display(bf.round(3))
fig, axs = plt.subplots(1, 2, figsize=(11, 3.5))
axs[0].loglog(bf["N"], bf["numpy p50 (ms)"], "o-", label="NumPy X @ q", color="#F28E2B")
axs[0].loglog(bf["N"], bf["faiss Flat p50 (ms)"], "s-", label="FAISS IndexFlatIP", color="#1F6FEB")
axs[0].loglog(bf["N"], bf["faiss Flat p99 (ms)"], "s:", label="FAISS Flat (p99)", color="#1F6FEB", alpha=.6)
axs[0].set_xlabel("N (vectores)"); axs[0].set_ylabel("ms por query (batch=1)"); axs[0].set_title("La fuerza bruta escala linealmente en N"); axs[0].legend(fontsize=8); axs[0].grid(alpha=.3, which="both")
gb_s = 4 * D * bf["N"] / (bf["faiss Flat p50 (ms)"] * 1e-3) / 1e9
axs[1].semilogx(bf["N"], gb_s, "o-", color="#2CA02C")
axs[1].set_xlabel("N (vectores)"); axs[1].set_ylabel("GB/s efectivos leídos"); axs[1].set_title("Ancho de banda efectivo de la fuerza bruta"); axs[1].grid(alpha=.3, which="both")
plt.tight_layout(); plt.show()
print(f"A N={N:,} y d={D}: {4*D*N/1e6:.0f} MB que leer por query. Para 10 M x 1024 d serían {4*1024*10_000_000/1e9:.0f} GB.")
''')
    nb.md(r'''> 👀 **Qué debes observar.** (1) En escala log-log la latencia es una **recta de pendiente 1**: duplicar $N$ duplica el tiempo. (2) A $N$ pequeño domina el *overhead* de llamada y el ancho de banda efectivo es bajo; al crecer $N$ se acerca al límite de memoria de tu CPU. (3) Con tu $N$ actual la fuerza bruta puede ser *rápida*: **el ANN solo gana cuando $N$ es grande o el presupuesto de latencia es estricto**. Guarda este gráfico como línea base.

## 3 · IVF desde cero: particionar con k-means

**Entrenamiento:** k-means con $n_{list}$ centroides (regla práctica: $n_{list}\approx\sqrt N$ a $4\sqrt N$). Cada vector se asigna a su centroide más cercano y va a su **lista invertida**. **Búsqueda:** calcula la similitud de la query con los $n_{list}$ centroides, visita las **$n_{probe}$ listas** más cercanas y busca exacto solo en ellas:

$$\text{coste} \approx n_{list}\,d + \frac{n_{probe}}{n_{list}}\,N\,d$$

Dos términos: el escaneo de centroides (crece con $n_{list}$) y el de las listas (crece con $n_{probe}$). El recall sube con $n_{probe}$ a costa de latencia.
''')
    nb.code(r'''
def kmeans(V, k, iters=12, seed=0):
    """k-means esférico (vectores normalizados: asignar por producto interno máximo, recentrar y normalizar)."""
    rng = np.random.default_rng(seed)
    C = V[rng.choice(len(V), k, replace=False)].copy()
    for _ in range(iters):
        a = (V @ C.T).argmax(1)
        for j in range(k):
            m = a == j
            if m.any():
                c = V[m].mean(0); C[j] = c / np.linalg.norm(c)
    return C

class MiniIVF:
    def __init__(self, nlist, seed=0):
        self.nlist, self.seed = nlist, seed
    def fit(self, V):
        self.C = kmeans(V, self.nlist, seed=self.seed)
        asign = (V @ self.C.T).argmax(1)
        self.V = V
        self.listas = [np.where(asign == j)[0] for j in range(self.nlist)]      # listas invertidas: celda -> ids
        return self
    def search(self, q, k=10, nprobe=4):
        celdas = np.argpartition(-(self.C @ q), nprobe)[:nprobe]
        cand = np.concatenate([self.listas[j] for j in celdas])
        s = self.V[cand] @ q
        top = cand[np.argsort(-s)[:k]]
        return top, len(cand) + self.nlist                                      # (ids, distancias calculadas)

NLIST = int(np.sqrt(N))
t0 = time.perf_counter(); ivf = MiniIVF(NLIST).fit(X); t_build = time.perf_counter() - t0
tam_listas = np.array([len(l) for l in ivf.listas])
print(f"nlist={NLIST} · entrenamiento+asignación {t_build:.1f}s · tamaño de lista: media {tam_listas.mean():.0f}, máx {tam_listas.max()}")

# FAISS equivalente
cuant = faiss.IndexFlatIP(D)
ivf_f = faiss.IndexIVFFlat(cuant, D, NLIST, faiss.METRIC_INNER_PRODUCT); ivf_f.train(X); ivf_f.add(X)
filas = []
for nprobe in (1, 2, 4, 8, 16, 32, 64):
    res = [ivf.search(q, 10, nprobe) for q in Q]
    ivf_f.nprobe = nprobe
    _, I = ivf_f.search(Q, 10)
    p50, p99, _ = mide_latencia(lambda q: ivf_f.search(q[None], 10), Q[:100])
    filas.append(dict(nprobe=nprobe, recall_propio=recall_vs_gt(np.stack([r[0] for r in res]), GT), recall_faiss=recall_vs_gt(I, GT),
                      pct_escaneado=100 * np.mean([r[1] for r in res]) / N, faiss_p50_ms=p50))
tab_ivf = pd.DataFrame(filas)
display(tab_ivf.round(3))
''')
    nb.code(r'''
fig, axs = plt.subplots(1, 2, figsize=(11, 3.5))
axs[0].plot(tab_ivf["nprobe"], tab_ivf["recall_propio"], "o-", label="IVF desde cero", color="#F28E2B")
axs[0].plot(tab_ivf["nprobe"], tab_ivf["recall_faiss"], "s--", label="FAISS IndexIVFFlat", color="#1F6FEB")
axs[0].set_xscale("log", base=2); axs[0].set_xlabel("nprobe"); axs[0].set_ylabel("recall@10"); axs[0].set_title("Recall vs nprobe"); axs[0].legend(); axs[0].grid(alpha=.3)
axs[1].plot(tab_ivf["pct_escaneado"], tab_ivf["recall_propio"], "o-", color="#F28E2B")
for r in tab_ivf.itertuples():
    axs[1].annotate(f"{r.nprobe}", (r.pct_escaneado, r.recall_propio), textcoords="offset points", xytext=(4, -10), fontsize=7)
axs[1].set_xlabel("% de vectores escaneados"); axs[1].set_ylabel("recall@10"); axs[1].set_title("Cuánto hay que mirar para un recall dado"); axs[1].grid(alpha=.3)
plt.tight_layout(); plt.show()
''')
    nb.md(r'''> 👀 **Qué debes observar.** (1) Tu IVF y el de FAISS dan casi el mismo recall (pequeñas diferencias por la inicialización de k-means). (2) El recall **sube rápido y luego se aplana**: pasar de `nprobe` 16 a 64 cuesta 4× más escaneo para ganar pocos puntos. (3) A la derecha, el recall se pierde sobre todo por vecinos que caen **en una celda vecina**: cuanto menos separados los clusters (datos más "difíciles"), más celdas hay que mirar. Lo habitual en producción: elegir `nprobe` como el menor valor que cumple el recall objetivo en un conjunto de validación.

## 4 · Product Quantization (PQ) y OPQ desde cero

**PQ** (Jégou et al., 2011) divide cada vector en $m$ subvectores de dimensión $d/m$ y aprende **un diccionario de $K=256$ centroides por subespacio** (k-means). Cada vector se sustituye por $m$ índices de **1 byte** (compresión $4d/m$). La distancia entre una query $q$ y un vector codificado se calcula con **ADC** (*asymmetric distance computation*): se precomputa una tabla $T_j[c]=\langle q_j,\mu_{j,c}\rangle$ (para cada subespacio $j$ y centroide $c$) y el score es
$$\langle q,\hat x\rangle=\sum_{j=1}^{m}T_j\big[\text{code}_j(x)\big],$$
solo $m$ búsquedas en tabla y sumas por vector (la query **no** se cuantiza: asimétrica).

✍️ **Ejemplo a mano ($d = 4$, $m = 2$, $K = 2$).** Diccionarios: subespacio 1 $\{c_{1,0} = (1, 1),\ c_{1,1} = (-1, 0)\}$; subespacio 2 $\{c_{2,0} = (0, 0),\ c_{2,1} = (1, 1)\}$. El documento $x = (0.9, 0.8, 0.1, -0.1)$ se codifica por el centroide más cercano en cada mitad: $(0.9, 0.8) \to 0$, $(0.1, -0.1) \to 0$; código `[0, 0]` (2 bytes en vez de 16). Query $q = (1, 0, 0.5, 0.5)$: tablas $T_1 = (\langle(1,0),c_{1,0}\rangle, \langle(1,0),c_{1,1}\rangle) = (1, -1)$ y $T_2 = (0, 1)$. Score aproximado $= T_1[0] + T_2[0] = 1 + 0 = 1$; el exacto es $\langle q, x\rangle = 0.9 + 0 + 0.05 - 0.05 = 0.9$. Es la VQ del módulo 08 aplicada por trozos (con $K^m$ «centroides» implícitos, aquí 4) y la misma idea que un diccionario de compresión: guardas el id del patrón, no el dato. A escala, $d = 768$ float32 = 3 072 B frente a $m = 96$ códigos = 96 B (32×).
 **OPQ** (Ge et al., 2013) aprende además una **rotación ortogonal** $R$ que equilibra la varianza entre subespacios antes de cuantizar; se resuelve alternando "entrenar PQ" y "Procrustes" ($R=UV^\top$ con $U\Sigma V^\top=\text{SVD}(X^\top\hat X)$).
''')
    nb.code(r'''
def entrena_pq(V, m, K=256, iters=8, n_train=8000):
    d = V.shape[1] // m
    muestra = V[np.random.default_rng(SEED).choice(len(V), min(n_train, len(V)), replace=False)]
    return [kmeans_l2(muestra[:, j * d:(j + 1) * d], min(K, len(muestra)), iters, seed=j) for j in range(m)]

def kmeans_l2(V, k, iters, seed=0):
    rng = np.random.default_rng(seed)
    C = V[rng.choice(len(V), k, replace=False)].copy()
    for _ in range(iters):
        a = (-2 * V @ C.T + (C ** 2).sum(1)).argmin(1)
        for j in range(k):
            m_ = a == j
            if m_.any():
                C[j] = V[m_].mean(0)
    return C

def codifica_pq(V, libros):
    d = V.shape[1] // len(libros)
    return np.stack([(-2 * V[:, j * d:(j + 1) * d] @ c.T + (c ** 2).sum(1)).argmin(1) for j, c in enumerate(libros)], 1).astype(np.uint8)

def decodifica_pq(codigos, libros):
    return np.concatenate([c[codigos[:, j]] for j, c in enumerate(libros)], 1)

def adc(q, libros, codigos):
    """Tablas T_j[c] = <q_j, mu_jc> y score = suma_j T_j[code_j]: solo m accesos a tabla por vector."""
    d = len(q) // len(libros)
    T = [c @ q[j * d:(j + 1) * d] for j, c in enumerate(libros)]
    return sum(T[j][codigos[:, j]] for j in range(len(libros)))

filas, PQ = [], {}
for m in (4, 8, 16, 32):
    if D % m:
        continue
    t0 = time.perf_counter(); libros = entrena_pq(X, m); codigos = codifica_pq(X, libros); t_pq = time.perf_counter() - t0
    mse = float(((X - decodifica_pq(codigos, libros)) ** 2).sum(1).mean())
    r_pq = np.stack([np.argsort(-adc(q, libros, codigos))[:10] for q in Q])
    r_refine = []                                                   # PQ para candidatos + re-ranking exacto de los 100 mejores
    for q in Q:
        cand = np.argsort(-adc(q, libros, codigos))[:100]
        r_refine.append(cand[np.argsort(-(X[cand] @ q))[:10]])
    PQ[m] = (libros, codigos)
    filas.append(dict(m=m, bytes_por_vector=m, compresion=f"{4*D/m:.0f}x", mse=mse, recall_ADC=recall_vs_gt(r_pq, GT),
                      recall_ADC_mas_refine100=recall_vs_gt(np.stack(r_refine), GT), seg_entrenar=t_pq))
tab_pq = pd.DataFrame(filas)
display(tab_pq.round(3))
''')
    nb.code(r'''
fig, axs = plt.subplots(1, 2, figsize=(11, 3.5))
axs[0].plot(tab_pq["bytes_por_vector"], tab_pq["recall_ADC"], "o-", label="solo ADC", color="#F28E2B")
axs[0].plot(tab_pq["bytes_por_vector"], tab_pq["recall_ADC_mas_refine100"], "s-", label="ADC + re-ranking exacto de 100", color="#2CA02C")
axs[0].axvline(4 * D, color="#6B7280", ls=":"); axs[0].text(4 * D, 0.05, " float32", color="#6B7280", fontsize=8)
axs[0].set_xscale("log", base=2); axs[0].set_xlabel("bytes por vector (m)"); axs[0].set_ylabel("recall@10"); axs[0].set_title("PQ: memoria vs recall"); axs[0].legend(fontsize=8); axs[0].grid(alpha=.3)

# OPQ: dónde ayuda de verdad (varianza concentrada en pocas dimensiones)
Xs, _ = genera_vectores(6000, 64, nc=30, nq=10, decay=1.0, sep=1.0)
def mse_pq(V, m=8, K=64):
    lib = entrena_pq(V, m, K, iters=6, n_train=6000); return float(((V - decodifica_pq(codifica_pq(V, lib), lib)) ** 2).sum(1).mean())
Rm, mses = np.eye(64), []
mses.append(mse_pq(Xs))
for it in range(3):
    lib = entrena_pq(Xs @ Rm, 8, 64, iters=6, n_train=6000); Y = decodifica_pq(codifica_pq(Xs @ Rm, lib), lib)
    U, _, Vt = np.linalg.svd(Xs.T @ Y); Rm = U @ Vt
    mses.append(mse_pq(Xs @ Rm))
axs[1].plot(range(len(mses)), mses, "o-", color="#1F6FEB")
axs[1].set_xlabel("iteración de OPQ (0 = PQ sin rotación)"); axs[1].set_ylabel("error de cuantización (MSE)"); axs[1].set_title("OPQ reduce la distorsión"); axs[1].grid(alpha=.3)
plt.tight_layout(); plt.show()
print(f"MSE PQ = {mses[0]:.3f} → OPQ = {mses[-1]:.3f} ({100*(1-mses[-1]/mses[0]):.0f}% menos)")
''')
    nb.md(r'''> 👀 **Qué debes observar.** (1) Con pocos bytes por vector el ADC **solo** pierde mucho recall (los datos de esta lección son poco anisótropos, un caso difícil para PQ); con más bytes sube. (2) **PQ + re-ranking exacto** de unos pocos cientos de candidatos recupera casi todo el recall con el mismo índice comprimido: es el patrón estándar (IVF-PQ + *refine*). Por eso en producción los códigos PQ viven en RAM y los vectores completos en disco/SSD. (3) A la derecha, **OPQ** reduce el error de cuantización cuando la varianza está desigualmente repartida entre subespacios (aquí `decay=1.0`); en datos casi isótropos la ganancia es mínima. Mide antes de pagar su coste de entrenamiento.
''')
    nb.gemini(
        "imagen", "M14-IMG-02", "Product Quantization: del vector al código de m bytes",
        "El proceso de PQ: partir en subvectores, buscar el centroide más cercano en cada diccionario y guardar solo los índices; y cómo se calcula la distancia con tablas (ADC).",
        """
        Diagrama técnico limpio, fondo blanco, formato 16:9. Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Tipografía sans-serif. Sin decoración.

        PARTE SUPERIOR (codificar), de izquierda a derecha:
        1) Una barra gris con 8 casillas etiquetada "vector x (d = 8, ejemplo)". Se divide con líneas verticales en 4 trozos de 2 casillas, coloreados azul, naranja, verde, gris, con la etiqueta "m = 4 subvectores".
        2) Cuatro cajas pequeñas (una por subvector), cada una con el texto "diccionario de 256 centroides" y una flecha desde el subvector hasta un centroide marcado.
        3) A la derecha, cuatro casillas con números: "17 | 203 | 5 | 88" bajo el título "código PQ = 4 bytes".
        PARTE INFERIOR (buscar con ADC): una query q dividida en los mismos 4 trozos; debajo, 4 tablas pequeñas "T1 … T4" (cada una con 256 valores, mostrar solo tres valores y puntos suspensivos); un recuadro final con la fórmula "score = T1[17] + T2[203] + T3[5] + T4[88]" y la etiqueta "4 accesos a tabla por vector".
        Pie de figura: "d = 1024 con m = 64 → 64 bytes por vector (64× menos que float32)".

        Evita: texto ilegible, números distintos de los indicados, flechas cruzadas, logos, decoración.
        """,
        "Un vector dividido en cuatro subvectores que se reemplazan por cuatro índices de diccionario y se puntúan con tablas",
        """
        x = [x1 x2 | x3 x4 | x5 x6 | x7 x8]      m = 4 subvectores
              ↓        ↓        ↓        ↓       (centroide más cercano en cada diccionario de 256)
        código = [ 17 | 203 | 5 | 88 ]           (4 bytes)
        score(q, x) ≈ T1[17] + T2[203] + T3[5] + T4[88]       Tj[c] = <q_j, centroide_jc>
        """,
    )
    nb.md(r'''> 👀 **Qué debes observar.** La query nunca se comprime: se construyen $m$ tablas de $K$ valores **una vez por query** y cada documento cuesta $m$ lecturas de tabla. La compresión es del lado del índice; la precisión del lado de la query (por eso se llama *asimétrico*).

### Combinar: IVF-PQ y su memoria con FAISS
Las dos ideas se combinan: IVF reduce **cuántos** vectores miras y PQ **cuánto cuesta** mirar cada uno. En FAISS, `IndexIVFPQ` codifica el **residuo** (vector − centroide de su celda), que tiene menos energía y se cuantiza mejor. Veamos el tamaño real serializado de cada familia con el mismo $N$.
''')
    nb.code(r"""
def construye_faiss(clave):
    if clave == "Flat":
        ix = faiss.IndexFlatIP(D)
    elif clave == "IVFFlat":
        ix = faiss.IndexIVFFlat(faiss.IndexFlatIP(D), D, NLIST, faiss.METRIC_INNER_PRODUCT)
    elif clave == "IVFPQ":
        ix = faiss.IndexIVFPQ(faiss.IndexFlatIP(D), D, NLIST, 16, 8, faiss.METRIC_INNER_PRODUCT)
    elif clave == "HNSW":
        ix = faiss.IndexHNSWFlat(D, 16, faiss.METRIC_INNER_PRODUCT); ix.hnsw.efConstruction = 100
    if not ix.is_trained:
        ix.train(X)
    t0 = time.perf_counter(); ix.add(X); return ix, time.perf_counter() - t0

filas, IDX = [], {}
for clave in ("Flat", "IVFFlat", "IVFPQ", "HNSW"):
    ix, t_add = construye_faiss(clave)
    IDX[clave] = ix
    filas.append(dict(indice=clave, MB=tam_indice_MB(ix), bytes_por_vector=tam_indice_MB(ix) * 1e6 / N, seg_construir=t_add))
mem = pd.DataFrame(filas)
display(mem.round(2))
fig, ax = plt.subplots(figsize=(6.4, 3.2))
ax.bar(mem["indice"], mem["bytes_por_vector"], color=["#6B7280", "#1F6FEB", "#2CA02C", "#F28E2B"])
ax.axhline(4 * D, color="k", ls=":"); ax.text(0.02, 4 * D + 4, f"float32 = {4*D} B/vector", fontsize=8)
ax.set_ylabel("bytes por vector (serializado)"); ax.set_title(f"Memoria real por familia · N={N:,}, d={D}")
plt.tight_layout(); plt.show()
""")
    nb.md(r"""> 👀 **Qué debes observar.** `Flat` y `IVFFlat` guardan los vectores completos (≈ $4d$ B). `HNSW` guarda **los vectores más el grafo** (cada nodo guarda sus vecinos): es *más grande* que `Flat`. `IVFPQ` guarda 16 bytes de código + id: ~10× menos. Elegir HNSW es pagar RAM por velocidad; elegir IVF-PQ, pagar recall por RAM.

## 5 · HNSW desde cero (mini)

**HNSW** (Malkov & Yashunin, 2016/2018) es un grafo de proximidad *jerárquico*:
- Cada vector recibe un **nivel máximo** aleatorio $\ell=\lfloor -\ln U\cdot m_L\rfloor$, con $m_L=1/\ln M$. Así $P(\ell\ge l)=M^{-l}$: cada capa tiene $M$ veces menos nodos que la inferior. Nº esperado de capas $\approx\ln N/\ln M$.
- **Búsqueda:** entra por la capa más alta con un nodo de entrada; en cada capa superior hace una **búsqueda voraz** (sigue al vecino más cercano a la query mientras mejore), baja a la capa siguiente con ese nodo y en la **capa 0** hace una búsqueda de haz con lista de tamaño $ef$.
- **Inserción:** igual que buscar para localizar los vecinos en cada capa $\le\ell$ (con `efConstruction`), conectar con $M$ vecinos elegidos por una **heurística** (acepta un candidato $c$ solo si está más cerca de la query que de cualquier vecino ya elegido: favorece vecinos en *direcciones distintas*) y recortar las listas de vecinos que excedan $M$ ($2M$ en la capa 0).
- **Parámetros:** `M` (conectividad: más memoria y recall), `efConstruction` (calidad del grafo, tiempo de construcción), `efSearch` (**el dial de latencia vs recall en consulta**).

Complejidad empírica: $O(\log N)$ saltos. Coste: RAM (vectores + grafo) y construcción lenta; no admite bien borrados.
""")
    nb.code(r"""
import heapq

class _HNSWBusqueda:
    '''Base del HNSW didáctico en NumPy puro: estructura, búsqueda por capa (haz de tamaño ef) y búsqueda jerárquica.
    Distancia L2: con vectores normalizados da el mismo ranking que el producto interno.'''
    def __init__(self, V, M=12, ef_construction=64, seed=SEED):
        self.X, self.n, self.M, self.M0, self.efc = V, len(V), M, 2 * M, ef_construction
        self.ml = 1 / math.log(M)
        self.rng = np.random.default_rng(seed)
        self.enlaces = []                       # enlaces[i][capa] = lista de vecinos
        self.entrada, self.capa_max, self.ndist = -1, -1, 0
    def _d(self, q, ids):
        self.ndist += len(ids)
        return ((self.X[ids] - q) ** 2).sum(1)
    def _busca_capa(self, q, eps, ef, capa, traza=None):
        vis = set(eps)
        d0 = self._d(q, list(eps))
        cand = list(zip(d0, eps)); heapq.heapify(cand)                    # min-heap de candidatos a expandir
        res = [(-d, e) for d, e in zip(d0, eps)]; heapq.heapify(res)       # max-heap de los ef mejores
        while cand:
            d, c = heapq.heappop(cand)
            if d > -res[0][0] and len(res) >= ef:
                break
            if traza is not None:
                traza.append(c)
            nb = [x for x in self.enlaces[c][capa] if x not in vis]
            if not nb:
                continue
            vis.update(nb)
            for dd, e in zip(self._d(q, nb), nb):
                if len(res) < ef or dd < -res[0][0]:
                    heapq.heappush(cand, (dd, e)); heapq.heappush(res, (-dd, e))
                    if len(res) > ef:
                        heapq.heappop(res)
        return sorted((-d, e) for d, e in res)
    def busca(self, q, k=10, ef=50, traza=False):
        ep, tr = [self.entrada], {}
        for capa in range(self.capa_max, 0, -1):
            tr[capa] = []
            ep = [self._busca_capa(q, ep, 1, capa, tr[capa])[0][1]]
        tr[0] = []
        res = self._busca_capa(q, ep, max(ef, k), 0, tr[0])[:k]
        ids = [e for _, e in res]
        return (ids, tr) if traza else ids
""")
    nb.code(r"""
class MiniHNSW(_HNSWBusqueda):
    '''Añade la INSERCIÓN: heurística de selección de vecinos, enlaces bidireccionales y recorte de grado.'''
    def _selecciona(self, cands, M):
        '''Heurística de selección: acepta c si está más cerca de la query que de cualquier vecino ya aceptado.'''
        out = []
        for dq, c in cands:
            if len(out) >= M:
                break
            if all(dq < ((self.X[c] - self.X[o]) ** 2).sum() for o in out):
                out.append(c)
        for dq, c in cands:                                               # completa hasta M si la heurística fue estricta
            if len(out) >= M:
                break
            if c not in out:
                out.append(c)
        return out
    def anade(self, i):
        q = self.X[i]
        nivel = int(-math.log(1 - self.rng.random()) * self.ml)
        self.enlaces.append([[] for _ in range(nivel + 1)])
        if self.entrada < 0:
            self.entrada, self.capa_max = i, nivel
            return
        ep = [self.entrada]
        for capa in range(self.capa_max, nivel, -1):                       # capas altas: búsqueda voraz (ef=1)
            ep = [self._busca_capa(q, ep, 1, capa)[0][1]]
        for capa in range(min(nivel, self.capa_max), -1, -1):
            W = self._busca_capa(q, ep, self.efc, capa)
            vecinos = self._selecciona(W, self.M)
            self.enlaces[i][capa] = list(vecinos)
            for e in vecinos:
                self.enlaces[e][capa].append(i)
                tope = self.M0 if capa == 0 else self.M
                if len(self.enlaces[e][capa]) > tope:                      # recorta con la misma heurística
                    ids = self.enlaces[e][capa]
                    self.enlaces[e][capa] = self._selecciona(sorted(zip(((self.X[ids] - self.X[e]) ** 2).sum(1), ids)), tope)
            ep = [e for _, e in W]
        if nivel > self.capa_max:
            self.entrada, self.capa_max = i, nivel
    def construye(self):
        for i in range(self.n):
            self.anade(i)
        return self

N_MINI = 2000 if FAST_DEV_RUN else 8000
Xm = X[:N_MINI]
GTm = exacto_topk(Q, Xm, 10)
t0 = time.perf_counter(); H = MiniHNSW(Xm, M=12, ef_construction=64).construye(); t_h = time.perf_counter() - t0
niveles = np.array([len(e) for e in H.enlaces])
print(f"mini-HNSW: N={N_MINI:,} construido en {t_h:.1f}s · capas={H.capa_max+1} · nodos por nivel máximo: {np.bincount(niveles)[1:].tolist()}")

filas = []
hf = faiss.IndexHNSWFlat(D, 12, faiss.METRIC_L2); hf.hnsw.efConstruction = 64; hf.add(Xm)
for ef in (10, 20, 40, 80, 160):
    H.ndist = 0
    res = [H.busca(q, 10, ef) for q in Q]
    hf.hnsw.efSearch = ef
    _, I = hf.search(Q, 10)
    filas.append(dict(ef=ef, recall_propio=recall_vs_gt(np.array(res), GTm), recall_faiss=recall_vs_gt(I, GTm), dist_por_query=H.ndist / len(Q),
                      fraccion_del_total=H.ndist / len(Q) / N_MINI))
tab_h = pd.DataFrame(filas)
display(tab_h.round(3))
""")
    nb.code(r"""
fig, axs = plt.subplots(1, 3, figsize=(14, 3.5))
axs[0].plot(tab_h["ef"], tab_h["recall_propio"], "o-", label="mini-HNSW", color="#F28E2B")
axs[0].plot(tab_h["ef"], tab_h["recall_faiss"], "s--", label="FAISS IndexHNSWFlat", color="#1F6FEB")
axs[0].set_xscale("log", base=2); axs[0].set_xlabel("efSearch"); axs[0].set_ylabel("recall@10"); axs[0].set_title("Recall vs efSearch"); axs[0].legend(fontsize=8); axs[0].grid(alpha=.3)
axs[1].plot(100 * tab_h["fraccion_del_total"], tab_h["recall_propio"], "o-", color="#F28E2B")
axs[1].set_xlabel("% de distancias calculadas respecto a fuerza bruta"); axs[1].set_ylabel("recall@10"); axs[1].set_title("Cuánto cuesta cada recall"); axs[1].grid(alpha=.3)
l = np.arange(0, H.capa_max + 1)
obs = np.array([(niveles > i).sum() for i in l])
axs[2].semilogy(l, obs, "o-", label="observado", color="#2CA02C"); axs[2].semilogy(l, N_MINI * 12.0 ** (-l), "k--", label="teoría: N·M^-l")
axs[2].set_xlabel("capa l"); axs[2].set_ylabel("nodos en capas ≥ l"); axs[2].set_title("Distribución de niveles"); axs[2].legend(fontsize=8); axs[2].grid(alpha=.3)
plt.tight_layout(); plt.show()
""")
    nb.md(r"""> 👀 **Qué debes observar.** (1) Tu mini-HNSW y el de FAISS tienen curvas parecidas: **`efSearch` es el dial** de recall/latencia. (2) En el segundo gráfico, alcanzar 0.95+ de recall requiere calcular solo una **fracción de las distancias** de la fuerza bruta (y esa fracción baja al crecer $N$ porque el coste es ≈ logarítmico). (3) El tercer gráfico confirma $P(\ell\ge l)=M^{-l}$: la capa $l$ tiene $\approx N M^{-l}$ nodos; por eso las capas altas son "autopistas" con pocos nodos.

### Ver las capas: HNSW en 2D
Construimos el mismo mini-HNSW sobre 150 puntos 2D y dibujamos las capas y el **recorrido** de una búsqueda: los nodos expandidos en cada capa (círculos rojos) entran por la capa alta y bajan hasta la zona de la query (estrella).
""")
    nb.code(r"""
P2 = (np.random.default_rng(3).normal(size=(150, 2)) * [1.0, 0.7]).astype(np.float32)
H2 = MiniHNSW(P2, M=4, ef_construction=16, seed=7).construye()
q2 = np.array([0.9, 0.5], dtype=np.float32)
ids2, traza2 = H2.busca(q2, k=3, ef=6, traza=True)
capas = H2.capa_max + 1
fig, axs = plt.subplots(1, capas, figsize=(4.2 * capas, 4), sharex=True, sharey=True)
axs = np.atleast_1d(axs)
for capa in range(capas):
    ax = axs[capas - 1 - capa]
    en_capa = [i for i, e in enumerate(H2.enlaces) if len(e) > capa]
    ax.scatter(P2[:, 0], P2[:, 1], s=6, c="#D1D5DB")
    for i in en_capa:
        for j in H2.enlaces[i][capa]:
            ax.plot(*P2[[i, j]].T, c="#1F6FEB", lw=0.5, alpha=.5)
    ax.scatter(P2[en_capa, 0], P2[en_capa, 1], s=22, c="#1F6FEB")
    vis = traza2.get(capa, [])
    ax.scatter(P2[vis, 0], P2[vis, 1], s=55, facecolors="none", edgecolors="#D62728", lw=1.6)
    ax.scatter(*q2, marker="*", s=200, c="#F28E2B", zorder=5)
    ax.set_title(f"capa {capa}" + (" (arriba)" if capa == capas - 1 else " (base)" if capa == 0 else ""), fontsize=10)
plt.suptitle("HNSW en 2D: nodos (azul), nodos expandidos (círculo rojo), query (estrella)", fontsize=10)
plt.tight_layout(); plt.show()
print({f"capa {c}": len(v) for c, v in sorted(traza2.items(), reverse=True)}, "nodos expandidos")
""")
    nb.md(r"""> 👀 **Qué debes observar.** En las capas altas hay pocos nodos y aristas **largas**: la búsqueda se acerca a la zona de la query en unos pocos saltos. En la capa 0 (todos los nodos, aristas cortas) solo se expande un puñado de nodos alrededor de la estrella. Esa es la intuición de $O(\log N)$: la jerarquía hace de **índice de saltos** sobre un grafo local.
""")
    nb.gemini(
        "video", "M14-VID-01", "Recorrido de HNSW por capas",
        "Animación de una búsqueda en HNSW: entrada por la capa superior, descenso voraz capa a capa y búsqueda con lista de candidatos en la capa 0.",
        """
        Video explicativo 16:9, fondo blanco, estilo diagrama técnico limpio. Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280; tipografía sans-serif; ritmo calmado; SIN voz en off ni música; solo texto en pantalla en español (términos técnicos en inglés).

        Composición: tres paneles horizontales apilados que representan las capas 2 (arriba), 1 (centro) y 0 (abajo) de un grafo HNSW. En la capa 2 hay 4 nodos grises con 4 aristas largas; en la capa 1 hay 10 nodos; en la capa 0 hay 40 nodos con muchas aristas cortas. Los nodos de las capas altas están conectados con líneas verticales punteadas a los mismos nodos en la capa de abajo. Una estrella naranja (la consulta) está en la zona derecha de la capa 0.

        Escena 1 (0–4 s): título "HNSW: búsqueda por capas". Aparecen los tres paneles con sus nodos.
        Escena 2 (4–10 s): el punto de entrada (nodo azul oscuro, arriba a la izquierda de la capa 2) se ilumina con la etiqueta "punto de entrada". Se comparan sus vecinos y el algoritmo salta al vecino más cercano a la estrella, resaltando la arista en verde. Texto: "capa 2: búsqueda voraz (ef = 1)".
        Escena 3 (10–15 s): una flecha vertical punteada baja el nodo actual a la capa 1; se repite el salto voraz hasta no poder mejorar. Texto: "capa 1: seguir mejorando".
        Escena 4 (15–24 s): baja a la capa 0; ahora se resalta una lista de candidatos (halo naranja alrededor de 6 nodos cercanos a la estrella) que se va actualizando: entran nodos nuevos y salen los más lejanos. Texto: "capa 0: lista de candidatos de tamaño ef".
        Escena 5 (24–28 s): los 3 nodos finales más cercanos a la estrella se marcan en verde con la etiqueta "top-k". Texto final: "Pocos saltos arriba + exploración local abajo ≈ O(log N)".

        Evita: voz, música, nodos que aparecen y desaparecen sin motivo, texto ilegible, decoración, cambios bruscos de cámara.
        """,
        "Animación de una búsqueda HNSW que desciende por tres capas hasta los vecinos más cercanos",
        """
        capa 2:  (E)────────o        o──────o         E = punto de entrada
                  ↓ salto voraz hacia la consulta ★
        capa 1:  o──o──(o)──o──o──o                     ↓ baja con el mejor nodo
        capa 0:  o-o-o-o-(o)-o-o-o-o-★   lista de candidatos (ef) -> top-k
        """,
        duration="25-30 s",
    )
    nb.md(r"""> 👀 **Qué debes observar.** El tiempo se reparte así: **pocos saltos en las capas altas** (guía gruesa), **mucha exploración en la capa 0** (precisión). `ef` controla cuántos candidatos se mantienen en esa exploración: más `ef` = más recall = más distancias.
""")
    # ───────────────────────────── 6. Vamana / DiskANN ─────────────────────────────
    nb.md(r"""## 6 · Vamana y DiskANN: grafos pensados para el SSD

HNSW exige **todo en RAM**. Para $10^9$ vectores eso son terabytes. **DiskANN** (Subramanya et al., NeurIPS 2019) resuelve el problema de dos maneras:

1. **Un grafo distinto, Vamana**, con grado acotado $R$ y **pocos saltos** (cada salto es una lectura aleatoria de SSD, ≈ 100 µs en NVMe: el número de saltos *es* la latencia).
2. **Arquitectura híbrida:** en RAM solo los **códigos PQ** de todos los vectores (para guiar la búsqueda con distancias aproximadas); en SSD, para cada nodo, su **vector completo y su lista de vecinos** juntos en un sector. La búsqueda por haz (*beam search*) lee `W` sectores por ronda y re-ordena con los vectores completos recién leídos.

**Construcción de Vamana.** Parte de un grafo aleatorio $R$-regular y de un nodo de entrada (*medoide*). Para cada punto $p$ (en orden aleatorio): (1) ejecuta `GreedySearch` desde el medoide hacia $p$ y guarda el conjunto $V$ de nodos **visitados**; (2) fija los vecinos de $p$ con **RobustPrune**$(p,V,\alpha,R)$; (3) añade las aristas inversas y recorta con RobustPrune los nodos que se pasan de grado $R$. Se hacen **dos pasadas**, primero con $\alpha=1$ y luego con $\alpha>1$ (p. ej. 1.2).

**RobustPrune.** Toma el candidato $p^\*$ más cercano a $p$, lo añade a los vecinos y **elimina** todos los $p'$ que quedan "cubiertos" por él: $\alpha\cdot d(p^\*,p')\le d(p,p')$. Con $\alpha=1$ es la poda tipo HNSW/RNG (solo aristas "útiles"); con $\alpha>1$ se conservan **aristas más largas**, lo que reduce el diámetro del grafo y por tanto el nº de saltos (a costa de más aristas por nodo).

Otras piezas: **FreshDiskANN** (Singh et al., 2021) soporta inserciones y borrados en streaming; **Filtered-DiskANN** añade filtros por etiqueta en la construcción del grafo.
""")
    nb.code(r"""
class Vamana:
    '''Vamana didáctico (distancia coseno sobre vectores normalizados).'''
    def __init__(self, V, R=16, L=48, alpha=1.2, seed=SEED):
        self.X, self.n, self.R, self.ndist = V, len(V), R, 0
        rng = np.random.default_rng(seed)
        self.g = [list(rng.choice(self.n, R, replace=False)) for _ in range(self.n)]     # grafo aleatorio R-regular
        self.s = int(np.argmin(((V - V.mean(0)) ** 2).sum(1)))                          # medoide aproximado = punto más cercano a la media
        for a in (1.0, alpha):                                                           # dos pasadas: alpha=1 y alpha>1
            for p in rng.permutation(self.n):
                visitados = self.voraz(V[p], L)[1]
                visitados.discard(int(p))
                self.poda(int(p), visitados, a)
                for j in self.g[p]:
                    if p not in self.g[j]:
                        self.g[j].append(int(p))
                        if len(self.g[j]) > R:
                            self.poda(j, set(self.g[j]), a)
        self.ndist = 0
    def voraz(self, q, L):
        '''GreedySearch: devuelve (candidatos ordenados, conjunto de nodos expandidos = lecturas de página).'''
        vis, cand, expandidos = {self.s}, {self.s: 1 - self.X[self.s] @ q}, set()
        self.ndist += 1
        while True:
            pend = [(d, c) for c, d in cand.items() if c not in expandidos]
            if not pend:
                break
            _, c = min(pend)
            expandidos.add(c)
            nb = [x for x in self.g[c] if x not in vis]
            if nb:
                vis.update(nb); self.ndist += len(nb)
                for x, d in zip(nb, 1 - self.X[nb] @ q):
                    cand[x] = d
            if len(cand) > L:
                cand = dict(sorted(cand.items(), key=lambda kv: kv[1])[:L])
        return sorted(cand, key=cand.get), expandidos
    def poda(self, p, V, alpha):
        '''RobustPrune: añade el más cercano y elimina a los que quedan cubiertos (alpha * d(p*, p') <= d(p, p')).'''
        V = list(V)
        d = 1 - self.X[V] @ self.X[p]
        orden = np.argsort(d); V = [V[i] for i in orden]; d = d[orden]
        salida, vivo = [], np.ones(len(V), bool)
        for i in range(len(V)):
            if not vivo[i]:
                continue
            salida.append(V[i])
            if len(salida) >= self.R:
                break
            dd = 1 - self.X[V[i + 1:]] @ self.X[V[i]]
            vivo[i + 1:] &= ~(alpha * dd <= d[i + 1:])
        self.g[p] = salida
    def busca(self, q, k=10, L=30):
        res, lecturas = self.voraz(q, L)
        return res[:k], len(lecturas)

N_V = 1500 if FAST_DEV_RUN else 5000
Xv, GTv = X[:N_V], exacto_topk(Q, X[:N_V], 10)
filas = []
for alpha in (1.0, 1.2):
    t0 = time.perf_counter(); V_ = Vamana(Xv, R=16, L=48, alpha=alpha); t_b = time.perf_counter() - t0
    grado = np.mean([len(v) for v in V_.g])
    for L in (10, 20, 40, 80):
        res = [V_.busca(q, 10, L) for q in Q]
        filas.append(dict(alpha=alpha, L=L, recall=recall_vs_gt(np.array([r[0] for r in res]), GTv), lecturas_por_query=np.mean([r[1] for r in res]), grado_medio=grado, seg_construir=t_b))
# referencia: nodos expandidos por el mini-HNSW (capas altas + capa 0)
Hv = MiniHNSW(Xv, M=12, ef_construction=64).construye()
for ef in (10, 20, 40, 80):
    out = [Hv.busca(q, 10, ef, traza=True) for q in Q]
    filas.append(dict(alpha=np.nan, L=ef, recall=recall_vs_gt(np.array([o[0] for o in out]), GTv),
                      lecturas_por_query=np.mean([sum(len(t) for t in o[1].values()) for o in out]), grado_medio=np.mean([len(e[0]) for e in Hv.enlaces]), seg_construir=np.nan))
tab_v = pd.DataFrame(filas)
tab_v["algoritmo"] = np.where(tab_v["alpha"].isna(), "mini-HNSW", "Vamana α=" + tab_v["alpha"].astype(str))
display(tab_v.round(3))
""")
    nb.code(r"""
T_LECTURA_MS = 0.1      # SUPUESTO: ≈ 100 µs por lectura aleatoria de 4 KB en NVMe (ajústalo a tu disco); lecturas secuenciales por ronda de beam W=1
fig, axs = plt.subplots(1, 2, figsize=(11.5, 3.6))
for alg, g in tab_v.groupby("algoritmo"):
    axs[0].plot(g["lecturas_por_query"], g["recall"], "o-", label=alg)
axs[0].set_xlabel("nodos expandidos por query (≈ lecturas de SSD)"); axs[0].set_ylabel("recall@10"); axs[0].set_title("Recall vs lecturas de página"); axs[0].legend(fontsize=8); axs[0].grid(alpha=.3)
for alg, g in tab_v.groupby("algoritmo"):
    axs[1].plot(g["lecturas_por_query"] * T_LECTURA_MS, g["recall"], "o-", label=alg)
axs[1].set_xlabel(f"latencia estimada de I/O (ms) con {T_LECTURA_MS*1e3:.0f} µs por lectura"); axs[1].set_ylabel("recall@10"); axs[1].set_title("Si el grafo viviera en SSD (estimación)"); axs[1].grid(alpha=.3)
plt.tight_layout(); plt.show()
""")
    nb.md(r"""> 👀 **Qué debes observar.** (1) Vamana alcanza recalls comparables al mini-HNSW con un número de **nodos expandidos** del mismo orden: el grafo es de calidad similar. (2) En esta escala diminuta (1 500 nodos) la diferencia entre $\alpha=1$ y $\alpha=1.2$ es pequeña; en el paper el efecto de $\alpha>1$ se nota en colecciones grandes, donde acorta el recorrido. (3) A la derecha, el eje es **latencia de I/O estimada** con un supuesto explícito de 100 µs por lectura: es lo que realmente paga DiskANN, y por eso minimiza lecturas, no distancias. (4) Un diseño con PQ en RAM evita leer los vecinos "malos": se usa la distancia aproximada para decidir qué sector leer.
""")
    nb.gemini(
        "imagen", "M14-IMG-03", "Arquitectura de DiskANN: grafo en SSD y PQ en RAM",
        "Qué vive en RAM (códigos PQ), qué vive en SSD (vector completo + vecinos de cada nodo) y cómo una búsqueda por haz lee pocos sectores.",
        """
        Diagrama técnico limpio, fondo blanco, formato 16:9. Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Tipografía sans-serif. Sin decoración.

        Dos zonas verticales separadas por una línea punteada.
        IZQUIERDA, azul, título "RAM (pequeña)": una tabla con 8 filas "id 0 … id 7" y una columna "código PQ (m bytes)" con ejemplos "[17 203 5 88]" en las dos primeras filas y puntos suspensivos. Debajo, la nota: "distancias aproximadas para decidir qué sector leer".
        DERECHA, naranja, título "SSD (grande)": una fila de 6 rectángulos alargados llamados "sector 4 KB", cada uno con dos partes: "vector completo" (barra larga) y "vecinos: [a, b, c, d]" (4 casillas).
        Entre ambas zonas, flechas: 1) desde un cuadro verde "consulta q" hacia la tabla PQ, con la etiqueta "1. puntuar vecinos con PQ"; 2) desde la tabla PQ hacia 2 sectores del SSD con la etiqueta "2. leer solo los W mejores sectores (beam search)"; 3) desde esos sectores hacia una caja verde "3. re-ordenar con vectores completos" y luego "top-k".
        Pie de figura: "Latencia ≈ nº de lecturas de SSD · RAM ≈ N × m bytes".

        Evita: texto ilegible, más de 6 sectores, números distintos de los indicados, logos, decoración.
        """,
        "Esquema con los códigos PQ en RAM, los sectores con vector y vecinos en SSD, y el flujo de búsqueda por haz",
        """
        RAM:  id0 [17 203 5 88]            SSD: [sector: vector completo | vecinos a b c d] x N
              id1 [ 9  44 120 3]    ←→      1) q puntúa vecinos con PQ  2) lee W sectores  3) re-ordena con vectores completos
        RAM ≈ N·m bytes · latencia ≈ nº de lecturas de SSD
        """,
    )
    nb.md(r"""> 👀 **Qué debes observar.** Dos cuellos de botella distintos: la **RAM** escala con $N\cdot m$ (bytes de PQ), la **latencia** con el número de lecturas. DiskANN permite que $N$ crezca 10–100× más que lo que cabe en RAM manteniendo latencias de milisegundos.

## 7 · ScaNN: cuantización *anisótropa*

La PQ minimiza el error de reconstrucción $\|x-\tilde x\|^2$. Pero en búsqueda por producto interno (MIPS) lo que importa es el error del **score** $\langle q,x\rangle$, y ese error no afecta por igual a todos los pares: para los vecinos que **sí** serán top-$k$ (los de score alto), la query está casi alineada con $x$. Descomponiendo el residuo $r=x-\tilde x$ en la componente **paralela** $r_\parallel$ (en la dirección de $x$) y la **ortogonal** $r_\perp$, el error de score proviene sobre todo de $r_\parallel$. ScaNN (Guo et al., ICML 2020) minimiza una pérdida **ponderada**
$$\ell(x,\tilde x)=h_\parallel\,\|r_\parallel\|^2+h_\perp\,\|r_\perp\|^2,\qquad h_\parallel>h_\perp,$$
con $h_\parallel/h_\perp$ derivado del umbral de score que se quiere preservar y de la dimensión. Resultado: códigos que **sacrifican error ortogonal** (que casi no altera el ranking) para **proteger los scores altos**. Es la base de la búsqueda vectorial de Google (`scann`: árbol/particionado + *asymmetric hashing* anisótropo + re-ranking).
""")
    nb.code(r"""
# Ejemplo numérico mínimo: dos palabras de código candidatas para x = (1, 0) y consultas alineadas con x
x = np.array([1.0, 0.0])
c1, c2 = np.array([0.8, 0.0]), np.array([1.0, 0.25])          # c1 = error PARALELO 0.2 · c2 = error ORTOGONAL 0.25
def error(c):
    r = x - c; r_par = (r @ x) / (x @ x) * x; return r_par, r - r_par
for nombre, c in (("c1 (error paralelo)", c1), ("c2 (error ortogonal)", c2)):
    rp, ro = error(c)
    mse = float((rp ** 2).sum() + (ro ** 2).sum())
    aniso = 4 * float((rp ** 2).sum()) + float((ro ** 2).sum())                  # h_par/h_perp = 4 (ejemplo)
    print(f"{nombre}: MSE = {mse:.4f} · pérdida anisótropa (η=4) = {aniso:.4f} · score con q=(1,0): <q,c> = {c[0]:.2f} (verdadero: 1.00)")
elige_mse = "c1" if ((error(c1)[0] ** 2).sum() + (error(c1)[1] ** 2).sum()) < ((error(c2)[0] ** 2).sum() + (error(c2)[1] ** 2).sum()) else "c2"
elige_aniso = "c1" if (4 * (error(c1)[0] ** 2).sum() + (error(c1)[1] ** 2).sum()) < (4 * (error(c2)[0] ** 2).sum() + (error(c2)[1] ** 2).sum()) else "c2"
print(f"PQ clásica (MSE) elige {elige_mse}; ScaNN (η=4) elige {elige_aniso}")
fig, ax = plt.subplots(figsize=(4.6, 3.8))
ax.annotate("", xy=x, xytext=(0, 0), arrowprops=dict(arrowstyle="->", color="#1F6FEB", lw=2)); ax.text(0.96, -0.08, "x", color="#1F6FEB")
for c, col, et in ((c1, "#F28E2B", "c1"), (c2, "#2CA02C", "c2")):
    ax.scatter(*c, c=col, s=60); ax.text(c[0] + 0.02, c[1] + 0.02, et, color=col)
    ax.plot([x[0], c[0]], [x[1], c[1]], ls="--", c=col, lw=1)
ax.set_xlim(0.6, 1.15); ax.set_ylim(-0.15, 0.4); ax.set_aspect("equal"); ax.grid(alpha=.3); ax.set_title("Residuo paralelo (c1) vs ortogonal (c2)")
plt.tight_layout(); plt.show()
""")
    nb.md(r"""> 👀 **Qué debes observar.** La PQ clásica prefiere $c_1$ (menor error cuadrático total) pero $c_1$ **subestima el score** de las consultas alineadas con $x$ (0.80 en vez de 1.00); la pérdida anisótropa prefiere $c_2$, que conserva el score exacto aunque su error total sea mayor. En la práctica el efecto es sutil y se mide con recall del top-$k$ de MIPS; ScaNN lo combina con particionado y re-ranking.

La librería oficial se instala con `pip install scann` (solo Linux x86). La celda siguiente la usa si está disponible (si no, la omite):
""")
    nb.code(r"""
try:
    import scann
    buscador = (scann.scann_ops_pybind.builder(X, 10, "dot_product")
                .tree(num_leaves=NLIST, num_leaves_to_search=16, training_sample_size=min(N, 10000))
                .score_ah(2, anisotropic_quantization_threshold=0.2)
                .reorder(100).build())
    ids, _ = buscador.search_batched(Q)
    print("ScaNN recall@10:", round(recall_vs_gt(np.asarray(ids), GT), 3))
except Exception as e:
    print("scann no disponible en este entorno:", type(e).__name__, "· (opcional: pip install scann en Linux x86)")
""")

    # ───────────────────────────── 8. RaBitQ ─────────────────────────────
    nb.md(r"""## 8 · Cuantización binaria con garantías: RaBitQ

El módulo 12 mostró la binaria "ingenua" ($\text{sign}(x)$). **RaBitQ** (Gao & Long, SIGMOD 2024) la convierte en un método con **estimador insesgado y cota de error**: $D$ bits por vector y un error $O(1/\sqrt D)$ con alta probabilidad.

**Construcción** (por celda IVF con centroide $c$; aquí un único centroide global = la media):
1. Residuo normalizado: $o=\dfrac{x-c}{\|x-c\|}$ (guardando $\|x-c\|$ y el escalar $\langle\bar o,o\rangle$ de abajo).
2. Se aplica una **rotación ortogonal aleatoria** $P$ y se toma el vértice del hipercubo más cercano: $b=\mathbb{1}[P^\top o>0]$, $\bar o=P\,\dfrac{2b-1}{\sqrt D}$ (un vector unitario). Solo se guarda $b$ ($D$ bits).
3. **Estimador del producto interno** con la query residual normalizada $q_r$:
$$\langle o,q_r\rangle\;\approx\;\frac{\langle\bar o,q_r\rangle}{\langle\bar o,o\rangle}$$
El numerador se calcula con operaciones de bits sobre $b$ (la query rotada); el denominador es un **factor de corrección** precomputado por vector que hace el estimador **insesgado** (sin él, la binaria "ingenua" subestima sistemáticamente los productos internos altos). La distancia se reconstruye con $\|x-q\|^2=\|x-c\|^2+\|q-c\|^2-2\|x-c\|\|q-c\|\langle o,q_r\rangle$.

**Extended RaBitQ** (2409.09913) generaliza a más de 1 bit por dimensión. En la práctica los sistemas usan el estimador para filtrar y **re-puntúan** con vectores completos (como en el rescoring del módulo 12).
""")
    nb.code(r"""
def rabitq_ajusta(V, seed=SEED):
    D_ = V.shape[1]
    c = V.mean(0)
    P, _ = np.linalg.qr(np.random.default_rng(seed).normal(size=(D_, D_)))             # rotación ortogonal aleatoria
    R_ = V - c; nr = np.linalg.norm(R_, axis=1); o = R_ / nr[:, None]
    z = o @ P                                                                          # P^T o
    bits = z > 0
    ip = (z * (2 * bits - 1)).sum(1) / math.sqrt(D_)                                    # <obar, o>: factor de corrección
    return dict(c=c, P=P, bits=bits, nr=nr, ip=ip, D=D_, o=o)

def rabitq_ip(st, q):
    qr = q - st["c"]; nq = np.linalg.norm(qr)
    zq = (qr / nq) @ st["P"]
    return ((2 * st["bits"] - 1) @ zq) / math.sqrt(st["D"]) / st["ip"], nq            # estimador insesgado de <o, q_r>

def sign_ingenuo(st, q):
    qr = (q - st["c"]) / np.linalg.norm(q - st["c"])
    return (np.sign(st["o"]) / math.sqrt(st["D"])) @ qr                               # sign(o)/sqrt(D) sin rotación ni corrección

rb = rabitq_ajusta(X)
ratios_rq, ratios_ing, errores = [], [], []
for q in Q[:100]:
    est, nq = rabitq_ip(rb, q)
    real = rb["o"] @ ((q - rb["c"]) / nq)
    top = np.argsort(-real)[:20]                                                       # los vecinos que importan: los de producto interno alto
    ratios_rq.append(np.mean(est[top] / real[top])); ratios_ing.append(np.mean(sign_ingenuo(rb, q)[top] / real[top]))
    errores.append(np.std(est - real))
print(f"estimado/real en los 20 mejores vecinos: RaBitQ = {np.mean(ratios_rq):.3f} · sign ingenuo = {np.mean(ratios_ing):.3f}  (1.0 = insesgado)")

# Error vs dimensión: debe escalar como 1/sqrt(D)
dims = [32, 64, 128, 256, 512]
err_d = []
for d_ in dims:
    Xd, Qd = genera_vectores(2000, d_, nq=20)
    s = rabitq_ajusta(Xd); e = []
    for q in Qd:
        est, nq = rabitq_ip(s, q); e.append(np.std(est - s["o"] @ ((q - s["c"]) / nq)))
    err_d.append(np.mean(e))
fig, axs = plt.subplots(1, 3, figsize=(14, 3.6))
q = Q[0]; est, nq = rabitq_ip(rb, q); real = rb["o"] @ ((q - rb["c"]) / nq)
axs[0].scatter(real[:1500], est[:1500], s=4, alpha=.5, c="#2CA02C", label="RaBitQ"); axs[0].scatter(real[:1500], sign_ingenuo(rb, q)[:1500], s=4, alpha=.4, c="#F28E2B", label="sign ingenuo")
lim = [real.min(), real.max()]; axs[0].plot(lim, lim, "k--", lw=.8); axs[0].set_xlabel("<o, q> real"); axs[0].set_ylabel("estimado"); axs[0].set_title("Estimador vs valor real (una query)"); axs[0].legend(fontsize=8)
axs[1].bar(["RaBitQ", "sign ingenuo"], [np.mean(ratios_rq), np.mean(ratios_ing)], color=["#2CA02C", "#F28E2B"]); axs[1].axhline(1, color="k", ls="--"); axs[1].set_ylabel("estimado / real (top-20)"); axs[1].set_title("Sesgo en los vecinos que importan")
axs[2].loglog(dims, err_d, "o-", color="#1F6FEB", label="error medido"); axs[2].loglog(dims, err_d[0] * np.sqrt(dims[0] / np.array(dims)), "k--", label="∝ 1/√D")
axs[2].set_xlabel("dimensión D"); axs[2].set_ylabel("desviación del error"); axs[2].set_title("El error baja como 1/√D"); axs[2].legend(fontsize=8); axs[2].grid(alpha=.3, which="both")
plt.tight_layout(); plt.show()
""")
    nb.md(r"""> 👀 **Qué debes observar.** (1) A la izquierda, RaBitQ se agrupa en torno a la diagonal; el *sign* ingenuo queda **por debajo** (escala comprimida). (2) En el centro, sobre los vecinos que importan, el ingenuo estima ≈ 0.7–0.8 del valor real (sesgo) mientras RaBitQ ≈ 1.0 (insesgado): eso es lo que arregla la división por $\langle\bar o,o\rangle$. (3) A la derecha, la desviación del error cae como $1/\sqrt D$ (recta de pendiente −1/2 en log-log): **más dimensiones = mejor estimación con 1 bit por dimensión**, lo contrario de lo que pasa en PQ. Esa propiedad hace atractiva la binaria para embeddings de 768–3072 dimensiones.

> 🏭 **Adopción (fuentes):** Elastic describe su *Better Binary Quantization* (BBQ, Elasticsearch 8.16) como construido sobre ideas de RaBitQ, con diferencias (un único centroide, sin rotación aleatoria del libro de códigos); Milvus informa soporte de RaBitQ desde la 2.6 y haber contribuido una versión optimizada a FAISS. Son afirmaciones de cada proyecto: verifica la versión que uses.

## 9 · Búsqueda filtrada: el problema abierto de la producción

Políglota necesita consultas como «solo documentación en español de la versión 3.x». Tres estrategias:

| Estrategia | Cómo | Problema |
|---|---|---|
| **Post-filtro** | buscar top-$k'$ ($k'\gg k$) y filtrar | si el filtro es muy selectivo, no queda nada en el top-$k'$ |
| **Pre-filtro** | construir la lista permitida y hacer **fuerza bruta** sobre ella | exacto, pero el coste crece con $s\cdot N$ ($s$ = selectividad) |
| **Filtro dentro del grafo** | ignorar al expandir los nodos no permitidos | el subgrafo permitido puede quedar **desconectado**: recall cae con $s$ pequeño |

ACORN (Patel et al., 2024) y Filtered-DiskANN atacan el problema modificando la construcción del grafo; los motores suelen **elegir la estrategia según la selectividad** estimada.
""")
    nb.code(r"""
rng = np.random.default_rng(SEED)
atributo = rng.random(N)                                   # atributo uniforme: selectividad = fracción permitida
hnsw = faiss.IndexHNSWFlat(D, 16, faiss.METRIC_INNER_PRODUCT); hnsw.hnsw.efConstruction = 100; hnsw.add(X)
EF, SOBREMUESTREO = 64, 10
filas = []
for sel in (0.5, 0.2, 0.05, 0.01, 0.002):
    ok = np.where(atributo < sel)[0]
    gt_f = ok[exacto_topk(Q, X[ok], 10)] if len(ok) > 10 else None
    if gt_f is None:
        continue
    # (a) post-filtro: top-(10*sobremuestreo) y quedarse con los permitidos
    hnsw.hnsw.efSearch = max(EF, 10 * SOBREMUESTREO)
    _, I = hnsw.search(Q, 10 * SOBREMUESTREO)
    permitido = set(ok.tolist())
    post = [[x for x in fila if x in permitido][:10] for fila in I]
    # (b) filtro dentro del grafo
    p = faiss.SearchParametersHNSW(); p.efSearch = EF; p.sel = faiss.IDSelectorBatch(ok)
    t0 = time.perf_counter(); _, I2 = hnsw.search(Q, 10, params=p); t_in = (time.perf_counter() - t0) / len(Q) * 1e3
    # (c) pre-filtro: fuerza bruta sobre los permitidos
    sub = np.ascontiguousarray(X[ok])
    t0 = time.perf_counter(); [np.argpartition(-(sub @ q), 10)[:10] for q in Q]; t_pre = (time.perf_counter() - t0) / len(Q) * 1e3   # incluye la selección top-k
    filas.append(dict(selectividad=sel, n_permitidos=len(ok), recall_post=recall_vs_gt(np.array([r + [-1] * (10 - len(r)) for r in post]), gt_f),
                      recall_en_grafo=recall_vs_gt(I2, gt_f), recall_pre=1.0, ms_en_grafo=t_in, ms_prefiltro=t_pre))
tab_f = pd.DataFrame(filas)
display(tab_f.round(3))
fig, axs = plt.subplots(1, 2, figsize=(11, 3.5))
axs[0].semilogx(tab_f["selectividad"], tab_f["recall_post"], "o-", label=f"post-filtro (x{SOBREMUESTREO})", color="#F28E2B")
axs[0].semilogx(tab_f["selectividad"], tab_f["recall_en_grafo"], "s-", label="filtro dentro del grafo", color="#1F6FEB")
axs[0].semilogx(tab_f["selectividad"], tab_f["recall_pre"], "^-", label="pre-filtro (exacto)", color="#2CA02C")
axs[0].set_xlabel("selectividad (fracción permitida)"); axs[0].set_ylabel("recall@10 vs exacto filtrado"); axs[0].set_title("El recall se rompe con filtros selectivos"); axs[0].legend(fontsize=8); axs[0].grid(alpha=.3, which="both")
axs[1].loglog(tab_f["selectividad"], tab_f["ms_prefiltro"], "^-", color="#2CA02C", label="pre-filtro (∝ s·N)")
axs[1].loglog(tab_f["selectividad"], tab_f["ms_en_grafo"], "s-", color="#1F6FEB", label="en el grafo")
axs[1].set_xlabel("selectividad"); axs[1].set_ylabel("ms por query"); axs[1].set_title("Latencia"); axs[1].legend(fontsize=8); axs[1].grid(alpha=.3, which="both")
plt.tight_layout(); plt.show()
""")
    nb.md(r"""> 👀 **Qué debes observar.** (1) Con filtros poco selectivos (50 %) todo funciona. (2) Al bajar la selectividad, el **post-filtro** colapsa (no hay suficientes permitidos en el top-100) y el **filtro dentro del grafo** también pierde recall (el subgrafo permitido se desconecta). (3) El **pre-filtro** es exacto y su coste *baja* con la selectividad (menos vectores que escanear): para filtros muy selectivos es **la mejor opción**. Regla de ingeniería: estimar la selectividad y elegir estrategia (pre-filtro si $s\cdot N$ es pequeño; filtro en grafo si es moderado; post-filtro solo si $s$ es alto).

## 10 · FAISS en uso real: barrer configuraciones y elegir con un SLA

El flujo de trabajo de un ingeniero de search: (1) fijar el **SLA** (p. ej. recall@10 ≥ 0.95, p99 ≤ 5 ms), (2) barrer familias y parámetros, (3) quedarse con la frontera de Pareto y (4) elegir el punto que cumple el SLA con **menos memoria**. `index_factory` describe una configuración en una cadena (`"IVF141,PQ16"`, `"HNSW16"`, `"IVF141,Flat"`).
""")
    nb.code(r"""
def barre(familia, construir, parametros, aplica):
    ix = construir()
    if not ix.is_trained:
        ix.train(X)
    t0 = time.perf_counter(); ix.add(X); t_b = time.perf_counter() - t0
    mb = tam_indice_MB(ix); out = []
    for pm in parametros:
        aplica(ix, pm)
        _, I = ix.search(Q, 10)
        p50, p99, qps = mide_latencia(lambda q: ix.search(q[None], 10), Q[:100])
        out.append(dict(familia=familia, param=pm, recall=recall_vs_gt(I, GT), p50_ms=p50, p99_ms=p99, QPS=qps, MB=mb, seg_construir=t_b))
    return out

_MANTENER_VIVOS = []

def mk_ivfpq_refine():
    base = faiss.IndexIVFPQ(faiss.IndexFlatIP(D), D, NLIST, 16, 8, faiss.METRIC_INNER_PRODUCT)
    ix = faiss.IndexRefineFlat(base)
    _MANTENER_VIVOS.append(base)                               # FAISS no es dueño del índice base: hay que mantener la referencia
    return ix

filas = []
filas += barre("IVF-Flat", lambda: faiss.IndexIVFFlat(faiss.IndexFlatIP(D), D, NLIST, faiss.METRIC_INNER_PRODUCT), [1, 2, 4, 8, 16, 32],
               lambda ix, p: setattr(ix, "nprobe", p))
filas += barre("IVF-PQ16", lambda: faiss.IndexIVFPQ(faiss.IndexFlatIP(D), D, NLIST, 16, 8, faiss.METRIC_INNER_PRODUCT), [4, 8, 16, 32, 64],
               lambda ix, p: setattr(ix, "nprobe", p))
filas += barre("IVF-PQ16 + refine x10", mk_ivfpq_refine, [4, 8, 16, 32],
               lambda ix, p: (setattr(faiss.extract_index_ivf(ix.base_index), "nprobe", p), setattr(ix, "k_factor", 10)))
filas += barre("HNSW16", lambda: (lambda h: (setattr(h.hnsw, "efConstruction", 100), h)[1])(faiss.IndexHNSWFlat(D, 16, faiss.METRIC_INNER_PRODUCT)),
               [8, 16, 32, 64, 128, 256], lambda ix, p: setattr(ix.hnsw, "efSearch", p))
barrido = pd.DataFrame(filas)
display(barrido.round(3).head(8))
""")
    nb.code(r"""
colores = {"IVF-Flat": "#1F6FEB", "IVF-PQ16": "#2CA02C", "IVF-PQ16 + refine x10": "#9467BD", "HNSW16": "#F28E2B"}
fig, axs = plt.subplots(1, 2, figsize=(12, 4))
for fam, g in barrido.groupby("familia"):
    axs[0].plot(g["p50_ms"], g["recall"], "o-", label=f"{fam} ({g['MB'].iloc[0]:.1f} MB)", color=colores[fam])
axs[0].axhline(0.95, color="k", ls=":"); axs[0].text(axs[0].get_xlim()[0], 0.955, " SLA recall ≥ 0.95", fontsize=8)
axs[0].set_xscale("log"); axs[0].set_xlabel("latencia p50 por query (ms, escala log)"); axs[0].set_ylabel("recall@10"); axs[0].set_title("Recall vs latencia (leyenda: memoria del índice)")
axs[0].legend(fontsize=8); axs[0].grid(alpha=.3, which="both")
ok = barrido[barrido["recall"] >= 0.95]
for fam, g in barrido.groupby("familia"):
    axs[1].scatter(g["MB"], g["p99_ms"], s=30 + 300 * g["recall"] ** 8, alpha=.6, color=colores[fam], label=fam)
axs[1].set_xscale("log"); axs[1].set_yscale("log"); axs[1].set_xlabel("memoria del índice (MB)"); axs[1].set_ylabel("p99 (ms)"); axs[1].set_title("Memoria vs p99 (tamaño = recall)"); axs[1].grid(alpha=.3, which="both")
plt.tight_layout(); plt.show()
if len(ok):
    mejor = ok.sort_values(["MB", "p99_ms"]).iloc[0]
    print(f"Con SLA recall≥0.95, la config de menor memoria es {mejor['familia']} (param={mejor['param']}): recall={mejor['recall']:.3f}, p99={mejor['p99_ms']:.3f} ms, {mejor['MB']:.1f} MB")
else:
    print("Ninguna configuración llega a recall 0.95 en este barrido: amplía los parámetros.")
""")
    nb.md(r"""> 👀 **Qué debes observar.** (1) Cada familia traza **su propia curva**: IVF-PQ ocupa ≈ 10× menos memoria pero **se estanca en un recall bajo** (la compresión introduce un error que más `nprobe` no arregla); IVF-PQ + *refine* devuelve el recall perdido a cambio de guardar los vectores completos (que pueden vivir en disco). (2) **Sorpresa honesta:** en esta escala diminuta ($N=20\,000$) y con estos datos poco estructurados, IVF-Flat suele igualar o superar a HNSW en latencia a recall ≈ 0.95. Los benchmarks públicos (*ann-benchmarks*, Aumüller et al.) muestran que los grafos tienden a dominar a recall alto en colecciones **grandes**, porque su coste crece ≈ logarítmicamente con $N$ y el de IVF ≈ con $\sqrt N$: **no extrapoles de $N$ pequeño; mide a tu escala**. (3) Con el mismo SLA de recall, la configuración ganadora depende de qué restricción pesa más: latencia, memoria o tiempo de construcción (HNSW tarda órdenes de magnitud más en construirse que IVF aquí). Tamaño de la burbuja del segundo gráfico: recall.

### La dificultad la pone el dato
Los parámetros óptimos dependen de la **estructura de los vectores**. Mismas configuraciones, tres conjuntos con distinta anisotropía (`decay`): casi isótropo (difícil), tal como los usamos, y muy anisótropo (los embeddings reales suelen tener espectros fuertemente decrecientes).
""")
    nb.code(r"""
filas = []
for decay in (0.0, 0.2, 1.0):
    Xd, Qd = genera_vectores(N, D, decay=decay, seed=1)
    gt_d = exacto_topk(Qd, Xd, 10)
    ivf_ = faiss.IndexIVFFlat(faiss.IndexFlatIP(D), D, NLIST, faiss.METRIC_INNER_PRODUCT); ivf_.train(Xd); ivf_.add(Xd); ivf_.nprobe = 8
    hn_ = faiss.IndexHNSWFlat(D, 16, faiss.METRIC_INNER_PRODUCT); hn_.hnsw.efConstruction = 100; hn_.add(Xd); hn_.hnsw.efSearch = 32
    pq_ = faiss.IndexIVFPQ(faiss.IndexFlatIP(D), D, NLIST, 16, 8, faiss.METRIC_INNER_PRODUCT); pq_.train(Xd); pq_.add(Xd); pq_.nprobe = 8
    filas.append(dict(decay=decay, IVF_nprobe8=recall_vs_gt(ivf_.search(Qd, 10)[1], gt_d), HNSW_ef32=recall_vs_gt(hn_.search(Qd, 10)[1], gt_d),
                      IVFPQ16_nprobe8=recall_vs_gt(pq_.search(Qd, 10)[1], gt_d)))
sens = pd.DataFrame(filas).set_index("decay")
display(sens.round(3))
sens.plot(kind="bar", figsize=(7, 3.4), color=["#1F6FEB", "#F28E2B", "#2CA02C"]); plt.ylabel("recall@10"); plt.title("Mismos parámetros, datos distintos"); plt.xticks(rotation=0); plt.grid(alpha=.3, axis="y")
plt.tight_layout(); plt.show()
""")
    nb.md(r"""> 👀 **Qué debes observar.** Con la **misma** configuración el recall cambia mucho entre conjuntos: IVF y HNSW **mejoran** cuando los datos son más anisótropos (los vecinos se separan mejor), mientras IVF-PQ **empeora** (las diferencias entre vecinos son pequeñas frente al error de cuantización; sin *refine* se nota). Los parámetros no se transfieren entre datasets. Un barrido hecho con vectores sintéticos o de otro modelo **no sirve** para fijar los parámetros de producción: vuelve a medir con tus embeddings (esto es lo que hace el proyecto con los vectores de Políglota).

## 11 · Puente con `recsys-course/08_deep_retrieval_ann`
| Tema | Aquí (módulo 14) | Allí (recsys 08) |
|---|---|---|
| Vectores | embeddings de texto (Matryoshka, binarios…) | embeddings de ítems de un *two-tower* |
| Índices | desde cero: IVF, PQ/OPQ, HNSW, Vamana, RaBitQ | uso de FAISS: Flat/IVF/IVF-PQ/HNSW, hnswlib, ScaNN |
| Foco | algoritmos, cuantización con garantías, disco, filtros | integración con el modelo, servicio top-K, filtrado de negocio |
Léelo para ver cómo el mismo índice sirve a un *two-tower*; lo que cambia es el **modelo que produce los vectores**, no el índice.
""")
    nb.md(r'''## 🗺️ Mapa de madurez (a oct-2026)
Ya has construido IVF, PQ y un HNSW mínimo y barrido FAISS con un SLA; la tabla sitúa esas familias y las más recientes (DiskANN, ScaNN, RaBitQ, filtros) por madurez antes de ver quién las usa.

🟢 sólido · 🟡 emergente · 🔴 experimental.

| Técnica | Madurez | Quién la usa (respaldado) | Fuente |
|---|---|---|---|
| Fuerza bruta (exacta, SIMD/GPU) | 🟢 | línea base obligatoria; óptima hasta cientos de miles de vectores | — |
| IVF (listas invertidas por k-means) | 🟢 | FAISS, Milvus, muchos sistemas | Jégou et al. 2011; Douze et al. 2024 |
| PQ / OPQ | 🟢 | FAISS (IVF-PQ), ScaNN, DiskANN (PQ en RAM) | Jégou et al. 2011; Ge et al. 2013 |
| HNSW | 🟢 | Lucene/Elasticsearch/OpenSearch, pgvector, Qdrant, Weaviate, FAISS… | Malkov & Yashunin 2016 (1603.09320) |
| ScaNN (cuantización anisótropa) | 🟢 | Google (`scann`); base de la búsqueda vectorial de Google | Guo et al. 2019 (1908.10396) |
| DiskANN / Vamana (grafo + SSD) | 🟢/🟡 | Microsoft (código abierto); sistemas con índices en disco | Subramanya et al. 2019; FreshDiskANN 2105.09613 |
| RaBitQ / Extended-RaBitQ | 🟡 | Elastic (BBQ, inspirado en RaBitQ), Milvus ≥ 2.6, contribuciones a FAISS | Gao & Long 2024 (2405.12497); 2409.09913 |
| Cuantización binaria + rescoring | 🟡 | Elastic BBQ, proveedores de embeddings (módulo 12) | blog HF 2024; Elastic |
| Búsqueda filtrada dentro del grafo (ACORN y similares) | 🟡 | investigación + algunos motores | Patel et al. 2024 (2403.04871) |
| GPU para ANN (FAISS-GPU/cuVS, CAGRA) | 🟡 | NVIDIA/Meta; depende de versiones | Douze et al. 2024; docs |
''')
    nb.md(r"""## 12 · 🏭 En producción

- **FAISS** (Meta; Douze et al., 2024) es la biblioteca de referencia: Flat, IVF, PQ/OPQ, HNSW, cuantización escalar, GPU y composición de índices con `index_factory`. El paper documenta el diseño y las decisiones de ingeniería.
- **HNSW** es el índice por defecto de gran parte de los motores: **Lucene/Elasticsearch/OpenSearch**, **pgvector** (ofrece HNSW e IVFFlat), Qdrant y Weaviate. Por eso la mayoría de las decisiones del equipo son `M`, `efConstruction` y `efSearch`.
- **Cuantización binaria derivada de RaBitQ:** Elastic documenta BBQ (Elasticsearch 8.16, Lucene) con reducciones de memoria de ≈ 95 % según su propio benchmark; Milvus informa soporte de RaBitQ desde la versión 2.6.
- **DiskANN** (Microsoft, código abierto) para índices que no caben en RAM; **ScaNN** (Google, código abierto) para MIPS con cuantización anisótropa.
- **Multivector:** Qdrant recomienda desactivar HNSW en el campo multivector cuando solo se usa para *reranking* (módulo 13).
- **Evaluación independiente:** *ann-benchmarks* (Aumüller et al., 2018) compara implementaciones en curvas recall-QPS; úsalo como referencia para tu clase de dataset, no como sustituto de medir los tuyos.
- La **operación** (sharding, réplicas, actualizaciones, backups) es el tema del módulo 18.
""")
    nb.md(r"""## 13 · 🧠 Secretos de la élite

1. **Mide con el protocolo correcto.** Neighbor recall contra fuerza bruta **sobre queries reales**, batch=1, un hilo, p99 (no la media) y bytes serializados reales. Comparar un índice a 8 hilos en lote con otro a 1 hilo es la fuente de la mitad de los benchmarks engañosos.
2. **Los parámetros no se transfieren entre datasets** (lo viste en la sección 10): el `nprobe` o `efSearch` que da 0.95 con un modelo de embeddings da otro valor con el siguiente. Reajusta tras **cada cambio de embedder, de dimensión o de cuantización** (módulo 12).
3. **Primero reduce el coste de la distancia, luego el número de distancias.** Matryoshka (módulo 12) divide el coste de cada distancia por 2–4× *antes* de que el índice haga nada, y se combina con cualquier ANN.
4. **PQ casi nunca va sola.** El patrón de producción es «códigos comprimidos en RAM para generar candidatos + vectores completos (disco/SSD) para re-ordenar» (IVF-PQ + refine, DiskANN, binaria + rescoring).
5. **HNSW cuesta construirlo y mantenerlo.** Construir es lento (aquí, decenas de veces más que IVF), consume más RAM que los vectores solos y los borrados suelen implementarse como marcas (*tombstones*) que degradan el grafo hasta reconstruirlo; planifica reconstrucciones periódicas (módulo 18). FreshDiskANN existe precisamente para el caso de actualización continua.
6. **Vigila la cola, no la media.** En IVF, listas muy desiguales (aquí la mayor tiene ≈ 3× la media) disparan el p99; en HNSW, la cola depende de `efSearch` y de la frialdad de la caché. Re-balancea o usa más celdas.
7. **Filtros: elige la estrategia según la selectividad.** Pre-filtro exacto cuando `s·N` es pequeño, filtro en el grafo cuando es moderado y post-filtro solo si es alto. Si cada inquilino (*tenant*) tiene pocos vectores, un índice por tenant puede ser mejor que un filtro.
8. **La binaria mejora con la dimensión.** Con RaBitQ el error baja como $1/\sqrt D$: para embeddings de 768–3072 dimensiones la binaria es mucho más viable que a 64 (por eso funciona bien con modelos recientes y mal con embeddings pequeños).
9. **El *refine* es un dial barato:** subir `k_factor` (candidatos re-puntuados) cuesta lecturas del vector completo, no distancias aproximadas; es la primera palanca cuando el recall no llega al SLA.
10. **Recall del índice ≠ recall de la tarea.** Un índice con recall@10 = 0.95 sobre un embedder con nDCG@10 = 0.60 sigue dando ≈ 0.57 de nDCG: evalúa ambas capas por separado (módulo 15).
""")
    nb.md(r"""## 14 · ⚠️ Errores comunes

| Error | Síntoma | Arreglo |
|---|---|---|
| Medir latencia en lote o con varios hilos | cifras irreproducibles en producción | batch=1, 1 hilo, p50/p99 |
| Calcular recall contra el propio índice aproximado | recall siempre ≈ 1 | ground truth con fuerza bruta exacta |
| Evaluar con queries tomadas del corpus de índice | recall inflado (el vecino más cercano es la propia query) | queries separadas del índice |
| Copiar parámetros de otro dataset/modelo | recall inesperadamente bajo | re-barrer con tus vectores |
| Usar L2 con vectores sin normalizar y producto interno en el índice | ranking incoherente | normalizar o elegir la métrica adecuada |
| PQ con `m` que no divide a `d` o entrenada con pocas muestras | libros pobres | `d % m == 0`, ≥ 39·256 muestras por subespacio como regla de FAISS |
| HNSW con `efSearch < k` | menos resultados que `k` | `efSearch ≥ k` |
| Post-filtro con filtros muy selectivos | resultados vacíos | pre-filtro / más sobremuestreo / grafo filtrable |
| Olvidar el *refine* en IVF-PQ | recall estancado | `IndexRefineFlat` o re-ranking con vectores completos |
| Mezclar vectores de dos versiones de embedder en un índice | recall aleatorio | un índice por (modelo, versión, dimensión, precisión) |
""")
    nb.md(r"""## 15 · Autoevaluación

<details><summary><b>1 · (Cálculo)</b> HNSW con $N=10^8$, $d=768$ en <code>float32</code> y $M=32$ (grado máximo $2M=64$ en la capa 0, enlaces de 4 B). Estima la RAM del índice.</summary>

Vectores: $10^8\cdot768\cdot4=307.2$ GB. Capa 0: $10^8\cdot64\cdot4=25.6$ GB (cota superior; las capas superiores añaden ≈ $1/M$ de nodos). Total ≈ **333 GB** (más metadatos). El grafo añade ≈ 8–10 % al tamaño de los vectores: el cuello de botella son los **vectores**, por eso se comprimen (PQ, binaria) o se mueven a disco.
</details>

<details><summary><b>2 · (Cálculo)</b> IVF con $N=10^7$, $n_{list}=4096$, $n_{probe}=32$. ¿Qué fracción del corpus se escanea y cuántas comparaciones hace una query?</summary>

Fracción $=32/4096=0.78\%$ → ≈ 78 000 vectores (si las listas están equilibradas) + 4096 comparaciones con centroides ≈ **82 000** distancias frente a $10^7$ de la fuerza bruta (≈ 120× menos).
</details>

<details><summary><b>3 · (Cálculo)</b> PQ con $d=768$, $m=96$, 8 bits por código: ¿bytes por vector, factor de compresión y tamaño de las tablas ADC por query?</summary>

96 B por vector; $768\cdot4/96=32\times$. Tablas: $96\times256$ floats $=98\,304$ B ≈ 96 KB por query (se calculan una vez por query y por celda si se usa el residuo).
</details>

<details><summary><b>4 · (Diagnóstico)</b> Tu HNSW dio recall@10 = 0.98 en validación, pero a las 3 semanas de producción cae a 0.90 sin cambiar nada. ¿Qué miras?</summary>

(a) Entraron muchos documentos nuevos con borrados por marca: el grafo se degrada (reconstruir). (b) **Deriva de la distribución de queries o de documentos** respecto a la de validación. (c) Cambió la versión del embedder para parte del índice. (d) Un cambio de `efSearch` por tuning de latencia. Revisa con una muestra de queries actuales y su ground truth por fuerza bruta.
</details>

<details><summary><b>5 · (Diagnóstico)</b> En IVF-Flat el p50 es 3 ms pero el p99 es 40 ms. ¿Causas probables?</summary>

Listas de tamaños muy desiguales (algunas queries caen en celdas enormes), caché fría, `nprobe` alto con contención de hilos, y GC/páginas de memoria. Soluciones: más celdas/balanceo, reducir `nprobe` con *refine*, fijar afinidad de hilos y precalentar.
</details>

<details><summary><b>6 · (Transferencia)</b> Tienes $10^9$ vectores de 768 dims y un servidor con 64 GB de RAM y SSD NVMe. Diseña el índice.</summary>

HNSW no cabe (≈ 3 TB). Opciones: **DiskANN/Vamana** (PQ de, p. ej., 64–96 B/vector en RAM = 64–96 GB, aún demasiado → PQ de 32 B = 32 GB + grafo y vectores completos en SSD), o **IVF-PQ + refine** con vectores completos en disco, o **binaria (RaBitQ) 96 B/vector + rescoring**. Reduciría la dimensión con Matryoshka (módulo 12) para bajar el PQ. Validaría recall y p99 con 1 000 queries reales y ground truth en una submuestra.
</details>

<details><summary><b>7 · (Transferencia)</b> ¿Por qué RaBitQ divide por $\langle\bar o,o\rangle$ y qué ocurre si no lo hace?</summary>

Porque el vector cuantizado $\bar o$ no es unitario respecto a $o$: $\langle\bar o,q\rangle$ **subestima** sistemáticamente $\langle o,q\rangle$ por el factor $\langle\bar o,o\rangle<1$. Dividir da un estimador **insesgado**; sin ello, los productos internos altos (los de los vecinos que buscamos) salen comprimidos y el ranking entre candidatos se distorsiona (en la sección 8 el ingenuo estimaba ≈ 0.75 del valor real).
</details>
""")
    nb.md(r"""## 16 · Referencias (verificadas; consultadas en oct-2026)

**Papers (arXiv)**
- Malkov & Yashunin (2016/2018). *Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs*. IEEE TPAMI 42(4), 2020. <https://arxiv.org/abs/1603.09320>
- Guo et al. (2019). *Accelerating Large-Scale Inference with Anisotropic Vector Quantization* (ScaNN). ICML 2020. <https://arxiv.org/abs/1908.10396>
- Gao & Long (2024). *RaBitQ: Quantizing High-Dimensional Vectors with a Theoretical Error Bound for Approximate Nearest Neighbor Search*. SIGMOD 2024. <https://arxiv.org/abs/2405.12497> · Gao et al. (2024). *Practical and Asymptotically Optimal Quantization of High-Dimensional Vectors in Euclidean Space for Approximate Nearest Neighbor Search* (Extended RaBitQ). Preprint. <https://arxiv.org/abs/2409.09913>
- Douze et al. (2024). *The Faiss library*. Preprint. <https://arxiv.org/abs/2401.08281>
- Aumüller, Bernhardsson & Faithfull (2018). *ANN-Benchmarks: A Benchmarking Tool for Approximate Nearest Neighbor Algorithms*. Information Systems 87 (2020; versión completa del artículo de SISAP 2017). <https://arxiv.org/abs/1807.05614>
- Patel et al. (2024). *ACORN: Performant and Predicate-Agnostic Search Over Vector Embeddings and Structured Data*. SIGMOD 2024. <https://arxiv.org/abs/2403.04871>
- Singh et al. (2021). *FreshDiskANN: A Fast and Accurate Graph-Based ANN Index for Streaming Similarity Search*. Preprint. <https://arxiv.org/abs/2105.09613>

**Papers (sin arXiv)**
- Jégou, Douze & Schmid (2011). *Product Quantization for Nearest Neighbor Search*. IEEE TPAMI 33(1).
- Ge, He, Ke & Sun (2013). *Optimized Product Quantization for Approximate Nearest Neighbor Search*. CVPR 2013.
- Subramanya et al. (2019). *DiskANN: Fast Accurate Billion-point Nearest Neighbor Search on a Single Node*. NeurIPS 2019.

**Código y blogs**
- FAISS: <https://github.com/facebookresearch/faiss> · DiskANN: <https://github.com/microsoft/DiskANN> · ScaNN: <https://github.com/google-research/google-research/tree/master/scann>
- Elastic Search Labs. *Better Binary Quantization (BBQ) in Lucene and Elasticsearch*. <https://www.elastic.co/search-labs/blog/better-binary-quantization-lucene-elasticsearch>
- Milvus. *Bring Vector Compression to the Extreme: How Milvus Serves 3× More Queries with RaBitQ* (blog de Milvus). <https://milvus.io/blog/bring-vector-compression-to-the-extreme-how-milvus-serves-3%C3%97-more-queries-with-rabitq.md>
- Curso de recsys del repositorio: [`recsys-course/08_deep_retrieval_ann`](../../recsys-course/08_deep_retrieval_ann/README.md).

**Para profundizar:** módulo 15 (evaluación de retrieval de extremo a extremo), módulo 18 (operación de bases vectoriales: Qdrant/pgvector, versionado y migración).
""")
    # <<END_LESSON>>
    nb.save(LESSON)


def _entre(src: str, a: str, b: str | None = None) -> str:
    i = src.index(a)
    j = src.index(b, i) if b else len(src)
    return src[i:j].rstrip() + "\n"


def project() -> None:
    nb = Notebook("Proyecto 14 · Índice de Políglota", colab_path=PROJECT, gpu=False)
    F_RECALL = _entre(CODE_ANN_BASE, "def recall_vs_gt", "def mide_latencia")
    SOL_EXACTO = _entre(CODE_ANN_BASE, "def exacto_topk", "def recall_vs_gt")
    SOL_LAT = _entre(CODE_ANN_BASE, "def mide_latencia", "def tam_indice_MB")
    SOL_TAM = _entre(CODE_ANN_BASE, "def tam_indice_MB")

    nb.md(nb.badge() + r"""

# Proyecto 14 · Índice de Políglota: curvas recall@10 vs latencia vs memoria

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 2 h · **GPU:** no necesaria (CPU) · **Cómputo:** 0 unidades de Colab.

**Conexión.** *Viene de:* módulo 12 (el embedder y la dimensión elegidos) y 13 (el retriever denso del sistema híbrido). *Va hacia:* módulo 15 (evaluar el sistema completo) y 18 (operar el índice: Qdrant/pgvector, versionado, migración).

## 1 · Contexto de negocio
Políglota Labs indexará **10 millones de fragmentos**. El CTO te entrega la «ficha técnica» que debe cumplir el índice en producción:

| Requisito | Valor |
|---|---|
| Recall@10 contra búsqueda exacta | ≥ 0.90 |
| Latencia p99 (batch = 1, un hilo) | ≤ 50 % del p99 de la fuerza bruta medida en tu máquina (al menos 2× más rápido) |
| Memoria del índice (extrapolada a 10 M) | ≤ 3 × la de la fuerza bruta `float32` |

Tu trabajo: medir con el protocolo correcto varias familias de índices FAISS sobre **vectores de Políglota**, dibujar las curvas, extraer la frontera de Pareto y **recomendar** una configuración (o decir con datos por qué ninguna cumple).

## 2 · Dataset
Embeddings del corpus Políglota (`carga_corpus`, módulo 00; sintético con `⚠️` si no hay acceso) calculados con el embedder del módulo 12 (si no se puede descargar, el fallback TF-IDF+SVD de 64 dimensiones). Como el corpus tiene solo ~400 documentos, se **amplía con copias ruidosas** (vecinos difíciles) hasta `N` vectores; las queries son las del corpus. **Con vectores reales de un modelo los resultados serán distintos de los del fallback**: lo importante es el procedimiento.

## 3 · Entregables
1. Funciones `exacto_topk`, `mide_latencia` y `tam_indice_MB` (protocolo de medición).
2. `construye` y `fija_parametro` para 4 familias FAISS: `Flat`, `IVF-Flat`, `IVF-PQ+refine` y `HNSW`.
3. `barrido`: tabla con recall@10, p50, p99, QPS, MB y MB extrapolados a 10 M para cada (familia, parámetro).
4. `no_dominados` (frontera de Pareto en 3 objetivos) y `elige_config` (mínima memoria que cumple el SLA).
5. Dos gráficas: recall vs latencia (con memoria en la leyenda) y recall vs memoria; y una conclusión escrita.

## 4 · Rúbrica (umbrales calibrados con lo que MIDE la solución de referencia)
La solución de referencia se ejecutó en un entorno **sin acceso a Hugging Face** (corpus sintético y embedder de respaldo TF-IDF+SVD de 64 dimensiones), con `N` = 20 000 y un hilo; **no se verificó con un embedder real**. Los umbrales son invariantes relativas; el valor medido está en la última columna.

| # | Criterio | Umbral | Medido por la solución |
|---|---|---|---|
| R1 | La fila `Flat` tiene recall = 1.0 (el oráculo es exacto) | = 1.0 | 1.000 |
| R2 | p99 ≥ p50 en todas las filas | 100 % | 100 % de las filas |
| R3 | Memoria: `Flat` ≈ 4·N·D bytes (±5 %) y `HNSW` > `Flat` | cumplido | Flat 5.12 MB (teórico 5.12) · HNSW 8.00 MB |
| R4 | Dentro de cada familia el recall no baja al subir el parámetro de búsqueda (tolerancia 0.01) | ≥ 90 % de pares | 100 % de pares |
| R5 | La frontera de Pareto tiene ≥ 3 puntos y ≥ 2 familias | cumplido | 10 puntos, 4 familias |
| R6 | `elige_config` devuelve una fila que cumple el SLA (o `None` si ninguna lo cumple) | cumplido | IVF-Flat nprobe=4 (recall 0.95, p99 0.06 ms, 5.3 MB) |
| R7 | Conclusión escrita con ≥ 3 números de tus tablas | — | revisión manual |
""")
    nb.md("## 5 · Preparación (celdas dadas)")
    nb.code(CODE_PIP)
    nb.code(C.CODE_SETUP_COMMON)
    for _src in src_corpus_cells():
        nb.code(_src)
    nb.code(SRC_METRICS)
    nb.code(C.CODE_EMBEDDER_TOOLS)
    nb.code(r'''
import faiss
faiss.omp_set_num_threads(N_THREADS)          # medición justa: un hilo
import pandas as pd
import matplotlib.pyplot as plt
''' + F_RECALL)

    # ── TODO 1-3 medición ──
    nb.md(r"""## 6 · Paso 1 — Protocolo de medición (TODO 1–3)
- **TODO 1 `exacto_topk(Q, X, k)`**: fuerza bruta por producto interno (vectores normalizados) procesando las queries por bloques de 64; devuelve los **índices** del top-`k` ordenados de mayor a menor score. Es el oráculo para el recall.
- **TODO 2 `mide_latencia(fn, Q)`**: llama a `fn(q)` para **cada query por separado** (batch = 1), tras un calentamiento de 10 queries, y devuelve `(p50_ms, p99_ms, qps)` donde `qps = 1000 / media_ms`.
- **TODO 3 `tam_indice_MB(index)`**: tamaño real del índice serializado en MB (`faiss.serialize_index`).

<details><summary>🪜 Pista 1 (idea)</summary>
Para el top-k sin ordenar todo: <code>np.argpartition</code> y luego ordena solo esos k. Para latencia, cronometra con <code>time.perf_counter()</code> una llamada por query y usa <code>np.percentile</code>.
</details>
<details><summary>🪜 Pista 2 (casi la API)</summary>
<code>idx = np.argpartition(-S, k, axis=1)[:, :k]</code> · <code>orden = np.take_along_axis(S, idx, 1).argsort(1)[:, ::-1]</code> · <code>faiss.serialize_index(index).nbytes / 1e6</code>.
</details>
""")
    nb.code(r'''
def exacto_topk(Q, X, k=10):
    # TODO 1: top-k exacto (índices) por producto interno, en bloques de 64 queries
    raise NotImplementedError("TODO 1")

def mide_latencia(fn, Q, calentamiento=10):
    # TODO 2: devuelve (p50_ms, p99_ms, qps) llamando a fn(q) una query cada vez
    raise NotImplementedError("TODO 2")

def tam_indice_MB(index):
    # TODO 3: tamaño serializado en MB
    raise NotImplementedError("TODO 3")

try:
    _X = np.random.default_rng(0).normal(size=(500, 16)).astype("float32"); _X /= np.linalg.norm(_X, axis=1, keepdims=True)
    _gt = exacto_topk(_X[:5], _X, 3)
    print("el vecino más cercano de cada vector es él mismo:", bool((_gt[:, 0] == np.arange(5)).all()))
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''')

    # ── datos ──
    nb.md(r"""## 7 · Paso 2 — Vectores de Políglota (dado)
Embebemos documentos y queries con el embedder del módulo 12 y ampliamos el corpus con copias ruidosas hasta `N` vectores (vecinos difíciles). Las queries y el índice quedan **separados** (las queries nunca se añaden al índice).
""")
    nb.code(r'''
CORPUS = carga_corpus(FAST_DEV_RUN)
DOC_TXT, Q_TXT = [d["text"] for d in CORPUS["docs"]], [q["text"] for q in CORPUS["queries"]]
emb = None
for clave in ("multilingual-e5-small", "paraphrase-multilingual-MiniLM-L12-v2"):
    emb = cargar_embedder(clave)
    if emb is not None:
        break
if emb is None:
    emb = cargar_embedder("multilingual-e5-small", textos_ajuste=DOC_TXT)
E_d, E_q = emb.encode_docs(DOC_TXT), emb.encode_queries(Q_TXT)

def aumenta(E, n_objetivo, sigma=0.8, seed=0):
    """Copias ruidosas de cada vector (normalizadas) hasta n_objetivo vectores: crea vecinos difíciles."""
    rng = np.random.default_rng(seed)
    bloques, total = [E], len(E)
    while total < n_objetivo:
        ruido = rng.normal(size=E.shape)
        ruido *= sigma / np.linalg.norm(ruido, axis=1, keepdims=True)
        X_ = E + ruido
        bloques.append((X_ / np.linalg.norm(X_, axis=1, keepdims=True)).astype(np.float32)); total += len(E)
    return np.vstack(bloques)[:n_objetivo]

N = 20000 if FAST_DEV_RUN else 200000
X = np.ascontiguousarray(aumenta(E_d, N))
Q = np.ascontiguousarray(E_q.astype(np.float32))
D = X.shape[1]
N_PROD = 10_000_000
print(f"embedder={emb.clave} (real={emb.is_real}) · X: {X.shape} · Q: {Q.shape}")
''')

    # ── TODO 4: construcción ──
    nb.md(r"""## 8 · Paso 3 — Construir y parametrizar 4 familias (TODO 4)
Implementa `construye(familia, X)` y `fija_parametro(ix, familia, valor)`:

| Familia | Construcción (producto interno) | Parámetro de búsqueda |
|---|---|---|
| `Flat` | `IndexFlatIP(D)` | — (usa `0`) |
| `IVF-Flat` | `IndexIVFFlat(IndexFlatIP(D), D, nlist)`, `nlist = int(sqrt(N))`, entrenar y añadir | `nprobe` |
| `IVF-PQ+refine` | `IndexIVFPQ(IndexFlatIP(D), D, nlist, m, 8)` envuelto en `IndexRefineFlat`; `m` = el mayor divisor de `D` en {32,16,8,4}; entrenar y añadir | `nprobe` (del índice base) con `k_factor = 10` |
| `HNSW` | `IndexHNSWFlat(D, 16, METRIC_INNER_PRODUCT)` con `efConstruction = 100` | `efSearch` |

<details><summary>🪜 Pista 1 (idea)</summary>
Los índices con entrenamiento (<code>is_trained == False</code>) necesitan <code>ix.train(X)</code> antes de <code>ix.add(X)</code>. Para <code>IndexRefineFlat</code> el <code>nprobe</code> se fija sobre el índice IVF interno.
</details>
<details><summary>🪜 Pista 2 (casi la API)</summary>
<code>base = faiss.IndexIVFPQ(faiss.IndexFlatIP(D), D, nlist, m, 8, faiss.METRIC_INNER_PRODUCT)</code> · <code>ix = faiss.IndexRefineFlat(base); KEEP.append(base)</code> (FAISS no es dueño de <code>base</code>: mantén la referencia) · <code>faiss.extract_index_ivf(ix.base_index).nprobe = v; ix.k_factor = 10</code> · HNSW: <code>ix.hnsw.efSearch = v</code>.
</details>
""")
    nb.code(r'''
KEEP = []                       # referencias que FAISS no posee (índice base de IndexRefineFlat)
FAMILIAS = {"Flat": [0], "IVF-Flat": [1, 2, 4, 8, 16, 32], "IVF-PQ+refine": [2, 4, 8, 16, 32], "HNSW": [8, 16, 32, 64, 128]}

def construye(familia, X):
    # TODO 4.a: devuelve el índice FAISS ya entrenado y con X añadido
    raise NotImplementedError("TODO 4.a")

def fija_parametro(ix, familia, valor):
    # TODO 4.b: fija nprobe / efSearch (y k_factor=10 en IVF-PQ+refine)
    raise NotImplementedError("TODO 4.b")

try:
    _ix = construye("IVF-Flat", X[:2000]); fija_parametro(_ix, "IVF-Flat", 4)
    print("IVF-Flat construido:", _ix.ntotal, "vectores")
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''')

    # ── TODO 5: barrido ──
    nb.md(r"""## 9 · Paso 4 — El barrido (TODO 5)
Para cada familia y parámetro: recall@10 contra `exacto_topk`, p50/p99/QPS con batch=1, `MB` real y `MB_10M` (= `MB * N_PROD / N`, extrapolación lineal: suficiente para comparar, **no** para dimensionar un clúster). Devuelve un `DataFrame` con columnas `familia, param, recall, p50_ms, p99_ms, QPS, MB, MB_10M, seg_construir`.

<details><summary>🪜 Pista 1 (idea)</summary>
Dos bucles: familias (construir es caro, se hace una vez) y valores del parámetro de búsqueda (`nprobe`, `efSearch`…, que se cambian sin reconstruir). Cada fila es un punto de la curva recall–latencia de la lección (sección 10).
</details>
<details><summary>🪜 Pista 2 (casi la API)</summary>
Construye el índice una vez por familia (mide <code>seg_construir</code>), y para cada valor: <code>fija_parametro</code>, <code>_, I = ix.search(Q, 10)</code>, <code>mide_latencia(lambda q: ix.search(q[None], 10), Q)</code>.
</details>
""")
    nb.code(r'''
def barrido(X, Q, GT):
    # TODO 5: recorre FAMILIAS y devuelve el DataFrame descrito arriba
    raise NotImplementedError("TODO 5")

try:
    GT = exacto_topk(Q, X, 10)
    RES = barrido(X, Q, GT)
    display(RES.round(3).head(10))
except NotImplementedError as e:
    GT = RES = None
    print("⏳ pendiente:", e)
''')

    # ── TODO 6-7 ──
    nb.md(r"""## 10 · Paso 5 — Frontera de Pareto y recomendación (TODO 6–7)
- `no_dominados(df, maximizar, minimizar)`: filas para las que **no existe otra** que sea al menos igual en todos los objetivos y estrictamente mejor en alguno. Úsalo con `maximizar=["recall"]`, `minimizar=["p99_ms", "MB"]`.
- `elige_config(df, recall_min, p99_max_ms, mem_max_MB10M)`: entre las filas que cumplen el SLA, la de **menor `MB`** (desempate: menor `p99_ms`); `None` si ninguna cumple.

<details><summary>🪜 Pista 1 (idea)</summary>
Pon todos los objetivos en «mayor es mejor» (cambia el signo de los que se minimizan). La fila $i$ está dominada si alguna otra es $\ge$ en todo y $>$ en algo. Con tres objetivos ya no basta el «ordena y recorre» del proyecto 12.
</details>
<details><summary>🪜 Pista 2 (casi la API)</summary>
<code>M = np.hstack([df[maximizar].to_numpy(), -df[minimizar].to_numpy()])</code>; para cada fila, <code>domina = ((M &gt;= M[i]).all(1)) &amp; ((M &gt; M[i]).any(1))</code> y consérvala si <code>not domina.any()</code>. Para <code>elige_config</code>: filtra por las tres condiciones y <code>sort_values(["MB", "p99_ms"]).iloc[0]</code>.
</details>
""")
    nb.code(r'''
RECALL_MIN, P99_MAX_MS = 0.90, None          # P99_MAX_MS = 0.5 x p99 de la fuerza bruta: se fija tras el barrido
MEM_MAX_MB10M = 3 * 4 * D * N_PROD / 1e6          # 3 x la fuerza bruta float32 extrapolada a 10 M

def no_dominados(df, maximizar, minimizar):
    # TODO 6: devuelve el subconjunto de filas no dominadas
    raise NotImplementedError("TODO 6")

def elige_config(df, recall_min, p99_max_ms, mem_max_MB10M):
    # TODO 7: fila de menor memoria que cumple el SLA (None si ninguna)
    raise NotImplementedError("TODO 7")

def dibuja(df, frente):
    colores = {"Flat": "#6B7280", "IVF-Flat": "#1F6FEB", "IVF-PQ+refine": "#9467BD", "HNSW": "#F28E2B"}
    fig, axs = plt.subplots(1, 2, figsize=(12, 4))
    for fam, g in df.groupby("familia"):
        axs[0].plot(g["p50_ms"], g["recall"], "o-", color=colores[fam], label=f"{fam} ({g['MB'].iloc[0]:.1f} MB)")
        axs[1].scatter(g["MB"], g["recall"], color=colores[fam], s=30, label=fam)
    axs[0].scatter(frente["p50_ms"], frente["recall"], s=90, facecolors="none", edgecolors="k", label="no dominados")
    axs[0].axhline(RECALL_MIN, color="k", ls=":"); axs[0].set_xscale("log"); axs[0].set_xlabel("p50 (ms, log)"); axs[0].set_ylabel("recall@10"); axs[0].legend(fontsize=7); axs[0].grid(alpha=.3, which="both")
    axs[1].set_xscale("log"); axs[1].set_xlabel("memoria del índice (MB, log)"); axs[1].set_ylabel("recall@10"); axs[1].grid(alpha=.3, which="both")
    plt.tight_layout(); plt.show()

try:
    P99_MAX_MS = 0.5 * float(RES.loc[RES["familia"] == "Flat", "p99_ms"].iloc[0])
    FRENTE = no_dominados(RES, ["recall"], ["p99_ms", "MB"])
    ELEGIDA = elige_config(RES, RECALL_MIN, P99_MAX_MS, MEM_MAX_MB10M)
    dibuja(RES, FRENTE)
    print("Configuración elegida:", None if ELEGIDA is None else ELEGIDA[["familia", "param", "recall", "p99_ms", "MB", "MB_10M"]].to_dict())
except (NotImplementedError, TypeError, AttributeError) as e:
    FRENTE = ELEGIDA = None
    print("⏳ pendiente:", repr(e))
''')
    nb.md(r"""> 👀 **Qué debes observar:** a la izquierda, cada familia es una curva: subir `nprobe`/`efSearch` compra recall con latencia, y la de HNSW suele quedar arriba-izquierda a costa de más memoria (mírala a la derecha). Los círculos negros son los no dominados: la configuración elegida debe ser uno de ellos. Si la fuerza bruta (gris) cumple el SLA con tu $N$, la respuesta correcta es «no hace falta ANN» (sección 1). La extrapolación `MB_10M` es lineal: sirve para comparar familias, no para dimensionar.""")
    nb.md("## 11 · Autocomprobación de la rúbrica")
    nb.code(r'''
def autograder():
    ch = {}
    try:
        flat = RES[RES["familia"] == "Flat"]
        ch["R1 Flat tiene recall = 1.0"] = bool((flat["recall"] >= 0.999).all() and len(flat))
        ch["R2 p99 ≥ p50"] = bool((RES["p99_ms"] >= RES["p50_ms"] - 1e-9).all())
        mb = RES.groupby("familia")["MB"].first()
        ch["R3 memoria coherente"] = bool(abs(mb["Flat"] - 4 * N * D / 1e6) / (4 * N * D / 1e6) < 0.05 and mb["HNSW"] > mb["Flat"])
        pares = tot = 0
        for fam, g in RES.groupby("familia"):
            r = g.sort_values("param")["recall"].to_numpy()
            pares += len(r) - 1; tot += int((np.diff(r) >= -0.01).sum())
        ch["R4 recall monótono en el parámetro (≥ 90 % de pares)"] = bool(pares == 0 or tot / pares >= 0.90)
    except Exception as e:
        for k in ("R1 Flat tiene recall = 1.0", "R2 p99 ≥ p50", "R3 memoria coherente", "R4 recall monótono en el parámetro (≥ 90 % de pares)"):
            ch.setdefault(k, False)
    try:
        ch["R5 Pareto ≥ 3 puntos y ≥ 2 familias"] = bool(len(FRENTE) >= 3 and FRENTE["familia"].nunique() >= 2)
    except Exception:
        ch["R5 Pareto ≥ 3 puntos y ≥ 2 familias"] = False
    try:
        ok = RES[(RES["recall"] >= RECALL_MIN) & (RES["p99_ms"] <= P99_MAX_MS) & (RES["MB_10M"] <= MEM_MAX_MB10M)]
        ch["R6 elige_config respeta el SLA"] = bool((len(ok) == 0 and ELEGIDA is None) or (ELEGIDA is not None and ELEGIDA["recall"] >= RECALL_MIN
                                                   and ELEGIDA["p99_ms"] <= P99_MAX_MS and ELEGIDA["MB_10M"] <= MEM_MAX_MB10M and ELEGIDA["MB"] <= ok["MB"].min() + 1e-9))
    except Exception:
        ch["R6 elige_config respeta el SLA"] = False
    for k, v in ch.items():
        print("✅" if v else "❌", k)
    return ch

_ = autograder()
''')
    nb.md(r"""## 12 · Tu conclusión (R7)
En ≤ 10 líneas, con números de tus tablas: ¿qué configuración recomiendas para 10 M de fragmentos y por qué? ¿Qué familia gana en latencia, cuál en memoria y cuál en tiempo de construcción? ¿Qué cambiaría si el SLA exigiera recall ≥ 0.99? ¿Qué riesgos ves al extrapolar de `N` = 20 000 a 10 M?

> *(Edita esta celda.)*

## 13 · Retos extra (nivel experto)
1. **Matryoshka + índice** (módulo 12): trunca el embedder a D/2 y D/4 y repite el barrido; ¿qué combinación (dimensión × familia) domina?
2. **Mini-HNSW de la lección** (sección 5) frente a `IndexHNSWFlat` con tus vectores: ¿cuántas distancias evalúa cada una para el mismo recall?
3. **Búsqueda filtrada**: añade un atributo `lang` (`es`/`en`/`code`) a cada vector (el corpus lo trae) y mide recall/latencia de pre-filtro, post-filtro y filtro en grafo (lección, sección 9).
4. **Binaria + rescoring con FAISS** (`IndexBinaryFlat` / `IndexBinaryIVF`): compara con `IVF-PQ+refine` en memoria y recall.
5. **Curva con N creciente**: repite con N = 20 k, 50 k, 100 k y grafica cómo escala la latencia de cada familia.

## 14 · Reflexión (producción e hilo conductor)
- ¿A partir de qué `N` empieza a ganar un ANN a la fuerza bruta en tu máquina? (reto 5)
- ¿Qué parte de tu elección cambia si el 30 % de las consultas llevan un filtro por idioma o versión?
- ¿Cómo detectarías en producción que el recall del índice se ha degradado (deriva, borrados acumulados)? (módulo 18)
- Si migras de embedder, ¿qué hay que reconstruir y cómo evitas el *downtime*?
- ¿Cuánto cuesta (RAM, $/mes) el índice elegido a 10 M y a 100 M de fragmentos?
""")

    nb.md(r"""---
# ⛔ SPOILER — intenta resolverlo primero
Las celdas siguientes **sobrescriben** tus funciones con la solución de referencia.
""")
    nb.code(SOL_EXACTO + "\n" + SOL_LAT + "\n" + SOL_TAM)
    nb.code(r'''
def construye(familia, X):
    nlist = int(np.sqrt(len(X)))
    if familia == "Flat":
        ix = faiss.IndexFlatIP(D)
    elif familia == "IVF-Flat":
        ix = faiss.IndexIVFFlat(faiss.IndexFlatIP(D), D, nlist, faiss.METRIC_INNER_PRODUCT)
    elif familia == "IVF-PQ+refine":
        m = max(d_ for d_ in (32, 16, 8, 4) if D % d_ == 0)
        base = faiss.IndexIVFPQ(faiss.IndexFlatIP(D), D, nlist, m, 8, faiss.METRIC_INNER_PRODUCT)
        KEEP.append(base)
        ix = faiss.IndexRefineFlat(base)
    elif familia == "HNSW":
        ix = faiss.IndexHNSWFlat(D, 16, faiss.METRIC_INNER_PRODUCT); ix.hnsw.efConstruction = 100
    else:
        raise ValueError(familia)
    if not ix.is_trained:
        ix.train(X)
    ix.add(X)
    return ix

def fija_parametro(ix, familia, valor):
    if familia == "IVF-Flat":
        ix.nprobe = valor
    elif familia == "IVF-PQ+refine":
        faiss.extract_index_ivf(ix.base_index).nprobe = valor
        ix.k_factor = 10
    elif familia == "HNSW":
        ix.hnsw.efSearch = valor

def barrido(X, Q, GT):
    filas = []
    for familia, valores in FAMILIAS.items():
        t0 = time.perf_counter(); ix = construye(familia, X); t_b = time.perf_counter() - t0
        mb = tam_indice_MB(ix)
        for v in valores:
            fija_parametro(ix, familia, v)
            _, I = ix.search(Q, 10)
            p50, p99, qps = mide_latencia(lambda q: ix.search(q[None], 10), Q)
            filas.append(dict(familia=familia, param=v, recall=recall_vs_gt(I, GT), p50_ms=p50, p99_ms=p99, QPS=qps, MB=mb,
                              MB_10M=mb * N_PROD / len(X), seg_construir=t_b))
    return pd.DataFrame(filas)

def no_dominados(df, maximizar, minimizar):
    A = df[maximizar].to_numpy() * 1.0
    B = df[minimizar].to_numpy() * 1.0
    M = np.hstack([A, -B])                                     # todos "mayor es mejor"
    keep = []
    for i in range(len(M)):
        domina = ((M >= M[i]).all(1)) & ((M > M[i]).any(1))
        keep.append(not domina.any())
    return df[np.array(keep)].sort_values("MB")

def elige_config(df, recall_min, p99_max_ms, mem_max_MB10M):
    ok = df[(df["recall"] >= recall_min) & (df["p99_ms"] <= p99_max_ms) & (df["MB_10M"] <= mem_max_MB10M)]
    return None if ok.empty else ok.sort_values(["MB", "p99_ms"]).iloc[0]

GT = exacto_topk(Q, X, 10)
RES = barrido(X, Q, GT)
display(RES.round(3))
P99_MAX_MS = 0.5 * float(RES.loc[RES["familia"] == "Flat", "p99_ms"].iloc[0])
FRENTE = no_dominados(RES, ["recall"], ["p99_ms", "MB"])
ELEGIDA = elige_config(RES, RECALL_MIN, P99_MAX_MS, MEM_MAX_MB10M)
dibuja(RES, FRENTE); plt.show()
print("Configuración elegida:", None if ELEGIDA is None else ELEGIDA[["familia", "param", "recall", "p99_ms", "MB", "MB_10M"]].to_dict())
_ = autograder()
''')
    nb.md("> 👀 **Qué debes observar:** compara tus curvas con estas. Si tu frontera tiene menos puntos, revisa que `no_dominados` use los tres objetivos y que la latencia se mida con batch = 1.")
    nb.md(r"""### Conclusión de referencia (ejemplo)
Con los números de la tabla anterior: la fuerza bruta da recall 1.0 como oráculo; IVF-Flat y HNSW alcanzan el recall objetivo con el parámetro de búsqueda más bajo que lo cumple, IVF-PQ+refine ocupa **más** que IVF-Flat porque, además de los códigos PQ, guarda los vectores completos para el re-ranking (en producción esos vectores irían a disco, no a RAM), y HNSW es el más grande y el más lento de construir. La configuración recomendada es la de **menor memoria que cumple recall, p99 y límite de memoria** (ver `ELEGIDA`); si ninguna cumple, los datos justifican relajar el SLA o cambiar de familia. Riesgos: extrapolar linealmente de 20 000 a 10 M, que el recall depende del embedder y de la dimensión, y que el p99 de una máquina de pruebas no es el de producción.
""")
    nb.save(PROJECT)


def readme() -> None:
    texto = """# Módulo 14 · Indexación y búsqueda aproximada de vecinos (ANN)

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) · **GPU:** no necesaria (CPU)

Con 10 M de fragmentos la búsqueda exacta cuesta decenas de GB de lecturas por consulta. Este módulo enseña a **medir** un índice (neighbor recall,
latencia p50/p99 con batch=1, memoria real) y construye desde cero los algoritmos que lo hacen posible: **IVF**, **PQ/OPQ**, un **mini-HNSW**
(con visualización de capas), **Vamana/DiskANN**, la idea de **ScaNN**, **RaBitQ** (estimador insesgado, error ∝ 1/√D) y **búsqueda filtrada**; después
usa **FAISS** en serio (barrido, frontera de Pareto y elección con un SLA).

> Puente con recsys: [`recsys-course/08_deep_retrieval_ann`](../../recsys-course/08_deep_retrieval_ann/README.md) cubre el uso de FAISS con un *two-tower*; aquí se construyen los algoritmos y se añaden grafos en disco, cuantización con garantías y filtros. La operación de bases vectoriales va en el módulo 18.

## Contenido
| Notebook | Qué hay dentro |
|---|---|
| [`14_indexacion_ann.ipynb`](14_indexacion_ann.ipynb) | Lección: fuerza bruta y protocolo de medición · IVF desde cero · PQ/OPQ desde cero (ADC, refine) · mini-HNSW + capas en 2D · Vamana (RobustPrune) y modelo de I/O de DiskANN · ScaNN (pérdida anisótropa) · mini-RaBitQ · filtros (pre/post/en grafo) · barrido FAISS con SLA · sensibilidad al dataset · 🏭 producción · 🧠 secretos · autoevaluación |
| [`14_proyecto_indexacion_ann.ipynb`](14_proyecto_indexacion_ann.ipynb) | Proyecto: índice de Políglota con curvas recall@10 vs latencia vs memoria; frontera de Pareto en 3 objetivos y elección bajo un SLA. Plantilla con TODOs, pistas 🪜, autocomprobación y solución tras ⛔ SPOILER |

## Objetivos
1. Medir ANN con el protocolo correcto y reconocer cuándo la fuerza bruta basta.
2. Implementar IVF, PQ/OPQ, HNSW, Vamana y RaBitQ (mini) y relacionarlos con FAISS.
3. Resolver búsqueda filtrada y razonar sobre el trade-off recall/latencia/memoria.
4. Elegir una configuración de índice que cumpla un SLA con datos propios.

## Datasets
Vectores sintéticos «tipo embedding» (mezcla de clusters con espectro decreciente) para la lección y **embeddings de Políglota** (corpus del módulo 00 con el embedder del módulo 12, ampliado con copias ruidosas) para el proyecto. Sin acceso a Hugging Face se usa el corpus sintético y un embedder de respaldo (el notebook avisa con `⚠️`).

## Lecturas clave (verificadas)
- Malkov & Yashunin, *HNSW* (1603.09320) · Guo et al., *ScaNN* (1908.10396) · Gao & Long, *RaBitQ* (2405.12497) · Douze et al., *The Faiss library* (2401.08281).
- Subramanya et al., *DiskANN* (NeurIPS 2019) · Singh et al., *FreshDiskANN* (2105.09613) · Patel et al., *ACORN* (2403.04871) · Aumüller et al., *ANN-Benchmarks* (1807.05614).

## Conexión con Políglota
Los vectores y la configuración (dimensión, precisión) vienen de los módulos 12–13; el índice elegido aquí se opera en el módulo 18 y se evalúa de extremo a extremo en el 15.

*Los notebooks se generan con `python tokenization-embeddings-course/_tools/builders/build_14.py` (desde la raíz del repo). Estado del arte a octubre de 2026.*
"""
    with open(f"{MOD}/README.md", "w", encoding="utf-8") as f:
        f.write(texto)
    print(f"OK {MOD}/README.md")


if __name__ == "__main__":
    lesson()
    project()
    readme()
