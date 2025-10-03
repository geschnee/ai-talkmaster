from fastapi.responses import JSONResponse
from datetime import datetime
import uuid

from typing import Optional

from pydantic import BaseModel, Field

from code.shared import app, config
from code.validation_utils import validate_chat_model
from code.aitalkmaster_utils import log


response_queue = []
MAX_CHATS_HISTORY = 1000
MAX_CHATS_NO_HISTORY = 1000

history_queue = []


def getKey(username, prompt, model, optionstring):
    key = f'{username}:{prompt}:{model}:{optionstring}'
    return key

class HistoryElement:

    conversation_key: str
    username: str
    model: str
    dialog: list
    system: str

    options: dict

    # Constructor (initialization method)
    def __init__(self, conversation_key, username, model, options, system):
        # Instance attributes
        self.conversation_key = conversation_key
        self.username = username
        self.model = model
        self.dialog = []
        self.options = options
        self.system = system
        
    # Instance method
    def addPrompt(self, prompt, message_id):
        d = {
            "role": "user",
            "content": prompt,
            "message_id": message_id
        }
        self.dialog.append(d)

    def addResponse(self, response):
        d = {
            "role": "assistant",
            "content": response    
        }
        self.dialog.append(d)
        
    def getDialog(self):
        dialog = []
        
        for ele in self.dialog:
            dialog.append({
                "role": ele["role"],
                "content": ele["content"]
            })
        return dialog
    
    def findResponsesSince(self, message_id):
        dialog = self.dialog

        concatenated_responses=""

        reached=False
        for ele in dialog:
            if ele["role"]=="user":
                if ele["message_id"] == message_id:
                    reached=True
            elif ele["role"]=="assistant" and reached:
                if concatenated_responses=="":
                    concatenated_responses=ele["content"]
                else:
                    concatenated_responses=concatenated_responses + "\n\n" + ele["content"]

        return concatenated_responses, concatenated_responses!=""

    def __str__(self):
        return str({
            "model": self.model,
            "messages": self.getDialog(),
            "options": self.options,
            "stream": False
        })


class ConversationStartRequest(BaseModel):
    username: str
    model: str
    simulatorHostname: str
    regionName: str
    system: Optional[str] = ""
    options: Optional[dict] = {}

@app.post("/api/conversation/start")
async def startConversation(request: ConversationStartRequest):
    try:
        log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} startConversation: {request.username}, {request.model}, {request.simulatorHostname}, {request.regionName}, {request.options}')

        while len(history_queue)>=MAX_CHATS_HISTORY:
            history_queue.pop()

        conversation_key = str(uuid.uuid4())

        he = HistoryElement(conversation_key, request.username, request.model, request.options, request.system)

        history_queue.append(he)

        return JSONResponse(
            status_code=200,
            content={"conversation_key": conversation_key}
        )

    except Exception as e:
        log(f'Exception in startConversation {e}')
        return JSONResponse(
            status_code=500,
            content=f"Internal server error: {e}"
        )
    

def getHistoryElement(conversation_key):
    for historyElement in history_queue:
        if historyElement.conversation_key==conversation_key:
            return historyElement
    
    return None

class ConversationGetMessageResponseRequest(BaseModel):
    conversation_key: str
    message_id: str

@app.post("/api/conversation/getMessageResponse")
async def conversationGetMessage(request: ConversationGetMessageResponseRequest):
    try:
        
        conversation_key = request.conversation_key
        message_id = request.message_id
        
        historyElement = getHistoryElement(conversation_key=conversation_key)
        if historyElement == None:
            return JSONResponse(
                status_code=401,
                content={"message": f"no conversation found with key: {conversation_key}"}
            )

        concatenated_responses, responsesFound = historyElement.findResponsesSince(message_id)

        if not responsesFound:
            return JSONResponse( 
                status_code=202,
                content={"message": "Waiting for message response", "conversation_key": conversation_key})

        return JSONResponse(
            status_code=200,
            content={"response": concatenated_responses, "message_id": message_id, "conversation_key": conversation_key}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=f"Internal server error getMessage: {e}"
        )

class ConversationSendMessageRequest(BaseModel):
    conversation_key: str
    prompt: str
    message_id: str

def get_response_ollama_conversation(he: HistoryElement) -> str:
        
    full_dialog = []
    full_dialog.append({
        "role": "system",
        "content": he.system  
    })
    for d in he.getDialog():
        full_dialog.append(d)

    response = config.get_or_create_ollama_chat_client().chat(model=he.model, messages = full_dialog, options=he.options)
    
    return response["message"]["content"]

