# Sources and confidence

Evidence base for the simulator (summarized from the project research notes, last updated 2026-10-24).
Netflix publishes little about its process; most evidence is anecdotal and **varies by team and level**.
The simulated loop is an approximation: confirm the real structure with your recruiter.

**Confidence scale.** High = primary Netflix source or several matching first-hand accounts. Medium = several third-party
sources agree, or one first-hand account. Low = single or contradictory sources.

**Assumptions (not facts).**
- Every stage duration in `catalog.yaml` is an assumption derived from loosely reported formats.
- L4 and L6 descriptors are extrapolated from L5; L5 (senior) is the core level [DesignGurus levels].
- There is no hiring committee or common rating scale at Netflix: the decision is pass/fail in a live discussion led by the HM
  (informed captain) [interviewing.io]. The simulator's recommendation and debrief rules are pedagogical, not Netflix's.
- Interview Query guides that mention a hiring committee or a modeling take-home contradict primary sources and are not used for structure.

**Loop structure (all stages).** Recruiter -> HM screen -> technical screen -> onsite split into VO1 (general) and VO2 (team-specific),
with a cut between them (High for SWE, Medium for MLE, Low for RS/DS) [interviewing.io], [PracHub VO1 billboard], [Blind messed up].
One or two directors are usually in the loop [interviewing.io], [Glassdoor MLE].

## recruiter-screen

Confidence: High
Duration: about 30 min (assumption: reported as roughly 30 minutes; not published by Netflix)

Sources:
- Culture, background, reason for changing jobs and "Why Netflix?" [PracHub DS 11 rounds], [IGotAnOffer questions].
- Reading the culture memo before starting is expected [Blind ML research intern]; the memo itself states compensation is "personal top of market for the role and location" [Netflix culture memo].
- Do not cite salary as the motivation: managers read it as a red flag [Exponent MLE] (Low: single source).

## hm-screen

Confidence: High
Duration: about 30 min (assumption)

Sources:
- "Very chill", two-way surface questions; the HM sells Netflix because the onsite is demanding [interviewing.io].
- Acts as gatekeeper: checks culture fit and that the background covers the role [Blind HM gatekeeper].
- Some loops involve HMs from two teams [PracHub DS 11 rounds].

## technical-screen

Confidence: High
Duration: 45-60 min (assumption: 60 min used; the 75 min `oa` variant is an assumption based on 75-90 min intern OAs)

Sources:
- Format A (ML intern, Feb 2026): 20 min prior project + 40 min ML coding [Glassdoor ML Intern]. Internship loop; no direct full-time MLE report (Low-Medium).
- MLE full-time: LeetCode-style plus recsys design, 1 coding + 1 prior experience + 2 director chats (L5, 2024) [Glassdoor MLE].
- Format B (applied GenAI org, Sep 2026): 30 min ML fundamentals (KV cache, Q/K/V attention, L1 vs L2) + 30 min live production PR review [PracHub MLE PR review] (Medium: single account).
- RS: ML fundamentals/framing + coding in a language of choice [Blind RS recsys]; ML Scientist L5: ML knowledge, coding and problem framing [Blind ML Scientist].
- DS: two screens, conceptual statistics and SQL/Python programming [Blind DS final loop], [PracHub DS 11 rounds].
- OA formats (reference only): MLE 4 multiple-choice + 2 coding; DS causal inference + statistics [PracHub MLE intern OA], [PracHub DS intern OA].
- A modeling take-home before the onsite appears only in a commercial guide [Interview101] (Low for MLE).

## presentation

Confidence: Medium
Duration: 45-60 min (assumption: 45 min research talk; 60 min take-home; reports mention a 1 h panel)

Sources:
- RS / research intern: 1 h panel presentation about own research [Glassdoor ML Intern].
- Senior DS: presentation of a product analytics and experimentation take-home to two DS [Glassdoor Senior DS].
- Exponent mentions a 10-15 min talk on a technical topic of the candidate's choice [Exponent MLE]. The two-person panel is a simulator simplification.

## coding

Confidence: High
Duration: 60 min (assumption)

Sources:
- Depends on the team: "no LeetCode" or LC-medium with a practical twist written by Netflix engineers [interviewing.io], [Blind no-leetcode].
- Two parts: a problem, then a production-scale or concurrency extension if time remains [interviewing.io], [PracHub VO1 billboard].
- The candidate writes their own tests [PracHub SWE open-book]; a non-optimal solution can cost the offer [Blind no-optimal].
- Netflix-flavored problems: homepage row dedup, watch-history duplicates, billboard rotation, sliding windows [PracHub SWE open-book], [PracHub data platform], [PracHub VO1 billboard].
- ML coding: ranking metrics (P@K, NDCG@K), cosine similarity / CF on sparse matrices [Interview Kickstart MLE], [Dataford MLE]. Weighted random key is from [Exponent MLE].

