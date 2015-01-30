
import pdb
import numpy
import uuid
import file_locations
import ctypes

class DelayTrain:
    def __init__(self, channel_length_uint32, control_data):
        self.channel_length_uint32 = channel_length_uint32
        
        #pdb.set_trace()
        delay64ints = numpy.array(control_data).view(numpy.uint64)
        delay32ints = numpy.array(control_data).view(numpy.uint32)
        delay8ints = numpy.array(control_data).view(numpy.uint8)
        self.delay_time = numpy.empty(len(delay64ints),dtype=numpy.uint32)
        self.delay_sync = numpy.empty(len(delay64ints),dtype=numpy.uint8)
        #print 'len(delay64ints)', len(delay64ints)
        #print 'len(delay8ints)', len(delay8ints) / 8.0
        for d in range(0,len(delay64ints)):
            self.delay_time[d] = int(delay32ints[d*2 + 1])
            self.delay_sync[d] = delay8ints[d*8 + 0]
            #print ((delay32ints[d*2+1]),
            #       bin(delay8ints[8*d+0]))
        
        
class Board:
    def __init__(self):
        pass

class TimingString:
    def __init__(self, ts):
        '''
        Timing string is constructed inside class ParserOutput, function
        package_timingstrings
        '''
        print "in class, TimingString; def __init__"
        self.raw_timing_bytes = ts
        self.length = numpy.array(ts[0:8]).view(numpy.uint64)
        ts = ts[8:]
        self.num_timing_groups = int(ts[0])
        #self.timing_group_header = []
        #self.timing_group_control_data = []
        self.timing_groups = []
        headerLength = 80
        hptr = 1
        ptr = headerLength * self.num_timing_groups + 1
        for tg in range(0, self.num_timing_groups):
            tgh = GroupHeader(ts[hptr:hptr + headerLength])
            cd = GroupControlData(tgh, ts[ptr:ptr + int(tgh.length_uint64)])
            tg = TimingGroup(tgh, cd)
            self.timing_groups.append(tg)
            hptr += headerLength
            ptr += int(tgh.length_uint64)
            tgh.to_string() 
            
        #for tg in range(0, self.num_timing_groups):
        #    if self.timing_group_header[tg].group_name.strip() == 'RIO01/delaytrain':
        #        DelayTrain(self.timing_group_header[tg], self.timing_group_control_data[tg] )

class TimingGroup:
    def __init__(self, timing_group, control_data):
        self.timing_group = timing_group
        self.control_data = control_data
        
class GroupControlData:
    def __init__(self, group_header, control_data):
        #pdb.set_trace()
        self.control_data = control_data
        self.group_header = group_header
        #header for group data
        class Header:
            pass
        self.header = Header()
        h = self.header
        h.data_length_uint64 = numpy.array(control_data[0:8]).view(numpy.dtype('<u8'))[0]
        h.num_channels = int(numpy.array(control_data[8:9]).view(numpy.dtype('<u1'))[0])
        h.bytespervalue = int(numpy.array(control_data[9:10]).view(numpy.dtype('<u1'))[0])
        h.bytesperrepeat = int(numpy.array(control_data[10:11]).view(numpy.dtype('<u1'))[0])
        h.denseT_size_uint32 = numpy.array(control_data[11:15]).view(numpy.dtype('<u4'))[0]
        self.channels_control_data = control_data[15:]
        self.delay_train = None
        self.channels = []
        
        channel_length_uint32 = numpy.array(self.channels_control_data[0:4]).view(numpy.dtype('<u4'))[0]
        control_data = self.channels_control_data[4:]
        if self.group_header.group_name.strip() == 'RIO01/delaytrain':
            self.delay_train = DelayTrain(channel_length_uint32, control_data)
        
        else:
            for chan in range(h.num_channels):
                #pdb.set_trace()
                cd = ChannelControlData(h, channel_length_uint32, control_data)
                self.channels.append(cd)
                control_data = control_data[channel_length_uint32:]
                
        lib = ctypes.cdll.LoadLibrary(file_locations.file_locations['SCADCA_dll'][uuid.getnode()]) 
        
        pdb.set_trace()
        value_type = '<u' + str(h.bytespervalue)
        self.DCA_from_clibrary = numpy.empty((h.num_channels,h.denseT_size_uint32),dtype=numpy.dtype(value_type))
        lib.tstodca24.argtypes = [numpy.ctypeslib.ndpointer(dtype=numpy.dtype(value_type),
                                                      ndim=2,
                                                      flags='C_CONTIGUOUS')]
        lib.tstodca24(self.DCA_from_clibrary, dtype=numpy.dtype(value_type))


       
