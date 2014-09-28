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
    def test(cls):
        data = {
            "lookup_isbn2book_com": {"7500756704": [u'Herge', u'Tintin Chinese: Tintin and the Broken Ear']},
            "lookup_www_lookupbyisbn_com": {"0425256863": [u'Charles Stross', u'The Rhesus Chart (Laundry Files)']},
            "lookup_google_com": {"0425256863": [u'Charles Stross', u'The Rhesus Chart']},
            "lookup_www_bokus_com": {"0425256863": [u'Charles Stross', u'The Rhesus Chart']},
            "lookup_bookdepository_co_uk": {"0425256863": [u'Charles Stross', u'The Rhesus Chart']},
            "lookup_bookstation_ro": {"9781909489400": [u'DASHNER, JAMES', u'The Maze Runner']},
            "lookup_kurslitteratur_se": {"9780262011532": [u'Abelson, Harold', u'Structure and interpretation of computer programs']},
            "lookup_biblio_com": {"0425256863": [u'Charles Stross', u'The Rhesus Chart']},
            "lookup_abebooks_com": {"0425256863": [u'Stross, Charles', u'The Rhesus Chart (Laundry Files)']},
            "lookup_btj_se": {"9780765329110": [u'Stross, Charles', u'Rapture of the Nerds, The']},
            "lookup_bokrecension_se": {"0425256863": [u'Charles Stross', u'The Rhesus Chart (Laundry Files Novel)']},
            "lookup_bokborsen_se": {"9789147100392": [u'Andersson, Jan-Olof', u'E2000 Classic F\xf6retagsekonomi 1 L\xf6sningsbok']}
            }

        for method in dir(cls):
            if method.startswith("lookup_") and method not in data:
                print "%s UNTESTED" % (method,)

        for method, examples in data.iteritems():
            fn = getattr(cls, method)
            for isbn, value in examples.iteritems():
                try:
                    res = fn(isbn)
                except Exception, e:
                    print "%s(%s): %s" % (method, isbn, e) 
                else:
                    if res != value:
                        print "%s(%s) != %s" % (method, isbn, res)
                    else:
                        print "%s OK" % (method,)
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
        title = re.search(r'<h1><span itemprop="name">([^<]*)</span></h1>', content).groups()[0].decode('latin-1')
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
         headers, content = cls.get_url("http://bookstation.ro/search/%s" % isbn)
         title = re.search(r'<a href="/item/[^>]*>[^<:]* : ([^</]*) / [^</]*</a>', content).groups()[0].decode('latin-1')
         author = re.search(r'<a href="/item/[^>]*>([^<:]*) : [^</]* / [^</]*</a>', content).groups()[0].decode('latin-1')
         return [author, title]

    @classmethod
    def lookup_kurslitteratur_se(cls, isbn):
         headers, content = cls.get_url("http://www.kurslitteratur.se/ISBN/%s" % isbn)
         title = re.search(r'<meta name="title" content="([^<]*)" />', content).groups()[0].decode('utf-8')
         author = re.search(r'<tr><td>Author</td><td>([^<]*)</td>', content).groups()[0].decode('utf-8')
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
         title = re.search(r'<span property="name">(.*)</span>', content).groups()[0].decode('utf-8')
         author = re.search(r'<strong property="author">(.*)</strong>', content).groups()[0].decode('utf-8')
         return [author, title]

    @classmethod
    def lookup_isbn2book_com(cls, isbn):
        if len(isbn) == 13 and isbn.startswith('978'):
            isbn = isbn[3:-1]
            c = sum((p+1) * int(d) for (p, d) in enumerate(isbn)) % 11
            if c == 10: c = 'X'
            isbn += str(c)
        headers, content = cls.get_url("http://isbn2book.com/q/%s" % isbn)
        title = re.search(r'alt="[^-"]* - ([^"]*)"', content).groups()[0].decode('latin-1')
        author = re.search(r'alt="([^-"]*) - [^"]*"', content).groups()[0].decode('latin-1')
        return [author, title]

    @classmethod
    def lookup_btj_se(cls, isbn):
        headers, content = cls.get_url("http://www.btj.se/default.aspx?search=%s" % isbn)
        title = re.search(r'<span id="ctl00_MainContent_SearchResultList_ArticleRepeat_ctl00_Article1_BookFacts_TitleText1">(.*)</span>', content).groups()[0].decode('utf-8')
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
        if '--test' in sys.argv:
            ISBNLookup.test()
        else:
            out = csv.writer(sys.stdout, dialect='excel')
            out.writerow(['author', 'title'])
            for isbn in sys.argv[1:]:
                out.writerow([x.encode('utf-8')
                              for x in ISBNLookup.lookup(isbn)])
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
