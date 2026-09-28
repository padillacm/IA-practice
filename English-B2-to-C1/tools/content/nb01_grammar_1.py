NOTEBOOK = {
    "file": "01_Grammar_Conditionals_Inversion_Clefts.ipynb",
    "title": "01 - Advanced Grammar I: Conditionals, Wishes, Inversion and Cleft Sentences",
    "cells": [
        ("md", """
At B2 you already know the "big four" conditionals. At C1 the difference is **flexibility**: mixing time frames,
using formal alternatives to *if*, and moving words around for **emphasis** (inversion, cleft sentences).
These structures are what make speech and writing sound *controlled* rather than just correct.

**How to use this notebook** (about 10-12 hours over 2 weeks):
1. Study one section per session. Read the examples aloud - your mouth needs to learn the structure too.
2. Do the exercise, run `check()`, read every explanation for the items you missed.
3. Finish each section with the *Your turn* task: write sentences **about your own life**. Personal = memorable.
4. Redo the sets you scored under 85% after 2-3 days.
"""),
        # ------------------------------------------------------------------ 1
        ("md", """
---
## 1. Conditionals beyond the basics

### 1.1 Mixed conditionals

The *if*-clause and the main clause refer to **different times**.

| Pattern | Meaning | Example |
|---|---|---|
| *If* + past perfect, *would* + infinitive | past condition -> **present** result | If I **had accepted** that offer, I **would be** in Canada now. |
| *If* + past simple, *would have* + past participle | **present/permanent** situation -> past result | If I **weren't** so shy, I **would have spoken** to her at the party. |

### 1.2 Formal inversion instead of *if*

Drop *if* and invert. Very common in formal writing, emails and presentations.

| Normal | Inverted |
|---|---|
| If I **had known**... | **Had I known**... |
| If you **should need** anything / If you need anything... | **Should you need** anything... |
| If the CEO **were to** resign... | **Were the CEO to** resign... |
| If it **hadn't been** for your help... | **Had it not been** for your help... (never *Hadn't it been*) |

### 1.3 Alternatives to *if*

| Expression | Nuance | Example |
|---|---|---|
| *unless* | = if ... not | I won't go **unless** you come too. |
| *provided / providing (that), as long as, on condition that* | strong condition | You can borrow it **as long as** you return it by Friday. |
| *supposing / suppose, what if* | imagining | **Supposing** you lost your job, what would you do? |
| *but for* + noun, *without* + noun | = if it hadn't been for | **But for** the traffic, we'd have been on time. |
| *otherwise* | = if not (after the main idea) | Leave now; **otherwise** you'll miss the bus. |
| *in case* | **precaution** (NOT a condition!) | Take an umbrella **in case** it rains. |
| *even if* | the condition doesn't change the result | **Even if** she apologised, I wouldn't forgive her. |
| *whether or not* | both options, same result | I'm going **whether or not** you like it. |

> Classic Spanish-speaker trap: *"en caso de que"* is usually **if**, not *in case*.
> *"Call me in case you need help"* sounds odd. Use **if** (or *should you need...*).
"""),
        ("ex", {
            "id": "g1_mixed",
            "title": "Mixed conditionals",
            "instructions": "Put the verb in brackets into the correct form. Think: which time does each clause refer to?",
            "items": [
                {"q": "If I ______ (not / miss) the train this morning, I wouldn't be so stressed now.", "a": ["hadn't missed", "had not missed"],
                 "why": "Past condition (this morning) -> present result (now)."},
                {"q": "If she ______ (be) more organised in general, she would have finished the report on time.", "a": ["were", "was"],
                 "why": "Permanent characteristic (present) -> past result."},
                {"q": "If we had invested in that company ten years ago, we ______ (be) rich now.", "a": ["would be"],
                 "why": "Past condition -> present result: would + infinitive."},
                {"q": "If he ______ (speak) better English, he would have got the job last month.", "a": ["spoke"],
                 "why": "Present/general ability -> past result."},
                {"q": "I ______ (not / ask) you for help yesterday if I didn't trust you.", "a": ["wouldn't have asked", "would not have asked"],
                 "why": "Present situation (I trust you) -> past result (yesterday)."},
                {"q": "If the government had acted sooner, the crisis ______ (not / be) so severe today.", "a": ["wouldn't be", "would not be"]},
                {"q": "You ______ (not / feel) so tired now if you had gone to bed earlier.", "a": ["wouldn't feel", "would not feel"]},
                {"q": "If I ______ (know) him better, I would have invited him to the wedding last month.", "a": ["knew"],
                 "why": "'I don't know him well' is a present state -> past result."},
            ],
        }),
        ("ex", {
            "id": "g1_cond_inversion",
            "title": "Inverted conditionals and 'but for'",
            "instructions": "Complete the second sentence so it means the same as the first. Write only the missing words.",
            "items": [
                {"q": "If I had known about the problem, I would have helped.\n______ about the problem, I would have helped.", "a": ["had I known"]},
                {"q": "If you need any further information, please contact us.\n______ any further information, please contact us.", "a": ["should you need", "should you require"]},
                {"q": "If the president resigned, there would be an election.\n______ resign, there would be an election.", "a": ["were the president to"]},
                {"q": "If it hadn't been for your help, I would have failed.\n______ your help, I would have failed.", "a": ["had it not been for", "but for", "without"],
                 "why": "Negative inversion keeps 'not' after the subject: Had it NOT been for... (never *Hadn't it been*)."},
                {"q": "If they had not cancelled the flight, we would be in Rome now.\n______ the flight, we would be in Rome now.", "a": ["had they not cancelled"]},
                {"q": "If it weren't for the rain, we could eat outside.\n______ the rain, we could eat outside.", "a": ["were it not for", "but for", "without"]},
            ],
        }),
        ("ex", {
            "id": "g1_if_alternatives",
            "title": "Alternatives to 'if'",
            "instructions": "Choose the best option.",
            "items": [
                {"q": "Take an umbrella ___ it rains later.", "options": ["in case", "unless", "provided"],
                 "why": "Precaution = in case. (Take it now because it might rain.)"},
                {"q": "You can borrow my car ___ you bring it back by six.", "options": ["provided", "unless", "in case"]},
                {"q": "I won't go to the party ___ you come with me.", "options": ["unless", "provided", "as long as"]},
                {"q": "___ you won the lottery, what would you do first?", "options": ["Supposing", "Unless", "Provided"]},
                {"q": "___ the storm, we would have arrived on time.", "options": ["But for", "Unless", "Otherwise"]},
                {"q": "Leave now; ___, you'll miss the bus.", "options": ["otherwise", "unless", "in case"]},
                {"q": "I'm going to the concert ___ you like it or not.", "options": ["whether", "even if", "unless"]},
                {"q": "___ she apologised, I still wouldn't forgive her.", "options": ["Even if", "Unless", "Provided that"]},
            ],
        }),
        ("md", """
### Your turn (1)
Write 4 true sentences about **your** life: 2 mixed conditionals, 1 with *Had I...*, 1 with *as long as* or *unless*.
Then say them aloud three times, faster each time.

*Example: If I hadn't started learning English as a teenager, I wouldn't be working for an international company now.*

1.
2.
3.
4.
"""),
        # ------------------------------------------------------------------ 2
        ("md", """
---
## 2. Wishes, regrets and the "unreal past"

After certain expressions, a **past form describes something unreal** (not a past time).

| Structure | Use | Example |
|---|---|---|
| *wish / if only* + past simple | present situation you'd like to be different | I wish I **had** more time. / If only I **knew** the answer. |
| *wish / if only* + past perfect | regret about the past | I wish I **hadn't said** that. |
| *wish* + *would* | annoying behaviour / change you want from **someone else** | I wish my neighbour **would stop** hammering. (not *I wish I would*) |
| *wish* + *could* | ability you don't have | I wish I **could** play the piano. |
| *I'd rather / I'd sooner* + other subject + past simple | preference about another person's action | I'd rather you **didn't smoke** in here. |
| *I'd rather* + infinitive (same subject) | your own preference | I'd rather **stay** in tonight. |
| *It's (high / about) time* + subject + past simple | something should already be happening | It's high time we **left**. / It's time **to leave**. |
| *as if / as though* + past | unreal comparison | He talks **as if** he **were** the boss. |

> In formal English, *were* is preferred for all persons: *If I were you... / as if she were...*. In conversation *was* is also fine.
"""),
        ("ex", {
            "id": "g1_wishes",
            "title": "Wishes and unreal past",
            "instructions": "Put the verb in brackets into the correct form.",
            "items": [
                {"q": "I wish I ______ (have) more free time - I'm exhausted.", "a": ["had"]},
                {"q": "She wishes she ______ (not / sell) her old flat; prices have doubled since.", "a": ["hadn't sold", "had not sold"]},
                {"q": "I wish my neighbours ______ (stop) playing loud music every night.", "a": ["would stop"],
                 "why": "wish + would = annoying habit of someone else that you want to change."},
                {"q": "If only I ______ (listen) to your advice last year!", "a": ["had listened"]},
                {"q": "It's high time the government ______ (do) something about housing.", "a": ["did"]},
                {"q": "I'd rather you ______ (not / tell) anyone about this yet.", "a": ["didn't tell", "did not tell"]},
                {"q": "He talks as if he ______ (be) the boss, but he's just an intern.", "a": ["were", "was"]},
                {"q": "I'd rather ______ (stay) at home tonight, if you don't mind.", "a": ["stay"],
                 "why": "Same subject (I ... I) -> bare infinitive."},
                {"q": "Come on, it's time ______ (leave); the taxi's waiting.", "a": ["to leave", "we left", "we were leaving"]},
                {"q": "I wish I ______ (can) speak Japanese.", "a": ["could"]},
            ],
        }),
        ("md", """
### Your turn (2)
Write 3 regrets or wishes that are **true for you** (one present, one past, one with *would* about someone else),
plus one sentence with *It's high time...*

1.
2.
3.
4.
"""),
        # ------------------------------------------------------------------ 3
        ("md", """
---
## 3. Inversion for emphasis

Put a **negative or restrictive expression at the front** and use **question word order** (auxiliary + subject).
It sounds formal and dramatic - perfect for presentations, storytelling and writing. Use it sparingly in casual chat.

| Expression | Example |
|---|---|
| Never (before) / Rarely / Seldom | **Never have I seen** such chaos. / **Rarely do we get** complaints. |
| Hardly / Scarcely ... **when** | **Hardly had** I sat down **when** the phone rang. |
| No sooner ... **than** | **No sooner had** we arrived **than** it started to rain. |
| Not only ... but (also) | **Not only did she** write it, **but** she **also** directed it. |
| Not until ... | **Not until** I got home **did I realise** I'd lost my keys. |
| Only after / Only when / Only by / Only then | **Only when** he left **did I understand**. (inversion goes in the **main** clause) |
| Under no circumstances / On no account / In no way / At no time | **Under no circumstances should you** open this door. |
| Little | **Little did he know** that... |
| Nowhere | **Nowhere will you find** better coffee. |
| So + adjective / Such + be + noun | **So loud was** the music that... / **Such was** the demand that... |

**Word-order formula:** Negative adverbial + **auxiliary** (do/does/did, have/had, modal, be) + **subject** + main verb.
If there's no auxiliary in the normal sentence, add *do/does/did*: *I rarely go* -> *Rarely **do** I **go***.
"""),
        ("ex", {
            "id": "g1_inversion",
            "title": "Negative inversion",
            "instructions": "Complete the second sentence so it means the same as the first. Write only the missing words.",
            "items": [
                {"q": "I have never seen such a beautiful sunset.\nNever ______ such a beautiful sunset.", "a": ["have I seen"]},
                {"q": "As soon as I arrived, the phone rang.\nNo sooner ______ than the phone rang.", "a": ["had I arrived"]},
                {"q": "He didn't realise the danger he was in.\nLittle ______ the danger he was in.", "a": ["did he realise", "did he realize"]},
                {"q": "You must not open this door under any circumstances.\nUnder no circumstances ______ this door.", "a": ["must you open", "should you open"]},
                {"q": "She not only wrote the script, but she also directed the film.\nNot only ______ the script, but she also directed the film.", "a": ["did she write"]},
                {"q": "I only understood the problem after reading the report.\nOnly after reading the report ______ the problem.", "a": ["did I understand"],
                 "why": "With 'Only after/when/by', the inversion happens in the MAIN clause."},
                {"q": "We didn't find out the truth until years later.\nNot until years later ______ the truth.", "a": ["did we find out", "did we discover", "did we learn"]},
                {"q": "The noise was so loud that we couldn't sleep.\nSo ______ that we couldn't sleep.", "a": ["loud was the noise"]},
                {"q": "The demand was so high that tickets sold out in minutes.\nSuch ______ that tickets sold out in minutes.", "a": ["was the demand"]},
                {"q": "We had hardly sat down when the lights went out.\nHardly ______ down when the lights went out.", "a": ["had we sat"]},
                {"q": "People rarely get a second chance like this.\nRarely ______ a second chance like this.", "a": ["do people get"]},
                {"q": "You can't find better coffee anywhere in the city.\nNowhere in the city ______ better coffee.", "a": ["can you find", "will you find"]},
            ],
        }),
        ("md", """
### Your turn (3)
Tell a short dramatic story (5-6 sentences) about a travel disaster or a lucky escape using **at least three** inversions
(*No sooner had..., Little did I know..., Only then did I...*). Then record yourself telling it without reading.
"""),
        # ------------------------------------------------------------------ 4
        ("md", """
---
## 4. Cleft sentences (focusing information)

Cleft sentences split one idea into two clauses to **put the spotlight** on one part. Native speakers use them
constantly in speech to emphasise, contrast and correct.

| Type | Structure | Example | Neutral version |
|---|---|---|---|
| *It*-cleft | It + be + **focus** + that/who... | **It was Maria** who called, not Ana. | Maria called. |
| *It ... not until* | It + be + not until + time + that... | **It wasn't until** Friday **that** we found the error. | We didn't find it until Friday. |
| *Wh*-cleft | What + clause + be + **focus** | **What I need is** a holiday. | I need a holiday. |
| *Wh*-cleft (actions) | What + subject + did + was (to) + infinitive | **What she did was (to) call** the police. | She called the police. |
| *What happened was* | What happened was (that) + clause | **What happened was that** the server crashed. | The server crashed. |
| *All* | All + clause + be + focus | **All I want is** some peace and quiet. | I only want peace and quiet. |
| *The thing / reason / place...* | The + noun + clause + be | **The reason (why)** I left **was that**... / **The place where** we met... | |
| Reversed | Focus + be + what... | **A holiday is what** I need. | |

**In conversation**, clefts are great "thinking time" starters: *What I'm trying to say is... / The thing is... / What worries me is...*
"""),
        ("ex", {
            "id": "g1_clefts",
            "title": "Cleft sentences",
            "instructions": "Complete the second sentence so it means the same as the first. Write only the missing words.",
            "items": [
                {"q": "I need a long holiday.\nWhat ______ a long holiday.", "a": ["I need is"]},
                {"q": "Her attitude annoys me, not her work.\nIt's ______ annoys me, not her work.", "a": ["her attitude that", "her attitude which"]},
                {"q": "I only want some peace and quiet.\nAll ______ some peace and quiet.", "a": ["I want is"]},
                {"q": "He moved back home because he lost his job.\nThe reason ______ that he lost his job.", "a": ["he moved back home was", "why he moved back home was"]},
                {"q": "We didn't discover the error until Friday.\nIt ______ Friday that we discovered the error.", "a": ["wasn't until", "was not until"]},
                {"q": "She called the police.\nWhat she ______ call the police.", "a": ["did was", "did was to"]},
                {"q": "The manager made the final decision.\nIt ______ made the final decision.", "a": ["was the manager who", "was the manager that"]},
                {"q": "I love the way she explains things.\nWhat ______ the way she explains things.", "a": ["I love is"]},
                {"q": "Something strange happened: the lights went off.\nWhat ______ that the lights went off.", "a": ["happened was"]},
                {"q": "I met my wife in Lisbon.\nLisbon ______ I met my wife.", "a": ["is where", "was where", "is the place where", "was the place where"]},
            ],
        }),
        ("md", """
### Your turn (4)
Answer these questions aloud using a cleft sentence to start each answer:

* What do you like most about your job/studies? -> *What I like most is...*
* What annoys you about public transport? -> *What really gets on my nerves is...*
* Who influenced you the most? -> *It was my ... who...*
* When did you realise you wanted to improve your English? -> *It wasn't until... that...*
"""),
        # ------------------------------------------------------------------ review
        ("md", """
---
## 5. Mixed review: error correction

Each sentence contains **one** mistake. Rewrite the whole sentence correctly.
These are open answers - `check()` marks exact matches and shows the model answer for the rest, so you can self-check.
"""),
        ("ex", {
            "id": "g1_errors",
            "title": "Error correction (Grammar I)",
            "type": "open",
            "instructions": "Rewrite each sentence correctly.",
            "items": [
                {"q": "Never I have seen such chaos.", "a": ["Never have I seen such chaos."]},
                {"q": "If I would have known, I would have come.", "a": ["If I had known, I would have come.", "Had I known, I would have come."]},
                {"q": "I wish I would be taller.", "a": ["I wish I were taller.", "I wish I was taller."]},
                {"q": "Only when he left I realised my mistake.", "a": ["Only when he left did I realise my mistake.", "Only when he left did I realize my mistake."]},
                {"q": "What I need it is more time.", "a": ["What I need is more time."]},
                {"q": "It's time we go home.", "a": ["It's time we went home.", "It's time to go home."]},
                {"q": "Hardly had we arrived than it started to rain.", "a": ["Hardly had we arrived when it started to rain."]},
                {"q": "Had I not been so tired, I would go out last night.", "a": ["Had I not been so tired, I would have gone out last night."]},
                {"q": "Hadn't it been for you, we would have lost.", "a": ["Had it not been for you, we would have lost."]},
                {"q": "Call me in case you need anything, and I'll come.", "a": ["Call me if you need anything, and I'll come.", "Call me if you need anything and I'll come."]},
            ],
        }),
        ("md", """
---
### Before you leave this notebook
* Score **85%+** on every set? Move on to Notebook 02. Otherwise, schedule a redo in 2-3 days.
* Log your time: `log_study(90, "grammar", "NB01 section 3")` (see Notebook 09).
* Recommended extra practice: *Advanced Grammar in Use* (Hewings), units on conditionals, inversion and cleft sentences.
"""),
        ("code", """
# log_study(60, "grammar", "NB01 - conditionals")
"""),
    ],
}
