# -*- coding: utf-8 -*-
"""
Python twisted server, implements an HTTP socket-server and command queue to
execute python commands, parse XTSM, and manage data in user-specific contexts.  

Created on Thu May 16 18:24:40 2013
           
This software is described at
https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Python_server

TODO:
    permit standard command library calls with POST payloads on websocket
    connections (for faster exchanges on standard calls) ?
    is this done and working ?
    redirect stdio to console
    execute command queue items on schedule
    queue in databomb upkeep (links and storage)
    
@author: Nate, Jed
"""

import uuid
import time
import sys
import inspect
import pickle
import types
import collections
import subprocess
import io
import os
import platform #Access to underlying platform’s identifying data
from datetime import datetime
from datetime import date   
import pdb
import __main__ as main
import colorama
colorama.init(strip=False)
import textwrap
import pickle
#import roperdarknoise as rdn
import pstats

import msgpack
import msgpack_numpy
from autobahn.twisted.websocket import WebSocketServerProtocol
from autobahn.twisted.websocket import WebSocketServerFactory
from autobahn.twisted.websocket import WebSocketClientFactory
from autobahn.twisted.websocket import WebSocketClientProtocol
from autobahn.twisted.websocket import connectWS
from autobahn.twisted.websocket import listenWS
from twisted.internet import wxreactor
from twisted.internet import defer
from twisted.internet.protocol import DatagramProtocol
wxreactor.install()
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.internet import task
from lxml import etree
from BaseHTTPServer import BaseHTTPRequestHandler
from StringIO import StringIO
import wx
import wx.html
from enthought.traits.api import HasTraits
from enthought.traits.api import Int as TraitedInt
from enthought.traits.api import Str as TraitedStr

from twisted.internet import stdio
from twisted.protocols import basic
from twisted.internet import error

import simplejson
import socket
import XTSMobjectify
import DataBomb
import InfiniteFileStream
msgpack_numpy.patch()#This patch actually changes the behavior of "msgpack"
#specifically, it changes how, "encoding='utf-8'" functions when unpacking
import XTSM_Server_Objects
import XTSM_Transforms
import live_content
import xstatus_ready
import file_locations
import server_initializations       
import glab_instrument
import script_server

import matplotlib as mpl
import matplotlib.pyplot as plt 
import hdf5_liveheap
import gc
#import objgraph
import numpy as np
import scipy
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import image_viewer
#from IPy import IP

def tracefunc(frame, event, arg, indent=[0]):
      global DEBUG_LINENO, TRACE_IGNORE
      try: 
          filename = frame.f_globals["__file__"]
          if filename.count("C:\\wamp\\vortex\\WebSocketServer\\DataBomb")==0:
              return tracefunc
      except: return
      for ti in TRACE_IGNORE: 
          if frame.f_code.co_name==ti: return
      DEBUG_LINENO+=1
      if event == "call":
          indent[0] += 2
          print "-" * indent[0] + "> call function", \
          frame.f_code.co_name, str(DEBUG_LINENO)
      elif event == "return":
          print "<" + "-" * indent[0], "exit function", frame.f_code.co_name
          indent[0] -= 2
      return tracefunc

DEBUG_LINENO = 0      
DEBUG_TRACE = False
TRACE_IGNORE=["popexecute","getChildNodes","getItemByFieldValue"]
MAX_SCRIPT_SERVERS = 2
      
if DEBUG_TRACE: sys.settrace(tracefunc)
DEBUG = True

try:
    port = int(sys.argv[1])
    wsport = int(sys.argv[2])
    udpbport = int(sys.argv[2])
except IndexError:
    port = 8083
    wsport = 8084
    udpbport = 8085

NUM_RETAINED_XTSM=10

class Experiment_Sync_Group(HasTraits):
    """
    A class to hold experiment sychronization data - this is the core
    organizational element, holding the current shotnumber, the active_xtsm
    generator, and the last several compiled xtsm objects ()
    """
    active_xtsm = TraitedStr('<XTSM></XTSM>')
    last_successful_xtsm = TraitedStr('<XTSM></XTSM>')
    shotnumber = TraitedInt(0)
    # note: last element is compiled_xtsm, defined by class below
    def __init__(self,server):
        self.server=server
    def _active_xtsm_changed(self, old, new): 
        self.server.broadcast('{"active_xtsm_post":"'+str(new)+'"}')
    def _shotnumber_changed(self, old, new): 
        self.server.broadcast('{"shotnumber":"'+str(new)+'"}')
    def __flush__(self):
        lsx=open(file_locations.file_locations['last_xtsm'][uuid.getnode()]+"last_xtsm.xtsm","w")
        lsx.write(self.last_successful_xtsm)
        lsx.close()
        self.compiled_xtsm.flush()
        self.compiled_xtsm.filestream.__flush__() 
    def __getstate__(self):
        print 'here'               

    class XTSM_stack(collections.OrderedDict):
        """
        A class to hold a stack of compiled XTSM objects and manage their
        storage and retrieval - for simplicity we subclass the orderedDict class
        in collections.  This is extended with an infinite filestream, into which
        the oldest xtsm objects are serialized for storage in this messagepack 
        format as shotnumber:xtsm entries.
        """
        filestream = InfiniteFileStream.FileStream({"file_root_selector":"xtsm_feed"})
        packer = msgpack.Packer()
        def __init__(self):
            collections.OrderedDict.__init__(self)
            self.archived={}
            self.timeadded={}
        def __del__(self):
            self.flush()
        def __getstate__(self):
            print 'andhere'
            
        def update(self,*args,**kwds):
            """
            inserts another element - should be shotnumber:xtsm pair 
            """
            collections.OrderedDict.update(self,*args,**kwds)
            for elm in args:
                self.archived.update({elm.keys()[0]:False})       
            for elm in args:
                self.timeadded.update({elm.keys()[0]:time.time()})
            while len(self)>NUM_RETAINED_XTSM:
                self.heave()
            #pdb.set_trace()                
            
        def archive(self):
            """
            checks if any elements are currently archivable, and archives them
            if any have not yet been archived, and are active
            but exceed the archive_timeout, they are forced deactive and archived.  
            
            """
            #pdb.set_trace() #Check to see if "self has elm" in it.
            for elm in self:
                if not self[elm].isActive(): 
                    self._archive_elm(elm)
                    continue
                if (time.time()-self.timeadded[elm]) > self.archive_timeout:
                    self._archive_elm(elm)
                    self[elm].deactivate(params={"message":"This element was deactivated when timed out from XTSM_Stack"})
                    continue        
                
        def _archive_elm(self,elm):
            """
            stores an element to disk in the infinite filestream - does not check
            if element is active - that is duty of caller
            """
            if type(elm)==type(0):
                elm=(elm,self[elm])
            self._write_out(elm)
            self.archived[elm[0]] = True  
            
        def _write_out(self,elm):
            """
            stores an element to disk in the infinite filestream 
            """
            self.filestream.write(self.packer.pack({elm[0]:elm[1].XTSM.write_xml()}))
            
        def heave(self):
            """
            removes the oldest element from the stack (FIFO-style), archiving
            it if it has not already been - in this case, the element is removed
            even if it has active listeners; they are removed too, to avoid memory leaks.
            """
            heavethis = self.popitem(last=False)
            if heavethis[1].isActive():
                heavethis[1].deactivate(params={"message":"This element was deactivated when heaved from XTSM_Stack"})
            if not self.archived[heavethis[0]]:
                self._write_out(heavethis)
                
        def flush(self):
            """
            heaves all elements from stack, saving to disk if necessary
            """
            while len(self)>0:
                self.heave()
                                
    compiled_xtsm = XTSM_stack()
    
class MulticastProtocol(DatagramProtocol):
    """
    Protocol to handle UDP multi-receiver broadcasts - used for servers
    to announce their presence to one another through periodic pings
    """
    resident=True
    def startProtocol(self):
        """
        Join the multicast address
        """
        interface_ = ""
        if socket.gethostbyname(socket.gethostname()) == '10.1.1.124':
            interface_ = '10.1.1.124'
        self.transport.joinGroup("228.0.0.5", interface=interface_)

    def send(self,message):
        """
        sends message on udp broadcast channel
        """
        self.transport.write(message, ("228.0.0.5", udpbport))

    def datagramReceived(self, datagram_, address):
        """
        called when a udp broadcast is received
        """
        #print "Datagram received from "+ repr(address) 
        datagram = simplejson.loads(datagram_)
        if hasattr(datagram,'keys'):
            if 'shotnumber_started' in datagram.keys():
                print datagram
                #dc.get('_exp_sync').shotnumber = datagram['shotnumber_started']
                self.server.pxi_time = float(datagram['time'])
                self.server.pxi_time_server_time = float(datagram['time']) - float(time.time())#Make this so that it synchronizes the clocks CP
                self.server.active_parser_ip = datagram['server_ip_in_charge']#Make this so that it synchronizes the clocks CP
                self.server.active_parser_port = datagram['server_port_in_charge']#Make this so that it synchronizes the clocks CP
                #dc = self.server.dataContexts['PXI']
                #if not dc.dict.has_key('_exp_sync'):
                #     exp_sync = Experiment_Sync_Group(self.server)
                #     dc.update({'_exp_sync':exp_sync})
                #dc['_exp_sync'].shotnumber = int(datagram['shotnumber_started'])
                #print "Shot started:", datagram['shotnumber_started'], "pxi_time:", self.server.pxi_time, "time.time():", float(time.time())
                return
        try:
            datagram["server_ping"] 
        except KeyError:
            print "unknown UDP message:\n", datagram
        ping_command = ServerCommand(self.server.catch_ping, datagram)
        self.server.command_queue.add(ping_command)
    
class HTTPRequest(BaseHTTPRequestHandler):
    """
    A class to handle HTTP request interpretation
    """
    def __init__(self, request_text):
        self.rfile = StringIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()
    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message

        
class WSClientProtocol(WebSocketClientProtocol):

    def onConnect(self, response):
        print("Server connected. Message as Client Protocol. : {0}".format(response.peer))
        self.in_use = True
        self.id = uuid.uuid4()
        self.time_of_creation = time.time()
        self.connection = self.factory.connection
        self.connection.protocol = self
        self.server = self.factory.connection_manager.server
        self.connection_manager = self.factory.connection_manager

    def onOpen(self):
        #print("WebSocket connection opened as client.")
        self.connection.ip = self.transport.getPeer().host
        self.connection.port = self.transport.getPeer().port
        self.connection.connection_manager.connectLog(self)
        self.connection.on_open()

    def onMessage(self, payload, isBinary):
        #print "class WSClientProtocol, func onMessage"
        #print payload
        self.log_message()
        self.connection.last_message_time = time.time()
        msg_command = ServerCommand(self.connection.on_message, payload, isBinary, self)
        self.server.command_queue.add(msg_command)
        


    def log_message(self):
        headerItemsforCommand=['host','origin']
        self.request = {k: self.http_headers[k] for k in headerItemsforCommand if k in self.http_headers}
        self.ctime = time.time()        
        self.request.update({'ctime':self.ctime,'protocol':self})
        self.request.update({'timereceived':time.time()})
        self.request.update({'write':self.sendMessage})
        # record where this request is coming from
        self.factory.connection_manager.elaborateLog(self,self.request)

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed as Client: {0}".format(reason))
        self.connection.on_close()
                          
        

class WSServerProtocol(WebSocketServerProtocol):
    """
    This is the websocket protocol - it defines the server's response to
    bidirectional open-port websocket communications.  This is useful for
    on-demand server-push and low-connection-overhead comm.
    
    added by NDG on 3-25-14, most methods not yet finished
    """
    resident=True
    bidirectional=True
    def onConnect(self, request):
        pass
        print("Client connecting. Message as Server Protocol. : {0}".format(request.peer))
        self.in_use = True
        self.id = uuid.uuid4()
        self.time_of_creation = time.time()
        self.server = self.factory.connection_manager.server
        self.connection_manager = self.factory.connection_manager

    def onOpen(self):
        pass
        #print("WebSocket connection open as server.")
        
        new_peer = PeerServer()
        new_peer.is_open_connection = True
        new_peer.server = self.factory.server
        new_peer.connection_manager = self.factory.connection_manager
        new_peer.protocol = self
        new_peer.port = self.transport.getPeer().port
        new_peer.ip = self.transport.getPeer().host
        self.connection = new_peer
        self.connection.protocol = self
        self.connection_manager.connectLog(self) 
        self.connection.last_message_time = time.time()
        self.connection.on_open()
   

        #peer = self.transport.getPeer()
        #self.factory.isConnectionOpen = True
        #self.connection_manager.add_peer_server_as_server(peer)
        #try:
        #    self.factory.openConnections.update({self.ConnectionUID:self})
       # except AttributeError: 
        #    self.factory.openConnections = {self.ConnectionUID:self}
        
        #Moved to add_peer_server in class Client Manager/PeerServer
        #self.ctime = time.time()
        #peer = self.transport.getPeer()
        #self.peer ='%s:%s' % (p.host,p.port)
        #self.ConnectionUID = uuid.uuid1().__str__()
        #self.clientManager.add_peer_server(peer)
        #pdb.set_trace()
        #try:
        #    self.factory.openConnections.update({self.ConnectionUID:self})
        #except AttributeError: 
        #    self.factory.openConnections = {self.ConnectionUID:self}
        #self.clientManager.connectLog(self)

    def failHandshake(self,code=1001,reason='Going Away'):
        pass        
            
    def onMessage(self, payload, isBinary):
        #print "On message"
        #print payload
        self.connection.last_connection_time = time.time()
        self.log_message()
        self.connection.last_message_time = time.time()
        msg_command = ServerCommand(self.connection.on_message, payload, isBinary, self)
        self.server.command_queue.add(msg_command)

    def log_message(self):
        headerItemsforCommand=['host','origin']
        self.request = {k: self.http_headers[k] for k in headerItemsforCommand if k in self.http_headers}
        self.ctime = time.time()        
        self.request.update({'ctime':self.ctime,'protocol':self})
        self.request.update({'timereceived':time.time()})
        self.request.update({'write':self.sendMessage})
        # record where this request is coming from
        self.factory.connection_manager.elaborateLog(self,self.request)

    #Moved to function in GlabClient
    """
    def onBinaryMessage(self,payload_):
        payload = msgpack.unpackb(payload_)
        print "---------Data Below!-------------"
        print payload

    #def giveit(self):
    #    self.sendMessage("adsdasd")

    def onTextMessage(self,payload):
        print "------------"
        print payload
        # we will treat incoming websocket text using the same commandlibrary as HTTP        
        # but expect incoming messages to be JSON data key-value pairs
        try:
            data = simplejson.loads(payload)
        except simplejson.JSONDecodeError:
            self.transport.write("The server is expecting JSON, not simple text")
            print "The server is expecting JSON, not simple text"
            self.transport.loseConnection()
            return False
        # if someone on this network has broadcast a shotnumber change, update the shotnumber in
        # the server's data contexts under _running_shotnumber
        #pdb.set_trace()        
        if hasattr(data, "shotnumber"):
            pdb.set_trace() # need to test the below
            #for dc in self.parent.dataContexts:
                #dc['_running_shotnumber']=data['shotnumber']
        data.update({'request':self.request})
        data.update({'socket_type':"Websocket"})
        SC=SocketCommand(params=data, request=self.request, CommandLibrary=self.server.commandLibrary)
        try:
            #self.commandQueue.add(SC)
            self.server.commandQueue.add(SC)
        #except AttributeError:
        #    self.commandQueue=CommandQueue(SC)
        except:
            self.sendMessage("{'server_console':'Failed to insert SocketCommand in Queue, reason unknown'}")
    """    
    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed as Server: {0}".format(reason))
        self.connection.on_close()
        #self.transport.loseConnection()
        #del self.server
        #Does this work?? 


            
        
