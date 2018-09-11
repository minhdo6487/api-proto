import datetime
import json

import math

from api.galleryMana.serializers import GolfCourseGallerySerializer
from api.golfcourseMana.serializers import GolfCourseSerializer, GolfCourseSettingsSerializer, \
    SubGolfCourseSerializer, HolesSerializer, ServicesSerializer, GolfCourseListSerializer, \
    GolfCourseServicesSerializer, GolfCourseBuggySerializer, GolfCourseCaddySerializer, GolfCourseClubSetSerializer, \
    TeeTypeSerializer, HoleTeeSerializer, GolfCourseStaffSerializer, FullGolfCourseSerializer, \
    GolfCourseReviewSerializer, PaginatedGolfCourseListSerializer
from api.golfcourseeventMana.serializers import PublicGolfCourseEventSerializer
from core.gallery.models import Gallery
from core.golfcourse.models import GolfCourse, GolfCourseServices, Services, SubGolfCourse, Hole, \
    GolfCourseClubSets, GolfCourseCaddy, GolfCourseBuggy, GolfCourseSetting, TeeType, HoleTee, GolfCourseStaff, \
    GolfCourseBookingSetting, GolfCourseReview, GolfCourseEvent
from core.location.models import Country
from core.teetime.models import BookingTime, DealEffective_TeeTime
from dateutil import relativedelta
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from geopy import distance
from pytz import timezone, country_timezones
from rest_framework import mixins
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from utils.django.models import get_or_none
from utils.rest.func import paginate_query, get_distance
from utils.rest.permissions import UserIsOwnerOrReadOnly
from utils.rest.viewsets import GetAndUpdateViewSet, OnlyGetViewSet


