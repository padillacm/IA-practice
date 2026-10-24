# Question bank: ml-depth

Driven by the session domain. Netflix Research areas map to the domains (research.md 2 ML depth). Prompts are original
and built from those areas and from Netflix-published practices. Publications are discussion context; never ask for their
figures. Each main question carries a follow-up chain ordered by increasing depth; stop the chain at the candidate's
limit. Items tagged L6 add architecture deep-dive and cross-team scope.

## Domain recsys

### ml-depth-recsys-01
```yaml
roles: [mle, rs]
levels: [L4, L5, L6]
variant: default
domain: recsys
kind: main
signal_points:
  - frames ranking as an objective choice (pointwise, pairwise, listwise) tied to what is shown and consumed
  - identifies position bias and exposure bias in logged data and corrects or randomizes for them
  - explains the offline-to-online gap and plans interleaving then A/B validation
  - names long-term satisfaction versus short-term engagement and a proxy for it
```
You own a ranker for a homepage row. Taking it from a logistic model on hand-made features to something much richer,
what objective do you train and how do you know it improves members' experience?

Follow-ups:
- Your logs only contain what the old ranker showed. What does that do to the labels and what do you do about it?
- Pairwise or listwise loss: what changes in the gradient and in what the model optimizes?
- Offline NDCG goes up and an interleaving test is flat. Give three explanations and the check for each.
- Engagement goes up and a long-term proxy goes down. Do you ship? What do you need to know?
- (L6) Four surfaces want this ranker. Describe the architecture that lets them share it without blocking each other.

### ml-depth-recsys-02
```yaml
roles: [mle, rs]
levels: [L5, L6]
variant: default
domain: recsys
kind: main
signal_points:
  - explains a shared foundation model for personalization (shared representation, per-surface adaptation, distillation or fine-tuning) and its trade-offs
  - discusses how downstream teams consume and update it (embeddings as features, fine-tuned heads, versioning, deprecation)
  - reasons about training-serving consistency, staleness and cost
  - raises evaluation of a shared model across surfaces with conflicting objectives
```
Discussion context: Netflix has written about moving toward a shared foundation model for personalization that several
surfaces build on. Without any specifics of that model, what are the main design decisions in such a system, and where would it hurt?

Follow-ups:
- Surface A wants the representation to change weekly and Surface B needs it frozen for a month. Resolve it.
- A downstream team fine-tunes and starts to diverge from the shared model. Is that a failure or a feature?
- How do you detect that the shared model has quietly gotten worse for one surface?
- What does it cost to keep a shared model fresh, and who pays?
- (L6) Draw the ownership model: who owns the model, the features, the evaluation and the migration plan when you change the representation?

### ml-depth-recsys-03
```yaml
roles: [mle, rs]
levels: [L5, L6]
variant: default
domain: recsys
kind: main
signal_points:
  - explains the idea of an LLM-native ranker with member history and context verbalized as text and the context window as a feature budget
  - reasons about what to keep, omit, compress and elaborate in the verbalized input and how to test each choice
  - explains why prefill-only scoring (one forward pass over all candidates) differs from generation in latency and cost
  - discusses a multi-objective loss with a reward-weighted term (long-term satisfaction proxy) versus full reinforcement learning, with risks (reward hacking, proxy drift)
  - names hallucinated titles, popularity over-recommendation and business-rule violations as off-the-shelf LLM limits
```
Discussion context: Netflix has described an LLM-native ranking approach where member history and context are turned
into text and the model scores catalog titles. Design the input and the training objective for such a ranker; do not worry about matching any published system.

Follow-ups:
- Your context budget is fixed. A member binged 40 episodes of one show. How do you represent that?
- What do you give up by verbalizing features as text compared with numeric feature vectors, and what do you gain?
- Why can all candidates be scored in one forward pass, and what constraint does it put on the architecture?
- You add a reward-weighted term for a long-term satisfaction proxy. How can the proxy mislead the model, and how do you catch it?
- How do you keep the ranker from recommending titles outside the catalog or violating availability rules?
- (L6) The base model is refreshed rarely and the ranking stage often. Where do you draw the interface, and what is your upgrade and rollback story?

