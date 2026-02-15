"""
Unified message queue system for processing all types of postMessage requests
"""
import queue
import threading
import traceback
from enum import Enum
from dataclasses import dataclass
from typing import Union, Callable, Any

from code.shared import log
from code.request_models import AitPostMessageRequest, ConversationPostMessageRequest, GenerateRequest, AitGenerateAudioRequest, TranslationRequest

class RequestType(Enum):
    """Type of request in the queue"""
    AIT = "ait"
    CONVERSATION = "conversation"
    GENERATE = "generate"
    TRANSLATION = "translation"

@dataclass
class QueuedMessageRequest:
    """Unified queued message request for background processing"""
    request_type: RequestType
    request_model: Union[AitPostMessageRequest, ConversationPostMessageRequest, GenerateRequest, TranslationRequest]
    ip_address: str
    processor: Callable[[Any, str], None]  # Function to process this request: (request_model, ip_address) -> None

@dataclass
class QueuedAudioGenerationRequest:
    """Queued audio generation request for background processing"""
    request_model: Union[AitGenerateAudioRequest]  # Supports ait audio generation only
    ip_address: str
    processor: Callable[[Any, str], None]  # Function to process this request: (request_model, ip_address) -> None

# Global queue for all message requests
message_queue = queue.Queue()

# Separate queue for audio generation requests (doesn't wait for other content)
audio_generation_queue = queue.Queue()

def queue_message_request(request_type: RequestType, request_model: Union[AitPostMessageRequest, ConversationPostMessageRequest, GenerateRequest, TranslationRequest], ip_address: str, processor: Callable):
    """Queue a message request for background processing"""
    queued_request = QueuedMessageRequest(
        request_type=request_type,
        request_model=request_model,
        ip_address=ip_address,
        processor=processor
    )
    message_queue.put(queued_request)

def background_message_worker():
    """Background worker thread that processes queued message requests"""
    worker_name = threading.current_thread().name
    while True:
        try:
            # Get a queued request (blocks until one is available)
            queued_request = message_queue.get()
            
            # Get message_id for logging (all request types have this field)
            message_id = getattr(queued_request.request_model, 'message_id', 'unknown')
            
            log(f'{worker_name}: Processing queued {queued_request.request_type.value} request for message_id: {message_id}')
            
            # Process the request using the provided processor function
            queued_request.processor(queued_request.request_model, queued_request.ip_address)
            
            log(f'{worker_name}: Completed processing {queued_request.request_type.value} message_id: {message_id}')
            
            # Mark the task as done
            message_queue.task_done()
            
        except Exception as e:
            log(f'Error in {worker_name}: {e}')
            log(f'stack: {traceback.print_exc()}')

def queue_audio_generation_request(request_model: Union[AitGenerateAudioRequest, TranslationRequest], ip_address: str, processor: Callable):
    """Queue an audio generation or translation request for background processing in a separate queue"""
    queued_request = QueuedAudioGenerationRequest(
        request_model=request_model,
        ip_address=ip_address,
        processor=processor
    )
    audio_generation_queue.put(queued_request)

def background_audio_generation_worker():
    """Background worker thread that processes queued audio generation and translation requests"""
    worker_name = threading.current_thread().name
    while True:
        try:
            # Get a queued request (blocks until one is available)
            queued_request = audio_generation_queue.get()
            
            # Get identifier for logging (join_key for audio generation, session_key for translation)
            identifier = getattr(queued_request.request_model, 'join_key', None) or getattr(queued_request.request_model, 'session_key', 'unknown')
            request_type = 'translation' if hasattr(queued_request.request_model, 'session_key') else 'audio generation'
            
            log(f'{worker_name}: Processing queued {request_type} request for {identifier}')
            
            # Process the request using the provided processor function
            queued_request.processor(queued_request.request_model, queued_request.ip_address)
            
            log(f'{worker_name}: Completed processing {request_type} request for {identifier}')
            
            # Mark the task as done
            audio_generation_queue.task_done()
            
        except Exception as e:
            log(f'Error in {worker_name}: {e}')
            log(f'stack: {traceback.print_exc()}')

def start_background_message_workers(num_workers: int = 4):
    """Start multiple background message worker threads
    
    Args:
        num_workers: Number of worker threads to start (default: 4)
    
    Returns:
        List of started worker threads
    """
    worker_threads = []
    for i in range(num_workers):
        worker_thread = threading.Thread(
            target=background_message_worker, 
            daemon=True,
            name=f"MessageWorker-{i+1}"
        )
        worker_thread.start()
        worker_threads.append(worker_thread)
    
    log(f"Started {num_workers} unified background message worker threads")
    return worker_threads

def start_background_audio_generation_workers(num_workers: int = 2):
    """Start multiple background audio generation worker threads
    
    Args:
        num_workers: Number of worker threads to start (default: 2)
    
    Returns:
        List of started worker threads
    """
    worker_threads = []
    for i in range(num_workers):
        worker_thread = threading.Thread(
            target=background_audio_generation_worker, 
            daemon=True,
            name=f"AudioGenerationWorker-{i+1}"
        )
        worker_thread.start()
        worker_threads.append(worker_thread)
    
    log(f"Started {num_workers} background audio generation worker threads")
    return worker_threads

