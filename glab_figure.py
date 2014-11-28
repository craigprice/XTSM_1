# -*- coding: utf-8 -*-
"""
Created on Sun Apr 20 12:40:21 2014

@author: Nate
"""

import uuid, numpy, matplotlib, StringIO, pdb, inspect, sys, itertools
import softstring
import xml.etree.ElementTree as ET
import matplotlib.cm
import matplotlib.mlab 
import matplotlib.pyplot

class glab_figure_core(object):
    """
    core class for figure objects - defines common functions and data
    elements for generation, display, reference and storage
    """

    # the following ditems element defines necessary and optional data
    # inputs required to make the figure (an example is given) - each
    # entry key denotes an element that will be attached as attribute
    # to the figure object, and will be pulled from the data argument to _set_data
    # if the value is a dictionary with a 'required' entry, a True value indicates
    # figure can only be drawn if this element exists; the names field of the
    # element defines a list of acceptable names for this field    
    ditems={'x': {'required':False,'names':['Abscissa', 'x', 'horizontal']},
            'y': {'required':True, 'names':['Ordinate', 'y', 'vertical']},
            'a_note_that_does_not_belong': {'note':'This must be overwritten!!'} }

    def __init__(self,params={}):
        defaultparams={"id":uuid.uuid1(),'options':{}}
        defaultparams.update(params)
        for item in defaultparams:
            setattr(self,item,defaultparams[item])

    def __setattr__(self,att,val):
        """
        overwritten set attribute routine - if data is set, calls _set_data
        """
        if att=='data': 
            self._set_data(val)
            return
        object.__setattr__(self,att,val)

    # following three methods are data-setting routines; can be overridden in subclasses as needed
    def _set_data(self,data):
        data_type_assignment_methods={type([]):             self._data_as_list, 
                                      type({}):             self._data_as_dict,
                                      type(numpy.array([])):self._data_as_numpyarray}       
        data_type_assignment_methods[type(data)](data) # calls assignment routine determined by data type
        self._verify_data()

    def _data_as_list(self,data):
        try:
            ndata=numpy.array(data)
        except:
            raise self.BadDataError
        self._data_as_numpyarray(ndata)
                
    def _data_as_dict(self,data):
        for ditem in self.ditems:
            for name in self.ditems[ditem]['names']:
                try: 
                    setattr(self, ditem, data[name])
                    break
                except: pass
            
    def _verify_data(self):
        """
        verifies necessary data exists, and calls autogenerate methods (_autogenerate_DATANAME) 
        if the data does not exist, and the method does
        """
        for item in [it for it in self.ditems if self.ditems[it]['required']]:
            if not hasattr(self,item): 
                raise self.MissingDataError
                return False
        for item in [it for it in self.ditems if not self.ditems[it]['required']]:
            if not hasattr(self,item):
                try: getattr(self,'_autogenerate_'+item)()
                except AttributeError: pass 
            
    def show(self):
        """
        shows a figure in a window from within a python session.  to display
        an image in a browser, svg data must be generated, and this is not the
        right method to invoke - see toSVG()
        """
        try: self.f.show()
        except AttributeError: 
            try:
                self.make()
                self.f.show()
            except: raise self.CannotFormPlotError

    def make(self):
        """
        makes an image for the figure, attached as self.f - this method must
        be overridden by subclasses to make the specific figure type
        """
        raise self.MethodUndefinedError 

    def toSVG(self):
        """
        generates and returns, and attaches as self.svgdata an SVG-format image string
        """
        if not hasattr(self,"f"): self.make()
        stream=StringIO.StringIO() # a stream to catch figure
        self.f.canvas.print_figure(stream,format="svg") # print the figure to a file stream         
        etx = ET.XML(stream.getvalue()) # this step only really necessary if dom-style transforms are necessary
        self.svgdata=ET.tostring(etx)
        return self.svgdata

    class MethodUndefinedError(Exception):
        pass
    class MissingDataError(Exception):
        pass
    class BadDataError(Exception):
        pass
    class CannotFormPlotError(Exception):
        pass        
    