class GolfCourseViewSet(OnlyGetViewSet):
    """ Viewset handle for requesting golf course information
    """
    queryset = GolfCourse.objects.all()
    serializer_class = GolfCourseSerializer
    permission_classes = (AllowAny,)
    parser_classes = (JSONParser, FormParser,)

    def create(self, request, *args, **kwargs):
        from core.golfcourse.models import City
        from core.user.models import UserProfile
        user = get_or_none(UserProfile, user=request.user)
        if not user:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        else:
            print ("ok")

        """
            :param request:
                "id": no need,
                "city": str
                "lat":str,
                "lon":str",
                "website":url link
                "address":str,
                "name":name of golfcourse,
                "phone":phone number,
                "subGolfcourse"
        """
        req_js = request.DATA

        gc_data = req_js
        gc = gc_data

        country = Country.objects.get(pk = 1 )

        try:
            if not 'subGolfcourse' in gc:
                num_hole = gc['holeInfo']['courseInfo']['courseHoles']
            else:

                num_hole = gc['subGolfcourse'][0]['holeInfo']['courseInfo']['courseHoles']
        except:
            num_hole = 18
        city, created = City.objects.get_or_create(name=gc['city'], country=country)
        create_gc = GolfCourse.objects.create(latitude=gc['lat'], longitude=gc['lon'], phone=gc['phone'],
                                              website=gc['website'], address=gc['address'], name=gc['name'],
                                              city=city,
                                              number_of_hole=num_hole, country=country)

        if 'subGolfcourse' in gc:
            subgolfcourse = gc['subGolfcourse']
        else:
            subgolfcourse = [gc]

        for sub_gc in subgolfcourse:
            s = SubGolfCourse.objects.create(name=sub_gc['name'], golfcourse=create_gc,
                                             number_of_hole=int(num_hole))
            # print (sub_gc['name'])

            if 'holeInfo' in sub_gc:
                hole_info = sub_gc['holeInfo']
                num_hole = hole_info['courseInfo']['courseHoles']
                par_info = hole_info['coursePar'][0]
                hole_hdc = hole_info['holeHandicaps'][0]
                for h_info in hole_info['coursePar']:
                    if h_info['m_l'] == 'Men':
                        par_info = h_info
                        break
                for h_info in hole_info['holeHandicaps']:
                    if h_info['m_l'] == 'Men':
                        hole_hdc = h_info
                        break

                for i in range(0, s.number_of_hole):
                    try:
                        if len(hole_info['courseGPS']) > 0:
                            Hole.objects.create(subgolfcourse=s, holeNumber=int(i + 1),
                                                par=par_info['H' + str(i + 1)],
                                                hdcp_index=hole_hdc['H' + str(i + 1)],
                                                lat=hole_info['courseGPS'][str(i + 1)][0]['latitude'],
                                                lng=hole_info['courseGPS'][str(i + 1)][0]['longitud'])
                        else:
                            Hole.objects.create(subgolfcourse=s, holeNumber=int(i + 1),
                                                par=par_info['H' + str(i + 1)],
                                                hdcp_index=hole_hdc['H' + str(i + 1)])
                    except:
                        Hole.objects.create(subgolfcourse=s, holeNumber=int(i + 1), par=par_info['H' + str(i + 1)],
                                            hdcp_index=hole_hdc['H' + str(i + 1)])
                        # print(hole_info['courseGPS'])
                for tee_box in hole_info['courseTeebox']:
                    if len(tee_box['teeName']) > 7:
                        color = 'Black'
                    else:
                        color = tee_box['teeName']
                    t = TeeType.objects.create(subgolfcourse=s, name=tee_box['teeName'], color=color,
                                               slope=tee_box['slope'], rating=tee_box['rating'])
                    for i in range(0, s.number_of_hole):
                        h = Hole.objects.get(subgolfcourse=s, holeNumber=int(i + 1))
                        yard = tee_box['H' + str(i + 1)]
                        HoleTee.objects.create(tee_type=t, yard=yard, hole=h)
        tee_type = TeeType.objects.filter(subgolfcourse = s.pk).values('color', 'slope','rating')
        return Response(
            {
                'status': '200',
                'detail':
                    {
                        'saved_golfcourse': create_gc.pk,
                        'saved_SubGolfcourse:': s.pk,
                        'tee_type': list(tee_type)

                    },
                'code': 'OK'},
            status=200)

    def list(self, request, *args, **kwargs):
        lat = request.QUERY_PARAMS.get('lat')
        lng = request.QUERY_PARAMS.get('lng')
        sort = request.QUERY_PARAMS.get('sort')
        country = request.QUERY_PARAMS.get('country', None)
        items = []
        if sort == 'country':
            results = {}
            country = Country.objects.all().values('id', 'name', 'flag')
            golfcourse = GolfCourse.objects.values('name', 'picture', 'longitude', 'latitude', 'country_id', 'id').all()
            results.update({
                'country': country,
                'golfcourse': golfcourse
            })
            return Response(results, status=200)
        if country:
            with open('api/golfcourseMana/country.json') as data_file:
                country_json = json.load(data_file)
            if country in country_json:
                try:
                    country_id = Country.objects.only('id').get(short_name=country)
                except Exception:
                    return Response([], status=200)
            else:
                try:
                    country_id = Country.objects.only('id').get(id=country)
                except Exception:
                    return Response([], status=200)
            golfcourse = GolfCourse.objects.filter(country_id=country_id)
            gc_serializer = FullGolfCourseSerializer(golfcourse)

            return Response(gc_serializer.data, status=200)

        if not lat or not lng:
            return super().list(request, *args, **kwargs)

        lat = float(lat)
        lng = float(lng)
        min_lat = lat - 1  # You have to calculate this offsets based on the user location.
        max_lat = lat + 1  # Because the distance of one degree varies over the planet.
        min_lng = lng - 1
        max_lng = lng + 1
        golfcourses = GolfCourse.objects.filter(latitude__gt=min_lat, latitude__lt=max_lat, longitude__gt=min_lng,
                                                longitude__lt=max_lng).exclude(pk=0)[:50]
        results = []
        origin = [(lat, lng)]
        destinations = [(g.latitude, g.longitude) for g in golfcourses]

        # there is nothing
        if len(destinations) == 0:
            return Response([], status=200)

        res = get_distance(origin, destinations)
        for g, d in zip(golfcourses, res['rows'][0]['elements']):
            serializer = GolfCourseListSerializer(g)
            serializer.data.update({'distance': d['distance']['value'] / 1000.0})
            results.append(serializer.data)
        results = sorted(results, key=lambda k: k['distance'])

        return Response(results, status=200)


