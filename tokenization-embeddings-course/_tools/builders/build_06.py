"""Construye los notebooks del módulo 06 (lección + proyecto) y su README.

    python tokenization-embeddings-course/_tools/builders/build_06.py     # desde la raíz del repo
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from nbbuild import Notebook  # noqa: E402
import a3_common as C  # noqa: E402
import _a3_src06 as S  # noqa: E402
import _a3_proj06 as P  # noqa: E402

COURSE = "tokenization-embeddings-course"
SLUG = "06_tokenizer_free_bytes_blt"
MOD_DIR = os.path.join(HERE, "..", "..", SLUG)
LESSON_REL = f"{COURSE}/{SLUG}/{SLUG}.ipynb"
PROJ_REL = f"{COURSE}/{SLUG}/06_proyecto_tokenizer_free_bytes_blt.ipynb"
os.makedirs(os.path.join(MOD_DIR, "assets"), exist_ok=True)
open(os.path.join(MOD_DIR, "assets", ".gitkeep"), "a").close()

obs, box, details = C.observe, C.box, C.details

# =====================================================================================
#                                       LECCIÓN
# =====================================================================================
nb = Notebook("Módulo 06 · Tokenizer-free I: bytes y patches", colab_path=LESSON_REL)

nb.md(nb.badge() + r"""

# Módulo 06 · Tokenizer-free I: bytes y *patches* (de CANINE y ByT5 a BLT)

| | |
|---|---|
| **Nivel** | 🔴 Experto |
| **Duración estimada** | ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) |
| **GPU recomendada** | Ninguna para `FAST_DEV_RUN=True` (CPU, ≈ 6-10 min en total). Con `FAST_DEV_RUN=False`: T4 (≈ 3-5 unidades de Colab, estimación; el modo completo entrena modelos algo mayores, sigue siendo didáctico) |
| **Prerrequisitos** | 01 (bytes/UTF-8), 02 (BPE, bytes por token), 04 (fertilidad, coste por idioma), 05 (patologías que nacen del vocabulario) |
| **Madurez del tema** | 🟡/🔴: hay un resultado a escala (BLT, 8B) y pesos abiertos, pero ningún LLM de frontera conocido lo usa en producción (ver «Mapa de madurez») |

> **Contexto Políglota Labs.** Tras el módulo 05 tienes un informe de patologías del tokenizer: tokens sub-entrenados, cuentas de letras erróneas, «impuesto» en español. Tu CTO pregunta:
> *«¿y si el modelo leyera bytes y nos olvidáramos del vocabulario?»* Esta lección te da el mecanismo (parches por entropía), el coste real de tal decisión y un banco de pruebas diminuto para
> **comprobarlo tú mismo**, sin vender humo: lo que aquí reproduces es **didáctico y a escala diminuta**, no el resultado del paper.
""")

nb.md(r"""
## 1. Objetivos de aprendizaje

1. **Explicar** por qué un modelo a nivel de bytes es costoso (longitud de secuencia) y **por qué a escala el coste dominante es el FFN por posición, no la atención**.
2. **Comparar** CANINE, ByT5, MegaByte, SpaceByte, MambaByte y BLT por *cómo agrupan* los bytes y dónde gastan cómputo.
3. **Implementar** un modelo de entropía de bytes (tabla n-grama y transformer diminuto) y **derivar** parches con las dos reglas de BLT (umbral global y restricción monótona).
4. **Calibrar** el umbral para un tamaño medio de parche objetivo y **verificar** la propiedad de *incremental patching* (BLT sí, BPE no).
5. **Construir** un *MiniBLT* (codificador local con hash de n-gramas → atención cruzada → transformer global → atención cruzada → decodificador local) y **verificar su causalidad**.
6. **Calcular** FLOPs por byte de BPE, bytes y BLT y **medir** bits-por-byte (bpb) frente a un baseline BPE a escala diminuta.
7. **Evaluar críticamente** los resultados publicados (qué prueban y qué no) y **etiquetar** la madurez de cada técnica.
""")

nb.md("## 2. 🔁 Conexión con módulos anteriores\n\nResponde antes de seguir (la respuesta está plegada).\n\n" +
      details("1 · (Módulo 01) ¿Cuántos bytes UTF-8 ocupan «n», «ñ» y «🙂»? ¿Qué implica para un modelo que lee bytes en español?",
              "1, 2 y 4 bytes. El español ocupa ~1.0x-1.1x bytes por carácter respecto al inglés, pero otros alfabetos pagan 2-3 bytes por carácter: un modelo de bytes ve secuencias *más largas* para esos idiomas, igual que un BPE entrenado sobre inglés los trocea en más tokens.") + "\n\n" +
      details("2 · (Módulo 02) Si el vocabulario BPE crece (de 32K a 128K), ¿qué pasa con los bytes por token y con la capa de salida?",
              "Los tokens son más largos (menos pasos del transformer) pero la matriz de embedding/proyección de salida crece. El paper de BLT lo ilustra: Llama 2 → Llama 3 sube de 3.7 a 4.4 bytes/token con una tabla de embeddings 4x mayor (BLT §2.4). Es un compromiso *fijo* vocabulario-cómputo; BLT lo rompe porque el tamaño de parche no depende de ninguna tabla.") + "\n\n" +
      details("3 · (Módulo 05) ¿Qué patologías del tokenizer desaparecerían por construcción si el modelo viera bytes? ¿Cuáles no?",
              "Desaparecen: tokens sub-entrenados/glitch (no hay vocabulario que quede huérfano), dependencia de espacios/mayúsculas como *ids* distintos y gran parte del problema de contar letras. No desaparecen: sesgos de datos, aritmética mal formada, ataques de Unicode (los bytes siguen ahí) ni el coste: la secuencia es más larga o hace falta parchear."))

nb.md(r"""
> 🧭 **Ruta núcleo vs ampliación.** La lección tiene ≈ 72 celdas (≈ 3 h; las celdas de entrenamiento tardan 1–3 min en CPU). *Núcleo (≈ 2 h), lo que usa el proyecto:* secciones 3, 4 (FLOPs por byte), 6 (teoría del parcheo por entropía), 7.1–7.2 (modelo de entropía y calibración del umbral), 8 (arquitectura BLT) y 10 (qué dice el paper). *Ampliación (≈ 1 h):* 5 (familia ByT5/CANINE/MegaByte/SpaceByte), 7.3 (parcheo incremental), 9 (MiniBLT desde cero y su entrenamiento) y 11 (librerías). Si vas justo de tiempo, ejecuta las celdas de la sección 9 sin estudiarlas y vuelve a ellas tras el proyecto.
""")

nb.md(r"""
## 3. Intuición primero: la tokenización es una heurística de compresión

Un tokenizer BPE es un **compresor sin pérdida con un diccionario fijo**: agrupa los pares de bytes más frecuentes (módulo 02). El transformer gasta **el mismo cómputo en cada token**, aunque
unos sean triviales («ción» tras «ac») y otros decisivos (la primera letra de un nombre propio). Y el modelo **nunca ve los bytes**: ve ids opacos. De ahí salen los problemas que ya medimos
en los módulos 04-05 (impuesto multilingüe, glitch tokens, «strawberry»).

**La alternativa obvia es leer bytes.** Pero la secuencia se alarga ~4-5x (módulo 02) y la atención es cuadrática… aunque el paper de BLT recuerda que *a escala* el coste dominante son las capas
feed-forward que corren **en cada posición**, no la atención. La solución de la familia moderna es **agrupar bytes en parches** (*patches*) y correr el transformer grande **solo una vez por parche**:

