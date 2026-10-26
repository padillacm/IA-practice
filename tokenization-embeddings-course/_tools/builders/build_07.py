"""Construye los notebooks del módulo 07 (lección + proyecto) y su README.

    python tokenization-embeddings-course/_tools/builders/build_07.py     # desde la raíz del repo
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from nbbuild import Notebook  # noqa: E402
import a3_common as C  # noqa: E402
import _a3_src07 as S  # noqa: E402
import _a3_proj07 as P  # noqa: E402

COURSE = "tokenization-embeddings-course"
SLUG = "07_hnet_tokenizer_transfer"
MOD_DIR = os.path.join(HERE, "..", "..", SLUG)
LESSON_REL = f"{COURSE}/{SLUG}/{SLUG}.ipynb"
PROJ_REL = f"{COURSE}/{SLUG}/07_proyecto_hnet_tokenizer_transfer.ipynb"
os.makedirs(os.path.join(MOD_DIR, "assets"), exist_ok=True)
open(os.path.join(MOD_DIR, "assets", ".gitkeep"), "a").close()
obs, details = C.observe, C.details

nb = Notebook("Módulo 07 · H-Net y tokenizer transfer", colab_path=LESSON_REL)

nb.md(nb.badge() + r"""

# Módulo 07 · Tokenizer-free II (H-Net) y *tokenizer transfer*

| | |
|---|---|
| **Nivel** | 🔴 Experto |
| **Duración estimada** | ≈ 6 h (lección ≈ 3.5 h + proyecto ≈ 2.5 h) |
| **GPU recomendada** | `FAST_DEV_RUN=True`: **CPU** (≈ 12-15 min en total). Modo completo: **L4** recomendada (≈ 6-10 unidades de Colab, estimación) para ajustar un GPT-2 pequeño real; T4 sirve con lotes menores |
| **Prerrequisitos** | 02-04 (BPE, vocabularios), 05 (patologías), **06 (BLT y parches por entropía)**; adelanto del 09 (matriz de embeddings y weight tying) |
| **Madurez del tema** | H-Net 🔴 (arXiv 2025, ICLR 2026, ≤1.3B de FLOPs equivalentes) · tokenizer transfer 🟡 (varias técnicas publicadas y código abierto; sin receta única) |

> **Contexto Políglota Labs.** Dos preguntas llegan a tu mesa. (1) *Producto:* «¿merece la pena apostar por un modelo sin tokenizer, en el que el **segmentador se aprende**?» (2) *Costes:* «Tenemos un modelo
> pequeño preentrenado con un tokenizer en inglés y código; el español sale en el doble de tokens. ¿Podemos **cambiarle el tokenizer** sin reentrenar de cero?» Esta lección responde a ambas con código que corre en CPU
> y con una dosis de escepticismo: lo que reproduces es **didáctico y diminuto**; las cifras de los papers son de los autores.
""")

nb.md(r"""
## 1. Objetivos de aprendizaje

1. **Explicar** el *dynamic chunking* de H-Net: módulo de *routing*, *downsampler*, suavizado (*smoothing*), *upsampler* con *straight-through estimator* y **ratio loss**, y por qué cada pieza hace falta.
2. **Implementar** un H-Net de una etapa en miniatura (PyTorch) y **verificar** su causalidad; **observar** cómo el modelo aprende fronteras sin supervisión.
3. **Comparar** el chunking aprendido con la heurística de espacios (SpaceByte) y con *pooling* fijo, y con el patching por entropía del módulo 06.
4. **Argumentar** con evidencia a favor y en contra de «¿está muerta la tokenización?», distinguiendo lo que los papers prueban de lo que no.
5. **Clasificar** las técnicas de *tokenizer transfer* (FVT, WECHSEL, FOCUS, Trans-Tokenization, ZeTT) por lo que necesitan y lo que hacen.
6. **Implementar** inicializaciones de embeddings para vocabulario nuevo (aleatoria, media, Hewitt, FVT, FOCUS-lite, WECHSEL-lite) y **medir** su efecto en bits-por-byte antes y después de un ajuste corto.
7. **Diseñar** un protocolo de evaluación honesto para un cambio de tokenizer (bpb, no pérdida por token).
""")

nb.md("## 2. 🔁 Conexión con módulos anteriores\n\n" +
      details("1 · (Módulo 06) ¿Qué decide dónde se corta en BLT y qué lo hace no diferenciable?",
              "Un modelo de bytes **aparte** (el modelo de entropía) mide $H(x_i)$ y un umbral $\\theta$ decide: es una decisión discreta tomada *antes* y fuera del grafo de la red principal, por lo que el segmentador no recibe gradiente del objetivo de lenguaje. H-Net quiere que esa decisión se aprenda de extremo a extremo.") + "\n\n" +
      details("2 · (Módulo 02/04) ¿Por qué no puedes comparar la pérdida por token de dos tokenizers distintos?",
              "Porque cada token cubre un número distinto de bytes: un tokenizer con tokens más largos tiene mayor pérdida *por token* aunque modele mejor el texto. Hay que normalizar por bytes (bpb) — idea que usamos otra vez aquí.") + "\n\n" +
      details("3 · (Módulo 05) Un token del vocabulario casi no aparece en el corpus de entrenamiento del modelo. ¿Qué le pasa a su embedding y qué implicaría para tokens recién añadidos?",
              "Sus filas de embedding reciben pocos gradientes y quedan cerca de la inicialización (tokens sub-entrenados/glitch). Un token **nuevo** tiene el mismo riesgo: si su inicialización es mala, el modelo tarda en aprenderlo o lo trata como ruido; por eso la inicialización importa."))

nb.md(r"""
## 3. Intuición primero

**Del módulo 06 al 07.** BLT demostró que agrupar bytes en parches funciona, pero con una pieza *externa y heurística*: un modelo de entropía entrenado aparte y un umbral. Pregunta natural: *¿y si el modelo aprendiera por sí solo dónde cortar, y además a varios niveles (bytes → palabras → frases)?* Eso es **H-Net** (Hwang, Wang y Gu, 2025): una red jerárquica tipo **U-Net** cuyo *downsampling* es **dinámico y aprendido** junto con el resto del modelo.

* **Analogía de compresión.** Una cadena de compresores donde cada etapa decide qué muestras conservar. Lo difícil es entrenar una decisión *discreta* («conservo este vector o no») con descenso de gradiente. H-Net lo consigue con tres trucos: un *router* basado en cambio de contexto, un **suavizado** que hace diferenciable la reconstrucción y una **ratio loss** que evita el colapso (todo o nada).
* **Analogía de recsys.** Es como un *mixture-of-experts* o *mixture-of-depths*: un router decide qué elementos reciben cómputo caro; la pérdida de balanceo impide que el router se degenere. De hecho la ratio loss se inspira en la de balanceo de carga de MoE.

**Segunda mitad de la lección — «tokenizer transfer».** Aunque el futuro fuera sin tokenizer, hoy hay millones de parámetros ya entrenados *atados* a un vocabulario. Cambiarlo (idioma, dominio, eficiencia) exige **inicializar los embeddings del vocabulario nuevo**. Es el primo pragmático del tema: menos glamuroso, mucho más usado.
""")
nb.gemini("imagen", "M07-IMG-01", "H-Net: U-Net jerárquica con chunking dinámico",
          "Arquitectura de H-Net de dos etapas: encoder → chunking → (encoder → chunking → main) → dechunk → decoder, con las conexiones residuales.",
          """Diagrama técnico limpio de arquitectura, fondo blanco, estilo figura de paper (sans-serif legible, flechas claras, sin ilustraciones decorativas ni texto inventado). Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Formato 16:9.
