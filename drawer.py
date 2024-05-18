#!/bin/env python

import pandas as pd
import geopandas as gpd
import numpy as np
import cv2 as cv
from shapely import Polygon, MultiPolygon
import matplotlib.pyplot as plt

def getCoords(coorText):
    coordinates = list()
    for coord in coorText.split('|'):
        if coord:
            sp = coord.split(',')
            coordinates.append((int(sp[0]),int(sp[1])))
    return np.array(coordinates)


def upscalling(x):
    return 10*x

#frame has form (xMin, xMax, yMin, yMax)
def mkImg(coordintes, frame):
    img = np.zeros((upscalling(frame[1]-frame[0]+1),upscalling(frame[3]-frame[2]+1)), dtype=np.ubyte)
    for y, x in coordintes:
        for i in range(upscalling(x-frame[0]),upscalling(x-frame[0]+1)):
            for j in range(upscalling(y-frame[2]),upscalling(y-frame[2]+1)):
                img[i][j] = 1
    return img

def getPoly(coordText, frame):
    img = mkImg(getCoords(coordText), frame)
    contours, hierarchy = cv.findContours(img, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    return Polygon(np.squeeze(contours[0]))

def getRegions():
    lg_xml = pd.read_xml('region4-00101-02-21-legends.xml', xpath='./regions/*', encoding='CP437')
    lg_xml.set_index('id', inplace=True)


    lgp_xml = pd.read_xml('region4-00101-02-21-legends_plus.xml', xpath='./regions/*', encoding='CP437')
    lgp_xml.set_index('id', inplace=True)

    regions = lg_xml.join(lgp_xml)

    oceanCoords = getCoords(regions[regions['type']=='Ocean']['coords'][0]).transpose()
    frameSize = (oceanCoords[0].min(), oceanCoords[0].max(), oceanCoords[1].min(), oceanCoords[1].max())

    img = mkImg(oceanCoords.transpose(),frameSize)

    contours, hierarchy = cv.findContours(img, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    poly = MultiPolygon().union(Polygon(np.squeeze(contours[0])))
    for cont in contours[1:]:
        poly = poly.difference(Polygon(np.squeeze(cont)))


    regions['geometry'] = regions['coords'].apply(getPoly, args=(frameSize,))
    regions.loc[regions['type']=='Ocean','geometry'] = poly

    del regions['coords']

    return gpd.GeoDataFrame(regions)

biomeColor = {'Ocean':'blue', 'Hills':'gray', 'Grassland':'green', 'Wetland':'purple', 'Desert':'yellow', 'Mountains':'black', 'Forest':'darkgreen', 'Tundra':'steelblue', 'Glacier':'white'}



