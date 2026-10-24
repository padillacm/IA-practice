---
variant: practical
roles: [mle, rs, ds]
levels: [L4, L5, L6]
title: Weighted random key
minutes: 35
---
# Weighted random key

Serving needs to sample a title with probability proportional to its weight (for example exploration traffic over
candidate titles). To keep the code testable, randomness is injected: the caller passes `u`, a float in `[0, 1)`.

Implement `WeightedKeySampler`:

- `__init__(weights)`: `weights` is a dict `key -> non-negative number`. Raise `ValueError` for a negative weight or when
  the total weight is 0.
- `pick(u)`: return the key selected by `u`. Let `target = u * total`; return the first key (in the dict's insertion
  order) whose cumulative weight is strictly greater than `target`. Keys with weight 0 are never returned.
- `update(key, weight)`: change the weight of an existing key (`KeyError` if unknown, `ValueError` if negative or if it
  would make the total 0). Updates are frequent; `pick` and `update` should both beat O(n) per call.

Start with the simple version and then make updates fast. Write your own tests (how do you test randomness?).
