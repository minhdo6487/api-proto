import base64
import json
from utils.rest.sendemail import send_email
from email.mime.image import MIMEImage
from api.bookingMana.serializers import BookedTeeTimeSerializer, BookedTeeTime_HistorySerializer, BookedPartner_HistorySerializer
from core.booking.models import BookedTeeTime, BookedPartner, BookedTeeTime_History, BookedPartner_History, BookedBuggy, BookedCaddy, PayTransactionStore, Voucher, BookedPayonlineLink,BookedGolfcourseEvent,BookedGolfcourseEventDetail
from core.teetime.models import GCSetting, TeeTime, TeeTimePrice, GuestType, PriceType, PriceMatrix, PriceMatrixLog, Holiday
from utils.django.models import get_or_none
from pytz import timezone, country_timezones
import datetime
from django.core.mail import EmailMultiAlternatives, EmailMessage
from core.golfcourse.models import GolfCourseStaff
from GolfConnect.settings import REDIS_HOST, REDIS_PORT, REDIS_DB, CURRENT_ENV, PAYMERCHANTCODE, PAYPASSCODE, PAYSECRETKEY, PAYURL
from django.utils.timezone import utc, pytz
from django.template import Context,Template
from django.template.loader import render_to_string, get_template
import redis
from celery import shared_task, task
from GolfConnect.settings import REDIS_HOST, REDIS_PORT, REDIS_DB, SETTINGS_PATH
redis_server = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
import os
import http.client
from hashlib import sha1, sha256
from django.contrib.sites.models import Site
from celery.utils.log import get_task_logger
from celery.task.schedules import crontab
from celery.decorators import periodic_task
from suds.client import Client
from django.core.mail.message import (
	DEFAULT_ATTACHMENT_MIME_TYPE, BadHeaderError, EmailMessage,
	EmailMultiAlternatives, SafeMIMEMultipart, SafeMIMEText,
	forbid_multi_line_headers, make_msgid,
)
logger = get_task_logger(__name__)
from collections import OrderedDict
DOW = {
	'Monday': 'Thứ Hai',
	'Tuesday': 'Thứ Ba',
	'Wednesday': 'Thứ Tư',
	'Thursday': 'Thứ Năm',
	'Friday': 'Thứ Sáu',
	'Saturday': 'Thứ Bảy',
	'Sunday': 'Chủ Nhật',
}
VNG = '123Pay'
VTC = 'VTCPay'
EMAIL_TEMPLATE_PATH = os.path.join(SETTINGS_PATH,'media/email_template/')
EMAIL_TEMPLATE_TYPE = {
	'REQUEST_CANCEL' : EMAIL_TEMPLATE_PATH + 'booking_cancellation.html',
	'NOTIFY_CANCELLED' : EMAIL_TEMPLATE_PATH + 'booking_cancelled.html'
}
VTC_STATUS_MAPPING = {
	'1': '1',
	'2': '1',
	'7': '10',
	'0': '20',
	'-1': '-100',
	'-5': '-10',
	'-6': '7201',
	'-99': '-100',
	'-699': '10'
}
def get_client_ip(request):
	x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
	if x_forwarded_for:
		ip = x_forwarded_for.split(',')[0]
	else:
		ip = request.META.get('REMOTE_ADDR')
	return ip
def notify_unlock(teetime):
	channel = 'booking-' + str(teetime.date)
	msg = {
		"id": teetime.id,
		"is_block": False
	}
	d = json.dumps(msg)
	redis_server.publish(channel, d)


def payment_queryOrder(paymentStore, request):
	clientIP = get_client_ip(request)
	values = OrderedDict()
	values['mTransactionID']= paymentStore.transactionId
	values['merchantCode']= PAYMERCHANTCODE
	values['clientIP']= clientIP
	values['passcode']= PAYPASSCODE
	headers = {
			'content-type': "application/json",
			'accept': "application/json",
		}
	cs = values['mTransactionID']+values['merchantCode']+values['clientIP']+values['passcode']+PAYSECRETKEY
	hashed = sha1(cs.encode('utf-8'))
	values['checksum'] = hashed.hexdigest()
	conn = http.client.HTTPSConnection(PAYURL)
	pay_url = "/queryOrder1"
	if CURRENT_ENV == 'prod':
		pay_url = "/queryOrder1"
	else:
		pay_url = "/miservice/queryOrder1"
	conn.request("POST", pay_url, json.dumps(values), headers)
	res = conn.getresponse()
	response_tuanly = json.loads(res.read().decode('utf-8'))
	print (response_tuanly)
	if not (int(response_tuanly[0]) == 1):
		return int(response_tuanly[0])
	else:
		returnCode = response_tuanly[0]
		paymentStore.payTransactionid = response_tuanly[1]
		transactionStatus = response_tuanly[2]
		paymentStore.totalAmount = response_tuanly[3]
		paymentStore.opAmount = response_tuanly[4]
		paymentStore.bankCode = response_tuanly[5]
		paymentStore.description = response_tuanly[6]
		paymentStore.save()
		return int(transactionStatus)

def auto_payment_queryOrder():
	list_paymentStore = PayTransactionStore.objects.filter(transactionStatus="0")
	domain = "golfconnect24.com"
	if CURRENT_ENV == 'prod':
		domain = "golfconnect24.com"
	else:
		domain = "dev.golfconnect24.com"
	if list_paymentStore.exists():
		for paymentStore in list_paymentStore:
			queryOrder(paymentStore,domain)
	else:
		return