### ml-depth-recsys-04
```yaml
roles: [mle, rs]
levels: [L5, L6]
variant: default
domain: recsys
kind: main
signal_points:
  - explains semantic IDs as discrete codes learned from content and behavior (for example residual quantization) and why they help generative retrieval and cold items
  - compares autoregressive beam search over codes with predicting several tokens at once (latency, error accumulation, diversity)
  - handles collisions, code drift when the quantizer is retrained, and catalog churn
  - proposes an offline and online evaluation for a generative retriever
```
Discussion context: recent work uses semantic IDs so that an LLM can recommend by generating item codes. How would you
build a generative retriever on semantic IDs, and what are the sharp edges?

Follow-ups:
- How are the codes learned and what property do you want from the code space?
- Beam search versus predicting several code tokens at once: what changes in latency, diversity and error?
- You retrain the quantizer. What happens to the model trained on the old codes?
- A new title arrives. What code does it get and how does the model learn to recommend it?
- (L6) Design the migration from an embedding-based retriever to the generative one, with the experiment plan and the stop condition.

### ml-depth-recsys-05
```yaml
roles: [mle, rs]
levels: [L4, L5, L6]
variant: default
domain: recsys
kind: main
signal_points:
  - formulates artwork choice as a contextual bandit with candidate images per title and a delayed, noisy reward
  - handles position and exposure effects, per-title data sparsity and non-stationarity
  - discusses where an LLM or vision-language model helps (candidate generation, reward modeling, post-training for preferences) and what it risks
  - plans offline evaluation with off-policy estimators and an online ramp
```
Discussion context: Netflix has described personalizing the artwork shown for a title with bandits and, more recently,
LLM post-training. Frame the problem and how you would test a new approach.

Follow-ups:
- What is the reward and over what window? What does clicking without playing do to it?
- Each title has only a few artworks and bursts of traffic at launch. How do you explore without hurting the launch?
- What can an off-policy estimator tell you here, and when is its variance unusable?
- How could a language or vision-language model help, and how would you tell it is helping and not only memorizing popular images?
- (L6) Artwork, ordering and row selection are tuned by different teams. How do you avoid interference between their experiments?

## Domain experimentation

### ml-depth-experimentation-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: experimentation
kind: main
signal_points:
  - explains interleaving (team-draft style) as a first-stage, high-sensitivity comparison and why position bias requires symmetric draft
  - states its limits: relative preference only, does not measure retention, implementation complexity, business logic interference
  - proposes the two-stage process: prune candidates with interleaving, confirm with A/B
  - reasons about metric attribution to the contributing ranker
```
You have 12 candidate rankers and traffic for two A/B tests. How do you choose which to test?

Follow-ups:
- How does team-draft interleaving build the merged list, and why must a position be equally likely to come from either ranker?
- Interleaving says ranker B wins. In the A/B it is neutral on retention. What explains both results?
- Which rankers cannot be compared by interleaving at all?
- How do you attribute a play to a ranker when both lists contain the title?
- (L6) Make interleaving a shared service for many teams. What contracts, guardrails and failure modes matter?

### ml-depth-experimentation-02
```yaml
roles: [mle, rs, ds]
levels: [L5, L6]
variant: default
domain: experimentation
kind: main
signal_points:
  - derives CUPED as regression adjustment with a pre-experiment covariate and the variance factor 1 - rho^2
  - chooses covariates that are pre-treatment and uncorrelated with assignment
  - connects to post-stratification, stratified sampling and regression adjustment with covariates
  - notes pitfalls: covariate leakage, missing pre-period for new users, heavy tails, and effect on estimand
```
Your primary metric has high variance and the test needs six weeks. How do you cut the time, and what does it cost?

Follow-ups:
- Derive the variance reduction from using a pre-experiment version of the metric as a covariate.
- New members have no pre-period. What do you do?
- Which covariates would break unbiasedness, and why?
- Heavy-tailed metric: what changes in your approach (winsorization, quantiles, bootstrap), and what estimand do you give up?
- (L6) Teams use different variance-reduction methods and report incomparable numbers. How do you set a common standard?

### ml-depth-experimentation-03
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: experimentation
kind: main
signal_points:
  - handles users in many concurrent tests (artwork, algorithm, encoding) with orthogonal assignment and interaction checks
  - analyzes heterogeneous effects and quantile effects (mean shift versus median shift) without multiple-comparison inflation
  - controls false discoveries across many metrics and segments (FDR, pre-registration)
  - explains the peeking problem and valid sequential methods
```
A test shows a significant improvement on one of 40 metrics and nothing on the primary. A manager wants to ship. What do you say?

