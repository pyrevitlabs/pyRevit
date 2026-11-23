# PartAtom stream

!!! note ""

    To easily extract this information from Revit models, see [Get Revit Model Information](../tools/get-rvt-info.md)  and [Extracting Revit File Info](index.md)  

Revit family files include a PartAtom stream written in ASCII.  
This stream is an xml document with specific `urn:schemas-autodesk-com:partatom` namespace

```xml
<?xml version="1.0" encoding="UTF-8"?>
<entry xmlns="http://www.w3.org/2005/Atom" xmlns:A="urn:schemas-autodesk-com:partatom">
    <title># Tag_Keynote</title>
    <id></id>
    <updated>2018-12-27T16:24:17Z</updated>
    <A:taxonomy>
        <term>adsk:revit</term><label>Autodesk Revit</label>
    </A:taxonomy>
    <A:taxonomy>
        <term>adsk:revit:grouping</term><label>Autodesk Revit Grouping</label>
    </A:taxonomy>
    <category>
        <term>Keynote Tags</term>
        <scheme>adsk:revit:grouping</scheme>
    </category>
    <link rel="design-2d" type="application/rfa" href=".">
    <A:design-file>
        <A:title># Tag_Keynote.rfa</A:title>
        <A:product>Revit</A:product>
        <A:product-version>2019</A:product-version>
        <A:updated>2018-12-27T16:24:17Z</A:updated>
    </A:design-file>
    </link>
    <A:features>
        <A:feature>
            <A:title>Family Parameters</A:title>
            <A:group>
                <A:title>Other</A:title>
                <Rotate_with_component displayName="Rotate with component"
                                       type="system"
                                       typeOfParameter="Yes/No">
                    No
                </Rotate_with_component>
            </A:group>
        </A:feature>
    </A:features>
    <A:family type="user">
        <A:variationCount>2</A:variationCount>
        <A:part type="user">
            <title># Text</title>
            <TYP. type="custom" typeOfParameter="Yes/No">No</TYP.>
            <Placeholder type="custom" typeOfParameter="Yes/No">Yes</Placeholder>
            <Keynote_Text displayName="Keynote Text" type="custom" typeOfParameter="Yes/No">Yes</Keynote_Text>
            <Keynote_Number displayName="Keynote Number" type="custom" typeOfParameter="Yes/No">No</Keynote_Number>
            <Hexagon type="custom" typeOfParameter="Yes/No">No</Hexagon>
        </A:part>
        <A:part type="user">
            <title># Symbol</title>
            <TYP. type="custom" typeOfParameter="Yes/No">No</TYP.>
            <Placeholder type="custom" typeOfParameter="Yes/No">Yes</Placeholder>
            <Keynote_Text displayName="Keynote Text" type="custom" typeOfParameter="Yes/No">No</Keynote_Text>
            <Keynote_Number displayName="Keynote Number" type="custom" typeOfParameter="Yes/No">Yes</Keynote_Number>
            <Hexagon type="custom" typeOfParameter="Yes/No">Yes</Hexagon>
        </A:part>
    </A:family>
</entry>
```

This stream contains many useful information about the family type, its parameters, and parameter values. Since this is a standard xml document, the stream is much easier to read and extract info from. Here is a C# snippet:

```csharp
using System.Xml;

// load xml document
var doc = new XmlDocument();
doc.LoadXml(rawPartAtom);
XmlNamespaceManager nsmgr = new XmlNamespaceManager(doc.NameTable);

// make sure to add the namespaces
nsmgr.AddNamespace("rfa", @"http://www.w3.org/2005/Atom");
nsmgr.AddNamespace("A", @"urn:schemas-autodesk-com:partatom");

// extract family category
string CategoryName;
var catElements = doc.SelectNodes("//rfa:entry/rfa:category/rfa:term", nsmgr);
if (catElements.Count > 0) {
    CategoryName = catElements[catElements.Count - 1].InnerText;
}
```