def queryOrder(paymentStore,domain):
	if 't' in paymentStore.transactionId:
		booked_id = paymentStore.transactionId[paymentStore.transactionId.index('t')+1:]
		booked = get_or_none(BookedTeeTime,pk=int(booked_id))
		if not booked:
			paymentStore.transactionStatus="-100"
			paymentStore.save()
			return
		if paymentStore.vendor == VNG:
			values = OrderedDict()
			values['mTransactionID']= paymentStore.transactionId
			values['merchantCode']= PAYMERCHANTCODE
			values['clientIP']= paymentStore.clientIP
			values['passcode']= PAYPASSCODE
			headers = {
					'content-type': "application/json",
					'accept': "application/json",
				}
			cs = values['mTransactionID']+values['merchantCode']+values['clientIP']+values['passcode']+PAYSECRETKEY
			hashed = sha1(cs.encode('utf-8'))
			values['checksum'] = hashed.hexdigest()
			conn = http.client.HTTPSConnection(PAYURL)
			pay_url = "/queryOrder1"
			if CURRENT_ENV == 'prod':
				pay_url = "/queryOrder1"
			else:
				pay_url = "/miservice/queryOrder1"
			conn.request("POST", pay_url, json.dumps(values), headers)
			res = conn.getresponse()
			response_tuanly = json.loads(res.read().decode('utf-8'))
			print (response_tuanly)
			transactionStatus = int(response_tuanly[0])
			if (transactionStatus == 1):
				paymentStore.payTransactionid = response_tuanly[1]
				transactionStatus = int(response_tuanly[2])
				paymentStore.totalAmount = response_tuanly[3]
				paymentStore.opAmount = response_tuanly[4]
				paymentStore.bankCode = response_tuanly[5]
				paymentStore.description = response_tuanly[6]
				paymentStore.save()
			if (transactionStatus == 0):
				res_ts = str(int(datetime.datetime.utcnow().replace(tzinfo=utc).timestamp()))
				booked_ts = booked.created + datetime.timedelta(minutes=8)
				booked_ts = booked_ts.timestamp()
				if int(booked_ts) <= int(res_ts):
					transactionStatus = -100
				else:
					return
			if (transactionStatus == 20 or transactionStatus == 10):
				res_ts = str(int(datetime.datetime.utcnow().replace(tzinfo=utc).timestamp()))
				booked_ts = booked.created + datetime.timedelta(minutes=8)
				booked_ts = booked_ts.timestamp()
				if int(booked_ts) <= int(res_ts):
					transactionStatus = -100
	elif 'n' in paymentStore.transactionId:
		booked_id = paymentStore.transactionId[paymentStore.transactionId.index('n')+1:]
		booked = get_or_none(BookedPayonlineLink,pk=int(booked_id))
		if not booked:
			paymentStore.transactionStatus="-100"
			paymentStore.save()
			return
		values = OrderedDict()
		values['mTransactionID']= paymentStore.transactionId
		values['merchantCode']= PAYMERCHANTCODE
		values['clientIP']= paymentStore.clientIP
		values['passcode']= PAYPASSCODE
		headers = {
				'content-type': "application/json",
				'accept': "application/json",
			}
		cs = values['mTransactionID']+values['merchantCode']+values['clientIP']+values['passcode']+PAYSECRETKEY
		hashed = sha1(cs.encode('utf-8'))
		values['checksum'] = hashed.hexdigest()
		conn = http.client.HTTPSConnection(PAYURL)
		pay_url = "/queryOrder1"
		if CURRENT_ENV == 'prod':
			pay_url = "/queryOrder1"
		else:
			pay_url = "/miservice/queryOrder1"
		conn.request("POST", pay_url, json.dumps(values), headers)
		res = conn.getresponse()
		response_tuanly = json.loads(res.read().decode('utf-8'))
		print (response_tuanly)
		transactionStatus = int(response_tuanly[0])
		if (transactionStatus == 1):
			paymentStore.payTransactionid = response_tuanly[1]
			transactionStatus = int(response_tuanly[2])
			paymentStore.totalAmount = response_tuanly[3]
			paymentStore.opAmount = response_tuanly[4]
			paymentStore.bankCode = response_tuanly[5]
			paymentStore.description = response_tuanly[6]
			paymentStore.save()
		if (transactionStatus == 0):
			res_ts = str(int(datetime.datetime.utcnow().replace(tzinfo=utc).timestamp()))
			booked_ts = paymentStore.created + datetime.timedelta(minutes=8)
			booked_ts = booked_ts.timestamp()
			if int(booked_ts) <= int(res_ts):
				transactionStatus = -100
			else:
				return
			if (transactionStatus == 20 or transactionStatus == 10):
				res_ts = str(int(datetime.datetime.utcnow().replace(tzinfo=utc).timestamp()))
				booked_ts = paymentStore.created + datetime.timedelta(minutes=8)
				booked_ts = booked_ts.timestamp()
				if int(booked_ts) <= int(res_ts):
					transactionStatus = -100
	elif 'e' in paymentStore.transactionId:
		booked_id = paymentStore.transactionId[paymentStore.transactionId.index('e')+1:]
		booked = get_or_none(BookedGolfcourseEvent,pk=int(booked_id))
		if not booked:
			paymentStore.transactionStatus="-100"
			paymentStore.save()
			return
		values = OrderedDict()
		values['mTransactionID']= paymentStore.transactionId
		values['merchantCode']= PAYMERCHANTCODE
		values['clientIP']= paymentStore.clientIP
		values['passcode']= PAYPASSCODE
		headers = {
				'content-type': "application/json",
				'accept': "application/json",
			}
		cs = values['mTransactionID']+values['merchantCode']+values['clientIP']+values['passcode']+PAYSECRETKEY
		hashed = sha1(cs.encode('utf-8'))
		values['checksum'] = hashed.hexdigest()
		conn = http.client.HTTPSConnection(PAYURL)
		pay_url = "/queryOrder1"
		if CURRENT_ENV == 'prod':
			pay_url = "/queryOrder1"
		else:
			pay_url = "/miservice/queryOrder1"
		conn.request("POST", pay_url, json.dumps(values), headers)
		res = conn.getresponse()
		response_tuanly = json.loads(res.read().decode('utf-8'))
		print (response_tuanly)
		transactionStatus = int(response_tuanly[0])
		if (transactionStatus == 1):
			paymentStore.payTransactionid = response_tuanly[1]
			transactionStatus = int(response_tuanly[2])
			paymentStore.totalAmount = response_tuanly[3]
			paymentStore.opAmount = response_tuanly[4]
			paymentStore.bankCode = response_tuanly[5]
			paymentStore.description = response_tuanly[6]
			paymentStore.save()
		if (transactionStatus == 0):
			res_ts = str(int(datetime.datetime.utcnow().replace(tzinfo=utc).timestamp()))
			booked_ts = paymentStore.created + datetime.timedelta(minutes=8)
			booked_ts = booked_ts.timestamp()
			if int(booked_ts) <= int(res_ts):
				transactionStatus = -100
			else:
				return
			if (transactionStatus == 20 or transactionStatus == 10):
				res_ts = str(int(datetime.datetime.utcnow().replace(tzinfo=utc).timestamp()))
				booked_ts = paymentStore.created + datetime.timedelta(minutes=8)
				booked_ts = booked_ts.timestamp()
				if int(booked_ts) <= int(res_ts):
					transactionStatus = -100
	else:
		return
	update_payment_online_status(paymentStore=paymentStore,booked=booked,bankCode=paymentStore.bankCode,transactionStatus=transactionStatus,domain=domain)


def update_payment_online_status(paymentStore,booked,bankCode,transactionStatus,domain):
	if isinstance(booked, BookedTeeTime):
		if (not paymentStore.transactionStatus or int(paymentStore.transactionStatus) == 0) and int(transactionStatus) == 1:
			booked.payment_status = True
			booked.teetime.is_booked = True
			booked.teetime.save()
			booked.status = 'PP'
			booked.payment_type = 'F'
			booked.save()
			paymentStore.transactionStatus = transactionStatus
			paymentStore.bankCode = bankCode
			paymentStore.save()
			send_email_task.delay(booked.teetime_id,domain,"C")
		elif int(transactionStatus) == 20 or int(transactionStatus) == 10:
			paymentStore.transactionStatus = '0'
			paymentStore.save()
		elif not int(transactionStatus) == 1:
			if not booked.payment_type=='F':
				paymentStore.transactionStatus = transactionStatus
				paymentStore.save()
				return
			if booked.status == 'PP':
				paymentStore.transactionStatus = transactionStatus
				paymentStore.save()
				return
			booked.teetime.is_booked = booked.teetime.is_request = booked.teetime.is_hold = False
			booked.teetime.hold_expire = None
			booked.teetime.save()
			if booked.voucher_code:
				voucher = Voucher.objects.filter(code=booked.voucher_code).first()
				if voucher:
					voucher.is_used = False
					voucher.save()
			booked_his = BookedTeeTime_History.objects.create(
					teetime_id           = booked.teetime_id,
					golfcourse_id        = booked.golfcourse_id,
					reservation_code     = booked.reservation_code,
					created              = booked.created,
					modified             = booked.modified,
					player_count         = booked.player_count,
					player_checkin_count = booked.player_checkin_count,
					payment_type         = booked.payment_type,
					status               = 'C',
					book_type            = booked.book_type,
					total_cost           = booked.total_cost,
					paid_amount          = booked.paid_amount,
					url                  = booked.url,
					qr_image             = booked.qr_image,
					qr_base64            = booked.qr_base64,
					qr_url               = booked.qr_url,
					booked_teetime       = booked.id,
					payment_status       = booked.payment_status
				)
			partner_list = BookedPartner.objects.filter(bookedteetime_id=booked.id)
			for _partner in partner_list:
				partner_his = BookedPartner_History.objects.create(
						bookedteetime_id = booked_his.id,
						user_id          = _partner.user_id,
						customer_id      = _partner.customer_id,
						status           = _partner.status
					)
			booked.delete()
			paymentStore.transactionStatus = transactionStatus
			paymentStore.save()
	elif isinstance(booked, BookedPayonlineLink):
		if (not paymentStore.transactionStatus or int(paymentStore.transactionStatus) == 0) and int(transactionStatus) == 1:
			booked.paymentStatus = True
			booked.save()
			paymentStore.transactionStatus = transactionStatus
			paymentStore.bankCode = bankCode
			paymentStore.save()
			subject = "Payonline of user \"{0}\" with amount \"{1}\": SUCCESS".format(booked.custName, booked.totalAmount)
			message = ""
			to = [booked.receiveEmail]
			if CURRENT_ENV == 'prod':
				to.append('booking@golfconnect24.com')
			send_email(subject, message, to)
		elif int(transactionStatus) == 20 or int(transactionStatus) == 10:
			paymentStore.transactionStatus = '0'
			paymentStore.save()
		elif not int(transactionStatus) == 1:
			paymentStore.transactionStatus = transactionStatus
			paymentStore.save()
			subject = "Payonline of user \"{0}\" with amount \"{1}\": FAIL".format(booked.custName, booked.totalAmount)
			message = ""
			to = [booked.receiveEmail]
			if CURRENT_ENV == 'prod':
				to.append('booking@golfconnect24.com')
			send_email(subject, message, to)
	if isinstance(booked, BookedGolfcourseEvent):
		if (not paymentStore.transactionStatus or int(paymentStore.transactionStatus) == 0) and int(transactionStatus) == 1:
			booked.payment_status = True
			booked.save()
			paymentStore.transactionStatus = transactionStatus
			paymentStore.bankCode = bankCode
			paymentStore.save()
			subject = "Payonline of EventMember \"{0}\" for Event \"{2}\" with amount \"{1}\": SUCCESS".format(booked.member.id, booked.total_cost, booked.member.event.id)
			message = ""
			to = []
			if CURRENT_ENV == 'prod':
				to.append('booking@golfconnect24.com')
			send_email(subject, message, to)
		elif int(transactionStatus) == 20 or int(transactionStatus) == 10:
			paymentStore.transactionStatus = '0'
			paymentStore.save()
		elif not int(transactionStatus) == 1:
			paymentStore.transactionStatus = transactionStatus
			paymentStore.save()
			subject = "Payonline of EventMember \"{0}\" for Event \"{2}\" with amount \"{1}\": FAIL".format(booked.member.id, booked.total_cost, booked.member.event.id)
			message = ""
			to = []
			if CURRENT_ENV == 'prod':
				to.append('booking@golfconnect24.com')
			send_email(subject, message, to)
	return
				
