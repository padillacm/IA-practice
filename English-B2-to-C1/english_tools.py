"""Helper toolkit for the B2 -> C1 English study notebooks.

Every notebook imports this module. It provides:
  * check()            - auto-mark an exercise set and log the result
  * review_mistakes()  - re-quiz yourself on items you got wrong before
  * study()            - spaced-repetition flashcards (Leitner system)
  * dictation() / check_dictation() - listening practice with text-to-speech
  * speak_timer() / random_prompt() - timed speaking practice
  * log_study() / weekly_report()   - study-hours tracker
All your data lives in the  progress/  folder next to this file.
"""

import csv
import datetime as _dt
import difflib
import json
import random
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
PROGRESS = ROOT / "progress"
PROGRESS.mkdir(exist_ok=True)

RESULTS_CSV = PROGRESS / "results.csv"
MISTAKES_CSV = PROGRESS / "mistakes.csv"
STUDY_LOG_CSV = PROGRESS / "study_log.csv"
SRS_STATE = PROGRESS / "srs_state.json"

SKILLS = ["grammar", "vocabulary", "listening", "speaking", "reading", "writing", "review"]


# --------------------------------------------------------------------------
# Answer normalisation
# --------------------------------------------------------------------------

_CONTRACTIONS = [
    (r"\bwon't\b", "will not"),
    (r"\bshan't\b", "shall not"),
    (r"\bcan't\b", "cannot"),
    (r"\bcan not\b", "cannot"),
    (r"\bain't\b", "is not"),
    (r"n't\b", " not"),
    (r"'re\b", " are"),
    (r"'ve\b", " have"),
    (r"'ll\b", " will"),
    (r"\bi'm\b", "i am"),
    (r"\blet's\b", "let us"),
]
_S_PRONOUNS = r"\b(it|he|she|that|there|what|who|here|where|how|this)'s\b"


