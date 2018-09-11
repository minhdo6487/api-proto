import base64
import json
import datetime
from utils.django.models import get_or_none
from pytz import timezone, country_timezones
import datetime, time
from django.utils.timezone import utc, pytz
from celery import shared_task, task
import redis
from celery import shared_task, task
from GolfConnect.settings import REDIS_HOST, REDIS_PORT, REDIS_DB
from celery.schedules import crontab
from celery.utils.log import get_task_logger
from celery.task.control import revoke
from celery.result import AsyncResult
from django.db.models import Q
logger = get_task_logger(__name__)

@task(name="notify_online_discount")
def notify_online_discount(teetime_id, discount, channel):
	redis_server = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
	if not teetime_id:
		return
	msg = {
		"id": teetime_id,
		"discount_online": discount
	}
	d = json.dumps(msg)
	a = redis_server.publish(channel, d)

def notify_discount(teetime_id, discount, channel, online_discount=None):
	from core.teetime.models import TeeTime
	teetime = get_or_none(TeeTime,pk=teetime_id)
	log_msg = "{0} got discount {1} from channel {2}".format(teetime_id, discount, channel)
	if not teetime or not teetime.available or not teetime.allow_paygc: #Tuan Ly: Hard code for no push notification for Pay@GC or Request Teetime
		return
	redis_server = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
	msg = {
		"id": teetime_id,
		"discount": discount,
		"discount_online": online_discount
	}
	d = json.dumps(msg)
	a = redis_server.publish(channel, d)

@task(name="stop_job_real_time_deal_now")
def stop_job_real_time_deal_now(bookingtime_id):
	from core.teetime.models import Deal, BookingTime, DealEffective_TeeTime
	from core.teetime.models import TeeTime, TeeTimePrice, JobBookingTime
	if not bookingtime_id:
		return
	bookingtime = get_or_none(BookingTime, pk=bookingtime_id)
	if not bookingtime:
		return
	filter_condition = {
		'bookingtime_id': bookingtime_id,
	}
	tz = timezone(country_timezones(bookingtime.deal.golfcourse.country.short_name)[0])
	now = datetime.datetime.utcnow()
	current_tz = datetime.datetime.fromtimestamp(now.timestamp(), tz)
	from_time = (datetime.datetime.combine(current_tz.date(), current_tz.time()) + datetime.timedelta(seconds=1)).time()
	from_date = current_tz.date()
	teetime_id = DealEffective_TeeTime.objects.filter(Q(**filter_condition)).values_list('teetime__id', flat=True)
	filter_deal = {
			'teetime__in': teetime_id,
			'bookingtime__deal__active': True,
			'bookingtime__deal__is_base': False,
			'bookingtime__date': from_date,
			'bookingtime__from_time__lte': from_time,
			'bookingtime__to_time__gte': from_time
	}

	filter_exclude1 = {
		'bookingtime__deal__effective_date': from_date,
		'bookingtime__deal__effective_time__gte': from_time 
	}
	filter_exclude2 = {
		'bookingtime__deal__expire_date': from_date,
		'bookingtime__deal__expire_time__lte': from_time 
	}
	dealteetime = DealEffective_TeeTime.objects.filter(Q(**filter_deal)).exclude(Q(**filter_exclude1) | Q(**filter_exclude2)).order_by('-modified')
	list_id = []
	if dealteetime.exists():
		for d in dealteetime:
			if d.teetime.id not in list_id:
				channel = 'booking-' + str(d.teetime.date)
				notify_discount(d.teetime.id, d.discount, channel, d.teetime.teetime_price.all()[0].cash_discount)
				list_id.append(d.teetime.id)
	remainid = [tid for tid in teetime_id if tid not in list_id]
	if remainid:
		teetime_price = TeeTimePrice.objects.filter(teetime_id__in=remainid,is_publish=True,hole=18)
		if teetime_price.exists():
			for tt in teetime_price:
				channel = 'booking-' + str(tt.teetime.date)
				notify_discount(tt.teetime.id, tt.online_discount, channel, tt.cash_discount)