class GolfCourseListViewSet(OnlyGetViewSet):
    """ Viewset handle for requesting golf course information
    """
    queryset = GolfCourse.objects.all()
    serializer_class = GolfCourseListSerializer
    parser_classes = (JSONParser, FormParser,)

    def list(self, request, *args, **kwargs):
        query = dict()
        valid_keys = ['country__name', 'name', 'country__short_name']
        is_paginate = request.QUERY_PARAMS.get('is_paginate')
        for k in request.QUERY_PARAMS:
            if k not in valid_keys:
                continue
            key = k
            if k == 'country__name' or k == 'name':
                key = k + '__contains'
            query[key] = request.QUERY_PARAMS.get(k)

        query = GolfCourse.objects.filter(Q(**query)).exclude(pk=0).order_by('-partner', 'name')

        country_code = request.QUERY_PARAMS.get('country__short_name', 'vn')
        tz = timezone(country_timezones(country_code)[0])
        now = datetime.datetime.utcnow()
        current_tz = datetime.datetime.fromtimestamp(now.timestamp(), tz)
        next_date = current_tz.date() + datetime.timedelta(days=1)
        filter_condition = {
            'date': current_tz.date(),
            'from_time__lte': current_tz.time(), 'to_time__gte': current_tz.time(),
            'deal__active': True
        }
        args = {}
        for k, v in filter_condition.items():
                if v:
                    args[k] = v
        booking_time = BookingTime.objects.filter(Q(**args))
        deal_teetime = {}
        count = {}
        if booking_time:
            for bt in booking_time:
                if not bt.deal.active:
                    continue
                if (current_tz.date() == bt.deal.effective_date and current_tz.time() <= bt.deal.effective_time) or (current_tz.date() == bt.deal.expire_date and current_tz.time() >= bt.deal.expire_time):
                    continue
                deal = DealEffective_TeeTime.objects.filter(bookingtime=bt, teetime__date=next_date)
                if deal.exists():
                    for d in deal:
                        if d.teetime.id not in deal_teetime.keys():
                            count[bt.deal.golfcourse.id] = (count[bt.deal.golfcourse.id] + 1) if bt.deal.golfcourse.id in count.keys() else 1
                            deal_teetime[d.teetime.id] = d
        #### END GETTING DEAL
        # Paginate

        if is_paginate:
            item = request.GET.get('item', 10)
            page = request.QUERY_PARAMS.get('page')
            paginate = paginate_query(query, page, item)
            serializer = PaginatedGolfCourseListSerializer(instance=paginate, context={'deal_count': count})
            serializer.data['results'] =sorted(serializer.data['results'], key=lambda x: x['name'])
            serializer.data['results'] = sorted(serializer.data['results'], key=lambda x: x['discount'], reverse=True)
            result = serializer.data
        else:
            serializer = GolfCourseListSerializer(query, context={'deal_count': count})
            result = sorted(serializer.data, key=lambda x: (x['discount']), reverse=True)

        return Response(result, status=200)


class SettingsUnderCourseViewSet(GetAndUpdateViewSet):
    """ Viewset handle for requesting settings of golf course information
    """
    queryset = GolfCourseSetting.objects.all()
    serializer_class = GolfCourseSettingsSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        gc_id = self.kwargs['golfcourse_pk']
        return GolfCourseSetting.objects.filter(golfcourse__id=gc_id)


class TeeTypeUnderGolfcourseViewSet(viewsets.ModelViewSet):
    """ Viewset handle for requesting holes of subcourse information
    """
    queryset = TeeType.objects.all()
    serializer_class = TeeTypeSerializer
    parser_classes = (JSONParser, FormParser,)

    # permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly,)

    def initial(self, request, *args, **kwargs):
        # logging.debug(request.TYPE)
        if request.method == 'POST':
            request.DATA['subgolfcourse'] = kwargs['scourse_pk']
        super().initial(request, *args, **kwargs)


class ServicesViewSet(viewsets.ModelViewSet):
    """ Viewset handle for requesting golf services information
    """
    queryset = Services.objects.all()
    serializer_class = ServicesSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly,)


class GolfCourseServicesUnderCourseViewSet(viewsets.ModelViewSet):
    """ Viewset handle for requesting golf course services information
    """
    queryset = GolfCourseServices.objects.all()
    serializer_class = GolfCourseServicesSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly,)

    def get_queryset(self):
        return GolfCourseServices.objects.filter(golfcourse=self.kwargs['golfcourse_pk'])

    def pre_save(self, obj):
        obj.golfcourse_id = self.kwargs['golfcourse_pk']


