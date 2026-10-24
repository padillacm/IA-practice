# Research: el proceso de entrevistas de ML en Netflix

Documento de soporte del change (no es un artefacto del schema). Recoge lo que se sabe públicamente, con qué confianza y qué decisiones de diseño se derivan. Última actualización: 2026-10-24 (tercera pasada, desde el PC del usuario).

**Método.** Tres pasadas:
1. Búsquedas web amplias: guías, Glassdoor, Blind, PracHub, Levels.fyi, Netflix Tech Blog, Netflix Research y prensa.
2. **Lectura directa** (curl) de: el memo de cultura en jobs.netflix.com, la guía de interviewing.io, la de Interview101, research.netflix.com, Levels.fyi, 12 hilos de Blind y 9 experiencias de PracHub (2025–2026).

3. **Tercera pasada (PC del usuario, solo WebFetch; sin navegador disponible).** Leída directamente: la guía de Exponent/Aced (`aced.io`, a donde redirige tryexponent.com) y un resumen de ZenML del post GenRec. **Siguen sin poder leerse** Glassdoor (las 4 páginas, 403), Reddit (la herramienta lo bloquea), Interview Query MLE/RS/AI Engineer (429), netflixtechblog.com (403: ni interleaving ni experimentation analysis) y 1point3acres (403). Dos reintentos con otras cabeceras fueron denegados por el clasificador de permisos como elusión de bloqueo anti-bot y no se insistió. Pendiente para quien tenga un navegador (Claude in Chrome): esas fuentes y los hilos de Blind nuevos.

**No legibles desde el entorno (pasadas 1–2, y siguen igual):**
- Glassdoor, Reddit y netflixtechblog.com responden 403 (anti-bot).
- Exponent/Aced: el proxy los rechaza.
- Interview Query: límite de peticiones (429).

Para esas fuentes se usan los extractos del buscador.

**Confianza.** **Alta** = fuente primaria de Netflix, o varios relatos de primera mano coincidentes. **Media** = varias fuentes de terceros coinciden o hay un relato de primera mano. **Baja** = una sola fuente o fuentes contradictorias. Netflix publica poco sobre su proceso: casi todo es anecdótico y **varía por equipo**.

## 1. Estructura general

| Hallazgo | Confianza | Fuentes |
|---|---|---|
| Pasos: recruiter call → **hiring manager screen** → technical phone screen → onsite "muy largo". El proceso está descentralizado y depende del equipo. | Alta | [interviewing.io], [Blind HM gatekeeper], [PracHub DS 11 rondas] |
| El onsite virtual se divide en **VO1 (general: coding, system design, behavioral)** y **VO2 (específico del equipo: system design del dominio del equipo, partnership con un manager de un equipo socio, segunda reunión con el HM)**. Hay un corte entre ambos: "4 hours of interviews and likely more if I had got past the first set". | Alta | [PracHub VO1 billboard], [PracHub data platform], [Blind messed up] |
| Recruiting puede ofrecer partir el onsite en 2 días. Hay relatos de hasta "9 interviews on a single day". | Media | [interviewing.io], [Blind RS vs MLE] |
| Suele haber 1–2 **directores** en el loop (uno de la organización que contrata y otro de una socia, para reducir sesgo). Uno puede hacer system design y el otro behavioral. Los directores a veces dejan 30 min para las preguntas del candidato. | Alta | [interviewing.io], [Glassdoor MLE: "2 with directors"] |
| **No hay hiring committee ni escala común a toda la empresa.** La decisión es binaria (pass / fail) en una discusión en vivo tras el onsite, buscando consenso ("then you discuss if you'd be open to changing your mind"). El hiring manager actúa como informed captain. | Alta | [interviewing.io], [four-leaf], [Glassdoor DS] |
| Los entrevistadores no están entrenados de forma uniforme y las preguntas no están estandarizadas: el estilo varía mucho de un entrevistador a otro. | Media | [interviewing.io], [Blind feedback 2018] |
| Resultado posible: "ok ratings, pero no encajas en este rol; otro hiring manager está interesado". Es **team matching** y suele implicar repetir parte del loop. Se puede entrevistar con varios equipos a la vez. | Alta | [Blind messed up], [interviewing.io] |
| El feedback al candidato es irregular: desde feedback detallado del HM hasta ninguna respuesta. | Alta | [Blind feedback 2018], [PracHub MLE PR review], [PracHub SWE open-book] |
| Títulos MLE / ML Scientist / Research Scientist casi intercambiables según el equipo: "I interviewed for one and asked for a different title and got it". | Media | [Blind RS vs MLE] |

