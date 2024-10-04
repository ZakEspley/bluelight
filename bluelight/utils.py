import getpass
import pwd
from pathlib import Path
import os

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