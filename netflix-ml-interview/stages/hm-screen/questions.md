# Question bank: hm-screen

Surface-level, two-way conversation (research.md 2 Hiring manager screen). Original prompts built from reported topics.

### hm-screen-past-work-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - clear problem statement and own role
  - quantified outcome with baseline
  - relevance to the team's domain
```
Tell me about the project you are most proud of. What was the problem, what did you personally do, and how did you know it worked?

Follow-ups:
- What was the baseline and how much did it move?
- What would you do differently?
- Who else was involved and what was their part?

### hm-screen-past-work-02
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - second project showing breadth
  - trade-off articulated
  - honest about a miss
```
What is a second project that is different from the first, and where did it not go as planned?

Follow-ups:
- When did you realize it was not working?
- What did you tell stakeholders and when?

### hm-screen-fit-recsys-01
```yaml
roles: [mle, rs]
levels: [L4, L5, L6]
variant: default
domain: recsys
kind: main
signal_points:
  - links own work to ranking, retrieval or personalization needs
  - understands offline versus online gap
  - knows scale constraints
```
Our team works on personalization: ranking titles for members across many surfaces. Where does your background connect most with that, and where would you need to ramp up?

Follow-ups:
- How have you dealt with the gap between offline metrics and an A/B result?
- What have you read or built lately that touches this?

### hm-screen-fit-exp-01
```yaml
roles: [ds, rs, mle]
levels: [L4, L5, L6]
variant: default
domain: experimentation
kind: main
signal_points:
  - links own work to experiment design and decisions
  - understands sensitivity and long-term outcomes
  - partner-facing communication
```
We make most product decisions with experiments. Tell me about a test you designed or analyzed that changed a decision, and what was hard about it.

Follow-ups:
- How did you choose the primary metric?
- Did you ever recommend not shipping a change that looked positive? What happened?

### hm-screen-fit-platform-01
```yaml
roles: [mle, ds, rs]
levels: [L4, L5, L6]
variant: default
domain: ml-platform
kind: main
signal_points:
  - platform thinking: users of the platform and their needs
  - reliability and cost awareness
  - adoption story
```
Part of what we do is give other teams tools to train and serve models. Tell me about something you built that others had to adopt. How did you get them to use it?

Follow-ups:
- What did users complain about first?
- How did you decide what not to build?

### hm-screen-scope-01
```yaml
roles: [mle, rs, ds]
levels: [L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - scope beyond own tasks
  - influence on other teams or leadership
  - decision ownership
```
Describe the largest area you owned. What decisions were yours, and what did you need other teams to agree to?

Follow-ups:
- Who disagreed and how did that resolve?
- What did you stop doing to make room for it?

### hm-screen-curiosity-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - recent learning
  - applies learning to work
  - asks questions back
```
What have you learned in the last few months that changed how you approach your work?

Follow-ups:
- What would you like to explore on our team?
- What do you think is overrated in your field?

### hm-screen-culture-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - decision-making style: who decides
  - candor in disagreement
  - ownership of mistakes
```
Think of your last significant decision at work. Who made the final call, who disagreed, and how did it end?

Follow-ups:
- How did you find out what people really thought?
- What would you have changed in how it was decided?

### hm-screen-motivation-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - motivation beyond pay
  - realistic expectation of a demanding environment
  - what they want next
```
Netflix expects a lot from people and gives a lot of freedom. What about that appeals to you, and what worries you?

Follow-ups:
- What kind of manager helps you do your best work?
- How do you feel about being measured by the keeper test, "would I fight to keep this person"?

### hm-screen-candidate-qa-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - quality of candidate's questions
  - interest in problems and decision process
  - not only perks or process
```
What questions do you have for me about the team, the work or Netflix?

Follow-ups:
- I will tell you honestly what I can and cannot say; what else would help you decide?

### hm-screen-followup-metrics
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: followup
signal_points:
  - quantifies impact
```
"If I called your old manager, what number would they quote for the impact of that work?"

### hm-screen-followup-we
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: followup
signal_points:
  - personal ownership
```
"You said 'we'. Which part did you personally decide or build?"
