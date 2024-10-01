# bluelight/main.py

import typer
import asyncio
from bluelight.config import load_config, save_config
from bluelight.bluetooth_monitor import monitor_bluetooth

# Create a Typer application instance
app = typer.Typer()

@app.command()
def add_device(mac_address: str, args: str = ""):
    """
    Add a new Bluetooth device with optional moonlight-qt arguments.

    Args:
        mac_address (str): The MAC address of the Bluetooth device.
        args (str, optional): Additional arguments for moonlight-qt.
    """
    # Load existing configuration
    config = load_config()
    # Add or update the device entry
    config["devices"][mac_address] = {"args": args}
    # Save the updated configuration
    save_config(config)
    typer.echo(f"Added device {mac_address} with args '{args}'")

@app.command()
def set_timeout(seconds: int):
    """
    Set the timeout before closing moonlight-qt after device disconnection.

    Args:
        seconds (int): Timeout duration in seconds.
    """
    # Load existing configuration
    config = load_config()
    # Update the timeout value
    config["timeout"] = seconds
    # Save the updated configuration
    save_config(config)
    typer.echo(f"Set timeout to {seconds} seconds")

@app.command()
def run():
    """
    Start the Bluetooth monitoring service.
    """
    typer.echo("Starting Bluetooth monitor...")
    # Run the monitor asynchronously
    asyncio.run(monitor_bluetooth())

if __name__ == "__main__":
    # Run the Typer app when the script is executed
    app()
