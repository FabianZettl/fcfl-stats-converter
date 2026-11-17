#!/usr/bin/env python3
"""Adds the playing styles of the game to data/skill_model.json (needs numpy): for every style a model of the EA FC values on the players whose position the style can have;
a style is only given when the player's values fit it (score above the threshold of the best F1).   python3 tools/fit_styles.py PATH_TO_PESDB_FOLDER"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'flconv')); sys.path.insert(0, os.path.join(HERE, '..', 'flconv', 'lib'))
import plbin, fcdb, playstyle
sys.argv = [sys.argv[0], sys.argv[1]]
exec(open(os.path.join(HERE, 'fit_skills.py')).read().split("field = [r for r in rows")[0].split("def logit_fit")[0])   # pb, EA, rows, OUT, GKA
exec("def logit_fit" + open(os.path.join(HERE, 'fit_skills.py')).read().split("def logit_fit")[1].split("def fit_group")[0])   # logit_fit, auc
path = os.path.join(HERE, '..', 'flconv', 'data', 'skill_model.json')
model = json.load(open(path))
allowed = {}
for r in playstyle.MAP['styles']:
    allowed.setdefault(r['style'], set()).update(r['pos'])
model['styles'] = {}
for style, poss in allowed.items():
    sel = [r for r in rows if r[1] in poss]
    X = np.array([r[2] for r in sel]); y = np.array([1.0 if pb.playing_style(r[0]) == style else 0.0 for r in sel])
    if y.sum() < 40:
        continue
    mu, sd = X.mean(0), X.std(0) + 1e-6; Z = (X - mu) / sd
    idx = np.arange(len(y)); np.random.RandomState(1).shuffle(idx); cv = np.zeros(len(y))
    for f in np.array_split(idx, 5):
        tr = np.setdiff1d(idx, f); w, b = logit_fit(Z[tr], y[tr]); cv[f] = Z[f] @ w + b
    best = (0, 0)
    for t in np.quantile(cv, np.linspace(0.02, 0.98, 97)):
        pr = cv >= t; tp = (pr & (y == 1)).sum(); p = tp / max(1, pr.sum()); rc = tp / y.sum(); f1 = 2 * p * rc / max(1e-9, p + rc)
        if f1 > best[0]: best = (f1, t)
    w, b = logit_fit(Z, y); z = Z @ w + b
    thr = float(np.quantile(z, 1 - (cv >= best[1]).mean()))
    model['styles'][style] = dict(auc=round(auc(cv, y), 3), f1=round(float(best[0]), 3), rate=round(float(y.mean()), 3), n=int(len(y)), gk=(0 in poss),
                                  w=[round(float(v / s), 5) for v, s in zip(w, sd)], b=round(float(b - (w * mu / sd).sum()), 4), thr=round(thr, 4))
    print('%-22s n=%5d rate=%.2f AUC=%.2f F1=%.2f' % (style, len(y), y.mean(), auc(cv, y), best[0]))
json.dump(model, open(path, 'w'))
