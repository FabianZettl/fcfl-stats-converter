"""Patch file for the team objects of the running game (tools/fcfl_livepatch.lua, F12): squad order, shirt numbers and the two formations of the given teams, read from the database files.
Object of team rank r (order of Team.bin) = base + r*1680: 40 x (pid u32, u32) from +0, 40 x u16 shirt numbers from +330, formation 1 and 2 (3 sets x (11 codes + 11 x depth,width) = 99 bytes) from +784 and +944.
The base is found by the module from a team that is NOT in the patch ("LOC" line: its first formation). Usage: team_patch_make.py DBFOLDER OUT TEAMID [TEAMID ...] [--swap=1:2,9:11]
--swap=a:b,... swaps the squad entries a and b (0 = GK, 0..10 = starting eleven) of the FIRST team, with their shirt numbers."""
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv'))
import dbmeta

args = [a for a in sys.argv[1:] if not a.startswith('--')]
db, outp, ids = args[0], args[1], [int(x) for x in args[2:]]
M = dbmeta.Meta(db, tempfile.mkdtemp())
rank = {t: i for i, t in enumerate(sorted(M.team))}
t_raw, f_raw = dbmeta._unz(os.path.join(db, 'Tactics.bin')), dbmeta._unz(os.path.join(db, 'TacticsFormation.bin'))
kens = {}
for o in range(0, len(t_raw), 12):
    k, tid, _g = struct.unpack_from('<III', t_raw, o)
    kens.setdefault(tid, []).append(k)
F = {}
for o in range(0, len(f_raw), 12):
    k, c, d, q, pl = struct.unpack_from('<IIBBH', f_raw, o)
    F.setdefault(k, {}).setdefault(pl >> 4, {})[pl & 15] = (c, d, q)


def block(k):
    out = b''
    for s in range(3):
        v = F[k][s]
        out += bytes(v[i][0] for i in range(11)) + b''.join(bytes((v[i][1], v[i][2])) for i in range(11))
    return out


lines = []
# locator: a team that is not patched and whose first formation is unique among all formations
cnt = {}
for tid, ks in kens.items():
    for k in ks:
        if k in F:
            cnt[block(k)] = cnt.get(block(k), 0) + 1
loc = next(t for t in sorted(kens) if t not in ids and kens[t][0] in F and cnt[block(kens[t][0])] == 1)
lines.append('LOC %d %s' % (rank[loc], block(kens[loc][0]).hex()))
for n, tid in enumerate(ids):
    sq = sorted((M.lineup[(tid, p)][0], p) for p in M.squad[tid] if (tid, p) in M.lineup)
    pids = [p for _, p in sq][:40]
    nums = [M.lineup[(tid, p)][1] for p in pids]
    if n == 0:
        for a in sys.argv:
            if a.startswith('--swap='):
                for pair in a[7:].split(','):
                    x, y = map(int, pair.split(':'))
                    pids[x], pids[y] = pids[y], pids[x]
                    nums[x], nums[y] = nums[y], nums[x]
    lines.append('T %d %s' % (rank[tid], ' '.join(map(str, pids))))
    lines.append('N %d %s' % (rank[tid], ' '.join(map(str, nums))))
    for i, k in enumerate(kens.get(tid, [])[:2]):
        if k in F:
            lines.append('F %d %d %s' % (rank[tid], i + 1, block(k).hex()))
open(outp, 'w').write('\n'.join(lines) + '\n')
print('locator team', loc, M.team[loc], '| patched', [M.team[t] for t in ids], '|', len(lines), 'lines')
