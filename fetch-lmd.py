#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse, subprocess as sp,re, shlex, os, sys, os.path as p, tarfile
from datetime import date
from uuid import uuid4
from lmd import make_paper, get_issue_date

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description="Holt LMD Ausgabe aus Jahr y und Monat m")
  parser.add_argument("-l", "--fetch_local_files", help="Falls die Ressourcen lokal vorhanden sind", action='store_true')
  parser.add_argument("-m", "--month", help="Nummer des Monats", type=int, default=None)
  parser.add_argument("-y", "--year", help="vierstellige Jahreszahl", type=int, default=None)
  args = parser.parse_args()
  y, m, is_online = args.year, args.month, not args.fetch_local_files

  # Berechne Erscheinungsdatum...
  issue_date = get_issue_date(y,m)
  
  if issue_date > date.today():
    print "\nDas voraussichtliche Erscheinungsdatum ist der %s!\n" % issue_date.strftime('%d.%m.%Y')
  else:
    datestring = issue_date.strftime('%Y-%m-%d')
    
    # Erzeuge Verzeichnisstruktur
    dirname = '%s/.%s' % ( p.expanduser('~'), uuid4() )
    tzip = tarfile.open('res/res.tar.gz')
    tzip.extractall( dirname )

    # Hole Seiten und parse in ein für calibre verwertbares Format
    make_paper( dirname, datestring , is_online )

    # in ein ebook konvertieren...
    src = dirname + '/index.html'
#    src = 'http://localhost:5000/%s' % datestring
    target = 'lmd%s.epub' % issue_date.strftime('%Y%m%d')
    cover = issue_date.strftime('https://dl.taz.de/titel/%Y/lmd_%Y_%m_%d.120.jpg')
    cmd = '/usr/bin/ebook-convert %(src)s %(target)s --cover=%(cover)s --chapter-mark=none --dont-split-on-page-breaks --page-breaks-before "/"'
    args = shlex.split( cmd % dict( src=src, target=target ,cover=cover ) )
    process = sp.Popen( args , stdout=sp.PIPE, stderr=sp.STDOUT )
    while process.poll() is None:
      sys.stdout.write(process.stdout.readline())
    
#    # Aufräumen...
#    for root, dnames, fnames in os.walk( dirname ):
#      for name in fnames:
#        os.remove( '%s/%s' % (root, name) )
#                 
#    for root, dnames, fnames in os.walk( dirname ):
#      for name in dnames:
#        os.rmdir( '%s/%s' % (root, name) )
#    
#    os.rmdir( dirname )
    

