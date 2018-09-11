import googlemaps
from GolfConnect.settings import GOOGLE_MAP_API_KEY
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage


__author__ = 'toantran'


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def paginate_query(query, page, item):
    paginator = Paginator(query, item)
    try:
        paginate = paginator.page(page)
    except PageNotAnInteger:
        paginate = paginator.page(1)
    except EmptyPage:
        paginate = paginator.page(paginator.num_pages)
    return paginate


def get_distance(origins, destionations):
    gmaps = googlemaps.Client(key=GOOGLE_MAP_API_KEY)
    return gmaps.distance_matrix(origins, destionations)