#!/usr/bin/python
# -*- coding: utf-8 -*-
################################################################################
#
# Die Klassen Page mit ihren Unterklassen dienen der Erzeugung von Web content.
# Die Funktion make_paper() dient der Erzeugung der XHTML-Dateien zur 
# Konvertierung in ein epub durch calibre.
# Einige Hilfsfunktionen dienen zB der Berechnung des Ausgabedatums einer
# LeMondeDiplo-Ausgabe, also letztendlich der Berechnung der URLs.
# Die Flask-App schließlich wird nur gebraucht, wenn der Appserver gestartet
# wird. Dies kann mit folgenden Optionen erfolgen. 
# 
# Usage: python lmd.py [-p n] [--options 'key1=value1,...'] [-d] [-o]
#
#  -p,  --port n      n ist Port des Servers, default ist 8000
#       --options kv  Weitere Flask-Server-Optionen als kommaseparierte kv-Paare
#  -d,  --debug       Schaltet debug mode ein
#  -o,  --open        Öffnet den Server für LAN und ggf. WAN
#
################################################################################

import re, shlex, sys, os.path as p, datetime as dt
from calendar import Calendar
from BeautifulSoup import BeautifulSoup as BS
from urllib import urlopen
from urlparse import urlparse
from jinja2 import Template
import threading, locale
from contextlib import contextmanager

dirname_templates     = "templates"
dirname_tpl_res       = "template_ressources"
tpl_entry_page        = "%s/entry-page.html" % dirname_templates
tpl_index             = "%s/index.html" % dirname_templates
tpl_article_web       = "%s/article-web.html" % dirname_templates
tpl_article_book      = "%s/article-book.html" % dirname_templates

class Page:
  '''
  Oberklasse, die ein Template und einen Parser für das Web-Scraping enthält.
  Nutzung etwa so:
  
  p=Page()
  response = p.make( web-scrape-url )
  
  oder
  
  p=Page()
  response = p.make( Wertepaare )
  
  Die vererbten Klassen enthalten jeweils ein Standard-Template, das während der
  Initialisierung überschrieben werden kann. In den vererbten Klassen muss die
  Funktion parse() überschrieben werden, damit Wertepaare aus der von 
  web-scrape-url bezogenen Seite extrahiert werden können. Diese können auch 
  direkt übergeben werden.
  '''

  def __init__( self, pname=None, template_name=None, **args):
    '''
    pname: Name der Datei, in welche eine zu erzeugende Seite gespeichert werden soll
    template_name: Dateipfad des zu ladenden Templates
    args: an das Template zu übergebende Wertepaare
    '''
    if template_name: self.template_name=template_name
    self.load_template( self.template_name )
    self.page_name = pname
    self.dic = args if args else dict()
    
  def get_content( self ):
    '''
    Gibt alle zwischengespeicherten Wertepaare zurück
    '''
    return self.dic
    
  def make( self, fname=None, **args ):
    '''
    Erzeugt das HTML auf Basis der übergebenen/zwischengespeicherten Wertepaare
    und speichert diese, falls das Template einen Pfad dafür bereit hält. Gibt 
    das Ergebnis als String zurück.
    fname = url der zu holenden und parsenden Seite
    '''
    if args:
      self.dic.update(**args)
    if fname:
      soup = self.fetch_soup( fname )
      self.parse( soup )
    response = self.render_template(**self.dic)
    if self.page_name:
      self.dump( response )
    return response
    
  def load_template( self, fname ):
    '''
    Lädt ein Template.
    fname: Dateipfaddes zu ladenden Templates
    '''
    f=open( fname )
    s = f.read()
    f.close()
    self.template = Template( s.decode('utf8') )

  def fetch_soup( self, fname ):
    '''
    Holt eine Seite und gibt diese als BeautifulSoup zurück
    fname: URL der zu parsenden Seite
    '''
    try:
      f=urlopen( fname )
    except Exception:
      log.error( "Could not fetch %s", fname )
      return
    p=f.read()
    f.close()
    return BS( p )
    
  def render_template( self, **args):
    """
    rendered ein Template auf Basis der übergebenen Wertepaare
    """
    return self.template.render(**args).encode('utf8')
  
  def dump( self, text ):
    """
    Speichert text in eine Datei. Der Pfad zu dieser Datei sollte bekannt sein
    """
    g = open( self.page_name, 'w' )
    g.write( text )
    g.close()
  
  def parse( self, soup ):
    '''
    Extrahiert aus einer wundervollen Suppe die zur Erzeugung eines Templates
    erforderlichen Wertepaare und speichert diese in self.dic zwischen. Muss 
    in Unterklasse erledigt werden.
    soup: BeautifulSoup-Objekt. In der Regel von einer geholten Seite.
    '''
    pass

