# Módulo 12 · LLMs y agentes en sistemas de recomendación

**Nivel:** 🔴 Experto · **Duración:** 7–9 h (lección) + 5–7 h (proyecto) · **GPU:** L4 recomendada (7–8B en bf16); T4 con 4-bit o modelos 1,5–3B; sin GPU funciona con la API de Claude/OpenAI o con el backend `mock`.
**Unidades de Colab estimadas:** ~15–25 (L4) en la lección, ~8–15 en el proyecto; ~0 en modo API/mock.

| Notebook | Contenido |
|---|---|
| [`12_llm_agents_recsys.ipynb`](12_llm_agents_recsys.ipynb) | Lección: LLM como encoder, ranker zero-shot listwise, LoRA estilo TALLRec, enriquecimiento y cold start, LLM-as-judge, explicaciones, agente LangGraph, simulación de usuarios, evaluación de agentes, costes |
| [`12_proyecto_agente_cinematch.ipynb`](12_proyecto_agente_cinematch.ipynb) | Proyecto: «Pregúntale a CineMatch», un agente conversacional con LangGraph, retriever de dos torres + FAISS y re-ranker LLM, evaluado con usuarios simulados |

## Objetivos
1. Usar LLMs como **encoders** de ítems y medir cuándo ganan a los embeddings de ID (cold start).
2. Construir un **re-ranker LLM listwise** robusto (parser anti-alucinación, *bootstrapping* contra el sesgo de posición) y evaluarlo con un protocolo realista.
3. Ajustar un LLM con **LoRA/QLoRA al estilo TALLRec** y compararlo con baselines clásicos (AUC).
4. **Enriquecer metadatos** offline (JSON validado, caché) y resolver **cold start** de ítems (mapeo texto → CF) y de usuarios (HyDE).
5. Montar un **LLM-as-judge** con protocolo de intercambio de posiciones y meta-evaluación.
6. Generar **explicaciones fundamentadas** y auditar alucinaciones automáticamente.
7. Diseñar un **agente recomendador con LangGraph**: estado tipado, herramientas de recsys, memoria corta (checkpointer) y larga (Store), *guardrails* de catálogo.
8. Evaluar agentes con **simuladores de usuario** (Agent4Rec, iEvaLM) y estimar **coste, latencia y alucinación** en producción.

## Backends de LLM
Todo usa una interfaz común `BaseLLM.generate()`:
- `hf`: 🤗 transformers (`Qwen/Qwen2.5-7B-Instruct` por defecto; también `Qwen/Qwen3-8B`, `meta-llama/Llama-3.1-8B-Instruct`), 4-bit NF4 automático si la GPU tiene < 20 GB.
- `vllm`: el mismo modelo con vLLM.
- `anthropic`: Claude vía API, por defecto `claude-sonnet-5-5` (`ANTHROPIC_API_KEY`, se lee de los *Secrets* de Colab).
- `openai`: `gpt-4o-mini` por defecto (`OPENAI_API_KEY`).
- `mock`: simulador sin GPU ni red para probar la tubería (**sus cifras no son resultados de LLM**).

`LLM_BACKEND="auto"` elige GPU → Anthropic → OpenAI → mock. Variables: `LLM_BACKEND`, `HF_MODEL`, `ANTHROPIC_MODEL`, `OPENAI_MODEL`, `EMB_MODEL`.

## Datasets y modelos
- **MovieLens latest-small** (GroupLens; `ml-1m` como alternativa). *Fallback* sintético con la misma forma si no hay red.
- Embeddings: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (multilingüe; alternativas `BAAI/bge-m3`, `Qwen/Qwen3-Embedding-0.6B`).
- LoRA: `Qwen/Qwen2.5-1.5B-Instruct` en `FAST_DEV_RUN`, `HF_MODEL` (7–8B, QLoRA) a escala completa.

## Utilidades de módulos anteriores
Cada notebook incluye, en versión mínima: carga de MovieLens y split temporal (módulo 01), `Recall/NDCG@K` (módulo 02) y retriever PureSVD + FAISS (módulo 08).

## Lecturas clave
- Hou et al. (2024). *LLMs are Zero-Shot Rankers for Recommender Systems*. [arXiv:2305.08845](https://arxiv.org/abs/2305.08845)
- Bao et al. (2023). *TALLRec*. [arXiv:2305.00447](https://arxiv.org/abs/2305.00447)
- Huang et al. (2023). *Recommender AI Agent (InteRecAgent)*. [arXiv:2308.16505](https://arxiv.org/abs/2308.16505)
- Zhang et al. (2024). *On Generative Agents in Recommendation (Agent4Rec)*. [arXiv:2310.10108](https://arxiv.org/abs/2310.10108)
- Wang et al. (2023). *Rethinking the Evaluation for Conversational Recommendation in the Era of LLMs (iEvaLM)*. [arXiv:2305.13112](https://arxiv.org/abs/2305.13112)
- Di Palma et al. (2025). *Do LLMs Memorize Recommendation Datasets?* [arXiv:2505.10212](https://arxiv.org/abs/2505.10212)
- Industria: Spotify + Llama (Meta AI, 2024), Netflix foundation model (2025) y GenRec (2026), YouTube PLUM ([arXiv:2510.07784](https://arxiv.org/abs/2510.07784)), LinkedIn 360Brew ([arXiv:2501.16450](https://arxiv.org/abs/2501.16450)).

## Conexión con CineMatch
El proyecto añade a CineMatch la superficie conversacional «Pregúntale a CineMatch», reutilizando el retriever (módulo 08) y preparando la integración en el capstone (módulo 18): las métricas de coste/latencia alimentan el módulo 16 y las trazas del agente, la monitorización del módulo 17.

## Regenerar los notebooks
```bash
python recsys-course/_tools/builders/build_12.py
```
