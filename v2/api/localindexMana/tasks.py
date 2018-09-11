import datetime
from celery import shared_task
from GolfConnect.celery import celery_is_up
from django.db.models import Q
from v2.utils.geohash_service import get_geoname_by_location
from v2.core.localindex.models import LocalIndex

def save_location(user_id=None,golfcourse_id=None,latitude=None,longitude=None):

    local_name = get_geoname_by_location(lat=latitude,lng=longitude)
    print (user_id, golfcourse_id, latitude, longitude, local_name)
    if not local_name:
        return False
    localindex, created = LocalIndex.objects.get_or_create(user_id=user_id,golfcourse_id=golfcourse_id)
    if created or not localindex.geoname:
        localindex.geoname = local_name
        localindex.save()
    return True

@shared_task
def __init_location_by_GPS():
    from core.user.models import UserLocation
    from core.golfcourse.models import GolfCourse
    #### Init Golfcourse
    golfcourse = GolfCourse.objects.all().values('id','latitude','longitude')
    [save_location(golfcourse_id=gc['id'], latitude=gc['latitude'], longitude=gc['longitude']) for gc in golfcourse]
    #### Init UserLocation
    user = UserLocation.objects.all().values('user_id','lat','lon')
    [save_location(golfcourse_id=us['user_id'], latitude=us['lat'], longitude=us['lon']) for us in user]
    return True

def init_location_by_GPS():
    if celery_is_up():
        __init_location_by_GPS.delay()
    else:
        __init_location_by_GPS()

#def update_location_by_GPS(sender, instance, created, **kwargs):
#   if celery_is_up():
#       __create_event_from_booking.delay(instance.user_email)
#   else:
#       __create_event_from_booking(instance.user_email)