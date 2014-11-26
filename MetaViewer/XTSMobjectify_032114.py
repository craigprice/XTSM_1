"""
This software is described in detail at https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Python_parser

What is next:
        fix problem with appending edges after last interval (line 550) 
        add an XTSM feature for maximum repeat length and implement parsing; also 0 byteperrepeat for repasints?
        Error: objectify doesn't define a class if it's not in the <XTSM> to begin with
        REMOVE ALL GROUP EDGES AND GROUP INTERVALS ON CLOCKING CHANNELS HERE line 473
        
small bugs:
    *ControlArray (and others?) created without __parent__   
    *When create class with a name of 'Value', the name might be conflict with the gnosis reserved keywords. It raises an error of "Object Value missing attribution _seq".
     
    
"""
import gnosis.xml.objectify # standard package used for conversion of xml structure to Pythonic objects, also core starting point for this set of routines
import sys, StringIO, urllib, uuid # standard packages for many things
import inspect, pdb, traceback, code  # used for profiling and debugging this code
import numpy, scipy, math, bisect # math routines 
numpy.set_printoptions(suppress=True,precision=7, threshold='nan')  # sets default printing options for numpy
from bitarray import bitarray # used to manipulate individual bits in arrays without wasting memory by representing bits as bytes
from lxml import html

XO_IGNORE=['PCDATA']  # ignored elements on XML_write operations

class XTSM_core(object):
    """
    Default Class for all elements appearing in an XTSM tree; contains generic methods
    for traversing the XTSM tree-structure, inserting and editing nodes and attributes,
    writing data out to XML-style strings, and performing parsing of node contents in
    python-syntax as expressions
    """
    scope={}  # dictionary of names:values for parsed variables in element's scope  
    scoped=False  # records whether scope has been determined
    scopePeers={} # contains a list of {TargetType,TargetField,SourceField} which are scope-peers, to be found by matching TargetType objects with TargetField's value equal to SourceField's value

    def __init__(self,value=None):
        self._seq=[]
        if value==None:
            self.PCDATA=''
        else:
            self.PCDATA=value
            self._seq={value}
        self.__parent__=None

    def insert(self,node,pos=0):
        "inserts a node node at the position pos into XTSM_core object"
        node.__parent__=self        
        if pos < 0: pos=0
        if pos > self._seq.__len__(): pos=self._seq.__len__()
        nodeType=type(node).__name__.split('_XO_')[-1]
        if hasattr(self, nodeType):  # begin insertion process
            if getattr(self,nodeType).__len__() > 1:
                getattr(self,nodeType).append(node)
                getattr(self,'_seq').insert(pos,node)
            else:
                setattr(self,nodeType,[getattr(self,nodeType),node])
                getattr(self,'_seq').insert(pos,node)
        else:
            setattr(self, nodeType, node)
            getattr(self,'_seq').insert(pos,node)
        return node
        
    def find_closest(self,array1,array2): #LRJ 3-11-2014
        '''
        Returns the indicies of array1 that are closest to the values of array2
        Array1 must be an ordered array
        '''
        idx=array1.searchsorted(array2)
        idx=numpy.clip(idx,1,len(array1)-1)
        left=array1[idx-1]
        right=array1[idx]
        idx-=array2-left<right-array2
        return idx
        
    def getDictMaxValue(self,dictionary): #LRJ 10-23-2013
        """
        Finds and returns the largrest numeric value in a dictionary
        """        
        self.valut=list(dictionary.values())
        return max(self.valut)
    
    
    def addAttribute(self,name,value):
        "adds an (XML) attribute to the node with assigned name and value"
        setattr(self,name,value)
        return getattr(self,name)
        
    def getOwnerXTSM(self):
        """
        Returns top-level XTSM element
        """
        if self.__parent__:
            return self.__parent__.getOwnerXTSM()
        else:
            return self
            
    def getFirstParentByType(self,tagtype):
        """
        Searches up the XTSM tree for the first ancestor of the type tagtype,
        returning the match, or None if it reaches toplevel without a match
        """
        if self.get_tag()==tagtype:
            return self
        else:
            if self.__parent__:
                return self.__parent__.getFirstParentByType(tagtype)
            else: return None
        
    def getChildNodes(self):
        """
        Returns all XTSM children of the node as a list
        """
        if (type(self._seq).__name__=='NoneType'): return []
        return [a for a in self._seq if type(a)!=type(u'')]
        
    def getDescendentsByType(self,targetType):
        """
        Returns a list of all descendents of given type
        """
        res=[]
        for child in self.getChildNodes():
            if hasattr(child,'getDescendentsByType'):
                res.extend(child.getDescendentsByType(targetType)) 
        if hasattr(self,targetType): res.extend(getattr(self,targetType))
        return res
    
    def getItemByFieldValue(self,itemType,itemField,itemFieldValue,multiple=False):
        """
        Returns the first XTSM subelement of itemType type with field itemField equal to itemFieldValue
        Note: will search all descendent subelements!
        """
        hits=set()
        if hasattr(self,itemType):
            for item in getattr(self,itemType): # advance to matching element
                if getattr(item,itemField).PCDATA==itemFieldValue:
                    if multiple: hits=hits.union({item})
                    else: return item
        for subelm in self.getChildNodes():
            if not hasattr(subelm,'getItemByFieldValue'): continue
            item=subelm.getItemByFieldValue(itemType,itemField,itemFieldValue,multiple)
            if item!=None and item!={}:
                if multiple: hits=hits.union(item) 
                else: return item
        if multiple: return hits
        else: return None 

    def getItemByFieldValueSet(self,itemType,FieldValueSet):
        """
        Returns all subelements of type which have all given fields with specified values
        FieldValueSet should be a dictionary of field:value pairs
        """
        for step,pair in enumerate(FieldValueSet.items()):
            if step==0: hits=self.getItemByFieldValue(itemType,pair[0],pair[1],True)
            else: hits=hits.intersection(self.getItemByFieldValue(itemType,pair[0],pair[1],True))
            if len(hits)==0: return hits
        return hits.pop()

    def getItemByAttributeValue(self,attribute,Value,multiple=False):
        """
        Returns the first subelement with (non-XTSM) attribute of specified value
        if multiple is true returns a list of all such elements
        """
        hits=set()
        if hasattr(self,attribute):
            if getattr(self,attribute)==Value: 
                if multiple: hits=hits.union({self})
                else: return self
        for subelm in self.getChildNodes():
            a=subelm.getItemByAttributeValue(attribute,Value,multiple) 
            if a: 
                if multiple: hits=hits.union({a})
                else: return a
        if multiple: return hits
        else: return None
                
    def parse(self,additional_scope=None):
        """
        parses the content of the node if the node has only 
        textual content. 
        ->>if it has parsable subnodes, it will NOT parse them -(NEED TO TAG PARSABLE NODES)
        this is done within the node's scope
        side-effect: if scope not already built, will build
        entirely untested
        """
        if (not hasattr(self,'PCDATA')): return None  # catch unparsable
        if (self.PCDATA==None): return None
        if not isinstance(self.PCDATA,basestring): return None
        suc=False        
        try:        # try to directly convert to floating point
            self._parseValue=float(self.PCDATA)
            suc=True
        except ValueError:    # if necessary, evaluate as expression
            if (not self.scoped): self.buildScope()  # build variable scope
            if additional_scope!=None:       
                tscope=dict(self.scope.items()+additional_scope.items())
            else: tscope=self.scope
            try: 
                self._parseValue=eval(html.fromstring(self.PCDATA.replace('#','&')).text,globals(),tscope)  # evaluate expression
                suc=True
            except NameError as NE:
                self.addAttribute('parse_error',NE.message)
        if suc:
            if hasattr(self._parseValue,'__len__'):
                if isinstance(self._parseValue,basestring) or len(self._parseValue)<2:
                    self.addAttribute('current_value',str(self._parseValue))
            else: self.addAttribute('current_value',str(self._parseValue))  # tag the XTSM
            return self._parseValue
        else: return None
    
    def buildScope(self):
        """
        constructs the parameter scope of this node as dictionary of variable name, value
        first collects ancestors' scopes starting from eldest
        then collects scopes of peers defined in scopePeers
        then collects parameter children 
        those later collected will shadow/overwrite coincident names
        """
        if self.__parent__: # if there is a parent, get its scope first (will execute recursively up tree)
            self.__parent__.buildScope()
            self.scope.update(self.__parent__.scope) # append parent's scope (children with coincident parameters will overwrite/shadow)
        if (not self.scoped):
            if hasattr(self,'scopePeers'):
                root=self.getOwnerXTSM()
                for peerRelation in self.scopePeers:
                    peerElm=root.getItemByFieldValue(peerRelation[0],peerRelation[1],getattr(self,peerRelation[2]).PCDATA) # loop through scope peers
                    if (peerElm != None):
                        if (not hasattr(peerElm,'scoped')): peerElm.buildScope() # build their scopes if necessary
                        self.scope.update(peerElm.scope) # append their scopes
            if hasattr(self,'Parameter'):
                for parameter in self.Parameter: # collect/parse parameter children
                    if (not hasattr(parameter,'_parseValue')): parameter.Value[0].parse()
                    self.scope.update({parameter.Name.PCDATA: parameter.Value[0]._parseValue})
        self.scoped=True # mark this object as scoped
        return None

    def get_tag(self):
        """
        returns the tagname of the node
        """
        return type(self).__name__.split('_XO_')[-1]
        
    def set_value(self, value):
        """
        sets the textual value of a node
        """
        pos=0
        if (self.PCDATA in self._seq):
            pos=self._seq.index(unicode(str(value)))
            self._seq.remove(unicode(str(value)))
        self._seq.insert(pos,unicode(str(value)))
        self.PCDATA=unicode(str(value))
        return self
        
    def generate_guid(self, depth=None):
        """
        generate a unique id number for this element and all descendents to
        supplied depth; if no depth is given, for all descendents.
        if element already has guid, does not generate a new one
        """
        if (not hasattr(self,'guid')):
            self.addAttribute('guid',str(uuid.uuid1()))
        if (depth == None):
            for child in self.getChildNodes(): child.generate_guid(None)
        else:
            if (depth>0):
                for child in self.getChildNodes(): child.generate_guid(depth-1)
        return
    
    def generate_guid_lookup(self,target=True):
        """
        creates a lookup list of guid's for all descendent elements that possess one
        adds the result as an element 'guid_lookup' if target input is default value True
        """
        if hasattr(self,'guid'): 
            guidlist=[self.guid]
        else:
            guidlist=[]
        for child in self.getChildNodes():
            guidlist.extend(child.generate_guid_lookup(False))
        if target: self.guid_lookup=guidlist
        return guidlist
    
    def generate_fasttag(self,running_index,topelem=None):
        """
        creates a lookup index and reference table
        """
        self._fasttag=running_index
        if topelem==None: 
             topelem=self
             topelem._fasttag_dict={running_index:self}
        else: topelem._fasttag_dict.update({running_index:self}) 
        running_index+=1
        for child in self.getChildNodes(): running_index=child.generate_fasttag(running_index,topelem)
        return running_index
    
    def remove_all(self, name):
        delattr(self,name)
        
        pass

    def write_xml(self, out=None, tablevel=0, whitespace='True'):
        """
        Serialize an _XO_ object back into XML to stream out; if no argument 'out' supplied, returns string
        If tablevel is supplied, xml will be indented by level.  If whitespace is set to true, original whitespace
        will be preserved.
        """
        global XO_IGNORE
        mode=False
        newline=False
        firstsub=True
        # if no filestream provided, create a stream into a string (may not be efficient)
        if (not out):
            mode=True
            out=StringIO.StringIO()
        # write tag opening
        out.write(tablevel*"  "+"<%s" % self.get_tag())
        # attribute output; ignore any listed in global XO_IGNORE
        for attr in self.__dict__:
            if (isinstance(self.__dict__[attr], basestring)):
                if (attr in XO_IGNORE): continue 
                out.write(' ' + attr + '="' + self.__dict__[attr] + '"')
        out.write('>')
        # write nodes in original order using _XO_ class _seq list
        if self._seq:            
            for node in self._seq:
                if isinstance(node, basestring):
                    if (not whitespace):
                        if node.isspace():
                            pass
                        else: 
                            out.write(node)                            
                    else: out.write(node)
                else:
                    if firstsub:
                        out.write("\n")
                        firstsub=False
                    node.write_xml(out,0 if (tablevel==0) else (tablevel+1),whitespace)
                    newline=True
        # close XML tag
        if newline:
            out.write(tablevel*"  ")
        out.write("</%s>\n" % self.get_tag())
        # if mode is stringy, return string        
        if mode:
            nout=out.getvalue()
            out.close()
            return nout
        return None
        
    def countDescendents(self,tagname):
        """
        Counts number of descendent nodes of a particular type
        """
        cnt=0
        for child in self.getChildNodes():
            cnt+=child.countDescendents(tagname)
        if hasattr(self,tagname):
            return cnt+getattr(self,tagname).__len__()
        else: return cnt
        
    def get_childNodeValue_orDefault(self,tagType,default):
        """
        gets the value of the first child Node of a given tagtype, 
        or returns a default value if the node does not exist
        or if it is empty
        """
        if not hasattr(self,tagType): return default
        val=getattr(self,tagType).PCDATA     
        if val != u'': return val
        else: return default
        
        
