# bluelight/bluetooth_monitor.py

import asyncio
import subprocess
import logging
import os
from bluelight.config import load_config
from dbus_next.aio import MessageBus
from dbus_next import BusType

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

    # Initialize connected devices and start moonlight-qt if necessary
    for path, interfaces in managed_objects.items():
        device_props = interfaces.get('org.bluez.Device1')
        if device_props:
            connected = device_props.get('Connected').value
            mac_address = device_props.get('Address').value
            if connected and mac_address in config['devices']:
                connected_devices.add(mac_address)
                logger.info(f"Device already connected: {mac_address}")
                # Start moonlight-qt for the already connected device
                args = config['devices'][mac_address].get('args', '')
                try:
                    subprocess.Popen(f"moonlight-qt {args}", shell=True)
                    logger.info(f"Started moonlight-qt for device {mac_address}")
                except Exception as e:
                    logger.exception(f"Failed to start moonlight-qt: {e}")

    # Define signal handler for PropertiesChanged
    def properties_changed(interface_name, changed_properties, invalidated_properties, **kwargs):
        if interface_name != 'org.bluez.Device1':
            return

        message = kwargs['message']
        path = message.path

        logger.debug(f"PropertiesChanged on {path}: {changed_properties}")

        # Extract the MAC address from the device path
        mac_address = path.split('/')[-1].replace('dev_', '').replace('_', ':').upper()
        if mac_address not in config['devices']:
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

    # Subscribe to PropertiesChanged signals for org.bluez.Device1
    bus.subscribe(
        sender='org.bluez',
        interface='org.freedesktop.DBus.Properties',
        member='PropertiesChanged',
        arg0='org.bluez.Device1',
        signal_fired=properties_changed
    )

    logger.info("Bluetooth monitor started, waiting for device connections...")
    # Keep the program running indefinitely
    await asyncio.Future()  # Run forever

if __name__ == '__main__':
    asyncio.run(monitor_bluetooth())
