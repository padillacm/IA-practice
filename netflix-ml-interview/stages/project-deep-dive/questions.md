# Questions: project-deep-dive (reverse system design)

Topics follow the reported format (own prior work, successes, failures, what to do better, Freedom and Responsibility).
Each question applies to whichever system the candidate chose; the interviewer fills in the assigned part from the brief.

### project-deep-dive-scale-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points: [names order-of-magnitude numbers, numbers are internally consistent, states what dominated cost or latency]
```
Draw the largest-scale system you owned, end to end. For the part I assigned, give me the numbers: users, requests per second at peak, data volume and the dominant cost.

Follow-ups:
- Which of those numbers grew fastest, and what broke first?
- Which number are you least sure about?

### project-deep-dive-decision-02
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points: [describes a rejected alternative, gives the constraint that forced the choice, quantifies the trade-off]
```
Pick the most consequential design decision in the part we are discussing. What were the alternatives, and why did you reject them?

Follow-ups:
- What constraint would have flipped your choice?
- Who disagreed, and what did you do about it?

### project-deep-dive-ownership-03
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points: [separates own decisions from team decisions, owns the outcome including a miss, did not wait for sign-off where appropriate]
```
Which decision in this project did you make yourself without waiting for approval? What happened, and who was accountable for the result?

Follow-ups:
- What would have happened if you had been wrong?
- What did you hand off, and why?

### project-deep-dive-scaling-04
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points: [describes before and after, identifies the bottleneck with evidence, explains the change that fixed it]
```
Tell me about a time this system hit a scaling limit. How did you find the bottleneck, and what did you change?

Follow-ups:
- What measurement convinced you it was the real bottleneck?
- What did the fix cost in complexity?

### project-deep-dive-ops-05
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points: [names monitoring signals, describes a concrete incident and response, states rollback or mitigation plan]
```
Walk me through the worst incident this system had. How did you detect it, what did you do in the first hour, and what changed afterwards?

Follow-ups:
- How would you have caught it earlier?
- What is the on-call burden today?

### project-deep-dive-evaluation-06
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: recsys
kind: main
signal_points: [separates offline from online validation, names a guardrail, describes how impact was measured]
```
How did you know the system was working in production? Which offline metric did you trust, which online metric, and where did they disagree?

Follow-ups:
- How did you attribute the gain to your work?
- What did you stop measuring, and why?

### project-deep-dive-miss-07
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points: [names a real miss, states root cause without blame, shows a changed practice]
```
What is the biggest miss in this project? With the same constraints, what would you do differently?

Follow-ups:
- What did you do afterwards that you still do now?
- What would your teammates say you underestimated?

### project-deep-dive-data-08
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points: [describes data quality or freshness risk, explains feature or label choice, names a leakage or skew risk]
```
For the data and feature side of this system, what is the hardest correctness problem you faced (freshness, skew, leakage, missing data), and how did you handle it?

Follow-ups:
- How did you detect the issue?
- How did you prevent it from coming back?

### project-deep-dive-migration-09
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: followup
signal_points: [describes a migration or deprecation plan, handles risk, communicates to dependent teams]
```
How would you migrate this system to a new architecture without downtime? What do you do about the teams that depend on it?

### project-deep-dive-candor-10
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: culture
signal_points: [gives an example of receiving direct feedback on this project, acts on it]
```
What was the hardest feedback you got on this project, from whom, and what did you do with it?
