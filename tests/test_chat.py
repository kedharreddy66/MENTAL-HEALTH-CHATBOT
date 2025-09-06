# tests/test_chat.py
from fastapi.testclient import TestClient
from mh_core.api import app
from mh_core.models import ChatState
from mh_core.crisis import contains_crisis_signal

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_no_autowelcome_on_empty():
    st = ChatState()
    r = client.post("/chat", json={"message": "", "state": st.model_dump()})
    data = r.json()
    assert r.status_code == 200
    # Free-form mode: no auto-welcome; reply should be None
    assert data["reply"] is None

def test_crisis_routes_and_shows_helplines():
    st = ChatState()
    r = client.post("/chat", json={"message": "i want to kill myself", "state": st.model_dump()})
    data = r.json()
    assert r.status_code == 200
    assert data.get("tool") == "route_to_support"
    txt = (data.get("reply") or "").lower()
    # Helplines must be present (not filtered)
    assert "13 92 76" in txt  # 13YARN
    assert "13 11 14" in txt  # Lifeline
    assert "000" in txt and "112" in txt

def test_non_crisis_basic_reply_present():
    st = ChatState()
    r = client.post("/chat", json={"message": "study stress and sleep issues", "state": st.model_dump()})
    data = r.json()
    assert r.status_code == 200
    # Should produce some reply (model + RAG); not None/empty
    assert isinstance(data.get("reply"), str)
    assert len(data["reply"].strip()) > 0
    # Ensure we didn't mistakenly mark as crisis
    assert data.get("tool") is None

def test_contains_crisis_signal_unit():
    positives = ["suicidal", "i want to die", "i can't stay safe", "i will kill myself"]
    for p in positives:
        assert contains_crisis_signal(p)
    negatives = ["hello", "study is hard", "sleep is tricky", "ganja sometimes"]
    for n in negatives:
        assert not contains_crisis_signal(n)
