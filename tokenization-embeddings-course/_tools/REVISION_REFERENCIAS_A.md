# Verificación de referencias · Bloque A (módulos 00–08)

Verificador de referencias A (26-oct-2026). Método: los 105 identificadores arXiv citados en 00–08 (builders, auxiliares
y README) se descargaron de `arxiv.org/abs/<id>` y se cruzaron automáticamente con el texto que los rodea (primer autor,
año, título); los enlaces no arXiv se comprobaron con WebFetch/WebSearch (unicode.org, rfc-editor.org, theregister.com y
GitHub no se pueden abrir directamente desde este entorno: se confirmaron por buscador o por la página espejo).
No se repite lo que ya contrastó la revisión técnica (`REVISION_TECNICA_A.md`: cifras de BLT, H-Net, ZeTT, SuperBPE,
Tao et al., Land & Bartolo, tasas de códecs, etc.).

Leyenda: ✅ verificada · ✏️ corregida · ❌ eliminada · ⚠️ fuente secundaria.

## 00 · Intro
| Referencia | Estado | Nota |
|---|---|---|
| Thakur et al. 2021, BEIR, arXiv:2104.08663 | ✏️ | Correcta; añadido venue (NeurIPS 2021 Datasets & Benchmarks) |
| Robertson & Zaragoza 2009, *The Probabilistic Relevance Framework: BM25 and Beyond*, FnTIR 3(4) | ✅ | |
| Reimers & Gurevych 2019, Sentence-BERT, arXiv:1908.10084 | ✏️ | Añadido venue (EMNLP-IJCNLP 2019) |
| Radford et al. 2019, GPT-2 (informe de OpenAI) | ✅ | |
| Wang, Cho & Gu 2019, byte-level subwords, arXiv:1909.03341 | ✅ | |
| Petrov et al. 2023, arXiv:2305.15425 | ✏️ | Añadido venue (NeurIPS 2023) |
| Ahia et al. 2023, arXiv:2305.13707 | ✏️ | Añadido venue (EMNLP 2023) |
| Khattab & Zaharia 2020 (ColBERT), Formal et al. 2021 (SPLADE) | ✏️ | Se citaban solo como «ColBERT.» / «SPLADE.»: título completo, autores y venue (SIGIR 2020 / SIGIR 2021 short) |
| Pagnoni et al. 2024, BLT, arXiv:2412.09871 | ✅ | |
| Anthropic, *Introducing Contextual Retrieval* | ✏️ | Fecha exacta (19-sep-2024) y cifra del post (−49 % de fallos en top-20, 5.7 % → 2.9 %) |
| `tiktoken`, `rank_bm25` (PyPI), `wikimedia/wikipedia` (HF) | ✅ | |
| Mapa de madurez (BM25 🟢, byte-level BPE 🟢, bi-encoders 🟢, híbrido 🟢 con Anthropic, SPLADE/ColBERT 🟡, BLT 🔴) | ✅ | Cada «quién la usa» tiene fuente citada |

