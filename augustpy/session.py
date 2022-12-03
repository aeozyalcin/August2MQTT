import bluepy.btle as btle
import threading
from Cryptodome.Cipher import AES
from . import util


class SessionDelegate(btle.DefaultDelegate):
    def __init__(self, session):
        btle.DefaultDelegate.__init__(self)
        self.session = session
        self.data = None
        self.cHandle = None

    def handleNotification(self, cHandle, data):
        # if self.data is not None:
        #     return
        print("Notification/Indication received!!!")

        print("Receiving response: " + data.hex())
        print("Notification handle: " + str(cHandle))

        data = self.session.decrypt(data)
        print("Decrypted response: " + data.hex())        
        self.session._validate_response(data)
        self.data = data
        self.cHandle = cHandle

        # print("HANDLE:::",self.session.delegate.cHandle)
        # temp = {} #dictionary
        # temp['cHandle'] = self.session.delegate.cHandle
        # temp['data'] = self.session.delegate.data
        # self.session.incomingData.append(temp)
        # if(self.session.delegate.cHandle != None):
        #     print("data incoming!")
        #     self.session.dataReady.set()




class Session:
    cipher_encrypt = None
    cipher_decrypt = None

    def __init__(self, lock, peripheral):
        self.peripheral = peripheral
        self.delegate = SessionDelegate(self)
        self.incomingData = []
        self.dataReady = threading.Event()
        self.notificationProcessor = None
        self.is_secure = False
        self.lock = lock
        #self.notificationProcessor = threading.Thread(target=notificationProcessor_thread, args=(1,self), daemon=True)
        #self.peripheral.withDelegate(self.delegate)

    def set_notificationProcessor(self):
        #self.notificationProcessor = threading.Thread(target=notificationProcessor_thread, args=(1,self), daemon=True)
        self.notificationProcessor = notificationProcessor_thread(self)

    def set_write(self, write_characteristic):
        self.write_characteristic = write_characteristic

    def set_read(self, read_characteristic):
        self.read_characteristic = read_characteristic

    def set_key(self, key: bytes):
        self.cipher_encrypt = AES.new(key, AES.MODE_CBC, iv=bytes(0x10))
        self.cipher_decrypt = AES.new(key, AES.MODE_CBC, iv=bytes(0x10))

    def decrypt(self, data: bytearray):
        if self.cipher_decrypt is not None:
            cipherText = data[0x00:0x10]
            plainText = self.cipher_decrypt.decrypt(cipherText)
            if type(data) is not bytearray:
                data = bytearray(data)
            util._copy(data, plainText)

        return data

    def build_command(self, opcode: int):
        cmd = bytearray(0x12)
        cmd[0x00] = 0xee
        cmd[0x01] = opcode
        cmd[0x10] = 0x02
        return cmd

    def _write_checksum(self, command: bytearray):
        checksum = util._simple_checksum(command)
        command[0x03] = checksum

    def _validate_response(self, response: bytearray):
        print("Response simple checksum: " + str(util._simple_checksum(response)))
        if util._simple_checksum(response) != 0:
            #raise Exception("Simple checksum mismatch")
            print("Simple checksum mismatch")

        if response[0x00] != 0xbb and response[0x00] != 0xaa:
            #raise Exception("Incorrect flag in response")
            print("Incorrect flag in response")

    def _write(self, command: bytearray):
        print("Writing command: " + command.hex())

        # NOTE: The last two bytes are not encrypted
        # General idea seems to be that if the last byte
        # of the command indicates an offline key offset (is non-zero),
        # the command is "secure" and encrypted with the offline key
        if self.cipher_encrypt is not None:
            plainText = command[0x00:0x10]
            #cipherText = bytearray(0x12)
            #cipherText[0:0x10] = self.cipher_encrypt.encrypt(plainText)
            cipherText = self.cipher_encrypt.encrypt(plainText)
            #cipherText[0x11:0x12] = command[0x11:0x12]
            util._copy(command, cipherText)

        print("Encrypted command: " + command.hex())
        #print("Encrypted command: " + cipherText.hex())

        #delegate = SessionDelegate(self)    
        
        # self.notificationProcessor.stop()
        try:
            # self.session.notificationProcessor.stop()
            # self.session.notificationProcessor.join()
            self.lock.wait_stop()
        except:
            pass

        self.incomingData = []
        self.peripheral.withDelegate(self.delegate)
        self.dataReady.clear()
        self.write_characteristic.write(command, True)

        if(self.is_secure==False):
            if(self.delegate.data is None and self.peripheral.waitForNotifications(5) is False):
            #while(delegate.data is None and self.peripheral.waitForNotifications(2) is False):
                #raise Exception("Notification timed out")
                print("Notification timed out")
                #print(self.write_characteristic.supportsRead())
                #self.peripheral.withDelegate(delegate)
                #self.write_characteristic.write(command, True)
                return None
            else:        
                temp = self.delegate.data
                self.delegate.data = None
                #return self.delegate.data
                return temp    
                #return self.delegate.data
        else:
            # self.notificationProcessor = notificationProcessor_thread(self)
            # self.notificationProcessor.start()
            self.lock.wait_start()


        #self.write_characteristic.write(cipherText, True)

        #if self.delegate.data is None and self.peripheral.waitForNotifications(5) is False:
        
        #while(delegate.data is None and self.peripheral.waitForNotifications(2) is False):
            #raise Exception("Notification timed out")
           
            #print("Notification timed out")
           
            #print(self.write_characteristic.supportsRead())
            #self.peripheral.withDelegate(delegate)
            #self.write_characteristic.write(command, True)
            
            #return None
        if(False):    
        #if((command[0x00] == 0xee) and (command[0x01] == 0x02) and (command[0x04] == 0x02)): #requested status
            return True
        else:
            if(self.dataReady.wait(5)): #if there is data ready
                print("GOT NOTIFICATION EVENT!!!")
                self.dataReady.clear()
                print("incoming queue length:",len(self.incomingData))
                while self.incomingData: # TODO: needs some more work....
                    dataSet = self.incomingData.pop()  
                    #if(dataSet['cHandle']==20):
                    return dataSet['data']                
            else: #timed out
                print("Notification timed out")
                return None

        #while(self.delegate.data is None):
        #    True
        #else:
        #temp = self.delegate.data
        #self.delegate.data = None
        #return self.delegate.data
        #return temp

    def _write_nr(self, command: bytearray):
        print("Writing command: " + command.hex())

        # NOTE: The last two bytes are not encrypted
        # General idea seems to be that if the last byte
        # of the command indicates an offline key offset (is non-zero),
        # the command is "secure" and encrypted with the offline key

        if self.cipher_encrypt is not None:
            plainText = command[0x00:0x10]
            cipherText = self.cipher_encrypt.encrypt(plainText)
            util._copy(command, cipherText)

        print("Encrypted command: " + command.hex())

        delegate = SessionDelegate(self)

        self.peripheral.withDelegate(delegate)
        self.write_characteristic.write(command, False)
        #if delegate.data is None and \
        #        self.peripheral.waitForNotifications(10) is False:
        #    raise Exception("Notification timed out")

        #return delegate.data
        return 0

    def execute(self, command: bytearray):
        self._write_checksum(command)
        return self._write(command)

    def execute_nr(self, command: bytearray):
        self._write_checksum(command)
        self._write_nr(command)
        #return self._write_nr(command)

