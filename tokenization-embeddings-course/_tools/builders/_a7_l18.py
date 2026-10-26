"""Lección 18 · Producción (autor A7). La llama build_18.py."""
import _a7_common as C


def lesson(nb):
    # ───────────────────────────── Cabecera ─────────────────────────────
    nb.md(nb.badge() + r'''

# Módulo 18 · Embeddings y retrieval en producción

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) · **GPU:** no necesaria (CPU en `FAST_DEV_RUN`; T4 opcional para medir throughput real de un embedder) · **Cómputo estimado:** 0 unidades de Colab en CPU; ≈ 1–2 unidades si usas T4 con `FAST_DEV_RUN=False`.

**Prerrequisitos:** 12 (embedders, Matryoshka, int8/binaria), 13 (híbrido y RRF), 14 (ANN y medición p50/p99), 15 (bootstrap pareado, drift), 17 (vec2text).

> 🧭 **Ruta núcleo vs ampliación.** Núcleo (≈ 2 h, lo que usa el proyecto): §1 costes · §2 batching · §4 caché · §5 versionado y migración · §7 vector DB y filtros. Ampliación (≈ 1 h): §3 colas y *tail latency* (y 3b, servidores) · §6 cuantización · §8 privacidad · §9 drift · §10 A/B e interleaving. Si vas justo de tiempo, ejecuta la ampliación sin estudiarla y vuelve a ella la semana siguiente (repaso espaciado).

**Hilo conductor — Políglota.** El prototipo funciona en un notebook. Ahora hay 2 M de usuarios potenciales, una factura que pagar y un modelo nuevo (v2) que el equipo quiere desplegar **sin reindexar a ciegas**. Hoy conviertes Políglota en un servicio: con costes calculados, latencia medida, caché, versionado, filtros, privacidad, monitorización y un plan de migración con números.

> **Estado del arte a octubre de 2026.** Toda cifra de precio o de producto lleva fecha y fuente; los supuestos de hardware están marcados como **supuesto** (no medidos aquí). Fuera de alcance: MLOps general (CI/CD, Kubernetes) y serving de LLMs generativos.
''')
    nb.md(r'''## 🎯 Objetivos de aprendizaje
1. **Calcular** el coste de embeber un corpus y de servir consultas con API vs GPU propia, con fórmulas y supuestos explícitos, y encontrar el punto de equilibrio.
2. **Medir** el efecto del tamaño de lote y del *padding* en el throughput de un encoder, y **simular** micro-batching dinámico para razonar p50/p99.
3. **Explicar** la amplificación de cola (*tail at scale*) con *fan-out* y **mitigarla** con *hedged requests*.
4. **Implementar** una caché de embeddings con la versión del modelo en la clave y medir el hit rate en tráfico tipo Zipf.
5. **Implementar y medir** la migración de embedder: re-embedding completo vs **adaptador lineal** (ridge / Procrustes) en función de los pares disponibles.
6. **Operar** una vector DB ligera (Qdrant en modo local, o FAISS como respaldo) con *named vectors* por versión y **filtros** por metadatos, y combinarla con BM25.
7. **Cuantificar** riesgos de privacidad (inversión de embeddings), **detectar drift** con PSI y **comparar** A/B vs interleaving por potencia estadística.
''')
    nb.md(r'''## 🔁 Conexión con módulos anteriores
<details><summary><b>1 · (M12, cálculo)</b> ¿Cuánta RAM ocupan 10 M de vectores de 768 dims en float32, int8 y binario?</summary>

$10^7 \times 768 \times 4$ B = **30.7 GB**; int8 = **7.7 GB**; binario (1 bit/dim) = **0.96 GB**. Hoy veremos qué parte de esa memoria debe vivir en RAM y cuál puede ir a disco (rescoring).
</details>
<details><summary><b>2 · (M14)</b> ¿Por qué medimos latencia con batch = 1 y reportamos p99 y no la media?</summary>

Porque en producción cada usuario espera **su** consulta; la media esconde la cola. El p99 es lo que ve 1 de cada 100 usuarios y, con *fan-out* a varios shards, la cola se amplifica (§3).
</details>
<details><summary><b>3 · (M15)</b> ¿Qué test usas para decir que v2 es mejor que v1 sobre el mismo golden set?</summary>

Un test **pareado** sobre las mismas queries (bootstrap pareado o permutación de signos), con IC de la diferencia. Lo reutilizamos tal cual (`paired_bootstrap` de `poliglota_eval.py`).
</details>
<details><summary><b>4 · (M17)</b> ¿Qué demostró vec2text sobre los embeddings de texto?</summary>

Que un embedding **no es un hash**: con acceso al embedder, se puede reconstruir gran parte del texto original (Morris et al. 2023). Consecuencia en producción: los vectores son **datos sensibles** y heredan la clasificación de privacidad del texto (§8).
</details>
<details><summary><b>5 · (M04 + M00, cálculo)</b> El corpus de Políglota es mitad español y mitad inglés. Si la prima de tokens del español frente al inglés es 1.3 con tu tokenizer, ¿cuánto sube la factura de una API que cobra por token respecto a un corpus todo en inglés del mismo contenido?</summary>

Factura ∝ tokens: $0.5\cdot 1 + 0.5\cdot 1.3 = 1.15$ → **+15 %**. La prima de tokens del módulo 04 no es una curiosidad lingüística: es una línea de la factura (módulo 00) y del throughput de la GPU propia (§1–§2). Por eso la §1 estima tokens con bytes/token y avisa de que el español y el código pagan más.
</details>
<details><summary><b>6 · (M01, diagnóstico)</b> Dos usuarios buscan «café»; uno lo teclea en NFC (`é` = U+00E9) y otro en NFD (`e` + U+0301). Si la caché hashea el texto tal cual, ¿aciertan la misma entrada?</summary>

No: son secuencias de code points (y de bytes UTF-8) distintas, así que el hash difiere y la segunda es un fallo de caché aunque el embedding sea el mismo. Por eso en la §4 **se normaliza antes de hashear** (NFC del módulo 01, más minúsculas y espacios).
</details>
''')

    # ───────────────────────────── Intuición ─────────────────────────────
    nb.md(r'''## 💡 Intuición: dos caminos, dos presupuestos
Un sistema de retrieval en producción tiene **dos rutas** con restricciones opuestas:

* **Ruta offline (indexación):** embeber millones de documentos. Importa el **throughput** (tokens/s/$) y la **reproducibilidad** (qué versión generó cada vector). La latencia de un documento da igual.
* **Ruta online (consulta):** embeber una query corta y buscar. Importa la **latencia de cola** (p99) y la **disponibilidad**. El coste por query es diminuto, pero se multiplica por millones.

Analogía con recsys: es el mismo patrón que un *two-tower* (torre de ítems precalculada offline, torre de usuario online). La diferencia: aquí **cambiar de modelo invalida todo el índice**, porque query y documentos deben vivir en el mismo espacio (§5).
''')
    nb.gemini(
        "imagen", "M18-IMG-01", "Arquitectura de un servicio de embeddings en producción",
        "Las dos rutas (offline de indexación y online de consulta) y las piezas que este módulo mide: caché, batching, índice versionado, filtros y monitorización.",
        """Diagrama técnico limpio, fondo blanco, paleta sobria: azul #1F6FEB (ruta online), naranja #F28E2B (ruta offline), verde #2CA02C (monitorización), gris #6B7280 (almacenamiento). Tipografía sans-serif legible, flechas claras, sin ilustraciones decorativas.
Composición en dos bandas horizontales.
Banda superior (naranja), de izquierda a derecha, con el título "Ruta offline (indexación)": cajas "Documentos ES/EN/código" → "Chunking" → "Caché por contenido (hash + versión)" → "Embedder v1/v2 (lotes grandes, GPU)" → "Índice vectorial versionado (colección v1 · colección v2)". Debajo de la flecha del embedder, texto pequeño "throughput: tokens/s/$".
Banda inferior (azul), con el título "Ruta online (consulta)": "Usuario" → "API /search" → "Caché de queries (LRU, clave = versión + texto normalizado)" → "Embedder (micro-batching)" → "Búsqueda: denso + BM25 + filtro idioma" → "Fusión RRF" → "Top-10". Texto pequeño bajo la API: "SLA: p99 ≤ 100 ms".
Una caja gris a la derecha "Alias prod → v1" conectada con línea discontinua a la colección v1, y otra línea discontinua gris hacia v2 con la etiqueta "migración (blue/green)".
Abajo, una franja verde que recorre todo el ancho: "Monitorización: p50/p99 · hit rate · drift (PSI) · A/B · privacidad".
Evita: logotipos de empresas, texto ilegible, flechas cruzadas, iconos decorativos, cifras inventadas.""",
        "Diagrama de dos bandas: ruta offline de indexación arriba y ruta online de consulta abajo, con caché, embedder, índice versionado, fusión y monitorización.",
        """
OFFLINE: Docs → Chunking → Caché(hash+versión) → Embedder (lotes) → Índice v1 | v2
                                                                   ↑ alias prod → v1
ONLINE : Usuario → /search → Caché LRU(versión+texto) → Embedder → denso+BM25+filtro → RRF → top-10
MONITOR: p50/p99 · hit rate · drift (PSI) · A/B · privacidad
""")
    nb.md(r'''> 👀 **Qué debes observar:** cada caja de la figura es una sección de esta lección y tiene **una métrica**: throughput y $ (offline), p99 y hit rate (online), PSI y potencia estadística (monitorización). Si no puedes ponerle número a una caja, todavía no está en producción.''')

    # ───────────────────────────── Setup ─────────────────────────────
    nb.md("## 0. Preparación\nCorpus, métricas y BM25 canónicos (módulo 00), embedders con fallback (módulo 12) y estadística pareada (módulo 15), copiados para que el notebook sea autocontenido.")
    nb.code(C.CODE_PIP)
    nb.code(C.CODE_SETUP)
    for src in C.src_corpus_cells():
        nb.code(src)
    nb.code(C.SRC_METRICS)
    nb.code(C.SRC_BM25)
    nb.code(C.STATS_SRC)
    nb.code(C.CODE_EMBEDDER_TOOLS)
    nb.code(C.CODE_LOAD)
    nb.code(C.CODE_HELPERS)
    nb.code(C.CODE_VERSIONES)
    nb.md(r'''> ⚠️ **Sobre las cifras.** En el entorno de autoría Hugging Face estaba bloqueado: v1 y v2 son los *fallbacks* TF-IDF+SVD (v1: n-gramas 3-4 → 48 d; v2: n-gramas 2-5 → 128 d). Son espacios **distintos e incompatibles**, que es exactamente lo que importa para la migración. Con red, la celda usa `multilingual-e5-small` (v1) y `multilingual-e5-base` (v2).''')

    # ───────────────────────────── §1 Costes ─────────────────────────────
    nb.md(r'''## 1. Costes: API vs GPU propia
📐 **Fórmulas.** Sea $T$ el número de tokens a embeber.

* **API** (pago por token): $\;C_\text{API} = \dfrac{T}{10^6}\, p$, con $p$ = USD por millón de tokens de entrada.
* **GPU propia** (pago por hora): $\;C_\text{GPU} = \dfrac{T}{\theta \cdot 3600 \cdot u}\, h$, con $\theta$ = tokens/s **medidos** de tu embedder en esa GPU, $u \in (0,1]$ = utilización efectiva (colas, picos, despliegues) y $h$ = USD/hora de la GPU.
* **Servicio online 24/7**: la GPU se paga aunque no haya tráfico. Con $G$ GPUs dedicadas al mes: $C = G \cdot 730 \cdot h$, con $G = \lceil T_\text{mes} / (\theta \cdot 3600 \cdot 730 \cdot u) \rceil$ (mínimo 1, o 2 para alta disponibilidad).

**Punto de equilibrio** (una GPU dedicada vs API): $T^\* = 730\,h \cdot 10^6 / p$ tokens/mes, siempre que una GPU dé abasto con $T^\*$.

✍️ **Ejemplo a mano (hazlo antes de ejecutar).** GPU a $h = 0.80$ $/h, 24/7: $730 \cdot 0.80 = 584$ $/mes, la uses o no. Frente a una API de $p = 0.02$ $/1M: $T^\* = 584 \cdot 10^6 / 0.02 = 2.92\times10^{10}$ tokens/mes. ¿Da abasto una GPU? Con $\theta = 20\,000$ tok/s y $u = 0.6$: $20\,000 \cdot 3600 \cdot 730 \cdot 0.6 = 3.15\times10^{10}$ tokens/mes, apenas por encima de $T^\*$. Frente a $p = 0.13$: $T^\* = 4.49\times10^{9}$, siete veces menos. Lectura: contra la API más barata, autohospedar solo compensa con la GPU casi llena. Es el mismo razonamiento de *build vs buy* que un coste fijo (servidor) frente a uno variable (por uso) en cualquier sistema; la celda siguiente lo dibuja con la tabla de precios.

Los **precios** de abajo son tarifas estándar publicadas (consultadas en oct-2026; cambian a menudo y algunas APIs tienen descuento por lotes asíncronos: **verifícalos**). El throughput y el precio de la GPU son **supuestos ilustrativos**: mídelos con tu modelo (la §2 enseña cómo).''')
    nb.code(r'''
PRECIOS_API = {                       # USD por 1M tokens de entrada, tarifa estándar (consultado oct-2026; VERIFICA)
    "OpenAI text-embedding-3-small": 0.02,
    "OpenAI text-embedding-3-large": 0.13,
    "Google gemini-embedding-001": 0.15,
}
GPU_USD_HORA = 0.80    # SUPUESTO: GPU de inferencia tipo L4 bajo demanda (varía por proveedor y región)
GPU_TOK_S = 20_000     # SUPUESTO: tokens/s de un encoder de ~100-300 M parámetros, fp16, lotes grandes. ¡MÍDELO!
UTIL = 0.6             # SUPUESTO: utilización efectiva

def coste_api(n_tokens, precio):
    return n_tokens / 1e6 * precio

def coste_gpu(n_tokens, usd_h=GPU_USD_HORA, tok_s=GPU_TOK_S, util=UTIL):
    return n_tokens / (tok_s * 3600 * util) * usd_h

def horas_gpu(n_tokens, tok_s=GPU_TOK_S, util=UTIL):
    return n_tokens / (tok_s * 3600 * util)

# Tokens del corpus: aproximación de 4 bytes/token (inglés con BPE ~ 4; el español y el código pagan más, módulo 04)
tok_corpus = sum(len(t.encode("utf-8")) for t in doc_texts) / 4
N_PROD, TOK_POR_CHUNK = 10_000_000, 400          # escenario Políglota a escala: 10 M de chunks de ~400 tokens
T_PROD = N_PROD * TOK_POR_CHUNK
filas = [{"opción": k, "corpus del notebook ($)": coste_api(tok_corpus, p), "re-embedding 10 M chunks ($)": coste_api(T_PROD, p)}
         for k, p in PRECIOS_API.items()]
filas.append({"opción": f"GPU propia (supuesto {GPU_TOK_S:,} tok/s, ${GPU_USD_HORA}/h)",
              "corpus del notebook ($)": coste_gpu(tok_corpus), "re-embedding 10 M chunks ($)": coste_gpu(T_PROD)})
print(f"Corpus del notebook ≈ {tok_corpus:,.0f} tokens · escenario = {T_PROD/1e9:.0f} B tokens · GPU: {horas_gpu(T_PROD):.0f} h")
pd.DataFrame(filas).round(4)
''')
    nb.code(r'''
# Coste MENSUAL de servir/embeber T_mes tokens: API (lineal) vs GPUs dedicadas (escalón, mínimo 1)
T_mes = np.logspace(8, 12, 200)
cap_gpu_mes = GPU_TOK_S * 3600 * 730 * UTIL
G = np.maximum(1, np.ceil(T_mes / cap_gpu_mes))
fig, ax = plt.subplots(figsize=(8, 4.5))
for (k, p), c in zip(PRECIOS_API.items(), [AZUL, NARANJA, VERDE]):
    ax.loglog(T_mes, coste_api(T_mes, p), color=c, label=f"API · {k} (${p}/1M)")
ax.loglog(T_mes, G * 730 * GPU_USD_HORA, color=GRIS, lw=2.5, label="GPU dedicada 24/7 (supuesto)")
for p, c in zip(PRECIOS_API.values(), [AZUL, NARANJA, VERDE]):
    t_eq = 730 * GPU_USD_HORA * 1e6 / p
    ax.axvline(t_eq, color=c, ls=":", lw=1)
ax.set_xlabel("tokens embebidos al mes"); ax.set_ylabel("USD / mes")
ax.set_title("Coste mensual: API por token vs GPU dedicada (precios oct-2026 + supuestos)")
ax.legend(fontsize=8); plt.tight_layout(); plt.show()
for k, p in PRECIOS_API.items():
    print(f"equilibrio con {k}: {730 * GPU_USD_HORA * 1e6 / p:.2e} tokens/mes (capacidad de 1 GPU: {cap_gpu_mes:.2e})")
''')
    nb.md(r'''> 👀 **Qué debes observar:** con estos supuestos, una GPU dedicada solo compensa frente a la API más barata **cerca de su capacidad máxima** (decenas de miles de millones de tokens al mes); frente a APIs de ~0.13–0.15 $/1M el equilibrio llega mucho antes. Las líneas punteadas son los puntos de equilibrio. Pero el $ no es el único eje: **latencia de red, residencia de datos, cuotas (rate limits) y control de versión del modelo** (una API puede retirar un modelo) empujan a autohospedar aunque cueste más.

🧠 El coste real de una migración no es el re-embedding (≈ decenas–cientos de $ para 4 B tokens según la tabla) sino **el doble índice durante semanas, la evaluación y el riesgo**. Por eso §5 mide alternativas.''')

    # ───────────────────────────── §2 Batching ─────────────────────────────
    nb.md(r'''## 2. Batching y padding: el throughput se gana en la forma del tensor
Un encoder procesa un lote como un tensor $(B, L_\max)$: todas las secuencias se **rellenan** (*padding*) hasta la más larga del lote. El trabajo útil es $\sum_i L_i$; el pagado es $B \cdot L_\max$ (y la atención crece con $L_\max^2$). Dos palancas:
1. **Lotes más grandes** amortizan el coste fijo por llamada (lanzamiento de kernels, Python, transferencia).
2. **Ordenar por longitud** (*length bucketing*) antes de cortar lotes reduce el relleno. TEI y sentence-transformers lo hacen internamente.

🧪 Medimos ambas con un encoder Transformer diminuto de **pesos aleatorios** (el coste depende de la forma, no de los pesos) y longitudes realistas sacadas del corpus.''')
    nb.code(r'''
import torch.nn as nn

class MiniEncoder(nn.Module):
    """Encoder de 2 capas, d=128, mean pooling con máscara. Solo para medir coste (pesos aleatorios)."""
    def __init__(self, vocab=8000, d=128, capas=2, cabezas=4):
        super().__init__()
        self.emb = nn.Embedding(vocab, d)
        capa = nn.TransformerEncoderLayer(d, cabezas, 4 * d, dropout=0.0, batch_first=True)
        self.enc = nn.TransformerEncoder(capa, capas, enable_nested_tensor=False)
    def forward(self, ids, mask):
        h = self.enc(self.emb(ids), src_key_padding_mask=~mask)
        m = mask.unsqueeze(-1).float()
        return (h * m).sum(1) / m.sum(1).clamp(min=1)

MAX_LEN = 256
long_tok = np.clip((np.array([len(t.split()) for t in doc_texts]) * 1.4).astype(int), 4, MAX_LEN)  # ~1.4 tokens/palabra
enc = MiniEncoder().eval()

def mide_throughput(longitudes, B, ordenar):
    orden = np.argsort(longitudes) if ordenar else np.arange(len(longitudes))
    util = pagado = 0; t0 = time.perf_counter()
    with torch.inference_mode():
        for s in range(0, len(orden), B):
            L = longitudes[orden[s:s + B]]; Lmax = int(L.max())
            ids = torch.randint(0, 8000, (len(L), Lmax))
            mask = torch.arange(Lmax)[None, :] < torch.as_tensor(L)[:, None]
            enc(ids, mask); util += int(L.sum()); pagado += len(L) * Lmax
    return util / (time.perf_counter() - t0), 1 - util / pagado

n_med = 160 if FAST_DEV_RUN else len(long_tok)
filas = []
for B in [1, 2, 4, 8, 16, 32, 64]:
    for ordenar in (False, True):
        tps, pad = mide_throughput(long_tok[:n_med], B, ordenar)
        filas.append({"B": B, "ordenado": ordenar, "tokens_utiles_s": tps, "padding": pad})
df_batch = pd.DataFrame(filas)
df_batch.pivot(index="B", columns="ordenado", values=["tokens_utiles_s", "padding"]).round(2)
''')
    nb.code(r'''
fig, axs = plt.subplots(1, 2, figsize=(11, 4))
for ordenar, c, et in ((False, NARANJA, "orden original"), (True, AZUL, "ordenado por longitud")):
    d = df_batch[df_batch.ordenado == ordenar]
    axs[0].plot(d.B, d.tokens_utiles_s, "o-", color=c, label=et)
    axs[1].plot(d.B, 100 * d.padding, "o-", color=c, label=et)
axs[0].set_xscale("log", base=2); axs[1].set_xscale("log", base=2)
axs[0].set_xlabel("tamaño de lote B"); axs[0].set_ylabel("tokens útiles / s (CPU, 1 hilo)")
axs[1].set_xlabel("tamaño de lote B"); axs[1].set_ylabel("% de cómputo gastado en padding")
axs[0].set_title("Throughput vs tamaño de lote"); axs[1].set_title("Desperdicio por padding")
axs[0].legend(); plt.tight_layout(); plt.show()
''')
    nb.md(r'''> 👀 **Qué debes observar:** (1) sin ordenar, el padding crece con $B$ (cada lote se rellena hasta su texto más largo) y se come parte de la ganancia del lote; (2) ordenando por longitud el padding queda casi en 0 y, para casi todo $B$, el throughput es mayor; (3) en CPU con **un hilo** la ganancia por lote se satura pronto (pocas unidades de cómputo que llenar; lotes grandes alargan $L_\max$ y la atención crece con $L_\max^2$) y la curva es ruidosa. En GPU el efecto del tamaño de lote es mucho mayor (miles de núcleos que llenar), hasta que se agota la memoria. **Esta celda es la forma correcta de obtener $\theta$** para la fórmula de costes: mide con tu modelo, tu hardware y tus longitudes reales, y repite varias veces.''')

    # ───────────────────────────── §3 Colas y cola larga ─────────────────────────────
    nb.md(r'''## 3. Latencia p50/p99: micro-batching dinámico y *tail at scale*
En la ruta online las queries llegan **una a una**. Un servidor con *micro-batching dinámico* (TEI, Triton, vLLM) espera hasta `max_wait` ms o hasta reunir `max_batch` peticiones y las procesa juntas. Modelo de coste de un lote: $t(B) = a + bB$ ($a$ = coste fijo, $b$ = coste marginal). Capacidad: $B/(a+bB)$ peticiones/ms, que crece con $B$.

Trade-off: esperar **suma latencia** a las primeras peticiones del lote pero **sube la capacidad**; cuando la carga se acerca a la capacidad sin lotes, la cola explota y el p99 se dispara.''')
    nb.gemini(
        "imagen", "M18-IMG-02", "Micro-batching dinámico en un servidor de embeddings",
        "Cómo un servidor agrupa peticiones que llegan una a una en lotes limitados por max_batch y max_wait, y por qué eso cambia p50 y p99.",
        """Diagrama técnico limpio, fondo blanco, paleta: azul #1F6FEB (peticiones), naranja #F28E2B (lote), verde #2CA02C (GPU), gris #6B7280 (eje de tiempo). Sans-serif legible.
Eje horizontal de tiempo en la parte inferior con la etiqueta "tiempo (ms)".
Arriba, a la izquierda, pequeñas flechas azules verticales que llegan a distintos instantes, etiquetadas "q1", "q2", "q3", "q4", "q5".
En el centro, un rectángulo naranja llamado "Cola del servidor" que agrupa q1, q2 y q3 con una llave y el texto "lote 1: se cierra por max_wait = 5 ms"; luego q4 y q5 agrupadas como "lote 2: se cierra por max_batch".
A la derecha, una caja verde "GPU: t(B) = a + b·B" que recibe cada lote.
Debajo de q1, una barra horizontal azul que muestra su latencia total dividida en dos tramos con texto: "espera en cola" (gris claro) y "cómputo del lote" (verde).
Esquina superior derecha: dos casillas de texto "max_batch = 32" y "max_wait = 5 ms".
Evita: números de rendimiento inventados, logotipos, iconos decorativos, flechas ambiguas.""",
        "Peticiones que llegan una a una se agrupan en lotes que se cierran por tiempo máximo de espera o por tamaño máximo, y se procesan en la GPU.",
        """
q1   q2 q3          q4 q5 ... →  tiempo
 |----lote 1 (cierra por max_wait=5ms)----|→ GPU t(B)=a+bB
                    |--lote 2 (cierra por max_batch)--|→ GPU
latencia(q1) = espera en cola + cómputo del lote
""")
    nb.md("> 👀 **Qué debes observar:** la primera petición de cada lote es la que más espera; `max_wait` acota esa espera. Ese tramo gris es el precio que pagas por la capacidad extra del lote.")
    nb.code(r'''
def simula_microbatch(qps, max_batch, max_wait_ms, a_ms=4.0, b_ms=0.5, n=4000, seed=SEED):
    """Un servidor: cierra el lote cuando hay max_batch peticiones o la más antigua lleva max_wait_ms (o cuando queda libre).
    t(B) = a + b·B (SUPUESTO ilustrativo: a = 4 ms fijos, b = 0.5 ms por query corta). Devuelve latencias (ms)."""
    rng = np.random.default_rng(seed)
    llegadas = np.cumsum(rng.exponential(1000.0 / qps, n))
    lat = np.empty(n); libre, i = 0.0, 0
    while i < n:
        limite = max(llegadas[i] + max_wait_ms, libre)
        j = i
        while j < n and j - i < max_batch and llegadas[j] <= limite:
            j += 1
        inicio = max(llegadas[j - 1], libre) if j - i == max_batch else limite
        fin = inicio + a_ms + b_ms * (j - i)
        lat[i:j] = fin - llegadas[i:j]; libre, i = fin, j
    return lat

esperas = [0, 1, 2, 5, 10, 20]
res = {qps: [np.percentile(simula_microbatch(qps, 32, w), [50, 99]) for w in esperas] for qps in (100, 200, 600)}
fig, ax = plt.subplots(figsize=(8, 4))
for (qps, r), c in zip(res.items(), [VERDE, AZUL, NARANJA]):
    r = np.array(r)
    ax.plot(esperas, r[:, 1], "o-", color=c, label=f"{qps} QPS · p99"); ax.plot(esperas, r[:, 0], "o--", color=c, alpha=.6, label=f"{qps} QPS · p50")
ax.set_yscale("log"); ax.set_xlabel("max_wait (ms)"); ax.set_ylabel("latencia (ms, log)")
ax.set_title("Micro-batching: p50/p99 vs max_wait (max_batch=32, t(B)=4+0.5·B ms, supuesto)")
ax.legend(fontsize=8, ncol=2); plt.tight_layout(); plt.show()
print("capacidad sin lotes ≈", round(1000 / 4.5), "QPS · con B=32 ≈", round(32 * 1000 / (4 + 0.5 * 32)), "QPS")
''')
    nb.md(r'''> 👀 **Qué debes observar:** a carga baja (100 QPS) esperar solo empeora la latencia: casi no hay con quién formar lote. Cerca de la capacidad sin lotes (≈ 222 QPS) y por encima (600 QPS), un `max_wait` de pocos ms **baja el p99 en órdenes de magnitud** porque evita que la cola crezca sin límite. El `max_wait` óptimo depende de la carga: por eso los servidores lo exponen como parámetro (y por eso se mide con tráfico realista, no con un bucle secuencial).

### La cola se amplifica con el *fan-out*
Si el índice está repartido en $S$ shards y la query espera al **más lento**, la probabilidad de tocar al menos un shard lento es $1-(1-p)^S$. Con $p = 1\%$ y $S = 64$, ¡el 47 % de las queries ve la cola! (Dean & Barroso, *The Tail at Scale*, 2013). Mitigación clásica: **hedged requests**: si un shard no responde antes de su p95, se lanza una réplica y se usa la primera respuesta.''')
    nb.code(r'''
def latencia_shards(S, n=20000, p_lento=0.01, hedge=False, seed=SEED):
    """Latencia por shard ~ lognormal(5 ms) con un 1 % de eventos lentos x10 (GC, compactación...). Query = máximo de S shards.
    hedge=True: si un shard supera su p95, se lanza una réplica en ese instante y gana la primera en responder."""
    rng = np.random.default_rng(seed)
    def muestra(size):
        t = rng.lognormal(np.log(5), 0.3, size)
        return np.where(rng.random(size) < p_lento, t * 10, t)
    t = muestra((n, S))
    if hedge:
        t95 = np.percentile(muestra(100000), 95)
        t = np.where(t > t95, np.minimum(t, t95 + muestra((n, S))), t)
    return t.max(axis=1)

Ss = [1, 2, 4, 8, 16, 32, 64]
p99 = [np.percentile(latencia_shards(S), 99) for S in Ss]
p99_h = [np.percentile(latencia_shards(S, hedge=True), 99) for S in Ss]
p50 = [np.percentile(latencia_shards(S), 50) for S in Ss]
fig, axs = plt.subplots(1, 2, figsize=(11, 4))
axs[0].plot(Ss, p99, "o-", color=NARANJA, label="p99 sin hedge"); axs[0].plot(Ss, p99_h, "o-", color=AZUL, label="p99 con hedged requests")
axs[0].plot(Ss, p50, "o--", color=GRIS, label="p50"); axs[0].set_xscale("log", base=2)
axs[0].set_xlabel("nº de shards (fan-out)"); axs[0].set_ylabel("latencia de la query (ms)"); axs[0].legend(); axs[0].set_title("La cola crece con el fan-out")
sim = [np.mean(latencia_shards(S) > 30) for S in Ss]
axs[1].plot(Ss, [1 - 0.99 ** S for S in Ss], "-", color=GRIS, label="teórico 1-(1-p)^S"); axs[1].plot(Ss, sim, "o", color=NARANJA, label="simulado (latencia > 30 ms)")
axs[1].set_xscale("log", base=2); axs[1].set_xlabel("nº de shards"); axs[1].set_ylabel("P(query lenta)"); axs[1].legend(); axs[1].set_title("Probabilidad de tocar un shard lento")
plt.tight_layout(); plt.show()
''')
    nb.md(r'''> 👀 **Qué debes observar:** el p50 apenas se mueve con más shards, pero el p99 salta a la latencia de los eventos lentos en cuanto $S$ supera ~16–32. Las *hedged requests* cuestan ≈ 5 % de peticiones extra (las que superan el p95) y devuelven el p99 cerca del p50. Lección de diseño: **no shardees un índice que cabe en una máquina**; con 10 M de vectores int8 de 768 d (7.7 GB) una réplica entera es más simple y más rápida que un *fan-out*.''')

    # ───────────────────────────── §TEI/vLLM ─────────────────────────────
    nb.md(r'''## 3b. Servidores de embeddings: TEI y vLLM (referencia práctica)
No escribas tu propio servidor de inferencia para producción: usa uno que ya implemente micro-batching, ordenación por longitud, truncado y métricas.

**Text Embeddings Inference (TEI, Hugging Face).** Binario en Rust con imágenes Docker por arquitectura. Ejemplo (fija una versión concreta: las notas de la v1.8.1 publican `cpu-1.8.1` y `cuda-1.8.1`; a oct-2026 existen versiones 1.9.x: **comprueba la etiqueta en la página de *releases***):
```bash
docker run -p 8080:80 -v $PWD/data:/data ghcr.io/huggingface/text-embeddings-inference:cpu-1.8.1 \
    --model-id intfloat/multilingual-e5-small --max-batch-tokens 16384
curl localhost:8080/embed -X POST -H 'Content-Type: application/json' -d '{"inputs": ["query: ¿cómo invalido la caché?"]}'
```
⚠️ Según sus notas de versión, TEI 1.9.0 cambió valores por defecto (p. ej. `--auto-truncate` pasa a `true` y la GeLU por defecto usa la aproximación tanh): **cambiar la versión del servidor puede cambiar tus vectores**. Trátala como parte de la versión del modelo.

**vLLM.** Sirve modelos de *pooling* (embeddings, rerankers) con `--runner pooling` (normalmente se detecta solo) y expone una API compatible con OpenAI (`/v1/embeddings`). Útil sobre todo para **LLM-as-embedder** (Qwen3-Embedding, e5-mistral), donde reutiliza su gestión de memoria:
```bash
vllm serve Qwen/Qwen3-Embedding-0.6B --runner pooling
```
La celda siguiente es un cliente mínimo: solo se ejecuta si defines la variable de entorno `TEI_URL` (no se pudo probar en el entorno de autoría: sin Docker ni acceso al hub).''')
    nb.code(r'''
def embed_tei(textos, url=os.environ.get("TEI_URL"), lote=32, timeout=30):
    """Cliente mínimo de TEI (/embed). Lotes en el cliente + reintentos con backoff exponencial."""
    import urllib.request
    out = []
    for s in range(0, len(textos), lote):
        cuerpo = json.dumps({"inputs": textos[s:s + lote], "normalize": True}).encode()
        for intento in range(4):
            try:
                req = urllib.request.Request(f"{url}/embed", data=cuerpo, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    out += json.load(r); break
            except Exception:
                if intento == 3:
                    raise
                time.sleep(0.5 * 2 ** intento * random.uniform(0.5, 1.5))
    return np.array(out, dtype=np.float32)

if os.environ.get("TEI_URL"):
    E = embed_tei(["query: hola mundo", "passage: hello world"]); print(E.shape)
else:
    print("TEI_URL no definida: cliente TEI omitido (celda opcional).")
''')

    # ───────────────────────────── §4 Caché ─────────────────────────────
    nb.md(r'''## 4. Caché: el embedding más barato es el que no calculas
Dos cachés distintas:
* **Caché de documentos (offline)**: clave = `hash(texto del chunk) + versión del modelo`. Al reindexar, solo se embeben los chunks nuevos o modificados (en documentación técnica, la mayoría no cambia entre releases).
* **Caché de queries (online)**: el tráfico de búsqueda sigue una ley de **Zipf**: pocas queries concentran mucho tráfico. Una LRU pequeña absorbe una fracción grande.

Dos reglas: **la versión del modelo va en la clave** y **se normaliza antes de hashear** (NFC, minúsculas, espacios). Implementamos la LRU (la misma que usarás en el proyecto) y medimos con tráfico simulado.''')
    nb.code(C.CODE_CACHE)
    nb.code(r'''
def trafico_zipf(n, universo, s=1.1, p_variante=0.35, seed=SEED):
    """n queries de un universo de 'intenciones' con frecuencia Zipf; parte llegan con variantes superficiales."""
    rng = np.random.default_rng(seed)
    p = 1.0 / np.arange(1, len(universo) + 1) ** s; p /= p.sum()
    out = []
    for i in rng.choice(len(universo), size=n, p=p):
        t = universo[i]
        if rng.random() < p_variante:
            t = rng.choice([t.upper(), t.capitalize(), "  " + t, t.replace(" ", "  "), t + " "])
        out.append(t)
    return out

universo = [f"{q_texts[i % len(q_texts)]}" + ("" if i < len(q_texts) else f" {i // len(q_texts)}") for i in range(3000)]
stream = trafico_zipf(20000, universo)
caps = [16, 64, 256, 1024, 4096]
hr = {"con normalización": [], "sin normalización": []}
for cap in caps:
    for modo in hr:
        c = LRUCache(cap)
        for t in stream:
            k = clave_cache("v2", t) if modo == "con normalización" else hashlib.sha1(f"v2\x00{t}".encode()).hexdigest()
            if c.get(k) is None:
                c.put(k, 1)
        hr[modo].append(c.hit_rate)
t0 = time.perf_counter(); VERS["v2"].encode_queries(q_texts[:50]); t_q = (time.perf_counter() - t0) / 50 * 1e3
fig, ax = plt.subplots(figsize=(7.5, 4))
for (m, v), c in zip(hr.items(), [AZUL, NARANJA]):
    ax.plot(caps, v, "o-", color=c, label=m)
ax.set_xscale("log", base=2); ax.set_xlabel("capacidad de la caché (entradas)"); ax.set_ylabel("hit rate")
ax.set_title("Caché LRU de queries con tráfico Zipf (s=1.1, 3 000 intenciones)"); ax.legend(); plt.tight_layout(); plt.show()
print(f"encode de una query (v2, CPU): {t_q:.2f} ms · ahorro medio con cap=1024: {hr['con normalización'][3] * t_q:.2f} ms/query")
''')
    nb.md(r'''> 👀 **Qué debes observar:** con Zipf, unas pocas centenas de entradas ya dan un hit rate alto, y **normalizar** antes de hashear suma decenas de puntos gratis (las variantes de mayúsculas/espacios dejan de ser fallos). La curva se aplana: duplicar la caché más allá de cierto punto apenas mejora. Con un embedder real en GPU remota, cada acierto ahorra un viaje de red + inferencia (ms), no microsegundos.

### ⚠️ El bug silencioso: la versión fuera de la clave
Simulamos que reentrenamos v2 (mismo tamaño, espacio rotado: lo que pasa al hacer *fine-tuning*) y re-indexamos, pero la caché sigue sirviendo vectores de la versión anterior:''')
    nb.code(r'''
rng = np.random.default_rng(SEED)
R, _ = np.linalg.qr(rng.normal(size=(EMB["v2"]["D"].shape[1],) * 2))   # rotación ortogonal: mismo modelo "reentrenado"
D_nuevo, Q_nuevo = EMB["v2"]["D"] @ R, EMB["v2"]["Q"] @ R
ok = evaluate(run_desde_scores(Q_nuevo @ D_nuevo.T), qrels)["ndcg"]
stale = evaluate(run_desde_scores(EMB["v2"]["Q"] @ D_nuevo.T), qrels)["ndcg"]
print(f"queries nuevas vs índice nuevo: nDCG@10 = {ok:.3f}")
print(f"queries de la CACHÉ VIEJA vs índice nuevo: nDCG@10 = {stale:.3f}   <- sin error, sin excepción, mismas dimensiones")
''')
    nb.md("> 👀 **Qué debes observar:** la calidad es idéntica con vectores coherentes y se hunde casi a azar con vectores de la versión anterior, **sin ningún error**: mismas dimensiones, mismos tipos. Por eso la versión del modelo (y del servidor, y del preprocesado) va en la clave de caché y en los metadatos de cada vector.")

    # ───────────────────────────── §6 Migración ─────────────────────────────
    nb.md(r'''## 5. Versionado y migración de embedders
Cambiar de embedder es la operación más cara y arriesgada de un sistema de retrieval: los vectores de v1 y v2 **no son comparables**. Opciones:

| Estrategia | Qué haces | Coste | Riesgo |
|---|---|---|---|
| **Re-embedding completo + blue/green** | Embebes todo con v2 en una colección nueva, evalúas, cambias el alias `prod` y conservas v1 para *rollback* | $T$ tokens + doble memoria durante la transición | bajo (rollback = cambiar el alias) |
| **Adaptador del lado de la query** | Aprendes $W$ con pares $(e_2(x), e_1(x))$ y consultas el índice v1 con $W e_2(q)$ | embeber una **muestra** con ambas versiones | calidad ≤ v1 + algo; deuda técnica |
| **Adaptador del lado del documento** | Proyectas el índice v1 al espacio v2 sin re-embeber | igual | no recupera lo que v1 no codificó |
| **Entrenamiento compatible hacia atrás** (BCT) | Entrenas v2 con una pérdida que lo mantiene comparable con v1 | entrenamiento | limita cuánto puede mejorar v2 |

📐 **Adaptador ridge:** $W^\* = \arg\min_W \lVert AW - B\rVert_F^2 + \lambda\lVert W\rVert_F^2 = (A^\top A + \lambda I)^{-1} A^\top B$, con $A \in \mathbb{R}^{n\times d_2}$ (embeddings v2 de $n$ textos) y $B \in \mathbb{R}^{n\times d_1}$ (los mismos textos con v1). **Procrustes ortogonal:** $W = UV^\top$ con $U\Sigma V^\top = \mathrm{SVD}(A^\top B)$: la mejor proyección que **conserva ángulos** (solo rota), menos expresiva pero más robusta con pocos pares.

🧪 Medimos nDCG@10 de las cuatro rutas en función de la fracción del corpus que embebemos con ambas versiones.''')
    nb.gemini(
        "video", "M18-VID-01", "Migración blue/green de un índice de embeddings",
        "La secuencia completa de una migración segura de v1 a v2: doble escritura, backfill, evaluación sombra, cambio de alias y rollback.",
        """Video de diagrama técnico animado, 16:9, fondo blanco, paleta sobria: azul #1F6FEB (v1), naranja #F28E2B (v2), verde #2CA02C (OK/evaluación), gris #6B7280 (infraestructura). Tipografía sans-serif grande y legible, sin voz en off, ritmo calmado, transiciones suaves.
0–5 s: aparece una caja gris "API /search" con una flecha hacia un cilindro azul "Colección v1 (prod)". Texto en pantalla: "Situación inicial: alias prod → v1".
5–11 s: aparece a la derecha un cilindro naranja vacío "Colección v2". Texto: "1. Crear colección nueva (sin tocar v1)".
11–18 s: una barra de progreso naranja se llena bajo v2 con el texto "2. Backfill: re-embeber todos los documentos con v2"; a la vez, flechas desde "Documentos nuevos" van a v1 y a v2. Texto: "Doble escritura durante el backfill".
18–25 s: desde "API /search" sale una flecha punteada hacia v2 con la etiqueta "tráfico sombra (no se muestra al usuario)"; aparece una caja verde "Evaluación: nDCG pareado + IC + interleaving". Texto: "3. Evaluar en sombra".
25–31 s: la flecha "alias prod" se desplaza de v1 a v2 con una animación suave. Texto: "4. Cambio atómico del alias prod → v2".
31–37 s: v1 queda en gris claro con el texto "conservada N días para rollback"; un botón "rollback = mover el alias" parpadea una vez. Texto final: "5. Retirar v1 cuando las métricas online lo confirmen".
Evita: logotipos de productos, texto pequeño, cifras inventadas, movimientos de cámara bruscos, música estridente.""",
        "Animación de una migración blue/green: crear colección v2, backfill con doble escritura, evaluación en sombra, cambio atómico del alias y rollback.",
        """
[API] ──alias prod──▶ [v1 ✔]          [v2 vacío]
1) crear v2   2) backfill + doble escritura   3) tráfico sombra → evaluación pareada
4) alias prod: v1 ──▶ v2 (atómico)    5) v1 retenida N días = rollback inmediato
""", duration="35-40 s")
    nb.md("> 👀 **Qué debes observar:** en ningún momento hay un índice a medio construir sirviendo tráfico; el cambio es un **puntero** (alias) y el rollback es moverlo de vuelta. El adaptador lineal que medimos a continuación es un **puente** para poder servir v2 antes de terminar el backfill (o cuando re-embeber es imposible), no un sustituto.")
    nb.code(C.CODE_ADAPTER)
    nb.code(r'''
D1, Q1, D2, Q2 = EMB["v1"]["D"], EMB["v1"]["Q"], EMB["v2"]["D"], EMB["v2"]["Q"]
nd = lambda S: evaluate(run_desde_scores(S), qrels)["ndcg"]
base = {"v1 nativo": nd(Q1 @ D1.T), "v2 re-embedding completo": nd(Q2 @ D2.T)}
fracs = [0.05, 0.1, 0.25, 0.5, 1.0]
curvas = {"query v2 → índice v1 (ridge)": [], "query v2 → índice v1 (Procrustes)": [], "índice v1 → espacio v2 (ridge)": []}
rng = np.random.default_rng(SEED)
for f in fracs:
    vals = {k: [] for k in curvas}
    for rep in range(3):                                      # 3 muestras aleatorias por fracción
        idx = rng.choice(len(doc_texts), max(8, int(f * len(doc_texts))), replace=False)
        W = ajusta_adaptador(D2[idx], D1[idx], lam=0.1)
        vals["query v2 → índice v1 (ridge)"].append(nd(l2n(Q2 @ W) @ D1.T))
        Wp = ajusta_adaptador(D2[idx], D1[idx], metodo="procrustes")
        vals["query v2 → índice v1 (Procrustes)"].append(nd(l2n(Q2 @ Wp) @ D1.T))
        Wd = ajusta_adaptador(D1[idx], D2[idx], lam=0.1)
        vals["índice v1 → espacio v2 (ridge)"].append(nd(Q2 @ l2n(D1 @ Wd).T))
    for k in curvas:
        curvas[k].append(np.mean(vals[k]))
fig, ax = plt.subplots(figsize=(8, 4.5))
for (k, v), c in zip(curvas.items(), [AZUL, VERDE, NARANJA]):
    ax.plot(np.array(fracs) * 100, v, "o-", color=c, label=k)
ax.axhline(base["v1 nativo"], color=GRIS, ls="--", label="v1 nativo"); ax.axhline(base["v2 re-embedding completo"], color="k", ls="--", label="v2 re-embedding completo")
ax.set_xscale("log"); ax.set_xlabel("% del corpus embebido con ambas versiones (pares para ajustar W)"); ax.set_ylabel("nDCG@10")
ax.set_title("Migración v1 → v2: adaptadores lineales vs re-embedding"); ax.legend(fontsize=8); plt.tight_layout(); plt.show()
pd.DataFrame(curvas, index=[f"{int(f*100)} %" for f in fracs]).round(3)
''')
    nb.md(r'''> 👀 **Qué debes observar:** (1) con muy pocos pares el adaptador ridge es **peor que quedarse en v1**: un adaptador mal ajustado es una regresión, no un puente; Procrustes (menos parámetros, conserva ángulos) degrada de forma distinta con pocos pares; (2) con suficientes pares el adaptador **recupera y puede superar levemente a v1**, pero (3) **ninguna ruta alcanza al re-embedding completo**: lo que v2 sabe y v1 no codificó no se recupera con una matriz. Además, ajustamos $W$ con embeddings de *documentos* y lo aplicamos a *queries*: con modelos con prefijos `query:`/`passage:` esa diferencia de distribución pesa más.

Comprobamos la decisión con el test pareado del módulo 15:''')
    nb.code(r'''
idx = rng.choice(len(doc_texts), len(doc_texts) // 2, replace=False)
W50 = ajusta_adaptador(D2[idx], D1[idx], lam=0.1)
pq_v1 = ndcg_por_query(run_desde_scores(Q1 @ D1.T)); pq_v2 = ndcg_por_query(run_desde_scores(Q2 @ D2.T))
pq_ad = ndcg_por_query(run_desde_scores(l2n(Q2 @ W50) @ D1.T))
for nombre, a, b in (("v2 completo − v1", pq_v2, pq_v1), ("adaptador 50 % − v1", pq_ad, pq_v1), ("v2 completo − adaptador 50 %", pq_v2, pq_ad)):
    r = paired_bootstrap(a, b)
    print(f"{nombre:30s} Δ={r['diff']:+.3f}  IC95=[{r['ci_low']:+.3f}, {r['ci_high']:+.3f}]  p={r['p_value']:.3f}")
coste_reembed = {k: coste_api(T_PROD, p) for k, p in PRECIOS_API.items()}
print(f"\nCosto de re-embeber 10 M chunks: API {min(coste_reembed.values()):.0f}–{max(coste_reembed.values()):.0f} $ · GPU propia ≈ {coste_gpu(T_PROD):.0f} $ ({horas_gpu(T_PROD):.0f} h, supuestos de §1)")
''')
    nb.md(r'''> 👀 **Qué debes observar:** si el IC de «v2 completo − adaptador» excluye el 0, el adaptador **deja calidad sobre la mesa** y solo se justifica como puente temporal. Compara esa pérdida con el coste del re-embedding (decenas–cientos de $ con estos supuestos): en la mayoría de casos **re-embeber es barato; lo caro es operar dos índices y validar**. El adaptador gana cuando el texto original ya no está disponible (solo guardaste vectores) o cuando el corpus es enorme y necesitas servir v2 *ya*.''')

    # ───────────────────────────── §7 Cuantización ─────────────────────────────
    nb.md(r'''## 6. Cuantización en producción: qué vive en RAM y qué en disco
El patrón de producción (módulo 12) es: **índice comprimido en RAM para generar candidatos + vectores de mayor precisión (en disco o memoria barata) para reordenar** los top-$K$. Aquí lo montamos sobre v2 y medimos calidad y memoria proyectada a 10 M de vectores.''')
    nb.code(r'''
def int8_calibra(Dcal, q=0.001):
    lo, hi = np.quantile(Dcal, q, axis=0), np.quantile(Dcal, 1 - q, axis=0)
    return lo, np.maximum(hi - lo, 1e-9) / 255.0

def int8_codifica(D, lo, esc):
    return np.clip(np.round((D - lo) / esc) - 128, -128, 127).astype(np.int8)

def int8_decodifica(Z, lo, esc):
    return (Z.astype(np.float32) + 128) * esc + lo

def busca_binaria(Q, D, rescore_con=None, K=40):
    """Hamming sobre signos (±1); con rescore_con=matriz float, reordena los K mejores con producto punto exacto."""
    Qb, Db = np.where(Q > 0, 1.0, -1.0), np.where(D > 0, 1.0, -1.0)
    S = Qb @ Db.T
    if rescore_con is None:
        return S
    out = np.full_like(S, -np.inf)
    top = np.argpartition(-S, K, axis=1)[:, :K]
    for i, cand in enumerate(top):
        out[i, cand] = Q[i] @ rescore_con[cand].T
    return out

d2 = D2.shape[1]
lo, esc = int8_calibra(D2)
D2_i8 = int8_decodifica(int8_codifica(D2, lo, esc), lo, esc)
filas = [
    {"precisión": "float32", "bytes/vector": 4 * d2, "nDCG@10": nd(Q2 @ D2.T)},
    {"precisión": "int8 (calibrado por dimensión)", "bytes/vector": d2, "nDCG@10": nd(Q2 @ D2_i8.T)},
    {"precisión": "binaria (1 bit/dim)", "bytes/vector": d2 / 8, "nDCG@10": nd(busca_binaria(Q2, D2))},
    {"precisión": "binaria + rescore float32 top-40", "bytes/vector": d2 / 8, "nDCG@10": nd(busca_binaria(Q2, D2, rescore_con=D2))},
]
df_q = pd.DataFrame(filas); df_q["GB en RAM (10 M vectores)"] = df_q["bytes/vector"] * 1e7 / 1e9
fig, ax = plt.subplots(figsize=(7.5, 4))
for (_, r), c in zip(df_q.iterrows(), [GRIS, AZUL, NARANJA, VERDE]):
    ax.scatter(r["GB en RAM (10 M vectores)"], r["nDCG@10"], s=90, color=c, label=r["precisión"])
ax.set_xscale("log"); ax.set_xlabel(f"GB en RAM para 10 M vectores de {d2} d (log)"); ax.set_ylabel("nDCG@10")
ax.set_title("Cuantización: memoria vs calidad (v2)"); ax.legend(fontsize=8); plt.tight_layout(); plt.show()
df_q.round(3)
''')
    nb.md(r'''> 👀 **Qué debes observar:** int8 casi no pierde calidad con 4× menos memoria; la binaria pura cae más (y con un embedder de solo 128 d, mucho más que con uno de 768–1024 d entrenado para ello); **binaria + rescore** recupera casi todo con 32× menos RAM, a cambio de leer $K$ vectores float por query (de SSD en producción). Con el fallback TF-IDF+SVD de 128 d la pérdida binaria es mayor que la que verías con modelos neuronales de alta dimensión: **mide con tu modelo**.''')

    # ───────────────────────────── §8 Vector DB ─────────────────────────────
    nb.md(r'''## 7. Vector DB ligera: Qdrant en modo local, filtros y versiones
Qdrant tiene un **modo local** en el propio cliente Python (`QdrantClient(":memory:")` o `path=...`): misma API que el servidor, sin desplegar nada. Usaremos tres funciones que importan en producción:
1. **Named vectors**: un mismo punto guarda `v1` y `v2` (dimensiones distintas) → la migración no duplica payloads.
2. **Filtros por payload** (`lang`, tenant, permisos) aplicados **durante** la búsqueda (no después: el post-filtro devuelve menos de $k$ resultados cuando el filtro es selectivo, módulo 14).
3. Verificación contra fuerza bruta: nunca confíes en un índice que no has comparado con el exacto.

Si `qdrant-client` no está disponible, la celda cae a **FAISS** con `IDSelectorBatch` (filtro dentro de la búsqueda). Equivalente en **pgvector** (no ejecutado aquí):
```sql
CREATE EXTENSION vector;
CREATE TABLE chunks (id text PRIMARY KEY, lang text, emb_v2 vector(768));
CREATE INDEX ON chunks USING hnsw (emb_v2 vector_cosine_ops);
SELECT id FROM chunks WHERE lang = 'es' ORDER BY emb_v2 <=> $1 LIMIT 10;   -- <=> = distancia coseno
```''')
    nb.code(r'''
try:
    from qdrant_client import QdrantClient, models
    QDRANT_OK = True
except ImportError:
    QDRANT_OK = False
    print("⚠️ qdrant-client no instalado: uso FAISS como respaldo.")

if QDRANT_OK:
    qc = QdrantClient(":memory:")                     # modo local embebido (sin servidor)
    qc.create_collection("poliglota", vectors_config={v: models.VectorParams(size=EMB[v]["D"].shape[1], distance=models.Distance.COSINE) for v in EMB})
    qc.upsert("poliglota", points=[models.PointStruct(id=i, vector={v: EMB[v]["D"][i].tolist() for v in EMB},
                                                      payload={"doc_id": doc_ids[i], "lang": str(doc_lang[i])}) for i in range(len(docs))])
    def busca_vdb(qvec, version, lang=None, k=10):
        filtro = models.Filter(must=[models.FieldCondition(key="lang", match=models.MatchValue(value=lang))]) if lang else None
        r = qc.query_points("poliglota", query=qvec.tolist(), using=version, limit=k, query_filter=filtro)
        return [p.id for p in r.points]
else:
    import faiss
    _idx = {v: faiss.IndexFlatIP(EMB[v]["D"].shape[1]) for v in EMB}
    for v in EMB: _idx[v].add(l2n(EMB[v]["D"]))
    def busca_vdb(qvec, version, lang=None, k=10):
        p = faiss.SearchParameters(sel=faiss.IDSelectorBatch(np.flatnonzero(doc_lang == lang).astype("int64"))) if lang else None
        return [int(i) for i in _idx[version].search(qvec[None].astype("float32"), k, params=p)[1][0] if i >= 0]

# Verificación contra fuerza bruta filtrada (numpy)
coinc = []
for i, q in enumerate(EMB["v2"]["Q"][:40]):
    lang = str(q_lang[i]); m = np.flatnonzero(doc_lang == lang)
    exacto = m[np.argsort(-(EMB["v2"]["D"][m] @ q))[:10]]
    coinc.append(len(set(exacto) & set(busca_vdb(q, "v2", lang))) / 10)
print(f"{'Qdrant local' if QDRANT_OK else 'FAISS'} vs fuerza bruta (top-10 con filtro): coincidencia media = {np.mean(coinc):.3f}")
''')
    nb.md("### Híbrido + filtro por idioma: ¿cuánto aporta el filtro?\nCuando el usuario elige idioma (o el sistema lo detecta), el filtro elimina distractores de otros idiomas. Medimos nDCG@10 por idioma con y sin filtro, para denso (v2), BM25 y la fusión RRF (módulo 13).")
    nb.code(r'''
def rrf_mat(*Ss, k=60):
    out = np.zeros_like(Ss[0])
    for S in Ss:
        rk = np.argsort(np.argsort(-S, axis=1, kind="stable"), axis=1, kind="stable")   # rango 0..n-1 por fila
        out += 1.0 / (k + rk + 1)
    return out

def con_filtro(S):
    """Pone -inf a los documentos de otro idioma que la query (filtro aplicado antes del ranking)."""
    return np.where(doc_lang[None, :] == q_lang[:, None], S, -np.inf)

S_dense = Q2 @ D2.T
sistemas = {"denso v2": S_dense, "BM25": S_BM25, "RRF(denso, BM25)": rrf_mat(S_dense, S_BM25)}
filas = []
for nombre, S in sistemas.items():
    for filtro in (False, True):
        pq = ndcg_por_query(run_desde_scores(con_filtro(S) if filtro else S))
        fila = {"sistema": nombre, "filtro idioma": filtro, "global": pq.mean()}
        fila.update({l: pq[q_lang == l].mean() for l in ("es", "en", "code")}); filas.append(fila)
df_f = pd.DataFrame(filas)
fig, ax = plt.subplots(figsize=(9, 4))
x = np.arange(3); w = 0.13
for j, (_, r) in enumerate(df_f.iterrows()):
    ax.bar(x + (j - 2.5) * w, [r["es"], r["en"], r["code"]], w, color=[AZUL, AZUL, NARANJA, NARANJA, VERDE, VERDE][j],
           alpha=1.0 if r["filtro idioma"] else 0.45, label=f"{r['sistema']}{' + filtro' if r['filtro idioma'] else ''}")
ax.set_xticks(x); ax.set_xticklabels(["es", "en", "code"]); ax.set_ylabel("nDCG@10"); ax.set_ylim(0, 1.05)
ax.set_title("nDCG@10 por idioma: con y sin filtro de idioma"); ax.legend(fontsize=7, ncol=3); plt.tight_layout(); plt.show()
df_f.round(3)
''')
    nb.md(r'''> 👀 **Qué debes observar:** el filtro ayuda donde los distractores de otro idioma compiten (la barra opaca frente a la translúcida de cada color) y no cambia nada donde el sistema ya no los confundía. Pero **un filtro mal elegido es un techo**: si una query en español busca una respuesta que solo existe en inglés (el caso típico de documentación técnica), filtrar por `lang=es` la vuelve imposible. En Políglota el filtro de idioma debe ser una **preferencia** (boost) o una opción del usuario, no una regla dura; los filtros duros son para **permisos y tenants**.''')

    # ───────────────────────────── §9 Privacidad ─────────────────────────────
    nb.md(r'''## 8. Privacidad: un embedding filtra el texto (puente con el módulo 17)
Morris et al. (2023, vec2text) reconstruyeron gran parte de textos cortos a partir de su embedding; Song & Raghunathan (2020) mostraron ataques de inversión y de inferencia de atributos sobre embeddings de frases. Consecuencias operativas:
* Los vectores heredan la **clasificación del texto** (PII, secretos, datos de cliente): cifrado en reposo, control de acceso, retención y borrado (el «derecho al olvido» también aplica a los vectores y a las cachés).
* **Aislamiento por tenant** (colecciones separadas o filtro obligatorio en el servidor, nunca solo en el cliente).
* Si envías texto a una API externa, el **texto** sale de tu perímetro (residencia de datos), no solo el vector.

🧪 Ataque mínimo medible: un **decodificador lineal** que, a partir del vector, predice qué palabras del vocabulario contiene el documento. El atacante tiene acceso al embedder (puede generar sus propios pares texto→vector) y obtiene vectores filtrados. Defensa evaluada: **ruido gaussiano** en los vectores almacenados. Medimos ataque (precisión@10 de palabras recuperadas) vs utilidad (nDCG@10).''')
    nb.gemini(
        "imagen", "M18-IMG-03", "Modelo de amenazas de un índice de embeddings",
        "Dónde se filtra información en un servicio de embeddings (API externa, vectores en reposo, cachés, logs, multi-tenant) y qué control mitiga cada punto.",
        """Diagrama técnico limpio, fondo blanco, paleta: azul #1F6FEB (flujo de datos), naranja #F28E2B (puntos de riesgo), verde #2CA02C (controles), gris #6B7280 (componentes). Sans-serif legible, flechas claras.
Flujo de izquierda a derecha con cajas grises: "Texto del cliente" → "API de embeddings (externa o propia)" → "Vector DB" → "Caché de queries" → "Logs".
Sobre cada caja, un triángulo naranja numerado con el riesgo:
1 sobre la API: "el texto sale del perímetro";
2 sobre Vector DB: "inversión del vector (vec2text)";
3 sobre la caché: "vectores sin borrar tras una solicitud de olvido";
4 sobre Logs: "queries con PII en texto plano";
5 entre dos cilindros "Tenant A" y "Tenant B" dentro de la Vector DB: "fuga entre tenants".
Debajo de cada riesgo, una etiqueta verde con el control: 1 "modelo propio o acuerdo de residencia"; 2 "cifrado + control de acceso; ruido (con coste de calidad)"; 3 "borrado por doc_id en índice y caché"; 4 "redacción de PII en logs"; 5 "colecciones separadas o filtro obligatorio en el servidor".
Título arriba: "Un embedding es un dato sensible".
Evita: candados o calaveras decorativas, logotipos, texto ilegible, flechas cruzadas.""",
        "Flujo texto → API → vector DB → caché → logs con cinco riesgos de privacidad numerados y el control que mitiga cada uno.",
        """
Texto → [API]① → [Vector DB ②  (Tenant A | Tenant B ⑤)] → [Caché ③] → [Logs ④]
① texto sale del perímetro → modelo propio / residencia
② inversión → cifrado, acceso, ruido      ③ olvido → borrar en índice y caché
④ PII en logs → redacción                 ⑤ multi-tenant → filtro obligatorio en servidor
""")
    nb.md("> 👀 **Qué debes observar:** la mayoría de los controles son de **ingeniería clásica** (acceso, cifrado, borrado, aislamiento); solo el punto 2 tiene una defensa «de ML» (ruido), y la medimos a continuación.")
    nb.code(r'''
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import Ridge

cv = CountVectorizer(binary=True, min_df=0.02, max_df=0.3, max_features=400, token_pattern=r"(?u)\b[^\W\d_]{4,}\b")  # sin palabras de plantilla
Y = cv.fit_transform(doc_texts).toarray().astype(np.float32)
perm = np.random.default_rng(SEED).permutation(len(docs)); tr, te = perm[: len(docs) // 2], perm[len(docs) // 2:]

def precision_ataque(Dfuga, k=10):
    """El atacante entrena con pares limpios (tiene el embedder) y ataca vectores filtrados Dfuga."""
    att = Ridge(alpha=1.0).fit(D2[tr], Y[tr])
    P = att.predict(Dfuga[te])
    top = np.argsort(-P, axis=1)[:, :k]
    return float(np.mean([Y[te][i, top[i]].mean() for i in range(len(te))]))

base_frec = float(np.mean(Y[te][:, np.argsort(-Y[tr].mean(0))[:10]].mean(1)))   # adivinar las 10 palabras más frecuentes
sigmas = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0]
rng = np.random.default_rng(SEED); fil = []
for s in sigmas:
    Dn = l2n(D2 + s * rng.normal(size=D2.shape) / np.sqrt(D2.shape[1]))     # ruido de norma ≈ s
    fil.append({"sigma": s, "ataque_p@10": precision_ataque(Dn), "nDCG@10": nd(Q2 @ Dn.T)})
df_p = pd.DataFrame(fil)
fig, ax = plt.subplots(figsize=(7.5, 4.2))
ax.plot(df_p["nDCG@10"], df_p["ataque_p@10"], "o-", color=NARANJA)
for _, r in df_p.iterrows():
    ax.annotate(f"σ={r.sigma}", (r["nDCG@10"], r["ataque_p@10"]), textcoords="offset points", xytext=(5, 5), fontsize=8)
ax.axhline(base_frec, color=GRIS, ls="--", label="atacante sin vector (palabras más frecuentes)")
ax.set_xlabel("utilidad: nDCG@10 del retrieval"); ax.set_ylabel("ataque: precisión@10 de palabras recuperadas")
ax.set_title("Privacidad vs utilidad: ruido gaussiano en los vectores almacenados"); ax.legend(fontsize=8); plt.tight_layout(); plt.show()
df_p.round(3)
''')
    nb.md(r'''> 👀 **Qué debes observar:** sin ruido, un simple decodificador lineal recupera muchas más palabras reales que el atacante sin vector (línea gris): **el vector filtra contenido**. El ruido baja el ataque, pero **baja la utilidad casi al mismo ritmo**: para acercar el ataque a la línea base hay que destruir buena parte del nDCG. Con el fallback (TF-IDF de n-gramas: un vector casi léxico) el ataque es especialmente fácil y robusto al ruido. Con embedders neuronales la curva puede ser muy distinta: Morris et al. (2023) reportan que un ruido gaussiano pequeño degrada mucho su ataque iterativo con poca pérdida de retrieval; pero un atacante puede reentrenar con vectores ruidosos. **Mide con tu modelo y con el ataque más fuerte que tengas.** Conclusión práctica (coherente con el módulo 17): el ruido no es una defensa gratuita; la defensa principal es **no dejar que los vectores salgan** (acceso, cifrado, aislamiento). Ataques más fuertes (vec2text, no lineales) recuperan más que este decodificador lineal: esta curva es una **cota inferior** del riesgo.''')

    # ───────────────────────────── §10 Drift ─────────────────────────────
    nb.md(r'''## 9. Monitorización de drift sin etiquetas
En producción casi nunca tienes qrels del tráfico real. Señales **sin etiquetas** que sí puedes calcular por día:
* **Confianza del retrieval**: similitud del top-1 (máximo coseno con el índice). Si baja, las queries caen fuera de lo que el índice cubre.
* **Fracción de queries «huérfanas»**: top-1 por debajo del percentil 5 de referencia.
* **PSI** (*Population Stability Index*) de la distribución del top-1 frente a una ventana de referencia: $\mathrm{PSI} = \sum_b (a_b - e_b)\ln\frac{a_b}{e_b}$, con $e_b$, $a_b$ las fracciones de referencia y actuales en el *bin* $b$ (bins por cuantiles de la referencia). Umbrales habituales (regla práctica, no ley): < 0.1 estable, 0.1–0.25 vigilar, > 0.25 actuar.

✍️ **Ejemplo a mano con 2 bins.** Referencia: mitad de las queries con top-1 por encima de la mediana, mitad por debajo, $e = (0.5, 0.5)$. Hoy: $a = (0.2, 0.8)$ (muchas queries con confianza baja). $\mathrm{PSI} = (0.2-0.5)\ln\frac{0.2}{0.5} + (0.8-0.5)\ln\frac{0.8}{0.5} = (-0.3)(-0.916) + (0.3)(0.470) = 0.275 + 0.141 = 0.42$ → **actuar**. Cada término es $\ge 0$ (diferencia y logaritmo tienen el mismo signo): el PSI es una divergencia de KL simetrizada, $\mathrm{KL}(a\Vert e) + \mathrm{KL}(e\Vert a)$, la misma familia que la entropía cruzada del módulo 06. Viene del *credit scoring* (estabilidad de la población que puntúa un modelo de riesgo): lo usamos igual, solo cambia la variable vigilada.

🧪 Simulamos 30 días: desde el día 15 crece la proporción de queries de un **tema nuevo** que la documentación aún no cubre.''')
    nb.code(r'''
TEMA_NUEVO = ["kubernetes", "helm", "pod", "ingress", "autoscaling", "namespace", "configmap", "daemonset", "kubectl", "rollout"]
def queries_tema_nuevo(n, rng):
    return [" ".join(rng.choice(TEMA_NUEVO, size=3, replace=False)) + rng.choice([" error", " cómo configurar", " best practice", ""]) for _ in range(n)]

def psi(ref, act, bins=10, eps=1e-4):
    cortes = np.quantile(ref, np.linspace(0, 1, bins + 1)); cortes[0], cortes[-1] = -np.inf, np.inf
    e = np.histogram(ref, cortes)[0] / len(ref) + eps; a = np.histogram(act, cortes)[0] / len(act) + eps
    return float(np.sum((a - e) * np.log(a / e)))

rng = np.random.default_rng(SEED); dias, top1 = 30, []
for d in range(dias):
    p_nuevo = 0.0 if d < 15 else min(0.6, 0.04 * (d - 14))
    n_new = rng.binomial(80, p_nuevo)
    txt = list(rng.choice(q_texts, 80 - n_new)) + queries_tema_nuevo(n_new, rng)
    top1.append((VERS["v2"].encode_queries(txt) @ D2.T).max(axis=1))
ref = np.concatenate(top1[:7]); umbral = np.quantile(ref, 0.05)
serie = pd.DataFrame({"día": range(dias), "top1_medio": [t.mean() for t in top1], "huérfanas": [np.mean(t < umbral) for t in top1],
                      "PSI": [psi(ref, t) for t in top1]})
fig, axs = plt.subplots(1, 2, figsize=(11, 3.8))
axs[0].plot(serie["día"], serie["top1_medio"], "o-", color=AZUL); axs[0].axvline(15, color=GRIS, ls=":")
axs[0].set_xlabel("día"); axs[0].set_ylabel("similitud top-1 media"); axs[0].set_title("Confianza del retrieval")
axs[1].plot(serie["día"], serie["PSI"], "o-", color=NARANJA, label="PSI del top-1"); axs[1].plot(serie["día"], serie["huérfanas"], "s-", color=VERDE, label="fracción de huérfanas")
axs[1].axhline(0.25, color=ROJO, ls="--", label="umbral PSI = 0.25"); axs[1].axvline(15, color=GRIS, ls=":")
axs[1].set_xlabel("día"); axs[1].set_title("Alarmas de drift sin etiquetas"); axs[1].legend(fontsize=8)
plt.tight_layout(); plt.show()
print("primer día con PSI > 0.25:", int(serie.loc[serie.PSI > 0.25, "día"].min()) if (serie.PSI > 0.25).any() else "ninguno")
''')
    nb.md(r'''> 👀 **Qué debes observar:** antes del día 15 el PSI se queda en ruido (los días 0–6 son la propia referencia); al entrar el tema nuevo, la similitud top-1 baja y el PSI cruza el umbral **antes** de que nadie se queje. La alarma no te dice *qué* falla: la acción es **muestrear las queries huérfanas**, etiquetarlas y decidir (¿falta contenido? ¿falta vocabulario en el tokenizer? ¿hay que reentrenar?). Ojo: el PSI depende del número de bins y del tamaño de la muestra diaria: calibra el umbral con días tranquilos.''')

    # ───────────────────────────── §11 A/B e interleaving ─────────────────────────────
    nb.md(r'''## 10. Evaluación online: A/B vs interleaving
El golden set dice si v2 es mejor **en tus queries juzgadas**; solo el tráfico real dice si es mejor **para tus usuarios** (gap offline/online, módulo 19).
* **A/B**: la mitad de los usuarios ve A y la otra mitad B; comparas una métrica de sesión (p. ej. éxito = al menos un clic). Varianza alta: cada usuario solo ve un sistema.
* **Interleaving (team-draft)**: cada usuario ve **una lista mezclada** de A y B (como elegir equipos: por turnos aleatorios cada sistema aporta su mejor documento aún no elegido); los clics se acreditan al «equipo» que aportó el documento. Es una comparación **pareada dentro de la misma impresión** → mucha más potencia (Chapelle et al. 2012 lo validaron a gran escala en buscadores web).

✍️ **Ejemplo a mano (team-draft).** A = [a, b, c], B = [b, d, a]. Ronda 1, la moneda dice «A primero»: A aporta `a`, B aporta su mejor aún no elegido, `b`. Ronda 2, «B primero»: B aporta `d`, A aporta `c`. Lista mostrada: [a, b, d, c] con equipos A = {a, c}, B = {b, d}. El usuario hace clic en `b` y `d` → B gana esta impresión 2–0. Como en un test pareado del módulo 15, cada impresión es su propio control (mismo usuario, misma query, mismo momento): por eso se necesita mucho menos tráfico que en un A/B.

🧪 Simulamos usuarios con un modelo de clic con **sesgo de posición** (examinan la posición $r$ con probabilidad decreciente; clic en relevante 0.8, en no relevante 0.05) usando los qrels como verdad, con A = v1 y B = v2. Medimos la **potencia** (fracción de 100 experimentos que detectan B > A con p < 0.05) frente al número de impresiones.''')
    nb.code(r'''
from scipy import stats
P_EXAM = np.array([0.95, 0.7, 0.5, 0.35, 0.25, 0.18, 0.13, 0.1, 0.08, 0.06])
rels_de = lambda run: np.array([[1.0 if qrels[q].get(d, 0) > 0 else 0.0 for d in run[q][:10]] for q in qids])
runA, runB = run_desde_scores(Q1 @ D1.T), run_desde_scores(Q2 @ D2.T)
RA, RB = rels_de(runA), rels_de(runB)

def team_draft(a, b, rng, k=10):
    """Team-draft interleaving: devuelve (lista mezclada, equipo de cada posición: 0=A, 1=B)."""
    out, eq, ia, ib = [], [], 0, 0
    while len(out) < k:
        turno_a = (sum(e == 0 for e in eq) < sum(e == 1 for e in eq)) or (sum(e == 0 for e in eq) == sum(e == 1 for e in eq) and rng.random() < 0.5)
        lista, j = (a, ia) if turno_a else (b, ib)
        while j < len(lista) and lista[j] in out: j += 1
        if j >= len(lista): break
        out.append(lista[j]); eq.append(0 if turno_a else 1)
        if turno_a: ia = j + 1
        else: ib = j + 1
    return out, np.array(eq)

rng = np.random.default_rng(SEED); VAR = 8                     # 8 mezclas aleatorias precalculadas por query
TD = [[team_draft(runA[q], runB[q], rng) for _ in range(VAR)] for q in qids]
TD_rel = np.array([[[1.0 if qrels[q].get(d, 0) > 0 else 0.0 for d in l] for l, _ in TD[i]] for i, q in enumerate(qids)])
TD_eq = np.array([[e for _, e in TD[i]] for i in range(len(qids))])

def clics(R, rng):
    ex = rng.random(R.shape) < P_EXAM[: R.shape[-1]]
    return ex & (rng.random(R.shape) < np.where(R > 0, 0.8, 0.05))

def potencia(n, sims=100, seed=SEED):
    rng = np.random.default_rng(seed); ab = il = 0
    for _ in range(sims):
        qa, qb = rng.integers(0, len(qids), n // 2), rng.integers(0, len(qids), n // 2)
        sa, sb = clics(RA[qa], rng).any(1), clics(RB[qb], rng).any(1)
        ab += (stats.ttest_ind(sb, sa).pvalue < 0.05) and sb.mean() > sa.mean()
        qi, v = rng.integers(0, len(qids), n), rng.integers(0, VAR, n)
        c = clics(TD_rel[qi, v], rng); eq = TD_eq[qi, v]
        gb, ga = (c & (eq == 1)).sum(1), (c & (eq == 0)).sum(1)
        wins_b, wins_a = int((gb > ga).sum()), int((ga > gb).sum())
        if wins_a + wins_b:
            il += (stats.binomtest(wins_b, wins_a + wins_b).pvalue < 0.05) and wins_b > wins_a
    return ab / sims, il / sims

ns = [50, 100, 200, 400, 800, 1600]
pot = np.array([potencia(n) for n in ns])
fig, ax = plt.subplots(figsize=(7.5, 4))
ax.plot(ns, pot[:, 0], "o-", color=NARANJA, label="A/B (éxito de sesión, t-test)"); ax.plot(ns, pot[:, 1], "o-", color=AZUL, label="team-draft interleaving (test binomial)")
ax.axhline(0.8, color=GRIS, ls="--", label="potencia 0.8"); ax.set_xscale("log")
ax.set_xlabel("impresiones totales"); ax.set_ylabel("potencia (detectar v2 > v1)"); ax.set_title("Potencia estadística: A/B vs interleaving (simulación)")
ax.legend(fontsize=8); plt.tight_layout(); plt.show()
print(f"nDCG@10 offline: v1={nd(Q1 @ D1.T):.3f} · v2={nd(Q2 @ D2.T):.3f}")
''')
    nb.md(r'''> 👀 **Qué debes observar:** para la misma diferencia de calidad, interleaving alcanza potencia 0.8 con **varias veces menos impresiones** que el A/B: cada impresión compara A y B para el mismo usuario y la misma query. A cambio, interleaving mide **preferencia relativa**, no el efecto en métricas de negocio (retención, conversión): el flujo habitual es *interleaving para cribar candidatos → A/B para confirmar el impacto* del ganador. En RAG, donde el «usuario» del retrieval es un LLM, los clics se sustituyen por señales del generador o por jueces, con sus sesgos (módulo 15).''')

    # ───────────────────────────── Cierre ─────────────────────────────
    nb.md(r'''## 🗺️ Mapa de madurez (a oct-2026)
Ya has medido cada pieza (costes, colas, caché, migración, cuantización, filtros, privacidad, drift, interleaving); ahora sitúalas: ¿cuáles son práctica estándar y cuáles todavía puentes o riesgos abiertos?

🟢 sólido · 🟡 emergente · 🔴 experimental.

| Técnica | Madurez | Quién la usa (respaldado) | Fuente |
|---|---|---|---|
| APIs de embeddings de pago por token | 🟢 | OpenAI (`text-embedding-3-*`), Google (`gemini-embedding-001`), Cohere, Voyage | páginas de modelo/precios de cada proveedor (oct-2026) |
| Servidores dedicados de embeddings (TEI) | 🟢 | Hugging Face Text Embeddings Inference (imágenes `cpu-*`/`cuda-*`) | repo `huggingface/text-embeddings-inference` |
| vLLM como servidor de *pooling*/embeddings | 🟡 | `--runner pooling`, endpoint compatible con OpenAI | docs de vLLM («Pooling Models») |
| Micro-batching dinámico | 🟢 | TEI, Triton, vLLM | docs de cada servidor |
| Hedged requests contra la cola | 🟢 | descrito para servicios de Google | Dean & Barroso 2013 |
| Caché de embeddings por contenido + versión | 🟢 | práctica estándar | — |
| Re-embedding completo con doble índice (blue/green) | 🟢 | práctica estándar en migraciones | docs de vector DBs (aliases de colecciones en Qdrant) |
| Adaptadores lineales entre versiones | 🟡 | puente temporal; base teórica en compatibilidad hacia atrás | Shen et al. 2020 (BCT) |
| Vector DB ligera (Qdrant local / pgvector) | 🟢 | Qdrant, pgvector (HNSW e IVFFlat) | docs oficiales |
| Cuantización binaria + rescoring en servicio | 🟢/🟡 | sentence-transformers, varias vector DBs | Shakir et al. 2024 (blog HF) |
| Inversión de embeddings como riesgo | 🟡 (riesgo real, defensas inmaduras) | — | Song & Raghunathan 2020; Morris et al. 2023 |
| Interleaving para evaluación online | 🟢 en buscadores web; 🟡 en RAG | Bing/Yahoo (estudios publicados) | Chapelle et al. 2012 |
''')
    nb.md(r'''## 🏭 En producción
* **Precios publicados (oct-2026, tarifa estándar por 1M tokens de entrada):** OpenAI `text-embedding-3-small` 0.02 $ y `text-embedding-3-large` 0.13 $ (página del modelo en la documentación de OpenAI); Google `gemini-embedding-001` 0.15 $ (anunciado al pasar a disponibilidad general en julio de 2025). Verifica siempre la página oficial: los precios y los descuentos por lote cambian.
* **Matryoshka como palanca de coste:** las APIs de OpenAI (`dimensions`) y Gemini (`output_dimensionality`) permiten pedir menos dimensiones: la memoria del índice escala lineal con $d$ (módulo 12).
* **TEI** (Hugging Face) es el servidor de referencia para encoders: micro-batching por tokens (`--max-batch-tokens`), imágenes por arquitectura y métricas Prometheus. **vLLM** cubre modelos de *pooling* y LLM-as-embedder con `--runner pooling`.
* **Vector DBs:** Qdrant (named vectors, filtros por payload, aliases de colección para cambios atómicos), pgvector (HNSW e IVFFlat dentro de Postgres: ideal si ya tienes Postgres y < decenas de millones de vectores), FAISS como librería (módulo 14).
* **Migraciones:** el patrón robusto es colección nueva + backfill + evaluación en sombra + cambio de alias; los adaptadores son puentes. La literatura de **compatibilidad hacia atrás** (Shen et al. 2020, BCT) nació en visión (reconocimiento facial) precisamente porque re-embeber galerías enormes era inviable.
* **Evaluación online:** interleaving (Chapelle et al. 2012; Radlinski et al. 2008) y A/B con la metodología de Kohavi et al. (2020).
''')
    nb.md(r'''## 🧠 Secretos de la élite
1. **La versión del vector es un contrato, no un número**: incluye modelo + revisión del checkpoint + servidor (TEI 1.9 cambió valores por defecto: GeLU con aproximación tanh y `--auto-truncate` activado, según sus notas de versión) + preprocesado (normalización Unicode, truncado, prefijo). Guárdala en el payload de cada punto y en la clave de caché; un cambio en cualquiera es una migración. Y no esperes reproducibilidad **bit a bit** fuera de ese contrato: la aritmética en coma flotante no es asociativa y muchos kernels de GPU cambian el orden de reducción según el tamaño de lote, que en un servidor depende de la carga; He (Thinking Machines Lab, 2025) lo identifica como la causa principal de la no-determinación de los endpoints de inferencia de LLMs, y el mismo mecanismo afecta a un encoder servido con micro-batching. Consecuencias: compara vectores con tolerancia (coseno ≥ 0.9999 en tests de CI, no `==`), no uses el hash del vector como identidad ni para deduplicar, y usa el texto normalizado + versión como clave (§4). (Con el `MiniEncoder` de §2 en CPU y un hilo, el mismo texto solo o dentro de un lote de 32 con padding sale idéntico bit a bit, en float32 y en bf16: el problema aparece con kernels que eligen estrategia según el lote.)
2. **Mide $\theta$ (tokens/s) con tus longitudes reales**: los benchmarks de throughput con textos de longitud fija sobreestiman el rendimiento con documentación real (longitudes de cola larga → padding).
3. **El p99 se diseña, no se optimiza al final**: evita el *fan-out* si el índice cabe en una réplica, usa hedged requests si no, y fija `max_wait` del micro-batching con tráfico realista (§3).
4. **Re-embeber suele ser barato; lo caro es la incertidumbre**: presupuesta el doble índice, la evaluación pareada y el interleaving, no solo los tokens.
5. **Un adaptador lineal mal ajustado es una regresión silenciosa**: con pocos pares puede quedar por debajo de v1 (§5). Ponle una puerta de calidad (test pareado contra v1) antes de servirlo.
6. **Los filtros duros son para permisos; la preferencia de idioma es un boost**: un filtro de idioma duro convierte en imposible la query ES cuya respuesta solo existe en EN.
7. **Monitoriza el top-1 sin etiquetas y muestrea las huérfanas**: es la forma más barata de descubrir qué falta en el índice (y alimentar el golden set del módulo 15).
8. **El borrado es parte del diseño**: un `DELETE` por `doc_id` debe propagarse a índice, réplicas, cachés y backups de vectores; con HNSW los borrados se marcan y degradan el grafo hasta compactar (módulo 14).
''')
    nb.md(r'''## ⚠️ Errores comunes
* Calcular el coste solo con el precio por token y olvidar el **doble índice** durante la migración, las re-indexaciones por cambios de chunking y el tráfico de evaluación.
* Medir latencia con un bucle secuencial en local y extrapolar a producción (sin red, sin cola, sin concurrencia).
* Caché **sin versión** en la clave, o sin normalizar el texto (hit rate artificialmente bajo).
* Mezclar en el mismo índice vectores de dos versiones «porque tienen la misma dimensión».
* Post-filtrar resultados de un ANN con filtros selectivos (devuelve < k resultados) en lugar de filtrar dentro de la búsqueda.
* Tratar los embeddings como anónimos y guardarlos sin control de acceso, o enviar texto con PII a una API externa sin revisar residencia de datos.
* Declarar ganador a v2 por nDCG offline sin test pareado ni validación online.
''')
    nb.md(r'''## 📝 Autoevaluación
<details><summary><b>1 · (Cálculo)</b> 50 M de chunks de 300 tokens. ¿Cuánto cuesta re-embeberlos con una API de 0.02 $/1M y con una GPU propia de 0.80 $/h que da 20 000 tokens/s al 60 % de utilización?</summary>

$T = 1.5\times 10^{10}$ tokens. API: $1.5\times10^{10}/10^6 \times 0.02 = $ **300 $**. GPU: $1.5\times10^{10}/(20\,000\cdot3600\cdot0.6) \approx 347$ h → **≈ 278 $** (y ≈ 14.5 días de una GPU, o 1.5 días con 10). El coste se parece; el **tiempo de calendario** y la cuota de la API suelen decidir.
</details>
<details><summary><b>2 · (Cálculo)</b> Fan-out a 32 shards; cada shard tiene un 1 % de probabilidad de responder lento. ¿Qué fracción de queries es lenta?</summary>

$1 - 0.99^{32} \approx$ **27.5 %**. El p99 del sistema queda determinado por el p99.97 de cada shard. Soluciones: menos shards (réplicas completas si cabe), hedged requests, timeouts con resultados parciales.
</details>
<details><summary><b>3 · (Diagnóstico)</b> Tras desplegar un fine-tune de v2 (misma dimensión), el nDCG online cae a casi cero para las queries más populares y es normal para las raras. ¿Qué pasó?</summary>

La **caché de queries** no incluye la versión en la clave: las queries populares (aciertos de caché) reciben vectores del modelo anterior y se comparan con un índice del nuevo; las raras (fallos de caché) se embeben con el modelo nuevo. Arreglo: versión en la clave + invalidación al cambiar el alias.
</details>
<details><summary><b>4 · (Diagnóstico)</b> Tu adaptador lineal v2→v1 entrenado con 2 000 pares da peor nDCG que v1. ¿Tres causas posibles?</summary>

(a) Pocos pares para la dimensión (ridge con $d_2 \times d_1$ parámetros; prueba más $\lambda$ o Procrustes); (b) pares de **documentos** aplicados a **queries** con prefijos distintos (`query:` vs `passage:`): ajusta con pares de queries; (c) muestra no representativa (todo de un idioma o tema). Siempre compáralo con v1 mediante un test pareado antes de servirlo.
</details>
<details><summary><b>5 · (Transferencia)</b> Un cliente exige que sus documentos no salgan de la UE y que se puedan borrar en 24 h. ¿Qué cambia en el diseño?</summary>

Embedder **autohospedado** en la región (o API con garantía de residencia), colección o filtro obligatorio por tenant en el servidor, borrado por `doc_id` propagado a índice, réplicas, caché de documentos y backups, y logs sin texto de queries. El ruido en vectores no sustituye nada de lo anterior.
</details>
<details><summary><b>6 · (Transferencia)</b> Tienes 2 candidatos y tráfico para 1 000 impresiones al día. ¿A/B o interleaving?</summary>

Interleaving para decidir rápido qué candidato prefieren los usuarios (mucha más potencia por impresión, §10); después, si el cambio es importante para negocio, un A/B más largo sobre el ganador para medir impacto en métricas de sesión.
</details>
''')
    nb.md(r'''## 📚 Referencias
**Papers y artículos**
* He, H. & Thinking Machines Lab (2025). *Defeating Nondeterminism in LLM Inference* (blog, 10-sep-2025). https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/
* Dean, J. & Barroso, L. A. (2013). *The Tail at Scale*. Communications of the ACM 56(2). https://doi.org/10.1145/2408776.2408794
* Shen, Y., Xiong, Y., Xia, W., Soatto, S. (2020). *Towards Backward-Compatible Representation Learning*. CVPR 2020. https://arxiv.org/abs/2003.11942
* Song, C. & Raghunathan, A. (2020). *Information Leakage in Embedding Models*. ACM CCS 2020. https://arxiv.org/abs/2004.00053
* Morris, J. X. et al. (2023). *Text Embeddings Reveal (Almost) As Much As Text* (vec2text). EMNLP 2023. https://arxiv.org/abs/2310.06816
* Chapelle, O., Joachims, T., Radlinski, F., Yue, Y. (2012). *Large-scale validation and analysis of interleaved search evaluation*. ACM TOIS 30(1).
* Radlinski, F., Kurup, M., Joachims, T. (2008). *How does clickthrough data reflect retrieval quality?* CIKM 2008.
* Kohavi, R., Tang, D., Xu, Y. (2020). *Trustworthy Online Controlled Experiments*. Cambridge University Press.
* Douze, M. et al. (2024). *The Faiss library*. Preprint. https://arxiv.org/abs/2401.08281
* Kusupati, A. et al. (2022). *Matryoshka Representation Learning*. NeurIPS 2022. https://arxiv.org/abs/2205.13147
* Sculley, D. et al. (2015). *Hidden Technical Debt in Machine Learning Systems*. NeurIPS 2015.

**Documentación y blogs (consultados oct-2026)**
* Hugging Face Text Embeddings Inference: https://github.com/huggingface/text-embeddings-inference
* vLLM, *Pooling Models*: https://docs.vllm.ai/en/latest/models/pooling_models/
* Qdrant (modo local, named vectors, filtros, aliases): https://qdrant.tech/documentation/
* pgvector: https://github.com/pgvector/pgvector
* OpenAI, modelo `text-embedding-3-small` (precio): https://developers.openai.com/api/docs/models/text-embedding-3-small
* Google (14-jul-2025). *Gemini Embedding now generally available in the Gemini API* (precio 0.15 $/1M): https://developers.googleblog.com/en/gemini-embedding-available-gemini-api/
* Shakir, Aarsen, Lee (2024). *Binary and Scalar Embedding Quantization for Significantly Faster & Cheaper Retrieval* (blog de Hugging Face): https://huggingface.co/blog/embedding-quantization

**Qué no se pudo probar en el entorno de autoría:** modelos reales del hub (se usaron los fallbacks), TEI/vLLM (sin Docker ni hub), pgvector (sin Postgres), throughput en GPU. Qdrant local, FAISS y FastAPI sí se ejecutaron.
''')