Título: "H-Net: una U-Net con chunking dinámico (2 etapas)".
Composición en forma de "U" con las entradas a la izquierda y las salidas a la derecha.
Bajada (izquierda, de arriba abajo), cada bloque con su etiqueta: "Bytes de entrada (L₀ posiciones)" → bloque azul "Encoder E⁰" → bloque naranja pequeño "Chunking 0 (routing + downsampler)" → "Vectores de etapa 1 (L₁ < L₀)" → bloque azul "Encoder E¹" → bloque naranja pequeño "Chunking 1" → "Vectores de etapa 2 (L₂ < L₁)".
Fondo de la U (abajo): bloque verde grande "Main network M (Transformer)" con la nota "procesa pocos vectores → casi todos los parámetros".
Subida (derecha, de abajo arriba): bloque naranja pequeño "Dechunking 1 (smoothing + upsampler)" → bloque azul "Decoder D¹" → bloque naranja pequeño "Dechunking 0" → bloque azul "Decoder D⁰" → "Predicción del siguiente byte".
Dos flechas horizontales discontinuas grises etiquetadas "conexión residual (Linear)" que van del Encoder E⁰ al Decoder D⁰ y del Encoder E¹ al Decoder D¹.
Una anotación lateral: "E y D: Mamba-2 en el paper · M: Transformer". Otra: "las fronteras (chunks) se aprenden de extremo a extremo".
Evita: ilustraciones decorativas, texto ilegible, más etapas de las indicadas, logotipos, flechas ambiguas, números no indicados.""",
          "Diagrama en U de H-Net con dos etapas de chunking, red principal en el fondo y conexiones residuales",
          """bytes -> [E0] --chunk0--> [E1] --chunk1--> [ M (Transformer) ] --dechunk1--> [D1] --dechunk0--> [D0] -> siguiente byte
            \\___________residual (Linear)____________________________________________/ (E0 -> D0)
                         \\_______residual (Linear)____________/ (E1 -> D1)""")
nb.md(obs("""
Las etapas **externas** (E, D) trabajan sobre secuencias largas, así que deben ser baratas (Mamba-2 en el paper); la **red principal** M trabaja sobre pocos vectores y concentra los parámetros. Las conexiones residuales devuelven al decoder el detalle fino que se perdió al comprimir. Una H-Net de una etapa es la misma figura con un solo U.
"""))

nb.code(S.PIP)
nb.code(C.SETUP_COMMON + S.SETUP_EXTRA + S.SETUP7)
nb.md("### 3.1 Corpus Políglota (utilidades del módulo 00)\n\nImplementación **canónica** de `carga_corpus()` (autor A1): Wikipedia ES/EN (HF) → API de Wikipedia → texto **sintético**; código: CodeSearchNet → funciones **reales** de la stdlib. Si ves «SINTÉTICO», interpreta las tendencias, no las cifras absolutas.")
for c in C.corpus_cells():
    nb.code(c)
nb.code(S.DATA)

nb.md(r"""
## 4. Teoría: el *dynamic chunking* de H-Net