## 2. Etapas y contenido

### Recruiter screen (≈30 min) — Alta
- Cultura, background, por qué buscas cambio y "Why Netflix?" ([PracHub DS 11 rondas], [IGotAnOffer questions]).
- El memo es lectura obligatoria antes de empezar ([Blind ML research intern]).
- Compensación: el memo confirma **"personal top of market for the role and location"** ([Netflix culture memo]).

### Hiring manager screen (≈30 min) — Alta
- "Very chill"; preguntas bidireccionales de superficie; el HM **vende Netflix** porque el onsite es muy exigente ([interviewing.io]).
- Hace de gatekeeper: comprueba el encaje cultural y que el background cubre el rol ([Blind HM gatekeeper]).
- Algunos loops tienen HMs de dos equipos ([PracHub DS 11 rondas]).

### Technical screen (45–60 min) — Alta
- **MLE, formato A** (Glassdoor, feb 2026): 20' de proyecto previo + 40' de ML coding ([Glassdoor ML Intern/MLE]).
- **MLE, formato B** (organización de GenAI aplicada, sep 2026): 30' de ML fundamentals (KV cache, attention con el cálculo de Q/K/V, normalización L1 vs L2) + 30' de **revisión en vivo de un PR de un feature pipeline**. Los tests pasan y hay que detectar qué fallaría en producción; luego se discute cómo servir esos features con distintos requisitos de tiempo real ([PracHub MLE PR review]).
- **RS** (recsys, 2022): "ML fundamentals + coding (language of your choice)"; en general, "1–2 rondas de ML (problem framing y fundamentals), coding y otra según el equipo" ([Blind RS recsys]).
- **ML Scientist L5** (2025): "ML knowledge screens, a coding screen, and problem framing" ([Blind ML Scientist]).
- **DS**: **dos** screens técnicos. Uno conceptual de estadística ("dirigido a quien tiene un PhD o ha estado expuesto de forma constante a estadística avanzada de grado") y otro de programación SQL y Python/R ("¿usas estas herramientas con la frecuencia suficiente?") ([Blind DS final loop]). Otro relato: "SQL puro que había que ejecutar" + "SQL + caso" ([PracHub DS 11 rondas]).
- **OA de prácticas** (referencia de formato): MLE con 4 preguntas tipo test (Bayes, forward pass, KNN, Transformers) + 2 de coding (multiplicación de matrices dispersas, conversión de formatos con imputación); DS con inferencia causal (ATE, ITT/TOT, IV/LATE) + test de estadística (CLT, t-stat, MDE) ([PracHub MLE intern OA], [PracHub DS intern OA]).
- Un take-home de modelado previo al onsite solo aparece en una guía comercial ([Interview101]). Confianza baja para MLE.

### Coding (VO) — Alta
- Según el equipo: "no LeetCode" o "LeetCode medium con un giro práctico, escrito por ingenieros de Netflix"; "LC interviews are not the norm here" (empleado de Netflix) ([interviewing.io], [Blind no-leetcode]).
- **Dos partes**: un problema y, si sobra tiempo, una extensión a escala de producción o una inmersión técnica (p. ej. multithreading) ([interviewing.io], [PracHub VO1 billboard]).
- El candidato **escribe sus propios tests** ([PracHub SWE open-book]). Una solución "no óptima" puede costar la oferta ([Blind no-optimal]).
- Problemas con sabor a Netflix: deduplicar contenido de la homepage por filas (global para las primeras n posiciones, por fila después), detectar duplicados en el historial de visionado (bucket sort), rotar un billboard o playlist de películas con scores actualizables (two treemaps; follow-ups de multithreading y escalado), sliding windows ([PracHub SWE open-book], [PracHub data platform], [PracHub VO1 billboard]).
- ML coding: métricas de ranking (P@K, NDCG@K), similitud coseno y CF sobre una matriz dispersa, PySpark en algunos roles ([Interview Kickstart MLE], [Dataford MLE]).

