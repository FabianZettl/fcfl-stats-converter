#!/usr/bin/env python3
"""Fits how the skills, COM playing styles and playing styles of the game follow from EA FC values (analysis tool, needs numpy; the result is data/skill_model.json, the tool itself needs no numpy).
  python3 tools/fit_skills.py PATH_TO_PESDB_FOLDER
The game database is matched with the EA FC data (full name, unique, age within 2 years); for every skill a logistic regression on the 34 EA attributes (and the position group) is fitted on the
players that are in both; its quality (area under the curve, cross-validated) and the best threshold are stored with it."""
import csv, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'flconv')); sys.path.insert(0, os.path.join(HERE, '..', 'flconv', 'lib'))
import plbin, fcdb, dbmeta

pesdb = sys.argv[1]
pb = plbin.PlayerBin(os.path.join(pesdb, 'Player.bin'))
EA = fcdb.load(os.path.join(HERE, '..', 'flconv', 'data', 'sofifa-base.csv'))
ATTR = list(fcdb.COLS.keys())
OUT = [c for c in ATTR if not c.startswith('gk_')]
GKA = [c for c in ATTR if c.startswith('gk_')]
rows = []
for i, pid in enumerate(pb.ids):
    nm = pb.get_name(i, 'name')
    m = EA.match(nm, None, None, None, age=pb.age(i) + 0)
    if m['status'] != 'ok':
        continue
    r = m['row']
    try:
        x = [float(r['raw'][c]) for c in (GKA if pb.position(i) == 0 else OUT)]
    except (ValueError, KeyError):
        continue
    rows.append((i, pb.position(i), x, r))
print(len(rows), 'matched players')

def logit_fit(X, y, l2=1.0, it=300):
    w = np.zeros(X.shape[1]); b = np.log((y.mean() + 1e-6) / (1 - y.mean() + 1e-6))
    for _ in range(it):   # Newton steps
        z = X @ w + b; p = 1 / (1 + np.exp(-z)); g = p * (1 - p) + 1e-6
        Xb = np.hstack([X, np.ones((len(X), 1))])
        H = (Xb * g[:, None]).T @ Xb + l2 * np.eye(Xb.shape[1]); H[-1, -1] -= l2
        step = np.linalg.solve(H, Xb.T @ (p - y) + l2 * np.append(w, 0))
        w -= step[:-1]; b -= step[-1]
        if np.abs(step).max() < 1e-6: break
    return w, b

def auc(score, y):
    o = np.argsort(score); r = np.empty(len(score)); r[o] = np.arange(1, len(score) + 1)
    n1 = y.sum(); n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else 0.5

def fit_group(sel, names, getter, feats):
    """sel: rows of the group; names: targets; returns {name: model}"""
    X = np.array([r[2] for r in sel]); mu, sd = X.mean(0), X.std(0) + 1e-6; Z = (X - mu) / sd
    res = {}
    for n in names:
        y = np.array([1.0 if getter(r, n) else 0.0 for r in sel])
        if y.sum() < 40 or y.sum() > len(y) - 40:
            continue
        idx = np.arange(len(y)); rng = np.random.RandomState(1); rng.shuffle(idx); folds = np.array_split(idx, 5); cv = np.zeros(len(y))
        for f in folds:
            tr = np.setdiff1d(idx, f); w, b = logit_fit(Z[tr], y[tr]); cv[f] = Z[f] @ w + b
        a = auc(cv, y)
        best = (0, 0, 0, 0)   # f1, precision, recall, threshold
        for t in np.quantile(cv, np.linspace(0.02, 0.98, 97)):
            pr = cv >= t; tp = (pr & (y == 1)).sum(); p = tp / max(1, pr.sum()); rc = tp / y.sum(); f1 = 2 * p * rc / max(1e-9, p + rc)
            if f1 > best[0]: best = (f1, p, rc, t)
        hi = None   # the lowest cross-validated score from which the share of right ones is at least 50 % (and at least 25 players): used to ADD a skill only where the values are clear
        for t in np.quantile(cv, np.linspace(0.30, 0.995, 140)):
            pr = cv >= t
            if pr.sum() >= 25 and (pr & (y == 1)).sum() / pr.sum() >= 0.5:
                hi = float(t); break
        w, b = logit_fit(Z, y)
        z = Z @ w + b
        # threshold on the full-fit score at the same quantile as the cross-validated best threshold
        q = (cv >= best[3]).mean(); thr = float(np.quantile(z, 1 - q))
        # w, b in raw attribute units: score = x.w + b is exactly the standardized score, so the thresholds are on the same scale
        res[n] = dict(auc=round(a, 3), f1=round(best[0], 3), precision=round(best[1], 3), recall=round(best[2], 3), rate=round(float(y.mean()), 4), n=int(y.sum()),
                      w=[round(float(v / s), 5) for v, s in zip(w, sd)], b=round(float(b - (w * mu / sd).sum()), 4), thr=round(thr, 4))
        if hi is not None:
            q2 = (cv >= hi).mean(); res[n]['thr_hi'] = round(float(np.quantile(z, 1 - q2)), 4)
    return res