* **Analogía de compresión.** Un compresor aritmético asigna más bits a lo impredecible. BLT hace lo análogo con el *cómputo*: mide con un modelo de bytes pequeño **cuánta incertidumbre** (entropía) hay en el siguiente byte y abre un parche nuevo — es decir, **gasta un paso del transformer grande** — donde la incertidumbre es alta.
* **Analogía de búsqueda/IR.** Es como indexar documentos: no llamas al reranker caro para *cada* documento, solo para los candidatos difíciles.
""")

nb.gemini("imagen", "M06-IMG-01", "El espectro de la tokenización: de bytes a parches",
          "Muestra la misma frase en cuatro granularidades (bytes, tokens BPE, parches fijos, parches dinámicos) y el compromiso entre control fino y número de pasos del transformer grande.",
          """Diagrama técnico limpio, fondo blanco, estilo infografía de paper (sans-serif legible, flechas claras, sin ilustraciones decorativas ni texto inventado). Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Formato 16:9.
Título superior: "El espectro de la tokenización: ¿cuántos bytes por paso del transformer?".
Composición: 4 filas horizontales apiladas, todas muestran la MISMA frase en español: "El gato duerme." (15 bytes, con el espacio escrito como ␣). A la izquierda de cada fila va una etiqueta en negrita; a la derecha, un texto gris pequeño.
Fila 1, etiqueta "Bytes": 15 cajitas grises, una por carácter (E, l, ␣, g, a, t, o, ␣, d, u, e, r, m, e, .). Texto derecha: "1 byte por paso · secuencia larga (15 pasos)".
Fila 2, etiqueta "Tokens BPE (vocabulario fijo)": 4 bloques naranjas contiguos con los textos "El", "␣gato", "␣duerme", ".". Texto derecha: "~4.4 bytes por token en Llama 3 (dato del paper de BLT) · ids opacos".
Fila 3, etiqueta "Parches fijos (MegaByte, k=4)": 4 bloques azules de igual ancho con los textos "El␣g", "ato␣", "duer", "me.". Texto derecha: "tamaño fijo · corta palabras al azar".
Fila 4, etiqueta "Parches dinámicos (BLT)": 5 bloques verdes de ancho distinto con los textos "El", "␣g", "ato", "␣d", "uerme." y encima de cada bloque una pequeña barra vertical cuya altura sugiere la entropía del primer byte (más alta en "g" y "d"). Texto derecha: "tamaño según la incertidumbre del siguiente byte (ilustrativo)".
Una flecha vertical a la izquierda de las filas, de arriba a abajo, con la leyenda "menos pasos del transformer grande ↓" y otra en el extremo opuesto "más control sobre los bytes ↑". Nota inferior en gris: "Segmentaciones ilustrativas; no son la salida de ningún modelo real".
Evita: ilustraciones decorativas, texto ilegible, números inventados distintos de los dados, flechas ambiguas, sombras 3D.""",
          "Cuatro filas con la frase «El gato duerme.» segmentada en bytes, tokens BPE, parches fijos y parches dinámicos",
          """Bytes      : [E][l][␣][g][a][t][o][␣][d][u][e][r][m][e][.]            15 pasos
BPE        : [El][␣gato][␣duerme][.]                                   4 pasos  (~4.4 B/token en Llama 3)
Fijos k=4  : [El␣g][ato␣][duer][me.]                                   4 pasos  (corta palabras)
Dinámicos  : [El][␣g][ato][␣d][uerme.]                                 5 pasos  (frontera donde sube la entropía; ilustrativo)""")
nb.md(obs("""
Cada bloque es un **paso del transformer grande**. Con bytes pagas 15; con BPE/parches pagas 4-5. La diferencia entre BPE y BLT no es *cuántos* pasos sino **quién decide dónde cortar**:
BPE lo decide una tabla estática aprendida *antes* (y el modelo no ve los bytes); BLT lo decide en línea con un modelo de entropía y el modelo **sí conserva el acceso a los bytes**.
"""))

nb.code(S.PIP)
nb.code(C.SETUP_COMMON + S.SETUP_EXTRA)
nb.md(r"""
### 3.1 Corpus Políglota (utilidades del módulo 00)

Las tres celdas siguientes son la implementación **canónica** de `carga_corpus()` (módulo 00, autor A1). Cadena: Wikipedia ES/EN vía Hugging Face → API pública de Wikipedia → texto **sintético**;
código: CodeSearchNet → funciones **reales** de la stdlib de Python. Si imprime «SINTÉTICO», los números absolutos de esta lección **no son comparables** con datos reales (las conclusiones cualitativas sí).
""")
for c in C.corpus_cells():
    nb.code(c)
nb.code(S.DATA)

nb.md(r"""
## 4. El coste de leer bytes: FLOPs por byte

Para una capa transformer con ancho $d$ y contexto $n$, el forward por posición cuesta aproximadamente

$$\text{FLOPs/posición/capa} \approx 2\,(4d^2 + 2\cdot 4d^2) + 4\,\tfrac{n}{2}\,d,$$

donde $4d^2$ son las proyecciones $Q,K,V,O$, $8d^2$ las dos matrices del FFN (con expansión 4x), y el último término es la atención causal (en media se atiende a $n/2$ posiciones). Cada MAC cuenta 2 FLOPs.
Para $d=4096$ el término de atención solo es relevante si $n$ es enorme: **el coste lo dominan las matrices que corren en cada posición** (de ahí el título del paper: *los parches escalan mejor que los tokens*).

Si el transformer grande corre una vez por **unidad** de $b$ bytes (token o parche), los FLOPs *por byte* de la parte global se dividen por $b$:

$$\text{FLOPs}_{\text{BLT}}/\text{byte} \;\approx\; \frac{L_g\,f(d_g,\,n/ps)}{ps} \;+\; (L_{enc}+L_{dec})\,f(d_l, w) \;+\; 2 d_l\cdot 256 \;+\; \text{cross}$$

con $ps$ el tamaño medio de parche, $f$ el coste por capa de arriba y $w$ la ventana de los modelos locales. (El paper da las fórmulas exactas en su §4.5 y Apéndice B; esta es una simplificación **didáctica**.)
""")
nb.code(S.FLOPS)
nb.md(obs("""
* La curva de BLT **cae como ~1/ps** hasta que el coste de los modelos locales (que corren por byte) pone un suelo. Con la config. ilustrativa, BLT con ps≈4.5 cuesta *lo mismo* que BPE (4.4 B/token): la gracia es que **ps no está atado a un vocabulario** y puedes subirlo.
* Un transformer isotrópico sobre bytes es ~4-5x más caro que BPE (un paso por byte). Ese es el muro que MegaByte/SpaceByte/BLT atacan.
* ⚠️ FLOPs ≠ latencia. El propio paper admite que su implementación puede no estar a la par en tiempo de reloj con los transformers tokenizados (§9).
"""))

nb.md(r"""
### 4.1 ¿Cuánto mide un «paso» en BPE? Bytes por token según vocabulario e idioma

