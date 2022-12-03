# August2MQTT
Ditch the August WiFi bridge, turn your Raspberry Pi into an MQTT Bridge, and own your lock!

This repo utilizes a heavily modified version of [Friendly0Fire/augustpy](https://github.com/Friendly0Fire/augustpy) and a moderately modified version of [adamf/BLE](https://github.com/adamf/BLE). The whole point of this repo is to create a quick/lightweight MQTT bridge for August locks, without using the August WiFi bridge/August servers. I run this on a Raspberry Pi Zero W that's within 20-30 ft of my lock.

# Umm, you must not have heard. There is now a native BLE integration for August Locks. Why should I use your repo?
I heard that it sometimes takes up to [15 seconds](https://github.com/esphome/issues/issues/3761#issuecomment-1333079982) for the locks to respond when using the native BLE integration. The way the native integration works is it connects to the lock only after you have sent a command to lock/unlock. This adds a crap ton of latency. That means that every time you send a command, you have to wait for your host machine, or BLE proxies to scan for the lock, connect to the lock, go through the long authentication/handshake process, then finally send your command.

I wanted something much faster and elegant. And I think I achieved that. To achieve low latency and fast response, the magic sauce with this repo is that the host machine is always connected via BLE to the lock.

# Wait what? Always connected? Are you out of your mind?
Yeah probably. But hear me out. That version of the blescan.py I modified allows me to set the BLE connection interval. Connection Interval is a concept in BLE that allows you to stay connected to a peripheral, and define how often the peripheral needs to wake up to maintain the connection. I am setting the connection interval long enough (1 second at the moment), and this minimizes the battery impact. Whether you are connected to the lock or not, the lock is already waking up every 300ms to send and advertisement packet, so the active connection is just a drop in the bucket. In my testing, I am getting months of battery life out of my lock, just like before.

__The main benefit here is latency__. When you send the MQTT command to unlock, the lock usually responds within a second. And when you manually lock/unlock the door, again, an MQTT message appears instantly. The slowest part of this whole thing right now is the Home Assistant/MQTT layer - but still tons quicker than the native BLE integration for August Locks.

# So how do I start using this?
This code is *rough*. It works, but it ain't sexy. You will notice a crap ton of commented lines, and maybe even comments from me/previous devs. But once you get it up and running, you will like it! 

So here is how you start:
1. Clone the repo. And create yourself a config.json file with the info for youe lock. Follow the instructions [here](https://github.com/Friendly0Fire/augustpy#setup) on how to create your lock config file. 
2. run setup.sh, which will download the required python libraries.
3. Go into `mqtt_august_bridge.py` and enter your MQTT server details. [Start here](https://github.com/aeozyalcin/August2MQTT/blob/7c642023cf61f34ea4f855b16ca4c509ae64ce11/mqtt_august_bridge.py#L65). This will eventually go into `config.json` that you configured in step 1.
4. Just run `python3 mqtt_august_bridge.py`. You will probably need to run it as sudo, since the we need access to the BLE hardware on your host. 

Things to know:
- The bridge will listen for MQTT topic `august/lock/set` to wait for lock/unlock commands.
- The bridge will publish to MQTT topic `august/lock/state`, when the lock reports a state change.
- The bridge will publish to MQTT topic `august/lock/voltage`, when it gets a lock battery voltage update.
