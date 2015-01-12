# -*- coding: utf-8 -*-
"""
Created on Fri Dec 26 18:00:39 2014

@author: Gemelke_Lab
"""

pass


import hdf5_liveheap
import numpy

e=numpy.random.rand(20,20,20) # generate 20 random matrices
for i in range(20): # the first ten of the following pushes will be heaved to disk, the last ten will stay in ram stack
    e[i,0,0]=121+i  # set top-left element to same as shotnumber will be when pushed, starting shotnumber will be 121


g=hdf5_liveheap.glab_liveheap(options={"element_structure":[20,20],"sizeof":10, "typecode":numpy.float}) # creates a stack of 20x20 float arrays, ten of which will be held in ram at any time
g.attach_datastore() # attaches a datastore with a randomly generated name
for i in range(e.shape[0]):
    g.push(e[i].squeeze(),121+i,0) # push it into the heap
test1=g[[140,128,139,125,126]] # retrieves this list of shotnumbers, non-sequential and split ram/disk

ds = hdf5_liveheap.glab_datastore()
handle = ds.get_handle('ccdimage',e[0])
handle2 = ds.get_handle('ccdimage',e[0])
sn = numpy.random.random_integers(1000*1000*1000)
rn = numpy.random.random_integers(1000*1000*1000)
handle.append(e[1], sn, rn)
handle.table.flush()
print (e[1]==handle.table.read()[0][2]).all()
print sn==handle2.table.read()[0][0]
print rn==handle2.table.read()[0][1]
print (e[1]==handle2.table.read()[0][2]).all()

des = numpy.empty(1,dtype=[
        ("shotnumber",numpy.int64),
        ("repnumber",numpy.int64),
        ('ccdimage',numpy.float64, (20, 20))
        ])