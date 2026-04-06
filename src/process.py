import requests
import rasterio as rio
import geopandas as gpd
import numpy as np
import rioxarray as rxr

from src import config


def get_url_raster(fires, fire_name, fire_days, date_mode, metric,):
    ''' Retrieves the URL for the specified metric raster from the API result endpoint. '''
    fire_event_name = fires.loc[(fires['fire_name'] == fire_name) & (fires['post_fire_days'] == fire_days), 'fire_event_name'].values[0]
    job_id = fires.loc[fires['fire_event_name'] == fire_event_name, 'job_id'].values[0]
    request = requests.get(f"{config.URL_RESULT}/{fire_event_name}/{job_id}")
    urls = request.json().get('coarse_severity_cog_urls')
    return urls.get(metric)

def get_raster_as_lonlat(raster_url):

    raster = rxr.open_rasterio(raster_url, masked=True)
    raster_reproj = raster.rio.reproject('EPSG:4326')

    array = raster_reproj.values[0]
    bounds = raster_reproj.rio.bounds()  # (left, bottom, right, top)
    extent = [bounds[0], bounds[2], bounds[1], bounds[3]]

    return raster_reproj, extent

def crop_to_calfire(raster, polygon):

    return

