# Lectura guiada de papers · Tokenización y embeddings

> Curso «Tokenización y Embeddings: de BPE a los modelos modernos» · material de cierre del módulo 19 · a **octubre de 2026**.
> Solo papers que existen: todos los identificadores arXiv de esta lista se comprobaron contra `arxiv.org/abs/<id>` (título coincidente) en oct-2026; la mayoría ya estaban verificados en las referencias de las lecciones 00–17. Las obras sin arXiv se citan por autor, año, título y lugar de publicación.

## Cómo usar esta lista
* **Prioridad:** ⭐⭐⭐ imprescindible (léelo entero) · ⭐⭐ recomendado (introducción, método y experimentos principales) · ⭐ ampliación (abstract, figuras y conclusiones).
* **Método de las tres pasadas** (Keshav 2007, *How to Read a Paper*, ACM SIGCOMM CCR): (1) 10 min: título, abstract, figuras, conclusiones → ¿qué afirma?; (2) 1 h: método y experimentos, sin las demostraciones → ¿qué evidencia lo respalda y contra qué baseline?; (3) varias horas: reprodúcelo mentalmente (o en el notebook del módulo) y busca supuestos ocultos.
* **Preguntas de lectura:** cada paper ⭐⭐⭐ trae preguntas. Respóndelas por escrito en 3–5 líneas; si no puedes, vuelve a la sección del paper indicada por la pregunta.
* **Etiquetas de madurez** del curso: 🟢 sólido · 🟡 emergente · 🔴 experimental, para recordar qué es práctica estándar y qué es investigación.
* **Ruta mínima (≈ 15 papers, ~20 h):** los marcados con ⭐⭐⭐.

---

## 00 · Intro y baseline
* ⭐⭐⭐ Thakur et al. (2021). *BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models*. arXiv:2104.08663. 🟢
  - ¿Por qué BM25 es tan difícil de batir fuera de dominio y qué tipo de modelos generalizan mejor según la tabla principal?
  - ¿Qué decisiones de construcción del benchmark (tareas, métricas, pooling) condicionan sus conclusiones?
* ⭐⭐ Robertson & Zaragoza (2009). *The Probabilistic Relevance Framework: BM25 and Beyond*. Foundations and Trends in IR. 🟢
* ⭐ Reimers & Gurevych (2019). *Sentence-BERT*. arXiv:1908.10084 (se lee a fondo en el módulo 10).

## 01 · Unicode y bytes
* ⭐⭐ Boucher & Anderson (2021). *Trojan Source: Invisible Vulnerabilities*. arXiv:2111.00169. 🟢
  - ¿Qué caracteres explotan y por qué la normalización NFC no los elimina?
* ⭐⭐ Mielke et al. (2021). *Between words and characters: A Brief History of Open-Vocabulary Modeling and Tokenization in NLP*. arXiv:2112.10508. 🟢 (el mejor mapa del terreno para todo el bloque A).
* ⭐ Unicode Standard Annex #15 (*Unicode Normalization Forms*) y #29 (*Text Segmentation*).

## 02 · BPE desde cero
* ⭐⭐⭐ Sennrich, Haddow, Birch (2016). *Neural Machine Translation of Rare Words with Subword Units*. arXiv:1508.07909. 🟢
  - ¿Qué problema de vocabulario abierto resuelve y qué hiperparámetro controla el trade-off longitud/vocabulario?
  - ¿Por qué el algoritmo original aprende merges dentro de palabras y no entre ellas?
* ⭐⭐ Wang, Cho, Gu (2019). *Neural Machine Translation with Byte-Level Subwords*. arXiv:1909.03341. 🟢
* ⭐⭐ Zouhar et al. (2023). *A Formal Perspective on Byte-Pair Encoding*. arXiv:2306.16837. 🟢 (BPE como aproximación voraz a un problema de compresión).
* ⭐ Kozma & Voderholzer (2024). *Theoretical Analysis of Byte-Pair Encoding*. arXiv:2411.08671.

## 03 · WordPiece, Unigram, SentencePiece
* ⭐⭐⭐ Kudo (2018). *Subword Regularization: Improving Neural Network Translation Models with Multiple Subword Candidates*. arXiv:1804.10959. 🟢
  - ¿Cómo se poda el vocabulario en Unigram y qué papel juega EM?
  - ¿Por qué muestrear segmentaciones regulariza y cuándo no ayuda?
