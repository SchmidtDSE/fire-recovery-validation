import pandas as pd
import numpy as np
import shapely
import geopandas as gpd
from shapely.validation import make_valid
from shapely.ops import unary_union

def create_bbox(fire_name, fires):
    ''' creates a buffered bounding box around a fire parameter '''
    
    fire = fires[fires['FIRE_NAME'] == fire_name].buffer(250).to_crs(epsg=4326)

    bbox = fire.bounds

    return bbox

def get_fire_date(fire_name, fires):
    ''' gets the alarm (start) date of a fire '''
    print('getting fire date')

    start_date = pd.to_datetime(fires[fires['FIRE_NAME'] == fire_name]['ALARM_DATE'].values[0]).to_datetime64()

    return start_date

def get_cont_date(fire_name, fires):
    ''' gets the containment date of a fire, returns None if missing '''

    raw = fires[fires['FIRE_NAME'] == fire_name]['CONT_DATE'].values[0]

    if pd.isnull(raw):
        return None

    return pd.to_datetime(raw).to_datetime64()

def create_query(fire_name, bbox, date_of_fire, post_fire_range, date_mode='alarm', sensor='sentinel-2'):
    ''' Creates an API query for the bounding box and time period specified.

    date_mode: 'alarm' or 'cont' — recorded in the fire_event_name for downstream tracking.
    sensor: 'sentinel-2' or 'landsat' — selects the satellite source used by the backend.
    '''

    pre_start = date_of_fire - np.timedelta64(21, 'D')
    pre_end = date_of_fire - np.timedelta64(1, 'D')
    post_end = date_of_fire + np.timedelta64(post_fire_range, 'D')

    api_request = {
        "fire_event_name": f"{fire_name}_date{str(date_of_fire).split('T')[0]}_range{post_fire_range}_mode{date_mode}_sensor{sensor}",
        "coarse_geojson": {
            "type": "Polygon",
            "coordinates": [[
                [float(bbox[0]), float(bbox[1])],
                [float(bbox[2]), float(bbox[1])],
                [float(bbox[2]), float(bbox[3])],
                [float(bbox[0]), float(bbox[3])],
                [float(bbox[0]), float(bbox[1])]
            ]]
        },
        "prefire_date_range": [str(pre_start).split('T')[0], str(pre_end).split('T')[0]],
        "postfire_date_range": [str(date_of_fire).split('T')[0], str(post_end).split('T')[0]],
        "sensor": sensor
    }

    return api_request

def append_result(results, fire_name, date_mode, post_fire_days, sensor, status, fire_event_name=None, job_id=None):

    results.append({
        'fire_event_name': fire_event_name,
        'job_id': job_id,
        'fire_name': fire_name,
        'date_mode': date_mode,
        'post_fire_days': post_fire_days,
        'sensor': sensor,
        'status': status
    })