field = [r for r in rows if r[1] != 0]; keepers = [r for r in rows if r[1] == 0]
model = dict(attrs=OUT, gk_attrs=GKA, skills={}, com={}, gk_skills={})
sk_get = lambda r, n: n in pb.skills(r[0])
com_get = lambda r, n: n in pb.com_styles(r[0])
for k, v in fit_group(field, list(plbin.SKILL_BITS), sk_get, OUT).items():
    model['skills'][k] = v
for k, v in fit_group(field, list(plbin.COM_BITS), com_get, OUT).items():
    model['com'][k] = v
for k, v in fit_group(keepers, list(plbin.SKILL_BITS), sk_get, GKA).items():
    model['gk_skills'][k] = v
json.dump(model, open(os.path.join(HERE, '..', 'flconv', 'data', 'skill_model.json'), 'w'))
# how good is each way to a skill: the PlayStyle mapping alone (players that the ratings page has), the attributes alone (cross-validated AUC), both together
import playstyle
api = {}
if len(sys.argv) > 2:
    for x in json.load(open(sys.argv[2])):
        api[str(x['id'])] = set(x.get('abil') or [a['label'] for a in x.get('playerAbilities', [])])
MAPSK = {}
for ps, m in playstyle.MAP['skills'].items():
    for k in (m.get('skills') or []) + (m.get('plus') or []) + (m.get('one_of') or []):
        MAPSK.setdefault(k, set()).add(ps)
    for k in (m.get('com') or []):
        MAPSK.setdefault(k, set()).add(ps)
ev = {}
for grp, getter, names in (('skills', sk_get, plbin.SKILL_BITS), ('com', com_get, plbin.COM_BITS)):
    for n in names:
        mp = MAPSK.get(n)
        cov = [r for r in field if r[3]['id'] in api]
        if not cov:
            continue
        y = np.array([1.0 if getter(r, n) else 0.0 for r in cov])
        e = dict(covered=len(cov), rate=round(float(y.mean()), 3), mapped=sorted(mp) if mp else [])
        if mp:
            pr = np.array([1.0 if any(a.rstrip('+') in mp for a in api[r[3]['id']]) else 0.0 for r in cov])
            tp = float((pr * y).sum()); e['map_precision'] = round(tp / max(1, pr.sum()), 3); e['map_recall'] = round(tp / max(1, y.sum()), 3)
            m_ = model[grp].get(n)
            if m_:
                sc = np.array([sum(w * float(r[3]['raw'][c]) for w, c in zip(m_['w'], OUT)) + m_['b'] for r in cov]); mo = (sc >= m_['thr']).astype(float)
                un = np.maximum(pr, mo); tp2 = float((un * y).sum()); e['both_precision'] = round(tp2 / max(1, un.sum()), 3); e['both_recall'] = round(tp2 / max(1, y.sum()), 3)
        ev[n] = e
json.dump(ev, open(os.path.join(HERE, '..', 'docs', 'skill_translation_quality.json'), 'w'), indent=1)
print('%-24s %5s %5s %5s %5s %6s' % ('skill', 'AUC', 'F1', 'prec', 'rec', 'rate'))
for grp in ('skills', 'com', 'gk_skills'):
    for k, v in sorted(model[grp].items(), key=lambda kv: -kv[1]['auc']):
        print('%-3s %-20s %5.2f %5.2f %5.2f %5.2f %6.3f' % (grp[:3], k, v['auc'], v['f1'], v['precision'], v['recall'], v['rate']))
