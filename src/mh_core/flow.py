# src/mh_core/flow.py
from .models import ChatState
from .content_loader import STRINGS

def _next_prompt(step: str) -> str:
    """Return the correct prompt based on the current step."""
    return {
        "strengths": STRINGS.get("strengths_prompt", ""),
        "worries": STRINGS.get("worries_prompt", ""),
        "goal": STRINGS.get("goal_prompt", ""),
        "support": STRINGS.get("support_prompt", ""),
        "nextStep": STRINGS.get("next_step_prompt", ""),
        "done": STRINGS.get("wrap_prompt", "")
    }.get(step, STRINGS.get("wrap_prompt", ""))

def advance_state(state: ChatState, user_text: str):
    """Advance the conversation state based on user input."""
    txt = (user_text or "").strip()

    # Allow user to ask for clarification (e.g. "what do you mean by strong?")
    if "what do you mean" in txt.lower() and "strong" in txt.lower():
        return state, STRINGS.get("clarify_strengths", "By strengths we mean supports that keep you going.")

    if state.step == "strengths":
        if txt.lower() == "next":
            state.step = "worries"
        elif txt:
            state.strengths.append(txt)
        return state, _next_prompt(state.step)

    if state.step == "worries":
        if txt.lower() == "next":
            state.step = "goal"
        elif txt:
            state.worries.append(txt)
        return state, _next_prompt(state.step)

    if state.step == "goal":
        if txt:
            state.goal = txt
            state.step = "support"
        return state, _next_prompt(state.step)

    if state.step == "support":
        if txt:
            state.support = txt
            state.step = "nextStep"
        return state, _next_prompt(state.step)

    if state.step == "nextStep":
        if txt:
            state.nextStep = txt
            state.step = "done"
        return state, _next_prompt("done")

    # Conversation done — wrap up
    return state, STRINGS.get("wrap_prompt", "")
