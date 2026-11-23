"""Patch files for the Sider module PESM-LivePatch (flconv/data/pesm-livepatch.lua): changes of Player.bin / PlayerAssignment / Tactics reach the RUNNING game when the
user presses F7 in the Sider overlay, no restart. Stdlib only, no other module of the converter needed (PESM uses a copy of this file).

Folder: <Sider>/content/pesm-livepatch/ (found from the database folder <Sider>/livecpk/<root>/common/etc/pesdb).
  players.txt  "COUNT n" + one line per field "pid byte_offset bit_shift bit_width new" (7 bit attribute fields of the 380 byte in-game block of a player; a newer
               line for the same field replaces the older one). The module only writes into the table with exactly n players.
  teams.txt    "LOC rank hex" (a team that is NOT patched, its first formation: the module finds the team array with it), then per team
               "T rank pid ..." (squad in line-up order), "N rank number ..." (shirt numbers), "F rank 1|2 hex" (formation 1 / 2, 3 sets x (11 position codes + 11 x depth, width)).
The game keeps the teams as an array of 1680 byte objects in the order of Team.bin: 40 x (pid, u32) at +0, 40 x u16 shirt numbers at +330, formations at +784 and +944
(found by comparing a memory dump with the files; checked in the game with line-up changes of two clubs).
The module is started with an empty folder at every start of the game (the game then loads the files as they are)."""
import os
import struct
import zlib

MAX_LINES = 400000   # more than this is a restart, not a live patch

# attribute -> (byte offset, bit shift) of its 7 bit field in the 380 byte block
F7 = {'OffensiveAwareness': (0x03, 0), 'BallControl': (0x06, 5), 'Dribbling': (0x05, 6), 'TightPossession': (0x08, 0), 'Finishing': (0x08, 7), 'LowPass': (0x09, 6),
      'LoftedPass': (0x0A, 5), 'Heading': (0x0C, 0), 'PlaceKicking': (0x0E, 5), 'Curl': (0x10, 0), 'Speed': (0x14, 7), 'Acceleration': (0x18, 7), 'KickingPower': (0x18, 0),
      'Jump': (0x19, 6), 'PhysicalContact': (0x15, 6), 'Balance': (0x16, 5), 'Stamina': (0x1A, 5), 'DefensiveAwareness': (0x04, 0), 'BallWinning': (0x0C, 7),
      'Aggression': (0x0D, 6), 'GKAwareness': (0x04, 7), 'GKCatching': (0x10, 7), 'GKClearing': (0x11, 6), 'GKReflexes': (0x12, 5), 'GKReach': (0x14, 0)}


def live_dir(pesdb):
    """<Sider>/content/pesm-livepatch, or None when the database folder is not below a livecpk folder"""
    p = os.path.abspath(pesdb)
    while os.path.basename(p) != 'livecpk':
        q = os.path.dirname(p)
        if q == p:
            return None
        p = q
    return os.path.join(os.path.dirname(p), 'content', 'pesm-livepatch')


def sider_dir(pesdb):
    d = live_dir(pesdb)
    return os.path.dirname(os.path.dirname(d)) if d else None


def _unz(path):
    raw = open(path, 'rb').read()
    if raw[3:8] != b'WESYS':
        raise ValueError('not a WESYS file: %s' % path)
    return zlib.decompress(raw[16:])


def _lines(path):
    try:
        return [l.rstrip('\n') for l in open(path, encoding='ascii')]
    except OSError:
        return []


def _save(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    open(tmp, 'w', encoding='ascii').write('\n'.join(lines) + '\n')
    os.replace(tmp, path)


def add_players(pesdb, changes, count):
    """changes {pid: {attribute: new value}} (only attributes that really changed) -> players.txt. Returns the number of field lines, or None when there is nothing to do or too much."""
    d = live_dir(pesdb)
    if not d:
        return None
    keep = {}
    for l in _lines(os.path.join(d, 'players.txt')):
        w = l.split()
        if len(w) == 5:
            keep[tuple(w[:3])] = l
    added = 0
    for pid, att in changes.items():
        for a, v in att.items():
            if a in F7:
                off, sh = F7[a]
                keep[(str(pid), str(off), str(sh))] = '%d %d %d 7 %d' % (pid, off, sh, v)
                added += 1
    if not added:
        return None
    if len(keep) > MAX_LINES:
        return -len(keep)
    _save(os.path.join(d, 'players.txt'), ['COUNT %d' % count] + list(keep.values()))
    return len(keep)


def _team_tables(pesdb):
    tm = _unz(os.path.join(pesdb, 'Team.bin'))
    rank = {struct.unpack_from('<I', tm, i * 1532 + 8)[0]: i for i in range(len(tm) // 1532)}
    t, f = _unz(os.path.join(pesdb, 'Tactics.bin')), _unz(os.path.join(pesdb, 'TacticsFormation.bin'))
    kens = {}
    for o in range(0, len(t) - 11, 12):
        k, tid, _g = struct.unpack_from('<III', t, o)
        kens.setdefault(tid, []).append(k)
    sets = {}
    for o in range(0, len(f) - 11, 12):
        k, c, d, q, pl = struct.unpack_from('<IIBBH', f, o)
        sets.setdefault(k, {}).setdefault(pl >> 4, {})[pl & 15] = (c, d, q)
    return rank, kens, sets


def _block(sets, k):
    s = sets.get(k)
    if not s or len(s) < 3 or any(len(s[i]) < 11 for i in range(3)):
        return None
    out = b''
    for i in range(3):
        v = s[i]
        out += bytes(v[j][0] for j in range(11)) + b''.join(bytes((v[j][1], v[j][2])) for j in range(11))
    return out


def add_team(pesdb, tid):
    """squad order, shirt numbers and formations of the team as they are in the database files now -> teams.txt (a newer entry replaces the older one of the same team)"""
    d = live_dir(pesdb)
    if not d:
        return False
    rank, kens, sets = _team_tables(pesdb)
    if tid not in rank:
        return False
    pa = _unz(os.path.join(pesdb, 'PlayerAssignment.bin'))
    sq = sorted(((k >> 10) & 63, pid, (k & 127) + 1) for _x, pid, t, k in struct.iter_unpack('<4I', pa) if t == tid)[:40]
    mine = ['T %d %s' % (rank[tid], ' '.join(str(p) for _, p, _ in sq)), 'N %d %s' % (rank[tid], ' '.join(str(n) for _, _, n in sq))]
    for i, k in enumerate(kens.get(tid, [])[:2]):
        b = _block(sets, k)
        if b:
            mine.append('F %d %d %s' % (rank[tid], i + 1, b.hex()))
    path = os.path.join(d, 'teams.txt')
    old = [l for l in _lines(path) if l[:1] in 'TNF' and l.split()[1] != str(rank[tid])]
    ranks = {int(l.split()[1]) for l in old} | {rank[tid]}
    # the locator: a team that is not patched and whose first formation is unique among all formations
    cnt = {}
    for ks in kens.values():
        for k in ks:
            b = _block(sets, k)
            if b:
                cnt[b] = cnt.get(b, 0) + 1
    loc = None
    for t2 in sorted(kens):
        b = _block(sets, kens[t2][0]) if t2 in rank and rank[t2] not in ranks else None
        if b and cnt[b] == 1:
            loc = 'LOC %d %s' % (rank[t2], b.hex())
            break
    if not loc:
        return False
    _save(path, [loc] + old + mine)
    return True
