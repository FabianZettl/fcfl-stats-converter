#!/usr/bin/env python3
"""Writes docs/PES_TRAITS_PROFILE.md: for every skill / COM style of the game which values make it likely, what the players that have it have on them, and from which value
on half of the players have it.   python3 tools/pes_traits_profile.py PATH_TO_PESDB_FOLDER PATH_TO_players_base.bin   (after tools/fit_pes_traits.py)"""
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
idx = [i for i, pid in enumerate(pb.ids) if pid in attrs and pb.position(i) != 0]
A = np.array([attrs[pb.ids[i]] for i in idx], dtype=float); P = np.array([pb.position(i) for i in idx])
M = json.load(open(os.path.join(HERE, '..', 'flconv', 'data', 'pes_traits_model.json')))
out = ['# What the players of the game have on the values behind a skill, COM style or playing style', '',
       'Measured on all %d outfield players of the database (their own original values and positions, no EA FC data). "from" = the value of the strongest attribute from which at least half of the players that reach it have the skill; "holders / others" = the mean of that attribute for the players that have the skill and for those that do not. Used by the tool to give skills to players that are not in the EA FC data (tools/fit_pes_traits.py).' % len(idx), '']
for grp, title in (('skills', 'Skills'), ('com', 'COM playing styles')):
    out += ['## ' + title, '', '| skill | share of players | strongest values (+ makes it likely) | holders / others | half have it from | main positions | quality |', '|---|---|---|---|---|---|---|']
    for n, e in sorted(M[grp].items(), key=lambda kv: -kv[1]['auc']):
        y = np.array([1 if (n in pb.skills(i) if grp == 'skills' else n in pb.com_styles(i)) else 0 for i in idx])
        top = [(a, w) for a, w in e['top'] if a in AB and w > 0][:3]
        if not top: continue
        a0 = AB.index(top[0][0]); col = A[:, a0]; frm = '–'
        for v in range(45, 96, 2):
            sel = col >= v
            if sel.sum() >= 40 and y[sel].mean() >= 0.5: frm = '%s %d' % (top[0][0], v); break
        pc = np.bincount(P[y == 1], minlength=13); mp = ', '.join('%s %d%%' % (POS[k], round(100 * pc[k] / max(1, pc.sum()))) for k in np.argsort(-pc)[:3])
        hv = ', '.join('%s %.0f / %.0f' % (a, A[y == 1, AB.index(a)].mean(), A[y == 0, AB.index(a)].mean()) for a, _ in top)
        out.append('| %s | %.1f %% | %s | %s | %s | %s | AUC %.2f%s |' % (n, 100 * e['rate'], ', '.join(a for a, _ in top), hv, frm, mp, e['auc'], ', safe (≥50 %) possible' if 'thr_hi' in e else ', no safe level'))
    out.append('')
out += ['## Playing styles', '', 'The playing style is mostly decided by the position; the values add information for the groups below (accuracy of a cross-validated model against the position alone):', '', '| position group | accuracy | position alone |', '|---|---|---|']
for g, v in M['styles'].items(): out.append('| %s | %.0f %% | %.0f %% |' % (g, 100 * v['acc'], 100 * v['baseline']))
open(os.path.join(HERE, '..', 'docs', 'PES_TRAITS_PROFILE.md'), 'w').write('\n'.join(out) + '\n')
print('written', len(out), 'lines')
