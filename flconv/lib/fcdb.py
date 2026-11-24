"""EA FC player database (CSV export, e.g. fc27-players-2026-10-11.csv): load, find the player of the game in it (unambiguous only) and give the stats in the form
of sofifa.convert (keys like 'crossing', 'attpos', 'defaw', ...), so the import of a player and of a whole team uses the same conversion and rules."""
import csv
import glob
import os
import re
import time
import unicodedata

_STOP = {'fc', 'cf', 'afc', 'sc', 'ac', 'as', 'ssc', 'club', 'fk', 'bk', 'sk', 'if', 'sv', 'vfb', 'vfl', 'tsg', 'cd', 'ud', 'sd', 'rc', 'us', 'ff', 'de', 'del', 'la', 'le', 'the', '1', 'calcio',
         'football', 'futbol', 'futebol', 'city', 'united', 'town', 'real', 'sporting', 'athletic', 'atletico'}
# CSV column -> key of sofifa.convert
COLS = {'crossing': 'crossing', 'finishing': 'finishing', 'heading': 'heading', 'short_passing': 'short', 'volleys': 'volleys', 'ball_control': 'ballcontrol', 'curve': 'curve',
        'dribbling': 'dribbling', 'free_kick_accuracy': 'fk', 'long_passing': 'long', 'acceleration': 'acceleration', 'agility': 'agility', 'balance': 'balance', 'reactions': 'reactions',
        'sprint_speed': 'sprint', 'jumping': 'jumping', 'long_shots': 'longshots', 'shot_power': 'shotpower', 'stamina': 'stamina', 'strength': 'strength', 'aggression': 'aggression',
        'positioning': 'attpos', 'composure': 'composure', 'interceptions': 'interceptions', 'penalties': 'penalties', 'vision': 'vision', 'def_awareness': 'defaw',
        'standing_tackle': 'standing', 'sliding_tackle': 'sliding', 'gk_diving': 'gkdiving', 'gk_handling': 'gkhandling', 'gk_kicking': 'gkkicking', 'gk_positioning': 'gkpositioning',
        'gk_reflexes': 'gkreflexes'}


def fold(s):
    s = unicodedata.normalize('NFKD', str(s or '')).replace('ø', 'o').replace('Ø', 'O').replace('đ', 'd').replace('ł', 'l').replace('ß', 'ss').replace('ı', 'i').replace('İ', 'I')
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in s if not unicodedata.combining(c)).lower()).strip()


_ALIAS = {'spurs': 'tottenham hotspur', 'paris sg': 'paris saint germain', 'man utd': 'manchester united', 'man city': 'manchester city', 'athletic club': 'athletic bilbao',
          'atletico madrid': 'atletico de madrid', 'inter': 'internazionale', 'wolves': 'wolverhampton wanderers', 'newcastle': 'newcastle united', 'brighton': 'brighton hove albion',
          'west ham': 'west ham united', 'leeds': 'leeds united', 'm gladbach': 'borussia monchengladbach', 'dortmund': 'borussia dortmund', 'leverkusen': 'bayer leverkusen',
          'rb leipzig': 'rb leipzig', 'ol': 'olympique lyonnais', 'om': 'olympique de marseille', 'sunderland': 'sunderland'}


def club_key(c):
    f = fold(c)
    f = _ALIAS.get(f, f)
    return frozenset(w for w in f.split() if w not in _STOP and len(w) > 1)


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _year(v):
    m = re.search(r'(\d{4})\s*$', str(v or ''))
    return int(m.group(1)) if m else None


