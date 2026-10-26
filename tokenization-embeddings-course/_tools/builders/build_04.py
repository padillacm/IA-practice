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
**Tokenización y Embeddings: de BPE a los modelos modernos**

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
4. **Medir** fertilidad, bytes por token y **paridad entre idiomas** (prima de tokens, *tokenization premium*; coloquialmente «token tax») sobre texto paralelo, y **traducirla a dinero y a contexto útil**.
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

<details><summary><b>R3 · (Módulo 03)</b> ¿Qué decide el pre-tokenizer y por qué ningún token puede cruzar sus fronteras?</summary>

Define las unidades dentro de las que se aplican los merges; si dos símbolos están en pre-tokens distintos nunca se fusionan. Hoy veremos qué pasa si se **relaja** esa restricción (SuperBPE).
</details>

<details><summary><b>R4 · (Módulo 01) (Cálculo)</b> La frase «Привет, мир» (ruso) tiene 11 caracteres. ¿Cuántos bytes UTF-8 ocupa y cuántos tokens costaría, como máximo, en un BPE byte-level sin merges para cirílico?</summary>

9 letras cirílicas × 2 bytes + «,» + espacio = **20 bytes** → hasta **20 tokens** (uno por byte), frente a ≈ 3–4 tokens de la frase inglesa equivalente con un vocabulario bueno. Ese cociente es la «prima» que hoy mediremos con contenido paralelo.
</details>

<details><summary><b>R5 · (Módulo 00) (Diagnóstico)</b> Cambias el tokenizer del índice BM25 y el nDCG@10 sube de 0.81 a 0.83 en 40 consultas. ¿Puedes afirmar que el nuevo es mejor?</summary>

No sin un intervalo: con pocas consultas el IC bootstrap del módulo 00 tiene una anchura de varios puntos. Calcula el IC de la **diferencia por consulta** (pareada) y solo afirma mejora si excluye el 0. Aplica igual a las comparaciones de tokenizers de este módulo.
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
## 3. Intuición primero: el vocabulario es un presupuesto

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
## 4. 📐 Teoría: los números del presupuesto

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
## 5. Vocabularios de modelos reales (verificado, fechado)

Cifras **a oct-2026** y solo las que he podido contrastar con una fuente primaria o con una medición propia. Los modelos lanzados después (o cuyos tokenizers no pude abrir) **no** están en la tabla: verifica con `AutoTokenizer.from_pretrained(...).vocab_size`/`len(tokenizer)` (¡las dos cifras pueden diferir por tokens añadidos!).

| Modelo / tokenizer | Algoritmo | Vocabulario | Fuente |
|---|---|---|---|
| GPT-2 (`r50k_base`) | byte-level BPE + regex | 50 257 | medido con `tiktoken` (arriba) |
| GPT-3.5/GPT-4 (`cl100k_base`) | byte-level BPE + regex | 100 277 (incl. especiales) | medido con `tiktoken` |
| GPT-4o (`o200k_base`) | byte-level BPE + regex | 200 019 (incl. especiales) | medido con `tiktoken` |
| Llama 2 | BPE vía SentencePiece | 32 000 | Land & Bartolo 2024 (tabla 1) |
| Llama 3 | tiktoken (100 K) + 28 K no ingleses | 128 256 | Llama 3 report; Land & Bartolo 2024 |
| Qwen2 | byte-level BPE | 151 643 regulares + 3 de control | Qwen2 technical report |
| Gemma (1/2) | SentencePiece | 256 000 | Land & Bartolo 2024 (tabla 1, Gemma 1); Gemma 2 report (arXiv:2408.00118: «256k entries») |
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
## 6. Multilingüe y prima de tokens: medir la paridad

Un tokenizer entrenado mayoritariamente con inglés necesita **más tokens para decir lo mismo** en otros idiomas. Petrov et al. (2023) lo cuantifican sobre texto **paralelo** (la misma frase traducida) y encuentran diferencias de hasta **15×** entre idiomas
con los tokenizers de LLM que analizaron, que persisten incluso en los pensados para ser multilingües; Ahia et al. (2023) lo traducen en **precio**: los hablantes de muchos idiomas pagan más por la misma información en APIs comerciales y reciben peor resultado.

**Prima de tokens** (*tokenization premium*, a veces «token tax») de un idioma $\ell$ frente al inglés, sobre $n$ frases paralelas:

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
ax[0].set_title("Prima de tokens frente al inglés (1.0 = paridad)"); plt.colorbar(im, ax=ax[0], fraction=0.03)
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
    "La prima de tokens por idioma: la misma frase, distinto número de tokens",
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
## 7. De la prima de tokens al dinero y al contexto útil

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
## 8. Números, espacios e indentación

**Números.** Si «1234567» se parte como `123|456|7` (grupos de 3 de izquierda a derecha, estilo GPT-3.5/4) las columnas de unidades de dos sumandos **no se alinean** con las del resultado.
Singh & Strouse (2024) mostraron en GPT-3.5/GPT-4 (modelos de marzo de 2023) que tokenizar **de derecha a izquierda** (forzado separando miles con comas) sube la precisión de la suma de 75.6 % a 97.8 % en GPT-3.5 (8-shot, sumandos de 7–9 dígitos), con un efecto algo menor pero presente en GPT-4: el error venía de la **alineación de tokens**, no de «no saber sumar».
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
## 9. Tokens especiales y *chat templates*

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

# ------------------------------- 11. SuperBPE -------------------------------
nb.md(r"""
## 10. Tokens que cruzan palabras: SuperBPE

Todo el pipeline de los módulos 02–03 asume que **un token no cruza una palabra**. Pero «a lot of», «de la», «search engine» funcionan como unidades semánticas. **SuperBPE** (Liu et al., 2025; COLM 2025) añade un **currículo de dos etapas** al BPE:

1. **Etapa 1** (hasta un punto de transición $t$): BPE normal con pre-tokenización por espacios → aprende **subpalabras**.
2. **Etapa 2** (de $t$ a $T$): se **desactiva** la pre-tokenización por espacios y se sigue fusionando → aparecen **superpalabras** (tokens que cruzan espacios).

Resultados que reportan los autores (8 B de parámetros, vocabulario de 200 k, entrenados desde cero, **solo inglés**): hasta ≈ 33 % menos tokens para el mismo texto, +4.0 puntos de media en 30 tareas (+8.2 en MMLU) con ≈ 27 % menos cómputo de inferencia; pero **empeora LAMBADA** (77.0 → 70.6) y exige más CPU/memoria para entrenar el tokenizer, y requiere deduplicar para evitar superpalabras de *boilerplate*.
Estado: 🟡 (resultado de un grupo, escala 8 B, inglés); no he verificado adopción en producción.

Vamos a implementar la **versión mínima**: etapa 1 con `BpeTrainer` de HF (palabras), etapa 2 con fusiones sobre listas de tokens que **sí pueden cruzar espacios**, y comparamos con BPE estándar al **mismo tamaño total de vocabulario**.
""")

nb.gemini(
    "video", "M04-VID-01",
    "SuperBPE: de subpalabras a superpalabras",
    "Animación de las dos etapas de SuperBPE sobre la frase «en el caso de la ley» mostrando cómo, al desactivar la pre-tokenización por espacios, aparecen tokens que cruzan palabras.",
    """Animación explicativa 16:9, estilo diagrama técnico limpio: fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif y monoespaciada para los tokens, sin ilustraciones decorativas, sin voz en off, ritmo calmado. Texto en pantalla en español. Duración total 30 segundos.

Frase de ejemplo (usa exactamente esta): "en el caso de la ley". El símbolo ▁ marca el inicio de palabra.

Escena 1 (0–6 s): Título "SuperBPE: dos etapas". Se muestra la frase como una fila de chips grises, un chip por palabra: [▁en] [▁el] [▁caso] [▁de] [▁la] [▁ley]. Debajo, una barrera vertical roja (#D62728) entre cada par de chips con el texto "pre-tokenización por espacios: ningún token cruza la barrera".
Escena 2 (6–14 s): Etiqueta "Etapa 1 (BPE normal, hasta el punto de transición t)". Los chips de palabras se parten en subpalabras con una animación suave: [▁en] [▁el] [▁ca][so] [▁de] [▁la] [▁ley] y luego vuelven a fusionarse parcialmente; aparece un contador "|V| crece hasta t".
Escena 3 (14–20 s): Etiqueta "Transición: se APAGA la pre-tokenización por espacios". Las barreras rojas se desvanecen.
Escena 4 (20–28 s): Etiqueta "Etapa 2 (de t a T)": los pares adyacentes más frecuentes se fusionan a través de los espacios, uno por uno, con una flecha naranja por cada fusión: [▁en][▁el] → [▁en▁el]; [▁de][▁la] → [▁de▁la]. Resultado final en una fila: [▁en▁el] [▁ca][so] [▁de▁la] [▁ley] (4 chips + 1 = 5 chips de 7 iniciales, mostrados como "7 → 5 tokens").
Escena 5 (28–30 s): Texto final: "Menos tokens por texto. Límites: probado a 8 B, solo en inglés".
Evita: números distintos a los indicados, texto ilegible, flechas que se crucen, elementos decorativos, transiciones rápidas, música o voz.""",
    "Animación de 30 s: la frase «en el caso de la ley» pasa de 7 a 5 tokens al apagar la pre-tokenización por espacios y fusionar a través de las palabras en la etapa 2 de SuperBPE.",
    """
 Etapa 1 (palabras):   [▁en] | [▁el] | [▁ca][so] | [▁de] | [▁la] | [▁ley]      (7 tokens; | = barrera de espacios)
 Transición:           se apaga la pre-tokenización por espacios
 Etapa 2 (superpalabras): [▁en▁el] [▁ca][so] [▁de▁la] [▁ley]                    (5 tokens)
""",
    duration="30 s",
)
nb.md(r"""
> 👀 **Qué debes observar.** La ganancia viene **solo de la etapa 2**, que fusiona pares *entre* palabras que ya son frecuentes (`▁de▁la`, `▁en▁el`). Es compresión pura; que además mejore el modelo (como reportan los autores) es una afirmación empírica aparte y todavía no replicada a gran escala.
""")

