# FCFL - Stats Converter

One converter for Football Life (PES 2021 engine): writes EA FC stats (and pasted SoFIFA / FMInside pages, manual edits) into the game database `Player.bin`
and, optionally through Gaffer's bridge, into a running Master League. Public repo: `FabianZettl/fcfl-stats-converter`. Local checkout: `~/Projects/fl-stats-converter`.
Run: `./start.sh` (stdlib `http.server`, default port 8790, UI in `flconv/static/index.html`). Tests: `for t in tests/test_*.py; do python3 $t; done` (all must print `ok`).

## How to work with the user (standing rules)
* Answer in **German**. End every reply with an honest **"Nicht geprüft"** note: what was not verified, what could still go wrong.
* **Ponytail mode**: the smallest change that fully solves the task. No extra features, options or abstractions that nobody asked for.
* **Screenshot-check every new UI** (chromedriver works over plain HTTP, no selenium installed; firefox/chromium `--screenshot` alone does not wait for the SPA).
* Update README/README.de/CHANGES/docs and the bundle when behaviour changes. Commit with the author `FCFL Stats Converter <noreply@example.invalid>` (`git -c user.name=... -c user.email=...`) and end the message with the `Co-Authored-By` line from the session reminder.
* **Confirm before outward-facing actions** (push is allowed, releases/tags/forum posts only after asking). Releases are built by `.github/workflows/release.yml` (Linux + Windows, PyInstaller one-file). Last release: v0.4.1 (development by time weighted by the performance; club view with pitch, Sofascore line-up + performance, height/weight/foot and shipped GrowthBridge.lua for the bridge, restart button).
* Never kill processes with `pkill -f` / `pgrep -f` patterns that match your own shell (it killed the shell twice, exit 144): use `ps -eo pid,args | awk '/pattern/ && !/awk/{print $1}'`.
* Do not run the user's untrusted downloads (e.g. `DR_Ultimate_Update_Tool_v41.exe`); unpack into an empty dir and read only data.
* There is **one** converter on purpose (the Gaffer-bound `fl-dbtool` was retired): do not build a second one.

## Files
* `flconv/server.py` - everything server-side: settings, Player.bin load/match, preview, apply, bulk job, Master League (bridge) writer, journal, HTTP routes.
* `flconv/plbin.py` - `PlayerBin`: WESYS container (16 byte header + zlib), 312 byte records, attributes (6 bit, +40), plus profile fields found by bit matching: position@434 (4 bit),
  age@408 (6 bit +15), height@216 (8 bit +100), weight@256 (7 bit +30), foot@514, 35 skill bits, 7 COM bits, playing style@155 (5 bit, 22 styles), weak foot use@454 / acc@462 (2 bit +1),
  13 position levels 0/1/2 (`POS_BITS`). `verify()` re-reads the file after a write.
* `flconv/convert.py` - scale shift, position boost, keeper model, `fit_overall`, youth bonus, `scale_player` (players without EA data, always from the ORIGINAL values).
* `flconv/timeshift.py` - development from 2026-09-01 to the write date. `flconv/dbmeta.py` - teams, leagues, squads (`PlayerAssignment.bin`) from the database folder.
* `flconv/lib/` - `fcdb.py` (EA FC csv), `sofifa.py` (port of the PES Stats Converter), `fmdata.py`, `gkcal.py`, `poscal.py`, `playstyle.py` (PlayStyle -> skills/COM/style, models, `cap`, `margins`).
* `flconv/data/` - `fc27-players.csv` (17,849 rows, PlayStyles from an OLDER game version, ~5,900 players), `playstyle_map.json`, `skill_model.json`, `pes_traits_model.json`, `position_model.json`, `fm_calib.json`.
* `tools/` - fitting scripts for the logistic models (numpy only for fitting, JSON coefficients at runtime). `docs/` - mapping and quality documents. `DATA.md` - data sources.
* Data dir (runtime): `~/.local/share/fl-stats-converter` (settings, backups, copy of the original `Player.bin`, journal, `potential-ml.json`, `assign-*.json`).

