NOTEBOOK = {
    "file": "02b_Grammar_Noun_Phrases_Relatives_Future_Hedging.ipynb",
    "title": "02b - Advanced Grammar III: Noun Phrases, Relative Clauses, Future Forms and the Grammar of Hedging",
    "cells": [
        ("md", """
Four areas that distinguish C1 from B2 in professional and academic English:

1. **Noun phrases and nominalisation**: packing information into nouns (*the government's decision to cut taxes*).
2. **Relative clauses**: *whose, which* referring to a whole clause, *most of whom*, prepositions + *which/whom*.
3. **Future forms**: future continuous and perfect, *be about to / due to / set to / bound to*, future in the past.
4. **Hedging grammar**: making claims more precise and careful (*are likely to, may well, would seem to*).

It ends with a **text-level cloze** that mixes structures from Notebooks 01, 02 and 02b, because in real life nobody tells
you which structure to use.
"""),
        # ------------------------------------------------------------------ 1
        ("md", """
---
## 1. Noun phrases and nominalisation

Turning verbs and adjectives into nouns makes speech and writing **more concise and formal** - essential for reports,
presentations and news.

| Verb-based (B2) | Noun-based (C1) |
|---|---|
| The government **decided** to cut taxes, which surprised analysts. | **The government's decision** to cut taxes surprised analysts. |
| Prices **rose quickly**, so demand **fell**. | **The rapid rise** in prices led to **a fall** in demand. |
| We **analysed** the data **carefully**. | We carried out **a careful analysis** of the data. |
| The company **failed** because it was **badly managed**. | The company's **failure** was due to **poor management**. |

**Compound adjectives before nouns** (the number stays **singular**, with hyphens):
*a contract for two years* -> **a two-year contract** (~~two-years~~) · *a walk of ten minutes* -> **a ten-minute walk** ·
*a man who is 40 years old* -> **a 40-year-old man**.
"""),
        ("ex", {
            "id": "g3_noun_phrases",
            "title": "Nominalisation and compound adjectives",
            "instructions": "Complete the second sentence so it means the same as the first. Write only the missing words.",
            "items": [
                {"q": "The government decided to cut taxes, which surprised analysts.\nThe government's ______ taxes surprised analysts.", "a": ["decision to cut"]},
                {"q": "Prices rose rapidly, which led to lower demand.\nThe rapid ______ prices led to lower demand.", "a": ["rise in", "increase in"]},
                {"q": "The company failed because it was badly managed.\nThe company's failure was due to ______.", "a": ["poor management", "bad management"]},
                {"q": "We signed a contract for two years.\nWe signed a ______ contract.", "a": ["two-year", "two year"]},
                {"q": "The station is a walk of ten minutes from here.\nThe station is a ______ walk from here.", "a": ["ten-minute", "ten minute"]},
                {"q": "The CEO resigned suddenly, and this shocked investors.\nThe CEO's ______ shocked investors.", "a": ["sudden resignation"]},
                {"q": "They analysed the results carefully.\nThey carried out a ______ the results.", "a": ["careful analysis of", "thorough analysis of"]},
                {"q": "Unemployment has increased significantly.\nThere has been a ______ unemployment.", "a": ["significant increase in", "significant rise in"]},
            ],
        }),
        # ------------------------------------------------------------------ 2
        ("md", """
---
## 2. Relative clauses: the C1 details

| Structure | Example |
|---|---|
| **which** referring to a **whole clause** (comma!) | He didn't call, **which** really annoyed me. (~~what annoyed me~~) |
| **whose** (possession, people and things) | The colleague **whose** laptop was stolen... / a company **whose** profits doubled |
| preposition + **whom / which** (formal) | the person **to whom** I spoke / the reasons **for which**... |
| informal: preposition at the end | the person (who) I spoke **to** |
| quantifier + **of whom / of which** | Forty people applied, **most of whom** were unqualified. / three options, **none of which**... |
| **Non-defining** (extra info): commas, never *that* | My brother, **who** lives in Lima, is a doctor. (~~, that lives~~) |
| **Defining** (identifies): no commas, *that* is fine | The man **that / who** lives next door is a doctor. |
| **where / when / why** | the city **where** I grew up / the day **when** we met / the reason **why** |
"""),
        ("ex", {
            "id": "g3_relatives",
            "title": "Relative clauses",
            "instructions": "Write ONE word in each gap.",
            "items": [
                {"q": "He forgot my birthday again, ______ really upset me.", "a": ["which"]},
                {"q": "The colleague ______ laptop was stolen has reported it to the police.", "a": ["whose"]},
                {"q": "The person to ______ I spoke was very helpful.", "a": ["whom"]},
                {"q": "Forty people applied for the job, most of ______ were unqualified.", "a": ["whom"]},
                {"q": "We were offered three options, none of ______ was acceptable.", "a": ["which"]},
                {"q": "My manager, ______ has worked here for 20 years, is retiring.", "a": ["who"],
                 "why": "Non-defining clause (commas): 'that' is not possible."},
                {"q": "That's the café ______ we first met.", "a": ["where"]},
                {"q": "It's a company ______ profits have doubled in two years.", "a": ["whose"]},
                {"q": "The reason ______ I called is to ask about the invoice.", "a": ["why", "that", "-"]},
                {"q": "She passed all her exams, ______ was a huge relief for her parents.", "a": ["which"]},
            ],
        }),
        # ------------------------------------------------------------------ 3
        ("md", """
---
## 3. Future forms beyond *will* and *going to*

| Form | Use | Example |
|---|---|---|
| **Future continuous** (will be + -ing) | in progress at a future time; polite questions about plans | This time tomorrow I**'ll be flying** to Lima. / **Will** you **be using** the car tonight? |
| **Future perfect** (will have + pp) | completed before a future time | By Friday I**'ll have finished** the report. |
| **Future perfect continuous** | duration up to a future point | By 2030 I**'ll have been working** here for ten years. |
| **be about to** | very near future | Hurry, the train **is about to** leave. |
| **be due to** | scheduled | The plane **is due to** land at 6. |
| **be set to** (news) | likely / planned | Prices **are set to** rise. |
| **be bound to** | certain | It's **bound to** rain - it always does. |
| **be on the verge / point of** + -ing / noun | very near | The talks are **on the verge of** collapse. |
| **Future in the past** | a past plan or prediction | I **was going to** call you, but... / I knew she **would** succeed. |
"""),
        ("ex", {
            "id": "g3_future",
            "title": "Future forms",
            "instructions": "Complete with the correct future form of the verb in brackets, or ONE word.",
            "items": [
                {"q": "This time tomorrow I ______ (fly) to Buenos Aires.", "a": ["will be flying", "'ll be flying", "am going to be flying"]},
                {"q": "By Friday we ______ (finish) the first draft.", "a": ["will have finished", "'ll have finished"]},
                {"q": "By 2030 I ______ (work) here for ten years.", "a": ["will have been working", "'ll have been working", "will have worked"]},
                {"q": "Quick - the film is ______ to start!", "a": ["about"]},
                {"q": "The new CEO is ______ to arrive at 10 a.m. (it's on the official schedule)", "a": ["due"]},
                {"q": "Electricity prices are ______ to rise by 15% next year, according to experts.", "a": ["set", "expected", "likely"]},
                {"q": "Don't lend him money - he's ______ to forget to pay you back. (it's certain)", "a": ["bound", "sure", "certain"]},
                {"q": "After weeks of disagreement, the talks are on the ______ of collapse.", "a": ["verge", "brink", "point"]},
                {"q": "I ______ (call) you last night, but I fell asleep. (a plan that didn't happen)", "a": ["was going to call", "was going to ring"]},
                {"q": "______ you be using the car this evening? I'd like to borrow it.", "a": ["will"]},
            ],
        }),
        # ------------------------------------------------------------------ 4
        ("md", """
---
## 4. The grammar of hedging

In Notebook 07 you learn hedging **phrases**. Here you learn the **grammar**: how to adjust the *strength* of a claim.
In international workplaces and in anything written, over-certain claims sound naive or arrogant.

| Certainty | Grammar |
|---|---|
| Certain | Prices **will** rise. This **proves** that... |
| Very likely | Prices **are likely to / are expected to / will probably** rise. **In all likelihood**, ... |
| Probable | Prices **may well** rise. **It seems likely that**... |
| Possible | Prices **may / might / could** rise. **There is a chance that**... |
| Tentative | This **would seem to suggest** that... **There is some evidence to suggest** that... **Arguably**, ... |
| Generalising carefully | **It tends to be the case that**... People **tend to**... **In most cases**... |

Other tools: **appear / seem to** (*The policy appears to have failed*), **softening adverbs** (*somewhat, relatively,
to some extent*), **passive reporting** (*It has been suggested that...*).
"""),
        ("ex", {
            "id": "g3_hedging",
            "title": "Hedging: make the claim more careful",
            "type": "open",
            "instructions": "Rewrite each over-certain claim using the hedging tool in brackets.",
            "items": [
                {"q": "Prices will rise next year. (likely)", "a": ["Prices are likely to rise next year.", "Prices will likely rise next year."]},
                {"q": "This proves that the campaign worked. (would seem to)", "a": ["This would seem to suggest that the campaign worked.", "This would seem to show that the campaign worked."]},
                {"q": "The policy failed. (appear)", "a": ["The policy appears to have failed.", "It appears that the policy failed."]},
                {"q": "Young people prefer to work from home. (tend)", "a": ["Young people tend to prefer working from home.", "Young people tend to prefer to work from home."]},
                {"q": "The merger will create jobs. (may well)", "a": ["The merger may well create jobs."]},
                {"q": "Remote work reduces productivity. (some evidence)", "a": ["There is some evidence to suggest that remote work reduces productivity.", "There is some evidence that remote work reduces productivity."]},
                {"q": "The new system is better. (arguably)", "a": ["The new system is arguably better.", "Arguably, the new system is better."]},
                {"q": "Customers are unhappy with the price. (to some extent)", "a": ["To some extent, customers are unhappy with the price.", "Customers are unhappy with the price to some extent."]},
            ],
        }),
        # ------------------------------------------------------------------ 5
        ("md", """
---
## 5. Text-level cloze: mixed structures (Notebooks 01, 02, 02b)

Read the whole email first. Then decide **which structure** each gap needs - nobody tells you in real life!

> Dear team,
>
> I'm writing about last week's product launch. **(1)** ______ (we / know) how unreliable the supplier was, we would never
> have signed the contract. Not until the Tuesday **(2)** ______ we realise that half the stock was missing.
> **(3)** ______ we should have done was check the contract terms before the launch date. **(4)** ______ (warn) twice
> by the logistics team, we really should have acted sooner. The supplier, **(5)** ______ contract expires in March,
> is **(6)** ______ to ask for an extension, and the board is **(7)** ______ to refuse. By the end of the month we
> **(8)** ______ (find) an alternative, and next quarter's results **(9)** ______ well improve as a result.
> **(10)** ______ you have any questions, please let me know.
"""),
        ("ex", {
            "id": "g3_text_cloze",
            "title": "Mixed-structure cloze (email)",
            "instructions": "Write the missing word(s) for each numbered gap in the email above.",
            "items": [
                {"q": "(1) ______ (we / know) how unreliable the supplier was...", "a": ["had we known", "if we had known"]},
                {"q": "(2) Not until the Tuesday ______ we realise...", "a": ["did"]},
                {"q": "(3) ______ we should have done was check the contract terms...", "a": ["what"]},
                {"q": "(4) ______ (warn) twice by the logistics team...", "a": ["having been warned"]},
                {"q": "(5) The supplier, ______ contract expires in March...", "a": ["whose"]},
                {"q": "(6) is ______ to ask for an extension (= planned / scheduled)", "a": ["due", "set", "about", "likely", "expected", "going"]},
                {"q": "(7) and the board is ______ to refuse (= it's certain)", "a": ["bound", "sure", "certain", "likely"]},
                {"q": "(8) By the end of the month we ______ (find) an alternative", "a": ["will have found", "'ll have found"]},
                {"q": "(9) next quarter's results ______ well improve", "a": ["may", "might", "could"]},
                {"q": "(10) ______ you have any questions, please let me know.", "a": ["should", "if"]},
            ],
        }),
        ("md", """
---
### Your turn: output with a checklist
Write (or record and transcribe) a **150-word update** to your team about a project that is behind schedule. Use at least:
- [ ] one nominalisation (*the delay in..., the decision to...*)
- [ ] one *which* referring to a whole clause
- [ ] one future perfect or *be due to / be set to*
- [ ] two hedging structures
- [ ] one inverted conditional or a past modal from Notebooks 01-02

Then paste it into an AI assistant with: *"Check my use of the structures in this list: [paste the checklist]. Then list any
errors with articles and prepositions. Don't rewrite the text."* Log your errors with `log_mistake()`.
"""),
        ("code", """
# log_study(60, "grammar", "NB02b relative clauses + hedging")
"""),
    ],
}
