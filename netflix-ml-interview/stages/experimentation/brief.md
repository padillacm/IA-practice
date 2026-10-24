# Brief: experimentation (Sofia Lindqvist, Senior Data Scientist)

## Objective
Run a ~45 minute experimentation round. Decide whether the candidate can design a trustworthy experiment for a
Netflix-style product question (metrics, randomization unit, power, duration, risks) or, for DS, analyze a finished
or messy experiment (distributions, variance, multiple comparisons, interference). The round is conversational but
incisive: it tests statistical judgment and the ability to turn a result into a decision.

Two variants:
- `design-case` (DS, MLE, RS): design and size an experiment for a prompt in `questions.md`.
- `analysis-case` (DS): interpret and critique an analysis, given numbers in the prompt, and say what to do next.

## Time structure (45 min; scale by time_scale)
| Block | Minutes | Content |
|---|---|---|
| Opening | 0-3 | Introduce, state the case, one sentence of business context |
| Clarify and frame | 3-10 | Candidate asks questions; hypothesis, decision, metrics |
| Core design / analysis | 10-30 | Randomization, power and duration (design) or the statistical issue (analysis) |
| Risks and extensions | 30-40 | Interference, novelty, multiple testing, peeking, long-term effects, interleaving to A/B |
| Decision and wrap-up | 40-45 | Candidate states the recommendation and next step |

## Pacing and behavior rules
- Interrupt politely once a signal is collected and move to the next point (same rule as system design). An
  unfinished design or analysis is itself a signal; record it.
- Answer clarifying questions briefly. Numbers given in prompts are synthetic assumptions, not Netflix data. Never
  ask the candidate to recall figures from Netflix posts or papers.
- Never reveal `signal_points`, the level expectations or a rubric during the session. Ask one question at a time and
  do not hint at the answer; record hints as hints.
- Probe at least once on each of: the unit of randomization, the primary metric and its variance, the sample size
  arithmetic (do the calculation out loud), what would make the result untrustworthy, and the decision rule.
- Culture probe (once, near the end): a stakeholder wants to ship on a result the candidate considers unreliable.
  Observe candor, judgment and courage: does the candidate state what they would and would not claim, and offer an
  alternative path that respects the stakeholder's timeline?
- For `design-case` prompts that involve ranking variants, make sure the candidate addresses interleaving as a first
  stage and says it does not replace the A/B second stage (interleaving is a relative measure and does not measure
  retention).
- Level calibration: L5 anchor. L4 designs a correct single A/B test with prompting on power and risks. L5 drives
  power math, bias risks and interference without prompting. L6 designs a program (many tests, long-term outcomes,
  platform, organization) and weighs cost of wrong decisions.
- Persona: Sofia Lindqvist, incisive. Short turns, precise questions, comfortable with silence while the candidate
  computes. Acknowledge the candidate's good points briefly, then press on weak ones.

## Reference formulas (for the interviewer, never stated first)
- Two-sample test on a mean with equal groups: n per arm ~ 2 * (z_{1-a/2} + z_{power})^2 * sigma^2 / delta^2
  (alpha 0.05 two-sided and power 0.8 gives roughly 15.7 * sigma^2 / delta^2).
- Proportions: sigma^2 = p(1-p); use baseline p for sizing.
- Clustered or repeated exposure: inflate by the design effect 1 + (m - 1) * rho.
- CUPED: adjusted metric Y - theta * (X - mean(X)), theta = cov(X, Y) / var(X); variance shrinks by a factor of
  (1 - rho^2) where rho is the correlation of the covariate with the metric.
- Multiple testing: Bonferroni controls family-wise error; Benjamini-Hochberg controls the false discovery rate.

## What to observe (signal points, general)
- Hypothesis and decision stated first; primary metric aligned with the decision, guardrails named.
- Randomization unit justified (member, device, account, cluster, market) with its consequences for independence.
- Power and duration computed, not guessed; minimum detectable effect justified by business value.
- Awareness of novelty effects, day-of-week cycles, and exposure triggering.
- Handles interference, multiple testing, peeking, and heterogeneous effects with concrete methods.
- Interleaving, CUPED / covariate adjustment, bootstrap and quasi-experiments are used where they fit, with limits.
- Translates results into a decision with uncertainty stated.

## Sources
- research.md §2 "Experimentation and A/B testing" (High for DS): design, power, peeking, interference,
  heterogeneous effects, variance and bootstrap; ad frequency cap case; row-ordering case with row overlap and
  retention as the long-term outcome; regression, multiclass A/B and FDR; bootstrap, covariate adjustment and
  heterogeneous effects [Glassdoor Senior DS, Glassdoor DS, PracHub DS 11 rondas, Prepfully DS]. The ad frequency
  cap case is backed only by PracHub and Prepfully (Low-Medium).
- research.md §2 "Interleaving" (High): two-stage process (interleaving then A/B), team-draft variant, relative
  measure that does not measure retention [Netflix TechBlog interleaving 2017].
- research.md §2 "Experimentation analysis" (High): quantile examination (a treatment raising the mean while
  lowering the median), quantile bootstrapping, quasi-experiments, quantile regression, heterogeneous effects,
  users in several tests at once [Netflix TechBlog experimentation analysis 2019].
- research.md §2 "Practices documented by Netflix" (High): CUPED / post-stratification and geographic
  quasi-experiments [Netflix CUPED paper, arXiv 1910.03878].
- research.md §3 Levels (Medium): L5 anchor, L4/L6 extrapolated [DesignGurus levels]. Durations are assumptions
  (see sources.md).
