"""Genera el módulo 00_intro: README + lección + proyecto.   Ejecutar desde la raíz del repo:
    python tokenization-embeddings-course/_tools/builders/build_00.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]  # tokenization-embeddings-course/
sys.path.insert(0, str(ROOT / "_tools"))
sys.path.insert(0, str(ROOT / "_tools" / "builders"))
from a1_common import SRC_GPT2, SRC_PLOT_STYLE, caja, details, mapa_madurez, obs, pista, preguntas  # noqa: E402
from nbbuild import Notebook  # noqa: E402
from poliglota_utils import SRC_BM25, SRC_METRICS, src_corpus_cells  # noqa: E402

MOD = ROOT / "00_intro"
MOD.mkdir(exist_ok=True)
(MOD / "assets").mkdir(exist_ok=True)
(MOD / "assets" / ".gitkeep").touch()
REL = "tokenization-embeddings-course/00_intro"

# ════════════════════════════════════════════════════════════════════════════
#  LECCIÓN
# ════════════════════════════════════════════════════════════════════════════
LPATH = f"{REL}/00_intro.ipynb"
nb = Notebook("Módulo 00 · Intro, entorno e hilo conductor", colab_path=LPATH)

nb.md(nb.badge() + r"""

# Módulo 00 · Intro, entorno e hilo conductor
**Tokenización y Embeddings: de BPE a los modelos modernos**

| | |
|---|---|
| **Nivel** | 🟢 Básico |
| **Duración estimada** | ≈ 2 h en total (lección ≈ 1 h + proyecto ≈ 1 h) |
| **GPU recomendada** | Ninguna: todo corre en CPU (0 unidades de cómputo de Colab Pro) |
| **Prerrequisitos** | Ninguno dentro del curso. Se asume Python sólido, PyTorch, Transformers y álgebra lineal/probabilidad |

> **Estado del arte de referencia: octubre de 2026.** Toda cifra sujeta a cambio lleva fecha; las técnicas se etiquetan 🟢 sólido / 🟡 emergente / 🔴 experimental.
""")

nb.md(r"""
## Objetivos de aprendizaje
Al terminar este módulo podrás:

1. **Describir** el pipeline completo *texto → bytes → tokens → ids → embeddings → índice → ranking* y situar cada módulo del curso en él.
2. **Distinguir** token (unidad discreta de un vocabulario) de embedding (vector aprendido asociado a una unidad o a un texto) con un ejemplo numérico.
3. **Configurar** el entorno de Colab del curso (semilla, `device`, `FAST_DEV_RUN`) y **reemplazar** correctamente las celdas 🎨/🎬 de Gemini por imágenes/videos en `assets/`.
4. **Cargar** el corpus Políglota con `carga_corpus()` (cadena oficial → espejo → sintético) e **interpretar** su esquema.
5. **Implementar** nDCG@k, Recall@k y MRR@k con el tratamiento correcto de empates, duplicados y consultas sin relevantes.
6. **Construir** un baseline BM25 con índice invertido, **validarlo** contra `rank_bm25` y **medir** su nDCG@10 por idioma con un intervalo de confianza bootstrap.
7. **Diagnosticar** por qué un baseline léxico falla (idioma, vocabulario, tokenización) y cómo eso motiva los módulos siguientes.
""")

nb.md(r"""
## 1. El mapa del curso
El curso tiene **21 módulos (00–20, ≈ 104 h)** y dos bloques: primero entendemos cómo un texto se convierte en **tokens** (bloque A) y luego cómo los tokens y los textos se convierten en **embeddings** que se pueden indexar y buscar (bloque B). Todo converge en **Políglota**, un buscador semántico multilingüe (ES/EN/código).

```text
 BLOQUE A · Texto y tokenización                         BLOQUE B · Embeddings
 00 Intro ─ 01 Unicode/bytes ─ 02 BPE ─ 03 WordPiece/    09 Capa de embedding ─ 10 Contextuales ─ 11 Contrastivo
 Unigram/SentencePiece ─ 04 Diseño ─ 05 Patologías ─     12 Embedders modernos ─ 13 Dense/sparse/late ─ 14 ANN
 06 Bytes/BLT ─ 07 H-Net/transfer ─ 08 Multimodal/audio  15 Evaluación ─ 16 Multimodal ─ 17 Interpretabilidad
                                                         18 Producción ─ 19 Playbook ─ 20 Capstone
```
""")

nb.code(SRC_PLOT_STYLE + r'''

# Horas por módulo (SYLLABUS del curso) coloreadas por bloque
mods = [("00 Intro", 2), ("01 Unicode/bytes", 4), ("02 BPE", 5), ("03 WordPiece/Unigram/SP", 5), ("04 Diseño tokenizers", 5),
        ("05 Patologías", 5), ("06 Bytes/BLT", 5), ("07 H-Net/transfer", 6), ("08 Multimodal/audio", 6),
        ("09 Capa de embedding", 5), ("10 Contextuales", 5), ("11 Contrastivo", 6), ("12 Embedders modernos", 5),
        ("13 Dense/sparse/late", 5), ("14 ANN", 5), ("15 Evaluación", 5), ("16 Multimodal", 5), ("17 Interpretabilidad", 5),
        ("18 Producción", 5), ("19 Playbook", 4), ("20 Capstone", 6)]
colores = [AZUL] * 9 + [NARANJA] * 9 + [VERDE] * 3
fig, ax = plt.subplots(figsize=(8, 6))
ax.barh([m for m, _ in mods][::-1], [h for _, h in mods][::-1], color=colores[::-1])
ax.set_xlabel("horas estimadas")
ax.set_title(f"Horas por módulo (total ≈ {sum(h for _, h in mods)} h)")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=AZUL, label="A · Tokenización"), Patch(color=NARANJA, label="B · Embeddings"),
                   Patch(color=VERDE, label="Producción y cierre")], loc="lower right")
plt.tight_layout(); plt.show()
''')

nb.md(obs(r"""Los módulos de tokenización (00–08) pesan ≈ 43 h, los de embeddings (09–17) ≈ 46 h y producción/cierre (18–20) ≈ 15 h: **tokenizar bien es cerca de la mitad del trabajo técnico**, y no es un detalle menor porque todo lo que viene después (costes, calidad multilingüe, robustez) depende de ello.
Los módulos 02, 06, 07, 11 y 13 son los más densos: reserva sesiones largas."""))

nb.gemini(
    "imagen", "M00-IMG-01", "Mapa del curso en dos bloques",
    "Un mapa visual de los 21 módulos agrupados en bloque A (tokenización) y bloque B (embeddings) con el hilo conductor Políglota creciendo por debajo. Sirve para orientarte y volver a él al cambiar de módulo.",
    """Diagrama técnico limpio, fondo blanco, estilo de infografía de curso, 16:9. Paleta sobria: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280, tipografía sans-serif legible, sin ilustraciones decorativas.
Composición: un camino horizontal de izquierda a derecha con 21 estaciones numeradas, dividido en dos filas.
Fila superior (franja azul, título «BLOQUE A · Texto y tokenización»), de izquierda a derecha, 9 cajas redondeadas con estos textos EXACTOS:
«00 Intro», «01 Unicode y bytes», «02 BPE desde cero», «03 WordPiece, Unigram, SentencePiece», «04 Diseño de tokenizers», «05 Patologías y robustez», «06 Bytes y BLT», «07 H-Net y tokenizer transfer», «08 Tokens multimodales y audio».
Fila inferior (franja naranja, título «BLOQUE B · Embeddings»), de izquierda a derecha, 9 cajas con estos textos EXACTOS:
«09 Capa de embedding», «10 Contextuales y de oraciones», «11 Aprendizaje contrastivo», «12 Embedders modernos», «13 Dense, sparse y late interaction», «14 Indexación y ANN», «15 Evaluación», «16 Embeddings multimodales», «17 Interpretabilidad y geometría».
A la derecha, una franja verde vertical con 3 cajas apiladas: «18 Producción», «19 Playbook de élite», «20 Capstone: Políglota completo».
Una flecha gris conecta cada caja con la siguiente; una flecha curva une «08» (fin de la fila superior) con «09» (inicio de la fila inferior).
Debajo de todo, una barra horizontal gris con degradado hacia verde y la etiqueta «Políglota: buscador semántico multilingüe (ES/EN/código) crece en cada módulo».
Título superior: «Tokenización y Embeddings: de BPE a los modelos modernos».
Evita: texto ilegible o inventado, más o menos de 21 módulos, flechas ambiguas, iconos decorativos, sombras exageradas.""",
    "Mapa de 21 módulos en dos bloques: tokenización (00–08) y embeddings (09–17) más producción y capstone (18–20)",
    """BLOQUE A · Texto y tokenización
[00]→[01]→[02]→[03]→[04]→[05]→[06]→[07]→[08]
                                         ↓
BLOQUE B · Embeddings
[09]→[10]→[11]→[12]→[13]→[14]→[15]→[16]→[17] → [18]→[19]→[20]
══════════ Políglota crece en cada módulo ═══════════►""",
)
nb.md(obs(r"""Cuando termines cada módulo vuelve a este mapa y ubica qué pieza de Políglota acabas de construir. Fíjate en el salto 08 → 09: pasamos de «cómo se parte el texto» a «qué vector le corresponde»; el puente entre ambos bloques es la **matriz de embeddings** (módulo 09)."""))

nb.md(r"""
## 2. Cómo usar este curso (Colab, `FAST_DEV_RUN`, celdas Gemini y `assets/`)

**Colab.** Abre cada notebook con el badge «Open In Colab». T4 es la GPU por defecto (Colab Pro); algunos módulos (07, 11, 16) recomiendan L4/A100 y lo indican en su cabecera con una estimación de unidades. **Este módulo y los tres primeros corren enteros en CPU.**

**`FAST_DEV_RUN`.** Toda celda pesada lee un flag `FAST_DEV_RUN = True` por defecto: con él, el notebook corre en minutos con datos diminutos (sirve para depurar y para entender). Cuando quieras resultados «de verdad», pon `FAST_DEV_RUN = False` (idealmente en GPU).

**Semilla y `device`.** Siempre `seed = 42` y detección de GPU. Los números que veas en tu pantalla dependen de la versión de las librerías y del corpus (real o sintético): por eso las rúbricas de los proyectos se calibran con lo que **mide la solución de referencia**, no con lo deseado.

**Celdas Gemini (🎨 imagen / 🎬 video).** Algunos diagramas y animaciones se generan **con Gemini**, no con código (los resultados con datos *nunca* van en celdas Gemini). Cada una es un bloque como el de abajo con: un **ID** único (`M00-IMG-01`), un **prompt completo y autocontenido** que copias y pegas en Gemini sin editar, el **nombre de archivo** que debes usar y un **placeholder** que se ve mientras no la reemplaces. Pasos:

1. Copia el prompt del bloque (la parte `text`) en Gemini y genera la imagen/video.
2. Guarda el archivo en la carpeta `assets/` de ese módulo con el nombre que indica la celda (p. ej. `assets/M00-IMG-01.png`).
3. Reemplaza la celda por la línea `![texto alternativo](assets/M00-IMG-01.png)` (o la etiqueta `<video …>` para video).

**Videos largos.** Los guiones de 🎬 vienen por escenas con tiempos («0–4 s: …»). Si tu generador de video produce clips cortos (unos segundos por petición), genera cada escena (o grupo de escenas) por separado con el mismo bloque de estilo del prompt y concaténalos en orden; el MP4 final se guarda con el nombre del ID.

Aunque no las reemplaces, la lección se entiende con el placeholder. El índice de todos los recursos del curso está en `extras/GEMINI_ASSETS.md`.
""")

nb.md(caja("📚 Para profundizar", r"""
Si trabajas en Colab y quieres que `assets/` persista, clona el repositorio en Drive o sube los archivos a la carpeta del módulo; las rutas del curso son relativas al notebook.
"""))

nb.code(r'''
# ── Entorno del curso (celda de arranque estándar) ──
!pip install -q numpy pandas matplotlib seaborn tiktoken rank_bm25 regex
''')

nb.code(r'''
import os, random, sys, time
import numpy as np

SEED = 42
random.seed(SEED); np.random.seed(SEED)
FAST_DEV_RUN = True   # True: subconjuntos diminutos, minutos en CPU. False: escala completa.

try:
    import torch
    torch.manual_seed(SEED); torch.set_num_threads(1)
    device = "cuda" if torch.cuda.is_available() else "cpu"
except ImportError:      # este módulo no necesita torch
    device = "cpu"
print(f"python {sys.version.split()[0]} | numpy {np.__version__} | device = {device} | FAST_DEV_RUN = {FAST_DEV_RUN}")
''')

nb.md(r"""
## 3. Intuición primero: del texto a un resultado de búsqueda

Un buscador moderno es una cadena de transformaciones. **Cada flecha pierde o crea información**, y la mayoría de los errores «misteriosos» de un sistema de retrieval nacen en las primeras flechas, antes de que el modelo vea nada.

```text
texto ──► bytes ──► tokens ──► ids ──► embeddings ──► (Transformer) ──► vector del texto ──► índice ──► ranking
  M01       M01       M02-08    M02-08    M09          M10-12              M10-12              M14       M13,15
"café"   63 61 66  c·a·f·é     [id…]     [vector…]                       [768 números…]
         c3 a9
```

