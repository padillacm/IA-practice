# Questions: experimentation

All numbers in prompts are synthetic assumptions for the exercise, not Netflix data. Banks are built from reported
topics and Netflix-published practices. Each main prompt lists the `signal_points` the interviewer uses to pace
the round.

# Variant: design-case

### exp-design-ad-frequency-cap-01
```yaml
roles: [ds, mle, rs]
levels: [L4, L5, L6]
variant: design-case
domain: ads
kind: main
signal_points:
  - states the hypothesis and decision (what frequency cap, trading revenue against member experience)
  - chooses the randomization unit (member or account across devices, not impression) and explains why
  - defines primary metric (revenue per member), guardrails (retention, hours watched, ad completion) and the horizon
  - does the sample size arithmetic with variance and a minimum detectable effect, in the room
  - handles heavy-tailed revenue (winsorize, quantiles or log) and CUPED or other variance reduction
  - treatment arms (several caps) and multiple comparisons
  - novelty and fatigue effects, duration of at least a full weekly cycle
  - interference between advertisers (shared budget and pacing) and with other concurrent tests
  - long-term effect on retention versus short-term revenue, and the decision rule
```
We run an ad-supported plan. Marketing wants to know whether to cap how many times a member sees the same ad per
week. Design and size an experiment to decide the cap.

**Interviewer data to offer when asked.** Revenue per member per week has mean 4.00 and standard deviation 12.00
(heavy right tail). Assume the business cares about a 1% change in revenue per member (delta 0.04) and a
non-inferiority bound of 0.2 percentage points on monthly retention. Baseline monthly retention 90%. Assume
millions of eligible members.

**Expected talking points.** Hypothesis and cap options (for example no cap, 3, 5); randomize on member (or account)
so frequency is consistent across devices; revenue sizing: n per arm ~ 15.7 * 12^2 / 0.04^2 ~ 1.4 million per arm
(ignoring variance reduction), CUPED on pre-period revenue to cut it; retention guardrail needs more sample or a
longer run; run at least two weekly cycles; check for novelty and ad fatigue; advertiser interference through budget
pacing; analysis with winsorized or bootstrap CIs; multiple-arm correction; decision rule combining revenue lift and
retention bound.

**L4.** Member-level randomization, a primary metric, a sample size formula and an A/B; needs prompting on guardrails,
heavy tails and duration.
**L5.** Does the power math with the given variance, adds CUPED, guardrails with non-inferiority, multiple arms,
novelty and a decision rule.
**L6.** Designs the program: sequential or staged rollout, long-term holdout for retention, interference through
budgets, platform support for repeated cap tests, and the cost of a wrong decision.

**Culture probe.** "The result at two weeks shows a +1.2% revenue lift with a retention guardrail that is
inconclusive. The VP wants to ship the cap tomorrow. What do you say?"

**Follow-ups**
- How does your sample size change if you apply CUPED with a correlation of 0.6 between pre- and post-revenue?
- Should the cap be randomized per ad, per member or per advertiser? Defend the unit.
- What do you do if the cap helps revenue short term and retention drops slowly after week 4?

### exp-design-row-ordering-retention-01
```yaml
roles: [ds, mle, rs]
levels: [L4, L5, L6]
variant: design-case
domain: recsys
kind: main
signal_points:
  - states the hypothesis for a personalized row-ordering model and the decision
  - treatment definition and control (current ordering) with the exposure to rows and overlap between rows
  - chooses the randomization unit (member) and handles shared profiles and devices
  - primary short-term metric and long-term outcome (retention) with their time scales and surrogates
  - handles row overlap (the same title in several rows) in metric definition and attribution
  - power and duration for a retention outcome (small effect, long horizon) and how to use surrogate metrics
  - interference and other concurrent tests (artwork, algorithm), triggered analysis
  - interleaving as a quick first stage for ranker variants, and that it does not replace the A/B for retention
  - heterogeneous effects (new vs tenured members, devices) and novelty
```
Design an A/B test for a new personalized row-ordering model on the homepage. Rows overlap in titles (the same title
can appear in several rows). The long-term outcome of interest is member retention.

**Interviewer data to offer when asked.** Baseline 30-day retention is 92%; the business cares about a 0.1 percentage
point change; weekly hours watched per member has mean 7 and standard deviation 9. Millions of eligible members.
Several other tests run concurrently on the homepage.

