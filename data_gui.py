    # -*- coding: utf-8 -*-
    
#http://stackoverflow.com/questions/4155052/how-to-display-a-message-box-on-pyqt4
    
    #Need the following block of imports to be before any twisted module imports.

    
import numpy
import scipy
import pdb
import inspect, time
import tables
import uuid
import datetime
import pdb

import os
import colorama
from StringIO import StringIO
   
import PyQt4
from PyQt4 import QtCore
from PyQt4.QtGui import *
import sys
from PyQt4.QtCore import QSettings

from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph
import pyqtgraph.dockarea
#from pyqtgraph.dockarea.Dock import DockLabel
import pyqtgraph.console

import msgpack
import msgpack_numpy
msgpack_numpy.patch()#This patch actually changes the behavior of "msgpack"
#specifically, it changes how, "encoding='utf-8'" functions when unpacking    
import pylab
import numpy
import scipy.optimize
import simplejson
    
DEBUG = True
global TIMING
TIMING = 1416876428
    

import gnosis.xml.objectify # standard package used for conversion of xml structure to Pythonic objects, also core starting point for this set of routines
import XTSMobjectify    
    
class CCDImage(tables.IsDescription):
    short_256_description = tables.StringCol(256)
    shotnumber = tables.Int64Col()
    image_number = tables.Int64Col()
    ccd_array = tables.FloatCol(shape=(512,512))

class ScopeTrace(tables.IsDescription):
    short_256_description = tables.StringCol(256)
    shotnumber = tables.Int64Col()
    ccd_array = tables.Int64Col(600)

class DataStorage():
    
    def __init__(self):       
        self.id = str(uuid.uuid4())
        self.filename = 'filename'
        today = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d')
        self.location_root = '..\\psu_data\\' + today + '\\hdf5_heap\\'
        filename = self.location_root + str(self.id) + '.h5'
        
        try:
            self.h5file = tables.open_file(filename,
                                 mode="a",
                                 title='title',
                                 driver="H5FD_SEC2",
                                 NODE_CACHE_SLOTS=0)
        except IOError:#Folder doesn't exist, then we make the day's folder.
            os.makedirs(self.location_root)
            self.h5file = tables.open_file(filename,
                                 mode="a",
                                 title='title',
                                 driver="H5FD_SEC2",
                                 NODE_CACHE_SLOTS=0)
                             
        self.group = self.h5file.create_group('/','data_group','CCD Scope data')
        self.table = self.h5file.create_table(self.group, 'ccd_data', CCDImage , "CCD Data")  
        