#class EchoProtocol(protocol.Protocol):
#    """
#    A simple example protocol to echo requests back on HTTP
#    """
#    def connectionMade(self):
#        p=self.transport.getPeer()
#        self.peer ='%s:%s' % (p.host,p.port)
#        print  datetime.now(), ":Connected from", self.peer
#    def dataReceived(self,data):
#        print data
#        self.transport.write('You Sent:\n')
#        self.transport.write(data)
#        self.transport.loseConnection()
#    def connectionLost(self,reason):
#        print datetime.now() , ":Disconnected from %s: %s" % (self.peer,reason.value)
             
        
class CommandProtocol(protocol.Protocol):
    """
    This is the protocol to handle incoming socket commands; it is here to
    listen on a socket, and insert command requests into a command queue - if 
    the request is valid, it will eventually be executed by the queue 
    """
    resident=False
    bidirectional=False
    def connectionMade(self):
        self.ctime = time.time()
        p = self.transport.getPeer()
        self.peer ='%s:%s' % (p.host,p.port)
        self.ConnectionUID = uuid.uuid1().__str__()
        try:
            self.factory.openConnections.update({self.ConnectionUID:self})
        except AttributeError:
            self.factory.openConnections={self.ConnectionUID:self}
        #print datetime.now(), "Connected from", self.peer, "at"
        self.factory.connection_manager.connectLog(self)
        self.server = self.factory.connection_manager.server
        self.alldata = ''
    
    def provide_console(self):
        """
        default face of server when contacted with a get request
        """
        #self.transport.write("this is a running XTSM server\n\r\n\r")
        #pdb.set_trace()
        """
        This may crash a websocket server if sent to port 8085 because it's not json
        """
        self.transport.write("<XML>"+self.factory.parent.xstatus()+"</XML>")
        self.transport.loseConnection()
    
    def dataReceived(self,data):
        """
        Algorithm called each time a data fragment (packet typ <1300 bytes) is taken in on socket
        If last packet in message, records the requested command in the queue
        """
        # on receipt of the first fragment determine message length, extract header info
        # NOTE: this can only handle header lengths smaller than the fragment size - 
        # the header MUST arrive in the first fragment
        # append the new data 
        self.alldata += data
        if u"?console" in data: self.provide_console()
        #requests = 0   #For use with priorities
        if not hasattr(self,'mlength'):
            # attempt to extract the header info with the current message subset
            try:            
                self.dataHTTP = HTTPRequest(self.alldata)
                self.boundary = self.dataHTTP.headers['content-type'].split('boundary=')[-1]
                fb = data.find('--' + self.boundary) # find the first used boundary string
                if fb == -1:
                    return # if there is none, the header must not be complete
                # if there is a boundary, header must be complete; get header data
                self.mlength = fb + int(self.dataHTTP.headers.dict['content-length'])
                headerItemsforCommand = ['host','origin','referer']
                self.request = {k: self.dataHTTP.headers[k] for k in headerItemsforCommand if k in self.dataHTTP.headers}
                self.request.update({'ctime':self.ctime,'protocol':self})
                # record where this request is coming from
                self.factory.connection_manager.elaborateLog(self,self.request)
            except: return  # if unsuccessful, wait for next packet and try again
        
        # if we made it to here, the header has been received
        # if the entirety of message not yet received, append this fragment and continue
        if self.mlength > len(self.alldata):
            return
        # if we have made it here, this is last fragment of message       
        # mark the 'all data received' time
        self.request.update({'timereceived':time.time()})
        # strip multipart data from incoming HTTP request
        kv = [datas.split('name="')[-1].split('"\n\r\n\r') for datas in self.alldata.split('--'+self.boundary+'--')]
        self.params = {k:v.rstrip() for k,v in kv[:-1]}
        # insert request, if valid, into command queue (persistently resides in self.Factory)        
        SC=SocketCommand(self.params,self.request)
        try:
            self.factory.connection_manager.server.command_queue.add(SC)
            #self.factory.commandQueue.add(SC)
        except AttributeError:
            print 'Failed to insert SocketCommand in Queue, No Queue'
            raise
            #self.factory.commandQueue=CommandQueue(SC)
        except:
            msg = {'Not_Command_text_message':'Failed to insert SocketCommand in Queue, reason unknown','terminator':'die'}
            self.transport.write(simplejson.dumps(msg, ensure_ascii = False).encode('utf8'))
            print 'Failed to insert SocketCommand in Queue, reason unknown'
            self.transport.loseConnection()
            raise
    # close the connection - should be closed by the command execution
    # self.transport.loseConnection()
    def connectionLost(self,reason):      
        try:
            del self.factory.openConnections[self.ConnectionUID]
        except KeyError:
            pass
        #print datetime.now(), "Disconnected from %s: %s" % (self.peer,reason.value)

class DataContext(XTSM_Server_Objects.XTSM_Server_Object):
    """
    A dataContext object stores variable definitions for a Python session
    in a sheltered scope, roughly one for each user, such that independent
    data analysis and experiment control sessions can be run without interferences
    
    .dict contains dictionary of variables and values
    """
    def __init__(self, name, server):
        #print "class DataContext, function __init__", 'name:', name
        self.dict = {"__context__":name}
        self.name = name
        self.server = server
        #Create DataBombList
        d = DataBomb.DataBombList(params={"server":self.server})
        self.dict.update({'_bombstack':d})
        #Create DataBombDispatcher
        d = DataBomb.DataBombDispatcher(params={"server":self.server}) 
        self.dict.update({'databomb_dispatcher':d})       
        #Create DataListenerManager
        d = DataBomb.DataListenerManager()
        self.dict.update({'data_listener_manager':d}) 

    def _close(self):
        pass
 
    def update(self,data):
        """
        updates a variable or variables according to a dictionary of new values
        """
        self.dict.update(data)
    def get(self,variablename):
        return self.dict[variablename]
    def __getitem__(self,vname):
        return self.get(vname)
    def xstatus(self):
        stat = '<DataContext><Name>' + self.name + '</Name>'
        for var in self.dict:
            try:
                stat +='<Variable>'
                stat += '<Name>'
                stat += var
                stat += '</Name>'
                stat += '<Type>'
                stat += '<![CDATA['
                stat += str(type(self.dict[var]))
                stat += ']]></Type>'
                stat += '<Value>'
                stat += '<![CDATA['
                stat += str(self.dict[var])[0:25]
                stat += ']]>'
                stat += '</Value>'
                stat += '</Variable>'
            except:
                stat += '<Unknown></Unknown>'
        stat += '</DataContext>'
        return stat
    def __flush__(self):
        for item in self.dict:
            try:
                self.dict[item].__flush__()
                self.dict[item].flush()
            except AttributeError:
                pass
        XTSM_Server_Objects.XTSM_Server_Object.__flush__(self)
        
class ConnectionManager(XTSM_Server_Objects.XTSM_Server_Object):
    """
    The client manager retains a list of recent clients, their IP addresses,
    and can later be used for permissioning, etc...
    """
    def __init__(self, server):
        self.server = server
        self.id = uuid.uuid4()
        self.maintenance_period = 5
        self.peer_servers = {}
        self.script_servers = {}
        self.TCP_connections = {}
        self.image_viewer_servers = {}
        
        maintenance_command = ServerCommand(self.periodic_maintainence)
        self.server.reactor.callLater(self.maintenance_period,
                                      self.server.command_queue.add,
                                      maintenance_command)
        # setup the websocket server services

        #self.wsfactory.protocol.commandQueue = self.commandQueue
        #self.wsfactory.protocol.clientManager = self.clientManager
        # listen on standard TCP port
        #self.laud = self.server.reactor.listenTCP(port, self.wsServerFactory)
        
        

        address = "ws://localhost:" + str(wsport)
        self.wsServerFactory = WebSocketServerFactory(address, debug=True)
        self.wsServerFactory.setProtocolOptions(failByDrop=False)
        #self.wsServerFactory.parent = self
        self.wsServerFactory.protocol = WSServerProtocol
        self.wsServerFactory.connection_manager = self
        self.wsServerFactory.server = self.server
        listenWS(self.wsServerFactory)
        
    def is_connections_closed(self):
        print "Checking connections"
        #pdb.set_trace()
        for key in self.peer_servers.keys():
            if self.peer_servers[key].protocol.state != self.peer_servers[key].protocol.STATE_CLOSED:
                return False
        for key in self.script_servers.keys():
            if self.script_servers[key].protocol.state != self.script_servers[key].protocol.STATE_CLOSED:
                return False
        return True    

       
    def identify_client(self,protocol):
        """
        attempts to identify a client by the connection protocol 
        
        resident protocols are identified by the ip:port string
        non-resident (ephemoral) protocols are identified by ip address and
        header info
        """
        if protocol.resident:
            return protocol.peer
        #pdb.set_trace()
        
    def connectLog(self,protocol):
        return # temporary disable
        #pdb.set_trace()
        pid = self.identify_client(protocol)
        try:
            self.clients[pid].connectLog()
        except KeyError:
            self.clients.update({pid:self.client(params={"protocol":protocol})})

    def elaborateLog(self,protocol,request):
        return # temporary disable
        pid = self.identify_client(protocol)
        try:
            self.clients[pid].elaborateLog()
        except KeyError:
            self.clients.update({pid:self.client(params={"protocol":protocol})})
        
    def update_client_roles(self,request,role):
        """
        keeps list of clients by 'role' the role is ascribed by the caller
        
        if peer is a request object, the ip:port will be determined, and if 
        request is an emphemeral TCP port, will ...
        
        """
        return
        #pdb.set_trace() #commend out by JZ on 10/3/14
        if not self.client_roles.has_key(request['protocol'].peer):
            self.client_roles.update({request['protocol'].peer:{role:time.time()}})
        else:
            self.client_roles[request['protocol'].peer].update({role:time.time()})
    role_timeouts={}
    def periodic_maintainence(self):
        """
        performs periodic maintenance on connection data with clients
        """
        if not hasattr(self,'peer_servers'):
            return
        for key in self.peer_servers.keys():
            #print self.peer_servers[key].last_broadcast_time
            if self.peer_servers[key].is_open_connection == False:
                continue
            if (time.time() - self.peer_servers[key].last_broadcast_time) > 30:
                print ("Shutting down inactive peer_server:",
                       self.peer_servers[key].name,
                       self.peer_servers[key].server_id,
                       'Last Broadcast time:',
                       str(time.time() -float(self.peer_servers[key].last_broadcast_time)),
                       'seconds ago')
                self.peer_servers[key].close()
                #del self.peer_servers[key]
        return # temporary disable
        self.__periodic_maintenance__()
