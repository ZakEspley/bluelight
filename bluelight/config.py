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

def update_allowed_devices(device_address: str):
    with open(CONFIG_FILE, 'r+') as config_file:
        config = json.load(config_file)
        allowed_devices = config.get('allowed_devices', [])

        # Add the new device if it's not already in the list
        if device_address not in allowed_devices:
            allowed_devices.append(device_address)
            config['allowed_devices'] = allowed_devices

            # Write back to the config file
            config_file.seek(0)
            json.dump(config, config_file, indent=4)
            config_file.truncate()

    print(f"Device {device_address} added to allowed devices.")