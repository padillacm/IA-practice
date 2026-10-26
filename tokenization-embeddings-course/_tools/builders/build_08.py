"""Construye los notebooks del módulo 08 (lección + proyecto) y su README.

    python tokenization-embeddings-course/_tools/builders/build_08.py     # desde la raíz del repo
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from nbbuild import Notebook  # noqa: E402
import a3_common as C  # noqa: E402
import _a3_src08 as S  # noqa: E402
import _a3_proj08 as P  # noqa: E402

COURSE = "tokenization-embeddings-course"
SLUG = "08_tokens_multimodales_audio"
MOD_DIR = os.path.join(HERE, "..", "..", SLUG)
LESSON_REL = f"{COURSE}/{SLUG}/{SLUG}.ipynb"
PROJ_REL = f"{COURSE}/{SLUG}/08_proyecto_tokens_multimodales_audio.ipynb"
os.makedirs(os.path.join(MOD_DIR, "assets"), exist_ok=True)
open(os.path.join(MOD_DIR, "assets", ".gitkeep"), "a").close()
obs, details = C.observe, C.details

nb = Notebook("Módulo 08 · Tokens multimodales y de audio", colab_path=LESSON_REL, gpu=True)

nb.md(nb.badge() + r"""

# Módulo 08 · Tokens multimodales y de audio: parches ViT, VQ-VAE, FSQ, RVQ y códecs neuronales
**Tokenización y Embeddings: de BPE a los modelos modernos**

| | |
|---|---|
| **Nivel** | 🟠 Avanzado |
| **Duración estimada** | ≈ 6 h (lección ≈ 3.5 h + proyecto ≈ 2.5 h) |
| **GPU recomendada** | `FAST_DEV_RUN=True`: **CPU** (≈ 6-10 min en total; MNIST y voz real FSDD, modelos de < 1M parámetros). Modo completo: **T4** (≈ 3-5 unidades de Colab, estimación) |
| **Prerrequisitos** | 02 (BPE como compresión), 04 (coste de contexto por idioma), 06 (bits por byte, parches); álgebra lineal y PyTorch (convoluciones) |
| **Madurez del tema** | 🟢 parches ViT y códecs de audio tipo EnCodec · 🟡 VQ/FSQ como interfaz con LLM, Mimi, tokenizers de video · 🔴 tokenizers 1D y modelos «continuos» unificados |

> **Contexto Políglota Labs.** El producto va a indexar pronto **PDFs con diagramas** y **grabaciones de soporte** (módulo 16 construye el retrieval multimodal). Antes de que alguien proponga «meterlo todo en el
> LLM», tu CTO quiere saber **qué es un token de imagen o de audio, cuántos hacen falta y cuánto cuesta en contexto**. En esta lección los construyes: un VQ-VAE/FSQ/RVQ desde cero sobre imágenes pequeñas, un
> códec de audio de juguete, y un LM sobre tokens de imagen (un «mini-Chameleon»). Todo diminuto y **didáctico**: no compite con EnCodec ni con VQGAN.
""")

nb.md(r"""
## 1. Objetivos de aprendizaje

1. **Distinguir** tokens **continuos** (parches ViT) de **discretos** (códigos de un codebook) y saber cuándo se usa cada uno.
2. **Implementar** `patchify` y demostrar que la *patch embedding* de ViT es una convolución con `stride = patch`.
3. **Derivar e implementar** VQ-VAE (distancia mínima, pérdida de codebook y *commitment*, *straight-through*), **medir** PSNR, bits por imagen y **perplejidad de uso** del codebook, y reproducir el **colapso del codebook**.
4. **Implementar** FSQ (cuantización escalar finita) y RVQ (cuantización residual con *quantizer dropout*) y compararlos con VQ.
5. **Entrenar** un LM sobre tokens de imagen y generar dígitos (la idea de Chameleon/VQGAN-transformer a escala de juguete).
6. **Construir** un códec de audio neuronal de juguete (encoder conv → RVQ → decoder conv) y **medir** tasa (kbps), SNR y distancia log-espectral frente a μ-law.
7. **Calcular** tasas de tokens por segundo/imagen/video y su **coste en contexto** (EnCodec, Mimi, Chameleon, Cosmos…).
8. **Etiquetar** la madurez de cada técnica (🟢/🟡/🔴) y **conectar** con embeddings multimodales (módulo 16) sin adelantarlo.
""")

nb.md("## 2. 🔁 Conexión con módulos anteriores\n\n" +
      details("1 · (Módulo 02) BPE comprime texto fusionando pares frecuentes. ¿En qué se parece y en qué se diferencia VQ de BPE?",
              "Ambos aprenden un **diccionario** de K entradas para representar los datos con menos símbolos. BPE es *discreto y exacto* (sin pérdida; el diccionario son cadenas de bytes); VQ es **con pérdida** (cada vector se aproxima por su centroide más cercano) y se entrena por gradiente junto con un decodificador. Ambos se evalúan con una relación tasa-distorsión: en BPE, bytes por token; en VQ, bits por token frente a error de reconstrucción.") + "\n\n" +
      details("2 · (Módulo 04/06) ¿Qué mide «bits por byte» y cómo se traduce a imágenes y audio?",
              "Mide la información que cuesta cada byte original. Para imágenes se usa **bits por píxel (bpp)** y para audio **kbps**; en los tres casos es una **tasa** que se compara a igual distorsión.") + "\n\n" +
      details("3 · (Módulo 04) ¿Por qué importa el número de tokens que genera cada modalidad para un LLM?",
              "El contexto de un transformer es finito y el coste de atención crece con $N^2$: una imagen de 1 024 tokens o un minuto de audio con 36 000 tokens consumen mucho más contexto que un párrafo de texto. La «tarifa por idioma» del módulo 04 es el mismo fenómeno con otra modalidad."))

nb.md(r"""
## 3. Intuición primero: tokenizar = cuantizar

Un LLM consume **secuencias**. Imágenes, audio y video son señales continuas y enormes (una foto de 512x512 tiene 262 144 píxeles; un minuto de audio a 24 kHz tiene 1.44 millones de muestras). *Tokenizar* una modalidad significa **comprimirla en una secuencia corta de unidades** que el modelo sepa manejar. Hay dos grandes familias:

| Familia | Qué es un «token» | Ejemplos | Ventaja | Coste |
|---|---|---|---|---|
| **Continua** | un **vector** (p. ej. un parche 16x16 proyectado a 768 números) | ViT, CLIP/SigLIP, encoders de VLM | sin pérdida de cuantización; se conecta con embeddings (módulo 16) | no se puede predecir con cross-entropy sobre un vocabulario |
| **Discreta** | un **id** de un codebook de tamaño $K$ (o de varios, en RVQ) | VQ-VAE, VQGAN, FSQ, EnCodec, Mimi | encaja con «predecir el siguiente token» y con un vocabulario unificado texto+imagen+audio | **pérdida** por cuantización y problemas de entrenamiento (colapso del codebook) |

