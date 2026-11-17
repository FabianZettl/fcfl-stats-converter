"""Scale of the game and position balance of the converted EA FC / SoFIFA values (format of the PES Stats Converter), fitted on 6411 outfield players that are in the game
and in the EA FC export (the values of the game against the converter result):
1. SHIFT: ONE number per attribute for every position (scale of the game, e.g. Jump -4.8). It never depends on the position: the profile of the player stays as EA FC rates him.
2. BOOST: per position and attribute a SMALL RAISE (0 to +3, 80% of the measured difference) for the eight attributes that matter most for the position in the overall of the game (a centre-back's defensive
   attributes, a striker's finishing): the game rates them higher than the converter. Values are NEVER lowered because of the position (a defender keeps his offensive
   values, a striker his defensive ones). Position 11 (SS) uses the forwards.
Implied overall against the game by position: within about +-1.6 (centre-backs without the boost -4.2)."""
SHIFT = {"OffensiveAwareness":-2.82,"BallControl":-0.66,"Dribbling":-1.21,"TightPossession":-2.66,"LowPass":-0.86,"LoftedPass":-0.08,"Finishing":-1.36,"Heading":-3.16,"PlaceKicking":-1.25,"Curl":-0.47,"Speed":0.72,"Acceleration":-0.3,"KickingPower":0.21,"Jump":-4.82,"PhysicalContact":-2.17,"Balance":-3.51,"Stamina":1.06,"DefensiveAwareness":-2.28,"BallWinning":-1.8,"Aggression":-0.69}
BOOST = {"1":{"Heading":3.0,"Speed":0.82,"Jump":2.73,"PhysicalContact":2.84,"Stamina":0.61,"DefensiveAwareness":3.0,"BallWinning":3.0,"Aggression":3.0},"2":{"LoftedPass":0.16,"Speed":0.94,"Acceleration":0.29,"Stamina":0.57},"3":{"Dribbling":0.2,"LoftedPass":0.09,"Speed":0.85,"Acceleration":0.25,"Stamina":0.82},"4":{"BallControl":0.19,"LowPass":1.95,"LoftedPass":1.05,"PhysicalContact":0.37,"Stamina":0.25},"5":{"BallControl":1.15,"TightPossession":1.51,"LowPass":2.51,"LoftedPass":1.17},"6":{"OffensiveAwareness":0.08,"BallControl":0.93,"Dribbling":2.18,"TightPossession":1.77,"LoftedPass":0.37,"Acceleration":0.37},"7":{"BallControl":0.8,"Dribbling":1.89,"TightPossession":1.36,"LoftedPass":0.45,"Stamina":0.09},"8":{"OffensiveAwareness":0.45,"BallControl":1.94,"Dribbling":1.22,"TightPossession":2.99,"LowPass":2.04,"LoftedPass":0.52},"9":{"OffensiveAwareness":1.15,"BallControl":0.89,"Dribbling":2.41,"TightPossession":2.12,"Finishing":0.25,"Acceleration":0.46},"10":{"OffensiveAwareness":1.07,"BallControl":0.9,"Dribbling":2.47,"TightPossession":1.96,"Finishing":0.41,"Acceleration":0.2},"11":{"OffensiveAwareness":2.62,"BallControl":0.41,"Dribbling":1.01,"TightPossession":0.72,"Finishing":2.09,"Acceleration":0.18},"12":{"OffensiveAwareness":3.0,"Finishing":3.0,"PhysicalContact":0.35}}


def correct(pos, attr, v):
    """-> (value, change by the scale, change by the position)"""
    sh = SHIFT.get(attr)
    if sh is None:
        return v, 0, 0
    a = max(40, min(99, int(round(v + sh))))
    bo = (BOOST.get(str(pos)) or {}).get(attr, 0)
    b = max(40, min(99, int(round(v + sh + bo))))
    return b, a - v, b - a