Entrenamos BPE de varios tamaños con `tokenizers` (módulo 02-03) sobre el corpus Políglota y medimos **bytes por token**: es el «patch size» implícito del BPE.
""")
nb.code(S.BPE_LEN)
nb.md(obs("""
* El tamaño medio de «parche» de BPE **crece con el vocabulario** (y con lo repetitivo que sea el idioma/dominio: el código suele comprimirse más que la prosa). Para pasar de ~4.4 a ~8 bytes/token tendrías que agrandar mucho el vocabulario y su tabla de embeddings.
* Un vocabulario entrenado con poca cantidad de ES penaliza al ES frente al EN (módulo 04): en bytes no hay «impuesto de vocabulario», solo el impuesto de UTF-8.
* (Si el corpus es sintético, las magnitudes absolutas no son las de Wikipedia/CodeSearchNet reales: mira las *tendencias*.)
"""))

nb.md(r"""
## 5. La familia de modelos a nivel de byte/carácter

| Modelo | Idea | Cómo agrupa | Debilidad señalada |
|---|---|---|---|
| **CANINE** (2021) | Encoder de caracteres: convolución con *stride* + atención local → transformer profundo sobre secuencia reducida → *upsampling* | stride fijo (4) | Solo encoder (no genera); un arquitectura distinta por tarea |
| **ByT5** (2021) | T5 estándar sobre bytes con casi ningún cambio | no agrupa | Secuencias ~4x más largas: coste alto en entrenamiento e inferencia |
| **Hourglass / Dynamic Token Pooling** (2021-22) | Transformer jerárquico con *down/upsampling*; segmentación aprendida o por heurística | fija o dinámica | Escala pequeña (≤150M / 40M) |
| **MegaByte** (2023) | Decodificador multiescala: modelo *global* sobre parches + modelo *local* dentro del parche | parches **fijos** de $k$ bytes | Parches fijos cortan palabras al azar; en el análisis de BLT queda por detrás de BPE a escala |
| **SpaceByte** (2024) | Parche nuevo tras cada byte tipo espacio | por **espacios** | No varía el tamaño de parche; no gestiona bien todos los idiomas |
| **MambaByte** (2024) | SSM (Mamba) sobre bytes, sin parches | no agrupa | Escala moderada (353M–972M en el paper); coste lineal pero sin ahorro de pasos |
| **BLT** (2024) | Parches por **entropía** del siguiente byte + codificador/decodificador locales con *cross-attention* + hash de n-gramas | **dinámica**, controlable | Sin leyes de escala propias; ver «Limitaciones» más abajo |
| **H-Net** (2025) | El segmentador **se aprende** de extremo a extremo (módulo 07) | aprendida | Escala hasta ≈1.3B (FLOPs de un GPT-3 XL) en el paper |
""")
nb.md("### 5.1 Cuatro maneras de agrupar la misma frase\n\nCódigo sencillo para las tres reglas «sin modelo» (stride, espacios, BPE); la regla por entropía llega en la sección 7.")
nb.code(S.SCHEMES_TEXT)
nb.md(obs("""
* **Stride** corta en cualquier sitio (`El s|erv|idor…`): una misma palabra se parte de formas distintas según su posición — el modelo debe aprender todas.
* **Espacios** y **BPE** respetan palabras, pero BPE usa una tabla estática y SpaceByte *siempre* abre parche tras un espacio (no puede hacer parches más largos en texto predecible, ni más cortos dentro de una palabra difícil).
"""))

nb.md(r"""
## 6. Teoría: parches por entropía (BLT)

**Modelo de entropía.** Se entrena un modelo de lenguaje de bytes *pequeño* $p_e$ en los mismos datos. Para cada posición $i$ se calcula la incertidumbre sobre el *siguiente* byte dado el pasado:

$$H(x_i) \;=\; -\sum_{v\in\mathcal{V}} p_e(x_i = v \mid \boldsymbol{x}_{<i})\,\log p_e(x_i = v \mid \boldsymbol{x}_{<i}),\qquad \mathcal{V}=\{0,\dots,255\}$$

($\mathcal{V}$ es el alfabeto de bytes; $H$ se mide en bits si el logaritmo es base 2.) En el paper, el modelo de entropía de los experimentos principales es un transformer de **100M parámetros, 14 capas, ancho 512 y ventana deslizante de 512 bytes** (§4.2), y notan que si su campo receptivo es pequeño puede **codificarse como tabla de búsqueda** — justo lo que hace nuestra tabla n-grama.

**Dos reglas para abrir un parche en $i$** (BLT §2.3):

$$\text{Umbral global: } H(x_i) > \theta_g \qquad\qquad \text{Restricción monótona aproximada: } H(x_i) - H(x_{i-1}) > \theta_r$$

La segunda detecta *rupturas* de una entropía que debería decrecer dentro de un parche (tras la primera letra de una palabra, el resto es más fácil) y sufre menos *entropy drift* cuando el contexto cambia (§4.4).

**Ejemplo a mano** (con $\log_2$, en bits). Tras «el servid» el modelo de entropía casi sabe lo que viene: $p(\texttt{o})=0.9$ y reparte 0.1 entre otros 10 bytes ($0.01$ cada uno):
$H=-0.9\log_2 0.9-10\cdot0.01\log_2 0.01=0.137+0.664=\mathbf{0.80}$ bits. Tras «el␣» (inicio de palabra) supón 16 iniciales igual de probables: $H=\log_2 16=\mathbf{4}$ bits. Con $\theta_g=2$ bits se abre parche en el inicio de palabra y **no** dentro de «servidor». Es la misma idea que un compresor aritmético (módulo 02, §9.5): lo predecible cuesta pocos bits y se agrupa; lo sorprendente cuesta muchos y recibe su propio paso de cómputo.

**Propiedad clave: parcheo incremental.** Al generar no existen los bytes futuros, así que la función de parcheo debe cumplir $f_p(\boldsymbol{x}_{<i}) = f_p(\boldsymbol{x})_{<i}$. Como $H(x_i)$ solo depende de $\boldsymbol{x}_{<i}$, el parcheo por entropía la cumple. **BPE no**: el mismo prefijo se tokeniza distinto según lo que venga después.

**Bits por byte (bpb).** Para comparar modelos con distinta segmentación no sirve la perplejidad por token:

$$\mathrm{BPB}(\boldsymbol{x}) \;=\; \frac{\mathcal{L}_{CE}(\boldsymbol{x})}{\ln 2\cdot n_{\text{bytes}}}$$

