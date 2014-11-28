# -*- coding: utf-8 -*-
"""
Created on Fri Mar 28 12:26:43 2014

@author: Nate
"""


import pdb,types,inspect

debug = True

class restricted_pickle():
    def __getstate__(self):
        """
        pickling routine - pickles only elements with explicitly defined getstate/setstate methods - pickle is not
        generic enough to understand complex objects; this inheritance class makes it more so, at the cost
        of being non-inclusive
        """
        dictout={'type': str(self.__class__)}
        return dictout.update({'data':{aa:getattr(self,aa).__getstate__() for aa in dir(self) if hasattr(getattr(self,aa),'__getstate__')}})

    def __setstate__(self,dictin):
        """
        unpickling routine - unpickles only elements with explicitly defined getstate/setstate methods 
        """
        for elm in dictin['data'].keys(): 
            try: # define new element of this type, call its setstate function
                setattr(self,elm,getattr(main, str(dictin['data'][elm]['type'].__class__).split("__main__.")[1]))                
                elm.__setstate__(dictin[elm])
            except KeyError: pass 

    
class B(restricted_pickle):
    monkey=1        
    def __getstate__(self):
        return {'type':'__main__.int','data':{'monkey':self.monkey}}
class A(restricted_pickle):
    cat=B()

st = types.FunctionType(pdb.set_trace.func_code, pdb.set_trace.func_globals, 
                        name = pdb.set_trace.func_name, 
                        argdefs = pdb.set_trace.func_defaults,
                        closure = pdb.set_trace.func_closure)
def save_and_trace():
    if not debug: return
    print 'saving state...'
    filename="C:\\wamp\\vortex\\WebSocketServer\\serverlog.pkl"
    filew=open(filename,"w")
    #pdb.set_trace()
    #pickle.dump(theBeast,filew)

    print 'debug flagged at line ' + str(inspect.getouterframes(inspect.currentframe())[1][2])
    st()
pdb.set_trace=save_and_trace
