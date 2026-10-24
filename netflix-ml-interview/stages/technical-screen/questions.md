# Question bank: technical-screen

Original prompts built from reported topics (see `brief.md` Sources). Items marked "interviewer only" must never be shown. Coding problems for `ml-coding`,
`ml-framing-coding` and `oa` live in `problems/`; PRs in `prs/`; the SQL dataset in `datasets/streaming.sql`.

## ml-coding (MLE): ML questions, about 20 minutes

### technical-screen-mlc-01
```yaml
roles: [mle]
levels: [L4, L5, L6]
variant: ml-coding
domain: recsys
kind: main
signal_points:
  - explains bias-variance with a concrete symptom (train versus validation gap)
  - states that L1 produces sparse weights and L2 shrinks them, with the reason
  - picks regularization strength on a time-based split, not a random one
  - connects regularization to sparse high-cardinality features such as title ids
```
You train a logistic regression to predict clicks on a title using millions of sparse features (title id, genre, device,
hour). Validation loss is far worse than training loss. Walk me through what you would do, and when you would choose L1 over L2.

Follow-ups:
- How do you pick the regularization strength, and on which split?
- What changes for a feature that appears only a few times?
- Elastic net: what problem does it solve that L1 alone has with correlated features?

### technical-screen-mlc-02
```yaml
roles: [mle]
levels: [L4, L5, L6]
variant: ml-coding
domain: recsys
kind: main
signal_points:
  - explains boosting as additive trees fit to residuals or gradients
  - names early stopping on a held-out set and the risk of leakage from random splits on time series
  - knows main knobs (learning rate, depth, number of trees, subsampling) and how they trade off
  - raises calibration or monitoring after deployment
```
A gradient-boosted tree model ranks candidate titles. Offline AUC keeps rising as you add trees but online results do not improve.
What is happening and how do you use early stopping correctly?

Follow-ups:
- Why can random-split validation overstate performance here?
- You lower the learning rate by 10x; what else changes?
- How do you monitor the model after launch?

### technical-screen-mlc-03
```yaml
roles: [mle]
levels: [L4, L5, L6]
variant: ml-coding
domain: recsys
kind: main
signal_points:
  - describes co-watch (item2vec style) embeddings from sessions as sequences
  - explains negative sampling and the effect of popularity on sampled negatives
  - proposes cold-start handling for new titles using content features
  - checks embeddings with nearest-neighbour sanity checks and downstream metrics
```
We want title embeddings from members' viewing sessions so that titles watched together are close. How would you train them,
and what do you do for a title released yesterday that nobody has watched yet?

Follow-ups:
- How do you choose negatives and why does it matter?
- How would you evaluate the embeddings before using them in a ranker?
- A blockbuster dominates every neighbour list. What do you change?

### technical-screen-mlc-04
```yaml
roles: [mle]
levels: [L4, L5, L6]
variant: ml-coding
domain: recsys
kind: main
signal_points:
  - defines P@K, recall@K, NDCG@K, coverage and diversity correctly
  - identifies popularity bias in offline evaluation and how to mitigate it
  - separates offline ranking metrics from online validation (interleaving then A/B)
  - knows that offline gains may not transfer because of exposure bias
```
Your new ranker improves NDCG@10 by 3% offline, but it recommends popular titles more often than the old one. Is that a good
change? How do you decide whether to ship, and what would you look at beyond NDCG?

Follow-ups:
- Which metric would show the popularity shift?
- How would interleaving help before a full A/B test?
- What bias is present in the logged data you evaluated on?

## ml-framing-coding (RS): framing and fundamentals

### technical-screen-mfc-01
```yaml
roles: [rs]
levels: [L4, L5, L6]
variant: ml-framing-coding
domain: recsys
kind: main
signal_points:
  - restates the product goal and asks what long-term outcome the surface serves
  - defines labels and exposure explicitly and names selection bias in logged data
  - proposes a primary metric, guardrails and an offline-to-online validation path
  - names at least two failure modes (feedback loop, popularity bias, novelty effects)
```
Frame this problem: "decide which titles to show in the top-left position of a member's homepage". What is the prediction
target, what data do you have, and what could go wrong?

Follow-ups:
- What is the label for a title that was never shown?
- How would you handle the fact that today's model chose what you logged?
- Which metric would you ship on, and which would block the launch?

