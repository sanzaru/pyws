#
# Simple Python websocket server class
# This class is intended to be extended by another class.
# Just extend it and override the handleClient() function.
#
# Author: Martin Albrecht
# Verion: 0.0.1
#
import sys, socket, select, re, hashlib, base64
from socket import *


# Opcode types
OPTYPE_CONT = 0x00 # Continious package
OPTYPE_TEXT = 0x01 # Text package
OPTYPE_BIN  = 0x02 # Binary package
OPTYPE_CLOS = 0x08 # Close package
OPTYPE_PING = 0x09 # Ping package
OPTYPE_PONG = 0x0A # Pong package


#
# WebSocketServer class
class WebSocketServer(object):
	# Constructor
	def __init__(self, portno, debug=False):
		self.port = portno
		self.sock = socket(AF_INET, SOCK_STREAM)
		self.sock.bind(("", self.port))
		self.sock.listen(256)		
		self.s_in = [self.sock]
		self.s_out = []
		self.s_exc = []
		self.debug = debug
		
		
	# Do initial handshake
	def _handshake(self, sock):
		proto = False
		magic_key = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
		buf = sock.recv(1024)	
		if buf: 
			tmp = re.search('Sec-WebSocket-Key: ([^\n]+)', buf.decode("UTF-8"))
			key = tmp.group(1).strip()+magic_key				
			tmp = re.search('Sec-WebSocket-Protocol: ([^\n]+)', buf.decode("UTF-8"))
			if tmp: proto = tmp.group(1).strip()
			accept = base64.b64encode(hashlib.sha1(key.encode("UTF-8")).digest())
			del(tmp)						
					
			hs = "HTTP/1.1 101 Switching Protocols\r\n"
			hs += "Upgrade: websocket\r\n"
			hs += "Connection: Upgrade\r\n"
			hs += "Sec-WebSocket-Accept: "+accept.decode("UTF-8")+"\r\n"
			if proto: 
				hs += "Sec-WebSocket-Protocol: "+proto+"\r\n"
			hs += "\r\n"
			
			return sock.send(bytes(hs.encode("UTF-8")))	
		
		
	# Send a package to the client
	# @return: <int> The count of sent bytes. If 0 an error has occured.	
	def _send(self, sock, msg, typ=OPTYPE_TEXT):
		out = bytearray()
		
		# TODO Implement check for fin bit!
		if typ == OPTYPE_CLOS: out.append(0x88) # Close
		elif typ == OPTYPE_PING: out.append(0x89) # Ping
		elif typ == OPTYPE_PONG: out.append(0x8A) # Pong
		else: out.append(0x81) # Flags + opcode (fin, noextensions)		
									
		# TODO Implement extended length calculation
		if len(msg) <= 127: out.append(len(msg))		
		else: out.append(len(msg))
			
		for i in range(0, len(msg)):			
			out.append(ord(msg[i]))			
		
		if self.debug: print("Send: ",out)
						
		return sock.send(out)
		
		
	# Internal receive data function
	def _recv(self, sock):
		sock.settimeout(0.1)
		msg = ''		
		try:		
			msg = sock.recv(1024)			
			# Python2 fallback: Convert string to int list for bitwise operations
			if isinstance(msg, str):
				tmp = []
				for i in range(0, len(msg)):
					tmp.append(ord(msg[i]))
				msg = tmp		
				del(tmp)	
		except:
			pass
			
		return msg
	
	
	# Calculate payload length if extended
	def _extlen(self, msg):
		l = 0
		for i in range(len(msg)):
			if msg[i] != 0: 
				if l == 0:
					l = msg[i]
				else:
					l <<= 8
					l |= msg[i]
		return l
		
		
	# Read data from the client
	def _fetch(self, sock):
		msg = self._recv(sock)
		if msg:						
			fin = msg[0]>>7 & 1
			rsv = []
			for i in range(3):
				rsv.append(msg[0]>>(6-i) & 1)
			opcode = msg[0] & 15
			mask = msg[1]>>7 & 1
			pllen = msg[1] & 127
			
			# Check for close 
			if opcode == OPTYPE_CLOS:
				self._send(sock, '', OPTYPE_CLOS)				
			
			# Calculate payload length and set offset for masking key
			if pllen <= 125:
				moff = 0
				
			elif pllen == 126:
				pllen = self._extlen(msg[2:4])
				moff = 2
				
			if pllen == 127:
				pllen = self._extlen(msg[2:10])
				moff = 8
			
			# Fetch the masking key based on offset
			mkey = []
			for i in range(4):
				mkey.append(msg[2+i+moff])
	
			# TODO Implement extension data support
			pldata = []
			ploff = 6+moff
				
			for i in range(pllen):
				pldata.append(msg[ploff+i])
				
			# Respond to ping
			if opcode == OPTYPE_PING:
				self._send(sock, pldata, OPTYPE_PONG)
						
			# Flags debug output
			if self.debug:
				#print("Len:",len(msg),"bytes /",(len(msg)*8),"bit")
				#print("FIN: ", fin)
				#for i in range(len(rsv)):
				#	print("RSV[",i,"]: ", rsv[i])
				#print("OPCODE: ", opcode)
				#print("MASK: ", mask)
				#print("PL LEN: ", pllen)
				#for i in range(len(mkey)):
				#	print("MKEY[",i,"]: ", mkey[i])
				#for i in range(len(pldata)):
				#	print("PLDATA[",i,"]: ", pldata[i])			
				print("STR_DECR: ", self.crypt(pldata, mkey))
						
			return self.crypt(pldata, mkey)
		
		
	# Crypt / Decrypt a string with a given mask key	
	def crypt(self, msg, mask):		
		decr = ''
		for i in range(0, len(msg)):			
			decr += chr(msg[i] ^ mask[(i%4)])
		return decr

	# Accept new connection and return client object when handshake was successful
	def accept(self):
		(sread, swrite, sexc) = select.select(self.s_in, self.s_out, self.s_exc)
		for sock in sread:			
			# New client
			if sock == self.sock:
				(client, address) = self.sock.accept()									
				if self.debug: print("Client connected ("+address[0]+")!")
				self.s_in.append(client)
				print("Doing handshake...")
				if not self._handshake(client):
					print("ERROR: Handshake failed!")
					self._send(client, '', OPTYPE_CLOS) # close connection						
					client.close()
					self.s_in.remove(client)
				else:
					return client.fileno()
			else:
				self.handleClient(sock)

	# Handle client connection
	# Override this funtion in the parent class to make it useful
	def handleClient(self, sock):
		return
	