import network
from time import sleep
from umqtt.simple import MQTTClient
import ujson

# Replace these values with your own
SSID = "KME759_Group_2"
PASSWORD = "Ryhma2Koulu."
BROKER_IP = "192.168.2.253"
port =1883
# Function to connect to WLAN
def connect_wlan():
    # Connecting to the group WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    # Attempt to connect once per second
    while wlan.isconnected() == False:
        print("Connecting... ")
        sleep(1)

    # Print the IP address of the Pico
    print("Connection successful. Pico IP:", wlan.ifconfig()[0])
    
def connect_mqtt():
    mqtt_client=MQTTClient("", BROKER_IP, port)
    mqtt_client.connect(clean_session=True)
    return mqtt_client

def message_callback(topic, msg):
    try:
        message = ujson.loads(msg)
        print(message)
        print(f"Stress index: {message["data"]["analysis"]["stress_index"]}")
    except Exception as e:
        print("failed delivering message", e)

# Main program
if __name__ == "__main__":
    try:
        connect_wlan()
        mqtt_client=connect_mqtt()
        mqtt_client.set_callback(message_callback)
        mqtt_client.subscribe("hr-data") 
        mqtt_client.subscribe("kubios-response")

        while True:
            # Sending a message every 5 seconds.
            topic = "kubios-request"
            message = {
                "id": 123,
                "type":"RRI",
                "data": [828, 836, 852, 760, 800, 796, 856, 824, 808, 776, 724, 816, 800, 812, 812,
812, 756, 820, 812, 800],
                "analysis": {"type": "readiness" }
                    }
            msg = ujson.dumps(message)
            mqtt_client.publish(topic, msg)
            sleep(5)
            mqtt_client.check_msg()

            
    except Exception as e:
        print(f"Failed to send MQTT message: {e}")

