# Verificación de referencias · Bloque B (módulos 09–20 y extras)

Verificador de referencias B (26-oct-2026). Método: los **176 identificadores arXiv** citados en 09–20 (builders,
auxiliares `_a5_*`, `_a6_*`, `_a7_*`, `_b1x_*`) y en los extras se descargaron de `arxiv.org/abs/<id>` (metadatos
`citation_author`, `citation_date`, comentarios y *journal-ref*) y se cruzaron con el primer autor y el año del texto;
los venues se tomaron del comentario de arXiv cuando lo declara, de las actas (ICML/PMLR, ICLR, NeurIPS, ACL Anthology)
por buscador, o de lo ya confirmado en `REVISION_REFERENCIAS_A.md`. Si no hay venue confirmado se marca «preprint».
No se repite lo de `REVISION_TECNICA_B.md` (títulos de los 103 IDs de `LECTURA_PAPERS.md`; fechas de Gemini Embedding 2,
Voyage-4 y jina-v5; cifras de ColPali, LIMIT, precios del 18). Hugging Face, dblp y la API de arXiv están bloqueados por
el proxy: lo de HF se confirmó por buscador.

Leyenda: ✅ verificada · ✏️ corregida · ❌ eliminada · ⚠️ fuente secundaria.

## Extras
### `LECTURA_PAPERS.md`
| Referencia | Estado | Nota |
|---|---|---|
| 103 IDs arXiv: primer autor y año | ✅ | Todos casan con `citation_author`/`citation_date` (años de publicación ≠ arXiv declarados: Sennrich 2016, Press & Wolf 2017, Xue 2022) |
| Venues de ≈ 85 entradas | ✏️ | Añadidos (p. ej. BEIR NeurIPS 2021 D&B, Press & Wolf EACL 2017, Yang ICLR 2018, Gao ICLR 2019, Inan ICLR 2017, MRL NeurIPS 2022, MTEB EACL 2023, MMTEB ICLR 2025, NV-Embed ICLR 2025, LLM2Vec COLM 2024, BGE-M3 Findings ACL 2024, ColBERTv2 NAACL 2022, PLAID CIKM 2022, MUVERA NeurIPS 2024, Bruch TOIS 2023, HNSW TPAMI, RaBitQ/ACORN SIGMOD 2024, ScaNN ICML 2020, LIMIT ICLR 2026, Thomas SIGIR 2024, Soboroff IRR 2025, SigLIP ICCV 2023, ColPali ICLR 2025, Gao et al. SAE ICLR 2025 (oral), AxBench ICML 2025 (PMLR 267), Park ICML 2024, Lost in the Middle TACL 2024) |
| Títulos abreviados («*Sentence-BERT*», «*BERT*», «*ColBERT*», «*SPLADE*», «*MTEB*», «*DPR*», «*SimCSE*», «*Gradient Cache*», «*CANINE*», «*SpaceByte*», «*MambaByte*», «*FOCUS*», «*WECHSEL*», «*ACORN*», «*RaBitQ*», «*DiskANN*», «Chameleon», «*Moshi*», «*SigLIP 2*», «*AxBench*»…) | ✏️ | Título completo; Inan et al. se citaba sin título |
| «ViDoRe Benchmark V2 / V3» sin autores | ✏️ | Macé et al. 2025 / Loison et al. 2026 (primer autor de arXiv) |
| Godey et al. 2024 | ✏️ | Título completo; sin venue confirmado (la v1 dice *under review*) → sin venue |
| Preprints sin venue (Mielke, Kozma, Singh & Strouse, E5, NV-Retriever, CPC, Faiss, FreshDiskANN, Late Chunking, SPLADE-v3, whitening, Paulo & Belrose, SigLIP 2) | ✏️ | Marcados «Preprint»/«Informe técnico» |
| Elhage et al. 2022 | ✏️ | Añadido «Transformer Circuits Thread (Anthropic)» |
| Obras sin arXiv (Robertson & Zaragoza FnTIR 3(4), Jégou TPAMI 2011, Cormack SIGIR 2009, Smucker CIKM 2007, Dean & Barroso CACM 56(2), Chapelle TOIS 30(1), Kohavi CUP 2020, Sculley NeurIPS 2015, Keshav CCR 2007) | ✅ | Título completo de RRF añadido |

### `GUIA_ENTREVISTAS.md`
| Referencia | Estado | Nota |
|---|---|---|
| 30 referencias de la lista final | ✏️ | Venues añadidos (mismos que arriba); Singh & Strouse, Oord y NV-Retriever como preprint |
| Shakir, Aarsen, Lee 2024 (blog de HF) | ✏️ | Título completo *Binary and Scalar Embedding Quantization for Significantly Faster & Cheaper Retrieval* (mar-2024) |
| Rumbelow & Watkins 2023 (LessWrong) | ✅ | Ya verificado en el bloque A (feb-2023) |
| Precio `text-embedding-3-small` 0.02 $/1M (preguntas 41 y 48: 80 $, 240 $) | ✅ | Coincide con la revisión técnica del 18; aritmética recalculada |
| Autores/años citados en las respuestas (Kudo 2018, Petrov 2023, … Dean & Barroso 2013) | ✅ | Coinciden con arXiv |

