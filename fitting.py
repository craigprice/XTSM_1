# -*- coding: utf-8 -*-
"""
Created on Thu Feb 05 18:00:15 2015

@author: User
"""



import pdb


import numpy

import matplotlib.pyplot as plt
import matplotlib.cm as cm

import os
import scipy
import scipy.ndimage
import pdb
import scipy.stats
import time

from scipy.optimize import leastsq

fname = 'C:\\wamp\\www\\tempdata'
#numpy.save(fname,numpy.asarray(arr))

data = numpy.load(fname + '.npy')[0]
data2 = data[30:-130,80:-80]

    
# define objective function: returns the array to be minimized

class GaussianFit2D:
    """
    2D Gaussian 
    
    SPEEDUP: take the log on the data once outside the fitting algorithm.
    Make better initial guesses.
    """
    def __init__(self, data, initial_guess={}, region_x=(0,512), region_y=(0,512), use_jac=True):
        
        init_params = {}
        init_params.update({'offset':0})
        init_params.update({'theta':0})
        
        init_params.update(initial_guess)
        
        if not (init_params.has_key('x0') or init_params.has_key('y0')):
            (x0,y0) = scipy.ndimage.measurements.center_of_mass(data2)
            init_params.update({'x0':x0})
            init_params.update({'y0':y0})
            
        if not init_params.has_key('sigma_x'):
            self.sumx = numpy.sum(data, axis=1)
            sigma_x = scipy.stats.mstats.moment(self.sumx, moment=2)
            init_params.update({'sigma_x':sigma_x})
        
        if not init_params.has_key('sigma_y'):
            self.sumy = numpy.sum(data, axis=0)
            sigma_y = scipy.stats.mstats.moment(self.sumy, moment=2) 
            init_params.update({'sigma_y':sigma_y})      
        
        if not init_params.has_key('amplitude'):
            init_params.update({'amplitude':numpy.amax(data)})
            
        self.init_params = init_params
        self.x = numpy.outer(numpy.ones(data.shape[0]),numpy.arange(data.shape[1]))
        self.y = numpy.outer(numpy.arange(data.shape[0]),numpy.ones(data.shape[1]))
        self.data = data
        self.ones = numpy.ones(data.shape)
        self.time = 0
        self.old_params = numpy.asarray(numpy.ones(7))
    
    def model(self, params, x, y, data):
        
        amplitude = params[0]
        sigma_x = params[1]
        sigma_y = params[2]
        offset = params[3]
        theta = params[4]
        x0 = params[5]
        y0 = params[6]
            
        self.rotx = (self.x*numpy.cos(theta) - self.y*numpy.sin(theta) - x0)
        self.roty = (self.x*numpy.sin(theta) + self.y*numpy.cos(theta) - y0)
        
        self.rotx2 = self.rotx*self.rotx #numpy.power(self.roty, 2.0) is slow
        self.roty2 = self.roty*self.roty
        
        self.xside = self.rotx2 / (-2.0*sigma_x*sigma_x)#numpy.power(self.roty, 2.0) is slow
        self.yside = self.roty2 / (-2.0*sigma_y*sigma_y)
        
        self.exponential = numpy.exp(self.xside + self.yside)
        
        self.main = amplitude * self.exponential
        
        #print 'params','\n', params
        #print 'self.old_params','\n', self.old_params,'\n'
        #self.old_params = params Error with assignment - don't know why
        self.old_params[0] = params[0]
        self.old_params[1] = params[1]
        self.old_params[2] = params[2]
        self.old_params[3] = params[3]
        self.old_params[4] = params[4]
        self.old_params[5] = params[5]
        self.old_params[6] = params[6]
        
        return self.main + offset
    

    def derivatives(self, params, x, y, data):
        
        t0=time.time()
        
        amplitude = params[0]
        sigma_x = params[1]
        sigma_y = params[2]
        offset = params[3]
        theta = params[4]
        x0 = params[5]
        y0 = params[6]
        
        if not (self.old_params == params).all():#Cannot use "self" values calculated from model()
            print "needing to call model"
            self.model(params, x, y, data)
        
            
        self.prex = self.main*(-2.0) / (-2.0*sigma_x*sigma_x)
        self.prey = self.main*(-2.0) / (-2.0*sigma_y*sigma_y)
    
        dfda = self.main/amplitude
        dfdsx = self.prex/sigma_x * self.rotx2
        dfdsy = self.prey/sigma_y * self.roty2
        dfdoff = self.ones
        temp_x = ((-1.0)*self.x*numpy.sin(theta) - self.y*numpy.cos(theta))
        temp_y = (self.x*numpy.cos(theta) + (-1.0)*self.y*numpy.sin(theta))
        dfdthe = (-1.0)*self.prex*self.rotx*temp_x + (-1.0)*self.prey*self.roty*temp_y
        dfdx0 = self.prex * self.rotx
        dfdy0 = self.prey * self.roty
        
        
        r = [dfda.ravel(),dfdsx.ravel(),dfdsy.ravel(),dfdoff.ravel(),
                dfdthe.ravel(),dfdx0.ravel(),dfdy0.ravel()]
                
        print 'derivatives', time.time()-t0
        self.time = self.time + time.time()-t0
        
        return r
                
    def residual_func(self, params, x, y, data):
        t0=time.time()
        r = self.model(params, x, y, data).ravel() - self.data.ravel()
        print 'residual', time.time()-t0
        self.time = self.time + time.time()-t0
        return r
        
    def fit(self):
        
        para = (
            self.init_params['amplitude'],
            self.init_params['sigma_x'],
            self.init_params['sigma_y'],
            self.init_params['offset'],
            self.init_params['theta'],
            self.init_params['x0'],
            self.init_params['y0']
            )
            
        t0=time.time()
        result = leastsq(self.residual_func, para,
                         args=(self.x, self.y, self.data),
                            xtol=0.3, ftol=0.3, maxfev=30,
                         #Dfun=self.derivatives, col_deriv=True,
                         full_output=True)
        print 'least square time', time.time() - t0, 's'
        print 'python time',self.time
        #print result
        
        
        fit_params = result[0]
        fit_amplitude = fit_params[0]
        fit_sigma_x = fit_params[1]
        fit_sigma_y = fit_params[2]
        fit_offset = fit_params[3]
        fit_theta = fit_params[4]
        fit_x0 = fit_params[5]
        fit_y0 = fit_params[6]
        
        residuals = numpy.reshape(self.residual_func(fit_params, self.x, self.y, self.data),(512-160,512-160))
        fit = data2 + residuals
        
        
        plt.imshow(data2,cmap = cm.Greys_r)
        plt.plot(self.sumx)
        plt.plot(self.sumy)
        plt.plot(numpy.sum(fit, axis=0))
        plt.plot(numpy.sum(fit, axis=1))
        plt.imshow(numpy.hstack((data2, fit, residuals)),cmap = cm.Greys_r)
        plt.show()
    


gf = GaussianFit2D(data2)
gf.fit()

