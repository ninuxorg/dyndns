#!/usr/bin/env python

from SocketServer import *
from xml.sax import *
import time
import os 
import socket
import sys
from threading import Lock
import logging

#first level domain
DOMAIN='ninux.org'
#the port on which the server will listen
PORT=8078
#configuration file
XMLFILE='/usr/local/dyndnsninux/dyndns.xml'
#nsupdate script - should take 2 parameters: ip and name 
NSUPDATESCRIPT='/bin/scriptaggiornaip4'
#after how many seconds allow connection from same IP address
CONNTIMEOUT=40
#logging settings
#logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s %(thread)d] %(levelname)s: %(message)s")
logging.getLogger().setLevel(logging.CRITICAL)
#user class
class User:
	name=""
	password=""
	comment=""
	hostnames=[]
	def __repr__(self):
		return"%s %s %s %s" % (self.name, self.password, self.comment, self.hostnames)
	
	def __str__(self):
		return self.__repr__()



#xml parser
class DynDnsParsingHandler(ContentHandler):
	isUserElement=False
	isNameElement=False
	isPasswordElement=False
	isCommentElement=False
	isHostnameElement=False
	
	def __init__(self,authmanager):
		self.authmanager=authmanager
		ContentHandler.__init__(self)
							
	def startElement(self,name,attrs):
		if name=="user":
			self.isUserElement=True
			self.newuser=User()
		if name=="name":
			self.isNameElement=True
		elif name=="password":
			self.isPasswordElement=True
		elif name=="comment":
			self.isCommentElement=True
		elif name=="hostname":
			self.hostname=""
			self.isHostnameElement=True
	
	def endElement(self, name):
		if name=="name":
			self.isNameElement=False
		if name=="password":
			self.isPasswordElement=False
		if name=="comment":
			self.isCommentElement=False
		if name=="hostname":
			self.newuser.hostnames.append(self.hostname)
			self.isHostnameElement=False
		if name=="user":
			self.isUserElement=False
			#set the global dictionaries
			self.authmanager._addUser(self.newuser)
						
	def characters (self,ch):
		if self.isNameElement:
			self.newuser.name+=ch
		elif self.isPasswordElement:
			self.newuser.password+=ch
		elif self.isCommentElement:
			self.newuser.comment+=ch
		elif self.isHostnameElement:
			self.hostname+=ch



#authorization manager
class AuthManager:
	"The AuthManager script parses the xml file and gives authorization"
	users={}
	xmlfile=""
	def __init__(self,xmlfile):
		self.xmlfile=xmlfile
		self.__updateEntries()
		
	def __updateEntries(self):
		parser=make_parser()
		curhandler=DynDnsParsingHandler(self)
		parser.setContentHandler(curhandler)
		try:
			parser.parse(open(self.xmlfile))
		except IOError:
			logging.critical("%s not found" % self.xmlfile)
			sys.exit(2)
		logging.debug(self.xmlfile+" parsed")
	
	def _addUser(self,userobject):
		assert(userobject.__class__==User)
		self.users.update({userobject.name:userobject})
		
	def isAuthorized(self,username,password,hostname):
		self.__updateEntries()
		try:
			loginok=(self.users[username].password==password and hostname in self.users[username].hostnames)
		except KeyError:
			loginok=False
		return loginok
	
	def getComment(self,username):
		self.__updateEntries()
		try:
			return users[username].comment
		except KeyError:
			return ""
 

#connection manager: to avoid concurrent connections from same IP address
class ConnManager:
	clients={}
	def __init__(self):
		self.clientslock=Lock()

	def isAllowed(self,ipaddress):
		self.clientslock.acquire()
		allowed=self.__isAllowed(ipaddress)
		self.clientslock.release()
		if not allowed:
			logging.warning("Repeated connection attempt from %s" % ipaddress)
		return allowed

	def __isAllowed(self,ipaddress):
		#unlocked function! Don't use!
		try:
			ts=self.clients[ipaddress]
		except KeyError:
			self.clients[ipaddress]=time.time()
			return True
		else:
			if (time.time()-ts) > CONNTIMEOUT:
				self.clients[ipaddress]=time.time()
				return True
			else:
				return False


#exceptions
class ConnectionException(Exception):
	pass

#Server handler		   
class LoginHandler (StreamRequestHandler):
	user=""
	passw=""
	host=""
	ip=""
	loadedrecords=False
	def outm(self,positive,message,critical=False):
		#send out a positive or negative message
		response=""
		if positive: 
			response="OK. "+message
		else:
			response="KO. "+message
		try:
			self.wfile.write(response+"\n")
		except:
			logging.error("Connection error client %s" % (self.ip,))
		else:
			if critical:
				logging.critical(response)
			else:
				logging.info(response)	
				
	def checklogin(self):			
		if am.isAuthorized(self.user,self.passw,self.host):
			self.outm(True,"Access Granted to user %s (%s)." % (self.user,self.ip))
			return True
		else:
			self.outm(False,"Access Denied to %s IP %s." % (self.user,self.ip),critical=True)
			return False

	def dyndnsdo(self):
		#do the dyndns stuff
		command = "%s %s %s" % (NSUPDATESCRIPT,self.ip,self.host)
		logging.debug("Executing %s" % command)
		if os.system(command)==0:
			self.outm(True, "DNS records updated: %s <-- %s.%s" % (self.ip,self.host,DOMAIN),critical=True)
		else:
			self.outm(False, "Error updating DNS records %s != %s.%s" % (self.ip,self.host,DOMAIN),critical=True)
	
	def handle(self):
		user=""
		passw=""
		host=""
		
		#get client IP address
		self.ip=self.client_address[0]
	
		if not cm.isAllowed(self.ip):
			self.outm(False,self.ip+" already connected or timeout not expired. Try again later")
			return
	
		self.outm(True,self.ip+" connected. Please supply your username.")
		
		#stateful protocol
		serverstatus=0
		while(serverstatus<4):
			cmd=self.rfile.readline().rstrip()
			if serverstatus==0:
				user=cmd
				pos=True
				msg="User "+user+". Please supply password"
				serverstatus=1
			elif serverstatus==1:
				passw=cmd
				pos=True
				msg="User "+user+". Password supplied. Please supply hostname"
				serverstatus=2
			elif serverstatus==2:
				host=cmd
				pos=True
				msg="Hostname "+host+" supplied"
				if ':static' in host:
					host=host.split(':')[0]
					msg += ". Request for static IP setting received, hostname corrected in "+host+". Please supply IP"
					serverstatus=3
				else:
					serverstatus=4
			elif serverstatus==3:
				ip=cmd
				pos=True
				msg="IP "+ip+" supplied"
				self.ip=ip
				serverstatus=4
			self.outm(pos, msg)
		
		#We should have an username, a password and a hostname
		self.user=user
		self.passw=passw
		self.host=host

		#check the login and do dyndns stuff
		if self.checklogin():
			self.dyndnsdo()
		

class ThreadingTCPServer(ThreadingMixIn,TCPServer): pass


if __name__=="__main__":

	am=AuthManager(XMLFILE)
	cm=ConnManager()
	
	try:
		logging.critical("Binding server to port %s" % PORT)
		dyndns=ThreadingTCPServer(('',PORT),LoginHandler)
	except socket.error, e:
		logging.error(e[1])
		logging.warning("Server Shutdown")
		sys.exit(1)
		
	try:
		logging.critical("Launching Server")
		dyndns.serve_forever()
	except KeyboardInterrupt:
		logging.critical("Server Shutdown")