## ai-assisted-coding

Confidence: Medium
Duration: 60 min (assumption)

Sources:
- New 2026 onsite round: work in a real codebase with AI tools while an interviewer is present; evaluates decomposition, instructions to the AI, verifying and rebutting its output, and extending it [Blind AI-assisted, Jul 2026] (single recent account).
- The simulator's imperfect AI pair (0-2 plausible flaws per repo) is a design choice, not a reported detail.

## ml-fundamentals

Confidence: Medium
Duration: 45 min (assumption)

Sources:
- Bias-variance, L1/L2, GBDT overfitting, co-watch embeddings, cold start, popularity bias, ranking metrics; in GenAI orgs KV cache and attention [Interview Query MLE], [PracHub MLE PR review].
- Exponent examples: CF, trees vs networks, bias-variance, post-deployment monitoring [Exponent MLE].
- `modeling-case` (DS) has no direct evidence; it is an optional simulator extension.
- Interview Query guides contradict primary sources on process structure (Low); only their topics are used.

## ml-system-design

Confidence: High
Duration: 60 min (assumption)

Sources:
- The round that weighs most; coding weighs least [interviewing.io], [Interview101].
- Questions are team-specific and hard; recurring themes: scale, availability, security; not generic product design [interviewing.io].
- The interviewer controls pace and interrupts once the signal is obtained; failing to finish the design sank a candidate [PracHub VO1 billboard], [PracHub data platform].
- Reported prompts: ML job scheduler, compute allocation, full-stack ML portal, homepage rows, artwork personalization, Continue Watching, personalized search, multimodal catalog embeddings [PracHub VO1 billboard], [PracHub MLE infra], [Interview Kickstart MLE].
- Netflix publications anchor the content: [Netflix TechBlog GenRec], [ResearchGate artwork]. Publications are discussion context; figures are never asked.

## experimentation

Confidence: High
Duration: 45 min (assumption)

Sources:
- Design, power, peeking, interference, heterogeneous effects, variance, bootstrap; ad frequency-cap sizing case [Glassdoor Senior DS], [PracHub DS 11 rounds], [Prepfully DS]. The frequency-cap case is not in the Glassdoor pages read (Low-Medium).
- Glassdoor DS reports: personalized row-ordering A/B with row overlap and retention; regression, type I/II errors, multiclass A/B, FDR; 2 case studies designing a full experiment [Glassdoor DS], [Glassdoor Senior DS].
- Netflix practices: interleaving as a first stage, CUPED / post-stratification, geo quasi-experiments, quantile bootstrap, quantile regression, heterogeneous effects [Netflix TechBlog interleaving], [Netflix TechBlog experimentation analysis], [Netflix CUPED paper], [arXiv 1910.03878].

## culture

Confidence: High
Duration: 45 min (assumption)

Sources:
- The memo (read directly) has 4 principles and 8 values (selflessness, judgment, candor, creativity, courage, inclusion, curiosity, resilience), the keeper test, context not control, informed captain, farming for dissent, disagree then commit [Netflix culture memo].
- The "Dream Team" interview is run by a director and is more intense (scale, accountability, open communication of concerns, high risk/high reward); not having read the memo "is a fail"; candidates must self-promote with metrics [interviewing.io].
- Culture signals are assessed in every round [Interview101], [Blind HM gatekeeper]. Directors sometimes leave 30 min for candidate questions [interviewing.io].

## ml-depth

Confidence: Medium
Duration: 45 min (assumption)

Sources:
- Netflix Research is not centralized; teams sit next to the business. Areas: Analytics, CV & Graphics, Consumer Insights, Encoding & Quality, Experimentation & Causal Inference, Machine Learning, ML Platform, NLP & Conversations, Recommendations [Netflix Research].
- Recsys anchors: GenRec (LLM-native ranker) [Netflix TechBlog GenRec]; semantic-ID LLM recommendation, Foundation Model in homepage and search, LLM-based artwork personalization [Netflix Research].
- Senior levels add an ML architecture deep dive [Interview Query MLE]. The domain list is the simulator's grouping of the research areas.

## project-deep-dive

Confidence: High
Duration: 45 min (assumption)

Sources:
- "Netflix goes into prior work experience more than other FAANGs": successes, failures, what you would do better; different people probe different parts; they look for Freedom & Responsibility [Blind HM gatekeeper].
- "Reverse system design": incisive questions on systems the candidate built, such as largest scale and how it was scaled [interviewing.io]; "1 previous experience" round in an L5 loop [Glassdoor MLE].

## partnership

Confidence: Medium
Duration: 45 min (assumption)