#        for peer in self.client_roles:
#            for role in self.client_roles[peer]:
#                try: 
#                    if (time-time()-self.client_roles[peer][role])>self.role_timeouts[role]:
#                        del self.client_roles[peer][role]
#                except KeyError: pass
    def xstatus(self):
        stat='<Clients>'
        try:
            statd=''
            for client in self.clients:
                statd += '<Client>'
                statd += '<Name>'
                statd += socket.gethostbyaddr(client.split(":")[0])[0]
                statd += '</Name>'
                statd += '<IP>'
                statd += client
                statd += '</IP>'
                statd += '<Referer>'
                statd += (self.clients[client])['referer']
                statd += '</Referer>'
                statd += '<LastConnect>'
                statd += str(round(-(self.clients[client])['lastConnect']
                                + time.time()))
                statd += '</LastConnect>'
                statd += '</Client>'
            stat+=statd
        except:
            stat+='<Updating></Updating>'
        stat+='</Clients>'
        return stat
    

    def add_peer_server(self, ping_payload):
        """
        Adds a peer server to the the Connection Manager for the main server.
        """
        #print "In class ClientManager, function, add_peer_server()"
        if ping_payload != None:
            new_peer = PeerServer()
            new_peer.is_open_connection = False
            new_peer.server = self.server
            new_peer.connection_manager = self
            new_peer.open_connection(ping_payload)
        else:
            raise
        
    def add_image_viewer_server(self, commands=None):
        """
        Adds a script server to the the Connection Manager for the main server.
        This is a barebones server whose only purpose is to execute little
        scripts that cannot be allowed to hog resources of the main server.
        There should be no more than ~16 script servers
        """
        if DEBUG: print "In class ConnectionManager, function, add_image_viewer_server()"
        new_image_viewer_server = ImageViewerServer()
        new_image_viewer_server.is_open_connection = False
        new_image_viewer_server.server = self.server
        new_image_viewer_server.connection_manager = self
        new_image_viewer_server.open_connection()

    def add_script_server(self):
        """
        Adds a script server to the the Connection Manager for the main server.
        This is a barebones server whose only purpose is to execute little
        scripts that cannot be allowed to hog resources of the main server.
        There should be no more than ~16 script servers
        """
        #print "In class ClientManager, function, add_script_server()"
        new_script_server = ScriptServer()
        new_script_server.is_open_connection = False
        new_script_server.server = self.server
        new_script_server.connection_manager = self
        new_script_server.open_connection()
        
    def get_available_script_server(self):
        for key in self.script_servers.keys():
            #print "in use:", self.script_servers[key].in_use
            if self.script_servers[key].in_use == False:
                return self.script_servers[key]
        
        #Past here, all script servers are in use
        global MAX_SCRIPT_SERVERS
        if len(self.script_servers) < MAX_SCRIPT_SERVERS:
            self.add_script_server()
        else:
            #print "Too Many Script_Servers. Killing oldest and using its resources."
            pass
            
        return None

    def use_script_server(self, script_sever):
        script_sever.in_use = True            
            
            
    def catch_ping(self, ping_payload):
        if not self.is_known_server(ping_payload):
            #Not known server. Add a new PeerServer
            #foreign_address = "ws://" + str(ping_payload['server_ip']) + ":" + str(ping_payload['server_port'])
            self.add_peer_server(ping_payload)
        
        
    def send(self,data, address,isBinary=False):
        #address can be the following: shadow, analysis, ip, ip:port styrings and numbers, peer_server object, ''ws://localhost:8086''
        #print "In class connection_manager, function, send()"
        if address.__class__.__name__ == 'ScriptServer':
            address.protocol.sendMessage(data,isBinary)
            #print "Just Sent:", data
            return True
        if address.__class__.__name__ == 'ImageViewerServer':
            address.protocol.sendMessage(data,isBinary)
            if DEBUG: print "Just Sent to ImageViewerServer:"
            #if DEBUG and not isBinary and len(data) < 10000: print data
            return True
        if address == 'active_parser':
            print "-----------act---------"
            for key in self.peer_servers:
                if self.peer_servers[key].ip == self.server.active_parser_ip:
                    self.peer_servers[key].protocol.sendMessage(data,isBinary)
                    print "Just Sent:", data   
                    return True
        # Only thing left is assuming that the address is an ip address.
        #try:
        #    IP(address)
        #except ValueError:
        #    raise
            #Invalid IP address - NB: "4" is a valid ip address, the notation is that it pads 0's
        #address is a valid ip address now.
        for peer in self.peer_servers.keys():
            if self.peer_servers[peer].ip == address:
                p = self.peer_servers[peer].protocol
                p.sendMessage(data,isBinary)
                #p.sendMessage(simplejson.dumps({'Not_Command_text_message':'hi','terminator':'die'}, ensure_ascii = False).encode('utf8'))
                if not isBinary:
                    pass
                    #print "Just Sent:", data
                else:
                    #print "Just Sent (binary):"
                    d = msgpack.unpackb(data)
                    if 'databomb' in d:
                        pass
                        #print "-A lot of databomb data here-"
                    else:
                        print d
                return True
        for ss in self.script_servers.keys():
            if self.script_servers[ss].ip == address:
                p = self.script_servers[ss].protocol
                #print p.sendMessage(data,isBinary)
                #print "Just Sent:", data
                return True
        print "Not Sent!:"
        #print data
        return False
        
    def is_known_server(self,ping_payload):
        #pdb.set_trace()
        #print self.peer_servers
        #print "in isKnownServer"
        #print payload['server_id']
        found = False
        #print "Peer Servers:"
        for key in self.peer_servers:
            pass
            #print self.peer_servers[key].ip
        for key in self.peer_servers:
            #print self.peer_servers[key].ip
            '''
            directory = dir(self.peer_servers[key])
            for d, v in enumerate(directory):
                print directory[d], getattr(self.peer_servers[key],str(directory[d]))
            '''
            if self.peer_servers[key].ip == ping_payload['server_ip']:
                found = True
                '''
                There will be two peer server instances for this server.
                (both client and server is a peer_server instance)
                '''
                self.peer_servers[key].server_id = ping_payload['server_id']
                self.peer_servers[key].last_broadcast_time = time.time()
                self.peer_servers[key].server_time = ping_payload['server_time']
                self.peer_servers[key].ping_payload = ping_payload
                if self.peer_servers[key].is_open_connection == False:
                    self.peer_servers[key].reconnect(ping_payload)
                #print "Known Server"
        #print "Unknown Server"
        return found
        
    def announce_data_listener(self,params):
        print "class connection_manager, function announce_data_listener"
        #pdb.set_trace() #commend out by JZ on 10/3/14
        return
        announcement = {"IDLSocket_ResponseFunction":"announce_listener",
                        #"shotnumber":"",
                        "ip_address":'10.1.1.124',
                        "server_id":self.server.id,
                        "instrument_of_interest":"ccd_camera",
                        "terminator":"die"}
        announcement.update(params)
        for i in self.connections:
            #pdb.set_trace()
            #self.connections[i].sendMessage(simplejson.dumps(announcement))
            self.connections[i].sendMessage(simplejson.dumps(announcement),isBinary=False)
        
        
class GlabClient(XTSM_Server_Objects.XTSM_Server_Object):
    """
    a generic class for clients
    """
    def __init__(self, params={}):
        for key in params:
            setattr(self,key,params[key])
        self.id = str(uuid.uuid1())
        #self.id = str(uuid.uuid4())
        self.protocol_id = None
        self.time_of_creation = time.time()
        self.last_connection_time = None
        self.ip = None
        self.is_open_connection = False
        self.port = None
        
    def __periodic_maintenance__(self):
        """
        flushes old connections and relations
        """
        pass
    
    def log_communication(self,request):
        """
        logs a request
        """
        pass

    def on_close(self):
       self.is_open_connection = False
       
    
    def close(self):
       print "Shutting down connection:", self.protocol.connection.ip
       self.protocol.sendClose()
       self.protocol.transport.loseConnection()

    def on_open(self):  
        self.last_broadcast_time = time.time()
        pass               
               
    def catch_msgpack_payload(self, payload_, protocol):
        #pdb.set_trace()
        #print "class GlabClient, func catch_msgpack_payload"
        try:
            payload = msgpack.unpackb(payload_)
        except:
            pdb.set_trace()
            raise
        
                    
        SC = SocketCommand(params = payload,
                           request = protocol.request,
                           CommandLibrary = self.server.commandLibrary)
        try:
            #self.commandQueue.add(SC)
            #pdb.set_trace()
            self.server.command_queue.add(SC)
            #print "added socket command"
        #except AttributeError:
            #    self.commandQueue=CommandQueue(SC)
        except:
            protocol.sendMessage("{'server_console':'Failed to insert SocketCommand in Queue, reason unknown'}")
            raise
        
        #print "class GlabClient, func catch_msgpack_payload - End"
        #print payload

    def catch_json_payload(self, payload_, protocol):
        # we will treat incoming websocket text using the same commandlibrary as HTTP        
        # but expect incoming messages to be JSON data key-value pairs
        try:
            payload = simplejson.loads(payload_)
        except simplejson.JSONDecodeError:
            msg = {'Not_Command_text_message':"The server is expecting JSON, not simple text",'terminator':'die'}
            protocol.transport.write(simplejson.dumps(msg, ensure_ascii = False).encode('utf8'))
            print "The server is expecting JSON, not simple text"
            protocol.transport.loseConnection()
            return False
        # if someone on this network has broadcast a shotnumber change, update the shotnumber in
        # the server's data contexts under _running_shotnumber
        #pdb.set_trace()  
        if 'Not_Command_text_message' in payload:
            print payload['Not_Command_text_message']
            return
            
        #print "payload:"
        #print payload

        '''
        if hasattr(payload, "shotnumber"):
            #pdb.set_trace() # need to test the below
            for dc in self.parent.dataContexts:
                dc['_running_shotnumber']=payload['shotnumber']
        '''
        payload.update({'request':protocol.request})
        #payload.update({'protocol':protocol})
        payload.update({'socket_type':"Websocket"})
        SC = SocketCommand(params = payload,
                           request = protocol.request,
                           CommandLibrary = self.server.commandLibrary)
        try:
            #self.commandQueue.add(SC)
            self.server.command_queue.add(SC)
        #except AttributeError:
            #    self.commandQueue=CommandQueue(SC)
        except:
            protocol.sendMessage("{'server_console':'Failed to insert SocketCommand in Queue, reason unknown'}")
            raise  

               
class TCPConnection(GlabClient):
    def __init__(self):
        ConnectionManager.GlabClient.__init__(self)
        print "in TCPConnection class, __init__()"
    pass    
   
class PeerServer(GlabClient):
    """
    class to hold data regarding other XTSM servers on network
    when added open web socket. server connects to this peer server.
    Others open with TCP
    """
    
    def __init__(self):
        GlabClient.__init__(self)
        #print "in PeerServer class, __init__()"
        self.server_id = None
        self.name = None
        self.ping_payload = None
        self.last_broadcast_time = 0
        self.protocol = None
        #pdb.set_trace()
        
    def reconnect(self, ping_payload):
       self.open_connection(ping_payload)
    
    def open_connection(self, ping_payload):
       self.is_open_connection = True
       self.server_id = ping_payload['server_id']
       self.server_name = ping_payload['server_name']
       self.ip = ping_payload['server_ip']
       self.port = ping_payload['server_port']
       try:
           self.server_id_node = ping_payload['server_id_node']
       except:
           pass
       self.server_time = ping_payload['server_time']
       self.last_broadcast_time = time.time()
       # Connect to the peer as a Client
       address = "ws://" + ping_payload['server_ip'] + ":" + ping_payload['server_port']
       #print address
       wsClientFactory = WebSocketClientFactory(address, debug = True)
       wsClientFactory.setProtocolOptions(failByDrop=False)
       wsClientFactory.protocol = WSClientProtocol
       wsClientFactory.connection_manager = self.server.connection_manager
       wsClientFactory.connection = self
       connectWS(wsClientFactory)
        

    def on_message(self, payload, isBinary, protocol):
        if isBinary:
            self.catch_msgpack_payload(payload, protocol)
        else:
            self.catch_json_payload(payload, protocol)
        
    def on_open(self):
        self.is_open_connection = True  
        self.last_broadcast_time = time.time()
        self.connection_manager.peer_servers.update({self.id:self})
        self.server.connection_manager.connectLog(self) 
        
class ImageViewerServer(GlabClient):
    def __init__(self):
        GlabClient.__init__(self)
        self.output_from_script = None
        self.in_use = True # Keep as true on initialization so that the
        #server doesn't accidentally  try to hand this server off to two
        #processes when it was just first created.
        if DEBUG: print "in DataGuiServer class, __init__()"
    pass
    
    def open_connection(self):
        new_port = 9100 + len(self.connection_manager.image_viewer_servers)
        if DEBUG: print "About to open"
        image_viewer_path = os.path.abspath(image_viewer.__file__)
        subprocess.Popen(['C:\\Python27\\python.exe',image_viewer_path]+['localhost',str(new_port)])
        if DEBUG: print "Done Opening"            
        # Connect to the data_gui_
        address = 'ws://localhost:'+str(new_port)
        wsClientFactory = WebSocketClientFactory(address, debug = True)
        wsClientFactory.setProtocolOptions(failByDrop=False)
        wsClientFactory.protocol = WSClientProtocol
        wsClientFactory.connection_manager = self.connection_manager
        wsClientFactory.connection = self
        #connectWS(wsClientFactory)  
        reactor.callLater(1,connectWS,wsClientFactory)
        self.connection_manager.connectLog(self)  
        self.last_broadcast_time = time.time()
        pass
    
    def on_message(self, payload, isBinary, protocol):
        #pdb.set_trace()
        if isBinary:
            pass
            if DEBUG: print "Binary message received: {0} bytes"#, payload
        else:
            #payload = payload.decode('utf8')
            if DEBUG: print "Text message received in Client ws protocol:",payload

    def on_open(self):
        self.in_use = True
        self.is_open_connection = True
        self.connection_manager.image_viewer_servers.update({self.id:self})
        self.server.connection_manager.connectLog(self)  
        self.last_connection_time = None
        self.in_use = False
        if DEBUG: print 'In class DataGuiServer, func on_open'
        
               
       
class ScriptServer(GlabClient):
    def __init__(self):
        GlabClient.__init__(self)
        self.output_from_script = None
        self.in_use = True # Keep as true on initialization so that the
        #server doesn't accidentally  try to hand this server off to two
        #processes when it was just first created.
        #print "in ScriptServer class, __init__()"
    pass
    
    def open_connection(self):
        new_port = 9000 + len(self.connection_manager.script_servers)
        #print "About to open"
        script_server_path = os.path.abspath(script_server.__file__)
        subprocess.Popen(['C:\\Python27\\python.exe',script_server_path]+['localhost',str(new_port)])
        #print "Done Opening"            
        # Connect to the new_script_server
        address = 'ws://localhost:'+str(new_port)
        wsClientFactory = WebSocketClientFactory(address, debug = True)
        wsClientFactory.setProtocolOptions(failByDrop=False)
        wsClientFactory.protocol = WSClientProtocol
        wsClientFactory.connection_manager = self.connection_manager
        wsClientFactory.connection = self
        connectWS(wsClientFactory)  
        self.connection_manager.connectLog(self)  
        self.last_broadcast_time = time.time()
        pass
    
    def on_message(self, payload, isBinary, protocol):
        if isBinary:
            pass
            #print "Binary message received: {0} bytes"#, payload
        else:
            payload = payload.decode('utf8')
            #print "Text message received in Client ws protocol:",payload
            
            self.output_from_script = payload
            self.last_connection_time = None
            print "Script Finished. Payload:"
            print payload
            #print "Waiting for server to take my payload and then set script_server.in_use = False"
            if self.output_from_script == '"Script Server Ready!"':
                self.output_from_script = None
                self.in_use = False

    def on_open(self):
        self.in_use = True
        self.is_open_connection = True
        self.connection_manager.script_servers.update({self.id:self})
        if len(self.connection_manager.script_servers) < 2:
            script_command = ServerCommand(self.connection_manager.add_script_server)
            reactor.callLater(0.1, self.server.command_queue.add, script_command)
        self.server.connection_manager.connectLog(self)  
        self.protocol.sendMessage("output_from_script = 'Script Server Ready!'")
        
        