* **Analogía de compresión de datos.** Es un **códec con pérdida**: el encoder hace de *transformada*, el cuantizador fija la **tasa** y el decoder reconstruye. Todo se evalúa con una curva **tasa-distorsión**.
* **Analogía de recsys/IR.** La cuantización vectorial residual es la hermana del **Product Quantization** de FAISS (módulo 14) y de los **semantic IDs** de recomendación generativa (Rajput et al., 2023, arXiv:2305.05065), donde un RQ-VAE convierte cada ítem en una pequeña secuencia de códigos. Aquí la usamos para reconstruir señales; allí, para **indexar**.
""")
nb.gemini("imagen", "M08-IMG-01", "Mapa de tokens por modalidad",
          "Muestra cómo cada modalidad se convierte en secuencia (parches continuos vs códigos discretos) y las tasas de tokens típicas.",
          """Diagrama técnico limpio, fondo blanco, estilo infografía de paper (sans-serif legible, flechas claras, sin ilustraciones decorativas ni texto inventado). Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Formato 16:9.
Título: "De señales continuas a secuencias de tokens".
Cuatro filas, de arriba a abajo; en cada fila, a la izquierda el icono esquemático de la señal (un rectángulo con trazos simples, sin dibujos realistas), en el centro un bloque con el método y a la derecha una secuencia de cajitas (los tokens) con la tasa.
Fila 1 "Texto": rectángulo con líneas de texto → bloque azul "Tokenizer BPE (módulos 02-04)" → cajitas con ids "412 · 87 · 3051 · 9" → "~1.3 tokens por palabra (orden de magnitud)".
Fila 2 "Imagen (continuo)": cuadrícula 14x14 sobre un cuadrado → bloque azul "Parches ViT 16x16 + proyección lineal" → cajitas con vectores (cada una con la etiqueta "vector de 768 números") → "196 tokens para una imagen de 224x224".
Fila 3 "Imagen (discreto)": cuadrado → bloque naranja "Encoder → cuantizador VQ/FSQ (codebook)" → cajitas con ids "5021 · 17 · 8190 · 733" → "1 024 tokens (codebook de 8192) para 512x512 en Chameleon".
Fila 4 "Audio (discreto)": onda sinusoidal → bloque verde "Códec neuronal: encoder → RVQ (8 niveles) → decoder" → una matriz de 8 filas x 4 columnas de cajitas de ids (columnas = frames) → "EnCodec 24 kHz a 6 kbps: 75 frames/s x 8 niveles = 600 tokens/s; Mimi: 12.5 frames/s x 8 = 100 tokens/s".
Una barra vertical a la derecha etiquetada "coste de contexto" con una flecha creciente de arriba a abajo.
Evita: ilustraciones decorativas, texto ilegible, números distintos de los indicados, flechas ambiguas, logotipos, sombras 3D.""",
          "Cuatro filas: texto con BPE, imagen con parches ViT, imagen con VQ discreto y audio con códec RVQ, con sus tasas de tokens",
          """Texto   -> BPE                         -> [412][87][3051]...        ~1.3 tokens/palabra
Imagen  -> parches ViT 16x16 + Linear  -> [v768][v768]...           196 tokens (224x224)         (continuo)
Imagen  -> encoder + VQ/FSQ            -> [5021][17][8190]...       1024 tokens (512x512, K=8192) (discreto)
Audio   -> encoder + RVQ x8 + decoder  -> 8 filas x frames de ids   75 Hz x 8 = 600 tok/s (EnCodec 6 kbps); Mimi: 12.5 Hz x 8 = 100 tok/s""")
nb.md(obs("""
Dos preguntas ordenan el módulo: **(1) ¿discreto o continuo?** (¿necesito *predecir* el token o solo *leerlo*?) y **(2) ¿cuántos tokens por segundo/imagen?** (el coste de contexto). La tabla de tasas que calculamos abajo te deja ver que un minuto de audio puede pesar **más que una novela corta** en tokens.
"""))

nb.code(S.PIP)
nb.code(C.SETUP_COMMON + S.SETUP8)
nb.md("Datos de imagen: **MNIST real** vía `torchvision` (si no hay red, figuras sintéticas 28x28) y dos **fotos reales** empaquetadas con scikit-learn.")
nb.code(S.DATA_IMG)

nb.md("## 4. Presupuesto de tokens: ¿cuánto contexto cuesta cada modalidad?\n\nAntes de implementar nada, una **calculadora**. Cada fila usa una cifra de un paper o la fórmula de la arquitectura (marcamos con `~` lo aproximado).")
nb.code(S.TOKEN_BUDGET)
nb.md(obs("""
* **El audio es caro:** a 6 kbps EnCodec produce 600 tokens/s; **1 hora = 2.16 M de tokens**, y una ventana de 128K tokens cabe solo ~3.6 minutos. Por eso Mimi baja a **12.5 Hz** (100 tokens/s aplanado) y Moshi modela los niveles con un transformer «de profundidad» pequeño en lugar de aplanarlos.
* Una imagen discreta de Chameleon (1 024 tokens) cuesta **~5 veces** un parche ViT-B/16 de 224² (196). Y el **video** (decenas de miles de tokens para 5 s) obliga a compresión espacio-temporal agresiva.
* TiTok (32 tokens por imagen) muestra que 1 024 no es ley natural: depende del tokenizer.
"""))

nb.md(r"""
## 5. Tokens continuos: parches ViT

Un **Vision Transformer** parte la imagen en una rejilla de parches $p\times p$, aplana cada uno ($p^2 C$ números) y lo proyecta linealmente a $D$ dimensiones: $N=(H/p)(W/p)$ tokens. Es *exactamente* una convolución con `kernel=p, stride=p`. Es también la «lectura» de una imagen que usan CLIP/SigLIP (módulo 16).
""")
nb.code(S.VIT)
nb.md(obs("""
* `conv == lineal sobre parches: True`: la *patch embedding* es una **convolución con stride = tamaño de parche**; no hay nada mágico.
* **Derecha:** el número de tokens crece **cuadráticamente con la resolución** y la atención cuesta ~$N^2$: duplicar el lado cuadruplica los tokens y multiplica por 16 el coste de atención. Por eso los VLMs recortan, remuestrean o agrupan parches.
"""))

nb.md(r"""
## 6. Tokens discretos: VQ-VAE

**Idea.** Un autoencoder cuyo cuello de botella es un **codebook** de $K$ vectores $\{e_j\}_{j=1}^{K}\subset\mathbb{R}^d$. El encoder produce $z_e(x)$ (una rejilla de vectores), cada vector se **sustituye por su vecino más cercano** y el decoder reconstruye desde esos vectores:

$$k = \arg\min_{j}\ \lVert z_e - e_j\rVert_2,\qquad z_q = e_k,\qquad \hat x = \text{Dec}(z_q).$$

**Pérdida** (van den Oord et al., 2017), con $\operatorname{sg}$ el *stop-gradient*:

$$\mathcal{L} = \underbrace{\lVert x-\hat x\rVert_2^2}_{\text{reconstrucción}} + \underbrace{\lVert \operatorname{sg}[z_e]-e\rVert_2^2}_{\text{codebook}} + \beta\underbrace{\lVert z_e-\operatorname{sg}[e]\rVert_2^2}_{\text{commitment}},\qquad \beta=0.25$$

