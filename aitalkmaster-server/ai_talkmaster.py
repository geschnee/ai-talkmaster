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
import code.conversation_views
import code.generate_views
import code.other_views

# Start background monitoring thread

if config.icecast_client is not None:
    from code.icecast_monitor import start_background_monitor
    start_background_monitor()
else:
    log("Icecast client is not configured, so background monitoring thread will not be started")

def shutdown_handler():
    """Handle server shutdown gracefully"""
    log("Server shutdown initiated - stopping all active streams...")
    
    try:
        # Stop all active liquidsoap streams
        from code.aitalkmaster_utils import stop_liquidsoap
        from code.aitalkmaster_views import active_aitalkmaster_instances, reset_aitalkmaster
        
        for join_key in list(active_aitalkmaster_instances.keys()):
            log(f"Stopping stream for join_key: {join_key}")
            if config.liquidsoap_client is not None:
                stop_liquidsoap(join_key)
            reset_aitalkmaster(join_key)
        
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