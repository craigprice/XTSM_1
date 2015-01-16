# -*- coding: utf-8 -*-
"""
Created on Tue May 21 15:19:04 2013

@author: Nate

This module defines a 'live heap' data class, which is essentially a stack
of like data items held in RAM, which are synchronously written out to an 
element in an hdf5 data file when the stack reaches a certain size.  
It is meant to provide transparent access to a heap of similar data taken
while some set of parameters is varied.  An example might be a series of 
images, each of which was taken at the end of a timing sequences generating
a BEC in an apparatus; each image corresponds to a specific iteration of the
experiment, labeled by a shotnumber (and optionally a repetition number).  
As this data is accumulated, it can be added to the live_heap, which 
manages the storage to disk by itself, and retains the latest portion in RAM 
ready for analysis in a transparent way. Ideally, the user does not need to 
be aware where the data currently resides.

this class is made ready for signaling through the pyqt signal mechanisms

common confusion:  following writes and appends to tables, the method .flush()
must be called on the pytables object self.table before data may be read back
from it.       
"""

import numpy,uuid,operator,os,time,types,itertools,numbers
import tables
import pdb
import pyqtgraph
import PyQt4
import xstatus_ready
import datetime

VERBOSE=True

class glab_datastore(PyQt4.QtCore.QObject,xstatus_ready.xstatus_ready):
    """
    This class wraps the pytables module to provide a data storage vehicle
    a single datastore is intended to interface with a single .hdf5 file
    on disk.
    Multiple live heaps can heave data into the same datastore.  
    """        
    def __init__(self, options={}):
        """
        constructor for datastore - should open or create an hdf5 file on disk
        to attach to - filepath should provide the path
        """
        PyQt4.QtCore.QObject.__init__(self) # this is here in case class is used with pyqt signals and slots
        self.id = str(uuid.uuid4()) # a unique identifier for the heap
        today = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d')
        self.location_root = '..\\psu_data\\' + today + '\\hdf5_heap\\'
        filename = self.location_root + str(self.id) + '.h5'
        
        self.options={"filepath":filename, "title":"Untitled" }
        self.options.update(options)

        try:
            self.h5 = tables.open_file(filename,
                                 mode="a",
                                 title=self.options["title"],
                                 driver="H5FD_SEC2",
                                 NODE_CACHE_SLOTS=0)
        except IOError:#Folder doesn't exist, then we make the day's folder.
            os.makedirs(self.location_root)
            self.h5 = tables.open_file(filename,
                                 mode="a",
                                 title=self.options["title"],
                                 driver="H5FD_SEC2",
                                 NODE_CACHE_SLOTS=0)        
        
        try:  # try to determine pre-existing file access records
            self.fileaccessgroup=self.h5.get_node("/","fa")    
            self.fatable=self.h5.get_node("/fa","access")    
        except tables.NoSuchNodeError:    # if they don't exist, create them
            self.fileaccessgroup=self.h5.create_group('/','fa','fileaccessgroup')
            self.fatable = self.h5.create_table(self.fileaccessgroup, 'access', self.AccessRecord , "Acess Records")
        self.handles=[] # an element to hold handles to individual heaps
        self.__record_action__("file opened") # record that the file was opened
        
    def __del__(self):
        """
        destructor for the datastore; meant to ensure file is flushed and
        closed on termination
        """
        self.__record_action__('file closed') # record closing of the file
        self.h5.close()
        for hind in xrange(len(self.handles)):  # close handles
            self.handles[hind].close()
        print "file "+self.options["filepath"]+" closed"

    def __record_action__(self, action):
        """
        records a file access action
        """
        facreaterec=self.fatable.row
        facreaterec['timestamp']=time.time()
        facreaterec['computerid']=os.environ['COMPUTERNAME']
        facreaterec['datastoreid']=self.id
        facreaterec['action']=action
        facreaterec.append()
        
    def flush(self):
        """
        flushes pending write requests to disk
        """
        self.__record_action__("file flush")        
        self.h5.flush()        
        
    def __str__(self):
        """
        string function output - representation of attached file
        """
        return self.h5.__str__()
        
    def view(self):
        """
        launches a viewer to browse contents of associated hdf file
        still working on this
`        """
        print self.h5
    
    def get_handle(self,element_id,element):
        """
        element must be a numpy array of the size desired.        
        
        links an element in the datastore to a liveheap by returning a handle
        corresponding to the provided element id.  id can be a string providing
        path to element in hdf5 style, or...
        if element does not exist, or an existing element has the wrong structure,
        creates a new element with _x appended to name
        """
        def exit_this(h):
            """
            exit routine - record action and return a data handle
            """
            t=self.dataHandle(h)
            self.handles.append(t)
            self.__record_action__("issued handle for "+str(element_id))
            return t
        # first create a numpy structured array as a descriptor for the table elements
        # start by finding a name from the id, assuming it can have path structure
        eparts=element_id.rsplit("/",1)
        table_name = eparts[-1]
        try:
            element.shape
        except AttributeError:#Want all data elements to be some kind of numpy array
            print "WARNING: Casting the element into numpy.asarray(element)"
            element = numpy.asarray(element)
            
        des = numpy.empty(1,dtype=[
                ("shotnumber",numpy.int64),
                ("repnumber",numpy.int64),
                (eparts[-1],element.dtype, element.shape)
                ])
        # now try to create or open the table, else looking for first unused name of type
        '''
        for ind in xrange(-1,1000):
            try: 
                h=self.h5.getNode("/"+element_id+("_"+str(ind))*(ind>0))
                if h.dtype==des.dtype: exit_this(h)
            except tables.exceptions.NoSuchNodeError: 
                h=self.h5.create_table("/",eparts[-1]+("_"+str(ind))*(ind>0),description=des.dtype)
                return exit_this(h)
        '''
        try: 
            h = self.h5.getNode("/"+table_name)
            if h.dtype == des.dtype:
                return exit_this(h)
            else:
                print "Types Don't Match"
                print h.dtype
                print des.dtype
        except tables.exceptions.NoSuchNodeError:
            print "Creating Table:", "/", table_name,des.dtype
            h = self.h5.create_table("/",table_name,description=des.dtype)
            return exit_this(h)
        
        for ind in xrange(0,100):
            print "WARNING: Could not find node with description:", element_id
            print "shotnumber =", des[0][0]
            print "repnumber =", des[0][1]
            print "data =", des[0][2].shape, des[0][2].dtype
            try:
                print "a"
                print "/"+table_name+("_"+str(ind))
                h = self.h5.getNode("/"+table_name+("_"+str(ind)))
                print "b"
                print h
                return exit_this(h)
            except tables.exceptions.NoSuchNodeError:
                print "c"
                h = self.h5.create_table("/",table_name+("_"+str(ind)),description=des.dtype)
                print "Creating node:", h,
                print "with description:", table_name+("_"+str(ind))
                print "shotnumber =", des[0][0]
                print "repnumber =", des[0][1]
                print "data =", des[0][2].shape, des[0][2].dtype
                pdb.set_trace()
                if h.dtype == des.dtype:
                    print "Using node:", h
                    return exit_this(h)
                else:
                    print "Error: in making table"
                    #print "Creating Table:", "/", table_name+("_"+str(ind))*(ind>0),des.dtype
                    #h = self.h5.create_table("/",table_name+("_"+str(ind))*(ind>0),description=des.dtype)
                    #return exit_this(h)

    def load_from_filestore(self,directory,tablename="Untitled",limit=None,dtype=numpy.float32):
        """
        Not intended to be used often - loads individual files from a directory
        and stores them in a named table in the datastore - unfinished
        """
        hh=None
        for dirname, dirnames, filenames in os.walk(directory):
            num=0
            # print path to all subdirectories first.
            for subdirname in dirnames:
                print os.path.join(dirname, subdirname)    
            # import data and append to an image stack.
            imgs=[]
            names=[]
            for filename in filenames:
                print os.path.join(dirname, filename)
                try: 
                    imgs.append(numpy.loadtxt(os.path.join(dirname, filename),dtype=dtype))
                    names.append(os.path.join(dirname, filename))
                    num+=1
                    if num>=limit:
                        return numpy.dstack(imgs)        
                    #del(imgs[0])
                except: 
                    print 'failed'
                if hh==None:
                    hh=self.get_handle("/"+tablename,imgs[0])

                try: hh.append(imgs[-1],num,0)
                except: pass
                
            return numpy.dstack(imgs)

    class dataHandle():
        """
        Provides access to an element in the datastore; primary means of 
        interface to data
        """
        def __init__(self,element):        
            self.table=element
            self.dataname=element.name
            self.status="open"
            
        def append(self,data,shotnumber,repnumber=0):
            """
            adds data to this table in file.
            """
            if self.status=="open":
                row=self.table.row
                row['shotnumber']=shotnumber
                row['repnumber']=repnumber
                try:
                    row[self.dataname]=data
                    row.append()
                except ValueError as e:
                    print e
                    print 'WARNING: Data was not Stored!'
            else:
                raise self.ClosedHandleError()

        def close(self):
            self.status="closed"
        
        class ClosedHandleError(Exception):
            def __str__(self): return "The corresponding file was closed" 
    
    class AccessRecord(tables.IsDescription):
        """
        structure for records of file access in associated h5 file
        """
        timestamp      = tables.FloatCol()   # timestamp of operation
        computerid     = tables.StringCol(36)  # name of machine performing op
        datastoreid    = tables.StringCol(36)  # type of action taken
        action         = tables.StringCol(36)  # type of action taken

    def peep(self,adict):
        """
        this function is used for testing the pyqtsignal_dressing module
        """
        print "peep"        
        