def _base_normalise(text):
    text = str(text).strip().lower()
    text = (text.replace("’", "'").replace("‘", "'")
                .replace("“", '"').replace("”", '"')
                .replace("–", "-").replace("—", "-"))
    for pattern, repl in _CONTRACTIONS:
        text = re.sub(pattern, repl, text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip().rstrip(".!?;:").strip()
    return text


def _variants(text):
    """All plausible expansions of an answer ('d -> would/had, it's -> it is/has)."""
    base = _base_normalise(text)
    forms = {base}
    for src, alts in ((r"'d\b", [" would", " had"]),):
        new = set()
        for f in forms:
            if re.search(src, f):
                new.update(re.sub(src, a, f) for a in alts)
            else:
                new.add(f)
        forms = new
    new = set()
    for f in forms:
        if re.search(_S_PRONOUNS, f):
            new.add(re.sub(_S_PRONOUNS, r"\1 is", f))
            new.add(re.sub(_S_PRONOUNS, r"\1 has", f))
        else:
            new.add(f)
    forms = new
    # commas are rarely what we are testing
    forms |= {f.replace(",", "") for f in forms}
    return {re.sub(r"\s+", " ", f).strip() for f in forms}


def is_correct(user, accepted):
    """True if the learner's answer matches any accepted answer."""
    if isinstance(accepted, str):
        accepted = [accepted]
    user_forms = _variants(user)
    for acc in accepted:
        if user_forms & _variants(acc):
            return True
    return False


# --------------------------------------------------------------------------
# Exercise sets
# --------------------------------------------------------------------------

_SET_CACHE = {}


def _load_sets():
    if not _SET_CACHE:
        for path in sorted((DATA / "exercises").glob("*.json")):
            for ex in json.loads(path.read_text(encoding="utf-8")):
                _SET_CACHE[ex["id"]] = ex
    return _SET_CACHE


def get_set(set_id):
    sets = _load_sets()
    if set_id not in sets:
        raise KeyError(f"Unknown exercise set '{set_id}'.")
    return sets[set_id]


def _append_csv(path, header, row):
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if new:
            writer.writerow(header)
        writer.writerow(row)


def _now():
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def check(set_id, answers, log=True):
    """Mark `answers` ({item_number: "your answer"}) against exercise `set_id`.

    Returns (score, total). Items of type 'open' (free rewrites) are shown with
    a model answer for self-assessment when they don't match exactly.
    """
    ex = get_set(set_id)
    items = ex["items"]
    score, total, to_review = 0, 0, 0
    print(f"=== {ex['title']} ===\n")
    for n, item in enumerate(items, start=1):
        user = str(answers.get(n, "") or "").strip()
        accepted = item["a"] if isinstance(item["a"], list) else [item["a"]]
        open_item = ex.get("type") == "open" or item.get("open", False)
        if not user:
            print(f"{n:>2}. -- (blank)   model answer: {accepted[0]}")
            total += 1
            continue
        if is_correct(user, accepted):
            score += 1
            total += 1
            print(f"{n:>2}. OK    {user}")
        elif open_item:
            to_review += 1
            print(f"{n:>2}. ??    {user}")
            print(f"       model: {accepted[0]}")
            print("       -> Compare carefully. If yours is equally correct, count it.")
        else:
            total += 1
            print(f"{n:>2}. XX    {user}")
            print(f"       correct: {' / '.join(accepted)}")
            if log:
                _append_csv(MISTAKES_CSV,
                            ["when", "set_id", "item", "question", "your_answer", "correct", "why"],
                            [_now(), set_id, n, item["q"], user, accepted[0], item.get("why", "")])
        if item.get("why") and not is_correct(user, accepted):
            print(f"       why: {item['why']}")
    print()
    if total:
        pct = round(100 * score / total)
        print(f"Score: {score}/{total} ({pct}%)" + (f"  + {to_review} to self-check" if to_review else ""))
        if pct >= 85:
            print("Excellent - this structure is becoming automatic. Move on.")
        elif pct >= 65:
            print("Good. Re-read the explanation for the items you missed and retry tomorrow.")
        else:
            print("Needs work. Re-study the section, then redo this set in 2-3 days.")
        if log:
            _append_csv(RESULTS_CSV, ["when", "set_id", "score", "total"], [_now(), set_id, score, total])
    else:
        print(f"{to_review} answers to self-check against the model answers.")
    return score, total


def review_mistakes(n=10, set_prefix=None):
    """Interactive re-quiz of items you got wrong in the past (spaced review).

    Items you answer correctly twice in a row are retired from the pool.
    """
    if not MISTAKES_CSV.exists():
        print("No mistakes logged yet. Do some exercises first!")
        return
    with MISTAKES_CSV.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    retired_path = PROGRESS / "retired_mistakes.json"
    retired = json.loads(retired_path.read_text()) if retired_path.exists() else {}
    pool = {}
    for r in rows:
        key = f"{r['set_id']}#{r['item']}"
        if retired.get(key, 0) >= 2:
            continue
        if set_prefix and not r["set_id"].startswith(set_prefix):
            continue
        pool[key] = r
    if not pool:
        print("Nothing to review - all past mistakes have been retired. Well done!")
        return
    keys = random.sample(list(pool), min(n, len(pool)))
    right = 0
    for i, key in enumerate(keys, 1):
        r = pool[key]
        item = get_set(r["set_id"])["items"][int(r["item"]) - 1]
        print(f"\n[{i}/{len(keys)}]  ({get_set(r['set_id'])['title']})")
        print(item["q"])
        if item.get("options"):
            for letter, opt in zip("abcd", item["options"]):
                print(f"   {letter}) {opt}")
        ans = input("Your answer (or 'q' to quit): ").strip()
        if ans.lower() == "q":
            break
        if is_correct(ans, item["a"]):
            right += 1
            retired[key] = retired.get(key, 0) + 1
            print("Correct!" + ("  (retired)" if retired[key] >= 2 else ""))
        else:
            retired[key] = 0
            print(f"Not quite. Answer: {item['a'] if isinstance(item['a'], str) else item['a'][0]}")
            if item.get("why"):
                print(f"Why: {item['why']}")
    retired_path.write_text(json.dumps(retired, indent=1))
    print(f"\nSession: {right}/{len(keys)} correct.")


def results_summary():
    """Print your best and latest score for every exercise set you have done."""
    if not RESULTS_CSV.exists():
        print("No results yet.")
        return
    with RESULTS_CSV.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    by_set = {}
    for r in rows:
        pct = round(100 * int(r["score"]) / max(int(r["total"]), 1))
        by_set.setdefault(r["set_id"], []).append((r["when"], pct))
    print(f"{'set':<28}{'attempts':>9}{'best':>7}{'latest':>8}")
    for sid in sorted(by_set):
        attempts = by_set[sid]
        print(f"{sid:<28}{len(attempts):>9}{max(p for _, p in attempts):>6}%{attempts[-1][1]:>7}%")


# --------------------------------------------------------------------------
# Spaced-repetition flashcards (Leitner boxes)
# --------------------------------------------------------------------------

INTERVALS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 16, 6: 35}   # box -> days until next review


