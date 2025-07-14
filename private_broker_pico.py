#
# Raspberry Pi Pico W MicroPython Code - Secure MQTT for Private HiveMQ Cloud
# Description: This script connects securely to a private HiveMQ Cloud broker
# using SSL/TLS encryption and authentication. It includes robust error
# handling to automatically reconnect if the connection is lost.
#
# Required Library: micropython-umqtt.simple
#

import network
import time
from umqtt.simple import MQTTClient
import ubinascii
import machine

# --- WiFi Configuration ---
WIFI_SSID = "test2"
WIFI_PASSWORD = "12345678"
# --------------------------

# --- HiveMQ Cloud MQTT Configuration ---
# IMPORTANT: Fill these in with the credentials from your HiveMQ Cloud dashboard
MQTT_BROKER_URL = "46ae51f4f3d74f3ca138768beed1676d.s1.eu.hivemq.cloud"
MQTT_USERNAME = "Piyushalways7"
MQTT_PASSWORD = "Piyushalways7"
MQTT_PORT = 8883 # Standard Port for Secure MQTT (TLS)
# ---------------------------------------

CLIENT_ID = ubinascii.hexlify(machine.unique_id()).decode()
# This topic is now on your private broker, so it doesn't need to be as unique.
MQTT_TOPIC = b'pico/messages' 

# Global variable to hold the mqtt_client instance
mqtt_client = None

def on_message_received(topic, msg):
    """Callback function to handle incoming MQTT messages."""
    print(f"Received message on topic {topic}: {msg.decode('utf-8')}")

def connect_to_wifi():
    """Connects the device to WiFi."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(1)
    print(f"Connected to WiFi! IP Address: {wlan.ifconfig()[0]}")

def connect_and_subscribe():
    """Connects to the MQTT broker and subscribes to the topic."""
    global mqtt_client
    print(f"Connecting to secure MQTT Broker: {MQTT_BROKER_URL}...")
    # For a secure connection, we must provide user, password, port, and ssl=True
    mqtt_client = MQTTClient(
        client_id=CLIENT_ID,
        server=MQTT_BROKER_URL,
        port=MQTT_PORT,
        user=MQTT_USERNAME,
        password=MQTT_PASSWORD,
        keepalive=60,
        ssl=True # This is crucial for a secure connection
    )
    mqtt_client.set_callback(on_message_received)
    try:
        mqtt_client.connect()
        mqtt_client.subscribe(MQTT_TOPIC)
        print(f"Connected to MQTT Broker and subscribed to topic: {MQTT_TOPIC.decode('utf-8')}")
        print("--- Waiting for messages... ---")
    except OSError as e:
        print(f"Failed to connect to MQTT broker: {e}. Rebooting...")
        time.sleep(5)
        machine.reset()

# --- Main Program ---
connect_to_wifi()
connect_and_subscribe()

while True:
    try:
        mqtt_client.check_msg()
        time.sleep(0.1)
    except OSError as e:
        print("Connection lost. Reconnecting...")
        time.sleep(5)
        connect_and_subscribe()

