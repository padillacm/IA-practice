# Revisión pedagógica 3 · módulos 16-22 y guía de estudio

Revisor: P3 (16-22). Criterios: carga cognitiva, andamiaje (ejemplo resuelto → práctica guiada → independiente), práctica de recuperación y repaso espaciado, alineamiento constructivo (objetivo ↔ lección ↔ proyecto ↔ autoevaluación), Bloom, analogías con ML / backend / SRE para un alumno que parte de cero en el stack.
Solo se editaron **builders** y solo texto (cajas, pistas, tablas, cabeceras): se comprobó que **todas las celdas de código de los 14 cuadernos son idénticas** a las de antes de la revisión, así que no cambió ninguna rúbrica, cifra verificada ni celda ejecutable y no hizo falta reejecutar. `check_course.py`: Todo OK.

## Resumen
Los siete módulos tenían muy buena base: intuición con tabla ML / backend / SRE, ≥ 6 gráficos con «👀 Qué debes observar», autoevaluación con Cálculo / Diagnóstico / Transferencia, proyectos con rúbrica y pistas, y lección del 21 con **cinco casos resueltos como variantes** de los de la mesa (ejemplo resuelto → práctica independiente bien diseñado). Los huecos reales fueron:

1. **Se usaba algo antes de enseñarlo (19).** El módulo 19 mete DaemonSet, Deployment, StatefulSet, Service *headless*, HPA, PDB, ConfigMap, CRD y Operator **sin ninguna explicación de Kubernetes**, y el alumno parte de cero (también de Docker). Añadida la sección **0 «Kubernetes mínimo»** (tabla concepto → equivalente en Compose / backend / ML, un manifiesto anotado línea a línea, Helm ≈ Jinja2 + ficheros de configuración tipo Hydra). Es el cambio de mayor impacto.
2. **Rutas «núcleo vs ampliación» ausentes o contradictorias.** 20 (84 celdas) y 21 (79 celdas, compendio de 74 secretos) no tenían la caja 🧭; 18 y 19 tenían la cabecera y la caja diciendo cosas distintas (18 declaraba núcleo §8 y §11 en la cabecera y ampliación en la caja). Unificadas, y 18/19 indican qué pasos del proyecto saltar si solo se hace el núcleo.
3. **TODOs difíciles sin pistas graduadas.** Añadidas 🪜 Pista 1 (idea) / 2 (casi la API) en 16 (TODO 1, 3, 4a, 5, 6), 20 (pasos 2, 5, 6, 7) y 22 (pasos 2, 5, 6, 7, 8); 17, 18, 19 y 21 ya tenían.
4. **Fórmula o técnica antes del ejemplo a mano.** Añadidos ejemplos resueltos: burn rate con 99 % y 120 tickets (16 §2), tasa de error con pesos 1/π sobre 1 000 trazas (18 §7), Luhn paso a paso con `4111 1111 1111 1111` (20 §3) y un ADR corto con números (22 §9, el entregable más inusual del capstone).
5. **🔁 de solo recuerdo / sin transferencia.** Ahora cada lección incluye al menos una pregunta de aplicación que enlaza con un módulo no inmediato: 16 (`rate()` del 09), 17 (bucles del 13 y SLO del 16), 18 (burn rate sobre métricas muestreadas, 16), 19 (nombres en Compose, 00), 20 (severidad de alertas, 16, antes un dato trivial), 21 (propagación `Traceparent`, 03 → caso E), 22 (contrato «una traza por ticket» → caso E).
6. **Alineamiento y prerrequisitos reales.** 21 decía «todos los módulos»: ahora lista los ocho que usa de verdad (03, 09, 11, 13, 15, 16, 18, 20); 17 pedía el 16 sin usarlo (ahora 13 y 16 solo para la reflexión); 19 pedía el 17 (innecesario) y no el 00 (necesario); 22 detalla los módulos clave.
7. **Analogías que faltaban.** Muestreo estadístico del perfilador = estimar la *accuracy* con un subconjunto de test (17); protobuf como «JSON binario con esquema» (17); HMAC como «hash con contraseña» y elegir umbral = punto de la curva ROC con presupuesto de FPR (20); reponderar una muestra estratificada / desbalanceo de clases (18).
8. **Consistencia.** Módulo 16: nivel 🔴 en cabecera y README del módulo frente a 🟠 en el README raíz → unificado a 🟠.