class XTSM_Element(gnosis.xml.objectify._XO_,XTSM_core):
    pass

class ClockPeriod(gnosis.xml.objectify._XO_,XTSM_core):
    pass

class body(gnosis.xml.objectify._XO_,XTSM_core):
    def parseActiveSequence(self):
        """
        finds/parses SequenceSelector node, identifies active Sequence, initiates subnodeParsing,
        constructs control arrays, returns the ParserOutput node, which is also attached as a 
        subnode to the active Sequence node        
        """
        try:
            if self.SequenceSelector:
                if not hasattr(self.SequenceSelector[0],'current_value'): 
                    self.SequenceSelector[0].parse() # parse SS if not done already
                    
                try:
                    aseq=self.getItemByFieldValue('Sequence','Name',self.SequenceSelector[0].current_value) # identify active sequence by name and begin collection
                    aseq.parse()
                except Exception as Error:
                    print Error
                    print traceback.format_exc()
            elif self.__parent__.SequenceSelector:
                if not hasattr(self.__parent__.SequenceSelector[0],'current_value'): 
                    self.__parent__.SequenceSelector[0].parse() # parse SS if not done already
                try:
                    aseq=self.getItemByFieldValue('Sequence','Name',self.__parent__.SequenceSelector[0].current_value) # identify active sequence by name and begin collection
                    aseq.parse()
                except Exception as Error:
                    print Error
        except Exception as Error:
            print Error            
        return aseq.ParserOutput[0]

class TimingProffer():
    """
    A helper class defined to aid XTSM parsing; holds data about request for timing events
    from edges, intervals... Provides methods for compromise timing when requests
    are conflictory or require arbitration of timing resolution, etc...
    """
    data={}  # a dictionary to be filled with arrays for each type of timing request: edge,interval, etc...
    valid_entries={'Edge':0,'Interval':0} # will hold the number of elements in the array which are currently valid data
    data_per_elem={'Edge':5,'Interval':7} # the number of elements needed to understand a request: time, value, timing group, channel...
    data_types={'Edge':numpy.float32,'Interval':numpy.float32}  # the data_type to store

    def __init__(self,generator):
        """
        Creates the timingProffer from a root element (such as a sequence)
        """
        # the following loops through all elements defined above as generating
        # proffers, creates a blank array to hold proffer data, stored in data dictionary. Take edges as example,
        # if the sequence has n edges and each edges have 5 parameters, then the array dimension would be n by 5
        for gentype in self.valid_entries.keys():
            self.data.update({gentype:numpy.empty([generator.countDescendents(gentype),self.data_per_elem[gentype]],self.data_types[gentype])})
    
    def insert(self,typename,elem):
        '''
        
        '''
        try:
            self.data[typename][self.valid_entries[typename]]=elem
            self.valid_entries[typename]=self.valid_entries[typename]+1
        except IndexError:  # Reset index to 0 if index is out of range.
            self.valid_entries[typename] = 0
            self.data[typename][self.valid_entries[typename]]=elem
            self.valid_entries[typename]=self.valid_entries[typename]+1

class Emulation_Matrix():
    """
    A helper class defined to store result of hardware emulation for a sequence
    should follow constructs at line 674 of IDL version
    NOT STARTED
    """
    pass

class ParserOutput(gnosis.xml.objectify._XO_,XTSM_core):
    """
    An XTSM class to store the control array structure generated by the parser
    """
    def package_timingstrings(self):
        """
        packaging of all group timingstrings into a single timingstring with header
        THIS IS NOT FINISHED
        """
        try: 
            headerLength=80
            bodyLength=sum([(cd.ControlArray.timingstring).shape[0] for cd in self.ControlData])
            num_tg=len(self.ControlData)
            ts=numpy.empty(bodyLength+num_tg*headerLength+1,dtype=numpy.uint8)
            ts[0]=num_tg            
            hptr=1
            ptr=headerLength*num_tg + 1
            for cd in self.ControlData:
                ts[hptr:hptr+headerLength] = cd.ControlArray.generate_package_header()
                hptr+=headerLength
                ts[ptr:ptr+cd.ControlArray.timingstring.shape[0]] = cd.ControlArray.timingstring
                ptr+=cd.ControlArray.timingstring.shape[0]
            # Add in length of entire string to begininning.
            try:
                totalLength = ts.shape
                tl=numpy.asarray(totalLength, dtype=numpy.uint64).view('u1')
                ts=numpy.concatenate((tl, ts))
            except OverflowError: return ""  # Overflow error means length of ts is greater than 8 byte integer.
        except AttributeError: return ""
        return ts

class GroupNumber(gnosis.xml.objectify._XO_,XTSM_core):
    pass

class ControlData(gnosis.xml.objectify._XO_,XTSM_core):
    """
    An XTSM class to store the control arrays generated by the parser
    """
class ControlArray(gnosis.xml.objectify._XO_,XTSM_core):
    """
    An XTSM class: control arrays generated by the parser
    """
    def generate_package_header(self):
        """
        creates the header for this timingstring when all groups' timingstrings are
        packaged together
        """
        headerLength=80
        tsh=numpy.zeros(headerLength,dtype=numpy.uint8) # declare memory for header
        tsh[0:8]=numpy.array([self.timingstring.shape[0]],dtype=numpy.uint64).view(numpy.uint8) # timingstring length in bytes
        tsh[8:16]=numpy.array([self.tGroup],dtype=numpy.uint64).view(numpy.uint8) # timing group number
        tsh[16]={'DigitalOutput':0,'AnalogOutput':1,'DigitalInput':2,'AnalogInput':3,'DelayTrain':4}[self.get_tgType()] # type of hardware interface
#        tsh[17]=  GOING TO IGNORE THESE AS TOO SPECIFIC FOR PARSER TO GENERATE
#        tsh[18]=
        tsh[19:23]=numpy.array([1000./self.clockgenresolution],dtype=numpy.uint32).view(numpy.uint8)
        tsh[23]=hasattr(self,'swTrigger') # whether this group software-triggers acquisition (taken directly from XTSM)
        tsh[24]=self.isSparse # whether the sparse/dense conversion should be run on this data by the acquisition hardware
        tsh[25]=1  #  HEADER VERSION
