from rest_framework import serializers
import datetime
from django.utils.timezone import utc, pytz
from core.booking.models import BookedTeeTime, BookedPartner, BookedClubset, BookedCaddy, BookedBuggy, BookingSetting, BookedTeeTime_History, BookedPartner_History
from core.booking.models import BookedGolfcourseEvent, BookedGolfcourseEventDetail
from core.golfcourse.models import GolfCourse, GolfCourseBookingSetting
from core.golfcourse.models import GolfCourseBuggy,GolfCourseCaddy
from core.teetime.models import GCSetting, TeeTime, TeeTimePrice, GuestType, TeetimeShowBuggySetting
from api.buggyMana.serializers import GolfCourseBuggySerializer, GolfCourseCaddySerializer
# import base64
from core.user.models import UserProfile
from utils.django.models import get_or_none


class BookingClubSetSerializer(serializers.ModelSerializer):
	class Meta:
		model = BookedClubset
		fields = ('id', 'clubset', 'quantity',)

	def to_native(self, obj):
		if obj is not None:
			serializers = super(BookingClubSetSerializer, self).to_native(obj)
			name = obj.clubset.clubset.name
			serializers.update({
				'name': name
			})
			return serializers

class BookingSettingSerializer(serializers.ModelSerializer):
	class Meta:
		model = BookingSetting

class BookingCaddySerializer(serializers.ModelSerializer):
	class Meta:
		model = BookedCaddy
		fields = ('teetime', 'caddy', 'quantity','amount')


class BookingBuggySerializer(serializers.ModelSerializer):
	class Meta:
		model = BookedBuggy
		fields = ('teetime', 'buggy', 'quantity', 'amount')


class BookingPartnerSerializer(serializers.ModelSerializer):
	class Meta:
		model = BookedPartner
		fields = ('id', 'user', 'status')

	def to_native(self, obj):
		if obj is not None:
			serializers = super(BookingPartnerSerializer, self).to_native(obj)
			return serializers

class BookedGolfcourseEventDetailSerializer(serializers.ModelSerializer):
	class Meta:
		model = BookedGolfcourseEventDetail

class BookedGolfcourseEventSerializer(serializers.ModelSerializer):
	booked_gc_event_detail = BookedGolfcourseEventDetailSerializer(many=True, source='booked_gc_event_detail', allow_add_remove=True)
	class Meta:
		model = BookedGolfcourseEvent
	def to_native(self, obj):
		if obj:
			serializers = super(BookedGolfcourseEventSerializer, self).to_native(obj)
			try:
				name = obj.member.customer.name
				email = obj.member.customer.email
				phone_number = obj.member.customer.phone_number
			except Exception as e:
				name = obj.member.user.user_profile.display_name
				email = obj.member.user.email
				phone_number = obj.member.user.user_profile.mobile

			serializers.update({
					'member': name,
					'email': email,
					'phone_number': phone_number
				})
			return serializers