## Detalle por módulo
- **16 SLOs:** nivel 🟠; ejemplo resuelto en §2; 🔁 +pregunta del 09 (`rate()`); pistas en TODO 1 (P1), 3 (P2), 4a (P1/P2: reproducir la regla vista en §7), 5 (P1/P2), 6 (P2).
- **17 Profiling:** prerrequisitos 13 y 16 corregidos; analogía ML del muestreo y glosa de protobuf; 🔁 +2 (13, 16). El proyecto ya estaba bien andamiado (pistas 1/2 en todos los pasos).
- **18 Escala:** ruta núcleo coherente (§1-8 y §12) y qué pasos del proyecto saltar; ejemplo resuelto 1/π antes del código de §7; 🔁 +Q16 (alerta sobre métricas sesgadas); «predice antes de ejecutar» en el Paso 6 del proyecto.
- **19 Kubernetes:** §0 «Kubernetes mínimo»; ruta núcleo coherente (§0-6, §8, §9) y qué pasos saltar; prerrequisito 00 (y 17 fuera); 🔁 +Q00; el paso de seguridad del proyecto remite al manifiesto anotado de la §0.
- **20 Privacidad:** caja 🧭 (núcleo ≈ 3 h; ampliación: §5.1, retención y supresión, §8 en vivo); Luhn resuelto a mano; HMAC glosado; analogía ROC/FPR; 🔁 Q4 reescrita (severidad ticket vs página); pistas en pasos 2, 5 (P1/P2), 6 (P1/P2), 7 (P1/P2).
- **21 Playbook / mesa:** caja 🧭; prerrequisitos reales; recuadro «predice → mira → compara» (ejemplo resuelto que se desvanece hacia la mesa); protocolo de la mesa (15 min por incidente, 6 pasos, orden sugerido B, D, A, E, C); 🔁 +Q03. Verificado que las alertas de los cinco incidentes son neutrales (solo síntoma) y que cada incidente trae 3-5 cambios plausibles con ruido; los datos necesarios para cada diagnóstico están en la lección (variantes resueltas).
- **22 Capstone:** tabla «Qué reutilizas de cada módulo» (paso → módulos → qué releer); ADR corto resuelto en la lección; pistas en pasos 2, 5, 6, 7, 8; 🔁 +Q21; prerrequisitos concretos.

## Guía de estudio (`GUIA_DE_ESTUDIO.md`)
Ciclo de 6 pasos por módulo (recuperar → leer/ejecutar → proyecto sin solución → pistas → autoevaluación → repaso espaciado), tabla de los 23 módulos con nivel, horas de cabecera frente a **horas reales** (suma de los tres informes: ≈ 118 h frente a ≈ 105 h anunciadas), grafo de prerrequisitos y mapa de conceptos en mermaid, ruta núcleo de ≈ 60 h, rutas por objetivo (trabajo actual ≈ 87 h, producto propio ≈ 87 h, entrevistas, depuración rápida), calendarios de 8 (núcleo), 12 y 16 semanas, escalera de ayuda cuando te atascas, hitos por bloque, mapa de los criterios del brief → módulos y glosario ES/EN de ≈ 50 términos. **Corrige las rutas del README**, que omitían prerrequisitos (el 10 exige 07 y 08; el 22 reutiliza 16 y 20); el README ya apunta a la guía.

