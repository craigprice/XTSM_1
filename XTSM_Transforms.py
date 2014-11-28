# -*- coding: utf-8 -*-
"""
Created on Tue Apr 15 19:53:39 2014

@author: Nate
"""
import lxml.etree, StringIO

def strip_to_active(xtsm_string):
    """
    strips prior results of parsing, data attachment and script evaluation
    """
    r=remove_attributes(xtsm_string,["current_value","parser_error","parser_warning"])
    r=remove_nodes(r,["DataLink","DataNode","ParserOutput","ControlArray","parsererror"])
    r=remove_node_subnodeValue(r,"Parameter","Name","shotnumber")
    return r 

def remove_node_subnodeValue(source,nodeType,subnodeType,subNodeValue):
    """
    removes a node of a given type with a subnode of given type and value
    """
    xsl="""<?xml version="1.0" encoding="ISO-8859-1"?>
        <xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
        <xsl:output method="xml" encoding="ISO-8859-1"/>
        
        <xsl:template match="*|@*">
            <xsl:copy>
              <xsl:apply-templates select="node()|@*"/>
            </xsl:copy>
        </xsl:template>"""
    xsl+="<xsl:template match='"+nodeType+"["+subnodeType+"=\""+subNodeValue+"\"]' /></xsl:stylesheet>"
    return apply_xsl(source,xsl)        

def remove_nodes(source,nodes):
    """
    removes a list of nodes input as nodes="nodename1 | nodename2 | ..."
    or as a list of strings ["nodename1","nodename2",...]
    from a source xml document - note any node removed will have children
    removed as well.
    """
    if type(nodes)==type([]): nodes="|".join(nodes)
    xsl="""<xsl:stylesheet version="1.0"
         xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
         <xsl:output omit-xml-declaration="yes" indent="yes"/>
         <xsl:strip-space elements="*"/>
        
         <xsl:param name="removeElementsNamed" select="'|"""
    xsl+= nodes 
    xsl+="""|'"/>
         <xsl:template match="node()|@*" name="identity">
          <xsl:copy>
           <xsl:apply-templates select="node()|@*"/>
          </xsl:copy>
         </xsl:template>
        
         <xsl:template match="*">
          <xsl:if test=
           "not(contains($removeElementsNamed,
                         concat('|',name(),'|' )
                         )
                )
           ">
           <xsl:call-template name="identity"/>
          </xsl:if>
         </xsl:template>
        </xsl:stylesheet>"""
    return apply_xsl(source,xsl)
    
def remove_attributes(source,attributes):
    """
    removes all occurences of given list of attributes input
    as a list of string names : ["attribute1","attribute2",...]
    """
    if isinstance(attributes,basestring): attributes=[attributes]
    attributes="@"+"|@".join(attributes)
    xsl="""<xsl:stylesheet version="1.0"
     xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
     xmlns:x="http://www.w3.org/1999/xhtml"
     xmlns="http://www.w3.org/1999/xhtml" exclude-result-prefixes="x">
     <xsl:output omit-xml-declaration="yes" indent="yes"/>
     <xsl:strip-space elements="*"/>
    
     <xsl:template match="node()|@*">
      <xsl:copy>
       <xsl:apply-templates select="node()|@*"/>
      </xsl:copy>
     </xsl:template>
    
     <xsl:template match=" """
    xsl+=attributes
    xsl+=""" "/>
    </xsl:stylesheet>"""
    return apply_xsl(source,xsl)    
    
def apply_xsl(source,xsl):
    dom = lxml.etree.parse(StringIO.StringIO(source))
    xslt = lxml.etree.parse(StringIO.StringIO(xsl))
    transform = lxml.etree.XSLT(xslt)
    newdom = transform(dom)
    return lxml.etree.tostring(newdom, pretty_print=True)
    