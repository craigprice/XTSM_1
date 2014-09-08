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
import io
import os
import platform #Access to underlying platform’s identifying data
from datetime import datetime
import pdb
import __main__ as main

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

import simplejson
import socket
import XTSMobjectify
import DataBomb
import InfiniteFileStream
msgpack_numpy.patch()
import XTSM_Server_Objects
import XTSM_Transforms
import live_content
import xstatus_ready
import file_locations
import server_initializations
import glab_instrument


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
      
if DEBUG_TRACE: sys.settrace(tracefunc)


try:
    port = int(sys.argv[1])
    wsport = int(sys.argv[2])
    udpbport = int(sys.argv[2])
except:
    port = 8083
    wsport = 8084
    udpbport = 8085

NUM_RETAINED_XTSM=100

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
            for elm in args: self.archived.update({elm.keys()[0]:False})       
            for elm in args: self.timeadded.update({elm.keys()[0]:time.time()})
            while len(self)>NUM_RETAINED_XTSM:
                self.heave()
            #pdb.set_trace()                
            
        def archive(self):
            """
            checks if any elements are currently archivable, and archives them
            if any have not yet been archived, and are active
            but exceed the archive_timeout, they are forced deactive and archived.  
            """
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
            if type(elm)==type(0): elm=(elm,self[elm])
            self._write_out(elm)
            self.archived[elm[0]]=True  
            
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
            heavethis=self.popitem(last=False)
            if heavethis[1].isActive(): heavethis[1].deactivate(params={"message":"This element was deactivated when heaved from XTSM_Stack"})
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
        self.transport.joinGroup("228.0.0.5")

    def send(self,message):
        """
        sends message on udp broadcast channel
        """
        self.transport.write(message, ("228.0.0.5", udpbport))

    def datagramReceived(self, datagram, address):
        """
        called when a udp broadcast is received
        """
        print "Datagram received from "+ repr(address) 
        if simplejson.loads(datagram).has_key("server_ping"): 
            #pdb.set_trace()
            self.server.server_pong(datagram)
    
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
     
   #def send(self,payload):
   #    self.sendMessage(payload)

   def hello(self):
       print "Saying hello as client"
         #self.sendMessage(simplejson.dumps({"IDLSocket_ResponseFunction":
         #                                   "set_global_variable_from_socket",
         #                                   "terminator":"die"}))
         #self.sendMessage("df")Test Case
         #self.sendMessage(simplejson.dumps("IDLSocket_Resp"))TestCase
         #self.sendMessage(b"\x00\x01\x03\x04", isBinary = True)
         #self.factory.reactor.callLater(1, hello)

   def onOpen(self):
      print("WebSocket connection opened as client.")
      #peer = self.transport.getPeer()
      #self.clientManagerOwningThisProtocol.add_peer_server_as_server(peer)
      self.hello()

   def onMessage(self, payload, isBinary):
      if isBinary:
         print("Binary message received: {0} bytes".format(len(payload)))
      else:
         print("Text message received: {0}".format(payload.decode('utf8')))

   def onClose(self, wasClean, code, reason):
      print("WebSocket connection closed as Client: {0}".format(reason))

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
        print("Client connecting. Message from server class. : {0}".format(request.peer))

    def onOpen(self):
        print("WebSocket connection open as server.")
        peer = self.transport.getPeer()
        self.clientManagerOwningThisProtocol.add_peer_server_as_server(peer)
        #Moved to add_peer_server in class Client Manager/PeerServer
        #self.ctime = time.time()
        #peer = self.transport.getPeer()
        #self.peer ='%s:%s' % (p.host,p.port)
        #self.ConnectionUID = uuid.uuid1().__str__()
        #self.clientManagerOwningThisProtocol.add_peer_server(peer)
        #pdb.set_trace()
        #try:
        #    self.factory.openConnections.update({self.ConnectionUID:self})
        #except AttributeError: 
        #    self.factory.openConnections = {self.ConnectionUID:self}
        #self.clientManager.connectLog(self)

    def failHandshake(self,code=1001,reason='Going Away'):
        pass        
            
    def onMessage(self, payload, isBinary):
        headerItemsforCommand=['host','origin']
        self.request={k: self.http_headers[k] for k in headerItemsforCommand if k in self.http_headers}
        self.request.update({'ctime':self.ctime,'protocol':self})
        self.request.update({'timereceived':time.time()})
        self.request.update({'write':self.sendMessage})
        # record where this request is coming from
        self.clientManager.elaborateLog(self,self.request)

        if isBinary:
            self.onBinaryMessage(payload)
        else:
            self.onTextMessage(payload)
        #pdb.set_trace()
        ## echo back message verbatim
        #self.sendMessage(payload, isBinary)

    def onBinaryMessage(self,payload):
        pass

    def giveit(self):
        self.sendMessage("adsdasd")

    def onTextMessage(self,payload):
        # we will treat incoming websocket text using the same commandlibrary as HTTP        
        # but expect incoming messages to be JSON data key-value pairs
        try:
            data = simplejson.loads(payload)
        except JSONDecodeError:
            self.transport.write("The server is expecting JSON, not simple text")
            print "The server is expecting JSON, not simple text"
            self.transport.loseConnection()
        # if someone on this network has broadcast a shotnumber change, update the shotnumber in
        # the server's data contexts under _running_shotnumber
        if hasattr(data, "shotnumber"):
            pdb.set_trace() # need to test the below
            #for dc in self.parent.dataContexts:
                #dc['_running_shotnumber']=data['shotnumber']
        data.update({'request':self.request})
        data.update({'socket_type':"Websocket"})
        SC=SocketCommand(params=data, request=self.request, CommandLibrary=self.commandQueue.commandLibrary)
        try:
            self.commandQueue.add(SC)
        except AttributeError:
            self.commandQueue=CommandQueue(SC)
        except:
            self.sendMessage("{'server_console':'Failed to insert SocketCommand in Queue, reason unknown'}")

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed as Server: {0}".format(reason))
        #Should remove peer_server

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
        print datetime.now(), "Connected from", self.peer, "at"
        self.factory.clientManager.connectLog(self)
        self.alldata = ''
    
    def provide_console(self):
        """
        default face of server when contacted with a get request
        """
        #self.transport.write("this is a running XTSM server\n\r\n\r")
        #pdb.set_trace()
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
                self.factory.clientManager.elaborateLog(self,self.request)
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
            self.factory.commandQueue.add(SC)
        except AttributeError:
            self.factory.commandQueue=CommandQueue(SC)
        except:
            self.transport.write(str('Failed to insert SocketCommand in Queue,',
                                     'reason unknown'))
            self.transport.loseConnection()
    # close the connection - should be closed by the command execution
    # self.transport.loseConnection()
    def connectionLost(self,reason):      
        try:
            del self.factory.openConnections[self.ConnectionUID]
        except KeyError:
            pass
        print datetime.now(), "Disconnected from %s: %s" % (self.peer,reason.value)

