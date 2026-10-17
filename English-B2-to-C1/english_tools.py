"""Helper toolkit for the B2 -> C1 English study notebooks.

Every notebook imports this module. Main functions:
  Exercises   check(), review_mistakes(), mixed_review(), log_mistake(), results_summary()
  Flashcards  study(), list_decks(), add_card(), export_anki()
  Listening   dictation(), check_dictation(), listen(), transcript(), micro(), log_listening_miss(), listening_report()
  Speaking    random_prompt(), speak_timer(), four_three_two(), speech_stats(), analyse_recording(), speaking_report()
  Tracking    log_study(), weekly_report(), diagnostic_profile()
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
MISTAKE_STATE = PROGRESS / "mistake_schedule.json"
STUDY_LOG_CSV = PROGRESS / "study_log.csv"
SPEAKING_LOG_CSV = PROGRESS / "speaking_log.csv"
LISTENING_LOG_CSV = PROGRESS / "listening_misses.csv"
SRS_STATE = PROGRESS / "srs_state.json"

SKILLS = ["grammar", "vocabulary", "listening", "speaking", "reading", "writing", "review"]
MISTAKE_FIELDS = ["when", "set_id", "item", "question", "your_answer", "correct", "why"]


def _today():
    return _dt.date.today()


def _now():
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def _read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")


def _append_csv(path, header, row):
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if new:
            writer.writerow(header)
        writer.writerow(row)


def _read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh))


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
_SPELLING = [  # British -> American spellings, so both are accepted
    (r"\b(\w{2,})is(e|es|ed|ing|ation|ations)\b", r"\1iz\2"),
    (r"\b(\w{2,})our\b", r"\1or"),
    (r"\b(\w+)yse(d|s)?\b", r"\1yze\2"),
    (r"\b(cancel|travel|model|label|signal|fuel)l(ed|ing|er)\b", r"\1\2"),
    (r"\bgruelling\b", "grueling"),
    (r"\bfulfil\b", "fulfill"),
    (r"\b(cent|theat|met|fib)re\b", r"\1er"),
]


def _base_normalise(text):
    text = str(text).strip().lower()
    text = (text.replace("’", "'").replace("‘", "'").replace("´", "'").replace("`", "'")
                .replace("“", '"').replace("”", '"').replace("…", "...")
                .replace("–", "-").replace("—", "-"))
    text = text.strip(" \t\n\"'")
    text = re.sub(r"^\(?([a-d])\)?[.)]?$", r"\1", text)                    # b) (b) b.
    text = re.sub(r"(?<=\w)-(?=\w)", " ", text)                             # worn-out -> worn out
    text = re.sub(r"\b(do|does|did|is|are|was|were|has|have|had|would|could|should|must|need|might)nt\b",
                  r"\1n't", text)                                          # didnt -> didn't
    text = re.sub(r"\bcant\b", "can't", text)
    text = re.sub(r"\bim\b", "i'm", text)
    for pattern, repl in _CONTRACTIONS:
        text = re.sub(pattern, repl, text)
    for pattern, repl in _SPELLING:
        text = re.sub(pattern, repl, text)
    text = re.sub(r"\s*[.?!;:]+\s+", ", ", text)                            # sentence breaks inside answers
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip().rstrip(".!?;:,").strip()
    return text


def _variants(text):
    """All plausible expansions of an answer ('d -> would/had, it's -> it is/has)."""
    forms = {_base_normalise(text)}
    new = set()
    for f in forms:
        if re.search(r"'d\b", f):
            new.update(re.sub(r"'d\b", alt, f) for alt in (" would", " had"))
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
    forms = new | {f.replace(",", "") for f in new}      # commas are rarely what we are testing
    return {re.sub(r"\s+", " ", f).strip() for f in forms}


def is_correct(user, accepted):
    """True if the learner's answer matches any accepted answer."""
    if isinstance(accepted, str):
        accepted = [accepted]
    user_forms = _variants(user)
    return any(user_forms & _variants(acc) for acc in accepted)


# --------------------------------------------------------------------------
# Exercise sets
# --------------------------------------------------------------------------

_SET_CACHE = {}
_SET_FILE = {}


def _load_sets():
    if not _SET_CACHE:
        for path in sorted((DATA / "exercises").glob("*.json")):
            for ex in _read_json(path, []):
                _SET_CACHE[ex["id"]] = ex
                _SET_FILE[ex["id"]] = path.stem
    return _SET_CACHE


def get_set(set_id):
    sets = _load_sets()
    if set_id not in sets:
        raise KeyError(f"Unknown exercise set '{set_id}'. Check the spelling in the cell.")
    return sets[set_id]


def _shown_answer(item):
    """The answer as we display it: 'b) put' for multiple choice, else the model answer."""
    return item["a"][-1] if item.get("options") else item["a"][0]