class GetTeetimeSerializer(serializers.ModelSerializer):
	class Meta:
		model = TeeTime
		exclude = ('created', 'modified', 'golfcourse', 'max_player')
	def to_native(self, obj):
		if obj:
			if obj.is_hold and obj.hold_expire < datetime.datetime.utcnow().replace(tzinfo=utc):
				obj.is_hold = False
				obj.hold_expire = None
				obj.save()
			serializers = super(GetTeetimeSerializer, self).to_native(obj)
			deal_teetime = self.context['deal_teetime']
			city = ''
			if obj.golfcourse.city:
				city = obj.golfcourse.city.name
			country = ''
			if obj.golfcourse.country:
				country = obj.golfcourse.country.name
			serializers.update({
				'golfcourse_id': obj.golfcourse.id,
				'golfcourse_name': obj.golfcourse.name,
				'golfcourse_short_name': obj.golfcourse.short_name,
				'golfcourse_address': obj.golfcourse.address,
				'golfcourse_country': country,
				'golfcourse_city': city,
				'golfcourse_phone': obj.golfcourse.phone,
				'golfcourse_website':obj.golfcourse.website,
				'golfcourse_contact':obj.golfcourse.contact_info,
				'golfcourse_owner_company':obj.golfcourse.owner_company
			})
			gtype = GuestType.objects.get(name='G')
			price = TeeTimePrice.objects.filter(teetime_id = obj.id, guest_type_id = gtype.id)
			buggy_price = None
			caddy_price = None
			## Check Buggy will be show or not
			bp = GolfCourseBuggy.objects.filter(golfcourse=obj.golfcourse, from_date__lte=obj.date, to_date__gte=obj.date).distinct('buggy').order_by('buggy','id').values('buggy','price_9','price_18','price_27','price_36')
			buggy_price = list(bp) if bp and bool([a for k,a in bp[0].items() if a != 0 and k != 'buggy']) else None
			if buggy_price and len(buggy_price) == 1:
				buggy_type = 2 if buggy_price[0]['buggy'] == 1  else 1
				buggy_price.append({'buggy': buggy_type, 'price_9': "0", 'price_36': "0", 'price_18': "0", 'price_27': "0"})
			cp = GolfCourseCaddy.objects.filter(golfcourse=obj.golfcourse).order_by('id').values('price_9','price_18','price_27','price_36')
			caddy_price = cp[0] if cp and bool([a for a in cp[0].values() if a != 0]) else None
			## Check Caddy will be show or not

			serializers['price'] = serializers['price_9'] = serializers['price_18'] = serializers['price_27'] = serializers['price_36'] = 0
			if obj.id in deal_teetime.keys():
				serializers['allow_paygc'] = False
			for p in price:
				if p.hole == 18:
					if not p.is_publish:
						return {}
					serializers['price'] = serializers['price_18'] = p.price
					serializers['discount'] = p.online_discount if obj.id not in deal_teetime.keys() else deal_teetime[obj.id]['discount_default']
					serializers['discount_online'] = p.cash_discount
					serializers['deal'] = deal_teetime[obj.id] if obj.id in deal_teetime.keys() else None
					serializers['gifts'] = p.gifts or ""
					serializers['food_voucher'] = p.food_voucher
					serializers['buggy'] = p.buggy
					serializers['caddy'] = p.caddy
					serializers['rank'] = 0
					serializers['buggy_price'] = buggy_price if p.buggy else None
					serializers['caddy_price'] = caddy_price if p.caddy else None
					if not p.teetime.available:
						serializers['discount'] = p.online_discount
					if not p.teetime.allow_payonline:
						serializers['discount_online'] = 0
				elif p.hole == 9:
					serializers['price_9'] = p.price
				elif p.hole == 27:
					serializers['price_27'] = p.price
				elif p.hole == 36:
					serializers['price_36'] = p.price
			return serializers

class BookingGolfcourseSerializer(serializers.ModelSerializer):
	class Meta:
		model = GolfCourse
		fields = ('id', 'name', 'address' )

	def to_native(self, obj):
		if obj is not None:
			serializers = super(BookingGolfcourseSerializer, self).to_native(obj)
			city = ''
			if obj.city:
				city = obj.city.id
			country = ''
			if obj.country:
				country = obj.country.name
			serializers.update({
				'city': city,
				'country' : country,
				'name': obj.short_name
			})
			return serializers


class MyBookingSerializer(serializers.ModelSerializer):
	class Meta:
		model = BookedTeeTime
		fields = ('id', 'teetime', 'modified')
		exclude = ('teetime',)

	def to_native(self, obj):
		if obj is not None:
			serializers = super(MyBookingSerializer, self).to_native(obj)
			golfcourse_name = obj.golfcourse.name
			serializers.update({
				'golfcourse_name': golfcourse_name,
				'teetime_date' : obj.teetime.date,
				'teetime_time' : obj.teetime.time
			})
			return serializers
	

