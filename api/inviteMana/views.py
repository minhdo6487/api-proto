from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from fuzzywuzzy import fuzz
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.views import APIView
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework import viewsets

from api.userMana.tasks import log_activity
from core.customer.models import Customer
from core.game.models import EventMember
from core.golfcourse.models import GolfCourseEvent, GolfCourse
from core.notice.models import Notice
from .serializers import InvitationSerializer, InvitedPeopleSerialier

# from core.invitation.models import Invitation, InvitedPeople
from core.booking.models import BookedTeeTime, BookedPartner
from utils.django.models import get_or_none
from utils.rest.viewsets import GetAndUpdateViewSet

# from utils.rest.sendemail import send_email, send_notification
from GolfConnect.settings import CURRENT_ENV
from api.noticeMana.tasks import send_email, send_notification

# from utils.rest.permissions import encrypt_val

DOW = {
    'Monday': 'Thứ Hai',
    'Tuesday': 'Thứ Ba',
    'Wednesday': 'Thứ Tư',
    'Thursday': 'Thứ Năm',
    'Friday': 'Thứ Sáu',
    'Saturday': 'Thứ Bảy',
    'Sunday': 'Chủ Nhật',
}


class InvitedPeopleViewSet(GetAndUpdateViewSet):
    queryset = EventMember.objects.all()
    serializer_class = InvitedPeopleSerialier
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser,)

    def partial_update(self, request, pk):
        serializer = self.serializer_class(data=request.DATA)
        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)
        super(InvitedPeopleViewSet, self).partial_update(request, pk)
        player = EventMember.objects.get(id=pk)
        invitation = player.event
        ctype = ContentType.objects.get_for_model(invitation)
        notice = get_or_none(Notice, content_type=ctype,
                             object_id=invitation.id,
                             to_user_id=player.player,
                             notice_type='IC',
                             from_user=invitation.user)
        if notice is not None:
            notice.notice_type = 'I'
            notice.is_show = False
            notice.is_read = False
            notice.save()
            return Response({'status': '200', 'code': 'OK',
                             'detail': 'OK'}, status=200)

        return Response({'status': '404', 'code': 'E_NOT_FOUND',
                         'detail': 'Not found notice'}, status=404)


