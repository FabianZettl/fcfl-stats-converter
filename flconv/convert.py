"""The conversion of an EA FC player (or of the page of FMInside) to the attributes of the game database - (formulas of the PES Stats Converter, scale of
the game, position balance, keeper model), but the overall of the player is the overall of the source (EA FC rating): the attributes are fitted to it, the current overall of the
game is not considered."""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'lib'))
import fcdb  # noqa: E402
import gkcal  # noqa: E402
import poscal  # noqa: E402
import sofifa  # noqa: E402
import plbin  # noqa: E402
import timeshift  # noqa: E402

AB = plbin.AB
W = {int(k): v for k, v in json.load(open(os.path.join(HERE, 'lib', 'ovr_weights_fl27.json'))).items()}
FIT_CAP = 8   # the fit to the overall changes an attribute by at most this much


def wvec(pos):
    return W.get(pos) or W.get({6: 5, 7: 5, 11: 12}.get(pos, pos)) or W[5]


def ovr_model(att, pos):
    w = wvec(pos)
    return sum(w[i] * att[a] for i, a in enumerate(AB)) + w[25]


def fit_overall(stats, pos, target, cap=FIT_CAP, lock=()):
    """round robin over the attributes that count for the position (most important first) until the overall of the model is the target -> (new stats, changes)"""
    w = wvec(pos)
    tw = sum(x for x in w[:25] if x > 0) or 1.0
    out = dict(stats)
    order = sorted((a for i, a in enumerate(AB) if w[i] > 0 and a not in lock), key=lambda a: -w[AB.index(a)])   # lock: attributes that must stay (PlayStyle bonuses)
    est = ovr_model(out, pos)
    sg = 1 if target > est else -1
    ch = {a: 0 for a in AB}
    i = 0
    while order and sg * (target - est) > 0.35 and i < len(order) * (cap + 2):
        a = order[i % len(order)]
        i += 1
        nv = out[a] + sg
        if 40 <= nv <= 99 and abs(ch[a] + sg) <= cap:
            out[a] = nv
            ch[a] += sg
            est += sg * w[AB.index(a)]
    return out, ch


EAPOS = {'GK': 0, 'CB': 1, 'LB': 2, 'LWB': 2, 'RB': 3, 'RWB': 3, 'CDM': 4, 'DMF': 4, 'CM': 5, 'CMF': 5, 'LM': 6, 'LMF': 6, 'RM': 7, 'RMF': 7, 'CAM': 8, 'AMF': 8, 'LW': 9,
         'LWF': 9, 'RW': 10, 'RWF': 10, 'SS': 11, 'CF': 12, 'ST': 12}


def fm_samples(path):
    try:
        return json.load(open(path)).get('samples') or []
    except Exception:
        return []


def _lin(pts, mode):
    mx, my = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    if mode == 'none':
        return 1.0, 0.0
    if mode == 'shift':
        return 1.0, my - mx
    vx = sum((p[0] - mx) ** 2 for p in pts)
    b = max(0.5, min(1.3, sum((p[0] - mx) * (p[1] - my) for p in pts) / vx)) if vx > 1 else 1.0
    return b, my - b * mx


def fm_fit(samples):
    """FM conversion -> EA FC conversion per attribute from players that are on both sides. For every attribute the method (nothing / shift / shift + slope) is chosen by
    leave-one-out cross validation: it is only used when it makes the error against the EA FC values clearly smaller on players it was not fitted on.
    -> {attribute: dict(n, mean, b, a, method, before, after)}"""
    out = {}
    if len(samples) < 6:
        return out
    for a in AB[:20]:
        pts = [(x['fm'][a], x['ea'][a]) for x in samples if a in x['fm'] and a in x['ea']]
        n = len(pts)
        if n < 6:
            continue
        err = {}
        for mode in ('none', 'shift', 'affine'):
            if mode == 'affine' and n < 12:
                continue
            e = []
            for i in range(n):
                b, c = _lin(pts[:i] + pts[i + 1:], mode)
                e.append(pts[i][1] - (b * pts[i][0] + c))
            err[mode] = (sum(x * x for x in e) / n) ** 0.5
        best = min(err, key=lambda m: err[m] + (0.2 if m != 'none' else 0))   # a method has to be at least 0.2 better than doing nothing
        b, c = _lin(pts, best)
        k = n / (n + 4.0)
        out[a] = dict(n=n, mean=round(sum(p[1] - p[0] for p in pts) / n, 2), b=round(1 + (b - 1) * k, 3), a=round(c * k, 2) if best == 'shift' else round((sum(p[1] for p in pts) / n - (1 + (b - 1) * k) * sum(p[0] for p in pts) / n) * (k if best != 'none' else 0), 2),
                      method=best, before=round(err['none'], 2), after=round(err[best], 2))
    return out


