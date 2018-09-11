import datetime
import uuid
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save,pre_delete
from django.dispatch import receiver
from django.db import IntegrityError
from django.db.models import Q

from core.golfcourse.models import GolfCourseBuggy, GolfCourseClubSets, GolfCourseCaddy
from core.golfcourse.models import GolfCourse, SubGolfCourse
from core.golfcourse.models import GolfCourseEvent, GolfCourseEventPriceInfo
from core.game.models import EventMember
from core.teetime.models import TeeTime
# from core.teetime.models import TeeTimeSetting
from core.customer.models import Customer
from core.notice.models import Notice
from core.user.models import UserProfile
from utils.rest.sendemail import send_email, send_generate_email


CHECK_IN = 'I'
CANCEL = 'C'
PENDING_PAID = 'PP'
PENDING_UPAID = 'PU'
BOOKING_PROCESS = 'PR'
BOOKING_REQUEST = 'R'
STATUS_CHOICES = (
		(CHECK_IN, 'Check In'),
		(CANCEL, 'Cancel'),
		(BOOKING_REQUEST, 'Booking Request'),
		(PENDING_PAID, 'Pending paid'),
		(PENDING_UPAID, 'Pending unpaid'),
		(BOOKING_PROCESS, 'Booking Process'))

FULL = 'F'
NOPAY = 'N'
PAYMENT_CHOICES = (
		(FULL, 'Full'),
		(NOPAY, 'NoPay'))

ONLINE = 'O'
PHONE = 'P'
WALKIN = 'W'
EMAIL = 'E'
BOOK_CHOICES = (
		(ONLINE, 'online'),
		(PHONE, 'Phone'),
		(WALKIN, 'Walkin'),
		(EMAIL, 'Email'))

SHOWUP = 'S'
ACCEPT = 'A'
PENDING_PAID = 'PP'
PENDING_UPAID = 'PU'
PARTNER_CHOICES = (
		(SHOWUP, 'ShowUp'),
		(CANCEL, 'Cancel'),
		(PENDING_PAID, 'Pending paid'),
		(PENDING_UPAID, 'Pending unpaid'),)

VNG = '123Pay'
VTC = 'VTCPay'
BOOKING_VENDOR = (
	(VNG, '123Pay'),
	(VTC, 'VTCPay'))

TRANSACTIONSTATUS = {
	-10: 'Giao dịch không tồn tại. Vui lòng thực hiện giao dịch mới',
	-100: 'Đơn hàng bị hủy',
	-20: 'Đơn hàng bị hủy',
	10: 'Đang kiểm tra thông tin tài khoản. Giao dịch chưa bị trừ tiền',
	20: 'Đang xác định trạng thái thanh toán từ ngân hàng',
	5000: 'Hệ thống bận',
	6000: 'Xác thực nguồn gọi thất bại',
	6100: 'Tham số truyền vào không đúng định dạng yêu cầu',
	6200: 'Vi phạm quy định nghiệp vụ  giữa đối tác & 123Pay',
	6212: 'Ngoài giới hạn thanh toán / giao dịch',
	7200: 'Thông tin thanh toán không hợp lệ',
	7201: 'Không đủ tiền trong tài khoản thanh toán',
	7202: 'Không đảm bảo số dư tối thiểu trong tài khoản thanh toán',
	7203: 'Giới hạn tại ngân hàng: Tổng số tiền / ngày',
	7204: 'Giới hạn tại ngân hàng: Tổng số giao dịch / ngày',
	7205: 'Giới hạn tại ngân hàng: Giá trị / giao dịch',
	7210: 'Khách hàng không nhập thông tin thanh toán',
	7211: 'Chưa đăng ký dịch vụ thanh toán trực tuyến',
	7212: 'Dịch vụ thanh toán trực tuyến của tài khoản đang tạm khóa',
	7213: 'Tài khoản thanh toán bị khóa',
	7220: 'Khách hàng không nhập OTP',
	7221: 'Nhập sai thông tin thẻ/tài khoản quá 3 lần',
	7222: 'Sai thông tin OTP',
	7223: 'OTP hết hạn',
	7224: 'Nhập sai thông tin OTP quá 3 lần',
	7231: 'Sai tên chủ thẻ',
	7232: 'Card không hợp lệ, không tìm thấy khách hàng / tài khoản',
	7233: 'Expired Card',
	7234: 'Lost Card',
	7235: 'Stolen Card',
	7236: 'Card is marked deleted',
	7241: 'Credit Card - Card Security Code verification failed',
	7242: 'Credit Card - Address Verification Failed',
	7243: 'Credit Card - Address Verification and Card Security Code Failed',
	7244: 'Credit Card - Card did not pass all risk checks',
	7245: 'Credit Card - Bank Declined Transaction',
	7246: 'Credit Card - Account has stop/hold(hold money,...)',
	7247: 'Credit Card - Account closed',
	7248: 'Credit Card - Frozen Account',
	7300: 'Lỗi giao tiếp hệ thống ngân hàng',
	7299: 'Giao dịch không thành công',
}

