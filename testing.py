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
