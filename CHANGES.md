# What was changed compared with the PES Stats Converter

The conversion started as a Python port of the browser extension **PES Stats Converter** by moth1995
(<https://github.com/moth1995/pes_stats_converter_copy_addon>, GPL-3.0): the formulas of `converters/pes21.js`
(`fromFIFA17To23Player` for EA FC / SoFIFA values, `fromFMPlayer` with the per-position min/max tables of `pes21-stats-table.js` for Football Manager values).
That part lives in `flconv/lib/sofifa.py` and `flconv/lib/fmdata.py` and is GPL-3.0 as well. This tool is GPL-3.0, too.

What is different or new:

| Area | The original | This tool |
|---|---|---|
| Where the stats come from | scrapes the page you are on | reads a data file of EA FC ratings, or the **text of a SoFIFA / FMInside page** that you paste (Ctrl+A, Ctrl+C) |
| Where they go | shows a table to copy by hand | writes `Player.bin` directly, per player / club / league / whole database, with **backup, check and restore** |
| Scale of the game | none | one shift per attribute (`lib/poscal.py` SHIFT), fitted on 6,411 outfield players that are in the game and in the EA data |
| Position balance | none | small raise (0 to +3) of the eight attributes that count most for the position (BOOST); values are never lowered because of the position |
| Goalkeepers | same formulas | a keeper model per attribute (`lib/gkcal.py`, linear, fitted on 619 keepers), because the EA export has no field attributes for keepers |
| Overall | not considered | the attributes are fitted (at most ±8 per attribute) so that the overall of the game, computed with a model of its own overall formula (`lib/ovr_weights_fl27.json`, RMSE about 0.6), equals the EA FC overall |
| Youth | none | optional bonus +1…+3 when the potential is far above the rating, by age |
| Time | none | development from 01.09.2026 to a date of your choice (`timeshift.py`: yearly change per age and attribute group, personal pace, dither) |
| Football Manager values | fixed formulas | the same formulas plus a **calibration** from FMInside pages of players that are also in the EA data (per attribute none / shift / affine, chosen by leave-one-out); attributes that FMInside hides or shows as a range (e.g. Determination, Flair: "generated when you start a save") are estimated from related attributes |
| Finding the player | by hand | automatic: full name, then year of birth, height, nation, club, overall last; uncertain players are listed for you to decide, your choices are remembered |
| Repeatability | – | the conversion always starts from the original values; players that are already converted are marked and skipped unless something that matters has changed |
| Names | – | names and shirt names can be edited or taken from the EA data (common name where there is one) |

Everything in `flconv/lib/poscal.py`, `gkcal.py` and `ovr_weights_fl27.json` was fitted on one database (Football Life 2027) and is specific to it.
