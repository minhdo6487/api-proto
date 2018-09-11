import datetime

from core.golfcourse.models import GolfCourse
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Avg
from django.db.models.signals import post_save, pre_save
from django.db import IntegrityError
import uuid
# from core.teetime.models import TeeTimeSetting

CHECK_IN = 'I'
CANCEL = 'C'
PENDING_PAID = 'PP'
PENDING_UPAID = 'PU'
BOOKING_REQUEST = 'R'
STATUS_CHOICES = (
    (CHECK_IN, 'Check In'),
    (CANCEL, 'Cancel'),
    (BOOKING_REQUEST, 'Booking Request'),
    (PENDING_PAID, 'Pending paid'),
    (PENDING_UPAID, 'Pending unpaid'))

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
    (PENDING_UPAID, 'Pending unpaid'))


class Hotel(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    description_en = models.TextField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    website = models.CharField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=50, null=True, blank=True)
    star = models.IntegerField(default=3)
    golfcourse_distance = models.IntegerField(default=0)
    downtown_distance = models.IntegerField(default=0)
    airport_distance = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class HotelImages(models.Model):
    hotel = models.ForeignKey(Hotel, related_name='hotel_images', null=True, blank=True)
    url = models.TextField()

    def __str__(self):
        return self.hotel.name


class HotelRoom(models.Model):
    hotel = models.ForeignKey(Hotel, related_name='hotel_room', null=True, blank=True)
    max_person = models.IntegerField(default=2)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.hotel.name + '-' + self.name


class PackageGolfCourse(models.Model):
    golfcourse = models.ForeignKey(GolfCourse, related_name='package_golfcourse')
    round = models.IntegerField(default=1)
    hole = models.IntegerField(default=18)

    def __str__(self):
        return str(self.round) + ' round - ' + str(self.hole) + ' hole -' + self.golfcourse.name

class HotelGolfcourseDistance(models.Model):
    golfcourse = models.ForeignKey(GolfCourse, related_name='distance_golfcourse', null=True, blank=True)
    hotel = models.ForeignKey(Hotel, related_name='distance_hotel', null=True, blank=True)
    short_name = models.TextField(null=True, blank=True)
    distance = models.IntegerField(default=0)

    def __str__(self):
        return self.hotel.name + '-' + self.golfcourse.name
    def save(self, *args, **kwargs):
        self.short_name = self.golfcourse.short_name
        return super(HotelGolfcourseDistance, self).save(*args, **kwargs)
        
class Services(models.Model):
    name = models.CharField(max_length=50)
    small_icon = models.TextField(null=True, blank=True)
    large_icon = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class ParentPackageTour(models.Model):
    title = models.CharField(max_length=100)
    rating = models.FloatField(default=0)

    is_destination = models.BooleanField(default=False)
    register_count = models.PositiveIntegerField(default=0)
    thumbnail = models.TextField(null=True, blank=True)
    from_date = models.DateField(null=True, blank=True)
    to_date = models.DateField(null=True, blank=True)
    slug = models.CharField(max_length=100, null=True, blank=True)
    term_condition = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    display_price = models.DecimalField(default=0, max_digits=20, decimal_places=0)
    discount = models.FloatField(default=0)
    longitude = models.FloatField(null=True,blank=True)
    latitude = models.FloatField(null=True,blank=True)

    is_publish = models.BooleanField(default=True)
    date_created = models.DateTimeField(null=True, blank=True, editable=False)
    date_modified = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.date_created = datetime.datetime.today()
        self.date_modified = datetime.datetime.today()
        return super(ParentPackageTour, self).save(*args, **kwargs)

    def __str__(self):
        return '[{}] - {}'.format(str(self.id), self.title)

    class Meta:
        ordering = ('display_price',)

class PackageTour(models.Model):
    title = models.CharField(max_length=100)
    day = models.PositiveSmallIntegerField(default=1)
    no_round = models.PositiveSmallIntegerField(default=1)
    hole = models.PositiveIntegerField(default=18)
    is_destination = models.BooleanField(default=False)
    register_count = models.PositiveIntegerField(default=0)
    discount = models.FloatField(default=0)
    parent = models.ForeignKey(ParentPackageTour, related_name='package_tour', null=True, blank=True)
    date_created = models.DateTimeField(null=True, blank=True, editable=False)
    date_modified = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.date_created = datetime.datetime.today()
        self.date_modified = datetime.datetime.today()
        return super(PackageTour, self).save(*args, **kwargs)

    def __str__(self):
        return '[{}] - {}'.format(str(self.id), self.title)


