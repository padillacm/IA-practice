NOTEBOOK = {
    "file": "01b_Accuracy_Core_Spanish_Speakers.ipynb",
    "title": "01b - Accuracy Core: The Errors Spanish Speakers Keep Making",
    "cells": [
        ("md", """
The CEFR describes C1 accuracy like this: *"consistently maintains a high degree of grammatical accuracy; errors are rare
and difficult to spot."* For Spanish speakers, the errors that stay the longest are **not** in advanced structures like
inversion. They're in small, high-frequency things: **articles, prepositions, tenses, missing subjects, word order and verb
patterns**. These errors are "fossilised": you know the rule, but under pressure your Spanish takes over.

That's why this notebook comes **first** (weeks 1-3, together with Notebook 01). Every section has an explanation, a
gap-fill, and error correction. It ends with a proofreading task on a real email.

**The secret for fossilised errors:** noticing + lots of correct repetition. After each section, say the correct
sentences aloud 3 times, and add your personal errors to your review bank with `log_mistake()`.
"""),
        # ------------------------------------------------------------------ 1
        ("md", """
---
## 1. Articles (a / an / the / no article)

| Rule | Correct | Spanish-influenced error |
|---|---|---|
| **General** statements with plural or uncountable nouns: **no article** | **Life** is hard. **People** are strange. **Unemployment** has risen. | ~~The life is hard.~~ ~~The people are strange.~~ |
| **Specific** things (we know which): **the** | **The people** who live next door are strange. | |
| Jobs: **a / an** | She's **an** engineer. | ~~She's engineer.~~ |
| *next / last* + time: no article | See you **next week**. I saw him **last Monday**. | ~~the next week~~ (= the following week, in a story) |
| Institutions for their purpose: no article | go to **school / work / bed / hospital / prison** | ~~go to the work~~ |
| Meals, languages, sports, most countries | have **lunch**, speak **English**, play **tennis**, live in **Spain** | ~~the English~~ (language) / ~~the Spain~~ |
| Countries with *States, Kingdom, Republic*, plurals | **the** USA, **the** UK, **the** Netherlands, **the** Philippines | |
| Superlatives, unique things, instruments | **the** best, **the** sun, **the** internet, play **the** guitar | |
| *most* = the majority: no article | **Most people** agree. | ~~The most people agree.~~ |

> **Quick test:** in Spanish you'd say *"la gente"*, *"el dinero"*, *"los jóvenes"* when you're talking in general.
> In English, general = **no article**: *people, money, young people*.
"""),
        ("ex", {
            "id": "a1_articles",
            "title": "Articles",
            "instructions": "Write a, an, the, or - (dash) if no article is needed.",
            "items": [
                {"q": "______ money doesn't bring happiness.", "a": ["-"], "why": "General statement, uncountable noun: no article."},
                {"q": "Can you give me back ______ money I lent you?", "a": ["the"], "why": "Specific money (the money I lent you)."},
                {"q": "My sister is ______ architect.", "a": ["an"]},
                {"q": "I'll call you ______ next week.", "a": ["-"]},
                {"q": "______ most people I know work from home at least one day a week.", "a": ["-"]},
                {"q": "He was taken to ______ hospital after the accident.", "a": ["-", "the"],
                 "why": "BrE: to hospital (as a patient). AmE: to the hospital. Both accepted."},
                {"q": "She moved to ______ United States in 2019.", "a": ["the"]},
                {"q": "______ young people today are more aware of mental health.", "a": ["-"]},
                {"q": "It's ______ best book I've read this year.", "a": ["the"]},
                {"q": "We had ______ lunch in a small café near the office.", "a": ["-"]},
                {"q": "I'd like to work for ______ international company.", "a": ["an"]},
                {"q": "______ inflation is the main concern for voters.", "a": ["-"]},
            ],
        }),
        # ------------------------------------------------------------------ 2
        ("md", """
---
## 2. Dependent prepositions and verb patterns

Prepositions are learned **with** the word, as a chunk. These are the ones Spanish speakers get wrong most often:

| Correct | Typical error (from Spanish) |
|---|---|
| depend **on** | ~~depend of~~ (*depender de*) |
| married **to**, get married **to** | ~~married with~~ (*casado con*) |
| arrive **in** a city / **at** a place | ~~arrive to~~ (*llegar a*) |
| discuss **sth** (no preposition) | ~~discuss about~~ |
| explain **sth to sb** | ~~explain me the problem~~ |
| **I agree** (verb) | ~~I am agree~~ (*estoy de acuerdo*) |
| interested **in**, good **at**, responsible **for**, afraid **of**, different **from/to** | ~~interested on~~, ~~good in~~ |
| think **about/of**, dream **of/about** | ~~think in~~ (*pensar en*) |
| consist **of**, comment **on**, focus **on**, insist **on**, rely **on** | ~~consist in~~ (in = formal "be essentially") |
| make sb **do** (no *to*) / let sb **do** | ~~made me to wait~~ |
| look forward to **-ing**, be used to **-ing** (*to* is a preposition here!) | ~~look forward to hear~~ |
| suggest **-ing** / suggest **that...** | ~~suggest him to go~~ |
| an increase **in** prices / an increase **of** 10% | ~~increase of prices~~ |
| the reason **for** / the impact **on** / access **to** | ~~the reason of~~ |
"""),
        ("ex", {
            "id": "a1_prepositions",
            "title": "Dependent prepositions",
            "instructions": "Write ONE word in each gap. Type - if no word is needed.",
            "items": [
                {"q": "Whether we travel or not depends ______ the weather.", "a": ["on", "upon"]},
                {"q": "She's been married ______ a Canadian for ten years.", "a": ["to"]},
                {"q": "We arrived ______ Madrid late at night.", "a": ["in"]},
                {"q": "We need to discuss ______ the budget tomorrow.", "a": ["-"]},
                {"q": "Could you explain the problem ______ me?", "a": ["to"]},
                {"q": "He's very good ______ solving problems under pressure.", "a": ["at"]},
                {"q": "I'm thinking ______ changing jobs.", "a": ["about", "of"]},
                {"q": "The course consists ______ twelve modules.", "a": ["of"]},
                {"q": "There has been a sharp increase ______ house prices.", "a": ["in"]},
                {"q": "What was the reason ______ the delay?", "a": ["for", "behind"]},
                {"q": "The new policy will have a big impact ______ small businesses.", "a": ["on", "upon"]},
                {"q": "Everyone should have access ______ clean water.", "a": ["to"]},
                {"q": "Who's responsible ______ this project?", "a": ["for"]},
                {"q": "Let's focus ______ the main issue.", "a": ["on", "upon"]},
            ],
        }),
        ("ex", {
            "id": "a1_verb_patterns",
            "title": "Verb patterns",
            "instructions": "Put the verb in brackets into the correct form (infinitive, bare infinitive or -ing).",
            "items": [
                {"q": "I look forward to ______ (hear) from you.", "a": ["hearing"]},
                {"q": "My boss made me ______ (redo) the whole report.", "a": ["redo"]},
                {"q": "I'm not used to ______ (work) such long hours.", "a": ["working"]},
                {"q": "She suggested ______ (take) a short break.", "a": ["taking"]},
                {"q": "They let us ______ (leave) early on Friday.", "a": ["leave"]},
                {"q": "I stopped ______ (smoke) five years ago.", "a": ["smoking"], "why": "stop + -ing = quit the activity."},
                {"q": "On the way home, I stopped ______ (buy) some bread.", "a": ["to buy"], "why": "stop + to = stop in order to do something."},
                {"q": "Remember ______ (lock) the door when you leave.", "a": ["to lock"], "why": "remember + to = don't forget (future)."},
                {"q": "I remember ______ (lock) the door - I'm sure it's locked.", "a": ["locking"], "why": "remember + -ing = memory of the past."},
                {"q": "If the printer doesn't work, try ______ (turn) it off and on again.", "a": ["turning"], "why": "try + -ing = experiment."},
                {"q": "I tried ______ (open) the window, but it was stuck.", "a": ["to open"], "why": "try + to = make an effort."},
                {"q": "Would you mind ______ (send) me the file again?", "a": ["sending"]},
                {"q": "We can't afford ______ (lose) this client.", "a": ["to lose"]},
                {"q": "It's worth ______ (check) the contract before signing.", "a": ["checking"]},
            ],
        }),
        # ------------------------------------------------------------------ 3
        ("md", """
---
## 3. Present perfect vs past simple, and *for / since*

| Use | Tense | Example |
|---|---|---|
| Finished time (*yesterday, in 2019, last week, ago, when I was...*) | **past simple** | I **saw** him yesterday. (~~I have seen him yesterday~~) |
| From the past **until now** (+ *for / since / how long*) | **present perfect** (simple or continuous) | I **have lived / have been living** here since 2015. (~~I live here since 2015~~) |
| Experience, no time given | **present perfect** | **Have** you ever **been** to Japan? |
| Recent news with present result | **present perfect** (BrE) | I**'ve lost** my keys. (AmE also: *I lost my keys.*) |

**for** + a period (*for three years*) · **since** + a starting point (*since 2015, since I was a child*) ·
**How long have you...?** (~~How long do you...?~~ = *¿Cuánto tiempo hace que...?*)
"""),
        ("ex", {
            "id": "a1_tenses",
            "title": "Present perfect or past simple?",
            "instructions": "Put the verb in brackets into the correct tense, or write for / since.",
            "items": [
                {"q": "I ______ (work) here since 2020.", "a": ["have worked", "have been working"]},
                {"q": "I ______ (see) him yesterday at the station.", "a": ["saw"]},
                {"q": "How long ______ (you / know) your best friend?", "a": ["have you known"]},
                {"q": "She ______ (move) to London three years ago.", "a": ["moved"]},
                {"q": "______ you ever ______ (be) to Mexico? (write both words: e.g. 'have ... been')", "a": ["have been", "have ... been", "have...been"]},
                {"q": "We've been waiting ______ forty minutes.", "a": ["for"]},
                {"q": "I haven't eaten anything ______ breakfast.", "a": ["since"]},
                {"q": "When ______ (you / start) learning English?", "a": ["did you start"]},
                {"q": "They ______ (be) married for twenty years - they're celebrating next week.", "a": ["have been"]},
                {"q": "I ______ (finish) the report last night, so you can read it now.", "a": ["finished"]},
            ],
        }),
        # ------------------------------------------------------------------ 4
        ("md", """
---
## 4. Subjects and word order

**English sentences always need a subject.** Spanish drops it; English uses *it* or *there*:

| Spanish | ~~Error~~ | Correct |
|---|---|---|
| Es importante llegar temprano. | ~~Is important to arrive early.~~ | **It**'s important to arrive early. |
| Hay muchos problemas. | ~~Are many problems.~~ / ~~Have many problems.~~ | **There** are many problems. |
| Está lloviendo. | ~~Is raining.~~ | **It**'s raining. |
| Me gusta. | ~~Like me.~~ | I like **it**. |

**Word order**
* Verb + object stay **together**: *I like football **very much*** (~~I like very much football~~).
* Frequency adverbs go **before** the main verb, **after** *be*: *I **always** forget*, *She's **never** late* (~~Always I forget~~).
* **Indirect questions** use statement order: *Can you tell me where **the station is**?* (~~where is the station~~).
* Adjectives go **before** nouns: *an **interesting** idea*.

**What vs that:** *what* = "the thing that". After *all, everything, something, the thing*, use **that** (or nothing):
*All (that) I need* (~~All what I need~~); *Everything (that) he said* (~~everything what~~).
"""),
        ("ex", {
            "id": "a1_word_order",
            "title": "Subjects, word order and 'what/that'",
            "type": "open",
            "instructions": "Each sentence has ONE mistake. Rewrite it correctly.",
            "items": [
                {"q": "Is important to check the figures before the meeting.", "a": ["It is important to check the figures before the meeting."]},
                {"q": "Are many reasons why the project failed.", "a": ["There are many reasons why the project failed."]},
                {"q": "I like very much this city.", "a": ["I like this city very much.", "I really like this city."]},
                {"q": "Can you tell me where is the meeting room?", "a": ["Can you tell me where the meeting room is?"]},
                {"q": "Always I forget my password.", "a": ["I always forget my password."]},
                {"q": "All what I need is a bit more time.", "a": ["All I need is a bit more time.", "All that I need is a bit more time."]},
                {"q": "I don't know what time does the train leave.", "a": ["I don't know what time the train leaves."]},
                {"q": "She is never on time, is a real problem.", "a": ["She is never on time, which is a real problem.", "She is never on time. It's a real problem."]},
                {"q": "I am agree with you completely.", "a": ["I agree with you completely.", "I completely agree with you."]},
                {"q": "Everything what he said was true.", "a": ["Everything he said was true.", "Everything that he said was true."]},
            ],
        }),
        # ------------------------------------------------------------------ 5
        ("md", """
---
## 5. Proofreading: a real email

This email was written by a B2 Spanish speaker. It has **8 errors** of the types in this notebook.
Rewrite the whole email correctly in the cell below, then compare with the model answer.
"""),
        ("md", """
> Hi Laura,
>
> I write you to explain about the delay in the project. As you know, the success of project depends of the supplier,
> and they have sent the materials only yesterday. Is very frustrating, because I have worked on this since three weeks.
> I suggest to have a quick call tomorrow to discuss about the next steps. Can you tell me what time is good for you?
>
> Best,
> Carlos
"""),
        ("ex", {
            "id": "a1_email",
            "title": "Proofread the email",
            "type": "open",
            "instructions": "Write the corrected email as ONE answer (item 1). Then list the 8 corrections in item 2 if you like.",
            "items": [
                {"q": "The corrected email",
                 "a": ["Hi Laura, I'm writing to explain the delay in the project. As you know, the success of the project depends on the supplier, and they only sent the materials yesterday. It's very frustrating, because I've been working on this for three weeks. I suggest having a quick call tomorrow to discuss the next steps. Can you tell me what time is good for you? Best, Carlos"]},
                {"q": "The 8 corrections",
                 "a": ["I'm writing (not I write you) / explain the delay (no 'about') / the success of the project / depends on / only sent (past simple with yesterday) / It's very frustrating / I've been working ... for three weeks / suggest having / discuss the next steps (no 'about')"]},
            ],
        }),
        ("md", """
---
### Your turn: find YOUR fossilised errors

1. Record yourself talking for 2 minutes about your job or studies (`random_prompt("workplace")` in Notebook 07).
2. Transcribe it and check it with this list: articles, prepositions, tenses, subjects, word order.
3. For each error, run `log_mistake("what I said", "correct version", "why")` - it goes into your review bank.

**AI feedback prompt** (paste with your transcript or a piece of your writing):
```
I'm a Spanish speaker at B2 level. Check this text ONLY for: articles, prepositions, present perfect vs past simple,
missing subjects (it/there), word order and verb patterns (-ing vs to). List each error as "wrong -> correct (rule)".
Don't rewrite the whole text and don't comment on anything else.
```
"""),
        ("code", """
# log_mistake("I have seen him yesterday", "I saw him yesterday", "finished time -> past simple")
# log_study(45, "grammar", "NB01b articles + prepositions")
"""),
    ],
}
