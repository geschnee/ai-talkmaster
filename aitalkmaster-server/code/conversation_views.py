from fastapi.responses import JSONResponse
from datetime import datetime
import uuid

from typing import Optional
from dataclasses import dataclass

from code.shared import app, config, log
from code.validation_decorators import validate_chat_model_decorator, rate_limit_decorator
from code.request_models import ConversationStartRequest, ConversationGetMessageResponseRequest, ConversationPostMessageRequest
from code.openai_response import CharacterResponse
from code.config import ChatClientMode
from code.rate_limiter import get_ip_address_for_rate_limit, increment_resource_usage
from fastapi import Request

conversation_queue = []
MAX_ACTIVE_CONVERSATIONS = 1000

@dataclass
class ConversationMessage:
    """Represents a user message in a conversation"""
    content: str
    message_id: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ConversationResponse:
    """Represents an assistant response in a conversation"""
    content: str
    message_id: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class Conversation:
    """Represents a conversation history with messages and metadata"""
    
    def __init__(self, conversation_key: str, username: str, model: str, options: dict, system: str):
        self.conversation_key = conversation_key
        self.username = username
        self.model = model
        self.user_messages: list[ConversationMessage] = []
        self.assistant_responses: list[ConversationResponse] = []
        self.options = options
        self.system = system
        
    def addMessage(self, message: str, message_id: str):
        """Add a user message to the conversation history"""
        user_message = ConversationMessage(
            content=message,
            message_id=message_id
        )
        self.user_messages.append(user_message)

    def addResponse(self, response: str, message_id: str):
        """Add an assistant response to the conversation history"""
        assistant_response = ConversationResponse(
            content=response,
            message_id=message_id
        )
        self.assistant_responses.append(assistant_response)
        
    def getDialog(self):
        """Get dialog for chat model"""
    
        # Combine user messages and assistant responses in chronological order
        all_messages = []
        
        # Add user messages
        for message in self.user_messages:
            all_messages.append({
                "role": "user",
                "content": message.content,
                "timestamp": message.timestamp
            })
        
        # Add assistant responses
        for response in self.assistant_responses:
            all_messages.append({
                "role": "assistant",
                "content": response.content,
                "timestamp": response.timestamp
            })
        
        # Sort by timestamp to maintain chronological order
        all_messages.sort(key=lambda x: x["timestamp"])
        
        dialog = []
        for message in all_messages:
            dialog.append({
                "role": message["role"],
                "content": message["content"]
            })
        
        return dialog
    
    def getMessageById(self, message_id: str) -> Optional[ConversationMessage]:
        """Get a specific user message by its ID"""
        for message in self.user_messages:
            if message.message_id == message_id:
                return message
        return None
    
    def findResponseByMessageId(self, message_id: str) -> Optional[ConversationResponse]:
        """Find a specific assistant response by its message ID"""
        for response in self.assistant_responses:
            if response.message_id == message_id:
                return response
        return None

    def __str__(self):
        """String representation for logging"""
        return str({
            "model": self.model,
            "messages": self.getDialog(),
            "options": self.options,
            "stream": False
        })

    
def getConversation(conversation_key):
    for conversation in conversation_queue:
        if conversation.conversation_key==conversation_key:
            return conversation
    return None


@app.post("/conversation/start")
@validate_chat_model_decorator
@rate_limit_decorator
def startConversation(request_model: ConversationStartRequest, fastapi_request: Request):
    try:
        log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} startConversation: {request_model.username}, {request_model.model}, {request_model.options}')

        while len(conversation_queue)>=MAX_ACTIVE_CONVERSATIONS:
            conversation_queue.pop()

        conversation_key = str(uuid.uuid4())

        conversation_queue.append(Conversation(conversation_key, request_model.username, request_model.model, request_model.options, request_model.system_instructions))

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


@app.get("/conversation/getMessageResponse")
def conversationGetMessage(request_model: ConversationGetMessageResponseRequest):
    try:
        conversation = getConversation(conversation_key=request_model.conversation_key)
        if conversation == None:
            return JSONResponse(
                status_code=400,
                content={"message": f"no conversation found with key: {request_model.conversation_key}"}
            )

        response = conversation.findResponseByMessageId(request_model.message_id)

        if response is None:
            return JSONResponse( 
                status_code=425,
                content={"message": "Waiting for message response", "conversation_key": request_model.conversation_key})

        return JSONResponse(
            status_code=200,
            content={"response": response.content, "message_id": request_model.message_id, "conversation_key": request_model.conversation_key}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=f"Internal server error getMessage: {e}"
        )

def get_response_ollama_conversation(conversation: Conversation, fastapi_request: Request) -> str:
    full_dialog = []
    full_dialog.append({
        "role": "system",
        "content": conversation.system  
    })
    for d in conversation.getDialog():
        full_dialog.append(d)

    response = config.get_or_create_ollama_chat_client().chat(model=conversation.model, messages = full_dialog, options=conversation.options)

    ip_address, _ = get_ip_address_for_rate_limit(fastapi_request)
    increment_resource_usage(ip_address, response["eval_count"])


    return response["message"]["content"]

def get_response_openai_conversation(conversation: Conversation, fastapi_request: Request) -> str:
    response = config.get_or_create_openai_chat_client().responses.parse(
        model=conversation.model,
        input=conversation.getDialog(),
        instructions=conversation.system,
        text_format=CharacterResponse,
        store=False
    )

    ip_address, _ = get_ip_address_for_rate_limit(fastapi_request)
    increment_resource_usage(ip_address, response.usage.total_tokens)

    return response.output_parsed.text_response # type: ignore

@app.post("/conversation/postMessage")
@rate_limit_decorator
def conversationPostMessage(request_model: ConversationPostMessageRequest, fastapi_request: Request):
    try:
        conversation = getConversation(conversation_key=request_model.conversation_key)
        if conversation == None:
            return JSONResponse(
                status_code=400,
                content={"message": f"no conversation found with key: {request_model.conversation_key}"}
            )


        conversation.addMessage(request_model.message, request_model.message_id)
        

        if config.chat_client.mode == ChatClientMode.OPENAI:
            response_msg = get_response_openai_conversation(conversation, fastapi_request)
        elif config.chat_client.mode == ChatClientMode.OLLAMA:
            response_msg = get_response_ollama_conversation(conversation, fastapi_request)
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "error": f'unknown chat client mode: {config.chat_client.mode}'
                }
            )

        conversation.addResponse(response_msg, request_model.message_id)

        log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} conversation/postMessage: username: {conversation.username} data:{request_model.model_dump()} conversation:{conversation}')
        
        return JSONResponse( 
            status_code=200,
            content={"response": response_msg, "message_id": request_model.message_id, "conversation_key": request_model.conversation_key}
        )

    except Exception as e:
        log(f"Exception {e}")
        return JSONResponse(
            status_code=500,
            content=f"Internal server error in postMessage: {e}"
        )
