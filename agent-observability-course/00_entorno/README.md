# Módulo 00 · Entorno: por qué los agentes rompen el monitoreo y cómo levantar el stack

🟢 Básico · ≈ 4 h · Servicios: perfil `core` (+ `metrics`) para la parte práctica; el resto funciona en modo degradado.

## Qué aprenderás
- Por qué un agente LLM rompe cuatro supuestos del monitoreo clásico (determinismo, longitud de la cadena, coste por petición, significado de «éxito»), **medido** con tráfico sintético de SupportOps.
- El mapa del stack: app (SDK OpenTelemetry) → Collector → Tempo / Loki / Prometheus → Grafana (+ Pyroscope).
- Docker y Compose desde cero: imagen, contenedor, volumen, red, puertos y **perfiles**; leer un `docker-compose.yml` línea a línea.
- Levantar el stack, comprobar que está **listo** (no solo «Up») y enviar a mano tu primera traza, log y métrica en OTLP/JSON.

## Archivos
| Archivo | Contenido |
|---|---|
| `00_entorno.ipynb` | Lección (teoría + código + 10 gráficos + autoevaluación) |
| `00_proyecto_entorno.ipynb` | Proyecto: levantar el stack, verificar su salud de extremo a extremo y crear tu primer dashboard como código |

## Servicios necesarios
```bash
cd agent-observability-course/stack
docker compose --profile core --profile metrics up -d     # ≈ 0,5 GB de RAM en reposo; ≈ 3,5 GB de imágenes la primera vez
```
Sin Docker: ambos notebooks funcionan en **modo degradado** (datos pregrabados; las comprobaciones online se marcan «no evaluable»).

## Lecturas
- Docker Docs, *Using profiles with Compose* — <https://docs.docker.com/compose/how-tos/profiles/>
- OpenTelemetry, *Observability primer* — <https://opentelemetry.io/docs/concepts/observability-primer/>
- Grafana Labs, `grafana/docker-otel-lgtm` — <https://github.com/grafana/docker-otel-lgtm>
- Honeycomb, *So We Shipped an AI Product. Did it Work?* — <https://www.honeycomb.io/blog/we-shipped-ai-product>

## Siguiente
`01_agente_base`: SupportOps por dentro (bucle LLM + herramientas, proveedor agnóstico, tráfico y fallos).
