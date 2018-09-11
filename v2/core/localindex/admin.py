from django.contrib import admin
import reversion

from .models import *

class LocalIndexAdmin(admin.ModelAdmin):
    raw_id_fields = ('golfcourse','user')

admin.site.register(LocalIndex, LocalIndexAdmin)

class LocalNameAdmin(admin.ModelAdmin):
	pass

admin.site.register(LocalName, LocalNameAdmin)