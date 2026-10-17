NOTEBOOK = {
    "file": "00_Start_Here_Diagnostic.ipynb",
    "title": "00 - Start Here: How This Course Works + Diagnostic Test",
    "cells": [
        ("md", """
Welcome! This folder is a self-study course designed to take you from a **"shaky B2"** to a **solid, usable C1**,
with extra focus on **advanced grammar, vocabulary/collocations, listening and speaking**.

## What C1 actually means

The Council of Europe (CEFR) describes a C1 user as someone who:

* can understand a wide range of **demanding, longer texts and recognise implicit meaning**;
* can express themselves **fluently and spontaneously without much obvious searching for expressions**;
* can use language **flexibly and effectively** for social, academic and professional purposes;
* can produce **clear, well-structured, detailed** speech and text, showing **controlled use of organisational
  patterns, connectors and cohesive devices**.

Notice what is *not* on that list: "never makes mistakes" or "uses very rare words". The jump from B2 to C1 is mostly about
**precision, naturalness (collocations!), flexibility (saying the same thing in several ways) and fluency under pressure**.

## How the course is organised

| Notebook | Focus | Hours (approx.) |
|---|---|---|
| 00 | Orientation + diagnostic (two parallel forms, retake every 4 weeks) + speaking benchmark | 1.5 |
| 01b | **Accuracy core for Spanish speakers**: articles, prepositions, tenses, word order, verb patterns | 8-10 |
| 01 | Grammar I: conditionals, wishes, inversion, cleft sentences | 10-12 |
| 02 | Grammar II: past modals, advanced passives, participle clauses, emphasis, subjunctive | 10-12 |
| 02b | Grammar III: noun phrases, relative clauses, future forms, the grammar of hedging | 8-10 |
| 03 | Vocabulary: collocations | 8-10 |
| 04 | Vocabulary: phrasal verbs, idioms and workplace English | 8-10 |
| 05 | Word formation, paraphrasing and "false friends" | 8-10 |
| 06 | Listening lab: connected speech, dictations, inference, podcast worksheets | ongoing |
| 07 | Speaking and pronunciation lab: functional language, pronunciation for Spanish speakers, feedback loop | ongoing |
| 08 | Spaced-repetition flashcards (10-15 min every day) | ongoing |
| 09 | Progress tracker, mixed review, mistake bank, C1 can-do checklist | weekly |

Read `STUDY_PLAN.md` for the 16-week schedule and `RESOURCES.md` for books, podcasts, websites and apps.

## How the exercises work

1. Read the explanation.
2. In the code cell under each exercise, type your answers between the quotes: `1: "had known",`
3. Run the cell. `check()` marks your answers (contractions, British/American spellings and common variants are accepted),
   explains mistakes and **saves them** in `progress/`. Blank items are skipped, so you can do a set in several sittings.
4. Every wrong answer goes into your personal *mistake bank*. Notebook 09 brings each one back after 1, 3, 7 and 21 days
   until you've got it right on four different days - plus a *mixed review* of everything you've studied.
5. For **open** answers (rewrites), compare with the model answers. If yours was wrong, re-run with `wrong=[item numbers]`.

> **Rules for yourself:** don't look things up during the diagnostic, and don't peek at answer keys in `data/exercises/`.
> Guessing honestly gives you a better study plan.

## Setup (once)

```bash
pip install -r requirements.txt      # jupyter, matplotlib, edge-tts, gTTS
```
`edge-tts` (natural neural voices in 8 accents) or `gTTS` give you audio for the listening exercises; both need internet.
Offline alternative: `pip install pyttsx3`. Optional: `pip install faster-whisper` to transcribe your own speaking recordings.

> **Tip:** don't use "Run All" in this course - run the cells one by one. Some tools (flashcards, reviews) ask you questions
> and wait for your answer.
"""),
        ("md", """
---
# Diagnostic test (about 40 minutes)

There are **two parallel forms**: take **Form A** now (week 0), **Form B** in week 4, A in week 8, B in week 12 and A in week 16.
None of these items appear anywhere else in the course, so your score measures real progress, not memory of the answers.
Mistakes made here are **not** added to your review bank.

Each form has five sections of 10 items: **grammar, accuracy (typical Spanish-speaker errors), collocations,
phrasal verbs & idioms, word formation**. Then there's a dictation and a speaking benchmark.

> For a gap where **no word** is needed (e.g. no article), type a dash: `-`
"""),
        ("md", "## Form A"),
        ("ex", {
            "id": "diag_A_grammar",
            "title": "Form A - Advanced grammar",
            "instructions": "Complete each sentence with the correct form of the word(s) in brackets, or one missing word.",
            "items": [
                {"q": "If she ______ (not / lend) me the money last year, I would still be paying off my debts now.", "a": ["hadn't lent", "had not lent"],
                 "why": "Mixed conditional: past condition -> present result."},
                {"q": "Not once ______ (she / complain) about the workload during the whole project.", "a": ["did she complain"],
                 "why": "Negative adverbial at the start -> inversion."},
                {"q": "It's about time the council ______ (repair) this road.", "a": ["repaired"]},
                {"q": "He ______ (be) at the gym now - he never trains on Sundays.", "a": ["can't be", "cannot be", "couldn't be"]},
                {"q": "What surprised me most ______ how calm everyone was.", "a": ["was"]},
                {"q": "______ (not / receive) a reply, I called them again.", "a": ["not having received", "having not received"]},
                {"q": "The ship is thought ______ (sink) in the 17th century.", "a": ["to have sunk"]},
                {"q": "I'd rather we ______ (not / discuss) this in front of the clients.", "a": ["didn't discuss", "did not discuss"]},
                {"q": "______ you require further assistance, please contact reception.", "a": ["should"]},
                {"q": "You ______ (bring) your umbrella - it didn't rain, and you carried it around all day for nothing.", "a": ["needn't have brought", "need not have brought"]},
            ],
        }),
        ("ex", {
            "id": "diag_A_accuracy",
            "title": "Form A - Accuracy core",
            "instructions": "Write ONE word (or the correct verb form) in each gap. Type - if no word is needed.",
            "items": [
                {"q": "Whether we go ahead depends ______ the price.", "a": ["on", "upon"]},
                {"q": "She's married ______ a doctor.", "a": ["to"]},
                {"q": "I ______ (live) in this city since 2015.", "a": ["have lived", "have been living"]},
                {"q": "______ is important to arrive early for the interview.", "a": ["it"]},
                {"q": "______ are many problems with this plan.", "a": ["there"]},
                {"q": "Can you tell me where the station ______?", "a": ["is"]},
                {"q": "I look forward to ______ (hear) from you.", "a": ["hearing"]},
                {"q": "______ unemployment has risen sharply this year.", "a": ["-", "no article", "none", "0", "ø"]},
                {"q": "He made me ______ (wait) for over an hour.", "a": ["wait"]},
                {"q": "I ______ (see) him yesterday at the station.", "a": ["saw"]},
            ],
        }),
        ("ex", {
            "id": "diag_A_collocations",
            "title": "Form A - Collocations",
            "instructions": "Choose the word that forms the most natural collocation. Type the letter or the word.",
            "items": [
                {"q": "The minister ___ an apology after the scandal.", "options": ["issued", "gave out", "made out"]},
                {"q": "She has a ___ grasp of the subject.", "options": ["firm", "heavy", "tall"]},
                {"q": "Don't make a ___ decision - take your time.", "options": ["snap", "sharp", "hot"]},
                {"q": "The film received ___ reviews from the critics.", "options": ["rave", "raving", "crazy"]},
                {"q": "There's a ___ possibility that the flight will be cancelled.", "options": ["distinct", "sharp", "heavy"]},
                {"q": "He ___ the blame for the error, although it wasn't his fault.", "options": ["took", "made", "did"]},
                {"q": "She ___ a fortune in property.", "options": ["made", "did", "took"]},
                {"q": "It's an ___ secret that he's leaving the company.", "options": ["open", "public", "known"]},
                {"q": "The two candidates had a ___ debate on TV.", "options": ["heated", "burning", "boiling"]},
                {"q": "The company ___ a profit for the first time last year.", "options": ["made", "did", "got"]},
            ],
        }),
        ("ex", {
            "id": "diag_A_phrasal_idioms",
            "title": "Form A - Phrasal verbs and idioms",
            "instructions": "Write ONE word in each gap.",
            "items": [
                {"q": "I'll pick you ______ from the airport at six.", "a": ["up"]},
                {"q": "Prices are expected to go ______ again next month.", "a": ["up"]},
                {"q": "She was brought ______ by her grandparents in a small village.", "a": ["up"]},
                {"q": "Could you fill ______ this form, please?", "a": ["in", "out"]},
                {"q": "Sorry, I've got to hang ______ now - someone's at the door.", "a": ["up"]},
                {"q": "I was so tired that I slept like a ______.", "a": ["log", "baby"]},
                {"q": "He's always been the black ______ of the family.", "a": ["sheep"]},
                {"q": "Don't worry about the test - it'll be a piece of ______.", "a": ["cake"]},
                {"q": "Keep your ______ crossed for me tomorrow!", "a": ["fingers"]},
                {"q": "I can't help you this week - I've got too much on my ______.", "a": ["plate"]},
            ],
        }),
        ("ex", {
            "id": "diag_A_word_formation",
            "title": "Form A - Word formation",
            "instructions": "Use the word in CAPITALS to form a word that fits the gap.",
            "items": [
                {"q": "The ______ of the two banks was announced today. (MERGE)", "a": ["merger"]},
                {"q": "Her ______ to detail is impressive. (ATTEND)", "a": ["attention"]},
                {"q": "The plan looked good on paper but was completely ______. (PRACTICE)", "a": ["impractical"]},
                {"q": "We were impressed by the ______ of the team. (FLEXIBLE)", "a": ["flexibility"]},
                {"q": "The situation is getting ______ worse. (PROGRESS)", "a": ["progressively"]},
                {"q": "There is a serious ______ of skilled workers. (SHORT)", "a": ["shortage"]},
                {"q": "His ______ to the company was rewarded with a promotion. (LOYAL)", "a": ["loyalty"]},
                {"q": "The heat in the office was ______. (BEAR)", "a": ["unbearable"]},
                {"q": "She spoke with great ______ during the presentation. (CONFIDENT)", "a": ["confidence"]},
                {"q": "Please ______ the file before you send it. (NAME)", "a": ["rename"]},
            ],
        }),
        ("md", """
## Form B (weeks 4 and 12)
"""),
        ("ex", {
            "id": "diag_B_grammar",
            "title": "Form B - Advanced grammar",
            "instructions": "Complete each sentence with the correct form of the word(s) in brackets, or one missing word.",
            "items": [
                {"q": "Were it not for the government subsidy, the firm ______ (go) bankrupt years ago.", "a": ["would have gone"]},
                {"q": "Only later ______ (I / realise) what had really happened.", "a": ["did I realise", "did I realize"]},
                {"q": "I wish you ______ (stop) interrupting me all the time!", "a": ["would stop"]},
                {"q": "I can't find my keys. They ______ (fall) out of my pocket in the taxi.", "a": ["might have fallen", "may have fallen", "could have fallen", "must have fallen"]},
                {"q": "It was her calm voice ______ reassured everyone.", "a": ["that", "which"]},
                {"q": "The report, ______ (write) in a hurry, contained several errors.", "a": ["written"]},
                {"q": "She is reported ______ (negotiate) with a rival firm at the moment.", "a": ["to be negotiating"]},
                {"q": "The committee recommended that the fee ______ (reduce).", "a": ["be reduced", "should be reduced"]},
                {"q": "If I ______ (be) you, I'd accept the offer.", "a": ["were", "was"]},
                {"q": "Scarcely ______ (the meeting / begin) when the fire alarm went off.", "a": ["had the meeting begun"]},
            ],
        }),
        ("ex", {
            "id": "diag_B_accuracy",
            "title": "Form B - Accuracy core",
            "instructions": "Write ONE word (or the correct verb form) in each gap. Type - if no word is needed.",
            "items": [
                {"q": "She's responsible ______ training new staff.", "a": ["for"]},
                {"q": "I'm really interested ______ learning more about it.", "a": ["in"]},
                {"q": "How long ______ her? (you / know)", "a": ["have you known"]},
                {"q": "I've worked here ______ three years.", "a": ["for"]},
                {"q": "______ is raining again.", "a": ["it"]},
                {"q": "I don't know what time the shop ______ (open).", "a": ["opens"]},
                {"q": "I'm used to ______ (get) up early.", "a": ["getting"]},
                {"q": "He's ______ engineer at a car company.", "a": ["an"]},
                {"q": "I stopped ______ (smoke) ten years ago and feel much better.", "a": ["smoking"]},
                {"q": "Could you explain the rules ______ me?", "a": ["to"]},
            ],
        }),
        ("ex", {
            "id": "diag_B_collocations",
            "title": "Form B - Collocations",
            "instructions": "Choose the word that forms the most natural collocation. Type the letter or the word.",
            "items": [
                {"q": "The police have ___ an investigation into the fire.", "options": ["launched", "thrown", "done"]},
                {"q": "She ___ a speech at the conference.", "options": ["gave", "said", "told"]},
                {"q": "The storm caused ___ damage to the coast.", "options": ["extensive", "wide", "tall"]},
                {"q": "He has a very ___ sense of humour.", "options": ["dry", "arid", "thirsty"]},
                {"q": "We had a ___ escape - the car nearly hit us.", "options": ["narrow", "thin", "slim"]},
                {"q": "The proposal ___ support from the board.", "options": ["won", "beat", "made"]},
                {"q": "Profits ___ by 40% last year.", "options": ["soared", "flew", "hopped"]},
                {"q": "Please ___ your seatbelts.", "options": ["fasten", "close", "lock"]},
                {"q": "The speech was followed by ___ applause.", "options": ["thunderous", "stormy", "heavy"]},
                {"q": "He ___ a good impression at the interview.", "options": ["made", "did", "put"]},
            ],
        }),
        ("ex", {
            "id": "diag_B_phrasal_idioms",
            "title": "Form B - Phrasal verbs and idioms",
            "instructions": "Write ONE word in each gap.",
            "items": [
                {"q": "The plane took ______ an hour late.", "a": ["off"]},
                {"q": "Could you turn ______ the music? It's too loud.", "a": ["down"]},
                {"q": "I ran ______ an old school friend at the supermarket.", "a": ["into"]},
                {"q": "We need to deal ______ this problem now.", "a": ["with"]},
                {"q": "She's always looked ______ to her older sister.", "a": ["up"]},
                {"q": "He's pulling your ______ - it isn't true.", "a": ["leg"]},
                {"q": "Horror films aren't really my cup of ______.", "a": ["tea"]},
                {"q": "Hang in ______ - things will get better.", "a": ["there"]},
                {"q": "She has a heart of ______ - she'd help anyone.", "a": ["gold"]},
                {"q": "I'm between jobs at the moment, so money's a bit ______.", "a": ["tight"]},
            ],
        }),
        ("ex", {
            "id": "diag_B_word_formation",
            "title": "Form B - Word formation",
            "instructions": "Use the word in CAPITALS to form a word that fits the gap.",
            "items": [
                {"q": "The ______ of the new law caused protests. (INTRODUCE)", "a": ["introduction"]},
                {"q": "His explanation wasn't very ______. (CONVINCE)", "a": ["convincing"]},
                {"q": "The team worked ______ to meet the deadline. (TIRE)", "a": ["tirelessly"]},
                {"q": "We need to ______ our online presence. (STRONG)", "a": ["strengthen"]},
                {"q": "The weather in the mountains is completely ______. (PREDICT)", "a": ["unpredictable"]},
                {"q": "She was praised for her ______. (HONEST)", "a": ["honesty"]},
                {"q": "The ______ between the two countries is growing. (TENSE)", "a": ["tension"]},
                {"q": "His ______ caused the accident. (CARE)", "a": ["carelessness"]},
                {"q": "A ______ of the report will be published online. (SUMMARISE)", "a": ["summary"]},
                {"q": "The ______ of the town has doubled since 1990. (POPULATE)", "a": ["population"]},
            ],
        }),
        ("md", """
---
## Listening benchmark

**Form A:** dictation 16. **Form B:** dictation 17. These two texts are reserved for the diagnostic - don't use them for practice.
Listen once without pausing, then twice more, pausing as much as you want. Type what you hear and check it.

**Extra (recommended):** pick an **unseen** 6-minute episode of BBC *6 Minute English* or a TED talk, listen once
without subtitles, and write a 5-sentence summary. Then check with the transcript and estimate the % you understood.
Record that % in Notebook 09.
"""),
        ("code", """
dictation(16)   # Form A. Form B: dictation(17). Accents: accent="uk", "au", "ie", "in"...
"""),
        ("code", """
my_transcript = \"\"\"

\"\"\"
check_dictation(16, my_transcript)   # or 17 for Form B
"""),
        ("md", """
## Speaking benchmark (the most important number to track)

1. Run `random_prompt("long turn")`, take 60 seconds to prepare, then **record yourself for 2 minutes** (phone recorder).
2. Transcribe it **word for word, including every "eh / um"** (or use `analyse_recording("file.m4a")`, see Notebook 07).
3. Run `speech_stats(transcript, 120, label="diagnostic week 0")`.
4. Count your errors per 100 words, and write your numbers into the table in Notebook 09.

**Keep the recording.** Comparing week 0 with week 16 is the most motivating thing you'll hear.
"""),
        ("code", """
# p = random_prompt("long turn")
# my_speech = \"\"\" paste your transcript here \"\"\"
# speech_stats(my_speech, seconds=120, label="diagnostic week 0")
"""),
        ("md", """
## Your profile
"""),
        ("code", """
diagnostic_profile()
where = {"grammar": "Notebooks 01, 02, 02b", "accuracy": "Notebook 01b (do it first!)",
         "collocations": "Notebook 03 + decks 'collocations' and 'functional_chunks'",
         "phrasal_idioms": "Notebook 04 + decks 'phrasal_verbs', 'idioms', 'workplace'",
         "word_formation": "Notebook 05"}
print("\\nWhere to work on each area:")
for area, nb in where.items():
    print(f"  {area:<16} -> {nb}")
print("\\nStart with your lowest area, but keep the daily routine (flashcards + listening + speaking) every day.")
"""),
        ("md", """
### Self-rating for speaking and listening

Tick honestly (edit this cell: change `[ ]` to `[x]`). If you can't tick at least 4 in a column, that skill is a priority.

| Listening - I can... | Speaking - I can... |
|---|---|
| [ ] follow a podcast for native speakers (e.g. *Planet Money*) without subtitles | [ ] talk for 2 minutes on a familiar topic without long pauses |
| [ ] understand a TV series without subtitles most of the time | [ ] disagree politely and give reasons, without sounding blunt |
| [ ] catch jokes, irony and implied criticism | [ ] rephrase when I don't know a word, without stopping |
| [ ] understand fast speech with contractions ("gonna", "shoulda", "d'ya") | [ ] use hedging ("It could be argued that...", "I'm not entirely sure...") |
| [ ] follow a conversation between several native speakers | [ ] tell a story using a range of past tenses and linkers |
| [ ] understand at least 2 accents besides US/UK standard | [ ] be understood easily by people who don't speak Spanish |
"""),
    ],
}