nb.code(r'''
Counter = collections.Counter
def bpe_palabras(textos, V: int) -> Tokenizer:
    t = Tokenizer(models.BPE(unk_token="[UNK]")); t.normalizer = normalizers.NFKC()
    t.pre_tokenizer = pre_tokenizers.Metaspace(replacement="▁", prepend_scheme="always")
    t.train_from_iterator(textos, trainers.BpeTrainer(vocab_size=V, special_tokens=["[UNK]"], initial_alphabet=[chr(i) for i in range(32, 127)]))
    return t

def superbpe(textos, t_etapa1: int, T: int):
    """Etapa 1: BPE por palabras hasta t_etapa1. Etapa 2: fusiones entre tokens ADYACENTES aunque crucen espacios, hasta T."""
    base = bpe_palabras(textos, t_etapa1)
    secs = [base.encode(x).tokens for x in textos]; fusiones = []
    for _ in range(T - t_etapa1):
        cnt = Counter()
        for s in secs: cnt.update(zip(s, s[1:]))
        if not cnt: break
        (a, b), _ = max(cnt.items(), key=lambda kv: (kv[1], kv[0])); fusiones.append((a, b))
        for k, s in enumerate(secs):
            i, out = 0, []
            while i < len(s):
                if i < len(s) - 1 and s[i] == a and s[i + 1] == b: out.append(a + b); i += 2
                else: out.append(s[i]); i += 1
            secs[k] = out
    return base, fusiones

def codifica_super(base, fusiones, texto):
    s = base.encode(texto).tokens
    for a, b in fusiones:
        i, out = 0, []
        while i < len(s):
            if i < len(s) - 1 and s[i] == a and s[i + 1] == b: out.append(a + b); i += 2
            else: out.append(s[i]); i += 1
        s = out
    return s

T_TOTAL, T_ETAPA1 = (2000, 1500) if FAST_DEV_RUN else (16000, 12000)
res_sb = {}
for lang in ["en", "es"]:
    tr = [d["text"] for d in train_docs if d["lang"] == lang]; te = test_by_lang[lang]
    t0 = time.time(); base, fus = superbpe(tr, T_ETAPA1, T_TOTAL); t_tr = time.time() - t0
    bpe = bpe_palabras(tr, T_TOTAL); nbytes = sum(len(x.encode()) for x in te)
    n_bpe = sum(len(bpe.encode(x).tokens) for x in te); n_sup = sum(len(codifica_super(base, fus, x)) for x in te)
    res_sb[lang] = {"bpe": nbytes / n_bpe, "super": nbytes / n_sup, "reduccion": 1 - n_sup / n_bpe, "fusiones": fus, "seg": t_tr}
    print(f"{lang}: bytes/token BPE {nbytes/n_bpe:.2f} -> SuperBPE {nbytes/n_sup:.2f} | {1-n_sup/n_bpe:.1%} menos tokens | entrenar etapa 2: {t_tr:.0f}s | ejemplos: {[a+b for a, b in fus[:6]]}")
''')

nb.code(r'''
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
x = np.arange(2); w = 0.35
ax[0].bar(x - w / 2, [res_sb[l]["bpe"] for l in ["en", "es"]], w, label=f"BPE (|V|={T_TOTAL})", color=COL["azul"])
ax[0].bar(x + w / 2, [res_sb[l]["super"] for l in ["en", "es"]], w, label=f"SuperBPE (t={T_ETAPA1})", color=COL["naranja"])
ax[0].set_xticks(x); ax[0].set_xticklabels(["inglés", "español"]); ax[0].set_ylabel("Bytes por token (test)"); ax[0].set_title("Misma talla de vocabulario, menos tokens"); ax[0].legend()
for l, c_ in zip(["en", "es"], [COL["verde"], COL["gris"]]):
    n_palabras = [a.count("▁") + b.count("▁") for a, b in res_sb[l]["fusiones"]]
    ax[1].plot(np.arange(len(n_palabras)), np.cumsum([1 if (a.count("▁") + b.count("▁")) >= 2 else 0 for a, b in res_sb[l]["fusiones"]]), label=f"{l}: superpalabras acumuladas", color=c_, lw=2)
ax[1].set_xlabel("Fusión de la etapa 2"); ax[1].set_ylabel("Tokens que cruzan ≥ 1 espacio (acumulado)"); ax[1].set_title("Etapa 2: casi todo son superpalabras"); ax[1].legend()
plt.tight_layout(); plt.show()
print("Superpalabras más frecuentes (ES):", [a + b for a, b in res_sb["es"]["fusiones"][:10]])
print("Superpalabras más frecuentes (EN):", [a + b for a, b in res_sb["en"]["fusiones"][:10]])
''')
nb.md(r"""
> 👀 **Qué debes observar.** **Izquierda:** con el *mismo* tamaño total de vocabulario, SuperBPE cubre más bytes por token (en nuestra escala diminuta la ganancia es de unos pocos %; los autores reportan hasta 33 % con 200 k y gran corpus: la ganancia crece con el vocabulario porque hay más pares frecuentes que fusionar).
> **Derecha:** casi toda la etapa 2 produce superpalabras. Las primeras son **palabras funcionales** frecuentes (`de la`, `en el`, `of the`): no son «semánticas»; en corpus grandes aparecen colocaciones como `a lot of`.
> **Límites:** más memoria/CPU para entrenar el tokenizer, riesgo de superpalabras de *boilerplate* si no deduplicas, y el trabajo reporta caídas puntuales (LAMBADA). Es 🟡.
""")

# ------------------------------- 12. Diseño para Políglota -------------------------------
nb.md(r"""
## 11. Receta: diseñar el vocabulario de Políglota

Un vocabulario se diseña con **tres palancas** y una función de coste:

1. **Mezcla del corpus del tokenizer** (qué proporción de ES, EN, código y, si aplica, otros idiomas). Un corpus «natural» (dominado por inglés) deja pocos merges al resto; suele muestrearse con **temperatura** $p_\ell\propto n_\ell^{\alpha}$ ($\alpha<1$ sube la proporción de idiomas pequeños; XLM-R usa $\alpha=0.3$ para muestrear idiomas al entrenar el modelo).
2. **Tamaño $V$**: se elige en la **rodilla** de la curva *tokens por KB vs $V$* (cuando añadir 1 k tokens ya ahorra < $\varepsilon$ %), acotado por el presupuesto de parámetros (sección 4).
3. **Pre-tokenización** (regex): dígitos, espacios/indentación, mayúsculas (módulo 02/03).

**Función de coste (la que usarás en el proyecto):** con tráfico esperado $w_\ell$ por idioma,
$\;J(V,\text{mezcla})=\sum_\ell w_\ell\cdot\text{tokens por KB}_\ell\;+\;\lambda\cdot V/10^{3}$, y se compara también la **peor prima** entre idiomas (equidad).

Primero medimos el efecto de la **mezcla** con un experimento controlado (mismo $V$, mismo total de texto de entrenamiento, solo cambia la proporción).
""")

nb.code(r'''
def corpus_mezcla(prop: dict, total_chars: int, semilla: int = SEED) -> list:
    """Muestrea documentos de train por idioma hasta total_chars*prop[idioma] caracteres (con reposición si hace falta)."""
    r = random.Random(semilla); out = []
    for lang, p in prop.items():
        pool = [d["text"] for d in train_docs if d["lang"] == lang]; acc = 0
        while acc < p * total_chars:
            t = r.choice(pool); out.append(t); acc += len(t)
    r.shuffle(out); return out

def bytes_por_token(tok, lang): 
    te = test_by_lang[lang]; return sum(len(x.encode()) for x in te) / sum(len(tok.encode(x).ids) for x in te)

TOTAL = 400_000 if FAST_DEV_RUN else 4_000_000
natural = {"en": 0.80, "es": 0.15, "code": 0.05}
suav = {k: v ** 0.3 / sum(u ** 0.3 for u in natural.values()) for k, v in natural.items()}      # temperatura alpha = 0.3
MEZCLAS = {"natural 80/15/5": natural, f"temperatura α=0.3 ({suav['en']:.0%}/{suav['es']:.0%}/{suav['code']:.0%})": suav,
           "equilibrada 1/3": {"en": 1 / 3, "es": 1 / 3, "code": 1 / 3}, "sesgo ES 20/60/20": {"en": 0.2, "es": 0.6, "code": 0.2}}
res_mix = {}
for nombre, prop in MEZCLAS.items():
    tk = entrena_bpe_bytes(corpus_mezcla(prop, TOTAL), V_PROPIO)
    res_mix[nombre] = {l: bytes_por_token(tk, l) for l in ["es", "en", "code"]}
dmix = pd.DataFrame(res_mix).T; print(dmix.round(2))
fig, ax = plt.subplots(figsize=(9, 4)); dmix[["es", "en", "code"]].plot.bar(ax=ax, rot=15, color=[COL["verde"], COL["azul"], COL["naranja"]])
ax.set_ylabel("Bytes por token en test (mayor = mejor)"); ax.set_title(f"La mezcla del corpus del tokenizer reparte el vocabulario (|V|={V_PROPIO})"); plt.tight_layout(); plt.show()
''')
nb.md(r"""
> 👀 **Qué debes observar.** Con el mismo $V$ y el mismo volumen de texto, **quien más pesa en la mezcla se lleva más merges**: la mezcla «natural» (80 % inglés) da el mejor inglés y el peor español; el sesgo al español invierte el orden. La mezcla suavizada (temperatura) y la equilibrada reparten mejor, **a costa de una pequeña pérdida en el idioma dominante**.
> No hay almuerzo gratis: es un reparto de un presupuesto fijo, y la decisión correcta depende del **tráfico** y de la política de equidad del producto (la sección siguiente lo formaliza).
""")

