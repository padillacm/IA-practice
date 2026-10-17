NOTEBOOK = {
    "file": "05_Word_Formation_Paraphrasing.ipynb",
    "title": "05 - Vocabulary III: Word Formation, Paraphrasing and Word Precision",
    "cells": [
        ("md", """
C1 speakers have **flexible vocabulary**: from one root they can produce the noun, the adjective, the adverb and
the opposite (*decide -> decision, decisive, decisively, indecisive*), and they can **say the same idea in several ways**.
That flexibility is what lets you keep talking when a word doesn't come - you just rephrase.

This notebook trains three things:
1. **Word formation** (prefixes and suffixes)
2. **Paraphrasing** with "key word transformations" - the best grammar + vocabulary workout that exists
3. **Precision**: confusing words and false friends for Spanish speakers
"""),
        ("md", """
## 1. Word formation toolkit

### Suffixes

| To make... | Suffixes | Examples |
|---|---|---|
| **nouns** | -tion/-sion, -ment, -ness, -ity, -ance/-ence, -ship, -hood, -ism, -er/-or/-ist, -al | decision, agreement, awareness, clarity, reliance, leadership, childhood, criticism, defender, refusal |
| **adjectives** | -ive, -ous, -al, -able/-ible, -ful, -less, -ic, -ent/-ant, -y | decisive, dangerous, economical, reliable, thoughtful, pointless, scientific, dependent, risky |
| **verbs** | -ise/-ize, -en, -ify | modernise, strengthen, simplify |
| **adverbs** | -ly (-ally after -ic) | consistently, dramatically |

### Prefixes

| Prefix | Meaning | Examples |
|---|---|---|
| un-, in-, im- (before p/m/b), il- (before l), ir- (before r), dis-, non- | not / opposite | unexpected, inaccurate, impossible, illegal, irrelevant, disrespectful, non-profit |
| mis- | wrongly | misunderstand, mislead, mismanage |
| over- / under- | too much / too little | overestimate, underpaid |
| re- | again | reconsider, rebuild |
| out- | more than / beyond | outnumber, outgrow |
| counter- | against | counterproductive |

**Spelling watch:** clear -> **clarity**; able -> **ability**; simple -> **simplify**; explain -> **explanation**;
pronounce -> **pronunciation**; maintain -> **maintenance**; deep -> **depth**; long -> **length**; strong -> **strength**.
"""),
        ("ex", {
            "id": "v5_word_formation",
            "title": "Word formation",
            "instructions": "Use the word in CAPITALS to form a word that fits the gap.",
            "items": [
                {"q": "The new policy has been ______ criticised by experts. (WIDE)", "a": ["widely"]},
                {"q": "There is growing ______ that the system needs reform. (RECOGNISE)", "a": ["recognition"]},
                {"q": "His ______ to compromise caused the talks to collapse. (WILLING)", "a": ["unwillingness"]},
                {"q": "The advertisement was deliberately ______. (LEAD)", "a": ["misleading"]},
                {"q": "We were impressed by the ______ of her argument. (CLEAR)", "a": ["clarity"]},
                {"q": "The results are ______ with previous research. (CONSIST)", "a": ["consistent", "inconsistent"]},
                {"q": "It was a completely ______ decision; nobody saw it coming. (EXPECT)", "a": ["unexpected"]},
                {"q": "The company faces ______ competition from abroad. (INCREASE)", "a": ["increasing", "increased"]},
                {"q": "He apologised for his ______ behaviour at the meeting. (RESPECT)", "a": ["disrespectful"]},
                {"q": "Some of the paintings in the collection are ______. (REPLACE)", "a": ["irreplaceable"]},
                {"q": "Poor ______ of resources led to the project's failure. (MANAGE)", "a": ["management", "mismanagement"]},
                {"q": "The ______ of the new bridge took three years. (CONSTRUCT)", "a": ["construction"]},
                {"q": "She has a remarkable ______ to stay calm under pressure. (ABLE)", "a": ["ability"]},
                {"q": "Many young people feel ______ with politics. (ILLUSION)", "a": ["disillusioned"]},
                {"q": "The data was ______ interpreted, which led to the wrong conclusions. (CORRECT)", "a": ["incorrectly"]},
                {"q": "Economic ______ has improved over the last decade. (STABLE)", "a": ["stability"]},
                {"q": "The two proposals are ______ different. (FUNDAMENTAL)", "a": ["fundamentally"]},
                {"q": "His ______ comments offended several colleagues. (THINK)", "a": ["thoughtless", "unthinking"]},
                {"q": "The government aims to ______ the tax system. (SIMPLE)", "a": ["simplify"]},
                {"q": "There was a clear ______ of opinion among the experts. (DIVIDE)", "a": ["division"]},
            ],
        }),
        # ------------------------------------------------------------------ 2
        ("md", """
### Word families in context
One root, several forms: choose the right one for each gap in this short text.

> *Our supplier used to be very (1) ______ (RELY), but recently its (2) ______ (RELY) has become a problem. We can't
> afford to be so (3) ______ (DEPEND) on one company, so we need to reduce our (4) ______ (DEPEND). The
> (5) ______ (DECIDE) to look for a second supplier was not easy, and some managers were (6) ______ (DECIDE) for weeks.
> In the end, the director acted (7) ______ (DECIDE), and the change should (8) ______ (STRONG) our position.*
"""),
        ("ex", {
            "id": "v5_word_families",
            "title": "Word families in context",
            "instructions": "Write the correct form of the word in CAPITALS for each numbered gap in the text above.",
            "items": [
                {"q": "(1) very ______ (RELY)", "a": ["reliable"]},
                {"q": "(2) its ______ (RELY) has become a problem", "a": ["reliability", "unreliability"]},
                {"q": "(3) so ______ (DEPEND) on one company", "a": ["dependent", "reliant"]},
                {"q": "(4) reduce our ______ (DEPEND)", "a": ["dependence", "dependency"]},
                {"q": "(5) The ______ (DECIDE) to look for a second supplier", "a": ["decision"]},
                {"q": "(6) some managers were ______ (DECIDE) for weeks", "a": ["undecided", "indecisive"]},
                {"q": "(7) the director acted ______ (DECIDE)", "a": ["decisively"]},
                {"q": "(8) should ______ (STRONG) our position", "a": ["strengthen"]},
            ],
        }),
        ("md", """
---
## 2. Paraphrasing: key word transformations

Complete the second sentence so it means the same as the first, **using the word in CAPITALS without changing it**.
Use **3-6 words** including the key word. This format (from the Cambridge C1 exam) is used here because it trains exactly
the skill you need in real conversation: **finding another way to say the same thing**.

Strategy:
1. What's the key word's grammar? (*SUCH* -> *such a/an + adj + noun*; *WISH* -> past perfect for regrets...)
2. What changes: tense, passive, a phrasal verb, a fixed expression?
3. Check that the meaning is identical and nothing is missing.
"""),
        ("ex", {
            "id": "v5_transformations",
            "title": "Key word transformations",
            "instructions": "Write only the missing words (3-6 words, including the word in CAPITALS).",
            "items": [
                {"q": "I'm sure she didn't take the money. CAN'T\nShe ______ the money.", "a": ["can't have taken", "cannot have taken"]},
                {"q": "It was wrong of you to shout at him. SHOULD\nYou ______ at him.", "a": ["should not have shouted", "shouldn't have shouted"]},
                {"q": "I regret not studying harder at university. WISH\nI ______ harder at university.", "a": ["wish I had studied", "wish I'd studied", "wish that I had studied"]},
                {"q": "The concert was cancelled because of the storm. CALLED\nThe concert ______ because of the storm.", "a": ["was called off", "had to be called off"]},
                {"q": "She was the only one who noticed the mistake. APART\nNobody ______ the mistake.", "a": ["apart from her noticed"]},
                {"q": "I found it difficult to understand his accent. DIFFICULTY\nI ______ his accent.", "a": ["had difficulty understanding", "had difficulty in understanding", "had great difficulty understanding", "had some difficulty understanding"]},
                {"q": "It's possible that they missed the train. MAY\nThey ______ the train.", "a": ["may have missed"]},
                {"q": "People say that the castle is haunted. SAID\nThe castle ______ haunted.", "a": ["is said to be"]},
                {"q": "He didn't realise how serious the situation was. LITTLE\n______ how serious the situation was.", "a": ["little did he realise", "little did he realize", "little did he know"]},
                {"q": "\"Don't forget to lock the door,\" she told me. REMINDED\nShe ______ the door.", "a": ["reminded me to lock"]},
                {"q": "The film was so boring that I fell asleep. SUCH\nIt ______ that I fell asleep.", "a": ["was such a boring film"]},
                {"q": "I haven't seen Mark for ages. SINCE\nIt's ______ Mark.", "a": ["been ages since I saw", "been ages since I last saw", "been ages since I've seen", "been ages since I have seen"]},
                {"q": "We postponed the meeting until next week. PUT\nThe meeting ______ until next week.", "a": ["was put off", "has been put off", "was put back", "has been put back"]},
                {"q": "Whatever you say, I won't change my mind. MATTER\nNo ______, I won't change my mind.", "a": ["matter what you say"]},
                {"q": "She is likely to win the election. CHANCES\nThe ______ win the election.", "a": ["chances are that she will", "chances are she will", "chances are that she'll", "chances are she'll"]},
                {"q": "I only realised my mistake when I got home. UNTIL\nIt ______ I got home that I realised my mistake.", "a": ["was not until", "wasn't until"]},
                {"q": "They will make the final decision next week. MADE\nThe final decision ______ next week.", "a": ["will be made", "is going to be made", "is to be made", "is being made"]},
                {"q": "Tom is not as experienced as Sarah. LESS\nTom ______ Sarah.", "a": ["is less experienced than", "has less experience than"]},
                {"q": "You must not tell anyone about this under any circumstances. ACCOUNT\nOn ______ anyone about this.", "a": ["no account must you tell", "no account should you tell", "no account are you to tell"]},
                {"q": "I'd prefer you not to smoke in here. RATHER\nI'd ______ in here.", "a": ["rather you did not smoke", "rather you didn't smoke"]},
            ],
        }),
        # ------------------------------------------------------------------ 3
        ("md", """
---
## 3. Precision: confusables and false friends

| Word | Meaning | Spanish trap |
|---|---|---|
| **actually** | in fact, really | NOT *actualmente* -> **currently / at the moment** |
| **eventually** | in the end, after a long time | NOT *eventualmente* -> **possibly / occasionally** |
| **assist** | help | *asistir a* -> **attend** |
| **embarrassed** | awkward, self-conscious (not *ashamed*) | *embarazada* -> **pregnant** |
| **sensible** | reasonable, practical | *sensible* -> **sensitive** |
| **realise** | understand, become aware | *realizar* -> **carry out, do, make** |
| **pretend** | act as if something is true | *pretender* -> **intend, aim, try** |
| **library** | biblioteca | *librería* -> **bookshop / bookstore** |
| **economic / economical** | related to the economy / not wasteful, cheap to run | |
| **affect / effect** | verb: influence / noun: result (verb *effect* = bring about) | |
| **disinterested / uninterested** | impartial / not interested | |
| **fewer / less** | countable / uncountable | |
"""),
        ("ex", {
            "id": "v5_confusables",
            "title": "Confusable words and false friends",
            "instructions": "Choose the correct word. Type the letter or the word.",
            "items": [
                {"q": "The new law will ___ thousands of workers.", "options": ["affect", "effect", "infect"]},
                {"q": "Buying in bulk is more ___.", "options": ["economical", "economic", "economics"]},
                {"q": "She gave me some very ___ advice about money.", "options": ["sensible", "sensitive", "sensational"]},
                {"q": "He's very ___ to criticism; he takes everything personally.", "options": ["sensitive", "sensible", "sensory"]},
                {"q": "___, we have 50 employees, but we plan to hire more next year.", "options": ["Currently", "Eventually", "Occasionally"]},
                {"q": "After years of trying, she ___ succeeded.", "options": ["eventually", "possibly", "presently"]},
                {"q": "More than 300 people ___ the conference.", "options": ["attended", "assisted", "assisted to"]},
                {"q": "I felt so ___ when I forgot her name.", "options": ["embarrassed", "pregnant", "embarrassing"]},
                {"q": "We need to ___ the problem before it gets worse.", "options": ["address", "direct", "adress"]},
                {"q": "The judge must be completely ___: she can have no personal interest in the case.", "options": ["disinterested", "uninterested", "unconcerned"]},
                {"q": "There were ___ people at the meeting than we expected.", "options": ["fewer", "less", "lesser"]},
                {"q": "It's only a ___ of time before they announce it.", "options": ["matter", "case", "subject"]},
                {"q": "The researchers ___ a series of experiments.", "options": ["carried out", "realised", "made up"]},
                {"q": "What do you ___ to do after you graduate?", "options": ["intend", "pretend", "attend"]},
                {"q": "I bought this novel at the ___ on the corner.", "options": ["bookshop", "library", "librery"]},
            ],
        }),
        ("md", """
---
### Your turn: paraphrase aloud
Pick any paragraph from a news article. Read one sentence, **look away**, and say it in a different way
(change the structure, use a synonym, use a passive, a cleft, a phrasal verb...). Do 10 sentences a day this week.
This is one of the most effective C1 speaking exercises there is.
"""),
        ("code", """
# log_study(45, "vocabulary", "NB05 key word transformations")
"""),
    ],
}
