#!/bin/python3

import augustpy.lock
import json
import time
import argparse

config = None

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

parser = argparse.ArgumentParser(description="Remotely control August locks.")
parser.add_argument('lock', metavar='L', type=str, nargs='+', help="The lock's name or address")
parser.add_argument('--lock', dest='action', action='store_const',
                   const='lock', help='Lock the lock')
parser.add_argument('--unlock', dest='action', action='store_const',
                   const='unlock', help='Lock the lock')
parser.add_argument('--status', dest='action', action='store_const',
                   const='status', help='Request lock status')
parser.set_defaults(action='status')

args = parser.parse_args()

for lock in locks:
    if lock.name in args.lock:
        #lock.connect()
        while(1):
            print ('cmd: ')
            var = str(input())
            if var == 'connect':
                print('connecting')
                lock.connect()
#                worked = False
#                while not worked:
#                    try:
#                        lock.connect()
#                    except:
#                        worked = False
#                        lock.disconnect()
#                        print("disconnected")
#                        try:
#                            lock.disconnect()
#                        except:
#                            print("disconnected")
#                    else:
#                        worked = True
            elif var == 'lock':
                lock.lock()
                print('locked')
            elif var == 'unlock':
                lock.unlock()
                print('unlocked')
            elif var == 'battery':
                print(lock.getBattery())
            elif var == 'voltage':
                print(lock.getVoltage())
            elif var == 'status':
                print(lock.getStatus())
            elif var == 's':
                print(lock.getStatus())
            elif var == 'getParam':
                print(lock.getParam(0x84))
            #elif var == 'setParam':
                #print(lock.setParam(0x84,0x60, 0xEA))
            #    print(lock.setParam(0x84,0xFF, 0xFF))
            elif var == 'disconnect':
                print('disconnecting')
                lock.disconnect()
            elif var == 'reset':
                print('resetting')
                lock.reset()
            elif var == 'led_G':
                print('green LED')
                lock.led_G()
            elif var == 'led_R':
                print('RED LED')
                lock.led_R()
            elif var == 'clear':
                print('clearing')
                lock.clear()
            elif var == 'wait_start':
                lock.wait_start()
            elif var == 'wait_stop':
                lock.wait_stop()