con $\mathcal{L}_{CE}$ la entropía cruzada total (en nats) de la secuencia y $n_{\text{bytes}}$ su longitud en bytes. (Detalle fino: para modelos tokenizados es una *aproximación*, porque asume que la probabilidad de la cadena es la de su tokenización canónica — el paper de H-Net lo advierte.)
""")

nb.md("### 6.1 Un modelo de entropía como tabla de búsqueda (n-grama) y como transformer\n\nPrimero la **tabla n-grama** con suavizado Witten-Bell (conteos de bytes, orden $n$): no es una red neuronal, pero es exactamente un «modelo de bytes con campo receptivo pequeño».")
nb.code(S.NGRAM)
nb.md("Ahora el **transformer diminuto** de bytes (el análogo, en pequeño, de los 100M parámetros del paper):")
nb.code(S.NN_BYTELM)
nb.md(obs("""
* Con pocos datos, la **tabla n-grama de orden 4-5 suele ganar** al transformer diminuto (memoriza); con más datos y entrenamiento el transformer mejora a n-gramas. Para *decidir dónde cortar* nos basta cualquiera de los dos si captura «aquí empieza una palabra nueva».
* El paper de BLT ablaciona el modelo de entropía y ve **rendimientos decrecientes por encima de ~50M parámetros y 512 bytes de contexto** (§7): el modelo de patching **no necesita ser grande**.
"""))

nb.md("## 7. Parches por entropía en acción")
nb.md("### 7.1 Calibrar el umbral para un tamaño medio de parche")
nb.code(S.PATCHING)
nb.md("### 7.2 La entropía del siguiente byte (réplica en pequeño de la Figura 4 del paper)")
nb.code(S.ENTROPY_PLOT)
nb.md(obs("""
* La entropía **se dispara en el primer byte de una palabra** (qué viene después de un espacio) y **cae dentro de la palabra** cuando ya conoces el comienzo. Las barras naranjas son inicios de parche: tienden a coincidir con inicios de palabra, **sin que nadie le dijera dónde están los espacios**.
* En código aparecen picos en identificadores y literales, y parches largos en estructuras repetidas. En texto sintético con plantillas, las palabras de la plantilla son casi deterministas (parches largos) y las variables, impredecibles.
"""))
nb.code(S.STRIP)
nb.md(obs("""
* Cada fila es una regla de segmentación y **cada bloque, un paso del transformer grande** (lo que se paga en FLOPs). Cuenta bloques: *stride* corta a ciegas (bloques iguales que parten palabras), *espacios* y *BPE* siguen las palabras, y *entropía* corta donde el siguiente byte es difícil de predecir.
* Fíjate en que la fila de entropía tiende a coincidir con inicios de palabra **sin saber qué es un espacio**, pero también agrupa palabras muy predecibles en un solo bloque y parte las raras en varios: el cómputo se reparte según la dificultad, no según la ortografía.
"""))
nb.code(S.PATCH_PLOTS)
nb.code(S.ACUERDO)
nb.md(obs("""
* **Izquierda:** una sola perilla ($\\theta$) controla el tamaño medio de parche, y por tanto el coste. Calibramos $\\theta$ para el objetivo 4.5 B/parche (el valor de BLT-Entropy en su mezcla de entrenamiento).
* **Derecha:** stride tiene *una sola* longitud (barra); BPE y entropía tienen **distribuciones anchas** — la entropía puede dar parches largos en lo predecible y de 1 byte en lo difícil. Con $\\theta$ calibrado las medias coinciden: la diferencia es *dónde* se corta.
"""))
nb.code(S.LANG)
nb.md(obs("""
Con **el mismo $\\theta$** para todos, los idiomas/dominios con menor entropía por byte obtienen parches más largos (menos cómputo por byte) y los más impredecibles obtienen parches más cortos. Así el cómputo **sigue a la densidad de información** — y por eso, en teoría, un modelo de bytes con parches dinámicos no castiga a un idioma solo por su vocabulario (matiz: sí lo penaliza si su *entropía* intrínseca es mayor o está poco representado en el modelo de entropía).
"""))
nb.md("### 7.3 La propiedad de parcheo incremental")
nb.code(S.INCREMENTAL)
nb.md(obs("""
El parcheo por entropía es incremental por construcción (100%). BPE **no lo es**: si cortas a mitad de palabra, la tokenización del prefijo difiere de la de la palabra completa, así que un generador que decidiera «¿abro token?» mirando solo el pasado no coincidiría con el tokenizer entrenado. Esto es lo que hace que BPE use un tokenizer *aparte* y BLT pueda decidir los parches *durante la generación*.
"""))

nb.md(r"""
## 8. Arquitectura BLT

BLT tiene **tres** transformers (Figura 2 del paper):

1. **Codificador local** $\mathcal{E}$ (ligero, $l_E \ll l_G$ capas): embebe bytes ($256\times h_E$), les **suma embeddings hash de n-gramas** (n = 3…8) y aplica capas alternas de transformer local (atención con ventana causal) y **atención cruzada** que **agrupa bytes en parches**: las *consultas* son un *pooling* de los bytes del parche, las *claves/valores* son los bytes de ese parche (máscara por parche).
2. **Transformer latente global** $\mathcal{G}$ (grande, el que consume casi todos los FLOPs): autoregresivo sobre **parches**, con máscara causal por bloques.
3. **Decodificador local** $\mathcal{D}$ (ligero): atención cruzada **inversa** (consultas = bytes, claves/valores = parches) seguida de capas locales, que predicen los bytes del *siguiente* parche.

**Embeddings hash de n-gramas** (BLT §3.2.1). Para cada posición $i$ y cada $n\in\{3,\dots,8\}$ se hashea el n-grama $g_{i,n}=\{b_{i-n+1},\dots,b_i\}$ a una tabla de tamaño fijo y se suma:

$$e_i = x_i + \sum_{n=3}^{8} E^{\text{hash}}_n\!\big(\text{Hash}(g_{i,n})\big),\qquad \text{Hash}(g)=\text{RollPolyHash}(g)\bmod |E^{\text{hash}}_n|$$

Es la forma de dar al codificador *pseudo-vocabulario sin vocabulario*: n-gramas frecuentes obtienen embeddings propios sin tabla de tokens.

**Lo que el paper encuentra** (a escala 1B, 100B bytes; Tablas 7-9): la atención cruzada del **decodificador** es la más útil; los embeddings hash de n-gramas dan «grandes mejoras» en bpb (p. ej. de 0.850 a 0.826 en la distribución de entrenamiento al añadir n-gramas 3-8 con tablas de 400K); y, con hash, un codificador de **una capa** basta y conviene dar más capas al decodificador.
""")
nb.gemini("imagen", "M06-IMG-02", "Arquitectura del Byte Latent Transformer",
          "Los tres módulos de BLT (codificador local, transformer latente global, decodificador local), el agrupamiento por entropía y las atenciones cruzadas.",
          """Diagrama técnico limpio de arquitectura, fondo blanco, estilo figura de paper (sans-serif legible, flechas claras, sin ilustraciones decorativas ni texto inventado). Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Formato 16:9.
Título: "Byte Latent Transformer (BLT): tres módulos".
Composición, de IZQUIERDA a DERECHA, con una fila de bytes en la parte inferior y una fila de bytes en la parte superior:
1) Parte inferior izquierda: una fila de 12 cajitas grises (bytes) con los textos "B","e","t","t","e","r","␣","t","h","a","n","␣". Debajo, una barra pequeña "Modelo de entropía (pequeño, 100M)" en gris que apunta con una flecha punteada a las cajitas y produce la etiqueta "entropía del siguiente byte H(x_i)". Marca con líneas verticales finas verdes tres fronteras que dividen los 12 bytes en 4 parches de tamaño distinto (3, 2, 4 y 3 bytes) con la etiqueta "fronteras: H(x_i) > θ".
2) Bloque azul claro, etiqueta "Codificador local (ligero)": recibe los bytes; encima un bloque pequeño etiquetado "+ embeddings hash de n-gramas (n = 3…8)". Dentro, texto "capas de transformer local + atención cruzada".
3) Flecha ancha etiquetada "atención cruzada: bytes → parches (consulta = parche, clave/valor = bytes del parche)" que lleva a 4 círculos naranjas etiquetados "patch 1", "patch 2", "patch 3", "patch 4".
4) Bloque naranja grande en el centro, etiqueta "Transformer latente global (grande)", subetiqueta "se ejecuta UNA vez por parche". Recibe los 4 círculos y emite 4 círculos de salida.
5) Flecha ancha etiquetada "atención cruzada: parches → bytes (consulta = byte, clave/valor = parche)" que lleva a un bloque verde claro, etiqueta "Decodificador local (ligero)".
6) Parte superior derecha: fila de 12 cajitas grises (bytes de salida) con el texto "predicción del siguiente byte".
Una llave bajo el bloque global con la leyenda "la mayor parte de los FLOPs"; otra bajo los bloques locales: "corren por byte, pero son pequeños".
Evita: ilustraciones decorativas, texto ilegible, números no indicados, flechas ambiguas, más de tres módulos principales, logotipos.""",
          "Diagrama de BLT: bytes con modelo de entropía → codificador local → parches → transformer global → decodificador local → bytes",
          """bytes  B e t t e r _ t h a n _
        |  modelo de entropía H(x_i) -> fronteras |  |  |
        v
 [Codificador local + hash n-gramas + cross-attn]   (bytes -> parches)
        v
   patch1   patch2   patch3   patch4
        v
 [ Transformer latente global ]    (1 paso por parche; casi todos los FLOPs)
        v
 [Decodificador local + cross-attn]   (parches -> bytes)
        v
