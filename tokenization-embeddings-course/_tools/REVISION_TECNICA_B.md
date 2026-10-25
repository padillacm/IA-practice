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

## 10 · Embeddings contextuales y de oraciones
- Verificado: pooling con máscara (incl. último token con padding a izquierda/derecha), whitening W = UΛ^{−1/2}
  (y su comprobación W^⊤ΣW = I), ABTT, descomposición de L2 con vectores unitarios, cifras de SBERT (Tabla 1: BERT
  media 54.81, CLS 29.19, GloVe 61.32), autoevaluación (√0.4 ≈ 0.632; 5000 s), E5 `query:`/`passage:`.
  El proyecto elige en validación y reporta en test (correcto) y ajusta μ/W con documentos, no con consultas.
- **Arreglado:** la lección imprimía «whitening k=best» con el k elegido sobre las propias consultas de test sin
  avisar (contradice el secreto 4): ahora la salida lo etiqueta como optimista. El comentario del split decía
  «estratificada por idioma» y es un hash del qid (no estratificado).

## 11 · Aprendizaje contrastivo
- Verificado: gradiente (p_ij − 1[i=j])/τ, derivación de la cota de Oord (pasos 1–4, con 1+(K−1)a ≥ Ka para a ≤ 1) y
  la cota rigurosa de Poole et al.; experimento gaussiano (I = −½ log(1−ρ²) = 1.96 nats con crítico óptimo; la
  constante de normalización se cancela en el softmax); saturación en log K; McAllester & Stratos 2020; Tschannen et
  al. 2020; τ de SimCSE (0.05) y E5 (0.01), MNRL `scale=20`; DPR (1 negativo BM25, lotes de 128); TopK-PercPos 95 %;
  CCPairs ≈ 270M; Gradient Cache exacto; autoevaluación (p = 0.599, pérdida 0.51; log 64 = 4.16).
- **Arreglado:** la respuesta del diagnóstico 3 («pérdida muy baja + colapso») daba «temperatura enorme» como causa;
  con negativos reales un modelo colapsado tiene pérdida ≈ log B, así que pérdida baja + colapso implica que los
  negativos no entran en la pérdida. Reescrita.
- Recomendaciones: (a) los negativos duros de un par se comparten como columnas con todo el lote; `grupo` evita
  conceptos repetidos entre consultas, pero un duro del par j puede ser del concepto de i (falso negativo cruzado):
  mencionarlo. (b) Los pares débiles del proyecto incluyen documentos relevantes del test (primera frase → resto):
  es entrenamiento transductivo legítimo (como ICT/GPL), pero conviene decirlo explícitamente.
