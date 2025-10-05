
import requests
from functools import wraps
from fastapi.responses import JSONResponse

from code.shared import app, config

def validate_chat_model(model: str) -> tuple[bool, str, list]:
    """
    Validate if the provided model is available in the current chat client.
    
    Returns:
        tuple: (is_valid, error_message, available_models_list)
    """
    try:
        # Get available models from config
        available_models = config.chat_client.valid_models
        
        # If no models configured, fall back to dynamic fetching
        if not available_models:
            if config.chat_client.mode == "openai":
                try:
                    openai_client = config.get_or_create_openai_chat_client()
                    openai_models = openai_client.models.list()
                    available_models = [model.id for model in openai_models.data]
                except Exception as e:
                    return False, f"Error fetching OpenAI models: {str(e)}", []
                    
            elif config.chat_client.mode == "ollama":
                try:
                    response = requests.get(config.chat_client.base_url + "/api/tags", timeout=10)
                    response.raise_for_status()
                    jsondata = response.json()
                    available_models = [model["name"] for model in jsondata["models"]]
                except Exception as e:
                    return False, f"Error fetching Ollama models: {str(e)}", []
            else:
                return False, f"Unknown chat client mode: {config.chat_client.mode}", []
        
        # Validate the model
        if model not in available_models:
            return False, f"Model '{model}' not available", available_models
        
        return True, "", available_models
        
    except Exception as e:
        return False, f"Error validating model: {str(e)}", []

def validate_audio_voice(voice: str) -> tuple[bool, str, list]:
    """
    Validate if the provided voice is available in the current audio client.
    
    Returns:
        tuple: (is_valid, error_message, available_voices_list)
    """
    try:
        available_voices = config.audio_client.valid_voices
        
        
        if voice not in available_voices:
            return False, f"Voice '{voice}' not available", available_voices
        
        return True, "", available_voices
        
    except Exception as e:
        return False, f"Error validating voice: {str(e)}", []

def validate_audio_model(model: str) -> tuple[bool, str, list]:
    """
    Validate if the provided audio model is available in the current audio client.
    
    Returns:
        tuple: (is_valid, error_message, available_models_list)
    """
    try:
        available_models = config.audio_client.valid_models
        
        if model not in available_models:
            return False, f"Audio model '{model}' not available", available_models
        
        return True, "", available_models
        
    except Exception as e:
        return False, f"Error validating audio model: {str(e)}", []

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
            
        is_valid_voice, voice_error, available_voices = validate_audio_voice(request.audio_voice)
        if not is_valid_voice:
            return JSONResponse(
                status_code=400,
                content={
                    "message_id": request.message_id,
                    "error": f"Invalid audio voice: {voice_error}",
                    "available_voices": available_voices
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


        is_valid_audio_model, audio_model_error, available_audio_models = validate_audio_model(request.audio_model)
        if not is_valid_audio_model:
            return JSONResponse(
                status_code=400,
                content={
                    "message_id": request.message_id,
                    "error": f"Invalid audio model: {audio_model_error}",
                    "available_audio_models": available_audio_models
                }
            )
        
        # If validation passes, call the original function
        return func(request, *args, **kwargs)
    
    return wrapper