# Revisión de ejecutabilidad · Bloque A (módulos 00–08)

Revisor de ejecutabilidad A (oct-2026). Cada notebook se ejecutó de arriba abajo con `nbclient` sobre una **copia** en el
scratchpad (sin outputs ni archivos generados dentro del curso), con `FAST_DEV_RUN=True`, CPU (`CUDA_VISIBLE_DEVICES=""`),
`OMP_NUM_THREADS=2` (4 CPUs compartidas), timeout de 600 s por celda y `allow_errors=True` para listar todos los fallos.
La celda `!pip install` se ejecutó como `--dry-run` (comprueba que los paquetes resuelven sin tocar el entorno).

Red del entorno: Hugging Face, openaipublic (tiktoken), Zenodo y la API de Wikipedia → 403 del proxy; raw.githubusercontent.com,
PyPI, arXiv y el espejo de PyTorch (MNIST) → OK. En Colab las ramas oficiales deberían funcionar.

| Notebook | Tiempo | Estado | Datos | Rúbrica (solución) | Cambios |
|---|---|---|---|---|---|
| 00 lección | 17 s | OK | Sintético ES/EN (aviso ⚠️ visible) + stdlib Python real; GPT-2 vía espejo GitHub con SHA-256 | — | — |
| 00 proyecto | 7 s | OK | Ídem | 12/12 (nDCG@10 0.878 ≥ 0.82) | — |
| 01 lección | 14 s | OK | Ídem | — | — |
| 01 proyecto | 15 s | OK | Ídem | 13/13 | — |
| 02 lección | 21 s | OK | Ídem; encode propio == tiktoken GPT-2 (18/18) | — | — |
| 02 proyecto | 7 s | OK | Ídem | 13/13 | — |
| 03 lección | 39 s | OK | **Real**: Europarl ES/EN (espejo NLTK en GitHub) + stdlib; r50k/cl100k/o200k no descargables (aviso) | — | pip sin `-U` |
| 03 proyecto | 14 s | OK | Real (ídem) | 11/11 | pip sin `-U` |
| 04 lección | 43 s | OK | Real (Europarl); tokenizers del hub no disponibles (aviso) | — | pip sin `-U` |
| 04 proyecto | 15 s | OK | Real (Europarl) | 13/16: los 3 pts «tiktoken o200k/cl100k disponible» no son alcanzables tras este proxy (sí en Colab). Mejora J 11 % (≥ 8 %), desbalance 1.20 (≤ 1.35) | pip sin `-U` |
| 05 lección | 93 s | OK | Real (Europarl) | — | pip sin `-U` |
| 05 proyecto | 74 s | OK | Real (Europarl) | 11/11 (prec@100 1.00, recall 0.42, AUC 1.0, P5 83 %) | pip sin `-U` |
| 06 lección | 274 s | OK | Sintético (aviso) + stdlib | — | — |
| 06 proyecto | 46 s | OK | Ídem | 7/7 (plantilla 0/7, esperado) | — |
| 07 lección | 370 s | OK | Sintético (aviso) + stdlib | — | — |
| 07 proyecto | 152 s | OK | Ídem | 7/7 | **R3 recalibrada** (ver abajo) |
| 08 lección | 354 s | OK | **MNIST real** (torchvision), fotos reales de scikit-learn, **voz real FSDD** (GitHub); EnCodec con pesos aleatorios (hub bloqueado, aviso) | — | **audio real con cadena**; `torchaudio` opcional |
| 08 proyecto | 140 s | OK | Fotos reales + voz real FSDD | 6/6 tras recalibrar R5 | **R5 recalibrada** |

Total bloque A en FAST_DEV_RUN/CPU: ≈ 28 min. Todas las celdas TODO de los proyectos están envueltas (`NotImplementedError`
capturado o rúbrica con ⬜/❌), así que «Ejecutar todo» nunca se rompe.

## Cambios aplicados (en builders; notebooks regenerados)
- **03–05 · `_a2_common.pip_cell`**: `!pip install -q -U tokenizers …` → sin `-U`. Actualizar solo `tokenizers` en Colab
  puede sacarlo del rango que exige el `transformers` preinstalado e impedir `import transformers` (04 y 05 lo usan).
- **07 proyecto · R3** (`_a3_proj07.py`): comparaba el bpb **cero-shot** FVT vs init aleatoria con margen 0; la diferencia
  medida es mínima y cambia entre entornos (autor 3.549 vs 3.554; aquí 3.572 vs 3.581). Ahora compara tras la fase de solo
  embeddings (K1 pasos), donde la ventaja es estable: medido 0.703 vs 0.779 → umbral FVT ≤ aleatoria − 0.03. Se imprime
  también el valor de la init aleatoria tras K1.
- **08 lección · EnCodec** (`_a3_src08.py`): `import torchaudio` estaba fuera del `try` y rompía la celda sin torchaudio
  (paquete en modo mantenimiento; su última versión en PyPI va por detrás de torch). Ahora es opcional, con remuestreo
  polifásico de SciPy como respaldo (probado).
- **08 · audio** (`_a3_src08.py`, `build_08.py`, `_a3_proj08.py`): el audio era siempre sintético, sin cadena de descarga.
  Ahora: **Free Spoken Digit Dataset** (repositorio oficial en GitHub, 8 kHz, CC BY-SA 4.0; descarga paralela de ~560
  wavs en segundos) → respaldo sintético con aviso ⚠️. Test con grabaciones distintas (índices 45–49). Textos de lección,
  proyecto y README actualizados.
- **08 proyecto · R5** recalibrada con lo medido con voz real: SNR 1.46 → 2.94 dB (1 → 4 niveles); umbral ≥ 2.5 dB y
  ganancia ≥ 1.0 dB (el respaldo sintético da 5.7 → 10.1 dB y también cumple).

## Comprobado sin cambios
- Primera celda `!pip install` correcta para Colab en todos (resuelve con `--dry-run`). En la lección 00 la celda de
  entorno va en la sección «Entorno del curso» (las celdas previas solo usan matplotlib/numpy, preinstalados en Colab).
- Avisos de datos sintéticos/espejo visibles en todas las cadenas (Wikipedia, CodeSearchNet, tiktoken, HF, MNIST, FSDD).

## Pendientes
- Recalibrar con datos reales de Wikipedia/HF (00–02, 06, 07 corrieron con corpus sintético) y verificar en Colab los 3
  pts de tiktoken o200k/cl100k del proyecto 04 y EnCodec con pesos reales (08).
- 06/07/08 tardan 4–6 min en CPU en FAST_DEV_RUN (celdas de entrenamiento de 70–150 s): aceptable, pero por encima del resto.
- Los builders generan IDs de celda aleatorios: regenerar produce diffs ruidosos; convendría fijar IDs deterministas en `nbbuild.py`.
