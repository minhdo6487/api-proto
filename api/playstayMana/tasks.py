import base64
import json
import os
from email.mime.image import MIMEImage
from GolfConnect.settings import REDIS_HOST, REDIS_PORT, REDIS_DB, CURRENT_ENV, PAYMERCHANTCODE, PAYPASSCODE, PAYSECRETKEY, PAYURL
from django.utils.timezone import utc, pytz
from django.template import Context,Template
from django.template.loader import render_to_string, get_template
import redis
from celery import shared_task, task
from GolfConnect.settings import REDIS_HOST, REDIS_PORT, REDIS_DB, SETTINGS_PATH
from django.core.mail.message import (
	DEFAULT_ATTACHMENT_MIME_TYPE, BadHeaderError, EmailMessage,
	EmailMultiAlternatives, SafeMIMEMultipart, SafeMIMEText,
	forbid_multi_line_headers, make_msgid,
)
from core.playstay.models import PackageTour, Hotel, PackageTourReview, BookedPackageTour, PackageGolfcourseFee, \
    PackageHotelRoomFee, PackageAdditionalFee, ParentPackageTour
from .serializers import PackageTourSerializer, ParentPackageTourListSerializer, ParentPackageTourDetailSerializer, PaginatedPackageTourSerializer, HotelSerializer, \
    PackageTourReviewSerializer, PaginatedPackageReviewSerializer, BookedPackageTourSerializer
redis_server = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
EMAIL_TEMPLATE_PATH = os.path.join(SETTINGS_PATH,'media/email_template/')