#        tsh[26:32]= Reserved for future use
        tsh[32:56]=numpy.fromstring(self.tGroupNode.Name[0].PCDATA[0:24].ljust(24,u" "),dtype=numpy.uint8)  # tGroup Name
        tsh[56:80]=numpy.fromstring(self.tGroupNode.ClockedBy[0].PCDATA[0:24].ljust(24,u" "),dtype=numpy.uint8)  # Clock Channel Name
        return tsh        
    '''
    def findNearestValue(self,array,array2):
        
        Returns an edge array with coerced times from denseT that are nearest to an edge's requested time
        This algorithm could be made more efficient by sorting edge_array and matching values starting at the last found value

        idx=array.searchsorted(array2)
        idx=numpy.clip(idx,1,len(array)-1)
        left = array[idx-1]
        right = array[idx]
        idx -= array - left < right - array  
        edge_array=array[idx]                      
            # edge_array[elem]=dense_time_array[abs(edge_array[elem]-dense_time_array).argmin()] #many computations to rewrite group edge array
        return edge_array
        '''

    def get_tgType(self):
        """
        Returns the timing group's type: Analog/Digital,Input/Output,DelayTrain as string
        """
        try: 
            if self.dTrain: return 'DelayTrain'
        except AttributeError: pass
        if self.ResolutionBits>1: rval='Analog'
        else: rval='Digital'
        rval+='Output'
        return rval
        
    def get_biographics(self):
        """
        get biographical data about the timing group: number of channels, its clock period, whether it is a delaytrain
        """
                
        self.tGroupNode=self.channelMap.getItemByFieldValue('TimingGroupData','GroupNumber',str(self.tGroup))
        self.clockgenresolution=self.channelMap.tGroupClockResolutions[self.tGroup]
        self.numchan=int(self.tGroupNode.ChannelCount.PCDATA)
        self.range=float(self.tGroupNode.Range.PCDATA)     
        self.ResolutionBits=int(self.tGroupNode.ResolutionBits.PCDATA)
        # math.ceil returns the smallest integer not less than the argument.         
        self.bytespervalue=int(math.ceil(self.ResolutionBits/8.))
        
        # The following lines introduces the calibrition for the channel value.
        if not self.tGroupNode.DACCalibration.PCDATA==None:
            self.DACCalibration=float(self.tGroupNode.DACCalibration.PCDATA) #LRJ 11-8-2013
        else:
            self.DACCalibration= (pow(2.,self.ResolutionBits-1)-1)/(self.range/2.)
            
        
        if hasattr(self.tGroupNode,'SoftwareTrigger'): self.swTrigger=True 
        if hasattr(self.tGroupNode,'DelayTrain'): self.dTrain=True 
        else: self.dTrain=False
        # if not self-clocked, get data about clocker
        if (self.tGroupNode.ClockedBy.PCDATA != u'self'):
            self.clocksourceNode=self.channelMap.getChannel(self.tGroupNode.ClockedBy.PCDATA)
            self.clocksourceTGroup=self.channelMap.getItemByFieldValue('TimingGroupData'
                                                                  ,'GroupNumber',
                                                                  self.clocksourceNode.TimingGroup.PCDATA)
            self.parentgenresolution=self.channelMap.tGroupClockResolutions[int(self.clocksourceTGroup.GroupNumber.PCDATA)]
            self.bytesperrepeat=4
            if self.ResolutionBits==u'1': self.ResolutionBits=0
        else: 
            self.parentgenresolution=self.clockgenresolution
            self.bytesperrepeat=4
        # Find the end time for the sequence
        if hasattr(self.sequence,'endtime'): self.seqendtime=self.sequence.endtime
        else: self.seqendtime=self.sequence.get_endtime()
        # if delay train group, use ResolutionBits for time-resolution
        try: 
            if self.dTrain: 
                self.bytespervalue=0
                self.bytesperrepeat=int(math.ceil(self.ResolutionBits/8.))
        except AttributeError: pass

    def get_edgeSources(self):
        
        """
        gets all sources of timing edges (Edges, Intervals) for this group from the timing Proffer object
        """
       
        # Find the edge that belongs to this timinggroup        
        if len(self.sequence.TimingProffer.data['Edge'])>0:
            self.groupEdges=(self.sequence.TimingProffer.data['Edge'])[(((self.sequence.TimingProffer.data['Edge'])[:,0]==int(self.tGroup)).nonzero())[0],]
        else: self.groupEdges=self.sequence.TimingProffer.data['Edge']
        # Find the interval that belongs to this timinggroup       
        if len(self.sequence.TimingProffer.data['Interval'])>0:
            self.groupIntervals=(self.sequence.TimingProffer.data['Interval'])[(((self.sequence.TimingProffer.data['Interval'])[:,0]==int(self.tGroup)).nonzero())[0],]
        else: self.groupIntervals=self.sequence.TimingProffer.data['Interval']
        # transpose to match IDL syntax
        self.groupEdges=self.groupEdges.transpose().astype(numpy.float64)
        self.groupIntervals=self.groupIntervals.transpose().astype(numpy.float64)
        # now check if any channels in this timingGroup are claimed as clocks by other timingGroups
        self.cStrings={}  # dictionary of clock times for each channel that clocks another timingGroup
        for channel in range(self.numchan):
            clocker=self.channelMap.isClock(self.tGroup,channel)
            if clocker:
                clockString = []
                for elem in self.sequence.ParserOutput.clockStrings[clocker]:
                    if elem % 10 == 9:  # Eliminate rounding errors at the source. Ineligant solution, only works for clock periods smaller than 0.001.
                        elem += 1
                    clockString.append(elem)
                clockString = numpy.array(clockString, dtype = 'uint64')
                self.cStrings.update({channel:(clockString*self.clockgenresolution)})
                # REMOVE ALL GROUP EDGES AND GROUP INTERVALS ON CLOCKING CHANNELS HERE

    def coerce_explicitEdgeSources(self):
        """
        coerce explicit timing edges to a multiple of the parent clock's timebase
        (using the parent's resolution allows us to subresolution step.)
        """
        #self.groupEdges[2,:]=((self.groupEdges[2,:]/self.parentgenresolution).round())*self.parentgenresolution #LRJ 10-23-2013 JZ 12/18
        #self.groupIntervals[2,:]=((self.groupIntervals[2,:]/self.parentgenresolution).round())*self.parentgenresolution #LRJ 10-23-2013  JZ 12/18
        #self.groupIntervals[3,:]=((self.groupIntervals[3,:]/self.parentgenresolution).round())*self.parentgenresolution #LRJ 10-23-2013  JZ 12/18
        self.lasttimecoerced=float(math.ceil(self.seqendtime/self.clockgenresolution))*self.clockgenresolution    

    def construct_denseT(self):
        """
        constructs a list of all times an update is necessary on this timing group:
        this could arise from an explicitly defined edge, an update in an interval,
        or from a clocking pulse needed by another channel 
        """
        
        # first create a sorted list of all times at beginning or end of interval, at an edge, or beginning or start of sequence
        self.alltimes=numpy.unique(numpy.append(self.groupIntervals[2:4,],self.groupEdges[2,]))
                
        self.alltimes=numpy.unique(numpy.append(self.alltimes,[self.channelMap.hardwaretime,self.lasttimecoerced]))  #LRJ 10-23-2013 replaced 0 with hardware time. 
                
        # create a list denseT of all update times necessary in the experiment 
        # self.denseT=numpy.array([0]) #LRJ replaced 0 with hardwaretime. 
        self.denseT=numpy.array([self.channelMap.hardwaretime],dtype=numpy.float32)       
        # loop through all windows between members of alltimes
        for starttime,endtime in zip(self.alltimes[0:-1],self.alltimes[1:]):
            
            # identify all intervals in this group active in this window
            if self.groupIntervals.size!=0:
                pre=(self.groupIntervals[2,]<=starttime).nonzero()
                post=(self.groupIntervals[3,]>starttime).nonzero()
                if ((len(pre)>0) and (len(post)>0)):
                    aInts=numpy.intersect1d(numpy.array(pre),numpy.array(post))
                    if aInts.size>0:
                        # find compromise timing resolution (minimum requested, coerced to parent clock multiple)
                        Tres=math.ceil(round(min(self.groupIntervals[5,aInts])/self.clockgenresolution,3))*self.clockgenresolution
                        # define the times in this window using universal time
                        T=numpy.linspace(starttime,endtime,(endtime-starttime)/Tres+1)
                        self.denseT=numpy.append(self.denseT,T)
                    else: self.denseT=numpy.append(self.denseT,starttime)   
                else: self.denseT=numpy.append(self.denseT,starttime)
            else: self.denseT=numpy.append(self.denseT,starttime)
        
        # This line add the endtime to the end of the denseT.       
        self.denseT=numpy.append(self.denseT,self.lasttimecoerced)

        self.denseT=numpy.unique(self.denseT)
        # now incorporate all clockstrings for clock channels:
        # merge all clock update times with denseT from edges and intervals (likely costly operation)
        allclcks=numpy.array([])
        if self.dTrain == True:            # Data in delay train cEdges is stored differently.
            for clockChannel in self.cStrings:
                try: 
                    allclcks=numpy.concatenate([allclcks,self.cEdges[clockChannel][2,:]])
                except AttributeError: 
                    self.cEdges={}
                    self.cEdges.update({clockChannel:self.generate_clockEdges(self.cStrings[clockChannel],None,clockChannel)})
                    allclcks=numpy.concatenate([allclcks,self.cEdges[clockChannel][2,:]])
                except KeyError: 
                    self.cEdges.update({clockChannel:self.generate_clockEdges(self.cStrings[clockChannel],None,clockChannel)})
                    allclcks=numpy.concatenate([allclcks,self.cEdges[clockChannel][2,:]])
        else: # If not a delay train...
                        
            for clockChannel in self.cStrings:
                try: allclcks=numpy.concatenate([allclcks,self.cEdges[clockChannel][0,:]])
                except AttributeError: 
                    self.cEdges={}
                    self.cEdges.update({clockChannel:self.generate_clockEdges(self.cStrings[clockChannel],None,clockChannel)})
                    allclcks=numpy.concatenate([allclcks,self.cEdges[clockChannel][0,:]])
                except KeyError: 
                    self.cEdges.update({clockChannel:self.generate_clockEdges(self.cStrings[clockChannel],None,clockChannel)})
                    allclcks=numpy.concatenate([allclcks,self.cEdges[clockChannel][0,:]])
        # choose the unique update times and sort them (sorting is a useful side-effect of the unique function)
             
        try: 
            self.denseT=numpy.unique(numpy.concatenate([allclcks, self.denseT]))          
            #Build an array indicating the clocking chain for the timing group. 
            #Format is an array of timing group numbers. For example tg 3 would give [2,6,0] which indicates that tg3 is clocked by tg 2 is clocked by tg 6 is clocked by tg 0
            self.channelMap.getClocks()
            self.clkchain=numpy.array([self.channelMap.Clocks[self.tGroup][0]])
            for elem in range(self.getDictMaxValue(self.channelMap.tGroupClockLevels)-self.channelMap.tGroupClockLevels[self.tGroup]):
                try :
                    self.clkchain=numpy.append(self.clkchain,self.channelMap.Clocks[self.clkchain[elem]][0])
                except KeyError :pass
                except IndexError: pass
            
            #Coerce all times in denseT to the timing group's own time resolution, its clocker's time resolution, its clocker's clocker's time resolution and so on through the clocking chain
            self.denseT=(self.denseT/self.channelMap.tGroupClockResolutions[self.tGroup]).round()*self.channelMap.tGroupClockResolutions[self.tGroup]           
            for elem in range(len(self.clkchain)):
                self.denseT=((self.denseT/self.channelMap.tGroupClockResolutions[self.clkchain[elem]]).round())*self.channelMap.tGroupClockResolutions[self.clkchain[elem]]
               
            self.denseT=numpy.unique(self.denseT)
            
        except: pass

    def sort_edgeSources(self):
        """
        sort edges and intervals by group index (channel), then by (start)time
        """
        if self.groupEdges.size > 0:
            self.groupEdges=self.groupEdges[:,numpy.lexsort((self.groupEdges[2,:],self.groupEdges[1,:]))] 
        if self.groupIntervals.size > 0:
            self.groupIntervals=self.groupIntervals[:,numpy.lexsort((self.groupIntervals[2,:],self.groupIntervals[1,:]))]

    def calculate_numalledges(self):
        """
        Calculate how many edges this timinggroup will have
        """
        self.numalledges=0
        # find out how many edges this timinggroup will have
        for intervalInd in self.groupIntervals[6,]:
            # get the interval, find how many samples it will generate
            interval=self.sequence._fasttag_dict[intervalInd]
            self.numalledges+=interval.expected_samples(self.denseT)
        # add the number of group edges
        self.numalledges+=self.groupEdges.shape[1]
        # add the number of clocking edges 
        self.numalledges+=sum([len(a) for a in self.cStrings.values()])

    def construct(self,sequence,channelMap,tGroup):
        """
        constructs the timing control array for a timingGroup in given sequence
        sequence should already have collected TimingProffers
        """
        # bind arguments to object
        self.sequence=sequence
        self.channelMap=channelMap
        self.tGroup=tGroup
        del sequence,channelMap,tGroup
        
        
        # get data about the channel, sequence and its clocking channel
        self.get_biographics()
        # locate the edges and intervals for this timing group, generated explicitly or by clocking requests                
        self.get_edgeSources()
        
        # coerce explicit timing edges to a multiple of the parent clock's timebase
        self.coerce_explicitEdgeSources() #LRJ 3-7-2014, edge coercion will be done inside of construct_denseT so that clockers and outputs agree on times.
        # create a list of all times an update is needed for this timing group                
        self.construct_denseT()
        # clockstring management: save the current timinggroup's clocking string to the ParserOutput node,
        # also find and eventually insert clocking strings for other timinggroups which should occur on a channel in the current timinggroup
        if not hasattr(self.sequence.ParserOutput,"clockStrings"): self.sequence.ParserOutput.clockStrings={}
        self.sequence.ParserOutput.clockStrings.update({self.tGroup:(self.denseT/self.parentgenresolution).astype('uint64')})
        # sort edges and intervals by group index (channel), then by (start)time
        self.sort_edgeSources()
        # create a channelData object for every channel; accumulates all edges for each channel
        self.channels={channum:channelData(self,channum) for channum in range(self.numchan)} 
        # HERE WE NEED TO CONVERT FLAGGED DIGITAL BOARDS INTO SINGLE CHANNEL INTEGER REPRESENTATIONS
        if self.ResolutionBits==1 and hasattr(self.tGroupNode,'ParserInstructions'):
            if self.tGroupNode.ParserInstructions[0].get_childNodeValue_orDefault('RepresentAsInteger','yes').lower() == 'yes':
                self.repasint=True                
                self.RepresentAsInteger()
        # Break these into channel control strings - first determine necessary size and define empty array
        self.TimingStringConstruct()

        return self
        
    def RepresentAsInteger(self):
        """
        Replaces an N-channel digital group intedge with a single-channel log_2(N)-bit intedge list
        This algorithm assumes the group is digital, channel intedges have no duplications, 
        and that the final edges all coincide - THIS LAST PART IS PROBLEMATIC
        """
                
        Nchan = len(self.channels)  # number of channels
        Nbitout = math.ceil(Nchan/8.)*8  # number of bits in integer to use
        try:
            dtype = {0:numpy.uint8,8:numpy.uint8,16:numpy.uint16,32:numpy.uint32,64:numpy.uint64}[Nbitout] # data type for output
        except KeyError:
            pass
        # get all update times
        channeltimes = numpy.concatenate([ch.intedges[0,:].astype(numpy.float) for ch in self.channels.values()])
        # get number of updates for each channel 
        chanlengths = [ch.intedges.shape[1] for ch in self.channels.values()]
        # get whether each channel is a clock channel
        channelclocks = [ch.isclock for ch in self.channels.values()]
        # create a set of ptrs to the update times for each channel
        ptrs = numpy.array([sum(chanlengths[0:j]) for j in range(0,len(chanlengths))])
        # find the final resting places of the pointers
        fptrs = [ptr for ptr in ptrs[1:]]
        # add in end pointer
        fptrs.append(channeltimes.shape[0])
        fptrs = numpy.array(fptrs)
        # create a bit-array to represent all channel outputs
        bits = bitarray([(not bool(ch.intedges[3,0])) for ch in self.channels.values()])
        # create arrays of output times and values for a single channel
        numtimes = len(numpy.unique(channeltimes))
        outvals = numpy.empty(numtimes,dtype=dtype)
        outtimes = numpy.empty(numtimes,dtype=numpy.uint64)
        outptr = 0  # a pointer to the first currently unwritten output element
        
        ### THE FOLLOWING LINES SHOULD NOT BE HERE AS FAR AS I CAN TELL - NDG THEY SHOULD BE REMOVED, and then RETESTED.        
        # fix channels with no edges/intervals to end at the correct time
        index = 0
        final_update = max(channeltimes)
        for i in range(len(channelclocks)):
            index += chanlengths[i] 
            if not channelclocks[i]:
                channeltimes[index - 1] = final_update
        ### NDG 3-11-14                
                
        if hasattr(self.tGroupNode, 'ParserInstructions') and hasattr(self.tGroupNode.ParserInstructions, 'Pulser'):
            if str.upper(str(self.tGroupNode.ParserInstructions.Pulser.PCDATA)) == 'YES': # for automatic pulses
                while not (ptrs == fptrs).all():
                    active = ptrs<fptrs # identify active pointers
                    time = min(channeltimes[ptrs[active.nonzero()]]) # current time smallest value for "active" pointers
                    #LRJ 10-30-2013 hitstrue disables unused channels
                    lineindex=0
                    hitstrue=[]
                    for ct in channeltimes[ptrs]:
                            if self.channels.values()[lineindex].intedges.shape[1] == 2 and ct==time:
                                hitstrue.append(False)
                            else:
                                hitstrue.append(ct==time)
                            lineindex+=1  
                    hits = [ct == time for ct in channeltimes[ptrs]] # find active pointers
                    bits = bitarray(hitstrue) # assign bits based on whether a matching time was found
                    # populate output arrays
                    outvals[outptr] = numpy.fromstring((bits.tobytes()[::-1]),dtype=dtype)
                    outtimes[outptr] = time
                    # advances pointers if active and hits are both true for that pointer.
                    ptrs += numpy.logical_and(active, hits)
                    outptr += 1
            else: # for alternating rise/fall pulses
                while not (ptrs == fptrs).all():
                    active = ptrs<fptrs # identify active pointers
                    time = min(channeltimes[ptrs[active.nonzero()]]) # current time smallest value for "active" pointers
                    flips = [ct == time for ct in channeltimes[ptrs]] # find active pointers
                    bits = bits^bitarray(flips) # flip bits where updates dictate using bitwise XOR
                    # populate output arrays
                    outvals[outptr] = numpy.fromstring((bits[::-1].tobytes()[::-1]), dtype = dtype)
                    outtimes[outptr] = time
                    # advances pointers if active and flips and both true for that pointer.
                    ptrs += numpy.logical_and(active, flips)
                    outptr += 1
                # Now change final values to be zeros.
                bits = bitarray(0 for ch in self.channels.values())
                outvals[-1] = numpy.fromstring((bits[::-1].tobytes()[::-1]), dtype = dtype)
        else: # for alternating rise/fall pulses
            while not (ptrs == fptrs).all():
                active = ptrs<fptrs # identify active pointers
                time = min(channeltimes[ptrs[active.nonzero()]]) # current time smallest value for "active" pointers
                flips = [ct == time for ct in channeltimes[ptrs]] # find pointers that indicates state change             
                bits = bits^bitarray(flips) # flip bits where updates dictate using bitwise XOR
                # populate output arrays
                outvals[outptr] = numpy.fromstring((bits[::-1].tobytes()[::-1]), dtype = dtype)
                outtimes[outptr] = time
                # advances pointers if active and flips and both true for that pointer.
                ptrs += numpy.logical_and(active, flips)
                outptr += 1
            # Now change final values to be zeros.
            bits = bitarray(0 for ch in self.channels.values())
            outvals[-1] = numpy.fromstring((bits[::-1].tobytes()[::-1]), dtype = dtype)            
        self.rawchannels = self.channels
        self.channels = {0:channelData(self, 0, times = outtimes, values = outvals)}
        self.numchan = 1
        self.bytespervalue = int(Nbitout / 8)
        self.bytesperrepeat = 0
        return
        
    def TimingStringConstruct(self):
        """
        Constructs the for this timing group, by defining a place
        in memory, then calling ChannelData elements to construct and fill
        their fragments
        """
        # first reserve a place for the timinstring in memory        
        # calculate the total number of edges on the timingGroup
        self.numalledges=sum([chan.intedges.shape[1] for chan in self.channels.values()])
        # calculate length of control string for entire timing group in bytes
        self.tsbytes=self.numalledges*(self.bytesperrepeat+self.bytespervalue)+4*self.numchan+15  ### last two terms account for header and segment headers
        self.timingstring=numpy.ones(self.tsbytes,numpy.uint8)  # will hold timingstring
        # create the timingstring header
        # First part of the header is the length of the control string for the entire timing group.
        self.timingstring[0:8]=numpy.asarray([self.tsbytes], dtype='<u8').view('u1')
        self.timingstring[8:15]=numpy.append(
                                  numpy.asarray([self.numchan,self.bytespervalue,self.bytesperrepeat], dtype='<u1').view('u1'),
                                  numpy.asarray([self.denseT.size], dtype='<u4').view('u1'))
        self.tsptr=15  # a pointer to the current position for writing data into the timingstring
        self.determine_TS_method()
        # now output each channel's timing string fragment
        for chan in self.channels.values():
            chan.timingstring_construct()
        
    def determine_TS_method(self):
        """
        Determines the type of timingstring to output for this group, and tags
        whether group will have sparse timingstring representation using attribute
        self.isSparse
        """
        if self.dTrain:
            self.method='Digital_DelayTrain'
            self.isSparse=False
        else: 
            if (self.ResolutionBits>1 and self.bytesperrepeat!=0):
                self.method='Analog_VR'
                self.isSparse=True
            if (self.ResolutionBits==1 and self.bytesperrepeat==0):
                self.method='Digital_R'
                if hasattr(self,'repasint'): self.isSparse=not self.repasint
                else: self.isSparse=True
            
    def generate_clockEdges(self,ctimes,chanObj,channelnumber):
        """
        Generates and returns an edge array corresponding to a clocking string, given the clock times as a 1D numpy array, and a channel object
        """
        # find channel data for this clock: active rise / active fall, pulse-width, delaytrain  
                
        ctimes=numpy.unique(ctimes)
        if chanObj==None:
            chanObj=self.channelMap.getItemByFieldValueSet('Channel',{'TimingGroup':str(self.tGroup),'TimingGroupIndex':str(channelnumber)})    # find the channel
        if chanObj: 
            try:
                chanObj=chanObj.pop() # if the channels are returned as part of a list, get one channel object from list
            except AttributeError:
                pass # if it doesn't have a 'pop' attribute, then it is simply one channel object.
        aEdge=chanObj.get_childNodeValue_orDefault('ActiveClockEdge','rise')
        pWidth=chanObj.get_childNodeValue_orDefault('PulseWidth','')
        dTrain=self.tGroupNode.get_childNodeValue_orDefault('DelayTrain','No')
        if hasattr(self.tGroupNode, 'ParserInstructions'):
            aPulse = self.tGroupNode.ParserInstructions.get_childNodeValue_orDefault('Pulser','No')
        else:
            aPulse = self.tGroupNode.get_childNodeValue_orDefault('Pulser','No')
        high=1
        low=0
        if not (str.upper(str(dTrain)) == 'YES' or str.upper(str(aPulse)) == 'YES'):  # algorithm for using a standard value,repeat pair
            if pWidth=='':  # if pWidth not defined create bisecting falltimes
                falltimes=(ctimes[0:-1]+ctimes[1:])/2.  # creates too few falltimes; need a last fall            
                falltimes=numpy.append(falltimes,[ctimes[-1] + self.channelMap.hardwaretime]) # creates a last fall time a hardwaretime after last rise.
            else: # if pulsewidth defined, use it to create falltimes
                falltimes=numpy.add(ctimes,pWidth)
            if self.ResolutionBits>1: # algorithm for an analog clock channel (should rarely be used)
                high=chanObj.get_childNodeValue_orDefault('HighLevel',5.)
                low=chanObj.get_childNodeValue_orDefault('HighLevel',0.)
            if str.upper(aEdge)!='RISE':  # if not rising edge trigger, swap high and low
                low,high=high,low
            intedges=numpy.empty((5,(ctimes.shape[0]*2)))
            intedges[3,1::2]=low  # set values
            intedges[3,0::2]=high
            intedges[2,1::2]=falltimes  # set times
            intedges[2,0::2]=ctimes
            intedges[0,1::2]=falltimes  # set time indices 
            intedges[0,0::2]=ctimes           
        
        elif str.upper(str(aPulse)) == 'YES': # algorithm for an automatic pulser which does not require fall times/falls on its own
            intedges = numpy.empty((5, ctimes.shape[0])) 
            intedges[3,:] = high  # set all values as high, since they fall automatically
            intedges[2,:] = ctimes  # set reduced times
            intedges[0,:] = ctimes  # set times
            
        else: # algorithm for a delay train pulser (returns only delay count between successive pulses in slot 0, times in slot 2)
            # negative time values (such as for digital clocking channel) appear as ridiculously large positive times.
            # remove the large positive time, offset all times by 2ns, and add in a new start time                   
            delays=ctimes[1:]-ctimes[:-1]
            delays=numpy.append(delays,self.channelMap.hardwaretime) #LRJ 10-29-2013 final delay time set to hardware time
            intedges=numpy.empty((5,ctimes.shape[0]))
            intedges[4,:]=-1
            intedges[3,:]=high  # all values for a delay train are irrelevant; a pulse will be issued at time ordinate
            intedges[2,0:]=ctimes  # times are recorded as actual times
            intedges[0,:]=delays
        intedges[4,:]=-1  # denote that these are parser-generated edges       
        #intedges[0,:]=self.tGroup  # set tGroup
        intedges[1,:]=channelnumber  # set channel number
        return intedges

