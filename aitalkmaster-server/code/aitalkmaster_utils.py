from typing import Optional
from datetime import datetime
from pathlib import Path
from mutagen.mp3 import MP3
import time
from dataclasses import dataclass
from code.shared import log

def time_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_audio_duration(file_path: Path) -> float:
    """Get the duration of an MP3 file in seconds"""
    
    try:
        audio = MP3(file_path)
        duration = audio.info.length
        
        return duration
    except Exception as e:
        log(f"Error getting audio duration for {file_path}: {e}")
        return 0.0

@dataclass
class UserMessage:
    """Represents a user message in the conversation"""
    message: str
    name: str
    message_id: str
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

@dataclass
class AssistantResponse:
    """Represents an assistant response in the conversation"""
    response: str
    name: str
    response_id: str
    filename: str
    timestamp: Optional[float] = None
    audio_created_at: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class AitalkmasterInstance:
    """Simplified AitalkmasterInstance class using message classes for better readability"""
    
    def __init__(self, join_key: str):
        self.join_key = join_key
        self.created_at = time.time()
        self.last_listened_at = time.time()
        
        # Lists of message objects for better readability
        self.user_messages: list[UserMessage] = []
        self.assistant_responses: list[AssistantResponse] = []
        
        # Audio sequence counter for this instance
        self.audio_sequence_counter = 0

    def addUserMessage(self, message: str, name: str, message_id: str):
        """Add a user message to the conversation"""
        user_msg = UserMessage(message=message, name=name, message_id=message_id)
        self.user_messages.append(user_msg)

    def addResponse(self, response: str, name: str, response_id: str, filename: str):
        """Add an assistant response to the conversation"""
        assistant_resp = AssistantResponse(
            response=response, 
            name=name, 
            response_id=response_id, 
            filename=filename
        )
        self.assistant_responses.append(assistant_resp)

    def contains_message_id(self, message_id: str) -> bool:
        """Check if a message ID already exists in user messages"""
        for user_msg in self.user_messages:
            if user_msg.message_id == message_id:
                return True
        return False
    
    def getDialog(self):
        """Get complete dialog including both user messages and assistant responses in chronological order"""
        dialog = []
        
        # Combine user messages and assistant responses in chronological order
        all_messages = []
        
        # Add user messages
        for user_msg in self.user_messages:
            all_messages.append({
                "timestamp": user_msg.timestamp,
                "role": "user",
                "content": f"{user_msg.name}: {user_msg.message}",
                "message_id": user_msg.message_id
            })
        
        # Add assistant responses
        for assistant_resp in self.assistant_responses:
            all_messages.append({
                "timestamp": assistant_resp.timestamp,
                "role": "assistant", 
                "content": f"{assistant_resp.name}: {assistant_resp.response}",
                "response_id": assistant_resp.response_id
            })
        
        # Sort by actual timestamp to maintain chronological order
        all_messages.sort(key=lambda x: x["timestamp"])
        
        # Return only the role and content for chat model compatibility
        for msg in all_messages:
            dialog.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return dialog

    def set_audio_created_at(self, response_id: str, timestamp: float):
        """Set the audio creation timestamp for a specific response"""
        for assistant_resp in self.assistant_responses:
            if assistant_resp.response_id == response_id:
                assistant_resp.audio_created_at = timestamp
                break

    def generate_sequence_str(self) -> str:
        """Generate a sequence string for audio files with leading zeros for proper sorting"""
        # Increment sequence counter for this instance
        self.audio_sequence_counter += 1
        sequence_number = self.audio_sequence_counter
        
        # Format sequence number with leading zeros for proper sorting (e.g., 001, 002, 003)
        sequence_str = f"{sequence_number:03d}"
        return sequence_str

    def __str__(self):
        return str(self.getDialog())

def remove_name(message: str, charactername: str):
    if message.lower().startswith(f"{charactername.lower()}: "):
        message = message[len(charactername)+2:]
    elif message.lower().startswith(f"{charactername.lower()}:"):
        message = message[len(charactername)+1:]
    return message