nb.code(r'''
# Barrido de V con la mezcla suavizada: ¿dónde está la rodilla?  y función de coste J con tráfico esperado
trafico = {"es": 0.5, "en": 0.3, "code": 0.2}          # supuesto de producto (parámetro)
LAMBDA = 3.0                                           # penalización de memoria: "tokens/KB" equivalentes por cada 1 k de vocabulario (parámetro de producto)
VS = [1000, 2000, 4000, 8000, 16000] if FAST_DEV_RUN else [4000, 8000, 16000, 32000, 64000]
corp = corpus_mezcla(suav, TOTAL); filas = []; TKS = {}          # TKS: guardamos cada candidato para auditarlo (sección 11.1)
for V in VS:
    tk = TKS[V] = entrena_bpe_bytes(corp, V)
    tpk = {l: 1000 / bytes_por_token(tk, l) for l in ["es", "en", "code"]}               # tokens por KB de texto
    J = sum(trafico[l] * tpk[l] for l in tpk) + LAMBDA * V / 1e3
    filas.append({"V": V, **{f"tpk_{l}": v for l, v in tpk.items()}, "tokens_prom": sum(trafico[l] * tpk[l] for l in tpk), "J": J})
dv = pd.DataFrame(filas).set_index("V"); print(dv.round(2))
mejora = (dv["tokens_prom"].shift(1) - dv["tokens_prom"]) / dv["tokens_prom"].shift(1) * 100
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
for l, c_ in zip(["es", "en", "code"], [COL["verde"], COL["azul"], COL["naranja"]]): ax[0].plot(dv.index, dv[f"tpk_{l}"], "o-", label=l, color=c_, lw=2)
ax[0].set_xscale("log"); ax[0].set_xlabel("Tamaño del vocabulario V"); ax[0].set_ylabel("Tokens por KB de texto (menor = mejor)"); ax[0].set_title("Rendimientos decrecientes por idioma"); ax[0].legend()
ax[1].plot(dv.index, dv["J"], "o-", c=COL["rojo"], lw=2); V_opt = int(dv["J"].idxmin()); ax[1].axvline(V_opt, color=COL["gris"], ls="--")
ax[1].set_xscale("log"); ax[1].set_xlabel("Tamaño del vocabulario V"); ax[1].set_ylabel("Coste J = Σ w·tokens/KB + λ·V/1000"); ax[1].set_title(f"Mínimo de J en V = {V_opt}"); plt.tight_layout(); plt.show()
print("mejora % al duplicar V:", mejora.round(1).dropna().to_dict(), "| V* =", V_opt)
''')
nb.md(r"""
> 👀 **Qué debes observar.** **Izquierda:** cada duplicación de $V$ ahorra menos tokens que la anterior (en nuestra corrida: −16 %, −14 %, −10 %, −7 %). Entre 4 k y 16 k el español sigue mejorando más que el inglés (≈ −21 % frente a ≈ −15 %), mientras el código, que necesita más tokens por KB, mejora menos (≈ −11 %).
> **Derecha:** $J$ tiene un mínimo interior: pasado cierto $V$, el coste en parámetros supera el ahorro de tokens (con $\lambda=3$ el mínimo cae en 8 000).
> Ese mínimo **depende de $\lambda$ y del tráfico** (decisiones de producto): cámbialos y verás moverse $V^*$. En un LLM real $\lambda$ sale del presupuesto de parámetros (sección 4) y de las leyes de escala (Tao et al., 2024).
""")

nb.md(r"""
### 11.1 🧠 Auditoría del vocabulario antes de un preentrenamiento caro

**Por qué se audita *antes*.** Después del preentrenamiento el tokenizer ya no se puede cambiar gratis: (1) cada fila de la matriz de embeddings (y de la cabeza de salida) está ligada a un id concreto; (2) el corpus de preentrenamiento suele guardarse **ya tokenizado** (shards de ids), así que un cambio obliga a re-tokenizar petabytes; (3) las leyes de escala y los presupuestos se expresan **en tokens de ese tokenizer**; (4) todas las evaluaciones y *checkpoints* intermedios quedan como referencia en esa unidad. Cambiarlo después es el problema de *tokenizer transfer* (módulo 07), que cuesta datos y calidad. Por eso los equipos de preentrenamiento lo tratan como una decisión de arquitectura, con su propia auditoría (práctica habitual; los informes técnicos rara vez publican el protocolo completo).

**Lista de control mínima** (todas sobre un *held-out* con la mezcla real del modelo, no del tokenizer):
1. **Round-trip exacto** `decode(encode(x)) == x` (sin pérdidas por normalización; módulos 01 y 03).
2. **Compresión por idioma/dominio** (bytes/token) y **peor prima** (sección 6).
3. **Más allá de la fertilidad: eficiencia de Rényi.** Zouhar et al. (2023) proponen $\;\mathrm{Eff}_\alpha=\dfrac{H_\alpha(p)}{\log |V|},\;\; H_\alpha(p)=\dfrac{1}{1-\alpha}\log\sum_{t}p(t)^{\alpha}$, con $p$ la distribución unigrama de tokens; con $\alpha=2.5$ correlaciona 0.78 con BLEU en sus experimentos de traducción, frente a −0.32 de la longitud comprimida. Penaliza vocabularios con tokens muy frecuentes *y* con muchos tokens rarísimos. ⚠️ No es un oráculo: Cognetta et al. (2024) construyen variantes de BPE que **suben** la eficiencia de Rényi mientras **empeoran** el modelo. Úsala como una señal más, nunca como objetivo a optimizar.
4. **Uso del vocabulario**: qué fracción de $V$ aparece en el held-out. Los ids que nunca aparecen son candidatos a **tokens sub-entrenados** (módulo 05), sobre todo si el corpus del tokenizer difiere del del modelo.
5. **Token más largo** y tokens «basura» (URLs, cadenas repetidas, *boilerplate*): suelen delatar duplicados en el corpus del tokenizer.
6. **Slots reservados y $V$ físico**: cuántos ids dejas libres para fine-tuning (tokens de control, herramientas, idiomas) y a qué múltiplo redondeas $V$ (siguiente celda).
""")
nb.code(r'''
import math
from collections import Counter

def renyi_eficiencia(conteos: Counter, V: int, alpha: float = 2.5) -> float:
    """Eficiencia de Rényi (Zouhar et al., 2023): H_alpha(p) / log|V|, con p = unigramas de tokens."""
    n = sum(conteos.values()); p = np.array([c / n for c in conteos.values()], dtype=float)
    return (math.log(np.sum(p ** alpha)) / (1 - alpha)) / math.log(V)

def auditoria_vocab(tk, held_out: dict) -> dict:
    """Auditoría barata de un tokenizer HF candidato sobre un held-out {idioma: [textos]}."""
    V = tk.get_vocab_size(); cont = Counter(); ok = tot = 0; fila = {"V": V}
    for lang, textos in held_out.items():
        nbytes = ntok = 0
        for x in textos:
            ids = tk.encode(x).ids; cont.update(ids); nbytes += len(x.encode("utf-8")); ntok += len(ids)
            ok += int(tk.decode(ids) == x); tot += 1
        fila[f"B/tok {lang}"] = nbytes / max(ntok, 1)
    fila["round-trip %"] = 100 * ok / max(tot, 1)
    fila["Rényi α=2.5"] = renyi_eficiencia(cont, V)
    fila["% de V visto"] = 100 * len(cont) / V
    fila["token más largo (chars)"] = max(len(tk.decode([i])) for i in range(V))
    return fila

daud = pd.DataFrame([auditoria_vocab(TKS[V], test_by_lang) for V in VS]).set_index("V")
print(daud.round(3))
fig, ax = plt.subplots(1, 2, figsize=(12, 4))
ax[0].plot(daud.index, daud["Rényi α=2.5"], "o-", c=COL["azul"], lw=2); ax[0].set_xscale("log")
ax[0].set_xlabel("Tamaño del vocabulario V"); ax[0].set_ylabel("Eficiencia de Rényi (α = 2.5)"); ax[0].set_title("Rényi: otra señal además de bytes/token")
ax[1].plot(daud.index, daud["% de V visto"], "o-", c=COL["rojo"], lw=2); ax[1].set_xscale("log")
ax[1].set_xlabel("Tamaño del vocabulario V"); ax[1].set_ylabel("% de ids que aparecen en el held-out"); ax[1].set_title("Ids nunca vistos = riesgo de tokens sub-entrenados")
plt.tight_layout(); plt.show()
''')
nb.md(r"""
> 👀 **Qué debes observar.** **Columna V:** el candidato más grande puede tener **menos** tokens de los pedidos (con `FAST_DEV_RUN`, ≈ 13 k en lugar de 16 k): el entrenador se quedó sin pares que fusionar en un corpus pequeño. Audita siempre el $V$ *real*, no el del fichero de configuración.
> **Izquierda:** mientras los bytes/token mejoran con $V$, la eficiencia de Rényi **empeora** (≈ 0.74 → 0.50 en nuestra corrida): las dos señales tiran en direcciones opuestas y la decisión necesita un criterio de producto o un modelo pequeño de prueba, no una sola métrica. **Derecha:** incluso con $V=1000$ no se ve el 100 % (muchos de los 256 bytes base nunca aparecen en ES/EN/código), y al crecer $V$ la fracción de ids vistos cae con fuerza (≈ 31 % en el mayor). Con un held-out tan pequeño la cifra absoluta exagera, pero la tendencia es la que importa: esos ids recibirán pocos gradientes si el modelo ve datos como el held-out (tokens sub-entrenados, módulo 05). El round-trip debe ser 100 % en un byte-level BPE sin normalizador: cualquier otro valor es un bug que hay que encontrar **antes** de gastar cómputo.
""")

