import http.client
import json
import smtplib
from smtplib import SMTPRecipientsRefused

import boto3
from botocore.exceptions import ClientError
from celery import shared_task

from GolfConnect.settings import SNS_REGION, S3_AWSKEY, S3_SECRET, CURRENT_ENV, XMPP_HOST, XMPP_PORT, \
    ANDROID_SNS_ARN_DEV, ANDROID_SNS_ARN_PROD, IOS_SNS_ARN_DEV, IOS_SNS_ARN_PROD, SETTINGS_PATH
from core.user.models import UserDevice, UserVersion
from django.contrib.auth.models import User
import urllib.parse as up
import urllib.request as ur
import optparse
import sys
import os
import xml.etree.cElementTree as ET
from django.template import Context,Template
from django.template.loader import render_to_string, get_template
from utils.django.models import get_or_none
from django.core.mail.message import (
    DEFAULT_ATTACHMENT_MIME_TYPE, BadHeaderError, EmailMessage,
    EmailMultiAlternatives, SafeMIMEMultipart, SafeMIMEText,
    forbid_multi_line_headers, make_msgid,
)

def set_endpoint_enabled(endpoint_arn, enabled=True):
    # Connect to AWS SNS
    sns = boto3.client('sns',
                       region_name=SNS_REGION,
                       aws_access_key_id=S3_AWSKEY,
                       aws_secret_access_key=S3_SECRET)

    return sns.set_endpoint_attributes(EndpointArn=endpoint_arn, Attributes={'Enabled': str(enabled)})

#@shared_task
#def send_email(subject, message, to):
#    msg = EmailMultiAlternatives(subject, message, 'GolfConnect24 <no-reply@golfconnect24.com>', to)
#    msg.attach_alternative(message, "text/html")
    # Send Email
#    try:
#        msg.send(fail_silently=True)
#    except (smtplib.socket.gaierror, SMTPRecipientsRefused, Exception) as e:
#        return str(e)
#    return True

@shared_task
def send_email(subject, data, email):
    ctx = {}
    template_data = Template(data)
    message = template_data.render(Context(ctx))
    msg = EmailMessage(subject, message, 'GolfConnect24 <no-reply@golfconnect24.com>', email)
    msg.content_subtype = "html"
    msg.send()
    return True

@shared_task
def update_version(userid, version, source):
    if userid.isdigit():
        user = get_or_none(User,pk=userid)
    else:
        user = User.objects.filter(email=userid.replace('%40','@')).first()
        version = 1
    if user:
        userversion, created = UserVersion.objects.get_or_create(user=user,source=source)
        userversion.version = version
        userversion.save()
    
@shared_task
def send_notification(user_ids, message, translate_message=None, badge=0, event_id=None, group_id=None):
    # Connect to AWS SNS
    print (user_ids, message, translate_message, badge, event_id, group_id)
    sns = boto3.client('sns',
                       region_name=SNS_REGION,
                       aws_access_key_id=S3_AWSKEY,
                       aws_secret_access_key=S3_SECRET)

    # Connect to Parse
    #connection = http.client.HTTPSConnection('api.parse.com', 443)
    #connection.connect()
    msg = {
        'message': message,
        'sound': 'default',
        'alert': message,
        'alert_vi': translate_message.get('alert_vi'),
        'alert_en': translate_message.get('alert_en')
    }
    if event_id is not None and event_id != 0:
        msg.update({'event_id': event_id})
    if group_id is not None and group_id != 0:
        msg.update({'group_id': group_id})
    if badge:
        msg.update({'badge': badge})

    payload = {
        'default': message,
        'APNS': json.dumps({
            'aps': msg
        }),
        'GCM': json.dumps({
            'data': msg
        }),
        'APNS_SANDBOX': json.dumps({
            'aps': msg
        }),
        '': json.dumps({
            'aps': msg
        })
    }
    for user_id in user_ids:
        devices = UserDevice.objects.filter(user_id=user_id)
        if devices:
            for d in devices:
                try:
                    set_endpoint_enabled(d.push_token)
                    r = sns.publish(TargetArn=d.push_token, Message=json.dumps(payload), MessageStructure='json')
                except ClientError as e:
                    print(e)
                    pass
        else:
            channels = CURRENT_ENV + '_user' + str(user_id)
            data = {
                "channels": [channels],
                "data": {
                    "sound": "default",
                    "alert": str(message)
                }
            }
            if translate_message:
                data['data'].update(translate_message)
            #connection.request('POST', '/1/push', json.dumps(data), {
            #    "X-Parse-Application-Id": "AixVJEQbPEKbQxStlLFgj6YvPPKyuKal84ufVuJP",
            #    "X-Parse-REST-API-Key": "wUtzoyjJqo3HEpauMSDazXfnXdH7pvR3gMR8ok1Z",
            #    "Content-Type": "application/json"
            #})
    #connection.close()
    return True

def send_register_email(display_name, email):
    instructional_register = os.path.join(SETTINGS_PATH,'media/email_template/instructional_register.html')
    if not os.path.exists(instructional_register):
        return False
    with open(instructional_register, encoding="utf-8") as f:
        data= f.read()
        data = data.replace('{display_name}', display_name)
        subject = 'Welcome to Golfconnect24'
        send_email.delay(subject,data, [email])
    return True

def send_after_booking_email(display_name, email):
    instructional_register = os.path.join(SETTINGS_PATH,'media/email_template/instructional_teetime.html')
    with open(instructional_register, encoding="utf-8") as f:
        data= f.read()
        data = data.replace('{display_name}', display_name)
        subject = 'Thank you for your booking from Golfconnect24'
        send_email.delay(subject,data, [email])
    return True

