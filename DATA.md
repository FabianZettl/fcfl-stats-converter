# Data

`flconv/data/fc27-players.csv` – ratings and attributes of **EA SPORTS FC 27** (17,849 male players, snapshot 12 Sep 2026, with date of birth),
with the heights of 7,725 of them added from a second data set.

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
