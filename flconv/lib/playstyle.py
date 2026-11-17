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
    skills, com = set(), set()
    for st, plus in styles.items():
        m = MAP['skills'].get(st)
        if not m:
            continue
        if any((raw or {}).get(k) is not None and int((raw or {}).get(k)) < v for k, v in (m.get('min') or {}).items()):
            continue
        skills.update(m.get('skills') or [])
        com.update(m.get('com') or [])
        if plus:
            skills.update(m.get('plus') or [])
        if m.get('one_of'):   # one of several: the same one for the same player every time
            skills.add(m['one_of'][zlib.crc32(('%s%d' % (st, pid)).encode()) % len(m['one_of'])])
    style = None
    for r in MAP['styles']:
        if pos in r['pos'] and sum(1 for n in r['need'] if n in styles) >= r['min']:
            style = r['style']
            break
    return dict(skills=skills, com=com, style=style)


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
