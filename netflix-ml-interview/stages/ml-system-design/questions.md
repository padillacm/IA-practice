# Questions: ml-system-design

Banks are built from reported topics and Netflix-published practices, not from "real Netflix questions". Numbers in
prompts are assumptions the interviewer may offer when asked; they are not Netflix figures. Each main prompt lists the
`signal_points` the interviewer uses to pace the round (collect, interrupt, move on).

# Variant: design

### mlsd-design-homepage-rows-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: design
domain: recsys
kind: main
signal_points:
  - frames the surface (rows, titles per row, devices) and the objective before designing
  - separates candidate generation from row/title ranking and page-level construction
  - handles row diversity, deduplication across rows and position bias
  - explore/exploit mechanism for new or uncertain titles and rows
  - offline metrics (ranking metrics, counterfactual or replay) and why they may not match online results
  - availability with cached or fallback homepage when the model service degrades
  - privacy and security of viewing history in features and logs
  - online validation with interleaving as a first stage and an A/B test as the second stage
  - finishes an end-to-end design in the time
```
Design the system that builds a member's personalized homepage: the rows, the titles inside each row and their
order, on TV, mobile and web.

**Clarifying requirements the candidate should raise.** Members and catalog scale (assume hundreds of millions of
members, tens of thousands of titles); latency budget at page load; freshness (does a title watched five minutes ago
change the page?); multiple profiles per account; what the page optimizes (long-term satisfaction and retention,
not clicks alone); device differences; business constraints (new releases, regional licensing).

**Expected talking points.** Candidate generation per row type, row selection and ordering, per-row title ranking,
page assembly with constraints, feature store with consistent offline/online features, batch precompute vs
request-time scoring (hybrid), multi-objective ranking, position bias, exploration, logging for counterfactual
training, caching and fallback pages, privacy controls, monitoring of metric drift and of data pipelines,
interleaving then A/B (interleaving is relative and does not measure retention, so a second stage is needed).

**L4.** A coherent two-stage (candidate generation then ranker) design with a feature store and a named metric; needs
prompting for fallbacks, diversity and online testing.
**L5.** Adds page-level construction, bias and exploration mechanisms, offline/online mismatch, degraded modes, and
a two-stage validation plan with guardrails, without prompting.
**L6.** Drives the trade-offs across surfaces and teams (shared foundation models vs per-surface models, batch vs
real-time cost), names platform reuse, ownership and rollout risks, and anticipates failure modes unprompted.

**Culture probe.** "You chose to precompute rows in batch. A product partner says members will feel the page is
stale and wants real-time scoring everywhere. Defend your choice or change it, and tell me what evidence would
move you."

**Follow-ups**
- How would you stop the same title appearing in five rows?
- The ranker improves offline NDCG but the A/B is flat. What do you check first?
- What is your fallback if the ranking service is down at 8pm on a Friday?
- Which logs would you need to train off the exposure the old policy created?

### mlsd-design-artwork-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: design
domain: rl-bandits
kind: main
signal_points:
  - frames the decision (which image, per title, per member, per context) and the reward definition
  - contextual bandit or equivalent with explicit explore/exploit and a delayed-reward discussion
  - candidate asset pool, quality and policy constraints (no misleading art, brand safety)
  - logging propensities and off-policy evaluation to train and evaluate without full exposure
  - attribution problems (an image drives a click but not satisfaction), position and neighbor interference
  - latency and availability of the image decision with a safe default per title
  - privacy and security of the signals used
  - online validation (artwork A/B, long-term outcome beyond clicks) and metric alignment
  - finishes an end-to-end design in the time
```
Design the system that chooses which artwork to show each member for each title.

**Clarifying requirements the candidate should raise.** Number of candidate images per title and how they are made;
decision granularity (per title, per row, per member); reward (play, play with completion, retention); cold start for
new titles; editorial and safety constraints; latency; whether artwork must be stable across sessions.

**Expected talking points.** Contextual bandit with Thompson sampling or similar, reward shaping beyond clicks,
propensity logging and off-policy evaluation, exploration cost and budget, new-title warm-up, a safe per-title
default, creative-quality filters, interaction with neighbor titles and rows, offline replay, A/B with long-term
outcome and guardrails, monitoring of reward drift.

