---
instance_id: 08-ml-system-design@design
session_id: gold-mlsd-strong-es
stage: ml-system-design
variant: design
phase: vo1
role: mle
level: L5
lang: es
domain: recsys
time_scale: 1.0
budget_minutes: 60
---

### T1 · interviewer · t=00m

Hola, soy Elena Vasquez, Staff ML Engineer. Hoy: diseña el sistema que construye la página de inicio personalizada de un miembro: las filas, los títulos dentro de cada fila y su orden, en TV, móvil y web. Tómate un minuto para preguntar lo que necesites.

<meta>
question_id: mlsd-design-homepage-rows-01
phase: intro
</meta>

### T2 · candidate · t=03m

Antes de diseñar quiero fijar el objetivo y las restricciones. Separaría el objetivo de negocio, la satisfacción del miembro a largo plazo medida con retención, del proxy que puedo optimizar día a día: inicios de reproducción con una duración mínima más finalización, porque los clics crudos premian el artwork engañoso. Declaro mis supuestos de forma explícita: unos 200 millones de miembros, un catálogo de unos 20.000 títulos, un presupuesto p99 de 300 ms para la petición de la página, y una frescura tal que un título empezado hace cinco minutos aparece en la siguiente carga de página, no necesariamente en la misma sesión. Guardarraíles: la diversidad de filas y la tasa de inicio de reproducción por perfil no deben empeorar, y el costo por mil peticiones se mantiene plano. Restricciones: el historial de visualización es sensible, así que las features se limitan por perfil con control de acceso, y se aplican filtros de licencias regionales. ¿Coincide este alcance con el tuyo, incluyendo varios perfiles por cuenta y la TV como dispositivo principal?

### T3 · interviewer · t=05m

Coincide. Los números de escala valen como supuestos. Adelante con la arquitectura.

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
</meta>

### T4 · candidate · t=12m

Usaría tres rutas. Batch offline: trabajos diarios y por hora construyen conjuntos de candidatos por tipo de fila (seguir viendo, porque viste, tendencias, novedades) con un modelo de recuperación two-tower y un índice ANN, y escriben embeddings de ítems y features de largo plazo del miembro en un feature store. Nearline: un procesador de streams sobre el log de eventos de reproducción, Kafka más un motor tipo Flink, actualiza features de corto plazo como las últimas 20 reproducciones en minutos e invalida las filas en caché de ese perfil. Online: el servicio de página lee filas de candidatos precalculadas de una caché clave-valor indexada por id de perfil, obtiene features online de un almacén de baja latencia, ejecuta el ranker y luego un ensamblador de página que ordena filas, deduplica títulos entre filas y aplica filtros de licencias. Las features offline y online salen de las mismas definiciones, y el entrenamiento usa joins point-in-time para evitar fuga de datos. Siguiendo una petición: la app de TV llama al servicio de página, la caché devuelve filas en menos de 20 ms, el ranker puntúa unos 500 candidatos y el ensamblador construye la página. Si el ranker excede 150 ms servimos la última página buena en caché de ese perfil, y si no existe, una página de popularidad regional.

### T5 · interviewer · t=14m

¿Cómo eliges el ranker de títulos y cómo lo entrenas?

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
</meta>

### T6 · candidate · t=22m

Comparo dos opciones. Un árbol con gradient boosting sobre features diseñadas es barato y maneja el arranque en frío mediante metadatos, pero es débil con el orden de visualización. Un modelo transformer secuencial sobre las últimas 50 reproducciones captura el orden, pero cuesta unos 30 ms por lote en GPU y necesita más datos. Con un presupuesto de 150 ms calcularía el embedding secuencial del miembro en nearline, de modo que la parte pesada queda fuera de la ruta de la petición, y dejaría una cabeza de ranking pequeña online. La pérdida es listwise con dos cabezas, inicio de reproducción y finalización, combinadas con pesos que ajusto contra retención en los tests. Los datos de entrenamiento vienen de impresiones registradas, que están sesgadas por la exposición de la política anterior y por la posición, así que registro la posición y la propensión de cada impresión, entreno con la posición como feature que neutralizo en inferencia, y reservo una pequeña fracción epsilon de tráfico de exploración aleatoria para obtener datos sin sesgo. Para elegir entre modelos offline uso NDCG@10 sobre un holdout temporal más una estimación de replay con ponderación inversa por propensión en la porción de exploración. Para títulos nuevos uso embeddings de contenido y Thompson sampling con un presupuesto fijo de exploración por fila.

