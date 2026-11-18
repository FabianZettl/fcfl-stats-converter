"""Conversion of SoFIFA (FIFA / FC) player stats to the 25 attributes of PES 21 / eFootball (the attributes Football Life uses).

The conversion formulas are a Python port of the ones in the browser extension "PES Stats Converter" by moth1995
(https://github.com/moth1995/pes_stats_converter_copy_addon, GPL-3.0, converters/pes21.js, method fromFIFA17To23Player) and are therefore GPL-3.0 as well.
Reading the text of a SoFIFA page (Ctrl+A, Ctrl+C on the page, paste into the tool) replaces the scraper of the extension."""
import math
import re

# label on the page (lower case, only letters) -> key
LABELS = {
    'crossing': 'crossing', 'finishing': 'finishing', 'headingaccuracy': 'heading', 'shortpassing': 'short', 'volleys': 'volleys',
    'ballcontrol': 'ballcontrol', 'curve': 'curve', 'dribbling': 'dribbling', 'fkaccuracy': 'fk', 'freekickaccuracy': 'fk', 'longpassing': 'long',
    'acceleration': 'acceleration', 'agility': 'agility', 'balance': 'balance', 'reactions': 'reactions', 'sprintspeed': 'sprint',
    'jumping': 'jumping', 'longshots': 'longshots', 'shotpower': 'shotpower', 'stamina': 'stamina', 'strength': 'strength',
    'aggression': 'aggression', 'attackposition': 'attpos', 'attposition': 'attpos', 'positioning': 'attpos', 'composure': 'composure',
    'interceptions': 'interceptions', 'penalties': 'penalties', 'vision': 'vision', 'defensiveawareness': 'defaw', 'marking': 'marking',
    'slidingtackle': 'sliding', 'standingtackle': 'standing',
    'gkdiving': 'gkdiving', 'gkhandling': 'gkhandling', 'gkkicking': 'gkkicking', 'gkpositioning': 'gkpositioning', 'gkreflexes': 'gkreflexes',
}


def _norm(s):
    return re.sub(r'[^a-z]', '', s.lower())


def parse_page(text):
    """Text of a SoFIFA player page (copied from the browser) -> {key: value}. Reads '65 Crossing', 'Crossing 65' and a number on the line next to its label."""
    lines = [l.strip() for l in str(text or '').splitlines()]
    out = {}
    for i, l in enumerate(lines):
        if not l:
            continue
        m = re.match(r'^(\d{1,3})\s+(.+)$', l)
        k = v = None
        if m and LABELS.get(_norm(m.group(2))):
            k, v = LABELS[_norm(m.group(2))], int(m.group(1))
        else:
            m = re.match(r'^(.+?)\s+(\d{1,3})$', l)
            if m and LABELS.get(_norm(m.group(1))):
                k, v = LABELS[_norm(m.group(1))], int(m.group(2))
            elif LABELS.get(_norm(l)) and re.fullmatch(r'[A-Za-z .]+', l):
                for j in (i - 1, i + 1):
                    if 0 <= j < len(lines) and re.fullmatch(r'\d{1,3}', lines[j]):
                        k, v = LABELS[_norm(l)], int(lines[j])
                        break
        if k and 0 <= v <= 99 and k not in out:
            out[k] = v
    for i, l in enumerate(lines):   # the headline numbers: "72" above "Overall rating", "79" above "Potential"
        key = {'overall rating': 'overall', 'potential': 'potential'}.get(l.lower())
        if key and key not in out:
            prev = next((lines[j] for j in range(i - 1, max(-1, i - 3), -1) if lines[j]), '')
            if re.fullmatch(r'\d{2}', prev):
                out[key] = int(prev)
    return out


def _rnd(x):
    return int(math.floor(x + 0.5))   # JavaScript Math.round