class GC24BookingVendor(models.Model):
		booking_vendor = models.CharField(max_length=7, choices=BOOKING_VENDOR, default=VTC)

class Voucher(models.Model):
		code = models.CharField(max_length=20, unique=True)
		is_used = models.BooleanField(default=False,db_index=True)
		date_created = models.DateTimeField(null=True, blank=True, editable=False)
		discount_amount = models.FloatField(default=0)
		from_date = models.DateTimeField(null=True, blank=True,db_index=True)
		to_date = models.DateTimeField(null=True, blank=True,db_index=True)

		def save(self, *args, **kwargs):
				""" On save, update timestamps
				"""
				if not self.id:
						self.created = datetime.datetime.today()
						self.code = self.code.upper()
				return super(Voucher, self).save(*args, **kwargs)

		def __str__(self):
				return self.code + '-' + str(self.from_date) + '-' + str(self.to_date) + '-' + str(self.is_used)  

def create_voucher(number,from_date, to_date, amount):
		for i in range(0, number):
				done = False
				while not done:
						try:
								code = str(uuid.uuid4())
								voucher_code = code[:6]
								Voucher.objects.create(code=voucher_code, from_date=from_date, to_date=to_date, discount_amount=amount)
								done = True
						except IntegrityError:
								done = False

class PayTransactionStore(models.Model):
		payTransactionid    = models.TextField(null=True, unique=True)
		transactionId       = models.TextField(null=True, unique=True)
		transactionStatus   = models.TextField(null=True,default="0")
		totalAmount         = models.TextField(null=True)
		opAmount            = models.TextField(null=True)
		bankCode            = models.TextField(null=True)
		description         = models.TextField(null=True)
		clientIP         = models.TextField(null=True,default="127.0.0.1")
		vendor 			 = models.TextField(null=True)
		created = models.DateTimeField(null=True, blank=True, editable=False)
		def __str__(self):
			return self.transactionId
		def save(self, *args, **kwargs):
			if not self.id:
				self.created = datetime.datetime.today()
			return super(PayTransactionStore, self).save(*args, **kwargs)


class BookedTeeTime(models.Model):
		""" This model stores only booked time slot
		"""
		teetime              = models.ForeignKey(TeeTime, related_name='booked_teetime',unique=True)
		golfcourse           = models.ForeignKey(GolfCourse, related_name='booked_teetime')
		# subgolfcourse        = models.ForeignKey(SubGolfCourse, null=True, blank=True)
		reservation_code     = models.TextField(editable=False, unique=True)
		created              = models.DateTimeField(null=True, blank=True, editable=False)
		modified             = models.DateTimeField(null=True, blank=True)
		player_count         = models.PositiveIntegerField(default=1)
		player_checkin_count = models.PositiveIntegerField(default=0)
		payment_type     = models.CharField(max_length=1,
																		choices=PAYMENT_CHOICES,
																		default=NOPAY)
		status          = models.CharField(max_length=2,
															choices=STATUS_CHOICES,
															default=BOOKING_REQUEST)
		book_type       = models.CharField(max_length=1,
																 choices=BOOK_CHOICES,
																 default=ONLINE)
		hole        = models.PositiveSmallIntegerField(default=18)
		total_cost  = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
		paid_amount = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)   
		url         = models.URLField(null=True, blank=True)
		qr_image    = models.ImageField(
												upload_to="qr_codes/",
												null=True,
												blank=True,
												editable=False
										)
		qr_base64     = models.TextField(editable=False)
		qr_url      = models.URLField(null=True, blank=True)
		voucher_code = models.CharField(max_length=20, blank=True, null=True)
		discount = models.FloatField(default=0)
		payment_status = models.BooleanField(default=False)
		company_address =  models.CharField(max_length=100, blank=True, null=True)
		invoice_address =  models.CharField(max_length=100, blank=True, null=True)
		invoice_name = models.CharField(max_length=100, blank=True, null=True)
		tax_code = models.CharField(max_length=100, blank=True, null=True)
		voucher_discount_amount = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
		user_device = models.CharField(max_length=3, blank=True, null=True, default='web')
		currencyCode = models.CharField(max_length=20, blank=True, null=True, default='VND')
		currencyValue = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
		back_link = models.CharField(max_length=255, blank=True, null=True)
		note = models.TextField(null=True,blank=True)
		
		def save(self, *args, **kwargs):
				""" On save, update timestamps
				"""
				if not self.id:
						self.created = datetime.datetime.today()
				if not (self.status == CHECK_IN or self.status == CANCEL):
					if self.teetime.is_booked:
						if self.payment_status:
							self.status = PENDING_PAID
						elif self.payment_type == 'F':
							self.status = BOOKING_PROCESS
						else:
							self.status = PENDING_UPAID
					elif self.teetime.is_request:
						self.status = BOOKING_REQUEST
				self.modified = datetime.datetime.today()
				return super(BookedTeeTime, self).save(*args, **kwargs)

		@staticmethod
		def __string__():
				return "Time Slot"
