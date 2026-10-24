---
variant: ml-coding
roles: [mle, rs]
levels: [L4, L5, L6]
title: User-based collaborative filtering with cosine similarity
minutes: 45
---
# User-based CF on a sparse matrix, with cold-start fallback

Ratings are stored sparsely: `ratings = {user: {item: rating}}` (ratings are positive floats; unseen means no entry).

Implement `recommend(ratings, user, n)` returning a list of at most `n` item ids:

1. **Similarity.** For the target `user`, compute cosine similarity with every other user over their sparse rating
   vectors: `dot(u, v) / (|u| * |v|)` where the dot product runs over co-rated items and the norms over all of each
   user's ratings.
2. **Score.** For each item the target has **not** rated, `score(item) = sum over other users v who rated item of
   sim(user, v) * rating(v, item)`. Only users with `sim > 0` matter.
3. **Rank.** Return the top `n` items by score descending, ties broken by item id ascending (ids are comparable).
4. **Cold-start fallback.** If the user is unknown, has no ratings, or fewer than `n` items received a positive score,
   fill the remaining slots with the most popular items (number of raters desc, then item id asc) that the user has not
   rated and that are not already in the list.

Constraints: do not build a dense users x items matrix and do not compare the target against users who share no item
with them; think about an inverted index `item -> users`. Write your own tests, including a dense brute-force check.
