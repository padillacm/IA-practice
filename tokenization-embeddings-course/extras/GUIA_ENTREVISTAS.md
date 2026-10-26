# Guía de entrevistas · Tokenización, embeddings y system design de búsqueda

> Curso «Tokenización y Embeddings: de BPE a los modelos modernos» · material de cierre del módulo 19 · estado del arte a **octubre de 2026**.
> 50 preguntas de básico a experto con **respuesta modelo**, **qué distingue a un candidato senior** y **banderas rojas**, más una rúbrica general y seis casos de *system design* resueltos.
> Las cifras que aparecen se pueden recalcular con las fórmulas del curso; las que dependen de proveedores llevan fecha.

## Cómo usar esta guía
* **Como candidato:** responde en voz alta antes de leer la respuesta modelo; cronométrate (2–4 min por pregunta conceptual, 35–45 min por caso de diseño). Después compara con la rúbrica, no con la memoria.
* **Como entrevistador:** elige 3–4 preguntas conceptuales de niveles crecientes + 1 caso de diseño. Puntúa con la rúbrica general; las «banderas rojas» pesan más que los aciertos.
* **Niveles:** 🟢 básico · 🟡 intermedio · 🟠 avanzado · 🔴 experto. Cada pregunta indica el módulo del curso donde se trabaja.

## Rúbrica general (para cualquier pregunta)
| Puntuación | Nivel | Qué se observa |
|---|---|---|
| 1 | No apto | Define términos de memoria sin mecanismo; no puede hacer un cálculo de servilleta; confunde métricas o espacios (p. ej. compara vectores de modelos distintos). |
| 2 | Junior | Explica el mecanismo correctamente; aplica la fórmula si se le guía; no menciona trade-offs ni cómo medir. |
| 3 | Senior | Mecanismo + cálculo correcto sin ayuda + trade-offs + **cómo lo mediría** (métrica, baseline, IC). Reconoce cuándo **no** usar la técnica. |
| 4 | Staff / élite | Lo anterior + fallos silenciosos y su detección, costo a escala, plan de migración/rollback, distingue lo 🟢 sólido de lo 🔴 experimental y cita evidencia concreta. |

Señales transversales de nivel alto: empieza por **requisitos y números** (N, QPS, SLA, memoria, idiomas), propone un **baseline fuerte** (BM25), habla de **evaluación pareada con IC**, y nombra **qué podría salir mal** sin que se lo pidan.

---

## A · Tokenización (preguntas 1–14)

### 1. 🟢 ¿Qué devuelve `len()` para «é» y por qué puede valer 1 o 2? (M01)
**Respuesta modelo.** Depende de la forma Unicode. En NFC «é» es un solo *code point* (U+00E9) → `len == 1` en Python, que cuenta code points. En NFD es «e» + U+0301 (tilde combinante) → `len == 2`. En UTF-8 ocupa 2 bytes en NFC y 3 en NFD. Un **grafema** (lo que ve el usuario) es uno en ambos casos. Consecuencia: normaliza (NFC) **igual** en indexación y en consulta, o tu tokenizer y tu BM25 verán cadenas distintas.
**Senior:** distingue bytes / code points / grafemas y sabe que Python cuenta code points, JavaScript unidades UTF-16. **Bandera roja:** «un carácter es un byte».

### 2. 🟢 ¿Por qué un BPE a nivel de byte no tiene tokens desconocidos? (M02)
**Respuesta modelo.** El vocabulario inicial son los 256 bytes; cualquier texto en UTF-8 es una secuencia de bytes, así que en el peor caso se codifica byte a byte. Los merges solo agrupan. El precio: textos raros (scripts poco representados) se fragmentan mucho → más tokens, más costo y más contexto consumido.
**Senior:** menciona `byte_fallback` en SentencePiece como la solución análoga para Unigram/BPE de caracteres. **Bandera roja:** confundir «sin OOV» con «representa bien todos los idiomas».

### 3. 🟢 Describe el entrenamiento y la codificación de BPE. ¿Qué complejidad tienen? (M02)
**Respuesta modelo.** Entrenamiento: contar pares adyacentes en el corpus pre-tokenizado, fusionar el más frecuente en un token nuevo, actualizar conteos, repetir hasta el tamaño de vocabulario; la implementación ingenua recuenta todo en cada merge ($O(M \cdot N)$ con $M$ merges y $N$ tamaño del corpus), la incremental solo actualiza los pares vecinos del par fusionado (con una cola de prioridad). Codificación: aplicar los merges **en orden de prioridad** (el rango del merge), no por frecuencia en el texto a codificar; la decodificación concatena bytes.
**Senior:** explica el desempate y por qué dos implementaciones entrenadas con el mismo corpus pueden diferir. **Bandera roja:** codificar «buscando el par más frecuente del texto de entrada».

### 4. 🟡 BPE vs WordPiece vs Unigram: ¿qué optimiza cada uno? (M03)
**Respuesta modelo.** BPE: fusiona el par **más frecuente** (codicioso, de abajo arriba). WordPiece: fusiona el par que **más sube la verosimilitud** del corpus bajo un modelo unigrama (≈ frecuencia del par normalizada por la de sus partes). Unigram LM (Kudo 2018): empieza con un vocabulario grande y **poda** los tokens cuya eliminación menos reduce la verosimilitud, optimizada con EM; segmenta con Viterbi y permite **muestrear** segmentaciones (*subword regularization*). SentencePiece es la librería que implementa BPE y Unigram sobre texto crudo con `▁` como espacio.
**Senior:** sabe que Unigram da una distribución sobre segmentaciones y lo conecta con robustez. **Bandera roja:** «SentencePiece es un algoritmo».

