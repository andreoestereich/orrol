#!/bin/env python

import pandas as pd
import numpy as np
#from shapely import Polygon
#import geopandas as gpd
import matplotlib.pyplot as plt

def getPoly(coorText):
    coordinates = list()
    for coord in coorText.split('|'):
        if coord:
            sp = coord.split(',')
            coordinates.append((int(sp[0]),int(sp[1])))

    return np.array(coordinates)

#frame has form (xMin, xMax, yMin, yMax)
def mkImg(coordintes, frame):
    img = np.zeros((frame[1]-frame[0]+1,frame[3]-frame[2]+1))
    for x, y in coordintes:
        img[x-frame[0]][y-frame[2]] = 1
    return img

biomeColor = {'Ocean':'blue', 'Hills':'gray', 'Grassland':'green', 'Wetland':'purple', 'Desert':'yellow', 'Mountains':'black', 'Forest':'darkgreen', 'Tundra':'steelblue', 'Glacier':'white'}

lg_xml = pd.read_xml('region4-00101-02-21-legends.xml', xpath='./regions/*', encoding='CP437')
lg_xml.set_index('id', inplace=True)


lgp_xml = pd.read_xml('region4-00101-02-21-legends_plus.xml', xpath='./regions/*', encoding='CP437')
lgp_xml.set_index('id', inplace=True)

regions = lg_xml.join(lgp_xml)

regions['coords'] = regions['coords'].apply(getPoly)



regions['color'] = regions['type'].apply(lambda x: biomeColor[x])

oceanCoords = regions[regions['type']=='Ocean']['coords'][0].transpose()
frameSize = (oceanCoords[0].min(), oceanCoords[0].max(), oceanCoords[1].min(), oceanCoords[1].max())

regions['img'] = regions['coords'].apply(mkImg, args=(frameSize))

for _, row in regions.iterrows():
    points = np.transpose(row['coords'])
    plt.scatter(points[0], points[1], color=row['color'], marker='s')

plt.imshow(regions[regions['type']=='Ocean']['img'][0])
plt.show()