* ⭐⭐ Kudo & Richardson (2018). *SentencePiece*. arXiv:1808.06226. 🟢
* ⭐⭐ Provilkov, Emelianenko, Voita (2020). *BPE-Dropout: Simple and Effective Subword Regularization*. arXiv:1910.13267. 🟢
* ⭐⭐ Schmidt et al. (2024). *Tokenization Is More Than Compression*. arXiv:2402.18376. 🟡
  - ¿Qué hipótesis («menos tokens = mejor modelo») ponen a prueba y qué encuentran?
* ⭐ Bostrom & Durrett (2020). *Byte Pair Encoding is Suboptimal for Language Model Pretraining*. arXiv:2004.03720.

## 04 · Diseño de tokenizers modernos
* ⭐⭐⭐ Petrov et al. (2023). *Language Model Tokenizers Introduce Unfairness Between Languages*. arXiv:2305.15425. 🟢
  - ¿Cómo miden la paridad y por qué necesitan texto paralelo?
  - ¿Qué consecuencias de costo y de contexto describen para los idiomas con peor paridad?
* ⭐⭐ Ahia et al. (2023). *Do All Languages Cost the Same? Tokenization in the Era of Commercial Language Models*. arXiv:2305.13707. 🟢
* ⭐⭐ Tao et al. (2024). *Scaling Laws with Vocabulary: Larger Models Deserve Larger Vocabularies*. arXiv:2407.13623. 🟡
* ⭐⭐ Liu et al. (2025). *SuperBPE: Space Travel for Language Models*. arXiv:2503.13423. 🟡
* ⭐ Dagan, Synnaeve, Rozière (2024). *Getting the most out of your tokenizer for pre-training and domain adaptation*. arXiv:2402.01035.

## 05 · Patologías y robustez
* ⭐⭐⭐ Land & Bartolo (2024). *Fishing for Magikarp: Automatically Detecting Under-trained Tokens in Large Language Models*. arXiv:2405.05417. 🟢
  - ¿Qué señal de la matriz de embeddings usan como detector y por qué funciona?
  - ¿Cómo verifican que un token candidato es realmente problemático?
* ⭐⭐ Singh & Strouse (2024). *Tokenization counts: the impact of tokenization on arithmetic in frontier LLMs*. arXiv:2402.14903. 🟡
* ⭐ Rumbelow & Watkins (2023). *SolidGoldMagikarp (plus, prompt generation)*. LessWrong (el post que popularizó los «glitch tokens»).
* ⭐ Li et al. (2024). *Glitch Tokens in Large Language Models: Categorization Taxonomy and Effective Detection*. arXiv:2404.09894.
* ⭐ Chai et al. (2024). *Tokenization Falling Short: On Subword Robustness in Large Language Models*. arXiv:2406.11687.

## 06 · Tokenizer-free I: bytes y patches
* ⭐⭐⭐ Pagnoni et al. (2024). *Byte Latent Transformer: Patches Scale Better Than Tokens*. arXiv:2412.09871. 🟡/🔴
  - ¿Cómo se decide el límite de un patch y qué modelo estima la entropía?
  - ¿Con qué presupuesto de FLOPs comparan contra un modelo con tokenizer y dónde gana/pierde?
* ⭐⭐ Yu et al. (2023). *MEGABYTE: Predicting Million-byte Sequences with Multiscale Transformers*. arXiv:2305.07185. 🔴
* ⭐⭐ Xue et al. (2022). *ByT5: Towards a token-free future with pre-trained byte-to-byte models*. arXiv:2105.13626. 🟡
* ⭐ Clark et al. (2022). *CANINE*. arXiv:2103.06874 · Slagle (2024). *SpaceByte*. arXiv:2404.14408 · Wang et al. (2024). *MambaByte*. arXiv:2401.13660.

## 07 · H-Net y tokenizer transfer
* ⭐⭐⭐ Hwang, Wang, Gu (2025). *Dynamic Chunking for End-to-End Hierarchical Sequence Modeling* (H-Net). arXiv:2507.07955. 🔴
  - ¿Cómo hace diferenciable la decisión de cortar (routing, smoothing) y qué controla la tasa de compresión?
  - ¿Qué evidencia aportan para afirmar que el chunking aprendido supera al BPE y en qué escala?
* ⭐⭐ Minixhofer, Ponti, Vulić (2024). *Zero-Shot Tokenizer Transfer*. arXiv:2405.07883. 🟡
* ⭐⭐ Dobler & de Melo (2023). *FOCUS*. arXiv:2305.14481 · Minixhofer, Paischer, Rekabsaz (2022). *WECHSEL*. arXiv:2112.06598. 🟡
* ⭐ Remy et al. (2024). *Trans-Tokenization and Cross-lingual Vocabulary Transfers*. arXiv:2408.04303.

