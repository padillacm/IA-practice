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
