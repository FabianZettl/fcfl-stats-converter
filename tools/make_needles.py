"""Search needles for tools/fcfl_livepatch.lua (F10): known values of one team, to find how the game keeps PlayerAssignment / Tactics / TacticsFormation / Team in memory.
Usage: make_needles.py DBFOLDER TEAM_ID OUTFILE   (line: name hexbytes)"""
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv'))
import dbmeta

db, tid, outp = sys.argv[1], int(sys.argv[2]), sys.argv[3]
M = dbmeta.Meta(db, tempfile.mkdtemp())
fm = M.formation[tid]
sq = sorted((M.lineup[(tid, p)][0], p) for p in M.squad[tid] if (tid, p) in M.lineup)
nodes = {
    'fm_codes': bytes(c for c, _, _ in fm),
    'fm_depth': bytes(d for _, d, _ in fm),
    'fm_width': bytes(w for _, _, w in fm),
    'fm_triples': b''.join(bytes(x) for x in fm[:4]),
    'squad_by_slot4': b''.join(struct.pack('<I', p) for _, p in sq[:4]),
    'squad_by_slot11': b''.join(struct.pack('<I', p) for _, p in sq[:11]),
    'squad_file_order4': b''.join(struct.pack('<I', p) for p in M.squad[tid][:4]),
    'team_name': M.team[tid].encode() + b'\0',
}
open(outp, 'w').write(''.join('%s %s\n' % (k, v.hex()) for k, v in nodes.items()))
print(M.team[tid], {k: len(v) for k, v in nodes.items()})
