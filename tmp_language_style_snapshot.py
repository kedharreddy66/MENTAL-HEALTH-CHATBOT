from typing import Dict, Tuple

STANDARD_TONE = {
    "greeting": "Hey, I'm here to listen. What's on your mind today?",
    "bridge_family": (
        "Before we get into worries, let's start with the strong people around you. "
        "Who helps keep you steady â€” family, Elders, friends?"
    ),
    "bridge_strengths": (
        "Great â€” now, what are the things that keep you strong â€” culture, Country, sport, music, art, being with mob?"
    ),
    "invite_worries": (
        "Thanks for sharing. When you're ready, we can yarn about the worries that take your strength away. "
        "Some people talk about study or work stress, money, relationships, sorry business, health, smoking/alcohol, or sleep. "
        "What's yours today?"
    ),
    "goals_intro": "Let's pick one small change that feels possible this week.",
}


def init_state() -> Dict:
    # Track basic flow + what we collect along the way
    return {
        "stay_strong_step": 1,
        "support": None,
        "strengths": None,
        "worry": None,
        "worry_category": "",
        "greeted": False,  # ensures we greet on the first bot reply
    }


# ---------- helpers
def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _is_readiness_text(text: str) -> bool:
    t = _norm(text)
    return t in {"ok", "okay", "im ready", "i am ready", "ready", "yeah", "yep", "sure"}


def _is_examples_question(text: str) -> bool:
    t = _norm(text)
    return t in {"what", "what?", "what do you mean", "not sure", "idk", "i dont know", "i don't know"}


def _is_worry_signal(text: str) -> bool:
    """Rough signal that the user is sharing a worry/feeling rather than people/strengths."""
    t = _norm(text)
    WORRY_WORDS = [
        "stress",
        "stressed",
        "anxious",
        "anxiety",
        "panic",
        "sad",
        "depress",
        "low",
        "angry",
        "anger",
        "overwhelmed",
        "worried",
        "worry",
        "scared",
        "fear",
        "tired",
        "exhausted",
        "burnt out",
        "burned out",
        "lonely",
        "sleep",
        "insomnia",
        "problem",
        "issue",
        "help",
        "support",
        "advice",
    ]
    return any(w in t for w in WORRY_WORDS)


def _looks_like_people_list(text: str) -> bool:
    """Detects if the answer names support people (family/Elders/friends)."""
    t = _norm(text)
    PEOPLE_WORDS = [
        "family",
        "elder",
        "elders",
        "friend",
        "friends",
        "mate",
        "mates",
        "mum",
        "mom",
        "dad",
        "mother",
        "father",
        "nan",
        "pop",
        "grandma",
        "grandpa",
        "aunty",
        "uncle",
        "cousin",
        "cousins",
        "brother",
        "sister",
        "siblings",
        "partner",
        "boyfriend",
        "girlfriend",
        "husband",
        "wife",
        "kids",
        "children",
        "child",
        "son",
        "daughter",
        "mob",
        "community",
        "coach",
        "teacher",
        "counsellor",
        "counselor",
        "worker",
    ]
    return any(w in t for w in PEOPLE_WORDS)


def _classify_worry(text: str) -> Tuple[str, str]:
    """Return (category, matched_phrase) or ("", "") if unknown."""
    t = _norm(text)
    if not t:
        return "", ""
    KEYS = [
        ("study", ["exam", "study", "assignment", "school", "uni", "college", "test"]),
        ("work", ["work", "boss", "shift", "job"]),
        ("money", ["money", "rent", "bills", "bill", "debt", "pay", "broke"]),
        (
            "relationships",
            [
                "relationship",
                "partner",
                "boyfriend",
                "girlfriend",
                "breakup",
                "friend",
                "argue",
                "fight",
            ],
        ),
        ("sorry_business", ["sorry business", "funeral", "grief", "loss"]),
        ("health", ["health", "sick", "pain", "doctor", "gp"]),
        ("smoking", ["smoke", "smoking", "cigarette", "ciggies"]),
        ("alcohol", ["alcohol", "drink", "drinking", "grog"]),
        ("sleep", ["sleep", "insomnia", "tired", "bedtime"]),
        ("anxiety", ["anxiety", "panic", "worry", "worried", "nervous"]),
        ("mood", ["depress", "sad", "low", "flat"]),
        ("anger", ["anger", "angry", "mad"]),
        ("substances", ["drugs", "ice", "weed", "cannabis", "marijuana"]),
        ("racism", ["racism", "racist", "discrimination", "prejudice", "stereotype", "racial"]),
        ("identity", ["identity", "culture", "language", "country", "mob"]),
    ]
    for cat, kws in KEYS:
        for k in kws:
            if k in t:
                return cat, k
    return "", ""


