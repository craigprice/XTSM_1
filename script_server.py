from autobahn.twisted.websocket import WebSocketServerProtocol, \
                                       WebSocketServerFactory
import time
import sys

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
         
         
      time.sleep(10)
      print "This is inside the Script Server"
      self.sendMessage("Done!", isBinary)

      ## echo back message verbatim
      #code = compile(payload, '<string>', 'exec')
      #exec code in context

   def onClose(self, wasClean, code, reason):
      print("WebSocket connection closed: {0}".format(reason))



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

   reactor.listenTCP(int(sys.argv[2]), factory)
   reactor.callLater(20, reactor.stop)
   reactor.run()