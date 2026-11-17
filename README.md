# FL Stats Converter

Converts **EA SPORTS FC** player stats (and pages of **FMInside** / **SoFIFA**) into the player database of
**Football Life** (`Player.bin`, the 25 attributes of PES 21 / eFootball): for **one player, a club, a league or the whole database**,
with a **backup before every write**, a check afterwards and a one-click restore.

You choose the path to your `Player.bin`, the tool compares your database with the EA FC data that comes with it,
shows what would change (every attribute, old → new, with the reason) and offers to write it. No other tool is needed.

> Deutsche Anleitung: [README.de.md](README.de.md)

## What is in it

* **Update the active database with EA FC stats** – the main purpose. League, club, player or the whole database, found automatically in the EA FC data that comes with the tool.
* **Manual converter for SoFIFA and FMInside** – open the player page, select everything (Ctrl+A), copy (Ctrl+C), paste it into the tool: it converts the values (SoFIFA) or the Football Manager attributes (FMInside) to the game.
  Search buttons for both sites are on every player.
* **Manual adjustments** – set the overall you want for a player (the attributes are moved to match), change single attributes, change names and shirt names.
* Folder picker, backups with one-click restore, players that are already converted are marked and skipped.

**Planned:** adjustments of height, weight, positions, skills and play styles, and more.

![A club with its players](docs/screenshots/club-bayern.png)
![One player with every attribute and the reason for it](docs/screenshots/player-harry-kane.png)

More: [a league club](docs/screenshots/club-3-liga.png) · [another club](docs/screenshots/club-molde.png) · [another player](docs/screenshots/player-tomas-jacob.png)

## Start

You need Python 3.9 or newer (nothing else, the tool uses only the standard library) **or** a download from the *Releases* page
(`fl-stats-converter-windows.exe`, `fl-stats-converter-linux`).

```
python3 flconv/server.py        # Linux / macOS     (or ./start.sh)
py flconv\server.py             # Windows           (or start.bat)
```

The tool opens `http://127.0.0.1:8790/` in your browser (it only listens on your own computer).

1. Enter the path of your `Player.bin` in the box *Your database* (the folder that contains it, a folder above it, or the file itself).
   For Football Life that is the folder `pesdb`, e.g. `…/livecpk/_FL26MyWorld/common/etc/pesdb`.
2. Choose a league, then a club. Players that are found in the EA FC data are shown with `old overall → new overall`.
3. Open a player to see every attribute with its reason, change values or names by hand, or use *Convert the club* / *Convert the whole database*.
4. Close the game while you write. Start a **new career** to see the new values.

Settings, backups and the copy of your original `Player.bin` are kept in `~/.local/share/fl-stats-converter` (Linux) or
`%APPDATA%\FL-Stats-Converter` (Windows); `--data-dir` changes that.

## What it does with a player

1. **Finds the player in the EA FC data.** The full name has to match first; if there are namesakes the tool narrows them down by year of birth
   (compared with the age in your database), height, nation and club, and looks at the overall last (clubs and overalls differ between
   the game and the export, players move). Anything it is not sure about is shown for you to decide, and what you decide is remembered.
   The search box and the paste field cover players who are not in the data.
2. **Converts the values** with the formulas of the *PES Stats Converter* (see [CHANGES.md](CHANGES.md) for everything that was changed or added),
   moves them to the scale of Football Life, balances them by position, uses a keeper model for goalkeepers and fits the result to the overall of the source.
3. **Youth bonus** (optional): +1 to +3 overall for young players whose potential is far above their rating (needs a potential, from a SoFIFA page).
4. **Development** to a date you choose: the EA data is from 01.09.2026; if your career is further on, young players grow and old ones decline by a model.
5. Writes `Player.bin`: **backup first**, write, read again and compare, on any difference the backup is put back.

The conversion always starts from the **original** values (a copy of your `Player.bin` is made the first time you use a database), so running it twice
gives the same result and never scales players down again.
If your `Player.bin` was already changed by another tool when you start, that changed file counts as the original; keep your own backup.

## Data

`flconv/data/fc27-players.csv` is a data set of EA SPORTS FC 27 ratings (17,849 male players, snapshot 12 Sep 2026). **Sources and licenses:** [DATA.md](DATA.md).
You can use another export with `--csv file.csv` (same columns, see DATA.md).

## Notes

* Developed and tested on **Linux** with the database of Football Life 2027. Windows should work (pure Python), but it was not tested there.
* The layout of `Player.bin` (WESYS container, 312 byte records, attribute bit fields) was found by comparing the file with the in-game table of the same database.
  Other databases or versions can differ: the tool checks the file when it reads it, refuses what it does not understand and always makes a backup, but try it on a copy first.
* This is a fan tool. It is not affiliated with or endorsed by EA, Konami, Sports Interactive, SoFIFA, FMInside or the Football Life team.
  All names and trademarks belong to their owners.

## License

GPL-3.0, see [LICENSE](LICENSE). The conversion formulas are derived from the *PES Stats Converter* by moth1995 (GPL-3.0), see [CHANGES.md](CHANGES.md).
