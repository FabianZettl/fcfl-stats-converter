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


# the German SoFIFA export (column titles in German, ';', one row per player): column -> column of the EA FC export (the values are the same, SoFIFA shows the EA FC values)
_DE_COLS = {'Flanken': 'crossing', 'Abschluss': 'finishing', 'Kopfball-Präzision': 'heading', 'Kurzpässe': 'short_passing', 'Volleys': 'volleys', 'Ballkontrolle': 'ball_control', 'Effet': 'curve',
            'Dribbling': 'dribbling', 'Freistoß-Präzision': 'free_kick_accuracy', 'Lange Pässe': 'long_passing', 'Beschleunigung': 'acceleration', 'Sprintgeschwindigkeit': 'sprint_speed',
            'Beweglichkeit': 'agility', 'Reaktionen': 'reactions', 'Balance': 'balance', 'Schusskraft': 'shot_power', 'Sprungkraft': 'jumping', 'Ausdauer': 'stamina', 'Stärke': 'strength',
            'Fernschüsse': 'long_shots', 'Aggressivität': 'aggression', 'Abfangen': 'interceptions', 'Stellungssp.': 'positioning', 'Übersicht': 'vision', 'Elfmeter': 'penalties',
            'Ruhe': 'composure', 'Defensives Bewusstsein': 'def_awareness', 'Faire Zweikämpfe': 'standing_tackle', 'Grätsche': 'sliding_tackle', 'TH Flugparaden': 'gk_diving',
            'TH Fangsicherheit': 'gk_handling', 'TH Abschlag': 'gk_kicking', 'TH Stellungsspiel': 'gk_positioning', 'TH Reflexe': 'gk_reflexes'}
_DE_POS = {'TW': 'GK', 'IV': 'CB', 'LIV': 'CB', 'RIV': 'CB', 'LV': 'LB', 'RV': 'RB', 'LAV': 'LWB', 'RAV': 'RWB', 'ZDM': 'CDM', 'ZM': 'CM', 'ZOM': 'CAM', 'LM': 'LM', 'RM': 'RM', 'LF': 'LW', 'RF': 'RW',
           'LA': 'LW', 'RA': 'RW', 'ST': 'ST', 'LS': 'ST', 'RS': 'ST', 'MS': 'CF'}   # EA FC 27 table (German -> English abbreviations)
_DE_ACCEL = {'Explosiv': 'Explosive', 'Explosiv (überwie.)': 'Mostly Explosive', 'Explosiv (kontr.)': 'Controlled Explosive', 'Kontrolliert': 'Controlled', 'Anhaltend (kontr.)': 'Controlled Lengthy',
             'Anhaltend (überwie.)': 'Mostly Lengthy', 'Anhaltend': 'Lengthy'}
_DE_WORK = {'Hoch': 'High', 'Mittel': 'Medium', 'Niedrig': 'Low'}
PS_UNKNOWN = {}   # German names in the PlayStyle columns that playstyles_de.json does not know: name -> number of players (so that they can be asked for, never guessed)
_PS = {}


def _ps_map():
    if not _PS:
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'playstyles_de.json'), encoding='utf-8') as f:
                _PS.update(__import__('json').load(f)['map'])
        except (OSError, ValueError, KeyError):
            _PS['_'] = ''
    return _PS


def _playstyles(normal, plus):
    """'Spielstile' and 'Spielstile+' of the German export -> the form of the EA FC export ('Rapid|Quick Step+'); names that are not known go to PS_UNKNOWN and are left out"""
    got = {}
    for col, is_plus in ((normal, False), (plus, True)):
        for t in str(col or '').split(','):
            t = t.strip()
            if not t or t == 'N/A':
                continue
            pl = is_plus or t.endswith('+')
            name = re.sub(r'\s*\+$', '', t)
            en = _ps_map().get(name)
            if en is None:
                PS_UNKNOWN[name] = PS_UNKNOWN.get(name, 0) + 1
                continue
            got[en] = got.get(en, False) or pl
    return '|'.join(k + ('+' if v else '') for k, v in got.items())
_COUNTRIES = {}


def _country(de):
    if not _COUNTRIES:
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'countries_de_en.json'), encoding='utf-8') as f:
                _COUNTRIES.update(__import__('json').load(f))
        except (OSError, ValueError):
            _COUNTRIES['_'] = ''
    return _COUNTRIES.get(de, de)


