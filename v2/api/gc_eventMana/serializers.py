import calendar
import json

import collections

from api.noticeMana.tasks import get_from_xmpp
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum
from rest_framework import serializers

from api.commentMana.serializers import CommentSerializer
from api.inviteMana.serializers import InvitedPeopleSerialier
from core.comment.models import Comment
from core.user.models import UserProfile
from core.customer.models import Customer
from core.game.models import EventMember, HOST
from core.golfcourse.models import GolfCourseBookingSetting, GolfCourseEvent, GroupOfEvent, BonusParRule, SubGolfCourse, EventPrize, \
	GolfCourse, GolfCourseEventSchedule, GolfCourseEventMoreInfo, GolfCourseEventBanner, GolfCourseEventPriceInfo, GolfCourseEventHotel
from core.playstay.models import Hotel

from core.teetime.models import GCSetting, TeeTime, TeeTimePrice, GuestType, TeetimeShowBuggySetting
from api.buggyMana.serializers import GolfCourseBuggySerializer, GolfCourseCaddySerializer
# import base64
from core.user.models import UserProfile


from utils.django.models import get_or_none

from core.like.models import Like, View
import datetime
import arrow

from core.booking.models import BookedTeeTime, BookedPartner, BookedClubset, BookedCaddy, BookedBuggy, BookingSetting, \
	BookedTeeTime_History, BookedPartner_History, BookedGolfcourseEvent, BookedGolfcourseEventDetail, BookedPartner_GolfcourseEvent

EVENT_CTYPE = ContentType.objects.get_for_model(GolfCourseEvent)
TODAY = datetime.date.today()


class GroupOfEventSerializer(serializers.ModelSerializer):
	class Meta:
		model = GroupOfEvent
		fields = ('id', 'event', 'from_index', 'to_index', 'name')

	def to_native(self, obj):
		if obj is not None:
			serializers = super(GroupOfEventSerializer, self).to_native(obj)
			is_delete = True
			if EventMember.objects.filter(group=obj).exists():
				is_delete = False
			serializers.update({
				'delete': is_delete
			})
			return serializers


class BonusParSerializer(serializers.ModelSerializer):
	class Meta:
		model = BonusParRule
		fields = ('event', 'hole', 'par')


class GolfCourseEventSerializer(serializers.ModelSerializer):
	group = GroupOfEventSerializer(many=True, required=False, source='group_event', allow_add_remove=True)
	bonus_par = BonusParSerializer(many=True, required=False)

	class Meta:
		model = GolfCourseEvent
		fields = ('id', 'user', 'date_created', 'golfcourse', 'name', 'date_start', 'date_end', 'rule', 'time',
				  'description', 'calculation', 'group', 'bonus_par', 'event_type', 'pass_code', 'tee_type',
				  'is_publish', 'score_type', 'pod')

	@staticmethod
	def validate_tee_type(attrs, source):
		if attrs[source]:
			subgolfcourse = SubGolfCourse.objects.filter(golfcourse=attrs['golfcourse'])[0]
			if attrs[source].subgolfcourse != subgolfcourse:
				raise serializers.ValidationError('tee_type does not exist')
		return attrs

	def to_native(self, obj):
		if obj:
			serializers = super(GolfCourseEventSerializer, self).to_native(obj)
			if obj.tee_type:
				serializers.update({'tee_color': obj.tee_type.color,
									'subgolfcourse': obj.tee_type.subgolfcourse.id,
									'subgolfcourse_name': obj.tee_type.subgolfcourse.name})
			if obj.pass_code:
				serializers.update({'has_pass': True})
			else:
				serializers.update({'has_pass': False})
			user_profile = UserProfile.objects.only('display_name').get(user_id=obj.user_id)
			golfcourse = GolfCourse.objects.only('name').get(id=obj.golfcourse_id)
			serializers.update({'display_name': user_profile.display_name,
								'golfcourse_name': golfcourse.name})
			del serializers['pass_code']
			return serializers

class GolfCourseEventPriceInfoSerializer(serializers.ModelSerializer):
	class Meta:
		model = GolfCourseEventPriceInfo
		ordering = ('id',)

class GolfCourseEventHotelInfoSerializer(serializers.ModelSerializer):
	class Meta:
		model = GolfCourseEventHotel
		ordering = ('id',)
	def to_native(self, obj):
		if obj:
			serializers = super(GolfCourseEventHotelInfoSerializer, self).to_native(obj)
			if obj.hotel:
				serializers.update({'hotel_name': obj.hotel.name,
									'hotel_address': obj.hotel.address})
			return serializers

