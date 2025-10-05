from fastapi import FastAPI

import requests

# Import configuration system
from code.config import get_config


# Get configuration instance
config = get_config()


def log(message):
    with open(config.aitalkmaster.log_file, "a") as file:
        file.write(message + "\n")
    print(message)

app = FastAPI()

if config.chat_client.mode == "openai":
    models = config.get_or_create_openai_chat_client().models.list()

    all_model_names = [model.id for model in models]

    log(f'list of Openai model names: {all_model_names}')
    
    for model in config.chat_client.valid_models:
        if model not in all_model_names:
            log(f'{model} is not availible in Openai endpoint, please change chat client valid_models config')
            exit()
    
elif config.chat_client.mode == "ollama":
    
    def get_models() -> list:
        thelist = requests.get(config.chat_client.base_url+"/api/tags")
        jsondata = thelist.json()
        result = list()

        for model in jsondata["models"]:
            result.append(model["model"])

        return result

    ollama_models = get_models()
    
    for model in config.chat_client.valid_models:
        if model not in ollama_models:
            log(f'{model} is not availible in Ollama endpoint, please change chat client valid_models config')
            log(f'list of Ollama model names: {ollama_models}')
            exit()

    # TODO test which one works, preferably the first one


if config.audio_client.mode == "openai":
    models = config.get_or_create_openai_audio_client().models.list()

    all_model_names = [model.id for model in models]

    
    
    for model in config.audio_client.valid_models:
        if model not in all_model_names:
            log(f'{model} is not availible in Openai endpoint, please change audio client valid_models config')
            log(f'list of Openai model names: {all_model_names}')
            exit()


    openai_voices = ["alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse"]
    
    log(f'list of Openai voice names: {openai_voices}')
    for voice in config.audio_client.valid_voices:
        if voice not in openai_voices:
            log(f'{voice} is not availible in Openai, please change audio client valid_voices config')
            exit()
    
elif config.audio_client.mode == "ollama":

    # TODO test this
    models = config.get_or_create_ollama_audio_client().models.list()
    
    all_model_names = [model.id for model in models]

    log(f'list of Ollama model names: {all_model_names}')
    
    for model in config.audio_client.valid_models:
        if model not in all_model_names:
            log(f'{model} is not availible in Ollama endpoint, please change audio client valid_models config')
            exit()

    def get_models() -> list:
        thelist = requests.get(config.audio_client.base_url+"/api/tags")
        jsondata = thelist.json()
        result = list()

        for model in jsondata["models"]:
            result.append(model["model"])

        return result

    models = get_models()
    log(f'Availible Ollama Models:')
    for model in models:
        log(model)
    
    # Validate voices for Ollama audio client (Kokoro)
    # For Kokoro, we need to check what voices are available
    # Since Kokoro might have different voice options, we'll validate against a known set
    # or make an API call to get available voices if the endpoint supports it
    try:
        # Try to get available voices from Kokoro endpoint
        voices_response = requests.get(config.audio_client.base_url.replace("/v1", "") + "/voices", timeout=10)
        if voices_response.status_code == 200:
            available_voices = voices_response.json()
            log(f'Available Kokoro voices: {available_voices}')
            
            for voice in config.audio_client.valid_voices:
                if voice not in available_voices:
                    log(f'{voice} is not available in Kokoro endpoint, please change audio client valid_voices config')
                    exit()
        else:
            log(f'Error validating Kokoro voices: {voices_response.status_code}')
            exit()
    except Exception as e:
        log(f'Error validating Kokoro voices: {e}')
        # Fallback validation
        kokoro_valid_voices = ["default", "female", "male"]
        log(f'Using fallback Kokoro voices: {kokoro_valid_voices}')
        
        for voice in config.audio_client.valid_voices:
            if voice not in kokoro_valid_voices:
                log(f'{voice} is not a known Kokoro voice, please change audio client valid_voices config')
                exit()