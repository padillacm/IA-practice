# Lecciones aprendidas (curso de Sistemas de Recomendación, 20 módulos, 10 agentes)

## Orquestación
- **Límites de API y reinicios del contenedor tumbaron agentes 3 veces.** En un reinicio se perdió ~1 h de trabajo no
  commiteado. → Protocolo de checkpoints desde el inicio: archivo de progreso por agente + commit/push tras cada
  subtarea. Reanudar con SendMessage (conserva el contexto del agente) en vez de lanzar uno nuevo.
- **Cambiar de "no commitees" a "commitea" a mitad de tarea** hizo que el sistema de permisos bloqueara a un agente.
  → Da permiso de commit en el prompt inicial y limita a "solo tus rutas" (`git add <rutas>`, nunca `-A`).
- Un hook exige que no queden cambios sin commitear al terminar cada turno: el coordinador hace commits "WIP: sync" de
  lo que llevan los agentes. Conviene que los agentes commiteen ellos mismos con frecuencia.
- 2–3 módulos por agente funciona bien (≈ 1–2 h por agente). 7 autores en paralelo saturan la CPU local: las
  latencias medidas no son fiables y LightGBM/FAISS pueden colgarse (fijar `LGB_THREADS=1`).
- Reporta al usuario cada vez que termina un agente: qué hay, qué se probó y qué no. El usuario lo agradece y
  detecta pronto lo que falta.

## Contenido y código
- Generar notebooks con **scripts builder** (nbformat) y validar sintaxis por celda evita JSON roto y permite que
  revisores editen sin conflictos. Nunca editar `.ipynb` a mano.
- Cada notebook debe ser **autocontenido en Colab**: los autores incrustan una celda de "utilidades del curso" (carga
  de datos, split, métricas). Riesgo: copias divergentes entre bloques → documenta diferencias de protocolo y haz que el
  revisor técnico las compare.
- **Datasets**: GroupLens, Hugging Face, Kaggle y Zenodo estaban bloqueados por el proxy del entorno. Funcionó un espejo
  en raw.githubusercontent.com. → Exige cadena oficial → espejo → sintético con el mismo esquema, y que el informe diga
  qué se probó con datos reales.
- **Rúbricas**: varias pedían cifras que la propia solución no alcanzaba (calibradas con lo deseado o con datos
  sintéticos). → Calibrar con lo medido y revisar con datos reales; el revisor de ejecutabilidad lo comprueba.
- Métricas de ranking: cuidado con empates optimistas (un modelo constante sacaría HR=1) y con muestras de test
  pequeñas (ML-100K en split temporal deja ~50 usuarios: ruido).
- Librerías con instalación rota en Python ≥ 3.11 (p. ej. `obp`): documentar el workaround en la celda.
- Añade `.gitignore` con `__pycache__/` y `data/` desde el principio (se colaron `.pyc` en un commit).
- El badge de Colab apunta a la rama por defecto: funcionará solo tras merge. Dilo al usuario.

## Revisión
- El revisor técnico encontró: fórmulas inconsistentes, citas con título/año erróneos, cifras de parámetros falsas,
  configs inválidas (Triton `dims: []`), un servicio que nunca usaba su ranker, OOM por matriz densa N².
- El revisor pedagógico encontró lo que el técnico no: 0 cajas de repaso espaciado en 20 lecciones, ~60/250 gráficos
  con interpretación, TODOs que saltaban a la solución, autoevaluación casi solo de recuerdo, prerrequisito usado antes
  de enseñarse (NDCG en el proyecto 01), módulos sobrecargados. → Inclúyelo siempre.
- Pedir al final un módulo extra de "élite" (masterclass con implementación de lo que el capstone solo enumera) y un
  compendio de secretos con fuentes fue lo más valorado para "destacar".
