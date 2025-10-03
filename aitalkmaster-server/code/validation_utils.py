
import requests

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