def _sniff(path):
    """-> (delimiter, field names) of a csv"""
    with open(path, encoding='utf-8-sig', newline='') as f:
        head = f.readline()
    d = ';' if head.count(';') > head.count(',') else ','
    return d, next(csv.reader([head], delimiter=d), [])


def _sniff_kind(path):
    """'ea' (EA FC export), 'de' (German SoFIFA export) or None"""
    _, cols = _sniff(path)
    return 'ea' if 'base_id' in cols and 'rating' in cols else 'de' if 'ID' in cols and 'Gesamtbewertung' in cols else None


def read_update(path):
    """the rows of an update in the form of the EA FC export (dicts of strings), or None when the file is no update: the EA FC export itself (column base_id) or the German SoFIFA export
    (columns ID and Gesamtbewertung; only what can be translated safely is taken over: rating, potential, club, nation, position, height, weight, foot, weak foot, skill moves, the 34
    attribute values; the PlayStyles stay those of the standard database). The date of a SoFIFA export is the one in its file name (sofifa-updates-270007-2026-11-24.csv)."""
    d, cols = _sniff(path)
    with open(path, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f, delimiter=d))
    if 'base_id' in cols and 'rating' in cols:
        return [r for r in rows if r.get('club_name') not in ('ICON', 'Hero') and r.get('rating')]
    if 'ID' not in cols or 'Gesamtbewertung' not in cols:
        return None
    m = re.search(r'(?<!\d)(20\d{2})[-_.]?(\d{2})[-_.]?(\d{2})(?!\d)', os.path.basename(path))
    mt = time.localtime(os.path.getmtime(path))
    snap = '%s-%s-%s' % (m.group(3), m.group(2), m.group(1)) if m else '%02d-%02d-%d' % (mt.tm_mday, mt.tm_mon, mt.tm_year)
    out = []
    for r in rows:
        if not (r.get('ID') or '').strip().isdigit() or not _int(r.get('Gesamtbewertung')):
            continue
        full = (r.get('Vollständiger Name') or r.get('Name') or '').strip()
        parts = full.split()
        pos = [_DE_POS[t] for t in re.findall(r'[A-Z]+', r.get('Positionen') or '') if t in _DE_POS]
        h = re.search(r'(\d+)\s*cm', r.get('Größe') or '')
        w = re.search(r'(\d+)\s*kg', r.get('Gewicht') or '')
        short = (r.get('Name') or '').strip()
        common = '' if re.match(r'^(?:[^\W\d_]\.\s*)+', short) or fold(short) == fold(full) else short   # a name the player is known by (Neymar, Carlos Augusto); 'K. Mbappé' is only an abbreviation
        n = dict(base_id=r['ID'].strip(), stats_id=r['ID'].strip(), first_name=parts[0] if len(parts) > 1 else full, last_name=' '.join(parts[1:]), full_name=full, common_name=common,   # the legal full name: the first word, then the rest (every part of it is indexed as a surname)
                 nation_name=_country((r.get('Nationalität') or '').strip()), club_name=(r.get('Verein') or '').strip(), position=pos[0] if pos else '',
                 position_alt=pos[1] if len(pos) > 1 else '', position_alt_2=pos[2] if len(pos) > 2 else '', position_alt_3=pos[3] if len(pos) > 3 else '',
                 rating=str(_int(r['Gesamtbewertung'])), potential=str(_int(r.get('Potenzial')) or ''), height=h.group(1) if h else '', weight=w.group(1) if w else '',
                 foot={'Rechts': 'Right', 'Links': 'Left'}.get((r.get('foot') or r.get('Starker Fuß') or '').strip(), ''), weak_foot=str(_int(r.get('Schwacher Fuß')) or ''), skill_moves=str(_int(r.get('Spezialbewegungen')) or ''),
                 birthdate='01-01-%s' % r['Geburtsjahr'].strip() if (r.get('Geburtsjahr') or '').strip().isdigit() else '', snapshot=snap)
        for de, en in _DE_COLS.items():
            if _int(r.get(de)) is not None:
                n[en] = str(_int(r[de]))
        ps = _playstyles(r.get('Spielstile'), r.get('Spielstile+'))
        if ps or 'Spielstile' in r:
            n['playstyles'] = ps   # a player of the export without PlayStyles has none (an empty value would not replace the old ones in an update: see DB)
        ct = (r.get('Vertrag') or '').strip()
        lf = re.match(r'\d{2}\.\d{2}\.\d{4}\s+(.+)$', ct)   # a loan: '31.12.2026 River Plate' = until, and the club he belongs to
        n.update(contract=ct if ct != 'N/A' else '', loan_from=lf.group(1) if lf else '', loan_end=(r.get('Leihende') or '').strip().replace('N/A', ''), joined=(r.get('Beigetreten am') or '').strip().replace('N/A', ''),
                 value=(r.get('Wert') or '').strip().replace('N/A', ''), wage=(r.get('Lohn') or '').strip().replace('N/A', ''), release_clause=(r.get('Freigabeklausel') or '').strip().replace('N/A', ''),
                 acceleration_type=_DE_ACCEL.get((r.get('Antritts-Typ') or '').strip(), ''), growth_profile=(r.get('Growth profile') or '').strip().replace('N/A', ''),
                 emotion='' if (r.get('Emotion') or '').strip() in ('N/A', 'PLAYER_EMOTION_0') else (r.get('Emotion') or '').strip(),
                 work_rate_att=_DE_WORK.get((r.get('Offensiv-Arbeitsrate') or '').strip(), ''), work_rate_def=_DE_WORK.get((r.get('Defensiv-Arbeitsrate') or '').strip(), ''),
                 international_reputation=str(_int(r.get('Internationale Reputation')) or ''), shirt_number=str(_int(r.get('Club kit number')) or ''))
        out.append(n)
    return out


