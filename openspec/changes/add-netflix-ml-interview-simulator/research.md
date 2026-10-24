# Research: el proceso de entrevistas de ML en Netflix

Documento de soporte del change (no es un artefacto del schema). Recoge lo que se sabe públicamente, con qué confianza y qué decisiones de diseño se derivan. Fecha de la investigación: 2026-10-24.

**Método y límites.** Se hicieron búsquedas web amplias en guías de preparación, Glassdoor, Blind, PracHub, Levels.fyi, el Netflix Tech Blog, Netflix Research y la prensa sobre el memo de cultura. La red del entorno no permitió abrir las páginas directamente (WebFetch bloqueado), así que lo que sigue sale de los extractos que devolvió el buscador. Netflix publica muy poco sobre su proceso de selección: la mayoría de las fuentes son de terceros y anecdóticas. Confianza: **Alta** = fuente primaria de Netflix o consenso amplio; **Media** = varias fuentes de terceros coinciden; **Baja** = una sola fuente o fuentes contradictorias.

## 1. Estructura general

| Hallazgo | Confianza | Fuentes |
|---|---|---|
| Proceso en 3 bloques: recruiter screen → screen técnico y/o con el hiring manager → loop final (virtual onsite) de unas 4–6 sesiones. Duración total de 3 a 7 semanas. | Media | [Exponent MLE], [Cleverprep], [Dataford MLE], [IGotAnOffer], [Interview101 MLE] |
| El loop **varía mucho por equipo y nivel**; casi todas las fuentes recomiendan confirmar la estructura con el recruiter. | Alta | [Interview101 MLE], [Exponent MLE], [Blind analytics eng] |
| El hiring manager pesa mucho: la conversación sobre trabajo pasado "decide la mayoría de los resultados". | Media | [DesignGurus leetcode], [interviewing.io guide], [Exponent MLE] |
| Suele haber 1–2 **directores** en el loop (uno de la organización que contrata y otro de una organización socia). | Media | [Copilot Interview / interviewing.io], [Interview101 MLE] |
| **No hay hiring committee central**: el panel hace un debrief y el hiring manager ("informed captain") decide. Hace falta un consenso alto; un informe habla de "aprobación unánime del equipo". No hay escala de puntuación común a toda la empresa: es pass / no-pass. | Media | [four-leaf], [Copilot Interview], [Glassdoor DS], [Interview Query L5] |
| La cultura se evalúa **en todas las rondas**, no solo en la de cultura. | Media | [Prepfully DS], [Interview101 MLE] |
| El feedback al candidato es irregular: hay quien recibe feedback detallado del HM y quien no recibe respuesta. | Media | [Glassdoor MLE], [Glassdoor ML Intern], [Blind feedback] |

## 2. Etapas observadas y su contenido

### Recruiter screen (≈30 min) — Media
- "Why Netflix?" aparece casi siempre; una respuesta genérica no funciona y hay que vincularla a un problema técnico concreto ([IGotAnOffer questions], [JobJourney]).
- El recruiter suele mandar antes el memo de cultura ([JobJourney], [Coditioning]).
- La compensación se trata pronto ("top of market") y el recruiter puede dar la banda y preguntar expectativas ([Techscreen], [Ophy]).

### Hiring manager (45–60 min) — Media
- Conversación en profundidad sobre trabajo pasado y encaje con las necesidades inmediatas del equipo ([Exponent MLE], [DesignGurus leetcode]).
- En el caso de DS, un informe describe una ronda con hiring managers de dos equipos ([PracHub DS 11 rondas]).

### Screen técnico (40–60 min) — Media
- MLE (Glassdoor, feb 2026): **20 min de proyecto previo + 40 min de "ML coding"** ([Glassdoor ML Intern/MLE]).
- Coding práctico en Python: funciones de similitud, métricas de recomendación (Precision@K, NDCG@K), collaborative filtering con coseno sobre una matriz dispersa, sliding windows o hash maps sobre eventos. A veces Spark/PySpark ([Interview Query MLE], [Dataford MLE], [Interview Kickstart MLE]).
- RS: estadística y fundamentos de ML con coding breve en Python o SQL ([Interview Query RS]).
- DS: SQL en vivo sobre datos de visualización o suscriptores (window functions, cohortes, retención, sesionización) y, en una segunda ronda, SQL + caso ([Prepfully DS], [PracHub DS 11 rondas]).
- Algunas guías mencionan un **take-home** de modelado o analítica de producto que luego se presenta ([Interview101 MLE], [Glassdoor Senior DS]). Confianza baja para MLE; media para DS.

