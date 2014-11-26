# -*- coding: utf-8 -*-
"""
Created on Fri Mar 21 19:53:48 2014

This module contains class definitions to handle data input from experiment
hardware - it allows the XTSM server to attach incoming data 'databombs' to
a list,  stream them raw to disk, unpack their contents, notify listeners
of their arrival, and create copies and links to the data for other elements

This is managed through two primary classes and their subclasses: 

    DataBombList
        FileStream
        DataBomb
    DataListenerManager
        DataListener
        
@author: Nate
"""

import msgpack, msgpack_numpy, StringIO, sys, time, struct, uuid, io, datetime
msgpack_numpy.patch()
from xml.sax import saxutils

class xstatus_ready():
    """
    Inheritance class to add a status output in xml-format to any object
    """
    def xstatus(self):
        """
        returns status of the listener as xml, and follows-on to child objects
        """
        status="<"+self.__class__.__name__+">"
        status+=self.iterate_dict(vars(self))
        status+="</"+self.__class__.__name__+">"
        return status
        
    def iterate_dict(self,dictelm):
        """
        steps through a dictionary
        """
        status=''
        for var in dictelm.keys():
            status+="<"+var+">"
            if type(dictelm[var])==type({}): status+=self.iterate_dict(dictelm[var])            
            elif hasattr(dictelm[var],'xstatus'): 
                status+=dictelm[var].xstatus()
            else: status+=saxutils.escape(str(dictelm[var]))
            status+="</"+var+">"                
        return status

