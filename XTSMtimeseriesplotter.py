# -*- coding: utf-8 -*-
"""
Created on Mon Jun 10 17:17:56 2013

This is code to create time-series plots for use with XTSM software.  Goal
is to have an object, which when populated with an array of time values, and
second (multidimensional) array of values for channels at times gives a
web-viewable plot of the timing data

TODO:
    FOR GENERIC USEFULNESS:
        return pythonic representation of svg as object for manipulation
    FOR DEBUGGING PARSER USES:
        add populate by intedges
        add populate by emulator outputs
    FOR GUI INTEGRATION:
        add pan and zoom to subplots
    FOR USE WITHIN PYTHON IDE:
        add native python view in graphics windows

@author: Nate
"""
import numpy, StringIO
import matplotlib.cm
import matplotlib.mlab 
import matplotlib.pyplot
import pdb
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, MaxNLocator
import xml.etree.ElementTree as ET

class TimeSeriesPlotter(object):
    """
    Class to implement time-series plots within XTSM framework
    """
    def __init__(self,time_values,channel_outputs):
        self.times=time_values
        self.outputs=channel_outputs
        self.params={'min_time':-1,'max_time':-1,
                        'channels':numpy.array([0]),'min_val':-10.,
                        'max_val':10.}
    def plot(self,extparams={}):
        """
        Constructs and returns the plot
        """
        self.params.update(extparams) # update and override the plot parameters
        #return image

class SVG_XYPlots(object):
    """
    Class to generate XY-scatter plots in timeseries style as SVG images, with optional point-click event links
    
    xvals, yvals, and links should be specified in a dictionary of lists of numpy arrays (xval and yval) and of strings (links)
    a list of the above will create a stacked series of such plots    
    
    for links, using "javascript:afunction(anargument);" will call a predefined function

    example usage (simple single plot):
    aa=SVG_XYPlots({'xvals':numpy.power(numpy.arange(1000.)/200.,2),'yvals':numpy.sin(numpy.arange(1000)*2*3.14159/200),'links':["javascript:alert('yes');" for a in range(1000)]})
    aa.draw()
    
    example usage (single overlaid plot):
    aa=SVG_XYPlots({'xvals':[numpy.power(numpy.arange(1000.)/200.,2),1+numpy.power(numpy.arange(1000.)/200.,2)],'yvals':[numpy.sin(numpy.arange(1000)*2*3.14159/200),numpy.sin(numpy.arange(1000)*2*3.14159/200)],'links':[["javascript:alert('yes');" for a in range(1000)],["javascript:alert('yes');" for a in range(1000)]]})
    aa.draw()
    
    example usage (double pane plot):
    aa=SVG_XYPlots({'xvals':[[numpy.power(numpy.arange(1000.)/200.,2)],[1+numpy.power(numpy.arange(1000.)/200.,2)]],'yvals':[[numpy.sin(numpy.arange(1000)*2*3.14159/200)],[numpy.sin(numpy.arange(1000)*2*3.14159/200)]],'links':[[["javascript:alert('yes');" for a in range(1000)]],[["javascript:alert('yes');" for a in range(1000)]]]})
    aa.draw()
    
    not yet supported: the flag asXTSM (boolean) if True will return the figure as an XTSM object
    """
    def __init__(self,data={}):
        """
        """
        default={'xvals':None,'yvals':None,'links':None,'plotlabels':None}
        default.update(data)
        data=default
        self.xvals=lev=data['xvals']
        self.yvals=data['yvals']
        self.links=data['links']
        self.plotlabels=data['plotlabels']
        if data['links']!=None: self.haslinks=True
        else: self.haslinks=False        
        if data['plotlabels']!=None: self.hasplotlabels=True
        else: self.hasplotlabels=False
        self.nohovers=False
        self.cursor=True
        # check list depth        
        num_lev=0
        while type(lev)==type([]):
            num_lev+=1
            lev=lev[0]
        # coerce depth to 2
        while num_lev<2:
            self.xvals=[self.xvals]
            self.yvals=[self.yvals]
            self.links=[self.links]
            num_lev+=1

    def draw(self,asXTSM=False):
        # this draw routine creates a stacked plot with a single pane for every list in axes
        # create an empty figure
        f, axes = matplotlib.pyplot.subplots(len(self.xvals), sharex=True, sharey=False)
        try: num_plots=len(axes)
        except TypeError: 
            num_plots=1
            axes=[axes]
        for axes,index in zip(axes,range(num_plots)):
            for xvals, yvals, link in zip(self.xvals[index],self.yvals[index],self.links[index]):
                ff = axes.plot(xvals,yvals,linestyle="steps-post") # add the scatter plot
                matplotlib.pyplot.setp(ff, color='grey', linewidth=2.0)                
                scatterpoints = axes.scatter(xvals,yvals,alpha=0.4) # add the scatter plot
                axes.xaxis.set_major_locator(MaxNLocator(11,prune='both')) # remove edge ticks to avoid overlapping
                axes.yaxis.set_major_locator(MaxNLocator(5,prune='both')) # remove edge ticks to avoid overlapping
                if self.haslinks: scatterpoints.set_urls(link) # set links to the points; can be of form "javascript: XXX;"
