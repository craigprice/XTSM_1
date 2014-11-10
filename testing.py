
import GPIB_control
import time
DEBUG = True
class gpib:
        
    def init_GPIB(self,address):
        '''
        if ip address is not found, run the program "GPIB Configuator" and look
        at ip. Or run "NetFinder" from Prologix
        '''
        self.GPIB_adapter = GPIB_control.PrologixGpibEthernet('10.1.1.113')
        
        read_timeout = 5.0
        if DEBUG: print "Setting adapter read timeout to %f seconds" % read_timeout
        self.GPIB_adapter.settimeout(read_timeout)
        
        gpib_address = int(13)#Analyzer
        if DEBUG: print "Using device GPIB address of %d" % gpib_address
        self.GPIB_device = GPIB_control.GpibDevice(self.GPIB_adapter, gpib_address)
        if DEBUG: print "Finished initialization of GPIB controller"
        
        
    
    def get_scope_field(self,q1="Data:Source CH1",
                        q2="Data:Encdg: ASCII",
                        q3="Data:Width 2",
                        q4="Data:Start 1",
                        q5="Data:Stop 500",
                        q6="wfmpre?" ,
                        q7="curve?",filename='NewScopeTrace',tdiv=10,vdiv=10):
    
    
        e1 = time.time()
        if not hasattr(self,'GPIB_device'):
            if DEBUG: print "GPIB device not ready"
            return
        response = self.GPIB_device.converse([q1,q2,q3,q4,q5,q6,q7])
        e2 = time.time()
        if DEBUG: print "Scope communication took", e2-e1, "sec"
        
        ystr = response["curve?"]
        if DEBUG: print "Data:", ystr
            
    
        print "Scope communication took", e2-e1,"s"
        #pdb.set_trace()
        ydata=[int(s) for s in ystr.split(',')]

        
    def get_spectrum_analyzer_trace(self):
    
        e1 = time.time()
        if not hasattr(self,'GPIB_device'):
            if DEBUG: print "GPIB device not ready"
            return
        
        q1 = 'FA?'#Specifies start frequency
        q2 = 'FB?'#Specifies stop frequency.
        q3 = 'RL?'#Adjusts the range level.
        q4 = 'RB?'#Specifies resolution bandwidth
        q5 = 'VB?'#Specifies video bandwidth.
        q6 = 'ST?'#Sweep Time
        q7 = 'LG?'#Log Scale
        q8 = 'AUNITS?'#Specifies amplitude units for input, output, and display
        #q9 = 'TDF B'#Specifies transfer in Binary format
        q9 = 'TDF P'#Specifies transfer in ASCII decimal values in real-number parameter format
        q10 = 'TRA?'
        e1 = time.time()
        response = g.GPIB_device.converse([q1,q2,q3,q4,q5,q6,q7,q8,q9])
        e2 = time.time()
        print response
        if DEBUG: print "communication took", e2-e1, "sec"
        
        
        e1 = time.time()
        response = g.GPIB_device.converse([q10])
        e2 = time.time()
        print response
        if DEBUG: print "communication took", e2-e1, "sec"
        
        
