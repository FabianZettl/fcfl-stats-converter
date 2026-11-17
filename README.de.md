# FL Stats Converter (Deutsch)

Rechnet die Werte von **EA SPORTS FC** (und von **FMInside**- und **SoFIFA**-Seiten) in die Spielerdatenbank von **Football Life** um
(`Player.bin`, die 25 Attribute von PES 21 / eFootball): für **einen Spieler, einen Verein, eine Liga oder die ganze Datenbank**,
mit **Backup vor jedem Schreiben**, Prüfung danach und Wiederherstellung per Klick.

Du gibst den Pfad zu deiner `Player.bin` an, das Tool vergleicht deine Datenbank mit den mitgelieferten EA-FC-Daten, zeigt jede Änderung
(Attribut, alt → neu, mit Begründung) und bietet an, sie zu schreiben.

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
