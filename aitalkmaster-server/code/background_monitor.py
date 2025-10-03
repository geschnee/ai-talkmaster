"""
Background monitoring thread for checking active theater plays
"""

import threading
import time
import xml.etree.ElementTree as ET
import requests


from code.aitalkmaster_utils import stop_liquidsoap
from code.shared import config, log
from code.config import IcecastClientConfig
from code.aitalkmaster_views import stop_aitstream

def get_mounts(IcecastClientConfig: IcecastClientConfig) -> list[str]:
    """Get all mount points from Icecast XML response"""
    url = f"http://{IcecastClientConfig.host}:{IcecastClientConfig.port}/admin/listmounts"
    
    try:
        response = requests.get(url, auth=(IcecastClientConfig.admin_user, IcecastClientConfig.admin_password))
        
        root = ET.fromstring(response.text)
        
        if root is None:
            return []
        
        # Extract mount names from <source mount="/stream/Godot"> elements
        mounts = []
        for source in root.findall('source'):
            mount_attr = source.get('mount')
            if mount_attr:
                mounts.append(mount_attr)
        return mounts
        
    except Exception as e:
        log(f"Error getting mounts: {e}")
        return []

def get_listeners(IcecastClientConfig: IcecastClientConfig, mount_path: str) -> int:
    # /admin/listmounts
    url = f"http://{IcecastClientConfig.host}:{IcecastClientConfig.port}/admin/stats"
    
    try:
        response = requests.get(url, auth=(IcecastClientConfig.admin_user, IcecastClientConfig.admin_password))
        
        root = ET.fromstring(response.text)
        
        for source in root.findall('source'):
            mount_attr = source.get('mount')
            if mount_attr == mount_path:
                listeners_elem = source.find('listeners')
                if listeners_elem is not None:
                    listeners = int(listeners_elem.text or 0)
                    return listeners
        
        return 0
        
    except Exception as e:
        log(f"Error getting listeners for {mount_path}: {e}")
        return 0

def get_icecast_listeners(join_key: str) -> int:
    """Get the number of listeners for a given join_key"""
    if config.icecast_client:
        return get_listeners(config.icecast_client, join_key)
    return 0

def icecast_list_mounts() -> list[str]:
    """List all mounts in icecast"""
    if config.icecast_client:
        return get_mounts(config.icecast_client)
    return []

def background_play_monitor():
    """Background thread that regularly checks if plays are still active"""
   
    if config.icecast_client == None:
        log("No icecast client config found, cancel background play monitor")
        return
    
    while True:
        try:
            # Import here to avoid circular imports
            from code.aitalkmaster_views import active_theater_plays
            
            log("Background play monitor: Checking active plays...")
            
            # Get the keep-alive list from config
            keep_alive_list = config.theater.join_key_keep_alive_list if config.theater else []
            

            mounts = icecast_list_mounts()

            # Check each active play
            plays_to_remove = []
            for join_key, play in active_theater_plays.items():
                if join_key in keep_alive_list:
                    # this play is kept alive, so we don't need to check if it's still active
                    continue

                log(f"Checking play: {join_key}, created: {play.created_at}, last_listened: {play.last_listened_at}")
                
                mount_path = f"/stream/{join_key}"

                if mount_path not in mounts:
                    log(f"Mount {mount_path} not found in icecast")
                    stats = 0
                else:
                    # use stats function to get number of listeners
                    stats = get_listeners(config.icecast_client, mount_path)


                if stats > 0:
                    play.last_listened_at = time.time()
                else:
                    if play.last_listened_at + 30 * 24 * 60 * 60 < time.time():
                        # remove the play after 30 days of inactivity
                        plays_to_remove.append(join_key)
                        log(f"Removed inactive play: {join_key}")

            
            # Remove inactive plays
            for join_key in plays_to_remove:
                if join_key in active_theater_plays:
                    stop_liquidsoap(join_key)
                    stop_aitstream(join_key)
                    del active_theater_plays[join_key]
                    log(f"Removed inactive play: {join_key}")

            
            # Sleep for 30 seconds before next check
            time.sleep(30)
            
        except Exception as e:
            log(f"Error in background play monitor: {e}")
            time.sleep(30)  # Continue running even if there's an error

def start_background_monitor():
    """Start the background monitoring thread"""
    background_thread = threading.Thread(target=background_play_monitor, daemon=True)
    background_thread.start()
    log("Background play monitor thread started")
    return background_thread