**L4.** A bandit or ranking model per title with click reward and an A/B test; needs prompting on delayed reward,
logging and safety.
**L5.** Defines reward carefully, handles exploration budget, propensity logging and off-policy evaluation, and
guards against misleading artwork with a fallback.
**L6.** Treats it as a platform: shared bandit service across surfaces, interference between concurrent tests,
organization-level trade-offs (creative team inputs, brand risk) and long-term measurement strategy.

**Culture probe.** "Your bandit lifts clicks but a designer shows the winning image is misleading for some titles.
Do you ship? What do you say to your own team and to the designer?"

**Follow-ups**
- How do you estimate the value of an image you almost never showed?
- Clicks go up and retention is flat. What does that tell you about the reward?
- How do you evaluate a new policy offline when the logging policy was a bandit?

### mlsd-design-search-ranking-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: design
domain: recsys
kind: main
signal_points:
  - separates query understanding, retrieval and ranking, and handles multiple intents (title, person, genre, mood)
  - blends relevance with personalization without making results unpredictable
  - handles training data bias (clicks only on what was shown) and position bias
  - offline metrics (NDCG, MRR, null-query rate) and their relation to online satisfaction
  - latency budget and graceful degradation of the personalized stage
  - security and privacy of query logs
  - online validation with interleaving as a first stage and an A/B test as the second stage
  - explore/exploit for new titles in search
  - finishes an end-to-end design in the time
```
Design a personalized search ranking system for a streaming catalog with mixed intents (titles, people, genres,
vague queries such as "something funny").

**Clarifying requirements the candidate should raise.** Languages and catalog scale, latency budget per keystroke or
per submission, share of known-item vs exploratory queries, personalization policy, what counts as success
(play after search, time to play, abandonment), regional availability of titles.

**Expected talking points.** Query parsing and entity linking, lexical plus embedding retrieval, learning-to-rank
with personal features, cold start for users and titles, handling no-result queries, bias correction, evaluation with
labeled sets and click models, interleaving for ranker comparison then A/B, caching, fallbacks to lexical-only
ranking, access control and retention of query logs.

**L4.** Retrieval plus a learned ranker, relevance metrics and an A/B; needs prompting on intents and degradation.
**L5.** Covers intent mix, bias correction, personalization guardrails, latency/degraded modes, and interleaving
before A/B unprompted.
**L6.** Frames search as part of a unified discovery stack with shared foundation representations, defines the
operating model (quality labels, ownership, rollout gates) and anticipates failure modes of embedding retrieval.

**Culture probe.** "Your personalization stage adds 40 ms and helps only 5% of queries. A teammate wants to cut it.
Take a position and defend it."

**Follow-ups**
- How would you handle a query for a title that is not available in the member's country?
- How do you evaluate rankers when most queries have one obviously right answer?
- What would you log to retrain next quarter?

### mlsd-design-autocomplete-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: design
domain: nlp-llm
kind: main
signal_points:
  - states the latency budget (per keystroke) and drives the architecture from it
  - candidate source (catalog, popular queries, personal history) with prefix index or trie and learned reranker
  - handles typos, multilingual input and non-Latin scripts
  - personalization and freshness (new releases trending) with safety filters
  - availability and fallback to a static index when the model is unavailable
  - privacy of typed text, retention and abuse or offensive suggestions
  - offline metrics (MRR of accepted suggestion, keystrokes saved) versus online metrics
  - online validation with interleaving as a first stage and an A/B test as the second stage
  - finishes an end-to-end design in the time
```
Design search autocomplete for a streaming service app, on TV and mobile.

**Clarifying requirements the candidate should raise.** Latency per keystroke (tens of ms), devices and input
methods (remote-control typing is slow and costly), languages, personalization, offensive-content policy, how
fresh suggestions must be, what success is (fewer keystrokes, faster time to play).

**Expected talking points.** Prefix index at the edge, candidate merge, lightweight reranker or distilled model,
caching by prefix, keystroke logging, typo tolerance, blocklists, trending signals, degradation to a static list,
privacy of typed text, evaluation (offline replay of sessions, online engagement), A/B with interleaving as a quick
first stage.

**L4.** Prefix index plus popularity ranking and an A/B; needs prompting on latency, safety and personalization.
**L5.** Latency-driven architecture, reranker with personal and trending signals, safety filters, fallbacks and
two-stage online testing.
**L6.** Sets the shared-service boundary with the search stack, discusses cost of per-keystroke inference at global
scale, abuse risk and policy ownership.

