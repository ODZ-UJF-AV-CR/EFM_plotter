import os
import glob
import h5py
import numpy as np
import matplotlib.pyplot as plt
import argparse
from datetime import datetime, timedelta, timezone

def parse_arguments():
    parser = argparse.ArgumentParser(description='Generate EFI helicorder plots for THUNDERMILL data.')
    parser.add_argument('--input', type=str, required=True, help='Root directory containing waveform data')
    parser.add_argument('--output', type=str, required=True, help='Root directory for output files')
    parser.add_argument('--date', type=str, help='Date to plot in YYYYMMDD format (default: yesterday or today based on current time)')
    parser.add_argument('--observatory', type=str, default='Musala', help='Name of the observatory (default: Musala)')
    parser.add_argument('--station', type=str, default='THUNDERMILL01', help='Station prefix (default: THUNDERMILL01)')
    parser.add_argument('--format', type=str, choices=['png', 'svg'], default='png', help='Output format (png or svg, default: png)')
    parser.add_argument('--theme', type=str, choices=['light', 'dark'], default='light', help='Plot theme (light or dark, default: light)')
    parser.add_argument('--calibration', type=float, default=1/1.4244*1000, help='Calibration coefficient for ADU to kV/m conversion (default: 701.98)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    return parser.parse_args()

def find_2d_dataset(h5obj):
    for name, item in h5obj.items():
        if isinstance(item, h5py.Dataset) and item.ndim == 2:
            return name, item
        elif isinstance(item, h5py.Group):
            found = find_2d_dataset(item)
            if found:
                return found
    return None

def main():
    args = parse_arguments()
    verbose = args.verbose
    
    # Get format, theme and calibration from args
    output_format = args.format
    theme = args.theme
    calibration_coefficient = args.calibration
    
    if verbose:
        print("=== EFI Helicorder Plot Generator ===")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Using output format: {output_format}")
        print(f"Using theme: {theme}")
        print(f"Using calibration coefficient: {calibration_coefficient}")
    
    # Set station prefix from arguments
    station_prefix = args.station
    observatory_name = args.observatory
    
    if verbose:
        print(f"Station: {station_prefix}")
        print(f"Observatory: {observatory_name}")
    
    # Kořenová složka dat
    base_data_dir = args.input
    # Kořenová složka pro výstupy
    processing_dir = args.output
    
    if verbose:
        print(f"Input directory: {base_data_dir}")
        print(f"Output directory: {processing_dir}")
    
    # Určení dne (UTC)
    if args.date:
        # Parse date from input format YYYYMMDD
        year = args.date[:4]
        month = args.date[4:6]
        day = args.date[6:8]
        day_to_plot = datetime(int(year), int(month), int(day))
        if verbose:
            print(f"Using specified date: {year}-{month}-{day}")
    else:
        now = datetime.now(timezone.utc)
        if now.hour < 2:
            day_to_plot = now - timedelta(days=1)
            if verbose:
                print("Current time is before 2:00 UTC, using yesterday's date")
        else:
            day_to_plot = now
            if verbose:
                print("Using today's date")
        
        year = f"{day_to_plot.year:04d}"
        month = f"{day_to_plot.month:02d}"
        day = f"{day_to_plot.day:02d}"
        if verbose:
            print(f"Selected date: {year}-{month}-{day}")
    
    day_prefix = f"{year}{month}{day}"
    print(f"Processing date: {day_prefix}")
    
    # Vstupní cesta ke složce s daty pro daný den
    date_path = os.path.join(base_data_dir, year, month, day)
    
    if verbose:
        print(f"Looking for data in: {date_path}")
    
    # Výstupní složka ve formátu YYYY_MM
    output_dir = os.path.join(processing_dir, f"{year}_{month}")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{station_prefix}_EFI_HELICORDER_{day_prefix}.{output_format}")
    
    if verbose:
        print(f"Created output directory: {output_dir}")
        print(f"Output file will be: {output_file}")
    
    hours = [f"{int(h):02d}" for h in range(24)]
    efi_blocks = []
    
    if verbose:
        print("Starting data loading process...")
    
    total_files_processed = 0
    hours_with_data = 0
    
    # Načítání dat
    for hour in hours:
        pattern = os.path.join(date_path, f"{station_prefix}_{day_prefix}_{hour}*.h5")
        files = sorted(glob.glob(pattern))
        
        if verbose:
            print(f"Hour {hour}: Found {len(files)} files matching pattern {pattern}")
        
        hour_efi = []
        files_in_hour = 0
        
        for file_path in files:
            try:
                with h5py.File(file_path, "r") as f:
                    data = None
                    if "waveform" in f:
                        data = f["waveform"][()]
                        if verbose:
                            print(f"  - Loaded waveform data from {os.path.basename(file_path)}")
                    else:
                        found = find_2d_dataset(f)
                        if found:
                            data = found[1][()]
                            if verbose:
                                print(f"  - Found 2D dataset '{found[0]}' in {os.path.basename(file_path)}")
                    
                    if data is not None:
                        diff_efi = data[:, 13] - data[:, 33]
                        hour_efi.append(diff_efi)
                        files_in_hour += 1
                        total_files_processed += 1
                        if verbose:
                            print(f"  - Processed EFI data with {len(diff_efi)} samples")
            except Exception as e:
                print(f"Error processing file {file_path}: {str(e)}")
        
        if hour_efi:
            hour_efi_arr = np.concatenate(hour_efi)
            efi_blocks.append(hour_efi_arr)
            hours_with_data += 1
            if verbose:
                print(f"  * Hour {hour}: Successfully processed {files_in_hour} files with total {len(hour_efi_arr)} samples")
        else:
            efi_blocks.append(None)
            if verbose:
                print(f"  * Hour {hour}: No data available")
    
    if verbose:
        print(f"Data loading complete. Processed {total_files_processed} files across {hours_with_data} hours.")
    
    # Check if we have any data
    if not any(block is not None for block in efi_blocks):
        print(f"ERROR: No data found for date {day_prefix}. Cannot generate plot.")
        return
    
    # Max délka dat
    maxlen = max(len(b) for b in efi_blocks if b is not None)
    if verbose:
        print(f"Maximum samples per hour: {maxlen}")
    
    efi_matrix = np.full((len(efi_blocks), maxlen), np.nan)
    for i, b in enumerate(efi_blocks):
        if b is not None:
            L = len(b)
            efi_matrix[i, :L] = b
            
    if verbose:
        print("Starting plot generation...")
    
    # Define theme colors
    if theme == 'dark':
        # Dark theme colors
        bg_color = '#121212'
        text_color = 'white'
        line_color1 = '#00B7EB'  # Cyan for even hours
        line_color2 = '#00FF7F'  # Spring green for odd hours
        grid_color = '#404040'
        figure_facecolor = '#1E1E1E'
        timestamp_color = '#808080'  # Gray
    else:
        # Light theme colors (default)
        bg_color = 'white'
        text_color = 'black'
        line_color1 = 'black'    # Black for even hours
        line_color2 = 'green'    # Green for odd hours
        grid_color = 'gray'
        figure_facecolor = 'white'
        timestamp_color = 'gray'
    
    # Create plot with theme colors
    fig, ax = plt.subplots(figsize=(14, 10))
    fig.patch.set_facecolor(figure_facecolor)
    ax.set_facecolor(bg_color)
    amp_offset = 15000
    bottom_margin = amp_offset * 2.5
    top_margin = amp_offset * 2.2
    ax.set_ylim(-bottom_margin, amp_offset * len(hours) + top_margin)
    
    if verbose:
        print("Setting up plot layout and axes...")
    
    # Hodiny opačně: 0h nahoře, 23h dole
    for i, row in enumerate(efi_matrix):
        base_y = (len(hours) - 1 - i) * amp_offset
        if not np.isnan(row).all():
            color = line_color1 if i % 2 == 0 else line_color2
            ax.plot(np.linspace(0, 60, maxlen), row + base_y, color=color, linewidth=0.7)
            if verbose:
                print(f"Plotting hour {hours[i]} data ({len(row[~np.isnan(row)])} valid points)")
        else:
            if verbose:
                print(f"No data to plot for hour {hours[i]}")
                
        ax.plot([0, 60], [base_y, base_y], color=grid_color, linewidth=0.2, linestyle="dashed")
    
    # Set text colors
    ax.tick_params(colors=text_color)
    for spine in ax.spines.values():
        spine.set_edgecolor(text_color)
    
    if verbose:
        print("Adding axis labels and ticks...")
        
    yticks = [(len(hours) - 1 - i) * amp_offset for i in range(len(hours))]
    yticklabels = [f"{h}h" for h in hours]
    ax.set_yticks(yticks)
    ax.set_yticklabels(yticklabels)
    ax.set_xlabel("Time in minutes", color=text_color)
    ax.set_ylabel("UTC hour", color=text_color)
    ax.set_title(f"{station_prefix} EFI: {year}-{month}-{day} (Observatory: {observatory_name})", color=text_color)
    
    if verbose:
        print("Adding scale bar...")
    
    # Svislá škála vpravo using the calibration coefficient
    ADU_per_kVm = calibration_coefficient
    scalebar_len = 10 * ADU_per_kVm
    scalex = 62
    scaley = -bottom_margin + amp_offset * 1
    ax.plot([scalex, scalex], [scaley, scaley + scalebar_len], color=text_color, linewidth=2, zorder=5)
    ax.text(scalex + 1, scaley + scalebar_len, "+", color=text_color, va="center", ha="left", fontsize=15, fontweight="bold")
    ax.text(scalex + 1, scaley, "-", color=text_color, va="center", ha="left", fontsize=15, fontweight="bold")
    ax.text(scalex + 1, scaley + scalebar_len / 2, "10 kV/m", color=text_color, va="center", ha="left", fontsize=12, rotation=90)
    
    plt.tight_layout()
    
    now_str = datetime.now(timezone.utc).strftime("Generated (UTC): %Y-%m-%d %H:%M:%S")
    fig.text(0.99, 0.015, now_str, ha='right', va='bottom', fontsize=9, color=timestamp_color)
    
    if verbose:
        print(f"Saving plot to: {output_file}")
    
    plt.savefig(output_file, dpi=120, facecolor=figure_facecolor, bbox_inches='tight')
    plt.close()
    print(f"Saved daily EFI helicorder: {output_file}")
    
    if verbose:
        print("=== Processing complete ===")

if __name__ == "__main__":
    main()
