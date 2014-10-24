# -*- coding: utf-8 -*-
"""
Created on Sat Apr 05 21:26:33 2014

@author: Nate
"""

import time, datetime, uuid, io, os
import xstatus_ready
import file_locations
import XTSM_Server_Objects
import pdb
import msgpack
import cStringIO
import zlib
import zipfile

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
        self.compression_strength = 9 # 1-9, 1 fastest, least compression. 6 default
        self.compressobj = zlib.compressobj(self.compression_strength)
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
            #self.zip_file = zipfile.ZipFile(self.location, mode='a', compression=zipfile.ZIP_DEFLATED)
            self.stream = io.open(self.location, 'ab')
        except IOError: #Folder doesn't exist, then we make the day's folder.
            os.makedirs(self.location_root)
            #self.zip_file = zipfile.ZipFile()
            self.stream = io.open(self.location, 'ab')
            #self.write(msgpack.packb('}'))
        self.filehistory = [self.location]
        print self.location

    class UnknownDestinationError(Exception):
        pass

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
        cBlock = self.compressobj.compress(bytestream)
        self.stream.write(cBlock)
        if (self.byteswritten > self.chunksize) and (not keep_stream_open): 
            self.__flush__()
            self.stream.write(bytestream)
            self.byteswritten += len(bytestream)
        return self.location
        
        
    def open_file(self):
        fileName = 'c:/wamp/www/raw_buffers/DBFS/2014-10-13/6ea6bf2e-52fe-11e4-b225-0010187736b5.msgp'
        import zlib
        import cStringIO
        import zipfile
        zf = zipfile.ZipFile(fileName, 'r')
        print zf.namelist()
        for info in zf.infolist():
            print info.filename
            print '\tComment:\t', info.comment
            print '\tModified:\t', datetime.datetime(*info.date_time)
            print '\tSystem:\t\t', info.create_system, '(0 = Windows, 3 = Unix)'
            print '\tZIP version:\t', info.create_version
            print '\tCompressed:\t', info.compress_size, 'bytes'
            print '\tUncompressed:\t', info.file_size, 'bytes'
            print
        #info = zf.getinfo(filename)
        #data = zf.read(filename)
        f = open(fileName,'rb')
        c = zlib.decompressobj()
        cBlock = c.decompress(f.read())
        print cBlock
        output = cStringIO.StringIO(cBlock)
        unpacker = msgpack.Unpacker(output,use_list=False)# If data was msgpacked
        print unpacker.next()
        print cBlock
        
    def chunkon(self):
        """
        this method creates a file for the next chunk of data
        """
        #self.stream.write(msgpack.packb('{'))
        self.stream.close()
        self.location = self.location_root + str(uuid.uuid1()) + '.msgp'            
        self.stream = io.open(self.location,'ab')
        self.compressobj = zlib.compressobj(self.compression_strength)
        #self.stream.write(msgpack.packb('}'))
        self.filehistory.append(self.location)
        self.byteswritten = 0
        
    def __flush__(self):
        cBlock = self.compressobj.flush()
        self.stream.write(cBlock)
        self.stream.flush()
        self.chunkon()
        self.output_log()
        
        
##############################################################################


class FS(xstatus_ready.xstatus_ready, XTSM_Server_Objects.XTSM_Server_Object):
    """
    CP
    A custom file stream object for data bombs and XTSM stacks; wraps zipfile
    module. As data is written in, this stream will automatically
    close archives that exceed the archive_size and open another.  the write method
    will return the full path to the data. no chunk of data passed in 
    a single call to write will be segmented into multiple files.
    """
    def __init__(self, params={}):
        print "class FS, func __init__()"
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
        self.location = self.location_root + str(uuid.uuid1()) + '.zip'
        try: 
            self.zip_file = zipfile.ZipFile(self.location, mode='a', compression=zipfile.ZIP_DEFLATED)
        except IOError: #Folder doesn't exist, then we make the day's folder.
            os.makedirs(self.location_root)
            self.zip_file = zipfile.ZipFile(self.location, mode='a', compression=zipfile.ZIP_DEFLATED)
        self.filehistory = [self.location]
        print self.location

    class UnknownDestinationError(Exception):
        pass

    def output_log(self):
        """
        outputs a log of recently written files
        """
        logstream = io.open(self.location_root + 'DBFS_LOG.txt', 'a')
        time_format = '%Y-%m-%d %H:%M:%S'
        time1 = datetime.datetime.fromtimestamp(time.time()).strftime(time_format)
        time2 = datetime.datetime.fromtimestamp(time.time()).strftime(time_format)
        timeheader= time1 + " through "+ time2
        msg = "\nThis is a log of file writes from the DataBomb module:\n"
        msg = msg + "This module has written the files below from the time period\n"
        msg = msg + timeheader + '\n\n'.join(self.filehistory)
        logstream.write(unicode(msg))
        logstream.close()
        
    def write(self, msg, keep_stream_open=False):
        """
        writes a msg to the zip archive.
        """
        info = zipfile.ZipInfo(fileName)
        info.date_time = time.localtime(time.time())
        info.compress_type = zipfile.ZIP_DEFLATED
        info.comment = 'Remarks go here'
        self.byteswritten += len(bytestream)
        cBlock = self.compressobj.compress(bytestream)
        self.stream.write(cBlock)
        if (self.byteswritten > self.chunksize) and (not keep_stream_open): 
            self.__flush__()
            self.stream.write(bytestream)
            self.byteswritten += len(bytestream)
        return self.location
        
        
    def open_file(self):
        fileName = 'c:/wamp/www/raw_buffers/DBFS/2014-10-13/6ea6bf2e-52fe-11e4-b225-0010187736b5.msgp'
        import zlib
        import cStringIO
        import zipfile
        zf = zipfile.ZipFile(fileName, 'r')
        print zf.namelist()
        for info in zf.infolist():
            print info.filename
            print '\tComment:\t', info.comment
            print '\tModified:\t', datetime.datetime(*info.date_time)
            print '\tSystem:\t\t', info.create_system, '(0 = Windows, 3 = Unix)'
            print '\tZIP version:\t', info.create_version
            print '\tCompressed:\t', info.compress_size, 'bytes'
            print '\tUncompressed:\t', info.file_size, 'bytes'
            print
        #info = zf.getinfo(filename)
        #data = zf.read(filename)
        f = open(fileName,'rb')
        c = zlib.decompressobj()
        cBlock = c.decompress(f.read())
        print cBlock
        output = cStringIO.StringIO(cBlock)
        unpacker = msgpack.Unpacker(output,use_list=False)# If data was msgpacked
        print unpacker.next()
        print cBlock
        
    def chunkon(self):
        """
        this method creates a file for the next chunk of data
        """
        #self.stream.write(msgpack.packb('{'))
        self.stream.close()
        self.location = self.location_root + str(uuid.uuid1()) + '.msgp'            
        self.stream = io.open(self.location,'ab')
        self.compressobj = zlib.compressobj(self.compression_strength)
        #self.stream.write(msgpack.packb('}'))
        self.filehistory.append(self.location)
        self.byteswritten = 0
        
    def __flush__(self):
        cBlock = self.compressobj.flush()
        self.stream.write(cBlock)
        self.stream.flush()
        self.chunkon()
        self.output_log()