"""Takes a new FM list (CSV from the FMInside scraper): puts it into flconv/data/fmdb/ (shipped) and the data folder fmdb/, adds its players to the FM calibration (a backup of the
calibration comes first), reports how well the calibration holds on 20 % of the players that were left out of the fit, and writes the thinned set that ships (300 samples).
Usage: update_fm_list.py LIST.csv [--dry]   (--dry: nothing is written, the calibration is worked out on a copy)"""
import collections
import csv
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'flconv'))
sys.path.insert(0, os.path.join(HERE, '..', 'flconv', 'lib'))
import convert  # noqa: E402
import fcdb  # noqa: E402
import fmcal  # noqa: E402
import fmdb  # noqa: E402

src = sys.argv[1]
dry = '--dry' in sys.argv
DATA = os.path.expanduser('~/.local/share/fl-stats-converter')
ship_dir, data_dir = os.path.join(HERE, '..', 'flconv', 'data', 'fmdb'), os.path.join(DATA, 'fmdb')
cal = os.path.join(DATA, 'fm_calib.json')
rows = list(csv.DictReader(open(src, encoding='utf-8-sig', newline=''), delimiter=';'))
assert rows and 'UID' in rows[0], 'not a list from the scraper (first column UID)'
name = os.path.basename(src)
print('list: %d rows, %d with values, %d with positions' % (len(rows), sum(fmdb.complete(r) for r in rows), sum(fmdb.has_positions(r) for r in rows)))
if not dry:
    for d in (ship_dir, data_dir):
        os.makedirs(d, exist_ok=True)
        shutil.copy2(src, os.path.join(d, name))
    if os.path.isfile(cal):
        shutil.copy2(cal, '%s.bak-before-list-%s' % (cal, time.strftime('%Y%m%d_%H%M%S')))
work = cal if not dry else os.path.join(tempfile.mkdtemp(), 'fm_calib.json')
if dry and os.path.isfile(cal):
    shutil.copy2(cal, work)
EA = fcdb.load(os.path.join(HERE, '..', 'flconv', 'data', 'sofifa-base.csv'))
rep, S = fmcal.add(open(src, encoding='utf-8').read(), EA, work)
print('matched:', dict(collections.Counter(('ok' if r['ok'] else r['msg']) for r in rep)))
print('calibration: %d samples, %d keepers' % (len(S), sum(1 for s in S if s.get('gk'))))


def rmse(T, c, attrs):
    e = [s['ea'][a] - (convert.fm_apply(c, a, s['fm'][a]) if c else s['fm'][a]) for s in T for a in attrs if a in s['fm'] and a in s['ea']]
    return round((sum(x * x for x in e) / len(e)) ** .5, 2) if e else None


for gk, attrs, label in ((False, convert.AB[:20], 'field players'), (True, convert.AB, 'keepers')):
    X = [s for s in S if bool(s.get('gk')) == gk]
    tr, te = [s for i, s in enumerate(X) if i % 5], [s for i, s in enumerate(X) if i % 5 == 0]
    print('%s: hold-out of %d players, off the EA FC conversion %s -> %s' % (label, len(te), rmse(te, None, attrs), rmse(te, convert.fm_fit(tr, gk), attrs)))
thin = lambda X, n: X[::max(1, len(X) // n)][:n]
T = thin([s for s in S if not s.get('gk')], 240) + thin([s for s in S if s.get('gk')], 60)
if not dry:
    json.dump(dict(samples=T), open(os.path.join(HERE, '..', 'flconv', 'data', 'fm_calib.json'), 'w'), ensure_ascii=False, indent=1)
    print('written: list in %s and %s, calibration, thinned set (%d samples). Next: tests, commit, push.' % (ship_dir, data_dir, len(T)))
else:
    print('dry run: nothing written')