class channelData():
    """
    subclass of ControlArray to store individual channel data
    """
    def __init__(self,parent,channelnumber,times=None,values=None):
        self.channel=channelnumber
        self.parent=parent
               
        if times==None:
            self.clockchans=[parent.channelMap.isClock(parent.tGroup,x) for x in range(parent.numchan)] #LRJ 10-31-2013 create list of clock channels in the active timing group. False for non-clocker channels, clocked timing group number for clock channels
            self.isclock=parent.channelMap.isClock(parent.tGroup,self.channel)
            # find the channel for data, get biographicals                
            chanObj=parent.channelMap.getItemByFieldValueSet('Channel',{'TimingGroup':str(parent.tGroup),'TimingGroupIndex':str(self.channel)})    # find the channel
            self.chanObj = chanObj
            if hasattr(chanObj,'InitialValue'): self.initval=chanObj.InitialValue[0].parse()
            else: self.initval=0
            if hasattr(chanObj,'HoldingValue'): 
                if (chanObj.HoldingValue[0].parse()!= None):
                    self.holdingval=chanObj.HoldingValue[0].parse()
                else:
                    self.holdingval=0
            else: self.holdingval=0
            # retrieve intedges
            if self.isclock:
                # if this is a clock channel, take the clock edges if already constructed or construct from clockstring
                try: 
                    if parent.dTrain!=True: self.intedges=self.clock_harvest(parent.cEdges[self.channel],parent.denseT)
                    else: self.intedges=parent.cEdges[self.channel]
                except (AttributeError,KeyError):
                    self.intedges=parent.generate_clockEdges(parent.cStrings[self.channel],self.chanObj,self.channel)
                # replace reduced times with standard times if not a delay train (if delay train, this has already been done)
                #if parent.dTrain != True:
                    #self.intedges[2,:] = self.intedges[0,:]  # this line corrects silliness in the generate_clockedges routine, which puts nonsense into column 2 of intedges; that should be fixed in generate_clockedges, and this line should be removed - NDG 03-11-14
            else:
                # for a non-clock channel, start with explicitly defined edges
                # step through each interval, reparse and append data
                try: 
                    #replace times in groupEdges with the nearest coerced time in denseT using the edge_harvest method of ControlArray
                    #parent.groupEdges[2,:]=parent.edge_harvest(parent.groupEdges[2,:],parent.denseT)
                    edgesonchannel=parent.groupEdges[:,(parent.groupEdges[1,:]==self.channel).nonzero()[0]]                    
                    self.intedges=numpy.empty((5L,edgesonchannel.shape[1]))                    
                    for i in range(edgesonchannel.shape[1]):
                        self.intedges[:,i]=self.parent.sequence._fasttag_dict[edgesonchannel[4,i]].parse_harvest(parent.denseT)
                    #self.intedges=parent.groupEdges[:,(parent.groupEdges[1,:]==self.channel).nonzero()[0]]
                except IndexError: self.intedges=numpy.empty((5,0))
                try: self.chanIntervals=parent.groupIntervals[:,(parent.groupIntervals[1,:]==self.channel).nonzero()[0]]
                except IndexError: self.chanIntervals=numpy.empty((7,0))
                for intervalInd in self.chanIntervals[6,]:
                   # locate the next interval, reparse for denseT and append
                   interval=parent.sequence._fasttag_dict[intervalInd]
                   try: self.intedges=numpy.hstack((self.intedges,interval.parse_harvest(parent.denseT)))
                   except: pdb.set_trace()
            if parent.dTrain != True:
                # now replace timingGroup numbers with update index
                if self.intedges.shape[1]>0:
                    #self.intedges[0,:]=parent.denseT.searchsorted(self.intedges[2,:])
                    # now time-sort all intedges
                    self.intedges=self.intedges[:,self.intedges[0,:].argsort()]
            # The following lines is aimed to add the initial and holding values for this channel. This process is now acomplished by creating initial subsequence and 
            # holding subsequence
            if not self.isclock:
                # add first and last edge if necessary
                if self.intedges.shape[1]>0:
                    if self.intedges[2,0]!=0:
                        self.intedges=numpy.hstack([numpy.array([[parent.denseT.searchsorted(parent.channelMap.hardwaretime),self.channel,parent.channelMap.hardwaretime,self.initval,-1]]).transpose(),self.intedges])
                    if self.intedges[2,-1]!=parent.lasttimecoerced:
                        self.intedges=numpy.hstack([self.intedges,numpy.array([[parent.denseT.searchsorted(parent.lasttimecoerced),self.channel,parent.lasttimecoerced,self.holdingval,-1]]).transpose()])
                else: 
                    self.intedges=numpy.hstack([numpy.array([[parent.denseT.searchsorted(parent.channelMap.hardwaretime),self.channel,parent.channelMap.hardwaretime,self.initval,-1]]).transpose(),self.intedges]) 
                    self.intedges=numpy.hstack([self.intedges,numpy.array([[parent.denseT.searchsorted(parent.lasttimecoerced),self.channel,parent.lasttimecoerced,self.holdingval,-1]]).transpose()])
          
            #else:
                #pass
        else:
            self.intedges=numpy.empty((5,times.shape[0]),dtype=numpy.float)
            self.intedges[4,:]=-1
            self.intedges[1,:]=self.parent.tGroup
            self.intedges[0,:]=times
            self.intedges[2,:]=self.parent.denseT
            self.intedges[3,:]=values

    def clock_harvest(self,clock_edge_array,dense_time_array): #LRJ 3-11-2014
        
        '''
        Returns an edge array entry with coerced times from denseT that are nearest to an edge's requested time
        '''
        #searchsorted routine on clockedges needs to be time characterized, this algorithm may be inefficient LRJ 3-12-2014
        idx=dense_time_array.searchsorted(clock_edge_array[2])
        close_array=numpy.isclose(dense_time_array[idx],clock_edge_array[2],0,1e-8) #need a quick way to find lowest tres and replace 1e-8 LRJ 3-12-2014
        if close_array.all(): 
            clock_edge_array[0]=idx
            return clock_edge_array
        else: 
            idx_actual=self.parent.find_closest(dense_time_array,clock_edge_array[2][numpy.where(close_array,0,1).nonzero()])
            clock_edge_array[2][numpy.where(close_array,0,1).nonzero()]=dense_time_array[idx_actual]        
        clock_edge_array[0]=dense_time_array.searchsorted(clock_edge_array[2])        
        return clock_edge_array
            
    def apply_channelTransforms(self):
        """
        Applies XTSM-declared tranformations to the channel output, including declared
        calibrations, min's, and max's, and scales and offsets into integer ranges
        """
        try: 
            if not (self.chanObj.Calibration[0].PCDATA == '' or self.chanObj.Calibration[0].PCDATA == None):
                V=self.intedges[:,3] # the variable V can be referenced in channel calibration formula (eval'd next line)
                self.intedges[:,3]=eval(self.chanObj.Calibration[0].PCDATA)
        except: pass
        minv=maxv=''
        try:
            maxv=self.chanObj.MaxValue[0].parse()
            minv=self.chanObj.MinValue[0].parse()
        except: pass
        if ((minv == '') or (minv == None)): minv = min(self.intedges[:,3])
        if ((maxv == '') or (maxv == None)): maxv = max(self.intedges[:,3])
        numpy.clip(self.intedges[:,3],max(-self.parent.range/2.,minv),min(self.parent.range/2.,maxv),self.intedges[:,3])        
        # scale & offset values into integer ranges
        numpy.multiply(self.parent.DACCalibration,self.intedges[:,3],self.intedges[:,3]) #LRJ 10-15-2013,8*bytespervalue replaced ResolutionBits   
        
    def timingstring_construct(self):
        """
        inserts the timingstring fragment for this channel into the parent ControlArray's existing timingstring at position tsptr;
        also enforces min and max values, channel calibration expressions, and scales to byte-form (these should be split to ancillary methods for maintainability)
        """
        length=self.intedges.shape[1]
        # first a header denoting this channel's length in bytes as 4bytes, LSB leading
        self.parent.timingstring[self.parent.tsptr:(self.parent.tsptr+4)]=numpy.asarray([int(length*(self.parent.bytesperrepeat+self.parent.bytespervalue))], dtype='<u4').view('u1')
        self.parent.tsptr+=4
        self.intedges=self.intedges.transpose()
        if length>0 and self.parent.method!="Digital_DelayTrain":
            # Perform channel hardware limit transformations here:
            if not hasattr(self.parent,'repasint'): self.apply_channelTransforms()
            # calculate repeats
            reps=numpy.empty(length,dtype=numpy.int32)
            reps[:-1]=self.intedges[1:,0]-self.intedges[:-1,0]
            reps[-1]=1  # add last repeat of one
            # now need to interweave values / repeats
            # create a numedges x (self.bytespervalue+self.bytesperrepeat) sized byte array
            interweaver=numpy.empty([length,(self.parent.bytesperrepeat+self.parent.bytespervalue)],numpy.byte)
            # load values into first bytespervalue columns. LRJ 10-16-2013-"signed" float value from scaling is cast into Two's Complement U16 
            interweaver[:,0:self.parent.bytespervalue]=numpy.lib.stride_tricks.as_strided(
                numpy.asarray(self.intedges[:,3],dtype='<u'+str(self.parent.bytespervalue)).view('u1'),
                [length,self.parent.bytespervalue],[self.parent.bytespervalue,1])
            try:
                # load repeats into last bytesperrepeat columns
                interweaver[:,self.parent.bytespervalue:(self.parent.bytespervalue+self.parent.bytesperrepeat)]=numpy.lib.stride_tricks.as_strided(
                    numpy.asarray(reps,dtype='<u'+str(self.parent.bytesperrepeat)).view('u1'),
                    [length,self.parent.bytesperrepeat],[self.parent.bytesperrepeat,1])
            except TypeError:
                pass
            # copy into timingstring
            self.parent.timingstring[self.parent.tsptr:(self.parent.tsptr+length*(self.parent.bytesperrepeat+self.parent.bytespervalue))]=interweaver.view('u1').reshape(interweaver.shape[0]*(self.parent.bytesperrepeat+self.parent.bytespervalue))
            self.parent.tsptr+=length*(self.parent.bytesperrepeat+self.parent.bytespervalue)
        else: # delay train algorithm
            if length>0:
                self.parent.timingstring[self.parent.tsptr:(self.parent.tsptr+length*(self.parent.bytesperrepeat+self.parent.bytespervalue))]=numpy.asarray((self.intedges[:,0]/self.parent.parentgenresolution).round(), dtype='<u'+str(self.parent.bytesperrepeat)).view('u1')  # NEED THIS ALGORITHM!
                self.parent.tsptr+=length*(self.parent.bytesperrepeat+self.parent.bytespervalue)
                
