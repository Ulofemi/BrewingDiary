from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db.models import Avg, Count, Min, Sum

import datetime
import time
import sys
import os
from pathlib import Path
from .models import Rezept, Malz, Maischen, Hopfenplan, Temperaturlogging
from .forms import RezeptForm, MalzForm, MaischeForm, HopfenForm
import json
import random



#################################################################################
# VIEWS
#################################################################################
def rezept_detail_view(request, id):
	# getting a recepy by id or error 404
	recepy = get_object_or_404(Rezept, id=id)
	
	# getting malt, mash and hopplan by recepy id
	malt = Malz.objects.filter(rezept=recepy.pk)
	mash = Maischen.objects.filter(rezept=recepy.pk)
	hopplan = Hopfenplan.objects.filter(rezept=recepy.pk)
	
	#############################################################
	# getting distinct hops --> save hop and amount in hop_recepy
	hops_distinct = hopplan.values_list('hopfen', flat=True).distinct()
	hop_recepy = []
	for hop in hops_distinct: 
		# building a tuple (name, amount)
		# amount = aggregate(Sum) over filter
		hop_recepy.append((hop, Hopfenplan.objects.filter(rezept=recepy, hopfen=hop).aggregate(Sum('menge'))['menge__sum']))

	#############################################################
	# getting infos about boiling
	# distinct durations for boiling
	duration_distinct = Hopfenplan.objects.filter(rezept=recepy.pk, verwendung='kochen').values_list('dauer', flat=True).distinct()
	hop_boiling = []
	for duration in duration_distinct:
		x = [] 
		y = Hopfenplan.objects.filter(rezept=recepy.pk, verwendung='kochen', dauer=duration)
		for i in y:
			x.append((i.hopfen, i.menge))
		hop_boiling.append([duration, x])

	#############################################################
	# Whirlpool
	hop_whirlpool = []
	for wp in Hopfenplan.objects.filter(rezept=recepy.pk, verwendung='whirlpool'):
		hop_whirlpool.append((wp.hopfen, wp.menge))

	#############################################################
	# Dry Hopping
	hop_dry = []
	for hd in Hopfenplan.objects.filter(rezept=recepy.pk, verwendung='stopfen'):
		hop_dry.append((hd.hopfen, hd.menge))

	#############################################################
	# read temperature --> getting a list of temperaures
	temperatures = GetTemperature()

	# contrlInstructions
	# 0 --> No Logging
	# 1 --> temperature ist ok
	# 2 --> to cold
	# 3 --> t warm
	controlInstructions = [0] * len(temperatures)
	
	# if logging is activated --> estimate target temperature
	if recepy.logging:
		# temperatures is a list of temperatures measured by sensors
		targetTemperature = Automation(recepy, temperatures)
		
		# check controlInstructions
		for i in range(len(controlInstructions)):
			# too cold if 3 K below target
			if targetTemperature - temperatures[i] > 3:
				controlInstructions[i] = 2
			# too warm if 2 K above target				
			elif targetTemperature - temperatures[i] < -2:
				controlInstructions[i] = 3
			# OK			
			else:
				controlInstructions[i] = 1

		# targetTemperatures added to list
		temperatures.append(targetTemperature)
		# def temperatureLogging(rezept, interval, temperaturen, prozess, solltemperatur):
		TemperatureLogging(recepy, temperatures)

	context = {
	'rezept':recepy,
	'malz':malt,
	'maische':mash, 
	'hopfenplan':hopplan, 
	'hopfen':hop_recepy, 
	'hopfenkochen':hop_boiling,
	'whirlpool':hop_whirlpool,
	'stopfen':hop_dry,
	'temperaturen':temperatures,
	'controlInstructions':controlInstructions
	}
	return render(request, "detail.html", context)

