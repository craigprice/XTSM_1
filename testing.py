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
'''


#compDecomp( compObj1, "../python.xml", "python.xml.gz" )
#print "source", os.stat("../python.xml").st_size/1024, "k"
#print "dest", os.stat("python.xml.gz").st_size/1024, "k"

# -*- coding: utf-8 -*-
"""
This example demonstrates many of the 2D plotting capabilities
in pyqtgraph. All of the plots may be panned/scaled by dragging with 
the left/right mouse buttons. Right click on any plot to show a context menu.
"""
'''
#import initExample ## Add path to library (just for examples; you do not need this)

import numpy as np
frame1 = np.asarray(np.random.rand(500,500).tolist())
frame2 = np.asarray(np.random.rand(500,500).tolist())
from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg

#QtGui.QApplication.setGraphicsSystem('raster')
app = QtGui.QApplication([])
#mw = QtGui.QMainWindow()
#mw.resize(800,800)

win = pg.GraphicsWindow(title="Basic plotting examples")
win.resize(1000,600)
win.setWindowTitle('pyqtgraph example: Plotting')

# Enable antialiasing for prettier plots
pg.setConfigOptions(antialias=True)



p5 = win.addPlot(title="Scatter plot, axis labels, log scale")
x = np.random.normal(size=1000) * 1e-5
y = x*1000 + 0.005 * np.random.normal(size=1000)
y -= y.min()-1.0
mask = x > 1e-15
x = x[mask]
y = y[mask]
p5.plot(x, y, pen=None, symbol='t', symbolPen=None, symbolSize=10, symbolBrush=(100, 100, 255, 50))
p5.setLabel('left', "Y Axis", units='A')
p5.setLabel('bottom', "Y Axis", units='s')
p5.setLogMode(x=True, y=False)

p5_2 = win.addPlot(title="Scatter plot, axis labels, log scale")
p5_2.plot(x, y, pen=None, symbol='t', symbolPen=None, symbolSize=10, symbolBrush=(100, 100, 255, 50))
p5_2.setLabel('left', "Y Axis", units='A')
p5_2.setLabel('bottom', "Y Axis", units='s')
p5_2.setLogMode(x=True, y=False)

## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
'''

# -*- coding: utf-8 -*-
"""
Demonstrates use of GLScatterPlotItem with rapidly-updating plots.

"""
# -*- coding: utf-8 -*-
"""
This example demonstrates the use of ImageView, which is a high-level widget for 
displaying and analyzing 2D and 3D data. ImageView provides:

  1. A zoomable region (ViewBox) for displaying the image
  2. A combination histogram and gradient editor (HistogramLUTItem) for
     controlling the visual appearance of the image
  3. A timeline for selecting the currently displayed frame (for 3D data only).
  4. Tools for very basic analysis of image data (see ROI and Norm buttons)

"""
## Add path to library (just for examples; you do not need this)
#import initExample

import numpy as np
import scipy
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import sys
pix = 512
frame1 = np.asarray(np.random.rand(pix,pix).tolist())
frame2 = np.asarray(np.random.rand(pix,pix).tolist())

def UpdateWhileRec():
    # Note, j should be initialised to 0 in the record function now
    global stack, andor, img, n, j, ishape 


    if andor.n_images_acquired > j:    
        # Data saving    <-- this part (and the whole while-loop) works OK
        i, j = andor.new_images_index
        stack[i - 1:j] = andor.images16(i, j, ishape, 1, n)

        # Image updating <-- this should now work
        img.setImage(stack[j - 1], autoLevels=False)

    if j < n:
        QTimer.singleShot(0, UpdateWhileRec)
    else:
        liveview()   # After recording, it goes back to liveview mode

app = QtGui.QApplication([])
win = QtGui.QMainWindow()
win.resize(800,800)
imv = pg.ImageView()
win.setCentralWidget(imv)
win.show()
img = np.random.normal(size=(pix, pix)) * 20 + 100
img = frame1
img = img[np.newaxis,:,:]
data = np.asarray([frame1,frame2])
imv.setImage(data)

if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
    QtGui.QApplication.instance().exec_()
    


## Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
