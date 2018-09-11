__author__ = 'toantran'
from django.contrib import admin

from .models import Gallery


class GalleryAdmin(admin.ModelAdmin):
    pass


admin.site.register(Gallery, GalleryAdmin)