from django import forms 
from .models import Rezept, Malz, Maischen, Hopfenplan
import datetime




# ModelForm
class RezeptForm(forms.ModelForm):

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

	datum = forms.DateField(initial=datetime.date.today())
	titel = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Pixelpils'}))
	stil = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Pils'}))
	url = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'http://masichemalzundmehr.de'}))

	zielvolumen = forms.DecimalField(widget=forms.NumberInput(attrs={'placeholder': '30.0'}))
	hauptguss = forms.DecimalField(widget=forms.NumberInput(attrs={'placeholder': '24.0'}))
	nachguss = forms.DecimalField(widget=forms.NumberInput(attrs={'placeholder': '18.0'}))

	stammwuerze = forms.DecimalField(required=False, widget=forms.NumberInput(attrs={'placeholder': '11.0'}))
	restextrakt = forms.DecimalField(required=False, widget=forms.NumberInput(attrs={'placeholder': '3.0'}))
	alkohol = forms.DecimalField(required=False, widget=forms.NumberInput(attrs={'placeholder': '5.1'}))
	hefe = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Nottingham'}))

	bittere = forms.DecimalField(required=False, widget=forms.NumberInput(attrs={'placeholder': '35.0'}))
	hopfenkochzeit = forms.DecimalField(widget=forms.NumberInput(attrs={'placeholder': '90'}))
	karbonisierung = forms.DecimalField(required=False, widget=forms.NumberInput(attrs={'placeholder': '5.1'}))

	notizen = forms.CharField(
                        required=False, 
                        widget=forms.Textarea())

	logging = forms.BooleanField(required=False, initial=False)
	intervall = forms.DecimalField(widget=forms.NumberInput(attrs={'placeholder': '300'}))

	aktuellerProzess = forms.ChoiceField(choices=mashingProcess)
	naechsterProzess = forms.ChoiceField(choices=mashingProcess)
	zeitstempelProzess = forms.DateTimeField(initial=datetime.datetime.now())	


	class Meta:
		model = Rezept
		fields = [
            'datum',
            'titel',
            'stil',
            'url',
            'zielvolumen',
            'hauptguss',
            'nachguss',
            'stammwuerze',
            'restextrakt', 
            'alkohol', 
            'hefe', 
            'bittere', 
            'hopfenkochzeit', 
            'karbonisierung', 
            'notizen',
            'logging', 
            'intervall', 
            'aktuellerProzess', 
            'naechsterProzess', 
            'zeitstempelProzess'
        ]


class MalzForm(forms.ModelForm):
	rezept = forms.ModelChoiceField(queryset=Rezept.objects.all())
	class Meta:
		model = Malz
		fields = [
			'rezept',
			'sorte', 
			'menge', 
			'notizen'
		]

	def __init__(self, *args, **kwargs):
		recepy = kwargs.pop('r','')
		super(MalzForm, self).__init__(*args, **kwargs)
		self.fields['rezept']=forms.ModelChoiceField(Rezept.objects.all(), initial=recepy)


class MaischeForm(forms.ModelForm):
	mashingProcess = (
    ('einmaischen','Einmaischen'),
    ('ersteRast', '1. Rast'),
    ('zweiteRast','2. Rast'),
    ('dritteRast','3. Rast'),
    ('vierteRast','4. Rast'),
    ('abmaischen','Abmaischen'),
    )

	rezept = forms.ModelChoiceField(queryset=Rezept.objects.all())
	prozess = forms.ChoiceField(choices=mashingProcess)
	class Meta:
		model = Maischen
		fields = [
			'rezept',
			'prozess', 
			'temperatur', 
			'dauer',
			'notizen'
		]

	def __init__(self, *args, **kwargs):
		r = kwargs.pop('r','')
		super(MaischeForm, self).__init__(*args, **kwargs)
		self.fields['rezept']=forms.ModelChoiceField(Rezept.objects.all(), initial=r)



class HopfenForm(forms.ModelForm):
	hopUse = (
    ('kochen','Kochen'),
    ('whirlpool','Whirlpool'),
    ('stopfen','Stopfen'),
    )

	rezept = forms.ModelChoiceField(queryset=Rezept.objects.all())
	verwendung = forms.ChoiceField(choices=hopUse)

	class Meta:
		model = Hopfenplan
		fields = [
			'rezept',
			'hopfen', 
			'menge', 
			'verwendung', 
			'dauer',
			'temperatur', 
			'notizen'
		]

	def __init__(self, *args, **kwargs):
		r = kwargs.pop('r','')
		super(HopfenForm, self).__init__(*args, **kwargs)
		self.fields['rezept']=forms.ModelChoiceField(Rezept.objects.all(), initial=r)