bytes  predicción del siguiente byte""")
nb.md(obs("""
Localiza dónde ocurre cada cosa: el **modelo de entropía** corre aparte (preprocesado) y solo decide fronteras; la **atención cruzada** hace el cambio de resolución (bytes↔parches); el **bloque grande** solo ve parches. Si cambias $\\theta$ cambias el número de parches y, con él, el coste del bloque naranja — sin tocar el modelo.
"""))
nb.gemini("imagen", "M06-IMG-03", "Cómputo uniforme por token vs. cómputo adaptativo por parche",
          "Contrasta un transformer tokenizado (mismo gasto en cada token) con BLT (gasto concentrado donde sube la entropía).",
          """Diagrama técnico limpio, fondo blanco, sans-serif legible, sin ilustraciones decorativas ni texto inventado. Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Formato 16:9.
Título: "¿Dónde se gasta el cómputo?".
Dos paneles horizontales apilados que comparten el mismo eje x: la frase "Daenerys Targaryen is in Game of Thrones" escrita en 41 casillas pequeñas (una por carácter, espacios como ␣).
Panel superior, título "Transformer con tokens BPE": encima de la frase, bloques naranjas CONTIGUOS de ancho similar con los textos "Dae", "ner", "ys", "␣Tar", "gar", "yen", "␣is", "␣in", "␣Game", "␣of", "␣Thrones"; cada bloque sostiene una columna naranja de la MISMA altura. Leyenda a la derecha: "el mismo cómputo en cada token".
Panel inferior, título "BLT con parches por entropía": una curva azul suave de entropía del siguiente byte sobre la frase, con picos al principio de cada palabra y valles dentro de ellas, y una línea roja horizontal discontinua etiquetada "umbral θ". Debajo, bloques verdes de ANCHO VARIABLE que empiezan donde la curva supera θ: columnas verdes altas y estrechas en los picos, columnas anchas y bajas donde la curva es baja. Leyenda a la derecha: "más cómputo donde hay más incertidumbre".
Nota inferior en gris: "Ilustración conceptual; los valores de entropía no son medidas reales".
Evita: valores numéricos de entropía inventados, adornos, texto ilegible, flechas ambiguas, sombras 3D.""",
          "Dos paneles: arriba cómputo igual por token BPE; abajo cómputo variable por parche según la curva de entropía",
          """BPE :  [Dae][ner][ys][ Tar][gar][yen][ is][ in][ Game][ of][ Thrones]
        ####  ####  ###  ####  ####  ####  ###  ###  #####  ###  ########   <- cómputo uniforme por token
BLT :  entropía:  /\\   /\\ ...  (picos al inicio de palabra, valles dentro)
        parches :  [Dae ner ys][ T][argaryen][ is][ in][ G][ame of][ T][hrones]   <- ancho/cómputo según θ (ilustrativo)""")
nb.md(obs("""
El ahorro de BLT no viene de «pensar menos» sino de **no repetir cómputo caro** en bytes triviales (las terminaciones de palabra) y de poder **gastar más** en los pocos bytes difíciles. En BPE ese reparto lo fija el diccionario, no el contenido.
"""))

nb.md(r"""
## 9. Implementación desde cero: *MiniBLT*

Implementamos las piezas de la figura en ~80 líneas de PyTorch. **Qué es y qué no es:**

| Sí lo hace | No lo hace (simplificaciones declaradas) |
|---|---|
| bytes → parches con la entropía de nuestra tabla n-grama; cross-attention con máscara por parche; transformer global **causal sobre parches**; decodificación de bytes con cross-attention al parche *anterior* | hash de n-gramas con un *rolling hash* simplificado y tablas diminutas (n=3-5, 4096 entradas); sin `FlexAttention` ni kernels: usamos máscaras densas; modelos de ≈1-2M parámetros; contexto de 128 bytes |

**Causalidad.** El byte $t$ se decodifica con (i) los bytes $\le t$ vía el codificador local causal y (ii) la salida del parche **anterior** $o_{j-1}$ del transformer global (que solo vio parches completos). Lo comprobamos con una prueba de «cambio un byte futuro y las salidas pasadas no varían».
""")
nb.code(S.MINIBLT_1)
nb.code(S.MINIBLT_2)
nb.md(r"""
### 9.1 Baselines y entrenamiento comparado

Entrenamos tres modelos con el **mismo transformer global** (mismo ancho y capas), la **misma ventana en bytes** (128, como hace BLT para no dar ventaja de contexto) y el mismo presupuesto de pasos:
(a) transformer **isotrópico sobre bytes**, (b) transformer sobre **tokens BPE** (el baseline de la industria), (c) **MiniBLT** con parches por entropía.
""")
nb.code(S.BASELINES)
nb.code(S.TRAIN)
nb.code(S.RESULTS_PLOT)
nb.md(obs("""
* A esta escala (≈1-2M de parámetros, minutos de CPU, 400 pasos, corpus pequeño o sintético) **BPE aprende mucho más rápido**: en la corrida de referencia del curso (corpus sintético) el transformer sobre BPE-512 llegó a ≈1.0 bpb, MiniBLT a ≈1.7 y el transformer de bytes a ≈2.9. **Es coherente con el paper**: ahí BPE gana con presupuestos pequeños y BLT lo alcanza «no muy lejos del punto compute-óptimo» (cruce en ≈150B-1T bytes según el tamaño, Tabla 2).
* Lo que sí debes ver: (1) MiniBLT **aprende** y supera al transformer de bytes con ≈ 1/4.3 de los pasos del transformer grande; (2) en FLOPs/byte queda al nivel de BPE; (3) la brecha con BPE depende de los pasos de entrenamiento y de los datos: no la generalices.
* **No repliques como conclusión** «BLT pierde frente a BPE»: este banco no tiene potencia estadística (una semilla, 300 pasos). Es una prueba de *mecanismo*.
"""))

nb.md(r"""
## 10. Resultados publicados: qué dice el paper (y qué no)

Cifras **reportadas por los autores** (Pagnoni et al., arXiv:2412.09871, v1 de diciembre 2024; ACL 2025). **No son nuestras mediciones** y pueden no reproducirse con otra receta.