def _goal_suggestions(cat: str) -> str:
    examples = {
        "study": [
            "Do one 25â€‘minute study block, then 5â€‘minute break",
            "Ask a friend/tutor one question you're stuck on",
            "Pack your bag and set your alarm for tomorrow morning",
        ],
        "work": [
            "Plan one short walk at lunch or after work",
            "Write the one thing you'll ask your boss about shifts",
            "Set a clear finish time for today",
        ],
        "money": [
            "List the top 3 bills and their due dates",
            "Call to set up a payment plan for one bill",
            "Try a noâ€‘spend day and take snacks/water from home",
        ],
        "relationships": [
            "Send a calm checkâ€‘in text to the person you trust",
            "Write what you want to say before the yarn",
            "Pick a quiet time and place to talk",
        ],
        "sorry_business": [
            "Spend time with family/Elders today",
            "Keep plans light and rest when you can",
            "Yarn with an Aboriginal health worker/ACCHO if it helps",
        ],
        "health": [
            "Book or confirm a GP appointment",
            "Take your meds at the same time today",
            "10â€‘minute gentle walk on Country/nature",
        ],
        "smoking": [
            "Delay your first smoke by 30 minutes",
            "Have one fewer smoke today",
            "Keep the house/car smokeâ€‘free",
        ],
        "alcohol": [
            "Plan 2 alcoholâ€‘free days this week",
            "Swap your first drink for water or soft drink",
            "Set a finish time before bed",
        ],
        "sleep": [
            "Screens off 30 minutes before bed",
            "Keep the same sleep and wake time tonight",
            "No caffeine after 2 pm today",
        ],
        "anxiety": [
            "2 minutes of slow breathing (in 4, hold 4, out 4, hold 4)",
            "Short walk or stretch",
            "Write the worry and one small action you can try",
        ],
        "mood": [
            "Call a strong person who lifts you up",
            "15 minutes of music/art/faith/culture",
            "Sit or walk on Country for a few minutes",
        ],
        "anger": [
            "Step outside and breathe before replying",
            "Write down what you want to say first",
            "Walk it out for 10 minutes",
        ],
        "substances": [
            "Message a mate to hang out sober",
            "Eat first and drink water",
            "Plan an early night",
        ],
        "racism": [
            "Yarn with someone who backs you about what happened",
            "Take space, breathe, and do one thing that helps you feel strong (music, walk, culture)",
            "Write down what you want to say or do next when you're ready",
        ],
        "identity": [
            "Spend a few minutes on Country or in nature if you can",
            "Reach out to an Elder/family member for a yarn",
            "Do a small cultural activity (song, art, language, story)",
        ],
        "": [
            "Text or yarn with a strong person who supports you",
            "10â€‘minute walk or gentle stretch",
            "One small task you've been putting off â€” just start it",
        ],
    }
    tips = examples.get(cat, examples[""])
    bullets = "\n- " + "\n- ".join(tips)
    return f"Here are a few simple ideas you could try:\n{bullets}\nWhich one fits you this week?"


# ---------- main flow
def render_normal_reply(state: Dict, last_user_text: str) -> str:
    """
    Advances through the AIMhi Stay Strong flow and mutates `state` so it persists.
      0) Greeting (first reply only)
      1) Support people  2) Strengths  3) Worries  4) Simple goal
    """
    if "stay_strong_step" not in state:
        state.update(init_state())

    # greet on the very first bot turn, regardless of user text
    if not state.get("greeted", False):
        state["greeted"] = True
        # Do not advance the step yet; next turn will go to Step 1 logic
        return STANDARD_TONE["greeting"]

    step = state.get("stay_strong_step", 1)
    text_raw = (last_user_text or "").strip()
    text = _norm(text_raw)

    # Step 1 -> ask about support people (but branch if they share a worry)
    if step == 1:
        if _is_worry_signal(text):
            state["stay_strong_step"] = 3
            return (
                "Thanks for telling me how you're feeling. I'm here. "
                "Can you share a bit about what's been making you feel this way? "
                + STANDARD_TONE["invite_worries"]
            )
        state["stay_strong_step"] = 2
        return STANDARD_TONE["bridge_family"]

    # Step 2 -> capture support if it looks like people; otherwise branch appropriately
    if step == 2:
        if _looks_like_people_list(text):
            state["support"] = text_raw
            state["stay_strong_step"] = 3
            return STANDARD_TONE["bridge_strengths"]

        # If they share a worry here, move to the worries step
        if _is_worry_signal(text) or not text:
            state["stay_strong_step"] = 3
            return "Thanks for telling me that. " + STANDARD_TONE["invite_worries"]

        # Otherwise gently reprompt for support people
        state["stay_strong_step"] = 2
        return "Who are your strong people â€” family, Elders, friends â€” who help keep you steady?"

    # Step 3 -> capture strengths -> invite worries (and stay here until one is given)
    if step == 3:
        if text_raw:
            state["strengths"] = text_raw

        if _is_readiness_text(text) or _is_examples_question(text) or not text:
            state["stay_strong_step"] = 3  # remain here
            return STANDARD_TONE["invite_worries"]

        # Try to classify as a worry
        cat, _ = _classify_worry(text)
        state["worry"] = text_raw
        state["worry_category"] = cat
        state["stay_strong_step"] = 4
        return "Thanks for telling me about that. " + STANDARD_TONE["goals_intro"]

    # Step 4 -> reflect & help pick a small step
    state["stay_strong_step"] = 4

    if not state.get("worry"):
        state["stay_strong_step"] = 3
        return STANDARD_TONE["invite_worries"]

    if _is_examples_question(text):
        cat = state.get("worry_category", "")
        return _goal_suggestions(cat)

    if text_raw:
        return (
            f"Thanks for telling me about \"{text_raw}\". "
            "What's one small thing you could do this week to feel a bit stronger about that?"
        )

    return STANDARD_TONE["goals_intro"]

