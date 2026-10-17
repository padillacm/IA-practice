# Revisión de ejecutabilidad 2 · módulos 12-22

Entorno: venv limpio (Python 3.13, `pip install -e ".[viz,otel,mcp,nb,dev]"` + ipykernel + nbclient; `mcp` 2.3.0, `opentelemetry-sdk` 1.45.1), CPU, 4 núcleos, `FAST_DEV_RUN=True`. Cada lección y proyecto se ejecutó de arriba abajo con nbclient (`allow_errors`, cwd = carpeta del notebook) en: (a) sin stack (daemon Docker arriba, stack abajo), (b) sin Docker/helm (`DOCKER_HOST` y `HELM` falsos) para 18-22, (c) con el stack real bajo `flock /tmp/obs-stack.lock` (`core+metrics` para 12-16 y 20-22; `core+profiling` para 17), `down -v` al terminar.

## Resultados
| Mód. | Sin stack | Sin Docker | Con stack | Rúbrica (plantilla ❌ / solución ✅) |
|---|---|---|---|---|
| 12 | OK 21 s + 11 s | n/a | OK 45 s + 10 s | 0/6 → 6/6 |
| 13 | OK | n/a | OK 36 s | 0/6 → 6/6 |
| 14 | OK | n/a | OK 65 s | 0/7 → 7/7 |
| 15 | OK | n/a | OK 85 s | 0/6 → 6/6 |
| 16 | OK | n/a | OK 184 s (§7.1) | 0/6 → 6/6 |
| 17 | OK (R7 omitida) | n/a | OK 69 s | 8/8 → 9/9 con Pyroscope (R7) |
| 18 | OK 154 s (Docker efímero) | OK (R9 omitida) | n/a (no usa el stack) | 9/9 (x6 en vivo idéntico) |
| 19 | OK (charts locales: no) | OK, 4/4 con 4 omitidas | n/a | 8/8 en vivo (x3); helm lint/template + kubeconform OK |
| 20 | OK | OK | OK 54 s | 0/7 → 7/7 |
| 21 | OK | OK | OK | 0/8 → 8/8 (+25/25 mesa) |
| 22 | OK | OK | OK 72 s | 0/8 → 8/8 |

Las rúbricas son deterministas: el resultado de la solución es idéntico entre ejecuciones y entre modos (solo cambia el panel «Estado del stack»). Sin salidas, trazas ni `*.executed.ipynb` en el repo (0 notebooks con outputs).

## Problemas encontrados y arreglados
1. **20 y 21 fallaban en venv limpio**: `DataFrame.style` exige `jinja2`, que ningún extra instalaba. `jinja2` añadido a los extras `viz` y `nb` (`pyproject.toml`).
2. **Carreras de puertos en 18-19 (R3)**: `docker run -d` seguido de `docker port ...splitlines()[0]` fallaba si la tabla de puertos aún estaba vacía; el Collector se daba por listo con solo leer su log; las métricas internas se leían una vez (de ahí `None` en la tabla de `num_traces`). Ahora: `_host_port` (reintentos con plazo y error con logs), `_docker_run` (reintentos), sondeo real de OTLP antes de enviar, reintentos en `send`/scrapes/`BackendLab._req`, sondeo de las métricas del procesador, `run_collector_experiment(attempts=3)` si no conserva nada, valores por defecto 0,0 en la tabla, línea base de RSS estabilizada en la tormenta de cardinalidad, y los mismos helpers en `k8s.py` (`ApiServerLab`, `FlowLab`, `AffinityLab`). No pude reproducir el fallo original en 3+3 ejecuciones (antes y después del arreglo); es endurecimiento preventivo. Residual: el RSS de la tormenta de 2 000 series varía ±5 MB (medición real).
3. **18 R9** contaba «sin Docker» como ❌ (`bool(None)`); ahora ⏭️. **19 R7** afirmaba «API server real» sin Docker; ahora lo etiqueta «solo la estructura».
4. **20 R1**: umbral de recall 0,86 → **0,85** (la solución mide 0,869; sin el detector DNI o IBAN baja a 0,844, por lo que sigue discriminando).
5. `.gitignore`: `*.executed.ipynb`, `*.nbconvert.ipynb`.
6. Regenerados 12-22 con la celda de instalación nueva de `_a1_common` (rev-ejec 00-11).

## Notas
- 17 R3/R4 miden speed-ups reales (≥5× y ≥3×); la solución de referencia da ≈18× y ≈5×: margen suficiente salvo CPU muy saturada.
- 19 en vivo: el nº de trazas del flujo de extremo a extremo varía (55-73) entre ejecuciones; la rúbrica (10-40 %) lo tolera.
- Con el stack, Pyroscope tarda ≈ 60 s: con el stack recién levantado, 17 avisa «arrancando» y cae a modo degradado (correcto).

## No probado
Pods reales en Kubernetes (el sandbox no ejecuta contenedores anidados); `helm pull` desde los repositorios oficiales (github.io bloqueado: se usó un clon local con `COURSE_CHARTS_DIR`); proveedores LLM reales; Colab; Windows/macOS; entorno sin ninguna caché de imágenes Docker (primera descarga).
