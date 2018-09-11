from core.golfcourse.models import GolfCourseStaff
from core.teetime.models import DealEffective_TeeTime,BookingTime,Deal,TimeRangeType,DealEffective_TimeRange,TeeTime
from api.dealMana.serializers import DealEffective_TeeTimeSerializer, BookingTimeSerializer, TimeRangeTypeSerializer, DealSerializer,DealEffective_TimeRangeSerializer
from api.dealMana.serializers import UnEffectTeeTimeSerializer,DealEffective_TeeTimeSerializer
from utils.rest.permissions import UserIsOwnerOrReadOnly
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from rest_framework.permissions import IsAuthenticated
from utils.django.models import get_or_none
from api.dealMana.tasks import parse_time, parse_date, validate_deal
import datetime
from django.http import Http404
from django.db.models import Q
from pytz import timezone, country_timezones

class GolfCourseTimeRangeViewSet(APIView):
	serializer_class = TimeRangeTypeSerializer
	permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly, )
	parser_classes = (JSONParser, FormParser,)
	def get_object(self, pk=None,golfcourse=None,from_time=None,to_time=None,deal=None):
		try:
			if pk:
				return TimeRangeType.objects.get(pk=pk)
			elif not deal:
				return TimeRangeType.objects.filter(golfcourse=golfcourse)
			else:
				return TimeRangeType.objects.filter(golfcourse=golfcourse,deal=deal)
		except:
			return None

	def get(self, request, format=None):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		deal_id = request.QUERY_PARAMS.get('id')
		query = self.get_object(golfcourse=staff.golfcourse, deal=deal_id).order_by('id')
		serializer = TimeRangeTypeSerializer(query)
		return Response({'status': '200', 'code': 'SUCCESS',
							 'detail': serializer.data or []}, status=200)

	def post(self, request, key=None):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
			return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		data = request.DATA
		gc = staff.golfcourse
		if not data:
			return Response({"code" : "E_NOT_FOUND", "detail" : "Empty data input"}, status=400)
		lq = []
		deal_id = None
		d = data[0]
		if 'deal_id' in d.keys() and d['deal_id']:
			deal_id = Deal.objects.get(pk=d['deal_id'])
		if not deal_id:
			return Response({"code" : "E_NOT_FOUND", "detail" : "Empty data input"}, status=400)
		deal_id.deal.all().delete()
		for d in data:
			query, created = TimeRangeType.objects.get_or_create(type_name=d['type_name'], golfcourse=staff.golfcourse, deal=deal_id)
			query.from_time = parse_time(d['from_time']) or query.from_time
			query.to_time = parse_time(d['to_time']) or query.to_time
			query.save()
			lq.append(query)
		lq = sorted(lq, key=lambda w: w.id)
		#query = self.get_object(golfcourse=staff.golfcourse)
		serializer = TimeRangeTypeSerializer(lq)
		return Response({'status': '200', 'code': 'UPDATE/CREATE SUCCESS',
							 'detail': serializer.data or []}, status=200)