## 08 · Tokens multimodales y de audio
* ⭐⭐⭐ van den Oord, Vinyals, Kavukcuoglu (2017). *Neural Discrete Representation Learning* (VQ-VAE). arXiv:1711.00937. 🟢
  - ¿Por qué hace falta el *straight-through estimator* y qué hacen los términos de *commitment* y de codebook?
* ⭐⭐ Mentzer et al. (2023). *Finite Scalar Quantization: VQ-VAE Made Simple*. arXiv:2309.15505. 🟢
* ⭐⭐ Zeghidour et al. (2021). *SoundStream*. arXiv:2107.03312 · Défossez et al. (2022). *High Fidelity Neural Audio Compression* (EnCodec). arXiv:2210.13438. 🟢
* ⭐ Esser et al. (2020). *Taming Transformers* (VQGAN). arXiv:2012.09841 · Chameleon Team (2024). arXiv:2405.09818 · Défossez et al. (2024). *Moshi*. arXiv:2410.00037.

## 09 · La capa de embedding en LLMs
* ⭐⭐⭐ Press & Wolf (2017). *Using the Output Embedding to Improve Language Models*. arXiv:1608.05859. 🟢
  - ¿Qué argumentos dan para atar entrada y salida y qué medición lo respalda?
* ⭐⭐ Yang et al. (2018). *Breaking the Softmax Bottleneck*. arXiv:1711.03953. 🟢
* ⭐⭐ Gao et al. (2019). *Representation Degeneration Problem in Training Natural Language Generation Models*. arXiv:1907.12009. 🟢
* ⭐ Godey, de la Clergerie, Sagot (2024). *Why do small language models underperform?* arXiv:2404.07647 · Inan et al. (2016). arXiv:1611.01462.

## 10 · Embeddings contextuales y de oraciones
* ⭐⭐⭐ Reimers & Gurevych (2019). *Sentence-BERT*. arXiv:1908.10084. 🟢
  - ¿Por qué BERT «crudo» con CLS o media da malos embeddings de oración y qué cambia el entrenamiento siamés?
* ⭐⭐ Devlin et al. (2019). *BERT*. arXiv:1810.04805. 🟢
* ⭐⭐ Ethayarajh (2019). *How Contextual are Contextualized Word Representations?* arXiv:1909.00512. 🟢
* ⭐ Su et al. (2021). *Whitening Sentence Representations*. arXiv:2103.15316 · Li et al. (2020). *On the Sentence Embeddings from Pre-trained Language Models* (BERT-flow). arXiv:2011.05864.

## 11 · Aprendizaje contrastivo
* ⭐⭐⭐ van den Oord, Li, Vinyals (2018). *Representation Learning with Contrastive Predictive Coding* (InfoNCE). arXiv:1807.03748. 🟢
  - Deriva la cota $I \ge \log K - \mathcal{L}$: ¿de qué depende que sea ajustada?
* ⭐⭐⭐ Wang & Isola (2020). *Understanding Contrastive Representation Learning through Alignment and Uniformity on the Hypersphere*. arXiv:2005.10242. 🟢
  - ¿Cómo se definen alineación y uniformidad y por qué la temperatura las equilibra?
* ⭐⭐ Karpukhin et al. (2020). *Dense Passage Retrieval*. arXiv:2004.04906 · Gao, Yao, Chen (2021). *SimCSE*. arXiv:2104.08821. 🟢
* ⭐⭐ Wang et al. (2022). *Text Embeddings by Weakly-Supervised Contrastive Pre-training* (E5). arXiv:2212.03533. 🟢
* ⭐⭐ Moreira et al. (2024). *NV-Retriever: Improving text embedding models with effective hard-negative mining*. arXiv:2407.15831. 🟡
* ⭐ Poole et al. (2019). *On Variational Bounds of Mutual Information*. arXiv:1905.06922 · Gao et al. (2021). *Gradient Cache*. arXiv:2101.06983.

## 12 · Embedders modernos
* ⭐⭐⭐ Kusupati et al. (2022). *Matryoshka Representation Learning*. arXiv:2205.13147. 🟢
  - ¿Qué pérdida optimizan exactamente y cuánto cuesta en entrenamiento frente a un modelo de una sola dimensión?
