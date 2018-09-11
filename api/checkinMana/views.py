from django.contrib.contenttypes.models import ContentType
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from rest_framework.response import Response

from core.checkin.models import Checkin
from api.checkinMana.serializers import CheckinSerializer, MultiCheckinSerializer
from utils.rest.viewsets import NotDeleteViewSet
from utils.django.models import get_or_none
from core.customer.models import Customer
from core.booking.models import BookedTeeTime, BookedPartner
from utils.rest.code import code


class CheckinViewSet(NotDeleteViewSet):
    """ Viewset handle for requesting course information
    """
    queryset = Checkin.objects.all()
    serializer_class = CheckinSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, FormParser,)
    filter_fields = ('reservation_code',)

    def create(self, request, *args, **kwargs):
        serializer = MultiCheckinSerializer(data=request.DATA)
        valid = serializer.is_valid()
        if not valid:
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)

        i = 0
        players = serializer.data['players']
        player_info = request.DATA['players']
        subgolfcourse = request.DATA['subgolfcourse']
        reservation_code = request.DATA['reservation_code']

        if reservation_code != '':
            booked_teetime = BookedTeeTime.objects.get(reservation_code=reservation_code)
            booked_teetime.status = 'I'
            booked_teetime.save()
            Checkin.objects.filter(reservation_code=reservation_code).delete()

        for player in players:
            name = player_info[i]['name']
            email = player_info[i]['email']
            phone = player_info[i]['phone']
            player_number = player_info[i]['player_number']
            if name == '' and email == '' and phone == '':
                return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                 'detail': 'You must fill at least name or email or phone'}, status=400)
            total_amount = player['total_amount']
            date = player['date']
            time = player['time']
            golfcourse = player['golfcourse']
            player = get_or_none(User, username=email)
            if reservation_code == '':
                if i == 0:
                    is_booked = get_or_none(BookedTeeTime, subgolfcourse=subgolfcourse, golfcourse=golfcourse,
                                            date_to_play=date, time_to_play=time)
                    if is_booked:
                        return Response({'status': '400', 'code': 'E_ALREADY_EXIST',
                                         'detail': code['E_ALREADY_EXIST']}, status=400)
                    if player:
                        teetime = BookedTeeTime.objects.create(golfcourse_id=golfcourse,
                                                               subgolfcourse_id=subgolfcourse,
                                                               time_to_play=time, date_to_play=date, status='I',
                                                               payment_type='F',
                                                               book_type='W', player_count=len(players),
                                                               user=request.user, booked_for=player)
                    else:
                        customer = Customer.objects.create(name=name, email=email, phone_number=phone,
                                                           golfcourse_id=golfcourse)
                        teetime = BookedTeeTime.objects.create(golfcourse_id=golfcourse,
                                                               subgolfcourse_id=subgolfcourse,
                                                               time_to_play=time, date_to_play=date, status='I',
                                                               payment_type='F',
                                                               book_type='W', player_count=len(players),
                                                               user=request.user, booked_for_customer=customer)
                    reservation_code = teetime.reservation_code
                else:
                    if player:
                        BookedPartner.objects.create(teetime=teetime, user=player, status='S')

            if player:
                ctype = ContentType.objects.get_for_model(player)
            else:
                player = Customer.objects.create(name=name, golfcourse_id=golfcourse, email=email, phone_number=phone)
                ctype = ContentType.objects.get_for_model(player)

            Checkin.objects.get_or_create(content_type=ctype,
                                          object_id=player.id,
                                          total_amount=total_amount,
                                          date=date,
                                          time=time,
                                          golfcourse_id=golfcourse,
                                          reservation_code=reservation_code,
                                          play_number=player_number)
            i += 1
        return Response({'status': '200', 'code': 'OK',
                         'detail': 'OK'}, status=200)