class IndexPage( Page ):
  """
  Template für die Indexseite.
  """

  template_name = '%s/index.html' % dirname_templates

  def parse( self, soup ):
    '''
    Parsed die Übersichtsseite mit den Artikel-Links
    '''
    args = dict(
      title='Le Monde Diplomatique',
      charset='utf8',
      builtdate = dt.datetime.now().strftime('%c'))
    articles = []
    c = soup.find('div',{'id':'content'})
#    date = c.strong.string
#    args.update(date=date)
    toc = c.ul
    for item in toc.findAll('li'):                  
      if item.a:
        url = urlparse( item.a['href'] ).path
        article = dict(
          href = url.replace('/','',1) if url.startswith('/') else url,
          guid = re.search('(\d+)', url).group(1) if re.search('(\d+)', url) else '',
          title = item.a.strong.string.strip() )
        item.a.strong.extract()
        article.update(abstract=item.renderContents())
        author = ''
        for entry in item.findAll('em'):
          author += entry.string
          entry.extract()
        article.update(
          author = author,
          description = item.text )
        articles.append( article )
    args.update(articles=articles)
    self.dic.update(**args)

class ArticlePage( Page ):
  '''
  Template für eine Artikelseite. Default ist die Web-Darstellung
  '''

  template_name = '%s/article-web.html' % dirname_templates

  def parse( self, soup ):
    '''
    Parsed eine Artikelseite
    '''
    args = dict(charset='utf8')
    c = soup.find('div',{'id':'content'})
    args.update(teaser=c.find('p',{'class':'Unterzeile'}).string if c.find('p',{'class':'Unterzeile'}) else '' )
    args.update(title=c.find('p',{'class':'Titel'}).string)
    args.update(author=c.find('p',{'class':'Korrespondent'}).string if c.find('p',{'class':'Korrespondent'}) else '' )
    args.update(initial=c.find('p',{'class':'Initial'}).renderContents() if c.find('p',{'class':'Initial'}) else '')
    p_list=c.findAll('p')
    f_list=filter(lambda p:p['class']=='Fussnote' if p.has_key('class') else False,p_list)
    footnotes = ''
    for f in f_list: footnotes+=str(f)
    footnotes=footnotes.replace('\"Fussnote','\"c-image__caption')
    args.update(footnotes=footnotes)
    c_list=filter(lambda p:p['class']=='Brot' or p['class']=='BrotO' or p['class']=='Zwischentitel' if p.has_key('class') else False,p_list)
    first = c_list.pop(0).renderContents()
    args.update(first_letter = first[0])
    re_first_word=re.compile('[\wüÜöÖäÄß-]*')
    match = re_first_word.match(first[1:])
    args.update(chunk = match.group())
    args.update(first = first[1+match.end():])    
    content=''
    for c in c_list: content+=str(c)
    content = content.replace('\"Brot\"','\"c-article-body\"').replace('\"BrotO\"','\"c-article-body\"').replace('\"Zwischentitel\"','\"c-article-body__subheadline\"')
    args.update(content=content)
    self.dic.update(**args)

