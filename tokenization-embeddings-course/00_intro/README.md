# Módulo 00 · Intro, entorno e hilo conductor

**Nivel:** 🟢 Básico · **Duración:** ≈ 2 h (lección ≈ 1 h + proyecto ≈ 1 h) · **Cómputo:** CPU (0 unidades de Colab)

| Archivo | Contenido |
|---|---|
| `00_intro.ipynb` | Lección: mapa del curso, token vs embedding (visión global), entorno Colab, celdas Gemini y `assets/`, corpus Políglota, métricas de retrieval, BM25 desde cero, experimentos de fallo, bootstrap |
| `00_proyecto_intro.ipynb` | Proyecto **Políglota v0**: estadísticas del corpus, métricas, BM25 con índice invertido, `split_ident`, evaluación por idioma con IC 95 %, análisis de errores, `poliglota_v0.json` |
| `assets/` | Carpeta (vacía, con `.gitkeep`) para las imágenes/videos de Gemini: `M00-IMG-01.png`, `M00-IMG-02.png`, `M00-IMG-03.png` |

## Objetivos
1. Describir el pipeline texto → bytes → tokens → ids → embeddings → índice → ranking y ubicar cada módulo del curso.
2. Distinguir token de embedding con ejemplos numéricos (lookup = one-hot × matriz).
3. Configurar el entorno (semilla 42, `device`, `FAST_DEV_RUN`) y reemplazar celdas Gemini.
4. Cargar el corpus Políglota con `carga_corpus()` y entender el contrato de datos.
5. Implementar nDCG@k, Recall@k y MRR@k con empates, duplicados y consultas sin relevantes bien tratados.
6. Construir y validar un baseline BM25 (contra `rank_bm25`) y medirlo con intervalo de confianza bootstrap.

## Contrato común del curso (lo que usan todos los módulos)
### `carga_corpus(fast_dev: bool = True) -> dict`
```python
{
  "docs":    [{"id": str, "lang": "es" | "en" | "code", "text": str}, ...],
  "queries": [{"qid": str, "lang": "es" | "en" | "code", "text": str}, ...],
  "qrels":   {qid: {doc_id: 1}},      # relevancia > 0 = relevante (hoy binaria)
  "source":  "real" | "synthetic",
}
```
* **Cadena de datos** (oficial → espejo → sintético; imprime qué fuente usó):
  Wikipedia ES/EN: HF `wikimedia/wikipedia` (`20231101.es` / `20231101.en`, streaming) → API pública de Wikipedia (introducciones de artículos aleatorios) → texto técnico **sintético** ES/EN (mismo esquema; `source="synthetic"` y aviso).
  Código: CodeSearchNet Python en HF (se prueban varios repos: `code-search-net/code_search_net`, `code_search_net`, `claudios/code_search_net`, `Nan-Do/code-search-net-python`) → funciones **reales** de la stdlib de Python con su docstring (offline).
* **Tamaños:** `fast_dev=True` → 150 artículos/idioma + 100 funciones, 110 consultas (40 ES, 40 EN, 30 código). `fast_dev=False` → 3 000 artículos/idioma (≤ 6 000 caracteres) + hasta 1 500 funciones, 550 consultas.
* **Mini golden set** de «ítem conocido»: Wikipedia → consulta = título del artículo (no está en `text`); código → consulta = primera frase del docstring, documento = función sin docstring. Sesgado a favor de métodos léxicos (ver 🧠 en la lección).
* **Sintético:** conceptos técnicos × aspectos × herramientas, con frases de ruido; los números absolutos no son comparables con los reales.

### Métricas canónicas
`ndcg_at_k(ranked_ids, rels, k=10)`, `recall_at_k(...)`, `mrr_at_k(...)`, `rank_from_scores(scores, doc_ids, k)` y `evaluate(run, qrels, k)`; `rels` es `dict doc_id → relevancia`.
Convenciones: ganancia **lineal** y descuento $1/\log_2(i+1)$ (como `trec_eval`/`pytrec_eval`, usados por BEIR y MTEB); **duplicados** en el ranking cuentan una vez; **sin relevantes → 0.0** y `evaluate` **excluye** esas consultas del promedio; **empates** de score → orden del corpus (determinista).

### Dónde vive el código canónico
Cada notebook es autocontenido (copia las celdas), pero la fuente única está en `_tools/builders/poliglota_utils.py` (+ `_tools/builders/poliglota_src/`). Un builder de otro módulo puede hacer:
```python
sys.path.insert(0, "tokenization-embeddings-course/_tools/builders")
from poliglota_utils import src_corpus_cells, SRC_METRICS, SRC_BM25
for src in src_corpus_cells(): nb.code(src)   # 3 celdas: datos sintéticos, generador, carga_corpus
nb.code(SRC_METRICS); nb.code(SRC_BM25)
```

## Datasets
Wikipedia ES/EN (`wikimedia/wikipedia`, CC BY-SA / GFDL), CodeSearchNet (Python), stdlib de Python (PSF). Sintético como último recurso.

## Estado de pruebas (entorno de autoría)
Hugging Face, Wikipedia, unicode.org y el CDN de OpenAI estaban **bloqueados** por el proxy del contenedor. Probado con datos **sintéticos** (+ stdlib real) y con *mocks* de `datasets`/`urllib` para las rutas oficial y espejo; la ruta con Wikipedia/CodeSearchNet reales **no pudo ejecutarse** aquí. Los umbrales de la rúbrica están calibrados con la solución sobre datos sintéticos.

## Lecturas
Thakur et al. 2021 (BEIR, arXiv:2104.08663) · Robertson & Zaragoza 2009 (BM25) · Reimers & Gurevych 2019 (SBERT, arXiv:1908.10084) · Petrov et al. 2023 (arXiv:2305.15425) · Ahia et al. 2023 (arXiv:2305.13707) · Anthropic 2024, «Introducing Contextual Retrieval».

## Siguiente módulo
**01 · Texto como bytes: Unicode, UTF-8, normalización** — code points vs bytes vs grafemas, UTF-8 a mano, NFC/NFKC, homoglifos y mojibake, con auditoría del corpus Políglota.