class Sequence(gnosis.xml.objectify._XO_,XTSM_core):
    def collectTimingProffers(self):
        """
        Performs a first pass through all edges and intervals, parsing and collecting all ((Start/ /End)time/value/channel) entries necessary to arbitrate clocking edges
        """
        
        self.TimingProffer=TimingProffer(self)
        if (not hasattr(self,'guid_lookup')): 
            self.generate_guid()            
            self.generate_guid_lookup()
        if (not hasattr(self,'_fasttag_dict')): 
            self.generate_fasttag(0)
        for subsequence in self.SubSequence:
            subsequence.collectTimingProffers(self.TimingProffer)
        return None
        
    def parse(self):
        """
        top-level algorithm for parsing a sequence;
        equivalent to XTSM_parse in IDL code
        """
        # get the channelmap node from the XTSM object.
        cMap=self.getOwnerXTSM().getDescendentsByType("ChannelMap")[0]
      
        # Add undecleared channels to the ChannelMap node. The following line causes a problem
        #in the postparse step. Since all the undecleared channels are created as nonclock channels, even that the
        #channel is in the clocking group 6 (RIO01sync). Having initial edges on these channels are problematic 
        #at the postparse step, where it combines the timing group RIO01/syn with delaytrain. by JZ 12/18
    
        #cMap.creatMissingChannels()
        
        # Insert a initilization subsequence in the sequence and a holding subsequence
        #self.channelInitilization()
        #self.channelHolding()        
        # Decipher channelMap, get resolutions

        channelHeir=cMap.createTimingGroupHeirarchy()        
        channelRes=cMap.findTimingGroupResolutions()
        
        # collect requested timing edges, intervals, etc...
          
        self.collectTimingProffers()
        
        
        
        # create an element to hold parser output
        pOutNode=self.insert(ParserOutput())
        # step through timing groups, starting from lowest on heirarchy
        #sorted (channelHeir, key=channelHeir.__getitem__) returns a list of groupnumer in the order of clocklevel, from low to high
        for tgroup in sorted(channelHeir, key=channelHeir.__getitem__):
            cA=pOutNode.insert(ControlData()) # create a control array node tagged with group number
            cA.insert(GroupNumber().set_value(tgroup))
            cA.insert(ControlArray().construct(self,cMap,tgroup))
        return

    def get_starttime(self):
        """
        gets the starttime for the sequence from XTSM tags(a parsed 'StartTime' tag). This method is added on 12/12/13 by JZ.
        """
        cMap=self.getOwnerXTSM().getDescendentsByType("ChannelMap")[0]
        ht=cMap.getHardwaretime()        
        
        if hasattr(self,'StartTime'):
            if not self.StartTime[0].PCDATA == None :
                starttime=self.StartTime[0].parse()
                self.starttime=starttime+2*ht
            else: self.starttime=2*ht
        else: self.starttime=2*ht    
        return self.starttime
    
    
    def get_endtime(self):
        """
        gets the endtime for the sequence from XTSM tags (a parsed 'EndTime' tag)
        or coerces to final time in edge and intervals, or to default maximum length
        of 100s. Leaving the EndTime node blank will make the endtime equal to the 
        maximum requested time plus twice the resolution of the slowest board.
        """
        maxlasttime=100000 # a default maximum sequence length in ms!!! 
        if hasattr(self,'EndTime'):
            #st=self.get_starttime()
            endtime=self.EndTime[0].parse()
            if ((endtime < maxlasttime) and (endtime > 0)): 
                self.endtime = endtime
            else: 
                if hasattr(self,'TimingProffer'): #LRJ 3-13-2014
                    try: edgeet=self.TimingProffer.data['Edge'][:,2].max()
                    except ValueError: edgeet=0
                    try: int1et=self.TimingProffer.data['Interval'][:,2].max()
                    except ValueError: int1et=0
                    try: int2et=self.TimingProffer.data['Interval'][:,3].max()
                    except ValueError: int2et=0
                    self.endtime=max(edgeet,int1et,int2et)+2*self.getOwnerXTSM().getDescendentsByType("ChannelMap")[0].hardwaretime
                else:               
                    self.endtime = maxlasttime
                    self.EndTime[0].addAttribute('parser_error','Invalid value: Coerced to '+str(maxlasttime)+' ms.')
        return self.endtime
        
    def channelInitilization(self):
        """
        At the beginning of the sequence, insert a initilization subsequence to set all the nonclock channel to the initial value at initial time. Added on 12/12/13 by JZ.
        """
        
        
        
        # First create a initialization subsequence as a instance of SubSequence class.
        inisequence=SubSequence()
        st=gnosis.xml.objectify._XO_StartTime()
        cMap=self.getOwnerXTSM().getDescendentsByType("ChannelMap")[0]
        channelRes=cMap.findTimingGroupResolutions()
        channelHeir=cMap.createTimingGroupHeirarchy()
        timesort=[]
        for s in range(len(channelHeir)):
            tgadvance=(2**channelHeir[s])*channelRes[s]
            timesort.append(tgadvance)
        initime=max(timesort)
        
        st.set_value(-initime)
        inisequence.insert(st)
        for chan in cMap.Channel:
            parserEdge=Edge()
            channelname=OnChannel()
            time=gnosis.xml.objectify._XO_Time()
            value=gnosis.xml.objectify._XO_Value()
            
            if hasattr(chan,'ChannelName'):
                channelname.set_value(chan.ChannelName[0].PCDATA)
                
            [tg,tgi]=cMap.getChannelIndices(channelname.PCDATA)
            if not cMap.isClock(tg,tgi):
                parserEdge.insert(channelname)
                time.set_value(0)
                if hasattr(chan,'InitialValue'):
                    value.set_value(chan.InitialValue.parse())
                else: value.set_value(0)
                parserEdge.insert(time)
                parserEdge.insert(value)
                       
                inisequence.insert(parserEdge)
            else: continue
        
        self.insert(inisequence)
        
        return None
        
        
    def channelHolding(self):
        """
        At the end of the sequence, insert a holding subsequence to set all the nonclock channel to the holding value at sequence endtime. Added on 12/19/13 by JZ.
        """
        holdsequence=SubSequence()
        st=gnosis.xml.objectify._XO_StartTime()
        cMap=self.getOwnerXTSM().getDescendentsByType("ChannelMap")[0]
        endtime=self.get_endtime()
        st.set_value(endtime)
        holdsequence.insert(st)
        
        for chan in cMap.Channel:
            parserEdge=Edge()
            channelname=OnChannel()
            time=gnosis.xml.objectify._XO_Time()
            value=gnosis.xml.objectify._XO_Value()
            
            if hasattr(chan,'ChannelName'):
                channelname.set_value(chan.ChannelName[0].PCDATA)
            
            [tg,tgi]=cMap.getChannelIndices(channelname.PCDATA)
            if not cMap.isClock(tg,tgi):
                parserEdge.insert(channelname)
                time.set_value(0)
                if hasattr(chan,'HoldingValue'):
                    if not chan.HoldingValue.PCDATA == None:
                        value.set_value(chan.HoldingValue.parse())
                    else: value.set_value(0)
                                                                                             
                else: value.set_value(0)
                parserEdge.insert(time)
                parserEdge.insert(value)
                       
                holdsequence.insert(parserEdge)
            else: continue
        
        self.insert(holdsequence)    
        
        return None
            
            
            
            

