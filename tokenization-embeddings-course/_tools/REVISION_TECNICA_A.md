# Revisión técnica · Bloque A (módulos 00–08)

Revisor técnico A (oct-2026). Se leyó el código de los builders (`_tools/builders/build_NN.py` y auxiliares) y se
verificaron cifras con el vocabulario real de GPT-2 (espejo GitHub con SHA-256) y con fuentes primarias cuando hizo
falta. Cambios aplicados en los builders y notebooks regenerados; recomendaciones no aplicadas al final de cada módulo.

## 00 · Intro
- Métricas canónicas (`poliglota_src/metrics.py`) y BM25 (`bm25.py`) revisados: DCG lineal, dedup, convención trec_eval,
  IDF Okapi con suelo ε·IDF medio idéntico a `rank_bm25`. Ejemplos resueltos (nDCG@4 = 0.651; nDCG@5 = 0.624) correctos.
- IDs GPT-2 del prompt M00-IMG-02 verificados (`30642 11341 1210 2420 656 3146 13`).
- **Arreglado:** rango de vocabularios «≈ 32 000–250 000» → «≈ 32 000–262 000» (Gemma 3 usa 262 144). Igual en 02.
- «Hasta 15 veces más tokens» (Petrov et al. 2023): coincide con el abstract.

## 01 · Unicode y bytes
- UTF-8 a mano, decodificador estricto, NFD a mano (Hangul + orden canónico) y fuzzing: correctos.
- Cifras de la tabla de 12 idiomas (bytes/code point; tokens GPT-2: EN 7, ES 13, tailandés 61, coreano 43) verificadas.
- **Arreglado:** la caja «Qué debes observar» de NFC vs NFD decía que GPT-2 tiene tokens `ción` o `más`; no los tiene
  (`canción` → `can·ci·ón`, `más` → `m·ás`). Ahora cita `ón`, `ás`, `ño`, que sí existen.

## 02 · BPE desde cero
- Revisado a fondo: `entrena_incremental` (actualización de vecinos incl. casos solapados `aaa`/`aaaa`, heap con
  invalidación perezosa) es equivalente al ingenuo con desempate lexicográfico; `_encode_trozo` por rango de merge;
  puente `a_tiktoken`/`desde_tiktoken` (receta minbpe). Ejemplo de Sennrich resuelto a mano correcto.
- Afirmaciones verificadas: Zouhar et al. 2023 (≈ 0.37; O(NM)→O(N log M)), Kozma & Voderholzer 2024 (APX-completo,
  0.333–0.625), Llama 3 (100 K + 28 K), mapeo modelo→encoding de tiktoken 0.14.0 y n_vocab 100 277 / 200 019,
  Singh & Strouse 2024 (R2L con comas).
- Arreglado: rango de vocabularios de la tabla de la sección 1 (hasta 262 000).
- Recomendación (no aplicada): `BPETokenizer.encode` codifica como texto normal un especial no permitido; `tiktoken`
  lanza error por defecto. Mencionarlo como diferencia de diseño.

## 03 · WordPiece, Unigram, SentencePiece
- Derivación de ΔL de WordPiece (exacta y aproximación m·(PMI−1)), ejemplo `hug/pug/pun/bun/hugs` (score 1/36 vs 0.05;
  ΔL exacto 28.0 para `##u##g`), lattice/forward-backward/Viterbi de Unigram y el ejemplo `hugs` (P(X)=0.1751,
  posterior 0.857) verificados. Defaults de SentencePiece (`shrinking_factor` 0.75, `max_sentence_length` 4192,
  semilla 1 M) y cifras de producción (Llama 3 3.17→3.94 chars/token, T5 10:1:1:1, Tekken) coherentes con las fuentes.
- **Arreglado (03, 04, 05):** `_a2_common.METRICS` usaba ganancia exponencial y no deduplicaba, distinto de la métrica
  canónica del módulo 00 (lineal, como trec_eval, con dedup). Ahora `METRICS` se lee de `poliglota_src/metrics.py`
  (fuente única). Con qrels binarios los números no cambian.
- **Arreglado:** prompt M03-IMG-03 decía «cuatro chips» y listaba cinco.
- Recomendación: `puntuaciones(..., "verosimilitud")` no trata el caso `a == b` (p. ej. `##a##a`), donde c_a baja 2m.

## 04 · Diseño de tokenizers modernos
- Fórmulas de presupuesto (12·L·d², V·d / 2·V·d, ahorro lineal vs cuadrático) y sus cifras (≈ 10–13 % → 46–54 %;
  autoevaluación ≈ 14 %) verificadas. Tao et al. 2024 (≥ 216 K para Llama2-70B; ARC-C 29.1→32.0), Qwen2
  (151 643 + 3), SuperBPE (−33 % tokens, +4.0 en 30 tareas, +8.2 MMLU, −27 % cómputo; LAMBADA 77.0→70.6) y
  Dagan et al. 2024 (> 50 B tokens) contrastados con los artículos.
- **Arreglado (04 y 05):** se citaba GPT-4 «84.4 % → 98.9 %» (Singh & Strouse 2024); el artículo solo da cifras
  exactas para GPT-3.5 (75.6 % → 97.8 %, 8-shot, sumandos de 7–9 dígitos) y describe el efecto en GPT-4 como algo
  menor. Se reescribió en la sección 9, en los secretos y en el módulo 05.
- Recomendación: la tabla de vocabularios dice «Gemma 3 ≈ 262 k / 256 k»; añadir la cifra del tokenizer publicado
  (262 144 piezas) cuando se pueda verificar con HF.