**Expected talking points.** Hypothesis; randomize at member level; retention power: for p=0.92, variance 0.0736,
detecting 0.001 needs n per arm ~ 15.7 * 0.0736 / 0.001^2 ~ 1.2 million, so use a longer horizon, CUPED, and
surrogate metrics (hours watched, streaming days) validated for their relation to retention; define engagement with
rows overlapping (count a title once per member-session, attribute to the first or any row) and avoid
double-counting; novelty and learning effects; check sample ratio mismatch and balance; concurrent tests (factorial
or orthogonal assignment, interaction checks); heterogeneous effects by tenure and device; interleaving to compare
several row-ordering variants cheaply, then an A/B for the finalists because interleaving is relative and does not
measure retention.

**L4.** Member-level A/B with engagement and retention metrics; needs prompting on overlap, power for retention and
concurrent tests.
**L5.** Handles overlap attribution, retention power with surrogates, concurrent tests, SRM checks and heterogeneity,
and proposes interleaving then A/B.
**L6.** Builds a measurement strategy: validated surrogates, long-term holdouts, platform guardrails and decision
rules for many ranking variants, and the cost-benefit of waiting for retention.

**Culture probe.** "Engagement is up and the retention read is not yet available. Product wants to ship. What do you
claim today and what do you refuse to claim?"

**Follow-ups**
- How would you validate that hours watched is a good surrogate for retention?
- Two other tests changed the homepage during your run. What do you check?
- Why not run interleaving only and skip the A/B?

### exp-design-artwork-test-01
```yaml
roles: [ds, mle, rs]
levels: [L4, L5, L6]
variant: design-case
domain: experimentation
kind: main
signal_points:
  - states the hypothesis for a new artwork selection policy and the decision
  - defines the unit (member) and the exposure (a member sees many titles, each with different artwork)
  - chooses metrics beyond clicks (play, completion, retention) and handles clicks without satisfaction
  - handles title-level versus member-level analysis and the dependence of observations within a member
  - explore/exploit in the treatment (bandit) and how it complicates the A/B analysis
  - interference between artwork tests, algorithm tests and encoding tests at the same time
  - heterogeneity (new titles vs catalog, popular vs niche) and multiple comparisons across titles
  - power and duration calculation
```
Design an A/B test to evaluate a personalized artwork selection policy (a bandit that picks one image per title per
member) against the current policy.

**Interviewer data to offer when asked.** The primary metric is the share of impressions that lead to a play of at
least two minutes (baseline 2.5%); members have on average 200 impressions per week; the effect of interest is a 2%
relative lift. Treat impressions within a member as correlated with intraclass correlation 0.1.

**Expected talking points.** Randomize at member level, analyze at member level (ratio metrics, delta method or
bootstrap by member) or use a cluster-robust analysis; design effect 1 + (m-1)rho with m=200, rho=0.1 inflates
variance by ~20; explore/exploit inside treatment (the policy learns during the test, so a ramp or burn-in); metrics:
play share, abandonment, retention; guardrails like misleading images; heterogeneity by title type; many-title
multiple testing and FDR; interference from other concurrent tests (artwork, algorithm, encoding); novelty.

**L4.** Member-level A/B with play share metric; needs prompting on correlation between impressions and on bandit
learning.
**L5.** Handles clustering and the design effect, bandit-in-treatment complications, heterogeneity with FDR control and
concurrent tests.
**L6.** Designs the experimentation approach for ongoing policy learning (holdouts, off-policy evaluation to
complement the A/B) and platform handling of overlapping tests.

**Culture probe.** "The new policy raises clicks by 3% but plays of two minutes or more are flat. A designer is
convinced it is a win. How do you handle the disagreement?"

**Follow-ups**
- What is your analysis unit and why not impressions?
- The bandit in treatment keeps learning. Does your A/B still estimate a meaningful effect?
- How do you detect interaction with a simultaneous encoding test?