class PublicGolfCourseEventSerializer(serializers.ModelSerializer):
	event_price_info = GolfCourseEventPriceInfoSerializer(many=True, source='event_price_info', allow_add_remove=True)
	hotel_info = GolfCourseEventHotelInfoSerializer(many=True, source='event_hotel_info', allow_add_remove=True)
	class Meta:
		model = GolfCourseEvent
		fields = ('id', 'golfcourse', 'name', 'date_start', 'date_end',
				  'description', 'rule', 'user', 'score_type', 'event_type', 'banner', 'price_range', 'discount','event_price_info', 'hotel_info', 'allow_stay')

	def to_native(self, obj):
		if obj:
			serializers = super(PublicGolfCourseEventSerializer, self).to_native(obj)
			time = serializers['date_start'].strftime('%d/%m')
			if serializers['date_end'] != serializers['date_start']:
				time += ' - ' + serializers['date_end'].strftime('%d/%m')
			gc = GolfCourse.objects.only('name').get(id=obj.golfcourse_id)
			join_count = EventMember.objects.filter(event=obj, customer__isnull=True).count()
			like_count = Like.objects.filter(content_type=EVENT_CTYPE, object_id=obj.id).aggregate(Sum('count'))[
				'count__sum']
			if not like_count:
				like_count = 0
			# cmt_serializer = CommentSerializer(comments)
			partners = obj.event_member.all().exclude(status=HOST).exclude(customer__isnull=False)
			partners_serializers = InvitedPeopleSerialier(partners, many=True)
			(count, uread) = get_from_xmpp('', obj.id)
			if not serializers['description']:
				serializers['description'] = None
			serializers.update({'date': time, 'golfcourse_name': gc.name,
								'join_count': join_count,
								'like_count': like_count,
								'invite_people': partners_serializers.data,
								'name': obj.user.user_profile.display_name,
								'event_name': obj.name,
								'email': obj.user.username,
								'time': obj.time,
								'pic': obj.user.user_profile.profile_picture,
								'gender': obj.user.user_profile.gender,
								'from_user_id': obj.user_id,
								'date_creation': calendar.timegm(obj.date_created.timetuple()),
								'comment_count': count})
			if obj.pass_code:
				serializers.update({'has_pass': True})
			else:
				serializers.update({'has_pass': False})

			return serializers


class GolfCourseEventScheduleSerializer(serializers.ModelSerializer):
	class Meta:
		model = GolfCourseEventSchedule

	def to_native(self, obj):
		serializers = super(GolfCourseEventScheduleSerializer, self).to_native(obj)
		data = json.JSONDecoder(object_pairs_hook=collections.OrderedDict).decode(serializers['details'])
		serializers['details'] = data.items()
		return serializers


class GolfCourseEventMoreInfoSerializer(serializers.ModelSerializer):
	class Meta:
		model = GolfCourseEventMoreInfo

class GolfCourseEventBannerSerializer(serializers.ModelSerializer):
	class Meta:
		model = GolfCourseEventBanner




class EventPrizeSerializer(serializers.ModelSerializer):
	class Meta:
		model = EventPrize


class RegisterEventSerializer(serializers.Serializer):
	email = serializers.EmailField(required=False)
	name = serializers.CharField(required=True, max_length=500)
	phone = serializers.CharField(max_length=50)
	handicap = serializers.FloatField(required=False)
	golfcourse = serializers.IntegerField(required=False, min_value=1)


class BookedGolfcourseEventDetailSerializer(serializers.ModelSerializer):
	class Meta:
		model = BookedGolfcourseEventDetail

class GC_Booking_Serializer(serializers.ModelSerializer):
	booked_gc_event_detail = BookedGolfcourseEventDetailSerializer(many=True, source='booked_gc_event_detail', allow_add_remove=True)
	class Meta:
		model = BookedGolfcourseEvent
		exclude = ('member',)

	def to_native(self, obj):
		if obj:
			serializers = super(GC_Booking_Serializer, self).to_native(obj)
			name = obj.member.customer.name
			email = obj.member.customer.email
			phone_number = obj.member.customer.phone_number
			serializers.update({
					'member': name,
					'email': email,
					'phone_number': phone_number
				})
			return serializers

