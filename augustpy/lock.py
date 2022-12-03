import bluepy.btle as btle
import bluetooth._bluetooth as bluez
import bledist.blescan as blescan
import Cryptodome.Random
import threading
from . import session, util
import time

class keepLockAlive(threading.Thread):
	def __init__(self, thread_id, name, Lock, interval):
		threading.Thread.__init__(self)
		self.thread_id = thread_id
		self.name = name
		self.lock = Lock
		self._stop_event = threading.Event()
		self.interval = interval

	def run(self):
		print("Starting Lock Keep alive")
		while not self._stop_event.isSet(): #while exit flag is not set
			self._stop_event.wait(self.interval)
			if(not self._stop_event.isSet()):
				try:
					print("Sending keep alive") 
					self.lock.getStatus()
					#self.lock.led_G()
				except btle.BTLEDisconnectError:
					print("Lock keep alive failed. Reconnecting.")
					self.lock.connect()
		print("Lock keep alive exited")	
		#TODO: Add another event and defs setting and clearing the event to start/stop the lockalive

	def stop(self):
		self._stop_event.set()
		print("Exit flag sent to Lock keep alive")

class notificationProcessor_thread(threading.Thread):
    def __init__(self, lock):
        threading.Thread.__init__(self)
        self._stop_event = threading.Event()
        self.lock = lock
        self.session = lock.session
        self.daemon = True

    def run(self):
        try:
            while not self._stop_event.isSet(): #while exit flag is not set
                if(self.session.peripheral.waitForNotifications(1) and self._stop_event.isSet()==False):
                    print("HANDLE:::",self.session.delegate.cHandle)
                    temp = {} #dictionary
                    temp['cHandle'] = self.session.delegate.cHandle
                    temp['data'] = self.session.delegate.data
                    self.session.incomingData.append(temp)

                    # self.session.delegate.data = None
                    # self.session.delegate.cHandle = None

                    if((temp['data'][0] == 0xbb) and (temp['data'][1] == 0x02) and (temp['data'][4] == 0x02)): #incoming data is "status"
                        print("Status update received")
                        self.lock.status = temp['data'][8]
                        # self.lock.statusEvent.set()
                        strstatus = self.lock.parseStatus()
                        if (self.lock._onStatusUpdate != None):
                            self.lock._onStatusUpdate(strstatus)

                    if(self.session.delegate.cHandle != None):
                        print("data incoming!")
                        self.session.dataReady.set()
        except btle.BTLEDisconnectError:
            self.lock.conn_state = "disconnected"
            self.lock.is_secure = False
            self.lock.session = None
            self.lock.peripheral = None
            print("Device disconnected unexpectedly!")
            self.lock.connect()

        print("Exiting notification processor thread.")

    def stop(self):
        print("Sending exit flag to notification processor thread.")
        self._stop_event.set()


