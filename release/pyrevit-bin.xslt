<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:wix="http://schemas.microsoft.com/wix/2006/wi"
    xmlns="http://schemas.microsoft.com/wix/2006/wi"
    version="1.0"
    exclude-result-prefixes="xsl wix">
    <xsl:output method="xml" indent="yes" omit-xml-declaration="yes" />
    <xsl:strip-space elements="*" />

    <!-- https://stackoverflow.com/questions/44765707/how-to-exclude-files-in-wix-toolset -->
    <!-- https://stackoverflow.com/questions/53498481/wix-xsl-transform-to-conditionally-remove-components -->
    <!-- mark engines directory and its contents -->
    <xsl:key name="EnginesDir" match="wix:Directory[@Name='engines']" use="@Id" />
    <xsl:key name="EnginesDirComps" match="wix:Component[ancestor::wix:Directory[@Name='engines']]" use="@Id" />

    <!-- copy everything verbatim -->
    <xsl:template match="@*|node()">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()" />
        </xsl:copy>
    </xsl:template>

    <!-- remove engines dir and all its component refs -->
    <xsl:template match="*[self::wix:Directory][key('EnginesDir', @Id )]" />
    <xsl:template match="*[self::wix:ComponentRef][key('EnginesDirComps', @Id )]" />

</xsl:stylesheet>