def fm_apply(cal, attr, v):
    c = cal.get(attr)
    if not c:
        return v
    return max(40, min(99, int(round(c['b'] * v + c['a'] + (1 - c['b']) * 0))))


def finish(fitted, pos, age, rating, months, pid, edits, form=None, devf=1.0):
    """development to the date of the write, then the values the user typed"""
    sh = timeshift.shift(fitted, pos, age if age is not None else 25.0, rating, months * devf, pid, tw=sum(x for x in wvec(pos)[:25] if x > 0) or 1.7) if months else dict(fitted)
    for a, v in (form or {}).items():   # performance since the date of the data (Sofascore)
        if a in sh:
            sh[a] = max(40, min(99, sh[a] + int(v)))
    for a, v in (edits or {}).items():
        if a in sh and v not in (None, ''):
            sh[a] = max(40, min(99, int(v)))
    return sh


def preview(pb, i, pos, ea_db=None, row=None, fm_text=None, target=None, fm_calib=None, cur=None, months=0, age=None, pid=None, edits=None, boost=None, form=None, devf=1.0):
    """-> dict(ok, rows, steps, ...) for the record i of Player.bin; cur: current values (default: Player.bin), months: development to the date of the write"""
    gk = pos == 0
    cur = cur or pb.attrs(i)
    d = dict(ok=True, pos=pos, ovr_cur=int(round(ovr_model(cur, pos))))
    xraw = None
    src_ovr = None
    if fm_text and not sofifa.is_fm(fm_text):   # page of SoFIFA (EA FC values of the page)
        raw = sofifa.parse_page(fm_text)
        miss = sofifa.missing(raw, gk)
        if miss:
            return dict(ok=False, msg='This is neither a FMInside nor a complete SoFIFA player page. Missing: %s' % ', '.join(miss[:6]))
        m = re.search(r'(\d{3}) ?cm', fm_text)
        stats = gkcal.convert_gk(raw, int(m.group(1)) if m else None) if gk else sofifa.convert(raw, False)
        xraw = raw
        sh = {}
        src_ovr = raw.get('overall')
        d['source'] = 'SoFIFA'
        d['src_ovr'] = src_ovr
        d['sofifa'] = dict(overall=raw.get('overall'), potential=raw.get('potential'))
    elif fm_text:
        raw = sofifa.parse_fm(fm_text)
        miss = sofifa.missing_fm(raw, gk)
        if miss:
            return dict(ok=False, msg='The FM page lacks: %s' % ', '.join(miss[:6]))
        stats = sofifa.convert_fm(raw, gk, pos, raw.get('overall'))
        smp = fm_samples(fm_calib) if fm_calib else []
        sh = fm_fit(smp) if not gk else {}
        d['fm'] = dict(n=len(smp), active=bool(sh))
        d['fm_est'] = raw.get('_est') or []
        d['source'] = 'FMInside'
        d['src_ovr'] = None
    elif row is not None:
        raw = ea_db.stats(row, gk)
        miss = sofifa.missing(raw, gk)
        if miss:
            return dict(ok=False, msg='The database entry lacks: %s' % ', '.join(miss[:6]))
        stats = gkcal.convert_gk(raw, row['height']) if gk else sofifa.convert(raw, False)
        xraw = raw
        sh = {}
        src_ovr = row['rating']
        d['source'] = 'EA FC'
        d['src_ovr'] = src_ovr
        d['db'] = dict(id=row['id'], name=row['name'], club=row['club'], rating=row['rating'], pos=row['pos'], nation=row['nation'])
    else:
        return dict(ok=False, msg='No source.')
    ex = (sofifa.explain_gk(xraw) if gk else sofifa.explain(xraw)) if xraw is not None else {}
    rows = []
    sc, fin0 = {}, {}
    for a in AB:
        v0 = stats.get(a, cur[a])
        v, pcd, pbd = poscal.correct(pos, a, v0) if (xraw is not None and not gk) else (v0, 0, 0)
        if sh.get(a):
            v2 = fm_apply(sh, a, v)
            pcd += v2 - v
            v = v2
        e = ex.get(a) or {}
        sc[a] = max(40, min(99, v0 + pcd))
        bo = (boost or {}).get(a, 0)
        fin0[a] = min(99, v + bo) if bo else v   # bonus of the PlayStyles: the overall is fitted afterwards, the other attributes give way
        rows.append(dict(attr=a, cur=cur[a], sofifa=v0, pc=pcd, pb=pbd, conv=v, base=e.get('base'), adj=(v0 - e['base']) if e.get('base') is not None else None,
                         src=e.get('src'), rule=e.get('rule'), model=bool(e.get('model'))))
    tgt = target if target is not None else src_ovr
    fitted0, ch = (fit_overall(fin0, pos, tgt, lock=set(boost or ())) if tgt is not None else (fin0, {a: 0 for a in AB}))
    fitted = finish(fitted0, pos, age, tgt if tgt is not None else ovr_model(fitted0, pos), months, pid or 0, edits, form, devf)
    w = wvec(pos)
    for r in rows:
        r['fit'] = ch[r['attr']]
        r['ps'] = (boost or {}).get(r['attr'], 0)
        r['ts'] = fitted[r['attr']] - fitted0[r['attr']]
        r['edited'] = bool(edits and edits.get(r['attr']) not in (None, '')) 
        r['final'] = fitted[r['attr']]
        r['oe'] = round(w[AB.index(r['attr'])] * (r['final'] - r['cur']), 2)
    addon = {a: stats.get(a, cur[a]) for a in AB}
    d.update(rows=rows, ovr_target=tgt, ovr_new=int(round(ovr_model(fitted, pos))),
             steps=dict(cur=d['ovr_cur'], addon=int(round(ovr_model(addon, pos))), scale=int(round(ovr_model(sc, pos))), pos=int(round(ovr_model(fin0, pos))), fit=int(round(ovr_model(fitted0, pos))), final=int(round(ovr_model(fitted, pos)))),
             final={a: fitted[a] for a in AB})
    return d


