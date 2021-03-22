from django.shortcuts import render
from django.http import HttpResponse 
from datetime import datetime
from rezepte.models import Rezept

# Create your views here.
def home_view(request, *args, **kwargs):
	# hole alle Rezepte aus der Datenbank und speichere in obj
	obj = Rezept.objects.all().order_by('-datum')
	# Lege Liste für die Übersicht an
	allRecepies = []
	for o in obj:
		allRecepies.append([o.titel, o.datum.strftime("%Y-%m-%d")])

	context = {
		'rezepte': allRecepies, 
		'objects': obj
	}

	return render(request, "home.html", context)