class GolfCourseTimeRangeDetailSet(APIView):
	serializer_class = TimeRangeTypeSerializer
	permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly, )
	parser_classes = (JSONParser, FormParser,)
	def get_object(self, pk):
		try:
			return TimeRangeType.objects.get(pk=pk)
		except TimeRangeType.DoesNotExist:
			raise Http404
	def check_valid_timerange_type_to_delete(self,pk):
		query = DealEffective_TimeRange.objects.values_list('id', flat=True).filter(timerange__id = pk.id, bookingtime__deal__active = True)
		if query:
			if DealEffective_TeeTime.objects.filter(timerange__in=set(query)).exists():
				return False
			else:
				return True
		else:
			return True
	def delete(self, request, pk, format=None):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		query = self.get_object(pk=pk)
		if query:
			if self.check_valid_timerange_type_to_delete(query):
				query.delete()
			else:
				return Response({'status': '400', 'code': 'DELETE FAIL', 'detail': 'This timerange type have exist teetime in active deeal. Please stop deal first'}, status=400)		
		return Response({'status': '200', 'code': 'DELETE SUCCESS'}, status=200)
	def put(self, request, pk, format=None):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		query = self.get_object(pk=pk)
		data = request.DATA
		if data is None:
			return Response({"code" : "E_NOT_FOUND", "detail" : "Empty data input"}, status=400)
		query.from_time = parse_time(data['from_time']) or query.from_time
		query.to_time = parse_time(data['to_time']) or query.to_time
		query.type_name = data['type_name']
		deal_id = None
		if 'deal_id' in data.keys() and data['deal_id']:
			deal_id = Deal.objects.get(pk=data['deal_id'])
		query.deal = deal_id
		query.save()
		serializer = TimeRangeTypeSerializer(query)
		return Response({'status': '200', 'code': 'UPDATE/CREATE SUCCESS',
							 'detail': serializer.data}, status=200)

class GolfCourseDealViewSet(APIView):
	serializer_class = DealSerializer
	permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly, )
	parser_classes = (JSONParser, FormParser,)

	def get_object(self, pk=None,deal_code=None,golfcourse=None,from_time=None,to_time=None):
		try:
			if pk:
				return Deal.objects.get(pk=pk)
			elif golfcourse:
				return Deal.objects.filter(golfcourse=golfcourse)
			elif deal_code:
				return get_or_none(Deal,deal_code=deal_code)
		except:
			return None
	def get(self, request, format=None):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		query = self.get_object(golfcourse=staff.golfcourse)
		serializer = DealSerializer(query)
		return Response({'status': '200', 'code': 'SUCCESS',
							 'detail': serializer.data or []}, status=200)


	@staticmethod
	def post(request, key=None):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		data = request.DATA
		gc = staff.golfcourse
		if data is None:
				return Response({"code" : "E_NOT_FOUND", "detail" : "Empty data input"}, status=400)
		lq = []
		for d in data:
			#if 'is_base' in d.keys() and d['is_base']:
			#	query = get_or_none(Deal, golfcourse=staff.golfcourse, active=True, is_base=True)
			#	if query and query.deal_code != d['deal_code']:
			#		return Response({'status': '400', 'code': 'EXIST DEAL',
			#				'detail': 'Cannot update'}, status=400)
			query, created = Deal.objects.get_or_create(deal_code=d['deal_code'], golfcourse=staff.golfcourse)
			if not query.active and query.end_date and not query.is_base:
				serializer = DealSerializer(query)
				return Response({'status': '400', 'code': 'CANNOT UPDATE ENDED DEAL',
							 'detail': serializer.data}, status=400)

			for k in d.keys():
				if 'end_date' in k or 'end_time' in k or 'active' in k:
					continue
				elif 'time' in k:
					setattr(query,k,parse_time(d[k]))
				elif 'date' in k:
					setattr(query,k,parse_date(d[k]))
				else:
					setattr(query,k,d[k])
			query.save()
			query = validate_deal(query)
			lq.append(query)
		serializer = DealSerializer(lq)
		return Response({'status': '200', 'code': 'UPDATE/CREATE SUCCESS',
							 'detail': serializer.data}, status=200)
