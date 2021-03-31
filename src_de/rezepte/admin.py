from django.contrib import admin
from .models import Rezept, Malz, Maischen, Hopfenplan, Temperaturlogging
# Register your models here.
admin.site.register(Rezept)
admin.site.register(Malz)
admin.site.register(Maischen)
admin.site.register(Hopfenplan)
admin.site.register(Temperaturlogging)