class InvitationViewSet(viewsets.ModelViewSet):
    queryset = GolfCourseEvent.objects.all()
    serializer_class = InvitationSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, FormParser,)

    def create(self, request, *args, **kwargs):
        if 'data' in request.DATA:
            request.DATA['data']['user'] = request.user.id
            data = request.DATA['data']
            players = request.DATA['data']['invite_people']
        else:
            request.DATA['user'] = request.user.id
            data = request.DATA
            players = request.DATA['invite_people']

        golfcourse_names = list(GolfCourse.objects.all().values('id', 'name'))

        try:
            int(data['golfcourse'])
        except ValueError:
            golfcourse_id = None
            for g in golfcourse_names:
                if fuzz.token_set_ratio(data['golfcourse'], g['name']) > 90:
                    golfcourse_id = g['id']
                    data['golfcourse'] = golfcourse_id
                    break
            if not golfcourse_id:
                return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                 'detail': 'Invalid GolfCourse'}, status=400)

        for player in players:
            email = player.get('email')
            phone = player.get('phone')
            user_id = player.get('user_id')
            if not any([email, phone, user_id]):
                return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                 'detail': 'You must fill at least email or phone'}, status=400)
            if email == request.user.username or user_id == request.user.id:
                    return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                     'detail': 'Cannot invite myself'}, status=400)

        data.update({'date_start': data['date'],
                     'date_end': data['date']})
        serializer = self.serializer_class(data=data)
        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)
        invitation = serializer.save()
        event_ctype = ContentType.objects.get_for_model(GolfCourseEvent)
        log_activity(request.user.id, 'create_event', invitation.id, event_ctype.id)
        if players:

            # ----- Message for gc24 notification ------
            detail = '<a href=/#/profile/' + str(request.user.id) + '/></a> mời bạn tham gia sự kiện tại <b>' + str(
                invitation.golfcourse.name) + '</b>'
            if invitation.time:
                detail += ' lúc <b>' + str(invitation.time.strftime('%H:%M')) + '</b>'
            detail += ' vào <b>' + DOW[str(invitation.date_start.strftime('%A'))] + ', ' + str(
                invitation.date_start.strftime('%d-%m-%Y')) + '</b>'

            detail_en = '<a href=/#/profile/' + str(request.user.id) + '/></a> invited you to join the event at <b>' + str(
                invitation.golfcourse.name) + '</b>'
            if invitation.time:
                detail_en += ' at <b>' + str(invitation.time.strftime('%H:%M')) + '</b>'
            detail_en += ' on <b>' + str(invitation.date_start.strftime('%A')) + ', ' + str(
                invitation.date_start.strftime('%d-%m-%Y')) + '</b>'

            # ----- Message for push notification ------
            detail_notify_en = str(request.user.user_profile.display_name) + ' invited you to join the event at ' + str(
                invitation.golfcourse.name)
            if invitation.time:
                detail_notify_en += ' at ' + str(invitation.time.strftime('%H:%M'))
            detail_notify_en += ' on ' + str(invitation.date_start.strftime('%A')) + ', ' + str(
                invitation.date_start.strftime('%d-%m-%Y'))

            detail_notify_vi = str(request.user.user_profile.display_name) + ' mời bạn tham gia sự kiện tại ' + str(
                invitation.golfcourse.name)
            if invitation.time:
                detail_notify_vi += ' lúc ' + str(invitation.time.strftime('%H:%M'))
            detail_notify_vi += ' vào ' + str(invitation.date_start.strftime('%A')) + ', ' + str(
                invitation.date_start.strftime('%d-%m-%Y'))

            translate_message = {
                'alert_vi': detail_notify_vi,
                'alert_en': detail_notify_en
            }
            # --- End message ---
            for player in players:
                name = player.get('name')
                email = player['email'].lower() if player.get('email') else None
                phone = player.get('phone')
                player = User.objects.filter(Q(id=player.get('user_id')) | Q(username=email) | Q(email=email)).first()
                if player:
                    instance, created = EventMember.objects.get_or_create(user=player,
                                                                          # status='P',
                                                                          event=invitation)
                    if not created:
                        instance.status = 'P'
                        instance.save()
                else:
                    created = False
                    player = Customer.objects.create(name=name, email=email, phone_number=phone)
                    instance = EventMember.objects.create(customer=player,
                                                          status='P',
                                                          event=invitation)

                if player and isinstance(player, User) and created:
                    Notice.objects.get_or_create(content_type=event_ctype,
                                                 object_id=invitation.id,
                                                 to_user=player,
                                                 detail=detail,
                                                 detail_en=detail_en,
                                                 notice_type='I',
                                                 from_user=request.user,
                                                 send_email=False)
                    send_notification.delay([player.id], detail_notify_en, translate_message)
        return Response({'status': '200', 'code': 'OK',
                         'detail': 'OK'}, status=200)

    def pre_save(self, obj):
        obj.user = self.request.user

    def partial_update(self, request, pk=None):
        type = request.DATA.get('type', 'Invite')

        if type == 'Book':
            teetime = get_or_none(BookedTeeTime, id=pk)
            players = request.DATA['invite_people']
            for player in players:
                email = player['email'].lower()
                player = get_or_none(User, username=email)
                if player:
                    BookedPartner.objects.get_or_create(user=player, teetime=teetime)
                else:
                    subject = 'Golfconnect24 Invitation'
                    message = 'You have been invited to play golf by ' + str(request.user)
                    send_email.delay(subject, message, [email])
        else:
            try:
                invitation = GolfCourseEvent.objects.get(id=pk)
            except Exception:
                return Response({'status': '404', 'code': 'E_NOT_FOUND',
                                 'detail': 'Not found'}, status=404)
            # ########## Update data no need to notify others ##########
            is_publish = request.DATA.get('is_publish', None)
            if is_publish is not None:
                if not EventMember.objects.filter(event=invitation,
                                                  user=request.user).exists() and invitation.user != request.user:
                    return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                                     'detail': 'You do not have permission to peform this action'}, status=401)
                invitation.is_publish = is_publish
                invitation.save(update_fields=['is_publish'])
                return Response({'status': '200', 'code': 'OK',
                                 'detail': 'OK'}, status=200)
            description = request.DATA.get('description', None)
            from_hdcp = request.DATA.get('from_hdcp', None)
            to_hdcp = request.DATA.get('to_hdcp', None)
            if description is not None or from_hdcp is not None or to_hdcp is not None:
                if request.user != invitation.user:
                    return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                                     'detail': 'You do not have permission to peform this action'}, status=401)
                invitation.description = description
                invitation.from_hdcp = from_hdcp
                invitation.to_hdcp = to_hdcp
                invitation.save(update_fields=['description', 'from_hdcp', 'to_hdcp'])
            # ##############################################################
            golfcourse = request.DATA.get('golfcourse', invitation.golfcourse_id)
            request.DATA['golfcourse'] = golfcourse
            golfcourse_names = list(GolfCourse.objects.all().values('id', 'name'))
            try:
                int(request.DATA['golfcourse'])
            except ValueError:
                golfcourse_id = None
                for g in golfcourse_names:
                    if fuzz.token_set_ratio(request.DATA['golfcourse'], g['name']) > 90:
                        golfcourse_id = g['id']
                        request.DATA['golfcourse'] = golfcourse_id
                        break
                if not golfcourse_id:
                    return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                     'detail': 'Invalid GolfCourse'}, status=400)

            players = request.DATA['invite_people']

            username = invitation.user.username
            check_invitation = GolfCourseEvent.objects.get(id=pk)
            invited_player = check_invitation.event_member.all().prefetch_related('user', 'customer')
            invited_email = []
            invited_user_ids = []
            for p in invited_player:
                if p.customer and p.customer.email:
                    invited_email.append(p.customer.email)
                elif p.user:
                    if p.user.email:
                        invited_email.append(p.user.email)
                    invited_user_ids.append(p.user.id)

            valid_player = []
            for player in players:
                email = player.get('email')
                phone = player.get('phone')
                user_id = player.get('user_id')
                if not any([email, phone, user_id]):
                    return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                     'detail': 'You must fill at least email or phone'}, status=400)

                if email == request.user.username or user_id == request.user.id:
                    return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                     'detail': 'Cannot invite myself'}, status=400)
                if (user_id not in invited_user_ids) and (email not in invited_email):
                    valid_player.append(player)

            request.DATA['invite_people'] = valid_player
            players = valid_player
            request.DATA.update({
                'date_start': request.DATA['date']
            })
            serializer = self.serializer_class(data=request.DATA)
            if not serializer.is_valid():
                return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                 'detail': serializer.errors}, status=400)

            user_ctype = ContentType.objects.get_for_model(User)
            customer_ctype = ContentType.objects.get_for_model(Customer)
            invitation_ctype = ContentType.objects.get_for_model(GolfCourseEvent)
            if invitation.user == request.user:
                updated = False
                if invitation.golfcourse_id != request.DATA['golfcourse']:
                    updated = True
                if str(invitation.date_start) != request.DATA['date']:
                    updated = True
                if invitation.time:
                    if str(invitation.time) != request.DATA['time']:
                        updated = True
                elif request.DATA['time']:
                    updated = True
                if updated:
                    # ----- Message for gc24 notification ------
                    message_destroy = '<a href=/#/profile/' + str(request.user.id) + '/>' + str(
                        request.user.user_profile.display_name) + '</a> hủy cuộc hẹn tại <b>' + invitation.golfcourse.name + '</b>'
                    if invitation.time:
                        message_destroy += ' lúc <b>' + str(invitation.time.strftime('%H:%M')) + '</b>'
                    message_destroy += ' vào <b>' + DOW[str(invitation.date_start.strftime('%A'))] + ', ' + str(
                        invitation.date_start.strftime('%d-%m-%Y')) + '</b>'

                    message_destroy_en = '<a href=/#/profile/' + str(request.user.id) + '/>' + str(
                        request.user.user_profile.display_name) + '</a>  has cancelled the invitation at <b>' + invitation.golfcourse.name + '</b>'
                    if invitation.time:
                        message_destroy_en += ' at <b>' + str(invitation.time.strftime('%H:%M')) + '</b>'
                    message_destroy_en += ' on <b>' + str(invitation.date_start.strftime('%A')) + ', ' + str(
                        invitation.date_start.strftime('%d-%m-%Y')) + '</b>'

                    super(InvitationViewSet, self).partial_update(request, pk)

                    new_invitation = GolfCourseEvent.objects.get(id=pk)
                    invited_player = new_invitation.event_member.all().prefetch_related('user', 'customer')

                    detail_html = '<br><br><br><b>Chào bạn,</b><br><br>' + str(
                        request.user.user_profile.display_name) + ' mời bạn tham gia sự kiện tại <b>' + str(
                        new_invitation.golfcourse) + '</b>'
                    if new_invitation.time:
                        detail_html += ' lúc <b>' + str(new_invitation.time.strftime('%H:%M')) + '</b>'
                    detail_html += ' vào <b>' + DOW[str(new_invitation.date_start.strftime('%A'))] + ', ' + str(
                        new_invitation.date_start.strftime('%d-%m-%Y')) + '</b>'

                    detail_htmlen = '<b>Hi,</b><br><br>' + str(
                        request.user.user_profile.display_name) + ' invited you to join the event at <b>' + str(
                        new_invitation.golfcourse) + '</b>'
                    if new_invitation.time:
                        detail_htmlen += ' at <b>' + str(new_invitation.time.strftime('%H:%M')) + '</b>'
                    detail_htmlen += ' on <b>' + str(new_invitation.date_start.strftime('%A')) + ', ' + str(
                        new_invitation.date_start.strftime('%d-%m-%Y')) + '</b>'

                    detail = '<a href=/#/profile/' + str(request.user.id) + '/>' + str(
                        request.user.user_profile.display_name) + '</a> mời bạn tham gia sự kiện tại <b>' + str(
                        new_invitation.golfcourse) + '</b>'
                    if new_invitation.time:
                        detail += ' lúc <b>' + str(new_invitation.time.strftime('%H:%M')) + '</b>'
                    detail += ' vào <b>' + DOW[str(new_invitation.date_start.strftime('%A'))] + ', ' + str(
                        new_invitation.date_start.strftime('%d-%m-%Y')) + '</b>'

                    # ----- Message destroy for push notification ------
                    message_destroy_notify = str(
                        request.user.user_profile.display_name) + ' has cancelled the invitation at ' + invitation.golfcourse.name
                    if invitation.time:
                        message_destroy_notify += ' at ' + str(invitation.time.strftime('%H:%M'))
                    message_destroy_notify += ' on ' + str(invitation.date_start.strftime('%A')) + ', ' + str(
                        invitation.date_start.strftime('%d-%m-%Y'))

                    message_destroy_notify_vi = str(
                        request.user.user_profile.display_name) + ' hủy cuộc hẹn tại ' + invitation.golfcourse.name
                    if invitation.time:
                        message_destroy_notify_vi += ' lúc ' + str(invitation.time.strftime('%H:%M'))
                    message_destroy_notify_vi += ' vào ' + str(invitation.date_start.strftime('%A')) + ', ' + str(
                        invitation.date_start.strftime('%d-%m-%Y'))

                    translate_message_destroy = {
                        'alert_vi': message_destroy_notify_vi,
                        'alert_en': message_destroy_notify
                    }
                    # ----- End message destroy for push notification ------

                    # ----- Message detail for push notification ------
                    detail_notify = str(
                        request.user.user_profile.display_name) + ' invited you to join the event at ' + str(
                        new_invitation.golfcourse.name)
                    if new_invitation.time:
                        detail_notify += ' at ' + str(new_invitation.time.strftime('%H:%M'))
                    detail_notify += ' on ' + str(new_invitation.date_start.strftime('%A')) + ', ' + str(
                        new_invitation.date_start.strftime('%d-%m-%Y'))

                    detail_notify_vi = str(
                        request.user.user_profile.display_name) + ' mời bạn tham gia sự kiện tại ' + str(
                        new_invitation.golfcourse.name)
                    if new_invitation.time:
                        detail_notify_vi += ' lúc ' + str(new_invitation.time.strftime('%H:%M'))
                    detail_notify_vi += ' vào ' + str(new_invitation.date_start.strftime('%A')) + ', ' + str(
                        new_invitation.date_start.strftime('%d-%m-%Y'))

                    translate_message_detail = {
                        'alert_en': detail_notify,
                        'alert_vi': detail_notify_vi
                    }

                    detail_en = '<a href=/#/profile/' + str(request.user.id) + '/>' + str(
                        request.user.user_profile.display_name) + '</a> invited you to join the event at <b>' + str(
                        new_invitation.golfcourse.name) + '</b>'
                    if new_invitation.time:
                        detail_en += ' at <b>' + str(new_invitation.time.strftime('%H:%M')) + '</b>'
                    detail_en += ' on <b>' + str(invitation.date_start.strftime('%A')) + ', ' + str(
                        new_invitation.date_start.strftime('%d-%m-%Y')) + '</b>'

                    ctype = invitation_ctype
                    subject = 'Golfconnect24 Invitation'
                    for invited in invited_player:
                        if invited.customer:
                            player = invited.customer
                        else:
                            player = invited.user
                        if player != request.user:
                            if isinstance(player, Customer):

                                if player.email:
                                    html_content = detail_htmlen + '.<br> <a href="' + 'https://' + request.META[
                                        'HTTP_HOST'] + '/#/register-invite/' + str(
                                        invited.id) + '">Click here to register</a>'
                                    html_content += detail_html + '.<br> <a href="' + 'https://' + request.META[
                                        'HTTP_HOST'] + '/#/register-invite/' + str(
                                        invited.id) + '">Nhấp vào đây để đăng kí</a>'
                                    # send_email.delay(subject, message_destroy_html, [player.email])
                                    # send_email.delay(subject, html_content, [player.email])
                            elif isinstance(player, User):
                                invited.status = 'P'
                                invited.save(update_fields=['status'])

                                Notice.objects.create(content_type=ctype,
                                                      object_id=invitation.id,
                                                      to_user=player,
                                                      detail=message_destroy,
                                                      detail_en=message_destroy_en,
                                                      notice_type='IN',
                                                      from_user=invitation.user,
                                                      send_email=False
                                                      )
                                Notice.objects.filter(content_type=ctype,
                                                      object_id=invitation.id,
                                                      to_user=player,
                                                      notice_type='I',
                                                      from_user=invitation.user).delete()

                                Notice.objects.get_or_create(content_type=ctype,
                                                             object_id=new_invitation.id,
                                                             to_user=player,
                                                             detail=detail,
                                                             detail_en=detail_en,
                                                             notice_type='I',
                                                             from_user=new_invitation.user,
                                                             send_email=False)
                                send_notification([player.id], detail_notify, translate_message_detail)

            invitation = GolfCourseEvent.objects.get(id=pk)

            detail = '<a href=/#/profile/' + str(request.user.id) + '/></a> mời bạn tham gia sự kiện tại <b>' + str(
                invitation.golfcourse.name) + '</b>'
            if invitation.time:
                detail += ' lúc <b>' + str(invitation.time.strftime('%H:%M')) + '</b>'
            detail += ' vào <b>' + DOW[str(invitation.date_start.strftime('%A'))] + ', ' + str(
                invitation.date_start.strftime('%d-%m-%Y')) + '</b>'

            detail_en = '<a href=/#/profile/' + str(request.user.id) + '/></a> invited you to join the event at <b>' + str(
                invitation.golfcourse.name) + '</b>'
            if invitation.time:
                detail_en += ' at <b>' + str(invitation.time.strftime('%H:%M')) + '</b>'
            detail_en += ' on <b>' + str(invitation.date_start.strftime('%A')) + ', ' + str(
                invitation.date_start.strftime('%d-%m-%Y')) + '</b>'

            # --- Message for push notifications
            detail_notify = str(request.user.user_profile.display_name) + ' invited you to join the event at ' + str(
                invitation.golfcourse.name)
            if invitation.time:
                detail_notify += ' at ' + str(invitation.time.strftime('%H:%M'))
            detail_notify += ' on ' + str(invitation.date_start.strftime('%A')) + ', ' + str(
                invitation.date_start.strftime('%d-%m-%Y'))

            detail_notify_vi = str(request.user.user_profile.display_name) + ' mời bạn tham gia sự kiện tại ' + str(
                invitation.golfcourse.name)
            if invitation.time:
                detail_notify_vi += ' lúc ' + str(invitation.time.strftime('%H:%M'))
            detail_notify_vi += ' vào ' + str(invitation.date_start.strftime('%A')) + ', ' + str(
                invitation.date_start.strftime('%d-%m-%Y'))

            translate_message_detail = {
                'alert_en': detail_notify,
                'alert_vi': detail_notify_vi
            }

            for player in players:
                name = player.get('name')
                email = player['email'].lower() if player.get('email') else None
                phone = player.get('phone')
                player = get_or_none(User, id=player.get('user_id'))
                if not player:
                    player = get_or_none(User, username=email)
                if not player:
                    player = User.objects.filter(email=email).first()  # try to get user by email
                if player:
                    instance, created = EventMember.objects.get_or_create(user=player,
                                                                          # status='P',
                                                                          event=invitation)
                    if not created:
                        instance.status = 'P'
                        instance.save(update_fields=['status'])
                else:
                    player = Customer.objects.create(name=name, email=email, phone_number=phone)
                    instance, created = EventMember.objects.get_or_create(customer=player,
                                                                          event=invitation)

                if created and isinstance(player, User):
                    ctype = invitation_ctype
                    Notice.objects.get_or_create(content_type=ctype,
                                                 object_id=invitation.id,
                                                 to_user=player,
                                                 detail=detail,
                                                 detail_en=detail_en,
                                                 notice_type='I',
                                                 from_user=request.user,
                                                 send_email=False)

                    send_notification([player.id], detail_notify, translate_message_detail)

        return Response({'status': '200', 'code': 'OK',
                         'detail': 'OK'}, status=200)

    def destroy(self, request, pk=None):
        temp = get_or_none(GolfCourseEvent, id=pk)
        if temp is None:
            return Response({'status': '404', 'code': 'E_NOT_FOUND',
                             'detail': 'Not found'}, status=404)
        players = temp.event_member.all()
        ctype = ContentType.objects.get_for_model(temp)
        if temp.user == request.user:
            message_html = '<b>Hi,</b><br><br>' + str(
                request.user.user_profile.display_name) + ' has cancelled the invitation at <b>' + temp.golfcourse.name + '</b>'
            if temp.time:
                message_html += ' at <b>' + str(temp.time.strftime('%H:%M')) + '</b>'
            message_html += ' on <b>' + str(temp.date_start.strftime('%A')) + ', ' + str(
                temp.date_start.strftime('%d-%m-%Y')) + '</b>'

            message_html += '<br><br><br><b>Chào bạn,</b><br><br>' + str(
                request.user.user_profile.display_name) + ' đã hủy cuộc hẹn tại <b>' + temp.golfcourse.name + '</b>'
            if temp.time:
                message_html += ' lúc <b>' + str(temp.time.strftime('%H:%M')) + '</b>'
            message_html += ' vào <b>' + DOW[str(temp.date_start.strftime('%A'))] + ', ' + str(
                temp.date_start.strftime('%d-%m-%Y')) + '</b>'

            subject = 'Golfconnect24 Invitation'
            message = '<a href=/#/profile/' + str(request.user.id) + '/>' + str(
                request.user.user_profile.display_name) + '</a> đã hủy cuộc hẹn tại <b>' + temp.golfcourse.name + '</b>'
            if temp.time:
                message += ' lúc <b>' + str(temp.time.strftime('%H:%M')) + '</b>'
            message += ' vào <b>' + DOW[str(temp.date_start.strftime('%A'))] + ', ' + str(
                temp.date_start.strftime('%d-%m-%Y')) + '</b>'

            message_en = '<a href=/#/profile/' + str(request.user.id) + '/>' + str(
                request.user.user_profile.display_name) + '</a> has cancelled the invitation at <b>' + temp.golfcourse.name + '</b>'
            if temp.time:
                message_en += ' at <b>' + str(temp.time.strftime('%H:%M')) + '</b>'
            message_en += ' on <b>' + str(temp.date_start.strftime('%A')) + ', ' + str(
                temp.date_start.strftime('%d-%m-%Y')) + '</b>'

            message_notify = str(
                request.user.user_profile.display_name) + ' has cancelled the invitation at ' + temp.golfcourse.name
            if temp.time:
                message_notify += ' at ' + str(temp.time.strftime('%H:%M'))
            message_notify += ' on ' + str(temp.date_start.strftime('%A')) + ', ' + str(
                temp.date_start.strftime('%d-%m-%Y'))

            message_notify_vi = str(
                request.user.user_profile.display_name) + ' đã hủy cuộc hẹn tại ' + temp.golfcourse.name
            if temp.time:
                message_notify_vi += ' lúc ' + str(temp.time.strftime('%H:%M'))
            message_notify_vi += ' vào ' + str(temp.date_start.strftime('%A')) + ', ' + str(
                temp.date_start.strftime('%d-%m-%Y'))

            translate_message_notify = {
                'alert_vi': message_notify_vi,
                'alert_en': message_notify
            }

            for player in players:
                if player.customer:
                    player = player.customer
                else:
                    player = player.user
                if isinstance(player, Customer):
                    pass
                    # if player.email:
                    #     send_email.delay(subject, message_html, [player.email])
                elif isinstance(player, User):
                    Notice.objects.create(content_type=ctype,
                                          object_id=temp.id,
                                          to_user=player,
                                          detail=message,
                                          detail_en=message_en,
                                          notice_type='IN',
                                          from_user=temp.user,
                                          send_email=False)

                    # send_notification.delay([player.id], message_notify, translate_message_notify)
            Notice.objects.filter(content_type=ctype,
                                  object_id=temp.id,
                                  notice_type='I').delete()
            # if temp.related_object:
            # temp.related_object.delete()
            temp.delete()
            # temp.is_show = False
            # temp.save(update_fields=['is_show'])

        else:
            partner = EventMember.objects.filter(event=temp, user=request.user)
            if not partner:
                return Response({'status': '404', 'code': 'E_NOT_FOUND',
                                 'detail': 'Not found'}, status=404)
            partner.delete()
            message = '<a href=/#/profile/' + str(request.user.id) + '/>' + str(
                request.user.user_profile.display_name) + '</a> đã hủy cuộc hẹn tại <b>' + temp.golfcourse.name + '</b>'
            if temp.time:
                message += ' lúc <b>' + str(temp.time.strftime('%H:%M')) + '</b>'
            message += ' vào <b>' + DOW[str(temp.date_start.strftime('%A'))] + ', ' + str(
                temp.date_start.strftime('%d-%m-%Y')) + '</b>'

            message_en = '<a href=/#/profile/' + str(request.user.id) + '/>' + str(
                request.user.user_profile.display_name) + '</a> has cancelled the invitation at <b>' + temp.golfcourse.name + '</b>'
            if temp.time:
                message_en += ' at <b>' + str(temp.time.strftime('%H:%M')) + '</b>'
            message_en += ' on <b>' + str(temp.date_start.strftime('%A')) + ', ' + str(
                temp.date_start.strftime('%d-%m-%Y')) + '</b>'

            message_notify = str(
                request.user.user_profile.display_name) + ' has cancelled the invitation at ' + temp.golfcourse.name
            if temp.time:
                message_notify += ' at ' + str(temp.time.strftime('%H:%M'))
            message_notify += ' on ' + str(temp.date_start.strftime('%A')) + ', ' + str(
                temp.date_start.strftime('%d-%m-%Y'))

            message_notify_vi = str(
                request.user.user_profile.display_name) + ' đã hủy cuộc hẹn tại ' + temp.golfcourse.name
            if temp.time:
                message_notify_vi += ' lúc ' + str(temp.time.strftime('%H:%M'))
            message_notify_vi += ' vào ' + str(temp.date_start.strftime('%A')) + ', ' + str(
                temp.date_start.strftime('%d-%m-%Y'))

            translate_message_notify = {
                'alert_vi': message_notify_vi,
                'alert_en': message_notify
            }
            Notice.objects.filter(content_type=ctype, object_id=temp.id, to_user=request.user).delete()
            Notice.objects.create(content_type=ctype,
                                  object_id=temp.id,
                                  to_user=temp.user,
                                  detail=message,
                                  detail_en=message_en,
                                  notice_type='IN',
                                  from_user=request.user,
                                  send_email=False)
            # send_notification.delay([temp.user.id], message_notify, translate_message_notify)
            for player in players:
                if player.user:
                    player = player.user
                    if isinstance(player, User) and player != request.user and player != temp.user:
                        Notice.objects.create(content_type=ctype,
                                              object_id=temp.id,
                                              to_user=player,
                                              detail=message,
                                              detail_en=message_en,
                                              notice_type='IN',
                                              from_user=request.user,
                                              send_email=False)
                        # send_notification.delay([player.id], message_notify, translate_message_notify)
        return Response({'status': '200', 'code': 'OK',
                         'detail': 'OK'}, status=200)

    def retrieve(self, request, pk=None):
        event = GolfCourseEvent.objects.filter(id=pk).first()
        if not event:
            return Response({'detail': 'Not found'}, status=404)
        item = InvitationSerializer(event).data
        if EventMember.objects.filter(user=request.user, event_id=pk).exists() or item['user'] == request.user.id:
            item.update({'is_join': True})
        if EventMember.objects.filter(user=request.user, event_id=pk, status='P').exists():
            item.update({'is_invited': True})
        return Response(item, status=200)


