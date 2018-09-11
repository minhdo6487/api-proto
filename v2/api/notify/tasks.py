"""
Push notification tasks
"""

from datetime import date

import arrow
from core.user.models import UserProfile
from . import models
from api.noticeMana.tasks import send_notification
from GolfConnect.settings import TIME_ZONE


def send_expired_schedules():
    """Query expired and send campaign to users"""
    limit = 1000
    now = arrow.now(TIME_ZONE)
    schedules = models.Schedule.objects.filter(sent_at__isnull=True, timed_at__gte=now.datetime)[:limit]
    for schedule in schedules:
        camp = models.Camp.objects.get(id=schedule.camp_id)
        if camp:
            send_camp(camp, schedule)


def send_camp(camp, schedule):
    # build query to load users
    now = arrow.now()
    min_date = date(now.datetime.year - camp.age_max, now.datetime.month, now.datetime.day)
    max_date = date(now.datetime.year - camp.age_min, now.datetime.month, now.datetime.day)
    filters = {
        'dob__gte': min_date,
        'dob__lte': max_date,
    }
    if camp.gender != '-':
        filters['gender'] = camp.gender.upper()
    raw_city_ids = camp.city_ids.split(',')
    city_ids = []
    for city_id in raw_city_ids:
        try:
            city_ids.append(int(city_id))
        except:
            pass
        
    if city_ids:
        filters['city_id__in'] = city_ids
    profiles = UserProfile.objects.filter(**filters)
    for profile in profiles:
        # do send notify
        title = camp.title
        body = camp.body
        send_notification([profile.user_id], body, {})
        log = models.CampLog(user_id=profile.user_id, schedule_id=schedule.id, title=title, body=body)
        log.save()
    
    schedule.sent_at = now.datetime
    schedule.save()
    
    # check completed camp
    remaining = models.Schedule.objects.filter(sent_at__isnull=True, camp_id=camp.id).count()
    if remaining == 0:
        camp.sent_at = now.datetime
        camp.save()
