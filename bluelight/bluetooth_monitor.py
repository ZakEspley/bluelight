# bluelight/bluetooth_monitor.py

import asyncio
import subprocess
import logging
from bluelight.config import load_config, update_allowed_devices
from dbus_next.aio import MessageBus
from dbus_next import BusType
import typer
from rich.prompt import Prompt
from rich.console import Console
from bluelight.config import load_config, update_allowed_devices
from bleak import BleakClient, BleakScanner
import json

BLUEZ_SERVICE_NAME = "org.bluez"
ADAPTER_INTERFACE = "org.bluez.Adapter1"
DEVICE_INTERFACE = "org.bluez.Device1"
OBJECT_MANAGER_INTERFACE = "org.freedesktop.DBus.ObjectManager"
DBUS_PROPERTIES = "org.freedesktop.DBus.Properties"

console = Console()

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

async def get_managed_objects(bus):
    """Returns all managed objects."""
    introspection = await bus.introspect('org.bluez', '/')
    proxy = bus.get_proxy_object(BLUEZ_SERVICE_NAME, "/", introspection)
    managed_objects = await proxy.get_interface(OBJECT_MANAGER_INTERFACE).call_get_managed_objects()
    return managed_objects


async def monitor_bluetooth():
    """
    Monitor Bluetooth device connections and disconnections using D-Bus
    PropertiesChanged signals on org.bluez.Device1 interfaces.
    """
    # Load configuration settings
    config = load_config()

    # Connect to the system bus
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

    # Keep track of connected devices
    connected_devices = set()

    # Get all managed objects
    introspection = await bus.introspect('org.bluez', '/')
    obj = bus.get_proxy_object('org.bluez', '/', introspection)
    obj_manager = obj.get_interface('org.freedesktop.DBus.ObjectManager')

    managed_objects = await obj_manager.call_get_managed_objects()

    # Function to create controller_status callback with mac_address closure
    def make_controller_status(mac_address):
        async def controller_status(interface_name, changed_properties, invalidated_properties):
            if interface_name != 'org.bluez.Device1':
                return
            # Check if 'Connected' property has changed
            if 'Connected' in changed_properties:
                connected = changed_properties['Connected'].value
                if connected:
                    # Device connected
                    if mac_address not in connected_devices:
                        connected_devices.add(mac_address)
                        logger.info(f"Device connected: {mac_address}")
                        args = config['devices'][mac_address].get('args', '')
                        try:
                            subprocess.Popen(f"moonlight-qt {args}", shell=True)
                            logger.info(f"Started moonlight-qt for device {mac_address}")
                        except Exception as e:
                            logger.exception(f"Failed to start moonlight-qt: {e}")
                else:
                    # Device disconnected
                    if mac_address in connected_devices:
                        connected_devices.remove(mac_address)
                        logger.info(f"Device disconnected: {mac_address}")
                        # Wait for the optional timeout before closing moonlight-qt
                        timeout = config.get('timeout', 0)
                        asyncio.create_task(disconnect_device(mac_address, timeout))
            else:
                # If only other properties (e.g., Battery) changed, do nothing
                pass
        return controller_status

    # Initialize connected devices and set up signal handlers
    for path, interfaces in managed_objects.items():
        # Look for any type of Bluetooth interface device
        device_props = interfaces.get('org.bluez.Device1')
        if device_props:
            mac_address = device_props.get('Address').value
            if mac_address in config['devices']:
                # Introspect the device
                device_introspection = await bus.introspect('org.bluez', path)
                # Create proxy object for the device
                device_obj = bus.get_proxy_object('org.bluez', path, device_introspection)
                # Get the Properties interface
                device_props_interface = device_obj.get_interface('org.freedesktop.DBus.Properties')
                # Add the controller_status callback to on_properties_changed signal
                device_props_interface.on_properties_changed(make_controller_status(mac_address))
                # Check if device is already connected
                connected = device_props.get('Connected').value
                if connected:
                    # Device is already connected
                    connected_devices.add(mac_address)
                    logger.info(f"Device already connected: {mac_address}")
                    # Start moonlight-qt for the already connected device
                    args = config['devices'][mac_address].get('args', '')
                    try:
                        subprocess.Popen(f"moonlight-qt {args}", shell=True)
                        logger.info(f"Started moonlight-qt for device {mac_address}")
                    except Exception as e:
                        logger.exception(f"Failed to start moonlight-qt: {e}")

    async def disconnect_device(mac_address, timeout):
        """
        Waits for the specified timeout and then kills moonlight-qt.
        """
        await asyncio.sleep(timeout)
        try:
            subprocess.Popen("pkill moonlight-qt", shell=True)
            logger.info(f"Stopped moonlight-qt after device {mac_address} disconnected")
        except Exception as e:
            logger.exception(f"Failed to kill moonlight-qt: {e}")

    logger.info("Bluetooth monitor started, waiting for device connections...")
    # Keep the program running indefinitely
    await asyncio.Future()  # Run forever


