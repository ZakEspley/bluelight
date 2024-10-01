# bluelight/bluetooth_monitor.py

import asyncio
import subprocess
import logging
from bluelight.config import load_config, update_allowed_devices
from dbus_next.aio import MessageBus


BLUEZ_SERVICE_NAME = "org.bluez"
ADAPTER_INTERFACE = "org.bluez.Adapter1"
DEVICE_INTERFACE = "org.bluez.Device1"
OBJECT_MANAGER_INTERFACE = "org.freedesktop.DBus.ObjectManager"
DBUS_PROPERTIES = "org.freedesktop.DBus.Properties"

async def get_managed_objects(bus):
    """Returns all managed objects."""
    proxy = await bus.get_proxy_object(BLUEZ_SERVICE_NAME, "/", None)
    managed_objects = await proxy.get_interface(OBJECT_MANAGER_INTERFACE).call_get_managed_objects()
    return managed_objects

async def pair_new_controller():
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

    # Get all managed objects and identify the Bluetooth adapter
    managed_objects = await get_managed_objects(bus)
    adapter_path = None
    for path, interfaces in managed_objects.items():
        if ADAPTER_INTERFACE in interfaces:
            adapter_path = path
            break

    if not adapter_path:
        print("No Bluetooth adapter found.")
        return

    # Start discovery on the adapter
    adapter = await bus.get_proxy_object(BLUEZ_SERVICE_NAME, adapter_path, None).get_interface(ADAPTER_INTERFACE)
    await adapter.call_start_discovery()
    print("Discovery started...")

    # Wait for device discovery and pair the first available device
    device_path = None
    async for path, interfaces in get_managed_objects(bus).items():
        if DEVICE_INTERFACE in interfaces:
            device_path = path
            break

    if not device_path:
        print("No devices found.")
        await adapter.call_stop_discovery()
        return

    # Pair the device
    device = await bus.get_proxy_object(BLUEZ_SERVICE_NAME, device_path, None).get_interface(DEVICE_INTERFACE)
    await device.call_pair()
    await device.call_trust()
    print(f"Device paired and trusted: {device_path}")

    # Update the allowed devices in config
    device_properties = await bus.get_proxy_object(BLUEZ_SERVICE_NAME, device_path, None).get_interface(DBUS_PROPERTIES)
    device_address = (await device_properties.call_get(DEVICE_INTERFACE, "Address")).value
    update_allowed_devices(device_address)

    # Stop discovery
    await adapter.call_stop_discovery()
    print("Discovery stopped.")

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

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

if __name__ == '__main__':
    asyncio.run(monitor_bluetooth())
