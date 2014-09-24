#! /usr/bin/python
# -*- coding: utf-8 -*-

import sys
import urllib
import contextlib
import re
import csv
import json
import HTMLParser

html = HTMLParser.HTMLParser()

class ISBNLookup(object):
    @classmethod
    def lookup(cls, isbn):
        for method in dir(cls):
            if method.startswith('lookup_'):
                try:
                    res = getattr(cls, method)(isbn)
                    if res is not None:
                        return res
                except Exception, e:
                    sys.stderr.write("%s: %s\n" % (method[len('lookup_'):], e))
        return ['', '']

    @classmethod
    def get_url(cls, url):
        with contextlib.closing(urllib.urlopen(url)) as f:
            return f.info(), f.read()

    @classmethod
    def lookup_www_lookupbyisbn_com(cls, isbn):
        headers, content = cls.get_url("http://www.lookupbyisbn.com/Search/Book/%s/1" % isbn)
        title = re.search(isbn + r'/1" title="Details for (.*)"', content).groups()[0].decode('utf-8')
        author = re.search(r'<u>(.*)</u>', content).groups()[0].decode('utf-8')
        return [author, title]

    @classmethod
    def lookup_google_com(cls, isbn):
         headers, content = cls.get_url("https://www.googleapis.com/books/v1/volumes?q=%s" % isbn)
         content = json.loads(content)
         title = content['items'][0]['volumeInfo']['title']
         author = ''
         if 'authors' in content['items'][0]['volumeInfo']:
             author = content['items'][0]['volumeInfo']['authors'][0]
         return [author, title]

    @classmethod
    def lookup_www_bokus_com(cls, isbn):
        headers, content = cls.get_url("http://www.bokus.com/bok/%s" % isbn)
        title = re.search(r'<span class="fn">([^<]*)</span>', content).groups()[0].decode('latin-1')
        author = re.search(r'class="author-link" [^>]*>([^<]*)</a>', content).groups()[0].decode('latin-1')
        return [author, title]

    @classmethod
    def lookup_bookdepository_co_uk(cls, isbn):
         headers, content = cls.get_url("http://www.bookdepository.co.uk/search?searchTerm=%s&search=search" % isbn)
         title = re.search(r'<span property="dc:title">([^<]*)</span>', content).groups()[0].decode('latin-1')
         author = re.search(r'<a property="dc:creator" [^>]*>([^<]*)</a>', content).groups()[0].decode('latin-1')
         return [author, title]

    @classmethod
    def lookup_bookstation_ro(cls, isbn):
         headers, content = cls.get_url("http://www.bookstation.ro/search/%s" % isbn)
         title = re.search(r'<a href="/item/[^>]*>[^<:]* : ([^</]*) / [^</]*</a>', content).groups()[0].decode('latin-1')
         author = re.search(r'<a href="/item/[^>]*>([^<:]*) : [^</]* / [^</]*</a>', content).groups()[0].decode('latin-1')
         return [author, title]

    @classmethod
    def lookup_kurslitteratur_se(cls, isbn):
         headers, content = cls.get_url("http://www.kurslitteratur.se/ISBN/%s" % isbn)
         title = re.search(r'<table id="titleinfo"><th colspan="2">([^<]*)</th><tr>', content).groups()[0].decode('utf-8')
         author = re.search(r'<h2>([^<]*)</h2>', content).groups()[0].decode('utf-8')
         return [author, title]

    @classmethod
    def lookup_biblio_com(cls, isbn):
         headers, content = cls.get_url("http://www.biblio.com/%s" % isbn)
         title = re.search(r'<h1>([^<]*)</h1>', content).groups()[0].decode('utf-8')
         author = re.search(r'<h2>by *([^<]*)</h2>', content).groups()[0].decode('utf-8')
         return [author, title]

    @classmethod
    def lookup_abebooks_com(cls, isbn):
         headers, content = cls.get_url("http://www.abebooks.com/servlet/SearchResults?isbn=%s" % isbn)
         title = re.search(r'<b><a *href="/servlet/BookDetailsPL\?bi=.*" *>([^>]*)</a></b>', content).groups()[0].decode('utf-8')
         author = re.search(r'<b><a *href="/servlet/BookDetailsPL\?bi=.*" *>.*<br/><b>*([^<]*)</b>', content).groups()[0].decode('utf-8')
         return [author, title]

    @classmethod
    def lookup_isbn2book_com(cls, isbn):
        if len(isbn) == 13 and isbn.startswith('978'):
            isbn = isbn[3:-1]
            c = sum((p+1) * int(d) for (p, d) in enumerate(isbn)) % 11
            if c == 10: c = 'X'
            isbn += str(c)
        headers, content = cls.get_url("http://isbn2book.com/q/%s" % isbn)
        title = re.search(r'<a href=".*"><font size="-1">([^>/]*) / [^>]*</font></a>', content).groups()[0].decode('latin-1')
        author = re.search(r'<a href=".*"><font size="-1">[^>/]* / ([^()>]*) \([^)>]*\)</font></a>', content).groups()[0].decode('latin-1')
        return [author, title]

    @classmethod
    def lookup_btj_se(cls, isbn):
        headers, content = cls.get_url("http://www.btj.se/default.aspx?search=%s" % isbn)
        title = re.search(r'id="ctl00_MainContent_SearchResultList_ArticleRepeat_ctl00_Article1_AbstractArticle_ArticleDetail_Image1" src=".*" alt="([^"]*)"', content).groups()[0].decode('utf-8')
        author = re.search(r'av <a href=".*">([^>]*)</a>', content).groups()[0].decode('utf-8')
        return [author, title]

    @classmethod
    def lookup_bokrecension_se(cls, isbn):
        headers, content = cls.get_url("http://www.bokrecension.se/query.php?q=%s" % isbn)
        title = re.search(r'<h1>([^>]*)</h1>', content).groups()[0].decode('utf-8')
        author = re.search(r'<a class=author href=".*">([^>]*)</a> ', content).groups()[0].decode('utf-8')
        return [author, title]

    @classmethod
    def lookup_bokborsen_se(cls, isbn):
        headers, content = cls.get_url("http://www.bokborsen.se/page-start?issearch=1&sallstr=%s" % isbn)
        title = html.unescape(re.search(r'<h1 style="font:bold 14px/1.2em arial,verdana">([^>]*)</h1>', content).groups()[0].decode('utf-8'))
        author = html.unescape(re.search(r'<strong>F&ouml;rfattare:</strong> ([^>]*)<br />', content).groups()[0].decode('utf-8'))
        return [author, title]

    #### Partial lookups

    # @classmethod
    # def lookup_adlibris_com(cls, isbn):
    #      headers, content = cls.get_url("http://www.adlibris.com/se/product.aspx?isbn=%s" % isbn)
    #      title = re.search(r'<span itemprop="name">([^<]*)</span>', content).groups()[0].decode('latin-1')
    #      author = ''
    #      return [author, title]

if __name__ == '__main__':
    if len(sys.argv) > 1:
        out = csv.writer(sys.stdout, dialect='excel')
        out.writerow(['author', 'title'])
        out.writerow([x.encode('utf-8')
                      for x in ISBNLookup.lookup(sys.argv[1])])
    else:
        rows = csv.reader(sys.stdin, dialect='excel')
        headers = rows.next()
        out = csv.writer(sys.stdout, dialect='excel')
        out.writerow(headers + ['author', 'title'])
        for row in rows:
            data = dict(zip(headers, row))
            #print data
            out.writerow(row + [x.encode('utf-8')
                                for x in ISBNLookup.lookup(data['isbn'])])