class GC_Booking_Detail_Serializer(serializers.ModelSerializer):
	booked_gc_event_detail = BookedGolfcourseEventDetailSerializer(many=True, source='booked_gc_event_detail', allow_add_remove=True)
	class Meta:
		model = BookedGolfcourseEvent
		# exclude = ('modified','created','golfcourse', 'qr_base64', 'qr_image', 'url')

	def to_native(self, obj):
		if obj is not None:

			serializers = super(GC_Booking_Detail_Serializer, self).to_native(obj)
			try:
				name = obj.member.customer.name
				email = obj.member.customer.email
				phone_number = obj.member.customer.phone_number
			except Exception as e:
				name = obj.member.user.user_profile.display_name
				email = obj.member.user.email
				phone_number = obj.member.user.user_profile.mobile

			event_member_status = obj.member.status

			checkin = 0

			'''
			Add infomation for booked golfcourse event
				- event hotel
				- location
				- event price 
			'''

			booked = get_or_none(BookedGolfcourseEvent,pk=int(obj.id))

			# try:
			# 	hotel = obj.member.event.event_hotel_info
			# except Exception as e:
			# 	pass

			# hotel_info = {}
			# if hotel and obj.member.event.allow_stay:
			# 	hotel_ID = obj.member.event.event_hotel_info.filter().values('hotel_id')
			# 	checkinDate = obj.member.event.event_hotel_info.filter().values('checkin')
			# 	checkinDate = checkinDate[0]['checkin']
			# 	checkoutDate = obj.member.event.event_hotel_info.filter().values('checkout')
			# 	checkoutDate = checkoutDate[0]['checkout']
			#
			# 	hotel_name = get_or_none(Hotel, pk = hotel_ID).name
			# 	hotel_address = get_or_none(Hotel, pk = hotel_ID).address
			# 	hotel_info = {
			# 		'hotel_name': hotel_name,
			# 		'hotel_address': hotel_address,
			# 		'checkinDate': checkinDate,
			# 		'checkoutDate': checkoutDate
			# 	}

			if obj.status == 'I':
				checkin = 1

			# for event member (models)
			member_id = obj.member_id

			# for golfcourse event (models), type = "GE",  to get more info
			gc_event_id = obj.member.event_id

			### Golfcourse Event ###
			# location
			golfcourse_name    = obj.member.event.golfcourse.name
			golfcourse_address = obj.member.event.golfcourse.address
			golfcourse_phone   = obj.member.event.golfcourse.phone
			golfcourse_website = obj.member.event.golfcourse.website
			golfcourse_hole = obj.member.event.golfcourse.number_of_hole

			gcevent_time = obj.member.event.time
			gcevent_date = obj.member.event.date_start
			gcevent_name = obj.member.event.name
			payment_discount_value_now = obj.member.event.payment_discount_value_now
			payment_discount_value_later = obj.member.event.payment_discount_value_later

			player_count = len(BookedPartner_GolfcourseEvent.objects.filter(bookedgolfcourse_id = obj.id).values_list('id', flat= True))
			# print (player_count, obj.id)
			try:
				price_info_id = obj.booked_gc_event_detail.all().first().price_info_id
				player_type = obj.member.event.event_price_info.filter(id = price_info_id).first().description
				golfcourse_price = obj.member.event.event_price_info.filter(id = price_info_id).first().price
			except Exception as e:
				player_type = golfcourse_price = None

			# print (obj.created)
			created = arrow.get(obj.created)
			gcevent_created = created.timestamp

			serializers.update({

				'member': name if name else "",
				'email': email if email else "",
				'phone_number': phone_number if phone_number else "",
				'event_member_status': event_member_status,
				'player_count': player_count,
				'gc_event_id': gc_event_id,
				#location
				'golfcourse_name': golfcourse_name,     
				'golfcourse_address': golfcourse_address,
				'golfcourse_phone': golfcourse_phone,
				'golfcourse_website': golfcourse_website,
				'hole': golfcourse_hole,
				#priceinfo
				'golfcourse_price': golfcourse_price,
				'player_type': player_type,

				'gcevent_time': gcevent_time,
				'gcevent_date': gcevent_date,
				'gcevent_name': gcevent_name,
				'payment_discount_value_now': payment_discount_value_now,
				'payment_discount_value_later': payment_discount_value_later,
				'created': gcevent_created
				#eventhotel
				# 'golfcourse_hotel': hotel_info
				})
			
			return serializers

