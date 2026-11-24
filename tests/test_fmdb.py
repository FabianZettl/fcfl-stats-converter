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
print('ok')
