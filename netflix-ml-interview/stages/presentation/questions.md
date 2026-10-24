# Questions: presentation (panel probe bank)

Topics are built from reported themes and Netflix-published practice. None is a reported verbatim question.
Lena = methodology probes; Marcus = impact and decision probes.

## research-talk (rs, mle)

### presentation-rt-baseline-01
```yaml
roles: [rs, mle]
levels: [L4, L5, L6]
variant: research-talk
domain: any
kind: main
signal_points: [names the strongest baseline, explains why it is fair, quantifies the gap with uncertainty]
```
Lena: What is the strongest simple baseline for the problem you presented, and how did you make sure it got the same tuning effort as your method?

Follow-ups:
- If the baseline closes half the gap, does the work still matter?
- What would convince you that the improvement is within noise?

### presentation-rt-assumption-02
```yaml
roles: [rs, mle]
levels: [L4, L5, L6]
variant: research-talk
domain: any
kind: main
signal_points: [lists key assumptions explicitly, says which is most fragile, describes how it was tested or would be]
```
Lena: Which assumption in your approach would hurt the most if it were false, and what did you do to check it?

Follow-ups:
- Show me where in your results that assumption could have broken and did not.

### presentation-rt-alternative-03
```yaml
roles: [rs, mle]
levels: [L4, L5, L6]
variant: research-talk
domain: any
kind: main
signal_points: [compares at least one distinct alternative family, gives a reason for rejection, acknowledges where the alternative wins]
```
Lena: Name another family of approaches you considered and why you did not pick it. Where would it win?

Follow-ups:
- If compute or labels were ten times cheaper, would you choose differently?

### presentation-rt-evaluation-04
```yaml
roles: [rs, mle]
levels: [L4, L5, L6]
variant: research-talk
domain: recsys
kind: main
signal_points: [separates offline metric from online outcome, explains the gap, proposes a validation plan]
```
Marcus: Your offline metric improved. What would you expect the online result to be, and what could make the two disagree?

Follow-ups:
- How would you design the online test, and which guardrail would you watch first?

### presentation-rt-impact-05
```yaml
roles: [rs, mle]
levels: [L4, L5, L6]
variant: research-talk
domain: any
kind: main
signal_points: [states a concrete decision or metric that changed, attributes the effect honestly, explains adoption by the team]
```
Marcus: Who used this work, and what did they do differently afterwards? What number moved?

Follow-ups:
- How much of that movement do you attribute to your contribution versus others'?
- If the team had ignored your result, what would have been lost?

### presentation-rt-failure-06
```yaml
roles: [rs, mle]
levels: [L4, L5, L6]
variant: research-talk
domain: any
kind: main
signal_points: [names a real negative result, shows what was learned, changes next step because of it]
```
Lena: What was the experiment that did not work, and how did it change your direction?

### presentation-rt-explain-07
```yaml
roles: [rs, mle]
levels: [L4, L5, L6]
variant: research-talk
domain: any
kind: followup
signal_points: [explains the core idea without jargon in two minutes]
```
Marcus: Explain the core idea to a product manager in two minutes, without using a formula.

### presentation-rt-culture-08
```yaml
roles: [rs, mle]
levels: [L4, L5, L6]
variant: research-talk
domain: any
kind: culture
signal_points: [credits collaborators by name, admits limits, asks the panel a real question]
```
Marcus: Who else shaped this work, and what did they disagree with you about?

## take-home (ds)

### presentation-th-validity-01
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: take-home
domain: experimentation
kind: main
signal_points: [checks sample ratio and pre-period balance before effects, states what failure would imply, does not skip checks]
```
Lena: Before you show me any effect, how do you know this experiment is trustworthy? What would you have done if the sample ratio were off?

Follow-ups:
- What would a significant pre-period difference between arms tell you?

### presentation-th-metric-02
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: take-home
domain: experimentation
kind: main
signal_points: [defends the primary metric against alternatives, names what it misses, defines guardrails with thresholds]
```
Marcus: Why this primary metric and not another? What does it fail to capture, and which guardrail would make you stop?

Follow-ups:
- Would a higher click-through on the new feature count as success? Why or why not?

### presentation-th-variance-03
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: take-home
domain: experimentation
kind: main
signal_points: [explains why the pre-period covariate is unbiased, reports interval width before and after, states the correlation that drives the gain]
```
Lena: How did you use the pre-experiment data, and why does that not bias the effect? How much narrower did your interval get?

Follow-ups:
- What goes wrong if the covariate is measured after assignment?

### presentation-th-heterogeneity-04
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: take-home
domain: experimentation
kind: main
signal_points: [accounts for multiple comparisons, separates pre-specified from exploratory slices, proposes a confirmation step]
```
Lena: You found differences across segments. How many slices did you look at, and how much should we trust the biggest one?

Follow-ups:
- Would you launch to one segment only on this evidence?

### presentation-th-decision-05
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: take-home
domain: experimentation
kind: main
signal_points: [gives a clear ship, iterate or stop recommendation, ties it to cost and risk, names the next test]
```
Marcus: Give me your recommendation in two sentences, then tell me what would change your mind.

### presentation-th-itt-06
```yaml
roles: [ds]
levels: [L5, L6]
variant: take-home
domain: causal-inference
kind: main
signal_points: [separates intent-to-treat from exposed-only, names the selection problem of comparing clickers, offers a valid alternative]
```
Lena: A teammate proposes comparing members who clicked the new element against everyone in control. What is wrong with that, and what would you estimate instead?

### presentation-th-novelty-07
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: take-home
domain: experimentation
kind: main
signal_points: [looks at effect by days since exposure, models decay or uses later window, avoids extrapolating week 1]
```
Lena: How do you know whether the lift persists? What would you plot, and what horizon would you decide on?

### presentation-th-survey-08
```yaml
roles: [ds]
levels: [L4, L5, L6]
variant: take-home
domain: experimentation
kind: followup
signal_points: [identifies response bias, suggests weighting or a randomized prompt]
```
Marcus: Only some members answered the survey. How does that change what you can say about satisfaction?