# the game rates players about this much higher than EA FC (mean over the players that are in both, by age): used to bring players that are not in the EA FC export to the EA level
AGE_OFF = [(18, 2.3), (19, 3.5), (20, 3.9), (21, 4.1), (22, 4.2), (23, 4.4), (25, 4.2), (28, 3.9), (31, 3.6), (99, 3.3)]


def age_offset(age):
    for lim, v in AGE_OFF:
        if (age or 26) <= lim:
            return v
    return 3.3


def scale_player(pb, i, pos, age, cur=None, months=0, pid=None, edits=None, form=None, devf=1.0):
    """a player that is not in the EA FC export: the profile stays, the level goes down by the usual difference of the game to EA FC (fit to the overall of the model)
    -> dict like preview()"""
    cur = cur or pb.attrs(i)
    o0 = ovr_model(cur, pos)
    tgt = max(40, int(round(o0 - age_offset(age))))
    fitted0, ch = fit_overall(cur, pos, tgt)
    fitted = finish(fitted0, pos, age, tgt, months, pid or 0, edits, form, devf)
    w = wvec(pos)
    rows = [dict(attr=a, cur=cur[a], final=fitted[a], fit=ch[a], oe=round(w[AB.index(a)] * (fitted[a] - cur[a]), 2)) for a in AB]
    return dict(ok=True, rows=rows, final={a: fitted[a] for a in AB}, ovr_cur=int(round(o0)), ovr_new=int(round(ovr_model(fitted, pos))), ovr_target=tgt, source='scaled',
                steps=dict(cur=int(round(o0)), fit=int(round(ovr_model(fitted0, pos))), final=int(round(ovr_model(fitted, pos)))))
