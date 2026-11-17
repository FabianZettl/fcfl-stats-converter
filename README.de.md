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
* **Schreiben in eine laufende Master League** (optional, braucht **Gaffer**): die 25 Attribute und (mit Profil/Skills) Skills, COM-Stile, Spielstil und Positionen gehen über die Bridge von Gaffer ins Spiel (braucht das aktualisierte Modul GrowthBridge.lua 1.3, Spiel danach neu starten), in Paketen mit Fortschrittsbalken (siehe englische README).
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
