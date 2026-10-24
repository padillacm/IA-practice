# Question bank: ml-fundamentals

Topics reported for this round: bias-variance, L1/L2, GBDT overfitting, co-watch embeddings, cold start, popularity
bias, ranking metrics, collaborative filtering, trees versus networks, post-deploy monitoring, and (GenAI orgs) KV
cache and attention (research.md 2 ML fundamentals; Exponent examples). These are original prompts built from those
topics, not recalled questions. Publications are discussion context; never ask for their figures.

Variants: `breadth` (mle, rs, ds) and `modeling-case` (ds, optional, no direct evidence).

## Variant breadth

### ml-fundamentals-biasvar-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5]
variant: breadth
domain: any
kind: main
signal_points:
  - decomposes expected error into bias squared, variance and irreducible noise
  - links model capacity, data size and regularization to each term
  - reads a train/validation gap and learning curve to diagnose which term dominates
  - proposes a remedy per diagnosis (more capacity or features vs more data, regularization, bagging)
```
Your model has 2% training error and 14% validation error. Walk me through the bias-variance decomposition and what
you would do next.

Follow-ups:
- Training and validation error are both 14%. What changed in your diagnosis and in your next step?
- Why does bagging reduce variance but barely change bias, while boosting does the opposite first?
- Does more data always help? Draw the learning curves where it does not.
- (L5) Does the classic U-shaped curve always hold for heavily over-parameterized networks? What do you believe, and why?

Level notes: L4 gives the decomposition and standard remedies; L5 reasons from learning curves and the noise floor.

### ml-fundamentals-regularization-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: breadth
domain: any
kind: main
signal_points:
  - states L1 induces sparsity and L2 shrinks weights, with the geometric or Bayesian reason (Laplace vs Gaussian prior)
  - explains why L1 is unstable under correlated features and L2 spreads weight
  - notes that features must be standardized before penalties and that the bias term is usually unpenalized
  - distinguishes weight regularization from L1 versus L2 normalization of vectors
```
Explain L1 and L2 regularization to a colleague who knows linear regression. When would you choose each?

Follow-ups:
- Why does L1 produce exact zeros and L2 does not? Give me the geometric picture or the prior.
- Two features are almost duplicates. What does each penalty do to their weights?
- Different question: what is L1 versus L2 normalization of an embedding vector, and when does the choice matter (for example cosine retrieval, or a softmax over dot products)?
- (L6) You inherit a model with ten thousand sparse features and a hand-tuned L1 strength. How do you make the choice defensible and cheap to maintain?

### ml-fundamentals-gbdt-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: breadth
domain: any
kind: main
signal_points:
  - lists tree-level controls (depth, min child weight or samples, leaves, gamma) and ensemble controls (learning rate, number of trees, subsampling, column subsampling, L1/L2 on leaf weights)
  - uses early stopping on a validation set that matches the deployment split and explains its leakage risk
  - explains the learning-rate versus number-of-trees trade-off
  - distinguishes overfitting to the validation set from overfitting to training data
```
Your gradient boosted trees reach near-zero training loss but validation loss starts climbing after 300 rounds. What do you do, and in what order?

Follow-ups:
- How does early stopping work, and what is wrong with early stopping on the same set you report the final metric on?
- You halve the learning rate. What happens to the optimal number of trees and to variance?
- Your rows are repeated interactions from the same users. How do you split, and what does a random split hide?
- (L6) The model is retrained daily. How do you set early stopping and tree controls so retraining does not need a human?

### ml-fundamentals-cowatch-01
```yaml
roles: [mle, rs]
levels: [L4, L5, L6]
variant: breadth
domain: recsys
kind: main
signal_points:
  - defines the co-watch objective (skip-gram or contrastive over sessions or user histories) and what a positive is
  - names failure modes: popularity dominance, sessions dominated by autoplay, cold items without vectors
  - evaluates embeddings intrinsically (nearest neighbors, clustering) and extrinsically (downstream metric)
  - chooses negative sampling and subsampling with a reason