### technical-screen-mfc-02
```yaml
roles: [rs]
levels: [L4, L5, L6]
variant: ml-framing-coding
domain: recsys
kind: main
signal_points:
  - compares supervised click prediction with a contextual bandit for choosing among images
  - explains exploration cost and logging propensities for off-policy evaluation
  - addresses reward definition (play versus quality play) and delayed feedback
```
We want to personalize which of several candidate images is shown for each title. Would you frame this as supervised learning or a
bandit? Defend your choice.

Follow-ups:
- What do you log so that you can evaluate a new policy offline?
- How do you explore without hurting members?
- What would the reward be, and how long do you wait for it?

### technical-screen-mfc-03
```yaml
roles: [rs]
levels: [L4, L5, L6]
variant: ml-framing-coding
domain: recsys
kind: main
signal_points:
  - explains AUC, NDCG and calibration and what each ignores
  - describes cross-entropy and why probabilities need calibration for downstream decisions
  - explains the bias-variance trade-off with a recommender example
  - handles ties and position bias in metric definitions
```
Compare AUC, NDCG@K and log loss as evaluation metrics for a ranker whose score is also used to decide how many rows to show.
Which one would you track and why?

Follow-ups:
- How can AUC rise while NDCG falls?
- What does calibration give you that ranking metrics do not?
- How does position bias leak into each metric?

## sql (DS): runnable SQL on `datasets/streaming.sql`

Schema (share with the candidate): `titles(title_id, name, genre, release_date)`, `users(user_id, country, signup_date)`,
`viewing_events(event_id, user_id, title_id, event_date, minutes_watched, completed)`,
`subscriptions(sub_id, user_id, plan, start_date, end_date)` (NULL end_date means active),
`ab_assignment(user_id, experiment_id, variant, assigned_at)`. The dataset is synthetic.

### technical-screen-sql-01
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: sql
domain: experimentation
kind: main
dataset: streaming
signal_points:
  - uses a window function (ROW_NUMBER) to isolate each new member's first watch
  - restricts events to on or after signup and defines new members clearly
  - breaks ties deterministically
  - sanity-checks the result against the number of new members with any event
```
Which five titles drove the most new sign-ups in February 2026? Define "drove" as the first title a new member (signed up in February)
watched on or after their signup date, and count members per title.

Follow-ups:
- What if a member's first day has two plays?
- Why is this a biased measure of "driving" sign-ups?
- How would you check the result is not dominated by one country?

Interviewer only. Reference SQL:
```sql
WITH new_users AS (
  SELECT user_id, signup_date FROM users WHERE signup_date >= '2026-02-01' AND signup_date < '2026-03-01'
), first_watch AS (
  SELECT e.user_id, e.title_id,
         ROW_NUMBER() OVER (PARTITION BY e.user_id ORDER BY e.event_date, e.event_id) AS rn
  FROM viewing_events e JOIN new_users n ON n.user_id = e.user_id AND e.event_date >= n.signup_date
)
SELECT t.title_id, t.name, COUNT(*) AS new_members_first_watch
FROM first_watch f JOIN titles t USING (title_id)
WHERE f.rn = 1
GROUP BY t.title_id, t.name
ORDER BY new_members_first_watch DESC, t.title_id
LIMIT 5;
```
Expected rows: (7, Title 07, 4), (12, Title 12, 4), (10, Title 10, 3), (1, Title 01, 2), (6, Title 06, 2).

### technical-screen-sql-02
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: sql
domain: experimentation
kind: main
dataset: streaming
signal_points:
  - defines active on a date with start_date and end_date, handling NULL end_date
  - counts distinct users, not subscription rows (resubscribers have two rows)
  - uses a LEFT JOIN or NOT EXISTS to find churned members
  - states the churn definition and its limits
```
Compute the churn rate for February 2026: among members with an active subscription on 2026-02-01, what share has no active
subscription on 2026-03-01? A subscription is active on a date if `start_date <= date` and (`end_date` is NULL or `end_date > date`).

Follow-ups:
- A member cancelled on Feb 10 and resubscribed on Feb 25. Are they churned in your definition?
- How would your query change to give churn for every month?
- What would you check before reporting this number to a PM?