El **argmin** no es diferenciable: se usa el **straight-through estimator**, $z_q = z_e + \operatorname{sg}(e - z_e)$, que en *forward* da $e$ y en *backward* copia el gradiente de $z_q$ a $z_e$. La pérdida de codebook mueve los $e_j$ hacia los vectores que se les asignan; el *commitment* evita que el encoder «salte» entre códigos.

**Ejemplo a mano.** Codebook de $K=3$ vectores en 2D: $e_1=(0,0)$, $e_2=(1,1)$, $e_3=(2,0)$, y un vector del encoder $z_e=(0.9,\,0.6)$. Distancias al cuadrado: $\lVert z_e-e_1\rVert^2=0.81+0.36=1.17$, $\lVert z_e-e_2\rVert^2=0.01+0.16=\mathbf{0.17}$, $\lVert z_e-e_3\rVert^2=1.21+0.36=1.57$ → **token 2**, $z_q=(1,1)$. Con $\beta=0.25$ el *commitment* vale $0.25\cdot0.17=0.043$, y ese token cuesta $\log_2 3=1.58$ bits. Es exactamente una asignación de **k-means** (los $e_j$ son centroides); la misma idea reaparece en la cuantización de productos (PQ) de los índices ANN del módulo 14.

**Tasa.** Con una rejilla de $N$ tokens, la tasa es $R = N\log_2 K$ bits por imagen (o $R/(H W)$ bits por píxel, **bpp**).

**Colapso del codebook.** Si solo unos pocos códigos ganan la asignación, el resto **nunca recibe gradiente** (están «muertos»): la tasa efectiva es mucho menor que $\log_2 K$. Se mide con la **perplejidad de uso** $\exp\!\big(-\sum_k p_k\ln p_k\big)$ ($p_k$ = frecuencia del código $k$): vale $K$ si el uso es uniforme y ~1 si colapsa. Soluciones habituales: inicializar el codebook **con vectores del encoder** (como hacemos), **reiniciar códigos muertos**, actualizar por **EMA**, o evitar el codebook (**FSQ**).
""")
nb.gemini("imagen", "M08-IMG-02", "VQ-VAE: encoder, codebook y decoder con straight-through",
          "Flujo completo de un VQ-VAE: imagen → rejilla de vectores continuos → vecino más cercano en el codebook → rejilla de ids → decoder, con el camino de gradiente straight-through.",
          """Diagrama técnico limpio, fondo blanco, estilo figura de paper (sans-serif legible, flechas claras, sin ilustraciones decorativas ni texto inventado). Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Formato 16:9.
Título: "VQ-VAE: de píxeles a ids y de vuelta".
De izquierda a derecha, cinco bloques:
1) Cuadrado gris etiquetado "Imagen x (28x28)".
2) Bloque azul "Encoder (convoluciones, stride 4)" que produce una rejilla de 7x7 cuadraditos azules etiquetada "z_e: 49 vectores de dimensión d".
3) En el centro, un recuadro naranja grande "Codebook: K vectores e₁ … e_K" mostrado como una columna de K filas (con "e₁", "e₂", "…", "e_K"). Desde un cuadradito de la rejilla azul sale una flecha etiquetada "vecino más cercano: k = argmin ‖z_e − e_j‖" hasta la fila "e₅" resaltada, y de ahí a un cuadradito naranja de una segunda rejilla 7x7 etiquetada "z_q = e_k". Debajo de la segunda rejilla, una tercera rejilla 7x7 de números (por ejemplo 5, 17, 17, 3, …) etiquetada "ids: 49 tokens (log₂K bits cada uno)".
4) Bloque verde "Decoder (deconvoluciones)" que produce un cuadrado gris etiquetado "Reconstrucción x̂".
5) Debajo de todo, una flecha curva discontinua roja que va desde z_q de vuelta hasta z_e con la etiqueta "straight-through: el gradiente se copia de z_q a z_e (el argmin no es diferenciable)".
Pie con las tres pérdidas en tres cajitas: "‖x − x̂‖²" (reconstrucción), "‖sg[z_e] − e‖²" (codebook), "β‖z_e − sg[e]‖²" (commitment).
Evita: ilustraciones decorativas, texto ilegible, números no indicados, flechas ambiguas, sombras 3D, logotipos.""",
          "Diagrama de VQ-VAE con encoder, búsqueda del vecino más cercano en el codebook, decoder y el camino de gradiente straight-through",
          """x (28x28) -> [Encoder] -> z_e (7x7 x d) --argmin--> ids (7x7, K valores) -> e[ids] = z_q -> [Decoder] -> x̂
                                   \\__________ straight-through: grad(z_q) -> z_e __________/
pérdidas: ||x-x̂||² + ||sg[z_e]-e||² + β||z_e - sg[e]||²""")
nb.md(obs("""
Hay **tres** caminos: (1) el de *reconstrucción* (a través de $z_q$ con STE hasta el encoder), (2) el del **codebook** (mueve los $e_j$ hacia los $z_e$) y (3) el del **commitment** (mantiene a $z_e$ cerca del código elegido). Sin el STE el encoder no recibiría gradiente de la reconstrucción.
"""))
nb.md("### 6.1 Cuantizadores desde cero\n\nLos tres cuantizadores (`VQ`, `FSQ`, `RVQ`) comparten interfaz.")
nb.code(S.QUANTIZERS)
nb.code(S.AE_MODEL)
nb.md("### 6.2 Entrenar un VQ-VAE ($K=64$, 49 tokens por imagen)")
nb.code(S.VQ_BASE)
nb.md(obs("""
* **Fila central:** la imagen se reconstruye desde solo **49 ids** (¡de ~6 300 bits en bruto a ~300!), con detalles borrosos: es una compresión **con pérdida** muy agresiva.
* **Fila inferior:** el mapa de tokens 7x7 tiene **estructura espacial**: trazos parecidos reutilizan los mismos ids. Eso es lo que un LM puede aprender a predecir después.
* **Perplejidad impresa:** si es muy inferior a $K$, el codebook no se usa por completo (siguiente celda).
"""))
nb.md("### 6.3 Barrido de $K$ y colapso del codebook\n\nEntrenamos varios $K$ y un caso **sin los trucos** de uso (sin init por datos ni reinicio de códigos muertos) para ver el colapso.")
nb.code(S.VQ_SWEEP)
nb.md(obs("""
* **Izquierda (tasa-distorsión):** más bits (más $K$) → más PSNR, con **rendimientos decrecientes**. El codo marca el compromiso razonable.
* **Centro:** perplejidad/$K$ **cae** al crecer $K$: con $K$ grande una parte del codebook se desperdicia aunque hayamos usado trucos. No pagas $\\log_2 K$ bits «útiles» por token.
* **Derecha:** sin trucos, **unos pocos códigos concentran todo el uso** (curva en escala log): el resto está muerto. Es el fallo más común al entrenar un VQ-VAE por primera vez.
"""))

nb.md(r"""
## 7. FSQ y RVQ: dos maneras de esquivar el codebook (o de apilarlo)

**FSQ — *Finite Scalar Quantization*** (Mentzer et al., 2023). Elimina el codebook: acota cada canal de $z$ con una $\tanh$ y lo **redondea a $L_i$ niveles** enteros (con STE para el redondeo):

