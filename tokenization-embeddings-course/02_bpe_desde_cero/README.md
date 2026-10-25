# Módulo 02 · BPE desde cero

**Nivel:** 🟡 Intermedio · **Duración:** ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) · **Cómputo:** CPU (0 unidades de Colab)

| Archivo | Contenido |
|---|---|
| `02_bpe_desde_cero.ipynb` | Lección: BPE (Gage 1994; Sennrich et al. 2016), ejemplo resuelto a mano, byte-level BPE (GPT-2), regex de pre-tokenización (GPT-2 / cl100k / o200k), entrenamiento ingenuo vs incremental, `encode`/`decode`, verificación contra `tiktoken` y HF `tokenizers` (y contra el GPT-2 real), experimentos (vocabulario, Zipf, impuesto de idioma, regex, bits por byte, orden de merges), complejidad |
| `02_proyecto_bpe_desde_cero.ipynb` | Proyecto: tu BPE entrenado en Políglota, verificado contra `tiktoken` y HF, evaluado (bytes/token, impuesto de idioma, barrido de vocabulario) y guardado en `poliglota_bpe.json` |
| `assets/` | Carpeta (con `.gitkeep`) para `M02-IMG-01..03.png` y `M02-VID-01.mp4` (celdas Gemini) |

## Objetivos
1. Situar BPE entre palabras y caracteres; resolver a mano el ejemplo `low/lower/newest/widest`.
2. Implementar byte-level BPE completo (regex, entrenamiento incremental, encode por rango, decode).
3. Comparar los regex de GPT-2, cl100k y o200k.
4. Verificar contra `tiktoken` y HF `tokenizers` (codificación idéntica; entrenamiento distinto por los desempates).
5. Medir compresión, vocabulario, impuesto de idioma, bits por byte y complejidad.

## Prerrequisitos
Módulos 00 (corpus, métricas) y 01 (bytes, UTF-8, normalización).

## Convenciones que este módulo aporta
* **`BPETokenizer`**: `vocab` (id→bytes), `merges` ((id_a, id_b)→id nuevo; el id es la prioridad), `special`; `encode(texto, allowed_special, max_id)`. El módulo 03 puede compararlo con WordPiece/Unigram.
* **Desempate del curso:** mayor conteo; empate → par menor lexicográfico (`tiktoken._educational`/`minbpe` usan «primer visto»; HF otra regla).
* **`desde_tiktoken(enc)`** recupera merges de cualquier `tiktoken.Encoding` (receta de `minbpe`), útil para cargar `cl100k_base`/`o200k_base` en tu propia clase.
* **`poliglota_bpe.json`** (salida del proyecto): `pat_str`, `merges` en orden, métricas. Patrones `PAT_GPT2/PAT_CL100K/PAT_O200K` copiados de `tiktoken` 0.14.0.

## Datos
Corpus Políglota (módulo 00). Partición 80/20 por documento.

## Estado de pruebas (entorno de autoría)
Ejecutado entero con `nbclient` sobre el corpus **sintético** (+ funciones reales de la stdlib). Con **datos reales de Wikipedia/CodeSearchNet no se pudo probar** (Hugging Face y Wikipedia bloqueados). Los vocabularios `cl100k_base`/`o200k_base` tampoco se pudieron descargar (CDN de OpenAI bloqueado): sus parches se verificaron contra el código de `tiktoken` 0.14.0 y la comparación contra el vocabulario **real de GPT-2** se hizo con un espejo de GitHub verificado por SHA-256. Los umbrales de la rúbrica están calibrados con datos sintéticos.

## Lecturas
Gage 1994 · Sennrich et al. 2016 (arXiv:1508.07909) · Wang et al. 2019 (arXiv:1909.03341) · Radford et al. 2019 · Zouhar et al. 2023 (arXiv:2306.16837) · Kozma & Voderholzer 2024 (arXiv:2411.08671) · Schmidt et al. 2024 (arXiv:2402.18376) · Singh & Strouse 2024 (arXiv:2402.14903) · Karpathy, `minbpe`.

## Siguiente módulo
**03 · WordPiece, Unigram, SentencePiece, tiktoken y HF tokenizers.**
