# Módulo 10 · Grafana: dashboards como código, correlación de señales y alertas

🟡 Intermedio · ≈ 4 h 30 min · Servicios: `core` + `metrics` (`docker compose --profile core --profile metrics up -d`, ≈ 0,45 GB). Sin Docker: se valida el JSON/YAML en local y se muestran capturas pregrabadas.

## Qué aprenderás
- Qué es (y qué no es) Grafana: un **frontend de consultas** sobre Prometheus, Loki y Tempo; por qué un dashboard debe **responder una pregunta** (RED, USE, señales de oro, modelo de madurez de la guía oficial).
- El **JSON de un dashboard** (paneles, `gridPos`, targets, `fieldConfig`, variables, enlaces) y el **provisioning** desde archivos, con sus trampas (UI vs. archivo, `uid` estable).
- **Dashboards como código** (`supportops.dashkit`: generación determinista, `lint`, `query_check` contra la API) y el ecosistema actual (Foundation SDK, Grafonnet, Terraform, `gcx`).
- **Variables** (consulta, texto, intervalo, datasource) y `$__rate_interval` (fórmula verificada contra Grafana).
- Qué **panel** usar para cada señal (stat, series, mapa de calor con **exemplars**, tabla de trazas TraceQL, logs LogQL).
- **Correlación**: exemplar → traza → logs → métricas; *data links*, enlaces de dashboard, correlaciones por API; **Explore**.
- **Alertas aprovisionadas**: consulta → reduce → umbral, `for`, `noDataState`, etiquetas, anotaciones con plantilla, política de notificación y contact point; ciclo Normal → Pending → Firing medido.
- El dashboard **«Salud del agente»** (síntomas → dónde → por qué) con navegación entre señales.

## Archivos
| Archivo | Contenido |
|---|---|
| `10_grafana.ipynb` | Lección (≥ 8 gráficos y 3 capturas reales, experimentos en vivo, 🧠 de élite, autoevaluación con cálculo/diagnóstico/transferencia) |
| `10_proyecto_grafana.ipynb` | Proyecto: construyes el dashboard como código + una regla de alerta, con rúbrica R1-R8 (+ L1-L2 en vivo) |
| `img/` | Capturas reales (Chromium sin interfaz): dashboard durante el incidente, Explore con la traza, alertas |
| `../stack/grafana/dashboards/10-salud-del-agente.json` | Dashboard aprovisionado (uid `salud-agente`), generado por `_tools/builders/build_10.py` |
| `../stack/grafana/provisioning/alerting/10-*.yaml` | Contact point, política de notificación y 3 reglas de alerta (síntomas; una pausada) |
| `../supportops/dashkit.py` | Constructor de dashboards, `lint`, `query_check`, `grafana()`, `upload()` |

## Servicios necesarios
`core` + `metrics`. Sin ellos, los notebooks siguen funcionando (JSON/YAML validados en local) y la rúbrica estructural del proyecto se completa.

## Lecturas
- Grafana, *Dashboard best practices* — <https://github.com/grafana/grafana/blob/main/docs/sources/visualizations/dashboards/build-dashboards/best-practices/index.md>
- Grafana, *File provisioning of alerting resources* — <https://github.com/grafana/grafana/blob/main/docs/sources/alerting/set-up/provision-alerting-resources/file-provisioning/index.md>
- Grafana Foundation SDK — <https://github.com/grafana/grafana-foundation-sdk> · Grafonnet — <https://github.com/grafana/grafonnet>
- Tom Wilkie, *The RED Method* — <https://grafana.com/blog/2018/08/02/the-red-method-how-to-instrument-your-services>
- Beyer et al., *Site Reliability Engineering*, cap. 6 — <https://sre.google/sre-book/monitoring-distributed-systems/>

## Siguiente
`11_multiagente`: ver una petición que atraviesa varios agentes, con los mismos dashboards y enlaces entre señales. (Las alertas por SLO y *burn rate* llegan en el módulo 16.)