class SubSequence(gnosis.xml.objectify._XO_,XTSM_core):
    def collectTimingProffers(self,timingProffer):
        """
        Performs a first pass through all edges and intervals, parsing and collecting all ((Start/ /End)time/value/channel) entries 
        necessary to arbitrate clocking edges
        """
        # Find the subsequence starttime and pass it to the subnode edge time,  interval and subsequence starttime, JZ on 12/12/13
        
        starttime=self.get_starttime()
        
        if (hasattr(self,'Edge')):
            for edge in self.Edge:
                timingProffer.insert('Edge',edge.parse_proffer(starttime))
        if (hasattr(self,'Interval')):
            for interval in self.Interval:
                timingProffer.insert('Interval',interval.parse_proffer(starttime)) 
        if (hasattr(self,'SubSequence')):
            for subsequence in self.SubSequence:
                subsequence.collectTimingProffers(timingProffer)
        return None
    
    def get_starttime(self):
        """
        gets the starttime for the subsequence from XTSM tags(a parsed 'StartTime' tag) and add the starttime of its parent, return the absolute starttime . This method is added on 12/12/13 by JZ.
        """
        if hasattr(self,'StartTime'):
            
            substarttime=self.StartTime[0].parse()
            try:
                self.starttime=substarttime+self.__parent__.get_starttime()
            except: print 'Subsequence StartTime Ivalid.'    
        return self.starttime
        
        