| Resultado | Cifra reportada | Condiciones |
|---|---|---|
| Escala | Estudio FLOP-controlado hasta 8B parámetros y 4T bytes de entrenamiento | Primer estudio así para modelos de bytes, según los autores |
| Paridad con Llama 3 | Media de 7 benchmarks: 61.1 (BLT-Entropy) vs 60.0 (Llama 3), ambos entrenados con el mismo presupuesto de FLOPs (1T tokens ≈ 4.5T bytes) | 8B, dataset BLT-1T; umbral de inferencia reajustado de 0.6 a 0.1 |
| Ahorro de inferencia | «Hasta 50% menos FLOPs» con parches de 8 bytes (con un coste menor en métricas) | Escalado con FLOPs de inferencia fijos: baselines de ≈ 470M y 3.6B (tokenizer de Llama 2) y 450M y 3.9B (Llama 3) |
| Robustez al ruido | HellaSwag con ruido (media): 64.3 vs 56.9 (Llama 3, 1T tokens) y 64.3 (Llama 3.1, 16T tokens) | 8B |
| Conciencia ortográfica | CUTE: 54.1 vs 27.5 (Llama 3) y 20.0 (Llama 3.1); «contains char» 55.9 vs 0.0 | 8B |
| Traducción multilingüe | FLORES-101, media de 27 idiomas X→En: 14.0 vs 12.1; En→X: 6.4 vs 5.9 | 8B, 1T tokens |
""")
nb.code(S.PAPER_PLOT)
nb.md(obs("""
* La ganancia más llamativa **no es el promedio de benchmarks de conocimiento** (diferencia de ~1 punto) sino **las tareas de caracteres**: CUTE pasa de 27.5 a 54.1, y Llama 3.1 con 16x más datos *no* lo arregla (20.0). La conciencia ortográfica **no se compra solo con datos** si el modelo no ve bytes.
* **Qué NO demuestran**: que BLT supere a BPE en *cualquier* escala (el paper no hace leyes de escala propias, §9); ni que sea más rápido en tiempo de reloj; ni que valga para codificadores de embeddings (BLT es un decodificador de lenguaje).
"""))

nb.gemini("video", "M06-VID-01", "Patching dinámico por entropía, paso a paso",
          "Animación del proceso: llegan bytes, el modelo de entropía mide la incertidumbre, se supera el umbral y se abre un parche; el transformer grande solo se activa al cerrar cada parche.",
          """Video explicativo técnico de 25 segundos, 16:9, 1080p, ritmo calmado, sin voz en off, sin música intensa (opcional un fondo muy suave). Estilo: diagrama limpio sobre fondo blanco, tipografía sans-serif legible, paleta azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Sin ilustraciones decorativas.
Texto de la escena: la frase "El servidor procesa las peticiones." escrita como una fila de cajitas, una por byte (espacios como ␣), en el centro-inferior de la pantalla.
Guion por escenas:
0–4 s: Título "Parches dinámicos por entropía" aparece y se desvanece. Aparece la fila de cajitas grises vacías y, sobre ella, un eje con la etiqueta "H(siguiente byte) en bits" y una línea roja discontinua horizontal etiquetada "umbral θ".
4–14 s: los bytes se iluminan de izquierda a derecha, uno cada ~0.3 s. Sobre cada byte crece una barra azul con la entropía: alta (supera θ) en "E", "s" (de "servidor"), "p" (de "procesa"), "l" (de "las"), "p" (de "peticiones"); baja en el resto de letras dentro de cada palabra. Cuando una barra supera la línea roja se vuelve naranja y aparece una línea vertical verde que abre un nuevo parche; el parche anterior se rellena de verde claro y se cierra con un pequeño "clic" visual.
14–20 s: los parches cerrados suben hacia un bloque grande etiquetado "Transformer latente global" que parpadea UNA vez por parche; debajo, contador "pasos del transformer grande: 5" frente a un contador gris "bytes: 35".
20–25 s: texto final en pantalla: "Mismo contenido: 35 bytes → 5 parches. El umbral θ controla el coste." Se desvanece.
Texto en pantalla solo en español, con términos técnicos en inglés (patch, threshold).
Evita: voz en off, texto ilegible, cambios bruscos de cámara, números distintos de los indicados, logos, decoraciones.""",
          "Animación en la que una fila de bytes se agrupa en parches cuando la entropía supera un umbral y el transformer grande se activa una vez por parche",
          """t=0s   [bytes vacíos] ---- línea θ ---------------------
t=4-14s  E l ␣ s e r v i d o r ...   barras de entropía: ▂▇ ▂ ▇▂▂▂▂▂ ...  (naranja = supera θ -> | nuevo parche)
t=14-20s parches cerrados -> [Transformer global] parpadea 1 vez por parche   (5 pasos vs 35 bytes)
t=20-25s "35 bytes -> 5 parches. θ controla el coste."
""", duration="25 s")
nb.md(obs("""
Fíjate en el orden causal: el umbral se evalúa **con el pasado** (no hay que mirar adelante), el parche se **cierra** cuando aparece el siguiente byte difícil y solo entonces corre el bloque caro. Es lo que permite generar byte a byte con parches dinámicos.
"""))

nb.md("## 11. Con librerías de industria: ByT5, CANINE y BLT en Hugging Face")
nb.code(S.LIBS)
nb.md(obs("""
* **ByT5** no tiene vocabulario que aprender: ids = bytes + 3 reservados; **CANINE** usa directamente *code points* de Unicode (por eso un emoji es 1 posición, pero 4 bytes). Las longitudes muestran el coste: ~1 posición por byte (ByT5) o por carácter (CANINE) frente a ~4 bytes/token de BPE.
* Para BLT usa el repositorio `facebookresearch/blt` o los pesos del hub; la clase `BltForCausalLM` de `transformers` existe en versiones recientes, pero necesita pesos convertidos: **verifica el nombre del checkpoint** antes de planificar un experimento (los pesos oficiales de Meta son de acceso controlado).
"""))

nb.md(r"""
## 12. Mapa de madurez (a oct-2026)

Tras ver el mecanismo, el mini-experimento y lo que dice el paper, esta tabla resume qué es sólido y qué no.

| Técnica | Madurez | Quién la usa / respaldo público | Fuente |
|---|---|---|---|
| Subword BPE (referencia) | 🟢 | Prácticamente todos los LLM abiertos con tokenizer documentado | Módulos 02-04 |
| CANINE (encoder a nivel de carácter con *downsampling*) | 🟡 | Google Research; pesos publicados; no es base de modelos de frontera | Clark et al., TACL 2022 (arXiv:2103.06874) |
| ByT5 (T5 byte-a-byte) | 🟡 | Google Research; robusto a ruido, 4x más largo | Xue et al., TACL 2022 (arXiv:2105.13626) |
| MegaByte (parches fijos, local+global) | 🔴 | Meta; el propio paper de BLT lo ve por detrás de BPE a escala | Yu et al., 2023 (arXiv:2305.07185) |
| SpaceByte (parche tras cada espacio) | 🔴 | Investigación (autor único); cierra parte de la brecha con BPE | Slagle, 2024 (arXiv:2404.14408) |
| MambaByte (SSM sobre bytes) | 🔴 | Investigación (COLM 2024); modelos de 353M a 972M (y 1.6B en una prueba de velocidad) | Wang et al., 2024 (arXiv:2401.13660) |
| **BLT: parches por entropía** | 🟡/🔴 | Meta FAIR; hasta 8B / 4T bytes; ACL 2025; pesos 1B y 7B en HF (acceso controlado) | Pagnoni et al., 2024 (arXiv:2412.09871) |
| *Byte-ification* de un LLM ya entrenado (Bolmo) | 🔴 | Ai2: Bolmo 1B/7B a partir de Olmo 2 1B / Olmo 3 7B | Minixhofer et al., 2025 (arXiv:2512.15586) |
| Chunking aprendido de extremo a extremo (H-Net) | 🔴 | Cartesia/CMU (módulo 07) | Hwang, Wang, Gu (arXiv:2507.07955) |

