
DEBUG = False
# BLE scanner based on https://github.com/adamf/BLE/blob/master/ble-scanner.py

# performs a simple device inquiry, and returns a list of ble advertizements 
# discovered device

# NOTE: Python's struct.pack() will add padding bytes unless you make the endianness explicit. Little endian
# should be used for BLE. Always start a struct.pack() format string with "<"

import os
import sys
import struct
import bluetooth._bluetooth as bluez

LE_META_EVENT = 0x3e
LE_PUBLIC_ADDRESS=0x00
LE_RANDOM_ADDRESS=0x01
LE_SET_SCAN_PARAMETERS_CP_SIZE=7
OGF_LE_CTL=0x08
OCF_LE_SET_SCAN_PARAMETERS=0x000B
OCF_LE_SET_SCAN_ENABLE=0x000C
OCF_LE_CREATE_CONN=0x000D
OCF_LE_CONN_UPDATE=0x0013
OCF_LE_CLEAR_WHITE_LIST=0x0010
OCF_LE_ADD_DEVICE_TO_WHITE_LIST=0x0011

LE_ROLE_MASTER = 0x00
LE_ROLE_SLAVE = 0x01

# these are actually subevents of LE_META_EVENT
EVT_LE_CONN_COMPLETE=0x01
EVT_LE_ADVERTISING_REPORT=0x02
EVT_LE_CONN_UPDATE_COMPLETE=0x03
EVT_LE_READ_REMOTE_USED_FEATURES_COMPLETE=0x04

# Advertisment event types
ADV_IND=0x00
ADV_DIRECT_IND=0x01
ADV_SCAN_IND=0x02
ADV_NONCONN_IND=0x03
ADV_SCAN_RSP=0x04

def returnnumberpacket(pkt):
	myInteger = 0
	multiple = 1
	
	for i in range(0, len(pkt)):
		myInteger +=  struct.unpack("B",pkt[i:i+1])[0] * multiple
		multiple = 1
		
	#for c in pkt:
	#	myInteger +=  struct.unpack("B",c)[0] * multiple
		#myInteger +=  struct.unpack("B",c:c+1)[0] * multiple
	#	multiple = 1
	return myInteger 

def returnstringpacket(pkt):
	#print(pkt)
	#print(type(pkt))
	myString = ""
	
	for i in range(0, len(pkt)):
		myString +=  "%02x" %struct.unpack("B",pkt[i:i+1])[0]
	#for c in pkt:
	#	print(type(c))
		#myString +=  "%02x" %struct.unpack("B",c)[0]
	#	myString +=  "%02x" %struct.unpack("B",c)[0]
	return myString 

def printpacket(pkt):
	for c in pkt:
		#sys.stdout.write("%02x " % struct.unpack("B",c)[0])
		sys.stdout.write("%02x " % struct.unpack("B",bytearray(c))[0])

def get_packed_bdaddr(bdaddr_string):
	packable_addr = []
	addr = bdaddr_string.split(':')
	addr.reverse()
	for b in addr: 
		packable_addr.append(int(b, 16))
	return struct.pack("<BBBBBB", *packable_addr)

def packed_bdaddr_to_string(bdaddr_packed):
	return ':'.join('%02x'%i for i in struct.unpack("<BBBBBB", bdaddr_packed[::-1]))

def hci_enable_le_scan(sock):
	hci_toggle_le_scan(sock, 0x01)

def hci_disable_le_scan(sock):
	hci_toggle_le_scan(sock, 0x00)

def hci_toggle_le_scan(sock, enable):
	cmd_pkt = struct.pack("<BB", enable, 0x00)
	bluez.hci_send_cmd(sock, OGF_LE_CTL, OCF_LE_SET_SCAN_ENABLE, cmd_pkt)

def hci_clear_whitelist(sock):
	bluez.hci_send_cmd(sock, OGF_LE_CTL, OCF_LE_CLEAR_WHITE_LIST)