class Scatter(glab_figure_core):

    ditems={'x': {'required':False,'names':['Abscissa', 'x', 'horizontal']},
            'y': {'required':True, 'names':['Ordinate', 'y', 'vertical']}}

    def _data_as_numpyarray(self,data):
        """
        data as numpy arrays will be treated differently depending on its 
        dimensionality, trying to anticipate different possible pass forms
        - this may be called directly or by data initially formed as a list
        or dict
        """
        try: data=numpy.array(data)
        except:
            rawdata=data
            data=numpy.array(data['data'])

        # the next several routines define the response for different dimensionalities of numpy array
        def onD1(data):
            return ([numpy.arange(len(data))],[data])
        def onD2(data): 
            if any(numpy.array(data.shape)==2L):
                # point pairs or pairs of 1d arrays:
                if data.shape[0]==2L: return ([data[0]],[data[1]])
                else: return ([data[:,0]],[data[:,1]])
            if data.shape[2]==3L:
                # point triplets of 1d arrays:
                x,y,self.labelind = ([],[],[])
                for trace in numpy.unique(data[:,:,2]):
                    ps = (data[:,2]==trace)
                    newx, newy=(data[ps,0],data[ps,1])
                    x.append(newx)
                    y.append(newy)
                    self.labelind.append(trace)
                else: return ([data[:,0]],[data[:,1]])
            # a generic 2D array will be interpreted as series of y data first index x value
            ydata=[]
            for ind in range(data.shape[1]):
                ydata.append(data[:,ind])
            return ([numpy.arange(len(data.shape[0]))]*data.shape[1],ydata)
        def onD3(data): # 3D data will be interpreted as an array of 2D forms, with last index enumerating them;
                        # the stacking option will be applied at the outermost level, overlaid on the inner
            for ind in range(data.shape[2]):
                x,y = ([],[])
                newx, newy = onD2(data[:,:,ind])
                x.append([newx])
                y.append([newy])
            return (x,y)
                
        # this calls the appropriate routine
        (self.x,self.y)=locals()['onD'+str(len(data.shape))](data)

    def _autogenerate_x(self):
        self.x=[]
        for trace in self.y:
            self.x.append(numpy.arange(len(trace)))

    def _autogenerate_links(self):
        self.links=[[None]]*len(self.x)
        
    def make(self):
        try: numsp={"Offset":1,"Overlaid":1,"Stacked":len(self.x)}[self.options['Stacking']]
        except KeyError: numsp=1
        self.f, self.axes = matplotlib.pyplot.subplots(numsp, sharex=True, sharey=False)
        try: num_plots=len(self.axes)
        except TypeError: 
            num_plots=1
            self.axes=[self.axes]
        for axis,index in zip(self.axes,range(num_plots)):
            if self.links[index]==[None]:
                scatterpoints = axis.scatter(self.x[index],self.y[index],alpha=0.4)
#            for xvals, yvals, link in zip(self.x[index],self.y[index],self.links[index]):
#                scatterpoints = axis.scatter(xvals,yvals,alpha=0.4) # add the scatter plot

class DensityPlot(glab_figure_core):
    ditems={'z': {'required':True,  'names':['data','z','intensity','height','amplitude']},
            'x': {'required':False, 'names':['x', 'horizontal']},
            'y': {'required':False, 'names':['y', 'vertical']}}

    def make(self):
        self.f = matplotlib.pyplot.figure()
        matplotlib.pyplot.imshow(self.z)
        
    def _autogenerate_x(self):
        self.x=numpy.arange(self.z.shape[0])

    def _autogenerate_y(self):
        self.y=numpy.arange(self.z.shape[1])

# utility function for below - flattens lists of strings

# some introspective data about this module:
plot_types = {cl[0]:cl[1] for cl in inspect.getmembers(sys.modules[__name__], inspect.isclass) if issubclass(cl[1],glab_figure_core)}
del plot_types['glab_figure_core']
plot_components = {ft:softstring.flattern([elm['names'] for elm in plot_types[ft].ditems.values()]) for ft in plot_types}
unique_plot_components = {ft: [n for n in plot_components[ft] if n not in softstring.flattern([plot_components[c] for c in plot_components if c!=ft ])] for ft in plot_types}