class CommandLibrary():
    """
    The Command Library contains all methods a server can execute in response
    to an HTTP request; the command is specified by name with the 
    "IDLSocket_ResponseFunction" parameter in an HTTP request
    Note: it is the responsibility of each routine to write responses
    _AND CLOSE_ the initiating HTTP communication using
    params>request>protocol>loseConnection()
    """
    def __init__(self):
        if DEBUG: print "class CommandLibrary, func __init__"
        
        self.data_storage = DataStorage()
        
    def execute_from_socket(self,params):
        """
        Executes an arbitrary python command through the socket, and returns the console
        output
        """
        if DEBUG: print("class data_guis.docked_gui.CommandLibrary, func execute_from_socket")
        if DEBUG: print("params.keys:", params.keys())
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
    def close_H5_create_new(self):
        self.data_storage.h5file.close()
        self.data_storage = DataStorage() 

    def check_consistency_with_xtsm(self, params):
        xtsm = '<XTSM>'+params['analysis_space_xtsm']+'</XTSM>'
        xtsm_object = XTSMobjectify.XTSM_Object(xtsm)
        self.factory.gui._console_namespace.update({"xtsm_object":xtsm_object})
        pass
    
    
    def plot_and_save_fluoresence_image(self,params):
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
        if DEBUG: print("Params.keys:", params.keys())
        packed_elements = []
        unpacked_databombs = {}
        for k,v in params.items():
            print k
            if "packed_databomb" in k:
                print k
                db = msgpack.unpackb(params[k])
                m = numpy.asarray(db['data'])
                g = self.factory.gui
                g.imgstack = numpy.concatenate((g.imgstack,[m[1]]), axis=0)
                
                new_image = self.data_storage.table.row
                new_image['short_256_description'] = 'with atoms'
                new_image['shotnumber'] = int(db['shotnumber'])
                new_image['image_number'] = 1
                new_image['ccd_array'] = m[1]
                new_image.append()
                
             
                
                self.data_storage.table.flush()
                
                if self.data_storage.table.nrows == 400: 
                    self.close_H5_create_new()
                #table = self.data_storage.h5file.root.data_group.ccd_data
                #g.imgstack = numpy.concatenate((g.imgstack,[corrected_image]), axis=0)
                #g.imgstack = numpy.concatenate((g.imgstack,[log_corr]), axis=0)
                #imgstack = [x['ccd_array'] for x in table.iterrows() ]#if x['short_256_description'] == 'Corrected Image']
                g.plot(g.imgstack)
                
               
                def gaussian_jz(x,
                             offset,w,a,c):
                    
                    '''
                    Define single peak gaussian function, parameters are listed below:
                    x, variable; offset; w, 1/sqrt(e) width ; a amplitude of the peak; c, peak center.
                    FWHM=2.3548*w
                    '''
                    return offset + a*numpy.exp(-(x-c)**2./(2.*w**2.))
            




                def gaussian(height, center_x, center_y, width_x, width_y):
                    """Returns a gaussian function with the given parameters"""
                    width_x = float(width_x)
                    width_y = float(width_y)
                    return lambda x,y: height*numpy.exp(
                                -(((center_x-x)/width_x)**2+((center_y-y)/width_y)**2)/2)
                    
                def moments(data):
                    """Returns (height, x, y, width_x, width_y)
                    the gaussian parameters of a 2D distribution by calculating its
                    moments """
                    total = data.sum()
                    X, Y = numpy.indices(data.shape)
                    x = (X*data).sum()/total
                    y = (Y*data).sum()/total
                    col = data[:, int(y)]
                    width_x = numpy.sqrt(abs(abs((numpy.arange(col.size)-y)**2*col).sum()/col.sum()))
                    row = data[int(x), :]
                    width_y = numpy.sqrt(abs(abs((numpy.arange(row.size)-x)**2*row).sum()/row.sum()))
                    height = data.max()
                    return height, x, y, width_x, width_y
                 
                def fitgaussian(data):
                    """Returns (height, x, y, width_x, width_y)
                    the gaussian parameters of a 2D distribution found by a fit"""
                    params = moments(data)
                    print params
                    errorfunction = lambda p: numpy.ravel(gaussian(*p)(*numpy.indices(data.shape)) -data)
                    p, success = scipy.optimize.leastsq(errorfunction, params)
                    print p
                    print success
                    return p
                    
                
                '''
                (height, center_x, center_y, width_x, width_y) = fitgaussian(m[1])
                fit = gaussian(*(height, center_x, center_y, width_x, width_y))
            
                #scipy.integrate.dblquad()
            
                
                t = pylab.text(0.95, 0.05, """
                x : %.1f
                y : %.1f
                width_x : %.1f
                width_y : %.1f""" %(center_x, center_y, width_x, width_y),
                fontsize=16, horizontalalignment='right',
                verticalalignment='bottom')
                print t.get_text()
                conversion_to_um = 5.2
                print 'Fitting: Double Gaussian.'
                print 'height =', float(height), 'counts'
                print 'center_x =', float(center_x), 'pixels', float(center_x) * conversion_to_um, 'micron'
                print 'center_y =', float(center_y), 'pixels', float(center_y) * conversion_to_um, 'micron'
                print 'sigma - width_x =', float(width_x), 'pixels', float(width_x) * conversion_to_um, 'micron'
                print 'sigma - width_y =', float(width_y), 'pixels', float(width_y) * conversion_to_um, 'micron'
                print 'FWHM - width_x =', float(2.3548*width_x), 'pixels', float(2.3548*width_x) * conversion_to_um, 'micron'
                print 'FWHM - width_y =', float(2.3548*width_y), 'pixels', float(2.3548*width_y) * conversion_to_um, 'micron'
                print "Atoms, 2D = ", float(height) * float(width_x) * float(width_y) * 303 * pow(10,-6) * 0.7,'\n'
                
            

                    
            
                #popt,popv = curve_fit(func, xdata, ydata, (-12.,12.,15.,25.,6.,5.,50.))
               '''
            
                try:
                    ydata = m[1][212]
                    g._dock_1D_plot.plot.plot(m[1][212])
                    #center = center_x
                except IndexError:
                    ydata =m[1][234]
                    g._dock_1D_plot.plot.plot(m[1][243])
                    center = 243
                '''    
                xdata = numpy.asarray(list(xrange(len(ydata))))
                popt,popv = scipy.optimize.curve_fit(gaussian_jz, xdata, ydata, (0.0,20.0,3000.0,230.0))  
                fit = gaussian_jz(xdata, *popt)
                
                g._dock_1D_plot.plot.plot(fit)
                
                print 'Fitting: Single Gaussian along x =', center
                print 'width =', float(popt[1]) * conversion_to_um, 'micron'
                print 'amplitude =', float(popt[2]), 'counts'
                print 'center =', float(popt[3]) * conversion_to_um, 'micron'
                print 'FWHM =', float(2.3548*popt[1]) * conversion_to_um, 'micron'
                print "Atoms, 1D (squared) = ", float(popt[2]) * float(popt[1]) * float(popt[1]) * 303 * pow(10,-6) * 0.7
                
            
                
                #g._dock_1D_plot.curve.setData(y=corrected_image[243])
                g._dock_1D_plot.update()
                
                #imgs = m.shape[2]
                #sns = numpy.asarray(numpy.full(imgs, int(db['shotnumber'])))
                #g.imgstack_shotnumbers = numpy.append(g.imgstack_shotnumbers,sns)
                #g.plot(g.imgstack)
                
                #g.update({'GUI_SN='+sn:image_stack_gui({'imgstack':numpy.asarray(unpacked_data)})})  # comment 1 line above out, put class defns above
                #g['GUI_SN='+sn]._console_namespace.update({'DB_SN='+sn:unpacked_databombs})    
               '''
        
    
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
        if DEBUG: print("Params.keys:", params.keys())
        packed_elements = []
        unpacked_databombs = {}
        for k,v in params.items():
            print k
            if "packed_databomb" in k:
                print k
                db = msgpack.unpackb(params[k])
                m = numpy.asarray(db['data'])
                g = self.factory.gui
                g.imgstack = numpy.concatenate((g.imgstack,m), axis=0)
                
                new_image = self.data_storage.table.row
                new_image['short_256_description'] = 'Background'
                new_image['shotnumber'] = int(db['shotnumber'])
                new_image['image_number'] = 1
                new_image['ccd_array'] = m[0]
                new_image.append()
                
                new_image = self.data_storage.table.row
                new_image['short_256_description'] = 'With Atoms'
                new_image['shotnumber'] = int(db['shotnumber'])
                new_image['image_number'] = 2
                new_image['ccd_array'] = m[1]
                new_image.append()                
                
                new_image = self.data_storage.table.row
                new_image['short_256_description'] = 'After Atoms'
                new_image['shotnumber'] = int(db['shotnumber'])
                new_image['image_number'] = 3
                new_image['ccd_array'] = m[2]
                new_image.append()
                
                new_image = self.data_storage.table.row
                new_image['short_256_description'] = 'Corrected Image'
                new_image['shotnumber'] = int(db['shotnumber'])
                new_image['image_number'] = 0
                corrected_image = numpy.divide(numpy.asarray(m[1],dtype=numpy.float),numpy.asarray(m[2],dtype=numpy.float))
                new_image['ccd_array'] = corrected_image
                new_image.append()
                
                new_image = self.data_storage.table.row
                new_image['short_256_description'] = 'Corrected Image - log'
                new_image['shotnumber'] = int(db['shotnumber'])
                new_image['image_number'] = 0
                log_corr = numpy.log(corrected_image)
                new_image['ccd_array'] = numpy.log(corrected_image)
                new_image.append()
                
                self.data_storage.table.flush()
                
                
                table = self.data_storage.h5file.root.data_group.ccd_data
                g.imgstack = numpy.concatenate((g.imgstack,[corrected_image]), axis=0)
                g.imgstack = numpy.concatenate((g.imgstack,[log_corr]), axis=0)
                #imgstack = [x['ccd_array'] for x in table.iterrows() ]#if x['short_256_description'] == 'Corrected Image']
                g.plot(g.imgstack)
                
               
                def gaussian_jz(x,
                             offset,w,a,c):
                    
                    '''
                    Define single peak gaussian function, parameters are listed below:
                    x, variable; offset; w, 1/sqrt(e) width ; a amplitude of the peak; c, peak center.
                    FWHM=2.3548*w
                    '''
                    return offset + a*numpy.exp(-(x-c)**2./(2.*w**2.))
            




                def gaussian(height, center_x, center_y, width_x, width_y):
                    """Returns a gaussian function with the given parameters"""
                    width_x = float(width_x)
                    width_y = float(width_y)
                    return lambda x,y: height*numpy.exp(
                                -(((center_x-x)/width_x)**2+((center_y-y)/width_y)**2)/2)
                    
                def moments(data):
                    """Returns (height, x, y, width_x, width_y)
                    the gaussian parameters of a 2D distribution by calculating its
                    moments """
                    total = data.sum()
                    X, Y = numpy.indices(data.shape)
                    x = (X*data).sum()/total
                    y = (Y*data).sum()/total
                    col = data[:, int(y)]
                    width_x = numpy.sqrt(abs(abs((numpy.arange(col.size)-y)**2*col).sum()/col.sum()))
                    row = data[int(x), :]
                    width_y = numpy.sqrt(abs(abs((numpy.arange(row.size)-x)**2*row).sum()/row.sum()))
                    height = data.max()
                    return height, x, y, width_x, width_y
                 
                def fitgaussian(data):
                    """Returns (height, x, y, width_x, width_y)
                    the gaussian parameters of a 2D distribution found by a fit"""
                    params = moments(data)
                    print params
                    errorfunction = lambda p: numpy.ravel(gaussian(*p)(*numpy.indices(data.shape)) -data)
                    p, success = scipy.optimize.leastsq(errorfunction, params)
                    print p
                    print success
                    return p
                    
                
                
                (height, center_x, center_y, width_x, width_y) = fitgaussian(corrected_image)
                fit = gaussian(*(height, center_x, center_y, width_x, width_y))
            
                #scipy.integrate.dblquad()
            
                
                t = pylab.text(0.95, 0.05, """
                x : %.1f
                y : %.1f
                width_x : %.1f
                width_y : %.1f""" %(center_x, center_y, width_x, width_y),
                fontsize=16, horizontalalignment='right',
                verticalalignment='bottom')
                print t.get_text()
                conversion_to_um = 5.2
                print 'Fitting: Double Gaussian.'
                print 'height =', float(height), 'counts'
                print 'center_x =', float(center_x), 'pixels', float(center_x) * conversion_to_um, 'micron'
                print 'center_y =', float(center_y), 'pixels', float(center_y) * conversion_to_um, 'micron'
                print 'sigma - width_x =', float(width_x), 'pixels', float(width_x) * conversion_to_um, 'micron'
                print 'sigma - width_y =', float(width_y), 'pixels', float(width_y) * conversion_to_um, 'micron'
                print 'FWHM - width_x =', float(2.3548*width_x), 'pixels', float(2.3548*width_x) * conversion_to_um, 'micron'
                print 'FWHM - width_y =', float(2.3548*width_y), 'pixels', float(2.3548*width_y) * conversion_to_um, 'micron'
                print "Atoms, 2D = ", float(height) * float(width_x) * float(width_y) * 303 * pow(10,-6) * 0.7,'\n'
                
            

                    
            
                #popt,popv = curve_fit(func, xdata, ydata, (-12.,12.,15.,25.,6.,5.,50.))
                try:
                    ydata = corrected_image[center_x]
                    g._dock_1D_plot.plot.plot(corrected_image[center_x])
                    center = center_x
                except IndexError:
                    ydata = corrected_image[234]
                    g._dock_1D_plot.plot.plot(corrected_image[243])
                    center = 243
                    
                xdata = numpy.asarray(list(xrange(len(ydata))))
                popt,popv = scipy.optimize.curve_fit(gaussian_jz, xdata, ydata, (0.0,20.0,3000.0,230.0))  
                fit = gaussian_jz(xdata, *popt)
                
                g._dock_1D_plot.plot.plot(fit)
                
                print 'Fitting: Single Gaussian along x =', center
                print 'width =', float(popt[1]) * conversion_to_um, 'micron'
                print 'amplitude =', float(popt[2]), 'counts'
                print 'center =', float(popt[3]) * conversion_to_um, 'micron'
                print 'FWHM =', float(2.3548*popt[1]) * conversion_to_um, 'micron'
                print "Atoms, 1D (squared) = ", float(popt[2]) * float(popt[1]) * float(popt[1]) * 303 * pow(10,-6) * 0.7
                
            
                
                #g._dock_1D_plot.curve.setData(y=corrected_image[243])
                g._dock_1D_plot.update()
                
                #imgs = m.shape[2]
                #sns = numpy.asarray(numpy.full(imgs, int(db['shotnumber'])))
                #g.imgstack_shotnumbers = numpy.append(g.imgstack_shotnumbers,sns)
                #g.plot(g.imgstack)
                
                #g.update({'GUI_SN='+sn:image_stack_gui({'imgstack':numpy.asarray(unpacked_data)})})  # comment 1 line above out, put class defns above
                #g['GUI_SN='+sn]._console_namespace.update({'DB_SN='+sn:unpacked_databombs})        

    
