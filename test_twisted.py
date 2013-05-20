# -*- coding: utf-8 -*-
"""
Basic test of a twisted server, starting from an Echo Protocol, then building
a command queue and server.

Created on Thu May 16 18:24:40 2013

TODO:
    finish command library - compile active xtsm
        latter requires integrating parser...
    redirect stdio to console
    execute command queue items on schedule

@author: Nate
"""
from twisted.internet import wxreactor
wxreactor.install()
from twisted.internet import protocol, reactor, task
from lxml import etree
from BaseHTTPServer import BaseHTTPRequestHandler
from StringIO import StringIO
import wx, wx.html
import uuid, time, sys
import socket, __main__ as main
import pdb

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

class EchoProtocol(protocol.Protocol):
    """
    A simple example protocol to echo requests back on HTTP
    """
    def connectionMade(self):
        p=self.transport.getPeer()
        self.peer ='%s:%s' % (p.host,p.port)
        print "Connected from", self.peer
    def dataReceived(self,data):
        print data
        self.transport.write('You Sent:\n')
        self.transport.write(data)
        self.transport.loseConnection()
    def connectionLost(self,reason):
        print "Disconnected from %s: %s" % (self.peer,reason.value)

class CommandProtocol(protocol.Protocol):
    """
    This is the protocol to handle incoming socket commands; it is here to
    listen on a socket, and insert command requests into a command queue - if 
    the request is valid, it will eventually be executed by the queue 
    """
    def connectionMade(self):
        p=self.transport.getPeer()
        self.peer ='%s:%s' % (p.host,p.port)
        self.ConnectionUID=uuid.uuid1().__str__()
        try: self.factory.openConnections.update({self.ConnectionUID:self})
        except AttributeError: self.factory.openConnections={self.ConnectionUID:self}
        print "Connected from", self.peer
        self.factory.clientManager.connectLog(self.peer)
    def dataReceived(self,data):
        dataHTTP=HTTPRequest(data)
        headerItemsforCommand=['host','origin','referer']
        self.request=dict((k, dataHTTP.headers[k]) for k in headerItemsforCommand if k in dataHTTP.headers)
        self.request.update({'timereceived':time.time(),'protocol':self})
        # record where this request is coming from
        self.factory.clientManager.elaborateLog(self.peer,self.request)        
        # strip multipart data from incoming HTTP request
        boundary=dataHTTP.headers['content-type'].split('boundary=')[-1]
        kv=[datas.split('name="')[-1].split('"\n\r\n\r') for datas in data.split('--'+boundary+'--')]
        self.params={k:v.rstrip() for k,v in kv[:-1]}
        # insert request, if valid, into command queue (persistently resides in self.Factory)        
        SC=SocketCommand(self.params,self.request)        
        try:
            self.factory.commandQueue.add(SC)
        except AttributeError:
            self.factory.commandQueue=CommandQueue(SC)
        except:
            self.transport.write('Failed to insert SocketCommand in Queue, reason unknown')
            self.transport.loseConnection()
        # close the connection - should be closed by the command execution
        # self.transport.loseConnection()
    def connectionLost(self,reason):      
        try: del self.factory.openConnections[self.ConnectionUID]
        except KeyError: pass
        print "Disconnected from %s: %s" % (self.peer,reason.value)

class DataContext():
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

class ClientManager():
    """
    The client manager retains a list of recent clients, their IP addresses,
    and can later be used for permissioning, etc...
    """
    def __init__(self):
        self.clients={}
    def connectLog(self,peer):
        self.clients.update({peer:{'lastConnect':time.time()}})
    def elaborateLog(self,peer,request):
        self.clients[peer].update(request)
    def xstatus(self):
        stat='<Clients>'
        for client in self.clients:
            stat+='<Client><Name>'+socket.gethostbyaddr(client.split(":")[0])[0]+'</Name><IP>'+client+'</IP><Referer>'+(self.clients[client])['referer']+'</Referer><LastConnect>'+str(round(-(self.clients[client])['lastConnect']+time.time()))+'</LastConnect></Client>'
        stat+='</Clients>'
        return stat

class CommandQueue():
    """
    The CommandQueue manages server command executions; it is basically a stack
    of requests generated by incoming requests, combined with a library of
    known commands with which to respond.
    """
    def __init__(self,Command=None):
        if Command!=None: self.queue=[Command]
        else: self.queue=[]
        self.commandLibrary=CommandLibrary()
    def add(self,Command):
        self.queue.append(Command)
    def popexecute(self):
        if len(self.queue)>0:
            self.queue.pop().execute(self.commandLibrary)
    def xstatus(self):
        stat=""
        if hasattr(self,'queue'):
            for command in self.queue:
                stat+="<Commands><Command><Name>"+command.params['IDLSocket_ResponseFunction']+"</Name>"
                for param in command.params:
                    stat+="<Parameter><Name>"+param+"</Name><Value><![CDATA["+command.params[param][0:25]+"]]></Value></Parameter>"
                stat+="</Command></Commands>"
        return stat

