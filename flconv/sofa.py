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
