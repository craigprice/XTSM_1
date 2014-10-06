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