def list_decks():
    decks = sorted(p.stem for p in (DATA / "decks").glob("*.json"))
    state = _load_srs()
    for d in decks:
        cards = load_deck(d)
        seen = sum(1 for c in cards if f"{d}::{c['front']}" in state)
        due = len(_due_cards(d, cards, state))
        print(f"{d:<22} {len(cards):>4} cards   {seen:>4} started   {due:>4} due today")
    return decks


def load_deck(name):
    return json.loads((DATA / "decks" / f"{name}.json").read_text(encoding="utf-8"))


def _load_srs():
    return json.loads(SRS_STATE.read_text()) if SRS_STATE.exists() else {}


def _save_srs(state):
    SRS_STATE.write_text(json.dumps(state, indent=1))


def _due_cards(deck, cards, state):
    today = _dt.date.today().isoformat()
    return [c for c in cards
            if f"{deck}::{c['front']}" in state and state[f"{deck}::{c['front']}"]["due"] <= today]


def study(deck, new=10, max_reviews=40, typed=False):
    """Review due cards and learn `new` new ones from `deck`.

    typed=False: think of the answer, press Enter, then grade yourself (y/n).
    typed=True : type the answer and it is auto-checked.
    """
    cards = load_deck(deck)
    state = _load_srs()
    due = _due_cards(deck, cards, state)
    random.shuffle(due)
    unseen = [c for c in cards if f"{deck}::{c['front']}" not in state][:new]
    queue = due[:max_reviews] + unseen
    if not queue:
        print("Nothing due. Come back tomorrow or raise `new`.")
        return
    print(f"{len(due[:max_reviews])} reviews + {len(unseen)} new cards. Type 'q' to stop.\n")
    right = graded = 0
    for i, card in enumerate(queue, 1):
        key = f"{deck}::{card['front']}"
        print(f"[{i}/{len(queue)}]  {card['front']}")
        if typed:
            ans = input("> ").strip()
            if ans.lower() == "q":
                break
            ok = is_correct(ans, card["back"].split(" / "))
            print("  Correct!" if ok else "  Not quite.")
        else:
            if input("  (Enter to reveal) ").strip().lower() == "q":
                break
        print(f"  => {card['back']}")
        if card.get("example"):
            print(f"     e.g. {card['example']}")
        if not typed:
            grade = input("  Did you know it? [y/n] ").strip().lower()
            if grade == "q":
                break
            ok = grade.startswith("y")
        box = state.get(key, {}).get("box", 1)
        box = min(box + 1, 6) if ok else 1
        right += ok
        graded += 1
        due_date = _dt.date.today() + _dt.timedelta(days=INTERVALS[box])
        state[key] = {"box": box, "due": due_date.isoformat()}
        print()
    _save_srs(state)
    print(f"Done: {right}/{graded} known. Progress saved.")


