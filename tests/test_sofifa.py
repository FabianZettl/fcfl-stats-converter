import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv', 'lib'))
import sofifa as S

assert S.pes(80) == 80 and S.pes(79) == 79 and S.pes(78) == 79 and S.pes(77) == 78 and S.pes(70) == 75 and S.pes(0) == 40 and S.pes(99) == 99
text = """Haaland
Overall rating
91
Attacking
Crossing 55
Finishing 95
Heading accuracy 85
Short passing 70
Volleys 91
Skill
Dribbling 80
Curve 70
FK Accuracy 60
Long passing 65
Ball control 82
Movement
Acceleration 80
Sprint speed 91
Agility 70
Reactions 90
Balance 62
Power
Shot power 92
Jumping 85
Stamina 85
Strength 93
Long shots 85
Mentality
Aggression 85
Interceptions 30
Att. Position 94
Vision 68
Penalties 83
Composure 88
Defending
Defensive awareness 27
Standing tackle 40
Sliding tackle 45
Goalkeeping
GK Diving 10
GK Handling 11
GK Kicking 12
GK Positioning 13
GK Reflexes 14
"""
p = S.parse_page(text)
assert len(p) >= 33 and p['finishing'] == 95 and p['attpos'] == 94 and not S.missing(p, True)
c = S.convert(p)
assert c['Finishing'] == 93 and c['Heading'] == 85 and c['Speed'] == 91 and c['GKReach'] == 40 and all(40 <= v <= 99 for v in c.values())
g = S.convert(p, gk=True)
assert g['GKReach'] > 40 and g['Heading'] == 99 - 0 or g['Heading'] >= 85
# 'number on the next line' layout and 'number first' layout
p2 = S.parse_page("65\nCrossing\n88 Finishing\n")
assert p2 == {'crossing': 65, 'finishing': 88}
# FMInside page
fm = "Current ability\n    71 / 100\nPotential\n    75 / 100\nFirst Touch (key)\t70\nPace (preferred)\t85\nCrossing\t45\nPunching (Tendency)\t30\n"
assert S.is_fm(fm) and not S.is_fm('Crossing 65')
q = S.parse_fm(fm)
assert q['overall'] == 71 and q['potential'] == 75 and q['First Touch'] == 70 and q['Pace'] == 85 and q['Punching (Tendency)'] == 30, q
full = {l: 60 for l in S._FM['labels'].values()}
c = S.convert_fm(full, pos=12, ca=71)
assert len(c) == 25 and all(40 <= v <= 99 for v in c.values()) and c['GKReach'] == 40 and c['Speed'] > 60, c
assert S.missing_fm({}, False) and not S.missing_fm(full, True)

# FMInside: the same page as copied text (label TAB value) and as innerText (label and value on two lines) gives the same values
_fm = "Current ability\n51 / 100\nPotential\nDynamic\nFirst Touch (key)\t70\nCrossing (preferred)\t60\nAcceleration\t60\nAggression\t50\n"
_fm2 = "Current ability\n51 / 100\nPotential\nDynamic\nFirst Touch (key)\n70\nCrossing (preferred)\n60\nAcceleration\n\n60\nAggression\n50\n"
assert S.parse_fm(_fm) == S.parse_fm(_fm2) and S.parse_fm(_fm2)['Acceleration'] == 60 and S.parse_fm(_fm2)['Crossing'] == 60
# the real innerText of FMInside: label, optional (preferred) / (key) and the value each on a line of their own
_fm3 = "Current ability\n51 / 100\nPotential\nDynamic\nTechnical\nCrossing\n\t60\nDribbling\n(preferred)\n\t70\nFirst Touch\n(key)\n\t65\nAggression\n\t50\n"
r3 = S.parse_fm(_fm3)
assert r3['Crossing'] == 60 and r3['Dribbling'] == 70 and r3['First Touch'] == 65 and r3['Aggression'] == 50, r3
print('ok')