def check(set_id, answers, wrong=None):
    """Mark `answers` ({item_number: "your answer"}) against exercise `set_id`.

    Blank items are skipped (not counted). For open answers (free rewrites) that don't
    match the model exactly, compare yourself; if yours was wrong, run the cell again with
    wrong=[item numbers] so those items go into your mistake bank.
    Returns (score, total).
    """
    ex = get_set(set_id)
    items = ex["items"]
    diagnostic = set_id.startswith("diag")
    wrong = set(wrong or [])
    if not any(str(v or "").strip() for v in answers.values()):
        print(f"=== {ex['title']} ===\nType your answers between the quotes first, then run this cell again.")
        return 0, 0
    score, total, to_review, blanks = 0, 0, 0, 0
    print(f"=== {ex['title']} ===\n")
    for n, item in enumerate(items, start=1):
        user = str(answers.get(n, "") or "").strip()
        accepted = item["a"]
        open_item = ex.get("type") == "open" or item.get("open", False)
        if not user:
            blanks += 1
            print(f"{n:>2}. --    (skipped)")
            continue
        ok = is_correct(user, accepted) and n not in wrong
        if ok:
            score += 1
            total += 1
            print(f"{n:>2}. OK    {user}")
            continue
        if open_item and n not in wrong:
            to_review += 1
            print(f"{n:>2}. ??    {user}")
            print(f"       model: {accepted[0]}")
            if len(accepted) > 1:
                print(f"       also:  {' / '.join(accepted[1:3])}")
            print(f"       -> Equally correct? Count it. Wrong? Re-run with  wrong=[{n}]  to save it for review.")
        else:
            total += 1
            print(f"{n:>2}. XX    {user}")
            print(f"       correct: {_shown_answer(item) if item.get('options') else ' / '.join(accepted[:4])}")
            if not diagnostic:
                _log_mistake_row(set_id, n, item["q"], user, _shown_answer(item), item.get("why", ""))
        if item.get("why"):
            print(f"       why: {item['why']}")
    print()
    if blanks:
        print(f"({blanks} item(s) left blank - not counted.)")
    if total:
        pct = round(100 * score / total)
        print(f"Score: {score}/{total} ({pct}%)" + (f"  + {to_review} to self-check" if to_review else ""))
        if diagnostic:
            print("(Diagnostic: mistakes are NOT added to your review bank, so the test stays a fair measure.)")
        elif pct >= 85:
            print("Excellent - this structure is becoming automatic. Move on.")
        elif pct >= 65:
            print("Good. Re-read the explanation for the items you missed and retry in a few days.")
        else:
            print("Needs work. Re-study the section, then redo this set in 2-3 days.")
        _append_csv(RESULTS_CSV, ["when", "set_id", "score", "total"], [_now(), set_id, score, total])
    else:
        print(f"{to_review} answer(s) to self-check against the model answers.")
    return score, total


# --------------------------------------------------------------------------
# Mistake bank with spaced review
# --------------------------------------------------------------------------

MISTAKE_INTERVALS = [1, 3, 7, 21]   # days between reviews; retired after len() correct answers on different days


def _log_mistake_row(set_id, item_no, question, your_answer, correct, why=""):
    _append_csv(MISTAKES_CSV, MISTAKE_FIELDS, [_now(), set_id, item_no, question, your_answer, correct, why])
    state = _read_json(MISTAKE_STATE, {})
    state[f"{set_id}#{item_no}"] = {"streak": 0, "due": _today().isoformat(), "last": ""}
    _write_json(MISTAKE_STATE, state)


def log_mistake(wrong, correct, why="", tag="own"):
    """Add one of YOUR OWN mistakes (from a tutor, AI feedback, your recordings) to the review bank.

    log_mistake("I have seen him yesterday", "I saw him yesterday", "finished past time -> past simple")
    """
    rows = [r for r in _read_csv(MISTAKES_CSV) if r["set_id"] == tag]
    n = len(rows) + 1
    _log_mistake_row(tag, n, f"Correct this: \"{wrong}\"", wrong, correct, why)
    print(f"Saved to your mistake bank ({tag} #{n}). It will come back in review_mistakes().")


def _find_logged_item(row):
    ex = _load_sets().get(row["set_id"])
    if ex:
        for it in ex["items"]:
            if it["q"] == row["question"]:
                return it, ex["title"]
    return {"q": row["question"], "a": [row["correct"]], "why": row.get("why", "")}, row["set_id"]


def _ask(item):
    print(item["q"])
    if item.get("options"):
        for letter, opt in zip("abcd", item["options"]):
            print(f"   {letter}) {opt}")
    return input("Your answer (Enter = skip, q = quit): ").strip()


