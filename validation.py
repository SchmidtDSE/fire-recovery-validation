#conda activate burnseverity
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt

import requests
import json

import geopandas as gpd

import rasterio as rio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.mask import mask
from rasterio import features
from rasterio.plot import show_hist

from shapely.geometry import shape, mapping
from shapely.ops import unary_union


def plot_fire(fire_name, fire_days, fire_polygon, fires):

    fire_event_name = fires.loc[(fires['fire_name'] == fire_name) & (fires['post_fire_days'] == fire_days), 'fire_event_name'].values[0]
    job_id = fires.loc[fires['fire_event_name'] == fire_event_name, 'job_id'].values[0]

    request = requests.get(f"https://fire-recovery-backend-dev-113009620257.us-central1.run.app/fire-recovery/result/analyze_fire_severity/{fire_event_name}/{job_id}")
    print(request)
    urls = request.json().get('coarse_severity_cog_urls')
    dnbr_url = urls.get('dnbr')
    rdnbr_url = urls.get('rdnbr')

    # Reproject dNBR to lat/lon
    with rio.open(dnbr_url) as src:
        transform, width, height = calculate_default_transform(
            src.crs, 'EPSG:4326', src.width, src.height, *src.bounds)
        
        dnbr_reproj = np.empty((height, width), dtype=src.dtypes[0])
        
        reproject(
            source=rio.band(src, 1),
            destination=dnbr_reproj,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs='EPSG:4326',
            resampling=Resampling.bilinear)
        
        # Get extent for plotting
        bounds = rio.transform.array_bounds(height, width, transform)
        dnbr_extent = [bounds[0], bounds[2], bounds[1], bounds[3]]  # [left, right, bottom, top]

    # Reproject RdNBR to lat/lon
    with rio.open(rdnbr_url) as src:
        transform, width, height = calculate_default_transform(
            src.crs, 'EPSG:4326', src.width, src.height, *src.bounds)
        
        rdnbr_reproj = np.empty((height, width), dtype=src.dtypes[0])
        
        reproject(
            source=rio.band(src, 1),
            destination=rdnbr_reproj,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs='EPSG:4326',
            resampling=Resampling.bilinear)
        
        rdnbr_extent = [bounds[0], bounds[2], bounds[1], bounds[3]]

    # Plot reprojected rasters with polygon overlay (fixed color scale)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Fixed color scale for comparison across fires
    vmin, vmax = -1, 1

    # dNBR
    im1 = axes[0].imshow(dnbr_reproj, cmap='RdYlGn_r', vmin=vmin, vmax=vmax, 
                        extent=dnbr_extent, origin='upper', zorder=1)
    fire_polygon.boundary.plot(ax=axes[0], color='cyan', linewidth=2, zorder=2)
    axes[0].set_xlim(dnbr_extent[0], dnbr_extent[1])
    axes[0].set_ylim(dnbr_extent[2], dnbr_extent[3])
    axes[0].set_title(f'dNBR ({fire_event_name})')
    axes[0].set_xlabel('Longitude')
    axes[0].set_ylabel('Latitude')
    plt.colorbar(im1, ax=axes[0])

    # RdNBR
    im2 = axes[1].imshow(rdnbr_reproj, cmap='RdYlGn_r', vmin=vmin, vmax=vmax,
                        extent=rdnbr_extent, origin='upper', zorder=1)
    fire_polygon.boundary.plot(ax=axes[1], color='cyan', linewidth=2, zorder=2)
    axes[1].set_xlim(rdnbr_extent[0], rdnbr_extent[1])
    axes[1].set_ylim(rdnbr_extent[2], rdnbr_extent[3])
    axes[1].set_title(f'RdNBR ({fire_event_name} after {fire_days} days)')
    axes[1].set_xlabel('Longitude')
    axes[1].set_ylabel('Latitude')
    plt.colorbar(im2, ax=axes[1])

    plt.tight_layout()
    plt.show()


