"""Construye los notebooks del módulo 04 (lección + proyecto) y su README.

    python tokenization-embeddings-course/_tools/builders/build_04.py     # desde la raíz del repo
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from nbbuild import Notebook  # noqa: E402
import _a2_common as C  # noqa: E402

COURSE = "tokenization-embeddings-course"
SLUG = "04_diseno_tokenizers_modernos"
MOD_DIR = os.path.join(HERE, "..", "..", SLUG)
LESSON_REL = f"{COURSE}/{SLUG}/{SLUG}.ipynb"
PROJ_REL = f"{COURSE}/{SLUG}/04_proyecto_diseno_tokenizers_modernos.ipynb"
os.makedirs(os.path.join(MOD_DIR, "assets"), exist_ok=True)

# celda común: carga de tiktoken con guardas (la usan lección y proyecto)
TIK_CELL = r'''
import tiktoken
TIK = {}
for nombre in ["r50k_base", "cl100k_base", "o200k_base"]:
    try:
        TIK[nombre] = tiktoken.get_encoding(nombre)     # 1ª vez: descarga de openaipublic.blob.core.windows.net
    except Exception as e:
        print(f"(no pude cargar {nombre}: {type(e).__name__}; tras un proxy usa TIKTOKEN_CACHE_DIR). Se omitirá en los análisis.")
print({n: e.n_vocab for n, e in TIK.items()})
'''

# =====================================================================================
#                                       LECCIÓN
# =====================================================================================
nb = Notebook("Módulo 04 · Diseño de tokenizers modernos", colab_path=LESSON_REL)

nb.md(nb.badge() + r"""

# Módulo 04 · Diseño de tokenizers modernos: vocabulario, multilingüe y costes

| | |
|---|---|
| **Nivel** | 🟠 Avanzado |
| **Duración estimada** | ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) |
| **GPU recomendada** | Ninguna (CPU). Coste en Colab ≈ 0 unidades |
| **Prerrequisitos** | Módulos 01–03 (bytes, BPE, WordPiece/Unigram/SentencePiece, `tiktoken`, HF `tokenizers`) |
| **Hilo conductor** | **Políglota**: decides el vocabulario del buscador (ES/EN/código) con criterios de ingeniería, no por costumbre |

> **Contexto Políglota Labs.** Ya sabes *entrenar* tokenizers (módulo 03). Ahora te preguntan: «¿de qué tamaño?, ¿qué mezcla de idiomas?, ¿cuánto nos cuesta que un cliente escriba en español en vez de inglés?,
> ¿cómo tokenizamos números e indentación?, ¿qué tokens especiales necesitamos para el chat del asistente?». Esta lección convierte esas preguntas en **medidas y fórmulas**.
""")

nb.md(r"""
## 1. Objetivos de aprendizaje

1. **Formular** el diseño de un vocabulario como un problema de presupuesto (parámetros de embedding, coste del softmax, longitud de secuencia) y **calcular** sus trade-offs.
2. **Resumir** qué dicen las leyes de escala con el vocabulario (Tao et al., 2024) y por qué los vocabularios de los modelos recientes crecieron.
3. **Comparar** vocabularios reales (GPT-2/GPT-4/GPT-4o, Llama, Gemma, Qwen, Mistral/Tekken) con cifras **verificadas y fechadas** y reconocer qué cifras no están verificadas.
4. **Medir** fertilidad, bytes por token y **paridad entre idiomas** («token tax», prima de tokenización) sobre texto paralelo, y **traducirla a dinero y a contexto útil**.
5. **Analizar** cómo se tokenizan números, indentación y código, y qué diseño (dígitos sueltos, grupos, R2L, espacios) cambia el rendimiento.
6. **Diseñar** tokens especiales y *chat templates* correctamente (y evitar los errores clásicos: doble BOS, máscaras de pérdida, plantillas distintas entre entrenamiento y servicio).
7. **Implementar** una versión mínima de **SuperBPE** (tokens que cruzan palabras) y evaluar su ganancia y sus límites.
8. **Decidir** el vocabulario de Políglota con una función de coste explícita (calidad por idioma vs memoria).
""")

nb.md(r"""
## 2. 🔁 Conexión con módulos anteriores

<details><summary><b>R1 · (Módulo 03)</b> ¿Cuál es la diferencia entre fertilidad y bytes por token, y por qué no basta la fertilidad para comparar idiomas como el chino o el japonés?</summary>

Fertilidad = tokens/palabra; bytes por token = bytes UTF-8 de texto cubiertos por cada token. En idiomas sin espacios entre palabras (zh, ja) «palabra» no está bien definida, así que la fertilidad no es comparable; hay que normalizar por **contenido paralelo** (la misma frase traducida) o por bytes/caracteres.
</details>

<details><summary><b>R2 · (Módulo 02)</b> ¿Por qué un tokenizer byte-level no tiene <code>[UNK]</code> pero puede ser carísimo para ciertos idiomas?</summary>

Cualquier texto se descompone en bytes, así que siempre es representable. Pero un carácter no latino ocupa 2–4 bytes en UTF-8 y, si el vocabulario no tiene merges para esa escritura, cada byte es un token: tokens por carácter ≈ bytes por carácter.
</details>

<details><summary><b>R3 · (Módulo 03)</b> ¿Qué decide el pre-tokenizador y por qué ningún token puede cruzar sus fronteras?</summary>

Define las unidades dentro de las que se aplican los merges; si dos símbolos están en pre-tokens distintos nunca se fusionan. Hoy veremos qué pasa si se **relaja** esa restricción (SuperBPE).
</details>
""")

nb.code(C.pip_cell())
nb.code(C.SETUP.strip("\n"))
nb.md(r"""
### Utilidades de datos