def hci_add_whitelist(sock, bdaddr_type, bdaddr):
	cmd_pkt = struct.pack("<B6s", bdaddr_type, get_packed_bdaddr(bdaddr) )
	bluez.hci_send_cmd(sock, OGF_LE_CTL, OCF_LE_ADD_DEVICE_TO_WHITE_LIST,cmd_pkt)

def hci_le_set_scan_parameters(sock, scan_type, interval = 0x0040, window = 0x0030, addr_type = 0x00, filter = 0x00):
	#old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)
	
	#SCAN_TYPE = 0x01 for active scan
	#ADDR_TYPE = 0x00 for public address
	#window = 0x0030
	#interval = 0x0040
	
	cmd_pkt = struct.pack("<BHHBB", scan_type, interval, window, addr_type, filter )
	#cmd_pkt = struct.pack("<BHHBB", 0x01, interval, window, 0x00, 0x00 )
	#cmd_pkt = struct.pack("<BBBBBBB", SCAN_TYPE, 0x0, INTERVAL, 0x0, WINDOW, OWN_TYPE, FILTER)
	bluez.hci_send_cmd(sock, OGF_LE_CTL, OCF_LE_SET_SCAN_PARAMETERS, cmd_pkt)

def hci_le_set_conn_parameters(sock, handle = None, min_interval = 0x0024, max_interval = 0x0030, latency = 0x0014, sup_timeout = 0x012C, min_ce_length = 0x0000, max_ce_length = 0x0000):
	global conn_handle
	#conn_handle = 0
	#latency = 0x0016

	#Min connection interval: 30.00 msec (0x0018)
	#Max connection interval: 50.00 msec (0x0028)
	#Connection latency: 0 (0x0000)
	#Supervision timeout: 420 msec (0x002a)
	#Min connection length: 0.000 msec (0x0000)
	#Max connection length: 0.000 msec (0x0000)

	# cmd_pkt = struct.pack("<HHHHHHH", 0x0040, min_interval, max_interval, latency, sup_timeout, min_ce_length, max_ce_length)
	#cmd_pkt = struct.pack("<BHHBB", 0x01, interval, window, 0x00, 0x00 )
	#cmd_pkt = struct.pack("<BBBBBBB", SCAN_TYPE, 0x0, INTERVAL, 0x0, WINDOW, OWN_TYPE, FILTER)
	# bluez.hci_send_cmd(sock, OGF_LE_CTL, OCF_LE_CONN_UPDATE, cmd_pkt)

	# cmd_pkt = struct.pack("<HHHHHHH", 0x0000, min_interval, max_interval, latency, sup_timeout, min_ce_length, max_ce_length)
	if(handle == None):
		tmp_handle = conn_handle
	else:
		tmp_handle = handle

	cmd_pkt = struct.pack("<HHHHHHH", tmp_handle, min_interval, max_interval, latency, sup_timeout, min_ce_length, max_ce_length)
	bluez.hci_send_cmd(sock, OGF_LE_CTL, OCF_LE_CONN_UPDATE, cmd_pkt)