def process_fire_metrics(fire_name, fire_days, fires, calfire):
    """
    Process fire severity metrics for a given fire and post-fire days.
    
    Returns:
    - list of dicts (one per metric: dnbr, rdnbr), or False if job not complete/error
    """
    
    # Get fire_event_name and job_id
    fire_rows = fires.loc[(fires['fire_name'] == fire_name) & (fires['post_fire_days'] == fire_days)]
    if len(fire_rows) == 0:
        print(f"  Warning: No job found for {fire_name} at {fire_days} days")
        return False
    
    fire_event_name = fire_rows['fire_event_name'].values[0]
    job_id = fire_rows['job_id'].values[0]
    
    # Get fire polygon
    fire_polygon = calfire[calfire['FIRE_NAME'] == fire_name]
    if len(fire_polygon) == 0:
        print(f"  Warning: No CalFire boundary found for {fire_name}")
        return False
    
    # Get URLs from API
    try:
        request = requests.get(f"https://fire-recovery-backend-dev-113009620257.us-central1.run.app/fire-recovery/result/analyze_fire_severity/{fire_event_name}/{job_id}")
        response_data = request.json()
        
        if response_data.get('status') != 'complete':
            print(f"  Job {fire_event_name} is {response_data.get('status')}")
            return False
        
        urls = response_data.get('coarse_severity_cog_urls')
        dnbr_url = urls.get('dnbr')
        rdnbr_url = urls.get('rdnbr')
    except Exception as e:
        print(f"  Error fetching URLs: {e}")
        return False
    
    # Store results - one row per metric
    results = []
    
    # Process both dNBR and RdNBR
    for metric_name, metric_url in [('dnbr', dnbr_url), ('rdnbr', rdnbr_url)]:
        try:
            with rio.open(metric_url) as src:
                # Reproject fire polygon to raster CRS
                fire_poly_reproj = fire_polygon.to_crs(src.crs)
                
                # Crop to CalFire boundary
                geoms = [mapping(geom) for geom in fire_poly_reproj.geometry]
                cropped, cropped_transform = mask(src, geoms, crop=True, nodata=np.nan)
                cropped_data = cropped[0]
                
                # Remove nodata values
                valid_data = cropped_data[~np.isnan(cropped_data)]
                
                # CalFire metrics (all pixels in boundary)
                # Filter out pixels with abs(x) > 1
                calfire_total = len(valid_data)
                calfire_data_filtered = valid_data[np.abs(valid_data) <= 1]
                calfire_n_removed = calfire_total - len(calfire_data_filtered)
                calfire_pct_removed = (calfire_n_removed / calfire_total * 100) if calfire_total > 0 else 0
                
                calfire_mean = np.mean(calfire_data_filtered) if len(calfire_data_filtered) > 0 else np.nan
                calfire_var = np.var(calfire_data_filtered) if len(calfire_data_filtered) > 0 else np.nan
                
                # Filtered metrics (pixels > 0)
                # First filter to pixels > 0, then filter out abs(x) > 1
                filtered_positive = valid_data[valid_data > 0]
                filtered_total = len(filtered_positive)
                filtered_data = filtered_positive[np.abs(filtered_positive) <= 1]
                filtered_n_removed = filtered_total - len(filtered_data)
                filtered_pct_removed = (filtered_n_removed / filtered_total * 100) if filtered_total > 0 else 0
                
                filtered_mean = np.mean(filtered_data) if len(filtered_data) > 0 else np.nan
                filtered_var = np.var(filtered_data) if len(filtered_data) > 0 else np.nan
                
                # Create polygon from filtered pixels (pixels > 0)
                filtered_mask = cropped_data > 0
                shapes_gen = features.shapes(
                    filtered_mask.astype(np.int16),
                    mask=filtered_mask,
                    transform=cropped_transform
                )
                
                # Combine all polygons
                filtered_polygons = [shape(geom) for geom, val in shapes_gen if val == 1]
                
                if len(filtered_polygons) > 0:
                    filtered_polygon = unary_union(filtered_polygons)
                    filtered_gdf = gpd.GeoDataFrame([1], geometry=[filtered_polygon], crs=src.crs)
                    filtered_gdf_latlon = filtered_gdf.to_crs('EPSG:4326')
                    filtered_polygon_latlon = filtered_gdf_latlon.geometry.values[0]
                else:
                    filtered_polygon_latlon = None
                
                # Append row for this metric
                results.append({
                    'fire_name': fire_name,
                    'fire_days': fire_days,
                    'fire_event_name': fire_event_name,
                    'metric': metric_name,
                    'calfire_mean': calfire_mean,
                    'calfire_var': calfire_var,
                    'calfire_n_removed': calfire_n_removed,
                    'calfire_pct_removed': calfire_pct_removed,
                    'filtered_mean': filtered_mean,
                    'filtered_var': filtered_var,
                    'filtered_n_removed': filtered_n_removed,
                    'filtered_pct_removed': filtered_pct_removed,
                    'filtered_polygon': filtered_polygon_latlon
                })
                
        except Exception as e:
            print(f"  Error processing {metric_name}: {e}")
            return False
    
    return results