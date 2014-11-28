import socket
import ctypes
import pdb

def bytes_to_integer(dataset, first_index, last_index):
    """
    Takes input of single bytes in the form of integers and returns a single integer.
    Example: 255, 2, 0, 0 --> 767
    Given a list of numbers, [x,y,z,a,...], the algorithm used is thus:
    new_integer = x * (256 ** 0) + y * (256 ** 1) + z * (256 ** 2) + a * (256 ** 3) + ...
    """
    byte_range = last_index - first_index + 1
    new_integer = 0
    for byte_number in range(byte_range):
        if dataset[(first_index + byte_number)] is not 0:   # Cuts down on runtime by not doing anything if a term is 0.
            new_integer += dataset[first_index + byte_number] * (256 ** byte_number)
    return new_integer

def sparse_to_dense_conversion(num_channels, num_updates, datalist):
    """
    Makes use of SCAtoDCA.dll to undergo sparse-to-dense conversions.
    """
    sparse_to_dense_convert = ctypes.CDLL('C:\\Users\\User\\Documents\\Visual Studio 2010\\Projects\\SCAtoDCA\\x64\\Release\\SCAtoDCA.dll')
    sdc = sparse_to_dense_convert
    """
    The following three lines are to make the functions be recognized as doubles instead of ints, which is the default.
    """
    sdc.tstodca44.restype = ctypes.c_double
    sdc.tstodca24.restype = ctypes.c_double
    sdc.tstodca14.restype = ctypes.c_double
    """
    The following details what the C functions are in C:
    double tstodca44(unsigned int *returnarray, unsigned char *inputarray)
    double tstodca24(unsigned short *returnarray, unsigned char *inputarray)
    double tstodca14(unsigned char *returnarray, unsigned char *inputarray)
    
    Relevant type conversions, listed as:
    C type --> ctype type --> Python type
    
    double --> c_double --> float
    unsigned int --> c_uint --> int/long
    unsigned short --> c_ushort --> int/long
    unsigned char --> c_ubyte --> int/long
    
    Uses of each function:
    tstodca44 : timing group channels (analog)
    """
    data_array = []
    cdataarray = ((ctypes.c_uint * num_updates) * num_channels)()
    # Create pointer for the empty data array
    array_pointer = ctypes.pointer(cdataarray)
    # Create 1D array (aka list) of timing group data. Then convert to C-type 1D array.
    cdatalist = []
    cdatalist = (ctypes.c_ubyte * len(datalist))(*datalist)  # Converts 1D array to C-type 1D array.
    # Create pointer for the input data list
    list_pointer = ctypes.pointer(cdatalist) 
    # Sparse-to-dense conversion function.
    sdc.tstodca44(array_pointer, list_pointer)
    # Convert newly filled 2D array back to python.
    for column in range(len(cdataarray)):
        row_values = []
        for row in range(len(cdataarray[column])):
            row_values.append(cdataarray[column][row])
        data_array.append(row_values)
    return data_array
    
def start_sequence():
    print 'Got here! (start_sequence())'

class AO_Emulator:
    def __init__(self):
        has_timingstring = False
        self.has_timingstring = has_timingstring
    
    def populate(self, timing_group):
        """
        Gets data from the timing_group's header.
        If sparse-to-dense conversion is required, sends body data to the sparse-dense converter to 
            expand value:repeat pairs in the timing group's body. This also creates a data array.
        Else, creates a data array. (Not included yet, because at this point, all data requires sparse-to-dense conversion.)
        If this timing group has the 'start_sequence_now' property as True, then it triggers the experiment simulation to run.
        """
        self.timing_group = timing_group
        timingstring = timing_group['timing_group_string']
        # Get data about the timing group from its header.
        timing_group_size = bytes_to_integer(timingstring, 0, 7)
        num_channels = timingstring[8]
        bytes_per_value = timingstring[9]
        bytes_per_repeat = timingstring[10]
        num_updates = bytes_to_integer(timingstring, 11, 14)
        body = timingstring[15:]
        # Store the gathered data in another dictionary and append to the timing group.
        group_info = {'timing_group_size':timing_group_size, 'num_channels':num_channels, 'bytes_per_value':bytes_per_value,
                       'bytes_per_repeat':bytes_per_repeat, 'updates':num_updates, 'body':body}
        timing_group.update(group_info)
        # Check whether the timing group requires sparse-to-dense conversion. IF so, send body data. Else, create data array from body.
        timingarray = []        
        if timing_group['sd_conversion']:
            # Must send number of channels, number of updates, and ENTIRE TIMING GROUP STRING, not just the body of the timing group.
            timingarray.append(sparse_to_dense_conversion(num_channels, num_updates, timingstring))
        else:
            pass
        if timing_group['start_sequence_now']:
            start_sequence()

