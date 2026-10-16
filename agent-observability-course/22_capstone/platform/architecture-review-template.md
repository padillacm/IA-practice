# Revisión de arquitectura · plataforma de observabilidad de <sistema>

**Estado:** borrador · **Autores:** <equipo> · **Fecha:** <fecha> · **Revisores:** <nombres/roles>

## 1. Contexto y objetivos
Qué sistema se observa (agentes, tráfico, equipos, usuarios de Grafana), qué decisiones debe permitir tomar la telemetría y qué **no** es objetivo.

## 2. Requisitos y restricciones
| Requisito | Medida | Objetivo |
|---|---|---|
| Disponibilidad del agente | ratio de tickets `ok|escalated` | ≥ 99 % |
| Latencia | p95 de `invoke_workflow` | ≤ 8 s |
| Calidad | groundedness (muestra uniforme) | ≥ 95 % |
| Coste | USD por ticket resuelto | ≤ ... |
| Privacidad | PII en backends | 0 (sin nombres) |
| Retención | por clase de dato | ... |

## 3. Arquitectura propuesta
Diagrama y descripción por capas: instrumentación → Collector (redacción, span metrics, tail sampling) → Tempo/Loki/Prometheus → Grafana/alertas. Despliegue (K8s/Helm) y límites.

## 4. Decisiones clave (ADR) y alternativas descartadas
| Decisión | Alternativas | Por qué | Coste/riesgo |
|---|---|---|---|
| Tail sampling en un gateway | head sampling; todo | ... | memoria ≈ tráfico × decision_wait |

## 5. Riesgos y modos de fallo
Para cada riesgo: probabilidad, impacto, **detección** (qué señal), **mitigación** y dueño. Incluye: pérdida silenciosa de telemetría, cardinalidad, trazas partidas, fuga de PII, regresión silenciosa.

## 6. Coste
Estimación mensual (volumen, retención, precio) con supuestos explícitos y sensibilidad (×2 tráfico, ×2 retención).

## 7. Plan de despliegue y de pruebas
Orden de rollout, pruebas canario, contratos de telemetría, mesa de incidentes y criterios de salida.

## 8. Preguntas abiertas
Lo que no se sabe y cómo se averiguará (con fecha).