## Pendientes (cambios grandes, no abordados)
- **Duraciones reales.** Las cabeceras dicen ≈ 4,5 h por módulo; por nº de celdas y densidad, 18-21 son más cercanos a 5-5,5 h (20 con 84 celdas, 21 con 79). La guía lo refleja; las cabeceras no se tocaron para no divergir del README.
- **Niveles 14-15.** Las cabeceras de los módulos 14 y 15 dicen 🔴 y el README raíz 🟠 (rango de P2); conviene unificar.
- **Proyecto 21 (mesa).** Las Pistas 2 de INC-C e INC-E son casi algorítmicas (dan la definición exacta de la evidencia que corrige `I.grade`); aceptable como pista de nivel 2, pero la mesa «pura» sin pistas queda como reto extra. El Paso 0 imprime el catálogo de causas (opción múltiple guiada): un reto extra podría pedir diagnosticar sin ver el catálogo.
- **Proyecto 18, Paso 6** se reduce a llamar a `S.collector_config`; se mitigó con «predice antes de ejecutar», pero un TODO que pida escribir el YAML a mano reforzaría la habilidad (cambiaría la rúbrica R6).
- **Proyecto 20, Paso 6** (ventana/umbral de alerta) es abierto: se añadió método (mirar la línea base) pero es el único TODO sin una única respuesta; funciona por rango.
- **Carga de 20 y 21.** Siguen siendo largos; la ruta núcleo ayuda, pero lo sano sería partirlos en dos cuadernos (lección A / B) como sugiere P2 para 09 y 11.
- Los proyectos 16-22 son casi todos sin gráficos propios: añadir una visualización del resultado ayudaría a la retroalimentación (p. ej. la curva de burn rate de la alerta del alumno en 16).

## No evaluado
No se ejecutó ningún notebook (solo cambió texto, ver arriba); las horas son estimaciones por nº de celdas y densidad, no mediciones con alumnos; no se comprobaron en un clúster real los pasos del 19 (limitación ya documentada en el módulo); la calidad de las pistas se juzgó leyendo la solución de referencia, no con estudiantes reales.

## Tabla para la guía de estudio (horas reales estimadas, lección + proyecto)
| Módulo | Horas reales | Nivel | Prerrequisitos | Conceptos clave |
|---|---|---|---|---|
| 16 SLOs, alertas e incidentes | 4,5 h | 🟠 | 09, 10, 13, 14, 15 | SLI / SLO, presupuesto de error, burn rate (14,4 · 6 · 1), multiventana, `min_events`, alerta como código, runbook, guardia, postmortem sin culpa |
| 17 Profiling (Pyroscope) | 5 h (3,5 núcleo) | 🟠 | 03, 07, 09, 13 | perfil como 4.º pilar, flamegraph (self/total), muestreo estadístico, GIL, CPU vs *wall*, pprof, Pyroscope v2, `span_id` ↔ perfil, Amdahl, perfil diferencial |
| 18 Escala, muestreo y coste | 5,5 h (3,5 núcleo) | 🔴 | 05, 07-09, 13, 16 | head vs tail sampling, `num_traces` y memoria, sesgo y pesos 1/π, métricas antes de muestrear, cardinalidad, multi-tenant, retención y *tiering*, coste del stack |
| 19 Kubernetes + Helm | 5,5 h (3,5 núcleo) | 🔴 | 00, 05, 18 | K8s mínimo, DaemonSet / Deployment / StatefulSet, Service *headless*, fusión de *values*, `helm lint/template`, `kubeconform`, `load_balancing` por `traceID`, HPA, Operator, GitOps |
| 20 Privacidad y seguridad | 5,5 h (3 núcleo) | 🔴 | 04, 05, 08, 12, 16 | PII y cuasi-identificadores, redactor (regex + Luhn), HMAC, niveles de captura, `redaction` / OTTL, `allowed_keys`, *prompt injection*, monitor de comportamiento, auditoría con cadena de hashes, supresión |
| 21 Playbook de élite | 5 h (3,5 núcleo) | 🔴 | 03, 09, 11, 13, 15, 16, 18, 20 | bucle de análisis, `find_window`, *bubble-up*, cascada de reintentos, bucle de herramientas, regresión silenciosa, tormenta de cardinalidad, trazas partidas, contratos de telemetría, cultura, compendio |
| 22 Capstone | 4,5 h | 🔴 | todo el curso (sobre todo 05, 09, 11, 14, 16, 18-21) | requisitos → arquitectura, contratos en CI, gateway integrado, SLO con incidente, IC de calidad, *scorecard*, checklist de 31 puntos, ADR y revisión de arquitectura, mesa como aceptación |