nb.md(r"""
### 11.2 La trampa de comparar pérdida por token (y cómo calcular bpb sin errores)

Un modelo con un tokenizer de tokens largos tiene **más** pérdida por token (cada token lleva más información) aunque modele **mejor** el texto. La métrica comparable es **bits por byte**: $\mathrm{bpb}=\dfrac{\sum_i \mathcal{L}_i}{\ln 2\cdot n_{\text{bytes}}}$ (pérdida total en nats sobre el texto, dividida por sus bytes UTF-8). Para verlo sin entrenar un Transformer, usamos el LM más simple posible: un **unigrama de tokens** (con suavizado de Laplace) entrenado con cada tokenizer candidato. Trampas habituales al calcular bpb (práctica habitual de evaluación):
* el denominador son los bytes del **texto original**, no del texto normalizado (un NFKC o un *lowercase* cambian los bytes);
* la pérdida debe sumar **todos** los tokens del texto (incluido el primero y el EOS si se evalúa) y no promediar por lote antes de convertir;
* ambos modelos deben evaluarse sobre **exactamente el mismo texto** (mismos documentos, mismos cortes de contexto **en bytes**, módulo 06).
""")
nb.code(r'''
def unigrama_loss_y_bpb(tk, textos_train, textos_test):
    """LM unigrama de tokens con Laplace: devuelve (nats por token, bits por byte) en test."""
    V = tk.get_vocab_size(); c = Counter(i for x in textos_train for i in tk.encode(x).ids); n = sum(c.values())
    nats = ntok = nbytes = 0
    for x in textos_test:
        ids = tk.encode(x).ids; ntok += len(ids); nbytes += len(x.encode("utf-8"))
        nats += sum(-math.log((c[i] + 1) / (n + V)) for i in ids)
    return nats / ntok, nats / (math.log(2) * nbytes)

test_todo = [x for v in test_by_lang.values() for x in v]
dlb = pd.DataFrame([dict(zip(["V", "nats/token", "bpb"], (V, *unigrama_loss_y_bpb(TKS[V], corp, test_todo)))) for V in VS]).set_index("V")
print(dlb.round(3))
fig, ax = plt.subplots(1, 2, figsize=(12, 4))
ax[0].plot(dlb.index, dlb["nats/token"], "o-", c=COL["naranja"], lw=2); ax[0].set_title("Pérdida por token: ¿el V pequeño 'gana'?")
ax[1].plot(dlb.index, dlb["bpb"], "o-", c=COL["verde"], lw=2); ax[1].set_title("Bits por byte: la comparación honesta")
for a, yl in zip(ax, ["nats por token (menor = mejor)", "bits por byte (menor = mejor)"]): a.set_xscale("log"); a.set_xlabel("Tamaño del vocabulario V"); a.set_ylabel(yl)
plt.tight_layout(); plt.show()
print("mejor V según pérdida/token:", int(dlb["nats/token"].idxmin()), "| mejor V según bpb:", int(dlb["bpb"].idxmin()))
''')
nb.md(r"""
> 👀 **Qué debes observar.** La pérdida por token **crece** con $V$ (cada token codifica más bytes), así que «elegir el $V$ con menor pérdida» premiaría siempre el vocabulario más pequeño. En bpb la ordenación se invierte: el mismo modelo unigrama describe el texto con menos bits por byte cuando los tokens capturan más estructura (en nuestra corrida 3.30 → 2.57 bpb), con rendimientos decrecientes al final, donde la escasez de datos por token empieza a pesar. Las dos métricas eligen $V$ distintos **con el mismo modelo y el mismo texto**: si en un informe ves «loss» comparada entre tokenizers, pide el bpb.
""")

nb.md(r"""
### 11.3 Slots reservados, $V$ físico y la unidad de las leyes de escala

* **Redondear $V$.** El vocabulario «físico» (filas de la matriz de embeddings) se redondea a un múltiplo de 64 o 128 para que las multiplicaciones de la cabeza de salida usen *tiles* completos de GPU; `nanoGPT` lo documenta en su configuración: «GPT-2 vocab_size of 50257, padded up to nearest multiple of 64 for efficiency» (50 304). Las filas extra son ids que el tokenizer nunca emite.
* **Reservar ids.** El tokenizer oficial de Llama 3 añade a sus 128 000 tokens base **256 especiales** (`num_reserved_special_tokens = 256`): unos pocos con nombre (`<|begin_of_text|>`, `<|eot_id|>`, `<|start_header_id|>`…) y el resto `<|reserved_special_token_N|>`, de forma que 128 256 ya es múltiplo de 128. Reservar sale barato al principio y evita redimensionar la matriz en el fine-tuning (nuevos roles, herramientas, modalidades).
* **⚠️ Reservado ≠ entrenado.** Un id que nunca aparece en el preentrenamiento no recibe señal útil: sus embeddings quedan en la inicialización (o los empuja hacia abajo el softmax de salida). Antes de usar un slot reservado en fine-tuning hay que **inicializarlo** (p. ej. con la media de los embeddings, módulo 07) y entrenarlo. En el modelo base de Llama 3 se reportaron filas a cero para tokens de la plantilla de chat que podían causar gradientes NaN al afinar (⚠️ fuente secundaria: tarjeta de modelo comunitaria `imone/Llama-3-8B-fixed-special-embedding` y la charla de Unsloth en AI Engineer; no hay comunicado de Meta).
* **Las leyes de escala están en tokens de *un* tokenizer.** Chinchilla (70 B parámetros, 1.4 T tokens; ≈ 20 tokens por parámetro) se entrenó con un SentencePiece de 32 000 sin NFKC (Hoffmann et al., 2022, sección 4 y tarjeta del modelo). Copiar «20 tokens por parámetro» con otro tokenizer cambia la **cantidad de texto**: hay que convertir a bytes con los bytes/token de cada tokenizer sobre la misma mezcla.
""")
nb.code(r'''
def v_fisico(v_base: int, reservados: int = 0, multiplo: int = 128) -> int:
    return math.ceil((v_base + reservados) / multiplo) * multiplo

for nombre, vb, r, m in [("GPT-2 (nanoGPT)", 50257, 0, 64), ("Llama 3", 128000, 256, 128), (f"Políglota V*={V_opt}", V_opt, 64, 128)]:
    vf = v_fisico(vb, r, m); print(f"{nombre:22s} base={vb:>7,} + reservados={r:>3} -> físico={vf:>7,} (múltiplo de {m}; {vf - vb - r} filas de relleno)")

# La misma regla "20 tokens por parámetro" con dos tokenizers distintos = cantidades distintas de TEXTO
N_PARAM = 100e6
b_tok = {V: sum(len(x.encode()) for x in test_todo) / sum(len(TKS[V].encode(x).ids) for x in test_todo) for V in (VS[0], VS[-1])}
for V, b in b_tok.items(): print(f"V={V:>6}: {b:.2f} bytes/token -> 20 tokens/parámetro x {N_PARAM:.0e} = {20 * N_PARAM * b / 1e9:.1f} GB de texto")
print(f"Mismo 'presupuesto en tokens', {b_tok[VS[-1]] / b_tok[VS[0]]:.2f}x más texto con V={VS[-1]}: convierte siempre a bytes antes de comparar.")
''')
nb.md(r"""
> 👀 **Qué debes observar.** El relleno a múltiplo de 128 cuesta muy pocas filas; los 256 reservados de Llama 3 son ≈ 0.2 % del vocabulario. Abajo, la misma regla «tokens por parámetro» con dos vocabularios da cantidades de texto distintas: un plan de datos o una comparación entre laboratorios hecha en tokens sin decir el tokenizer **no es comparable**.
""")

nb.md(r"""
## 12. Resumen de decisiones de diseño

| Decisión | Pregunta que debes poder responder con datos | Herramienta de esta lección |
|---|---|---|
| Tamaño $V$ | ¿dónde está la rodilla *tokens/KB vs V* y cuánto pesan los embeddings? | secciones 4 y 11 |
| Mezcla de idiomas | ¿qué idioma paga más y es aceptable? | prima de tokens (sección 6) y experimento de mezcla |
| Números | ¿dígitos sueltos, grupos de 3 o R2L? | sección 8 |
| Código | ¿se colapsan los runs de espacios? ¿tabs? | sección 8 |
| Especiales y plantilla | ¿una única fuente de verdad para entrenar y servir? | sección 9 |
| ¿Cruzar palabras? | ¿ganancia > complejidad? (🟡) | sección 10 |
| Auditoría antes del preentrenamiento | ¿round-trip 100 %, Rényi, % de V visto, slots reservados, $V$ físico? | sección 11.1–11.3 |

""")