@task(name="stop_job_real_time_deal")
def stop_job_real_time_deal(bookingtime_id, end_deal_now):
	from core.teetime.models import Deal, BookingTime, DealEffective_TeeTime
	from core.teetime.models import TeeTime, TeeTimePrice, JobBookingTime
	if not bookingtime_id:
		return
	bookingtime = get_or_none(BookingTime, pk=bookingtime_id)
	if not bookingtime:
		return
	filter_condition = {
		'bookingtime_id': bookingtime_id,
		'bookingtime__deal__active': True,
		'bookingtime__deal__is_base': False,
	}
	from_time = (datetime.datetime.combine(bookingtime.date, bookingtime.to_time) + datetime.timedelta(seconds=1)).time()
	from_date = bookingtime.date
	teetime_id = DealEffective_TeeTime.objects.filter(Q(**filter_condition)).values_list('teetime__id', flat=True)
	filter_deal = {
			'teetime__in': teetime_id,
			'bookingtime__deal__active': True,
			'bookingtime__deal__is_base': False,
			'bookingtime__date': from_date,
			'bookingtime__from_time__lte': from_time,
			'bookingtime__to_time__gte': from_time
	}

	filter_exclude1 = {
		'bookingtime__deal__effective_date': from_date,
		'bookingtime__deal__effective_time__gte': from_time 
	}
	filter_exclude2 = {
		'bookingtime__deal__expire_date': from_date,
		'bookingtime__deal__expire_time__lte': from_time 
	}
	dealteetime = DealEffective_TeeTime.objects.filter(Q(**filter_deal)).exclude(Q(**filter_exclude1) | Q(**filter_exclude2)).order_by('-modified')
	list_id = []
	if dealteetime.exists():
		for d in dealteetime:
			if d.teetime.id not in list_id:
				channel = 'booking-' + str(d.teetime.date)
				notify_discount(d.teetime.id, d.discount, channel, d.teetime.teetime_price.all()[0].cash_discount)
				list_id.append(d.teetime.id)
	remainid = [tid for tid in teetime_id if tid not in list_id]
	if remainid:
		teetime_price = TeeTimePrice.objects.filter(teetime_id__in=remainid,is_publish=True,hole=18)
		if teetime_price.exists():
			for tt in teetime_price:
				channel = 'booking-' + str(tt.teetime.date)
				notify_discount(tt.teetime.id, tt.online_discount, channel, tt.cash_discount)

@task(name="start_job_real_time_deal")
def start_job_real_time_deal(bookingtime_id, end_deal_now):
	from core.teetime.models import Deal, BookingTime, DealEffective_TeeTime
	from core.teetime.models import TeeTime, TeeTimePrice, JobBookingTime
	#Recheck information again
	if not bookingtime_id:
		return
	bookingtime = get_or_none(BookingTime, pk=bookingtime_id)
	if not bookingtime:
		return
	filter_condition = {
		'bookingtime_id': bookingtime_id,
		'bookingtime__deal__active': True,
		'bookingtime__deal__is_base': False,
	}
	from_time = bookingtime.from_time
	from_date = bookingtime.date
	mydeal_teetime = DealEffective_TeeTime.objects.filter(Q(**filter_condition))
	if not mydeal_teetime.exists():
		return
	teetime_id = mydeal_teetime.values_list('teetime__id', flat=True)
	filter_deal = {
			'teetime__in': teetime_id,
			'bookingtime__deal__active': True,
			'bookingtime__deal__is_base': False,
			'bookingtime__date': from_date,
			'bookingtime__from_time__lte': from_time,
			'bookingtime__to_time__gte': from_time
	}

	filter_exclude1 = {
		'bookingtime__deal__effective_date': from_date,
		'bookingtime__deal__effective_time__gte': from_time 
	}
	filter_exclude2 = {
		'bookingtime__deal__expire_date': from_date,
		'bookingtime__deal__expire_time__lte': from_time 
	}
	dealteetime = DealEffective_TeeTime.objects.filter(Q(**filter_deal)).exclude(Q(**filter_exclude1) | Q(**filter_exclude2)).order_by('-modified')
	if not dealteetime.exists():
		dealteetime = mydeal_teetime
	list_id = []
	for d in dealteetime:
		if not d.teetime.id in list_id and d.bookingtime.id == bookingtime_id:
			channel = 'booking-' + str(d.teetime.date)
			notify_discount(d.teetime.id, d.discount, channel, d.teetime.teetime_price.all()[0].cash_discount)
			list_id.append(d.teetime.id)

