import smtplib
from smtplib import SMTPRecipientsRefused
import json
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
import base64
import datetime
from GolfConnect.settings import CURRENT_ENV
def send_generate_email(instance):
    str_booked_id = 'n' + str(instance.id)
    encode_data = base64.urlsafe_b64encode(str_booked_id.encode('ascii')).decode('ascii')
    domain = ''
    if CURRENT_ENV == 'prod':
        domain = "golfconnect24.com"
    else:
        domain = "dev.golfconnect24.com"
    request_url = 'https://'+domain+'#/booking-request/payment/'+str(encode_data)+'/'
    instance.paymentLink = request_url
    instance.save()
    subject = "Payment Link for user \"{0}\" with price \"{1}\" ".format(instance.custName, instance.totalAmount)
    to = instance.receiveEmail
    message = request_url
    send_email(subject, message, [to])

def send_email(subject, message, to):
    msg = EmailMultiAlternatives(subject, message, 'GolfConnect24 <no-reply@golfconnect24.com>', to)
    msg.attach_alternative(message, "text/html")
    # Send Email
    try:
        msg.send(fail_silently=True)
    except (smtplib.socket.gaierror, SMTPRecipientsRefused, Exception):
        return False
    return True


def send_notification(channels, data):
    connection = http.client.HTTPSConnection('api.parse.com', 443)
    connection.connect()
    connection.request('POST', '/1/push', json.dumps({
        "channels": [channels],
        "data": {
            "sound": "default",
            "alert": str(data)
        }
    }), {
                           "X-Parse-Application-Id": "AixVJEQbPEKbQxStlLFgj6YvPPKyuKal84ufVuJP",
                           "X-Parse-REST-API-Key": "wUtzoyjJqo3HEpauMSDazXfnXdH7pvR3gMR8ok1Z",
                           "Content-Type": "application/json"
                       })
    connection.close()
    return True