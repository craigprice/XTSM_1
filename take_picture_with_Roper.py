#import glab_instrument
#self.server.dataContexts['default'].update({'Test_instrument':glab_instrument.Glab_Instrument(params={'server':self.server,'create_example_pollcallback':True})})
'''
'''
import Roper_CCD
isInitialized = False
#pdb.set_trace()
for key in self.server.dataContexts['default'].dict:
    #print "Checking if Initialized", self.server.dataContexts['default'].dict
    if key == 'Roper_CCD':
        isInitialized = True
#print "df"
if not isInitialized:
    print "Not initialized"
    self.server.dataContexts['default'].update({'Roper_CCD':Roper_CCD.Princeton_CCD(params={'server':self.server})})
    #self.server.dataContexts['default'].dict['Roper_CCD'].set_autoframing()

   # self.server.dataContexts['default'].dict['Roper_CCD'].set_param()
self.server.dataContexts['default'].dict['Roper_CCD'].set_param({"EXP_TIMING_MODE":3,
                       "EXP_EXPOSURE":0.1, 
                       "EXP_ACCUMS":1, 
                       "EXP_SEQUENTS":1,
                       "EXP_ANALOG_GAIN":1})    
self.server.dataContexts['default'].dict['Roper_CCD'].start_acquisition()
#print "Done with Script"
'''
'''