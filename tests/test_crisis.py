# tests/test_crisis.py
import re
from fastapi.testclient import TestClient

from mh_core.api import app
from mh_core.crisis import contains_crisis_signal, SUPPORT_TEXT
from mh_core.models import ChatState

client = TestClient(app)

def test_contains_crisis_signal_positive_cases():
    positives = [
        "i want to die",
        "I wanna die",
        "i can't go on",
        "thinking about suicide",
        "i feel suicidal",
        "i want to end it",
        "i will kill myself",
        "i can't stay safe",
        "i want to self-harm",
        "no reason to live",
        "give up",
    ]
    for txt in positives:
        assert contains_crisis_signal(txt), f"Should detect crisis for: {txt}"

def test_contains_crisis_signal_negative_cases():
    negatives = [
        "i feel sad",
        "i'm stressed",
        "study is hard",
        "sleep is tricky",
        "hello",
        "ganja sometimes helps me relax",
        "can we yarn about family?",
    ]
    for txt in negatives:
        assert not contains_crisis_signal(txt), f"Should NOT detect crisis for: {txt}"

def test_support_text_has_required_services():
    # Make sure the helplines are present (sanity checks)
    low = SUPPORT_TEXT.lower()
    assert "13yarn" in low
    assert "lifeline" in low
    assert "kids helpline" in low
    assert "suicide call back" in low
    assert "beyond blue" in low
    # emergency numbers
    assert "000" in SUPPORT_TEXT
    assert "112" in SUPPORT_TEXT

def test_api_crisis_route_shows_helplines_and_tool():
    st = ChatState()
    r = client.post("/chat", json={"message": "i want to kill myself", "state": st.model_dump()})
    assert r.status_code == 200
    data = r.json()
    assert data.get("tool") == "route_to_support"
    # Ensure numbers made it through (not filtered)
    txt = data.get("reply", "")
    assert "13 92 76" in txt  # 13YARN
    assert "13 11 14" in txt  # Lifeline
    assert "000" in txt and "112" in txt