class CommandQueue():
    """
    The CommandQueue manages server command executions; it is basically a stack
    of requests generated by incoming requests, combined with a library of
    known commands with which to respond.
    """
    def __init__(self,server,Command=None,owner=None):
        self.server = server
        if Command!=None:
            self.queue=[Command]
        else: 
            self.queue=[]
        if owner!=None: 
            self.owner=owner

    def get_next_command(self):
        '''
        Get compile_active_xtsm asap, otherwise, other priority commands
        '''
        for command in self.queue:
            if not hasattr(command, 'command'):
                continue
            if not hasattr(command.command, 'has_key'):
                continue
            if not command.command.has_key('IDLSocket_ResponseFunction'):
                continue
            if command.command['IDLSocket_ResponseFunction'] == 'compile_active_xtsm':
                compile_command = command
                self.queue.remove(compile_command)
                return compile_command
            else:
                continue
            
        return self.queue.pop()
            
            
    
    def add(self,command):
        #print "class Queue, function add"
        #pdb.set_trace()
        if isinstance(  command , ServerCommand):
            #print "This is a ServerCommand"
            pass
            #pdb.set_trace()
        self.queue.append(command)
        #print "class Queue, function add - End"
    def popexecute(self):
        #print "class Queue, function popexecute"
        if len(self.queue) > 0:
            #print "Executing top of Queue"
            command = self.get_next_command()
            command.execute(self.server.commandLibrary)
            #print "Executing top of Queue - End"
    def xstatus(self):
        stat="<Commands>"
        if hasattr(self,'queue'):
            for command in self.queue:
                stat += '<Command>'
                try:
                    statd = ''
                    statd += "<Name>"
                    statd += command.params['IDLSocket_ResponseFunction']
                    statd += "</Name>"
                    for param in command.params:
                        statd += "<Parameter>"
                        statd += "<Name>" + param + "</Name>"
                        statd += "<Value>"
                        statd += "<![CDATA["
                        statd += command.params[param][0:25]
                        statd += "]]>"
                        statd += "</Value>"
                        statd += "</Parameter>"
                    stat += statd
                except: stat += "<Updating></Updating>"
                stat += '</Command>'
        stat += "</Commands>"
        return stat

class CommandLibrary():
    """
    The Command Library contains all methods a server can execute in response
    to an HTTP request; the command is specified by name with the 
    "IDLSocket_ResponseFunction" parameter in an HTTP request
    Note: it is the responsibility of each routine to write responses
    _AND CLOSE_ the initiating HTTP communication using
    params>request>protocol>loseConnection()
    """
    def __init__(self, server):
        #print "class CommandLibrary, func __init__"
        self.server = server
        
    def __determineContext__(self,params):
        #print "class CommandLibrary, func __determineContext__"
        #print params
        if not params.has_key('data_context'):
            ip_address = ''
            try:
                ip_address = params['request']['protocol'].peer.split(":")[0]
            except KeyError:
                print "Error: class CommandLibrary, func __determineContext__"
                pdb.set_trace()
                raise
            default_dc_name = "default:" + ip_address
            dcname = default_dc_name
            if ip_address == '127.0.0.1':
                dcname = 'default:' + self.server.ip
            if not self.server.dataContexts.has_key(dcname):
                dc = DataContext(dcname, self.server)
                self.server.dataContexts.update({dcname:dc})
            #print "dcname:",dcname
            return self.server.dataContexts[dcname]
            
        dcname = params['data_context']
        if not self.server.dataContexts.has_key(dcname):
            dc = DataContext(dcname, self.server)
            self.server.dataContexts.update({dcname:dc})
        #print "dcname:",dcname
        return self.server.dataContexts[dcname]
        
        '''
        old function:
        print "class CommandLibrary, func __determineContext__"
        print params
        try: 
            dcname = params['data_context']
            if dcname == 'exp_sync':
                dcname = 'default:10.1.1.136'
            #print "dcname:", dcname
            if not params['request']['protocol'].server.dataContexts.has_key(dcname):
                raise KeyError
        except KeyError:
            # look for a default data context for this IP address, if none, create
            #pdb.set_trace()
            dcname = "default:"+params['request']['protocol'].peer.split(":")[0]
            if params['request']['protocol'].peer.split(":")[0] == '127.0.0.1':
                dcname = "default:"+self.server.ip
            if not params['request']['protocol'].server.dataContexts.has_key(dcname):
                dc = DataContext(dcname, self.server)
                params['request']['protocol'].server.dataContexts.update({dcname:dc})
        print "dcname:",dcname
        return params['request']['protocol'].server.dataContexts[dcname]
        '''        
        
    # below are methods available to external HTTP requests - such as those required
    # by experiment GUI and timing system to implement basic functions of timing system
    # all must accept a single dictionary argument params, containing arguments of HTTP request
    # and an item 'request', which contains data on HTTP request and a reference to the twisted
    # protocol instance handling the response
    def set_global_variable_from_socket(self,params):
        """
        sets a variable by name in the caller's data context
        """
        #print "class CommandLibrary, func set_global_variable_from_socket"
        if params.has_key('IDLSPEEDTEST'):
            srtime = time.time()
            """
            These write functions may crash any websocket connections that it
            tries to write into since it may not be json
            """
            params['request']['protocol'].transport.write(params['IDLSPEEDTEST'])
            ertime = time.time()
            params['request']['protocol'].transport.write(str(srtime-params['request']['ctime'])+','+str(ertime-srtime)+','+str(params['request']['timereceived']-params['request']['ctime'])+',0,0,0')      
            params['request']['protocol'].transport.loseConnection()
            return
        try: 
            varname=set(params.keys()).difference(set(['IDLSocket_ResponseFunction',
                                                       'terminator',
                                                       'request',
                                                       'data_context'])).pop()
        except KeyError:
            params['request']['protocol'].transport.write('Error: Set_global requested, but no Variable Supplied')
            params['request']['protocol'].transport.loseConnection()
            return
        if varname!='_active_xtsm':
            dc=self.__determineContext__(params)
            dc.update({varname:params[varname]})
            params['request']['protocol'].transport.write(str(varname)+
                                                              ' updated at ' +
                                                              time.strftime("%H:%M:%S") +
                                                              '.' )
            params['request']['protocol'].transport.loseConnection()
            return
        else:
            self.post_active_xtsm(params)

