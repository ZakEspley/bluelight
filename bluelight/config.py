# bluelight/config.py

import json
from pathlib import Path

# Define the path to the configuration file in the user's home directory
CONFIG_FILE = Path.home() / '.bluelight_config.json'

def load_config():
    """
    Load the configuration from the JSON file.
    If the file doesn't exist, return a default configuration.
    """
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        # Return default configuration if the file doesn't exist
        return {"devices": {}, "timeout": 300}

def save_config(config):
    """
    Save the configuration dictionary to the JSON file.
    """
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
