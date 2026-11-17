"""Player.bin: read / write of the attributes, names and the bit fields, on a small made-up database (the real one is not part of this repository)."""
import os, struct, sys, tempfile, zlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv'))
import plbin

REC = plbin.REC
data = bytearray(REC * 3)
for i, pid in enumerate((100, 200, 300)):
    struct.pack_into('<I', data, i * REC + 8, pid)
z = zlib.compress(bytes(data))
path = os.path.join(tempfile.mkdtemp(), 'Player.bin')
open(path, 'wb').write(b'\x00\x00\x00WESYS\x00\x00\x00\x00\x00\x00\x00\x00\x00'[:8] + struct.pack('<II', len(z), len(data)) + z)

pb = plbin.PlayerBin(path)
assert pb.n == 3 and pb.ids == [100, 200, 300]
for a in plbin.AB:   # every attribute in its own bits: writing one must not touch another
    pb.set(1, a, 77)
    assert pb.get(1, a) == 77 and sum(pb.get(1, b) != 40 for b in plbin.AB) == 1
    pb.set(1, a, 40)
pb.set(1, 'Speed', 99)
pb.set(1, 'Speed', 120)   # limited to 99
assert pb.get(1, 'Speed') == 99 and pb.get(0, 'Speed') == 40 and pb.get(2, 'Speed') == 40
pb.set_name(2, 'name', 'Ben Winterburn')
pb.set_name(2, 'shirt', 'WINTERBURN')
assert pb.get_name(2, 'name') == 'Ben Winterburn' and pb.get_name(2, 'shirt') == 'WINTERBURN' and pb.get_name(0, 'name') == ''
pb.set_height(1, 195); pb.set_weight(1, 88); pb.set_foot(1, 'Left')
assert (pb.height(1), pb.weight(1), pb.foot(1)) == (195, 88, 'Left') and (pb.height(0), pb.weight(0), pb.foot(0)) == (100, 30, 'Right')
assert pb.get(1, 'Speed') == 99 and pb.get(1, 'Stamina') == 40   # the attributes are untouched
pb.set_foot(1, 'Right')
assert pb.foot(1) == 'Right' and pb.height(1) == 195
pb.save()
pb2 = plbin.PlayerBin(path)   # what was written is what is read again
assert pb2.get(1, 'Speed') == 99 and pb2.get_name(2, 'name') == 'Ben Winterburn' and pb2.changed() == []
print('ok')
