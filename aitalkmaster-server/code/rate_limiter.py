

import time
from typing import Dict
from collections import defaultdict, deque
from code.shared import config, log
from fastapi import Request

# In-memory storage for rate limiting
# Structure: {ip_address: deque of (timestamp, weight) tuples}
rate_limit_storage: Dict[str, deque] = defaultdict(lambda: deque())

def clean_old_entries(ip_address: str, current_time: float, window_seconds: int):
    if ip_address not in rate_limit_storage:
        return
    
    # Remove entries older than the window
    while (rate_limit_storage[ip_address] and 
           current_time - rate_limit_storage[ip_address][0][0] > window_seconds):
        rate_limit_storage[ip_address].popleft()

def get_total_weight(ip_address: str, window_seconds: int) -> float:
    current_time = time.time()
    clean_old_entries(ip_address, current_time, window_seconds)
    
    total_weight = 0.0
    for timestamp, weight in rate_limit_storage[ip_address]:
        total_weight += weight
    
    return total_weight

def increment_resource_usage(ip_address: str, weight: float) -> None:
    
    current_time = time.time()
    rate_limit_storage[ip_address].append((current_time, weight))
    
    # Log the increment for debugging
    log(f"Rate limit: Incremented usage for IP {ip_address} with weight {weight} at {current_time}")
    
    # Clean up old entries to prevent memory bloat
    clean_old_entries(ip_address, current_time, 86400)  # Clean entries older than 24 hours

def rate_limit_exceeded(ip_address: str) -> bool:
    day_weight = get_total_weight(ip_address, 86400)
    if day_weight > config.server.usage.rate_limit_per_day:
        log(f"Rate limit: IP {ip_address} exceeded day limit ({day_weight}/{config.server.usage.rate_limit_per_day})")
        return True
    
    return False


def get_headers(request: Request) -> dict:
    # Extract headers from the request object
    headers = {}
    if hasattr(request, 'headers'):
        headers = dict(request.headers)
    elif hasattr(request, '__dict__'):
        # Try to find headers in request attributes
        for attr_name in ['headers', 'request_headers', 'http_headers']:
            if hasattr(request, attr_name):
                headers = dict(getattr(request, attr_name))
                break
    
    return headers

def get_ip_address_for_rate_limit(request: Request) -> tuple[str, str]:
    # Determine IP address to use for rate limiting
    if config.server.usage.rate_limit_xForwardedFor:
        headers = get_headers(request)
        if headers.get('x-forwarded-for') is not None:
            ip_address = headers.get('x-forwarded-for')
        else:
            return None, "No IP address found (x-forwarded-for header not found), inform the admin about this error"
    else:
        if request.client.host is not None:
            ip_address = request.client.host
        else:
            return None, "No IP address found, inform the admin about this error"
    
    return ip_address, None