class BookedTeeTime_History(models.Model):
		""" This model stores only booked time slot
		"""
		booked_teetime = models.IntegerField(default=0, db_index=True)
		teetime              = models.ForeignKey(TeeTime, related_name='booked_teetime_his')
		golfcourse           = models.ForeignKey(GolfCourse, related_name='booked_teetime_his')
		# subgolfcourse        = models.ForeignKey(SubGolfCourse, null=True, blank=True)
		reservation_code     = models.TextField(editable=False)
		created              = models.DateTimeField(null=True, blank=True, editable=False)
		modified             = models.DateTimeField(null=True, blank=True)
		player_count         = models.PositiveIntegerField(default=1)
		player_checkin_count = models.PositiveIntegerField(default=0)
		payment_type     = models.CharField(max_length=1,
																		choices=PAYMENT_CHOICES,
																		default=NOPAY)
		payment_status  = models.BooleanField(default=False)
		status          = models.CharField(max_length=2,
															choices=STATUS_CHOICES,
															default=PENDING_UPAID)
		book_type       = models.CharField(max_length=1,
																 choices=BOOK_CHOICES,
																 default=ONLINE)
		total_cost  = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
		paid_amount = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)   
		url         = models.URLField(null=True, blank=True)
		qr_image    = models.ImageField(
												upload_to="qr_codes/",
												null=True,
												blank=True,
												editable=False
										)
		qr_base64     = models.TextField(editable=False)
		qr_url      = models.URLField(null=True, blank=True)
		cancel_on   = models.DateTimeField(null=True, blank=True, editable=False)
		def save(self, *args, **kwargs):
			if not self.id:
				self.cancel_on = datetime.datetime.today()
			return super(BookedTeeTime_History, self).save(*args, **kwargs)

class BookedPartner_History(models.Model):
		bookedteetime = models.ForeignKey(BookedTeeTime_History, related_name='book_partner_his')
		user          = models.ForeignKey(User,null=True,blank=True, related_name='book_partner_his')
		customer      = models.ForeignKey(Customer,null=True,blank=True, related_name='book_partner_his')
		status        = models.CharField(max_length=2,
															choices=PARTNER_CHOICES,
															default=PENDING_UPAID)

class BookingSetting(models.Model):
		code     = models.CharField(max_length=100, db_index=True, unique=True)
		value    = models.CharField(max_length=1000)
		created  = models.DateTimeField(null=True, blank=True, editable=False)
		modified = models.DateTimeField(null=True, blank=True)

		def save(self, *args, **kwargs):
				""" On save, update timestamps
				"""
				if not self.id:
						self.created = datetime.datetime.today()
				self.modified = datetime.datetime.today()
				return super(BookingSetting, self).save(*args, **kwargs)


class BookedPartner(models.Model):
		bookedteetime = models.ForeignKey(BookedTeeTime, related_name='book_partner')
		user          = models.ForeignKey(User,null=True,blank=True, related_name='book_partner')
		customer      = models.ForeignKey(Customer,null=True,blank=True, related_name='book_partner')
		status        = models.CharField(max_length=2,
															choices=PARTNER_CHOICES,
															default=PENDING_UPAID)