Una etapa de H-Net aplica $\hat x = \mathcal{E}(x)$, $(x', p) = \text{Chunk}(\hat x)$, $\hat z' = \mathcal{M}(x')$, $z = \text{Dechunk}(\hat z', p) + \text{Linear}(\hat x)$ y decodifica con $\mathcal{D}$. Los símbolos: $x\in\mathbb{R}^{L\times D}$ la entrada de la etapa, $\hat x$ la salida del encoder, $p_t\in[0,1]$ la «confianza de frontera» en $t$.

**(1) Routing.** Medir *cambio de contexto* entre vecinos con similitud coseno de proyecciones aprendidas:

$$q_t = W_q\hat x_t,\quad k_t = W_k\hat x_t,\quad p_t = \tfrac12\!\left(1 - \frac{q_t^\top k_{t-1}}{\lVert q_t\rVert\,\lVert k_{t-1}\rVert}\right),\quad b_t = \mathbb{1}[p_t \ge 0.5],\quad p_1 = 1.$$

Si dos posiciones consecutivas son parecidas ($\cos\approx 1$) $p_t\approx 0$ (misma unidad); si difieren ($\cos\approx -1$) $p_t\approx 1$ (frontera). $b_t$ marca los bordes.

**(2) Downsampler.** Se **seleccionan** los vectores con $b_t=1$ (el paper compara con *mean/max pooling* y atención cruzada y se queda con la selección por simplicidad y rendimiento). La red principal $\mathcal{M}$ ve solo esos vectores.

**(3) Smoothing (dechunk).** La decisión $b_t$ es discreta y bloquea el gradiente. El suavizado hace la reconstrucción **diferenciable** con una media móvil exponencial sobre los *chunks*:

$$\bar z_j = P_j\,\hat z_j + (1-P_j)\,\bar z_{j-1},$$

con $P_j$ la $p$ del vector-frontera del chunk $j$. Con $P_j\approx 1$ el chunk se queda tal cual; con $P_j\approx 0.5$ se mezcla con el anterior (corrige fronteras dudosas).

**(4) Upsampler con STE.** Cada $\bar z_j$ se repite hasta la siguiente frontera ($\tilde z_t=\bar z_{\sum_{k\le t}b_k}$) y se multiplica por la confianza:

$$c_t = p_t^{\,b_t}(1-p_t)^{1-b_t},\qquad \text{STE}(c_t)=c_t+\operatorname{sg}(1-c_t),\qquad \text{Upsample}_t = \text{STE}(c_t)\,\tilde z_t,$$

donde $\operatorname{sg}$ es *stop-gradient*: en forward vale 1 (no altera la señal) y en backward deja pasar el gradiente de $c_t$. Premia fronteras confiadas y acertadas, y castiga las dudosas.

**(5) Ratio loss.** Sin regularizar, el router colapsaría a «todo es frontera» o «nada lo es». Con $F=\frac1L\sum b_t$ (fracción real de bordes) y $G=\frac1L\sum p_t$ (probabilidad media):

$$\mathcal{L}_{\text{ratio}} = \frac{N}{N-1}\Big((N-1)\,F\,G + (1-F)(1-G)\Big),\qquad \mathcal{L}=\mathcal{L}_{AR}+\alpha\sum_s \mathcal{L}^{s}_{\text{ratio}},\ \ \alpha=0.03,$$

con $N$ el factor de compresión objetivo. Aunque $F$ no es diferenciable, el gradiente fluye por $G$; el mínimo $\mathcal{L}_{\text{ratio}}=1$ se alcanza en $F=G=1/N$. (Idea tomada de la pérdida de balanceo de carga de los MoE.)

**Ejemplo a mano.** *Routing:* si $\cos(q_t,k_{t-1})=0.8$, $p_t=\tfrac12(1-0.8)=0.10$ → $b_t=0$ (sigue la unidad); si $\cos=-0.2$, $p_t=0.60$ → $b_t=1$ (frontera). *Ratio loss* con $N=4$ (objetivo: 1 frontera cada 4 bytes): en el óptimo $F=G=0.25$, $\mathcal{L}_{\text{ratio}}=\tfrac43(3\cdot0.0625+0.75\cdot0.75)=\tfrac43\cdot0.75=\mathbf{1}$; si el router colapsa a «todo es frontera» ($F=G=1$), $\tfrac43\cdot3=\mathbf{4}$; a «nada es frontera» ($F=G=0$), $\tfrac43\cdot1=\mathbf{1.33}$. Ambos colapsos se penalizan, como la pérdida de balanceo de un MoE penaliza mandar todo a un experto.

**Mejoras de entrenamiento** (§2.3 del paper): normalización al final de cada red (*norm balance*), proyección lineal solo en el camino residual, y **tasas de aprendizaje mayores en las etapas externas** (que ven secuencias más largas y deciden las fronteras de las internas).

**Inferencia.** H-Net decide *por byte* si lo pasa a la red principal; el decoder corre en cada byte y la red principal solo al cerrar chunks — parecido a la decodificación especulativa (un modelo pequeño cada paso, uno grande cada pocos).
""")
nb.gemini("imagen", "M07-IMG-02", "Routing, smoothing y upsampling en H-Net",
          "Mecánica de una etapa de chunking: similitud coseno entre vecinos → p_t → bordes → selección → suavizado EMA → repetición hasta el siguiente borde.",
          """Diagrama técnico limpio, fondo blanco, estilo figura de paper (sans-serif legible, flechas claras, sin texto inventado). Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Formato 16:9.
Título: "Una etapa de dynamic chunking, paso a paso".
Cuatro paneles en fila de izquierda a derecha, numerados 1 a 4, todos sobre la secuencia de bytes "n e w _ p r o d u c t !" (12 casillas; "_" es un espacio).
Panel 1 "Routing": debajo de cada par de casillas vecinas, una barra azul cuya altura es p_t = ½(1 − cos(q_t, k_{t−1})). Barras altas (≥ 0.5, resaltadas en naranja) bajo "n", "p" y bajo "d" (esta última algo más baja, ≈ 0.55). Línea horizontal discontinua roja en 0.5 etiquetada "umbral 0.5". La primera barra vale 1.0 (etiqueta "p₁ = 1").
Panel 2 "Downsampler": solo las casillas con barra naranja (n, p, d) se copian a una fila nueva más corta, etiquetada "vectores seleccionados x′ (L′ < L)".
Panel 3 "Smoothing": tres círculos de salida de la red principal con la fórmula "z̄ⱼ = Pⱼ·ẑⱼ + (1 − Pⱼ)·z̄ⱼ₋₁"; el tercer círculo, con P = 0.55, aparece mezclado (degradado entre verde y gris) y se anota "frontera dudosa → se mezcla con el chunk anterior".
Panel 4 "Upsampler": cada círculo se repite hasta el siguiente borde sobre las 12 casillas (3 bloques de colores: azul, naranja, verde de anchos 4, 5 y 3), con la leyenda "× STE(cₜ)" y "forward vale 1; el gradiente pasa por cₜ".
Evita: ilustraciones decorativas, texto ilegible, números no indicados, flechas ambiguas, sombras 3D.""",
          "Cuatro paneles que muestran routing por similitud coseno, selección de bordes, suavizado EMA y repetición con STE",
          """1 Routing    : n e w _ p r o d u c t !   p_t: [1.0 .1 .1 .2 .9 .1 .1 .55 .1 .1 .1 .1]  borde si p>=0.5
2 Downsample : se conservan los vectores en n, p, d   -> L' = 3
3 Smoothing  : z̄_j = P_j ẑ_j + (1-P_j) z̄_{j-1}      (d con P=.55 se mezcla con el chunk anterior)
4 Upsample   : [n e w _][p r o d u][c t !] x STE(c_t)   (forward: x1; backward: gradiente de c_t)""")
nb.md(obs("""
El suavizado es lo que permite aprender fronteras «a ciegas»: una frontera dudosa (P≈0.5) no tira la información del chunk, la **mezcla** con el anterior; y, si acierta, el factor $c_t$ la recompensa. Sin esto, el gradiente no llegaría a $W_q,W_k$.
"""))

nb.md(r"""
### 4.1 BLT frente a H-Net (qué cambia respecto al módulo 06)

| | **BLT (módulo 06)** | **H-Net (este módulo)** |
|---|---|---|
| ¿Quién decide las fronteras? | Modelo de entropía **aparte**, umbral fijo | Router **dentro** del modelo, entrenado extremo a extremo |
| ¿Diferenciable? | No (preprocesado) | Sí (smoothing + STE + ratio loss) |
| Control del coste | Umbral $\theta$ (también en inferencia) | Compresión objetivo $N$ (ratio loss) |
| Representación del chunk | Atención cruzada sobre los bytes del parche | **Selección** del vector-frontera (+ residual al decoder) |
| Jerarquía | 1 nivel de parches | **Recursiva**: la red principal puede ser otra H-Net |
| Backbone | Transformers | Mamba-2 en E/D, Transformer en M |
| Escala reportada | hasta 8B / 4T bytes | FLOPs de GPT-3 Large y XL (760M / 1.3B), 100B tokens de FineWeb-Edu |
""")

nb.md("## 5. MiniHNet desde cero\n\n**Qué es y qué no es.** Una etapa de H-Net con E y D como transformers causales pequeños (el paper usa Mamba-2) y los mismos mecanismos de chunking: routing por coseno, selección, EMA, upsampler con STE, residual proyectado inicializado a 0 y ratio loss. No incluye jerarquía de dos etapas, *norm balance* completo ni *LR modulation*. Comprobamos la **causalidad** igual que en el módulo 06.")
nb.code(S.HNET_UTIL)
nb.code(S.HNET_MODEL)
nb.md(r"""
### 5.1 Entrenamiento comparado: chunking aprendido vs espacios vs *pool* fijo

Tres variantes **idénticas salvo la función de chunking** (como en la Tabla 1 del paper): `dc` (aprendido, con ratio loss con $N=4$), `space` (inicios de palabra, heurística de SpaceByte) y `pool` (cada 4 bytes). Mismo presupuesto de pasos y datos. Una sola semilla: **mira tendencias, no diferencias de milésimas**.
""")
nb.code(S.HNET_TRAIN)
nb.code(S.HNET_PLOTS)
nb.md(obs("""
* **Centro:** $F$ (fracción real de bordes) se acerca al objetivo $1/N$ gracias a la ratio loss: el router **no colapsa** ni a «todo» ni a «nada». $G$ (probabilidad media, por la que fluye el gradiente) tarda más y suele quedar por encima: con un entrenamiento tan corto el router aún es poco «confiado» (muchas $p_t$ cerca de 0.5).
* **Izquierda:** en el paper el orden es *pool fijo < espacios < chunking aprendido*. A esta escala (2 min de CPU, una semilla) las diferencias pueden ser pequeñas o invertirse: lo que valida el mecanismo es que **aprende** y que el coste es el de ~1/4 de los pasos de la red principal.
* **Derecha:** las longitudes de chunk aprendidas son **variables** (como las de BPE o entropía) mientras `pool` tiene una sola longitud.
"""))
nb.code(S.HNET_BOUNDARIES)
nb.md(obs("""
Si el entrenamiento ha avanzado lo suficiente, las barras naranjas (bordes) empiezan a **coincidir con las líneas verdes (inicios de palabra)** sin que se haya dado ninguna supervisión de espacios. Con 400 pasos el efecto es parcial: compara la **precisión** y el **recall** impresos con los del azar (misma densidad de bordes). Los autores del paper reportan fronteras mucho más claras (palabras, morfemas) tras entrenar con ~100B de tokens.
"""))
nb.gemini("video", "M07-VID-01", "Cómo aprende H-Net dónde cortar",
          "Evolución (ilustrativa) de la probabilidad de frontera p_t a lo largo del entrenamiento: de ruido a picos en inicios de palabra, con la ratio loss estabilizando la densidad de bordes.",
          """Video explicativo técnico de 28 segundos, 16:9, 1080p, ritmo calmado, sin voz en off. Estilo: diagrama limpio sobre fondo blanco, tipografía sans-serif legible, paleta azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Sin ilustraciones decorativas ni datos reales (todo es ilustrativo y debe decirlo una nota fija abajo: "Ilustración conceptual").
Escena fija: la frase "el servidor procesa las peticiones" en una fila de casillas (una por carácter, espacios como ␣) abajo; encima, una fila de barras azules que representan p_t (probabilidad de frontera) y una línea roja discontinua en 0.5. Un contador arriba a la derecha dice "paso de entrenamiento".
Guion por escenas:
0–5 s: título "H-Net aprende sus propias fronteras". Aparece la frase y las barras con alturas casi aleatorias (entre 0.3 y 0.7); contador "paso 0". Etiqueta: "al inicio, el router no sabe nada".
5–14 s: el contador avanza a "paso 100" y "paso 250"; las barras se van diferenciando: las que están sobre la primera letra de cada palabra (e, s, p, l, p) suben por encima de 0.5 y se vuelven naranjas; las demás bajan. Aparecen líneas verticales verdes tenues en los inicios de palabra reales para comparar.
14–22 s: contador "paso 400". Aparece una barra lateral pequeña con dos marcadores: "F (bordes reales)" y "G (prob. media)" convergiendo hacia una línea horizontal etiquetada "objetivo 1/N". Texto: "la ratio loss mantiene la densidad de bordes".
22–28 s: texto final: "Las fronteras emergen sin supervisión; el router decide qué vectores pasan a la red principal". Se desvanece.
Texto en pantalla en español, con términos técnicos en inglés (router, ratio loss).
Evita: voz en off, texto ilegible, datos numéricos distintos de los indicados, cambios bruscos, logotipos.""",
          "Animación de barras de probabilidad de frontera que se concentran en los inicios de palabra a lo largo del entrenamiento",
          """paso 0  : barras ~0.5 al azar sobre "el servidor procesa las peticiones"
paso 250: barras altas (naranja) sobre e, s, p, l, p; bajas en el resto
paso 400: F y G convergen a 1/N  ->  bordes ~ inicios de palabra""", duration="28 s")
nb.md(obs("""
Observa dos cosas: (1) las fronteras **emergen** del objetivo de predecir el siguiente byte (no hay etiqueta de «inicio de palabra»); (2) la ratio loss actúa como **termostato** de la densidad de bordes: sin él, el router podría dar bordes en todos los bytes y anular el ahorro.
"""))

nb.md(r"""
## 6. ¿Está muerta la tokenización?

El argumento «los tokenizers desaparecerán» es atractivo; el argumento «es una moda» también. Pongamos la evidencia lado a lado (todas las cifras son **reportadas por los autores**, a oct-2026).

### Evidencia a favor de los modelos sin tokenizer

| Evidencia | Fuente | Matiz |
|---|---|---|
| Un modelo de bytes con parches por entropía iguala a Llama 3 a 8B (1T tokens / ~4.5T bytes, mismos FLOPs) y gana en ortografía (CUTE 54.1 vs 27.5) | BLT, arXiv:2412.09871 | Un solo conjunto de datos y receta; BPE gana a bajo cómputo |
| H-Net de 1 etapa sobre bytes supera a un Transformer BPE (GPT-2) con FLOPs y datos igualados; 2 etapas ≈ un Transformer del doble de tamaño; ventaja mayor en chino, código y ADN | H-Net, arXiv:2507.07955 | Escala ≤ 1.3B; baseline = tokenizer GPT-2 (50K), más débil que los de Llama 3 o similares |
| Convertir (*byte-ify*) un LLM subword en byte-level con poco entrenamiento adicional es viable; Bolmo 1B/7B abiertos | Bolmo, arXiv:2512.15586 | Parte de un backbone entrenado **con** tokenizer: hereda su conocimiento |
| Jerarquías bytes→palabras aprendidas son competitivas con BPE | AU-Net, arXiv:2506.14761 (NeurIPS 2025) | «Jerarquías poco profundas»; las profundas son «prometedoras» |

### Evidencia en contra (o que matiza)

| Evidencia | Fuente | Matiz |
|---|---|---|
| Hasta ~2x más lento en entrenamiento y difícil de *batchear* en inferencia (cómputo dinámico) | H-Net, §Discusión | «No fundamental», dicen; pero hoy es un coste real |
| FLOPs ≠ latencia: las implementaciones actuales pueden no igualar el reloj de los transformers tokenizados | BLT, §9 | |
| Los tokenizers siguen mejorando: **SuperBPE** (tokens que cruzan espacios) da +4.0 % medio en 30 tareas con 8B y hasta 33 % menos tokens | Liu et al., arXiv:2503.13423 | Mejor BPE, no «sin BPE» |
| La compresión no es lo único: PathPiece (mínimo nº de tokens) **no** da mejor rendimiento | Schmidt et al., EMNLP 2024 | Matiza el mito «menos tokens = mejor» |
| Ecosistema: caché de prefijos por token, *constrained decoding*, facturación, evaluación y herramientas de interpretabilidad asumen tokens | — | Coste de migración, no científico |
| No hay (que yo sepa) evidencia pública de un LLM de frontera de producción sin tokenizer | — | «Sin evidencia pública» ≠ «no existe» |

**Veredicto de este curso (opinión razonada, no hecho):** la tokenización **no está muerta, se está internalizando**. Hay buenas razones científicas para que la segmentación se aprenda (equidad multilingüe, robustez, dominios sin vocabulario natural como ADN), pero a oct-2026 los resultados llegan a ≈ 1-8B y la ingeniería sigue por detrás. Un cambio de opinión razonable se produciría con (1) replicación independiente a > 30B, (2) parity de latencia real en *serving*, o (3) un modelo de frontera que lo declare.
""")
nb.code(S.REPORTED_PLOT)
nb.md(obs("""
* Las barras son **cifras de las tablas del paper** (no ejecutadas aquí). H-Net 2 etapas mejora 0.013-0.015 bpb sobre el Transformer BPE en ambas escalas; con tareas zero-shot, +2.2 y +2.6 puntos de media según el paper.
* Mira los **ejes truncados**: las diferencias de bpb entre H-Net 1 etapa, espacios y Transformer son del orden de 0.001-0.005. Los autores mismos hablan de «ruido» en algunas comparaciones de evaluación.
* La conclusión robusta del paper es *cualitativa*: la jerarquía y el chunking aprendido **se pagan solos** a FLOPs iguales y su ventaja crece con los datos (cruce con el Transformer a los 30B bytes para 2 etapas en XL).
"""))

nb.md(r"""
## 7. Tokenizer transfer: cambiar el vocabulario de un modelo ya entrenado

**Problema (Minixhofer et al., 2024).** Un LM está *atado* a su tokenizer: su matriz de embeddings $E_a\in\mathbb{R}^{|V_a|\times d}$ (y, si no hay *weight tying*, la de salida) solo tiene sentido para $V_a$. Queremos un tokenizer nuevo $(V_b, T_b)$ —otro idioma, dominio o tamaño— **conservando el cuerpo del modelo**. Todo se reduce a: *¿cómo inicializar $E_b$?* Después, un ajuste corto.

### 7.1 Taxonomía de métodos (lo que necesitan y cómo inicializan)

| Método | Idea | Necesita | Verificado en |
|---|---|---|---|
| Aleatoria | $e_b(t)\sim\mathcal{N}(0,\sigma^2)$ | nada | línea base |
| Media / Hewitt | todos los nuevos = media de $E_a$ (o muestra de $\mathcal{N}(\mu,\Sigma)$ de $E_a$) | nada | `transformers` (`mean_resizing=True`) |
| **FVT** | $e_b(t)=\frac1{\lvert T_a(t)\rvert}\sum_{s\in T_a(t)} e_a(s)$: media de la descomposición con el tokenizer antiguo | tokenizer antiguo | Gee et al. 2022; descrito en ZeTT §2 |
| **WECHSEL** | embeddings estáticos (fastText) de ambos idiomas alineados con diccionario bilingüe + Procrustes; $e_b(t)=\sum_{s\in \text{kNN}}\mathrm{softmax}(\cos/\tau)\,e_a(s)$, $\tau=0.1$, $k=10$ | fastText ambos idiomas + diccionario | arXiv:2112.06598 |
| **FOCUS** | copia los tokens **compartidos**; cada nuevo = combinación **sparsemax** de los compartidos, con pesos por similitud en un espacio auxiliar (fastText sobre el idioma destino) | datos no etiquetados del destino | arXiv:2305.14481 |
| **Trans-Tokenization** | alinea tokens de origen y destino con un **corpus paralelo** (alineador estadístico) y promedia ponderando por recuento de alineación | corpus paralelo (o diccionario) | arXiv:2408.04303 (COLM 2024) |
| **ZeTT** | una **hiperred** (otro LM pequeño) que, dado un tokenizer, *predice* sus embeddings componiendo los de la descomposición; se entrena sobre muchos tokenizers y generaliza a uno nuevo **sin datos del destino** | entrenar la hiperred | arXiv:2405.07883 (NeurIPS 2024) |

**Ejemplo a mano (FVT).** El tokenizer nuevo tiene `▁servidor`; el antiguo lo parte en `▁serv` + `idor` con embeddings (de juguete, $d=2$) $(1,0)$ y $(0,2)$. FVT lo inicializa con la media: $e_b(\texttt{▁servidor})=(0.5,\,1)$. Un token que el antiguo ya tenía igual se copia tal cual. Es la misma intuición que el *cold start* de un ítem nuevo en recsys: lo inicializas con la media de los ítems con los que se relaciona, no al azar.

**Resultados reportados por ZeTT** (no los hemos reproducido): con XLM-R, tokenizers específicos por idioma acortan las secuencias ≈ 14 % en media, aceleran la inferencia > 16 % y conservan XNLI a ≈ 1 % en promedio; con Mistral-7B, un tokenizer de código con ~10 % menos tokens preserva la corrección funcional a ≈ 3 %; y el hueco restante se cierra con **< 1B tokens** de entrenamiento continuado, frente a cientos de miles de millones en trabajos previos. En decodificadores el problema es más difícil: FOCUS «es aproximadamente aleatorio en el peor caso» (−23.2 % en BoolQ) y da 0 % pass@1 en HumanEval Python.

**Otros caminos:** OFA (parametrización factorizada de embeddings, arXiv:2311.08849), AdaptiVocab (adaptar el vocabulario a un dominio, arXiv:2503.19693), *retrofitting* con tokenización dinámica (arXiv:2411.18553) y destilación entre tokenizers (ALM, arXiv:2503.20083).

### 7.2 La métrica correcta
Tras el cambio, la pérdida *por token* **no es comparable** (los tokens nuevos cubren más bytes). Evaluamos **bits por byte** sobre el mismo texto con cada tokenizer.
""")
nb.md("### 7.3 Montaje del experimento\n\nModelo base: **GPT-2 en miniatura** (`GPT2LMHeadModel`, 3 capas, ancho 128) preentrenado solo con **inglés + código** y un BPE de 512 tokens (tokenizer A). Destino: **español** con un BPE propio de 768 tokens (tokenizer B). En el modo completo se usa el **GPT-2 small real** (124M) y su tokenizer de 50 257 tokens si tienes acceso al hub.")
nb.code(S.BPE_FN)
nb.code(S.TT_DATA)
nb.code(S.TT_FERT)
nb.md(obs("""
El tokenizer B (entrenado en español) produce tokens más largos sobre el español: **menos pasos del transformer por byte**. Ese es el beneficio de adaptar el vocabulario; el coste es el de inicializar y ajustar el nuevo $E_b$. (En el módulo 04 viste lo mismo con vocabularios reales: la «tarifa por idioma».)
"""))
nb.code(S.TT_MODEL)
nb.md(r"""
### 7.4 Inicializaciones desde cero

Seis maneras de rellenar $E_b$. Todas **copian** los tokens cuya cadena aparece en ambos vocabularios (los «compartidos») y difieren en cómo tratan al resto.

* **Hewitt:** muestrear de $\mathcal{N}(\mu,\Sigma)$ ajustada a $E_a$ para que el softmax no reparta masa extra a los nuevos. (La implementación por defecto de Hugging Face usa $\epsilon\Sigma$ con $\epsilon=10^{-9}$: en la práctica, la media.)
* **FOCUS-lite:** `sparsemax` sobre similitudes en un espacio auxiliar. Aquí el espacio auxiliar es **PPMI + SVD** sobre el texto tokenizado (un «fastText de juguete»); el paper usa fastText.
* **WECHSEL-lite:** espacios auxiliares de A y B **alineados con Procrustes** usando los tokens compartidos como «diccionario», y media ponderada por softmax (τ=0.1, k=10).
""")
nb.code(S.TT_INITS)
nb.code(S.TT_AUX)
nb.code(S.TT_RUN)
nb.code(S.TT_CONTROLS)
nb.code(S.TT_PLOTS)
nb.md(obs("""
* **Izquierda (cero-shot):** justo tras cambiar de tokenizer, las inicializaciones **informadas** (FVT, FOCUS-lite; en nuestra corrida también WECHSEL-lite) quedan algo por debajo de la media/Hewitt, y todas por debajo de la línea roja (el modelo **sin** adaptar). Las diferencias son pequeñas: en ZeTT los heurísticos pueden estar «a nivel del azar» en decodificadores — aquí el modelo es diminuto, no extrapoles.
* **Centro y derecha:** tras 100 pasos de **solo embeddings** las curvas se separan (FVT/WECHSEL ganan algo a media/Hewitt); al descongelar todo el modelo las diferencias se **comprimen** casi a cero — la inicialización ahorra *pasos*, no cambia el destino (de ahí que ZeTT mida cuántos tokens hacen falta para cerrar el hueco).
* **Controles:** *seguir con A* (línea roja discontinua) acaba por encima de todos los cambios de tokenizer a igualdad de pasos —con más tokens por byte— y *desde cero con B* (negra) tarda más: el preentrenamiento sí valía. Tu criterio de ingeniero: ¿el bpb final y el ahorro de tokens compensan el coste de ajustar?
* ⚠️ Una semilla, ~300 pasos, modelo de ~0.5M parámetros: **cualitativo**.
"""))
nb.code(S.TT_PCA)
nb.md(obs("""
Cada panel muestra los embeddings **viejos** (gris) y los **nuevos** (naranja). `media`: los nuevos colapsan en **un punto** (varianza ≈ 0) → todos reciben el mismo logit, el modelo no puede distinguirlos hasta que el ajuste los separe. `aleatoria`: nubes sin relación con el espacio del modelo. `FVT`/`FOCUS`/`WECHSEL`: los nuevos caen **dentro de la nube de los viejos** con varianza propia — «posiciones razonables» desde el paso 0. La razón entre varianzas (título) es un buen diagnóstico rápido.
"""))
nb.gemini("imagen", "M07-IMG-03", "Estrategias para inicializar el vocabulario nuevo",
          "Compara cuatro maneras de dar un embedding a un token nuevo (media, FVT, FOCUS/sparsemax, WECHSEL/Procrustes) con un ejemplo concreto.",
          """Diagrama técnico limpio, fondo blanco, estilo infografía de paper (sans-serif legible, flechas claras, sin ilustraciones decorativas ni texto inventado). Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Formato 16:9.
Título: "¿Qué embedding le damos al token nuevo «ción»?".
Contexto a la izquierda, en un recuadro gris: "Vocabulario antiguo A (inglés): …, 'tion', 'ation', 'c', 'i', 'ón' …" y "Vocabulario nuevo B (español): …, 'ción', 'dad', …". Debajo, un cuadro: "Tokens compartidos (se copian): 'a', 'e', 'ion'".
A la derecha, cuatro mini-diagramas en cuadrícula 2×2, cada uno con un título, una flecha desde "ción (nuevo)" hacia su vector de salida (círculo naranja) y los pesos escritos como números sobre las flechas de entrada:
1) "Media (Hewitt/HF)": flechas desde TODOS los embeddings del vocabulario antiguo (nube gris) hacia un solo círculo naranja en el centro de la nube. Nota: "todos los nuevos quedan en el mismo punto".
2) "FVT": el texto "ción" se descompone con el tokenizer antiguo en "c" + "i" + "ón"; flechas de pesos iguales (1/3, 1/3, 1/3) hacia el círculo naranja. Nota: "media de la descomposición".
3) "FOCUS": flechas desde los tokens compartidos con pesos distintos (0.7, 0.3, 0.0) producidos por "sparsemax"; nota: "pesos exactamente 0 fuera del soporte; similitud en un espacio auxiliar entrenado con texto en español".
4) "WECHSEL": dos nubes (inglés y español) alineadas con una flecha curva etiquetada "rotación de Procrustes"; el círculo naranja se calcula con los k vecinos más cercanos y "softmax(cos/τ)".
Pie en gris: "Después de cualquier init: ajuste corto (primero solo embeddings, luego todo el modelo)".
Evita: ilustraciones decorativas, texto ilegible, números distintos de los indicados, flechas ambiguas, logotipos.""",
          "Cuadrícula de cuatro estrategias de inicialización de un token nuevo con pesos de ejemplo",
          """Nuevo: 'ción' (B). Compartidos: a, e, ion.