Interviewer only. Reference SQL:
```sql
WITH start_active AS (
  SELECT DISTINCT user_id FROM subscriptions
  WHERE start_date <= '2026-02-01' AND (end_date IS NULL OR end_date > '2026-02-01')
), end_active AS (
  SELECT DISTINCT user_id FROM subscriptions
  WHERE start_date <= '2026-03-01' AND (end_date IS NULL OR end_date > '2026-03-01')
)
SELECT COUNT(*) AS active_feb1,
       SUM(CASE WHEN e.user_id IS NULL THEN 1 ELSE 0 END) AS churned,
       ROUND(1.0 * SUM(CASE WHEN e.user_id IS NULL THEN 1 ELSE 0 END) / COUNT(*), 4) AS churn_rate
FROM start_active s LEFT JOIN end_active e USING (user_id);
```
Expected row: (17, 5, 0.2941).

### technical-screen-sql-03
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: sql
domain: experimentation
kind: main
dataset: streaming
signal_points:
  - detects users assigned to both variants and excludes them, reporting how many
  - uses LEFT JOIN so that users with no events count as zero minutes
  - limits events to the post-assignment window
  - computes per-user outcomes before averaging per variant
  - notes sample ratio mismatch as a check
```
For experiment `row_order_v2`, per variant report the number of users, the average minutes watched in the 7 days starting on the
assignment date (`assigned_at` inclusive, 7 days exclusive), and the share of users with at least one completed view. Handle
data problems you find in `ab_assignment`.

Follow-ups:
- Are the two variants the size you expected? What test would you run?
- Why do users with no events matter for the average?
- How would you add a confidence interval for the difference?

Interviewer only. Reference SQL:
```sql
WITH assign AS (
  SELECT user_id, MIN(variant) AS variant, MIN(assigned_at) AS assigned_at, COUNT(DISTINCT variant) AS nv
  FROM ab_assignment WHERE experiment_id = 'row_order_v2' GROUP BY user_id
), clean AS (
  SELECT * FROM assign WHERE nv = 1
), per_user AS (
  SELECT c.user_id, c.variant,
         COALESCE(SUM(e.minutes_watched), 0) AS minutes_7d,
         COALESCE(MAX(e.completed), 0) AS any_completed
  FROM clean c LEFT JOIN viewing_events e
    ON e.user_id = c.user_id AND e.event_date >= c.assigned_at AND e.event_date < date(c.assigned_at, '+7 days')
  GROUP BY c.user_id, c.variant
)
SELECT variant, COUNT(*) AS users, ROUND(AVG(minutes_7d), 2) AS avg_minutes_7d,
       ROUND(AVG(any_completed), 4) AS completion_rate
FROM per_user GROUP BY variant ORDER BY variant;
```
Expected rows: (control, 20, 45.6, 0.35), (treatment, 14, 39.07, 0.1429). Data problem: user 5 has both variants (35 distinct users
in the experiment, 34 after exclusion). The 20 versus 14 split is a sample-ratio-mismatch discussion point (it is synthetic data, but the candidate should flag it).

### technical-screen-sql-04
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: sql
domain: any
kind: main
dataset: streaming
signal_points:
  - aggregates before windowing
  - uses RANK or DENSE_RANK and explains the difference for ties
  - computes share within genre with SUM() OVER (PARTITION BY ...)
  - orders output deterministically
```
For each genre, list the two most-watched titles by total minutes, with the title's share of its genre's total minutes (all titles in the genre).

Follow-ups:
- What changes if two titles tie for second place?
- Why is raw minutes a poor popularity measure for a newly released title?
- Rewrite the share without a window function.

Interviewer only. Reference SQL:
```sql
WITH g AS (
  SELECT t.genre, t.title_id, t.name, SUM(e.minutes_watched) AS minutes
  FROM viewing_events e JOIN titles t USING (title_id) GROUP BY t.genre, t.title_id, t.name
)
SELECT genre, title_id, minutes, ROUND(1.0 * minutes / SUM(minutes) OVER (PARTITION BY genre), 4) AS genre_share, rnk
FROM (SELECT g.*, RANK() OVER (PARTITION BY genre ORDER BY minutes DESC) AS rnk FROM g)
WHERE rnk <= 2 ORDER BY genre, rnk, title_id;
```
Expected rows: (comedy, 6, 491, 0.5486, 1), (comedy, 2, 404, 0.4514, 2), (documentary, 4, 834, 0.6061, 1), (documentary, 12, 542, 0.3939, 2),
(drama, 1, 744, 0.5763, 1), (drama, 5, 547, 0.4237, 2), (thriller, 7, 927, 0.5646, 1), (thriller, 3, 715, 0.4354, 2).

