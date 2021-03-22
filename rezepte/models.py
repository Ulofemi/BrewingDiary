from django.db import models
import datetime
from django.urls import reverse
# Create your models here.

class Rezept(models.Model):
	class Meta:
		verbose_name_plural = "Rezepte"

	mashingProcess = (
	('heizen','Aufheizen'),
	('einmaischen','Einmaischen'),
    ('ersteRast', '1. Rast'),
    ('zweiteRast','2. Rast'),
    ('dritteRast','3. Rast'),
    ('vierteRast','4. Rast'),
    ('abmaischen','Abmaischen'),
    ('läutern','Läutern'),
    ('kochen','Kochen'),
    ('kühlen','Kühlen'),
    ('gärung','Gärung'),
    ('ende','Ende'),
    )
	
	# Datum, Titel und Stil
	datum = models.DateField(default=datetime.date.today())
	titel = models.CharField(max_length=120)
	stil = models.CharField(max_length=120)
	url = models.CharField(max_length=500, blank=True)
	
	# Zielvolumen und HG + NG
	zielvolumen = models.DecimalField(max_digits=3, decimal_places=1)
	hauptguss = models.DecimalField(max_digits=3, decimal_places=1)
	nachguss = models.DecimalField(max_digits=3, decimal_places=1)

	# Stammwürze, Restextrakt, Alkohol und Hefe
	stammwuerze = models.DecimalField(max_digits=3, decimal_places=1, blank=True)
	restextrakt = models.DecimalField(max_digits=3, decimal_places=1, blank=True)
	alkohol = models.DecimalField(max_digits=3, decimal_places=1, blank=True)
	hefe = models.CharField(max_length=120)

	# Hopfendetails
	bittere = models.DecimalField(max_digits=3, decimal_places=1, blank=True)
	hopfenkochzeit = models.DecimalField(max_digits=3, decimal_places=0)
	
	# Karbonisierung
	karbonisierung = models.DecimalField(max_digits=3, decimal_places=1, blank=True, default=5.0)
	
	# Sonstiges
	notizen = models.TextField(blank=True)

	# Logging wird als Variable verwendet --> Wenn True, dann werden Temperaturen in die DB gespeichert
	logging = models.BooleanField(default=False)

	# Intervall (wie oft sollen Temperaturen g espeichert werden in Sekunden)
	intervall = models.DecimalField(max_digits=3, decimal_places=0, default=180)

	# Aktueller Prozess
	aktuellerProzess = models.CharField(max_length=120, choices=mashingProcess, default='heizen')
	naechsterProzess = models.CharField(max_length=120, choices=mashingProcess, default='einmaischen')
	zeitstempelProzess = models.DateTimeField(blank=True, default=datetime.datetime(year=2020, month=1, day=1, hour=1, minute=0, second=0))

	# Anzeige im Admininterface
	def __str__(self):
		return f'{self.datum}, {self.titel}'

	def get_absolute_detail_url(self):
		return reverse("rezept", kwargs={"id": self.id})		#f"rezept/{self.id}/"

	def get_absolute_temp_url(self):
		return reverse("graph", kwargs={"id": self.id})		#f"rezept/{self.id}/"

	def get_absolute_edit_url(self):
		return reverse("edit", kwargs={"id": self.id})		#f"rezept/{self.id}/"

	"""
	# Ein paar Getter
	def getTitel(self):
		return self.titel
	def getDatum(self):
		return self.datum
	def getId(self):
		return self.id
	"""


class Malz(models.Model):
	class Meta:
		verbose_name_plural = "Malz"

	rezept = models.ForeignKey('Rezept', on_delete=models.CASCADE)
	sorte = models.CharField(max_length=120)
	menge = models.DecimalField(max_digits=4, decimal_places=2)
	notizen = models.TextField(blank=True)

	# Anzeige im Admininterface
	def __str__(self):
		return f'{self.rezept}, {self.sorte}'



class Maischen(models.Model):
	class Meta:
		verbose_name_plural = "Maischen"

	mashingProcess = (
    ('einmaischen','Einmaischen'),
    ('ersteRast', '1. Rast'),
    ('zweiteRast','2. Rast'),
    ('dritteRast','3. Rast'),
    ('vierteRast','4. Rast'),
    ('abmaischen','Abmaischen'),
    )

	rezept = models.ForeignKey('Rezept', on_delete=models.CASCADE)
	prozess = models.CharField(max_length=120, choices=mashingProcess)
	temperatur = models.DecimalField(max_digits=3, decimal_places=1)
	dauer = models.DecimalField(max_digits=4, decimal_places=2)
	notizen = models.TextField(blank=True)

	# Anzeige im Admininterface
	def __str__(self):
		return f'{self.rezept}, {self.prozess}'



class Hopfenplan(models.Model):
	class Meta:
		verbose_name_plural = "Hopfenplan"

	hopUse = (
    ('kochen','Kochen'),
    ('whirlpool','Whirlpool'),
    ('stopfen','Stopfen'),
    )

	rezept = models.ForeignKey('Rezept', on_delete=models.CASCADE)
	hopfen = models.CharField(max_length=120)
	menge = models.DecimalField(max_digits=3, decimal_places=1)
	verwendung = models.CharField(max_length=120, choices=hopUse)
	dauer = models.DecimalField(max_digits=4, decimal_places=2)
	temperatur = models.DecimalField(max_digits=3, decimal_places=1)
	notizen = models.TextField(blank=True)

	# Anzeige im Admininterface
	def __str__(self):
		return f'{self.rezept}, {self.hopfen}, {self.verwendung}'

	"""
	def getHopfen(self):
		return self.hopfen
	"""


class Temperaturlogging(models.Model):
	class Meta:
		verbose_name_plural = "Temperaturlogging"

	rezept = models.ForeignKey('Rezept', on_delete=models.CASCADE)
	zeitstempel = models.DateTimeField()
	sollwert = models.DecimalField(max_digits=5, decimal_places=2, default=20.0) 
	sensor1 = models.DecimalField(max_digits=5, decimal_places=2)
	sensor2 = models.DecimalField(max_digits=5, decimal_places=2)
	prozess = models.CharField(max_length=120)

	# Anzeige im Admininterface
	def __str__(self):
		return f'{self.zeitstempel}'