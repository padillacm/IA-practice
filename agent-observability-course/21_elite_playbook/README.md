# Módulo 21 · Masterclass de élite: depuración de producción de agentes

🔴 **Experto** · ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min)

> ⚠️ Los incidentes son **simulaciones deterministas** del agente de SupportOps (`mock`, semilla fija) con telemetría real del SDK de OpenTelemetry: reproducen la **forma** de cada fallo, no son sistemas reales (≈ 4 tickets/min, valores de memoria del caso D de un modelo simple).
> Los ejemplos de la lección son **variantes** de los de la mesa del proyecto.

No hay herramientas nuevas: hay **criterio**. Un método (bucle de análisis, *bubble-up*, `find_window`), cinco casos de la familia que más duele —**cascada de reintentos, bucle de herramientas, regresión silenciosa, tormenta de cardinalidad y trazas partidas**— con su mitigación **verificada re-ejecutando el incidente**, patrones y antipatrones,
cultura de observabilidad (con una autoevaluación de madurez) y un **compendio de secretos de élite** de los módulos 00-21, con fuentes.

## Objetivos
1. Aplicar el bucle de análisis a un incidente de un agente usando solo telemetría.
2. Detectar cuándo empezó un incidente y qué atributos distinguen a los casos malos.
3. Diagnosticar cascada, bucle, regresión silenciosa, tormenta de cardinalidad y trazas partidas.
4. Verificar una mitigación con datos y prevenir con contratos de telemetría.
5. Elegir patrones, evitar antipatrones y evaluar la madurez de una organización.

## Contenido
| Archivo | Qué es |
|---|---|
| `21_elite_playbook.ipynb` | Lección (15 secciones, 13 gráficos, cinco casos resueltos, 🧠 de élite, compendio consultable, autoevaluación) |
| `21_proyecto_mesa_de_incidentes.ipynb` | Proyecto «mesa de incidentes»: diagnostica 5 incidentes **sin pistas directas** (rúbrica R1-R8, pistas 🪜 solo de método, solución tras ⛔ SPOILER) |
| `COMPENDIO_SECRETOS.md` | Compendio de secretos de élite 00-21 por tema, con módulo y fuente (generado por `build_21.py`) |
| `../supportops/incidents.py` | `build_incident`, `grade`, `trace_table`, `minute_table`, `loop_tickets`, catálogos de causas y mitigaciones (¡la verdad está dentro: no la leas antes de diagnosticar!) |
| `../supportops/tests/test_incidents.py` | Pruebas del módulo |
| `../stack/grafana/dashboards/21-sala-de-guerra.json` | Dashboard «21 · Sala de guerra de SupportOps» (uid `sala-de-guerra`) |

## Servicios necesarios
- **Sin Docker** (modo degradado): todo salvo la sección 9 de la lección y la validación del Collector de la sección 5. Funciona en Colab.
- **Con stack** (opcional): `cd stack && docker compose --profile core --profile metrics up -d`. La sección 9 tarda ≈ 3 min.

## Lecturas
- Majors, Fong-Jones, Miranker (2022), *Observability Engineering* · Carretto (2020), *Edgar* (Netflix Tech Blog) · Sigelman et al. (2010), *Dapper* · Beyer et al., *SRE* cap. 15 y *SRE Workbook* cap. 5 · `danluu/post-mortems`.

## Cómo se conecta
Antes: todo el curso (00-20). Después: el 22 convierte la mesa en el **plan de pruebas** del capstone y reutiliza el compendio como lista de comprobación de la revisión de arquitectura.