* ⭐⭐⭐ Muennighoff et al. (2022). *MTEB*. arXiv:2210.07316 · Enevoldsen et al. (2025). *MMTEB*. arXiv:2502.13595. 🟢
  - ¿Qué tareas agrega la media y por qué no predice el rendimiento en tu dominio?
* ⭐⭐ BehnamGhader et al. (2024). *LLM2Vec*. arXiv:2404.05961 · Lee et al. (2024). *NV-Embed*. arXiv:2405.17428. 🟡
* ⭐⭐ Wang et al. (2024). *Multilingual E5 Text Embeddings*. arXiv:2402.05672 · Chen et al. (2024). *M3-Embedding* (BGE-M3). arXiv:2402.03216. 🟢
* ⭐ Zhang et al. (2025). *Qwen3 Embedding*. arXiv:2506.05176 · Vera et al. (2025). *EmbeddingGemma*. arXiv:2509.20354 · Lee et al. (2025). *Gemini Embedding*. arXiv:2503.07891. 🟡 (verifica versiones vigentes).

## 13 · Dense, sparse y late interaction
* ⭐⭐⭐ Khattab & Zaharia (2020). *ColBERT*. arXiv:2004.12832. 🟢
  - ¿Por qué MaxSim permite precalcular los documentos y cuánto cuesta almacenarlos?
* ⭐⭐ Santhanam et al. (2021). *ColBERTv2*. arXiv:2112.01488 · Santhanam et al. (2022). *PLAID*. arXiv:2205.09707. 🟢
* ⭐⭐ Formal et al. (2021). *SPLADE*. arXiv:2107.05720 · Lassance et al. (2024). *SPLADE-v3*. arXiv:2403.06789. 🟢
* ⭐⭐ Dhulipala et al. (2024). *MUVERA: Multi-Vector Retrieval via Fixed Dimensional Encodings*. arXiv:2405.19504. 🟡
* ⭐⭐ Bruch, Gai, Ingber (2022). *An Analysis of Fusion Functions for Hybrid Retrieval*. arXiv:2210.11934 · Cormack, Clarke, Büttcher (2009). *Reciprocal Rank Fusion…* SIGIR. 🟢
* ⭐ Nogueira & Cho (2019). *Passage Re-ranking with BERT*. arXiv:1901.04085 · Günther et al. (2024). *Late Chunking*. arXiv:2409.04701.

## 14 · Indexación y ANN
* ⭐⭐⭐ Malkov & Yashunin (2016). *Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs*. arXiv:1603.09320. 🟢
  - ¿Para qué sirven las capas superiores y qué hace la heurística de selección de vecinos?
* ⭐⭐⭐ Douze et al. (2024). *The Faiss library*. arXiv:2401.08281. 🟢
  - ¿Cómo organizan el espacio de diseño (compresión × estructura de índice) y qué métricas recomiendan para compararlos?
* ⭐⭐ Jégou, Douze, Schmid (2011). *Product Quantization for Nearest Neighbor Search*. IEEE TPAMI. 🟢
* ⭐⭐ Subramanya et al. (2019). *DiskANN*. NeurIPS · Singh et al. (2021). *FreshDiskANN*. arXiv:2105.09613. 🟢
* ⭐⭐ Gao & Long (2024). *RaBitQ*. arXiv:2405.12497. 🟡 · Guo et al. (2020). *Accelerating Large-Scale Inference with Anisotropic Vector Quantization* (ScaNN). arXiv:1908.10396. 🟢
* ⭐ Patel et al. (2024). *ACORN*. arXiv:2403.04871 · Aumüller et al. (2018). *ANN-Benchmarks*. arXiv:1807.05614.

## 15 · Evaluación de retrieval
* ⭐⭐⭐ Weller, Boratko, Naim, Lee (2025). *On the Theoretical Limitations of Embedding-Based Retrieval*. arXiv:2508.21038. 🟡
  - ¿Qué cantidad (rango de signo) acota lo que un embedding de dimensión $d$ puede representar y cómo construyen LIMIT?
  - ¿Qué familias de modelos resisten mejor y por qué?
* ⭐⭐⭐ Smucker, Allan, Carterette (2007). *A Comparison of Statistical Significance Tests for Information Retrieval Evaluation*. CIKM. 🟢
  - ¿Qué tests recomiendan y por qué el test de signos es peor?
* ⭐⭐ Thomas et al. (2023). *Large language models can accurately predict searcher preferences*. arXiv:2309.10621 · Soboroff (2024). *Don't Use LLMs to Make Relevance Judgments*. arXiv:2409.15133. 🟡 (léelos juntos: son posturas opuestas).