* **Bytes (módulo 01).** El ordenador no ve letras: ve bytes. «é» ocupa 2 bytes en UTF-8; un ideograma chino, 3; un emoji, 4. Esto condiciona el coste de todo lo demás.
* **Tokens (módulos 02–08).** Un *tokenizer* parte el texto en unidades de un vocabulario fijo (≈ 32 000–262 000 entradas en modelos actuales; p. ej. Gemma 3 usa 262 144). Es **discreto y determinista**: no aprende con gradientes.
* **Embeddings (módulos 09–12).** Cada token (y cada texto completo) se asocia a un **vector denso** que *sí* se aprende. Textos parecidos → vectores cercanos.
* **Índice y ranking (módulos 13–15).** Buscar es encontrar los vectores más cercanos a la consulta (o combinar con señales léxicas como BM25).

> **Analogía con lo que ya sabes (recomendación/IR).** El tokenizer es el *parser de términos* de un motor de búsqueda; el embedding es el *vector de ítem* de un sistema de recomendación; el índice ANN es el *candidate generator* de dos torres. Y el vocabulario es a un LLM lo que el catálogo de ítems a un recsys: lo que no esté en el catálogo, no se puede representar directamente.
""")

nb.gemini(
    "imagen", "M00-IMG-02", "Pipeline: del texto al ranking",
    "El recorrido completo de una consulta: texto, bytes, tokens, ids, embeddings, vector de la consulta, búsqueda en el índice y lista ordenada. Con un ejemplo real tokenizado con GPT-2.",
    """Diagrama técnico limpio de un pipeline, fondo blanco, 16:9, flechas gruesas de izquierda a derecha. Paleta: azul #1F6FEB para texto y tokens, naranja #F28E2B para vectores, verde #2CA02C para el índice y los resultados, gris #6B7280 para anotaciones. Tipografía sans-serif legible, sin ilustraciones decorativas.
Composición: 7 etapas en una fila, cada una como una caja redondeada con título arriba y contenido debajo. Los textos son EXACTOS:
1) Título «Texto». Contenido: «Tokenizers turn text into numbers.»
2) Título «Bytes (UTF-8)». Contenido: «54 6F 6B 65 6E 69 7A 65 72 73 …» y debajo en gris pequeño «1 byte por letra ASCII».
3) Título «Tokens». Contenido: siete cajitas azules consecutivas con estos textos exactos: «Token», «izers», « turn», « text», « into», « numbers», «.»
4) Título «IDs (vocabulario GPT-2)». Contenido: siete números exactos bajo cada token, en este orden: «30642», «11341», «1210», «2420», «656», «3146», «13».
5) Título «Embeddings». Contenido: siete barras verticales pequeñas naranjas (un vector por token) con la etiqueta «un vector por token (se aprende)».
6) Título «Vector del texto». Contenido: una sola barra naranja alargada con la etiqueta «un vector por texto (pooling)».
7) Título «Índice y ranking». Contenido: un pequeño espacio 2D con puntos grises y tres puntos verdes cercanos a una estrella naranja (la consulta), y a la derecha una lista «1. doc A», «2. doc B», «3. doc C».
Encima de las etapas, una cinta con los nombres de los bloques del curso: sobre las etapas 2-4 «Bloque A · Tokenización», sobre las etapas 5-7 «Bloque B · Embeddings».
Título superior: «De texto a resultado de búsqueda».
Evita: números distintos de los indicados, tokens inventados, texto ilegible, flechas que se crucen, elementos decorativos o personas.""",
    "Pipeline de 7 etapas: texto, bytes, tokens, ids, embeddings, vector del texto, índice y ranking",
    """Texto            Bytes        Tokens                                   IDs                              Embeddings     Texto→vector   Índice
"Tokenizers  →  54 6F 6B 65 → [Token][izers][ turn][ text][ into][ numbers][.] → 30642 11341 1210 2420 656 3146 13 → ▮▮▮▮▮▮▮ (7 vectores) → ▮ (1 vector) → ★ ← ● ● ●
 turn text ..."   6E 69 7A …
 (Bloque A: tokenización ────────────────────────────)   (Bloque B: embeddings ─────────────────────────────────────)""",
)
nb.md(obs(r"""Con el recurso insertado, sigue los **siete** IDs de izquierda a derecha: son exactamente los que obtendrás con `tiktoken` y el vocabulario GPT-2 en la celda siguiente. Fíjate en que la frase en inglés tarda **7 tokens**; veremos que la misma idea en español cuesta bastante más (la «prima de tokens»)."""))

nb.md(r"""
## 4. Qué es un token (visión global)

Un **token** es una unidad *discreta* de un vocabulario fijo $\mathcal{V}$ (un conjunto finito de cadenas o de secuencias de bytes) a la que se le asigna un **entero** (su id). Un tokenizer es una función $\text{tok}: \Sigma^* \to \mathcal{V}^*$ (de cadenas a secuencias de tokens) y su inversa aproximada, $\text{detok}$.

Un token **no es una palabra**. Veamos la misma frase cortada de cuatro maneras: por palabras, por caracteres, por bytes y por el tokenizer de GPT-2 (byte-level BPE, que implementarás en el módulo 02).
""")

nb.code(SRC_GPT2)

nb.code(r'''
frases = {
    "ES": "Los tokenizadores convierten texto en números.",
    "EN": "Tokenizers turn text into numbers.",
    "código": "def añadir_ñu(x): return x+1",
}
enc = get_gpt2_encoding()
filas = []
for nombre, s in frases.items():
    ids = enc.encode(s) if enc else []
    filas.append({"idioma": nombre, "palabras (split)": len(s.split()), "caracteres": len(s),
                  "bytes UTF-8": len(s.encode("utf-8")), "tokens GPT-2": len(ids) if enc else float("nan")})
import pandas as pd
df_tok = pd.DataFrame(filas).set_index("idioma")
display(df_tok)
if enc:
    ids = enc.encode(frases["ES"])
    print("ES →", [enc.decode_single_token_bytes(i).decode("utf-8", "replace") for i in ids])
    ids = enc.encode(frases["EN"])
    print("EN →", [enc.decode_single_token_bytes(i).decode("utf-8", "replace") for i in ids], ids)
''')

nb.code(r'''
fig, ax = plt.subplots(figsize=(8, 3.8))
df_tok.plot.bar(ax=ax, color=[GRIS, AZUL, NARANJA, VERDE], rot=0, width=0.8)
ax.set_ylabel("unidades por frase"); ax.set_title("La misma idea, cuatro granularidades")
plt.tight_layout(); plt.show()
''')

nb.md(obs(r"""1. **Palabras < tokens < caracteres ≈ bytes** en inglés, pero en español el número de tokens se acerca más al de caracteres: el vocabulario de GPT-2 se construyó mayoritariamente con inglés.
2. «ñ» y «ú» ocupan **2 bytes** cada una: bytes ≠ caracteres (módulo 01).
3. El código también se fragmenta: `_`, `(`, `)` y los espacios consumen tokens. Más tokens = más coste y menos contexto útil."""))

nb.md(r"""
> ### 🧪 Mini-experimento: ¿cuánto cuesta un idioma?
> La relación **tokens / palabra** se llama *fertilidad*. En esta frase el español rinde peor que el inglés. En el módulo 04 la medirás con corpus paralelos (Flores) y en el 02 verás **por qué** ocurre (qué texto se usó para aprender las fusiones). Dato de contexto: Petrov et al. (2023) y Ahia et al. (2023) documentan que la misma frase traducida puede costar hasta 15 veces más tokens según el idioma y el tokenizer (ver referencias).
""")

nb.md(r"""
## 5. Qué es un embedding (visión global)

Un **embedding** es un vector denso $\mathbf{e}\in\mathbb{R}^d$ que representa una unidad (un token, una oración, un documento, una imagen…) de modo que la **geometría refleje similitud**: unidades parecidas ⇒ vectores cercanos.

Hay **dos usos** que no debes confundir:

| | Embedding de token (capa de embedding) | Embedding de texto (sentence/document embedding) |
|---|---|---|
| Entrada | un id entero $i \in \{0,\dots,|\mathcal{V}|-1\}$ | una secuencia de tokens |
| Salida | fila $i$ de una matriz $E \in \mathbb{R}^{|\mathcal{V}|\times d}$ | un vector que resume todo el texto |
| Cómo se obtiene | búsqueda en tabla (*lookup*) | pasar por un Transformer y hacer *pooling* |
| Módulos | 09 | 10, 11, 12 |

**Lookup = producto con one-hot.** Si $\mathbf{x}_i\in\{0,1\}^{|\mathcal{V}|}$ es el one-hot del id $i$, entonces $\mathbf{x}_i^\top E = E_{i,:}$. Es una multiplicación matricial que nadie hace de verdad (se indexa), pero explica por qué los gradientes solo actualizan las filas de los tokens presentes.

**Similitud.** Para comparar vectores se usa casi siempre el **coseno**:
$$\cos(\mathbf{u},\mathbf{v})=\frac{\mathbf{u}^\top\mathbf{v}}{\lVert\mathbf{u}\rVert\,\lVert\mathbf{v}\rVert}\in[-1,1]$$
donde $\mathbf{u}^\top\mathbf{v}=\sum_k u_kv_k$ es el producto escalar y $\lVert\cdot\rVert$ la norma euclídea. Si los vectores están normalizados ($\lVert\mathbf{u}\rVert=1$), coseno = producto escalar.

A continuación, un **juguete hecho a mano** (los vectores NO están aprendidos; los escribimos para fijar la idea): 6 palabras en un espacio de 2 dimensiones con un eje «animal» y otro «vehículo», incluyendo traducciones ES/EN.
""")

nb.code(r'''
palabras = ["gato", "cat", "perro", "coche", "car", "camión"]
V = np.array([[0.90, 0.10], [0.88, 0.15], [0.80, 0.20], [0.10, 0.90], [0.12, 0.88], [0.20, 0.80]])  # (6, 2) a mano
Vn = V / np.linalg.norm(V, axis=1, keepdims=True)
cos = Vn @ Vn.T

fig, axs = plt.subplots(1, 2, figsize=(10, 4))
for (x, y), p, c in zip(V, palabras, [AZUL, AZUL, AZUL, NARANJA, NARANJA, NARANJA]):
    axs[0].annotate("", xy=(x, y), xytext=(0, 0), arrowprops=dict(arrowstyle="->", color=c, lw=1.6))
    axs[0].text(x + 0.02, y + 0.02, p, color=c)
axs[0].set_xlim(0, 1.1); axs[0].set_ylim(0, 1.1); axs[0].set_xlabel("eje «animal»"); axs[0].set_ylabel("eje «vehículo»")
axs[0].set_title("Vectores de juguete en 2D")
im = axs[1].imshow(cos, vmin=0, vmax=1, cmap="Blues")
axs[1].set_xticks(range(6), palabras, rotation=45); axs[1].set_yticks(range(6), palabras)
for i in range(6):
    for j in range(6):
        axs[1].text(j, i, f"{cos[i, j]:.2f}", ha="center", va="center", fontsize=8, color="white" if cos[i, j] > 0.6 else "black")
axs[1].set_title("Similitud coseno"); axs[1].grid(False); plt.colorbar(im, ax=axs[1], fraction=0.046)
plt.tight_layout(); plt.show()
print("cos(gato, cat) =", round(float(cos[0, 1]), 3), "| cos(gato, coche) =", round(float(cos[0, 3]), 3))
''')

nb.md(obs(r"""Dos bloques cuadrados en la matriz: animales por un lado, vehículos por otro, y **las traducciones (gato/cat, coche/car) son vecinas**. Eso es lo que *aprenden* los embedders multilingües (módulos 10–12). Un buscador léxico como BM25, en cambio, ve «gato» y «cat» como cadenas distintas (lo comprobaremos en la sección 9)."""))

nb.code(r'''
# De token id a vector: lookup en una matriz E (aleatoria: aún no hay aprendizaje)
rng = np.random.default_rng(SEED)
vocab_juguete = {"<pad>": 0, "el": 1, "gato": 2, "duerme": 3, "coche": 4}
E = rng.normal(0, 1, size=(len(vocab_juguete), 3))          # |V| x d
ids = [vocab_juguete[t] for t in ["el", "gato", "duerme"]]
print("ids:", ids)
print("lookup E[ids] =\n", E[ids].round(2))
onehot = np.eye(len(vocab_juguete))[ids]                      # (3, |V|)
assert np.allclose(onehot @ E, E[ids])                        # one-hot @ E == indexar
print("✔ one-hot @ E == E[ids]")
''')

nb.md(caja("💡 Intuición", r"""
La matriz $E$ de arriba es aleatoria, así que sus filas **no significan nada todavía**. En un LLM real se aprende junto con el resto del modelo (módulo 09); en un *embedder* de texto se aprende con aprendizaje contrastivo (módulo 11). Lo único que fija este módulo es la **forma** del problema: tokens discretos → vectores continuos.
"""))

nb.md(r"""
## 6. El hilo conductor: Políglota

