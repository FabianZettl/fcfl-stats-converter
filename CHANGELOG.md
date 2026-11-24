# Changelog

Releases of FCFL - Stats Converter, newest first. (`CHANGES.md` lists what is different from the PES Stats Converter this tool started from.)

## v0.7.4 - 2026-11-24
* **"Values are as of" can be changed** in the settings (it was fixed to 01.09.2026). Automatic = the date of the standard database or of the newest update that brought something (24.11.2026 now); a typed date overrides it, *Automatic* takes it back. The development to the write date and the age of the players count from it.
* FM list of 33,000 players (19,800 with every attribute); FM calibration from 10,400 players: field players 5.8 -> 4.3, keepers 5.7 -> 1.9.
* **Clear errors of the database are corrected** (age 2+ years off, wrong nation) when the player is certain (exactly this name at this club) and every source that speaks (EA FC, FM list) agrees; shown as 'Corrected ...' under the profile, written with the profile. Several German country names of the SoFIFA export were not translated (Tschechische Repub., Korea Republik, Bosnien-Herzegowina ...): fixed.
* **'Not the right player' also searches the FM list** (FM · name · club ...): the chosen FM player is remembered and converted from his FM values.
* **Only the date decides** which row of a SoFIFA update counts. v0.7.3 ranked the updates by the number in the file name; that number is only a counter of the scraper. The standard database (`sofifa-base-2026-11-24.csv`) has the state of 24 Nov 2026: an update dated before or on that day changes nothing and brings back no player the base lacks; a later one is laid over by date, whatever its number is.

## v0.7.3 - 2026-11-24
* **SoFIFA updates in the German export**: the numbers of an update carry the change ('70+1', '66-1'); they were not read, so 40-50 % of the rows of every update file were dropped. Now they are read.
* **The roster version decides before the date**: an update of an older roster never beats the standard database (roster 270008) and does not bring back a player that the newer roster does not have; a newer roster (270009 and on) wins. Ties between an update and the standard database go to the standard database.

## v0.7.2 - 2026-11-24
* **New standard database**: the German SoFIFA export of all players (`sofifa-base-2026-11-24.csv`, 19,594 players with potential, PlayStyles, growth profile, contracts, loans, values) replaces the EA FC 27 data set; updates follow as CSV files. Players converted from the old database show *convert again* once. An entry with holes in the attributes lets a complete FM row take over. The FM list has 22,000 players (14,900 with every attribute); the FM calibration (8,900 players, keepers apart) is redone against the new base: field players 5.7 -> 4.3, keepers 5.7 -> 1.9.
* **FM list assignment** uses the nationality of the player (Player.bin bit 233) next to club, age and height; the PES nation numbers are turned into country names from confident matches. 96 % of the 10,700 assigned players have the same nation in the FM list.
* **Players that only the FM list has** get the same player page as those of EA FC: full name, nation, date of birth, FM ability and potential instead of the EA FC rating, FM roles instead of the PlayStyles, weak foot with the FM value; the overall steps say "FM values".
* **Source tab on every player page**: *EA FC values* | *FM values* for a player that both sources have. The choice is remembered with the player (`source-<db>.json` in the data folder), so later runs over a club or the database keep it.
* **More players found in the FM list**: a different spelling is found by a shared word of the name together with club, age, height and nation (Neymar Jr / Neymar, Juan Cuadrado / Juan Guillermo Cuadrado); an uncertain EA FC match (the only entry with the name, but another age) lets the FM list take over instead of leaving the player out.
* `tools/fm_todo.py`: the rows of the list that still have no attributes and the players of the database that neither EA FC nor the list has, best first, for the scraper.
* **SoFIFA updates**: CSV files with new player values are loaded live (Tools > SoFIFA update, or the folder `ea-updates`); the date of an update is found (snapshot, else the file name, else the day of the file); for every player the newest row counts over earlier updates and the standard database, any number of updates. The start page lists them, the player page names the update, changed players show *convert again*. The German SoFIFA export (`sofifa-updates-270007-2026-11-24.csv`) is read as well: its date comes from the file name, its rating / potential / club / nation / positions / height / weight / foot / weak foot / 34 attribute values are laid over the standard database, the PlayStyles stay.
* **The new German SoFIFA base export** (`ea-base` folder): PlayStyles translated with the EA FC 27 table (36 names, `playstyles_de.json`), growth profile scales the youth bonus, emotion / acceleration type / work rates / contract / loan / value / wage on the player page, loans are found by the parent club. A PlayStyle name that is not in the table is reported, never guessed. Mapped on request: Trivela, Flair, Power Header, Aerial, 1v1 Close Down, *Führungsstärke* = Captaincy, the CPU AI traits = COM Long Ranger / Early Cross. The potential is kept in the journal with every written player.

## v0.7.1 - 2026-11-24
* **New FM list**: 11,000 players, 8,500 with every attribute, all with position ratings. FM calibration from 6,000 players (held out: field players 5.7 -> 4.4, keepers 5.6 -> 1.7).
* **Positions from FM, corrected**: the two middle FM ratings straddle the border between the levels of the game (checked on 6,600 players with the original levels: *accomplished* is level 0 / 1 / 2 in 15 / 41 / 44 %, *competent* 50 / 35 / 16 %). So the level the player has is kept inside the band that the rating allows: *natural* = 2, *accomplished* keeps 1-2, *competent* keeps up to 1 (never adds), everything else 0. Bruno Fernandes keeps CMF 2 (before: lowered to 1 and shown as lost) and loses only LMF and RMF.
* The player page tells **lost** (cannot play there any more, red dashed) from **lowered** (still playable, one level lower, orange dotted, listed with the levels).
* `tools/update_fm_list.py`: one command for a new FM list (copy, calibration with backup, hold-out report).

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