**Culture probe.** "Product wants to show trending suggestions that may surface sensitive topics. Where do you
draw the line and who decides?"

**Follow-ups**
- How do you update the index when a major title launches at midnight?
- What do you do when the model service times out after 20 ms?
- How would you measure that suggestions helped rather than only reordered effort?

### mlsd-design-continue-watching-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: design
domain: recsys
kind: main
signal_points:
  - defines the problem (rank in-progress titles and next episodes, with resume position) and its signals
  - treats it as a recsys problem, not just a recency sort (intent to resume, abandoned titles, shared accounts)
  - data freshness and cross-device consistency of playback state
  - streaming vs batch updates and consistency of resume position
  - availability and graceful degradation when personalized ranking fails (recency fallback)
  - privacy and profile separation in shared accounts
  - offline/online metric alignment (resume rate vs long-term satisfaction)
  - online validation with interleaving as a first stage and an A/B test as the second stage
  - finishes an end-to-end design in the time
```
Design the Continue Watching row: which in-progress titles and next episodes appear, in what order, on each device.

**Clarifying requirements the candidate should raise.** Definition of "in progress", staleness windows, shared
profiles, cross-device resume, next-episode logic, whether a title can be removed by the member, latency and freshness
expectations right after playback ends.

**Expected talking points.** Event stream of playback heartbeats into a state store, resume-intent model (probability
of returning given time since last watch, completion, genre, day part), ranking with constraints, de-duplication with
other rows, cache invalidation after playback, offline labels (did the member resume within N days), fallback to
recency order, A/B with a satisfaction outcome not only row clicks.

**L4.** Recency-based ranking plus a model for resume probability; needs prompting on state consistency and fallbacks.
**L5.** State pipeline and consistency, intent modeling, guardrails for shared accounts, fallback ordering and a
two-stage validation plan.
**L6.** Connects this row to the page-level objective (how it competes with other rows), defines ownership of the
playback-state service, and plans the rollout and monitoring strategy across devices.

**Culture probe.** "The model says to hide a half-watched title the member returns to once a year. A PM says hiding
anything is a trust violation. How do you resolve this?"

**Follow-ups**
- A member finishes an episode on TV and opens the phone ten seconds later. What do they see and why?
- How do you detect that your resume-state pipeline is silently lagging?

### mlsd-design-title-cold-start-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: design
domain: recsys
kind: main
signal_points:
  - frames cold start for a new title (no interactions) and for new members separately
  - content-based representation (metadata, text, multimodal embeddings) and transfer from similar titles
  - explore/exploit with an explicit exploration budget and how to stop exploring
  - handling popularity bias and fairness to new content
  - avoiding feedback loops and exposure bias in training
  - availability of the launch-day path and monitoring of rapid-changing signals
  - offline evaluation for cold items (time-split, item-holdout) and why it differs from warm
  - online validation with interleaving as a first stage and an A/B test as the second stage
  - finishes an end-to-end design in the time
```
Design the system that decides how to introduce a brand new title to the right members on day one, before there is any
viewing data.

**Clarifying requirements the candidate should raise.** What metadata exists pre-launch (cast, genre, trailer,
synopsis), marketing commitments, the launch calendar, regional rollout, acceptable cost of showing a title to the
wrong audience, how many members can be used for exploration.

**Expected talking points.** Content embeddings from text and video, nearest-neighbor transfer from similar titles,
bandit exploration budget with a decay schedule, calibrated uncertainty, business-rule boosts, feedback loops,
cold-item offline evaluation, A/B with guardrails on member experience and on the effect on warm titles.

**L4.** Content-based features plus popularity of similar titles; needs prompting on exploration and evaluation.
**L5.** Explicit exploration budget and decay, calibrated scores, bias discussion, cold-item offline protocol and
online validation.
**L6.** Aligns with business (marketing, content strategy), discusses organization-level trade-offs of exposure
fairness, and designs the system so it generalizes to all new content types.

**Culture probe.** "Marketing demands a prominent slot for a flagship title regardless of the model. Do you comply?
How do you quantify what that costs?"

**Follow-ups**
- How would you know the exploration has produced enough data to stop?
- What breaks if the content embedding is wrong for an unusual title?