class GroupHeader:
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
        
        
        
class ChannelControlData:
    def __init__(self, header, channel_length_uint32, control_data): 
        num_pairs = channel_length_uint32 / (header.bytesperrepeat + header.bytespervalue)
        print num_pairs
        value_type = '<u' + str(header.bytespervalue)
        if header.bytesperrepeat > 0:
            repeat_type = '<u' + str(header.bytesperrepeat)
        else:
            repeat_type = None
        self.values = numpy.empty(num_pairs, dtype=numpy.dtype(value_type))
        if repeat_type != None:
            self.repeats = numpy.empty(num_pairs, dtype=numpy.dtype(repeat_type))
        #pdb.set_trace()
        pair8ints = numpy.array(control_data).view(numpy.uint8)
        ptr = 0
        for p in range(num_pairs):
            temp_v_arr = numpy.array(pair8ints[ptr:ptr + header.bytespervalue])
            numpy.append(self.values, temp_v_arr.view(numpy.dtype(value_type))[0])
            ptr = ptr + header.bytespervalue
            print self.values[p],
            if repeat_type != None:
                temp_r_arr = numpy.array(pair8ints[ptr:ptr + header.bytesperrepeat])
                numpy.append(self.repeats, temp_r_arr.view(numpy.dtype(repeat_type))[0])
                ptr = ptr + header.bytesperrepeat
                print self.repeats[p]
            print ''
        
        
        
class TimingDiagram:

    def print_diagram(self, xtsm_object):
        print "class TimingDiagram, func print_diagram"
        #pdb.set_trace()
        seq = xtsm_object.XTSM.getActiveSequence()
        cMap=seq.getOwnerXTSM().getDescendentsByType("ChannelMap")[0]
        #channelHeir=cMap.createTimingGroupHeirarchy()        
        #channelRes=cMap.findTimingGroupResolutions()
        #Parser out put node. Use TimingProffer
        #Control arrays hold what is actually coming out.
        seq.collectTimingProffers()
        edge_timings_0 = seq.TimingProffer.data['Edge']
        
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
                    
                    
            
        edge_timings = numpy.asarray([x for x in edge_timings_0 if not x[1] == -1])
        print "hi"
        #pdb.set_trace()
        edge_timings = edge_timings[numpy.lexsort((edge_timings[:, 1], edge_timings[:, 2]))]
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
            
        #pdb.set_trace()
        unique_group_channels = []
        for edge in edges:
            is_found = False
            for ugc in unique_group_channels:
                if edge.name == ugc.name:
                    is_found = True
            if not is_found:
                unique_group_channels.append(edge)
                

        
        #pdb.set_trace()
        unique_times = []
        for edge in edges:
            is_found = False
            for t in unique_times:
                if edge.time == t.time:
                    is_found = True
            if not is_found:
                unique_times.append(edge)        
               
        #pdb.set_trace() 
        from operator import itemgetter
        edge_timings_by_group = sorted(edge_timings, key=itemgetter(2))
        edge_timings_by_group_list = []
        for edge in edge_timings_by_group:
            edge_timings_by_group_list.append(edge.tolist())
        #print edge_timings
        for p in edge_timings_by_group_list: print p   
        
        #pdb.set_trace()
        #pdb.set_trace()
        print "Printing Diagram"
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
                    s = s + '|' + str('%8s' % str(current_edge.initial_value))
                    is_first = False
                    previous_edge.value = current_edge.initial_value
                    if previous_edge.value == 'None ':
                        previous_edge.value = 0
                if is_found:
                    if current_edge.value > previous_edge.value:
                        s += '^' + str('%8s' % str(current_edge.value))
                    else:
                        s += 'v' + str('%8s' % str(current_edge.value))
                    previous_edge = current_edge
                else:
                    s += '|' + '.'*8
            s = s + '|' + str('%8s' % str(current_edge.holding_value))
            print s             
                       
                       
        s = "Time (ms)".rjust(longest_name) + '|' + str('%8s' % str(" Initial"))
        for t in unique_times:
            s += '|' + str('%8s' % str(t.time))
        s = s + '|' + str('%8s' % str(" Holding"))
        print s
        
    
