# FCFL - Stats Converter (Deutsch)

Rechnet die Werte von **EA SPORTS FC** (und von **FMInside**- und **SoFIFA**-Seiten) in die Spielerdatenbank von **Football Life** um
(`Player.bin`, die 25 Attribute von PES 21 / eFootball): für **einen Spieler, einen Verein, eine Liga oder die ganze Datenbank**,
mit **Backup vor jedem Schreiben**, Prüfung danach und Wiederherstellung per Klick.

Du gibst den Pfad zu deiner `Player.bin` an, das Tool vergleicht deine Datenbank mit den mitgelieferten EA-FC-Daten, zeigt jede Änderung
(Attribut, alt → neu, mit Begründung) und bietet an, sie zu schreiben.

## Was drin ist

* **Aktive Datenbank mit EA-FC-Werten aktualisieren** – der Hauptzweck. Liga, Verein, Spieler oder die ganze Datenbank, automatisch in den mitgelieferten EA-FC-Daten gefunden.
* **Manueller Konverter für SoFIFA und FMInside** – Spielerseite öffnen, alles markieren (Strg+A), kopieren (Strg+C), im Tool einfügen: es rechnet die Werte (SoFIFA) bzw. die Football-Manager-Attribute (FMInside) um.
  Suchknöpfe für beide Seiten bei jedem Spieler.
* **Manuelle Anpassungen** – gewünschtes Overall eines Spielers einstellen (die Attribute werden angepasst), einzelne Attribute, Namen und Trikotnamen ändern.
* **Größe, Gewicht und starker Fuß** des EA-Eintrags werden mitgeschrieben (Schalter in der Seitenleiste), mit Icons in der Profil-Karte des Spielers, eigene Werte sind möglich.
* **Skills, COM-Stile und Playing Style** aus den EA-FC-PlayStyles (experimentell, Schalter in der Seitenleiste: off / add / replace), nach der Tabelle in [docs/PLAYSTYLE_MAPPING.md](docs/PLAYSTYLE_MAPPING.md).
* **Schreiben in eine laufende Master League** (optional, braucht **Gaffer**): die 25 Attribute und (mit Profil/Skills) Skills, COM-Stile, Spielstil, Positionen sowie Größe, Gewicht und Fuß gehen über die Bridge von Gaffer ins Spiel (braucht das aktualisierte Modul GrowthBridge.lua 1.3, Spiel danach neu starten), in Paketen mit Fortschrittsbalken (siehe englische README).
* **Datenbank-Modus**: nach dem Schreiben wird `EDIT00000000` aus dem Save-Ordner von Football Life 2027 entfernt (den Ordner gibst du an, oder du löschst die Datei selbst) (Kopie im Datenordner, `moved/`), sonst überschreibt das Spiel die neuen Werte. Der Converter liefert sein eigenes `GrowthBridge.lua` mit und gleicht es beim Start mit dem Sider-`modules`-Ordner ab.
* **Suche** nach Spielern und Teams in der Seitenleiste (ohne Umweg über das Liga-Menü).
* Ordnerauswahl, Backups mit Wiederherstellung per Klick, bereits konvertierte Spieler werden markiert und übersprungen.

**Geplant:** Positionen, schwacher Fuß, Attribut-Boni für PlayStyle+ und mehr.

## Start

Python 3.9 oder neuer (sonst nichts, nur die Standardbibliothek) **oder** der Download von der *Releases*-Seite.

```
python3 flconv/server.py        # Linux / macOS   (oder ./start.sh)
py flconv\server.py             # Windows         (oder start.bat)
```

Das Tool öffnet `http://127.0.0.1:8790/` im Browser (es lauscht nur auf deinem eigenen Rechner).

1. Im Feld *Your database* den Pfad zur `Player.bin` eintragen (Ordner mit der Datei, ein Ordner darüber oder die Datei selbst),
   bei Football Life der Ordner `pesdb`, z. B. `…/livecpk/_FL26MyWorld/common/etc/pesdb`.
2. Liga wählen, dann Verein. Gefundene Spieler zeigen `alter Overall → neuer Overall`.
3. Spieler öffnen: jedes Attribut mit Begründung, eigene Werte oder Namen eintragen, oder *Convert the club* / *Convert the whole database*.
4. Spiel beim Schreiben schließen, danach eine **neue Karriere** starten.

Einstellungen, Backups und die Kopie deiner Original-`Player.bin` liegen in `~/.local/share/fl-stats-converter` (Linux) bzw.
`%APPDATA%\FL-Stats-Converter` (Windows).

Alles Weitere (Zuordnung der Spieler, Umrechnung, Jugendbonus, Entwicklung, Sicherheit) steht in der englischen [README.md](README.md),
die Änderungen gegenüber dem PES Stats Converter in [CHANGES.md](CHANGES.md), die Datenquellen in [DATA.md](DATA.md).
Die Umrechnung geht immer von den **Originalwerten** aus (beim ersten Benutzen einer Datenbank wird eine Kopie angelegt): zweimal ausführen gibt dasselbe Ergebnis.

## FM-Liste (FMInside-Export) als Fallback und Lückenfüller

Der Converter bringt eine Liste aus FMInside mit (`flconv/data/fmdb/`, CSV, `;`, erste Spalte `UID`, eine Zeile je Spieler, etwa 10.000 Spieler, davon etwa 6.000 mit allen Werten). Eigene, neuere Listen kommen in den Ordner `fmdb` im Datenordner (`~/.local/share/fl-stats-converter/fmdb/` unter Linux; mehrere Dateien sind möglich, deine gewinnen je UID gegen die mitgelieferte). Der Converter nutzt sie so:

