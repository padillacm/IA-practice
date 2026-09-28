NOTEBOOK = {
    "file": "09_Progress_And_Review.ipynb",
    "title": "09 - Progress Tracker, Mixed Review and C1 Checklist",
    "cells": [
        ("md", """
**Three times a week (10-15 min):** mixed review + due mistakes (sections 3-4).
**Every Sunday (30-45 min):** log time, weekly report, speaking and listening numbers, plan next week.
**Every 4 weeks:** diagnostic (Notebook 00, alternating Forms A/B), C1 checklist, re-record your benchmark prompt.

> Run the cells one by one (not "Run All"): the review tools ask you questions and wait for your answers.
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
## 3. Mixed review (interleaving)
Questions from **all** the sets you've already done - not only your mistakes - mixed across notebooks.
Older sets and sets with lower scores come up more often. This is what stops you forgetting the conditionals from week 1
by week 12. Do it 3 times a week from week 3.
"""),
        ("code", """
mixed_review(n=20)
"""),
        ("md", """
## 4. Mistake bank
Every wrong answer from `check()`, `mixed_review()` and your own `log_mistake()` entries comes back after **1, 3, 7 and 21 days**,
and is retired only after you get it right on **four different days**. Filter by notebook with `set_prefix`:
`"a1"` (accuracy), `"g1"`, `"g2"`, `"g3"` (grammar), `"v3"`, `"v4"`, `"v5"` (vocabulary), `"l6"`, `"s7"`, `"own"` (your own).
"""),
        ("code", """
review_mistakes(n=15)            # or review_mistakes(10, set_prefix="own")
"""),
        ("code", """
# Add mistakes from tutors, AI feedback or your own recordings:
# log_mistake("It depends of the price", "It depends on the price", "depend ON")
"""),
        ("md", "## 5. Exercise scores by notebook (redo anything under 85%)"),
        ("code", """
results_summary()
"""),
        ("md", "## 6. Speaking and listening numbers"),
        ("code", """
speaking_report()     # words per minute and fillers per minute over time (from speech_stats)
"""),
        ("code", """
listening_report()    # what you mishear most (from check_dictation and log_listening_miss)
"""),
        ("md", "## 7. Diagnostic results"),
        ("code", """
diagnostic_profile()
"""),
        ("md", """
### Progress table (fill in every 4 weeks)

| Week | Form | Grammar | Accuracy | Colloc. | Phrasal/idioms | Word form. | Dictation % | Unseen audio % | Words/min | Fillers/min | Errors/100 words |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | A | | | | | | | | | | |
| 4 | B | | | | | | | | | | |
| 8 | A | | | | | | | | | | |
| 12 | B | | | | | | | | | | |
| 16 | A | | | | | | | | | | |

## 8. Monthly: C1 can-do checklist
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
- [ ] I can summarise something I heard or read for someone else (mediation).
- [ ] I can hedge, soften and disagree diplomatically.
- [ ] I can rephrase smoothly when I can't find a word, and most listeners don't notice.

**Grammar and vocabulary**
- [ ] I consistently maintain a high degree of grammatical accuracy; errors are rare and hard to spot.
- [ ] Articles, prepositions and present perfect vs past simple are no longer a problem for me.
- [ ] I use conditionals, inversion, cleft sentences, past modals and participle clauses naturally.
- [ ] I have a broad lexical repertoire and good command of collocations and idiomatic expressions.
- [ ] I can switch between formal and informal register (Latin verbs vs phrasal verbs).

## 9. Weekly reflection
**This week's topic** (see the topic cycle in STUDY_PLAN.md):

**What went well?**

**What was hard?**

**3 expressions I learnt and actually used:**

**Next week's focus:**
"""),
    ],
}
