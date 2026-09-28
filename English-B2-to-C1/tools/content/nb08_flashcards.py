NOTEBOOK = {
    "file": "08_Flashcards_Spaced_Repetition.ipynb",
    "title": "08 - Daily Flashcards (Spaced Repetition)",
    "cells": [
        ("md", """
**10-15 minutes every day, no exceptions.** This is the single habit that will grow your active vocabulary the most.

### How it works (Leitner system)
Every card lives in a "box". **g**ood moves it up a box (it comes back later), **h**ard keeps it in the same box,
**a**gain sends it back to box 1 - and you'll see it again before the session ends.

| Box | Next review |
|---|---|
| 1 | today (again) |
| 2 | in 1 day |
| 3 | in 3 days |
| 4 | in 1 week |
| 5 | in ~2 weeks |
| 6 | in ~5 weeks |

### Rules
* **8 new cards per day in total** (across all decks) - that's the default. More sounds tempting, but by week 3 you'd face
  150+ reviews a day and quit. At 8 a day you'll have met all 320+ built-in cards in about six weeks - after that,
  your own `my_words` cards take over.
* **Say the answer aloud**, then say the example sentence aloud.
* Be honest. "Almost" = **a**gain.
* **Direction matters:**
  - *Productive* (definition -> expression) for what you want to **use**: collocations, connectors, functional chunks, workplace.
  - *Receptive* (`reverse=True`: expression -> meaning) for what you mainly need to **understand**: idioms, false friends.

### Decks
"""),
        ("code", """
list_decks();
"""),
        ("md", """
| Deck | Content | Direction |
|---|---|---|
| `my_words` | **your own** cards (from conversations, podcasts, mistakes) - the most valuable deck | both |
| `functional_chunks` | phrases for agreeing, hedging, buying time, interrupting, emails | productive |
| `collocations` | high-frequency C1 collocations (verb+noun, adj+noun, adverb+adj, work) | productive |
| `connectors` | discourse markers and linkers, with register notes | productive |
| `phrasal_verbs` | the phrasal verbs you need to understand natives and sound natural | productive |
| `advanced_vocab` | C1 words with their patterns (*concede that...*, *foster creativity*) | productive |
| `workplace` | meeting and office English (*circle back, heads-up, drop the ball*) | productive |
| `idioms` | modern, frequently used idioms | **receptive** |
| `false_friends` | traps for Spanish speakers (*actually, eventually, compromise, billion...*) | **receptive** |

## Today's session
"""),
        ("code", """
study(["my_words", "functional_chunks", "collocations"])      # think, press Enter, grade g / h / a
"""),
        ("code", """
study(["idioms", "false_friends"], reverse=True)              # see the expression, explain the meaning
"""),
        ("code", """
# study("connectors", typed=True)     # type the answer - auto-checked
"""),
        ("md", """
## Weekly rotation
The daily limit of 8 new cards is shared, so just rotate which decks you open:
* **Mon/Thu:** my_words + functional_chunks + collocations
* **Tue/Fri:** my_words + phrasal_verbs + workplace
* **Wed/Sat:** my_words + advanced_vocab + connectors; idioms/false_friends with `reverse=True`
* **Sun:** reviews only: `study([...all decks...], new=0)`

## Add your own cards
Whenever you meet a useful expression (in a podcast, a series, a conversation, or a mistake you made), add it.
The best cards have a **clear prompt** (ideally the example sentence with a gap), the **exact chunk**, and **your own example**.
"""),
        ("code", """
# add_card(deck, front, back, example)
# add_card("my_words",
#          "The mayor promised to t_____ the housing problem head-on. (deal with, determined)",
#          "tackle",
#          "The new mayor has promised to tackle the housing problem head-on.")
"""),
        ("md", """
## Export to Anki (optional)
If you prefer to review on your phone, export any deck and import it into **Anki** (free on Android/desktop, AnkiMobile on iOS):
*File -> Import*.
"""),
        ("code", """
# export_anki("collocations")      # creates progress/anki_collocations.txt
"""),
        ("code", """
# log_study(15, "vocabulary", "SRS daily")
"""),
    ],
}
