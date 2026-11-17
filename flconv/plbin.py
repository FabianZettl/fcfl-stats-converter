"""Player.bin of the game database (livecpk/.../common/etc/pesdb): WESYS container (16 byte header, zlib) with 312 byte records.
The 25 attributes are 6 bit fields (+40, values 40..103), little endian bit order, at fixed bit offsets of the record. The layout was found by comparing the records
with the in-game table of the same database (players_base.bin, same player order): all 25 fields match 100%% on 33,193 players."""
import os
import shutil
import struct
import time
import zlib

REC = 312
# attribute -> bit offset inside the record
ATTR_BITS = {'OffensiveAwareness': 370, 'BallControl': 281, 'Dribbling': 352, 'TightPossession': 416, 'LowPass': 263, 'LoftedPass': 402, 'Finishing': 396, 'Heading': 288,
             'PlaceKicking': 250, 'Curl': 332, 'Speed': 306, 'Acceleration': 344, 'KickingPower': 358, 'Jump': 294, 'PhysicalContact': 390, 'Balance': 376, 'Stamina': 338,
             'DefensiveAwareness': 275, 'BallWinning': 312, 'Aggression': 384, 'GKAwareness': 326, 'GKCatching': 364, 'GKClearing': 269, 'GKReflexes': 320, 'GKReach': 300}
AB = list(ATTR_BITS)


class PlayerBin:
    def __init__(self, path):
        self.path = path
        raw = open(path, 'rb').read()
        if raw[3:8] != b'WESYS':
            raise ValueError('Not a WESYS file: %s' % path)
        self.head = raw[:16]
        self.data = bytearray(zlib.decompress(raw[16:]))
        if len(self.data) % REC:
            raise ValueError('Player.bin length is not a multiple of %d' % REC)
        self.n = len(self.data) // REC
        self.ids = [struct.unpack_from('<I', self.data, i * REC + 8)[0] for i in range(self.n)]
        self.index = {pid: i for i, pid in enumerate(self.ids)}
        self.orig = bytes(self.data)

    def get(self, i, attr):
        b = i * REC * 8 + ATTR_BITS[attr]
        o = b >> 3
        return (((self.data[o] | (self.data[o + 1] << 8)) >> (b & 7)) & 63) + 40

    def attrs(self, i):
        return {a: self.get(i, a) for a in ATTR_BITS}

    def set(self, i, attr, v):
        v = max(40, min(99, int(v))) - 40
        b = i * REC * 8 + ATTR_BITS[attr]
        o, s = b >> 3, b & 7
        w = self.data[o] | (self.data[o + 1] << 8)
        w = (w & ~(63 << s)) | (v << s)
        self.data[o], self.data[o + 1] = w & 255, (w >> 8) & 255

    def bits(self, i, off, w):
        b = i * REC * 8 + off
        o = b >> 3
        v = int.from_bytes(self.data[o:o + 4], 'little') >> (b & 7)
        return v & ((1 << w) - 1)

    def position(self, i):
        """0 GK ... 12 CF (the order of dbmeta.POS_NAMES); bit field found by comparing with the in-game table: 100 % of 33,193 players"""
        return self.bits(i, 434, 4)

    def age(self, i):
        """age in the year the database was made (6 bit field + 15)"""
        return self.bits(i, 408, 6) + 15

    def height(self, i):
        """cm (8 bit field + 100)"""
        return self.bits(i, 216, 8) + 100

    def set_bits(self, i, off, w, v):
        b = i * REC * 8 + off
        o = b >> 3
        cur = int.from_bytes(self.data[o:o + 4], 'little')
        mask = ((1 << w) - 1) << (b & 7)
        cur = (cur & ~mask) | ((int(v) << (b & 7)) & mask)
        self.data[o:o + 4] = cur.to_bytes(4, 'little')

    def set_height(self, i, cm):
        self.set_bits(i, 216, 8, max(100, min(355, int(cm))) - 100)

    def weight(self, i):
        """kg (7 bit field at bit 256, value + 30): found by comparing with the weights of the EA ratings page (correlation 0.83 on 2,500 players)"""
        return self.bits(i, 256, 7) + 30

    def set_weight(self, i, kg):
        self.set_bits(i, 256, 7, max(30, min(157, int(kg))) - 30)

    def foot(self, i):
        """'Right' / 'Left' (1 bit at bit 514, 97.6 % agreement with the FIFPlay data on 5,489 players)"""
        return 'Left' if self.bits(i, 514, 1) else 'Right'

    def set_foot(self, i, foot):
        self.set_bits(i, 514, 1, 1 if str(foot).lower().startswith('l') else 0)

    def changed(self):
        """indices of the records that differ from the file as it was read"""
        d, o = self.data, self.orig
        return [i for i in range(self.n) if d[i * REC:(i + 1) * REC] != o[i * REC:(i + 1) * REC]]

    def pack(self):
        z = zlib.compress(bytes(self.data), 9)
        return self.head[:8] + struct.pack('<II', len(z), len(self.data)) + z

    def save(self, path=None):
        path = path or self.path
        tmp = path + '.tmp'
        open(tmp, 'wb').write(self.pack())
        os.replace(tmp, path)
        self.orig = bytes(self.data)