def temperatur_detail_view(request, id):
	recepy = get_object_or_404(Rezept, id=id)

	# timestamp and targettemperature
	time_raw = Temperaturlogging.objects.filter(rezept=recepy).values_list('zeitstempel').order_by('id')
	target_raw = Temperaturlogging.objects.filter(rezept=recepy).values_list('sollwert').order_by('id')
	
	# sensors 1, 2, 3, ...
	s1_raw = Temperaturlogging.objects.filter(rezept=recepy).values_list('sensor1').order_by('id')
	s2_raw = Temperaturlogging.objects.filter(rezept=recepy).values_list('sensor2').order_by('id')
	
	# creating lists for data
	timestamp = []
	targetTemperatures = []
	s1 = []
	s2 = []

	# filling lists from raw data
	for ts in time_raw:
		timestamp.append(ts[0].strftime("%d-%H:%M"))

	for s in target_raw:
		targetTemperatures.append(float(s[0]))

	for s in s1_raw:
		s1.append(float(s[0]))

	for s in s2_raw:
		s2.append(float(s[0]))

	# creating series
	sensor1_series = {
		'name': 'Sensor 1',
		'data': s1,
		'color': 'rgba(93, 162, 252, 1.0)' #'#91bbf2'
	}

	sensor2_series = {
		'name': 'Sensor 2',
		'data': s2,
		'color': 'rgba(30, 196, 147, 1.0)' # '#82c493',
	}

	target_series = {
		'name': 'Solltemperatur',
		'data': targetTemperatures,
		'color': 'rgba(237, 100, 100, 0.5)' #'#ed6464', #237, 100, 100
	}
	#'title': {'text': 'Temperatur Test'},
	chart = {
		'chart': {'type': 'spline', 'zoomType': 'xy', 'height': 600},
		'navigator': {'enabled': True},
		'title': {'text': ''},
		'xAxis': {'categories': timestamp, 'type': 'datetime', 'tickInterval': 15, 'gridLineColor': '#2C3043'},
		'yAxis': {'title': {'text': 'Temperatur [°C]'}, 'gridLineColor': '#2C3043', 'gridLineDashStyle': 'Dot'},
		'scrollbar': {'enabled': True},
		'series': [sensor1_series, sensor2_series, target_series]
    }

	dump = json.dumps(chart)

	context = {
		'rezept': recepy,
		'chart': dump
	}

	return render(request, "graph.html", context)

def rezept_update_view(request, id=id):
	edit = True
	recepy = get_object_or_404(Rezept, id=id)

	formRezept = RezeptForm(request.POST or None, instance=recepy)
	if formRezept.is_valid():
		formRezept.save()
	
	formMalz = MalzForm(request.POST or None, r=recepy)
	if formMalz.is_valid():
		formMalz.save()
	
	formMaischen = MaischeForm(request.POST or None, r=recepy)
	if formMaischen.is_valid():
		formMaischen.save()

	formHopfen = HopfenForm(request.POST or None, r=recepy)
	if formHopfen.is_valid():
		formHopfen.save()

	context = {
		'formRezept': formRezept,
		'formMalz': formMalz,
		'formMaischen': formMaischen,
		'formHopfen': formHopfen,
		'edit': edit,
		'rezept': recepy
	}
	return render(request, "create.html", context)

def rezept_create_view(request):
	edit = False
	form = RezeptForm(request.POST or None)
	if form.is_valid():
		form.save()

	context = {
		'form': form,
		'edit': edit
	}
	return render(request, "create.html", context)

def loggingToggleView(request, id):
	recepy = get_object_or_404(Rezept, id=request.POST.get('rezept_id'))
	if recepy.logging:
		recepy.logging = False
	else:
		recepy.logging = True
	recepy.save()

	return HttpResponseRedirect(reverse("rezept", kwargs={"id": id}))

#################################################################################
# FUNCITONS
#################################################################################

def GetTemperature():
	# if no RaspberryPi --> No Sensors --> Random
	debug = True

	# result is a list of temperatures
	result = []
	if debug:
		result.append(random.randrange(70,90))
		result.append(random.randrange(70,90))
	else: 
		sensors = []
		# name of sensors ds18b20 
		# THIS MUST BE MODIFIED
		sensor1 = '/sys/bus/w1/devices/28-00000c20f6f0/w1_slave'
		sensor2 = '/sys/bus/w1/devices/28-00000c21017e/w1_slave'
		sensors.append(sensor1)
		sensors.append(sensor2)

		for s in sensors:
			f = open(s, 'r')
			lines = f.readlines()
			f.close()

			temperaturStr = lines[1].find('t=')
			# Check if temperature is found
			tempData = lines[1][temperaturStr+2:]
			tempCelsius = float(tempData) / 1000.0
			tempKelvin = 273 + float(tempData) / 1000
			tempFahrenheit = float(tempData) / 1000 * 9.0 / 5.0 + 32.0
			result.append(tempCelsius)
	return result