def handle_cancel_booking(ids):
	if isinstance(ids,int):
		list_id = [ids]
	else:
		list_id = ids
	booked_list = BookedTeeTime.objects.filter(teetime_id__in=list_id).exclude(status='I')
	for booked in booked_list:
		notify_unlock(booked.teetime)
		if booked.voucher_code:
			voucher = Voucher.objects.filter(code=booked.voucher_code).first()
			if voucher:
				voucher.is_used = False
				voucher.save()
		if booked.payment_type=='F' and not booked.payment_status:
			continue
		t_status = booked.teetime.is_booked
		tt = get_or_none(TeeTime, pk=booked.teetime_id)
		if tt:
			if tt.is_booked is True or tt.is_request:
				tt.is_booked   = False
				tt.is_request   = False
				tt.is_hold     = False
				tt.hold_expire = None
				tt.save(update_fields=['is_booked', 'is_hold', 'hold_expire','is_request'])
				
		# create history bookedteetime

		booked_his = BookedTeeTime_History.objects.create(
				teetime_id           = booked.teetime_id,
				golfcourse_id        = booked.golfcourse_id,
				reservation_code     = booked.reservation_code,
				created              = booked.created,
				modified             = booked.modified,
				player_count         = booked.player_count,
				player_checkin_count = booked.player_checkin_count,
				payment_type         = booked.payment_type,
				status               = booked.status,
				book_type            = booked.book_type,
				total_cost           = booked.total_cost,
				paid_amount          = booked.paid_amount,
				url                  = booked.url,
				qr_image             = booked.qr_image,
				qr_base64            = booked.qr_base64,
				qr_url               = booked.qr_url,
				booked_teetime       = booked.id,
				payment_status       = booked.payment_status
			)
		partner_list = BookedPartner.objects.filter(bookedteetime_id=booked.id)
		for _partner in partner_list:
			partner_his = BookedPartner_History.objects.create(
					bookedteetime_id = booked_his.id,
					user_id          = _partner.user_id,
					customer_id      = _partner.customer_id,
					status           = _partner.status
				)        
		if not t_status:
			booked.delete()
		else:
			if booked_his:
				encode_data = base64.urlsafe_b64encode(str(booked.id).encode('ascii')).decode('ascii')
				buggy_data = get_booked_buggy_caddy(booked.id)
				if booked.payment_status:
					send_email_task.delay(booked_his.pk,encode_data,'CP',buggy_data)
				else:
					send_email_task.delay(booked_his.pk,encode_data,'CN', buggy_data)
				booked.delete()
@shared_task
def task_auto_expire_holding(id):
	teetime = get_or_none(TeeTime, pk=id)
	if teetime and teetime.is_hold is True and teetime.is_block is False and teetime.is_booked is False and teetime.hold_expire:
		if teetime.hold_expire < datetime.datetime.utcnow().replace(tzinfo=utc):
			teetime.is_hold = False
			teetime.hold_expire = None
			teetime.save()
			## publish redis
			channel = 'booking-' + teetime.date.strftime('%Y-%m-%d')
			msg = {
				"id": teetime.id,
				"is_hold": teetime.is_hold
			}
			msg = json.dumps(msg)
			redis_server.publish(channel, msg)
	return True

@task(name="send_email_task")
def send_email_task(booked_id,domain,email_type,data=None):
	if email_type == 'R':
		return send_email_request_booking(booked_id,domain)
	elif email_type == 'C':
		return send_confirmation(booked_id, domain)
	elif email_type == 'CP':
		return send_notify_booking_cancelled_paid('NOTIFY_CANCELLED', booked_id, domain, data)
	elif email_type == 'CN':
		return send_notify_booking_cancelled_nopaid('NOTIFY_CANCELLED', booked_id, domain, data)
	else:
		return 

def get_booked_buggy_caddy(teetime_id):
	booked = BookedTeeTime.objects.get(pk=teetime_id)
	teetime_price = get_or_none(TeeTimePrice, teetime_id=booked.teetime.id, hole=18)
	teetime_price2 = get_or_none(TeeTimePrice, teetime_id=booked.teetime.id, hole=booked.hole)
	booked_buggy = get_or_none(BookedBuggy, teetime=booked)
	booked_caddy = get_or_none(BookedCaddy, teetime=booked)
	data = {}
	data['buggy'] = teetime_price.buggy
	data['caddy'] = teetime_price.caddy
	data['green_fee'] = teetime_price2.price
	discount = float(booked.discount)
	voucher_code = booked.voucher_code
	voucher_amount = int(booked.voucher_discount_amount)
	data['discount'] = discount
	data['hole'] = booked.hole
	data['discount_amount'] = discount*float(teetime_price2.price)/100
	data['gifts'] = teetime_price.gifts
	data['free'] = teetime_price.food_voucher
	data['voucher_code'] = voucher_code
	data['voucher_amount'] = voucher_amount
	data['description'] = booked.teetime.description
	data['available'] = teetime_price.teetime.available
	if booked_caddy:
		data['caddy_qty'] = booked_caddy.quantity
		data['caddy_amount'] = float(booked_caddy.amount)
	if booked_buggy:
		data['buggy_qty'] = booked_buggy.quantity
		data['buggy_amount'] = float(booked_buggy.amount)
	return data

