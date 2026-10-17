# Módulo 01 · El agente base: SupportOps v0

🟢 Básico · ≈ 4 h 20 min · **No necesita servicios de Compose** (todo simulado; funciona en Colab).

## Qué aprenderás
- Qué es un agente (bucle LLM + herramientas) frente a una llamada simple y a un workflow; el bucle escrito a mano en ≈ 25 líneas.
- **SupportOps v0**: el agente de soporte del curso (`supportops/`), sin instrumentar, con reintentos, herramientas simuladas y RAG (TF-IDF).
- Proveedor LLM agnóstico: `LLM_PROVIDER=mock|anthropic|openai|ollama` (el `mock` determinista es el valor por defecto y el de las rúbricas).
- Tokens y coste de un agente: por qué el contexto crece y el coste se dispara con los pasos.
- **Tráfico sintético** reproducible (semilla, esquema, ventanas de incidente) y **siete fallos inyectados** (latencia, errores del proveedor, errores y timeouts de herramientas, alucinación, bucle de herramientas, fuga de PII).
- Los **puntos de extensión** donde se instrumentará el agente (módulo 03) y un `RecordingInstrumentor` para ver el modelo de datos.

## Archivos
| Archivo | Contenido |
|---|---|
| `01_agente_base.ipynb` | Lección (teoría + código + 12 gráficos + autoevaluación) |
| `01_proyecto_agente_base.ipynb` | Proyecto: añadir la herramienta `check_stock` sin regresiones, definir la «huella» de 3 fallos y construir un detector ciego |

## Servicios necesarios
Ninguno. (`pip install -e agent-observability-course[viz]` lo hace el primer bloque de cada notebook.)

## Variables de entorno (opcionales)
`LLM_PROVIDER`, `LLM_MODEL`, `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `OLLAMA_HOST`, `SUPPORTOPS_SEED` (ver `_tools/INTERFACES.md`). **Nunca** pongas claves en un notebook.

## Lecturas
- Anthropic, *Building effective agents* — <https://www.anthropic.com/engineering/building-effective-agents>
- Yao et al., *ReAct* — <https://arxiv.org/abs/2210.03629> · Lewis et al., *RAG* — <https://arxiv.org/abs/2005.11401>
- Anthropic, *Tool use with Claude* — <https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview>

## Siguiente
`02_tres_pilares`: traces, metrics y logs, el modelo de datos de OpenTelemetry y las *golden signals* aplicadas a agentes.
