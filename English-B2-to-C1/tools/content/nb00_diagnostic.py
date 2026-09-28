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
| 00 | Orientation + diagnostic test (retake every 4 weeks) | 1 |
| 01 | Grammar I: conditionals, wishes, inversion, cleft sentences | 10-12 |
| 02 | Grammar II: past modals, advanced passives, participle clauses, emphasis, subjunctive | 10-12 |
| 03 | Vocabulary: collocations | 8-10 |
| 04 | Vocabulary: phrasal verbs and idioms | 8-10 |
| 05 | Word formation, paraphrasing and "false friends" | 8-10 |
| 06 | Listening lab: connected speech, dictations, inference, podcast worksheets | ongoing |
| 07 | Speaking and pronunciation lab: functional language, pronunciation for Spanish speakers, timed speaking | ongoing |
| 08 | Spaced-repetition flashcards (15 min every day) | ongoing |
| 09 | Progress tracker, mistake review, C1 can-do checklist | weekly |

Read `STUDY_PLAN.md` for the 16-week schedule and `RESOURCES.md` for books, podcasts, websites and apps.

## How the exercises work

1. Read the explanation.
2. In the code cell under each exercise, type your answers between the quotes: `1: "had known",`
3. Run the cell. `check()` marks your answers, explains mistakes and **saves them** in `progress/`.
4. Every wrong answer goes into your personal *mistake bank*. Notebook 09 re-tests you on it until you get each one right twice.

> **Rules for yourself:** don't look things up during the diagnostic, and don't peek at answer keys in `data/exercises/`.
> Guessing honestly gives you a better study plan.

## Setup (once)

```bash
pip install jupyter matplotlib gTTS
```
`gTTS` gives you text-to-speech audio for the listening dictations (needs internet). Offline alternative: `pip install pyttsx3`.
"""),
        ("md", """
---
# Diagnostic test (about 30-40 minutes)