1 Media    : todos los nuevos -> media(E_A)                       (colapsan en un punto)
2 FVT      : T_A('ción') = [c, i, ón] -> (e_c + e_i + e_ón)/3
3 FOCUS    : sparsemax(cos(aux)) sobre compartidos -> 0.7 e_ion + 0.3 e_a + 0 e_e
4 WECHSEL  : Procrustes(aux_B -> aux_A) y softmax(cos/0.1) sobre los 10 vecinos más cercanos""")
nb.md(obs("""
Lee el diagrama de menos a más información: **media** (ninguna) → **FVT** (el propio tokenizer antiguo) → **FOCUS** (datos del destino) → **WECHSEL** (datos de ambos + diccionario). ZeTT sustituye esa heurística por una función **aprendida** de la descomposición.
"""))
nb.code(S.TT_MEAN_RESIZE)

nb.md(r"""
### 7.5 Checklist para un cambio de tokenizer en un proyecto real

1. **Tokens especiales:** `pad`, `eos`, `bos`, plantillas de chat; si no se mapean, el modelo "no sabe parar".
2. **Cabeza de salida:** con *weight tying* se comparte; si no, hay que inicializar **también** la matriz de salida (ZeTT predice las dos).
3. **Reetiquetar los datos** con el tokenizer nuevo y recalcular longitudes: el contexto efectivo en bytes cambia.
4. **Medir en bpb** (o en una métrica de tarea), con el mismo texto, antes y después; cuidado con filtrar el *test* en los datos de ajuste.
5. **Regresión en lo que no se adaptó:** el inglés y el código no deben degradarse (mide el bpb sobre ellos).
6. **Presupuesto de ajuste:** primero solo embeddings (barato y estable), luego descongelar. Registra cuántos tokens hacen falta para cerrar el hueco.
""")

nb.md(r"""
## 8. Mapa de madurez (a oct-2026)