### T7 · interviewer · t=24m

Ahora son las 8pm de un viernes y el servicio de ranking se degrada. ¿Qué pasa? Cuéntame también de seguridad y costo.

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
</meta>

### T8 · candidate · t=33m

Objetivo de disponibilidad: 99,95% para cargas de página, con p99 por debajo de 300 ms. Modos degradados: si el ranker cae o va lento, el servicio de página sirve la última página buena del perfil desde caché; si el almacén de features online cae, el ranker corre con features por defecto calculadas en batch, con menor calidad pero con página; si la caché está fría para un perfil, caemos a una página de popularidad regional. Probaría cada una de esas rutas con pruebas de carga y alertaría sobre la tasa de fallback. Seguridad: las features del historial de visualización se etiquetan como restringidas, el acceso es por servicio y auditado, los logs guardan ids de perfil con hash y un límite de retención, y los títulos no estrenados solo son visibles para perfiles internos marcados, filtrados en el ensamblador de página para que un error del ranker no pueda filtrarlos. El motor de costo es la inferencia en GPU del codificador secuencial; lo mitigo calculando el embedding en nearline solo para perfiles activos en el último día y cacheándolo, en lugar de ejecutarlo por petición.

### T9 · interviewer · t=35m

Supón que el nuevo ranker mejora NDCG offline pero el A/B está plano. ¿Cómo validas y qué revisas?

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
</meta>

### T10 · candidate · t=44m

Validaría en dos etapas. Primero interleaving, que necesita mucho menos tráfico y detecta rápido la preferencia de ranking, pero es una medida relativa: me dice qué ranker prefieren los miembros dentro de la misma lista y no dice nada sobre retención. Por eso la segunda etapa es un A/B con retención y horas como métricas primarias y inicio de reproducción y diversidad como guardarraíles, durante al menos dos semanas completas para cubrir ciclos semanales. Las métricas offline y online pueden discrepar porque el replay offline está sesgado por la política de registro y por la posición, y porque offline no ve efectos a nivel de página ni de novedad. Si NDCG sube y el A/B está plano reviso primero el sesgo entre entrenamiento y servicio comparando las features online registradas con las recalculadas, luego el sesgo de exposición del holdout, y luego si la mejora se concentra en un segmento pequeño. El monitoreo tiene tres capas: calidad del modelo (calibración, deriva de la distribución de scores, reproducción efectiva de los títulos mejor rankeados), datos (tasas de nulos, retraso de frescura del pipeline nearline) y sistema (p99, tasa de aciertos de caché, tasa de fallback). Disparador de rollback: un guardarraíl roto o una tasa de fallback superior al 5% durante diez minutos. Como el sistema decide qué mostrar, mantengo activo el tráfico de exploración epsilon para que los datos sigan sin sesgo.

### T11 · interviewer · t=47m

Un socio de producto dice que los miembros sentirán la página desactualizada y quiere puntuación en tiempo real en todas partes. Defiende tu decisión o cámbiala, y dime qué evidencia te haría cambiar.

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
culture_probe: {value: judgment}
</meta>

### T12 · candidate · t=52m

Mantendría el enfoque híbrido pero cambiaría una cosa. Mi posición: los candidatos en batch más las features nearline ya se refrescan en minutos, y puntuar todo en tiempo real multiplica el costo de GPU y ensancha la latencia de cola, con lo que arriesga el objetivo de 300 ms. El socio tiene razón en que la obsolescencia duele en un caso, justo después de que el miembro termina un título, así que añadiría un re-rank en tiempo de petición de las primeras filas cuando haya llegado un evento de reproducción en los últimos diez minutos. Lo que me haría cambiar: una prueba donde el brazo en tiempo real mejore la retención o los inicios de reproducción por más de lo que justifica el costo. Todavía no sé cuánta obsolescencia notan realmente los miembros, así que lo mediría con un A/B sobre la edad de la caché antes de pagar la infraestructura.

### T13 · interviewer · t=55m

Gracias, ese es nuestro tiempo.

<meta>
question_id: mlsd-design-homepage-rows-01
phase: closed
</meta>