class GolfCourseDealDetailSet(APIView):
	serializer_class = DealSerializer
	permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly, )
	parser_classes = (JSONParser, FormParser,)
	def get_object(self, pk):
		try:
			return Deal.objects.get(pk=pk)
		except Deal.DoesNotExist:
			raise Http404
	def delete(self, request, pk, format=None):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		query = self.get_object(pk=pk)
		if query:
			query.delete()
		return Response({'status': '200', 'code': 'DELETE SUCCESS'}, status=200)
	def put(self, request, pk, format=None):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		query = self.get_object(pk=pk)
		query = validate_deal(query)
		data = request.DATA
		if data is None:
			return Response({"code" : "E_NOT_FOUND", "detail" : "Empty data input"}, status=400)
		#Deal not active and have end_date: DEAL ENDED
		if not query.active and query.end_date:
			serializer = DealSerializer(query)
			return Response({'status': '400', 'code': 'CANNOT UPDATE ENDED DEAL',
							 'detail': serializer.data}, status=400)
		else:
			deal_status = query.active
			for k in data.keys():
				if 'end_date' in k or 'end_time' in k:
					continue
				elif 'time' in k:
					setattr(query,k,parse_time(data[k]))
				elif 'date' in k:
					setattr(query,k,parse_date(data[k]))
				else:
					setattr(query,k,data[k])
			#Last active, now deactive: STOP DEAL
			if not query.active and deal_status:
				query.end_date = datetime.datetime.today()
				query.end_time = datetime.datetime.now().time()
			query.save()
			serializer = DealSerializer(query)
			return Response({'status': '200', 'code': 'UPDATE/CREATE SUCCESS',
							'detail': serializer.data}, status=200)


class GolfCourseDealBookingViewSet(APIView):
	serializer_class = BookingTimeSerializer
	permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly, )
	parser_classes = (JSONParser, FormParser,)
	def get_object(self, pk=None,deal=None,golfcourse=None,from_time=None,to_time=None):
		try:
			if pk:
				return BookingTime.objects.get(pk=pk)
			elif deal:
				return BookingTime.objects.filter(deal=deal)
		except:
			return None
	def get(self, request):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		deal_id = request.QUERY_PARAMS.get('id')
		bookingtime = self.get_object(deal=deal_id)
		serializer = BookingTimeSerializer(bookingtime)
		return Response({'status': '200', 'code': 'SUCCESS',
							 'detail': serializer.data or []}, status=200)
	def get_dealteetime(self, pk=None,bookingtime=None,timerange=None):
		try:
			if pk:
				return DealEffective_TeeTime.objects.get(pk=pk)
			elif timerange:
				teetimes = DealEffective_TeeTime.objects.filter(timerange=timerange)
				teetimes = sorted(teetimes, key=lambda w: w.teetime.time)
				return teetimes
		except:
			return []
	def get_teetime(self,timerange=None):
		try:
			tr = get_or_none(DealEffective_TimeRange,pk=timerange)
			if not tr:
				return []
			from_time = tr.timerange.from_time
			to_time = tr.timerange.to_time
			golfcourse = tr.timerange.golfcourse
			date = tr.date
			filter_condition = {
				'date': date,
				'time__gte': from_time, 'time__lte': to_time,
				'golfcourse_id': golfcourse
			}
			arguments = {}
			for k, v in filter_condition.items():
				if v:
					arguments[k] = v
			teetimes = TeeTime.objects.filter(Q(**arguments)).filter(is_block=False, is_booked=False, is_request=False, available=True)
			teetimes = sorted(teetimes, key=lambda w: w.time)
			return teetimes
		except:
			return []
	def check_and_update_deal_teetime(self,timerange):
		deal_teetime = self.get_dealteetime(timerange=timerange.id)
		if deal_teetime:
			for d in deal_teetime:
				d.hole=timerange.bookingtime.deal.hole
				d.discount = timerange.discount
				d.save()
			return
		else:
			teetime = self.get_teetime(timerange=timerange.id)
			if not teetime:
				return
			for tt in teetime:
				d, created = DealEffective_TeeTime.objects.get_or_create(bookingtime=timerange.bookingtime,teetime=tt)
				d.timerange = timerange.id
				d.hole=timerange.bookingtime.deal.hole
				d.discount = timerange.discount
				d.save()
	def post(self, request):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		data = request.DATA
		gc = staff.golfcourse
		if data is None:
				return Response({"code" : "E_NOT_FOUND", "detail" : "Empty data input"}, status=400)
		for d in data:
			deal = get_or_none(Deal, pk=d['id'])
			if not deal:
				return Response({"code" : "E_NOT_FOUND", "detail" : "Deal not found"}, status=400)
			query, created = BookingTime.objects.get_or_create(date=parse_date(d['date']), deal=deal, from_time=parse_time(d['from_time']),to_time=parse_time(d['to_time']))
			if 'timerange' in d.keys() and d['timerange']:
				for t in d['timerange']:
					tr = get_or_none(TimeRangeType, pk=t['timerange'])
					if not tr:
						return Response({"code" : "E_NOT_FOUND", "detail" : "Not found Time range"}, status=400)
					q,c = DealEffective_TimeRange.objects.get_or_create(bookingtime=query, timerange=tr, date=parse_date(t['date']))
					q.discount = t['discount']
					q.save()
					if not deal.is_base:
						self.check_and_update_deal_teetime(q)
			query.save()
		bookingtime = self.get_object(deal=deal)
		serializer = BookingTimeSerializer(bookingtime)
		return Response({'status': '200', 'code': 'UPDATE/CREATE SUCCESS',
							 'detail': serializer.data}, status=200)

