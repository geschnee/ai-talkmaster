
import random
from fastapi import Request
from fastapi.responses import JSONResponse
import time
from fastapi.responses import StreamingResponse
from pathlib import Path
import uuid
import shutil
from datetime import datetime

import traceback

from code.aitalkmaster_utils import PostMessageRequest, TheaterPlay, time_str, get_audio_duration, remove_name, MessageResponseRequest, ResetTheaterRequest, ChatResponse, start_liquidsoap
from code.validation_utils import validate_chat_model, validate_audio_voice, validate_audio_model
from code.shared import app, config, log


active_theater_plays = {}
finished_theater_plays = []



# Track audio file sequence numbers per join_key
audio_sequence_counters = {}



def save_audio(filename: str, response_msg: str, audio_voice: str, audio_model: str, audio_description: str):
    if config.audio_client.mode == "openai":
        response = config.get_or_create_openai_audio_client().audio.speech.create(
            model=audio_model,
            voice=audio_voice,
            input=response_msg,
            instructions=audio_description,
            response_format="mp3",
            speed=1.0)
    else:
        response = config.get_or_create_ollama_audio_client().audio.speech.create(
            model=audio_model,
            voice=audio_voice,
            input=response_msg,
            instructions=audio_description,
            response_format="mp3",
            speed=1.0)
    with open(filename, "wb") as f:
        f.write(response.content)

def move_audio_files_to_inactive(join_key: str):
    """Move audio files from active to inactive folder when conversation is reset"""
    try:
        # Create inactive directory structure
        inactive_base_dir = Path('./generated-audio/inactive')
        inactive_base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create date-based subfolder
        current_date = datetime.now().strftime("%Y%m%d")
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
            
            # Remove the now-empty active directory
            active_dir.rmdir()
            log(f'Removed empty active directory: {active_dir}')
            
            return True
        else:
            log(f'No active directory found for join_key: {join_key}')
            return False
            
    except Exception as e:
        log(f'Error moving audio files for {join_key}: {e}')
        return False



def get_response_ollama(request: PostMessageRequest, play: TheaterPlay) -> str:
        
    full_dialog = []
    full_dialog.append({
        "role": "system",
        "content": request.system_instructions  
    })
    for d in play.getDialog():
        full_dialog.append(d)

    response = config.get_or_create_ollama_chat_client().chat(model=request.model, messages = full_dialog, options=request.options)
    
    response_msg = remove_name(response["message"]["content"], request.charactername)
    
    return response_msg

def get_response_openai(request: PostMessageRequest, play: TheaterPlay) -> str:

    response = config.get_or_create_openai_chat_client().responses.parse(
        model=request.model,
        input=play.getDialog(),
        instructions=request.system_instructions,
        text_format=ChatResponse,
        store=False
    )

    return response.output_parsed.text_response # type: ignore

def build_filename(request: PostMessageRequest):
    # Create subdirectory for the join_key in active folder
    join_key_dir = Path(f'./generated-audio/active/{request.join_key}')
    join_key_dir.mkdir(parents=True, exist_ok=True)
    
    # Get or initialize sequence counter for this join_key
    if request.join_key not in audio_sequence_counters:
        audio_sequence_counters[request.join_key] = 0
    
    # Increment sequence counter for this join_key
    audio_sequence_counters[request.join_key] += 1
    sequence_number = audio_sequence_counters[request.join_key]
    
    # Format sequence number with leading zeros for proper sorting (e.g., 001, 002, 003)
    sequence_str = f"{sequence_number:03d}"
    
    fn = f'./generated-audio/active/{request.join_key}/{sequence_str}_{request.charactername}_{request.message_id}_{request.audio_voice}_{str(uuid.uuid4())}.mp3'
    return fn


def get_or_create_theater_play(join_key: str) -> TheaterPlay:
    if join_key in active_theater_plays.keys():
        play = active_theater_plays[join_key]
    else:
        play = TheaterPlay(join_key=join_key)
        liquidsoap_success = start_liquidsoap(join_key)
        active_theater_plays[join_key] = play
    return play

