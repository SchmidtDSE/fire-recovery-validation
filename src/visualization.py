import requests
import matplotlib.pyplot as plt
import rasterio as rio
import geopandas as gpd
import numpy as np
from rasterio.warp import calculate_default_transform, reproject, Resampling

from src import config
from src import process


def plot_fire(fire_name, fire_days, fire_polygon, fires):
    ''' Plots dNBR and RBR rasters for a given fire event and post-fire period, with the fire perimeter overlaid. '''

    dnbr_url = process.get_url_raster(fires, fire_name, fire_days, date_mode = 'alarm', metric = 'dnbr')
    rbr_url = process.get_url_raster(fires, fire_name, fire_days, date_mode = 'alarm', metric = 'rbr')

    dnbr_reproj, dnbr_extent = process.get_raster_as_lonlat(dnbr_url)
    rbr_reproj, rbr_extent = process.get_raster_as_lonlat(rbr_url)

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
    axes[0].set_title(f'dNBR ({fire_name} after {fire_days} days)')
    axes[0].set_xlabel('Longitude')
    axes[0].set_ylabel('Latitude')
    plt.colorbar(im1, ax=axes[0])

    # RBR
    im2 = axes[1].imshow(rbr_reproj, cmap='RdYlGn_r', vmin=vmin, vmax=vmax,
                        extent=rbr_extent, origin='upper', zorder=1)
    fire_polygon.boundary.plot(ax=axes[1], color='cyan', linewidth=2, zorder=2)
    axes[1].set_xlim(rbr_extent[0], rbr_extent[1])
    axes[1].set_ylim(rbr_extent[2], rbr_extent[3])
    axes[1].set_title(f'RBR ({fire_name} after {fire_days} days)')
    axes[1].set_xlabel('Longitude')
    axes[1].set_ylabel('Latitude')
    plt.colorbar(im2, ax=axes[1])

    plt.tight_layout()
    plt.show()