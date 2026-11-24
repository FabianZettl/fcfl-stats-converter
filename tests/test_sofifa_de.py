"""The German SoFIFA export (';', German titles) as an update: rating, club, nation, position, height and the attribute values are taken over, the PlayStyles stay, the date is the one in the
file name (not the roster number in front of it), a new player is added, N/A is no value, a row without a rating is left out."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv', 'lib'))
import fcdb  # noqa: E402

d = tempfile.mkdtemp()
base = os.path.join(d, 'fc27-players.csv')
H = 'base_id,stats_id,first_name,last_name,common_name,full_name,nation_name,club_name,position,rating,potential,height,birthdate,snapshot,sprint_speed,playstyles'
open(base, 'w', encoding='utf-8-sig').write(H + '\n' + '1,1,Anna,Alpha,,Anna Alpha,England,Arsenal,ST,80,82,180,01-01-2000,12-09-2026,70,Finesse Shot\n')
up = os.path.join(d, 'up')
os.makedirs(up)
GH = 'ID;Name;Vollständiger Name;Nationalität;Positionen;Verein;Alter;Gesamtbewertung;Potenzial;Geburtsjahr;Größe;Gewicht;foot;Sprintgeschwindigkeit;Schwacher Fuß;Spielstile;Link'
rows = [GH,
        '1;A. Alpha;Anna Alpha;Russland;ZOM, LF, ST;Inter Milan;27;86;88;2000;"192cm 6\'4""";82kg 181lbs;Links;91;4;Weiter Abwurf;https://x',
        '9;C. Neu;Carl Van Neu;Brasilien;TW;Ajax;20;70;80;2006;"185cm 6\'1""";80kg 176lbs;Rechts;N/A;2;;https://y',
        '10;;;;;;;;;;;;;;;;']
open(os.path.join(up, 'sofifa-updates-270007-2026-11-24.csv'), 'w', encoding='utf-8-sig').write('\n'.join(rows) + '\n')

u = fcdb.update_files(up)
assert u[0]['date'] == (2026, 11, 24)   # not 2700-07-20 from the number 270007
g = {r['raw']['base_id']: r for r in fcdb.DB(base, u).rows}
a, c = g['1'], g['9']
assert a['rating'] == 86 and a['potential'] == 88 and a['club'] == 'Inter Milan' and a['nation'] == 'Russia' and a['pos'] == 'CAM' and a['alt'] == ['LW', 'ST'] and a['height'] == 192
assert a['raw']['sprint_speed'] == '91' and a['raw']['foot'] == 'Left' and a['raw']['weak_foot'] == '4'
assert a['raw']['playstyles'] == 'Finesse Shot'   # the German PlayStyle names are not translated: the ones of the standard database stay
assert a['name'] == 'Anna Alpha' and a['raw']['first_name'] == 'Anna' and a['upd'] and a['raw']['snapshot'] == '24-11-2026'
assert c['rating'] == 70 and c['nation'] == 'Brazil' and c['pos'] == 'GK' and c['raw']['first_name'] == 'Carl Van' and c['raw']['last_name'] == 'Neu'
assert 'sprint_speed' not in c['raw']   # N/A
assert len(g) == 2   # the row without a rating is left out
assert fcdb.read_update(base)   # the EA FC export itself is read as well
other = os.path.join(d, 'other.csv')
open(other, 'w').write('a;b\n1;2\n')
assert fcdb.read_update(other) is None   # no export of SoFIFA
print('ok')
