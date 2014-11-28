import httplib
import ctypes
import itertools
import numpy as np
np.set_printoptions(suppress=True,precision=3, threshold='nan')  # sets default printing options for numpy
import pdb

def bytes_to_integer(dataset, first_index = 0, last_index = -1):
    """
    Takes input array (dataset) and converts to a single integer. Assumes dataset is LSB.
    """
    if last_index == -1:
        last_index = len(dataset) - 1
    integers = []
    for byte_number in range(first_index, last_index + 1):
        try:
            # Convert each number to binary and append to list of numbers.
            integers.append('{0:08b}'.format(dataset[byte_number]))
        except ValueError:
            # Sometimes the bytearray casts a number as a letter. Try recasting it as a number.
            byte = ord(dataset[byte_number])
            integers.append('{0:08b}'.format(byte))
    # Reverse the list order to account for little-endianness.
    integers.reverse()
    # Join list numbers together to form one long binary number, then read into base 10.
    new_integer = ''.join(integers)
    new_integer = int(new_integer, 2)
    return new_integer

def bytes_to_string(dataset, first_index, last_index):
    """
    Takes input of integers, converts to character and joins them together.
    Also removes white space.
    """
    message_parts = []
    for byte_number in range(first_index, last_index + 1):
        # Converts integer to character.
        char = chr(dataset[byte_number])
        # Add new character to message parts.
        message_parts.append(char)
    # Join message parts together.
    message = ''.join(message_parts)
    # Remove whitespace.
    message = message.replace(' ', '')
    return message

def count_repeats(bytes_per_value, bytes_per_repeat, num_channels, body):
    """
    Counts the number of repeats per channel. Returns the largest such number for troubleshooting purposes.
    (Ideally, all of the channels should have the same number of repeats.)
    The largest value is sent back, because it is the larger number of repeats which can potentially crash the program.
    """
    bytes_per_pair = bytes_per_value + bytes_per_repeat
    largest_repeats_per_channel = 0
    body_remaining = body
    for i in range(num_channels):
        repeats_per_channel = 0
        len_channel = 0
        len_channel = bytes_to_integer(body_remaining, 0, 3)
        # Assign channel data to channel. Channel data consists of value:repeat pairs, as specified by the len_channel. Technically also includes the bytes to specify channel length, but we already used that.
        channel = body_remaining[4:(len_channel + 4)]
        # Eliminate channel data from the remainder of the body.
        body_remaining = body_remaining[len_channel + 4:]
        # Cycles through data in the channel, starting with the first repeat value and increasing by a value:repeat pair each cycle.
        for repeat_start in range(bytes_per_value, len(channel), bytes_per_pair):
            # Adds value of repeat to the number of repeats (so far) for the channel.
            repeats_per_channel += bytes_to_integer(channel, repeat_start, (repeat_start + bytes_per_repeat - 1))
        if repeats_per_channel > largest_repeats_per_channel:
            # If there is a discrepancy between repeat values for different channels, and it is not the first loop, then say so.
            if largest_repeats_per_channel is not 0:
                print 'ERROR: Two channels have different total numbers of repeats.'
            largest_repeats_per_channel = repeats_per_channel
    return largest_repeats_per_channel
    
