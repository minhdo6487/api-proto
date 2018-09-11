__author__ = 'toantran'
__author__ = 'toantran'
from django.contrib import admin

from .models import *


class CountryAdmin(admin.ModelAdmin):
    pass


admin.site.register(Country, CountryAdmin)

class CityAdmin(admin.ModelAdmin):
    pass


admin.site.register(City, CityAdmin)

class DistrictAdmin(admin.ModelAdmin):
    pass


admin.site.register(District, DistrictAdmin)