```
You want title embeddings from co-watch data. How do you build them, and how do you know they are good?

Follow-ups:
- Which pairs count as co-watched: same session, same week, same user ever? What bias does each choice add?
- Popular titles appear next to everything. What do the vectors look like and how do you correct for it?
- A title launched yesterday. How does it get a vector, and how do you avoid the cold vector hurting retrieval?
- (L6) Several teams train their own title embeddings. What would make sharing one embedding service worthwhile, and what would break it?

### ml-fundamentals-coldstart-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: breadth
domain: recsys
kind: main
signal_points:
  - separates user cold start from item cold start and names signals available for each
  - proposes content-based features or metadata embeddings, onboarding signals and exploration
  - handles the evaluation problem: offline logs have no data for cold entities
  - states a plan for graduating from the cold-start policy to the learned model
```
How do you recommend a title on launch day, when it has no interaction data? And how about a brand-new member?

Follow-ups:
- Which content features would you use for the title, and how do you test they carry signal before launch?
- How much exploration is acceptable on a surface that members see first, and who decides?
- How do you evaluate cold-start quality offline when the logs have no cold items?
- (L6) The cold-start policy and the main ranker disagree on a title. How do you structure the system so that disagreements are measurable and the policy retires cleanly?

### ml-fundamentals-popbias-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: breadth
domain: recsys
kind: main
signal_points:
  - explains the feedback loop: exposure drives interactions, which drive training labels, which drive exposure
  - distinguishes popularity as a true preference signal from popularity as exposure bias
  - proposes mitigations (inverse propensity weighting, debiased sampling, exploration, calibrated or diversified re-ranking)
  - evaluates with metrics that expose the problem (coverage, long-tail recall, long-term retention)
```
Our model recommends mostly popular titles and accuracy metrics look fine. Is that a problem, and what would you do?

Follow-ups:
- How can you tell whether popularity is preference or exposure bias from logged data alone?
- Inverse propensity weighting has high variance. What do you do about it?
- What does popularity-heavy ranking cost the business over months that a one-week A/B test misses?
- (L6) Propose how a platform team would let several rankers share a debiasing method without sharing a model.

### ml-fundamentals-rankmetrics-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5]
variant: breadth
domain: any
kind: main
signal_points:
  - computes P@K, R@K and a small-example NDCG correctly with the log discount
  - explains MAP as the mean over queries of average precision and where it differs from NDCG (binary vs graded relevance)
  - states which metric to use when (P@K for fixed-size slate with binary relevance, NDCG for graded relevance and position sensitivity, R@K for candidate generation)
  - names a failure mode for each metric
```
A user has 3 relevant titles. Your ranker returns ten titles and the relevant ones sit at positions 1, 4 and 8. Compute P@5, R@5, average precision and NDCG@10 with binary relevance, and tell me when you would prefer each.

Follow-ups:
- Why is NDCG discounted logarithmically and not linearly? What is the assumption about user behavior?
- When is P@K the right metric even though it ignores order inside the top K?
- Candidate generation versus the final ranker: which metric for each and why?
- A user has only one relevant title in the catalog. What happens to the usefulness of each metric?

### ml-fundamentals-rankbeyond-01
```yaml
roles: [mle, rs, ds]
levels: [L5, L6]
variant: breadth
domain: recsys
kind: main
signal_points:
  - defines coverage, diversity (intra-list distance or category entropy) and serendipity (relevant and unexpected)
  - explains why accuracy metrics miss these and how they trade off with accuracy
  - connects metrics to member outcomes (long-term satisfaction, retention) and to measurement limits offline
  - proposes how to validate online (interleaving as a first stage, then an A/B on long-term outcomes)
```
Offline NDCG improved by 3% but a colleague argues the new ranker is worse for members. Which other metrics would you look at, how do you define them, and how would you decide?

Follow-ups:
- Define serendipity operationally. What is "unexpected" relative to?
- Diversity went down by a small amount and NDCG went up. What further evidence moves your decision?
- Why can interleaving tell you about relative quality quickly but not about retention?
- (L6) How do you make "diversity" a metric several teams can agree on without it becoming a number that gets gamed?

