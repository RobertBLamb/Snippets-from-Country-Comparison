from django.shortcuts import render
import folium
from .forms import MetricsToTrack
import geopandas as gpd
import mysql.connector
from django.views import View
import os


class map(View):
    def __init__(self):   
        # log into database
        self.db = mysql.connector.connect(
            host = os.environ.get('db_host'),
            user = os.environ.get('db_user'),
            password = os.environ.get('db_password'),
            database ='world_comparison'
        )

        self.cursor = self.db.cursor()  
        # countries to have an alt color
        self.qualifing_countries = set()
        self.tool_tips = ['ADMIN']
        self.tool_tip_labels = ['Country:']

        self.tool_tip_label_key = {
            'population': 'Population:', 'population_growth': 'Annual Population Growth:', 'country_land_area': 'Land Area in Km:', 
            'population_density': 'Population per Km:', 'tree_per_km': 'Number of Trees per Km', 'traffic_deaths_per_100k': 'Traffic Deaths per 100k People:', 
            'car_ownership_rate': 'Car ownership Rate:', 'unemployment_rate': 'Unemployment Percentage', 'suicide_rate': 'Suicide Rate:',
            'life_expectancy':'Life Expectancy:', 'obesity':'Obesity Rate:', 'guaranteed_leave':'Days off per Year:', 'annual_work_hours':'Hours Worked per Year:',
            'wealth_inequality':'Gini Index(Inequality index):'
        }
        self.geoJson_df = gpd.read_file('countries.geojson')
        self.geoJson_df = self.geoJson_df.sort_values('ADMIN')



    def get(self, request):
        forms = MetricsToTrack()
        self.cursor.close()    
        m = self.make_map()
                
        context = {
            'm': m,
            'form': forms, 
        }

        return render(request, 'index.html', context)


    def post(self, request):
        forms = MetricsToTrack(request.POST)
        if forms.is_valid():
            # adjust value(s) from what was input
            forms = self.adjust_form_values(forms)

            # cleaned_data shows the form results, not the countries
            query_builder = "SELECT country_name FROM world_data "
            first_parameter = True

            # TODO: this code is bad and I should feel bad, rework once prototype is finished
            # this is checking the variable names, if variable is the same as the db entry it works
            for name in forms.cleaned_data:
                if name[-4:] != "_Mod" and forms.data[name]:

                    # add searched variable to geojson doc
                    self.tool_tips.append(name)
                    self.tool_tip_labels.append(self.tool_tip_label_key[name])

                    sign = name + "_Mod"

                    if first_parameter:
                        first_parameter = False
                        query_builder += (
                                "WHERE " + str(name) + str(forms[sign].value()) + str(forms[name].value()))
                    else:
                        query_builder += (
                            " and " + str(name) + str(forms[sign].value()) + str(forms[name].value()))
            
            self.cursor.execute(query_builder)
            for country in self.cursor:
                self.qualifing_countries.add(str(country)[2:-3])  

        m = self.make_map()

        context = {
            'm': m,
            'form': forms, 
        }
        return render(request, 'index.html', context)
 
    def adjust_form_values(self, forms):
        if forms.cleaned_data['wealth_inequality']:
            forms.cleaned_data['wealth_inequality'] /= 100
        return forms

    def make_map(self):
        # create map object
        # TODO: create darkmode using 'CartoDB dark_matter' as map background
        m = folium.Map(location=[0,0],zoom_start=2, tiles='CartoDB positron',max_bounds=True, min_zoom=1.5, max_zoom=6)
        Style_function = lambda x: {
                                    'fillOpacity': .5 if x['properties']['ADMIN'] in self.qualifing_countries else .1,
                                    'fillColor': '#591ee1' if x['properties']['ADMIN'] in self.qualifing_countries else '#1be4d9',
                                    'weight': 1
                                    }
       
       # get values for all countries
        for i in range(1, len(self.tool_tips)):
            query = "SELECT {} FROM world_data ".format(self.tool_tips[i])
            self.cursor.execute(query)
            country_value = []

            for country in self.cursor:
                country_value.append(str(country)[1:-2])  
            
            self.geoJson_df[self.tool_tips[i]] = country_value

        self.cursor.close()


        folium.GeoJson(
            self.geoJson_df, 
            name='geoJson',
            style_function=Style_function, 
            tooltip=folium.GeoJsonTooltip(
                fields= self.tool_tips, 
                aliases= self.tool_tip_labels, 
                sticky=True),
                show=True
            ).add_to(m)
        
        m = m._repr_html_()
        return m