class docked_gui():
    """
    Core class for data viewing GUIs.  Uses a set of docks to store controls
    
    subclass this to create new GUIs; each method named _init_dock_XXX will
    create another dock automatically on initialization in alphabetical order
    of the XXX's.  A console is created by default
    """
    """
    Class to generate a gui to analyze image stacks (3d array of data)
    
    image stack can be passed in params as dictionary element with key "imgstack"
    this will be placed into image stack viewer dock, and passed into console namespace
    
    console data may be passed into console using "_console_namespace" entry in params dictionary
    """
    _console_namespace={}
    def __init__(self,params={}):
        if DEBUG: print("class data_guis.docked_gui, func __init__")

        for k in params.keys():
            setattr(self,k,params[k])
        
        if hasattr(self,"imgstack"):
            self.imgstack = params["imgstack"] 
        else:
            self._generate_random_imgstack()
            self.imgstack = numpy.random.normal(size=(3, 512, 512)) 
            self.imgstack_shotnumbers = numpy.asarray([0,0,0],dtype=int)
               
        self._console_namespace.update({"self":self})
        self._console_namespace.update({"imgstack":self.imgstack}) 
            
        self.app = QtGui.QApplication([])     
        self.win = QtGui.QMainWindow()
        self.dock_area = pyqtgraph.dockarea.DockArea()
        self.win.setCentralWidget(self.dock_area)
        self.win.resize(1000,1000)
        self.win.setWindowTitle('Analysis Space')

        self.command_library = CommandLibrary()
        
        self._init_dock_console()
        self._init_dock_cursor()    
        self._init_dock_control()
        self._init_dock_1D_plot()
        self._init_dock_image_view()
        
        self.win.show()
        
        
    def _methods_to_xml(self):
        out=""
        for meth in dir(self):
            if type(getattr(self,meth))==type(self._methods_to_xml):
                print "<Method><Name>"+meth+"</Name><Source><![CDATA["+inspect.getsource(getattr(self,meth))+"]]></Source></Method>"
        return out
    def _init_dock_console(self):
        self._dock_console = pyqtgraph.dockarea.Dock("Console", size=(500,150))
        self.dock_area.addDock(self._dock_console, 'bottom')      ## place d1 at left edge of dock area (it will fill the whole space since there are no other docks yet)
        self._console = pyqtgraph.console.ConsoleWidget(namespace=self._console_namespace)
        self._dock_console.addWidget(self._console)     
        
    def _init_dock_cursor(self):
        self._dock_cursor = pyqtgraph.dockarea.Dock("Cursor Interface", size=(500,30))
        self.dock_area.addDock(self._dock_cursor, 'bottom')
        self.curs_pos_label = QtGui.QLabel("")
        self._dock_cursor.addWidget(QtGui.QLabel("Cursor Data:"))
        self._dock_cursor.addWidget(self.curs_pos_label)
        
    def _init_dock_control(self):
        self._dock_control = pyqtgraph.dockarea.Dock("Dock Control", size=(500, 50)) ## give this dock the minimum possible size
        self.dock_area.addDock(self._dock_control, 'top')      ## place d1 at left edge of dock area (it will fill the whole space since there are no other docks yet)
        self._layout_widget = pyqtgraph.LayoutWidget()        
        label = QtGui.QLabel(" -- DockArea -- ")
        saveBtn = QtGui.QPushButton('Save dock state')
        restoreBtn = QtGui.QPushButton('Restore dock state')
        restoreBtn.setEnabled(False)
        fileField = QtGui.QLineEdit('File')
        self._layout_widget.addWidget(label, row=0, col=0)
        self._layout_widget.addWidget(saveBtn, row=1, col=0)
        self._layout_widget.addWidget(restoreBtn, row=2, col=0)
        self._layout_widget.addWidget(fileField, row=3, col=0)
        self._dock_control.addWidget(self._layout_widget)
        state = None
        def save():
            global state
            state = self.dock_area.saveState()
            print state['main']
            print dockstate_to_xml(state['main'])
            restoreBtn.setEnabled(True)
        def load():
            global state
            self.dock_area.restoreState(state)
        saveBtn.clicked.connect(save)
        restoreBtn.clicked.connect(load)
        
             
        
    def _init_dock_1D_plot(self):
        self._dock_1D_plot = pyqtgraph.dockarea.Dock("1D Plot", size=(500,500))
        self.dock_area.addDock(self._dock_1D_plot, 'bottom')
        self._dock_1D_plot.addWidget(QtGui.QLabel("1D Plot"))
        self._dock_1D_plot.win = pyqtgraph.GraphicsWindow()
        self._dock_1D_plot.plot = self._dock_1D_plot.win.addPlot(title="1D Plot")
        
        self._dock_1D_plot.data = numpy.random.normal(size=(200))
        self._dock_1D_plot.curve = self._dock_1D_plot.plot.plot(y=self._dock_1D_plot.data)
        
        self._dock_1D_plot.addWidget(self._dock_1D_plot.win)
        
    def _init_dock_image_view(self):
        self._dock_image_view = pyqtgraph.dockarea.Dock("Image View", size=(500,500))
        self.dock_area.addDock(self._dock_image_view, 'top')
        self.imv = pyqtgraph.ImageView()
        self._dock_image_view.addWidget(self.imv)
        #self._dock_image_view.label = DockLabel("Shotnumber = ", self._dock_image_view)
        self._dock_image_view.updateStyle()
        self.imv.setImage(self.imgstack, xvals=numpy.arange(self.imgstack.shape[0]))#.linspace(1., 3., ))

        # attempt to add to context menu (right mouse button) for cursor drop
        self.imv.view.menu.cursorDrop = QtGui.QAction("Drop Cursor", self.imv.view.menu)
        self.imv.view.menu.dropCursor = self.dropCursor
        self.imv.view.menu.cursorDrop.triggered.connect(self.imv.view.menu.dropCursor)
        self.imv.view.menu.addAction(self.imv.view.menu.cursorDrop)
        acs = self.imv.view.menu.subMenus()
        def newSubMenus():
            return [self.imv.view.menu.cursorDrop] + acs
        self.imv.view.menu.subMenus = newSubMenus        
        self.imv.view.menu.valid = False
        self.imv.view.menu.view().sigStateChanged.connect(self.imv.view.menu.viewStateChanged)
        self.imv.view.menu.updateState()


        #cross hair
        self.imv.vLine = pyqtgraph.InfiniteLine(angle=90, movable=False)
        self.imv.hLine = pyqtgraph.InfiniteLine(angle=0, movable=False)
        self.imv.addItem(self.imv.vLine, ignoreBounds=True)
        self.imv.addItem(self.imv.hLine, ignoreBounds=True)
        
        self.imv.vb = self.imv.view

        def animate(evt):
            if self.imv.playTimer.isActive():
                self.imv.playTimer.stop()
                return
            fpsin = self._imv_fps_in
            fps = float(str(fpsin.text()).split("FPS")[0])
            self.imv.play(fps)            

        #animation controls
        self._imv_fps_in = QtGui.QLineEdit('10 FPS')   
        self._imv_anim_b = QtGui.QPushButton('Animate')
        self._imv_anim_b.clicked.connect(animate)
        
        self._imv_layout_widg = pyqtgraph.LayoutWidget()
        self._imv_layout_widg.addWidget(QtGui.QLabel("Animation:"), row=0, col=0)
        self._imv_layout_widg.addWidget(self._imv_fps_in, row=0, col=1)
        self._imv_layout_widg.addWidget(self._imv_anim_b, row=0, col=2)
             
        self._dock_image_view.addWidget(self._imv_layout_widg)
        

        def jumpFrames(n):
            """Move video frame ahead n frames (may be negative)"""
            if self.imv.axes['t'] is not None:
                self.imv.setCurrentIndex(self.imv.currentIndex + n)
                try:
                    pass
                    #self._dock_image_view.label = DockLabel("Shotnumber = "+str(self.imgstack_shotnumbers[self.imv.currentIndex]), self._dock_image_view)
                    #self._dock_image_view.updateStyle()
                except IndexError:
                    pass
        self.imv.jumpFrames = jumpFrames
        
        def mouseMoved(evt):
            pos = evt[0]  ## using signal proxy turns original arguments into a tuple
            if self.imv.scene.sceneRect().contains(pos):
                mousePoint = self.imv.vb.mapSceneToView(pos)
                self.imv.vLine.setPos(mousePoint.x())
                self.imv.hLine.setPos(mousePoint.y())
                index = (int(mousePoint.x()),int(mousePoint.y()))
                x = "<span style='font-size: 12pt;color: blue'>x=%0.1f,   " % mousePoint.x()
                y = "<span style='color: red'>y=%0.1f</span>,   " % mousePoint.y()
                if index[0] > 0 and index[0] < len(self.imgstack[1][0]):
                    if index[1] > 0 and index[1] < len(self.imgstack[2][0]):
                        #Fix the next line so that the z axis is for the image that is displayed
                        try:
                            z = "<span style='color: green'>z=%0.1f</span>" % self.imgstack[self.imv.currentIndex, index[0], index[1]]
                        except:
                            z="<span style='color: green'>z=Error</span>"
                            print "index:", index
                            print "len(self.imgstack[1][0]:", len(self.imgstack[1][0])
                            print "self.imv.currentIndex:", self.imv.currentIndex
                        self.curs_pos_label.setText(x+y+z)
        
        
        self.proxy = pyqtgraph.SignalProxy(self.imv.scene.sigMouseMoved, rateLimit=60, slot=mouseMoved)
                
    def saveSettings(self):
        settings = PyQt4.QtCore.QSettings('test', 'test')
        settings.setValue("state", self.win.saveState())
        settings.sync()
        
    def readSettings(self):
        settings = PyQt4.QtCore.QSettings('test', 'test')
        state = settings.value("state", PyQt4.QtCore.QByteArray()).toByteArray();
        self.win.restoreState(state)
    def plot(self,img):
        """
        plots to image viewer
        """
        print 'Class image_stack_gui, function plot'
        #pdb.set_trace()
        self.imv.setImage(numpy.asarray(img))
        
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
            self.vLine = pyqtgraph.InfiniteLine(angle=90, movable=True)
            self.hLine = pyqtgraph.InfiniteLine(angle=0, movable=True)
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
        
        
    def _generate_random_imgstack(self):
        ## Create random 3D data set with noisy signals
        img = scipy.ndimage.gaussian_filter(numpy.random.normal(size=(10, 10)), (5, 5)) * 20 + 100
        img = img[numpy.newaxis,:,:]
        decay = numpy.exp(-numpy.linspace(0,0.3,100))[:,numpy.newaxis,numpy.newaxis]
        data = numpy.random.normal(size=(100, 10, 10))
        data += img * decay
        data += 2
        ## Add time-varying signal
        sig = numpy.zeros(data.shape[0])
        sig[30:] += numpy.exp(-numpy.linspace(1,10, 70))
        sig[40:] += numpy.exp(-numpy.linspace(1,10, 60))
        sig[70:] += numpy.exp(-numpy.linspace(1,10, 30))        
        sig = sig[:,numpy.newaxis,numpy.newaxis] * 3
        data[:,50:60,50:60] += sig
        self.imgstack=data
        
