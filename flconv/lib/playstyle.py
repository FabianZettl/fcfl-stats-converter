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


def from_values(raw, pos):
    """skills and COM playing styles that the EA FC values alone make clear (the share of right ones is at least 50 %, fitted on the players that are in the game and in the EA data, tools/fit_skills.py);
    raw: the attribute columns of the EA FC entry"""
    if not _MODEL:
        try:
            _MODEL.append(json.load(open(os.path.join(HERE, '..', 'data', 'skill_model.json'))))
        except OSError:
            _MODEL.append({})
    m = _MODEL[0]
    if not m:
        return set(), set()
    gk = pos == 0
    names = m['gk_attrs'] if gk else m['attrs']
    try:
        x = [float(raw[c]) for c in names]
    except (KeyError, TypeError, ValueError):
        return set(), set()
    sk, cm = set(), set()
    for grp, out in ((m['gk_skills'] if gk else m['skills']), sk), ((m['com'] if not gk else {}), cm):
        for n, v in grp.items():
            if 'thr_hi' in v and sum(w * a for w, a in zip(v['w'], x)) + v['b'] >= v['thr_hi']:
                out.add(n)
    sk.discard('Captaincy')
    return sk, cm