class ChannelMap(gnosis.xml.objectify._XO_,XTSM_core):
    def getChannelIndices(self,channelName):
        """
        returns the timingGroup number and timingGroup index for a channel of specified name as a pair [tg,tgi]
        """
        if (not hasattr(self,'Channel')): return [-1,-1]
        for chan in self.Channel:
            if hasattr(chan,'ChannelName'):
                if chan.ChannelName[0].PCDATA==channelName: 
                    return [float(chan.TimingGroup[0].PCDATA),float(chan.TimingGroupIndex[0].PCDATA)]
        else: return [-1,-1]

    def getClocks(self):
        """
        Assembles a list of all clocking channels and stores as self.Clocks
        """
        self.Clocks={}
        for tg in self.TimingGroupData:
            if hasattr(tg,'ClockedBy'):
                clck=self.getChannel(tg.ClockedBy[0].PCDATA)
                if clck != None:
                    self.Clocks.update({int(tg.GroupNumber[0].PCDATA):[int(clck.TimingGroup[0].PCDATA),int(clck.TimingGroupIndex[0].PCDATA)]})
        return

    def isClock(self,timingGroup,channelIndex):
        """
        returns False if channel is not a clock; otherwise returns timingGroup number
        the channel is a clock for
        """
        if (not hasattr(self,'Clocks')):
            self.getClocks()
        for tg,c in self.Clocks.items():
            if c==[timingGroup,channelIndex]:
                return tg
        return False

    def getChannel(self,channelName):
        """
        returns the timingGroup number and timingGroup index for a channel of specified name as a pair [tg,tgi]. Return the channel node, not the index
        """
        if (not hasattr(self,'Channel')): return None
        for chan in self.Channel:
            if hasattr(chan,'ChannelName'):
                if chan.ChannelName[0].PCDATA==channelName: 
                    return chan
        else: return None
        
    def createTimingGroupHeirarchy(self):
        """
        Creates a heirarchy of timing-groups by associating each with a level.
        The lowest level, 0, clocks nothing
        one of level 1 clocks one of level 0        
        one of level 2 clocks one of level 1...etc
        results are stored in the object as attribute tGroupClockLevels,
        which is a dictionary of (timingGroup# : timingGroupLevel) pairs
        """
        tgroups=self.getDescendentsByType('TimingGroupData')
        tGroupClockLevels=numpy.zeros(len(tgroups),numpy.byte)
        bumpcount=1
        while bumpcount!=0:
            maxlevel=max(tGroupClockLevels)
            if maxlevel>len(tgroups): pass #raise exception for circular loop
            bumpcount=0
            tgn=[]
            for s in range(len(tgroups)):
                if hasattr(tgroups[s],"GroupNumber"):
                    gn=int(tgroups[s].GroupNumber[0].PCDATA)
                else: pass
                    # raise 'All timing groups must have groupnumbers; offending <TimingGroupData> node has position '+s+' in channelmap'
                if maxlevel==0: tgn=[tgn,gn]
                if (tGroupClockLevels[s] == maxlevel):
                    if hasattr(tgroups[s],'ClockedBy'): clocksource=tgroups[s].ClockedBy.PCDATA
                    else: pass # raise 'TimingGroup '+gn+' must have a channel as clock source (<ClockedBy> node)' 
                    if (clocksource != 'self'):
                        clockgroup=self.getChannel(clocksource).TimingGroup[0].PCDATA
                        for k in range(len(tgroups)):
                            if tgroups[k].GroupNumber[0].PCDATA==clockgroup: break
                        tGroupClockLevels[k]=maxlevel+1
                        bumpcount+=1
        tGroupNumbers = [int(a.GroupNumber.PCDATA) for a in self.getDescendentsByType('TimingGroupData')]
        self.tGroupClockLevels = dict(zip(tGroupNumbers,tGroupClockLevels)) # dictionary of tg#:tgLevel pairs
        return self.tGroupClockLevels
        
    def findTimingGroupResolutions(self):
        """
        establish clocking resolutions which work for each clocking chain, 
        such that descendents clock at a multiple of their clocker's base frequency
        stores result at self.tGroupClockResolutions
        (first establishes a timingGroup heirarchy if not already existent on node)        
        Untested - should follow block at line 627 in IDL version
        """
        if (not hasattr(self,'tGroupClockLevels')): self.createTimingGroupHeirarchy()
        cl=max(self.tGroupClockLevels.values()) 
        res={}        
        while (cl >=0):
            tgThisLevel=[tg for tg,tgl in self.tGroupClockLevels.items() if tgl==cl]
            for tg in tgThisLevel:
                tgNode=self.getItemByFieldValue('TimingGroupData','GroupNumber',str(tg))
                if hasattr(tgNode,'ClockPeriod'):
                    cpNode=tgNode.ClockPeriod[0]
                    clockperiod=cpNode.PCDATA
                else: 
                    clockperiod=0.0002   # add a clockperiod node with default value
                    cpNode=tgNode.insert(ClockPeriod(str(clockperiod)))
                if hasattr(cpNode,'current_value'): 
                    if cpNode.current_value != u'':
                        clockperiod=cpNode.current_value
                if hasattr(tgNode,'ClockedBy'):
                    if tgNode.ClockedBy[0].PCDATA!='self':
                        clocksource=tgNode.ClockedBy[0].PCDATA
                        clockgroup=self.getItemByFieldValue('TimingGroupData','GroupNumber',self.getChannel(clocksource).TimingGroup[0].PCDATA)
                        if hasattr(clockgroup,'ClockPeriod'):
                            if hasattr(clockgroup.ClockPeriod[0],'current_value'):
                                timerperiod=clockgroup.ClockPeriod[0].current_value
                            else: timerperiod=clockgroup.ClockPeriod[0].PCDATA
                        else: timerperiod=0.0002
                        clockperiod=math.ceil(float(clockperiod)/float(timerperiod))*float(timerperiod)
                if hasattr(tg,'current_value'):
                    tgNode.current_value=str(clockperiod)
                else: tgNode.addAttribute('current_value',str(clockperiod))
                try: res.update({tg:float(clockperiod)})  # this needs to be converted to a numeric value, not a string !!!!!
                except ValueError: res.update({tg:0.0002})
            cl-=1
        self.tGroupClockResolutions=res
        #self.hardwaretime=self.getDictMaxValue(self.tGroupClockResolutions)
        return res
    
    def getHardwaretime(self):
        """
        This method is used to get the minimum time advance required to syn the level 0 board. Added on 12/19/2013 by JZ.
        """
        channelRes=self.findTimingGroupResolutions()
        channelHeir=self.createTimingGroupHeirarchy()
        timesort=[]
        for s in range(len(channelHeir)):
            tgadvance=(2**channelHeir[s])*channelRes[s]
            timesort.append(tgadvance)
        hardwaretime=max(timesort)
        self.hardwaretime=hardwaretime
        
        return self.hardwaretime
          
    
    def creatMissingChannels(self):
        """
        This methods intends to create undecleared channels for each timing group, including/not including the FPGA board, in the channalmap and assign initial and holding values for them. 
        """
        # First for each TimingGroupData in the channelmap, find its GroupNumber and Channelcount. Count how many channels are in this timing group. 
        # First find the number of timing groups in the channelmap.
        timinggroup=self.getDescendentsByType('TimingGroupData')
        channel=self.getDescendentsByType('Channel')
        
        #The following define all the missing channels and assign default initial and holding values for them, including the channels on the PFGA board.
        for tg in range(len(timinggroup)):
            # Get the timing group number and channelcount in this timinggroup.            
            tgn=int(timinggroup[tg].GroupNumber[0].PCDATA)
            chancount=int(timinggroup[tg].ChannelCount[0].PCDATA)
            for tgi in range(chancount):
                # Check whether this channel has been decleared. If yes, then check the next channel. 
                # If not, then declear this channel with default initial and holding value.              
                for chan in channel:
                    ctg=int(chan.TimingGroup[0].PCDATA)
                    ctgi=int(chan.TimingGroupIndex[0].PCDATA)
                    if [tgn,tgi]==[ctg,ctgi]: break
                else:
                    newchannel=gnosis.xml.objectify._XO_Channel()
                    newname=gnosis.xml.objectify._XO_ChannelName()
                    newtg=gnosis.xml.objectify._XO_TimingGroup()
                    newtgi=gnosis.xml.objectify._XO_TimingGroupIndex()
                    newinival=gnosis.xml.objectify._XO_InitialValue()
                    newholdval=gnosis.xml.objectify._XO_HoldingValue()
                    
                    nm='TG'+str(tgn)+'TGI'+str(tgi)
                    newname.set_value(nm)
                    newtg.set_value(tgn)
                    newtgi.set_value(tgi)
                    newinival.set_value(0)
                    newholdval.set_value(0)
                    
                    newchannel.insert(newname)
                    newchannel.insert(newtg)
                    newchannel.insert(newtgi)
                    newchannel.insert(newinival)
                    newchannel.insert(newholdval)
                    
                    self.insert(newchannel)
        
        return None
        
        #The following define all the missing channels and assign default initial and holding values for them, not including the channels on the PFGA board.
        '''
        for tg in timinggroup:
            if not ((tg.Name[0].PCDATA == 'RIO01/sync') or (tg.Name[0].PCDATA == 'RIO01/delaytrain')):
                tgn=int(tg.GroupNumber[0].PCDATA)
                chancount=int(tg.ChannelCount[0].PCDATA)
                for tgi in range(chancount):
                    for chan in channel:
                        chantg=int(chan.TimingGroup[0].PCDATA)
                        chantgi=int(chan.TimingGroupIndex[0].PCDATA)
                        if [tgn,tgi]==[chantg,chantgi]: break
                    else:
                        newchannel=gnosis.xml.objectify._XO_Channel()
                        newname=gnosis.xml.objectify._XO_ChannelName()
                        newtg=gnosis.xml.objectify._XO_TimingGroup()
                        newtgi=gnosis.xml.objectify._XO_TimingGroupIndex()
                        newinival=gnosis.xml.objectify._XO_InitialValue()
                        newholdval=gnosis.xml.objectify._XO_HoldingValue()
                        
                        nm='TG_'+str(tgn)+'_TGI_'+str(tgi)
                        newname.set_value(nm)
                        newtg.set_value(tgn)
                        newtgi.set_value(tgi)
                        newinival.set_value(0)
                        newholdval.set_value(0)
                        
                        newchannel.insert(newname)
                        newchannel.insert(newtg)
                        newchannel.insert(newtgi)
                        newchannel.insert(newinival)
                        newchannel.insert(newholdval)
                        
                        self.insert(newchannel)
                        
        return None
                
       '''        
       
        
        
        
        
        
        
        
        
        
        
        
        
class Edge(gnosis.xml.objectify._XO_,XTSM_core):
    scopePeers=[['Channel','ChannelName','OnChannel']]
    def parse_proffer(self,startTime):
        """
        returns parsed values for [[timinggroup,channel,time,edge]]
        times will be returned relative to the provided (numeric) start-time
        unfinished!
        """
        t=self.Time[0].parse()+startTime
        self.time=t
        v=self.Value[0].parse()
        self.value=v
        [tg,c]=self.OnChannel[0].getTimingGroupIndex()
        self.channel=c        
        if (not hasattr(self,'guid')):
            self.generate_guid(1)
        if hasattr(self,'_fasttag'): return [tg,c,t,v,self._fasttag]
        else: return [tg,c,t,v,-1]
        
    def parse_harvest(self,dense_time_array):
        '''
        Returns an edge array entry with coerced times from denseT that are nearest to an edge's requested time
        ''' 
        idx=dense_time_array.searchsorted(self.time)
        if dense_time_array[idx]!=self.time: 
            try:
                if abs(dense_time_array[idx]-self.time)>abs(dense_time_array[idx-1]-self.time):
                    idx=idx-1
            except IndexError: pass
        self.Time[0].addAttribute("current_value",str(dense_time_array[idx]))
        self.time=dense_time_array[idx]
        self.value=self.Value[0].parse({'T':self.time,'TI':self.time})
        return numpy.array([idx,self.channel,self.time,self.value,self._fasttag])
        
#class ParserEdge(gnosis.xml.objectify._XO_,XTSM_core):
    """
    A class for parser-generated timing edges.      
    """

#class Time(gnosis.xml.objectify._XO_,XTSM_core):
    #pass

#class Value(gnosis.xml.objectify._XO_,XTSM_core):
   
#class Name(gnosis.xml.objectify._XO_,XTSM_core):
    #pass

#class StartTime(gnosis.xml.objectify._XO_,XTSM_core):
    #pass

class Interval(gnosis.xml.objectify._XO_,XTSM_core):
    scopePeers=[['Channel','ChannelName','OnChannel']]
    def parse_proffer(self,startTime):
        """
        returns parsed values for [[timinggroup,channel,starttime,endttime,Vresolution,Tresolution,edge]]
        times will be returned relative to the provided (numeric) start-time
        unfinished!
        """
        st=self.StartTime[0].parse()+startTime
        et=self.EndTime[0].parse()+startTime
        self.endtime=et
        self.starttime=st
        #v=self.Value[0].parse()
        vres=self.VResolution[0].parse()
        tres=self.TResolution[0].parse()
        [tg,c]=self.OnChannel[0].getTimingGroupIndex()
        self.tg=tg
        self.c=c
        if (not hasattr(self,'guid')):
            self.generate_guid(1)
        if hasattr(self,'_fasttag'): return [tg,c,st,et,vres,tres,self._fasttag]
        else: return [tg,c,st,et,vres,tres,-1]
        
    def expected_samples(self, dense_time_array):
        """
        Returns number of samples interval will generate given a dense time array
        """
        return ((dense_time_array>=self.starttime)&(dense_time_array<=self.endtime)).sum()
        
    def parse_harvest(self, dense_time_array):
        """
        Returns all edges according to times in this interval
        first index (timinggroup number) replaced with time index
        """
        
        time_res = eval(self.TResolution.PCDATA)
        startind=dense_time_array.searchsorted(self.starttime)
        endind=dense_time_array.searchsorted(self.endtime)        
        # The update times for this interval are extracted using the indices. JZ 12/27/2013        
        T=dense_time_array[startind:(endind+1)]        
        # The next line is commented out by JZ on 12/27/2013. Sometimes the extraction will miss elements due to time coercing.        
        #T=numpy.extract((dense_time_array>=self.starttime)*(dense_time_array<=self.endtime),dense_time_array)
        TI=T-self.starttime
        # now find times which are not on the interval's time resolution
        # JZ comment the following lines 1294 to 1305 on 12/9/2013
        #repeats = []
        #for time in T:
            #test_exp = time % time_res
            # eliminate rounding errors in modulus calculations to 100ns precision.
            #test_exp = math.floor((test_exp * (10**7)) + 1) - 1
            #if test_exp: # mod != 0
                #repeats.append(time)
        #repeats.reverse()
        # delete the incorrect times
        #for elem in repeats:
            #T = numpy.delete(T, elem)
            #TI = numpy.delete(TI, elem)
        # now re-evaluate values using these times
        V=self.Value[0].parse({'T':T,'TI':TI})
        numelm=T.size
        #startind=dense_time_array.searchsorted(self.starttime)
        #endind=dense_time_array.searchsorted(self.endtime)
        
        if hasattr(self,'_fasttag'):                    
            
            # next line was found problematic on 12/06/13 by ndg and jz - 
            #new_array = numpy.array([numpy.arange(startind,endind+1),numpy.repeat(self.c,numelm),T,V,numpy.repeat(self._fasttag,numelm)])
            # Next line may have problem, since             
            new_array = numpy.vstack((numpy.arange(startind,endind+1),numpy.repeat(self.c,numelm),T,V,numpy.repeat(self._fasttag,numelm)))            
            
            return new_array

class OnChannel(gnosis.xml.objectify._XO_,XTSM_core):
    def getTimingGroupIndex(self):
        """
        This should return the timingGroup number and and index of the channel.
        Unfinished!
        """
        [tg,c]=self.getOwnerXTSM().head[0].ChannelMap[0].getChannelIndices(self.PCDATA)
        return [tg,c]

class Parameter(gnosis.xml.objectify._XO_,XTSM_core):
    def __init__(self, name=None, value=None):
        XTSM_core.__init__(self)
        if name!=None:
            self.insert(gnosis.xml.objectify._XO_Name(name))
        if value!=None:
            self.insert(gnosis.xml.objectify._XO_Value(value))
        return None

