#!/usr/bin/env python3
"""Which positions a player can play, from his values: a model per position (cross-validated) on the players of the database itself (analysis tool, needs numpy; result
data/position_model.json).   python3 tools/fit_positions.py PATH_TO_PESDB_FOLDER PATH_TO_players_base.bin
Targets: 'plays it' (competent or natural, level >= 1) and 'natural' (level 2) for each of the 13 positions, features: the 25 attributes and the main position."""
import json, os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'flconv')); sys.path.insert(0, os.path.join(HERE, '..', 'flconv', 'lib'))
import plbin, dbmeta
pb = plbin.PlayerBin(os.path.join(sys.argv[1], 'Player.bin')); AB = plbin.AB
raw = open(sys.argv[2], 'rb').read(); attrs = {}
for k in range(len(raw) // 380):
    b = raw[k * 380:(k + 1) * 380]
    attrs[struct.unpack_from('<I', b, 0x30)[0]] = [(int.from_bytes(b[off:off + 4], 'little') >> sh) & 127 for (off, sh) in (dbmeta._F7[a] for a in AB)]
POS = ['GK', 'CB', 'LB', 'RB', 'DMF', 'CMF', 'LMF', 'RMF', 'AMF', 'LWF', 'RWF', 'SS', 'CF']
rows = [(i, pb.position(i), attrs[pid]) for i, pid in enumerate(pb.ids) if pid in attrs and pb.position(i) != 0]
X = np.array([list(map(float, a)) + [1.0 if m == k else 0.0 for k in range(1, 13)] for _, m, a in rows]); mu, sd = X.mean(0), X.std(0) + 1e-6; Z = (X - mu) / sd
LV = np.array([pb.positions(i) for i, _, _ in rows])
def logit_fit(Z, y, l2=2.0, it=120):
    w = np.zeros(Z.shape[1]); b = np.log((y.mean() + 1e-6) / (1 - y.mean() + 1e-6)); Zb = np.hstack([Z, np.ones((len(Z), 1))])
    for _ in range(it):
        zz = np.clip(Z @ w + b, -30, 30); p = 1 / (1 + np.exp(-zz)); g = p * (1 - p) + 1e-6
        H = (Zb * g[:, None]).T @ Zb + l2 * np.eye(Zb.shape[1]); H[-1, -1] -= l2
        st = np.linalg.solve(H, Zb.T @ (p - y) + l2 * np.append(w, 0)); w -= st[:-1]; b -= st[-1]
        if np.abs(st).max() < 1e-6: break
    return w, b
def auc(s, y):
    o = np.argsort(s); r = np.empty(len(s)); r[o] = np.arange(1, len(s) + 1); n1 = y.sum(); n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else 0.5
model = dict(attrs=AB, positions=POS, plays={}, natural={}, mu=[round(float(v), 4) for v in mu], sd=[round(float(v), 4) for v in sd])
mains = np.array([m for _, m, _ in rows])
print('%-4s %-8s %6s %5s %6s %6s' % ('pos', 'target', 'rate', 'AUC', 'prec', 'recall'))
for p in range(1, 13):
    for tgt, lv in (('plays', 1), ('natural', 2)):
        y = ((LV[:, p] >= lv) & (mains != p)).astype(float)   # beside the main position
        if y.sum() < 60: continue
        idx = np.arange(len(y)); np.random.RandomState(1).shuffle(idx); cv = np.zeros(len(y))
        for f in np.array_split(idx, 5):
            tr = np.setdiff1d(idx, f); w, b = logit_fit(Z[tr], y[tr]); cv[f] = Z[f] @ w + b
        hi = None
        for t in np.quantile(cv, np.linspace(0.30, 0.998, 200)):
            pr = cv >= t
            if pr.sum() >= 25 and (pr & (y == 1)).sum() / pr.sum() >= 0.6: hi = float(t); break
        w, b = logit_fit(Z, y); z = Z @ w + b
        e = dict(auc=round(auc(cv, y), 3), rate=round(float(y.mean()), 4), w=[round(float(v / s), 5) for v, s in zip(w, sd)], b=round(float(b - (w * mu / sd).sum()), 4))
        pr_ = rc_ = None
        if hi is not None:
            e['thr_hi'] = round(float(np.quantile(z, 1 - (cv >= hi).mean())), 4); pr = cv >= hi
            pr_ = float((pr & (y == 1)).sum() / pr.sum()); rc_ = float((pr & (y == 1)).sum() / y.sum()); e['precision'] = round(pr_, 3); e['recall'] = round(rc_, 3)
        model[tgt][POS[p]] = e
        print('%-4s %-8s %6.3f %5.2f %6s %6s' % (POS[p], tgt, y.mean(), e['auc'], '%.2f' % pr_ if pr_ else '-', '%.2f' % rc_ if rc_ else '-'))
json.dump(model, open(os.path.join(HERE, '..', 'flconv', 'data', 'position_model.json'), 'w'))
