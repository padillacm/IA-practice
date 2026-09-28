NOTEBOOK = {
    "file": "06_Listening_Lab.ipynb",
    "title": "06 - Listening Lab: Connected Speech, Dictation, Inference and Real-World Listening",
    "cells": [
        ("md", """
### Why listening feels hard at B2
You probably know most of the words you hear - but in fast native speech they **don't sound like the words you learnt**.
*What do you want to do?* becomes /ˈwɒdʒə ˈwɒnə du/ ("whaddaya wanna do"). The problem is usually **perception**, not vocabulary.
C1 listening also means catching **attitude, irony and what is implied but not said**.

### The plan: two kinds of listening, every day

| | Intensive (20-30 min/day) | Extensive (30-60 min/day) |
|---|---|---|
| Goal | train your ear to decode fast speech | build automaticity, vocabulary and stamina |
| Material | short clips (1-3 min), slightly above your level | podcasts / series you **enjoy**, ~80-90% understood |
| How | dictation, transcripts, repeat, shadow | just listen, no stopping, subtitles in English or none |
| Tools here | sections 1-3 of this notebook | section 4 worksheet + `RESOURCES.md` |

### The 5-pass method for intensive listening (use it with any clip)
1. **Gist:** listen once, no pausing. What's it about? Who? What's their attitude?
2. **Detail:** listen again, pausing. Write key points.
3. **Transcribe** the hardest 30 seconds (dictation).
4. **Check** with the transcript/subtitles. Classify every miss: unknown word? weak form? linking? speed? accent?
5. **Shadow:** play it again and speak *along with* the speaker, copying rhythm and intonation.
"""),
        # ------------------------------------------------------------------ 1
        ("md", """
---
## 1. Decoding connected speech

| Feature | What happens | Examples |
|---|---|---|
| **Weak forms** | function words lose stress and the vowel becomes /ə/ (schwa) | *to* /tə/, *for* /fə/, *can* /kən/, *and* /ən/, *of* /əv/, *have* /əv/, *them* /ðəm/ |
| **Linking** | final consonant joins the next vowel | *turn_it_off* -> /tɜːnɪˈtɒf/, *an_apple* |
| **Elision** | sounds disappear, especially /t/ and /d/ | *nex(t) day*, *las(t) night*, *han(d)bag*, *Chris(t)mas* |
| **Assimilation** | sounds change to fit their neighbours | *did you* -> /ˈdɪdʒu/, *would you* -> /ˈwʊdʒu/, *don't you* -> /ˈdəʊntʃu/, *ten people* -> /tem ˈpiːpl/ |
| **Contractions & reductions** | in informal speech | *gonna* (going to), *wanna* (want to), *gotta* (have got to), *dunno*, *lemme*, *gimme*, *kinda*, *shoulda / coulda / woulda / musta* |
| **Glottal stop** (UK/US) | /t/ becomes a catch in the throat | *wha' about i'?*, *bu'on* (button) |
| **Flap T** (US) | /t/ between vowels sounds like a soft /d/ | *water* -> "wader", *a lot of* -> "a lodda", *get it* -> "gedit" |

> You don't need to *speak* like this (although reducing weak forms will make you sound much more natural).
> You **do** need to *recognise* it.
"""),
        ("ex", {
            "id": "l6_connected_speech",
            "title": "Decode connected speech",
            "instructions": "Write each sentence in full, standard English (as you would write it).",
            "items": [
                {"q": "Whaddaya wanna do tonight?", "a": ["What do you want to do tonight?"]},
                {"q": "I dunno, lemme think.", "a": ["I don't know, let me think."]},
                {"q": "We shoulda left earlier.", "a": ["We should have left earlier."]},
                {"q": "Ya gotta be kidding me.", "a": ["You have got to be kidding me.", "You've got to be kidding me.", "You have to be kidding me.", "You've gotta be kidding me."]},
                {"q": "I'm gonna grab a coffee. D'ya want one?", "a": ["I am going to grab a coffee. Do you want one?", "I'm going to grab a coffee. Do you want one?"]},
                {"q": "It's kinda weird, innit?", "a": ["It's kind of weird, isn't it?", "It is kind of weird, is it not?"]},
                {"q": "She musta forgotten.", "a": ["She must have forgotten."]},
                {"q": "Didja see that?", "a": ["Did you see that?"]},
                {"q": "Gimme a sec.", "a": ["Give me a second.", "Give me a sec."]},
                {"q": "I oughta call him.", "a": ["I ought to call him."]},
                {"q": "Wouldja mind closing the window?", "a": ["Would you mind closing the window?"]},
                {"q": "Where'dja get that jacket?", "a": ["Where did you get that jacket?"]},
            ],
        }),
        ("md", """
**Now hear it:** search these phrases on **YouGlish** (e.g. "what do you want to do", "should have") and listen to
10 real speakers say each one. Notice how different they sound from the "dictionary" version.
"""),
        # ------------------------------------------------------------------ 2
        ("md", """
---
## 2. Dictation (text-to-speech)

Dictation is old-fashioned and **incredibly effective**: it shows you exactly which sounds you don't perceive.

**Protocol:**
1. Run `dictation(n)` and listen to the whole text once.
2. Listen again, pausing after each phrase, and type it into `my_text`.
3. Run `check_dictation(n, my_text)` and analyse **why** you missed each word.
4. Listen a final time while reading the original, then **shadow** it (speak along).
5. Change accent next time: `accent="co.uk"` (British), `"com.au"` (Australian), `"ca"`, `"ie"` (Irish), `"co.in"` (Indian).

Use `slow=True` only for the first attempt of a hard text - real life is not slow!
"""),
        ("code", """
texts = dictations()   # list of available dictations
"""),
        ("code", """
n = 1
dictation(n, accent="com")   # try accent="co.uk" later
"""),
        ("code", """
my_text = \"\"\"

\"\"\"
check_dictation(n, my_text)
"""),
        # ------------------------------------------------------------------ 3
        ("md", """
---
## 3. Listening for inference and attitude

At C1, questions are rarely "What colour was the car?". They are "What does the speaker **imply**?",
"How does she **feel** about...?", "What is the speaker's **main point**?".

For each passage: run `listen(n)` **without reading the transcript**, listen twice, then answer.
Only after checking, run `transcript(n)` and listen once more while reading.

**Signals to listen for:**
* **Hedging** = uncertainty or politeness: *I'm not saying it can't be done, but...* (= I think it can't!)
* **Contrast markers** = the important part comes after: *but, however, that said, having said that, then again*
* **Understatement** (very British): *It wasn't the best idea* (= a terrible idea); *let's just say...* (= I won't say it directly)
* **Intonation**: a falling-rising tone on *Well...* or *Interesting...* often signals doubt.
"""),
        ("code", """
listen(1)            # A voicemail from your manager
"""),
        ("ex", {
            "id": "l6_passage1",
            "title": "Passage 1 - A voicemail from your manager",
            "instructions": "Listen to passage 1 twice, then choose the best answer.",
            "items": [
                {"q": "Why is Laura calling?", "options": ["to question the proposed schedule", "to cancel the project", "to congratulate you on finishing early"]},
                {"q": "What does Laura really think about the timeline?", "options": ["It is probably unrealistic.", "It is too slow.", "It is exactly what she expected."],
                 "why": "'More optimistic than I'd expected' + 'I'm not saying it can't be done, but...' = polite doubt."},
                {"q": "What does she suggest?", "options": ["adding some extra time before committing to the client", "asking the client for more money", "giving the project to Daniel"]},
                {"q": "What does she imply about the client?", "options": ["They can be difficult to work with.", "They are old friends of Daniel's.", "They are thinking of cancelling."],
                 "why": "'Let's just say they weren't the easiest people to work with' = understatement."},
            ],
        }),
        ("code", """
listen(2)            # A podcast opinion on remote work
"""),
        ("ex", {
            "id": "l6_passage2",
            "title": "Passage 2 - Remote work: a mixed picture",
            "instructions": "Listen to passage 2 twice, then choose the best answer.",
            "items": [
                {"q": "What is the speaker's main point?", "options": ["The value of remote work depends on the type of task.", "Remote work has been a disaster for most companies.", "Offices will soon disappear completely."]},
                {"q": "How does the speaker feel about extreme views on remote work?", "options": ["critical - the evidence doesn't support them", "enthusiastic about both of them", "undecided between them"]},
                {"q": "Which activity does the speaker say suffers when people work remotely?", "options": ["training junior staff", "tasks that need deep concentration", "writing reports"]},
                {"q": "What does the speaker recommend?", "options": ["organising the working week around the needs of different tasks", "returning to the office full time", "letting each employee decide freely"]},
            ],
        }),
        ("code", """
listen(3)            # A short lecture on memory
"""),
        ("ex", {
            "id": "l6_passage3",
            "title": "Passage 3 - Why we forget (lecture)",
            "instructions": "Listen to passage 3 twice, then choose the best answer.",
            "items": [
                {"q": "What did Ebbinghaus use in his experiments?", "options": ["lists of nonsense syllables", "lists of foreign words", "photographs of faces"]},
                {"q": "According to the speaker, when do we forget new information fastest?", "options": ["within the first day or so", "after about a week", "after about a month"]},
                {"q": "What does the speaker say about cramming?", "options": ["It creates a false, short-lived feeling of having learned something.", "It is the most efficient way to prepare for exams.", "It only works for languages."]},
                {"q": "Why, according to the speaker, does spaced repetition work?", "options": ["The effort of recalling information strengthens the memory.", "It is easier and more relaxing than cramming.", "It lets you study more material in less time."]},
            ],
        }),
        ("code", """
listen(4)            # A news report
"""),
        ("ex", {
            "id": "l6_passage4",
            "title": "Passage 4 - News report: the four-day week",
            "instructions": "Listen to passage 4 twice, then choose the best answer.",
            "items": [
                {"q": "What was the main finding of the trial?", "options": ["Most companies kept the four-day week afterwards.", "Productivity fell sharply in most companies.", "Most employees wanted to return to five days."]},
                {"q": "Why does the reporter mention the critics?", "options": ["to point out that the companies may not be typical", "to show that the results were fake", "to explain why the trial was cancelled"]},
                {"q": "What is the reporter's attitude to the results?", "options": ["cautiously positive", "completely dismissive", "extremely enthusiastic"]},
                {"q": "What does 'the jury is still out' mean here?", "options": ["No final conclusion has been reached yet.", "The case is going to court.", "The experts have rejected the idea."]},
            ],
        }),
        ("code", """
# After answering, read along:
# transcript(1)
"""),
        # ------------------------------------------------------------------ 4
        ("md", """
---
## 4. Real-world listening worksheet

Use this for any podcast episode, TED talk, YouTube video or series episode. Copy the template into a new markdown cell
(or your notebook) each time. Aim for **3 worksheets per week** plus plenty of relaxed extensive listening.

```
Date:            Source / episode:                     Length:        Accent(s):
Understood (%):  gist ___   details ___

1. GIST (one sentence):
2. Five key points:
   -
3. Speaker's attitude / opinion (and HOW I knew - words, tone?):
4. Something implied but not said directly:
5. Five useful chunks (collocations, phrasal verbs, idioms) - with the full sentence:
   -
6. 30 seconds I transcribed + what I missed and why:
7. One-minute spoken summary: recorded?  [ ]
```

### Suggested listening ladder (see `RESOURCES.md` for links)

| Stage | Material | Subtitles |
|---|---|---|
| Weeks 1-4 | BBC Learning English (*6 Minute English*, *The English We Speak*), TED-Ed, *All Ears English* | English |
| Weeks 5-8 | TED talks, *Planet Money*, *Hidden Brain*, *The Indicator*, series like *Ted Lasso*, *The Office* | English -> none |
| Weeks 9-12 | *Freakonomics Radio*, *99% Invisible*, *The Rest Is History* (UK), BBC Radio 4, news without subs | none |
| Weeks 13-16 | *In Our Time* (BBC Radio 4), panel shows (*Would I Lie to You?*), films, fast conversational podcasts | none |

**Browser tool:** *Language Reactor* (extension for Netflix/YouTube) shows dual subtitles and lets you replay sentence by sentence -
perfect for intensive listening with series.
"""),
        ("code", """
# log_study(30, "listening", "dictation 1 + worksheet: Planet Money ep.")
"""),
    ],
}