## 16 · Embeddings multimodales
* ⭐⭐⭐ Radford et al. (2021). *Learning Transferable Visual Models From Natural Language Supervision* (CLIP). arXiv:2103.00020. 🟢
  - ¿Qué escala de datos y qué pérdida usan, y cómo evalúan zero-shot?
* ⭐⭐ Zhai et al. (2023). *Sigmoid Loss for Language Image Pre-Training* (SigLIP). arXiv:2303.15343 · Tschannen et al. (2025). *SigLIP 2*. arXiv:2502.14786. 🟢
* ⭐⭐ Liang et al. (2022). *Mind the Gap: Understanding the Modality Gap in Multi-modal Contrastive Representation Learning*. arXiv:2203.02053. 🟢
* ⭐⭐ Faysse et al. (2024). *ColPali: Efficient Document Retrieval with Vision Language Models*. arXiv:2407.01449. 🟡
* ⭐ ViDoRe Benchmark V2 (2025). arXiv:2505.17166 · ViDoRe V3 (2026). arXiv:2601.08620.

## 17 · Interpretabilidad y geometría
* ⭐⭐⭐ Hewitt & Liang (2019). *Designing and Interpreting Probes with Control Tasks*. arXiv:1909.03368. 🟢
  - ¿Qué es la selectividad y por qué una sonda con mucha capacidad engaña?
* ⭐⭐⭐ Morris et al. (2023). *Text Embeddings Reveal (Almost) As Much As Text* (vec2text). arXiv:2310.06816. 🟡
  - ¿Por qué la corrección iterativa reconstruye mucho mejor que un decodificador directo y qué defensas evalúan?
* ⭐⭐ Elhage et al. (2022). *Toy Models of Superposition*. arXiv:2209.10652 · Park, Choe, Veitch (2023). *The Linear Representation Hypothesis and the Geometry of Large Language Models*. arXiv:2311.03658. 🟡
* ⭐⭐ Gao et al. (2024). *Scaling and evaluating sparse autoencoders*. arXiv:2406.04093. 🟡
* ⭐ Paulo & Belrose (2025). *Sparse Autoencoders Trained on the Same Data Learn Different Features*. arXiv:2501.16615 · Wu et al. (2025). *AxBench*. arXiv:2501.17148. 🔴 (lectura crítica de los SAE).

## 18 · Producción
* ⭐⭐⭐ Dean & Barroso (2013). *The Tail at Scale*. Communications of the ACM 56(2). 🟢
  - ¿Por qué el fan-out amplifica la cola y qué técnicas proponen (hedged/tied requests)?
* ⭐⭐ Shen et al. (2020). *Towards Backward-Compatible Representation Learning*. CVPR. arXiv:2003.11942. 🟡
* ⭐⭐ Song & Raghunathan (2020). *Information Leakage in Embedding Models*. ACM CCS. arXiv:2004.00053. 🟡
* ⭐⭐ Chapelle, Joachims, Radlinski, Yue (2012). *Large-scale validation and analysis of interleaved search evaluation*. ACM TOIS 30(1). 🟢
* ⭐ Kohavi, Tang, Xu (2020). *Trustworthy Online Controlled Experiments*. Cambridge University Press · Sculley et al. (2015). *Hidden Technical Debt in Machine Learning Systems*. NeurIPS.

## 19 · Playbook de élite
* ⭐⭐ Liu et al. (2023). *Lost in the Middle: How Language Models Use Long Contexts*. arXiv:2307.03172. 🟢 (por qué el orden del contexto recuperado importa en RAG).
* ⭐⭐ Relee BEIR (00), Smucker et al. (15) y Bruch et al. (13) con una pregunta nueva: *¿qué decisión de producción cambiaría si sus conclusiones no se cumplieran en tu dominio?*

## 20 · Capstone
No hay lecturas nuevas: el capstone es el momento de **releer en tercera pasada** los tres papers que más afectan a tus decisiones (típicamente el de tu embedder del módulo 12, el de tu índice del 14 y uno de evaluación del 15) y escribir en el informe técnico qué supuesto de cada paper verificaste en Políglota y cuál no.

---

### Plantilla de ficha de lectura (copiar en tus notas)
```text
Paper: <autores, año, título, id>
Afirmación principal (1 frase):
Evidencia (tabla/figura clave, baseline, métrica, tamaño):
Supuestos que podrían no cumplirse en Políglota:
Qué reproduje (módulo/celda) y qué obtuve:
Madurez (🟢/🟡/🔴) y por qué:
Una pregunta que le haría a los autores:
```