$$\hat z_i = \operatorname{round}\big(\lfloor L_i/2\rfloor\tanh(z_i)\big),\qquad |\mathcal{C}| = \prod_{i=1}^{d}L_i\quad(\text{p. ej. } [8,6,5]\Rightarrow 240\text{ códigos}).$$

El «codebook» es **implícito** (una rejilla de enteros), no hay pérdidas auxiliares y el uso es casi uniforme. Los tokenizers discretos de Cosmos usan niveles $(8,8,8,5,5,5)$, es decir **64 000** códigos.

**RVQ — *Residual Vector Quantization*** (SoundStream/EnCodec). Apila $Q$ cuantizadores, cada uno sobre el **residuo** del anterior:

$$r_0 = z,\quad q_i = \text{VQ}_i(r_{i-1}),\quad r_i = r_{i-1}-q_i,\qquad \hat z=\sum_{i=1}^{Q}q_i,\qquad \text{tasa}=Q\log_2 K\ \text{bits por posición}.$$

Los primeros niveles capturan lo grueso; los siguientes **refinan**. Entrenando con ***quantizer dropout*** (usar un $Q$ aleatorio por lote, como en SoundStream) **un solo modelo sirve varias tasas**: recortas niveles en inferencia.
""")
nb.code(S.FSQ_RVQ)
nb.md(obs("""
* **VQ vs FSQ (izquierda y centro):** con un presupuesto parecido de códigos (~256 vs 240) FSQ alcanza una calidad comparable **sin codebook, sin pérdidas auxiliares y sin trucos** (init por datos, reinicios). En la corrida de referencia: VQ 22.3 dB con perplejidad 22/256 y FSQ 21.2 dB con 41/240 — FSQ usa **casi el doble** de su vocabulario, aunque ninguno lo llena (MNIST 7x7 no tiene variedad para cientos de códigos); el paper de FSQ reporta uso casi completo a escala. Dos detalles prácticos que nos costó descubrir: **normalizamos** la entrada de FSQ por su desviación típica (si no, todo redondea a 0) y usamos un **learning rate menor** (con 2e-3 el autoencoder colapsaba a una salida constante en esta semilla). FSQ no tiene codebook, pero sigue siendo sensible a la escala.
* **Derecha:** un único modelo **RVQ** con `n_q = 1…4` traza una **curva de tasas** (más niveles → más PSNR). El VQ simple necesita **un modelo por punto** de la curva.
* ⚠️ Una semilla, ~400 pasos, MNIST: las diferencias finas (±0.5 dB) **no son concluyentes**; busca las tendencias.
"""))

nb.md(r"""
## 8. Tokens de imagen dentro de un LLM (estilo Chameleon) y modelos «continuos»

**Chameleon** (Meta, 2024) entrena un transformer *early-fusion* sobre **secuencias mixtas** texto+imagen en un único vocabulario: un tokenizer de imagen convierte una imagen de 512x512 en **1 024 tokens** de un codebook de **8 192**, y el vocabulario total (BPE de texto + tokens de imagen) es de **65 536** entradas. **Emu3** (BAAI, 2024) lleva la idea a «solo predecir el siguiente token» para texto, imagen y video.

**¿Por qué discretizar?** Porque permite usar la **misma pérdida** (cross-entropy del siguiente token) y la misma arquitectura para todo, y mezclar modalidades en una secuencia. **¿Por qué no?** La cuantización **pierde información** y limita la calidad; Transfusion (Meta, hasta 7B) combina cross-entropy para texto con **difusión** sobre parches *continuos* y reporta que escala **mejor** que cuantizar las imágenes; MAR (Li et al. 2024) modela cada token continuo con una **pérdida de difusión** y «elimina la necesidad de tokenizers discretos».

Aquí construimos, a escala de juguete, la receta discreta: **un LM sobre los 49 tokens de cada imagen**, con un token de *clase* como «prompt». Es el mismo principio de VQGAN + transformer (Esser et al., 2020), sin GAN ni perceptual loss.
""")
nb.code(S.PRIOR)
nb.md(obs("""
Cada fila se genera con un **token de clase** como prefijo y 49 tokens muestreados autoregresivamente, que el decoder del VQ-VAE traduce a píxeles. Verás trazos plausibles pero **borrosos o con artefactos**: tiene dos fuentes de error (el LM sobre tokens y la capacidad del VQ-VAE), exactamente las que un VQGAN real mitiga con más escala, pérdidas perceptual/adversarial y codebooks mayores. La idea que importa: **una vez discretizada la imagen, generarla es «solo» un LM** sobre un vocabulario unificado.
"""))

nb.md(r"""
## 9. Audio: de la forma de onda a tokens con un códec neuronal

**Pipeline** (SoundStream, EnCodec, DAC, Mimi): `waveform → encoder convolucional (stride total S) → RVQ (Q niveles) → decoder → waveform`. A una frecuencia de muestreo $f_s$, el encoder entrega $f_s/S$ *frames* por segundo, y

$$\text{tasa} = \frac{f_s}{S}\cdot Q\cdot\log_2 K\ \ \text{bit/s},\qquad \text{tokens/s}= \frac{f_s}{S}\cdot Q .$$

| Códec | Frecuencia | Frames/s | Cuantización | Tasa |
|---|---|---|---|---|
| **SoundStream** (Google, 2021) | 24 kHz | 75 (strides 2,4,5,8) | RVQ con *quantizer dropout* | 3-18 kbps |
| **EnCodec** (Meta, 2022) | 24 kHz | 75 | RVQ hasta 32 codebooks de 1 024 entradas (10 bits) | 1.5, 3, 6, 12, 24 kbps |
| **DAC** (Descript, 2023) | 44.1 kHz | — | RVQGAN mejorado | 8 kbps (~90x de compresión) |
| **Mimi** (Kyutai, 2024) | 24 kHz | **12.5** | 8 cuantizadores de 2 048 entradas (11 bits); el primero **destila** información semántica (WavLM) | **1.1 kbps** |

* **Verificación aritmética:** EnCodec 24 kHz con 8 codebooks: $75\times 8\times 10 = 6\,000$ bit/s ✓. Mimi: $12.5\times 8\times 11 = 1\,100$ bit/s ✓.
* **Tokens acústicos vs semánticos.** Los niveles de un códec puro capturan *cómo suena* (timbre, ruido). Mimi y SpeechTokenizer añaden **destilación de un modelo de habla** (WavLM) en el primer nivel para que contenga *qué se dice*; así un LM puede predecir el contenido con los primeros tokens y los detalles acústicos con los siguientes.
* **Entrenamiento:** reconstrucción en forma de onda + **pérdida espectral multi-escala** + **discriminadores** (GAN) + pérdidas de commitment del RVQ. Nosotros usamos solo las dos primeras (no hay GAN), de ahí un audio con artefactos.
""")
nb.gemini("imagen", "M08-IMG-03", "Códec de audio neuronal con RVQ (EnCodec/SoundStream)",
          "Arquitectura de un códec de audio neuronal: encoder convolucional, RVQ de varios niveles y decoder; con la cuenta de tokens por segundo.",
          """Diagrama técnico limpio, fondo blanco, estilo figura de paper (sans-serif legible, flechas claras, sin ilustraciones decorativas ni texto inventado). Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Formato 16:9.