### 5. 🟡 ¿Para qué sirve el regex de pre-tokenización de GPT-2/cl100k/o200k? (M02, M04)
**Respuesta modelo.** Corta el texto en trozos (palabras con su espacio inicial, números, puntuación, espacios) **antes** de BPE, para que los merges no crucen esas fronteras: evita tokens como «perro.» o «. El», estabiliza la tokenización de contracciones y controla cómo se agrupan los dígitos (cl100k/o200k limitan los números a grupos de hasta 3 dígitos). Cambiar el regex cambia la compresión y el comportamiento aritmético.
**Senior:** conecta con SuperBPE (tokens que cruzan palabras, un relajamiento deliberado de esta regla). **Bandera roja:** no saber que existe un paso previo a BPE.

### 6. 🟡 ¿Qué es la fertilidad y cómo medirías el «impuesto de idioma»? (M04)
**Respuesta modelo.** Fertilidad = tokens por palabra (o por carácter/byte). El impuesto se mide con **texto paralelo** (mismo contenido en varios idiomas, p. ej. FLORES): ratio de tokens del idioma X frente al inglés. Petrov et al. (2023) y Ahia et al. (2023) muestran diferencias de varias veces entre idiomas: se paga más por el mismo contenido y cabe menos en el contexto.
**Senior:** usa texto paralelo, no corpus distintos; reporta también bytes/token. **Bandera roja:** comparar fertilidad con textos no paralelos.

### 7. 🟡 Cálculo: vocabulario de 128 k y $d=4096$. ¿Cuántos parámetros tiene la matriz de embedding? ¿Y con unembedding sin atar? (M04, M09)
**Respuesta modelo.** $128\,000 \times 4096 \approx 5.2\times10^8$ (≈ 0.52 B) por matriz; sin *weight tying* son dos matrices ≈ 1.05 B. En bf16, ≈ 1 GB y 2 GB. Trade-off del vocabulario: más grande ⇒ secuencias más cortas (menos cómputo de atención, más contexto efectivo) pero más parámetros, softmax más caro y tokens raros peor entrenados.
**Senior:** menciona el efecto en modelos pequeños (la cabeza pesa proporcionalmente mucho) y las leyes de escala del vocabulario. **Bandera roja:** no saber hacer el producto.

### 8. 🟠 ¿Qué son los tokens «glitch» y cómo los detectarías sin ejecutar el modelo? (M05)
**Respuesta modelo.** Tokens que existen en el vocabulario pero casi no aparecieron en los datos de entrenamiento del modelo (el tokenizer se entrenó con otro corpus): sus embeddings apenas recibieron gradiente y el modelo se comporta de forma anómala con ellos («SolidGoldMagikarp», Rumbelow & Watkins 2023). Detección (Land & Bartolo 2024): embeddings de entrada cercanos al centroide de tokens nunca vistos o con norma atípica, frecuencia ~0 en un corpus de referencia, y verificación por comportamiento (pedir al modelo que repita el token).
**Senior:** explica *por qué* colapsan (solo reciben gradiente vía weight decay/softmax). **Bandera roja:** «es un bug del tokenizer».

### 9. 🟠 ¿Por qué la tokenización de números afecta a la aritmética? (M04, M05)
**Respuesta modelo.** Si los dígitos se agrupan en bloques de izquierda a derecha («12345» → «123»,«45»), los bloques no se alinean con las posiciones decimales y el modelo debe aprender sumas con acarreos entre fragmentos variables. Singh & Strouse (2024) muestran que forzar el agrupamiento de derecha a izquierda mejora la exactitud en aritmética de LLMs de frontera. Alternativas: un dígito por token.
**Senior:** propone un experimento controlado (mismo modelo, prompts con separadores de miles). **Bandera roja:** atribuirlo solo a «falta de datos».

