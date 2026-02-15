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

from code.audio_utils import stop_aitalkmaster_stream, stop_translation_stream
from code.shared import config, log
from code.config import IcecastClientConfig
from code.aitalkmaster_views import reset_aitalkmaster

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
        
        log(f"Mounts: {mounts}")
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
    """Get the number of listeners for a given join_key (aitalkmaster stream)"""
    if config.icecast_client:
        mount_path = f"/aitalkmaster/{join_key}"
        return get_listeners(config.icecast_client, mount_path)
    return 0

def get_translation_listeners(session_key: str) -> int:
    """Get the number of listeners for a given session_key (translation stream)"""
    if config.icecast_client:
        mount_path = f"/translation/{session_key}"
        return get_listeners(config.icecast_client, mount_path)
    return 0

def icecast_list_mounts() -> list[str]:
    """List all mounts in icecast"""
    if config.icecast_client:
        return get_mounts(config.icecast_client)
    return []
    

def delete_active_icecast_directory(join_key: str):
    """Delete the active aitalkmaster icecast directory"""
    
    active_dir = Path(f'./generated-audio/aitalkmaster/active/{join_key}')
    if active_dir.exists():
        shutil.rmtree(active_dir)
        log(f"Deleted active aitalkmaster icecast directory: {active_dir}")
        return True
    else:
        log(f"Active aitalkmaster icecast directory not found: {active_dir}")
    return False

def delete_translation_directory(session_key: str):
    """Delete the translation directory"""
    
    translation_dir = Path(f'./generated-audio/translation/active/{session_key}')
    if translation_dir.exists():
        shutil.rmtree(translation_dir)
        log(f"Deleted translation directory: {translation_dir}")
        return True
    else:
        log(f"Translation directory not found: {translation_dir}")
    return False

def get_active_directories() -> list[tuple[str, str]]:
    """Get the detached active directories from both aitalkmaster and translation folders
    Returns list of tuples: (directory_name, directory_type) where type is 'aitalkmaster' or 'translation'
    """
    directories = []
    
    # Get aitalkmaster directories
    aitalkmaster_base = Path('./generated-audio/aitalkmaster/active')
    if aitalkmaster_base.exists():
        for directory in aitalkmaster_base.glob('*'):
            if directory.is_dir():
                directories.append((directory.name, 'aitalkmaster'))
    
    # Get translation directories
    translation_base = Path('./generated-audio/translation/active')
    if translation_base.exists():
        for directory in translation_base.glob('*'):
            if directory.is_dir():
                directories.append((directory.name, 'translation'))
    
    return directories

def background_aitalkmaster_monitor():
    """Background thread that regularly checks if ait instances and translation sessions are still active"""
   
    from code.aitalkmaster_views import active_aitalkmaster_instances
    from code.translation_views import active_translation_sessions

    
    while True:
        try:
            
            log("Background aitalkmaster monitor: Checking active ait instances and translation sessions...")
            
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
                
                mount_path = f"/aitalkmaster/{join_key}"

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

            # Check each active translation session
            translation_sessions_to_remove = []
            for session_key, translation_session in active_translation_sessions.items():
                log(f"Checking translation session: {session_key}, created: {translation_session.created_at}, last_listened: {translation_session.last_listened_at}")
                
                mount_path = f"/translation/{session_key}"

                if mount_path not in mounts:
                    log(f"Translation mount {mount_path} not found in icecast")
                    stats = 0
                else:
                    # use stats function to get number of listeners
                    stats = get_listeners(config.icecast_client, mount_path)

                if stats > 0:
                    translation_session.last_listened_at = time.time()
                else:
                    if translation_session.last_listened_at + 30 * 24 * 60 * 60 < time.time():
                        # remove the session after 30 days of inactivity
                        translation_sessions_to_remove.append(session_key)

            # Clean up orphaned aitalkmaster mounts
            for mount in mounts:
                if mount.startswith("/aitalkmaster/"):
                    join_key = mount.replace("/aitalkmaster/", "")
                    if join_key not in active_aitalkmaster_instances.keys():
                        stop_aitalkmaster_stream(join_key)
                        log(f"Removed inactive aitalkmaster mount: {join_key}")
            
            # Clean up orphaned translation mounts
            for mount in mounts:
                if mount.startswith("/translation/"):
                    session_key = mount.replace("/translation/", "")
                    if session_key not in active_translation_sessions.keys():
                        stop_translation_stream(session_key)
                        log(f"Removed inactive translation mount: {session_key}")
            
            # Remove inactive ait instances
            for join_key in ait_instances_to_remove:
                if join_key in active_aitalkmaster_instances:
                    stop_aitalkmaster_stream(join_key)
                    reset_aitalkmaster(join_key)
                    del active_aitalkmaster_instances[join_key]

                    delete_active_icecast_directory(join_key)
                    log(f"Removed inactive ait instance: {join_key}")

            # Remove inactive translation sessions
            for session_key in translation_sessions_to_remove:
                if session_key in active_translation_sessions:
                    stop_translation_stream(session_key)
                    del active_translation_sessions[session_key]
                    delete_translation_directory(session_key)
                    log(f"Removed inactive translation session: {session_key}")

            active_directories = get_active_directories()
            log(f"Active directories: {active_directories}")

            # Clean up detached directories (not in either active list)
            for directory_name, directory_type in active_directories:
                if directory_type == 'aitalkmaster':
                    if directory_name not in active_aitalkmaster_instances.keys():
                        delete_active_icecast_directory(directory_name)
                        log(f"Deleted detached aitalkmaster directory: {directory_name}")
                elif directory_type == 'translation':
                    if directory_name not in active_translation_sessions.keys():
                        delete_translation_directory(directory_name)
                        log(f"Deleted detached translation directory: {directory_name}")

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
