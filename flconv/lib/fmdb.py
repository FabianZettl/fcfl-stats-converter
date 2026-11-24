"""The FM list: players exported from FMInside (CSV, ';', one row per player; the columns of the list of the user's scraper), the fallback source behind EA FC / SoFIFA and the
filler for what EA FC does not give (positions, weak foot, foot, height). Lists are read from folders (every *.csv that starts with 'UID;', later files win by UID)."""
import csv
import glob
import os
import re
import time

import fcdb
import sofifa

POS_COLS = (('Pos GK', 0), ('Pos DC', 1), ('Pos DL', 2), ('Pos DR', 3), ('Pos WBL', 2), ('Pos WBR', 3), ('Pos DM', 4), ('Pos MC', 5), ('Pos ML', 6), ('Pos MR', 7), ('Pos AMC', 8),
            ('Pos AML', 9), ('Pos AMR', 10), ('Pos ST', 12))   # FM position -> index of the 13 positions of the game (GK CB LB RB DMF CMF LMF RMF AMF LWF RWF SS CF)
LEVEL = {'natural': 2, 'accomplished': 1}   # checked on 51 players that are in the database: natural is level 2 in 93 %, unavailable is 0 in 97 %; competent is no safe sign
WF_USE = {1: 1, 2: 2, 3: 2, 4: 3, 5: 4}   # FM weak foot 1-5 -> weak foot use / accuracy 1-4 of the game: the average of the game's values for FM 2 / 3 / 4 is 1.9 / 2.2 / 3.0 (use)
WF_ACC = {1: 1, 2: 2, 3: 3, 4: 3, 5: 4}   # and 2.1 / 2.6 / 3.4 (accuracy), 51 players


class FMList:
    def __init__(self, folders):
        self.rows, self.by_name = {}, {}
        for f in folders:
            for path in sorted(glob.glob(os.path.join(f, '*.csv'))):
                try:
                    with open(path, encoding='utf-8-sig', newline='') as fh:
                        if not fh.read(4) == 'UID;':
                            continue
                        fh.seek(0)
                        for r in csv.DictReader(fh, delimiter=';'):
                            if (r.get('UID') or '').strip().isdigit():
                                self.rows[r['UID']] = r
                except OSError:
                    continue
        for r in self.rows.values():
            for n in {fcdb.fold(r.get('Name')), fcdb.fold(r.get('Full name'))}:
                if n:
                    self.by_name.setdefault(n, []).append(r)
        self.by_tok = {}
        for r in self.rows.values():
            for t in {t for n in (fcdb.fold(r.get('Name')), fcdb.fold(r.get('Full name'))) for t in n.split() if len(t) > 2}:
                self.by_tok.setdefault(t, []).append(r)

    def __len__(self):
        return len(self.rows)

    def search(self, q, n=14):
        """free search (all words of q in name / club / nation), rows with all values and the better ones first"""
        ws = fcdb.fold(q).split()
        hits = [r for r in self.rows.values() if ws and all(w in ' '.join(fcdb.fold(r.get(k)) for k in ('Name', 'Full name', 'Club', 'Nationality')) for w in ws)]
        return sorted(hits, key=lambda r: (not complete(r), -(_int(r.get('Ability (0-99)')) or 0)))[:n]

    def find(self, name, club=None, age=None, height=None, nation=None, min_score=0):
        """the player of the list for a player of the database, or None. Candidates have his name; each gets points for what fits (club, age, height) and loses points for what does
        not: club (some word of the club name is the same) +2, unknown or another club 0 (players move); age 0 / 1 / 2 / more years apart +2 / +1 / -1 / -3; height within 2 cm / 5 cm / more
        +2 / 0 / -2; nation (the same country name) +2, another -2, unknown 0. The best one is taken when it has at least `min_score` points and is at least one point ahead of the next."""
        c = list(self.by_name.get(fcdb.fold(name), []))
        if not c:
            return self._fuzzy(name, club, age, height, nation)
        ck = fcdb.club_key(club) if club else frozenset()
        sc = []
        for r in c:
            v = 2 if ck and ck & fcdb.club_key(r.get('Club')) else 0
            a = _int(r.get('Age'))
            if age is not None and a is not None:
                v += {0: 2, 1: 1, 2: -1}.get(abs(a - age), -3)
            h = height_of(r)
            if height and h:
                v += 2 if abs(h - height) <= 2 else 0 if abs(h - height) <= 5 else -2
            if nation and (r.get('Nationality') or '').strip():
                v += 2 if fcdb.fold(nation) == fcdb.fold(r['Nationality']) else -2
            sc.append((v, r))
        sc.sort(key=lambda x: -x[0])
        if sc[0][0] < min_score or (len(sc) > 1 and sc[0][0] - sc[1][0] < 1):
            return None
        return sc[0][1]


    def _fuzzy(self, name, club, age, height, nation):
        """no player has exactly this name (Neymar Jr / Neymar, Juan Cuadrado / Juan Guillermo Cuadrado, a Brazilian with one name): a player that shares a word of the name AND has the same club,
        an age within 1 year, the height within 3 cm and the same nation (where those are known). Only when exactly one fits."""
        toks = [t for t in fcdb.fold(name).split() if len(t) > 2]
        ck = fcdb.club_key(club) if club else frozenset()
        if not toks or not ck or age is None:
            return None
        cand = {}
        for t in toks:
            for r in self.by_tok.get(t, []):
                cand[r['UID']] = r
        ok = []
        last = toks[-1]
        for r in cand.values():
            rt = {t for n in (fcdb.fold(r.get('Name')), fcdb.fold(r.get('Full name'))) for t in n.split()}
            one = len(fcdb.fold(r.get('Name')).split()) == 1 and fcdb.fold(r.get('Name')) == toks[0]   # a player with one name (Fábio, Neymar)
            if last not in rt and not one:   # a shared first name alone is no evidence
                continue
            a, h = _int(r.get('Age')), height_of(r)
            if a is None or abs(a - age) > 1 or not (ck & fcdb.club_key(r.get('Club'))):
                continue
            if height and h and abs(h - height) > 3:
                continue
            if nation and (r.get('Nationality') or '').strip() and fcdb.fold(nation) != fcdb.fold(r['Nationality']):
                continue
            ok.append(r)
        return ok[0] if len(ok) == 1 else None