class SecureSession(Session):

    def __init__(self, lock, peripheral, key_index):
        super().__init__(lock, peripheral)
        self.key_index = key_index

    def set_key(self, key: bytes):
        self.cipher_encrypt = AES.new(key, AES.MODE_ECB)
        self.cipher_decrypt = AES.new(key, AES.MODE_ECB)

    def build_command(self, opcode: int):
        cmd = bytearray(0x12)
        cmd[0x00] = opcode
        cmd[0x10] = 0x0f
        cmd[0x11] = self.key_index
        return cmd

    def _write_checksum(self, command: bytearray):
        checksum = util._security_checksum(command)
        checksum_bytes = checksum.to_bytes(4, byteorder='little', signed=False)
        util._copy(command, checksum_bytes, destLocation=0x0c)

    def _validate_response(self, data: bytes):
        print("Response security checksum: " + str(util._security_checksum(data)))
        response_checksum = int.from_bytes(data[0x0c:0x10], byteorder='little', signed=False)
        print("Response message checksum: " + str(response_checksum))
        if util._security_checksum(data) != response_checksum:
            #raise Exception("Security checksum mismatch")
            print("Security checksum mismatch")
    
    def execute(self, command: bytearray):
        self._write_checksum(command)
        return self._write(command)

    def _write(self, command: bytearray):
        print("Writing command: " + command.hex())

        # NOTE: The last two bytes are not encrypted
        # General idea seems to be that if the last byte
        # of the command indicates an offline key offset (is non-zero),
        # the command is "secure" and encrypted with the offline key
        if self.cipher_encrypt is not None:
            plainText = command[0x00:0x10]
            cipherText = self.cipher_encrypt.encrypt(plainText)
            util._copy(command, cipherText)

        print("Encrypted command: " + command.hex())

        #delegate = SessionDelegate(self)    
        
        
        self.peripheral.withDelegate(self.delegate)
        self.write_characteristic.write(command, True)

        if(self.delegate.data is None and self.peripheral.waitForNotifications(5) is False):
        #while(delegate.data is None and self.peripheral.waitForNotifications(2) is False):
            #raise Exception("Notification timed out")
            print("Notification timed out")
            #print(self.write_characteristic.supportsRead())
            #self.peripheral.withDelegate(delegate)
            #self.write_characteristic.write(command, True)
            return None
        else:        
            temp = self.delegate.data
            self.delegate.data = None
            #return self.delegate.data
            return temp    
            #return self.delegate.data

        #while(self.delegate.data is None):
        #    True
        #else:
        #temp = self.delegate.data
        #self.delegate.data = None
        #return self.delegate.data
        #return temp