### AI-assisted coding (nuevo, 2026) — Media
- Ronda del onsite en la que el candidato trabaja en un **codebase real con herramientas de IA**. Hay un entrevistador presente. Se evalúa cómo descompone el trabajo, cómo da instrucciones a la IA, si **verifica y rebate su output** y si sabe extenderlo, no solo si el código funciona ([Blind AI-assisted, jul 2026]).

### ML fundamentals / breadth — Media
- Bias-variance, L1/L2, overfitting en GBDT, embeddings de co-watch, cold start, popularity bias, métricas de ranking. En organizaciones de GenAI: KV cache y attention ([Interview Query MLE], [PracHub MLE PR review]).

### ML system design — Alta
- **La ronda que más pesa** en Netflix; coding es la que menos ([interviewing.io], [Interview101]).
- Las preguntas son propias y difíciles, a menudo sobre lo que el equipo construye ahora. Los temas recurrentes son escala, disponibilidad y seguridad. No suelen ser preguntas de producto genéricas del tipo "Design Spotify" ([interviewing.io]).
- El entrevistador controla el ritmo: interrumpe en cuanto obtiene la señal y pasa al siguiente punto. **No terminar el diseño a tiempo tumbó a un candidato** que había respondido bien a todo ([PracHub VO1 billboard], [PracHub data platform]).
- Prompts de ML reportados: ML job scheduler (training vs batch inference, asignación de recursos, monitorización, crash handling, multi-tenancy), compute allocation, portal ML full-stack, homepage rows, artwork personalization, Continue Watching, búsqueda personalizada, embeddings multimodales del catálogo ([PracHub VO1 billboard], [PracHub MLE infra], [Interview Kickstart MLE]).
- "Reverse system design": preguntas incisivas sobre sistemas que el candidato construyó (cuál fue el de mayor escala, cómo lo escaló) ([interviewing.io]).

### ML depth (dominio del equipo) — Media
- Netflix Research no centraliza la investigación: los equipos trabajan junto al negocio. Áreas: Analytics, CV & Graphics, Consumer Insights, Encoding & Quality, **Experimentation & Causal Inference, Machine Learning, ML Platform, NLP & Conversations, Recommendations** ([Netflix Research]).
- **GenRec** (2026, resumen secundario de ZenML; el post original no se pudo leer): ranker LLM-nativo en dos fases (adaptar un LLM abierto a datos de Netflix y post-entrenar para ranking con pesos por recompensa), historial convertido a texto con un "feature budget" que reduce tokens ~⅓, pérdida multiobjetivo, inferencia en modo prefill puntuando todos los candidatos en un forward pass (vLLM), A/B con ~10 % del tráfico durante ~4 semanas ([ZenML GenRec]; Baja hasta leer el post). Ancla útil para preguntas de system design de recsys con LLM.
- Publicaciones recientes que anclan el contenido: LLM recommendation con semantic IDs (beam search autoregresivo vs multi-token prediction, oct 2026), integración del Foundation Model en la homepage y la búsqueda (feb 2026), artwork personalization vía LLM post-training (feb 2026) ([Netflix Research]).

### Experimentación y A/B testing — Alta en DS
- Diseño, power, peeking, interferencia, efectos heterogéneos, varianza y bootstrap; caso práctico: diseñar y dimensionar un experimento de **frequency cap de anuncios** ([Glassdoor Senior DS], [PracHub DS 11 rondas], [Prepfully DS]).
- Prácticas documentadas por Netflix: interleaving como primera etapa, CUPED / post-estratificación, quasi-experimentos geográficos ([Netflix TechBlog interleaving], [Netflix CUPED paper], [arXiv 1910.03878]).

### Loop final según Exponent — Media
- Tras el technical screen, **hasta 6 rondas de 30 min**: una técnica (ML, A/B tests, ML system design y a veces código) y rondas de cultura con RR. HH., el hiring manager y casi siempre un **manager "partner" de otro equipo**. Suele pedirse una **charla de 10–15 min** sobre un tema técnico a elección del candidato. Las rondas de cultura se evalúan con rúbrica explícita ([Exponent MLE], leído directamente en aced.io; guía comercial, coincide con interviewing.io y PracHub en el partner manager).
- Preguntas de ejemplo: CF, árboles vs redes, descomposición sesgo-varianza, función que devuelve una clave aleatoria con probabilidad proporcional a sus pesos, predecir la puntuación de una reseña a partir del texto, qué métricas monitorizar tras desplegar, "diseña un sistema como Netflix"; conductuales: la vez que fuiste honesto en el trabajo, feedback difícil a un compañero, qué dicen de ti tus compañeros ([Exponent MLE]).
- Consejo repetido: no citar el salario como motivación, los managers lo ven como señal de alerta ([Exponent MLE]; Baja, una sola fuente).

