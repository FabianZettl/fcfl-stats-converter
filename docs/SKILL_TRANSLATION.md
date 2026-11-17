# Translation PES skill ⇄ EA FC (measured)

## The rule

A skill or COM playing style is **only given when both are true**:
1. **EA FC has the matching PlayStyle** for the player (mapping in [PLAYSTYLE_MAPPING.md](PLAYSTYLE_MAPPING.md), section 1), and
2. **the EA FC values make the skill safe for this player**: a model per skill, fitted on the 14,913 players that are in the game and in the EA data (`tools/fit_skills.py`), must make it at least 50 % sure (cross-validated).

**Exception: the PlayStyle that IS the skill** (the same ability) is given on its own: Precision Header → Heading, Long Throw → Long Throw, Chip Shot → Chip Shot Control, Acrobatic → Acrobatic Finishing, Intercept → Interception, Whipped Pass → Pinpoint Crossing, Incisive Pass → Through Passing, Far Throw → GK Long Throw, Trickster → COM Trickster (`direct` in `flconv/data/playstyle_map.json`). For all other skills a PlayStyle alone is not enough, and good values alone do not give a skill that EA FC does not have. Nothing is ever removed in mode *add*.

**Measured:** over the 9,482 players that have PlayStyle data, 62 % of the skills given this way are also in the game for the same player today (the bar "PlayStyle only": 15 to 40 % depending on the skill). The rest is not "wrong", EA PlayStyles and Konami skills are two independent designs; it shows why the safe bar is used.

## Which skills can be given

* **Can be given** (the values reach the 50 % bar): Acrobatic Clear, Acrobatic Finishing, Cut Behind & Turn, Double Touch, Fighting Spirit, First-time Shot, Gamesmanship, Heading, Interception, Long Range Drive, Long Range Shooting, Man Marking, One-touch Pass, Penalty Specialist, Pinpoint Crossing, Step On Ball Control, Through Passing, Weighted Pass.
* **COM playing styles that can be given:** Early Cross, Incisive Run, Long Ball Expert, Long Ranger, Mazing Run, Speeding Bullet, Trickster.
* **Never given** (the values never reach 50 %, so no safe translation exists; the skill stays as it is): Captaincy, Chip Shot Control, Cross Over Turn, Dipping Shot, Flip Flap, Heel Trick, Long Throw, Low Lofted Pass, Marseille Turn, Outside Curler, Rising Shots, Scissors Feint, Scotch Move, Sombrero, Track Back. COM: none.
* **Goalkeeper skills** (GK Long Throw, GK Low Punt): from the keeper attributes and the EA PlayStyle *Far Throw*.
* Skills without a known bit in `Player.bin` (Knuckle Shot, Rabona, No Look Pass, GK High Punt, GK Penalty Saver, Super-sub) are not written.

## Playing styles

A playing style is only changed when the EA PlayStyle combination of the table in `PLAYSTYLE_MAPPING.md` (section 3) matches the position **and** the values tell that style apart well (AUC at least 0.70) and fit: this is the case for *Target Man*, *Cross Specialist*, *The Destroyer* and *Defensive Full-back*. For all other styles the values do not tell them apart (the style is mostly a matter of position), so the current style is kept.

## The other direction: EA PlayStyles that PES only shows through values

PlayStyles without a real skill in PES (Slide Tackle, Jockey, Block, Anticipate, Quick Step, Relentless, Rapid and the goalkeeper ones) give **+1** (PlayStyle) or **+2** (PlayStyle+) on the matching attributes; for all other PlayStyles only the PlayStyle+ gives **+1**. The attributes are raised before the fit to the overall, are kept out of the fit, and the other attributes give way so that the overall of the EA FC entry is reached again. Switch: *PlayStyle bonus on attributes* in the sidebar; the table is the section `boost` of `flconv/data/playstyle_map.json`.

## Quality per skill

| PES skill / COM | EA PlayStyle(s) | safe from the values | AUC |
|---|---|---|---|
| Acrobatic Clear | Aerial Fortress, Block | yes | 0.86 |
| Acrobatic Finishing | Acrobatic | yes | 0.85 |
| Captaincy | – | no | 0.80 |
| Chip Shot Control | Chip Shot | no | 0.85 |
| Cross Over Turn | Technical | no | 0.79 |
| Cut Behind & Turn | – | yes | 0.81 |
| Dipping Shot | – | no | 0.78 |
| Double Touch | First Touch | yes | 0.83 |
| Fighting Spirit | Bruiser, Enforcer, Relentless | yes | 0.76 |
| First-time Shot | Low Driven Shot | yes | 0.88 |
| Flip Flap | Trickster | no | 0.78 |
| Gamesmanship | – | yes | 0.80 |
| Heading | Aerial Fortress, Precision Header | yes | 0.89 |
| Heel Trick | Tiki Taka | no | 0.81 |
| Interception | Intercept | yes | 0.83 |
| Long Range Drive | Finesse Shot | yes | 0.82 |
| Long Range Shooting | Power Shot | yes | 0.79 |
| Long Throw | Long Throw | no | 0.84 |
| Low Lofted Pass | Long Ball Pass | no | 0.77 |
| Man Marking | Anticipate, Jockey | yes | 0.89 |
| Marseille Turn | Technical | no | 0.79 |
| One-touch Pass | Pinged Pass, Tiki Taka | yes | 0.80 |
| Outside Curler | Gamechanger, Inventive | no | 0.78 |
| Penalty Specialist | Dead Ball | yes | 0.83 |
| Pinpoint Crossing | Whipped Pass | yes | 0.82 |
| Rising Shots | Low Driven Shot | no | 0.78 |
| Scissors Feint | Technical | no | 0.82 |
| Scotch Move | Trickster | no | 0.81 |
| Sombrero | Trickster | no | 0.77 |
| Step On Ball Control | Press Proven | yes | 0.79 |
| Through Passing | Incisive Pass | yes | 0.83 |
| Track Back | – | no | 0.74 |
| Weighted Pass | Long Ball Pass | yes | 0.80 |
| Early Cross | Whipped Pass | yes | 0.85 |
| Incisive Run | – | yes | 0.84 |
| Long Ball Expert | Long Ball Pass | yes | 0.82 |
| Long Ranger | – | yes | 0.79 |
| Mazing Run | Technical | yes | 0.85 |
| Speeding Bullet | Quick Step, Rapid | yes | 0.86 |
| Trickster | Trickster | yes | 0.88 |