class MyBookingDetailSerializer(serializers.ModelSerializer):
	class Meta:
		model = BookedTeeTime
		exclude = ('modified','created', 'teetime', 'golfcourse', 'qr_base64', 'qr_image', 'url')

	def to_native(self, obj):
		if obj is not None:
			serializers = super(MyBookingDetailSerializer, self).to_native(obj)
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
				'cancel_day' : cancel_day
			})
			return serializers

class BookingSerializer(serializers.ModelSerializer):
	clubsets = BookingClubSetSerializer(many=True, required=False, source='booked_clubset', allow_add_remove=True)
	caddies = BookingCaddySerializer(many=True, required=False, source='booked_caddy', allow_add_remove=True)
	buggies = BookingBuggySerializer(many=True, required=False, source='booked_buggy', allow_add_remove=True)
	partners = BookingPartnerSerializer(many=True, required=False, source='partner', allow_add_remove=True)
	customer_email = serializers.CharField(max_length=100, required=False)
	customer_name = serializers.CharField(max_length=100, required=False)
	customer_phone = serializers.CharField(max_length=100, required=False)

	class Meta:
		model = BookedTeeTime
		# fields = ('id', 'golfcourse', 'subgolfcourse', 'clubsets', 'caddies', 'buggies', 'partners',
		#           'date_to_play', 'time_to_play', 'booked_for', 'booked_for_customer', 'player_count', 'payment_type',
		#           'book_type', 'total_amount', 'paid_amount', 'buggy_amount', 'caddy_amount', 'clubset_amount',
		#           'reservation_code', 'status', 'user', 'date_creation', 'date_modified', 'caddy_count')

	def to_native(self, obj):
		if obj is not None:
			serializers = super(BookingSerializer, self).to_native(obj)
			is_visitor = False
			if obj.booked_for:
				book_for_name = obj.booked_for.user_profile.display_name
				book_for_email = obj.booked_for.username
				book_for_phone = obj.booked_for.user_profile.mobile
				serializers.update({'book_for_username': book_for_name, 'book_for_useremail': book_for_email,
									'book_for_userphone': book_for_phone})
			if obj.booked_for_customer:
				customer_name = obj.booked_for_customer.name
				customer_email = obj.booked_for_customer.email
				customer_phone = obj.booked_for_customer.phone_number
				serializers.update({'customer_name': customer_name, 'customer_email': customer_email,
									'customer_phone': customer_phone})
				is_visitor = True
			username = obj.user.user_profile.display_name
			mobile = obj.user.user_profile.mobile
			user_email = obj.user.username
			golfcourse_name = obj.golfcourse.name
			clubset_number = obj.booked_clubset.all().count()
			caddy_number = obj.booked_caddy.all().count()
			buggy_number = obj.booked_buggy.all().count()
			serializers.update({
				'clubset_number': clubset_number,
				'buggy_number': buggy_number,
				'caddy_number': caddy_number,
				'golfcourse_name': golfcourse_name,
				'booked_by_name': username,
				'booked_by_email': user_email,
				'is_visitor': is_visitor,
			})
			return serializers

	def get_validation_exclusions(self, instance=None):
		exclusions = super(BookingSerializer, self).get_validation_exclusions(instance)
		return exclusions + ['clubsets'] + ['caddies'] + ['buggies'] + ['partners']

class ComissionSerializer(serializers.ModelSerializer):
	class Meta:
		model = BookedTeeTime
		exclude = ('modified','created', 'teetime', 'golfcourse')
	def to_native(self, obj):
		if obj is not None:
			serializers = {}
			checkin = 0
			if obj.status == 'I':
				checkin = 1
			book_partner = obj.book_partner.all()[0]
			customer_name = book_partner.customer.name
			customer_phone = book_partner.customer.phone_number
			customer_email = book_partner.customer.email
			player_count = obj.player_count if checkin == 0 else obj.player_checkin_count
			serializers.update({
				'id': obj.id,
				'created' : round(obj.created.timestamp() * 1000),
				'teetime_date' : datetime.datetime.combine(obj.teetime.date, datetime.datetime.min.time()).timestamp() * 1000,
				'teetime_time' : datetime.timedelta(hours=obj.teetime.time.hour,minutes=obj.teetime.time.minute).total_seconds() * 1000,
				'customer_name': customer_name,
				'customer_phone': customer_phone,
				'customer_email': customer_email,
				'golfcourse_name': obj.golfcourse.name,
				'teetime_id' : obj.teetime.id,
				'player_count': player_count,
				'checkin': checkin,
				'hole': obj.hole,
				'discount': obj.discount
			})
			return serializers

