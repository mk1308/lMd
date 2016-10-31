#!/usr/bin/python
# -*- coding: utf-8 -*-

import re, shlex, sys, os.path as p, datetime as dt
from calendar import Calendar
from BeautifulSoup import BeautifulSoup as BS
from urllib import urlopen
from urlparse import urlparse
from jinja2 import Template
import threading, locale
from contextlib import contextmanager

class Page:

  def __init__( self, pname=None, template_name=None, **args):
    if template_name: self.template_name=template_name
    self.load_template( self.template_name )
    self.page_name = pname
    self.dic = args if args else dict()
    
  def get_content( self ):
    return self.dic
    
  def make( self, fname=None, **args ):
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
    f=open( fname )
    s = f.read()
    f.close()
    self.template = Template( s.decode('utf8') )

  def fetch_soup( self, fname ):
    print fname
    try:
      f=urlopen( fname )
    except Exception:
      print "Could not fetch %s" % fname
      return
    p=f.read()
    f.close()
    return BS( p )
    
  def render_template( self, **args):
    return self.template.render(**args).encode('utf8')
  
  def dump( self, text ):
    g = open( self.page_name, 'w' )
    g.write( text )
    g.close()

class IndexPage( Page ):

  template_name = 'res/page.html'

  def parse( self, soup ):
    args = dict(
      title='Le Monde Diplomatique',
      charset='utf8',
      builtdate = dt.datetime.now().strftime('%c'))
    articles = []
    c = soup.find('div',{'id':'content'})
    date = c.strong.string
    args.update(date=date)
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

  template_name = 'res/article-web.html'

  def parse( self, soup ):
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

def make_paper( root, date, is_online=True ):
  '''
  Produziert die komplette Ausgabe als xhtml
  '''
  src_root = "http://monde-diplomatique.de" if is_online else "monde-diplomatique.de"
  index_path = "%s/archiv-text?text=%s" % (src_root,date)
  href_index = "../index.html"
  index = IndexPage('%s/index.html' % root )
  index.make( index_path, stylesheet = 'res/index_styles.css', logo = 'res/logo.png' )
  article_refs = map( lambda entry : entry['href'], index.get_content()['articles'] )
  i=0
  while i < len(article_refs):
    src_path = '%s/%s' % (src_root,article_refs[i])
    target_path = '%s/%s' % (root,article_refs[i])
    next_path = '%s/%s' % (src_root,article_refs[ (i+1) % len(article_refs) ])
    next_target = '%s' % (p.basename( next_path )) 
    article=ArticlePage( target_path,'res/article-book.html', stylesheet = '../res/index_styles.css', date = date )
    article.make(src_path,home=href_index,next=next_target)
    i+=1

cal = Calendar()
    
def get_issue_date(y=None,m=None):
  today = dt.date.today()
  if not y:
    y=today.year
  if not m:
    m=today.month -1
  dates= map(lambda w:w[get_wd(y,m)],cal.monthdayscalendar(y,m))
  d = dates[1] if dates[1] > 6 else dates[2]
  return dt.date(y,m,d)

def get_wd(y,m):
  return 3 if y > 2014 or y == 2014 and m > 3 else 4

LOCALE_LOCK = threading.Lock()

@contextmanager
def setlocale(name):
  with LOCALE_LOCK:
    saved = locale.setlocale(locale.LC_ALL)
    try:
      yield locale.setlocale(locale.LC_ALL, name)
    finally:
      locale.setlocale(locale.LC_ALL, saved)

if __name__=='__main__':
  from flask import Flask, request, url_for, send_from_directory, redirect
  from os import path
  
  curdir = path.abspath('.')
  app = Flask('LMd',static_folder=curdir+'/res')
  content=dict()
  src_root = "http://monde-diplomatique.de"
  font_folder = curdir+'/res/fonts'
  pubdate = ' '
  
  @app.route('/')
  def index():
    '''
    Die Überblicksseite mit den links zu den Ausgaben
    '''
    issues_page = Page(
        template_name = "res/entry-page.html",
        charset = "utf8",
        stylesheet = url_for('static',filename='index_styles.css'), 
        logo = url_for('static',filename='logo.png') )
    # Schleife mit aktuellem Monat initialisieren
    m = dt.date.today().month
    issues = list()
    while m > 0:
      dateobj = get_issue_date( m=m )           # Bestimme Ausgabedatum
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
    # send_static_file will guess the correct MIME type
    return app.send_static_file( path )
  
  @app.route('/rss/<date>')
  def get_rss(date):
    pubdate = date
    logo = url_for('static',filename='logo.png')
    issue_path = "%s/archiv-text?text=%s" % (src_root, date)
    issue = IndexPage(template_name='res/rss.xml')
    with setlocale( 'en_US.UTF-8' ):
      pubdate = dt.datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
    response = issue.make( issue_path, logo = logo, pubdate = pubdate )
    return response
  
  @app.route('/<date>')
  def get_issue(date):
    pubdate = date
    stylesheet = url_for('static',filename='index_styles.css')
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
    stylesheet = url_for('static',filename='article_styles.css')
    stylesheet_content = url_for('static',filename='index_styles.css')
    stylesheet_foundation = url_for('static',filename='res/css/foundation.css')
    js_foundation = url_for('static',filename='res/js/vendor/foundation.js')
    js_jquery = url_for('static',filename='res/js/vendor/jquery.js')
    js_what_input = url_for('static',filename='res/js/vendor/what-input.js')
    js_app = url_for('static',filename='res/js/app.js')
    article_path = "%s/artikel/%s" % (src_root,article)
    article_i = ArticlePage( )   
    print 'Artikel %s' % article 
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

  app.run(debug=True,port=8000)

  
