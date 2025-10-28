"""
The methods in this file are used to monitor the icecast server and check if the aitalkmaster instances are being listened to.
After 30 days of inactivity, the aitalkmaster stream is removed.
"""

import threading
import time
import xml.etree.ElementTree as ET
import requests
import shutil
from pathlib import Path

from code.aitalkmaster_utils import stop_liquidsoap
from code.shared import config, log
from code.config import IcecastClientConfig
from code.aitalkmaster_views import reset_aitalkmaster

def get_mounts(IcecastClientConfig: IcecastClientConfig) -> list[str]:
    """Get all mount points from Icecast XML response"""
    url = f"http://{IcecastClientConfig.host}:{IcecastClientConfig.port}/admin/listmounts"
    
    try:
        log(f"Getting mounts from {url}")
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
    

def delete_active_icecast_directory(join_key: str):
    """Delete the active icecast directory"""
    
    active_dir = Path(f'./generated-audio/active/{join_key}')
    if active_dir.exists():
        shutil.rmtree(active_dir)
        log(f"Deleted active icecast directory: {active_dir}")
        return True
    else:
        log(f"Active icecast directory not found: {active_dir}")
    return False

def get_active_directories() -> list[str]:
    """Get the detached active directories"""
    active_directories = Path('./generated-audio/active').glob('*')
    return [directory.name for directory in active_directories if directory.is_dir()]

def background_aitalkmaster_monitor():
    """Background thread that regularly checks if ait instances are still active"""
   
    from code.aitalkmaster_views import active_aitalkmaster_instances

    
    while True:
        try:
            
            log("Background aitalkmaster monitor: Checking active ait instances...")
            
            # Get the keep-alive list from config
            keep_alive_list = config.aitalkmaster.join_key_keep_alive_list if config.aitalkmaster else []
            

            mounts = icecast_list_mounts()

            # Check each active ait instance
            ait_instances_to_remove = []
            for join_key, ait_instance in active_aitalkmaster_instances.items():
                if join_key in keep_alive_list:
                    # this instance is kept alive, so we don't need to check if it's still active
                    continue

                log(f"Checking ait instance: {join_key}, created: {ait_instance.created_at}, last_listened: {ait_instance.last_listened_at}")
                
                mount_path = f"/stream/{join_key}"

                if mount_path not in mounts:
                    log(f"Mount {mount_path} not found in icecast")
                    stats = 0
                else:
                    # use stats function to get number of listeners
                    stats = get_listeners(config.icecast_client, mount_path)


                if stats > 0:
                    ait_instance.last_listened_at = time.time()
                else:
                    if ait_instance.last_listened_at + 30 * 24 * 60 * 60 < time.time():
                        # remove the instance after 30 days of inactivity
                        ait_instances_to_remove.append(join_key)

            for mount in mounts:
                join_key = mount.replace("/stream/", "")
                if join_key not in active_aitalkmaster_instances.keys():
                    stop_liquidsoap(join_key)
                    log(f"Removed inactive mount: {join_key}")
            
            # Remove inactive ait instances
            for join_key in ait_instances_to_remove:
                if join_key in active_aitalkmaster_instances:
                    stop_liquidsoap(join_key)
                    reset_aitalkmaster(join_key)
                    del active_aitalkmaster_instances[join_key]

                    delete_active_icecast_directory(join_key)
                    log(f"Removed inactive ait instance: {join_key}")


            active_directories = get_active_directories()
            log(f"Active directories: {active_directories}")

            for directory in active_directories:
                if directory not in active_aitalkmaster_instances.keys():
                    delete_active_icecast_directory(directory)
                    log(f"Deleted detached active icecast directory: {directory}")

            # Sleep for 30 seconds before next check
            time.sleep(30)
            
        except Exception as e:
            log(f"Error in background aitalkmaster monitor: {e}")
            time.sleep(30)  # Continue running even if there's an error

def start_background_monitor():
    """Start the background monitoring thread"""
    background_thread = threading.Thread(target=background_aitalkmaster_monitor, daemon=True)
    background_thread.start()
    log("Background aitalkmaster monitor thread started")
    return background_thread
