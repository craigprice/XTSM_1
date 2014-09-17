from autobahn.twisted.websocket import WebSocketServerProtocol, \
                                       WebSocketServerFactory
import time
import sys
import simplejson
import pdb
from twisted.internet.protocol import DatagramProtocol
import uuid
import glab_instrument

from twisted.internet import task

last_connection_time = time.time()
time_last_check = time.time()
time_now = time.time()

class MyServerProtocol(WebSocketServerProtocol):

   def onConnect(self, request):
      print("Client connecting: {0}".format(request.peer))

   def onOpen(self):
      print("WebSocket connection open.")

   def onMessage(self, payload, isBinary):
      if isBinary:
         print("Binary message received: {0} bytes".format(len(payload)))
      else:
         print("Text message received: {0}".format(payload.decode('utf8')))
         
         
      print "This is inside the Script Server"
      code_locals = {}
      #self.sendMessage("Done!", isBinary)

      # echo back message verbatim
      print "payload:"
      print payload
      print "compile...."
      #payload = "self.dataContexts['default'].update({'Test_instrument':glab_instrument.Glab_Instrument(params={'server':self,'create_example_pollcallback':True})})"
      try:
          code = compile(payload, '<string>', 'exec')
      except:
          print "compile unsuccessful"
          code_locals.update({'output_from_script':'None','terminator':'die'})
          data = simplejson.dumps(code_locals)
          self.sendMessage(data, isBinary=False)
          
      print "compile successful"
      exec code in code_locals
      print payload
      print code_locals
      data = simplejson.dumps(code_locals['output_from_script'])
      print data
      self.sendMessage(data, isBinary=False)

   def onClose(self, wasClean, code, reason):
      print("WebSocket connection closed: {0}".format(reason))

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

    def datagramReceived(self, datagram_, address):
        """
        called when a udp broadcast is received
        Add functionality for "catching the ping and pinging back to tell the
        main server that I am still ready and not in_use
        """
        #print "Datagram received from "+ repr(address) 
        datagram = simplejson.loads(datagram_)
        port = address[1]
        if datagram['server_uuid_node'] == uuid.getnode() and port == 8085 and datagram.has_key("server_ping"): 
            #pdb.set_trace()
            global last_connection_time
            last_connection_time = time.time()
            
    


def server_shutdown():
    print "------------------Shutting Down ScriptServer Now!------------------"
    reactor.callLater(0.01, reactor.stop)
       
def check_for_main_server():
    global time_last_check
    global time_now
    time_last_check = time_now
    time_now = time.time()
    #print time_last_check, time_now, last_connection_time
    if (time_now - last_connection_time) > 11 and (time_now - time_last_check) < 11:
        server_shutdown()
        

if __name__ == '__main__':


   from twisted.python import log
   from twisted.internet import reactor

   log.startLogging(sys.stdout)
   #sys.argv.append('script_server')
   sys.argv.append('localhost')
   sys.argv.append('9000')

    # sys.argv[0] = file name of this script
    # sys.argv[1] = ip address of this server
    # sys.argv[2] = port to listen on
   factory = WebSocketServerFactory("ws://" + 'localhost' + ":"+str(sys.argv[2]), debug = True)
   factory.setProtocolOptions(failByDrop=False)
   factory.protocol = MyServerProtocol
   
   udpbport = 8085
   multicast = reactor.listenMulticast(udpbport, MulticastProtocol(),listenMultiple=True)

   check = task.LoopingCall(check_for_main_server)
   call_period = 1#sec
   check.start(call_period)

   reactor.listenTCP(int(sys.argv[2]), factory)
   #reactor.callLater(60*30, reactor.stop)
   reactor.run()