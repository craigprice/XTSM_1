import pylab
import numpy
import scipy.optimize

def gaussian(height, center_x, center_y, width_x, width_y):
    """Returns a gaussian function with the given parameters"""
    width_x = float(width_x)
    width_y = float(width_y)
    return lambda x,y: height*numpy.exp(
                -(((center_x-x)/width_x)**2+((center_y-y)/width_y)**2)/2)
       
def moments(data):
    """Returns (height, x, y, width_x, width_y)
    the gaussian parameters of a 2D distribution by calculating its
    moments """
    total = data.sum()
    X, Y = numpy.indices(data.shape)
    x = (X*data).sum()/total
    y = (Y*data).sum()/total
    col = data[:, int(y)]
    width_x = numpy.sqrt(abs((numpy.arange(col.size)-y)**2*col).sum()/col.sum())
    row = data[int(x), :]
    width_y = numpy.sqrt(abs((numpy.arange(row.size)-x)**2*row).sum()/row.sum())
    height = data.max()
    return height, x, y, width_x, width_y
   
def fitgaussian(data):
    """Returns (height, x, y, width_x, width_y)
    the gaussian parameters of a 2D distribution found by a fit"""
    params = moments(data)
    errorfunction = lambda p: numpy.ravel(gaussian(*p)(*numpy.indices(data.shape)) -
                            data)
    p, success = scipy.optimize.leastsq(errorfunction, params)
    return p
    
'''
# Create the gaussian data
Xin, Yin = numpy.mgrid[0:201, 0:201]
data = gaussian(3, 100, 100, 20, 40)(Xin, Yin) + numpy.random.random(Xin.shape)

pylab.matshow(data, cmap=pylab.cm.gist_earth_r)

params = fitgaussian(data)
fit = gaussian(*params)
   
pylab.contour(fit(*numpy.indices(data.shape)), cmap=pylab.cm.copper)
ax = pylab.gca()
(height, x, y, width_x, width_y) = params


t = pylab.text(0.95, 0.05, """
x : %.1f
y : %.1f
width_x : %.1f
width_y : %.1f""" %(x, y, width_x, width_y),
fontsize=16, horizontalalignment='right',
verticalalignment='bottom', transform=ax.transAxes)
print t.text()

pylab.show()
'''

'''

import zipfile
import msgpack
#mfile = '45dc6b61-7052-11e4-b42a-0010187736b5.zip'
#path = 'C:\\wamp\\www\\raw_buffers\\DBFS\\2014-11-19\\'
mfile = '51ef3c11-71c0-11e4-b1b5-0010187736b5.zip'
path = 'C:\\wamp\\www\\raw_buffers\\DBFS\\2014-11-21\\'
zf = zipfile.ZipFile( path + mfile , 'r')
info = zf.infolist()
print info
print info[0].filename
msgp_data = zf.read(info[0].filename)
payload = msgpack.unpackb(msgp_data)
data = msgpack.unpackb(payload['packed_data'])['data']
print data[1][1]

import tables
h5file = tables.open_file("C:\\wamp\\www\\WebSocketServer\\edf2f6ca-53da-4118-84fd-fc1c30d4ab29.h5", "r")
table = h5file.root.data_group.ccd_data
data = [x['ccd_array'] if x['short_256_description'] == 'flouresence' for x in table.iterrows()]

'''

import os
'''
self.today = datetime.datetime.fromtimestamp(self.init_time).strftime('%Y-%m-%d')
os.makedirs('C:\\wamp\\www\\archie\\')
for i = enumerate():
'''

import datetime
import datetime

start = datetime.datetime.strptime("2014-11-13", '%Y-%m-%d')
end = datetime.datetime.strptime("2014-11-26", "%Y-%m-%d")
date_generated = [start + datetime.timedelta(days=x) for x in range(0, (end-start).days)]

for date in date_generated:
    os.makedirs("C:\\wamp\\www\\psu_data\\"+date.strftime("%Y-%m-%d")+'\\raw_data') 
    os.makedirs("C:\\wamp\\www\\psu_data\\"+date.strftime("%Y-%m-%d")+'\\xtsm') 
    os.makedirs("C:\\wamp\\www\\psu_data\\"+date.strftime("%Y-%m-%d")+'\\hdf5_heap') 