### Coding en el loop — Media
- Hay equipos que "no hacen LeetCode" y prefieren coding práctico del dominio, y otros que hacen LeetCode medium "con un giro práctico" ([interviewing.io guide], [Blind "no leetcode"]).
- A partir de senior se espera código de calidad de producción (manejo de errores, testabilidad) ([DataInterview MLE]).
- Una solución "not optimal" puede costar la oferta ([Blind SWE onsite]).

### Presentación — Media
- RS / intern de investigación: **panel presentation de 1 h** sobre la propia investigación, seguida de una conversación sobre el background ([Glassdoor ML Intern 2026], [Interview Query RS]).
- DS senior: presentación de un take-home (analítica de producto y experimentación) a dos data scientists, seguida de preguntas de estadística: varianza, bootstrap, efectos heterogéneos ([Glassdoor Senior DS]).
- Exponent menciona una charla técnica de 10–15 min en las rondas de cultura ([Aced/Exponent process]). Confianza baja.

### ML fundamentals / breadth — Media
- Bias-variance, regularización L1/L2, overfitting en GBDT (early stopping, profundidad, min_samples_leaf), embeddings a partir de co-watch, cold start, popularity bias, métricas de ranking (P@K, R@K, MAP, NDCG, cobertura, diversidad, serendipia) ([Interview Query MLE], [Dataford MLE]).

### ML system design (≈60 min, la ronda con más peso para MLE) — Media
- Prompts reportados: personalización dinámica de la homepage (filas), arquitectura de recomendación de vídeo (ingesta de eventos → feature store → two-tower → ranker → caché), Continue Watching, ranking de búsqueda personalizado, embeddings multimodales del catálogo con GenAI, predicción de binge-watching y reentrenamiento diario sobre petabytes ([Interview Kickstart MLE], [Exponent system design], [PracHub system design]).
- Peso estimado en un desglose: system design ~25 %, conducta/cultura ~33 %, ML depth ~25 %, coding ~17 % ([Exponent MLE]). Confianza baja (una sola fuente).

### ML depth (dominio) — Media
- Depende del equipo. Netflix Research lista: recomendación, RL, visión, NLP, optimización, causalidad e investigación operativa ([Netflix Research jobs], [Interview Query RS]). Ofertas recientes: LLM post-training, content understanding y Ads ([Built In RS L4/L5]).
- Contexto técnico actual: el **foundation model de recomendación** de Netflix (inspirado en LLMs, con leyes de escala) y su integración en la homepage y la búsqueda (2025–2026); la personalización de artwork con bandits y, más recientemente, con LLM post-training ([Netflix Research archive], [arXiv 2601.02764], [ResearchGate artwork]).

### Experimentación y A/B testing — Alta en DS, Media en MLE/RS
- Es "make-or-break" para DS: diseño de tests, power analysis, peeking (¿parar con un día significativo?), interferencia, sesgos, efectos heterogéneos y elección de la métrica primaria (p. ej. un test de artwork personalization) ([Prepfully DS], [Interview Query DS]).
- Prácticas de Netflix documentadas en fuentes primarias: **interleaving** como primera etapa para podar algoritmos de ranking antes del A/B, **CUPED** y post-estratificación para reducir varianza, **quasi-experimentos** geográficos y una plataforma de experimentación orientada a científicos ([Netflix TechBlog interleaving], [Netflix CUPED paper], [arXiv 1910.03878], [MarTech quasi]).

### Project deep dive — Media
- En un loop L5 reportado: "1 coding, 1 previous experience, 2 with directors" ([Glassdoor MLE]). Se espera hablar de sistemas de ML en producción que el candidato haya llevado de principio a fin ([InterviewBoost MLE]).

### Cultura — Alta (memo) / Media (formato de la ronda)
- Memo de junio de 2024, "The Best Work of Our Lives". Cuatro ideas: **Dream Team, People over Process, Uncomfortably Exciting, Great and Always Better**. Ocho valores: **selflessness, judgment, candor, creativity, courage, inclusion, curiosity, resilience** (candor, creativity y resilience son nuevos; salen communication, integrity, passion e innovation) ([Netflix culture PDF], [Medium twosapp], [Startups.co.uk]).
- **Keeper test** (texto del memo): "if X wanted to leave, would I fight to keep them?" y "knowing everything I know today, would I hire X again?". No se aplica a baches de corto plazo ([Benzinga], [Fortune 2024]).
- Otros conceptos: context not control, highly aligned / loosely coupled, informed captain, farming for dissent, disagree and commit ([Startups.co.uk], [SpaceComplexity behavioral]).
- Formato: preguntas conductuales directas con historias concretas: llevar la contraria a un stakeholder, decidir con datos incompletos, asumir un riesgo ([Interview101 MLE], [SpaceComplexity behavioral]).