Follow-ups:
- A treatment raises mean play delay but lowers its median. How do you investigate and report that?
- You find the effect only in one device segment. How do you decide whether it is real?
- The team checks the dashboard daily and stops when p < 0.05. What is the cost and what do you replace it with?
- Two experiments overlap on the same users. When is that a problem?
- (L6) Design the experimentation review process so these decisions do not depend on who is in the room.

## Domain causal-inference

### ml-depth-causal-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: causal-inference
kind: main
signal_points:
  - states the identification assumptions for observational estimates (ignorability, positivity, SUTVA)
  - chooses among matching, weighting, regression adjustment and doubly robust estimation with reasons
  - checks overlap and covariate balance, and runs placebo or sensitivity analyses
  - separates ATE, ATT and CATE and ties the estimand to the decision
```
Members who use a new feature retain better. How would you estimate its causal effect without a randomized test?

Follow-ups:
- Which unobserved variable most threatens your estimate, and how would you bound its influence?
- Propensity scores are near 0 or 1 for many members. What does that tell you?
- Why is a doubly robust estimator attractive, and when does it still fail?
- How would you check your pipeline recovers a known effect (a simulation or a past randomized test)?
- (L6) A team wants to use this estimator as a standard in decision documents. What validation and governance would you require?

### ml-depth-causal-02
```yaml
roles: [mle, rs, ds]
levels: [L5, L6]
variant: default
domain: causal-inference
kind: main
signal_points:
  - designs geographic or market-level quasi-experiments when user-level randomization is impossible (synthetic control, difference-in-differences, matched markets)
  - states parallel-trends and no-spillover assumptions and tests them with pre-period placebo
  - sizes power for few clusters and computes cluster-robust inference
  - plans for interference and seasonality
```
You want to know the effect of a regional marketing change and cannot randomize members. How do you do it?

Follow-ups:
- Which regions do you pick as controls, and how do you check they are valid?
- You have six comparable regions. What does that do to your inference?
- A holiday hit one region only. How does this change your estimate?
- When would synthetic control beat difference-in-differences?
- (L6) The company runs many such studies. How do you build a shared tool and a review checklist?

### ml-depth-causal-03
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: causal-inference
kind: main
signal_points:
  - distinguishes predicting an outcome from predicting a treatment effect (uplift)
  - explains meta-learners (S, T, X, R) or causal forests and their evaluation (uplift curves, Qini)
  - recognizes that evaluating uplift needs randomized data
  - proposes a targeting policy with budget constraints and monitoring of effect decay
```
You want to send a retention nudge to the members it helps most. How do you model who those are?

Follow-ups:
- Why is a churn-risk model the wrong targeting model?
- How do you evaluate uplift when each member got only one treatment?
- Your estimated CATE is noisy. How do you avoid acting on noise?
- Effects shrink over time as members see more nudges. How do you detect and handle it?
- (L6) Several teams send nudges. How do you prevent members from receiving conflicting treatments and keep each team's measurement valid?

## Domain rl-bandits

### ml-depth-rlbandits-01
```yaml
roles: [mle, rs]
levels: [L4, L5, L6]
variant: default
domain: rl-bandits
kind: main
signal_points:
  - compares epsilon-greedy, UCB and Thompson sampling and their regret behavior
  - sets up a contextual bandit with features, a model of expected reward and exploration over uncertainty
  - handles delayed and batched feedback and non-stationarity
  - states the logging requirements (propensities) for later off-policy evaluation
```
You need to choose among 5 candidate images per title for each member. Walk me through a bandit solution.

Follow-ups:
- Why does Thompson sampling often work well in practice and what does it need from the model?
- Rewards arrive hours later and traffic is batched. What changes?
- What do you log so you can evaluate a different policy later?
- Preferences drift as members see the same image repeatedly. How do you adapt?
- (L6) Ten teams want to run bandits on different surfaces. What do you offer as a shared platform and what stays with each team?

### ml-depth-rlbandits-02
```yaml
roles: [mle, rs]
levels: [L5, L6]
variant: default
domain: rl-bandits
kind: main
signal_points:
  - explains off-policy evaluation (IPS, self-normalized IPS, doubly robust) with the variance-bias trade-off
  - requires support (positivity) of the logging policy and diagnoses violations
  - clips or shrinks weights with a stated bias cost
  - links estimator results to an online ramp decision
```
You have logs from a stochastic policy and a new candidate policy. Estimate the candidate's value without deploying it.