Título: "Códec neuronal de audio: waveform → tokens → waveform".
De izquierda a derecha:
1) Una onda sonora gris etiquetada "Audio 24 kHz (1.44 M muestras por minuto)".
2) Bloque azul "Encoder convolucional (strides 2·4·5·8 = 320)" con una flecha etiquetada "75 frames por segundo".
3) Un bloque naranja grande "RVQ: 8 cuantizadores en cascada". Dentro, 8 cajitas apiladas "VQ 1 (1 024 entradas)", "VQ 2", "…", "VQ 8", unidas por flechas verticales etiquetadas "residuo". A la derecha del bloque, una matriz de 8 filas x 5 columnas de cajitas pequeñas con ids (filas = niveles, columnas = frames), etiquetada "tokens: 75 x 8 = 600 por segundo".
4) Bloque verde "Decoder convolucional" que reconstruye una onda gris etiquetada "Audio reconstruido".
Debajo, una línea horizontal con tres marcas: "1 nivel → baja calidad", "4 niveles → media", "8 niveles → 6 kbps" (con la cuenta "75 × 8 × 10 bits = 6 000 bit/s") y la leyenda "quantizer dropout: un solo modelo, varias tasas".
Nota lateral en gris: "Mimi: 12.5 frames/s x 8 niveles de 2 048 entradas = 1.1 kbps".
Evita: ilustraciones decorativas, texto ilegible, números distintos de los indicados, flechas ambiguas, sombras 3D, logotipos.""",
          "Diagrama de códec neuronal: audio, encoder convolucional, cascada de 8 cuantizadores RVQ, matriz de tokens y decoder",
          """audio 24 kHz -> [Encoder strides 2*4*5*8=320] -> 75 frames/s -> [RVQ: VQ1 -> VQ2 -> ... -> VQ8 (residuos)] -> ids 8 x frames
ids -> [Decoder] -> audio reconstruido     |  75 x 8 x 10 bits = 6000 bit/s  |  quantizer dropout: 1..8 niveles""")
nb.md(obs("""
El orden de los niveles **importa**: el 1.º captura lo más energético (envolvente, tono) y los demás añaden detalle; por eso se pueden **truncar niveles** para bajar la tasa. La matriz de tokens (niveles x frames) es lo que luego modelan los LMs de audio (MusicGen, Moshi…), ya sea **aplanándola** (más tokens) o con un transformer extra para los niveles.
"""))

nb.md("### 9.1 Voz real a 8 kHz y un códec de juguete\n\nUsamos el **Free Spoken Digit Dataset** (FSDD: dígitos hablados en inglés por 6 hablantes, 8 kHz mono, CC BY-SA 4.0), que se descarga de su repositorio oficial en GitHub en segundos; concatenamos las grabaciones y cortamos clips de 1 s. Si no hay red, el respaldo es **voz sintética** (pulsos glotales + formantes de vocales + envolvente silábica) con aviso visible. Es un banco **didáctico** y pequeño: LibriSpeech tiene mucha más variedad.")
nb.code(S.AUDIO_DATA)
nb.code(S.AUDIO_MODEL)
nb.code(S.AUDIO_EVAL)
nb.md(obs("""
* **Espectrogramas:** con 1 nivel (1 kbps) se conserva el **contorno grueso** (tono/envolvente) y se pierde el detalle armónico; con 4 niveles (4 kbps) reaparece **parte** del detalle armónico. Eso es el «refinamiento residual» en acción.
* **SNR vs tasa:** cada nivel extra suma ~1 kbps y mejora el SNR, con rendimientos decrecientes (en la corrida de referencia con voz real FSDD: 1.5 → 2.9 dB de 1 a 4 niveles; el respaldo sintético, más regular, llega a ≈ 10 dB). **μ-law** (cuantización escalar por muestra) necesita **decenas de kbps** para lograr SNRs parecidos: un códec neuronal aprende una representación mucho más compacta *para este tipo de señal*.
* ⚠️ **Matiz honesto:** el SNR en forma de onda **no es la métrica perceptual** que usan los códecs reales (MUSHRA, ViSQOL, PESQ): un códec puede tener SNR bajo y sonar bien porque conserva el espectro y no la fase. Y nuestro banco es diminuto (unos minutos de dígitos hablados): **no extrapoles** el SNR a EnCodec/DAC.
"""))
nb.code(S.CODES_PLOT)
nb.md(obs("""
Cada columna es un **frame** (8 ms) y cada fila un **nivel**. Observa que el nivel 1 cambia más «lentamente» con la envolvente de las vocales, mientras los niveles posteriores parecen más ruidosos (detalle fino). La **perplejidad por nivel** te dice si el codebook de cada nivel está usado o colapsado.
"""))
nb.gemini("video", "M08-VID-01", "Cuantización vectorial residual: cada nivel refina el error",
          "Animación 2D de un vector que se aproxima por pasos: el nivel 1 elige el centroide más cercano, el nivel 2 cuantiza el residuo, etc., y el error baja.",
          """Video explicativo técnico de 24 segundos, 16:9, 1080p, ritmo calmado, sin voz en off y sin música. Estilo: diagrama limpio sobre fondo blanco, tipografía sans-serif legible, paleta azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Sin ilustraciones decorativas.
Escena fija: un plano cartesiano 2D con un punto objetivo azul etiquetado "z (vector a codificar)" en la posición aproximada (3.2, 2.1). Nota fija abajo: "Ilustración conceptual con K = 4 centroides por nivel".
Guion por escenas:
0–4 s: título "RVQ: cada nivel corrige lo que dejó el anterior". Aparece el punto z y 4 puntos grises etiquetados "codebook 1" en (0,0), (4,0), (0,4), (4,4).
4–10 s: una línea discontinua une z con el centroide más cercano (4,4); ese centroide se vuelve naranja, etiqueta "nivel 1: q₁". Se dibuja una flecha roja desde q₁ hasta z, etiquetada "residuo r₁ = z − q₁ (error aún grande)". Contador "error: alto".
10–17 s: el plano se re-centra en el residuo r₁ (se traslada para que q₁ quede en el origen); aparecen 4 centroides pequeños verdes etiquetados "codebook 2" alrededor del origen. Se elige el más cercano (verde brillante, etiqueta "nivel 2: q₂"); la flecha roja se acorta. Contador "error: medio".
17–22 s: se repite una vez más con "codebook 3" (centroides diminutos); la flecha roja casi desaparece. Contador "error: bajo". Aparece la fórmula "ẑ = q₁ + q₂ + q₃".
22–24 s: texto final "Cada nivel = log₂ K bits; más niveles = más fidelidad". Se desvanece.
Texto en pantalla en español.
Evita: voz en off, texto ilegible, números distintos de los indicados, cambios bruscos de cámara, logotipos.""",
          "Animación de cuantización vectorial residual con tres niveles que reducen el error de aproximación de un vector 2D",
          """nivel 1: z=(3.2,2.1) -> centroide (4,4)  residuo r1 grande
nivel 2: r1 recentrado -> centroide verde q2     residuo r2 medio
nivel 3: r2 -> q3                                residuo r3 pequeño   ẑ = q1+q2+q3""", duration="24 s")
nb.md(obs("""
El error baja **con cada nivel** y cada nivel cuesta lo mismo ($\\log_2 K$ bits): es una **codificación progresiva**. Truncar niveles = bajar la tasa sin reentrenar, siempre que se haya entrenado con *quantizer dropout*.
"""))

nb.md(r"""
### 9.2 EnCodec real con Hugging Face