class BookedPartnerThankyou(models.Model):
	email = models.CharField(max_length=888)
	modified_date = models.DateField(auto_now_add=True, blank=True)
	def __str__(self):
		return self.email

def update_reservation_code(sender, instance, created, **kwargs):
		if created:
				done = False
				while not done:
						try:
								code = str(uuid.uuid4())
								instance.reservation_code = code[:7]
								instance.save()
								done = True
						except IntegrityError:
								done = False


def update_booking_count(sender, instance, created, **kwargs):
		if instance.booked_for:
				user_profile = UserProfile.objects.get(user=instance.booked_for)
				user_profile.book_success_counter += 1
				user_profile.save()


def send_email_to_player(sender, instance, created, **kwargs):
		if instance.booked_for:
				subject = 'Booking confirmation'
				email = instance.booked_for.email
				message = 'You successfully book online at golfconnect24.com'
				send_email(subject, message, [email])


def send_notification_to_user(sender, instance, created, **kwargs):
		if instance.reservation_code:
				detail_en = 'You have booked a teetime with reservation code:' + instance.reservation_code
				detail = 'Bạn đã được đặt sân với mã code là ' + instance.reservation_code
				ctype = ContentType.objects.get_for_model(instance)
				Notice.objects.get_or_create(content_type=ctype,
																		 object_id=instance.id,
																		 to_user=instance.user,
																		 detail=detail,
																		 detail_en=detail_en,
																		 notice_type='B',
				)
				if instance.booked_for:
						if instance.booked_for_id != instance.user.id:
								detail = 'Bạn đã được đặt sân với mã code là ' + instance.reservation_code + 'bởi ' + instance.user.username
								detail_en = 'You have been booked a teetime with reservation code:' + instance.reservation_code + 'by ' + instance.user.username
								Notice.objects.get_or_create(content_type=ctype,
																						 object_id=instance.id,
																						 to_user=instance.booked_for,
																						 detail_en=detail_en,
																						 detail=detail,
																						 notice_type='B',
								)


# Connect create profile function to post_save signal of BookedBuggy model
post_save.connect(update_reservation_code, sender=BookedTeeTime)
# post_save.connect(update_booking_count, sender=BookedTeeTime)
# post_save.connect(send_notification_to_user, sender=BookedTeeTime)



def send_email_to_partners(sender, instance, created, **kwargs):
		if created:
				subject = 'Booking confirmation'
				email = instance.user.email
				message = 'You successfully book online at golfconnect24.com'
				send_email(subject, message, [email])


def send_notification_to_partner(sender, instance, created, **kwargs):
		if created:
				if instance.user:
						teetime = instance.teetime
						detail_en = 'You has been invited to play golf by ' + teetime.user.username
						detail = teetime.user.username + ' đã mời bạn chơi golf'
						ctype = ContentType.objects.get_for_model(teetime)
						Notice.objects.get_or_create(content_type=ctype,
																				 object_id=teetime.id,
																				 to_user=instance.user,
																				 from_user=teetime.user,
																				 detail=detail,
																				 detail_en=detail_en)



# Connect create profile function to post_save signal of BookedBuggy model
# post_save.connect(send_notification_to_partner, sender=BookedPartner)


class BookedClubset(models.Model):
		teetime = models.ForeignKey(BookedTeeTime, related_name='booked_clubset')
		clubset = models.ForeignKey(GolfCourseClubSets, related_name='booked_clubset')
		quantity = models.PositiveIntegerField()
		amount = models.DecimalField(default=0.0, max_digits=9, decimal_places=2)

		@staticmethod
		def __string__():
				return "Booked Clubsets"


def update_bookedclubsets_amount(sender, instance, created, **kwargs):
		if created:
				instance.amount = instance.clubset.price * instance.quantity
				instance.save()

# Connect create profile function to post_save signal of BookedClubsets model
post_save.connect(update_bookedclubsets_amount, sender=BookedClubset)