def review_mistakes(n=10, set_prefix=None):
    """Re-quiz past mistakes that are due. Each item comes back after 1, 3, 7 and 21 days
    and is retired only after you get it right on 4 different days."""
    rows = _read_csv(MISTAKES_CSV)
    if not rows:
        print("No mistakes logged yet. Do some exercises first!")
        return
    state = _read_json(MISTAKE_STATE, {})
    latest = {}
    for r in rows:
        latest[f"{r['set_id']}#{r['item']}"] = r
    today = _today().isoformat()
    due = [k for k, r in latest.items()
           if (not set_prefix or r["set_id"].startswith(set_prefix))
           and state.get(k, {}).get("streak", 0) < len(MISTAKE_INTERVALS)
           and state.get(k, {}).get("due", today) <= today]
    active = sum(1 for k in latest if state.get(k, {}).get("streak", 0) < len(MISTAKE_INTERVALS))
    if not due:
        print(f"Nothing due today. {active} item(s) still in your bank - come back tomorrow.")
        return
    keys = random.sample(due, min(n, len(due)))
    right = asked = 0
    try:
        for i, key in enumerate(keys, 1):
            item, title = _find_logged_item(latest[key])
            print(f"\n[{i}/{len(keys)}]  ({title})")
            ans = _ask(item)
            if ans.lower() == "q":
                break
            if not ans:
                continue
            asked += 1
            st = state.get(key, {"streak": 0, "due": today, "last": ""})
            if is_correct(ans, item["a"]):
                right += 1
                if st.get("last") != today:
                    st["streak"] = st.get("streak", 0) + 1
                st["last"] = today
                if st["streak"] >= len(MISTAKE_INTERVALS):
                    print("Correct! Retired - well done.")
                else:
                    days = MISTAKE_INTERVALS[st["streak"]]
                    st["due"] = (_today() + _dt.timedelta(days=days)).isoformat()
                    print(f"Correct! Next check in {days} day(s).")
            else:
                st.update(streak=0, last=today, due=(_today() + _dt.timedelta(days=1)).isoformat())
                print(f"Not quite. Answer: {_shown_answer(item)}")
                if item.get("why"):
                    print(f"Why: {item['why']}")
            state[key] = st
    finally:
        _write_json(MISTAKE_STATE, state)
    print(f"\nSession: {right}/{asked} correct. {active} item(s) in your bank.")


def mixed_review(n=20):
    """Interleaved review of items from ALL sets you've already done (not only mistakes).

    Older sets and sets with lower scores are picked more often. Wrong answers go to the mistake bank.
    """
    results = _read_csv(RESULTS_CSV)
    sets = _load_sets()
    stats = {}
    for r in results:
        if r["set_id"] in sets and not r["set_id"].startswith("diag"):
            pct = int(r["score"]) / max(int(r["total"]), 1)
            stats[r["set_id"]] = (r["when"][:10], pct)
    pool = []
    for sid, (when, pct) in stats.items():
        ex = sets[sid]
        if ex.get("type") == "open":
            continue
        age = max((_today() - _dt.date.fromisoformat(when)).days, 1)
        weight = age * (1.5 - pct)
        for idx, item in enumerate(ex["items"], 1):
            pool.append((weight, sid, idx, item))
    if not pool:
        print("Do a few exercise sets first - mixed review draws on sets you've already attempted.")
        return
    chosen = []
    pool = pool[:]
    while pool and len(chosen) < n:
        pick = random.choices(range(len(pool)), weights=[p[0] for p in pool])[0]
        chosen.append(pool.pop(pick))
    right = asked = 0
    for i, (_, sid, idx, item) in enumerate(chosen, 1):
        print(f"\n[{i}/{len(chosen)}]  ({sets[sid]['title']})")
        ans = _ask(item)
        if ans.lower() == "q":
            break
        if not ans:
            continue
        asked += 1
        if is_correct(ans, item["a"]):
            right += 1
            print("Correct!")
        else:
            print(f"Not quite. Answer: {_shown_answer(item)}")
            if item.get("why"):
                print(f"Why: {item['why']}")
            _log_mistake_row(sid, idx, item["q"], ans, _shown_answer(item), item.get("why", ""))
    print(f"\nMixed review: {right}/{asked} correct.")


def results_summary():
    """Best and latest score for every exercise set, grouped by notebook (including sets not done yet)."""
    sets = _load_sets()
    by_set = {}
    for r in _read_csv(RESULTS_CSV):
        pct = round(100 * int(r["score"]) / max(int(r["total"]), 1))
        by_set.setdefault(r["set_id"], []).append(pct)
    current = None
    done = 0
    for sid, ex in sets.items():
        if _SET_FILE[sid] != current:
            current = _SET_FILE[sid]
            print(f"\n{current}")
        att = by_set.get(sid)
        if att:
            done += 1
            flag = "" if att[-1] >= 85 else "   <- redo"
            print(f"  {sid:<24}{ex['title'][:38]:<40} best {max(att):>3}%  latest {att[-1]:>3}%{flag}")
        else:
            print(f"  {sid:<24}{ex['title'][:38]:<40} not yet")
    print(f"\n{done}/{len(sets)} sets attempted.")