> **Honestidad.** «🟡/🔴» significa: *hay un resultado a escala que respalda la idea, pero no hay evidencia pública de un LLM de frontera en producción con ella*. «Evidencia pública» ≠ «nadie lo usa»:
> los laboratorios no siempre documentan su tokenizer. Lo que sí es verificable es lo que aparece en los papers y en los repositorios abiertos.
""")

nb.md(r"""
## 13. 🏭 En producción

* **Quién lo hace público.** Meta FAIR publicó código y pesos de BLT (1B y 7B en el hub de Hugging Face; el README del repositorio remite a una licencia no comercial: léela antes de usarlo). Ai2 publicó **Bolmo 1B/7B**, obtenidos por *byte-ification* de Olmo 2 1B / Olmo 3 7B, y reporta que la conversión usa una fracción pequeña del presupuesto de preentrenamiento (arXiv:2512.15586). Cartesia/CMU publicaron los pesos de H-Net (módulo 07).
* **Lo que NO está documentado.** No he encontrado evidencia pública de un LLM de frontera cerrado (OpenAI, Anthropic, Google, Mistral…) que use parches de bytes en producción; sus tokenizers, cuando se documentan, siguen siendo de subpalabras. Trátalo como «sin evidencia pública», no como «no existe».
* **Fricciones de ingeniería** (del propio paper y de H-Net): las librerías están optimizadas para tokens fijos; la atención cruzada con máscaras por parche necesita `FlexAttention` o kernels propios; el cómputo y la memoria son **dinámicos** (lotes con parches desiguales) y el *batching* de inferencia con pasos de coste distinto es difícil; ahorro en FLOPs ≠ ahorro en milisegundos.
* **Dónde sí compensa hoy** (hipótesis razonables, no garantías): dominios donde el vocabulario no existe o es mal ajustado (ADN, código con símbolos raros, idiomas poco representados), tareas sensibles a la ortografía y entradas con ruido. Para **embedders de Políglota** (módulos 09-12), el estándar sigue siendo un encoder con tokenizer: BLT es un decodificador y no hay un recetario de embedders por parches.
* **Coste de cambiar de paradigma:** pierdes el ecosistema (caché de prefijos por token, *constrained decoding* por vocabulario, *logit bias*, facturación por token, evaluación por token) o tienes que rehacerlo.
""")

nb.md(r"""
## 14. 🧠 Secretos de la élite

1. **bpb o nada.** Comparar pérdida por token entre tokenizers es un error de categoría; compara **bits por byte** (o FLOPs por byte a calidad igual). Y recuerda que, para modelos tokenizados, bpb asume la tokenización canónica (H-Net, §Discusión).
2. **Iguala el contexto en bytes.** BLT mantiene constante el nº de bytes por lote (16M) y por secuencia (8k, luego 16k bytes) para que un patch size mayor no «trampee» con contexto más largo (§4.3). En comparativas bytes-vs-tokens, el control más olvidado es la ventana *en bytes*.
3. **El modelo de entropía es chico y barato… pero sensible a su contexto.** En BLT, el patching empieza a producir parches *progresivamente más largos* en contenido repetitivo (opciones de MMLU) por «entropy drift»; lo mitigan reiniciando el contexto del modelo de entropía en saltos de línea y usando la restricción monótona (§4.4).
4. **El umbral es una perilla de inferencia.** BLT-Entropy se entrena con un umbral de 0.6 y en evaluación lo bajan a 0.1, ganando precisión a costa de más pasos (§5.2): el *patch size* es una palanca de calidad/coste que BPE no ofrece.
5. **Los hash de n-gramas son parte del resultado, no un adorno.** La ablación (Tabla 8) los llama «vitales» para igualar a los tokenizados; sin ellos el codificador local debería ser mucho mayor.
6. **Más datos no arreglan lo que el tokenizer oculta.** CUTE: Llama 3.1 (16T tokens) obtiene 20.0 frente a 54.1 de BLT (1T) (Tabla 3). Si tu producto depende de manipulación de caracteres, el cuello de botella es la representación.
7. **Las leyes de escala heredadas pueden ser subóptimas.** BLT usa la proporción datos/parámetros compute-óptima de Llama 3 (hecha para BPE); los autores admiten que podría no ser la óptima para BLT (§9).
8. **El FLOP no es el reloj.** El paper reconoce que su implementación puede no igualar el tiempo de reloj de los transformers tokenizados (§9). Mide latencia p50/p99 reales antes de vender el ahorro.
""")

nb.md(r"""
## 15. ⚠️ Errores comunes

* **Usar perplejidad por token** para comparar byte-level con BPE. Usa bpb.
* **Dar más contexto en bytes** al modelo de parches que al baseline y atribuirle la mejora al patching.
* **Calibrar el umbral en validación o test** (o con otra mezcla de datos): calíbralo en entrenamiento y reporta el tamaño medio de parche *resultante* en test. Cambiar de dominio cambia el tamaño de parche (y el coste).
* **Dejar fuga de futuro:** si el parche abre en $i$ por un cálculo que mira $x_{\ge i}$, el modelo ve el futuro. Verifica causalidad con una prueba de perturbación (como la de MiniBLT).
* **Creer que «tokenizer-free» = «sin preprocesado»:** sigues necesitando normalización Unicode (módulo 01), límites de longitud y manejo de bytes inválidos.
* **Generalizar un banco diminuto:** 300 pasos y una semilla no concluyen nada sobre 8B. Repite con semillas, aumenta datos y reporta incertidumbre antes de afirmar.
""")

nb.md(r"""
## 16. Autoevaluación

""" + "\n\n".join([
    details("1 · (Cálculo) Un BPE da 4.4 bytes/token y BLT 8 bytes/parche. Con el mismo modelo global, ¿qué fracción de los pasos del transformer grande se ahorra? ¿Y de los FLOPs totales si el modelo global es el 100% del coste de BPE y los modelos locales de BLT añaden un 10% de ese coste?",
            "Pasos globales por byte: 1/4.4 = 0.227 frente a 1/8 = 0.125, es decir 0.125/0.227 = 0.55 → **−45%** de pasos del transformer grande. FLOPs totales de BLT relativos a BPE: 0.55 (global) + 0.10 (locales) = **0.65**, es decir ≈ −35%. Cuanto más dominante sea el global, más cerca de ese −45%; el paper habla de ahorros «de hasta ~50%» con parches de 8 bytes."),
    details("2 · (Cálculo) Un modelo BPE tiene entropía cruzada de 2.1 nats por token y 4.4 bytes/token. ¿Cuál es su bpb?",
            "bpb = 2.1 / (ln 2 · 4.4) = 2.1 / 3.050 = **0.689** bits por byte."),
    details("3 · (Diagnóstico) Tu modelo de parches produce parches cada vez más largos al final de un prompt con muchas opciones A/B/C/D repetidas. ¿Qué sucede y cómo se mitiga?",
            "El modelo de entropía ve el patrón repetido en su contexto y su entropía cae (*entropy drift*), con lo que casi nunca supera el umbral. BLT lo mitiga reiniciando el contexto del modelo de entropía en saltos de línea y usando la restricción monótona aproximada en vez del umbral global."),
    details("4 · (Diagnóstico) Una compañera mide «BLT-diminuto pierde con BPE-diminuto por 0.05 bpb» con una semilla y 300 pasos. ¿Qué objetarías?",
            "Falta de potencia: una semilla, pocos pasos, corpus pequeño/sintético, modelos fuera del régimen compute-óptimo (el paper ve que BPE gana con poco cómputo y BLT cruza más tarde). Hay que repetir con semillas, reportar intervalos y comparar a FLOPs iguales."),
    details("5 · (Transferencia) Políglota quiere un embedder multilingüe ES/EN/código robusto a erratas. ¿Qué idea de este módulo reutilizarías y cuál no?",
            "Reutilizable: agrupar por entropía/costes variables, hash de n-gramas como entrada subléxica robusta (fastText-style), evaluación con perturbaciones de ortografía. No reutilizable tal cual: BLT es un decodificador de lenguaje y su salida son bytes; para un embedder necesitas pooling sobre una representación de secuencia (CANINE es un encoder, pero no es SOTA en retrieval)."),
    details("6 · (Transferencia) ¿Por qué un generador autoregresivo con BPE necesita un tokenizer externo y BLT no necesita un segmentador externo en inferencia?",
            "BPE no es incremental: la segmentación de un prefijo depende del futuro, así que se aplica *antes*. El parcheo por entropía es incremental: la decisión en el byte $i$ solo depende de $x_{<i}$, por lo que se puede ejecutar durante la generación."),
    details("7 · (Recuerdo) ¿Por qué BLT añade embeddings hash de n-gramas al codificador?",
            "Dan al codificador información de n-gramas frecuentes (3…8) sin un vocabulario de tokens, lo que mejora mucho el bpb (Tabla 8) y permite un codificador local de una sola capa."),
]))

nb.md(r"""
## 17. Referencias