**Contexto.** Eres ML engineer en **Políglota Labs**, una startup que construye un buscador semántico para documentación técnica en **español, inglés y código**. En cada módulo añades una pieza; en el módulo 20 las integras.

| Etapa | Módulos | Pieza de Políglota |
|---|---|---|
| Corpus + baseline | **00** | `carga_corpus()`, métricas, **BM25** (este módulo) |
| Tokenizer propio | 01–05 | auditoría Unicode, BPE, WordPiece/Unigram, diseño de vocabulario, robustez |
| Alternativas | 06–08 | bytes/patches, H-Net, tokenizer transfer, tokens multimodales |
| Embeddings | 09–12 | capa de embedding, pooling, entrenamiento contrastivo, embedders modernos |
| Recuperación híbrida | 13–14 | dense + sparse + late interaction, índice ANN |
| Evaluación y más | 15–17 | banco de evaluación, multimodal, interpretabilidad |
| Producto | 18–20 | servicio, decisiones de diseño, capstone |
""")

nb.gemini(
    "imagen", "M00-IMG-03", "Arquitectura final de Políglota",
    "La arquitectura objetivo del buscador (la que construirás por piezas): ingesta y normalización, tokenizer propio, embedder, índice híbrido, reranker y evaluación; cada pieza marcada con el módulo donde se construye.",
    """Diagrama de arquitectura limpio, fondo blanco, 16:9. Paleta: azul #1F6FEB (texto y tokens), naranja #F28E2B (vectores y modelos), verde #2CA02C (índice y servicio), gris #6B7280 (anotaciones). Tipografía sans-serif legible, flechas claras, sin ilustraciones decorativas.
Composición de izquierda a derecha en dos carriles.
Carril superior «Indexación (offline)»: cajas conectadas por flechas con estos textos EXACTOS, de izquierda a derecha:
«Corpus ES/EN/código [M00]» → «Normalización Unicode [M01]» → «Tokenizer BPE propio [M02-M05]» → «Embedder (dense) [M09-M12]» → «Índice ANN + índice BM25 [M13-M14]».
Carril inferior «Consulta (online)»: «Consulta del usuario» → «Normalización + tokenizer» → «Embedder + BM25» → «Fusión híbrida (RRF) [M13]» → «Reranker cross-encoder [M13]» → «Top-10 resultados».
Una flecha vertical de la caja «Índice ANN + índice BM25» del carril superior hacia la caja «Fusión híbrida (RRF)» del inferior.
A la derecha, una columna vertical verde con dos cajas: «Evaluación: nDCG@10, Recall@k, MRR [M15]» y «Servicio, caché y monitoreo [M18]».
Una caja punteada gris en la esquina inferior izquierda: «Opcional: imágenes y PDFs [M16]».
Título superior: «Políglota: buscador semántico multilingüe».
Evita: añadir cajas o módulos que no estén en esta lista, texto ilegible, iconos decorativos, flechas ambiguas.""",
    "Arquitectura de Políglota con carriles de indexación y consulta, índice híbrido, reranker, evaluación y servicio",
    """INDEXACIÓN (offline)
[Corpus M00] → [Normalización M01] → [Tokenizer BPE M02-05] → [Embedder M09-12] → [Índice ANN + BM25 M13-14]
                                                                                          │
CONSULTA (online)                                                                         ▼
[Consulta] → [Norm + tokenizer] → [Embedder + BM25] ──────────────► [Fusión RRF M13] → [Reranker M13] → [Top-10]
                                                                   [Evaluación M15] [Servicio M18]""",
)
nb.md(obs(r"""Cada caja lleva el módulo donde la construyes. Nota que el **tokenizer** y la **normalización** están *antes* del embedder y del BM25: si ahí se pierde información (una tilde, un emoji, un espacio), ningún modelo posterior la recupera."""))

nb.md(r"""
## 7. El corpus Políglota: `carga_corpus()`

Todos los módulos usan **el mismo contrato de datos**. La función `carga_corpus(fast_dev)` devuelve un diccionario:

```python
{
  "docs":    [{"id": str, "lang": "es" | "en" | "code", "text": str}, ...],
  "queries": [{"qid": str, "lang": "es" | "en" | "code", "text": str}, ...],
  "qrels":   {qid: {doc_id: 1}},          # relevancia (>0 = relevante)
  "source":  "real" | "synthetic",
}
```

**Cadena de descarga (oficial → espejo → sintético):**

| Parte | 1) oficial | 2) espejo | 3) último recurso |
|---|---|---|---|
| Wikipedia ES/EN | HF `wikimedia/wikipedia` (snapshot `20231101`, *streaming*) | API pública de Wikipedia (artículos aleatorios, solo la introducción) | texto técnico **sintético** ES/EN (avisa en rojo) |
| Código Python | CodeSearchNet en HF (varios repos por cambios de formato de `datasets`) | funciones **reales** de la biblioteca estándar de Python con su docstring | — |

**Mini golden set.** Cada consulta es una búsqueda de *«ítem conocido»*: en Wikipedia, la consulta es el **título** del artículo (que no aparece en el `text`) y el único relevante es ese artículo; en código, la consulta es la **primera frase del docstring** y el relevante es la función (con el docstring ya eliminado). Es barato y reproducible, pero tiene un sesgo que discutiremos en «Secretos de la élite».

> ⚠️ Si `source == "synthetic"`, los números absolutos **no son comparables** con datos reales: sirven para depurar el código, no para sacar conclusiones sobre Wikipedia.

Cada notebook del curso es autocontenido: copia estas celdas (la implementación canónica vive en el repositorio, `_tools/builders/poliglota_src/`).
""")

_c = src_corpus_cells()
nb.code("# ── Celda 1/3 de carga_corpus · datos del corpus SINTÉTICO (último recurso) ──\n" + _c[0])
nb.code("# ── Celda 2/3 de carga_corpus · generador sintético ──\n" + _c[1])
nb.code("# ── Celda 3/3 de carga_corpus · cadena oficial → espejo → sintético ──\n" + _c[2])

nb.code(r'''
t0 = time.time()
corpus = carga_corpus(fast_dev=FAST_DEV_RUN)
docs, queries, qrels, source = corpus["docs"], corpus["queries"], corpus["qrels"], corpus["source"]
print(f"\nsource = {source!r} | {len(docs)} docs | {len(queries)} queries | {time.time() - t0:.1f} s")
for lang in ("es", "en", "code"):
    d = next(x for x in docs if x["lang"] == lang); q = next(x for x in queries if x["lang"] == lang)
    print(f"\n[{lang}] doc {d['id']}: {d['text'][:140]!r}...\n[{lang}] query {q['qid']}: {q['text']!r} → relevante {list(qrels[q['qid']])}")
''')

nb.code(r'''
import pandas as pd
df = pd.DataFrame(docs)
df["chars"] = df.text.str.len(); df["bytes"] = df.text.map(lambda t: len(t.encode("utf-8"))); df["palabras"] = df.text.str.split().map(len)

fig, axs = plt.subplots(1, 2, figsize=(11, 3.8))
for lang, c in zip(("es", "en", "code"), (AZUL, NARANJA, VERDE)):
    axs[0].hist(df[df.lang == lang].chars, bins=30, alpha=0.6, color=c, label=lang)
axs[0].set_xlabel("caracteres por documento"); axs[0].set_ylabel("nº de documentos"); axs[0].set_title("Longitud de los documentos"); axs[0].legend()
g = df.groupby("lang")[["chars", "bytes"]].sum()
axs[1].bar(g.index, (g.bytes / g.chars - 1) * 100, color=[VERDE, NARANJA, AZUL])  # índice ordenado: code, en, es
axs[1].set_ylabel("bytes extra por cada 100 caracteres"); axs[1].set_title("Sobrecoste de bytes sobre ASCII puro")
plt.tight_layout(); plt.show()
display(df.groupby("lang")[["chars", "bytes", "palabras"]].mean().round(1))
''')

nb.md(obs(r"""1. **Bytes extra**: el inglés y el código rondan 0 (ASCII puro: 1 byte por carácter); el español queda por encima por las vocales acentuadas y la «ñ» (2 bytes cada una). Con el corpus sintético el efecto es pequeño; con Wikipedia real mide tú el valor. Es una pista del coste oculto de los idiomas con diacríticos (módulo 01 lo cuantifica con 12 idiomas).
2. Los documentos de código y los de Wikipedia tienen distribuciones de longitud distintas: cualquier hiperparámetro que dependa de la longitud (como $b$ en BM25) se comportará distinto por tipo de corpus."""))

nb.md(r"""
## 8. Métricas de retrieval canónicas

Definimos una sola vez (y se copian idénticas en todos los módulos) tres métricas. Sea $\text{rel}_i$ la relevancia del documento en la posición $i$ del ranking y $k$ el corte:

$$\text{DCG@}k=\sum_{i=1}^{k}\frac{\text{rel}_i}{\log_2(i+1)},\qquad \text{nDCG@}k=\frac{\text{DCG@}k}{\text{IDCG@}k}$$

* $\text{IDCG@}k$ es el DCG del **ranking ideal** (relevantes ordenados por relevancia decreciente): normaliza a $[0,1]$.
* $\dfrac{1}{\log_2(i+1)}$ es el **descuento por posición**: acertar en el puesto 1 vale 1.0; en el 2, 0.63; en el 10, 0.29.
* $\text{Recall@}k=\dfrac{|\{\text{relevantes}\}\cap\{\text{top-}k\}|}{|\{\text{relevantes}\}|}$.
* $\text{MRR@}k=\dfrac{1}{\text{rango del primer relevante}}$ si está en el top-$k$; si no, 0 (promediado sobre consultas).

**Ejemplo resuelto a mano.** Ranking `[d3, d1, d7, d2]`, relevantes `{d1, d2}` (relevancia 1):

* DCG@4 = $\dfrac{1}{\log_2 3}+\dfrac{1}{\log_2 5}=0.6309+0.4307=1.0616$ (d1 en la posición 2, d2 en la 4).
* IDCG@4 = $\dfrac{1}{\log_2 2}+\dfrac{1}{\log_2 3}=1+0.6309=1.6309$.
* nDCG@4 = $1.0616/1.6309=\mathbf{0.651}$. Recall@4 = $2/2=1$. MRR@4 = $1/2=0.5$.

**Convenciones (importantes y a menudo mal implementadas):** ganancia **lineal** (la de `trec_eval`/`pytrec_eval`, que usan BEIR y MTEB); **duplicados** en el ranking cuentan una sola vez; las consultas **sin relevantes** devuelven 0 y `evaluate()` las **excluye** del promedio; los **empates** de score se rompen por orden del corpus (determinista).
""")

nb.code("# ── Métricas canónicas de retrieval (idénticas en todos los módulos) ──\n" + SRC_METRICS)

nb.code(r'''
# Tests: el ejemplo a mano + casos límite
r = ["d3", "d1", "d7", "d2"]; rel = {"d1": 1, "d2": 1}
assert abs(ndcg_at_k(r, rel, 4) - 0.6510) < 1e-3
assert recall_at_k(r, rel, 4) == 1.0 and mrr_at_k(r, rel, 4) == 0.5
assert ndcg_at_k(["d1", "d1", "d1"], {"d1": 1}, 10) == 1.0            # duplicados no inflan el DCG
assert ndcg_at_k(r, {}, 10) == 0.0 and recall_at_k(r, {}, 10) == 0.0   # sin relevantes: 0 (evaluate() las excluye)
assert rank_from_scores([0.5, 0.9, 0.9], ["a", "b", "c"]) == ["b", "c", "a"]  # empate b/c -> orden del corpus
graded = {"a": 3, "b": 2, "c": 0}                                     # relevancias graduadas
print("nDCG@3 graduado, orden ideal:", ndcg_at_k(["a", "b", "c"], graded, 3), "| invertido:", round(ndcg_at_k(["b", "a", "c"], graded, 3), 3))
print("✔ métricas OK")
''')

nb.code(r'''
i = np.arange(1, 11)
fig, ax = plt.subplots(figsize=(6.5, 3.6))
ax.plot(i, 1 / np.log2(i + 1), "o-", color=AZUL, label=r"$1/\log_2(i+1)$ (nDCG)")
ax.plot(i, 1 / i, "s--", color=NARANJA, label=r"$1/i$ (MRR)")
ax.set_xlabel("posición en el ranking $i$"); ax.set_ylabel("peso de un acierto"); ax.set_title("¿Cuánto vale acertar en la posición i?")
ax.set_xticks(i); ax.legend(); plt.tight_layout(); plt.show()
''')

nb.md(obs(r"""El descuento de nDCG es **más suave** que el de MRR: en la posición 10 un acierto aún vale 0.29 de uno en la 1ª posición (con MRR vale 0.10). Por eso MRR castiga mucho más no poner el relevante primero, y nDCG@10 tolera listas con varios relevantes. Elegir la métrica es elegir qué comportamiento premias."""))

nb.md(r"""
## 9. Baseline léxico: BM25 desde cero

### Intuición
BM25 puntúa un documento $D$ para una consulta $Q$ sumando, por cada término de la consulta, **cuánta evidencia** aporta: (a) cuán *raro* es el término en el corpus (IDF), (b) cuántas veces aparece en el documento con **saturación** (la 10.ª aparición aporta mucho menos que la 2.ª) y (c) una **normalización por longitud** (un documento largo menciona más términos «por azar»).

