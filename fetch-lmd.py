#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse, subprocess as sp,re, shlex, os, sys, os.path as p, tarfile, logging
from datetime import date
from uuid import uuid4
from lmd import make_paper, get_issue_date, get_current_issue_date


dirname_output      = "epub"            # Unterverzeichnis für die erzeugten epubs
dirname_ressources  = "epub-ressources" # Das Verzeichnis mit der komprimierten vorgefertigten Struktur
tarfile_name        = "res.tar.gz"      # Die komprimierte Struktur
    
if __name__ == '__main__':
  parser = argparse.ArgumentParser(description="Holt LMD Ausgabe aus Jahr y und Monat m")
  parser.add_argument("-l", "--fetch_local_files", help="Falls die Ressourcen lokal vorhanden sind", action='store_true')
  parser.add_argument("-m", "--month", help="Nummer des Monats", type=int, default=None)
  parser.add_argument("-y", "--year", help="vierstellige Jahreszahl", type=int, default=None)
  parser.add_argument("-d", "--debug", help="schaltet Debug-Modus ein", action='store_true' )
  args = parser.parse_args()
  y, m, is_online = args.year, args.month, not args.fetch_local_files

  log_level=logging.DEBUG if args.debug else logging.ERROR
  log = logging.getLogger(__name__)
  logging.basicConfig( 
      name = __name__,
      format='%(asctime)s[%(name)s][%(threadName)s]%(levelname)s: %(message)s',
      level=log_level )


  # Berechne Erscheinungsdatum...
  issue_date = get_issue_date(y,m)
  log.debug( "Das gewählte Erscheinungsdatum ist der %s", issue_date.strftime('%d.%m.%Y') )
  
  if issue_date > date.today():
    o = raw_input( "\nDas gewählte Erscheinungsdatum liegt in der Zukunft.\nAktuelle Ausgabe laden? (J/n)\n" )
    if o.capitalize() == 'J':
      issue_date = get_current_issue_date()
      print "Erscheinungsdatum der aktuellen Ausgabe ist der %s" % issue_date.strftime('%d.%m.%Y')
    else:
      issue_date = None
      log.debug( "Beende Prozess..." )

  if issue_date:
    log.debug( "Erzeuge epub der Ausgabe vom %s", issue_date.strftime('%d.%m.%Y') )
    datestring = issue_date.strftime('%Y-%m-%d')
  
    # Erzeuge Verzeichnisstruktur für das zu erzeugende epub einschließlich stylesheets etc.
    dirname = '%s/.%s' % ( p.expanduser('~'), uuid4() )
    tzip = tarfile.open( '%s/%s' % (dirname_ressources, tarfile_name) )
    tzip.extractall( dirname )
    log.debug( "Verzeichnisstruktur für epub in %s erzeugt.", dirname )

    # Hole Seiten und parse in ein für calibre verwertbares Format
    make_paper( dirname, datestring, is_online )
    log.debug( "XHTML-Dateien zur Erzeugung des epub in %s fertiggestellt.", dirname )

    # in ein ebook konvertieren...
    src = dirname + '/index.html'
#    src = 'http://localhost:5000/%s' % datestring
    target_name = 'lmd%s.epub' % issue_date.strftime('%Y%m%d')
    target      = '%s/%s' % ( dirname_output, target_name )
    cover = issue_date.strftime('https://dl.taz.de/titel/%Y/lmd_%Y_%m_%d.120.jpg')
    cmd = '/usr/bin/ebook-convert %(src)s %(target)s --cover=%(cover)s --chapter-mark=none --dont-split-on-page-breaks --page-breaks-before "/"'
    args = shlex.split( cmd % dict( src=src, target=target ,cover=cover ) )
    process = sp.Popen( args , stdout=sp.PIPE, stderr=sp.STDOUT )
    log.debug("Erzeuge epub...\n")
    while process.poll() is None:
      sys.stdout.write(process.stdout.readline())
    log.debug("Fertig!")
    
    # Aufräumen...
    for root, dnames, fnames in os.walk( dirname, topdown=False ):
      for name in fnames:
        log.debug("removing %s/%s..." % (root, name))
        os.remove( '%s/%s' % (root, name) )
      for name in dnames:
        log.debug("removing %s/%s..." % (root, name))
        os.rmdir( '%s/%s' % (root, name) )
    
    os.rmdir( dirname )
    log.debug( "Temporäres Verzeichnis %s wieder gelöscht", dirname )
    

