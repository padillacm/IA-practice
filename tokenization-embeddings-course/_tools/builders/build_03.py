"""Construye los notebooks del módulo 03 (lección + proyecto) y su README.

    python tokenization-embeddings-course/_tools/builders/build_03.py     # desde la raíz del repo
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from nbbuild import Notebook  # noqa: E402
import _a2_common as C  # noqa: E402

COURSE = "tokenization-embeddings-course"
SLUG = "03_wordpiece_unigram_sentencepiece"
MOD_DIR = os.path.join(HERE, "..", "..", SLUG)
LESSON_REL = f"{COURSE}/{SLUG}/{SLUG}.ipynb"
PROJ_REL = f"{COURSE}/{SLUG}/03_proyecto_wordpiece_unigram_sentencepiece.ipynb"
os.makedirs(os.path.join(MOD_DIR, "assets"), exist_ok=True)

# =====================================================================================
#                                       LECCIÓN
# =====================================================================================
nb = Notebook("Módulo 03 · WordPiece, Unigram, SentencePiece, tiktoken y HF tokenizers", colab_path=LESSON_REL)

nb.md(nb.badge() + r"""

# Módulo 03 · WordPiece, Unigram LM, SentencePiece, tiktoken y HF `tokenizers`

| | |
|---|---|
| **Nivel** | 🟡 Intermedio |
| **Duración estimada** | ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) |
| **GPU recomendada** | Ninguna (todo corre en CPU; `FAST_DEV_RUN = True` termina en minutos). Coste en Colab: ≈ 0 unidades |
| **Prerrequisitos** | Módulo 01 (Unicode, bytes, normalización) y módulo 02 (BPE desde cero, byte-level BPE, regex de pre-tokenización) |
| **Hilo conductor** | **Políglota**: en el módulo 02 construiste *un* tokenizer. Aquí aprendes las otras dos familias que dominan la industria y las comparas sobre el mismo corpus ES/EN/código |

> **Contexto Políglota Labs.** Tu CTO te pregunta: «¿por qué BERT usa `##`, T5 usa `▁`, GPT usa regex+bytes y alguien dice que
> Unigram segmenta mejor el español? ¿Cuál montamos para el buscador?». Al terminar esta lección podrás **implementar** el criterio de
> WordPiece y el algoritmo EM de Unigram a mano, **entrenar** los tres tipos con HF `tokenizers` y SentencePiece, **exportar** a `tiktoken`
> y defender la elección con métricas (fertilidad, bytes/token, alineación morfológica, robustez a `[UNK]`).
""")

nb.md(r"""
## 1. Objetivos de aprendizaje

Al terminar serás capaz de:

1. **Distinguir** las dos decisiones que toma todo tokenizer de subpalabras: *(a)* cómo se **construye** el vocabulario (BPE: fusionar de abajo arriba; WordPiece: fusionar por verosimilitud; Unigram: partir de un vocabulario grande y **podar**) y *(b)* cómo se **segmenta** un texto con ese vocabulario (merges en orden, *longest-match-first*, Viterbi).
2. **Derivar** el criterio de WordPiece como ganancia de log-verosimilitud de un modelo unigrama y **calcular a mano** un paso de entrenamiento (BPE vs WordPiece) sobre un corpus de 5 palabras.
3. **Implementar desde cero** el entrenamiento de Unigram LM (semilla de subcadenas → EM con *forward-backward* → poda por pérdida) y la segmentación por Viterbi y por muestreo.
4. **Explicar** qué aporta SentencePiece (tokenización *lossless*, sin pre-tokenización dependiente del idioma, `▁`, `byte_fallback`) y entrenar modelos `unigram` y `bpe` con su API.
5. **Construir** un pipeline completo de HF `tokenizers` (normalizer → pre-tokenizer → model → post-processor → decoder) y entrenar BPE/WordPiece/Unigram con la *misma* tubería para comparar solo el algoritmo.
6. **Aplicar** subword regularization (BPE-dropout, muestreo Unigram) y medir su efecto.
7. **Usar `tiktoken`**, reproducir su BPE en ~15 líneas y **exportar** un tokenizer BPE entrenado con HF a un `tiktoken.Encoding` verificando igualdad exacta.
8. **Evaluar** tokenizers con fertilidad, bytes por token, tasa de `[UNK]`, y alineación morfológica (F1 de fronteras), y **justificar** una elección con datos.
""")

nb.md(r"""
## 2. 🔁 Conexión con módulos anteriores

Antes de empezar, responde de memoria (despliega para comprobar). Lo necesitarás en la próxima hora.

<details><summary><b>R1 · (Módulo 02)</b> En BPE, ¿qué par se fusiona en cada paso y qué guarda el tokenizer entrenado para poder codificar texto nuevo?</summary>

El par adyacente **más frecuente** en el corpus (ponderado por frecuencia de palabra). Se guarda la **lista ordenada de merges**; al codificar se aplican los merges en ese orden (o, equivalentemente, se fusiona siempre el par con menor *rank*).
</details>

<details><summary><b>R2 · (Módulo 02)</b> ¿Para qué sirve la regex de pre-tokenización de GPT-2/cl100k y por qué ningún token cruza sus fronteras?</summary>

Parte el texto en «pre-tokens» (palabras con su espacio inicial, números, puntuación, espacios…) **antes** de aplicar BPE; el BPE se aplica por separado a cada pre-token, así que ningún merge puede unir dos pre-tokens. Evita tokens como `.\n\n` mezclados con letras y fija la granularidad mínima.
</details>

<details><summary><b>R3 · (Módulo 01)</b> ¿Por qué <code>"año"</code> puede ser 1 o 2 «caracteres» según la normalización (NFC vs NFD) y por qué importa antes de entrenar un tokenizer?</summary>

En NFD la `ñ` es `n` + U+0303 (2 code points); en NFC es 1 code point. Si entrenas con una forma e infieres con otra, los mismos textos producen secuencias de tokens distintas (o `[UNK]`). La normalización es parte del tokenizer y debe ser idéntica en entrenamiento e inferencia.
</details>

<details><summary><b>R4 · (Módulo 01)</b> ¿Cuántos bytes ocupa <code>"é"</code> en UTF-8 y qué implica para un tokenizer a nivel de byte?</summary>

2 bytes (`0xC3 0xA9`). Un tokenizer byte-level puede representar cualquier texto sin `[UNK]`, pero un carácter no latino puede costar 3–4 tokens si el vocabulario no tiene merges para él (la raíz del «impuesto por idioma» que veremos en el módulo 04).
</details>
""")

nb.code(C.pip_cell())
nb.code(C.SETUP.strip("\n"))
nb.md(r"""
### Corpus Políglota (utilidades)

Cada notebook del curso es autocontenido: la celda siguiente es la **copia local** de `carga_corpus()` (contrato común del curso).
Cadena de descarga: **oficial** (HF `wikimedia/wikipedia` ES/EN + CodeSearchNet Python) → **espejo** (muestra de Europarl ES/EN del
repositorio público `nltk_data` en GitHub + código Python real de la biblioteca estándar) → **sintético** con el mismo esquema (avisa en pantalla).
Devuelve `{"docs", "queries", "qrels", "source", "detail"}`; aquí solo usamos `docs` (el módulo 00 usa las consultas para BM25).
> Diferencia con la versión canónica del módulo 00: añadimos la clave `detail` (qué fuente se usó por idioma) y el mini golden set es automático (primera frase del documento).
""")
for _c in C.cells(C.CORPUS_1) + C.cells(C.CORPUS_2):
    nb.code(_c)
nb.code(C.CORPUS_USE.strip("\n"))
nb.code(C.METRICS.strip("\n") + "\n" + C.TOKMETRICS.strip("\n"))
nb.code(r'''
# Partimos el corpus en entrenamiento (80 %) y test (20 %) POR DOCUMENTO: nunca midas un tokenizer con texto con el que se entrenó.
rng = random.Random(SEED)
train_docs, test_docs = [], []
for lang in ["es", "en", "code"]:                       # partición estratificada por idioma
    pool = [d for d in docs if d["lang"] == lang]; rng.shuffle(pool)
    cut = int(0.8 * len(pool))
    train_docs += pool[:cut]; test_docs += pool[cut:]
train_texts = [d["text"] for d in train_docs]
test_by_lang = {l: [d["text"] for d in test_docs if d["lang"] == l] for l in ["es", "en", "code"]}
print(len(train_texts), "docs de entrenamiento |", {l: len(v) for l, v in test_by_lang.items()}, "docs de test por idioma")
''')

nb.md(r"""
## 3. Mapa de madurez

Estado del arte a **oct-2026**. 🟢 sólido (estándar de industria) · 🟡 emergente · 🔴 experimental.

| Técnica | Madurez | Quién la usa (con respaldo) | Fuente |
|---|---|---|---|
| BPE + regex + bytes (tiktoken) | 🟢 | Familia GPT (`cl100k_base`, `o200k_base`); Llama 3 parte del vocabulario de tiktoken (100K) y añade 28K tokens multilingües | Llama 3 (Grattafiori et al. 2024), tiktoken |
| WordPiece (inferencia *longest-match-first*, prefijo `##`) | 🟢 (en declive para modelos generativos) | BERT (vocabulario de 30 000) y descendientes | Devlin et al. 2018 |
| SentencePiece (BPE o Unigram, `▁`) | 🟢 | T5 (32 000 *wordpieces*), XLM-R (250 k), Llama 1/2 (BPE vía SentencePiece, dígitos sueltos, *byte fallback*), Gemma 3 (SentencePiece con dígitos separados y bytes) | Raffel 2019; Conneau 2019; Touvron 2023; Gemma 3 report 2025 |
| Unigram LM (poda por pérdida) | 🟢 | Es el `model_type` por defecto de SentencePiece (la librería con la que se entrenaron T5 y XLM-R) | Kudo 2018; docs de SentencePiece |
| Subword regularization (muestreo Unigram, BPE-dropout) | 🟡 | Estándar en traducción y ASR; **poco usado en el pretraining de LLMs grandes**; evidencia de robustez a typos en LLMs | Kudo 2018; Provilkov 2020; Chai et al. 2024 |
| Entrenar el tokenizer con *likelihood* exacto de WordPiece | 🔴 | El código de entrenamiento original de Google no es público; en HF `WordPieceTrainer` entrena con un procedimiento tipo BPE (lo verificamos abajo) | Schuster & Nakajima 2012; experimento de esta lección |
""")

nb.md(r"""
## 4. Intuición primero: dos decisiones, no una

Todo tokenizer de subpalabras responde dos preguntas **independientes**:

1. **Entrenamiento (elegir el vocabulario).** ¿Qué trozos de texto merecen una entrada en la tabla?
2. **Inferencia (segmentar).** Dado un vocabulario fijo y una palabra nueva, ¿cómo la parto?

| Familia | Cómo construye el vocabulario | Cómo segmenta | Marca de continuación |
|---|---|---|---|
| **BPE** (Sennrich 2016) | *Bottom-up*: empieza en caracteres/bytes y **fusiona el par más frecuente** | Aplica los merges aprendidos en orden de prioridad | ninguna (la regex/pre-tokenizer fija las fronteras) |
| **WordPiece** (Schuster & Nakajima 2012) | *Bottom-up*: fusiona el par que **más aumenta la verosimilitud** de un modelo de lenguaje unigrama | **Longest-match-first** (voraz, de izquierda a derecha) | `##` en las piezas que continúan una palabra |
| **Unigram LM** (Kudo 2018) | *Top-down*: empieza con un vocabulario enorme y **poda** lo que menos daña la verosimilitud (EM) | **Viterbi** (la segmentación más probable) o **muestreo** (regularización) | ninguna |
| **SentencePiece** (Kudo & Richardson 2018) | **No es un algoritmo, es una librería**: implementa BPE y Unigram directamente sobre texto crudo | según el modelo | `▁` marca el *inicio* de palabra |

> 💡 **Analogía de compresión.** BPE ≈ un compresor tipo LZ/Re-Pair: sustituye lo más repetido. Unigram ≈ elegir un **código con
> longitud variable óptimo** (Huffman/entropía) para un lenguaje de piezas y luego recortar el diccionario por lo que menos aporta.
> **Analogía IR.** Elegir el vocabulario es como decidir qué términos entran al índice invertido; la segmentación es el *stemmer*:
> distintos *stemmers* sobre el mismo corpus dan índices con recall distinto.
""")

nb.gemini(
    "imagen", "M03-IMG-01",
    "Tres formas de construir un vocabulario de subpalabras",
    "Contrasta BPE/WordPiece (bottom-up: fusionar) frente a Unigram (top-down: podar) con la misma palabra de ejemplo y el criterio de selección de cada uno.",
    """Diagrama técnico limpio, fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif legible, flechas claras, sin ilustraciones decorativas. Formato 16:9.

Título arriba al centro: "Tres formas de construir un vocabulario de subpalabras".

Tres filas horizontales (carriles), una por algoritmo. En cada carril, de izquierda a derecha, hay una secuencia de cajas que muestra la evolución de la MISMA palabra "internacional".

Carril 1 (color azul, etiqueta a la izquierda "BPE · bottom-up"): cajas: [i][n][t][e][r][n][a][c][i][o][n][a][l] (13 cajitas) → flecha con texto "fusiona el par MÁS FRECUENTE" → [in][t][er][n][a][c][io][n][a][l] → flecha → [inter][nac][ional]. Debajo del carril, una caja pequeña: "criterio: count(a,b)".

