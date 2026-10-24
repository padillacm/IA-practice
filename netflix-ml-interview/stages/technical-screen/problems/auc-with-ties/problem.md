---
variant: ml-framing-coding
roles: [rs]
levels: [L4, L5, L6]
title: ROC AUC with tied scores
minutes: 20
---
# ROC AUC with tied scores

Implement `roc_auc(labels, scores)`: the area under the ROC curve for binary `labels` (0/1) and real-valued `scores`.
Interpret AUC as the probability that a random positive is scored above a random negative, with **ties counting 1/2**.

- Raise `ValueError` if the inputs differ in length or there is no positive or no negative example.
- Target O(n log n): sort once, use average ranks for tied scores (the rank-sum / Mann-Whitney U formulation).

Then `auc_by_group(groups, labels, scores)` returns `{group: auc}` for groups that have both classes, and
`macro_auc(...)`, the unweighted mean over those groups (0.0 if none). Explain why per-member or per-row AUC can
differ from the global AUC in a recommender evaluation.

Write your own tests, including all-tied scores.