### ml-fundamentals-cf-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5]
variant: breadth
domain: recsys
kind: main
signal_points:
  - contrasts memory-based (user-user, item-item) with model-based (matrix factorization, neural) collaborative filtering
  - explains implicit versus explicit feedback and the confidence-weighting idea
  - names sparsity, scalability, cold start and popularity bias as limits
  - links factorization to learned embeddings and dot-product scoring
```
Explain collaborative filtering. When does it work well and when does it fail?

Follow-ups:
- Why is item-item often preferred over user-user at scale?
- Matrix factorization on implicit data: what is a negative, and what do you do about missing entries?
- What does a two-tower neural model give you over matrix factorization, and what does it cost?
- How would you add side information (genre, language, device) to CF?

### ml-fundamentals-treesnn-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: breadth
domain: any
kind: main
signal_points:
  - states where trees win (tabular data, heterogeneous features, small data, little feature scaling) and where networks win (raw perceptual or sequence data, representation sharing, multimodal)
  - discusses serving cost, latency, update cadence and debuggability
  - mentions that hybrids exist (tree leaves or embeddings as features, networks over tabular data)
  - says how to decide empirically (baseline first, equal tuning budget, same split)
```
For a tabular prediction problem with 200 features and 5 million rows, would you reach for gradient boosted trees or a neural network? Why?

Follow-ups:
- What changes if one of the features is a sequence of the last 500 titles watched?
- How do you compare the two fairly, and what mistakes make the comparison misleading?
- Feature importance is requested by a partner team. What can you offer for each model family, and how much would you trust it?
- (L6) The team maintains a stack of tree models fed by thousands of hand-made features. What would you need to see to propose moving part of it to a learned representation?

### ml-fundamentals-monitoring-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: breadth
domain: ml-platform
kind: main
signal_points:
  - separates system health (latency, errors, freshness), data health (schema, missing rates, distribution shift) and model health (score distribution, calibration, business metrics)
  - names leading versus lagging indicators and acknowledges delayed labels
  - sets alert thresholds with a rationale and an owner, not just "monitor everything"
  - defines rollback criteria and a holdout or shadow comparison
```
You just deployed a new ranking model. Which metrics do you monitor in the first hour, first week and first quarter, and what makes you roll back?

Follow-ups:
- Labels arrive days later. What do you watch in the meantime?
- Feature X starts arriving as null for 5% of requests. What happens to the model and how do you detect it?
- How do you tell a real drop from a seasonal pattern or a new-release effect?
- (L6) Ten models share one feature store. How do you design monitoring so that one team's change cannot silently degrade another's model?

### ml-fundamentals-bayes-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5]
variant: breadth
domain: any
kind: main
signal_points:
  - applies Bayes rule correctly to a base-rate problem
  - interprets prior, likelihood and posterior and explains why base rates dominate for rare events
  - connects to a model use (naive Bayes, Bayesian smoothing of rates, MAP as regularization)
  - checks the answer for plausibility
```
A fraud model flags 95% of fraudulent accounts and wrongly flags 2% of legitimate ones. One account in 1,000 is fraudulent. An account is flagged. What is the probability it is fraudulent, and what do you conclude about using this model?

Follow-ups:
- How would you change the threshold or the operating point for a human-review queue versus an automatic block?
- A title has 3 plays and 2 likes. How would you estimate its true like rate for ranking, and why not use 2/3?
- Show the link between MAP estimation with a Gaussian prior and L2 regularization.

### ml-fundamentals-forward-01
```yaml
roles: [mle, rs]
levels: [L4, L5]
variant: breadth
domain: any
kind: main
signal_points:
  - writes the forward pass of a small MLP with shapes (batch, features, hidden) and a nonlinearity
  - explains softmax plus cross-entropy and why logits are used for stability
  - states what backprop needs from the forward pass (cached activations) and the memory consequence
  - catches a shape or broadcasting mistake when prompted
```
Write out the forward pass of a two-layer MLP for a batch of 32 examples with 100 features, 64 hidden units and 5 classes. Give the shapes at each step and the loss.