NAME_OFFS = {'name': (68, 251), 'shirt': (129,), 'nshirt': (190,)}   # 61 byte UTF-8 fields: name (twice), shirt name, shirt name of the national team
NAME_LEN = 61


def _set_name(data, i, field, text):
    b = str(text).encode('utf-8')[:NAME_LEN - 1]
    while True:   # do not cut inside a multi byte character
        try:
            b.decode('utf-8')
            break
        except UnicodeDecodeError:
            b = b[:-1]
    for off in NAME_OFFS[field]:
        o = i * REC + off
        data[o:o + NAME_LEN] = b + b'\0' * (NAME_LEN - len(b))


def get_name(data, i, field):
    o = i * REC + NAME_OFFS[field][0]
    return bytes(data[o:o + NAME_LEN]).split(b'\0')[0].decode('utf-8', 'replace')


PlayerBin.set_name = lambda self, i, field, text: _set_name(self.data, i, field, text)
PlayerBin.get_name = lambda self, i, field: get_name(self.data, i, field)



# --- skills, COM playing styles, playing style, weak foot, positions: bit offsets of Player.bin, found by matching every bit of the in-game table (whose layout is known) with the
# bit of Player.bin that has exactly the same values for 4,000 players (one single match for each)
SKILL_BITS = {"Scissors Feint": 519, "Flip Flap": 485, "Marseille Turn": 497, "Sombrero": 482, "Cut Behind & Turn": 528, "Scotch Move": 525, "Heading": 495, "Long Range Drive": 527, "Acrobatic Finishing": 524, "Heel Trick": 505, "First-time Shot": 511, "One-touch Pass": 507, "Weighted Pass": 484, "Pinpoint Crossing": 483, "Outside Curler": 493, "Low Lofted Pass": 488, "GK Low Punt": 490, "Long Throw": 521, "GK Long Throw": 522, "Gamesmanship": 491, "Man Marking": 504, "Track Back": 517, "Acrobatic Clear": 530, "Captaincy": 492, "Fighting Spirit": 486, "Penalty Specialist": 501, "Chip Shot Control": 506, "Step On Ball Control": 500, "Dipping Shot": 494, "Rising Shots": 499, "Interception": 503, "Double Touch": 523, "Cross Over Turn": 287, "Long Range Shooting": 518, "Through Passing": 487}
COM_BITS = {"Trickster": 489, "Mazing Run": 531, "Speeding Bullet": 526, "Incisive Run": 510, "Long Ball Expert": 529, "Early Cross": 447, "Long Ranger": 520}
STYLE_OFF, STYLE_W = 155, 5   # index in STYLES
STYLES = ['Balanced', 'Goal Poacher', 'Dummy Runner', 'Fox in the Box', 'Prolific Winger', 'Classic No. 10', 'Hole Player', 'Box-to-Box', 'Anchor Man', 'The Destroyer', 'Extra Frontman',
          'Offensive Full-back', 'Defensive Full-back', 'Target Man', 'Creative Playmaker', 'Build Up', 'Offensive Goalkeeper', 'Defensive Goalkeeper', 'Roaming Flank', 'Cross Specialist',
          'Orchestrator', 'Full-back Finisher']
