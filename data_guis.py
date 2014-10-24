    # -*- coding: utf-8 -*-
    
#http://stackoverflow.com/questions/4155052/how-to-display-a-message-box-on-pyqt4
    
    #Need the following block of imports to be before any twisted module imports.

    
import numpy
import scipy, pdb
import inspect, time
import uuid
import pdb
   
from PyQt4 import QtCore
from PyQt4.QtGui import *
import sys

from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import pyqtgraph.dockarea
import pyqtgraph.console

    
import msgpack
import msgpack_numpy
msgpack_numpy.patch()#This patch actually changes the behavior of "msgpack"
#specifically, it changes how, "encoding='utf-8'" functions when unpacking    
    
DEBUG = True    
    
class docked_gui():
    """
    Core class for data viewing GUIs.  Uses a set of docks to store controls
    
    subclass this to create new GUIs; each method named _init_dock_XXX will
    create another dock automatically on initialization in alphabetical order
    of the XXX's.  A console is created by default
    """
    _console_namespace={}
    def __init__(self,params={}):
        if DEBUG: print("class data_guis.docked_gui, func __init__")
        for k in params.keys():
            setattr(self,k,params[k])
        self._console_namespace.update({"self":self})  
        #self._console_namespace.update({"execute_from_socket":self.execute_from_socket})        
        self.app = QtGui.QApplication([])
        ## Create window with ImageView widget
        self.win = QtGui.QMainWindow()
        self.dock_area = pyqtgraph.dockarea.DockArea()
        self.win.setCentralWidget(self.dock_area)
        #win.setCentralWidget(imv)
        self.win.resize(800,800)
        self.command_library = CommandLibrary(self)
        

        
        for dock in sorted([m for m in dir(self) if (("_init_dock_" in m))]):
            pass
            print dock
            getattr(self,dock)()
        
        
        #reactor.run()
            
    #def execute_from_socket(self, command):
        
    def _init_dock_dockcon(self):
        self.__dock_dockcon = pyqtgraph.dockarea.Dock("Dock Control", size=(500, 50)) ## give this dock the minimum possible size
        self.dock_area.addDock(self.__dock_dockcon, 'top')      ## place d1 at left edge of dock area (it will fill the whole space since there are no other docks yet)
        self._layout_widg= pg.LayoutWidget()
        label = QtGui.QLabel(" -- DockArea -- ")
        saveBtn = QtGui.QPushButton('Save dock state')
        restoreBtn = QtGui.QPushButton('Restore dock state')
        restoreBtn.setEnabled(False)
        fileField = QtGui.QLineEdit('File')
        self._layout_widg.addWidget(label, row=0, col=0)
        self._layout_widg.addWidget(saveBtn, row=1, col=0)
        self._layout_widg.addWidget(restoreBtn, row=2, col=0)
        self._layout_widg.addWidget(fileField, row=3, col=0)
        self.__dock_dockcon.addWidget(self._layout_widg)
        state = None
        def save():
            global state
            state = self.dock_area.saveState()
            restoreBtn.setEnabled(True)
        def load():
            global state
            self.dock_area.restoreState(state)
        saveBtn.clicked.connect(save)
        restoreBtn.clicked.connect(load)
    def _init_dock_console(self):
        self.__dock_console = pyqtgraph.dockarea.Dock("Console", size=(500,150))
        self.dock_area.addDock(self.__dock_console, 'bottom')      ## place d1 at left edge of dock area (it will fill the whole space since there are no other docks yet)
        self._console = pyqtgraph.console.ConsoleWidget(namespace=self._console_namespace)
        self.__dock_console.addWidget(self._console)
        