def diagnostic_profile():
    """Your latest diagnostic scores per area, read from your results."""
    latest = {}
    for r in _read_csv(RESULTS_CSV):
        if r["set_id"].startswith("diag"):
            latest[r["set_id"]] = (int(r["score"]), int(r["total"]), r["when"][:10])
    if not latest:
        print("No diagnostic results yet.")
        return {}
    for sid, (s, t, when) in sorted(latest.items()):
        pct = round(100 * s / max(t, 1))
        level = "C1 range" if pct >= 80 else "B2+ (almost there)" if pct >= 60 else "B2 - priority"
        print(f"{sid:<28} {'#' * (pct // 10)}{'.' * (10 - pct // 10)} {pct:>3}%  {level:<20} ({when})")
    return latest


# --------------------------------------------------------------------------
# Spaced-repetition flashcards (Leitner boxes)
# --------------------------------------------------------------------------

INTERVALS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 16, 6: 35}   # box -> days until next review
DAILY_NEW_LIMIT = 8                                   # new cards per day across ALL decks


def list_decks():
    decks = sorted(p.stem for p in (DATA / "decks").glob("*.json"))
    state = _load_srs()
    for d in decks:
        cards = load_deck(d)
        seen = sum(1 for c in cards if _card_key(d, c) in state)
        due = len(_due_cards(d, cards, state))
        print(f"{d:<20} {len(cards):>4} cards   {seen:>4} started   {due:>4} due today")
    print(f"\nNew cards introduced today: {_new_today(state)}/{DAILY_NEW_LIMIT}")
    return decks


def load_deck(name):
    path = DATA / "decks" / f"{name}.json"
    if not path.exists():
        valid = ", ".join(sorted(p.stem for p in (DATA / "decks").glob("*.json")))
        raise FileNotFoundError(f"No deck called '{name}'. Available: {valid}")
    return _read_json(path, [])


def _card_key(deck, card):
    return f"{deck}::{card.get('id') or card['front']}"


def _load_srs():
    return _read_json(SRS_STATE, {})


def _new_today(state):
    meta = state.get("_meta", {})
    return meta.get("new_count", 0) if meta.get("date") == _today().isoformat() else 0


def _due_cards(deck, cards, state):
    today = _today().isoformat()
    return [c for c in cards if _card_key(deck, c) in state and state[_card_key(deck, c)]["due"] <= today]


def study(decks, new=None, max_reviews=40, typed=False, reverse=False):
    """Review due cards and learn new ones.

    decks   : a deck name or a list, e.g. study(["collocations", "my_words"])
    new     : new cards for this session (default: what's left of the daily limit of 8)
    typed   : type the answer (auto-checked) instead of self-grading
    reverse : show the expression, you explain the meaning (use for idioms / false_friends)
    Grades: g = good (knew it), h = hard (knew it with effort), a = again (didn't know).
    """
    if isinstance(decks, str):
        decks = [decks]
    state = _load_srs()
    budget = max(DAILY_NEW_LIMIT - _new_today(state), 0) if new is None else new
    queue, new_cards = [], []
    for deck in decks:
        cards = load_deck(deck)
        due = _due_cards(deck, cards, state)
        queue += [(deck, c) for c in due]
        new_cards += [(deck, c) for c in cards if _card_key(deck, c) not in state]
    random.shuffle(queue)
    queue = queue[:max_reviews]
    if "my_words" in decks:                      # your own cards first
        new_cards.sort(key=lambda dc: dc[0] != "my_words")
    new_cards = new_cards[:budget]
    queue += new_cards
    if not queue:
        print("Nothing due and no new cards left for today. Come back tomorrow!")
        return
    print(f"{len(queue) - len(new_cards)} reviews + {len(new_cards)} new. Grades: g = good, h = hard, a = again, q = quit.\n")
    right = graded = 0
    seen_new = set()
    try:
        i = 0
        while i < len(queue):
            deck, card = queue[i]
            i += 1
            key = _card_key(deck, card)
            prompt, answer = (card["back"], card["front"]) if reverse else (card["front"], card["back"])
            print(f"[{deck}]  {prompt}")
            if typed and not reverse:
                ans = input("> ").strip()
                if ans.lower() == "q":
                    break
                targets = [card["answer"]] if card.get("answer") else card["back"].split(" / ")
                ok = is_correct(ans, targets)
                print("  Correct!" if ok else "  Not quite.")
                grade = "g" if ok else "a"
            else:
                if input("  (think / say it aloud, then Enter) ").strip().lower() == "q":
                    break
            print(f"  => {answer}")
            if card.get("example"):
                print(f"     e.g. {card['example']}")
            if not (typed and not reverse):
                grade = input("  [g]ood / [h]ard / [a]gain: ").strip().lower()[:1]
                if grade == "q":
                    break
                grade = {"y": "g", "n": "a"}.get(grade, grade)
                if grade not in "gha" or not grade:
                    grade = "h"
            if key not in state and key not in seen_new:
                seen_new.add(key)
            box = state.get(key, {}).get("box", 1)
            if grade == "g":
                box = min(box + 1, 6)
            elif grade == "a":
                box = 1
                queue.append((deck, card))        # see it again before the session ends
            graded += 1
            right += grade != "a"
            due_date = _today() + _dt.timedelta(days=INTERVALS[box] if grade != "a" else 0)
            state[key] = {"box": box, "due": due_date.isoformat()}
            print()
    finally:
        count = _new_today(state) + len(seen_new)
        state["_meta"] = {"date": _today().isoformat(), "new_count": count}
        _write_json(SRS_STATE, state)
    print(f"Done: {right}/{graded} known. Progress saved.")


