---
variant: practical
roles: [mle, rs, ds]
levels: [L4, L5, L6]
title: Billboard rotation with updatable scores
minutes: 40
---
# Billboard rotation with updatable scores

The homepage billboard rotates through movies. Implement `Billboard` with these operations:

- `add(movie, score)`: add a movie (or replace its score if it exists).
- `update(movie, score)`: change the score of an existing movie (raise `KeyError` if unknown).
- `remove(movie)`: remove a movie (raise `KeyError` if unknown).
- `get()`: return the next movie to show, or `None` if the billboard is empty.

Rotation rules:

- Movies are served in descending score order; ties are broken by movie id ascending.
- Within a **cycle** every movie is returned **exactly once**. When all movies of the cycle have been returned, a new
  cycle starts containing all current movies.
- A score update takes effect for the **current cycle** if the movie has not been returned yet in it; otherwise it
  applies from the next cycle.
- A movie added mid-cycle is eligible in the current cycle. A movie removed mid-cycle is not returned again.

Target: `add`, `update`, `remove` and `get` in O(log n) (amortized is fine). Write your own tests.