class CommandLibrary():
    """
    The Command Library contains all methods a server can execute in response
    to an HTTP request; the command is specified by name with the 
    "IDLSocket_ResponseFunction" parameter in an HTTP request
    Note: it is the responsibility of each routine to write responses
    _AND CLOSE_ the initiating HTTP communication using
    params>request>protocol>loseConnection()
    """
    def __init__(self, gui):
        if DEBUG: print "class CommandLibrary, func __init__"
        #self.server = server
        self.gui = gui
        
    def execute_from_socket(self,params):
        """
        Executes an arbitrary python command through the socket, and returns the console
        output
        """
        # setup a buffer to capture response, temporarily grab stdio
        params['request']['protocol'].transport.write()
        rbuffer = StringIO()
        sys.stdout = rbuffer
        try: 
            exec params['command'] in self._console_namespace 
            sys.stdout = sys.__stdout__ 
            params['request']['protocol'].transport.write('Python>'+rbuffer.getvalue()+'\n\r')
        except:
            sys.stdout = sys.__stdout__ 
            params['request']['protocol'].transport.write('ERROR>'+rbuffer.getvalue()+'\n\r')
            params['request']['protocol'].transport.loseConnection()
            return
        # exec command has side-effect of adding builtins; remove them
        if self.gui._console_namespace.has_key('__builtins__'): 
            del self.gui._console_namespace['__builtins__']
        # update data context
        # params['request']['protocol'].transport.loseConnection()
        rbuffer.close()
        
    def set_global_variable_from_socket(self,params):
        """
        sets a data element in the console namespace (equivalent to a 'data context')
        """
        if DEBUG: print("class data_guis.docked_gui.CommandLibrary, func set_global_variable_from_socket")
        try:
            del params["IDLSocket_ResponseFunction"]
        except KeyError:
            pass
        try:
            del params["terminator"]
        except KeyError:
            pass
        
        #print params
        packed_elements = {}
        for k,v in params.items():
            if "packed" in k:
                packed_elements.update({k:v})
                
        for k,v in packed_elements.items():
            v = msgpack.unpackb(v)
            params.pop(k)
            k = k.replace('packed','unpacked')
            params.update({k:v})
        if DEBUG: print(params.keys())
        if DEBUG: print(self.gui._console_namespace.keys())
        self.gui._console_namespace.update(params)
        if DEBUG: print(self.gui._console_namespace.keys())
        self.gui._console_namespace['imgstack'] = numpy.asarray(params['unpacked_databomb']['data'])
        self.gui.imv.close()
        #self.gui._init_dock_console()
        #self.gui._init_dock_cursor()
        #self.gui._init_dock_dockcon()
        self.gui._init_dock_zimv()
        #self.imv = pg.ImageView()
        
        self.gui.imv = pg.ImageView()
        self.gui.imv.show()
        self.gui.imv.setImage(self.gui._console_namespace['imgstack'])
        #self.gui.imv = pg.ImageView()
        #self.gui.win.show()
        #self.gui.imv.setImage(self.gui._console_namespace['imgstack'])
        #self.gui.imv = pg.ImageView()
        #self.gui.imv.update()
        #self.gui.app.processEvents()
        #QtGui.QApplication.processEvents()
        
class image_stack_gui(docked_gui):
    """
    Class to generate a gui to analyze image stacks (3d array of data)
    
    image stack can be passed in params as dictionary element with key "imgstack"
    this will be placed into image stack viewer dock, and passed into console namespace
    
    console data may be passed into console using "_console_namespace" entry in params dictionary
    """
    def __init__(self, params={}):
        for k in params.keys():
            setattr(self,k,params[k])
        if not hasattr(self,"imgstack"):
            self._generate_random_imgstack()
            #self.imgstack = np.random.normal(size=(512, 512, 1))
        self._console_namespace.update({"imgstack":self.imgstack})        
        docked_gui.__init__(self,params=params)

        self.imv = pg.ImageView()

   

