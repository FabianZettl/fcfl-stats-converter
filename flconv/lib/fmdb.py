"""The FM list: players exported from FMInside (CSV, ';', one row per player; the columns of the list of the user's scraper), the fallback source behind EA FC / SoFIFA and the
filler for what EA FC does not give (positions, weak foot, foot, height). Lists are read from folders (every *.csv that starts with 'UID;', later files win by UID)."""
import csv
import glob
import os
import re

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

    def __len__(self):
        return len(self.rows)

    def find(self, name, club=None, age=None):
        """the one player of the list for a player of the database (name; several with the name: the club, then the age), or None. The age may differ by 3 years at most."""
        c = list(self.by_name.get(fcdb.fold(name), []))
        if len(c) > 1 and club:
            ck = fcdb.club_key(club)
            c = [r for r in c if fcdb.club_key(r.get('Club')) == ck] or c
        if len(c) > 1 and age is not None:
            c = [r for r in c if _int(r.get('Age')) is not None and abs(_int(r['Age']) - age) <= 1] or c
        if len(c) != 1:
            return None
        a = _int(c[0].get('Age'))
        return c[0] if age is None or a is None or abs(a - age) <= 3 else None


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


def positions(r):
    """13 levels 0/1/2 from the position ratings (natural 2, accomplished 1)"""
    out = [0] * 13
    for col, k in POS_COLS:
        out[k] = max(out[k], LEVEL.get((r.get(col) or '').strip().lower(), 0))
    return out


def weak_foot(r):
    """(use, accuracy) of the game, or None"""
    v = _int(r.get('Weak foot'))
    return (WF_USE[max(1, min(5, v))], WF_ACC[max(1, min(5, v))]) if v else None


def foot(r):
    f = (r.get('Footedness') or '').strip().capitalize()
    return f if f in ('Left', 'Right') else None


def height(r):
    h = _int(r.get('Height'))
    return h if h and 140 <= h <= 230 else None
