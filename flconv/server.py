#!/usr/bin/env python3
"""FCFL - Stats Converter: converts EA FC (or FMInside / SoFIFA page) stats into the player database of Football Life (Player.bin), for one player, a club, a league or the whole
database, always with a backup and a check.   python3 server.py [--port 8790] [--data-dir DIR]"""
import argparse
import glob
import hashlib
import json
import os
import shutil
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'lib'))
import convert  # noqa: E402
import playstyle  # noqa: E402
import collections  # noqa: E402
import timeshift  # noqa: E402
import dbmeta  # noqa: E402
import fcdb  # noqa: E402
import fmcal  # noqa: E402
import plbin  # noqa: E402

def default_data_dir():
    if os.environ.get('FLCONV_DATA'):
        return os.environ['FLCONV_DATA']
    if os.name == 'nt':
        return os.path.join(os.environ.get('APPDATA') or os.path.expanduser('~'), 'FL-Stats-Converter')
    return os.path.join(os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share'), 'fl-stats-converter')


DATA = default_data_dir()   # settings, backups, the copy of the original Player.bin, journal, your assignments
DEF = dict(
    pesdb='',
    plan='',
    csv=os.path.join(HERE, 'data', 'fc27-players.csv'),
    fmcal=os.path.join(DATA, 'fm_calib.json'),
    backups=os.path.join(DATA, 'backups'),
    journal=os.path.join(DATA, 'converted.json'),
)
CFG = dict(DEF)
LOCK = threading.Lock()
SET_FILE = os.path.join(DATA, 'settings.json')
SET = dict(mode='db', dbpath='', date='', bridge='', modules='')   # mode: 'db' = the database file, 'ml' = a running Master League through Gaffer
CFG['gaffer'] = 'http://127.0.0.1:8767'


def resolve_pesdb(p):
    """folder chosen by the user (.../common, .../_FL26MyWorld, .../etc/pesdb) -> the folder that holds Player.bin"""
    p = os.path.expanduser(str(p or '').strip().strip('"'))
    if os.path.basename(p).lower() == 'player.bin':
        p = os.path.dirname(p)
    for c in (p, os.path.join(p, 'etc', 'pesdb'), os.path.join(p, 'common', 'etc', 'pesdb'), os.path.join(p, 'pesdb')):
        if c and os.path.isfile(os.path.join(c, 'Player.bin')):
            return c
    return None


def settings_load():
    try:
        SET.update(json.load(open(SET_FILE)))
    except Exception:
        pass
    r = resolve_pesdb(SET.get('dbpath'))
    if r:
        CFG['pesdb'] = r
    CFG['journal'] = journal_path()


def db_key():
    return hashlib.md5(CFG['pesdb'].encode()).hexdigest()[:8]


def journal_path():
    if SET.get('mode') == 'ml':
        return os.path.join(DATA, 'converted-ml.json')
    return os.path.join(DATA, 'converted-%s.json' % db_key())


LIVE = dict(mt=None, d={})

GDATE = dict(key=None, v=None, fail=0)

LSQ = dict(t=0, d=None)

GL = dict(key=None, v=None, fail=0, t=0, p=[], pot={})

PEND = {}


def live_attrs():
    """values in the running game: the dump of the Gaffer bridge (players_dump.bin, 380 byte blocks)"""
    p = os.path.join(bridge_dir(), 'players_dump.bin')
    try:
        mt = os.path.getmtime(p)
    except OSError:
        return {}
    if LIVE['mt'] != mt:
        d, ix = {}, {}
        raw = open(p, 'rb').read()
        for k in range(len(raw) // 380):
            b = raw[k * 380:(k + 1) * 380]
            pid = int.from_bytes(b[0x30:0x34], 'little')
            ix[pid] = k
            d[pid] = {a: (int.from_bytes(b[off:off + 4], 'little') >> sh) & 127 for a, (off, sh) in dbmeta._F7.items()}
        LIVE['mt'], LIVE['d'], LIVE['ix'], LIVE['raw'] = mt, d, ix, raw
        GL['key'] = GDATE['key'] = None   # a new dump of the game: club, potential and date are read again (in the background)
        LSQ['t'] = 0
        MATCH.clear()
    return LIVE['d']


IG_SKILL = {'Scissors Feint': 291, 'Flip Flap': 292, 'Marseille Turn': 293, 'Sombrero': 294, 'Cut Behind & Turn': 295, 'Scotch Move': 296, 'Heading': 297, 'Long Range Drive': 298,
            'Acrobatic Finishing': 300, 'Heel Trick': 301, 'First-time Shot': 302, 'One-touch Pass': 303, 'Weighted Pass': 304, 'Pinpoint Crossing': 305, 'Outside Curler': 306,
            'Low Lofted Pass': 308, 'GK Low Punt': 309, 'Long Throw': 310, 'GK Long Throw': 311, 'Gamesmanship': 312, 'Man Marking': 313, 'Track Back': 314, 'Acrobatic Clear': 315,
            'Captaincy': 316, 'Fighting Spirit': 318, 'Penalty Specialist': 320, 'Chip Shot Control': 322, 'Step On Ball Control': 323, 'Dipping Shot': 324, 'Rising Shots': 325,
            'Interception': 327, 'Double Touch': 328, 'Cross Over Turn': 329, 'Long Range Shooting': 330, 'Through Passing': 331}   # name -> bit in the 380 byte block of the running game
IG_COM = {'Trickster': 223, 'Mazing Run': 255, 'Speeding Bullet': 286, 'Incisive Run': 287, 'Long Ball Expert': 288, 'Early Cross': 289, 'Long Ranger': 290}
IG_POS = (274, 268, 270, 272, 260, 262, 264, 266, 258, 253, 256, 251, 249)   # GK CB LB RB DMF CMF LMF RMF AMF LWF RWF SS CF: 2 bit 0..2
assert set(IG_SKILL) == set(plbin.SKILL_BITS) and set(IG_COM) == set(plbin.COM_BITS)


def ml_fields(pr):
    """profile of the converter (skills, COM styles, playing style, positions) -> {field of the GrowthBridge module: value}"""
    f = {}
    if 'skills' in pr:
        f.update({'B%d' % k: int(n in pr['skills']) for n, k in IG_SKILL.items()})
    if 'com_styles' in pr:
        f.update({'B%d' % k: int(n in pr['com_styles']) for n, k in IG_COM.items()})
    if pr.get('playing_style') in plbin.STYLES:
        f['Style'] = plbin.STYLES.index(pr['playing_style'])
    if 'positions' in pr:
        f.update({'P%d' % l: max(0, min(2, int(v))) for l, v in zip(IG_POS, pr['positions'])})
    if 'height' in pr:
        f['Height'] = int(pr['height'])
    if 'weight' in pr:
        f['Weight'] = int(pr['weight'])
    if 'foot' in pr:
        f['Foot'] = int(pr['foot'] == 'Left')
    return f


def live_x(pid):
    """the same fields as in the running game (dump): {field: value}"""
    live_attrs()
    k = LIVE.get('ix', {}).get(pid)
    if k is None:
        return {}
    b = LIVE['raw'][k * 380:(k + 1) * 380]
    v = int.from_bytes(b, 'little')
    f = {'B%d' % x: (v >> x) & 1 for x in list(IG_SKILL.values()) + list(IG_COM.values())}
    f.update({'P%d' % l: (v >> l) & 3 for l in IG_POS})
    f['Style'] = (b[0x1D] >> 3) & 31
    f.update(Height=b[0], Weight=b[1], Foot=b[23] >> 7)
    return f


def cur_attrs(pid):
    if SET['mode'] == 'ml':
        a = live_attrs().get(pid)
        pe = PEND.get(pid)
        if pe and pe[0] > (LIVE['mt'] or 0):
            a = dict(a or M.pb.attrs(M.pb.index[pid]), **pe[1])
        if a:
            return a
    return M.pb.attrs(M.pb.index[pid])


GSL = dict(t=0, v=None)   # slot and modification time of the save in Gaffer
GBUSY = set()


def gaffer_slot():
    """(slot, mtime) of the newest save in Gaffer; asked at most every 5 s (cheap)"""
    if time.time() - GSL['t'] > 5:
        try:
            sl = json.load(urllib.request.urlopen(CFG['gaffer'] + '/api/slots', timeout=3))
            GSL['v'] = (sl[0]['slot'], sl[0].get('mtime')) if sl else None
        except Exception:
            GSL['v'] = None
        GSL['t'] = time.time()
    return GSL['v']


def _cached(cache, key, fetch, first_wait=True, min_age=0):
    """what Gaffer gave for this state of the save (key); a new state is fetched in the background while the old value is still used, only the very first fetch waits.
    A failed fetch is not tried again for 30 s. This keeps the page fast when Gaffer is busy (its /api/state takes seconds and /api/players is 10 MB)."""
    name = id(cache)
    if cache.get('v') is not None and (cache.get('key') == key or time.time() - cache.get('ok', 0) < min_age):   # min_age: a heavy call of Gaffer is not repeated before that many seconds
        return cache['v']
    if time.time() - cache.get('fail', 0) < max(30, min(min_age, 120)):   # Gaffer goes on with a call that timed out: do not pile up new ones
        return cache.get('v')
    def run():
        try:
            v = fetch()
            cache.update(key=key, v=v, fail=0, ok=time.time())
        except Exception:
            cache['fail'] = time.time()
        finally:
            GBUSY.discard(name)
    if cache.get('v') is None:   # nothing yet: the first fetch is waited for
        if name in GBUSY:
            return None
        GBUSY.add(name)
        run()
        return cache.get('v')
    if name not in GBUSY:
        GBUSY.add(name)
        threading.Thread(target=run, daemon=True).start()
    return cache['v']


def gaffer_date():
    """date of the running career in Gaffer (d/m/yyyy of the loaded save) -> (y, m, d) or None; fetched again only when the save has changed"""
    sl = gaffer_slot()
    if not sl:
        return GDATE.get('v')
    def fetch():
        st = json.load(urllib.request.urlopen(CFG['gaffer'] + '/api/state?slot=' + urllib.parse.quote(sl[0]), timeout=180))
        d, m, y = [int(x) for x in str(st['info']['date']).split('/')[:3]]
        return (y, m, d)
    return _cached(GDATE, sl[1], fetch, min_age=300)   # /api/state of Gaffer reads the whole save (up to 25 s)


def gaffer_list():
    """all players of the running save from Gaffer (current club, potential), fetched again only when the save has changed"""
    sl = gaffer_slot()
    if not sl:
        if GL['p']:
            return GL['p']
        raise OSError('Gaffer not reachable')
    def fetch():
        p = json.load(urllib.request.urlopen(CFG['gaffer'] + '/api/players?slot=' + urllib.parse.quote(sl[0]), timeout=600))['players']
        GL['pot'] = {x['id']: x['pot'] for x in p if x.get('pot')}
        GL['t'] = time.time()
        return p
    v = _cached(GL, sl[1], fetch, min_age=1800)   # /api/players of Gaffer takes minutes and blocks Gaffer meanwhile
    if v is None:
        raise OSError('Gaffer not reachable')
    GL['p'] = v
    return v


def pot_of(pid):
    """potential of the player in the game (FL scale, about 4 above EA FC). Gaffer's potential moves with the current overall of the player (it rises when he improves),
    so it is kept the first time it is read: otherwise a conversion would change the youth bonus of the next one and the results would drift."""
    pc = POTC['d']
    if pc is None:
        try:
            pc = POTC['d'] = json.load(open(os.path.join(DATA, 'potential-ml.json')))
        except (OSError, ValueError):
            pc = POTC['d'] = {}
    k = str(pid)
    if k in pc:
        return pc[k]
    try:
        gaffer_list()
    except Exception:
        pass
    v = GL['pot'].get(pid)
    if v:
        pc[k] = v
        os.makedirs(DATA, exist_ok=True)
        json.dump(pc, open(os.path.join(DATA, 'potential-ml.json'), 'w'))
    return v


POTC = dict(d=None)


def live_squads():
    """ML mode: the squads as they are in the running save (Gaffer: current club of every player, after transfers) -> (tid -> [pids], pid -> tid); None if not available"""
    if SET['mode'] != 'ml':
        return None
    if time.time() - LSQ['t'] < 20:
        return LSQ['d']
    LSQ['t'] = time.time()
    try:
        P = gaffer_list()
        keyed = collections.defaultdict(list)
        for t in M.team:
            if t in M.league_of:
                keyed[fcdb.fold(M.team[t])].append(t)
        bykey = collections.defaultdict(list)
        for t in M.league_of:
            bykey[fcdb.club_key(M.team[t])].append(t)
        tid_of = {}
        for c in {p.get('club') for p in P if p.get('club')}:
            f = fcdb.fold(c)
            L = keyed.get(f) or bykey.get(fcdb.club_key(c)) or []
            if len(L) == 1:
                tid_of[c] = L[0]
        sq, of = collections.defaultdict(list), {}
        for p in P:
            t = tid_of.get(p.get('club'))
            if t and p['id'] in M.pb.index:
                sq[t].append(p['id'])
                of[p['id']] = t
        LSQ['d'] = (dict(sq), of, len(tid_of))
    except Exception as ex:
        print('[live squads]', ex)
        LSQ['d'] = None
    return LSQ['d']


def target_date():
    if SET['mode'] == 'ml':
        return gaffer_date() or timeshift.BASE
    try:
        y, m, d = [int(x) for x in str(SET.get('date') or '').split('-')]
        return (y, m, d)
    except Exception:
        return timeshift.BASE




def months():
    return round(max(-36.0, min(120.0, timeshift.months_between(timeshift.BASE, target_date()))), 2)


def age_base(pid):
    """age at 01.09.2026: from the date of birth of the EA FC entry when there is one, otherwise the age of the database"""
    m = MATCH.get(pid)
    r = m.get('row') if m and m.get('status') == 'ok' else None
    bd = str(r['raw'].get('birthdate') or '') if r else ''
    try:
        d, mo, y = [int(x) for x in bd.split('-')]
        return (timeshift.BASE[0] - y) + (timeshift.BASE[1] - mo) / 12.0 + (timeshift.BASE[2] - d) / 365.0
    except Exception:
        a = M.age.get(pid)
        return float(a) if a else None
M = None
EA = None
MATCH = {}


def load():
    global M, EA
    CFG['journal'] = journal_path()
    if not CFG['pesdb']:
        M = None
        EA = EA or fcdb.load(CFG['csv'])
        return
    plan = CFG['plan'] or os.path.join(CFG['pesdb'], '..', '..', '..', 'leaguebuilder-plan.json')   # names of the leagues, when the database comes with them
    M = dbmeta.Meta(CFG['pesdb'], os.path.join(DATA, 'original-' + db_key()), plan)
    EA = fcdb.load(CFG['csv'])
    MATCH.clear()
    ASSIGN.clear()
    ASSIGN.update(assign_load())


def pos_of(pid):
    return M.pos.get(pid, 5)


def base_club(pid):
    """club in the starting database: that is the club the EA FC export is about, so players are matched with it"""
    return M.team.get(M.club_of.get(pid), '')


def club_name(pid):
    ls = live_squads()
    return M.team.get((ls[1].get(pid) if ls and pid in ls[1] else M.club_of.get(pid)), '')


def cur_ovr(pid):
    return int(round(convert.ovr_model(cur_attrs(pid), pos_of(pid))))


BYCLUB = {}
_EG = {'GK': 'GK', 'CB': 'DF', 'LB': 'DF', 'RB': 'DF', 'LWB': 'DF', 'RWB': 'DF', 'CDM': 'MF', 'CM': 'MF', 'LM': 'MF', 'RM': 'MF', 'CAM': 'MF', 'LW': 'FW', 'RW': 'FW', 'CF': 'FW', 'ST': 'FW'}


def fuzzy(pid):
    """spelling differences inside the squad of the same club (Konstantinos / Kostas Tsimikas): similar name (0.9), same line, age and overall fit, clearly the best"""
    import difflib
    ck = fcdb.club_key(base_club(pid))
    if not ck:
        return None
    if not BYCLUB:
        for r in EA.rows:
            BYCLUB.setdefault(r['ck'], []).append(r)
    pos = pos_of(pid)
    g = 'GK' if pos == 0 else 'DF' if pos <= 3 else 'MF' if pos <= 8 else 'FW'
    nm, age, cur = fcdb.fold(M.name.get(pid, '')), M.age.get(pid), orig_ovr(pid)
    best = []
    for k, L in BYCLUB.items():
        if not k or not (k == ck or k <= ck or ck <= k):
            continue
        for x in L:
            if _EG.get(x['pos'], 'MF') != g or abs(x['rating'] - cur) > 9 or (age and x['byear'] and abs(2026 - x['byear'] - age) > 2):
                continue
            sc = max(difflib.SequenceMatcher(None, nm, x['full']).ratio(), difflib.SequenceMatcher(None, nm, fcdb.fold(x['raw'].get('common_name'))).ratio())
            if sc >= 0.9:
                best.append((sc, x))
    best.sort(key=lambda t: -t[0])
    if best and (len(best) == 1 or best[0][0] - best[1][0] >= 0.05):
        return best[0][1]
    return None


def orig_ovr(pid):
    """overall of the original database (the in-game copy players_base.bin): the matching must not change when Player.bin has been written"""
    a = M.base_attrs.get(pid)
    if a:
        return convert.ovr_model(a, pos_of(pid))
    return cur_ovr(pid)


def assign_file():
    return os.path.join(DATA, 'assign-%s.json' % db_key())


def assign_load():
    try:
        return json.load(open(assign_file(), encoding='utf-8'))
    except (OSError, ValueError):
        return {}


ASSIGN = {}   # pid -> EA FC id chosen by the user; kept, so that the player is found again without asking


def assign_set(pid, db_id):
    if db_id:
        ASSIGN[str(pid)] = str(db_id)
    else:
        ASSIGN.pop(str(pid), None)
    os.makedirs(DATA, exist_ok=True)
    json.dump(ASSIGN, open(assign_file(), 'w'), indent=0)
    MATCH.pop(pid, None)


def match(pid):
    m = MATCH.get(pid)
    if m is None and str(pid) in ASSIGN:
        m = EA.match('', None, db_id=ASSIGN[str(pid)])
        if m['status'] == 'ok':
            m['why'] = 'assigned by you'
            MATCH[pid] = m
            return m
        m = None
    if m is None:
        gk = pos_of(pid) == 0
        m = EA.match(M.name.get(pid, ''), base_club(pid), None, gk, ovr=orig_ovr(pid), age=M.age.get(pid), height=M.height.get(pid))
        if m['status'] == 'none':
            x = fuzzy(pid)
            if x:
                m = dict(status='ok', row=x, candidates=[], why='similar name in the club')
        MATCH[pid] = m
    return m


JC = dict(path=None, mt=None, d={})


def journal():
    """the journal of the tool (what was written for which player); parsed again only when the file has changed (it has tens of thousands of entries)"""
    p = CFG['journal']
    try:
        st = os.stat(p)
    except OSError:
        return {}
    if JC['path'] != p or JC['mt'] != (st.st_mtime_ns, st.st_size):
        try:
            JC['d'] = json.load(open(p))
        except Exception:
            JC['d'] = {}
        JC['path'], JC['mt'] = p, (st.st_mtime_ns, st.st_size)
    return JC['d']


def ahash(att):
    return hashlib.md5(bytes(att[a] for a in plbin.AB)).hexdigest()[:12]


YF = dict(youth=True, profile=True, skills='off', psboost=False)   # setting of the last write (for the journal)


def sig_of(pid, src, youth):
    """what a conversion depends on: the EA FC player found, the youth bonus and the development period (in quarters). Pages (FMInside / SoFIFA) have no signature: only the values count."""
    if src not in ('EA FC', 'scaled'):
        return 'page'
    m = match(pid)
    sid = m['row']['id'] if src == 'EA FC' and m['status'] == 'ok' else src
    return hashlib.md5(('%s|%d|%d|p%d|s%d' % (sid, int(bool(youth)), int(months() // 3), int(YF.get('profile', True)), {'off': 0, 'add': 1, 'replace': 2}.get(YF.get('skills'), 0) + 4 * int(bool(YF.get('psboost'))))).encode()).hexdigest()[:10]


def jentry(pid, src, att):
    return dict(src=src, when=time.strftime('%Y-%m-%d %H:%M'), h=ahash(att), sig=sig_of(pid, src, YF['youth']), a=[att[x] for x in plbin.AB])


def near(cur, j, tol=3):
    """the values are still (about) what was written: small changes by the game (training, form) do not count as a change"""
    a = j.get('a')
    return bool(a) and all(abs(cur[x] - v) <= tol for x, v in zip(plbin.AB, a))


def unchanged(pid, cur, youth, jn):
    """converted earlier by this tool and nothing changed that matters: same source, same settings, values still as written"""
    j = jn.get(str(pid))
    if not j or not j.get('sig') or not near(cur, j):
        return False
    ok = match(pid)['status'] == 'ok'
    if (j['src'] == 'scaled' and ok) or (j['src'] == 'EA FC' and not ok):   # EA FC found / lost since
        return False
    return j['sig'] == sig_of(pid, j['src'], youth)


def is_done(pid, youth=True):
    """-> (source name, stale): source name when the attributes in Player.bin equal what the conversion of the source that is found NOW gives (EA FC: recomputed from the current
    export; FMInside / SoFIFA page: the values the tool wrote, unchanged since), otherwise (None, True) when the tool wrote the player earlier but the values differ from the
    current source, else (None, False)"""
    cur = cur_attrs(pid)
    j = journal().get(str(pid))
    m = match(pid)
    if j and j.get('sig') and j.get('a'):   # remembered with its signature: only a change of the source, the settings or (more than a little) of the values counts
        if unchanged(pid, cur, youth, {str(pid): j}):
            return ('scaled to EA level' if j['src'] == 'scaled' else j['src']), False
        return None, True
    if m['status'] == 'ok':
        try:
            p = preview(dict(pid=pid, youth=youth))
            if p.get('ok') and p['final'] == cur:
                return 'EA FC', False
        except Exception:
            pass
        return None, bool(j)
    if j and j.get('src') in ('FMInside', 'SoFIFA', 'scaled'):
        same = j.get('h') == ahash(cur) or j.get('attrs') == cur
        return ('scaled to EA level' if j['src'] == 'scaled' else j['src'], False) if same else (None, True)
    return None, bool(j)


def pl_row(pid, youth=True):
    m = match(pid)
    dn, stale = is_done(pid, youth)
    d = dict(done=dn, stale=stale, pid=pid, name=M.name.get(pid) or ('Player %d' % pid), pos=dbmeta.POS_NAMES[pos_of(pid)] if pos_of(pid) < 13 else '?', age=M.age.get(pid), ovr=cur_ovr(pid), status=m['status'])
    if m['status'] == 'ok':
        r = m['row']
        d['ea'] = dict(name=r['name'], club=r['club'], rating=r['rating'], why=m['why'])
    return d


def squad_of(tid):
    ls = live_squads()
    return ls[0].get(tid, []) if ls and tid in ls[0] else M.players_of(tid)


PROFILE_FIELDS = ('height', 'weight', 'foot')
PROFILE_RANGE = dict(height=(140, 230), weight=(40, 140))


def profile_for(pid, row, edits=None):
    """height, weight and preferred foot: what the database has now and what the EA FC entry (or your own edit) says -> {field: {cur, new, src}}; only fields that have a value"""
    pb = M.pb
    i = pb.index[pid]
    cur = dict(height=pb.height(i), weight=pb.weight(i), foot=pb.foot(i))
    out = {}
    for f in PROFILE_FIELDS:
        new = src = None
        if row:
            raw = row['height'] if f == 'height' else row['raw'].get(f)
            if f == 'foot':
                new = raw if raw in ('Left', 'Right') else None
            else:
                try:
                    new = int(float(raw)) if raw not in (None, '') else None
                except (TypeError, ValueError):
                    new = None
            src = 'EA FC' if new is not None else None
        ed = (edits or {}).get(f)
        if ed not in (None, ''):
            if f == 'foot':
                new = 'Left' if str(ed).lower().startswith('l') else 'Right'
            else:
                lo, hi = PROFILE_RANGE[f]
                new = max(lo, min(hi, int(float(ed))))
            src = 'you'
        if new is not None:
            out[f] = dict(cur=cur[f], new=new, src=src)
    return out


def gaffer_player(pid):
    """value, wage, potential and contract of the player in the running save (Gaffer), when Gaffer is reachable"""
    try:
        if SET['mode'] != 'ml' and not GUP['ok'] and time.time() - GUP['t'] < 30:
            return None   # Gaffer was not reachable a moment ago
        try:
            gaffer_list()
        except Exception:
            GUP.update(t=time.time(), ok=False)
            return None
        GUP.update(t=time.time(), ok=True)
        if GL.get('byid_t') != GL['t']:
            GL['byid'] = {p['id']: p for p in GL['p']}
            GL['byid_t'] = GL['t']
        g = GL['byid'].get(pid)
        return dict(mv=g.get('mv'), sal=g.get('sal'), pot=g.get('pot'), until=g.get('until'), ovr=g.get('ovr'), club=g.get('club')) if g else None
    except Exception:
        return None


def skillset_for(pid, row, mode):
    """skills, COM playing styles and playing style from the EA FC PlayStyles of the entry: mode 'add' keeps what the player has, 'replace' gives him exactly what the PlayStyles give
    -> {'skills'|'com_styles'|'playing_style': {cur, new, add, rem}} only where something changes"""
    if mode not in ('add', 'replace') or not row:
        return {}
    ps = playstyle.parse(row['raw'].get('playstyles'))
    if not ps:
        return {}
    pb = M.pb
    i = pb.index[pid]
    try:
        pen = int(row['raw'].get('penalties')) if row['raw'].get('penalties') else None
    except ValueError:
        pen = None
    d = playstyle.derive(ps, pos_of(pid), dict(penalties=pen), pid)
    vs, vc = playstyle.values_fit(row['raw'], pos_of(pid))   # a skill needs the EA PlayStyle AND values that fit
    d['skills'] = (d['skills'] & vs) | d['direct']   # the PlayStyle that IS the skill (Precision Header = Heading) needs no test of the values
    d['com'] = (d['com'] & vc) | d['direct_com']
    if d['style'] and not playstyle.style_fits(d['style'], row['raw'], pos_of(pid)):
        d['style'] = None
    out = {}
    mg = playstyle.margins(row['raw'], pos_of(pid))
    for key, cur, want, lim, dr in (('skills', pb.skills(i), d['skills'], playstyle.MAX_SKILLS, d['direct']), ('com_styles', pb.com_styles(i), d['com'], playstyle.MAX_COM, d['direct_com'])):
        new = playstyle.cap(cur, want, mode, lim, lambda n: (n in dr) * 100 + mg.get(n, 0))   # at most 10 skills / 5 COM styles
        if new != cur:
            out[key] = dict(cur=sorted(cur), new=sorted(new), add=sorted(new - cur), rem=sorted(cur - new))
    cs = pb.playing_style(i)
    if d['style'] and d['style'] != cs:
        out['playing_style'] = dict(cur=cs, new=d['style'])
    return out


def values_traits_for(pid, final, mode, row=None, paste=False):
    """players for whom EA FC has no PlayStyles (not in the data, a page that was pasted, a profile that is still empty): skills, COM styles and playing style from their values and their
    position, and the positions they can play -> same form as skillset_for"""
    if mode not in ('add', 'replace'):
        return {}
    pb = M.pb
    i = pb.index[pid]
    pos = pos_of(pid)
    out = {}
    cur_sk, cur_cm, cur_st = pb.skills(i), pb.com_styles(i), pb.playing_style(i)
    if not cur_sk and not cur_cm or paste:   # a filled profile (from the game) is kept as it is; an empty one (or a pasted page) is filled from the values
        t = playstyle.traits_from_values(final, pos)
        rk = lambda n: t.get('margin', {}).get(n, 0)
        t['skills'] = playstyle.cap(cur_sk, t['skills'], 'replace', playstyle.MAX_SKILLS, rk)   # at most 10 skills / 5 COM styles
        t['com'] = playstyle.cap(cur_cm, t['com'], 'replace', playstyle.MAX_COM, rk)
        if t['skills']:
            out['skills'] = dict(cur=sorted(cur_sk), new=sorted(t['skills']), add=sorted(t['skills']), rem=[])
        if t['com']:
            out['com_styles'] = dict(cur=sorted(cur_cm), new=sorted(t['com']), add=sorted(t['com']), rem=[])
        if t['style'] and (cur_st == 'Balanced' or paste):
            out['playing_style'] = dict(cur=cur_st, new=t['style'])
    return out


def unfilled(pid):
    """a profile that nobody has filled yet (no skills, no COM style, playing style 'Balanced'): a player that is new in the game"""
    pb = M.pb
    i = pb.index[pid]
    return not pb.skills(i) and not pb.com_styles(i) and pb.playing_style(i) == 'Balanced'


def positions_for(pid, final, row=None, paste=False):
    """positions that the values make safe, added to the ones the player has (never lowered) -> {'cur', 'new', 'add'} or None. For a player of the EA FC data only the alternative
    positions of EA FC count (confirmed by the values); a player with an empty profile or a pasted page gets them from the values and his position."""
    pb = M.pb
    i = pb.index[pid]
    cur = pb.positions(i)
    alt = [a for a in (row['alt'] if row else []) if a]
    if alt:
        prop = playstyle.positions_from_values(final, pos_of(pid), alt, only_alt=True)
    elif paste or unfilled(pid):
        prop = playstyle.positions_from_values(final, pos_of(pid))
    else:
        return None
    new = [max(a, b) for a, b in zip(cur, prop)]
    if new == cur:
        return None
    return dict(cur=cur, new=new, add=[dbmeta.POS_NAMES[k] for k in range(13) if new[k] > cur[k]])


def ea_names(row):
    """names of the EA FC player: with a common name (Vini Jr.) it is name and shirt name, otherwise first + last name and the surname on the shirt"""
    r = row['raw']
    cn = (r.get('common_name') or '').strip()
    first, last = (r.get('first_name') or '').strip(), (r.get('last_name') or '').strip()
    full = cn or ('%s %s' % (first, last)).strip()
    shirt = (cn or last or full).upper()
    return dict(name=full, shirt=shirt, nshirt=shirt)


def missing(cid=None, limit=500):
    """players that are not found in the EA FC database (or only uncertain), best overall first: of one league, or of the whole database"""
    if cid is not None:
        pids = [p for t in M.leagues[cid]['teams'] for p in squad_of(t)]
    else:
        pids = [p for p in M.pb.ids if club_name(p)]   # players of a club; classic players and free agents without a club are not listed
    out = []
    for p in pids:
        m = match(p)
        if m['status'] != 'ok':
            out.append(dict(pid=p, name=M.name.get(p) or ('Player %d' % p), club=club_name(p), pos=dbmeta.POS_NAMES[pos_of(p)] if pos_of(p) < 13 else '?', age=M.age.get(p), ovr=cur_ovr(p), status=m['status']))
    out.sort(key=lambda x: -x['ovr'])
    return dict(ok=True, total=len(out), of=len(pids), players=out[:limit])


FIND = dict(key=None, teams=[], players=[])


def find(q, limit=12):
    """search of the page: teams and players by name (every word has to appear), best first"""
    words = fcdb.fold(q).split()
    if not words or M is None:
        return dict(ok=True, teams=[], players=[])
    if FIND['key'] is not M:   # built once per loaded database
        FIND.update(key=M, teams=[(fcdb.fold(n), tid) for tid, n in M.team.items() if tid in M.league_of],
                    players=[(pid, fcdb.fold(M.name.get(pid, '') + ' ' + M.short.get(pid, ''))) for pid in M.pb.ids])
    def rank(blob, first):
        return 0 if blob.startswith(words[0]) else (1 if (' ' + words[0]) in (' ' + blob) else 2)
    teams = sorted(((rank(b, 0), M.team[t], t) for b, t in FIND['teams'] if all(w in b for w in words)), key=lambda x: (x[0], x[1]))[:limit]
    hits = [pid for pid, b in FIND['players'] if all(w in b for w in words)]
    hits.sort(key=lambda p: rank(fcdb.fold(M.name.get(p, '')), 0))
    top = hits[:400]   # the overall is only computed for the best matches
    top.sort(key=lambda p: (rank(fcdb.fold(M.name.get(p, '')), 0), -cur_ovr(p)))
    hits = top + hits[400:]
    pl = [dict(pid=p, name=M.name.get(p) or ('Player %d' % p), club=club_name(p), pos=dbmeta.POS_NAMES[pos_of(p)] if pos_of(p) < 13 else '?', age=M.age.get(p), ovr=cur_ovr(p)) for p in hits[:limit]]
    return dict(ok=True, teams=[dict(tid=t, name=n, league=(M.leagues.get(M.league_of.get(t)) or {}).get('name'), lid=M.league_of.get(t)) for _, n, t in teams], players=pl, more=max(0, len(hits) - limit))


def club_view(tid, youth=True):
    pids = squad_of(tid)
    pl = [pl_row(p, youth) for p in pids]
    pl.sort(key=lambda x: -x['ovr'])
    return dict(ok=True, tid=tid, name=M.team.get(tid, ''), league=(M.leagues.get(M.league_of.get(tid)) or {}).get('name'), players=pl, found=sum(1 for x in pl if x['status'] == 'ok'), total=len(pl),
                done=sum(1 for x in pl if x.get('done')))


def league_view(cid):
    L = M.leagues[cid]
    out = []
    for t in L['teams']:
        pids = squad_of(t)
        out.append(dict(tid=t, name=M.team.get(t, ''), n=len(pids), found=sum(1 for p in pids if match(p)['status'] == 'ok')))
    return dict(ok=True, id=cid, name=L['name'], clubs=out)


def candidates(pid, q=None):
    name = M.name.get(pid, '')
    seen, out = set(), []
    qs = [q] if q else [name] + [t for t in fcdb.fold(name).split() if len(t) > 3][::-1]
    cur = cur_ovr(pid)
    gk = pos_of(pid) == 0
    ck = fcdb.club_key(base_club(pid))
    for s in qs:
        for x in EA.search(s, 30):
            if x['id'] in seen or (not q and (x['pos'] == 'GK') != gk):
                continue
            seen.add(x['id'])
            out.append((0 if (ck and x['ck'] and ck & x['ck']) else 1, abs(x['rating'] - cur), x))
    out.sort(key=lambda t: (t[0], t[1]))
    return [dict(id=x['id'], name=x['name'], club=x['club'], rating=x['rating'], pos=x['pos'], nation=x['nation']) for _, _, x in out[:10]]


YOUTH = {16: 1.0, 17: 1.0, 18: 1.0, 19: 0.85, 20: 0.65, 21: 0.45, 22: 0.25}


def youth_bonus(pid, rating, pot=None):
    """Small raise of the overall for young players whose potential is far above the rating (gap from 6 points, +3 at 14), weighted by age (16-18 full, 22 a quarter, from 23 none).
    The potential comes from the EA FC entry (if the export has the column) or from a SoFIFA page; without a potential there is no bonus."""
    age = M.age.get(pid)
    f = YOUTH.get(age, 0.0 if age and age > 22 else (1.0 if age else 0.0))
    if not rating:
        return 0
    if pot:   # potential on the EA FC scale (SoFIFA page or the data)
        gap = pot - rating
    else:     # potential of the game (Master League, via Gaffer; its scale is about 4 above EA FC); none known: no bonus
        gp = pot_of(pid)
        if not gp:
            return 0
        gap = gp - 4 - rating
    return int(round(min(3.0, max(0.0, (gap - 5) / 3.0)) * f))   # only a clearly large gap counts: from 6 points, +3 at 14


def row_for(pid, db_id=None):
    if db_id:
        m = EA.match('', None, db_id=db_id)
        return m['row']
    m = match(pid)
    return m['row'] if m['status'] == 'ok' else None


def preview(body):
    pid = int(body['pid'])
    i = M.pb.index[pid]
    fm = body.get('fm') or None
    row = None if fm else row_for(pid, body.get('db_id'))
    if not fm and row is None:
        m = match(pid)
        return dict(ok=False, status=m['status'], msg='Not found in the database.' if m['status'] == 'none' else 'Several players or an uncertain match: choose one.',
                    candidates=candidates(pid))
    target = body.get('target')
    yb = 0
    if target is None and row is not None and body.get('youth', True):
        yb = youth_bonus(pid, row['rating'], row.get('potential'))
        target = row['rating'] + yb if yb else None
    if target is None and fm and not convert.sofifa.is_fm(fm):   # SoFIFA page: its overall (and potential) are the target
        pg = convert.sofifa.parse_page(fm)
        if pg.get('overall'):
            yb = youth_bonus(pid, pg['overall'], pg.get('potential')) if body.get('youth', True) else 0
            target = pg['overall'] + yb
    mo = months()
    boost = playstyle.boosts(playstyle.parse(row['raw'].get('playstyles'))) if (row and not fm and body.get('psboost')) else None
    want = body.get('target')   # a target typed by the user is the overall AFTER the development: the fit is moved by the difference (the development comes on top of the fit)
    tg = target
    for _ in range(4):
        p = convert.preview(M.pb, i, pos_of(pid), EA, row, fm, tg, CFG['fmcal'], cur=cur_attrs(pid), months=mo, age=age_base(pid), pid=pid, edits=body.get('edits'), boost=boost)
        if want is None or not p.get('ok') or p['ovr_new'] == int(want):
            break
        tg += int(want) - p['ovr_new']
    if want is not None and p.get('ok'):
        p['ovr_target'] = int(want)
    if body.get('db_id') and p.get('ok') and ASSIGN.get(str(pid)) != str(body['db_id']):
        assign_set(pid, body['db_id'])   # the choice is remembered
    if p.get('ok') and p.get('db') and str(pid) in ASSIGN:
        p['assigned'] = True
    if p.get('ok'):
        p['youth'] = yb
        p['age'] = M.age.get(pid)
        p['months'] = mo
        p['date'] = '%02d.%02d.%d' % target_date()[::-1]
        p['names'] = {f: M.pb.get_name(i, f) for f in ('name', 'shirt', 'nshirt')}
        if row and not fm:
            p['names_ea'] = ea_names(row)
        p['profile'] = profile_for(pid, row if not fm else None, body.get('pedits'))
        mode = body.get('skills', 'off')
        has_ps = bool(row and not fm and playstyle.parse(row['raw'].get('playstyles')))
        p['skillset'] = skillset_for(pid, row if not fm else None, mode) if has_ps else values_traits_for(pid, p['final'], mode, row, paste=bool(fm))
        if mode in ('add', 'replace'):
            pz = positions_for(pid, p['final'], row if not fm else None, paste=bool(fm))
            if pz:
                p['skillset']['positions'] = pz
        p['pos_ovr'] = {k: int(round(convert.ovr_model(p['final'], k))) for k in range(13)}
        p['positions'] = M.pb.positions(i)
        p['pos_main'] = pos_of(pid)
        raw = row['raw'] if (row and not fm) else {}
        p['info'] = dict(full=('%s %s' % (raw.get('first_name', ''), raw.get('last_name', ''))).strip() if raw else '', nation=raw.get('nation_name') or '', club_ea=raw.get('club_name') or '',
                         birthdate=raw.get('birthdate') or '', height=M.pb.height(i), weight=M.pb.weight(i), foot=M.pb.foot(i), ea_foot=raw.get('foot') or '', weak_foot=raw.get('weak_foot') or '',
                         skill_moves=raw.get('skill_moves') or '', rating=(row or {}).get('rating') if row and not fm else None, potential=(row or {}).get('potential') if row and not fm else None,
                         ea_pos=raw.get('position') or '', age=M.age.get(pid))
        p['gaffer'] = gaffer_player(pid)
        p['traits'] = dict(skills=sorted(M.pb.skills(i)), com=sorted(M.pb.com_styles(i)), style=M.pb.playing_style(i), weak_use=M.pb.weak_foot_use(i), weak_acc=M.pb.weak_foot_acc(i))
        p['ea_styles'] = sorted(playstyle.parse(row['raw'].get('playstyles')).items()) if row and not fm else []
    if p.get('ok'):
        p['pid'] = pid
        p['name'] = M.name.get(pid)
        p['club'] = club_name(pid)
    return p


def backup():
    os.makedirs(CFG['backups'], exist_ok=True)
    f = os.path.join(CFG['backups'], 'Player.bin.%s' % time.strftime('%Y%m%d-%H%M%S'))
    shutil.copy2(os.path.join(CFG['pesdb'], 'Player.bin'), f)
    return f


def apply(body):
    """Writes the converted values of the chosen players (into Player.bin or into the running game, see the mode); the user's own values and names are applied on top."""
    dry = bool(body.get('dry'))
    YF['youth'] = bool(body.get('youth', True))
    YF['profile'] = bool(body.get('profile', True))
    YF['skills'] = body.get('skills', 'off')
    YF['psboost'] = bool(body.get('psboost'))
    choices = {int(k): v for k, v in (body.get('choices') or {}).items()}
    pids = [int(p) for p in body.get('pids') or []]
    for t in body.get('tids') or []:   # whole clubs: every player that is found unambiguously
        pids += [p for p in squad_of(int(t)) if match(p)['status'] == 'ok' and p not in pids]
    report, writes, srcs, names, profs = [], {}, {}, {}, {}
    sk_n = 0
    for pid in pids:
        ch = choices.get(pid) or {}
        done = not ch and not body.get('force') and (len(pids) > 1) and is_done(pid, body.get('youth', True))[0]
        if done and not (YF['profile'] or YF['skills'] != 'off'):
            report.append(dict(pid=pid, name=M.name.get(pid), ok=False, msg='already converted', skipped=True))
            continue
        try:
            p = preview(dict(pid=pid, db_id=ch.get('db_id'), fm=ch.get('fm'), target=ch.get('target'), edits=ch.get('edits'), pedits=ch.get('pedits'), skills=YF['skills'], psboost=YF['psboost'], youth=body.get('youth', True)))
        except Exception as ex:
            p = dict(ok=False, msg=str(ex))
        if not p.get('ok'):
            report.append(dict(pid=pid, name=M.name.get(pid), ok=False, msg=p.get('msg'), ovr=cur_ovr(pid)))
            continue
        cur = cur_attrs(pid)
        if done:   # converted earlier: only what changed in the profile
            p['final'] = cur
        if p['final'] != cur:
            writes[pid] = p['final']
            srcs[pid] = p.get('source') or 'EA FC'
        if YF['profile'] or ch.get('pedits'):
            pr = {f: v['new'] for f, v in (p.get('profile') or {}).items() if v['new'] != v['cur'] and (YF['profile'] or v['src'] == 'you')}
            if pr:
                profs[pid] = pr
        if YF['skills'] != 'off' and p.get('skillset'):
            profs.setdefault(pid, {}).update({k: v['new'] for k, v in p['skillset'].items()})
            sk_n += 1
        want = dict(p.get('names_ea') or {}) if body.get('ea_names') else {}
        want.update(ch.get('names') or {})
        nm = {k: v for k, v in want.items() if k in plbin.NAME_OFFS and str(v).strip() and str(v) != p['names'].get(k)}
        if nm:
            names[pid] = nm
        if done and pid not in profs:
            report.append(dict(pid=pid, name=M.name.get(pid), ok=False, msg='already converted', skipped=True))
            continue
        report.append(dict(pid=pid, name=M.name.get(pid), ok=True, ovr_cur=p['ovr_cur'], ovr_new=p['ovr_new'], target=p['ovr_target']))
    for pid, ch in choices.items():   # only names changed (nothing else to convert)
        if pid not in writes and (ch.get('names')) and pid in M.pb.index:
            nm = {k: v for k, v in ch['names'].items() if k in plbin.NAME_OFFS and str(v).strip()}
            if nm:
                names[pid] = nm
    if dry or not (writes or names or profs):
        return dict(ok=True, dry=True, report=report, written=0, profile=len(profs), skills=sk_n)
    r = commit(writes, srcs, names, profs)
    if SET['mode'] == 'ml' and names:
        r['skipped'] = dict(names=len(names))   # names, height, weight and foot are not written into the running game
    return dict(r, report=report, dry=False, mode=SET['mode'])


def commit(writes, srcs, names=None, profs=None):
    """-> dict(ok, written, backup)"""
    if SET['mode'] == 'ml':
        return ml_write(writes, srcs, profs)
    r = write_all(writes, srcs, names or {}, profs or {})
    if r.get('ok'):
        r['edit'] = drop_edit()
    return r


def _keep(path, name):
    """moves/copies a file we are about to remove or replace into DATA/moved (nothing is deleted for good)"""
    os.makedirs(os.path.join(DATA, 'moved'), exist_ok=True)
    dst = os.path.join(DATA, 'moved', '%s.%s' % (name, time.strftime('%Y%m%d-%H%M%S')))
    shutil.copy2(path, dst)
    return dst


def drop_edit():
    """EDIT00000000 of Football Life 2027 (the game's own file of edited data) overwrites the database at the start: after a write it has to go (a copy is kept in DATA/moved)"""
    p = os.path.abspath(CFG['pesdb'] or '')
    sub = os.path.join('Documents', 'SPGAME', 'Football Life', '2027', 'save', 'EDIT00000000')
    if 'drive_c' in p:   # Wine / Proton prefix
        c = glob.glob(os.path.join(p.split('drive_c')[0], 'drive_c', 'users', '*', sub))
    else:
        c = [os.path.join(os.path.expanduser('~'), sub)]
    c = [f for f in c if os.path.isfile(f)]
    if not c:
        return 'EDIT00000000 not found: if the game has one (save folder of Football Life 2027), delete it yourself, it would overwrite the new values.'
    try:
        for f in c:
            _keep(f, 'EDIT00000000')
            os.remove(f)
    except OSError as ex:
        return 'EDIT00000000 could not be removed (%s): delete it yourself, the game is probably running.' % ex
    return 'EDIT00000000 removed (copy in %s)' % os.path.join(DATA, 'moved')


MOD = dict(state='')   # GrowthBridge.lua in the modules folder of Sider: 'ok' | 'updated' | 'none'


def modules_dir():
    if SET.get('modules'):
        return SET['modules']
    b = bridge_dir()   # .../SiderAddons/content/ml-immersion/bridge -> .../SiderAddons/modules
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(b))), 'modules') if b else ''


def sync_module():
    """our adapted GrowthBridge.lua (data/GrowthBridge.lua) must be the one in the modules folder: checked at the start and when the folders change, replaced if it differs"""
    d = modules_dir()
    dst = os.path.join(d, 'GrowthBridge.lua') if d else ''
    if not d or not os.path.isdir(d):
        MOD['state'] = 'none'
        return
    src = os.path.join(HERE, 'data', 'GrowthBridge.lua')
    if os.path.isfile(dst) and open(dst, 'rb').read() == open(src, 'rb').read():
        MOD['state'] = 'ok'
        return
    try:
        if os.path.isfile(dst):
            _keep(dst, 'GrowthBridge.lua')
        shutil.copy2(src, dst)
        MOD['state'] = 'updated'
    except OSError:
        MOD['state'] = 'none'


JOB = dict(state='idle')


def bulk_job(rest, youth, dry, profile=True, skills='off', psboost=False):
    """The whole database: players that are in the EA FC export are converted, the others are kept or brought to the EA level (same profile, lower level)."""
    global JOB
    t0 = time.time()
    YF['youth'] = bool(youth)
    YF['profile'] = bool(profile)
    YF['skills'] = skills
    YF['psboost'] = bool(psboost)
    profs = {}
    pb = M.pb
    jn = journal()
    writes, srcs = {}, {}
    cnt = collections.Counter()
    chg_f, chg_s = [], []
    mo = months()
    JOB = dict(state='running', done=0, total=pb.n, dry=dry, t=t0)
    try:
        for n, pid in enumerate(pb.ids):
            JOB['done'] = n
            i = pb.index[pid]
            cur = cur_attrs(pid)
            same = unchanged(pid, cur, youth, jn)
            if same and (not (profile or skills != 'off') or jn[str(pid)]['src'] != 'EA FC'):
                cnt['already'] += 1
                continue
            m = match(pid)
            if m['status'] == 'ok':
                p = preview(dict(pid=pid, youth=youth, skills=skills, psboost=psboost))
                if not p.get('ok'):
                    cnt['failed'] += 1
                    continue
                pr = {f: v['new'] for f, v in (p.get('profile') or {}).items() if v['new'] != v['cur']} if profile else {}
                if skills != 'off' and p.get('skillset'):
                    pr.update({k: v['new'] for k, v in p['skillset'].items()})
                    cnt['skills'] += 1
                if same:   # converted earlier: only what changed in the profile (new PlayStyles, positions ...), the attributes stay
                    p['final'] = cur
                if p['final'] == cur and not pr:
                    cnt['already'] += 1
                    continue
                if pr:
                    profs[pid] = pr
                    cnt['profile'] += 1
                if p['final'] != cur:
                    writes[pid], srcs[pid] = p['final'], 'EA FC'   # (the file only changes where values differ; the running game gets only the differences, see ml_write)
                    chg_f.append(p['ovr_new'] - p['ovr_cur'])
                    cnt['converted'] += 1
            elif rest == 'scale':
                j = jn.get(str(pid))
                if j and j.get('src') == 'scaled' and j.get('h') == ahash(cur):
                    cnt['already'] += 1
                    continue
                # always from the ORIGINAL values (players_base.bin), never from what is in the database now: a second run gives the same result instead of scaling down again
                p = convert.scale_player(pb, i, pos_of(pid), M.age.get(pid), cur=M.base_attrs.get(pid) or pb.attrs(i), months=mo, pid=pid)
                if p['final'] == cur:
                    cnt['already'] += 1
                    continue
                if skills != 'off':   # players that are not in the EA FC data: skills, playing style and positions from their values and position
                    tr = values_traits_for(pid, p['final'], skills)
                    pz = positions_for(pid, p['final'], None)
                    if pz:
                        tr['positions'] = pz
                    if tr:
                        profs.setdefault(pid, {}).update({k: v['new'] for k, v in tr.items()})
                        cnt['skills'] += 1
                writes[pid], srcs[pid] = p['final'], 'scaled'
                chg_s.append(p['ovr_new'] - p['ovr_cur'])
                cnt['scaled'] += 1
            else:
                cnt['kept'] += 1
        res = dict(counts=dict(cnt), mean_converted=round(sum(chg_f) / len(chg_f), 2) if chg_f else 0, mean_scaled=round(sum(chg_s) / len(chg_s), 2) if chg_s else 0, months=mo)
        if dry or not (writes or profs):
            JOB = dict(state='done', dry=True, result=res, secs=round(time.time() - t0, 1))
            return
        JOB['done'] = pb.n
        JOB['phase'] = 'writing'
        r = commit(writes, srcs, None, profs)
        JOB = dict(state='done' if r.get('ok') else 'error', dry=False, result=res, write=r, secs=round(time.time() - t0, 1))
    except Exception as ex:
        JOB = dict(state='error', msg=str(ex))


def write_all(writes, srcs, names, profs=None):
    profs = profs or {}
    """Player.bin: backup, write, read again and check, journal"""
    with LOCK:
        pb = M.pb
        before = bytes(pb.data)
        bk = backup()
        try:
            for pid, att in writes.items():
                i = pb.index[pid]
                for a, v in att.items():
                    pb.set(i, a, v)
            for pid, nm in names.items():
                for k, v in nm.items():
                    pb.set_name(pb.index[pid], k, v)
            for pid, pr in profs.items():
                for k, v in pr.items():
                    getattr(pb, 'set_' + k)(pb.index[pid], v)
            pb.save()
            exp = {pid: dict(attrs=writes.get(pid), names=names.get(pid), prof=profs.get(pid)) for pid in set(writes) | set(names) | set(profs)}
            bad = plbin.verify(pb.path, pb.ids, exp, before)
            if bad:
                raise ValueError('; '.join(bad[:3]))
        except Exception as ex:
            shutil.copy2(bk, pb.path)
            pb.data[:] = before
            pb.orig = bytes(before)
            return dict(ok=False, msg='Writing failed, the backup was restored: %s' % ex, backup=bk)
        MATCH.clear()
        jn = journal()
        for pid in writes:
            jn[str(pid)] = jentry(pid, srcs.get(pid), pb.attrs(pb.index[pid]))
        json.dump(jn, open(CFG['journal'], 'w'))
        return dict(ok=True, written=len(writes), names=len(names), profile=len(profs), backup=bk)


ML_TAGS = {}

ML_CHUNK = int(os.environ.get('FLDB_CHUNK', 20000))

JQ = dict(state='idle')

JQ_RESULT = {}


def _bridge(name):
    return os.path.join(bridge_dir(), name)


def _compact(tx):
    """removes the commands of the packages that are done (or cancelled) from growth.csv, so that the file stays small; atomic, and tried again when Gaffer appended meanwhile"""
    p = _bridge('growth.csv')
    for _ in range(5):
        size = os.path.getsize(p)
        with open(p, encoding='utf-8', errors='replace', newline='') as fh:
            keep = [ln for ln in fh.read().split('\n') if ln and ln.split(',', 1)[0] not in tx]
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write('\n'.join(keep) + ('\n' if keep else ''))
        if os.path.getsize(p) == size:
            os.replace(tmp, p)
            return
    os.remove(tmp)


def _jwrite(pids, writes, srcs):
    jn = journal()
    for pid in pids:
        if pid in writes:
            jn[str(pid)] = jentry(pid, srcs.get(pid), writes[pid])
    json.dump(jn, open(CFG['journal'], 'w'))


def _feed(tag, chunks, writes, srcs, expect):
    """package by package: append to growth.csv, wait until the game has answered every command of the package, remove the package from the file, next"""
    global JQ
    rp = _bridge('growth-result.csv')
    off = os.path.getsize(rp) if os.path.isfile(rp) else 0
    try:
        for ci, (pids, lines) in enumerate(chunks, 1):
            if JQ.get('cancel'):
                break
            tx = {ln.split(',', 1)[0] for ln in lines}
            seen = set()
            for pid in pids:
                if pid in writes:
                    PEND[pid] = (time.time(), dict(writes[pid]))
            with open(_bridge('growth.csv'), 'a', encoding='utf-8', newline='\n') as fh:
                fh.write('\n'.join(lines) + '\n')
            JQ.update(chunk=ci, sent=JQ['sent'] + len(lines), msg='Package %d of %d sent, waiting for the game …' % (ci, len(chunks)))
            last = time.time()
            while len(seen) < len(tx) and not JQ.get('cancel'):
                time.sleep(2)
                if os.path.isfile(rp) and os.path.getsize(rp) > off:
                    with open(rp, 'rb') as fh:
                        fh.seek(off)
                        data = fh.read()
                    cut = data.rfind(b'\n') + 1
                    off += cut
                    for ln in data[:cut].decode('utf-8', 'replace').split('\n'):
                        r = ln.strip().split(',')   # the game writes CRLF
                        if len(r) >= 4 and r[0] in tx and r[0] not in seen:
                            seen.add(r[0])
                            last = time.time()
                            if r[1] == 'ok':
                                JQ['ok' if str(expect.get(r[0])) == r[3] else 'different'] += 1
                            else:
                                JQ['failed'] += 1
                    JQ['confirmed'] = JQ['ok'] + JQ['different'] + JQ['failed']
                waited = time.time() - last
                JQ['msg'] = ('Package %d of %d: ' % (ci, len(chunks))) + ('waiting for the game … is the Master League loaded and F7 pressed? (%d s)' % waited if waited > 45 else 'the game is writing …')
            if len(seen) >= len(tx):
                _compact(tx)
                _jwrite(pids, writes, srcs)
                JQ['players_done'] += len(pids)
            else:   # cancelled: take back what the game has not answered yet
                _compact(tx)
                _jwrite([p for p in pids if all(ln.split(',', 1)[0] in seen for ln in lines if ln.split(',')[1] == str(p))], writes, srcs)
        JQ.update(state='cancelled' if JQ.get('cancel') else 'done', msg='Cancelled.' if JQ.get('cancel') else 'All packages are written.', ended=time.time())
    except Exception as ex:
        JQ.update(state='error', msg='Stopped: %s' % ex, ended=time.time())


def ml_write(writes, srcs, profs=None):
    """The running Master League (the way Gaffer does it for single players): 'set' commands in growth.csv of the bridge, the Lua module GrowthBridge writes them into the memory
    of the game while a career runs (F7 once). Only values that differ from the running game are sent. Big writes go package by package (ML_CHUNK values), see _feed."""
    global JQ
    live = live_attrs()
    tag = 'fldb%d' % int(time.time())
    per, want = {}, {}
    xf = {pid: ml_fields(pr) for pid, pr in (profs or {}).items()}   # profile fields: only players that are in the running game
    for pid in set(writes) | set(xf):
        cur = dict(live.get(pid) or M.pb.attrs(M.pb.index[pid]), **(live_x(pid) if pid in xf else {}))
        att = dict(writes.get(pid) or {}, **(xf.get(pid) if cur.get('Style') is not None else {}))
        want[pid] = {a: v for a, v in att.items() if cur.get(a) != v}
        L = ['%s-%d-%s,%d,%s,set,%d' % (tag, pid, a, pid, a, v) for a, v in want[pid].items()]
        if L:
            per[pid] = L
    n = sum(len(L) for L in per.values())
    if not n:
        return dict(ok=True, written=0, lines=0, msg='The running game already has these values.')
    ML_TAGS[tag] = {(pid, a): v for pid, att in want.items() for a, v in att.items()}
    if n <= ML_CHUNK:
        for pid, att in writes.items():
            PEND[pid] = (time.time(), dict(att))
        with open(_bridge('growth.csv'), 'a', encoding='utf-8', newline='\n') as fh:
            fh.write('\n'.join(ln for L in per.values() for ln in L) + '\n')
        _jwrite(list(writes), writes, srcs)
        return dict(ok=True, written=len(writes), lines=n, tag=tag, backup='growth.csv (bridge)')
    if JQ.get('state') == 'running':
        return dict(ok=False, msg='A big write is still running (%s of %s values confirmed). Wait for it or cancel it first.' % (format(JQ['confirmed'], ','), format(JQ['total'], ',')))
    chunks, cur_p, cur_l = [], [], []
    for pid, L in per.items():
        if cur_l and len(cur_l) + len(L) > ML_CHUNK:
            chunks.append((cur_p, cur_l))
            cur_p, cur_l = [], []
        cur_p.append(pid)
        cur_l += L
    if cur_l:
        chunks.append((cur_p, cur_l))
    expect = {'%s-%d-%s' % (tag, pid, a): v for (pid, a), v in ML_TAGS[tag].items()}
    JQ = dict(state='running', tag=tag, total=n, sent=0, confirmed=0, ok=0, different=0, failed=0, chunk=0, chunks=len(chunks), players=len(per), players_done=0, started=time.time(), msg='Starting …')
    threading.Thread(target=_feed, args=(tag, chunks, writes, srcs, expect), daemon=True).start()
    return dict(ok=True, written=len(writes), lines=n, tag=tag, chunked=True, chunks=len(chunks), backup='growth.csv (bridge), in %d packages' % len(chunks))


def ml_status(tag):
    """what the game reports for the commands of one write (growth-result.csv of the bridge): confirmed values against the values that were sent"""
    if JQ.get('tag') == tag:   # a big write: the feeder counts
        return dict(ok=True, total=JQ['total'], confirmed=JQ['ok'], different=JQ['different'], failed=JQ['failed'], rows=[], game_running=True, job={k: v for k, v in JQ.items() if k != 'cancel'})
    exp = ML_TAGS.get(tag) or {}
    got = {}
    p = _bridge('growth-result.csv')
    if os.path.isfile(p):
        pre = tag + '-'
        with open(p, encoding='utf-8', errors='replace') as fh:
            for ln in fh:
                if ln.startswith(pre):
                    r = ln.rstrip('\n').split(',')
                    if len(r) >= 4:
                        m = r[0][len(pre):].split('-', 1)
                        if len(m) == 2 and m[0].isdigit():
                            got[(int(m[0]), m[1])] = (r[1], r[2], r[3])
    rows, ok, bad = [], 0, 0
    for (pid, a), v in exp.items():
        g = got.get((pid, a))
        if g and g[0] == 'ok':
            if str(v) == g[2]:
                ok += 1
            else:
                bad += 1
        if len(exp) <= 60 or (g and g[0] == 'ok' and str(v) != g[2]):
            rows.append(dict(pid=pid, attr=a, expected=v, status=g[0] if g else 'waiting', old=g[1] if g else None, new=g[2] if g else None))
    other = sum(1 for g in got.values() if g[0] != 'ok')
    return dict(ok=True, total=len(exp), confirmed=ok, different=bad, failed=other, rows=rows[:80], game_running=bool(live_attrs()))


GUP = dict(t=0, ok=False)


def proxy(path, handler):
    """photos and club logos of Gaffer, when Gaffer runs (the page shows a placeholder otherwise)"""
    try:
        if not GUP['ok'] and time.time() - GUP['t'] < 30:
            raise OSError('Gaffer not reachable')
        with urllib.request.urlopen(CFG['gaffer'] + path, timeout=8) as r:
            GUP.update(t=time.time(), ok=True)
            b = r.read()
            handler.send_response(200)
            handler.send_header('Content-Type', r.headers.get('Content-Type', 'image/png'))
            handler.send_header('Cache-Control', 'max-age=3600')
            handler.send_header('Content-Length', str(len(b)))
            handler.end_headers()
            handler.wfile.write(b)
    except Exception:
        GUP.update(t=time.time(), ok=False)
        handler.send_response(404)
        handler.send_header('Content-Length', '0')
        handler.end_headers()


def fs_list(path, kind=''):
    """for the folder picker of the page: the sub folders of a folder (the server runs on your own computer); path '' = the start points (drives on Windows)"""
    path = os.path.expanduser(str(path or '').strip().strip('"'))
    if not path:
        if os.name == 'nt':
            roots = [d + ':\\' for d in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if os.path.isdir(d + ':\\')]
        else:
            roots = ['/'] + [os.path.join('/mnt', d) for d in sorted(os.listdir('/mnt'))] if os.path.isdir('/mnt') else ['/']
            roots += [os.path.join('/media', d) for d in sorted(os.listdir('/media'))] if os.path.isdir('/media') else []
        return dict(ok=True, path='', parent=None, home=os.path.expanduser('~'), dirs=[dict(name=r, path=r, player=False) for r in roots], found=None)
    if os.path.isfile(path):
        path = os.path.dirname(path)
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        return dict(ok=False, msg='This folder does not exist.')
    dirs = []
    try:
        for n in sorted(os.listdir(path), key=str.lower):
            f = os.path.join(path, n)
            if os.path.isdir(f) and not n.startswith('.'):
                dirs.append(dict(name=n, path=f, player=os.path.isfile(os.path.join(f, 'growth.csv')) if kind == 'bridge' else bool(resolve_pesdb(f))))
    except OSError as ex:
        return dict(ok=False, msg='Cannot read this folder: %s' % ex)
    par = os.path.dirname(path)
    return dict(ok=True, path=path, parent=par if par != path else '', home=os.path.expanduser('~'), dirs=dirs, found=(path if os.path.isfile(os.path.join(path, 'growth.csv')) else None) if kind == 'bridge' else resolve_pesdb(path))


def find_bridge():
    """the bridge folder of Gaffer next to the database: .../SiderAddons/content/ml-immersion/bridge"""
    p = os.path.abspath(CFG['pesdb'] or '.')
    while True:
        c = os.path.join(p, 'content', 'ml-immersion', 'bridge')
        if os.path.isdir(c):
            return c
        q = os.path.dirname(p)
        if q == p:
            return ''
        p = q


def bridge_dir():
    return SET.get('bridge') or find_bridge()


def settings_view():
    r = resolve_pesdb(SET.get('dbpath'))
    td = target_date()
    br = bridge_dir()
    gd = gaffer_date() if SET['mode'] == 'ml' else None
    return dict(ok=True, mode=SET['mode'], dbpath=SET.get('dbpath'), pesdb=r, db_ok=bool(r), loaded=M is not None, date=SET.get('date') or '', data_dir=DATA,
                modules=modules_dir(), module=MOD['state'], bridge=br, bridge_ok=bool(br and os.path.isfile(os.path.join(br, 'growth.csv'))), gaffer_date=('%02d.%02d.%d' % gd[::-1]) if gd else None,
                target='%02d.%02d.%d' % td[::-1], base='01.09.2026', months=months(), players=M.pb.n if M else 0, live=len(live_attrs()) if SET['mode'] == 'ml' else 0)


def settings_set(body):
    ch_db = False
    with LOCK:
        if body.get('mode') in ('db', 'ml'):
            SET['mode'] = body['mode']
        if 'bridge' in body:
            b = os.path.expanduser(str(body['bridge'] or '').strip().strip('"'))
            if b and not os.path.isdir(b):
                return dict(ok=False, msg='This bridge folder does not exist.')
            SET['bridge'] = b
        if 'modules' in body:
            m = os.path.expanduser(str(body['modules'] or '').strip().strip('"'))
            if m and not os.path.isdir(m):
                return dict(ok=False, msg='This modules folder does not exist.')
            SET['modules'] = m
        if 'date' in body:
            SET['date'] = str(body['date'] or '')
        if body.get('dbpath') and body['dbpath'] != SET.get('dbpath'):
            r = resolve_pesdb(body['dbpath'])
            if not r:
                return dict(ok=False, msg='No Player.bin found there. Choose the folder that contains Player.bin (the pesdb folder, or a folder above it), or the Player.bin file itself.')
            SET['dbpath'], CFG['pesdb'], ch_db = body['dbpath'], r, True
        os.makedirs(DATA, exist_ok=True)
        json.dump(SET, open(SET_FILE, 'w'))
        CFG['journal'] = journal_path()
        if SET['mode'] == 'ml':
            sync_module()
    if ch_db:
        load()
    GDATE['key'] = None
    MATCH.clear()
    return settings_view()


def backups():
    d = CFG['backups']
    return [dict(file=f, size=os.path.getsize(os.path.join(d, f)), when=time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(os.path.getmtime(os.path.join(d, f)))))
            for f in sorted(os.listdir(d), reverse=True)] if os.path.isdir(d) else []


def restore(body):
    f = os.path.join(CFG['backups'], os.path.basename(str(body.get('file'))))
    if not os.path.isfile(f):
        raise ValueError('Backup not found')
    with LOCK:
        plbin.PlayerBin(f)   # must be readable
        backup()
        shutil.copy2(f, os.path.join(CFG['pesdb'], 'Player.bin'))
        load()
    return dict(ok=True)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send_json(self, o, code=200):
        b = json.dumps(o).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(b)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(b)

    def host_ok(self):
        h = (self.headers.get('Host') or '').rsplit(':', 1)[0].strip('[]').lower()
        return h in ('127.0.0.1', 'localhost', '::1')

    def do_GET(self):
        if not self.host_ok():
            self.send_json(dict(ok=False, error='forbidden'), 403)
            return
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        try:
            if M is None and u.path not in ('/', '/index.html', '/api/init', '/api/settings'):
                self.send_json(dict(ok=False, error='Choose the folder with Player.bin first.'))
                return
            if u.path in ('/', '/index.html'):
                b = open(os.path.join(HERE, 'static', 'index.html'), 'rb').read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(b)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(b)
            elif u.path == '/api/init':
                self.send_json(dict(ok=True, pesdb=CFG['pesdb'], loaded=M is not None, players=M.pb.n if M else 0, ea=len(EA.rows), csv=os.path.basename(CFG['csv']),
                                    leagues=[dict(id=c, name=L['name'], n=len(L['teams'])) for c, L in sorted(M.leagues.items(), key=lambda kv: kv[1]['name'])] if M else [], backups=backups()))
            elif u.path == '/api/fs':
                self.send_json(fs_list((q.get('path') or [''])[0], (q.get('kind') or [''])[0]))
            elif u.path in ('/api/wiki/img', '/api/crest'):
                proxy(self.path, self)
            elif u.path == '/api/find':
                self.send_json(find((q.get('q') or [''])[0]))
            elif u.path == '/api/league':
                self.send_json(league_view(int(q['id'][0])))
            elif u.path == '/api/missing':
                self.send_json(missing(int(q['id'][0]) if q.get('id') else None, int((q.get('limit') or ['500'])[0])))
            elif u.path == '/api/prow':
                self.send_json(dict(ok=True, row=pl_row(int(q['pid'][0]), (q.get('youth') or ['1'])[0] != '0')))
            elif u.path == '/api/club':
                self.send_json(club_view(int(q['tid'][0]), (q.get('youth') or ['1'])[0] != '0'))
            elif u.path == '/api/search':
                self.send_json(dict(ok=True, items=[dict(id=x['id'], name=x['name'], club=x['club'], rating=x['rating'], pos=x['pos'], nation=x['nation']) for x in EA.search(q['q'][0], 14)]))
            elif u.path == '/api/candidates':
                self.send_json(dict(ok=True, items=candidates(int(q['pid'][0]), (q.get('q') or [None])[0])))
            elif u.path == '/api/fmcal':
                self.send_json(fmcal.view(CFG['fmcal']))
            elif u.path == '/api/settings':
                self.send_json(settings_view())
            elif u.path == '/api/ml/job':
                self.send_json(dict(ok=True, job={k: v for k, v in JQ.items() if k != 'cancel'}))
            elif u.path == '/api/stamp':
                live_attrs()
                self.send_json(dict(ok=True, dump=LIVE['mt'], mode=SET['mode']))
            elif u.path == '/api/ml/status':
                self.send_json(ml_status(q['tag'][0]))
            elif u.path == '/api/job':
                self.send_json(dict(ok=True, **JOB))
            elif u.path == '/api/backups':
                self.send_json(dict(ok=True, items=backups()))
            else:
                self.send_json(dict(ok=False, error='not found'), 404)
        except Exception as ex:
            self.send_json(dict(ok=False, error=str(ex)), 200)

    def do_POST(self):
        if not self.host_ok():
            self.send_json(dict(ok=False, msg='forbidden'), 403)
            return
        n = int(self.headers.get('Content-Length') or 0)
        body = json.loads(self.rfile.read(n) or b'{}')
        try:
            if M is None and self.path != '/api/settings':
                self.send_json(dict(ok=False, msg='Choose the folder with Player.bin first.'))
                return
            if self.path == '/api/preview':
                self.send_json(preview(body))
            elif self.path == '/api/apply':
                self.send_json(apply(body))
            elif self.path == '/api/fmcal/add':
                rep, _ = fmcal.add(str(body.get('text') or ''), EA, CFG['fmcal'])
                self.send_json(dict(ok=True, report=rep, view=fmcal.view(CFG['fmcal'])))
            elif self.path == '/api/fmcal/clear':
                json.dump(dict(samples=[]), open(CFG['fmcal'], 'w'))
                self.send_json(dict(ok=True, view=fmcal.view(CFG['fmcal'])))
            elif self.path == '/api/bulk':
                if JOB.get('state') == 'running':
                    self.send_json(dict(ok=False, msg='A run is active.'))
                else:
                    threading.Thread(target=bulk_job, args=(body.get('rest', 'scale'), body.get('youth', True), bool(body.get('dry', True)), body.get('profile', True), body.get('skills', 'off'), bool(body.get('psboost'))), daemon=True).start()
                    time.sleep(0.2)
                    self.send_json(dict(ok=True))
            elif self.path == '/api/settings':
                self.send_json(settings_set(body))
            elif self.path == '/api/ml/cancel':
                JQ['cancel'] = True
                self.send_json(dict(ok=True))
            elif self.path == '/api/unassign':
                assign_set(int(body['pid']), None)
                self.send_json(dict(ok=True))
            elif self.path == '/api/restore':
                self.send_json(restore(body))
            else:
                self.send_json(dict(ok=False, error='not found'), 404)
        except Exception as ex:
            self.send_json(dict(ok=False, msg=str(ex)), 200)


def main():
    global SET_FILE, DATA
    ap = argparse.ArgumentParser(description='FCFL - Stats Converter')
    ap.add_argument('--port', type=int, default=8790)
    ap.add_argument('--data-dir', help='where settings, backups and the original copy are kept (default: %s)' % DATA)
    ap.add_argument('--db', help='folder with Player.bin (or the file itself)')
    ap.add_argument('--csv', help='EA FC export (default: the one that comes with the tool)')
    ap.add_argument('--no-browser', action='store_true')
    ap.add_argument('--gaffer', help='address of Gaffer for the Master League mode (default: %s)' % CFG['gaffer'])
    a = ap.parse_args()
    if a.data_dir:
        DATA = os.path.abspath(a.data_dir)
        CFG.update(fmcal=os.path.join(DATA, 'fm_calib.json'), backups=os.path.join(DATA, 'backups'))
        SET_FILE = os.path.join(DATA, 'settings.json')
    if a.csv:
        CFG['csv'] = a.csv
    if a.gaffer:
        CFG['gaffer'] = a.gaffer
    os.makedirs(DATA, exist_ok=True)
    if not os.path.isfile(CFG['fmcal']):   # your own copy of the FM calibration, it grows with your samples
        shutil.copy2(os.path.join(HERE, 'data', 'fm_calib.json'), CFG['fmcal'])
    settings_load()
    if a.db:
        SET['dbpath'] = a.db
        settings_load()
    load()
    if SET['mode'] == 'ml':
        sync_module()
    url = 'http://127.0.0.1:%d/' % a.port
    print('FCFL - Stats Converter on %s  (%d EA FC players%s)' % (url, len(EA.rows), ', %d players in the database' % M.pb.n if M else ', no database chosen yet'), flush=True)
    try:
        srv = ThreadingHTTPServer(('127.0.0.1', a.port), H)
    except OSError:   # already running (second click on the start icon): open the page of the running one
        try:
            urllib.request.urlopen(url + 'api/settings', timeout=3).read()
        except Exception:
            print('Port %d is in use by something else; start with --port NUMBER.' % a.port)
            raise SystemExit(1)
        print('Already running: %s' % url)
        if not a.no_browser:
            import webbrowser
            webbrowser.open(url)
        return
    if not a.no_browser:
        import webbrowser
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    srv.serve_forever()


if __name__ == '__main__':
    main()
