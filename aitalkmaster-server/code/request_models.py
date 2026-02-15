
from typing import Optional
from pydantic import BaseModel

class GenerateRequest(BaseModel):
    message_id: str
    message: str
    system_instructions: Optional[str] = ""
    model: Optional[str] = ""
    options: Optional[dict] = {}

# Conversation requests (single-character conversations with history, no audio streaming)
class ConversationStartRequest(BaseModel):
    model: Optional[str] = ""
    system_instructions: Optional[str] = ""
    options: Optional[dict] = {}

class ConversationPostMessageRequest(BaseModel):
    conversation_key: str
    message: str
    message_id: str

# AI Talkmaster requests (multi-character conversations with history and audio streaming)
class AitPostMessageRequest(BaseModel):
    join_key: str
    username: str # name of the agent that said the message
    message: str
    model: Optional[str] = ""
    system_instructions: Optional[str] = ""
    charactername: str
    message_id: str
    audio_voice: Optional[str] = ""
    options: Optional[dict] = {}
    audio_instructions: Optional[str] = ""
    audio_model: Optional[str] = ""

class AitResetJoinkeyRequest(BaseModel):
    join_key: str

class AitStartConversationRequest(BaseModel):
    join_key: str

class AitGenerateAudioRequest(BaseModel):
    join_key: str
    username: str
    message: str
    audio_instructions: Optional[str] = ""
    audio_voice: Optional[str] = ""
    audio_model: Optional[str] = ""

# Translation requests
class TranslationRequest(BaseModel):
    session_key: str
    message: str
    source_language: str
    target_language: str
    model: Optional[str] = ""
    audio_voice: Optional[str] = ""
    audio_model: Optional[str] = ""
    message_id: str