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

    # Set DISPLAY environment variable if necessary
    os.environ['DISPLAY'] = ':0'  # Adjust if your display is different

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
                    subprocess.Popen(f"moonlight-qt {args}", shell=True, env=os.environ)
                    logger.info(f"Started moonlight-qt for device {mac_address}")
                except Exception as e:
                    logger.exception(f"Failed to start moonlight-qt: {e}")

    # Define signal handler for PropertiesChanged
    def properties_changed(interface, changed, invalidated, path):
        if interface != 'org.bluez.Device1':
            return

        logger.debug(f"PropertiesChanged on {path}: {changed}")

        # Extract the MAC address from the device path
        mac_address = path.split('/')[-1].replace('dev_', '').replace('_', ':').upper()
        if mac_address not in config['devices']:
            return

        # Check if 'Connected' property has changed
        if 'Connected' in changed:
            connected = changed['Connected'].value
            if connected:
                # Device connected
                if mac_address not in connected_devices:
                    connected_devices.add(mac_address)
                    logger.info(f"Device connected: {mac_address}")
                    args = config['devices'][mac_address].get('args', '')
                    try:
                        subprocess.Popen(f"moonlight-qt {args}", shell=True, env=os.environ)
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

    # Add signal handler for PropertiesChanged
    def signal_handler(message):
        if message.member != 'PropertiesChanged':
            return
        interface = message.body[0]
        changed_properties = message.body[1]
        invalidated_properties = message.body[2]
        path = message.path
        properties_changed(interface, changed_properties, invalidated_properties, path)

    bus.add_message_handler(signal_handler)

    logger.info("Bluetooth monitor started, waiting for device connections...")
    # Keep the program running indefinitely
    await asyncio.Future()  # Run forever

if __name__ == '__main__':
    asyncio.run(monitor_bluetooth())
