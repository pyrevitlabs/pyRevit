# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET

from pyrevit import script

__context__ = 'zero-doc'


utf8xml = script.get_bundle_file('utf8.xml')
utf16xml = script.get_bundle_file('utf16.xml')


for xmlfile in [utf8xml, utf16xml]:
    print('Testing: {}'.format(xmlfile))
    c = ET.parse(xmlfile)
    print(c)

    xmlp = ET.XMLParser(encoding="utf-16")
    f = ET.parse(xmlfile, parser=xmlp)
    print(xmlp, f)
