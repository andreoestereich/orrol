#!/bin/env python

import xml.etree.ElementTree as ET

world = ET.parse('region1-00050-01-01-legends_plus.xml')

root = world.getroot()
 
for child in root[4][0]:
    print(child.tag, child.attrib)