class DataContext(XTSM_Server_Objects.XTSM_Server_Object):
    """
    A dataContext object stores variable definitions for a Python session
    in a sheltered scope, roughly one for each user, such that independent
    data analysis and experiment control sessions can be run without interferences
    
    .dict contains dictionary of variables and values
    """
    def __init__(self,name):
        self.dict={"__context__":name}
        self.name=name
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
            try: self.dict[item].__flush__()
            except AttributeError: pass
        XTSM_Server_Objects.XTSM_Server_Object.__flush__(self)
        
class ClientManager(XTSM_Server_Objects.XTSM_Server_Object):
    """
    The client manager retains a list of recent clients, their IP addresses,
    and can later be used for permissioning, etc...
    """
    def __init__(self,owner=None):
        self.server=owner
        self.maintenance_task = self.server.task.LoopingCall(self.periodic_maintainence)
        self.maintenance_task.start(120)
        self.peer_servers = {}
        self.clients = {}
        self.clientFactories = {}
        # setup the websocket services
        self.wsServerFactory = WebSocketServerFactory("ws://localhost:" + 
                                                str(wsport),
                                                debug=False)
        self.wsServerFactory.setProtocolOptions(failByDrop=False)
        #self.wsServerFactory.parent = self
        self.wsServerFactory.protocol = WSServerProtocol
        self.wsServerFactory.protocol.clientManagerOwningThisProtocol = self
        #self.wsfactory.protocol.commandQueue = self.commandQueue
        #self.wsfactory.protocol.clientManager = self.clientManager
        # listen on standard TCP port
        self.laud = self.server.reactor.listenTCP(wsport, self.wsServerFactory)
       
    def identify_client(self,protocol):
        """
        attempts to identify a client by the connection protocol 
        
        resident protocols are identified by the ip:port string
        non-resident (ephemoral) protocols are identified by ip address and
        header info
        """
        if protocol.resident:
            return protocol.peer
        pdb.set_trace()
        
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
        pdb.set_trace()
        if not self.client_roles.has_key(request['protocol'].peer):
            self.client_roles.update({request['protocol'].peer:{role:time.time()}})
        else:
            self.client_roles[request['protocol'].peer].update({role:time.time()})
    role_timeouts={}
    def periodic_maintainence(self):
        """
        performs periodic maintenance on connection data with clients
        """
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
    
    
    class GlabClient(XTSM_Server_Objects.XTSM_Server_Object):
        """
        a generic class for clients
        """
        def __init__(self, params={}):
            for key in params: setattr(self,key,params[key])
            self.uuid=str(uuid.uuid4())
            self.time_of_first_contact=time.time()
        def __periodic_maintenance__(self):
            """
            flushes old connections and relations
            """
            pass
        def log_communication(self,request):
            """
            logs a request
            """
            
    class PeerServer(GlabClient):
        """
        class to hold data regarding other XTSM servers on network
        when added open web socket. server connects to this peer server.
        Others open with TCP
        """
        
        def __init__(self):
            ClientManager.GlabClient.__init__(self)
            print "in PeerServer class, __init__()"
            self.connection_time = None
            self.last_broadcast_time = None
            self.server_time = None
            self.ip = None
            self.port = None
            self.connectionUID = None
            self.id = None
            self.name = None
            self.ping_payload = None
            print "End __init__ from PeerServer class"
            #pdb.set_trace()
            
    def add_peer_server_as_client(self,payload_):
        """
        adds a peer server client to the manager's clients
        """
        print "Adding Peer Server as client"
        #pdb.set_trace()
        address = "ws://" + str(payload_['server_ip']) + ":" + str(wsport)
        wsClientFactory = WebSocketClientFactory(address, debug = True)
        wsClientFactory.protocol = WSClientProtocol
        connectWS(wsClientFactory)
        peer_server = self.PeerServer()
        peer_server.ping_payload = payload_
        peer_server.id = payload_['server_id']
        peer_server.name = payload_['server_name']
        peer_server.server_time = payload_['server_time']
        peer_server.ip = payload_['server_ip']
        peer_server.port = wsport
        peer_server.connection_time = time.time()
        peer_server.last_broadcast_time = peer_server.connection_time
        peer_server.connectionUID = uuid.uuid1().__str__()
        self.clientFactories.update({peer_server.connectionUID: wsClientFactory})
        self.peer_servers.update({peer_server.connectionUID:peer_server})
        self.clients.update({peer_server.connectionUID:peer_server})

        '''
        print self.peer_servers
        self.ping_payload = payload
        self.server_id = payload['server_id']
        self.server_name = payload['server_name']
        self.server_time = payload['server_time']
        self.server_ip = payload['server_ip']
        self.server_ping = payload['server_ping']
        connect_string = "ws://" + str(self.server_ip) + ":" + str(wsport)
        print connect_string
        self.client_factory = WebSocketClientFactory(connect_string,
                                                     debug = True)
        self.client_factory.protocol = WSClientProtocol
        connectWS(self.client_factory)
        example = {"IDLSocket_ResponseFunction":"set_global_variable_from_socket","terminator":"die"}
        #self.client_factory.protocol.send(simplejson.dumps(example))
        pdb.set_trace()
        self.peer_servers.update({payload['server_id']:self.PeerServer(payload)})
        print self.peer_servers
        '''
        print "Added Peer Server"
        
    def add_peer_server_as_server(self,peer_):
        peer_server = self.PeerServer()
        peer_server.connection_time = time.time()
        peer_server.ip = peer_.host
        peer_server.port = peer_.port
        peer_server.connectionUID = uuid.uuid1().__str__()
        self.peer_servers.update({peer_server.ConnectionUID:peer_server})
        self.clients.update({peer_server.ConnectionUID:peer_server})
        self.connectLog(peer_server)

    def sendMessageToPeerServer(self,message, peer_server):
        pdb.set_trace()
        peer_server.client_factory.protocol.sendMessage(message)
        
    def isKnownServer(self,payload_):
        #pdb.set_trace()
        print self.peer_servers
        print "in isKnownServer"
        for key in self.peer_servers:
            print self.peer_servers[key].ip, payload_['server_ip']
            if self.peer_servers[key].ip == payload_['server_ip']:
                self.peer_servers[key].id = payload_['server_id']
                self.peer_servers[key].name = payload_['server_name']
                self.peer_servers[key].last_broadcast_time = time.time()
                self.peer_servers[key].server_time = payload_['server_time']
                self.peer_servers[key].ping_payload = payload_
                print "Known Server"
                return True
        print "Unknown Server"
        return False
        
    def ping(self,payload):
        print "In ping()"
        print self.peer_servers
        for key in self.peer_servers:
            print self.peer_servers[key].ping_payload
        self.peer_servers[payload['server_id']].ping_payload = payload
        self.peer_servers[payload['server_id']].server_time = payload['server_time']
        print "End of ping()"
        