### 10. 🟠 ¿Qué es el problema del *prompt boundary* y qué es *token healing*? (M05)
**Respuesta modelo.** Si el prompt termina a mitad de lo que normalmente sería un token (p. ej. «http:» sin «//»), el modelo ve una tokenización que casi nunca vio en entrenamiento y la continuación se degrada. *Token healing*: retroceder el último token del prompt y restringir la generación a continuaciones cuyo prefijo coincida con el texto eliminado.
**Senior:** lo conecta con espacios finales en prompts y con la tokenización de chat templates. **Bandera roja:** no ver la relación con la tokenización.

### 11. 🟠 ¿Qué riesgos tiene NFKC frente a NFC en un pipeline de búsqueda? (M01, M05)
**Respuesta modelo.** NFC solo compone equivalencias canónicas (no cambia el significado visible). NFKC además aplica equivalencias de **compatibilidad**: ligaduras «ﬁ»→«fi», ancho completo → ASCII, superíndices «²»→«2», lo que puede cambiar el significado (fórmulas, códigos) pero ayuda contra homoglifos y variantes. Elegir uno y aplicarlo **igual** en ambos lados; además, filtrar invisibles y controles bidi (Trojan Source, Boucher & Anderson 2021).
**Senior:** distingue normalización (equivalencia) de seguridad (homoglifos entre scripts, que NFKC no resuelve). **Bandera roja:** «normalizar siempre con NFKC y listo».

### 12. 🟡 Da dos bugs típicos de tokens especiales o *chat templates*. (M04)
**Respuesta modelo.** (a) Tokenizar texto de usuario con tokens especiales permitidos: el usuario puede inyectar `<|endoftext|>` o marcas de rol (en `tiktoken`, `allowed_special`/`disallowed_special`). (b) Aplicar a un modelo un template distinto del que usó en su ajuste (roles, saltos de línea, BOS duplicado): el modelo funciona «casi» bien y nadie lo detecta. (c) Añadir BOS/EOS dos veces al concatenar.
**Senior:** propone un test de contrato que compare la tokenización con la plantilla oficial. **Bandera roja:** no saber que los tokens especiales se tratan aparte.

### 13. 🔴 Explica el *patching* por entropía del Byte Latent Transformer y su madurez. (M06)
**Respuesta modelo.** BLT (Pagnoni et al. 2024) agrupa bytes en *patches* dinámicos: un modelo pequeño de bytes estima la entropía del siguiente byte y se abre un patch nuevo cuando supera un umbral (texto predecible → patches largos). Un encoder local convierte bytes en representaciones de patch, un transformer **latente** grande opera por patch y un decoder local vuelve a bytes. El ahorro: el modelo grande corre una vez por patch, no por byte, y el cómputo se asigna donde hay incertidumbre. Madurez 🟡/🔴: resultados prometedores a escala de investigación, ecosistema y serving inmaduros frente a BPE.
**Senior:** compara FLOPs por byte con un modelo de tokens y menciona H-Net (chunking aprendido). **Bandera roja:** «la tokenización está muerta».

### 14. 🔴 Quieres adaptar un LLM preentrenado a un tokenizer nuevo para español técnico. ¿Opciones? (M07)
**Respuesta modelo.** *Tokenizer transfer*: crear el vocabulario nuevo e **inicializar** sus embeddings de forma informada — media de los embeddings de los sub-tokens antiguos que lo componen (FVT), combinaciones ponderadas por similitud en un espacio auxiliar (FOCUS, WECHSEL), alineación por traducción (Trans-Tokenization) o hiperredes que predicen embeddings para cualquier tokenizer (ZeTT, Minixhofer et al. 2024) — y luego un ajuste corto. Medir en **bits por byte** (no perplejidad por token, que no es comparable entre tokenizers) antes y después.
**Senior:** sabe por qué la perplejidad por token engaña. **Bandera roja:** «cambio el tokenizer y reentreno solo la cabeza».

---

## B · Embeddings (preguntas 15–30)

### 15. 🟢 Con vectores normalizados, ¿coseno, producto punto y L2 dan el mismo ranking? (M10, M14)
**Respuesta modelo.** Sí: si $\lVert q\rVert=\lVert d\rVert=1$, $\cos = q\cdot d$ y $\lVert q-d\rVert^2 = 2 - 2\,q\cdot d$, monótona decreciente. Sin normalizar, el producto punto favorece vectores de norma grande (en algunos modelos, la norma correlaciona con la longitud o la frecuencia).
**Senior:** comprueba la norma en un test de contrato. **Bandera roja:** usar producto punto con vectores sin normalizar «porque es más rápido».

### 16. 🟢 ¿Qué es el *weight tying* y cuándo conviene? (M09)
**Respuesta modelo.** Compartir la matriz de embedding de entrada con la de salida (unembedding) (Press & Wolf 2017; Inan et al. 2016): ahorra $V\cdot d$ parámetros y regulariza. Conviene sobre todo en modelos pequeños, donde esas matrices son una fracción grande del total; muchos modelos grandes las desatan para dar más capacidad a la cabeza.
**Bandera roja:** no saber que existen dos matrices.

### 17. 🟡 Pooling CLS vs media vs último token. ¿Qué bug típico tiene el último token? (M10, M12)
**Respuesta modelo.** CLS: un vector entrenado para resumir (bueno si el modelo se entrenó así). Media: promedio con **máscara** de padding (robusto, estándar en SBERT). Último token: natural en decoders causales (solo el último ha visto todo). Bug: con *padding* a la derecha, la posición «última» del tensor es un token de padding; hay que indexar por longitud real o usar padding a la izquierda.
**Senior:** menciona latent attention pooling (NV-Embed) y atención bidireccional (LLM2Vec). **Bandera roja:** promediar incluyendo el padding.

### 18. 🟡 ¿Qué es la anisotropía y cómo se corrige? (M10)
**Respuesta modelo.** Los embeddings de modelos preentrenados ocupan un cono estrecho: casi cualquier par tiene coseno alto, lo que reduce el contraste. Correcciones: centrar (restar la media), *whitening* (centrar y decorrelacionar con la covarianza), quitar las dimensiones dominantes (all-but-the-top) o, mejor, **entrenamiento contrastivo**, que optimiza la uniformidad.
**Senior:** sabe que whitening se ajusta en un corpus y puede no transferir. **Bandera roja:** creer que coseno alto implica similitud semántica alta.

### 19. 🟡 Escribe InfoNCE y explica la temperatura y los negativos en el lote. (M11)
**Respuesta modelo.** $\mathcal{L} = -\frac1B\sum_i \log \frac{\exp(s(q_i,d_i)/\tau)}{\sum_j \exp(s(q_i,d_j)/\tau)}$: cada query debe identificar su documento entre los $B$ del lote; los otros $B-1$ son negativos gratis. $\tau$ pequeña afila el softmax (concentra el gradiente en los negativos difíciles), grande lo suaviza; valores típicos en retrieval ≈ 0.01–0.05. Lotes más grandes ⇒ más negativos ⇒ mejor (Gradient Cache permite lotes grandes con poca memoria).
**Senior:** deriva el gradiente respecto a un negativo (proporcional a su probabilidad softmax). **Bandera roja:** no saber qué papel tiene $\tau$.

### 20. 🟠 Negativos duros: ¿cómo los minas y qué es un falso negativo? (M11)
**Respuesta modelo.** Negativos duros = documentos parecidos pero no relevantes (top-k de BM25 o de un embedder previo). Riesgo: muchos son **relevantes no etiquetados** (falsos negativos) y enseñan lo contrario. Mitigaciones: descartar los candidatos con score cercano al positivo (p. ej. umbral relativo tipo TopK-PercPos, Moreira et al. 2024), filtrar con un cross-encoder o saltar los primeros puestos.
**Bandera roja:** «cuanto más duros, mejor».

### 21. 🟠 ¿Por qué InfoNCE es una cota de la información mutua y qué implica? (M11)
**Respuesta modelo.** Oord et al. (2018): $I(X;Y) \ge \log K - \mathcal{L}_{\text{InfoNCE}}$ con $K$ candidatos. La cota satura en $\log K$: con pocos negativos no puede estimar más información que $\log K$ (Poole et al. 2019). Implicación práctica: más negativos permiten «aprender más»; pero optimizar la cota no garantiza buenas representaciones (alineación y uniformidad, Wang & Isola 2020).
**Senior:** sabe que la cota es floja y por qué. **Bandera roja:** confundir la pérdida con la MI.

### 22. 🟠 ¿Cómo funciona Matryoshka y qué haces al truncar? (M12)
**Respuesta modelo.** Kusupati et al. (2022): se suma la pérdida en varios prefijos del vector ($d_1 < d_2 < \dots$), forzando a que las primeras dimensiones sean un buen embedding por sí mismas. Al truncar hay que **renormalizar**. Sin entrenamiento Matryoshka, truncar degrada mucho más (mejor PCA). Varias APIs exponen la dimensión de salida como parámetro.
**Bandera roja:** truncar sin renormalizar, o truncar un modelo no entrenado así esperando lo mismo.

### 23. 🟠 Cálculo: 50 M de vectores de 1024 d. Memoria en float32, int8 y binario. ¿Cómo recuperas calidad con binario? (M12, M18)
**Respuesta modelo.** float32: $5\cdot10^7 \cdot 4096$ B = **204.8 GB**; int8: **51.2 GB**; binario: **6.4 GB**. Binario + *rescoring*: buscar candidatos (top-$K$, p. ej. 100) con Hamming en RAM y reordenarlos con la query en float contra vectores int8/float leídos de disco (Shakir et al. 2024). int8 necesita **calibrar** rangos por dimensión.
**Senior:** combina con Matryoshka (512 d → la mitad) y discute qué vive en RAM vs SSD. **Bandera roja:** no saber hacer la cuenta.

### 24. 🟠 Bi-encoder vs cross-encoder vs late interaction: costo y calidad. (M10, M13)
**Respuesta modelo.** Bi-encoder: un vector por texto, documentos precalculados, búsqueda ANN: barato, menos preciso. Cross-encoder: lee query y documento juntos (atención cruzada completa): el más preciso, pero $O(\text{candidatos})$ pasadas por query ⇒ solo para reordenar un top-K. Late interaction (ColBERT): un vector por token y MaxSim $\sum_i \max_j q_i\cdot d_j$: precisión cercana al cross-encoder con documentos precalculados, a costa de **almacenamiento** (un vector por token; ColBERTv2 lo comprime con residuos, PLAID acelera, MUVERA lo reduce a un vector fijo para usar ANN estándar).
**Bandera roja:** proponer un cross-encoder sobre todo el corpus.

### 25. 🟠 ¿Qué es SPLADE y cuándo lo preferirías a un denso? (M13)
**Respuesta modelo.** Un modelo que produce un vector **disperso** sobre el vocabulario (pesos por término, incluidos términos de expansión) a partir de las logits MLM con $\log(1+\mathrm{ReLU})$ y max-pooling, con regularización FLOPS para la dispersión. Se sirve con índice invertido: hereda la exactitud léxica y la interpretabilidad, con expansión aprendida. Útil cuando importan identificadores y términos raros o cuando ya tienes infraestructura de índice invertido.
**Bandera roja:** confundirlo con TF-IDF.

### 26. 🔴 ¿Cómo se convierte un LLM decoder en embedder? (M12)
**Respuesta modelo.** Opciones: pooling del **último token** con una instrucción en el prompt (e5-mistral, Qwen3-Embedding); habilitar **atención bidireccional** y adaptar con MNTP + contrastivo (LLM2Vec, BehnamGhader et al. 2024); **latent attention pooling** (NV-Embed, Lee et al. 2024). Todos terminan con ajuste contrastivo. Trade-off: mejor calidad en benchmarks, pero 10–100× más cómputo por embedding que un encoder pequeño.
**Senior:** cuantifica el costo de embedding del corpus con cada opción. **Bandera roja:** «usar los hidden states medios de cualquier LLM sin ajuste».

### 27. 🔴 ¿Qué dice LIMIT sobre los límites de los embeddings de un solo vector? (M15)
**Respuesta modelo.** Weller et al. (2025) muestran, con un argumento de empaquetamiento de esferas con margen γ ($d \ge \log\binom{n}{k}/\log(1+1/\gamma)$; la primera versión usaba el rango de signo de la matriz de qrels), que con dimensión $d$ fija hay combinaciones de documentos relevantes (top-k) que **no pueden** representarse para todas las queries; construyen un dataset sencillo (LIMIT) donde embedders punteros fallan y modelos multi-vector o sparse lo hacen mejor. Implicación de diseño: para consultas combinatorias («documentos que mencionan A y B»), un solo vector tiene un techo; el híbrido y el reranking no son opcionales.
**Bandera roja:** «basta con subir la dimensión» sin matizar.

### 28. 🔴 ¿Qué es el *modality gap* en CLIP y por qué importa en un índice mixto? (M16)
**Respuesta modelo.** Los embeddings de imagen y de texto ocupan regiones separadas de la esfera (Liang et al. 2022), en parte por la inicialización y la temperatura del contrastivo. En un índice con textos e imágenes, una query de texto tiende a recuperar textos antes que imágenes relevantes. Mitigaciones: índices separados con fusión, centrado por modalidad, o modelos entrenados para cerrarlo.
**Bandera roja:** mezclar modalidades en un índice sin medir.

### 29. 🔴 ¿Puede un embedding revelar el texto original? ¿Qué haces en producción? (M17, M18)
**Respuesta modelo.** Sí: vec2text (Morris et al. 2023) reconstruye gran parte de textos cortos iterando un modelo de corrección; Song & Raghunathan (2020) muestran inversión e inferencia de atributos. En producción: los vectores heredan la clasificación del texto (acceso, cifrado, retención, borrado propagado a índice/caché/backups, aislamiento de tenants en el servidor). El ruido reduce el ataque pero también la utilidad; no sustituye a los controles.
**Bandera roja:** «los embeddings son anónimos».

### 30. 🟡 ¿Cómo eliges un embedder para un producto? ¿Qué te dice y qué no MTEB? (M12, M15)
**Respuesta modelo.** MTEB/MMTEB dan una primera criba por tarea e idioma, pero: la media mezcla tareas irrelevantes, hay riesgo de contaminación/overfitting al leaderboard y no mide tu dominio, latencia ni costo. Proceso: 3–6 candidatos por restricciones (licencia, idiomas, tamaño, on-prem) → golden set propio estratificado → nDCG con **IC pareado** → frontera calidad/latencia/memoria (Matryoshka, cuantización) → decisión.
**Bandera roja:** elegir el primero del leaderboard.

---

## C · Retrieval, índices y evaluación (preguntas 31–40)

### 31. 🟢 Escribe BM25 y explica $k_1$ y $b$. (M00, M13)
**Respuesta modelo.** $\text{score}(q,d)=\sum_{t\in q}\mathrm{idf}(t)\,\frac{tf_{t,d}(k_1+1)}{tf_{t,d}+k_1\left(1-b+b\frac{|d|}{\text{avgdl}}\right)}$. $k_1$ controla la **saturación** de la frecuencia (≈ 1.2: la 10.ª aparición aporta poco más que la 3.ª); $b$ la **normalización por longitud** (0 = ninguna, 1 = total; ≈ 0.75). El idf penaliza términos comunes.
**Bandera roja:** no saber que BM25 satura la frecuencia.

### 32. 🟡 ¿Qué es RRF y por qué funciona sin calibrar scores? (M13)
**Respuesta modelo.** $\text{RRF}(d)=\sum_r \frac{1}{k+\text{rango}_r(d)}$ con $k\approx 60$ (Cormack et al. 2009). Usa solo **rangos**, así que no hace falta que los scores de BM25 y del denso estén en la misma escala. La combinación lineal de scores normalizados puede superarla si se ajusta el peso **sin fuga** (Bruch et al. 2022).
**Bandera roja:** sumar scores crudos de BM25 y coseno.

### 33. 🟡 Parámetros de HNSW: $M$, `efConstruction`, `efSearch`. (M14)
**Respuesta modelo.** $M$: número de vecinos por nodo y capa (más ⇒ más recall y más memoria, ≈ $2M$ enteros por vector en la capa 0). `efConstruction`: tamaño de la lista de candidatos al insertar (calidad del grafo y tiempo de construcción). `efSearch`: tamaño del haz en la búsqueda (recall vs latencia, ajustable por query). La búsqueda baja de capas dispersas a densas de forma voraz.
**Senior:** sabe que los borrados degradan el grafo y que el filtrado rompe la conectividad. **Bandera roja:** no distinguir parámetros de construcción y de búsqueda.

### 34. 🟠 Explica IVF-PQ y la distancia asimétrica (ADC). Memoria por vector. (M14)
**Respuesta modelo.** IVF: k-means en $n_{list}$ centroides; cada vector va a la lista de su centroide; la búsqueda solo visita `nprobe` listas. PQ: dividir el vector en $m$ subvectores y cuantizar cada uno con 256 centroides (1 byte) ⇒ $m$ bytes por vector. ADC: para una query, precalcular una tabla $m\times256$ de distancias a los centroides de cada subespacio; la distancia a un vector es la suma de $m$ consultas a la tabla. Con $m=64$: 64 B/vector (frente a 3 072 B en float32 con $d=768$). Se suele reordenar (*refine*) un top-K con vectores exactos.
**Bandera roja:** creer que PQ descomprime los vectores para comparar.

### 35. 🟠 Búsqueda filtrada: pre-filtro, post-filtro, filtro en el grafo. (M14, M18)
**Respuesta modelo.** Post-filtro: buscar top-K y descartar los que no cumplen ⇒ con filtros selectivos devuelve menos de $k$ (o nada). Pre-filtro: restringir a los candidatos que cumplen y buscar entre ellos (fuerza bruta si son pocos, o un índice por partición). Filtro en el grafo: recorrer el grafo saltando nodos que no cumplen, con cuidado de no desconectarlo (ACORN, Patel et al. 2024). La elección depende de la **selectividad**.
**Bandera roja:** post-filtrar ACL con 2 % de documentos visibles.

### 36. 🟡 Cálculo: ranking [d3, d1, d9, d2], relevantes {d1: 3, d2: 2, d5: 1}. nDCG@4 con ganancia lineal. (M00, M15)
**Respuesta modelo.** DCG = $3/\log_2 3 + 2/\log_2 5 = 1.893 + 0.861 = 2.754$. IDCG = $3/\log_2 2 + 2/\log_2 3 + 1/\log_2 4 = 3 + 1.262 + 0.5 = 4.762$. nDCG@4 ≈ **0.578**. (d5 no aparece: cuenta en el ideal.)
**Bandera roja:** normalizar solo por los relevantes recuperados.

### 37. 🟠 ¿Cómo decides si el sistema B es mejor que A con 300 queries? (M15)
**Respuesta modelo.** Métrica **por query** para ambos sistemas sobre las **mismas** queries → test pareado (bootstrap pareado de la diferencia media con IC95, o permutación de signos); la unidad de remuestreo es la **query**. Si comparas muchos sistemas, corrige (Holm). Reporta Δ, IC y p, además de slices (idioma, tipo de query). Smucker et al. (2007) comparan tests para IR.
**Bandera roja:** comparar dos medias sin IC o con un test no pareado.

### 38. 🟠 ¿Qué sesgos tienen los qrels por *pooling* y los jueces LLM? (M15, M19)
**Respuesta modelo.** Pooling: solo se juzga el top-k de los sistemas existentes; un sistema nuevo que encuentra relevantes no juzgados es penalizado. LLM-as-judge: puede acercarse a juicios humanos en algunos entornos (Thomas et al. 2023) pero tiene sesgos (preferencia por textos parecidos a lo que genera, sensibilidad al prompt, circularidad si el juez se parece al sistema evaluado; Soboroff 2024 advierte contra sustituir a humanos). Mitigación: pools de varios sistemas, juzgar el top-k del sistema nuevo, validar el juez con una muestra humana (κ).
**Bandera roja:** usar el mismo LLM como generador y como juez sin validación.

### 39. 🟠 Tu nDCG offline sube 0.03 y online no cambia nada. Hipótesis. (M18, M19)
**Respuesta modelo.** (a) La mezcla de tráfico difiere del golden set (pondera por slice); (b) la interfaz muestra 3 resultados y la mejora está en las posiciones 4–10; (c) las queries reales tienen respuestas que el golden set no contiene o son ambiguas; (d) la mejora está dentro del IC; (e) la latencia subió y compensa; (f) el experimento online no tiene potencia (usa interleaving).
**Senior:** propone cómo distinguir cada hipótesis con datos. **Bandera roja:** «los usuarios no saben lo que quieren».

### 40. 🟠 ¿Cómo detectas drift en un buscador sin etiquetas? (M15, M18)
**Respuesta modelo.** Señales sin etiquetas por ventana temporal: distribución de la similitud top-1 (y su PSI frente a una referencia), fracción de queries «huérfanas» (top-1 bajo), distancia entre centroides de queries, tasa de queries sin clics/reformuladas, distribución de idiomas y longitudes. Las alarmas disparan **muestreo y etiquetado** de queries huérfanas, no un reentrenamiento automático.
**Bandera roja:** esperar a que bajen las métricas de negocio.

---

## D · Producción (preguntas 41–44)

### 41. 🟠 Cálculo: re-embeber 10 M de chunks de 400 tokens. API a 0.02 $/1M vs GPU a 0.80 $/h con 20 000 tokens/s al 60 %. (M18)
**Respuesta modelo.** $T = 4\cdot10^9$ tokens. API: **80 $**. GPU: $4\cdot10^9/(20\,000\cdot3600\cdot0.6) = 92.6$ h ⇒ **≈ 74 $** (≈ 4 días con 1 GPU). El costo es parecido; deciden tiempo de calendario, cuotas, residencia de datos y control de versión del modelo. (Precio de API: tarifa estándar publicada de `text-embedding-3-small` a oct-2026; GPU: supuestos.)
**Bandera roja:** olvidar la utilización o la doble memoria durante la migración.

### 42. 🟠 Plan para migrar de embedder v1 a v2 en un índice de 100 M de vectores. (M18)
**Respuesta modelo.** Colección nueva v2 (nunca mezclar versiones), **backfill** con doble escritura de documentos nuevos, evaluación en sombra (test pareado en golden set + interleaving), cambio **atómico** de un alias `prod`, v1 conservada para rollback, invalidación de cachés (la versión va en la clave). Adaptador lineal v2→v1 (ridge/Procrustes con pares) solo como puente mientras dura el backfill, con su propia puerta de calidad (puede quedar por debajo de v1 con pocos pares). Presupuesto: tokens + doble RAM durante semanas + evaluación.
**Bandera roja:** re-embeber in situ sobre el índice que sirve tráfico.

### 43. 🟠 Fan-out a 50 shards, cada uno con un 1 % de respuestas lentas. ¿Qué fracción de queries es lenta y cómo lo mitigas? (M18)
**Respuesta modelo.** $1-0.99^{50}\approx$ **39.5 %**. Mitigaciones: menos shards (réplicas completas si el índice cabe, cuantización para que quepa), *hedged requests* tras el p95 (Dean & Barroso 2013), timeouts con resultados parciales, aislar fuentes de lentitud (GC, compactaciones).
**Bandera roja:** optimizar la media.

### 44. 🟡 ¿Qué debe llevar la clave de una caché de embeddings? (M18)
**Respuesta modelo.** Hash del texto **normalizado** (NFC, minúsculas si el modelo es insensible, espacios) + **versión** completa del vector (modelo, checkpoint, servidor, preprocesado, prefijo, dimensión/precisión). Sin versión, tras una migración se sirven vectores viejos contra un índice nuevo **sin error** visible: las queries populares (aciertos) se rompen y las raras no.
**Bandera roja:** clave = texto crudo.

---

## E · System design (casos 45–50)

**Estructura esperada de la respuesta (35–45 min):** (1) requisitos y supuestos explícitos (5 min) → (2) estimación de capacidad: unidades, tokens, memoria por precisión, QPS, réplicas (5–8 min) → (3) arquitectura offline y online (10 min) → (4) evaluación offline y online con criterios de aceptación (5 min) → (5) operación: versionado, migración, monitorización, privacidad (5 min) → (6) riesgos y siguiente iteración (3 min).

**Rúbrica de los casos (100 pts):** capacidad correcta ±15 % (25) · la arquitectura respeta memoria y SLA con números (25) · cubre los requisitos específicos del caso (20) · plan de evaluación pareado + online (15) · operación y riesgos (15). *Staff:* cuantifica alternativas descartadas y dice qué mediría primero.

### 45. 🔴 Búsqueda semántica de documentación técnica multilingüe: 5 M documentos × 2 400 tokens, chunks de 400, ES/EN/PT + código, 300 QPS, p99 150 ms, máquinas de 64 GB. (M19, proyecto C1)
**Respuesta modelo.** Capacidad: $5\cdot10^6\cdot2400/400 = 3\cdot10^7$ chunks; $1.2\cdot10^{10}$ tokens; float32 $d=768$: 92 GB (no cabe en el 70 % de 64 GB = 45 GB); int8 + grafo HNSW (≈ 256 B): ≈ 31 GB → cabe. Réplicas: $\max(2, \lceil 300/500\rceil)=2$ (QPS por réplica es un supuesto que se mide). Arquitectura: embedder multilingüe (API o autohospedado), BM25 con tokenización de identificadores (códigos de error), RRF, reranker sobre top-40 (≈ 80 ms), total ≈ 140 ms. Evaluación: golden set ≥ 300 queries estratificado por idioma/tipo con test ciego, IC pareado vs actual, interleaving. Operación: alias, re-embedding ≈ 240 $ con API a 0.02 $/1M.
**Banderas rojas:** confundir documentos con chunks; float32 sin mirar la RAM; sin BM25.

### 46. 🔴 Búsqueda de código interna con permisos: 4 M chunks de 300 tokens, $d=1024$, cada usuario ve ~2 % de los repos, commits cada minuto, on-prem, 50 QPS, p99 300 ms, 32 GB. (proyecto C2)
**Respuesta modelo.** float32: 16.4 GB + grafo ≈ 17.4 GB ≤ 22.4 GB → HNSW float32. ACL: **pre-filtro en el servidor** (≈ 80 k candidatos ⇒ fuerza bruta sobre el subconjunto en pocos ms) o grafo con filtros; nunca post-filtro ni filtro en el cliente. Streaming: HNSW admite inserciones; borrados marcados + compactación. Embedder de código autohospedado; BM25 con split de `snake_case`/`camelCase`. Re-embedding en GPU propia ≈ 22 $ (supuestos). Tests de autorización en CI.
**Banderas rojas:** post-filtro; enviar código a una API externa.

### 47. 🔴 RAG de soporte sobre 200 k PDFs escaneados (4 M páginas) con tablas y diagramas, datos de salud en la UE, borrado en 30 días. (M16, proyecto C3)
**Respuesta modelo.** Multi-vector visual tipo ColPali: 4 M × ~1 030 × 128 × 2 B ≈ 1 TB → no en RAM. Diseño: primera etapa con OCR + embedder de texto (16.4 GB float32 + grafo, cabe) e híbrido con BM25; segunda etapa MaxSim visual solo sobre top-K páginas leídas de SSD (o MUVERA/binarización para reducir). Privacidad: todo autohospedado en la UE, cifrado y acceso por rol, borrado por `doc_id` en índice/caché/backups con auditoría, logs sin PII. Evaluación: golden set por tipo de página (texto/tabla/diagrama) — ahí se decide si lo visual compensa.
**Banderas rojas:** multi-vector entero en RAM; «el ruido protege los datos».

### 48. 🔴 Búsqueda de productos: 300 M de ítems, 5 000 QPS, filtros de precio/categoría/stock, actualizaciones de stock por segundo. (M14, M18)
**Respuesta modelo.** Memoria: $d=256$ (Matryoshka) int8 = 77 GB + grafo ≈ 77 GB por copia → shards por categoría o DiskANN; réplicas $\lceil 5000/500\rceil = 10$ (supuesto) por shard. Filtros: stock/precio como atributos filtrables **dentro** de la búsqueda (pre-filtro por partición de categoría + filtro en grafo); los cambios de stock no re-embeben (son payload). Híbrido: BM25 para marcas/SKUs + denso para intención; reranker con señales de negocio (aprendizaje de ranking) fuera de alcance del embedder. Evaluación: interleaving con clics + A/B de conversión. Cola: el fan-out por shards exige hedged requests.
**Banderas rojas:** re-embeber al cambiar el precio; ignorar la cola con 10+ shards.

### 49. 🔴 Deduplicar casi-duplicados en 1 B de documentos antes de entrenar un modelo. (M14, M19)
**Respuesta modelo.** Dos niveles: (1) léxico barato (MinHash + LSH sobre shingles) para casi-duplicados textuales, que escala a miles de millones con poca memoria; (2) semántico (embeddings + ANN con umbral de coseno) para paráfrasis, sobre lo que sobrevive o por bloques. Cálculo de memoria del paso 2: 1 B × 256 d binario = 32 GB (factible), con rescoring. Evaluación: precisión/recall de pares sobre una muestra etiquetada, y efecto aguas abajo (métrica del modelo entrenado). Umbral elegido en validación, no a ojo.
**Banderas rojas:** todos-contra-todos ($10^{18}$ pares); umbral sin muestra etiquetada.

### 50. 🔴 «Tras cambiar a un embedder nuevo, el nDCG online cae para las queries más populares y sube para el resto.» Diagnostica. (M18, M19)
**Respuesta modelo.** Patrón típico de **caché sin versión**: las populares son aciertos de caché con vectores del modelo viejo comparados contra el índice nuevo; las raras se embeben con el modelo nuevo. Verificación: tasa de aciertos por bucket de popularidad vs caída de calidad; comprobar la versión en la clave y en los metadatos de los vectores. Arreglo: versión en la clave, invalidación al mover el alias, test de contrato que compare vector servido vs recalculado para una muestra. Post-mortem sin culpables con la regla nueva en el linter de PRs.
**Banderas rojas:** culpar al modelo y hacer rollback sin entender la causa.

---

### Referencias citadas en la guía
Press & Wolf 2017 (arXiv:1608.05859) · Inan et al. 2016 (arXiv:1611.01462) · Kudo 2018 (arXiv:1804.10959) · Petrov et al. 2023 (arXiv:2305.15425) · Ahia et al. 2023 (arXiv:2305.13707) · Rumbelow & Watkins 2023 (LessWrong, «SolidGoldMagikarp») · Land & Bartolo 2024 (arXiv:2405.05417) · Singh & Strouse 2024 (arXiv:2402.14903) · Boucher & Anderson 2021 (arXiv:2111.00169) · Pagnoni et al. 2024 (BLT, arXiv:2412.09871) · Minixhofer et al. 2024 (ZeTT, arXiv:2405.07883) · Oord et al. 2018 (arXiv:1807.03748) · Poole et al. 2019 (arXiv:1905.06922) · Wang & Isola 2020 (arXiv:2005.10242) · Moreira et al. 2024 (NV-Retriever, arXiv:2407.15831) · Kusupati et al. 2022 (arXiv:2205.13147) · Shakir, Aarsen, Lee 2024 (blog de Hugging Face) · BehnamGhader et al. 2024 (arXiv:2404.05961) · Lee et al. 2024 (NV-Embed, arXiv:2405.17428) · Weller et al. 2025 (arXiv:2508.21038) · Liang et al. 2022 (arXiv:2203.02053) · Morris et al. 2023 (arXiv:2310.06816) · Song & Raghunathan 2020 (arXiv:2004.00053) · Cormack et al. 2009 (SIGIR) · Bruch et al. 2022 (arXiv:2210.11934) · Patel et al. 2024 (ACORN, arXiv:2403.04871) · Smucker et al. 2007 (CIKM) · Thomas et al. 2023 (arXiv:2309.10621) · Soboroff 2024 (arXiv:2409.15133) · Dean & Barroso 2013 (CACM).
