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
