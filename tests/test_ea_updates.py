"""SoFIFA updates: the date of an update is found, a newer update beats an older one and the standard database, an older snapshot does not beat a newer one, new players are added."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv', 'lib'))
import fcdb  # noqa: E402

HEAD = 'base_id,stats_id,first_name,last_name,common_name,full_name,nation_name,club_name,position,rating,potential,height,birthdate,snapshot,sprint_speed'


def csvfile(folder, name, rows):
    path = os.path.join(folder, name)
    open(path, 'w', encoding='utf-8-sig').write(HEAD + '\n' + '\n'.join(','.join(str(x) for x in r) for r in rows) + '\n')
    return path


def row(bid, first, last, rating, snap, speed=70, club='Arsenal'):
    return [bid, bid, first, last, '', first + ' ' + last, 'England', club, 'ST', rating, rating + 2, 180, '01-01-2000', snap, speed]


root = tempfile.mkdtemp()
base = csvfile(root, 'fc27-players.csv', [row(1, 'Anna', 'Alpha', 80, '12-09-2026'), row(2, 'Bert', 'Beta', 70, '12-09-2026')])
ups = os.path.join(root, 'updates')
os.makedirs(ups)
csvfile(ups, 'newer.csv', [row(1, 'Anna', 'Alpha', 84, '24-11-2026', speed=88), row(3, 'Cora', 'Gamma', 75, '24-11-2026')])   # a new value and a new player
csvfile(ups, 'older.csv', [row(1, 'Anna', 'Alpha', 82, '10-10-2026'), row(2, 'Bert', 'Beta', 72, '10-10-2026')])              # between the standard database and the newer update
open(os.path.join(ups, 'notes.csv'), 'w').write('a,b\n1,2\n')                                                                 # no SoFIFA export: ignored
open(os.path.join(ups, 'fc27-2026-12-01.csv'), 'w').write(HEAD + '\n' + ','.join(str(x) for x in row(2, 'Bert', 'Beta', 74, '')) + '\n')   # no snapshot: the date in the file name

u = fcdb.update_files(ups)
assert [x['name'] for x in u] == ['older.csv', 'newer.csv', 'fc27-2026-12-01.csv'] and u[0]['date'] == (2026, 10, 10) and u[2]['date'] == (2026, 12, 1)
db = fcdb.DB(base, u)
by = {r['full']: r for r in db.rows}
assert by['anna alpha']['rating'] == 84 and by['anna alpha']['upd'] == 'newer.csv'    # the newest update wins over the older one and the standard database
assert by['bert beta']['rating'] == 74 and by['bert beta']['upd'] == 'fc27-2026-12-01.csv'   # the file name gives the date when there is no snapshot
assert by['cora gamma']['rating'] == 75 and len(db.rows) == 3                           # a player that the standard database does not have is added
assert fcdb.DB(base).rows[0]['upd'] is None and fcdb.DB(base).rows[0]['rating'] == 80  # without updates: the standard database
# a row with an older snapshot does not replace a newer one, whatever the order of the files
csvfile(ups, 'zz-late-file-old-data.csv', [row(1, 'Anna', 'Alpha', 60, '01-01-2026')])
u2 = fcdb.update_files(ups)
assert fcdb.DB(base, u2).rows[0]['rating'] == 84 or {r['full']: r for r in fcdb.DB(base, u2).rows}['anna alpha']['rating'] == 84
assert len(fcdb.load(base, ups).updates) == len(u2) and fcdb.load(base, ups) is fcdb.load(base, ups)   # cached until a file changes
# eight updates (more than one row per player, dates all different): for every player the row with the newest snapshot
import random
random.seed(7)
r8 = tempfile.mkdtemp()
b8 = csvfile(r8, 'fc27-players.csv', [row(i, 'P%d' % i, 'Player', 60, '12-09-2026') for i in range(1, 31)])
u8 = os.path.join(r8, 'u')
os.makedirs(u8)
days = [(y, m, d) for y, m in ((2026, 10), (2026, 11), (2026, 12), (2027, 1)) for d in range(1, 29)]   # all after the standard database
random.shuffle(days)
best = {i: ((2026, 9, 12), 60) for i in range(1, 31)}
for f in range(1, 9):
    rows = []
    for i in random.sample(range(1, 31), 12):
        d = days.pop()
        rating = 61 + f * 3 + i % 3
        rows.append(row(i, 'P%d' % i, 'Player', rating, '%02d-%02d-%d' % (d[2], d[1], d[0])))
        if d > best[i][0]:
            best[i] = (d, rating)
    csvfile(u8, 'upd%d.csv' % f, rows)
got = {int(r['raw']['base_id']): r['rating'] for r in fcdb.DB(b8, fcdb.update_files(u8)).rows}
assert all(got[i] == best[i][1] for i in best), [(i, got[i], best[i]) for i in best if got[i] != best[i][1]]
print('ok')
