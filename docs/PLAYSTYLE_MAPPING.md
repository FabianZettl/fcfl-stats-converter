# EA FC 27 PlayStyles → PES 21 Skills & Playing Styles

Eigener Zuordnungsvorschlag, keine offizielle Zuordnung. (Own proposal, not an official mapping.) Implemented in `flconv/data/playstyle_map.json` and `flconv/lib/playstyle.py`.

- PES 21 kennt keine „+"-Stufen. Ein PlayStyle+ wird als zusätzlicher Skill oder als Attribut-Bonus (+3 bis +5) abgebildet. *(Implemented: the additional skill; the attribute bonus is not implemented yet.)*
- FC-PlayStyles entsprechen in PES meist Skills plus Attributen.
- PES-Playing-Styles ergeben sich aus Position und Rolle (siehe Abschnitt 3).

## 1. Skills: FC 27 PlayStyle → PES 21

| FC 27 | PES 21 Skill(s) | Attribut zum Hochziehen |
|---|---|---|
| Acrobatic | Acrobatic Finishing | Finishing, Balance |
| Chip Shot | Chip Shot Control | Finishing, Curl |
| Dead Ball | Knuckle Shot, Penalty Specialist (nur wenn passend) | Place Kicking, Curl |
| Finesse Shot | Long Range Drive | Curl, Finishing |
| Gamechanger | Outside Curler, Rabona | Curl, Dribbling |
| Low Driven Shot | Rising Shots (PS+: zusätzlich First-time Shot) | Finishing, Kicking Power |
| Power Shot | Long Range Shooting | Kicking Power |
| Precision Header | Heading | Heading, Jump |
| Incisive Pass | Through Passing | Low Pass, Offensive Awareness |
| Inventive | No Look Pass, Outside Curler | Low Pass, Curl |
| Long Ball Pass | Weighted Pass, Low Lofted Pass (PS+); COM-Stil Long Ball Expert | Lofted Pass |
| Pinged Pass | One-touch Pass | Low Pass |
| Tiki Taka | One-touch Pass, Heel Trick | Ball Control, Tight Possession |
| Whipped Pass | Pinpoint Crossing; COM-Stil Early Cross | Lofted Pass, Curl |
| First Touch | Double Touch | Ball Control |
| Press Proven | Step On Skill Control | Tight Possession, Balance |
| Rapid | COM-Stil Speeding Bullet | Speed, Dribbling Speed |
| Technical | Scissors Feint, Marseille Turn oder Cross Over Turn; COM-Stil Mazing Run | Dribbling, Ball Control |
| Trickster | Flip Flap, Sombrero, Scotch Move; COM-Stil Trickster | Dribbling |
| Aerial Fortress | Heading, Acrobatic Clear | Heading, Jump |
| Anticipate | Man Marking | Ball Winning, Defensive Awareness |
| Block | Acrobatic Clear (Blocker, falls im Editor vorhanden) | Defensive Awareness |
| Intercept | Interception | Defensive Awareness |
| Jockey | Man Marking | Defensive Engagement, Speed |
| Slide Tackle | kein Skill in PES 21 | Ball Winning, Aggression |
| Bruiser | Fighting Spirit | Physical Contact |
| Enforcer | Fighting Spirit | Physical Contact, Balance |
| Long Throw | Long Throw | Kicking Power |
| Quick Step | COM-Stil Speeding Bullet | Acceleration |
| Relentless | Fighting Spirit (optional Captaincy) | Stamina |

### Torwart

| FC 27 | PES 21 |
|---|---|
| 1v1 Close Down | Reflexes, Catching; Playing Style Offensive Goalkeeper |
| Cross Claimer | Catching, Aerial-Werte |
| Deflector | Reflexes |
| Far Reach | Reaching |
| Far Throw | GK Long Throw (plus GK Low Punt oder GK High Punt) |
| Footwork | Reflexes (kein eigener Skill vorhanden) |

## 2. Hinweise

- Anticipate, Jockey und Block haben in PES keine echte Entsprechung und laufen deshalb über Man Marking und Attribute.
- Bei Finesse Shot, Gamechanger und Fighting Spirit sind mehrere Lösungen vertretbar.
- Skill-Namen und -Anzahl in PES 21 (39 bis 41 je nach Quelle) gegen die Editor-Datenbank prüfen.

## 3. Playing Styles: abgeleitet aus Position und PlayStyle-Kombination