class DataBombList(xstatus_ready):
    """
    A class to define a list of dataBombs, and organize their deployment
    
    params probably should include an element keyed 'dataListenerManagers'
    with a list of such elements who are sensitive to these bombs
    """
    def __init__(self,params={}):
        defaultparams={ }
        for key in params.keys(): defaultparams.update({key:params[key]})
        for key in defaultparams.keys(): setattr(self,key,defaultparams[key])   
        self.databombs={}
        self.stream=self.FileStream()

    def add(self,bomb):
        """
        adds a bomb to the list - the bomb input is expected to be of the 
        messagepack format.  Returns unique identifier assigned to bomb
        """
        if bomb.__class__!=self.DataBomb: 
            try: bomb=self.DataBomb(bomb)
            except: 
                raise self.BadBombError
                return
        self.databombs.update({bomb.uuid:bomb})
        return bomb.uuid
        
    def deploy(self,criteria):
        """
        deploys bombs based on selection criteria, which can be:
            'all' - deploys all bombs in the list
            'next' - deploys one based on a First-In-First-Out (FIFO) model
            uuid - deploys by the unique identifier assigned to the bomb on add
        """
        if not hasattr(self,'dataListenerManagers'): self.dataListenerManagers=[]
        def all_c(o):
            for bomb in o.databombs:
                bomb.deploy(o.stream,self.dataListenerManagers)
        def next_c(o):
            o.databombs[min([(bomb.timestamp,bomb.uuid) for bomb in o.databombs])[1]].deploy(o.stream,self.dataListenerManagers)
        ops={ 'all': all_c, 'next':next_c }
        try: ops[criteria](self)
        except KeyError: 
            try: self.databombs[criteria].deploy(self.stream,self.dataListenerManagers)
            except KeyError: raise self.UnknownBombError

    class BadBombError(Exception):
        pass

    class UnknownBombError(Exception):
        pass

    class FileStream(xstatus_ready):
        """
        A custom file stream object for data bombs; wraps io module to create
        an infinite output stream to a series of files of approximately one
        'chunksize' length.  As data is written in, this stream will automatically
        close files that exceed the chunksize and open another.  the write method
        will return the name data was written into - no chunk of data passed in 
        a single call to write will be segmented into multiple files
        """
        def __init__(self, params={}):
            today=datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d')
            defaultparams={ 'timecreated':time.time()
                            , 'chunksize': 100000000, 'byteswritten' : 0
                            , 'location_root':'vortex.phys.psu.edu/raw_buffers/DBFS/'+today+'/'}
            for key in params.keys(): defaultparams.update({key:params[key]})
            for key in defaultparams.keys(): setattr(self,key,defaultparams[key])   
            self.location=self.location_root+str(uuid.uuid1())+'.msgp'
            self.stream=io.open(self.location,'ab')
            self.filehistory=[self.location]

        def __del__(self):
            """
            This will assure file stream is closed when object is destroyed,
            and will output a log file 
            """
            self.stream.close()
            self.output_log()

        def output_log(self):
            """
            outputs a log of recently written files
            """
            logstream=io.open(self.location_root+'DBFS_LOG.txt','a')
            timeheader=datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S') + " through "+datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
            logstream.write("""
                            This is a log of file writes from the DataBomb module:
                            This module has written the files below from the time period
                            
                            """ + timeheader + "\n"
                            + '\n'.join(self.filehistory))
            
        def write(self,bytestream, preventFrag=False):
            """
            writes bytes to the io stream - if the total bytes written by this
            and previous calls since last chunk started exceeds chunksize, 
            opens a new file for the next chunk after writing the current request
            
            returns the file location of the chunk written.
            """
            self.byteswritten+=len(bytestream)
            self.stream.write(bytestream)
            loc=self.location
            if ((self.byteswritten > self.chunksize) and (not preventFrag)): 
                self.chunkon()
            return loc
            
        def chunkon(self):
            """
            this method creates a file for the next chunk of data
            """
            self.stream.close()
            self.location=self.location_root+str(uuid.uuid1())+'.msgp'            
            self.stream=io.open(self.location,'ab')
            self.filehistory.append(self.location)
            self.byteswritten=0

    class DataBomb(xstatus_ready):
        """
        The databomb class is meant to implement a socket-based drop of data into
        the XTSM webserver.  Data should arrive as an HTTP post request, with a single
        argument as payload, in the form of a messagepack formatted binary string.
        (The messagepack may contained as many named variables as needed).  The 
        databomb class contains methods for unpacking, and will strip data identifying
        the generator.  This data is used to notify listeners the data is present
        using the DataListenerManager and DataListenerManager.DataListener classes.
        Furthermore, databombs can be automatically streamed to disk as they arrive
        as a means of (vertical) raw data storage.
        """
        def __init__(self,messagepack):
            self.messagepack=messagepack
            self.timestamp=time.time()
            self.uuid='DB'+uuid.uuid1().__str__()
            
        def unpack(self):
            """
            Unpacks bytes from messagepack into key-value pair data
            in a dictionary; extract sender.  Looks for some optional special fields:
                sender: a string labeling the sender; choosing a unique id is sender's responsibility            
                shotnumber: an integer representing the shotnumber
                repnumber: an integer representing the repetition number
                onunpack: a string of python commands to execute on unpack
            """
            self.data=msgpack.unpackb(self.messagepack)
            notify_data_elms=['sender','shotnumber','repnumber']
            for elm in notify_data_elms:        
                try: self.notify_data.append({elm:self.data[elm]})
                except KeyError: pass
            try: 
                self.unpack_instructions=self.data['onunpack']
                try: 
                    rbuffer = StringIO()
                    sys.stdout = rbuffer
                    exec(self.unpack_instructions,self.data)
                    if self.data.has_key('__builtins__'): 
                        del self.data['__builtins__']
                    sys.stdout = sys.__stdout__ 
                    self.data.update({"onunpack_response":rbuffer.getvalue()})
                except: self.data.update({"onunpack_error":True})
            except KeyError: pass
            
        def stream_to_disk(self,stream):
            """
            streams bytes out to file object for raw-receipt-storage 
            appends a header to identify the bomb by its uuid, followed by timestamp,
            then raw data in its messagepack byte stream -
            entire object should be unpackable using messagepack unpackb routine
            twice - first to extract 'data' element, then to unpack data
            """
            idheader = msgpack.packb('id')+msgpack.packb(str(self.bombid))
            timeheader = msgpack.packb('timestamp')+msgpack.packb(str(self.timestamp))
            dataheader = '\xdb' + struct.pack('>L',len(self.messagepack))
            if not hasattr(self,'raw_links'): self.raw_links=[]
            self.raw_links.append(stream.write('\x83' + idheader + timeheader + dataheader, preventFrag=True))
            stream.write(self.messagepack)
            
        def deploy_fragments(self,listenerManagers):
            """
            sends individual data elements to destination in XTSM generators;
            intended to establish links to saved raw data, append to horizontal
            stacks as requested in xtsm, and initiate analyses - listeners should
            already have been installed in a manager by the XTSM elements, and
            this deployment should trigger them
            """
            if not hasattr(listenerManagers,'__iter__'): listenerManagers=[listenerManagers]
            for fragment in self.data.keys():
                for listenerManager in listenerManagers:
                    self.notify_data.update({"fragmentName":fragment})                    
                    listenerManager.notify_data_present(self.notify_data,{fragment:self.data[fragment]},{fragment:[f+"["+fragment+"]" for f in self.raw_links]})
            try: del self.notify_data["fragmentName"]
            except KeyError: pass
            
        def deploy(self,stream,listenerManagers):
            """
            streams data to disk, unpacks and deploys fragments
            """
            self.stream_to_disk(stream)
            self.unpack()
            self.deploy_fragments(listenerManagers)
        
