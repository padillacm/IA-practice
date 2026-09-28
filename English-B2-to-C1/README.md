# English B2 → C1: Self-Study Course in Jupyter Notebooks

An interactive, 16-week course to go from a shaky B2 to a solid, usable **C1**, with extra focus on
**advanced grammar, vocabulary/collocations, listening and speaking**. Everything is in English.

## Quick start

```bash
cd English-B2-to-C1
pip install -r requirements.txt
jupyter notebook notebooks/00_Start_Here_Diagnostic.ipynb
```
Also works in VS Code, JupyterLab or any Jupyter environment. Run the first cell of each notebook before anything else.

## What's inside

| Path | What it is |
|---|---|
| `notebooks/00_Start_Here_Diagnostic.ipynb` | How the course works + a 40-item diagnostic + a listening check + self-rating |
| `notebooks/01_Grammar_Conditionals_Inversion_Clefts.ipynb` | Mixed/inverted conditionals, alternatives to *if*, wishes, negative inversion, cleft sentences |
| `notebooks/02_Grammar_Modals_Passives_Participles.ipynb` | Past modals, reporting passives, causative, participle clauses, emphasis/ellipsis, subjunctive |
| `notebooks/03_Vocabulary_Collocations.ipynb` | Delexical verbs, adjective/adverb collocations, language for ideas & data, B2→C1 upgrades |
| `notebooks/04_Vocabulary_Phrasal_Verbs_Idioms.ipynb` | Particle meanings, register (formal ↔ phrasal), 25 high-frequency idioms |
| `notebooks/05_Word_Formation_Paraphrasing.ipynb` | Prefixes/suffixes, 20 key word transformations, false friends for Spanish speakers |
| `notebooks/06_Listening_Lab.ipynb` | Connected speech decoding, 12 text-to-speech dictations (6 accents), inference passages, podcast worksheet |
| `notebooks/07_Speaking_Pronunciation_Lab.ipynb` | Functional language, diplomacy, pronunciation for Spanish speakers, shadowing, timed speaking (28 prompts) |
| `notebooks/08_Flashcards_Spaced_Repetition.ipynb` | Leitner-system flashcards: 240+ cards in 6 decks + your own deck, Anki export |
| `notebooks/09_Progress_And_Review.ipynb` | Study-hours tracker with chart, mistake bank review, scores, C1 can-do checklist |
| `STUDY_PLAN.md` | **16-week plan** (10–12 h/week), with a daily routine and 4 phases |
| `RESOURCES.md` | Books, dictionaries, podcasts, series, apps and tutors |
| `english_tools.py` | The helper toolkit behind the notebooks |
| `progress/` | **Your data** (scores, mistakes, flashcard state, study log). Commit it if you want to back it up |

## How exercises work

```python
answers = {
    1: "had known",
    2: "should you need",
}
check("g1_cond_inversion", answers)
```
`check()` marks your answers (it accepts contractions and common variants), explains mistakes and saves them to your
**mistake bank**. `review_mistakes()` quizzes you on them again until you've got each one right twice.
Answer keys are in `data/exercises/`, so don't look before you answer!

## Toolkit cheat-sheet

| Function | Use |
|---|---|
| `check(set_id, answers)` | mark an exercise |
| `review_mistakes(n=10, set_prefix=None)` | re-quiz past mistakes |
| `study(deck, new=10, typed=False)` | daily flashcards |
| `add_card(deck, front, back, example)` / `export_anki(deck)` | your own cards / Anki export |
| `dictation(n, accent="co.uk")` / `check_dictation(n, text)` | listening dictation |
| `listen(n)` / `transcript(n)` | inference passages |
| `random_prompt(kind)` / `speak_timer(seconds, prep)` | timed speaking |
| `log_study(minutes, skill, activity)` / `weekly_report()` / `results_summary()` | tracking |

## Extending the course
Exercise content lives in `tools/content/*.py`. Edit it or add a new `nbXX_*.py` module, then rebuild:
```bash
pip install nbformat
python tools/build_notebooks.py
```
Rebuilding regenerates the notebooks and answer keys. Your answers inside the notebooks will be overwritten, but `progress/` isn't touched.