Follow-ups:
- The importance weights are heavy-tailed. What do you do and what does it cost?
- The new policy picks actions the old one almost never took. What can you say?
- Doubly robust: what do you need from the reward model for it to help?
- How do you turn the estimate and its interval into a go or no-go?
- (L6) Set standards so that teams report comparable off-policy results.

### ml-depth-rlbandits-03
```yaml
roles: [mle, rs]
levels: [L5, L6]
variant: default
domain: rl-bandits
kind: main
signal_points:
  - contrasts a bandit (immediate reward) with sequential RL (long-term satisfaction, state transitions) and when the extra complexity is warranted
  - names the difficulties of RL for recommendation: credit assignment, offline data, reward design, distribution shift, safety
  - shows alternatives short of full RL (reward-weighted supervised objectives, slate-level rewards, constrained optimization)
  - proposes safe deployment (conservative policy update, guardrail metrics, holdouts)
```
Leadership wants the ranker to optimize long-term satisfaction instead of next-session engagement. Do you use reinforcement learning?

Follow-ups:
- What state and reward would you use and what could go wrong with the reward?
- You only have logs. What breaks when you train with standard offline RL?
- What can you get from a reward-weighted objective that you cannot from plain supervised learning, and what can you not?
- How do you detect reward hacking in production?
- (L6) Describe the architecture and review process that would let a team try this safely, including rollback.

## Domain cv

### ml-depth-cv-01
```yaml
roles: [mle, rs]
levels: [L4, L5, L6]
variant: default
domain: cv
kind: main
signal_points:
  - designs a visual representation learning pipeline (self-supervised or contrastive, pretrained backbone) for title frames or clips
  - discusses data issues: near-duplicate frames, scene boundaries, label scarcity
  - evaluates embeddings by retrieval quality and downstream task, not loss alone
  - addresses compute and storage for video-scale data
```
You must build frame-level embeddings of the whole catalog to support artwork selection and similarity. How?

Follow-ups:
- Near-duplicate frames dominate a video. What does that do to training and to evaluation?
- Contrastive versus supervised pretraining: when do you choose each?
- How do you measure that the embedding captures what members care about?
- Throughput: the catalog grows by thousands of hours a week. What does your pipeline look like?
- (L6) Several teams want different granularities (frame, shot, scene, title). Design the shared representation and the contract.

### ml-depth-cv-02
```yaml
roles: [mle, rs]
levels: [L5, L6]
variant: default
domain: cv
kind: main
signal_points:
  - frames artwork selection as image ranking with aesthetic, content and safety constraints (faces, text, brand rules)
  - uses detection, quality and saliency models as filters or features
  - handles label noise and subjectivity in aesthetic quality
  - plans online validation with members' behavior and guardrails
```
Build a system that proposes candidate artwork frames for a new title from raw video.

Follow-ups:
- Which automated filters do you apply before ranking, and what errors do they make?
- Aesthetic labels are subjective. How do you collect and use them?
- How does the output feed a bandit, and what must you log?
- A frame contains a person who should not be shown in some regions. What does the system do?
- (L6) How do you structure the creative and ML teams' interface so that ML does not become a bottleneck?

### ml-depth-cv-03
```yaml
roles: [mle, rs]
levels: [L4, L5, L6]
variant: default
domain: cv
kind: main
signal_points:
  - explains a vision backbone choice (CNN versus vision transformer) with data, compute and inductive-bias trade-offs
  - describes evaluation under distribution shift (new content types, animation versus live action)
  - plans deployment trade-offs (distillation, quantization, batch versus real time)
  - names an error analysis approach by slice
```
Your classifier trained on live-action content degrades on animation. Diagnose and fix.

Follow-ups:
- How do you separate dataset shift from a labeling issue?
- Fine-tune, augment, or train a mixture of experts? Compare.
- How do you evaluate by slice without hundreds of tiny test sets?
- You can only afford a model one-fifth the size. What do you give up and how do you decide?
- (L6) The model feeds three downstream products. How do you roll out a replacement safely?

## Domain nlp-llm

