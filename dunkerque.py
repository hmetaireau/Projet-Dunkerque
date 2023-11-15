from flask import Flask, render_template
from bokeh.models import LinearAxis, HoverTool
from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.resources import INLINE
from bokeh.models import ColumnDataSource, DatetimeTickFormatter, LinearAxis, Range1d,DatetimeTicker
from bokeh.transform import factor_cmap
import bokeh.palettes as bp
import pandas as pd
import json
import folium
from folium import plugins
from shapely.geometry import Point, Polygon
import numpy as np
import geopandas as gpd
from folium.features import GeoJsonPopup as mi
import matplotlib.dates as mdates


# GRAPHIQUE DONNÉES MÉTÉO

def create_graph_weather():
    
    # Importation du jeu de données weather
    data_weather = pd.read_excel('Donnees_carte.xlsx', sheet_name='meteo_graphique')
    
    data_weather.columns = ["dates", "wind_speed", "waves"] # Changement du nom des colonnes
        
    # Source de données Bokeh
    source = ColumnDataSource(data=dict(dates=data_weather['dates'],
                                        wind_speed=data_weather['wind_speed'],
                                        waves=data_weather['waves']))
    
    # Créer le graphique
    p = figure(height=500,width=700, x_axis_type="datetime")
    p.xaxis.major_label_orientation = "horizontal"
    
    # Ajout outil Hover
    hover = HoverTool(
        tooltips=[
            ("Date", "@dates{%F %H:%M}"),
            ("Vitesse du Vent", "@wind_speed{0.2f} km/h"),
            ("Hauteur des vagues", "@waves{0.2f} m")
        ],
        formatters={
            "@dates": "datetime", 
        },
        mode='vline',  # Afficher les informations uniquement à la position verticale de la souris
        renderers=[p.line(x='dates', y='wind_speed', line_width=2, line_color='blue', legend_label='Vitesse du Vent (km/h)', source=source)]  # spécifier le rendu de la ligne "Vitesse du Vent"

    )
    
    p.add_tools(hover)
    
    
    # Ligne de la vitesse du vent
    p.line(x='dates', y='wind_speed', line_width=2, line_color='blue', legend_label='Vitesse du Vent (km/h)', source=source)
    p.yaxis.axis_label = "Vitesse du Vent (km/h)"
    

    # Ligne de la hauteur des vagues
    p.line(x='dates', y='waves', line_width=2, line_color='red', legend_label='Hauteur des vagues (m)', source=source, y_range_name="foo")
    p.extra_y_ranges = {"foo": Range1d(start=-0, end=2)}
    p.add_layout(LinearAxis(y_range_name="foo", axis_label="Hauteur des vagues (m)"), 'right')
    
    
    p.xgrid.grid_line_color = None
    p.y_range.start = 0
    p.legend.orientation = "horizontal"
    p.legend.location = "top_center"
    p.xaxis.formatter = DatetimeTickFormatter(days="%b %d", hours="%H:%M") 
    
    return p


# CARTE DU CAMP