## 05 · Patologías y robustez
- Indicadores de Land & Bartolo (2024) contrastados con el PDF: distancia coseno de filas de salida a la media de
  tokens de referencia (bytes 0xF5–0xFF) y norma de entrada para no atados; la variante con PCA del apéndice A no
  mejora de forma consistente, así que omitirla está bien. Banco MiniGPT con «intrusos» (verdad de referencia) correcto.
- Auditoría de tiktoken verificada en GPT-2 (344 parciales = 0.68 %, 0 inalcanzables). Phan et al. 2024 (≈ 18 % en FIM),
  derivación del gradiente para tokens nunca objetivo y token healing coherentes.
- **Arreglado:** la sección 6 decía que el indicador coseno es «para modelos con embeddings atados»; en el artículo
  vale con o sin tying (toda la matriz de salida recibe gradiente). Cifras GPT-4 de Singh & Strouse (ver 04).

## 06 · Tokenizer-free I (bytes, BLT)
- Código revisado: Witten-Bell, reglas de parcheo global/monótona, calibración por bisección, entropías con ventana
  deslizante (contexto máximo), MiniBLT (máscaras por parche, decodificación con el parche anterior y prueba de
  causalidad), bpb del baseline BPE normalizado por bytes de los objetivos. Correcto.
- Cifras de BLT contrastadas con arXiv:2412.09871 (Tablas 1, 3, 4, 8: 60.0/58.0/61.1; CUTE 27.5/20.0/54.1;
  «contains char» 0.0/55.9; HellaSwag con ruido 56.9/64.3; FLORES 12.1→14.0 y 5.9→6.4; ablación n-gramas
  0.850→0.826; modelo de entropía 100M/14 capas/ventana 512). Bolmo (arXiv:2512.15586, Olmo 2 1B / Olmo 3 7B) existe.
- **Arreglado:** MambaByte se describía como «350M en el paper»; el artículo entrena 353M y 972M (y 1.6B en la prueba
  de velocidad). El ahorro de inferencia a FLOPs fijos compara con baselines Llama 2 **y** Llama 3 (se añadió).
  El video M06-VID-01 decía «34 bytes» para una frase de 35.
- Recomendación: `es_espacio` trata los bytes iniciales UTF-8 (≥ 0xC0) como no-espacio, una variante razonable para
  español que conviene declarar frente a la definición de SpaceByte.

## 07 · H-Net y tokenizer transfer
- MiniHNet contrastado con arXiv:2507.07955: routing p_t = ½(1−cos(q_t,k_{t−1})), p_1 = 1, selección de bordes,
  EMA z̄_j = P_j ẑ_j + (1−P_j) z̄_{j−1}, STE de la confianza, residual lineal, ratio loss (Ec. 10, α = 0.03, mínimo 1 en
  F = G = 1/N). Tabla 2 del paper (bpb 0.756/0.760/0.755/0.755/0.743 y 0.730/0.733/0.726/0.728/0.715; precisión media)
  coincide exactamente. ICLR 2026 (H-Net) y NeurIPS 2025 (AU-Net) verificados.
- Tokenizer transfer: sparsemax, FOCUS (sparsemax sobre solapados en espacio auxiliar), WECHSEL (Procrustes, k = 10,
  τ = 0.1), FVT (Gee et al., EMNLP 2022, arXiv:2402.09977), `mean_resizing` de transformers (covarianza × 1e-9) y las
  cifras de ZeTT (−14 % longitud, > 16 % velocidad, XNLI a 1 %, código −10 % tokens a ≈ 3 %, < 1B tokens) verificadas
  en el PDF. Todas las referencias arXiv del mapa de madurez existen (SOMBRERO 2601.22805, ALM 2503.20083, etc.).
- Sin cambios necesarios. Recomendación: WECHSEL-lite usa los tokens compartidos como diccionario (el original usa un
  diccionario bilingüe de palabras); ya está declarado como «lite».

## 08 · Tokens multimodales y de audio
- Tasas verificadas: ViT (224/16)² = 196, Chameleon 512² → 1024 tokens (codebook 8192, vocabulario total 65 536),
  Cosmos FSQ (8,8,8,5,5,5) = 64 000 y compresiones 4x8x8/8x8x8/8x16x16, EnCodec 75 Hz × 10 bits (1.5–24 kbps),
  SoundStream (strides 2·4·5·8 = 320), Mimi 12.5 Hz × 8 × 11 bits = 1.1 kbps, MusicGen (EnCodec 32 kHz, 50 Hz),
  128K tokens ≈ 3.6 min a 600 tok/s. Autoevaluación (13 312 bits, 0.0508 bpp, ≈ 472x) correcta.
- Código: VQ (pérdida codebook + β·commitment, STE, init por datos, reinicio de códigos muertos), FSQ (acotado con
  tanh y desplazamiento para L par, índice en base mixta, como la implementación de referencia), RVQ con quantizer
  dropout, códec toy (stride 64 → 125 Hz × 8 bits = 1 kbps por nivel) y μ-law. Correcto. Sin cambios.

## Pendientes y recomendaciones generales
- `extras/GEMINI_ASSETS.md` está desactualizado (40 de 67 recursos y prompts antiguos de M03-IMG-03 y M06-VID-01):
  regenerarlo con `gen_gemini_index.py` en la pasada final de consistencia (no se hizo aquí para no pisar a los autores
  que trabajan en 09–11).
- Los umbrales de rúbrica de 00–08 están calibrados con corpus sintético/espejo (avisado en cada proyecto); conviene
  recalibrarlos con datos reales (HF/openaipublic) cuando el entorno lo permita (revisor de ejecutabilidad).
- `tiktoken` cl100k/o200k no se descargan en este entorno (openaipublic bloqueado): las cifras de 03–05 con esos
  encodings vienen de la medición de los autores y no se recalcularon aquí; GPT-2 sí se verificó (espejo con SHA-256).