class BookedTeeTimeSerializer(serializers.ModelSerializer):
	class Meta:
		model = BookedTeeTime
		exclude = ('modified','created', 'teetime', 'golfcourse')

	def to_native(self, obj):
		if obj is not None:
			serializers = super(BookedTeeTimeSerializer, self).to_native(obj)
			checkin = 0
			if obj.status == 'I':
				checkin = 1
			customer_name = customer_phone = customer_email = ""
			book_partner = obj.book_partner.all().first()
			if book_partner:
				customer_name = book_partner.customer.name
				customer_phone = book_partner.customer.phone_number
				customer_email = book_partner.customer.email
			teetime_price = get_or_none(TeeTimePrice, teetime_id=obj.teetime.id, hole=18)
			teetime_price2 = get_or_none(TeeTimePrice, teetime_id=obj.teetime.id, hole=obj.hole)
			discount = float(obj.discount) or float(teetime_price.online_discount)
			green_fee = (100 - discount) * int(teetime_price2.price) / 100
			buggy = get_or_none(BookedBuggy, teetime=serializers['id'])
			caddy = get_or_none(BookedCaddy, teetime=serializers['id'])
			#bb = get_or_none(GolfCourseBuggy, golfcourse=obj.golfcourse.id)
			bp = GolfCourseBuggy.objects.filter(golfcourse=obj.golfcourse.id, from_date__lte=obj.teetime.date, to_date__gte=obj.teetime.date, buggy=1).distinct('buggy').order_by('buggy','id').values('buggy','price_9','price_18','price_27','price_36')
			bb = bp[0] if bp and bool([a for k,a in bp[0].items() if a != 0 and k != 'buggy']) else None

			bc = get_or_none(GolfCourseCaddy, golfcourse=obj.golfcourse.id)
			buggy_qty = 0
			buggy_unit_price = 0
			caddy_qty = 0
			caddy_unit_price = 0
			if buggy:
				buggy_qty = buggy.quantity
				buggy_unit_price = buggy.amount
			else:
				if bb:
					if int(serializers['hole']) == 9:
						buggy_unit_price = bb['price_9'] or 0
					elif int(serializers['hole']) == 18:
						buggy_unit_price = bb['price_18'] or 0
					elif int(serializers['hole']) == 27:
						buggy_unit_price = bb['price_27'] or 0
					else:
						buggy_unit_price = bb['price_36'] or 0
			if caddy:
				caddy_qty = caddy.quantity
				caddy_unit_price = caddy.amount
			else:
				if bc:
					if int(serializers['hole']) == 9:
						caddy_unit_price = bc.price_9 or 0
					elif int(serializers['hole']) == 18:
						caddy_unit_price = bc.price_18 or 0
					elif int(serializers['hole']) == 27:
						caddy_unit_price = bc.price_27 or 0
					else:
						caddy_unit_price = bc.price_36 or 0
			serializers.update({
				'golfcourse_id': obj.golfcourse.id,
				'golfcourse_name': obj.golfcourse.name,
				'golfcourse_address': obj.golfcourse.address,
				'golfcourse_phone': obj.golfcourse.phone,
				'golfcourse_website':obj.golfcourse.website,
				'golfcourse_contact':obj.golfcourse.contact_info,
				'created' : round(obj.created.timestamp() * 1000),
				'teetime_date' : datetime.datetime.combine(obj.teetime.date, datetime.datetime.min.time()).timestamp() * 1000,
				'teetime_time' : datetime.timedelta(hours=obj.teetime.time.hour,minutes=obj.teetime.time.minute).total_seconds() * 1000,
				'date' : str(obj.teetime.date),
				'time' : str(obj.teetime.time),
				'customer_name': customer_name,
				'customer_phone': customer_phone,
				'customer_email': customer_email,
				'teetime_id' : obj.teetime.id,
				'unit_price' : green_fee,
				'description' : obj.teetime.description,
				'buggy_qty': buggy_qty,
				'caddy_qty': caddy_qty,
				'caddy_unit_price': caddy_unit_price,
				'buggy_unit_price': buggy_unit_price,
				'checkin' : checkin,
				'food_voucher': teetime_price.food_voucher,
				'gifts': teetime_price.gifts
			})
			return serializers