#Loopiong Call, under server.chck for new image on cameradatabomb -> databomb dispatcher - 
        #dispatcher periodically called bvia looping call and the dispatcher periodically sends it off. - 1s eg.
        #add function in command library that gets all instrucments attached to that server. - children of GLabInstrument.
        #second function in command library that adds you as a destination to the databomb dispatcher. - send it back over the client websocket.
        #databomb dispatcher is also a member objct of the Server.
        

    def scan_instruments(self):
        interested_instruments = []
        for dc in self.server.dataContexts:
            for key in dc:
                if isinstance(dc[key], glab_instrument.Glab_Instrument):
                    interested_instruments.append(dc[key])
                    
        return interested_instruments
        
        
        #End Test

    def announce_listener(self,params):
        #print "class server, function announce_listener"
        self.server.DataBombDispatcher.link_to_instrument(params)
        #send back errors - return fail - ie no instrument.


    def get_global_variable_from_socket(self,params):
        """
        gets a variable by name from the caller's data context
        """
        """
        These write functions may crash any websocket connections that it
        tries to write into since it may not be json
        """
        #print "class CommandLibrary, func get_global_variable_from_socket"
        try:
            varname=params['variablename']
            dc=self.__determineContext__(params)
            # A special case is required for XTSM, as it will return an object, not a string, if it is not cantented to another string.
            params['request']['protocol'].transport.write(str(dc.get(varname)))
            params['request']['protocol'].transport.loseConnection()
        except KeyError:
            params['request']['protocol'].transport.write('Error: get_global requested, but no variable name supplied')
            params['request']['protocol'].transport.loseConnection()

    def ping_idl_from_socket(self,params):
        """
        These write functions may crash any websocket connections that it
        tries to write into since it may not be json
        """
        params['request']['protocol'].transport.write('ping')
        params['request']['protocol'].transport.loseConnection()

    def get_server_status(self,params):
        """
        These write functions may crash any websocket connections that it
        tries to write into since it may not be json
        """
        params['request']['protocol'].transport.write(params['request']['protocol'].factory.parent.xstatus())
        params['request']['protocol'].transport.loseConnection()

    def get_data_contexts(self,params):
        """
        Gets all data contexts from the server and sends the key under which each is stored.
        """
        """
        These write functions may crash any websocket connections that it
        tries to write into since it may not be json
        """
        #print "class CommandLibrary, func get_data_contexts"
        for dc in params['request']['protocol'].factory.parent.dataContexts:
            params['request']['protocol'].transport.write(str(dc) + ',')
        params['request']['protocol'].transport.loseConnection()

    def execute_from_socket(self,params):
        """
        Executes an arbitrary python command through the socket, and returns the console
        output
        """
        """
        These write functions may crash any websocket connections that it
        tries to write into since it may not be json
        """
        #print "class CommandLibrary, func execute_from_socket"
        dc=self.__determineContext__(params).dict
        # setup a buffer to capture response, temporarily grab stdio
        params['request']['protocol'].transport.write('<Python<           '+params['command']+'\n\r')        
        rbuffer = StringIO()
        sys.stdout = rbuffer
        try: exec(params['command'],dc)
        except:
            """
            These write functions may crash any websocket connections that it
            tries to write into since it may not be json
            """
            params['request']['protocol'].transport.write('>Python>   ERROR\n\r')
            params['request']['protocol'].transport.loseConnection()
            return
        # exec command has side-effect of adding builtins; remove them
        if dc.has_key('__builtins__'): 
            del dc['__builtins__']
        # update data context
        # remember to restore the original stdout!
        sys.stdout = sys.__stdout__ 
        # requests variables from the directory and writes to user.
        params['request']['protocol'].transport.write('>Code>')
        for var in dc:
            params['request']['protocol'].transport.write('>Var>' + var + ' is ' + str(type(var)) + ' and is equal to ' + str(dc[var]))
        params['request']['protocol'].transport.write('>Code>')
        # output the response buffer to the HTTP request
        params['request']['protocol'].transport.write('>Python>   '+rbuffer.getvalue()+'\n\r')
        params['request']['protocol'].transport.loseConnection()
        rbuffer.close()

    def post_active_xtsm(self, params):
        """
        Posts the active xtsm string that will be used for all subsequent calls
        from timing systems
        """
        #print "class CommandLibrary, func post_active_xtsm"
        params.update({'data_context':'10.1.1.136'})#Not sure if this the right idea. CP
        dc = self.__determineContext__(params)
        try: 
            exp_sync = dc.get('_exp_sync')        
        except: 
            exp_sync = Experiment_Sync_Group(self.server)
            dc.update({'_exp_sync':exp_sync})
        try:
            ax = params['_active_xtsm']
        except KeyError:
            ax = params['active_xtsm']
        ax = XTSM_Transforms.strip_to_active(ax)
        exp_sync.active_xtsm = ax
        """
        These write functions may crash any websocket connections that it
        tries to write into since it may not be json
        """
        params['request']['protocol'].transport.write('Active XTSM updated at ' + time.strftime("%H:%M:%S") + '.' )
        params['request']['protocol'].transport.loseConnection()

    def request_xtsm(self,params):
        """
        Retrieves and returns xtsm by shotnumber
        """
        #print "class CommandLibrary, func request_xtsm"
        dc = self.__determineContext__(params)
        message = 'XTSM requested, but shot number does not exist'
        '''
        Added to make work CP. To fix, need to change the gui query.
        '''
        try: 
            exp_sync = dc.get('_exp_sync')
        except:
            params.update({'data_context':'PXI'})
            dc = self.__determineContext__(params)
        '''
        End addition CP
        '''
        #pdb.set_trace()
        
        try: 
            exp_sync = dc.get('_exp_sync')
        except:
            self._respond_and_close(params,"XTSM requested, but none exists")
            return
        try:
            sn = exp_sync.shotnumber + int(params['shotnumber'])
            xtsm = exp_sync.compiled_xtsm[sn].XTSM
            msg = {"xtsm":xtsm.write_xml(),"shotnumber":int(params['shotnumber'])}
            #xtsm = exp_sync.compiled_xtsm[int(params['shotnumber'])].XTSM
            #msg = {"xtsm":xtsm.write_xml(),"shotnumber":int(params['shotnumber'])}
            reqxtsm = simplejson.dumps({"xtsm_return":simplejson.dumps(msg)})
            #print reqxtsm
        except KeyError: 
            try:
                params['request']['write']('{"server_console":"'+message+'"}')
            except KeyError: 
                params['request']['protocol'].transport.write(message)
                params['request']['protocol'].transport.loseConnection()
                print "Error"
        try:
            params['request']['write'](reqxtsm)
        except KeyError: 
            """
            These write functions may crash any websocket connections that it
            tries to write into since it may not be json
            """
            params['request']['protocol'].transport.write(reqxtsm)
            params['request']['protocol'].transport.loseConnection()
            print "Error"
        except UnboundLocalError:
            pass
            print "GUI tried to search for shotnumber that doesn't exist."

    def compile_active_xtsm(self, params):
        """
        Compiles the active xtsm in the current data context for requestor,
        and returns the timingstring to the requestor through the html response
        
        the current context is with highest priority the one specified by the
        "data_context" element in the caller's request, with next highest the 
        context assigned to the requester by default, and with next highest the
        first datacontext retrieved with a "pxi_data_context" element naming
        the requester's data context.  If any are missing the _exp_sync element
        containing the active_xtsm string and shotnumber, they are skipped.
        """
        #print params
        # mark requestor as an XTSM compiler
        #print "In class CommandLibrary, function compile_active_xtsm", "time:", float(time.time()) - 1412863872
        
        '''
        self.server.connection_manager.update_client_roles(params['request'],'active_XTSM_compiler')
        dc = self.__determineContext__(params)
        print "datacontext name:", dc.name
        if not dc.dict.has_key('_exp_sync'):
            exp_sync = Experiment_Sync_Group(self.server)
            dc.update({'_exp_sync':exp_sync})
        dc['_exp_sync'].shotnumber = int(params['shotnumber'])
        print "datacontext name:", dc.name
        '''
        
        
        self.server.connection_manager.update_client_roles(params['request'],'active_XTSM_compiler')
        print params
        
        if params['request']['host'] == '169.254.174.200:8083':
            params.update({'data_context':'10.1.1.136'})#Not sure if this the right idea. CP
            #Coming from the PXI system. Right now a hack to preserve backwards
            #compatability. I think I need to change this in labview
            #params.update({'data_context':'PXI'})
            dc = self.__determineContext__(params)
            if not dc.dict.has_key('_exp_sync'):
                exp_sync = Experiment_Sync_Group(self.server)
                dc.update({'_exp_sync':exp_sync})
            dc['_exp_sync'].shotnumber = int(params['shotnumber'])
        dc = self.__determineContext__(params)
        
        '''
        if True:
        #if params['data_context'] == 'PXI_emulator':
            #Coming from the PXI system. Right now a hack to preserve backwards
            #compatability. I think I need to change this in labview
            #params.update({'data_context':'PXI'})
            dc = self.__determineContext__(params)
            if not dc.dict.has_key('_exp_sync'):
                exp_sync = Experiment_Sync_Group(self.server)#pass the reference of dc
                dc.update({'_exp_sync':exp_sync})
            dc['_exp_sync'].shotnumber = int(params['shotnumber'])
        dc = self.__determineContext__(params)        
        '''
        '''
        These lines are obsolete I think (CP) the pxi data context is "PXI"
        parent_dc = ''
        if dc.dict.has_key('_exp_sync'): 
            parent_dc=dc
            
        # next lines look for the first defined data context that has
        # a pxi_data_context element matching 'default:ip address' of pxi system 
        else:
            for name, pdc in params['request']['protocol'].factory.parent.dataContexts.iteritems():
                try:
                    if ((pdc.get('pxi_data_context') == dc.get('__context__')) and pdc.dict.has_key('_exp_sync')):
                        parent_dc = pdc
                except KeyError:
                    pass
        # if none exists, exit and return
        if parent_dc == '':
            self.server.broadcast('{"server_console": "'+ params['request']['protocol'].peer.split(":")[0] +
                                ' requested timing data, but nothing is ' +
                                'assigned to run on this system."}')
            params['request']['protocol'].transport.loseConnection()
            return
        else:
            dc = parent_dc
        '''
        if not dc.dict.has_key('_exp_sync'): 
            self.server.broadcast('{"server_console": "'+
                                params['request']['protocol'].peer.split(":")[0] +
                                ' requested timing data, but nothing is ' +
                                'assigned to run on this system."}')
            params['request']['protocol'].transport.loseConnection()
            print "Error: nothing assigned to run"
            return
        
        #print "datacontext name:", dc.name
        # get the experiment synchronization object; retrieve the current shotnumber
        exp_sync = dc.get('_exp_sync')
        #
        '''
        The pxi system is now keeping track of the shotnumber.
        '''
        sn = exp_sync.shotnumber
        
        #pdb.set_trace()
        # turn the active_xtsm string into an object
        dc.update({'_active_xtsm_obj':XTSMobjectify.XTSM_Object(exp_sync.active_xtsm)})
        xtsm_object = dc.get('_active_xtsm_obj')
        #print "datacontext name:", dc.name

        # parse the active xtsm to produce timingstrings
        self.server.broadcast('{"server_console": "' +#'server_console' comnmand in javasdcript
        str(datetime.now()) +  " Parsing started" + " Shotnumber= " + str(sn) + '"}')
        
        try:
            XTSMobjectify.preparse(xtsm_object)
        except AttributeError:
            print "Error: Bad XTSM"
            self.server.bad_xtsm = xtsm_object
            self.server.bad_xtsm_params = params
            return
        t0 = time.time()
        parserOutput = xtsm_object.parse(sn)
        tp = time.time()
        XTSMobjectify.postparse(parserOutput)            
        t1 = time.time()
        #print "Parse Time: " , t1-t0, "s", "(postparse ", t1-tp, " s)"
        self.server.broadcast('{"server_console": "' +
                                 str(datetime.now()) +
                                 " Parsing finished" +
                                 " Shotnumber= " + str(sn) +  '"}')
        self.server.broadcast('{"parsed_active_xtsm": "' +
                                 str(datetime.now()) + '"}')

        #Setting parameters:
        #pdb.set_trace()
        for par in xtsm_object.XTSM.getDescendentsByType("Parameter"):
            if hasattr(par,"PostToContext"):
                if par.PostToContext.PCDATA == 'True':
                    try:
                        dc.update({par.Name.PCDATA:par.Value.parse()})
                    except Exception as e:
                        par.addAttribute("parser_error", str(e))
                        print "Error: parser"
                        return

        # setup data listeners for returned data
        #pdb.set_trace()
        if (not dc.dict.has_key('_bombstack')):
            dc.update({'_bombstack':DataBomb.DataBombList()})
        if (not hasattr(dc['_bombstack'],'dataListenerManagers')):
            setattr(dc['_bombstack'],
                        'dataListenerManagers',
                        DataBomb.DataListenerManager())            
        #pdb.set_trace()
        if (not dc.dict.has_key('_analysis_stream')):
            p = {'file_root_selector':'analysis_stream'}
            dc.update({'_analysis_stream':InfiniteFileStream.FileStream(params=p)})
        xtsm_object.XTSM._analysis_stream = dc['_analysis_stream']
        #pdb.set_trace()
        xtsm_object.installListeners(dc['_bombstack'].dataListenerManagers)#This calls _generate_listeners_ and passes in the DLM instance.
        #InstallListeners passes the return of __generate_listeners__ to spawn in DLM class
        # InstrumentCommands
        #print "datacontext name:", dc.name
            
        #Dispatch all scripts, - Scripts in InstrumentCommand is in a subset of all Scripts - so, dispatch all Scripts first
        for d in self.server.dataContexts:
            pass
            #print d
        #Need to find the InstrumentCommand for the current sequence 
            
        commands = xtsm_object.XTSM.getDescendentsByType("InstrumentCommand")#Need to dispatch all scripts. Change This CP
        for c in commands:
            c.Script.dispatch(self.server)
            
            
            #self.server.dataContexts['default:10.1.1.112'].update({'Test_instrument':glab_instrument.Glab_Instrument(params={'server':self.server,'create_example_pollcallback':True})})
            #return
                #Also need to change the passing in of a script body to actually have those lines of code.
                #Then in the GUI we can make a text box so the code is visible,
                #And - if there gets to be lots of code, it can be put into the "Roper_CCD" class as a function to call.

            ## Testing CP
            #for key in self.dataContexts:
            #    m = self.dataContexts[key].dict['data_listener_manager']
            #    m.spawn(params={'sender':'Pfaffian','server':self})
            #    for key2 in m.listeners:
            #        m.listeners[key2].announce_interest('10.1.1.112')

            # Send scripts CP
            #scripts = parserOutput.getDescendentsByType("Script")
            #for s in scripts:
            #    s.dispatch(self.server)

            # send back the timingstrings
        timingstringOutput = str(bytearray(parserOutput.package_timingstrings()))
        """
        These write functions may crash any websocket connections that it
        tries to write into since it may not be json
        """
        #print "timingstringOutput, at time:", float(time.time()) - 1412863872
        #pdb.set_trace()
        params['request']['protocol'].transport.write(timingstringOutput)
        #dc.get('_exp_sync').shotnumber = sn + 1 PXI system will keep track of sn
        params['request']['protocol'].transport.loseConnection()

        # begin tracking changes to the xtsm_object
        def _changed_xtsm(changedelm):
            self.server.broadcast('{"xtsm_change":"'+str(sn)+'"}')
        xtsm_object.XTSM.onChange = _changed_xtsm
            
        # attach the xtsm object that generated the outgoing control arrays to the experiment sync's xtsm_stack
        dc['_exp_sync'].compiled_xtsm.update({sn:xtsm_object})
        dc['_exp_sync'].last_successful_xtsm = exp_sync.active_xtsm
        #print 'end compile active'

    def testparse_active_xtsm(self, params):
        """
        Parses the active_xtsm and posts the processed xtsm in the current data context
        as _testparsed_xtsm, as well as returns it to the requester as an xml string
        """
        #print "In class CommandLibrary, function testparse_active_xtsm"
        dc = self.__determineContext__(params)  # gets the calling command's data context
        parent_dc = ''  # begins looking for the pxi system's data context
        for name, pdc in params['request']['protocol'].factory.parent.dataContexts.iteritems():
            try:
                if dc.get('__context__') == pdc.get('pxi_data_context'):
                    parent_dc = pdc
            except KeyError:
                pass

        if parent_dc=='':
            parent_dc = dc  # if there is no pxi data context, revert to caller's
        active_xtsm = parent_dc.get('_active_xtsm')  # retrieve the xtsm code currently active
        try:
            sn = parent_dc.get('_shotnumber')
        except AttributeError:
            sn = 0

        xtsm_object = XTSMobjectify.XTSM_Object(active_xtsm)
        #print datetime.now(), " Parsing started", " Shotnumber= ",sn
        XTSMobjectify.preparse(xtsm_object)
        parserOutput = xtsm_object.parse(sn)
        XTSMobjectify.postparse(parserOutput)
        #print datetime.now(), " Parsing finished", " Shotnumber= ",sn

        timingstringOutput = str(bytearray(parserOutput.package_timingstrings()))
        # create timingstring even though it isn't used
        
        parsed_xtsm = xtsm_object.XTSM.write_xml()
        dc.update({'_testparsed_xtsm':parsed_xtsm})
        """
        These write functions may crash any websocket connections that it
        tries to write into since it may not be json
        """
        params['request']['protocol'].transport.write(str(parsed_xtsm))
        params['request']['protocol'].transport.loseConnection()

    def databomb(self, params):
        """
        dumps a messagepack data bomb into current data context's bombstack
        this is a method for data collection hardware to report data into
        the webserver to be stored to disk, associated with the generating XTSM,
        and for analyses to be initiated 
        """
        
        print "dealing with data bomb that came back"
        #print self.server.dataContexts['default:127.0.0.1'].dict['_bombstack'].dataListenerManagers.listeners #This is the context that has the listeners
        #pdb.set_trace()
        
        dc=self.__determineContext__(params)
        #print dc.dict['_bombstack'].dataListenerManagers.listeners#Should have listeners installed
        if (not dc.dict.has_key('_bombstack')):
            dc.update({'_bombstack':DataBomb.DataBombList()})
        # data listeners should be attached under the bombstack!!
        # if (not dc.dict.has_key('dataListenerManagers')): dc.update({'dataListenerManagers':DataBomb.DataListenerManager()})
        if (not hasattr(dc['_bombstack'],'dataListenerManagers')):
            setattr(dc['_bombstack'],
                    'dataListenerManagers',
                    DataBomb.DataListenerManager())

        
        bomb_id=dc['_bombstack'].add(DataBomb.DataBombList.DataBomb(params['databomb']))
        msg = {'Not_Command_text_message':'databomb ' + bomb_id + ' updated at ' + time.strftime("%H:%M:%S") + '.','terminator':'die'}
        #msg = {'Not_Command_text_message':'hi','terminator':'die'}        
        
        #This closes the ws connection - I don't know why - CP       
        #params['request']['protocol'].transport.write(simplejson.dumps(msg, ensure_ascii = False).encode('utf8'))
        if str(params['request']['protocol'].transport.getPeer().port) != str(wsport):
            pass
            #params['request']['protocol'].transport.loseConnection()
            
        # next line adds a deployment command to the command queue
        #This should be moved into the Databomb class
        self.server.command_queue.add(ServerCommand(dc['_bombstack'].deploy,bomb_id))
        #self.temp_plot_oneframe(params, bomb_id,dc) #LRJ 10-21-2014 _oneframe
        raw_databomb = msgpack.unpackb(params['databomb'])
        self.server.databombs_for_image_viewer.update({str(raw_databomb['shotnumber']):params['databomb']})
        
        self.temp_plot(params, bomb_id,dc)
        
       
        
    def temp_plot_qt(self,params,bomb_id, dc):
        print "plotting"
        raw_databomb = msgpack.unpackb(params['databomb'])
        fig = plt.figure(figsize=(18, 12))  
        ax = fig.add_subplot(221)
        #pdb.set_trace()
        raw_img_data = raw_databomb['data']
        num_pics = len(raw_img_data)
        corrected_image = [[]]
        if num_pics != 0:
            if num_pics == 3:
                #print "three frames"prindd
                corrected_image = np.subtract(np.asarray(raw_img_data[1],dtype=int),
                                              np.asarray(raw_img_data[2],dtype=int))
            else:
                print "Not Supported"
                return
                raise
        #min_scale = 65536
        max_scale_zoom = -50
        min_scale_zoom = 30*1000
        max_scale_full = -50
        min_scale_full = 30*1000
        if dc.dict.has_key('ImageScaleZoomMax'):
            max_scale_zoom = dc['ImageScaleZoomMax']
        if dc.dict.has_key('ImageScaleZoomMin'):
            min_scale_zoom = dc['ImageScaleZoomMin']
        if dc.dict.has_key('ImageScaleFullMax'):
            max_scale_full = dc['ImageScaleFullMax']
        if dc.dict.has_key('ImageScaleFullMin'):
            min_scale_full = dc['ImageScaleFullMin']
            

        pix = 512
        frame1 = np.asarray(np.random.rand(pix,pix).tolist())
        frame2 = np.asarray(np.random.rand(pix,pix).tolist())

        app = QtGui.QApplication([])
        win = QtGui.QMainWindow()
        win.resize(800,800)
        imv = pg.ImageView()
        win.setCentralWidget(imv)
        win.show()
        img = np.random.normal(size=(pix, pix)) * 20 + 100
        img = frame1
        img = img[np.newaxis,:,:]
        data = np.asarray([frame1,frame2])
        imv.setImage(data)
        
        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtGui.QApplication.instance().exec_()
        
        
    def temp_plot(self, params, bomb_id,dc):
                
        raw_databomb = msgpack.unpackb(params['databomb'])
        #hdf5_liveheap.glab_liveheap
        #file_storage = hdf5_liveheap.glab_datastore()
        #file_storage.
                
        
        fig = plt.figure(figsize=(18, 12))  
        ax = fig.add_subplot(221)
        #pdb.set_trace()
        raw_img_data = raw_databomb['data']
        num_pics = len(raw_img_data)
        corrected_image = [[]]
        if num_pics != 0:
            if num_pics == 1:
                print "one frame"
                corrected_image = np.subtract(np.asarray(raw_img_data[0],dtype=int), rdn.darkavg)
            elif num_pics == 2:
                print "two frames"
                #corrected_image = np.subtract(np.asarray(raw_img_data[1],dtype=int),
                #                              np.asarray(raw_img_data[0],dtype=int))
                corrected_image= np.subtract(np.asarray(raw_img_data[1],dtype=int), rdn.darkavg)               
            elif num_pics == 3:
                #print "three frames"prindd