def sparse_to_dense_conversion(bytes_per_value, num_channels, num_updates, datalist):
    """
    Makes use of SCAtoDCA.dll to undergo sparse-to-dense conversions.
    """
    sparse_to_dense_convert = ctypes.CDLL('C:\\wamp\\www\\MetaViewer\\SCAtoDCA\\SCAtoDCA.dll')
    sdc = sparse_to_dense_convert
    """
    The following three lines are to make the functions be recognized as doubles instead of ints, which is the default in python.
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
    If bytes per value == 1, use tstodca14.
    If bytes per value == 2, use tstodca14.
    If bytes per value == 4, use tstodca14.
    """
    data_array = []
    # Create 1D array (aka list) of timing group data. Then convert to C-type 1D array.
    cdatalist = []
    cdatalist = (ctypes.c_ubyte * len(datalist))(*datalist)  # Converts 1D array to C-type 1D array.
    # Create pointer for the input data list
    list_pointer = ctypes.pointer(cdatalist)
    if bytes_per_value == 1:
        cdataarray = ((ctypes.c_ubyte * num_updates) * num_channels)()
        # Create pointer for the empty data array
        array_pointer = ctypes.pointer(cdataarray)
        # Sparse-to-dense conversion function.
        sdc.tstodca14(array_pointer, list_pointer)
    elif bytes_per_value == 2:
        cdataarray = ((ctypes.c_ushort * num_updates) * num_channels)()
        # Create pointer for the empty data array
        array_pointer = ctypes.pointer(cdataarray)
        # Sparse-to-dense conversion function.
        sdc.tstodca24(array_pointer, list_pointer)
    elif bytes_per_value == 4:
        cdataarray = ((ctypes.c_uint * num_updates) * num_channels)()
        # Create pointer for the empty data array
        array_pointer = ctypes.pointer(cdataarray)
        # Sparse-to-dense conversion function.
        sdc.tstodca44(array_pointer, list_pointer)
    else:
        print 'ERROR: Bytes per value must be 1, 2, or 4.'
    # Convert newly filled 2D array back to python.
    for column in range(len(cdataarray)):
        row_values = []
        for row in range(len(cdataarray[column])):
            row_values.append(cdataarray[column][row])
        data_array.append(row_values)
    return data_array

def populate_group(timing_emulator):
    """
    Gets data from the timing_group's header.
    If sparse-to-dense conversion is required, sends body data to the sparse-dense converter to 
        expand value:repeat pairs in the timing group's body. This also creates a data array.
    Else, creates a data array. (Not included yet, because at this point, all data requires sparse-to-dense conversion.)
    """
    timing_group = timing_emulator.timing_group
    timingarray = timing_emulator.timingarray
    timingstring = timing_group['timing_group_string']
    # Get data about the timing group from its header.
    timing_group_length = bytes_to_integer(timingstring, 0, 7)
    num_channels = timingstring[8]
    bytes_per_value = timingstring[9]
    bytes_per_repeat = timingstring[10]
    num_updates = bytes_to_integer(timingstring, 11, 14)
    body = timingstring[15:]
    # Store the gathered data in another dictionary and append to the timing group.
    group_info = {'timing_group_length':timing_group_length, 'num_channels':num_channels, 'bytes_per_value':bytes_per_value,
                   'bytes_per_repeat':bytes_per_repeat, 'updates':num_updates, 'body':body}
    timing_group.update(group_info)
    if bytes_per_repeat != 0:
        # Check that the total number of repeats (per channel) == number of updates before trying to create data array.
        repeats_per_channel = count_repeats(bytes_per_value, bytes_per_repeat, num_channels, body)      
        if repeats_per_channel == num_updates:
            # Check whether the timing group requires sparse-to-dense conversion. IF so, send body data. Else, create data array from body.
            if timing_group['sd_conversion']:
                # Must send number of channels, number of updates, and ENTIRE TIMING GROUP STRING, not just the body of the timing group.
                timingarray.append(sparse_to_dense_conversion(bytes_per_value, num_channels, num_updates, timingstring))
                # The append gave us a 2D array inside a 1D array. Now we eliminate the unwanted outer 1D array.
                timingarray = np.array(timingarray[0], dtype = 'float')
            else: # Since the body format is the same, just with "1" as all of its repeat values, there's no reason not to send the array along as if it required sparse-to-dense conversion.
                # Must send number of channels, number of updates, and ENTIRE TIMING GROUP STRING, not just the body of the timing group.
                timingarray.append(sparse_to_dense_conversion(bytes_per_value, num_channels, num_updates, timingstring))
                # The append gave us a 2D array inside a 1D array. Now we eliminate the unwanted outer 1D array.
                timingarray = np.array(timingarray[0], dtype = 'float')
            timing_emulator.timingarray = timingarray  # Need to manually set these values again after the numpy conversion.
        else:
            print 'The total input repeats is:', repeats_per_channel, ', while the listed number of updates is:', num_updates, '.'
            pdb.set_trace()
    else:  # Double-checking the number of repeats doesn't make sense if there are none.
        timingarray = []
        channel_length = bytes_to_integer(body, 0, 3) + 4  # All channels are the same length if they have no repeat values.
        for i in range(num_channels):
            channelarray = []
            for j in range(i * channel_length + 4, (i + 1) * channel_length, bytes_per_value):
                value = bytes_to_integer(body, j, (j + bytes_per_value - 1))
                channelarray.append(value)
            timingarray.append(channelarray)
        timing_emulator.timingarray = np.array(timingarray, dtype = 'float')