Four sections of 10 questions. At the end you'll get a profile showing where to focus first.
Retake it every 4 weeks (Weeks 4, 8, 12, 16) and compare in Notebook 09.
"""),
        ("ex", {
            "id": "diag_grammar",
            "title": "Advanced grammar",
            "instructions": "Complete each sentence with the correct form of the word(s) in brackets, or one missing word.",
            "items": [
                {"q": "If I ______ (take) that job in Berlin, I would be living there now.", "a": ["had taken"],
                 "why": "Mixed conditional: past condition (had + past participle) -> present result."},
                {"q": "Not only ______ (he / forget) my birthday, but he also forgot our anniversary.", "a": ["did he forget"],
                 "why": "Negative adverbial at the start -> question-style inversion."},
                {"q": "It's high time you ______ (start) looking for a new flat.", "a": ["started"],
                 "why": "It's (high) time + subject + past simple (unreal past)."},
                {"q": "She ______ (be) at home - the lights are off and her car isn't there.", "a": ["can't be", "cannot be", "couldn't be"],
                 "why": "Logical deduction (negative, present): can't be."},
                {"q": "What I really need ______ a good night's sleep.", "a": ["is"],
                 "why": "Wh-cleft: What + clause + is + focus."},
                {"q": "______ (finish) his speech, he sat down to loud applause.", "a": ["having finished"],
                 "why": "Perfect participle for an action completed before the main one."},
                {"q": "The suspect is believed ______ (leave) the country last week.", "a": ["to have left"],
                 "why": "Passive reporting verb + perfect infinitive for a past action."},
                {"q": "I'd rather you ______ (not / mention) this to anyone.", "a": ["didn't mention", "did not mention"],
                 "why": "I'd rather + different subject + past simple."},
                {"q": "______ you need any help, don't hesitate to call.", "a": ["should"],
                 "why": "Inverted first conditional: Should you need... = If you need..."},
                {"q": "We ______ (hurry). The train was late anyway, so we rushed for nothing.", "a": ["needn't have hurried", "need not have hurried"],
                 "why": "needn't have + past participle: we did it, but it was unnecessary."},
            ],
        }),
        ("ex", {
            "id": "diag_collocations",
            "title": "Collocations",
            "instructions": "Choose the word that forms the most natural collocation. Type the letter or the word.",
            "items": [
                {"q": "She ___ a lot of effort into the project.", "options": ["put", "made", "gave"]},
                {"q": "We need to ___ steps to fix this.", "options": ["take", "do", "make"]},
                {"q": "Whether it's a good film is a ___ of opinion.", "options": ["matter", "question", "case"]},
                {"q": "I have a ___ memory of that day.", "options": ["vivid", "bright", "lively"]},
                {"q": "There's been a ___ increase in prices this month.", "options": ["sharp", "strong", "hard"]},
                {"q": "After weeks of talks, they finally ___ a compromise.", "options": ["reached", "arrived", "got"]},
                {"q": "He's a ___ believer in hard work.", "options": ["firm", "hard", "solid"]},
                {"q": "The news came as a ___ shock.", "options": ["complete", "full", "whole"]},
                {"q": "The company ___ record profits last year.", "options": ["posted", "did", "put"]},
                {"q": "I'm ___ aware of the risks involved.", "options": ["well", "highly", "strongly"]},
            ],
        }),
        ("ex", {
            "id": "diag_phrasal_idioms",
            "title": "Phrasal verbs and idioms",
            "instructions": "Write ONE word in each gap.",
            "items": [
                {"q": "The wedding was ______ off at the last minute.", "a": ["called"]},
                {"q": "I can't put ______ with his arrogance any longer.", "a": ["up"]},
                {"q": "We need to come up ______ a better plan.", "a": ["with"]},
                {"q": "Let's get the ball ______ and start the meeting.", "a": ["rolling"]},
                {"q": "That new laptop cost an arm and a ______.", "a": ["leg"]},
                {"q": "She turned ______ the job offer because the salary was too low.", "a": ["down"]},
                {"q": "He's always sitting on the ______; he never takes sides.", "a": ["fence"]},
                {"q": "I'll look ______ the matter and get back to you.", "a": ["into"]},
                {"q": "Don't worry, it's not rocket ______ - anyone can do it.", "a": ["science"]},
                {"q": "The two managers aren't on the same ______ about the budget.", "a": ["page"]},
            ],
        }),
        ("ex", {
            "id": "diag_word_formation",
            "title": "Word formation",
            "instructions": "Use the word in CAPITALS to form a word that fits the gap.",
            "items": [
                {"q": "The ______ of the new museum was delayed by six months. (OPEN)", "a": ["opening"]},
                {"q": "Her ______ was obvious from the way she smiled. (HAPPY)", "a": ["happiness"]},
                {"q": "The results were rather ______, to be honest. (DISAPPOINT)", "a": ["disappointing"]},
                {"q": "It's ______ to park on this side of the street. (LEGAL)", "a": ["illegal"]},
                {"q": "His sudden ______ surprised everyone in the department. (RESIGN)", "a": ["resignation"]},
                {"q": "We need a more environmentally ______ approach. (SUSTAIN)", "a": ["sustainable"]},
                {"q": "We seriously ______ the time the project would take. (ESTIMATE)", "a": ["underestimated"]},
                {"q": "These two drugs should never be taken ______. (SIMULTANEOUS)", "a": ["simultaneously"]},
                {"q": "She has been a lifelong ______ of human rights. (DEFEND)", "a": ["defender"]},
                {"q": "The speech was ______ long; most people stopped listening. (NECESSARY)", "a": ["unnecessarily"]},
            ],
        }),
        ("md", """
## Listening mini-check (optional but recommended)

Run the cell below, listen **once** without pausing, then **twice more** pausing as much as you want.
Type what you hear and check it. (Needs `pip install gTTS` + internet, or `pyttsx3` offline.)
"""),
        ("code", """
dictation(5)   # accent options: accent="co.uk", "com.au", "ca", "ie", "co.in"
"""),
        ("code", """
my_transcript = \"\"\"

\"\"\"
check_dictation(5, my_transcript)
"""),
        ("md", """
## Your profile

Paste your scores into the cell below (the `Score: x/10` lines above) and run it.
"""),
        ("code", """
scores = {
    "grammar":         0,   # diag_grammar
    "collocations":    0,   # diag_collocations
    "phrasal_idioms":  0,   # diag_phrasal_idioms
    "word_formation":  0,   # diag_word_formation
}
where = {
    "grammar": "Notebooks 01 and 02",
    "collocations": "Notebook 03 + deck 'collocations' in Notebook 08",
    "phrasal_idioms": "Notebook 04 + decks 'phrasal_verbs' and 'idioms'",
    "word_formation": "Notebook 05",
}
for area, s in sorted(scores.items(), key=lambda kv: kv[1]):
    level = "C1 range" if s >= 8 else "B2+ (almost there)" if s >= 6 else "B2 - priority"
    bar = "#" * s + "." * (10 - s)
    print(f"{area:<16} {bar} {s}/10  {level:<20} -> {where[area]}")
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
