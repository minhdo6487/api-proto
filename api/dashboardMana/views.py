from  datetime import datetime, timedelta,timezone
from utils.rest.permissions import UserIsOwnerOrReadOnly
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from utils.django.models import get_or_none
from django.db.models import Count,Sum
from core.teetime.models import TeeTime
from collections import Counter
from django.contrib.auth.models import User
from core.playstay.models import BookedPackageTour
from core.booking.models import BookedPartner,BookedTeeTime,BookedBuggy
from api.bookingMana.views import get_gc24_booked_teetime_price

class TimeRange(object):
	from_date = datetime.today()
	to_date = datetime.today()
	prev_from_date = datetime.today()
	prev_to_date = datetime.today()


def get_previous_timerange(from_date,to_date):
	# check if date range is  month
	time_range = TimeRange()
	time_range.from_date = from_date
	time_range.to_date = to_date
	delta = to_date - from_date 

	time_range.prev_from_date = time_range.from_date - timedelta(days=delta.days+1)
	time_range.prev_to_date = time_range.from_date - timedelta(days=1)

	return time_range

def calc_trend(current,previous,positive):
	class_name = "green up"
	is_good = True
	percentage = 0
	if current+previous >0:
		percentage = float((current - previous)/(current +  previous)*100)
	if (current - previous) < 0 and positive :
		class_name = "red down"
		is_good = False
	if positive == False :
		if current - previous < 0:
			class_name = "green up"
			is_good = False
		if (current - previous) >= 0:
			class_name = "red down"
			is_good = True
	trend = {}
	trend.update({
		'previous':previous,
		'current':current,
		'is_good':is_good,
		'class_name':class_name,
		'percent':"%.1f" % percentage + "%"
	})
		
	return trend

def booking_revenue(time_range):
	
	#analysis teetime booking
	booked_teetimes = BookedTeeTime.objects.filter(created__range=(time_range.from_date, time_range.to_date)).all()
	prev_booked_teetimes = BookedTeeTime.objects.filter(created__range=(time_range.prev_from_date, time_range.prev_to_date)).all()

	current_teetime_revenue = sum(value.total_cost for value in booked_teetimes )
	prev_teetime_revenue = sum(value.total_cost for value in prev_booked_teetimes )
	
	

	teetime_booking={}
	teetime_booking_trend = calc_trend(current_teetime_revenue,prev_teetime_revenue,True)
	teetime_booking.update({
		'currency_code':"VND",
		'current':current_teetime_revenue,
		'trend':teetime_booking_trend
		})

 	#analysis package_booking
	# booked_packages = BookedPackageTour.objects.filter(date_created__range=(time_range.from_date, time_range.to_date))
	# current_packaged_revenue = sum(value.total_cost for value in booked_packages)
	# prev_booked_packages = BookedPackageTour.objects.filter(date_created__range=(time_range.prev_from_date, time_range.prev_to_date))
	# prev_packaged_revenue = sum(value.total_cost for value in prev_booked_packages)
	current_packaged_revenue = 0
	prev_packaged_revenue = 0
	package_booking={}
	package_booking_trend = calc_trend(current_packaged_revenue,prev_packaged_revenue,True)
	package_booking.update({
		'currency_code':"VND",
		'current':current_packaged_revenue,
		'trend':package_booking_trend
		})

	#analysis lost_rev
	lost_teetimes = BookedTeeTime.objects.filter(created__range=(time_range.from_date, time_range.to_date) ).all()
	prev_lost_teetimes = BookedTeeTime.objects.filter(created__range=(time_range.prev_from_date, time_range.prev_to_date)).all()

	current_teetime_lost = sum(value.total_cost for value in lost_teetimes if value.status=='C' )
	prev_teetime_lost = sum(value.total_cost for value in prev_booked_teetimes if value.status=='C')

	lost_rev={}
	lost_rev.update({
		'currency_code':"VND",
		'current':current_teetime_lost,
		'trend':calc_trend(current_teetime_lost,prev_teetime_lost,False)
		})

 	#summary data for booking revenue
	booking_rev = {}
	current_revenue = current_teetime_revenue+current_packaged_revenue
	prev_revenue = prev_teetime_revenue + prev_packaged_revenue
	
	booking_rev.update({
 		'currency_code':"VND",
 		'current':current_revenue,
 		'trend':calc_trend(current_revenue,prev_revenue,True),
 		'teetime_booking':teetime_booking,
 		'package_booking':package_booking,
 		'lost_rev':lost_rev
 		})

	return booking_rev