Todas verificadas (título/autores/fecha) consultando arXiv o el ACL Anthology en la fecha de redacción.

* Pagnoni, Pasunuru, Rodriguez, Nguyen, Muller, Li, Zhou, Yu, Weston, Zettlemoyer, Ghosh, Lewis, Holtzman, Iyer. **Byte Latent Transformer: Patches Scale Better Than Tokens.** arXiv:2412.09871 (dic. 2024); ACL 2025 (Long Papers), <https://aclanthology.org/2025.acl-long.453>. Código: <https://github.com/facebookresearch/blt>.
* Clark, Garrette, Turc, Wieting. **CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation.** TACL 2022, arXiv:2103.06874.
* Xue et al. **ByT5: Towards a token-free future with pre-trained byte-to-byte models.** TACL 2022, arXiv:2105.13626.
* Yu, Simig, Flaherty, Aghajanyan, Zettlemoyer, Lewis. **MEGABYTE: Predicting Million-byte Sequences with Multiscale Transformers.** arXiv:2305.07185.
* Slagle. **SpaceByte: Towards Deleting Tokenization from Large Language Modeling.** arXiv:2404.14408.
* Wang, Gangavarapu, Yan, Rush. **MambaByte: Token-free Selective State Space Model.** COLM 2024, arXiv:2401.13660.
* Nawrot et al. **Hierarchical Transformers Are More Efficient Language Models.** arXiv:2110.13711. · Nawrot et al. **Efficient Transformers with Dynamic Token Pooling.** arXiv:2211.09761.
* Hwang, Wang, Gu. **Dynamic Chunking for End-to-End Hierarchical Sequence Modeling.** arXiv:2507.07955 (ICLR 2026) — módulo 07.
* Videau et al. **From Bytes to Ideas: Language Modeling with Autoregressive U-Nets.** NeurIPS 2025, arXiv:2506.14761.
* Minixhofer et al. **Bolmo: Byteifying the Next Generation of Language Models.** arXiv:2512.15586.
* Schmidt et al. **Tokenization Is More Than Compression.** EMNLP 2024, arXiv:2402.18376.
* Neitemeier et al. **Hierarchical Autoregressive Transformers: Combining Byte- and Word-Level Processing…** arXiv:2501.10322.
* Documentación: Hugging Face `transformers` (`ByT5Tokenizer`, `CanineTokenizer`, `BltForCausalLM`).

## 18. Siguiente paso

El **proyecto** (`06_proyecto_tokenizer_free_bytes_blt.ipynb`) te pide construir un *patcher entrópico* y compararlo con BPE en estabilidad, compresión y coste. En el **módulo 07** el segmentador deja de ser una heurística externa y se **aprende** (H-Net), y veremos cómo *cambiar el tokenizer* de un modelo ya entrenado.
""")

nb.save(os.path.join(MOD_DIR, f"{SLUG}.ipynb"))

# =====================================================================================
#                                       PROYECTO
# =====================================================================================
P.build(LESSON_REL, PROJ_REL, MOD_DIR, SLUG)

# =====================================================================================
#                                       README
# =====================================================================================
README = r"""# Módulo 06 · Tokenizer-free I: bytes y *patches*

**Nivel:** 🔴 Experto · **Duración:** ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) · **Cómputo:** CPU en `FAST_DEV_RUN=True` (≈ 6-10 min); T4 opcional en modo completo

| Archivo | Contenido |
|---|---|
| `06_tokenizer_free_bytes_blt.ipynb` | Lección: coste de leer bytes (FLOPs/byte), familia CANINE/ByT5/MegaByte/SpaceByte/MambaByte, entropía del siguiente byte, parches por entropía (umbral global y restricción monótona), parcheo incremental, arquitectura BLT, **MiniBLT** desde cero y comparación con BPE a escala diminuta, resultados publicados, ByT5/CANINE/BLT en Hugging Face |
| `06_proyecto_tokenizer_free_bytes_blt.ipynb` | Proyecto: **mini patcher entrópico vs BPE** (plantilla con TODOs, pistas, rúbrica calibrada y solución tras SPOILER) |
| `assets/` | Imágenes/video de Gemini: `M06-IMG-01.png`, `M06-IMG-02.png`, `M06-IMG-03.png`, `M06-VID-01.mp4` |

## Objetivos
1. Explicar por qué leer bytes es caro y cómo los parches recuperan el coste (FLOPs por byte).
2. Comparar CANINE, ByT5, MegaByte, SpaceByte, MambaByte y BLT.
3. Implementar un modelo de entropía de bytes y derivar parches (umbral global / monótono), calibrando el tamaño medio.
4. Verificar la propiedad de parcheo incremental y la causalidad de un modelo con parches.
5. Construir un MiniBLT y compararlo (con honestidad estadística) con un baseline BPE.
6. Leer críticamente los resultados del paper de BLT y etiquetar la madurez (🟡/🔴).

## Datasets
Corpus Políglota (`carga_corpus()` del módulo 00): Wikipedia ES/EN (HF) + CodeSearchNet; fallback sintético + funciones reales de la stdlib de Python. **Estado de pruebas:** en el entorno de autoría Hugging Face estaba bloqueado, así que se validó con el corpus **sintético** (+ código real de la stdlib). Las conclusiones cualitativas se sostienen; los números absolutos no son comparables con datos reales.

## Lecturas
Pagnoni et al. 2024 (BLT, arXiv:2412.09871) · Yu et al. 2023 (MegaByte, arXiv:2305.07185) · Slagle 2024 (SpaceByte, arXiv:2404.14408) · Xue et al. 2022 (ByT5, arXiv:2105.13626) · Clark et al. 2022 (CANINE, arXiv:2103.06874) · Wang et al. 2024 (MambaByte, arXiv:2401.13660).

## Enlaces
Anterior: [05 · Patologías y robustez](../05_patologias_robustez/) · Siguiente: [07 · Tokenizer-free II y tokenizer transfer](../07_hnet_tokenizer_transfer/)
"""
with open(os.path.join(MOD_DIR, "README.md"), "w", encoding="utf-8") as f:
    f.write(README)
print("README escrito")