### technical-screen-sql-05
```yaml
roles: [ds]
levels: [L5, L6]
variant: sql
domain: any
kind: main
dataset: streaming
signal_points:
  - computes each member's first event date with a grouped subquery
  - uses date arithmetic correctly in SQLite (julianday)
  - separates members with no events from late activators and states the denominator
```
Find, per country, how many members started watching more than 14 days after signing up (late activators). Then say what the
denominator should be if the PM wants a rate.

Follow-ups:
- Do members with no events at all belong in the numerator, the denominator or neither?
- How would you test whether the rate differs across countries?

Interviewer only. Reference SQL:
```sql
SELECT u.country, COUNT(*) AS late_activators
FROM users u JOIN (SELECT user_id, MIN(event_date) AS first_date FROM viewing_events GROUP BY user_id) f USING (user_id)
WHERE julianday(f.first_date) - julianday(u.signup_date) > 14
GROUP BY u.country ORDER BY late_activators DESC, u.country;
```
Expected rows: (BR, 3), (US, 2).

## stats (DS): conceptual statistics

### technical-screen-stats-01
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: stats
domain: experimentation
kind: main
signal_points:
  - interprets a log-outcome coefficient as an approximate percentage change (exp(b)-1)
  - separates statistical significance from practical size and uses confidence intervals
  - knows R-squared does not validate causal claims and can be low in a valid randomized test
  - names heteroskedasticity-robust or clustered standard errors and multicollinearity
```
You regress `log(minutes_watched_7d)` on `treatment`, `tenure_months` and `device`, using a randomized test. The treatment coefficient
is 0.05 with a standard error of 0.02 and R-squared is 0.08. Interpret the output for a product manager and tell me what you would worry about.

Follow-ups:
- Why include `tenure_months` in a randomized test?
- Members appear multiple times in the data. What happens to the standard errors?
- Two predictors have a correlation of 0.95. Which estimates are affected?

Interviewer only. Key points: exp(0.05)-1 is about 5.1%; 95% CI is about 0.05 +/- 1.96*0.02 = [0.011, 0.089] (1% to 9%); low R-squared is fine for
estimating a randomized effect; covariates reduce variance; cluster by member; collinearity inflates standard errors of the correlated terms but not
the treatment coefficient when treatment is randomized.

### technical-screen-stats-02
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: stats
domain: experimentation
kind: main
signal_points:
  - defines type I and type II errors and links alpha and power to them
  - explains that with a fixed sample, lowering alpha increases beta
  - relates p-value to the null hypothesis and does not misstate it as the probability the null is true
  - applies the ideas to a launch decision with asymmetric costs
```
Define type I and type II errors for a test of a new homepage layout. If shipping a bad layout costs more than missing a good
one, how do you set alpha and power?

Follow-ups:
- What does a p-value of 0.03 mean, and what does it not mean?
- What happens to the type II error if you change alpha from 0.05 to 0.01 at the same sample size?
- A test is underpowered and not significant. What can you conclude?

### technical-screen-stats-03
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: stats
domain: experimentation
kind: main
signal_points:
  - explains the family-wise error rate and the false discovery rate
  - applies Bonferroni and Benjamini-Hochberg correctly to a small list
  - chooses the procedure according to the cost of false positives
  - notes dependence between tests and metrics
