# scripts/chat_cli.py
"""
Simple command-line chat client to test your running API.
Keeps conversation state between turns.
"""

import requests

API_URL = "http://127.0.0.1:8000/chat"
state = None

print("💬 Chat started. Type 'exit' to quit.")
while True:
    msg = input("> ").strip()
    if msg.lower() in {"exit", "quit"}:
        print("👋 Goodbye!")
        break

    payload = {"message": msg, "state": state}
    try:
        res = requests.post(API_URL, json=payload)
        res.raise_for_status()
        data = res.json()
        state = data.get("state")
        tool = data.get("tool")
        if tool == "route_to_support":
            print("🚨 Crisis detected → app should show support screen.")
        if data.get("reply"):
            print(f"🤖 {data['reply']}")
    except Exception as e:
        print(f"❌ Error talking to API: {e}")
