

from autobahn.twisted.websocket import WebSocketServerProtocol, \
                                       WebSocketServerFactory

from twisted.internet.protocol import DatagramProtocol
import time

class MulticastProtocol(DatagramProtocol):
    """
    Protocol to handle UDP multi-receiver broadcasts - used for servers
    to announce their presence to one another through periodic pings
    """
    def startProtocol(self):
        """
        Join the multicast address
        """
        self.transport.joinGroup("228.0.0.6")

    def send(self,message):
        """
        sends message on udp broadcast channel
        """
        self.transport.write(message, ("228.0.0.6", 8090))

    def datagramReceived(self, datagram_, address):
        """
        called when a udp broadcast is received
        """
        print "datagramreceived",datagram_

            
        


class MyServerProtocol(WebSocketServerProtocol):

   def onConnect(self, request):
      print("Client connecting: {0}".format(request.peer))

   def onOpen(self):
      self.bytes = 0
      #print("WebSocket connection open.")
      self.connect_time = time.time()

   def onMessage(self, payload, isBinary):
      if isBinary:
         pass
         #print "-Binary message received", len(payload)/(1000*1000.0)
         
      else:
         print "Text message received:", payload
      
      
      print    "At local time:........", time.time() - self.connect_time


   def onClose(self, wasClean, code, reason):
      print("WebSocket connection closed: {0}".format(reason))

   '''
   def onMessageFrameData(self, payload):
       #print len(payload[0])/(1000*1000.0)
       #print payload
       self.bytes = self.bytes + len(payload)
       print len(payload)/(1000.0) , 'KB', self.bytes/1000.0, 'KB'
   '''


if __name__ == '__main__':

   import sys

   from twisted.python import log
   from twisted.internet import reactor

   log.startLogging(sys.stdout)

   factory = WebSocketServerFactory("ws://localhost:8086", debug = False)
   factory.protocol = MyServerProtocol

   #multicast = reactor.listenMulticast(8090, MulticastProtocol(),listenMultiple=True)

   reactor.listenTCP(8086, factory)
   reactor.run()