class CommandLibrary():
    """
    The Command Library contains all methods a server can execute in response
    to an HTTP request; the command is specified by name with the 
    "IDLSocket_ResponseFunction" parameter in an HTTP request
    Note: it is the responsibility of each routine to write responses
    _AND CLOSE_ the initiating HTTP communication using params>request>protocol>loseConnection()
    """
    def __init__(self):
        pass 
    def __determineContext__(self,params):
        try: 
            dcname=params['data_context']
        except KeyError:
            # look for a default data context for this IP address, if none, create
            dcname="default:"+params['request']['protocol'].peer.split(":")[0]
            if not params['request']['protocol'].factory.parent.dataContexts.has_key(dcname):
                dc=DataContext(dcname)
                params['request']['protocol'].factory.parent.dataContexts.update({dcname:dc})
        return params['request']['protocol'].factory.parent.dataContexts[dcname]
    # below are methods available to external HTTP requests - such as those required
    # by experiment GUI and timing system to implement basic functions of timing system
    # all must accept a single dictionary argument params, containing arguments of HTTP request
    # and an item 'request', which contains data on HTTP request and a reference to the twisted
    # protocol instance handling the response
    def set_global_variable_from_socket(self,params):
        try: 
            varname=set(params.keys()).difference(set(['IDLSocket_ResponseFunction','terminator','request','data_context'])).pop()
        except KeyError:
            params['request']['protocol'].transport.write('Error: Set_global requested, but no Variable Supplied')
            params['request']['protocol'].transport.loseConnection()
        dc=self.__determineContext__(params)
        dc.update({varname:params[varname]})
        params['request']['protocol'].transport.loseConnection()
    def get_global_variable_from_socket(self,params):
        try: 
            varname=params['variablename']
        except KeyError:
            params['request']['protocol'].transport.write('Error: get_global requested, but no variable name supplied')
            params['request']['protocol'].transport.loseConnection()
        dc=self.__determineContext__(params)
        params['request']['protocol'].transport.write(str(dc.get[varname]))
        params['request']['protocol'].transport.loseConnection()
    def ping_idl_from_socket(self,params):
        params['request']['protocol'].transport.write('pong')
        params['request']['protocol'].transport.loseConnection()
    def get_server_status(self,params):
        params['request']['protocol'].transport.write(params['request']['protocol'].factory.parent.xstatus())
        params['request']['protocol'].transport.loseConnection()
    def execute_from_socket(self,params):
        dc=self.__determineContext__(params).dict
        # setup a buffer to capture response, temporarily grab stdio
        params['request']['protocol'].transport.write('<IDL<           '+params['command']+'\n\r')        
        rbuffer = StringIO()
        sys.stdout = rbuffer
        try: exec(params['command'],dc)
        except:
            params['request']['protocol'].transport.write('>IDL>   ERROR\n\r')
            params['request']['protocol'].transport.loseConnection()
            return
        # exec command has side-effect of adding builtins; remove them
        if dc.has_key('__builtins__'): 
            del dc['__builtins__']
        # update data context
        # remember to restore the original stdout!
        sys.stdout = sys.__stdout__   
        # output the response buffer to the HTTP request
        params['request']['protocol'].transport.write('>IDL>   '+rbuffer.getvalue()+'\n\r')
        params['request']['protocol'].transport.loseConnection()
        rbuffer.close()
    def compile_active_xtsm(self,params):
        pass
        
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
                request.protocol.transport.write('No command included in request.')
                request.protocol.transport.loseConnection()
            return None
        self.params=params
        self.request=request
        if CommandLibrary==None:
            return None
        if hasattr(CommandLibrary,self.params['IDLSocket_ResponseFunction']):
            self.functional=True
            return None
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
            getattr(CommandLibrary,self.params['IDLSocket_ResponseFunction'])(p)
        except AttributeError:
            print 'Missing Socket_ResponseFunction: ', self.params['IDLSocket_ResponseFunction']

class GlabServerFactory(protocol.Factory):
    """
    creates the 'factory' class that generates protocols which are executed
    in response to incoming HTTP requests
    """

    def associateCommandQueue(self,commandQueue):
        self.commandQueue=commandQueue
    def associateClientManager(self,clientManager):
        self.clientManager=clientManager
    def xstatus(self):
        stat=""
        if hasattr(self,'openConnections'):
            stat+="<Connections>"
            for connection in self.openConnections:
                stat+="<Connection name='"+connection+"'>"
                stat+="<From><Origin>"+self.openConnections[connection].request['origin']+"</Origin>"
                stat+="<Referer>"+self.openConnections[connection].request['referer']+"</Referer>"
                stat+="</From>"
                stat+="<TimeElapsed>"+str(round(time.time()-self.openConnections[connection].request['timereceived']))+"</TimeElapsed>"
                if self.openConnections[connection].params.has_key('IDLSocket_ResponseFunction'):
                    stat+="<Command>"+self.openConnections[connection].params['IDLSocket_ResponseFunction']+"</Command>"
                stat+="</Connection>"
            stat+="</Connections>"
        return stat