### Fórmula
$$\text{BM25}(Q,D)=\sum_{t\in Q}\text{IDF}(t)\cdot\frac{f(t,D)\,(k_1+1)}{f(t,D)+k_1\left(1-b+b\,\dfrac{|D|}{\text{avgdl}}\right)},\qquad \text{IDF}(t)=\ln\!\left(1+\frac{N-n_t+0.5}{n_t+0.5}\right)$$

* $f(t,D)$: veces que el término $t$ aparece en $D$ (*term frequency*). $|D|$: longitud de $D$ en términos; $\text{avgdl}$: longitud media del corpus.
* $N$: nº de documentos; $n_t$: nº de documentos que contienen $t$ (*document frequency*).
* $k_1\approx1.2$–$2$ controla la **saturación** de $f$; $b\in[0,1]$ controla cuánto se **normaliza por longitud** ($b=0$: nada; $b=1$: total).
* Esta variante de IDF (la de Lucene) nunca es negativa; la de `rank_bm25.BM25Okapi` usa $\ln\frac{N-n_t+0.5}{n_t+0.5}$ y **sí puede serlo** para términos en más de la mitad de los documentos (la librería los sustituye por un suelo $\epsilon\cdot\overline{\text{IDF}}$).

**Ejemplo resuelto a mano** ($k_1=1.2$, $b=0.75$). Corpus: D1 = «gato negro», D2 = «gato gato blanco», D3 = «perro negro»; consulta «gato».

* $N=3$, $n_{\text{gato}}=2$ ⇒ $\text{IDF}=\ln(1+1.5/2.5)=\ln 1.6=0.470$. $\text{avgdl}=(2+3+2)/3=2.33$.
* D1 ($f=1$, $|D|=2$): $0.470\cdot\dfrac{1\cdot2.2}{1+1.2\,(0.25+0.75\cdot 2/2.33)}=0.470\cdot\dfrac{2.2}{2.071}=\mathbf{0.499}$.
* D2 ($f=2$, $|D|=3$): $0.470\cdot\dfrac{2\cdot2.2}{2+1.2\,(0.25+0.75\cdot 3/2.33)}=0.470\cdot\dfrac{4.4}{3.457}=\mathbf{0.598}$.
* D3 ($f=0$): 0. Ranking: D2 > D1 > D3. Fíjate en que D2 tiene **el doble** de apariciones pero solo un **20 %** más de score: saturación + penalización por longitud. La celda que sigue a la implementación lo comprueba con el `BM25` propio.

**Implementación:** un **índice invertido** (`término → [(doc, tf)]`) que solo visita los documentos que contienen algún término de la consulta. Es la misma estructura que usa Lucene/Elasticsearch (analogía directa con la búsqueda de candidatos de un recsys).
""")

nb.code(r'''
ks = np.linspace(0, 20, 200)
fig, axs = plt.subplots(1, 2, figsize=(11, 3.8))
for k1, c in zip((0.5, 1.2, 2.0, 5.0), (AZUL, NARANJA, VERDE, GRIS)):
    axs[0].plot(ks, ks * (k1 + 1) / (ks + k1), color=c, label=f"$k_1={k1}$")
axs[0].plot(ks, ks, "k:", lw=1, label="sin saturación (lineal)")
axs[0].set_xlabel("frecuencia del término $f(t,D)$"); axs[0].set_ylabel("contribución (sin IDF)"); axs[0].set_title("Saturación de la frecuencia"); axs[0].legend(); axs[0].set_ylim(0, 12)
for b, c in zip((0.0, 0.5, 0.75, 1.0), (GRIS, VERDE, AZUL, NARANJA)):
    ratio = np.linspace(0.2, 4, 100)   # |D| / avgdl
    axs[1].plot(ratio, 3 * 2.2 / (3 + 1.2 * (1 - b + b * ratio)), color=c, label=f"$b={b}$")
axs[1].set_xlabel("longitud relativa $|D|/\\mathrm{avgdl}$"); axs[1].set_ylabel("contribución con $f=3$, $k_1=1.2$"); axs[1].set_title("Normalización por longitud"); axs[1].legend()
plt.tight_layout(); plt.show()
''')

nb.md(obs(r"""**Izquierda.** Con $k_1$ pequeño la curva se aplana enseguida (la 3.ª aparición casi no suma); con $k_1$ grande se acerca al conteo lineal. **Derecha.** Con $b=0$ los documentos largos no se penalizan (curva plana); con $b=1$ la contribución cae a la mitad cuando el documento es el doble de largo que el promedio. Estos dos botones son los únicos hiperparámetros relevantes de BM25."""))

nb.code("# ── Tokenización léxica simple + BM25 propio con índice invertido ──\n" + SRC_BM25)

nb.code(r'''
# Comprobación del ejemplo resuelto a mano (D1, D2, D3 y la consulta «gato»)
mini = BM25(k1=1.2, b=0.75).fit([["gato", "negro"], ["gato", "gato", "blanco"], ["perro", "negro"]], ["D1", "D2", "D3"])
print(np.round(mini.scores(["gato"]), 3), mini.search(["gato"], 3))   # esperado: [0.499 0.598 0.] ['D2', 'D1', ...]
''')

nb.code(r'''
def construir_bm25(docs, acentos="keep", **kw):
    bm = BM25(**kw).fit([tokenize_simple(d["text"], acentos) for d in docs], [d["id"] for d in docs])
    return bm

def correr(bm, queries, acentos="keep", k=10, tok=tokenize_simple):
    return {q["qid"]: bm.search(tok(q["text"], acentos), k) for q in queries}

t0 = time.time()
bm25 = construir_bm25(docs)
run = correr(bm25, queries)
print(f"indexado + {len(queries)} consultas en {time.time() - t0:.2f} s | vocabulario léxico: {len(bm25.postings):,} términos")

def por_idioma(run, qrels, k=10):
    filas = []
    for lang in ("es", "en", "code", None):
        qr = {q["qid"]: qrels[q["qid"]] for q in queries if lang is None or q["lang"] == lang}
        filas.append({"grupo": lang or "TODAS", **evaluate(run, qr, k)})
    return pd.DataFrame(filas).set_index("grupo")

res = por_idioma(run, qrels)
display(res.round(3))
''')

nb.code(r'''
# Validación cruzada con rank_bm25 (misma fórmula de IDF y mismos k1, b)
from rank_bm25 import BM25Okapi
toks = [tokenize_simple(d["text"]) for d in docs]
ref = BM25Okapi(toks, k1=1.5, b=0.75)
mio = BM25(k1=1.5, b=0.75, idf="okapi").fit(toks, [d["id"] for d in docs])
q = tokenize_simple(queries[0]["text"])
diff = np.abs(ref.get_scores(q) - mio.scores(q)).max()
print(f"máx |score_rank_bm25 − score_propio| = {diff:.2e}")
assert diff < 1e-9
run_ref = {x["qid"]: rank_from_scores(ref.get_scores(tokenize_simple(x["text"])), [d["id"] for d in docs], 10) for x in queries}
run_mio = correr(mio, queries)
print("nDCG@10 rank_bm25:", round(evaluate(run_ref, qrels)["ndcg"], 4), "| propio (idf=okapi):", round(evaluate(run_mio, qrels)["ndcg"], 4),
      "| propio (idf=lucene, k1=1.2):", round(res.loc["TODAS", "ndcg"], 4))
''')

nb.code(r'''
ax = res.loc[["es", "en", "code", "TODAS"], ["ndcg", "recall", "mrr"]].plot.bar(figsize=(8, 3.8), color=[AZUL, NARANJA, VERDE], rot=0, width=0.8)
ax.set_ylim(0, 1.05); ax.set_ylabel("valor de la métrica @10"); ax.set_title(f"Baseline BM25 por tipo de consulta (corpus {source})")
for c in ax.containers: ax.bar_label(c, fmt="%.2f", fontsize=8)
plt.tight_layout(); plt.show()
''')

nb.md(obs(r"""1. El BM25 propio y `rank_bm25` coinciden hasta el error numérico cuando usan la misma fórmula de IDF: ya sabes **qué** hace la librería.
2. Compara las barras: **código** puntúa claramente por debajo de ES/EN. Las consultas de código son frases en inglés (docstrings) y los documentos son identificadores como `join_path`: poco solapamiento de *cadenas*. Es un problema de **vocabulario** (y de tokenización), no de BM25.
3. Si `source == "synthetic"`, ES y EN salen casi perfectos porque el generador es repetitivo: no extraigas conclusiones sobre Wikipedia."""))

nb.md(r"""
## 10. Experimentos: dónde falla un buscador léxico

