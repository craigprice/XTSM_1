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
import traceback
import sys
import socket

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
import hdf5_liveheap
import pprint
#from pyqt_signal_dressing import _signal_dressed_import
#hdf5_liveheap=_signal_dressed_import("hdf5_liveheap")
    
DEBUG = False
global TIMING
TIMING = 1416876428
    


    
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
        
    def create_new_analysis_space(self,params):
        if DEBUG: print("class data_guis.docked_gui.CommandLibrary, func create_new_analysis_space")
        #gui = docked_gui()  # comment 1 line above out, put class defns above  CP 2015-01
        #exec params['script_body'] in globals(), {}
        command = {'script_body': params['script_body'],
                   'context' : {'self':self}}
        self._execute(command)
           
           
    def _execute(self, commands):               
        script = commands['script_body']
        context = commands['context']
        old_stdout = sys.stdout
        if DEBUG: print "commands"
        if DEBUG: print commands
        try:
            capturer = StringIO()
            sys.stdout = capturer
            t0=time.time()
            script = script.replace('\g', '>')
            script = script.replace('\l', '<')
            exec script in globals(),context
            t1=time.time()
            context.update({"_starttime":t0,"_exectime":(t1-t0),"_script_console":capturer.getvalue()})
        except Exception as e: 
            context.update({'_SCRIPT_ERROR':e})
            print '_SCRIPT_ERROR'
            print 'Script:'
            pprint.pprint(script)
            print 'Context:'
            pprint.pprint(context.keys())
            print e
            print e.message
            traceback.print_stack()
            traceback.print_exception(*sys.exc_info())
