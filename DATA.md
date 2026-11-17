# Data

`flconv/data/fc27-players.csv` – ratings and attributes of **EA SPORTS FC 27** (17,849 male players, snapshot 12 Sep 2026, with date of birth),
with height, weight, preferred foot, weak foot and skill moves added where they are known (see below).

| Part | Source | License / note |
|---|---|---|
| Ratings, attributes, date of birth | Export of the official EA ratings page (`drop-api.ea.com/rating/ea-sports-fc`) published in the repository **LakshmiKanth11/EA_FC_ANALYSIS** (<https://github.com/LakshmiKanth11/EA_FC_ANALYSIS>), snapshot 12.09.2026 | The repository states no license. The values are the facts shown on EA's public ratings page; EA owns the underlying game data. |
| Height | **FC 27 Players Dataset** by Sam Teo on Kaggle (<https://www.kaggle.com/>, data from FIFPlay.com, retrieved 11.10.2026) | Kaggle: Open Database License (ODbL), contents: Database Contents License |

The data set is included because the tool needs it. If you are the owner of any of it and want it removed, open an issue and it will be taken out.

**Using another file:** `python3 flconv/server.py --csv your.csv` – same columns as `fc27-players.csv`:
`stats_id, first_name, last_name, common_name, full_name, club_name, nation_name, position, position_alt, position_alt_2, position_alt_3, rating, potential, height, birthdate (dd-mm-yyyy)`
and the attribute columns `crossing, finishing, heading, short_passing, volleys, ball_control, curve, dribbling, free_kick_accuracy, long_passing, acceleration, agility, balance, reactions,
sprint_speed, jumping, long_shots, shot_power, stamina, strength, aggression, positioning, composure, interceptions, penalties, vision, def_awareness, standing_tackle, sliding_tackle,
gk_diving, gk_handling, gk_kicking, gk_positioning, gk_reflexes`. Rows with club `ICON` or `Hero` are ignored.
The potential column is empty in this data set (it is filled by pasting a SoFIFA page).

**Columns `weight`, `foot`, `weak_foot`, `skill_moves`, `playstyles` and missing heights** were added with `tools/add_profile_columns.py` (join on the EA player id `stats_id`):
* weight (12,026 players), weak foot, skill moves and heights that the first data set lacks (5,639): the official EA ratings page (`drop-api.ea.com/rating/ea-sports-fc`), pulled 17 Nov 2026. It still serves an older game version than FC 27 (players that are not in it get no value); height, weight and foot hardly change between versions.
* preferred foot (13,467 players): the FIFPlay data above (FC 27) where it has the player, otherwise the ratings page.
The tool writes height, weight and foot only where the data has a value; empty means "leave as it is".
* `playstyles` (5,923 players): the PlayStyles of the ratings page as `Rapid|Technical+` (`+` = PlayStyle+); empty where the page has none or does not have the player.
