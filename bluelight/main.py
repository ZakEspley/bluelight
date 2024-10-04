# bluelight/main.py

import typer
import asyncio
import subprocess
from bluelight.config import load_config, save_config
from bluelight.bluetooth_monitor import monitor_bluetooth, pair_new_controller
from rich.console import Console
from rich.prompt import Prompt
from pathlib import Path
from bluelight.utils import get_original_user_info

# Create a Typer application instance
app = typer.Typer()
console = Console()
user, home_dir, uid = get_original_user_info()
# Paths to systemd files
SERVICE_FILE_PATH = "/etc/systemd/system/bluelight.service"
SERVICE_CONTENT = f"""
[Unit]
Description=Bluelight Daemon Service
After=network.target

[Service]
ExecStart=bluelight run
Restart=always
User={user}
Group={user}
WorkingDirectory={home_dir}
Environment=XDG_RUNTIME_DIR=/run/user/{uid}
#AmbientCapabilities=CAP_NET_ADMIN CAP_NET_RAW
#NoNewPrivileges=true
BusName=bluelight

[Install]
WantedBy=default.target
"""


@app.command()
def daemon_start():
    """
    Creates a systemd service to run bluelight as a daemon on startup.
    """
    service_file = Path(SERVICE_FILE_PATH)
    
    # Write the service file content
    with open(service_file, 'w') as f:
        f.write(SERVICE_CONTENT)
    
    # Set permissions and enable service
    subprocess.run(["sudo", "chmod", "644", SERVICE_FILE_PATH], check=True)
    subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
    subprocess.run(["sudo", "systemctl", "enable", "bluelight.service"], check=True)
    subprocess.run(["sudo", "systemctl", "start", "bluelight.service"], check=True)
    
    typer.echo("Bluelight service created and started successfully.")

@app.command()
def daemon_stop():
    """
    Removes the systemd service for bluelight and disables it from startup.
    """
    subprocess.run(["sudo", "systemctl", "stop", "bluelight.service"], check=True)
    subprocess.run(["sudo", "systemctl", "disable", "bluelight.service"], check=True)
    service_file = Path(SERVICE_FILE_PATH)
    
    # Remove the service file
    if service_file.exists():
        service_file.unlink()
    
    subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
    typer.echo("Bluelight service stopped and removed successfully.")

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
    if len(allowed_devices.items()) == 0:
        console.print("[bold red]No devices saved. Run the command [italic]bluelight pair[/italic] to pair a controller[/bold red]")
        raise typer.Exit()
    for mac_address, device_info in allowed_devices.items():
        display_name = device_info["name"]
        manufacturer_name = device_info["manufacturer"]
        nickname = device_info["nickname"]
        device_list.append(mac_address)
        console.print(f"[{idx}] [bold]{nickname}[/bold] : {display_name} : {manufacturer_name} : ({mac_address})")
        idx += 1
    # Add an option to quit
    console.print(f"[{idx}] [bold red]Quit[/bold red]")

    # Use Rich prompt to select a device
    selected_idx = Prompt.ask(
        "[bold yellow]Select the device number you want to connect to[/bold yellow]", 
        choices= [str(i+1) for i in range(idx)]
    )
    selected_idx = int(selected_idx)

    if selected_idx == idx:
        console.print("[bold red] Quitting ... [/bold red]")
        raise typer.Exit()
    selected_name = allowed_devices[device_list[selected_idx-1]]["name"]
    selected_address = device_list[selected_idx-1]


    console.print(f"[bold orange] Removing device {selected_name} ({selected_address})...[/bold orange]")
    allowed_devices.pop(selected_address)
    try:
        subprocess.run(["bluetoothctl", "remove", selected_address], check=True)
        console.print(f"[bold green] Device {selected_name} ({selected_address}) has been successfully removed[/bold green]")
        config["allowed_devices"] = allowed_devices
        save_config(config)
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Failed to remove {selected_name} ({selected_address}). Error: {e}[/bold red]")
    

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