def make_paper( target, date, is_online=True ):
  '''
  Produziert die komplette Ausgabe als xhtml. Baustelle: Das richtige Handling der Links.
  target:     Verzeichnis, in welchem das generierte xhtml abgelegt werden soll
  date:     Datum der zu erzeugenden Ausgabe im Format, in welchem es abgefufen werden kann
  is_online: True, wenn inline abgerufen werden soll 
  '''
  local = "monde-diplomatique.de"
  # Falls offline nehme lokale Dateien:
  src_root_url = "http://monde-diplomatique.de" if is_online else local 
  src_index_path = "%s/archiv-text?text=%s" % (src_root_url,date) # url des Index der gewünschten Ausgbe
  # Als erstes die Indexseite machen...
  target_index = IndexPage('%s/index.html' % target )
  target_index.make( src_index_path, stylesheet = 'res/index_styles.css', logo = 'res/logo.png' )
  # ...und dann die Links zu den Artikeln extrahieren und die Artikelseiten machen
  article_refs = map( lambda entry : entry['href'], target_index.get_content()['articles'] )
  i=0
  while i < len(article_refs):
    src_url = '%s/%s' % (src_root_url,article_refs[i])
    target_path = '%s/%s' % (target,article_refs[i])
    next_path = '%s/%s' % (src_root_url,article_refs[ (i+1) % len(article_refs) ])
    next_target = '%s' % (p.basename( next_path )) 
    article=ArticlePage( target_path, tpl_article_book, 
      stylesheet = '../res/stylesheet.css', 
      date = date,
      home = "../index.html",
      next=next_target )
    article.make( src_url )
    i+=1

cal = Calendar()
    
def get_issue_date(y=None,m=None):
  '''
  Berechne das Datum der jeweiligen Monatsausgabe
  Wenn nichts angegeben ist, das Datum der aktuellen Ausgabe.
  Datum wird als datetime.date-Objekt zurückgegeben
  '''
  today = dt.date.today()
  if not y:
    y=today.year
  if not m:
    m=today.month
  dates= map(lambda w:w[get_wd(y,m)],cal.monthdayscalendar(y,m))
  d = dates[1] if dates[1] > 6 else dates[2]
  return dt.date(y,m,d)

def get_wd(y,m):
  '''
  Der Erscheinungstag war vor April 2014 immer der Mittwoch, seitdem der Donnerstag
  '''
  return 3 if y > 2014 or y == 2014 and m > 3 else 4

LOCALE_LOCK = threading.Lock()

# RSS-Dateien wollen das Datum in einem bestimmten Format, das nicht dem deutschen
# entspricht. Deshalb für das temporäre Umschalten der Sprachungebung diese Funktion.
@contextmanager
def setlocale(name):
  '''
  Zum Einschalten der Sprachumgebung name
  name= en_US oder de_De
  '''
  with LOCALE_LOCK:
    saved = locale.setlocale(locale.LC_ALL)
    try:
      yield locale.setlocale(locale.LC_ALL, name)
    finally:
      locale.setlocale(locale.LC_ALL, saved)

################################################################################
#
# Die lMd-Webapp
#
################################################################################

