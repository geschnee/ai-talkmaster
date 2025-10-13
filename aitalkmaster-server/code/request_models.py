
from typing import Optional

from pydantic import BaseModel

class GenerateGetMessageResponseRequest(BaseModel):
    username: str
    prompt: str
    model: str
    system_instructions: str
    options: Optional[dict] = {}

class GenerateRequest(BaseModel):
    username: str
    prompt: str
    model: str
    system_instructions: str
    options: Optional[dict] = {}


class ConversationStartRequest(BaseModel):
    username: str
    model: str
    simulatorHostname: str
    regionName: str
    system_instructions: Optional[str] = ""
    options: Optional[dict] = {}

class ConversationPostMessageRequest(BaseModel):
    conversation_key: str
    prompt: str
    message_id: str

class ConversationGetMessageResponseRequest(BaseModel):
    conversation_key: str
    message_id: str

class AitPostMessageRequest(BaseModel):
    join_key: str
    username: str # name of the agent that said the message
    message: str
    model: str
    system_instructions: str
    charactername: str
    message_id: str
    audio_voice: Optional[str] = ""
    options: Optional[dict] = {}
    audio_instructions: Optional[str] = ""
    audio_model: Optional[str] = ""

class AitMessageResponseRequest(BaseModel):
    join_key: str
    message_id: str

class AitResetJoinkeyRequest(BaseModel):
    join_key: str

class AitGenerateAudioRequest(BaseModel):
    join_key: str
    username: str
    message: str
    message_id: str
    audio_instructions: Optional[str] = ""
    audio_voice: Optional[str] = ""
    audio_model: Optional[str] = ""