def add_card(deck, front, back, example=""):
    """Add a card to a deck (created if it doesn't exist). Use 'my_words' for your own."""
    path = DATA / "decks" / f"{deck}.json"
    cards = _read_json(path, [])
    if any(c["front"] == front for c in cards):
        print("A card with that front already exists in this deck.")
        return
    cards.append({"front": front, "back": back, "example": example})
    _write_json(path, cards)
    print(f"Added to '{deck}' ({len(cards)} cards).")


def export_anki(deck):
    """Write a tab-separated file you can import into Anki (front, back + example)."""
    out = PROGRESS / f"anki_{deck}.txt"
    with out.open("w", encoding="utf-8") as fh:
        fh.write("#separator:tab\n#html:true\n")
        for c in load_deck(deck):
            back = c["back"] + (f"<br><i>{c['example']}</i>" if c.get("example") else "")
            fh.write(f"{c['front']}\t{back}\n")
    print(f"Exported to {out}")


# --------------------------------------------------------------------------
# Listening: text-to-speech, dictation, passages
# --------------------------------------------------------------------------

ACCENTS = {  # name -> (gTTS domain, edge-tts neural voice)
    "us": ("us", "en-US-GuyNeural"), "com": ("com", "en-US-JennyNeural"),
    "uk": ("co.uk", "en-GB-SoniaNeural"), "co.uk": ("co.uk", "en-GB-RyanNeural"),
    "au": ("com.au", "en-AU-NatashaNeural"), "com.au": ("com.au", "en-AU-WilliamNeural"),
    "ca": ("ca", "en-CA-ClaraNeural"), "ie": ("ie", "en-IE-EmilyNeural"),
    "in": ("co.in", "en-IN-NeerjaNeural"), "co.in": ("co.in", "en-IN-PrabhatNeural"),
    "za": ("co.za", "en-ZA-LeahNeural"), "co.za": ("co.za", "en-ZA-LukeNeural"),
    "ng": ("com.ng", "en-NG-EzinneNeural"), "com.ng": ("com.ng", "en-NG-AbeoNeural"),
}


def _play_file(path, rate=1.0):
    import base64
    from IPython.display import HTML, display
    b64 = base64.b64encode(Path(path).read_bytes()).decode()
    display(HTML(f'<audio controls src="data:audio/mpeg;base64,{b64}" '
                 f'onloadedmetadata="this.playbackRate={rate}"></audio>'))


def _speak(text, slow=False, accent="com", rate=1.0):
    """Play `text` aloud. Engines: edge-tts (neural, best) -> gTTS -> pyttsx3 (offline)."""
    if accent not in ACCENTS:
        raise ValueError(f"Unknown accent {accent!r}. Use one of: {', '.join(ACCENTS)}")
    tld, voice = ACCENTS[accent]
    out = PROGRESS / "_tts.mp3"
    errors = []
    try:
        import asyncio
        import threading
        import edge_tts
        err = []

        def _run():
            try:
                asyncio.run(edge_tts.Communicate(text, voice, rate="-25%" if slow else "+0%").save(str(out)))
            except Exception as e:  # noqa: BLE001
                err.append(e)
        t = threading.Thread(target=_run)
        t.start()
        t.join()
        if err:
            raise err[0]
        _play_file(out, rate)
        return True
    except ImportError:
        pass
    except Exception as e:  # noqa: BLE001
        errors.append(f"edge-tts failed: {e}")
    try:
        from gtts import gTTS
        gTTS(text=text, lang="en", tld=tld, slow=slow).save(str(out))
        _play_file(out, rate)
        return True
    except ImportError:
        pass
    except Exception as e:  # noqa: BLE001
        errors.append(f"gTTS failed: {e}")
    if errors:
        print("\n".join(errors))
        print("Check your internet connection (both engines are online services).")
        return False
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", int(175 * rate * (0.75 if slow else 1)))
        engine.say(text)
        engine.runAndWait()
        print("(Played through pyttsx3 on this computer's speakers.)")
        return True
    except Exception:  # noqa: BLE001
        pass
    print("No text-to-speech engine found. Install one:  pip install edge-tts   (or gTTS / pyttsx3)")
    print("Workaround: ask someone to read the text to you - without looking at it!")
    return False