`transformers` incluye `EncodecModel` con los pesos oficiales (`facebook/encodec_24khz`). Si no hay acceso al hub, la celda instancia el modelo con **pesos aleatorios** solo para mostrar las **formas** y la **tasa de tokens** (el audio decodificado sería ruido).
""")
nb.code(S.ENCODEC_TRY)
nb.md(obs("""
`audio_codes` tiene forma `[chunks, batch, n_q, frames]`: con `bandwidth=6.0` hay **8 niveles** a **75 frames/s** = **600 tokens/s**, que es la cifra de nuestra tabla de presupuesto. Cámbialo a `1.5` y verás 2 niveles (150 tokens/s).
"""))

nb.md(r"""
## 10. Tokenizers de video

El video añade el eje temporal: un **tokenizer 3D** comprime con factores $c_t\times c_s\times c_s$ (tiempo x alto x ancho), de modo que $N\approx \tfrac{T}{c_t}\cdot\tfrac{H}{c_s}\cdot\tfrac{W}{c_s}$. **Cosmos** (NVIDIA, 2025) publica tokenizers *continuos* y *discretos* (FSQ, 64 000 códigos) con compresiones espacio-temporales de **4x8x8, 8x8x8 y 8x16x16** (y 8x8 / 16x16 para imágenes); **MAGVIT-v2** (Google/CMU) usa *lookup-free quantization* para un vocabulario común de imagen y video. La compresión más agresiva ahorra contexto pero **degrada la calidad** (el paper de Cosmos muestra el compromiso PSNR-compresión).
""")
nb.code(S.VIDEO_CALC)
nb.md(obs("""
En escala log-log, las tres rectas son **paralelas** (el factor de compresión es constante) y separadas **órdenes de magnitud**: un clip de 30 s a 720p con 4x8x8 supera de lejos una ventana de 128K tokens, y solo las compresiones más agresivas caben. Es el análogo de la prima de tokens por idioma: **el tokenizer decide cuánto contexto consume una modalidad**.
"""))

nb.md(r"""
## 11. Puente con embeddings multimodales (módulo 16)

No lo desarrollamos aquí, solo lo ubicamos: los **parches ViT** (sección 5) son la entrada de CLIP/SigLIP, y un **embedding de imagen** para retrieval es el vector resultante de procesar esos tokens y **agruparlos** (pooling) o conservarlos como **multi-vector** (ColPali, módulo 16). Los **tokens discretos** de este módulo sirven sobre todo para **generar o comprimir**, no para comparar: para buscar PDFs en Políglota querrás vectores **continuos** alineados con texto. (La excepción son los *semantic IDs* de recomendación generativa, que usan RQ-VAE para indexar.)
""")

nb.md(r"""
## 12. Mapa de madurez (a oct-2026)

Con las tres modalidades vistas, esta tabla resume qué tokenizers son estándar y cuáles emergentes.

| Técnica | Madurez | Quién la usa / respaldo público | Fuente |
|---|---|---|---|
| Parches ViT (tokens continuos) | 🟢 | Base de los encoders visuales de CLIP/SigLIP y de VLMs abiertos que los conectan a un LLM (p. ej. LLaVA) | Dosovitskiy et al. 2020 (arXiv:2010.11929); Liu et al. 2023 (arXiv:2304.08485) |
| VQ-VAE | 🟢 (técnica) / 🟡 (como interfaz LLM) | Base de VQGAN y de los tokenizers de imagen discretos (DALL·E 1 usó una variante, el dVAE con relajación Gumbel-softmax) | van den Oord et al. 2017 (arXiv:1711.00937) |
| VQGAN (+ transformer *prior*) | 🟢 | CompVis; pérdida perceptual + adversarial sobre VQ | Esser et al. 2020 (arXiv:2012.09841) |
| **FSQ** | 🟡 | Tokenizers *discretos* de Cosmos (NVIDIA) con niveles (8,8,8,5,5,5) = 64 000 | Mentzer et al. 2023 (arXiv:2309.15505); Cosmos (arXiv:2501.03575) |
| LFQ / MAGVIT-v2 | 🟡 | Google/CMU; ICLR 2024; tokenizer de imagen+video con vocabulario común | Yu et al. 2023 (arXiv:2310.05737) |
| Tokens de imagen en un LLM (early fusion): Chameleon, Emu3 | 🟡 | Meta (Chameleon, 2024); BAAI (Emu3, 2024) | arXiv:2405.09818; arXiv:2409.18869 |
| Híbridos continuos+LM: Transfusion, MAR/Fluid (sin cuantización vectorial) | 🔴/🟡 | Meta (Transfusion, hasta 7B); resultados en investigación | arXiv:2408.11039; arXiv:2406.11838; arXiv:2410.13863 |
| Tokenizers 1D de imagen (TiTok, FlexTok) | 🔴 | ByteDance/TUM (32 tokens por imagen); EPFL/Apple | arXiv:2406.07550; arXiv:2502.13967 |
| SoundStream, **EnCodec**, DAC (RVQ) | 🟢 | EnCodec es el tokenizer de MusicGen (50 Hz, 32 kHz); DAC: 44.1 kHz a 8 kbps (~90x) | arXiv:2107.03312; 2210.13438; 2306.06546; 2306.05284 |
| **Mimi** (tokens semántico-acústicos, 12.5 Hz) | 🟡 | Kyutai (Moshi): conversación en tiempo real | arXiv:2410.00037 |
| Tokenizers de video 3D (Cosmos, MAGVIT-v2) | 🟡 | NVIDIA (pesos abiertos), Google | arXiv:2501.03575; arXiv:2310.05737 |

> Los modelos cerrados de frontera (multimodales nativos) **no documentan** sus tokenizers: lo que sabemos viene de papers abiertos.
""")

nb.md(r"""
## 13. 🏭 En producción

* **Imagen.** Los VLM abiertos más usados leen la imagen con un **encoder ViT continuo** y un proyector hacia el LLM (LLaVA); los modelos de **generación** tipo Chameleon/Emu3 usan **tokenizers discretos**; las líneas de investigación Transfusion/MAR/Fluid reducen o eliminan la cuantización. Los laboratorios de frontera cerrados no documentan sus tokenizers multimodales.
* **Audio.** **EnCodec** es el tokenizer de **MusicGen** (Meta; 50 Hz a 32 kHz según su paper) y de otros LMs de audio; **Mimi** (12.5 Hz, 1.1 kbps) es la pieza de **Moshi**, un modelo de diálogo en *streaming* (Kyutai). DAC (Descript) es un códec abierto de alta fidelidad.
* **Video.** NVIDIA publica los tokenizers Cosmos (discretos con FSQ y continuos). Los costes de contexto se gestionan con compresión agresiva, jerarquías y *streaming*.
* **Costes y trade-offs.** (1) Más compresión = menos contexto pero menos calidad; (2) más niveles RVQ = más tokens por segundo; (3) los tokens de audio **aplanados** multiplican el contexto por el nº de niveles (por eso Moshi usa un transformer de profundidad); (4) un tokenizer *no se cambia* sin reentrenar el LM (como en el módulo 07, pero sin tokenizer transfer fácil).
* **Políglota.** En esta fase el valor está en **entender el coste**: indexar audio/imagen con tokens discretos en un LLM generativo sería caro; el camino del módulo 16 (embeddings continuos y multi-vector) encaja mejor con retrieval.
""")

nb.md(r"""
## 14. 🧠 Secretos de la élite