### 10.1 La barrera del idioma
BM25 compara **cadenas**. Si la consulta está en español y el documento relevante en inglés (o al revés), solo se solapan cognados y nombres propios. Probemos con 6 pares de oraciones paralelas escritas a mano.
""")

nb.code(r'''
pares = [("El gato duerme en el sofá", "The cat sleeps on the sofa"),
         ("Configura la caché del servidor", "Configure the server cache"),
         ("La base de datos está bloqueada", "The database is locked"),
         ("Instala el paquete con pip", "Install the package with pip"),
         ("El balanceador reparte las peticiones", "The load balancer spreads the requests"),
         ("Reinicia el contenedor de Docker", "Restart the Docker container")]
es_docs = [a for a, _ in pares]; en_docs = [b for _, b in pares]
def acierto(consultas, coleccion):
    bm = BM25().fit([tokenize_simple(t) for t in coleccion], [str(i) for i in range(len(coleccion))])
    top1 = [bm.search(tokenize_simple(c), 1)[0] for c in consultas]
    sin_solape = [bm.scores(tokenize_simple(c)).max() == 0 for c in consultas]
    # un «acierto» con score 0 sería un empate resuelto por el orden del corpus (suerte), no recuperación
    return np.mean([int(t) == i and not z for i, (t, z) in enumerate(zip(top1, sin_solape))]), sum(sin_solape)
print("ES → ES (mismo idioma):  acierto@1 = %.2f | consultas sin NINGÚN término en común: %d" % acierto(es_docs, es_docs))
print("ES → EN (traducción):    acierto@1 = %.2f | consultas sin NINGÚN término en común: %d" % acierto(es_docs, en_docs))
''')

nb.md(obs(r"""Con el mismo idioma el acierto es 1.0; cruzando idiomas la mayoría de las consultas **no comparte ni un término** con su traducción (los pocos aciertos se deben a cognados y nombres propios como «Docker», «pip» o «cache/caché» tras plegar mayúsculas). Fíjate además en que no contamos como acierto un top-1 con score 0: sería un empate resuelto por el orden del corpus. Un embedder multilingüe resolverá esto (módulos 10–12); mientras tanto, es la razón de ser de Políglota."""))

nb.md(r"""
### 10.2 La tokenización importa incluso para BM25
En código, las consultas dicen «join path components» y los documentos contienen `os.path.join(a, *p)`. Una tokenización que **divide identificadores** (`snake_case`, `camelCase`) hace visibles las palabras. Medimos el efecto sobre las consultas de código.
""")

nb.code(r'''
import re
def split_ident(text, acentos="keep"):
    """Divide snake_case y camelCase además de \\w+: 'getHTTPResponse_code' -> ['get','http','response','code']."""
    enteros = [w for w in tokenize_simple(text, acentos) if "_" in w]   # conserva también el identificador entero
    texto = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)          # camelCase
    texto = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", texto)       # HTTPResponse
    texto = texto.replace("_", " ")
    return tokenize_simple(texto, acentos) + enteros

code_docs = [d for d in docs if d["lang"] == "code"]; code_q = [q for q in queries if q["lang"] == "code"]
qr_code = {q["qid"]: qrels[q["qid"]] for q in code_q}
resultados = {}
for nombre, tok in (("\\w+ (palabras)", tokenize_simple), ("dividir identificadores", split_ident)):
    bm = BM25().fit([tok(d["text"]) for d in code_docs], [d["id"] for d in code_docs])
    run_c = {q["qid"]: bm.search(tok(q["text"]), 10) for q in code_q}
    resultados[nombre] = evaluate(run_c, qr_code)["ndcg"]
print({k: round(v, 3) for k, v in resultados.items()})
fig, ax = plt.subplots(figsize=(5.5, 3.2))
ax.bar(list(resultados), list(resultados.values()), color=[GRIS, VERDE]); ax.set_ylabel("nDCG@10 (consultas de código)")
ax.set_title("Efecto de la tokenización léxica en código"); plt.tight_layout(); plt.show()
''')

nb.md(obs(r"""Dividir identificadores es una decisión de **tokenización** (no de modelo) y cambia el nDCG@10 de código. Esto anticipa el tema del curso: *cómo cortes el texto determina qué puede encontrar el sistema*. Si la mejora te parece pequeña o grande, recuerda que depende del corpus (real/sintético) y del número de consultas: la siguiente sección cuantifica esa incertidumbre."""))

nb.md(r"""
### 10.3 ¿Cuánta incertidumbre tiene tu nDCG? Intervalo bootstrap
Con unas decenas de consultas, el nDCG@10 medio es una estimación ruidosa. Remuestreamos las **consultas** con reemplazo (*bootstrap*) para obtener un intervalo del 95 %.
""")

nb.code(r'''
def ndcg_por_query(run, qrels, k=10):
    return np.array([ndcg_at_k(run[qid], rels, k) for qid, rels in qrels.items()])

def bootstrap_ci(valores, n_boot=2000, alpha=0.05, seed=SEED):
    rng = np.random.default_rng(seed)
    medias = rng.choice(valores, size=(n_boot, len(valores)), replace=True).mean(axis=1)
    return valores.mean(), np.quantile(medias, [alpha / 2, 1 - alpha / 2]), medias

v = ndcg_por_query(run, qrels)
media, (lo, hi), medias = bootstrap_ci(v)
print(f"nDCG@10 = {media:.3f}  IC95% [{lo:.3f}, {hi:.3f}]  (n = {len(v)} consultas)")
fig, ax = plt.subplots(figsize=(6.5, 3.4))
ax.hist(medias, bins=40, color=AZUL, alpha=0.8); ax.axvline(media, color=NARANJA, lw=2, label="media")
ax.axvline(lo, color=GRIS, ls="--", label="IC 95 %"); ax.axvline(hi, color=GRIS, ls="--")
ax.set_xlabel("nDCG@10 medio de cada remuestreo"); ax.set_ylabel("frecuencia"); ax.set_title("Bootstrap sobre las consultas"); ax.legend()
plt.tight_layout(); plt.show()
''')

nb.md(obs(r"""El intervalo tiene una anchura de varios puntos de nDCG. **Si dos sistemas difieren menos que eso, no puedes afirmar que uno sea mejor** con este golden set. El módulo 15 formaliza esto (tests pareados, tamaño de muestra); aquí ya tienes el hábito: *reporta siempre un intervalo*."""))

nb.md(r"""
## 11. Mapa de madurez
Estado a **octubre de 2026**. 🟢 sólido (estándar de industria) · 🟡 emergente (resultados publicados, adopción parcial) · 🔴 experimental.
""" + "\n\n" + mapa_madurez([
    ("BM25 / retrieval léxico con índice invertido", "🟢", "Lucene y los motores construidos sobre él; baseline de BEIR", "Thakur et al. 2021 (BEIR, arXiv:2104.08663); Robertson & Zaragoza 2009"),
    ("Byte-level BPE (tokenización de LLMs)", "🟢", "GPT-2 y la familia de encodings de `tiktoken` (modelo → encoding en `tiktoken/model.py`)", "Radford et al. 2019; Wang et al. 2019 (arXiv:1909.03341); repositorio `tiktoken`"),
    ("Embeddings de oraciones con bi-encoders", "🟢", "Sentence-BERT y sucesores", "Reimers & Gurevych 2019 (arXiv:1908.10084)"),
    ("Retrieval híbrido (embeddings + BM25)", "🟢", "Anthropic documenta «Contextual Retrieval» combinando ambos (sep-2024)", "anthropic.com/news/contextual-retrieval"),
    ("Sparse aprendido (SPLADE) y late interaction (ColBERT)", "🟡", "Resultados fuertes en BEIR; adopción parcial en producción", "Formal et al. 2021 (arXiv:2107.05720); Khattab & Zaharia 2020 (arXiv:2004.12832)"),
    ("Modelos sin tokenizer (p. ej. Byte Latent Transformer)", "🔴", "Investigación de Meta FAIR; no es el estándar de producción", "Pagnoni et al. 2024 (arXiv:2412.09871)"),
]) + "\n")

nb.md(r"""
## 12. 🏭 En producción
* **BM25 sigue vivo.** En sistemas reales casi nunca se sustituye el retrieval léxico: se **combina** con embeddings (*hybrid search*). Anthropic describe en su post «Introducing Contextual Retrieval» (sep-2024) que combinar embeddings con BM25 reduce los fallos de recuperación frente a usar solo embeddings (sus cifras son de su propio benchmark; no las generalices).
* **Tokenización = coste.** Las APIs de LLM cobran por token; la prima de tokens entre idiomas (Ahia et al., 2023; Petrov et al., 2023) es un factor de coste y de equidad que se decide *antes* del modelo.
* **El pipeline se versiona entero.** Cambiar el tokenizer o la normalización invalida los índices (hay que re-indexar): es una decisión de ingeniería, no un hiperparámetro.
* **Coste de este módulo:** CPU, segundos. Un BM25 sobre millones de documentos se hace con Lucene/Elasticsearch/OpenSearch; aquí lo implementamos para entender qué hacen.
""")

nb.md(r"""
**🧪 ¿Cuánto cuesta de verdad una prima de tokens?** Si tu idioma necesita $r$ veces más tokens para el mismo texto, el coste **no** siempre es $r$. Con la aproximación de Kaplan et al. (2020) para el cómputo del *forward* por token, $C_{\text{fwd}}\approx 2N + 2\,n_{\text{layer}}\,n_{\text{ctx}}\,d_{\text{model}}$ ($N$ = parámetros sin embeddings), procesar $n$ tokens cuesta $\approx n\,(2N + 2\,n_{\text{layer}}\,n\,d_{\text{model}})$ (cota con el contexto completo): el término lineal crece como $r$ y el de atención como $r^2$. Además, en una ventana fija cabe $1/r$ del texto. La celda lo calcula para una configuración de tamaño 7 B (32 capas, $d=4096$; números ilustrativos).
""")
nb.code(r'''
def flops_forward(n_tok: int, N: float = 6.5e9, L: int = 32, d: int = 4096) -> float:
    """Kaplan et al. (2020): C_fwd por token ≈ 2N + 2·L·n_ctx·d; aquí n_ctx = n_tok (cota superior)."""
    return n_tok * (2 * N + 2 * L * n_tok * d)

for n_base in (1_000, 32_000):
    for r in (1.5, 3.0):
        coste = flops_forward(int(r * n_base)) / flops_forward(n_base)
        print(f"texto que en inglés ocupa {n_base:>6,} tokens | prima r={r}: x{r:.1f} en factura por token, x{coste:.2f} en FLOPs, {1/r:.0%} del texto en la misma ventana")
''')
nb.md(obs(r"""Con textos cortos el sobrecoste en cómputo ≈ $r$ (domina $2N$); con contextos largos supera claramente a $r$ (tiende a $r^2$ cuanto más domina la atención; con 32 k tokens y $r=3$ ya es ≈ 5×). Por eso la prima de tokens de un idioma es un problema de **latencia y de capacidad de servicio**, no solo de factura, y por eso los laboratorios lo miden antes de fijar el tokenizer (módulo 04)."""))

nb.md(r"""
## 13. 🧠 Secretos de la élite
1. **Empieza SIEMPRE por un baseline léxico.** BEIR mostró que BM25 es un baseline robusto frente a modelos neuronales en evaluación *zero-shot* (Thakur et al., 2021). Si tu embedder no gana a BM25 en tu dominio, el problema no es el modelo.
2. **Los empates cambian tus resultados.** Con scores iguales, el orden de entrada decide el ranking: `rank_from_scores` rompe los empates por orden de corpus para que el experimento sea reproducible. Es un fallo de evaluación clásico (lo verificaste en el test de arriba).
3. **Duplicados y consultas sin relevantes.** Un doc repetido en el ranking inflaría el DCG si no se deduplica; una consulta sin relevantes dividiría por cero. Toda implementación seria fija una convención y la documenta (aquí: dedup + exclusión).
4. **El tamaño del subconjunto cambia el nivel absoluto.** Con un corpus más grande hay más distractores: el nDCG baja. Compara sistemas **solo sobre el mismo corpus y las mismas consultas** (corre `FAST_DEV_RUN = False` y compruébalo).
5. **Golden sets de «ítem conocido» están sesgados.** Si la consulta es el título del documento, los modelos léxicos salen favorecidos (comparten palabras con el texto). Para comparar embedders hay que construir consultas que **no** copien el vocabulario del documento (módulo 15).
6. **El IDF de la librería no es el de Lucene.** `rank_bm25.BM25Okapi` puede dar IDF negativo y lo corrige con un suelo; Lucene usa $\ln(1+\cdot)$. Dos «BM25» distintos dan rankings distintos: documenta cuál usas.
7. **Reporta intervalos de confianza.** Con ≈ 100 consultas, ±3–5 puntos de nDCG son ruido (mídelo con el bootstrap de arriba, que usa tus datos).
8. **La tokenización léxica es una variable experimental.** Quitar tildes, dividir identificadores o usar stemming mueve el nDCG tanto como cambiar de algoritmo de ranking; anótala en cada experimento.
""")

nb.md(r"""
## 14. ⚠️ Errores comunes
* **Confundir token con palabra** (o con carácter): un token es lo que dice el vocabulario del tokenizer, y varía por modelo.
* **Comparar nDCG entre corpus o subconjuntos distintos** (o entre datos sintéticos y reales).
* **Calcular nDCG con `ranked_ids` sin ordenar** o con relevancias como booleanos si el dataset es graduado.
* **Mezclar `FAST_DEV_RUN=True` con conclusiones «de producción»**: el modo rápido es para depurar.
* **Olvidar fijar la semilla** y los empates: dos ejecuciones dan rankings distintos.
* **Dejar celdas Gemini sin reemplazar al compartir el notebook**: funcionan, pero verás el placeholder.
""")

nb.md(r"""
## 15. Autoevaluación
""" + "\n" + preguntas([
    ("(Cálculo)", "Un ranking devuelve `[a, b, c, d, e]` y los relevantes son `{b: 1, e: 1}`. Calcula nDCG@5, Recall@3 y MRR@5.",
     "DCG = $1/\\log_2 3 + 1/\\log_2 6 = 0.6309 + 0.3869 = 1.0178$. IDCG = $1 + 1/\\log_2 3 = 1.6309$. **nDCG@5 = 0.624**. Recall@3: sólo `b` está en el top-3 → $1/2 = 0.5$. MRR@5: primer relevante en la posición 2 → $0.5$."),
    ("(Diagnóstico)", "Tu BM25 devuelve score 0 para todos los documentos de una consulta en español sobre un corpus en inglés. ¿Es un bug del índice? ¿Qué harías?",
     "No es un bug: BM25 compara cadenas y la consulta no comparte ningún término con los documentos (IDF·TF = 0). Soluciones: un embedder multilingüe (módulos 10–12), traducir la consulta, o expandirla; y en tu evaluación, reportar el rendimiento *por idioma* para no promediar el problema."),
    ("(Transferencia)", "Tu golden set tiene consultas con 3 documentos relevantes con grados 3, 2 y 1. ¿Qué cambia en tu implementación y por qué la ganancia lineal puede ser discutible?",
     "El IDCG se calcula con los 3 grados ordenados descendentemente (3, 2, 1) y el nDCG pasa a premiar el orden entre relevantes. La ganancia lineal ($\\text{rel}$) es la de `trec_eval`; la exponencial ($2^{\\text{rel}}-1$) enfatiza más los muy relevantes. Elegir una u otra cambia los números: fija la convención y no compares con trabajos que usan la otra."),
    ("", "¿Por qué se usa el coseno (o el producto escalar con vectores normalizados) y no la distancia euclídea sin normalizar para comparar embeddings de texto?",
     "El coseno ignora la norma, que en muchos modelos refleja la frecuencia del token o la longitud del texto más que su significado. Con vectores normalizados, coseno, producto escalar y distancia euclídea son equivalentes en ranking ($\\lVert u-v\\rVert^2 = 2-2\\cos$)."),
    ("", "¿Qué dos hiperparámetros de BM25 controlan la saturación y la normalización por longitud, y qué valores toman con `b = 0`?",
     "$k_1$ controla la saturación de la frecuencia y $b$ la normalización por longitud. Con $b=0$ no se normaliza: un documento largo no se penaliza por serlo."),
    ("", "Menciona dos razones por las que el español puede costar más tokens que el inglés con el tokenizer de GPT-2.",
     "1) El vocabulario se construyó con mayoría de texto en inglés, así que hay menos fusiones para el español. 2) Las vocales con tilde y la «ñ» ocupan 2 bytes y, si no hay token que las contenga, se parten en bytes. (Lo desarrollan los módulos 01, 02 y 04.)"),
]) + "\n")

nb.md(caja("➡️ Siguiente módulo", r"""
**01 · Texto como bytes.** Hemos visto que «ñ» pesa 2 bytes y que el español paga un sobrecoste. En el módulo 01 implementas UTF-8 a mano, distingues code points, bytes y grafemas, normalizas (NFC/NFD/NFKC) y auditas tu corpus Políglota: la capa sobre la que se construye cualquier tokenizer.
"""))

nb.md(r"""
## 16. Referencias
Todas las referencias de arXiv fueron comprobadas (título y autores) el 25-oct-2026 y de nuevo, con venue y enlaces, el 26-oct-2026 (verificador de referencias).