def booking_revenue_by_channel(time_range):
	#get teetime booking
	booked_teetimes = BookedTeeTime.objects.filter(created__range=(time_range.from_date, time_range.to_date)).all()
	prev_booked_teetimes = BookedTeeTime.objects.filter(created__range=(time_range.prev_from_date, time_range.prev_to_date)).all()

	#booking via website
	current_web_revenue = sum(value.total_cost for value in booked_teetimes if value.user_device=='web')
	prev_web_revenue = sum(value.total_cost for value in prev_booked_teetimes if  value.user_device=='web')
	web_quantity  = sum(value and value.user_device=='web' for value in booked_teetimes)
	
	web_rev={}
	web_rev.update({
		'currency_code':"VND",
		'current':current_web_revenue,
		'quantity':web_quantity,
		'trend':calc_trend(current_web_revenue,prev_web_revenue,True)
		})
	#booking via ios
	ios_rev = {}
	current_ios_revenue = sum(value.total_cost for value in booked_teetimes if value.user_device=='ios')
	prev_ios_revenue = sum(value.total_cost for value in prev_booked_teetimes  if value.user_device=='ios')
	ios_quantity  = sum(value and value.user_device=='ios' for value in booked_teetimes)

	ios_rev={}
	ios_rev.update({
		'currency_code':"VND",
		'current':current_ios_revenue,
		'quantity':ios_quantity,
		'trend':calc_trend(current_ios_revenue,prev_ios_revenue,True)
		})
	#booking via android
	android_rev = {}
	current_android_revenue = sum(value.total_cost for value in booked_teetimes if value.user_device=='and')
	prev_android_revenue = sum(value.total_cost for value in prev_booked_teetimes if value.user_device=='and')
	android_quantity  = sum(value and value.user_device=='and' for value in booked_teetimes)

	android_rev={}
	android_rev.update({
		'currency_code':"VND",
		'current':current_android_revenue,
		'quantity':android_quantity,
		'trend':calc_trend(current_android_revenue,prev_android_revenue,True)
		})
	#summary data for booking revenue by channel
	rev_by_channel = {}
	rev_by_channel.update({
 		'currency_code':"VND",
 		'current':0,
 		'trend':"",
 		'web_rev':web_rev,
 		'ios_rev':ios_rev,
 		'android_rev':android_rev
 		})

	return rev_by_channel

def booking_round(time_range):
	#get teetime booking
	booked_teetimes = BookedTeeTime.objects.filter(created__range=(time_range.from_date, time_range.to_date)).all()
	prev_booked_teetimes = BookedTeeTime.objects.filter(created__range=(time_range.prev_from_date, time_range.prev_to_date)).all()

	#booking week day
	current_weekday_round = sum(value.teetime.date and value.teetime.date.weekday()<5 for value in booked_teetimes )
	prev_weekday_round = sum(value.teetime.date and value.teetime.date.weekday()<5  for value in prev_booked_teetimes )
	
	booking_weekday_rounds={}
	booking_weekday_rounds.update({
		'currency_code':"VND",
		'current':0,
		'quantity':current_weekday_round,
		'trend':calc_trend(current_weekday_round,prev_weekday_round,True)
		})
	#booking weekenday
	current_weekend_round = sum(value.teetime.date and value.teetime.date.weekday()>=5 for value in booked_teetimes )
	prev_weekend_round = sum(value.teetime.date and value.teetime.date.weekday()>=5  for value in prev_booked_teetimes )
	
	booking_weekend_rounds={}
	booking_weekend_rounds.update({
		'currency_code':"VND",
		'current':0,
		'quantity':current_weekend_round,
		'trend':calc_trend(current_weekend_round,prev_weekend_round,True)
		})
	
	#summary data for booking rounds
	current_round=current_weekday_round+current_weekend_round
	previous_round=prev_weekday_round+prev_weekend_round;
	booking_rounds={}
	booking_rounds.update({
		'currency_code':"VND",
		'current':0,
		'quantity':current_round,
		'booking_weekday_rounds':booking_weekday_rounds,
		'booking_weekend_rounds':booking_weekend_rounds,
		'trend':calc_trend(current_round,previous_round,True)
		})

	return booking_rounds

