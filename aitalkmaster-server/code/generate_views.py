from fastapi.responses import JSONResponse
from datetime import datetime


from code.shared import app, config, log
from code.validation_decorators import validate_chat_model_decorator, rate_limit_decorator
from code.request_models import GenerateGetMessageResponseRequest, GenerateRequest
from code.config import ChatClientMode
from code.rate_limiter import get_ip_address_for_rate_limit, increment_resource_usage
from fastapi import Request


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

def get_response_ollama_generate(request: GenerateRequest, fastapi_request: Request) -> str:
    response = config.get_or_create_ollama_chat_client().generate(model=request.model, prompt=request.prompt, system=request.system_instructions, options=request.options)


    ip_address, _ = get_ip_address_for_rate_limit(fastapi_request)
    increment_resource_usage(ip_address, response["eval_count"])
    
    
    return response["response"]
    
def get_response_openai_generate(request: GenerateRequest, fastapi_request: Request) -> str:
    response = config.get_or_create_openai_chat_client().responses.create(model=request.model, input=request.prompt, instructions=request.system_instructions)
    

    ip_address, _ = get_ip_address_for_rate_limit(fastapi_request)

    log(f'response: {response}')
    log(f'response usage: {response.usage}')
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
        log(f'response generated')
        log(f'response: {response_msg}')

        log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} generate/postMessage: data:{request_model.model_dump()} response:{response_msg}')

        response_json = {
            "response": response_msg,
            "username": request_model.username,
            "prompt": request_model.prompt,
            "model": request_model.model
        }
                    
        # Store the response in our list
        d = {
            "key": getKey(request_model.username, request_model.model, request_model.prompt, request_model.system_instructions, str(request_model.options)),
            "response": response_json
        }
        log(f'key generated')
        response_queue.append(d)

        while len(response_queue)>=MAX_CHATS_NO_HISTORY:
            response_queue.pop()

        log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} generate/postMessage: data:{request_model.model_dump()} response:{response_msg}')
        
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

from fastapi import Request

@app.get("/generate/headersLog")
@rate_limit_decorator
def headersLog(request: Request):
    # Log request headers directly without decorator
    
    try:

        log(f'in function headersLog request IP: {request.client.host}')
        # Extract headers from the request object


        log(f'in function headersLog request: {request}')
        headers = {}
        if hasattr(request, 'headers'):
            headers = dict(request.headers)
        elif hasattr(request, '__dict__'):
            # Try to find headers in request attributes
            for attr_name in ['headers', 'request_headers', 'http_headers']:
                if hasattr(request, attr_name):
                    headers = dict(getattr(request, attr_name))
                    break
        
        # Log the headers using the same log function as other views
        log(f"in function headersLog Headers for headersLog endpoint: {headers}")
        
        # Log specific important headers if they exist
        important_headers = ['user-agent', 'authorization', 'content-type', 'x-forwarded-for', 'x-real-ip']
        for header_name in important_headers:
            if header_name in headers:
                # Mask sensitive headers
                if header_name in ['authorization']:
                    log(f"in function headersLog Header {header_name}: [REDACTED]")
                else:
                    log(f"in function headersLog Header {header_name}: {headers[header_name]}")
                    
    except Exception as e:
        log(f"Failed to log headers for headersLog: {str(e)}")

    return JSONResponse(
        status_code=200,
        content={
            "message": "headers logged"
        }
    )