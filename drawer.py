#!/bin/env python

import pandas as pd
import geopandas as gpd
import numpy as np
import cv2 as cv
from shapely import Polygon, MultiPolygon, centroid
import folium

#import matplotlib.pyplot as plt

def getCoords(coorText):
    coordinates = list()
    for coord in coorText.split('|'):
        if coord:
            sp = coord.split(',')
            coordinates.append((int(sp[0]),int(sp[1])))
    return np.array(coordinates)

def getRectangle(txt):
    coord = txt.split(':')
    y1,x1 = coord[0].split(',')
    y2,x2 = coord[1].split(',')
    return [[int(x1),int(y1)],[int(x2),int(y2)]]

def rectangleCenter(corners):
    xc = corners[0][0] + (corners[1][0]-corners[0][0])/2
    yc = corners[0][1] + (corners[1][1]-corners[0][1])/2
    return [xc, yc]

#16 is the same upscalling used in the game when you zoom in
def upscalling(x):
    return 16*x

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
    contours, _ = cv.findContours(img, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    poly = MultiPolygon().union(Polygon(np.squeeze(contours[0])))
    for cont in contours[1:]:
        poly = poly.difference(Polygon(np.squeeze(cont)))

    return poly

def getRegions():
    lg_xml = pd.read_xml('region4-00101-02-21-legends.xml', xpath='./regions/*', encoding='CP437')
    lg_xml.set_index('id', inplace=True)


    lgp_xml = pd.read_xml('region4-00101-02-21-legends_plus.xml', xpath='./regions/*', encoding='CP437')
    lgp_xml.set_index('id', inplace=True)

    regions = lg_xml.join(lgp_xml)

    oceanCoords = getCoords(regions[regions['type']=='Ocean']['coords'][0]).transpose()
    frameSize = (oceanCoords[0].min(), oceanCoords[0].max(), oceanCoords[1].min(), oceanCoords[1].max())

    regions['geometry'] = regions['coords'].apply(getPoly, args=(frameSize,))

    del regions['coords']

    #return regions
    return gpd.GeoDataFrame(regions)

def makeRegionsMap():
    biomeColor = {'Ocean':'blue', 'Hills':'gray', 'Grassland':'green', 'Wetland':'purple', 'Desert':'yellow', 'Mountains':'black', 'Forest':'darkgreen', 'Tundra':'steelblue', 'Glacier':'white'}


    regions = getRegions()

    center = centroid(regions[regions["type"]=="Ocean"]["geometry"][0])
    center = list(center.coords)[0]

    base_map = folium.Map(crs='Simple', zoom_start=0, tiles=None, location=center, default_zoom_start=20)

    popup = folium.GeoJsonPopup(
        fields=["name", "evilness"],
        localize=True,
        labels=True,
        sticky=False,
        style="""
            background-color: #F0EFEF;
            border: 2px solid black;
            border-radius: 3px;
            box-shadow: 3px;
        """,
        max_width=800
    )

    mp = folium.GeoJson(data=regions.to_json(),
        style_function=lambda x: {
            "color": "white",
            "weight": 0,
            "dashArray": "5, 5",
            "fillColor": biomeColor[x["properties"]["type"]]
        }, popup=popup)
    mp.add_to(base_map)
    return base_map

def makeSitesMap():
    # siteIcons = {'camp':'☼', 'cave':'•', 'dark fortress':'Π', 'dark pits': 'º', 'forest retreat': '¶','fortress':'Ω','castle': '○',
    #              'fort': '○','hamlet': '=','hillocks': 'Ω','labyrinth': '#','lair': '•','monastery': '○','mountain halls': 'Ω','ruins': 'μ',
    #              'forest retreat ruins': 'μ','shrine': 'Å','tomb': '0','tower': 'I','town': '+','vault': '■'}

    sites = pd.read_xml('region4-00101-02-21-legends.xml', xpath='./sites/*', encoding='CP437')
    sites.set_index('id', inplace=True)

    lgp_xml = pd.read_xml('region4-00101-02-21-legends_plus.xml', xpath='./sites/*')
    lgp_xml.set_index('id', inplace=True)
    lgp_xml.rename(columns={'structures':'structures_plus'}, inplace=True)

    sites = sites.join(lgp_xml)

    siteLayer = folium.FeatureGroup('Sites', control=False)
    for _, row in sites.iterrows():
        rect = getRectangle(row['rectangle'])
        folium.Rectangle(bounds=rect, color=None, fill=True, fill_color='#ff0000', fill_opacity=0.2).add_to(siteLayer)
        center = rectangleCenter(rect)
        imgPath = 'imgs/sites/Icon_site_%s.png'%(row.type.replace(' ','_'))
        icon = folium.features.CustomIcon(imgPath, icon_size=(16,16))
        folium.Marker(center, tooltip=row['name'], icon=icon).add_to(siteLayer)

    return siteLayer


map = makeRegionsMap()
makeSitesMap().add_to(map)
map.save("map.html")

