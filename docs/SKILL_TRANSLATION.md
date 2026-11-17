# Translation PES skill ⇄ EA FC (measured)

Every skill and COM playing style of PES 21 and how the tool gets it from EA FC data. Two ways: **EA PlayStyles** (mapping in `PLAYSTYLE_MAPPING.md`) and **values** (a model per skill, fitted on the 14,913 players that are in the game and in the EA data, `tools/fit_skills.py`).

* "from values": a skill is added only when the values make it at least 50 % sure (cross-validated). `no` = the values do not tell (the share of right ones stays under 50 %), the skill then only comes from a PlayStyle.
* "PlayStyle vs. game" = how often the mapped EA PlayStyle agrees with the skill the game gives the same player today: precision / recall, on the 5,9k players the ratings page has PlayStyles for. These are low: EA PlayStyles and Konami skills are two independent designs, so the tool adds the EA-derived skills, it does not recover the old ones. This is why **add** is the safe mode and **replace** is not.
* "base rate" = share of the players that have the skill in the game.

| PES skill | EA PlayStyle(s) mapped | from values | PlayStyle vs. game (prec / rec) | base rate |
|---|---|---|---|---|
| Acrobatic Clear | Aerial Fortress, Block | yes (≥50 % sure from AUC 0.86) | 0.283 / 0.208 | 0.127 |
| Acrobatic Finishing | Acrobatic | yes (≥50 % sure from AUC 0.85) | 0.514 / 0.039 | 0.093 |
| Captaincy | – | no (AUC 0.80) | – | 0.042 |
| Chip Shot Control | Chip Shot | no (AUC 0.85) | 0.375 / 0.1 | 0.028 |
| Cross Over Turn | Technical | no (AUC 0.79) | 0.136 / 0.207 | 0.049 |
| Cut Behind & Turn | – | yes (≥50 % sure from AUC 0.81) | – | 0.134 |
| Dipping Shot | – | no (AUC 0.78) | – | 0.062 |
| Double Touch | First Touch | yes (≥50 % sure from AUC 0.83) | 0.359 / 0.092 | 0.090 |
| Fighting Spirit | Bruiser, Enforcer, Relentless | yes (≥50 % sure from AUC 0.76) | 0.314 / 0.178 | 0.148 |
| First-time Shot | Low Driven Shot | yes (≥50 % sure from AUC 0.88) | 0.451 / 0.064 | 0.148 |
| Flip Flap | Trickster | no (AUC 0.78) | 0.111 / 0.04 | 0.017 |
| Gamesmanship | – | yes (≥50 % sure from AUC 0.80) | – | 0.113 |
| Heading | Aerial Fortress, Precision Header | yes (≥50 % sure from AUC 0.89) | 0.491 / 0.295 | 0.168 |
| Heel Trick | Tiki Taka | no (AUC 0.81) | 0.108 / 0.021 | 0.047 |
| Interception | Intercept | yes (≥50 % sure from AUC 0.83) | 0.527 / 0.117 | 0.239 |
| Long Range Drive | Finesse Shot | yes (≥50 % sure from AUC 0.82) | 0.354 / 0.167 | 0.089 |
| Long Range Shooting | Power Shot | yes (≥50 % sure from AUC 0.79) | 0.486 / 0.096 | 0.098 |
| Long Throw | Long Throw | no (AUC 0.84) | 0.356 / 0.19 | 0.047 |
| Low Lofted Pass | Long Ball Pass | no (AUC 0.77) | 0.163 / 0.174 | 0.061 |
| Man Marking | Anticipate, Jockey | yes (≥50 % sure from AUC 0.89) | 0.27 / 0.164 | 0.093 |
| Marseille Turn | Technical | no (AUC 0.79) | 0.122 / 0.275 | 0.033 |
| One-touch Pass | Pinged Pass, Tiki Taka | yes (≥50 % sure from AUC 0.80) | 0.435 / 0.056 | 0.149 |
| Outside Curler | Gamechanger, Inventive | no (AUC 0.78) | 0.203 / 0.193 | 0.061 |
| Penalty Specialist | Dead Ball | yes (≥50 % sure from AUC 0.83) | 0.123 / 0.06 | 0.053 |
| Pinpoint Crossing | Whipped Pass | yes (≥50 % sure from AUC 0.82) | 0.46 / 0.149 | 0.104 |
| Rising Shots | Low Driven Shot | no (AUC 0.78) | 0.17 / 0.045 | 0.069 |
| Scissors Feint | Technical | no (AUC 0.82) | 0.182 / 0.25 | 0.059 |
| Scotch Move | Trickster | no (AUC 0.81) | 0.175 / 0.041 | 0.027 |
| Sombrero | Trickster | no (AUC 0.77) | 0.143 / 0.046 | 0.019 |
| Step On Ball Control | Press Proven | yes (≥50 % sure from AUC 0.79) | 0.214 / 0.052 | 0.129 |
| Through Passing | Incisive Pass | yes (≥50 % sure from AUC 0.83) | 0.532 / 0.15 | 0.131 |
| Track Back | – | no (AUC 0.74) | – | 0.045 |
| Weighted Pass | Long Ball Pass | yes (≥50 % sure from AUC 0.80) | 0.246 / 0.176 | 0.090 |

**COM playing styles**

| COM style | EA PlayStyle(s) mapped | from values | PlayStyle vs. game (prec / rec) | base rate |
|---|---|---|---|---|
| Early Cross | Whipped Pass | yes (≥50 % sure from AUC 0.85) | 0.6 / 0.129 | 0.158 |
| Incisive Run | – | yes (≥50 % sure from AUC 0.84) | – | 0.192 |
| Long Ball Expert | Long Ball Pass | yes (≥50 % sure from AUC 0.82) | 0.597 / 0.182 | 0.222 |
| Long Ranger | – | yes (≥50 % sure from AUC 0.79) | – | 0.235 |
| Mazing Run | Technical | yes (≥50 % sure from AUC 0.85) | 0.65 / 0.237 | 0.218 |
| Speeding Bullet | Quick Step, Rapid | yes (≥50 % sure from AUC 0.86) | 0.734 / 0.292 | 0.202 |
| Trickster | Trickster | yes (≥50 % sure from AUC 0.88) | 0.683 / 0.041 | 0.100 |

**Goalkeepers** (GK skills from the keeper attributes): Captaincy (AUC 0.78), GK Long Throw (AUC 0.64, ≥50 %), GK Low Punt (AUC 0.59, ≥50 %)

## The other direction: EA PlayStyles that PES only shows through values

PlayStyles without a real skill in PES (Slide Tackle, Jockey, Block, Anticipate, Quick Step, Relentless, Rapid and the goalkeeper ones) give **+1** (PlayStyle) or **+2** (PlayStyle+) on the matching attributes; for all other PlayStyles only the PlayStyle+ gives **+1**. The attributes are raised before the fit to the overall, are kept out of the fit, and the other attributes give way so that the overall of the EA FC entry is reached again. Switch: *PlayStyle bonus on attributes* in the sidebar; the table is the section `boost` of `flconv/data/playstyle_map.json`.

## Not derivable

Skills the values cannot tell and that have no EA PlayStyle: **Captaincy, Dipping Shot, Track Back**; skills without a known bit in `Player.bin` (Knuckle Shot, Rabona, No Look Pass, GK High Punt, GK Penalty Saver, Super-sub) are not written. The tool never removes these.
