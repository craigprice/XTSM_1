# -*- coding: utf-8 -*-
"""
Created on Fri Dec 19 17:03:46 2014

@author: Daily User
"""

import sys
import time
import uuid
import pdb
import datetime
import msgpack
import msgpack_numpy
msgpack_numpy.patch()#This patch actually changes the behavior of "msgpack"
#specifically, it changes how, "encoding='utf-8'" functions when unpacking
#from twisted.python import log


from autobahn.twisted.websocket import WebSocketClientFactory
from autobahn.twisted.websocket import WebSocketClientProtocol
from twisted.protocols.basic import LineReceiver
from autobahn.twisted.websocket import connectWS
from twisted.internet import protocol
from twisted.internet import reactor
import numpy  
import platform #Access to underlying platforms identifying data     
DEBUG = True
       
TCP_PROTOCOL = None
WS_PROTOCOL = None                            


class MyClientProtocol(WebSocketClientProtocol):

   def onConnect(self, response):
      print("Server connected: {0}".format(response.peer))
      global WS_PROTOCOL
      WS_PROTOCOL = self

   def onOpen(self):
      print("WebSocket connection open.")



   def onMessage(self, payload, isBinary):
      print("Message received")

   def onClose(self, wasClean, code, reason):
      print("WebSocket connection closed: {0}".format(reason))


class ForwardDataProtocol(LineReceiver):#protocol.Protocol
    """
    
    """
    def connectionMade(self):
        
        global TCP_PROTOCOL
        TCP_PROOTOCOL = self
        p=self.transport.getPeer()
        self.peer ='%s:%s' % (p.host,p.port)
        print  datetime.datetime.now(), ":Connected from", self.peer
        
        self.setRawMode()
#    def dataReceived(self,data):
#        if not hasattr(self,"all_data"): self.all_data=""
#        #if len(self.all_data)< 1000: print data
#        self.all_data+=data
#        print "pckt:"+str(len(data))+","+str(len(self.all_data))
#        if len(self.all_data)<self.expected_msg_size:
#            return
#        print numpy.fromstring(self.all_data,numpy.uint16)[0:100]
#        self.transport.loseConnection()
#        pdb.set_trace()
#        #arr = numpy.fromtext(data, dtype = float, sep="\t")
#        #arr =[[float(digit) for digit in line.split('\t')] for line in data.split('\n')]
#        #arr =[[digit for digit in line.split('\t')] for line in data.split('\n')]
#        #arr = numpy.asarray(arr)
#        #print arr
#        #print arr.shape
#        #self.factory.ws_factory.protocol.sendMessage()
#        #self.transport.write('You Sent:\n')
#        #self.transport.write(data)
#        #self.factory.ws_factory.protocol.transport.write(data)
    def rawDataReceived(self, data):
        if not hasattr(self,"ptr"): 
            self.ptr = 0 # init a pointer
            self.num_frames = 0
            print "begin"
        
        str_to_arr = numpy.fromstring(data, numpy.uint8)
        if self.ptr == 0:
	    
            self.num_frames = int(str_to_arr[0])
            if self.num_frames > 8 or self.num_frames == 0:
                print "Error: bad data? self.num_frames = " + str(self.num_frames)
                return
            print "num_frames", self.num_frames
            str_to_arr = str_to_arr[1:]
            self.expected_msg_size = self.num_frames*513*769*2+1#The plus one is the first byte of the ccd data which is = number of frames
            self.all_data=numpy.empty(self.expected_msg_size-1,dtype=numpy.uint8)# define empty array to dump data in
            
        self.all_data[self.ptr:self.ptr+len(str_to_arr)] = str_to_arr
        self.ptr = self.ptr + len(str_to_arr) # fill and advance ptr
        print "pckt:"+str(len(data))+", "+str(len(self.all_data))+ ", "+str(self.ptr)
        if self.ptr<(self.expected_msg_size-1): # if this is not last packet, continue
            print "not last"
            return
        #for s in range(20):
        #    print self.all_data.view(dtype=numpy.uint16).newbyteorder()[s]
        self.all_data=self.all_data.view(dtype=numpy.uint16).newbyteorder() # reverse byteorder to match labview's representation
        self.transport.loseConnection() # drop connection
        time1=time.time()
        #print len(self.all_data)-((self.expected_msg_size-1)/2)  
        
        reshaped_data = self.all_data.view()
        reshaped_data.shape = (self.num_frames, 769, 513)#This should raise an error if it would copy data by reshaping
        #arr = numpy.reshape(self.all_data, (self.num_frames, 769, 513), order = 'C')
        #print "Here"
        #'''
        #pdb.set_trace()
        
        
        print "aquired data"
        pre_packed = {"data":reshaped_data}
        default_databomb_destination_priorities = ["10.1.1.112:8084", "127.0.0.1:8084","127.0.0.1:8083"]
        # some default data-packaging parameters 
        default_data = {"generator":str(self),
                        "generator_instance":str(uuid.uuid1()),
                        "time_served":time.time(), 
                        "begin_acq_time":0,
                        "end_acq_time":0,
                        "destination_priorities":default_databomb_destination_priorities} 
        pre_packed.update(default_data)    
        pre_packed.update({"server_instance":str(self.factory.server_id)})
        pre_packed.update({"server_machine":platform.node()})# The computers network name
        
        pre_packed.update({"shotnumber":0})  #Add a udb multicast protocol to receive the shotnumber updates.
        pre_packed.update({"repnumber":0}) 
        
        try: 
            caller=inspect.stack()[1][3]
        except: 
            caller="Unknown"
        pre_packed.update({"generator":caller})
        
        pre_packed.update({"server_IP_address":uuid.getnode()})
        pre_packed.update({"packed_time":time.time()})  
        pre_packed.update({"packed_by":str(uuid.getnode())+"_ForwardDataProtocol"}) 
        print pre_packed.keys()
        #print pre_packed
        #return
        packed_data = msgpack.packb(pre_packed, use_bin_type=True)
        
        pm = {"IDLSocket_ResponseFunction":"databomb"}
        pm.update({"data_context":"PXI"})
        pm.update({"databomb":packed_data})
        packed_message = msgpack.packb(pm, use_bin_type=True)

        #destination = '10.1.1.124:8084'
	#time1=time.time()
        print "finished packing"
        #'''
        global WS_PROTOCOL
        WS_PROTOCOL.sendMessage(packed_message, isBinary = True)
        
        print "Sent in", time.time()-time1,"s"

    def connectionLost(self,reason):
        print datetime.datetime.now() , ":Disconnected from %s: %s" % (self.peer,reason.value)
        print "Connection Close", time.time(),"s"

   
uid = uuid.uuid1()

#log.startLogging(sys.stdout)

wsClientFactory = WebSocketClientFactory("ws://10.1.1.124:8084", debug = False)
wsClientFactory.setProtocolOptions(failByDrop=False)
wsClientFactory.server_id = uid
wsClientFactory.protocol = MyClientProtocol

connectWS(wsClientFactory)

tcp_factory = protocol.Factory()
tcp_factory.server_id = uid
tcp_factory.protocol = ForwardDataProtocol
reactor.listenTCP(8086, tcp_factory)


reactor.run()