def convert_values(bytes_per_value, timingarray, value_range):
    """
    Values are scaled and offset in order to fill the range of bit values available when being sent from the server to the hardware.
    Hence, to retrieve the desired values, the current values must be scaled and offset in reverse.
    
    NOTE: This function requires numpy array as the format of the timingarray.
    Returned array is numpy array.
    """
    offset = 2.**(8*bytes_per_value - 1)
    scale = ((2.**(8*bytes_per_value - 1)) - 1)/(value_range/2)
    timingarray -= offset
    timingarray /= scale
    return timingarray

def expand_channels(timingarray, num_channels):
    """
    Takes a digital timing array of 1 channel and turns it into a digital array of N channels,
    where N == num_channels.
    
    Returned array is numpy array.
    """
    new_array = []
    new_array.append(timingarray)
    new_array = np.uint8(new_array)
    expanded_array = np.unpackbits(new_array, axis = 0)
    return expanded_array

def clock(emulator):
    """
    Returns list of channel values for a given timing group.
    """
    channel_values = emulator.timingarray[:,0]
    emulator.timingarray = np.delete(emulator.timingarray, 0, 1)  # Remove 0th column from array.
    return channel_values

class AO_Emulator:
    def __init__(self):
        # Indicates that the Emulator initially has no timingstring assigned to it.
        has_timingstring = False
        self.has_timingstring = has_timingstring
    
    def populate(self, timing_group, hardware_emulator):
        """
        Finds the header info from the group timingstring and creates a timingarray based on the timingstring's body.
        Then converts those values to be within the proper range, as set by value_range.
        Finally, determines what clocks this group, and assigns it to an object that is "hardwired" to that clock.
        """
        self.timing_group = timing_group
        timingarray = []
        self.timingarray = timingarray
        populate_group(self)
        # Unscale and onset values.
        value_range = 20 # Manually input scale. This one goes from -10volts to 10volts.
        self.timingarray = convert_values(self.timing_group['bytes_per_value'], self.timingarray, value_range)
        # Create default channel values of 0, for use before the emulator is first clocked.
        self.channel_values = np.zeros(self.timing_group['num_channels'])
        # Assign to clocking group based on the timing group's name.
        if timing_group['timing_group_clock_name'] == '/PXI1Slot2/PFI1':
            hardware_emulator.analog1 = self
        elif timing_group['timing_group_clock_name'] == '/PXI1Slot2/PFI2':
            hardware_emulator.analog2 = self
        elif timing_group['timing_group_clock_name'] == '/PXI1Slot2/PFI3':
            hardware_emulator.analog3 = self
        elif timing_group['timing_group_clock_name'] == '/PXI1Slot2/PXI_Trig5':
            hardware_emulator.fineao = self
        else:
            print 'ERROR: Unknown timing group name.'
        pdb.set_trace()

class AI_Emulator:
    def __init__(self):
        # Indicates that the Emulator initially has no timingstring assigned to it.
        has_timingstring = False
        self.has_timingstring = has_timingstring
    
    def populate(self, timing_group, hardware_emulator):
        """
        Finds the header info from the group timingstring and creates a timingarray based on the timingstring's body.
        Then converts those values to be within the proper range, as set by value_range.
        Finally, determines what clocks this group, and assigns it to an object that is "hardwired" to that clock.
        
        NOTE: This is simply a copy of the DO Emulator, as we are not currently using any analog inputs. Hence, this should be redone once we do.
        """
        print 'WARNING: Analog Input string detected. This emulator is not currently equipped to handle analog inputs correctly. You have been warned.'
        self.timing_group = timing_group
        timingarray = []
        self.timingarray = timingarray
        populate_group(self)
        # Unscale and onset values.
        value_range = 20 # Manually input scale. This one goes from -10volts to 10volts.
        self.timingarray = convert_values(self.timing_group['bytes_per_value'], self.timingarray, value_range)

