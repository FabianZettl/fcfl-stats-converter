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
