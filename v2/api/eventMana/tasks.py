import datetime
from celery import shared_task
from GolfConnect.celery import celery_is_up
from django.db.models import Q
@shared_task
def __queue_user_booking_to_event(booking_id, user_email):
	from v2.core.eventqueue.models import EventQueue
	from core.booking.models import BookedTeeTime
	try:
		booked_teetime = BookedTeeTime.objects.get(pk=booking_id)
		EventQueue.objects.create(booking=booked_teetime,user_email=user_email)
	except:
		pass
	finally:
		return True

@shared_task
def __create_event_from_booking(user_email):
	from django.contrib.auth.models import User
	from django.contrib.contenttypes.models import ContentType
	from v2.core.eventqueue.models import EventQueue
	from core.booking.models import BookedTeeTime
	from core.golfcourse.models import GolfCourseEvent
	from api.userMana.tasks import log_activity
	eventqueue = EventQueue.objects.get_eventqueue(user_email=user_email)
	print (eventqueue)
	user = User.objects.filter(Q(**({'email':user_email})) | Q(**({'username':user_email}))).first()
	print (user)
	event_ctype = ContentType.objects.get_for_model(GolfCourseEvent)
	if eventqueue.exists() and user:
		user_displayname = user.user_profile.display_name or user.username
		for eq in eventqueue:
			ge = GolfCourseEvent.objects.create(time=eq.booking.teetime.time,
										   user=user,
										   golfcourse=eq.booking.golfcourse,
										   description='{} want to play'.format(user_displayname),
										   date_start=eq.booking.teetime.date,
										   date_end=eq.booking.teetime.date,
										   is_publish=True,
										   pod= 'M' if eq.booking.teetime.time > datetime.datetime.strptime('12:00', '%H:%M').time() else 'A'
										   )
			print (user.id, 'create_event', ge.id, event_ctype.id)
			log_activity(user.id, 'create_event', ge.id, event_ctype.id)
			eq.is_created = True
			eq.save()

def queue_user_booking_to_event(*args):
	if celery_is_up():
		__queue_user_booking_to_event.delay(*args)
	else:
		__queue_user_booking_to_event(*args)

def create_event_from_booking(sender, instance, created, **kwargs):
	if celery_is_up():
		__create_event_from_booking.delay(instance.user_email)
	else:
		__create_event_from_booking(instance.user_email)

def create_event_from_user(sender, instance, created, **kwargs):
	if celery_is_up():
		__create_event_from_booking.delay(instance.user.email or instance.user.username)
	else:
		__create_event_from_booking(instance.user.email or instance.user.username)