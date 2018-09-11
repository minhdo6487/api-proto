import datetime

import base64
import pyqrcode
from api.teetimeMana.views import fn_getHostname
from core.playstay.models import PackageTour, Hotel, PackageTourReview, BookedPackageTour, PackageGolfcourseFee, \
    PackageHotelRoomFee, PackageAdditionalFee, ParentPackageTour
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from rest_framework import mixins
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from .serializers import PackageTourSerializer, ParentPackageTourListSerializer, ParentPackageTourDetailSerializer, PaginatedPackageTourSerializer, HotelSerializer, \
    PackageTourReviewSerializer, PaginatedPackageReviewSerializer, BookedPackageTourSerializer
from .tasks import playstay_request_booking_email

class ParentPackageTourViewSet(mixins.RetrieveModelMixin,
                         mixins.ListModelMixin,
                         GenericViewSet):

    queryset = ParentPackageTour.objects.all()
    serializer_class = ParentPackageTourListSerializer
    permission_classes = (AllowAny,)
    parser_classes = (JSONParser, FormParser,)

    def retrieve(self, request, pk):
        query = ParentPackageTour.objects.filter(pk=pk).first()
        if not query:
            return Response({'status': '404', 'detail': 'Not found'}, status=404)
        serializer = ParentPackageTourDetailSerializer(query)

        return Response(serializer.data, status=200)

    def list(self, request, *args, **kwargs):
        filter_query = dict()

        is_destination = request.QUERY_PARAMS.get('destination', False)
        filter_query['is_destination'] = bool(int(is_destination))

        query = ParentPackageTour.objects.filter(**filter_query)

        item = request.GET.get('item', 10)
        paginator = Paginator(query, item)
        page = request.QUERY_PARAMS.get('page')
        try:
            package_tour = paginator.page(page)
        except PageNotAnInteger:
            package_tour = paginator.page(1)
        except EmptyPage:
            package_tour = paginator.page(paginator.num_pages)
        serializer = PaginatedPackageTourSerializer(instance=package_tour)

        return Response(serializer.data, status=200)
class PackageTourViewSet(mixins.RetrieveModelMixin,
                         mixins.ListModelMixin,
                         GenericViewSet):
    """ Viewset handle for requesting course information
    """
    queryset = PackageTour.objects.all()
    serializer_class = PackageTourSerializer
    permission_classes = (AllowAny,)
    parser_classes = (JSONParser, FormParser,)

class HotelViewSet(viewsets.ModelViewSet):
    """ Viewset handle for requesting course information
    """
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer
    permission_classes = (AllowAny,)
    parser_classes = (JSONParser, FormParser,)


class PackageTourReviewViewSet(mixins.DestroyModelMixin,
                               mixins.CreateModelMixin,
                               mixins.UpdateModelMixin,
                               GenericViewSet):
    """ Viewset handle for requesting course information
    """
    queryset = PackageTourReview.objects.all()
    serializer_class = PackageTourReviewSerializer
    permission_classes = (AllowAny,)
    parser_classes = (JSONParser, FormParser,)

    def create(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            request.DATA['user'] = request.user.id
        return super().create(request, *args, **kwargs)


@api_view(['GET'])
def get_package_tour_review(request, pk):
    query = PackageTourReview.objects.filter(package_tour__parent=pk)
    item = request.GET.get('item', 10)
    paginator = Paginator(query, item)
    page = request.QUERY_PARAMS.get('page')
    try:
        package_review = paginator.page(page)
    except PageNotAnInteger:
        package_review = paginator.page(1)
    except EmptyPage:
        package_review = paginator.page(paginator.num_pages)
    serializer = PaginatedPackageReviewSerializer(instance=package_review)

    return Response(serializer.data, status=200)


## Booked
class BookedPackageViewSet(mixins.CreateModelMixin,
                           mixins.RetrieveModelMixin,
                           GenericViewSet):
    queryset = BookedPackageTour.objects.all()
    serializer_class = BookedPackageTourSerializer
    permission_classes = (AllowAny,)
    parser_classes = (JSONParser, FormParser,)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.DATA)

        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)
        total_cost = compute_total_cost(request.DATA)
        if total_cost != serializer.data['total_cost']:
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': 'Total cost mismatch'}, status=400)
        item = serializer.save()

        # Generate qr code
        qr_url, qr_code = generate_qr_code(fn_getHostname(request), item.id)
        item.qr_url = qr_url
        item.qr_code = qr_code
        item.save()
        playstay_request_booking_email.delay(item.id)
        return Response(serializer.data, status=200)

    def retrieve(self, request, pk=None):
        item = BookedPackageTour.objects.filter(qr_code=pk).first()
        if not item:
            return Response({'status': '404', 'detail': 'Not found'}, status=404)

        serializer = BookedPackageTourSerializer(item)
        return Response(serializer.data, status=200)
def compute_total_cost(data):
    total_cost = 0
    package_tour = PackageTour.objects.filter(id=data['package_tour']).first()
    #no_night = 1 if len(data['golfcourses']) == 1 else int(data.get('quantity',1))
    no_night = int(data.get('quantity',1))
    for item in data['golfcourses']:
        query = PackageGolfcourseFee.objects.filter(id=item['package_golfcourse']).first()
        total_cost += int(query.price) * int(item.get('quantity', 1)) * int(item.get('no_round', 1))
    for item in data['hotels']:
        query = PackageHotelRoomFee.objects.filter(id=item['package_hotel_room']).first()
        total_cost += int(query.price) * int(item.get('quantity', 1)) * no_night
    for item in data['additionals']:
        query = PackageAdditionalFee.objects.filter(id=item['package_additional']).first()
        total_cost += int(query.price) * int(item.get('quantity', 1))
    #total_cost *= int(data.get('quantity',1)) if len(data['golfcourses']) == 1 else 1
    total_cost *= (1 - (package_tour.discount / 100))
    return total_cost


def generate_qr_code(domain, book_id):
    qr_code = base64.urlsafe_b64encode(str(book_id).encode('ascii')).decode('ascii')
    uri = 'https://{}/#/package-tour-book/{}'.format(domain, qr_code)
    url = pyqrcode.create(uri)
    filename = 'media/qr_codes/{}.png'.format(qr_code)
    url.png(filename, scale=6)
    qr_url = 'https://{}/api/media/qr_codes/{}.png'.format(domain, qr_code)
    return qr_url, qr_code