### mlsd-design-daily-retraining-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: design
domain: ml-platform
kind: main
signal_points:
  - quantifies the data volume and sets the freshness requirement (why daily)
  - data pipeline design (incremental, partitioned, deduplicated) and cost vs freshness trade-offs
  - training/serving skew and point-in-time correct features
  - model validation gates before promotion, shadow and canary, rollback
  - failure handling, idempotent reruns and backfills
  - security and governance of data (access control, PII, retention)
  - monitoring of data drift and model quality, alerting
  - offline/online metric alignment before an automated promotion
  - online validation of retrained models (interleaving to compare quickly, A/B for the promoted ones)
  - finishes an end-to-end design in the time
```
A ranking model must be retrained every day on petabytes of interaction data. Design the training pipeline and the
promotion process.

**Clarifying requirements the candidate should raise.** Why daily and what happens if a day is missed; size of the
data and growth; training time budget; model size; cost limits; who owns the model; whether promotion is automatic.

**Expected talking points.** Incremental data windows and downsampling, distributed training with checkpointing,
point-in-time feature joins, reproducibility and lineage, automated evaluation gates, shadow scoring, canary and
rollback, handling failed or late upstream data, cost control, drift monitoring, access control and PII handling,
interleaving to compare a new model against production with little traffic then A/B for important launches.

**L4.** A daily batch pipeline with train, evaluate, deploy steps; needs prompting on skew, gates and rollback.
**L5.** Gates, canary and rollback, failure and backfill handling, drift monitoring, cost trade-offs and security of
data, with online validation.
**L6.** Treats it as a platform for many teams: standardized promotion criteria, cost allocation, ownership of
incidents, and criteria for when a model may be promoted automatically.

**Culture probe.** "An automated gate blocked today's model because offline metrics dropped 0.3%, but the owning
team says the drop is noise and wants an override. What do you build, and what do you say to the team?"

**Follow-ups**
- How do you detect a silently corrupted upstream partition?
- A retrain run fails at 95% of the epochs. What is lost and what do you do?
- How would you let teams train less often when freshness does not matter?

### mlsd-design-ml-job-scheduler-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: design
domain: ml-platform
kind: main
signal_points:
  - distinguishes training jobs (long, checkpointed, GPU) from batch inference (throughput, deadline) and their SLOs
  - resource allocation (quotas, priorities, fair share, preemption, gang scheduling for multi-GPU)
  - multi-tenancy isolation, noisy neighbors and cost attribution
  - crash handling (retries, checkpoint resume, idempotency, node failure, poison jobs)
  - monitoring (queue time, utilization, failure rate, SLO burn) and alerting
  - security (per-tenant access, secrets, data access, audit)
  - scheduler availability itself (state store, leader election, recovery)
  - how users validate that a job did the right thing (lineage, model registry hooks)
  - finishes an end-to-end design in the time
```
Design a scheduler for ML jobs on a shared cluster. It must run model training and batch inference jobs from many
teams, allocate resources, monitor jobs and handle crashes.

**Clarifying requirements the candidate should raise.** Number of tenants and jobs per day, job duration distribution,
GPU vs CPU mix, SLOs (start latency, completion deadlines), priority rules, preemption policy, cost accounting,
on-prem vs cloud, data locality.

**Expected talking points.** Job spec and API, queues with quotas and priorities, scheduler loop with bin packing and
gang scheduling, preemption with checkpointing, retry policy with backoff and failure classification, heartbeat and
state reconciliation, cluster autoscaling, observability (queue time, utilization, goodput), multi-tenancy limits and
cost attribution, access control, high availability of the control plane, graceful degradation under capacity loss.

**L4.** A working queue-and-workers design with retries; needs prompting on preemption, multi-tenancy and the
scheduler's own availability.
**L5.** Priorities, fair share, checkpointed preemption, failure taxonomy, observability and control plane
recovery covered with concrete mechanisms.
**L6.** Defines the product and organizational model: quota governance, chargeback, SLO tiers, build vs adopt, and
how adoption across teams is staged.

**Culture probe.** "A high-priority team keeps preempting everyone else's jobs and the other teams are angry. How do
you decide, and who do you tell first?"

**Follow-ups**
- A node dies with 200 jobs on it. Walk through what happens in the next five minutes.
- How do you prevent one tenant's runaway job from starving everyone?
- How do you test the scheduler's failure handling?

