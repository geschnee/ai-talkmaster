
import random
from fastapi import Request
import time
from fastapi.responses import StreamingResponse
from pathlib import Path


from code.aitalkmaster_utils import AitalkmasterInstance, time_str, get_audio_duration
from code.shared import app, log

from code.aitalkmaster_views import active_aitalkmaster_instances

# Track active connections by IP address
stream_active_connections = {}
stream_connection_counter = 0

CHUNK_SIZE = 1024

def generate_audio_stream(join_key: str, request: Request):
    """Generator function to stream audio files from the specific AitalkmasterInstance"""
    global stream_connection_counter, stream_active_connections

    stream_connection_counter += 1 
    connectionname = stream_connection_counter

    # Get client IP address
    client_ip = request.client.host if request.client else "unknown"
    
    # Check if there's already a connection from this IP
    existing_played_files = set()
    if client_ip in stream_active_connections:
        existing_connection = stream_active_connections[client_ip]
        log(f'{connectionname} {time_str()} Killing existing connection from IP {client_ip} (connection: {existing_connection["connectionname"]})')
        # Preserve the played audio files from the existing connection
        existing_played_files = existing_connection.get("played_audio_files", set())
        # We can't kill the existing connection, but we can mark it for cleanup
        # The existing connection will be cleaned up when it tries to yield next
    
    
    # Store this connection info with played audio files
    stream_active_connections[client_ip] = {
        "connectionname": connectionname,
        "join_key": join_key,
        "start_time": time.time(),
        "played_audio_files": existing_played_files,  # Preserve played files from previous connection
    }
    
    # Get the played audio files for this IP
    played_audio_files = stream_active_connections[client_ip]["played_audio_files"]

    log(f'{connectionname} {time_str()} Streaming audio for join_key: {join_key}, request URL: {request.url}, headers: {dict(request.headers)}, client: {client_ip}')

   
    waiting_audio_files = list(Path("fallback-audio").glob("*.mp3"))


    try:
        next_start = time.time()
        playback_range = 60 # play the audios of messages that were created in the last X seconds

        while True:  # Loop forever for continuous streaming

            if time.time() < next_start:
                time.sleep(1)
                continue

            # Check if this connection should be terminated (newer connection from same IP exists)
            if client_ip in stream_active_connections:
                current_connection = stream_active_connections[client_ip]
                if current_connection["connectionname"] != connectionname:
                    log(f'{connectionname} {time_str()} Terminating connection - newer connection exists for IP {client_ip}')
                    return
            

            if join_key in active_aitalkmaster_instances:
                
                ait_instance = active_aitalkmaster_instances[join_key]
                
                # Get audio files from assistant responses in this play
                audio_files_to_play = []
                for assistant_resp in ait_instance.assistant_responses:
                    if assistant_resp.filename and Path(assistant_resp.filename).exists() and assistant_resp.filename not in played_audio_files:
                        # Check if audio_created_at exists and is within playback range
                        if assistant_resp.audio_created_at and assistant_resp.audio_created_at + playback_range > time.time():
                            audio_files_to_play.append(assistant_resp.filename)
            else:
                log(f'{connectionname} {time_str()} The join_key {join_key} was not found (waiting for new content)')
                audio_files_to_play = []
            

            if audio_files_to_play==[]:

                # No new audio files available, play some background sounds
                audio_file = Path(random.choice(waiting_audio_files))
                if audio_file.exists():
                    try:
                        duration = get_audio_duration(audio_file)
                        next_start = time.time() + duration

                        with open(audio_file, "rb") as f:
                            chunk = f.read(CHUNK_SIZE)
                            while chunk:
                                try:
                                    yield chunk
                                    chunk = f.read(CHUNK_SIZE)
                                except (BrokenPipeError, ConnectionResetError):
                                    log(time_str() + " stream client disconnected crowd")
                                    return  # Client disconnected
                            
                        log(f'{connectionname} {time_str()} Played waiting audio {audio_file}')
                        
                    except Exception as e:
                        log(f"{connectionname} {time_str()} Error streaming audio file {audio_file}: {e}")
                else:
                    # No background audio file, sleep to prevent busy waiting
                    time.sleep(1)
                
            
            elif len(audio_files_to_play) > 0:

                for audio_file in audio_files_to_play:
                    log(f'{connectionname} {time_str()} will play audio file: {audio_file}')
                    try:

                        duration = get_audio_duration(audio_file)
                        next_start = time.time() + duration
                        with open(audio_file, "rb") as f:
                            chunk = f.read(CHUNK_SIZE)
                            while chunk:
                                try:
                                    yield chunk
                                    chunk = f.read(CHUNK_SIZE)
                                except (BrokenPipeError, ConnectionResetError):
                                    log(f'{connectionname} {time_str()} stream client disconnected')
                                    return  # Client disconnected
                    
                    except Exception as e:
                        log(f"Error streaming audio file {audio_file}: {e}")
                        continue  # Skip this file and continue with the next one
                
                    played_audio_files.add(audio_file)
                    stream_active_connections[client_ip]["played_audio_files"] = played_audio_files
    except BrokenPipeError:
        log(f'{connectionname} {time_str()} stream client disconnected broken pipe')
        return
    except ConnectionResetError:
        log(f'{connectionname} {time_str()} stream client disconnected connection reset')
        return
    except Exception as e:
        print(f"{connectionname} {time_str()} Error in audio stream: {e}")
        log(f"Error in audio stream: {e}")
        return


@app.get("/ait/stream-audio/{join_key}")
def stream_audio(join_key: str, request: Request):
    """
    Stream audio files from the specific AitalkmasterInstance, playing each assistant message audio once.
    This endpoint can be used, however the icecast mount provided by the liquidsoap and icecast services is preferred.
    """

    if join_key not in active_aitalkmaster_instances:
        # No active ait_instance with this join_key, wait a bit and try again
        print(f'The join_key {join_key} was not found in stream, create new ait_instance')
        ait_instance = AitalkmasterInstance(join_key=join_key)
        active_aitalkmaster_instances[join_key] = ait_instance
    
    return StreamingResponse(
        generate_audio_stream(join_key, request),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-cache",
            "Content-Disposition": "inline; filename=audio_stream.mp3"
        }
    )