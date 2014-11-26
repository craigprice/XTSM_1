# -*- coding: utf-8 -*-
"""
Created on Tue Apr 15 19:00:53 2014

@author: Nate
"""
import xstatus_ready
class XTSM_Server_Object():
    def __flush__(self):
        """
        A method called down the server object tree to flush all pending file
        dumps and data - intended to forcibly store data before a server shutdown
        """
        for child in self.__dict__:
            try: child.__flush__()
            except AttributeError: pass 

    def __periodic_maintenance__(self):
        """
        A method called down the server object tree to perform maintanence
        """
        for child in self.__dict__:
            try: child.__periodic_maintenance__()
            except AttributeError: pass 