Con H-Net y tokenizer transfer ya vistos, esta tabla resume qué es sólido, emergente o experimental.

| Técnica | Madurez | Quién la usa / respaldo público | Fuente |
|---|---|---|---|
| BLT (parches por entropía, módulo 06) | 🟡/🔴 | Meta FAIR; hasta 8B, pesos 1B/7B | arXiv:2412.09871 (ACL 2025) |
| **H-Net / dynamic chunking** | 🔴 | CMU / Cartesia (Albert Gu); código `goombalab/hnet` y pesos en el hub de Cartesia; ICLR 2026; hasta ~1.3B de FLOPs equivalentes | arXiv:2507.07955 |
| Seguimiento de H-Net (SOMBRERO, H-Net++, chunking adaptativo…) | 🔴 | Grupos académicos / industriales; resultados a ~1B o menos | p. ej. arXiv:2601.22805 |
| AU-Net (U-Net autoregresiva bytes→palabras) | 🔴 | Meta FAIR / NeurIPS 2025; «en pie de igualdad» con BPE en jerarquías poco profundas | arXiv:2506.14761 |
| *Byte-ification* (Bolmo) | 🔴/🟡 | Ai2: Bolmo 1B/7B abiertos, convertidos desde Olmo 2/3 | arXiv:2512.15586 |
| Init por media / muestreo de la distribución (Hewitt) | 🟢 | Es el **valor por defecto** de `resize_token_embeddings(mean_resizing=True)` en `transformers` | Documentación de `transformers`; blog de J. Hewitt (2021) |
| FVT (media de la descomposición) | 🟢/🟡 | Compresión de modelos (Gee et al., 2022); baseline estándar en la literatura de transfer | arXiv:2402.09977 |
| WECHSEL | 🟡 | Transferencia de GPT-2/RoBERTa a otros idiomas; código abierto | arXiv:2112.06598 |
| FOCUS | 🟡 | Especialización monolingüe de XLM-R; checkpoints y código publicados | arXiv:2305.14481 |
| Trans-Tokenization | 🟡 | Familia «Tweeties» (COLM 2024), adaptada desde Mistral-7B | arXiv:2408.04303 |
| ZeTT (hiperred) | 🟡/🔴 | NeurIPS 2024; hiperredes publicadas (XLM-R, Mistral-7B, TinyLlama) | arXiv:2405.07883 |
| Destilación entre tokenizers (ALM) | 🔴 | Investigación (2025) | arXiv:2503.20083 |