```
A multi-cell test compares 6 variants of a row design against control and you get p-values 0.001, 0.008, 0.012, 0.030, 0.041 and 0.20.
Which are significant at 5% under Bonferroni and under Benjamini-Hochberg? When would you prefer each?

Follow-ups:
- What is controlled in each case?
- What if you looked at 20 metrics per variant?

Interviewer only. Bonferroni threshold 0.05/6 = 0.00833: rejects 0.001 and 0.008 (2 rejections). BH thresholds i/6*0.05 = 0.0083, 0.0167, 0.025, 0.0333, 0.0417,
0.05: largest i with p(i) <= threshold is i=5 (0.041 <= 0.0417), so 5 rejections. Bonferroni controls the family-wise error rate; BH controls the expected false discovery proportion
under independence or positive dependence.

### technical-screen-stats-04
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: stats
domain: experimentation
kind: main
signal_points:
  - computes a standard error and t-statistic for a difference in means
  - states the CLT assumptions and why it applies to sample means, not raw data
  - gives a confidence interval and interprets it correctly
  - notes heavy tails and when the t approximation is questionable
```
Treatment has mean 52.0 minutes and control 50.0 minutes, each with standard deviation 12 and 400 members. Compute the
t-statistic, state what the CLT gives you here, and give a 95% confidence interval for the difference.

Follow-ups:
- Watch time is heavily right-skewed. Does the CLT still help at n = 400? How would you check?
- What changes if the members are not independent?

Interviewer only. SE = 12*sqrt(2/400) = 0.849; t = 2/0.849 = 2.36 (two-sided p about 0.018); 95% CI about [0.34, 3.66].

### technical-screen-stats-05
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: stats
domain: experimentation
kind: main
signal_points:
  - describes the nonparametric bootstrap procedure step by step
  - chooses a percentile or BCa interval and explains the resampling unit (member, not event)
  - knows where the bootstrap fails (extremes, tiny samples, dependent data) and when to use it (medians, quantiles, ratios)
```
The treatment lowers the mean play delay but you suspect the median moved the other way. How would you build a confidence interval for the
difference in medians, and what is the resampling unit?

Follow-ups:
- Why is resampling events instead of members wrong?
- When does the bootstrap give a poor answer?
- How many resamples do you need?

### technical-screen-stats-06
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: stats
domain: experimentation
kind: main
signal_points:
  - computes minimum detectable effect from sigma, alpha, power and n, or sample size from a target MDE
  - states the effect of variance reduction on MDE
  - discusses practical constraints (duration, novelty effects, traffic)
```
Standard deviation of weekly minutes is 10. With 10,000 members per arm, alpha 0.05 two-sided and 80% power, what MDE can you detect?
How many members per arm would you need to detect 0.5 minutes?

Follow-ups:
- A pre-experiment covariate explains 30% of the variance (R-squared 0.3). What happens to the MDE?
- What if you can only run the test for one week?

Interviewer only. MDE = (1.96 + 0.84) * 10 * sqrt(2/10000) is about 0.40 minutes. Sample size n = 2 * (2.80 * 10 / 0.5)^2 is about 6,280 per arm. A covariate with R-squared
0.3 scales the standard deviation by sqrt(0.7), so the MDE falls by about 16%.

### technical-screen-stats-07
```yaml
roles: [ds]
levels: [L5, L6]
variant: stats
domain: causal-inference
kind: main
signal_points:
  - distinguishes ATE, ITT and TOT/ATT
  - computes the Wald estimator and names the IV assumptions (relevance, independence, exclusion, monotonicity)
  - states that IV identifies the local effect on compliers
  - explains why comparing exposed to unexposed members inside treatment is biased
```
We randomly encourage half of members with a notification to try a new feature; only 40% of the encouraged members actually use it,
and no unencouraged member can. Average watch time is 0.6 minutes higher in the encouraged group. What are the ITT and the effect
on those who use the feature, and under what assumptions?

Follow-ups:
- Why not compare users to non-users?
- Which members does the estimate describe?
- What if the notification itself increases watch time for non-users?

Interviewer only. ITT = 0.6. With one-sided non-compliance the Wald estimator is ITT / take-up = 0.6 / 0.4 = 1.5 minutes (TOT, which equals the LATE for compliers
here). Assumptions: independence (randomization), relevance, exclusion restriction, monotonicity (trivially true with one-sided non-compliance).

## fundamentals-pr-review (MLE)

### technical-screen-fpr-01
```yaml
roles: [mle]
levels: [L4, L5, L6]
variant: fundamentals-pr-review
domain: any
kind: main
signal_points:
  - writes the attention computation softmax(QK^T/sqrt(d_k))V and says what Q, K and V are
  - explains the sqrt(d_k) scaling and causal masking
  - states the cost in sequence length (quadratic) and the memory consequence
```
Explain self-attention step by step: what are Q, K and V, how is the output computed, and why is there a scaling factor?