def add_card(deck, front, back, example=""):
    """Add a card to a deck (created if it doesn't exist). Use 'my_words' for your own."""
    path = DATA / "decks" / f"{deck}.json"
    cards = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    if any(c["front"] == front for c in cards):
        print("A card with that front already exists in this deck.")
        return
    cards.append({"front": front, "back": back, "example": example})
    path.write_text(json.dumps(cards, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Added to '{deck}' ({len(cards)} cards).")


def export_anki(deck):
    """Write a tab-separated file you can import into Anki (front, back, example)."""
    out = PROGRESS / f"anki_{deck}.txt"
    with out.open("w", encoding="utf-8") as fh:
        for c in load_deck(deck):
            back = c["back"] + (f"<br><i>{c['example']}</i>" if c.get("example") else "")
            fh.write(f"{c['front']}\t{back}\n")
    print(f"Exported to {out}")


# --------------------------------------------------------------------------
# Listening: dictation with text-to-speech
# --------------------------------------------------------------------------

def _speak(text, slow=False, accent="com"):
    """Play `text` aloud. Tries gTTS (online, natural) then pyttsx3 (offline)."""
    try:
        from gtts import gTTS
        from IPython.display import Audio, display
        out = PROGRESS / "_tts.mp3"
        gTTS(text=text, lang="en", tld=accent, slow=slow).save(str(out))
        display(Audio(str(out), autoplay=False))
        return True
    except Exception:
        pass
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 130 if slow else 175)
        engine.say(text)
        engine.runAndWait()
        return True
    except Exception:
        pass
    print("No text-to-speech engine found. Install one:  pip install gTTS   (or pyttsx3)")
    print("Workaround: ask a friend/AI voice tool to read the text, or paste it into")
    print("Google Translate and press the speaker icon - without looking at it!")
    return False


def dictations():
    texts = json.loads((DATA / "dictations.json").read_text(encoding="utf-8"))
    for i, t in enumerate(texts, 1):
        print(f"{i:>2}. [{t['level']}] {t['title']}  ({len(t['text'].split())} words)")
    return texts


def dictation(number, slow=False, accent="com"):
    """Play dictation `number`. accent: 'com' (US), 'co.uk' (UK), 'com.au', 'ca', 'co.in', 'ie'."""
    texts = json.loads((DATA / "dictations.json").read_text(encoding="utf-8"))
    t = texts[number - 1]
    print(f"Dictation {number}: {t['title']}  - listen, pause, and type what you hear.")
    _speak(t["text"], slow=slow, accent=accent)


def check_dictation(number, typed):
    """Word-by-word comparison of your transcript against the original."""
    texts = json.loads((DATA / "dictations.json").read_text(encoding="utf-8"))
    original = texts[number - 1]["text"]
    norm = lambda s: re.findall(r"[a-z0-9']+", _base_normalise(s))  # noqa: E731
    a, b = norm(original), norm(typed)
    sm = difflib.SequenceMatcher(None, a, b)
    out, errors = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            out.append(" ".join(a[i1:i2]))
        else:
            out.append(f"[{' '.join(a[i1:i2]) or '+'} -> {' '.join(b[j1:j2]) or '_'}]")
            errors.append((" ".join(a[i1:i2]), " ".join(b[j1:j2])))
    acc = round(100 * sm.ratio())
    print(f"Accuracy: {acc}%\n")
    print(" ".join(out))
    print("\nOriginal:\n" + original)
    if errors:
        print("\nLook at WHY you missed each one: weak form? linking? unknown word? speed?")
    _append_csv(RESULTS_CSV, ["when", "set_id", "score", "total"], [_now(), f"dictation_{number}", acc, 100])
    return acc


def _passages():
    return json.loads((DATA / "listening_passages.json").read_text(encoding="utf-8"))


def listen(number, slow=False, accent="com"):
    """Play listening passage `number` (don't read the transcript yet!)."""
    p = _passages()[number - 1]
    print(f"Passage {number}: {p['title']}  ({p['type']})")
    _speak(p["text"], slow=slow, accent=accent)


def transcript(number):
    p = _passages()[number - 1]
    print(p["title"] + "\n")
    print(p["text"])


# --------------------------------------------------------------------------
# Speaking
# --------------------------------------------------------------------------

def speak_timer(seconds=60, prep=15):
    """Countdown: `prep` seconds to plan, then `seconds` to speak (record yourself!)."""
    from IPython.display import clear_output
    for label, dur in (("PREPARE", prep), ("SPEAK", seconds)):
        for left in range(dur, 0, -1):
            clear_output(wait=True)
            print(f"{label}: {left:>3}s")
            time.sleep(1)
    clear_output(wait=True)
    print("STOP. Now listen to your recording and fill in the self-assessment.")


def random_prompt(kind=None):
    prompts = json.loads((DATA / "speaking_prompts.json").read_text(encoding="utf-8"))
    pool = [p for p in prompts if kind is None or p["kind"] == kind]
    p = random.choice(pool)
    print(f"[{p['kind']}]  {p['prompt']}")
    if p.get("hints"):
        print("  Try to use: " + " | ".join(p["hints"]))
    return p


# --------------------------------------------------------------------------
# Study log
# --------------------------------------------------------------------------

def log_study(minutes, skill, activity="", notes="", date=None):
    """Record a study session. skill: grammar, vocabulary, listening, speaking, reading, writing, review."""
    skill = skill.lower().strip()
    if skill not in SKILLS:
        raise ValueError(f"skill must be one of {SKILLS}")
    date = date or _dt.date.today().isoformat()
    _append_csv(STUDY_LOG_CSV, ["date", "minutes", "skill", "activity", "notes"],
                [date, int(minutes), skill, activity, notes])
    print(f"Logged {minutes} min of {skill} on {date}.")


def weekly_report(target_hours=10, weeks=8, plot=True):
    """Hours per ISO week and per skill, compared with your weekly target."""
    if not STUDY_LOG_CSV.exists():
        print("No study sessions logged yet. Use log_study(minutes, skill, activity).")
        return
    with STUDY_LOG_CSV.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    table = {}
    for r in rows:
        y, w, _ = _dt.date.fromisoformat(r["date"]).isocalendar()
        wk = f"{y}-W{w:02d}"
        table.setdefault(wk, {s: 0 for s in SKILLS})
        table[wk][r["skill"]] += int(r["minutes"]) / 60
    wks = sorted(table)[-weeks:]
    print(f"{'week':<10}" + "".join(f"{s[:5]:>7}" for s in SKILLS) + f"{'TOTAL':>8}")
    for wk in wks:
        tot = sum(table[wk].values())
        flag = "  OK" if tot >= target_hours else f"  (-{target_hours - tot:.1f}h)"
        print(f"{wk:<10}" + "".join(f"{table[wk][s]:>7.1f}" for s in SKILLS) + f"{tot:>8.1f}{flag}")
    total_h = sum(sum(v.values()) for v in table.values())
    print(f"\nAll-time: {total_h:.1f} hours. Cambridge English estimates ~200 guided learning hours per CEFR level (B2 -> C1).")
    print(f"You are about {min(100, round(100 * total_h / 200))}% of the way there.")
    if plot:
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("(pip install matplotlib to see the chart)")
            return
        fig, ax = plt.subplots(figsize=(9, 4))
        bottom = [0] * len(wks)
        for s in SKILLS:
            vals = [table[w][s] for w in wks]
            ax.bar(wks, vals, bottom=bottom, label=s)
            bottom = [b + v for b, v in zip(bottom, vals)]
        ax.axhline(target_hours, color="black", linestyle="--", linewidth=1, label="target")
        ax.set_ylabel("hours")
        ax.set_title("Study hours per week")
        ax.legend(ncol=4, fontsize=8, frameon=False)
        ax.spines[["top", "right"]].set_visible(False)
        plt.tight_layout()
        plt.show()