class DataListenerManager(xstatus_ready):
    """
    A class to manage data listeners
    """
    def __init__(self):
        self.listeners={}
        
    def spawn(self,params={}):
        """
        creates a listener for data returned from
        apparatus / input hardware; use when an experiment is defined and expects
        data to be returned and either linked to the generator or processed in some
        way

        arguments passed in by dictionary -
        listen_for - identifies what to listen for as a key-value dictionary of must-haves 
        generator  identify who is listening as ({'fasttag':XXXX, 'xtsm': xtsm_object } for an XTSM element)
        onlink - callback method after data has been linked in to listener
        onattach - callback method after data has been attached to listener
        onclose - callback after item is destroyed 
        """
        defaultparams={'listen_for':{'sender':'','shotnumber':-1,'repnumber': None}
                        , 'timecreated':time.time(), 'generator': None
                        , 'timeout':360 }
        for key in params.keys(): defaultparams.update({key:params[key]})
        newguy=self.DataListener(defaultparams)        
        self.listeners.update({newguy.id:newguy})
    
    def notify_data_present(self, generator_info, data, datalinks):
        """
        method for data to announce its presence 
        searches for relevant listeners and links or attaches as desired
        listeners will try to match generator_info (a dictionary) and express interest
        if they do, data will be linked or attached as they request
        """
        for listener in self.listeners:
            if listener.query_interest(generator_info):
                (listener.getMethod())(generator_info,data,datalinks)

    def flush(self):
        """
        Cleans up listener tree by removing listener's who have timed-out or
        reached their designated number of collection events
        """
        for listener in self.listeners.keys():
            if self.listeners[listener].query_dead(): del self.listeners[listener]

    class DataListener(xstatus_ready):
        """
        A class of objects that define a 'listener' for data returned from
        apparatus / input hardware; use when an experiment is defined and expects
        data to be returned and either linked to the generator or processed in some
        way
        
        arguments passed in by dictionary of arguments - 
        listen_for - identifies what to listen for as a key-value dictionary of must-haves 
        generator - identifies who is listening as ({'fasttag':XXXX, 'xtsm': xtsm_object } for an XTSM element)
        onlink - callback method after data has been linked in to listener
        onattach - callback method after data has been attached to listener
        onclose - callback after item is destroyed 
        """
        def __init__(self,params={}):
            """
            constructor for class
            """
            self.id='DL'+str(uuid.uuid1())
            defaultparams={'listen_for':{'sender':'','shotnumber':-1,'repnumber': None}
                            , 'timecreated':time.time(), 'generator': None
                            , 'timeout':360, 'eventcount':1 }        
            for key in params.keys(): defaultparams.update({key:params[key]})
            self.datalinks=[]
            self.expirationtime=time.time()+defaultparams['timeout']
            for key in defaultparams.keys():
                setattr(self,key,defaultparams[key])   
    
        def __del__(self):
            """
            NOTE:  listener must be killed by its owner manager - this is prone to cause memory leak
            """
            if hasattr(self,'onclose'): self.onclose(self)
        
        def query_interest(self, generator_id):
            """
            returns true if this listener is interested in data from the 
            provided generator id
             - a match will be flagged if every element in the listener's dictionary
             is matched by the event's generator id dictionary - however the generator
             may provide more info than necessary, and the listener need not specify them all
            """
            for element in self.listen_for.keys():
                try:  
                    if self.listen_for[element] != generator_id[element]: return False
                except KeyError: return False
            return True
    
        def query_dead(self):
            """
            checks whether listener has passed timeout or has already responded
            to its event(s)
            """
            if self.expirationtime<time.time(): return True
            if self.eventcount<=0: return True
            return False
    
        def attachdata(self,data,datalinks):
            """
            Attaches the data the listener is looking for directly
            """
            self.data=data
            self.eventcount-=1
            if hasattr(self,'onattach'): self.onattach(self)
    
        def linkdata(self,data,datalinks):
            """
            Links the data the listener is looking for - 
            the link should take the form of a string forming a resource locator;
            intended for linking to files (hdf5 via liveheaps, or raw data from bomb file dumps)
            """
            self.datalinks.append(datalinks)
            self.eventcount-=1            
            if hasattr(self,'onlink'): self.onlink(self)

        def getMethod(self):
            """
            returns the method, link or attach, for this listener
            """
            try: 
                if self.method=='attach': return self.attachdata
                else: return self.linkdata
            except NameError: return self.linkdata 
            return self.linkdata