### mlsd-design-compute-allocation-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: design
domain: ml-platform
kind: main
signal_points:
  - frames what is allocated (GPU hours, training vs inference vs experimentation) and the objective
  - demand forecasting and utilization measurement (goodput, idle, fragmentation)
  - allocation policy (quotas, auctions, priorities, reservations) and fairness
  - elasticity and spot or preemptible capacity with checkpointing
  - resilience to capacity loss and to burst demand (a launch, a retrain storm)
  - governance and access control, cost visibility to teams
  - validation of the policy online (shadow, pilot teams) and metrics of success
  - finishes an end-to-end design in the time
```
Design the system that allocates a fixed pool of expensive compute (GPUs) among many ML teams and workloads: training,
batch inference and experimentation.

**Clarifying requirements the candidate should raise.** Pool size and growth, workload mix, business priorities,
tolerance for queueing, budget model (chargeback vs quota), forecast horizon, spot availability.

**Expected talking points.** Demand forecasting, utilization dashboards, quota with borrowing, priority classes,
preemptible tiers, autoscaling, bin packing and fragmentation, capacity reservations for launches, cost visibility,
policy simulation on historical traces, pilot rollout.

**L4.** Quotas per team and a queue; needs prompting on utilization, forecasting and elasticity.
**L5.** Policy with borrowing and preemptible tiers, utilization metrics, burst handling, and a simulated rollout.
**L6.** Connects allocation to business priorities and budget, designs governance and escalation, and weighs build vs
buy and long-term capacity planning.

**Culture probe.** "Leadership wants your policy to favor the homepage team; others will say it is unfair. Defend a
policy and how you would communicate it."

**Follow-ups**
- How would you detect that a team hoards idle GPUs?
- How do you test a new allocation policy without hurting teams?

### mlsd-design-ml-portal-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: design
domain: ml-platform
kind: main
signal_points:
  - frames users (researchers, MLEs, analysts) and the workflow from data to deployed model
  - components (data discovery, notebooks, experiment tracking, training, registry, deployment, monitoring)
  - separation of control plane and data plane, APIs and extensibility
  - multi-tenancy, authentication and authorization, secrets and data governance
  - availability and upgrade strategy for the platform itself
  - reproducibility and lineage across experiments and deployments
  - how platform quality is measured (adoption, time to first model, incidents)
  - how model quality is validated online with interleaving to A/B through the platform
  - finishes an end-to-end design in the time
```
Design a full-stack ML portal for an internal organization: from exploring data to training, registering, deploying
and monitoring models.

**Clarifying requirements the candidate should raise.** Who the users are and their skill range, existing tooling,
languages and frameworks, governance requirements, scale of users and models, what teams do today that hurts.

**Expected talking points.** Self-service workflows, paved path vs escape hatches, experiment tracking and registry,
one-click deployment with canary and rollback, monitoring and model cards, access control by data classification,
cost visibility, platform SLOs, versioned APIs, adoption strategy and metrics, integration with the A/B platform for
interleaving and A/B tests.

**L4.** A set of services (notebooks, training, registry, serving) with basic auth; needs prompting on
governance, reproducibility and measuring adoption.
**L5.** Control/data plane separation, governance, lineage, deployment safety and platform metrics with trade-offs
between paved path and flexibility.
**L6.** Treats the portal as a product with a roadmap, adoption strategy, organizational ownership and deprecation
policy, and anticipates scaling and security risks.

**Culture probe.** "A star team wants to bypass the portal for speed. Do you allow it? What do you tell them and the
team that follows the paved path?"

**Follow-ups**
- How do you know the portal is helping, rather than adding process?
- How do you handle a model that was deployed through the portal and later found to use data it should not have?

### mlsd-design-realtime-features-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: design
domain: ml-platform
kind: main
signal_points:
  - states latency, throughput and freshness requirements per feature
  - online store design (key-value, caching, TTL, hot keys) and streaming feature computation
  - training/serving consistency and point-in-time correctness
  - availability, replication, regional failover and degraded mode with defaults
  - security and privacy (access control per feature set, PII, retention)
  - monitoring of feature freshness, null rates and drift
  - cost trade-offs of real-time versus batch features and which features justify real-time
  - validation that a new feature helps (offline lift then online A/B with interleaving)
  - finishes an end-to-end design in the time