## Core behaviour (do not break)
* **Idempotent**: always computed from the original values (copy of the first `Player.bin`), never from what is in the database now. The journal stores per player `sig` (EA id, youth, quarter of months, profile flag, skill mode, psboost) and the written values `a` (tolerance 3).
  Players already converted are skipped unless something changed; if only the profile changed (PlayStyles, skills, positions) they are written again with only the changed values.
* **Matching**: full name first, then year of birth (+-2), height (+-3, narrowing only), nation, club; overall last (FL overall is about EA + 4). User assignments persist (`assign-<hash>.json`).
* Pipeline: EA values -> scale shift -> position boost -> keeper model -> PlayStyle boosts (locked) -> fit to EA overall -> youth bonus -> timeshift -> user edits.
* **Skills/COM/playing style/positions** are given only when EA FC has the PlayStyle AND the values make it safe (the PlayStyle that IS the skill, e.g. Precision Header = Heading, is enough). Default mode "add".
  **At most 10 skills and 5 COM styles** per player: add keeps what he has and fills up; replace takes the best of (has + wanted); rank = PlayStyle itself first, then the margin of the values above the safe bar.
  Players without EA data get skills/styles/positions from their own values and position (validation: skills 51 %, styles 75 %, positions 61 % precision / 84 % recall, in-sample).
* Backups before every write; `write_all` verifies by reading the file again and restores the backup on a mismatch.