1. **Mide la perplejidad de uso del codebook, siempre.** Un VQ con $K=8192$ y perplejidad 300 es un VQ de ~300 códigos; la calidad se estanca y no sabes por qué. Es la métrica de salud nº 1.
2. **FSQ simplifica el entrenamiento:** sin codebook, sin *commitment*, sin reinicios; el paper de FSQ reporta uso de codebook casi completo y calidad comparable a VQ (vigila la **escala de entrada** al `tanh`: si es pequeña, todo redondea al mismo nivel). Es el motivo de que Cosmos use FSQ (niveles 8,8,8,5,5,5).
3. **El *quantizer dropout* es el truco de SoundStream** para tener **un modelo, muchas tasas**; sin él, recortar niveles en inferencia da basura (el decoder nunca vio esa configuración).
4. **El primer nivel de RVQ concentra la «semántica».** Mimi lo aprovecha **destilando** WavLM en el primer cuantizador (split RVQ) para que los primeros tokens lleven contenido y los demás acústica.
5. **La tasa de frames manda el coste.** 75 Hz (EnCodec) vs 12.5 Hz (Mimi) son 6x de diferencia en pasos de LM a igual nº de niveles; baja la frecuencia con un encoder más profundo y *una buena pérdida*.
6. **MSE/SNR/PSNR no son calidad perceptual.** Los códecs reales usan pérdidas **perceptuales/adversariales** y se evalúan con tests de escucha (MUSHRA) o métricas como ViSQOL; los VQGAN, con LPIPS/FID. Reportar solo PSNR engaña.
7. **Los tokenizers 1D rompen la regla «una cuadrícula = una imagen»:** TiTok representa una imagen con 32 tokens (frente a 256 de VQGAN en el mismo experimento del paper); cuando el contexto es el cuello de botella, el tokenizer es una palanca mayor que el tamaño del LM.
8. **Lo que no puede cuantizarse bien, no se cuantiza:** Transfusion y MAR defienden que, para generación de imagen, mantener **tokens continuos** (con difusión por token) evita el techo de calidad de los codebooks.
""")

nb.md(r"""
## 15. ⚠️ Errores comunes

* **Olvidar el *stop-gradient*/STE:** sin STE el encoder no entrena; sin `detach` en el codebook loss, ambos términos se pisan.
* **Inicializar el codebook al azar con escala distinta a la del encoder:** los códigos nunca ganan y quedan muertos. Inicializa **con salidas del encoder** y reinicia los muertos.
* **Reportar solo PSNR** (o SNR) para comparar tokenizers/códecs: añade una métrica perceptual y escucha/mira las muestras.
* **Comparar bitrates sin contar los niveles aplanados:** «1.1 kbps» y «600 tokens/s» no son lo mismo que «tokens por segundo que ve el LM».
* **Evaluar en el *train*:** mide en datos no vistos (test), y con imágenes/audio de **otra distribución** si vas a generalizar.
* **Pensar que discreto = mejor:** depende de la tarea (generación vs retrieval vs comprensión).
""")

nb.md(r"""
## 16. Autoevaluación

""" + "\n\n".join([
    details("1 · (Cálculo) Chameleon tokeniza 512x512 en 1 024 tokens con un codebook de 8 192. ¿Cuántos bits por imagen, cuántos bits por píxel y cuánta compresión frente a RGB de 24 bpp?",
            "Bits = 1 024 · log₂ 8192 = 1 024 · 13 = **13 312 bits** (≈ 1.66 KB). Píxeles = 512² = 262 144 → **0.0508 bpp**. Compresión = 24 / 0.0508 ≈ **472x** (con pérdida)."),
    details("2 · (Cálculo) EnCodec a 24 kHz con 8 codebooks de 1 024 entradas y 75 frames/s: ¿tasa en kbps y tokens por minuto? ¿Y Mimi (12.5 Hz, 8 x 2048)?",
            "EnCodec: 75·8·10 = 6 000 bit/s = **6 kbps**; tokens/min = 75·8·60 = **36 000**. Mimi: 12.5·8·11 = **1 100 bit/s = 1.1 kbps**; tokens/min = 12.5·8·60 = **6 000** (o solo 750 pasos de tiempo si el LM modela los 8 niveles con un transformer de profundidad)."),
    details("3 · (Diagnóstico) Entrenas un VQ-VAE con K = 1 024 y la perplejidad de uso es 12. La reconstrucción es borrosa. ¿Qué pasa y qué pruebas, en orden?",
            "**Colapso del codebook**: se usan ~12 códigos. Pruebas: (1) inicializar el codebook con salidas del encoder (k-means); (2) reiniciar códigos muertos periódicamente; (3) reducir la dimensión del código $d$ o usar EMA; (4) pasar a FSQ/LFQ. Verifica con la perplejidad tras cada cambio."),
    details("4 · (Diagnóstico) Tu códec RVQ entrenado con Q = 8 suena bien con 8 niveles pero con 2 niveles es ruido. ¿Por qué?",
            "No se entrenó con *quantizer dropout*: el decoder nunca vio reconstrucciones desde pocos niveles y los niveles 1-2 no están optimizados para ser suficientes por sí solos. Solución: muestrear $n_q$ aleatorio por lote durante el entrenamiento (SoundStream)."),
    details("5 · (Transferencia) Políglota quiere buscar en PDFs con diagramas (módulo 16). ¿Elegirías tokens discretos tipo VQ o parches ViT continuos? ¿Por qué?",
            "Parches ViT **continuos** (y sus embeddings, p. ej. multi-vector): para *comparar* y buscar necesitas vectores alineados con el texto, no ids con pérdida de cuantización. Los tokens discretos sirven para **generar o comprimir**."),
    details("6 · (Transferencia) Un cliente quiere meter 1 hora de llamadas de soporte en un LLM de 128K de contexto. ¿Es viable con EnCodec a 6 kbps? ¿Y con Mimi? ¿Qué harías?",
            "EnCodec: 2.16 M de tokens → no cabe (128K ≈ 3.6 min). Mimi aplanado: 360 K tokens → tampoco; con un transformer de profundidad sobre 12.5 Hz×3600 = 45 000 pasos sí cabría en ~45K posiciones. Alternativas: **transcribir** (ASR) y usar texto (~13 K tokens/h), resumir por tramos, o indexar con embeddings por ventanas y recuperar."),
    details("7 · (Recuerdo) ¿Para qué sirve el *straight-through estimator* en un VQ-VAE?",
            "El argmin al codebook no es diferenciable. El STE hace $z_q = z_e + \\operatorname{sg}(e - z_e)$: en forward vale $e$ y en backward copia el gradiente de $z_q$ a $z_e$, de modo que el encoder aprende de la pérdida de reconstrucción."),
]))

nb.md(r"""
## 17. Referencias

