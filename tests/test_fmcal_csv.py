"""FM list exported from FMInside (CSV, ';'): attributes 1-20 become the 0-99 of the page, so the existing FM conversion can use them."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv', 'lib'))
import fmcal  # noqa: E402
import sofifa  # noqa: E402

text = '﻿UID;Name;Club;Ability (0-99);Potential (0-99);Crossing;Acceleration;Off the Ball;Pace\n1;Kylian Mbappé;R. Madrid;96;99;13;20;x;19\n'
(name, club, raw), = fmcal.csv_items(text)
assert (name, club) == ('Kylian Mbappé', 'R. Madrid')
assert raw['Crossing'] == 65 and raw['Acceleration'] == 99 and raw['Pace'] == 95   # 5 x, at most 99
assert 'Off the Ball' not in raw and raw['overall'] == 96 and raw['potential'] == 99   # a value that is not a number is left out
print('ok')