def main():

            
        
    #app=a.app   # ,if necessary
    #win=a.win   # ,if necessary
    
    global gui
    gui = docked_gui()  # comment 1 line above out, put class defns above
 
    
    #QtGui.QApplication.instance().exec_() # this start command needs to be here to enable cursors, and hence this must initialize last

    #pdb.set_trace()
    #time.sleep(3)
    
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
    from twisted.python import log
    log.startLogging(sys.stdout)
   
    from twisted.internet import stdio
    from twisted.protocols import basic
    from twisted.internet import error

    
    class Keyboard_Input(basic.LineReceiver):
        """
        Keyboard input protocol - for simultaneous input of python commands
        and browsing of server objects while the server is running
        """
        from os import linesep as delimiter # doesn't seem to work
        if os.name=='nt': delimiter="\n"
        def __init__(self):
            self.pre_e=colorama.Style.BRIGHT+ colorama.Back.RED+colorama.Fore.WHITE
            self.post_e=colorama.Fore.RESET+colorama.Back.RESET+colorama.Style.RESET_ALL
        #        self.setRawMode()
        def connectionMade(self):
            pass
        def lineReceived(self, line):
            """
            called when a line of input received - executes and prints result
            or passes error message to console
            """
            rbuffer = StringIO()
            po = sys.stdout
            sys.stdout = rbuffer
            err = False
            try:
                exec line in globals(),locals()
            except Exception as e:
                err = e
            sys.stdout = po
            print '>u> ' + line
            if err:
                out = self.pre_e + str(e) + self.post_e
            else:
                out = rbuffer.getvalue()
            if out != "":
                print '>s> ' + out
        
    class MyServerProtocol(WebSocketServerProtocol):
    
        def onConnect(self, request):
            if DEBUG: print("class data_guis.MyServerProtocol, func onConnect: {0}".format(request.peer))
            
        def onOpen(self):
            if DEBUG: print("class data_guis.MyServerProtocol, func onOpen")
            
        def onMessage(self, payload_, isBinary):
            if DEBUG: print "class data_guis.MyServerProtocol, func onMessage asdf (4) " + str(time.time()-TIMING)
            #self.log_message()
            if isBinary:
                payload = msgpack.unpackb(payload_)
                if not payload.has_key('IDLSocket_ResponseFunction'):
                    return None
                try:
                    #ThisResponseFunction = getattr(self.factory.app.command_library,
                    #                           payload['IDLSocket_ResponseFunction'])
                    ThisResponseFunction = getattr(self.factory.command_library,
                                               payload['IDLSocket_ResponseFunction'])
                except AttributeError:
                    if DEBUG: print ('Missing Socket_ResponseFunction:',
                                     payload['IDLSocket_ResponseFunction'])
                ThisResponseFunction(payload)
            else:
                payload = simplejson.loads(payload_)
                if 'Not_Command_text_message' in payload:
                    if DEBUG: print payload['Not_Command_text_message']
                    return
                if DEBUG: print "payload:"
                if DEBUG and not len(payload) < 10000: print payload
                if not payload.has_key('IDLSocket_ResponseFunction'):
                    return None
                try:
                    #ThisResponseFunction = getattr(self.factory.app.command_library,
                    #                           payload['IDLSocket_ResponseFunction'])
                    ThisResponseFunction = getattr(self.factory.command_library,
                                               payload['IDLSocket_ResponseFunction'])
                except AttributeError:
                    if DEBUG: print ('Missing Socket_ResponseFunction:',
                                     payload['IDLSocket_ResponseFunction'])
                ThisResponseFunction(payload)
                    

            
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
        #win.close()
        #app.quit()
        reactor.callLater(0.01, reactor.stop)
    
    
    keyboard = Keyboard_Input()
    stdio.StandardIO(keyboard)
    
    sys.argv.append('localhost')
    sys.argv.append('9100')
    #sys.argv[0] = file name of this script
    # szys.argv[1] = ip address of this server
    # sys.argv[2] = port to listen on
    factory = WebSocketServerFactory("ws://" + 'localhost' + ":"+str(sys.argv[2]), debug = False)
    factory.setProtocolOptions(failByDrop=False)
    factory.protocol = MyServerProtocol
    try:
        reactor.listenTCP(int(sys.argv[2]), factory)
        #a.factory = factory
        command_library = CommandLibrary()
        factory.command_library = command_library
        command_library.factory = factory
        factory.gui = gui
    except twisted.internet.error.CannotListenError:
        server_shutdown()
    
    
    reactor.run()
    