class GolfCourseDealBookingDetail(APIView):
	serializer_class = BookingTimeSerializer
	permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly, )
	parser_classes = (JSONParser, FormParser,)
	def get_object(self, pk=None,deal=None,golfcourse=None,from_time=None,to_time=None):
		try:
			if pk:
				return BookingTime.objects.get(pk=pk)
			elif deal:
				return BookingTime.objects.filter(deal=deal)
		except:
			return None
	def delete(self, request, pk, format=None):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		query = self.get_object(pk=pk)
		if query:
			query.delete()
		return Response({'status': '200', 'code': 'DELETE SUCCESS'}, status=200)
	def get_dealteetime(self, pk=None,bookingtime=None,timerange=None):
		try:
			if pk:
				return DealEffective_TeeTime.objects.get(pk=pk)
			elif timerange:
				teetimes = DealEffective_TeeTime.objects.filter(timerange=timerange)
				teetimes = sorted(teetimes, key=lambda w: w.teetime.time)
				return teetimes
		except:
			return []
	def get_teetime(self,timerange=None):
		try:
			tr = get_or_none(DealEffective_TimeRange,pk=timerange)
			if not tr:
				return []
			from_time = tr.timerange.from_time
			to_time = tr.timerange.to_time
			golfcourse = tr.timerange.golfcourse
			date = tr.date
			filter_condition = {
				'date': date,
				'time__gte': from_time, 'time__lte': to_time,
				'golfcourse_id': golfcourse
			}
			arguments = {}
			for k, v in filter_condition.items():
				if v:
					arguments[k] = v
			teetimes = TeeTime.objects.filter(Q(**arguments)).filter(is_block=False, is_booked=False, is_request=False, available=True)
			teetimes = sorted(teetimes, key=lambda w: w.time)
			return teetimes
		except:
			return []
	def check_and_update_deal_teetime(self,timerange):
		deal_teetime = self.get_dealteetime(timerange=timerange.id)
		if deal_teetime:
			for d in deal_teetime:
				d.hole=timerange.bookingtime.deal.hole
				d.discount = timerange.discount
				d.save()
			return
		else:
			teetime = self.get_teetime(timerange=timerange.id)
			if not teetime:
				return
			for tt in teetime:
				d, created = DealEffective_TeeTime.objects.get_or_create(bookingtime=timerange.bookingtime,teetime=tt)
				d.timerange = timerange.id
				d.hole=timerange.bookingtime.deal.hole
				d.discount = timerange.discount
				d.save()
	def put(self, request, pk, format=None):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		query = self.get_object(pk=pk)
		data = request.DATA
		query.date = parse_date(data['date'])
		query.from_time = parse_time(data['from_time'])
		query.to_time = parse_time(data['to_time'])
		if 'timerange' in data.keys() and data['timerange']:
			for t in data['timerange']:
				tr = get_or_none(TimeRangeType, pk=t['timerange'])
				if not tr:
					return Response({"code" : "E_NOT_FOUND", "detail" : "Not found Time range"}, status=400)
				q,c = DealEffective_TimeRange.objects.get_or_create(bookingtime=query, timerange=tr, date=parse_date(t['date']))
				q.discount = t['discount']
				q.save()
				if not q.bookingtime.deal.is_base:
					self.check_and_update_deal_teetime(q)
		query.save()
		serializer = BookingTimeSerializer(query)
		return Response({'status': '200', 'code': 'UPDATE/CREATE SUCCESS',
							 'detail': serializer.data}, status=200)