class PackageTourServices(models.Model):
    package_tour = models.ForeignKey(PackageTour, related_name='services', null=True, blank=True)
    service = models.ForeignKey(Services, related_name='package_services', null=True, blank=True)
    is_free = models.BooleanField(default=False)

    class Meta:
        unique_together = ('service', 'package_tour')

    def __str__(self):
        return str(self.package_tour_id) + '-' + self.package_tour.title + '-' + self.service.name


class PackageTourFee(models.Model):
    package_tour = models.ForeignKey(PackageTour, related_name='fees', null=True, blank=True)
    name = models.CharField(max_length=50)
    display_price = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)

    def __str__(self):
        return str(self.package_tour_id) + '-' + self.name

    class Meta:
        ordering = ('display_price',)


class PackageAdditionalFee(models.Model):
    package_service = models.ForeignKey(PackageTourFee, related_name='package_additional', null=True, blank=True)
    service = models.ForeignKey(Services, related_name='package_additional', null=True, blank=True)
    price = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
    gc_price = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)

    def __str__(self):
        return str(self.package_service.package_tour_id) + '-' + self.package_service.name + '-' + self.service.name

    class Meta:
        unique_together = ('service', 'package_service')


class PackageHotelRoomFee(models.Model):
    hotel_room = models.ForeignKey(HotelRoom, related_name='package_hotel')
    package_service = models.ForeignKey(PackageTourFee, related_name='package_hotel', null=True, blank=True)
    price = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
    gc_price = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)

    def __str__(self):
        return str(self.package_service.package_tour_id) + '-' + self.package_service.name + '-' + str(
            self.hotel_room.name)

    class Meta:
        unique_together = ('hotel_room', 'package_service')
        ordering = ('price',)


class PackageGolfcourseFee(models.Model):
    package_golfcourse = models.ForeignKey(PackageGolfCourse, related_name='package_golfcourse', null=True, blank=True)
    package_service = models.ForeignKey(PackageTourFee, related_name='package_golfcourse', null=True, blank=True)
    price = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)  # price for hotel
    gc_price = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)

    def __str__(self):
        return str(self.package_service.package_tour_id) + '-' + self.package_service.name

    class Meta:
        unique_together = ('package_golfcourse', 'package_service')


class PackageTourDetail(models.Model):
    package_tour = models.ForeignKey(PackageTour, related_name='package_detail')
    html_homepage = models.TextField(null=True, blank=True)


class PackageTourSetting(models.Model):
    package_tour = models.ForeignKey(PackageTour, related_name='package_setting')
    date = models.DateTimeField(null=True, blank=True)
    max_register = models.PositiveIntegerField(default=0)


class PackageTourReview(models.Model):
    package_tour = models.ForeignKey(PackageTour, related_name='package_review')
    user = models.ForeignKey(User, blank=True, null=True, related_name='package_review')
    name = models.CharField(max_length=100, blank=True, null=True)
    rating = models.FloatField(default=5)
    comment = models.TextField(null=True, blank=True)
    title = models.CharField(max_length=100)
    date_created = models.DateTimeField(null=True, blank=True, editable=False)
    date_modified = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.date_created = datetime.datetime.today()
        self.date_modified = datetime.datetime.today()
        return super(PackageTourReview, self).save(*args, **kwargs)


class BookedPackageTour(models.Model):
    package_tour = models.ForeignKey(PackageTour, related_name='booked_package')
    user = models.ForeignKey(User, related_name='booked_package', null=True, blank=True)
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.CharField(max_length=100)
    total_cost = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
    discount = models.FloatField(default=0)
    paid_amount = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
    payment_type = models.CharField(max_length=1, choices=PAYMENT_CHOICES, default=NOPAY)
    payment_status = models.BooleanField(default=False)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default=BOOKING_REQUEST)
    voucher = models.CharField(max_length=50, blank=True, null=True)
    checkin_date = models.DateField()
    checkout_date = models.DateField()
    note = models.TextField(blank=True, null=True)
    qr_code = models.CharField(max_length=32, null=True, blank=True)
    qr_url = models.TextField(max_length=100, blank=True, null=True)
    reservation_code = models.TextField(editable=False, unique=True)
    quantity = models.PositiveIntegerField(default=1)
    currencyCode = models.CharField(max_length=20, blank=True, null=True, default='VND')
    currencyValue = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
    date_created = models.DateTimeField(null=True, blank=True, editable=False)
    date_modified = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.date_created = datetime.datetime.today()
        self.date_modified = datetime.datetime.today()
        self.discount = self.package_tour.discount
        return super(BookedPackageTour, self).save(*args, **kwargs)


