# -*- coding: utf-8 -*-
"""
Created on Sun Aug 10 12:18:56 2014

@author: Nate
"""
import DataBomb
import uuid, time, numpy, pdb

default_databomb_destination_priorities = ["active_parser","169.254.174.200:8084","169.254.174.200:8083","127.0.0.1:8084","127.0.0.1:8083"]

class Glab_Instrument():
    """
    Core class for an instrument interface, which initializes hardware,
    collects data, and posts it to an XTSM server somewhere, running from within
    an XTSM server (not necessarily the same it is running within (i.e. is attached to))
    """
    def __init__(self,params={}):
        self.generator_uid=str(uuid.uuid1())
        try: self.server=params['server']
        except KeyError:
            print "WARNING:: Instrument " + str(self)+" created without associated server"
            self.server=None
        self.server_tasks=[]
#        pdb.set_trace()
        if params.has_key("create_example_pollcallback"):
            if params["create_example_pollcallback"]:
                self._server_poll_example=self._Xserver_poll
                self._server_callback_example=self._Xserver_callback
        if self.server:
            server_polls=[m for m in dir(self) if "_server_poll" in m]
            server_callbacks=[m for m in dir(self) if "_server_callback" in m]
            for poll in server_polls:
                callback=poll.replace("poll","callback")
                if callback not in server_callbacks:
                    print "WARNING:: Instrument provides poll mechanism without a callback; it is ignored"
                self.server_tasks.append(self.server.attach_poll_callback(getattr(self,poll),getattr(self,callback),getattr(self,poll)._poll_period))
    def __del__(self):
        # this won't be sufficient to prevent memory leaks stemming from server callbacks -
        # their linkage to the server will prevent an instrument from being
        # garbage collected.
        for task in self.server_tasks:
            task.stop()
            
    def register_server_callback(self,callback,execute_time):
        """
        schedules a routine to be executed via the attached server at
        a specific machine time
        """
        pass # not written yet            
        
    def serve_data(self, data):
        """
        routine to post data through the attached server using a databomb
        data is provided by the incoming argument data (ideally a dictionary)
        
        by default this will append identifiers for the data [time, generator ids, etc...]
        any of which can be overwritten by items in incoming data
        """
        print "serving data"
        if not self.server: 
            return False
            
        # assemble the data payload
        if type(data)!=type({}): data={"data":data}
        # some default data-packaging parameters 
        default_data = {"generator":str(self), "generator_instance":self.generator_uid,"time_served":time.time(), "destination_priorities":default_databomb_destination_priorities}     
        try: default_data.update({"server_instance":self.server.uuid,"server_machine":self.server.hostid})
        except: pass
        # attempt to get the active shot-number and rep_number from the server
        try: default_data.update({"shotnumber":self.server.dataContexts['default']['_running_shotnumber']})  
        except: pass     
        try: default_data.update({"repnumber":self.server.dataContexts['default']['_running_repnumber']})  
        except: pass  
        default_data.update(data)
        data=default_data
        # construct the data-bomb and instruct server to send it
        if not hasattr(self.server,"DataBombDispatcher"):
            self.server.DataBombDispatcher=DataBomb.DataBombDispatcher(params={"server":self.server})
        self.last_served_dispatchid=self.server.DataBombDispatcher.add(data)

    def _Xserver_poll(self):
        """
        An example poll-callback routine - will only be attached if the parameter
        create_example_pollcallback is set to true in initialization
        """
        # this triggers every-other time it is polled
        print "generic instrument polled"
        if not hasattr(self,"_poll_example_it"): self._poll_example_it = 0
        self._poll_example_it = (self._poll_example_it+1)%2 
        if self._poll_example_it==0:
            return True
        else: return False
    _Xserver_poll._poll_period=15.
    
    def _Xserver_callback(self):
        """
        An example poll-callback routine
        """
        print "generic instrument callback called"
        # generate some random data and return it using the serve data mechanism
        self.serve_data(numpy.random.rand(100,100))