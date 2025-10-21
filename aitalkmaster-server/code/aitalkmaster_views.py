from fastapi.responses import JSONResponse
from fastapi import Request
import time
from pathlib import Path
import uuid
import shutil
from datetime import datetime
from mutagen.easyid3 import EasyID3

import traceback

from code.config import ChatClientMode, AudioClientMode
from code.aitalkmaster_utils import AitalkmasterInstance, remove_name, start_liquidsoap
from code.request_models import AitPostMessageRequest, AitMessageResponseRequest, AitResetJoinkeyRequest, AitGenerateAudioRequest, AitStartConversationRequest
from code.validation_decorators import validate_chat_model_decorator, validate_audio_decorator, rate_limit_decorator
from code.shared import app, config, log
from pydub import AudioSegment
from code.openai_response import CharacterResponse
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
import io
from code.rate_limiter import get_ip_address_for_rate_limit, increment_resource_usage

active_aitalkmaster_instances = {}
finished_aitalkmaster_instances = []

# Track audio file sequence numbers per join_key
audio_sequence_counters = {}

# Get or initialize sequence counter for this join_key
def generate_sequence_str(join_key: str):
    if join_key not in audio_sequence_counters:
        audio_sequence_counters[join_key] = 0
    
    # Increment sequence counter for this join_key
    audio_sequence_counters[join_key] += 1
    sequence_number = audio_sequence_counters[join_key]
    
    # Format sequence number with leading zeros for proper sorting (e.g., 001, 002, 003)
    sequence_str = f"{sequence_number:03d}"
    return sequence_str

def save_audio(filename: str, response_msg: str, audio_voice: str, audio_model: str, audio_instructions: str, fastapi_request: Request):
    if config.audio_client.mode == AudioClientMode.OPENAI:
        response = config.get_or_create_openai_audio_client().audio.speech.create(
            model=audio_model,
            voice=audio_voice,
            input=response_msg,
            instructions=audio_instructions,
            response_format="mp3",
            speed=1.0)
        
        
        # log(f'headers: {response.response.headers}')
        # the headers do not provide a direct "cost"
        # we should use the duration of the audio to estimate the cost
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
    
    ip_address, _ = get_ip_address_for_rate_limit(fastapi_request)
    # Use duration as weight for rate limiting (duration in seconds)
    increment_resource_usage(ip_address, duration_seconds * config.server.usage.audio_cost_per_second)

    output_path = filename
    audio.export(output_path, format="mp3", bitrate="192k")


def save_metadata(filename: str, name: str, join_key: str):
    mp3 = MP3(filename)
    if mp3.tags is None:
        mp3.add_tags()

    # Use EasyID3 to set metadata
    tags = EasyID3(filename)
    tags["title"] = join_key
    tags["artist"] = "AIT " + name
    tags["album"] = join_key
    tags["genre"] = "Speech"
    tags.save()

def move_audio_files_to_inactive(join_key: str):
    """Move audio files from active to inactive folder when conversation is reset"""
    try:
        # Create inactive directory structure
        inactive_base_dir = Path('./generated-audio/inactive')
        inactive_base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create date-based subfolder
        current_date = datetime.now().strftime("%Y%m%d-%H%M%S")
        inactive_dir = inactive_base_dir / f"{join_key}_{current_date}"
        inactive_dir.mkdir(parents=True, exist_ok=True)
        
        # Source directory (active conversation)
        active_dir = Path(f'./generated-audio/active/{join_key}')
        
        if active_dir.exists():
            # Move all files from active to inactive directory
            for file_path in active_dir.iterdir():
                if file_path.is_file():
                    destination = inactive_dir / file_path.name
                    shutil.move(str(file_path), str(destination))
                    log(f'Moved audio file: {file_path} -> {destination}')
            
            # We only make the directory empty, removing the active directory itself would stop the audio stream.
            
            return True
        else:
            log(f'No active directory found for join_key: {join_key}')
            return False
            
    except Exception as e:
        log(f'Error moving audio files for {join_key}: {e}')
        return False

def get_response_ollama(request: AitPostMessageRequest, ait_instance: AitalkmasterInstance, fastapi_request: Request) -> str:
    full_dialog = []
    full_dialog.append({
        "role": "system",
        "content": request.system_instructions  
    })
    for d in ait_instance.getDialog():
        full_dialog.append(d)

    response = config.get_or_create_ollama_chat_client().chat(model=request.model, messages = full_dialog, options=request.options)
    
    response_msg = remove_name(response["message"]["content"], request.charactername)

  

    log(f'response: {response}')
    log(f'eval count: {response["eval_count"]}')

    ip_address, _ = get_ip_address_for_rate_limit(fastapi_request)
    increment_resource_usage(ip_address, response["eval_count"])
    
    return response_msg

