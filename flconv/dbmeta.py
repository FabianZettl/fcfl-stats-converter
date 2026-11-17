"""What the tool needs to show: players (name, position, age, height) of Player.bin, the teams (Team.bin), their leagues (Competition/CompetitionEntry) and which team a player belongs to
(PlayerAssignment). Everything comes from the database folder itself. The original values of the players (before the first write of this tool) are kept in a copy of Player.bin
(see Meta.__init__): the conversion always starts from the original, so running it twice does not change the result."""
import json
import os
import re
import shutil
import struct
import zlib

import plbin

POS_NAMES = ['GK', 'CB', 'LB', 'RB', 'DMF', 'CMF', 'LMF', 'RMF', 'AMF', 'LWF', 'RWF', 'SS', 'CF']
_NOT_LEAGUE = re.compile(r'(CUP|CHAMPIONS|EUROPE_LEAGUE|WORLD|EURO$|COPA|ASIA|AFRICA|SUPER|UECL)')


def _unz(path):
    raw = open(path, 'rb').read()
    if raw[3:8] != b'WESYS':
        raise ValueError('Unknown format: %s' % path)
    return zlib.decompress(raw[16:])


def league_title(code):
    m = re.match(r'FL_(\d+)_LEAGUE', code)
    if m:
        return 'League %s' % m.group(1)
    m = re.match(r'([A-Z_]+?)_D(\d)_LEAGUE', code)
    if m:
        return '%s · Division %s' % (m.group(1).replace('_', ' ').title().replace('Us', 'USA').replace('Ksa', 'Saudi Arabia'), m.group(2))
    return code.replace('_', ' ').title()


class _Base:
    """attributes of the original Player.bin by player id"""
    def __init__(self, pb):
        self.pb = pb

    def get(self, pid, default=None):
        i = self.pb.index.get(pid)
        return self.pb.attrs(i) if i is not None else default


class Meta:
    def __init__(self, pesdb, orig_dir, plan_json=None):
        """pesdb: folder with Player.bin; orig_dir: where the copy of the original Player.bin is kept (made on first use)"""
        self.pesdb = pesdb
        self.pb = plbin.PlayerBin(os.path.join(pesdb, 'Player.bin'))
        os.makedirs(orig_dir, exist_ok=True)
        op = os.path.join(orig_dir, 'Player.bin.original')
        if not os.path.isfile(op):
            shutil.copy2(os.path.join(pesdb, 'Player.bin'), op)
        self.orig_path = op
        self.orig = plbin.PlayerBin(op)
        if self.orig.ids != self.pb.ids:   # another database in the same place: the copy does not fit
            shutil.copy2(os.path.join(pesdb, 'Player.bin'), op)
            self.orig = plbin.PlayerBin(op)
        pb = self.pb
        self.name = {p: pb.get_name(i, 'name') for i, p in enumerate(pb.ids)}
        self.short = {p: pb.get_name(i, 'shirt') for i, p in enumerate(pb.ids)}
        self.pos = {p: pb.position(i) for i, p in enumerate(pb.ids)}
        self.age = {p: pb.age(i) for i, p in enumerate(pb.ids)}
        self.height = {p: pb.height(i) for i, p in enumerate(pb.ids)}
        self.base_attrs = _Base(self.orig)
        self._teams()
        self._leagues(plan_json)
        self._assign()

    def _teams(self):
        tm = _unz(os.path.join(self.pesdb, 'Team.bin'))
        S = 1532
        self.team = {}
        for i in range(len(tm) // S):
            r = tm[i * S:(i + 1) * S]
            tid = struct.unpack_from('<I', r, 8)[0]
            nm = (r[368:438].split(b'\0')[0] or r[158:228].split(b'\0')[0]).decode('utf-8', 'replace')
            self.team[tid] = nm

    def _leagues(self, plan_json):
        c = _unz(os.path.join(self.pesdb, 'Competition.bin'))
        e = _unz(os.path.join(self.pesdb, 'CompetitionEntry.bin'))
        names = {}
        if plan_json and os.path.isfile(plan_json):
            try:
                for row in json.load(open(plan_json)).get('leagues', []):
                    if isinstance(row.get('cid'), int):
                        names[row['cid'] & 255] = row.get('name')
            except Exception:
                pass
        comp = {}
        for off in range(0, len(c), 36):
            code = c[off + 8:off + 36].split(b'\0')[0].decode('ascii', 'replace')
            cid = struct.unpack_from('>H', c, off + 4)[0] & 255
            if code.endswith('_LEAGUE') and not _NOT_LEAGUE.search(code):
                comp[cid] = names.get(cid) or league_title(code)
        mem = {}
        for off in range(0, len(e), 12):
            tid, _u, cid = struct.unpack_from('<III', e, off)
            if (cid & 255) in comp:
                mem.setdefault(cid & 255, set()).add(tid)
        self.leagues = {cid: dict(id=cid, name=comp[cid], teams=sorted(mem[cid], key=lambda t: self.team.get(t, ''))) for cid in comp if len(mem.get(cid, ())) >= 8}
        self.league_of = {t: cid for cid, L in self.leagues.items() for t in L['teams']}

    def _assign(self):
        pa = _unz(os.path.join(self.pesdb, 'PlayerAssignment.bin'))
        self.squad = {}   # team id -> [player ids]
        self.club_of = {}
        for i in range(len(pa) // 16):
            _x, pid, tid, _k = struct.unpack_from('<4I', pa, i * 16)
            self.squad.setdefault(tid, []).append(pid)
            if tid in self.league_of and pid not in self.club_of:
                self.club_of[pid] = tid

    def players_of(self, tid):
        return [p for p in self.squad.get(tid, []) if p in self.pb.index]
