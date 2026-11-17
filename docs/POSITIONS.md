# Positions from the values

The positions of a player in the game (0 none, 1 competent, 2 natural, for each of the 13 positions) follow the main position and the values. Measured on the 29606 outfield players of the database (their own original values and positions, `tools/fit_positions.py`, cross-validated):

* The main position is natural for 99.8 % of the players. Most players play 1 to 3 positions, and the second positions follow clear patterns (a centre back also right back, left back or defensive midfield; a centre forward the second striker; a winger the wide midfield and the other wing).

| position (beside the main one) | "plays it" share | AUC | sure at 60 % : share of right ones | recall |
|---|---|---|---|---|
| CB | 8 % | 0.94 | 0.61 | 0.51 |
| LB | 10 % | 0.86 | 0.62 | 0.08 |
| RB | 10 % | 0.83 | 0.60 | 0.08 |
| DMF | 22 % | 0.93 | 0.60 | 0.83 |
| CMF | 22 % | 0.95 | 0.60 | 0.89 |
| LMF | 34 % | 0.93 | 0.60 | 0.94 |
| RMF | 34 % | 0.93 | 0.60 | 0.93 |
| AMF | 29 % | 0.94 | 0.60 | 0.92 |
| LWF | 22 % | 0.93 | 0.60 | 0.85 |
| RWF | 21 % | 0.92 | 0.60 | 0.82 |
| SS | 37 % | 0.98 | 0.60 | 1.00 |
| CF | 15 % | 0.96 | 0.60 | 0.90 |

## What the tool does with it

* **Players of the EA FC data:** only the *alternative positions of EA FC* are added (mapped: CDM→DMF, CM→CMF, CAM→AMF, LM→LMF, RM→RMF, LW→LWF, RW→RWF, ST→CF, LWB→LB, RWB→RB), and only when the model of the values is not far under its safe bar. A position of the game is never lowered.
* **Players that are new in the game** (no skills, no COM style, playing style *Balanced*) **and pasted pages (SoFIFA / FMInside):** the positions come from the values and the main position, where the model is at least 60 % sure; *natural* (2) only where the separate model for natural is sure as well.
* All other players keep the positions they have.
* Check on the players of the game with their original values: of the other positions the models give, 61 % are also in the game, and 84 % of the game's other positions are found.

Switch: *Skills & playing style* in the sidebar (the same switch, mode *add*).