def booking_type(time_range):
	#get teetime booking
	booked_teetimes = BookedTeeTime.objects.filter(created__range=(time_range.from_date, time_range.to_date)).all()
	prev_booked_teetimes = BookedTeeTime.objects.filter(created__range=(time_range.prev_from_date, time_range.prev_to_date)).all()

	#booking paid online and to be played
	current_on_tobe_revenue = sum(value.total_cost for value in booked_teetimes if value.payment_type=='F' and value.status!='I')
	prev_on_tobe_revenue = sum(value.total_cost for value in prev_booked_teetimes if value.payment_type=='F' and value.status!='I')
	on_tobe_quantity  = sum(value and value.payment_type=='F'  and value.status!='I' for value in booked_teetimes)
	
	on_tobe_rev={}
	on_tobe_rev.update({
		'currency_code':"VND",
		'current':current_on_tobe_revenue,
		'quantity':on_tobe_quantity,
		'trend':calc_trend(current_on_tobe_revenue,prev_on_tobe_revenue,True)
		})
	#booking paid online and played
	current_on_played_revenue = sum(value.total_cost for value in booked_teetimes if  value.payment_type=='F' and value.status=='I')
	prev_on_played_revenue = sum(value.total_cost for value in prev_booked_teetimes if value.payment_type=='F' and value.status=='I')
	on_played_quantity  = sum(value and value.payment_type=='F'  and value.status=='I' for value in booked_teetimes)
	
	on_played_rev={}
	on_played_rev.update({
		'currency_code':"VND",
		'current':current_on_played_revenue,
		'quantity':on_played_quantity,
		'trend':calc_trend(current_on_played_revenue,prev_on_played_revenue,True)
		})

	#booking online analysis
	online_rev={}
	on_quatity = on_tobe_quantity+on_played_quantity
	current_on_rev = current_on_played_revenue+current_on_tobe_revenue
	prev_on_rev = prev_on_tobe_revenue+prev_on_played_revenue
	online_rev.update({
		'currency_code':"VND",
		'current':current_on_rev,
		'quantity':on_quatity,
		'on_tobe_rev':on_tobe_rev,
		'on_played_rev':on_played_rev,
		'trend':calc_trend(current_on_rev,prev_on_rev,True)
		})

	#booking paid LATER and to be played
	current_later_tobe_revenue = sum(value.total_cost for value in booked_teetimes if value.payment_type=='N' and value.status!='I')
	prev_later_tobe_revenue = sum(value.total_cost for value in prev_booked_teetimes if  value.payment_type=='N' and value.status!='I')
	later_tobe_quantity  = sum(value and value.payment_type=='N'  and value.status!='I' for value in booked_teetimes)
	
	later_tobe_rev={}
	later_tobe_rev.update({
		'currency_code':"VND",
		'current':current_later_tobe_revenue,
		'quantity':later_tobe_quantity,
		'trend':calc_trend(current_later_tobe_revenue,prev_later_tobe_revenue,True)
		})
	#booking paid LATER and played
	current_later_played_revenue = sum(value.total_cost for value in booked_teetimes if  value.payment_type=='N' and value.status=='I')
	prev_later_played_revenue = sum(value.total_cost for value in prev_booked_teetimes if  value.payment_type=='N' and value.status=='I')
	later_played_quantity  = sum(value and value.payment_type=='N'  and value.status=='I' for value in booked_teetimes)
	
	later_played_rev={}
	later_played_rev.update({
		'currency_code':"VND",
		'current':current_later_played_revenue,
		'quantity':later_played_quantity,
		'trend':calc_trend(current_later_played_revenue,prev_later_played_revenue,True)
		})

	#booking LATER analysis
	later_rev={}
	later_quatity = later_tobe_quantity+later_played_quantity
	current_later_rev = current_later_played_revenue+current_later_tobe_revenue
	prev_later_rev = prev_later_tobe_revenue+prev_later_played_revenue
	later_rev.update({
		'currency_code':"VND",
		'current':current_later_rev,
		'quantity':later_quatity,
		'later_tobe_rev':later_tobe_rev,
		'later_played_rev':later_played_rev,
		'trend':calc_trend(current_later_rev,prev_later_rev,True)
		})
	#booking type analysis
	booking_type_rev={}
	booking_type_quantity = later_quatity+on_quatity
	booking_type_current = current_on_rev+current_later_rev
	booking_type_prev = prev_on_rev+prev_later_rev

	booking_type_rev.update({
		'currency_code':"VND",
		'current':booking_type_current,
		'quantity':booking_type_quantity,
		'online_rev':online_rev,
		'later_rev':later_rev,
		'trend':calc_trend(booking_type_current,booking_type_prev,True)
		})

	return booking_type_rev

