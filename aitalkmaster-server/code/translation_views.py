from fastapi.responses import JSONResponse
from fastapi import Request
import time
from pathlib import Path
from datetime import datetime
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
import traceback
import io
from dataclasses import dataclass
from typing import Optional

from code.config import ChatClientMode, AudioClientMode
from code.audio_utils import start_translation_stream, queue_translation_audio
from code.request_models import TranslationRequest
from code.validation_decorators import validate_audio_decorator, rate_limit_decorator, validate_session_key_decorator, validate_chat_model_decorator
from code.shared import app, config, log
from pydub import AudioSegment
from code.rate_limiter import get_ip_address_for_rate_limit, increment_resource_usage
from code.message_queue import queue_message_request, RequestType
from code.translation_utils import build_audio_instructions, build_translation_instructions

# Dictionary to track active translation sessions
active_translation_sessions = {}

@dataclass
class TranslationResult:
    """Represents a completed translation"""
    message_id: str
    original_message: str
    translated_text: str
    source_language: str
    target_language: str
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class TranslationSession:
    """Manages a translation session with audio sequence tracking"""
    
    def __init__(self, session_key: str):
        self.session_key = session_key
        self.created_at = time.time()
        self.last_listened_at = time.time()
        self.audio_sequence_counter = 0
        self.translations: list[TranslationResult] = []  # Store completed translations
    
    def generate_sequence_str(self) -> str:
        """Generate a sequence string for audio files with leading zeros for proper sorting"""
        self.audio_sequence_counter += 1
        sequence_number = self.audio_sequence_counter
        sequence_str = f"{sequence_number:03d}"
        return sequence_str
    
    def add_translation(self, translation: TranslationResult):
        """Add a completed translation to the session"""
        self.translations.append(translation)
    
    def get_translation(self, message_id: str) -> Optional[TranslationResult]:
        """Get a translation by message_id"""
        for translation in self.translations:
            if translation.message_id == message_id:
                return translation
        return None

    def contains_message_id(self, message_id: str) -> bool:
        """Check if a message ID already exists in translations"""
        for translation in self.translations:
            if translation.message_id == message_id:
                return True
        return False

def get_or_create_translation_session(session_key: str) -> TranslationSession:
    """Get or create a translation session"""
    if session_key in active_translation_sessions.keys():
        session = active_translation_sessions[session_key]
    else:
        session = TranslationSession(session_key=session_key)
        if config.liquidsoap_client is not None:
            start_translation_stream(session_key)
        active_translation_sessions[session_key] = session
    return session


def translate_text(message: str, source_language: str, target_language: str, ip_address: str, model: str = "") -> str:
    """Translate text from source language to target language using the chat client"""
    try:
        translation_input = message
        translation_instructions = build_translation_instructions(source_language, target_language)
        
        # Use provided model or default
        translation_model = model if model else config.chat_client.default_model
        
        if config.chat_client.mode == ChatClientMode.OPENAI:
            response = config.get_or_create_openai_chat_client().responses.create(
                model=translation_model,
                input=translation_input,
                instructions=translation_instructions
            )
            translated_text = response.output[0].content[0].text.strip()
            
            # Track token usage for rate limiting
            increment_resource_usage(ip_address, response.usage.total_tokens)
        
        elif config.chat_client.mode == ChatClientMode.OLLAMA:
            response = config.get_or_create_ollama_chat_client().generate(
                model=translation_model,
                prompt=translation_input,
                system=translation_instructions,
                options={}
            )
            translated_text = response["response"].strip()
            
            # Track eval_count for rate limiting
            increment_resource_usage(ip_address, response["eval_count"])
        else:
            log(f'Error: unknown chat client mode: {config.chat_client.mode}')
            return message  # Return original message if translation fails
        
        return translated_text
        
    except Exception as e:
        log(f'Error translating text: {e}')
        log(f'stack: {traceback.print_exc()}')
        return message  # Return original message if translation fails

def save_audio(filename: str, response_msg: str, audio_voice: str, audio_model: str, audio_instructions: str, ip_address: str):
    """Save audio file from translated text"""
    if config.audio_client.mode == AudioClientMode.OPENAI:
        response = config.get_or_create_openai_audio_client().audio.speech.create(
            model=audio_model,
            voice=audio_voice,
            input=response_msg,
            instructions=audio_instructions,
            response_format="mp3",
            speed=1.0)
    else:
        response = config.get_or_create_opensource_audio_client().audio.speech.create(
            model=audio_model,
            voice=audio_voice,
            input=response_msg,
            instructions=audio_instructions,
            response_format="mp3",
            speed=1.0)

    with open(filename, "wb") as f:
        f.write(response.content)

    # Get audio duration for rate limiting
    audio = AudioSegment.from_file(io.BytesIO(response.content), format="mp3")
    duration_seconds = len(audio) / 1000.0  # pydub returns duration in milliseconds

    log(f'duration_seconds: {duration_seconds}')
    
    # Use duration as weight for rate limiting (duration in seconds)
    increment_resource_usage(ip_address, duration_seconds * config.server.usage.audio_cost_per_second)

    output_path = filename
    audio.export(output_path, format="mp3", codec="libmp3lame", bitrate="128k")

