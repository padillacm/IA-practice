# Módulo 22 · Capstone: plataforma de observabilidad completa para SupportOps

🔴 **Experto** · ≈ 4 h 30 min (guía y plataforma de referencia ≈ 2 h 30 min + entrega final ≈ 2 h)

> ⚠️ Todo es **simulado y determinista** (`mock`, semilla 42). El análisis de muestreo y coste usa el corpus del módulo 18 (agente único); el multi-agente aporta contratos, SLO y privacidad. Los precios son ilustrativos.
> Ningún pod llegó a ejecutarse en un clúster en el entorno de construcción (módulo 19): del despliegue se verifican valores y configuraciones, no un clúster en marcha. El README de cada sección lo dice.

**No hay conceptos nuevos: es integración.** El multi-agente de SupportOps con instrumentación OTel por servicio, captura de contenido configurable y redacción; un **gateway del Collector** (`memory_limiter` → `redaction` → `span_metrics` antes del muestreo → `tail_sampling` → `batch`) validado con el binario real y probado contra Tempo/Loki/Prometheus;
**contratos de telemetría**, SLOs con burn rate, calidad con intervalo, coste por agente solo en hojas, sesgo del muestreo; un **scorecard** automático y un **checklist de producción** de 31 puntos (15 automáticos); y una **revisión de arquitectura** que se defiende con riesgos, señales y mitigaciones.

## Objetivos
1. Diseñar la arquitectura a partir de requisitos medibles y justificarla (ADR).
2. Verificar la instrumentación con contratos automáticos.
3. Configurar y validar un gateway del Collector que integre privacidad, RED y muestreo.
4. Medir muestreo, coste, SLO y calidad con su propia telemetría.
5. Evaluar la plataforma (scorecard + checklist) y defenderla en una revisión de arquitectura.

## Contenido
| Archivo | Qué es |
|---|---|
| `22_capstone.ipynb` | Guía y plataforma de referencia (16 secciones, 8 gráficos, gateway real en Docker, scorecard, checklist, revisión de riesgos, 🧠 de élite, autoevaluación) |
| `22_proyecto_capstone.ipynb` | Entrega final: gateway, contratos, SLO, calidad, muestreo, coste, checklist y revisión de arquitectura (rúbrica integral R1-R8, pistas 🪜, solución tras ⛔ SPOILER) |
| `platform/collector-gateway.yaml` | Gateway del Collector de la plataforma (generado por `build_22.py`, validado con `otelcol validate` 0.162.0) |
| `platform/production-checklist.yaml` | Checklist de producción (31 puntos; `automatica: true` = lo mide el scorecard) |
| `platform/architecture-review-template.md` | Plantilla de la revisión de arquitectura (formato ADR) |
| `../stack/grafana/dashboards/22-plataforma-agentes.json` | Dashboard «22 · Plataforma de agentes de SupportOps» (uid `plataforma-agentes`) |

## Servicios necesarios
- **Sin Docker** (modo degradado): todo salvo la validación del Collector y la sección 11 de la lección. Funciona en Colab.
- **Con stack** (opcional): `cd stack && docker compose --profile core --profile metrics up -d`. La sección 11 levanta un gateway efímero en la red `agentobs_default` (≈ 4 min).

## Lecturas
- Módulos 00-21 · Nygard (2011), *Documenting Architecture Decisions* · *SRE* cap. 32 (production readiness reviews) · Majors et al. (2022), *Observability Engineering*.

## Cómo se conecta
Todo lo anterior. La **mesa de incidentes** (módulo 21) es el examen de aceptación y el **compendio de secretos** (`21_elite_playbook/COMPENDIO_SECRETOS.md`) la lista de comprobación de la revisión.