def booking_played(time_range):
	#get teetime booking
	booked_teetimes = BookedTeeTime.objects.filter(created__range=(time_range.from_date, time_range.to_date)).all()
	prev_booked_teetimes = BookedTeeTime.objects.filter(created__range=(time_range.prev_from_date, time_range.prev_to_date)).all()

	#round played
	current_round_quantity = booked_teetimes.count()
	prev_round_quantity = prev_booked_teetimes.count()
	
	round_quantity={}
	round_quantity.update({
		'currency_code':"VND",
		'current':0,
		'quantity':current_round_quantity,
		'trend':calc_trend(current_round_quantity,prev_round_quantity,True)
		})

	#player played
	current_player_quantity = sum(value.player_count for value in booked_teetimes )
	previous_player_quantity = sum(value.player_count for value in prev_booked_teetimes )
	
	player_quantity={}
	player_quantity.update({
		'currency_code':"VND",
		'current':0,
		'quantity':current_player_quantity,
		'trend':calc_trend(current_player_quantity,previous_player_quantity,True)
		})

	# analysis booking Played
	booking_played={}
	booking_played.update({
		'currency_code':"VND",
		'current':0,
		'trend':'',
		'round_quantity':round_quantity,
		'player_quantity':player_quantity
		})
	return booking_played

def round_cancelled(time_range):
	#get teetime booking
	booked_teetimes = BookedTeeTime.objects.filter(created__range=(time_range.from_date, time_range.to_date)).all()
	prev_booked_teetimes = BookedTeeTime.objects.filter(created__range=(time_range.prev_from_date, time_range.prev_to_date)).all()
	
	# refund amount anaylys
	current_refund_rev = sum(value.total_cost for value in booked_teetimes if value and value.status=='C' and value.payment_type=='F')
	previous_refund_rev = sum(value.total_cost for value in prev_booked_teetimes if value and value.status=='C' and value.payment_type=='F')
	refund_quantity  = sum(value  and value.status=='C' and value.payment_type=='F' for value in booked_teetimes)
	
	refund_amount={}
	refund_amount.update({
		'currency_code':"VND",
		'current':current_refund_rev,
		'quantity':0,
		'trend':calc_trend(current_refund_rev,previous_refund_rev,False)
		})
	#cancelled amount analysis
	current_cancelled_rev = sum(value.total_cost for value in booked_teetimes if value and value.status=='C')
	previous_cancelled_rev = sum(value.total_cost for value in prev_booked_teetimes if value and value.status=='C')
	cancelled_quantity  = sum(value  and value.status=='C' for value in booked_teetimes)
	previous_cancelled_quantity  = sum(value  and value.status=='C' for value in prev_booked_teetimes)
	
	cancel_amount={}
	cancel_amount.update({
		'currency_code':"VND",
		'current':current_cancelled_rev,
		'quantity':0,
		'trend':calc_trend(current_cancelled_rev,previous_cancelled_rev,False)
		})

	round_cancelled={}
	round_cancelled.update({
		'currency_code':"VND",
		'current':0,
		'quantity':cancelled_quantity,
		'trend':calc_trend(cancelled_quantity,previous_cancelled_quantity,False),
		'refund_amount':refund_amount,
		'cancel_amount':cancel_amount
		})

	return round_cancelled;

def get_top_5_golfcourse(time_range):
	# top 5 golfcourses
	current_5_golfcourse=BookedTeeTime.objects.filter(created__range=(time_range.from_date, time_range.to_date)).values('golfcourse').annotate(num_books=Count('golfcourse')).order_by('-num_books')[:5]

	top_5_course =[]
	total_round=0
	total_rev=0
	prev_rev=0
	sum_top_5_course={}
	# print(current_5_golfcourse)
	for top_course in current_5_golfcourse:
		golf_course ={}
		filterred_course = BookedTeeTime.objects.filter(created__range=(time_range.from_date, time_range.to_date),golfcourse_id=top_course['golfcourse']).all()
		current_total_cost = sum(value.total_cost for value in filterred_course if value )
		
		prev_filterred_course = BookedTeeTime.objects.filter(created__range=(time_range.prev_from_date, time_range.prev_to_date),golfcourse_id=top_course['golfcourse']).all()
		prev_total_cost = sum(value.total_cost for value in prev_filterred_course if value )
		total_round+=top_course['num_books']
		total_rev+=current_total_cost
		prev_rev+=prev_total_cost
		golf_course.update({
			'currency_code':"VND",
			'quantity':top_course['num_books'],
			'current':current_total_cost,
			'name':filterred_course[0].golfcourse.name,
			'trend':calc_trend(current_total_cost,prev_total_cost,True)
			})
		top_5_course.append(golf_course);
	sum_top_5_course.update({
		'currency_code':"VND",
		'current':total_rev,
		'quantity':total_round,
		'trend':calc_trend(total_rev,prev_rev,True),
		'golfcourses':top_5_course
		})
	return sum_top_5_course

