"""Skills, COM playing styles and playing style of PES 21 from the PlayStyles of EA FC (mapping: data/playstyle_map.json, own proposal, see docs/PLAYSTYLE_MAPPING.md)."""
import json
import os
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
MAP = json.load(open(os.path.join(HERE, '..', 'data', 'playstyle_map.json'), encoding='utf-8'))


def parse(text):
    """'Rapid|Technical+' -> {'Rapid': False, 'Technical': True} (True = PlayStyle+)"""
    out = {}
    for t in str(text or '').split('|'):
        t = t.strip()
        if t:
            out[t.rstrip('+')] = out.get(t.rstrip('+'), False) or t.endswith('+')
    return out


def derive(styles, pos, raw=None, pid=0):
    """-> dict(skills, com, style): what the PlayStyles of EA FC (dict from parse) give; style None = no rule applies (keep the current one)"""
    skills, com, direct, direct_com = set(), set(), set(), set()
    for st, plus in styles.items():
        m = MAP['skills'].get(st)
        if not m:
            continue
        if any((raw or {}).get(k) is not None and int((raw or {}).get(k)) < v for k, v in (m.get('min') or {}).items()):
            continue
        skills.update(m.get('skills') or [])
        com.update(m.get('com') or [])
        direct.update(m.get('direct') or [])
        direct_com.update(m.get('direct_com') or [])
        if plus:
            skills.update(m.get('plus') or [])
        if m.get('one_of'):   # one of several: the same one for the same player every time
            skills.add(m['one_of'][zlib.crc32(('%s%d' % (st, pid)).encode()) % len(m['one_of'])])
    style = None
    for r in MAP['styles']:
        if pos in r['pos'] and sum(1 for n in r['need'] if n in styles) >= r['min']:
            style = r['style']
            break
    return dict(skills=skills, com=com, style=style, direct=direct & skills, direct_com=direct_com & com)


def boosts(styles):
    """-> {attribute: bonus} from the PlayStyles (dict from parse): PlayStyle +1 / PlayStyle+ +2 for 'always', only PlayStyle+ (+1) for 'plus'; the biggest bonus per attribute"""
    out = {}
    for st, plus in styles.items():
        b = MAP['boost'].get(st)
        if not b:
            continue
        v = (2 if plus else 1) if b['mode'] == 'always' else (1 if plus else 0)
        for a in b['attrs']:
            if v > out.get(a, 0):
                out[a] = v
    return out


_MODEL = []
STYLE_MIN_AUC = 0.70   # a playing style is only given when the values tell it apart at least this well


def _model():
    if not _MODEL:
        try:
            _MODEL.append(json.load(open(os.path.join(HERE, '..', 'data', 'skill_model.json'))))
        except OSError:
            _MODEL.append({})
    return _MODEL[0]


def _score(v, x):
    return sum(w * a for w, a in zip(v['w'], x)) + v['b']


def values_fit(raw, pos):
    """the skills and COM playing styles whose values make them SAFE for the player (cross-validated share of right ones at least 50 %, tools/fit_skills.py), whatever the PlayStyles say:
    -> (skills, com). A skill is only given when EA FC has the PlayStyle AND this test is passed."""
    m = _model()
    if not m:
        return set(), set()
    gk = pos == 0
    try:
        x = [float(raw[c]) for c in (m['gk_attrs'] if gk else m['attrs'])]
    except (KeyError, TypeError, ValueError):
        return set(), set()
    # 'thr_hi' = the values alone make the skill at least 50 % sure (cross-validated); skills for which the values never reach that are never given (they cannot be given safely)
    sk = {n for n, v in (m['gk_skills'] if gk else m['skills']).items() if 'thr_hi' in v and _score(v, x) >= v['thr_hi']}
    cm = {n for n, v in ({} if gk else m['com']).items() if 'thr_hi' in v and _score(v, x) >= v['thr_hi']}
    return sk, cm


def style_fits(style, raw, pos):
    """does the playing style fit the values? Only styles that the values tell apart (AUC >= STYLE_MIN_AUC) are given at all"""
    v = (_model().get('styles') or {}).get(style)
    if not v or v['auc'] < STYLE_MIN_AUC:
        return False
    try:
        x = [float(raw[c]) for c in (_model()['gk_attrs'] if pos == 0 else _model()['attrs'])]
    except (KeyError, TypeError, ValueError):
        return False
    return _score(v, x) >= v['thr']


