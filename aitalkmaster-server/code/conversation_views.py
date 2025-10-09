from fastapi.responses import JSONResponse
from datetime import datetime
import uuid

from typing import Optional
from dataclasses import dataclass

from code.shared import app, config
from code.validation_decorators import validate_chat_model_decorator
from code.aitalkmaster_utils import log
from code.request_models import ConversationStartRequest, ConversationGetMessageResponseRequest, ConversationSendMessageRequest
from code.openai_response import CharacterResponse
from code.config import ChatClientMode

history_queue = []
MAX_CHATS_HISTORY = 1000

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

class HistoryElement:
    """Represents a conversation history with messages and metadata"""
    
    def __init__(self, conversation_key: str, username: str, model: str, options: dict, system: str):
        self.conversation_key = conversation_key
        self.username = username
        self.model = model
        self.user_messages: list[ConversationMessage] = []
        self.assistant_responses: list[ConversationResponse] = []
        self.options = options
        self.system = system
        
    def addPrompt(self, prompt: str, message_id: str):
        """Add a user message to the conversation history"""
        user_message = ConversationMessage(
            content=prompt,
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

    
def getHistoryElement(conversation_key):
    for historyElement in history_queue:
        if historyElement.conversation_key==conversation_key:
            return historyElement
    return None


@app.post("/conversation/start")
@validate_chat_model_decorator
async def startConversation(request: ConversationStartRequest):
    try:
        log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} startConversation: {request.username}, {request.model}, {request.simulatorHostname}, {request.regionName}, {request.options}')

        while len(history_queue)>=MAX_CHATS_HISTORY:
            history_queue.pop()

        conversation_key = str(uuid.uuid4())

        history_queue.append(HistoryElement(conversation_key, request.username, request.model, request.options, request.system_instructions))

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
async def conversationGetMessage(request: ConversationGetMessageResponseRequest):
    try:
        historyElement = getHistoryElement(conversation_key=request.conversation_key)
        if historyElement == None:
            return JSONResponse(
                status_code=400,
                content={"message": f"no conversation found with key: {request.conversation_key}"}
            )

        response = historyElement.findResponseByMessageId(request.message_id)

        if response is None:
            return JSONResponse( 
                status_code=425,
                content={"message": "Waiting for message response", "conversation_key": request.conversation_key})

        return JSONResponse(
            status_code=200,
            content={"response": response.content, "message_id": request.message_id, "conversation_key": request.conversation_key}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=f"Internal server error getMessage: {e}"
        )

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

def get_response_openai_conversation(he: HistoryElement) -> str:
    response = config.get_or_create_openai_chat_client().responses.parse(
        model=he.model,
        input=he.getDialog(),
        instructions=he.system,
        text_format=CharacterResponse,
        store=False
    )

    return response.output_parsed.text_response # type: ignore

@app.post("/conversation/sendMessage")
async def conversationSendMessage(request: ConversationSendMessageRequest):
    try:
        historyElement = getHistoryElement(conversation_key=request.conversation_key)
        if historyElement == None:
            return JSONResponse(
                status_code=400,
                content={"message": f"no conversation found with key: {request.conversation_key}"}
            )


        historyElement.addPrompt(request.prompt, request.message_id)
        

        if config.chat_client.mode == ChatClientMode.OPENAI:
            response_msg = get_response_openai_conversation(historyElement)
        elif config.chat_client.mode == ChatClientMode.OLLAMA:
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

        historyElement.addResponse(response_msg, request.message_id)

        log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} memorySendMessage: username: {historyElement.username} data:{request.model_dump()} historyElement:{historyElement}')
        
        return JSONResponse( 
            status_code=200,
            content={"response": response_msg, "message_id": request.message_id, "conversation_key": request.conversation_key}
        )

    except Exception as e:
        log(f"Exception {e}")
        return JSONResponse(
            status_code=500,
            content=f"Internal server error in sendMessage: {e}"
        )