Follow-ups:
- What is the time and memory complexity in sequence length?
- What does a causal mask do and where is it applied?
- What changes with multi-head attention?

### technical-screen-fpr-02
```yaml
roles: [mle]
levels: [L4, L5, L6]
variant: fundamentals-pr-review
domain: nlp-llm
kind: main
signal_points:
  - states that the KV cache stores keys and values of previous tokens to avoid recomputation during decoding
  - computes memory growth with layers, heads, head dimension, sequence length and batch
  - distinguishes prefill from decode and names bandwidth as the decode bottleneck
```
What does a KV cache store, why does it speed up generation, and what does it cost?

Follow-ups:
- Estimate the cache size for a model with L layers, H heads of dimension d, sequence length n and batch b.
- How does prefill differ from decode in compute and memory behavior?
- What techniques reduce cache size?

### technical-screen-fpr-03
```yaml
roles: [mle]
levels: [L4, L5, L6]
variant: fundamentals-pr-review
domain: any
kind: main
signal_points:
  - explains L1 versus L2 geometrically and in terms of gradients (constant versus proportional shrinkage)
  - ties L1 to sparsity and feature selection, and L2 to stability under collinearity
  - mentions Bayesian priors (Laplace versus Gaussian) or weight decay in optimizers
```
Compare L1 and L2 regularization: what does each do to the weights, and when would you pick each?

Follow-ups:
- Why does L1 give exact zeros and L2 does not?
- Does weight decay equal L2 regularization with Adam?

### technical-screen-fpr-pr-01
```yaml
roles: [mle]
levels: [L4, L5, L6]
variant: fundamentals-pr-review
domain: ml-platform
kind: main
pr: rolling-watch-features
signal_points:
  - detects same-day future events or label leakage in the window
  - detects the UTC versus device-local time mismatch
  - detects the unbounded merge and estimates its size
  - raises training/serving skew and proposes feature logging or a shared definition
  - ranks findings by impact and states what to ask the author to change
```
Review the pull request in `prs/rolling-watch-features/pr.diff` (show with `context.md`). The unit test passes. What would worry you in production, in order of priority?

Follow-ups:
- Walk me through the rows that fall in the window for one member with a click.
- How would you serve these three features at request time and for the nightly batch?

Interviewer only: use `prs/rolling-watch-features/issues.md` for expected findings, the hint ladder and the serving follow-up.

### technical-screen-fpr-pr-02
```yaml
roles: [mle]
levels: [L4, L5, L6]
variant: fundamentals-pr-review
domain: ml-platform
kind: main
pr: backfill-title-popularity
signal_points:
  - detects that the append write is not idempotent under retry or concurrent runs
  - detects fan-out from the slowly changing dimension join
  - detects point-in-time leakage from the table-wide mean and from computed_at
  - detects the per-day LabelEncoder skew
  - proposes atomic publish and stable versioned ids for serving
```
Review the pull request in `prs/backfill-title-popularity/pr.diff` (show with `context.md`). The unit test passes. What would worry you before the 18-month backfill runs tonight?

Follow-ups:
- What happens if the orchestrator retries a failed task?
- How do you serve these features to the cold-start ranker (20 ms p99) and to the nightly trainer?

Interviewer only: use `prs/backfill-title-popularity/issues.md` for expected findings, the hint ladder and the serving follow-up.

## intern-project-coding (format reported for the ML Intern loop)

### technical-screen-intern-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: intern-project-coding
domain: any
kind: main
signal_points:
  - states the problem, baseline and metric in two minutes
  - separates their own contribution from the team's
  - names one decision they would reverse and why
  - gives a concrete result with scale or effect size
```
Pick the project from your background you know best. In three minutes: the problem, the baseline, the metric, what you personally built, and the result.

Follow-ups:
- What was the hardest bug or data issue?
- What would you do differently with another month?
- How did you validate that the result was real?

### technical-screen-intern-02
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: intern-project-coding
domain: any
kind: main
signal_points:
  - explains the evaluation protocol and its leakage risks
  - describes an ablation or comparison with a stronger baseline
  - connects the work to deployment or decision-making
```
For the same project: how did you evaluate it, what could have made the numbers look better than reality, and how would the work run in production?

