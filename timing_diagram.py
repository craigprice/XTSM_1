
import pdb
import numpy


class Delay_Train_Emulator:
    def __init__(self, header, control_data):
        self.timing_string_header = header
        self.timing_string_control_data = control_data
        #header for group data
        self.data_length_uint64 = numpy.array(control_data[0:8]).view(numpy.dtype('<u8'))[0]
        self.num_channels = numpy.array(control_data[8:9]).view(numpy.dtype('<u1'))[0]
        self.bytespervalue = numpy.array(control_data[9:10]).view(numpy.dtype('<u1'))[0]
        self.bytesperrepeat = numpy.array(control_data[10:11]).view(numpy.dtype('<u1'))[0]
        self.denseT_size_uint32 = numpy.array(control_data[11:15]).view(numpy.dtype('<u4'))[0]
        control_data = control_data[15:]
        #header for channel data
        self.channel_length_uint32 = numpy.array(control_data[0:4]).view(numpy.dtype('<u4'))[0]
        control_data = control_data[4:]
        #the first bit high in the sync grop is the clock for the digital board
        
        #delay64ints = []
        #for i in range(0,len(control_data),8):
        #    delay64ints.append(numpy.array(control_data[i:i+8]).view(numpy.uint64)[0]) #SPEED UP TARGET CP 2014-12-19
            
        
        delay64ints = numpy.array(control_data).view(numpy.uint64)
        delay32ints = numpy.array(control_data).view(numpy.uint32)
        delay8ints = numpy.array(control_data).view(numpy.uint8)
        self.delay_time = numpy.empty(len(delay64ints),dtype=numpy.uint32)
        self.delay_sync = numpy.empty(len(delay64ints),dtype=numpy.uint8)
        for d in range(0,len(delay64ints)):
            self.delay_time[d] = delay32ints[d*2]
            self.delay_sync[d] = delay8ints[4 + d*8]
            #print (0b00010000 & self.delay_sync[d])
            print bin(self.delay_sync[d])
        
        count = 0
        for d in range(0,len(delay64ints)):
            if 0b10000000 & self.delay_sync[d] == 0b10000000:
                count = count + 1
        print count
        pdb.set_trace()
        
        '''
        self.tsbytes=self.numalledges*(self.bytesperrepeat+self.bytespervalue)+4*self.numchan+15  ### last two terms account for header and segment headers
        self.timingstring=numpy.ones(self.tsbytes,numpy.uint8)  # will hold timingstring
        # create the timingstring header
        # First part of the header is the length of the control string for the entire timing group.
        self.timingstring[0:8]=numpy.asarray([self.tsbytes], dtype='<u8').view('u1')
        self.timingstring[8:15]=numpy.append(
                                  numpy.asarray([self.numchan,self.bytespervalue,self.bytesperrepeat], dtype='<u1').view('u1'),
                                  numpy.asarray([self.denseT.size], dtype='<u4').view('u1'))
        self.tsptr=15  # a pointer to the current position for writing data into the timingstring
        
        ###
        
        # first a header denoting this channel's length in bytes as 4bytes, LSB leading
        self.parent.timingstring[self.parent.tsptr:(self.parent.tsptr+4)]=numpy.asarray([int(length*(self.parent.bytesperrepeat+self.parent.bytespervalue))], dtype='<u4').view('u1')
        self.parent.tsptr+=4
        '''

class TimingString:
    def __init__(self, ts):
        print "in class, TimingString; def __init__"
        self.raw_timing_bytes = ts
        self.length = numpy.array(ts[0:8]).view(numpy.uint64)
        ts = ts[8:]
        self.num_timing_groups = int(ts[0])
        self.timing_group_header = []
        self.timing_group_control_data = []
        headerLength = 80
        hptr = 1
        ptr = headerLength * self.num_timing_groups + 1
        for tg in range(0, self.num_timing_groups):
            self.timing_group_header.append(TimingStringHeader(ts[hptr:hptr + headerLength]))
            control_array_length = int(self.timing_group_header[tg].length_uint64)
            self.timing_group_control_data.append(ts[ptr:ptr + control_array_length])
            hptr += headerLength
            ptr += control_array_length
            self.timing_group_header[tg].to_string() 
            
        for tg in range(0, self.num_timing_groups):
            print self.timing_group_header[tg].group_name
            if self.timing_group_header[tg].group_name.strip() == 'RIO01/delaytrain':
                Delay_Train_Emulator(self.timing_group_header[tg], self.timing_group_control_data[tg] )
        
        
