# -*- coding: utf-8 -*-
"""
Created on Mon Nov 03 10:50:30 2014

@author: User
"""
import pprint
import lxml.etree as ET

parser = ET.XMLParser(remove_blank_text=True)
dom = ET.parse("C:\\wamp\\www\\MetaViewer\\transforms\\default.xsd", parser)
xslt = ET.parse("C:\\wamp\\www\\MetaViewer\\transforms\\XTSM_xsd_to_xsl_light.xsl", parser)
transform = ET.XSLT(xslt)
newdom = transform(dom)
print(ET.tostring(newdom, pretty_print=True))
f = open('C:\\wamp\\www\\MetaViewer\\transforms\\default.xsl','w')
f.write('<?xml version="1.0" encoding="utf-8"?>\n')
f.write(ET.tostring(newdom, pretty_print=True))
f.close()