nb.md(r"""
## 13. Mapa de madurez

Con todo lo visto, esta tabla resume qué decisiones de diseño son estándar y cuáles emergentes.

Estado del arte a **oct-2026**; las cifras de vocabulario cambian con cada versión de modelo.

| Técnica / decisión | Madurez | Quién la usa (con respaldo) | Fuente |
|---|---|---|---|
| Vocabularios de 100–260 k (frente a 32 k) | 🟢 | cl100k ≈ 100 k y o200k ≈ 200 k (medido en la sección 5); Llama 3 = 128 256; Qwen2 = 151 643 + 3; Gemma ≈ 256 k | tiktoken; Land & Bartolo 2024; Qwen2 report; Gemma 3 report |
| Dígitos tratados aparte (sueltos o en grupos) | 🟢 | Llama 1/2 y Gemma 3: dígitos separados; GPT-3.5/4: grupos de hasta 3 dígitos | Touvron 2023; Gemma 3; Singh & Strouse 2024 |
| Tokenizador específico con código/indentación (espacios agrupados) | 🟢 | cl100k/o200k agrupan espacios; GPT-2 no (medido en la sección 8) | Dagan et al. 2024; medición propia |
| Vocabulario óptimo según presupuesto de cómputo (leyes de escala con V) | 🟡 | Resultados de NeurIPS 2024 a ≤ 3 B parámetros; extrapolación a modelos grandes no contrastada | Tao et al. 2024 |
| Equidad multilingüe del tokenizer (paridad) | 🟡 | Medida y reportada (p. ej. Tekken de Mistral frente al SentencePiece anterior); sin estándar común | Petrov et al. 2023; Ahia et al. 2023; anuncio de Mistral NeMo (2024) |
| Tokens que cruzan palabras (SuperBPE) | 🟡 / 🔴 | Resultados a 8 B, solo inglés; adopción en producción no verificada | Liu et al. 2025 (COLM) |
| Chat templates con tokens de control | 🟢 | Estándar de facto (ChatML, plantillas por modelo en `tokenizer_config`) | Docs de HF `transformers` |
""")

nb.md(r"""
## 14. 🏭 En producción

Cifras de vocabulario **a oct-2026** (ver tabla de la sección 5); verifica siempre contra el modelo exacto.

- **OpenAI.** `o200k_base` (GPT-4o) amplió el vocabulario de ≈ 100 k a ≈ 200 k; en nuestra medición reduce la prima de hindi de ≈ 4.9× a ≈ 1.6× y la de ruso de ≈ 2.1× a ≈ 1.25× frente a `cl100k` (mini-conjunto paralelo; repítelo con FLORES+).
- **Meta.** Llama 3 pasó de 32 000 (Llama 2) a 128 256 tokens y reporta una compresión sobre inglés de 3.17 → 3.94 caracteres/token.
- **Mistral.** Tekken (≈ 130 k + ≈ 1 k de control, basado en tiktoken, > 100 idiomas) sustituye al SentencePiece anterior (guía de tokenización de Mistral); el anuncio de Mistral NeMo (jul-2024) reporta ≈ 30 % más compresión en código fuente, chino, italiano, francés, alemán, español y ruso, 2x en coreano y 3x en árabe.
- **Google.** Gemma usa vocabularios de ≈ 256 k con dígitos separados y bytes; la proporción de parámetros en embeddings es muy alta en los modelos pequeños (gráfico de la sección 4).
- **Cohere.** Command R/R+ usan 255 029 tokens con embeddings atados (tabla 1 de Land & Bartolo 2024); Cohere publicó además el análisis de tokens sub-entrenados que verás en el módulo 05.
- **Coste real.** Facturación por token + paridad = **prima de precio por idioma** (Ahia et al., 2023). Antes de comprometer un contrato de API para un producto multilingüe, **mide tus textos con el tokenizer del proveedor** y proyecta el coste por idioma.
- **Auditoría antes de preentrenar.** Lo habitual es congelar el tokenizer tras una batería como la de la sección 11.1 (round-trip, compresión y prima por idioma, uso del vocabulario, especiales) sobre la mezcla de datos **del modelo**; los informes técnicos casi nunca publican el protocolo completo, pero sí sus consecuencias (p. ej. los 256 reservados de Llama 3 o el relleno a múltiplos de 64/128 de `nanoGPT`).
- **Evaluación independiente.** Compara tokenizers con un corpus que **no** se usó para entrenarlos (FLORES+, por ejemplo) y siempre sobre *contenido paralelo*.
""")

nb.md(r"""
## 15. 🧠 Secretos de la élite

1. **Compara en bits por byte, no por token.** Perplexidad/pérdida por token no es comparable entre vocabularios distintos; Tao et al. (2024) usan una pérdida normalizada por carácter para sus leyes de escala.
2. **El vocabulario óptimo crece con el cómputo, y los modelos reales están por debajo.** Tao et al. predicen ≥ 216 K para Llama2-70B frente a los 32 K reales; los vocabularios 100–260 k de 2024–2026 van en esa dirección (🟡: resultado a ≤ 3 B parámetros).
3. **El tokenizer es la unidad de tus leyes de escala.** «≈ 20 tokens por parámetro» (Chinchilla: 70 B, 1.4 T tokens) se midió con un SentencePiece de 32 000 sin NFKC (Hoffmann et al., 2022). Con otro tokenizer, el mismo número de tokens es otra cantidad de texto (sección 11.3): los planes de datos y las comparaciones entre laboratorios se hacen en **bytes**, o declarando el tokenizer.
4. **Reservado no es entrenado.** Llama 3 deja 256 ids especiales (128 000 + 256 = 128 256, múltiplo de 128) para crecer sin redimensionar; pero un slot que nunca apareció en el preentrenamiento llega al fine-tuning sin entrenar. Inicialízalo (media de embeddings, módulo 07) y vigila los NaN. Y la fertilidad no basta para auditar: añade Rényi (Zouhar et al., 2023), sabiendo que se puede «trampear» (Cognetta et al., 2024).
5. **La pre-tokenización de números cambia la aritmética.** Singh & Strouse (2024): tokenización R2L sube la suma de 75.6 % a 97.8 % en GPT-3.5 (8-shot; efecto menor pero presente en GPT-4, marzo 2023); es un cambio de *una línea de regex* con efecto medible.
6. **El espacio en blanco se paga en tokens.** Con GPT-2 la indentación cuesta ≈ 15 tokens extra por línea a 16 espacios; la agrupación de `cl100k`/`o200k` la deja en ≈ 1 (medido arriba, sobre código Python real).
7. **Cambiar el tokenizer de un modelo ya entrenado es caro.** Dagan et al. (2024) reportan que especializar el tokenizer de un modelo preentrenado tras afinarlo con más de 50 B de tokens da ganancias grandes de velocidad y contexto efectivo, pero ese volumen de datos ilustra el coste (módulo 07); por eso se diseña bien a la primera.
8. **Tokenizers que cruzan palabras (SuperBPE) comprimen más con el mismo vocabulario**, pero la evidencia de mejora de modelo viene de un único grupo a 8 B en inglés (🟡).
""")

nb.md(r"""
## 16. ⚠️ Errores comunes

1. Medir la paridad con **texto no paralelo** (los idiomas tienen densidad de información distinta) o con muy pocas frases.
2. **Comparar perplexidades por token** entre tokenizers.
3. Fijar `V` «porque lo usa Llama» sin mirar el presupuesto de parámetros ni el tráfico por idioma.
4. Entrenar el tokenizer con el **corpus natural** (80 % inglés) y sorprenderse del coste en español.
5. Olvidar los **tokens especiales** en el vocabulario del modelo (fila de embedding no inicializada o sin entrenar → módulo 05).
6. Usar una **plantilla de chat distinta** en entrenamiento y en servicio, o duplicar BOS.
7. Cambiar la regex de pre-tokenización de números/espacios **después** de entrenar el modelo.
8. Citar precios y tamaños de vocabulario sin fecha: cambian cada versión.
""")

