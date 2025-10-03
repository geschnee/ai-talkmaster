from fastapi import Request
from fastapi.responses import JSONResponse

from code.shared import app, config
from code.aitalkmaster_utils import log


@app.get("/statusOllamaProxy")
def status(request: Request):
    return JSONResponse( 
        status_code=200,
        content="status online")

@app.get("/models")
def get_available_models():
    """
    Returns the list of valid chat models from the configuration.
    Only shows models that are explicitly configured as valid_models.
    """
    try:
        # Get valid models from config
        valid_models = config.chat_client.valid_models
        
        if not valid_models:
            return JSONResponse(
                status_code=200,
                content={
                    "chat_client_mode": config.chat_client.mode,
                    "chat_models": [],
                    "count": 0,
                    "message": "No valid models configured"
                }
            )
        
        log(f'Retrieved {len(valid_models)} configured models for {config.chat_client.mode}')
        
        return JSONResponse(
            status_code=200,
            content={
                "chat_client_mode": config.chat_client.mode,
                "chat_models": valid_models,
                "count": len(valid_models)
            }
        )
        
    except Exception as e:
        log(f'Exception in /models: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
        )

@app.get("/voices")
def get_available_voices():
    """
    Returns the list of valid audio models and voices from the configuration.
    Only shows models and voices that are explicitly configured as valid.
    """
    try:
        # Get configured voices and models from config
        voices = config.audio_client.valid_voices
        models = config.audio_client.valid_models
        
        log(f'Retrieved {len(voices)} configured voices and {len(models)} configured models for {config.audio_client.mode}')
        
        return JSONResponse(
            status_code=200,
            content={
                "audio_client_mode": config.audio_client.mode,
                "default_voice": config.audio_client.default_voice,
                "default_model": config.audio_client.default_model,
                "valid_voices": voices,
                "audio_models": models,
                "voice_count": len(voices),
                "model_count": len(models)
            }
        )
        
    except Exception as e:
        log(f'Exception in /voices: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
        )

# Block everything else
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def block_everything(path: str):
    return JSONResponse(
            status_code=401,
            content={"message": "This endpoint is not available."}
        )