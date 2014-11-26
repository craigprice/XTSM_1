# -*- coding: utf-8 -*-
"""
Created on Mon Nov 03 10:50:30 2014

@author: User
"""

import lxml.etree as ET

dom = ET.parse("C:\\wamp\\www\\MetaViewer\\transforms\\default.xsd")
xslt = ET.parse("C:\\wamp\\www\\MetaViewer\\transforms\\XTSM_xsd_to_xsl_light.xsl")
transform = ET.XSLT(xslt)
newdom = transform(dom)
print(ET.tostring(newdom, pretty_print=True))
f = open('C:\\wamp\\www\\MetaViewer\\transforms\\default.xsl','w')
f.write('<?xml version="1.0" encoding="utf-8"?>\n')
f.write(ET.tostring(newdom, pretty_print=True))
f.close()