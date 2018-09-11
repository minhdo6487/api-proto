from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.conf import settings

admin.autodiscover()

urlpatterns = patterns('',
                       url(r'^api/', include('api.urls')),
                       url(r'^api/v2/', include('v2.api.urls')),
                       url(r'^api/grappelli/', include('grappelli.urls')),  # grappelli URLS
                       url(r'^api/gc24/assmin/', include(admin.site.urls)),
                       url(r'^staff/', include(admin.site.urls)),
                       ) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
