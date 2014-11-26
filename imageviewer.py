# -*- coding: utf-8 -*-
"""
Created on Sun Oct 19 18:27:24 2014

@author: Nate
"""

import numpy as np
import scipy, pdb
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import pyqtgraph.dockarea
import pyqtgraph.console
import sys, inspect, time

class docked_gui():
    """
    Core class for data viewing GUIs.  Uses a set of docks to store controls
    
    subclass this to create new GUIs; each method named _init_dock_XXX will
    create another dock automatically on initialization in alphabetical order
    of the XXX's.  A console is created by default
    """
    _console_namespace={}
    def __init__(self,params={}):
        for k in params.keys():
            setattr(self,k,params[k])
        self._console_namespace.update({"self":self})        
        self.app = QtGui.QApplication([])
        ## Create window with ImageView widget
        self.win = QtGui.QMainWindow()
        self.dock_area = pyqtgraph.dockarea.DockArea()
        self.win.setCentralWidget(self.dock_area)
        #win.setCentralWidget(imv)
        self.win.resize(800,800)
        
        for dock in sorted([m for m in dir(self) if (("_init_dock_" in m))]):
            getattr(self,dock)()
        
    def _init_dock_dockcon(self):
        self.__dock_dockcon = pyqtgraph.dockarea.Dock("Dock Control",size=(500, 50)) ## give this dock the minimum possible size
        self.dock_area.addDock(self.__dock_dockcon, 'top')      ## place d1 atleft edge of dock area (it will fill the whole space since there are no other docks yet)
        self._layout_widg= pg.LayoutWidget()
        label = QtGui.QLabel(" -- DockArea -- ")
        saveBtn = QtGui.QPushButton('Save dock state')
        restoreBtn = QtGui.QPushButton('Restore dock state')
        restoreBtn.setEnabled(False)
        fileField = QtGui.QLineEdit('File')

        self._generate_lad()
        r=0
        for elm in [label,saveBtn,restoreBtn,fileField]:
            self._layout_widg.addWidget(elm,row=r,col=0)
            r+=1
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
        self.dock_area.addDock(self.__dock_console, 'bottom')      ## place d1at left edge of dock area (it will fill the whole space since there are noother docks yet)
        self._console =pyqtgraph.console.ConsoleWidget(namespace=self._console_namespace)
        self.__dock_console.addWidget(self._console)

    def _generate_lad(self):
        self.lad = QtGui.QComboBox()
        self.addable_docks=[]        
        for cbi in ["Add:"]+sorted([m for m in dir(self) if (("_init_dock_" in m))]):
            na=cbi.replace("_init_dock_","")            
            self.addable_docks+=[na]
            self.lad.addItem(na)
           
        QtCore.QObject.connect(self.lad,QtCore.SIGNAL("currentIndexChanged(int)"),self._launch_a_dock)
        self._layout_widg.addWidget(self.lad, row=4, col=0)

    def _launch_a_dock(self):
        """
        fired by launch a new dock combo box
        """
        if str(self.lad.currentText())=="Add:": return
        self.launch_dock(str(self.lad.currentText()))
        self.lad.setCurrentIndex(0)

    def launch_dock(self,name):
        """
        launches a new dock by its type name, will attach as self.__dock_newname
        where newname is the dock type name _X with X an integer
        """
        name.replace("_init_dock_","")
        name=name+"_0"
        while hasattr(self,"__dock_"+name):
            name=str("_".join(name.split("_")[0:-1]))+str(int(name.split("_")[-1])+1)
        setattr(self,"__dock_"+name, pyqtgraph.dockarea.Dock(name, size=(500, 50))) ## give this dock the minimum possible size
        self.dock_area.addDock(getattr(self,"__dock_"+name), 'top')      ## place d1 at left edge of dock area (it will fill the whole space since there are no other docks yet)        

        
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
            #pass            
            #self._generate_random_imgstack()
    
            self.imgstack=params['_console_namespace']['imgstack']
            self._console_namespace.update({"imgstack":params['_console_namespace']['imgstack']})        
        docked_gui.__init__(self,params=params)
        self.imv = pg.ImageView()

    def _start(self):
#        self.win.show()
        self.win.setWindowTitle('Image View')
        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtGui.QApplication.instance().exec_()

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
        x = np.outer((np.arange(nx)-center[0]),np.ones(ny))
        y = np.outer(np.ones(nx),(np.arange(ny)-center[1]))
        r = np.sqrt(np.power(x,2.)+np.power(y,2.))
        phi = np.arctan2(y,x)
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
        self.imv.setImage(self.imgstack, xvals=np.arange(self.imgstack.shape[0]))#.linspace(1., 3., ))
        QtGui.QApplication.instance().exec_() # this start command needs to be here to enable cursors, and hence this must initialize last

    def _init_dock_cursor(self):
        self._dock_cursor = pyqtgraph.dockarea.Dock("Cursor Interface", size=(500,30))
        self.dock_area.addDock(self._dock_cursor, 'bottom')
        self.curs_pos_label = QtGui.QLabel("")
        self._dock_cursor.addWidget(QtGui.QLabel("Cursor Data:"))
        self._dock_cursor.addWidget(self.curs_pos_label)
        
    def _generate_random_imgstack(self):
        ## Create random 3D data set with noisy signals
        img = scipy.ndimage.gaussian_filter(np.random.normal(size=(200, 200)), (5, 5)) * 20 + 100
        img = img[np.newaxis,:,:]
        decay = np.exp(-np.linspace(0,0.3,100))[:,np.newaxis,np.newaxis]
        data = np.random.normal(size=(100, 200, 200))
        data += img * decay
        data += 2
        ## Add time-varying signal
        sig = np.zeros(data.shape[0])
        sig[30:] += np.exp(-np.linspace(1,10, 70))
        sig[40:] += np.exp(-np.linspace(1,10, 60))
        sig[70:] += np.exp(-np.linspace(1,10, 30))        
        sig = sig[:,np.newaxis,np.newaxis] * 3
        data[:,50:60,50:60] += sig
        self.imgstack=data