Copia local de `carga_corpus()` (contrato común; ver módulo 03/00) y de `carga_paralelo()`: **frases paralelas** para medir paridad. Cadena para el paralelo: **FLORES+** (`openlanguagedata/flores_plus`, puede requerir aceptar términos y un token de HF) →
**opus-100 en-es** → **mini-conjunto de 16 frases × 12 idiomas escrito a mano** (aviso en pantalla). Con el mini-conjunto las cifras absolutas son *orientativas* (n pequeño): las conclusiones relativas (qué idioma paga más) son las que se sostienen.
""")
for _c in C.cells(C.CORPUS_1) + C.cells(C.CORPUS_2):
    nb.code(_c)
nb.code(C.CORPUS_USE.strip("\n"))
for _c in C.cells(C.PARALELO):
    nb.code(_c)
nb.code(C.PARALELO_LOADER.strip("\n") + "\n\npar = carga_paralelo(fast_dev=FAST_DEV_RUN)\nprint('paralelo:', par['source'], '| frases:', par['n'], '| idiomas:', list(par['langs']))")
nb.code(C.METRICS.strip("\n") + "\n" + C.TOKMETRICS.strip("\n"))
nb.code(TIK_CELL.strip("\n"))
nb.code(r'''
import pandas as pd
from tokenizers import Tokenizer, models, pre_tokenizers, normalizers, trainers, decoders, Regex
from tokenizers.pre_tokenizers import ByteLevel
rng = random.Random(SEED); train_docs, test_docs = [], []
for lang in ["es", "en", "code"]:
    pool = [d for d in docs if d["lang"] == lang]; rng.shuffle(pool); cut = int(0.8 * len(pool))
    train_docs += pool[:cut]; test_docs += pool[cut:]
test_by_lang = {l: [d["text"] for d in test_docs if d["lang"] == l] for l in ["es", "en", "code"]}
print({l: len(v) for l, v in test_by_lang.items()}, "docs de test | train:", len(train_docs))
''')

nb.md(r"""
## 3. Mapa de madurez

Estado del arte a **oct-2026**; las cifras de vocabulario cambian con cada versión de modelo.

| Técnica / decisión | Madurez | Quién la usa (con respaldo) | Fuente |
|---|---|---|---|
| Vocabularios de 100–260 k (frente a 32 k) | 🟢 | cl100k ≈ 100 k y o200k ≈ 200 k (medido abajo); Llama 3 = 128 256; Qwen2 = 151 643 + 3; Gemma ≈ 256 k | tiktoken; Land & Bartolo 2024; Qwen2 report; Gemma 3 report |
| Dígitos tratados aparte (sueltos o en grupos) | 🟢 | Llama 1/2 y Gemma 3: dígitos separados; GPT-3.5/4: grupos de hasta 3 dígitos | Touvron 2023; Gemma 3; Singh & Strouse 2024 |
| Tokenizador específico con código/indentación (espacios agrupados) | 🟢 | cl100k/o200k agrupan espacios; GPT-2 no (medido abajo) | Dagan et al. 2024; medición propia |
| Vocabulario óptimo según presupuesto de cómputo (leyes de escala con V) | 🟡 | Resultados de NeurIPS 2024 a ≤ 3 B parámetros; extrapolación a modelos grandes no contrastada | Tao et al. 2024 |
| Equidad multilingüe del tokenizer (paridad) | 🟡 | Medida y reportada (p. ej. Tekken de Mistral frente al SentencePiece anterior); sin estándar común | Petrov et al. 2023; Ahia et al. 2023; docs de Mistral |
| Tokens que cruzan palabras (SuperBPE) | 🟡 / 🔴 | Resultados a 8 B, solo inglés; adopción en producción no verificada | Liu et al. 2025 (COLM) |
| Chat templates con tokens de control | 🟢 | Estándar de facto (ChatML, plantillas por modelo en `tokenizer_config`) | Docs de HF `transformers` |
""")

nb.md(r"""
## 4. Intuición primero: el vocabulario es un presupuesto

Cada token del vocabulario cuesta **parámetros** (una fila de $d$ números en la matriz de embeddings y otra en la de salida), **cómputo** (el softmax final es $O(V\cdot d)$ por token generado) y **datos** (cada fila necesita ver suficientes ejemplos para entrenarse; los tokens raros quedan *sub-entrenados*, módulo 05).
A cambio, un vocabulario mayor **acorta las secuencias**: menos tokens para el mismo texto = menos cómputo de atención ($O(n^2)$), más texto en la ventana de contexto y menos pasos de decodificación.

```
 V pequeño ─────────────────────────────────────────────► V grande
 + embeddings baratos            - secuencias largas      + secuencias cortas        - matriz grande, softmax caro
 + cada token muy entrenado      - contexto "efectivo"↓   - tokens raros sub-entrenados
 + robusto a typos               - más pasos al generar   - más sensible a datos de tokenizer≠modelo
```
> 💡 **Analogía de compresión.** Es el compromiso clásico *tamaño del diccionario ↔ longitud del mensaje* de LZ/Huffman: el diccionario también se transmite (aquí: se entrena y se guarda en el modelo).
> **Analogía recsys.** Equivale al tamaño de la tabla de embeddings de ítems: ítems de cola larga con pocos ejemplos tienen embeddings pobres; se reparten *hash buckets* o se agrupan.
""")

nb.gemini(
    "imagen", "M04-IMG-01",
    "El vocabulario como presupuesto: qué se gana y qué se paga",
    "Balanza conceptual entre el tamaño del vocabulario V y sus costes/beneficios (embeddings, softmax, longitud de secuencia, tokens sub-entrenados).",
    """Diagrama técnico limpio, fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif legible, flechas claras, sin ilustraciones decorativas ni dibujos de balanzas realistas. Formato 16:9.

Título arriba: "El vocabulario es un presupuesto".

Composición: una barra horizontal central con una flecha de doble punta; el extremo izquierdo etiquetado "V pequeño (p. ej. 32 k)" y el derecho "V grande (p. ej. 256 k)". Debajo de la barra, dos columnas de cajas.

Columna izquierda (borde azul), cabecera "Lo que se GANA al crecer V": cuatro cajas apiladas: "Secuencias más cortas (menos tokens por texto)", "Más texto cabe en el contexto", "Menos pasos al generar", "Mejor cobertura de idiomas y de código".
Columna derecha (borde naranja), cabecera "Lo que se PAGA al crecer V": cuatro cajas apiladas: "Más parámetros: V × d en la matriz de entrada (y otra de salida si no hay weight tying)", "Softmax más caro: O(V · d) por token", "Tokens raros con pocos ejemplos: sub-entrenados", "Más superficie de ataque: glitch tokens".

