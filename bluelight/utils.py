import getpass
import pwd
from pathlib import Path
import os
import subprocess

def get_original_user_info() -> tuple:
    """
    Returns the original (non-root) user and their home directory.
    Uses the SUDO_USER environment variable if running as sudo.
    """
    # If running with sudo, get the original user from SUDO_USER environment variable
    original_user = os.getenv("SUDO_USER")
    if original_user:
        home_dir = pwd.getpwnam(original_user).pw_dir
    else:
        # Fallback to current user if not running with sudo
        original_user = getpass.getuser()
        home_dir = str(Path.home())
    uid = pwd.getpwnam(original_user).pw_uid
    return original_user, home_dir, uid

def is_service_active(service_name: str) -> bool:
    """
    Check if a systemd service is currently active (running).
    
    Args:
        service_name (str): Name of the service to check.
    
    Returns:
        bool: True if the service is active, False otherwise.
    """
    result = subprocess.run(["systemctl", "is-active", service_name], capture_output=True, text=True)
    return result.stdout.strip() == "active"

def is_service_enabled(service_name: str) -> bool:
    """
    Check if a systemd service is currently enabled.
    
    Args:
        service_name (str): Name of the service to check.
    
    Returns:
        bool: True if the service is enabled, False otherwise.
    """
    result = subprocess.run(["systemctl", "is-enabled", service_name], capture_output=True, text=True)
    return result.stdout.strip() == "enabled"