def send_notify_booking_cancelled_paid(type , pk, encode_data, buggy_data):
	with open(EMAIL_TEMPLATE_TYPE[type], encoding="utf-8") as f:
		data= f.read()
		teetime = BookedTeeTime_History.objects.get(pk=pk)
		serializer = BookedTeeTime_HistorySerializer(teetime)
		tee_data = serializer.data
		paid_status = """
		<table class="layout layout--no-gutter" style="border-collapse: collapse;table-layout: fixed;Margin-left: auto;Margin-right: auto;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #e1e1e1;" align="center" emb-background-style>
			<tbody>
				<tr>
					<td class="column " style="padding: 0 10px;text-align: left;vertical-align: top;color: #60666d;font-size: 14px;line-height: 21px;font-family: &quot;Open Sans&quot;,sans-serif;width: 580px;">
						<table cellpadding="0" style="width:100%; border-collapse: collapse; font-size:13px;">
							<tr>
								<td>
									<div style="padding-left:10px;Margin-right: 20px;">
										<p style="Margin-top: 0;Margin-bottom: 0;"><span style="color:#ff0000"><strong>Amounts/ Số tiền</strong></span></p>
									</div>
								</td>
								<td>
									<div style="Margin-left: 20px;Margin-right: 20px;Margin-top: 12px;Margin-bottom: 12px;">
										<p style="Margin-top: 0;Margin-bottom: 0;text-align: left;"><span style="color:#ff0000"><strong>{total_cost} đ</strong></span></p>
									</div>
								</td>
							</tr>
						</table>
					</td>
				</tr>
			</tbody>
		</table>"""
		data = data.replace('{name}', tee_data['customer_name'])
		data = data.replace('{paid_status}',paid_status)
		data = data.replace('{phone}', tee_data['customer_phone'])
		data = data.replace('{code}', tee_data['reservation_code'])
		data = data.replace('{total_cost}', "{:,}".format(int(teetime.total_cost)))
		data = data.replace('{golfcourse_address}', tee_data['golfcourse_address'])
		teetime_date = teetime.teetime.date
		teetime_time = teetime.teetime.time
		teetime_vi = DOW[str(teetime_date.strftime('%A'))] + \
									', ' + teetime_date.strftime('%d') + \
									' tháng ' + teetime_date.strftime('%m') + ', ' + \
									teetime_date.strftime('%Y') + ' lúc ' + \
									teetime_time.strftime('%H:%M')
		teetime_en = str(teetime_date.strftime('%A')) + \
									', ' + teetime_date.strftime('%d') + \
									' ' + teetime_date.strftime('%B') + ', ' + \
									teetime_date.strftime('%Y') + ' at ' + \
									teetime_time.strftime('%H:%M')

		createdDate = teetime.created
		try:
			country_code = teetime.golfcourse.country.short_name
			if country_code != '':
				tz = timezone(country_timezones(teetime.golfcourse.country.short_name)[0])
			if tz:
				createdDate = datetime.datetime.fromtimestamp(createdDate.timestamp(), tz)
		except Exception as e:
			pass
		created_vi = DOW[str(createdDate.strftime('%A'))] + \
									', ' + createdDate.strftime('%d') + \
									' tháng ' + createdDate.strftime('%m') + ', ' + \
									createdDate.strftime('%Y') + ' lúc ' + \
									createdDate.strftime('%H:%M')
		created_en = str(createdDate.strftime('%A')) + \
									', ' + createdDate.strftime('%d') + \
									' ' + createdDate.strftime('%B') + ', ' + \
									createdDate.strftime('%Y') + ' at ' + \
									createdDate.strftime('%H:%M')
		data = data.replace('{teetime_en}', teetime_en)
		data = data.replace('{teetime_vi}', teetime_vi)
		data = data.replace('{created_en}', created_en)
		data = data.replace('{created_vi}', created_vi)
		name_phone = tee_data['customer_name']
		if tee_data['customer_phone']:
			name_phone += ' - ' + tee_data['customer_phone']
		# get teetime gift ...
		gtype = GuestType.objects.get(name = 'G')
		teetime_price = get_or_none(TeeTimePrice, teetime_id=tee_data['teetime_id'], hole=18, guest_type_id=gtype.id)
		booked_bc = buggy_data
		data = data.replace('{hole}', str(booked_bc['hole']))
		email_html= """<div style="height:{2}px;font-weight:bold; margin-top: 10px;">
				   <span style="float:left;">{0}</span>
				   <span style="float:right;color:red;">{1}</span></div>"""
		_green_fee = booked_bc['green_fee']
		i_buggy = ""
		if booked_bc['buggy']:
			i_buggy += "(buggy"
		if booked_bc['caddy']:
			if i_buggy:
				i_buggy += ", caddy included)"
			else:
				i_buggy += "(caddy included)"
		else:
			if i_buggy:
				i_buggy += " included)"
		d = "\0"
		pref = "Green fees{0}"
		if i_buggy:
			d = """<br><span style="color:#ADA8A8;">{0}</span>""".format(i_buggy)
			pref = pref.format(d)
		else:
			pref = pref.format('\0')
		t = "{:,}".format(int(_green_fee))
		t2 = "{0} VND x {1}".format(t, teetime.player_count)
		size = 40 if i_buggy else 20
		pf = email_html.format(pref, t2, size)
		data = data.replace('{green_fee}', pf)
		if booked_bc['description']:
			golfcourse_name = tee_data['golfcourse_name'] + " - "+ booked_bc['description']
		else:
			golfcourse_name = tee_data['golfcourse_name']
		data = data.replace('{golfcourse_name}', golfcourse_name)
		if booked_bc['discount_amount']:
			green_fee_discount = booked_bc['discount_amount'] * int(teetime.player_count)
			t = "{:,}".format(int(green_fee_discount))
			t2 = "-{0} VND".format(t)
			pf = email_html.format("Discount", t2, 20)
			data = data.replace('{discount}', pf)
		else:
			data = data.replace('{discount}', '\0')

		email_html= """<div style="height:20px;font-weight:bold; margin-top: 10px;">
				   <span style="float:left;">{0}</span> 
				   <span style="float:right;color:red;">{1}</span></div>"""
		if 'caddy_qty' in booked_bc.keys() and not int(booked_bc['caddy_qty']) == 0:
			bprice = booked_bc['caddy_amount']
			t = "{:,}".format(int(bprice))
			temp = "{0} VND x {1}".format(t, booked_bc['caddy_qty'])
			pf = email_html.format("Caddy fee", temp)
			data = data.replace('{caddy}', pf)
		else:
			data = data.replace('{caddy}', '\0')
		if 'buggy_qty' in booked_bc.keys() and not int(booked_bc['buggy_qty']) == 0:
			bprice = booked_bc['buggy_amount']
			t = "{:,}".format(int(bprice))
			temp = "{0} VND x {1}".format(t, booked_bc['buggy_qty'])
			pf = email_html.format("Buggy fee", temp)
			data = data.replace('{buggy}', pf)
		else:
			data = data.replace('{buggy}', '\0')

		if booked_bc['gifts']:
			e_html = """<br>Gift / Quà Tặng: {0}</br>""".format(booked_bc['gifts'])
			data = data.replace('{gifts}', e_html)
		else:
			data = data.replace('{gifts}', "")

		if booked_bc['free']:
			e_html = """<br>Free / Miễn phí: Food Voucher</br>"""
			data = data.replace('{free}', e_html)
		else:
			data = data.replace('{free}', "")
		# end    
		data = data.replace('{name_phone}', name_phone)
		data = data.replace('{player_count}', str(tee_data['player_count']))
		# data = data.replace('{qr_base64}', created.qr_base64)
		if CURRENT_ENV == 'prod':
			bcc_email = ['booking@golfconnect24.com']
		else:
			bcc_email = []
		golfstaffs = GolfCourseStaff.objects.filter(golfcourse_id=teetime.golfcourse_id)
		
		email = []
		email.append(tee_data['customer_email'])
		for gs in golfstaffs:
			email.append(gs.user.email)
		ctx = {}
		template_data = Template(data)
		message = template_data.render(Context(ctx))
		# data = htmltpl.render(d)
		msg = EmailMessage('BOOKING CANCELLATION - HỦY ĐẶT SÂN #{}'.format(tee_data['reservation_code']), message,
									'GolfConnect24 <no-reply@golfconnect24.com>', email, bcc=bcc_email)
		msg.content_subtype = "html"
		msg.send()
		return
