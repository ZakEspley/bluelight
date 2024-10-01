# bluelight/bluetooth_monitor.py

import asyncio
from bluelight.config import load_config
import subprocess
from dbus_next.aio import MessageBus
from dbus_next import BusType
from dbus_next.constants import NameFlag

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
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

    # Obtain the BlueZ object manager interface
    introspection = await bus.introspect('org.bluez', '/')
    obj = bus.get_proxy_object('org.bluez', '/', introspection)
    obj_manager = obj.get_interface('org.freedesktop.DBus.ObjectManager')

    # Define signal handlers for InterfacesAdded and InterfacesRemoved
    def interfaces_added(path, interfaces):
        """
        Handler for when a new interface is added.
        """
        device_props = interfaces.get('org.bluez.Device1')
        if device_props:
            # Get the MAC address of the connected device
            mac_address = device_props.get('Address').value
            if mac_address in config['devices']:
                # Start moonlight-qt with optional arguments
                args = config['devices'][mac_address].get('args', '')
                subprocess.Popen(f"moonlight-qt {args}", shell=True)
                connected_devices.add(mac_address)
                print(f"Device connected: {mac_address}")

    def interfaces_removed(path, interfaces):
        """
        Handler for when an interface is removed.
        """
        if 'org.bluez.Device1' in interfaces:
            # Extract the MAC address from the device path
            mac_address = path.split('/')[-1].replace('dev_', '').replace('_', ':')
            if mac_address in connected_devices:
                # Wait for the optional timeout before closing moonlight-qt
                timeout = config.get('timeout', 0)
                asyncio.create_task(disconnect_device(mac_address, timeout))
                connected_devices.remove(mac_address)
                print(f"Device disconnected: {mac_address}")

    async def disconnect_device(mac_address, timeout):
        """
        Waits for the specified timeout and then kills moonlight-qt.
        """
        await asyncio.sleep(timeout)
        subprocess.Popen("pkill moonlight-qt", shell=True)

    # Connect signal handlers
    obj_manager.on_interfaces_added(interfaces_added)
    obj_manager.on_interfaces_removed(interfaces_removed)

    # Call GetManagedObjects to initialize the connected devices
    managed_objects = await obj_manager.call_get_managed_objects()

    # Initialize connected devices
    for path, interfaces in managed_objects.items():
        device_props = interfaces.get('org.bluez.Device1')
        if device_props:
            connected = device_props.get('Connected').value
            if connected:
                mac_address = device_props.get('Address').value
                if mac_address in config['devices']:
                    connected_devices.add(mac_address)
                    print(f"Device already connected: {mac_address}")

    # Keep the program running indefinitely
    await asyncio.Future()  # Run forever
