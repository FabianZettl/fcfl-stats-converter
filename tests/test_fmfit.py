"""FM calibration: the fit finds a plain offset, keepers are fitted apart, thousands of samples do not make it slow, the file fit is worked out once per version of the file."""
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv', 'lib'))
import convert  # noqa: E402

A = convert.AB[:20]
S = []
for i in range(3000):
    fm = {a: 50 + (i * 7 + k * 13) % 40 for k, a in enumerate(A)}
    S.append(dict(name='p%d' % i, pos=5, fm=fm, ea={a: v + 5 for a, v in fm.items()}))   # EA FC is 5 above FM everywhere
t = time.time()
cal = convert.fm_fit(S)
assert time.time() - t < 10, 'too slow for thousands of samples'
assert all(c['method'] in ('shift', 'affine') and abs(convert.fm_apply(cal, a, 70) - 75) <= 1 for a, c in cal.items())
K = [dict(name='k%d' % i, pos=0, gk=True, fm={a: 60 + i % 30 for a in convert.AB}, ea={a: 62 + i % 30 for a in convert.AB}) for i in range(20)]
assert convert.fm_fit(S[:10] + K[:3], True) == {}                     # fewer than 6 keepers: no fit
assert len(convert.fm_fit(K, True)) == 25 and convert.fm_fit(K) == {} and convert.fm_fit(S[:50], True) == {}   # keepers and field players are not mixed
path = os.path.join(tempfile.mkdtemp(), 'c.json')
json.dump(dict(samples=S[:200]), open(path, 'w'))
n, c1 = convert.fm_cal(path)
assert n == 200 and c1
convert.fm_fit = lambda *a, **k: (_ for _ in ()).throw(AssertionError('worked out again'))   # the same version of the file: from the cache
assert convert.fm_cal(path)[1] is c1
print('ok')
