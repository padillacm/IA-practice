# AI-assisted coding - question bank

Each main question assigns one repo. The orchestrator copies only `workspace/` and the task statement from the repo into the session space; the interviewer works from the task statement and never from `flaws.yaml` or `notes.md` contents shown to the candidate.

### ai-assisted-feature-cache-01

```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
repo: feature-cache-service
signal_points:
  - "Plan before prompting: partition ids into hits and misses, one backend call for all misses, order and duplicates handled"
  - "Gives the AI the contract (one backend call, duplicates, unknown ids omitted, key includes the feature set) instead of a bare request"
  - "Reads the AI diff before `::apply` and writes at least one test the diff did not come with"
  - "Probes cache semantics: key composition, exact TTL boundary, stale reads"
  - "Pushes back with a reason when the AI's change weakens keying or expiry"
```

Feature lookup service with a TTL/LRU cache. Work through the task in `tasks.md` for the repo `feature-cache-service`: add a batch lookup (`get_many`) and per-feature-set TTLs to an online feature service that sits in front of a slow backend on a ranking request path.

Open by giving the task statement and asking for questions. Let the candidate plan and explore the code before using the AI pair. Scale scope by level: L4 completes Part 1 with tests, L5 completes both parts and explains verification, L6 also leads the extension discussion.

Follow-ups on verification strategy:
- How would you verify that two different feature sets can never see each other's cached values?
- What exactly happens at the instant an entry reaches its TTL, and how would a test pin that down?
- Extension: how would you stop many concurrent requests from stampeding the backend on the same missing key?
- Extension: should unknown ids be cached (negative caching)? What are the risks on this request path?

### ai-assisted-feature-cache-fu-verify

```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: followup
repo: feature-cache-service
```

Ask after the candidate says they are done: "How do you know this is correct, and what would you not ship yet?" If the answer is only "the tests pass", ask which behavior the existing tests do not pin down. If the candidate applied an AI diff, ask what they checked in it before `::apply`. Never indicate whether a specific diff was wrong.

### ai-assisted-offline-eval-01

```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
repo: offline-eval-job
signal_points:
  - "Threads the window through existing functions instead of duplicating the evaluation loop"
  - "States the time interval precisely in the prompt, and keeps deduplication and the time split intact"
  - "Asks whether anything at or after the cutoff can reach the baseline, and tests it with a future-only item"
  - "Checks that default behavior (no window) is unchanged on the existing fixture"
  - "Explains how they would know a reported lift is not inflated"
```

Offline evaluation job over logged impressions. Work through the task in `tasks.md` for the repo `offline-eval-job`: add a trailing-window popularity baseline and a per-day report to an offline job that compares a recommender's logged ranking with a popularity baseline.

Open by giving the task statement and asking for questions. Let the candidate plan and explore the code before using the AI pair. Scale scope by level: L4 completes Part 1 with tests, L5 completes both parts and explains verification, L6 also leads the extension discussion.

Follow-ups on verification strategy:
- If offline lift jumps 40% after this change, what do you check first?
- Why does deduplication use the impression id and not the user and item pair?
- Extension: the logged slate was produced by a different policy than the one you want to evaluate. What biases remain in this metric?
- Extension: how would you put confidence intervals on the per-day numbers?

### ai-assisted-offline-eval-fu-verify

```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: followup
repo: offline-eval-job
```

Ask after the candidate says they are done: "How do you know this is correct, and what would you not ship yet?" If the answer is only "the tests pass", ask which behavior the existing tests do not pin down. If the candidate applied an AI diff, ask what they checked in it before `::apply`. Never indicate whether a specific diff was wrong.

### ai-assisted-title-dedup-01

```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
repo: title-deduplicator
signal_points:
  - "Passes the record kind to the normalization step so movies are untouched"
  - "Specifies the exact marker forms and the cases that must not change (movies, regional qualifiers)"
  - "Runs the existing tests, adds a few targeted tests, and applies a correct AI diff without needless rework"
  - "Names what was deliberately left out (e.g. Part N, non-English markers)"
  - "If they claim a defect in the AI output, can produce a failing input or retracts the claim"
```

Catalog title deduplicator. Work through the task in `tasks.md` for the repo `title-deduplicator`: make title normalization ignore trailing season or limited-series markers for series records, so the same series is grouped into one record.

Open by giving the task statement and asking for questions. Let the candidate plan and explore the code before using the AI pair. Scale scope by level: L4 completes Part 1 with tests, L5 completes both parts and explains verification, L6 also leads the extension discussion.

Follow-ups on verification strategy:
- What inputs did you decide not to handle, and why is that acceptable?
- How would you measure the precision and recall of the deduplicator on real catalog data?
- Extension: how would you add fuzzy matching without merging unrelated titles, and who reviews low-confidence merges?
- Extension: should merging be transitive? What can go wrong?

### ai-assisted-title-dedup-fu-verify

```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: followup
repo: title-deduplicator
```

Ask after the candidate says they are done: "How do you know this is correct, and what would you not ship yet?" If the answer is only "the tests pass", ask which behavior the existing tests do not pin down. If the candidate applied an AI diff, ask what they checked in it before `::apply`. Never indicate whether a specific diff was wrong.

### ai-assisted-general-fu-pushback

```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: followup
```

Ask when the candidate has accepted or rejected an AI proposal without explaining why: "What made you comfortable with that?" or "What would you tell a teammate who wanted to merge this as is?". Treat the answer as evidence for verification and candor. Do not reveal whether the proposal was flawed.