#          del context['__builtin__']  # removes the backeffect of exec on context to add builtins
        sys.stdout = old_stdout
        if DEBUG: print "Context: " + str([context])
        if DEBUG: pprint.pprint(context)
        if hasattr(commands, 'callback_function'):
            if commands['callback_function'] != 'None':
                callback = commands['callback_function']
                callback()
                
                
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
        if DEBUG: print("class data_guis.docked_gui.CommandLibrary, func check_consistency_with_xtsm")
        
        #xtsm_object = XTSMobjectify.XTSM_Object("<XTSM>" + example_AS_xtsm + "</XTSM>")
        #xtsm_object.XTSM.AnalysisSpace.gui = 

        xtsm = '<XTSM>'+params['analysis_space_xtsm']+'</XTSM>'
        try:
            xtsm_object = XTSMobjectify.XTSM_Object(xtsm)
        except Exception as e:
            print "Error:", e
            print e.message
            traceback.print_stack()
            traceback.print_exception(*sys.exc_info())
            return
        
        
        xtsm_object.XTSM.AnalysisSpace.gui = self.gui
        
        to_update_all = False
        try:
            self.gui._console_namespace['AnalysisSpace'].Name
        except KeyError:
            to_update_all = True
            self.gui._console_namespace.update({'AnalysisSpace':xtsm_object.XTSM.AnalysisSpace})
        
        if self.gui._console_namespace['AnalysisSpace'].Name.PCDATA != xtsm_object.XTSM.AnalysisSpace.Name.PCDATA:
            to_update_all = True
            self.gui._console_namespace.update({'AnalysisSpace':xtsm_object.XTSM.AnalysisSpace})
                
        gui_space = self.gui._console_namespace['AnalysisSpace']
        
        docks = xtsm_object.XTSM.getDescendentsByType('Dock')
        for d in docks:
            try:
                gui_dock = gui_space.getItemByFieldValue('Dock', 'Name', d.Name.PCDATA)
            except AttributeError as e:
                print "Error:", e
                print e.message
                traceback.print_stack()
                traceback.print_exception(*sys.exc_info())
                return
                
            #pprint.pprint('d.Method._seq[0]'+d.Method[0]._seq[0])
            #pprint.pprint('gui_dock.Method[0]._seq[0]'+gui_dock.Method[0]._seq[0])
            
            command = {'script_body': d.Method[0]._seq[0],
                       'context' : {'self':self.gui, '_xtsm_dock': d}}
                       
            if (to_update_all or gui_dock.Name.PCDATA == None or gui_dock.Method[0]._seq[0] != d.Method[0]._seq[0]):
                self._execute(command)
            
        
        heaps = xtsm_object.XTSM.getDescendentsByType('Heap')
        if DEBUG: print "Here are the heaps:"
        for h in heaps:
            if DEBUG: print h.write_xml()
            try:
                gui_heap = gui_space.getItemByFieldValue('Heap', 'Name', h.Name.PCDATA)
            except AttributeError as e:
                print "Error:", e
                print e.message
                traceback.print_stack()
                traceback.print_exception(*sys.exc_info())
                return
                
            
            command = {'script_body': h.Method[0]._seq[0],
                       'context' : {'self':self.gui, '_xtsm_heap': h}}
                
            if (to_update_all or gui_heap.Name.PCDATA == None or gui_heap.Method[0]._seq[0] != h.Method[0]._seq[0]):
                self._execute(command)

        
            
    def test(self,adict):
        print "dffg"
        pass
        
        
    def databomb(self, params):
        if DEBUG: print("class data_guis.docked_gui.CommandLibrary, func databomb")
        db = msgpack.unpackb(params['databomb'])
        ns = self.factory.gui._console_namespace
        scripts = ns['AnalysisSpace'].getDescendentsByType('Script')
        #xtsm_heap = ns['xtsm_object'].XTSM.getDescendentsByType('Heap')[0]
        #if any(x in [xtsm_heap.DataCriteria.PCDATA] for x in list(ns.values())):
        #    ns[xtsm_heap.Name.PCDATA].push(numpy.asarray(db['data']), shotnumber=numpy.asarray(db['shotnumber']))
        try:
            self.factory.gui._console_namespace['databombs'].append(db)
            self.factory.gui._console_namespace['_last_databomb'] = db
        except KeyError:
            self.factory.gui._console_namespace.update({'databombs':[db]})
            self.factory.gui._console_namespace['_last_databomb'] = db
        #print scripts[0].ScriptBody.PCDATA
        #print repr(scripts[0].ScriptBody.PCDATA)
        #print scripts[0].ScriptBody._seq
        #print scripts[0].ScriptBody.write_xml()
        #scripts[0].ScriptBody.PCDATA = scripts[0].ScriptBody.PCDATA.replace('\\n ','\n')
        #scripts[0].ScriptBody.PCDATA = scripts[0].ScriptBody.PCDATA.replace('\\n','\n')
        #scripts[0].ScriptBody.PCDATA = scripts[0].ScriptBody.PCDATA.replace('\\t','\t')
        #print scripts[0].ScriptBody.PCDATA
        #print repr(scripts[0].ScriptBody.PCDATA)
        #xtsm_heap = ns['xtsm_object'].XTSM.getDescendentsByType('Heap')[0]
        #ns[xtsm_heap.Name.PCDATA].push(numpy.asarray(db['data']), shotnumber=numpy.asarray(db['shotnumber']))
        #print numpy.asarray(db['data']).shape
        #print numpy.asarray(db['shotnumber'])
        '''
        try:
            ns[xtsm_heap.Name.PCDATA].push(numpy.asarray(db['data'][0]), shotnumber=numpy.asarray(db['shotnumber']))
        except Exception as e:
            print "Error in push to heap"
            print e
            print inspect.getsource(hdf5_liveheap)
            return
        '''
        for script in scripts:
            if script.ExecuteOnEvent.PCDATA != "databomb":
                continue
            try:
                exec script.ScriptBody._seq[0] in globals(), ns
            except Exception as e:
                print 'Error in exec:'
                print 'Script:'
                pprint.pprint(script.ScriptBody._seq[0])
                print 'Context:'
                pprint.pprint(ns.keys())
                print e
                print e.message
                traceback.print_stack()
                traceback.print_exception(*sys.exc_info())
                return
        
    
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


 
import gnosis.xml.objectify # standard package used for conversion of xml structure to Pythonic objects, also core starting point for this set of routines
import XTSMobjectify  

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
            
        if hasattr(self,"imgstack"):
            self.imgstack = params["imgstack"] 
        else:
            self._generate_random_imgstack()
            self.imgstack = numpy.random.normal(size=(3, 512, 512)) 
        self._console_namespace.update({"self":self})
        self._console_namespace.update({"imgstack":self.imgstack}) 
            
        self.app = QtGui.QApplication([])     
        self.win = QtGui.QMainWindow()
        self.dock_area = pyqtgraph.dockarea.DockArea()
        self.win.setCentralWidget(self.dock_area)
        self.win.resize(1000,1000)
        self.win.setWindowTitle('Analysis Space')

        self.command_library = CommandLibrary()
        
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
        
    def read_state(self):
        """
        reads and appends data about dock placement from the underlying 
        Dock_Gui element after creation or while running
        """
        if DEBUG: print("class data_guis.Docked_Gui, func read_state")
        #new_representation=AnalysisSpace()
        state=self.dock_area.saveState()
        print "state"
        pprint.pprint(state)
        print "state['main']"
        pprint.pprint(state['main'])
        def dockstate_to_xml(state):
            def elm_to_xml(elms,out):
                print 'elms'
                pprint.pprint(elms)
                #pdb.set_trace()
                if type(elms)!=type([]):
                    elms=[elms]
                for elm in elms:
                    elm_type=elm[0]
                    elm_type = elm_type.title()
                    out+="<"+str(elm_type)+">\n"
                    if type(elm[1])==type([]):
                        out=elm_to_xml(elm[1],out)
                    else:
                        elm_docktype=elm[1]
                        out+="<Type>"+str(elm_docktype)+"</Type>\n"
                    for k in elm[2]:
                        out+="<"+k.title()+">"+str(elm[2][k])+"</"+k.title()+">\n"
                    out+="</"+str(elm_type)+">\n"
                return out
            out=""
            out=elm_to_xml(state,out)
            return out   
            
        #pdb.set_trace()
        #print "<AnalysisSpace>"
        #print _sources_to_xml()
        print "<State>"
        print "<Float>"
        print str([])
        print "</Float>"
        print "<Main>"
        print dockstate_to_xml(state['main'])
        print "</Main>"
        print "</State>"
        #print "</AnalysisSpace>"
        def rec_step():
            pass
            # what we did before, a recursive function to dive into and assemble the xml, with sizes appended as well
            # also determining all used classes of docks, outputting them, and their methods
        return
        return new_representation.write_xml()        
        
    def state_to_settings(self,state):
        '''
        This will take a saved settings file in xml, and turn it back into the
        expected form to restore the state of the data_gui.
        
        Unifinished. Copied from settings_to_xml without change yet.
        '''
        try:
            xtsm_object = XTSMobjectify.XTSM_Object("<XTSM>" + state + "</XTSM>")
        except:
            xtsm_object = state
        settings = {}
        settings.update({'float':xtsm_object.Float})
        settings.update({'main':xtsm_object.Main})
        def state_to_settings(state):
            def xml_to_elm(state,out):
                print 'elms'
                pprint.pprint(elms)
                #if state.getChildren()
                if type(elms)!=type([]):
                    elms=[elms]
                for elm in elms:
                    elm_type=elm[0]
                    elm_type = elm_type.title()
                    out+="<"+str(elm_type)+">\n"
                    if type(elm[1])==type([]):
                        out=elm_to_xml(elm[1],out)
                    else:
                        elm_docktype=elm[1]
                        out+="<Type>"+str(elm_docktype)+"</Type>\n"
                    for k in elm[2]:
                        out+="<"+k.title()+">"+str(elm[2][k])+"</"+k.title()+">\n"
                    out+="</"+str(elm_type)+">\n"
                return out
            out=""
            out=elm_to_xml(state,out)
            return out   
        
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
        print 'Not functional'
        #pdb.set_trace()
        #self.imv.setImage(numpy.asarray(img))
        
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

