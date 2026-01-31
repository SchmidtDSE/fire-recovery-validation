def plot_fire(fire_event_name):
    urls = test.json().get('coarse_severity_cog_urls')
    dnbr_url = urls.get('dnbr')
    rdnbr_url = urls.get('rdnbr')

    fire_polygon = calfire[calfire['FIRE_NAME'] == 'COFFEE POT'].to_crs(epsg=4326)

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
    axes[0].set_title('dNBR (fixed scale -1 to 1)')
    axes[0].set_xlabel('Longitude')
    axes[0].set_ylabel('Latitude')
    plt.colorbar(im1, ax=axes[0])

    # RdNBR
    im2 = axes[1].imshow(rdnbr_reproj, cmap='RdYlGn_r', vmin=vmin, vmax=vmax,
                        extent=rdnbr_extent, origin='upper', zorder=1)
    fire_polygon.boundary.plot(ax=axes[1], color='cyan', linewidth=2, zorder=2)
    axes[1].set_xlim(rdnbr_extent[0], rdnbr_extent[1])
    axes[1].set_ylim(rdnbr_extent[2], rdnbr_extent[3])
    axes[1].set_title('RdNBR (fixed scale -1 to 1)')
    axes[1].set_xlabel('Longitude')
    axes[1].set_ylabel('Latitude')
    plt.colorbar(im2, ax=axes[1])

    plt.tight_layout()
    plt.show()