class BookedGCSerializer(serializers.ModelSerializer):
	class Meta:
		model = BookedTeeTime
		exclude = ('modified','created', 'teetime', 'golfcourse')

	def to_native(self, obj):
		if obj is not None:
			serializers = super(BookedGCSerializer, self).to_native(obj)
			book_partner = obj.book_partner.all().first()
			if book_partner:  
				customer_name = book_partner.customer.name
				customer_phone = book_partner.customer.phone_number
				customer_email = book_partner.customer.email
			else:
				customer_name = customer_phone = customer_email = ""
			teetime_price = get_or_none(TeeTimePrice, teetime_id=obj.teetime.id, hole=18)
			teetime_price2 = get_or_none(TeeTimePrice, teetime_id=obj.teetime.id, hole=obj.hole)
			discount = float(obj.discount) or float(teetime_price.online_discount)
			green_fee = (100 - discount) * int(teetime_price2.price) / 100
			buggy = get_or_none(BookedBuggy, teetime=serializers['id'])
			caddy = get_or_none(BookedCaddy, teetime=serializers['id'])
			#bb = get_or_none(GolfCourseBuggy, golfcourse=obj.golfcourse.id)
			bp = GolfCourseBuggy.objects.filter(golfcourse=obj.golfcourse, from_date__lte=obj.teetime.date, to_date__gte=obj.teetime.date, buggy=1).distinct('buggy').order_by('buggy','id').values('buggy','price_9','price_18','price_27','price_36')
			bb = bp[0] if bp and bool([a for k,a in bp[0].items() if a != 0 and k != 'buggy']) else None
			bc = get_or_none(GolfCourseCaddy, golfcourse=obj.golfcourse.id)
			buggy_qty = 0
			buggy_unit_price = 0
			caddy_qty = 0
			caddy_unit_price = 0
			if buggy:
				buggy_qty = buggy.quantity
				buggy_unit_price = buggy.amount
			else:
				if bb:
					if int(serializers['hole']) == 9:
						buggy_unit_price = bb['price_9'] or 0
					elif int(serializers['hole']) == 18:
						buggy_unit_price = bb['price_18'] or 0
					elif int(serializers['hole']) == 27:
						buggy_unit_price = bb['price_27'] or 0
					else:
						buggy_unit_price = bb['price_36'] or 0
			if caddy:
				caddy_qty = caddy.quantity
				caddy_unit_price = caddy.amount
			else:
				if bc:
					if int(serializers['hole']) == 9:
						caddy_unit_price = bc.price_9 or 0
					elif int(serializers['hole']) == 18:
						caddy_unit_price = bc.price_18 or 0
					elif int(serializers['hole']) == 27:
						caddy_unit_price = bc.price_27 or 0
					else:
						caddy_unit_price = bc.price_36 or 0
			status = 1
			if obj.teetime.is_booked:
				status = 2 # booked
			elif obj.teetime.is_request:
				status = 1 #Just request
				serializers['reservation_code'] = ''
			checkin = 0
			if obj.status == 'I':
				checkin = 1
			serializers.update({
				'available': obj.teetime.available,
				'golfcourse_id': obj.golfcourse.id,
				'golfcourse_name': obj.golfcourse.name,
				'golfcourse_address': obj.golfcourse.address,
				'golfcourse_phone': obj.golfcourse.phone,
				'golfcourse_website':obj.golfcourse.website,
				'golfcourse_contact':obj.golfcourse.contact_info,
				'created' : round(obj.created.timestamp() * 1000),
				'teetime_date' : datetime.datetime.combine(obj.teetime.date, datetime.datetime.min.time()).timestamp() * 1000,
				'teetime_time' : datetime.timedelta(hours=obj.teetime.time.hour,minutes=obj.teetime.time.minute).total_seconds() * 1000,
				'customer_name': customer_name,
				'customer_phone': customer_phone,
				'customer_email': customer_email,
				'teetime_id' : obj.teetime.id,
				'unit_price' : green_fee,
				'description' : obj.teetime.description,
				'buggy_qty': buggy_qty,
				'caddy_qty': caddy_qty,
				'caddy_unit_price': caddy_unit_price,
				'buggy_unit_price': buggy_unit_price,
				'food_voucher': teetime_price.food_voucher,
				'gifts': teetime_price.gifts,
				'payment_type': obj.payment_type,
				'checkin': checkin,
				'status': status
			})
			return serializers

