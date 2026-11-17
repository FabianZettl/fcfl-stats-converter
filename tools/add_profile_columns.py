#!/usr/bin/env python3
"""One-off data preparation: adds weight, foot, weak_foot and skill_moves to flconv/data/fc27-players.csv.
  python3 tools/add_profile_columns.py ea.json [fifplay.csv]
ea.json: the player list of the official EA ratings page (drop-api.ea.com/rating/ea-sports-fc, pages of 100 pulled one after the other, the field playerAbilities is not needed);
the join is on the EA player id (stats_id). fifplay.csv (optional): the FIFPlay export on Kaggle, its foot values (FC 27) win over those of the ratings page.
Heights that are missing in the CSV are filled from the ratings page, too."""
import csv, json, sys, os
src = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv', 'data', 'fc27-players.csv')
api = {str(x['id']): x for x in json.load(open(sys.argv[1]))}
fifp = {}
if len(sys.argv) > 2:
    for r in csv.DictReader(open(sys.argv[2], encoding='utf-8-sig')):
        fifp[r['stats_id']] = r
rows = list(csv.DictReader(open(src, encoding='utf-8-sig')))
cols = list(rows[0].keys())
for c in ('weight', 'foot', 'weak_foot', 'skill_moves'):
    if c not in cols:
        cols.append(c)
n = dict(weight=0, foot=0, height=0)
for r in rows:
    a, f = api.get(r['stats_id']), fifp.get(r['stats_id'])
    r['weight'] = str(a['weight']) if a and a.get('weight') else r.get('weight', '')
    foot = (f or {}).get('foot') or ({1: 'Right', 2: 'Left'}.get(a.get('preferredFoot')) if a else '') or r.get('foot', '')
    r['foot'] = foot
    r['weak_foot'] = (f or {}).get('weak_foot') or (str(a['weakFootAbility']) if a and a.get('weakFootAbility') else r.get('weak_foot', ''))
    r['skill_moves'] = (f or {}).get('skill_moves') or (str(a['skillMoves']) if a and a.get('skillMoves') else r.get('skill_moves', ''))
    if not r.get('height') and a and a.get('height'):
        r['height'] = str(a['height']); n['height'] += 1
    n['weight'] += bool(r['weight']); n['foot'] += bool(r['foot'])
with open(src, 'w', encoding='utf-8', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader(); w.writerows(rows)
print(len(rows), 'rows; weight', n['weight'], 'foot', n['foot'], 'height filled', n['height'])
