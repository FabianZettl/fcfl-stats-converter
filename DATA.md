# Data

`flconv/data/sofifa-base.csv` – the **German SoFIFA export of all players** (19,594 rows, snapshot 24 Nov 2026): rating, potential, the 34 attribute values, positions, height, weight, preferred and weak foot,
skill moves, PlayStyles (*Spielstile*, *Spielstile+*), growth profile, emotion, acceleration type, work rates, contract, loan, value, wage and release clause. It replaces the EA FC 27 data set (`fc27-players.csv`, an export of
EA's public ratings page) that the tool used before; the PlayStyle names are translated with the table of EA FC 27 (`flconv/data/playstyles_de.json`, from the German and English EA pages).

| Part | Source | License / note |
|---|---|---|
| All values of `sofifa-base.csv` | the player pages of sofifa.com, exported by the user's own tool and delivered as a CSV | The values are the facts shown on SoFIFA's public pages (they are the EA SPORTS FC values); SoFIFA and EA own the underlying data. |
| `playstyles_de.json` | the PlayStyle pages of EA SPORTS FC 27 (German and English) | Names only. |

The data set is included because the tool needs it. If you are the owner of any of it and want it removed, open an issue and it will be taken out.

**Using another file:** `python3 flconv/server.py --csv your.csv`, or put a newer export into the folder `ea-base` of the data folder (it is used at once). The tool reads the German SoFIFA export and the EA FC export with these columns:
`stats_id, first_name, last_name, common_name, full_name, club_name, nation_name, position, position_alt, position_alt_2, position_alt_3, rating, potential, height, birthdate (dd-mm-yyyy)`
and the attribute columns `crossing, finishing, heading, short_passing, volleys, ball_control, curve, dribbling, free_kick_accuracy, long_passing, acceleration, agility, balance, reactions,
sprint_speed, jumping, long_shots, shot_power, stamina, strength, aggression, positioning, composure, interceptions, penalties, vision, def_awareness, standing_tackle, sliding_tackle,
gk_diving, gk_handling, gk_kicking, gk_positioning, gk_reflexes`. Rows with club `ICON` or `Hero` are ignored.
The potential column is filled in the German SoFIFA export.

**Columns `weight`, `foot`, `weak_foot`, `skill_moves`, `playstyles` and missing heights** were added with `tools/add_profile_columns.py` (join on the EA player id `stats_id`):
* weight (12,026 players), weak foot, skill moves and heights that the first data set lacks (5,639): the official EA ratings page (`drop-api.ea.com/rating/ea-sports-fc`), pulled 17 Nov 2026. It still serves an older game version than FC 27 (players that are not in it get no value); height, weight and foot hardly change between versions.
* preferred foot (13,467 players): the FIFPlay data above (FC 27) where it has the player, otherwise the ratings page.
The tool writes height, weight and foot only where the data has a value; empty means "leave as it is".
* `playstyles` (5,923 players): the PlayStyles of the ratings page as `Rapid|Technical+` (`+` = PlayStyle+); empty where the page has none or does not have the player.
