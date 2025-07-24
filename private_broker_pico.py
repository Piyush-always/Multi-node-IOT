import network
import time
from umqtt.simple import MQTTClient
import ubinascii
import machine
import socket

# --- GPIO Pin Configuration for Relays ---
UP_RELAY_PIN = 16    # GPIO pin for UP relay (change as needed)
DOWN_RELAY_PIN = 17  # GPIO pin for DOWN relay (change as needed)

# Initialize GPIO pins
up_relay = machine.Pin(UP_RELAY_PIN, machine.Pin.OUT)
down_relay = machine.Pin(DOWN_RELAY_PIN, machine.Pin.OUT)

# Set initial state (relays OFF)
up_relay.off()
down_relay.off()

# --- WiFi Configuration ---
WIFI_SSID = "test2"
WIFI_PASSWORD = "12345678"

# --- HiveMQ Cloud MQTT Configuration ---
MQTT_BROKER_URL = "46ae51f4f3d74f3ca138768beed1676d.s1.eu.hivemq.cloud"
MQTT_USERNAME = "Piyushalways7"
MQTT_PASSWORD = "Piyushalways7"

# Try SSL connection (this is what HiveMQ Cloud likely requires)
MQTT_PORT = 8883  # SSL port
USE_SSL = True    # HiveMQ Cloud typically requires SSL

# Connection parameters for stability
KEEPALIVE_INTERVAL = 30  # Reduced from 60 for better connection monitoring
PING_INTERVAL = 10       # Send ping every 10 seconds
MAX_RECONNECT_ATTEMPTS = 3

CLIENT_ID = f"pico_{ubinascii.hexlify(machine.unique_id()).decode()[:8]}"
MQTT_TOPIC = b'pico/messages'

mqtt_client = None
last_ping_time = 0
connection_stable = False

def control_relay(command):
    """Control relays based on MQTT command."""
    try:
        command = command.strip().lower()
        # print(f"Processing command: '{command}'")
        
        if command == "up 1":
            up_relay.on()
            print("UP relay turned ON")
        elif command == "up 0":
            up_relay.off()
            print("UP relay turned OFF")
        elif command == "down 1":
            down_relay.on()
            print("DOWN relay turned ON")
        elif command == "down 0":
            down_relay.off()
            print("DOWN relay turned OFF")
        else:
            print(f"Unknown command: {command}")
            print("Valid commands: 'up 1', 'up 0', 'down 1', 'down 0'")
            
    except Exception as e:
        print(f"Error controlling relay: {e}")

def on_message_received(topic, msg):
    """Callback function to handle incoming MQTT messages."""
    try:
        message = msg.decode('utf-8')
        # print(f"Received message on topic {topic.decode('utf-8')}: {message}")
        
        # Process the relay command
        control_relay(message)
        
    except Exception as e:
        print(f"Error processing message: {e}")