if __name__ == '__main__':
    main()
    
"""
Below until MARKER1 is objectification of AnalysisSpaces
"""



class XTSM_Element(gnosis.xml.objectify._XO_,XTSMobjectify.XTSM_core):
    pass

class Analysis_Space_Core(XTSMobjectify.XTSM_core):
    """
    Default Class for all elements appearing in an XTSM Analysis_Space tree; contains generic methods
    for traversing the XTSM tree-structure, inserting and editing nodes and attributes,
    writing data out to XML-style strings, and performing parsing of node contents in
    python-syntax as expressions
    """
    pass

class Docked_Gui():
    """
    Core class for data viewing GUIs.  Uses a set of docks to store controls
    A console is created by default
    """
    _console_namespace={}
    def __init__(self,params={}):
        if DEBUG: print("class data_guis.docked_gui, func __init__")

        for k in params.keys():
            setattr(self,k,params[k])
        
        self._console_namespace.update({"self":self})
            
        self.app = QtGui.QApplication([])     
        self.win = QtGui.QMainWindow()
        self.dock_area = pyqtgraph.dockarea.DockArea()
        self.win.setCentralWidget(self.dock_area)
        self.win.resize(1000,1000)
        self.win.setWindowTitle('Analysis Space')

        self.command_library = CommandLibrary()
        
        self.docks=[]
        for dock in params["docks"]:
            d = dock._init_dock(self)
            d._sources = dock._sources
            self.docks.append(d)
            
        
        self.win.show()
            
    def _sources_to_xml(self):
        out=""
        for dock in self.docks:
            for method in dock._sources:
                print "<DockType>"
                print "<Name>" + dock__class__ + "</Name>"
                print "<Method><Source><![CDATA["+method+"]]></Source></Method>"
                print "</DockType>"
        return out            
            
    def _methods_to_xml(self):
        out=""
        for meth in dir(self):
            if type(getattr(self,meth))==type(self._methods_to_xml):
                print "<Method><Name>"+meth+"</Name><Source><![CDATA["+inspect.getsource(getattr(self,meth))+"]]></Source></Method>"
        return out

