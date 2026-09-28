NOTEBOOK = {
    "file": "09_Progress_And_Review.ipynb",
    "title": "09 - Progress Tracker, Mistake Review and C1 Checklist",
    "cells": [
        ("md", """
Use this notebook **every Sunday** (about 30-45 minutes):
1. Log any sessions you forgot during the week.
2. Look at your weekly report - did you hit your target (10+ hours)?
3. Review your mistake bank.
4. Check your exercise scores and plan next week's redos.
5. Once a month: update the C1 can-do checklist and retake the diagnostic (Notebook 00).
"""),
        ("md", """
## 1. Log your study time
Skills: `grammar`, `vocabulary`, `listening`, `speaking`, `reading`, `writing`, `review`.
Tip: add a `log_study(...)` call at the end of every session - it takes 5 seconds.
"""),
        ("code", """
# log_study(minutes, skill, activity="", notes="", date="YYYY-MM-DD")
# log_study(90, "listening", "Hidden Brain episode + worksheet", "hard to follow the guest's accent")
# log_study(30, "speaking", "italki lesson", date="2026-10-01")
"""),
        ("md", "## 2. Weekly report"),
        ("code", """
weekly_report(target_hours=10)
"""),
        ("md", """
## 3. Mistake bank review
Every wrong answer from every `check()` is saved in `progress/mistakes.csv`. This quiz asks them again;
an item is **retired** after you get it right twice in a row. Aim to keep the bank small!

Filter by notebook with `set_prefix`: `"g1"`, `"g2"` (grammar), `"v3"`, `"v4"`, `"v5"` (vocabulary), `"l6"`, `"s7"`, `"diag"`.
"""),
        ("code", """
review_mistakes(n=15)            # or review_mistakes(10, set_prefix="g1")
"""),
        ("md", "## 4. Exercise scores (best and latest attempt)"),
        ("code", """
results_summary()
"""),
        ("md", """
**Redo rule:** any set with a *latest* score below 85% -> redo it this week (clear your answers first).

## 5. Monthly: C1 can-do checklist
Based on the CEFR C1 descriptors. Edit this cell once a month: `[ ]` -> `[x]` when you can do it **comfortably**.

**Listening**
- [ ] I can follow extended speech even when it is not clearly structured and relationships are only implied.
- [ ] I can understand TV series and films without subtitles, with only occasional difficulty.
- [ ] I can follow fast conversations between several native speakers.
- [ ] I can recognise a wide range of idioms and colloquialisms and appreciate register shifts.
- [ ] I can understand at least three different accents (e.g. US, UK, Australian/Irish/Indian).
- [ ] I can pick up attitude, irony and implied meaning.

**Speaking**
- [ ] I can express myself fluently and spontaneously without much obvious searching for expressions.
- [ ] I can use language flexibly and effectively for social and professional purposes.
- [ ] I can formulate ideas and opinions with precision and relate my contribution skilfully to others'.
- [ ] I can present clear, detailed descriptions of complex subjects, developing points and rounding off with a conclusion.
- [ ] I can hedge, soften and disagree diplomatically.
- [ ] I can rephrase smoothly when I can't find a word, and most listeners don't notice.

**Grammar and vocabulary**
- [ ] I consistently maintain a high degree of grammatical accuracy; errors are rare and hard to spot.
- [ ] I use conditionals, inversion, cleft sentences, past modals and participle clauses naturally.
- [ ] I have a broad lexical repertoire and good command of collocations and idiomatic expressions.
- [ ] I can switch between formal and informal register (Latin verbs vs phrasal verbs).

## 6. Diagnostic history
Record your diagnostic scores (Notebook 00) every 4 weeks:

| Week | Grammar | Collocations | Phrasal/idioms | Word formation | Dictation % |
|---|---|---|---|---|---|
| 0 | | | | | |
| 4 | | | | | |
| 8 | | | | | |
| 12 | | | | | |
| 16 | | | | | |

## 7. Weekly reflection
**What went well this week?**

**What was hard?**

**3 expressions I learnt and actually used:**

**Next week's focus:**
"""),
    ],
}