def _pick(items, number, what):
    if not 1 <= number <= len(items):
        raise ValueError(f"{what} number must be between 1 and {len(items)}.")
    return items[number - 1]


def dictations():
    texts = _read_json(DATA / "dictations.json", [])
    for i, t in enumerate(texts, 1):
        print(f"{i:>2}. [{t['level']}] {t['title']}  ({len(t['text'].split())} words)")
    return texts


def dictation(number, accent="com", rate=1.0, chunks=False, slow=False):
    """Play dictation `number`.

    accent: us, uk, au, ca, ie, in, za, ng (see ACCENTS)
    rate  : playback speed, e.g. 0.85 for a first hard attempt (keeps natural rhythm)
    chunks: True -> one player per phrase, so you can replay phrase by phrase
    """
    t = _pick(_read_json(DATA / "dictations.json", []), number, "Dictation")
    print(f"Dictation {number}: {t['title']}  - listen, pause, and type what you hear.")
    _speak(t["text"], slow=slow, accent=accent, rate=rate)
    if chunks:
        for i, ch in enumerate(re.split(r"(?<=[,;.])\s+", t["text"]), 1):
            print(f"Phrase {i}")
            _speak(ch, accent=accent, rate=rate)


_NUMBERS = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six",
            "7": "seven", "8": "eight", "9": "nine", "10": "ten", "11": "eleven", "12": "twelve",
            "13": "thirteen", "20": "twenty", "30": "thirty", "45": "forty five", "50": "fifty",
            "100": "hundred"}
_WEAK = {"a", "an", "the", "to", "of", "for", "and", "at", "from", "can", "have", "has", "had", "was", "were",
         "been", "do", "does", "you", "your", "them", "him", "her", "that", "than", "some", "but", "or", "are",
         "as", "would", "will", "is", "it", "in", "on", "we", "they", "he", "she", "i", "id", "wed", "youd",
         "its", "thats", "ive", "weve", "theyve", "theyd", "hed", "shed", "ill", "well", "youre", "were", "theyre"}


def _dict_tokens(s):
    s = str(s).lower().replace("’", "'").replace("´", "'")
    for pattern, repl in _SPELLING:
        s = re.sub(pattern, repl, s)
    s = re.sub(r"(\d),(\d)", r"\1\2", s)
    words = []
    for w in re.findall(r"[a-z0-9']+", s):
        words += _NUMBERS.get(w, w).replace("'", "").split()    # apostrophes are spelling, not listening
    return words


def _miss_category(orig, typed):
    o, t = orig.split(), typed.split()
    if o and all(w in _WEAK for w in o) or (not o and all(w in _WEAK for w in t)):
        return "weak form"
    if "".join(o) == "".join(t):
        return "linking / word boundary"
    if len(o) == len(t) == 1 and o[0][:3] == t[0][:3]:
        return "ending (-s / -ed / contraction)"
    return "vocabulary / other"


def check_dictation(number, typed):
    """Word-by-word comparison of your transcript against the original, with error types."""
    if not str(typed).strip():
        print("Type what you heard between the triple quotes first, then run this cell again.")
        return None
    t = _pick(_read_json(DATA / "dictations.json", []), number, "Dictation")
    original = t["text"]
    a, b = _dict_tokens(original), _dict_tokens(typed)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out, cats = [], {}
    errors = 0
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            out.append(" ".join(a[i1:i2]))
            continue
        orig, got = " ".join(a[i1:i2]), " ".join(b[j1:j2])
        errors += max(i2 - i1, j2 - j1)
        cat = _miss_category(orig, got)
        cats[cat] = cats.get(cat, 0) + 1
        out.append(f"[{orig or '+'} -> {got or '_'}]")
        _append_csv(LISTENING_LOG_CSV, ["when", "source", "heard", "actual", "category"],
                    [_now(), f"dictation_{number}", got, orig, cat])
    acc = max(0, round(100 * (1 - errors / max(len(a), 1))))
    print(f"Accuracy: {acc}%   (word errors: {errors} of {len(a)} words)\n")
    print(" ".join(out))
    print("\nOriginal:\n" + original)
    if cats:
        print("\nLikely causes: " + ", ".join(f"{k} x{v}" for k, v in cats.items()))
        print("Then: listen again while reading, and shadow the sentences you missed.")
    _append_csv(RESULTS_CSV, ["when", "set_id", "score", "total"], [_now(), f"dictation_{number}", acc, 100])
    return acc