# --- players that are not in the EA FC data: skills, COM styles, playing style and positions from their own values and their position, with the models fitted on the players of
# the game (tools/fit_pes_traits.py, tools/fit_positions.py)
AB = ['OffensiveAwareness', 'BallControl', 'Dribbling', 'TightPossession', 'LowPass', 'LoftedPass', 'Finishing', 'Heading', 'PlaceKicking', 'Curl', 'Speed', 'Acceleration', 'KickingPower',
      'Jump', 'PhysicalContact', 'Balance', 'Stamina', 'DefensiveAwareness', 'BallWinning', 'Aggression', 'GKAwareness', 'GKCatching', 'GKClearing', 'GKReflexes', 'GKReach']
_M = {}


def _load(name):
    if name not in _M:
        try:
            _M[name] = json.load(open(os.path.join(HERE, '..', 'data', name)))
        except OSError:
            _M[name] = {}
    return _M[name]


def traits_from_values(attrs, pos):
    """-> dict(skills, com, style): what the values and the position make safe (a skill: the model is at least 50 % sure); style None = keep the current one"""
    m = _load('pes_traits_model.json')
    if not m:
        return dict(skills=set(), com=set(), style=None)
    x = [float(attrs[a]) for a in AB]
    if pos == 0:
        sk = {n for n, v in m['gk_skills'].items() if 'thr_hi' in v and sum(w * a for w, a in zip(v['w'], x)) + v['b'] >= v['thr_hi']}
        return dict(skills=sk, com=set(), style=None)
    xf = x + [1.0 if pos == k else 0.0 for k in range(13)]
    sk = {n for n, v in m['skills'].items() if 'thr_hi' in v and sum(w * a for w, a in zip(v['w'], xf)) + v['b'] >= v['thr_hi']}
    cm = {n for n, v in m['com'].items() if 'thr_hi' in v and sum(w * a for w, a in zip(v['w'], xf)) + v['b'] >= v['thr_hi']}
    style = None
    for g, ps in m['style_groups'].items():
        v = m['styles'].get(g)
        if pos in ps and v and v['acc'] >= v['baseline'] + 0.05:   # only where the values tell more than the position alone
            W = v['W']
            z = [(a - mu) / sd for a, mu, sd in zip(xf, m['mu'], m['sd'])]
            S = [sum(zz * W[j][k] for j, zz in enumerate(z)) for k in range(len(m['style_names']))]
            mx = max(S); P = [pow(2.718281828, s_ - mx) for s_ in S]; t = sum(P)
            k = max(range(len(P)), key=lambda q: P[q])
            if P[k] / t >= 0.5:
                style = m['style_names'][k]
    return dict(skills=sk, com=cm, style=style)


_PNAMES = ['GK', 'CB', 'LB', 'RB', 'DMF', 'CMF', 'LMF', 'RMF', 'AMF', 'LWF', 'RWF', 'SS', 'CF']
_EAPOS = {'GK': 0, 'CB': 1, 'LB': 2, 'LWB': 2, 'RB': 3, 'RWB': 3, 'CDM': 4, 'CM': 5, 'LM': 6, 'RM': 7, 'CAM': 8, 'LW': 9, 'RW': 10, 'ST': 12, 'CF': 12}
RELAX = 1.5   # an alternative position of EA FC needs a model score only this far (logit units) under the safe bar


def positions_from_values(attrs, main, ea_alt=(), only_alt=False):
    """-> list of 13 levels (0 none, 1 competent, 2 natural) that the values and the main position make safe: the main position is natural; another position is added when the model is
    sure (precision 60 %), or when EA FC lists it as an alternative position and the model is not far under the bar (only_alt: only the second way). Natural (2) only where the
    'natural' model is sure."""
    m = _load('position_model.json')
    lv = [0] * 13
    lv[main] = 2
    if not m or main == 0:
        return lv
    xf = [float(attrs[a]) for a in AB] + [1.0 if main == k else 0.0 for k in range(1, 13)]
    alt = {_EAPOS[a] for a in ea_alt if a in _EAPOS}
    for p in range(1, 13):
        if p == main:
            continue
        v = m['plays'].get(_PNAMES[p])
        if not v:
            continue
        sc = sum(w * a for w, a in zip(v['w'], xf)) + v['b']
        if (not only_alt and 'thr_hi' in v and sc >= v['thr_hi']) or (p in alt and 'thr_hi' in v and sc >= v['thr_hi'] - RELAX):
            lv[p] = 1
            n = m['natural'].get(_PNAMES[p])
            if n and 'thr_hi' in n and sum(w * a for w, a in zip(n['w'], xf)) + n['b'] >= n['thr_hi']:
                lv[p] = 2
    return lv