def pes(f):
    """FIFA 0-99 stat onto the PES scale (identity from 80 up, two FIFA points per PES point below)."""
    f = _rnd(f)
    v = f if f >= 80 else 79 - (79 - f) // 2
    return max(40, min(99, v))


def _cl(x):
    return max(40, min(99, x))


def _avg(*a):
    return sum(a) / float(len(a))


def convert(s, gk=False):
    """s: parsed SoFIFA stats -> {attribute name of the game: value}."""
    g = lambda k, d=None: s.get(k, d)
    r = {}
    oa = pes(g('attpos'))
    r['OffensiveAwareness'] = oa + (1 if g('attpos') < g('reactions') else -1 if g('attpos') > g('reactions') else 0)
    r['BallControl'] = pes(g('ballcontrol'))
    r['Dribbling'] = pes(g('dribbling'))
    r['TightPossession'] = pes(_avg(g('ballcontrol'), g('composure')))
    adj = 1 if g('short') < g('vision') else -1 if g('short') > g('vision') else 0
    r['LowPass'] = pes(g('short')) + adj
    r['LoftedPass'] = pes(max(g('long'), g('crossing'))) + adj
    fin = pes(g('finishing')) + (1 if g('finishing') < g('volleys') else -1 if g('finishing') > g('volleys') else 0)
    ls = pes(g('longshots'))
    fin += 1 if fin < ls else -1 if fin > ls else 0
    r['Finishing'] = fin
    r['Heading'] = pes(g('heading'))
    pk = pes(g('penalties') * 0.3 + g('fk') * 0.7)
    r['PlaceKicking'] = pk if pk >= 60 else pes(g('penalties'))
    r['Curl'] = pes(g('curve'))
    r['Speed'] = pes(g('sprint'))
    r['Acceleration'] = pes(g('acceleration'))
    r['KickingPower'] = pes(_avg(g('shotpower'), g('strength')) if g('shotpower') < 70 else g('shotpower'))
    r['Jump'] = pes(g('jumping'))
    r['PhysicalContact'] = pes(g('strength'))
    bal = pes(_avg(g('agility'), g('balance')))
    r['Balance'] = bal + (1 if bal > g('reactions') else -1 if bal < g('reactions') else 0)
    r['Stamina'] = pes(max(g('stamina'), 60))
    da = g('defaw') if 'defaw' in s else g('marking')
    r['DefensiveAwareness'] = pes(da) + (1 if da < g('interceptions') else -1 if da > g('interceptions') else 0)
    r['BallWinning'] = pes(max(g('standing'), g('sliding')))
    r['Aggression'] = pes(g('aggression'))
    for k in ('GKAwareness', 'GKCatching', 'GKClearing', 'GKReflexes', 'GKReach'):
        r[k] = 40
    if gk:
        for k, d in (('OffensiveAwareness', 15), ('BallControl', 10), ('Dribbling', 15), ('LowPass', 5), ('LoftedPass', 5), ('Finishing', 10), ('Heading', 20), ('Curl', 10),
                     ('Jump', 10), ('PhysicalContact', 15), ('Stamina', 20), ('DefensiveAwareness', 5), ('BallWinning', 5)):
            r[k] = _cl(r[k] + d)
        r['KickingPower'] = pes(g('gkkicking'))
        r['GKAwareness'] = pes(_avg(g('gkdiving'), g('gkhandling'), g('gkpositioning'), g('gkreflexes')) + 5)
        r['GKCatching'] = pes(g('gkhandling') + 5)
        r['GKClearing'] = pes(_avg(g('gkdiving'), g('gkhandling')) + 5)
        r['GKReflexes'] = pes(g('gkreflexes') + 5)
        r['GKReach'] = pes(g('gkpositioning') + 5)
    return {k: _cl(v) for k, v in r.items()}


