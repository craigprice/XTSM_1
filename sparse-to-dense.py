import ctypes
import pdb

sd_convert = ctypes.CDLL('C:\\Users\\User\\Documents\\Visual Studio 2010\\Projects\\SCAtoDCA\\x64\\Release\\SCAtoDCA.dll')
sd = sd_convert
"""
The following three lines are to make the functions be recognized as doubles instead of ints, which is the default.
"""
sd.tstodca44.restype = ctypes.c_double
sd.tstodca24.restype = ctypes.c_double
sd.tstodca14.restype = ctypes.c_double
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
datastream = '54,0,0,0,0,0,0,0,2,4,4,5,0,0,0,16,0,0,0,200,0,0,0,3,0,0,0,125,0,0,0,2,0,0,0,16,0,0,0,210,0,0,0,4,0,0,0,225,0,0,0,1,0,0,0'
# Create empty C-type 2D array for sparse-to-dense conversion to populate.
num_channels = 2
num_updates = 5
dataarray = []
cdataarray = ((ctypes.c_uint * num_updates) * num_channels)()
# Create pointer for the empty data array
array_pointer = ctypes.pointer(cdataarray)
# Create 1D array (aka list) of timing group data. Then convert to C-type 1D array.
datalist = []
cdatalist = []
for data in datastream.split(','):
    datalist.append(int(data))
    cdatalist = (ctypes.c_ubyte * len(datalist))(*datalist)  # Converts 1D array to C-type 1D array.
# Create pointer for the input data list
list_pointer = ctypes.pointer(cdatalist) 
# Sparse-to-dense conversion function.
sd.tstodca44(array_pointer, list_pointer)
# Convert newly filled 2D array back to python.
for column in range(len(cdataarray)):
    row_values = []
    for row in range(len(cdataarray[column])):
        row_values.append(cdataarray[column][row])
    dataarray.append(row_values)
print dataarray
pdb.set_trace()