def _passages():
    return _read_json(DATA / "listening_passages.json", [])


def listen(number, accent="com", rate=1.0):
    """Play listening passage `number` (don't read the transcript yet!)."""
    p = _pick(_passages(), number, "Passage")
    print(f"Passage {number}: {p['title']}  ({p['type']})")
    if p.get("voices"):   # dialogue: one voice per speaker
        for line in p["text"].split("\n"):
            speaker, _, said = line.partition(": ")
            print(f"{speaker}:", end=" ")
            if not _speak(said, accent=p["voices"].get(speaker, accent), rate=rate):
                break
    else:
        _speak(p["text"], accent=accent, rate=rate)


def transcript(number):
    p = _pick(_passages(), number, "Passage")
    print(p["title"] + "\n")
    print(p["text"])


def micro(number, accent="com", rate=1.0):
    """Play micro-dictation sentence `number` (weak forms and fast speech)."""
    s = _pick(_read_json(DATA / "micro_dictations.json", []), number, "Sentence")
    print(f"Sentence {number}")
    _speak(s, accent=accent, rate=rate)


def log_listening_miss(category, heard="", actual="", source=""):
    """Log something you misheard in authentic audio. category: weak form, linking / word boundary,
    ending (-s / -ed / contraction), vocabulary / other, speed, accent."""
    _append_csv(LISTENING_LOG_CSV, ["when", "source", "heard", "actual", "category"],
                [_now(), source, heard, actual, category])
    print("Logged.")


def listening_report():
    rows = _read_csv(LISTENING_LOG_CSV)
    if not rows:
        print("No listening misses logged yet.")
        return
    counts = {}
    for r in rows:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    total = sum(counts.values())
    print("What you mishear most (train this in Notebook 06 section 1):\n")
    for cat, c in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"{cat:<34} {'#' * round(30 * c / total):<30} {c}")


# --------------------------------------------------------------------------
# Speaking
# --------------------------------------------------------------------------

def speak_timer(seconds=60, prep=15):
    """Countdown: `prep` seconds to plan, then `seconds` to speak (record yourself!)."""
    from IPython.display import clear_output
    try:
        for label, dur in (("PREPARE", prep), ("SPEAK", seconds)):
            for left in range(dur, 0, -1):
                clear_output(wait=True)
                half = "   (halfway)" if label == "SPEAK" and left == dur // 2 else ""
                print(f"{label}: {left:>3}s{half}")
                time.sleep(1)
        clear_output(wait=True)
        print("STOP. Now listen to your recording and fill in the self-assessment.")
    except KeyboardInterrupt:
        clear_output(wait=True)
        print("Timer stopped.")


def four_three_two(prep=60):
    """The 4-3-2 fluency technique: same topic for 4, 3 and 2 minutes, a new (imagined) listener each time."""
    listeners = ["a friend who knows nothing about the topic", "a colleague in a hurry", "your manager, in an elevator"]
    for i, (secs, who) in enumerate(zip((240, 180, 120), listeners), 1):
        input(f"Round {i}: {secs // 60} minutes, speaking to {who}. Press Enter to start...")
        speak_timer(seconds=secs, prep=prep if i == 1 else 0)
    print("Done! Round 3 should have felt noticeably more fluent. Run speech_stats() on your last recording.")


def random_prompt(kind=None):
    prompts = _read_json(DATA / "speaking_prompts.json", [])
    pool = [p for p in prompts if kind is None or p["kind"] == kind]
    if not pool:
        raise ValueError(f"kind must be one of: {', '.join(sorted({p['kind'] for p in prompts}))}")
    p = random.choice(pool)
    print(f"[{p['kind']}]  {p['prompt']}")
    if p.get("hints"):
        print("  Try to use: " + " | ".join(p["hints"]))
    return p


_FILLERS = r"\b(eh|um+|uh+|er+m?|hmm+|este|o sea|pues|like|you know|i mean)\b"


