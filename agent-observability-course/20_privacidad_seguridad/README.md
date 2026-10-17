# Módulo 20 · Privacidad y seguridad de la telemetría de agentes

🔴 **Experto** · ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min)

> ⚠️ Los datos personales son **sintéticos** y los ataques de *prompt injection* están **simulados** (`InjectableLLM`, un modelo deliberadamente vulnerable y determinista): no mide la vulnerabilidad de ningún LLM real.
> Esto es ingeniería de telemetría, **no asesoría legal**.

Tu observabilidad es una segunda copia de los datos de tus clientes: aquí mides cuánta PII acaba en spans y logs, la **redactas** (a mano, con el procesador `redaction` y con OTTL en un Collector real), decides **qué contenido capturar**, **detectas prompt injection**
(contenido + comportamiento solo con trazas), alertas, auditas con una cadena de hashes y fijas **retención por clase de dato**.

## Objetivos
1. Mapear y medir la PII por señal con la captura de contenido apagada y encendida.
2. Implementar un redactor (regex + Luhn + diccionario; etiqueta / máscara / HMAC) y evaluarlo (recall y sobre-redacción).
3. Configurar y verificar `redaction` y `transform` (OTTL) en el Collector 0.162.0; entender sus límites y por qué un hash sin clave no protege.
4. Diseñar una política de captura de contenido por niveles.
5. Detectar inyección directa e indirecta (detector de contenido + monitor de comportamiento) y medir su compromiso.
6. Alertar (métricas, logs con `trace_id`, regla de Grafana como código), auditar y fijar retención.

## Contenido
| Archivo | Qué es |
|---|---|
| `20_privacidad_seguridad.ipynb` | Lección (13 secciones, 11 gráficos, Collector real, inyección en vivo, 🧠 de élite, autoevaluación) |
| `20_proyecto_privacidad_seguridad.ipynb` | Proyecto: redactor, seudónimos, config del Collector, detector de inyección, monitor de comportamiento, alerta y auditoría (rúbrica R1-R7, pistas 🪜, solución tras ⛔ SPOILER) |
| `../supportops/privacy.py` | `Redactor`, detectores, `InjectionDetector`, `InjectableLLM`, `BehaviorMonitor`, `PrivacyInstrumentor`, `AuditTrail`, retención, `RedactionLab` (Collector efímero) |
| `../supportops/tests/test_privacy.py` | Pruebas del módulo |
| `../stack/grafana/dashboards/20-privacidad-seguridad.json` | Dashboard «20 · Privacidad y seguridad de SupportOps» (uid `privacidad-seguridad`) |

## Servicios necesarios
- **Sin Docker** (modo degradado): todo salvo las comprobaciones con Collector/Loki reales (se emulan y se marcan «simulado»). Funciona en Colab.
- **Con Docker**: el Collector de las secciones 5 y 6 es un contenedor efímero con puertos aleatorios (no necesita el stack ni el candado).
- **Con stack** (opcional): `cd stack && docker compose --profile core --profile metrics up -d`. La sección 8 tarda ≈ 3 min.

## Lecturas
- README del procesador `redaction` y de las funciones OTTL (`opentelemetry-collector-contrib`, v0.162.0).
- OWASP Top 10 para aplicaciones LLM 2025 (LLM01, LLM02) · Greshake et al. (2023), *Indirect Prompt Injection* (arXiv:2302.12173) · Willison (2025), *The lethal trifecta*.

## Cómo se conecta
Antes: módulos 04 (contenido *opt-in*), 05 (Collector), 08 (Loki), 12 (herramientas), 16 (alertas). Después: el 21 reutiliza las señales de seguridad en la mesa de incidentes; el 22 integra redacción, detección y auditoría en la plataforma completa.
