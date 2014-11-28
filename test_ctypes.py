# -*- coding: utf-8 -*-
"""
Created on Sat May 10 00:29:46 2014

@author: Nate
"""

import ctypes
#from numpy.ctypeslib import ndpointer
import numpy
from bitarray import bitarray
import time, pdb

VERBOSE=True
BENCHMARK=True
DEVELOP=False
PULSER=False

from numpy.ctypeslib import ndpointer
lib = ctypes.cdll.LoadLibrary("c:\\Users\\Nate\\documents\\visual studio 2010\\Projects\\testctype\\x64\\Release\\testctype.dll")
fun_repasuint8 = lib.repasuint8
fun_repasuint8.restype = None
fun_repasuint8.argtypes = [ndpointer(ctypes.c_uint32, flags="C_CONTIGUOUS"), ctypes.c_uint32,
                ndpointer(ctypes.c_uint32, flags="C_CONTIGUOUS"), ctypes.c_ubyte,
                ndpointer(ctypes.c_ubyte, flags="C_CONTIGUOUS"), ctypes.c_uint32]
fun_repasuint8dev = lib.repasuint8dev
fun_repasuint8dev.restype = None
fun_repasuint8dev.argtypes = [ndpointer(ctypes.c_uint32, flags="C_CONTIGUOUS"), ctypes.c_uint32,
                ndpointer(ctypes.c_uint32, flags="C_CONTIGUOUS"), ctypes.c_ubyte,
                ndpointer(ctypes.c_ubyte, flags="C_CONTIGUOUS"), ctypes.c_uint32]
fun_repasuint8pulse= lib.repasuint8pulse
fun_repasuint8pulse.restype = None
fun_repasuint8pulse.argtypes = [ndpointer(ctypes.c_uint32, flags="C_CONTIGUOUS"), ctypes.c_uint32,
                ndpointer(ctypes.c_uint32, flags="C_CONTIGUOUS"), ctypes.c_ubyte,
                ndpointer(ctypes.c_ubyte, flags="C_CONTIGUOUS"), ctypes.c_uint32]
fun_repasuint8pulsedev = lib.repasuint8pulsedev
fun_repasuint8pulsedev.restype = None
fun_repasuint8pulsedev.argtypes = [ndpointer(ctypes.c_uint32, flags="C_CONTIGUOUS"), ctypes.c_uint32,
                ndpointer(ctypes.c_uint32, flags="C_CONTIGUOUS"), ctypes.c_ubyte,
                ndpointer(ctypes.c_ubyte, flags="C_CONTIGUOUS"), ctypes.c_uint32]

def repasint(flipstring,PULSER=False,DEV=False):
    outdata = numpy.empty(numpy.unique(flipstring).shape[0]+1, dtype=numpy.uint8)
    ptrs = ((flipstring==0).nonzero())[0].astype(numpy.uint32)
    pdb.set_trace()
    if PULSER:
        if DEV: fun_repasuint8pulsedev(flipstring, flipstring.size, ptrs, 0B11111111, outdata,outdata.size+1)
        else: fun_repasuint8pulse(flipstring, flipstring.size, ptrs, 0B11111111, outdata,outdata.size+1)
        # reversed each byte in c-algorithm to match original algorithm's output - possible this could be removed later?
    else:
        if DEV: fun_repasuint8dev(flipstring, flipstring.size, ptrs, 0B11111111, outdata,outdata.size+1)
        else: fun_repasuint8(flipstring, flipstring.size, ptrs, 0B11111111, outdata,outdata.size+1)
        outdata[-1]=0
    return outdata[1:]

def OldRepresentAsInteger(channeltimes, PULSER=False):
            
    Nchan = 8
    Nbitout = 8  # number of bits in integer to use
    try:
        dtype = {0:numpy.uint8,8:numpy.uint8,16:numpy.uint16,32:numpy.uint32,64:numpy.uint64}[Nbitout] # data type for output
    except KeyError:
        pass
    ptrs = ((channeltimes==0).nonzero())[0].astype(numpy.uint32)
    # find the final resting places of the pointers
    fptrs = [ptr for ptr in ptrs[1:]]
    # add in end pointer
    fptrs.append(channeltimes.shape[0])
    fptrs = numpy.array(fptrs)
    # create a bit-array to represent all channel outputs
    bits = bitarray([1]*Nchan)
    # create arrays of output times and values for a single channel
    numtimes = len(numpy.unique(channeltimes))
    outvals = numpy.empty(numtimes,dtype=dtype)
    outtimes = numpy.empty(numtimes,dtype=numpy.uint64)
    outptr = 0  # a pointer to the first currently unwritten output element

    if PULSER:
        optrs=ptrs
        while not (ptrs == fptrs).all():
            active = ptrs<fptrs # identify active pointers
            time = min(channeltimes[ptrs[active.nonzero()]]) # current time smallest value for "active" pointers
            #LRJ 10-30-2013 hitstrue disables unused channels
            lineindex=0
            hitstrue=[]
            for ct in channeltimes[ptrs]:
                    if (ptrs[lineindex]-optrs[lineindex])==2 and ct==time:#self.channels.values()[lineindex].intedges.shape[1] == 2 and ct==time:
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
    else:            
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
        bits = bitarray([0]*Nchan)
        outvals[-1] = numpy.fromstring((bits[::-1].tobytes()[::-1]), dtype = dtype)            
    return outvals

def generate_testdata(scale):
    a=numpy.array([0,100*scale,0,100*scale,0,100*scale], dtype=numpy.uint32)
    a=numpy.append(a,numpy.arange(0,scale, dtype=numpy.uint32)*10)
    a=numpy.append(a,numpy.array([100*scale], dtype=numpy.uint32))    
    a=numpy.append(a,numpy.arange(0,scale, dtype=numpy.uint32)*15)
    a=numpy.append(a,numpy.array([100*scale], dtype=numpy.uint32))
    a=numpy.append(a,numpy.array([0,100*scale,0,100*scale,0,100*scale], dtype=numpy.uint32))
    return a

a=generate_testdata(100)

t0=time.time()
outdata=repasint(a,PULSER=PULSER)
print time.time()-t0
if VERBOSE:
    strout=""
    for line in range(0,8):
        for elm in outdata:
            strout += str((int(elm) >> line) % 2)
        strout += "\n"
    print strout


if DEVELOP:
    t0=time.time()
    outdata3=repasint(a,DEV=True, PULSER=PULSER)
    print time.time()-t0
    if VERBOSE:
        strout=""
        for line in range(0,8):
            for elm in outdata3:
                strout += str((int(elm) >> line) % 2)
            strout += "\n"
        print strout
    print "equality check: ", (outdata3==outdata).all()
del lib

if BENCHMARK:
    t0=time.time()
    outdata2=OldRepresentAsInteger(a, PULSER=PULSER)
    print time.time()-t0
    if VERBOSE:
        strout=""
        for line in range(0,8):
            for elm in outdata2:
                strout += str((int(elm) >> line) % 2)
            strout += "\n"
        print strout
    print "equality check: ", (outdata2==outdata).all()