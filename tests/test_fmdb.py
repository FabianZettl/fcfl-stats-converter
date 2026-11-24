"""The FM list: reading, finding a player, the page text for the FM conversion, positions and weak foot."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv', 'lib'))
import fmcal  # noqa: E402
import fmdb  # noqa: E402
import sofifa  # noqa: E402

LAB = list(sofifa.FM_LABELS.values())
head = ['UID', 'Name', 'Full name', 'Club', 'Positions', 'Ability (0-99)', 'Potential (0-99)', 'Age', 'Footedness', 'Weak foot', 'Height', 'Pos ST', 'Pos AMC', 'Pos AML', 'Pos DC', 'Pos WBL'] + LAB


def row(uid, name, club, age, **kw):
    d = dict(UID=uid, Name=name, **{'Full name': name}, Club=club, Positions='AML, ST', **{'Ability (0-99)': '96', 'Potential (0-99)': '99'}, Age=str(age), Footedness='Right', **{'Weak foot': '4'},
             Height='178 CM', **{'Pos ST': 'natural', 'Pos AMC': 'accomplished', 'Pos AML': 'natural', 'Pos DC': 'unavailable', 'Pos WBL': 'competent'})
    d.update({l: '13' for l in LAB})
    d.update({'Pace': '20', 'Crossing': '1'})
    d.update(kw)
    return ';'.join(d.get(h, '') for h in head)


folder = tempfile.mkdtemp()
open(os.path.join(folder, 'a.csv'), 'w', encoding='utf-8-sig').write('\n'.join([';'.join(head), row('1', 'Kylian Mbappé', 'R. Madrid', 27), row('2', 'Ahmed Ali', 'Al Ahly', 25), row('3', 'Ahmed Ali', 'Zamalek', 30)]) + '\n')
open(os.path.join(folder, 'notes.csv'), 'w').write('not;a;list\n1;2;3\n')   # a csv that is no list is ignored
L = fmdb.FMList([folder])
assert len(L) == 3
mb = L.find('Kylian Mbappe', 'Real Madrid', 27)
assert mb and mb['UID'] == '1'
assert L.find('Ahmed Ali') is None                                        # two players, nothing to tell them apart: none
assert L.find('Ahmed Ali', 'Zamalek')['UID'] == '3'                       # the club does
assert L.find('Ahmed Ali', None, 25)['UID'] == '2'                        # or the age
assert L.find('Kylian Mbappé', 'R. Madrid', 40) is None                   # more than 3 years off: another player
r = fmdb.raw(mb)
assert r['Pace'] == 99 and r['Crossing'] == 5 and r['Dribbling'] == 65 and r['overall'] == 96 and r['potential'] == 99
txt = fmdb.page_text(mb)
assert sofifa.is_fm(txt) and fmcal.info(txt)['name'] == 'Kylian Mbappé' and fmcal.info(txt)['age'] == 27
assert sofifa.parse_fm(txt) == r                                          # the page text gives back exactly the values
lv = fmdb.positions(mb)
assert lv[12] == 2 and lv[8] == 1 and lv[9] == 2 and lv[1] == 0 and lv[2] == 0   # ST natural, AMC accomplished, AML natural; competent / unavailable give nothing
assert fmdb.weak_foot(mb) == (3, 3) and fmdb.weak_foot(dict(mb, **{'Weak foot': ''})) is None
assert fmdb.foot(mb) == 'Right' and fmdb.foot(dict(mb, Footedness='Either')) is None and fmdb.height(mb) == 178 and fmdb.height(dict(mb, Height='99 CM')) is None
assert fmdb.complete(mb) and not fmdb.complete(dict(mb, Pace=''))   # a row without all attributes is no source of values
assert not fmdb.complete(dict(UID='9', Name='X', Positions='ST', **{'Ability (0-99)': '80'}))
assert fmdb.has_positions(mb) and fmdb.detail(mb)
listrow = dict(UID='9', Name='X', Positions='ST')
assert not fmdb.has_positions(listrow) and not fmdb.detail(listrow) and fmdb.detail(dict(listrow, **{'Weak foot': '3'}))   # a line of a list has nothing to add to an EA FC player
assert fmdb.plausible(mb, 12) and fmdb.plausible(mb, 9) and fmdb.plausible(mb, 8)   # AML, ST: a striker, a left winger, an attacking midfielder fit
assert not fmdb.plausible(mb, 0) and not fmdb.plausible(mb, 1) and not fmdb.plausible(dict(mb, Positions='GK'), 12) and fmdb.plausible(dict(mb, Positions='GK'), 0)
assert fmdb.plausible(dict(mb, Positions=''), 1)   # nothing to judge by
bruno = dict(mb, **{'Pos AMC': 'natural', 'Pos MC': 'accomplished', 'Pos ST': 'competent', 'Pos ML': 'unavailable', 'Pos AML': 'competent', 'Pos ST': 'competent', 'Pos DM': 'competent'})
cur = [0, 0, 0, 0, 0, 2, 2, 1, 2, 1, 1, 1, 0]   # CMF 2, LMF 2, RMF 1, AMF 2, LWF 1, RWF 1, SS 1
lv = fmdb.positions(bruno, cur)
assert lv[5] == 2 and lv[8] == 2          # accomplished keeps his CMF 2, natural AMF 2
assert lv[6] == 0 and lv[9] == 1 and lv[4] == 0   # ML unavailable: lost; AML competent keeps 1; DM competent never adds
assert fmdb.positions(bruno)[5] == 1 and fmdb.positions(bruno, [0] * 13)[5] == 1 and fmdb.positions(bruno, [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0])[9] == 1   # without levels: accomplished 1; competent 2 -> 1
# points: club, age, height (the club alone is not needed: players move)
two = fmdb.FMList([folder])
row_a, row_b = two.rows['2'], two.rows['3']
assert two.find('Ahmed Ali', None, 25, 178)['UID'] == '2' and two.find('Ahmed Ali', None, 30, 178)['UID'] == '3'
assert two.find('Kylian Mbappé', 'Bayern München', 27, 178) is not None        # another club, but age and height fit
assert two.find('Kylian Mbappé', 'R. Madrid', 27, 195) is not None             # 17 cm off, but club and age fit (2 + 2 - 2 = 2)
assert two.find('Kylian Mbappé', 'Bayern München', 29, 195) is None            # nothing fits: another player with the same name
assert two.find('Kylian Mbappé', None, 28, 190) is None                        # no club, age 1 year off (+1), height 12 cm off (-2): -1 points
# names that differ: found by a shared word AND club, age, height and nation, but not by a first name alone
fz = tempfile.mkdtemp()
open(os.path.join(fz, 'f.csv'), 'w', encoding='utf-8-sig').write('\n'.join([';'.join(head + ['Nationality']),
    row('11', 'Neymar', 'Santos', 33, Height='175 CM') + ';Brazil', row('12', 'Juan Guillermo Cuadrado', 'Millonarios F.C.', 37, Height='178 CM') + ';Colombia',
    row('13', 'Luka Vrbančić', 'Osijek', 20, Height='182 CM') + ';Croatia']) + '\n')
F = fmdb.FMList([fz])
assert F.find('Neymar Jr', 'Santos FC', 33, 175, 'Brazil')['UID'] == '11'            # one name in FM: its word is the first word of the name
assert F.find('Juan Cuadrado', 'Millonarios FC', 37, 178, 'Colombia')['UID'] == '12'   # the surname is shared, club / age / height / nation fit
assert F.find('Luka Tunjić', 'NK Osijek', 19, 183, 'Croatia') is None                  # only the first name is shared: another player
assert F.find('Juan Cuadrado', 'Millonarios FC', 37, 178, 'Argentina') is None         # another nation
assert F.find('Juan Cuadrado', 'Real Madrid', 37, 178, 'Colombia') is None             # another club
print('ok')
