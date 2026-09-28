NOTEBOOK = {
    "file": "07_Speaking_Pronunciation_Lab.ipynb",
    "title": "07 - Speaking and Pronunciation Lab",
    "cells": [
        ("md", """
### What changes from B2 to C1 in speaking

| B2 | C1 |
|---|---|
| Can keep going, but with noticeable pauses to search for words | Speaks **fluently and spontaneously**; rarely has to search for expressions |
| Uses a limited set of linkers (*and, but, because, so*) | Uses a **wide range of connectors and discourse markers** |
| States opinions directly | **Nuances** opinions: hedging, softening, conceding |
| Gets stuck when a word is missing | **Rephrases** smoothly (*"it's a kind of..."*, *"what I mean is..."*) |
| Pronunciation clear; accent influenced by L1 but rarely affects intelligibility | Can **vary intonation and stress** to express finer shades of meaning |

You can't become fluent by studying speaking - you need **hours of speaking with feedback**. This notebook gives you:
1. functional language and discourse markers - practised, not just listed;
2. workplace and cultural English (diplomacy, British understatement, emails);
3. pronunciation work targeted at Spanish speakers, including stress and intonation;
4. a **feedback loop**: record -> transcribe -> measure -> correct -> log -> re-record.
"""),
        # ------------------------------------------------------------------ 1
        ("md", """
---
## 1. Functional language bank

Learn these as **chunks** - say them aloud until they come out automatically. They're also in the `functional_chunks` deck.

**Giving opinions with nuance**
*As I see it, ... / If you ask me, ... / I'd argue that... / My take on it is that... / I'm inclined to think that... /
I tend to feel that... / I'm fairly confident that... / For me, the key issue is...*

**Hedging and softening** (essential in British and international workplaces; US colleagues are often more direct, but hedging is never wrong)
*It could be argued that... / To some extent... / There's a case for... / I'm not entirely sure that... /
It might be worth considering... / That's not necessarily the case. / It seems to me that... / I may be wrong, but...*

**Agreeing and disagreeing diplomatically**
*I couldn't agree more (strong - only when you really agree). / That's a fair point (a concession, not full agreement). /
I see where you're coming from, but... / I take your point, but... / I'm not sure I'd go that far. /
I'd see it slightly differently. / That's true up to a point.*
> *With respect, ...* (and even more *with the greatest respect*) signals **strong** disagreement in British English and can
> sound irritated. In most meetings, *I see it slightly differently* is safer.

**Speculating**
*I'd imagine that... / Chances are... / It's bound to... / I wouldn't be surprised if... / There's a good chance that... /
It's highly unlikely that... / In all likelihood...*

**Buying time** (natural fillers instead of silence)
*Let me think... / How can I put this? / Well, it depends... / I've never really thought about it, but... /
The thing is, ... / What I'm trying to say is... / Good question - let me think about how best to put this.*
> Replace Spanish fillers (*eh, este, o sea, pues*) with English ones: *um / uh* (AmE), *erm / er* (BrE), *well, so, I mean,
> you know, sort of / kind of*. *Este...* is the one that gives Latin American speakers away most.
> *That's a good question* is heavily overused in presentations - vary it.

**Rephrasing when you don't know a word**
*It's a kind of... / It's the thing you use to... / What do you call it... / Let me put it another way. / In other words, ... /
What I mean is...*

**Structuring a longer turn**
*There are a couple of reasons for this. First of all, ... / On top of that, ... / Another thing is... / That said, ... /
On the other hand, ... / All in all, ... / So, to sum up, ... / Coming back to your question, ...*

**Emphasising**
*What really matters is... / The point is... / The last thing we need is... / I do think that... / By far the biggest problem is...*

**Spoken discourse markers and backchannels** (what keeps a conversation natural)
*Mind you, ... (= but consider this) / Then again, ... / To be fair, ... / As I say, ... / Going back to what you said... /
Anyway, ... / Fair enough. / Tell me about it! / Really? How come? / Fair point, but... / I know what you mean.*
"""),
        ("ex", {
            "id": "s7_markers",
            "title": "Choose the discourse marker",
            "instructions": "Write the missing word(s) in each mini-dialogue.",
            "items": [
                {"q": "The flat is expensive. ______ you, it's the only one near the station.", "a": ["mind"]},
                {"q": "He can be quite rude. To be ______, he did apologise afterwards.", "a": ["fair"]},
                {"q": "So, going ______ to what I was saying about the budget...", "a": ["back"]},
                {"q": "As I ______, the deadline is fixed - we can't move it.", "a": ["say", "said"]},
                {"q": "A: 'The traffic this morning was awful.'  B: 'Tell me ______ it!'", "a": ["about"]},
                {"q": "A: 'I'd rather not talk about it.'  B: 'Fair ______.'", "a": ["enough"]},
                {"q": "A: 'I'm leaving the company.'  B: 'Really? How ______?'", "a": ["come"]},
                {"q": "It's a great city to live in. Then ______, the winters are terrible.", "a": ["again"]},
                {"q": "Anyway, that's ______ the point. What I wanted to ask was...", "a": ["beside", "not"]},
                {"q": "I know ______ you mean - I had exactly the same problem.", "a": ["what"]},
            ],
        }),
        ("ex", {
            "id": "s7_upgrade",
            "title": "Make it sound C1",
            "type": "open",
            "instructions": "Rewrite each B2-style sentence so that it sounds more nuanced, diplomatic or natural. Compare with the models.",
            "items": [
                {"q": "I think that's wrong.", "a": ["I'm not sure that's quite right.", "I'm not entirely convinced that's the case.", "I see it a bit differently, actually."]},
                {"q": "Your idea is bad.", "a": ["I like where you're going with this, but I'm not sure it'd work in practice.", "I have a few reservations about that.", "I can see a couple of potential issues with that."]},
                {"q": "I agree.", "a": ["Exactly - that's what I was thinking.", "Yes, I think that's right.", "I couldn't agree more."]},
                {"q": "Maybe it will rain.", "a": ["It might well rain.", "I wouldn't be surprised if it rained.", "I've got a feeling it's going to rain."]},
                {"q": "I don't know the word... eh... the thing for opening wine.", "a": ["What do you call it... the thing you use to get the cork out of a wine bottle?", "You know, the gadget with a spiral bit that you twist into the cork."]},
                {"q": "You are late again. This is a problem.", "a": ["I've noticed you've been running late quite a lot recently - is everything OK?", "I just wanted to mention timekeeping - it's started to affect the team. Is there anything getting in the way?"]},
                {"q": "The report has many mistakes.", "a": ["The report needs another proofread - I've flagged quite a few errors.", "I think the report could do with another pass before it goes out."]},
                {"q": "I want a raise.", "a": ["Could we find some time to talk about my salary?", "I'd like to discuss the possibility of a raise (BrE: pay rise), based on what I've delivered this year."]},
                {"q": "Send me the report.", "a": ["Could you send me the report when you get a chance?", "Would you mind sending over the report?"]},
                {"q": "No, we can't do that.", "a": ["I'm afraid that's not something we can do at the moment.", "Unfortunately, that won't be possible - but what we could do is..."]},
                {"q": "I didn't finish the task.", "a": ["I'm running a bit behind on that - I'll have it to you by tomorrow morning.", "That's taken longer than expected; can I get it to you by Thursday?"]},
                {"q": "You didn't understand my email.", "a": ["I don't think I explained that very clearly - let me clarify.", "Sorry, I think my email may have been a bit confusing."]},
            ],
        }),
        ("ex", {
            "id": "s7_diplomatic",
            "title": "Choose the most natural professional response",
            "instructions": "Choose the response a skilled C1 speaker would most likely use. Careful: some wrong options are typical Spanish-speaker calques.",
            "items": [
                {"q": "A colleague proposes an unrealistic deadline.", "options": ["That might be a bit tight - could we walk through the timeline together?", "I'm afraid that deadline is simply impossible.", "With the greatest respect, that's not realistic."]},
                {"q": "Your manager asks your opinion on a plan you don't like.", "options": ["I can see the logic behind it, but I do have a couple of concerns.", "Honestly? I don't think it's a good plan.", "It's very interesting."]},
                {"q": "You didn't understand what someone said in a meeting.", "options": ["Sorry, I didn't quite catch that - could you say it again?", "Can you repeat, please?", "Sorry, what?"]},
                {"q": "You need more time to answer a difficult question.", "options": ["Good question - give me a second to think about that.", "I don't know, sorry.", "Wait, wait..."]},
                {"q": "You want to interrupt politely.", "options": ["Sorry to jump in - could I just add something here?", "Sorry, but I must interrupt you.", "Excuse me, I want to say something."]},
                {"q": "Someone makes a good point that changes your mind.", "options": ["Actually, that's a fair point - I hadn't looked at it that way.", "OK, you are right and I was wrong.", "Maybe. We'll see."]},
                {"q": "You need a file from a colleague by Friday (email).", "options": ["Would you be able to send it over by Friday?", "Send me the file on Friday, please.", "I need the file for Friday."]},
                {"q": "You're asked to take on extra work you don't have time for.", "options": ["I'd love to help, but I don't have the bandwidth this week - could it wait until Monday?", "No, I can't. I'm very busy.", "Impossible, I have too much work."]},
                {"q": "On a video call, the other person's audio drops out.", "options": ["Sorry, you cut out for a second - could you repeat the last bit?", "I don't hear you.", "Your connection is bad."]},
            ],
        }),
        ("md", """
**Why the other options fail:** *Can you repeat, please?* is a calque of *¿Puede repetir?* · *I need it **for** Friday* is a calque
of *para el viernes* (English: **by** Friday) · *I must interrupt you* sounds like a court order ·
*It's very interesting* is British code for "I don't think much of it" (see below) · *With the greatest respect* = "you're wrong".
"""),
        # ------------------------------------------------------------------ 2
        ("md", """
---
## 2. Culture at work: understatement, directness and emails

### Decoding British understatement
British professionals soften criticism so much that the real message can be missed. This is a well-known (and slightly
humorous) generalisation - not every Brit talks like this - but you **will** meet all of these phrases.

| They say... | They usually mean... | You might hear... |
|---|---|---|
| "That's quite good." | It's OK, but not great. | "That's very good." |
| "Not bad." / "Not bad at all." | That's good, even very good. | "It's mediocre." |
| "With the greatest respect..." | I think you're wrong (and I'm irritated). | "They respect me." |
| "That's a very brave proposal." | That's a risky / crazy idea. | "They admire my courage." |
| "Very interesting." | I don't agree / I don't think much of it. | "They're impressed." |
| "I'll bear it in mind." | I probably won't do anything about it. | "They'll consider it seriously." |
| "I was a bit disappointed that..." | I'm really annoyed that... | "It doesn't really matter." |
| "Perhaps you could consider..." / "I would suggest..." | Do this. | "It's optional." |
| "Just a few minor comments." | Please rewrite large parts of this. | "It's nearly finished." |
| "By the way..." / "Incidentally..." | This is actually the main point. | "This isn't important." |
| "It's not ideal." | It's a serious problem. | "It's a small issue." |
| "I hear what you're saying." | I disagree and don't want to discuss it further. | "They agree with me." |
| "You must come round for dinner some time." | A friendly gesture, not a real invitation (yet). | "When shall I come?" |

**Watch *quite*:** in British English, *quite* + a gradable adjective **reduces** it (*quite good* = fairly good); with an
extreme adjective it means *completely* (*quite right, quite impossible*). In American English, *quite good* usually means *very good*.

### ...and in American workplaces

| They say... | They usually mean... |
|---|---|
| "How are you?" / "How's it going?" | Hello. (Answer "Good, thanks - you?", not a health report.) |
| "Let me push back on that a little." | I disagree. (Normal and not aggressive in US meetings.) |
| "Let's circle back on this." | Not now - and possibly never. |
| "We should grab coffee sometime." | Friendly; a real plan only if a date is suggested. |
| "Great job!" / "Awesome!" | Fine, thanks. (American praise is generous; don't over-read it.) |
| "I hear you." | I understand your point (not necessarily agreement). |

**For Spanish speakers:** Spanish is often more direct in requests (*"Mándame el informe"* translated literally sounds like an
order). In English, turn imperatives into questions: *Could you...? / Would you mind...? / Would it be possible to...?*
And remember that in US meetings silence is read as agreement - say clearly if you disagree.

### Email English: avoid these Spanish calques

| Calque (Spanish origin) | Natural English |
|---|---|
| "Dear Mr. Juan," (*Estimado Sr. Juan*) | "Dear Mr Pérez," (formal) / "Hi Juan," (normal internal email) |
| "Cordial greetings," (*Saludos cordiales* as an opener) | "Hi all," / "Hello everyone," |
| "I send you the file." (*Le envío...*) | "Please find the file attached." (formal) / "I've attached the file." / "Here's the file." |
| "I remain attentive to your comments." (*Quedo atento/a*) | "I look forward to hearing from you." / "Let me know if you have any questions." |
| "I stay pending." (*Quedo pendiente*) | "I'll wait to hear from you." / "I'll keep an eye out for it." |
| "Please, can you send me...?" | "Could you please send me...?" / "Would you mind sending me...?" |
| "I need it for Friday." | "I need it **by** Friday." |
| "I have a doubt about..." (*una duda*) | "I have a question about..." |
| "We are in contact." (*Estamos en contacto*) | "Speak soon." / "Let's keep in touch." |

**Passive-aggressive email phrases you'll receive:** *"Per my last email..."* = I already told you. *"Just a gentle reminder..."*
= You're late. *"Going forward..."* = Don't do that again. *"As discussed..."* = You agreed to this - don't deny it.
"""),
        # ------------------------------------------------------------------ 3
        ("md", """
---
## 3. Pronunciation for Spanish speakers

Focus on **intelligibility and naturalness**, not a "perfect" accent. English has ~12 vowels + 8 diphthongs (Spanish has 5).

| Issue | Spanish tendency | Practise |
|---|---|---|
| **/iː/ - /ɪ/** | one *i* | *sheep/ship, leave/live, feel/fill, bean/bin* |
| **/æ/ - /ʌ/ - /ɑː/** | all become Spanish *a* | *cat - cut - cart, hat - hut - heart, cap - cup - carp*. /æ/ jaw open and spread; /ʌ/ short, relaxed, central; /ɑː/ long, back |
| **/ɜː/** | *e/o/a* + r; *work* = *walk* | *work/walk, first/fast, heard/hard, bird/bored* - lips neutral, tongue in the middle, long |
| **/ʊ/ - /uː/, /ɒ/ - /ɔː/** | one *u*, one *o* | *full/fool, look/Luke; cot/caught* (UK) |
| **Diphthongs /eɪ/ /əʊ/** | pure *e*, *o* | *let/late, get/gate; no, go, phone, won't/want* |
| **Schwa /ə/** | pronouncing every vowel fully | the most common sound in English: *a*bout, doct*o*r, *to*day, comf*or*t*a*ble |
| **Aspiration of /p t k/** | no puff of air, so *pig* sounds like *big* | a puff of air at the start of stressed syllables: *pin, time, come, today*. Hold a paper in front of your mouth: it moves on *pin*, not on *spin* |
| **Initial s + consonant** | adding "e": *"espeak"* | *speak, student, Spain, school, strong* - start with a hissing /s/ |
| **/s/ - /z/** | no separate /z/ | *rice/rise, peace/peas, loose/lose, price/prize*; buzz in *is, was, easy, busy, because* |
| **Final -s** | dropped, or always /s/ | /s/ after voiceless (*cats*), /z/ after voiced (*dogs, plays*), /ɪz/ after s z ʃ ʒ tʃ dʒ (*buses, watches*) |
| **-ed endings** | always /ed/ | /t/ after voiceless p k f s ʃ tʃ θ (*worked*); /d/ after voiced (*played*); /ɪd/ only after /t d/ (*wanted*) |
| **Final consonants / voicing** | dropped or devoiced | *asked* /ɑːskt/, *months*; lengthen the vowel before voiced finals: *bet/bed, back/bag, safe/save* |
| **/ŋ/** | *-ing* -> [in] or [iŋɡ] | *sin/sing, thin/thing, win/wing*; *singer* (no /ɡ/) vs *finger* (/ɡ/) |
| **Final /m/ /n/** | merged | *team/teen, some/sun/sung* |
| **/b/ vs /v/** | same sound | /v/ = **upper** teeth lightly on the lower lip, with voice. /b/ = both lips fully closed, then released. The soft Spanish *b/v* of *la vaca* is neither - make /b/ a full stop |
| **/θ/ /ð/** | LatAm: /t/, /s/, /f/; Spain: /d/ for /ð/ | Spain: use your *z* in *cero* for /θ/. Everyone: the soft *d* of *nada / cada* is English /ð/ - use it at the start of words too: *this, the, they* |
| **/ʃ/ - /tʃ/** | one sound (varies by country) | *share/chair, sheep/cheap, wash/watch, cash/catch* |
| **/h/** | Spanish *j* /x/ (too strong) | *house, hotel, behind* - just a soft breath |
| **/dʒ/ - /j/**, **/w/** | mixing; *would* -> "gwud" | *jet/yet, jail/Yale, juice/use; west/guest, wood/good* |
| **/ʒ/** | /s/ or /j/ | *measure, usually, decision* (the Rioplatense *yo* [ʒo] is this sound) |
| **Dark L** | clear Spanish *l* everywhere | after vowels, raise the back of the tongue: *feel, all, milk, people, world* |
| **/r/** | trilled or tapped | tongue doesn't touch the roof of the mouth; UK: silent before consonants and at word end (*car, park*) |
| **Word stress** | wrong syllable (esp. cognates) | *deVELop, PHOtograph, phoTOgrapher, eCOnomy, deMOcracy* |
| **Sentence stress & rhythm** | every syllable equal | English is **stress-timed**: stress content words, reduce the rest: *I WANT to GO to the SHOP* |
| **Nuclear / contrastive stress** | last word by default | stress the **new or contrasted** word: *I asked for **RED** wine, not white* / *I **DID** send it* |
| **Intonation range** | narrow - can sound bored or abrupt | wider pitch jump on the key word; see the table below |
"""),
        ("ex", {
            "id": "s7_ed_endings",
            "title": "-ed endings",
            "instructions": "How is the -ed ending pronounced? Write t, d or id. Say each word aloud before answering.",
            "items": [
                {"q": "worked", "a": ["t", "/t/"]},
                {"q": "played", "a": ["d", "/d/"]},
                {"q": "wanted", "a": ["id", "/id/", "ɪd", "/ɪd/", "əd", "/əd/"]},
                {"q": "decided", "a": ["id", "/id/", "ɪd", "/ɪd/", "əd", "/əd/"]},
                {"q": "laughed", "a": ["t", "/t/"]},
                {"q": "changed", "a": ["d", "/d/"]},
                {"q": "stopped", "a": ["t", "/t/"]},
                {"q": "needed", "a": ["id", "/id/", "ɪd", "/ɪd/", "əd", "/əd/"]},
                {"q": "watched", "a": ["t", "/t/"]},
                {"q": "cleaned", "a": ["d", "/d/"]},
                {"q": "finished", "a": ["t", "/t/"]},
                {"q": "visited", "a": ["id", "/id/", "ɪd", "/ɪd/", "əd", "/əd/"]},
                {"q": "raised", "a": ["d", "/d/"]},
                {"q": "missed", "a": ["t", "/t/"]},
                {"q": "judged", "a": ["d", "/d/"]},
                {"q": "naked (adjective - an exception!)", "a": ["id", "/id/", "ɪd", "/ɪd/", "əd", "/əd/"]},
                {"q": "learned (adjective: 'a learned professor' = very educated)", "a": ["id", "/id/", "ɪd", "/ɪd/", "əd", "/əd/"]},
                {"q": "used (in 'I'm used to it')", "a": ["t", "/t/"]},
            ],
        }),
        ("ex", {
            "id": "s7_s_endings",
            "title": "-s endings",
            "instructions": "How is the -s ending pronounced? Write s, z or iz. Say it aloud first.",
            "items": [
                {"q": "cats", "a": ["s", "/s/"]},
                {"q": "dogs", "a": ["z", "/z/"]},
                {"q": "watches", "a": ["iz", "/iz/", "ɪz", "/ɪz/", "əz", "/əz/"]},
                {"q": "plays", "a": ["z", "/z/"]},
                {"q": "laughs", "a": ["s", "/s/"]},
                {"q": "buses", "a": ["iz", "/iz/", "ɪz", "/ɪz/", "əz", "/əz/"]},
                {"q": "needs", "a": ["z", "/z/"]},
                {"q": "months", "a": ["s", "/s/"]},
                {"q": "changes", "a": ["iz", "/iz/", "ɪz", "/ɪz/", "əz", "/əz/"]},
                {"q": "Laura's (possessive)", "a": ["z", "/z/"]},
                {"q": "Mike's (possessive)", "a": ["s", "/s/"]},
                {"q": "rises", "a": ["iz", "/iz/", "ɪz", "/ɪz/", "əz", "/əz/"]},
            ],
        }),
        ("ex", {
            "id": "s7_word_stress",
            "title": "Word stress",
            "instructions": "Which syllable is stressed? Write the number (1 = first syllable). Check tricky ones in the Cambridge Dictionary and listen.",
            "items": [
                {"q": "pho-to-graph", "a": ["1"]},
                {"q": "pho-to-gra-pher", "a": ["2"]},
                {"q": "pho-to-gra-phic", "a": ["3"]},
                {"q": "e-co-no-my", "a": ["2"]},
                {"q": "e-co-no-mic", "a": ["3"]},
                {"q": "de-ve-lop", "a": ["2"]},
                {"q": "com-for-ta-ble (usually said with 3 syllables: COMF-ta-ble)", "a": ["1"]},
                {"q": "ve-ge-ta-ble (usually 3 syllables: VEG-ta-ble)", "a": ["1"]},
                {"q": "de-ter-mine", "a": ["2"]},
                {"q": "ho-tel", "a": ["2"]},
                {"q": "in-te-res-ting (usually 3 syllables: IN-tres-ting)", "a": ["1"]},
                {"q": "ca-te-go-ry", "a": ["1"]},
                {"q": "a-na-ly-sis", "a": ["2"]},
                {"q": "tech-no-lo-gy", "a": ["2"]},
                {"q": "pre-sen-ta-tion", "a": ["3"]},
                {"q": "ad-van-tage", "a": ["2"]},
                {"q": "re-cord (noun: 'a world record')", "a": ["1"]},
                {"q": "re-cord (verb: 'to record a song')", "a": ["2"]},
                {"q": "in-crease (noun)", "a": ["1"]},
                {"q": "in-crease (verb)", "a": ["2"]},
                {"q": "de-mo-cra-cy", "a": ["2"]},
                {"q": "de-mo-cra-tic", "a": ["3"]},
                {"q": "in-dus-try", "a": ["1"]},
                {"q": "ca-tas-tro-phe", "a": ["2"]},
                {"q": "ho-ri-zon", "a": ["2"]},
                {"q": "Eu-ro-pe-an", "a": ["3"]},
                {"q": "e-ven-tu-al-ly", "a": ["2"]},
                {"q": "par-ti-ci-pate", "a": ["2"]},
            ],
        }),
        ("md", """
### Sentence stress and intonation

**Nuclear stress:** in every thought group, one word carries the main stress - usually the **new or contrasted** information.
Repeated information is de-stressed.

| Pattern | Tone | Example |
|---|---|---|
| Wh- question | fall ↘ | *Where do you **live**↘?* |
| Yes/no question | rise ↗ | *Are you **com**ing↗?* |
| Tag: checking / expecting agreement | fall ↘ | *It's cold, **is**n't it↘?* |
| Tag: real question | rise ↗ | *You've met Ana, **have**n't you↗?* |
| Lists | rise, rise, fall | *red↗, green↗ and blue↘* |
| Reservation / "but..." | fall-rise ↘↗ | *The food was **good**↘↗...* (but the service wasn't) |
| Thought groups | pause + one nucleus per group | *The report / which we sent on **Mon**day / was never **read**.* |

**The classic drill:** say *I didn't say she stole the money* seven times, stressing a different word each time.
Explain the meaning of each version (e.g. *I didn't say **SHE** stole it* = someone else did).
"""),
        ("ex", {
            "id": "s7_nuclear_stress",
            "title": "Which word carries the main stress?",
            "instructions": "Read the context, then write the ONE word that gets the main (nuclear) stress in B's reply.",
            "items": [
                {"q": "A: Did you buy the red one?  B: 'No, I bought the blue one.'", "a": ["blue"]},
                {"q": "A: Who sent the email?  B: 'Maria sent it.'", "a": ["maria"]},
                {"q": "A: You didn't send it, did you?  B: 'I did send it.'", "a": ["did"]},
                {"q": "A: Is the meeting on Monday?  B: 'No, it's on Tuesday.'", "a": ["tuesday"]},
                {"q": "A: I love London.  B: 'I hate London.'", "a": ["hate"]},
                {"q": "A: Where do you work?  B: 'I work in a bank.'", "a": ["bank"]},
                {"q": "A: Coffee?  B: 'I'd prefer tea, actually.'", "a": ["tea"]},
                {"q": "A: I thought you lived in Madrid.  B: 'I used to live in Madrid.'", "a": ["used"]},
                {"q": "A: Is it your car?  B: 'No, it's my sister's car.'", "a": ["sister's", "sister"]},
                {"q": "A glass building for growing plants: a GREENhouse or a green HOUSE? Write the stressed word.", "a": ["green"]},
            ],
        }),
        ("md", """
### Minimal pairs: say them, record them, compare
Say each pair aloud 3 times, record yourself, and check with **YouGlish** or the Cambridge Dictionary audio.
One column + one tongue twister = a perfect 2-minute warm-up before speaking practice.

| /iː/-/ɪ/ | /b/-/v/ | /s/-/θ/ | /d/-/ð/ | /dʒ/-/j/ | /æ/-/ʌ/-/ɑː/ | /ʃ/-/tʃ/ | /s/-/z/ | /n/-/ŋ/ | /ɜː/-/ɔː/ | voiceless-voiced | /w/-/ɡ/ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sheep-ship | berry-very | sink-think | day-they | jet-yet | cat-cut-cart | share-chair | rice-rise | sin-sing | work-walk | bet-bed | west-guest |
| leave-live | ban-van | sick-thick | dare-there | jail-Yale | hat-hut-heart | sheep-cheap | peace-peas | thin-thing | bird-bored | back-bag | wood-good |
| feel-fill | best-vest | mouse-mouth | breed-breathe | jeer-year | cap-cup-carp | wash-watch | loose-lose | ran-rang | firm-form | safe-save | wet-get |
| seat-sit | boat-vote | pass-path | udder-other | juice-use | match-much-march | cash-catch | price-prize | win-wing | shirt-short | rope-robe | wail-gale |

Practise both directions: many Spanish speakers say *yes* as "jes", so *yet/jet* get confused both ways.

**Tongue twisters:**
* /θ/: *Three thin thinkers thinking thick thoughtful thoughts.*
* /b/-/v/: *Bob's best vest is very, very black, but Vince's van is a big blue bus.*
* /s/: *She sells sea shells, and she speaks Spanish to students in Spain.*
* /ʃ/-/tʃ/: *Cheap ships, cheap sheep, cheap chips. Which wristwatch is a Swiss wristwatch?*
* /ŋ/: *The king was singing a long song, bringing nothing but ringing.*
* /ɜː/: *The first nurse walked to work early on Thursday.*
"""),
        # ------------------------------------------------------------------ 4
        ("md", """
---
## 4. Shadowing (15 minutes a day)

Shadowing = speaking **at the same time** as a native speaker, copying their rhythm, stress, intonation and linking.

1. Choose a 1-2 minute clip **with a transcript** (TED talk, podcast with transcript, a dictation from Notebook 06).
2. **Mark the transcript:** `/` for thought-group boundaries, CAPS for the stressed syllable in each group, ↗↘ for tones.
3. Listen once while reading.
4. Read aloud *with* the audio, a split second behind. Pause and repeat difficult phrases.
5. Shadow **without** the transcript.
6. Record your final version and compare it with the original. What's different? Stress? Speed? Linking?

Repeat the **same** clip for 3-5 days before moving on. Depth beats variety here.
"""),
        # ------------------------------------------------------------------ 5
        ("md", """
---
## 5. Timed speaking with a feedback loop

**The loop (do it at least 3 times a week):**
1. **Record** a 2-minute answer to a prompt (phone voice recorder is fine).
2. **Transcribe** it word for word, errors and "um"s included - by hand, with your phone's dictation, or with
   `analyse_recording("file.m4a")` (needs `pip install faster-whisper`; words it gets wrong may be pronunciation problems).
3. **Measure:** `speech_stats(transcript, seconds)` gives words per minute and fillers per minute, and saves them.
4. **Notice:** underline every error and every place you paused to search for a word.
5. **Correct and upgrade** 5 sentences using the language bank; log each error with `log_mistake(...)`.
6. **Re-record the same task the next day.** Task repetition is one of the best-proven ways to build fluency.

### The 4-3-2 technique
Talk about the **same** topic for **4 minutes**, then **3**, then **2**, each time to a **different (imagined) listener**.
The time pressure is the point: by round 3 you'll say the same content faster and more fluently. `four_three_two()` runs it.

Prompt types: `"long turn"`, `"opinion"`, `"discussion"`, `"storytelling"`, `"workplace"`, `"describe"`, `"mediation"`,
`"abstract"`, `"compare"`, `"negotiation"`, `"interaction"` (the last one is for a partner or AI role-play).
"""),
        ("code", """
p = random_prompt()          # or random_prompt("workplace")
"""),
        ("code", """
speak_timer(seconds=120, prep=60)   # or: four_three_two()
"""),
        ("code", """
my_speech = \"\"\"
paste your transcript here (keep the um's and eh's!)
\"\"\"
# speech_stats(my_speech, seconds=120, targets=p["hints"], label="remote work opinion")
"""),
        ("md", """
### Self-assessment after listening to your recording (edit this cell each time)
Descriptors paraphrased from the CEFR Companion Volume (2020).

| Criterion | 1 = B2 | 2 = B2+ | 3 = C1 | Me |
|---|---|---|---|---|
| **Fluency** | fairly even pace; noticeable pauses while searching for words | long stretches without searching; pauses mostly for ideas | fluent and spontaneous, almost effortless; only a conceptually hard topic slows me down | |
| **Range** | enough to give views clearly; some repetition and circumlocution | varied vocabulary; some collocations and idioms | broad range; I can say exactly what I mean without restricting what I want to say | |
| **Accuracy** | good control; errors don't cause misunderstanding | occasional slips, often self-corrected | consistently high accuracy; errors are rare and hard to spot | |
| **Coherence** | limited linkers; some "jumpiness" in long turns | clear structure, varied linkers | smoothly flowing, well-structured speech; controlled use of cohesive devices | |
| **Interaction** | takes turns, sometimes clumsily | reacts naturally, asks follow-ups | uses a range of discourse phrases to take and keep the floor and to relate my turn to others' | |
| **Sounds** | accent clearly L1-influenced, little effect on intelligibility | most target sounds controlled | virtually all sounds articulated; accent never affects intelligibility | |
| **Prosody** | generally appropriate stress and intonation | word and sentence stress mostly right | intonation and stress used to convey fine shades of meaning | |
| **Nuance** | opinions stated fairly directly | some hedging | qualifies statements precisely (degree, certainty, concession) | |

**Numbers today:** words/min ___ · fillers/min ___ · errors per 100 words ___ · longest run without a pause ___

**One thing I'll improve tomorrow:**

**Words I needed but didn't know** (add them to `my_words`!):
"""),
        # ------------------------------------------------------------------ 6
        ("md", """
---
## 6. Real conversations (the most important part)

Grammar and vocabulary only become fluency through **real interaction**. Aim for **3 conversations a week**:

* **Tutors:** italki, Preply - ask for "C1 conversation practice with written corrections after the lesson".
  Cambly offers mostly unstructured chat with native speakers: good for fluency, less correction.
* **Free exchanges:** Tandem, HelloTalk, local language-exchange events (Meetup.com; many Spanish and Latin American
  cities have regular "Mundo Lingo"-style nights - check local availability).
* **Public speaking:** Toastmasters International - most large Spanish-speaking cities have at least one English-language
  club (use the Toastmasters club finder).
* **AI conversation partner** (daily, low-pressure practice in a voice mode). Paste this prompt:

```
You are my English conversation partner and coach. My level is B2 and I'm working towards C1.
I'm a [JOB] and I use English at work with [US / UK / international] colleagues, so use [American / British] English.
Talk with me about [TOPIC], or role-play [SCENARIO, e.g. "a status meeting where I have to explain a delay"].
Speak naturally, at normal speed, in short turns (2-4 sentences), so I do most of the talking.
Ask follow-up questions, interrupt me sometimes and push back on my opinions a little.
Don't correct me during the conversation. When I say "FEEDBACK", give me:
(1) my 5 most important grammar/vocabulary mistakes, each as "I said -> better", with a one-line reason;
(2) 5 things I said that were correct but unnatural, and how a native speaker would say them;
(3) moments where my register was too direct, too formal or too informal;
(4) 3 C1 collocations, phrasal verbs or workplace expressions I could have used;
(5) words in your transcript of my speech that look mis-recognised (they may be pronunciation problems);
(6) a score from 1 to 3 for fluency, range, accuracy, coherence and interaction, using CEFR B2/C1 descriptors.
```

**After every conversation**, write down 3 things you wanted to say but couldn't, find out how to say them, and add them to
`my_words`. Log the mistakes from the feedback with `log_mistake()`. This "gap noticing" is one of the most effective
habits you can build.
"""),
        ("code", """
# log_mistake("I have a doubt about the invoice", "I have a question about the invoice", "doubt = uncertainty")
# log_study(30, "speaking", "4-3-2 on 'remote work' + shadowing TED clip")
"""),
    ],
}
