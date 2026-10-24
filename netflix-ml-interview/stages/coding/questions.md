# Question bank: coding

Problems live in `problems/<id>/` (statement, starter, hidden tests, reference, follow-ups) and count as `main` items. This file adds
generic production follow-ups and culture probes the interviewer may use after any problem. All items are original prompts built from reported topics.

### coding-followup-scale-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: practical
domain: any
kind: followup
signal_points:
  - estimates data volume before choosing a design
  - partitions by a natural key (member, title) and names the skew risk
  - states what is computed offline vs online
```
Your solution works for one member's page. Now it must run for every request across hundreds of millions of members. What is the
volume, where does it run (client, service, batch), and what changes in your data structures?

Follow-ups:
- What is the hot key in this workload and what happens to it?
- What do you cache and how do you invalidate it?

### coding-followup-concurrency-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: practical
domain: any
kind: followup
signal_points:
  - identifies shared mutable state
  - chooses among coarse lock, fine-grained lock and immutable snapshot with a reason
  - names the invariant that must hold under concurrent calls
```
Several threads now call your code concurrently while another thread updates the underlying data. What is shared, what
invariant must always hold, and how do you protect it?

Follow-ups:
- What is the cost of your choice on the read path?
- How would you test it and what flakiness would you expect?

### coding-followup-ml-scale-01
```yaml
roles: [rs, mle]
levels: [L4, L5, L6]
variant: ml-coding
domain: recsys
kind: followup
signal_points:
  - gives the complexity in terms of non-zeros, not dimensions
  - proposes sharding the computation with a stated join or reduce key
  - proposes an approximation (sampling, top-k neighbours, thresholding) and its cost to quality
```
The matrix grows to 100 million rows and 1 million columns. Which part of your approach stops working first, and how do
you restructure it across many machines?

Follow-ups:
- What do you keep sparse at each step?
- How would you check that the approximation did not hurt recommendation quality?

### coding-followup-sql-scale-01
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: sql-pandas
domain: any
kind: followup
signal_points:
  - reasons about partitioning and incremental aggregation
  - names late-arriving data and idempotent rewrites
  - can state the equivalent logic in pandas
```
This query now runs daily over trillions of rows. How would you make it incremental, and what happens when events arrive
late? Show me the same logic in pandas for a single day.

Follow-ups:
- Which part of the pandas version would not fit in memory?
- How do you make the daily job safe to re-run?

### coding-followup-lc-scale-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: lc-style
domain: any
kind: followup
signal_points:
  - gives the complexity bound and the memory bound
  - extends to a stream or to parallel chunks with a stated boundary rule
```
Your function receives its input as a stream that is too large for memory, or split across many workers. What do you keep, and
what do you carry across chunk boundaries?

Follow-ups:
- What is the worst-case memory?

### coding-culture-pushback-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: practical
domain: any
kind: culture
signal_points:
  - disagrees with the proposed shortcut and gives a technical reason
  - proposes a test or measurement to settle the disagreement
  - accepts the interviewer's point when it is right
```
After the candidate states an approach, say: "I think sorting the whole input on every call is simpler, and nobody will notice the
cost. Can we just do that?" Observe whether they push back with reasons, ask about data size, or give in.

Follow-ups:
- What would change your mind?

### coding-culture-bug-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: practical
domain: any
kind: culture
signal_points:
  - states the bug and its cause plainly, without blame or defensiveness
  - shares what they would add to the tests so it does not recur
```
When a test fails (theirs or the hidden suite), ask: "Walk me through what happened, and what you take from it." Observe how they
admit the mistake and what they learned.

Follow-ups:
- Which test would have caught it earlier?

### coding-culture-curiosity-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: ml-coding
domain: any
kind: culture
signal_points:
  - asks about edge cases or product behavior they were unsure of
  - names what they do not know and how they would find out
```
Near the end ask: "What part of this problem did you find least clear, and what would you want to learn before shipping it?"

Follow-ups:
- Who would you ask?
