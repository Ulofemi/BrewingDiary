from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db.models import Avg, Count, Min, Sum, Max
from django.db.models import Q

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
		print(type(temperatures[1]))
		targetTemperature = Automation(recepy, temperatures)
		
		# check controlInstructions
		for i in range(len(controlInstructions)):
			targetTemperature = float(targetTemperature)
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
		'form': formRezept,
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


def stats_view(request, *args, **kwargs):
	#recepy_all = Rezept.objects.all()
	beer_amount = Rezept.objects.aggregate(Sum('zielvolumen'))
	malt_amount = Malz.objects.aggregate(Sum('menge'))
	malt_amount_per_liter = malt_amount['menge__sum'] / beer_amount['zielvolumen__sum']
	hop_amount = Hopfenplan.objects.aggregate(Sum('menge'))
	hop_amount_per_liter = hop_amount['menge__sum'] / beer_amount['zielvolumen__sum']

	ibu_high = Rezept.objects.aggregate(Max('bittere'))
	ibu_low = Rezept.objects.exclude(bittere=0).aggregate(Min('bittere'))
	sw_high = Rezept.objects.aggregate(Max('stammwuerze'))
	sw_low = Rezept.objects.exclude(stammwuerze=0).aggregate(Min('stammwuerze'))

	recepy_ibu_high = Rezept.objects.get(bittere=ibu_high['bittere__max'])
	recepy_ibu_low = Rezept.objects.get(bittere=ibu_low['bittere__min'])
	recepy_sw_high = Rezept.objects.get(stammwuerze=sw_high['stammwuerze__max'])
	recepy_sw_low = Rezept.objects.get(stammwuerze=sw_low['stammwuerze__min'])


	dump_pie = get_hops_amount()
	dump_bar = get_hops_recepy_amount()
	dump_pie_malts = get_malts_amount()

	context = {
		'beer_amount': beer_amount['zielvolumen__sum'],
		'malt_amount': malt_amount['menge__sum'],
		'malt_amount_liter': malt_amount_per_liter,
		'hop_amount': hop_amount['menge__sum'],
		'hop_amount_liter': hop_amount_per_liter,
		'ibu_high': recepy_ibu_high,
		'ibu_low': recepy_ibu_low,
		'sw_high': recepy_sw_high,
		'sw_low': recepy_sw_low,
		'chart_pie': dump_pie,
		'chart_bar': dump_bar,
		'dump_pie_malts': dump_pie_malts
	}
	return render(request, "statistics.html", context)
#################################################################################
# FUNCITONS
#################################################################################

def GetTemperature():
	# if no RaspberryPi --> No Sensors --> Random
	debug = True

	# result is a list of temperatures
	result = []
	if debug:
		result.append(random.randrange(15,35))
		result.append(random.randrange(15,35))
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


def get_hops_amount():
	colors = Get_Colors()
	hops_all = Hopfenplan.objects.order_by('hopfen').values('hopfen').distinct()

	series = []
	for idx, h in enumerate(hops_all):
		color = colors[idx % len(colors)]
		hopfenplans = Hopfenplan.objects.filter(hopfen=h['hopfen'])
		recepies_different = hopfenplans.values('rezept').distinct()
		amount_all = hopfenplans.values('menge')
		hopfen_sum = 0
		for amount in amount_all:
			hopfen_sum = hopfen_sum + amount['menge']

		s = {
			'name': str(h['hopfen']),
			'y': float(hopfen_sum),
			'sliced': True,
			'color': color
		}
		series.append(s)

	chart_pie = {
		'chart': {'type': 'pie',
				  'style': {
					  'fontFamily': 'Arial',
					  'color': '#7EB2DD'}
				  },
		'tooltip': {'pointFormat': '<b>{point.y:.0f} g</b> <br> <b>{point.percentage:.0f}%</b>'},
		'title': {'text': 'Hopfenanteile von Pixelbräu',
				  'style': {
					  'color': '#7EB2DD'}
				  },
		'series': [{'name': 'Hopfen',
					'data': series,
					'dataLabels': {
						'enabled': 'true',
						'style': {
							'color': '#7EB2DD',
							'textOutline': 'transparent'}
					}}]
	}

	return json.dumps(chart_pie)