Sources:
- A manager from a partner team interviews in behavioral format about cross-team collaboration [PracHub data platform]; also "partner" director in an L5 MLE loop [Glassdoor MLE]; a "stakeholder chat" in a Feb 2026 MLE report [PracHub MLE infra].
- Exponent: almost always a partner manager from another team [Exponent MLE] (commercial guide).

## hm-onsite

Confidence: Medium
Duration: 45 min (assumption)

Sources:
- Second meeting with the HM in VO2 [Blind messed up], [PracHub data platform]; the HM acts as informed captain and decides after a live discussion; no hiring committee [interviewing.io], [four-leaf].
- Team matching: outcomes like "ok ratings but not a fit for this role; another HM is interested" [Blind messed up], [interviewing.io]. The simulator maps this to the `referred` outcome.

## Reference list

Primary (Netflix)
- [Netflix culture memo]: https://jobs.netflix.com/culture
- [Netflix Research]: https://research.netflix.com/
- [Netflix TechBlog interleaving]: https://netflixtechblog.com/interleaving-in-online-experiments-at-netflix-a04ee392ec55
- [Netflix TechBlog experimentation analysis]: https://netflixtechblog.com/reimagining-experimentation-analysis-at-netflix-71356393af21
- [Netflix TechBlog GenRec]: https://netflixtechblog.com/genrec-towards-llm-native-recommendation-at-netflix-f20be6f643e3
- [Netflix CUPED paper]: https://www.researchgate.net/publication/305997925_Improving_the_Sensitivity_of_Online_Controlled_Experiments_Case_Studies_at_Netflix
- [arXiv 1910.03878]: https://arxiv.org/html/1910.03878
- [ResearchGate artwork]: https://www.researchgate.net/publication/327953121_Artwork_personalization_at_netflix

First hand
- [Blind AI-assisted, Jul 2026]: https://www.teamblind.com/post/netflix-ai-assisted-interview-7o1ukyfe
- [Blind DS final loop]: https://www.teamblind.com/post/netflix-final-interview-loop-experience-xbok7ivr
- [Blind RS recsys]: https://www.teamblind.com/post/Netflix-Interview-Research-Scientist-Zfg7kPNA
- [Blind ML Scientist]: https://www.teamblind.com/post/netflix-ml-scientist-interview-gazwxhe3
- [Blind ML research intern]: https://www.teamblind.com/post/machine-learning-research-internship-interview-netflix-z4ssjk36
- [Blind messed up]: https://www.teamblind.com/post/netflix-messed-up-interview-t81cm5ma
- [Blind no-leetcode]: https://www.teamblind.com/post/netflix-interview-bullshit-jz014woq
- [Blind HM gatekeeper] / [Blind no-optimal]: https://www.teamblind.com/post/netflix-interview-experience-j1j6tzh4
- [PracHub MLE PR review]: https://prachub.com/interview-experiences/netflix-machine-learning-engineer-interview-experience-ml-fundamentals-plus-a-production-pr-review-rejected
- [PracHub DS 11 rounds]: https://prachub.com/interview-experiences/netflix-data-scientist-interview-experience-eleven-rounds-two-and-a-half-months-and-a-hiring-manager-swap
- [PracHub VO1 billboard]: https://prachub.com/interview-experiences/netflix-software-engineer-interview-experience-passed-vo1-with-a-billboard-rotation-coding-round-and-an-ml-job-scheduler-system-design
- [PracHub data platform]: https://prachub.com/interview-experiences/netflix-software-engineer-interview-experience-data-platform-loop-rejected-after-the-final-system-design-round
- [PracHub SWE open-book]: https://prachub.com/interview-experiences/netflix-software-engineer-interview-experience-an-open-book-coding-screen-that-still-ended-in-rejection
- [PracHub MLE infra], [PracHub MLE intern OA], [PracHub DS intern OA]: prachub.com (titles and summaries only)
- [Glassdoor MLE], [Glassdoor ML Intern], [Glassdoor Senior DS], [Glassdoor DS]: glassdoor.com interview pages for Netflix (read Oct 2026; not every page)

Third-party guides
- [interviewing.io]: https://interviewing.io/guides/hiring-process/netflix
- [Interview101]: https://www.interview101.com/interviews/netflix/machine-learning-engineer (commercial)
- [Exponent MLE]: https://www.tryexponent.com/guides/netflix-machine-learning-engineer-interview (commercial)
- [Interview Query MLE] / [Interview Query RS]: https://www.interviewquery.com/interview-guides/netflix-machine-learning-engineer (Low, see assumptions)
- [Interview Kickstart MLE], [Dataford MLE], [Prepfully DS], [IGotAnOffer questions], [four-leaf], [DesignGurus levels]