def pair_new_controller():
    """
    Connect to a wireless Bluetooth controller using Bleak and set the device as trusted.
    """
    # Load company identifiers for manufacturer data
    with open("./company_identifiers.json") as file:
        COMPANY_IDENTIFIERS = json.load(file)
    # Convert keys to integers for proper comparison
    COMPANY_IDENTIFIERS = {int(k): COMPANY_IDENTIFIERS[k] for k in COMPANY_IDENTIFIERS}
    async def connect():
        # Start Bluetooth scanning
        console.print("[bold green]Scanning for Bluetooth devices...[/bold green]")
        devices = await BleakScanner.discover(return_adv=True)

        if not devices:
            console.print("[bold red]No Bluetooth devices found. Please ensure the device is in pairing mode.[/bold red]")
            raise typer.Exit()

        # Create a list of devices with more context using metadata or address as fallback
        device_list = {}
        idx = 1
        for mac_address, (device, advertisement_data) in devices.items():
            # Extract manufacturer data if available
            manufacturer_name = "Unknown Manufacturer"
            if advertisement_data.manufacturer_data:
                for manufacturer_id in advertisement_data.manufacturer_data:
                    manufacturer_name = COMPANY_IDENTIFIERS.get(manufacturer_id, "Unknown Manufacturer")

            # Set device name or use "Unknown Device" if name is not available
            device_name = device.name or "Unknown Device"
            
            # Check if device name is the same as the MAC address, which indicates an unknown device
            if str.join(":",device_name.split("-")) == mac_address:
                device_name = "Unknown Device"

            # Highlight potential controllers based on device name
            if "controller" in device_name.lower():
                display_name = f"[bold green]{device_name}[/bold green]"
            else:
                display_name = device_name

            # Store the device information for display and selection
            device_list[str(idx)] = {
                "device": device,
                "name": device_name,
                "manufacturer": manufacturer_name,
                "address": mac_address
            }
            # Display the device information with index
            console.print(f"[{idx}] {display_name} : {manufacturer_name} : ({mac_address})")
            idx += 1

        # Add an option to quit
        console.print(f"[{idx}] [bold red]Quit[/bold red] (Run again to rescan)")

        # Use Rich prompt to select a device
        selected_idx = Prompt.ask(
            "[bold yellow]Select the device number you want to connect to[/bold yellow]", 
            choices=list(device_list.keys()) + [str(idx)]
        )

        if selected_idx == str(idx):
            console.print("[bold red]Quitting...[/bold red]")
            raise typer.Exit()

        # Get selected device information
        selected_device = device_list[selected_idx]
        console.print(f"[bold green]Connecting to {selected_device['name']} ({selected_device['address']})...[/bold green]")

        # Attempt to connect to the selected device
        async with BleakClient(selected_device['address']) as client:
            if client.is_connected:
                console.print(f"[bold green]Successfully connected to {selected_device['name']}![/bold green]")

                # Mark the device as trusted using `bluetoothctl`
                try:
                    console.print(f"[bold green]Setting {selected_device['address']} as a trusted device...[/bold green]")
                    # Run `bluetoothctl` command to set device as trusted
                    subprocess.run(["bluetoothctl", "trust", selected_device['address']], check=True)
                    console.print(f"[bold green]Device {selected_device['address']} is now trusted![/bold green]")
                    update_allowed_devices(selected_device['address'], selected_device['name'], selected_device['manufacturer'])
                except subprocess.CalledProcessError as e:
                    console.print(f"[bold red]Failed to set {selected_device['address']} as trusted. Error: {e}[/bold red]")
            else:
                console.print(f"[bold red]Failed to connect to {selected_device['name']}.[/bold red]")

    # Run the connection function
    asyncio.run(connect())

if __name__ == '__main__':
    asyncio.run(monitor_bluetooth())