def speech_stats(transcript_text, seconds, targets=(), label=""):
    """Fluency numbers for one recording. Transcribe your recording word for word (phone dictation,
    analyse_recording(), or by hand - keep the 'um's!) and pass its length in seconds."""
    text = str(transcript_text)
    words = re.findall(r"[A-Za-z']+", text)
    minutes = max(seconds, 1) / 60
    fillers = len(re.findall(_FILLERS, text.lower()))
    types = {w.lower() for w in words}
    used = [t for t in targets if t.lower() in text.lower()]
    wpm = round(len(words) / minutes)
    print(f"Words per minute : {wpm}   (C1 conversation is typically ~120-160)")
    print(f"Fillers / minute : {fillers / minutes:.1f}   (aim to bring this down week by week)")
    print(f"Different words  : {len(types)} of {len(words)} ({round(100 * len(types) / max(len(words), 1))}%)")
    if targets:
        print(f"Target chunks used: {len(used)}/{len(targets)}  {used}")
    _append_csv(SPEAKING_LOG_CSV, ["when", "label", "seconds", "wpm", "fillers_per_min", "type_token", "targets_used"],
                [_now(), label, seconds, wpm, round(fillers / minutes, 1),
                 round(len(types) / max(len(words), 1), 2), len(used)])
    return {"wpm": wpm, "fillers_per_min": round(fillers / minutes, 1)}


def analyse_recording(path, model_size="small", label=""):
    """Transcribe an audio file with faster-whisper (pip install faster-whisper) and compute fluency stats.
    Words the machine got wrong may be pronunciation problems - check them on YouGlish."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("pip install faster-whisper   (or transcribe by hand and use speech_stats())")
        return None
    model = WhisperModel(model_size, compute_type="int8")
    segs, _ = model.transcribe(str(path), language="en", word_timestamps=True,
                               initial_prompt="Umm, let me think, like, hmm... uh, so, er, yeah.")
    words = [w for s in segs for w in s.words]
    if not words:
        print("No speech found.")
        return None
    dur = words[-1].end - words[0].start
    pauses = sum(1 for a, b in zip(words, words[1:]) if b.start - a.end > 1.0)
    text = "".join(w.word for w in words).strip()
    print(text + "\n")
    print(f"Silent pauses > 1 s: {pauses}")
    speech_stats(text, dur, label=label or Path(path).name)
    return text


def speaking_report():
    rows = _read_csv(SPEAKING_LOG_CSV)
    if not rows:
        print("No recordings analysed yet. Use speech_stats() after each recording.")
        return
    print(f"{'when':<18}{'label':<28}{'wpm':>6}{'fillers/min':>13}")
    for r in rows[-12:]:
        print(f"{r['when']:<18}{r['label'][:26]:<28}{r['wpm']:>6}{r['fillers_per_min']:>13}")


# --------------------------------------------------------------------------
# Study log
# --------------------------------------------------------------------------

def _week(d):
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def log_study(minutes, skill, activity="", notes="", date=None):
    """Record a study session. skill: grammar, vocabulary, listening, speaking, reading, writing, review.
    date: 'YYYY-MM-DD' (default today)."""
    skill = skill.lower().strip()
    if skill not in SKILLS:
        raise ValueError(f"skill must be one of {SKILLS}")
    date = date or _today().isoformat()
    try:
        _dt.date.fromisoformat(date)
    except ValueError:
        raise ValueError("date must look like '2026-10-01' (year-month-day).") from None
    _append_csv(STUDY_LOG_CSV, ["date", "minutes", "skill", "activity", "notes"],
                [date, round(float(minutes), 1), skill, activity, notes])
    print(f"Logged {minutes} min of {skill} on {date}.")


def weekly_report(target_hours=10, weeks=8, plot=True):
    """Hours per ISO week and per skill, compared with your weekly target."""
    rows = _read_csv(STUDY_LOG_CSV)
    if not rows:
        print("No study sessions logged yet. Use log_study(minutes, skill, activity).")
        return
    table = {}
    for r in rows:
        try:
            wk = _week(_dt.date.fromisoformat(r["date"]))
            table.setdefault(wk, {s: 0 for s in SKILLS})
            table[wk][r["skill"]] += float(r["minutes"]) / 60
        except (ValueError, KeyError):
            print(f"(skipping unreadable line: {dict(r)})")
    wks = [_week(_today() - _dt.timedelta(weeks=k)) for k in range(weeks - 1, -1, -1)]
    for wk in wks:
        table.setdefault(wk, {s: 0 for s in SKILLS})
    print(f"{'week':<10}" + "".join(f"{s[:5]:>7}" for s in SKILLS) + f"{'TOTAL':>8}")
    for wk in wks:
        tot = sum(table[wk].values())
        flag = "  OK" if tot >= target_hours else f"  (-{target_hours - tot:.1f}h)"
        print(f"{wk:<10}" + "".join(f"{table[wk][s]:>7.1f}" for s in SKILLS) + f"{tot:>8.1f}{flag}")
    total_h = sum(sum(v.values()) for v in table.values())
    print(f"\nAll-time: {total_h:.1f} hours = {min(100, round(100 * total_h / 200))}% of the ~200 guided learning hours")
    print("Cambridge English estimates per CEFR level. (Hours are only a guide - the diagnostic and your")
    print("speaking numbers measure actual progress.)")
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
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.show()
