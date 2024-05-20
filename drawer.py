#!/bin/env python

import pandas as pd
import geopandas as gpd
import numpy as np
import cv2 as cv
from shapely import Polygon, MultiPolygon, centroid
import folium

#import matplotlib.pyplot as plt

popUpStyle = """
            background-color: #F0EFEF;
            border-radius: 3px;
            box-shadow: 3px;
            """

#In the game they do top to bottom and left to right coordinates. This means
#that the coordinates are writen as (-long,lat) pairs
def getCoords(coorText):
    coordinates = list()
    for coord in coorText.split('|'):
        if coord:
            sp = coord.split(',')
            coordinates.append([-int(sp[1]),int(sp[0])])
    return np.array(coordinates)

def getRectangle(txt,xmax):
    coord = txt.split(':')
    y1,x1 = coord[0].split(',')
    y2,x2 = coord[1].split(',')
    return [[xmax-int(x1),int(y1)],[xmax-int(x2),int(y2)]]

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
    for x, y in coordintes:
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
    lg_xml = pd.read_xml(legendsXML, xpath='./regions/*', encoding='CP437')
    lg_xml.set_index('id', inplace=True)


    lgp_xml = pd.read_xml(legendsXMLp, xpath='./regions/*')
    lgp_xml.set_index('id', inplace=True)

    regions = lg_xml.join(lgp_xml)

    regions.name = regions.name.str.title()

    oceanCoords = getCoords(regions[regions['type']=='Ocean']['coords'][0]).transpose()
    frameSize = (oceanCoords[0].min(), oceanCoords[0].max(), oceanCoords[1].min(), oceanCoords[1].max())

    regions['geometry'] = regions['coords'].apply(getPoly, args=(frameSize,))

    del regions['coords']

    #return regions
    return gpd.GeoDataFrame(regions)

def makeRegionsMap():
    biomeColor = {'Ocean':'#2f49ff', 'Hills':'grey', 'Grassland':'lightgreen', 'Wetland':'brown', 'Desert':'yellow', 'Mountains':'black', 'Forest':'darkgreen', 'Tundra':'steelblue', 'Glacier':'white', 'Lake':'lightblue'}


    regions = getRegions()

    center = centroid(regions[regions["type"]=="Ocean"]["geometry"][0])
    center = list(center.coords)[0]
    bounds = regions[regions["type"]=="Ocean"]["geometry"][0].bounds

    base_map = folium.Map(crs='Simple', zoom_start=0, tiles=None, location=center)
    base_map.fit_bounds([[bounds[0],bounds[1]],[bounds[2],bounds[3]]])

    popup = folium.GeoJsonPopup(
        fields=["name", "evilness","type"],
        localize=True,
        labels=True,
        sticky=False,
        style=popUpStyle,
        max_width=400
    )

    mp = folium.GeoJson(data=regions.to_json(),
        style_function=lambda x: {
            "color": "white",
            "weight": 0,
            "dashArray": "5, 5",
            "fillColor": biomeColor[x["properties"]["type"]]
        }, popup=popup)
    mp.add_to(base_map)
    return (base_map, bounds[2])

def sitesNEntities():
    sites = pd.read_xml(legendsXML, xpath='./sites/*', encoding='CP437')
    sites.set_index('id', inplace=True)

    lgp_xml = pd.read_xml(legendsXMLp, xpath='./sites/*')
    lgp_xml.set_index('id', inplace=True)
    lgp_xml.rename(columns={'structures':'structures_plus'}, inplace=True)

    sites = sites.join(lgp_xml)
    del lgp_xml

    entities = pd.read_xml(legendsXML, xpath='./entities/*', encoding='CP437')
    entities.set_index('id', inplace=True)
    
    lgp_xml = pd.read_xml(legendsXMLp, xpath='./entities/*')
    lgp_xml = lgp_xml.filter(['id','race','type'])
    lgp_xml.set_index('id', inplace=True)
    entities = entities.join(lgp_xml)

    sites.name = sites.name.str.title()
    entities.race = entities.race.str.replace('_',' ', regex=True)
    entities.name = entities.name.str.title()
    entities.race = entities.race.str.title()

    return (sites, entities)

def makeSitesMap(xmax):
    # siteIcons = {'camp':'☼', 'cave':'•', 'dark fortress':'Π', 'dark pits': 'º', 'forest retreat': '¶','fortress':'Ω','castle': '○',
    #              'fort': '○','hamlet': '=','hillocks': 'Ω','labyrinth': '#','lair': '•','monastery': '○','mountain halls': 'Ω','ruins': 'μ',
    #              'forest retreat ruins': 'μ','shrine': 'Å','tomb': '0','tower': 'I','town': '+','vault': '■'}
    def sitePopup(name, owner_id, civ_id):
        html = ""
        if isinstance(name,str):
            html += "<h4>%s</h4><br>"%(name)
        else:
            html += "<h4>Unknown</h4><br>"
        if np.isnan(owner_id):
            html += "<b>Unknown owner</b>"
        else:
            html += "<b>"+entities['name'][owner_id]+"</b>"
        if (not np.isnan(civ_id)):
            html += ' from ' + entities['name'][civ_id]
            if isinstance(entities['race'][civ_id],str):
                html += ' (' + entities['race'][civ_id] + ').'
        return html

    sites, entities = sitesNEntities()

    siteLayer = folium.FeatureGroup('Sites', control=True)
    for _, row in sites.iterrows():
        rect = getRectangle(row['rectangle'], xmax)
        folium.Rectangle(bounds=rect, color=None, fill=True, fill_color='#ff0000', fill_opacity=0.2).add_to(siteLayer)
        center = rectangleCenter(rect)
        imgPath = 'imgs/sites/Icon_site_%s.png'%(row.type.replace(' ','_'))
        icon = folium.features.CustomIcon(imgPath, icon_size=(16,16))
        popup = sitePopup(row['name'], row['cur_owner_id'], row['civ_id'])
        folium.Marker(center, tooltip=row['name'], icon=icon, popup=popup).add_to(siteLayer)

    return siteLayer

legendsXML = 'test/region4-00101-02-21-legends.xml'
legendsXMLp = 'test/region4-00101-02-21-legends_plus.xml'

map, xmax = makeRegionsMap()
makeSitesMap(xmax).add_to(map)
map.save("map.html")