def parse_events(sock, loop_count=100):
	global conn_handle
	old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)
	# perform a device inquiry on bluetooth device #0
	# The inquiry should last 8 * 1.28 = 10.24 seconds
	# before the inquiry is performed, bluez should flush its cache of
	# previously discovered devices
	flt = bluez.hci_filter_new()
	bluez.hci_filter_all_events(flt)
	bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
	sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )
	# done = False
	# results = []
	myFullList = []
	for i in range(0, loop_count):
		pkt = sock.recv(255)
		ptype, event, plen = struct.unpack("BBB", pkt[:3])
		#print "--------------" 
		if event == bluez.EVT_INQUIRY_RESULT_WITH_RSSI:
			i =0
		elif event == bluez.EVT_NUM_COMP_PKTS:
			i =0 
		elif event == bluez.EVT_DISCONN_COMPLETE:
			i =0 
		elif event == LE_META_EVENT:
			
			#subevent, = struct.unpack("B", pkt[3])
			subevent, = struct.unpack("B", pkt[3:4])
			pkt = pkt[4:]
			if subevent == EVT_LE_CONN_COMPLETE:
				#le_handle_connection_complete(pkt)
				# event_params = dd.recv(3+bluez.EVT_CONN_COMPLETE_SIZE)[3:]
				# status, conn_handle, bd_addr, link_type, encrypt_enabled = struct.unpack('<BH6sBB', event_params)
				# print(pkt.hex())	
				# print(pkt[3:13].hex())				
				status, conn_handle, bd_addr, link_type, encrypt_enabled = struct.unpack('<BH6sBB', pkt[2:13])				
				print("Connection complete event!!! Conn handle:", conn_handle)
				print(pkt.hex())
				# print(pkt[3:13].hex())			
				#hci_disable_le_scan(sock)
				hci_le_set_scan_parameters(sock, scan_type = 0x01) #active scan
				hci_enable_le_scan(sock)
			elif subevent == EVT_LE_CONN_UPDATE_COMPLETE:
				print("Connection parameter update complete!")
				status, handle, interval, latency, sup_timeout = struct.unpack('<BHHHH', pkt)
				print(pkt.hex())
				print("Status:", status)
				print("Interval:", interval*1.25)
				print("Latency:", latency)
				print("Timeout:", sup_timeout*interval*1.25)
				# 000000280000003601
			elif subevent == EVT_LE_ADVERTISING_REPORT:
				#print "advertising report"
				#num_reports = struct.unpack("B", pkt[0])[0]
				#print(pkt[0])
				#print(pkt[0:1])
				num_reports = struct.unpack("B", pkt[0:1])[0]
				# report_pkt_offset = 0
				for i in range(0, num_reports):	
					local_dict = {} #dictionary
					
					address = packed_bdaddr_to_string(pkt[3:9]) #address
					local_dict['address'] = address
					
				
					
					evt_type = struct.unpack("b",pkt[1:2])[0] #adv event type
					#evt_type = returnnumberpacket(pkt[1:2]) #adv event type
					
					local_dict['evt_type']= evt_type
					
					
					data_length = struct.unpack("b",pkt[9:10])[0] #data length					
					#if((evt_type==2)):
					if(1):
						data_arr = pkt[10:10+data_length] #data array						
						
						ii = 0
						data = []
						
						try:
							while ii < data_length:
								pak_len = data_arr[ii]							
								
								#if(pak_len == 0):
								#	break
									
								pak_type = data_arr[ii+1]
								pak_data = data_arr[ii+2:(ii+pak_len+1)]
								data.append( (pak_len,pak_type,pak_data) )
								ii += pak_len + 1													
							# put error checking to avoid getting stuck in this while loop!
							local_dict['data']= data
						except:
							local_dict['data']= []
							
						#print(data)		
						
					rssi = 	struct.unpack("b", pkt[-1 : ])[0] #rssi
					#rssi = 	returnnumberpacket(pkt[-1 : ]) #rssi
					
					local_dict['rssi']= rssi
						

					#Adstring += ","
					#Adstring += "%i" % returnnumberpacket(pkt[report_pkt_offset -6: report_pkt_offset - 4]) 
					#Adstring += ","
					#Adstring += "%i" % returnnumberpacket(pkt[report_pkt_offset -4: report_pkt_offset - 2]) 
					#Adstring += ","
					#Adstring += "%i" % struct.unpack("b", pkt[report_pkt_offset -2 : report_pkt_offset -1])
					#Adstring += ","
					#Adstring += "%i" % struct.unpack("b", pkt[-1 : ]) #rssi


					#print("%i" % struct.unpack("b", pkt[report_pkt_offset -2 : report_pkt_offset -1]))
					#print((pkt[report_pkt_offset -1 : report_pkt_offset]))
					
					#try:
					#	Adstring += ","
					#	Adstring += "%i" % struct.unpack("b", pkt[-1 : ])
					#except: 1
					
					#Adstring += ","
					#print(pkt[report_pkt_offset -2 : report_pkt_offset-1])
					#Adstring += "%i" % struct.unpack("b", pkt[report_pkt_offset -1 : report_pkt_offset-0])
					myFullList.append(local_dict)
			#done = True
	sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )
	return myFullList
