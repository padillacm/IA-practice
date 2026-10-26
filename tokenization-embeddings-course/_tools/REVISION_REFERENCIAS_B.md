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
