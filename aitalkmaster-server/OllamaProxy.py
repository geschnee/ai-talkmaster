# Import shared components
from code.shared import app, config, log

import openai
import signal
import atexit

log("--------------------------------------------")
log("Server has been started")


log(f'Openai version: {openai.__version__}')


log(f'config: {config.get_config_summary()}')

# Import views after app is created
import code.aitalkmaster_views
import code.aitalkmaster_native_stream_views
import code.one_on_one_conversation_views
import code.email_views
import code.other_views

# Start background monitoring thread
from code.background_monitor import start_background_monitor
start_background_monitor()

def shutdown_handler():
    """Handle server shutdown gracefully"""
    log("Server shutdown initiated - stopping all active streams...")
    
    try:
        # Stop all active liquidsoap streams
        from code.aitalkmaster_utils import stop_liquidsoap
        from code.aitalkmaster_views import active_theater_plays, stop_aitstream
        
        for join_key in list(active_theater_plays.keys()):
            log(f"Stopping stream for join_key: {join_key}")
            stop_liquidsoap(join_key)
            stop_aitstream(join_key)
        
        log("All streams stopped successfully")
        
    except Exception as e:
        log(f"Error during shutdown: {e}")

# Register shutdown handlers
atexit.register(shutdown_handler)

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    log(f"Received signal {signum}, shutting down...")
    shutdown_handler()
    exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

import uvicorn
if __name__ == "__main__":
    uvicorn.run(app, host=config.server.host, port=config.server.port)