def send_notify_booking_cancelled_nopaid(type , pk, encode_data, buggy_data):
	with open(EMAIL_TEMPLATE_TYPE[type], encoding="utf-8") as f:
		data= f.read()
		teetime = BookedTeeTime_History.objects.get(pk=pk)
		serializer = BookedTeeTime_HistorySerializer(teetime)
		tee_data = serializer.data
		data = data.replace('{paid_status}','\0')
		data = data.replace('{name}', tee_data['customer_name'])
		data = data.replace('{phone}', tee_data['customer_phone'])
		data = data.replace('{code}', tee_data['reservation_code'])
		data = data.replace('{total_cost}', "{:,}".format(teetime.total_cost))
		data = data.replace('{golfcourse_address}', tee_data['golfcourse_address'])
		if len(tee_data['golfcourse_address'].strip()) > 36:
			data = data.replace('{scale_bookedon}', '<br></br>')
		else:
			data = data.replace('{scale_bookedon}', '\0')
		teetime_date = teetime.teetime.date
		teetime_time = teetime.teetime.time
		teetime_vi = DOW[str(teetime_date.strftime('%A'))] + \
									', ' + teetime_date.strftime('%d') + \
									' tháng ' + teetime_date.strftime('%m') + ', ' + \
									teetime_date.strftime('%Y') + ' lúc ' + \
									teetime_time.strftime('%H:%M')
		teetime_en = str(teetime_date.strftime('%A')) + \
									', ' + teetime_date.strftime('%d') + \
									' ' + teetime_date.strftime('%B') + ', ' + \
									teetime_date.strftime('%Y') + ' at ' + \
									teetime_time.strftime('%H:%M')

		createdDate = teetime.created
		try:
			country_code = teetime.golfcourse.country.short_name
			if country_code != '':
				tz = timezone(country_timezones(teetime.golfcourse.country.short_name)[0])
			if tz:
				createdDate = datetime.datetime.fromtimestamp(createdDate.timestamp(), tz)
		except Exception as e:
			pass
		created_vi = DOW[str(createdDate.strftime('%A'))] + \
									', ' + createdDate.strftime('%d') + \
									' tháng ' + createdDate.strftime('%m') + ', ' + \
									createdDate.strftime('%Y') + ' lúc ' + \
									createdDate.strftime('%H:%M')
		created_en = str(createdDate.strftime('%A')) + \
									', ' + createdDate.strftime('%d') + \
									' ' + createdDate.strftime('%B') + ', ' + \
									createdDate.strftime('%Y') + ' at ' + \
									createdDate.strftime('%H:%M')
		data = data.replace('{teetime_en}', teetime_en)
		data = data.replace('{teetime_vi}', teetime_vi)
		data = data.replace('{created_en}', created_en)
		data = data.replace('{created_vi}', created_vi)
		name_phone = tee_data['customer_name']
		if tee_data['customer_phone']:
			name_phone += ' - ' + tee_data['customer_phone']
		# get teetime gift ...
		gtype = GuestType.objects.get(name = 'G')
		teetime_price = get_or_none(TeeTimePrice, teetime_id=tee_data['teetime_id'], hole=18, guest_type_id=gtype.id)
		booked_bc = buggy_data
		data = data.replace('{hole}', str(booked_bc['hole']))
		email_html= """<div style="height:{2}px;font-weight:bold; margin-top: 10px;">
				   <span style="float:left;">{0}</span>
				   <span style="float:right;color:red;">{1}</span></div>"""
		_green_fee = booked_bc['green_fee']
		i_buggy = ""
		if booked_bc['buggy']:
			i_buggy += "(buggy"
		if booked_bc['caddy']:
			if i_buggy:
				i_buggy += ", caddy included)"
			else:
				i_buggy += "(caddy included)"
		else:
			i_buggy += " included)"
		d = "\0"
		pref = "Green fees{0}"
		if i_buggy:
			i_buggy += ")"
			d = """<br><span style="color:#ADA8A8;">{0}</span>""".format(i_buggy)
			pref = pref.format(d)
		else:
			pref = pref.format('\0')
		t = "{:,}".format(int(_green_fee))
		t2 = "{0} VND x {1}".format(t, teetime.player_count)
		size = 40 if i_buggy else 20
		pf = email_html.format(pref, t2, size)
		data = data.replace('{green_fee}', pf)
		if booked_bc['discount_amount']:
			green_fee_discount = booked_bc['discount_amount'] * int(teetime.player_count)
			t = "{:,}".format(int(green_fee_discount))
			t2 = "-{0} VND".format(t)
			pf = email_html.format("Discount", t2, 20)
			data = data.replace('{discount}', pf)
		else:
			data = data.replace('{discount}', '\0')

		email_html= """<div style="height:20px;font-weight:bold; margin-top: 10px;">
				   <span style="float:left;">{0}</span> 
				   <span style="float:right;color:red;">{1}</span></div>"""
		if 'caddy_qty' in booked_bc.keys() and not int(booked_bc['caddy_qty']) == 0:
			bprice = booked_bc['caddy_amount']
			t = "{:,}".format(int(bprice))
			temp = "{0} VND x {1}".format(t, booked_bc['caddy_qty'])
			pf = email_html.format("Caddy fee", temp)
			data = data.replace('{caddy}', pf)
		else:
			data = data.replace('{caddy}', '\0')
		if 'buggy_qty' in booked_bc.keys() and not int(booked_bc['buggy_qty']) == 0:
			bprice = booked_bc['buggy_amount']
			t = "{:,}".format(int(bprice))
			temp = "{0} VND x {1}".format(t, booked_bc['buggy_qty'])
			pf = email_html.format("Buggy fee", temp)
			data = data.replace('{buggy}', pf)
		else:
			data = data.replace('{buggy}', '\0')

		if booked_bc['gifts']:
			e_html = """<br>Gift / Quà Tặng: {0}</br>""".format(booked_bc['gifts'])
			data = data.replace('{gifts}', e_html)
		else:
			data = data.replace('{gifts}', "")

		if booked_bc['free']:
			e_html = """<br>Free / Miễn phí: Food Voucher</br>"""
			data = data.replace('{free}', e_html)
		else:
			data = data.replace('{free}', "")
		# end
		if booked_bc['description']:
			golfcourse_name = tee_data['golfcourse_name'] + " - "+ booked_bc['description']
		else:
			golfcourse_name = tee_data['golfcourse_name']
		data = data.replace('{golfcourse_name}', golfcourse_name)
		data = data.replace('{name_phone}', name_phone)
		data = data.replace('{player_count}', str(tee_data['player_count']))
		# data = data.replace('{qr_base64}', created.qr_base64)
		if CURRENT_ENV == 'prod':
			bcc_email = ['booking@golfconnect24.com']
		else:
			bcc_email = []
		golfstaffs = GolfCourseStaff.objects.filter(golfcourse_id=teetime.golfcourse_id)
		
		email = []
		email.append(tee_data['customer_email'])
		for gs in golfstaffs:
			email.append(gs.user.email)
		ctx = {}
		template_data = Template(data)
		message = template_data.render(Context(ctx))
		# data = htmltpl.render(d)
		msg = EmailMessage('BOOKING CANCELLATION - HỦY ĐẶT SÂN #{}'.format(tee_data['reservation_code']), message,
									'GolfConnect24 <no-reply@golfconnect24.com>', email, bcc=bcc_email)
		msg.content_subtype = "html"
		msg.send()
		return