class DecidedFromMailView(APIView):
    parser_classes = (JSONParser, FormParser,)

    @staticmethod
    def post(request, type, user_id):
        ctype = ContentType.objects.get_for_model(User)
        invite_people = get_or_none(EventMember, pk=user_id)
        status = type
        invitation = invite_people.event
        user = invite_people.user

        invited_player = invitation.event_member.all()
        invite_ctype = ContentType.objects.get_for_model(GolfCourseEvent)
        Notice.objects.filter(content_type=invite_ctype,
                              object_id=invitation.id,
                              to_user=user,
                              notice_type='I',
                              from_user=invitation.user).delete()
        # if isinstance(invitation.related_object, GolfCourseEvent) and invitation.related_object.event_type == 'PE':
        # EventMember.objects.filter(user=user, event=invitation.related_object).update(is_active=True)
        response = ''
        if status == 'C':
            invite_people.delete()
            response = ' đã từ chối cuộc hẹn'
            response_en = ' rejected the invitation'
        elif status == 'A':
            invite_people.status = status
            invite_people.is_active = True
            invite_people.save(update_fields=['status', 'is_active'])
            response = ' đã chấp nhận cuộc hẹn'
            response_en = ' accepted the invitation'
        detail = '<a href=/#/profile/' + str(user.id) + '/>' + str(
            user.user_profile.display_name) + '</a>' + response + ' tại <b>' + str(invitation.golfcourse.name) + '</b>'
        if invitation.time:
            detail += ' lúc <b>' + str(invitation.time.strftime('%H:%M')) + '</b>'
        detail += ' vào <b>' + DOW[str(invitation.date_start.strftime('%A'))] + ', ' + str(
            invitation.date_start.strftime('%d-%m-%Y')) + '</b>'
        detail_en = '<a href=/#/profile/' + str(user.id) + '/>' + str(
            user.user_profile.display_name) + '</a>' + response_en + ' at <b>' + str(
            invitation.golfcourse.name) + '</b>'
        if invitation.time:
            detail_en += ' at <b>' + str(invitation.time.strftime('%H:%M')) + '</b>'
        detail_en += ' on <b>' + str(invitation.date_start.strftime('%A')) + ', ' + str(
            invitation.date_start.strftime('%d-%m-%Y')) + '</b>'

        message_notify = str(user.user_profile.display_name) + response_en + ' at ' + str(invitation.golfcourse.name)
        if invitation.time:
            message_notify += ' at ' + str(invitation.time.strftime('%H:%M'))
        message_notify += ' on ' + str(invitation.date_start.strftime('%A')) + ', ' + str(
            invitation.date_start.strftime('%d-%m-%Y'))

        message_notify_vi = str(user.user_profile.display_name) + response + ' tại ' + str(invitation.golfcourse.name)
        if invitation.time:
            message_notify_vi += ' lúc ' + str(invitation.time.strftime('%H:%M'))
        message_notify_vi += ' vào ' + str(invitation.date_start.strftime('%A')) + ', ' + str(
            invitation.date_start.strftime('%d-%m-%Y'))

        translate_message_notify = {
            'alert_vi': message_notify_vi,
            'alert_en': message_notify
        }
        for invited in invited_player:
            if invited.customer:
                player = invited.customer
            else:
                player = invited.user
            if player != user:
                if isinstance(player, User):
                    Notice.objects.create(content_type=ctype,
                                          object_id=invitation.id,
                                          to_user=player,
                                          detail=detail,
                                          detail_en=detail_en,
                                          notice_type='IN',
                                          from_user=user,
                                          send_email=False)
                    # if player.user_profile.deviceToken:
                    #     send_notification.delay([player.id], message_notify, translate_message_notify)
        Notice.objects.create(content_type=ctype,
                              object_id=invitation.id,
                              to_user=invitation.user,
                              detail=detail,
                              detail_en=detail_en,
                              notice_type='IN',
                              from_user=user,
                              send_email=False)
        # if invitation.user.user_profile.deviceToken:
        #     send_notification.delay([invitation.user.id], message_notify, translate_message_notify)
        return Response(status=200)


