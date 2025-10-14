from fastapi.responses import JSONResponse
from datetime import datetime


from code.shared import app, config, log
from code.validation_decorators import validate_chat_model_decorator
from code.request_models import GenerateGetMessageResponseRequest, GenerateRequest
from code.config import ChatClientMode



response_queue = []
MAX_CHATS_NO_HISTORY = 1000

def getKey(username: str, model: str, prompt: str, system_instructions: str, optionstring: str):
    key = f'{username}:{model}:{prompt}:{system_instructions}:{optionstring}'
    return key

@app.get("/generate/getMessageResponse")
def generateGetMessageResponse(request: GenerateGetMessageResponseRequest):
    try:

        key = getKey(request.username, request.model, request.prompt, request.system_instructions, str(request.options))

        for response in response_queue:
            if response["key"]==key:
                return JSONResponse( 
                    status_code=200,
                    content=response["response"]
                )
            
        return JSONResponse(
            status_code=425,
            content={"message": f"requested response for {key} not in list"}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=f"Internal server error: {e}"
        )

def get_response_ollama_generate(request: GenerateRequest) -> str:
    response = config.get_or_create_ollama_chat_client().generate(model=request.model, prompt=request.prompt, system=request.system_instructions, options=request.options)
    
    log(f'response from ollama: {response}')
    return response["response"]
    
def get_response_openai_generate(request: GenerateRequest) -> str:
    response = config.get_or_create_openai_chat_client().responses.create(model=request.model, input=request.prompt, instructions=request.system_instructions)
    
    return response.output[0].content[0].text


@app.post("/generate/postMessage")
@validate_chat_model_decorator
def generate(request: GenerateRequest):
    log(f'generate/postMessage')
    try:
        if config.chat_client.mode == ChatClientMode.OPENAI:
            response_msg = get_response_openai_generate(request)
        elif config.chat_client.mode == ChatClientMode.OLLAMA:
            response_msg = get_response_ollama_generate(request)
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "error": f'unknown chat client mode: {config.chat_client.mode.value}'
                }
            )
        log(f'response generated')
        log(f'response: {response_msg}')

        log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} generate/postMessage: data:{request.model_dump()} response:{response_msg}')

        response_json = {
            "response": response_msg,
            "username": request.username,
            "prompt": request.prompt,
            "model": request.model
        }
                    
        # Store the response in our list
        d = {
            "key": getKey(request.username, request.model, request.prompt, request.system_instructions, str(request.options)),
            "response": response_json
        }
        log(f'key generated')
        response_queue.append(d)

        while len(response_queue)>=MAX_CHATS_NO_HISTORY:
            response_queue.pop()

        log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} generate/postMessage: data:{request.model_dump()} response:{response_msg}')
        
        return JSONResponse( 
            status_code=200,
            content=response_json
        )
    
    except Exception as e:
        log(f'exception in /api/generate: {e}')
        return JSONResponse(
            status_code=500,
            content=f"Internal server error: {str(e)}"
        )