@task(name="playstay_request_booking_email")
def playstay_request_booking_email(booked_id):
	email_path = EMAIL_TEMPLATE_PATH + "playstay_request.html"
	booked = BookedPackageTour.objects.get(pk=booked_id)
	booked_data = BookedPackageTourSerializer(booked).data
	package_tour = PackageTour.objects.filter(id=booked_data['package_tour']).first()
	with open(email_path, encoding="utf-8") as f:
		data= f.read()
		if CURRENT_ENV == 'prod':
			bcc_email = ['booking@golfconnect24.com']
		else:
			bcc_email = []
		total_cost = int(booked_data['total_cost'])
		data = data.replace('{customer_name}',booked_data['customer_name'])
		data = data.replace('{booked_id}',booked_data['reservation_code'])
		data = data.replace('{customer_phone}',booked_data['customer_phone'])
		data = data.replace('{customer_email}',booked_data['customer_email'])
		data = data.replace('{total_cost}', "{:,}".format(total_cost))
		data = data.replace('{checkin_date}',booked_data['checkin_date'].strftime('%b %d, %Y'))
		data = data.replace('{checkout_date}',booked_data['checkout_date'].strftime('%b %d, %Y'))
		data = data.replace('{note}',booked_data['note'])
		data = data.replace('{no_nights}',str(booked_data['quantity']))
		if len(booked_data['golfcourses']) > 1:
			no_rounds = len(booked_data['golfcourses'])
		else:
			no_rounds = booked_data['golfcourses'][0]['no_round']
		no_rooms = 0
		total_stay = 0

		template_hotel = """
		<tr align="center">
            <td align="left" valign="top" width="60%">
                <span style="margin: 0; font-size: 15px; line-height: 21px; font-family: 'Helvetica', Arial, sans-serif; color: #333333;">
                            <span id="ctl13_lblRoomName">{hotel_name} - {room_name}</span></span>
            </td>
            <td align="right" valign="top" width="40%">
                <span style="margin: 0; font-size: 15px; line-height: 21px; font-family: 'Helvetica', Arial, sans-serif; color: #333333;">
                            <span id="ctl13_lblRoomPrice">{hotel_no_rooms} Room{scale}</span>
                </span>
            </td>
        </tr>
		"""
		template_golfcourse = """
		<tr align="center">
            <td align="left" valign="top" width="60%">
                <span style="margin: 0; font-size: 15px; line-height: 21px; font-family: 'Helvetica', Arial, sans-serif; color: #333333;">
                            <span id="ctl13_lblRoomName">{golfcourse_name}</span></span>
            </td>
            <td align="right" valign="top" width="40%">
                <span style="margin: 0; font-size: 15px; line-height: 21px; font-family: 'Helvetica', Arial, sans-serif; color: #333333;">
                            <span id="ctl13_lblRoomPrice">{golfcourse_no_round} Round{scale}</span>
                </span>
            </td>
        </tr>

		"""
		package_hotel = ""
		for hotel in booked_data['hotels']:
			no_rooms += hotel['quantity']
			total_stay += int(hotel['price'])
			td = {'room_name': hotel['info']['room_info']['name'], 'hotel_no_rooms': hotel['quantity'], 'hotel_name': hotel['name'], 'scale': 's' if hotel['quantity'] > 1 else ''}
			package_hotel += template_hotel.format(**td)

		total_play = 0
		package_golfcourse = ""
		golfcourse_no_round = 1 if len(booked_data['golfcourses']) > 1 else 0
		for golfcourse in booked_data['golfcourses']:
			total_play += int(golfcourse['price'])
			gc_round = golfcourse_no_round or golfcourse['no_round']
			td = {'golfcourse_name': golfcourse['info']['golfcourse_info']['name'], 'golfcourse_no_round': gc_round, 'scale': 's' if (gc_round > 1) else ''}
			package_golfcourse += template_golfcourse.format(**td)
		total_stay *= booked_data['quantity']
		#total_play *= 1 if len(booked_data['golfcourses']) > 1 else booked_data['quantity']
		no_golfer = booked_data['golfcourses'][0]['quantity']
		data = data.replace('{no_rooms}',str(no_rooms))
		data = data.replace('{no_golfer}',str(no_golfer))
		data = data.replace('{total_stay}', "{:,}".format(total_stay))
		data = data.replace('{total_play}', "{:,}".format(total_play))
		data = data.replace('{package_hotel}',package_hotel)
		data = data.replace('{package_golfcourse}',package_golfcourse)
		scale_nogolfer = 's' if no_golfer > 1 else ''
		data = data.replace('{scale_nogolfer}',scale_nogolfer)

		total_sum = total_play+total_stay
		data = data.replace('{total_sum}', "{:,}".format(total_sum))
		
		template_discount = """
		<tr align="center">
            <td align="left" style="border-top: 1px dotted #dedede;">
                <strong style="margin: 0; font-size: 15px; line-height: 21px; font-family: 'Helvetica', Arial, sans-serif; color: #333333;">
					<span id="ctl13_lblTxtTotalPrice">Discount (-{0}%)</span>
				</strong>
            </td>
            <td align="right" valign="top" width="40%" style="border-top: 1px dotted #dedede;">
                <strong style="margin: 0; font-size: 15px; line-height: 21px; font-family: 'Helvetica', Arial, sans-serif; color: #333333;">
					<span id="ctl13_lblTotalPrice">VND -{1:,}</span>
				</strong>
            </td>
        </tr>
		"""
		if booked_data['discount']:
			td = template_discount.format(package_tour.discount,total_play+total_stay-total_cost)
			data = data.replace('{discount_amount}',td)
		else:
			data = data.replace('{discount_amount}','')
		hotel_id = int(booked_data['hotels'][0]['info']['room_info']['hotel'])
		hotel = Hotel.objects.get(pk=hotel_id)

		data = data.replace('{hotel_name}',hotel.name.upper())
		data = data.replace('{hotel_address}',(hotel.address or ''))
		data = data.replace('{hotel_image}',hotel.hotel_images.all()[0].url if hotel.hotel_images.all().count() > 0 else '')

		package_tour = PackageTour.objects.get(pk=booked_data['package_tour'])
		package_name = "{0} | {1} round{2} {3} night{4}".format(package_tour.title, no_rounds, 's' if no_rounds > 1 else '',booked_data['quantity'], 's' if booked_data['quantity'] > 1 else '')
		data = data.replace('{package_name}',package_name)

		template_currency = """
		<tr align="center">
            <td align="left" align="right" valign="top" width="40%">
                <strong style="margin: 0; font-size: 20px; line-height: 21px; font-family: 'Helvetica', Arial, sans-serif; color: #333333;">
				    <span id="ctl13_lblTxtTotalPrice"></span>
				</strong>
            </td>
            <td align="right" valign="top" width="40%">
                <strong style="margin: 0; font-size: 20px; line-height: 21px; font-family: 'Helvetica', Arial, sans-serif; color: #333333;">
					<span id="ctl13_lblTotalPrice">{currencyCode} {currencyValue}*</span>
				</strong>
            </td>
        </tr>
		"""
		#round(a,2)
		if booked_data['currencyCode'] and booked_data['currencyCode'] != 'VND':
			temp_currency = {'currencyCode': booked_data['currencyCode'], 'currencyValue': round(booked_data['currencyValue'],2)}
			currency = template_currency.format(**temp_currency)
			data = data.replace('{currency}', currency)
		else:
			data = data.replace('{currency}', '')
		email = [booked_data['customer_email']]
		ctx = {'email':booked_data['customer_email']}
		text = 'Thanks you for your booking with GolfConnect24'
		template_data = Template(data)
		message = template_data.render(Context(ctx))
		msg = EmailMessage('GOLFCONNECT24 BOOKING REQUEST #{}'.format(booked_data['reservation_code']), message,
								from_email='GolfConnect24 <no-reply@golfconnect24.com>', to=email,bcc=bcc_email)
		msg.content_subtype = "html"
		msg.send()
	return
	