class DecidedView(APIView):
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def post(request):
        ctype = ContentType.objects.get_for_model(User)
        invite_ctype = ContentType.objects.get_for_model(GolfCourseEvent)
        invitation_id = request.DATA.get('invitation', None)
        invitation = get_or_none(GolfCourseEvent, id=invitation_id)
        if not invitation:
            return Response({'status': '404', 'code': 'E_NOT_FOUND',
                             'detail': 'Not found this invitation'}, status=404)

        invite_people = get_or_none(EventMember, event=invitation, user=request.user)
        user = request.user
        if not invite_people:
            return Response({'status': '404', 'code': 'E_NOT_FOUND',
                             'detail': 'Not found this user'}, status=404)
        status = request.DATA.get('type', None)

        invited_player = invitation.event_member.all()
        response = ''
        if status == 'C':
            invite_people.delete()
            response = ' đã từ chối cuộc hẹn'
            response_en = ' rejected the invitation'
            notice_type = 'IC'
        elif status == 'A':
            invite_people.status = status
            invite_people.is_active = True
            invite_people.is_join = True
            invite_people.save(update_fields=['status', 'is_active', 'is_join'])
            response = ' đã chấp nhận cuộc hẹn'
            response_en = ' accepted the invitation'
            notice_type = 'IA'
        Notice.objects.filter(object_id=int(invitation_id), content_type=invite_ctype).update(is_show=True,
                                                                                              is_read=True,
                                                                                              notice_type=notice_type)
        # if isinstance(invitation.related_object, GolfCourseEvent) and invitation.related_object.event_type == 'PE':
        # EventMember.objects.filter(user=request.user, event=invitation.related_object).update(is_active=True)

        detail = '<a href=/#/profile/' + str(user.id) + '/>' + str(
            user.user_profile.display_name) + '</a>' + response + ' tại <b>' + str(invitation.golfcourse.name) + '</b>'
        if invitation.time:
            detail += ' lúc <b>' + str(invitation.time.strftime('%H:%M')) + '</b>'
        detail += ' vào <b>' + DOW[str(invitation.date_start.strftime('%A'))] + ', ' + str(
            invitation.date_start.strftime('%d-%m-%Y')) + '</b>'
        detail_en = '<a href=/#/profile/' + str(user.id) + '/>' + str(
            user.user_profile.display_name) + '</a>' + response_en + ' at <b>' + str(
            invitation.golfcourse.name) + '</b>'
        if invitation.time:
            detail_en += ' at <b>' + str(invitation.time.strftime('%H:%M')) + '</b>'
        detail_en += ' on <b>' + str(invitation.date_start.strftime('%A')) + ', ' + str(
            invitation.date_start.strftime('%d-%m-%Y')) + '</b>'

        message_notify = str(user.user_profile.display_name) + response_en + ' at ' + str(invitation.golfcourse.name)
        if invitation.time:
            message_notify += ' at ' + str(invitation.time.strftime('%H:%M'))
        message_notify += ' on ' + str(invitation.date_start.strftime('%A')) + ', ' + str(
            invitation.date_start.strftime('%d-%m-%Y'))

        message_notify_vi = str(user.user_profile.display_name) + response + ' tại ' + str(invitation.golfcourse.name)
        if invitation.time:
            message_notify_vi += ' lúc ' + str(invitation.time.strftime('%H:%M'))
        message_notify_vi += ' vào ' + str(invitation.date_start.strftime('%A')) + ', ' + str(
            invitation.date_start.strftime('%d-%m-%Y'))

        translate_message_notify = {
            'alert_vi': message_notify_vi,
            'alert_en': message_notify
        }
        for invited in invited_player:
            if invited.customer:
                player = invited.customer
            else:
                player = invited.user
            if player != user:
                if isinstance(player, User):
                    Notice.objects.create(content_type=ctype,
                                          object_id=invitation.id,
                                          to_user=player,
                                          detail=detail,
                                          detail_en=detail_en,
                                          notice_type='IN',
                                          from_user=user,
                                          send_email=False)
                    # if player.user_profile.deviceToken:
                    #     send_notification.delay([player.id], message_notify, translate_message_notify)
        Notice.objects.create(content_type=ctype,
                              object_id=invitation.id,
                              to_user=invitation.user,
                              detail=detail,
                              detail_en=detail_en,
                              notice_type='IN',
                              from_user=user,
                              send_email=False)
        # if invitation.user.user_profile.deviceToken:
        #     send_notification.delay([invitation.user.id], message_notify, translate_message_notify)
        return Response({'status': '200', 'code': 'OK',
                         'detail': 'OK'}, status=200)