def get_top_5_golfer(time_range):
	# top 5 golfcourses
	current_5_golfer=BookedPartner.objects.filter(bookedteetime__created__range=(time_range.from_date, time_range.to_date)).select_related(
            'booked_teetimte').values('user').annotate(num_books=Count('user')).order_by('-num_books')[:5]

	
	sum_top_5_golfer={}
	top_5_golfer=[]
	total_round=0
	total_rev=0
	prev_rev=0
	for top_golfer in current_5_golfer:
		golfer ={}
		filterred_golfer = BookedPartner.objects.filter(bookedteetime__created__range=(time_range.from_date, time_range.to_date),user=top_golfer['user'], bookedteetime__teetime__is_booked=True).select_related('booked_teetime').all()
		current_total_cost = sum(value.bookedteetime.total_cost for value in filterred_golfer if value.bookedteetime )

		pre_filterred_golfer = BookedPartner.objects.filter(bookedteetime__created__range=(time_range.prev_from_date, time_range.prev_to_date),user=top_golfer['user'], bookedteetime__teetime__is_booked=True).select_related('booked_teetime').all()
		pre_total_cost = sum(value.bookedteetime.total_cost for value in pre_filterred_golfer if value.bookedteetime )

		golfer.update({
			'currency_code':"VND",
			'quantity':top_golfer['num_books'],
			'current':current_total_cost,
			'name':filterred_golfer[0].customer.name,
		    'trend':calc_trend(current_total_cost,pre_total_cost,True)
			})
		total_round+=top_golfer['num_books']
		total_rev+=current_total_cost
		prev_rev+=pre_total_cost
		top_5_golfer.append(golfer);

	sum_top_5_golfer.update({
		'currency_code':"VND",
		'current':total_rev,
		'quantity':total_round,
		'trend':calc_trend(total_rev,prev_rev,True),
		'golfers':top_5_golfer
		})
	return sum_top_5_golfer


def get_booking_profits(time_range):
	booked_teetimes = BookedTeeTime.objects.filter(created__range=(time_range.from_date, time_range.to_date))
	current_profits = []
	current_tee_profit = 0;
	for tt in booked_teetimes:
		profit={}
		gc_unit_green_fee = get_gc_price(tt.id)
		gc_unit_buggy_fee = get_gc_buggy_price(tt.id, tt.hole)
		green_fee = gc_unit_green_fee * tt.player_checkin_count
		buggy_fee = gc_unit_buggy_fee 
		total_profit = tt.total_cost - green_fee - buggy_fee;
		current_tee_profit+=total_profit
		profit.update(
			{'gc_unit_green_fee': gc_unit_green_fee,
			'gc_unit_buggy_fee': gc_unit_buggy_fee,
			'total_cost': buggy_fee+buggy_fee,
			'paid_amount':tt.total_cost,
			'profit':total_profit
			})
		current_profits.append(profit)

	prev_booked_teetimes = BookedTeeTime.objects.filter(created__range=(time_range.prev_from_date, time_range.prev_to_date))
	prev_profits = []
	prev_tee_profit=0
	for tt in prev_booked_teetimes:
		profit={}
		gc_unit_green_fee = get_gc_price(tt.id)
		gc_unit_buggy_fee = get_gc_buggy_price(tt.id, tt.hole)
		green_fee = gc_unit_green_fee * tt.player_checkin_count
		buggy_fee = gc_unit_buggy_fee 
		total_profit = tt.total_cost - green_fee - buggy_fee;
		prev_tee_profit+=total_profit
		profit.update(
			{'gc_unit_green_fee': gc_unit_green_fee,
			'gc_unit_buggy_fee': gc_unit_buggy_fee,
			'total_cost': buggy_fee+buggy_fee,
			'paid_amount':tt.total_cost,
			'profit':total_profit
			})
		prev_profits.append(profit)



	current_ps_profit = 0
	prev_ps_profit = 0
	ps_profits = {}    
	ps_profits.update({
		'currency_code':"VND",
		'current':current_ps_profit,
		'quantity':0,
		'trend':calc_trend(current_ps_profit,prev_ps_profit,True)
	})

	teetime_profits = {}    
	teetime_profits.update({
		'currency_code':"VND",
		'current':current_tee_profit,
		'quantity':0,
		'trend':calc_trend(current_tee_profit,prev_tee_profit,True)
	})

	booking_profits = {}
	current_profit = current_ps_profit+current_tee_profit
	prev_profit = prev_tee_profit + prev_ps_profit
	booking_profits.update({
		'currency_code':"VND",
		'current':current_profit,
		'quantity':0,
		'teetime_profits':teetime_profits,
		'ps_profits':ps_profits,
		'trend':calc_trend(current_profit,prev_profit,True)
	})

	return booking_profits
