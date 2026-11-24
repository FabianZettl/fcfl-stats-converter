# Changelog

Releases of FCFL - Stats Converter, newest first. (`CHANGES.md` lists what is different from the PES Stats Converter this tool started from.)

## v0.7.0 - 2026-11-24

**FM list built in**
* The converter ships a list exported from FMInside (`flconv/data/fmdb/`, about 10,000 players, 5,800 with every attribute, 7,000 with position ratings). Your own newer lists go into the `fmdb` folder of the data folder and win by UID. The start page shows how many players the FM database has.
* **Positions come from FM first**: a player with position ratings in the list gets exactly those (natural = level 2, accomplished = 1, everything else 0). EA FC (alternative positions) and the values model are only the fallback. The second striker and the main position of the player are kept. A row that does not fit the player (a keeper called like a striker) is not used.
* The club view says **Found EAFC**, **Found FM** or **Found EAFC & FM** for every player.
* The player page shows which positions a player **gets and loses** when converted: white frame + for added, red dashed - for lost, and a line under the pitch.
* Converting a whole club or league now also takes players that EA FC does not have but the FM list does (they were skipped before).

**FM conversion calibrated to EA FC**
* The FM conversion is moved to the level of the EA FC conversion per attribute, from 4,500 players that are in both. Checked on players that were not used for the fit (20 % held out): field players 5.7 -> 4.3 points off the EA FC conversion, **keepers 5.6 -> 1.7**. The release carries a thinned set of 300 samples; the full set stays on your machine.

## v0.6.2 - 2026-11-24
* FM calibration from 2,900 players; the fit is worked out once per version of the calibration file and the cross validation is capped, so a preview stays fast.

## v0.6.1 - 2026-11-24
* A row of the FM list without all attributes (a list that only has names, club and ability) is no source of values.

## v0.6.0 - 2026-11-24
* **FM list** (FMInside export as CSV) as fallback source for players EA FC / SoFIFA does not have, and as filler for what EA FC does not give: **weak foot** (now written into `Player.bin`; mapping fitted on 51 players of the game), preferred foot and height.
* **Keepers** are calibrated apart from field players (own samples, own fit, the keeper model for the EA FC side).
* The FM calibration box takes the CSV list like page text.

## v0.5.0 - 2026-11-23
* **PESM-LivePatch**: changes written by the converter (or by PESM) reach the **running game** with F7 in the Sider overlay, no restart: the 25 attributes, line-ups, shirt numbers and formations. A first-start notice sets the Sider module up after your OK (copies it, adds one line to `sider.ini`, backup first). The overlay has a short guide in English.
* The club view draws the **formation of the database** (`Tactics.bin` / `TacticsFormation.bin`).
* Not live (restart needed): skills, COM styles, positions, names, new or moved players.

## v0.4.2 - 2026-11-21
* Windows / PyInstaller build: the exe stopped at start because a data folder was looked for one level too high; the league key is id + variant (Megapack).
* FMInside paste: label and value on two lines, `(preferred)` / `(key)`, any Unicode space or invisible mark are read; the error shows the text around "Crossing".
* Browser userscript (Tampermonkey) for SoFIFA / FMInside: a button sends the player page to the converter, which opens the player with the conversion ready.
* Sofascore: enter the club link when it is not found (remembered), clear message on 403 with a ten minute pause, one call per second.
* New screenshots: start page, club view with pitch, performance panel, Sofascore line-up.

## v0.4.1 - 2026-11-18
* The performance since the date of the data weights the development by time: over- or underperforming one's values changes how much of the age curve counts; the exact effect on the overall is shown.

## v0.4.0 - 2026-11-18
* Club view with pitch, Sofascore line-up and performance, height / weight / foot, the shipped `GrowthBridge.lua` for the Master League bridge, restart button.