| Position | FC-PlayStyle-Kombination | PES 21 Playing Style |
|---|---|---|
| ST | Power Shot, Low Driven, Precision Header | Goal Poacher oder Fox in the Box |
| ST | Bruiser, Precision Header, Aerial | Target Man |
| ST | Tiki Taka, Incisive, Technical | Dummy Runner |
| Flügel | Finesse, Technical, Rapid | Prolific Winger |
| Flügel | Whipped Pass, Rapid | Cross Specialist |
| Flügel | Incisive, Tiki Taka, Technical | Roaming Flank |
| ZOM | Incisive, Tiki Taka, Inventive | Creative Playmaker |
| ZOM | Technical, First Touch, wenig Tempo | Classic No. 10 |
| ZOM | Quick Step, Finesse, Low Driven | Hole Player |
| ZM | Relentless, Intercept | Box-to-Box |
| ZM/DM | Bruiser, Anticipate, Intercept | The Destroyer |
| DM | Long Ball, Pinged, Incisive | Orchestrator |
| DM | Anticipate, Intercept, Block | Anchor Man |
| IV | Long Ball, Pinged | Build Up |
| AV | Rapid, Whipped, Quick Step | Offensive Full-back |
| AV | Finesse, Low Driven | Full-back Finisher |
| AV | Anticipate, Intercept, Jockey | Defensive Full-back |
| TW | Far Reach, Deflector, Cross Claimer | Defensive Goalkeeper |
| TW | 1v1 Close Down, Footwork, Far Throw | Offensive Goalkeeper |

## 4. Referenzlisten

**EA FC 27 PlayStyles (36, jeweils mit PlayStyle+):**
- Finishing: Acrobatic, Chip Shot, Dead Ball, Finesse Shot, Gamechanger, Low Driven Shot, Power Shot, Precision Header
- Passing: Incisive Pass, Inventive, Long Ball Pass, Pinged Pass, Tiki Taka, Whipped Pass
- Ball Control: First Touch, Press Proven, Rapid, Technical, Trickster
- Defending: Aerial Fortress, Anticipate, Block, Intercept, Jockey, Slide Tackle
- Physical: Bruiser, Enforcer, Long Throw, Quick Step, Relentless
- Goalkeeper: 1v1 Close Down, Cross Claimer, Deflector, Far Reach, Far Throw, Footwork

**PES 21 Player Skills (bis zu 41):** Scissors Feint, Double Touch, Flip Flap, Marseille Turn, Sombrero, Cross Over Turn, Cut Behind & Turn, Scotch Move, Step On Skill Control, Heading, Long Range Drive, Chip Shot Control, Long Range Shooting, Knuckle Shot, Dipping Shot, Rising Shots, Acrobatic Finishing, Heel Trick, First-time Shot, One-touch Pass, Through Passing, Weighted Pass, Pinpoint Crossing, Outside Curler, Rabona, No Look Pass, Low Lofted Pass, GK Low Punt, GK High Punt, Long Throw, GK Long Throw, Penalty Specialist, GK Penalty Saver, Gamesmanship, Man Marking, Track Back, Interception, Acrobatic Clear, Captaincy, Super-sub, Fighting Spirit

**PES 21 COM Playing Styles (7):** Trickster, Mazing Run, Speeding Bullet, Incisive Run, Long Ball Expert, Early Cross, Long Ranger

**PES 21 Playing Styles (21):** Goal Poacher, Dummy Runner, Fox in the Box, Target Man, Creative Playmaker, Prolific Winger, Roaming Flank, Cross Specialist, Classic No. 10, Hole Player, Box-to-Box, The Destroyer, Orchestrator, Anchor Man, Build Up, Extra Frontman, Offensive Full-back, Full-back Finisher, Defensive Full-back, Offensive Goalkeeper, Defensive Goalkeeper

## 5. What the tool does with it (and what not)

* Only skills whose bit in `Player.bin` is known are written (35 of them, plus the 7 COM styles and the playing style). **Not written:** Knuckle Shot, Rabona, No Look Pass, GK High Punt, GK Penalty Saver, Super-sub (no bit found), the attribute bonuses of the third column and the Playing Style "Classic No. 10" rule "wenig Tempo" (needs a pace condition).
* "Dead Ball → Penalty Specialist" only when the EA penalties value is 75 or more ("nur wenn passend").
* Technical gives Scissors Feint and one of Marseille Turn / Cross Over Turn (the same one for the same player every time).
* PlayStyle data of the EA ratings page is from an older game version than FC 27 and covers about 5,900 players.