#    def _start(self):
##        self.win.show()
#        self.win.setWindowTitle('Image View')
#        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
#            QtGui.QApplication.instance().exec_()

    def plot(self,img):
        """
        plots to image viewer
        """
        self.imv.setImage(img)
        
    def generate_coordinates(self, center=None):
        """
        returns arrays for coordinates (x,y,r,phi) in rectangular and cylindrical
        systems consistent with current image size, centered on optional center param
        """
        (nx,ny)=self.imgstack.shape[1:3]
        if center==None: center=(nx/2,ny/2)
        x = numpy.outer((numpy.arange(nx)-center[0]),numpy.ones(ny))
        y = numpy.outer(numpy.ones(nx),(numpy.arange(ny)-center[1]))
        r = numpy.sqrt(numpy.power(x,2.)+numpy.power(y,2.))
        phi = numpy.arctan2(y,x)
        return (x,y,r,phi)

    class cursor():
        """
        Class for cursors in image viewer
        """
        def __init__(self, coord=(0,0)):
            self.x=coord[0]
            self.y=coord[1]
            self.vLine = pg.InfiniteLine(angle=90, movable=True)
            self.hLine = pg.InfiniteLine(angle=0, movable=True)
            self.vLine.setPos(self.x)
            self.hLine.setPos(self.y)
        def addto(self,to):
            to.addItem(self.vLine, ignoreBounds=True)
            to.addItem(self.hLine, ignoreBounds=True)

    def dropCursor(self):
        """
        Drops a cursor at the current position of crosshair
        """
        coord=(self.vLine.getPos()[0],self.hLine.getPos()[1])        
        c=self.cursor(coord=coord)
        c.addto(self.imv)
        try: self.cursors.append(c)
        except: self.cursors=[c]
        

    def _init_dock_zimv(self):
        self.__dock_imv = pyqtgraph.dockarea.Dock("Image View", size=(500,500))
        self.dock_area.addDock(self.__dock_imv, 'top')
        self.imv=pg.ImageView()
        self.__dock_imv.addWidget(self.imv)
        
        #pdb.set_trace()

        self.win.show()

        # attempt to add to context menu (right mouse button) for cursor drop
        self.imv.view.menu.cursorDrop = QtGui.QAction("Drop Cursor", self.imv.view.menu)
        self.imv.view.menu.dropCursor=self.dropCursor
        self.imv.view.menu.cursorDrop.triggered.connect(self.imv.view.menu.dropCursor)
        self.imv.view.menu.addAction(self.imv.view.menu.cursorDrop)
        acs=self.imv.view.menu.subMenus()
        def newSubMenus():
            return [self.imv.view.menu.cursorDrop] + acs
        self.imv.view.menu.subMenus=newSubMenus        
        self.imv.view.menu.valid=False
        self.imv.view.menu.view().sigStateChanged.connect(self.imv.view.menu.viewStateChanged)
        self.imv.view.menu.updateState()


        #cross hair
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.imv.addItem(self.vLine, ignoreBounds=True)
        self.imv.addItem(self.hLine, ignoreBounds=True)
        self.vb=self.imv.view

        def animate(evt):
            if self.imv.playTimer.isActive():
                self.imv.playTimer.stop()
                return
            fpsin=self.imv_fps_in
            fps=float(str(fpsin.text()).split("FPS")[0])
            self.imv.play(fps)            

        #animation controls
        self._imv_layout_widg = pg.LayoutWidget()
        self._imv_layout_widg.addWidget(QtGui.QLabel("Animation:"), row=0, col=0)
        self.imv_anim_b = QtGui.QPushButton('Animate')
        self._imv_layout_widg.addWidget(QtGui.QLabel("Animation:"), row=0, col=0)
        self.imv_fps_in = QtGui.QLineEdit('10 FPS')        
        self._imv_layout_widg.addWidget(self.imv_fps_in, row=0, col=1)
        self._imv_layout_widg.addWidget(self.imv_anim_b, row=0, col=2)
        self.__dock_imv.addWidget(self._imv_layout_widg)
        self.imv_anim_b.clicked.connect(animate)
        
        def mouseMoved(evt):
            pos = evt[0]  ## using signal proxy turns original arguments into a tuple
            mousePoint = self.vb.mapSceneToView(pos)
            self.vLine.setPos(mousePoint.x()-5)
            self.hLine.setPos(mousePoint.y()-5)
            index = (int(mousePoint.x()),int(mousePoint.y()))
            if self.imv.scene.sceneRect().contains(pos):
                try: 
                    self.curs_pos_label.setText("<span style='font-size: 12pt;color: blue'>x=%0.1f,   <span style='color: red'>y=%0.1f</span>,   <span style='color: green'>z=%0.1f</span>" % (mousePoint.x(),mousePoint.y(),self.imgstack[1,index[0],index[1]]))#
                except IndexError: pass        