class TimingStringHeader:
    def __init__(self, header):
        self.raw_header = header
        self.length_uint64 = numpy.array(header[0:8]).view(numpy.uint64)[0]
        self.group_number_uint64 = numpy.array(header[8:16]).view(numpy.uint64)[0]
        type_hardware = {0:'DigitalOutput',1:'AnalogOutput',2:'DigitalInput',3:'AnalogInput',4:'DelayTrain'}
        self.type_hardware = type_hardware[int(header[16])]
        self.clock_resolution_uint32 = numpy.array(header[19:23]).view(numpy.uint32)[0]
        self.is_trigger = bool(header[23])
        self.isSparse = bool(header[24])
        self.version = int(header[25])
        self.group_name = str(header[32:56].decode('utf-8'))
        self.clock_channel_name = str(header[56:80].decode('utf-8'))
        
        
    def to_string(self):
        print "raw_header", self.raw_header
        print "length_uint64", self.length_uint64
        print "group_number_uint64", self.group_number_uint64
        print "type_hardware", self.type_hardware
        print "clock_resolution_uint32", self.clock_resolution_uint32
        print "is_trigger", self.is_trigger
        print "isSparse", self.isSparse
        print "version", self.version
        print "group_name", self.group_name
        print "clock_channel_name", self.clock_channel_name
        
        
        '''
        tl=numpy.asarray(totalLength, dtype=numpy.uint64).view('u1')
        '''
        '''
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
                self.timing_string_ints = ts
                tl=numpy.asarray(totalLength, dtype=numpy.uint64).view('u1')
                ts=numpy.concatenate((tl, ts))
            except OverflowError: return ""  # Overflow error means length of ts is greater than 8 byte integer.
        except AttributeError: return ""
        return ts
        '''
        
        '''
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
class TimingDiagram:

    def print_diagram(self, xtsm_object):
        pdb.set_trace()
        seq = xtsm_object.XTSM.getActiveSequence()
        cMap=seq.getOwnerXTSM().getDescendentsByType("ChannelMap")[0]
        #channelHeir=cMap.createTimingGroupHeirarchy()        
        #channelRes=cMap.findTimingGroupResolutions()
        #Parser out put node. Use TimingProffer
        #Control arrays hold what is actually coming out.
        seq.collectTimingProffers()
        edge_timings = seq.TimingProffer.data['Edge']
        
        class Edge:
            def __init__(self, timing_group, channel_number, time, value, tag,
                         name, initial_value, holding_value):
                self.timing_group = timing_group
                self.channel_number = channel_number
                self.time = time
                self.value = value
                self.tag = tag
                self.max = 0
                self.min = 0
                self.name = name
                self.holding_value = holding_value
                self.initial_value = initial_value
                
            def is_same(self,edge):
                if ((self.timing_group == edge.timing_group) and
                (self.channel_number == edge.channel_number) and
                (self.time == edge.time) and
                (self.value == edge.value) and
                (self.tag == edge.tag)):
                    return True
                else:
                    return False
            
        edges = []
        longest_name = 0
        for edge in edge_timings:
            for channel in cMap.Channel:
                tgroup = int(channel.TimingGroup.PCDATA)
                tgroupIndex = int(channel.TimingGroupIndex.PCDATA)
                if tgroup == int(edge[0]) and tgroupIndex == int(edge[1]):
                    name = channel.ChannelName.PCDATA
                    init_val = ''
                    hold_val = ''
                    try:
                        init_val = channel.InitialValue.PCDATA
                    except AttributeError:
                        init_val = 'None '
                    try:
                        hold_val = channel.HoldingValue.PCDATA
                    except AttributeError:
                        hold_val = 'None '
                    if len(name) > longest_name:
                        longest_name = len(name)
                    edges.append(Edge(edge[0],edge[1],edge[2],edge[3],edge[4],
                                      name, init_val,hold_val))
                    #pdb.set_trace()
            
        unique_group_channels = []
        for edge in edges:
            is_found = False
            for ugc in unique_group_channels:
                if edge.is_same(ugc):
                    is_found = True
            if not is_found:
                unique_group_channels.append(edge)
                
                
        from operator import itemgetter
        edge_timings_by_group = sorted(edge_timings, key=itemgetter(2))
        edge_timings_by_group_list = []
        for edge in edge_timings_by_group:
            edge_timings_by_group_list.append(edge.tolist())
        #print edge_timings
        for p in edge_timings_by_group_list: print p   
        
        unique_times = []
        for edge in edges:
            is_found = False
            for t in unique_times:
                if edge.time == t.time:
                    is_found = True
            if not is_found:
                unique_times.append(edge)        
        
        
        #pdb.set_trace()
        for ugc in unique_group_channels:
            s = ugc.name.rjust(longest_name)
            current_edge = edges[0]
            previous_edge = edges[0]
            is_first = True
            for t in unique_times:
                is_found = False
                for edge in edges:
                    if edge.timing_group == ugc.timing_group and edge.channel_number == ugc.channel_number and edge.time == t.time:
                        is_found = True
                        current_edge = edge
                if is_first:
                    s = s + '|' + str('%7s' % str(current_edge.initial_value))
                    is_first = False
                    previous_edge.value = current_edge.initial_value
                    if previous_edge.value == 'None ':
                        previous_edge.value = 0
                if is_found:
                    if current_edge.value > previous_edge.value:
                        s += '^' + str('%7s' % str(current_edge.value))
                    else:
                        s += 'v' + str('%7s' % str(current_edge.value))
                    previous_edge = current_edge
                else:
                    s += '|' + '.'*7
            s = s + '|' + str('%7s' % str(current_edge.holding_value))
            print s             
                       
                       
        s = "Time (ms)".rjust(longest_name) + '|' + str('%7s' % str("Initial"))
        for t in unique_times:
            s += '|' + str('%7s' % str(t.time))
        s = s + '|' + str('%7s' % str("Holding"))
        print s
        
    