class CommandQueue():
    """
    The CommandQueue manages server command executions; it is basically a stack
    of requests generated by incoming requests, combined with a library of
    known commands with which to respond.
    """
    def __init__(self,Command=None,owner=None):
        if Command!=None: self.queue=[Command]
        else: self.queue=[]
        if owner!=None: self.owner=owner
        self.commandLibrary=CommandLibrary(self.owner)
    def add(self,Command):
        self.queue.append(Command)
    def popexecute(self):
        if len(self.queue)>0:
            self.queue.pop().execute(self.commandLibrary)
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
    def __init__(self, owner=None):
        if owner!=None: self.owner=owner
        
    def __determineContext__(self,params):
        try: 
            dcname = params['data_context']
            if not params['request']['protocol'].factory.parent.dataContexts.has_key(dcname):
                raise KeyError
        except KeyError:
            # look for a default data context for this IP address, if none, create
            dcname = "default:"+params['request']['protocol'].peer.split(":")[0]
            if not params['request']['protocol'].factory.parent.dataContexts.has_key(dcname):
                dc = DataContext(dcname)
                params['request']['protocol'].factory.parent.dataContexts.update({dcname:dc})
        return params['request']['protocol'].factory.parent.dataContexts[dcname]
    # below are methods available to external HTTP requests - such as those required
    # by experiment GUI and timing system to implement basic functions of timing system
    # all must accept a single dictionary argument params, containing arguments of HTTP request
    # and an item 'request', which contains data on HTTP request and a reference to the twisted
    # protocol instance handling the response
    def set_global_variable_from_socket(self,params):
        """
        sets a variable by name in the caller's data context
        """
        if params.has_key('IDLSPEEDTEST'):
            srtime = time.time()
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
        for dc in self.owner.dataContexts:
            for key in dc:
                if isinstance(dc[key], glab_instrument.Glab_Instrument):
                    interested_instruments.append(dc[key])
                    
        return interested_instruments
        
        
        #End Test

    def link_to_instrument(self,params):
        try:        
            self.owner.DataBombDispatcher.link_to_instrument(params)
        except:
            raise
        #send back errors - return fail - ie no instrument.

    def get_global_variable_from_socket(self,params):
        """
        gets a variable by name from the caller's data context
        """
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
        params['request']['protocol'].transport.write('pong')
        params['request']['protocol'].transport.loseConnection()

    def get_server_status(self,params):
        params['request']['protocol'].transport.write(params['request']['protocol'].factory.parent.xstatus())
        params['request']['protocol'].transport.loseConnection()

    def get_data_contexts(self,params):
        """
        Gets all data contexts from the server and sends the key under which each is stored.
        """
        for dc in params['request']['protocol'].factory.parent.dataContexts:
            params['request']['protocol'].transport.write(str(dc) + ',')
        params['request']['protocol'].transport.loseConnection()

    def execute_from_socket(self,params):
        """
        Executes an arbitrary python command through the socket, and returns the console
        output
        """
        dc=self.__determineContext__(params).dict
        # setup a buffer to capture response, temporarily grab stdio
        params['request']['protocol'].transport.write('<Python<           '+params['command']+'\n\r')        
        rbuffer = StringIO()
        sys.stdout = rbuffer
        try: exec(params['command'],dc)
        except:
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
        dc=self.__determineContext__(params)
        try: 
            exp_sync=dc.get('_exp_sync')        
        except: 
            exp_sync=Experiment_Sync_Group(self.owner)
            dc.update({'_exp_sync':exp_sync})
        try:
            ax=params['_active_xtsm']
        except KeyError:
            ax=params['active_xtsm']
        ax=XTSM_Transforms.strip_to_active(ax)
        exp_sync.active_xtsm=ax
        params['request']['protocol'].transport.write('Active XTSM updated at ' + time.strftime("%H:%M:%S") + '.' )
        params['request']['protocol'].transport.loseConnection()

    def request_xtsm(self,params):
        """
        Retrieves and returns xtsm by shotnumber
        """
        dc = self.__determineContext__(params)
        message = 'XTSM requested, but shot number does not exist'
        try: 
            exp_sync=dc.get('_exp_sync')
        except:
            self._respond_and_close(params,"XTSM requested, but none exists")
            return
        try:
            reqxtsm = simplejson.dumps({"xtsm_return":simplejson.dumps({"xtsm":exp_sync.compiled_xtsm[int(params['shotnumber'])].XTSM.write_xml(),
                                                                        "shotnumber":int(params['shotnumber'])})})
        except KeyError: 
            try: params['request']['write']('{"server_console":"'+message+'"}')
            except KeyError: 
                params['request']['protocol'].transport.write(message)
                params['request']['protocol'].transport.loseConnection()

        try: params['request']['write'](reqxtsm)
        except KeyError: 
             params['request']['protocol'].transport.write(reqxtsm)
             params['request']['protocol'].transport.loseConnection()

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
        # mark requestor as an XTSM compiler
        self.owner.clientManager.update_client_roles(params['request'],
                                                     'active_XTSM_compiler')
        
        dc=self.__determineContext__(params)
        parent_dc = ''
        if dc.dict.has_key('_exp_sync'): parent_dc=dc
        # next lines look for the first defined data context that has
        # a pxi_data_context element matching 'default:ip address' of pxi system 
        else:
            for name, pdc in params['request']['protocol'].factory.parent.dataContexts.iteritems():
                try:
                    if ((pdc.get('pxi_data_context') == dc.get('__context__')) and
                        pdc.dict.has_key('_exp_sync')):
                        parent_dc = pdc
                except KeyError:
                    pass
        # if none exists, exit and return
        if parent_dc == '':
            self.owner.broadcast('{"server_console": "'+
                                 params['request']['protocol'].peer.split(":")[0] +
                                ' requested timing data, but nothing is ' +
                                'assigned to run on this system."}')
            params['request']['protocol'].transport.loseConnection()
            return
        else:
            # get the experiment synchronization object; retrieve the current shotnumber
            dc=parent_dc
            exp_sync = dc.get('_exp_sync')
            sn = exp_sync.shotnumber
         
            # turn the active_xtsm string into an object
            dc.update({'_active_xtsm_obj':XTSMobjectify.XTSM_Object(exp_sync.active_xtsm)})
            xtsm_object = dc.get('_active_xtsm_obj')

            # parse the active xtsm to produce timingstrings
            self.owner.broadcast('{"server_console": "' +
                                 str(datetime.now()) +
                                 " Parsing started" +
                                 " Shotnumber= " +
                                 str(sn) +
                                 '"}')
            XTSMobjectify.preparse(xtsm_object)
            t0 = time.time()
            parserOutput = xtsm_object.parse(sn)
            tp = time.time()
            XTSMobjectify.postparse(parserOutput)            
            t1 = time.time()
            print "Parse Time: " , t1-t0, "s", "(postparse ", t1-tp, " s)"
            self.owner.broadcast('{"server_console": "' +
                                 str(datetime.now()) +
                                 " Parsing finished" +
                                 " Shotnumber= " +
                                 str(sn) +
                                 '"}')
            self.owner.broadcast('{"parsed_active_xtsm": "' +
                                 str(datetime.now()) +
                                 '"}')

            # send back the timingstrings
            timingstringOutput = str(bytearray(parserOutput.package_timingstrings()))
            params['request']['protocol'].transport.write(timingstringOutput)
            dc.get('_exp_sync').shotnumber = sn + 1
            params['request']['protocol'].transport.loseConnection()

            # setup data listeners for returned data
            if (not dc.dict.has_key('_bombstack')):
                dc.update({'_bombstack':DataBomb.DataBombList()})
            if (not hasattr(dc['_bombstack'],'dataListenerManagers')):
                setattr(dc['_bombstack'],
                        'dataListenerManagers',
                        DataBomb.DataListenerManager())            

            if (not dc.dict.has_key('_analysis_stream')): dc.update({'_analysis_stream':InfiniteFileStream.FileStream(params={'file_root_selector':'analysis_stream'})})
            xtsm_object.XTSM._analysis_stream = dc['_analysis_stream']
            xtsm_object.installListeners(dc['_bombstack'].dataListenerManagers)

            # begin tracking changes to the xtsm_object
            def _changed_xtsm(changedelm):
                self.owner.broadcast('{"xtsm_change":"'+str(sn)+'"}')
            xtsm_object.XTSM.onChange=_changed_xtsm
            
            # attach the xtsm object that generated the outgoing control arrays to the experiment sync's xtsm_stack
            dc['_exp_sync'].compiled_xtsm.update({sn:xtsm_object})
            dc['_exp_sync'].last_successful_xtsm=exp_sync.active_xtsm


    def testparse_active_xtsm(self, params):
        """
        Parses the active_xtsm and posts the processed xtsm in the current data context
        as _testparsed_xtsm, as well as returns it to the requester as an xml string
        """
        dc=self.__determineContext__(params)  # gets the calling command's data context
        parent_dc = ''  # begins looking for the pxi system's data context
        for name, pdc in params['request']['protocol'].factory.parent.dataContexts.iteritems():
            try:
                if dc.get('__context__') == pdc.get('pxi_data_context'):
                    parent_dc = pdc
            except KeyError:
                pass

        if parent_dc=='': parent_dc=dc  # if there is no pxi data context, revert to caller's
        active_xtsm = parent_dc.get('_active_xtsm')  # retrieve the xtsm code currently active
        try: sn = parent_dc.get('_shotnumber')
        except AttributeError: sn = 0

        xtsm_object = XTSMobjectify.XTSM_Object(active_xtsm)
        print datetime.now(), " Parsing started", " Shotnumber= ",sn
        XTSMobjectify.preparse(xtsm_object)
        parserOutput = xtsm_object.parse(sn)
        XTSMobjectify.postparse(parserOutput)
        print datetime.now(), " Parsing finished", " Shotnumber= ",sn

        timingstringOutput = str(bytearray(parserOutput.package_timingstrings()))
        # create timingstring even though it isn't used
        
        parsed_xtsm=xtsm_object.XTSM.write_xml()
        dc.update({'_testparsed_xtsm':parsed_xtsm})
        params['request']['protocol'].transport.write(str(parsed_xtsm))
        params['request']['protocol'].transport.loseConnection()

    def databomb(self, params):
        """
        dumps a messagepack data bomb into current data context's bombstack
        this is a method for data collection hardware to report data into
        the webserver to be stored to disk, associated with the generating XTSM,
        and for analyses to be initiated 
        """
        dc=self.__determineContext__(params)
        if (not dc.dict.has_key('_bombstack')):
            dc.update({'_bombstack':DataBomb.DataBombList()})
        # data listeners should be attached under the bombstack!!
        # if (not dc.dict.has_key('dataListenerManagers')): dc.update({'dataListenerManagers':DataBomb.DataListenerManager()})
        if (not hasattr(dc['_bombstack'],'dataListenerManagers')):
            setattr(dc['_bombstack'],
                    'dataListenerManagers',
                    DataBomb.DataListenerManager())

        dbombnum=dc['_bombstack'].add(DataBomb.DataBombList.DataBomb(params['databomb']))
        params['request']['protocol'].transport.write('databomb ' +
                                                      dbombnum +
                                                      ' updated at ' +
                                                      time.strftime("%H:%M:%S") +
                                                      '.')
        params['request']['protocol'].transport.loseConnection()
        # next line adds a deployment command to the command queue
        self.owner.commandQueue.add(ServerCommand(dc['_bombstack'].deploy,dbombnum))
        
        # mark requestor as a data generator
        pdb.set_trace()

    def stop_listening(self,params):
        """
        Exit routine, stops twisted reactor (abruptly).
        """
        print "Closing Python Manager"
        broadcastMessage = "Python Manager Shutting Down on Request."
        self.owner.broadcast('{"server_console":'+broadcastMessage+'}')
        msg = "Closing Python Manager - Goodbye."
        try:
            params['request']['write'](msg)
        except KeyError: 
             params['request']['protocol'].transport.write(msg)
             params['request']['protocol'].transport.loseConnection()
        self.owner.stop()

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

    def _respond_and_close(params,msg):
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
        self.command=command
        self.args=args
        
    def execute(self, Library=None):
        try: self.command(*self.args)
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
        if not params.has_key('IDLSocket_ResponseFunction'):
            self.functional=False
            if request != None:
                if request.has_key("write"):
                    request["write"]('No command included in request.')
                else:                
                    request.protocol.transport.write('No command included in request.')
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
            if request.has_key("write"):
                request["write"]('No command included in request.')
            else:                
                request.protocol.transport.write('No command included in request.')
                request.protocol.transport.loseConnection()            
        return None
        
    def execute(self,CommandLibrary):
        """
        Executes this command from CommandLibrary's functions
        """
        p=self.params
        p.update({'request':self.request})
        
        try:
            ThisResponseFunction = getattr(CommandLibrary,
                                           self.params['IDLSocket_ResponseFunction'])
        except AttributeError:
            print ('Missing Socket_ResponseFunction:',
                   self.params['IDLSocket_ResponseFunction'])
        ThisResponseFunction(p)

        
