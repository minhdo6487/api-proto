__author__ = 'toantran'

from celery import shared_task
from core.game.models import Game, Score,Hole
from utils.rest.handicap import handicap36, normal_handicap, course_handicap, adjusted_gross_scores, \
    handicap_differential, handicap_index, \
    Callaway, StableFord, Peoria

@shared_task
def async_calculate_game(game_id,hdcus=False, callaway=False, stable_ford=False, peoria=False, system36=False,
                           normal=False, hdc_net=False):
    g = Game.objects.get(id=game_id)
    handicap = g.handicap
    scores = g.score.all().only('tee_type')[:1]
    strokes = list(Score.objects.filter(game_id=g.id).values_list('stroke', flat=True))
    #strokes = []

    # for score in scores:
    #     strokes.append(score.stroke)
    #     pars.append(score.hole.par)
    if not scores or not scores[0].tee_type:
    	return True
    tee_type = scores[0].tee_type
    pars = list(Hole.objects.filter(subgolfcourse_id=tee_type.subgolfcourse_id).values_list('par', flat=True))
    slope_rating = tee_type.slope
    course_rating = tee_type.rating
    gross = sum(strokes)
    user = g.event_member.user
    if handicap:
        hdc_us = handicap
    else:
        if not user:
            hdc_us = 40
        else:
            if user.user_profile.handicap_us:
                hdc_us = float(user.user_profile.handicap_us)
            else:
                user.user_profile.handicap_us = 40
                user.user_profile.save(update_fields=['handicap_us'])
                hdc_us = float(user.user_profile.handicap_us)

    # Compute 'hdcus'
    if hdcus:
        course_hdc = course_handicap(hdc_us, slope_rating)
        g.adj, adjust_stroke = adjusted_gross_scores(strokes, course_hdc, pars)
        g.hdc_us = handicap_differential(g.adj, hdc_us, pars, course_rating,slope_rating)
    if not g.handicap:
        g.handicap = 0
    # Compute 'callaway'
    if callaway:
        c = Callaway()
        g.hdc_callaway = c.calculate(strokes, pars)

    # Compute 'stable_ford'
    if stable_ford:
        s = StableFord()
        g.hdc_stable_ford = s.calculate(strokes, pars)

    # Compute 'peoria'
    if peoria:
        if g.event_member.event and g.event_member.event.bonus_par.exists():
            p = Peoria()
            bonus_pars = g.event.bonus_par.all()
            special = []
            i = 0
            for b in bonus_pars:
                if b.par == 1:
                    special.append(i)
                i += 1
            g.hdc_peoria = p.calculate(strokes, pars, special)

    # Compute 'system36'
    if system36:
        hdc_36 = handicap36(strokes, pars)
        g.handicap_36 = hdc_36
        g.hdc_36 = gross - hdc_36

    # Compute normalgroup_link
    if normal:
        hdcp = normal_handicap(strokes, pars)
        if handicap:
            hdcp = hdcp - handicap
        g.hdcp = hdcp

    #Compute hdc net

    if hdc_net:
        g.hdc_net = gross - g.handicap
    # Compute gross
    g.gross_score = gross

    # Save object
    g.save()