Follow-ups:
- Why not apply softmax and take the log separately? What is log-sum-exp doing?
- What do you have to keep from the forward pass to compute gradients, and how does that change training memory versus inference?
- What goes wrong if you drop the nonlinearity?
- What changes if the batch has padded sequences of different lengths?

### ml-fundamentals-knn-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: breadth
domain: any
kind: main
signal_points:
  - describes KNN, the role of K and the distance metric, and the bias-variance effect of K
  - raises feature scaling and the curse of dimensionality
  - explains approximate nearest neighbor search as the scalable variant and its recall-latency trade-off
  - connects to embedding retrieval in recommendation
```
Explain k-nearest neighbors. What does K control, and why does it get harder in high dimensions?

Follow-ups:
- You have 100 million item embeddings and 20 ms. What do you build, and what do you give up?
- Cosine versus Euclidean on unnormalized embeddings: when do they disagree?
- (L6) Index rebuilds lag behind new titles. How do you keep freshness without rebuilding on every change?

### ml-fundamentals-attention-01
```yaml
roles: [mle, rs]
levels: [L5, L6]
variant: breadth
domain: nlp-llm
kind: main
signal_points:
  - computes Q, K and V as learned linear projections of the same input (self-attention) and shows the shapes
  - writes softmax(QK^T / sqrt(d_k)) V and explains the scaling factor
  - explains causal masking, multi-head attention and the quadratic cost in sequence length
  - distinguishes self- from cross-attention
```
Explain how attention is computed in a transformer layer. Where do the queries, keys and values come from?

Follow-ups:
- Why divide by the square root of the key dimension?
- Where does the quadratic cost come from, and what are two ways to reduce it?
- What does masking do in a decoder, and how does it differ at training time versus generation time?
- (L6) Your ranking model scores a history of 2,000 events. What would you change in attention or in the input to stay inside a latency budget?

### ml-fundamentals-kvcache-01
```yaml
roles: [mle, rs]
levels: [L5, L6]
variant: breadth
domain: nlp-llm
kind: main
signal_points:
  - explains that keys and values of past tokens are reused during autoregressive decoding, so each step computes only the new token's attention
  - estimates KV cache memory (layers x heads x head_dim x sequence x 2 x bytes) and its growth with batch and context
  - distinguishes prefill (parallel over the prompt) from decode (sequential)
  - lists mitigations (grouped or multi-query attention, quantization, paging, prefix sharing)
```
What is the KV cache, why does it speed up generation, and what does it cost?

Follow-ups:
- Estimate the cache size for a model with 32 layers, 32 heads of dimension 128, 4,000 tokens, 16-bit values, batch of 1.
- Which workloads are bound by memory bandwidth and which by compute, prefill or decode?
- A scoring service only needs one forward pass over a long prompt and never generates. How does that change what you need to cache or serve?
- (L6) Many requests share a long system prefix. How would you design serving to exploit that, and what breaks isolation or freshness?

### ml-fundamentals-calibration-01
```yaml
roles: [mle, rs, ds]
levels: [L5, L6]
variant: breadth
domain: ads
kind: main
signal_points:
  - defines calibration (predicted probability matches observed frequency) and distinguishes it from discrimination (AUC)
  - names measurement tools (reliability diagram, expected calibration error, log loss) and their pitfalls with binning
  - proposes fixes (Platt scaling, isotonic regression, temperature scaling) and where to fit them
  - explains when calibration matters (probabilities used in expected-value decisions, auctions, thresholds) versus pure ranking