class AnalysisSpace(gnosis.xml.objectify._XO_,Analysis_Space_Core):
    """
    The toplevel object for an analysis space
    """
    
    def _methods_to_xml(self):
        if DEBUG: print("class data_guis.AnalysisSpace, func _methods_to_xml")
        out=""
        for meth in dir(self):
            if type(getattr(self,meth))==type(self._methods_to_xml):
                print "<Method><Name>"+meth+"</Name><Source><![CDATA["+inspect.getsource(getattr(self,meth))+"]]></Source></Method>"
        return out    


class Heap(gnosis.xml.objectify._XO_,Analysis_Space_Core):
    """
    docks created during objectification of XTSM - use _spawn method to
    generate a pyqtgraph dock object from this XTSM element
    """
    def __init__(self):
        if DEBUG: print "class Heap, function __init__"
        for meth in self.Method:
            try:
                meth._src=meth.write_xml().split('<Method>')[1].split('</Method>')[0]
            except Exception as e:
                context.update({'_SCRIPT_ERROR':e})
                print e
                print context  

class Dock(gnosis.xml.objectify._XO_,Analysis_Space_Core):
    """
    docks created during objectification of XTSM - use _spawn method to
    generate a pyqtgraph dock object from this XTSM element
    """
    def __init__(self):
        if DEBUG: print "class Dock, function __init__"
        for meth in self.Method:
            try:
                meth._src=meth.write_xml().split('<Method>')[1].split('</Method>')[0]
            except Exception as e:
                context.update({'_SCRIPT_ERROR':e})
                print e
                print context
        
class Method(gnosis.xml.objectify._XO_,Analysis_Space_Core):
    def write_xml(self, out=None, tablevel=0, whitespace='True',CDATA_ESCAPE=True):
        if DEBUG: print("class data_guis.Method, func write_xml")
        return Analysis_Space_Core.write_xml(self,out=out, tablevel=tablevel, whitespace=whitespace,CDATA_ESCAPE=CDATA_ESCAPE)


gnosis.xml.objectify._XO_ = XTSM_Element
# identify all XTSM classes defined above, override the objectify _XO_ subclass for each
allclasses=inspect.getmembers(sys.modules[__name__],inspect.isclass)
XTSM_Classes=[tclass[1] for tclass in allclasses if (issubclass(getattr(sys.modules[__name__],tclass[0]),getattr(getattr(sys.modules[__name__],'XTSMobjectify'),'XTSM_core')))]
for XTSM_Class in XTSM_Classes:
    setattr(gnosis.xml.objectify, "_XO_"+XTSM_Class.__name__, XTSM_Class)
del allclasses