def save_metadata(filename: str, session_key: str):
    """Save metadata to audio file"""
    mp3 = MP3(filename)
    if mp3.tags is None:
        mp3.add_tags()

    # Use EasyID3 to set metadata
    tags = EasyID3(filename)
    tags["title"] = session_key
    tags["artist"] = "Translation"
    tags["album"] = session_key
    tags["genre"] = "Speech"
    tags.save()

def process_translation(request_model: TranslationRequest, ip_address: str):
    """Process a translation request in the background"""
    try:
        data_json = request_model.model_dump()
        log(f'Processing queued translation data: {data_json}')

        session_key = request_model.session_key

        session = get_or_create_translation_session(session_key)  # This starts the audio stream if it is not already running

        # Translate the message
        translated_text = translate_text(
            request_model.message,
            request_model.source_language,
            request_model.target_language,
            ip_address,
            request_model.model or ""
        )

        # Create directory for the session_key if it doesn't exist (use translation-specific directory)
        session_dir = Path(f'./generated-audio/translation/active/{request_model.session_key}')
        session_dir.mkdir(parents=True, exist_ok=True)
        
        sequence_str = session.generate_sequence_str()
        
        # Generate filename with sequence number
        filename = f'{sequence_str}_translation_{request_model.source_language}_to_{request_model.target_language}_{request_model.audio_voice}.mp3'
        full_name = f'./generated-audio/translation/active/{request_model.session_key}/{filename}'
        
        
        # Store the translation result
        translation_result = TranslationResult(
            message_id=request_model.message_id,
            original_message=request_model.message,
            translated_text=translated_text,
            source_language=request_model.source_language,
            target_language=request_model.target_language
        )
        session.add_translation(translation_result)
        
        save_audio(full_name, translated_text, request_model.audio_voice or "", request_model.audio_model or "", build_audio_instructions(request_model.target_language), ip_address)
        save_metadata(full_name, session_key)

        queue_translation_audio(session_key, filename)
        
        log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} translation (background): {request_model.source_language} -> {request_model.target_language}: {request_model.message[:50]}... -> {translated_text[:50]}... -> {filename}')
        
    except Exception as e:
        log(f'exception in process_translation: {e}')
        log(f'stack: {traceback.print_exc()}')

@app.post("/translation/translate")
@validate_session_key_decorator
@validate_audio_decorator
@rate_limit_decorator
@validate_chat_model_decorator
def translate(request_model: TranslationRequest, fastapi_request: Request):
    try:
        session_key = request_model.session_key

        # Extract IP address for rate limiting in background processing
        ip_address, error = get_ip_address_for_rate_limit(fastapi_request)
        if error:
            return JSONResponse(
                status_code=500,
                content={
                    "error": error
                }
            )

        session = get_or_create_translation_session(session_key)
        if session.contains_message_id(request_model.message_id):
            return JSONResponse(
                status_code=400,
                content={
                    "message_id": request_model.message_id, 
                    "error": f'Invalid message ID, already exists in translation with key {request_model.session_key}'
                }
            )
        
        # Queue the request for background processing in the audio generation queue
        queue_message_request(RequestType.TRANSLATION, request_model, ip_address, process_translation)
        
        # Return early with 425 status to indicate the request is being processed
        if config.icecast_client is not None and config.icecast_client.translation_stream_endpoint_prefix != "":
            stream_url = config.icecast_client.translation_stream_endpoint_prefix + session_key
            return JSONResponse(
                status_code=425,
                content={
                    "message_id": request_model.message_id,
                    "status": "processing",
                    "info": "Translation request queued for background processing",
                    "stream_url": stream_url
                }
            )
        else:
            return JSONResponse(
                status_code=425,
                content={
                    "message_id": request_model.message_id,
                    "status": "processing",
                    "info": "Translation request queued for background processing"
                }
            )
            
    except Exception as e:
        log(f'exception in /translation/translate: {e}')
        log(f'stack: {traceback.print_exc()}')
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Internal server error: {str(e)}"
            }
        )

@app.get("/translation/getTranslation")
def getTranslation(session_key: str, message_id: str):
    """Get a translation result by session_key and message_id"""
    if " " in session_key:
        return JSONResponse(
            status_code=400,
            content={
                "error": f'Invalid session key "{session_key}", it contains spaces',
            }
        )

    try:
        if session_key in active_translation_sessions.keys():
            session = active_translation_sessions[session_key]
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"There was no translation session with the session_key: {session_key}"
                }
            )
        
        translation = session.get_translation(message_id)
        if translation:
            return JSONResponse(
                status_code=200,
                content={
                    "message_id": message_id,
                    "original_message": translation.original_message,
                    "translated_text": translation.translated_text,
                    "source_language": translation.source_language,
                    "target_language": translation.target_language
                }
            )

        return JSONResponse(
            status_code=425,
            content={
                "message_id": message_id,
                "status": "processing",
                "info": f'Translation for message_id: {message_id} is not ready yet'
            }
        )
        
    except Exception as e:
        log(f'exception in /translation/getTranslation: {e}')
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Internal server error: {str(e)}"
            }
        )

