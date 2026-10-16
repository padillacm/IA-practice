# Módulo 17 · Profiling continuo con Pyroscope

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 4 h 30 (lección) + ≈ 2 h (proyecto) · **Servicios:** perfil `profiling` (Pyroscope 2.1.2); `core` solo para la sección traza↔perfil.

El **cuarto pilar** de la observabilidad: de «este span es lento» a «esta línea de código gasta la CPU». Aprendes a leer y construir flamegraphs, a escribir un muestreador de pila y el formato **pprof** a mano, a
empujar perfiles a **Pyroscope 2.x** (Connect-RPC, `/ingest` y el SDK `pyroscope-io`), a correlacionar traza y perfil con `span_id` y a encontrar y arreglar un cuello de botella real de SupportOps midiendo el efecto con un perfil diferencial.

## Contenido

| Archivo | Qué es |
|---|---|
| `17_profiling_pyroscope.ipynb` | Lección (15 secciones, 12 gráficos: pilares, error de muestreo, flamegraph a mano, GIL, CPU vs wall, arquitectura de Pyroscope, Amdahl, diferencial, traza↔perfil, coste) |
| `17_proyecto_profiling_pyroscope.ipynb` | Proyecto: diagnóstico con perfiles, arreglo verificable, perfiles en Pyroscope, ticket más caro y guarda de CPU (rúbrica R1-R9, pistas 🪜, solución tras ⛔ SPOILER) |
| `recorded/capture_seed42.json.gz` | Captura pregrabada (modo sin Pyroscope): pilas lentas/rápidas, GIL, sobrecarga, perfiles leídos de Pyroscope |
| `../supportops/profiling.py` | `SamplingProfiler`, pprof a mano, `PyroscopeClient`, `HotPathInstrumentor`, `run_workload`, `plot_flamegraph`, dashboard |
| `../supportops/tests/test_profiling.py` | 14 pruebas (las de Pyroscope se saltan si no está en :4040) |
| `../stack/grafana/dashboards/17-profiling.json` | Dashboard «17 · Profiling continuo» (uid `profiling`) |
| `../stack/grafana/provisioning/datasources/datasources.yaml` | Añade `tracesToProfiles` al datasource de Tempo (salto span → perfil) |

## Servicios necesarios

- **Sin Docker**: las secciones 1-5 y los experimentos de CPU de la lección y el proyecto (modo degradado con captura pregrabada en lo que depende de Pyroscope). Funciona en Colab.
- **Con Pyroscope**: `cd stack && docker compose --profile profiling up -d` (tarda ≈ 60-90 s en estar *ready*; el SDK `pyroscope-io` y `pyroscope-otel` se instalan en la primera celda).
- **Traza ↔ perfil**: `docker compose --profile core --profile profiling up -d`.

## Lecturas

- Gregg, *The Flame Graph* (ACM Queue 2016) · Ren et al., *Google-Wide Profiling* (IEEE Micro 2010).
- Documentación de Grafana Pyroscope (arquitectura v2, clientes) y `api/querier/v1/querier.proto`.
- OpenTelemetry Profiles (alfa pública, marzo 2026): https://opentelemetry.io/blog/2026/profiles-alpha/

## Qué se probó (honestidad)

Probado con Docker real: Pyroscope 2.1.2 (push Connect y `/ingest` con pprof propio, SDK `pyroscope-io 1.3.0`, `SelectMergeStacktraces`, `SelectMergeSpanProfile`, `LabelNames/Values`, `SelectSeries`), `pyroscope-otel 1.1.0` con el Collector+Tempo reales
(el span raíz lleva `pyroscope.profile.id` y su perfil se recupera por `span_id`), el datasource con `tracesToProfiles` y las 3 consultas del dashboard contra `/api/ds/query`. **No** probado: la navegación visual «Profiles for this span» en un navegador, perfiles de memoria (`mem_enabled`), perfilador eBPF/Alloy,
el perfilador de pila experimental del SDK y OTel Profiles.
