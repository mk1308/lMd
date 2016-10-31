LMD
===

Skript um von der Site monde-diplomatique.de archivierte Ausgaben entweder im neuen Kleid per flask-app oder als eBook zu ziehen.

lmd.py enthält dazu die erforderlichen Parser und läuft auch als flask app.
fetch-lmd.py konvertiert in ein epub und nutzt dazu ebook-convert (calibre).
usage: fetch-lmd.py [-h] [-l] [-m MONTH] [-y YEAR]

Holt LMD Ausgabe aus Jahr y und Monat m

optional arguments:
  -h, --help            show this help message and exit
  -l, --fetch_local_files
                        Falls die Ressourcen lokal vorhanden sind
  -m MONTH, --month MONTH
                        Nummer des Monats
  -y YEAR, --year YEAR  vierstellige Jahreszahl
  
Wenn nichts weiter angegeben ist, wird automatisch die letzte vollständig verfügbare Ausgabe gezogen. wenn nur der Monat angegeben ist, die Ausgabe dieses Monats im aktuellen Jahr, wenn verfügbar.