@app.post("/aiT/postMessage")
def postaiTMessage(request: PostMessageRequest):
    try:
        data_json = request.model_dump()
        log(f'postMessage data: {data_json}')

        # Validate chat model
        is_valid_model, model_error, available_models = validate_chat_model(request.model)
        if not is_valid_model:
            return JSONResponse(
                status_code=400,
                content={
                    "message_id": request.message_id,
                    "error": f"Invalid chat model: {model_error}",
                    "available_models": available_models
                }
            )

        # Set defaults for audio parameters if empty
        if request.audio_voice == "":
            request.audio_voice = config.audio_client.default_voice
        if request.audio_model == "":
            request.audio_model = config.audio_client.default_model

        # Validate audio voice
        is_valid_voice, voice_error, available_voices = validate_audio_voice(request.audio_voice or "")
        if not is_valid_voice:
            return JSONResponse(
                status_code=400,
                content={
                    "message_id": request.message_id,
                    "error": f"Invalid audio voice: {voice_error}",
                    "available_voices": available_voices
                }
            )

        # Validate audio model
        is_valid_audio_model, audio_model_error, available_audio_models = validate_audio_model(request.audio_model or "")
        if not is_valid_audio_model:
            return JSONResponse(
                status_code=400,
                content={
                    "message_id": request.message_id,
                    "error": f"Invalid audio model: {audio_model_error}",
                    "available_audio_models": available_audio_models
                }
            )

        join_key = request.join_key

        play = get_or_create_theater_play(join_key)

        if play.contains_message_id(request.message_id):
            # TODO fix return codes and scripts
            return JSONResponse(
                status_code=400, # TODO use a code, that the owner get messaged
                content={
                    "message_id": request.message_id, 
                    "error": f'Invalid message ID, already exists in aiT with key {request.join_key}'
                }
            )
        
        play.addUserMessage(request.message, name=request.username, message_id=request.message_id)
        

        if config.chat_client.mode == "openai":
            response_msg = get_response_openai(request, play)
        elif config.chat_client.mode == "ollama":
            log(f'before get_response_ollama')
            response_msg = get_response_ollama(request, play)
            log(f'obtained response_msg from ollama: {response_msg}')
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "error": f'unknown chat client mode: {config.chat_client.mode}'
                }
            )

        filename = build_filename(request)



        play.addResponse(response_msg, request.charactername, response_id=request.message_id, filename=filename)

        

        filename = save_audio(filename, response_msg, request.audio_voice or "", request.audio_model or "", request.audio_description or "")
        
        
        play.set_audio_created_at(request.message_id, time.time())
        
        log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} aiTSendMessage: data: {request.message} response: {response_msg}')
        


        return JSONResponse(
            status_code=200,
            content={
                "message_id": request.message_id, 
                "response": response_msg
            }
        )
    except Exception as e:
        log(f'exception in /aiT/postMessage: {e}')
        log(f'stack: {traceback.print_exc()}')
        return JSONResponse(
            status_code=500,
            content=f"Internal server error: {str(e)}"
        )

@app.post("/aiT/getMessageResponse")
def getaiTMessageResponse(request: MessageResponseRequest):
    try:
        join_key = request.join_key

        if join_key in active_theater_plays.keys():
            play = active_theater_plays[join_key]
        else:
            print(f'no active conv with key: {join_key}')
            return JSONResponse(
                status_code=400,
                content=f"There was no conversation with the join_key: {join_key}"
            )

        message_id = request.message_id
        
        for assistant_resp in play.assistant_responses:
            if assistant_resp.response_id == message_id:
                return JSONResponse(
                    status_code=200,
                    content={
                        "message_id": message_id, 
                        "response": assistant_resp.response
                    }
                )

        return JSONResponse(
            status_code=400,
            content=f'There was no response for response_id: {message_id}'
        )
        
    except Exception as e:
        log(f'exception in /aiT/getMessageResponse: {e}')
        return JSONResponse(
            status_code=500,
            content=f"Internal server error: {str(e)}"
        )
    
def stop_aitstream(join_key: str):
    # Move audio files to inactive folder before resetting
    move_success = move_audio_files_to_inactive(join_key)
    if move_success:
        log(f'Successfully moved audio files for {join_key} to inactive folder')
    else:
        log(f'Warning: Failed to move some audio files for {join_key}')
    
    finished_theater_plays.append(active_theater_plays[join_key])

    del active_theater_plays[join_key]
    
    # Reset the sequence counter for this join_key
    if join_key in audio_sequence_counters:
        del audio_sequence_counters[join_key]

@app.post("/aiT/resetTheater")
def resetTheater(request: ResetTheaterRequest):
    try:
        join_key = request.join_key

        if join_key in active_theater_plays.keys():
            stop_aitstream(join_key)

            log(f'conv has been reset: {join_key}')
        else:
            log(f'conv resetRequest for key but key not found: {join_key}')
        return JSONResponse(
            status_code=200,
            content=f"{join_key} has been reset"
        )
    except Exception as e:
        log(f'exception in /resetTheater: {e}')
        return JSONResponse(
            status_code=500,
            content=f"Internal server error: {str(e)}"
        )
