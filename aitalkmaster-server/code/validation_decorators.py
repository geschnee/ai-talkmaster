import requests
from functools import wraps
from fastapi.responses import JSONResponse

from code.shared import config

def check_chat_model(model: str) -> tuple[bool, list]:
    # Get available models from config
    available_models = config.chat_client.allowed_models
        
    if model not in available_models:
        return False, available_models
        
    return True, available_models

def check_audio_voice(voice: str) -> tuple[bool, list]:
    allowed_voices = config.audio_client.allowed_voices
        
    if voice not in allowed_voices:
        return False, allowed_voices
        
    return True, allowed_voices
        
def check_audio_model(model: str) -> tuple[bool, list]:
    
    available_models = config.audio_client.allowed_models
    if model not in available_models:
        return False, available_models
        
    return True, available_models
        

def validate_chat_model_decorator(func):
    """
    Decorator to validate chat model in request parameters.
    Expects the function to receive a request object with 'model' and 'message_id' attributes.
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        # Validate chat model
        if request.model == "":
            request.model = config.chat_client.default_model

        is_valid_model, available_models = check_chat_model(request.model)
        if not is_valid_model:
            return JSONResponse(
                status_code=400,
                content={
                    "message_id": request.message_id,
                    "error": f"Invalid chat model: {request.model}",
                    "available_models": available_models
                }
            )
        
        # If validation passes, call the original function
        return func(request, *args, **kwargs)
    
    return wrapper

def validate_audio_voice_decorator(func):
    """
    Decorator to validate audio voice in request parameters.
    Expects the function to receive a request object with 'audio_voice' and 'message_id' attributes.
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        # Validate audio voice
        
        if request.audio_voice == "":
            request.audio_voice = config.audio_client.default_voice
            
        is_valid_voice, allowed_voices = check_audio_voice(request.audio_voice)
        if not is_valid_voice:
            return JSONResponse(
                status_code=400,
                content={
                    "message_id": request.message_id,
                    "error": f"Invalid audio voice: {request.audio_voice}",
                    "allowed_voices": allowed_voices
                }
            )
        
        # If validation passes, call the original function
        return func(request, *args, **kwargs)
    
    return wrapper

def validate_audio_model_decorator(func):
    """
    Decorator to validate audio model in request parameters.
    Expects the function to receive a request object with 'audio_model' and 'message_id' attributes.
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        # Validate audio model
        if request.audio_model == "":
            request.audio_model = config.audio_client.default_model


        is_valid_audio_model, available_audio_models = check_audio_model(request.audio_model)
        if not is_valid_audio_model:
            return JSONResponse(
                status_code=400,
                content={
                    "message_id": request.message_id,
                    "error": f"Invalid audio model: {request.audio_model}",
                    "available_audio_models": available_audio_models
                }
            )
        
        # If validation passes, call the original function
        return func(request, *args, **kwargs)
    
    return wrapper