nb.md(r"""
## 17. Autoevaluación

<details><summary><b>1 · (Cálculo)</b> Un modelo con L = 32, d = 4096 y V = 128 256 sin weight tying: ¿cuántos parámetros hay en embeddings y qué fracción son del total?</summary>

$N_{\text{no-emb}}\approx12\cdot32\cdot4096^2\approx6.44\times10^9$; $N_{\text{emb}}=2\cdot128256\cdot4096\approx1.05\times10^9$; total ≈ 7.49 B → **≈ 14 %** en embeddings. (Es una aproximación genérica: GQA/SwiGLU cambian constantes.)
</details>

<details><summary><b>2 · (Cálculo)</b> Un texto español mide 2 000 bytes. Con β = 4.0 bytes/token cuesta 500 tokens; con β = 3.2 cuesta 625. Si la API cobra 1 USD por millón de tokens y procesas 10 M de textos así al mes, ¿cuánto cuesta cada opción?</summary>

500 tok × 10 M = 5 000 M tok → **5 000 USD**; 625 tok × 10 M = 6 250 M tok → **6 250 USD** (+25 %). Un tokenizer con 25 % más de tokens cuesta 25 % más (y consume 25 % más de ventana).
</details>

<details><summary><b>3 · (Diagnóstico)</b> Tu clasificador multilingüe rinde peor en hindi que en español aunque tiene el mismo nº de ejemplos. El tokenizer es cl100k. ¿Qué miras primero?</summary>

La **prima de tokens** (hindi ≈ 4.9× en nuestra medición con cl100k): las secuencias hindi son mucho más largas (truncan antes en `max_length`, diluyen la atención) y los tokens por byte son casi bytes sueltos. Mide longitudes de secuencia y tasa de truncamiento por idioma; considera un tokenizer con mejor paridad (o200k, Tekken…) o ampliar `max_length` para hindi.
</details>

<details><summary><b>4 · (Diagnóstico)</b> Tras cambiar la plantilla de chat de tu servicio, la calidad cae 3 puntos sin errores en logs. ¿Causa probable?</summary>

Divergencia entre la plantilla de entrenamiento y la de servicio (un `\n`, un espacio, falta de `add_generation_prompt`, doble BOS). Compara byte a byte la cadena y los ids producidos en servicio con un ejemplo del dataset de post-entrenamiento.
</details>

<details><summary><b>5 · (Transferencia)</b> Políglota añadirá portugués y quiere mantener V ≈ 32 k para un embedder pequeño. ¿Qué haces?</summary>

Mides la prima actual de pt con un corpus paralelo (FLORES+), reentrenas con mezcla suavizada (temperatura) que suba el peso del portugués y barres V (p. ej. 24 k–48 k) con la función de coste J; decides con tráfico esperado y presupuesto de parámetros. Si el vocabulario viejo ya está en producción, evalúas el coste de re-indexar (módulos 07 y 18).
</details>

<details><summary><b>6 · (Transferencia)</b> ¿Adoptarías SuperBPE en Políglota? Argumenta.</summary>

Pros: ≈ 6–7 % menos tokens a igual V en nuestra escala (hasta ≈ 33 % reportado con 200 k), menos coste y más contexto. Contras: evidencia 🟡 (8 B, solo inglés), tokenizer más pesado de entrenar, riesgo de superpalabras de boilerplate, y un buscador con BM25/embeddings por token se beneficia de granularidad de palabra para *matching*. Haría un A/B sobre el golden set antes de adoptarlo.
</details>

<details><summary><b>7 · (Recuerdo)</b> ¿Por qué se compara en «bits por byte» entre tokenizers?</summary>

Porque la pérdida por token depende de cuánto texto cubre cada token; normalizando por bytes/caracteres la comparación es independiente del vocabulario.
</details>
""")

nb.md(r"""
## 18. Referencias

**Papers (verificados: autores, título, venue y enlace; revisados el 26-oct-2026)**
- Tao, C. et al. (2024). *Scaling Laws with Vocabulary: Larger Models Deserve Larger Vocabularies.* NeurIPS 2024. <https://arxiv.org/abs/2407.13623>
- Petrov, A., La Malfa, E., Torr, P. y Bibi, A. (2023). *Language Model Tokenizers Introduce Unfairness Between Languages.* NeurIPS 2023. <https://arxiv.org/abs/2305.15425>
- Ahia, O. et al. (2023). *Do All Languages Cost the Same? Tokenization in the Era of Commercial Language Models.* EMNLP 2023. <https://arxiv.org/abs/2305.13707>
- Liu, A., Hayase, J., Hofmann, V., Oh, S., Smith, N. A. y Choi, Y. (2025). *SuperBPE: Space Travel for Language Models.* COLM 2025. <https://arxiv.org/abs/2503.13423>
- Singh, A. K. y Strouse, D. J. (2024). *Tokenization counts: the impact of tokenization on arithmetic in frontier LLMs.* Preprint. <https://arxiv.org/abs/2402.14903>
- Dagan, G., Synnaeve, G. y Rozière, B. (2024). *Getting the most out of your tokenizer for pre-training and domain adaptation.* ICML 2024. <https://arxiv.org/abs/2402.01035>
- Rust, P. et al. (2021). *How Good is Your Tokenizer? On the Monolingual Performance of Multilingual Language Models.* ACL 2021. <https://arxiv.org/abs/2012.15613>
- Goldman, O. et al. (2024). *Unpacking Tokenization: Evaluating Text Compression and its Correlation with Model Performance.* Findings of EMNLP 2024. <https://arxiv.org/abs/2403.06265>
- Schmidt, C. W. et al. (2024). *Tokenization Is More Than Compression.* EMNLP 2024. <https://arxiv.org/abs/2402.18376>
- Land, S. y Bartolo, M. (2024). *Fishing for Magikarp: Automatically Detecting Under-trained Tokens in Large Language Models.* EMNLP 2024. <https://arxiv.org/abs/2405.05417> (tabla de vocabularios)
- Llama Team (2024). *The Llama 3 Herd of Models.* <https://arxiv.org/abs/2407.21783> · Gemma Team (2024). *Gemma 2: Improving Open Language Models at a Practical Size.* <https://arxiv.org/abs/2408.00118> · Gemma Team (2025). *Gemma 3 Technical Report.* <https://arxiv.org/abs/2503.19786> · Yang et al. (2024). *Qwen2 Technical Report.* <https://arxiv.org/abs/2407.10671>
- Zouhar, V., Meister, C., Gastaldi, J. L., Du, L., Sachan, M. y Cotterell, R. (2023). *Tokenization and the Noiseless Channel.* ACL 2023. <https://arxiv.org/abs/2306.16842>
- Cognetta, M., Zouhar, V., Moon, S. y Okazaki, N. (2024). *Two Counterexamples to Tokenization and the Noiseless Channel.* LREC-COLING 2024. <https://arxiv.org/abs/2402.14614>
- Hoffmann, J. et al. (2022). *Training Compute-Optimal Large Language Models* (Chinchilla). NeurIPS 2022. <https://arxiv.org/abs/2203.15556>
- Conneau, A. et al. (2019). *Unsupervised Cross-lingual Representation Learning at Scale.* ACL 2020. <https://arxiv.org/abs/1911.02116>
- Touvron, H. et al. (2023). *LLaMA: Open and Efficient Foundation Language Models.* <https://arxiv.org/abs/2302.13971>

**Datos, librerías y docs**
- FLORES+ (`openlanguagedata/flores_plus`) y `Helsinki-NLP/opus-100` en Hugging Face Datasets; `tiktoken` <https://github.com/openai/tiktoken>; Mistral, guía de tokenización <https://docs.mistral.ai/guides/tokenization/> y anuncio de Mistral NeMo <https://mistral.ai/news/mistral-nemo/>; `nanoGPT` (`model.py`, relleno de `vocab_size` a 50 304) <https://github.com/karpathy/nanoGPT>; tokenizer de Llama 3 (`llama/tokenizer.py`, `num_reserved_special_tokens = 256`) <https://github.com/meta-llama/llama3>; tarjeta comunitaria `imone/Llama-3-8B-fixed-special-embedding` (fuente secundaria sobre filas a cero).

**Siguiente:** módulo 05 (qué falla cuando el vocabulario y los datos del modelo no coinciden: glitch tokens, números, letras, Unicode).
""")
nb.save(os.path.join(MOD_DIR, f"{SLUG}.ipynb"))

# =====================================================================================
#                                       PROYECTO
# =====================================================================================
pj = Notebook("Proyecto 04 · Benchmark de tokenizers y vocabulario de Políglota", colab_path=PROJ_REL)
pj.md(pj.badge() + r"""

# Proyecto 04 · Benchmark de fertilidad/paridad y diseño del vocabulario de Políglota

| | |
|---|---|
| **Nivel** | 🟠 Avanzado |
| **Duración estimada** | ≈ 2 h |
| **GPU recomendada** | Ninguna (CPU, `FAST_DEV_RUN = True`) |
| **Prerrequisitos** | Lección del módulo 04 y proyecto 03 |

## Contexto de negocio
Políglota Labs va a **entrenar su propio embedder** y necesita congelar el vocabulario. Tu CTO pide dos entregables: **(A)** un benchmark honesto de los tokenizers candidatos (los públicos y el tuyo) en **ES / EN / código** y en otros idiomas con texto paralelo,
y **(B)** una **receta de vocabulario** (mezcla de corpus + tamaño $V$) justificada con una función de coste con el tráfico esperado (50 % ES, 30 % EN, 20 % código).

> **Conexión.** Viene del proyecto 03 (entrenaste y comparaste algoritmos con un pipeline idéntico). Va hacia el módulo 05 (cómo falla un vocabulario) y, más adelante, hacia el embedder de Políglota (módulos 09–11), que **hereda** este vocabulario.

## Dataset
Corpus Políglota (`carga_corpus`: HF → espejo Europarl + stdlib → sintético) y texto paralelo (`carga_paralelo`: FLORES+ → opus-100 → 16 frases × 12 idiomas escritas a mano; avisa en pantalla).

## Entregables y rúbrica
1. `benchmark(registro, par)`: tabla de **prima de tokens** y **bytes/token** por tokenizer e idioma (+ `tokens_por_kb` en ES/EN/código).
2. `entrena_candidato(prop, V)` y `evalua_candidato(tok)` → tokens por KB por idioma.
3. `selecciona(...)`: barrido de mezclas × V y elección por la función de coste $J$.
4. Un archivo `poliglota_vocab.json` con la receta y las métricas, y una decisión escrita.

La rúbrica puntúa de forma automática. Umbrales calibrados con **lo que mide la solución de referencia** (corpus espejo, `FAST_DEV_RUN=True`, mini-conjunto paralelo) menos un margen; los criterios *relativos* se sostienen con otros datos, los absolutos se relajan.
""")
pj.code(C.pip_cell())
pj.code(C.SETUP.strip("\n"))
for _c in C.cells(C.CORPUS_1) + C.cells(C.CORPUS_2):
    pj.code(_c)
