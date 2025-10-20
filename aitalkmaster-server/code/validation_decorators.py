import requests
from functools import wraps
from fastapi.responses import JSONResponse
from fastapi import Request

from code.shared import config, log
from code.rate_limiter import rate_limit_exceeded, get_ip_address_for_rate_limit

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
    @wraps(func)
    def wrapper(request_model, fastapi_request: Request, *args, **kwargs):
        # Validate chat model
        if request_model.model == "":
            request_model.model = config.chat_client.default_model

        is_valid_model, available_models = check_chat_model(request_model.model)
        if not is_valid_model:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"Invalid chat model: {request_model.model}",
                    "available_models": available_models
                }
            )
        
        # If validation passes, call the original function
        return func(request_model, fastapi_request, *args, **kwargs)
    
    return wrapper

def validate_audio_decorator(func):

    @wraps(func)
    def wrapper(request_model, fastapi_request: Request, *args, **kwargs):


        if config.audio_client is None:
            # no need for audio validation
            return func(request_model, fastapi_request, *args, **kwargs)

        # Validate audio model
        if request_model.audio_model == "":
            request_model.audio_model = config.audio_client.default_model

        if request_model.audio_voice == "":
            request_model.audio_voice = config.audio_client.default_voice


        is_valid_audio_model, available_audio_models = check_audio_model(request_model.audio_model)
        if not is_valid_audio_model:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"Invalid audio model: {request_model.audio_model}",
                    "available_audio_models": available_audio_models
                }
            )

        is_valid_voice, allowed_voices = check_audio_voice(request_model.audio_voice)
        if not is_valid_voice:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"Invalid audio voice: {request_model.audio_voice}",
                    "allowed_voices": allowed_voices
                }
            )
        
        # If validation passes, call the original function
        return func(request_model, fastapi_request, *args, **kwargs)
    
    return wrapper




def rate_limit_decorator(func):
    """
    Decorator that checks if the request is within the weighted rate limit.
    """
    @wraps(func)
    def wrapper(request_model, fastapi_request: Request, *args, **kwargs):
        log(f'Rate limit check for IP: {fastapi_request.client.host}')

        if config.server.usage.use_rate_limit:
            ip_address, error = get_ip_address_for_rate_limit(fastapi_request)
            if error:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": error
                    }
                )
        
            if rate_limit_exceeded(ip_address):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Daily rate limit exceeded",
                        "ip_address": ip_address
                    }
                )
            else:
                return func(request_model, fastapi_request, *args, **kwargs)

        else:
            return func(request_model, fastapi_request, *args, **kwargs)

    
    return wrapper