class DO_Emulator:
    def __init__(self):
        # Indicates that the Emulator initially has no timingstring assigned to it.
        has_timingstring = False
        self.has_timingstring = has_timingstring
    
    def populate(self, timing_group, hardware_emulator):
        """
        Finds the header info from the group timingstring and creates a timingarray based on the timingstring's body.
        Then converts those values to be within the proper range, as set by value_range.
        Also creates a group of default channel values.
        Finally, determines what clocks this group, and assigns it to an object that is "hardwired" to that clock.
        """
        self.timing_group = timing_group
        timingarray = []
        self.timingarray = timingarray
        populate_group(self)
        if timing_group['timing_group_clock_name'] == '/PXI1Slot2/PXI_Trig7':
            exp_num_channels = 32
            self.expand_channels(exp_num_channels)
            self.channel_values = np.zeros(self.timing_group['num_channels'])
            hardware_emulator.digital1 = self
        pdb.set_trace()
    
    def expand_channels(self, num_channels):
        """
        Expands a single channel to num_channels channels.
        It is assumed that the final channels are digital channels. (Ie. Their values are 0's and 1's.)
        """
        channel_array = np.array(self.timingarray[0], dtype = 'uint' + str(num_channels))
        num_updates = self.timing_group['updates']
        timingarray = np.empty(shape = [num_channels, num_updates], dtype = 'bool')
        binary_format = '{0:0' + str(num_channels) + 'b}'
        for i in range(num_updates):
            val_as_binary = (binary_format.format(channel_array[i]))[::-1]
            val_as_binarylist = np.array([int(x) for x in str(val_as_binary)])
            timingarray[:,i] = val_as_binarylist
        self.timingarray = timingarray
            
    def cycle(self, fpga):
        ####################################REDO###################################
        """
        Since the DO board currently clocks all of the AO boards, check if the channels assigned to each AO emulator are rising from 0 to 1.
        If so, clock that board.  Always clocks itself. Returns values for itself and all AO emulators.
        
        The previous cycle's data for this emulator is stored here, while the previous cycle's data for each AO board is stored there.
        
        AO-clocking portion: Channel 0 goes to the timing group clocked by PFI1, ch1 to PFI2, ch2 to PFI3. Groups have been hardwired to analog1, analog2, and analog3 based on their clocking names.
        """
        hardware_emulator = fpga.hardware_emulator
        # Self-clocking portion.
        digital_values = clock(self)
        # Check if previous values exist. If not, this is the first run, so create some.
        try:
            self.previous_values
        except AttributeError:
            self.previous_values = [0, 0, 0]  # Only create enough for value-checking.
        # Clock each AO emulator if the corresponding digital channel is on a rise. Else, channel values remain the same.
        if digital_values[0] > self.previous_values[0]:
            hardware_emulator.analog1.channel_values = clock(hardware_emulator.analog1)
        if digital_values[1] > self.previous_values[1]:
            hardware_emulator.analog2.channel_values = clock(hardware_emulator.analog2)
        if digital_values[2] > self.previous_values[2]:
            hardware_emulator.analog3.channel_values = clock(hardware_emulator.analog3)
        # Join together all the output values, starting with the DO emulator, followed by the AO emulators, and return them.
        output_values = []
        output_values.append(digital_values)
        # Get values for all analog emulators, if they exist.
        try:
            output_values.append(hardware_emulator.analog1.channel_values)
        except AttributeError:
            pass
        try:
            output_values.append(hardware_emulator.analog2.channel_values)
        except AttributeError:
            pass
        try:            
            output_values.append(hardware_emulator.analog3.channel_values)
        except AttributeError:
            pass
        output_values = np.array(output_values)
        # Set new digital values as previous values for the next run.
        self.previous_values = digital_values

        return output_values

