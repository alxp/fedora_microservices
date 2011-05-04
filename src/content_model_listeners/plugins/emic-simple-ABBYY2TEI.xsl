<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns="http://www.abbyy.com/FineReader_xml/FineReader8-schema-v2.xml"
    xpath-default-namespace="http://www.abbyy.com/FineReader_xml/FineReader8-schema-v2.xml">

    <xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes"/>

    <xsl:template match="/">
        <xsl:processing-instruction name="oxygen">
            <xsl:text>RNGSchema="http://www.tei-c.org/Vault/P5/1.7.0/xml/tei/custom/schema/relaxng/tei_all.rng" type="xml"</xsl:text>
        </xsl:processing-instruction>
        <TEI xmlns="http://www.tei-c.org/ns/1.0">

            <teiHeader>
                <fileDesc>
                    <titleStmt>
                        <title/>
                    </titleStmt>

                    <publicationStmt>
                        <p/>
                    </publicationStmt>
                    <sourceDesc>
                        <p/>
                    </sourceDesc>
                </fileDesc>
                <encodingDesc>
                    <p/>
                </encodingDesc>
            </teiHeader>
            <facsimile xmlns="http://www.tei-c.org/ns/1.0">
                <xsl:attribute name="xml:id">
                    <xsl:value-of select="generate-id()"/>
                </xsl:attribute>

                <surface xmlns="http://www.tei-c.org/ns/1.0">
                    <graphic xmlns="http://www.tei-c.org/ns/1.0" url="$PID/JP2" width="$widthpx"
                        height="$heightpx"/>
                </surface>
            </facsimile>
            <text>
                <body>
                    <xsl:apply-templates select="document/page"/>
                </body>
            </text>

        </TEI>
    </xsl:template>

    <xsl:template match="page">
        <div type="page" xmlns="http://www.tei-c.org/ns/1.0">
            <xsl:attribute name="n">
                <xsl:value-of select="position()-1"/>
            </xsl:attribute>
            <xsl:apply-templates/>
        </div>
        <xsl:text>&#10;</xsl:text>
    </xsl:template>

    <xsl:template match="block[@blockType='Text']">
        <div xmlns="http://www.tei-c.org/ns/1.0">
            <xsl:apply-templates/>
        </div>
    </xsl:template>

    <xsl:template match="block[@blockType='Text']/text/par">
        <p xmlns="http://www.tei-c.org/ns/1.0">
            <xsl:apply-templates/>
        </p>
    </xsl:template>
</xsl:stylesheet>