def get_malts_amount():
	colors = Get_Colors()
	malts_all = Malz.objects.order_by('sorte').values('sorte').distinct()
	series = []
	for idx, m in enumerate(malts_all):
		color = colors[idx % len(colors)]
		malts = Malz.objects.filter(sorte=m['sorte'])
		amount_all = malts.values('menge')

		malts_sum = 0

		for malt in amount_all:
			print(malt)
			malts_sum = malts_sum + malt['menge']

		s = {
			'name': str(m['sorte']),
			'y': float(malts_sum),
			'sliced': True,
			'color': color
		}
		series.append(s)

	chart_pie = {
		'chart': {'type': 'pie',
				  'style': {
					  'fontFamily': 'Arial',
					  'color': '#7EB2DD'}
				  },
		'tooltip': {'pointFormat': '<b>{point.y:.0f} g</b> <br> <b>{point.percentage:.0f}%</b>'},
		'title': {'text': 'Malzanteile von Pixelbräu',
				  'style': {
					  'color': '#7EB2DD'}
				  },
		'series': [{'name': 'Malz',
					'data': series,
					'dataLabels': {
						'enabled': 'true',
						'style': {
							'color': '#7EB2DD',
							'textOutline': 'transparent'}
					}}]
	}

	return json.dumps(chart_pie)


def get_hops_recepy_amount():
	colors = Get_Colors()
	hops_all = Hopfenplan.objects.order_by('hopfen').values('hopfen').distinct()

	xAxisCategories = []
	data = []
	for idx, h in enumerate(hops_all):
		xAxisCategories.append(h['hopfen'])
		color = colors[idx % len(colors)]
		hopfenplans = Hopfenplan.objects.filter(hopfen=h['hopfen'])
		recepies_different = hopfenplans.values('rezept').distinct()
		d = [str(h['hopfen']), len(recepies_different)]
		data.append(d)
		print(len(recepies_different))

	# creating chart
	chart_bar = {
		'chart': {'type': 'bar',
				  'style': {
					  'fontFamily': 'Arial',
					  'color': '#7EB2DD'}
				  },
		'title': {'text': 'Hopfeneinsatz in Rezepten'},
		'yAxis': {'min': 0,
				  'title': {
					  'text': 'Anzahl Rezepte',
					  'align': 'high'},
				  'labels': {
					  'style': {
						  'color': '#7EB2DD'}
				  }},
		'tooltip': {'pointFormat': '<b>{point.y:.0f} Rezepte</b>'},
		'series': [{
			'name': 'Hopfen',
			'data': data}]
	}

	# return chart to json
	return json.dumps(chart_bar)

def Get_Colors():
    colors = [
        '#34568B',
        '#FF6F61',
        '#6B5B95',
        '#009B77',
        '#D65076',
        '#5B5EA6',
        '#9B2335',
        '#DFCFBE',
        '#98B4D4',
        '#f39c12',
        '#2ecc71',
        '#cb4335',
        '#2980b9',
        '#7b241c',
        '#943126',
        '#633974',
        '#5b2c6f',
        '#1a5276',
        '#21618c',
        '#117864',
        '#0e6655',
        '#196f3d',
        '#1d8348',
        '#9a7d0a',
        '#9c640c',
        '#935116',
        '#873600',
        '#DFFF00',
        '#FFBF00',
        '#FF7F50',
        '#DE3163',
        '#9FE2BF',
        '#40E0D0',
        '#6495ED',
        '#CCCCFF'
    ]
    random.shuffle(colors)
    return colors


"""
print('##########################')
print('Hopfen: {}'.format(h['hopfen']))
print('Anzahl in Rezepten: {}'.format(len(all_recepies)))
print('Gesamtmenge: {}'.format(hopfen_sum))
"""