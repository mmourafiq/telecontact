# -*- coding: utf-8 -*-
'''
Created on Nov 01, 2012

@author: Mourad Mourafiq

@copyright: Copyright © 2011

other contributers:
'''
from bs4 import BeautifulSoup

import cPickle as pickle
import re
import random
import time
import urllib
import urllib2
import urlparse

def to_utf(doc):
    return doc.encode('latin-1').decode('utf-8')    

url_base = "http://www.telecontact.ma/liens"
url_base_search = "http://www.telecontact.ma/trouver/index.php?nxo=moteur&nxs=process&recherche=guidee"

class TC(object):
    """
        TC object that executes queries and returns set of results
        
        URL templates to make TC searches.
            http://www.telecontact.ma/liens/what/where.php&page=            
            page=page number
            what = object of search
            where = location
    """
    def __init__(self, pause=5.0, page=1, search=True, what="", where=""):
        """
            @type  pause: long
            @param url: not to burden the server
            @type  page: int
            @param page: pagination 
            @type  query: str
            @param query: the object of the search
            @type  where: str
            @param where: where to look
        
            @rtype:  object
            @return: the instance of TC
        """
        self.pause = pause
        self.page = page        
        self.what = what
        self.where = where
        self.search = search
        self.max = 0
    
    def is_max_set(self):
        return True if self.max > 0 else False
    
    def set_max_pages(self, max):
        self.max = max
    
    def get_max_pages(self):
        return self.max
    
    def set_pause(self, pause):
        self.pause = pause

    def set_page(self, page=0):                
        self.page = page if page> 0 else self.page + 1  
    
    def get_page(self):
        return self.page
    
    def set_what(self, what):
        self.what = what
    
    def set_where(self, where):
        self.where = where   
    
    def set_search(self, search):
        self.search = search
    
    def get_construct_url(self):        
        return self.__url_contruction_search() if self.search else self.__url_contruction()
        
    # Returns a generator that yields URLs.
    def get_results(self, title_def):
        """
        Returns search results for the current query as a iterator.                
        """            
        # pause, so as to not overburden TC
        #time.sleep(self.pause+(random.random()-0.5)*5)                        
    
        # Prepare the URL of the first request.
        url_search = self.get_construct_url()
        print url_search
        # Request the TC Search results page.
        stat = True
        while stat:
            try:
                html = self.__get_result(url_search)
                # Parse the response and extract the summaries                
                soup = BeautifulSoup(html, from_encoding='latin-1')
                if soup.findAll(text=re.compile("captcha")) != []:                    
                    print "Failed page "+self.get_page()+", captcha retrying"
                else:
                    stat = False
            except:
                print "Failed page "+str(self.get_page())+", retrying"
                time.sleep(4)            
        
        #check if the max pages is set
        if not self.is_max_set():
            try:
                max =  int(re.findall(r'\d+', soup.find("div", {"class": "paginationResultat"}).findNext("a", {"class": "suivant"}).findNext("a").findNextSiblings(text=True)[0])[0])
            except:
                max = 0
            self.set_max_pages(max)
        
        for table in soup.findAll("div", {"class": "drs"}):
            result = ""
            try :                                           
                if table.findNext("div", {"class": "visuelResultat"}) is None:                    
                    name_spec_loc = table.findNext("span", {"id": "resultats_h3_span"}) 
                    name_spec = name_spec_loc.findNext("h2", {"class": "h2_rs_st_pnl"})
                    if self.search:
                        title_name = re.findall('\w+', to_utf(name_spec.string), re.UNICODE)
                        title = title_name[-1]
                        name = " ".join(title_name[:-1])
                    else:                    
                        title = ' '.join(re.findall('\w+', to_utf(name_spec.findNext("a",{"class": "moodalbox"}).string), re.UNICODE))
                    if title == title_def:
                        if not self.search:
                            name = ' '.join(re.findall('\w+', to_utf(name_spec.string), re.UNICODE))
                        loc = name_spec_loc.findNext("div", {"class": "adresse"}).findNext('span')
                        address = to_utf(loc.string)                  
                        try:      
                            quartier = ' '.join(re.findall('\w+', to_utf(loc.findNextSibling(text=True)), re.UNICODE)[1:])
                        except:
                            quartier = ""
                        postal_code = re.findall('\d+',  to_utf(loc.findNextSibling("span").string))[0]                    
                        address_href = loc.findNext("a", {"class": "moodalbox"})['href']
                        try :
                            lng, lat = re.findall("-*\d+\.\d+", address_href)
                        except :
                            lng, lat = 0, 0                 
                        phone = ''.join(re.findall('\d+', table.findNext('li', {'class': 'tel'}).findNext(text=True)))
                        result = str(name), str(quartier), str(address), str(postal_code), str(phone), lat, lng                         
            except :
                pass
            if result != "":
                yield result
    
    def __url_contruction(self):
        """
        Construct the activity url
        """                                  
        url_search = url_base        
        # what          
        url_search += '/%(what)s' % {"what":self.what}
        # where
        url_search += '/%(where)s.php' % {"where":self.where}
        #page
        page = "&page=%(page)s" % {"page":self.page}        
        url_search += page
        return url_search    
    
    def __url_contruction_search(self):
        """
        Construct the search url
        """                                      
        url_search = url_base_search        
        # what          
        url_search += '&rubrique=%(what)s' % {"what":self.what}
        # where
        url_search += '&region=%(where)s' % {"where":self.where}
        #page
        page = "&page=%(page)s" % {"page":self.page}        
        url_search += page
        return url_search    
        
    # Request the given URL and return the response page, using the cookie jar.
    def __get_result(self, url):
        """
        Request the given URL and return the response page, using the cookie jar.
    
        @type  url: str
        @param url: URL to retrieve.
    
        @rtype:  str
        @return: Web page retrieved for the given URL.
    
        @raise IOError: An exception is raised on error.
        @raise urllib2.URLError: An exception is raised on error.
        @raise urllib2.HTTPError: An exception is raised on error.
        """
        request = urllib2.Request(url)
        request.add_header('User-Agent',                           
                           'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.10) Gecko/20100915\
              Ubuntu/10.04 (lucid) Firefox/3.6.10')        
        response = urllib2.urlopen(request)        
        html = response.read()
        response.close()        
        return html
