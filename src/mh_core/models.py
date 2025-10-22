from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class ChatState(BaseModel):
    """
    Conversation state that travels back and forth between client and server.
    No personal details. Only plan-related fields + current step.
    """
    step: str = Field(default="support")  # support | strengths | worries | goal | nextStep | done
    strengths: List[str] = Field(default_factory=list)
    worries: List[str] = Field(default_factory=list)
    goal: str = ""
    support: str = ""
    nextStep: str = ""
    # Crisis flow state: none | check | done
    crisis: str = Field(default="none")
    # Conversation memory (recent message turns)
    history: List[Dict[str, str]] = Field(default_factory=list)

class ChatIn(BaseModel):
    """
    Incoming payload from the app.
    - message: the latest user text
    - state: (optional) previous conversation state
    """
    message: str
    state: Optional[ChatState] = None
    provider: Optional[str] = None  # 'ollama' (default) or 'gemini'

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
    # Optional richer payloads (used by chat.html for crisis flow)
    mode: Optional[str] = None
    messages: Optional[List[str]] = None


class SignupIn(BaseModel):
    email: Optional[str] = None
    username: str
    password: Optional[str] = None  # optional if using OTP-only


class LoginIn(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None  # optional if using OTP-only


class TokenOut(BaseModel):
    token: str
    user: dict


class UserOut(BaseModel):
    id: str
    username: str
    email: Optional[str] = None


# OTP flows
class SignupRequestIn(BaseModel):
    email: str
    username: str


class SignupVerifyIn(BaseModel):
    email: str
    username: str
    code: str
    password: Optional[str] = None


class LoginRequestIn(BaseModel):
    email: str


class LoginVerifyIn(BaseModel):
    email: str
    code: str


# Profile updates
 
