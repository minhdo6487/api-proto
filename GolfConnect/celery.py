from __future__ import absolute_import

import os

from celery import Celery
import celery.bin.celery
import celery.bin.base
import celery.platforms
from django.conf import settings
import dotenv
import arrow
dotenv.read_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GolfConnect.settings')

app = Celery('GolfConnect')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

status = celery.bin.celery.CeleryCommand.commands['status']()
status.app = status.get_app()

def celery_is_up():
    try:
        status.run()
        return True
    except celery.bin.base.Error as e:
        if e.status == celery.platforms.EX_UNAVAILABLE:
            return False
        raise e

@app.task
def restart_deal_real_time():
	from core.teetime.models import Deal
	from api.dealMana.tasks import handle_realtime_booking_deal
	deal = Deal.objects.filter(active=True, is_base=False)
	if deal.exists():
		for instance in deal:
			list_bookingtime = instance.bookingtime.all()
			if list_bookingtime:
				for lb in list_bookingtime:
					handle_realtime_booking_deal(lb)

@app.task()
def push_notification_tick():
	from v2.api.notify.tasks import push_notification_on_tick
	push_notification_on_tick()

#
# @app.task(bind=True)
# def debug_task(self):
#     print('Request: {0!r}'.format(self.request))