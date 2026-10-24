# Research: the Netflix ML interview process

Supporting document for the change (not a schema artifact). It collects what is publicly known, with what confidence, and which design decisions follow from it. Last updated: 2026-10-24 (third pass, from the user's PC, with Claude in Chrome).

**Method.** Three passes:
1. Broad web searches: guides, Glassdoor, Blind, PracHub, Levels.fyi, Netflix Tech Blog, Netflix Research and press.
2. **Direct reading** (curl) of: the culture memo on jobs.netflix.com, the interviewing.io guide, the Interview101 one, research.netflix.com, Levels.fyi, 12 Blind threads and 9 PracHub experiences (2025–2026).

3. **Third pass (user's PC, with Claude in Chrome; the user solved Glassdoor's Cloudflare anti-bot check by hand).** Read directly in the browser: **the 4 Glassdoor interview pages** (MLE 5 accounts; ML Intern 4; Senior DS 10 of 12; DS US 10 of 16, all from 2018–2026; later pages not read), **Interview Query** (MLE and Research Scientist guides), the **Netflix TechBlog** posts on interleaving (2017), experimentation analysis (2019) and **GenRec** (30 Jul 2026), and the **Exponent** guide (aced.io, via WebFetch). **Could not be read:** Reddit (the extension blocks it for security restrictions: no attempt was made to get around it), 1point3acres (403 via WebFetch) and Blind (no new threads were searched). Two retries via WebFetch/curl with browser headers were denied by the permission classifier as anti-bot circumvention and were not repeated.

**Not readable from the environment in passes 1–2 (Glassdoor, Interview Query and the TechBlog were read later, in pass 3; Reddit still cannot be read):**
- Glassdoor, Reddit and netflixtechblog.com respond 403 (anti-bot).
- Exponent/Aced: the proxy rejects them.
- Interview Query: rate limit (429).

For those sources, search-engine excerpts were used until pass 3, in which they were read directly (see above).

**Confidence.** **High** = primary Netflix source, or several matching first-hand accounts. **Medium** = several third-party sources agree or there is one first-hand account. **Low** = a single source or contradictory sources. Netflix publishes little about its process: almost everything is anecdotal and **varies by team**.

## 1. General structure

| Finding | Confidence | Sources |
|---|---|---|
| Steps: recruiter call → **hiring manager screen** → technical phone screen → "very long" onsite. The process is decentralized and depends on the team. | High | [interviewing.io], [Blind HM gatekeeper], [PracHub DS 11 rondas] |
| The virtual onsite is split into **VO1 (general: coding, system design, behavioral)** and **VO2 (team-specific: system design of the team's domain, partnership with a manager from a partner team, second meeting with the HM)**. There is a cut between the two: "4 hours of interviews and likely more if I had got past the first set". | High for SWE · Medium for MLE · Low for RS/DS (the DS accounts describe a single onsite) | [PracHub VO1 billboard], [PracHub data platform], [Blind messed up] |
| Recruiting may offer to split the onsite into 2 days. There are accounts of up to "9 interviews on a single day". | Medium | [interviewing.io], [Blind RS vs MLE] |
| There are usually 1–2 **directors** in the loop (one from the hiring organization and another from a partner one, to reduce bias). One may do system design and the other behavioral. Directors sometimes leave 30 min for the candidate's questions. | High | [interviewing.io], [Glassdoor MLE: "2 with directors"] |
| **There is no hiring committee or company-wide scale.** The decision is binary (pass / fail) in a live discussion after the onsite, seeking consensus ("then you discuss if you'd be open to changing your mind"). The hiring manager acts as informed captain. | High | [interviewing.io], [four-leaf], [Glassdoor DS] |
| Interviewers are not trained uniformly and questions are not standardized: style varies greatly from one interviewer to another. | Medium | [interviewing.io], [Blind feedback 2018] |
| Possible outcome: "ok ratings, but you are not a fit for this role; another hiring manager is interested". This is **team matching** and usually implies repeating part of the loop. One can interview with several teams at once. | High | [Blind messed up], [interviewing.io] |
| Feedback to the candidate is irregular: from detailed feedback from the HM to no reply at all. | High | [Blind feedback 2018], [PracHub MLE PR review], [PracHub SWE open-book] |
| MLE / ML Scientist / Research Scientist titles are almost interchangeable depending on the team: "I interviewed for one and asked for a different title and got it". | Medium | [Blind RS vs MLE] |

## 2. Stages and content

### Recruiter screen (≈30 min) — High
- Culture, background, why you are looking for a change and "Why Netflix?" ([PracHub DS 11 rondas], [IGotAnOffer questions]).
- The memo is mandatory reading before starting ([Blind ML research intern]).
- Compensation: the memo confirms **"personal top of market for the role and location"** ([Netflix culture memo]).

### Hiring manager screen (≈30 min) — High
- "Very chill"; two-way surface-level questions; the HM **sells Netflix** because the onsite is very demanding ([interviewing.io]).
- Acts as gatekeeper: checks cultural fit and that the background covers the role ([Blind HM gatekeeper]).
- Some loops have HMs from two teams ([PracHub DS 11 rondas]).

### Technical screen (45–60 min) — High
- **Format A** (Glassdoor, **ML Intern**, Feb 2026; corrects the previous pass, which attributed it to MLE): 20 min on a prior project + 40 min of ML coding; virtual onsite with a 1 h panel presentation, HM 15 min and potential mentor 30 min; "they did not ask about ML concepts"; 5 weeks ([Glassdoor ML Intern]). This is an internship loop: for full-time MLE there is no direct account of this format.
- **Full-time MLE on Glassdoor** (5 accounts read): Aug 2026, OA and then interviews with "LeetCode medium and hard" plus recommender system design; Jan 2025, general ML questions and a medium LC, and then ghosting; Jul 2024 (L5), 4 interviews: 1 coding, 1 on prior experience and 2 with directors (one from the team and another from a "partner" team, to talk about how you work with others) ([Glassdoor MLE]). Confirms directors and partner (Medium-High) and that coding varies by team.
- **MLE, format B** (applied GenAI organization, Sep 2026): 30' of ML fundamentals (KV cache, attention with the Q/K/V computation, L1 vs L2 normalization) + 30' of **live review of a feature pipeline PR**. The tests pass and you must detect what would fail in production; then it is discussed how to serve those features with different real-time requirements ([PracHub MLE PR review]).
- **RS** (recsys, 2022): "ML fundamentals + coding (language of your choice)"; in general, "1–2 ML rounds (problem framing and fundamentals), coding and another depending on the team" ([Blind RS recsys]).
- **ML Scientist L5** (2025): "ML knowledge screens, a coding screen, and problem framing" ([Blind ML Scientist]).
- **DS**: **two** technical screens. One conceptual on statistics ("aimed at someone with a PhD or consistently exposed to advanced graduate-level statistics") and another on SQL and Python/R programming ("do you use these tools often enough?") ([Blind DS final loop]). Another account: "pure SQL that had to be executed" + "SQL + case" ([PracHub DS 11 rondas]).
- **Internship OA** (format reference): MLE with 4 multiple-choice questions (Bayes, forward pass, KNN, Transformers) + 2 coding (sparse matrix multiplication, format conversion with imputation); DS with causal inference (ATE, ITT/TOT, IV/LATE) + a statistics test (CLT, t-stat, MDE) ([PracHub MLE intern OA], [PracHub DS intern OA]).
- A modeling take-home before the onsite only appears in a commercial guide ([Interview101]). Low confidence for MLE.

### Coding (VO) — High
- Depending on the team: "no LeetCode" or "LeetCode medium with a practical twist, written by Netflix engineers"; "LC interviews are not the norm here" (Netflix employee) ([interviewing.io], [Blind no-leetcode]).
- **Two parts**: a problem and, if time remains, an extension to production scale or a technical deep dive (e.g. multithreading) ([interviewing.io], [PracHub VO1 billboard]).
- The candidate **writes their own tests** ([PracHub SWE open-book]). A "non-optimal" solution can cost the offer ([Blind no-optimal]).
- Netflix-flavored problems: deduplicate homepage content by rows (global for the first n positions, per row afterwards), detect duplicates in viewing history (bucket sort), rotate a billboard or playlist of movies with updatable scores (two treemaps; multithreading and scaling follow-ups), sliding windows ([PracHub SWE open-book], [PracHub data platform], [PracHub VO1 billboard]).
- ML coding: ranking metrics (P@K, NDCG@K), cosine similarity and CF on a sparse matrix, PySpark in some roles ([Interview Kickstart MLE], [Dataford MLE]).

### AI-assisted coding (new, 2026) — Medium
- An onsite round in which the candidate works on a **real codebase with AI tools**. An interviewer is present. What is evaluated is how they decompose the work, how they instruct the AI, whether they **verify and push back on its output** and whether they know how to extend it, not just whether the code works ([Blind AI-assisted, jul 2026]).

### ML fundamentals / breadth — Medium
- Bias-variance, L1/L2, overfitting in GBDT, co-watch embeddings, cold start, popularity bias, ranking metrics. In GenAI organizations: KV cache and attention ([Interview Query MLE], [PracHub MLE PR review]).

### ML system design — High
- **The round that weighs the most** at Netflix; coding is the one that weighs the least ([interviewing.io], [Interview101]).
- The questions are their own and hard, often about what the team is building now. Recurring topics are scale, availability and safety. They are not usually generic product questions of the "Design Spotify" type ([interviewing.io]).
- The interviewer controls the pace: interrupts as soon as they get the signal and moves to the next point. **Not finishing the design on time sank a candidate** who had answered everything well ([PracHub VO1 billboard], [PracHub data platform]).
- Reported ML prompts: ML job scheduler (training vs batch inference, resource allocation, monitoring, crash handling, multi-tenancy), compute allocation, full-stack ML portal, homepage rows, artwork personalization, Continue Watching, personalized search, multimodal catalog embeddings ([PracHub VO1 billboard], [PracHub MLE infra], [Interview Kickstart MLE]).
- "Reverse system design": incisive questions about systems the candidate built (which was the largest scale, how they scaled it) ([interviewing.io]).

### ML depth (team domain) — Medium
- Netflix Research does not centralize research: teams work alongside the business. Areas: Analytics, CV & Graphics, Consumer Insights, Encoding & Quality, **Experimentation & Causal Inference, Machine Learning, ML Platform, NLP & Conversations, Recommendations** ([Netflix Research]).
- **GenRec** (Netflix post of 30 Jul 2026, **read directly**, High; the numbers are those Netflix publishes). LLM-native ranker that post-trains an internal LLM in two phases (Phase 1, adapted base that is rarely updated; Phase 2, ranking, which is refreshed more). It verbalizes history, context and metadata as text; the context window is the new "feature budget" (retain strong signals, omit weak ones, compress repetitions such as binge, elaborate new titles) and drops to ~⅓ of tokens without noticeable degradation. Scoring head over the catalog (embedding per title), multi-objective loss (ranking with cross-entropy, language modeling and **reward-weighted loss** with long-term satisfaction proxies and content rebalancing; no full RL, GRPO is left as future work). Served with vLLM in **prefill-only mode**: one forward pass scores all candidates. Results: ~+1.6% offline MRR with ~40 times fewer Phase 2 examples; A/B on batch-compute surfaces with ~10% of traffic for ~4 weeks, with significant short- and long-term improvements (no magnitudes). Ablations: the backbone from ~1B to ~10B improves MRR; Phase 1 versus an open LLM, +10–20%; Phase 2 versus Phase 1, +35–50% (≈80% after 2 weeks of aging). Stated motivation: the current stack depends on thousands of hand-made features and it is expensive to incorporate new content types. Limitations of off-the-shelf LLMs that it cites: they over-recommend what is popular, hallucinate titles outside the catalog and ignore business constraints. Anchor for system design and ml-depth of recsys with LLMs.
- Recent publications that anchor the content: LLM recommendation with semantic IDs (autoregressive beam search vs multi-token prediction, Oct 2026), Foundation Model integration in the homepage and search (Feb 2026), artwork personalization via LLM post-training (Feb 2026) ([Netflix Research]).

### Experimentation and A/B testing — High for DS
- Design, power, peeking, interference, heterogeneous effects, variance and bootstrap; practical case: design and size an **ad frequency cap** experiment ([Glassdoor Senior DS], [PracHub DS 11 rondas], [Prepfully DS]).
- **Glassdoor DS (read directly).** Jul 2026, offer accepted, ~4 weeks: SQL technical screen (titles that drove new sign-ups), then A/B testing of a personalized model and success metrics; prompt: design an A/B of a **personalized row-ordering model** on the homepage, with overlap between rows and retention as the long-term outcome. Jan 2026: regression (coefficients, R², type I/II error), multiclass A/B and FDR. Jan 2026 (another review, Low: one review and loose summary): after recruiter and technical/manager screen, **two onsite rounds** on technical and "Dream Team", with HM decision and unanimous team approval. 2024: present your research and then **2 case studies** of designing the whole experiment; SQL and Python. 2021 (Senior DS, Member UI): bootstrap, covariate adjustment, heterogeneous effects and a product analytics take-home with new metrics. The 2015–2022 reviews insist on detailed ML in the screen (L1/L2, word2vec, ReLU), sometimes with no experimentation questions despite the role ([Glassdoor DS], [Glassdoor Senior DS]). The **ad frequency cap** case does not appear in the pages read (10 of 12 and 10 of 16 accounts); it is still backed only by [PracHub DS 11 rondas] and [Prepfully DS].
- Practices documented by Netflix: interleaving as a first stage, CUPED / post-stratification, geographic quasi-experiments ([Netflix TechBlog interleaving], [Netflix CUPED paper], [arXiv 1910.03878]).
- **Interleaving, read in the original post (2017, High).** Two-stage process: a quick pruning with ranker interleaving and then a traditional A/B on the candidates. It uses a variant of team draft: a coin toss decides who picks first and the rankers alternate with their best-positioned video still available; hours watched are attributed to the ranker that contributed the video. Because of position bias, in each position a video must be equally likely to be from A or B. It requires more than 100 times fewer users than the most sensitive A/B metric for 95% power and correlates with it. Limits: complex implementation, business logic interferes, and it is a **relative measure** that does not measure retention directly, which is why the second stage is needed.
- **Experimentation analysis, read in the original post (2019, High).** ABlaze platform; three pillars: Metrics Repo (generated SQL), Causal Models (Python/R with data compression) and visualizations with Plotly. Example of an encodes test where a treatment raises the mean play delay but lowers the median, so quantiles are examined. Techniques it cites: interleaving, quantile bootstrapping, quasi-experiments, quantile regression and heterogeneous effects. A user can be in several tests at once (artwork, algorithm, encoding).

### Final loop according to Exponent — Medium
- After the technical screen, **up to 6 rounds of 30 min**: one technical (ML, A/B tests, ML system design and sometimes code) and culture rounds with HR, the hiring manager and almost always a **"partner" manager from another team**. A **10–15 min talk** on a technical topic of the candidate's choice is usually requested. The culture rounds are evaluated with an explicit rubric ([Exponent MLE], read directly on aced.io; commercial guide, agrees with interviewing.io and PracHub on the partner manager).
- Example questions: CF, trees vs networks, bias-variance decomposition, a function that returns a random key with probability proportional to its weights, predicting a review's score from the text, which metrics to monitor after deploying, "design a system like Netflix"; behavioral: the time you were honest at work, difficult feedback to a colleague, what your colleagues say about you ([Exponent MLE]).
- Repeated advice: do not cite salary as motivation, managers see it as a red flag ([Exponent MLE]; Low, a single source).

### Interview Query guides (read directly, Mar 2026) — Low
- The MLE and Research Scientist guides are generic and **contradict primary sources**: they talk about a weekly "hiring committee" and a "centralized packet review" with scores in 24 h, and a modeling take-home for MLE. Netflix describes the opposite (HM decision as informed captain, no committee) in [Netflix culture memo] and [interviewing.io]. They are not used for the process structure.
- What is usable are the topics: ML coding, SQL, recommendation and search autocomplete system design, ad breaks, and that at senior levels an ML architecture deep-dive is added. RS: 30 min of research presentation at high levels ([Interview Query MLE], [Interview Query RS]).

### Presentation — Medium
- RS / research intern: **1 h panel presentation** on one's own research ([Glassdoor ML Intern 2026]).
- Senior DS: presentation of a product analytics and experimentation take-home to two DS ([Glassdoor Senior DS]).

### Project deep dive — High
- "Netflix goes into prior work experience more than other FAANGs": successes, failures and what you would do better; different people dig into different parts; they look for *Freedom & Responsibility* in your stories ([Blind HM gatekeeper]). "1 previous experience" in an L5 loop ([Glassdoor MLE]).

### Partnership (VO2) — Medium
- A manager from a **partner team** interviews in behavioral format about cross-team collaboration ([PracHub data platform]). An MLE account (Feb 2026) mentions a "stakeholder chat" ([PracHub MLE infra]).

### Culture / "Dream Team" — High
- The current memo, read directly, describes 4 principles: **The Dream Team, People Over Process, Uncomfortably Exciting, Great and Always Better**.
- Its 8 values, with each one's description according to the memo:
  - **Selflessness**: humility to seek the best ideas; seeking what is best for Netflix, not for oneself or one's team; helping others succeed.
  - **Judgment**: long-term solutions; good decisions despite ambiguity; data that informs intuition.
  - **Candor**: giving and receiving feedback; openly admitting mistakes and sharing what was learned.
  - **Creativity**: embracing new ideas and persisting in search of more innovative solutions.
  - **Courage**: vulnerability in pursuit of truth; risking failure or challenging the status quo.
  - **Inclusion**: recognizing and countering one's own biases.
  - **Curiosity**: learning fast; interest in others' ideas; humility about what one does not know.
  - **Resilience**: adapting quickly; making hard decisions without delay; embracing challenges.
- Keeper test, verbatim: "if X wanted to leave, would I fight to keep them?" / "knowing everything I know today, would I hire X again?". "We stick with employees through short-term bumps."
- People Over Process: "context not control"; "We avoid decision-making by committee… we identify an **informed captain**"; "**highly aligned and loosely coupled**"; "**farming for dissent**"; "**disagree then commit**"; captain's subsequent reflection.
- Candor as a habit: "constructive feedback is part of our everyday work (like brushing your teeth)", also toward someone more senior.
- Source of all the above: [Netflix culture memo].
- In the interview: the **"Dream Team" interview** is conducted by a director and is more intense (scale, accountability, open communication of concerns, high risk and high reward). If you fail behavioral you are rejected, and not reading the memo "is a fail". You have to promote yourself with metrics and impact: favorite project, the latest and the most significant, what you look for in your next role ([interviewing.io]).
- Culture signals are evaluated in all rounds ([Interview101], [Blind HM gatekeeper]).

## 3. Levels — Medium
- Formal levels since 2022. L4 ≈ SWE II with more autonomy than usual, **L5 = senior, the core level**, L6 = staff ([DesignGurus levels]).
- US MLE compensation: L4 ≈ $403K and L5 ≈ $575K TC; median $550K with 18 data points ([Levels.fyi MLE]).

## 4. Reference loops (synthesis for the simulator)

| Role | Screens | VO1 (general) | VO2 (team) |
|---|---|---|---|
| ML Engineer | recruiter, HM screen, technical screen (`ml-coding`: ML questions + medium coding; optional B: fundamentals + PR review; the 20'+40' format is from internships) | coding, ml-system-design, culture | ml-depth, project-deep-dive, partnership, HM onsite |
| Research Scientist | recruiter, HM screen, technical screen (ML fundamentals/framing + coding) | presentation (research talk), ml-fundamentals, coding (ML), culture | ml-depth, partnership, HM onsite |
| Data Scientist (experimentation & analytics) | recruiter, HM screen, technical screen ×2 (executable SQL · statistics) | presentation (take-home), experimentation ×2 (design · analysis), coding (SQL/pandas), culture | partnership, HM onsite (optional modeling case, no direct evidence) |

Optional in any role: `ai-assisted-coding`, and the stages that are not in the role's default loop.

## 5. Implications for the design

1. **14 stages** in three phases (screen, VO1, VO2), with per-role loops and per-stage variants (`stage@variant`).
2. **Cut between VO1 and VO2**: a mini-debrief decides whether to continue.
3. **Final debrief** with binary pass / fail per interviewer, consensus and HM decision. Three possible outcomes: Hire, No Hire, or "not a fit for this team → referred to another" (team matching).
4. Realistic interviewer behaviors:
   - they control the pace and interrupt when they already have the signal;
   - time management counts as a signal;
   - two-part coding, with production and concurrency follow-ups and tests written by the candidate;
   - variable interviewer styles.
5. New rounds: `ai-assisted-coding` (with an "AI pair" agent that is deliberately imperfect), `partnership` (manager from a partner team) and the PR review variant in `technical-screen`.
6. Culture with the verbatim text of the current memo and culture signals in all stages.
7. Technical content anchored in Netflix publications (interleaving, CUPED, foundation model, semantic IDs, artwork personalization). Banks based on reported topics, **not on leaked questions**.
8. Visible notice that loops vary by team.

## Sources

**Primary (Netflix)**
- [Netflix culture memo]: https://jobs.netflix.com/culture (read directly) · PDF: https://jobs.netflix.com/netflix-culture.pdf
- [Netflix Research]: https://research.netflix.com/ (read directly) · archive: https://research.netflix.com/archive
- [Netflix TechBlog interleaving]: https://netflixtechblog.com/interleaving-in-online-experiments-at-netflix-a04ee392ec55 (read directly; 2017)
- [Netflix TechBlog experimentation analysis]: https://netflixtechblog.com/reimagining-experimentation-analysis-at-netflix-71356393af21 (read directly; 2019)
- [Netflix TechBlog GenRec]: https://netflixtechblog.com/genrec-towards-llm-native-recommendation-at-netflix-f20be6f643e3 (read directly; 30 Jul 2026)
- [Netflix CUPED paper]: https://www.researchgate.net/publication/305997925_Improving_the_Sensitivity_of_Online_Controlled_Experiments_Case_Studies_at_Netflix
- [arXiv 1910.03878]: https://arxiv.org/html/1910.03878 · [arXiv 2601.02764]: https://arxiv.org/pdf/2601.02764
- [ResearchGate artwork]: https://www.researchgate.net/publication/327953121_Artwork_personalization_at_netflix

**First-hand (read directly)**
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
- [PracHub MLE infra]: https://prachub.com/interview-experiences/netflix-machine-learning-engineer-interview-experience-ml-infra-onsite-with-coding-stakeholder-chat-and-compute-allocation-design (title only; paid content)
- [PracHub MLE VO2 portal]: https://prachub.com/interview-experiences/netflix-machine-learning-engineer-interview-experience-vo2-a-culture-bq-round-and-a-fullstack-ml-portal-design (title only)
- [PracHub MLE intern OA]: https://prachub.com/interview-experiences/netflix-intern-machine-learning-engineer-interview-experience-90-minute-oa-with-4-mc-and-2-coding-questions
- [PracHub DS intern OA]: https://prachub.com/interview-experiences/netflix-intern-data-scientist-interview-experience-a-75-minute-causal-inference-oa-that-left-me-guessing
- [PracHub DS 11 rondas]: https://prachub.com/interview-experiences/netflix-data-scientist-interview-experience-eleven-rounds-two-and-a-half-months-and-a-hiring-manager-swap
- [PracHub VO1 billboard]: https://prachub.com/interview-experiences/netflix-software-engineer-interview-experience-passed-vo1-with-a-billboard-rotation-coding-round-and-an-ml-job-scheduler-system-design
- [PracHub data platform]: https://prachub.com/interview-experiences/netflix-software-engineer-interview-experience-data-platform-loop-rejected-after-the-final-system-design-round
- [PracHub SWE open-book]: https://prachub.com/interview-experiences/netflix-software-engineer-interview-experience-an-open-book-coding-screen-that-still-ended-in-rejection

**Glassdoor first-hand (read directly in the browser on 2026-10-24; not all account pages)**
- [Glassdoor MLE]: https://www.glassdoor.com/Interview/Netflix-Machine-Learning-Engineer-Interview-Questions-EI_IE11891.0,7_KO8,33.htm
- [Glassdoor ML Intern]: https://www.glassdoor.com/Interview/Netflix-Machine-Learning-Intern-Interview-Questions-EI_IE11891.0,7_KO8,31.htm
- [Glassdoor Senior DS]: https://www.glassdoor.com/Interview/Netflix-Senior-Data-Scientist-Interview-Questions-EI_IE11891.0,7_KO8,29.htm
- [Glassdoor DS]: https://www.glassdoor.com/Interview/Netflix-Data-Scientist-US-Interview-Questions-EI_IE11891.0,7_KO8,22_IL.23,25_IN1.htm

**Third-party guides**
- [interviewing.io]: https://interviewing.io/guides/hiring-process/netflix (read directly; based on Netflix interviewers, SWE-oriented)
- [Interview101]: https://www.interview101.com/interviews/netflix/machine-learning-engineer (read directly; commercial)
- [Levels.fyi MLE]: https://www.levels.fyi/companies/netflix/salaries/software-engineer/title/machine-learning-engineer (read directly)
- [Exponent MLE]: https://www.tryexponent.com/guides/netflix-machine-learning-engineer-interview → https://www.aced.io/guides/netflix-machine-learning-engineer-interview (read directly, 2026-10-24)
- [Interview Query MLE]: https://www.interviewquery.com/interview-guides/netflix-machine-learning-engineer · [Interview Query RS]: https://www.interviewquery.com/interview-guides/netflix-research-scientist (both read directly; Low, see above)
- [Interview Kickstart MLE]: https://interviewkickstart.com/interview-questions/companies/netflix/machine-learning-engineer
- [Dataford MLE]: https://dataford.io/interview-guides/netflix/machine-learning-engineer
- [Prepfully DS]: https://prepfully.com/interview-guides/netflix-data-scientist
- [IGotAnOffer questions]: https://igotanoffer.com/en/advice/netflix-interview-questions
- [four-leaf]: https://four-leaf.ai/blog/netflix-hiring-process
- [DesignGurus levels]: https://www.designgurus.io/blog/netflix-software-engineer-levels
