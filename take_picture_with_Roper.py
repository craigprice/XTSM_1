
import Roper_CCD
self.server.dataContexts['default'].update({'Roper_CCD':Roper_CCD.Princeton_CCD(params={'server':self.server})})
self.server.dataContexts['default']['Roper_CCD'].set_autoframing()
self.server.dataContexts['default']['Roper_CCD'].start_acquisition()