#                corrected_image = np.log(np.divide(np.asarray(raw_img_data[1],dtype=float),
#                                              np.asarray(raw_img_data[2],dtype=float)))
                 corrected_image = np.subtract(np.asarray(raw_img_data[1],dtype=float),np.asarray(raw_img_data[2],dtype=float))
                 msg = {'shotnumber':raw_databomb['shotnumber'], 'data':corrected_image }
                 packed_message = msgpack.packb(msg , use_bin_type=True)
                 self.server.databomblist.append(packed_message) #add by Jz to create a list of databombs for imageviewer
                 #thresh_image = np.divide(np.asarray(raw_img_data[1],dtype=int),np.asarray(raw_img_data[2],dtype=int))
               
            else:
                print "Not Supported"
                return
                raise
        #min_scale = 65536
        
        max_scale_zoom = 500
        min_scale_zoom = 0
        max_scale_full = 500
        min_scale_full = 50
        
        
        if dc.dict.has_key('ImageScaleZoomMax'):
            max_scale_zoom = dc['ImageScaleZoomMax']
        if dc.dict.has_key('ImageScaleZoomMin'):
            min_scale_zoom = dc['ImageScaleZoomMin']
        if dc.dict.has_key('ImageScaleFullMax'):
            max_scale_full = dc['ImageScaleFullMax']
        if dc.dict.has_key('ImageScaleFullMin'):
            min_scale_full = dc['ImageScaleFullMin']
        
        
        #bottom_left_coord = (120,345)
        #top_right_coord = (340,180)
        bottom_left_coord = (400,170)#(x,y)
        top_right_coord = (450,200)
        #bottom_left_coord = (260,165)
        #top_right_coord = (271,185)
        region_of_interest = corrected_image[top_right_coord[1]:bottom_left_coord[0],
                                             bottom_left_coord[1]:top_right_coord[0]]
        #region_of_interest = corrected_image[180:350, #down, specify bottom,
        #                                     120:350]#second number is how far accross
        #pdb.set_trace()
        self.server.ALL_DATABOMBS.update({str(raw_databomb['shotnumber']):[raw_img_data[0],raw_img_data[1],raw_img_data[2]]})
        cax = ax.imshow(np.asarray(raw_img_data[1],dtype=float), cmap = mpl.cm.Greys_r,vmin=min_scale_full, vmax=max_scale_full, interpolation='none')#, cmap = mpl.cm.spectral mpl.cm.Greys_r)   
        cbar = fig.colorbar(cax)
        
        ax2 = fig.add_subplot(232)
        cax2 = ax2.imshow(np.asarray(raw_img_data[2],dtype=float), cmap = mpl.cm.Greys_r,vmin=min_scale_full, vmax=max_scale_full,interpolation='none')#, cmap = mpl.cm.spectral mpl.cm.Greys_r)                   

        ax3 = fig.add_subplot(233)
        cax3 = ax3.imshow(corrected_image, cmap = mpl.cm.Greys_r,vmin=min_scale_zoom, vmax=max_scale_zoom,interpolation='none')#, cmap = mpl.cm.spectral mpl.cm.Greys_r)                   
        cbar3 = fig.colorbar(cax3)

        ax4 = fig.add_subplot(234)
        cax4 = ax4.imshow(region_of_interest, cmap = mpl.cm.Greys_r,vmin=min_scale_zoom, vmax=max_scale_zoom,interpolation='none')#, cmap = mpl.cm.spectral mpl.cm.Greys_r)                   
        num_atoms = float(region_of_interest.sum()) * 303 * pow(10,-6) * 0.7
        cbar4 = fig.colorbar(cax4)
        '''        
        ax5 = fig.add_subplot(235)
        cax5 = ax5.imshow(thresh_image, cmap = mpl.cm.Greys_r,vmin=0, vmax=2,interpolation='none')#, cmap = mpl.cm.spectral mpl.cm.Greys_r)                   
        cbar5 = fig.colorbar(cax5)
        '''
        
        '''
        numrows, numcols = corrected_image.shape
        def format_coord(x, y):
            col = int(x+0.5)
            row = int(y+0.5)
            if col>=0 and col<numcols and row>=0 and row<numrows:
                z = corrected_image[row,col]
                return 'x=%1.4f, y=%1.4f, z=%1.4f'%(x, y, z)
            else:
                return 'x=%1.4f, y=%1.4f'%(x, y)

        ax.format_coord = format_coord 
        ax2.format_coord = format_coord 
        ax3.format_coord = format_coord 
        

        numrows, numcols = corrected_image.shape
        ax4.format_coord = format_coord       
        '''
        
        path = file_locations.file_locations['raw_buffer_folders'][uuid.getnode()]+'/'+date.today().isoformat()
        file_name = 'databomb_' + bomb_id + '_at_time_' + str(raw_databomb['packed_time'])
        plt.title("SN="+str(raw_databomb['shotnumber'])+'\n_'+path+'\n/'+file_name+' Counts = '+str(region_of_interest.sum()), fontsize=10)
        #plt.title("SN="+str(raw_databomb['shotnumber'])+' Counts = '+ str(region_of_interest.sum()), fontsize=10)
       #reactor.callInThread(plt.show,'block=False')
        #reactor.callFromThread(plt.close)
        #subtracted image
        plt.show(block=False)
                
        '''        
        f = open(path+'/'+file_name+'.txt', 'w')
        pickle.dump(corrected_image,f)
        f.close()
        #first raw image
        f = open(path+'/'+file_name+'_raw_img1.txt', 'w')
        pickle.dump(raw_img_data[0],f)
        f.close()
        #second raw image
        f = open(path+'/'+file_name+'_raw_img2.txt', 'w')
        pickle.dump(raw_img_data[1],f)
        f.close()
        #third raw image
        f = open(path+'/'+file_name+'_raw_img3.txt', 'w')
        pickle.dump(raw_img_data[2],f)
        f.close()
        '''        
        #print "--> Data pickled to:", path+'/'+file_name+'.txt'
        #plt.savefig(path+'/'+file_name+'.svg')
        plt.savefig(path+'/'+file_name+'.png')
        print "Shotnumber:", str(raw_databomb['shotnumber'])
        #print "Path to saved picture/data:", str(path+'/'+file_name+'.txt')
        #plt.close()
        
        # mark requestor as a data generator
        #pdb.set_trace()
       
    def temp_plot_oneframe(self, params, bomb_id,dc):
        
        raw_databomb = msgpack.unpackb(params['databomb'])
        #hdf5_liveheap.glab_liveheap
        #file_storage = hdf5_liveheap.glab_datastore()
        #file_storage.
                
        
        fig = plt.figure(figsize=(18, 12))  
        ax = fig.add_subplot(221)  
        
        #pdb.set_trace()
        raw_img_data = raw_databomb['data']
        num_pics = len(raw_img_data)
        corrected_image = raw_img_data[0]
       
      
        
        
        '''
        numrows, numcols = corrected_image.shape
        def format_coord(x, y):
            col = int(x+0.5)
            row = int(y+0.5)
            if col>=0 and col<numcols and row>=0 and row<numrows:
                z = corrected_image[row,col]
                return 'x=%1.4f, y=%1.4f, z=%1.4f'%(x, y, z)
            else:
                return 'x=%1.4f, y=%1.4f'%(x, y)
       '''
       
        max_scale=1200
        #max_scale=np.amax(corrected_image)
        min_scale=np.amin(corrected_image)
        #min_scale=0
        cax = ax.imshow(np.asarray(corrected_image,dtype=float), cmap = mpl.cm.Greys_r,vmin=min_scale, vmax=max_scale, interpolation='none')#, cmap = mpl.cm.spectral mpl.cm.Greys_r)   
        cbar = fig.colorbar(cax)
        
        path = file_locations.file_locations['raw_buffer_folders'][uuid.getnode()]+'/'+date.today().isoformat()
        file_name = 'databomb_' + bomb_id + '_at_time_' + str(raw_databomb['packed_time'])
        plt.title("SN="+str(raw_databomb['shotnumber']), fontsize=10)
        plt.show(block=False)
               
     
        plt.savefig(path+'/'+file_name+'.png')
        print "Shotnumber:", str(raw_databomb['shotnumber'])
        #print "Path to saved picture/data:", str(path+'/'+file_name+'.txt')
        #plt.close()
        
        # mark requestor as a data generator
        #pdb.set_trace()    
    
    
    def stop_listening(self,params):
        """
        Exit routine, stops twisted reactor (abruptly).
        """
        print "Closing Python Manager"
        broadcastMessage = "Python Manager Shutting Down on Request."
        self.server.broadcast('{"server_console":'+broadcastMessage+'}')
        msg = {'Not_Command_text_message':"Closing Python Manager - Goodbye.",'terminator':'die'}
        try:
            params['request']['write'](simplejson.dumps(msg, ensure_ascii = False).encode('utf8'))
        except KeyError: 
             params['request']['protocol'].transport.write(simplejson.dumps(msg, ensure_ascii = False).encode('utf8'))
             params['request']['protocol'].transport.loseConnection()
        """
        msg = "Closing Python Manager - Goodbye."
        try:
            params['request']['write'](msg)
        except KeyError: 
             params['request']['protocol'].transport.write(msg)
             params['request']['protocol'].transport.loseConnection()
        """
        self.server.stop()

    def request_content(self,params):
        """
        generates or looks up and supplies a live content item
        """
        dc = self.__determineContext__(params)
        if (not dc.dict.has_key('_content_manager')):
            dc.update({'_content_manager':live_content.Live_Content_Manager()})
        content = dc['_content_manager'].get_content(params["content_id"],
                                                     requester=params["request"]["protocol"])
        self._deliver_content(params,params["content_id"],content)

    def live_content_event(self,params):
        """
        responds to a live content event by passing it to the content manager
        """
        dc = self.__determineContext__(params)
        if (not dc.dict.has_key('_content_manager')):
            dc.update({'_content_manager':live_content.Live_Content_Manager()})
        dc['_content_manager'].registerEvent(params)
        
    def _deliver_content(self,params,content_id,content):
        """
        sends live_content items to a consumer - is called by request_content
        """
        try: 
            write_method = params["request"]["write"]
        except KeyError:
            write_method = params["request"]["protocol"].sendMessage
        content_json = simplejson.dumps({content_id:content})
        msg = simplejson.dumps({"receive_live_content":content_json})
        write_method(msg)

    def execute_script(self, params):
        #May want to pass this to a shadow server
        #Add functionality where main server timesout the shadow server if it doesn't return the original secript
        #Now should make a list of shadow servers.
        #Look into specifing which processor the script is launched on
        #Limit number to ~100
        #Keep track in peer_server.
        #dc=self.__determineContext__(params)
        #time = dc.get('time')
        #shotnumber = dc.get('shotnumber')
        #script = dc.get('script_xml')
        #script = "print 'This is script that is executed'"
        #pdb.set_trace()    
        #print "class CommandLibrary, function execute_script"
        
        #script = 'output_from_script = "hi"'
        #script_body = params['script_body']
        #print "script_body:"
        #print script_body
        #self.server.script_queue.add(params)
        #if self.server.clientManager.send("Hi",'ws://localhost:8086'):
        #self.server.send(script,'ws://localhost:8086')
        #wsClientFactory = WebSocketClientFactory(address, debug = True)
        #wsClientFactory.protocol = WSClientProtocol
        #wsClientFactory.clientManager = self
        #connectWS(wsClientFactory)          
        
        #print "class ScriptQueue, function popexecute"
        #print "script_servers:", self.server.clientManager.script_servers
        #print "script_queue =", self.queue
        
        '''Need to move this to the conditions on exectuting commands in the queue'''
        script_server = self.server.connection_manager.get_available_script_server()#Need to call this in order to create script_servers. Returns None when no servers ready     
        #print "return from get_avail... ss =", ss
        if script_server == None:
            pass
            #Need to add self back to the queue
            return
        if params['on_main_server'] == True:
            #This should be done in the sheltered scipt environment.
            #Add functionality for timing
            #print "Executing on Main Server"
            code_locals = {}
            #print "print queue[0]:"
            #print self.queue[0]
            #print "compile...."
            #inst = glab_instrument(self.server)
            #inst.name = self.queue[0]['name']
            #if self.queue[0]['name'] == 'CCD':
            ##    Roper_CCD.Princeton_CCD(self.queue[0])
            #self.server.instruments.update({inst.id:inst})
            #try:
            #    code = compile(self.queue.pop()['script_body'], '<string>', 'exec')
            #except:
            #    print "compile unsuccessful"
            #    raise
            #print "compile successful"
            print "executing"
            script = params['script_body']
            with open(script) as f:
                #Capture std out, look at sheltered script
                code = compile(f.read(), script, 'exec')
                exec(code, globals(), locals())#Copying of variables occur
            print "done executing"
            return
        else:
            #add functionality for timing
            #self.queue.pop().execute(self.server.commandLibrary)    
            #Trying to connect to a server that is not responsive will restart that server and try to connect again.
            #self.server.clientManager.use_script_server(ss)
            #print "got server"
            self.server.send(params['script_body'], script_server)
            return
        return

    def _respond_and_close(self,params,msg):
        """
        resonds to and closes (for standard HTTP) the socket communication 
        """
        try:
            params['request']['write']('{"server_console":'+msg+'}')
        except KeyError: 
            params['request']['protocol'].transport.write(msg)
            params['request']['protocol'].transport.loseConnection()

        