Follow-ups:
- How did you split the data?
- Which baseline was hardest to beat?
- Who would use it and how?

## oa (asynchronous online assessment): multiple choice

Multiple-choice items for the OA. The two coding problems are `problems/oa-sparse-matmul-coo` and `problems/oa-format-convert-impute`. Answer keys are interviewer only.

### technical-screen-oa-mc-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: oa
domain: any
kind: main
signal_points:
  - applies Bayes' rule with base rate, sensitivity and false positive rate
  - computes the posterior as about 15%
```
A rare condition affects 1% of members' accounts (fraud). A detector flags 90% of fraudulent accounts and also flags 5% of legitimate ones. An account
is flagged. The probability that it is fraudulent is closest to: (A) 90%  (B) 50%  (C) 15%  (D) 5%.

Answer key (interviewer only): C. P = 0.009 / (0.009 + 0.0495) = 0.154.

### technical-screen-oa-mc-02
```yaml
roles: [mle, rs]
levels: [L4, L5, L6]
variant: oa
domain: any
kind: main
signal_points:
  - computes a two-layer forward pass with ReLU by hand
```
A network has input x = [1, 2]. Layer 1: W1 = [[1, 0], [-1, 1]], b1 = [0, 1], followed by ReLU. Layer 2: w2 = [2, 1], b2 = -1 (a scalar output, no activation).
The output is: (A) 2  (B) 3  (C) 4  (D) 5.

Answer key (interviewer only): B. h = ReLU([1*1+0*2+0, -1*1+1*2+1]) = [1, 2]; output = 2*1 + 1*2 - 1 = 3.

### technical-screen-oa-mc-03
```yaml
roles: [mle, rs]
levels: [L4, L5, L6]
variant: oa
domain: any
kind: main
signal_points:
  - applies k-nearest-neighbours with different k and understands the effect of k on the decision
```
One-dimensional training points with labels: 1:A, 2:A, 3.5:B, 5:A, 6:A. A query x = 3.4 is classified with k-nearest neighbours (Euclidean distance, majority vote). The prediction is:
(A) A for k = 1 and A for k = 3  (B) B for k = 1 and A for k = 3  (C) B for k = 1 and B for k = 3  (D) A for k = 1 and B for k = 3.

Answer key (interviewer only): B. For k = 1 the nearest point is 3.5 (B). For k = 3: 3.5 (B), 2 (A, distance 1.4), 5 (A, distance 1.6) so A.

### technical-screen-oa-mc-04
```yaml
roles: [mle, rs]
levels: [L4, L5, L6]
variant: oa
domain: nlp-llm
kind: main
signal_points:
  - states the quadratic dependence of self-attention on sequence length
  - separates the attention score computation from the position-wise feed-forward cost
```
In a transformer layer, you double the input sequence length (same hidden size and batch). The cost of computing the attention score matrix QK^T:
(A) doubles  (B) quadruples  (C) grows 8 times  (D) is unchanged.

Answer key (interviewer only): B. The score matrix is n by n, so cost and memory scale with n squared; the feed-forward cost only doubles.

### technical-screen-oa-mc-05
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: oa
domain: experimentation
kind: main
signal_points:
  - computes a standard error and t-statistic for a difference in means
  - computes the MDE from sigma, alpha, power and n
```
Two arms of 400 members each have mean 52 and 50 minutes, standard deviation 12. The two-sided t-statistic is closest to: (A) 0.9  (B) 1.4  (C) 2.4  (D) 4.7.

Answer key (interviewer only): C. SE = 12*sqrt(2/400) = 0.849; t = 2/0.849 = 2.36.

### technical-screen-oa-mc-06
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: oa
domain: causal-inference
kind: main
signal_points:
  - separates ITT from the effect on those who take the treatment
  - applies the Wald estimator under one-sided non-compliance
```
Members are randomly encouraged to use a feature. Take-up is 40% in the encouraged group and 0% in the other. Watch time is 0.6 minutes higher in the encouraged group.
The effect of using the feature on those who take it up is: (A) 0.24  (B) 0.6  (C) 1.0  (D) 1.5.

Answer key (interviewer only): D. TOT = ITT / take-up = 0.6 / 0.4 = 1.5.
