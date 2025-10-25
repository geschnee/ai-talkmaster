from fastapi.responses import JSONResponse
from datetime import datetime


from code.shared import app, config, log, llm_log
from code.validation_decorators import validate_chat_model_decorator, rate_limit_decorator
from code.request_models import GenerateGetMessageResponseRequest, GenerateRequest
from code.config import ChatClientMode
from code.rate_limiter import get_ip_address_for_rate_limit, increment_resource_usage
from fastapi import Request


generate_response_queue = []
MAX_CHATS_NO_HISTORY = 1000


@app.get("/generate/getMessageResponse")
def generateGetMessageResponse(request: GenerateGetMessageResponseRequest):
    try:

        
        for response in generate_response_queue:
            if response["message_id"]==request.message_id:
                return JSONResponse( 
                    status_code=200,
                    content={
                        "message_id": request.message_id,
                        "response": response["response"]
                    }
                )
            
        return JSONResponse(
            status_code=425,
            content={"message": f"requested response for {request.message_id} not in list"}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=f"Internal server error: {e}"
        )

def get_response_ollama_generate(request: GenerateRequest, fastapi_request: Request) -> str:
    response = config.get_or_create_ollama_chat_client().generate(model=request.model, prompt=request.message, system=request.system_instructions, options=request.options)

    ip_address, _ = get_ip_address_for_rate_limit(fastapi_request)
    increment_resource_usage(ip_address, response["eval_count"])
    
    return response["response"]
    
def get_response_openai_generate(request: GenerateRequest, fastapi_request: Request) -> str:
    response = config.get_or_create_openai_chat_client().responses.create(model=request.model, input=request.message, instructions=request.system_instructions)
    
    ip_address, _ = get_ip_address_for_rate_limit(fastapi_request)

    increment_resource_usage(ip_address, response.usage.total_tokens)

    return response.output[0].content[0].text


@app.post("/generate/postMessage")
@validate_chat_model_decorator
@rate_limit_decorator
def generate(request_model: GenerateRequest, fastapi_request: Request):
    log(f'generate/postMessage')
    try:
        if config.chat_client.mode == ChatClientMode.OPENAI:
            response_msg = get_response_openai_generate(request_model, fastapi_request)
        elif config.chat_client.mode == ChatClientMode.OLLAMA:
            response_msg = get_response_ollama_generate(request_model, fastapi_request)
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "error": f'unknown chat client mode: {config.chat_client.mode.value}'
                }
            )
        

        log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} generate/postMessage: data:{request_model.model_dump()} response:{response_msg}')
        llm_log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} Generate response: data:{request_model.model_dump()} response:{response_msg}')

                    
        # Store the response in our list
        d = {
            "message_id": request_model.message_id,
            "response": response_msg,
            "message": request_model.message,
            "model": request_model.model,
            "system_instructions": request_model.system_instructions,
            "options": request_model.options
        }
        generate_response_queue.append(d)

        while len(generate_response_queue)>=MAX_CHATS_NO_HISTORY:
            generate_response_queue.pop()

        log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} generate/postMessage: data:{request_model.model_dump()} response:{response_msg}')
        
        return JSONResponse( 
            status_code=200,
            content={"message_id": request_model.message_id, "response": response_msg}
        )
    
    except Exception as e:
        log(f'exception in /api/generate: {e}')
        return JSONResponse(
            status_code=500,
            content=f"Internal server error: {str(e)}"
        )