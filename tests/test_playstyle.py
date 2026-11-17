import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv', 'lib'))
import playstyle as P
ps = P.parse('Finesse Shot|Acrobatic|Quick Step+|Technical')
assert ps == {'Finesse Shot': False, 'Acrobatic': False, 'Quick Step': True, 'Technical': False}
d = P.derive(ps, 9, dict(penalties=60), 5)
assert {'Long Range Drive', 'Acrobatic Finishing', 'Scissors Feint'} <= d['skills'] and len(d['skills']) == 4   # + one of Marseille Turn / Cross Over Turn
assert d['com'] == {'Speeding Bullet', 'Mazing Run'} and d['style'] == 'Prolific Winger'
assert P.derive(ps, 9, dict(penalties=60), 5) == d   # the same every time
assert P.derive(P.parse('Dead Ball'), 5, dict(penalties=70), 1)['skills'] == set() and P.derive(P.parse('Dead Ball'), 5, dict(penalties=80), 1)['skills'] == {'Penalty Specialist'}
assert P.derive({}, 12, None, 0) == dict(skills=set(), com=set(), style=None)
print('ok')
