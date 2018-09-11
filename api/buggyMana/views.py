import datetime
from core.golfcourse.models import GolfCourseBuggy, GolfCourseCaddy, GolfCourseStaff
from core.teetime.models import GuestType
from api.buggyMana.serializers import GolfCourseBuggySerializer, GolfCourseCaddySerializer
from utils.rest.permissions import UserIsOwnerOrReadOnly
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from rest_framework.permissions import IsAuthenticated
from utils.django.models import get_or_none

BUGGY_2_SEAT = 1
BUGGY_4_SEAT = 2
def fn_update_buggy_price(bi,bg,p9,p18,p27,p36,ps9,ps18,ps27,ps36,gc,fd,td):
	if bi:
		buggy_data,created = GolfCourseBuggy.objects.get_or_create(pk=bi,golfcourse=gc)
		buggy_data.golfcourse=gc
		buggy_data.buggy=bg
		buggy_data.price_9=p9
		buggy_data.price_18=p18
		buggy_data.price_27=p27
		buggy_data.price_36=p36
		buggy_data.price_standard_9=ps9 or 0
		buggy_data.price_standard_18=ps18 or 0
		buggy_data.price_standard_27=ps27 or 0
		buggy_data.price_standard_36=ps36 or 0
		buggy_data.from_date=fd
		buggy_data.to_date=td
		buggy_data.save()
	else:
		GolfCourseBuggy.objects.create(golfcourse=gc,buggy=bg,price_9=p9,price_18=p18,price_27=p27,price_36=p36,
									price_standard_9=ps9 or 0,price_standard_18=ps18 or 0,price_standard_27=ps27 or 0,price_standard_36=ps36 or 0,
									from_date=fd, to_date=td)
	return True

def fn_update_caddy_price(p9,p18,p27,p36,gc):
	obj = get_or_none(GolfCourseCaddy, golfcourse = gc)
	if obj:
		obj.price_9 = p9
		obj.price_18 = p18
		obj.price_27 = p27
		obj.price_36 = p36
		obj.save()
	else:
		return False
	return True
class GolfCourseBuggyViewSet(APIView):
	""" Viewset handle for requesting buggy information
	"""
	serializer_class = GolfCourseBuggySerializer
	permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly, )
	parser_classes = (JSONParser, FormParser,)
	def create_golfcoursebuggy(self,gc=None,bg=BUGGY_2_SEAT):
		GolfCourseBuggy.objects.create(golfcourse=gc,buggy=bg)

	def get(self, request, format=None):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		query = GolfCourseBuggy.objects.filter(golfcourse=staff.golfcourse)
		if not query.exists():
				GolfCourseBuggy.objects.create(golfcourse=staff.golfcourse,buggy=BUGGY_2_SEAT)
				GolfCourseBuggy.objects.create(golfcourse=staff.golfcourse,buggy=BUGGY_4_SEAT)
		query = GolfCourseBuggy.objects.filter(golfcourse=staff.golfcourse)
		serializer = GolfCourseBuggySerializer(query)
		return Response({'status': '200', 'code': 'SUCCESS',
							 'detail': serializer.data}, status=200)
	@staticmethod
	def post(request, key=None):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		data = request.DATA
		gc = staff.golfcourse
		if data is None:
				return Response({"code" : "E_NOT_FOUND", "detail" : "Not found"}, status=400)
		id_list = [d['buggy_id'] for d in data if 'buggy_id' in d.keys() and d['buggy_id']]
		GolfCourseBuggy.objects.filter(golfcourse=gc).exclude(pk__in=id_list).delete()
		for d in data:
				try:
						buggy_id = d.get('buggy_id',None)
						buggy = d['buggy']
						price_9 = d['price_9'] if d['price_9'] is not None and d['price_9'] > 0 else 0
						price_18 = d['price_18'] if d['price_18'] is not None and d['price_18'] > 0 else 0
						price_27 = d['price_27'] if d['price_27'] is not None and d['price_27'] > 0 else 0
						price_36 = d['price_36'] if d['price_36'] is not None and d['price_36'] > 0 else 0
						price_standard_9 = d.get('price_standard_9',None)
						price_standard_18 = d.get('price_standard_18',None)
						price_standard_27 = d.get('price_standard_27',None)
						price_standard_36 = d.get('price_standard_36',None)
						from_date = d.get('from_date',datetime.datetime.today().date())
						to_date = d.get('to_date',datetime.datetime.today().date())
						result = fn_update_buggy_price(buggy_id,buggy,price_9,price_18,price_27,price_36,price_standard_9,
													price_standard_18,price_standard_27,price_standard_36,gc,from_date, to_date)
						if not result:
								return Response({"code" : "E_NOT_FOUND", "detail" : "Not found"}, status=400)
				except KeyError:
						return Response({"code" : "E_NOT_FOUND", "detail" : "Not found"}, status=400)
		return Response({'status': '200', 'code': 'OK',
								 'detail': 'OK'}, status=200)

class GolfCourseCaddyViewSet(APIView):
	""" Viewset handle for requesting buggy information
	"""
	serializer_class = GolfCourseCaddySerializer
	permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly, )
	parser_classes = (JSONParser, FormParser,)
	@staticmethod
	def get(request, format=None):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		query = GolfCourseCaddy.objects.filter(golfcourse=staff.golfcourse)
		if not query.exists():
				GolfCourseCaddy.objects.create(golfcourse=staff.golfcourse)
		query = GolfCourseCaddy.objects.filter(golfcourse=staff.golfcourse)
		serializer = GolfCourseCaddySerializer(query)
		return Response({'status': '200', 'code': 'SUCCESS',
							 'detail': serializer.data}, status=200)
	@staticmethod
	def post(request, key=None):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		data = request.DATA
		gc = staff.golfcourse
		if data is None:
				return Response({"code" : "E_NOT_FOUND", "detail" : "Not found"}, status=400)
		try:
				price_9 = data['price_9'] if data['price_9'] is not None and data['price_9'] > 0 else 0
				price_18 = data['price_18'] if data['price_18'] is not None and data['price_18'] > 0 else 0
				price_27 = data['price_27'] if data['price_27'] is not None and data['price_27'] > 0 else 0
				price_36 = data['price_36'] if data['price_36'] is not None and data['price_36'] > 0 else 0
				result = fn_update_caddy_price(price_9,price_18,price_27,price_36,gc)
				if not result:
						return Response({"code" : "E_NOT_FOUND", "detail" : "Not found"}, status=400)
		except KeyError:
				return Response({"code" : "E_NOT_FOUND", "detail" : "Not found"}, status=400)
		return Response({'status': '200', 'code': 'OK',
								 'detail': 'OK'}, status=200)