> **Regla del curso:** «🔴» = hay un paper con resultados a pequeña/mediana escala y código, pero **no hay evidencia pública de adopción en producción a gran escala**.
""")

nb.md(r"""
## 9. 🏭 En producción

* **Cambiar de tokenizer es una práctica real, pero pequeña:** se hace para **adaptar un modelo abierto a un idioma o dominio** (p. ej. las familias monolingües derivadas con WECHSEL/FOCUS/Trans-Tokenization y la serie «Tweeties» de Mistral-7B) y para **comprimir** modelos (FVT). Los laboratorios grandes, cuando necesitan un idioma nuevo, a menudo extienden el vocabulario y continúan el preentrenamiento; las cifras concretas rara vez se publican.
* **Hugging Face:** `resize_token_embeddings` inicializa por defecto con la media/covarianza de los embeddings viejos (`mean_resizing=True`). Para añadir tokens de dominio es lo razonable; para **sustituir** el vocabulario entero, no.
* **H-Net en la práctica:** los autores publicaron código (`goombalab/hnet`) y pesos; la propia discusión del paper avisa de entrenamiento hasta ≈2x más lento, de memoria dinámica y de la dificultad de *batchear* la inferencia con coste desigual por posición. Trátalo como **investigación reproducible**, no como dependencia de producción.
* **Políglota:** (1) para el **embedder** (módulos 09-12) la decisión práctica es *qué tokenizer heredas* de un encoder existente y cuándo extenderlo con tokens de dominio (conecta con el 09); (2) para un futuro **generativo**, seguir BLT/H-Net/Bolmo como opción de largo plazo, no de la hoja de ruta actual.
""")

nb.md(r"""
## 10. 🧠 Secretos de la élite