### exp-design-interleaving-to-ab-01
```yaml
roles: [ds, mle, rs]
levels: [L4, L5, L6]
variant: design-case
domain: experimentation
kind: main
signal_points:
  - explains the two-stage process (interleaving to prune many ranker variants, then A/B for survivors)
  - describes the interleaving mechanism (for example team draft with a coin toss for who picks first) and attribution of plays to the contributing ranker
  - explains position bias handling (a video equally likely from each ranker in each position)
  - states that interleaving is a relative measure and does not measure retention, so it does not replace the A/B
  - discusses sensitivity advantage (far fewer members needed) and the check that interleaving agrees with A/B outcomes
  - limitations (implementation complexity, business logic interfering, surfaces where the mix is unnatural)
  - traffic allocation across many variants and the pruning rule
  - A/B second stage design (metrics, power, duration, guardrails)
```
A team has 12 candidate ranking models for the homepage. Design the experimentation plan to choose one to launch.

**Interviewer data to offer when asked.** Traffic available for experimentation is limited. The final launch
criterion is a long-term retention and engagement improvement.

**Expected talking points.** Stage 1: interleave pairs (or each variant against the control) with a team-draft style
procedure, attribute watch hours to the contributing ranker, compute preference; this needs far fewer members than
an A/B on the same metric; use it to discard variants. Stage 2: A/B test the top 1 to 3 for retention and
engagement with guardrails. Caveats: interleaving is a relative measure and does not measure retention, so
alternatives are validated by A/B; interleaving complexity and business logic interference; validate agreement
between interleaving and A/B on past launches; multiple comparisons among 12 variants.

**L4.** Mentions interleaving and A/B but may mix up their roles; needs prompting on the mechanism, bias and why the
second stage is required.
**L5.** Explains the mechanism, bias handling and limits, sets pruning and traffic rules, and designs the A/B stage
with power and guardrails.
**L6.** Builds the program: metric validation between stages, error budgets (false pruning of a good variant), reuse
across teams and platform requirements.

**Culture probe.** "A senior engineer says interleaving already shows variant 7 wins by a large margin and the A/B is
a waste of traffic. Respond."

**Follow-ups**
- Why does a video need to be equally likely to come from either ranker in each position?
- How would you check that interleaving results predict A/B results?
- What do you lose if interleaving is applied to a surface with a carousel layout?

### exp-design-geo-quasi-01
```yaml
roles: [ds, mle, rs]
levels: [L5, L6]
variant: design-case
domain: causal-inference
kind: main
signal_points:
  - recognizes when member-level randomization is not feasible (marketing, network or market-level effects)
  - proposes a geo experiment or quasi-experiment with matched markets, difference-in-differences or synthetic control
  - states the identifying assumptions (parallel trends, no spillover across geographies) and how to test them
  - power with few units (markets) and the use of pre-period data
  - inference with few clusters (permutation or randomization inference, bootstrap)
  - validity threats (concurrent campaigns, seasonality, spillover) and sensitivity analysis
  - decision rule and what claims the evidence supports
```
Marketing wants to measure the incremental effect of a billboard and social campaign for a new series on sign-ups.
You cannot randomize individual members. Design the measurement.

**Interviewer data to offer when asked.** There are 30 comparable markets. Weekly sign-ups per market are measured for
12 weeks before launch. Campaign spend can be allocated per market.

**Expected talking points.** Randomize markets or pick matched markets; difference-in-differences or synthetic
control using pre-period; check parallel trends in pre-period; few clusters so use randomization inference or
permutation; power depends on pre-period correlation; spillover across adjacent markets; seasonality and concurrent
events; report intervals not just point estimates.

**L5.** Chooses a geo design, states assumptions and tests them, and handles few-cluster inference.
**L6.** Designs a measurement program (repeated geo tests, calibrating observational models with experiments) and
states clear limits on claims.

**Culture probe.** "The campaign team already declared success from a before-and-after chart. How do you raise your
doubts?"

**Follow-ups**
- How many markets do you assign to treatment and why?
- How do you decide whether neighboring markets contaminate the control?

# Variant: analysis-case

### exp-analysis-quantile-effects-01
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: analysis-case
domain: experimentation
kind: main
signal_points:
  - notices that a mean increase with a median decrease means the distribution shape changed
  - proposes looking at quantiles (for example p10, p50, p90, p99) and the full distribution
  - explains quantile treatment effects, quantile regression or quantile bootstrapping and their interpretation
  - interprets the business meaning (a long tail of slow starts versus a typical improvement)
  - uncertainty for quantiles (bootstrap) and sample size for tail quantiles
  - heterogeneity as a possible cause (a subgroup got worse, another better)
  - recommendation with a stated decision rule and next experiment
