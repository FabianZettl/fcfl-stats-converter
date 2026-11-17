"""Calibration of the FM conversion: players that are in the EA FC database and on FMInside give pairs (FM conversion, EA FC conversion); the fit (convert.fm_fit) moves the
FM values to the level of the EA FC values per attribute."""
import json
import os
import re
import time

import convert
import fcdb
import poscal
import sofifa

HEAD = re.compile(r'(?=FMInside\s*Football Manager community since 2004)')


def split_pages(text):
    parts = [p for p in HEAD.split(text or '') if sofifa.is_fm(p)]
    return parts or ([text] if sofifa.is_fm(text or '') else [])


def info(page):
    m = re.search(r'\n([^\n]+?) is an? (\d+)-year-old ([A-Z, ]+?) for (.+?) in Football Manager', page)
    if not m:
        m2 = re.search(r'Name: ([^\n]+)', page)
        return dict(name=m2.group(1).strip() if m2 else '', club='')
    return dict(name=m.group(1).strip(), age=int(m.group(2)), pos=m.group(3).strip(), club=m.group(4).strip())


def add(text, ea_db, path):
    pages = split_pages(text)
    samples = convert.fm_samples(path)
    rep = []
    for pg in pages:
        i = info(pg)
        raw = sofifa.parse_fm(pg)
        if raw.get('_est'):
            rep.append(dict(name=i.get('name'), ok=False, msg='hidden or ranged attributes (%s): log in to FMInside or take a page with exact values' % ', '.join(raw['_est'])))
            continue
        if sofifa.missing_fm(raw, False):
            rep.append(dict(name=i.get('name'), ok=False, msg='goalkeeper or incomplete page'))
            continue
        m = ea_db.match(i.get('name', ''), i.get('club'), None, False)
        if m['status'] != 'ok':
            rep.append(dict(name=i.get('name'), ok=False, msg='not found in the EA FC database' if m['status'] == 'none' else 'several players with this name'))
            continue
        row = m['row']
        pos = convert.EAPOS.get(row['pos'], 5)
        if pos == 0:
            rep.append(dict(name=i.get('name'), ok=False, msg='goalkeeper'))
            continue
        base = sofifa.convert(ea_db.stats(row, False), False)
        ea = {a: poscal.correct(pos, a, v)[0] for a, v in base.items() if not a.startswith('GK')}
        fm = {a: v for a, v in sofifa.convert_fm(raw, False, pos, raw.get('overall')).items() if not a.startswith('GK')}
        samples = [x for x in samples if x.get('name') != row['name']] + [dict(name=row['name'], pos=pos, fm=fm, ea=ea)]
        rep.append(dict(name=row['name'], ok=True, club=row['club']))
    json.dump(dict(samples=samples), open(path, 'w'), ensure_ascii=False, indent=1)
    return rep, samples


def view(path):
    S = convert.fm_samples(path)
    cal = convert.fm_fit(S)
    names = [x.get('name') for x in S]
    return dict(ok=True, n=len(S), active=bool(cal), names=names, attrs=[dict(attr=a, **cal[a]) for a in convert.AB[:20] if a in cal],
                diff=[dict(attr=a, mean=round(sum(d) / len(d), 1), sd=round((sum((x - sum(d) / len(d)) ** 2 for x in d) / len(d)) ** .5, 1)) for a in convert.AB[:20]
                      for d in [[x['ea'][a] - x['fm'][a] for x in S if a in x['fm'] and a in x['ea']]] if d] if S else [])