class ServerCommand():
    def __init__(self,command,*args):
        """
        Constructs a server command object, to be executed in the command queue
        
        These objects are separated from the SocketCommand library to provide
        secure functions which cannot be called from sockets.
        """
        #print "In class ServerCommand, func __init__"
        self.command=command
        self.args=args
        
    def execute(self, Library=None):
        #print "In class ServerCommand, func execute"
        try: 
            self.command(*self.args)
        except Exception as e:
            print e
            pdb.set_trace()

        
class SocketCommand():
    def __init__(self, params=None, request=None, CommandLibrary=None):
        """
        Constructs a SocketCommand object, which should contain one parameter
        in dictionary param with name IDLSocket_ResponseFunction, corresponding
        to a name in the CommandLibrary.  If CommandLibrary is supplied, verifies
        command's existence and tags property 'functional' true
        """
        self.command = params
        if not params.has_key('IDLSocket_ResponseFunction'):
            self.functional=False
            if request != None:
                msg = {'Not_Command_text_message':'No command included in request.','terminator':'die'}
                if request.has_key("write"):
                    request["write"](simplejson.dumps(msg, ensure_ascii = False).encode('utf8'))
                else:                
                    request.protocol.transport.write(simplejson.dumps(msg, ensure_ascii = False).encode('utf8'))
                    request.protocol.transport.loseConnection()
            return None
        self.params = params
        self.request = request
        if CommandLibrary == None:
            return None
        if hasattr(CommandLibrary,self.params['IDLSocket_ResponseFunction']):
            self.functional=True
            return None
        else:
            msg = {'Not_Command_text_message':'No command included in request.','terminator':'die'}
            if request.has_key("write"):
                request["write"](simplejson.dumps(msg, ensure_ascii = False).encode('utf8'))
            else:                
                request.protocol.transport.write(simplejson.dumps(msg, ensure_ascii = False).encode('utf8'))
                request.protocol.transport.loseConnection()  
        return None
        
    def execute(self,CommandLibrary):
        """
        Executes this command from CommandLibrary's functions
        """
        #print "In class SocketCommand, function execute"
        #print "Params:"
        if self.params.has_key("databomb"):
            #print "---A databomb's data---"
            pass
            #pdb.set_trace()
        else:
            pass
            #print self.params
        p=self.params
        p.update({'request':self.request})
        
        try:
            ThisResponseFunction = getattr(CommandLibrary,
                                           self.params['IDLSocket_ResponseFunction'])
        except AttributeError:
            print ('Missing Socket_ResponseFunction:',
                   self.params['IDLSocket_ResponseFunction'])
        #print "Calling this ResponseFunction:",self.params['IDLSocket_ResponseFunction']
        ThisResponseFunction(p)
        '''
        if self.params['IDLSocket_ResponseFunction'] == 'compile_active_xtsm':
            filenames = []
            for i in range(1):
                name = 'c:\psu_data\profile_stats_%d.txt' % i
                profile.runctx('getattr(CommandLibrary, self.params["IDLSocket_ResponseFunction"])(self.params)',globals(),locals(), filename=name)
            stats = pstats.Stats('c:\psu_data\profile_stats_0.txt')
            for i in range(0, 1):
                stats.add('c:\psu_data\profile_stats_%d.txt' % i)
            stats.sort_stats('cumulative')
            stats.print_stats()
            pass
        else:
            ThisResponseFunction(p)
        print "In class SocketCommand, function execute - End."
        '''
        #print "In class SocketCommand, function execute - End."

        
class GlabServerFactory(protocol.Factory):
    """
    creates the 'factory' class that generates protocols which are executed
    in response to incoming HTTP requests
    """

    def associateCommandQueue(self,command_queue):
        self.command_queue = command_queue
    def associateConnectionManager(self,connection_manager):
        self.connection_manager = connection_manager
    def xstatus(self):
        stat=""
        if hasattr(self,'openConnections'):
            stat+="<Connections>"
            try:            
                for connection in self.openConnections:
                    statd=""
                    statd+="<Connection name='"+connection+"'>"
                    statd+="<From><Origin>"+self.openConnections[connection].request['origin']+"</Origin>"
                    statd+="<Referer>"+self.openConnections[connection].request['referer']+"</Referer>"
                    statd+="</From>"
                    statd+="<TimeElapsed>"+str(round(time.time()-self.openConnections[connection].request['ctime']))+"</TimeElapsed>"
                    if self.openConnections[connection].params.has_key('IDLSocket_ResponseFunction'):
                        statd+="<Command>"+self.openConnections[connection].params['IDLSocket_ResponseFunction']+"</Command>"
                    statd+="</Connection>"
                    stat+=statd
            except:
                stat+="<Updating></Updating>"
            stat+="</Connections>"
        return stat

class Keyboard_Input(basic.LineReceiver):
    """
    Keyboard input protocol - for simultaneous input of python commands
    and browsing of server objects while the server is running
    """
    from os import linesep as delimiter # doesn't seem to work
    if os.name=='nt': delimiter="\n"
    def __init__(self):
        self.pre_e=colorama.Style.BRIGHT+ colorama.Back.RED+colorama.Fore.WHITE
        self.post_e=colorama.Fore.RESET+colorama.Back.RESET+colorama.Style.RESET_ALL
#        self.setRawMode()
    def connectionMade(self):
        pass
    def lineReceived(self, line):
        """
        called when a line of input received - executes and prints result
        or passes error message to console
        """
        rbuffer = StringIO()
        po=sys.stdout
        sys.stdout = rbuffer
        err=False
        if not hasattr(self,"dc"):
            self.dc={"self":self.server}
        try: exec(line,self.dc)
        except Exception as e: err=e
        # remove backeffect on dictionary
        if self.dc.has_key('__builtins__'): 
            del self.dc['__builtins__']
        # update data context
        # remember to restore the original stdout!
        sys.stdout = po
        print '>u> '+line
        if err: out = self.pre_e+str(e)+self.post_e
        else: out = rbuffer.getvalue()
        if out!="": print '>s> ' + out
    def rawDataReceived(self,data):
        print data

class Mediated_StdOut(StringIO):
    """
    class that catches all output, streams into one of several contextual buffers 
    (determined from where the print statement originated)
    and handles printing to consoles
    """
    passthrough=False
    class contextual_buffer():
        """
        a buffer for output separated by context
        """
        def __init__(self,params={}):
            default_params={"lines_retained":20,"linestack":[".\n" for a in range(20)],
                            "prompt":"","display_name":"","bg":colorama.Back.WHITE,
                            "col":colorama.Fore.BLACK,"width":140}
            default_params.update(params)
            for it in default_params: setattr(self,it,default_params[it])
            self.context_col={}
            self.cols=[getattr(colorama.Fore,a) for a in ["BLACK", "RED", "GREEN", "YELLOW", "BLUE", "MAGENTA", "CYAN"]]
            self.col_inc=0
            self.line_term=colorama.Fore.RESET + colorama.Back.RESET + colorama.Style.RESET_ALL
            self.textwrapper = textwrap.TextWrapper()
        def write(self,s):
            self.textwrapper.width=110
            outs=self.textwrapper.wrap(str(s))
            if self.col=="contextualize":
                col=self.color_by_context(s)
            else: col=self.col
            for out in outs:
                self.linestack.pop(0)
                self.linestack.append(col+str(out).strip()+self.line_term)      
        def dump(self,stream):
            stream.write("-"*10+self.display_name+"-"*10+"\n")
            for a in range(self.lines_retained):
                if self.linestack[a]!="\n": 
                    stream.write(self.linestack[a])
                    if self.linestack[a][-1]!="\n": stream.write("\n")
            stream.write(self.prompt)
        def color_by_context(self,s):
            try: col=self.context_col[inspect.stack()[3][3]]
            except KeyError: 
                self.context_col.update({inspect.stack()[3][3]:self.cols[self.col_inc % len(self.cols)]})
                self.col_inc+=1
                col=self.context_col[inspect.stack()[3][3]]
            return col

    default_params={"prompt":"","display_name":"default","bg":colorama.Back.WHITE,"col":"contextualize"}
    received_params={"prompt":">u> ","display_name":"console","bg":colorama.Back.WHITE,"col":colorama.Fore.BLACK}
    buffers={"default":contextual_buffer(default_params),
             "lineReceived":contextual_buffer(received_params)}
    def write(self,s):
        """
        write routine called by print statements
        """
        if self.passthrough:
            sys.stdout=sys.__stdout__
            print s
            sys.stdout=sys.self
            return            
        cb=self._determine_context_buffer(s)
        cb.write(s)
        self.dump()
        
    def dump(self):
        """
        prints all buffers to console
        """
#        self.partial_in=""
#        for line in sys.stdin: 
#        self.partial_in+=sys.stdin.read(1)
        sys.stdout = sys.__stdout__
        os.system('cls')
        for cb in self.buffers.values():
            cb.dump(sys.stdout)
        sys.stdout = self
        
    def _determine_context_buffer(self,s):
        """
        tries to determine a context from the print statement's calling routine 
        """
        try: return self.buffers[inspect.stack()[2][3]]
        except KeyError: return self.buffers['default']
        
    def __del__(self):
        self.passthrough=True
        os.system('cls')
        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__