### Presentation — Media
- RS / research intern: **panel presentation de 1 h** sobre la propia investigación ([Glassdoor ML Intern 2026]).
- DS senior: presentación de un take-home de analítica de producto y experimentación a dos DS ([Glassdoor Senior DS]).

### Project deep dive — Alta
- "Netflix goes into prior work experience more than other FAANGs": aciertos, fallos y qué harías mejor; distintas personas profundizan en distintas partes; buscan *Freedom & Responsibility* en tus historias ([Blind HM gatekeeper]). "1 previous experience" en un loop L5 ([Glassdoor MLE]).

### Partnership (VO2) — Media
- Un manager de un **equipo socio** entrevista en formato behavioral sobre la colaboración entre equipos ([PracHub data platform]). Un relato de MLE (feb 2026) menciona una "stakeholder chat" ([PracHub MLE infra]).

### Culture / "Dream Team" — Alta
- El memo vigente, leído directamente, describe 4 principios: **The Dream Team, People Over Process, Uncomfortably Exciting, Great and Always Better**.
- Sus 8 valores, con la descripción de cada uno según el memo:
  - **Selflessness**: humildad para buscar las mejores ideas; buscar lo mejor para Netflix, no para uno mismo o su equipo; ayudar a otros a tener éxito.
  - **Judgment**: soluciones de largo plazo; buenas decisiones pese a la ambigüedad; datos que informan la intuición.
  - **Candor**: dar y recibir feedback; admitir errores abiertamente y compartir lo aprendido.
  - **Creativity**: acoger nuevas ideas y persistir en busca de soluciones más innovadoras.
  - **Courage**: vulnerabilidad en busca de la verdad; arriesgarse a fallar o desafiar el statu quo.
  - **Inclusion**: reconocer y contrarrestar los propios sesgos.
  - **Curiosity**: aprender rápido; interés por las ideas de otros; humildad sobre lo que no se sabe.
  - **Resilience**: adaptarse rápido; tomar decisiones difíciles sin demora; abrazar los retos.
- Keeper test, textual: "if X wanted to leave, would I fight to keep them?" / "knowing everything I know today, would I hire X again?". "We stick with employees through short-term bumps."
- People Over Process: "context not control"; "We avoid decision-making by committee… we identify an **informed captain**"; "**highly aligned and loosely coupled**"; "**farming for dissent**"; "**disagree then commit**"; reflexión posterior del captain.
- Candor como hábito: "constructive feedback is part of our everyday work (like brushing your teeth)", también hacia alguien más senior.
- Fuente de todo lo anterior: [Netflix culture memo].
- En la entrevista: la **"Dream Team" interview** la conduce un director y es más intensa (escala, accountability, comunicación abierta de preocupaciones, alto riesgo y alta recompensa). Si suspendes behavioral te rechazan, y no leer el memo "is a fail". Toca promocionarse con métricas e impacto: proyecto favorito, el último y el más significativo, qué buscas en tu siguiente rol ([interviewing.io]).
- Las señales de cultura se evalúan en todas las rondas ([Interview101], [Blind HM gatekeeper]).

## 3. Niveles — Media
- Niveles formales desde 2022. L4 ≈ SWE II con más autonomía de lo habitual, **L5 = senior, el nivel núcleo**, L6 = staff ([DesignGurus levels]).
- Compensación de MLE en EE. UU.: L4 ≈ $403K y L5 ≈ $575K de TC; mediana $550K con 18 datos ([Levels.fyi MLE]).

## 4. Loops de referencia (síntesis para el simulador)