class ChatResponse(BaseModel):
    text_response: str = Field(description="character response")

def get_response_openai_conversation(he: HistoryElement) -> str:

    response = config.get_or_create_openai_chat_client().responses.parse(
        model=he.model,
        input=he.getDialog(),
        instructions=he.system,
        text_format=ChatResponse,
        store=False
    )

    return response.output_parsed.text_response # type: ignore

@app.post("/api/conversation/sendMessage")
async def conversationSendMessage(request: ConversationSendMessageRequest):
    try:
        data_json = request.model_dump()
        
        
        conversation_key = request.conversation_key
        prompt = request.prompt
        message_id = request.message_id

        historyElement = getHistoryElement(conversation_key=conversation_key)
        if historyElement == None:
            return JSONResponse(
                status_code=401,
                content={"message": f"no conversation found with key: {conversation_key}"}
            )


        historyElement.addPrompt(prompt, message_id)
        

        if config.chat_client.mode == "openai":
            response_msg = get_response_openai_conversation(historyElement)
        elif config.chat_client.mode == "ollama":
            log(f'before get_response_ollama')
            response_msg = get_response_ollama_conversation(historyElement)
            log(f'obtained response_msg from ollama: {response_msg}')
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "error": f'unknown chat client mode: {config.chat_client.mode}'
                }
            )
 
        # reduce size of response:
        response_json = {}
        response_json["conversation_key"]= conversation_key
        response_json["response"] = response_msg

        historyElement.addResponse(response_msg)

        log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} memorySendMessage: username: {historyElement.username} data:{data_json} historyElement:{historyElement}')
        
        return JSONResponse( 
            status_code=202,
            content={"message": "request was processed, use conversation/getMessageResponse to retrieve it"}
        )

    except Exception as e:
        log(f"Exception {e}")
        return JSONResponse(
            status_code=500,
            content=f"Internal server error in sendMessage: {e}"
        )

class GenerateGetResponseRequest(BaseModel):
    username: str
    prompt: str
    model: str
    options: Optional[dict] = {}

@app.post("/api/getResponse")
async def getResponse(request: GenerateGetResponseRequest):
    try:
        
        data = request.model_dump()
        
        username = request.username
        prompt = request.prompt
        model = request.model
        options = request.options

        key = getKey(username, prompt, model, str(options))

        while len(response_queue)>=MAX_CHATS_NO_HISTORY:
            response_queue.pop()

        for response in response_queue:
            if response["key"]==key:
                return response["response"]
            
        return JSONResponse(
            status_code=202,
            content={"message": f"requested response for {key} not in list"}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=f"Internal server error: {e}"
        )

class GenerateRequest(BaseModel):
    join_key: str
    username: str # name of the SL user that said the message (can also be an actor)
    prompt: str
    model: str
    system_instructions: str
    charactername: str
    options: Optional[dict] = {}

def get_response_ollama_generate(request: GenerateRequest) -> str:
    response = config.get_or_create_ollama_chat_client().generate(model=request.model, prompt=request.prompt, options=request.options)
    
    return response["message"]["content"]
    
def get_response_openai_generate(request: GenerateRequest) -> str:
    response = config.get_or_create_openai_chat_client().responses.create(model=request.model, input=request.prompt)
    
    return response.output[0].content[0].text

# Only allow /api/generate POST, with token
@app.post("/api/generate")
async def generate(request: GenerateRequest):
    try:
        username = request.join_key
        prompt = request.prompt
        model = request.model
        options = request.options

        # Validate chat model
        is_valid_model, model_error, available_models = validate_chat_model(request.model)
        if not is_valid_model:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"Invalid chat model: {model_error}",
                    "available_models": available_models
                }
            )

        if config.chat_client.mode == "openai":
            response_msg = get_response_openai_generate(request)
        elif config.chat_client.mode == "ollama":
            log(f'before get_response_ollama')
            response_msg = get_response_ollama_generate(request)
            log(f'obtained response_msg from ollama: {response_msg}')
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "error": f'unknown chat client mode: {config.chat_client.mode}'
                }
            )

        
        response_json = {}
        response_json["response"]= response_msg
        response_json["username"] = username
        response_json["prompt"]=prompt
        response_json["model"]=model
                    
        # Store the response in our list

        d = {
            "key": getKey(username, prompt, model, str(options)),
            "response": response_json
        }
        response_queue.append(d)

        log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} noMemorySendMessage: data:{request.model_dump()} response:{response_msg}')
        
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