class AI_Emulator:
    def __init__(self):
        has_timingstring = False
        self.has_timingstring = has_timingstring

    def populate(self, timing_group):
        self.timing_group = timing_group
        if timing_group['start_sequence_now']:
            start_sequence()

class DO_Emulator:
    def __init__(self):
        has_timingstring = False
        self.has_timingstring = has_timingstring
    
    def populate(self, timing_group):
        self.timing_group = timing_group
        if timing_group['start_sequence_now']:
            start_sequence()

class DI_Emulator:
    def __init__(self):
        has_timingstring = False
        self.has_timingstring = has_timingstring
    
    def populate(self, timing_group):
        self.timing_group = timing_group
        if timing_group['start_sequence_now']:
            start_sequence()

class FPGA_Emulator:
    def __init__(self):
        has_timingstring = False
        self.has_timingstring = has_timingstring
        
    def populate(self, timing_group):
        self.timing_group = timing_group
        if timing_group['start_sequence_now']:
            start_sequence()

class Hardware_Emulator:
    """
    Main Hardware Emulator.
    It takes in one datastream for one experiment run.
    This datastream is broken up into timing group, which are sent to board emulators.
    These board emulators further break up their data fragments, ultimately creating a 2D array
        of data similar to that which would be stored in RAM by the actual hardware.
    Upon sequence start, the boards update, outputting the simulated voltage that each board emulator
        would output on a channel.
    
    Actual hardware:
        1 digital output (DO)
        3 analog outputs (AO)
        0 digital input (DI)
        1 analog input (AI)        
        1 FPGA board (FPGA)
        
    Clocking set-up:
        FPGA board clocks DO board and AI board.
        DO board clocks all AO boards.
    """
    def __init__(self):
        # Initialize starting boards.
        self.initialize_emulators()
        # Gets initial data via python socket.
        self.get_data()
        # Assigns data to timing groups.
        self.fragment_data()
        # Assigns timing groups to emulators.
        self.populate_emulators()
    
    def initialize_emulators(self):
        """
        Creates emulators for each piece of actual hardware present.
        NOTE: If actual hardware changes, you must manually change the board number values below (eg. num_do).
        """
        do = []
        ao = []
        di = []
        ai = []
        fpga = []
        # Manually input following values based on actual hardware.
        num_do = 1        
        num_ao = 3
        num_di = 0
        num_ai = 1
        num_fpga = 1
        # Create an emulator for each piece of hardware entered above.
        for i in range(num_do):
            do.append(DO_Emulator())
        for i in range(num_ao):
            ao.append(AO_Emulator())
        for i in range(num_di):
            di.append(DI_Emulator())
        for i in range(num_ai):
            ai.append(AI_Emulator())
        for i in range(num_fpga):
            fpga.append(FPGA_Emulator())
        self.ao = ao
        self.do = do
        self.ai = ai
        self.di = di
        self.fpga = fpga
    
    def get_data(self):
        datastream = '2,  55,0,0,0,0,0,0,0, 1,0,0,0,0,0,0,0, 1, 1, 1, 255,0,0,0, 1, 1, 0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,  55,0,0,0,0,0,0,0, 2,0,0,0,0,0,0,0, 1, 2, 2, 42,0,0,0, 0, 1, 0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   54,0,0,0,0,0,0,0, 2, 4, 4, 5,0,0,0, 16,0,0,0, 200,0,0,0, 3,0,0,0, 125,0,0,0, 2,0,0,0, 16,0,0,0, 200,0,0,0, 4,0,0,0, 225,0,0,0, 1,0,0,0,   54,0,0,0,0,0,0,0,2,4,4,5,0,0,0,16,0,0,0,123,0,0,0,2,0,0,0,64,0,0,0,3,0,0,0,16,0,0,0,20,0,0,0,1,0,0,0,42,0,0,0,4,0,0,0'
        """
        Makes use of python's built-in socket library to create a simple listener.
        This is only meant to receive one packet of data per run. (Hence, I called this a "simple" listener.)
        """
        # The following works, but is commented out for easy-testing purposes.
        """
        datastream = ''

        running = True
        connector = None

        host = '127.0.0.1'
        port = '8083'
        maxClient = 999999999

        # Creates new socket. Do not mess with.
        connector = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        # Tells socket which url:port to listen to, along with how many connections (max) it can make.
        connector.bind ( ( str(host), int(port) ) )
        connector.listen ( int(maxClient) )

        while running:
            print ('Running on port ' + port + ' ... ')
            channel, details = connector.accept()

            if running:
                print ( 'New connection with: ' + str(details) )
                # Non-blocking = 0, blocking = 1.
                channel.setblocking(1)
                # recv = received data
                datastream = channel.recv(9000000)
            
                # The next three lines are for debugging purposes:
                #print ( 'host: ' + str(details[0]) )
                #print ( 'port: ' + str(details[1]) )
                #print data_string
            
                # Close after one run.
                channel.close()
                running = False
                connector.close()
        """
        # Creates 1D array of bytes from the datastream. Also strips away any extra spaces.
        datastream = [int(data.strip()) for data in datastream.split(',')]
        self.datastream = datastream

    def fragment_data(self):
        """
        The datastream will be fragmented in two ways: head vs body, and parts belonging to each timing group.
        Relevant data will be extracted from the header for each timing group, while the body will be broken up
        into smaller datastreams for each invididual timing group, as determined by header info.
        This will all be put into a list of timing groups.
        """
        # First byte contains the number of timing groups, which allows us to determine the size of the header.
        num_groups = int(self.datastream[0])
        header_size = (num_groups * 80) + 1
        # The header consists of everything in the datastream until the header_size is reached. Quantity is currently unused.
        header = self.datastream[:header_size]
        # The body is everything in the datastream after the header.
        body = self.datastream[header_size:]
        # A copy of the body, which will be fragmented into each timing stream.
        body_remaining = body
        timing_groups = []
        # Now we want to divide up the datastream into parts for each timing group.
        for i in range(0, num_groups):
            # Extracts data from the datastream header about each timing group and stores in a dictionary.
            timing_groups.append(self.timing_group_info(i))
            # Extracts data from the datastream body for each timing group, based on header info "timing_group_bytes".
            timing_group_string = body_remaining[:timing_groups[i]['timing_group_bytes']]
            # Add data for the timing group to its dictionary.
            timing_groups[i].update({'timing_group_string':timing_group_string})
            # Eliminate this timing group's data from remaining body, for use in next loop.
            body_remaining = body_remaining[timing_groups[i]['timing_group_bytes']:]
        self.header_size = header_size
        self.header = header
        self.body = body
        self.timing_groups = timing_groups
    
    def timing_group_info(self, group_number):
        """
        Extract timing group info from header and stores as key:value pairs.
        Meanings of each byte can be found at https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Python_parser_interface#TimingString_Structure
        or on the labview VI for the Rubidium Timing Experiment.
        Returns dictionary of such pairs for each timing group.
        """
        # Relevant data from header consists of 80 bytes for each timing group.
        relevant_data = self.datastream[((group_number * 80) + 1):(((group_number + 1) * 80) + 1)]
        # Insert a dummy in order to match up indeces with wiki/VI values.
        relevant_data.insert(0, 0)
        # Assign bytes to variables for data storage, based on wiki/VI values.
        timing_group_bytes = bytes_to_integer(relevant_data, 1, 8)
        timing_group_number = bytes_to_integer(relevant_data, 9, 16)
        device_type = relevant_data[17]
        timing_number = relevant_data[18]
        clock_source = relevant_data[19]
        clock_frequency = bytes_to_integer(relevant_data, 20, 23)
        start_sequence_now = bool(relevant_data[24])    # Since this is a simple True/False byte, it is simple to evaluate it now.
        undergo_sd_convert = bool(relevant_data[25])    # Since this is a simple True/False byte, it is simple to evaluate it now.
        #reserved = bytes_to_integer(relevant_data, 26, 32)
        timing_group_name = bytes_to_integer(relevant_data, 33, 56)
        timing_group_clock_name = bytes_to_integer(relevant_data, 57, 80)
        # All of the above data is gathered into one large dictionary for the group.
        header_info = {'timing_group_bytes':timing_group_bytes, 'timing_group_number':timing_group_number,
                       'device_type':device_type, 'timing_number':timing_number, 'clock_source':clock_source,
                       'clock_frequency':clock_frequency, 'start_sequence_now':start_sequence_now,
                       'sd_conversion':undergo_sd_convert, 'timing_group_name':timing_group_name,
                       'timing_group_clock_name':timing_group_clock_name}
        return header_info
        
    def populate_emulators(self):
        """
        Put each timing group into an available emulator, based on the timing group's device_type property.
        """
        counter = 0     # Counts number of groups which will start last.
        for group in self.timing_groups:
            if (counter > 1):
                print 'ERROR: 2 groups have the "start immediately" property as "yes" (aka byte #24 = 1).'
            # Assign the timing group with "start_sequence_now = True" last, if it is not last already.
            elif (group['start_sequence_now']) and (group is not self.timing_groups[-1]):  
                # Assigns timing group as last on the list.
                self.timing_groups.append(group)
                # Causes error report to user if this loop runs more than once. Aka, two timing groups have this property.
                counter += 1
            else:
                # Look at each group's "device_type" key to determine which type of emulator to put it in.
                device = group['device_type']
                group_assigned = False
                # Look at the available emulators of each type, check if they have a timing string already, and assign new timing group to first empty emulator of its type.
                if device == 0: # Digital output
                    for emulator in self.do:
                        if (not emulator.has_timingstring) and (not group_assigned):
                            # Send timing group to emulator.
                            emulator.populate(group)
                            # Stops the emulator from accepting any more timing groups.
                            emulator.has_timingstring = True
                            # Stops the timing group from being assigned to any other emulators.
                            group_assigned = True
                elif device == 1: # Analog output
                    for emulator in self.ao:
                        if (not emulator.has_timingstring) and (not group_assigned):
                            # Send timing group to emulator.
                            emulator.populate(group)
                            # Stops the emulator from accepting any more timing groups.
                            emulator.has_timingstring = True
                            # Stops the timing group from being assigned to any other emulators.
                            group_assigned = True
                elif device == 2: # Digital input
                    for emulator in self.di:
                        if (not emulator.has_timingstring) and (not group_assigned):
                            # Send timing group to emulator.
                            emulator.populate(group)
                            # Stops the emulator from accepting any more timing groups.
                            emulator.has_timingstring = True
                            # Stops the timing group from being assigned to any other emulators.
                            group_assigned = True
                elif device == 3: # Analog input
                    for emulator in self.ai:
                        if (not emulator.has_timingstring) and (not group_assigned):
                            # Send timing group to emulator.
                            emulator.populate(group)
                            # Stops the emulator from accepting any more timing groups.
                            emulator.has_timingstring = True
                            # Stops the timing group from being assigned to any other emulators.
                            group_assigned = True
                elif device == 4: # FPGA
                    for emulator in self.fpga:
                        if (not emulator.has_timingstring) and (not group_assigned):
                            # Send timing group to emulator.
                            emulator.populate(group)
                            # Stops the emulator from accepting any more timing groups.
                            emulator.has_timingstring = True
                            # Stops the timing group from being assigned to any other emulators.
                            group_assigned = True
                else:
                    print 'ERROR: ', device, ' is an unknown device type.'
                    group_assigned = True   # Technically incorrect, but this stops two error messages from firing for one problem.
                # Only occurs if the group satisfies one of the if or elif statements above, but is not assigned to an emulator.
                if not group_assigned:
                    print 'ERROR: Did not supply enough ', device, ' emulators.'
        pdb.set_trace()
        
HAL9000 = Hardware_Emulator()