class GlabPythonManager():
    """
    This is the top-level object; it manages queueing the TCP socket commands,
    and other things as time goes on...
    """
    def __init__(self):
        # create a Command Queue, Client Manager, and Default Data Context
        self.commandQueue=CommandQueue()
        self.clientManager=ClientManager()
        self.dataContexts={'default':DataContext('default')}
        # create a TCP socket listener (called a factory by twisted)
        self.listener=GlabServerFactory()
        self.listener.parent=self
        # associate the CommandProtocol as a response method on that socket
        self.listener.protocol=CommandProtocol
        # tell the twisted reactor what port to listen on, and which factory to use for response protocols
        reactor.listenTCP(8082, self.listener)
        def hello(): print 'Listening on port', 8082
        reactor.callWhenRunning(hello)
        # associate the Command Queue and ClienManager with the socket listener
        self.listener.associateCommandQueue(self.commandQueue)
        self.listener.associateClientManager(self.clientManager)
        # create a periodic command queue execution
        self.queueCommand=task.LoopingCall(self.commandQueue.popexecute)
        self.queueCommand.start(0.03)
        self.initdisplay()
        self.refreshdisplay=task.LoopingCall(self.display.refresh)
        self.refreshdisplay.start(0.5)
        # run the main response loop through twisted framework
        reactor.run()
    def stop(self,dummy=None):
        """
        Exit routine; stops twisted reactor
        """
        print "Closing Python Manager"
        reactor.stop()        
        print "Done"
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
        self.displayframe.Show(True)
        myWxAppInstance = self.displayapp
        reactor.registerWxApp(myWxAppInstance)
        splash="<html><body><h2>GLab Python Manager</h2></body></html>"
        print self.xstatus()
        print self.xstatus("html")
        self.display.updateHTML(splash+self.xstatus("html"))
        #tried to redirect stdout to tkinter console, not working:
        #sys.stdout = self.StdoutRedirector( self.display.statuswindow )
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
        stat+='<Server><Host><Name>'+socket.gethostname()+'</Name><IP>'+socket.gethostbyname(socket.gethostname())+'</IP></Host><Script>'+main.__file__+'</Script><LocalTime>'+time.asctime()+'</LocalTime></Server>'
        # Clients
        stat+=self.clientManager.xstatus()        
        # Active Connections        
        stat+=self.listener.xstatus()
        # Command Queue
        stat+=self.commandQueue.xstatus()
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
            </xsl:template>
            <xsl:template match="Server"><table border="1px"><tr><td><b>Server:</b></td><td><xsl:value-of select="./Host/Name"/></td><td><xsl:value-of select="./Host/IP"/>:<xsl:value-of select="./Host/Port"/></td><td><b>Local Time:</b></td><td><xsl:value-of select="./LocalTime"/></td></tr></table></xsl:template>
            <xsl:template match="Clients"><table border="1px"><tr><td><b>Recent Clients:</b></td></tr><xsl:apply-templates select="Client"/></table></xsl:template>
            <xsl:template match="Client"><tr><td><xsl:value-of select="./Name"/></td><td><xsl:value-of select="./IP"/></td><td><xsl:value-of select="./LastConnect"/>(s) ago</td><td><xsl:value-of select="./Referer"/></td></tr></xsl:template>     
            <xsl:template match="Connections"><table border="1px"><tr><td><b>Open Connections:</b></td></tr><xsl:apply-templates select="Connection"/></table></xsl:template>
            <xsl:template match="Connection"><tr><td><xsl:value-of select="./From/Referer"/></td><td><xsl:value-of select="./Command"/></td><td><xsl:value-of select="./TimeElapsed"/>s</td><td><xsl:value-of select="./Referer"/></td></tr></xsl:template>     
            <xsl:template match="Commands"><table border="1px"><tr><td><b>Command Queue:</b></td></tr><xsl:apply-templates select="Command"/></table></xsl:template>
            <xsl:template match="Command"><tr><td><xsl:value-of select="./Name"/></td><td><table border='1px'><xsl:apply-templates select="Parameter"/></table></td><td><xsl:value-of select="./TimeElapsed"/>s</td><td><xsl:value-of select="./Referer"/></td></tr></xsl:template>     
            <xsl:template match="Parameter"><tr><td><xsl:value-of select="./Name"/></td><td><xsl:value-of select="./Value"/></td></tr></xsl:template>            
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

# do it all:
theBeast=GlabPythonManager()