### ml-depth-nlpllm-01
```yaml
roles: [mle, rs]
levels: [L4, L5, L6]
variant: default
domain: nlp-llm
kind: main
signal_points:
  - designs a retrieval-augmented or fine-tuned LLM for catalog search or conversational recommendation, with grounding in the catalog
  - addresses hallucinated titles, freshness and permissions (region availability)
  - evaluates with task metrics, human or LLM judges (with their biases), and online behavior
  - discusses latency and cost levers (distillation, caching, smaller model for routing)
```
Design a natural-language title search ("something funny like a heist movie but gentler") for a streaming catalog.

Follow-ups:
- The model confidently names a title that is not available in the member's country. What prevents that?
- How would you evaluate it offline with no labeled relevance?
- If you use an LLM judge, how do you know it is not biased toward the model's style?
- Prefill cost dominates. What do you cache and what do you precompute?
- (L6) Search, homepage and customer support want conversational features. What do you build once, and what do you leave to each?

### ml-depth-nlpllm-02
```yaml
roles: [mle, rs]
levels: [L5, L6]
variant: default
domain: nlp-llm
kind: main
signal_points:
  - explains post-training stages (supervised fine-tuning, preference optimization, reward-weighted objectives) and what each changes
  - discusses data quality, catastrophic forgetting, and parameter-efficient methods
  - reasons about scaling the backbone versus data (cost-benefit) without citing specific figures
  - evaluates for regressions across capabilities and for safety
```
You have a base LLM and member interaction logs. How do you adapt it into a ranking model, and how do you decide on backbone size?

Follow-ups:
- What goes in Phase 1 (adapt the base to the domain) versus Phase 2 (task-specific training), and why separate them?
- LoRA or full fine-tuning: what do you decide on and why?
- How do you detect that the adapted model forgot something you need?
- A bigger backbone helps offline. What else do you need to see before paying for it?
- (L6) The backbone will be shared by ranking, search and explanations. Draw the interfaces and the release process.

### ml-depth-nlpllm-03
```yaml
roles: [mle, rs]
levels: [L4, L5, L6]
variant: default
domain: nlp-llm
kind: main
signal_points:
  - explains serving costs of transformers: prefill versus decode, KV cache memory, batching and paged memory
  - distinguishes prefill-only scoring from generation and where each is bound (compute versus bandwidth)
  - estimates capacity (tokens per second, memory per request) with stated assumptions
  - proposes optimizations and their risks (quantization, speculative decoding, prefix caching)
```
You need to score 500 candidate titles for one member within a strict latency budget using a transformer with a long input. How do you serve it?

Follow-ups:
- Why is a scoring pass cheaper than generating the same number of tokens?
- Estimate the memory per concurrent request for the input and where the bottleneck is.
- Prefix caching helps if many requests share a prefix. What in your input is shareable and what is not?
- Quantization lowers cost. How do you check that it does not change rankings in ways that matter?
- (L6) Plan capacity and cost across several model owners sharing GPUs.

## Domain ads

### ml-depth-ads-01
```yaml
roles: [mle, rs]
levels: [L4, L5, L6]
variant: default
domain: ads
kind: main
signal_points:
  - builds a CTR or conversion prediction model with calibration requirements and delayed feedback
  - handles feature crosses, sparse categorical features and embeddings at scale
  - explains why calibration matters for pacing and auction decisions
  - addresses selection bias because only shown ads have outcomes
```
Build a click and conversion prediction model for ads shown within a streaming product.

Follow-ups:
- Conversions arrive days after a click. How do you train without waiting?
- You downsample negatives. What happens to the probabilities and how do you correct them?
- Only shown ads have labels. What bias does this give and what do you do?
- How do you detect that calibration drifted for one advertiser segment?
- (L6) Several ads products share one model. Design the evaluation and rollout so a gain in one does not hide a loss in another.

### ml-depth-ads-02
```yaml
roles: [mle, rs, ds]
levels: [L5, L6]
variant: default
domain: ads
kind: main
signal_points:
  - designs an ad-frequency-cap experiment with a user-level unit, a cap policy arm, and metrics for advertiser value and member experience (retention)
  - handles novelty, fatigue and long-term effects with holdouts and long runtimes
  - sizes the test (power for a small effect on a noisy outcome) and uses variance reduction
  - reasons about spillover through advertiser budgets or shared inventory
```
How would you decide the right ad frequency cap, and how would you test it?

Follow-ups:
- What are the primary and guardrail metrics, and whose interests do they represent?
- Members who see more ads differ from those who see fewer. Why can't you just compare them?
- How long must the test run to see fatigue, and how do you make the answer usable sooner?
- Advertisers share a budget across members. Where does interference appear?
- (L6) Advertisers, product and finance disagree on the objective. How do you structure the decision?