class MyBookingSerializer_v2(serializers.ModelSerializer):
	class Meta:
		model = BookedTeeTime
		fields = ('id', 'teetime', 'modified')
		exclude = ('teetime',)

	def to_native(self, obj):
		if obj is not None:
			serializers = super(MyBookingSerializer_v2, self).to_native(obj)
			golfcourse_name = obj.golfcourse.name

			cus_id = BookedPartner.objects.filter(bookedteetime_id = int(obj.id) ).values('customer_id')  
			
			event_member_id = list(EventMember.objects.filter(customer_id__exact = cus_id).values('id'))
			
			booked_gc_event_info = []
			if event_member_id != []:
				key =  (event_member_id[0]['id'])
				booked = BookedGolfcourseEvent.objects.filter(member_id__exact = key)
				res = GC_Booking_Detail_Serializer(booked)
				booked_gc_event_info = res.data 


			serializers.update({
				'golfcourse_name': golfcourse_name,
				'teetime_date' : obj.teetime.date,
				'teetime_time' : obj.teetime.time,
				'booked_gc_event_info': booked_gc_event_info

			})
			return serializers
	

class MyBookingDetailSerializer_v2(serializers.ModelSerializer):
	class Meta:
		model = BookedTeeTime
		# exclude = ('modified','created', 'teetime', 'golfcourse', 'qr_base64', 'qr_image', 'url')

	def to_native(self, obj):
		if obj is not None:
			serializers = super(MyBookingDetailSerializer_v2, self).to_native(obj)
			checkin = 0
			if obj.status == 'I':
				checkin = 1
			book_partner = obj.book_partner.all()[0]
			customer_name = book_partner.customer.name
			customer_phone = book_partner.customer.phone_number
			customer_email = book_partner.customer.email
			setting = get_or_none(GolfCourseBookingSetting, golfcourse=obj.golfcourse)
			if setting:
				cancel_day = str(int(setting.cancel_hour / 24))
			else:
				cancel_day = ''
			teetime_price = get_or_none(TeeTimePrice, teetime_id=obj.teetime.id, hole=18)
			teetime_price2 = get_or_none(TeeTimePrice, teetime_id=obj.teetime.id, hole=obj.hole)
			discount = float(obj.discount)
			green_fee = (100 - discount) * int(teetime_price2.price) / 100

			'''
			@ add booked golfcourse event
			need custome_id
			'''

			cus_id = BookedPartner.objects.filter(bookedteetime_id = int(obj.id) ).values('customer_id')
			# print (cus_id)
			# event_member_id = list(EventMember.objects.filter(customer_id__exact = cus_id).values('id'))
			event_member_id = list(EventMember.objects.filter(customer_id__in = cus_id).values('id'))
			# print (event_member_id)
			# check_user_exist = obj.book_partner.all()
			# for i in check_user_exist:
			# 	if i.user_id:
			# 		l = list(EventMember.objects.filter(user_id=i.user_id).values_list('id', flat=True))
			# 		booked_gc_event_info = []
			# 		for item in l:
			# 			booked = BookedGolfcourseEvent.objects.filter(member_id__exact=item)
			# 			res = GC_Booking_Detail_Serializer(booked)
			# 			if res.data:
			# 				# booked_gc_event_info.append(res.data)
			# 				booked_gc_event_info= (res.data)
			#
			# 		break
			# 	else:
			#
			# 		booked_gc_event_info = []
					# if event_member_id != []:
					# 	for i in range(len(event_member_id)):
					# 		# key =  (event_member_id[0]['id'])
					# 		key =  (event_member_id[i]['id'])
					# 		booked = BookedGolfcourseEvent.objects.filter(member_id__exact = key)
					# 		res = GC_Booking_Detail_Serializer(booked)
					# 		if res.data:
					# 			booked_gc_event_info.append(res.data)

			serializers.update({
				'golfcourse_name': obj.golfcourse.name,
				'golfcourse_id': obj.golfcourse.id,
				'payment_status': obj.payment_status,
				'golfcourse_address': obj.golfcourse.address,
				'golfcourse_phone': obj.golfcourse.phone,
				'golfcourse_website':obj.golfcourse.website,
				'golfcourse_contact':obj.golfcourse.contact_info,
				# 'subgolfcourse_name': obj.subgolfcourse.name,
				'created' : round(obj.created.timestamp() * 1000),
				'teetime_date' : obj.teetime.date,
				'teetime_time' : obj.teetime.time,
				'customer_name': customer_name,
				'customer_phone': customer_phone,
				'customer_email': customer_email,
				'teetime_id' : obj.teetime.id,
				'unit_price' : green_fee,
				'checkin' : checkin,
				'cancel_day' : cancel_day,

				#gc_event_info#
				# 'booked_gc_event_info': booked_gc_event_info
			})
			return serializers