Abajo, una franja gris con una curva en forma de U (sin números en los ejes) etiquetada en el eje X "Tamaño del vocabulario V" y en el eje Y "Pérdida a presupuesto de cómputo fijo", con un punto verde en el mínimo y el texto "óptimo: crece con el cómputo (Tao et al., 2024)".
Evita: números inventados, texto ilegible, flechas ambiguas, iconos decorativos, sombras, degradados.""",
    "Esquema con el eje de tamaño del vocabulario V y dos columnas: lo que se gana (secuencias más cortas, más contexto) y lo que se paga (parámetros, softmax, tokens sub-entrenados), con una curva en U cuyo mínimo crece con el cómputo.",
    """
 V pequeño (~32k) <────────────────────────────> V grande (~256k)
 SE GANA al crecer V                      SE PAGA al crecer V
  - secuencias más cortas                  - parámetros: V x d (x2 sin weight tying)
  - más texto en el contexto               - softmax O(V·d) por token
  - menos pasos al generar                 - tokens raros sub-entrenados
  - mejor cobertura idiomas/código         - más glitch tokens
 pérdida a cómputo fijo: curva en U, mínimo en V* (crece con el cómputo)
""",
)
nb.md(r"""
> 👀 **Qué debes observar.** No existe un «mejor V» absoluto: es el mínimo de una curva en U que **se desplaza a la derecha cuando aumenta el presupuesto de cómputo** (resultado que formalizan Tao et al., 2024). Por eso los modelos grandes y recientes usan vocabularios mayores que los de 2020.
""")

nb.md(r"""
## 5. 📐 Teoría: los números del presupuesto

Sea $d$ la dimensión del modelo, $L$ el nº de capas y $V$ el tamaño del vocabulario. Aproximaciones habituales (Transformer denso estándar, FFN $4d$; las variantes GQA/SwiGLU cambian constantes pero no la conclusión):

$$
N_{\text{no-emb}}\approx 12\,L\,d^{2},\qquad N_{\text{emb}}=V\,d\ \ (\text{con weight tying}),\qquad N_{\text{emb}}=2\,V\,d\ \ (\text{sin tying}).
$$

- **Coste de salida por token generado:** $\approx 2\,V\,d$ FLOPs (multiplicar el estado final por la matriz $V\times d$ y luego softmax).
- **Longitud de secuencia:** para un texto de $B$ bytes, $n=B/\beta(V)$ con $\beta$ = bytes por token, creciente y cóncava en $V$ (lo medimos en el módulo 03: rendimientos decrecientes).
- **Coste de atención** $\propto n^2$ y de FFN/proyecciones $\propto n$: reducir $n$ un 20 % ahorra ≈ 20 % en la parte lineal y ≈ 36 % en la cuadrática.

### Leyes de escala con el vocabulario (Tao et al., 2024)
Entrenaron modelos de 33 M a 3 B de parámetros variando $V$ y observaron que **el vocabulario óptimo depende del presupuesto de cómputo**: los parámetros del vocabulario deben crecer, pero **más despacio** que los no-vocabulario;
predicen que el óptimo para Llama2-70B habría sido ≥ 216 K (frente a 32 K reales) y, a igual cómputo, pasar de 32 K a 43 K mejoró ARC-Challenge de 29.1 a 32.0 (resultados de los autores a esa escala; 🟡). Para comparar vocabularios distintos usan una pérdida **normalizada por caracteres/bytes**, no por token (si no, el vocabulario mayor «parece» peor porque predice tokens más difíciles).

> ⚠️ **Por qué no comparar perplexidad por token entre tokenizers.** Un tokenizer con tokens más largos predice *menos* tokens, cada uno con más información; su pérdida por token es mayor aunque el modelo sea igual de bueno. Compara **bits por byte** (o por carácter).
""")

nb.code(r'''
# Fracción de parámetros que se va al vocabulario, para un Transformer "genérico" (aprox. 12·L·d² sin embeddings)
configs = {"A": (24, 1536), "B": (28, 1792), "C": (32, 4096), "D": (40, 5120), "E": (80, 8192)}   # (capas, d_model) genéricas
Vs = np.array([32_000, 50_257, 100_277, 128_256, 200_019, 256_000])
fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.2))
for (nombre, (L, d)), c_ in zip(configs.items(), plt.cm.viridis(np.linspace(0.05, 0.9, len(configs)))):
    n_no = 12 * L * d ** 2
    ax[0].plot(Vs / 1e3, 100 * (2 * Vs * d) / (n_no + 2 * Vs * d), "o-", color=c_, label=f"L={L}, d={d} ({n_no/1e9:.1f} B sin emb.)")
ax[0].set_xlabel("Tamaño del vocabulario V (miles)"); ax[0].set_ylabel("% de parámetros en embeddings (sin weight tying)"); ax[0].set_title("El vocabulario pesa MUCHO en modelos pequeños"); ax[0].legend(fontsize=7)
# Ahorro de cómputo al acortar la secuencia: lineal vs cuadrático
red = np.linspace(0, 0.5, 50)
ax[1].plot(100 * red, 100 * red, label="partes lineales (FFN, proyecciones)", c=COL["azul"], lw=2)
ax[1].plot(100 * red, 100 * (1 - (1 - red) ** 2), label="atención (∝ n²)", c=COL["naranja"], lw=2)
ax[1].set_xlabel("Reducción de tokens por texto (%)"); ax[1].set_ylabel("Ahorro de FLOPs (%)"); ax[1].set_title("Acortar la secuencia ahorra más en la atención"); ax[1].legend()
plt.tight_layout(); plt.show()
print("Ejemplo d=4096, L=32 (≈6.4 B no-emb): V=32k ->", f"{2*32000*4096/1e9:.2f} B en embeddings;", " V=256k ->", f"{2*256000*4096/1e9:.2f} B")
''')
nb.md(r"""
> 👀 **Qué debes observar.** **Izquierda:** en un modelo de ≈ 0.7–1 B parámetros sin embeddings, pasar de 32 k a 256 k tokens mete **de ≈ 10–13 % a ≈ 46–54 %** de los parámetros totales en las matrices de embedding (sin weight tying): los modelos pequeños con vocabularios enormes son en buena parte «tablas de embeddings».
> En un modelo de ≈ 64 B sin embeddings el mismo cambio cuesta de < 1 % a ≈ 6 %. **Derecha:** un 20 % menos de tokens ahorra ≈ 20 % en lo lineal y ≈ 36 % en la atención: la compresión del tokenizer es un multiplicador de cómputo.
""")

# ------------------------------- 6. Vocabularios reales -------------------------------
nb.md(r"""
## 6. Vocabularios de modelos reales (verificado, fechado)