def get_response_openai(request: AitPostMessageRequest, ait_instance: AitalkmasterInstance, fastapi_request: Request) -> str:

    response = config.get_or_create_openai_chat_client().responses.parse(
        model=request.model,
        input=ait_instance.getDialog(),
        instructions=request.system_instructions,
        text_format=CharacterResponse,
        store=False
    )

    ip_address, _ = get_ip_address_for_rate_limit(fastapi_request)
    increment_resource_usage(ip_address, response.usage.total_tokens)

    return response.output_parsed.text_response # type: ignore

def build_filename(request: AitPostMessageRequest):
    # Create subdirectory for the join_key in active folder
    join_key_dir = Path(f'./generated-audio/active/{request.join_key}')
    join_key_dir.mkdir(parents=True, exist_ok=True)
    
    sequence_str = generate_sequence_str(request.join_key)
    
    fn = f'./generated-audio/active/{request.join_key}/{sequence_str}_{request.charactername}_{request.message_id}_{request.audio_voice}_{str(uuid.uuid4())}.mp3'
    return fn


def get_or_create_ait_instance(join_key: str) -> AitalkmasterInstance:
    if join_key in active_aitalkmaster_instances.keys():
        ait_instance = active_aitalkmaster_instances[join_key]
    else:
        reset_aitalkmaster(join_key)
        ait_instance = AitalkmasterInstance(join_key=join_key)
        if config.liquidsoap_client is not None:
            start_liquidsoap(join_key)
        active_aitalkmaster_instances[join_key] = ait_instance
    return ait_instance


@app.post("/ait/postMessage")
@validate_chat_model_decorator
@validate_audio_decorator
@rate_limit_decorator
def postaitMessage(request_model: AitPostMessageRequest, fastapi_request: Request):
    try:
        data_json = request_model.model_dump()
        log(f'postMessage data: {data_json}')

        join_key = request_model.join_key

        ait_instance = get_or_create_ait_instance(join_key)

        if ait_instance.contains_message_id(request_model.message_id):
            return JSONResponse(
                status_code=400,
                content={
                    "message_id": request_model.message_id, 
                    "error": f'Invalid message ID, already exists in ait with key {request_model.join_key}'
                }
            )
        
        ait_instance.addUserMessage(request_model.message, name=request_model.username, message_id=request_model.message_id)
        

        if config.chat_client.mode == ChatClientMode.OPENAI:
            response_msg = get_response_openai(request_model, ait_instance, fastapi_request)
        elif config.chat_client.mode == ChatClientMode.OLLAMA:
            response_msg = get_response_ollama(request_model, ait_instance, fastapi_request)
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "error": f'unknown chat client mode: {config.chat_client.mode}'
                }
            )

        if config.audio_client is not None:
            filename = build_filename(request_model)
        else:
            filename = None

        ait_instance.addResponse(response_msg, request_model.charactername, response_id=request_model.message_id, filename=filename)

        if config.audio_client is not None:
            save_audio(filename, response_msg, request_model.audio_voice or "", request_model.audio_model or "", request_model.audio_instructions or "", fastapi_request)
            save_metadata(filename, request_model.charactername, join_key)
        
            ait_instance.set_audio_created_at(request_model.message_id, time.time())
        
        log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} ait/postMessage: data: {request_model.message} response: {response_msg}')
        

        return JSONResponse(
            status_code=200,
            content={
                "message_id": request_model.message_id, 
                "response": response_msg
            }
        )
    except Exception as e:
        log(f'exception in /ait/postMessage: {e}')
        log(f'stack: {traceback.print_exc()}')
        return JSONResponse(
            status_code=500,
            content=f"Internal server error: {str(e)}"
        )

@app.get("/ait/getMessageResponse")
@rate_limit_decorator
def getaitMessageResponse(request_model: AitMessageResponseRequest, fastapi_request: Request):
    try:
        join_key = request_model.join_key

        if join_key in active_aitalkmaster_instances.keys():
            ait_instance = active_aitalkmaster_instances[join_key]
        else:
            return JSONResponse(
                status_code=400,
                content=f"There was no conversation with the join_key: {join_key}"
            )

        message_id = request_model.message_id
        
        for assistant_resp in ait_instance.assistant_responses:
            if assistant_resp.response_id == message_id:
                return JSONResponse(
                    status_code=200,
                    content={
                        "message_id": message_id, 
                        "response": assistant_resp.response
                    }
                )

        return JSONResponse(
            status_code=425,
            content=f'There was no response for response_id: {message_id}'
        )
        
    except Exception as e:
        log(f'exception in /ait/getMessageResponse: {e}')
        return JSONResponse(
            status_code=500,
            content=f"Internal server error: {str(e)}"
        )
    
