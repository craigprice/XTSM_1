# -*- coding: utf-8 -*-
"""
Created on Tue Mar 25 16:29:19 2014

@author: Nate
"""
from enthought.traits.api import HasTraits
from enthought.traits.api import Int as TraitedInt
from enthought.traits.api import Int as TraitedStr

class Experiment_Sync_Group(HasTraits):
    active_xtsm = TraitedStr('initial')
    shotnumber = TraitedInt(0)
    def __init__(self,server):
        self.server=server
    def _active_xtsm_changed(self, old, new): 
        self.server.broadcast("{'active_xtsm_post':"+str(new)+"}")
    def _shotnumber_changed(self, old, new): 
        self.server.broadcast("{'shotnumber':"+str(new)+"}")

#class Something(object):
#    @property
#    def some_value(self):
#        return self._actual
#    @some_value.setter
#    def some_value(self, value):
#        print "some_value changed to", value
#        self._actual = value