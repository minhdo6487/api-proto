import itertools

from api.golfcourseMana.serializers import PlayStayGolfCourseSerializer
from rest_framework import serializers

from core.playstay.models import PackageTour, PackageTourServices, PackageTourFee, PackageGolfcourseFee, \
    PackageHotelRoomFee, Hotel, HotelRoom, Services, HotelImages, PackageTourReview, BookedPackageTour, \
    PackageAdditionalFee, BookedPackageHotel, BookedPackageGolfcourse, BookedPackageAdditional, PackageGolfCourse, \
    ParentPackageTour, HotelGolfcourseDistance
from core.golfcourse.models import GolfCourse
from rest_framework.pagination import PaginationSerializer


class HotelRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelRoom


class HotelImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelImages

class HotelGolfcourseDistanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelGolfcourseDistance

class HotelSerializer(serializers.ModelSerializer):
    rooms = HotelRoomSerializer(many=True, source='hotel_room', allow_add_remove=True)
    images = HotelImagesSerializer(many=True, source='hotel_images', read_only=True)

    class Meta:
        model = Hotel


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Services


class PackageGolfCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageGolfCourse


class PackageTourServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageTourServices

    def to_native(self, obj):
        serializers = super(PackageTourServiceSerializer, self).to_native(obj)
        serializers.update({'service_info': ServiceSerializer(obj.service).data})
        del serializers['service']
        del serializers['package_tour']
        return serializers


class PackageHotelRoomFeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageHotelRoomFee
        order_by = ('price',)

    def to_native(self, obj):
        serializers = super(PackageHotelRoomFeeSerializer, self).to_native(obj)
        room_info = HotelRoomSerializer(obj.hotel_room)
        serializers['price'] = int(serializers['price'])
        del room_info.data['id']
        del serializers['package_service']
        del serializers['gc_price']
        serializers.update({'room_info': room_info.data, 'upgrades': []})

        return serializers


class PackageGolfcourseFeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageGolfcourseFee

    def to_native(self, obj):
        if obj is not None:
            serializers = super(PackageGolfcourseFeeSerializer, self).to_native(obj)
            serializers.update({'golfcourse_info': PlayStayGolfCourseSerializer(obj.package_golfcourse.golfcourse).data,
                                'package_golfcourse_info': PackageGolfCourseSerializer(obj.package_golfcourse).data})
            serializers['price'] = int(serializers['price'])
            del serializers['package_service']
            del serializers['gc_price']
            return serializers


class PackageAdditionalFeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageAdditionalFee

    def to_native(self, obj):
        serializers = super(PackageAdditionalFeeSerializer, self).to_native(obj)
        service = ServiceSerializer(obj.service)
        serializers.update({'service_info': service.data})
        serializers['price'] = int(serializers['price'])
        del serializers['gc_price']
        del serializers['package_service']
        return serializers


class PackageTourFeeSerializer(serializers.ModelSerializer):
    golfcourses = PackageGolfcourseFeeSerializer(many=True, source='package_golfcourse', allow_add_remove=True)
    hotel_rooms = PackageHotelRoomFeeSerializer(many=True, source='package_hotel', allow_add_remove=True)
    additionals = PackageAdditionalFeeSerializer(many=True, source='package_additional', allow_add_remove=True)

    class Meta:
        model = PackageTourFee

    def to_native(self, obj):
        serializers = super(PackageTourFeeSerializer, self).to_native(obj)
        hotel_info = dict()
        if serializers.get('hotel_rooms'):
            hotel = Hotel.objects.filter(id=serializers['hotel_rooms'][0]['room_info']['hotel']).first()
            hotel_info = HotelSerializer(hotel).data
            hotel_info.update({'price': serializers['hotel_rooms'][0]['price']})
            golfcourse_id = []
            for item in obj.package_golfcourse.all():
                golfcourse_id.append(item.package_golfcourse.golfcourse.id)
            hotel_distance = HotelGolfcourseDistance.objects.filter(hotel=hotel,golfcourse__in=golfcourse_id)
            distances = HotelGolfcourseDistanceSerializer(hotel_distance).data
            hotel_info.update({'distances':distances})
            rooms = dict()
            for i, item in enumerate(serializers['hotel_rooms']):
                room_type = item['room_info']['name'].split()[0]
                if room_type not in rooms:
                    rooms.update({room_type: [item]})
                else:
                    rooms[room_type].append(item)
            hotel_rooms = []
            for k in rooms:
                item = rooms[k][0].copy()
                item['upgrades'] = rooms[k]
                hotel_rooms.append(item)
            serializers['hotel_rooms'] = hotel_rooms
        serializers.update({'hotel': hotel_info})
        return serializers