def send_email_request_booking(booked_id,domain):
	email_path = EMAIL_TEMPLATE_PATH + "booking_request.html"
	with open(email_path, encoding="utf-8") as f:
		data= f.read()
		teetime = BookedTeeTime.objects.get(pk=booked_id)
		booked_bc = get_booked_buggy_caddy(teetime.id)
		serializer = BookedTeeTimeSerializer(teetime)
		tee_data = serializer.data
		encode_data = base64.urlsafe_b64encode(str(teetime.id).encode('ascii')).decode('ascii')
		cancel_teetime_url = 'https://' + domain + '/#/bookingTerm/' + str(teetime.teetime.golfcourse.id) + '/'
		request_url = 'https://'+domain+'#/booking-request/payment/'+str(encode_data)+'/'

		data = data.replace('{name}', tee_data['customer_name'])
		data = data.replace('{phone}', tee_data['customer_phone'])
		data = data.replace('{code}', tee_data['reservation_code'])
		data = data.replace('{total_cost}', "{:,}".format(int(teetime.total_cost)))
		data = data.replace('{cancel_url}', cancel_teetime_url)
		data = data.replace('{hole}', str(teetime.hole))
		greenfee_tpl = """<tr style="height: 30px;">
								<td >
								   <b>{0}</b><br>{1}
								</td>
								<td style="    vertical-align: top;">{2} đ</td>
								<td style="text-align:right;vertical-align: top;">x    {3}</td>
								<td style="text-align:right;vertical-align: top;">
									{4} đ</td>
							</tr>
				"""
		_green_fee = booked_bc['green_fee']
		i_buggy = ""
		if booked_bc['buggy']:
			i_buggy += "(buggy"
		if booked_bc['caddy']:
			if i_buggy:
				i_buggy += ", caddy included)"
			else:
				i_buggy += "(caddy included)"
		else:
			if i_buggy:
				i_buggy += " included)"
		d = "\0"
		pref = "{0}"
		if not i_buggy:
			i_buggy = "\0"
		t = "{:,}".format(int(_green_fee))
		t3 = "{:,}".format((int(_green_fee)*int(teetime.player_count)))
		pf = greenfee_tpl.format("Green fee", i_buggy, t, teetime.player_count,t3)
		data = data.replace('{green_fee}', pf)
		discount_tpl = """<tr style="height: 30px;">
								<td style="font-weight:bold;color:red;font-size: 12px">
								   {0}(-{1}%)
								</td>
								<td colspan="4" style="text-align:right;color:red;">
									{2} đ</td>
							</tr>
				"""
		if booked_bc['discount_amount']:
			green_fee_discount = booked_bc['discount_amount'] * int(teetime.player_count)
			t = "{:,}".format(int(green_fee_discount))
			t2 = "-{0}".format(t)
			pf = discount_tpl.format("Discount", booked_bc['discount'], t2)
			data = data.replace('{discount}', pf)
		else:
			data = data.replace('{discount}', '\0')
		discount_tpl = """<tr style="height: 30px;">
								<td style="font-weight:bold;color:red;font-size: 12px">
								   {0}
								</td>
								<td colspan="4" style="text-align:right;color:red;">
									{2} đ</td>
							</tr>
				"""
		if booked_bc['voucher_code']:
			green_fee_discount = booked_bc['voucher_amount']
			t = "{:,}".format(int(green_fee_discount))
			t2 = "-{0}".format(t)
			pf = discount_tpl.format("Voucher", booked_bc['voucher_amount'], t2)
			data = data.replace('{voucher}', pf)
		else:
			data = data.replace('{voucher}', '\0')

		email_html= """<tr style="height: 30px;">
								<td style="font-weight:bold">{0}</td>
								<td>{1} đ</td>
								<td style="text-align:right">x    {2}</td>
								<td style="text-align:right">{3} đ</td>
							</tr>"""
		if 'caddy_qty' in booked_bc.keys() and not int(booked_bc['caddy_qty']) == 0:
			bprice = booked_bc['caddy_amount']
			t = "{:,}".format(int(bprice))
			temp2 = "{:,}".format((int(bprice)*int(booked_bc['caddy_qty'])))
			pf = email_html.format("Caddy fee", t, booked_bc['caddy_qty'], temp2)
			data = data.replace('{caddy}', pf)
		else:
			data = data.replace('{caddy}', '\0')
		if 'buggy_qty' in booked_bc.keys() and not int(booked_bc['buggy_qty']) == 0:
			bprice = booked_bc['buggy_amount']
			t = "{:,}".format(int(bprice))
			temp2 = "{:,}".format((int(bprice)*int(booked_bc['buggy_qty'])))
			pf = email_html.format("Buggy fee", t, booked_bc['buggy_qty'], temp2)
			data = data.replace('{buggy}', pf)
		else:
			data = data.replace('{buggy}', '\0')
		#if booked_bc['available']:
		tmp_content_contact = """
		<p style="Margin-top: 16px;Margin-bottom: 20px;"><span style="color:#60666d"><em>Or you can proceed to <a href="{request_url}">pay now online</a> to confirm your tee time.
   		</span></p>
   		<p style="Margin-top: 16px;Margin-bottom: 20px;"><span style="color:#60666d"><em>Hoặc quý khách có thể <a href="{request_url}">thanh toán trực tuyến ngay</a> để xác nhận đặt sân.
   		</span></p>
		"""
		data = data.replace('{teetime_request}',tmp_content_contact)
		#else:
		#	data = data.replace('{teetime_request}','\0')
		data = data.replace('{request_url}', request_url)
		if booked_bc['description']:
			golfcourse_name = tee_data['golfcourse_name'] + " - "+ booked_bc['description']
		else:
			golfcourse_name = tee_data['golfcourse_name']
		data = data.replace('{golfcourse_name}', golfcourse_name)
		data = data.replace('{golfcourse_address}', tee_data['golfcourse_address'])
		if len(tee_data['golfcourse_address'].strip()) > 36:
			data = data.replace('{scale_bookedon}', '<br></br>')
		else:
			data = data.replace('{scale_bookedon}', '\0')
		teetime_date = teetime.teetime.date
		teetime_time = teetime.teetime.time
		teetime_vi = DOW[str(teetime_date.strftime('%A'))] + \
									', ' + teetime_date.strftime('%d') + \
									' tháng ' + teetime_date.strftime('%m') + ', ' + \
									teetime_date.strftime('%Y') + ' lúc ' + \
									teetime_time.strftime('%H:%M')
		teetime_en = str(teetime_date.strftime('%A')) + \
									', ' + teetime_date.strftime('%d') + \
									' ' + teetime_date.strftime('%B') + ', ' + \
									teetime_date.strftime('%Y') + ' at ' + \
									teetime_time.strftime('%H:%M')

		createdDate = teetime.created
		try:
			country_code = teetime.golfcourse.country.short_name
			if country_code != '':
				tz = timezone(country_timezones(teetime.golfcourse.country.short_name)[0])
			if tz:
				createdDate = datetime.datetime.fromtimestamp(createdDate.timestamp(), tz)
		except Exception as e:
			pass
		created_vi = DOW[str(createdDate.strftime('%A'))] + \
									', ' + createdDate.strftime('%d') + \
									' tháng ' + createdDate.strftime('%m') + ', ' + \
									createdDate.strftime('%Y') + ' lúc ' + \
									createdDate.strftime('%H:%M')
		created_en = str(createdDate.strftime('%A')) + \
									', ' + createdDate.strftime('%d') + \
									' ' + createdDate.strftime('%B') + ', ' + \
									createdDate.strftime('%Y') + ' at ' + \
									createdDate.strftime('%H:%M')
		data = data.replace('{teetime_en}', teetime_en)
		data = data.replace('{teetime_vi}', teetime_vi)
		data = data.replace('{created_en}', created_en)
		data = data.replace('{created_vi}', created_vi)
		data = data.replace('{player_count}', str(tee_data['player_count']))
		if booked_bc['gifts']:
			e_html = """<br>Gift / Quà Tặng: {0}</br>""".format(booked_bc['gifts'])
			data = data.replace('{gifts}', e_html)
		else:
			data = data.replace('{gifts}', "")

		if booked_bc['free']:
			e_html = """<br>Free / Miễn phí: Food Voucher</br>"""
			data = data.replace('{free}', e_html)
		else:
			data = data.replace('{free}', "")
		template_currency = """
			<tr style="height: 24px;">
	            <td></td>
	            <td colspan="4"  style="text-align:right;"><strong>{currencyCode} {currencyValue}</strong> </td>
	        </tr>
		"""
		if teetime.currencyCode and teetime.currencyCode != 'VND':
			t_data = {'currencyCode': teetime.currencyCode, 'currencyValue': round(teetime.currencyValue,2)}
			t_currency = template_currency.format(**t_data)
			data = data.replace('{currency}', t_currency)
		else:
			data = data.replace('{currency}', "")
		if CURRENT_ENV == 'prod':
			bcc_email = ['booking@golfconnect24.com']
		else:
			bcc_email = []
		email = [tee_data['customer_email']]
		ctx = {'email':tee_data['customer_email']}
		text = 'Thanks you for your booking with GolfConnect24'
		template_data = Template(data)
		message = template_data.render(Context(ctx))
		msg = EmailMessage('GOLFCONNECT24 BOOKING REQUEST - YÊU CẦU ĐẶT SÂN #{}'.format(tee_data['reservation_code']), message,
								from_email='GolfConnect24 <no-reply@golfconnect24.com>', to=email,bcc=bcc_email)
		msg.content_subtype = "html"
		msg.send()
		return

