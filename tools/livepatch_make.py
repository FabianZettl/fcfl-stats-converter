"""Patch file for tools/fcfl_livepatch.lua: the attributes that differ between two Player.bin files (old = what the running game loaded, new = the file now).
Line: pid byte_offset bit_shift bit_width old new, offsets of the 380 byte in-game block (dbmeta._F7). Usage: livepatch_make.py OLD NEW OUT"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv'))
import dbmeta
import plbin

old, new = plbin.PlayerBin(sys.argv[1]), plbin.PlayerBin(sys.argv[2])
rows = []
for pid, j in new.index.items():
    i = old.index.get(pid)
    if i is None:
        continue
    for a, (off, sh) in dbmeta._F7.items():
        o, n = old.get(i, a), new.get(j, a)
        if o != n:
            rows.append('%d %d %d 7 %d %d' % (pid, off, sh, o, n))
os.makedirs(os.path.dirname(os.path.abspath(sys.argv[3])), exist_ok=True)
open(sys.argv[3], 'w').write('\n'.join(rows) + '\n')
print(len(rows), 'lines,', len({r.split()[0] for r in rows}), 'players')