Cifras **a oct-2026** y solo las que he podido contrastar con una fuente primaria o con una medición propia. Los modelos lanzados después (o cuyos tokenizers no pude abrir) **no** están en la tabla: verifica con `AutoTokenizer.from_pretrained(...).vocab_size`/`len(tokenizer)` (¡las dos cifras pueden diferir por tokens añadidos!).

| Modelo / tokenizer | Algoritmo | Vocabulario | Fuente |
|---|---|---|---|
| GPT-2 (`r50k_base`) | byte-level BPE + regex | 50 257 | medido con `tiktoken` (arriba) |
| GPT-3.5/GPT-4 (`cl100k_base`) | byte-level BPE + regex | 100 277 (incl. especiales) | medido con `tiktoken` |
| GPT-4o (`o200k_base`) | byte-level BPE + regex | 200 019 (incl. especiales) | medido con `tiktoken` |
| Llama 2 | BPE vía SentencePiece | 32 000 | Land & Bartolo 2024 (tabla 1) |
| Llama 3 | tiktoken (100 K) + 28 K no ingleses | 128 256 | Llama 3 report; Land & Bartolo 2024 |
| Qwen2 | byte-level BPE | 151 643 regulares + 3 de control | Qwen2 technical report |
| Gemma (1/2) | SentencePiece | 256 000 | Land & Bartolo 2024 (tabla 1) |
| Gemma 3 | SentencePiece (dígitos separados, bytes) | ≈ 262 k (texto) / 256 k (pie de tabla): el informe es inconsistente | Gemma 3 report |
| Mistral NeMo y posteriores (**Tekken**) | BPE basado en tiktoken | ≈ 130 k + ≈ 1 k tokens de control | Docs de Mistral (tokenization guide) |
| Command R (Cohere) | BPE | 255 029 | Land & Bartolo 2024 (tabla 1) |

> 🧠 **Patrón:** de 32 k (2023) a 100–256 k (2024–2026). Las dos razones, ambas medibles aquí: *(i)* mejor compresión multilingüe y de código, *(ii)* el vocabulario pesa poco en modelos grandes (gráfico anterior).
""")

nb.code(r'''
# Registro de tokenizers a comparar: nombre -> función texto -> lista de tokens (ids o strings). Solo cuenta len().
def entrena_bpe_bytes(textos, vocab_size: int) -> Tokenizer:
    """Byte-level BPE (regex GPT-2) entrenado aquí: nuestro 'vocabulario propio'."""
    PAT = r"""'(?:[sdmt]|ll|ve|re)| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""
    t = Tokenizer(models.BPE())
    t.pre_tokenizer = pre_tokenizers.Sequence([pre_tokenizers.Split(Regex(PAT), behavior="isolated"), ByteLevel(add_prefix_space=False, use_regex=False)])
    t.decoder = decoders.ByteLevel()
    t.train_from_iterator(textos, trainers.BpeTrainer(vocab_size=vocab_size, initial_alphabet=ByteLevel.alphabet(), special_tokens=["<|endoftext|>"]))
    return t

V_PROPIO = 4000 if FAST_DEV_RUN else 32000
bpe_propio = entrena_bpe_bytes([d["text"] for d in train_docs], V_PROPIO)
REG = {f"tiktoken {n.replace('_base','')}": (lambda s, e=e: e.encode_ordinary(s)) for n, e in TIK.items()}
REG[f"BPE propio ({V_PROPIO//1000}k, ES/EN/código)"] = lambda s: bpe_propio.encode(s).ids

# Tokenizers de modelos reales vía HF (cuando hay red). IDs sin verificar desde este entorno: la celda salta los que fallen.
MODELOS_HF = {"GPT-2": "gpt2", "Qwen2.5": "Qwen/Qwen2.5-0.5B", "XLM-R": "FacebookAI/xlm-roberta-base",
              "Mistral-NeMo (Tekken)": "mistralai/Mistral-Nemo-Instruct-2407", "Llama-3.2": "unsloth/Llama-3.2-1B"}
cargados = []
if hay_red("https://huggingface.co"):
    from transformers import AutoTokenizer
    for nombre, repo in MODELOS_HF.items():
        try:
            tk = AutoTokenizer.from_pretrained(repo)
            REG[f"{nombre} [HF]"] = (lambda s, tk=tk: tk.encode(s, add_special_tokens=False)); cargados.append(f"{nombre}: len(tokenizer)={len(tk)}")
        except Exception as e:
            print(f"   (omitido {nombre}: {type(e).__name__})")
    print("tokenizers HF cargados:", cargados)
else:
    print("Sin acceso a HF: se analizan los tokenizers disponibles localmente (tiktoken + el nuestro). Con red, esta celda añade tokenizers de modelos reales.")