class glab_liveheap(PyQt4.QtCore.QObject):
    """
    This is the root class for live heaps.
    
    Live heaps are intended to facilitate run-time data collection and analysis,
    providing automated data-storage (holding a specified amount of recent data 
    elements in RAM, and archiving to disk afterward).  
    """
    def __init__(self,options={}):
        """
        Constructor for live heaps
        
        sizeof should be the maximum number of data elements to hold in dynamic memory
        element_structure should be a list of dimensions for each data element
        typecode should be the numpy-supported Python data type for each element
        FILENAME should specify the desired hdf5 file to link to the heap
        GENERATOR ... i forget ...
        DATANAME should specify the desired name of the element        
        """
        self.id="_"+str(uuid.uuid4()).replace("-","")
        # first define default options and override
        PyQt4.QtCore.QObject.__init__(self) # for signal/slotting
        default_options={"sizeof":None,
                         "element_structure":(), 
                         "typecode":numpy.dtype("float64"),
                         "filename":None, 
                         "dataname":"untitled_"+str(uuid.uuid1()),
                         "_warn_duplicates":True,
                         "use_reps":False }
        default_options.update(options)
        # if no stack size given, set RAM size to 10MByte
        if default_options["sizeof"]==None:
            try:
                size = default_options["typecode"].itemsize*reduce(operator.mul,default_options["element_structure"])
                default_options.update({"sizeof":int((1e+7)/size)})
            except TypeError:
                default_options.update({"sizeof":int((1e+7)/default_options["typecode"].itemsize)})
        # transfer to attributes of self
        for option in default_options.keys():
            setattr(self,option,default_options.get(option))
        # the data stack for RAM will be created immediately on intialization
        # and never redefined to avoid constant copying or re-reservation 
        self.stack=numpy.empty((self.sizeof,)+tuple(self.element_structure),dtype=self.typecode)
        # the stack is N+1 dimensional, with N the size of the element
        self.stackorders=numpy.array([-1 for a in xrange(self.sizeof)])
        self.current_order=0L
        # a stack order >=0 defines the arrangement, larger numbers represent later elements
        # -1 denotes empty element 
        self.shotnumbers=numpy.array([-1 for a in xrange(self.sizeof)])
        # shotnumbers are stored as absolute shotnumbers 
        self.repnumbers=numpy.array([-1 for a in xrange(self.sizeof)])
        # repnumbers are stored as absolutes
        self.archived=numpy.array([True for a in xrange(self.sizeof)])
        # archived is boolean representing whether or not this element exists on permanent storage
        #True is used as initialization here so that when the file is closed, it won't save the junk data that was created in the empty numpy array.
        self.last_pushed=0
        
    def __getitem__(self,indices):
        """
        item getter, returns elements to x[indices] call
        
        indices may be provided as a list of 1,2 or larger comma-separated indexing
        arguments.  the first index represents shotnumbers, and the final
        N arguments, with N the number of element dimensions, sub-array elements.
        if self.use_reps is set True, the repetition range is supplied as the
        second indexing element.  All elements may be specified using numpy conventions,
        as single elements, lists, or slices with standard syntax.  Additionally,
        string keywords may be supplied for each dimension, including 'all', 'first',
        or 'live' (shot/rep numbers).  Additional keywords can be supplied with the
        self.custom_indexing_table dictionary, which holds the string value as a key, 
        and corresponding value a function that returns a list of indices
        
        TODO:  catch / handle missing elements
        TODO:  implement 'first' for cases rep number not specified, and reps not 0
        TODO:  thurough testing and error-trapping
        """
        #pdb.set_trace()
        # first necessary to determine 'signature' of indices
        # how many dimensions are specified, and in what way
        
        if type(indices)!=types.TupleType: indices=(indices,)

        x_d={True:2,False:1}[self.use_reps] # number of dimensions in excess of elm's
        # if too many dimensions are provided, separate the overflow
        if len(indices)>(x_d+len(self.element_structure)): 
            over_spec=indices[x_d+len(self.element_structure):]
            indices=indices[0:x_d+len(self.element_structure)]
        # if too few dimensions are provided, pad with 'all's for data structure
        if len(indices)<(x_d+len(self.element_structure)):
            indices+=(u"all",)*(x_d+len(self.element_structure)-len(indices))
        inds=[] # array to hold arrays, each the indices of elements along
                # a given dimension
        # if not using reps, take 'first' rep matching shotnumber
        if not self.use_reps:
            indices=(indices[0],)+(u"first",)+tuple(indices[1:])
        if self.use_reps and len(indices)<(x_d+len(self.element_structure)):
            indices=(indices[0],)+(u"all",)+tuple(indices[1:])            
        # step through each dimension, convert specification into an array of indices
        n_dim=len(indices) # number of dimensions specified
        for dim,ind in zip(range(n_dim),indices):
            inds.append(self.__process_indices__(dim,ind,n_dim))
        # make a numpy array to hold the result
        res=numpy.empty((len(inds[0]),len(inds[1]))+tuple(self.stack[[0]+inds[2:]].shape),dtype=self.typecode)
        # for shotnumbers and repnumbers, must determine if they are all in 
        # RAM or some are on disk, and retrieve all from either ram or disk
        # first check the stack, then get from disk
        if inds[1]==[-3]: # -3 signifies first match to shotnumber, regardless of rep number
            from_archive=numpy.empty(shape=(0,2),dtype=numpy.uint32)
            for s,p in zip(inds[0],range(len(inds[0]))): 
                if s not in self.shotnumbers: 
                    from_archive=numpy.append(from_archive,[[s,p]],0)
                    continue
                res[p,0,...]=self.stack[numpy.where(self.shotnumbers==s)[0][0]][inds[2:]]
        else: # enters for shot/rep pair specified
            from_archive=numpy.empty(shape=(0,4),dtype=numpy.uint32)
            sr=itertools.product(inds[0],inds[1]) # all needed pairs
            pl=itertools.product(range(len(inds[0])),range(len(inds[1]))) # their placement in output array
            sr_ram=zip(self.shotnumbers,self.repnumbers) # all shot/rep pairs in ram
            for srh,plh in itertools.izip(sr,pl): 
                if srh not in sr_ram: # if not found, append to list to get from disk later
                    from_archive=numpy.append(from_archive,[[srh[0],srh[1],plh[0],plh[1]]],0)
                    continue
                res[plh[0],plh[1],...]=self.stack[sr_ram.index(srh)][inds[2:]] # insert result to output
        # now need to find those which are only on archive
        # start by mapping which to retrieve
        if from_archive.size!=0:  # enters if any elements not found on ram stack
            self.datastore_handle.table.flush()
            if inds[1]==[-3]: # enters on a first-rep selection
                asns=self.getshotnumbers(archived=True)
                asns=numpy.append([asns],[numpy.arange(asns.shape[0])],axis=0).transpose()
                from_archive=from_archive[numpy.argsort(from_archive[:,0]),:]
                asns=asns[numpy.argsort(asns[:,0]),:]
                ret_ind=asns[:,0].searchsorted(from_archive[:,0])
                # this could be done more effeciently by converting list to slices
                if from_archive.shape[0] > 1:
                    res = res.squeeze()
                from_table = self.datastore_handle.table[asns[ret_ind,1]]
                res[from_archive[:,1],...] = from_table[self.id][[slice(None,None,None)]+inds[2:]].squeeze()#If this fails, check effect of squeezing
            else:  # enters for shot/rep specified
                sr_disk=numpy.append([self.getshotnumbers(archived=True)],
                                      [self.getrepnumbers(archived=True)],
                                       0).transpose()
                # convert shot/rep pairs (each 32-bit ints) to single (64-bit) integers for easier matching 
                from_archive1=(from_archive[:,0:2].view(dtype=numpy.uint64)*numpy.array([1L,2L**32L],dtype=numpy.uint64)).sum(axis=1)  # need to search for these
                sr_disk1=(sr_disk.view(dtype=numpy.uint64)*numpy.array([1L,2L**32L],dtype=numpy.uint64)).sum(axis=1)
                # sort both arrays for faster search matching
                from_archive1=numpy.append([from_archive1],[numpy.arange(from_archive1.shape[0],dtype=numpy.uint32)],axis=0).transpose()
                sr_disk1=numpy.append([sr_disk1],[numpy.arange(sr_disk1.shape[0],dtype=numpy.uint32)],axis=0).transpose()
                from_archive1=from_archive1[numpy.argsort(from_archive1[:,0]),:]
                sr_disk1=sr_disk1[numpy.argsort(sr_disk1[:,0]),:]
                # match elements on disk
                ret_ind=sr_disk1[:,0].searchsorted(from_archive1[:,0])
                # next lines handle missing elements
