"""Decompressed copies of database files for tools/fcfl_livepatch.lua (F8 probe): export_raw.py DBFOLDER OUTDIR"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv'))
import dbmeta

src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
for n in ('PlayerAssignment', 'Tactics', 'TacticsFormation', 'Team', 'Competition', 'CompetitionEntry'):
    d = dbmeta._unz(os.path.join(src, n + '.bin'))
    open(os.path.join(dst, n + '.raw'), 'wb').write(d)
    print(n, len(d))