```
Design a real-time feature serving system for personalization models: features computed from recent member activity
must be available to rankers in a few milliseconds.

**Clarifying requirements the candidate should raise.** Feature types and counts, freshness SLA per feature,
read volume per second, latency budget, regions, consistency needs, who creates features.

**Expected talking points.** Stream processing for aggregates, online store with replication, batch backfill and
parity checks, feature registry and ownership, schema and versioning, caching, handling hot keys, defaults when
features are missing, monitoring of freshness, access control and PII, cost decision about which features are
real-time, offline-to-online lift validation.

**L4.** Stream job writing to a key-value store with a read API; needs prompting on skew, defaults and monitoring.
**L5.** Consistency between offline and online, failover/degraded behavior, freshness SLAs, governance and cost
reasoning.
**L6.** Designs the feature platform contract across teams, versioning and deprecation, multi-region strategy and
cost allocation, and anticipates failure modes.

**Culture probe.** "A team ships a feature that adds 10 ms at p99 to everyone's reads. Do you block the launch? How do
you tell them?"

**Follow-ups**
- How do you detect that online and offline values for a feature disagree?
- What do rankers do when a feature is missing for a request?

### mlsd-design-ad-breaks-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: design
domain: ads
kind: main
signal_points:
  - frames the decision (where to place breaks, which ad, how many) and constraints (member experience, advertiser contracts)
  - two sides of the objective (member experience vs revenue) with guardrails
  - ad selection and pacing, frequency capping and delivery guarantees
  - latency and availability of ad decisions and safe fallbacks (fill with house content)
  - security and privacy (no sensitive targeting, consent, data separation)
  - explore/exploit for new ads and advertisers, cold start
  - offline/online metric alignment (predicted vs realized engagement and revenue)
  - online validation with interleaving as a first stage where applicable and an A/B test with long-term retention
  - finishes an end-to-end design in the time
```
Design the system that decides ad breaks and ad selection in an ad-supported streaming tier: where breaks occur in a
title, which ads fill them, and how often a member sees the same ad.

**Clarifying requirements the candidate should raise.** Content types (live, series, film), contractual delivery
commitments, member experience limits (ads per hour), targeting restrictions and privacy rules, latency of the ad
decision, measurement partners, how revenue and member satisfaction trade off.

**Expected talking points.** Break placement (content-aware, scene boundaries) with constraints, ad selection as
constrained optimization (pacing, budget, frequency cap), prediction of engagement and completion, auction or
guaranteed-delivery mix, exploration for new ads, fallback when the ad server is slow, privacy and consent
controls, logging for attribution, guardrail metrics on retention, A/B with long-term effect.

**L4.** A break placement rule plus ranker with frequency cap; needs prompting on delivery guarantees, privacy and
fallbacks.
**L5.** Constrained optimization with pacing and exploration, guardrails, degraded mode and a validation plan with
retention as a guardrail.
**L6.** Frames the two-sided objective at business level, handles contractual and organizational constraints, and
anticipates measurement and trust risks.

**Culture probe.** "Revenue is up 4% but a guardrail shows slightly higher cancellation among heavy viewers. Do you
ship? Make the case in two minutes."

**Follow-ups**
- How would you cap how often one member sees one ad across devices?
- What happens if the ad server fails mid-title?

### mlsd-design-catalog-embeddings-01
```yaml
roles: [mle, rs, ds]
levels: [L5, L6]
variant: design
domain: cv
kind: main
signal_points:
  - frames the consumers of the embeddings (search, recs, similarity, content analytics) and the quality definition
  - multimodal inputs (text, video frames, audio, metadata) and fusion strategy
  - training objective (contrastive, co-watch supervision) and evaluation on downstream tasks
  - batch computation at catalog scale and incremental updates for new titles
  - versioning and compatibility of embeddings across consumers (backfills, dual-write)
  - security and rights constraints (unreleased content access control)
  - offline/online alignment (embedding quality metrics vs downstream online lift)
  - online validation through downstream A/B with interleaving as a first stage
  - finishes an end-to-end design in the time
```
Design a multimodal embedding system for the whole catalog: titles are represented from text, video and audio so that
many teams can use the vectors for recommendation, search and analytics.

**Clarifying requirements the candidate should raise.** Consumers and their needs, number of titles and updates per
day, languages, embedding dimension and storage, latency (batch vs online), tolerance for embedding changes.

