import datetime
from core.golfcourse.models import (
                                GolfCourseEvent,)
from core.notice.models import (
                                Notice,)
from core.user.models import (
                            UserGroupChat,)
from api.userMana.tasks import (
                            get_last_modified_room,
                            get_unread_room)
from v2.core.chatservice.models import (
                                UserChatPresence,)
from django.contrib.contenttypes.models import (
                                ContentType,)

from celery import (
                shared_task,)

from GolfConnect.celery import celery_is_up
from .serializers import UserChatQuerySerializer


event_ctype = ContentType.objects.get_for_model(GolfCourseEvent)

@shared_task
def __remove_too_long_status(room):
    UserChatPresence.objects.filter(room_id__in=room).delete()
    return True

def remove_too_long_status(room_id):
    print ("Tuan Ly: remove too long status: {}".format(room_id))
    if celery_is_up():
        __remove_too_long_status.delay(room_id)
    else:
        __remove_too_long_status(room_id)


def __get_first_day_last_month():
    today = datetime.datetime.today()
    first_today = today.replace(day=1)
    from_date = first_today - datetime.timedelta(days=1)
    from_date = from_date.replace(day=1, hour=0, minute=0, second=0)
    return int(from_date.timestamp())

def __get_statistic_notification(user):
    today = datetime.datetime.today().date()
    notifications = Notice.objects.filter(to_user=user, notice_type__in=['I', 'G', 'FR'])
    notifications = list(
        filter(lambda x: (x.content_type == event_ctype and x.related_object and x.related_object.date_start >= today) or (x.content_type != event_ctype),
               notifications))
    return [{'record_type': 'notice', 'record_id': 1, 'unread_count': len(notifications) or 0, 'comment_count': len(notifications) or 0}]

def __get_statistic_roomchat(user):
    user_presence = UserChatPresence.objects.get_offline(user_id=user.id)
    user_room = user_presence.values_list('room_id', flat=True)
    rooms_last_modified = get_last_modified_room(list(user_room))
    flag_point = __get_first_day_last_month()
    room = [x['event_id'] for x in rooms_last_modified 
                if x['timestamp'] and not ('group'in x['event_id'] and int(x['timestamp']) < flag_point)]
    unused_room = [x for x in list(user_room) if x not in room]
    #remove_too_long_status(unused_room)
    user_room = user_presence.filter(room_id__in=room)
    my_data = UserChatQuerySerializer(user_room)
    data = get_unread_room(my_data.data)
    return data

def __get_statistic_groupchat(user, room):
    user_off = UserChatPresence.objects.get_offline(user_id=user.id)
    user_onl = UserChatPresence.objects.get_online(user_id=user.id)
    modi = "{}Z".format(datetime.datetime.utcnow().isoformat('T'))
    my_data = []
    for r in room:
        if 'activity' in r:
            continue
        user_groupchat = UserGroupChat.objects.filter(user=user, groupchat__group_id=r).first()
        user_offline = user_off.filter(room_id=r).order_by('id').first()
        user_online = user_onl.filter(room_id=r).order_by('id').first()
        d = {'room_id': r,
             'modified_at': modi}
        if user_groupchat:
            d.update({'date_joined': "{}Z".format(user_groupchat.date_joined.isoformat('T')),
                      'modified_at': "{}Z".format(user_groupchat.date_joined.isoformat('T'))})
        if user_offline:
            d.update({'modified_at': "{}Z".format(user_offline.modified_at.isoformat('T'))})

        if user_online:
            d.update({'modified_at': modi})
        my_data.append(d)
    if my_data:
        return get_unread_room(my_data)
    else:
        return []

def get_user_chat_statistic(user=None, room_id=[], is_notify=True, is_room=True):
    notice = []
    room = []
    group = []
    if is_notify:
        notice = __get_statistic_notification(user)
    if is_room and not room_id:
        room = __get_statistic_roomchat(user)
    if is_room and room_id:
        group = __get_statistic_groupchat(user, room_id)
    data = notice + room + group
    return data