print(list(REG))
''')

# ------------------------------- 7. Paridad -------------------------------
nb.md(r"""
## 7. Multilingüe y «token tax»: medir la paridad

Un tokenizer entrenado mayoritariamente con inglés necesita **más tokens para decir lo mismo** en otros idiomas. Petrov et al. (2023) lo cuantifican sobre texto **paralelo** (la misma frase traducida) y encuentran diferencias de hasta **15×** entre idiomas
con los tokenizers de LLM que analizaron, que persisten incluso en los pensados para ser multilingües; Ahia et al. (2023) lo traducen en **precio**: los hablantes de muchos idiomas pagan más por la misma información en APIs comerciales y reciben peor resultado.

**Prima de tokenización** (*premium*) de un idioma $\ell$ frente al inglés, sobre $n$ frases paralelas:

$$
\text{premium}(\ell)=\frac{\sum_{i=1}^{n}|\text{tok}(s_i^{\ell})|}{\sum_{i=1}^{n}|\text{tok}(s_i^{\text{en}})|}\qquad(\text{1.0 = paridad con el inglés}).
$$

Y la métrica complementaria **bytes por token** $\beta_\ell=\sum |s^\ell|_{\text{bytes}}/\sum|\text{tok}|$. Un tokenizer «justo» no tiene $\beta$ igual en todos los idiomas (los scripts ocupan distinto nº de bytes), pero sí debería tener un *premium* cercano a 1.

> ⚠️ **Honestidad de datos.** Con FLORES+ (≈ 1000 frases/idioma) las cifras son fiables. Con el mini-conjunto de 16 frases escrito a mano son **orientativas**; ordena los idiomas, pero no cites decimales.
""")

nb.code(r'''
def tabla_paridad(par: dict, registro: dict, langs=None) -> pd.DataFrame:
    langs = langs or [l for l in par["langs"]]
    filas = []
    for nombre, enc in registro.items():
        tot = {l: sum(len(enc(s)) for s in par["langs"][l]) for l in langs}
        byt = {l: sum(len(s.encode("utf-8")) for s in par["langs"][l]) for l in langs}
        for l in langs:
            filas.append({"tokenizer": nombre, "idioma": l, "tokens": tot[l], "premium": tot[l] / tot["en"], "bytes_por_token": byt[l] / tot[l]})
    return pd.DataFrame(filas)

dp = tabla_paridad(par, REG)
prem = dp.pivot_table(index="tokenizer", columns="idioma", values="premium")[list(par["langs"])]
bpt = dp.pivot_table(index="tokenizer", columns="idioma", values="bytes_por_token")[list(par["langs"])]
print(prem.round(2).to_string())
''')

nb.code(r'''
fig, ax = plt.subplots(1, 2, figsize=(14, 4.2), gridspec_kw={"width_ratios": [1.25, 1]})
im = ax[0].imshow(prem.values, cmap="YlOrRd", vmin=1, vmax=max(3, prem.values.max()))
ax[0].set_xticks(range(prem.shape[1])); ax[0].set_xticklabels(prem.columns); ax[0].set_yticks(range(prem.shape[0])); ax[0].set_yticklabels(prem.index, fontsize=8); ax[0].grid(False)
for i in range(prem.shape[0]):
    for j in range(prem.shape[1]): ax[0].text(j, i, f"{prem.values[i, j]:.1f}", ha="center", va="center", fontsize=8, color="white" if prem.values[i, j] > 2.4 else "black")
ax[0].set_title("Prima de tokenización frente al inglés (1.0 = paridad)"); plt.colorbar(im, ax=ax[0], fraction=0.03)
sel = [n for n in prem.index if "o200k" in n or "cl100k" in n or "propio" in n]
for n, c_ in zip(sel, [COL["azul"], COL["verde"], COL["naranja"]]): ax[1].plot(bpt.columns, bpt.loc[n].values, "o-", label=n, color=c_, lw=2)
ax[1].set_ylabel("Bytes de texto por token"); ax[1].set_title("Cuánto texto cubre cada token, por idioma"); ax[1].legend(fontsize=7)
plt.tight_layout(); plt.show()
''')
nb.md(r"""
> 👀 **Qué debes observar** (mini-conjunto de 16 frases; orientativo).
> **(1)** Con `cl100k` las escrituras alejadas del latín pagan mucho más que el inglés (hindi ≈ 4.9×, árabe ≈ 3×, ruso ≈ 2.1×) y los idiomas latinos algo menos pero **no** 1.0 (español ≈ 1.3×). Con `r50k` (GPT-2) es peor aún (hindi ≈ 7×, ruso ≈ 5.5×).
> **(2)** `o200k` comprime la brecha: hindi ≈ 1.6×, árabe ≈ 1.2×, ruso ≈ 1.25×; pero el **japonés sigue siendo el más caro (≈ 1.85×)**. Ampliar el vocabulario hacia otros idiomas es exactamente lo que cuestan los 100 k tokens extra.
> **(3)** **Nuestro BPE propio** (solo ES/EN/código) es *favorable* al español (≈ 1.2×) pero muy injusto con ru/hi/ja/ko/ar (≈ 4–8×): casi un token por byte. Si el producto atenderá esos idiomas, hay que incluirlos en el corpus del tokenizer.
""")

nb.gemini(
    "imagen", "M04-IMG-02",
    "El impuesto por idioma: la misma frase, distinto número de tokens",
    "Ilustra de forma cualitativa que una misma frase traducida se parte en más o menos tokens según el idioma y que eso se traduce en coste y contexto.",
    """Diagrama técnico limpio, fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif legible, sin ilustraciones decorativas. Formato 16:9.

Título arriba: "Token tax: la misma frase, distinto coste".

Cuatro filas horizontales. Cada fila tiene a la izquierda el nombre del idioma y la frase, y a la derecha una cadena de "fichas" rectangulares (chips) que representan los tokens (los chips NO llevan texto, solo son rectángulos; su número es ilustrativo).
Fila 1, "Inglés": "The model was trained on many languages." con 8 chips azules.
Fila 2, "Español": "El modelo se entrenó con muchos idiomas." con 11 chips verdes.
Fila 3, "Ruso": "Модель обучена на многих языках." con 17 chips naranjas.
Fila 4, "Hindi": "मॉडल को कई भाषाओं पर प्रशिक्षित किया गया था।" con 34 chips grises.
Al final de cada fila, una barra horizontal proporcional al nº de chips y una etiqueta "×1.0", "×1.4", "×2.1", "×4.3" respectivamente (marcadas con el texto "valores ilustrativos").
Debajo, tres cajas pequeñas en una fila: "$ más caro por la misma información", "menos contexto útil en la ventana", "más latencia al generar".
Pie en letra pequeña gris: "Cifras ilustrativas; mide tu tokenizer con texto paralelo (FLORES)".
Evita: presentar los números como mediciones reales, texto ilegible, iconos decorativos, banderas, sombras, degradados.""",
    "Cuatro filas con la misma frase en inglés, español, ruso e hindi y un número creciente de fichas (tokens) ilustrativas, con la etiqueta de coste relativo y tres consecuencias: dinero, contexto y latencia.",
    """
 Inglés  The model was trained on many languages.     [][][][][][][][]                     x1.0
 Español El modelo se entrenó con muchos idiomas.     [][][][][][][][][][]                 x1.4
 Ruso    Модель обучена на многих языках.             [][][][][][][][][][][][][][][][][]   x2.1
 Hindi   मॉडल को कई भाषाओं पर प्रशिक्षित ...          [][][]...(34 fichas)                  x4.3   (ilustrativo)
 consecuencias: $ más caro | menos contexto útil | más latencia
""",
)
nb.md(r"""
> 👀 **Qué debes observar.** Lo que importa no es la cifra exacta (ilustrativa aquí) sino la **cadena causal**: más tokens por la misma información → más dinero (se factura por token), menos documentos en el contexto y más pasos de decodificación. Compáralo con tu tabla de paridad real de arriba.
""")

# ------------------------------- 8. Costes -------------------------------
nb.md(r"""
## 8. Del token tax al dinero y al contexto útil

Si una API factura a $p$ dólares por millón de tokens (**valor que debes leer en la tarifa vigente de tu proveedor: aquí es un parámetro ilustrativo**), el coste de procesar la **misma información** en el idioma $\ell$ es

$$
\text{coste}(\ell)=\text{premium}(\ell)\cdot c_{\text{en}},\qquad c_{\text{en}}=\frac{p}{10^{6}}\cdot\overline{\text{tok}}_{\text{en}}\cdot n_{\text{frases}}.
$$

Y, para una ventana de contexto de $W$ tokens, cabe $W/(\overline{\text{tok}}_{\ell})$ frases del idioma $\ell$ (**contexto efectivo**). Con lo medido arriba:
""")

nb.code(r'''
PRECIO_USD_POR_MTOK = 1.0     # ILUSTRATIVO: sustituye por la tarifa vigente de tu proveedor (varía por modelo y fecha)
VENTANA = 128_000             # tokens de contexto (parámetro)
N_FRASES_MES = 50_000_000     # volumen de ejemplo: frases procesadas al mes

