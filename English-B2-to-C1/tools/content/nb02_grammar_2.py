NOTEBOOK = {
    "file": "02_Grammar_Modals_Passives_Participles.ipynb",
    "title": "02 - Advanced Grammar II: Past Modals, Advanced Passives, Participle Clauses, Emphasis and the Subjunctive",
    "cells": [
        ("md", """
This notebook covers the structures that make C1 English sound **concise and precise**:
speculating about the past, reporting information impersonally, packing ideas into participle clauses,
avoiding repetition, and formal "subjunctive" patterns.

Same method as Notebook 01: explanation -> exercise -> `check()` -> *Your turn*. About 10-12 hours.
"""),
        # ------------------------------------------------------------------ 1
        ("md", """
---
## 1. Past modals: deduction, criticism and "unnecessary" actions

**Modal + have + past participle** talks about the past.

| Form | Meaning | Example |
|---|---|---|
| *must have* done | I'm **sure** it happened | The ground's wet - it **must have rained**. |
| *can't / couldn't have* done | I'm **sure** it didn't happen | She **can't have seen** me; she didn't say hello. |
| *may / might / could have* done | **possibly** it happened | I **might have left** my keys at work. |
| *should / ought to have* done | it was the right thing, but you **didn't** | You **should have told** me! |
| *shouldn't have* done | it was wrong, but you **did** | I **shouldn't have eaten** so much. |
| *could have* done | possible in the past, but **didn't happen** | You **could have been** hurt! |
| *needn't have* done | you **did** it, but it wasn't necessary | We **needn't have hurried** - the film started late. |
| *didn't need to / didn't have to* do | it wasn't necessary (usually you **didn't** do it) | I **didn't need to take** a taxi; Ana gave me a lift. |
| *must have been* doing | sure about an activity in progress | He looks exhausted - he **must have been working** all night. |

> **Pronunciation tip:** in fast speech *have* is reduced to /əv/: *must've* /ˈmʌstəv/, *should've*, *could've*.
> (That's why some natives mistakenly write "should of"!)
"""),
        ("ex", {
            "id": "g2_past_modals",
            "title": "Past modals",
            "instructions": "Complete each sentence with a past modal and the verb in brackets.",
            "items": [
                {"q": "The streets are wet. It ______ (rain) last night.", "a": ["must have rained"]},
                {"q": "She ______ (see) me - she walked straight past without saying hello.", "a": ["can't have seen", "cannot have seen", "couldn't have seen"]},
                {"q": "I'm not sure where my keys are. I ______ (leave) them at the office.", "a": ["might have left", "may have left", "could have left"]},
                {"q": "You ______ (tell) me it was a formal dinner! I was the only one in jeans.", "a": ["should have told", "ought to have told"]},
                {"q": "We ______ (buy) so much food - half of it went to waste.", "a": ["needn't have bought", "need not have bought", "shouldn't have bought", "should not have bought"]},
                {"q": "He looks exhausted. He ______ (work) all night.", "a": ["must have been working", "must have worked"]},
                {"q": "That ______ (be) Tom you saw at the party - he's in Canada this month.", "a": ["can't have been", "cannot have been", "couldn't have been"]},
                {"q": "Why did you walk home alone at 3 a.m.? You ______ (get) attacked!", "a": ["could have got", "could have gotten", "might have got", "might have gotten", "could have been"]},
                {"q": "I ______ (take) a taxi because Anna offered me a lift, so I saved some money.", "a": ["didn't need to take", "did not need to take", "didn't have to take", "did not have to take"]},
                {"q": "They ______ (forget) about the meeting - they're never late.", "a": ["must have forgotten"]},
            ],
        }),
        ("md", """
### Your turn (1)
Look at these situations and speculate aloud with at least **two** different past modals each:
* Your colleague arrived at work soaking wet and in a very bad mood.
* The restaurant you booked is closed, with no sign on the door.
* Your friend hasn't answered your messages for three days.
"""),
        # ------------------------------------------------------------------ 2
        ("md", """
---
## 2. Advanced passives and the causative

### 2.1 Impersonal / reporting passives
Used constantly in news, reports and academic English to present information **without committing to it**.

| Pattern | Example |
|---|---|
| *It is said / believed / thought / reported / expected / alleged that...* | **It is believed that** the painting is a fake. |
| Subject + *is said to* + **infinitive** (same time / future) | The painting **is believed to be** a fake. |
| Subject + *is said to* + **have + past participle** (earlier) | He **is said to have earned** millions. |
| Subject + *is said to* + **be + -ing** (in progress now) | The company **is reported to be planning** layoffs. |
| *There is said to be...* | **There are thought to be** over 100 survivors. |

### 2.2 The causative
| Pattern | Meaning | Example |
|---|---|---|
| *have / get* + object + past participle | someone does it for you | I'm **having my car repaired**. |
| same pattern | something bad happened to you | She **had her bag stolen**. |
| *get* + person + **to** + infinitive | persuade | I **got my brother to help** me. |
| *have* + person + infinitive | ask/arrange (esp. AmE, professional) | I'll **have my assistant call** you. |

### 2.3 Other C1 passives
* *need* + -ing = passive meaning: *The windows **need cleaning*** (= need to be cleaned).
* *get*-passive (informal, often unexpected/negative events): *He **got fired**.*
* Passive with modals + perfect: *The problem **should have been fixed** weeks ago.*
"""),
        ("ex", {
            "id": "g2_passives",
            "title": "Reporting passives and the causative",
            "instructions": "Complete the second sentence so it means the same as the first. Write only the missing words.",
            "items": [
                {"q": "People believe that the painting is a fake.\nThe painting ______ a fake.", "a": ["is believed to be"]},
                {"q": "People say that he earned millions in the 1990s.\nHe ______ millions in the 1990s.", "a": ["is said to have earned", "is said to have made"]},
                {"q": "Reports suggest that the company is planning layoffs.\nThe company ______ planning layoffs.", "a": ["is reported to be", "is said to be", "is thought to be", "is believed to be"]},
                {"q": "They think the thieves escaped through the window.\nThe thieves ______ through the window.", "a": ["are thought to have escaped", "are believed to have escaped"]},
                {"q": "A mechanic is repairing my car at the moment.\nI'm ______ at the moment.", "a": ["having my car repaired", "getting my car repaired"]},
                {"q": "I persuaded my brother to help me move.\nI got ______ me move.", "a": ["my brother to help"]},
                {"q": "It is expected that prices will rise.\nPrices ______ rise.", "a": ["are expected to"]},
                {"q": "Someone stole her bag on the train.\nShe ______ on the train.", "a": ["had her bag stolen", "got her bag stolen"]},
                {"q": "The windows need cleaning.\nThe windows need ______.", "a": ["to be cleaned"]},
                {"q": "It was alleged that the minister had lied.\nThe minister ______ lied.", "a": ["was alleged to have"]},
            ],
        }),
        ("md", """
### Your turn (2)
Find a news article (BBC, Guardian, Reuters) and copy **three** sentences that use reporting passives.
Then write 3 sentences about rumours in your city/industry: *X is said to be..., Y is thought to have...*
"""),
        # ------------------------------------------------------------------ 3
        ("md", """
---
## 3. Participle clauses

Participle clauses replace a full clause (with *because, when, after, which, who*...) to make sentences **shorter
and more elegant**. The subject must be the same as the main clause!

| Type | Replaces | Example |
|---|---|---|
| Present participle (-ing) | active; cause or simultaneous action | **Feeling** tired, I went to bed early. (= Because I felt...) |
| Negative | | **Not knowing** what to say, she stayed silent. |
| Perfect participle | an action **before** the main one | **Having finished** the report, she went home. |
| Perfect passive | passive action before | **Having been warned** twice, he knew the risks. |
| Past participle | passive | **Built** in 1890, the bridge is still in use. |
| Reduced relative (active) | *who/which* + active verb | The woman **sitting** next to me was a doctor. |
| Reduced relative (passive) | *who/which* + passive verb | The houses **destroyed** in the fire... |
| After conjunctions | *when, while, after, before, since, once* | **While waiting** for the bus, I read the news. |

> **Dangling participle** (a common error): *~~Walking into the room, the lights went out.~~* - the lights weren't walking!
> -> *Walking into the room, **I** noticed the lights go out.*
"""),
        ("ex", {
            "id": "g2_participles",
            "title": "Participle clauses",
            "instructions": "Complete the second sentence using a participle clause. Write only the missing words.",
            "items": [
                {"q": "Because I didn't know anyone, I left early.\n______ anyone, I left early.", "a": ["not knowing"]},
                {"q": "After she had finished the report, she went home.\n______ the report, she went home.", "a": ["having finished", "after finishing", "after having finished"]},
                {"q": "The castle, which was built in the 12th century, attracts thousands of visitors.\n______ in the 12th century, the castle attracts thousands of visitors.", "a": ["built"]},
                {"q": "Anyone who wishes to attend must register by Friday.\nAnyone ______ to attend must register by Friday.", "a": ["wishing"]},
                {"q": "As he had been warned twice, he knew the risks.\n______ twice, he knew the risks.", "a": ["having been warned"]},
                {"q": "The people who were injured in the accident were taken to hospital.\nThe people ______ in the accident were taken to hospital.", "a": ["injured"]},
                {"q": "While I was walking home, I saw an old friend.\n______ home, I saw an old friend.", "a": ["walking", "while walking"]},
                {"q": "Since I had never been to Asia before, I found the trip overwhelming.\n______ to Asia before, I found the trip overwhelming.", "a": ["never having been", "not having been", "having never been"]},
            ],
        }),
        # ------------------------------------------------------------------ 4
        ("md", """
---
## 4. Emphasis, substitution and ellipsis

Advanced speakers **avoid repeating words**, and add emphasis with grammar rather than just "very".

| Tool | Example |
|---|---|
| Emphatic *do / does / did* | I **do** like it, honestly! / She **did** call - you just didn't hear. |
| *so / not* replacing a clause | "Is it raining?" "I **think so** / I **hope not** / I'm **afraid so** / I **don't think so**." |
| *if so / if not* | Do you have a receipt? **If so**, we can refund you. |
| *so / neither / nor* + auxiliary | "I love jazz." "**So do I**." / "I can't swim." "**Neither can I**." |
| *one / ones* | These shoes are too small. Do you have any bigger **ones**? |
| *do so* (formal) | He was asked to resign but refused to **do so**. |
| Ellipsis after *to* | "Would you like to come?" "I'd love **to**." |
| Intensifiers | no evidence **whatsoever**, not **at all**, **by far** the best, the **very** same day, **such** a mess |
"""),
        ("ex", {
            "id": "g2_emphasis",
            "title": "Emphasis, substitution and ellipsis",
            "instructions": "Write ONE word in each gap.",
            "items": [
                {"q": "\"Will it rain tomorrow?\" \"I hope ______.\" (You want a sunny day.)", "a": ["not"]},
                {"q": "\"Is the shop closed already?\" \"I'm afraid ______.\"", "a": ["so"]},
                {"q": "I don't like horror films, and ______ does my sister.", "a": ["neither", "nor"]},
                {"q": "You say I never help, but I ______ help! I did the dishes yesterday.", "a": ["do"]},
                {"q": "Some candidates may already have experience. If ______, they will start on a higher salary.", "a": ["so"]},
                {"q": "These shoes are too small. Do you have any bigger ______?", "a": ["ones"]},
                {"q": "I asked him to apologise, but he refused to do ______.", "a": ["so"]},
                {"q": "There is no evidence ______ to support this claim.", "a": ["whatsoever"]},
                {"q": "\"Would you like to join us for dinner?\" \"I'd love ______!\"", "a": ["to"]},
                {"q": "She is ______ far the best candidate we've interviewed.", "a": ["by"]},
            ],
        }),
        # ------------------------------------------------------------------ 5
        ("md", """
---
## 5. The subjunctive and formal structures

After verbs and adjectives of **demand, suggestion or importance**, formal English uses the **base form** of the verb
for all persons (no *-s*, no past). British English often uses *should* + infinitive instead.

| Trigger | Example |
|---|---|
| *suggest, recommend, insist, demand, propose, request, ask* **that** | The doctor recommended **that he rest**. (NOT *rests*) |
| *It is essential / vital / crucial / important / imperative that* | It is vital **that every employee be** informed. |
| Negative: **not** + base form | They insisted **that she not travel** alone. |
| BrE alternative | They insisted that she **should not travel** alone. |
| Fixed expressions | **Be that as it may**, ... / **Come what may**, ... / **So be it**. / **If need be**, ... |

> Spanish speakers: this works like *"Recomendó que descansara"* - but in English the verb doesn't change at all: **rest**.
> Also: *suggest* can't take an object + infinitive: ~~*I suggested him to go*~~ -> *I suggested **that he go / (should) go*** or *I suggested **going***.
"""),
        ("ex", {
            "id": "g2_subjunctive",
            "title": "Subjunctive and fixed expressions",
            "instructions": "Put the verb in brackets into the correct form, or complete the fixed expression with ONE word.",
            "items": [
                {"q": "The doctor recommended that he ______ (rest) for two weeks.", "a": ["rest", "should rest"]},
                {"q": "It is essential that every employee ______ (be) informed before Monday.", "a": ["be", "should be", "is"],
                 "why": "Formal: 'be'. BrE: 'should be'. ('is' is common in informal BrE but less formal.)"},
                {"q": "They insisted that she ______ (not / travel) alone.", "a": ["not travel", "should not travel", "shouldn't travel"]},
                {"q": "The committee proposed that the rule ______ (change).", "a": ["be changed", "should be changed"]},
                {"q": "It's vital that he ______ (take) his medication every day.", "a": ["take", "should take"]},
                {"q": "I suggest that she ______ (apply) for the position.", "a": ["apply", "should apply"]},
                {"q": "______ that as it may, we still need a decision by Friday.", "a": ["be"]},
                {"q": "We'll finish the project on time, come what ______.", "a": ["may"]},
            ],
        }),
        ("md", """
---
## 6. Mixed review: error correction
Each sentence has **one** mistake. Rewrite it correctly (open answers - compare with the model).
"""),
        ("ex", {
            "id": "g2_errors",
            "title": "Error correction (Grammar II)",
            "type": "open",
            "instructions": "Rewrite each sentence correctly.",
            "items": [
                {"q": "You should of told me earlier.", "a": ["You should have told me earlier."]},
                {"q": "He is said to be born in Mexico.", "a": ["He is said to have been born in Mexico."]},
                {"q": "I suggested him to take the train.", "a": ["I suggested that he take the train.", "I suggested that he should take the train.", "I suggested he take the train.", "I suggested taking the train."]},
                {"q": "I cut my hair yesterday at the new salon.", "a": ["I had my hair cut yesterday at the new salon.", "I got my hair cut yesterday at the new salon."]},
                {"q": "Having finished dinner, the dishes were washed.", "a": ["Having finished dinner, we washed the dishes.", "Having finished dinner, I washed the dishes."]},
                {"q": "She can't have saw the message.", "a": ["She can't have seen the message."]},
                {"q": "It is essential that he arrives on time.", "a": ["It is essential that he arrive on time.", "It is essential that he should arrive on time."]},
                {"q": "The car needs to repair.", "a": ["The car needs repairing.", "The car needs to be repaired."]},
            ],
        }),
        ("md", """
---
### Before you leave this notebook
* 85%+ on every set? Go to Notebook 03. Otherwise schedule a redo.
* Run `review_mistakes()` in Notebook 09 at the end of each week.
* Extra practice: *Advanced Grammar in Use* (Hewings) units on modals, passives and participle clauses;
  *Destination C1 & C2* (Mann & Taylore-Knowles) grammar units.
"""),
        ("code", """
# log_study(60, "grammar", "NB02 - past modals")
"""),
    ],
}