def TemperatureLogging(rezept, temperaturen):
	interval = rezept.intervall
	prozess = rezept.aktuellerProzess
	solltemperatur = temperaturen[-1]

	# getting all saved data
	loggings = Temperaturlogging.objects.filter(rezept=rezept).order_by('-zeitstempel')

	# if no loggings so far --> Adding first one --> Else checking if interval <= last record
	if not loggings:
		Temperaturlogging.objects.create(rezept=rezept, sollwert=solltemperatur, sensor1=temperaturen[0], sensor2=temperaturen[1], prozess=prozess, zeitstempel=timezone.localtime())
	elif (timezone.localtime() - loggings[0].zeitstempel).total_seconds() >= interval:
		print('Seit letztem Temperatur-Log sind {} Sekunden verstrichen'.format((timezone.localtime() - loggings[0].zeitstempel).total_seconds()))
		Temperaturlogging.objects.create(rezept=rezept, sollwert=solltemperatur, sensor1=temperaturen[0], sensor2=temperaturen[1], prozess=prozess, zeitstempel=timezone.localtime())
	else:
		print('Seit letztem Temperatur-Log sind {} Sekunden verstrichen'.format((timezone.localtime() - loggings[0].zeitstempel).total_seconds()))



def NextProcess(rezept, nextNextProcess):
	# rezept.naechsterProzess wird in aktuellen Prozess geschrieben
	# in rezept.naechsterProzess wird naechstProzess geschrieben
	rezept.aktuellerProzess = rezept.naechsterProzess
	rezept.zeitstempelProzess = timezone.localtime()
	rezept.naechsterProzess = nextNextProcess
	rezept.save()