**Expected talking points.** Encoders per modality, fusion, contrastive or behavior-supervised training, evaluation
on retrieval and downstream tasks, versioning with backfills, serving as a shared feature, access controls for
unreleased content, monitoring drift, cost of video processing.

**L5.** Encoders and fusion, objective, evaluation, versioning and downstream validation.
**L6.** Platform contract across consumers, migration strategy for new versions, cost-quality trade-offs and
organizational ownership.

**Culture probe.** "A consumer team depends on v1 vectors and refuses to migrate while v2 is clearly better. How do
you handle it?"

**Follow-ups**
- How would you tell the new embedding is better before every consumer retrains?
- A title's trailer is mislabeled in a different language. What breaks?

# Variant: problem-framing

### mlsd-framing-objective-metric-01
```yaml
roles: [rs, mle, ds]
levels: [L4, L5, L6]
variant: problem-framing
domain: recsys
kind: main
signal_points:
  - separates the business goal (long-term satisfaction, retention) from proxy objectives (play, completion)
  - proposes a primary metric, guardrails and diagnostic metrics with reasons
  - identifies how the proxy can be gamed or can diverge from the goal
  - data required, label definition and leakage risks
  - baseline hierarchy (popularity, simple heuristic, current production)
  - offline evaluation design and why it may not predict online results
  - online validation plan with interleaving as a first stage and an A/B test as second stage
  - risks and failure modes (feedback loops, popularity bias, fairness, privacy)
  - sketches a minimal end-to-end system in the time
```
A product team wants a model that "recommends what members will enjoy". Frame it as an ML problem: what exactly do you
optimize, how do you know it works, and what could go wrong?

**Clarifying requirements the candidate should raise.** Surface and decision being made; what "enjoy" means to the
business; time horizon; available signals; constraints (latency, catalog, regions).

**Expected talking points.** Objective hierarchy, label construction from viewing (completion, rewatch, return),
multi-objective trade-offs, baselines, time-split offline evaluation, counterfactual methods, online experiment design
with guardrails, risks, and a first version that can be shipped.

**L4.** Picks a defensible objective and metric and a baseline; needs prompting on divergence between proxy and goal
and on online validation.
**L5.** Argues the objective hierarchy, anticipates proxy gaming and leakage, designs offline and two-stage online
evaluation.
**L6.** Frames the problem as an investment: what to learn first, decision criteria for continuing, and how the
choice affects other teams' metrics.

**Culture probe.** "You pick completion rate. A colleague argues it rewards short content and hurts the catalog.
Update, defend, or find a third option, and say why."

**Follow-ups**
- What would your first baseline be and what would make you abandon the model?
- How would you detect offline that your label leaks the future?

### mlsd-framing-data-baselines-01
```yaml
roles: [rs, mle, ds]
levels: [L4, L5, L6]
variant: problem-framing
domain: experimentation
kind: main
signal_points:
  - identifies the data needed, its biases (exposure, selection, position) and missing counterfactuals
  - defines train/validation/test splits that respect time and users
  - builds a baseline ladder and an ablation plan
  - offline metrics aligned to the decision and their limits
  - proposes a plan to reduce the offline/online gap (replay, off-policy evaluation, small online tests)
  - online validation with interleaving as a first stage and an A/B test as second stage
  - risks (privacy, feedback loops) and a stopping rule for the project
  - sketches a minimal end-to-end system in the time
```
You are asked to predict which members will cancel in the next 30 days and to use the prediction to decide whom to
reach with a retention intervention. Frame the problem: data, baselines, offline evaluation and risks.

**Clarifying requirements the candidate should raise.** What decision the prediction drives; intervention type and
cost; whether the goal is prediction or uplift; labeling window; how members are exposed to interventions today.

**Expected talking points.** Prediction versus causal uplift (targeting the persuadable), selection bias, label
windows and leakage, time-based splits, calibration, baselines (recency/frequency, GBDT on simple features),
evaluation by uplift or Qini rather than accuracy alone, randomized holdout, privacy of cancellation data, and
fairness across member groups.

**L4.** Predictive model with time split and baselines; needs prompting on uplift versus prediction.
**L5.** Distinguishes prediction from uplift, designs randomized evaluation, calibration, leakage controls.
**L6.** Frames the decision economics, runs a staged plan with go/no-go criteria, and addresses fairness and
organizational use of the model.