"""
Overrides below ensure plain English style with no slang or contractions
in bot-authored text, while keeping cultural references respectful.
"""

def _goal_suggestions(cat: str) -> str:  # override with plain-English suggestions
    examples = {
        "study": [
            "Do one 25 minute study block, then a 5 minute break",
            "Ask a friend or tutor one question you are stuck on",
            "Pack your bag and set your alarm for tomorrow morning",
        ],
        "work": [
            "Plan one short walk at lunch or after work",
            "Write the one thing you will ask your boss about shifts",
            "Set a clear finish time for today",
        ],
        "money": [
            "List the top three bills and their due dates",
            "Call to set up a payment plan for one bill",
            "Try a no-spend day and take snacks and water from home",
        ],
        "relationships": [
            "Send a calm check-in message to the person you trust",
            "Write what you want to say before the conversation",
            "Pick a quiet time and place to talk",
        ],
        "sorry_business": [
            "Spend time with family or Elders today",
            "Keep plans light and rest when you can",
            "Talk with an Aboriginal health worker or ACCHO if it helps",
        ],
        "health": [
            "Book or confirm a GP appointment",
            "Take your medicine at the same time today",
            "10 minute gentle walk on Country or in nature",
        ],
        "smoking": [
            "Delay your first cigarette by 30 minutes",
            "Have one fewer cigarette today",
            "Keep the house and car smoke-free",
        ],
        "alcohol": [
            "Plan two alcohol-free days this week",
            "Swap your first drink for water or a soft drink",
            "Set a finish time before bed",
        ],
        "sleep": [
            "Screens off 30 minutes before bed",
            "Keep the same sleep and wake time tonight",
            "No caffeine after 2 pm today",
        ],
        "anxiety": [
            "Two minutes of slow breathing (in 4, hold 4, out 4, hold 4)",
            "Short walk or stretch",
            "Write the worry and one small action you can try",
        ],
        "mood": [
            "Call a strong person who lifts you up",
            "15 minutes of music, art, faith, or culture",
            "Sit or walk on Country for a few minutes",
        ],
        "anger": [
            "Step outside and breathe before replying",
            "Write down what you want to say first",
            "Walk it out for 10 minutes",
        ],
        "substances": [
            "Message a friend to hang out sober",
            "Eat first and drink water",
            "Plan an early night",
        ],
        "racism": [
            "Talk with someone who supports you about what happened",
            "Take space, breathe, and do one thing that helps you feel strong (music, a walk, culture)",
            "Write down what you want to say or do next when you are ready",
        ],
        "identity": [
            "Spend a few minutes on Country or in nature if you can",
            "Reach out to an Elder or family member for a conversation",
            "Do a small cultural activity (song, art, language, story)",
        ],
        "": [
            "Text or talk with a strong person who supports you",
            "10 minute walk or gentle stretch",
            "One small task you have been putting off â€” just start it",
        ],
    }
    tips = examples.get(cat, examples[""])
    bullets = "\n- " + "\n- ".join(tips)
    return f"Here are a few simple ideas you could try:\n{bullets}\nWhich one fits you this week?"


# Override tone strings to remove contractions and colloquialisms
STANDARD_TONE = {
    "greeting": "Hello. I am here to listen. What is on your mind today?",
    "bridge_family": (
        "Before we talk about worries, let us start with the strong people around you. "
        "Who helps keep you steady? Family, Elders, friends?"
    ),
    "bridge_strengths": (
        "Thank you. Now, what are the things that keep you strong? "
        "Culture, Country, sport, music, art, being with community?"
    ),
    "invite_worries": (
        "Thank you for sharing. When you are ready, we can talk about the worries that make things harder. "
        "Some people talk about study or work stress, money, relationships, sorry business, health, smoking or alcohol, or sleep. "
        "What is on your mind today?"
    ),
    "goals_intro": "Let us choose one small change that feels possible this week.",
}