### ml-depth-ads-03
```yaml
roles: [mle, rs]
levels: [L5, L6]
variant: default
domain: ads
kind: main
signal_points:
  - formulates ad allocation as constrained optimization with pacing, budgets and delivery guarantees
  - uses bandit or control-theory methods for pacing and explains exploration cost
  - discusses auction design effects (first versus second price, bid shading) at an operational level
  - monitors for budget exhaustion, underdelivery and feedback loops
```
Advertisers buy a fixed number of impressions over a month. How would you allocate and pace them across members and sessions?

Follow-ups:
- A large advertiser's campaign is underdelivering midway. What levers do you have and what do they cost?
- How do you learn the value of an impression for a new advertiser?
- How do predicted-probability errors turn into pacing errors?
- What do you monitor so a bug does not burn a budget in an hour?
- (L6) Describe the architecture across prediction, allocation and serving, and who owns each part.

## Domain ml-platform

### ml-depth-mlplatform-01
```yaml
roles: [mle, rs]
levels: [L4, L5, L6]
variant: default
domain: ml-platform
kind: main
signal_points:
  - designs a training and batch-inference scheduler with queues, priorities, quotas and preemption
  - handles failure: retries, checkpointing, idempotence, stuck jobs, multi-tenant fairness
  - exposes observability (job state, cost, GPU utilization) and cost attribution
  - compares gang scheduling and bin packing for distributed training
```
Design the scheduler that runs training and batch inference jobs for many ML teams on a shared GPU cluster.

Follow-ups:
- A long training job and a latency-sensitive batch job compete for the same GPUs. Who wins and how do you enforce it?
- A node dies at 90% of a job. What did you design for?
- A team's jobs always sit in the queue. How do you find out whether it is fairness, quota or a bug?
- How do you charge or allocate cost so teams change behavior?
- (L6) The platform has 30 teams and conflicting needs. How do you decide what to build, and how do you manage migrations?

### ml-depth-mlplatform-02
```yaml
roles: [mle, rs]
levels: [L4, L5, L6]
variant: default
domain: ml-platform
kind: main
signal_points:
  - designs a feature store with consistent offline and online features, point-in-time correctness and backfills
  - addresses training-serving skew, freshness SLOs and schema evolution
  - discusses real-time feature serving latency, caching and fallbacks
  - assigns ownership and quality checks for shared features
```
Design feature serving so that training and serving see the same features.

Follow-ups:
- A feature is computed differently in batch and online. How do you detect and prevent it?
- How do you build a training set with point-in-time correctness?
- The feature store's p99 latency spikes. What is the fallback and its cost?
- A feature's owner changes its definition. How does a downstream model owner find out?
- (L6) How do you decide which features become platform assets, and how do you retire the rest?

### ml-depth-mlplatform-03
```yaml
roles: [mle, rs]
levels: [L5, L6]
variant: default
domain: ml-platform
kind: main
signal_points:
  - designs an ML portal or self-service layer (experiment tracking, model registry, deployment, lineage)
  - defines safe deployment: shadow, canary, automatic rollback and guardrail metrics
  - plans daily retraining pipelines with data validation and promotion gates
  - reasons about adoption: golden path versus flexibility, and the paved-road principle
```
Design the self-service system that lets an ML team go from experiment to a monitored production model with daily retraining.

Follow-ups:
- What gates must a model pass before it replaces the current one automatically?
- A retraining run silently trains on partial data. How do you prevent that?
- How do you let advanced teams leave the paved road without losing safety?
- What do you measure to know the platform is working?
- (L6) Your platform competes with teams' own tooling. How do you win adoption without mandating it?

## Cross-domain

### ml-depth-any-01
```yaml
roles: [mle, rs]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - picks a technical decision from their own work and explains the alternatives rejected
  - goes three levels deep on mechanism when asked "why" and "what breaks"
  - separates what they built, read, and guess
  - connects the decision to a measurable outcome and a later lesson
```
Pick the most technically interesting decision in your recent work in this domain. What were the alternatives, and what would you do differently now?

Follow-ups:
- What was the first thing that made you doubt the approach?
- What evidence told you it was working?
- What did you stop doing as a result?
- (L6) Which decision would you have wanted another team to make with you, and why?
