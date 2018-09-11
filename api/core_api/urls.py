from django.conf.urls import url
from .views import version

urlpatterns = [
    url(r'version', version)
]