## 09 · Capa de embedding en LLMs
| Referencia | Estado | Nota |
|---|---|---|
| 15 IDs arXiv (Press & Wolf, Inan, Yang, Gao, Godey, Kobayashi, Land & Bartolo, Chung, He, Gemma ×2, Hsu, Takase, Mikolov ×2) | ✅ | Primer autor y año coinciden |
| Venues | ✏️ | Añadidos/completados: EACL 2017, ICLR 2017 (Inan), ICLR 2018/2019/2021, Findings ACL 2023 (Kobayashi), EMNLP 2024 (Land & Bartolo), ICLR 2023 (DeBERTaV3), COLM 2025 (*Spike No More*, según arXiv), ICLR 2013 workshop / NeurIPS 2013 (word2vec), EMNLP 2014, NeurIPS 2014; Godey y Liger Kernel como preprint |
| Godey et al. 2024 | ✏️ | Título abreviado «LM Saturation» → *Studying Language Model Saturation via the Softmax Bottleneck*; «< ~1000 dimensiones» coincide con el abstract |
| Gemma 1 «share embeddings across our inputs and outputs»; Gemma 2 «Tied embedding» | ✅ | Comprobado en el PDF/HTML de arXiv |
| nanoGPT `vocab_size = 50304` «padded up to nearest multiple of 64 for efficiency» | ✅ | `model.py` en GitHub (línea 111) |
| Hewitt 2021 (blog), Liger Kernel (GitHub), `resize_token_embeddings` | ✅ | Ya verificados en el bloque A / revisión técnica |
| Mapa de madurez / 🏭 / 🧠 | ✅ | Cada «quién la usa» con fuente (GPT-2, Gemma 1/2, RemBERT, DeBERTaV3, Liger, Cohere) |
| Prompts Gemini (ids «[1212, 8745, …]», piezas de «serialización») | ⚠️ | Ilustrativos: el vocabulario de GPT-2 no se puede descargar desde aquí; el texto no los presenta como ids reales |

## 10 · Embeddings contextuales y de oraciones
| Referencia | Estado | Nota |
|---|---|---|
| 15 IDs arXiv (Devlin, Reimers ×2, Ethayarajh, Li, Su ×2, Mu, Timkey, Godey, Libovický, Wang, Muennighoff, Karpukhin, Steck) | ✅ | Autor y año coinciden |
| Mu & Viswanath 2018 (texto, comentario y Mapa de madurez) | ✏️ | Faltaba la coautora: Mu, Bhat & Viswanath (ICLR 2018) |
| Venues | ✏️ | NAACL 2019, EMNLP-IJCNLP 2019 ×2, EMNLP 2020 ×3 (Reimers 2020, BERT-flow, DPR), EMNLP 2021 (Timkey), EACL 2024 (Godey), Findings ACL 2023 (INSTRUCTOR), WWW 2024 Companion (Steck); whitening, Libovický, E5 y SGPT como preprint |
| Cifras de SBERT (54.81 / 29.19 / 61.32) | ✅ | Ya contrastadas por la revisión técnica |
| Mapa de madurez («quién la usa»: SBERT, E5 *average pooling*, DPR `[CLS]`, SGPT, INSTRUCTOR, `paraphrase-multilingual-*`) | ✅ | Todos descritos así en sus papers/model cards |
| `sentence-transformers` (PyPI, `Transformer`/`Pooling`) | ✅ | |
| Prompts Gemini | ✅ | Sin datos técnicos verificables más allá de fórmulas ya revisadas |

