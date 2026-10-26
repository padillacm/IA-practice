# Revisión élite / industria · Bloque A (módulos 00–08)

Revisor élite A (oct-2026), con la vara «experto de laboratorio/empresa top» (equipos de tokenización y datos de
preentrenamiento). Criterio: ¿las secciones 🏭 y 🧠 son concretas, verificables y explican **por qué** importan?
¿Falta algo que todo experto sabría? Donde la lección solo mencionaba, se añadió **implementación pequeña** (CPU,
`FAST_DEV_RUN`). Toda afirmación nueva tiene fuente comprobada en esta revisión (arXiv/GitHub) o se presenta como
práctica habitual sin cifra. Cambios en los builders; notebooks regenerados y ejecutados con `nbclient` en una copia
(`OMP_NUM_THREADS=1`, CPU). No se tocó nada hecho por las revisiones técnica, pedagógica, de ejecutabilidad ni de referencias.

## 04 · Diseño de tokenizers modernos
Diagnóstico: 🏭 y 🧠 ya eran concretos y con fuente, pero faltaba lo que hace un equipo **antes** de un preentrenamiento
caro: auditar el vocabulario más allá de la fertilidad, por qué el tokenizer no se cambia después, la trampa de la
pérdida por token, slots reservados / $V$ físico y que las leyes de escala están en unidades de un tokenizer.
- **Añadido §11.1 Auditoría del vocabulario antes de preentrenar** (por qué no se puede cambiar después: ids ligados a
  filas, shards ya tokenizados, presupuestos en tokens, checkpoints de referencia) + `auditoria_vocab()`: round-trip,
  bytes/token por idioma, **eficiencia de Rényi α=2.5** (Zouhar et al., ACL 2023: 0.78 vs −0.32 con BLEU) con su
  contraejemplo (Cognetta et al., LREC-COLING 2024), % de $V$ visto en held-out (riesgo de sub-entrenados), token más
  largo. Resultado medido: Rényi empeora (0.74→0.50) mientras bytes/token mejora; el candidato de 16 k se queda en
  ≈ 13 k (el $V$ real ≠ el pedido).
- **Añadido §11.2 Trampa de la pérdida por token** con un LM unigrama por tokenizer: nats/token elige V=1000, bpb elige
  V=16000 (3.30→2.57). Lista de errores al calcular bpb (bytes del texto original, todos los tokens, mismo texto).
- **Añadido §11.3 Slots reservados, $V$ físico y leyes de escala**: `v_fisico()` (nanoGPT 50 257→50 304, verificado en
  `model.py`; Llama 3 128 000 + 256 = 128 256, verificado en `llama/tokenizer.py`); «reservado ≠ entrenado» (filas a
  cero en Llama 3 base: ⚠️ fuente secundaria, marcada); Chinchilla 70 B / 1.4 T con SentencePiece 32 000 sin NFKC
  (verificado en el PDF) → la regla «20 tokens/parámetro» con dos tokenizers da 1.67× de diferencia en texto.
- 🧠: sustituidos los puntos 3 (token tax, duplicado con §7 y 🏭) y 4 (tablas de embeddings, duplicado con §4) por
  «el tokenizer es la unidad de tus leyes de escala» y «reservado no es entrenado + Rényi y su trampa». 🏭: bullet de
  auditoría como práctica habitual. Tabla de decisiones y referencias actualizadas. Lección: 63 → 72 celdas.

## 02 · BPE desde cero
Diagnóstico: 🧠 sólido (desempates y orden de merges, regex de dígitos, sub-entrenados, bpb), con fuentes. Faltaba la
interacción **tokenizer ↔ mezcla de datos** y su lado de seguridad/privacidad.
- **Añadido §9.7 (ampliación, en la 🧭) «Lo que los merges delatan»**: formulación de Hayase et al. (NeurIPS 2024;
  cifras de su abstract: GPT-4o ≈ 39 % no inglés, Mistral NeMo ≈ 47 %, GPT-3.5 y Claude ≈ 60 % código, presentadas
  como estimaciones de los autores) e implementación mínima: BPE sobre mezclas con pesos conocidos por byte →
  inferencia por rejilla en el símplex con muestras de *test* por categoría. Error absoluto medio medido: 0.00 / 0.03 /
  0.10 (peor con mezcla dominada por código). ≈ 20 s en CPU.
- 🧠 #5 (token a medio carácter UTF-8, ya cubierto en 01 #8 y en §7) sustituido por «los merges filtran tu mezcla de
  datos» (privacidad + auditoría del tokenizer heredado). Referencia añadida. Lección: 81 → 84 celdas.