1. **La ratio loss es el 'termostato'.** Sin ella el router colapsa (todo o nada); con ella, $F\to G\to 1/N$. Observa $F$ y $G$ por separado en tus logs: si $F\ne G$ de forma persistente, el router no es confiado (el paper nota que $\mathcal{L}_{\text{ratio}}$ puede bajar de 1 cuando $F\neq G$).
2. **Smoothing + STE no son decoración:** el paper los ablaciona y muestra que sin ellos el router aprende mal; la decisión dura sola no da gradiente útil. Si implementas tu propio chunker, prueba primero con y sin.
3. **Las etapas externas piden más learning rate.** Ven secuencias más largas y deciden las fronteras de las internas; H-Net escala el LR por etapa (§2.3). Un H-Net con LR uniforme es uno mal sintonizado.
4. **El baseline importa.** H-Net compara contra un Transformer con el **tokenizer GPT-2**; BLT contra **Llama 3 (128K)**. Un tokenizer mejor (o SuperBPE) sube la vara. Al leer «supera a BPE», pregunta *cuál* BPE.
5. **La inicialización por media 'mata' la diversidad.** Todos los tokens nuevos quedan en un punto y el softmax los trata igual; es seguro (no altera la distribución anterior) pero lento. Mide la varianza de los nuevos respecto a los viejos (como en el panel PCA).
6. **Mide en bpb *y* en robustez:** tras un cambio de tokenizer, una init puede ganar en bpb medio y perder en tokens raros o en código. Evalúa en cada dominio.
7. **FOCUS, WECHSEL y compañía fueron diseñados para codificadores/modelos pequeños;** ZeTT documenta que en decodificadores grandes los heurísticos pueden caer «a nivel del azar» en cero-shot y que hacen falta ~cientos de millones de tokens de entrenamiento para cerrar el hueco.
8. **Pregunta incómoda:** ¿tu mejora viene del *tokenizer nuevo* o de *haber entrenado más en el idioma*? El control «seguir con A» responde.
""")

nb.md(r"""
## 11. ⚠️ Errores comunes

* **Comparar pérdida por token** entre tokenizers (mide bpb).
* **Olvidar la matriz de salida** cuando no hay *weight tying*, o los tokens especiales.
* **Inicializar con la media y concluir que 'el método funciona'** sin entrenar: todos los nuevos son iguales hasta que el gradiente los separa.
* **Entrenar el tokenizer nuevo con datos de evaluación** (fuga) o evaluar solo en el idioma destino sin vigilar la regresión en el origen.
* **Creer que H-Net 'demuestra' que BPE ya no sirve:** los resultados son ≤1.3B FLOPs-equivalentes, un conjunto de datos, un baseline BPE concreto.
* **Aplicar el chunker durante el entrenamiento mirando bytes futuros:** rompe la causalidad. Valida con una prueba de perturbación (como la de MiniHNet).
""")

nb.md(r"""
## 12. Autoevaluación

""" + "\n\n".join([
    details("1 · (Cálculo) Con $N=4$, calcula $\\mathcal{L}_{\\text{ratio}}$ para $F=G=0.25$ y para $F=G=0.5$.",
            "$\\frac{4}{3}\\big(3\\cdot 0.25\\cdot0.25 + 0.75\\cdot0.75\\big)=\\frac43(0.1875+0.5625)=1.0$ (el mínimo). Con $F=G=0.5$: $\\frac43(3\\cdot0.25+0.25)=\\frac43\\cdot 1.0=1.333$. La pérdida penaliza comprimir menos de lo pedido."),
    details("2 · (Cálculo) Un chunk tiene $\\hat z_1=(2,0)$ con $P_1=1$ y el siguiente $\\hat z_2=(0,4)$ con $P_2=0.5$. ¿Cuánto vale $\\bar z_2$?",
            "$\\bar z_1 = P_1\\hat z_1 + 0 = (2,0)$. $\\bar z_2 = 0.5\\cdot(0,4)+0.5\\cdot(2,0) = (1, 2)$: una frontera dudosa se mezcla con el chunk anterior."),
    details("3 · (Diagnóstico) Tras cambiar de tokenizer, la pérdida por token pasa de 3.1 a 3.4 nats y el equipo dice que el modelo empeoró. Los bytes por token pasaron de 2.5 a 4.0. ¿Qué concluyes?",
            "bpb antes = 3.1/(ln2·2.5) = 1.79; después = 3.4/(ln2·4.0) = 1.23. El modelo **mejoró** (~31 % menos bits por byte); la pérdida por token no es comparable."),
    details("4 · (Diagnóstico) Inicializas con la media y, tras 10 pasos, el modelo reparte la misma probabilidad a todos los tokens nuevos. ¿Es un bug? ¿Cómo lo acelerarías?",
            "No es un bug: todos los nuevos tienen el mismo embedding y, con weight tying, el mismo logit. Se separan solo cuando el gradiente los diferencia. Acelerar: inicializaciones informadas (FVT/FOCUS/WECHSEL) o añadir ruido de la covarianza de los viejos (Hewitt)."),
    details("5 · (Transferencia) Políglota quiere añadir 2 000 tokens de dominio (nombres de librerías) al vocabulario de un encoder para embeddings. ¿Qué método elegirías y por qué?",
            "FVT (media de la descomposición con el tokenizer original) es barato y no necesita datos adicionales: cada librería nueva se inicializa como la media de sus subtokens; luego ajuste corto con el contrastivo del módulo 11. Si tienes corpus del dominio, FOCUS-lite aporta pesos informados. Siempre midiendo retrieval (nDCG@10) y no solo pérdida."),
    details("6 · (Transferencia) Escribe en dos líneas qué resultado haría que dejes de decir «la tokenización no está muerta».",
            "Por ejemplo: una replicación independiente de H-Net/BLT a ≥ 30B parámetros que iguale a un Transformer con un tokenizer fuerte (o que lo supere) **y** con latencia de serving igual o menor. Fíjate que la condición incluye *ingeniería*, no solo bpb."),
    details("7 · (Recuerdo) ¿Qué problema resuelven el smoothing y la ratio loss, respectivamente?",
            "El smoothing hace diferenciable la reconstrucción a partir de decisiones discretas (el gradiente llega al router). La ratio loss evita el colapso a «todo/nada» y fija la compresión objetivo $N$."),
]))

nb.md(r"""
## 13. Referencias

