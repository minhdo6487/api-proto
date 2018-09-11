from celery import shared_task

from core.user.models import UserActivity
from GolfConnect.settings import XMPP_HOST, XMPP_PORT
from urllib.request import Request, urlopen
import json

@shared_task
def log_activity(user_id, verb, object_id, ctype_id, public=True):
    u = UserActivity.objects.filter(user_id=user_id, verb=verb, object_id=object_id, content_type_id=ctype_id).first()
    if u:
        u.public = public
        u.save()
    else:
        UserActivity.objects.create(user_id=user_id, verb=verb, object_id=object_id, content_type_id=ctype_id, public=public)
    return True

@shared_task
def query_online_user_xmpp():
    try:
        url = "http://{0}:{1}/myapi/online-list".format(XMPP_HOST, XMPP_PORT)
        req = Request(url)
        response = urlopen(req)
        d = json.loads(response.read().decode('utf-8'))
        return d
    except:
        return {'online_user':[]}

@shared_task
def get_last_modified_room(list_modified):
    try:
        url = "http://{0}:{1}/myapi/last-modified-room".format(XMPP_HOST, XMPP_PORT)
        data = {
            'event_id': list_modified,
        }
        req = Request(url, json.dumps(data).encode('utf8'))
        response = urlopen(req)
        d = json.loads(response.read().decode('utf-8'))
        return d
    except:
        return []

@shared_task
def get_unread_room(list_modified):
    try:
        url = "http://{0}:{1}/myapi/unread-room".format(XMPP_HOST, XMPP_PORT)
        data = {
            'event_id': list_modified
        }
        req = Request(url, json.dumps(data).encode('utf8'))
        response = urlopen(req)
        d = json.loads(response.read().decode('utf-8'))
        return d
    except:
        return []

@shared_task
def block_user(from_id):
    from core.user.models import UserPrivacy, GroupChat, UserGroupChat
    user_privacy = UserPrivacy.objects.filter(user_id=from_id, action='D')
    group1 = GroupChat.objects.filter(group_member__user_id=from_id).values_list('id',flat=True)
    data = []
    if not user_privacy.first():
        user_privacy = UserPrivacy.objects.filter(user_id=from_id, action='A')
    for uprivacy in user_privacy:
        group = GroupChat.objects.filter(group_member__user_id=uprivacy.target.id, id__in=list(group1)).values_list('group_id',flat=True)
        d = {
            'target_id': str(uprivacy.target.id),
            'group': [str(x) for x in list(group)],
            'action': 'deny' if uprivacy.action == 'D' else 'allow'
        }
        data.append(d)
    try:
        url = "http://{0}:{1}/myapi/block-user".format(XMPP_HOST, XMPP_PORT)
        data = {
            'from_id': str(from_id),
            'data': data
        }
        req = Request(url, json.dumps(data).encode('utf8'))
        response = urlopen(req)
        return
    except:
        pass