pj.code(C.CORPUS_USE.strip("\n"))
for _c in C.cells(C.PARALELO):
    pj.code(_c)
pj.code(C.PARALELO_LOADER.strip("\n") + "\n\npar = carga_paralelo(fast_dev=FAST_DEV_RUN)\nprint('paralelo:', par['source'], '| frases:', par['n'], '| idiomas:', list(par['langs']))")
pj.code(C.METRICS.strip("\n") + "\n" + C.TOKMETRICS.strip("\n"))
pj.code(TIK_CELL.strip("\n"))
pj.code(r'''
import pandas as pd
from tokenizers import Tokenizer, models, pre_tokenizers, normalizers, trainers, decoders, Regex
from tokenizers.pre_tokenizers import ByteLevel
rng = random.Random(SEED); train_docs, test_docs = [], []
for lang in ["es", "en", "code"]:
    pool = [d for d in docs if d["lang"] == lang]; rng.shuffle(pool); cut = int(0.8 * len(pool))
    train_docs += pool[:cut]; test_docs += pool[cut:]
test_by_lang = {l: [d["text"] for d in test_docs if d["lang"] == l] for l in ["es", "en", "code"]}

def entrena_bpe_bytes(textos, vocab_size: int) -> Tokenizer:
    """Byte-level BPE (regex GPT-2). Es el 'tokenizer propio' de Políglota (módulos 02-03)."""
    PAT = r"""'(?:[sdmt]|ll|ve|re)| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""
    t = Tokenizer(models.BPE())
    t.pre_tokenizer = pre_tokenizers.Sequence([pre_tokenizers.Split(Regex(PAT), behavior="isolated"), ByteLevel(add_prefix_space=False, use_regex=False)])
    t.decoder = decoders.ByteLevel()
    t.train_from_iterator(textos, trainers.BpeTrainer(vocab_size=vocab_size, initial_alphabet=ByteLevel.alphabet(), special_tokens=["<|endoftext|>"]))
    return t

def corpus_mezcla(prop: dict, total_chars: int, semilla: int = SEED) -> list:
    """Muestrea documentos de train por idioma hasta total_chars*prop[idioma] caracteres."""
    r = random.Random(semilla); out = []
    for lang, p in prop.items():
        pool = [d["text"] for d in train_docs if d["lang"] == lang]; acc = 0
        while acc < p * total_chars:
            t = r.choice(pool); out.append(t); acc += len(t)
    r.shuffle(out); return out

TOTAL = 400_000 if FAST_DEV_RUN else 4_000_000
TRAFICO = {"es": 0.5, "en": 0.3, "code": 0.2}          # supuesto de producto
LAMBDA = 3.0                                           # penalización de vocabulario (tokens/KB por cada 1 k de V)
natural = {"en": 0.80, "es": 0.15, "code": 0.05}
suav = {k: v ** 0.3 / sum(u ** 0.3 for u in natural.values()) for k, v in natural.items()}
MEZCLAS = {"natural": natural, "suavizada": suav, "equilibrada": {"en": 1 / 3, "es": 1 / 3, "code": 1 / 3}, "sesgo_es": {"en": 0.2, "es": 0.6, "code": 0.2}}
VS = [2000, 4000, 8000] if FAST_DEV_RUN else [8000, 16000, 32000]
def intenta(f, *a, **k):
    try: return f(*a, **k)
    except NotImplementedError as e: print("⏳ pendiente:", e); return None
REG = {f"tiktoken {n.replace('_base','')}": (lambda s, e=e: e.encode_ordinary(s)) for n, e in TIK.items()}
REG["BPE propio (natural)"] = (lambda tk: (lambda s: tk.encode(s).ids))(entrena_bpe_bytes(corpus_mezcla(natural, TOTAL), VS[1]))
print(list(REG))
''')

pj.md(r"""
## Paso 1 · Benchmark de paridad

**TODO.** Implementa `benchmark(registro, par)` → `DataFrame` con una fila por (tokenizer, idioma) y columnas `tokens`, `premium` (= tokens del idioma / tokens del inglés) y `bytes_por_token`. Después `tokens_por_kb(registro)` → DataFrame con tokens por KB de texto de test en `es`, `en` y `code` (usa `test_by_lang`).

<details><summary>🪜 Pista 1</summary>

Para cada idioma suma `len(enc(frase))` sobre todas las frases paralelas; la prima divide entre el total del inglés. `bytes_por_token` = bytes UTF-8 totales / tokens totales.
</details>
<details><summary>🪜 Pista 2</summary>

`tot = {l: sum(len(enc(s)) for s in par["langs"][l]) for l in par["langs"]}`; `byt = {l: sum(len(s.encode()) for s in par["langs"][l]) ...}`; en `tokens_por_kb`: `1000 * tokens / bytes` por idioma sobre `test_by_lang[l]`.
</details>
""")
pj.code(r'''
def benchmark(registro: dict, par: dict) -> pd.DataFrame:
    # TODO: filas {"tokenizer","idioma","tokens","premium","bytes_por_token"}
    raise NotImplementedError("TODO paso 1a")

def tokens_por_kb(registro: dict) -> pd.DataFrame:
    # TODO: índice = tokenizer, columnas = es/en/code (tokens por KB de texto de test)
    raise NotImplementedError("TODO paso 1b")

dp = intenta(benchmark, REG, par); tk_kb = intenta(tokens_por_kb, REG)
if dp is not None: print(dp.pivot_table(index="tokenizer", columns="idioma", values="premium").round(2).to_string())
if tk_kb is not None: print(tk_kb.round(1))
''')

pj.md(r"""
## Paso 2 · Candidatos de vocabulario

**TODO.** `evalua_candidato(tok)` devuelve `{"es": tokens/KB, "en": ..., "code": ...}` sobre el test; `entrena_candidato(prop, V)` entrena un BPE byte-level con el corpus `corpus_mezcla(prop, TOTAL)` y tamaño `V`.

<details><summary>🪜 Pista 1</summary>

Son dos líneas cada una, reutilizando `entrena_bpe_bytes`, `corpus_mezcla` y `test_by_lang`; en tokens/KB usa `1000 * tokens / bytes`.
</details>
<details><summary>🪜 Pista 2</summary>

`entrena_bpe_bytes(corpus_mezcla(prop, TOTAL), V)`; y `{l: 1000 * sum(len(tok.encode(t).ids) for t in test_by_lang[l]) / sum(len(t.encode()) for t in test_by_lang[l]) for l in ("es", "en", "code")}`. Es lo mismo que hiciste en la lección (§11) con la mezcla suavizada.
</details>
""")
pj.code(r'''
def evalua_candidato(tok: Tokenizer) -> dict:
    # TODO: tokens por KB en es/en/code (test)
    raise NotImplementedError("TODO paso 2a")

def entrena_candidato(prop: dict, V: int) -> Tokenizer:
    # TODO: BPE byte-level con corpus de la mezcla `prop` y tamaño V
    raise NotImplementedError("TODO paso 2b")
''')

pj.md(r"""
## Paso 3 · Selección por coste

**TODO.** `selecciona(mezclas, vs)` entrena todas las combinaciones, calcula para cada una
$J=\sum_\ell w_\ell\cdot\text{tokens/KB}_\ell+\lambda\,V/1000$ (con `TRAFICO` y `LAMBDA`) y la **peor razón** entre idiomas $\max_\ell \text{tpk}_\ell/\min_\ell \text{tpk}_\ell$ (equidad), y devuelve un `DataFrame` con columnas `mezcla, V, tpk_es, tpk_en, tpk_code, J, desbalance`, ordenado por `J`.

<details><summary>🪜 Pista 1</summary>

Doble bucle `for nombre, prop in mezclas.items(): for V in vs:` + `evalua_candidato(entrena_candidato(prop, V))`.
</details>
<details><summary>🪜 Pista 2</summary>

`J = sum(TRAFICO[l] * t[l] for l in t) + LAMBDA * V / 1e3`; `desbalance = max(t.values()) / min(t.values())`.
</details>
""")
pj.code(r'''
def selecciona(mezclas: dict, vs: list) -> pd.DataFrame:
    # TODO: barrido mezclas x V; columnas mezcla, V, tpk_es, tpk_en, tpk_code, J, desbalance; ordenado por J
    raise NotImplementedError("TODO paso 3")

cand = intenta(selecciona, MEZCLAS, VS)
if cand is not None: print(cand.round(2).to_string(index=False))
''')

pj.md(r"""
## Paso 4 · La receta

**TODO.** Escribe `poliglota_vocab.json` con `{"mezcla": ..., "V": ..., "tokens_por_kb": {...}, "J": ..., "justificacion": "..."}` (justificación ≥ 300 caracteres con **≥ 3 cifras** y **un riesgo**: p. ej. qué idioma pierde con tu elección y qué harías si el tráfico cambia).

<details><summary>🪜 Pista 1</summary>

La fila ganadora es `cand.iloc[0]` (ya está ordenado por `J`); de ahí salen `mezcla`, `V`, `J` y los `tpk_*`. Guarda con `json.dump(receta, open("poliglota_vocab.json", "w"), ensure_ascii=False, indent=2)`.
</details>
<details><summary>🪜 Pista 2</summary>

Para la justificación compara la ganadora con la mezcla **natural** al mismo `V` (cuánto baja `J` en %), cita el `desbalance` y nombra el idioma con más tokens/KB como riesgo. Plantilla: «Elegimos … porque J baja de … a … (−…%) … El desbalance es … El riesgo es …; si el tráfico de … sube, …».
</details>
""")
pj.code(r'''
receta = {}      # TODO: dict con la receta (ver enunciado)
''')