| Rol | Screens | VO1 (general) | VO2 (equipo) |
|---|---|---|---|
| ML Engineer | recruiter, HM screen, technical screen (A: proyecto + ML coding · B: fundamentals + PR review) | coding, ml-system-design, culture | ml-depth, project-deep-dive, partnership, HM onsite |
| Research Scientist | recruiter, HM screen, technical screen (ML fundamentals/framing + coding) | presentation (research talk), ml-fundamentals, coding (ML), culture | ml-depth, partnership, HM onsite |
| Applied / Data Scientist | recruiter, HM screen, technical screen ×2 (SQL ejecutable · estadística) | presentation (take-home), experimentation, coding (SQL/pandas), culture | ml-fundamentals (caso de modelado), partnership, HM onsite |

Opcionales en cualquier rol: `ai-assisted-coding`, y las etapas que no estén en el loop por defecto del rol.

## 5. Implicaciones para el diseño

1. **14 etapas** en tres fases (screen, VO1, VO2), con loops por rol y variantes por etapa (`stage@variant`).
2. **Corte entre VO1 y VO2**: un mini-debrief decide si se continúa.
3. **Debrief final** con pass / fail binario por entrevistador, consenso y decisión del HM. Tres resultados posibles: Hire, No Hire, o "no encaja en este equipo → referido a otro" (team matching).
4. Comportamientos realistas de los entrevistadores:
   - controlan el ritmo e interrumpen cuando ya tienen la señal;
   - la gestión del tiempo cuenta como señal;
   - coding en dos partes, con follow-ups de producción y concurrencia y tests escritos por el candidato;
   - estilos de entrevistador variables.
5. Nuevas rondas: `ai-assisted-coding` (con un agente "AI pair" imperfecto a propósito), `partnership` (manager de un equipo socio) y la variante de PR review en `technical-screen`.
6. Cultura con el texto literal del memo vigente y señales de cultura en todas las etapas.
7. Contenido técnico anclado en publicaciones de Netflix (interleaving, CUPED, foundation model, semantic IDs, artwork personalization). Bancos basados en temas reportados, **no en preguntas filtradas**.
8. Aviso visible de que los loops varían por equipo.

## Fuentes

**Primarias (Netflix)**
- [Netflix culture memo]: https://jobs.netflix.com/culture (leído directamente) · PDF: https://jobs.netflix.com/netflix-culture.pdf
- [Netflix Research]: https://research.netflix.com/ (leído directamente) · archivo: https://research.netflix.com/archive
- [Netflix TechBlog interleaving]: https://netflixtechblog.com/using-interleaving-in-online-experiments-to-accelerate-algorithm-innovation-at-netflix-a04ee392ec55
- [Netflix TechBlog experimentation analysis]: https://netflixtechblog.com/reimagining-experimentation-analysis-at-netflix-71356393af21
- [Netflix CUPED paper]: https://www.researchgate.net/publication/305997925_Improving_the_Sensitivity_of_Online_Controlled_Experiments_Case_Studies_at_Netflix
- [arXiv 1910.03878]: https://arxiv.org/html/1910.03878 · [arXiv 2601.02764]: https://arxiv.org/pdf/2601.02764
- [ResearchGate artwork]: https://www.researchgate.net/publication/327953121_Artwork_personalization_at_netflix