class PackageTourSerializer(serializers.ModelSerializer):
    services = PackageTourServiceSerializer(many=True, source='services', allow_add_remove=True)
    fees = PackageTourFeeSerializer(many=True, source='fees', allow_add_remove=True)

    class Meta:
        model = PackageTour

    def to_native(self, obj):
        serializers = super(PackageTourSerializer, self).to_native(obj)
        serializers.update({'night': obj.day - 1})
        serializers['fees'] = sorted(serializers['fees'], key=lambda x: sum(int(item['price']) for item in x['golfcourses']) + min(int(item['price']) for item in x['hotel_rooms']))
        return serializers


class ParentPackageTourListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentPackageTour

    def to_native(self, obj):
        if obj is not None:
            serializers = super(ParentPackageTourListSerializer, self).to_native(obj)
            package_tour = obj.package_tour.first()
            package_fee_ids = [item.id for item in package_tour.fees.all()]
            package_gc_ids = [item.package_golfcourse.id for item in
                              PackageGolfcourseFee.objects.filter(package_service_id__in=package_fee_ids)]
            pk_golfcourse = PackageGolfCourse.objects.filter(id__in=package_gc_ids).order_by(
                'golfcourse_id').distinct('golfcourse_id')
            golfcourses = [{'round': item.round,
                            'hole': item.hole,
                            'golfcourse': item.golfcourse.name,
                            'longitude': item.golfcourse.longitude,
                            'latitude': item.golfcourse.latitude
                            } for item in pk_golfcourse]
            no_round = sum([item.round for item in pk_golfcourse])
            no_hole = max([item.hole for item in pk_golfcourse])
            serializers.update({'golfcourses':golfcourses, 'round': no_round, 'hole': no_hole})
            return serializers


class ParentPackageTourDetailSerializer(serializers.ModelSerializer):
    package_tours = PackageTourSerializer(many=True, source='package_tour', allow_add_remove=True)

    class Meta:
        model = ParentPackageTour

    def to_native(self, obj):
        serializers = super(ParentPackageTourDetailSerializer, self).to_native(obj)

        rating_count = PackageTourReview.objects.filter(package_tour__parent=obj).count()
        serializers.update({'rating_count': rating_count})
        if len(serializers['package_tours']) > 1:
            serializers.update({'single_package': False})
        else:
            serializers.update({'single_package': True})
        return serializers


class PackageTourReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageTourReview

    def to_native(self, obj):
        serializers = super(PackageTourReviewSerializer, self).to_native(obj)
        name = serializers['name']
        pic = None
        if obj.user:
            name = obj.user.user_profile.display_name
            pic = obj.user.user_profile.profile_picture
        serializers.update({'name': name, 'pic': pic})
        return serializers


class PaginatedPackageReviewSerializer(PaginationSerializer):
    class Meta:
        object_serializer_class = PackageTourReviewSerializer


class PaginatedPackageTourSerializer(PaginationSerializer):
    class Meta:
        object_serializer_class = ParentPackageTourListSerializer


## Booked
class BookedPackageHotelSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookedPackageHotel

    def to_native(self, obj):
        serializers = super(BookedPackageHotelSerializer, self).to_native(obj)
        pk_golfcourse = PackageHotelRoomFeeSerializer(obj.package_hotel_room).data
        # del pk_golfcourse['golfcourse_info']
        serializers.update({'info': pk_golfcourse})
        return serializers


class BookedPackageGolfcourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookedPackageGolfcourse

    def to_native(self, obj):
        serializers = super(BookedPackageGolfcourseSerializer, self).to_native(obj)
        pk_golfcourse = PackageGolfcourseFeeSerializer(obj.package_golfcourse).data
        pk_golfcourse['golfcourse_info']
        serializers.update({'info': pk_golfcourse})
        return serializers


class BookedPackageAdditionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookedPackageAdditional


class BookedPackageTourSerializer(serializers.ModelSerializer):
    golfcourses = BookedPackageGolfcourseSerializer(many=True, source='booked_golfcourse', allow_add_remove=True)
    hotels = BookedPackageHotelSerializer(many=True, source='booked_hotel', allow_add_remove=True)
    additionals = BookedPackageAdditionalSerializer(many=True, source='booked_additional', allow_add_remove=True)

    class Meta:
        model = BookedPackageTour