def connect_to_wifi():
    """Connects the device to WiFi with retry logic."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    # Disconnect if already connected to refresh connection
    if wlan.isconnected():
        print("Disconnecting from WiFi to refresh connection...")
        wlan.disconnect()
        time.sleep(2)
    
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
        timeout = 15  # Increased timeout
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            print(".", end="")
            
        print()  # New line after dots
        if not wlan.isconnected():
            print("Failed to connect to WiFi")
            return False
            
    print(f"Connected to WiFi! IP Address: {wlan.ifconfig()[0]}")
    return True

def test_broker_connectivity():
    """Test if we can reach the MQTT broker."""
    try:
        print(f"Testing connectivity to {MQTT_BROKER_URL}:{MQTT_PORT}")
        addr = socket.getaddrinfo(MQTT_BROKER_URL, MQTT_PORT)[0][-1]
        s = socket.socket()
        s.settimeout(10)
        s.connect(addr)
        s.close()
        print("✓ Broker is reachable")
        return True
    except Exception as e:
        print(f"✗ Cannot reach broker: {e}")
        return False

def connect_and_subscribe():
    """Connects to the MQTT broker and subscribes to the topic."""
    global mqtt_client, connection_stable
    
    print(f"Connecting to MQTT Broker: {MQTT_BROKER_URL}...")
    print(f"Using Client ID: {CLIENT_ID}")
    print(f"Port: {MQTT_PORT}, SSL: {USE_SSL}")
    
    # Test basic connectivity first
    if not test_broker_connectivity():
        return False
    
    try:
        # Clean up existing connection if any
        if mqtt_client:
            try:
                mqtt_client.disconnect()
            except:
                pass
        
        # Create MQTT client with conditional SSL
        if USE_SSL:
            mqtt_client = MQTTClient(
                client_id=CLIENT_ID,
                server=MQTT_BROKER_URL,
                port=MQTT_PORT,  
                user=MQTT_USERNAME,
                password=MQTT_PASSWORD,
                keepalive=KEEPALIVE_INTERVAL,  # Use configurable keepalive
                ssl=True,
                ssl_params={
                    'server_hostname': MQTT_BROKER_URL,
                    'do_handshake': True
                }
            )
        else:
            mqtt_client = MQTTClient(
                client_id=CLIENT_ID,
                server=MQTT_BROKER_URL,
                port=MQTT_PORT,
                user=MQTT_USERNAME,
                password=MQTT_PASSWORD,
                keepalive=KEEPALIVE_INTERVAL
            )
        
        mqtt_client.set_callback(on_message_received)
        
        # Connect to broker
        print("Attempting to connect...")
        mqtt_client.connect()
        print("Connected to MQTT Broker successfully!")
        
        # Subscribe to topic
        mqtt_client.subscribe(MQTT_TOPIC)
        print(f"Subscribed to topic: {MQTT_TOPIC.decode('utf-8')}")
        
        connection_stable = True
        return True
        
    except Exception as e:
        print(f"MQTT Connection Error: {e}")
        print(f"Error type: {type(e)}")
        connection_stable = False
        
        # Specific error handling for common issues
        if "MQTTException: 5" in str(e):
            print("Error 5: Connection refused - Check credentials and broker URL")
        elif "MQTTException: 1" in str(e):
            print("Error 1: Unacceptable protocol version")
        elif "MQTTException: 2" in str(e):
            print("Error 2: Identifier rejected")
        elif "MQTTException: 3" in str(e):
            print("Error 3: Server unavailable")
        elif "MQTTException: 4" in str(e):
            print("Error 4: Bad username or password")
            
        return False

def send_ping():
    """Send a ping to keep the connection alive."""
    global last_ping_time, mqtt_client
    
    current_time = time.time()
    if current_time - last_ping_time >= PING_INTERVAL:
        try:
            mqtt_client.ping()
            last_ping_time = current_time
            print(".")
        except Exception as e:
            print(f"Ping failed: {e}")
            return False
    return True

def is_wifi_connected():
    """Check if WiFi is still connected."""
    wlan = network.WLAN(network.STA_IF)
    return wlan.isconnected()

def robust_reconnect():
    """Robust reconnection with WiFi check."""
    global connection_stable
    
    print("Starting robust reconnection...")
    connection_stable = False
    
    # First check WiFi
    if not is_wifi_connected():
        print("WiFi disconnected, reconnecting...")
        if not connect_to_wifi():
            return False
    
    # Then reconnect MQTT
    for attempt in range(MAX_RECONNECT_ATTEMPTS):
        print(f"MQTT reconnection attempt {attempt + 1}/{MAX_RECONNECT_ATTEMPTS}")
        if connect_and_subscribe():
            return True
        time.sleep(2)  # Short delay between attempts
    
    print("Failed to reconnect after all attempts")
    return False

def main():
    """Main program loop."""
    print("=== Relay Control System Starting ===")
    print(f"UP relay on GPIO {UP_RELAY_PIN}")
    print(f"DOWN relay on GPIO {DOWN_RELAY_PIN}")
    print("Commands: 'up 1', 'up 0', 'down 1', 'down 0'")
    print("=====================================")
    
    if not connect_to_wifi():
        print("Cannot continue without WiFi connection")
        return
    
    # Try to connect to MQTT broker
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        if connect_and_subscribe():
            break
        else:
            retry_count += 1
            print(f"Retry {retry_count}/{max_retries} in 5 seconds...")
            time.sleep(5)
    
    if retry_count >= max_retries:
        print("Max retries reached. Rebooting...")
        machine.reset()
    
    print("--- Waiting for relay commands... ---")
    global last_ping_time
    last_ping_time = time.time()
    
    # Main loop with improved error handling
    while True:
        try:
            # Check for incoming messages
            mqtt_client.check_msg()
            
            # Send periodic pings to maintain connection
            if connection_stable and not send_ping():
                raise OSError("Ping failed")
            
            time.sleep(0.1)
            
        except OSError as e:
            print(f"Connection lost: {e}")
            
            # Try robust reconnection
            if not robust_reconnect():
                print("Reconnection failed. Rebooting...")
                time.sleep(5)
                machine.reset()
        
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(1)  # Brief pause before continuing

if __name__ == "__main__":
    main()