## 11 · Aprendizaje contrastivo
| Referencia | Estado | Nota |
|---|---|---|
| 22 IDs arXiv (Oord, Poole, McAllester & Stratos, Tschannen, Wang & Isola, Wang & Liu, SimCLR, Henderson, SimCSE, DPR, ANCE, RocketQA, TAS-B, NV-Retriever, Robinson, Gradient Cache, E5, GTE, C-Pack, Nomic Embed, Qwen3 Embedding, LoRA) | ✅ | Autor y año coinciden |
| *RocketQA.* | ✏️ | Título completo (*An Optimized Training Approach to Dense Passage Retrieval for Open-Domain Question Answering*), NAACL 2021 |
| Venues | ✏️ | Años añadidos a los que solo decían «ICML/ICLR/EMNLP/CVPR»; ANCE ICLR 2021, TAS-B SIGIR 2021, Gradient Cache RepL4NLP 2021, C-Pack SIGIR 2024, Nomic Embed TMLR, SimCLR ICML 2020, LoRA ICLR 2022 (según arXiv/actas); CPC, Henderson, NV-Retriever, E5, GTE y Qwen3 Embedding como preprint |
| Cifras (CCPairs ≈ 270M, TopK-PercPos 95 %, τ 0.05/0.01, `scale=20`) | ✅ | Ya contrastadas por la revisión técnica |
| `sentence-transformers` (`MultipleNegativesRankingLoss`, `CachedMultipleNegativesRankingLoss`, `BatchSamplers.NO_DUPLICATES`, `mine_hard_negatives`, `add_adapter`) | ✅ | API pública de la librería (v3+) |
| Mapa de madurez / 🏭 | ✅ | Cada «quién la usa» con su informe técnico (E5, GTE, BGE, Nomic, Qwen3, DPR, ANCE, RocketQA, NV-Retriever) |

## 12 · Embedders modernos
| Referencia | Estado | Nota |
|---|---|---|
| 20 IDs arXiv (Kusupati, mE5, e5-mistral, BGE-M3, mGTE, Nomic ×2, NV-Embed, LLM2Vec, Qwen3, Gemini Embedding, EmbeddingGemma, jina v3/v4, MTEB, MMTEB, LIMIT, ModernBERT) | ✅ | Autor y año coinciden |
| Venues | ✏️ | NeurIPS 2022 (MRL), ACL 2024 (e5-mistral), Findings ACL 2024 (BGE-M3), EMNLP 2024 Industry (mGTE), TMLR (Nomic), ICLR 2025 (NV-Embed, MMTEB), COLM 2024 (LLM2Vec), EACL 2023 (MTEB), ICLR 2026 (LIMIT) |
| ModernBERT «*A Modern Bidirectional Encoder…*» | ✏️ | Título completo |
| **jina-embeddings-v5-text-nano: contexto** | ✏️ | **Resuelto: 8k (8192).** Lo dan el anuncio de Jina (tabla: small 32 768, nano 8192), el blog y la documentación de Elastic y la página de v5-omni-nano; solo la página de modelo de nano dice 32K (errata probable). Fecha precisada (18-feb-2026); licencia CC-BY-NC-4.0 y 677 M confirmados por la página de Jina. Añadida la referencia del anuncio |
| «Omitir la instrucción cuesta 1–5 %» (🧠 2), atribuido a «la tarjeta de Qwen3-Embedding, citada en un export ONNX de Qdrant» | ✏️ | Fuente primaria encontrada: README de `QwenLM/Qwen3-Embedding` («typically yields an improvement of 1% to 5%»); también confirma 32K, MRL y 1024/2560/4096. Añadido a referencias |
| *Introducing MTEB v2* (blog de HF) | ✏️ | Título completo y autores (Solomatin, Enevoldsen, Chung; 20-oct-2025) |
| Cohere *Announcing Embed Multimodal v4* (256/512/1024/1536, 128k, imagen+texto) | ✅ | URL del changelog confirmada por buscador |
| Shakir, Aarsen, Lee 2024 (HF), docs de `sentence-transformers`, OpenAI (25-ene-2024), Gemini Embedding 2 (preview/GA), EmbeddingGemma (< 200 MB), MongoDB/Voyage-4 | ✅ | Confirmados por la revisión técnica o por buscador (los dominios no abren desde el proxy) |
| Mapa de madurez / 🏭 | ✅ | Cada «quién la usa» con paper, tarjeta o documentación del proveedor |

## 13 · Dense, sparse y late interaction
| Referencia | Estado | Nota |
|---|---|---|
| 17 IDs arXiv (ColBERT, ColBERTv2, PLAID, WARP, MUVERA, SPLADE ×3, SPLADE-v3, Geng, BGE-M3, Jina-ColBERT-v2, Late Chunking, Nogueira & Cho, Bruch, BEIR, Qwen3) | ✅ | Autor y año coinciden |
| «*SPLADE*», «*SPLADE v2*», «*From Distillation to Hard Negative Sampling…*», «*M3-Embedding (BGE-M3)*», «*BEIR*» | ✏️ | Títulos completos (y autores de SPLADE v2, que faltaban) |
| Venues | ✏️ | SIGIR 2020 (ColBERT), NAACL 2022, CIKM 2022 (PLAID), SIGIR 2025 (WARP), NeurIPS 2024 (MUVERA), SIGIR 2021/2022 short (SPLADE), Findings ACL 2024, TOIS 2023 (Bruch), NeurIPS 2021 D&B (BEIR), FnTIR 3(4); preprints marcados |
| MUVERA «2–5× menos candidatos … (no verificado aquí)» (🧠 6) | ✏️ | Confirmado en el abstract; quitado el aviso |
| Jina-ColBERT-v2 «89 idiomas, 8192 tokens, consultas de 32, 128/96/64» (🏭) | ✏️ / ⚠️ | 8192 (preentrenamiento) y cabezas MRL 64/96/128 confirmados en el PDF; «89 idiomas» y «consultas de 32» solo en el anuncio de Jina (no abre desde aquí): atribuidos a él |
| Vespa: ColBERT embedder con compresión asimétrica de hasta 32× y Long-Context ColBERT | ✅ | Blog de Vespa (por buscador) |
| Weaviate MUVERA (v1.31) y recomendación para modelos tipo ColPali | ✅ | Blog y documentación de Weaviate (por buscador) |
| Qdrant multivector `MAX_SIM` + `m=0`; Elastic ELSER / `semantic_text`; OpenSearch neural sparse; bge-reranker-v2-m3 | ✅ | Documentación oficial |
| Mapa de madurez | ✅ | Cada «quién la usa» con documentación del motor o paper |