class GlabPythonManager():
    """
    This is the top-level object; it manages queueing the TCP socket commands,
    and other things as time goes on...
    """
    def __init__(self):
        # intercept print statements
        #sys.stdout = Mediated_StdOut()
        
        if debug:
            print "debug: GlabPythonManager(), __init__"
        # general identifiers
        self.id = str(uuid.uuid1())
        self.hostid = platform.node()# The computer’s network name

        # create a TCP socket listener (called a factory by twisted)
        self.listener = GlabServerFactory()
        self.listener.parent = self

        # tell the twisted reactor what port to listen on and
        # which factory to use for response protocols
        global port
        global wsport        
        self.reactor = reactor
        self.task = task
        try:
            reactor.listenTCP(port, self.listener)
        except error.CannotListenError:
            time.sleep(10)
            reactor.listenTCP(port, self.listener)
        #reactor.addSystemEventTrigger('before','shutdown',server_shutdown)


        # create a Command Queue, Client Manager, and Default Data Context
        self.command_queue = CommandQueue(self)
        self.commandLibrary = CommandLibrary(self)
        self.connection_manager = ConnectionManager(self)
        self.dataContexts = {}
        self.server = self
        self.ip = None
        self.instruments = {}
        self.pxi_time_server_time = 0
        self.active_parser_ip = None
        self.active_parser_port = 0
        self.pxi_time = 0
        self.ALL_DATABOMBS = {}
        self.databombs_for_image_viewer = {}#ALL DATABOMBS
        self.server.databomblist=[]
        #if self.ALL_DATABOMBS.len
        # associate the CommandProtocol as a response method on that socket
        self.listener.protocol = CommandProtocol

        # associate the Command Queue and ClienManager with the socket listener
        self.listener.associateCommandQueue(self.command_queue)
        self.listener.associateConnectionManager(self.connection_manager)
        
        # create a periodic command queue execution
        self.queueCommand = task.LoopingCall(self.command_queue.popexecute)
        self.queueCommand.start(0.03)
        self.initdisplay()

        
        # setup the udp broadcast for peer discovery
        self.multicast = reactor.listenMulticast(udpbport, 
                                                 MulticastProtocol(),
                                                 listenMultiple=True)
        self.multicast.protocol.server = self 
        

        reactor.addSystemEventTrigger('before', 'shutdown', self.stop)
        #self.clientManager.announce_data_listener(self.data_listener_manager.listeners[i],'ccd_image','rb_analysis')
        
        #self.execu = task.LoopingCall(self.commandLibrary.execute_script)
        #self.period = 5.0
        #self.execu.start(self.period)
        
        self.server_ping_period = 5.0 
        reactor.callWhenRunning(self._init_when_running)

        #Moved into Client Manager CP
        # setup the websocket services
        #self.wsfactory = WebSocketServerFactory("ws://localhost:" + 
        #                                        str(wsport),
        #                                        debug=False)
        #self.wsfactory.setProtocolOptions(failByDrop=False)
        #self.wsfactory.parent = self
        #self.wsfactory.protocol = WSServerProtocol
        #self.wsfactory.protocol.commandQueue = self.commandQueue
        #self.wsfactory.protocol.clientManager = self.clientManager
        

        # run initialization script specific to this machine
        try: 
            init_code = server_initializations.initializations[uuid.getnode()]
            if init_code:
                exec(init_code) in globals(), locals()
        except KeyError:
            print ("WARNING:: no supplementary server_initialization data",
                   "present for this machine")

        self.keyboard=Keyboard_Input()
        self.keyboard.server=self
        stdio.StandardIO(self.keyboard)

        #Moved into Client Manager CP
        # listen on standard TCP port
        #self.laud = reactor.listenTCP(wsport, self.wsfactory)
        
        #Testing CP 08/2014
        #pdb.set_trace()
        #self.client_factory = WebSocketClientFactory("ws://10.1.1.178:8084", debug = True)
        #self.client_factory.protocol = WSClientProtocol
        #connectWS(self.client_factory)
        
        
        # the display has been disabled due to conflicts and hangs
        #self.refreshdisplay=task.LoopingCall(self.display.refresh)
        #self.refreshdisplay.start(0.5)

    def send_to_image_viewer(self, databombs):
        #pdb.set_trace()
        packed_message = msgpack.packb({"IDLSocket_ResponseFunction":'set_global_variable_from_socket',
                                        'data_context':'default:10.1.1.136',
                                        'packed_databomb':databombs},
                                         use_bin_type=True)#self.packed_data       
        
        for p in self.server.connection_manager.image_viewer_servers:
            pass
            pass
            self.server.send(packed_message,self.server.connection_manager.image_viewer_servers[p], isBinary=True)

    def _init_when_running(self):
        self.server.id_node = uuid.getnode()
        self.server.ip = socket.gethostbyname(socket.gethostname())
        self.server.name = socket.gethostname()
        dc_name = 'default:'+str(self.server.ip)
        dc = DataContext(dc_name, self.server)
        self.dataContexts.update({dc_name:dc})
        #self.command_queue.add(ServerCommand(self.connection_manager.add_script_server))
        self.command_queue.add(ServerCommand(self.connection_manager.add_image_viewer_server))
        self.command_queue.add(ServerCommand(self.server_ping))
        print ('Listening on ports:',
               str(port), '(standard HTTP),',
               str(wsport) + ' (websocket)',
               str(udpbport) + ' (udp port)')

    def run(self):
        """
        Run the server
        """
        reactor.run()

    def server_shutdown(self):
        port = reactor.listenTCP(portNumber, factory)
        port.stopListening()
        
        connector = reactor.connectTCP(host, port, factory)
        connector.disconnect()

    def announce_data_listener(self,params):
        print "class server, function announce_data_listener"
        self.connection_manager.announce_data_listener(params)

    def stop(self,dummy=None):
        """
        Exit routine; stops twisted reactor
        """
        print "Closing Python Manager"
        self.flush_all()
        for key in self.connection_manager.peer_servers.keys():
            self.connection_manager.peer_servers[key].protocol.sendClose()
        for key in self.connection_manager.script_servers.keys():
            self.connection_manager.script_servers[key].protocol.sendClose()
        self.close_all()
        #self.laud.loseConnection()
        print self.connection_manager.is_connections_closed()
        reactor.stop()
        print "Done"
                
    def flush_all(self):
        for dc in self.dataContexts:
            self.dataContexts[dc].__flush__()

    def close_all(self):
        for dc in self.dataContexts:
            self.dataContexts[dc]._close()

    def server_ping(self):
        """
        sends an identifying message on udp broadcast port
        """
        
        if not hasattr(self,"ping_data"):
            #need to include a list called ping_data - which is updated as needed. by "ping_data fnctions in objects of the server.
        #Nmaely this includes a list of instruments that are attached to the server.
            self.ping_data={"server_id":self.id,
                            "server_name":self.name,
                            "server_ip":self.ip,
                            "server_port":str(wsport),
                            "server_id_node":self.id_node,
                            "server_ping":"ping!"}
        self.ping_data.update({"server_time":time.time()})
        self.multicast.protocol.send(simplejson.dumps(self.ping_data))
        server_command = ServerCommand(self.server_ping)
        reactor.callLater(self.server_ping_period,
                          self.command_queue.add,
                          server_command)

        
    def is_own_ping_broadcast(self,payload_):
        if payload_['server_id'] == self.id:
            return True
        else:
            return False     
        
        
    def catch_ping(self,payload):
        """
        recieves an identifying message on udp broadcast port from other
        servers, and establishes a list of all other servers
        """    
        
        #print "In GlabPythonManager, pong()"
        #pdb.set_trace()
        #self.peer_servers[payload['server_name']]
        '''
        if self.isOwnPingBroadcast(payload):
            pass
            #print "ignoring own broadcast"
        else:
            #print "ping from a peer server. Giving payload to the Client Manager."
        '''
        self.connection_manager.catch_ping(payload)
            
        #try:
        #    self.clientManager.ping(simplejson.loads(payload))
        #except (AttributeError, KeyError): 
        #    self.clientManager.add_peerServer(simplejson.loads(payload))
        #if not hasattr(self,"server_network"): self.server_network={}
        #self.server_network.update({data['server_id']:data})
            
    def broadcast(self,messagestring, UDP=False):
        """
        broadcasts a message to all clients connected through the websockets 
        or by udp broadcast (UDP flag) - the latter will reach all listeners
        """
        if UDP: 
            self.multicast.protocol.send(messagestring)
            return
        try:
            for client in self.wsfactory.openConnections.keys():
                self.wsfactory.openConnections[client].sendMessage(messagestring)
        except AttributeError:
            pass
        
    def send(self,data,address,isBinary=False):
        """
        sends data to a specified address, provided as a sting in the form
        ip:port, a server_id string in the form of a uuid1 provided through
        peer discovery, or by role, in the form of a string "role:XXX" where
        XXX is one of:
            
        the send method will be chosen from among existing websocket connection
        if it exists, or establishes one if it does not.  Returns False if
        failed returns data if there was a response
        
        Should look into the client manager for a valid destination.
        If no valid destinations return false
        """
        #print "In class Server, function, send()"
        #dest = self.resolve_address(address)
        peer_to_send_message = None
        #or uid in self.clientManager.peer_servers:
        #pdb.set_trace()
        #peer_server = self.clientManager.connections[uid]
        #if peer_server.ip == address:
            #peer_to_send_message = peer_server
        #pdb.set_trace()
        return self.connection_manager.send(data,address,isBinary)
        
        #for client in self.clientManager.connections.keys():
            #pdb.set_trace()
            #self.clientManager.connections[client].sendMessage("------From RBAnalysis---Hi")
    
    def resolve_address(self,address):
        """
        attempts to resolve a network address string in the form ip:port, 
        a server_id string in the form of a uuid1 provided through peer
        discovery, or by role, in the form of a string "role:XXX" where XXX
        is one of:
            
        returns an ip:port string if successful, "" if not
        """
        return "Not yet functional"
        if type(address)!=type(""): address=str(address)
        if (len(address.split(":"))==2) and (len(address.split("."))==3):
            return address
        if "role:" in address:
            try:
                return self.clients_by_role[address.split("role:")[1]]
            except AttributeError:
                return ""
        
        
    
    class display():
        pass
    class IORedirector(object):
        '''A general class for redirecting I/O to this Text widget.'''
        def __init__(self,text_area):
            self.text_area = text_area
    class StdoutRedirector(IORedirector):
        '''A class for redirecting stdout to this Text widget.'''
        def write(self,str):
            self.text_area.write(str,False)
    def initdisplay(self):
        # try a wx window control pane
        self.displayapp = wx.PySimpleApp()
        # create a window/frame, no parent, -1 is default ID, title, size
        self.displayframe = wx.Frame(None, -1, "HtmlWindow()", size=(1000, 600))
        # call the derived class, -1 is default ID
        self.display=self.HtmlPanel(self.displayframe,-1,self)
        # show the frame
        #self.displayframe.Show(True)
        myWxAppInstance = self.displayapp
        reactor.registerWxApp(myWxAppInstance)
        splash="<html><body><h2>GLab Python Manager</h2></body></html>"
        print self.xstatus()
        print self.xstatus("html")
        self.display.updateHTML(splash+self.xstatus("html"))
        #tried to redirect stdout to tkinter console, not working:
        #sys.stdout = self.StdoutRedirector( self.display.statuswindow )
    def attach_poll_callback(self,poll,callback,poll_time, onTimeFromNow=False):
        """
        attaches a poll-and-callback event mechanism to the main event-loop
        - used by the Glab_instrument class for data read-outs
        poll and callback should be functions or methods, and poll_time is
        a float representing the time in seconds between polls
        
        the task assigned to the polling is stored in a list 'pollcallbacks'
        attached to the server object, and a reference to this task is returned 
        to the caller
        """
        def pollcallback():
            if poll(): 
                callback()
            else:
                return
        #Will this interfere with the CommandQueue executing "compile_active_xtsm"?
        thistask = task.LoopingCall(pollcallback)
        if not hasattr(self, "pollcallbacks"):
            self.pollcallbacks=[]        
        self.pollcallbacks.append(thistask)
        thistask.start(poll_time)
        return thistask
        
    class HtmlPanel(wx.Panel):
        """
        class HtmlPanel inherits wx.Panel and adds a button and HtmlWindow
        """
        def __init__(self, parent, id, owner):
            self.server=owner            
            # default pos is (0, 0) and size is (-1, -1) which fills the frame
            wx.Panel.__init__(self, parent, id)
            self.SetBackgroundColour("red")
            self.html1 = wx.html.HtmlWindow(self, id, pos=(0,30), size=(1000,600))            
            self.btn1 = wx.Button(self, -1, "Stop Twisted Reactor", pos=(0,0))
            self.btn1.Bind(wx.EVT_BUTTON, self.server.stop)            
            self.btn2 = wx.Button(self, -1, "Refresh", pos=(120,0))
            self.btn2.Bind(wx.EVT_BUTTON, self.refresh)
            wx.EVT_CLOSE(self, lambda evt: reactor.stop())
        def refresh(self, event=None):
            self.html1.SetPage(self.server.xstatus("html"))
        def getHTML(self):
            return self.html1.GetParser().GetSource()
        def updateHTML(self,html):
            self.html1.SetPage(html)
            
    def xstatus(self, xformat="xml"):
        """
        Creates a status snap-shot in XML
        """
        stat='<Status>'
        # Server parameters
        stat += '<Server>'
        stat += '<Host>'
        stat += '<Name>'+ socket.gethostname()+  '</Name>'
        stat += '<IP>' + socket.gethostbyname(socket.gethostname()) + '</IP>'
        stat += '</Host>'
        stat += '<Script>' + main.__file__ + '</Script>'
        stat += '<LocalTime>' + time.asctime() + '</LocalTime>'
        stat += '</Server>'
        # Clients
        stat+=self.connection_manager.xstatus()        
        # Active Connections        
        stat+=self.listener.xstatus()
        # Command Queue
        stat+=self.command_queue.xstatus()
        # Data Contexts
        if hasattr(self,'dataContexts'):
            stat+='<DataContexts>'
            for dc in self.dataContexts.values():
                stat+=dc.xstatus()
            stat+='</DataContexts>'
        stat+='</Status>'
        if xformat=="html":
            # the xsl below transforms the status xml into viewable html
            xsltransform='''
            <xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
            <xsl:template match="Status"><h4>Status:</h4>
                <div><xsl:apply-templates select="Server" /></div>
                <div><xsl:apply-templates select="Clients" /></div>
                <div><xsl:apply-templates select="Connections" /></div>
                <div><xsl:apply-templates select="Commands" /></div>
                <div><xsl:apply-templates select="DataContexts" /></div>
            </xsl:template>
            <xsl:template match="Server"><table border="1px"><tr><td><b>Server:</b></td><td><xsl:value-of select="./Host/Name"/></td><td><xsl:value-of select="./Host/IP"/>:<xsl:value-of select="./Host/Port"/></td><td><b>Local Time:</b></td><td><xsl:value-of select="./LocalTime"/></td></tr></table></xsl:template>
            <xsl:template match="Clients"><table border="1px"><tr><td><b>Recent Clients:</b></td></tr><xsl:apply-templates select="Client"/></table></xsl:template>
            <xsl:template match="Client"><tr><td><xsl:value-of select="./Name"/></td><td><xsl:value-of select="./IP"/></td><td><xsl:value-of select="./LastConnect"/>(s) ago</td><td><xsl:value-of select="./Referer"/></td></tr></xsl:template>     
            <xsl:template match="Connections"><table border="1px"><tr><td><b>Open Connections:</b></td></tr><xsl:apply-templates select="Connection"/></table></xsl:template>
            <xsl:template match="Connection"><tr><td><xsl:value-of select="./From/Referer"/></td><td><xsl:value-of select="./Command"/></td><td><xsl:value-of select="./TimeElapsed"/>s</td><td><xsl:value-of select="./Referer"/></td></tr></xsl:template>     
            <xsl:template match="Commands"><table border="1px"><tr><td><b>Command Queue:</b></td></tr><xsl:apply-templates select="Command"/></table></xsl:template>
            <xsl:template match="Command"><tr><td><xsl:value-of select="./Name"/></td><td><table border='1px'><xsl:apply-templates select="Parameter"/></table></td><td><xsl:value-of select="./TimeElapsed"/>s</td><td><xsl:value-of select="./Referer"/></td></tr></xsl:template>     
            <xsl:template match="Parameter"><tr><td><xsl:value-of select="./Name"/></td><td><xsl:value-of select="./Value"/></td></tr></xsl:template>            
            <xsl:template match="DataContexts"><table border="1px"><tr><td><b>Data Contexts:</b></td></tr><xsl:apply-templates select="DataContext"/></table></xsl:template>
            <xsl:template match="DataContext"><tr><td><xsl:value-of select="./Name"/></td><td><table border='1px'><xsl:apply-templates select="Variable"/></table></td></tr></xsl:template>            
            <xsl:template match="Variable"><tr><td><xsl:value-of select="./Name"/></td><td><xsl:value-of select="./Type"/></td><td><xsl:value-of select="./Value"/></td></tr></xsl:template>
            <xsl:template match="*"><li><i><xsl:value-of select ="local-name()"/>:</i><ul><xsl:apply-templates /></ul></li>
            </xsl:template>
            </xsl:stylesheet>
            '''
            xslt_root = etree.XML(xsltransform)
            transform = etree.XSLT(xslt_root)
            doc = etree.parse(StringIO(stat))
            result_tree = transform(doc)
            stat=str(result_tree)
        return stat

    def __enter__(self):
        return self
        
    def __exit__(self):
        self.save()
        
# do it all:
#with GlabPythonManager() as theBeast:
#    pass
debug=True
active_xtsm = ''

theBeast=GlabPythonManager()
theBeast.run()