class AnalysisSpace(gnosis.xml.objectify._XO_,Analysis_Space_Core):
    """
    The toplevel object for an analysis space, sometimes called a data_gui
    """
    def read_state(self):
        """
        reads and appends data about dock placement from the underlying 
        Dock_Gui element after creation or while running
        """
        new_representation=AnalysisSpace()
        state=self.gui.dock_area.saveState()
        print state
        def dockstate_to_xml(state):
            def elm_to_xml(elms,out):
                #pdb.set_trace()
                if type(elms)!=type([]):
                    elms=[elms]
                for elm in elms:
                    elm_type=elm[0]
                    elm_type = elm_type.title()
                    out+="<"+str(elm_type)+">"
                    if type(elm[1])==type([]):
                        out=elm_to_xml(elm[1],out)
                    else:
                        elm_docktype=elm[1]
                        out+="<Type>"+str(elm_docktype)+"</Type>"
                    out+="</"+str(elm_type)+">"
                return out
            out=""
            out=elm_to_xml(state,out)
            return out   
            

        
        #pdb.set_trace()
        print "<AnalysisSpace>"
        print _sources_to_xml()
        print "<State>"
        print dockstate_to_xml(state['main'])
        print "</State>"
        print "</AnalysisSpace>"
        def rec_step():
            pass
            # what we did before, a recursive function to dive into and assemble the xml, with sizes appended as well
            # also determining all used classes of docks, outputting them, and their methods
        return new_representation.write_xml()

    
    def _launch_if_necessary(self):
        """
        checks if this AnalysisSpace is already running; if not, launches it
        
        if already running, reads dock states (etc?) and returns xml representation
        of its current state
        """
        pass # needs writing
    
    def _launch(self):
        """
        creates and launches the data_gui
        """
        # creates all pyqt representation of docks
        self._indocktrinate()
        # create the gui (pyqtgraph object) itself
        self.gui = Docked_Gui(params={"docks":self.docks})
        self.gui.parent_xtsm_analysis_space = self
        # create event loop and internals using twisted and pyqt
        self._start_engine()

    def _indocktrinate(self):
        """
        spawn all docks and source
        """
        # first spawn pyqt dock objects
        self.docks=[]
        for dock in self.Dock:
            self.docks.append(dock._spawn())
    
    def _start_engine(self):
        """
        start the qtreactor and socket communications
        """
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
        from twisted.python import log
        log.startLogging(sys.stdout)
       
        from twisted.internet import stdio
        from twisted.protocols import basic
        from twisted.internet import error
    
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
                        #ThisResponseFunction = getattr(self.factory.app.command_library,
                        #                           payload['IDLSocket_ResponseFunction'])
                        ThisResponseFunction = getattr(self.factory.command_library,
                                                   payload['IDLSocket_ResponseFunction'])
                    except AttributeError:
                        if DEBUG: print ('Missing Socket_ResponseFunction:',
                                         payload['IDLSocket_ResponseFunction'])
                    ThisResponseFunction(payload)
                else:
                    print payload_.keys()
                
                
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
            #win.close()
            #app.quit()
            reactor.callLater(0.01, reactor.stop)
        
        sys.argv.append('localhost')
        sys.argv.append('9100')
        #sys.argv[0] = file name of this script
        # szys.argv[1] = ip address of this server
        # sys.argv[2] = port to listen on
        factory = WebSocketServerFactory("ws://" + 'localhost' + ":"+str(sys.argv[2]), debug = False)
        factory.setProtocolOptions(failByDrop=False)
        factory.protocol = MyServerProtocol
        try:
            reactor.listenTCP(int(sys.argv[2]), factory)
            #a.factory = factory
            command_library = CommandLibrary()
            factory.command_library = command_library
            command_library.factory = factory
            factory.gui = self.gui
        except twisted.internet.error.CannotListenError:
            server_shutdown()
        
        reactor.run()