## 14 · Indexación ANN
| Referencia | Estado | Nota |
|---|---|---|
| 8 IDs arXiv (HNSW, ScaNN, RaBitQ, Extended RaBitQ, Faiss, ANN-Benchmarks, ACORN, FreshDiskANN) | ✅ | Autor y año coinciden |
| Venues | ✏️ | HNSW IEEE TPAMI 42(4) 2020, ScaNN ICML 2020, RaBitQ y ACORN SIGMOD 2024, ANN-Benchmarks Information Systems 87 (2020), Jégou TPAMI 33(1), OPQ CVPR 2013, DiskANN NeurIPS 2019; Extended RaBitQ, Faiss y FreshDiskANN como preprint |
| Milvus, *Bring Vector Compression to the Extreme…* | ✏️ | Existe (RaBitQ desde Milvus 2.6, ≈ 3× QPS); añadida la URL |
| Elastic BBQ (Elasticsearch 8.16, ≈ 95 % menos memoria) | ✅ | Elastic Search Labs (por buscador; el dominio no abre desde el proxy) |
| FAISS, DiskANN, ScaNN (repositorios) | ✅ | README presentes en GitHub (raw) |
| pgvector (HNSW e IVFFlat), Lucene/Elasticsearch/OpenSearch, Qdrant, Weaviate con HNSW | ✅ | Documentación oficial |
| Enlace al curso de recsys (`recsys-course/08_deep_retrieval_ann`) | ✅ | Existe en el repositorio |
| Mapa de madurez | ✅ | «Quién la usa» respaldado (FAISS, Google ScaNN, Microsoft DiskANN, Elastic BBQ, Milvus ≥ 2.6) |

## 15 · Evaluación de retrieval
| Referencia | Estado | Nota |
|---|---|---|
| 20 IDs arXiv (BEIR, MIRACL, MTEB, MMTEB, SciFact, Wang et al. 2013, MS MARCO, Arabzadeh, Urbano, Thomas, Faggioli, Soboroff, Clarke & Dietz, Alaofi, Zheng, LIMIT, Reimers 2021, e5-mistral…) | ✅ | Autor y año coinciden |
| RTEB: blog de HF (beta oct-2025) y póster NeurIPS 2026 (`neurips.cc/virtual/2026/poster/139103`, Verma, Liu et al.) | ✅ | Ambos existen (por buscador): 48 datasets, 28 privados |
| e5-mistral «sección de análisis de contaminación» | ✅ | El PDF tiene la sección *Test Set Contamination Analysis* (nombrada); venue ACL 2024 |
| Alaofi et al. | ✏️ | Título completo con el paréntesis «(best café near me; …)»; SIGIR-AP 2024 confirmado en arXiv |
| Venues | ✏️ | Años añadidos (NeurIPS 2021 D&B, ICLR 2025, EMNLP 2020, COLT 2013, ECIR 2022, KDD 2020, CIKM 2007, SIGIR 2006/2019, NeurIPS 2023 D&B, ACL 2021); nuevos: MIRACL TACL 11 (2023), MTEB EACL 2023, MS MARCO SIGIR 2021, Arabzadeh *Information Retrieval Journal* 25 (2022), Thomas SIGIR 2024, Faggioli ICTIR 2023, Soboroff IRR 2025; Clarke & Dietz preprint |
| Smucker et al. 2007 (DOI 10.1145/1321440.1321528), Sakai 2006 (DOI 10.1145/1148170.1148261), ranx (GitHub) | ✅ | |
| Enlace a `recsys-course/02_evaluation` | ✅ | Existe en el repositorio |
| Mapa de madurez | ✅ | MTEB usa nDCG@10 en retrieval; LIMIT con autores de Google DeepMind/JHU; RTEB beta oct-2025 |