class BookedTeeTime_HistorySerializer(serializers.ModelSerializer):
	class Meta:
		model = BookedTeeTime_History

	def to_native(self, obj):
		if obj is not None:
			serializers = super(BookedTeeTime_HistorySerializer, self).to_native(obj)
			checkin = 0
			if obj.status == 'I':
				checkin = 1
			book_partner = obj.book_partner_his.all()[0]            
			customer_name = book_partner.customer.name
			customer_phone = book_partner.customer.phone_number
			customer_email = book_partner.customer.email
			teetime_price = get_or_none(TeeTimePrice, teetime_id=obj.teetime.id, hole=18)
			#teetime_price2 = get_or_none(TeeTimePrice, teetime_id=obj.teetime.id, hole=obj.booked_teetime.hole)
			#green_fee = (100 - float(teetime_price.online_discount)) * int(teetime_price2.price) / 100
			serializers.update({
				'golfcourse_id': obj.golfcourse.id,
				'golfcourse_name': obj.golfcourse.name,
				'golfcourse_address': obj.golfcourse.address,
				'golfcourse_phone': obj.golfcourse.phone,
				'golfcourse_website':obj.golfcourse.website,
				'golfcourse_contact':obj.golfcourse.contact_info,
				'created' : round(obj.created.timestamp() * 1000),
				'cancel_on' : round(obj.cancel_on.timestamp() * 1000) if obj.cancel_on else None ,
				'teetime_date' : datetime.datetime.combine(obj.teetime.date, datetime.datetime.min.time()).timestamp() * 1000,
				'teetime_time' : datetime.timedelta(hours=obj.teetime.time.hour,minutes=obj.teetime.time.minute).total_seconds() * 1000,
				'date' : str(obj.teetime.date),
				'time' : str(obj.teetime.time),
				'customer_name': customer_name,
				'customer_phone': customer_phone,
				'customer_email': customer_email,
				'teetime_id' : obj.teetime.id,
				'unit_price' : 0,
				'description' : '',
				'buggy_qty': 0,
				'caddy_qty': 0,
				'caddy_unit_price': 0,
				'buggy_unit_price': 0,
				'checkin' : checkin,
				'food_voucher': False,
				'gifts': ''
			})
			return serializers

class BookedPartner_HistorySerializer(serializers.ModelSerializer):
	class Meta:
		model = BookedPartner_History

	def to_native(self, obj):
		if obj is not None:
			serializers = super(BookedPartner_HistorySerializer, self).to_native(obj)
			# if obj.user:
			#     email = obj.user.email
			#     mobile = obj.user.user_profile.mobile
			#     display_name = obj.user.user_profile.display_name
			# else:
			#     email = obj.email
			#     mobile = ''
			#     display_name = ''
			# serializers.update({
			#     'email': email,
			#     'phone': mobile,
			#     'name': display_name
			# })
			return serializers

