# -*- coding: utf-8 -*-
"""
Created on Wed Dec 24 14:42:21 2014

@author: User
"""
import hdf5_liveheap

heap = hdf5_liveheap.glab_liveheap({"element_structure":[512,512],
                                    "filename":"test_file",
                                    "typecode":numpy.dtype("uint16")})#numpy.uint16 will not work