NEEDED = ['crossing', 'finishing', 'heading', 'short', 'volleys', 'ballcontrol', 'curve', 'dribbling', 'fk', 'long', 'acceleration', 'agility', 'balance', 'reactions', 'sprint', 'jumping',
          'longshots', 'shotpower', 'stamina', 'strength', 'aggression', 'attpos', 'composure', 'interceptions', 'penalties', 'vision', 'standing', 'sliding']


def missing(s, gk=False):
    need = NEEDED + (['gkdiving', 'gkhandling', 'gkkicking', 'gkpositioning', 'gkreflexes'] if gk else []) + ([] if ('defaw' in s or 'marking' in s) else ['defaw'])
    return [k for k in need if k not in s]


# ---------------------------------------------------------------- FMInside (Football Manager 27): port of fromFMPlayer / fmStatToPes21 of the extension (fmdata.py)
import fmdata as _fmd
_FM = _fmd.DATA
FM_LABELS = {_norm(v): v for v in _FM['labels'].values()}
_POSN = ['GK', 'CB', 'LB', 'RB', 'DMF', 'CMF', 'LMF', 'RMF', 'AMF', 'LWF', 'RWF', 'SS', 'CF']
_ATTR = {'offensiveAwareness': 'OffensiveAwareness', 'ballControl': 'BallControl', 'dribbling': 'Dribbling', 'tightPossession': 'TightPossession', 'lowPass': 'LowPass',
         'loftedPass': 'LoftedPass', 'finishing': 'Finishing', 'heading': 'Heading', 'placeKicking': 'PlaceKicking', 'curl': 'Curl', 'speed': 'Speed', 'acceleration': 'Acceleration',
         'kickingPower': 'KickingPower', 'jump': 'Jump', 'physicalContact': 'PhysicalContact', 'balance': 'Balance', 'stamina': 'Stamina', 'defensiveAwareness': 'DefensiveAwareness',
         'ballWinning': 'BallWinning', 'aggression': 'Aggression', 'gkAwareness': 'GKAwareness', 'gkCatching': 'GKCatching', 'gkClearing': 'GKClearing', 'gkReflexes': 'GKReflexes',
         'gkReach': 'GKReach'}


def is_fm(text):
    t = str(text or '')
    return bool(re.search(r'Current ability', t) and re.search(r'Potential', t) and re.search(r'\bFirst Touch\b', t))


def parse_fm(text):
    """Text of a FMInside player page (Ctrl+A, Ctrl+C) -> {FM label: value 0-99 as on the page, overall, potential}."""
    out = {}
    t = str(text or '')
    for key, lab in (('overall', 'Current ability'), ('potential', 'Potential')):
        m = re.search(lab + r'\s*\n?\s*(\d{1,3})\s*/\s*100', t)
        if m:
            out[key] = int(m.group(1))
    rng = {}
    t = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060\ufeff]', '', t)   # invisible marks that a web page puts around a number
    ls = [x.strip() for x in t.splitlines() if x.strip()]
    lines, i = [], 0
    while i < len(ls):   # the label and its value on separate lines (innerText of the page: 'Dribbling', '(preferred)', '70'): put them together
        k = i + 1 + (1 if i + 1 < len(ls) and re.fullmatch(r'\((?:key|preferred)\)', ls[i + 1]) else 0)
        nx = ls[k] if k < len(ls) else ''
        if re.fullmatch(r'\d{1,2}(\s*[\u2013-]\s*\d{1,2})?', nx) and not re.search(r'\s\d{1,2}$', ls[i]) and _norm(re.sub(r'\((?:key|preferred)\)', '', ls[i])) in FM_LABELS:
            lines.append(ls[i] + '\t' + nx)
            i = k + 1
        else:
            lines.append(ls[i])
            i += 1
    for ln in lines:
        m = re.match(r'^(.+?)\s+(\d{1,2})$', ln)
        r = re.match(r'^(.+?)\s+(\d{1,2})\s*[\u2013-]\s*(\d{1,2})$', ln)   # '5-25': FMInside shows a range for values the game generates when a save starts
        if r:
            k = FM_LABELS.get(_norm(re.sub(r'\((?:key|preferred)\)', '', r.group(1))))
            if k:
                rng[k] = (int(r.group(2)), int(r.group(3)))
            continue
        if not m:
            continue
        k = FM_LABELS.get(_norm(re.sub(r'\((?:key|preferred)\)', '', m.group(1))))
        if k and k not in out:
            out[k] = int(m.group(2))
    # hidden (Determination, Flair for visitors who are not logged in) or a range: a value that fits the rest of the player, inside the range if there is one
    rel = {'Determination': ('Work Rate', 'Teamwork', 'Bravery'), 'Flair': ('Technique', 'Dribbling', 'Off the Ball')}
    vals = [v for k, v in out.items() if k not in ('overall', 'potential')]
    est = []
    for k in set(rng) | set(rel):
        if k in out or (k not in rng and not all(s in out for s in rel.get(k, ('?',)))):
            continue
        src = [out[s] for s in rel.get(k, ()) if s in out]
        v = sum(src) / float(len(src)) if len(src) == len(rel.get(k, ())) and src else (sum(vals) / float(len(vals)) if vals else 50)
        lo, hi = rng.get(k, (0, 99))
        out[k] = int(round(min(hi, max(lo, v))))
        est.append(k)
    if est:
        out['_est'] = est
    return out