def create_map_camp():
    
    ## Load data from ressources
    
    with open('ressources/Camp.geojson') as fCamps:
        dataCamps = json.load(fCamps)
    
    with open('ressources/communautes_T1.geojson') as fCom1:
        dataCom1 = json.load(fCom1)
    
    with open('ressources/communautes_T2.geojson') as fCom2:
        dataCom2 = json.load(fCom2)
        
    with open('ressources/Try_game.geojson') as fGame:
        dataGame = json.load(fGame)
        
    print(dataCom1)#dictionary of features
    print(dataCom2)#dictionary of features
    
    #version 2 : read a geodataframe with geopandas
    geodataCom1 = gpd.read_file('ressources/communautes_T1.geojson', encoding='utf-8')
    geodataCom2 = gpd.read_file('ressources/communautes_T2.geojson', encoding='utf-8')
    
    print(geodataCom1.shape) #(15, 3)
    print(geodataCom2.shape) #(18, 1)
    
    #Global parameters to be set through a Web interface 
    periode = 'T1'
    day = 7
    
    #Centre du code
    m = folium.Map(location=[51.000766, 2.256553], zoom_start=15)
    
    folium.TileLayer(tiles='OpenStreetMap').add_to(m)
    #folium.TileLayer(tiles='Stamen Terrain').add_to(m)
    #folium.TileLayer(tiles='Stamen Toner').add_to(m)
    folium.TileLayer(tiles='Ma BDTopo', attr='https://wxs.ign.fr/topographie/geoportail/tms/1.0.0/BDTOPO/{z}/{x}/{y}.pbf').add_to(m)
    
    
    def function_get_human_points(dataCom):
        '''Code using a dictionary of features in parameter,
        old fashion withou geopandas - DEPRECATED
        '''
        # List to store all points to put inside polygones
        all_human_points = []
    
        # wihout GeoDataFrame
        # Itérate on the dictionnary of features given in parameter 
        for feature in dataCom['features']:
            if feature['geometry']['type'] == 'Polygon':
                # Polygon Coordinates 
                polygon_coordinates = feature['geometry']['coordinates'][0]
                
                # Create thr Polygon object
                polygon = Polygon(polygon_coordinates)
                            
                #Get bounds of the polygon
                minx, miny, maxx, maxy = polygon.bounds
                
                # Number of points to generate
                num_points = 50  
                # Change here : total number of points is proportional to camps size, and number of points per feature is proportional to the area of the feature. 
                
                # Points inside the current polygon
                human_points = []
                # Generate randomly points inside the bounding box of the current polygon
                while len(human_points) < num_points:
                    point = Point(minx + (maxx - minx) * np.random.random(), miny + (maxy - miny) * np.random.random())
                    if polygon.contains(point):
                        human_points.append(point)
                
                # Add those points to the result 
                all_human_points.extend(human_points)
        return all_human_points
    
    def function_get_human_points_from_geo(dataCom):
        '''With GeoPandas and a GeoDataFrame in parameter
        return a list of points to put inside polygons
        
        Note : 
        - number of points should be a parameter related to the total number of points is proportional to camps size
        - total number of points should be proportional to camps size, given in parameter
        - number of points per feature could be proportional to the area of the feature.
        - polygones could be dilated/contracted according the "normal" size of the camp (take the average)
        '''
        
        # List to store all points to put inside polygones
        all_human_points = []
    
        # wihout GeoDataFrame
        # Itérate on the dictionnary of features given in parameter 
        for index, row in dataCom.iterrows():
            polygon = row['geometry']
            
            #Get bounds of the polygon
            minx, miny, maxx, maxy = polygon.bounds
                
            # Number of points to generate
            num_points = 50  
            # Change here : total number of points is proportional to camps size, and number of points per feature is proportional to the area of the feature. 
            
            # Points inside the current polygon
            human_points = []
            # Generate randomly points inside the bounding box of the current polygon
            while len(human_points) < num_points:
                point = Point(minx + (maxx - minx) * np.random.random(), miny + (maxy - miny) * np.random.random())
                if polygon.contains(point):
                    human_points.append(point)
            
            # Add those points to the result 
            all_human_points.extend(human_points)
        return all_human_points
    
    function_get_human_points_from_geo(geodataCom2)
    
    
    #Style Polygon for distro zones
    def polygon_style(feature):
        return {
            "fillColor": "green",
            "color": "black",
            "weight": 2,
            "fillOpacity": 0.5
        }
    #Style polygones T1
    def polygon_style2(feature):
        return {
            "fillColor": "cyan",
            "color": "black",
            "weight": 2,
            "fillOpacity": 0.5
        }
    #Style polygones T2
    def polygon_style3(feature):
        return {
            "fillColor": "pink",
            "color": "black",
            "weight": 2,
            "fillOpacity": 0.5
        }
        
    #Points for distro zones in camp
    folium.GeoJson(dataCamps, 
        name="Camps",
        marker = folium.Marker(
            icon=folium.Icon(
                icon_color='black',icon='fa-solid fa-tents',color="green",prefix='fa'
        )),
        style_function=polygon_style,
        popup=mi(
            fields=['name', 'description'],
            aliases=['Nom', 'Description'],
            labels=True,
            style='width: 200px;',
            sticky=False
            )
        ).add_to(m)
    
    
    #Select polygons matching the period
    if periode == 'T1':
        #dataCom = dataCom1
        dataCom = geodataCom1
    else : 
        #dataCom = dataCom2
        dataCom = geodataCom2
    
    #Polygones for communauties
    if periode == 'T1':
        folium.GeoJson(geodataCom1, 
                    name="Communauté T1",
                    style_function=polygon_style2,
                    tooltip="Communauté T1"
            ).add_to(m)
    else:
        folium.GeoJson(geodataCom2, 
            name="Communauté T2",
            style_function=polygon_style3,
            tooltip="Communauté T2"
            ).add_to(m)
    
    #Add game enclosure
    folium.GeoJson(dataGame,
        name='Game',
        tooltip='Game',
        marker = folium.Marker(
            icon=folium.Icon(
                icon_color='black',icon='fa-solid fa-gamepad',color="beige",prefix='fa'
            )),
        popup=mi(
            fields=['name', 'description'],
            aliases=['Nom', 'Description'],
            labels=True,
            style='width: 350px;',
            sticky=False
        )
    ).add_to(m)
    
    # Create humans points inside T1/T2 polygons of communauties
    if type(dataCom).__name__ == 'GeoDataFrame' : 
        all_human_points = function_get_human_points_from_geo(dataCom)
    else : 
        all_human_points = function_get_human_points(dataCom)
        
    # Add all humans like circles to Folium map
    if day%2 == 0 :
        #day even
        print('even day '+str(day)+' during period: '+periode)
        fill_color_param = 'blue'
    else : 
        #odd day
        print('odd day '+str(day)+' during period: '+periode)
        fill_color_param = 'red'
        
    for point in all_human_points:
        folium.CircleMarker(location=[point.y, point.x], radius=1, color=fill_color_param, fill=True, fill_color=fill_color_param).add_to(m)
    
    # Add a control to select tiles layers
    folium.LayerControl().add_to(m)
    
    return m

    