#        mouseMoved.alabel=self.alabel
        mouseMoved.vLine=self.vLine
        mouseMoved.hLine=self.hLine
        mouseMoved.vb=self.vb
        

        
        proxy = pg.SignalProxy(self.imv.scene.sigMouseMoved, rateLimit=60, slot=mouseMoved)
        ## Display the data and assign each frame a time value from 1.0 to 3.0
        self.imv.setImage(self.imgstack, xvals=numpy.arange(self.imgstack.shape[0]))#.linspace(1., 3., ))
  ###      QtGui.QApplication.instance().exec_() # this start command needs to be here to enable cursors, and hence this must initialize last

    def _init_dock_cursor(self):
        self._dock_cursor = pyqtgraph.dockarea.Dock("Cursor Interface", size=(500,30))
        self.dock_area.addDock(self._dock_cursor, 'bottom')
        self.curs_pos_label = QtGui.QLabel("")
        self._dock_cursor.addWidget(QtGui.QLabel("Cursor Data:"))
        self._dock_cursor.addWidget(self.curs_pos_label)
        
    def _generate_random_imgstack(self):
        ## Create random 3D data set with noisy signals
        img = scipy.ndimage.gaussian_filter(numpy.random.normal(size=(512, 512)), (5, 5)) * 20 + 100
        img = img[numpy.newaxis,:,:]
        decay = numpy.exp(-numpy.linspace(0,0.3,10))[:,numpy.newaxis,numpy.newaxis]
        data = numpy.random.normal(size=(10, 512, 512))
        data += img * decay
        data += 2
        ## Add time-varying signal
        sig = numpy.zeros(data.shape[0])
        sig[3:] += numpy.exp(-numpy.linspace(1,10, 7))
        sig[4:] += numpy.exp(-numpy.linspace(1,10, 6))
        sig[7:] += numpy.exp(-numpy.linspace(1,10, 3))        
        sig = sig[:,numpy.newaxis,numpy.newaxis] * 3
        data[:,50:60,50:60] += sig
        self.imgstack=data
        
def main():

    #app = QApplication(sys.argv)
            
        
    a = image_stack_gui()  # comment 1 line above out, put class defns above
    app=a.app   # ,if necessary
    win=a.win   # ,if necessary
    
    import qtreactor.pyqt4reactor
    qtreactor.pyqt4reactor.install()
    
    last_connection_time = time.time()
    time_last_check = time.time()   
    time_now = time.time()

    
    from twisted.internet import reactor
    from twisted.internet import task
    from autobahn.twisted.websocket import WebSocketServerProtocol
    from autobahn.twisted.websocket import WebSocketServerFactory
    from autobahn.twisted.websocket import WebSocketClientFactory
    from autobahn.twisted.websocket import WebSocketClientProtocol
    from autobahn.twisted.websocket import connectWS
    from autobahn.twisted.websocket import listenWS
    from twisted.internet.protocol import DatagramProtocol
    import twisted.internet.error
    
    #from twisted.python import log

    
        
    class MyServerProtocol(WebSocketServerProtocol):
    
        def onConnect(self, request):
            if DEBUG: print("class data_guis.MyServerProtocol, func onConnect: {0}".format(request.peer))
            
        def onOpen(self):
            if DEBUG: print("class data_guis.MyServerProtocol, func onOpen")
            
        def onMessage(self, payload_, isBinary):
            if DEBUG: print "class data_guis.MyServerProtocol, func onMessage"
            #self.log_message()
            if isBinary:
                payload = msgpack.unpackb(payload_)
                if not payload.has_key('IDLSocket_ResponseFunction'):
                    return None
                try:
                    ThisResponseFunction = getattr(self.factory.app.command_library,
                                               payload['IDLSocket_ResponseFunction'])
                except AttributeError:
                    if DEBUG: print ('Missing Socket_ResponseFunction:',
                                     payload['IDLSocket_ResponseFunction'])
                ThisResponseFunction(payload)
            else:
                print payload_
            
            
        def onClose(self, wasClean, code, reason):
            if DEBUG: print("class data_guis.MyServerProtocol, func onClose: {0}".format(reason))
            server_shutdown()
    
               
    def check_for_main_server():
        global time_last_check
        global time_now
        time_last_check = time_now
        time_now = time.time()
        #print time_last_check, time_now, last_connection_time
        if (time_now - last_connection_time) > 1100000 and (time_now - time_last_check) < 11:
            server_shutdown()
        
        
    def server_shutdown():
        if DEBUG: print "----------------Shutting Down DataGuiServer Now!----------------"
        win.close()
        app.quit()
        reactor.callLater(0.01, reactor.stop)
    

    sys.argv.append('localhost')
    sys.argv.append('9100')
    #sys.argv[0] = file name of this script
    # szys.argv[1] = ip address of this server
    # sys.argv[2] = port to listen on
    factory = WebSocketServerFactory("ws://" + 'localhost' + ":"+str(sys.argv[2]), debug = True)
    factory.setProtocolOptions(failByDrop=False)
    factory.protocol = MyServerProtocol
    try:
        reactor.listenTCP(int(sys.argv[2]), factory)
        a.factory = factory
        factory.app = a
    except twisted.internet.error.CannotListenError:
        server_shutdown()
    

    reactor.run()
    
if __name__ == '__main__':
    main()