```
Your click model has strong AUC. Why might a partner team still say it is unusable, and what would you check?

Follow-ups:
- Two models have the same AUC. One is calibrated, the other is not. When does the difference change a decision?
- You trained with negative downsampling at 1 in 10. What happens to the predicted probabilities and how do you fix them?
- Calibration drifts after a product change. How do you detect and correct it without retraining everything?
- (L6) Several teams consume the same score at different thresholds. How do you define a calibration contract?

## Variant modeling-case

The modeling-case variant is optional and has no direct evidence of use at Netflix (research.md 4). Cases are original and framed as generic subscription or text problems.

### ml-fundamentals-case-churn-01
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: modeling-case
domain: any
kind: main
signal_points:
  - frames churn as a precise prediction target (who, horizon, definition of churn, voluntary vs involuntary) tied to a decision
  - proposes features by family and avoids label leakage and time travel in training data
  - uses a time-based split and a metric matched to the action (precision at a budget, uplift rather than risk)
  - separates predicting who will leave from deciding who to treat, and says how to test the intervention causally
```
A subscription service wants to reduce churn. Frame it as a modeling problem and take me through the model, the evaluation and what the business does with it.

Follow-ups:
- How do you define churn for a user who pauses, or who is on a shared account?
- Your top feature is "visited the cancellation page". What is wrong, and what do you do?
- The retention team can contact 2% of members per week. How does that change your metric and your model?
- The model finds high-risk members, but the intervention barely helps them. What would you build instead?
- (L6) Two teams need churn scores for different horizons and actions. How do you decide between one shared model and two?

### ml-fundamentals-case-review-01
```yaml
roles: [ds]
levels: [L4, L5]
variant: modeling-case
domain: nlp-llm
kind: main
signal_points:
  - frames review-score prediction as ordinal regression, regression or classification and justifies the choice
  - proposes a baseline (bag of words or TF-IDF with a linear model) before a pretrained text encoder
  - handles label noise, class imbalance and reviewer effects, and splits by user or time to avoid leakage
  - selects metrics (MAE, quadratic weighted kappa, per-class recall) and reads errors qualitatively
```
Given a few million written reviews with one to five star ratings, predict the rating from the text. How do you approach it?

Follow-ups:
- Most reviews are five stars. What does that do to accuracy, and what do you report instead?
- Should the model predict a number, a class or a distribution? What changes downstream?
- A pretrained encoder is only 1% better than your linear baseline. What do you recommend and why?
- Some reviews are sarcastic or mention a different product. How do you find and treat these?

### ml-fundamentals-case-engagement-01
```yaml
roles: [ds]
levels: [L5, L6]
variant: modeling-case
domain: any
kind: main
signal_points:
  - turns a vague goal (predict long-term member value) into a target with horizon, unit and decision it supports
  - identifies proxy and delayed-label problems and proposes surrogate outcomes with a validation plan
  - addresses confounding between exposure and outcome and avoids reading a predictive model as causal
  - plans monitoring, retraining cadence and a decision rule for when the model is wrong
```
Leadership asks for "a model of how valuable a new member will be". How do you turn that into something you can build and trust?

Follow-ups:
- The true outcome takes a year to observe. What do you train on in the meantime, and how do you validate the proxy?
- Members who watch more also retain more. Can you use this model to decide whom to nudge to watch more?
- Different countries have different baseline behavior. One model, many models, or a hierarchical approach?
- (L6) How would you make this model a shared asset rather than a one-team artifact, and what governance would it need?

### ml-fundamentals-case-forecast-01
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: modeling-case
domain: any
kind: main
signal_points:
  - frames demand or viewership forecasting with horizon, granularity and decision (capacity, content investment)
  - handles seasonality, launches, trend breaks and cold items in features or hierarchy
  - backtests with rolling-origin splits and reports error by segment, not one global number
  - reports uncertainty intervals and says how a decision-maker should use them
```
You are asked to forecast first-week viewing for upcoming titles. How would you build and evaluate this?

Follow-ups:
- There is no history for the new title. What is your prior, and how do you update it as early data arrives?
- Your error is 15% on average, but 60% on big launches. Which one matters, and what do you do?
- A competitor event shifts viewing. How do you keep the model from learning that as a pattern?
- (L6) Finance, content and infrastructure all consume the forecast. How do you set one accuracy definition they will accept?