Carril 2 (color naranja, etiqueta "WordPiece · bottom-up"): cajas: [i][##n][##t][##e][##r][##n][##a][##c][##i][##o][##n][##a][##l] → flecha con texto "fusiona el par que MÁS AUMENTA la verosimilitud" → [in][##ter][##nac][##ional]. Debajo: caja pequeña: "criterio: ΔL ≈ m · (PMI − 1)"; aparte, una nota gris: "inferencia: longest-match-first".

Carril 3 (color verde, etiqueta "Unigram LM · top-down"): a la izquierda una nube grande de cajas superpuestas con texto "vocabulario semilla ≈ 1 000 000 subcadenas" → flecha con texto "EM + poda del 20 % de piezas con menor pérdida (repetir)" → nube más pequeña "vocabulario final" → resultado [▁inter][nacional]. Debajo: caja pequeña: "criterio: pérdida al eliminar la pieza; inferencia: Viterbi".

Bajo los tres carriles, una barra gris con el texto: "Misma pregunta, tres respuestas: ¿qué trozos merecen una entrada en el vocabulario?".
Todas las etiquetas en español, términos técnicos en inglés tal como se han escrito arriba.
Evita: texto ilegible o inventado, flechas ambiguas que se crucen, iconos decorativos, sombras, degradados, más de las cajas indicadas.""",
    "Tres carriles que muestran cómo BPE y WordPiece fusionan piezas de abajo arriba y Unigram poda un vocabulario grande de arriba abajo, para la palabra «internacional».",
    """
BPE        : i n t e r n a c i o n a l --(fusiona par MÁS FRECUENTE)--> in|ter|nac|ional
WordPiece  : i ##n ##t ##e ##r ... ##l --(fusiona par que MÁS SUBE la verosimilitud)--> in ##ter ##nac ##ional
Unigram    : [~1 000 000 subcadenas] --(EM + poda 20 % de menor pérdida, repetir)--> [vocab final] --> ▁inter nacional
""",
)
nb.md(r"""
> 👀 **Qué debes observar.** Los dos primeros carriles **empiezan pequeño y crecen** (fusionan); el tercero **empieza enorme y se encoge**.
> Lo que cambia entre BPE y WordPiece no es la dirección sino el **criterio** del par elegido; lo que cambia en Unigram es que el vocabulario
> se *optimiza* contra una función objetivo explícita (verosimilitud del corpus) en lugar de seguir una regla voraz.
""")

# ------------------------------- 5. WordPiece -------------------------------
nb.md(r"""
## 5. WordPiece: fusionar por verosimilitud (no por frecuencia)

### 5.1 La idea (Schuster & Nakajima, 2012)

WordPiece nació en Google para voz en japonés/coreano: sin espacios entre palabras y con alfabetos enormes, necesitaban un inventario de piezas
que **maximizara la verosimilitud** de los datos bajo un modelo de lenguaje, no solo que comprimiera. El procedimiento es el mismo esqueleto que BPE
(empezar en caracteres y fusionar de forma voraz) pero con otro **criterio de selección**.

### 5.2 📐 Derivación

Modela el texto como una secuencia de $N$ piezas independientes; con $c(t)$ ocurrencias de la pieza $t$, la verosimilitud máxima es

$$
\mathcal{L} \;=\; \sum_t c(t)\,\log\frac{c(t)}{N}\;=\;\sum_t f\!\big(c(t)\big)\;-\;f(N),\qquad f(x)=x\log x .
$$

Si fusionamos el par $(a,b)\to ab$ que aparece $m$ veces (y suponemos que no se solapa), los contadores cambian:
$c(a)\to c(a)-m,\; c(b)\to c(b)-m,\; c(ab)=m,\; N\to N-m$. La ganancia **exacta** es

$$
\Delta\mathcal{L}(a,b)=\big[f(c_a-m)-f(c_a)\big]+\big[f(c_b-m)-f(c_b)\big]+f(m)-\big[f(N-m)-f(N)\big].
$$

Con $m\ll c_a,c_b,N$ (expansión de primer orden de $f(x-m)\approx f(x)-m(\log x+1)$) queda:

$$
\boxed{\;\Delta\mathcal{L}(a,b)\;\approx\; m\Big(\log\frac{m\,N}{c_a\,c_b}-1\Big)\;=\;m\,\big(\mathrm{PMI}(a,b)-1\big)\;}
$$

donde $\mathrm{PMI}(a,b)=\log\frac{p(ab)}{p(a)p(b)}$ con $p(ab)\approx m/N$. Interpretación: **frecuencia ($m$) × asociación (PMI)**.

- **BPE** elige $\arg\max\, m$: ignora cuánto «se pertenecen» $a$ y $b$.
- La fórmula que verás en tutoriales (p. ej. el curso de LLM de Hugging Face) es $\text{score}(a,b)=\dfrac{m}{c_a\,c_b}$, que **solo conserva el cociente de PMI sin la log ni el peso $m$**: favorece pares *raros pero perfectamente asociados* (y ya verás que, sobre texto real, produce basura).
- El criterio de verosimilitud exacto pondera ambos: un par muy frecuente con PMI moderado puede ganar a uno raro con PMI altísimo.

> ⚠️ **Matiz honesto.** El paper de 2012 describe un procedimiento voraz que maximiza la verosimilitud de un modelo de lenguaje sobre el corpus; el código
> de entrenamiento que Google usó para BERT **no se publicó**. Lo que implementamos abajo es la versión «didáctica» $\Delta\mathcal L$ de arriba.
""")

nb.code(r'''
from collections import Counter

def init_splits(word_freqs: dict, prefix: str) -> dict:
    """Cada palabra -> lista de símbolos. prefix='##' (WordPiece: las piezas que continúan la palabra) o '' (BPE clásico)."""
    return {w: [w[0]] + [prefix + ch for ch in w[1:]] for w in word_freqs}

def estadisticas(word_freqs: dict, splits: dict):
    """Cuenta pares adyacentes y unidades, ponderando por la frecuencia de cada palabra."""
    pares, unidades = Counter(), Counter()
    for w, f in word_freqs.items():
        s = splits[w]
        for u in s: unidades[u] += f
        for a, b in zip(s, s[1:]): pares[(a, b)] += f
    return pares, unidades

def fusiona(par: tuple, splits: dict, prefix: str) -> str:
    """Aplica el merge (a,b)->ab en todas las palabras (in-place). En WordPiece el '##' del segundo símbolo desaparece al fusionar."""
    a, b = par; nuevo = a + b[len(prefix):]
    for w, s in splits.items():
        i, out = 0, []
        while i < len(s):
            if i < len(s) - 1 and s[i] == a and s[i + 1] == b: out.append(nuevo); i += 2
            else: out.append(s[i]); i += 1
        splits[w] = out
    return nuevo
''')

nb.code(r'''
def f_xlogx(x: float) -> float: return x * math.log(x) if x > 0 else 0.0

def puntuaciones(pares, unidades, criterio: str) -> dict:
    N = sum(unidades.values())
    if criterio == "bpe":                                   # frecuencia del par
        return dict(pares)
    if criterio == "score":                                 # m / (c_a c_b)  (fórmula de tutoriales)
        return {p: m / (unidades[p[0]] * unidades[p[1]]) for p, m in pares.items()}
    out = {}                                                # "verosimilitud": ΔL exacto del modelo unigrama
    for (a, b), m in pares.items():
        ca, cb = unidades[a], unidades[b]
        out[(a, b)] = (f_xlogx(ca - m) - f_xlogx(ca)) + (f_xlogx(cb - m) - f_xlogx(cb)) + f_xlogx(m) - (f_xlogx(N - m) - f_xlogx(N))
    return out

def entrena_fusiones(word_freqs: dict, n_fusiones: int, criterio: str = "bpe"):
    """Entrena n_fusiones merges con el criterio dado: 'bpe' | 'score' | 'verosimilitud'. Devuelve (historial, splits)."""
    prefix = "" if criterio == "bpe" else "##"
    splits = init_splits(word_freqs, prefix); historial = []
    for _ in range(n_fusiones):
        pares, unidades = estadisticas(word_freqs, splits)
        if not pares: break
        sc = puntuaciones(pares, unidades, criterio)
        mejor = max(sc, key=lambda p: (sc[p], p))           # desempate determinista
        historial.append({"par": mejor, "m": pares[mejor], "score": sc[mejor], "nuevo": fusiona(mejor, splits, prefix)})
    return historial, splits

def segmenta_con_fusiones(palabra: str, historial: list, prefix: str) -> list:
    """Segmenta una palabra NUEVA reaplicando los merges en el orden en que se aprendieron."""
    s = {palabra: [palabra[0]] + [prefix + ch for ch in palabra[1:]]}
    for h in historial: fusiona(h["par"], s, prefix)
    return s[palabra]
''')

nb.md(r"""
### 5.3 Un corpus de 5 palabras, resuelto a mano

Usamos el corpus de juguete clásico: `hug`×10, `pug`×5, `pun`×12, `bun`×4, `hugs`×5. Con prefijo `##` en las piezas internas:

| Palabra | Símbolos iniciales | Frec. |
|---|---|---|
| hug | `h` `##u` `##g` | 10 |
| pug | `p` `##u` `##g` | 5 |
| pun | `p` `##u` `##n` | 12 |
| bun | `b` `##u` `##n` | 4 |
| hugs | `h` `##u` `##g` `##s` | 5 |

Contadores de unidades: `h`=15, `p`=17, `b`=4, `##u`=36, `##g`=20, `##n`=16, `##s`=5. Pares: (`##u`,`##g`)=20, (`p`,`##u`)=17, (`##u`,`##n`)=16, (`h`,`##u`)=15, (`##g`,`##s`)=5, (`b`,`##u`)=4.

- **BPE** elige el más frecuente: `##u`+`##g` (20) → `ug`.
- **Score** $m/(c_a c_b)$: los cinco pares con `##u` valen todos $\tfrac{1}{36}\approx 0.0278$, pero (`##g`,`##s`) vale $5/(20\cdot5)=0.05$ → **gana `##g##s`**, un par que BPE dejaría para el final.
- **Verosimilitud ($\Delta\mathcal L$)**: lo calcula la celda siguiente; compárala con tu intuición antes de ejecutar.

🧪 **Predice antes de ejecutar:** ¿coincidirá la primera fusión por verosimilitud con la de BPE o con la de *score*?
""")

nb.code(r'''
toy = {"hug": 10, "pug": 5, "pun": 12, "bun": 4, "hugs": 5}
for crit in ["bpe", "score", "verosimilitud"]:
    hist, sp = entrena_fusiones(toy, 5, crit)
    print(f"{crit:>14}: " + "  ".join(f"{h['par'][0]}+{h['par'][1]} (m={h['m']}, s={h['score']:.3f})" for h in hist[:4]))
print()
pares, unid = estadisticas(toy, init_splits(toy, "##"))
sc = puntuaciones(pares, unid, "verosimilitud")
for p in sorted(sc, key=sc.get, reverse=True): print(f"ΔL{p} = {sc[p]:+.3f}   (m={pares[p]})")
''')

nb.md(r"""
Observa: BPE y verosimilitud coinciden aquí en el primer paso (`##u##g`), pero *score* no. En texto real los tres divergen mucho más, como vamos a ver.

**Comprobación numérica de la aproximación.** Antes de fiarnos del $\Delta\mathcal L\approx m(\mathrm{PMI}-1)$ de la derivación, verifiquemos sobre pares reales del español del corpus Políglota cuánto se parece a la ganancia exacta, y qué par elige cada criterio **en el primer paso**.
""")

nb.code(r'''
# Frecuencias de palabra (minúsculas, solo alfabéticas) del ESPAÑOL de entrenamiento
ws = Counter()
for d in train_docs:
    if d["lang"] == "es": ws.update(w.lower() for w in palabras(d["text"]) if w.isalpha())
N_PAL = 3000 if FAST_DEV_RUN else 8000
wf_es = dict(ws.most_common(N_PAL))
print(f"{len(ws)} palabras distintas; usamos las {len(wf_es)} más frecuentes ({sum(wf_es.values())/sum(ws.values()):.0%} de las ocurrencias)")

pares, unid = estadisticas(wf_es, init_splits(wf_es, "##")); N = sum(unid.values())
exacto = puntuaciones(pares, unid, "verosimilitud"); sc_wp = puntuaciones(pares, unid, "score")
aprox = {p: m * (math.log(m * N / (unid[p[0]] * unid[p[1]])) - 1) for p, m in pares.items()}
top = sorted(pares, key=pares.get, reverse=True)[:300]
x = np.array([exacto[p] for p in top]); y = np.array([aprox[p] for p in top])
print(f"corr(exacto, aproximado) en los 300 pares más frecuentes = {np.corrcoef(x, y)[0,1]:.4f}")
print("Mejor par por frecuencia (BPE):       ", max(pares, key=pares.get))
print("Mejor par por score m/(ca·cb):        ", max(sc_wp, key=sc_wp.get), "  <- ruido: caracteres raros de nombres propios")
print("Mejor par por ΔL (verosimilitud):     ", max(exacto, key=exacto.get))
''')

nb.code(r'''
# Entrenamos 300 merges con cada criterio y medimos tokens/palabra en palabras NO vistas (las del test)
N_MERGES = 150 if FAST_DEV_RUN else 400
hist_crit, curvas = {}, {}
test_words = [w.lower() for t in test_by_lang["es"] for w in palabras(t) if w.isalpha()][:4000]
for crit in ["bpe", "score", "verosimilitud"]:
    hist_crit[crit], sp = entrena_fusiones(wf_es, N_MERGES, crit)
    prefix = "" if crit == "bpe" else "##"
    curvas[crit] = []
    for k in range(0, N_MERGES + 1, 10):
        muestra = test_words[:800]
        curvas[crit].append((k, np.mean([len(segmenta_con_fusiones(w, hist_crit[crit][:k], prefix)) for w in muestra])))
    print(f"{crit:>14}: primeras fusiones ->", [h["nuevo"] for h in hist_crit[crit][:12]])

fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
ax[0].scatter(x, y, s=12, c=COL["azul"], alpha=0.6)
lim = [min(x.min(), y.min()), max(x.max(), y.max())]; ax[0].plot(lim, lim, "--", c=COL["gris"], label="y = x")
ax[0].set_xlabel("ΔL exacto (nats)"); ax[0].set_ylabel("Aproximación m·(PMI − 1)"); ax[0].set_title("La aproximación sigue al ΔL exacto (y lo subestima si m es grande)"); ax[0].legend()
for crit, c_ in zip(curvas, [COL["azul"], COL["rojo"], COL["naranja"]]):
    ks, vs = zip(*curvas[crit]); ax[1].plot(ks, vs, label=crit, c=c_, lw=2)
ax[1].set_xlabel("Nº de merges aprendidos"); ax[1].set_ylabel("Piezas por palabra (palabras de test)"); ax[1].set_title("Compresión en palabras no vistas"); ax[1].legend()
plt.tight_layout(); plt.show()
''')

nb.md(r"""
> 👀 **Qué debes observar.**
> **Izquierda:** los puntos siguen la diagonal: la aproximación $m(\mathrm{PMI}-1)$ ordena bien los pares y es casi exacta para ganancias pequeñas o moderadas; en los pares más frecuentes (cuando $m$ es comparable a $c_a$ o $c_b$ la expansión de primer orden deja de valer) **subestima** la ganancia real.
> **Derecha:** BPE comprime más rápido (minimiza piezas por palabra, que es *su* objetivo); el criterio **score** casi no comprime (elige pares raros y «bonitos» estadísticamente);
> **verosimilitud** queda entre ambos y, mirando sus primeras fusiones (`##ión`, `##ción`…), tiende a descubrir **sufijos reales**. Conclusión: *el criterio de selección decide qué trozos
> entran al vocabulario, no solo cuánto comprimen*. Ojo: la curva que gana en compresión no es necesariamente la que mejor modela (módulo 04).
""")

nb.md(r"""
### 5.4 Inferencia WordPiece: *longest-match-first*

Una vez fijado el vocabulario, WordPiece **no** reaplica los merges: segmenta cada palabra buscando, desde el inicio, la **pieza más larga** que esté en el vocabulario
(las siguientes llevan el prefijo `##`). Si en algún punto no encuentra ninguna, **toda la palabra se convierte en `[UNK]`** (¡no solo el trozo!). Es un algoritmo voraz y, escrito ingenuamente, $O(n^2)$ por palabra.

Vamos a implementarlo y a verificar que coincide **exactamente** con HF `tokenizers` usando el mismo vocabulario.
""")

nb.code(r'''
from tokenizers import Tokenizer, models, pre_tokenizers, normalizers, trainers, decoders, processors

def wordpiece_encode(palabra: str, vocab, unk: str = "[UNK]") -> list:
    """Longest-match-first. Devuelve piezas con '##' en las continuaciones, o [UNK] si falla en cualquier punto."""
    out, i = [], 0
    while i < len(palabra):
        j, pieza = len(palabra), None
        while j > i:
            cand = palabra[i:j] if i == 0 else "##" + palabra[i:j]
            if cand in vocab: pieza = cand; break
            j -= 1
        if pieza is None: return [unk]
        out.append(pieza); i = j
    return out

# Vocabulario: caracteres + merges aprendidos con el criterio de verosimilitud (con '##' en las continuaciones)
_, sp_v = entrena_fusiones(wf_es, N_MERGES, "verosimilitud")
vocab_set = {"[UNK]"} | {s for segs in sp_v.values() for s in segs}
vocab_ids = {t: i for i, t in enumerate(sorted(vocab_set))}
hf_wp = Tokenizer(models.WordPiece(vocab=vocab_ids, unk_token="[UNK]", max_input_chars_per_word=100))
hf_wp.pre_tokenizer = pre_tokenizers.WhitespaceSplit()

pruebas = test_words[:1500] + ["internacionalización", "wxyzq", "café"]
difieren = [w for w in pruebas if wordpiece_encode(w, vocab_set) != hf_wp.encode(w).tokens]
print(f"vocabulario: {len(vocab_set)} piezas | palabras comparadas: {len(pruebas)} | discrepancias con HF tokenizers: {len(difieren)}")
for w in ["internacionalización", "wxyzq", "recomendaciones"]:
    print(f"  {w:>22} -> {wordpiece_encode(w, vocab_set)}")
''')

nb.md(r"""
> 🏭 **Sorpresa de ingeniería (verifícala tú mismo en la sección 9).** En HF `tokenizers`, `WordPieceTrainer` **no implementa el criterio de verosimilitud**: internamente reutiliza la maquinaria de BPE (fusiones por frecuencia) y solo añade
> el prefijo `##` y la inferencia *longest-match-first*. Lo comprobaremos midiendo el solapamiento de vocabularios con `BpeTrainer`.
""")

# ------------------------------- 6. Unigram LM -------------------------------
nb.md(r"""
## 6. Unigram LM (Kudo, 2018): un vocabulario que se *optimiza*, no que se acumula

### 6.1 El modelo

Un tokenizer Unigram es un **modelo de lenguaje de piezas independientes**: $P(\mathbf{x})=\prod_{i=1}^{M}p(x_i)$, con $\sum_{t\in V}p(t)=1$.
Una palabra (o frase) $X$ admite **muchas** segmentaciones $\mathbf{x}\in S(X)$ (el conjunto de caminos en un *lattice*). Hay dos usos:

- **Inferencia determinista (Viterbi):** $\mathbf{x}^*=\arg\max_{\mathbf{x}\in S(X)}P(\mathbf{x})$, por programación dinámica en $O(n\cdot L)$ ($L$ = longitud máxima de pieza).
- **Muestreo (subword regularization):** $\mathbf{x}\sim P(\mathbf{x}\mid X)\propto P(\mathbf{x})^{\alpha}$ con $\alpha\in(0,1]$ (suaviza la distribución).

### 6.2 📐 Entrenamiento: EM sobre una variable oculta

El corpus tiene verosimilitud marginal (suma sobre *todas* las segmentaciones, la segmentación es la variable oculta):

$$
\mathcal{L}(V,p)=\sum_{s=1}^{|D|}\log P(X^{(s)})=\sum_{s}\log\sum_{\mathbf{x}\in S(X^{(s)})}P(\mathbf{x}).
$$

- **E-step (cuentas esperadas).** Para cada palabra se recorre el lattice con *forward-backward*: $\alpha_j=\operatorname{logsumexp}_{i<j}\big(\alpha_i+\log p(w_{i:j})\big)$,
  $\beta_i=\operatorname{logsumexp}_{j>i}\big(\log p(w_{i:j})+\beta_j\big)$. La probabilidad *a posteriori* de que la arista $(i,j)$ esté en la segmentación es $\gamma_{ij}=\exp(\alpha_i+\log p(w_{i:j})+\beta_j-\alpha_n)$ y la cuenta esperada de una pieza $t$ es $c(t)=\sum_{\text{palabras}}f\sum_{(i,j):w_{i:j}=t}\gamma_{ij}$.
- **M-step.** $p(t)\leftarrow c(t)/\sum_{t'}c(t')$. (SentencePiece usa una variante bayesiana con digamma; la forma simple basta para entender el mecanismo.)
- **Poda.** Con el $p$ actual, para cada pieza $t$ (salvo los caracteres sueltos, que garantizan cobertura) se calcula cuánto **empeora** $\mathcal{L}$ si se elimina: $\text{loss}(t)=\mathcal{L}(V)-\mathcal{L}(V\setminus\{t\})$.
  Se conserva una fracción $\eta$ de las piezas con mayor pérdida (Kudo propone 80 %; en SentencePiece el parámetro es `shrinking_factor`, **0.75 por defecto**) y se repite EM. Se itera hasta llegar al tamaño de vocabulario deseado.
- **Semilla.** Todos los caracteres + las subcadenas más «valiosas» (SentencePiece usa un array de sufijos para ordenarlas por frecuencia × longitud y se queda con ~1 M).

> 💡 **Contraste con BPE.** BPE nunca *reconsidera*: una fusión hecha es permanente (y sus piezas intermedias quedan en el vocabulario aunque ya nadie las use: es la fuente de muchos «tokens basura», módulo 05).
> Unigram **revisa** todo el vocabulario en cada ronda contra una función objetivo explícita.

### 6.3 Un ejemplo resuelto a mano: la palabra `hugs`

Vocabulario semilla (probabilidades que suman 1): `h`=.10, `u`=.10, `g`=.10, `s`=.10, `hu`=.05, `ug`=.15, `gs`=.05, `hug`=.15, `ugs`=.05, `hugs`=.15.

| Segmentación | Producto de probabilidades |
|---|---|
| `hugs` | 0.15 |
| `hug`·`s` | 0.15·0.10 = 0.015 |
| `h`·`ugs` | 0.10·0.05 = 0.005 |
| `hu`·`gs` | 0.05·0.05 = 0.0025 |
| `h`·`ug`·`s` | 0.10·0.15·0.10 = 0.0015 |
| `hu`·`g`·`s` | 0.05·0.10·0.10 = 0.0005 |
| `h`·`u`·`gs` | 0.10·0.10·0.05 = 0.0005 |
| `h`·`u`·`g`·`s` | 0.10⁴ = 0.0001 |

Suma $P(X)=0.1751$. Viterbi elige `hugs` y su probabilidad *a posteriori* es $0.15/0.1751\approx 0.857$. La celda siguiente lo verifica con el código genérico que usaremos luego.
""")

nb.code(r'''
NEG = -1e18   # "−∞" para log-probabilidades

def lse(a: float, b: float) -> float:
    """log(exp(a) + exp(b)) estable."""
    if a < b: a, b = b, a
    return a if b <= NEG else a + math.log1p(math.exp(b - a))

def aristas(s: str, logp: dict, max_len: int):
    """Genera todas las aristas (i, j, log p) del lattice de la cadena s."""
    for i in range(len(s)):
        for j in range(i + 1, min(len(s), i + max_len) + 1):
            p = logp.get(s[i:j])
            if p is not None: yield i, j, p

def viterbi(s: str, logp: dict, max_len: int = 8):
    """Segmentación más probable por programación dinámica. Devuelve (piezas, log P)."""
    n = len(s); best = [NEG] * (n + 1); best[0] = 0.0; back = [0] * (n + 1)
    for i, j, p in sorted(aristas(s, logp, max_len), key=lambda e: e[1]):
        if best[i] + p > best[j]: best[j] = best[i] + p; back[j] = i
    out, j = [], n
    while j > 0: out.append(s[back[j]:j]); j = back[j]
    return out[::-1], best[n]

def forward_backward(s: str, logp: dict, max_len: int = 8):
    """alpha[j], beta[i] en log-espacio y la lista de aristas."""
    n = len(s); ar = list(aristas(s, logp, max_len))
    alpha = [NEG] * (n + 1); alpha[0] = 0.0
    for i, j, p in sorted(ar, key=lambda e: e[1]):
        if alpha[i] > NEG: alpha[j] = lse(alpha[j], alpha[i] + p)
    beta = [NEG] * (n + 1); beta[n] = 0.0
    for i, j, p in sorted(ar, key=lambda e: -e[0]):
        if beta[j] > NEG: beta[i] = lse(beta[i], p + beta[j])
    return alpha, beta, ar

def e_step(word_freqs: dict, logp: dict, max_len: int = 8):
    """Cuentas esperadas de cada pieza y log-verosimilitud total del corpus."""
    esp, total = Counter(), 0.0
    for w, f in word_freqs.items():
        alpha, beta, ar = forward_backward(w, logp, max_len); n = len(w)
        total += f * alpha[n]
        for i, j, p in ar: esp[w[i:j]] += f * math.exp(alpha[i] + p + beta[j] - alpha[n])
    return esp, total

# --- verificación con el ejemplo a mano ---
probs = {"h": .10, "u": .10, "g": .10, "s": .10, "hu": .05, "ug": .15, "gs": .05, "hug": .15, "ugs": .05, "hugs": .15}
lp_toy = {k: math.log(v) for k, v in probs.items()}
alpha, beta, ar = forward_backward("hugs", lp_toy, 4)
print("P(X) =", round(math.exp(alpha[4]), 4), "| Viterbi:", viterbi("hugs", lp_toy, 4)[0], "| P(viterbi|X) =", round(0.15 / math.exp(alpha[4]), 3))
esp, ll = e_step({"hugs": 1}, lp_toy, 4)
print("cuentas esperadas (suman nº medio de piezas):", {k: round(v, 3) for k, v in esp.items()}, "| suma =", round(sum(esp.values()), 3))
''')

nb.gemini(
    "video", "M03-VID-01",
    "Unigram LM: lattice, EM y poda de un vocabulario",
    "Animación paso a paso del entrenamiento Unigram sobre la palabra «hugs»: todas las segmentaciones del lattice con su probabilidad, camino de Viterbi, reestimación EM y poda de piezas de menor pérdida.",
    """Animación explicativa, 16:9, estilo diagrama técnico limpio: fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif legible, sin ilustraciones decorativas, sin voz en off, ritmo calmado (cada escena se sostiene lo suficiente para leer). Todo el texto en pantalla en español, términos técnicos en inglés. Duración total 40 segundos.

Datos exactos (no inventes otros números). Palabra de ejemplo: "hugs". Vocabulario semilla con probabilidades: h = 0.10, u = 0.10, g = 0.10, s = 0.10, hu = 0.05, ug = 0.15, gs = 0.05, hug = 0.15, ugs = 0.05, hugs = 0.15.

Escena 1 (0–6 s): Título "Unigram LM: entrenar un vocabulario con EM y poda". Aparece una tabla de 10 filas "pieza | p" con los valores exactos de arriba. Subtítulo: "Vocabulario semilla (suma de probabilidades = 1)".
Escena 2 (6–16 s): La palabra "hugs" como 4 cuadros h u g s alineados horizontalmente y numerados con nodos 0 1 2 3 4. Se dibujan arcos sobre los cuadros, uno por cada pieza del vocabulario que cabe (h, u, g, s, hu, ug, gs, hug, ugs, hugs), cada arco con su etiqueta. Luego aparece, a la derecha, la lista de las 8 segmentaciones con su producto, una a una: "hugs = 0.15", "hug·s = 0.015", "h·ugs = 0.005", "hu·gs = 0.0025", "h·ug·s = 0.0015", "hu·g·s = 0.0005", "h·u·gs = 0.0005", "h·u·g·s = 0.0001". Debajo: "P(X) = suma = 0.1751".
Escena 3 (16–22 s): Se resalta en naranja grueso el camino "hugs" y aparece la etiqueta "Viterbi = argmax P(x) = hugs (posterior 0.857)".
Escena 4 (22–30 s): Un ciclo con dos cajas conectadas por flechas circulares: "E-step: cuentas esperadas (forward-backward)" → "M-step: p(t) = c(t) / Σ c" y de nuevo al E-step; junto al ciclo, las barras de las probabilidades de las piezas cambian de altura suavemente (animación de reestimación) sin mostrar valores nuevos.
Escena 5 (30–38 s): Las 10 piezas se ordenan en una columna con una barra verde "pérdida al eliminar la pieza" (alta para hugs, hug, s, h; baja para gs, ugs, hu). Las tres piezas de menor pérdida (gs, ugs, hu) se desvanecen en gris con una cruz roja #D62728 y el texto "poda: se eliminan las piezas que menos dañan la verosimilitud; los caracteres sueltos NUNCA se podan".
Escena 6 (38–40 s): Texto final centrado: "Repetir EM + poda hasta llegar al tamaño de vocabulario deseado".
Evita: números distintos a los dados, texto ilegible o diminuto, flechas que se crucen sin motivo, elementos decorativos, transiciones rápidas, música o voz.""",
    "Animación de 40 segundos que muestra el lattice de la palabra «hugs», el camino de Viterbi, el ciclo EM y la poda de piezas con menor pérdida en Unigram LM.",
    """
 vocabulario semilla ──► lattice de "hugs" ──► Viterbi: hugs (post. 0.857)
 ┌─────────────┐          0 ─h─1─u─2─g─3─s─ 4
 │ pieza   p   │          arcos: h u g s hu ug gs hug ugs hugs
 │ hugs  0.15  │                   │
 │ hug   0.15  │                   ▼
 │ ...         │          E-step (forward-backward) ⇄ M-step (p = c / Σc)
 └─────────────┘                   │
                                   ▼
          poda: se caen gs, ugs, hu (menor pérdida); h u g s se quedan siempre
""",
    duration="40 s",
)
nb.md(r"""
> 👀 **Qué debes observar.** (1) El lattice codifica *todas* las segmentaciones a la vez: no hay que enumerarlas, la programación dinámica las suma o maximiza.
> (2) Viterbi no es «la única segmentación»: aquí `hugs` tiene probabilidad posterior 0.857, pero `hug·s` conserva 8.6 %. Esa incertidumbre es la que explota el muestreo (subword regularization).
> (3) La poda es **la diferencia clave con BPE**: las piezas se *eliminan* por su contribución a la verosimilitud, y los caracteres sueltos se protegen para garantizar cobertura.
""")

nb.code(r'''
def m_step(esp: Counter, chars: set) -> dict:
    tot = sum(esp.values())
    return {p: math.log(c / tot) for p, c in esp.items() if c > 1e-3 or p in chars}    # descarta piezas con cuenta ~0

def semilla(word_freqs: dict, max_len: int = 8, k: int = 3000):
    """Vocabulario inicial: todos los caracteres + las k subcadenas con mayor (frecuencia × longitud)."""
    cnt = Counter()
    for w, f in word_freqs.items():
        for i in range(len(w)):
            for j in range(i + 1, min(len(w), i + max_len) + 1): cnt[w[i:j]] += f
    chars = {p for p in cnt if len(p) == 1}
    top = sorted((p for p in cnt if len(p) > 1), key=lambda p: -cnt[p] * len(p))[:k]
    tot = sum(cnt[p] for p in chars | set(top))
    return {p: math.log(cnt[p] / tot) for p in chars | set(top)}, chars

def poda(word_freqs: dict, logp: dict, chars: set, keep: float = 0.8, target: int = 0, max_len: int = 8) -> dict:
    """Quita las piezas cuya ausencia empeora menos la verosimilitud (aproximada con Viterbi). Nunca borra caracteres sueltos."""
    base = {w: viterbi(w, logp, max_len) for w in word_freqs}
    usan = collections.defaultdict(list)
    for w, (seg, _) in base.items():
        for p in set(seg):
            if p not in chars: usan[p].append(w)
    perdida = {}
    for p in logp:
        if p in chars: continue
        lp2 = {q: v for q, v in logp.items() if q != p}                       # vocabulario sin p
        perdida[p] = sum(word_freqs[w] * (base[w][1] - viterbi(w, lp2, max_len)[1]) for w in usan.get(p, []))   # >= 0
    orden = sorted(perdida, key=perdida.get, reverse=True)                      # más dañinas de borrar primero
    n_keep = max(int(len(orden) * keep), target - len(chars))
    keepset = set(orden[:n_keep])
    return {p: v for p, v in logp.items() if p in chars or p in keepset}
''')

nb.code(r'''
def entrena_unigram(word_freqs: dict, vocab_size: int, max_len: int = 8, seed_k: int = 3000, keep: float = 0.8, em_iters: int = 2):
    """Unigram LM mínimo: semilla -> [EM x em_iters -> poda] hasta llegar a vocab_size. Devuelve (log p, historial, caracteres)."""
    logp, chars = semilla(word_freqs, max_len, seed_k); hist = []
    while True:
        for _ in range(em_iters):
            esp, ll = e_step(word_freqs, logp, max_len); logp = m_step(esp, chars)
        hist.append({"vocab": len(logp), "loglik": ll})
        if len(logp) <= vocab_size: break
        logp = poda(word_freqs, logp, chars, keep, target=vocab_size, max_len=max_len)
    return logp, hist, chars

wf_uni = {"▁" + w: f for w, f in wf_es.items()}          # '▁' marca el inicio de palabra (como SentencePiece)
V_UNI = 500 if FAST_DEV_RUN else 2000
t0 = time.time()
logp_uni, hist_uni, chars_uni = entrena_unigram(wf_uni, V_UNI, seed_k=3000 if FAST_DEV_RUN else 12000)
print(f"entrenado en {time.time()-t0:.1f}s | rondas: {len(hist_uni)} | vocabulario final: {len(logp_uni)}")
for h in hist_uni: print(f"  |V| = {h['vocab']:5d}   log-verosimilitud del corpus = {h['loglik']:,.0f}")
for w in ["internacional", "parlamento", "recomendaciones", "nuevos", "unigram"]:
    print(f"  {w:>16} -> {viterbi('▁' + w, logp_uni)[0]}")
''')

nb.code(r'''
# --- Lattice de una palabra: todas las piezas posibles (arcos) y el camino de Viterbi ---
from matplotlib.patches import FancyArrowPatch

def dibuja_lattice(palabra: str, logp: dict, ax, max_len: int = 8):
    s = "▁" + palabra; n = len(s); seg, _ = viterbi(s, logp, max_len)
    camino, pos = set(), 0
    for p in seg: camino.add((pos, pos + len(p))); pos += len(p)
    for i, j, p in aristas(s, logp, max_len):
        if j - i == 1 and (i, j) not in camino: continue                 # omitimos caracteres sueltos fuera del camino (ruido visual)
        en = (i, j) in camino
        rad = 0.6 if i % 2 == 0 else -0.6                                  # alterna arriba/abajo para que no se tapen
        ax.add_patch(FancyArrowPatch((i, 0), (j, 0), connectionstyle=f"arc3,rad={rad}", arrowstyle="-", lw=2.8 if en else 0.9,
                                     color=COL["naranja"] if en else COL["gris"], alpha=1 if en else 0.55))
        y = -rad * (j - i) / 2                                             # altura del vértice del arco
        ax.text((i + j) / 2, y + (0.35 if y > 0 else -0.35), f"{s[i:j]}\n{p:.1f}", ha="center", va="center", fontsize=7,
                color=COL["naranja"] if en else COL["gris"])
    ax.scatter(range(n + 1), [0] * (n + 1), c=COL["azul"], zorder=3, s=25)
    for k, ch in enumerate(s): ax.text(k + 0.5, 0, ch, ha="center", va="center", fontsize=9, color=COL["azul"], fontweight="bold",
                                       bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))
    ax.set_xlim(-0.5, n + 0.5); ax.set_ylim(-3.4, 3.4); ax.axis("off")
    ax.set_title(f"Lattice de «{palabra}» (naranja = Viterbi; etiqueta = pieza y log p) → {seg}", fontsize=10)

fig, ax = plt.subplots(1, 1, figsize=(12, 4.6)); dibuja_lattice("recomendaciones", logp_uni, ax); plt.show()
''')

nb.md(r"""
> 👀 **Qué debes observar.** Cada arco es una pieza que *cabe* en esa posición; el lattice contiene **todas** las segmentaciones posibles como caminos de izquierda a derecha. El camino naranja (Viterbi) es el de mayor suma de log-probabilidades:
> prefiere pocas piezas frecuentes (log p ≈ −5 a −7) antes que muchas piezas cortas. Así «ve» Unigram la morfología: `reco·men·da·ciones` aparece porque cada trozo es una pieza probable por sí misma.
""")

nb.code(r'''
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
ax[0].plot([h["vocab"] for h in hist_uni], [h["loglik"] for h in hist_uni], "o-", c=COL["verde"], lw=2)
ax[0].invert_xaxis(); ax[0].set_xlabel("Tamaño del vocabulario |V| (la poda avanza hacia la derecha)"); ax[0].set_ylabel("Log-verosimilitud del corpus")
ax[0].set_title("EM + poda: verosimilitud vs tamaño del vocabulario")

# ¿Cuánta incertidumbre hay en la segmentación? P(camino de Viterbi | palabra) = P(viterbi) / P(palabra)
post = []
for w in list(wf_uni)[:1500]:
    alpha_, _, _ = forward_backward(w, logp_uni); seg, lp_best = viterbi(w, logp_uni)
    post.append(math.exp(lp_best - alpha_[len(w)]))
ax[1].hist(post, bins=30, color=COL["azul"], alpha=0.85)
ax[1].set_xlabel("P(segmentación de Viterbi | palabra)"); ax[1].set_ylabel("Nº de palabras"); ax[1].set_title("Ambigüedad de la segmentación Unigram")
plt.tight_layout(); plt.show()
print(f"mediana de P(Viterbi | palabra) = {np.median(post):.2f}; palabras con P < 0.5: {np.mean(np.array(post) < 0.5):.0%}")
''')

nb.md(r"""
> 👀 **Qué debes observar.** **Izquierda:** la log-verosimilitud **sube** al principio (EM refina probabilidades y desaparecen piezas sin uso) y luego **cae suavemente** conforme la poda quita piezas útiles:
> es el trade-off *tamaño del vocabulario ↔ ajuste* que BPE no te muestra. **Derecha:** la mayoría de las palabras tiene una segmentación claramente dominante (mediana de P(Viterbi | palabra) ≈ 0.9 con este vocabulario pequeño), pero hay una cola de palabras (≈ 4 % con P < 0.5) con **ambigüedad real**; esa masa de probabilidad es la que explota el muestreo.
""")

nb.md(r"""
### 6.4 Subword regularization: muestrear segmentaciones

Si en lugar de Viterbi **muestreas** $\mathbf{x}\sim P(\mathbf{x}\mid X)^{\alpha}$ durante el entrenamiento del modelo de lenguaje/traducción, el mismo texto aparece con tokenizaciones distintas en cada época
(*data augmentation* a nivel de tokenización). Kudo (2018) lo propuso con Unigram; Provilkov et al. (2020) con **BPE-dropout** (omitir cada merge con probabilidad $p$). Muestrear exactamente se logra con
*forward-filtering, backward-sampling*: se calcula $\alpha$ hacia adelante con $\alpha\cdot\log p$ y se muestrea hacia atrás eligiendo la última pieza con probabilidad $\propto e^{\alpha_i+\alpha\log p(w_{i:j})}$.
""")

nb.code(r'''
def muestrea(s: str, logp: dict, alpha: float = 1.0, max_len: int = 8, rng=random) -> list:
    """Forward-filtering / backward-sampling: segmentación ~ P(x)^alpha normalizada."""
    lp = {k: alpha * v for k, v in logp.items()}
    fw, _, _ = forward_backward(s, lp, max_len)
    j, out = len(s), []
    while j > 0:
        cand = [(i, fw[i] + lp[s[i:j]]) for i in range(max(0, j - max_len), j) if s[i:j] in lp and fw[i] > NEG]
        m = max(c[1] for c in cand)
        i = rng.choices([c[0] for c in cand], weights=[math.exp(c[1] - m) for c in cand])[0]
        out.append(s[i:j]); j = i
    return out[::-1]

r = random.Random(SEED)
for a in [1.0, 0.5, 0.2]:
    print(f"alpha={a}:")
    for _ in range(3): print("   ", muestrea("▁internacionalización", logp_uni, a, rng=r))
palabras_test = ["▁" + w for w in test_words[:300]]
res_alpha = {}
for a in [2.0, 1.0, 0.5, 0.2, 0.05]:
    segs = [muestrea(w, logp_uni, a, rng=r) for w in palabras_test]
    res_alpha[a] = np.mean([len(s_) for s_ in segs])
vit = np.mean([len(viterbi(w, logp_uni)[0]) for w in palabras_test])
print("piezas/palabra  Viterbi:", round(float(vit), 3), "| muestreo:", {a: round(float(v), 3) for a, v in res_alpha.items()})
''')

nb.md(r"""
Con $\alpha$ grande el muestreo se concentra en Viterbi; con $\alpha\to0$ la distribución se aplana y salen segmentaciones más fragmentadas (más piezas por palabra). Para regularizar se suele usar $\alpha$ entre 0.1 y 0.5
(SentencePiece: `enable_sampling=True, alpha=0.1, nbest_size=-1`). **Importante:** el muestreo es solo para **entrenar**; en inferencia se usa siempre la segmentación determinista.
""")

# ------------------------------- 7. SentencePiece -------------------------------
nb.md(r"""
## 7. SentencePiece: una *librería*, no un algoritmo

**SentencePiece** (Kudo & Richardson, 2018) no inventa un algoritmo de subpalabras: **implementa BPE y Unigram** (más `char` y `word`) con cuatro decisiones de diseño que cambiaron la industria:

1. **Entrena desde texto crudo, sin pre-tokenización dependiente del idioma.** No hay un `split()` previo: sirve igual para inglés, español, chino o japonés (sin espacios). Internamente solo separa por *script* Unicode y números (`split_by_unicode_script`, `split_by_number`).
2. **Tokenización reversible (*lossless*).** El espacio se convierte en un símbolo visible `▁` (U+2581) que forma parte de los tokens: $\text{decode}(\text{encode}(s))=s$. Con WordPiece/BERT, en cambio, se pierde la información de espacios («don't» → `don ' t`).
3. **Modelo autocontenido.** El archivo `.model` incluye vocabulario **y** reglas de normalización (por defecto NFKC con ajustes, `nmt_nfkc`); el mismo binario tokeniza igual en cualquier sitio.
4. **Regularización integrada.** Muestreo Unigram y BPE-dropout *on the fly* (`enable_sampling`, `alpha`, `nbest_size`).

Defaults que debes conocer (los comprobamos en el código de la versión instalada): `model_type=unigram`, `character_coverage=0.9995` (porcentaje de caracteres del corpus que deben quedar cubiertos; usa 1.0 para alfabetos pequeños), `byte_fallback=False`, `add_dummy_prefix=True`,
`remove_extra_whitespaces=True`, `split_digits=False`, `max_sentence_length=4192` **bytes** (¡las líneas más largas se descartan en silencio!).
""")

nb.gemini(
    "imagen", "M03-IMG-02",
    "Tokenización reversible con ▁ frente a pre-tokenizar por espacios",
    "Muestra que con espacios como símbolo visible (▁) la tokenización es reversible, y que un pre-tokenizador que descarta los espacios pierde información (dos espacios, indentación, saltos de línea).",
    """Diagrama técnico limpio, fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280, rojo #D62728 solo para el error), tipografía sans-serif y monoespaciada para los tokens, flechas claras, sin ilustraciones decorativas. Formato 16:9.

Título arriba: "Reversibilidad: ¿se puede reconstruir el texto original?".

Dos paneles lado a lado separados por una línea vertical gris.

Panel izquierdo (borde naranja), cabecera "Pre-tokenizar por espacios (estilo BERT/WordPiece)". Fila 1, caja gris "Texto original": "Hola  mundo\\n    x = 1" (con DOS espacios entre Hola y mundo, un salto de línea y 4 espacios de indentación, representados visualmente con puntos grises "·" para los espacios y "↵" para el salto: "Hola··mundo↵····x·=·1"). Flecha hacia abajo con la etiqueta "split() + descartar espacios". Fila 2, cuatro cajas de tokens: [Hola] [mundo] [x] [=] [1]. Flecha hacia abajo con etiqueta "decode: unir con 1 espacio". Fila 3, caja con borde rojo: "Hola mundo x = 1" y debajo, en rojo, "✗ pierde: espacio doble, salto de línea, indentación".

Panel derecho (borde azul), cabecera "SentencePiece (▁ = espacio visible)". Fila 1, la misma caja gris "Texto original" con los mismos puntos "·" y "↵". Flecha hacia abajo con la etiqueta "encode (normalización identidad + byte fallback)". Fila 2, cajas de tokens: [Hola] [▁▁mundo] [<0x0A>] [▁▁▁▁x] [▁=] [▁1]. Flecha hacia abajo con la etiqueta "decode: concatenar y cambiar ▁ por espacio". Fila 3, caja con borde verde: "Hola··mundo↵····x·=·1" y debajo, en verde, "✓ idéntico al original".

En la parte inferior, una barra gris con el texto: "Lossless: decode(encode(s)) = s  ·  la configuración por defecto de SentencePiece normaliza espacios y por eso NO es lossless para código".
Evita: texto ilegible, tokens inventados distintos a los indicados, flechas ambiguas, iconos decorativos, sombras, degradados.""",
    "Comparación de dos paneles: pre-tokenizar por espacios pierde espacios dobles, saltos de línea e indentación; SentencePiece con ▁ y byte fallback reconstruye el texto exacto.",
    """
 Texto:  Hola··mundo↵····x·=·1        (· = espacio, ↵ = salto de línea)

 Pre-tokenizar (BERT)                       SentencePiece (identidad + byte_fallback)
 [Hola][mundo][x][=][1]                     [Hola][▁▁mundo][<0x0A>][▁▁▁▁x][▁=][▁1]
 decode -> "Hola mundo x = 1"   ✗           decode -> "Hola  mundo\\n    x = 1"   ✓
""",
)
nb.md(r"""
> 👀 **Qué debes observar.** El panel izquierdo **no es invertible**: varios textos distintos producen los mismos tokens. En el derecho cada carácter (incluidos espacios y saltos) queda codificado, así que se reconstruye exactamente.
> Pero ojo a la nota inferior: **«SentencePiece» no implica «lossless» automáticamente**; depende de la configuración de normalización, que vamos a medir ahora.
""")

nb.code(r'''
import sentencepiece as spm

# SentencePiece lee UNA frase por línea (y descarta las de > 4192 bytes): partimos documentos en frases/líneas
SP_TXT = "sp_corpus.txt"
lineas = []
for d in train_docs:
    if d["lang"] == "code": lineas += [l for l in d["text"].split("\n") if l.strip()]
    else: lineas += [s_.strip() for s_ in re.split(r"(?<=[.!?])\s+", d["text"]) if s_.strip()]
with open(SP_TXT, "w", encoding="utf-8") as f: f.write("\n".join(l[:1000] for l in lineas))
print(len(lineas), "líneas de entrenamiento")

V_SP = 2000 if FAST_DEV_RUN else 16000
def entrena_spm(prefix: str, model_type: str = "unigram", **kw) -> "spm.SentencePieceProcessor":
    spm.SentencePieceTrainer.train(input=SP_TXT, model_prefix=prefix, vocab_size=V_SP, model_type=model_type, hard_vocab_limit=False,
                                   character_coverage=0.9995, byte_fallback=True, input_sentence_size=200000, shuffle_input_sentence=True,
                                   minloglevel=2, **kw)
    return spm.SentencePieceProcessor(model_file=prefix + ".model")

t0 = time.time()
sp_uni = entrena_spm("sp_uni", "unigram")                                  # configuración por defecto (normalización nmt_nfkc, colapsa espacios)
sp_bpe = entrena_spm("sp_bpe", "bpe")
sp_id = entrena_spm("sp_uni_id", "unigram", normalization_rule_name="identity", remove_extra_whitespaces=False,
                    add_dummy_prefix=False, allow_whitespace_only_pieces=True)   # configuración "lossless" (apta para código)
print(f"3 modelos entrenados en {time.time()-t0:.1f}s | piezas: {sp_uni.get_piece_size()} / {sp_bpe.get_piece_size()} / {sp_id.get_piece_size()}")
print("ids especiales:", {sp_uni.id_to_piece(i): i for i in range(4)}, "| primer byte-token:", sp_uni.id_to_piece(3), "..", sp_uni.id_to_piece(258))
''')

nb.code(r'''
muestras = [d["text"] for d in test_docs if d["lang"] in ("es", "code")][:40]
for nombre, sp in [("unigram (defaults)", sp_uni), ("bpe (defaults)", sp_bpe), ("unigram (identity)", sp_id)]:
    ok = sum(sp.decode(sp.encode(t)) == t for t in muestras)
    print(f"{nombre:>20}: decode(encode(t)) == t en {ok}/{len(muestras)} textos")

t = "Hola  mundo\n    x = 1 😀"
for nombre, sp in [("defaults", sp_uni), ("identity", sp_id)]:
    print(f"\n[{nombre}] {sp.encode(t, out_type=str)}\n   decode -> {sp.decode(sp.encode(t))!r}")

# Subword regularization integrada: la MISMA frase, tokenizaciones distintas
print("\nMuestreo Unigram (alpha=0.1, nbest_size=-1):")
for _ in range(3): print("  ", sp_uni.encode("la internacionalización de los parlamentos", out_type=str, enable_sampling=True, alpha=0.1, nbest_size=-1))
print("Determinista:", sp_uni.encode("la internacionalización de los parlamentos", out_type=str))
''')

nb.md(r"""
**Lo que acabas de medir**

- Con los **defaults**, SentencePiece **no** es lossless: normaliza (NFKC), colapsa espacios dobles y convierte saltos de línea en espacios. Para lenguaje natural suele ser lo deseado; para **código** destroza la indentación.
- Con `normalization_rule_name="identity"`, `remove_extra_whitespaces=False`, `allow_whitespace_only_pieces=True` y `byte_fallback=True`, el round-trip es exacto (los saltos de línea caen en tokens-byte `<0x0A>` porque casi nunca aparecieron al entrenar por líneas; en un entrenamiento serio se incluyen en el corpus).
- `byte_fallback=True` reemplaza el `<unk>` por **bytes UTF-8** (`<0xF0><0x9F>…` para un emoji): cualquier texto es representable. Es el enfoque de Llama 1/2 (Touvron et al., 2023: «fallback to bytes to decompose unknown UTF-8 characters»).
""")

# ------------------------------- 8. HF tokenizers -------------------------------
nb.md(r"""
## 8. HF `tokenizers`: la tubería de 5 etapas

Casi todo tokenizer moderno de Hugging Face (BERT, GPT-2, Llama 3, T5, Qwen…) se describe como una **tubería** de 5 etapas, implementada en Rust (`tokenizers`) y serializable en **un solo `tokenizer.json`**:

| # | Etapa | Entrada → salida | Ejemplos |
|---|---|---|---|
| 1 | **Normalizer** | `str` → `str` | `NFC`/`NFKC`, `Lowercase`, `StripAccents`, `Replace`, `BertNormalizer` |
| 2 | **Pre-tokenizer** | `str` → lista de pre-tokens con *offsets* | `Whitespace`, `Metaspace` (`▁`), `ByteLevel` (GPT-2), `Split(Regex(...))`, `Digits`, `Punctuation` |
| 3 | **Model** | pre-token → ids | `BPE`, `WordPiece`, `Unigram`, `WordLevel` |
| 4 | **Post-processor** | ids → ids con tokens especiales | `TemplateProcessing("[CLS] $A [SEP]")`, `BertProcessing`, `RobertaProcessing` |
| 5 | **Decoder** | ids → `str` | `ByteLevel`, `WordPiece(prefix="##")`, `Metaspace` |

> 💡 **Para quien viene de IR/recsys:** es el equivalente al *analyzer* de Lucene/Elasticsearch (char filters → tokenizer → token filters). Si el analyzer de indexación y el de consulta difieren, no encuentras nada; aquí, si normalizer/pre-tokenizer difieren entre entrenamiento e inferencia, el modelo ve otra cosa.
""")

nb.gemini(
    "imagen", "M03-IMG-03",
    "La tubería de 5 etapas de HF tokenizers con un ejemplo real",
    "Sigue una sola frase por las 5 etapas (normalizer, pre-tokenizer, model, post-processor, decoder), mostrando la representación intermedia en cada paso.",
    """Diagrama técnico limpio, fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif legible y monoespaciada para los textos de ejemplo, flechas claras de izquierda a derecha, sin ilustraciones decorativas. Formato 16:9.

Título arriba: "HF tokenizers: normalizer → pre-tokenizer → model → post-processor → decoder".

Cinco cajas grandes alineadas de izquierda a derecha, conectadas por flechas azules. Cada caja tiene: arriba su número y nombre; en medio una pequeña descripción; abajo una "tarjeta" con el estado del texto tras esa etapa. Frase de ejemplo (usa exactamente estos textos):

Entrada (tarjeta gris a la izquierda, antes de la caja 1): "  ¡Café CON leche!  "

Caja 1 · "Normalizer" (azul). Descripción: "str → str (NFKC, minúsculas)". Tarjeta: "  ¡café con leche!  ".
Caja 2 · "Pre-tokenizer" (naranja). Descripción: "str → pre-tokens + offsets". Tarjeta con cuatro chips: [¡] [café] [con] [leche] [!] (cinco chips, con los offsets pequeños debajo: (2,3) (3,7) (8,11) (12,17) (17,18)).
Caja 3 · "Model (WordPiece)" (verde). Descripción: "pre-token → piezas → ids". Tarjeta con chips: [¡] [café] [con] [le] [##che] [!] y debajo los ids: 12 408 57 301 88 13.
Caja 4 · "Post-processor" (gris oscuro). Descripción: "añade tokens especiales". Tarjeta: [CLS] [¡] [café] [con] [le] [##che] [!] [SEP] con ids 2 12 408 57 301 88 13 3.
Caja 5 · "Decoder" (azul). Descripción: "ids → str". Tarjeta: "¡ café con leche !" y una nota pequeña "(WordPiece pierde el espaciado original)".

Debajo de las cinco cajas, una franja gris con dos flechas curvas de vuelta hacia la izquierda: "offsets: cada token recuerda su posición en el texto ORIGINAL" y "se guarda todo en un único tokenizer.json".
Evita: texto ilegible, ids o textos distintos a los indicados, flechas que se crucen, iconos decorativos, sombras, degradados.""",
    "Cinco etapas de un tokenizer de Hugging Face (normalizer, pre-tokenizer, model, post-processor, decoder) con el estado de la frase «¡Café CON leche!» tras cada una.",
    """
 "  ¡Café CON leche!  "
   │ 1 Normalizer      -> "  ¡café con leche!  "
   │ 2 Pre-tokenizer   -> [¡][café][con][leche][!]  + offsets
   │ 3 Model WordPiece -> [¡][café][con][le][##che][!]  -> ids
   │ 4 Post-processor  -> [CLS] ... [SEP]
   ▼ 5 Decoder         -> "¡ café con leche !"
""",
)
nb.md(r"""
> 👀 **Qué debes observar.** Cada etapa es **independiente y sustituible**: puedes cambiar solo el normalizer (p. ej. quitar el `Lowercase`) sin tocar el modelo. Los *offsets* viajan con cada token hasta el texto original: gracias a eso funcionan NER, resaltado de resultados y *highlighting* en un buscador como Políglota.
""")

nb.code(r'''
# Recorremos las 5 etapas con un tokenizer WordPiece pequeño entrenado en el corpus Políglota
demo = Tokenizer(models.WordPiece(unk_token="[UNK]"))
demo.normalizer = normalizers.Sequence([normalizers.NFKC(), normalizers.Lowercase()])
demo.pre_tokenizer = pre_tokenizers.Whitespace()
demo.train_from_iterator(train_texts, trainers.WordPieceTrainer(vocab_size=3000, special_tokens=["[UNK]", "[CLS]", "[SEP]", "[PAD]"]))
demo.post_processor = processors.TemplateProcessing(single="[CLS] $A [SEP]", pair="[CLS] $A [SEP] $B:1 [SEP]:1",
                                                    special_tokens=[("[CLS]", demo.token_to_id("[CLS]")), ("[SEP]", demo.token_to_id("[SEP]"))])
demo.decoder = decoders.WordPiece(prefix="##")

texto = "  ¡Café CON leche, 3 veces!  "
norm = demo.normalizer.normalize_str(texto)
pre = demo.pre_tokenizer.pre_tokenize_str(norm)
enc = demo.encode(texto)
print("1 normalizer     :", repr(norm))
print("2 pre-tokenizer  :", pre)
print("3 model + 4 post :", list(zip(enc.tokens, enc.ids)))
print("   offsets (texto ORIGINAL):", enc.offsets)
print("5 decoder        :", repr(demo.decode(enc.ids)), "  <- el espaciado original NO se recupera")
print("   serializable en un solo archivo:", len(demo.to_str()), "caracteres de JSON")
''')

nb.md(r"""
### 8.1 Entrenar las tres familias con **la misma tubería**

Para que la comparación sea justa (¡solo cambia el algoritmo!) usamos el mismo normalizer (NFKC) y el mismo pre-tokenizer (`Metaspace` + puntuación aislada, a la SentencePiece) y variamos el `Model` + `Trainer`.
Medimos en el **test** por idioma: **fertilidad** (tokens por palabra), **bytes por token** (cuánto texto cubre cada token) y **tasa de `[UNK]`**.
""")

nb.code(r'''
def construye_hf(tipo: str, vocab_size: int) -> Tokenizer:
    """BPE | WordPiece | Unigram con idéntica normalización y pre-tokenización (solo cambia el algoritmo)."""
    pre = pre_tokenizers.Sequence([pre_tokenizers.Metaspace(replacement="▁", prepend_scheme="always"), pre_tokenizers.Punctuation(behavior="isolated")])
    if tipo == "bpe":
        tok, tr = Tokenizer(models.BPE(unk_token="[UNK]")), trainers.BpeTrainer(vocab_size=vocab_size, special_tokens=["[UNK]"])
    elif tipo == "wordpiece":
        tok, tr = Tokenizer(models.WordPiece(unk_token="[UNK]")), trainers.WordPieceTrainer(vocab_size=vocab_size, special_tokens=["[UNK]"], continuing_subword_prefix="##")
    else:
        tok, tr = Tokenizer(models.Unigram()), trainers.UnigramTrainer(vocab_size=vocab_size, special_tokens=["[UNK]"], unk_token="[UNK]")
    tok.normalizer = normalizers.NFKC(); tok.pre_tokenizer = pre
    tok.train_from_iterator(train_texts, tr)
    return tok

TAMANOS = [1000, 4000] if FAST_DEV_RUN else [4000, 16000, 32000]
hf_tok, filas = {}, []
for tipo in ["bpe", "wordpiece", "unigram"]:
    for vs in TAMANOS:
        t0 = time.time(); tok = construye_hf(tipo, vs); hf_tok[(tipo, vs)] = tok
        for lang in ["es", "en", "code"]:
            m = metricas_tokenizacion(lambda s: tok.encode(s).tokens, test_by_lang[lang])
            filas.append({"algoritmo": tipo, "vocab": vs, "idioma": lang, **m, "seg_entrenar": time.time() - t0})
import pandas as pd
df = pd.DataFrame(filas)
print(df.pivot_table(index=["algoritmo", "vocab"], columns="idioma", values="fertilidad").round(3))
print()
print(df.pivot_table(index=["algoritmo", "vocab"], columns="idioma", values="bytes_por_token").round(2))
''')

nb.code(r'''
# ¿El WordPieceTrainer de HF entrena "por verosimilitud"? Comparamos su vocabulario con el de BpeTrainer (mismo tamaño, mismos datos)
vs = TAMANOS[-1]
v_bpe = set(hf_tok[("bpe", vs)].get_vocab())
v_wp = {t[2:] if t.startswith("##") else t for t in hf_tok[("wordpiece", vs)].get_vocab()}
v_uni = set(hf_tok[("unigram", vs)].get_vocab())
jac = lambda a, b: len(a & b) / len(a | b)
print(f"Jaccard vocab  WordPiece(sin ##) vs BPE: {jac(v_wp, v_bpe):.2f}  |  Unigram vs BPE: {jac(v_uni, v_bpe):.2f}  |  Unigram vs WordPiece: {jac(v_uni, v_wp):.2f}")

# Tasa de [UNK] en texto del test y en un "estrés": escrituras y emojis que el corpus casi no contiene.
# OJO: HF Unigram devuelve el trozo desconocido con su TEXTO original pero con id = unk; por eso contamos por id, no por cadena "[UNK]".
estres = ["Привет, мир", "你好，世界", "مرحبا بالعالم", "नमस्ते दुनिया", "😀🚀 ¡hola!", "naïve café Ünïcödé"]
def n_unk(tok, texto): return tok.encode(texto).ids.count(tok.token_to_id("[UNK]"))
for tipo in ["bpe", "wordpiece", "unigram"]:
    tok = hf_tok[(tipo, vs)]
    unk_test = sum(n_unk(tok, t) for ts in test_by_lang.values() for t in ts)
    print(f"{tipo:>10}: [UNK] en el test = {unk_test:3d} | estrés ->", [n_unk(tok, t) for t in estres], "(nº de [UNK] por cadena de estrés)")
for tipo in ["wordpiece", "bpe", "unigram"]:
    e = hf_tok[(tipo, vs)].encode("hola 😀 mundo"); print(f"{tipo:>10}: {e.tokens}  ids unk: {[i for i in e.ids if i == 0]}")
''')

nb.md(r"""
**Lo que acabas de medir (y que debes poder explicar)**

- **`WordPieceTrainer` ≈ `BpeTrainer`.** El Jaccard entre los vocabularios (quitando `##`) es altísimo: en HF `tokenizers`, entrenar «WordPiece» es esencialmente BPE con prefijo `##` + inferencia *longest-match-first*. Lo que distingue a la implementación de HF de BPE es la **inferencia** y el `[UNK]` por palabra completa, no el criterio de fusión.
- **Unigram es otra bestia**: su vocabulario solo coincide parcialmente con el de BPE, porque se obtiene podando, no fusionando.
- **`[UNK]` y escrituras no vistas.** BPE sin bytes produce un `[UNK]` **por carácter** desconocido, WordPiece uno **por palabra** (descarta toda la palabra), y Unigram un `[UNK]` por tramo desconocido. Los tres *pierden información* al encontrar algo que no entrenaron. La solución industrial es el nivel de bytes (GPT-2, tiktoken) o `byte_fallback` (SentencePiece/Llama) que ya viste.
""")

nb.code(r'''
fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
vs = TAMANOS[-1]
sub = df[df["vocab"] == vs]
w = 0.26
for k, (tipo, c_) in enumerate(zip(["bpe", "wordpiece", "unigram"], [COL["azul"], COL["naranja"], COL["verde"]])):
    vals = [sub[(sub.algoritmo == tipo) & (sub.idioma == l)]["fertilidad"].iloc[0] for l in ["es", "en", "code"]]
    ax[0].bar(np.arange(3) + (k - 1) * w, vals, w, label=tipo, color=c_)
ax[0].set_xticks(range(3)); ax[0].set_xticklabels(["español", "inglés", "código"]); ax[0].set_ylabel("Fertilidad (tokens / palabra)"); ax[0].set_title(f"Fertilidad por idioma (|V|={vs})"); ax[0].legend()
for tipo, c_ in zip(["bpe", "wordpiece", "unigram"], [COL["azul"], COL["naranja"], COL["verde"]]):
    s_ = df[(df.algoritmo == tipo) & (df.idioma == "es")].sort_values("vocab")
    ax[1].plot(s_["vocab"], s_["fertilidad"], "o-", label=tipo, color=c_, lw=2)
ax[1].set_xscale("log"); ax[1].set_xlabel("Tamaño del vocabulario"); ax[1].set_ylabel("Fertilidad en español"); ax[1].set_title("Más vocabulario → menos tokens (rendimientos decrecientes)"); ax[1].legend()
# Zipf de uso de tokens sobre el test en español
for tipo, c_ in zip(["bpe", "wordpiece", "unigram"], [COL["azul"], COL["naranja"], COL["verde"]]):
    cnt = Counter(t for s_ in test_by_lang["es"] for t in hf_tok[(tipo, vs)].encode(s_).tokens)
    fr = np.array(sorted(cnt.values(), reverse=True)); ax[2].loglog(np.arange(1, len(fr) + 1), fr, label=f"{tipo} ({len(fr)} tokens usados)", color=c_)
ax[2].set_xlabel("Rango del token"); ax[2].set_ylabel("Frecuencia en el test (ES)"); ax[2].set_title("Uso de tokens: ley de Zipf"); ax[2].legend()
plt.tight_layout(); plt.show()
''')

nb.md(r"""
> 👀 **Qué debes observar.**
> **(1)** Para el mismo tamaño de vocabulario BPE/WordPiece obtienen **menor fertilidad** que Unigram (comprimen más); el **código** es el que más tokens por «palabra» necesita (palabras = identificadores + símbolos).
> **(2)** Subir el vocabulario reduce la fertilidad con **rendimientos decrecientes** (curva casi plana al final): aquí nace el trade-off del módulo 04 (más vocabulario = embeddings más grandes y tokens raros sub-entrenados).
> **(3)** Zipf: unos pocos tokens concentran casi todo el uso y una cola larga aparece muy pocas veces; esa cola es la candidata a *under-trained tokens* (módulo 05). Unigram suele usar **más tipos distintos** (cola más larga) con la misma tabla.
> ⚠️ Menor fertilidad **no** significa mejor modelo: Schmidt et al. (2024) muestran que más compresión no se traduce de forma fiable en mejor rendimiento posterior.
""")

nb.md(r"""
### 8.2 ¿Qué algoritmo respeta mejor la morfología?

Bostrom & Durrett (2020) encontraron que Unigram produce subpalabras **más alineadas con la morfología** que BPE y que los modelos preentrenados con Unigram igualan o superan a BPE en inglés y japonés.
Vamos a medirlo con un mini **gold standard** escrito a mano (30 palabras ES + 30 EN con sus morfemas): puntuamos la **F1 de fronteras** entre las piezas del tokenizer y las fronteras morfológicas.
Es una prueba pequeña y con juicio humano (las fronteras morfológicas admiten discusión): úsala como diagnóstico, no como veredicto.
""")

nb.code(r'''
MORF_ES = ["re|construc|ción", "des|confian|za", "im|pens|able", "trabaj|ador|es", "feliz|mente", "organiza|ciones", "publica|ción", "il|legal|mente",
           "descubri|miento", "pensa|miento", "agrupa|ción", "comunica|ción", "in|felic|idad", "des|hacer", "pre|histór|ico", "sub|desarrollo",
           "co|opera|ción", "automática|mente", "ir|reversible", "re|ubic|ar", "des|organiza|ción", "hermosa|mente", "re|comenda|ciones",
           "inter|nacional|es", "actualiza|ción", "indepen|diente|mente", "multi|lingüe", "pos|guerra", "sobre|ajuste", "ejecuta|ble"]
MORF_EN = ["un|believ|able", "re|construct|ion", "inter|national|iz|ation", "happi|ness", "un|happi|ly", "dis|agree|ment", "mis|understand|ing",
           "pre|process|ing", "re|us|able", "nation|al|ism", "effect|ive|ly", "token|iz|ation", "re|writ|ing", "non|linear", "sub|word",
           "multi|lingual", "over|fit|ting", "under|estimate", "counter|example", "teach|er|s", "re|commend|ation|s", "quick|ly",
           "in|depend|ent|ly", "un|control|led", "de|code", "en|code", "pre|train|ing", "fine|tun|ing", "dis|connect|ed", "work|ing|s"]

def fronteras(partes):
    pos, acc = set(), 0
    for p in partes[:-1]: acc += len(p); pos.add(acc)
    return pos

def f1_morfologico(segmenta, gold: list) -> dict:
    """segmenta: palabra -> lista de piezas. F1 micro de fronteras internas frente al gold."""
    tp = fp = fn = 0
    for g in gold:
        gold_p = g.split("|"); palabra = "".join(gold_p)
        pred = [p.replace("▁", "").replace("##", "") for p in segmenta(palabra)]
        pred = [p for p in pred if p]
        if "".join(pred) != palabra: pred = [palabra]            # [UNK] u otra pérdida: sin fronteras
        a, b = fronteras(pred), fronteras(gold_p)
        tp += len(a & b); fp += len(a - b); fn += len(b - a)
    p = tp / max(tp + fp, 1); r = tp / max(tp + fn, 1)
    return {"precision": p, "recall": r, "f1": 2 * p * r / max(p + r, 1e-9)}

filas_m = []
for tipo in ["bpe", "wordpiece", "unigram"]:
    tok = hf_tok[(tipo, vs)]
    for nombre, gold in [("es", MORF_ES), ("en", MORF_EN)]:
        filas_m.append({"tokenizer": f"hf-{tipo}", "idioma": nombre, **f1_morfologico(lambda w: tok.encode(w).tokens, gold)})
for nombre_sp, sp in [("spm-unigram", sp_uni), ("spm-bpe", sp_bpe)]:
    for nombre, gold in [("es", MORF_ES), ("en", MORF_EN)]:
        filas_m.append({"tokenizer": nombre_sp, "idioma": nombre, **f1_morfologico(lambda w: sp.encode(w, out_type=str), gold)})
dm = pd.DataFrame(filas_m)
print(dm.pivot_table(index="tokenizer", columns="idioma", values="f1").round(3))
print(f"(vocabulario HF = {vs}; SentencePiece = {V_SP})")
''')

nb.code(r'''
# Heatmap: ¿cuánto coinciden las fronteras de segmentación de los distintos tokenizers en palabras del test?
def fronteras_de(segmenta, palabra):
    pred = [p.replace("▁", "").replace("##", "") for p in segmenta(palabra)]
    return fronteras([p for p in pred if p])

pal_test = list(dict.fromkeys(w for w in test_words if len(w) >= 5))[:800]
segs = {f"hf-{t}": (lambda w, tok=hf_tok[(t, vs)]: tok.encode(w).tokens) for t in ["bpe", "wordpiece", "unigram"]}
segs["spm-unigram"] = lambda w: sp_uni.encode(w, out_type=str)
segs["spm-bpe"] = lambda w: sp_bpe.encode(w, out_type=str)
nombres = list(segs); B = {n: [fronteras_de(segs[n], w) for w in pal_test] for n in nombres}
M = np.zeros((len(nombres), len(nombres)))
for i, a in enumerate(nombres):
    for j, b in enumerate(nombres):
        inter = sum(len(x & y) for x, y in zip(B[a], B[b])); union = sum(len(x | y) for x, y in zip(B[a], B[b]))
        M[i, j] = inter / max(union, 1)
fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.4))
im = ax[0].imshow(M, cmap="Blues", vmin=0, vmax=1); ax[0].set_xticks(range(len(nombres))); ax[0].set_yticks(range(len(nombres)))
ax[0].set_xticklabels(nombres, rotation=35, ha="right"); ax[0].set_yticklabels(nombres); ax[0].grid(False)
for i in range(len(nombres)):
    for j in range(len(nombres)): ax[0].text(j, i, f"{M[i,j]:.2f}", ha="center", va="center", color="white" if M[i, j] > 0.55 else "black", fontsize=9)
ax[0].set_title("Acuerdo de fronteras (Jaccard) en palabras no vistas"); plt.colorbar(im, ax=ax[0], fraction=0.046)
piv = dm.pivot_table(index="tokenizer", columns="idioma", values="f1").reindex(nombres)
piv.plot.bar(ax=ax[1], color=[COL["naranja"], COL["azul"]], rot=30); ax[1].set_ylabel("F1 de fronteras morfológicas"); ax[1].set_title("Alineación morfológica (mini gold, n=30 por idioma)"); ax[1].legend(title="idioma")
plt.tight_layout(); plt.show()
''')

nb.md(r"""
> 👀 **Qué debes observar.**
> **Izquierda:** los tokenizers basados en fusiones (HF-BPE, SentencePiece-BPE, HF-WordPiece) coinciden entre sí bastante más (≈ 0.4–0.6) que con el Unigram de HF (≈ 0.2): **Unigram parte las palabras en otros sitios**. (SentencePiece usa aquí |V| = 2000 y HF 4000: parte de las diferencias es de tamaño, no de algoritmo; en el proyecto lo controlarás.)
> **Derecha:** en esta corrida (corpus espejo, `FAST_DEV_RUN`) el **Unigram de HF obtiene la mayor F1 morfológica en ambos idiomas** y SentencePiece-Unigram supera a su equivalente BPE en ambos, en línea con Bostrom & Durrett (2020).
> Pero la prueba es pequeña (30 palabras por idioma) y el corpus de entrenamiento diminuto: no extrapoles magnitudes. Lo robusto: **el algoritmo cambia dónde caen las fronteras, no solo cuántos tokens salen**.
""")

nb.md(r"""
### 8.3 El normalizer decide qué distinciones existen

Un normalizer mal elegido destruye información **antes** de que el algoritmo vea nada. El caso clásico para español: `BertNormalizer(lowercase=True, strip_accents=True)` (el de los modelos BERT *uncased*) convierte `está`→`esta`, `sí`→`si`, `él`→`el`, `año`→`ano`.
Medimos cuántas palabras *distintas* del corpus colapsan en la misma cadena.
""")

nb.code(r'''
sin_tildes = normalizers.BertNormalizer(clean_text=True, handle_chinese_chars=True, strip_accents=True, lowercase=True)
nfkc = normalizers.NFKC()
colisiones = collections.defaultdict(set)
for w in ws:                                      # ws: palabras del español de entrenamiento (ya en minúsculas)
    colisiones[sin_tildes.normalize_str(w)].add(w)
colis = {k: v for k, v in colisiones.items() if len(v) > 1}
n_tipos = sum(len(v) for v in colis.values())
print(f"{len(ws)} tipos de palabra | {len(colis)} grupos colisionan tras quitar tildes (afectan a {n_tipos} tipos = {n_tipos/len(ws):.1%})")
print("Ejemplos:", [sorted(v) for v in list(colis.values())[:6]])
frases = ["El año pasado él dijo que sí.", "Si lo sé, te lo digo: ¿cómo estás?"]
for fr in frases: print(f"  {fr!r}\n    BERT-uncased: {sin_tildes.normalize_str(fr)!r}\n    NFKC        : {nfkc.normalize_str(fr)!r}")
''')

# ------------------------------- 9. tiktoken -------------------------------
nb.md(r"""
## 9. `tiktoken` y su relación con tu BPE del módulo 02

`tiktoken` es el tokenizer de OpenAI (código abierto, núcleo en Rust): **solo codifica/decodifica**, no entrena. Un `Encoding` son tres cosas:

1. `pat_str`: la **regex de pre-tokenización** (la que estudiaste en el módulo 02),
2. `mergeable_ranks`: un diccionario `bytes → rank` (el *rank* es el id del token **y** la prioridad de fusión: como los tokens se crean en orden de merge, no hace falta una lista de merges aparte),
3. `special_tokens`: p. ej. `<|endoftext|>`.

Algoritmo: regex → por cada pre-token, si está entero en `mergeable_ranks` se emite; si no, se parte en bytes y se fusiona repetidamente el par adyacente cuya concatenación tenga **menor rank**. Es exactamente el BPE de byte-level que implementaste, solo que el orden de merges está implícito en el rank.
""")

nb.code(r'''
import tiktoken
TIK = {}
for nombre in ["r50k_base", "cl100k_base", "o200k_base"]:
    try:
        TIK[nombre] = tiktoken.get_encoding(nombre)          # descarga el vocabulario la 1ª vez (necesita acceso a openaipublic.blob.core.windows.net)
    except Exception as e:
        print(f"   (no pude cargar {nombre}: {type(e).__name__}. Si estás tras un proxy, descarga el .tiktoken y usa TIKTOKEN_CACHE_DIR)")
print("encodings disponibles en la librería:", tiktoken.list_encoding_names())
for n, e in TIK.items():
    print(f"{n:>12}: n_vocab = {e.n_vocab:>7,} | tokens especiales: {sorted(e.special_tokens_set)[:3]}...")
if TIK:
    print("\ncl100k pat_str :", TIK["cl100k_base"]._pat_str)
    print("o200k  pat_str :", TIK["o200k_base"]._pat_str[:150], "...")
    print("\nmodelo -> encoding:", {m: tiktoken.encoding_for_model(m).name for m in ["gpt-4", "gpt-4o"]})
    e = TIK["cl100k_base"]; t = "Hola, ¿cómo estás? def f(x): return x**2"
    ids = e.encode(t); print(len(ids), "tokens:", [e.decode_single_token_bytes(i) for i in ids])
''')

nb.code(r'''
import regex   # el módulo `regex` (no `re`): soporta \p{L} y cuantificadores posesivos como en tiktoken

def bpe_pieza(pieza: bytes, ranks: dict, dropout: float = 0.0, rng=random) -> list:
    """BPE de tiktoken en ~12 líneas: fusiona el par adyacente de MENOR rank hasta que no queden pares en el vocabulario.
    dropout>0 -> BPE-dropout: cada candidato de merge se ignora con probabilidad `dropout` en cada paso."""
    if dropout == 0 and pieza in ranks: return [pieza]          # atajo (con dropout hay que partir también las palabras que son 1 token)
    partes = [bytes([b]) for b in pieza]
    while len(partes) > 1:
        cand = [(ranks[partes[i] + partes[i + 1]], i) for i in range(len(partes) - 1) if partes[i] + partes[i + 1] in ranks]
        if dropout > 0: cand = [c for c in cand if rng.random() >= dropout]
        if not cand: break
        _, i = min(cand); partes[i:i + 2] = [partes[i] + partes[i + 1]]
    return partes

def encode_mini(texto: str, enc, dropout: float = 0.0, rng=random) -> list:
    """Equivalente a enc.encode_ordinary(texto) (sin tokens especiales), devolviendo los ids."""
    pat = regex.compile(enc._pat_str); ranks = enc._mergeable_ranks
    return [ranks[p] for pre in pat.findall(texto) for p in bpe_pieza(pre.encode("utf-8"), ranks, dropout, rng)]

if TIK:
    e = TIK["cl100k_base"]
    todos = [t for ts in test_by_lang.values() for t in ts]
    iguales = sum(encode_mini(t, e) == e.encode_ordinary(t) for t in todos)
    print(f"mi BPE de 12 líneas == tiktoken.encode_ordinary en {iguales}/{len(todos)} textos de test (ES/EN/código)")
else:
    print("tiktoken no disponible en este entorno: salta las celdas siguientes de la sección 9 o configura la caché.")
''')

nb.md(r"""
### 9.1 BPE-dropout y subword regularization con tu propio BPE

Ahora que tienes `bpe_pieza(..., dropout=p)`, probemos **BPE-dropout** (Provilkov et al., 2020): en cada paso, cada merge candidato se ignora con probabilidad $p$, así que la misma palabra se segmenta de forma distinta cada vez
(y con $p=0$ recuperas BPE estándar; con $p=1$, bytes). Medimos cuánto se fragmenta el texto y cuántas segmentaciones distintas aparecen.
""")

nb.code(r'''
if TIK:
    e = TIK["cl100k_base"]; ranks = e._mergeable_ranks; r = random.Random(SEED)
    palabras_es = [" " + w for w in test_words[:300]]
    ps = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5]
    toks_por_palabra = [np.mean([len(bpe_pieza(w.encode(), ranks, p, r)) for w in palabras_es]) for p in ps]
    ejemplo = " internacionalización"
    distintas = [len({tuple(bpe_pieza(ejemplo.encode(), ranks, p, r)) for _ in range(300)}) for p in ps]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].plot(ps, toks_por_palabra, "o-", c=COL["azul"], lw=2); ax[0].set_xlabel("Probabilidad de dropout p"); ax[0].set_ylabel("Tokens por palabra (ES, cl100k)"); ax[0].set_title("BPE-dropout fragmenta el texto")
    ax[1].plot(ps, distintas, "o-", c=COL["naranja"], lw=2); ax[1].set_xlabel("Probabilidad de dropout p"); ax[1].set_ylabel("Segmentaciones distintas (300 muestras)"); ax[1].set_title(f"Diversidad para «{ejemplo.strip()}»")
    plt.tight_layout(); plt.show()
    for p in [0.0, 0.1, 0.3]: print(f"p={p}:", [bytes(x).decode("utf-8", "replace") for x in bpe_pieza(ejemplo.encode(), ranks, p, r)])
''')

nb.md(r"""
> 👀 **Qué debes observar.** Con $p=0$ la segmentación es única. En nuestra corrida, con $p=0.1$ ya aparecen ≈ 8 segmentaciones distintas de una palabra larga y la fragmentación solo sube de ≈ 1.4 a ≈ 1.6 tokens/palabra: ese es el rango útil para regularizar.
> Con $p=0.5$ el texto casi duplica su número de tokens (≈ 2.9) y salen ≈ 90 segmentaciones: se rompe hacia bytes. Chai et al. (2024) reportan que los LLM siguen siendo frágiles a typos y cambios de formato derivados de la tokenización y que técnicas como BPE-dropout ayudan; **a gran escala casi nadie lo usa en el pretraining** (🟡): complica la reproducibilidad y el beneficio frente a datos masivos es incierto.
""")

nb.md(r"""
### 9.2 Del tokenizer HF a `tiktoken` (y vuelta)

Un tokenizer **byte-level BPE** entrenado con HF `tokenizers` (regex + `ByteLevel`) puede **exportarse a un `tiktoken.Encoding`** porque ambos son el mismo objeto matemático: unos `mergeable_ranks` y una regex.
Solo hay que deshacer el alfabeto «visible» de GPT-2 (`bytes_to_unicode`) y renumerar los ranks (bytes sueltos primero, luego los merges en orden de id). Verificamos **igualdad exacta**.
""")

nb.code(r'''
from tokenizers import Regex
from tokenizers.pre_tokenizers import ByteLevel

PAT_GPT2 = r"""'(?:[sdmt]|ll|ve|re)| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""
bl = Tokenizer(models.BPE())
bl.pre_tokenizer = pre_tokenizers.Sequence([pre_tokenizers.Split(Regex(PAT_GPT2), behavior="isolated"), ByteLevel(add_prefix_space=False, use_regex=False)])
bl.decoder = decoders.ByteLevel()
bl.train_from_iterator(train_texts, trainers.BpeTrainer(vocab_size=TAMANOS[-1], initial_alphabet=ByteLevel.alphabet(), special_tokens=["<|endoftext|>"]))

def bytes_a_unicode() -> dict:
    """Tabla de GPT-2: cada byte 0-255 -> un carácter Unicode imprimible."""
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
    cs, n = bs[:], 0
    for b in range(256):
        if b not in bs: bs.append(b); cs.append(256 + n); n += 1
    return dict(zip(bs, map(chr, cs)))

def hf_a_tiktoken(tok: Tokenizer, pat: str, nombre: str = "poliglota_demo"):
    u2b = {v: k for k, v in bytes_a_unicode().items()}
    piezas = sorted((i, bytes(u2b[ch] for ch in t)) for t, i in tok.get_vocab().items() if t != "<|endoftext|>")
    ranks = {bytes([i]): i for i in range(256)}                         # bytes sueltos: ranks 0..255
    for _, b in piezas:
        if len(b) > 1: ranks[b] = len(ranks)                             # merges en orden de id (= orden de fusión)
    return tiktoken.Encoding(name=nombre, pat_str=pat, mergeable_ranks=ranks, special_tokens={"<|endoftext|>": len(ranks)})

mi_enc = hf_a_tiktoken(bl, PAT_GPT2)
u2b = {v: k for k, v in bytes_a_unicode().items()}
difieren = 0
for t in [t for ts in test_by_lang.values() for t in ts] + ["Año nuevo: ¿qué tal? 😀 def f(x):\n    return x"]:
    a = [bytes(u2b[ch] for ch in x) for x in bl.encode(t).tokens]
    b = [mi_enc.decode_single_token_bytes(i) for i in mi_enc.encode_ordinary(t)]
    difieren += a != b
print(f"tokenizer HF exportado a tiktoken: n_vocab = {mi_enc.n_vocab} | textos con tokenización distinta: {difieren}")
print("round-trip:", mi_enc.decode(mi_enc.encode_ordinary("Año nuevo 😀")))
''')

nb.md(r"""
> 🧠 **Por qué importa.** Con este puente puedes entrenar **tu** vocabulario con las herramientas de HF y servirlo con `tiktoken` (rápido, sin dependencias pesadas), o al revés. Es también la base para auditar tokenizers de terceros: todo `tokenizer.json` byte-level cabe en este molde.
""")

nb.code(r'''
if TIK:
    filas_t = []
    for nombre, enc_fn in [("tiktoken r50k (GPT-2/3)", lambda t: TIK["r50k_base"].encode_ordinary(t)), ("tiktoken cl100k (GPT-4)", lambda t: TIK["cl100k_base"].encode_ordinary(t)),
                           ("tiktoken o200k (GPT-4o)", lambda t: TIK["o200k_base"].encode_ordinary(t)), (f"nuestro BPE-bytes ({mi_enc.n_vocab})", lambda t: mi_enc.encode_ordinary(t)),
                           (f"SentencePiece unigram ({V_SP})", lambda t: sp_uni.encode(t))]:
        for lang in ["es", "en", "code"]:
            filas_t.append({"tokenizer": nombre, "idioma": lang, **metricas_tokenizacion(enc_fn, test_by_lang[lang])})
    dt = pd.DataFrame(filas_t)
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.3))
    for a_, metrica, tit in [(ax[0], "fertilidad", "Fertilidad (tokens por palabra, menor = mejor)"), (ax[1], "bytes_por_token", "Bytes por token (mayor = mejor)")]:
        piv = dt.pivot_table(index="idioma", columns="tokenizer", values=metrica).loc[["es", "en", "code"]]
        piv.plot.bar(ax=a_, rot=0, color=[COL["gris"], COL["azul"], COL["verde"], COL["naranja"], COL["rojo"]]); a_.set_title(tit); a_.set_xlabel("")
        a_.legend(fontsize=7)
    plt.tight_layout(); plt.show()
    print(dt.pivot_table(index="tokenizer", columns="idioma", values="bytes_por_token").round(2))
