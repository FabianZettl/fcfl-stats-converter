# What the players of the game have on the values behind a skill, COM style or playing style

Measured on all 29606 outfield players of the database (their own original values and positions, no EA FC data). "from" = the value of the strongest attribute from which at least half of the players that reach it have the skill; "holders / others" = the mean of that attribute for the players that have the skill and for those that do not. Used by the tool to give skills to players that are not in the EA FC data (tools/fit_pes_traits.py).

## Skills

| skill | share of players | strongest values (+ makes it likely) | holders / others | half have it from | main positions | quality |
|---|---|---|---|---|---|---|
| Heading | 13.6 % | Heading, Jump, Finishing | Heading 76 / 63, Jump 76 / 68, Finishing 65 / 64 | Heading 73 | CB 50%, CF 34%, DMF 5% | AUC 0.92, safe (≥50 %) possible |
| Man Marking | 7.7 % | Aggression, BallWinning, PhysicalContact | Aggression 79 / 67, BallWinning 77 / 63, PhysicalContact 80 / 69 | Aggression 85 | CB 72%, DMF 14%, CMF 5% | AUC 0.92, safe (≥50 %) possible |
| First-time Shot | 13.4 % | Finishing, OffensiveAwareness | Finishing 74 / 62, OffensiveAwareness 74 / 64 | Finishing 75 | CF 66%, LWF 7%, RWF 7% | AUC 0.90, safe (≥50 %) possible |
| Acrobatic Finishing | 8.0 % | Finishing, Jump, KickingPower | Finishing 74 / 63, Jump 72 / 69, KickingPower 76 / 71 | Finishing 83 | CF 56%, LWF 11%, RWF 10% | AUC 0.88, safe (≥50 %) possible |
| Long Throw | 3.7 % | Speed, Heading | Speed 78 / 74, Heading 68 / 65 | – | RB 36%, CB 28%, LB 26% | AUC 0.88, safe (≥50 %) possible |
| Acrobatic Clear | 10.4 % | Jump | Jump 75 / 69 | – | CB 66%, RB 12%, LB 10% | AUC 0.88, safe (≥50 %) possible |
| Through Passing | 11.6 % | LowPass, TightPossession | LowPass 75 / 69, TightPossession 73 / 68 | LowPass 83 | CMF 37%, AMF 26%, DMF 9% | AUC 0.86, safe (≥50 %) possible |
| Pinpoint Crossing | 9.1 % | LoftedPass, Curl | LoftedPass 74 / 69, Curl 71 / 65 | – | LB 29%, RB 19%, AMF 10% | AUC 0.86, safe (≥50 %) possible |
| Interception | 19.7 % | BallWinning, LowPass, Heading | BallWinning 73 / 62, LowPass 71 / 69, Heading 69 / 64 | BallWinning 75 | CB 44%, DMF 20%, RB 13% | AUC 0.85, safe (≥50 %) possible |
| Chip Shot Control | 2.6 % | OffensiveAwareness | OffensiveAwareness 75 / 65 | – | CF 48%, AMF 13%, LWF 12% | AUC 0.85, no safe level |
| Track Back | 3.9 % | Aggression, OffensiveAwareness, BallWinning | Aggression 70 / 68, OffensiveAwareness 72 / 65, BallWinning 62 / 64 | – | CF 31%, CMF 14%, LWF 12% | AUC 0.84, no safe level |
| Weighted Pass | 7.8 % | LoftedPass, Curl, TightPossession | LoftedPass 75 / 69, Curl 70 / 65, TightPossession 73 / 68 | LoftedPass 81 | CMF 30%, DMF 22%, CB 16% | AUC 0.83, safe (≥50 %) possible |
| One-touch Pass | 12.5 % | LowPass, TightPossession | LowPass 75 / 69, TightPossession 73 / 68 | LowPass 81 | CMF 35%, DMF 16%, AMF 15% | AUC 0.82, safe (≥50 %) possible |
| Captaincy | 4.3 % | DefensiveAwareness, Heading, Balance | DefensiveAwareness 70 / 62, Heading 71 / 65, Balance 70 / 69 | DefensiveAwareness 87 | CB 36%, DMF 17%, CMF 15% | AUC 0.82, no safe level |
| Scissors Feint | 5.4 % | Dribbling, TightPossession, Curl | Dribbling 76 / 69, TightPossession 73 / 68, Curl 70 / 65 | – | LWF 24%, RWF 19%, CF 14% | AUC 0.82, no safe level |
| Cut Behind & Turn | 11.7 % | Dribbling, BallControl, LowPass | Dribbling 75 / 69, BallControl 75 / 70, LowPass 73 / 69 | Dribbling 85 | LWF 17%, AMF 17%, RWF 16% | AUC 0.82, safe (≥50 %) possible |
| Scotch Move | 2.3 % | Dribbling, Balance | Dribbling 76 / 69, Balance 76 / 69 | – | LWF 26%, AMF 17%, RWF 17% | AUC 0.82, no safe level |
| Penalty Specialist | 5.0 % | PlaceKicking, Stamina, Finishing | PlaceKicking 67 / 62, Stamina 75 / 75, Finishing 72 / 64 | – | CF 49%, CMF 9%, AMF 8% | AUC 0.82, safe (≥50 %) possible |
| Double Touch | 8.1 % | Dribbling, TightPossession, Balance | Dribbling 75 / 69, TightPossession 73 / 68, Balance 75 / 69 | – | LWF 19%, AMF 18%, RWF 16% | AUC 0.81, safe (≥50 %) possible |
| Long Range Drive | 7.6 % | Finishing, Curl, KickingPower | Finishing 70 / 63, Curl 71 / 65, KickingPower 74 / 71 | – | LWF 22%, RWF 16%, AMF 16% | AUC 0.81, safe (≥50 %) possible |
| Fighting Spirit | 13.1 % | Aggression, Stamina, Balance | Aggression 75 / 67, Stamina 78 / 74, Balance 70 / 69 | Aggression 85 | CB 24%, DMF 20%, CMF 17% | AUC 0.81, safe (≥50 %) possible |
| Rising Shots | 6.0 % | GKReach, GKClearing, GKReflexes | GKReach 40 / 40, GKClearing 40 / 40, GKReflexes 40 / 40 | – | CF 29%, CMF 18%, DMF 11% | AUC 0.81, no safe level |
| Step On Ball Control | 11.1 % | Dribbling, TightPossession | Dribbling 75 / 69, TightPossession 74 / 68 | – | AMF 19%, CMF 17%, LWF 14% | AUC 0.80, safe (≥50 %) possible |
| Outside Curler | 5.7 % | TightPossession, Curl, LoftedPass | TightPossession 74 / 68, Curl 71 / 65, LoftedPass 73 / 69 | TightPossession 85 | AMF 19%, CMF 15%, LWF 13% | AUC 0.79, safe (≥50 %) possible |
| Gamesmanship | 10.4 % | Dribbling, Aggression, Balance | Dribbling 75 / 69, Aggression 65 / 69, Balance 74 / 69 | – | LWF 18%, RWF 17%, CF 17% | AUC 0.79, safe (≥50 %) possible |
| Flip Flap | 1.7 % | Dribbling | Dribbling 76 / 69 | – | LWF 26%, RWF 18%, AMF 15% | AUC 0.79, no safe level |
| Low Lofted Pass | 5.6 % | LoftedPass, TightPossession, Curl | LoftedPass 75 / 69, TightPossession 72 / 68, Curl 70 / 65 | – | CMF 27%, DMF 18%, CB 15% | AUC 0.79, safe (≥50 %) possible |
| Long Range Shooting | 8.8 % | KickingPower, Finishing | KickingPower 76 / 71, Finishing 69 / 64 | KickingPower 87 | CMF 26%, CF 15%, AMF 14% | AUC 0.79, safe (≥50 %) possible |
| Heel Trick | 4.4 % | Dribbling, TightPossession, Aggression | Dribbling 75 / 69, TightPossession 74 / 68, Aggression 65 / 68 | – | CF 24%, AMF 18%, LWF 15% | AUC 0.78, no safe level |
| Dipping Shot | 5.4 % | KickingPower, Finishing, PlaceKicking | KickingPower 75 / 71, Finishing 69 / 64, PlaceKicking 68 / 62 | – | CMF 17%, CF 17%, AMF 16% | AUC 0.77, no safe level |
| Marseille Turn | 3.2 % | Dribbling, TightPossession, BallControl | Dribbling 76 / 69, TightPossession 75 / 68, BallControl 76 / 71 | – | AMF 20%, CMF 18%, LWF 13% | AUC 0.77, no safe level |
| Cross Over Turn | 4.2 % | Dribbling, Speed | Dribbling 75 / 69, Speed 79 / 74 | – | LWF 22%, CF 18%, RWF 16% | AUC 0.77, no safe level |
| Sombrero | 1.9 % | Dribbling, TightPossession | Dribbling 75 / 69, TightPossession 73 / 68 | – | AMF 21%, LWF 17%, CF 14% | AUC 0.76, no safe level |