#                if not self.nohovers:
#                   for pt in range(len(xvals)): 
#                       axes.annotate("..agag",xy=(xvals[pt],yvals[pt]))
                if self.hasplotlabels:
                    labelprops=dict(boxstyle='round', facecolor='wheat', alpha=0.5)                    
                    axes.text(.02,.95,self.plotlabels[index],transform=axes.transAxes, fontsize=28/num_plots,verticalalignment='top', bbox=labelprops)
        f.subplots_adjust(hspace=0)
        stream=StringIO.StringIO() # a stream to catch figure
        f.canvas.print_figure(stream,format="svg") # print the figure to a file stream            
        # objectify the svg image
        etx = ET.XML(stream.getvalue())
        if self.haslinks:
            # find the svg namespace prefix
            svgprefix=etx.tag[:-3]
            # find all link elements
            linkelms=etx.findall('*//'+svgprefix+'a')
            # determine the xlink namespace prefix for href
            xlinkprefix=[link for link in linkelms[0].attrib.keys() if link.split('href')!=-1][0][:-4]
            for linkelm in linkelms:
                if linkelm.attrib[xlinkprefix+'href'].find('title(')!=-1:
                    ts=linkelm.attrib[xlinkprefix+'href'].split('title(',1)[1].split(');',1)
                    linkelm.set(xlinkprefix+'title',ts[0])
                    linkelm.attrib[xlinkprefix+'href']=ts[1]
        # insert link to scripts for cursor movement...
        if self.cursor:
            etx.insert(0,ET.Element("{http://www.w3.org/2000/svg}script"))
            scriptnode=etx.find("{http://www.w3.org/2000/svg}script")
            scriptnode.set("{http://www.w3.org/1999/xlink}href","XTSM_svgScripts.js")
            etx.insert(len(etx.getchildren()),ET.Element("{http://www.w3.org/2000/svg}line")) # this should be inserted after all patches
            linenode=etx.getchildren()[-1]#find("{http://www.w3.org/2000/svg}line")
            linenode.set("id","cursor_vline")
            linenode.set("x1","100")
            linenode.set("x2","100")
            linenode.set("y1","0")
            linenode.set("y2","432")
            linenode.set("style","stroke:rgb(200,200,255);stroke-width:2")
            etx.insert(len(etx.getchildren()),ET.Element("{http://www.w3.org/2000/svg}line")) # this should be inserted after all patches
            linenode=etx.getchildren()[-1]#find("{http://www.w3.org/2000/svg}line")
            linenode.set("id","cursor_hline")
            linenode.set("x1","0")
            linenode.set("x2","576")
            linenode.set("y1","200")
            linenode.set("y2","200")
            linenode.set("style","stroke:rgb(200,200,255);stroke-width:2")
            etx.find("*[@id='figure_1']").set("onmousemove","move(evt)")
            pdb.set_trace()
            # draw the line - STOPPED HERE            
        outfile = open('scatter2.svg', 'w')
        outfile.write(ET.tostring(etx))
        #f.canvas.print_figure('scatter2.svg')
        #if asXTSM: return 'unsupported'
        #else: return stream.getvalue() # return figure as string
        
        
        