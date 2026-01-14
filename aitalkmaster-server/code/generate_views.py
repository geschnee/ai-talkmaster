from fastapi.responses import JSONResponse
from datetime import datetime
import traceback

from code.shared import app, config, log, llm_log
from code.validation_decorators import validate_chat_model_decorator, rate_limit_decorator
from code.request_models import GenerateRequest
from code.config import ChatClientMode
from code.rate_limiter import get_ip_address_for_rate_limit, increment_resource_usage
from fastapi import Request
from code.message_queue import queue_message_request, RequestType

generate_response_queue = []
MAX_CHATS_NO_HISTORY = 1000

@app.get("/generate/getMessageResponse")
def generateGetMessageResponse(message_id: str):
    try:
        for response in generate_response_queue:
            if response["message_id"]==message_id:
                return JSONResponse( 
                    status_code=200,
                    content={
                        "message_id": message_id,
                        "response": response["response"]
                    }
                )
            
        return JSONResponse(
            status_code=425,
            content={"message": f"requested response for {message_id} not in list"}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=f"Internal server error: {e}"
        )

def get_response_ollama_generate(request: GenerateRequest, ip_address: str) -> str:
    response = config.get_or_create_ollama_chat_client().generate(model=request.model, prompt=request.message, system=request.system_instructions, options=request.options)

    increment_resource_usage(ip_address, response["eval_count"])
    
    return response["response"]
    
def get_response_openai_generate(request: GenerateRequest, ip_address: str) -> str:
    response = config.get_or_create_openai_chat_client().responses.create(model=request.model, input=request.message, instructions=request.system_instructions)
    
    increment_resource_usage(ip_address, response.usage.total_tokens)

    return response.output[0].content[0].text

def process_generate_post_message(request_model: GenerateRequest, ip_address: str):
    """Process a generate postMessage request in the background"""
    try:
        if config.chat_client.mode == ChatClientMode.OPENAI:
            response_msg = get_response_openai_generate(request_model, ip_address)
        elif config.chat_client.mode == ChatClientMode.OLLAMA:
            response_msg = get_response_ollama_generate(request_model, ip_address)
        else:
            log(f'Error: unknown chat client mode: {config.chat_client.mode.value}')
            return
        
        log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} generate/postMessage (background): data:{request_model.model_dump()} response:{response_msg}')
        llm_log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} generate/postMessage (background): data:{request_model.model_dump()} response:{response_msg}')

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
        
    except Exception as e:
        log(f'exception in process_generate_post_message: {e}')
        log(f'stack: {traceback.print_exc()}')


@app.post("/generate/postMessage")
@validate_chat_model_decorator
@rate_limit_decorator
def generate(request_model: GenerateRequest, fastapi_request: Request):
    log(f'generate/postMessage (queued)')
    try:
        # Extract IP address for rate limiting in background processing
        ip_address, error = get_ip_address_for_rate_limit(fastapi_request)
        if error:
            return JSONResponse(
                status_code=500,
                content={
                    "error": error
                }
            )
        
        # Queue the request for background processing
        queue_message_request(RequestType.GENERATE, request_model, ip_address, process_generate_post_message)
        
        # Return 425 to indicate the request is being processed
        return JSONResponse(
            status_code=425,
            content={
                "message_id": request_model.message_id,
                "status": "processing",
                "info": "Request queued for background processing"
            }
        )
    
    except Exception as e:
        log(f'exception in /generate/postMessage: {e}')
        log(f'stack: {traceback.print_exc()}')
        return JSONResponse(
            status_code=500,
            content=f"Internal server error: {str(e)}"
        )