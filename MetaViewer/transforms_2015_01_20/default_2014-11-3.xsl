﻿<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" exclude-result-prefixes="xs xsl xtsm_viewer" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output omit-xml-declaration="yes" indent="yes" encoding="UTF-8" method="xml" />
  <xsl:template name="toolpanel">
    <img src="../images/seqicon_uparrow.png" height="15px" align="right" alt="⇑" xtsm_viewer_event="onclick:modifyElement_update_editor('move','+1');" />
    <img src="../images/seqicon_downarrow.png" height="15px" align="right" alt="⇓" xtsm_viewer_event="onclick:modifyElement_update_editor('move','-1');" />
    <img src="../images/seqicon_clone.png" height="15px" align="right" alt="c" xtsm_viewer_event="onclick:modifyElement_update_editor('clone');" />
    <img src="../images/seqicon_x.png" height="15px" align="right" alt="X" xtsm_viewer_event="onclick:modifyElement_update_editor('delete');" />
    <img src="../images/seqicon_code.png" height="15px" align="right" alt="&lt;..&gt;" xtsm_viewer_event="onclick:toggleProp_update_editor('editMode');" />
    <img src="../images/seqicon_plus.png" height="15px" align="right" alt="+" xtsm_viewer_event="onclick:spawn_child_menu();" />
  </xsl:template>
  <xsl:template name="repeat">
    <xsl:param name="output" />
    <xsl:param name="count" />
    <xsl:value-of select="$output" />
    <xsl:if test="$count &gt; 1">
      <xsl:call-template name="repeat">
        <xsl:with-param name="output" select="$output" />
        <xsl:with-param name="count" select="$count - 1" />
      </xsl:call-template>
    </xsl:if>
  </xsl:template>
  <xsl:template name="treeid">divtree<xsl:for-each select="ancestor-or-self::*">__<xsl:value-of select="name()" />_<xsl:value-of select="count(preceding-sibling::*[name(.) = name(current())])+1" /></xsl:for-each></xsl:template>
  <xsl:template match="/XTSM">
    <ul>
      <xsl:apply-templates />
    </ul>
  </xsl:template>
  <xsl:template name="topline_preamble">
    <xsl:attribute name="gen_id">
      <xsl:call-template name="treeid" />
      <xsl:text>__</xsl:text>
    </xsl:attribute>
    <xsl:attribute name="class">xtsm_<xsl:value-of select="name()" />_head</xsl:attribute>
    <img height="15px">
      <xsl:attribute name="src">
        <xsl:choose>
          <xsl:when test="@expanded='1'">../images/DownTriangleIcon.png</xsl:when>
          <xsl:otherwise>../images/RightFillTriangleIcon.png</xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
      <xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('expanded');</xsl:attribute>
    </img>
    <input type="checkbox">
      <xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute>
      <xsl:if test="not(@disable) or @disable!='1'">
        <xsl:attribute name="checked">checked</xsl:attribute>
      </xsl:if>
    </input>
    <img height="15px">
      <xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('lock');</xsl:attribute>
      <xsl:attribute name="src">
        <xsl:choose>
          <xsl:when test="@lock='1'">../images/seqicon_lock.png</xsl:when>
          <xsl:otherwise>../images/seqicon_unlock.png</xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
      <xsl:attribute name="alt">☠</xsl:attribute>
    </img>
    <xsl:value-of select="name()" />:</xsl:template>
  <xsl:template name="gen_input_field">
    <xsl:value-of select="name()" />:<xsl:call-template name="repeat"><xsl:with-param name="count" select="20- string-length(name(.))" /><xsl:with-param name="output">.</xsl:with-param></xsl:call-template><input><xsl:attribute name="value"><xsl:value-of select="child::node()" /></xsl:attribute><xsl:attribute name="title"><xsl:value-of select="concat(&quot;parsed-to:      &quot;,@current_value)" /></xsl:attribute><xsl:attribute name="name"><xsl:value-of select="name()" />_<xsl:value-of select="count(preceding-sibling::*[name(.) = name(current())])+1" /></xsl:attribute><xsl:attribute name="xtsm_viewer_event">onblur:updateElement_update_editor('');</xsl:attribute><xsl:attribute name="size">25</xsl:attribute></input><xsl:if test="@editmode='html' or @editmode='tohtml'"><img src="images/seqicon_translate.png" height="20px" /></xsl:if></xsl:template>
  <xsl:template name="child_div">
    <xsl:attribute name="gen_id">divtree<xsl:for-each select="ancestor-or-self::*">__<xsl:value-of select="name()" />_<xsl:value-of select="count(preceding-sibling::*[name(.) = name(current())])+1" /></xsl:for-each></xsl:attribute>
    <xsl:attribute name="class">xtsm_<xsl:value-of select="name()" />_body</xsl:attribute>
    <xsl:attribute name="style">display:<xsl:choose><xsl:when test="@expanded='1'">block</xsl:when><xsl:otherwise>none</xsl:otherwise></xsl:choose>;</xsl:attribute>
    <xsl:if test="name()='Figure'">
      <div>
        <xsl:attribute name="content_id">
          <xsl:value-of select="@content_id" />
        </xsl:attribute>
        <img src="../images/seqicon_null.jpg" height="15px">
          <xsl:attribute name="xtsm_viewer_event">onload:load_livedata('<xsl:value-of select="@content_id" />');</xsl:attribute>
        </img>
      </div>
    </xsl:if>
    <ul>
      <xsl:choose>
        <xsl:when test="@editmode='codemirror'">
          <li>
            <textarea cols="80" rows="10">
              <xsl:copy-of select="." />
            </textarea>
          </li>
        </xsl:when>
        <xsl:otherwise>
          <xsl:apply-templates select="child::node()" />
        </xsl:otherwise>
      </xsl:choose>
    </ul>
  </xsl:template>
  <xsl:template match="*[not(*)]" priority="-2">
    <li>
      <div>
        <xsl:attribute name="gen_id">
          <xsl:call-template name="treeid" />
        </xsl:attribute>
        <input type="checkbox">
          <xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute>
          <xsl:if test="not(@disable) or @disable!='1'">
            <xsl:attribute name="checked">checked</xsl:attribute>
          </xsl:if>
        </input>
        <a title="Non-standard XTSM tag." style="background-color:yellow;">
          <xsl:call-template name="gen_input_field" />
        </a>
        <xsl:call-template name="toolpanel" />
      </div>
    </li>
  </xsl:template>
  <xsl:template match="*[*]" priority="-2">
    <li>
      <div>
        <xsl:call-template name="topline_preamble" />
        <a title="Nonstandard XTSM element as container" style="background-color:yellow;">
          <xsl:text>(?)</xsl:text>
        </a>
        <xsl:call-template name="repeat">
          <xsl:with-param name="count" select="20- string-length(name(.))" />
          <xsl:with-param name="output">.</xsl:with-param>
        </xsl:call-template>
        <xsl:call-template name="toolpanel" />
      </div>
      <div>
        <xsl:call-template name="child_div" />
      </div>
    </li>
  </xsl:template>
  


  <xsl:template match="XTSM"><li><div><xsl:call-template name="topline_preamble" /><xsl:call-template name="repeat"><xsl:with-param name="count" select="20- string-length(name(.))" /><xsl:with-param name="output">.</xsl:with-param></xsl:call-template><xsl:call-template name="toolpanel" /></div><div><xsl:choose><xsl:when test="@expanded='1'"><xsl:call-template name="child_div" /></xsl:when><xsl:otherwise /></xsl:choose></div></li></xsl:template>

  <xsl:template match="SequenceSelector"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="head"><li><div><xsl:call-template name="topline_preamble" /><xsl:call-template name="repeat"><xsl:with-param name="count" select="20- string-length(name(.))" /><xsl:with-param name="output">.</xsl:with-param></xsl:call-template><xsl:call-template name="toolpanel" /></div><div><xsl:choose><xsl:when test="@expanded='1'"><xsl:call-template name="child_div" /></xsl:when><xsl:otherwise /></xsl:choose></div></li></xsl:template>

  <xsl:template match="ChannelMap"><li><div><xsl:call-template name="topline_preamble" /><xsl:call-template name="repeat"><xsl:with-param name="count" select="20- string-length(name(.))" /><xsl:with-param name="output">.</xsl:with-param></xsl:call-template><xsl:call-template name="toolpanel" /></div><div><xsl:choose><xsl:when test="@expanded='1'"><xsl:call-template name="child_div" /></xsl:when><xsl:otherwise /></xsl:choose></div></li></xsl:template>

  <xsl:template match="Channel"><li><div><xsl:call-template name="topline_preamble" /><xsl:call-template name="repeat"><xsl:with-param name="count" select="20- string-length(name(.))" /><xsl:with-param name="output">.</xsl:with-param></xsl:call-template><xsl:for-each select="ChannelName"><xsl:call-template name="gen_input_field" /></xsl:for-each><xsl:call-template name="toolpanel" /></div><div><xsl:choose><xsl:when test="@expanded='1'"><xsl:call-template name="child_div" /></xsl:when><xsl:otherwise /></xsl:choose></div></li></xsl:template>

  <xsl:template match="TimingGroupData"><li><div><xsl:call-template name="topline_preamble" /><xsl:call-template name="repeat"><xsl:with-param name="count" select="20- string-length(name(.))" /><xsl:with-param name="output">.</xsl:with-param></xsl:call-template><xsl:for-each select="Name | GroupNumber"><xsl:call-template name="gen_input_field" /></xsl:for-each><xsl:call-template name="toolpanel" /></div><div><xsl:choose><xsl:when test="@expanded='1'"><xsl:call-template name="child_div" /></xsl:when><xsl:otherwise /></xsl:choose></div></li></xsl:template>


  <xsl:template match="body"><li><div><xsl:call-template name="topline_preamble" /><xsl:call-template name="repeat"><xsl:with-param name="count" select="20- string-length(name(.))" /><xsl:with-param name="output">.</xsl:with-param></xsl:call-template><xsl:call-template name="toolpanel" /></div><div><xsl:choose><xsl:when test="@expanded='1'"><xsl:call-template name="child_div" /></xsl:when><xsl:otherwise /></xsl:choose></div></li></xsl:template>

  <xsl:template match="Sequence"><li><div><xsl:call-template name="topline_preamble" /><xsl:call-template name="repeat"><xsl:with-param name="count" select="20- string-length(name(.))" /><xsl:with-param name="output">.</xsl:with-param></xsl:call-template><xsl:for-each select="Name"><xsl:call-template name="gen_input_field" /></xsl:for-each><xsl:call-template name="toolpanel" /></div><div><xsl:choose><xsl:when test="@expanded='1'"><xsl:call-template name="child_div" /></xsl:when><xsl:otherwise /></xsl:choose></div></li></xsl:template>

  <xsl:template match="SubSequence"><li><div><xsl:call-template name="topline_preamble" /><xsl:call-template name="repeat"><xsl:with-param name="count" select="20- string-length(name(.))" /><xsl:with-param name="output">.</xsl:with-param></xsl:call-template><xsl:for-each select="Name | StartTime"><xsl:call-template name="gen_input_field" /></xsl:for-each><xsl:call-template name="toolpanel" /></div><div><xsl:choose><xsl:when test="@expanded='1'"><xsl:call-template name="child_div" /></xsl:when><xsl:otherwise /></xsl:choose></div></li></xsl:template>

  <xsl:template match="Edge"><li><div><xsl:call-template name="topline_preamble" /><xsl:call-template name="repeat"><xsl:with-param name="count" select="20- string-length(name(.))" /><xsl:with-param name="output">.</xsl:with-param></xsl:call-template><xsl:for-each select="Time | Value | OnChannel"><xsl:call-template name="gen_input_field" /></xsl:for-each><xsl:call-template name="toolpanel" /></div><div><xsl:choose><xsl:when test="@expanded='1'"><xsl:call-template name="child_div" /></xsl:when><xsl:otherwise /></xsl:choose></div></li></xsl:template>

  <xsl:template match="Interval"><li><div><xsl:call-template name="topline_preamble" /><xsl:call-template name="repeat"><xsl:with-param name="count" select="20- string-length(name(.))" /><xsl:with-param name="output">.</xsl:with-param></xsl:call-template><xsl:for-each select="StartTime | EndTime | Value | OnChannel"><xsl:call-template name="gen_input_field" /></xsl:for-each><xsl:call-template name="toolpanel" /></div><div><xsl:choose><xsl:when test="@expanded='1'"><xsl:call-template name="child_div" /></xsl:when><xsl:otherwise /></xsl:choose></div></li></xsl:template>

  <xsl:template match="Sample"><li><div><xsl:call-template name="topline_preamble" /><xsl:call-template name="repeat"><xsl:with-param name="count" select="20- string-length(name(.))" /><xsl:with-param name="output">.</xsl:with-param></xsl:call-template><xsl:for-each select="StartTime | EndTime | OnChannel"><xsl:call-template name="gen_input_field" /></xsl:for-each><xsl:call-template name="toolpanel" /></div><div><xsl:choose><xsl:when test="@expanded='1'"><xsl:call-template name="child_div" /></xsl:when><xsl:otherwise /></xsl:choose></div></li></xsl:template>

  <xsl:template match="Script"><li><div><xsl:call-template name="topline_preamble" /><xsl:call-template name="repeat"><xsl:with-param name="count" select="20- string-length(name(.))" /><xsl:with-param name="output">.</xsl:with-param></xsl:call-template><xsl:for-each select="Name"><xsl:call-template name="gen_input_field" /></xsl:for-each><xsl:call-template name="toolpanel" /></div><div><xsl:choose><xsl:when test="@expanded='1'"><xsl:call-template name="child_div" /></xsl:when><xsl:otherwise /></xsl:choose></div></li></xsl:template>

  <xsl:template match="ScriptOutput"><li><div><xsl:call-template name="topline_preamble" /><xsl:call-template name="repeat"><xsl:with-param name="count" select="20- string-length(name(.))" /><xsl:with-param name="output">.</xsl:with-param></xsl:call-template><xsl:for-each select="Name"><xsl:call-template name="gen_input_field" /></xsl:for-each><xsl:call-template name="toolpanel" /></div><div><xsl:choose><xsl:when test="@expanded='1'"><xsl:call-template name="child_div" /></xsl:when><xsl:otherwise /></xsl:choose></div></li></xsl:template>

  <xsl:template match="Heap"><li><div><xsl:call-template name="topline_preamble" /><xsl:call-template name="repeat"><xsl:with-param name="count" select="20- string-length(name(.))" /><xsl:with-param name="output">.</xsl:with-param></xsl:call-template><xsl:for-each select="HeapTo"><xsl:call-template name="gen_input_field" /></xsl:for-each><xsl:call-template name="toolpanel" /></div><div><xsl:choose><xsl:when test="@expanded='1'"><xsl:call-template name="child_div" /></xsl:when><xsl:otherwise /></xsl:choose></div></li></xsl:template>


  <xsl:template match="DataNode"><li><div><xsl:call-template name="topline_preamble" /><xsl:call-template name="repeat"><xsl:with-param name="count" select="20- string-length(name(.))" /><xsl:with-param name="output">.</xsl:with-param></xsl:call-template><xsl:for-each select="Name"><xsl:call-template name="gen_input_field" /></xsl:for-each><xsl:call-template name="toolpanel" /></div><div><xsl:choose><xsl:when test="@expanded='1'"><xsl:call-template name="child_div" /></xsl:when><xsl:otherwise /></xsl:choose></div></li></xsl:template>

  <xsl:template match="Parameter"><li><div><xsl:call-template name="topline_preamble" /><xsl:call-template name="repeat"><xsl:with-param name="count" select="20- string-length(name(.))" /><xsl:with-param name="output">.</xsl:with-param></xsl:call-template><xsl:for-each select="Name | Value"><xsl:call-template name="gen_input_field" /></xsl:for-each><xsl:call-template name="toolpanel" /></div><div><xsl:choose><xsl:when test="@expanded='1'"><xsl:call-template name="child_div" /></xsl:when><xsl:otherwise /></xsl:choose></div></li></xsl:template>

  <xsl:template match="Figure"><li><div><xsl:call-template name="topline_preamble" /><xsl:call-template name="repeat"><xsl:with-param name="count" select="20- string-length(name(.))" /><xsl:with-param name="output">.</xsl:with-param></xsl:call-template><xsl:for-each select="Name | FigureType"><xsl:call-template name="gen_input_field" /></xsl:for-each><xsl:call-template name="toolpanel" /></div><div><xsl:choose><xsl:when test="@expanded='1'"><xsl:call-template name="child_div" /></xsl:when><xsl:otherwise /></xsl:choose></div></li></xsl:template>

  <xsl:template match="HeapTo"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>


  <xsl:template match="DataLink"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="Name"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="ChannelName"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="ClockedBy"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="Calibration"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="Time"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="StartTime"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="Value"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="EndTime"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="OnChannel"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="Description"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="Comments"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="ConnectsTo"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="Group"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="TimingGroup"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="ChannelCount"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="TimingGroupIndex"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="ResolutionBits"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="HoldingValue"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="ClockPeriod"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="SelfClockPeriod"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="Scale"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="MinValue"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="MaxValue"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="MaxDuty"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="MaxDuration"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="MaxTriggers"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="GroupNumber"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="TResolution"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="VResolution"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  <xsl:template match="DelayTrain"><li><div><xsl:attribute name="gen_id"><xsl:call-template name="treeid" /></xsl:attribute><input type="checkbox"><xsl:attribute name="xtsm_viewer_event">onclick:toggleProp_update_editor('disable');</xsl:attribute><xsl:if test="not(@disable) or @disable!='1'"><xsl:attribute name="checked">checked</xsl:attribute></xsl:if></input><xsl:call-template name="gen_input_field" /><xsl:call-template name="toolpanel" /></div></li></xsl:template>

  
    
    
    
  

  
    
    
  

  
    
    
  

</xsl:stylesheet>