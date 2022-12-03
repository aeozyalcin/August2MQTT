import paho.mqtt.client as mqtt
import bluepy.btle as btle
import augustpy.lock
import json
import time
import argparse
import threading

global mqtt_event
global mqtt_message
global lock


def onStatusUpdate(state):
    client.publish("august/lock/state", state) 

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("august/lock/set")

def on_mqtt(client, userdata, message):
    # global lock
    global mqtt_event
    global mqtt_message

    # print("received message: " ,str(message.payload.decode("utf-8")))
    # print("received topic: " ,str(message.topic.decode("utf-8")))
    print(" Received message " + str(message.payload)
        + " on topic '" + message.topic
        + "' with QoS " + str(message.qos))

    mqtt_message = message
    mqtt_event.set()    

    # if(str(message.payload.decode("utf-8")) == 'LOCK'):
    #     print("got lock!")
    #     if(lock.is_connected()):
    #         try:                
    #             lock.force_lock()
    #         except btle.BTLEDisconnectError:
    #             #lock.conn_state = "disconnected"
    #             lock.is_secure = False
    #             lock.session = None
    #             lock.peripheral = None
    #             print("Device disconnected unexpectedly!")
    #             lock.connect()
    #             lock.force_lock()
    # elif(str(message.payload.decode("utf-8")) == 'UNLOCK'):
    #     print("got unlock!")
    #     if(lock.is_connected()):
    #         try:                
    #             lock.force_unlock()
    #         except btle.BTLEDisconnectError:
    #             print("Failed... Reconnecting.")
    #             lock.connect()            
    # elif(str(message.payload.decode("utf-8")) == 'STATUS'):
    #     if(lock.is_connected()):
    #         lock.getStatus()

mqtt_event = threading.Event()

broker_address="192.168.0.192" # <== this is where your MQTT server IP goes. No need for the port.
client = mqtt.Client("august_rpi") # <== this is just the name of the MQTT client. I called mine "august_rpi"
client.username_pw_set("august", "lock") # <== use this if your MQTT server requires authentication. If not, you can comment out this whole line.
client.connect(broker_address)

client.publish("august/bridge/availability", "online", retain=True)
#client.subscribe("august/lock/set")
client.on_message = on_mqtt
client.on_connect = on_connect
client.loop_start()

config = None
i = 0

with open("config.json", "r") as config_file:
    config = json.load(config_file)

if type(config) is dict:
    config = [config]

locks = []
for lock_config in config:
    lock = augustpy.lock.Lock(lock_config["bluetoothAddress"], lock_config["handshakeKey"], lock_config["handshakeKeyIndex"])
    if "name" in lock_config:
        lock.set_name(lock_config["name"])
    locks.append(lock)

lock = locks[0]  ##sketch AF....
lock._onStatusUpdate = onStatusUpdate

if(lock.connect()):
    client.publish("homeassistant/lock/L30DGX6/config", '{"name": "Front Door Lock", "state_topic": "august/lock/state", "availability_topic": "august/lock/availability", "unique_id": "L30DGX6", "command_topic": "august/lock/set"}', retain=True)
    client.publish("august/lock/availability", "online", retain=True)
    lock.getStatus()
    # client.publish("august/lock/state", lock.getStatus()) 
else:
    client.publish("august/lock/availability", "offline")

while(1):
    if(mqtt_event.wait(75)): #we got an mqtt event
        mqtt_event.clear()

        if(str(mqtt_message.payload.decode("utf-8")) == 'LOCK'):
            print("got lock mqtt message!")
            if(lock.is_connected()):
                if(lock.force_lock()):
                    pass
                else:
                    #client.publish("august/lock/availability", "offline", retain=True)
                    if(lock.connect()):
                        client.publish("august/lock/availability", "online", retain=True)
                        lock.force_lock()
                    else:
                        print("Couldn't reconnect & lock")
                        #client.publish("august/lock/availability", "offline", retain=True)
            else:
                client.publish("august/lock/availability", "offline", retain=True)
                if(lock.connect()):
                    client.publish("august/lock/availability", "online", retain=True)
                    lock.force_lock()

        elif(str(mqtt_message.payload.decode("utf-8")) == 'UNLOCK'):
            print("got unlock mqtt message!")
            if(lock.is_connected()):
                if(lock.force_unlock()):
                    pass
                else:
                    #client.publish("august/lock/availability", "offline", retain=True)
                    if(lock.connect()):
                        client.publish("august/lock/availability", "online", retain=True)
                        lock.force_unlock()
                    else:
                        print("Couldn't reconnect & unlock")
                        #client.publish("august/lock/availability", "offline", retain=True)
            else:
                client.publish("august/lock/availability", "offline", retain=True)
                if(lock.connect()):
                    client.publish("august/lock/availability", "online", retain=True)
                    lock.force_lock()

    else: #75 seconds expired
        if(i==0):
            i=1
            if(lock.is_connected()):
                if(lock.getStatus()):
                    client.publish("august/lock/availability", "online", retain=True)
                else:
                    if(lock.is_connected()):
                        lock.getStatus() # try again
                    if(not lock.is_connected()):
                        #client.publish("august/lock/availability", "offline", retain=True)
                        if(lock.connect()):
                            client.publish("august/lock/availability", "online", retain=True)
                        else:
                            print("Couldn't reconnect")
                            # client.publish("august/lock/availability", "offline", retain=True)
            else:
                #client.publish("august/lock/availability", "offline", retain=True)
                if(lock.connect()):
                    client.publish("august/lock/availability", "online", retain=True)
                else:
                    client.publish("august/lock/availability", "offline", retain=True)
        else:
            i=0
            if(lock.is_connected()):
                resp = lock.getVoltage()
                if(resp):
                    client.publish("august/lock/voltage", resp)
                    client.publish("august/lock/availability", "online", retain=True)
                else:
                    if(lock.is_connected()):
                        resp = lock.getVoltage() # try again
                        if(resp):
                            client.publish("august/lock/voltage", resp)
                            client.publish("august/lock/availability", "online", retain=True)

                    if(not lock.is_connected()):
                        #client.publish("august/lock/availability", "offline", retain=True)
                        if(lock.connect()):
                            client.publish("august/lock/availability", "online", retain=True)
                        else:
                            print("Couldn't reconnect")
                            # client.publish("august/lock/availability", "offline", retain=True)
            else:
                #client.publish("august/lock/availability", "offline", retain=True)
                if(lock.connect()):
                    client.publish("august/lock/availability", "online", retain=True)
                else:
                    client.publish("august/lock/availability", "offline", retain=True)