def main_test():
    """
    Trouble-shooting and testing procedure - not for long-term use
    """
    # parse the XML file
    # c:/wamp/www/sequences/8-6-2012/alternate.xtsm
    # /12-1-2012/FPGA_based.xtsm
   # xml_obj = gnosis.xml.objectify.XML_Objectify(u'c:/wamp/vortex/sequences/12-1-2012/FPGA_based_complex.xtsm')
    xml_obj = gnosis.xml.objectify.XML_Objectify(u'C:/wamp/www/MetaViewer/sequences/9-21-2013/14h_3m_9s.xtsm')
    py_obj = xml_obj.make_instance()
    py_obj.insert(Parameter(u'shotnumber',u'23'))
    try: py_obj.body.Sequence[0].parse()
    except:
        type, value, tb = sys.exc_info()
        traceback.print_exc()
        last_frame = lambda tb=tb: last_frame(tb.tb_next) if tb.tb_next else tb
        frame = last_frame().tb_frame
        ns = dict(frame.f_globals)
        ns.update(frame.f_locals)
        code.interact(local=ns)
    return py_obj

def trace_on_err():
    """
    Used to trace into error location automatically - not used long-term
    """
    type, value, tb = sys.exc_info()
    traceback.print_exc()
    last_frame = lambda tb=tb: last_frame(tb.tb_next) if tb.tb_next else tb
    frame = last_frame().tb_frame
    ns = dict(frame.f_globals)
    ns.update(frame.f_locals)
    code.interact(local=ns)


def trace_calls(frame, event, arg):
    if event != 'call':
        return 
    co = frame.f_code
    func_name = co.co_name
    if func_name == 'write':
        # Ignore write() calls from print statements
        return
    func_line_no = frame.f_lineno
    func_filename = co.co_filename
    caller = frame.f_back
    caller_line_no = caller.f_lineno
    caller_filename = caller.f_code.co_filename
    print 'Call to %s on line %s of %s from line %s of %s' % \
        (func_name, func_line_no, func_filename,
         caller_line_no, caller_filename)
    return

class InvalidSource(Exception):
    """
    An exception class raised in the XTSM_Object initialization routine
    """
    def __init__(self,source):
        self.msg='type '+str(type(source))+' cannot create an XTSM object'

class XTSM_Object(object):
    def __init__(self,source):
        """
        Builds an XTSM object from an XTSM string, a file-like stream or a filepath to
        a textfile containing xtsm - THIS IS A TOPLEVEL ROUTINE FOR THE PARSER 
        """
        if not isinstance(source, basestring):
            try: source=source.getvalue()
            except AttributeError: 
                raise InvalidSource(source)
        if source.find('<XTSM')==-1:
            try: source=urllib.urlopen(source).read()
            except IOError: 
                try: source=urllib.urlopen('file:'+source).read()
                except IOError: InvalidSource(source)
        self.XTSM = gnosis.xml.objectify.make_instance(source)
        
    def parse(self, shotnumber = 0):
        """
        parses the appropriate sequence, given a shotnumber (defaults to zero)
        - THIS IS A TOPLEVEL ROUTINE FOR THE PARSER
        """
        self.XTSM.insert(Parameter(u'shotnumber',str(shotnumber)))
        parserOutput=self.XTSM.body[0].parseActiveSequence()
        return parserOutput

class Command_Library:
    """
    Houses a list of commands for pre/post parsing instructions.
    
    Note: Any functions which require additional values beyond "self" and "xtsm_obj" 
        should receive them all as a single variable, aka a 1D array of extra variables.
    """
    def __init__(self):
        pass
    
    def combine_with_delaytrain(self, XTSM_obj, params):
        """
        POST PARSE COMMAND ONLY
        
        Combines one or more timing groups with the delay train. Must have the
        same number of updates as the delay train. Final group will take the 
        place of the delay train and delete all others.
        Required params: Timing Groups Names.
            The Timing Group Names should all be strings. Timing string values will be appended in the order that
            the timing groups are input. Must include a delay train.
        Optional params: Length per Value, Length of Filler, Position of Filler
            Length per Value is an integer representing the number of bytes each end-value should be. Default is the length of the original values combined with no filler.
                Note: If this field is shorter than the combined length of the original values, this field will be ingored.
                (Ex: Sync has values == 1 byte, Delaytrain has "values" == 4 bytes. Hence, Length per value has a default value of 5 and must be >= 5.)
            Position of Filler should only be present if Length per Value > end-value length. This specifies the index at which filler will be placed.
                If unspecified, all filler will be placed at the end of the end-value.
                (Ex: Sync, Filler, Delaytrain has Position of filler == 1, since Sync takes the 0th position.)
            Length of Filler should be an integer number of bytes for the first filler. This variable should only be present if directly preceeded by a Position of Filler variable.
                If unspecified, will take on the largest possible filler length.
            Note: This Position of Filler/Length of Filler cycle can repeated. Each pair is executed sequentially.
        """
        # File params as either a timing group or a filler number.
       
        timing_group_names = []
        filler_info = []
        for param in params:
            if param != None:  # Ignore blank params.
                try:  # If the param can be expressed as an integer, then it's not a timing group name.
                    filler_info.append(int(param))
                except ValueError:
                    timing_group_names.append(str(param))
        # Gets relevant information (such as bytes_per_value, or bpv) from each group. The delay group is handled differently from the other groups.
        control_num = []
        timingstring_values = []
        num_updates = []
        value_size = 0
        for tg_name in timing_group_names:
            for k in range(len(XTSM_obj.ControlData)):
                ControlData = XTSM_obj.ControlData[k]
                if str(ControlData.ControlArray.tGroupNode.Name._seq[0]) == tg_name:
                    control_num.append(k)
                    # Now get the values for each timing group.
                    tg_string = ControlData.ControlArray.timingstring.tolist()
                    tg_body = tg_string[19:]
                    tg_bpr = tg_string[10]
                    tg_values = []
                    if hasattr(ControlData.ControlArray.tGroupNode, "DelayTrain"):
                        dControlData = ControlData
                        value_size += tg_bpr
                        # Note: For the delay train, the repeats are the "values".
                        for i in range(0, len(tg_body), (tg_bpr)):
                            tg_values.append(tg_body[i:(i+tg_bpr)])
                        num_updates.append(len(tg_values))
                    else:
                        tg_bpv = tg_string[9]
                        value_size += tg_bpv
                        for i in range(0, len(tg_body), (tg_bpv + tg_bpr)):
                            tg_values.append(tg_body[i:(i+tg_bpv)])
                    timingstring_values.append(tg_values)
        # Now that the data is extracted, delete the old timing groups.
        
        control_num.sort()
        control_num.reverse()  # List is sorted and reversed so as to not mess up the indeces of higher entries by deleting a lower entry.
        for i in control_num:
            del XTSM_obj.ControlData[i]
        # Find the max value size, if specified.
        if filler_info:
            max_size = filler_info.pop(0)
            
        else:
            max_size = value_size
        # If the max value size is larger than the current value size, look for filler pos/len pairs. Then place filler in the designated (or default) position.
        while value_size < max_size:
            
            try:
                filler_pos = filler_info.pop(0)
                try:
                    filler_len = filler_info.pop(0)
                except:
                    filler_len = max_size - value_size
            except:
                filler_pos = len(timingstring_values)
                filler_len = max_size - value_size
            # Insert a new column with only one element at the filler position. This element has the filler length as its value.
            timingstring_values.insert(filler_pos, [filler_len])
            value_size += filler_len
        
        # Joins next timingstring array in timingstring_values to the previous one. If the next array is a filler, create a zero array with dimensions specified by the number of updates and the filler length.
                
        for group_values in timingstring_values:
            if len(group_values) == 1:
                try:
                    newstring_body = numpy.concatenate((newstring_body, numpy.zeros((num_updates[0], group_values[0]), dtype = "uint8")), axis = 1)
                except NameError:
                    try:
                        newstring_body = numpy.zeros((num_updates[0], group_values[0]), dtype = "uint8")
                    except ValueError: print 'valueError Found!'
                    
            else:
                try:
                    newstring_body = numpy.concatenate((newstring_body, numpy.array(group_values, dtype = "uint8")), axis = 1)
                except NameError:
                    newstring_body = numpy.array(group_values, dtype = "uint8")
        # Flatten the new array so that it's a 1D array of values.
        newstring_body = newstring_body.flatten()
        # Reconstruct a new header, given the string length, number of channels (1), bytes_per_value (0), bytes_per_repeat (value_size), num_updates, and body length.
        body_length = newstring_body.shape[0]
        string_length = body_length + 19
        newstring = numpy.concatenate((numpy.array([string_length], dtype = "<u8").view("<u1"), numpy.array([1,0,value_size], dtype = "<u1"), numpy.array([num_updates[0], body_length], dtype = "<u4").view("<u1"), newstring_body))
        # Replace the delay train's timingstring with the new timingstring. Then send the new delay train data back to the XTSM object.
        dControlData.ControlArray.timingstring = newstring
        XTSM_obj.ControlData.append(dControlData)




def preparse(xtsm_obj):
    """
    Executes functions before parsing the XTSM code.
    """
    xtsm_obj.Command_Library = Command_Library()
    for command in xtsm_obj.XTSM.head.PreParseInstructions.ParserCommand:
        try:
            # Check if the command exists in the Command Library. If so, execute it.
            command_name = getattr(xtsm_obj.Command_Library, str(command.Name.PCDATA))
            command_vars = []
            try:
                # Check for values to go with the command.
                non_blank_var = False
                for var in command.Value:
                    command_vars.append(var.PCDATA)
                    if var.PCDATA != None:
                        non_blank_var = True
                if non_blank_var:
                    command_name(xtsm_obj, command_vars)
                else:
                    command_name(xtsm_obj)
            except:
                command_name(xtsm_obj)
        except AttributeError:
            # If the command field is not blank, print missing command error.
            if command.Name.PCDATA != None:
                print 'Missing command function: ' + command.Name.PCDATA

def postparse(timingstring):
    """
    Executes functions after parsing the XTSM code.Combine timing strings from timing groups with the delay train. 
    You must list names of groups to combine (each in a seperate "value" field), including the delay train group.  These groups must have the same number of updates.
    You can optionally include integer values for a byte-length-per-value, along with filler position and filler length, the latter two of which can be repeated indefinitely.
    For more info, see the parser's Command_Library.
    """
    
    timingstring.Command_Library = Command_Library()
    timingstring.XTSM = timingstring.__parent__.__parent__.__parent__
    for command in timingstring.XTSM.head.PostParseInstructions.ParserCommand:
        try:
            # Check if the command exists in the Command Library. If so, execute it.
            command_name = getattr(timingstring.Command_Library, str(command.Name.PCDATA))
            command_vars = []
            try:
                # Check for values to go with the command.
                non_blank_var = False
                for var in command.Value:
                    command_vars.append(var.PCDATA)
                    if var.PCDATA != None:
                        non_blank_var = True
                if non_blank_var:
                    command_name(timingstring, command_vars)
                else:
                    command_name(timingstring)
            except:
                command_name(timingstring)
        except AttributeError:
            # If the command field is not blank, print missing command error.
            if command.Name.PCDATA != None:
                print 'Missing command function: ' + command.Name.PCDATA
        
        
# module initialization
# override the objectify default class
gnosis.xml.objectify._XO_ = XTSM_Element
# identify all XTSM classes defined above, override the objectify _XO_ subclass for each
allclasses=inspect.getmembers(sys.modules[__name__],inspect.isclass)
XTSM_Classes=[tclass[1] for tclass in allclasses if (issubclass(getattr(sys.modules[__name__],tclass[0]),getattr(sys.modules[__name__],'XTSM_core')))]
for XTSM_Class in XTSM_Classes:
    setattr(gnosis.xml.objectify, "_XO_"+XTSM_Class.__name__, XTSM_Class)
del allclasses
# this ends module initialization 