def _date(v):
    """'24-11-2026' or '2026-11-24' -> (2026, 11, 24), else None"""
    m = re.match(r'\s*(\d{1,2})[-./](\d{1,2})[-./](\d{4})', str(v or ''))
    if m:
        return int(m.group(3)), int(m.group(2)), int(m.group(1))
    m = re.match(r'\s*(\d{4})-(\d{2})-(\d{2})', str(v or ''))
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def _read(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return [r for r in csv.DictReader(f) if r.get('club_name') not in ('ICON', 'Hero') and r.get('rating')]   # special cards are no real squads


def update_files(folder):
    """The SoFIFA updates in a folder (every csv with the columns base_id and snapshot), oldest first: [dict(path, name, date)]. The date of an update is the newest snapshot in it, else a date in the
    file name (fc27-players-2026-11-24.csv), else the day the file was changed."""
    out = []
    for path in sorted(glob.glob(os.path.join(folder or '', '*.csv'))):
        try:
            with open(path, encoding='utf-8-sig', newline='') as f:
                rd = csv.DictReader(f)
                if not rd.fieldnames or 'base_id' not in rd.fieldnames or 'rating' not in rd.fieldnames:
                    continue
                snap = max((d for d in (_date(r.get('snapshot')) for r in rd) if d), default=None)
        except OSError:
            continue
        m = re.search(r'(\d{4})[-_.]?(\d{2})[-_.]?(\d{2})', os.path.basename(path))
        mt = time.localtime(os.path.getmtime(path))
        fdate = (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (mt.tm_year, mt.tm_mon, mt.tm_mday)
        out.append(dict(path=path, name=os.path.basename(path), date=snap or fdate, mtime=os.path.getmtime(path)))
    return sorted(out, key=lambda u: (u['date'], u['mtime']))


class DB:
    def __init__(self, path, updates=()):
        """path: the standard database; updates: update_files(...) - a player of an update replaces the player of the same base_id when its snapshot (else the date of the file) is not older"""
        self.path = path
        self.rows = []
        self.by_full = {}
        self.by_last = {}
        self.updates = []   # [dict(name, date, rows, used)]
        base = _read(path)
        cur = {}   # base_id -> (date, row dict, label)
        for r in base:
            cur[r.get('base_id') or r['stats_id']] = (_date(r.get('snapshot')) or (), r, 'standard')
        for u in updates:
            n = used = 0
            for r in _read(u['path']):
                n += 1
                k, d = r.get('base_id') or r.get('stats_id'), _date(r.get('snapshot')) or u['date']
                if k not in cur or d >= (cur[k][0] or ()):
                    cur[k] = (d, r, u['name'])
            self.updates.append(dict(name=u['name'], date=u['date'], rows=n))
        for lab in {v[2] for v in cur.values()}:
            for u in self.updates:
                if u['name'] == lab:
                    u['used'] = sum(1 for v in cur.values() if v[2] == lab)
        for d, r, lab in cur.values():
            first, last = fold(r.get('first_name')), fold(r.get('last_name'))
            row = dict(id=r['stats_id'] or r['base_id'], name='%s %s' % (r.get('first_name', ''), r.get('last_name', '')) if not r.get('common_name') else r['common_name'],
                       full=(first + ' ' + last).strip(), first=first, last=last, club=r.get('club_name', ''), ck=club_key(r.get('club_name')), nation=r.get('nation_name', ''),
                       pos=r.get('position', ''), alt=[r.get(k, '') for k in ('position_alt', 'position_alt_2', 'position_alt_3') if r.get(k)], rating=_int(r.get('rating')),
                       potential=_int(r.get('potential')), height=_int(r.get('height')), byear=_year(r.get('birthdate')), raw=r, upd=None if lab == 'standard' else lab, upd_date=d)
            self.rows.append(row)
            for k in {row['full'], fold(r.get('common_name')), fold(r.get('full_name'))}:
                if k:
                    self.by_full.setdefault(k, []).append(row)
            lt = last.split()
            for i in range(len(lt)):   # indexed under every part of the surname: 'strand larsen', 'larsen' and 'strand' (Grimaldo in Grimaldo Garcia)
                for j in range(i + 1, len(lt) + 1):
                    self.by_last.setdefault(' '.join(lt[i:j]), []).append(row)

    def stats(self, row, gk=False):
        """-> dict in the form of sofifa.parse_page + overall/potential. Keepers have no field attributes in the export: they get a low value."""
        out = {}
        for col, key in COLS.items():
            v = _int(row['raw'].get(col))
            if v is None and gk and not key.startswith('gk'):
                v = 25
            if v is not None:
                out[key] = v
        out['overall'], out['potential'] = row['rating'], row['potential']
        return out

    def search(self, q, limit=14):
        """Free search by name / club / nation (all words must appear), best rated first."""
        words = fold(q).split()
        if not words:
            return []
        out = []
        for x in self.rows:
            blob = ' '.join([x['full'], fold(x['raw'].get('common_name')), fold(x['raw'].get('full_name')), fold(x['club']), fold(x['nation'])])
            if all(w in blob for w in words):
                out.append((0 if x['full'].startswith(words[0]) or x['last'].startswith(words[0]) else 1, -x['rating'], x))
        out.sort(key=lambda t: (t[0], t[1]))
        return [t[2] for t in out[:limit]]

    def match(self, name, club=None, nation=None, gk=None, db_id=None, ovr=None, age=None, height=None):
        """-> dict(status 'ok'|'ambiguous'|'none', row, candidates, why). Only an unambiguous player is taken."""
        if db_id:
            r = next((x for x in self.rows if x['id'] == str(db_id)), None)
            return dict(status='ok' if r else 'none', row=r, candidates=[], why='chosen')
        n = fold(name)
        parts = n.split()
        if not parts:
            return dict(status='none', row=None, candidates=[], why='no name')
        cand = list(self.by_full.get(n, []))
        why = 'name'
        if not cand and len(parts) >= 2:   # spelling differences, initials ('J. Strand Larsen') and long surnames: ending of the surname + first name starts the same
            seen = set()
            for k in range(1, min(3, len(parts) - 1) + 1):
                last, f1 = ' '.join(parts[-k:]), parts[0]
                for x in self.by_last.get(last, []):
                    f2 = x['first'].split()[0] if x['first'] else ''
                    if id(x) not in seen and f1 and f2 and (len(f1) == 1 and f2[0] == f1 or f1[:3] == f2[:3] or f1.startswith(f2) or f2.startswith(f1)):
                        seen.add(id(x))
                        cand.append(dict(x, loose=(x['last'] != last)))   # loose: only the end of a longer surname matches (Carvajal in Olmo Carvajal)
            if not cand and len(parts) >= 2:   # all words of the name are part of the full name (Gabriel Magalhaes = Gabriel Dos Santos Magalhaes)
                ps = set(parts)
                cand = [x for x in self.by_last.get(parts[-1], []) if ps <= set((x['first'] + ' ' + x['last']).split()) | set(fold(x['raw'].get('common_name')).split())]
            why = 'surname'
        if gk is not None:
            cand = [x for x in cand if (x['pos'] == 'GK') == bool(gk)]
        if not cand:
            return dict(status='none', row=None, candidates=[], why='not in the database')
        ck = club_key(club) if club else frozenset()

        def uniq(L):   # the same player listed twice (old club) counts as one when the stats are the same
            seen, out = set(), []
            for x in L:
                k = (x['rating'], x['raw'].get('sprint_speed'), x['raw'].get('finishing'), x['raw'].get('short_passing'), x['raw'].get('strength'), x['raw'].get('gk_reflexes'))
                if k not in seen:
                    seen.add(k)
                    out.append(x)
            return out
        age_d = lambda x: abs(2026 - x['byear'] - age) if (age and x.get('byear')) else None
        h_d = lambda x: abs(x['height'] - height) if (height and x.get('height')) else None
        L = uniq([x for x in cand if not x.get('loose')])
        if L:
            # the full name decides; the club is not used (players move), the overall only at the very end.
            # narrowing, each step only when it leaves someone: year of birth (+-2), height (+-3 cm), nation, club, overall (the game's overall is about 4 above EA FC)
            steps = [(lambda x: age_d(x) is not None and age_d(x) <= 2, 'age'), (lambda x: h_d(x) is not None and h_d(x) <= 3, 'height'),
                     (lambda x: bool(nation) and fold(x['nation']) == fold(nation), 'nation'), (lambda x: bool(ck and x['ck'] and (x['ck'] & ck)), 'club'),
                     (lambda x: ovr is not None and abs(x['rating'] + 4 - ovr) <= 6, 'overall')]
            used = []
            for f, nm in steps:
                if len(L) == 1:
                    break
                L2 = [x for x in L if f(x)]
                if L2 and len(L2) < len(L):
                    L, used = L2, used + [nm]
            if len(L) == 1:
                x = L[0]
                if (age_d(x) or 0) > 3 and not (ck and x['ck'] and (x['ck'] & ck)):   # one player with this name, but the age clearly differs (the heights of the game are too often different to count): ask
                    return dict(status='ambiguous', row=None, candidates=[x], why='the only entry with this name, but the age differs: please confirm')
                return dict(status='ok', row=x, candidates=[], why=why + ('+' + '+'.join(used) if used else ''))
            return dict(status='ambiguous', row=None, candidates=L[:8], why='several players with this name')
        L = uniq([x for x in cand if x.get('loose') and ck and x['ck'] and (x['ck'] & ck)])   # only the end of a longer surname: the club must fit
        if len(L) == 1:
            return dict(status='ok', row=L[0], candidates=[], why=why + '+club')
        return dict(status='none', row=None, candidates=[], why='not in the database')


_CACHE = {}


def load(path, folder=None):
    """the standard database plus the updates in `folder` (see update_files); worked out again when a file changes"""
    ups = update_files(folder) if folder else []
    key = (os.path.getmtime(path), tuple((u['path'], u['mtime']) for u in ups))
    c = _CACHE.get(path)
    if not c or c[0] != key:
        _CACHE[path] = (key, DB(path, ups))
    return _CACHE[path][1]
