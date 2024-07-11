import numpy as np
import datetime
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import pandas as pd
import argparse
from pychmirad import ChmiRad
import io
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.animation import FFMpegWriter
from matplotlib.gridspec import GridSpec
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from tqdm import tqdm

# Function to clean non-numeric characters from strings
def clean_data(value):
    try:
        return float(value)
    except ValueError:
        return np.nan  # or you can use a default value like 0

def ptp_orient(array):
    ret = []
    for arr in array:
        min_val = np.min(arr)
        max_val = np.max(arr)
        
        min_idx = np.argmin(arr)
        max_idx = np.argmax(arr)
    
        if min_idx < max_idx:
            ret.append(max_val - min_val)
        else:
            ret.append(min_val - max_val)
    return ret

def main(file_path, center_lat, center_lon, save_mp4=False):
    # Load CSV file
    data = []
    with open(file_path, 'r') as file:
        for line in file:
            data.append(line.strip().split(','))

    dates = np.array([int(float(x[0])) for x in data])
    adc_values = [x[1:] for x in data]
    max_length = max(len(sublist) for sublist in adc_values)
    adc_values = [sublist + [255]*(max_length - len(sublist)) for sublist in adc_values]
    adc_values = np.array([[clean_data(value) for value in sublist] for sublist in adc_values])

    angles = np.linspace(0, 180, max_length)
    values = adc_values - 255

    p2p = ptp_orient(values)
    angle_index = np.argmax(values, axis=1) / max_length

    window_size = 20
    smoothed_angle_index = np.convolve(angle_index, np.ones(window_size) / window_size, mode='same')
    smoothed_p2p = np.convolve(p2p, np.ones(window_size) / window_size, mode='same')

    strmy_pokles = np.where(np.diff(p2p) < -10)
    strmy_pokles_casy = dates[strmy_pokles]

    # Initialize radar data visualizer
    rad_view = ChmiRad()

    # Download radar data for the entire range of dates
    start_datetime = datetime.datetime.utcfromtimestamp(dates[0])
    end_datetime = datetime.datetime.utcfromtimestamp(dates[-1])
    rad_view.download_data_range(start_datetime, end_datetime, interval_minutes=10)

    # Create a figure and axis for plotting
    fig = plt.figure(figsize=(16, 9))
    gs = GridSpec(3, 2, height_ratios=[1, 1, 2], figure=fig)

    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1:, :], projection=ccrs.PlateCarree())

    cbar_ax = fig.add_axes([0.95, 0.1, 0.02, 0.5])  # Position for the colorbar

    # Set dark background for the map
    ax3.set_facecolor('black')

    # Variable to keep track of the last radar data timestamp
    last_radar_data_datetime = None


    pbar = tqdm(total=len(p2p), desc="Processing")


    def update(i):
        print(i/10)
        pbar.update(i/10)

        nonlocal last_radar_data_datetime


        
        timestamp = dates[i]
        timestamp_datetime = datetime.datetime.utcfromtimestamp(timestamp)
        
        ax1.clear()
        ax2.clear()
        
        # Plot peak-to-peak amplitude over time
        ax1.plot(dates, p2p, ".", color='blue', alpha=0.1, label='Peak-to-peak amplitude')
        ax1.plot(dates, smoothed_p2p, color='blue', alpha=0.5, lw=2, label='Peak-to-peak amplitude, rolling mean')
        ax1.set_ylabel('Peak-to-peak amplitude - relative [kV/m]', color='blue')
        ax1.set_ylim(-255 * 2, 255 * 2)
        ax1.grid()
        ax1.legend()
        
        # Add a cursor showing the current time
        ax1.axvline(x=timestamp, color='red', linestyle='--', label='Current time')
        
        # Plot individual row from CSV file as polar plot
        ax2.plot(angles, values[i], label=f'Time: {timestamp_datetime}')
        ax2.set_ylim(-255, 255)
        ax2.grid()
        ax2.legend()
        
        # Plot radar data only if it has changed
        data_datetime = rad_view.round_down_to_nearest_five(timestamp_datetime)
        if data_datetime != last_radar_data_datetime:
            ax3.clear()
            last_radar_data_datetime = data_datetime
            
            if data_datetime not in rad_view.data_dict:
                print(f"Data for {data_datetime} not found, downloading...")
                rad_view.download_data(data_datetime)
            
            radar_data = rad_view.data_dict[data_datetime]
            extent = [rad_view.longitudes.min(), rad_view.longitudes.max(), rad_view.latitudes.min(), rad_view.latitudes.max()]
            
            ax3.add_feature(cfeature.BORDERS)
            ax3.add_feature(cfeature.COASTLINE)
            ax3.add_feature(cfeature.LAKES, alpha=0.5)
            ax3.add_feature(cfeature.RIVERS)
            
            # Add cities and highways
            ax3.add_feature(cfeature.NaturalEarthFeature('cultural', 'admin_1_states_provinces_lines', '10m', edgecolor='gray', facecolor='none'))
            ax3.add_feature(cfeature.NaturalEarthFeature('cultural', 'urban_areas', '10m', edgecolor='dimgray', facecolor='dimgray', alpha=0.5))
            ax3.add_feature(cfeature.NaturalEarthFeature('cultural', 'roads', '10m', edgecolor='grey', facecolor='none'))

            #radar_data[radar_data < 50] = np.nan
            radar_data = np.ma.masked_where(radar_data < 50, radar_data)
            im = ax3.imshow(radar_data, extent=extent, origin='upper', cmap='gist_ncar', transform=ccrs.PlateCarree(), alpha=0.7, vmin=0)
            
            #ax3.scatter(center_lon, center_lat, color='red', marker='o', label='Center', transform=ccrs.PlateCarree())
            
            # Add cross at the center coordinates
            ax3.plot([center_lon - 0.2, center_lon + 0.2], [center_lat, center_lat], color='red', transform=ccrs.PlateCarree())
            ax3.plot([center_lon, center_lon], [center_lat - 0.2, center_lat + 0.2], color='red', transform=ccrs.PlateCarree())
            
            if i == 0:  # Add colorbar only once
                plt.colorbar(im, cax=cbar_ax, label='Reflectivity (dBZ)')
            
            ax3.set_extent([center_lon - 1.6, center_lon + 1.6, center_lat - 0.75, center_lat + 0.75], crs=ccrs.PlateCarree())
            ax3.set_title(f'PseudoCAPPI 2km Reflectivity ({data_datetime}), Czech hydrometeorological institute')
            ax3.set_xlabel('Longitude')
            ax3.set_ylabel('Latitude')
            ax3.legend()

            plt.tight_layout()

    # Save the animation as MP4
    if save_mp4:
        writer = FFMpegWriter(fps=20, metadata=dict(artist='Me'), bitrate=1800)
    ani = animation.FuncAnimation(fig, update, frames=range(0, len(dates), 10), repeat=False)
    if save_mp4:
        ani.save(f'radar_animation_{file_path}.mp4', writer=writer)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Plot radar data and EFM log data.')
    parser.add_argument('file_path', type=str, help='Path to the CSV file')
    parser.add_argument('lon', type=float, help='Longitude of the center point')
    parser.add_argument('lat', type=float, help='Latitude of the center point')
    parser.add_argument('--mp4', action='store_true', help='Save the animation as MP4')

    args = parser.parse_args()

    main(args.file_path, args.lat, args.lon, save_mp4=args.mp4)