## 3. Niveles — Media
- Netflix introdujo niveles formales en 2022. L4 ≈ SWE II (con más autonomía que un mid-level típico), **L5 = senior, el nivel núcleo** (dueño de punta a punta de un sistema o área), L6 = staff ([DesignGurus levels], [Levels.fyi MLE]). Las ofertas de ML aparecen como L4, L5 y L6.

## 4. Roles y loops de referencia (síntesis para el simulador)

| Rol | Screens | Loop final típico |
|---|---|---|
| ML Engineer | recruiter, hiring manager, technical screen (proyecto + ML coding) | coding, ml-system-design (peso máximo), ml-depth, project-deep-dive, culture (con director) |
| Research Scientist | recruiter, hiring manager, technical screen (stats/ML + coding breve) | presentation (research talk 1 h), ml-depth, ml-fundamentals, coding (ML), culture |
| Applied / Data Scientist | recruiter, hiring manager, technical screen (SQL + caso) | presentation (take-home), experimentation (decisiva), ml-fundamentals (caso de modelado), coding (SQL/pandas), culture/producto |

## 5. Implicaciones para el diseño

1. Catálogo de **11 etapas**, con un loop por defecto por rol y etapas opcionales (en lugar de 9 iguales para todos).
2. Se añaden `technical-screen` (formato mixto) y `presentation` (research talk o take-home readout, con material entregado antes).
3. Se sustituye el "hiring committee" por un **debrief con decisión del hiring manager**: cada entrevistador da pass / no-pass, se busca consenso alto, un "strong no" suele bloquear y el HM decide como informed captain.
4. Señales de cultura evaluadas **en todas las etapas**, no solo en `culture`.
5. La escala de 4 puntos por competencia es una herramienta pedagógica del simulador; la recomendación de cada entrevistador se expresa como pass / no-pass, que es como funciona el debrief real.
6. Contenido técnico anclado en prácticas documentadas por Netflix (interleaving, CUPED, quasi-experimentos, foundation model, artwork personalization). Banco de preguntas basado en temas reportados, **no en preguntas filtradas**.
7. Aviso visible: los loops reales varían por equipo; el simulador es una aproximación.

## Fuentes

