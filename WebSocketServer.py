import pdb,inspect
#from twisted.internet.protocol import Protocol, Factory
import XTSMserver
#theBeast=XTSMserver.GlabPythonManager()
from autobahn.twisted.websocket import WebSocketServerProtocol, \
                                       WebSocketServerFactory

class MyServerProtocol(WebSocketServerProtocol):

    def onConnect(self, request):
        print 'hey'
        print("Client connecting: {0}".format(request.peer))

    def onOpen(self):
        print("WebSocket connection open.")

    def failHandshake(self,code=1001,reason='Going Away'):
        pass        
#        pdb.set_trace() 
            
    def onMessage(self, payload, isBinary):
        if isBinary:
            print("Binary message received: {0} bytes".format(len(payload)))
        else:
            print("Text message received: {0}".format(payload.decode('utf8')))

        ## echo back message verbatim
        self.sendMessage(payload, isBinary)

#    def onMessageBegin(self, payload, isBinary):
#        print("message began")

    def onClose(self, wasClean, code, reason):
#        pdb.set_trace()
        print("WebSocket connection closed: {0}".format(reason))


if __name__ == '__main__':

    import sys

    from twisted.python import log
#    from twisted.internet import reactor

#    pdb.set_trace()
    log.startLogging(sys.stdout)

    factory = WebSocketServerFactory("ws://localhost:8084", debug = False)
    factory.setProtocolOptions(failByDrop=False)
    factory.protocol = MyServerProtocol

    XTSMserver.reactor.listenTCP(8084, factory)

    XTSMserver.reactor.run()
    #print inspect.getsourcelines(factory.protocol._dataReceived)