def Automation(rezept, temperaturen):
	"""
	1. Current process? Heating, Mashing, Lautering, Boiling
	2. Next Process?
	3. What condition

	heizen 			heating
	einmaischen 	mashing in
	heizen			heating
	1. Rast 		mash pause
	heizen 			heating
	2. Rast  		mash pause
	heizen  		heating
	abmasichen 		mash out
	läutern 		lauter tun
	kochen 			boiling
	kühlen 			cooling
	gärung 			fermentation

	In Recepy is the current and next process saved

	"""
	# this should go to a new model --> better to handle
	maischeProzesse = [
		'einmaischen',
		'ersteRast',
		'zweiteRast',
		'dritteRast',
		'vierteRast',
		'abmaischen'
	]

	#print('Aktueller Prozess: {}'.format(rezept.aktuellerProzess))
	
	targetTemperature = 0

	# switch case would be smart

	# if heating ...
	# after heating comes normally one of these: mashing in, mash pause, mashing out
	if rezept.aktuellerProzess == 'heizen':
		# getting next process filter by recepy.pk and recepy.nextprocess
		maischen = Maischen.objects.filter(rezept=rezept.pk, prozess=rezept.naechsterProzess)
		
		# what if there is no mashing process after heating?!?
		if not maischen: 
			pass
		# what if there are more than 1 mashing process after heating?!?
		# e.g. the recepy has 2 times "mashing in"
		elif len(maischen) > 1:
			pass
		# if there is only 1 matching process
		elif len(maischen) == 1:
			# getting this one process
			maischen = Maischen.objects.get(rezept=rezept.pk, prozess=rezept.naechsterProzess)
			# getting the target temperature
			targetTemperature = maischen.temperatur
			#print('Heizen bis: {}'.format(solltemperatur))

			# if it is a heating process, the requirement to get to the next process is only the temperature
			if max(temperaturen) >= targetTemperature: 
				# if the next process is mashing out it follows not heating but lauter tun
				if rezept.naechsterProzess == 'abmaischen':
					nextNextProcess = 'läutern'
					NextProcess(rezept, nextNextProcess)
				# after mashing in or 1st, 2nd, ... pause it follows normally heating
				else:
					nextNextProcess = 'heizen'
					NextProcess(rezept, nextNextProcess)

	# if not heating, then maybe a mashing process?
	elif rezept.aktuellerProzess in maischeProzesse:
		maischen = Maischen.objects.filter(rezept=rezept.pk, prozess=rezept.aktuellerProzess)
		
		# what if there is no mashing process?!?
		if not maischen: 
			pass
		# what if there are more than 1 mashing process
		# e.g. the recepy has 2 times "mashing in"
		elif len(maischen) > 1:
			pass
		# if there is only 1 matching process
		elif len(maischen) == 1:
			maischen = Maischen.objects.get(rezept=rezept.pk, prozess=rezept.aktuellerProzess)
			targetTemperature = maischen.temperatur

			# a mashing processes has a target temperature and a duration
			# in the recepy is the timestamp of the process change stored --> It is possible to calculate the duration
			print('Aktuelle Solltemperatur: {} °C'.format(targetTemperature))
			print('Gesamtdauer: {} min'.format(maischen.dauer))
			print('Bisher schon {} min im aktuellen Prozess'.format(timezone.localtime() - rezept.zeitstempelProzess))

			# requirement to get to the enxt process is the duration
			if (timezone.localtime() - rezept.zeitstempelProzess).total_seconds() >= maischen.dauer * 60:
				# if the current process is mashing out --> then lauter tun --> then boiling
				if rezept.aktuellerProzess == 'abmaischen':
					# nächster Prozess ist läutern dann kochen
					nextNextProcess = 'kochen'
					NextProcess(rezept, nextNextProcess)
				# if not --> then heating --> checking what comes nextNext
				else: 
					for idx, m in enumerate(maischeProzesse): 
						# m = process --> mashing in, 1st pasue , 2nd pause, mashing out
						if rezept.aktuellerProzess == m:
							# nextNext Prozess --> maischeProzesse[idx + 1]
							nextMashing = Maischen.objects.filter(rezept=rezept.pk, prozess=maischeProzesse[idx + 1])
							if not nextMashing: 
								nextNextProcess = 'abmaischen'
								NextProcess(rezept, nextNextProcess)
							elif len(nextMashing) == 1:
								nextNextProcess = maischeProzesse[idx + 1]
								NextProcess(rezept, nextNextProcess)

	# if not heating and not mashing --> then maybe lauter tun?
	elif rezept.aktuellerProzess == 'läutern':
		print('Bisher schon {} beim Läutern'.format(timezone.localtime() - rezept.zeitstempelProzess))
		targetTemperature = 78
		# if temperateure > 90 °C --> then boiling
		if max(temperaturen) >= 90: 
			# next boiling, nextNext cooling
			nextNextProcess = 'kühlen'
			NextProcess(rezept, nextNextProcess)

	# if not heating and not mashing and not lauter tun --> then maybe boiling?
	elif rezept.aktuellerProzess == 'kochen':
		print('Bisher schon {} beim Kochen'.format(timezone.localtime() - rezept.zeitstempelProzess))
		targetTemperature = 90
		# end of boiling is dertermined by duration
		if (timezone.now() - rezept.zeitstempelProzess).total_seconds() >= rezept.hopfenkochzeit * 60:
			# next cooling, nextNext fermentation
			nextNextProcess = 'gärung'
			NextProcess(rezept, nextNextProcess)

	# if not heating and not mashing and not lauter tun and not boiling --> then maybe cooling?
	elif rezept.aktuellerProzess == 'kühlen':
		# goal is to get to 20 °C for yeast
		targetTemperature = 20
		# for yeast is 30 °C ok
		if max(temperaturen) <= 30: 
			# next process fermentation, nextNext end
			nextNextProcess = 'ende'
			NextProcess(rezept, nextNextProcess)

	# if not heating and not mashing and not lauter tun and not boiling and not coolingh --> then maybe fermentation?
	elif rezept.aktuellerProzess == 'gärung':
		print('Bisher läuft die Gärung schon {}'.format(timezone.localtime() - rezept.zeitstempelProzess))
		targetTemperature = 20

	return targetTemperature

