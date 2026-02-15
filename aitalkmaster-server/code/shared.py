from fastapi import FastAPI
from contextlib import asynccontextmanager
import time
from datetime import datetime

from code.config import get_config

config = get_config()

def log(message):
    with open(config.server.log_file, "a") as file:
        file.write(message + "\n")
    print(message)

def llm_log(message):
    with open(config.server.llm_log_file, "a") as file:
        file.write(message + "\n")
    print(message)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan event handler"""
    # Startup
    log("FastAPI startup event triggered - initializing server...")
    # Add any startup initialization here if needed
    log("FastAPI startup completed successfully")
    
    yield
    
    # Shutdown
    log("FastAPI shutdown event triggered - performing cleanup...")
    llm_log("FastAPI shutdown event triggered - performing cleanup...")
    
    try:
        # Import here to avoid circular imports
        from code.audio_utils import stop_aitalkmaster_stream, stop_translation_stream
        from code.aitalkmaster_views import active_aitalkmaster_instances, reset_aitalkmaster
        from code.icecast_monitor import delete_active_icecast_directory
        
        # Stop all active liquidsoap streams
        for join_key in list(active_aitalkmaster_instances.keys()):
            log(f"Stopping stream for join_key: {join_key}")
            if config.liquidsoap_client is not None:
                stop_aitalkmaster_stream(join_key)
            reset_aitalkmaster(join_key)
            delete_active_icecast_directory(join_key)
        
        # Stop all active translation streams
        from code.translation_views import active_translation_sessions
        for session_key in list(active_translation_sessions.keys()):
            log(f"Stopping translation stream for session_key: {session_key}")
            if config.liquidsoap_client is not None:
                stop_translation_stream(session_key)

        from code.conversation_views import conversation_queue
        for conversation in conversation_queue:
            llm_log(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} Conversation: Server shutdown - logging active conversation: {conversation}')

        
        log("FastAPI shutdown cleanup completed successfully")
        
    except Exception as e:
        log(f"Error during FastAPI shutdown: {e}")

app = FastAPI(lifespan=lifespan)