class Lock:
    COMMAND_SERVICE_UUID        = btle.UUID("0000fe24-0000-1000-8000-00805f9b34fb")
    WRITE_CHARACTERISTIC        = btle.UUID("bd4ac611-0b45-11e3-8ffd-0800200c9a66")
    READ_CHARACTERISTIC         = btle.UUID("bd4ac612-0b45-11e3-8ffd-0800200c9a66")
    SECURE_WRITE_CHARACTERISTIC = btle.UUID("bd4ac613-0b45-11e3-8ffd-0800200c9a66")
    SECURE_READ_CHARACTERISTIC  = btle.UUID("bd4ac614-0b45-11e3-8ffd-0800200c9a66")

    def __init__(self, address, keyString, keyIndex):
        self.address = address
        self.key = bytes.fromhex(keyString)
        self.key_index = keyIndex
        self.name = None
        self.notificationProcessor = None
        self.notificationProcessor_sec = None
        self.socket = bluez.hci_open_dev(0)

        self.peripheral = None
        self.session = None
        self.secure_session = None
        self.command_service = None
        self.is_secure = False
        self.conn_state = "disconnected"
        self.comm_state = "ready"
        self.status = 0
        self.statusEvent = threading.Event()
        self._onStatusUpdate = None

    def set_name(self, name):
        self.name = name

    def connect(self):
        success = False
        i=0        
        while(not success and i<5): #was 10 tries
            try:
                self.peripheral = btle.Peripheral(self.address)
                if self.name is None:
                    self.name = self.peripheral.addr

                self.session = session.Session(self,self.peripheral)
                self.secure_session = session.SecureSession(self, self.peripheral, self.key_index)
                #self.notificationProcessor = threading.Thread(target=notificationProcessor_thread, args=(1,self.session), daemon=True)
                #self.notificationProcessor_sec = threading.Thread(target=notificationProcessor_thread, args=(2,self.secure_session), daemon=True)

                self.command_service = self.peripheral.getServiceByUUID(self.COMMAND_SERVICE_UUID)

                characteristics = self.command_service.getCharacteristics()
                #descs = characteristic.getDescriptors()
                for characteristic in characteristics:
                    if characteristic.uuid == self.WRITE_CHARACTERISTIC:
                        self.session.set_write(characteristic)
                        #print("Handle: " + characteristic.handle)
                        #print("ValHandle: " + characteristic.getHandle())
                    elif characteristic.uuid == self.READ_CHARACTERISTIC:
                        self.session.set_read(characteristic)
                        #descs = characteristic.getDescriptors()
                        #for desc in descs:
                            #print("found  desc: " + str(desc.uuid))
                            #str_uuid = str(desc.uuid).lower()
                            #if str_uuid.startswith("00002902"):
                                #mcu_sub_handle = desc.handle
                                #mcu_sub_handle = 21
                                #print("*** Found MCU subscribe handle: " + str(mcu_sub_handle))
                    elif characteristic.uuid == self.SECURE_WRITE_CHARACTERISTIC:
                        self.secure_session.set_write(characteristic)
                        print("Set Secure Write")
                    elif characteristic.uuid == self.SECURE_READ_CHARACTERISTIC:
                        self.secure_session.set_read(characteristic)
                        print("Set Secure Read")
                        #descs = characteristic.getDescriptors()
                        #for desc in descs:
                            #print("found  desc: " + str(desc.uuid))
                            #str_uuid = str(desc.uuid).lower()
                            #if str_uuid.startswith("00002902"):
                                #sec_sub_handle = desc.handle
                                #sec_sub_handle = 26
                                #print("*** Found SEC subscribe handle: " + str(sub_handle))

                #start wait for notification thread here
                #self.notificationProcessor.start()
                #self.notificationProcessor_sec.start()

                response = self.peripheral.writeCharacteristic(26, b'\x02\x00', withResponse=True)
                print("Subscription SEC request response: ",response)

                response = self.peripheral.writeCharacteristic(21, b'\x02\x00', withResponse=True)
                print("Subscription MCU request response: ",response)

                #self.session.notificationProcessor.start()
                #self.secure_session.notificationProcessor.start()

                #descs = self.peripheral.getDescriptors()
                #for desc in descs:
                #    print("  desc: " + str(desc))
                #    str_uuid = str(desc.uuid).lower()
                    #if str_uuid.startswith("00002902"):
                    #    print("*** Found subscribe handle: " + str(subscribe_handle))

                self.secure_session.set_key(self.key)
                #print("hello")
                #print(self.session.read_characteristic.supportsRead())

                response = None
                ii=0
                while(response == None and ii<10):
                    handshake_keys = Cryptodome.Random.get_random_bytes(16)
                    ii+=1
                    # Send SEC_LOCK_TO_MOBILE_KEY_EXCHANGE
                    cmd = self.secure_session.build_command(0x01)
                    util._copy(cmd, handshake_keys[0x00:0x08], destLocation=0x04)
                    response = self.secure_session.execute(cmd)
                    print(response)
                    success = True
            except KeyboardInterrupt:
                quit()
            except btle.BTLEDisconnectError:
                print("Connection probably failed")
                success = False
                time.sleep(0.5)
            i+=1

        if(success):
            if response[0x00] != 0x02:
                raise Exception("Unexpected response to SEC_LOCK_TO_MOBILE_KEY_EXCHANGE: " +
                                response.hex())

            self.is_secure = True
            self.session.is_secure = True

            session_key = bytearray(16)
            util._copy(session_key, handshake_keys[0x00:0x08])
            util._copy(session_key, response[0x04:0x0c], destLocation=0x08)
            self.session.set_key(session_key)
            self.secure_session.set_key(session_key)

            # Send SEC_INITIALIZATION_COMMAND
            cmd = self.secure_session.build_command(0x03)
            util._copy(cmd, handshake_keys[0x08:0x10], destLocation=0x04)
            response = self.secure_session.execute(cmd)
            if response[0] != 0x04:
                raise Exception("Unexpected response to SEC_INITIALIZATION_COMMAND: " +
                                response.hex())

        if(success and self.is_secure):
            self.peripheral.writeCharacteristic(26, b'\x00\x00', withResponse=False) #disable notifications from SEC? don't care anymore...
            # print("Subscription SEC request response: ",response)
            self.session.dataReady.clear()
            #self.session.notificationProcessor = notificationProcessor_thread(self)
            #self.session.notificationProcessor.start()
            self.conn_state = "connected"
            self.keepAlive = keepLockAlive(33, "lock keep alive",self,60)
            # self.keepAlive.start()
            # blescan.hci_le_set_conn_parameters(self.socket, handle = 0x0040, min_interval = 0x0027, max_interval = 0x0028, latency = 0x000F, sup_timeout = 0x0136) # 420 ms timeout
            blescan.hci_le_set_conn_parameters(self.socket, handle = 0x0040, min_interval = 0x0027, max_interval = 0x0028, latency = 0x001E, sup_timeout = 0x01F4) #1000ms latency, 3000 ms timeout

            return True
        else:
            return False

    def force_lock(self):
        # blescan.hci_le_set_conn_parameters(self.socket, handle = 0x0040, min_interval = 0x0027, max_interval = 0x0028, latency = 0x0001, sup_timeout = 0x002A) # 420 ms timeout
        cmd = self.session.build_command(0x0b)
        # result = self.session.execute(cmd)

        try:
            response = self.session.execute(cmd)
        except btle.BTLEDisconnectError:
            print("Device disconnected unexpectedly!")
            self.is_secure = False
            self.session = None
            self.peripheral = None
            return False

        # blescan.hci_le_set_conn_parameters(self.socket, handle = 0x0040, min_interval = 0x0027, max_interval = 0x0028, latency = 0x000F, sup_timeout = 0x0136) # 420 ms timeout
        return response

    def force_unlock(self):
        # blescan.hci_le_set_conn_parameters(self.socket, handle = 0x0040, min_interval = 0x0027, max_interval = 0x0028, latency = 0x0001, sup_timeout = 0x002A) # 420 ms timeout
        cmd = self.session.build_command(0x0a)

        try:
            response = self.session.execute(cmd)
        except btle.BTLEDisconnectError:
            print("Device disconnected unexpectedly!")
            self.is_secure = False
            self.session = None
            self.peripheral = None
            return False

        # blescan.hci_le_set_conn_parameters(self.socket, handle = 0x0040, min_interval = 0x0027, max_interval = 0x0028, latency = 0x000F, sup_timeout = 0x0136) # 420 ms timeout
        return response


    def lock(self):
        if self.getStatus() == 'unlocked':
            return self.force_lock()

        return True

    def unlock(self):
        if self.getStatus() == 'locked':
            return self.force_unlock()

        return True

    def wait_start(self):
        self.session.notificationProcessor = notificationProcessor_thread(self)
        self.session.notificationProcessor.start()
    
        return True

    def wait_stop(self):
        self.session.notificationProcessor.stop()
        self.session.notificationProcessor.join()
        return True

    def setParam(self,param,val1,val2):
        cmd = bytearray(0x12)
        cmd[0x00] = 0xee
        cmd[0x01] = 0x03
        #cmd[0x03] = 0x0c #checksum?
        cmd[0x04] = param
        cmd[0x08] = val1
        cmd[0x09] = val2
        cmd[0x10] = 0x02

        response = self.session.execute(cmd)
        print(response.hex())

    def getParam(self,param):
        cmd = bytearray(0x12)
        cmd[0x00] = 0xee
        cmd[0x01] = 0x04
        #cmd[0x03] = 0x0c #checksum?
        cmd[0x04] = param
        cmd[0x10] = 0x02

        response = self.session.execute(cmd)
        print(response.hex())

    def getStatus(self):
        cmd = bytearray(0x12)
        cmd[0x00] = 0xee
        cmd[0x01] = 0x02
        #cmd[0x03] = 0x0c #checksum?
        cmd[0x04] = 0x02
        #cmd[0x10] = 0x02

        self.statusEvent.clear()
        try:
            response = self.session.execute(cmd)
        except btle.BTLEDisconnectError:
            print("Device disconnected unexpectedly!")
            self.is_secure = False
            self.session = None
            self.peripheral = None
            return False

        if(response != None):
            self.status = response[0x08]
            return self.parseStatus()
        else:
            print("Got NONE status :(")
            return False
        #if(not self.statusEvent.wait(5)):
        #    print("Notification Timed out")

        # strstatus = 'unknown'
        # if self.status == 0x02:
        #     strstatus = 'unlocking'
        # elif self.status == 0x03:
        #     strstatus = 'unlocked'
        # elif self.status == 0x04:
        #     strstatus = 'locking'
        # elif self.status == 0x05:
        #     strstatus = 'locked'

        # if strstatus == 'unknown':
        #     print("Unrecognized status code: " + hex(self.status))

        # return self.parseStatus()

    def parseStatus(self):
        strstatus = 'unknown'
        if self.status == 0x02:
            strstatus = 'unlocking'
        elif self.status == 0x03:
            strstatus = 'unlocked'
        elif self.status == 0x04:
            strstatus = 'locking'
        elif self.status == 0x05:
            strstatus = 'locked'

        if strstatus == 'unknown':
            print("Unrecognized status code: " + hex(self.status))

        return strstatus

    def getVoltage(self):
        cmd = bytearray(0x12)
        cmd[0x00] = 0xee
        cmd[0x01] = 0x02
        #cmd[0x03] = 0x0c #checksum?
        #cmd[0x04] = 0x05 #battery %
        cmd[0x04] = 0x0F #batteryVoltage
        #cmd[0x10] = 0x02

        # response = self.session.execute(cmd)


        try:
            response = self.session.execute(cmd)
        except btle.BTLEDisconnectError:
            print("Device disconnected unexpectedly!")
            self.is_secure = False
            self.session = None
            self.peripheral = None
            return False

        if(response != None):
            return (response[0x09] * 256) + response[0x08]            
        else:
            print("Got NONE status :(")
            return False


        # voltage = (response[0x09] * 256) + response[0x08]
        #bb0200690f000000b7140000000000000000
        #bb0200df050000005f000000000000000000
        # return voltage

    def getBattery(self):
        cmd = bytearray(0x12)
        cmd[0x00] = 0xee
        cmd[0x01] = 0x02
        #cmd[0x03] = 0x0c #checksum?
        cmd[0x04] = 0x05 #battery %
        #cmd[0x04] = 0x0F #batteryVoltage
        #cmd[0x10] = 0x02

        response = self.session.execute(cmd)
        battery = response[0x08]

        return battery

    def disconnect(self):
        self.keepAlive.stop()
        self.session.notificationProcessor.stop() #stop the notification processor thread
        self.session.notificationProcessor.join() #wait for notification processor thread to terminate

        if self.is_secure:
            cmd = self.secure_session.build_command(0x05)
            cmd[0x11] = 0x00
            self.secure_session.execute_nr(cmd)
            #print("disconnect response:",response)
            #if response[0] != 0x8b:
            #    raise Exception("Unexpected response to DISCONNECT: " +
            #                    response.hex())


        self.peripheral.disconnect() #should probably put this line in a try/except
        self.is_secure = False
        self.session = None
        self.peripheral = None
        print('Disconnected...')
        return True

    def led_G(self):
        cmd = self.session.build_command(14)
        cmd[4] = 0x01
        response = self.session.execute(cmd)

    def led_R(self):
        cmd = self.session.build_command(14)
        cmd[4] = 0x00
        response = self.session.execute(cmd)

    def is_connected(self):
        return type(self.session) is session.Session \
            and self.is_secure

        #return type(self.session) is session.Session \
        #    and self.peripheral.addr is not None
