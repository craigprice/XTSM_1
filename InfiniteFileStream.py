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
import pprint

DEBUG = False

class Filestream(xstatus_ready.xstatus_ready, XTSM_Server_Objects.XTSM_Server_Object):
    """
    CP
    A custom file stream object for data bombs and XTSM stacks; wraps zipfile
    module. the write method
    will return the full path to the data. no chunk of data passed in 
    a single call to write will be segmented into multiple files.
    """
    def __init__(self, params={}):
        if DEBUG: print "class FS, func __init__()"
        self.init_time = time.time()
        self.today = datetime.datetime.fromtimestamp(self.init_time).strftime('%Y-%m-%d')
        self.defaultparams = {'zip archive created':self.init_time}
        try:
            #self.location_root = file_locations.file_locations[params['file_root_selector']][uuid.getnode()]+'\\'+self.today+'\\'
            self.location_root = '..\\psu_data\\'+self.today+'\\'+params['filestream_folder']+'\\'
            self.backup_location_root = '..\\backup_psu_data\\'+self.today+'\\'+params['filestream_folder']+'\\'
            self.defaultparams.update({'location_root':self.location_root})
        except KeyError: 
            print "error"
            pdb.set_trace()
            raise self.UnknownDestinationError
        for key in params.keys():
            self.defaultparams.update({key:params[key]})
        for key in self.defaultparams.keys():
            setattr(self, key, self.defaultparams[key])  
        try:
            self.logstream = io.open(self.location_root + 'filestream_log.txt', 'a')
        except IOError: #Folder doesn't exist, then we make the day's folder.
            os.makedirs(self.location_root)
            self.logstream = io.open(self.location_root + 'filestream_log.txt', 'a')
        self.logstream.write(unicode('This is a log of file writes\n'))
        self.logstream.close()
        self.root_zip_name = str(uuid.uuid1()) + '.zip'
        if DEBUG: print "location_root", self.location_root

    class UnknownDestinationError(Exception):
        pass

    def output_log(self):
        """
        outputs a log of recently written files
        """
        self.logstream = io.open(self.location_root + 'filestream_log.txt', 'a')
        time_format = '%Y-%m-%d %H:%M:%S'
        time1 = datetime.datetime.fromtimestamp(self.init_time).strftime(time_format)
        timeheader= time1
        msg = "This module has written,\n"
        msg = msg + self.zip_file_name + '\\' + self.fileName + '\n'
        msg = msg + "at time, " + timeheader + '\n'
        self.logstream.write(unicode(msg))
        #pprint.pprint(unicode(dir(self)), logstream)
        self.logstream.close()
        
    def _write_file(self, msg, comments='', prefix='', extension='.dat', is_backup=False):
        """
        writes a file to the zip archive.
        """
        if is_backup:
            self.zip_file_name = self.backup_location_root + self.root_zip_name
        else:
            self.zip_file_name = self.location_root + self.root_zip_name
        if DEBUG: print "zip_file_name", self.zip_file_name
        try: 
            self.zip_file = zipfile.ZipFile(self.zip_file_name,
                                            mode='a',
                                            compression=zipfile.ZIP_DEFLATED,
                                            allowZip64=True)
        except IOError: #Folder doesn't exist, then we make the day's folder.
            if is_backup:
                os.makedirs(self.backup_location_root)
            else:
                os.makedirs(self.location_root)
            self.zip_file = zipfile.ZipFile(self.zip_file_name,
                                            mode='a',
                                            compression=zipfile.ZIP_DEFLATED,
                                            allowZip64=True)
        self.fileName = str(prefix) + str(uuid.uuid1()) + str(extension)
        info = zipfile.ZipInfo(self.fileName, date_time=time.localtime(time.time()))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.comment = comments + str(self.defaultparams)
        self.zip_file.writestr(info, msg)
        self.zip_file.close()
        self.output_log()
        return self.zip_file_name + "/" + self.fileName
        
        
    def write_file(self, msg, comments='', prefix='', extension='.dat', is_backup=False):
        """
        writes a file to the zip archive.
        """
        self._write_file(msg, comments=comments, prefix='Backup_'+prefix, extension=extension, is_backup=True)
        #self.check_todays_files()
        return self._write_file(msg, comments=comments, prefix=prefix, extension=extension, is_backup=False)
        
    def __flush__(self):
        pass
        
