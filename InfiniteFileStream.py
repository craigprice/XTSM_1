# -*- coding: utf-8 -*-
"""
Created on Sat Apr 05 21:26:33 2014

@author: Nate
"""

import time, datetime, uuid, io, os
import xstatus_ready
import file_locations
import XTSM_Server_Objects
import msgpack

DEFAULT_CHUNKSIZE=100*1000*1000

class FileStream(xstatus_ready.xstatus_ready, XTSM_Server_Objects.XTSM_Server_Object):
    """
    A custom file stream object for data bombs and XTSM stacks; wraps io module to create
    an infinite output stream to a series of files of approximately one
    'chunksize' length.  As data is written in, this stream will automatically
    close files that exceed the chunksize and open another.  the write method
    will return the name data was written into - no chunk of data passed in 
    a single call to write will be segmented into multiple files
    """
    def __init__(self, params={}):
        print "class FileStream, func __init__()"
        today = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d')
        defaultparams = { 'timecreated':time.time(),
                       'chunksize': DEFAULT_CHUNKSIZE,
                       'byteswritten' : 0}
        try:
            location_root = file_locations.file_locations[params['file_root_selector']][uuid.getnode()]
            defaultparams.update({'location_root':location_root+'/'+today+'/'})
        except KeyError: 
            print "error"
            raise self.UnknownDestinationError
        for key in params.keys():
            defaultparams.update({key:params[key]})
        for key in defaultparams.keys():
            setattr(self, key, defaultparams[key])   
        self.location = self.location_root + str(uuid.uuid1()) + '.msgp'
        try: 
            self.stream = io.open(self.location, 'ab')
        except IOError: #Folder doesn't exist, then we make the day's folder.
            os.makedirs(self.location_root)
            self.stream = io.open(self.location, 'ab')
            self.write(msgpack.packb('}'))
        self.filehistory = [self.location]

    class UnknownDestinationError(Exception):
        pass

    def __del__(self):
        """
        This will assure file stream is closed when object is destroyed,
        and will output a log file 
        """
        print "deleting nicely"
        self.stream.write(msgpack.packb('{'))
        self.stream.close()
        self.output_log()

    def output_log(self):
        """
        outputs a log of recently written files
        """
        logstream=io.open(self.location_root+'DBFS_LOG.txt','a')
        time_format = '%Y-%m-%d %H:%M:%S'
        time1 = datetime.datetime.fromtimestamp(time.time()).strftime(time_format)
        time2 = datetime.datetime.fromtimestamp(time.time()).strftime(time_format)
        timeheader= time1 + " through "+ time2
        msg = "\nThis is a log of file writes from the DataBomb module:\n"
        msg = msg + "This module has written the files below from the time period\n"
        msg = msg + timeheader + '\n\n'.join(self.filehistory)
        logstream.write(unicode(msg))
        logstream.close()
        
    def write(self,bytestream, keep_stream_open=False):
        """
        writes bytes to the io stream - if the total bytes written by this
        and previous calls since last chunk started exceeds chunksize, 
        opens a new file for the next chunk after writing the current request
        
        returns the file location of the chunk written.
        """
        self.byteswritten += len(bytestream)
        self.stream.write(bytestream)
        if (self.byteswritten > self.chunksize) and (not keep_stream_open): 
            self.chunkon()
            self.byteswritten += len(bytestream)
            self.stream.write(bytestream)
        return self.location
        
    def chunkon(self):
        """
        this method creates a file for the next chunk of data
        """
        self.stream.write(msgpack.packb('{'))
        self.stream.close()
        self.location = self.location_root + str(uuid.uuid1()) + '.msgp'            
        self.stream = io.open(self.location,'ab')
        self.stream.write(msgpack.packb('}'))
        self.filehistory.append(self.location)
        self.byteswritten = 0
        
    def __flush__(self):
        self.stream.flush()
        self.chunkon()
        self.output_log()