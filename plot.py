#!/usr/bin python

import matplotlib.pyplot as plt
import serial
import pandas as pd

ser = serial.Serial('/dev/ttyUSB0')

fig = plt.figure("EFM")
plt.rcParams.update({'font.size': 20})

while True:

	try:
		line = ser.readline()
		wave = pd.DataFrame()
		wave['field'] = [int(item) if item.isdigit() else 0 for item in line.decode().split(',')]
	except:
		continue
		
	#wave['phase'] = (wave.index)
	wave['phase'] = (wave.index) * 180/(len(wave)-1)
	wave['field'] = ((wave['field'])-256) * ((3/5.5)*2.5/(139-129))
	#print(wave)
	
	plt.title('Electric Field Mill')
	plt.plot(wave[:-1].phase, wave[:-1].field, lw=3)

	plt.ylim(-40,40)
	plt.xlim(0,180)
	plt.xlabel('Rotor Phase [°]')
	plt.ylabel('Electric Field [kV/m]')
	
	# DRAW, PAUSE AND CLEAR
	plt.draw()
	plt.pause(0.5)
	plt.clf()