def _int(v):
    m = re.search(r'\d+', str(v or ''))
    return int(m.group()) if m else None


def raw(r):
    """the row as sofifa.parse_fm gives a pasted page: {FM label: 0-99 as on the page (1-20 times 5), overall, potential}"""
    out = {lab: min(99, int(r[lab]) * 5) for lab in sofifa.FM_LABELS.values() if (r.get(lab) or '').strip().isdigit()}
    for key, col in (('overall', 'Ability (0-99)'), ('potential', 'Potential (0-99)')):
        if _int(r.get(col)) is not None:
            out[key] = _int(r[col])
    return out


def page_text(r):
    """text that looks like a FMInside player page for everything that reads one (is_fm, info, parse_fm): the FM list as a source of the existing FM conversion"""
    ls = ['FMInside Football Manager community since 2004', '', '%s is a %s-year-old %s for %s in Football Manager' % (r.get('Name'), _int(r.get('Age')) or 25, (r.get('Positions') or 'CM').upper(), r.get('Club') or ''),
          'Current ability %s/100' % raw(r).get('overall', 70), 'Potential %s/100' % raw(r).get('potential', raw(r).get('overall', 70))]
    ls += ['%s %d' % (k, v) for k, v in raw(r).items() if k not in ('overall', 'potential')]
    return '\n' + '\n'.join(ls) + '\n'


def complete(r):
    """the row has every attribute the FM conversion needs (a list that only has names, club, ability and age is no source of values; keepers need the keeper attributes)"""
    return not sofifa.missing_fm(raw(r), (r.get('Positions') or '').strip().startswith('GK'))


LINE_FM = {'GK': 0, 'DC': 1, 'DL': 1, 'DR': 1, 'WBL': 1.5, 'WBR': 1.5, 'DM': 1.5, 'MC': 2, 'ML': 2, 'MR': 2, 'AMC': 2.5, 'AML': 2.7, 'AMR': 2.7, 'ST': 3}   # lines of the pitch, back to front
LINE_PES = (0, 1, 1, 1, 1.5, 2, 2, 2, 2.5, 2.7, 2.7, 3, 3)   # the same for the 13 positions of the game


def plausible(r, main):
    """the FM row can be the player of the database whose main position is `main` (index 0..12): a keeper is a keeper, otherwise one of his FM positions is within one line of it.
    Catches a wrong match by name (the Brazilian Ronaldo of the database and a keeper called Ronaldo)"""
    ls = [LINE_FM[t] for t in re.findall(r'[A-Z]+', r.get('Positions') or '') if t in LINE_FM]
    if not ls or not 0 <= main < 13:
        return True
    if main == 0 or 0 in ls:
        return main == 0 and 0 in ls
    return any(abs(x - LINE_PES[main]) <= 1.0 for x in ls)


def has_positions(r):
    """the row has the position ratings (a detail row, not only a line of a list)"""
    return any((r.get(col) or '').strip() for col, _ in POS_COLS)


def detail(r):
    """a detail row: it has position ratings or the weak foot (what the FM list adds to an EA FC player)"""
    return has_positions(r) or bool(_int(r.get('Weak foot')))


BAND = {'natural': (2, 2), 'accomplished': (1, 2), 'competent': (0, 1)}   # the levels of the game that a FM rating allows; checked on 6,600 players of the game (original levels): natural is 2 in 85 %,
# accomplished 0 / 1 / 2 in 15 / 41 / 44 %, competent 50 / 35 / 16 %, unavailable is 0 in 94 %: the two middle ratings straddle the border, so the level the player has is kept inside the band


def positions(r, cur=None):
    """13 levels 0/1/2 from the position ratings. Without `cur`: natural 2, accomplished 1, the rest 0. With the levels the player has: natural 2; accomplished keeps what he has between 1 and 2;
    competent keeps what he has up to 1 (never adds); everything else 0 (FM says he cannot play there)"""
    out = [0] * 13
    for col, k in POS_COLS:
        lab = (r.get(col) or '').strip().lower()
        lo, hi = BAND.get(lab, (0, 0))
        v = lo if cur is None else min(hi, max(lo, cur[k])) if lab != 'competent' else min(hi, cur[k])
        out[k] = max(out[k], v)
    return out


def weak_foot(r):
    """(use, accuracy) of the game, or None"""
    v = _int(r.get('Weak foot'))
    return (WF_USE[max(1, min(5, v))], WF_ACC[max(1, min(5, v))]) if v else None


def foot(r):
    f = (r.get('Footedness') or '').strip().capitalize()
    return f if f in ('Left', 'Right') else None


def birth(r):
    """date of birth as EA FC writes it (DD-MM-YYYY), or ''"""
    try:
        return time.strftime('%d-%m-%Y', time.strptime((r.get('Date of birth') or '').strip(), '%d %B %Y'))
    except ValueError:
        return ''


def height_of(r):
    h = _int(r.get('Height'))
    return h if h and 100 <= h <= 250 else None


def height(r):
    h = _int(r.get('Height'))
    return h if h and 140 <= h <= 230 else None