WEAK_USE_OFF, WEAK_ACC_OFF = 454, 462   # 2 bit each, value + 1 (1..4)
POS_BITS = [[None, 351], [468, 469], [318, 319], [474, 475], [414, 415], [456, 457], [466, 467], [460, 461], [464, 465], [472, 473], [476, 477], [478, 479], [470, 471]]   # positions 0..12 (GK CB LB RB DMF CMF LMF RMF AMF LWF RWF SS CF): (low bit, high bit) of a 0..2 rating (2 = natural)


def _pb_skills(self, i):
    return {n for n, o in SKILL_BITS.items() if self.bits(i, o, 1)}


def _pb_set_skills(self, i, names):
    for n, o in SKILL_BITS.items():
        self.set_bits(i, o, 1, 1 if n in names else 0)


def _pb_com(self, i):
    return {n for n, o in COM_BITS.items() if self.bits(i, o, 1)}


def _pb_set_com(self, i, names):
    for n, o in COM_BITS.items():
        self.set_bits(i, o, 1, 1 if n in names else 0)


def _pb_style(self, i):
    v = self.bits(i, STYLE_OFF, STYLE_W)
    return STYLES[v] if v < len(STYLES) else None


def _pb_set_style(self, i, name):
    self.set_bits(i, STYLE_OFF, STYLE_W, STYLES.index(name))


def _pb_positions(self, i):
    return [(self.bits(i, lo, 1) if lo is not None else 0) + 2 * self.bits(i, hi, 1) for lo, hi in POS_BITS]


PlayerBin.skills, PlayerBin.set_skills = _pb_skills, _pb_set_skills
PlayerBin.com_styles, PlayerBin.set_com_styles = _pb_com, _pb_set_com
PlayerBin.playing_style, PlayerBin.set_playing_style = _pb_style, _pb_set_style
PlayerBin.weak_foot_use = lambda self, i: self.bits(i, WEAK_USE_OFF, 2) + 1
PlayerBin.weak_foot_acc = lambda self, i: self.bits(i, WEAK_ACC_OFF, 2) + 1
PlayerBin.positions = _pb_positions


def verify(path, expected_ids, expected, before):
    """Reads the file again and checks that exactly the expected attributes (and names) changed. expected: {pid: {'attrs': {...}, 'names': {...}, 'prof': {height, weight, foot}}} -> list of problems"""
    pb = PlayerBin(path)
    bad = []
    if pb.ids != expected_ids:
        return ['player ids differ']
    allowed = {pb.index[pid]: e for pid, e in expected.items()}
    for i in range(pb.n):
        a, b = before[i * REC:(i + 1) * REC], pb.data[i * REC:(i + 1) * REC]
        if a == b:
            continue
        e = allowed.get(i)
        if e is None:
            bad.append('record %d changed unexpectedly' % i)
            continue
        tmp = PlayerBin.__new__(PlayerBin)
        tmp.data = bytearray(a)
        for k, v in (e.get('attrs') or {}).items():
            PlayerBin.set(tmp, 0, k, v)
        for k, v in (e.get('names') or {}).items():
            _set_name(tmp.data, 0, k, v)
        for k, v in (e.get('prof') or {}).items():
            getattr(PlayerBin, 'set_' + k)(tmp, 0, v)
        if bytes(tmp.data) != bytes(b):
            bad.append('record %d: more changed than expected' % i)
    return bad