def _fm_branch(gk):
    return _FM['gk'] if gk else _FM['field']


def missing_fm(s, gk=False):
    need = {_FM['labels'][n] for parts in _fm_branch(gk).values() for n in parts}
    return sorted(k for k in need if k not in s)


def _ca_points(ca):
    c = ca * 2
    for lim, v in ((90, -10), (100, -9), (110, -8), (120, -7), (130, -6), (140, -5), (150, -4), (160, -3), (170, -2), (180, -1)):
        if c <= lim:
            return v
    return 1


def convert_fm(s, gk=False, pos=5, ca=None):
    """s: parse_fm result; pos: position code of the game (0 GK ... 12 CF); ca: ability of the page (0-99), None = 70."""
    ca = 70 if ca is None else ca
    row = _POSN[pos] if 0 <= pos < 13 else 'CMF'
    mx, mn = _FM['max'][row], _FM['min'][row]
    fm = {k: v / 5.0 for k, v in s.items() if k not in ('overall', 'potential', '_est')}   # the page shows 1-20 scaled to 0-99
    out = {}
    for a, parts in _fm_branch(gk).items():
        avg = sum(fm[_FM['labels'][n]] for n in parts) / float(len(parts))
        out[_ATTR[a]] = _cl(_rnd(((mx[a] - mn[a]) / 20.0) * avg + mn[a] + _ca_points(ca)))
    if not gk:
        for k in ('GKAwareness', 'GKCatching', 'GKClearing', 'GKReflexes', 'GKReach'):
            out[k] = 40
    return out


# ---------------------------------------------------------------- explanation: which values a converted attribute is made of
_L = {'attpos': 'Att. position', 'reactions': 'Reactions', 'ballcontrol': 'Ball control', 'dribbling': 'Dribbling', 'composure': 'Composure', 'short': 'Short passing', 'vision': 'Vision',
      'long': 'Long passing', 'crossing': 'Crossing', 'finishing': 'Finishing', 'volleys': 'Volleys', 'longshots': 'Long shots', 'heading': 'Heading accuracy', 'penalties': 'Penalties',
      'fk': 'FK accuracy', 'curve': 'Curve', 'sprint': 'Sprint speed', 'acceleration': 'Acceleration', 'shotpower': 'Shot power', 'strength': 'Strength', 'jumping': 'Jumping',
      'agility': 'Agility', 'balance': 'Balance', 'stamina': 'Stamina', 'defaw': 'Defensive awareness', 'marking': 'Marking', 'interceptions': 'Interceptions', 'standing': 'Standing tackle',
      'sliding': 'Sliding tackle', 'aggression': 'Aggression'}


