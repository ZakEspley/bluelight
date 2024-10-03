# bluelight/main.py

import typer
import asyncio
import subprocess
from bluelight.config import load_config, save_config
from bluelight.bluetooth_monitor import monitor_bluetooth, pair_new_controller
from rich.console import Console
from rich.prompt import IntPrompt

# Create a Typer application instance
app = typer.Typer()
console = Console()

@app.command()
def timeout(seconds: int):
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
def pair():
    """
    Puts the application into pairing mode to pair new controllers.
    """
    typer.echo("Entering pairing mode. Please make your controller discoverable.")
    asyncio.run(pair_new_controller())
    typer.echo("Pairing mode complete.")

@app.command()
def unpair():
    """
    Removes one of the devices from your list.
    """
    config = load_config()
    allowed_devices = config.get("allowed_devices")
    device_list = []
    idx = 1
    for mac_address, device_info in allowed.items():
        display_name = device_info["name"]
        manufacturer_name = device_info["manufacturer"]
        device_list.append(mac_address)
        console.print(f"[{idx}] {display_name} : {manufacturer_name} : ({mac_address})")
        idx += 1
    # Add an option to quit
    console.print(f"[{idx}] [bold red]Quit[/bold red]")

    # Use Rich prompt to select a device
    selected_idx = IntPrompt.ask(
        "[bold yellow]Select the device number you want to connect to[/bold yellow]", 
        choices=list(range(idx+1))[1:]
    )

    if selected_idx == idx:
        console.print("[bold red] Quitting ... [/bold red]")
        raise typer.Exit()
    selected_name = allowed_devices[device_list[idx-1]]["name"]
    selected_address = allowed_devices[device_list[idx-1]]


    console.print(f"[bold orange] Removing device {selected_name} ({selected_address})...[/bold orange]")
    allowed_devices.pop(selected_address)
    try:
        subprocess.run(["bluetoothctl", "remove", selected_address], check=True)
        console.print(f"[bold green] Device {selected_name} ({selected_address}) has been successfully removed[/bold green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Failed to remove {selected_device} ({selected_address}). Error: {e}[/bold red]")

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
