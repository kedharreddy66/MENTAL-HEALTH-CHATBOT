from pydantic import BaseModel, Field
from typing import Optional, List

class ChatState(BaseModel):
    """
    Conversation state that travels back and forth between client and server.
    No personal details. Only plan-related fields + current step.
    """
    step: str = Field(default="strengths")  # strengths | worries | goal | support | nextStep | done
    strengths: List[str] = []
    worries: List[str] = []
    goal: str = ""
    support: str = ""
    nextStep: str = ""

class ChatIn(BaseModel):
    """
    Incoming payload from the app.
    - message: the latest user text
    - state: (optional) previous conversation state
    """
    message: str
    state: Optional[ChatState] = None
    fast: Optional[bool] = None  # optional client hint to enable fast mode per-request

class ChatOut(BaseModel):
    """
    Server response:
    - reply: text for the chatbot to show
    - state: updated conversation state
    - tool: optional routing signal (e.g., 'route_to_support' for crisis)
    """
    reply: Optional[str] = None
    state: Optional[ChatState] = None
    tool: Optional[str] = None