- [Netflix culture PDF]: https://jobs.netflix.com/netflix-culture.pdf · memo actual: https://jobs.netflix.com/culture
- [Benzinga]: https://www.benzinga.com/general/entertainment/24/06/39470966/netflix-alters-keeper-test-in-corporate-culture-memo-managers-now-ask-would-i-fight-to-keep
- [Fortune 2024]: https://www.fortune.com/2024/06/25/netflix-managers-keeper-test-rehire-or-fire-staff
- [Medium twosapp]: https://medium.com/twosapp/netflixs-culture-core-principles-and-values-new-in-2024-35faeb9673da
- [Startups.co.uk]: https://startups.co.uk/news/netflix-culture-memo/
- [Netflix TechBlog interleaving]: https://netflixtechblog.com/using-interleaving-in-online-experiments-to-accelerate-algorithm-innovation-at-netflix-a04ee392ec55
- [Netflix TechBlog experimentation analysis]: https://netflixtechblog.com/reimagining-experimentation-analysis-at-netflix-71356393af21
- [Netflix CUPED paper]: https://www.researchgate.net/publication/305997925_Improving_the_Sensitivity_of_Online_Controlled_Experiments_Case_Studies_at_Netflix
- [arXiv 1910.03878]: https://arxiv.org/html/1910.03878
- [MarTech quasi]: https://martech.org/how-netflix-quasi-experiments-let-it-go-beyond-the-limitations-of-a-b-testing/
- [Netflix Research archive]: https://research.netflix.com/archive
- [arXiv 2601.02764]: https://arxiv.org/pdf/2601.02764
- [ResearchGate artwork]: https://www.researchgate.net/publication/327953121_Artwork_personalization_at_netflix
- [Built In RS L4/L5]: https://builtin.com/job/research-scientist-l4-machine-learning-and-inference-research-llm-post-training/7175170 · https://builtin.com/job/research-scientist-l5-content-understanding/7841888
- [Glassdoor MLE]: https://www.glassdoor.com/Interview/Netflix-Machine-Learning-Engineer-Interview-Questions-EI_IE11891.0,7_KO8,33.htm
- [Glassdoor ML Intern]: https://www.glassdoor.com/Interview/Netflix-Machine-Learning-Intern-Interview-Questions-EI_IE11891.0,7_KO8,31.htm
- [Glassdoor Senior DS]: https://www.glassdoor.com/Interview/Netflix-Senior-Data-Scientist-Interview-Questions-EI_IE11891.0,7_KO8,29.htm
- [Glassdoor DS]: https://www.glassdoor.com/Interview/Netflix-Data-Scientist-US-Interview-Questions-EI_IE11891.0,7_KO8,22_IL.23,25_IN1.htm
- [PracHub DS 11 rondas]: https://prachub.com/interview-experiences/netflix-data-scientist-interview-experience-eleven-rounds-two-and-a-half-months-and-a-hiring-manager-swap
- [PracHub system design]: https://prachub.com/companies/netflix/categories/system-design
- [Blind analytics eng]: https://www.teamblind.com/post/analytics-engineer-netflix-interview-experience-jnsw8gsx
- [Blind SWE onsite]: https://www.teamblind.com/post/netflix-interview-experience-j1j6tzh4
- [Blind "no leetcode"]: https://www.teamblind.com/post/netflix-interview-bullshit-jz014woq
- [Blind feedback]: https://www.teamblind.com/post/interview-experience-with-netflix-fiyso5er
- [interviewing.io guide]: https://interviewing.io/guides/hiring-process/netflix
- [Engineering Enablement]: https://engineeringenablement.substack.com/p/the-netflix-software-engineering
- [Exponent MLE]: https://www.tryexponent.com/guides/netflix-machine-learning-engineer-interview
- [Exponent system design]: https://www.tryexponent.com/blog/netflix-system-design-interview
- [Aced/Exponent process]: https://www.aced.io/blog/an-inside-look-into-the-netflix-interview-process
- [Interview Query MLE]: https://www.interviewquery.com/interview-guides/netflix-machine-learning-engineer
- [Interview Query RS]: https://www.interviewquery.com/interview-guides/netflix-research-scientist
- [Interview Query DS]: https://www.interviewquery.com/interview-guides/netflix-data-scientist
- [Interview Query L5]: https://www.interviewquery.com/interview-guides/netflix
- [Interview101 MLE]: https://www.interview101.com/interviews/netflix/machine-learning-engineer
- [Dataford MLE]: https://dataford.io/interview-guides/netflix/machine-learning-engineer
- [DataInterview MLE]: https://www.datainterview.com/blog/netflix-machine-learning-engineer-interview
- [Cleverprep]: https://www.cleverprep.com/companies/netflix/machine-learning-engineer
- [Interview Kickstart MLE]: https://interviewkickstart.com/interview-questions/companies/netflix/machine-learning-engineer
- [InterviewBoost MLE]: http://interviewboost.ai/interview-questions/netflix-machine-learning-engineer-interview-questions
- [Prepfully DS]: https://prepfully.com/interview-guides/netflix-data-scientist
- [IGotAnOffer]: https://igotanoffer.com/en/advice/netflix-interview-process
- [IGotAnOffer questions]: https://igotanoffer.com/en/advice/netflix-interview-questions
- [JobJourney]: https://www.jobjourney.pro/blog/netflix-interview-questions-guide
- [Coditioning]: https://www.coditioning.com/blog/501/netflix-swe-recruiter-screen
- [Techscreen]: https://techscreen.app/articles/netflix-technical-interview-process-2026
- [Ophy]: https://ophyai.com/blog/company-guides/netflix-interview-guide
- [four-leaf]: https://four-leaf.ai/blog/netflix-hiring-process
- [Copilot Interview]: https://copilotinterview.com/blog/netflix-interview-process
- [SpaceComplexity behavioral]: https://spacecomplexity.ai/blog/netflix-behavioral-interview-questions
- [DesignGurus leetcode]: https://www.designgurus.io/answers/detail/does-netflix-ask-leetcode-questions-in-interviews
- [DesignGurus levels]: https://www.designgurus.io/blog/netflix-software-engineer-levels
- [Levels.fyi MLE]: https://www.levels.fyi/companies/netflix/salaries/software-engineer/title/machine-learning-engineer
- [Netflix Research jobs]: https://research.netflix.com/