def explain(s):
    """{attribute: dict(src [(label, value)], rule, base)}: the inputs of the conversion, how they are combined and the value on the PES scale before the +/-1 rules."""
    g = lambda k, d=None: s.get(k, d)
    def e(keys, rule, comp):
        return dict(src=[[_L[k], g(k)] for k in keys if g(k) is not None], rule=rule, base=pes(comp))
    da = 'defaw' if 'defaw' in s else 'marking'
    pk = g('penalties', 0) * .3 + g('fk', 0) * .7
    return {
        'OffensiveAwareness': e(['attpos', 'reactions'], 'Att. position; +1 if Reactions are higher, -1 if lower', g('attpos', 0)),
        'BallControl': e(['ballcontrol'], 'Ball control', g('ballcontrol', 0)),
        'Dribbling': e(['dribbling'], 'Dribbling', g('dribbling', 0)),
        'TightPossession': e(['ballcontrol', 'composure'], 'average of Ball control and Composure', _avg(g('ballcontrol', 0), g('composure', 0))),
        'LowPass': e(['short', 'vision'], 'Short passing; +1 if Vision is higher, -1 if lower', g('short', 0)),
        'LoftedPass': e(['long', 'crossing', 'short', 'vision'], 'the better of Long passing and Crossing; +1/-1 like Low pass (Short passing against Vision)', max(g('long', 0), g('crossing', 0))),
        'Finishing': e(['finishing', 'volleys', 'longshots'], 'Finishing; +1/-1 against Volleys, then +1/-1 against Long shots', g('finishing', 0)),
        'Heading': e(['heading'], 'Heading accuracy', g('heading', 0)),
        'PlaceKicking': e(['penalties', 'fk'], '30% Penalties + 70% FK accuracy (below 60: Penalties only)', pk if pk >= 60 else g('penalties', 0)),
        'Curl': e(['curve'], 'Curve', g('curve', 0)),
        'Speed': e(['sprint'], 'Sprint speed', g('sprint', 0)),
        'Acceleration': e(['acceleration'], 'Acceleration', g('acceleration', 0)),
        'KickingPower': e(['shotpower', 'strength'], 'Shot power (below 70: average with Strength)', _avg(g('shotpower', 0), g('strength', 0)) if g('shotpower', 0) < 70 else g('shotpower', 0)),
        'Jump': e(['jumping'], 'Jumping', g('jumping', 0)),
        'PhysicalContact': e(['strength'], 'Strength', g('strength', 0)),
        'Balance': e(['agility', 'balance', 'reactions'], 'average of Agility and Balance; +1/-1 against Reactions', _avg(g('agility', 0), g('balance', 0))),
        'Stamina': e(['stamina'], 'Stamina (at least 60)', max(g('stamina', 0), 60)),
        'DefensiveAwareness': e([da, 'interceptions'], 'Defensive awareness; +1/-1 against Interceptions', g(da, 0)),
        'BallWinning': e(['standing', 'sliding'], 'the better of Standing and Sliding tackle', max(g('standing', 0), g('sliding', 0))),
        'Aggression': e(['aggression'], 'Aggression', g('aggression', 0)),
    }


def explain_gk(s):
    """Keepers: all attributes come from one model of the game (gkcal), the inputs are the keeper values, Reactions, speed and height."""
    src = [[l, s.get(k)] for l, k in (('GK Diving', 'gkdiving'), ('GK Handling', 'gkhandling'), ('GK Kicking', 'gkkicking'), ('GK Positioning', 'gkpositioning'), ('GK Reflexes', 'gkreflexes'), ('Reactions', 'reactions')) if s.get(k) is not None]
    import gkcal
    return {a: dict(src=src, rule='model of the game fitted on %d keepers (EA FC keeper values, Reactions, speed, height)' % 619, base=None, model=True) for a in gkcal.COEF}
