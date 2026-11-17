#!/usr/bin/env python3
"""How the skills, COM playing styles and playing styles of the game follow from the values of the players THEMSELVES (analysis tool, needs numpy; the result is data/pes_traits_model.json).
  python3 tools/fit_pes_traits.py PATH_TO_PESDB_FOLDER [PATH_TO_ORIGINAL_ATTRIBUTES]
Every player of the database with his 25 attributes and his position is one sample; no EA FC data and no matching is needed. The attributes are the ORIGINAL ones of the database
(the file players_base.bin of the Gaffer bridge, or an unchanged copy of Player.bin given as second argument).
For every skill and COM style a logistic regression is fitted (cross-validated AUC, the lowest score from which the share of right ones is at least 50 %), for the playing style a
softmax regression per position group. docs/PES_TRAITS_PROFILE.md lists for each skill which values make it likely and what holders have on them."""
import json, os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'flconv')); sys.path.insert(0, os.path.join(HERE, '..', 'flconv', 'lib'))
import plbin, dbmeta

pb = plbin.PlayerBin(os.path.join(sys.argv[1], 'Player.bin'))
AB = plbin.AB
attrs = {}
if len(sys.argv) > 2 and sys.argv[2].lower().endswith('players_base.bin'):
    raw = open(sys.argv[2], 'rb').read()
    for k in range(len(raw) // 380):
        b = raw[k * 380:(k + 1) * 380]
        attrs[struct.unpack_from('<I', b, 0x30)[0]] = [(int.from_bytes(b[off:off + 4], 'little') >> sh) & 127 for (off, sh) in (dbmeta._F7[a] for a in AB)]
elif len(sys.argv) > 2:
    ob = plbin.PlayerBin(sys.argv[2])
    for i, pid in enumerate(ob.ids):
        attrs[pid] = [ob.get(i, a) for a in AB]
else:
    for i, pid in enumerate(pb.ids):
        attrs[pid] = [pb.get(i, a) for a in AB]
rows = [(i, pb.position(i), attrs[pid]) for i, pid in enumerate(pb.ids) if pid in attrs]
print(len(rows), 'players')
POS = ['GK', 'CB', 'LB', 'RB', 'DMF', 'CMF', 'LMF', 'RMF', 'AMF', 'LWF', 'RWF', 'SS', 'CF']
def feats(a, pos):
    return list(map(float, a)) + [1.0 if pos == k else 0.0 for k in range(13)]
X = np.array([feats(r[2], r[1]) for r in rows]); mu, sd = X.mean(0), X.std(0) + 1e-6; Z = (X - mu) / sd
ISGK = np.array([r[1] == 0 for r in rows])

def logit_fit(Z, y, l2=2.0, it=200):
    w = np.zeros(Z.shape[1]); b = np.log((y.mean() + 1e-6) / (1 - y.mean() + 1e-6)); Zb = np.hstack([Z, np.ones((len(Z), 1))])
    for _ in range(it):
        zz = np.clip(Z @ w + b, -30, 30); p = 1 / (1 + np.exp(-zz)); g = p * (1 - p) + 1e-6
        H = (Zb * g[:, None]).T @ Zb + l2 * np.eye(Zb.shape[1]); H[-1, -1] -= l2
        step = np.linalg.solve(H, Zb.T @ (p - y) + l2 * np.append(w, 0)); w -= step[:-1]; b -= step[-1]
        if np.abs(step).max() < 1e-6: break
    return w, b

def auc(score, y):
    o = np.argsort(score); r = np.empty(len(score)); r[o] = np.arange(1, len(score) + 1); n1 = y.sum(); n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else 0.5

def fit_flag(y, Z, mu, sd, names):
    idx = np.arange(len(y)); np.random.RandomState(1).shuffle(idx); cv = np.zeros(len(y))
    for f in np.array_split(idx, 5):
        tr = np.setdiff1d(idx, f); w, b = logit_fit(Z[tr], y[tr]); cv[f] = Z[f] @ w + b
    hi = None
    for t in np.quantile(cv, np.linspace(0.30, 0.998, 200)):
        pr = cv >= t
        if pr.sum() >= 25 and (pr & (y == 1)).sum() / pr.sum() >= 0.5: hi = float(t); break
    w, b = logit_fit(Z, y); z = Z @ w + b
    e = dict(auc=round(auc(cv, y), 3), rate=round(float(y.mean()), 4), w=[round(float(v / s), 5) for v, s in zip(w, sd)], b=round(float(b - (w * mu / sd).sum()), 4))
    if hi is not None:
        e['thr_hi'] = round(float(np.quantile(z, 1 - (cv >= hi).mean())), 4)
        pr = cv >= hi; e['precision'] = round(float((pr & (y == 1)).sum() / pr.sum()), 3); e['recall'] = round(float((pr & (y == 1)).sum() / y.sum()), 3)
    e['top'] = [(names[j], round(float(w[j]), 2)) for j in np.argsort(-np.abs(w))[:5]]
    return e

model = dict(attrs=AB, positions=POS, skills={}, com={}, gk_skills={}, styles={})
prof = {}
FN = AB + POS   # names of the features of the field players (attributes and position)
Zf, Xf = Z[~ISGK], X[~ISGK]
muf, sdf = Xf.mean(0), Xf.std(0) + 1e-6; Zf = (Xf - muf) / sdf
Xk = X[ISGK][:, :25]; muk, sdk = Xk.mean(0), Xk.std(0) + 1e-6; Zk = (Xk - muk) / sdk
frows = [r for r, g in zip(rows, ISGK) if not g]; krows = [r for r, g in zip(rows, ISGK) if g]
for grp, names, get in (('skills', plbin.SKILL_BITS, lambda i, n: n in pb.skills(i)), ('com', plbin.COM_BITS, lambda i, n: n in pb.com_styles(i))):
    for n in names:
        y = np.array([1.0 if get(r[0], n) else 0.0 for r in frows])
        if y.sum() < 40: continue
        model[grp][n] = fit_flag(y, Zf, muf, sdf, FN)
        has = Xf[y == 1][:, :25]; no = Xf[y == 0][:, :25]
        prof[n] = dict(grp=grp, n=int(y.sum()), rate=float(y.mean()), has={AB[j]: round(float(has[:, j].mean()), 1) for j in range(25)}, no={AB[j]: round(float(no[:, j].mean()), 1) for j in range(25)})
for n in ('GK Long Throw', 'GK Low Punt', 'Captaincy'):
    y = np.array([1.0 if n in pb.skills(r[0]) else 0.0 for r in krows])
    if y.sum() >= 40: model['gk_skills'][n] = fit_flag(y, Zk, muk, sdk, AB)
# playing styles: softmax regression on the players of each position group
styles = sorted({pb.playing_style(r[0]) for r in rows})
Y = np.array([styles.index(pb.playing_style(r[0])) for r in rows])
def softmax_fit(Z, y, K, l2=2.0, it=300, lr=0.5):
    W = np.zeros((Z.shape[1], K)); Yh = np.eye(K)[y]
    for _ in range(it):
        S = Z @ W; S -= S.max(1, keepdims=True); P = np.exp(S); P /= P.sum(1, keepdims=True)
        W -= lr * (Z.T @ (P - Yh) / len(Z) + l2 * W / len(Z))
    return W
GROUPS = {'GK': [0], 'DEF': [1, 2, 3], 'DM/CM': [4, 5], 'WIDE-MID': [6, 7], 'AM/WING': [8, 9, 10], 'FWD': [11, 12]}
model['style_groups'] = GROUPS; model['style_names'] = styles; accs = {}
for g, ps in GROUPS.items():
    sel = np.array([r[1] in ps for r in rows]); Zg = Z[sel]; yg = Y[sel]
    idx = np.arange(len(yg)); np.random.RandomState(1).shuffle(idx); ok = 0
    for f in np.array_split(idx, 5):
        tr = np.setdiff1d(idx, f); W = softmax_fit(Zg[tr], yg[tr], len(styles)); ok += int((np.argmax(Zg[f] @ W, 1) == yg[f]).sum())
    W = softmax_fit(Zg, yg, len(styles)); base = np.bincount(yg).max() / len(yg)
    model['styles'][g] = dict(acc=round(ok / len(yg), 3), baseline=round(float(base), 3), n=int(len(yg)), W=[[round(float(v), 4) for v in row] for row in W])
    accs[g] = (ok / len(yg), base)
model['mu'] = [round(float(v), 4) for v in mu]; model['sd'] = [round(float(v), 4) for v in sd]
json.dump(model, open(os.path.join(HERE, '..', 'flconv', 'data', 'pes_traits_model.json'), 'w'))
json.dump(prof, open('/tmp/pes_traits_profile.json', 'w'))
print('%-22s %5s %5s %6s %s' % ('skill / COM', 'AUC', 'prec', 'rate', 'strongest values'))
for grp in ('skills', 'com'):
    for n, e in sorted(model[grp].items(), key=lambda kv: -kv[1]['auc']):
        print('%-22s %5.2f %5s %6.3f %s' % (n, e['auc'], e.get('precision', '-'), e['rate'], ', '.join('%s %+.1f' % t for t in e['top'][:3])))
for g, (a, b) in accs.items(): print('playing style, %-9s accuracy %.2f (position alone: %.2f)' % (g, a, b))