```
An encoding change was tested. For video play delay (seconds), the treatment arm's mean is higher than control (2.31
vs 2.20, p=0.02), but the median is lower (1.10 vs 1.18, p=0.01). Product asks: "did it help or hurt?" Walk me
through how you would analyze it and what you would recommend.

**Interviewer data to offer when asked.** Each arm has about 4 million plays. Percentiles for control: p10 0.40, p50
1.18, p90 4.5, p99 12.0. For treatment: p10 0.38, p50 1.10, p90 4.9, p99 15.0.

**Expected talking points.** The change improves the typical experience but worsens the tail; mean is dominated by
the tail; compute quantile treatment effects with bootstrap CIs; tail effects matter for member experience; segment
by device and network to find where the tail worsens; consider a guardrail on p99; decision depends on the cost of
tail experiences; maybe ship to a subset, fix the tail, rerun.

**L4.** Notes the contradiction and asks for percentiles; needs prompting on bootstrap and interpretation.
**L5.** Computes quantile effects with CIs, finds the tail cause by segmentation and gives a conditional
recommendation.
**L6.** Defines quantile-based guardrails for the platform, sets up how decisions on distributional changes are made,
and weighs cost to the experience.

**Culture probe.** "The encoding team insists the median is what members feel and wants to ship. Do you agree?"

**Follow-ups**
- How would you bootstrap a CI for the difference in p99? What is the sample size concern?
- How does the unit of analysis (play versus member) change the answer?

### exp-analysis-bootstrap-ci-01
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: analysis-case
domain: experimentation
kind: main
signal_points:
  - chooses the bootstrap for a statistic with an unknown or messy sampling distribution (ratio, median, quantile)
  - resamples at the randomization unit (member) not the observation, and explains why
  - describes percentile and bootstrap-t or BCa intervals and their trade-offs
  - number of resamples and Monte Carlo error; compute cost on large data (compression, Poisson bootstrap)
  - recognizes when the bootstrap fails (extreme quantiles, tiny samples, heavy tails)
  - compares with the delta method for ratio metrics
  - communicates the interval correctly (not as a probability that the effect is in the interval)
```
An A/B test compares revenue per member between arms. A teammate reports a mean difference of +0.8% with a bootstrap
95% CI of [-0.3%, 1.9%], but resampled individual play events rather than members. A second metric is the ratio of
completed plays to started plays. Critique the analysis and say how you would redo it.

**Interviewer data to offer when asked.** Members have between 1 and 600 events; revenue is highly skewed; there are
5 million members per arm.

**Expected talking points.** Event-level resampling ignores within-member correlation and understates variance, so
the CI is too narrow; resample members (cluster bootstrap) or use the delta method for ratios; the Poisson bootstrap
or pre-aggregation for scale; percentile vs BCa; number of resamples; heavy tails, winsorization trade-offs;
interpreting the CI as a procedure, not a probability about the parameter.

**L4.** Identifies the wrong resampling unit; needs prompting on the ratio metric and scale.
**L5.** Fixes the unit, handles the ratio with the delta method or cluster bootstrap, and explains compute choices.
**L6.** Designs a platform-level approach (compressed data, standard intervals, validation by A/A tests) and sets
standards for reporting.

**Culture probe.** "Your corrected CI now crosses zero and the earlier report had been sent to leadership. How do you
communicate the correction?"

**Follow-ups**
- How would you verify that your intervals have correct coverage?
- When does the bootstrap give a poor interval for a quantile?

### exp-analysis-heterogeneous-effects-01
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: analysis-case
domain: causal-inference
kind: main
signal_points:
  - distinguishes pre-specified subgroup analysis from exploratory data dredging
  - controls for multiple subgroup comparisons (FDR, hierarchical or interaction tests)
  - estimates conditional average treatment effects with interaction terms or a causal forest or meta-learners
  - discusses sample size and noise in subgroups
  - checks that segment membership is not affected by treatment
  - separates statistical from practical significance and the decision (targeted rollout)
  - proposes a validation (holdout or follow-up experiment) before acting on heterogeneity