class SubGolfCourseUnderCourseViewSet(viewsets.ModelViewSet):
    """ Viewset handle for requesting sub course of specific golfcourse information
    """
    queryset = SubGolfCourse.objects.all()
    serializer_class = SubGolfCourseSerializer
    parser_classes = (JSONParser, FormParser,)


    # permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly,)

    def get_queryset(self):
        return SubGolfCourse.objects.filter(golfcourse=self.kwargs['golfcourse_pk'])

    def initial(self, request, *args, **kwargs):
        # logging.debug(request.TYPE)
        if request.method == 'POST':
            request.DATA['golfcourse'] = kwargs['golfcourse_pk']
        super().initial(request, *args, **kwargs)


class SubGolfCourseViewSet(viewsets.ModelViewSet):
    """ Viewset handle for requesting sub course of specific golfcourse information
    """
    queryset = SubGolfCourse.objects.all()
    serializer_class = SubGolfCourseSerializer
    parser_classes = (JSONParser, FormParser,)


class StaffUnderCourseViewSet(viewsets.ModelViewSet):
    """ Viewset handle for requesting sub course of specific golfcourse information
    """
    queryset = GolfCourseStaff.objects.all()
    serializer_class = GolfCourseStaffSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """ Get
        """
        return GolfCourseStaff.objects.filter(golfcourse=self.kwargs['golfcourse_pk'])

    def initial(self, request, *args, **kwargs):
        if request.method == 'POST':
            request.DATA['golfcourse'] = kwargs['golfcourse_pk']
        super().initial(request, *args, **kwargs)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def golfcourse_id_by_staff(request):
    user = request.user.id
    staff = get_or_none(GolfCourseStaff, user=user)
    if staff is None:
        return Response({'status': '404', 'code': 'E_NOT_FOUND',
                         'detail': 'Cannot find you in golfcourse'}, status=404)

    serializer = GolfCourseSerializer(staff.golfcourse)
    return Response(serializer.data, status=200)


class HolesUnderSubCourseViewSet(viewsets.ModelViewSet):
    """ Viewset handle for requesting holes of subcourse information
    """
    queryset = Hole.objects.all()
    serializer_class = HolesSerializer
    parser_classes = (JSONParser, FormParser,)

    # permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly,)

    def get_queryset(self):
        """ Get List Hole of subcourse
        """
        return Hole.objects.filter(subgolfcourse=self.kwargs['scourse_pk'])

    def initial(self, request, *args, **kwargs):
        # logging.debug(request.TYPE)
        if request.method == 'POST':
            request.DATA['subgolfcourse'] = kwargs['scourse_pk']
        super().initial(request, *args, **kwargs)


class HolesViewSet(viewsets.ModelViewSet):
    """ Viewset handle for requesting holes of subcourse information
    """
    queryset = Hole.objects.all()
    serializer_class = HolesSerializer
    parser_classes = (JSONParser, FormParser,)


class HolesTeeUnderHoleViewSet(viewsets.ModelViewSet):
    """ Viewset handle for requesting holes of subcourse information
    """
    queryset = HoleTee.objects.all()
    serializer_class = HoleTeeSerializer
    parser_classes = (JSONParser, FormParser,)

    # permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly,)

    def get_queryset(self):
        """ Get all friend request to current use
        """
        return HoleTee.objects.filter(hole=self.kwargs['hole_pk'])

    def initial(self, request, *args, **kwargs):
        if request.method == 'POST':
            request.DATA['hole'] = kwargs['hole_pk']
        super().initial(request, *args, **kwargs)


class GolfCourseBuggyViewSet(viewsets.ModelViewSet):
    """ Viewset handle for requesting course information
    """
    queryset = GolfCourseBuggy.objects.all()
    serializer_class = GolfCourseBuggySerializer
    permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly,)
    parser_classes = (JSONParser, FormParser,)

    def get_queryset(self):
        """ Get all friend request to current use
        """
        return GolfCourseBuggy.objects.filter(golfcourse=self.kwargs['golfcourse_pk'])

    def initial(self, request, *args, **kwargs):
        # logging.debug(request.TYPE)
        if request.method == 'POST':
            request.DATA['golfcourse'] = kwargs['golfcourse_pk']
        super().initial(request, *args, **kwargs)