def  main():
    
    gui = Docked_Gui()    
    
    if DEBUG: print("function main()")
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
            interface_ = ""
            if socket.gethostbyname(socket.gethostname()) == '10.1.1.124':
                interface_ = '10.1.1.124'
            self.transport.joinGroup("228.0.0.5", interface=interface_)
        
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
            #if DEBUG: print "Datagram received from "+ repr(address)
            pass

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
                payload = simplejson.loads(payload_)
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
    
    sys.argv.append('localhost')
    sys.argv.append('9100')
    #sys.argv[0] = file name of this script
    # szys.argv[1] = ip address of this server
    # sys.argv[2] = port to listen on
    factory = WebSocketServerFactory("ws://" + 'localhost' + ":"+str(sys.argv[2]), debug=DEBUG)
    factory.setProtocolOptions(failByDrop=False)
    factory.protocol = MyServerProtocol
    try:
        reactor.listenTCP(int(sys.argv[2]), factory)
        #a.factory = factory
        command_library = CommandLibrary()
        factory.command_library = command_library
        command_library.factory = factory
        #factory.gui = self.gui
        command_library.gui = gui
        factory.gui = gui
        ping_data={"server_id":sys.argv[3],
                "server_name":"",
                "server_ip":"",
                "server_port":int(sys.argv[2]),
                "server_id_node":"",
                "server_ping":"server_ready!",
                "server_time":time.time()}
        ready = simplejson.dumps(ping_data)
        udpbport = 8085
        multicast = reactor.listenMulticast(udpbport, 
                                                 MulticastProtocol(),
                                                 listenMultiple=True)
        reactor.callWhenRunning(multicast.protocol.send, ready)        
        
    except twisted.internet.error.CannotListenError:
        server_shutdown()
    
    reactor.run()    
    
    

if __name__ == '__main__':
    main()