class BookedPackageHotel(models.Model):
    booked_package = models.ForeignKey(BookedPackageTour, related_name='booked_hotel', null=True, blank=True)
    package_hotel_room = models.ForeignKey(PackageHotelRoomFee, related_name='booked_hotel')
    name = models.CharField(max_length=50, null=True, blank=True)
    price = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)


class BookedPackageGolfcourse(models.Model):
    booked_package = models.ForeignKey(BookedPackageTour, related_name='booked_golfcourse', null=True, blank=True)
    package_golfcourse = models.ForeignKey(PackageGolfcourseFee, related_name='booked_golfcourse')
    name = models.CharField(max_length=50, null=True, blank=True)
    price = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    no_round = models.PositiveIntegerField(default=1)


class BookedPackageAdditional(models.Model):
    booked_package = models.ForeignKey(BookedPackageTour, related_name='booked_additional', null=True, blank=True)
    package_additional = models.ForeignKey(PackageAdditionalFee, related_name='booked_additional')
    name = models.CharField(max_length=50, null=True, blank=True)
    price = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)


def compute_rating(sender, instance, created, **kwargs):
    query = PackageTourReview.objects.filter(package_tour__parent=instance.package_tour.parent).aggregate(Avg('rating'))
    avg_rating = 0
    if query['rating__avg']:
        avg_rating = round(query['rating__avg'], 1)
    instance.package_tour.parent.rating = avg_rating
    instance.package_tour.parent.save(update_fields=['rating'])


post_save.connect(compute_rating, sender=PackageTourReview)


def add_register_count(sender, instance, created, **kwargs):
    if created:
        instance.package_tour.register_count += 1
        instance.package_tour.save(update_fields=['register_count'])
        instance.package_tour.parent.register_count += 1
        instance.package_tour.parent.save(update_fields=['register_count'])

        done = False
        while not done:
            try:
                code = str(uuid.uuid4())
                instance.reservation_code = code[:7]
                instance.save()
                done = True
            except IntegrityError:
                done = False


post_save.connect(add_register_count, sender=BookedPackageTour)

def calculate_total_stay(sender, instance, created, **kwargs):
    if created:
        instance.price = instance.package_hotel_room.price * instance.quantity
        instance.name = instance.package_hotel_room.hotel_room.hotel.name
        instance.save(update_fields=['price','name'])

post_save.connect(calculate_total_stay, sender=BookedPackageHotel)

def calculate_total_play(sender, instance, created, **kwargs):
    if created:
        instance.price = instance.package_golfcourse.price * instance.quantity * instance.no_round
        instance.save(update_fields=['price'])
post_save.connect(calculate_total_play, sender=BookedPackageGolfcourse)

def display_total_play(sender, instance, created, **kwargs):
    price_play = sum(item.price for item in instance.package_service.package_golfcourse.all())
    price_stay = instance.package_service.package_hotel.all().first().price if instance.package_service.package_hotel.all().first() else 0
    price_stay *= (len(instance.package_service.package_golfcourse.all()) - 1) or 1
    display_price = price_play + price_stay
    instance.package_service.display_price = display_price
    instance.package_service.save(update_fields=['display_price'])
        
post_save.connect(display_total_play, sender=PackageGolfcourseFee)

def display_total_stay(sender, instance, created, **kwargs):
    price_stay = instance.price
    price_play = sum(item.price for item in instance.package_service.package_golfcourse.all())
    price_stay *= (len(instance.package_service.package_golfcourse.all()) - 1) or 1
    display_price = price_play + price_stay
    instance.package_service.display_price = display_price
    instance.package_service.save(update_fields=['display_price'])
post_save.connect(display_total_stay, sender=PackageHotelRoomFee)

def calculate_total_fee(sender, instance, created, **kwargs):
    display_price_list = []
    for item in instance.package_tour.parent.package_tour.all():
        display_price_list += item.fees.all().values_list('display_price',flat=True)
    instance.package_tour.parent.display_price = min(display_price_list)
    instance.package_tour.parent.save(update_fields=['display_price'])
post_save.connect(calculate_total_fee, sender=PackageTourFee)