#                self.DNE=numpy.where(ret_ind>=sr_disk1.shape[0])
#                ret_ind=(ret_ind<sr_disk1.shape[0])
                # copy into result array
                #pdb.set_trace()
                res[from_archive[from_archive1[:,1],2],
                    from_archive[from_archive1[:,1],3],...] = self.datastore_handle.table[sr_disk1[ret_ind,1].astype(numpy.int64)][self.id][[slice(None,None,None)]+inds[2:]].squeeze()
            # return the result array
            if not self.use_reps: return res.squeeze()
        return res

    def __process_indices__(self,dim,ind,n_dim):
        """
        handles indexing of a given dimension for the stack
        """
        if isinstance(ind,numbers.Number): ind=[ind]
        handler={types.SliceType: self.__h_slice,
                 types.ListType : self.__h_array,
                 types.StringTypes[0] : self.__h_string,
                 types.StringTypes[1] : self.__h_string
                 }[type(ind)]
        inds = handler(dim,ind,n_dim)
        return inds
    """
    The following routines __h_XXX(self,dim,ind,n_dim) are handlers
    for indexing elements specified with different types
    """
    def __h_slice(self,dim,ind,n_dim):
        # this slicing evaluation will work only in cases where the shotnumber
        # is contiguous 
        if dim in [0,1]:
            return [ii for ii in xrange(*ind.indices(max(self.getshotnumbers())))]
        return ind
    def __h_array(self,dim,ind,n_dim):
        return ind
    def __h_string(self,dim,ind,n_dim):
        # be case-insensitive
        ind=str(ind).lower()
        # behavior for shot and rep numbers 
        if dim==0: getn=self.getshotnumbers
        if dim==1 and self.use_reps: getn=self.getrepnumbers
        if dim in [0,1]:
            if ind=="live": return getn(live=True)
            if ind=="all" : return getn(live=False)
        if dim==1: 
            if ind=="first": return [-3]
        if ind=="all" : return slice(None, None, None)
        # check if string refers to a custom_indexing element (which
        # should be a dictionary of string:handler_function pairs, the handler
        # returning an array of indices), the string should be all lower-case
        # useful for roi storage or complex or repeated indexing tasks 
        try: 
            return self.custom_indexing_table[ind](dim,ind,n_dim)
        except (KeyError,AttributeError): pass 
        except: self.warning("custom indexing element called, but has some error") 
        # otherwise forward the string to the elements.  maybe they know
        # what to do with it
        return ind
        
    def __setitem__(self,indices):
        """
        item getter, returns elements to x[indices] call  
        """
        pdb.set_trace()
        return self.stack[indices]
        
    def permanent_id(self, shotnumber, repnumber=1):
        """
        returns a permanent id (resource locator) to retrieve data element with 
        """
        return "method for heap locator not yet written"
        
    def heave(self,heap_index=None):
        """
        this tosses an element from the RAM stack, and writes to disk if
        element is not already marked as archived
        """
        if heap_index==None:
            heap_index=self.stackorders.argmin()
        if not self.archived[heap_index]:
            self.archive(heap_index)

    def archive(self,heap_index):
        """
        stores an element to disk or permanent storage
        """
        self.datastore_handle.append(self.stack[heap_index,...],
                                    self.shotnumbers[heap_index],
                                    self.repnumbers[heap_index])
        return

    def warning(self,message):
        """
        raises a warning - if pyqt signaling is used, remember you can trigger
        on this
        """
        message="WARNING: stack "+self.id+" reports "+message
        if VERBOSE: print message

    def push(self,element,shotnumber=None,repnumber=None):
        """
        this will add an element to the top of the stack; if necessary an existing element
        will be heaved from the bottom of RAM stack to disk/file, either shot and rep numbers
        should be provided, or the heap should be linked to retrieval methods named
        self.get_current_shotnumber and self.get_current_repnumber 
        """
        # first use robust method to determine shot and rep numbers
        
        if shotnumber==None: 
            try: shotnumber=self.get_current_shotnumber()
            except AttributeError: 
                self.warning("no means given to record shotnumber") 
                shotnumber=-2 # shotnumber -2 signifies none provided
        self.use_repnumbers = False
        if repnumber==None and self.use_repnumbers:
            try: repnumber=self.get_current_repnumber()
            except AttributeError: 
                self.warning("no means given to record repnumber")
                repnumber=-2 # repnumber -2 signifies none provided

        if (shotnumber in self.getshotnumbers()) and (repnumber in self.getrepnumbers()):
            self.warning("duplicate shot or rep number")

        # begin update
        # first determine if any elements must be heaved (possibly to disk) to make room
        mustheave=False
        try:
            pushind=numpy.where(self.stackorders==-1)[0][0]
        except IndexError: 
            pushind=self.stackorders.argmin()
            mustheave=True
        if mustheave:
            self.heave(pushind)
        # next must update the stack element itself
        self.shotnumbers[pushind]=shotnumber
        self.repnumbers[pushind]=repnumber
        self.stack[pushind,...]=element  # this overwrites the least valuable elm in place
        self.archived[pushind]=False
        self.stackorders[pushind]=self.current_order
        self.current_order+=1L
        
        # check for duplicated data, warn if enabled
        if self._warn_duplicates:
            if len(self.stack) > 1 and not (pushind == 0 and self.last_pushed == 0) and (self.stack[pushind,...]==self.stack[self.last_pushed,...]).all():
                self.warning("duplicated data")
            
        self.last_pushed=pushind
        
    def getdata(self,shotnumbers=None,repnumbers=None,live=False):
        """
        this method will return data corresponding to a list of shotnumbers and
        repnumbers, or return all data in the file, or in RAM, according to the live flag
        """
        if live:
            return self.stack
        return self.stack # needs be replaced by scanning file
        
    def getshotnumbers(self,live=False,archived=False):
        """
        this method will return all shot numbers present in the file and RAM (default), 
        or all live (RAMish) shotnumbers, or archived as specified in the live and archived flags
        """
        if live and not archived: 
            return self.shotnumbers
        self.datastore_handle.table.flush()
        if archived and not live: return self.datastore_handle.table.col('shotnumber')
        return numpy.append(self.datastore_handle.table.col('shotnumber'),
                            self.shotnumbers[numpy.logical_not(self.archived).nonzero()])

    def getrepnumbers(self,live=False,archived=False):
        """
        this method will return all shot numbers present in the file (default), 
        or all live (RAMish) shotnumbers, or archived as specified in the live and archived flags
        """
        if live and not archived: 
            return self.repnumbers
        self.datastore_handle.table.flush()
        if archived and not live: return self.datastore_handle.table.col('repnumber')
        return numpy.append(self.datastore_handle.table.col('repnumber'),
                            self.repnumbers[numpy.logical_not(self.archived).nonzero()])

    def attach_datastore(self,datastore=None, options={}):
        """
        associates a datastore (portal to an h5 file) with this stack
        """
        if datastore == None:
            datastore = glab_datastore(options=options)
        self.datastore = datastore
        self.datastore_handle = datastore.get_handle(self.id,self.stack[0,...])
           
