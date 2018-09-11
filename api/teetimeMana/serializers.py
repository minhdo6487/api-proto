import logging
from rest_framework import serializers
from core.booking.models import BookedTeeTime
from core.teetime.models import GCSetting, TeeTime, TeeTimePrice, GuestType, PriceType, PriceMatrix, PriceMatrixLog, Holiday, RecurringTeetime
from utils.django.models import get_or_none
import datetime, time
from django.utils.timezone import utc, pytz
from pytz import timezone, country_timezones
from core.teetime.models import TeeTime, TeeTimePrice, GuestType, BookingTime, DealEffective_TeeTime
class RecurringTeetimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringTeetime

class TeeTimePriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeeTimePrice

    def to_native(self, obj):
        if obj:
            logging.error(obj)
            serializers = super(TeeTimePriceSerializer, self).to_native(obj)
            return serializers


class TeeTimeManagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeeTime
        exclude = ('created', 'modified')
    def to_native(self, obj):
        if obj:
            serializers = super(TeeTimeManagementSerializer, self).to_native(obj)
            gtype = GuestType.objects.get(name = 'G')
            price = get_or_none(TeeTimePrice, teetime_id = serializers['id'], guest_type_id = gtype.id, hole = 18)
            price_9 = get_or_none(TeeTimePrice, teetime_id = serializers['id'],
                                                guest_type_id = gtype.id,
                                                hole = 9)
            price_27 = get_or_none(TeeTimePrice,teetime_id = serializers['id'],
                                                guest_type_id = gtype.id,
                                                hole = 27)
            price_36 = get_or_none(TeeTimePrice,teetime_id = serializers['id'],
                                                guest_type_id = gtype.id,
                                                hole = 36)
            if price:
                serializers['price'] = price.price
                serializers['price_18'] = price.price
                serializers['GC24_hole_18'] = price.price_standard
            else:
                serializers['price'] = 0
                serializers['price_18'] = 0
                serializers['GC24_hole_18'] = 0

            if price_9:
                serializers['price_9'] = price_9.price
                serializers['GC24_hole_9'] = price_9.price_standard
            else:
                serializers['price_9'] = 0
                serializers['GC24_hole_9'] = 0

            if price_27:
                serializers['price_27'] = price_27.price
                serializers['GC24_hole_27'] = price_27.price_standard
            else:
                serializers['price_27'] = 0
                serializers['GC24_hole_27'] = 0

            if price_36:
                serializers['price_36'] = price_36.price
                serializers['GC24_hole_36'] = price_36.price_standard
            else:
                serializers['price_36'] = 0
                serializers['GC24_hole_36'] = 0
            serializers['cash_discount']   = price.cash_discount if price else 0
            serializers['online_discount'] = price.online_discount if price else 0
            serializers['gifts']           = price.gifts if price else ''
            serializers['food_voucher']    = price.food_voucher if price else False
            serializers['buggy']           = price.buggy if price else False
            serializers['caddy']           = price.caddy if price else False

            serializers['status']          = 1
            if serializers['is_block'] == True:
                                            serializers['status'] = 2
            elif serializers['is_booked'] == True:
                                            serializers['status'] = 3
                                            booked = get_or_none(BookedTeeTime, teetime=obj)
                                            if not booked:
                                                obj.is_booked = False
                                                obj.save()
                                                serializers['status'] = 1
                                                serializers['is_booked'] = False
                                            elif booked.payment_type == 'F' and not booked.payment_status:
                                                serializers['status'] = 4
            elif serializers['is_request'] == True:
                                            serializers['status'] = 4              
            elif price and price.is_publish == False:
                                            serializers['status'] = 0
            ts = time.mktime(serializers['date'].timetuple()) * 1000
            serializers['teetime_date'] = serializers['date']
            serializers['date'] = ts
            serializers['time'] = datetime.timedelta(hours=serializers['time'].hour,minutes=serializers['time'].minute).total_seconds() * 1000
            serializers['golfcourse_name'] = obj.golfcourse.name
            if self.context.get('is_admin', False):
                tz = timezone(country_timezones(obj.golfcourse.country.short_name)[0])
                now = datetime.datetime.fromtimestamp(datetime.datetime.utcnow().timestamp(), tz)
                deal_teetime = DealEffective_TeeTime.objects.filter(teetime__id=obj.id, bookingtime__date=now.date(), bookingtime__deal__active=True).order_by('-modified')
                for dtt in deal_teetime:
                    if dtt.bookingtime.from_time <= now.time() <= dtt.bookingtime.to_time:
                        if (now.date() == dtt.bookingtime.deal.effective_date and dtt.bookingtime.deal.effective_time <= now.time()) or \
                            (now.date() == dtt.bookingtime.deal.expire_date and now.time() <= dtt.bookingtime.deal.expire_time) or \
                            (now.date() != dtt.bookingtime.deal.effective_date and now.date() != dtt.bookingtime.deal.expire_date):
                            serializers['online_discount'] = dtt.discount
                            break
            return serializers


class TeeTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeeTime
        exclude = ('created', 'modified', 'golfcourse', 'max_player')

    def to_native(self, obj):
        if obj:
            serializers = super(TeeTimeSerializer, self).to_native(obj)
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
            
            return serializers
# class MultiTeeTimeSettingSerializer(serializers.Serializer):
#     teetime_setting = TeeTimeSettingSerializer(many=True)


class GuestTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = GuestType

    def to_native(self, obj):
        if obj:
            serializers = super(GuestTypeSerializer, self).to_native(obj)
            # del serializers['golfcourse']
            return serializers


class GCSettingSerializer(serializers.ModelSerializer):

    class Meta:
        model = GCSetting

    def to_native(self, obj):
        if obj:
            serializers = super(GCSettingSerializer, self).to_native(obj)
            return serializers


class PriceTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = PriceType

    def to_native(self, obj):
        if obj:
            serializers = super(PriceTypeSerializer, self).to_native(obj)
            # del serializers['golfcourse']
            return serializers


class PriceMatrixSerializer(serializers.ModelSerializer):

    class Meta:
        model = PriceMatrix

    def to_native(self, obj):
        if obj:
            serializers = super(PriceMatrixSerializer, self).to_native(obj)
            del serializers['matrix_log']
            return serializers


class PriceMatrixLogSerializer(serializers.ModelSerializer):
    # matrix = PriceMatrixSerializer(many=True,source='price_matrix')

    class Meta:
        model = PriceMatrixLog
        # exclude = ('date_modified', 'date_created',)

    def to_native(self, obj):
        if obj:
            serializers = super(PriceMatrixLogSerializer, self).to_native(obj)
            # serializers.update({'date_modified':obj.date_modified})
            # del serializers['golfcourse']
            # del serializers['matrix']
            return serializers


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday


class ArchivedTeetimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeeTime
        exclude = ('created', 'modified', 'golfcourse', 'max_player','hold_expire')
    def to_native(self, obj):
        if obj:
            if obj.is_hold and obj.hold_expire < datetime.datetime.utcnow().replace(tzinfo=utc):
                obj.is_hold = False
                obj.hold_expire = None
                obj.save()
            serializers = super(ArchivedTeetimeSerializer, self).to_native(obj)
            city = ''
            if obj.golfcourse.city:
                city = obj.golfcourse.city.name
            country = ''
            if obj.golfcourse.country:
                country = obj.golfcourse.country.name
            serializers.update({
                'teetime_id': obj.id,
                'golfcourse_id': obj.golfcourse.id,
                'golfcourse_name': obj.golfcourse.name or "",
                'golfcourse_short_name': obj.golfcourse.short_name or "",
                'golfcourse_address': obj.golfcourse.address or "",
                'golfcourse_country': country or "",
                'golfcourse_website':obj.golfcourse.website or "",
                'golfcourse_contact':obj.golfcourse.contact_info or ""
            })
            gtype = GuestType.objects.get(name='G')
            price = TeeTimePrice.objects.filter(teetime_id = obj.id, guest_type_id = gtype.id)
            ## Check Caddy will be show or not

            serializers['price'] = serializers['price_9'] = serializers['price_18'] = serializers['price_27'] = serializers['price_36'] = 0
            for p in price:
                if p.hole == 18:
                    serializers['price'] = serializers['price_18'] = p.price
                    serializers['discount'] = p.online_discount
                    serializers['discount_online'] = p.cash_discount
                    serializers['gifts'] = p.gifts or ""
                    serializers['food_voucher'] = p.food_voucher
                    serializers['buggy'] = p.buggy
                    serializers['caddy'] = p.caddy
                    serializers['rank'] = 0
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