class GlabServerFactory(protocol.Factory):
    """
    creates the 'factory' class that generates protocols which are executed
    in response to incoming HTTP requests
    """

    def associateCommandQueue(self,commandQueue):
        self.commandQueue = commandQueue
    def associateClientManager(self,clientManager):
        self.clientManager = clientManager
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

class GlabPythonManager():
    """
    This is the top-level object; it manages queueing the TCP socket commands,
    and other things as time goes on...
    """
    def __init__(self):
        if debug:
            print "debug: GlabPythonManager(), __init__"
        # general identifiers
        self.uuid = str(uuid.uuid1())
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
        #reactor.listenTCP(port, self.listener)
        def hello():
            print ('Listening on ports ' + str(port) +' (standard HTTP),',
            str(wsport) + ' (websocket)',
            str(udpbport) + ' (udp port)')
        reactor.callWhenRunning(hello)

        # create a Command Queue, Client Manager, and Default Data Context
        self.commandQueue = CommandQueue(owner=self)
        self.clientManager = ClientManager(owner=self)
        self.dataContexts = {'default':DataContext('default')}
                
        # associate the CommandProtocol as a response method on that socket
        self.listener.protocol = CommandProtocol

        # associate the Command Queue and ClienManager with the socket listener
        self.listener.associateCommandQueue(self.commandQueue)
        self.listener.associateClientManager(self.clientManager)
        
        # create a periodic command queue execution
        self.queueCommand = task.LoopingCall(self.commandQueue.popexecute)
        self.queueCommand.start(0.03)
        self.initdisplay()

        # setup the udp broadcast for peer discovery
        self.multicast = reactor.listenMulticast(udpbport, 
                                                 MulticastProtocol(),
                                                 listenMultiple=True)
        #pdb.set_trace()
        self.multicast.protocol.server = self        
        self.server_pinger = task.LoopingCall(self.server_ping)
        self.server_ping_period = 5.0
        self.server_pinger.start(self.server_ping_period)

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

    def run(self):
        """
        Run the server
        """
        reactor.run()

    def stop(self,dummy=None):
        """
        Exit routine; stops twisted reactor
        """
        print "Closing Python Manager"
        reactor.stop()        
        self.flush_all()
        self.laud.loseConnection()        
        print "Done"

    def flush_all(self):
        for dc in self.dataContexts:
            self.dataContexts[dc].__flush__()

    def server_ping(self):
        """
        sends an identifying message on udp broadcast port
        """
        if not hasattr(self,"ping_data"):
            #need to include a list called ping_data - which is updated as needed. by "ping_data fnctions in objects of the server.
        #Nmaely this includes a list of instruments that are attached to the server.
            self.ping_data={"server_id":self.uuid,
                            "server_name":socket.gethostname(),
                            "server_ip":socket.gethostbyname(socket.gethostname()),
                            "server_ping":"ping!"}
        self.ping_data.update({"server_time":time.time()})
        self.multicast.protocol.send(simplejson.dumps(self.ping_data))
        
    def isOwnPingBroadcast(self,payload_):
        print payload_['server_id']
        print self.uuid
        if payload_['server_id'] == self.uuid:
            return True
        else:
            return False     
        
    def isKnownServer(self,payload_):
        return self.clientManager.isKnownServer(payload_)
        
        
    def server_pong(self,payload):
        """
        recieves an identifying message on udp broadcast port from other
        servers, and establishes a list of all other servers
        """
        print "In GlabPythonManager, server_pong()"
        #pdb.set_trace()
        #self.peer_servers[payload['server_name']]
        payload = simplejson.loads(payload)
        if self.isOwnPingBroadcast(payload):
            print "ignoring own broadcast"
            return
        if not self.isKnownServer(payload):
            print "Unknown Server. Adding to known peers."
            self.clientManager.add_peer_server_as_client(payload)
            
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
        
    def send(self,data,address):
        """
        sends data to a specified address, provided as a sting in the form
        ip:port, a server_id string in the form of a uuid1 provided through
        peer discovery, or by role, in the form of a string "role:XXX" where
        XXX is one of:
            
        the send method will be chosen from among existing websocket connection
        if it exists, or establishes one if it does not.  Returns False if
        failed returns data if there was a response
        """
        
        #pdb.set_trace()
        #dest = self.resolve_address(address)
        peer_to_send_message = None
        for uid in self.clientManager.peer_servers:
            peer_server = self.clientManager.peer_servers[uid]
            if peer_server.server_ip == address:
                peer_to_send_message = peer_server
        #pdb.set_trace()
        self.clientManager.sendMessageToPeerServer(data,peer_server)
        

    
    
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
    def attach_poll_callback(self,poll,callback,poll_time):
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
            if poll(): callback()
            else: return
        thistask=task.LoopingCall(pollcallback)
        if not hasattr(self, "pollcallbacks"): self.pollcallbacks=[]        
        self.pollcallbacks.append(thistask)
        thistask.start(poll_time)
        return thistask
        
    class HtmlPanel(wx.Panel):
        """
        class HtmlPanel inherits wx.Panel and adds a button and HtmlWindow
        """
        def __init__(self, parent, id, owner):
            self.owner=owner            
            # default pos is (0, 0) and size is (-1, -1) which fills the frame
            wx.Panel.__init__(self, parent, id)
            self.SetBackgroundColour("red")
            self.html1 = wx.html.HtmlWindow(self, id, pos=(0,30), size=(1000,600))            
            self.btn1 = wx.Button(self, -1, "Stop Twisted Reactor", pos=(0,0))
            self.btn1.Bind(wx.EVT_BUTTON, self.owner.stop)            
            self.btn2 = wx.Button(self, -1, "Refresh", pos=(120,0))
            self.btn2.Bind(wx.EVT_BUTTON, self.refresh)
            wx.EVT_CLOSE(self, lambda evt: reactor.stop())
        def refresh(self, event=None):
            self.html1.SetPage(self.owner.xstatus("html"))
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
        stat+=self.clientManager.xstatus()        
        # Active Connections        
        stat+=self.listener.xstatus()
        # Command Queue
        stat+=self.commandQueue.xstatus()
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

