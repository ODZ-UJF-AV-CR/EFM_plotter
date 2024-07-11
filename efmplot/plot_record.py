import numpy as np
import datetime
import matplotlib.pyplot as plt

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

f = "EFM_THUNDERMILL01log_20240710_173235_UTC.csv"
f = "EFM_THUNDERMILL01log_20240710_173259_UTC.csv"
#f = "EFM_THUNDERMILL01log_20240710_153113_UTC.csv"

with open(f, 'r') as file:
    data = []
    for line in file:
        data.append(line.strip().split(','))

dates = np.array([int(float(x[0]))/1 for x in data])



adc_values = [x[1:] for x in data]
max_length = max(len(sublist) for sublist in adc_values)
adc_values = [sublist + [255]*(max_length - len(sublist)) for sublist in adc_values]
adc_values = [[clean_data(value)-255 for value in sublist] for sublist in adc_values]

angles = np.linspace(0, 180, max_length)
values = np.array(adc_values)-255

#p2p = np.ptp(values, axis=1)
p2p = ptp_orient(values)
angle_index = np.argmax(values, axis=1)
angle_index = (angle_index / max_length)


window_size = 20
smoothed_angle_index = np.convolve(angle_index, np.ones(window_size)/window_size, mode='same')
smoothed_p2p = np.convolve(p2p, np.ones(window_size)/window_size, mode='same')


strmy_pokles = np.where(np.diff(p2p) < -10)
strmy_pokles_casy = dates[strmy_pokles]


# Vykreslení grafu
fig = plt.figure()
ax1 = fig.add_subplot(111)
ax2 = ax1.twinx()

#ax1.set_xlabel('Max phase')

ax1.set_ylabel('Max value angle [deg]', color='red')
l1 = ax1.plot(dates, angle_index, '.', color='red', alpha=0.1, label='Max value angle (0-1 full range)')
l2 = ax1.plot(dates, smoothed_angle_index, color = 'red', alpha=0.5, label='Max value angle, rolling mean')
ax1.set_ylim(0, 1)
ax1.tick_params('y', colors='red')


l3 = ax2.plot(dates, p2p, ".", color='blue', alpha=0.1, label='peak-to-peak amplitude')
l4 = ax2.plot(dates, smoothed_p2p, color='blue', alpha=0.5, lw=2 , label='peak-to-peak amplitude, rolling mean')
ax2.set_ylim(-255*2, 255*2)
ax2.set_ylabel('peak-to-peak amplitude - relative [kV/m]', color='blue')
ax2.tick_params('y', colors='blue')
ax2.grid(True)

#l5 = ax1.vlines(strmy_pokles_casy, 0, 180, color='green', alpha=0.5, label='Steep decrease in amplitude')

timestamps = [datetime.datetime.fromtimestamp(date) for date in ax1.get_xticks()]
formatted_dates = [timestamp.strftime('%y-%m-%d\n%H:%M:%S') for timestamp in timestamps]

ax1.set_xticklabels(formatted_dates, rotation=0)

# ask matplotlib for the plotted objects and their labels
ax1.legend(handles=l3+l4+l1+l2)


plt.title('Electric Field Mill data (USTTHUNDERMILL01) {}'.format(timestamps[0].strftime('%Y-%m-%d')))
plt.grid(True)
plt.show()
plt.tight_layout()
plt.clf()
