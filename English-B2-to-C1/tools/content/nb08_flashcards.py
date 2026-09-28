NOTEBOOK = {
    "file": "08_Flashcards_Spaced_Repetition.ipynb",
    "title": "08 - Daily Flashcards (Spaced Repetition)",
    "cells": [
        ("md", """
**15 minutes every day, no exceptions.** This is the single habit that will grow your active vocabulary the most.

### How it works (Leitner system)
Every card lives in a "box". Get it right and it moves up a box and comes back later; get it wrong and it goes back to box 1.

| Box | Next review |
|---|---|
| 1 | today (again) |
| 2 | in 1 day |
| 3 | in 3 days |
| 4 | in 1 week |
| 5 | in ~2 weeks |
| 6 | in ~5 weeks |

This follows the *forgetting curve* (you'll hear about it in the Notebook 06 lecture): you review each item just before you'd forget it.

### Rules
* The **front** shows a definition or a gap; you produce the **English expression**. Producing (not just recognising) is what builds speaking vocabulary.
* **Say the answer aloud**, then say the example sentence aloud.
* Be honest with `y/n`. "Almost" = **n**.
* 10 new cards a day is plenty (that's ~1,100 new expressions in 16 weeks).

### Decks included
"""),
        ("code", """
list_decks();
"""),
        ("md", """
| Deck | Content |
|---|---|
| `collocations` | high-frequency C1 collocations (verb+noun, adj+noun, adverb+adj) |
| `phrasal_verbs` | the phrasal verbs you need to understand natives and sound natural |
| `idioms` | modern, frequently used idioms |
| `advanced_vocab` | C1 words for discussing ideas, work and society |
| `connectors` | discourse markers and linkers for speaking and writing |
| `false_friends` | traps for Spanish speakers |
| `my_words` | **your own** cards (created with `add_card`) - the most valuable deck |

## Today's session
"""),
        ("code", """
study("collocations", new=10)          # think, press Enter, grade yourself y/n
"""),
        ("code", """
study("phrasal_verbs", new=5, typed=True)   # typed=True: type the answer, auto-checked
"""),
        ("md", """
## Rotation suggestion
* **Mon/Thu:** collocations + advanced_vocab
* **Tue/Fri:** phrasal_verbs + idioms
* **Wed/Sat:** connectors + false_friends + my_words
* **Sun:** only due reviews (`new=0`) across all decks

## Add your own cards
Whenever you meet a useful expression (in a podcast, a series, a conversation, or a mistake you made), add it.
The best cards have a **clear prompt**, the **exact chunk**, and **your own example**.
"""),
        ("code", """
# add_card(deck, front, back, example)
add_card("my_words",
         "to deal with a difficult problem in a determined way (verb + noun)",
         "tackle a problem",
         "The new mayor has promised to tackle the housing problem head-on.")
"""),
        ("md", """
## Export to Anki (optional)
If you prefer to review on your phone, export any deck to a CSV file and import it into **Anki** (free on Android/desktop,
AnkiMobile on iOS): *File -> Import*, fields separated by tab.
"""),
        ("code", """
# export_anki("collocations")      # creates progress/anki_collocations.txt
"""),
        ("code", """
# log_study(15, "vocabulary", "SRS daily")
"""),
    ],
}