ref = "tiktoken o200k" if "tiktoken o200k" in prem.index else prem.index[0]
sub = dp[dp.tokenizer == ref].set_index("idioma"); n_par = par["n"]
tok_por_frase = sub["tokens"] / n_par
coste = tok_por_frase * N_FRASES_MES / 1e6 * PRECIO_USD_POR_MTOK
cabe = VENTANA / tok_por_frase
res = pd.DataFrame({"tokens/frase": tok_por_frase.round(1), "premium": sub["premium"].round(2), "coste_mes_USD": coste.round(0), "frases_en_ventana": cabe.round(0)})
print(f"Tokenizer: {ref} | precio ilustrativo {PRECIO_USD_POR_MTOK} USD/Mtok | volumen {N_FRASES_MES:,} frases/mes | ventana {VENTANA:,}")
print(res.to_string())
fig, ax = plt.subplots(1, 2, figsize=(12.5, 4))
orden = res["premium"].sort_values().index
ax[0].bar(orden, res.loc[orden, "coste_mes_USD"] / 1e3, color=[COL["azul"] if l == "en" else COL["naranja"] for l in orden]); ax[0].set_ylabel("Coste mensual (miles de USD, ilustrativo)"); ax[0].set_title(f"Misma información, distinto coste ({ref})")
ax[1].bar(orden, res.loc[orden, "frases_en_ventana"] / 1e3, color=[COL["azul"] if l == "en" else COL["verde"] for l in orden]); ax[1].set_ylabel("Frases que caben en la ventana (miles)"); ax[1].set_title(f"Contexto efectivo con W = {VENTANA:,}")
plt.tight_layout(); plt.show()
''')
nb.md(r"""
> 👀 **Qué debes observar.** Los dos gráficos son **la misma información leída de dos formas**: el idioma con mayor prima paga más y, a la vez, mete menos texto en la ventana. Con el precio y el volumen ilustrativos de la celda el recargo del japonés es ≈ +85 % sobre el inglés (≈ 500 USD/mes más); con tarifas reales y volúmenes de producto es una **decisión de negocio** (y de equidad) que se toma al diseñar el tokenizer, no después.
""")

# ------------------------------- 9. Números y código -------------------------------
nb.md(r"""
## 9. Números, espacios e indentación

**Números.** Si «1234567» se parte como `123|456|7` (grupos de 3 de izquierda a derecha, estilo GPT-3.5/4) las columnas de unidades de dos sumandos **no se alinean** con las del resultado.
Singh & Strouse (2024) mostraron en GPT-3.5/GPT-4 (modelos de marzo de 2023) que tokenizar **de derecha a izquierda** (forzado separando miles con comas) sube la precisión de la suma de ≈ 75.6 % a ≈ 97.8 % (GPT-3.5) y de ≈ 84.4 % a ≈ 98.9 % (GPT-4): el error venía de la **alineación de tokens**, no de «no saber sumar».
Llama 1/2 y Gemma 3 optan por **dígitos sueltos** (alineación perfecta, secuencias más largas). Es un diseño con trade-offs; la evidencia a escala actual es 🟡.

**Espacios.** GPT-2 usaba un token por espacio de indentación; cl100k/o200k tienen tokens para **runs de espacios**. Dagan et al. (2024) muestran que la regex de pre-tokenización y el tamaño cambian velocidad, contexto efectivo y rendimiento en código. Medimos ambos efectos.
""")

nb.code(r'''
numeros = ["7", "42", "1234", "1234567", "3.14159", "20241025", "1,234,567"]
if TIK:
    for n, e in TIK.items():
        print(f"{n:>12}:", {x: [e.decode_single_token_bytes(i).decode() for i in e.encode_ordinary(x)] for x in ["1234567", "3.14159", "1,234,567"]})
    print("\npatrón de números cl100k:", [p for p in TIK["cl100k_base"]._pat_str.split("|") if "N" in p][:2])
    # tokens por número según longitud (n dígitos)
    longitudes = list(range(1, 16)); r_ = random.Random(SEED)
    cuenta = {n: [np.mean([len(e.encode_ordinary("".join(r_.choice("0123456789") for _ in range(L)))) for _ in range(80)]) for L in longitudes] for n, e in TIK.items()}
    cuenta["dígitos sueltos"] = longitudes