```
A new homepage layout shows an overall effect of +0.3% hours watched (p=0.04). Slicing by 20 segments (country, device,
tenure and plan), the analyst highlights one segment, mobile users in new markets, with +4.1% (p=0.003), and proposes
launching only there. Evaluate and say what you would do.

**Interviewer data to offer when asked.** The segment holds 2% of members. No segments were pre-registered. A
second segment shows -2.0% (p=0.04).

**Expected talking points.** Twenty or more slices at 0.05 give about one false positive; correct with
Benjamini-Hochberg or Bonferroni; pre-registration versus exploration; interaction test; effect shrinkage
(winner's curse); a validation experiment on the segment; for broader heterogeneity use causal forest or X-learner
with honest estimation; check segment definitions are pre-treatment; decision to personalize needs value of targeting
and a holdout.

**L4.** Notices the multiple slices; needs prompting on correction and validation.
**L5.** Applies FDR correction, discusses winner's curse, designs the follow-up test and a CATE approach.
**L6.** Builds the policy: a pre-registered heterogeneity framework, uplift targeting evaluation and organization-wide
rules for subgroup claims.

**Culture probe.** "The PM already told a market lead that mobile in new markets is a big winner. How do you reset the
expectation?"

**Follow-ups**
- What sample size would you need to confirm the segment effect?
- How do you evaluate a policy that targets by predicted treatment effect?

### exp-analysis-cuped-variance-01
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: analysis-case
domain: experimentation
kind: main
signal_points:
  - explains CUPED (adjusting the metric with a pre-experiment covariate) and why it reduces variance without bias
  - computes theta = cov(X, Y) / var(X) and the variance reduction factor 1 - rho^2
  - requires the covariate to be pre-treatment and unaffected by treatment
  - chooses covariates (pre-period metric) and discusses stratification or regression adjustment alternatives
  - handles members without pre-period data (new members)
  - explains the effect on the required sample size or test duration
  - checks that point estimate is unchanged in expectation and validates by A/A tests
```
A test of a new recommendations model on weekly hours watched shows a lift of +0.5% with a 95% CI of [-0.4%, +1.4%].
The team wants to run it three more weeks to get significance. Propose an alternative and quantify it.

**Interviewer data to offer when asked.** Pre-experiment hours (weekly average over the previous 4 weeks) correlate
with in-experiment hours at 0.7 for tenured members; 18% of members are new with no history.

**Expected talking points.** CUPED with the pre-period average: variance factor 1 - 0.49 = 0.51, so the CI narrows by
about 29% (sqrt(0.51) ~ 0.71) for tenured members; new members handled by a separate stratum or covariate default;
checking balance and covariate pre-treatment status; regression adjustment; the equivalent sample size reduction
(about half); validate with an A/A test; avoid post-treatment covariates.

**L4.** Describes CUPED roughly; needs prompting on the formula and new members.
**L5.** Quantifies the variance reduction, handles new members, validates and compares with post-stratification.
**L6.** Designs a platform-level variance reduction strategy (standardized covariates, regularly validated), and
weighs it against running longer.

**Culture probe.** "The team insists extending the test is simpler. How do you argue for the adjusted analysis
without making them feel the earlier plan was wrong?"

**Follow-ups**
- What if the covariate was measured partly after exposure began?
- Does CUPED change the estimand?

### exp-analysis-multiple-testing-peeking-01
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: analysis-case
domain: experimentation
kind: main
signal_points:
  - identifies peeking (repeated significance checks) as inflating the type I error
  - proposes fixed-horizon discipline or sequential methods (alpha spending, always-valid p-values)
  - identifies the multiple-metrics, multiple-arms and multiple-segments problem
  - distinguishes family-wise error control from false discovery rate and picks one with a reason
  - sample ratio mismatch and other validity checks before interpreting results
  - proposes pre-registration of the primary metric and a decision rule
  - recommendation for the specific case with what claims are supported