class DI_Emulator:
    def __init__(self):
        # Indicates that the Emulator initially has no timingstring assigned to it.
        has_timingstring = False
        self.has_timingstring = has_timingstring
    
    def populate(self, timing_group):
        """
        Finds the header info from the group timingstring and creates a timingarray based on the timingstring's body.
        Then converts those values to be within the proper range, as set by value_range.
        Also creates a group of default channel values.
        Finally, determines what clocks this group, and assigns it to an object that is "hardwired" to that clock.
        
        NOTE: This is simply a copy of the DO Emulator, as we are not currently using any digital inputs. Hence, this should be redone once we do.
        """
        print 'WARNING: Digital Input string detected. This emulator is not currently equipped to handle digital inputs correctly. You have been warned.'
        self.timing_group = timing_group
        timingarray = []
        self.timingarray = timingarray
        populate_group(self)
        # Unscale and onset values.
        value_range = 20 # Manually input scale. This one goes from -10volts to 10volts.
        self.timingarray = convert_values(self.timing_group['bytes_per_value'], self.timingarray, value_range)

class FPGA_Emulator:
    def __init__(self):
        # Indicates that the Emulator initially has no timingstring assigned to it.
        has_timingstring = False
        self.has_timingstring = has_timingstring
        
    def populate(self, timing_group):
        """
        Classifies incoming data by what type it is (eg. delay train, sync commands, etc.)
        Finds the header info from the group timingstring and creates a timingarray based on the timingstring's body.
        Then converts those values to be within the proper range, as set by value_range.
        Also creates a group of default channel values.
        Finally, determines what clocks this group, and assigns it to an object that is "hardwired" to that clock.
        """
        self.timing_group = timing_group
        timingarray = []
        self.timingarray = timingarray
        # Assign to delay or sync based on the timing group's name.
        self.create_delaytrain()
        pdb.set_trace()

    def create_delaytrain(self):
        """
        Used only for delay trains. Gets header info like a normal timing group, but it does not undergo
        sparse-to-dense conversions or repeat checks like other timing groups.
        Instead, it creates a delay train from the body.
        """
        timingstring = self.timing_group['timing_group_string']
        # Get data about the timing group from its header.
        timing_group_length = bytes_to_integer(timingstring, 0, 7)
        num_channels = timingstring[8]
        bytes_per_value = timingstring[9]
        bytes_per_repeat = timingstring[10]
        num_updates = bytes_to_integer(timingstring, 11, 14)
        body = timingstring[15:]
        # Store the gathered data in another dictionary and append to the timing group.
        group_info = {'timing_group_length':timing_group_length, 'num_channels':num_channels, 'bytes_per_value':bytes_per_value,
                       'bytes_per_repeat':bytes_per_repeat, 'updates':num_updates, 'body':body}
        self.timing_group.update(group_info)
        # Create delay train from body.
        delaystring_length = bytes_to_integer(body, 0, 3)
        delaystring = body[4:]
        syncarray = []
        dtrain = []
        # Every bytes_per_repeat bytes, group the bytes to form an integer number of delays until the next pulse.
        for start_index in range(0, delaystring_length, bytes_per_repeat):
            syncarray.append(delaystring[start_index])
            dtrain.append(bytes_to_integer(delaystring, (start_index + 4), start_index + (bytes_per_repeat - 1)))
        self.syncarray = expand_channels(syncarray, 8)
        self.delaytrain = dtrain

    def run_sequence(self, hardware_emulator):
        """
        Runs the timing sequence.
        
        Current hardware clocking setup:
        Delay Train
        - Sync commands
        -- DO board
        --- AO boards
        - Async commands (unused)
        - Crosspoint switch
        - Etc.
        
        Current format of output:
        Time: <time>
        Timing Group Name: <timinggroupname>
        Channel: <value>
        Channel: <value>
        ...
        Timing Group Name: <timinggroup2name>
        ...
        
        End Time is manually chosen as 50 seconds.
        """
        self.hardware_emulator = hardware_emulator
        elapsed_time = 0    # Seconds
        run_time = 50   # Seconds
        # Records the time whenever the system updates.
        update_times = []
        # Gets added to the output_array after each clock pulse, aka 'unit_time'.
        output_array = []
        # The delay train's inverted clock frequency serves as our basic unit of time.
        unit_time = 1.0/self.timing_group['clock_frequency']  # Seconds
        # Set the first delay counter.
        delay_counter = self.delaytrain.pop(0)
        # Every unit time, clock the FPGA emulator. If the FPGA emulator is not on a delay, return output values.
        for elapsed_time in itertools.count(0, unit_time):
            if delay_counter == 0:  # Send out pulses.
                # Add this time as an update time.
                update_times.append(elapsed_time*1000)
                # Send out a pulse on sync commands and table the response.
                output_array.append(self.clock_sync())
                # Send out a pulse on async commands and table the response.
                #output_array.append(self.clock_async())
                # Remove first value of delay train and set as new counter.
                try:
                    delay_counter = self.delaytrain.pop(0)
                except:  # Stop loop if there are no more delays to get.
                    break
            else:  # Delay.
                delay_counter -= 1
            # End the sequence if the elapsed time is greater than the experiment's run time.
            if elapsed_time >= (run_time):
                break
        # Turn the update times into a 1D numpy array.
        numpy_updates = np.array(update_times, dtype = 'float')
        # Turn the output values into a 2D array.
        numpy_output = np.array(output_array)
        # Transpose output array so that rows = channels, columns = times(, and value = channel voltage at a given time).
        pdb.set_trace()        
        
    def clock_sync(self):
        """
        Sends out a "pulse" on each channel if the channel's value is a 1 (aka 'on').
        
        Current hardware setup:
        Channel 0 --> DO board 'PXI1Slot2/port0:3' (hardware_emulator.digital1)
        Channel 1 --> Nothing
        Channel 2 --> Nothing
        Channel 3 --> Nothing
        Channel 4 --> Nothing
        Channel 5 --> Nothing
        Channel 6 --> Nothing
        Channel 7 --> Nothing
        
        Return is in the form: DO, AO, DI, AI
        Given the specific setup, this means the return is: DO, AO, AO, AO
        """
        channel_values = []
        # Get a set of sync commands.
        sync_values = self.syncarray[:,0]
        self.syncarray = np.delete(self.syncarray, 0, 1)  # Remove 0th column from array.
        # Analyze those commands. Note that all channels can send commands simultaneously (hence the name "synchronous commands".
        if sync_values[0] == 1:
            channel_values.append(self.hardware_emulator.digital1.cycle(self))
        if sync_values[1] == 1:
            print 'ERROR: Nothing is set for sync command 1 yet.'
        if sync_values[2] == 1:
            channel_values.append(clock(self.hardware_emulator.fineao))
        if sync_values[3] == 1:
            print 'ERROR: Nothing is set for sync command 3 yet.'
        if sync_values[4] == 1:
            print 'ERROR: Nothing is set for sync command 4 yet.'
        if sync_values[5] == 1:
            print 'ERROR: Nothing is set for sync command 5 yet.'
        if sync_values[6] == 1:
            print 'ERROR: Nothing is set for sync command 6 yet.'
        if sync_values[7] == 1:
            print 'ERROR: Nothing is set for sync command 7 yet.'
        return channel_values

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
        # Run experiment sequence.
        self.fpga[0].run_sequence(self)
    
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
        num_ao = 4
        num_di = 0
        num_ai = 1
        num_fpga = 1
        # Create an emulator for each piece of hardware entered above. This is used to store timing groups and limit the timing groups to the amount that physically exists.
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
        # Create an "hardwired" representation of each emulator to be clocked by FPGA board (directly or indirectly).
        analog1 = []
        analog2 = []
        analog3 = []
        fineao = []
        digital1 = []
        self.ao = ao
        self.do = do
        self.ai = ai
        self.di = di
        self.fpga = fpga
        self.analog1 = analog1
        self.analog2 = analog2
        self.analog3 = analog3
        self.fineao = fineao
        self.digital1 = digital1
    
    def get_data(self):
        """
        Makes use of the httplib to send a POST request to the python server.
        Data received is in byte form, Little-Endian.
        """
        #pdb.set_trace()
        # Assemble your boundary and transfer data.
        boundary = '--aardvark'
        transferdata = []
        transferdata.append('--' + boundary + '\n\rContent-Disposition: form-data; name="IDLSocket_ResponseFunction"\n\r\n\r' + 'compile_active_xtsm' + '\n\r--' + boundary + '--\n\r')
        transferdata.append('--' + boundary + '\n\rContent-Disposition: form-data; name="terminator"\n\r\n\r' + 'die' + '\n\r--' + boundary + '--\n\r')
        transferdata = ''.join(transferdata)
        # Set up an HTTP connection.
        connection = httplib.HTTPConnection("127.0.0.1", 8083)
        connection.connect()
        connection.putrequest('POST', '127.0.0.1:8083')
        # Declare HTTP headers
        headers = {}
        headers['Content-Type'] = 'multipart/form-data; boundary=' + boundary
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.110 Safari/537.36'
        headers['Accept-Language'] = 'en-US,en;q=0.8'
        headers['Accept'] = '*/*'
        headers['Connection'] = 'keep-alive'
        # Python doesn't automatically generate a content length, so find the length of your transfer data.
        net_length = len(transferdata)
        headers['Content-Length'] = net_length
        # Send all headers over the open connection.
        for i in headers:
            connection.putheader(i, headers[i])
        connection.endheaders()
        # Send request. 
        connection.send(transferdata)
        # Get response and print results.
        response = connection.getresponse()
        response.status
        response.reason
        datastream = response.read()
        
        connection.close()
        
        # Split up datastream into a list of elements and convert to alphanumeric characters if it isn't already one.
        datalist = []
        for elem in datastream:
            datalist.append(ord(elem))
        datalist_length = datalist[:8]
        datalist = datalist[8:]
        self.datalist = datalist
        self.datalist_length = datalist_length
        pdb.set_trace()

    def fragment_data(self):
        """
        The datalist will be fragmented in two ways: head vs body, and parts belonging to each timing group.
        Relevant data will be extracted from the header for each timing group, while the body will be broken up
        into smaller datastreams for each invididual timing group, as determined by header info.
        This will all be put into a list of timing groups.
        """
        # First byte contains the number of timing groups, which allows us to determine the size of the header.
        num_groups = self.datalist[0]
        header_size = (num_groups * 80) + 1
        # The header consists of everything in the datastream until the header_size is reached. Quantity is currently unused.
        header = self.datalist[:header_size]
        # The body is everything in the datastream after the header.
        body = self.datalist[header_size:]
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
        relevant_data = self.datalist[((group_number * 80) + 1):(((group_number + 1) * 80) + 1)]
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
        version = relevant_data[26]
        #reserved = bytes_to_integer(relevant_data, 27, 32)
        timing_group_name = bytes_to_string(relevant_data, 33, 56)
        timing_group_clock_name = bytes_to_string(relevant_data, 57, 80)
        # All of the above data is gathered into one large dictionary for the group.
        header_info = {'timing_group_bytes':timing_group_bytes, 'timing_group_number':timing_group_number,
                       'device_type':device_type, 'timing_number':timing_number, 'clock_source':clock_source,
                       'clock_frequency':clock_frequency, 'start_sequence_now':start_sequence_now,
                       'sd_conversion':undergo_sd_convert, 'version':version, 
                       'timing_group_name':timing_group_name, 'timing_group_clock_name':timing_group_clock_name}
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
                name = group['timing_group_name']
                group_assigned = False
                # Look at the available emulators of each type, check if they have a timing string already, and assign new timing group to first empty emulator of its type.
                if device == 0: # Digital output
                    for emulator in self.do:
                        if (not emulator.has_timingstring) and (not group_assigned):
                            # Send timing group to emulator.
                            emulator.populate(group, self)
                            # Stops the emulator from accepting any more timing groups.
                            emulator.has_timingstring = True
                            # Stops the timing group from being assigned to any other emulators.
                            group_assigned = True
                elif device == 1: # Analog output
                    for emulator in self.ao:
                        if (not emulator.has_timingstring) and (not group_assigned):
                            # Send timing group to emulator.
                            emulator.populate(group, self)
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
                elif device == 4: # FPGA delay train.
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
        
HAL9000 = Hardware_Emulator()