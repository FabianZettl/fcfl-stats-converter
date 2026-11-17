"""Development of a player between the date of the values (01.09.2026) and another date: young players grow, old players decline, each attribute group at its own age
(physical early, technique later, mental and defensive last, keepers three years later); better young players grow faster, every player has his own pace (+-25 %),
the rounding is spread by a per-player/per-attribute dither so that two players of the same age do not get the same numbers."""
import hashlib
import math

BASE = (2026, 9, 1)
# yearly change per age: (physical, technical, mental)
CURVE = {16: (4.5, 4.0, 3.5), 17: (4.0, 3.8, 3.4), 18: (3.5, 3.4, 3.0), 19: (3.0, 3.0, 2.7), 20: (2.4, 2.6, 2.4), 21: (1.8, 2.1, 2.1), 22: (1.2, 1.7, 1.8), 23: (0.7, 1.3, 1.5),
         24: (0.3, 1.0, 1.2), 25: (0.0, 0.7, 1.0), 26: (-0.2, 0.4, 0.8), 27: (-0.5, 0.2, 0.6), 28: (-0.9, 0.0, 0.4), 29: (-1.3, -0.2, 0.2), 30: (-1.7, -0.5, 0.0),
         31: (-2.1, -0.9, -0.2), 32: (-2.5, -1.3, -0.5), 33: (-2.9, -1.7, -0.9), 34: (-3.3, -2.1, -1.3), 35: (-3.7, -2.5, -1.7)}
GROUP = {'Speed': 0, 'Acceleration': 0, 'Stamina': 0, 'Jump': 0, 'Balance': 0,
         'BallControl': 1, 'Dribbling': 1, 'TightPossession': 1, 'LowPass': 1, 'LoftedPass': 1, 'Finishing': 1, 'Curl': 1, 'PlaceKicking': 1, 'KickingPower': 1, 'Heading': 1,
         'OffensiveAwareness': 2, 'DefensiveAwareness': 2, 'BallWinning': 2, 'Aggression': 2, 'PhysicalContact': 2,
         'GKAwareness': 2, 'GKCatching': 2, 'GKClearing': 2, 'GKReflexes': 2, 'GKReach': 2}


def months_between(a, b):
    """a, b: (year, month, day) -> months (fractional)"""
    return (b[0] - a[0]) * 12 + (b[1] - a[1]) + (b[2] - a[2]) / 30.0


def _u(pid, key):
    h = hashlib.md5(('%s|%s' % (pid, key)).encode()).digest()
    return int.from_bytes(h[:4], 'little') / 4294967296.0


def rate(age, grp, gk=False):
    a = age - (3 if gk else 0)
    a = max(16, min(35, a))
    lo, f = int(math.floor(a)), a - math.floor(a)
    hi = min(35, lo + 1)
    return CURVE[lo][grp] * (1 - f) + CURVE[hi][grp] * f


def shift(stats, pos, age, rating, months, pid, tw=1.7):
    """stats {attr: value}; age at the base date (float); months > 0 forward in time, < 0 back; tw: sum of the positive weights of the overall model of the position (the curve is the
    change of the OVERALL per year, an attribute moves by that divided by tw). -> new stats"""
    if not months:
        return dict(stats)
    gk = pos == 0
    pace = 0.75 + 0.5 * _u(pid, 'pace')   # this player grows / declines 25 % slower or faster
    out = {}
    for a, v in stats.items():
        if not gk and a.startswith('GK'):
            out[a] = v   # a field player keeps his keeper values
            continue
        grp = GROUP.get(a, 2)
        # the age moves along: integrate in steps of one month
        d, t = 0.0, 0.0
        step = 1.0 if months > 0 else -1.0
        n = int(abs(months))
        rest = abs(months) - n
        for k in range(n + 1):
            w = 1.0 if k < n else rest
            if w <= 0:
                break
            ag = age + t / 12.0
            r = rate(ag, grp, gk)
            if r > 0 and age < 26:
                r *= max(0.6, min(1.4, 0.6 + (rating - 60) / 25.0))   # a good young player has more potential
            d += step * r / 12.0 * w
            t += step * w
        d *= pace / tw
        x = v + d
        base = math.floor(x)
        v2 = base + (1 if _u(pid, a) < x - base else 0)   # dither
        out[a] = max(40, min(99, int(v2)))
    return out


if __name__ == '__main__':
    s = {a: 70 for a in GROUP}
    y = shift(s, 5, 18.0, 75, 12, 1)
    o = shift(s, 5, 33.0, 75, 12, 2)
    assert sum(y.values()) > sum(s.values()) + 20 and sum(o.values()) < sum(s.values()) - 15, (sum(y.values()), sum(o.values()))
    assert shift(s, 5, 25, 70, 0, 3) == s
    # forward and back about cancel
    f = shift(s, 5, 22.0, 70, 6, 4)
    b = shift(f, 5, 22.5, 70, -6, 4)
    assert abs(sum(b.values()) - sum(s.values())) < 25
    assert shift(s, 0, 33.0, 75, 12, 5)['GKAwareness'] >= shift(s, 5, 33.0, 75, 12, 5)['GKAwareness'] - 2
    print('ok')
