from django.contrib import admin

from . import models


class CampAdmin(admin.ModelAdmin):
    pass


class CampLogAdmin(admin.ModelAdmin):
    pass


admin.site.register(models.Camp, CampAdmin)
admin.site.register(models.CampLog, CampLogAdmin)