def get_gc_price(booking_id):
    item = get_or_none(BookedTeeTime, pk=booking_id)
    return get_gc24_booked_teetime_price(item) if item else 0


def get_gc_buggy_price(teetime_id, hole):
    bookedbuggy = get_or_none(BookedBuggy, teetime=teetime_id)
    if bookedbuggy:
        k = "price_standard_{0}".format(str(hole))
        return getattr(bookedbuggy.buggy, k, 0)*bookedbuggy.quantity
    return 0
@api_view(['GET'])
def get_dashboard_summary(request):
	from_date = request.QUERY_PARAMS.get('from_date', '')
	to_date = request.QUERY_PARAMS.get('to_date', '')

	from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
	to_date = datetime.strptime(to_date, '%Y-%m-%d').date()

	# from_date = from_date.replace(hour=0, minute=0, second=0, tzinfo=timezone.utc)
	# to_date = to_date.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
	

	time_range=get_previous_timerange(from_date,to_date)

	results = {}
	results.update({
		'booking_revenue': booking_revenue(time_range),
		'booking_profits':get_booking_profits(time_range),
		'booking_revenue_by_channel':booking_revenue_by_channel(time_range),
		'booking_round':booking_round(time_range),
		'booking_type':booking_type(time_range),
		'booking_played':booking_played(time_range),
		'round_cancelled':round_cancelled(time_range),
		'top_5_golfcourse':get_top_5_golfcourse(time_range),
		'top_5_golfer':get_top_5_golfer(time_range),
		'from_date':time_range.from_date,
		'to_date':time_range.to_date
		})
	return Response(results, status=200)

@api_view(['GET'])
def get_activities(request):
	top_activities = []
	
	new_booking = BookedTeeTime.objects.order_by('-created')[:10]
	for booking in new_booking:
		partner = get_or_none(BookedPartner, bookedteetime=booking.id)
		user = partner.customer.name
		item = {}
		item.update({
			'date':booking.created,
			'type':"booked",
			'action':"has booked a teetime",
			'user':user
			})
		if booking.teetime.is_request == True:
			item.update({
			'date':booking.created,
			'type':"requested",
			'action':"has requested a teetime",
			'user':user
			})

		top_activities.append(item)

	cancel_booking = BookedTeeTime.objects.filter(status='C').order_by('-created')[:10]
	for booking in cancel_booking:
		partner = get_or_none(BookedPartner, bookedteetime=booking.id)
		user = partner.customer.name
		item = {}
		item.update({
			'date':booking.created,
			'type':"cancelled",
			'action':"has cancelled a booking",
			'user':user
			})
		top_activities.append(item)

	checkin_booking = BookedTeeTime.objects.filter(status='I').order_by('-created')[:10]
	for booking in checkin_booking:
		partner = get_or_none(BookedPartner, bookedteetime=booking.id)
		user = partner.customer.name
		item = {}
		item.update({
			'date':booking.created,
			'type':"checked-in",
			'action':"has checked-in",
			'user':user
			})
		top_activities.append(item)

	top_user = User.objects.order_by('-date_joined')[:10]
	for user in top_user:
		item = {}
		item.update({
			'date':user.date_joined,
			'type':"new",
			'action':"has registered",
			'user':user.first_name +" " + user.last_name
			})
		top_activities.append(item)

	now = datetime.now()
	noshow_booking = BookedTeeTime.objects.filter(payment_status=True, teetime__date__lt=now).exclude(status__in=['I', 'R']).order_by('-teetime__date')[:10]
	for booking in noshow_booking:
		partner = get_or_none(BookedPartner, bookedteetime=booking.id)
		user = partner.customer.name
		item = {}
		item.update({
			'date':booking.created,
			'type':"no-show",
			'action':"has been no-show",
			'user':user
			})
		top_activities.append(item)

	return Response(top_activities, status=200)