# indentación: tokens por línea de código real con n espacios de indentación
def costo_indent(enc, codigos):
    por_nivel = collections.defaultdict(list)
    for c in codigos:
        for ln in c.split("\n"):
            if ln.strip():
                sp = len(ln) - len(ln.lstrip(" "))
                por_nivel[sp].append(len(enc(ln)) - len(enc(ln.lstrip(" "))))
    return {k: float(np.mean(v)) for k, v in sorted(por_nivel.items()) if k in (0, 4, 8, 12, 16) and len(v) >= 5}
codigos = [d["text"] for d in docs if d["lang"] == "code"]
ind = {nombre: costo_indent(enc, codigos) for nombre, enc in REG.items() if "tiktoken" in nombre or "propio" in nombre}
print({k: {n: round(v, 2) for n, v in d.items()} for k, d in ind.items()})
''')

nb.code(r'''
if TIK:
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.2))
    for (n, ys), c_ in zip(cuenta.items(), [COL["gris"], COL["azul"], COL["verde"], COL["rojo"]]): ax[0].plot(longitudes, ys, "o-", label=n, color=c_, lw=2, ms=4)
    ax[0].set_xlabel("Dígitos del número"); ax[0].set_ylabel("Tokens"); ax[0].set_title("Tokens por número aleatorio"); ax[0].legend(fontsize=8)
    niveles = [0, 4, 8, 12, 16]; w = 0.2
    for k, ((nombre, d), c_) in enumerate(zip(ind.items(), [COL["gris"], COL["azul"], COL["verde"], COL["naranja"]])):
        ax[1].bar(np.arange(len(niveles)) + (k - 1.5) * w, [d.get(n_, 0) for n_ in niveles], w, label=nombre, color=c_)
    ax[1].set_xticks(range(len(niveles))); ax[1].set_xticklabels([f"{n_} espacios" for n_ in niveles]); ax[1].set_ylabel("Tokens extra por la indentación (media por línea)")
    ax[1].set_title("Coste de la indentación en código Python real"); ax[1].legend(fontsize=7)
    plt.tight_layout(); plt.show()