def send_confirmation(teetime_id,domain):
	email_path = EMAIL_TEMPLATE_PATH + "booking_confirmation.html"
	if isinstance(teetime_id,int):
		teetime_id = teetime_id
	else:
		teetime_id = teetime_id.id
	with open(email_path, encoding="utf-8") as f:
		data= f.read()
		teetime = BookedTeeTime.objects.get(teetime_id=teetime_id)
		booked_bc = get_booked_buggy_caddy(teetime.id)
		serializer = BookedTeeTimeSerializer(teetime)
		tee_data = serializer.data
		encode_data = base64.urlsafe_b64encode(str(teetime.id).encode('ascii')).decode('ascii')
		cancel_teetime_url = 'https://' + domain + '/#/cancel-teetime/' + encode_data + '/'
		data = data.replace('{name}', tee_data['customer_name'])
		data = data.replace('{phone}', tee_data['customer_phone'])
		data = data.replace('{code}', tee_data['reservation_code'])
		data = data.replace('{total_cost}', "{:,}".format(int(teetime.total_cost)))
		data = data.replace('{cancel_url}', cancel_teetime_url)
		data = data.replace('{hole}', str(teetime.hole))
		greenfee_tpl = """<tr style="height: 30px;">
								<td >
								   <b>{0}</b><br>{1}
								</td>
								<td style="    vertical-align: top;">{2} đ</td>
								<td style="text-align:right;vertical-align: top;">x    {3}</td>
								<td style="text-align:right;vertical-align: top;">
									{4} đ</td>
							</tr>
				"""
		_green_fee = booked_bc['green_fee']
		i_buggy = ""
		if booked_bc['buggy']:
			i_buggy += "(buggy"
		if booked_bc['caddy']:
			if i_buggy:
				i_buggy += ", caddy included)"
			else:
				i_buggy += "(caddy included)"
		else:
			if i_buggy:
				i_buggy += " included)"
		d = "\0"
		pref = "{0}"
		if not i_buggy:
			i_buggy = "\0"
		t = "{:,}".format(int(_green_fee))
		t3 = "{:,}".format((int(_green_fee)*int(teetime.player_count)))
		pf = greenfee_tpl.format("Green fee", i_buggy, t, teetime.player_count,t3)
		data = data.replace('{green_fee}', pf)
		discount_tpl = """<tr style="height: 30px;">
								<td style="font-weight:bold;color:red;font-size: 12px">
								   {0}(-{1}%)
								</td>
								<td colspan="4" style="text-align:right;color:red;">
									{2} đ</td>
							</tr>
				"""
		if booked_bc['discount_amount']:
			green_fee_discount = booked_bc['discount_amount'] * int(teetime.player_count)
			t = "{:,}".format(int(green_fee_discount))
			t2 = "-{0}".format(t)
			pf = discount_tpl.format("Discount", booked_bc['discount'], t2)
			data = data.replace('{discount}', pf)
		else:
			data = data.replace('{discount}', '\0')
		discount_tpl = """<tr style="height: 30px;">
								<td style="font-weight:bold;color:red;font-size: 12px">
								   {0}
								</td>
								<td colspan="4" style="text-align:right;color:red;">
									{2} đ</td>
							</tr>
				"""
		if booked_bc['voucher_code']:
			green_fee_discount = booked_bc['voucher_amount']
			t = "{:,}".format(int(green_fee_discount))
			t2 = "-{0}".format(t)
			pf = discount_tpl.format("Voucher", booked_bc['voucher_amount'], t2)
			data = data.replace('{voucher}', pf)
		else:
			data = data.replace('{voucher}', '\0')
		email_html= """<tr style="height: 30px;">
								<td style="font-weight:bold">{0}</td>
								<td>{1} đ</td>
								<td style="text-align:right">x    {2}</td>
								<td style="text-align:right">{3} đ</td>
							</tr>"""
		if 'caddy_qty' in booked_bc.keys() and not int(booked_bc['caddy_qty']) == 0:
			bprice = booked_bc['caddy_amount']
			t = "{:,}".format(int(bprice))
			temp2 = "{:,}".format((int(bprice)*int(booked_bc['caddy_qty'])))
			pf = email_html.format("Caddy fee", t, booked_bc['caddy_qty'], temp2)
			data = data.replace('{caddy}', pf)
		else:
			data = data.replace('{caddy}', '\0')
		if 'buggy_qty' in booked_bc.keys() and not int(booked_bc['buggy_qty']) == 0:
			bprice = booked_bc['buggy_amount']
			t = "{:,}".format(int(bprice))
			temp2 = "{:,}".format((int(bprice)*int(booked_bc['buggy_qty'])))
			pf = email_html.format("Buggy fee", t, booked_bc['buggy_qty'], temp2)
			data = data.replace('{buggy}', pf)
		else:
			data = data.replace('{buggy}', '\0')

		if booked_bc['gifts']:
			e_html = """<br>Gift / Quà Tặng: {0}</br>""".format(booked_bc['gifts'])
			data = data.replace('{gifts}', e_html)
		else:
			data = data.replace('{gifts}', "")

		if booked_bc['free']:
			e_html = """<br>Free / Miễn phí: Food Voucher</br>"""
			data = data.replace('{free}', e_html)
		else:
			data = data.replace('{free}', "")
		if booked_bc['description']:
			golfcourse_name = tee_data['golfcourse_name'] + " - "+ booked_bc['description']
		else:
			golfcourse_name = tee_data['golfcourse_name']
		data = data.replace('{golfcourse_name}', golfcourse_name)
		data = data.replace('{golfcourse_address}', tee_data['golfcourse_address'])
		if len(tee_data['golfcourse_address'].strip()) > 36:
			data = data.replace('{scale_bookedon}', '<br></br>')
		else:
			data = data.replace('{scale_bookedon}', '\0')
		teetime_date = teetime.teetime.date
		teetime_time = teetime.teetime.time
		teetime_vi = DOW[str(teetime_date.strftime('%A'))] + \
									', ' + teetime_date.strftime('%d') + \
									' tháng ' + teetime_date.strftime('%m') + ', ' + \
									teetime_date.strftime('%Y') + ' lúc ' + \
									teetime_time.strftime('%H:%M')
		teetime_en = str(teetime_date.strftime('%A')) + \
									', ' + teetime_date.strftime('%d') + \
									' ' + teetime_date.strftime('%B') + ', ' + \
									teetime_date.strftime('%Y') + ' at ' + \
									teetime_time.strftime('%H:%M')

		createdDate = teetime.created
		try:
			country_code = teetime.golfcourse.country.short_name
			if country_code != '':
				tz = timezone(country_timezones(teetime.golfcourse.country.short_name)[0])
			if tz:
				createdDate = datetime.datetime.fromtimestamp(createdDate.timestamp(), tz)
		except Exception as e:
			pass
		created_vi = DOW[str(createdDate.strftime('%A'))] + \
									', ' + createdDate.strftime('%d') + \
									' tháng ' + createdDate.strftime('%m') + ', ' + \
									createdDate.strftime('%Y') + ' lúc ' + \
									createdDate.strftime('%H:%M')
		created_en = str(createdDate.strftime('%A')) + \
									', ' + createdDate.strftime('%d') + \
									' ' + createdDate.strftime('%B') + ', ' + \
									createdDate.strftime('%Y') + ' at ' + \
									createdDate.strftime('%H:%M')
		data = data.replace('{teetime_en}', teetime_en)
		data = data.replace('{teetime_vi}', teetime_vi)
		data = data.replace('{created_en}', created_en)
		data = data.replace('{created_vi}', created_vi)
		data = data.replace('{player_count}', str(tee_data['player_count']))
		template_currency = """
			<tr style="height: 24px;">
	            <td></td>
	            <td colspan="4"  style="text-align:right;"><strong>{currencyCode} {currencyValue}</strong> </td>
	        </tr>
		"""
		if teetime.currencyCode and teetime.currencyCode != 'VND':
			t_data = {'currencyCode': teetime.currencyCode, 'currencyValue': round(teetime.currencyValue,2)}
			t_currency = template_currency.format(**t_data)
			data = data.replace('{currency}', t_currency)
		else:
			data = data.replace('{currency}', "")
		if tee_data['payment_status']:
			data = data.replace('{payment_status}', "Paid")
		else:
			data = data.replace('{payment_status}', "Unpaid")
		# data = data.replace('{qr_base64}', created.qr_base64)
		if CURRENT_ENV == 'prod':
			bcc_email = ['booking@golfconnect24.com']
		else:
			bcc_email = []
		golfstaffs = GolfCourseStaff.objects.filter(golfcourse_id=teetime.golfcourse_id)

		email = [tee_data['customer_email']]
		for gs in golfstaffs:
			email.append(gs.user.email)
		# data = htmltpl.render(d)
		ctx = {}
		template_data = Template(data)
		message = template_data.render(Context(ctx))
		
		msg = EmailMessage('GOLFCONNECT24 BOOKING CONFIRMATION - XÁC NHẬN ĐẶT SÂN #{}'.format(tee_data['reservation_code']), message,
									'GolfConnect24 <no-reply@golfconnect24.com>', email, bcc_email)
		msg.content_subtype = "html"
		try:
			with open('media/qr_codes/' + encode_data + '.png', "rb") as f:
				data = f.read()
				msg_qr_img = MIMEImage(data)
				msg_qr_img.add_header('Content-ID', '<{}>'.format('qr.png'))
				msg.attach(msg_qr_img)
		except Exception:
			pass
		msg.send()
		return