**Culture probe.** "Your model shows high AUC, but the retention team says it targets members who would have stayed
anyway. How do you respond, and what would you do next?"

**Follow-ups**
- What does the randomized holdout cost and how big must it be?
- How do you decide the intervention budget threshold?

### mlsd-framing-offline-eval-01
```yaml
roles: [rs, mle, ds]
levels: [L4, L5, L6]
variant: problem-framing
domain: recsys
kind: main
signal_points:
  - proposes offline metrics for ranking (NDCG, MAP, coverage, diversity) with trade-offs
  - recognizes exposure and position bias in logged data and proposes off-policy methods
  - checks metric sensitivity and the correlation between offline and online movements
  - explains the offline/online discrepancy and how to calibrate trust in an offline metric
  - online validation plan with interleaving as a first stage and an A/B test as second stage
  - explore/exploit and data collection to improve future evaluation
  - risks and monitoring after launch
  - sketches a minimal end-to-end evaluation harness in the time
```
Your team's new ranker beats production by 3% offline NDCG on logged data. Design the evaluation that decides whether to
launch it.

**Clarifying requirements the candidate should raise.** How logs were generated, propensities available, what online
metric defines success, traffic available, how many candidate models are in flight.

**Expected talking points.** Bias of logged data, inverse propensity scoring and its variance, replay, counterfactual
evaluation, interleaving to prune many rankers quickly and an A/B test for retained ones (interleaving is relative and
does not measure retention), metric correlation studies, guardrails, post-launch monitoring.

**L4.** Offline metrics and an A/B test; needs prompting on bias in logs and on pruning.
**L5.** Off-policy or replay evaluation, interleaving as first stage, discrepancy analysis and monitoring.
**L6.** Designs the evaluation system for many teams (shared harness, metric governance), decides when offline results
are trusted without an online test, and quantifies the cost of wrong launches.

**Culture probe.** "The offline gain is real but the A/B is flat. A senior colleague says to ship anyway. What do you
do?"

**Follow-ups**
- How many users would an interleaving test need compared with an A/B on retention? What does it not tell you?
- How do you detect that the offline metric has stopped predicting online results?

### mlsd-framing-risks-llm-ranker-01
```yaml
roles: [rs, mle]
levels: [L5, L6]
variant: problem-framing
domain: nlp-llm
kind: main
signal_points:
  - frames what an LLM adds to ranking (text history, cold items) and what it costs (latency, compute, serving)
  - defines the objective and training signals beyond next-item prediction
  - identifies known failure modes (popularity bias, hallucinated or unavailable titles, ignoring business constraints)
  - baseline ladder against the current production ranker and ablations
  - offline evaluation and how it would fail to predict online results
  - cost and serving trade-offs (batch scoring vs online) and availability fallbacks
  - online validation with interleaving as a first stage and an A/B test as second stage with long-term outcomes
  - data and privacy risks (verbalizing viewing history)
  - sketches a minimal end-to-end system in the time
```
A team proposes replacing a feature-based ranker with an LLM-based ranker that reads a verbalized viewing history.
Frame the problem: when is it worth it, what could go wrong, and how would you decide?

This prompt uses published work as context only. Do not ask for figures from any paper or blog post; if the candidate
cites one, ask how the idea applies here.

**Clarifying requirements the candidate should raise.** Surfaces and latency budget, current stack's pain points,
cost budget, how often the model must be refreshed, privacy rules for history in text.

**Expected talking points.** Value hypotheses (fewer hand-made features, easier to add content types), baseline and
ablation plan, constraints (catalog grounding, unavailable titles, business rules), batch precompute vs online,
evaluation (offline ranking, then interleaving, then A/B with short and long horizons), cost model, privacy and
fallback to the existing ranker.

**L5.** States hypotheses, baselines and ablations, risks specific to LLM ranking, and a staged validation plan.
**L6.** Frames cost-benefit and migration across surfaces, stopping criteria, organizational impact and safe fallbacks.

**Culture probe.** "Leadership is excited and wants it live in a quarter. You think the evidence is thin. What do you
say, to whom, and in what order?"

**Follow-ups**
- Which of your assumptions would be cheapest to test first?
- How would you keep the model from recommending titles unavailable in a member's region?