def reset_aitalkmaster(join_key: str):
    # We do not stop the liquidsoap stream since that would lead to an interruption in the OpenSimulator viewers' audio stream.

    if config.audio_client is not None:
        move_audio_files_to_inactive(join_key)

    if join_key in active_aitalkmaster_instances.keys():
        finished_aitalkmaster_instances.append(active_aitalkmaster_instances[join_key])

        del active_aitalkmaster_instances[join_key]
        
        # Reset the sequence counter for this join_key
        if join_key in audio_sequence_counters:
            del audio_sequence_counters[join_key]

@app.post("/ait/resetJoinkey")
@rate_limit_decorator
def resetJoinkey(request_model: AitResetJoinkeyRequest, fastapi_request: Request):
    try:
        join_key = request_model.join_key

        if join_key in active_aitalkmaster_instances.keys():
            reset_aitalkmaster(join_key)

            log(f'conv has been reset: {join_key}')
        else:
            log(f'conv resetRequest for key but key not found: {join_key}')
        return JSONResponse(
            status_code=200,
            content=f"{join_key} has been reset"
        )
    except Exception as e:
        log(f'exception in /ait/resetJoinkey: {e}')
        return JSONResponse(
            status_code=500,
            content=f"Internal server error: {str(e)}"
        )

@app.post("/ait/startConversation")
def startStream(request_model: AitStartConversationRequest, fastapi_request: Request):
    try:
        join_key = request_model.join_key

        if join_key in active_aitalkmaster_instances.keys():
            if config.icecast_client is not None and config.icecast_client.stream_endpoint_prefix != "":
                stream_url = config.icecast_client.stream_endpoint_prefix + join_key
                return JSONResponse(
                    status_code=200,
                    content=f'AIT conversation with join_key {join_key} is already running. You can listen to the audio stream at {stream_url} as region audio or using VLC Media player.'
                )
            else:
                return JSONResponse(
                    status_code=200,
                    content=f'AIT conversation with join_key {join_key} is already running.'
                )
        else:
            _ = get_or_create_ait_instance(join_key)
            if config.icecast_client is not None and config.icecast_client.stream_endpoint_prefix != "":
                stream_url = config.icecast_client.stream_endpoint_prefix + join_key
                return JSONResponse(
                    status_code=200,
                    content=f'Started AIT conversation with join_key {join_key}. You can listen to the audio stream at {stream_url} as region audio or using VLC Media player.'
                )
            else:
                return JSONResponse(
                    status_code=200,
                    content=f'Started AIT conversation with join_key {join_key}.'
                )

    except Exception as e:
        log(f'exception in /ait/startConversation: {e}')
        return JSONResponse(
            status_code=500,
            content=f"Internal server error: {str(e)}"
        )

@app.post("/ait/generateAudio")
@validate_audio_decorator
@rate_limit_decorator
def generateAudio(request_model: AitGenerateAudioRequest, fastapi_request: Request):
    try:

        if config.audio_client is None:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f'audio is not available on this AI Talkmaster server'
                }
            )

        join_key = request_model.join_key

        _ = get_or_create_ait_instance(join_key) # This starts the audio stream if it is not already running

        # Create directory for the join_key if it doesn't exist
        join_key_dir = Path(f'./generated-audio/active/{request_model.join_key}')
        join_key_dir.mkdir(parents=True, exist_ok=True)
        
        sequence_str = generate_sequence_str(request_model.join_key)
        
        # Generate filename with sequence number
        filename = f'./generated-audio/active/{request_model.join_key}/{sequence_str}_{request_model.username}_{request_model.message_id}_{request_model.audio_voice}_{str(uuid.uuid4())}.mp3'
        
        save_audio(filename, request_model.message, request_model.audio_voice, request_model.audio_model, request_model.audio_instructions, fastapi_request)

        save_metadata(filename, request_model.username, join_key)
        
        log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} generateAudio: message: {request_model.message} -> {filename}')
        
        return JSONResponse(
            status_code=200,
            content={
                "message_id": request_model.message_id,
                "filename": filename,
                "status": "success"
            }
        )
        
    except Exception as e:
        log(f'exception in /ait/generateAudio: {e}')
        log(f'stack: {traceback.print_exc()}')
        return JSONResponse(
            status_code=500,
            content={
                "message_id": request_model.message_id,
                "error": f"Internal server error: {str(e)}"
            }
        )