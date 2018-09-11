import logging
from GolfConnect.settings import CURRENT_ENV
from core.game.models import EventMember
from core.realtime.models import UserSubcribe
from django.db.models import Sum
import json
import http.client
__author__ = 'toantran'
from celery import shared_task
TPL_STR = CURRENT_ENV + '_user'
# def send_notification_to_subcribe_user(api, username, user_id, ctype, object_id):
#     try:
#         user_subcribe = UserSubcribe.objects.get(content_type_id=ctype, object_id=object_id)
#         connection = http.client.HTTPSConnection('api.parse.com', 443)
#         connection.connect()
#         for id in eval(user_subcribe.user):
#             if id != user_id:
#                 channel = TPL_STR + str(id)
#                 try:
#                     m, created = UserBadge.objects.get_or_create(user_id=id, event_id=object_id)
#                     m.count += 1
#                     m.save(update_fields=['count'])
#                 except Exception as e:
#                     pass
#                 badge = UserBadge.objects.filter(user_id=id).aggregate(Sum('count'))['count__sum']
#                 if not badge:
#                     badge = 0
#                 # alert_vi = username + ' đã bình luận về sự kiện của bạn'
#                 # alert_en = username + ' commented on your event'
#
#                 r = connection.request('POST', '/1/push', json.dumps({
#                     "channels": [channel],
#                     "data": {
#                         #"sound": "default",
#                         "api":api,
#                         # "alert":"Test send badge",
#                         "badge":badge,
#                         # "alert_vi": str(alert_vi),
#                         # "alert_en": str(alert_en),
#                         # "alert": str(alert_en)
#                     }
#                 }), {
#                                        "X-Parse-Application-Id": "AixVJEQbPEKbQxStlLFgj6YvPPKyuKal84ufVuJP",
#                                        "X-Parse-REST-API-Key": "wUtzoyjJqo3HEpauMSDazXfnXdH7pvR3gMR8ok1Z",
#                                        "Content-Type": "application/json"
#                                    })
#         connection.close()
#         return True
#     except Exception as e:
#         print(e)
#         return False

def send_notification_event_channel(api, channel):
    try:
        print(channel)
        connection = http.client.HTTPSConnection('api.parse.com', 443)
        connection.connect()
        connection.request('POST', '/1/push', json.dumps({
            "channels":[channel],
            "data": {
                "sound": "default",
                "api": api,
                "alert": "Update Event"
            }
        }), {
                               "X-Parse-Application-Id": "AixVJEQbPEKbQxStlLFgj6YvPPKyuKal84ufVuJP",
                               "X-Parse-REST-API-Key": "wUtzoyjJqo3HEpauMSDazXfnXdH7pvR3gMR8ok1Z",
                               "Content-Type": "application/json"
                           })
        connection.close()
        return True
    except Exception as e:
        print(e)
        return False