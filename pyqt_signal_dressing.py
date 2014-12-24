"""
Created on Thu Nov 20 13:44:07 2014

@author: Nate

pyqt_signal_dressing.py

This module provides machinery for attaching pyqt signals to every method 
within desired classes within other modules, and utility functions for 
examining existing signals and slots. 

"""

from PyQt4.QtCore import QObject, pyqtSignal

import importlib, inspect, PyQt4, re, imp
import pdb

def _signal_dressed_import(module_name):
    """
    this imports a module, dressing all methods inside top-level classes which
    subclass PyQt4.QtCore.Object with a pair of pyqt signals, one emitted 
    before the method fires, one after, called _className___s_methodName_(fired/tofire).
    
    use:  to import a module named 'hdf5_liveheap', do not use import hdf5_liveheap;
    instead use: hdf5_liveheap=_signal_dressed_import('hdf5_liveheap'), 
    then use module components as usual. 
            
    each object instance now created from any toplevel class that inherits PyQt4.QtCore.Object
    will now have both signals attached as attributes of the object for each method
    to connect a slot (a callback function) to these signals, do the following:
        
        g = theimportedModule.aToplevelClass()
        g._aToplevelClass___s_methodName_fired.connect(aSlotFunction)
    
    calling the method via

        g.methodName()
        
    results in execution of aSlotFunction after execution of g.methodName

    all slot functions are presumed to take a dictionary in the form 
    {"args":args,"kwargs":kwargs} for arguments and keywords
    
    remember that the objects you want signals attached to must have PyQt4.QtCore.Object
    inherited.  If you get the error message:
    
        pyqtSignal must be bound to a QObject, not 'YOURCLASSNAME'
        
    it is likely because you did not call the QObject __init__ in your initializer
    for the class as in :
        
      class YOURCLASSNAME(PyQt4.QtCore.Object):  
        def __init__(self):
            someofyourcode
            PyQt4.QtCore.Object.__init__(self)
            moreofyourcode
   
    for other examples, see test() function in this module   
   
    implementation:  due to peculiarities of pyqtSignal (which cannot be defined
    dynamically, this works by rewriting the source code of the module, and 
    compiling on the fly.  It is a pain, but seems to be necessary)
    """
    module = importlib.import_module(module_name)
    # find all classes which are subclass of PyQt4.QtCore.QObject
    classes_to_dress=[getattr(module,on) for on in dir(module) 
                    if (inspect.isclass(getattr(module,on)) and 
                    issubclass(getattr(module,on),PyQt4.QtCore.QObject))]
    # now rewrite the source to statically add pyqtSignals as attributes
    # for each method in each class (not inherited from PyQt4.QtCore.QObject)
    insrec=[]
    for c in classes_to_dress:
        # get the non-inherited methods
        meths_to_dress=[m for m in dir(c) if m not in dir(PyQt4.QtCore.QObject)]
        for m in meths_to_dress: 
            # find the line of source code on which method is defined
            try: 
                if inspect.isclass(getattr(c,m)): continue
                if inspect.getmodule(getattr(c,m))!=module: continue
                firstline=inspect.getsourcelines(getattr(c,m))[1]
            except IOError: continue
            # create lines to insert signal defns and wrapper statement
            sigins=["___s_"+m+"_tofire=PyQt4.QtCore.pyqtSignal(dict)"]
            sigins+=["___s_"+m+"_fired=PyQt4.QtCore.pyqtSignal(dict)"]
            sigins+=["@wrap_signals"]
            insrec.append((sigins,firstline))
    module_source=inspect.getsource(module).split("\n")
    # sort backward by line number
    insrec=sorted(insrec, key=lambda tup: -tup[1])
    # insert the sourcelines for this method
    for ins in insrec:
        # determine appropriate tablevel
        beg=re.split('(\s*)',module_source[ins[1]-1])[1]
        module_source_b=module_source[0:(ins[1]-1)]
        module_source_e=module_source[ins[1]-1:]
        module_source_m=[]        
        for lin in ins[0]:
            module_source_m+=[beg+lin]
        module_source=module_source_b+module_source_m+module_source_e
    # now define the wrapper function to emit signals
    wrap_body="""
import inspect
def wrap_signals(fn):
    def fnc(*args,**kwargs):
        getattr(args[0],"_"+args[0].__class__.__name__+"_"+"__s_"+fn.func_name+"_tofire").emit({"args":args,"kwargs":kwargs})
        res=fn(*args,**kwargs)
        getattr(args[0],"_"+args[0].__class__.__name__+"_"+"__s_"+fn.func_name+"_fired" ).emit({"args":args,"kwargs":kwargs})
        return res
    return fnc
    """
    # assemble the source code and execute it within a new module context
    module_source=wrap_body+"\n".join(module_source)
    mymodule = imp.new_module(module_name)
    exec(module_source,mymodule.__dict__)
    # return the module
    return mymodule

def test():
    """
    this should result in a lot of 'peep's written to stdout until recursion
    depth is reached.
    """
    hdf5_liveheap=_signal_dressed_import("hdf5_liveheap")
    g1=hdf5_liveheap.glab_datastore()
    g2=hdf5_liveheap.glab_datastore()
    g1._glab_datastore___s_peep_fired.connect(g2.peep)
    g2._glab_datastore___s_peep_fired.connect(g1.peep)
    g1.peep({})