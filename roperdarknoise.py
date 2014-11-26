# -*- coding: utf-8 -*-
"""
Created on Mon Sep 29 15:31:26 2014

@author: Gemelke_Lab
"""

import pickle
import numpy as np
import matplotlib.pyplot as plt
import pdb
#10 image for 100 ms exposure time at 0 C with Roper CCD, dark noise (CCD blocked by cap)
dark1=open('C:\\wamp\\www\\raw_buffers\\DBFS\\2014-09-29\\databomb_DB939d0240-480e-11e4-83af-0010187736b5_at_time_1412018817.28.txt')
dark2=open('C:\\wamp\\www\\raw_buffers\\DBFS\\2014-09-29\\databomb_DB94ce2f40-480e-11e4-904b-0010187736b5_at_time_1412018819.27.txt')
dark3=open('C:\\wamp\\www\\raw_buffers\\DBFS\\2014-09-29\\databomb_DB9b5ca6c0-480e-11e4-845c-0010187736b5_at_time_1412018830.27.txt')
dark4=open('C:\\wamp\\www\\raw_buffers\\DBFS\\2014-09-29\\databomb_DBa15287c0-480e-11e4-874b-0010187736b5_at_time_1412018840.27.txt')
dark5=open('C:\\wamp\\www\\raw_buffers\\DBFS\\2014-09-29\\databomb_DBa7e0ff40-480e-11e4-8d21-0010187736b5_at_time_1412018851.27.txt')
dark6=open('C:\\wamp\\www\\raw_buffers\\DBFS\\2014-09-29\\databomb_DBadd6e040-480e-11e4-be57-0010187736b5_at_time_1412018861.27.txt')
dark7=open('C:\\wamp\\www\\raw_buffers\\DBFS\\2014-09-29\\databomb_DBb46557c0-480e-11e4-89a0-0010187736b5_at_time_1412018872.27.txt')
dark8=open('C:\\wamp\\www\\raw_buffers\\DBFS\\2014-09-29\\databomb_DBba5b38c0-480e-11e4-b00e-0010187736b5_at_time_1412018882.27.txt')
dark9=open('C:\\wamp\\www\\raw_buffers\\DBFS\\2014-09-29\\databomb_DBc0e9b040-480e-11e4-99a6-0010187736b5_at_time_1412018893.27.txt')
dark10=open('C:\\wamp\\www\\raw_buffers\\DBFS\\2014-09-29\\databomb_DBc77827c0-480e-11e4-9684-0010187736b5_at_time_1412018904.27.txt')
dark11=open('C:\\wamp\\www\\raw_buffers\\DBFS\\2014-09-29\\databomb_DBcd6e08c0-480e-11e4-9b42-0010187736b5_at_time_1412018914.27.txt')


darkarr1 = np.asarray(pickle.load(dark1),dtype=int)
darkarr2 = np.asarray(pickle.load(dark2),dtype=int)
darkarr3 = np.asarray(pickle.load(dark3),dtype=int)
darkarr4 = np.asarray(pickle.load(dark4),dtype=int)
darkarr5 = np.asarray(pickle.load(dark5),dtype=int)
darkarr6 = np.asarray(pickle.load(dark6),dtype=int)
darkarr7 = np.asarray(pickle.load(dark7),dtype=int)
darkarr8 = np.asarray(pickle.load(dark8),dtype=int)
darkarr9 = np.asarray(pickle.load(dark9),dtype=int)
darkarr10 = np.asarray(pickle.load(dark10),dtype=int)
darkarr11 = np.asarray(pickle.load(dark11),dtype=int)

darkavg=(darkarr1+darkarr2+darkarr3+darkarr4+darkarr5+darkarr6+darkarr7+darkarr8+darkarr9+darkarr10+darkarr11)/11.0
darkdev=np.sqrt(((darkarr1-darkavg)**2+(darkarr2-darkavg)**2+(darkarr3-darkavg)**2+(darkarr4-darkavg)**2+(darkarr5-darkavg)**2+(darkarr6-darkavg)**2+(darkarr7-darkavg)**2+(darkarr8-darkavg)**2+(darkarr9-darkavg)**2+(darkarr10-darkavg)**2+(darkarr11-darkavg)**2)/11.0)

#pdb.set_trace()
#plt.imshow(darkavg)
#plt.show(block=False)

#plt.imshow(darkdev)
#plt.show(block=False)


dark1.close()
dark2.close()
dark3.close()
dark4.close()
dark5.close()
dark6.close()
dark7.close()
dark8.close()
dark9.close()
dark10.close()
dark11.close()


#pdb.set_trace()