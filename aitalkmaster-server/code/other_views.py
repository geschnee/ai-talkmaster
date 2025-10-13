from fastapi import Request
from fastapi.responses import JSONResponse

from code.shared import app, config
from code.aitalkmaster_utils import log

@app.get("/statusAitalkmaster")
def status(request: Request):
    return JSONResponse( 
        status_code=200,
        content="status online")

@app.get("/chat_models")
def get_available_models():
    
    try:
        # Get valid models from config
        allowed_models = config.chat_client.allowed_models
        
        return JSONResponse(
            status_code=200,
            content={
                "chat_client_mode": config.chat_client.mode,
                "chat_models": allowed_models,
                "count": len(allowed_models)
            }
        )
    except Exception as e:
        log(f'Exception in /models: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
        )

@app.get("/audio_models")
def get_available_voices():
    try:
        # Get configured voices and models from config

        if config.audio_client is None:
            return JSONResponse(
                status_code=400,
                content={"error": f"Audio client is not configured"}
            )

        voices = config.audio_client.allowed_voices
        models = config.audio_client.allowed_models
        
        log(f'Retrieved {len(voices)} configured voices and {len(models)} configured models for {config.audio_client.mode}')
        
        return JSONResponse(
            status_code=200,
            content={
                "audio_client_mode": config.audio_client.mode,
                "default_voice": config.audio_client.default_voice,
                "default_model": config.audio_client.default_model,
                "allowed_voices": voices,
                "audio_models": models,
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