@shared_task
def send_thankyou_email(teetime_id):
	from api.noticeMana.tasks import send_after_booking_email
	from core.booking.models import BookedPartnerThankyou
	booked_teetime = BookedTeeTime.objects.filter(teetime_id__in=teetime_id)
	booked_data = BookedTeeTimeSerializer(booked_teetime).data
	for data in booked_data:
		email_booking = BookedPartnerThankyou.objects.filter(email=data['customer_email'].strip().lower())
		now = datetime.datetime.today()
		if data['customer_email'] and not email_booking.filter(modified_at=now).first() and email_booking.count() < 3:
			send_after_booking_email(data['customer_name'],data['customer_email'])
			BookedPartnerThankyou.objects.create(email=data['customer_email'].strip().lower())
	return True

@shared_task
def send_email_booking_event(booked_id):
	from core.booking.models import BookedGolfcourseEvent,BookedGolfcourseEventDetail
	from api.bookingMana.serializers import BookedGolfcourseEventSerializer
	booked = get_or_none(BookedGolfcourseEvent,pk=booked_id)
	if not booked:
		return False
	email_stayplay = EMAIL_TEMPLATE_PATH + "event_request_stayplay.html"
	email_play  = EMAIL_TEMPLATE_PATH + "event_request_play.html"
	booked_data = BookedGolfcourseEventSerializer(booked).data
	createdDate = booked.created
	try:
		country_code = booked_data.member.event.golfcourse.country.short_name
		if country_code != '':
			tz = timezone(country_timezones(booked_data.member.event.golfcourse.country.short_name)[0])
		if tz:
			createdDate = datetime.datetime.fromtimestamp(createdDate.timestamp(), tz)
	except Exception as e:
		pass
	created_vi = DOW[str(createdDate.strftime('%A'))] + \
									', ' + createdDate.strftime('%d') + \
									' tháng ' + createdDate.strftime('%m') + ', ' + \
									createdDate.strftime('%Y') + ' lúc ' + \
									createdDate.strftime('%H:%M')
	created_en = str(createdDate.strftime('%A')) + \
								', ' + createdDate.strftime('%d') + \
								' ' + createdDate.strftime('%B') + ', ' + \
								createdDate.strftime('%Y') + ' at ' + \
								createdDate.strftime('%H:%M')
	hotel = None
	try:
		hotel = booked.member.event.event_hotel_info
	except:
		pass
	data = ''
	if hotel and booked.member.event.allow_stay:
		hotel_name = hotel.hotel.name
		hotel_address = hotel.hotel.address
		checkinDate = hotel.checkin
		checkin_vi = DOW[str(checkinDate.strftime('%A'))] + \
									', ' + checkinDate.strftime('%d') + \
									' tháng ' + checkinDate.strftime('%m') + ', ' + \
									checkinDate.strftime('%Y') 
		checkin_en = str(checkinDate.strftime('%A')) + \
									', ' + checkinDate.strftime('%d') + \
									' ' + checkinDate.strftime('%B') + ', ' + \
									checkinDate.strftime('%Y') 
		checkoutDate = hotel.checkout
		checkout_vi = DOW[str(checkoutDate.strftime('%A'))] + \
									', ' + checkoutDate.strftime('%d') + \
									' tháng ' + checkoutDate.strftime('%m') + ', ' + \
									checkoutDate.strftime('%Y') 
		checkout_en = str(checkoutDate.strftime('%A')) + \
									', ' + checkoutDate.strftime('%d') + \
									' ' + checkoutDate.strftime('%B') + ', ' + \
									checkoutDate.strftime('%Y') 
		with open(email_stayplay, encoding="utf-8") as f:
			data = f.read()
			data = data.replace('{hotel_name}',hotel_name)
			data = data.replace('{hotel_address}',hotel_address)
			data = data.replace('{checkin_vi}',checkin_vi)
			data = data.replace('{checkin_en}',checkin_en)
			data = data.replace('{checkout_vi}',checkout_vi)
			data = data.replace('{checkout_en}',checkout_en)
	else:
		eventDate = booked.member.event.date_start
		event_vi = DOW[str(eventDate.strftime('%A'))] + \
									', ' + eventDate.strftime('%d') + \
									' tháng ' + eventDate.strftime('%m') + ', ' + \
									eventDate.strftime('%Y') 
		event_en = str(eventDate.strftime('%A')) + \
									', ' + eventDate.strftime('%d') + \
									' ' + eventDate.strftime('%B') + ', ' + \
									eventDate.strftime('%Y') 
		with open(email_play, encoding="utf-8") as f:
			data = f.read()
			data = data.replace('{eventdate_en}',event_vi)
			data = data.replace('{eventdate_vi}',event_en)
	data = data.replace('{event_name}', booked.member.event.name)
	data = data.replace('{code}',booked_data['reservation_code'])
	data = data.replace('{name}',booked_data['member'])
	data = data.replace('{phone}',booked_data['phone_number'])
	data = data.replace('{created_en}',created_en)
	data = data.replace('{created_vi}',created_vi)
	data = data.replace('{golfcourse_name}',booked.member.event.golfcourse.name)
	data = data.replace('{golfcourse_address}',booked.member.event.golfcourse.address)
	data = data.replace('{total_cost}', "{:,}".format(int(booked_data['total_cost'])))
	greenfee_tpl = """<tr style="height: 30px;">
								<td >
								   <b>{0}</b>
								</td>
								<td style="text-align:right;vertical-align: top;">x    {2}</td>
								<td style="text-align:right;vertical-align: top;">{1} đ</td>
								<td style="text-align:right;vertical-align: top;">
									{3} đ</td>
							</tr>
				"""
	greefee_data = ""
	event_price = booked.member.event.event_price_info.all()
	green_cost = 0
	for item in booked_data['booked_gc_event_detail']:
		query = event_price.filter(id=item['price_info']).first()
		item_price = int(query.price)*int(item.get('quantity', 1))
		green_cost += item_price
		greefee_data += greenfee_tpl.format(query.display, "{:,}".format(int(query.price)), int(item.get('quantity', 1)),
											"{:,}".format(int(item_price)))
	data = data.replace('{event_detail}', greefee_data)
	discount_tpl = """<tr style="height: 30px;">
								<td style="font-weight:bold;color:red;font-size: 12px">
								   {0}(-{1}%)
								</td>
								<td colspan="4" style="text-align:right;color:red;">
									-{2} đ</td>
							</tr>
				"""
	if booked.discount and booked.discount != 0:
		discount_amount = int(green_cost) - int(booked_data['total_cost'])
		discount = discount_tpl.format('Discount',booked_data['discount'],"{:,}".format(int(discount_amount)))
		data = data.replace('{discount}',discount)
	else:
		data = data.replace('{discount}','\0')
	if CURRENT_ENV == 'prod':
		bcc_email = ['booking@golfconnect24.com']
	else:
		bcc_email = []
	email = [booked_data['email']]
	ctx = {'email':booked_data['email']}
	text = 'Thanks you for your booking with GolfConnect24'
	template_data = Template(data)
	message = template_data.render(Context(ctx))
	msg = EmailMessage('GOLFCONNECT24 BOOKING REQUEST #{}'.format(booked_data['reservation_code']), message,
							from_email='GolfConnect24 <no-reply@golfconnect24.com>', to=email,bcc=bcc_email)
	msg.content_subtype = "html"
	msg.send()
	return True