## COM playing styles

| skill | share of players | strongest values (+ makes it likely) | holders / others | half have it from | main positions | quality |
|---|---|---|---|---|---|---|
| Speeding Bullet | 18.0 % | Speed, Dribbling, Acceleration | Speed 80 / 73, Dribbling 74 / 69, Acceleration 80 / 73 | Speed 79 | LWF 18%, RB 18%, RWF 17% | AUC 0.88, safe (≥50 %) possible |
| Early Cross | 13.4 % | LoftedPass, Curl | LoftedPass 72 / 69, Curl 69 / 65 | – | LB 32%, RB 32%, CB 8% | AUC 0.87, safe (≥50 %) possible |
| Incisive Run | 17.6 % | Dribbling | Dribbling 75 / 68 | Dribbling 79 | LWF 28%, RWF 25%, CF 11% | AUC 0.87, safe (≥50 %) possible |
| Trickster | 8.9 % | Dribbling, BallControl | Dribbling 76 / 69, BallControl 76 / 71 | Dribbling 81 | LWF 22%, AMF 21%, RWF 18% | AUC 0.86, safe (≥50 %) possible |
| Mazing Run | 20.2 % | Dribbling, Acceleration | Dribbling 75 / 68, Acceleration 78 / 73 | Dribbling 77 | AMF 19%, LWF 18%, RWF 16% | AUC 0.85, safe (≥50 %) possible |
| Long Ball Expert | 18.3 % | LoftedPass | LoftedPass 73 / 69 | – | CB 41%, CMF 22%, DMF 19% | AUC 0.85, safe (≥50 %) possible |
| Long Ranger | 20.4 % | KickingPower | KickingPower 75 / 71 | KickingPower 79 | CMF 27%, CF 15%, AMF 13% | AUC 0.81, safe (≥50 %) possible |

## Playing styles

The playing style is mostly decided by the position; the values add information for the groups below (accuracy of a cross-validated model against the position alone):

| position group | accuracy | position alone |
|---|---|---|
| GK | 67 % | 67 % |
| DEF | 73 % | 36 % |
| DM/CM | 66 % | 46 % |
| WIDE-MID | 36 % | 36 % |
| AM/WING | 70 % | 49 % |
| FWD | 68 % | 63 % |
