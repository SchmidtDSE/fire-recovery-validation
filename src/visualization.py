import requests
import matplotlib.pyplot as plt
import rasterio as rio
import geopandas as gpd
import numpy as np
from rasterio.warp import calculate_default_transform, reproject, Resampling

from src import config

def get_url_raster(fire_event_name, job_id, metric):
    ''' Retrieves the URL for the specified metric raster from the API result endpoint. '''
    request = requests.get(f"{config.URL_RESULT}/{fire_event_name}/{job_id}")
    urls = request.json().get('coarse_severity_cog_urls')
    return urls.get(metric)

def plot_fire(fire_name, fire_days, fire_polygon, fires):
    ''' Plots dNBR and RBR rasters for a given fire event and post-fire period, with the fire perimeter overlaid. '''
    fire_event_name = fires.loc[(fires['fire_name'] == fire_name) & (fires['post_fire_days'] == fire_days), 'fire_event_name'].values[0]
    job_id = fires.loc[fires['fire_event_name'] == fire_event_name, 'job_id'].values[0]

    dnbr_url = get_url_raster(fire_event_name, job_id, 'dnbr')
    rbr_url = get_url_raster(fire_event_name, job_id, 'rbr')

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

    # Reproject RBR to lat/lon
    with rio.open(rbr_url) as src:
        transform, width, height = calculate_default_transform(
            src.crs, 'EPSG:4326', src.width, src.height, *src.bounds)
        
        rbr_reproj = np.empty((height, width), dtype=src.dtypes[0])
        
        reproject(
            source=rio.band(src, 1),
            destination=rbr_reproj,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs='EPSG:4326',
            resampling=Resampling.bilinear)
        
        rbr_extent = [bounds[0], bounds[2], bounds[1], bounds[3]]

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

    # RBR
    im2 = axes[1].imshow(rbr_reproj, cmap='RdYlGn_r', vmin=vmin, vmax=vmax,
                        extent=rbr_extent, origin='upper', zorder=1)
    fire_polygon.boundary.plot(ax=axes[1], color='cyan', linewidth=2, zorder=2)
    axes[1].set_xlim(rbr_extent[0], rbr_extent[1])
    axes[1].set_ylim(rbr_extent[2], rbr_extent[3])
    axes[1].set_title(f'RBR ({fire_event_name} after {fire_days} days)')
    axes[1].set_xlabel('Longitude')
    axes[1].set_ylabel('Latitude')
    plt.colorbar(im2, ax=axes[1])

    plt.tight_layout()
    plt.show()