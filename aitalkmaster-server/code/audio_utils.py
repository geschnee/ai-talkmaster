"""Audio streaming utilities for liquidsoap integration"""
import requests
from code.shared import config, log

def send_http_command(endpoint: str, data: str) -> bool:
    """Send an HTTP POST request to the liquidsoap server"""
    if config.liquidsoap_client == None:
        log(f"[-] No liquidsoap client config found, canceling HTTP request to '{endpoint}'")
        return False

    try:
        url = f"http://{config.liquidsoap_client.host}:{config.liquidsoap_client.http_port}{endpoint}"
        response = requests.post(
            url,
            data=data,
            timeout=5,
            headers={'Content-Type': 'text/plain'}
        )
        
        if response.status_code == 200:
            log(f"[*] HTTP request to '{endpoint}' successful, response: {response.text.strip()}")
            return True
        else:
            log(f"[-] HTTP request to '{endpoint}' failed with status {response.status_code}: {response.text.strip()}")
            return False
            
    except requests.exceptions.Timeout:
        log(f"[-] HTTP request to '{endpoint}' timed out")
        return False
    except requests.exceptions.ConnectionError:
        log(f"[-] Cannot connect to liquidsoap HTTP server at {config.liquidsoap_client.host}:{config.liquidsoap_client.http_port}")
        return False
    except Exception as e:
        log(f"[-] Error sending HTTP request to '{endpoint}': {e}")
        return False

def start_aitalkmaster_stream(stream_name: str) -> bool:
    """Start a liquidsoap stream via HTTP request"""
    
    log(f"[+] Starting liquidsoap stream for '{stream_name}'")
    data = f"{stream_name}"
    success = send_http_command("/start_aitalkmaster_stream", data)
    
    return success

def queue_aitalkmaster_audio(stream_name: str, filename: str) -> bool:
    """Queue an audio file for a specific liquidsoap stream via HTTP request"""
    log(f"[+] Queuing audio file '{filename}' for '{stream_name}'")
    data = f"{stream_name}::{filename}"
    success = send_http_command("/queue_aitalkmaster_audio", data)
    return success

def stop_aitalkmaster_stream(stream_name: str) -> bool:
    """Stop a specific aitalkmaster liquidsoap stream via HTTP request"""
    
    log(f"[-] Stopping aitalkmaster liquidsoap stream for '{stream_name}'")
    data = f"{stream_name}"
    success = send_http_command("/stop_aitalkmaster_stream", data)
    
    return success

# Translation-specific audio streaming functions (use different mount points)
def start_translation_stream(session_key: str) -> bool:
    """Start a translation liquidsoap stream via HTTP request (uses separate mount point)"""
    
    log(f"[+] Starting translation liquidsoap stream for '{session_key}'")
    data = f"translation::{session_key}"
    success = send_http_command("/start_translation_stream", data)
    
    return success

def queue_translation_audio(session_key: str, filename: str) -> bool:
    """Queue an audio file for a translation liquidsoap stream via HTTP request"""
    log(f"[+] Queuing translation audio file '{filename}' for '{session_key}'")
    data = f"translation::{session_key}::{filename}"
    success = send_http_command("/queue_translation_audio", data)
    return success

def stop_translation_stream(session_key: str) -> bool:
    """Stop a translation liquidsoap stream via HTTP request"""
    
    log(f"[-] Stopping translation liquidsoap stream for '{session_key}'")
    data = f"translation::{session_key}"
    success = send_http_command("/stop_translation_stream", data)
    
    return success

