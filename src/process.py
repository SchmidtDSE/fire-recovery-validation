import requests
import rasterio as rio
import geopandas as gpd
import shapely as shp
import numpy as np
import rioxarray as rxr

from src import config


def lookup_job(fire_name, fire_days, date_mode, sensor, fires):
    ''' Looks up the fire_event_name and job_id for a given fire/day/mode/sensor combination. '''
    row = fires.loc[(fires['fire_name'] == fire_name) &
                    (fires['post_fire_days'] == fire_days) &
                    (fires['date_mode'] == date_mode) &
                    (fires['sensor'] == sensor)]

    fire_event_name = row['fire_event_name'].values[0]
    job_id = row['job_id'].values[0]
    job_status = row['job_status'].values[0]

    if job_status != 'complete':
        raise ValueError(f"Job {fire_event_name} did not complete (job_status='{job_status}')")

    return fire_event_name, job_id

def get_url_raster(fire_event_name, job_id, metric):
    ''' Retrieves the URL for the specified metric raster from the API result endpoint. '''
    request = requests.get(f"{config.URL_RESULT}/{fire_event_name}/{job_id}")
    urls = request.json().get('coarse_severity_cog_urls')
    return urls.get(metric)

def get_raster_as_lonlat(raster_url):
    ''' Retrieves the raster from the URL and reprojects it to EPSG:4326 (lon/lat). Returns the reprojected raster and its extent. '''
    raster = rxr.open_rasterio(raster_url, masked=True)
    raster_reproj = raster.rio.reproject('EPSG:4326')

    array = raster_reproj.values[0]
    bounds = raster_reproj.rio.bounds()  # (left, bottom, right, top)
    extent = [bounds[0], bounds[2], bounds[1], bounds[3]]

    return raster_reproj, extent

def convert_burnscar_to_polygon(raster):
    ''' Filtera raster to pixels with burn index > 0 and converts to a polygon. '''
    raster_filtered = raster.where(raster > 0)

    shapes_gen = list(rio.features.shapes(
        raster_filtered.values[0],
        mask=raster_filtered.notnull().values[0].astype(np.uint8),
        transform=raster_filtered.rio.transform()
    ))

    geoms = [shp.geometry.shape(sh) for sh, _ in shapes_gen]
    dissolved = shp.ops.unary_union(geoms)

    return gpd.GeoDataFrame(geometry=[dissolved], crs=raster_filtered.rio.crs)

def calculate_statistical_indicators(raster, polygon):
    ''' Calculates statistical indicators of burn index across the burn scar '''
    polygon = polygon.to_crs(raster.rio.crs)
    raster_clipped = raster.rio.clip(polygon.geometry, polygon.crs, drop=False)

    raster_filtered = raster.where(abs(raster) <= 1)

    mean = raster_clipped.mean().item()
    var = raster_clipped.var().item()
    max = raster_clipped.max().item()
    min = raster_clipped.min().item()
    q_25, q_50, q_75 = raster_clipped.quantile([0.25, 0.5, 0.75], dim=['x', 'y'], skipna=True)

    return mean, var, max, min, q_25, q_50, q_75

def append_results(fire_name, fire_days, date_mode, sensor, metric,
                   mean, var, max, min, q_25, q_50, q_75,
                   indictators):
    ''' Appends the calculated indicators to the results CSV. '''

    new_row = {
        'fire_name': fire_name,
        'post_fire_days': fire_days,
        'date_mode': date_mode,
        'sensor': sensor,
        'metric': metric,
        'mean': mean,
        'var': var,
        'max': max,
        'min': min,
        'q_25': q_25.item(),
        'q_50': q_50.item(),
        'q_75': q_75.item()
    }
    indictators.append(new_row)

