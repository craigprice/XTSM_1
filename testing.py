# -*- coding: utf-8 -*-
"""
Created on Mon Oct 06 09:23:00 2014

@author: Gemelke_Lab
"""

'''This works
import msgpack
f = open('c:/wamp/www/raw_buffers/DBFS/2014-10-06/temp15.msgp','ab')
msg = {'1':7,'3':5,'23451':3,'345':3453}
m = msgpack.packb(msg, use_bin_type=True)
f.write(m)
f.close()
f = open('c:/wamp/www/raw_buffers/DBFS/2014-10-06/temp15.msgp','rb')
um = msgpack.unpackb(m, encoding='utf-8')
print um
'''
'''
import msgpack
f = open('c:/wamp/www/raw_buffers/DBFS/2014-10-06/temp16.msgp','ab')
msg = {'1':7,'3':5,'23451':3,'345':3453}
m = msgpack.packb(msg, use_bin_type=True)
f.write(m)
f.close()
f = open('c:/wamp/www/raw_buffers/DBFS/2014-10-06/temp16.msgp','rb')
unpacker = msgpack.Unpacker(f,use_list=False, encoding='utf-8')
#um = msgpack.unpackb(m, encoding='utf-8')
print unpacker
'''


'''
print unpacker.read_map_header()
key = unpacker.unpackb()
print key
key = unpacker.unpackb()
print key
key = unpacker.unpackb()
print key
key = unpacker.unpackb()
print key
'''


import zlib
import msgpack
import time
import InfiniteFileStream
import msgpack_numpy
msgpack_numpy.patch()#This patch actually changes the behavior of "msgpack"
#specifically, it changes how, "encoding='utf-8'" functions when unpacking

#stream = InfiniteFileStream.FileStream({'file_root_selector':'xtsm_feed'})

#file = 'C:\wamp\www\raw_buffers\DBFS\2014-10-09\f2da7991-501f-11e4-91bf-0010187736b5.msgp'

#databomb = {'data':[[4,4,4,4],[4,357,357,573]]}
#messagepack = msgpack.packb(databomb, use_bin_type=True)
#msgpack.packb(to_disk, use_bin_type=True)
to_disk = {'id': str(5),
           'time_packed': str(time.time()),
                      'len_of_data': str(len('messagepack')),
                      'packed_databomb':' messagepack' }
#encoder = zlib.compressobj()
#data = encoder.compress('to_disk')
#data = data + encoder.flush()
#stream.write(data, keep_stream_open=False) 
#encoder = zlib.compressobj()
#data = encoder.compress('azfsgSF')
#data = data + encoder.flush()
#stream.write(data, keep_stream_open=False) 
#location = stream.location
#stream.__flush__()

#data = data + encoder.compress(" of ")
#data = data + encoder.flush()
#data = data + encoder.compress("brian")
#data = data + encoder.flush()

#print stream.location
#f = open(stream.location,'rb')
#data = f.read()
#print data
#print repr(data)
#print repr(zlib.decompress(data))


'''
import zlib
encoder = zlib.compressobj()
data = encoder.compress("life")
data = data + encoder.compress(" of ")
data = data + encoder.compress("brian")
data = data + encoder.flush()
print repr(data)
print repr(zlib.decompress(data))
'''

"""Compress a file using a compressor object."""
import zlib, bz2, os, cStringIO

'''
source= file( srcName, "r" )
dest= file( dstName, "w" )
block= source.read( 2048 )
while block:
    cBlock= compObj.compress( block )
    dest.write(cBlock)
    block= source.read( 2048 )
cBlock= compObj.flush()
dest.write( cBlock )
source.close()
dest.close()
'''
bytestream = msgpack.packb({'to_disk':3}, use_bin_type=True)
filename = 'C:\\wamp\\www\\raw_buffers\\DBFS\\2014-10-09\\test'+str(time.time())+'.txt'
f = open(filename,'ab')
c = zlib.compressobj()
cBlock = c.compress( bytestream )
f.write(cBlock)
cBlock = c.compress( bytestream )
f.write(cBlock)
cBlock = c.flush()
f.write(cBlock)
f.close()


f = open(filename,'rb')
c= zlib.decompressobj()
cBlock= c.decompress(f.read() )
print cBlock
output = cStringIO.StringIO(cBlock)
unpacker = msgpack.Unpacker(output,use_list=False)
print unpacker.next()
print cBlock 
print unpacker.next()



#compDecomp( compObj1, "../python.xml", "python.xml.gz" )
#print "source", os.stat("../python.xml").st_size/1024, "k"
#print "dest", os.stat("python.xml.gz").st_size/1024, "k"


