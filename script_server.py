from autobahn.twisted.websocket import WebSocketServerProtocol, \
                                       WebSocketServerFactory
import time
import sys
import simplejson


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
         
         
      time.sleep(1)
      print "This is inside the Script Server"
      #self.sendMessage("Done!", isBinary)

      # echo back message verbatim
      print "compile...."
      code = compile(payload, '<string>', 'exec')
      code_locals = {}
      exec code in code_locals
      print payload
      print code_locals
      data = simplejson.dumps(code_locals['output_from_script'])
      print data
      self.sendMessage(data, isBinary=False)

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
   reactor.callLater(60*1, reactor.stop)
   reactor.run()