* Kaplan, J. et al. (2020). *Scaling Laws for Neural Language Models.* arXiv:2001.08361. https://arxiv.org/abs/2001.08361 (aproximación de FLOPs por token, sección 2.1)
* Thakur, N., Reimers, N., Rücklé, A., Srivastava, A., Gurevych, I. (2021). *BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information Retrieval Models.* NeurIPS 2021 (Datasets and Benchmarks). arXiv:2104.08663. https://arxiv.org/abs/2104.08663
* Robertson, S., Zaragoza, H. (2009). *The Probabilistic Relevance Framework: BM25 and Beyond.* Foundations and Trends in Information Retrieval 3(4).
* Reimers, N., Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.* EMNLP-IJCNLP 2019. arXiv:1908.10084. https://arxiv.org/abs/1908.10084
* Radford, A. et al. (2019). *Language Models are Unsupervised Multitask Learners* (GPT-2). OpenAI.
* Wang, C., Cho, K., Gu, J. (2019). *Neural Machine Translation with Byte-Level Subwords.* arXiv:1909.03341. https://arxiv.org/abs/1909.03341
* Petrov, A., La Malfa, E., Torr, P., Bibi, A. (2023). *Language Model Tokenizers Introduce Unfairness Between Languages.* NeurIPS 2023. arXiv:2305.15425. https://arxiv.org/abs/2305.15425
* Ahia, O. et al. (2023). *Do All Languages Cost the Same? Tokenization in the Era of Commercial Language Models.* EMNLP 2023. arXiv:2305.13707. https://arxiv.org/abs/2305.13707
* Khattab, O., Zaharia, M. (2020). *ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT.* SIGIR 2020. arXiv:2004.12832. https://arxiv.org/abs/2004.12832
* Formal, T., Piwowarski, B., Clinchant, S. (2021). *SPLADE: Sparse Lexical and Expansion Model for First Stage Ranking.* SIGIR 2021 (short). arXiv:2107.05720. https://arxiv.org/abs/2107.05720
* Pagnoni, A. et al. (2024). *Byte Latent Transformer: Patches Scale Better Than Tokens.* arXiv:2412.09871. https://arxiv.org/abs/2412.09871
* Anthropic (19-sep-2024). *Introducing Contextual Retrieval.* https://www.anthropic.com/news/contextual-retrieval (con BM25 contextual + embeddings contextuales, los fallos de recuperación en el top-20 bajan un 49 %, del 5.7 % al 2.9 %, en su benchmark interno)
* Código: `tiktoken` (https://github.com/openai/tiktoken) · `rank_bm25` (https://pypi.org/project/rank-bm25/) · Hugging Face `wikimedia/wikipedia` (https://huggingface.co/datasets/wikimedia/wikipedia)
""")

nb.save(str(ROOT.parent / LPATH))

# ════════════════════════════════════════════════════════════════════════════
#  PROYECTO · Políglota v0
# ════════════════════════════════════════════════════════════════════════════
PPATH = f"{REL}/00_proyecto_intro.ipynb"
pb = Notebook("Módulo 00 · Proyecto: Políglota v0", colab_path=PPATH)

# ---- código de la SOLUCIÓN (se usa en la solución y para medir umbrales) ----
SOL_STATS = r'''
def estadisticas_corpus(docs):
    df = pd.DataFrame(docs)
    df["chars"] = df.text.str.len()
    df["bytes"] = df.text.map(lambda t: len(t.encode("utf-8")))
    df["palabras"] = df.text.str.split().map(len)
    g = df.groupby("lang").agg(n_docs=("id", "count"), chars_medio=("chars", "mean"),
                               bytes_medio=("bytes", "mean"), palabras_medio=("palabras", "mean"))
    g["bytes_por_char"] = g.bytes_medio / g.chars_medio
    return g.round(3)
'''
SOL_METRICS = r'''
def dcg_at_k(ranked_ids, rels, k=10):
    ranked = list(dict.fromkeys(ranked_ids))[:k]                      # dedup conservando orden
    return sum(rels.get(d, 0) / math.log2(i + 2) for i, d in enumerate(ranked) if rels.get(d, 0) > 0)

def ndcg_at_k(ranked_ids, rels, k=10):
    ideal = sorted((r for r in rels.values() if r > 0), reverse=True)[:k]
    idcg = sum(r / math.log2(i + 2) for i, r in enumerate(ideal))
    return 0.0 if idcg == 0 else dcg_at_k(ranked_ids, rels, k) / idcg

def recall_at_k(ranked_ids, rels, k=10):
    relevantes = {d for d, r in rels.items() if r > 0}
    if not relevantes:
        return 0.0
    return len(relevantes & set(list(dict.fromkeys(ranked_ids))[:k])) / len(relevantes)

def mrr_at_k(ranked_ids, rels, k=10):
    for i, d in enumerate(list(dict.fromkeys(ranked_ids))[:k]):
        if rels.get(d, 0) > 0:
            return 1.0 / (i + 1)
    return 0.0
'''
SOL_BM25 = r'''
class BM25:
    def __init__(self, k1=1.2, b=0.75, idf="lucene", epsilon=0.25):
        self.k1, self.b, self.idf_kind, self.epsilon = k1, b, idf, epsilon

    def fit(self, docs_tokens, doc_ids):
        self.doc_ids, self.N = list(doc_ids), len(docs_tokens)
        self.dl = np.array([len(t) for t in docs_tokens], dtype=float)
        self.avgdl = float(self.dl.mean())
        self.postings = defaultdict(list)                                  # término -> [(índice_doc, tf)]
        for i, toks in enumerate(docs_tokens):
            for term, tf in Counter(toks).items():
                self.postings[term].append((i, tf))
        n = {t: len(p) for t, p in self.postings.items()}
        if self.idf_kind == "lucene":
            self.idf = {t: math.log(1 + (self.N - c + 0.5) / (c + 0.5)) for t, c in n.items()}
        else:
            self.idf = {t: math.log(self.N - c + 0.5) - math.log(c + 0.5) for t, c in n.items()}
            piso = self.epsilon * sum(self.idf.values()) / len(self.idf)
            self.idf = {t: (v if v >= 0 else piso) for t, v in self.idf.items()}
        return self

    def scores(self, q_tokens):
        s = np.zeros(self.N)
        for term in q_tokens:
            for i, tf in self.postings.get(term, ()):
                norma = self.k1 * (1 - self.b + self.b * self.dl[i] / self.avgdl)
                s[i] += self.idf[term] * tf * (self.k1 + 1) / (tf + norma)
        return s
'''
SOL_IDENT = r'''
def split_ident(text):
    """'getHTTPResponse_code' -> ['get', 'http', 'response', 'code'] (+ el identificador entero si tenía '_')."""
    enteros = [w for w in tokenize_simple(text) if "_" in w]
    t = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    t = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", t).replace("_", " ")
    return tokenize_simple(t) + enteros
'''
SOL_FIT = r'''
def tok_doc(d):
    return split_ident(d["text"]) if d["lang"] == "code" else tokenize_simple(d["text"])

def construir_indice(docs, tok=tok_doc, **kw):
    return BM25(**kw).fit([tok(d) for d in docs], [d["id"] for d in docs])

def ranking(bm, queries, tok=split_ident, k=10):
    return {q["qid"]: bm.search(tok(q["text"]), k) for q in queries}
'''

# ---- Umbrales de rúbrica: MEDIDOS con la solución (corpus sintético, FAST_DEV, seed 42, n=110 consultas; oct-2026) ----
MED = dict(all=0.878, es=0.982, en=0.932, code=0.668, code_base=0.606)
UMB = dict(all=0.82, es=0.92, en=0.87, code=0.60, mejora=0.02)  # = medido − margen ≈ 0.06 (0.04 en la mejora de código)

pb.md(pb.badge() + r"""

# Proyecto 00 · Políglota v0: corpus, métricas y baseline BM25
**Módulo 00 · Intro, entorno e hilo conductor**

| | |
|---|---|
| **Nivel** | 🟢 Básico |
| **Duración estimada** | ≈ 1 h |
| **GPU recomendada** | Ninguna (CPU) |
| **Entregable** | `poliglota_v0.json` con el baseline medido (lo reutilizarás como punto de comparación en módulos posteriores) |
""")

pb.md(r"""
## Contexto de negocio
Eres ML engineer en **Políglota Labs**. La startup quiere lanzar un buscador para documentación técnica en español, inglés y código. Antes de gastar un euro en embeddings, tu CTO pide un **«Políglota v0»**: un buscador léxico (BM25) con un banco de evaluación pequeño pero fiable, para saber desde dónde partimos y qué tienen que superar los modelos futuros.

Tu misión: (1) cargar y entender el corpus, (2) implementar las métricas y el BM25 **tú mismo**, (3) medir el baseline por idioma con intervalo de confianza, (4) analizar dónde falla y (5) guardar el baseline.

**Conexión con módulos siguientes.** Este baseline se compara contra tu tokenizer propio (01–05, afecta a la tokenización léxica) y contra los embedders (09–13). La normalización Unicode (módulo 01) y el tokenizer BPE (módulo 02) cambiarán estos números.
""")

pb.md(r"""
## Dataset
Corpus Políglota (`carga_corpus`, ver lección 00): Wikipedia ES/EN (HF `wikimedia/wikipedia`) + código Python (CodeSearchNet), con una cadena **oficial → espejo → sintético**. En `FAST_DEV_RUN=True`: 150 artículos por idioma + 100 funciones y 110 consultas. La celda de carga te dirá si `source` es `real` o `synthetic`.
""")

pb.md(r"""
## Entregables y criterios de evaluación (rúbrica)

| # | Criterio | Umbral (corpus **sintético**, `FAST_DEV_RUN=True`) | Umbral (corpus **real**) |
|---|---|---|---|
| R1 | `estadisticas_corpus` devuelve las 3 filas y la suma de documentos correcta | tests ✅ | tests ✅ |
| R2 | `ndcg_at_k`, `recall_at_k`, `mrr_at_k` pasan los tests de casos límite (duplicados, sin relevantes, ejemplo a mano) | tests ✅ | tests ✅ |
| R3 | Tu `BM25` coincide con `rank_bm25.BM25Okapi` (idf=`okapi`, mismos $k_1$, $b$) | máx. \|Δscore\| ≤ 1e-6 | igual |
| R4 | nDCG@10 global de tu baseline | ≥ **@U_all@** | sin umbral calibrado*: reporta tu valor y compáralo con la solución |
| R5 | nDCG@10 por idioma (ES / EN) | ES ≥ **@U_es@**, EN ≥ **@U_en@** | sin umbral calibrado* |
| R6 | nDCG@10 en consultas de código con `split_ident` | ≥ **@U_code@** y mejora ≥ **+@U_mejora@** frente a `\w+` | no empeora frente a `\w+` |
| R7 | IC 95 % bootstrap calculado y `poliglota_v0.json` guardado con las claves requeridas | ✅ | ✅ |
| R8 | Análisis de errores escrito (≥ 3 hipótesis razonadas sobre las consultas que fallan) | manual | manual |

\* Los umbrales sintéticos son lo que **mide la solución de referencia** (nDCG@10 global = @G_all@, ES = @G_es@, EN = @G_en@, código = @G_code@; código con `\w+` = @G_cb@; n = 110 consultas, semilla 42) **menos un margen de ≈ 0.06**. No hemos podido medir la solución sobre Wikipedia real en el entorno de autoría (Hugging Face y Wikipedia estaban bloqueados), así que con datos reales no inventamos un umbral: la solución imprime sus valores al final del notebook para que compares.
"""
    .replace("@U_all@", f"{UMB['all']:.2f}").replace("@U_es@", f"{UMB['es']:.2f}").replace("@U_en@", f"{UMB['en']:.2f}")
    .replace("@U_code@", f"{UMB['code']:.2f}").replace("@U_mejora@", f"{UMB['mejora']:.2f}")
    .replace("@G_all@", f"{MED['all']:.3f}").replace("@G_es@", f"{MED['es']:.3f}").replace("@G_en@", f"{MED['en']:.3f}")
    .replace("@G_code@", f"{MED['code']:.3f}").replace("@G_cb@", f"{MED['code_base']:.3f}"))

pb.md(r"""
## 0. Preparación (celdas dadas: no hay que modificarlas)
""")
pb.code(r'''
!pip install -q numpy pandas matplotlib rank_bm25 regex
''')
pb.code(r'''
import math, random, re, sys, time
from collections import Counter, defaultdict
import numpy as np, pandas as pd
import matplotlib.pyplot as plt

SEED = 42
random.seed(SEED); np.random.seed(SEED)
FAST_DEV_RUN = True      # True: subconjunto pequeño (minutos). False: corpus mayor.
CHECKS: dict = {}        # aquí se registra el resultado de cada comprobación de la rúbrica

def chequea(nombre, fn):
    """Ejecuta fn() y registra ✅/❌/⏳ sin romper «Ejecutar todo»."""
    try:
        fn(); CHECKS[nombre] = True; print("✅", nombre)
    except NotImplementedError as e:
        CHECKS[nombre] = None; print("⏳ pendiente:", nombre, "→", e)
    except AssertionError as e:
        CHECKS[nombre] = False; print("❌", nombre, "→", e)
    except Exception as e:  # noqa: BLE001
        CHECKS[nombre] = False; print("💥", nombre, "→", type(e).__name__, e)
''')
_c = src_corpus_cells()
pb.code("# ── carga_corpus (celda 1/3) ──\n" + _c[0])
pb.code("# ── carga_corpus (celda 2/3) ──\n" + _c[1])
pb.code("# ── carga_corpus (celda 3/3) ──\n" + _c[2])
pb.code(r'''
# Utilidades dadas: tokenización léxica y ordenación determinista por score
import unicodedata
''' + SRC_BM25.split("class BM25")[0].replace("import math\nimport re\nimport unicodedata\nfrom collections import Counter, defaultdict\n\nimport numpy as np\n\n", "") + r'''

def rank_from_scores(scores, doc_ids, k=None):
    """Orden por score desc.; los empates se rompen por orden del corpus (reproducible)."""
    scores = np.asarray(scores, dtype=float)
    order = np.lexsort((np.arange(len(scores)), -scores))
    return [doc_ids[i] for i in (order[:k] if k else order)]

def buscar(bm, q_tokens, k=10):
    return rank_from_scores(bm.scores(q_tokens), bm.doc_ids, k)

def evaluate(run, qrels, k=10):
    """Promedia nDCG/Recall/MRR@k sobre las consultas con algún relevante (usa TUS funciones de métricas)."""
    n, tot = 0, dict(ndcg=0.0, recall=0.0, mrr=0.0)
    for qid, rels in qrels.items():
        if not any(r > 0 for r in rels.values()):
            continue
        tot["ndcg"] += ndcg_at_k(run.get(qid, []), rels, k); tot["recall"] += recall_at_k(run.get(qid, []), rels, k)
        tot["mrr"] += mrr_at_k(run.get(qid, []), rels, k); n += 1
    return {**{m: v / max(n, 1) for m, v in tot.items()}, "n_queries": n}
''')
pb.code(r'''
corpus = carga_corpus(fast_dev=FAST_DEV_RUN)
docs, queries, qrels, source = corpus["docs"], corpus["queries"], corpus["qrels"], corpus["source"]
print(f"source = {source!r} | {len(docs)} docs | {len(queries)} queries")
''')

pb.md(r"""
## TODO 1 · Estadísticas del corpus
Implementa `estadisticas_corpus(docs)`: un `DataFrame` indexado por `lang` con `n_docs`, `chars_medio`, `bytes_medio`, `palabras_medio` y `bytes_por_char` (= `bytes_medio / chars_medio`). «Bytes» es la longitud del texto codificado en **UTF-8**.

""" + pista(1, "Construye un `DataFrame` a partir de la lista de dicts y añade columnas con la longitud en caracteres, en bytes (`len(t.encode('utf-8'))`) y en palabras (`t.split()`). Después agrupa por `lang`.") + "\n\n" + pista(2, "`df.groupby('lang').agg(n_docs=('id', 'count'), chars_medio=('chars', 'mean'), ...)`. Calcula `bytes_por_char` como cociente de dos columnas del resultado."))
pb.code(r'''
def estadisticas_corpus(docs):
    # TODO: devuelve un DataFrame indexado por 'lang' con las 5 columnas indicadas
    raise NotImplementedError("TODO 1: implementa estadisticas_corpus")

def test_stats():
    g = estadisticas_corpus(docs)
    assert set(g.index) == {"es", "en", "code"}, "faltan idiomas en el índice"
    assert g.n_docs.sum() == len(docs), "n_docs no suma el total"
    assert (g.bytes_por_char >= 1).all(), "bytes_por_char no puede ser < 1 (un carácter ocupa ≥ 1 byte)"
chequea("R1 estadísticas", test_stats)
try:
    display(estadisticas_corpus(docs))
except NotImplementedError:
    pass
''')

pb.md(r"""
## TODO 2 · Métricas de retrieval
Implementa `ndcg_at_k`, `recall_at_k` y `mrr_at_k` (ganancia **lineal**, descuento $1/\log_2(i+1)$). Reglas: los **duplicados** en `ranked_ids` cuentan una vez; si no hay relevantes devuelven `0.0`; `rels` es `doc_id → relevancia` y relevante = `rel > 0`.

""" + pista(1, "Primero deduplica `ranked_ids` conservando el orden (`list(dict.fromkeys(...))`) y recorta a `k`. El DCG suma `rel / log2(posición + 1)`; con índice desde 0 es `log2(i + 2)`.") + "\n\n" + pista(2, "IDCG: ordena las relevancias `> 0` de mayor a menor, toma `k` y calcula el mismo DCG. nDCG = DCG / IDCG (o 0 si IDCG = 0). Recall@k = |relevantes ∩ top-k| / |relevantes|. MRR@k = 1/(posición del primer relevante)."))
pb.code(r'''
def ndcg_at_k(ranked_ids, rels, k=10):
    # TODO
    raise NotImplementedError("TODO 2a: implementa ndcg_at_k")

def recall_at_k(ranked_ids, rels, k=10):
    # TODO
    raise NotImplementedError("TODO 2b: implementa recall_at_k")

def mrr_at_k(ranked_ids, rels, k=10):
    # TODO
    raise NotImplementedError("TODO 2c: implementa mrr_at_k")

def test_metricas():
    r, rel = ["d3", "d1", "d7", "d2"], {"d1": 1, "d2": 1}
    assert abs(ndcg_at_k(r, rel, 4) - 0.6510) < 1e-3, "ejemplo a mano de la lección: nDCG@4 = 0.651"
    assert recall_at_k(r, rel, 4) == 1.0 and recall_at_k(r, rel, 1) == 0.0
    assert mrr_at_k(r, rel, 4) == 0.5 and mrr_at_k(r, rel, 1) == 0.0
    assert ndcg_at_k(["d1", "d1", "d1"], {"d1": 1}, 10) == 1.0, "los duplicados no deben inflar el DCG"
    assert ndcg_at_k(r, {}, 10) == 0.0 and recall_at_k(r, {}, 10) == 0.0 and mrr_at_k(r, {}, 10) == 0.0
    assert abs(ndcg_at_k(["b", "a"], {"a": 3, "b": 2}, 2) - (2 + 3 / math.log2(3)) / (3 + 2 / math.log2(3))) < 1e-9, "ganancia lineal con grados"
chequea("R2 métricas", test_metricas)
''')

pb.md(r"""
## TODO 3 · BM25 con índice invertido
Completa `fit` y `scores`. `fit` recibe `docs_tokens` (lista de listas de términos) y `doc_ids`; debe guardar `self.N`, `self.dl` (longitudes), `self.avgdl`, `self.postings` (`término → [(índice_doc, tf), ...]`) y `self.idf` (dict). Soporta `idf="lucene"` ($\ln(1+\frac{N-n+0.5}{n+0.5})$) e `idf="okapi"` ($\ln\frac{N-n+0.5}{n+0.5}$ con suelo $\epsilon\cdot\overline{\text{IDF}}$ para los negativos, $\epsilon=0.25$, como `rank_bm25`). `scores(q_tokens)` devuelve un `np.ndarray` de tamaño `N`.

""" + pista(1, "Para cada documento cuenta los términos con `Counter(tokens)` y añade `(i, tf)` a `postings[término]`. La *document frequency* $n_t$ es `len(postings[t])`.") + "\n\n" + pista(2, "En `scores`, recorre solo los términos de la consulta y, para cada `(i, tf)` de su lista de postings, suma `idf[t] * tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl[i] / avgdl))` a `s[i]`. El suelo de `okapi`: `piso = epsilon * media(idf)`; los `idf < 0` pasan a valer `piso`."))
pb.code(r'''
class BM25:
    def __init__(self, k1=1.2, b=0.75, idf="lucene", epsilon=0.25):
        self.k1, self.b, self.idf_kind, self.epsilon = k1, b, idf, epsilon

    def fit(self, docs_tokens, doc_ids):
        # TODO: guarda self.doc_ids, self.N, self.dl, self.avgdl, self.postings y self.idf
        raise NotImplementedError("TODO 3a: implementa BM25.fit")

    def scores(self, q_tokens):
        # TODO: devuelve un array (N,) con el score BM25 de cada documento
        raise NotImplementedError("TODO 3b: implementa BM25.scores")

def test_bm25():
    toks = [["a", "b", "b"], ["b", "c"], ["c", "c", "d"], ["e"]]
    bm = BM25(k1=1.2, b=0.75).fit(toks, ["0", "1", "2", "3"])
    s = bm.scores(["b"])
    assert s.shape == (4,) and s[3] == 0 and s[2] == 0 and s[0] > s[1] > 0, "b aparece 2 veces en el doc 0 (más largo) y 1 en el doc 1"
    assert buscar(bm, ["c"], 2) == ["2", "1"], "c: tf=2 en el doc 2 gana al doc 1"
chequea("R3a BM25 mini", test_bm25)
''')

pb.md(r"""
**Validación contra `rank_bm25`.** La librería es la referencia de industria (versión sencilla). Con la misma fórmula de IDF y los mismos $k_1$, $b$ los scores deben coincidir.
""")
pb.code(r'''
def test_vs_rank_bm25():
    from rank_bm25 import BM25Okapi
    toks = [tokenize_simple(d["text"]) for d in docs]
    ref = BM25Okapi(toks, k1=1.5, b=0.75)
    mio = BM25(k1=1.5, b=0.75, idf="okapi").fit(toks, [d["id"] for d in docs])
    dif = max(np.abs(ref.get_scores(q) - mio.scores(q)).max() for q in (tokenize_simple(x["text"]) for x in queries[:20]))
    assert dif <= 1e-6, f"máx |Δscore| = {dif:.2e} (> 1e-6): revisa la fórmula / el suelo de idf negativos"
chequea("R3 BM25 == rank_bm25", test_vs_rank_bm25)
''')

pb.md(r"""
## TODO 4 · Tokenización de código: dividir identificadores
En la lección vimos que dividir `snake_case` y `camelCase` ayuda en código. Implementa `split_ident(text)`: devuelve los términos de `tokenize_simple` aplicados al texto con los identificadores **divididos**, y además los identificadores enteros que contenían `_` (para no perder `os_path`). Ejemplo: `split_ident("getHTTPResponse_code")` ⊇ `['get', 'http', 'response', 'code']`.

""" + pista(1, "Inserta un espacio entre minúscula/dígito y mayúscula (`re.sub(r'([a-z0-9])([A-Z])', r'\\1 \\2', t)`), trata aparte las siglas (`HTTPResponse` → `HTTP Response`) y cambia `_` por espacio antes de `tokenize_simple`.") + "\n\n" + pista(2, "Dos `re.sub` (camelCase y siglas) + `.replace('_', ' ')`; luego `tokenize_simple(...)`. Para conservar los identificadores con guion bajo, usa primero `[w for w in tokenize_simple(text) if '_' in w]`."))
pb.code(r'''
def split_ident(text):
    # TODO
    raise NotImplementedError("TODO 4: implementa split_ident")

def test_split():
    assert {"get", "http", "response", "code"} <= set(split_ident("getHTTPResponse_code"))
    assert {"join", "path", "os_join_path"} <= set(split_ident("os_join_path(a, b)"))
    assert split_ident("Hola mundo") == ["hola", "mundo"]
chequea("R6a split_ident", test_split)
''')

pb.md(r"""
## TODO 5 · Construir el índice, buscar y medir por idioma
Construye **un único índice** con todos los documentos (así una consulta en español también compite contra documentos en inglés y código, como en el producto real). Tokeniza los documentos de tipo `code` con `split_ident` y el resto con `tokenize_simple`; las **consultas** se tokenizan siempre con `tokenize_simple` (son lenguaje natural, incluso las de código). Compara contra el baseline que usa `tokenize_simple` en todo y rellena el diccionario `RESULTADOS`.

""" + pista(1, "Una función `tok_doc(d)` que mire `d['lang']`. `BM25().fit([tok_doc(d) for d in docs], [d['id'] for d in docs])`.") + "\n\n" + pista(2, "`run = {q['qid']: buscar(bm, tokenize_simple(q['text']), 10) for q in queries}` y `evaluate(run, qrels_del_grupo)`, donde `qrels_del_grupo` filtra por `q['lang']`. Repite con el baseline sin `split_ident`."))
pb.code(r'''
RESULTADOS = {}

def evaluar_grupo(run, lang=None):
    qr = {q["qid"]: qrels[q["qid"]] for q in queries if lang is None or q["lang"] == lang}
    return evaluate(run, qr)["ndcg"]

def pipeline(tok_doc):
    # TODO: construye el índice global con tok_doc, busca todas las consultas (top-10) y devuelve (bm, run)
    raise NotImplementedError("TODO 5: implementa pipeline")

try:
    bm_base, run_base = pipeline(lambda d: tokenize_simple(d["text"]))
    bm_split, run_split = pipeline(lambda d: split_ident(d["text"]) if d["lang"] == "code" else tokenize_simple(d["text"]))
    RESULTADOS = {"ndcg_all": evaluar_grupo(run_split), "ndcg_es": evaluar_grupo(run_split, "es"), "ndcg_en": evaluar_grupo(run_split, "en"),
                  "ndcg_code": evaluar_grupo(run_split, "code"), "ndcg_code_base": evaluar_grupo(run_base, "code")}
    print({k: round(v, 3) for k, v in RESULTADOS.items()})
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''')
pb.code(r'''
# Gráfico: baseline vs split_ident por grupo
if RESULTADOS:
    grupos = ["es", "en", "code"]
    a = [evaluar_grupo(run_base, g) for g in grupos]; b = [evaluar_grupo(run_split, g) for g in grupos]
    x = np.arange(3); fig, ax = plt.subplots(figsize=(6.5, 3.6))
    ax.bar(x - 0.2, a, 0.4, label="tokenize_simple", color="#6B7280"); ax.bar(x + 0.2, b, 0.4, label="+ split_ident en código", color="#1F6FEB")
    ax.set_xticks(x, grupos); ax.set_ylim(0, 1.05); ax.set_ylabel("nDCG@10"); ax.set_title(f"Políglota v0 (corpus {source})"); ax.legend()
    plt.tight_layout(); plt.show()
''')
pb.md("> 👀 **Qué debes observar.** ES y EN casi no cambian (la división de identificadores solo se aplica al grupo `code`); en `code` la barra azul debe superar a la gris: partir `getUserName` en `get`, `user`, `name` (en los documentos) permite que una consulta en lenguaje natural como «get user name» los encuentre. Si la azul queda por debajo, revisa que `tok_doc` aplique `split_ident` solo a los documentos `code` (las consultas siguen con `tokenize_simple`).")

pb.md(r"""
## TODO 6 · Intervalo de confianza bootstrap
Implementa `bootstrap_ci(valores, n_boot=2000, alpha=0.05, seed=42)`: remuestrea **las consultas** con reemplazo `n_boot` veces y devuelve `(media, (lo, hi))` con los cuantiles `alpha/2` y `1-alpha/2` de las medias remuestreadas.

""" + pista(1, "`rng = np.random.default_rng(seed)`; `rng.choice(valores, size=(n_boot, len(valores)), replace=True)` te da todos los remuestreos de golpe.") + "\n\n" + pista(2, "`medias = remuestreos.mean(axis=1)`; `np.quantile(medias, [alpha/2, 1-alpha/2])`."))
pb.code(r'''
def bootstrap_ci(valores, n_boot=2000, alpha=0.05, seed=42):
    # TODO
    raise NotImplementedError("TODO 6: implementa bootstrap_ci")

def test_ci():
    v = np.array([0.0, 1.0] * 50)
    m, (lo, hi) = bootstrap_ci(v)
    assert abs(m - 0.5) < 1e-9 and 0.35 < lo < 0.5 < hi < 0.65, f"IC inesperado: {lo:.3f}-{hi:.3f}"
chequea("R7a bootstrap", test_ci)
if RESULTADOS:
    try:
        v = np.array([ndcg_at_k(run_split[q["qid"]], qrels[q["qid"]]) for q in queries])
        m, (lo, hi) = bootstrap_ci(v); RESULTADOS["ci95"] = [float(lo), float(hi)]
        print(f"nDCG@10 global = {m:.3f}  IC95% [{lo:.3f}, {hi:.3f}]  (n = {len(v)})")
    except NotImplementedError:
        pass
''')

pb.md(r"""
## TODO 7 · Análisis de errores
Lista las 5 consultas **de código** con peor resultado (la posición del relevante en el ranking completo, o «fuera del top-100»). Después, en la celda de texto siguiente, **escribe al menos 3 hipótesis** razonadas de por qué fallan (vocabulario, tokenización, idioma, ruido…), apoyándote en lo que ves.

""" + pista(1, "Para cada consulta de código pide el ranking completo (`k=len(docs)`) y busca la posición del único relevante con `.index(...)`.") + "\n\n" + pista(2, "Ordena por esa posición descendente y muestra `q['text']`, la posición y los primeros 200 caracteres del documento relevante (`docs` por id)."))
pb.code(r'''
def peores_consultas(bm, tok_q=tokenize_simple, lang="code", n=5):
    # TODO: devuelve una lista de (qid, texto_consulta, posición_del_relevante) con las n peores, de peor a mejor
    raise NotImplementedError("TODO 7: implementa peores_consultas")

try:
    por_id = {d["id"]: d for d in docs}
    for qid, texto, pos in peores_consultas(bm_split):
        rel_id = next(iter(qrels[qid]))
        print(f"[{qid}] pos={pos} | consulta: {texto!r}\n      relevante: {por_id[rel_id]['text'][:160]!r}\n")
except NotImplementedError as e:
    print("⏳ pendiente:", e)
except NameError:
    print("⏳ completa antes el TODO 5")
''')
pb.md(r"""
**✍️ Tus hipótesis (escribe aquí, ≥ 3):**

1. …
2. …
3. …
""")

pb.md(r"""
## TODO 8 · Guardar el baseline
Guarda `poliglota_v0.json` con las claves `source`, `n_docs`, `n_queries`, `k1`, `b`, `tokenizacion`, `ndcg_all`, `ndcg_es`, `ndcg_en`, `ndcg_code`, `ndcg_code_base`, `ci95`. En módulos posteriores lo cargarás para comparar tu nuevo tokenizer/embedder con este punto de partida.
""")
pb.code(r'''
import json, pathlib
CLAVES = ["source", "n_docs", "n_queries", "k1", "b", "tokenizacion", "ndcg_all", "ndcg_es", "ndcg_en", "ndcg_code", "ndcg_code_base", "ci95"]

def guardar_baseline(path="poliglota_v0.json"):
    # TODO: construye el dict con las CLAVES (valores de RESULTADOS + metadatos), guárdalo como JSON y devuélvelo
    raise NotImplementedError("TODO 8: implementa guardar_baseline")

def test_json():
    d = guardar_baseline()
    assert all(k in d for k in CLAVES), f"faltan claves: {[k for k in CLAVES if k not in d]}"
    assert json.loads(pathlib.Path("poliglota_v0.json").read_text())["source"] == source
chequea("R7b poliglota_v0.json", test_json)
''')

pb.md(r"""
## Rúbrica: comprobación automática
Ejecuta esta celda cuando hayas terminado. R8 (análisis de errores) es manual.
""")
UMB_JSON = repr(UMB)
pb.code(r'''
UMBRALES_SINTETICO = ''' + UMB_JSON + r'''   # medidos con la solución (ver tabla de la rúbrica)

def rubrica():
    filas = [(k, {True: "✅", False: "❌", None: "⏳"}[v]) for k, v in CHECKS.items()]
    if RESULTADOS:
        u = UMBRALES_SINTETICO
        if source == "synthetic":
            reglas = [("R4 nDCG@10 global", RESULTADOS["ndcg_all"], u["all"]), ("R5 ES", RESULTADOS["ndcg_es"], u["es"]),
                      ("R5 EN", RESULTADOS["ndcg_en"], u["en"]), ("R6 código con split_ident", RESULTADOS["ndcg_code"], u["code"]),
                      ("R6 mejora vs \\w+", RESULTADOS["ndcg_code"] - RESULTADOS["ndcg_code_base"], u["mejora"])]
            filas += [(f"{n} = {v:.3f} (≥ {t:.2f})", "✅" if v >= t else "❌") for n, v, t in reglas]
        else:
            print("ℹ️ corpus REAL: no hay umbrales calibrados; reporta y compara con la solución.")
            filas.append(("R6 split_ident no empeora código", "✅" if RESULTADOS["ndcg_code"] >= RESULTADOS["ndcg_code_base"] else "❌"))
    for n, e in filas:
        print(f"{e}  {n}")
    print("\n(R8: análisis de errores escrito → revísalo tú)")
rubrica()
''')

pb.md(r"""
## Retos extra (nivel experto)
1. **Ajusta $k_1$ y $b$** con una búsqueda en rejilla sobre un *split de validación* de consultas y reporta en un split de test distinto (¿cuánto sube y cuánto es sobreajuste con solo ~100 consultas? usa el bootstrap).
2. **Plegado de tildes** (`tokenize_simple(..., accents='fold')`): ¿cambia el nDCG en ES? ¿Cuándo daña (p. ej. «sí»/«si», «papá»/«papa»)?
3. **Vectoriza** `scores` con `scipy.sparse` (matriz término-documento) y compara velocidad con el índice invertido en `FAST_DEV_RUN=False`.
4. **Golden set honesto.** Construye 20 consultas que *no* copien el vocabulario del documento (parafraseadas a mano) y mide cuánto cae BM25 frente a las de «ítem conocido».
5. **IDF Lucene vs Okapi**: mide la diferencia de nDCG@10 y de rankings (tau de Kendall) entre ambas variantes.
""")

pb.md(r"""
## Reflexión
* El baseline de código es el más débil. Con lo que sabes del pipeline texto → bytes → tokens → embeddings, ¿qué **dos** módulos del curso atacan ese problema y por qué?
* ¿Qué decisión de **tokenización léxica** (acentos, mayúsculas, división de identificadores) tomarías en Políglota en producción y cómo la validarías sin sobreajustar a tu golden set?
* Si mañana cambias la normalización Unicode (módulo 01) de tus documentos, ¿qué tienes que volver a calcular? ¿Y si cambias el tokenizer del embedder (módulo 02)?
""")

pb.md(r"""
---
# ⛔ SPOILER — intenta resolverlo primero
Debajo está la solución de referencia completa y ejecutable. Si «Ejecutar todo» llega hasta aquí, estas celdas **sobrescriben** tus funciones con las de referencia (es útil para comprobar la rúbrica con resultados correctos).
""")
pb.code("# ── SOLUCIÓN · TODO 1 ──" + SOL_STATS)
pb.code("# ── SOLUCIÓN · TODO 2 ──" + SOL_METRICS)
pb.code("# ── SOLUCIÓN · TODO 3 ──" + SOL_BM25)
pb.code("# ── SOLUCIÓN · TODO 4 ──" + SOL_IDENT)
pb.code(r'''
# ── SOLUCIÓN · TODO 5, 6, 7, 8 ──
def pipeline(tok_doc):
    bm = BM25().fit([tok_doc(d) for d in docs], [d["id"] for d in docs])
    return bm, {q["qid"]: buscar(bm, tokenize_simple(q["text"]), 10) for q in queries}

bm_base, run_base = pipeline(lambda d: tokenize_simple(d["text"]))
bm_split, run_split = pipeline(lambda d: split_ident(d["text"]) if d["lang"] == "code" else tokenize_simple(d["text"]))
RESULTADOS = {"ndcg_all": evaluar_grupo(run_split), "ndcg_es": evaluar_grupo(run_split, "es"), "ndcg_en": evaluar_grupo(run_split, "en"),
              "ndcg_code": evaluar_grupo(run_split, "code"), "ndcg_code_base": evaluar_grupo(run_base, "code")}

def bootstrap_ci(valores, n_boot=2000, alpha=0.05, seed=42):
    rng = np.random.default_rng(seed)
    medias = rng.choice(valores, size=(n_boot, len(valores)), replace=True).mean(axis=1)
    return float(valores.mean()), tuple(np.quantile(medias, [alpha / 2, 1 - alpha / 2]))

v = np.array([ndcg_at_k(run_split[q["qid"]], qrels[q["qid"]]) for q in queries])
m, (lo, hi) = bootstrap_ci(v); RESULTADOS["ci95"] = [float(lo), float(hi)]

def peores_consultas(bm, tok_q=tokenize_simple, lang="code", n=5):
    out = []
    for q in (q for q in queries if q["lang"] == lang):
        rank = buscar(bm, tok_q(q["text"]), len(docs))
        rel = next(iter(qrels[q["qid"]]))
        out.append((q["qid"], q["text"], rank.index(rel) + 1))
    return sorted(out, key=lambda t: -t[2])[:n]

def guardar_baseline(path="poliglota_v0.json"):
    d = {"source": source, "n_docs": len(docs), "n_queries": len(queries), "k1": bm_split.k1, "b": bm_split.b,
         "tokenizacion": "tokenize_simple (+ split_ident en código)", **{k: RESULTADOS[k] for k in RESULTADOS}}
    pathlib.Path(path).write_text(json.dumps(d, indent=2, ensure_ascii=False))
    return d

print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in RESULTADOS.items()})
print(f"nDCG@10 global = {m:.3f}  IC95% [{lo:.3f}, {hi:.3f}]")
for qid, texto, pos in peores_consultas(bm_split):
    print(f"  pos={pos:>4} | {texto[:90]!r}")
chequea("R1 estadísticas", test_stats); chequea("R2 métricas", test_metricas); chequea("R3a BM25 mini", test_bm25)
chequea("R3 BM25 == rank_bm25", test_vs_rank_bm25); chequea("R6a split_ident", test_split); chequea("R7a bootstrap", test_ci)
chequea("R7b poliglota_v0.json", test_json)
rubrica()
''')
pb.md(caja("📌 Valores de referencia de la solución", r"""
Con corpus **sintético**, `FAST_DEV_RUN=True`, semilla 42 (oct-2026): nDCG@10 global 0.878, ES 0.982, EN 0.932, código 0.668 (0.606 con `\w+`). Con datos **reales** tus números serán distintos (no pudimos medirlos en el entorno de autoría); la celda anterior imprime los de tu ejecución. Guarda `poliglota_v0.json`: el módulo 15 lo usará como punto de partida.
"""))

pb.save(str(ROOT.parent / PPATH))