import unittest
class test_basic_functions(unittest.TestCase):

    def setUp(self):
        print 'class test_basic_functions, function setUp'
        self.e=numpy.random.rand(20,20,20) # generate 20 random matrices
        for i in range(20): # the first ten of the following pushes will be heaved to disk, the last ten will stay in ram stack
            self.e[i,0,0]=121+i  # set top-left element to same as shotnumber will be when pushed, starting shotnumber will be 121

        self.ds = glab_datastore()

    
    def test_getitem(self):
        """
        checks basic insertion and retrieval with heap and 20 20x20 float arrays, with half held in ram
        """
        print 'class test_basic_functions, function test_getitem'
        g=glab_liveheap(options={"element_structure":[20,20],"sizeof":10, "typecode":numpy.float}) # creates a stack of 20x20 float arrays, ten of which will be held in ram at any time
        g.attach_datastore() # attaches a datastore with a randomly generated name
        for i in range(self.e.shape[0]):
            g.push(self.e[i].squeeze(),121+i,0) # push it into the heap
        test1=g[[140,128,139,125,126]] # retrieves this list of shotnumbers, non-sequential and split ram/disk
        #print test1
        self.assertEqual(test1.shape,(5L,20L,20L)) # check dimensionality
        self.assertTrue((test1[:,0,0].squeeze()==[140.,128.,139.,125.,126.]).all()) # check correct shots recovered
        test2=g[[140,128,139,125,126],5:15,5:15] # retrieves this list of shotnumbers, sub-arrayed on retrieval
        self.assertEqual(test2.shape,(5L,10L,10L)) # check dimensionality
        self.assertTrue((test2[:,0,0]==self.e[numpy.array([140,128,139,125,126])-121,5,5]).all()) # check correct shots recovered
        #g.use_reps=True # now use repetition numbers
        #test3=g[[140,128,139,125,126],0,5:15,5:15] # retrieve these shotnumbers, rep#=0, and subarray a 10x10 element subset of all
        #self.assertTrue((test3[:,0,0]==self.e[numpy.array([140,128,139,125,126])-121,5,5]).all()) # check correct shots recovered
        
        
        self.assertTrue((g[122] == self.e[1]).all())#Retreving single value from RAM
        self.assertTrue((g[122+18] == self.e[1+18]).all())#Retreving single value from disk
        self.assertTrue((g[[122,122+18]] == [self.e[1],self.e[1+18]]).all())
           
        
    def test_get_handle(self):
        print 'class test_basic_functions, function test_get_handle'
        handle = self.ds.get_handle('ccdimage',self.e[0])
        handle2 = self.ds.get_handle('ccdimage',self.e[0])
        sn = numpy.random.random_integers(1000*1000*1000)
        rn = numpy.random.random_integers(1000*1000*1000)
        handle.append(self.e[1], sn, rn)
        handle.table.flush()
        self.assertTrue((self.e[1]==handle.table.read()[0][2]).all())
        self.assertTrue((self.e[1]==handle2.table.read()[0][2]).all())
    
        
    def test_get_different_handle(self):
        print 'class test_basic_functions, function test_get_different_handle'
        handle = self.ds.get_handle('ccdimage',self.e[0])
        print '1'
        test_data = numpy.random.randint(numpy.random.random_integers(1000*1000*1000), size=(40, 40))
        print '2'
        handle2 = self.ds.get_handle('ccdimage',test_data)
        print '3'
        sn = numpy.random.random_integers(1000*1000*1000)
        print '4'
        rn = numpy.random.random_integers(1000*1000*1000)
        print '5'
        pdb.set_trace()
        handle.append(self.e[1], sn, rn)
        print '6'
        pdb.set_trace()
        handle2.append(test_data, sn, rn)
        print '7'
        handle.table.flush()
        print '8'
        handle2.table.flush()
        print '9'
        self.assertTrue((self.e[1]==handle.table.read()[0][2]).all())
        print '10'
        self.assertTrue((test_data==handle2.table.read()[0][2]).all())
        print '11'