class DockType(gnosis.xml.objectify._XO_,Analysis_Space_Core):
    """
    Root factory for a defined dock type, instances created during objectification of XTSM
    
    """
    
    def __init__(self):
        
        class this_docktype():
            """
            factory class for generating the pyqt-object docks
            """   
                
            def _init_dock(self,parent_qt):
                """
                function to instantiate dock, must be present, should
                typically be overwritten to generate the content of the dock,
                i.e. buttons and so forth
                
                this function should always return the dock it generated, and
                as good form attach that dock as self._dock
                """
                self._dock = pyqtgraph.dockarea.Dock("Default Dock", size=(500,100))
                parent_qt.dock_area.addDock(self._dock, 'bottom')
                return self._dock
                
            
        self.factory=this_docktype
        self.factory._sources = []
    
    def _install_sources(self):
        old_stdout = sys.stdout
        for meth in self.Method:
            try:
                context={"self":self}
                capturer = StringIO()
                sys.stdout = capturer
                src=meth.write_xml().split('<Method>')[1].split('</Method>')[0]
                src=meth.write_xml().split('<![CDATA[')[1].split(']]>')[0]
                exec src in globals(),context 
                sys.stdout = old_stdout
                for elm in context:
                    setattr(self.factory,elm,context[elm])
            except Exception as e:
                context.update({'_SCRIPT_ERROR':e})
                print e
        sys.stdout = old_stdout # make sure we have stdout back
        self.factory._sources.append(src)
                