def deal_get_from_time(instance):
	start_time = datetime.datetime.combine(instance.date, instance.from_time)
	end_time = datetime.datetime.combine(instance.date, instance.to_time) + datetime.timedelta(seconds=1)
	check_eff = check_exp = True
	apply_start_time = start_time
	apply_end_time = end_time
	if instance.date == instance.deal.effective_date:
		effective_time = datetime.datetime.combine(instance.deal.effective_date, instance.deal.effective_time)
		apply_start_time = max(apply_start_time, effective_time)
		apply_end_time = max(apply_end_time, effective_time)
	
	if instance.date == instance.deal.expire_date:
		expire_time = datetime.datetime.combine(instance.deal.expire_date, instance.deal.expire_time)
		apply_start_time = min(apply_start_time, expire_time)
		apply_end_time = min(apply_end_time, expire_time)
		
	tz = timezone(country_timezones(instance.deal.golfcourse.country.short_name)[0])
	local_start_dt = tz.localize(apply_start_time, is_dst=None)
	local_end_dt = tz.localize(apply_end_time, is_dst=None)
	start_time = local_start_dt.astimezone(utc).replace(tzinfo=None)
	end_time = local_end_dt.astimezone(utc).replace(tzinfo=None)
	return {
		'start_time': start_time,
		'end_time': end_time
	}

def handle_realtime_booking_deal(instance):
	from core.teetime.models import TeeTime, TeeTimePrice, JobBookingTime
	now = datetime.datetime.utcnow()
	info = deal_get_from_time(instance)
	job_schedule, created = JobBookingTime.objects.get_or_create(bookingtime=instance)
	if job_schedule.schedule_task_id:
		revoke(job_schedule.schedule_task_id, terminate=True)
	if job_schedule.schedule_end_task_id:
		revoke(job_schedule.schedule_end_task_id, terminate=True)
	if (info['start_time'] < now and info['end_time'] > now):
		end_deal_now = stop_job_real_time_deal_now.apply_async(args=[instance.id],eta=now)
		end_deal = stop_job_real_time_deal.apply_async(args=[instance.id, end_deal_now.id],eta=info['end_time'])
		job_schedule.schedule_end_task_id = end_deal.id
		job_schedule.save()
	elif (info['start_time'] > now and info['end_time'] > now):
		end_deal_now = stop_job_real_time_deal_now.apply_async(args=[instance.id],eta=now)
		end_deal = stop_job_real_time_deal.apply_async(args=[instance.id, end_deal_now.id],eta=info['end_time'])
		start_deal = start_job_real_time_deal.apply_async(args=[instance.id, end_deal_now.id],eta=info['start_time'])
		job_schedule.schedule_task_id = start_deal.id
		job_schedule.schedule_end_task_id = end_deal.id
		job_schedule.save()

def parse_time(time):
	try:
		t = datetime.datetime.strptime(time, '%H:%M').time()
	except Exception:
		return datetime.time.min
	return t

def parse_date(date_data):
	try:
		date = datetime.datetime.strptime(date_data, '%Y-%m-%d').date()
	except Exception:
		try:
			date = datetime.datetime.strptime(date_data, '%y-%m-%d').date()
			print ('Tuan Ly ',date)
		except Exception:
			print ("Error here")
			return None
	return date
def validate_deal(deal):
	tz = timezone(country_timezones(deal.golfcourse.country.short_name)[0])
	now = datetime.datetime.utcnow()
	current_tz = datetime.datetime.fromtimestamp(now.timestamp(), tz)
	if (not deal.active and deal.end_date) or (deal.is_base):
		return deal
	else:
		if (deal.expire_date < current_tz.date()) or (deal.expire_date == current_tz.date() and deal.expire_time < current_tz.time()):
			deal.active = False
			deal.end_date = deal.expire_date
			deal.end_time = deal.expire_time
			deal.save()
	return deal