class BookedCaddy(models.Model):
		teetime = models.ForeignKey(BookedTeeTime, related_name='teetime_caddy', null=True)
		caddy = models.ForeignKey(GolfCourseCaddy, related_name='booked_caddy')
		amount = models.DecimalField(default=0.0, max_digits=9, decimal_places=2)
		quantity = models.PositiveIntegerField(default=0)
		@staticmethod
		def __string__():
				return "Booked Caddy"

class BookedBuggy(models.Model):
		teetime = models.ForeignKey(BookedTeeTime, related_name='teetime_buggy', null=True)
		buggy = models.ForeignKey(GolfCourseBuggy, related_name='booked_buggy')
		quantity = models.PositiveIntegerField()
		amount = models.DecimalField(default=0.0, max_digits=9, decimal_places=2)

		@staticmethod
		def __string__():
				return "Booked Buggy"

class BookedPayonlineLink(models.Model):
	custName = models.CharField(max_length=255)
	custAddress = models.CharField(max_length=255)
	custMail = models.CharField(max_length=255)
	custPhone = models.CharField(max_length=255)
	totalAmount = models.CharField(max_length=255)
	description = models.CharField(max_length=255, default="Please select your preferred card to pay")
	receiveEmail = models.CharField(max_length=255, default="thao.vuong@ludiino.com")
	paymentStatus = models.BooleanField(default=False, editable=False)
	paymentLink = models.CharField(max_length=255, null=True, blank=True, editable=False)

	def __str__(self):
		return self.custName + ' - ' + str(self.totalAmount) + ' - ' + str(self.paymentStatus)

	class Meta:
		ordering = ['-id']

def generate_email(sender, instance, created, **kwargs):
	if created:
		send_generate_email(instance)

post_save.connect(generate_email, sender=BookedPayonlineLink)

class BookedGolfcourseEvent(models.Model):
	member = models.ForeignKey(EventMember, related_name='booked_gc_event')
	discount = models.FloatField(default=0)
	total_cost  = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
	
	payment_type     = models.CharField(max_length=1,choices=PAYMENT_CHOICES,default=NOPAY)
	book_type       = models.CharField(max_length=1,choices=BOOK_CHOICES,default=ONLINE)
	payment_status = models.BooleanField(default=False)
	url         = models.URLField(null=True, blank=True)
	qr_image    = models.ImageField(upload_to="qr_codes/",null=True,blank=True,editable=False)
	qr_base64     = models.TextField(editable=False)
	qr_url      = models.URLField(null=True, blank=True)

	created              = models.DateTimeField(null=True, blank=True, editable=False)
	modified             = models.DateTimeField(null=True, blank=True)
	reservation_code     = models.TextField(editable=False, unique=True)
	status          = models.CharField(max_length=2,choices=STATUS_CHOICES,default=BOOKING_REQUEST)
	user_device = models.CharField(max_length=3, blank=True, null=True, default='web')
	def save(self, *args, **kwargs):
		if not self.id:
				self.created = datetime.datetime.today()
		if self.payment_status:
			self.status = PENDING_PAID
		elif not self.payment_status and self.payment_type == 'F':

			if self.status == 'C':
                ### handle status cancel
				self.status = CANCEL
			else:
				self.status = BOOKING_PROCESS

		else:
			self.status = BOOKING_REQUEST
		self.modified = datetime.datetime.today()
		return super(BookedGolfcourseEvent, self).save(*args, **kwargs)

	def __str__(self):
		return 'id: {}'.format(self.id)

class BookedGolfcourseEventDetail(models.Model):
	booked_event = models.ForeignKey(BookedGolfcourseEvent, related_name='booked_gc_event_detail')
	price_info = models.ForeignKey(GolfCourseEventPriceInfo, related_name='booked_gc_event_detail')
	quantity = models.PositiveIntegerField(default=0)
	price = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)

class BookedPartner_GolfcourseEvent(models.Model):
		bookedgolfcourse = models.ForeignKey(BookedGolfcourseEvent, related_name='book_partner_gcevent')
		customer      = models.ForeignKey(Customer,null=True,blank=True, related_name='book_partner_gcevent')
		# def __str__(self):
			# return self.bookedgolfcourse, self.customer

post_save.connect(update_reservation_code, sender=BookedGolfcourseEvent)


def calculate_price(request):
		total_amount = 0
		clubsets_amount = 0
		buggy_amount = 0
		caddy_amount = 0
		VAT = Decimal(float(total_amount) * 0.1)
		total_amount = round(total_amount + VAT, 2)
		return total_amount