## 01 · Unicode y bytes
| Referencia | Estado | Nota |
|---|---|---|
| UAX #15 *Unicode Normalization Forms* | ✏️ | Confirmada (rev. 57, Unicode 17.0, 30-jul-2025, ed. K. Whistler); URL oficial `https://www.unicode.org/reports/tr15/` |
| UAX #29 *Unicode Text Segmentation* | ✏️ | Título confirmado; URL oficial `www.unicode.org/reports/tr29/` (revisión no fijada: la URL apunta a la vigente) |
| UTS #39 *Unicode Security Mechanisms* | ✏️ | Título confirmado; URL oficial `www.unicode.org/reports/tr39/`; se menciona `confusables.txt` |
| RFC 3629 (Yergeau 2003) | ✏️ | Título exacto *UTF-8, a transformation format of ISO 10646*, STD 63, reemplaza RFC 2279. Se quitó el aviso «no pudieron abrirse» |
| Pike & Thompson, *Hello World or Καλημέρα κόσμε or こんにちは 世界*, USENIX Winter 1993 | ✏️ | Confirmado en usenix.org (añadida URL). En la sección 3 decía «Pike & Thompson, 1992»: el diseño es de 1992, la publicación de 1993; ahora lo distingue |
| The Register, 28-ago-2024 (Rehberger, ASCII smuggling) | ✏️ | El título no era «Microsoft Copilot «Copirate»»: es *From Copilot to Copirate* |
| Boucher & Anderson 2021, Trojan Source, arXiv:2111.00169 | ✅ | (USENIX Security 2023) |
| Xue et al. 2021, ByT5, arXiv:2105.13626 | ✅ | (TACL 2022) |
| Mielke et al. 2021, arXiv:2112.10508 | ✅ | |
| Wang et al. 2019, Petrov et al. 2023, Ahia et al. 2023, Pagnoni et al. 2024 | ✅ | |
| Shannon 1948, BSTJ | ✅ | |
| SentencePiece `doc/normalization.md` (default `nmt_nfkc`) | ✅ | Reglas `nmt_nfkc`, `nfkc`, `nmt_nfkc_cf`, `nfkc_cf`, `identity` confirmadas |
| PEP 393, PEP 3131, `ftfy` (PyPI) | ✅ | |
| Elasticsearch `asciifolding`, plugin ICU `icu_normalizer`/`icu_folding` (🏭) | ✅ | Documentación oficial de Elastic |
| Prompts Gemini (bytes de 👨‍👩‍👧‍👦 = 25, € = E2 82 AC, «pаypal» = 70 D0 B0 …) | ✅ | Recalculados con Python |
| Mapa de madurez | ✅ | Tag characters 🟡 respaldado por The Register; resto con norma o paper |

## 02 · BPE desde cero
| Referencia | Estado | Nota |
|---|---|---|
| Gage 1994, *A New Algorithm for Data Compression*, C Users Journal 12(2): 23–38 | ✅ | |
| Sennrich, Haddow & Birch 2016, ACL 2016, arXiv:1508.07909 | ✅ | |
| Wang, Cho & Gu 2019; Radford et al. 2019 (GPT-2) | ✅ | |
| Zouhar et al. 2023, arXiv:2306.16837 | ✏️ | Añadido venue: Findings of ACL 2023 (2023.findings-acl.38); cifras ≈ 0.37 y O(N log M) confirmadas en el abstract |
| Kozma & Voderholzer 2024, arXiv:2411.08671 | ✅ | Preprint |
| Schmidt et al. 2024, *Tokenization Is More Than Compression* | ✏️ | Añadido venue (EMNLP 2024); la afirmación de 🧠 3 coincide con el abstract |
| Bostrom & Durrett 2020 | ✏️ | Añadido venue (Findings of EMNLP 2020) |
| Singh & Strouse 2024, arXiv:2402.14903 | ✅ | Cifras ya corregidas por la revisión técnica |
| Petrov et al. 2023; Ahia et al. 2023 | ✏️ | Título completo de Ahia y venues (NeurIPS 2023 / EMNLP 2023) |
| Land & Bartolo 2024 | ✏️ | Añadido venue (EMNLP 2024) |
| Llama Team 2024, *The Llama 3 Herd of Models* | ✅ | Primer autor en arXiv: Grattafiori et al.; «Llama Team, AI @ Meta» es la autoría que da el propio informe |
| Provilkov et al. 2019, BPE-Dropout | ✏️ | Título completo y venue (ACL 2020) |
| Liu et al. 2025, SuperBPE | ✏️ | Añadido venue (COLM 2025) |
| Pagnoni et al. 2024, BLT; Shannon 1948 | ✏️/✅ | Título completo de BLT |
| `tiktoken` (incl. `_educational.py`), `minbpe`, HF `tokenizers`, `subword-nmt` | ✅ | Repositorios públicos existentes |
| 🏭 mapeo modelo → encoding de `tiktoken` 0.14.0 | ✅ | Verificado por la revisión técnica en el código instalado |
| Mapa de madurez | ✅ | Cada fila con fuente; SuperBPE 🟡 «8B en el artículo» confirmado |
