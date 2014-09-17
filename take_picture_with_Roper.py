import Roper_CCD
for key in self.server.dataContexts['default']:
    if self.server.dataContexts['default'][key] == 'Roper_CCD":
        print "ALready initialized"
        raise
self.server.dataContexts['default'].update({'Roper_CCD':Roper_CCD.Princeton_CCD(params={'server':self.server})})
self.server.dataContexts['default']['Princeton_CCD'].set_autoframing()
self.server.dataContexts['default']['Princeton_CCD'].start_acquisition()