Verificadas (título/autores/fecha) en arXiv o en el repositorio oficial en la fecha de redacción.

* Hwang, Wang, Gu. **Dynamic Chunking for End-to-End Hierarchical Sequence Modeling** (H-Net). arXiv:2507.07955 (jul. 2025); ICLR 2026. Código: <https://github.com/goombalab/hnet>.
* Pagnoni et al. **Byte Latent Transformer: Patches Scale Better Than Tokens.** arXiv:2412.09871; ACL 2025.
* Videau et al. **From Bytes to Ideas: Language Modeling with Autoregressive U-Nets.** arXiv:2506.14761; NeurIPS 2025.
* Minixhofer et al. **Bolmo: Byteifying the Next Generation of Language Models.** arXiv:2512.15586.
* Neitemeier et al. **SOMBRERO: Measuring and Steering Boundary Placement in End-to-End Hierarchical Sequence Models.** arXiv:2601.22805.
* Minixhofer, Ponti, Vulić. **Zero-Shot Tokenizer Transfer.** NeurIPS 2024, arXiv:2405.07883. Código: <https://github.com/bminixhofer/zett>.
* Dobler, de Melo. **FOCUS: Effective Embedding Initialization for Monolingual Specialization of Multilingual Models.** arXiv:2305.14481.
* Minixhofer, Paischer, Rekabsaz. **WECHSEL: Effective initialization of subword embeddings for cross-lingual transfer of monolingual language models.** arXiv:2112.06598.
* Remy, Delobelle, Avetisyan, Khabibullina, de Lhoneux, Demeester. **Trans-Tokenization and Cross-lingual Vocabulary Transfers: Language Adaptation of LLMs for Low-Resource NLP.** COLM 2024, arXiv:2408.04303.
* Gee, Zugarini, Rigutini et al. **Fast Vocabulary Transfer for Language Model Compression.** arXiv:2402.09977.
* Liu, Lin, Wang et al. **OFA: A Framework of Initializing Unseen Subword Embeddings for Efficient Large-scale Multilingual Continued Pretraining.** arXiv:2311.08849.
* Minixhofer, Vulić, Ponti. **Universal Cross-Tokenizer Distillation via Approximate Likelihood Matching.** arXiv:2503.20083.
* Liu, Hayase, Hofmann et al. **SuperBPE: Space Travel for Language Models.** arXiv:2503.13423.
* Schmidt et al. **Tokenization Is More Than Compression.** EMNLP 2024, arXiv:2402.18376.
* Martins, Astudillo. **From Softmax to Sparsemax: A Sparse Model of Attention and Multi-Label Classification.** ICML 2016.
* Hewitt. **Initializing New Word Embeddings for Pretrained Language Models** (blog, 2021): <https://nlp.stanford.edu/~johnhew/vocab-expansion.html> (enlace citado en la documentación de `transformers.resize_token_embeddings`).

## 14. Siguiente paso

El **proyecto** (`07_proyecto_hnet_tokenizer_transfer.ipynb`) te pide cambiar el tokenizer de un modelo pequeño, implementar inicializaciones y medir bpb antes/después de un ajuste corto. El **módulo 08** sale del texto: tokens de **imagen y audio**, con otra forma de «tokenizar» (cuantización vectorial).
""")
nb.save(os.path.join(MOD_DIR, f"{SLUG}.ipynb"))

P.build(LESSON_REL, PROJ_REL, MOD_DIR, SLUG)

README = r"""# Módulo 07 · Tokenizer-free II (H-Net) y *tokenizer transfer*

**Nivel:** 🔴 Experto · **Duración:** ≈ 6 h (lección ≈ 3.5 h + proyecto ≈ 2.5 h) · **Cómputo:** CPU en `FAST_DEV_RUN=True` (≈ 12-15 min); **L4 recomendada** (≈ 6-10 unidades) en modo completo con GPT-2 small real

| Archivo | Contenido |
|---|---|
| `07_hnet_tokenizer_transfer.ipynb` | Lección: dynamic chunking de H-Net (routing, smoothing, STE, ratio loss), **MiniHNet** desde cero, debate «¿está muerta la tokenización?», taxonomía de tokenizer transfer (FVT, WECHSEL, FOCUS, Trans-Tokenization, ZeTT), seis inicializaciones implementadas, medición en bpb antes/después de un ajuste corto |
| `07_proyecto_hnet_tokenizer_transfer.ipynb` | Proyecto: **cambiar el tokenizer de un modelo pequeño** (plantilla con TODOs, pistas, rúbrica calibrada, solución tras SPOILER) |
| `assets/` | Imágenes/video de Gemini: `M07-IMG-01.png`, `M07-IMG-02.png`, `M07-IMG-03.png`, `M07-VID-01.mp4` |

## Objetivos
1. Explicar y implementar el chunking dinámico de H-Net (routing, selección, EMA, STE, ratio loss) y verificar su causalidad.
2. Evaluar con evidencia «¿está muerta la tokenización?».
3. Clasificar los métodos de tokenizer transfer y cuándo usar cada uno.
4. Inicializar embeddings de vocabulario nuevo (media, Hewitt, FVT, FOCUS-lite, WECHSEL-lite) y medir bpb cero-shot y tras un ajuste corto.

## Datasets y modelos
Corpus Políglota (`carga_corpus()` del módulo 00). Modelo base: GPT-2 en miniatura entrenado en la propia lección (modo rápido) o **GPT-2 small** (`gpt2`) en modo completo. **Estado de pruebas:** en el entorno de autoría Hugging Face estaba bloqueado: todo se probó con corpus **sintético** (+ código real de la stdlib) y modelos diminutos locales; la ruta con `gpt2` real y Wikipedia real **no pudo ejecutarse**.

## Lecturas
Hwang, Wang y Gu 2025 (H-Net, arXiv:2507.07955) · Minixhofer et al. 2024 (ZeTT, arXiv:2405.07883) · Dobler y de Melo 2023 (FOCUS) · Minixhofer et al. 2022 (WECHSEL) · Remy et al. 2024 (Trans-Tokenization).

## Enlaces
Anterior: [06 · Tokenizer-free I](../06_tokenizer_free_bytes_blt/) · Siguiente: [08 · Tokens multimodales y de audio](../08_tokens_multimodales_audio/)
"""
with open(os.path.join(MOD_DIR, "README.md"), "w", encoding="utf-8") as f:
    f.write(README)
print("README escrito")