class GolfCourseDealTeeTimeViewSet(APIView):
	serializer_class = DealEffective_TeeTimeSerializer
	permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly, )
	parser_classes = (JSONParser, FormParser,)
	def get_object(self, pk=None,bookingtime=None,timerange=None):
		try:
			if pk:
				return DealEffective_TeeTime.objects.get(pk=pk)
			elif timerange:
				teetimes = DealEffective_TeeTime.objects.filter(timerange=timerange)
				teetimes = sorted(teetimes, key=lambda w: w.teetime.time)
				return teetimes
		except:
		    return []
	def get_teetime(self,bookingtime=None,timerange=None):
		try:
			tr = get_or_none(DealEffective_TimeRange,pk=timerange)
			if not tr:
				return []
			from_time = tr.timerange.from_time
			to_time = tr.timerange.to_time
			golfcourse = tr.timerange.golfcourse
			date = tr.date
			filter_condition = {
				'date': date,
				'time__gte': from_time, 'time__lte': to_time,
				'golfcourse_id': golfcourse
			}
			arguments = {}
			for k, v in filter_condition.items():
				if v:
					arguments[k] = v
			teetimes = TeeTime.objects.filter(Q(**arguments)).filter(is_block=False, is_booked=False, is_request=False, available=True)
			teetimes = sorted(teetimes, key=lambda w: w.time)
			return teetimes
		except:
			return []
	def get(self, request):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		timerange = request.QUERY_PARAMS.get('timerange')
		dealteetime = self.get_object(timerange=timerange)
		undeal = self.get_teetime(timerange=timerange)
		serializer = DealEffective_TeeTimeSerializer(dealteetime)
		list_id = [data['id'] for data in serializer.data]
		serializer2 = UnEffectTeeTimeSerializer(undeal,timerange)
		data = [d for d in serializer2.data if not d['id'] in list_id]
		data = data + serializer.data
		return Response({'status': '200', 'code': 'SUCCESS',
							 'detail': data or []}, status=200)
	def post(self, request, key=None):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		data = request.DATA
		tr = data['timerange']
		timerange = get_or_none(DealEffective_TimeRange,pk=tr)
		if not timerange:
			return Response({'status': '400', 'code': 'E_NOT_FOUND'}, status=400)
		if 'id' in data:
			list_id = data['id']
			dealteetime = self.get_object(timerange=timerange.id)
			if dealteetime:
				for deal in dealteetime:
					if not deal.teetime.id in list_id:
						deal.delete()
			for i in list_id:
				#teetimes = TeeTime.objects.filter(Q(**arguments)).filter(is_block=False, is_booked=False, is_request=False, available=True)
				teetime = get_or_none(TeeTime,pk=i)
				if not teetime:
					continue
				d, created = DealEffective_TeeTime.objects.get_or_create(bookingtime=timerange.bookingtime,teetime=teetime)
				d.timerange=tr
				d.hole=timerange.bookingtime.deal.hole
				d.discount = timerange.discount
				d.save()
			return Response({'status': '200', 'code': 'SUCCESS'}, status=200)
		else:
			return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'Wrong parameters'}, status=401)