''')

nb.md(r"""
> 👀 **Qué debes observar** (cifras de nuestra corrida sobre el corpus espejo; las tuyas cambiarán con Wikipedia).
> **(1)** `cl100k` y `o200k` necesitan menos tokens que nuestro BPE de 4 000 piezas en los tres dominios, pero **`r50k` (GPT-2/3) es peor que el nuestro en español y en código**: su vocabulario, entrenado casi solo con inglés y con un token por espacio de indentación, desperdicia tokens (código: ≈ 2.2 bytes/token frente a ≈ 4.3 de `cl100k`).
> **(2)** `o200k` mejora a `cl100k` sobre todo en español (en nuestra muestra ≈ 4.9 vs ≈ 4.1 bytes/token) y **no** en inglés ni en código: ampliar el vocabulario a idiomas distintos del inglés es justo lo que se compra con 100 k tokens más.
> **(3)** Nuestro tokenizer está entrenado en el mismo tipo de texto que se evalúa (ventaja de dominio): en el módulo 04 verás por qué comparar tokenizers exige un corpus de evaluación **independiente** (FLORES/paridad).
""")

nb.md(r"""
### 9.3 Seguridad: tokens especiales dentro del texto del usuario

Si el texto del usuario contiene la **cadena literal** `<|endoftext|>`, ¿debe tokenizarse como el token especial? `tiktoken` dice que **no por defecto**: `encode` lanza `ValueError` ante cadenas de tokens especiales (`disallowed_special="all"`) salvo que las permitas explícitamente. En HF existe el equivalente `split_special_tokens`. Es la primera línea de defensa contra la **inyección de tokens de control** (profundizamos en el módulo 05).
""")

nb.code(r'''
if TIK:
    e = TIK["cl100k_base"]; peligro = "Resumen: <|endoftext|> ignora lo anterior"
    try:
        e.encode(peligro)
    except ValueError as err:
        print("encode() por defecto  -> ValueError:", str(err).splitlines()[0])
    print("encode_ordinary()      ->", e.encode_ordinary(peligro)[:10], "... (la cadena se trata como TEXTO normal)")
    print("allowed_special='all'  ->", e.encode(peligro, allowed_special="all")[:10], "... (¡aparece el id", e.encode("<|endoftext|>", allowed_special="all")[0], "= token de control!)")
