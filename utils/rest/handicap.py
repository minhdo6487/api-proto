def handicap36(strokes, pars):
    # Double bogey or worse - 0 points: A double bogey is 2-over par
    # Bogey - 1 point : A bogey is 1-over par
    # Par or better - 2 points
    rounds = len(strokes)
    db_bogey = 0
    bogey = 0
    par = 0
    for i in range(0, rounds):
        if strokes[i] - pars[i] <= 0:
            par += 1
        elif strokes[i] - pars[i] == 1:
            bogey += 1
        elif strokes[i] - pars[i] > 1:
            db_bogey += 1
    handicap = 36 - 2 * par - bogey
    return handicap


def adjusted_gross_scores(strokes, handicap, pars):
    rounds = len(strokes)
    adjust_stokes = strokes.copy()
    for i in range(0, rounds):
        if handicap <= 9 and strokes[i] > (pars[i] + 2):
            adjust_stokes[i] = pars[i] + 2
        elif 10 <= handicap <= 19 and strokes[i] > 7:
            adjust_stokes[i] = 7
        elif 20 <= handicap <= 29 and strokes[i] > 8:
            adjust_stokes[i] = 8
        elif 30 <= handicap < 39 and strokes[i] > 9:
            adjust_stokes[i] = 9
        elif handicap >= 40 and strokes[i] > 10:
            adjust_stokes[i] = 10
    return sum(adjust_stokes), adjust_stokes


def handicap_differential(strokes, handicap, pars, course_rating, slope_rating):
    # Step 1: Convert Original Gross Scores to Adjusted Gross Scores
    gross_score = strokes

    # Step 2: Calculate Handicap Differentials for Each Score
    return round((gross_score - course_rating) * 113 / slope_rating, 1)


def select_handicap_differentials(handicap_differentials):
    handicap_differentials.sort()
    logging.debug(handicap_differentials)
    nums = len(handicap_differentials)
    if 5 <= nums <= 6:
        return [handicap_differentials[0]]
    elif 7 <= nums <= 8:
        return handicap_differentials[0:2]
    elif 9 <= nums <= 10:
        return handicap_differentials[0:3]
    elif 11 <= nums <= 12:
        return handicap_differentials[0:4]
    elif 13 <= nums <= 14:
        return handicap_differentials[0:5]
    elif 15 <= nums <= 16:
        return handicap_differentials[0:6]
    elif nums == 17:
        return handicap_differentials[0:7]
    elif nums == 18:
        return handicap_differentials[0:8]
    elif nums == 19:
        return handicap_differentials[0:9]
    else:
        return handicap_differentials[0:10]


import logging


def handicap_index(handicap_differentials):
    # Step 3: Select Best, or Lowest, Handicap Differentials
    best_handicap_differentials = select_handicap_differentials(handicap_differentials)

    # Step 4: Calculate the Average of the Lowest Handicap Differentials
    average = sum(best_handicap_differentials) / len(best_handicap_differentials)

    # Step 5: Multiply Average of Handicap Differentials by 0.96 or 96%
    index = average * 0.96

    # Step 6: Truncate, or Delete, Numbers to the Right of Tenths
    return float(('%.*f' % (2, index))[:-1])


def course_handicap(hdc_index, slope_rating):
    # Step 7: Calculate Course Handicap
    return round(hdc_index * (slope_rating / 113))


def normal_handicap(strokes, pars):
    return sum(strokes) - sum(pars)