''')
nb.md(r"""
> 👀 **Qué debes observar.** **Izquierda:** con `cl100k`/`o200k` un número crece **a saltos de 3 dígitos** (≈ 1 token por cada 3 cifras); GPT-2 (`r50k`) usa mezclas irregulares; solo «dígitos sueltos» es lineal y alineado. Cada diseño elige entre **longitud** y **alineación aritmética**.
> **Derecha:** en GPT-2 la indentación cuesta ≈ **un token por espacio** (16 espacios ≈ 16 tokens), mientras cl100k/o200k la colapsan a ≈ 1 token: la mitad del «peso» de un archivo de código con indentación profunda desaparece por una decisión de regex/vocabulario (Dagan et al., 2024).
""")

# ------------------------------- 10. Especiales y chat templates -------------------------------
nb.md(r"""
## 10. Tokens especiales y *chat templates*

Los **tokens especiales** (`<|endoftext|>`, `<s>`, `<|im_start|>`…) no se aprenden por frecuencia: se **reservan** en el vocabulario y se insertan por código. Hay tres familias:

1. **Estructura de secuencia:** BOS/EOS/PAD/UNK/SEP (`[CLS]`, `[SEP]` en BERT).
2. **Roles y turnos de chat:** `<|im_start|>user … <|im_end|>` (ChatML), `<|start_header_id|>` en Llama 3, `[INST]` en Mistral v1–v3… cada familia de modelos tiene **su** plantilla.
3. **Capacidades:** *fill-in-the-middle* (`<|fim_prefix|>…`), herramientas, imágenes, «pensamiento».

Un **chat template** es la función que convierte `[{"role": ..., "content": ...}, ...]` en la cadena exacta (con sus tokens especiales) con la que el modelo fue *post-entrenado*. En HF vive en `tokenizer.chat_template` (Jinja) y se aplica con `tokenizer.apply_chat_template`.
**Regla de oro:** la plantilla en servicio debe ser **idéntica** a la de entrenamiento; un espacio o un salto de línea de más degrada resultados de forma silenciosa.
""")

nb.gemini(
    "imagen", "M04-IMG-03",
    "Anatomía de una conversación con chat template (ChatML)",
    "Muestra cómo un diálogo de 3 mensajes se convierte en una secuencia con tokens especiales y qué tokens entran en la pérdida del post-entrenamiento.",
    """Diagrama técnico limpio, fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif legible y monoespaciada para la cadena, flechas claras. Formato 16:9.

Título arriba: "De mensajes a tokens: el chat template".

Parte superior (izquierda): una lista de 3 mensajes en cajas apiladas, cada una con su rol en una etiqueta de color: [system] "Eres un asistente de Políglota Labs." (gris), [user] "¿Qué es un token?" (azul), [assistant] "Un trozo de texto que el modelo usa como unidad." (verde).
Flecha ancha hacia la derecha etiquetada "apply_chat_template".
Parte superior (derecha): la cadena resultante en una caja monoespaciada, con los tokens especiales resaltados en naranja, exactamente así (cada línea en su renglón):
<|im_start|>system
Eres un asistente de Políglota Labs.<|im_end|>
<|im_start|>user
¿Qué es un token?<|im_end|>
<|im_start|>assistant
Un trozo de texto que el modelo usa como unidad.<|im_end|>

Parte inferior: la misma secuencia dibujada como una fila de chips de izquierda a derecha agrupados en tres bloques (system, user, assistant). Debajo de cada chip una línea indica "pérdida": los chips del bloque assistant (incluido <|im_end|>) tienen una marca verde "entra en la pérdida (label)"; los de system y user tienen una marca gris "enmascarado (-100)".
Leyenda abajo a la derecha: naranja = token especial, verde = parte entrenada, gris = contexto.
Nota pequeña: "La plantilla de servicio debe ser idéntica a la de entrenamiento".
Evita: texto ilegible, cadenas distintas a las indicadas, flechas ambiguas, iconos decorativos, sombras, degradados.""",
    "Tres mensajes (system, user, assistant) convertidos con apply_chat_template en una cadena ChatML con tokens especiales, y la misma secuencia con los tokens del turno assistant marcados como parte de la pérdida.",
    """
 [system] Eres un asistente...   --apply_chat_template-->
 [user]   ¿Qué es un token?          <|im_start|>system\nEres un asistente...<|im_end|>\n
 [assistant] Un trozo de texto...     <|im_start|>user\n¿Qué es un token?<|im_end|>\n
                                       <|im_start|>assistant\nUn trozo de texto...<|im_end|>
 pérdida:  system/user = enmascarado (-100) | assistant (+ <|im_end|>) = entra en la pérdida
""",
)
nb.md(r"""
> 👀 **Qué debes observar.** (1) Los roles son **texto + tokens especiales**, no una API mágica. (2) En el post-entrenamiento solo se calcula la pérdida sobre las respuestas del asistente (y su token de cierre, para que aprenda a *parar*); el resto se enmascara. (3) Si en servicio olvidas el `<|im_start|>assistant\n` final, el modelo no sabe que le toca hablar.
""")

nb.code(r'''
# 1) Ampliar un Encoding de tiktoken con tokens de chat (receta del README de tiktoken)
if TIK:
    cl = TIK["cl100k_base"]
    cl_im = tiktoken.Encoding(name="cl100k_im", pat_str=cl._pat_str, mergeable_ranks=cl._mergeable_ranks,
                              special_tokens={**cl._special_tokens, "<|im_start|>": 100264, "<|im_end|>": 100265})
    def chatml(mensajes, generar=True):
        s = "".join(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n" for m in mensajes)
        return s + ("<|im_start|>assistant\n" if generar else "")
    msgs = [{"role": "system", "content": "Eres un asistente de Políglota Labs."}, {"role": "user", "content": "¿Qué es un token?"}]
    txt = chatml(msgs); ids = cl_im.encode(txt, allowed_special="all")
    print(repr(txt)); print(len(ids), "tokens | especiales presentes:", [i for i in ids if i >= 100257])
    # máscara de pérdida: solo lo que viene DESPUÉS de '<|im_start|>assistant\n' hasta '<|im_end|>'
    completa = chatml(msgs + [{"role": "assistant", "content": "Un trozo de texto."}], generar=False)
    ids_c = cl_im.encode(completa, allowed_special="all"); inicio = len(cl_im.encode(chatml(msgs), allowed_special="all"))
    mask = [0] * inicio + [1] * (len(ids_c) - inicio - 1)  + [0]       # entrena respuesta + <|im_end|>; el '\n' final no
    print("tokens con pérdida:", [cl_im.decode([i]) for i, m in zip(ids_c, mask) if m])
''')

nb.code(r'''
# 2) El mismo mecanismo con HF: chat_template Jinja en un tokenizer propio
from transformers import PreTrainedTokenizerFast
from tokenizers import processors
msgs = [{"role": "system", "content": "Eres un asistente de Políglota Labs."}, {"role": "user", "content": "¿Qué es un token?"}]
bpe_chat = entrena_bpe_bytes([d["text"] for d in train_docs] + ["<|im_start|> <|im_end|> system user assistant"], V_PROPIO)
bos_id = bpe_chat.token_to_id("<|endoftext|>")
bpe_chat.post_processor = processors.TemplateProcessing(single="<|endoftext|> $A", special_tokens=[("<|endoftext|>", bos_id)])   # BOS automático
hf = PreTrainedTokenizerFast(tokenizer_object=bpe_chat, bos_token="<|endoftext|>", eos_token="<|endoftext|>", pad_token="<|endoftext|>")
hf.add_special_tokens({"additional_special_tokens": ["<|im_start|>", "<|im_end|>"]})
hf.chat_template = ("{% for m in messages %}<|im_start|>{{ m['role'] }}\n{{ m['content'] }}<|im_end|>\n{% endfor %}"
                    "{% if add_generation_prompt %}<|im_start|>assistant\n{% endif %}")
salida = hf.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
print(repr(salida))
# Error clásico (doble BOS): la plantilla ya escribió el BOS en el texto y el tokenizer añade otro al re-tokenizar
plantilla_con_bos = "<|endoftext|>" + salida
con = hf(plantilla_con_bos)["input_ids"]; sin = hf(plantilla_con_bos, add_special_tokens=False)["input_ids"]
print("add_special_tokens=True  ->", con.count(bos_id), "BOS al inicio:", con[:3])
print("add_special_tokens=False ->", sin.count(bos_id), "BOS al inicio:", sin[:3])
''')

nb.md(r"""
**Errores típicos con plantillas** (los verás en producción): (1) **doble BOS**: la plantilla ya añade `<s>` y el tokenizer lo añade otra vez al tokenizar el texto resultante (`add_special_tokens=False` al re-tokenizar); (2) plantilla de *entrenamiento* ≠ de *servicio* (un `\n` de más);
(3) olvidar `add_generation_prompt=True`; (4) enmascarar mal la pérdida (entrenar también sobre el prompt del usuario); (5) **inyección de tokens de control** desde el texto del usuario (si el usuario escribe `<|im_end|>` y tu tokenizer lo convierte en el token real, puede cerrar el turno: módulo 05).
""")