**Primera mano (leídos directamente)**
- [Blind AI-assisted, jul 2026]: https://www.teamblind.com/post/netflix-ai-assisted-interview-7o1ukyfe
- [Blind DS final loop]: https://www.teamblind.com/post/netflix-final-interview-loop-experience-xbok7ivr
- [Blind RS recsys]: https://www.teamblind.com/post/Netflix-Interview-Research-Scientist-Zfg7kPNA
- [Blind ML Scientist]: https://www.teamblind.com/post/netflix-ml-scientist-interview-gazwxhe3
- [Blind RS vs MLE]: https://www.teamblind.com/post/Netflix-Research-Scientist-vs-MLE-vs-ML-Scientist-OUwTjGwq
- [Blind ML research intern]: https://www.teamblind.com/post/machine-learning-research-internship-interview-netflix-z4ssjk36
- [Blind messed up]: https://www.teamblind.com/post/netflix-messed-up-interview-t81cm5ma
- [Blind no-leetcode]: https://www.teamblind.com/post/netflix-interview-bullshit-jz014woq
- [Blind feedback 2018]: https://www.teamblind.com/post/interview-experience-with-netflix-fiyso5er
- [Blind HM gatekeeper] / [Blind no-optimal]: https://www.teamblind.com/post/netflix-interview-experience-j1j6tzh4
- [PracHub MLE PR review]: https://prachub.com/interview-experiences/netflix-machine-learning-engineer-interview-experience-ml-fundamentals-plus-a-production-pr-review-rejected
- [PracHub MLE infra]: https://prachub.com/interview-experiences/netflix-machine-learning-engineer-interview-experience-ml-infra-onsite-with-coding-stakeholder-chat-and-compute-allocation-design (solo el título; contenido de pago)
- [PracHub MLE VO2 portal]: https://prachub.com/interview-experiences/netflix-machine-learning-engineer-interview-experience-vo2-a-culture-bq-round-and-a-fullstack-ml-portal-design (solo el título)
- [PracHub MLE intern OA]: https://prachub.com/interview-experiences/netflix-intern-machine-learning-engineer-interview-experience-90-minute-oa-with-4-mc-and-2-coding-questions
- [PracHub DS intern OA]: https://prachub.com/interview-experiences/netflix-intern-data-scientist-interview-experience-a-75-minute-causal-inference-oa-that-left-me-guessing
- [PracHub DS 11 rondas]: https://prachub.com/interview-experiences/netflix-data-scientist-interview-experience-eleven-rounds-two-and-a-half-months-and-a-hiring-manager-swap
- [PracHub VO1 billboard]: https://prachub.com/interview-experiences/netflix-software-engineer-interview-experience-passed-vo1-with-a-billboard-rotation-coding-round-and-an-ml-job-scheduler-system-design
- [PracHub data platform]: https://prachub.com/interview-experiences/netflix-software-engineer-interview-experience-data-platform-loop-rejected-after-the-final-system-design-round
- [PracHub SWE open-book]: https://prachub.com/interview-experiences/netflix-software-engineer-interview-experience-an-open-book-coding-screen-that-still-ended-in-rejection

**Primera mano (solo extractos del buscador; 403)**
- [Glassdoor MLE]: https://www.glassdoor.com/Interview/Netflix-Machine-Learning-Engineer-Interview-Questions-EI_IE11891.0,7_KO8,33.htm
- [Glassdoor ML Intern]: https://www.glassdoor.com/Interview/Netflix-Machine-Learning-Intern-Interview-Questions-EI_IE11891.0,7_KO8,31.htm
- [Glassdoor Senior DS]: https://www.glassdoor.com/Interview/Netflix-Senior-Data-Scientist-Interview-Questions-EI_IE11891.0,7_KO8,29.htm
- [Glassdoor DS]: https://www.glassdoor.com/Interview/Netflix-Data-Scientist-US-Interview-Questions-EI_IE11891.0,7_KO8,22_IL.23,25_IN1.htm

**Guías de terceros**
- [interviewing.io]: https://interviewing.io/guides/hiring-process/netflix (leído directamente; basado en entrevistadores de Netflix, orientado a SWE)
- [Interview101]: https://www.interview101.com/interviews/netflix/machine-learning-engineer (leído directamente; comercial)
- [Levels.fyi MLE]: https://www.levels.fyi/companies/netflix/salaries/software-engineer/title/machine-learning-engineer (leído directamente)
- [Exponent MLE]: https://www.tryexponent.com/guides/netflix-machine-learning-engineer-interview → https://www.aced.io/guides/netflix-machine-learning-engineer-interview (leído directamente, 2026-10-24)
- [ZenML GenRec]: https://www.zenml.io/llmops-database/llm-native-recommendation-system-at-scale (resumen secundario leído directamente; el post de Netflix no)
- [Interview Query MLE]: https://www.interviewquery.com/interview-guides/netflix-machine-learning-engineer · [Interview Query RS]: https://www.interviewquery.com/interview-guides/netflix-research-scientist
- [Interview Kickstart MLE]: https://interviewkickstart.com/interview-questions/companies/netflix/machine-learning-engineer
- [Dataford MLE]: https://dataford.io/interview-guides/netflix/machine-learning-engineer
- [Prepfully DS]: https://prepfully.com/interview-guides/netflix-data-scientist
- [IGotAnOffer questions]: https://igotanoffer.com/en/advice/netflix-interview-questions
- [four-leaf]: https://four-leaf.ai/blog/netflix-hiring-process
- [DesignGurus levels]: https://www.designgurus.io/blog/netflix-software-engineer-levels
