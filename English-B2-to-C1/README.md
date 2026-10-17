# English B2 → C1: Self-Study Course in Jupyter Notebooks

An interactive, 16-week course to go from a shaky B2 to a solid, usable **C1**, with extra focus on
**accuracy, advanced grammar, vocabulary/collocations, listening and speaking**. Everything is in English.

## Quick start

```bash
cd English-B2-to-C1
pip install -r requirements.txt
jupyter notebook notebooks/00_Start_Here_Diagnostic.ipynb
```
Also works in VS Code and JupyterLab. Run the first cell of each notebook before anything else, and run cells one by one
(not "Run All"): the flashcard and review tools ask you questions and wait for your answers.
In Google Colab, clone the repository first (`!git clone ...` then `%cd .../English-B2-to-C1`).

## What's inside

| Path | What it is |
|---|---|
| `notebooks/00_Start_Here_Diagnostic.ipynb` | How the course works; diagnostic in **two parallel forms** (5 areas × 10 items); listening and speaking benchmarks |
| `notebooks/01b_Accuracy_Core_Spanish_Speakers.ipynb` | Articles, dependent prepositions, verb patterns, present perfect vs past simple, subjects and word order, email proofreading |
| `notebooks/01_Grammar_Conditionals_Inversion_Clefts.ipynb` | Mixed/inverted conditionals, alternatives to *if*, wishes, negative inversion, cleft sentences |
| `notebooks/02_Grammar_Modals_Passives_Participles.ipynb` | Past modals, reporting passives, causative, participle clauses, emphasis/ellipsis, subjunctive |
| `notebooks/02b_Grammar_Noun_Phrases_Relatives_Future_Hedging.ipynb` | Nominalisation, relative clauses, advanced future forms, the grammar of hedging, mixed-structure text cloze |
| `notebooks/03_Vocabulary_Collocations.ipynb` | Delexical verbs, adjective/adverb collocations, ideas & data, semantic prosody and register, text cloze, B2→C1 upgrades |
| `notebooks/04_Vocabulary_Phrasal_Verbs_Idioms.ipynb` | Particle meanings, register (formal ↔ phrasal), 25 high-frequency idioms, workplace and meeting English |
| `notebooks/05_Word_Formation_Paraphrasing.ipynb` | Prefixes/suffixes, word families, 20 key word transformations, false friends for Spanish speakers |
| `notebooks/06_Listening_Lab.ipynb` | Connected speech, weak/strong forms, micro-dictations, 17 dictations in 8 accents, 5 inference passages (incl. a dialogue), podcast worksheet |
| `notebooks/07_Speaking_Pronunciation_Lab.ipynb` | Functional language and discourse markers, workplace culture (understatement, emails), pronunciation for Spanish speakers (sounds, stress, intonation), feedback loop, 50 prompts |
| `notebooks/08_Flashcards_Spaced_Repetition.ipynb` | Leitner flashcards: 320+ cards in 8 decks + your own deck; 8 new cards/day; productive and receptive modes; Anki export |
| `notebooks/09_Progress_And_Review.ipynb` | Study-hours chart, mixed review, spaced mistake bank, scores by notebook, speaking/listening numbers, C1 checklist |
| `STUDY_PLAN.md` | **16-week plan** (~11 h/week), balanced across input, output, focused study and fluency, with a weekly topic cycle |
| `RESOURCES.md` | Books, dictionaries, podcasts, series, apps, tutors and pronunciation tools |
| `english_tools.py` | The helper toolkit behind the notebooks |
| `progress/` | **Your data** (scores, mistakes, flashcard state, logs). Ignored by git by default; see `.gitignore` to back it up |

## How exercises work

```python
answers = {
    1: "had known",
    2: "should you need",
}
check("g1_cond_inversion", answers)
```
`check()` marks your answers and explains mistakes. It accepts contractions, British and American spelling, and common
variants. Blank items are skipped, so you can do a set in several sittings. Wrong answers go to your **mistake bank**:
`review_mistakes()` brings each one back after 1, 3, 7 and 21 days. `mixed_review()` quizzes you on everything you've
studied, mixed together. For open answers (rewrites), compare with the model answers and re-run with `wrong=[...]` to save
your real mistakes. Answer keys are in `data/exercises/`, so don't look before you answer!

## Toolkit cheat-sheet

| Function | Use |
|---|---|
| `check(set_id, answers, wrong=None)` | mark an exercise |
| `review_mistakes(n)` / `mixed_review(n)` / `log_mistake(wrong, correct, why)` | spaced review; add your own errors |
| `results_summary()` / `diagnostic_profile()` | scores by notebook / diagnostic results |
| `study(decks, new=None, typed=False, reverse=False)` | daily flashcards |
| `add_card(deck, front, back, example)` / `export_anki(deck)` | your own cards / Anki export |
| `dictation(n, accent="uk", chunks=True, rate=0.85)` / `check_dictation(n, text)` | listening dictation with error types |
| `micro(n)` / `listen(n)` / `transcript(n)` | micro-dictations / inference passages |
| `log_listening_miss(category, ...)` / `listening_report()` | track what you mishear |
| `random_prompt(kind)` / `speak_timer(s, prep)` / `four_three_two()` | timed speaking |
| `speech_stats(transcript, seconds)` / `analyse_recording(file)` / `speaking_report()` | fluency numbers |
| `log_study(minutes, skill, activity)` / `weekly_report()` | study hours |

## Extending the course
Exercise content lives in `tools/content/*.py`. Edit it or add a new `nbXX_*.py` module, then rebuild:
```bash
pip install nbformat
python tools/build_notebooks.py
```
Rebuilding regenerates the notebooks and answer keys (your answers typed inside the notebooks are overwritten; `progress/` isn't touched).
