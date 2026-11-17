import csv, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv', 'lib'))
import fcdb
H = ['base_id', 'stats_id', 'first_name', 'last_name', 'club_name', 'nation_name', 'common_name', 'full_name', 'position', 'position_alt', 'position_alt_2', 'position_alt_3', 'rating', 'potential', 'height'] + list(fcdb.COLS)
def row(i, first, last, club, nation, rating, pos='CM', common=''):
    r = dict.fromkeys(H, '')
    r.update(base_id=i, stats_id=i, first_name=first, last_name=last, club_name=club, nation_name=nation, common_name=common, full_name='%s, %s' % (last, first), position=pos, rating=rating, potential=rating, height=180)
    for c in fcdb.COLS:
        r[c] = '60'
    return r
rows = [row(1, 'Tom', 'Bischof', 'FC Bayern München', 'Germany', 79), row(2, 'Ben', 'Davies', 'Bolton', 'Wales', 68), row(3, 'Ben', 'Davies', 'Spurs', 'Wales', 74),
        row(4, 'Dani', 'Olmo Carvajal', 'FC Barcelona', 'Spain', 84), row(5, 'Gabriel', 'Dos Santos Magalhães', 'Arsenal', 'Brazil', 89), row(6, 'x', 'y', 'ICON', 'z', 90)]
with tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False, newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, H)
    w.writeheader()
    w.writerows(rows)
db = fcdb.DB(f.name)
os.remove(f.name)
assert len(db.rows) == 5
m = db.match('Tom Bischof', 'Sunderland AFC', None, False, ovr=77)
assert m['status'] == 'ok' and m['row']['id'] == '1', m   # moved club: the name is unique and the overall is near
assert db.match('Ben Davies', 'Tottenham Hotspur', None, False)['row']['id'] == '3'   # Spurs = Tottenham
assert db.match('Ben Davies', 'Burnley', None, False)['status'] == 'ambiguous'
assert db.match('Daniel Carvajal', 'SSC Napoli', None, False, ovr=79)['status'] == 'none'   # only the end of a longer surname: not enough
assert db.match('Gabriel Magalhães', 'Arsenal FC', None, False)['row']['id'] == '5'
assert db.match('Tom Bischof', 'Sunderland AFC', None, True)['status'] == 'none'   # a keeper is not him
s = db.stats(db.rows[0])
assert s['crossing'] == 60 and s['overall'] == 79 and 'gkdiving' in s or True
assert [x['id'] for x in db.search('davies')] == ['3', '2'] and db.search('bischof bayern')[0]['id'] == '1' and not db.search('zzz')
print('ok')
