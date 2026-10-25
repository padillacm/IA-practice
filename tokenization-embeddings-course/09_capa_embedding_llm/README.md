# Módulo 09 · La capa de embedding en LLMs

**Nivel:** 🟡 Intermedio · **Duración:** ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) · **Cómputo:** CPU (0 unidades de Colab; GPT-2 small corre en CPU, T4 opcional)

| Archivo | Contenido |
|---|---|
| [`09_capa_embedding_llm.ipynb`](09_capa_embedding_llm.ipynb) | Lección: lookup = one-hot × E · anatomía E / W_U y coste en parámetros (GPT-2: 31 %) · weight tying atado vs desatado · derivación del gradiente del unembedding y colapso de filas huérfanas (medido) · weight decay en filas nunca vistas (medido vs predicho) · geometría de E: norma vs frecuencia, anisotropía, espectro y rango efectivo, vecinos, PCA · cuello de botella softmax (experimento) y cross-entropy por trozos · extensión de vocabulario con 4 inicializaciones medidas en bits por byte, fertilidad y masa filtrada · caja histórica word2vec/GloVe/PMI |
| [`09_proyecto_capa_embedding_llm.ipynb`](09_proyecto_capa_embedding_llm.ipynb) | Proyecto Políglota: auditoría de la capa de embedding (normas, frecuencias, colapso de filas no vistas) y extensión con 32 tokens de dominio inicializados por media de sub-tokens, con rúbrica automática |
| `assets/` | Imágenes de Gemini: `M09-IMG-01.png`, `M09-IMG-02.png`, `M09-IMG-03.png` |

## Objetivos
1. Explicar el lookup como producto one-hot y por qué solo las filas vistas reciben gradiente de entrada.
2. Cuantificar el peso de E/W_U y el ahorro del weight tying.
3. Derivar el gradiente del unembedding y predecir el colapso de los tokens que nunca son objetivo.
4. Medir la geometría de E (normas, frecuencia, anisotropía, espectro, vecinos).
5. Demostrar el cuello de botella softmax y el coste de la cabeza.
6. Extender el vocabulario y comparar inicializaciones con métricas correctas (bpb).

## Datasets y modelos
- Corpus Políglota canónico (`carga_corpus`, módulo 00): Wikipedia ES/EN + CodeSearchNet (o stdlib) → sintético si no hay red.
- GPT-2 small (`gpt2`, Hugging Face). **Fallback documentado:** mini-GPT-2 atado (2 capas, d = 64, BPE de 500 tokens) entrenado en el propio notebook.

## Estado de pruebas (entorno de autoría)
Hugging Face estaba **bloqueado** por el proxy: los dos notebooks se ejecutaron completos con el corpus **sintético** + stdlib y el **mini-GPT-2 de fallback** (CPU, ≈ 3.5 min la lección, ≈ 1.5 min el proyecto). Las celdas con GPT-2 real y configs de otros modelos **no** pudieron ejecutarse; están protegidas con `try/except`. Los umbrales de la rúbrica están calibrados con esa ejecución.

## Lecturas clave
Press & Wolf 2017 (arXiv:1608.05859) · Inan et al. 2016 (arXiv:1611.01462) · Yang et al. 2018 (arXiv:1711.03953) · Gao et al. 2019 (arXiv:1907.12009) · Godey et al. 2024 (arXiv:2404.07647) · Land & Bartolo 2024 (arXiv:2405.05417) · Hewitt 2021 (blog de inicialización de vocabulario).

## Conexión con Políglota
Fija cómo se representa cada token dentro de un modelo. El módulo 10 pasa de vectores por token a vectores por frase; el 11 entrena el embedder propio de Políglota.

Los notebooks se generan con `python tokenization-embeddings-course/_tools/builders/build_09.py` (desde la raíz del repo).
