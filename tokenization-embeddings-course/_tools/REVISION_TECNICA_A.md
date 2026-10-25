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