```
A test with 4 arms and 25 metrics was checked daily for 14 days. On day 9 the dashboard showed one arm significant on
one metric (p=0.03) and the team stopped the test and shipped that arm. Critique the process and say what the evidence
supports.

**Interviewer data to offer when asked.** The planned duration was 28 days. The sample ratio check on day 9 was not
run. The other 24 metrics for that arm were not significant.

**Expected talking points.** Daily peeking inflates false positives (roughly several times the nominal rate over 14
looks); 4 arms times 25 metrics is 100 comparisons so about 5 false positives expected at 0.05; use a
pre-registered primary metric, sequential tests if early stopping is wanted, BH-FDR for secondary metrics;
check SRM; the finding is a hypothesis, not a launch justification; rerun or continue to the planned horizon.

**L4.** Identifies peeking and multiple comparisons; needs prompting on methods and SRM.
**L5.** Quantifies the inflation, proposes sequential or fixed-horizon plans, FDR, and SRM, and gives a conditional
recommendation.
**L6.** Designs the platform guardrails (always-valid inference, automatic SRM checks, decision logs) and the
organizational norms for stopping.

**Culture probe.** "The test owner is a senior leader's favorite project. How do you deliver this critique?"

**Follow-ups**
- If the team insists on early stopping, what method would you give them?
- How would you decide between Bonferroni and Benjamini-Hochberg here?

### exp-analysis-interference-network-01
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: analysis-case
domain: causal-inference
kind: main
signal_points:
  - identifies interference (SUTVA violation) and its mechanisms (social sharing, shared inventory, marketplace, cluster)
  - quantifies the bias direction (usually underestimates or overestimates the global effect)
  - proposes designs to address interference (cluster randomization, geo or market-level, switchback, two-sided randomization)
  - discusses power loss from clustering and the design effect
  - detects interference empirically (compare exposure levels, ego-network designs)
  - handles users in several overlapping tests
  - recommendation matching the specific mechanism
```
A team tests a feature that lets members share a title with friends via a link. The A/B test (member-level
randomization) shows no effect on the number of titles played, though usage of the feature is high. A teammate says
"no effect". Evaluate.

**Interviewer data to offer when asked.** Treated members share links with friends, and 60% of friends are in the control
group.

**Expected talking points.** Friends in control receive links from treated members, so control is contaminated and the
estimated difference understates the effect; the effect on the total system is not identified by this design;
cluster randomization on friend graph communities, ego-network randomization; power loss; measurement of
spillovers; a two-stage design; also overlapping tests and platform handling.

**L4.** Notices contamination; needs prompting on designs to fix it.
**L5.** Gives bias direction and mechanism, cluster-based redesign, power implications and measurement of spillover.
**L6.** Designs an interference-aware experimentation approach for the organization (graph-cluster infra,
switchback where applicable) and states what claims remain valid.

**Culture probe.** "The team wants to cancel the feature based on 'no effect'. How do you intervene, and how do you
keep trust?"

**Follow-ups**
- Which direction is the bias and how do you know?
- What would a switchback test look like for a shared resource such as a content server?

### exp-analysis-quasi-experiment-01
```yaml
roles: [ds]
levels: [L5, L6]
variant: analysis-case
domain: causal-inference
kind: main
signal_points:
  - identifies why an observational comparison is biased (selection, confounding)
  - proposes difference-in-differences, synthetic control or regression discontinuity as fitting the case
  - states and tests assumptions (parallel pre-trends, no anticipation, no spillover)
  - inference with few treated units (permutation, placebo tests)
  - sensitivity analysis and robustness (alternative controls, pre-period window)
  - compares with an experiment and states what claims are supportable
  - calibrates the observational estimate against experiments where available
```
A new series launched in one country only and the analytics team reports that sign-ups rose 15% in that country
versus the previous month. They claim the series caused it. Evaluate the claim and propose an analysis.

**Interviewer data to offer when asked.** Twelve comparable countries did not get the launch. Weekly sign-ups are
available for 52 weeks before. A pricing promotion ran in the launch country two weeks before launch.

**Expected talking points.** Before-after confounded by trend, seasonality and the promotion; use difference-in-
differences or synthetic control with the 12 control countries, check pre-trends, placebo tests over time and
countries; few units so permutation inference; the promotion is a confound and may need a different identification
strategy; report an interval and caveats; if possible, follow with a geo experiment to calibrate.

**L5.** Rejects the before-after claim, proposes DiD or synthetic control with checks and addresses the promotion.
**L6.** Treats it as a measurement strategy: calibration against experiments, organizational guidance on causal claims
and a plan for prospective geo tests.

**Culture probe.** "Your analysis shows a smaller effect than the claim that was already shared. How do you deliver
the update?"

**Follow-ups**
- What pre-period window do you choose and why?
- What would convince you that the promotion, not the series, drove sign-ups?