* **Fallback-Quelle:** Ein Spieler, den EA FC / SoFIFA nicht hat (kein Treffer), wird aus der Liste umgerechnet, wie eine eingefügte FMInside-Seite (mit der Kalibrierung unten). Ein unsicherer EA-Treffer wird nicht ersetzt, den wählst du wie bisher.
* **Positionen kommen zuerst aus FM:** Ein Spieler mit Positionsbewertungen in der Liste bekommt genau diese (*natural* = Stufe 2, *accomplished* = 1, alles andere 0; der Schattenstürmer hat keine FM-Bewertung und bleibt; seine Hauptposition bleibt auf Stufe 2). EA FC (Alternativpositionen) und das Wertemodell sind der Ersatz für Spieler ohne FM-Bewertung. Eine Zeile, die nicht zur Position des Spielers passt (ein Torwart mit dem Namen eines Stürmers), wird nicht benutzt. In der Spielerliste zeigt ein Chip *Found EAFC*, *Found FM* oder *Found EAFC & FM*.
* **Füllt, was EA FC nicht liefert:** den **schwachen Fuß** (Häufigkeit und Genauigkeit, wird in die `Player.bin` geschrieben; FM 2 / 3 / 4 ergibt 2/2, 2/3, 3/3, an 51 Spielern des Spiels angepasst), bevorzugten Fuß und Größe, wo EA FC keine hat.
* **Kalibrierung:** Die FM-Umrechnung wird je Attribut auf das Niveau der EA-FC-Umrechnung gebracht (an Spielern geprüft, die nicht zum Anpassen dienten, 20 % von 2.900 zurückgehalten: Feldspieler 5,7 → 4,3 Punkte Abstand zur EA-FC-Umrechnung, Torhüter 5,6 → 1,7; ausgeliefert ist ein ausgedünnter Satz von 300 Proben, der volle bleibt bei dir; Torhüter haben eine eigene Anpassung). Eine Liste lässt sich im Feld *FM-Kalibrierung* wie Seitentext einfügen und liefert weitere Proben.

## Änderungen ins laufende Spiel laden (PESM-LivePatch, ohne Neustart)

Schreibt der Converter `Player.bin` (Attribute) oder eine Aufstellung, legt er kleine Patch-Dateien in `<Sider>/content/pesm-livepatch/` ab und bringt das Sider-Modul
**PESM-LivePatch** mit (`flconv/data/pesm-livepatch.lua`, wird beim ersten Schreiben nach `<Sider>/modules/` kopiert). Der Datenbankordner muss unter `<Sider>/livecpk/` liegen.

1. Einmalig: beim ersten Start dieser Version fragt der Converter (Hinweis unten rechts), ob er es einrichten soll: nach deinem OK kopiert er das Modul und trägt `lua.module = "pesm-livepatch.lua"` in die `sider.ini` ein (vorher Backup der `sider.ini`). Das Spiel einmal neu starten.
2. Im Converter ändern und schreiben (oder in PESM, das dieselben Dateien nutzt).
3. Im Hauptmenü des Spiels das Sider-Overlay öffnen (Leertaste), **PESM-LivePatch** wählen (Taste `1`), **F7** drücken.
4. Overlay schließen und das Match ganz normal starten: neue Aufstellung, Rückennummern und Attribute sind da, kein Neustart.

Live geht: die 25 Attribute, Kaderreihenfolge (Aufstellung), Rückennummern, Formationen. Neustart nötig: Skills, COM-Styles, Positionen, Namen, neue oder gewechselte Spieler.

## Aufstellung und Performance (Sofascore)
* **Line-up from Sofascore** (Vereinsansicht, Datenbank-Modus): liest das letzte Spiel des Vereins und schreibt Startelf, Bank und Trikotnummern in `PlayerAssignment.bin` (Backup, Prüfung nach dem Schreiben). Die Formation selbst wird nicht geschrieben. Das Spielfeld in der Vereinsansicht zeigt die Startelf.
* **Performance since 01.09.**: Note und Sofascore-Werte (Passen, Dribbling, Defensive, Schuss, Torwart) seit dem Stand der Daten, gewichtet nach Minuten (mindestens 3 Spiele und 270 Minuten, volles Gewicht ab 900), verglichen mit dem Team-Schnitt: wer besser ist als sein Team, bekommt auf den passenden Einzelwerten bis zu +3, wer schlechter ist, bis zu -3. Das Overall bewegt sich höchstens um 2, in der Praxis um 0 oder 1. Auch die Entwicklung über die Zeit wird gewichtet: bestätigt der Spieler seine Werte, bleibt sie wie sie ist; übertrifft er sie, wächst ein junger Spieler stärker bzw. baut ein älterer weniger ab (bis zu x1,5 bzw. x0,5), untertrifft er sie, umgekehrt. Die Rechnung steht in der englischen README. Option *Live data (performance)* unter *Conversion options*; *Convert the club* wendet sie zusammen mit den anderen Optionen an.

## Browser-Button für SoFIFA und FMInside (Tampermonkey)
Statt Strg+A, Strg+C und Einfügen: `userscript/fcfl-send-player.user.js` in Tampermonkey installieren. Auf einer Spielerseite von sofifa.com oder fminside.net erscheint unten rechts der Knopf **→ FCFL**. Er schickt die Seite an den laufenden Converter (`127.0.0.1:8790`, bei anderem Port oben im Skript `FCFL` ändern), der den Spieler in deiner Datenbank über den Namen findet und die Umrechnung der Seite zeigt; ein Klick schreibt sie. Gibt es mehrere Spieler mit dem Namen, wählst du den richtigen aus.