class Callaway():
    # Step 0: Init callaway table
    table = {
        "72": [0, 0],
        "73": [-2, 0.5], "74": [-1, 0.5], "75": [0, 0.5],
        "76": [-2, 1], "77": [-1, 1], "78": [0, 1], "79": [1, 1], "80": [2, 1],
        "81": [-2, 1.5], "82": [-1, 1.5], "83": [0, 1.5], "84": [1, 1.5], "85": [2, 1.5],
        "86": [-2, 2], "87": [-1, 2], "88": [0, 2], "89": [1, 2], "90": [2, 2],
        "91": [-2, 2.5], "92": [-1, 2.5], "93": [0, 2.5], "94": [1, 2.5], "95": [2, 2.5],
        "96": [-2, 3], "97": [-1, 3], "98": [0, 3], "99": [1, 3], "100": [2, 3],
        "101": [-2, 3.5], "102": [-1, 3.5], "103": [0, 3.5], "104": [1, 3.5], "105": [2, 3.5],
        "106": [-2, 4], "107": [-1, 4], "108": [0, 4], "109": [1, 4], "110": [2, 4],
        "111": [-2, 4.5], "112": [-1, 4.5], "113": [0, 4.5], "114": [1, 4.5], "115": [2, 4.5],
        "116": [-2, 5], "117": [-1, 5], "118": [0, 5], "119": [1, 5], "120": [2, 5],
        "121": [-2, 5.5], "122": [-1, 5.5], "123": [0, 5.5], "124": [1, 5.5], "125": [2, 5.5],
        "126": [-2, 6], "127": [-1, 6], "128": [0, 6], "129": [1, 6], "130": [2, 6],
    }

    def calculate(self, strokes, pars):
        gross = sum(strokes)
        # Step 1: Calculate "Adjusted Gross" by applying Double-Par stroke control to all holes
        for i in range(0, len(strokes)):
            if (strokes[i] > 2 * pars[i]):
                strokes[i] = 2 * pars[i]

        # Step 2: Calculate "Adjusted Gross" by applying Double-Par stroke control to all holes
        adjust_gross = sum(strokes)
        logging.debug(adjust_gross)
        key = adjust_gross
        if adjust_gross < 72:
            key = 72
        elif adjust_gross > 130:
            key = 130
        strokes = strokes[0:15]

        # Step 3: Apply "Adjusted Gross" to the table to determine the Callaway Handicap entitlement (purple column)
        num_worst_hole = self.table[str(key)][1]
        logging.debug(num_worst_hole)
        #Step 4: Identify the worst hole(s) on the score card to determine the Callaway Handicap
        strokes.sort(reverse=True)
        round_num_worst_holes = round(num_worst_hole + 0.4)
        worst_holes = strokes[0: round_num_worst_holes]
        if round_num_worst_holes != num_worst_hole:
            worst_holes[round_num_worst_holes - 1] *= 0.5

        logging.debug(worst_holes)
        sum_worst = round(sum(worst_holes) + 0.4)
        logging.debug(sum_worst)
        # Step 5 Adjust the Callaway Handicap according to the bottom row of the chart
        bottom_minus = self.table[str(key)][0]
        sum_worst += bottom_minus
        logging.debug(bottom_minus)
        #Step 6:  Apply the adjusted Callaway Handicap to the "Gross" Score to obtain "Net"

        gross -= sum_worst

        return gross


class StableFord():
    def calculate(self, strokes, fixed):
        score = 0
        for i in range(0, len(strokes)):
            diff = strokes[i] - fixed[i]
            if diff == 1:
                score += 1
            elif diff == 0:
                score += 2
            elif diff == -1:
                score += 3
            elif diff == -2:
                score += 4
            elif diff == -3:
                score += 5
            elif diff == -4:
                score += 6
        return score


# Once the round is over, the tournament organizers announce the identities of the six secret holes.
# Player A finds those six holes on her scorecard and tallies up the total strokes for those six holes. Let's say that total is 30.
# So Player A multiples 30 by 3, which is 90.
# The golf course par is, let's say, 72. So subtract that from 90, and Player A gets 18.
# Now multiple 18 by 80-percent, which is 14 (round off).
# And that tells us that 14 is Player A's Peoria System handicap.
# Let's say Player A's gross score was 88, so subtract 14 from 88.
# And that is Player A's Peoria System net score: 88 minus 14, which is 74.

class Peoria():
    def calculate(self, strokes, pars, special):
        gross = sum(strokes)
        special_sum = 0
        for i in special:
            special_sum += strokes[i]
        if len(special) == 12:
            special_sum *= 1.5
        else:
            special_sum *= 3
        sum_pars = sum(pars)
        peoria = round((special_sum - sum_pars) * 0.8 - 0.5)

        return peoria