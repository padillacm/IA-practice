NOTEBOOK = {
    "file": "06_Listening_Lab.ipynb",
    "title": "06 - Listening Lab: Connected Speech, Dictation, Inference and Real-World Listening",
    "cells": [
        ("md", """
### Why listening feels hard at B2
You probably know most of the words you hear - but in fast native speech they **don't sound like the words you learnt**.
*What do you want to do?* becomes /ˈwɒdʒə ˈwɒnə ˈduː/ (UK, "wodja wanna do") or /ˈwʌɾəjə ˈwɑːnə ˈduː/ (US, "whaddaya wanna do"). The problem is usually **perception**, not vocabulary.
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
| **Weak forms** | function words lose stress and the vowel becomes /ə/ (schwa) | *to* /tə/ (before consonants; /tu/ before vowels), *for* /fə/, *can* /kən/, *and* /ən/, *of* /əv/, *have* /əv/, *them* /ðəm/, *was* /wəz/, *were* /wə/, *at* /ət/, *from* /frəm/, *but* /bət/, *than* /ðən/, *that* (conjunction) /ðət/, *some* /səm/, *does* /dəz/, *him* /ɪm/, *her* /ə/, *you/your* /jə/, *are* /ə/ |
| **Strong forms** | the same words are **full** at the end of a phrase or when contrasted | *What are you looking **at** /æt/?* · *Yes, I **can** /kæn/.* · *It's not **for** you, it's **from** you.* |
| **can / can't (US)** | the /t/ of *can't* is often inaudible | *I can go* /aɪ kən ˈɡoʊ/ vs *I can't go* /aɪ ˈkæn(ʔ) ˈɡoʊ/: listen for the **full, stressed vowel** in *can't* |
| **Linking** | final consonant joins the next vowel; /r/, /w/, /j/ glides | *turn_it_off* /tɜːnɪˈtɒf/ · *far_away* /fɑːr əˈweɪ/ · UK intrusive r: *law_and order* /ˌlɔːr ən ˈɔːdə/ · *go_on* /ɡəʊ wɒn/ · *I_agree* /aɪ jəˈɡriː/ |
| **Elision** | /t/ and /d/ disappear **between two consonants** (not before a vowel) | *mus(t) be*, *firs(t) thing*, *I don'(t) know*, *las(t) night* /lɑːs naɪt/ - but *last of all* /lɑːst əv/ |
| **Assimilation** | sounds change to fit their neighbours | *did you* -> /ˈdɪdʒu/ or /ˈdɪdʒə/, *would you* -> /ˈwʊdʒu/, *don't you* -> /ˈdəʊntʃu/, *ten people* -> /tem ˈpiːpl/, *good boy* /ɡʊb bɔɪ/, *that cake* /ðæk keɪk/, *this shop* /ðɪʃ ʃɒp/, *handbag* /ˈhæmbæɡ/ |
| **Contractions & reductions** | in informal speech | *gonna* (going to), *wanna* (want to), *gotta* (have got to), *dunno*, *lemme*, *gimme*, *kinda*, *shoulda / coulda / woulda / musta* |
| **Glottal stop** | /t/ becomes a catch in the throat. UK (esp. London, spreading everywhere); US mainly before /n/ and at word end | *wha' about i'?*, *bu'on* (button), *moun'ain* (US) |
| **Flap T** (US, Canada, Australia) | /t/ between vowels, before an unstressed syllable, becomes a quick tap | It's **exactly the Spanish single *r* in *pero, cara***: *water* ≈ "guára", *a lot of* ≈ "a lára", *get it* ≈ "guérit". *latter* = *ladder*, *twenty* -> "twenny". (*attack* keeps a real /t/ - stressed syllable.) |

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
        ("ex", {
            "id": "l6_weak_strong",
            "title": "Strong or weak form?",
            "instructions": "Is the CAPITALISED word said in its strong form or its weak form (with /ə/)? Write strong or weak. Say each sentence aloud.",
            "items": [
                {"q": "I CAN swim, but not very well.", "a": ["weak"]},
                {"q": "A: Can you swim?  B: Yes, I CAN.", "a": ["strong"]},
                {"q": "What are you looking AT?", "a": ["strong"]},
                {"q": "Meet me AT six.", "a": ["weak"]},
                {"q": "She WAS late again.", "a": ["weak"]},
                {"q": "A: Was she late?  B: Yes, she WAS.", "a": ["strong"]},
                {"q": "Where are you FROM?", "a": ["strong"]},
                {"q": "I'm FROM Seville.", "a": ["weak"]},
                {"q": "Would you like SOME tea?", "a": ["weak"]},
                {"q": "SOME people just never learn. (= certain people)", "a": ["strong"]},
                {"q": "It's not FOR you, it's from you.", "a": ["strong"]},
                {"q": "She's taller THAN me.", "a": ["weak"]},
            ],
        }),
        ("md", """
### Micro-dictations: hear the weak forms
Each sentence is short and full of weak forms and linking. Play it (`micro(n)`), replay as often as you need, and type
**exactly** what was said (contractions like *I'd've* can be written in full: *I would have*).
"""),
        ("code", """
micro(1)          # change the number: 1-10. Try accent="uk" too.
"""),
        ("ex", {
            "id": "l6_micro",
            "title": "Micro-dictations",
            "instructions": "Type each sentence you heard with micro(1) ... micro(10).",
            "items": [
                {"q": "micro(1)", "a": ["I'd have told you if I'd known.", "I would have told you if I had known."]},
                {"q": "micro(2)", "a": ["What are you going to do about it?"]},
                {"q": "micro(3)", "a": ["There's a lot of work to do before the end of the week."]},
                {"q": "micro(4)", "a": ["Could you give him a call and ask him to come in?"]},
                {"q": "micro(5)", "a": ["I was hoping we could have a chat about it."]},
                {"q": "micro(6)", "a": ["Some of them have already left for the airport."]},
                {"q": "micro(7)", "a": ["She must have been waiting for ages."]},
                {"q": "micro(8)", "a": ["It's not as bad as it looks."]},
                {"q": "micro(9)", "a": ["He can't have seen it, or he'd have said something.", "He cannot have seen it, or he would have said something."]},
                {"q": "micro(10)", "a": ["We've been meaning to get in touch with them for a while."]},
            ],
        }),
        ("md", """
### Recognising accents

| Feature | UK (standard southern) | US (General American) | Also listen for |
|---|---|---|---|
| /r/ after vowels | silent: *car* /kɑː/ | pronounced: /kɑːr/ | Irish, Scottish: pronounced |
| *bath, dance, can't* | /ɑː/ | /æ/ | North of England: /a/ |
| *water, better* | [t] or glottal [ʔ] | flap [ɾ] ("wader") | Australia: flap too |
| *go, no* | /əʊ/ | /oʊ/ | Scotland/Ireland: nearly pure [oː] |
| *hot, lot* | /ɒ/ (rounded) | /ɑː/ (like *father*) | |
| *new, tune* | /njuː/, /tʃuːn/ | /nuː/, /tuːn/ | |
"""),
        # ------------------------------------------------------------------ 2
        ("md", """
---
## 2. Dictation (text-to-speech)

Dictation is old-fashioned and **incredibly effective**: it shows you exactly which sounds you don't perceive.

**Protocol:**
1. Run `dictation(n)` and listen to the whole text once.
2. Listen again, pausing after each phrase, and type it into `my_text`.
3. Run `check_dictation(n, my_text)`. It shows each miss and a **likely cause** (weak form, linking, ending, vocabulary)
   and saves it, so `listening_report()` in Notebook 09 shows what you mishear most.
4. Listen a final time while reading the original, then **shadow** it (speak along).
5. **Retell it** in your own words for 30-60 seconds (record yourself). Input -> output.
6. Change accent next time: `accent="uk"`, `"au"`, `"ie"` (Irish), `"in"` (Indian), `"za"` (South African), `"ca"`, `"ng"`.

Tips: `chunks=True` gives you one player per phrase; `rate=0.85` slows playback a little while keeping natural rhythm.
Dictations 16 and 17 are reserved for the diagnostic.

> **About the audio:** synthetic voices (TTS) are clear but don't reduce words or show attitude the way real people do.
> Use them to train *perception of words*; for tone, irony and real fast speech, use authentic audio (section 4).
> `pip install edge-tts` gives the most natural voices.
"""),
        ("code", """
texts = dictations()   # list of available dictations
"""),
        ("code", """
n = 1
dictation(n, accent="us", chunks=False)   # later: accent="uk", chunks=True, rate=0.85
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
* **Hedging** = uncertainty or politeness: *I'm not saying it can't be done, but...* (= I have serious doubts)
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
                {"q": "Why is Laura calling?", "options": ["to express doubts about the proposed schedule", "to ask you to hand the Henderson project over to Daniel", "to tell you the client has rejected your timeline"]},
                {"q": "What does Laura really think about the timeline?", "options": ["It is too ambitious as it stands.", "It is achievable only if Daniel joins the team.", "It is more cautious than she expected."],
                 "why": "'More optimistic than I'd expected' + 'I'm not saying it can't be done, but...' = polite doubt."},
                {"q": "What does she suggest?", "options": ["allowing extra time before making a commitment to the client", "committing to the client now and adjusting the plan later", "letting Daniel negotiate the deadline with the client"]},
                {"q": "What does she imply about the client?", "options": ["They can be difficult to work with.", "They were unhappy with Daniel's work last year.", "They are likely to demand a shorter deadline."],
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
                {"q": "How does the speaker feel about extreme views on remote work?", "options": ["critical - the evidence doesn't support them", "sympathetic to the view that remote work has been a disaster", "reluctant to give any opinion of their own"]},
                {"q": "Which activity does the speaker say suffers when people work remotely?", "options": ["training junior staff", "tasks that need deep concentration", "meetings with clients"]},
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
                {"q": "What does the speaker say about cramming?", "options": ["It creates a false, short-lived feeling of having learned something.", "It is the most efficient way to prepare for exams.", "It works well as long as you review again the following week."]},
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
                {"q": "What is the reporter's attitude to the results?", "options": ["cautiously positive", "broadly sceptical - the results are probably misleading", "convinced the model will work across the whole economy"]},
                {"q": "What does 'the jury is still out' mean here?", "options": ["No final conclusion has been reached yet.", "The case is going to court.", "The experts have rejected the idea."]},
            ],
        }),
        ("code", """
listen(5)            # A conversation: planning the team away-day (two voices)
"""),
        ("ex", {
            "id": "l6_passage5",
            "title": "Passage 5 - Planning the team away-day (irony and tone)",
            "instructions": "Listen to passage 5 twice, then choose the best answer.",
            "items": [
                {"q": "How does B feel about the paintballing plan?", "options": ["unenthusiastic, although B doesn't say so directly", "genuinely excited", "worried about getting hurt"]},
                {"q": "What does B imply about the last away-day?", "options": ["It didn't achieve much.", "It was too expensive.", "It was cancelled at the last minute."]},
                {"q": "Why might B hesitate to make a suggestion to Karen?", "options": ["B could end up with extra work.", "Karen doesn't like new ideas.", "B doesn't know Karen well."]},
                {"q": "In B's first turn, 'Brilliant' is...", "options": ["ironic", "sincere", "a question"]},
            ],
        }),
        ("md", """
**After each passage:** record a 60-second summary of it for someone who didn't hear it (*"Basically, the speaker argues
that..."*). This turns listening input into speaking output - and it's a real C1 skill (called *mediation*).
"""),
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
6. 30 seconds I transcribed + what I missed and why (log each: log_listening_miss("weak form", heard, actual, source)):
7. One-minute spoken summary: recorded?  [ ]   speech_stats() run?  [ ]
```

### Suggested listening ladder (see `RESOURCES.md` for links)

| Stage | Material | Subtitles |
|---|---|---|
| Weeks 1-4 | BBC Learning English (*6 Minute English*, *The English We Speak*, *Tim's Pronunciation Workshop*), TED-Ed, *All Ears English* | English |
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