# CARTE LITTORAL

def create_map_lit():

   
    #Récupérage des données
    with open('ressources/arret_bus_camp.geojson') as fArretDeBus:
        dataArretDeBus = json.load(fArretDeBus)
    
    with open('ressources/arrivees_region.geojson') as fArriveesRegions:
        dataArriveesRegions = json.load(fArriveesRegions)
    
    with open('ressources/CRA_coquelles.geojson') as fCoquelles:
        dataCoquelles = json.load(fCoquelles)
    
    with open('ressources/depart_arrivee_camps.geojson') as fDepartsArrivees:
        dataDepartsArrivees = json.load(fDepartsArrivees)
    
    with open('ressources/emprise_2154_ok_buffer5.geojson') as fEmprise:
        dataEmprise = json.load(fEmprise)
    
    with open('ressources/Try_bateau_commune.geojson') as fBateau:
        dataBateau = json.load(fBateau)
        
    #Centre du code
    m2 = folium.Map(location=[51.000766, 2.256553], zoom_start=10)
    
    folium.TileLayer(tiles='OpenStreetMap').add_to(m2)
    folium.TileLayer(tiles='Stamen Terrain').add_to(m2)
    folium.TileLayer(tiles='Stamen Toner').add_to(m2)
    folium.TileLayer(tiles='Ma BDTopo', attr='https://wxs.ign.fr/topographie/geoportail/tms/1.0.0/BDTOPO/{z}/{x}/{y}.pbf').add_to(m2)
    # Ajouter un contrôle de couches pour sélectionner les tuiles

    #Points pour les arrêts de bus
    folium.GeoJson(dataArretDeBus, 
        name="Arrets de bus",
        marker = folium.Marker(
            icon=folium.Icon(
                icon_color='black',icon='fa-solid fa-bus',color="white",prefix='fa'
        )),
        popup=mi(
            fields=['accessible', 'nom_arret','desserte',],
            aliases=['Accessibilitée', 'Nom', 'Dessertes'],
            labels=True,
            style='width: 200px;',
            sticky=False
            )
        ).add_to(m2)
    
    #Points pour les arrivees regions, point d'arrivées vers le camps.
    folium.GeoJson(dataArriveesRegions,
        name="Arrivées Régions",
        marker = folium.Marker(
            icon=folium.Icon(
                icon_color='black',icon='fa-solid fa-map-pin',color="darkblue",prefix='fa'
        )),
        popup=mi(
            fields=['name', 'description'],
            aliases=['Nom', 'Description'],
            labels=True,
            style='width: 200px;',
            sticky=False
            )
        ).add_to(m2)
    
    #Point destinations des mises à l'abri
    folium.GeoJson(dataCoquelles, 
        name='Coquelles',
        marker = folium.Marker(
            icon=folium.Icon(
                icon_color='black',icon='fa-solid fa-city',color="darkpurple",prefix='fa',
        )),
        
        ).add_to(m2)
    
    #Departs arrivées : point de depart/arrivée situé au camp
    folium.GeoJson(dataDepartsArrivees, 
        tooltip='Départs Arrivées',
        name='Depart arrivees',
        marker = folium.Marker(
            icon=folium.Icon(
                icon_color='black',icon='fa-solid fa-map',color="cadetblue",prefix='fa'
            )),
        popup=mi(
            fields=['name', 'description'],
            aliases=['Nom', 'Description'],
            labels=True,
            style='width: 200px;',
            sticky=False
            )
    ).add_to(m2)
    
    #cadre de la carte 2 permettant de déterminer le niveau de zoom - le seul en projection 2154 (lambert 93)
    folium.GeoJson(dataEmprise, 
        name='Depart arrivees',
        marker = folium.Marker(
            icon=folium.Icon(
                icon_color='black',icon='fa-solid fa-man',color="cadetblue",prefix='fa'
            )),
    
    ).add_to(m2)
    
    #Bateaux point des départs vers l'angleterre : 
    # fleche courte, orientée avec Douvres (en angleterre) d'épaisseur proportionnelle à la commune du point (Boulogne, Calais, Dunkerque ou ...) / arrivees_UK
    
    for feature in dataBateau['features']:
        # Récupérer les coordonnées du point
        lon, lat = feature['geometry']['coordinates']
        
        # Créer une ligne droite vers le nord
        arrow = plugins.AntPath(
            locations=[[lat, lon], [lat+0.25, lon-0.4]],
            color='red', weight=2, dash_array=[10, 20], pulse_color='yellow'
        ).add_to(m2)
    
    folium.GeoJson(dataBateau,
        name='Bateau',
        tooltip='Bateau',
        marker = folium.Marker(
            icon=folium.Icon(
                icon_color='black',icon='fa-solid fa-ship',color="blue",prefix='fa'
            )),
        popup=mi(
            fields=['commune'],
            aliases=['Commune'],
            labels=True,
            style='width: 300px!important;',
            sticky=False
        )
    ).add_to(m2)
    
    
    
    features = dataBateau['features']
    
    # Add markers for each point
    for feature in features:
        coords = feature['geometry']['coordinates']
        commune = feature['properties']['commune']
        folium.Marker(
            location=coords,
            popup=commune,
            icon=folium.Icon(icon="circle"),
        ).add_to(m2)
    
    # Create lines with arrow markers between the points
    for i in range(len(features) - 1):
        start_coords = features[i]['geometry']['coordinates']
        end_coords = features[i + 1]['geometry']['coordinates']
        folium.PolyLine(
            locations=[start_coords, end_coords],
            color="blue",
            weight=2,
            tooltip=f"Ligne de {features[i]['properties']['commune']} à {features[i+1]['properties']['commune']}",
            markers=[
                folium.Marker(location=end_coords, icon=folium.Icon(icon="arrow", prefix="fa"))
            ],
        ).add_to(m2)
    
    
    folium.LayerControl().add_to(m2)
    
    return m2
    
app = Flask(__name__)

# grab the static resources
js_resources = INLINE.render_js()
css_resources = INLINE.render_css()

@app.route('/dunkerque')
def combined_page():
    
    p = create_graph_weather()
    m = create_map_camp()
    m2 = create_map_lit()

    p_script, p_div = components(p)
    m_html = m._repr_html_()
    m2_html = m2._repr_html_()

    return render_template('dunkerque.html', 
                           p_script=p_script,
                           p_div=p_div,
                           m_html=m_html,
                           m2_html=m2_html,
                           js_resources=js_resources,
                           css_resources=css_resources
                           )

if __name__ == '__main__':
    app.run(debug=True, port=5050)
