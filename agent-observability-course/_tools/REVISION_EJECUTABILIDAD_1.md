# Revisión de ejecutabilidad E1 · módulos 00-11

Revisor: rev-ejec-00-11. Entorno: Python 3.13, 4 CPU, 15 GB, Docker 29.8.2; `FAST_DEV_RUN=True`, CPU, sin claves API (`LLM_PROVIDER=mock`).

## Método
- Copia limpia de los archivos versionados (sin `data/` ni nada ignorado) y ejecución de las 24 notebooks (lección + proyecto) de arriba abajo con `nbclient`, `allow_errors=True`; se cuentan errores fuera de celdas TODO.
- Los proyectos incluyen la solución de referencia ejecutable en su última celda, así que «ejecutar todo» evalúa la rúbrica con la solución.
- Pasadas: (a) sin stack, 2 veces (`STACK_HOST=nohost.invalid` y `OTEL_EXPORTER_OTLP_ENDPOINT` inválido para forzar el modo degradado) · (b) con stack `core`+`metrics` y `TEMPO_CONFIG=tempo-metrics.yaml` bajo `flock /tmp/obs-stack.lock`: 00-11 (pasada 1) y 00,03,05,07,08,09,10,11 (pasada 2) · (c) `core` solo con `tempo.yaml` por defecto: 03,05,07,08 · (d) venv limpio (solo ipykernel+nbclient+nbformat; la primera celda instala todo, incluido `%pip` de 06) sin stack.
- Determinismo: comparación celda a celda de las salidas entre las dos pasadas.

## Resultados
| Módulo | Sin stack (x2) | Con stack (x2) | Rúbrica (solución) |
|---|---|---|---|
| 00 | OK | OK (19+8 s) | OK; sin stack 4 «no evaluable» (R1,R2,R4,R6) |
| 01, 02, 04, 06, 11 | OK | OK | 6/6, 6/6, 10/10, 6/6, 6/6 |
| 03 | OK | OK (12+5 s) | 10/10 |
| 05 | OK | OK (39+50 s) | 11/11 con stack; sin stack 10 OK + R11 «no evaluable» |
| 07 | OK | OK (41+56 s) | 6/6 |
| 08 | OK | OK (20+6 s) | 6/6 |
| 09 | OK | OK (157+88 s) | 10/10 (sin stack 7 + L «n/a») |
| 10 | OK | OK (202+5 s) | 10/10 (sin stack 8) |

Tiempos «lección+proyecto». Sin stack: ≤ 1 min por notebook (05 lección ≈ 40 s, 06 ≈ 35 s con `pip`). RAM del stack bajo carga: Grafana ≈ 300 MiB, Tempo ≈ 185, Loki ≈ 100-135, Prometheus ≈ 70, Collector ≈ 70 (≈ 0,75 GB total): coherente con «≈ 1 GB con carga». Pico de la sesión de Python: no se midió con precisión (< 1 GB en `top` puntual).

Las únicas diferencias entre ejecuciones son ids aleatorios (trace_id/span_id/instance.id), marcas de tiempo, rutas de la máquina, mediciones de tiempo/memoria en demos de lección (03, 05, 07, 08, 09, 11) y el solapamiento de `{ }` con `limit` en 07 (no determinismo de Tempo, explicado en el texto). Ninguna rúbrica depende de latencias de la máquina y todas dieron el mismo resultado en las dos ejecuciones.

## Problemas encontrados y arreglados
1. **Celda de instalación rota en venv limpio (grave).** Tras `pip install -e` en el mismo kernel, la celda siguiente fallaba con `ModuleNotFoundError: supportops` (el editable recién instalado no se ve hasta reiniciar). Solo se manifestaba la primera vez en un entorno sin el paquete. Arreglo en `BOOT` de `builders/_a1_common.py`: `sys.path.insert(0, ROOT)` + `importlib.invalidate_caches()`. Regeneradas 00-11 (el cambio afecta también a 12-22; avisado al revisor 12-22). Verificado en un venv nuevo.
2. Ejecutadas, ninguna `*.executed.ipynb` ni salida guardada en los `.ipynb` versionados (0 outputs). `.gitignore` ya excluye `*.executed.ipynb` y `*.nbconvert.ipynb` (añadido por el revisor 12-22).

## Observaciones (sin cambios)
- Proyecto 08, estado plantilla: el TODO 1 (`logging.Formatter` que lanza `NotImplementedError`) imprime «--- Logging error ---» por stderr porque `logging` captura la excepción; es ruido esperado de una celda TODO.
- `STACK_HOST` no afecta al endpoint OTLP por defecto de `setup_telemetry` (`localhost:4318`): con otro host hay que fijar también `OTEL_EXPORTER_OTLP_ENDPOINT`.
- Con `core` solo y Tempo por defecto (`tempo.yaml`), 03, 05, 07 y 08 ejecutan sin errores y la rúbrica pasa (las partes de span-metrics de 07 se degradan).
- Rutas absolutas, `data/` y claves API: ninguna celda depende de ellos (las copias de prueba no tenían `data/`; los pregrabados están versionados).

## No probado
- Colab real (solo el camino `git clone` por lectura de código) y Windows/macOS.
- Proveedores LLM reales (anthropic/openai/ollama).
- `FAST_DEV_RUN=False` (tamaños completos).
- Máquinas con < 8 GB de RAM; ejecución simultánea con otros usuarios del stack.
