<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:msxsl="urn:schemas-microsoft-com:xslt" exclude-result-prefixes="msxsl">
    <xsl:output method="xml" indent="yes"/>
  <xsl:template name="treeid">divtree<xsl:for-each select="ancestor-or-self::*">__<xsl:value-of select="name()" />_<xsl:value-of select="count(preceding-sibling::*[name(.) = name(current())])+1" /></xsl:for-each></xsl:template>

  <xsl:template match=" node()">
    <xsl:choose>
      <xsl:when test="count(./node())=0">
        <li><xsl:value-of select="name(.)"/><input type="text"><xsl:attribute name="value"><xsl:value-of select="."/></xsl:attribute></input><xsl:apply-templates select="@* | node()"/></li>
      </xsl:when>
      <xsl:when test="count(./node())>0">
        <xsl:value-of select="name(.)"/><ul><xsl:apply-templates select="@* | node()"/></ul>
      </xsl:when>
    </xsl:choose>
  </xsl:template>

</xsl:stylesheet>
