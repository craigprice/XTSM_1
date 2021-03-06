"""
Objects created in default context for various parts of XTSM server and parser functions - 
each entry has a typename as key, with a dictionary as value, in which the keys
are machine id numbers (as returned by uuid.getnode() on the machine in question)
and the value is a filepath root ending in '/' or a file location.


Created on Sat Apr 05 21:32:42 2014

@author: Nate
"""

import uuid,sys
#imports={264840316731455L: None, 11603160389L: ["PI_Camera_Python","gnosis"] }
#modules={}
#for mod in imports[uuid.getnode()]:
#    setattr(sys.modules[__name__],mod,__import__(mod))

fqhe_master_init="""
import PI_Camera_Python
self.dataContexts['default'].update({'Princeton_CCD':PI_Camera_Python.Princeton_CCD(params={'server':self})})
self.dataContexts['default']['Princeton_CCD'].set_autoframing()
self.dataContexts['default']['Princeton_CCD'].start_acquisition()
"""

natural_init="""
import glab_instrument
self.dataContexts['default'].update({'Test_instrument':glab_instrument.Glab_Instrument(params={'server':self,'create_example_pollcallback':True})})
"""
# the dictionary below has an entry for each machine, with a script
# that should be executed at the time the server is initialized
initializations={264840316731455L: natural_init, 
                 11603160389L: fqhe_master_init}

