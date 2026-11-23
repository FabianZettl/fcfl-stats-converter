import os
import struct
import sys
import tempfile
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'flconv'))
import livepatch  # noqa: E402


def wesys(path, data):
    z = zlib.compress(data)
    open(path, 'wb').write(b'\x00\x00\x01WESYS' + struct.pack('<II', len(z), len(data)) + z)


root = tempfile.mkdtemp()
db = os.path.join(root, 'SiderAddons', 'livecpk', 'x', 'common', 'etc', 'pesdb')
os.makedirs(db)
tids = [10, 20, 30, 40]
wesys(os.path.join(db, 'Team.bin'), b''.join(struct.pack('<II', 0, 0) + struct.pack('<I', t) + bytes(1532 - 12) for t in tids))
pa = b''
for t in tids:
    for slot in range(14):
        pa += struct.pack('<4I', 0, t * 100 + slot, t, (slot << 10) | (slot + 5))
wesys(os.path.join(db, 'PlayerAssignment.bin'), pa)
tac, fm = b'', b''
for n, t in enumerate(tids):
    for j in range(2):
        k = 1 + n * 2 + j
        tac += struct.pack('<III', k, t, 0)
        for s in range(3):
            for i in range(11):   # a different depth for every formation, so every first formation is unique
                fm += struct.pack('<IIBBH', k, 0 if i == 0 else 1, 3 + i + k, 50 + s, s * 16 + i)
wesys(os.path.join(db, 'Tactics.bin'), tac)
wesys(os.path.join(db, 'TacticsFormation.bin'), fm)

assert livepatch.live_dir(db) == os.path.join(root, 'SiderAddons', 'content', 'pesm-livepatch')
assert livepatch.live_dir('/nowhere/pesdb') is None

assert livepatch.add_team(db, 20)
teams = open(os.path.join(livepatch.live_dir(db), 'teams.txt')).read().split('\n')
assert teams[0].startswith('LOC ') and not teams[0].startswith('LOC 1 ')   # the locator is not team 20 (rank 1)
t_line = [l for l in teams if l.startswith('T 1 ')][0].split()
assert t_line[2:4] == ['2000', '2001'] and len(t_line) == 2 + 14   # squad of team 20 in line-up order
n_line = [l for l in teams if l.startswith('N 1 ')][0].split()
assert n_line[2:4] == ['6', '7']   # shirt numbers (k & 127) + 1
assert len([l for l in teams if l.startswith('F 1 ')]) == 2 and all(len(l.split()[3]) == 198 for l in teams if l.startswith('F '))

assert livepatch.add_team(db, 20) and livepatch.add_team(db, 30)   # again: the old entry is replaced, the other team is added
teams = open(os.path.join(livepatch.live_dir(db), 'teams.txt')).read().split('\n')
assert len([l for l in teams if l.startswith('T ')]) == 2
loc_rank = int(teams[0].split()[1])
assert loc_rank not in (1, 2)   # neither of the patched teams

assert livepatch.add_players(db, {7: {'Speed': 80, 'Stamina': 70}}, 1000) == 2
assert livepatch.add_players(db, {7: {'Speed': 81}, 8: {'Jump': 60}}, 1000) == 3   # a newer line replaces the older one
lines = open(os.path.join(livepatch.live_dir(db), 'players.txt')).read().split('\n')
assert lines[0] == 'COUNT 1000' and '7 20 7 7 81' in lines and '7 20 7 7 80' not in lines
assert livepatch.add_players(db, {}, 1000) is None
print('ok')