class GolfCourseGalleryViewSet(viewsets.ModelViewSet):
    queryset = Gallery.objects.all()
    serializer_class = GolfCourseGallerySerializer
    permission_classes = (UserIsOwnerOrReadOnly,)
    parser_classes = (JSONParser, FormParser,)

    def get_queryset(self):
        ctype = ContentType.objects.get_by_natural_key('golfcourse', 'golfcourse')
        return Gallery.objects.filter(content_type=ctype.id, object_id=self.kwargs['golfcourse_pk'])

    def initial(self, request, *args, **kwargs):
        if request.method == 'POST':
            request.DATA['golfcourse'] = kwargs['golfcourse_pk']
        super().initial(request, *args, **kwargs)


class GolfCourseClubSetsViewSet(viewsets.ModelViewSet):
    """ Viewset handle for requesting course information
    """
    queryset = GolfCourseClubSets.objects.all()
    serializer_class = GolfCourseClubSetSerializer
    permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly,)
    parser_classes = (JSONParser, FormParser,)

    def get_queryset(self):
        return GolfCourseClubSets.objects.filter(golfcourse=self.kwargs['golfcourse_pk'])

    def initial(self, request, *args, **kwargs):
        # logging.debug(request.TYPE)
        if request.method == 'POST':
            request.DATA['golfcourse'] = kwargs['golfcourse_pk']
        super().initial(request, *args, **kwargs)


class GolfCourseCaddyViewSet(viewsets.ModelViewSet):
    """ Viewset handle for Golfcourse caddy
    """
    queryset = GolfCourseCaddy.objects.all()
    serializer_class = GolfCourseCaddySerializer
    permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly,)
    parser_classes = (JSONParser, FormParser,)

    def get_queryset(self):
        """ Return all caddy of 1 golfcourse by golfcourse pk
        """
        return GolfCourseCaddy.objects.filter(golfcourse=self.kwargs['golfcourse_pk'])

    def initial(self, request, *args, **kwargs):
        # logging.debug(request.TYPE)
        if request.method == 'POST':
            request.DATA['golfcourse'] = kwargs['golfcourse_pk']
        super().initial(request, *args, **kwargs)


@api_view(['GET'])
def golfcourse_term(request, golfcourse_id):
    st = GolfCourseBookingSetting.objects.filter(golfcourse_id=golfcourse_id).first()
    if not st:
        return Response({'status': '404', 'code': 'E_NOT_FOUND',
                         'detail': 'Not found'}, status=404)
    return Response({'policy': st.policy,
                     'policy_en': st.policy_en,
                     'request_policy': st.request_policy,
                     'request_policy_en': st.request_policy_en,
                     'status': 200}, status=200)


@api_view(['GET'])
def golfcourse_review(request, golfcourse_id):
    st = GolfCourseReview.objects.filter(golfcourse_id=golfcourse_id)
    serializer = GolfCourseReviewSerializer(st)
    return Response({'data': serializer.data})


@api_view(['GET'])
def golfcourse_event(request, golfcourse_id):
    today = datetime.datetime.today()
    end_date = (today + relativedelta.relativedelta(months=2)).replace(day=1)
    start_date = (today - relativedelta.relativedelta(months=1)).replace(day=1)
    semi_null = {
        'semi_null': 'coalesce(\"golfcourse_golfcourseevent\".\"banner\",\'\')=\'\''
    }
    st = GolfCourseEvent.objects.filter(golfcourse_id=golfcourse_id,
                                        is_publish=True,
                                        date_start__gte=start_date,
                                        date_start__lt=end_date).exclude(event_type='GE', date_end__lt=(today - datetime.timedelta(days=14))).extra(select=semi_null, order_by=['semi_null','-date_start'])
    serializer = PublicGolfCourseEventSerializer(st)
    return Response({'data': serializer.data})


class GolfCourseReviewViewSet(mixins.RetrieveModelMixin,
                              mixins.UpdateModelMixin,
                              mixins.DestroyModelMixin,
                              mixins.CreateModelMixin,
                              GenericViewSet):
    """ Viewset handle for requesting holes of subcourse information
    """
    queryset = GolfCourseReview.objects.all()
    serializer_class = GolfCourseReviewSerializer
    parser_classes = (JSONParser, FormParser,)

    def initial(self, request, *args, **kwargs):
        if request.method == 'POST':
            request.DATA['user'] = request.user.id
        super().initial(request, *args, **kwargs)

