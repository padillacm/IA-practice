# Question bank: hm-onsite

Domain-anchored and prior-work questions for the demanding HM round. Original prompts built from topics and from
Netflix-published practices; nothing here asks the candidate to recall figures from Netflix papers or posts.

### hm-onsite-domain-recsys-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: recsys
kind: main
signal_points:
  - defines the objective beyond clicks (long-term satisfaction)
  - names offline versus online gap
  - cold start and popularity bias handled
  - evaluation plan
```
Our members open the app with no query. You own the ranking of titles on the homepage. How do you decide what the model is optimizing, and how would you know a change made members better off a quarter later?

Follow-ups:
- What goes wrong if you optimize for plays only?
- How do you handle a title that launched yesterday?
- Offline metric improves, A/B is flat. What do you do?

### hm-onsite-domain-recsys-02
```yaml
roles: [mle, rs]
levels: [L5, L6]
variant: default
domain: recsys
kind: main
signal_points:
  - reasons about LLM-native versus feature-engineered rankers
  - names failure modes (popularity bias, out-of-catalog output, business constraints)
  - serving cost and latency
```
A proposal on your desk replaces a stack built on thousands of hand-made features with a ranker built on a language model that reads a verbalized member history. What do you want to know before you approve a quarter of work on it?

Follow-ups:
- What are the risks you would test first, cheaply?
- How would you decide the context budget for history?
- Who else needs to agree?

### hm-onsite-domain-exp-01
```yaml
roles: [ds, rs, mle]
levels: [L4, L5, L6]
variant: default
domain: experimentation
kind: main
signal_points:
  - chooses a sensitive primary metric and guardrails
  - handles interference/overlap between concurrent tests
  - long-term versus short-term outcomes
```
Two teams want to test changes that both affect the homepage at the same time, and leadership wants a decision in three weeks. How do you structure the experimentation, and what do you refuse to promise?

Follow-ups:
- How would a cheaper first-stage method change your plan?
- How would you decide the test is long enough?

### hm-onsite-domain-causal-01
```yaml
roles: [ds, rs]
levels: [L5, L6]
variant: default
domain: causal-inference
kind: main
signal_points:
  - identifies when randomization is not possible
  - names an identification strategy and its assumptions
  - states threats to validity
```
We launched a feature in one region for operational reasons, and the business now wants to know its effect on retention. You were not part of the launch. What do you do?

Follow-ups:
- What assumption would you most worry about and how would you test it?
- What do you tell the stakeholder who wants one number?

### hm-onsite-domain-bandit-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: rl-bandits
kind: main
signal_points:
  - explore/exploit trade-off in a live product
  - delayed or proxy reward
  - off-policy evaluation or safe exploration
```
A surface needs to pick one of several candidate items per member and learn from feedback that arrives days later. How do you design the learning loop and keep exploration from hurting members?

Follow-ups:
- How do you evaluate a new policy before it serves live traffic?
- What would convince you the reward proxy is wrong?

### hm-onsite-domain-cv-01
```yaml
roles: [mle, rs]
levels: [L4, L5, L6]
variant: default
domain: cv
kind: main
signal_points:
  - frames a visual personalization or quality problem as an ML task
  - labeling cost and evaluation
  - trade-off between model quality and compute
```
We want to choose or generate a visual (an image for a title) per member. How do you frame the problem, evaluate candidates without labeling everything, and decide when a visual is good enough to show?

Follow-ups:
- What are the risks of showing a misleading image?
- How would you use members' behavior as a signal without feedback loops?

### hm-onsite-domain-nlp-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: nlp-llm
kind: main
signal_points:
  - evaluation of generated or ranked text
  - hallucination and grounding to the catalog
  - cost and latency of serving
```
A search feature will use a language model to interpret conversational queries. How do you decide it is better than the existing system and safe to ship?

Follow-ups:
- How do you keep it from returning titles that do not exist?
- What does your first online test look like?

### hm-onsite-domain-ads-01
```yaml
roles: [ds, mle, rs]
levels: [L4, L5, L6]
variant: default
domain: ads
kind: main
signal_points:
  - incrementality versus attribution
  - frequency and member experience constraints
  - experiment design for a two-sided system
```
We introduce more ads on a plan. How do you measure whether the change creates value without damaging member experience, and what is the design of the test?

Follow-ups:
- How would you set a frequency cap and justify it?
- What guardrails would you require before launching?

### hm-onsite-domain-platform-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: ml-platform
kind: main
signal_points:
  - identifies platform users and their needs
  - reliability, multi-tenancy and cost
  - adoption and deprecation strategy
```
Teams train hundreds of models on shared compute. What would you change first in the platform, and how would you know it worked?

Follow-ups:
- Who loses if you change it?
- How do you decide what to deprecate?

### hm-onsite-priorwork-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - ownership of a hit with quantified result
  - counterfactual reasoning (what would have happened otherwise)
  - ability to explain decisions at the right depth
```
Pick the project from your background that you think is most relevant to this team. Why did you choose it, what was your decision, and what was the result relative to doing nothing?

Follow-ups:
- Who disagreed with your approach?
- What was the next-best option and why did you drop it?
- What did the result teach you that you did not expect?

### hm-onsite-priorwork-02
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - names a real miss and its cause
  - does not blame others
  - states what changed afterward
```
Tell me about something you shipped or recommended that turned out to be wrong or less valuable than you claimed. What did you miss?

Follow-ups:
- When did you tell people, and how?
- What do you do differently now?

### hm-onsite-vision-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - prioritized plan with metrics
  - states what they would not do
  - identifies riskiest assumption
```
If you joined this team, what are you doing in the first six months and what are you deliberately not doing?

Follow-ups:
- What would make you change this plan in month two?
- How will I know it is working?

### hm-onsite-scope-01
```yaml
roles: [mle, rs, ds]
levels: [L6]
variant: default
domain: any
kind: main
signal_points:
  - cross-team scope
  - influence without authority
  - resolves conflicting goals between teams
```
Tell me about a time you changed what another team worked on or how it worked, with no authority over them. What was their objection and how did it end?

Follow-ups:
- How did you find out the objection was real and not political?
- What did you give up?
- Who owned the decision after you left the room?

### hm-onsite-scope-02
```yaml
roles: [mle, rs, ds]
levels: [L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - owns work spanning more than one team
  - dependency management
  - outcome at organization level
```
What is the most cross-team piece of work you have led? What did each team need from the others, and where did it nearly break?

Follow-ups:
- What did you write down so that the work did not depend on you?
- How did you handle a team that would not commit?

### hm-onsite-challenge-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - handles challenge to own claim
  - updates with evidence or defends with evidence
  - not defensive
```
Take your last answer. I think it is wrong because the main benefit you cited is probably explained by something else. Convince me, or change my mind, or tell me where I am wrong.

Follow-ups:
- What evidence would settle it?
- If the team decided I was right, what would you do?

### hm-onsite-growth-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - realistic self-assessment
  - specific growth goal
  - receives feedback
```
What is the feedback you most often hear from managers or peers, and how have you acted on it?

Follow-ups:
- What would your peers say you should stop doing?

### hm-onsite-followup-why-not
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: followup
signal_points:
  - alternatives considered
```
"Why that and not the alternative? What would have to be true for the alternative to win?"

### hm-onsite-followup-fail
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: followup
signal_points:
  - production failure reasoning
```
"Suppose it fails in production at 2 am. What breaks first, and who is on call for it?"