class DealPerGC(APIView):
	serializer_class = TimeRangeTypeSerializer
	#permission_classes = (IsAuthenticated, )
	parser_classes = (JSONParser, FormParser,)
	@staticmethod
	def get(request):
		country_code = request.QUERY_PARAMS.get('country', 'vn')
		tz = timezone(country_timezones(country_code)[0])
		now = datetime.datetime.utcnow()
		current_tz = datetime.datetime.fromtimestamp(now.timestamp(), tz)
		filter_condition = {
			'date': current_tz.date(),
			'from_time__lte': current_tz.time(), 'to_time__gte': current_tz.time()
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
				deal = DealEffective_TeeTime.objects.filter(bookingtime=bt)
				if deal.exists():
					for d in deal:
						if d.teetime.id not in deal_teetime.keys():
							count[bt.deal.golfcourse.id] = (count[bt.deal.golfcourse.id] + 1) if bt.deal.golfcourse.id in count.keys() else 1
							deal_teetime[d.teetime.id] = d
		return Response({'detail': count}, status=200)

class ImportDeal(APIView):
	serializer_class = BookingTimeSerializer
	permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly, )
	parser_classes = (JSONParser, FormParser,)
	def get_object(self, pk=None,deal=None,golfcourse=None,from_time=None,to_time=None):
		try:
			if pk:
				return BookingTime.objects.get(pk=pk)
			elif deal:
				return BookingTime.objects.filter(deal=deal)
		except:
			return None
	def check_date(self, date):
		date_valid = True
		try:
			date = datetime.datetime.strptime(date, '%d/%m/%Y').date()
				# time = datetime.datetime.strptime(obj['time'], '%H:%M')
		except Exception:
			date_valid = False
			pass
			# try again parse format example '12/9/15'
		try:                
			if date_valid is False:
				date = datetime.datetime.strptime(date, '%d/%m/%y').date()
		except Exception:
			return None
		return date
	def check_time(self,time):
		try:
			time = datetime.datetime.strptime(time, '%H:%M').time()
		except Exception:
			return None
		else:
			return time
	def get(self, request, key=None, format=None):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		bookingtime = self.get_object(deal=key)
		serializer = BookingTimeSerializer(bookingtime)
		return Response({'status': '200', 'code': 'SUCCESS',
							 'detail': serializer.data}, status=200)
	def post(self, request, key=None):
		staff = get_or_none(GolfCourseStaff, user=request.user)
		if staff is None:
				return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
							  'detail': 'You do not have permission to peform this action'}, status=401)
		data = request.DATA
		gc = staff.golfcourse
		if data is None:
				return Response({"code" : "E_NOT_FOUND", "detail" : "Empty data input"}, status=400)
		for d in data:
			booking_date = self.check_date(d['booking_date'])
			teetime_date = self.check_date(d['teetime_date'])
			from_time = self.check_time(d['from_time'])
			to_time = self.check_time(d['to_time'])
			if booking_date and teetime_date and from_time is not None and to_time is not None and d['discount']:
				pfix = str(booking_date).replace('-','')
				name = "Deal_{0}".format(pfix)
				deal,c = Deal.objects.get_or_create(golfcourse=gc,deal_code=name,effective_date=booking_date,expire_date=booking_date)
				bookingt,c2 = BookingTime.objects.get_or_create(deal=deal, date=booking_date,from_time=from_time,to_time=to_time)
				teetime = TeeTime.objects.filter(golfcourse=gc, date=teetime_date)
				if teetime.exists():
					for tt in teetime:
						deal_teetime, c3 = DealEffective_TeeTime.objects.get_or_create(bookingtime=bookingt,timerange=0,teetime=tt)
						deal_teetime.discount = d['discount']
						deal_teetime.save()
				deal.save()
				bookingt.save()
		return Response({'status': '200', 'code': 'IMPORT SUCCESS'}, status=200)
