#!/usr/bin/env python

import matplotlib.pyplot as plt
import serial

ser = serial.Serial('/dev/ttyUSB0')

fig = plt.figure("EFM")

while True:

	try:
		line = ser.readline()

		wave = [int(item) if item.isdigit() else 0 for item in line.decode().split(',')]
	except:
		continue

	plt.plot(wave[:-1])

	plt.ylim(0,511)
	plt.xlabel('Phase [a.u.]')
	plt.ylabel('Electric Field [a.u.]')
	
	# DRAW, PAUSE AND CLEAR
	plt.draw()
	plt.pause(0.5)
	plt.clf()
