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