def broadcast_push_notification(devices, payload):
    sns = boto3.client('sns',
                       region_name=SNS_REGION,
                       aws_access_key_id=S3_AWSKEY,
                       aws_secret_access_key=S3_SECRET)

    for d in devices:
        try:
            sns.publish(TargetArn=d.push_id, Message=json.dumps(payload), MessageStructure='json')
        except:
            pass


def get_endpoint_arn(push_id, device_type):
    sns = boto3.client('sns',
                       region_name=SNS_REGION,
                       aws_access_key_id=S3_AWSKEY,
                       aws_secret_access_key=S3_SECRET)

    platform_arn = {
        'android_dev': ANDROID_SNS_ARN_DEV,
        'android_prod': ANDROID_SNS_ARN_PROD,
        'ios_dev': IOS_SNS_ARN_DEV,
        'ios_prod': IOS_SNS_ARN_PROD
    }.get(device_type)

    return sns.create_platform_endpoint(PlatformApplicationArn=platform_arn, Token=push_id)['EndpointArn']

def _get_by_username(username, event):
    u = up.quote(username)
    request_url = "http://{2}:{3}/myapi/room-message-count?u={0}&r={1}".format(u, event, XMPP_HOST, XMPP_PORT)
    try:
        with ur.urlopen(request_url) as f:
            a = f.read().decode('utf-8')
            d = json.loads(a)
            return (d['comment_count'], d['unread'])
    except:
        return (0, 0)
def _get_by_userid(user_id,event):
    try:
        request_url = "http://{2}:{3}/myapi/room-message-count?u={0}&r={1}".format(user_id, event, XMPP_HOST, XMPP_PORT)
        with ur.urlopen(request_url) as f:
            a = f.read().decode('utf-8')
            d = json.loads(a)
            return (d['comment_count'], d['unread'])
    except:
        return (0,0)
    
def _get_by_nonuser(event):
    request_url = "http://{1}:{2}/myapi/room-message-count?r={0}".format(event, XMPP_HOST, XMPP_PORT)
    try:
        with ur.urlopen(request_url) as f:
            a = f.read().decode('utf-8')
            d = json.loads(a)
            return (d['comment_count'], d['unread'])
    except:
        return (0, 0)

def get_from_xmpp(username, event):
    from v2.api.chatserviceMana.tasks import get_user_chat_statistic
    if CURRENT_ENV != 'prod':
        return (0, 0)
    if username:
        user = User.objects.filter(username=username).first()
        if not user:
            return (0,0)
        data = get_user_chat_statistic(user=user, room_id=[str(event)], is_notify=False, is_room=True)
        if not data:
            return (0,0)
        return (data[0]['comment_count'], data[0]['unread_count'])
    else:
        return _get_by_nonuser(event)
    
def get_from_xmpp_forgroup(username, event, date_joined):
    if CURRENT_ENV != 'prod':
        return (0, 0)
    request_url = ""
    if username:
        u = up.quote(username)
        dat = date_joined.isoformat('T') + 'Z'
        request_url = "http://{2}:{3}/myapi/room-message-count?u={0}&r={1}&d={4}".format(u, event, XMPP_HOST, XMPP_PORT, dat)
    try:
        with ur.urlopen(request_url) as f:
            a = f.read().decode('utf-8')
            d = json.loads(a)
            return (d['comment_count'], d['unread'])
    except:
        return (0, 0)

def get_badge_xmpp(username):
    # if CURRENT_ENV != 'prod':
    #     return 0, 0
    from v2.api.chatserviceMana.tasks import get_user_chat_statistic
    # if CURRENT_ENV != 'prod':
    #     return 0, 0
    print ('Push')
    if username:
        user = User.objects.filter(pk=username).first()
        if not user:
            return 0
        data = get_user_chat_statistic(user=user, room_id=[], is_notify=True, is_room=True)
        print (username, sum([d.get('unread_count',0) for d in data]))
        if not data:
            return 0
        return sum([d.get('unread_count',0) for d in data])
    else:
        return _get_by_nonuser(event)


def strip_tag(tag):
    strip_ns_tag = tag
    split_array = tag.split('}')
    if len(split_array) > 1:
        strip_ns_tag = split_array[1]
        tag = strip_ns_tag
    return tag


def elem_to_internal(elem, strip_ns=1, strip=1):
    """Convert an Element into an internal dictionary (not JSON!)."""

    d = {}
    elem_tag = elem.tag
    if strip_ns:
        elem_tag = strip_tag(elem.tag)
    else:
        for key, value in list(elem.attrib.items()):
            d[key] = value

    # loop over subelements to merge them
    for subelem in elem:
        v = elem_to_internal(subelem, strip_ns=strip_ns, strip=strip)

        tag = subelem.tag
        if strip_ns:
            tag = strip_tag(subelem.tag)

        value = v[tag]

        try:
            # add to existing list for this tag
            d[tag].append(value)
        except AttributeError:
            # turn existing entry into a list
            d[tag] = [d[tag], value]
        except KeyError:
            # add a new non-list entry
            d[tag] = value
    text = elem.text
    tail = elem.tail
    if strip:
        # ignore leading and trailing whitespace
        if text:
            text = text.strip()
        if tail:
            tail = tail.strip()

    if not d:
        d = text or None
    return {elem_tag: d}


def elem2json(elem, strip_ns=1, strip=1):

    """Convert an ElementTree or Element into a JSON string."""

    if hasattr(elem, 'getroot'):
        elem = elem.getroot()
    return elem_to_internal(elem, strip_ns=strip_ns, strip=strip)
    #return json.dumps()

def xml2json(xmlstring, strip_ns=1, strip=1):

    """Convert an XML string into a JSON string."""

    elem = ET.fromstring(xmlstring)
    return elem2json(elem, strip_ns=strip_ns, strip=strip)