if __name__=='__main__':
  '''
  Webapp definieren und Appserver starten
  '''
  from flask import Flask, request, url_for, send_from_directory, redirect
  from os import path
  
  curdir = path.abspath('.')
  app = Flask('LMd',static_folder= '%s/%s' % ( curdir, dirname_tpl_res))
  content=dict()
  src_root = "http://monde-diplomatique.de"
  font_folder = '%s/%s/fonts' % ( curdir, dirname_tpl_res )
  pubdate = ' '
  
  @app.route('/')
  def index():
    '''
    Die Überblicksseite mit den links zu den Ausgaben
    '''
    issues_page = Page(
        template_name = tpl_entry_page,
        charset = "utf8",
        stylesheet = url_for('static',filename='css/index_styles.css'), 
        logo = url_for('static',filename='logo.png') )
    # Schleife mit aktuellem Monat initialisieren
    m = dt.date.today().month
    issues = list()
    while m > 0:
      dateobj = get_issue_date( m=m )           # Bestimme Ausgabedatum
      if dateobj > dt.date.today():
        # Nichts zu tun, wenn das Ausgabedatum noch vor uns liegt
        m = m-1
        continue
      datestring = dateobj.strftime('%Y-%m-%d') # ...für den link
      date = dateobj.strftime('%d. %B %Y')      # ...für den Text
      href = '/'+datestring     
      issues.append( dict(href=href,date=date))
      m = m-1
    response = issues_page.make( articles=issues )
    content['issues'] = issues
    return response

  @app.route('/res/<path>')
  def static_proxy(path):
    '''
    Alles unterhalb template_ressources
    '''
    # send_static_file will guess the correct MIME type
    return app.send_static_file( path )
  
  @app.route('/rss/<date>')
  def get_rss(date):
    '''
    Gibt einen Feed zurück
    '''
    pubdate = date
    logo = url_for('static',filename='logo.png')
    issue_path = "%s/archiv-text?text=%s" % (src_root, date)
    issue = IndexPage(template_name='%s/rss.xml' % dirname_templates )
    with setlocale( 'en_US.UTF-8' ):
      pubdate = dt.datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
    response = issue.make( issue_path, logo = logo, pubdate = pubdate )
    return response
  
  @app.route('/<date>')
  def get_issue(date):
    '''
    Gibt die Indexseite der Ausgabe mit Datum date zurück
    '''
    pubdate = date
    stylesheet = url_for('static',filename='css/index_styles.css')
    logo = url_for('static',filename='logo.png')
    issue_path = "%s/archiv-text?text=%s" % (src_root, date)
    issue = IndexPage()
    content['current']=issue.get_content()
    i=0
    response = issue.make( issue_path, stylesheet = stylesheet, logo = logo )
    article_refs = map( lambda entry : entry['href'], issue.get_content()['articles'] )
    while i < len(article_refs):
      next_target = article_refs[ (i+1) % len(article_refs) ]
      next_path = p.basename( next_target )
      content[article_refs[i]] = next_path
      i+=1
    return response
  
  @app.route('/artikel/<article>')
  def get_article(article):
    '''
    Liefert eine Artikelseite aus
    '''
    stylesheet = url_for('static',filename='css/article_styles.css')
    stylesheet_content = url_for('static',filename='css/index_styles.css')
    stylesheet_foundation = url_for('static',filename='css/foundation.css')
    js_foundation = url_for('static',filename='js/vendor/foundation.js')
    js_jquery = url_for('static',filename='js/vendor/jquery.js')
    js_what_input = url_for('static',filename='js/vendor/what-input.js')
    js_app = url_for('static',filename='js/app.js')
    article_path = "%s/artikel/%s" % (src_root,article)
    article_i = ArticlePage( )   
    return article_i.make(article_path,
        logo = url_for('static', filename="logofficiel-enlong.png"),
        issues = content['issues'],
        current = content[ 'current' ],
        next=content[ 'artikel/' + article ],
        home = url_for('index',filename = pubdate),
        stylesheet = stylesheet,
        stylesheet_content = stylesheet_content,
        stylesheet_foundation = stylesheet_foundation,
        js_foundation = js_foundation,
        js_jquery = js_jquery,
        js_what_input = js_what_input,
        js_app = js_app )
  
  @app.route('/fonts/<fname>')
  def get_fonts(fname):
    return send_from_directory( font_folder, fname )

  # configure Flask logging
  from logging import FileHandler, DEBUG
  logger = FileHandler('error.log')
  app.logger.setLevel(DEBUG)
  app.logger.addHandler(logger)
    
  # log Flask events
  from time import asctime
  app.logger.debug(u"Flask server started " + asctime())
  @app.after_request
  def write_access_log(response):
      app.logger.debug(u"%s %s -> %s" % (asctime(), request.path, response.status_code))
      return response

  import argparse
    
  server = argparse.ArgumentParser(description="Startet den Appserver")
  server.add_argument("-p", "--port", help="Port des Servers", type=int, default=8000)
  server.add_argument("--options", help="Weitere Flask-Server-Optionen als kommaseparierte key=value-Paare", type=str, default=None)
  server.add_argument("-d", "--debug", help="Schaltet debug mode ein", action='store_true')
  server.add_argument("-o", "--open", help="Öffnet den Server für LAN und ggf. WAN", action='store_true')
  opts = server.parse_args()
  server_opts = dict(debug=opts.debug,port=opts.port)
  port = opts.port
  if opts.debug:
    log.setLevel( logging.DEBUG )
  if opts.open: 
    server_opts.update(host='0.0.0.0')
  if opts.options:
    key_value_pattern = re.compile('[a-zA-Z0-9_]*=.*')
    kvs=opts.options.split(',')
    for kv in kvs:
      if key_value_pattern.match( kv ):
        key, value = kv.split('=')
        if value.isdigit(): value = int( value )
        if value=='True': value = True 
        if value=='False': value = False 
        server_opts.update({key:value})
      else:
        log.error('%s will be ignored, because it is not a key value pair!',kv)

  app.run( **server_opts )

  
