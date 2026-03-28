import psutil
import logging

logger = logging.getLogger(__name__)

CPU_THRESHOLD = 90.0
RAM_THRESHOLD = 90.0
ALLOW_OVERLOAD = True

def is_system_overloaded() -> bool:
    """
    Checks if the system resources are critically utilized (both CPU and RAM pegging limits).
    Returns True if BOTH CPU and RAM exceed the threshold, and ALLOW_OVERLOAD is False.
    """
    if ALLOW_OVERLOAD:
        return False

    cpu_usage = psutil.cpu_percent(interval=0.1)
    ram_usage = psutil.virtual_memory().percent
    
    logger.info(f"System Load Check - CPU: {cpu_usage:.1f}%, RAM: {ram_usage:.1f}%")
    
    if cpu_usage > CPU_THRESHOLD and ram_usage > RAM_THRESHOLD:
        logger.warning(f"System critically overloaded! Recommending hard rejection.")
        return True
    return False

def is_system_busy() -> bool:
    """
    Returns True if either CPU or RAM is above the threshold (so we can issue a soft warning).
    """
    cpu_usage = psutil.cpu_percent(interval=0.0) # non-blocking reading for busy check
    ram_usage = psutil.virtual_memory().percent
    
    if cpu_usage > CPU_THRESHOLD or ram_usage > RAM_THRESHOLD:
        logger.info(f"System busy state triggered - CPU: {cpu_usage:.1f}%, RAM: {ram_usage:.1f}%")
        return True
    return False

def get_system_stats() -> dict:
    """
    Helper function to get current stats (can be used for our /health endpoint later).
    """
    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "ram_percent": psutil.virtual_memory().percent
    }
