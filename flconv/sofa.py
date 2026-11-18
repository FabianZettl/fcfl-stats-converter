"""Sofascore (unofficial JSON, no key): the last match of a team with its line-up and shirt numbers. Plain `curl` (urllib is turned away), at most one call every 0.5 s, every answer is
cached in the data folder (a finished match never changes). shortcut: nothing here is promised by Sofascore, if the calls stop working the module is the only place to fix."""
import hashlib
import json
import os
import subprocess
import time

BASE = 'https://api.sofascore.com/api/v1/'
CACHE = [os.path.join(os.path.expanduser('~'), '.cache', 'fl-stats-converter-sofa')]
_last = [0.0]


def get(path, ttl=None):
    """JSON of an endpoint; ttl seconds (None = for ever) for the cache"""
    os.makedirs(CACHE[0], exist_ok=True)
    f = os.path.join(CACHE[0], hashlib.md5(path.encode()).hexdigest() + '.json')
    if os.path.isfile(f) and (ttl is None or time.time() - os.path.getmtime(f) < ttl):
        return json.load(open(f, encoding='utf-8'))
    time.sleep(max(0.0, 0.5 - (time.time() - _last[0])))
    try:
        r = subprocess.run(['curl', '-s', '-f', '-m', '25', BASE + path], capture_output=True)
    except FileNotFoundError:
        raise OSError('curl was not found (needed to ask Sofascore)')
    _last[0] = time.time()
    if r.returncode:
        raise OSError('Sofascore did not answer (%s, curl %d)' % (path, r.returncode))
    d = json.loads(r.stdout)
    json.dump(d, open(f, 'w', encoding='utf-8'))
    return d


def find_team(name):
    """[(id, name, country)] of football clubs"""
    q = name.replace(' ', '%20')
    out = []
    for x in get('search/teams?q=' + q, 30 * 86400).get('results', []):
        e = x.get('entity') or {}
        if e.get('sport', {}).get('slug') == 'football' and not e.get('national'):
            out.append((e['id'], e.get('name', ''), (e.get('country') or {}).get('name', '')))
    return out


def last_lineup(team_id):
    """the newest finished match of the team: dict(event, date, home, opponent, formation, players=[dict(name, no, pos, sub, rating, minutes)]) or None"""
    ev = [e for e in get('team/%d/events/last/0' % team_id, 3600).get('events', []) if e.get('status', {}).get('type') == 'finished']
    if not ev:
        return None
    e = max(ev, key=lambda x: x['startTimestamp'])
    L = get('event/%d/lineups' % e['id'])
    home = e['homeTeam']['id'] == team_id
    side = L.get('home' if home else 'away') or {}
    pl = [dict(name=p['player']['name'], no=p.get('shirtNumber') or p.get('jerseyNumber'), pos=p.get('position'), sub=bool(p.get('substitute')),
               rating=(p.get('statistics') or {}).get('rating'), minutes=(p.get('statistics') or {}).get('minutesPlayed')) for p in side.get('players', [])]
    return dict(event=e['id'], date=time.strftime('%d.%m.%Y', time.localtime(e['startTimestamp'])), home=home, opponent=e['awayTeam' if home else 'homeTeam']['name'],
                formation=side.get('formation'), players=pl)


ASPECT = {'pass': 'passValueNormalized', 'dribble': 'dribbleValueNormalized', 'defensive': 'defensiveValueNormalized', 'shot': 'shotValueNormalized', 'goalkeeper': 'goalkeeperValueNormalized'}


def team_form(team_id, since):
    """what every player of the team did in the finished matches since `since` (unix time): {name: dict(n, minutes, rating, goals, assists, asp={aspect: value})}; rating and the
    aspect values (Sofascore's own per-match value of passing / dribbling / defending / shooting / goalkeeping, 0 = as expected) are weighted by minutes"""
    evs, page = [], 0
    while page < 6:
        d = get('team/%d/events/last/%d' % (team_id, page), 3600)
        es = d.get('events', [])
        evs += es
        if not es or not d.get('hasNextPage') or min(e['startTimestamp'] for e in es) < since:
            break
        page += 1
    out = {}
    for e in sorted(evs, key=lambda x: x['startTimestamp']):
        if e.get('status', {}).get('type') != 'finished' or e['startTimestamp'] < since:
            continue
        side = get('event/%d/lineups' % e['id']).get('home' if e['homeTeam']['id'] == team_id else 'away') or {}
        for p in side.get('players', []):
            st = p.get('statistics') or {}
            mn = st.get('minutesPlayed') or 0
            if mn < 1 or st.get('rating') is None:
                continue
            o = out.setdefault(p['player']['name'], dict(n=0, minutes=0, rsum=0.0, goals=0, assists=0, asum={}, amin={}))
            o['n'] += 1
            o['minutes'] += mn
            o['rsum'] += st['rating'] * mn
            o['goals'] += st.get('goals') or 0
            o['assists'] += st.get('goalAssist') or 0
            for k, f in ASPECT.items():
                if st.get(f) is not None:
                    o['asum'][k] = o['asum'].get(k, 0.0) + st[f] * mn
                    o['amin'][k] = o['amin'].get(k, 0) + mn
    for name, o in out.items():
        o['rating'] = o['rsum'] / o['minutes']
        o['asp'] = {k: o['asum'][k] / o['amin'][k] for k in o['asum']}
        for k in ('rsum', 'asum', 'amin'):
            del o[k]
    return out
