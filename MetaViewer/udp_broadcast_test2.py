# -*- coding: utf-8 -*-
"""
Created on Sat Aug 09 16:40:41 2014

@author: Nate
"""

from twisted.internet import reactor, task

from twisted.internet.protocol import DatagramProtocol

class MulticastPingClient(DatagramProtocol):

    def startProtocol(self):
        # Join the multicast address, so we can receive replies:
        self.transport.joinGroup("228.0.0.5")
        # Send to 228.0.0.5:8005 - all listeners on the multicast address
        # (including us) will receive this message.
        self.queueCommand=task.LoopingCall(self.ping)
        self.queueCommand.start(1.0)

    def ping(self):
        self.transport.write('Client: Pinged', ("228.0.0.5", 8085))

    def datagramReceived(self, datagram, address):
        print "Datagram %s received from %s" % (repr(datagram), repr(address))


reactor.listenMulticast(8085, MulticastPingClient(), listenMultiple=True)
reactor.run()