class Dock(gnosis.xml.objectify._XO_,Analysis_Space_Core):
    """
    docks created during objectification of XTSM - use _spawn method to
    generate a pyqtgraph dock object from this XTSM element
    """
    def _spawn(self):
        """
        spawns the dock itself using the factory class defined elsewhere in
        AnalysisSpace container, returns result, an instance of the factory class
        """
        try: 
            dock_type=self.getFirstParentByType("AnalysisSpace").getItemByFieldValue("DockType","Name",self.Type.PCDATA)
            dock_type._install_sources()
            self._dock=dock_type.factory()
            self._dock._sources = dock_type.factory._sources
            pdb.set_trace()
        except Exception as e:
            pdb.set_trace()
            print e
        #print self._dock._methods_to_xml()
        return self._dock
        
class Method(gnosis.xml.objectify._XO_,Analysis_Space_Core):
    def write_xml(self, out=None, tablevel=0, whitespace='True',CDATA_ESCAPE=True):
        return Analysis_Space_Core.write_xml(self,out=out, tablevel=tablevel, whitespace=whitespace,CDATA_ESCAPE=CDATA_ESCAPE)


gnosis.xml.objectify._XO_ = XTSM_Element
# identify all XTSM classes defined above, override the objectify _XO_ subclass for each
allclasses=inspect.getmembers(sys.modules[__name__],inspect.isclass)
XTSM_Classes=[tclass[1] for tclass in allclasses if (issubclass(getattr(sys.modules[__name__],tclass[0]),getattr(getattr(sys.modules[__name__],'XTSMobjectify'),'XTSM_core')))]
for XTSM_Class in XTSM_Classes:
    setattr(gnosis.xml.objectify, "_XO_"+XTSM_Class.__name__, XTSM_Class)
del allclasses

"""
MARKER1
"""

example_AS_xtsm=u"""<AnalysisSpace>
    <DockType>
        <Name>Console</Name>
        <Method><![CDATA[
def _init_dock(self,parent_qt):
    self._dock= pyqtgraph.dockarea.Dock("Console", size=(500,150))
    parent_qt.dock_area.addDock(self._dock, 'bottom')      ## place d1 at left edge of dock area (it will fill the whole space since there are no other docks yet)
    _console = pyqtgraph.console.ConsoleWidget(namespace=parent_qt._console_namespace)
    self._dock.addWidget(_console)
    return self._dock
]]>
        </Method>
    </DockType>
        <Dock>
            <Type>Console</Type>
        </Dock>
        <Dock>
            <Type>Console</Type>
        </Dock>
        <Dock>
            <Type>Console</Type>
        </Dock>
</AnalysisSpace>"""    