import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv', 'lib'))
import playstyle as P
# a tall, strong, good heading centre back: the Heading skill and a defensive style are safe, a striker's skills are not
cb = dict.fromkeys(P.AB, 55); cb.update(Heading=88, Jump=84, PhysicalContact=85, DefensiveAwareness=84, BallWinning=82, Aggression=80, GKAwareness=40, GKCatching=40, GKClearing=40, GKReflexes=40, GKReach=40)
t = P.traits_from_values(cb, 1)
assert 'Heading' in t['skills'] and 'First-time Shot' not in t['skills'] and 'Acrobatic Finishing' not in t['skills']
lv = P.positions_from_values(cb, 1)
assert lv[1] == 2 and lv[12] == 0 and lv[11] == 0
st = dict.fromkeys(P.AB, 50); st.update(Finishing=90, OffensiveAwareness=88, Heading=75, KickingPower=84, GKAwareness=40, GKCatching=40, GKClearing=40, GKReflexes=40, GKReach=40)
assert 'First-time Shot' in P.traits_from_values(st, 12)['skills'] and P.positions_from_values(st, 12)[1] == 0
print('ok')
