#!/usr/bin/env python3
"""FCFL - Stats Converter: converts EA FC (or FMInside / SoFIFA page) stats into the player database of Football Life (Player.bin), for one player, a club, a league or the whole
database, always with a backup and a check.   python3 server.py [--port 8790] [--data-dir DIR]"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import convert  # noqa: E402
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
SET = dict(dbpath='', date='')


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
    return os.path.join(DATA, 'converted-%s.json' % db_key())


def target_date():
    try:
        y, m, d = [int(x) for x in str(SET.get('date') or '').split('-')]
        return (y, m, d)
    except Exception:
        return timeshift.BASE


def cur_attrs(pid):
    return M.pb.attrs(M.pb.index[pid])


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
    return base_club(pid)


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


def journal():
    try:
        return json.load(open(CFG['journal']))
    except Exception:
        return {}


def ahash(att):
    return hashlib.md5(bytes(att[a] for a in plbin.AB)).hexdigest()[:12]


YF = dict(youth=True)   # setting of the last write (for the journal)


def sig_of(pid, src, youth):
    """what a conversion depends on: the EA FC player found, the youth bonus and the development period (in quarters). Pages (FMInside / SoFIFA) have no signature: only the values count."""
    if src not in ('EA FC', 'scaled'):
        return 'page'
    m = match(pid)
    sid = m['row']['id'] if src == 'EA FC' and m['status'] == 'ok' else src
    return hashlib.md5(('%s|%d|%d' % (sid, int(bool(youth)), int(months() // 3))).encode()).hexdigest()[:10]


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
    return M.players_of(tid)


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
    if not pot:   # no potential known: no bonus
        return 0
    gap = pot - rating
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
    want = body.get('target')   # a target typed by the user is the overall AFTER the development: the fit is moved by the difference (the development comes on top of the fit)
    tg = target
    for _ in range(4):
        p = convert.preview(M.pb, i, pos_of(pid), EA, row, fm, tg, CFG['fmcal'], cur=cur_attrs(pid), months=mo, age=age_base(pid), pid=pid, edits=body.get('edits'))
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
    choices = {int(k): v for k, v in (body.get('choices') or {}).items()}
    pids = [int(p) for p in body.get('pids') or []]
    for t in body.get('tids') or []:   # whole clubs: every player that is found unambiguously
        pids += [p for p in squad_of(int(t)) if match(p)['status'] == 'ok' and p not in pids]
    report, writes, srcs, names = [], {}, {}, {}
    for pid in pids:
        ch = choices.get(pid) or {}
        if not ch and not body.get('force') and (len(pids) > 1) and is_done(pid, body.get('youth', True))[0]:
            report.append(dict(pid=pid, name=M.name.get(pid), ok=False, msg='already converted', skipped=True))
            continue
        try:
            p = preview(dict(pid=pid, db_id=ch.get('db_id'), fm=ch.get('fm'), target=ch.get('target'), edits=ch.get('edits'), youth=body.get('youth', True)))
        except Exception as ex:
            p = dict(ok=False, msg=str(ex))
        if not p.get('ok'):
            report.append(dict(pid=pid, name=M.name.get(pid), ok=False, msg=p.get('msg'), ovr=cur_ovr(pid)))
            continue
        writes[pid] = p['final']
        srcs[pid] = p.get('source') or 'EA FC'
        want = dict(p.get('names_ea') or {}) if body.get('ea_names') else {}
        want.update(ch.get('names') or {})
        nm = {k: v for k, v in want.items() if k in plbin.NAME_OFFS and str(v).strip() and str(v) != p['names'].get(k)}
        if nm:
            names[pid] = nm
        report.append(dict(pid=pid, name=M.name.get(pid), ok=True, ovr_cur=p['ovr_cur'], ovr_new=p['ovr_new'], target=p['ovr_target']))
    for pid, ch in choices.items():   # only names changed (nothing else to convert)
        if pid not in writes and (ch.get('names')) and pid in M.pb.index:
            nm = {k: v for k, v in ch['names'].items() if k in plbin.NAME_OFFS and str(v).strip()}
            if nm:
                names[pid] = nm
    if dry or not (writes or names):
        return dict(ok=True, dry=True, report=report, written=0)
    r = commit(writes, srcs, names)
    return dict(r, report=report, dry=False)


def commit(writes, srcs, names=None):
    """-> dict(ok, written, backup)"""
    return write_all(writes, srcs, names or {})


JOB = dict(state='idle')


def bulk_job(rest, youth, dry):
    """The whole database: players that are in the EA FC export are converted, the others are kept or brought to the EA level (same profile, lower level)."""
    global JOB
    t0 = time.time()
    YF['youth'] = bool(youth)
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
            cur = pb.attrs(i)
            if unchanged(pid, cur, youth, jn):
                cnt['already'] += 1
                continue
            m = match(pid)
            if m['status'] == 'ok':
                p = preview(dict(pid=pid, youth=youth))
                if not p.get('ok'):
                    cnt['failed'] += 1
                    continue
                if p['final'] == cur:
                    cnt['already'] += 1
                    continue
                writes[pid], srcs[pid] = p['final'], 'EA FC'
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
                writes[pid], srcs[pid] = p['final'], 'scaled'
                chg_s.append(p['ovr_new'] - p['ovr_cur'])
                cnt['scaled'] += 1
            else:
                cnt['kept'] += 1
        res = dict(counts=dict(cnt), mean_converted=round(sum(chg_f) / len(chg_f), 2) if chg_f else 0, mean_scaled=round(sum(chg_s) / len(chg_s), 2) if chg_s else 0, months=mo)
        if dry or not writes:
            JOB = dict(state='done', dry=True, result=res, secs=round(time.time() - t0, 1))
            return
        JOB['done'] = pb.n
        JOB['phase'] = 'writing'
        r = commit(writes, srcs)
        JOB = dict(state='done' if r.get('ok') else 'error', dry=False, result=res, write=r, secs=round(time.time() - t0, 1))
    except Exception as ex:
        JOB = dict(state='error', msg=str(ex))


def write_all(writes, srcs, names):
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
            pb.save()
            exp = {pid: dict(attrs=writes.get(pid), names=names.get(pid)) for pid in set(writes) | set(names)}
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
        return dict(ok=True, written=len(writes), names=len(names), backup=bk)


def fs_list(path):
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
                dirs.append(dict(name=n, path=f, player=bool(resolve_pesdb(f))))
    except OSError as ex:
        return dict(ok=False, msg='Cannot read this folder: %s' % ex)
    par = os.path.dirname(path)
    return dict(ok=True, path=path, parent=par if par != path else '', home=os.path.expanduser('~'), dirs=dirs, found=resolve_pesdb(path))


def settings_view():
    r = resolve_pesdb(SET.get('dbpath'))
    td = target_date()
    return dict(ok=True, dbpath=SET.get('dbpath'), pesdb=r, db_ok=bool(r), loaded=M is not None, date=SET.get('date') or '', data_dir=DATA,
                target='%02d.%02d.%d' % td[::-1], base='01.09.2026', months=months(), players=M.pb.n if M else 0)


def settings_set(body):
    ch_db = False
    with LOCK:
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
    if ch_db:
        load()
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
                self.send_json(fs_list((q.get('path') or [''])[0]))
            elif u.path == '/api/league':
                self.send_json(league_view(int(q['id'][0])))
            elif u.path == '/api/missing':
                self.send_json(missing(int(q['id'][0]) if q.get('id') else None, int((q.get('limit') or ['500'])[0])))
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
                    threading.Thread(target=bulk_job, args=(body.get('rest', 'scale'), body.get('youth', True), bool(body.get('dry', True))), daemon=True).start()
                    time.sleep(0.2)
                    self.send_json(dict(ok=True))
            elif self.path == '/api/settings':
                self.send_json(settings_set(body))
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
    a = ap.parse_args()
    if a.data_dir:
        DATA = os.path.abspath(a.data_dir)
        CFG.update(fmcal=os.path.join(DATA, 'fm_calib.json'), backups=os.path.join(DATA, 'backups'))
        SET_FILE = os.path.join(DATA, 'settings.json')
    if a.csv:
        CFG['csv'] = a.csv
    os.makedirs(DATA, exist_ok=True)
    if not os.path.isfile(CFG['fmcal']):   # your own copy of the FM calibration, it grows with your samples
        shutil.copy2(os.path.join(HERE, 'data', 'fm_calib.json'), CFG['fmcal'])
    settings_load()
    if a.db:
        SET['dbpath'] = a.db
        settings_load()
    load()
    url = 'http://127.0.0.1:%d/' % a.port
    print('FCFL - Stats Converter on %s  (%d EA FC players%s)' % (url, len(EA.rows), ', %d players in the database' % M.pb.n if M else ', no database chosen yet'), flush=True)
    srv = ThreadingHTTPServer(('127.0.0.1', a.port), H)
    if not a.no_browser:
        import webbrowser
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    srv.serve_forever()


if __name__ == '__main__':
    main()