## FM list (FMInside CSV lists)
* `flconv/lib/fmdb.py` reads every `*.csv` that starts with `UID;` from `<data dir>/fmdb/` and `flconv/data/fmdb/` (git-ignored: scraped third-party data stays out of the public repo; FMInside's robots.txt says ai-train=no). `server.fm_row(pid)` finds the player (name, then club, then age +-1; unique only; age within 3).
* Rule (user): SoFIFA / EA FC first, FM list as the fallback, and FM always fills what EA lacks: `preview` takes the list as a pasted page when the EA match is 'none' (source 'FM list', journal src 'FM list', signature = row UID + values); `positions_for(..., fmr)` adds natural 2 / accomplished 1; `profile_for(..., fmr)` adds weak foot (`PlayerBin.set_weak_foot`, mapping fitted on 51 players: use {1:1,2:2,3:2,4:3,5:4}, acc {1:1,2:2,3:3,4:3,5:4}), foot, height. Weak foot is not sent to the Master League bridge.
* The CSV has FM attributes 1-20; the FM conversion wants the 0-99 of the page (`convert_fm` divides by 5): `fmdb.raw` multiplies by 5 (this was a 20 point error once). Calibration: `fmcal.add` takes the CSV (header `UID;`) and keepers (`gk: true` samples, own `fm_fit(samples, gk=True)`, both sides as the converter makes them); `flconv/data/fm_calib.json` ships a thinned set of 300 samples (the full 2,900 stay in the data dir); hold-out (20 %): field players 5.67 → 4.32, keepers 5.58 → 1.70 RMSE. The fit is cached per file version (`convert.fm_cal`) and cross-validates on at most 400 players (quadratic otherwise). Keepers need `Off the Ball` etc. in the list (missing ones make `missing_fm` skip them).

## Live loading into the running game (PESM-LivePatch)
* `flconv/livepatch.py` (stdlib only, PESM uses a copy) writes `<Sider>/content/pesm-livepatch/players.txt|teams.txt` after every database write (`server.live_after`); the Sider module `flconv/data/pesm-livepatch.lua` (F7 in the overlay) writes them into the game's memory. Files are NOT in memory as images: the game converts them (player table = 380 byte blocks, teams = 1680 byte objects in the order of Team.bin: squad 40 x (pid,u32) at +0, shirt numbers u16 at +330, formations 99 byte at +784/+944). Found with `tools/dev/` (needle search, memory dump); line-up swaps for two clubs verified in the game.
* Live (attributes confirmed in the game 2026-11-23): 25 attributes, line-up, shirt numbers, formations. Restart needed: skills/COM/positions/style/body, names, transfers. Not live-patched: Competition/CompetitionEntry (not needed).
* Set-up needs the user's OK: `server.lp_status` / `lp_install` (`/api/livepatch`, notice bottom right in the UI): copies the module, adds `lua.module = "pesm-livepatch.lua"` after the last active module line of sider.ini (backup `sider.ini.bak-fcfl-<time>`, line endings kept); a shipped newer module replaces an installed older one silently. Overlay texts are English. Test: `tests/test_lp_install.py`.
* The module empties its patch files at every start (the game loads the files as they are then). Sider's Lua has no `pcall` (shim in the module); keys only reach the module whose overlay page is shown.

## Master League mode (Gaffer bridge, NOT worked on any more, left in the app)
* The bridge dir is `<Sider>/content/ml-immersion/bridge` (`growth.csv` commands `tx,pid,field,set,value`; answers in `growth-result.csv`, CRLF; `players_dump.bin` = 380 byte blocks of the running game after F7).
* Writes go through `GrowthBridge.lua` (Sider module, version **1.27** in Gaffer pc512e): attributes (25), `B<bit>` skills/COM, `P<bit>` position levels (2 bit, 0..2), `Style`. Only values that differ from the dump are sent.
  Big writes are chunked (`ML_CHUNK=20000`, package by package, compaction of `growth.csv`, `/api/ml/status|job|cancel`). **A huge `growth.csv` once kept the game at a black screen at start: never queue more than a few thousand lines at once.**
* **Not written into the running game**: names, height, weight, foot, weak foot.
* Gaffer calls are expensive: `gaffer_date()` (`/api/state`, up to 25 s) at most every 5 min, `gaffer_list()` (`/api/players`, minutes) at most every 30 min, both in the background, failed calls not repeated for 2 min (`_cached(..., min_age=)`).
* The Gaffer side (modules, patches, update procedure) lives in `~/Projects/gaffer-linux` (own CLAUDE.md/PATCHES.md there). The Lua module there must keep the converter's fields when Gaffer updates it (`rebase450/edits/bruecke.py`).

## Open / ideas
* Weak foot writing (offsets known, not written); height/weight/foot into the running game (offsets in the game block unverified).
* FC27 PlayStyles for all players and an FM27 data export (data source missing; the user would build it in if someone has one).
* Lineups/shirt numbers FOUND (shown in the club view): in `PlayerAssignment.bin` `k`: shirt number = (k & 127) + 1 (matches EA FC pages), order in the line-up = (k >> 10) & 63, 0..10 = starting eleven, rest = bench/reserves (800 of 800 teams: unique, order 0 is the GK, exactly one GK in the XI). The formation is read (in the club view) and written live by PESM-LivePatch (not into the file by the converter): `Tactics.bin` (12 byte: id|team|packed bits, 2 per team) -> `TacticsFormation.bin` (id|position code|depth|width|place=set*16+slot, 3 sets x 11); first record, set 0 fits the XI best (80 % same position, others 60-73 %), found by PESM (`~/Projects/pesm`, `pesm/fl/taktikdb.py`); the packed bits and the meaning of the other sets/records are open, the club view draws it (`Meta.formation`); the in-game body fields (Height byte 0, Weight byte 1, Foot bit 191, weak foot use bit 280 / acc bit 276 of the 380 byte block) are written through the bridge (weak foot not yet).
* Planned: an updated forum post (Evo-Web, BBCode) for v0.4.0, only after asking.

## Not verified (as of the last session)
* Profile writing through the bridge was verified offline only (bits agree with `Player.bin` for 6,000 players: positions and style 100 %, skills 5 of 252,000 differ); never seen inside the running game.
* The Windows build was never run. Nothing of the new `Player.bin` fields was tested inside the game.