Verificadas (título/autores/fecha) en arXiv en la fecha de redacción; venues revisados el 26-oct-2026.

* Dosovitskiy et al. **An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale.** ICLR 2021, arXiv:2010.11929.
* van den Oord, Vinyals, Kavukcuoglu. **Neural Discrete Representation Learning** (VQ-VAE). NeurIPS 2017, arXiv:1711.00937. · Razavi et al. **Generating Diverse High-Fidelity Images with VQ-VAE-2.** NeurIPS 2019, arXiv:1906.00446.
* Esser, Rombach, Ommer. **Taming Transformers for High-Resolution Image Synthesis** (VQGAN). CVPR 2021, arXiv:2012.09841.
* Mentzer, Minnen, Agustsson, Tschannen. **Finite Scalar Quantization: VQ-VAE Made Simple.** ICLR 2024, arXiv:2309.15505.
* Yu et al. **Language Model Beats Diffusion — Tokenizer is Key to Visual Generation** (MAGVIT-v2, LFQ). ICLR 2024, arXiv:2310.05737.
* Chameleon Team. **Chameleon: Mixed-Modal Early-Fusion Foundation Models.** arXiv:2405.09818. · Wang et al. **Emu3: Next-Token Prediction is All You Need.** arXiv:2409.18869.
* Zhou et al. **Transfusion: Predict the Next Token and Diffuse Images with One Multi-Modal Model.** ICLR 2025, arXiv:2408.11039. · Li et al. **Autoregressive Image Generation without Vector Quantization.** NeurIPS 2024, arXiv:2406.11838. · Fan et al. **Fluid: Scaling Autoregressive Text-to-image Generative Models with Continuous Tokens.** arXiv:2410.13863.
* Yu et al. **An Image is Worth 32 Tokens for Reconstruction and Generation** (TiTok). NeurIPS 2024, arXiv:2406.07550. · Bachmann et al. **FlexTok: Resampling Images into 1D Token Sequences of Flexible Length.** ICML 2025, arXiv:2502.13967.
* Zeghidour et al. **SoundStream: An End-to-End Neural Audio Codec.** IEEE/ACM TASLP 30 (2022), arXiv:2107.03312. · Défossez et al. **High Fidelity Neural Audio Compression** (EnCodec). TMLR 2023, arXiv:2210.13438. · Kumar et al. **High-Fidelity Audio Compression with Improved RVQGAN** (DAC). NeurIPS 2023, arXiv:2306.06546.
* Défossez et al. **Moshi: a speech-text foundation model for real-time dialogue** (Mimi). arXiv:2410.00037. · Zhang et al. **SpeechTokenizer: Unified Speech Tokenizer for Speech Large Language Models.** ICLR 2024, arXiv:2308.16692.
* Copet et al. **Simple and Controllable Music Generation** (MusicGen). NeurIPS 2023, arXiv:2306.05284.
* NVIDIA. **Cosmos World Foundation Model Platform for Physical AI.** arXiv:2501.03575.
* Liu et al. **Visual Instruction Tuning** (LLaVA). NeurIPS 2023, arXiv:2304.08485. · Rajput et al. **Recommender Systems with Generative Retrieval.** NeurIPS 2023, arXiv:2305.05065.
* Documentación: `torchvision.datasets.MNIST`, `transformers.EncodecModel`, `scikit-learn` (`load_sample_image`).

## 18. Siguiente paso

El **proyecto** (`08_proyecto_tokens_multimodales_audio.ipynb`) te pide tokenizar **una foto real y un clip de audio** y medir **reconstrucción y compresión** frente a JPEG y μ-law. El **módulo 09** vuelve al texto: la **capa de embedding** de los LLM, donde cada id que hemos aprendido a construir se convierte en un vector.
""")
nb.save(os.path.join(MOD_DIR, f"{SLUG}.ipynb"))

P.build(LESSON_REL, PROJ_REL, MOD_DIR, SLUG)

README = r"""# Módulo 08 · Tokens multimodales y de audio

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 6 h (lección ≈ 3.5 h + proyecto ≈ 2.5 h) · **Cómputo:** CPU en `FAST_DEV_RUN=True` (≈ 6-10 min); T4 en modo completo

| Archivo | Contenido |
|---|---|
| `08_tokens_multimodales_audio.ipynb` | Lección: presupuesto de tokens por modalidad, parches ViT (continuo), VQ-VAE/FSQ/RVQ desde cero en MNIST, colapso del codebook, un LM sobre tokens de imagen (mini-Chameleon), códec de audio de juguete con RVQ y *quantizer dropout* (SNR/LSD vs μ-law), EnCodec en `transformers`, tokenizers de video, tokens discretos vs continuos |
| `08_proyecto_tokens_multimodales_audio.ipynb` | Proyecto: **tokenizar una foto real (VQ) y un clip de audio (RVQ)** y medir reconstrucción y compresión vs JPEG y μ-law (plantilla con TODOs, pistas, rúbrica calibrada, solución tras SPOILER) |
| `assets/` | Imágenes/video de Gemini: `M08-IMG-01.png`, `M08-IMG-02.png`, `M08-IMG-03.png`, `M08-VID-01.mp4` |

## Objetivos
1. Distinguir tokens continuos (parches) y discretos (códigos) y calcular su coste de contexto.
2. Implementar VQ-VAE, FSQ y RVQ; medir PSNR, bits por imagen y perplejidad de uso del codebook.
3. Entrenar un LM sobre tokens de imagen y generar muestras.
4. Construir un códec de audio de juguete y medir kbps, SNR y distancia log-espectral.
5. Conectar con embeddings multimodales (módulo 16) sin adelantarlo.

## Datasets
**MNIST** real (`torchvision`, descarga desde el espejo de PyTorch; respaldo: figuras sintéticas), **foto real** empaquetada con scikit-learn (`china.jpg`, `flower.jpg`; sin descargas) y **voz real** del *Free Spoken Digit Dataset* (GitHub; respaldo: audio sintético «tipo voz»). Opcional: LibriSpeech pequeño / pesos de EnCodec desde el hub (no disponibles en el entorno de autoría; con fallback documentado). **Estado de pruebas:** MNIST real, fotos reales de scikit-learn, voz real FSDD y el respaldo sintético se ejecutaron; EnCodec/Mimi **con pesos reales** y LibriSpeech **no pudieron probarse** (hub bloqueado): la celda de EnCodec se probó con pesos aleatorios (solo formas y tasas).

## Lecturas
Oord et al. 2017 (VQ-VAE) · Esser et al. 2020 (VQGAN) · Mentzer et al. 2023 (FSQ) · Chameleon 2024 · Zeghidour et al. 2021 (SoundStream) · Défossez et al. 2022 (EnCodec) · Défossez et al. 2024 (Moshi/Mimi) · NVIDIA 2025 (Cosmos).

## Enlaces
Anterior: [07 · Tokenizer-free II y tokenizer transfer](../07_hnet_tokenizer_transfer/) · Siguiente: [09 · La capa de embedding en LLMs](../09_capa_embedding_llm/)
"""
with open(os.path.join(MOD_DIR, "README.md"), "w", encoding="utf-8") as f:
    f.write(README)
print("README escrito")
