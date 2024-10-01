# bluelight/bluetooth_monitor.py

import asyncio
from bluelight.config import load_config
import subprocess
from dbus_next.aio import MessageBus
from dbus_next.constants import MessageType

async def monitor_bluetooth():
    """
    Asynchronously monitor Bluetooth connection and disconnection events
    using the D-Bus interface provided by BlueZ.
    """
    # Load configuration settings
    config = load_config()

    # Create a set to keep track of connected devices
    connected_devices = set()

    # Connect to the system bus
    bus = await MessageBus(bus_type=MessageBus.TYPE_SYSTEM).connect()

    # Get a proxy object for the BlueZ service
    introspection = await bus.introspect('org.bluez', '/org/bluez/hci0')
    obj = bus.get_proxy_object('org.bluez', '/org/bluez/hci0', introspection)
    adapter = obj.get_interface('org.bluez.Adapter1')

    # Define signal handlers for interfaces added and removed
    async def interfaces_added(path, interfaces):
        """
        Handler for when a new interface is added.
        """
        device_props = interfaces.get('org.bluez.Device1')
        if device_props:
            mac_address = device_props.get('Address')
            if mac_address in config['devices']:
                # Start moonlight-qt with optional arguments
                args = config['devices'][mac_address].get('args', '')
                subprocess.Popen(f"moonlight-qt {args}", shell=True)
                connected_devices.add(mac_address)
                print(f"Device connected: {mac_address}")

    async def interfaces_removed(path, interfaces):
        """
        Handler for when an interface is removed.
        """
        if 'org.bluez.Device1' in interfaces:
            # Extract the MAC address from the device path
            mac_address = path.rsplit('/', 1)[-1].replace('_', ':')
            if mac_address in connected_devices:
                # Wait for the optional timeout before closing moonlight-qt
                timeout = config.get('timeout', 0)
                await asyncio.sleep(timeout)
                subprocess.Popen("pkill moonlight-qt", shell=True)
                connected_devices.remove(mac_address)
                print(f"Device disconnected: {mac_address}")

    # Add signal listeners for InterfacesAdded and InterfacesRemoved
    bus.add_message_handler(lambda msg: asyncio.create_task(
        handle_signals(msg, interfaces_added, interfaces_removed)
    ))

    # Keep the program running
    await asyncio.Future()  # Run forever

async def handle_signals(message, interfaces_added_handler, interfaces_removed_handler):
    """
    Handle D-Bus signals for interface additions and removals.
    """
    if message.message_type != MessageType.SIGNAL:
        return

    if message.member == 'InterfacesAdded':
        path = message.body[0]
        interfaces = message.body[1]
        await interfaces_added_handler(path, interfaces)
    elif message.member == 'InterfacesRemoved':
        path = message.body[0]
        interfaces = message.body[1]
        await interfaces_removed_handler(path, interfaces)