def update_files(folder):
    """The SoFIFA updates in a folder (every csv that read_update takes), oldest first: [dict(path, name, date)]. The date of an update is the newest snapshot in it, else a date in the file name
    (fc27-players-2026-11-24.csv), else the day the file was changed."""
    out = []
    for path in sorted(glob.glob(os.path.join(folder or '', '*.csv'))):
        try:
            rows = read_update(path)
        except (OSError, csv.Error, UnicodeDecodeError):
            continue
        if not rows:
            continue
        snap = max((d for d in (_date(r.get('snapshot')) for r in rows) if d), default=None)
        m = re.search(r'(?<!\d)(20\d{2})[-_.]?(\d{2})[-_.]?(\d{2})(?!\d)', os.path.basename(path))
        mt = time.localtime(os.path.getmtime(path))
        fdate = (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (mt.tm_year, mt.tm_mon, mt.tm_mday)
        out.append(dict(path=path, name=os.path.basename(path), date=snap or fdate, mtime=os.path.getmtime(path)))
    return sorted(out, key=lambda u: (u['date'], u['mtime']))


class DB:
    def __init__(self, path, updates=()):
        """path: the standard database; updates: update_files(...) - a player of an update replaces the player of the same base_id when its snapshot (else the date of the file) is not older"""
        self.path = path
        PS_UNKNOWN.clear()   # counted again while this database is read
        self.base_tag = '%s-%d' % (os.path.basename(path), os.path.getsize(path))   # a replaced standard database makes the players that were converted from the old one 'convert again'
        self.rows = []
        self.by_full = {}
        self.by_last = {}
        self.updates = []   # [dict(name, date, rows, used)]
        base = read_update(path) if _sniff_kind(path) == 'de' else _read(path)
        cur = {}   # base_id -> (date, row dict, label)
        for r in base:
            cur[r.get('base_id') or r['stats_id']] = (_date(r.get('snapshot')) or (), r, 'standard')
        for u in updates:
            n = used = 0
            for r in read_update(u['path']) or []:
                n += 1
                k, d = r.get('base_id') or r.get('stats_id'), _date(r.get('snapshot')) or u['date']
                if k not in cur:
                    cur[k] = (d, r, u['name'])
                elif d >= (cur[k][0] or ()):   # the same player: what the update says replaces the values, what it does not say (PlayStyles, ...) stays
                    nr = dict(cur[k][1])
                    nr.update({a: b for a, b in r.items() if b not in ('', None)})
                    cur[k] = (d, nr, u['name'])
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