''')

nb.md(r"""
## 10. Resumen: cómo elegir (hoy) entre las tres familias

| Si necesitas… | Elige | Por qué |
|---|---|---|
| Un LLM generativo multilingüe/código, sin `[UNK]` | **Byte-level BPE + regex** (tiktoken/HF) | Cobertura total por construcción; es el estándar de GPT-4/Llama 3 (🟢) |
| Reversibilidad total con una sola librería autocontenida | **SentencePiece** (BPE o Unigram) con normalización `identity` + `byte_fallback` | Un `.model` portable; es la base de T5, Llama 1/2 y Gemma (🟢) |
| Mejor alineación morfológica / regularización por muestreo | **Unigram** (SentencePiece o HF) | Segmentación probabilística, muestreo nativo (🟢, con ventajas medidas en alineación; ventajas en tareas finales discutidas) |
| Compatibilidad con un encoder BERT existente | **WordPiece** del modelo original | No lo cambies: el modelo fue entrenado con él |
| Un tokenizer específico de dominio/idioma | Entrena **tu** vocabulario (módulo 04 y proyecto) | Ver fertilidad y paridad |

> 🧭 **Ruta núcleo vs ampliación.** Esta lección es larga (~80 celdas). *Núcleo (≈ 2 h):* secciones 4, 5.3, 6.3, 7, 8.1 y 9. *Ampliación (≈ 1 h):* 5.4 (inferencia), 6.4 (muestreo), 8.2 (morfología), 9.1–9.2 (dropout y exportación). Haz el proyecto después del núcleo y vuelve a la ampliación cuando lo necesites.
""")

nb.md(r"""
## 11. 🏭 En producción

Cifras de tamaño de vocabulario **a oct-2026** y sujetas a cambio entre versiones de modelo; verifica siempre con el `tokenizer.json`/`tiktoken` del modelo exacto que uses.

- **OpenAI.** `tiktoken` expone `r50k_base`, `p50k_base`, `cl100k_base` (GPT-3.5/GPT-4) y `o200k_base` (GPT-4o); medimos arriba `n_vocab` = 100 277 y 200 019 (incluyen tokens especiales). Todo es byte-level BPE + regex. Fuente: repositorio de `tiktoken` (MIT) y `tiktoken.encoding_for_model`.
- **Meta.** Llama 1/2 usan BPE vía SentencePiece con dígitos separados y *byte fallback* (Touvron et al. 2023; Llama 2 tiene 32 000 piezas según el análisis de Land & Bartolo 2024). **Llama 3 cambió a un vocabulario de 128 K** construido a partir de los 100 K tokens de tiktoken más 28 K para idiomas no ingleses; sobre una muestra de inglés la compresión mejoró de 3.17 a 3.94 caracteres por token (Llama 3 herd of models, 2024).
- **Google.** BERT: WordPiece de 30 000 (Devlin et al. 2018). T5: SentencePiece de 32 000 *wordpieces*, entrenado con una mezcla 10:1:1:1 de inglés:alemán:francés:rumano (Raffel et al. 2019). Gemma 3: SentencePiece con dígitos separados, espacios preservados y codificación a nivel de byte; el informe da ≈ 262 k entradas en el texto y 256 k en un pie de tabla (inconsistencia del propio informe).
- **Mistral.** Los tokenizers v1–v2 son SentencePiece; **Tekken** (desde Mistral NeMo) es BPE basado en tiktoken, entrenado con más de 100 idiomas, con ≈ 130 k piezas + ≈ 1 k tokens de control, y Mistral reporta mejor compresión que el SentencePiece anterior (≈ 30 % en código y varios idiomas) según su guía de tokenización.
- **Hugging Face.** `tokenizers` (Rust) es el motor detrás de `AutoTokenizer`; un `tokenizer.json` serializa las 5 etapas. Song et al. (2021) propusieron un WordPiece de tiempo lineal.
- **Trade-offs de escala.** Entrenar un SentencePiece Unigram con 1 M de subcadenas semilla sobre decenas de GB es costoso en memoria; por eso se muestrea (`input_sentence_size`, `shuffle_input_sentence`) y se pondera por idioma. Entrenar BPE/WordPiece con HF es mucho más rápido que Unigram (lo viste en los tiempos).
""")

nb.md(r"""
## 12. 🧠 Secretos de la élite

1. **«WordPiece» en HF no es WordPiece-por-verosimilitud.** Medimos Jaccard ≈ 0.9 entre el vocabulario de `WordPieceTrainer` y el de `BpeTrainer`: la diferencia práctica está en la **inferencia** (*longest-match-first*) y en que un carácter desconocido manda **toda la palabra** a `[UNK]`. El vocabulario original de BERT lo entrenó código interno de Google no publicado.
2. **El pre-tokenizador pesa más que el algoritmo.** Schmidt et al. (2024) concluyen que la pre-tokenización y la inicialización del vocabulario con BPE importan más que minimizar el nº de tokens; Dagan et al. (2024) muestran que tamaño, regex y datos del tokenizer cambian velocidad, contexto efectivo y rendimiento en código. Compara algoritmos **con la misma tubería** (como hicimos).
3. **Menos tokens ≠ mejor modelo, pero tampoco es irrelevante.** Goldman et al. (2024) encuentran correlación entre compresión y rendimiento (más fuerte en generación y modelos pequeños); Schmidt et al. (2024) muestran que PathPiece, que minimiza tokens, no gana. Usa la compresión como *restricción de coste*, no como objetivo.
4. **La inferencia voraz suele bastar.** Uzan et al. (2024) comparan siete métodos de inferencia sobre cuatro tokenizers: la decodificación simple (voraz) funciona sorprendentemente bien, así que no pierdas semanas optimizando el segmentador antes que el vocabulario.
5. **SentencePiece descarta en silencio las líneas de más de `max_sentence_length` (4192 bytes por defecto)** y su normalización por defecto (`nmt_nfkc` + colapso de espacios) **no es lossless**: en nuestra medición, 29/40 vs 40/40 textos recuperados exactamente con `identity`. Para código, desactiva el colapso de espacios.
6. **Cuenta los `[UNK]` por id, no por cadena.** HF Unigram devuelve el tramo desconocido con su texto original pero con el id de `[UNK]`; contar `"[UNK]"` en `tokens` da 0 y esconde el problema.
7. **La mezcla de idiomas del corpus del tokenizer es una decisión de producto.** T5 usó 10:1:1:1 (EN:DE:FR:RO) para cubrir sus tareas; XLM-R muestrea idiomas con $\alpha=0.3$ al entrenar el modelo (Conneau et al.). Un vocabulario entrenado con 90 % inglés asigna mucho menos espacio al español (módulo 04).
8. **`byte_fallback` y los bytes ocupan ids del vocabulario.** Con `byte_fallback=True` pierdes 256 + 3 ids de tu `vocab_size`; con vocabularios pequeños (como nuestros 2 000) es una fracción apreciable.
""")

nb.md(r"""
## 13. ⚠️ Errores comunes

1. **Medir un tokenizer con texto de entrenamiento.** Siempre partición por documento y, para decisiones serias, un corpus de evaluación independiente (FLORES, módulo 04).
2. **Cambiar el normalizer entre entrenamiento e inferencia** (o guardar solo el vocabulario sin el `tokenizer.json` completo): produce tokenizaciones distintas y `[UNK]` inesperados.
3. **Atribuir al algoritmo lo que es del pre-tokenizador** (comparar BPE con regex GPT-2 vs Unigram con `Metaspace` y concluir «Unigram es peor»).
4. **Usar `BertNormalizer` con `strip_accents=True` en español** (`sé/se`, `él/el`, `qué/que`).
5. **Esperar que `decode(encode(x)) == x`** con WordPiece/BERT o con SentencePiece por defecto.
6. **Dejar `allowed_special="all"` en texto no confiable** (inyección de tokens de control; módulo 05).
7. **Olvidar que `vocab_size` incluye especiales y bytes** y comparar vocabularios «del mismo tamaño» con composición distinta.
8. **Usar muestreo de segmentaciones en inferencia.** Subword regularization es solo para entrenar; en inferencia, Viterbi/merges deterministas.
9. **Entrenar SentencePiece con líneas enormes** (se descartan sin aviso) o sin barajar/muestrear en corpus gigantes.
""")

nb.md(r"""
## 14. Autoevaluación

<details><summary><b>1 · (Cálculo)</b> En el corpus de juguete (N = 113 unidades), el par (<code>##u</code>, <code>##g</code>) tiene m = 20, c(<code>##u</code>) = 36 y c(<code>##g</code>) = 20. Calcula la aproximación $m(\log\frac{mN}{c_ac_b}-1)$ y compárala con el ΔL exacto (28.0). ¿Por qué difieren tanto?</summary>

$\log\frac{20\cdot113}{36\cdot20}=\log 3.139=1.144$; $20\,(1.144-1)\approx 2.9$, frente a 28.0 exacto. Difieren porque la expansión de primer orden exige $m\ll c_a, c_b$; aquí $m=c_b=20$: **todas** las `##g` desaparecen al fusionar, el término $f(c_b-m)=f(0)$ no es «pequeño». Con pares así hay que usar la fórmula exacta (que es lo que hace el código).
</details>

<details><summary><b>2 · (Cálculo)</b> Con el vocabulario semilla de <code>hugs</code>, ¿cuál es la probabilidad <i>a posteriori</i> de la segmentación <code>hug·s</code>?</summary>

$P(\text{hug·s})=0.15\cdot0.10=0.015$; $P(X)=0.1751$; posterior $=0.015/0.1751\approx0.086$ (8.6 %). Es la masa que el muestreo Unigram puede devolver en vez de `hugs`.
</details>

<details><summary><b>3 · (Diagnóstico)</b> Tu buscador en español no distingue «¿qué hora es?» de «que hora es». El tokenizer es un BERT-<i>uncased</i> multilingüe. ¿Qué pasa y cómo lo arreglas?</summary>

El `BertNormalizer(strip_accents=True, lowercase=True)` elimina las tildes **antes** de tokenizar, así que `qué` y `que` son la misma cadena (medimos 34 grupos de colisión en nuestro corpus). Solución: usar un modelo *cased* o un normalizer NFC/NFKC sin `strip_accents`, y re-indexar con el mismo normalizer en consulta e índice.
</details>

<details><summary><b>4 · (Diagnóstico)</b> Tras tokenizar un repositorio de Python con SentencePiece por defecto, el código decodificado pierde la indentación. ¿Causa y arreglo?</summary>

La normalización por defecto (`nmt_nfkc`, `remove_extra_whitespaces=True`) colapsa espacios y convierte saltos de línea en espacios; además el corpus se entrena por líneas. Arreglo: `normalization_rule_name="identity"`, `remove_extra_whitespaces=False`, `allow_whitespace_only_pieces=True`, `add_dummy_prefix=False` y `byte_fallback=True`; verifica con un test de round-trip sobre un conjunto de código.
</details>

<details><summary><b>5 · (Transferencia)</b> Para Políglota (ES/EN/código) debes decidir entre byte-level BPE con regex y SentencePiece-Unigram. Argumenta con criterios medibles.</summary>

Criterios: (i) cobertura sin `[UNK]` (ambos con bytes/`byte_fallback`); (ii) fertilidad y bytes/token **por idioma** sobre un corpus de evaluación independiente; (iii) manejo de código (espacios/indentación: la regex del BPE los trata bien, SentencePiece requiere configuración `identity`); (iv) alineación morfológica si el sparse retrieval (BM25) se apoya en el tokenizer (Unigram suele ganar); (v) ecosistema (`tiktoken`/HF) y reproducibilidad. Se decide con el benchmark del proyecto y el del módulo 04, no por moda.
</details>

<details><summary><b>6 · (Recuerdo)</b> ¿Por qué WordPiece segmenta con <i>longest-match-first</i> y Unigram con Viterbi? ¿Qué significa <code>##</code>?</summary>

WordPiece define un vocabulario, no una distribución sobre segmentaciones, así que usa una regla voraz determinista. Unigram es un modelo probabilístico, así que la segmentación óptima es el camino de máxima probabilidad (Viterbi) y se puede muestrear. `##` marca una pieza que **continúa** una palabra (no está al inicio).
</details>

<details><summary><b>7 · (Transferencia)</b> Quieres que tu clasificador sea robusto a typos. ¿Cómo usarías subword regularization y qué precaución tomas?</summary>

Entrena (o afina) con tokenización muestreada (Unigram `alpha≈0.1–0.5` o BPE-dropout `p≈0.05–0.1`) para que el modelo vea múltiples segmentaciones de la misma palabra; evalúa con un conjunto con typos sintéticos. Precauciones: en inferencia usa la segmentación determinista; mide el coste en reproducibilidad y verifica que no degrade el texto limpio (la evidencia a gran escala es 🟡).
</details>

<details><summary><b>8 · (Recuerdo)</b> ¿Qué tres componentes definen un <code>tiktoken.Encoding</code> y por qué no necesita una lista de merges?</summary>

`pat_str` (regex), `mergeable_ranks` (bytes → rank) y `special_tokens`. El rank de cada token es su orden de creación, que coincide con la prioridad de fusión; basta fusionar siempre el par de menor rank.
</details>
""")

nb.md(r"""
## 15. Referencias

**Papers (verificados: autor, año, título, enlace)**
- Schuster, M. y Nakajima, K. (2012). *Japanese and Korean voice search.* ICASSP 2012. <https://ieeexplore.ieee.org/document/6289079>
- Wu, Y. et al. (2016). *Google's Neural Machine Translation System: Bridging the Gap between Human and Machine Translation.* <https://arxiv.org/abs/1609.08144>
- Sennrich, R., Haddow, B. y Birch, A. (2016). *Neural Machine Translation of Rare Words with Subword Units.* <https://arxiv.org/abs/1508.07909>
- Kudo, T. (2018). *Subword Regularization: Improving Neural Network Translation Models with Multiple Subword Candidates.* <https://arxiv.org/abs/1804.10959>
- Kudo, T. y Richardson, J. (2018). *SentencePiece: A simple and language independent subword tokenizer and detokenizer for Neural Text Processing.* <https://arxiv.org/abs/1808.06226>
- Provilkov, I., Emelianenko, D. y Voita, E. (2020). *BPE-Dropout: Simple and Effective Subword Regularization.* <https://arxiv.org/abs/1910.13267>
- Bostrom, K. y Durrett, G. (2020). *Byte Pair Encoding is Suboptimal for Language Model Pretraining.* <https://arxiv.org/abs/2004.03720>
- Song, X. et al. (2021). *Fast WordPiece Tokenization.* <https://arxiv.org/abs/2012.15524>
- Uzan, O., Schmidt, C. W., Tanner, C. y Pinter, Y. (2024). *Greed is All You Need: An Evaluation of Tokenizer Inference Methods.* <https://arxiv.org/abs/2403.01289>
- Schmidt, C. W. et al. (2024). *Tokenization Is More Than Compression.* <https://arxiv.org/abs/2402.18376>
- Goldman, O. et al. (2024). *Unpacking Tokenization: Evaluating Text Compression and its Correlation with Model Performance.* <https://arxiv.org/abs/2403.06265>
- Dagan, G., Synnaeve, G. y Rozière, B. (2024). *Getting the most out of your tokenizer for pre-training and domain adaptation.* <https://arxiv.org/abs/2402.01035>
- Chai, Y. et al. (2024). *Tokenization Falling Short: On Subword Robustness in Large Language Models.* <https://arxiv.org/abs/2406.11687>
- Devlin, J. et al. (2018). *BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding.* <https://arxiv.org/abs/1810.04805>
- Raffel, C. et al. (2019). *Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer (T5).* <https://arxiv.org/abs/1910.10683>
- Conneau, A. et al. (2019). *Unsupervised Cross-lingual Representation Learning at Scale (XLM-R).* <https://arxiv.org/abs/1911.02116>
- Touvron, H. et al. (2023). *LLaMA: Open and Efficient Foundation Language Models.* <https://arxiv.org/abs/2302.13971>
- Llama Team, Meta (2024). *The Llama 3 Herd of Models.* <https://arxiv.org/abs/2407.21783>
- Gemma Team (2025). *Gemma 3 Technical Report.* <https://arxiv.org/abs/2503.19786>
- Land, S. y Bartolo, M. (2024). *Fishing for Magikarp: Automatically Detecting Under-trained Tokens in Large Language Models.* <https://arxiv.org/abs/2405.05417>

**Librerías y documentación**
- `tiktoken` (OpenAI, MIT): <https://github.com/openai/tiktoken> · `sentencepiece` (Google): <https://github.com/google/sentencepiece> · `tokenizers` (Hugging Face): <https://github.com/huggingface/tokenizers>
- Hugging Face LLM Course, cap. 6: Unigram <https://huggingface.co/learn/llm-course/chapter6/7> y construcción de tokenizers bloque a bloque <https://huggingface.co/learn/llm-course/chapter6/8>
- Mistral AI, guía de tokenización (Tekken): <https://docs.mistral.ai/guides/tokenization/>

**Siguiente:** módulo 04 (diseño de tokenizers modernos: tamaño del vocabulario, paridad multilingüe, costes) y proyecto de este módulo.
""")

nb.save(os.path.join(MOD_DIR, f"{SLUG}.ipynb"))