example_AS_xtsm=u"""
<AnalysisSpace>

<Name>Absorption</Name>
        <Script>
          <Name>Plot_CCD_Image</Name>
          <Description>Plotting</Description>
          <ExecuteOnEvent>databomb</ExecuteOnEvent>
          <ExecuteOnMainServer>False</ExecuteOnMainServer>
          <Time>0</Time>
          <Remote>True</Remote>
          <ScriptBody>
<![CDATA[
import numpy
self.apogee_raw_image_0_heap.push(_last_databomb['data'][0],_last_databomb['shotnumber'],0)
self.apogee_raw_image_1_heap.push(_last_databomb['data'][1],_last_databomb['shotnumber'],0)
div = numpy.divide(numpy.asarray(_last_databomb['data'][0],dtype=numpy.float),
                   numpy.asarray(_last_databomb['data'][1],dtype=numpy.float))
div = numpy.log(div)
self.apogee_log_divided_image_heap.push(div,_last_databomb['shotnumber'],0)

self.raw_image_0_dock.imv.setImage(numpy.asarray(self.apogee_raw_image_0_heap['all'].squeeze()))
self.raw_image_1_dock.imv.setImage(numpy.asarray(self.apogee_raw_image_1_heap['all'].squeeze()))
self.divided_image_dock.imv.setImage(numpy.asarray(self.apogee_log_divided_image_heap['all'].squeeze()))



]]>	  
            </ScriptBody>
        </Script>
        <Heap>
          <Name>Raw_Image_With_Atoms</Name>
          <DataCriteria>'10.1.1.110'</DataCriteria>
          <Priority>0</Priority>
          <Method>
<![CDATA[
print '_xtsm_heap.Name.PCDATA', _xtsm_heap.Name.PCDATA
self.absorption_datastore = hdf5_liveheap.glab_datastore({'title':'Absorption'})
#options = {"element_structure":[769,513],
options = {"element_structure":[512,512],
           "dataname":_xtsm_heap.Name.PCDATA,
           "typecode":numpy.dtype("uint16"),#numpy.uint16 will not work
           "datastore":self.absorption_datastore}
self.apogee_raw_image_0_heap = hdf5_liveheap.glab_liveheap(options)
self._console_namespace.update({'apogee_raw_image_0_heap':self.apogee_raw_image_0_heap})
self._console_namespace.update({'absorption_datastore':self.absorption_datastore})
]]>
          </Method>
        </Heap>
        <Heap>
          <Name>Raw_Image_No_Atoms</Name>
          <DataCriteria>'10.1.1.110'</DataCriteria>
          <Method>
<![CDATA[
print '_xtsm_heap.Name.PCDATA', _xtsm_heap.Name.PCDATA
#options = {"element_structure":[769,513],
options = {"element_structure":[512,512],
           "dataname":_xtsm_heap.Name.PCDATA,
           "typecode":numpy.dtype("uint16"),#numpy.uint16 will not work
           "datastore":self.absorption_datastore}
self.apogee_raw_image_1_heap = hdf5_liveheap.glab_liveheap(options)
self._console_namespace.update({'apogee_raw_image_1_heap':self.apogee_raw_image_1_heap})
]]>
          </Method>
        </Heap>
        <Heap>
          <Name>Log_Divided</Name>
          <DataCriteria>'10.1.1.110'</DataCriteria>
          <Method>
<![CDATA[
print '_xtsm_heap.Name.PCDATA', _xtsm_heap.Name.PCDATA
#options = {"element_structure":[769,513],
options = {"element_structure":[512,512],
           "dataname":_xtsm_heap.Name.PCDATA,
           "typecode":numpy.dtype("float64"),#numpy.uint16 will not work
           "datastore":self.absorption_datastore}
self.apogee_log_divided_image_heap = hdf5_liveheap.glab_liveheap(options)
self._console_namespace.update({'apogee_log_divided_image_heap':self.apogee_log_divided_image_heap})
]]>
          </Method>
        </Heap>      
    <Dock>
        <Name>Raw_Image_0</Name>
        <Method>
<![CDATA[
#'self' is the gui object.
#variables created in this script will not be placed in the console namespace unless explicitly placed there.
name = str(_xtsm_dock.Name.PCDATA)
#d = pyqtgraph.dockarea.Dock(name, size=(500,500))
#setattr(self, name+'_dock', d)
#dock = getattr(self, name+'_dock')
self.raw_image_0_dock = pyqtgraph.dockarea.Dock(name, size=(500,500))
self.raw_image_0_dock.label.setText(QtCore.QString(name))
self.dock_area.addDock(self.raw_image_0_dock, 'top')
self.raw_image_0_dock.updateStyle()


self.raw_image_0_dock.imv = pyqtgraph.ImageView()
imv = self.raw_image_0_dock.imv
self.raw_image_0_dock.addWidget(imv)
imv.setImage(self.imgstack, xvals=numpy.arange(self.imgstack.shape[0]))#.linspace(1., 3., ))


# attempt to add to context menu (right mouse button) for cursor drop
imv.view.menu.cursorDrop = QtGui.QAction("Drop Cursor", imv.view.menu)
imv.view.menu.dropCursor = self.dropCursor
imv.view.menu.cursorDrop.triggered.connect(imv.view.menu.dropCursor)
imv.view.menu.addAction(imv.view.menu.cursorDrop)

imv.acs = imv.view.menu.subMenus()

global gui
gui = self
def newSubMenus():
    global gui
    self = gui
    return [self.raw_image_0_dock.imv.view.menu.cursorDrop] + self.raw_image_0_dock.imv.acs
imv.view.menu.subMenus = newSubMenus        
imv.view.menu.valid = False
imv.view.menu.view().sigStateChanged.connect(imv.view.menu.viewStateChanged)
imv.view.menu.updateState()


#cross hair
imv.vLine = pyqtgraph.InfiniteLine(angle=90, movable=False)
imv.hLine = pyqtgraph.InfiniteLine(angle=0, movable=False)
imv.addItem(imv.vLine, ignoreBounds=True)
imv.addItem(imv.hLine, ignoreBounds=True)

imv.vb = imv.view

def animate(evt):
    global gui
    self = gui
    if self.raw_image_0_dock.imv.playTimer.isActive():
        self.raw_image_0_dock.imv.playTimer.stop()
        return
    fpsin = self._imv_fps_in
    fps = float(str(fpsin.text()).split("FPS")[0])
    self.raw_image_0_dock.imv.play(fps)            

#animation controls
self._imv_fps_in = QtGui.QLineEdit('10 FPS')   
self._imv_anim_b = QtGui.QPushButton('Animate')
self._imv_anim_b.clicked.connect(animate)

self._imv_layout_widg = pyqtgraph.LayoutWidget()
self._imv_layout_widg.addWidget(QtGui.QLabel("Animation:"), row=0, col=0)
self._imv_layout_widg.addWidget(self._imv_fps_in, row=0, col=1)
self._imv_layout_widg.addWidget(self._imv_anim_b, row=0, col=2)
     
self.raw_image_0_dock.addWidget(self._imv_layout_widg)
def mouseMoved(evt):
    global gui
    self = gui
    pos = evt[0]  ## using signal proxy turns original arguments into a tuple
    if self.raw_image_0_dock.imv.scene.sceneRect().contains(pos):
        mousePoint = self.raw_image_0_dock.imv.vb.mapSceneToView(pos)
        self.raw_image_0_dock.imv.vLine.setPos(mousePoint.x())
        self.raw_image_0_dock.imv.hLine.setPos(mousePoint.y())
        index = (int(mousePoint.x()),int(mousePoint.y()))
        x = "\lspan style='font-size: 12pt;color: blue'\gx=%0.1f,   " % mousePoint.x() #Need to escape the \lessthan, \greaterthan to use them
        #x =  "X = " + str(int(mousePoint.x())) + "; "
        y = "\lspan style='color: red'\gy=%0.1f\l/span\g,   " % mousePoint.y()
        #y =  "Y = " + str(int(mousePoint.y())) + "; "
        if index[0] \g 0 and index[0] \l len(self.imgstack[1][0]):
            if index[1] \g 0 and index[1] \l len(self.imgstack[2][0]):
                #Fix the next line so that the z axis is for the image that is displayed
                try:
                    z = "\lspan style='color: green'\gz=%0.1f\l/span\g" % self.imgstack[self.raw_image_0_dock.imv.currentIndex, index[0], index[1]]
                    #z = "Z = " + str(self.imgstack[self.raw_image_0_dock.imv.currentIndex, index[0], index[1]])
                except: 
                    z="\lspan style='color: green'\gz=Error\l/span\g"
                    #z=" Error "
                    print "index:", index
                    print "len(self.imgstack[1][0]:", len(self.imgstack[1][0])
                    print "self.raw_image_0_dock.imv.currentIndex:", self.raw_image_0_dock.imv.currentIndex
                self.curs_pos_label.setText(str(x)+str(y)+str(z))


self.raw_image_0_dock.proxy = pyqtgraph.SignalProxy(imv.scene.sigMouseMoved, rateLimit=60, slot=mouseMoved)



self._console_namespace.update({'raw_image_0_dock':self.raw_image_0_dock})

]]>
        </Method>
    </Dock>  
    <Dock>
        <Name>Raw_Image_1</Name>
        <Method>
<![CDATA[
name = 'raw_image_no_atoms'
self.raw_image_1_dock = pyqtgraph.dockarea.Dock(name, size=(500,500))
self.raw_image_1_dock.label.setText(QtCore.QString(name))
self.dock_area.addDock(self.raw_image_1_dock, 'above', self._console_namespace['raw_image_0_dock'])
self.raw_image_1_dock.updateStyle()


self.raw_image_1_dock.imv = pyqtgraph.ImageView()
imv = self.raw_image_1_dock.imv
self.raw_image_1_dock.addWidget(imv)
imv.setImage(self.imgstack, xvals=numpy.arange(self.imgstack.shape[0]))#.linspace(1., 3., ))


# attempt to add to context menu (right mouse button) for cursor drop
imv.view.menu.cursorDrop = QtGui.QAction("Drop Cursor", imv.view.menu)
imv.view.menu.dropCursor = self.dropCursor
imv.view.menu.cursorDrop.triggered.connect(imv.view.menu.dropCursor)
imv.view.menu.addAction(imv.view.menu.cursorDrop)

imv.acs = imv.view.menu.subMenus()

global gui
gui = self
def newSubMenus():
    global gui
    self = gui
    return [self.raw_image_1_dock.imv.view.menu.cursorDrop] + self.raw_image_1_dock.imv.acs
imv.view.menu.subMenus = newSubMenus        
imv.view.menu.valid = False
imv.view.menu.view().sigStateChanged.connect(imv.view.menu.viewStateChanged)
imv.view.menu.updateState()


#cross hair
imv.vLine = pyqtgraph.InfiniteLine(angle=90, movable=False)
imv.hLine = pyqtgraph.InfiniteLine(angle=0, movable=False)
imv.addItem(imv.vLine, ignoreBounds=True)
imv.addItem(imv.hLine, ignoreBounds=True)

imv.vb = imv.view

def animate(evt):
    global gui
    self = gui
    if self.raw_image_1_dock.imv.playTimer.isActive():
        self.raw_image_1_dock.imv.playTimer.stop()
        return
    fpsin = self._imv_fps_in
    fps = float(str(fpsin.text()).split("FPS")[0])
    self.raw_image_1_dock.imv.play(fps)            

#animation controls
self._imv_fps_in = QtGui.QLineEdit('10 FPS')   
self._imv_anim_b = QtGui.QPushButton('Animate')
self._imv_anim_b.clicked.connect(animate)

self._imv_layout_widg = pyqtgraph.LayoutWidget()
self._imv_layout_widg.addWidget(QtGui.QLabel("Animation:"), row=0, col=0)
self._imv_layout_widg.addWidget(self._imv_fps_in, row=0, col=1)
self._imv_layout_widg.addWidget(self._imv_anim_b, row=0, col=2)
     
self.raw_image_1_dock.addWidget(self._imv_layout_widg)
def mouseMoved(evt):
    global gui
    self = gui
    pos = evt[0]  ## using signal proxy turns original arguments into a tuple
    if self.raw_image_1_dock.imv.scene.sceneRect().contains(pos):
        mousePoint = self.raw_image_1_dock.imv.vb.mapSceneToView(pos)
        self.raw_image_1_dock.imv.vLine.setPos(mousePoint.x())
        self.raw_image_1_dock.imv.hLine.setPos(mousePoint.y())
        index = (int(mousePoint.x()),int(mousePoint.y()))
        x = "\lspan style='font-size: 12pt;color: blue'\gx=%0.1f,   " % mousePoint.x() #Need to escape the \lessthan, \greaterthan to use them
        #x =  "X = " + str(int(mousePoint.x())) + "; "
        y = "\lspan style='color: red'\gy=%0.1f\l/span\g,   " % mousePoint.y()
        #y =  "Y = " + str(int(mousePoint.y())) + "; "
        if index[0] \g 0 and index[0] \l len(self.imgstack[1][0]):
            if index[1] \g 0 and index[1] \l len(self.imgstack[2][0]):
                #Fix the next line so that the z axis is for the image that is displayed
                try:
                    z = "\lspan style='color: green'\gz=%0.1f\l/span\g" % self.imgstack[self.raw_image_1_dock.imv.currentIndex, index[0], index[1]]
                    #z = "Z = " + str(self.imgstack[self.raw_image_1_dock.imv.currentIndex, index[0], index[1]])
                except: 
                    z="\lspan style='color: green'\gz=Error\l/span\g"
                    #z=" Error "
                    print "index:", index
                    print "len(self.imgstack[1][0]:", len(self.imgstack[1][0])
                    print "self.raw_image_1_dock.imv.currentIndex:", self.raw_image_1_dock.imv.currentIndex
                self.curs_pos_label.setText(str(x)+str(y)+str(z))


self.raw_image_1_dock.proxy = pyqtgraph.SignalProxy(imv.scene.sigMouseMoved, rateLimit=60, slot=mouseMoved)



self._console_namespace.update({'raw_image_1_dock':self.raw_image_1_dock})

]]>
        </Method>
    </Dock>  

    <Dock>
        <Name>Divided_Image</Name>
        <Method>
<![CDATA[
name = 'divided_image'
self.divided_image_dock = pyqtgraph.dockarea.Dock(name, size=(500,500))
self.divided_image_dock.label.setText(QtCore.QString(name))
self.dock_area.addDock(self.divided_image_dock, 'right', self._console_namespace['raw_image_0_dock'])
self.divided_image_dock.updateStyle()


self.divided_image_dock.imv = pyqtgraph.ImageView()
imv = self.divided_image_dock.imv
self.divided_image_dock.addWidget(imv)
imv.setImage(self.imgstack, xvals=numpy.arange(self.imgstack.shape[0]))#.linspace(1., 3., ))


# attempt to add to context menu (right mouse button) for cursor drop
imv.view.menu.cursorDrop = QtGui.QAction("Drop Cursor", imv.view.menu)
imv.view.menu.dropCursor = self.dropCursor
imv.view.menu.cursorDrop.triggered.connect(imv.view.menu.dropCursor)
imv.view.menu.addAction(imv.view.menu.cursorDrop)

imv.acs = imv.view.menu.subMenus()

global gui
gui = self
def newSubMenus():
    global gui
    self = gui
    return [self.divided_image_dock.imv.view.menu.cursorDrop] + self.divided_image_dock.imv.acs
imv.view.menu.subMenus = newSubMenus        
imv.view.menu.valid = False
imv.view.menu.view().sigStateChanged.connect(imv.view.menu.viewStateChanged)
imv.view.menu.updateState()


#cross hair
imv.vLine = pyqtgraph.InfiniteLine(angle=90, movable=False)
imv.hLine = pyqtgraph.InfiniteLine(angle=0, movable=False)
imv.addItem(imv.vLine, ignoreBounds=True)
imv.addItem(imv.hLine, ignoreBounds=True)

imv.vb = imv.view

def animate(evt):
    global gui
    self = gui
    if self.divided_image_dock.imv.playTimer.isActive():
        self.divided_image_dock.imv.playTimer.stop()
        return
    fpsin = self._imv_fps_in
    fps = float(str(fpsin.text()).split("FPS")[0])
    self.divided_image_dock.imv.play(fps)            

#animation controls
self._imv_fps_in = QtGui.QLineEdit('10 FPS')   
self._imv_anim_b = QtGui.QPushButton('Animate')
self._imv_anim_b.clicked.connect(animate)

self._imv_layout_widg = pyqtgraph.LayoutWidget()
self._imv_layout_widg.addWidget(QtGui.QLabel("Animation:"), row=0, col=0)
self._imv_layout_widg.addWidget(self._imv_fps_in, row=0, col=1)
self._imv_layout_widg.addWidget(self._imv_anim_b, row=0, col=2)
     
self.divided_image_dock.addWidget(self._imv_layout_widg)
def mouseMoved(evt):
    global gui
    self = gui
    pos = evt[0]  ## using signal proxy turns original arguments into a tuple
    if self.divided_image_dock.imv.scene.sceneRect().contains(pos):
        mousePoint = self.divided_image_dock.imv.vb.mapSceneToView(pos)
        self.divided_image_dock.imv.vLine.setPos(mousePoint.x())
        self.divided_image_dock.imv.hLine.setPos(mousePoint.y())
        index = (int(mousePoint.x()),int(mousePoint.y()))
        x = "\lspan style='font-size: 12pt;color: blue'\gx=%0.1f,   " % mousePoint.x() #Need to escape the \lessthan, \greaterthan to use them
        #x =  "X = " + str(int(mousePoint.x())) + "; "
        y = "\lspan style='color: red'\gy=%0.1f\l/span\g,   " % mousePoint.y()
        #y =  "Y = " + str(int(mousePoint.y())) + "; "
        if index[0] \g 0 and index[0] \l len(self.imgstack[1][0]):
            if index[1] \g 0 and index[1] \l len(self.imgstack[2][0]):
                #Fix the next line so that the z axis is for the image that is displayed
                try:
                    z = "\lspan style='color: green'\gz=%0.1f\l/span\g" % self.imgstack[self.divided_image_dock.imv.currentIndex, index[0], index[1]]
                    #z = "Z = " + str(self.imgstack[self.divided_image_dock.imv.currentIndex, index[0], index[1]])
                except: 
                    z="\lspan style='color: green'\gz=Error\l/span\g"
                    #z=" Error "
                    print "index:", index
                    print "len(self.imgstack[1][0]:", len(self.imgstack[1][0])
                    print "self.divided_image_dock.imv.currentIndex:", self.divided_image_dock.imv.currentIndex
                self.curs_pos_label.setText(str(x)+str(y)+str(z))


self.divided_image_dock.proxy = pyqtgraph.SignalProxy(imv.scene.sigMouseMoved, rateLimit=60, slot=mouseMoved)



self._console_namespace.update({'divided_image_dock':self.divided_image_dock})

]]>
        </Method>
    </Dock>  
    <Dock>
        <Name>cut_along_x</Name>
        <Method>
<![CDATA[
name = 'cut_along_x'
cut_along_x_dock = pyqtgraph.dockarea.Dock(name, size=(500,100))
cut_along_x_dock.label.setText(QtCore.QString(name))
self.dock_area.addDock(cut_along_x_dock, 'bottom', self._console_namespace['raw_image_0_dock'])
cut_along_x_dock.addWidget(QtGui.QLabel(name))
cut_along_x_dock.win = pyqtgraph.GraphicsWindow()
cut_along_x_dock.plot = cut_along_x_dock.win.addPlot(title=name)

cut_along_x_dock.data = numpy.random.normal(size=(200))
cut_along_x_dock.curve = cut_along_x_dock.plot.plot(y=cut_along_x_dock.data)

cut_along_x_dock.addWidget(cut_along_x_dock.win)
self._console_namespace.update({'cut_along_x_dock':cut_along_x_dock})
]]>
        </Method>
    </Dock>
    <Dock>
        <Name>cut_along_y</Name>
        <Method>
<![CDATA[
name = 'cut_along_y'
cut_along_y_dock = pyqtgraph.dockarea.Dock(name, size=(500,100))
cut_along_y_dock.label.setText(QtCore.QString(name))
self.dock_area.addDock(cut_along_y_dock, 'right', self._console_namespace['cut_along_x_dock'])
cut_along_y_dock.addWidget(QtGui.QLabel(name))
cut_along_y_dock.win = pyqtgraph.GraphicsWindow()
cut_along_y_dock.plot = cut_along_y_dock.win.addPlot(title=name)

cut_along_y_dock.data = numpy.random.normal(size=(200))
cut_along_y_dock.curve = cut_along_y_dock.plot.plot(y=cut_along_y_dock.data)

cut_along_y_dock.addWidget(cut_along_y_dock.win)
self._console_namespace.update({'cut_along_y_dock':cut_along_y_dock})
]]>
        </Method>
    </Dock>
    <Dock>
        <Name>Console</Name>
        <Method>
<![CDATA[
name = 'Console'
console_dock = pyqtgraph.dockarea.Dock(name, size=(250,1))
console_dock.label.setText(QtCore.QString(name))
self.dock_area.addDock(console_dock, 'bottom')      ## place d1 at left edge of dock area (it will fill the whole space since there are no other docks yet)
_console = pyqtgraph.console.ConsoleWidget(namespace=self._console_namespace)
console_dock.addWidget(_console)
self._console_namespace.update({'console_dock':console_dock})
]]>
        </Method>
    </Dock>
    <Dock>
        <Name>Cursor</Name>
        <Method>
<![CDATA[
name = 'Cursor Interface'
cursor_dock = pyqtgraph.dockarea.Dock(name, size=(1,1))
cursor_dock.label.setText(QtCore.QString(name))
self.dock_area.addDock(cursor_dock, 'left', self._console_namespace['console_dock'])
self.curs_pos_label = QtGui.QLabel("")
cursor_dock.addWidget(QtGui.QLabel("Cursor Data:"))
cursor_dock.addWidget(self.curs_pos_label)
self._console_namespace.update({'cursor_dock':cursor_dock})
]]>
        </Method>
    </Dock>
    <Dock>
        <Name>Control</Name>
        <Method>
<![CDATA[
name = 'Dock Control'
control_dock = pyqtgraph.dockarea.Dock(name, size=(1, 1)) ## give this dock the minimum possible size
control_dock.label.setText(QtCore.QString(name))
self.dock_area.addDock(control_dock, 'bottom', self._console_namespace['cursor_dock'])      ## place d1 at left edge of dock area (it will fill the whole space since there are no other docks yet)
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
control_dock.addWidget(self._layout_widget)
state = None
def save():
    global state
    state = self.dock_area.saveState()
    print state['main']
    #print self.dockstate_to_xml(state['main'])
    print self.read_state()
    restoreBtn.setEnabled(True)
def load():
    global state
    self.dock_area.restoreState(state)
saveBtn.clicked.connect(save)
restoreBtn.clicked.connect(load)
self._console_namespace.update({'control_dock':control_dock})
]]>
        </Method>
    </Dock>
</AnalysisSpace>
"""    

xtsm_object = XTSMobjectify.XTSM_Object("<XTSM>" + example_AS_xtsm + "</XTSM>")
#xtsm_object.XTSM.AnalysisSpace.gui = 