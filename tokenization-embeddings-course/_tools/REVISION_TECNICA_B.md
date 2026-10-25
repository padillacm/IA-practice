# Revisión técnica · Bloque B (módulos 09–20 y extras)

Revisor técnico B (oct-2026). Se leyó el código de los builders (`_tools/builders/build_NN.py` y auxiliares) y se
contrastaron fórmulas y cifras con fuentes primarias cuando hizo falta. Cambios aplicados en los builders y notebooks
regenerados; recomendaciones no aplicadas al final de cada módulo. Métricas canónicas: `poliglota_src/metrics.py`
(módulos 00–14) y `15_evaluacion_retrieval/poliglota_eval.py` (15–20) revisadas: ganancia lineal, dedup, convención
trec_eval, bootstrap por queries, test pareado por *shift*, sign-flip y Holm correctos.

## 09 · Capa de embedding en LLMs
- Verificado: one-hot·E, gradiente de salida (p_j − 1[j=y])·h y colapso hacia −h̄, decaimiento AdamW e^{−ηλn},
  rango ≤ d+1 del log-softmax, cifras de GPT-2 small (38 597 376 = 31 % de 124 439 808; 163 037 184 sin tying),
  memoria de logits (8.4 GB), autoevaluación (262 M = 21.8 %; e^{−1}), Godey et al. 2024, nanoGPT 50 304.
- **Arreglado:** R2 del proyecto («colapso de filas no vistas») es un test válido solo con el mini-GPT-2 de fallback
  (allí «no visto en Políglota» = «nunca visto al entrenar»); con GPT-2 real fallaría sin ser un error del alumno.
  Ahora R2 solo se exige en el fallback y la rúbrica lo explica.
- Recomendación: `bpb_y_fuga` trunca a T=64 *tokens*, así que el tokenizer extendido evalúa un trozo de texto algo más
  largo que el base; bpb lo normaliza, pero truncar por bytes haría la comparación exacta.