pj.md(r"""
## Rúbrica (autoevaluación)

Referencia medida (corpus espejo, `FAST_DEV_RUN=True`): prima del hindi con cl100k ≈ 4.9 (umbral > 3.0); mejor candidato J ≈ 269 frente a ≈ 303 de la mezcla natural con V = 4 000 (−11 %; umbral −8 %); desbalance del mejor ≈ 1.2 (umbral ≤ 1.35).
""")
pj.code(r'''
def rubrica():
    R = []; ok = lambda nombre, cond, pts: R.append((nombre, bool(cond), pts))
    ok("1a · benchmark devuelve prima 1.0 para el inglés en todos los tokenizers", dp is not None and np.allclose(dp[dp.idioma == "en"]["premium"], 1.0), 2)
    if dp is not None and "tiktoken o200k" in set(dp.tokenizer) and "tiktoken cl100k" in set(dp.tokenizer):
        P = dp.pivot_table(index="tokenizer", columns="idioma", values="premium")
        ok("1a · o200k reduce la prima media (no-inglés) frente a cl100k", P.loc["tiktoken o200k"].mean() < P.loc["tiktoken cl100k"].mean(), 2)
        ok("1a · la prima del hindi con cl100k > UMBRAL_HI (n pequeño: orientativo)", P.loc["tiktoken cl100k"].get("hi", 0) > UMBRALES["hi_cl100k"], 1)
    else:
        ok("1a · tiktoken disponible (o200k y cl100k)", False, 3)
    ok("1b · tokens por KB calculados para es/en/code", tk_kb is not None and {"es", "en", "code"} <= set(tk_kb.columns), 2)
    ok("3 · el barrido devuelve mezclas × V ordenado por J", cand is not None and len(cand) == len(MEZCLAS) * len(VS) and cand["J"].is_monotonic_increasing, 2)
    if cand is not None and len(cand):
        mejor = cand.iloc[0]; base = cand[(cand.mezcla == "natural") & (cand.V == VS[1])]["J"].iloc[0]
        ok(f"3 · el mejor candidato mejora a 'natural'@V={VS[1]} en ≥ {UMBRALES['mejora_J']:.0%} de J", mejor["J"] <= base * (1 - UMBRALES["mejora_J"]), 2)
        ok("3 · el mejor candidato NO es la mezcla 'natural' (con este tráfico 50/30/20)", mejor["mezcla"] != "natural", 1)
        ok(f"3 · desbalance del mejor ≤ {UMBRALES['desbalance']}", mejor["desbalance"] <= UMBRALES["desbalance"], 1)
    else:
        ok("3 · candidatos", False, 4)
    ok("4 · receta con mezcla, V y J", {"mezcla", "V", "J"} <= set(receta), 1)
    j = str(receta.get("justificacion", ""))
    ok("4 · justificación ≥ 300 caracteres con ≥ 3 cifras", len(j) >= 300 and len(re.findall(r"\d+[.,]?\d*", j)) >= 3, 2)
    tot = sum(p for _, _, p in R); got = sum(p for _, c, p in R if c)
    for nombre, c, p in R: print(("✅" if c else "⬜"), f"[{p}]", nombre)
    print(f"\nPuntuación: {got}/{tot}")
UMBRALES = {"hi_cl100k": 3.0, "mejora_J": 0.08, "desbalance": 1.35}
rubrica()
''')

pj.md(r"""
## ⛔ SPOILER — intenta resolverlo primero

Debajo está la solución de referencia completa; al ejecutarla se redefinen las funciones y la rúbrica final puntúa la referencia.
""")
pj.code(r'''
def benchmark(registro: dict, par: dict) -> pd.DataFrame:
    langs = list(par["langs"]); filas = []
    for nombre, enc in registro.items():
        tot = {l: sum(len(enc(s)) for s in par["langs"][l]) for l in langs}
        byt = {l: sum(len(s.encode("utf-8")) for s in par["langs"][l]) for l in langs}
        for l in langs: filas.append({"tokenizer": nombre, "idioma": l, "tokens": tot[l], "premium": tot[l] / tot["en"], "bytes_por_token": byt[l] / tot[l]})
    return pd.DataFrame(filas)

def tokens_por_kb(registro: dict) -> pd.DataFrame:
    out = {}
    for nombre, enc in registro.items():
        out[nombre] = {l: 1000 * sum(len(enc(t)) for t in test_by_lang[l]) / sum(len(t.encode()) for t in test_by_lang[l]) for l in ["es", "en", "code"]}
    return pd.DataFrame(out).T

dp = benchmark(REG, par); tk_kb = tokens_por_kb(REG)
print(dp.pivot_table(index="tokenizer", columns="idioma", values="premium").round(2).to_string()); print(tk_kb.round(1))

def evalua_candidato(tok: Tokenizer) -> dict:
    return {l: 1000 * sum(len(tok.encode(t).ids) for t in test_by_lang[l]) / sum(len(t.encode()) for t in test_by_lang[l]) for l in ["es", "en", "code"]}

def entrena_candidato(prop: dict, V: int) -> Tokenizer:
    return entrena_bpe_bytes(corpus_mezcla(prop, TOTAL), V)

def selecciona(mezclas: dict, vs: list) -> pd.DataFrame:
    filas = []
    for nombre, prop in mezclas.items():
        for V in vs:
            t = evalua_candidato(entrena_candidato(prop, V))
            J = sum(TRAFICO[l] * t[l] for l in t) + LAMBDA * V / 1e3
            filas.append({"mezcla": nombre, "V": V, "tpk_es": t["es"], "tpk_en": t["en"], "tpk_code": t["code"], "J": J, "desbalance": max(t.values()) / min(t.values())})
    return pd.DataFrame(filas).sort_values("J").reset_index(drop=True)

cand = selecciona(MEZCLAS, VS); print(cand.round(2).to_string(index=False))
''')
pj.code(r'''
mejor = cand.iloc[0]; nat = cand[(cand.mezcla == "natural") & (cand.V == VS[1])].iloc[0]
receta = {"mezcla": mejor["mezcla"], "V": int(mejor["V"]), "J": float(mejor["J"]),
          "tokens_por_kb": {l: float(mejor[f"tpk_{l}"]) for l in ["es", "en", "code"]},
          "justificacion": (f"Elijo la mezcla '{mejor['mezcla']}' con V={int(mejor['V'])}: J={mejor['J']:.1f} frente a {nat['J']:.1f} de la mezcla natural 80/15/5 con V={VS[1]} "
                            f"({1 - mejor['J'] / nat['J']:.0%} menos). Con el tráfico 50 % ES / 30 % EN / 20 % código el español necesita {mejor['tpk_es']:.0f} tokens/KB (frente a {nat['tpk_es']:.0f} con la natural). "
                            f"Riesgo: el inglés pasa de {nat['tpk_en']:.0f} a {mejor['tpk_en']:.0f} tokens/KB y no se evaluó ningún idioma fuera de ES/EN/código (el BPE propio cuesta casi un token por byte en ruso/hindi/árabe según el benchmark de paridad); "
                            f"si el tráfico cambia o se añaden idiomas hay que reentrenar con λ y pesos nuevos antes de congelar el vocabulario del embedder.")}
import json; json.dump(receta, open("poliglota_vocab.json", "w"), ensure_ascii=False, indent=2)
print(json.dumps({k: v for k, v in receta.items() if k != "justificacion"}, indent=1), "| justificación:", len(receta["justificacion"]), "caracteres")
rubrica()
''')
pj.md(r"""
## Retos extra (nivel experto)

1. **Equidad explícita.** Añade a $J$ un término de equidad (p. ej. $\mu\cdot(\text{peor prima}-1)$) y mira cómo cambia la mezcla ganadora; ¿qué $\mu$ iguala ES y EN?
2. **Más idiomas.** Con `carga_paralelo` (FLORES+ si tienes acceso) añade pt/fr/de a la mezcla y mide la prima de hi/ar/ja con y sin ellos.
3. **SuperBPE para Políglota.** Reutiliza la implementación de la lección y compara bytes/token y el nDCG@10 de BM25 (proyecto 03) con BPE a igual $V$.
4. **Dígitos.** Entrena con dígitos sueltos vs. grupos de 3 (cambia la regex) y mide tokens/KB en un corpus numérico (facturas, logs).
5. **Plantilla de chat de Políglota.** Diseña los tokens especiales (roles, `<|doc|>`, `<|code|>`) y escribe un test que verifique que servir y entrenar producen los mismos ids.

## Reflexión (producción y Políglota)

- ¿Qué métrica de tokenización pondrías en el dashboard de producción (por idioma) y qué umbral dispararía una alerta?
- Si un cliente grande exige soporte de japonés/hindi, ¿cuál es tu plan *sin* reentrenar el embedder? (Pista: módulo 07, tokenizer transfer.)
- ¿Cómo repartirías el presupuesto de parámetros entre vocabulario y capas para el embedder pequeño de Políglota?
""")
pj.save(os.path.join(MOD_DIR, "04_proyecto_diseno_tokenizers_modernos.ipynb"))
