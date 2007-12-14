# Copyright (c) 2006,2007 Mitch Garnaat http://garnaat.org/
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

def query_lister(domain, query='', max_results=None, sort=None):
    more_results = True
    num_results = 0
    more_token = None
    while more_results:
        rs = domain.connection.query(domain.name, query, None, more_token, sort)
        for item_name in rs:
            if max_results:
                if num_results == max_results:
                    raise StopIteration
            yield item_name
            num_results += 1
        more_token = rs.more_token
        more_results = more_token != None
        
class QueryResultSet:

    def __init__(self, domain=None, query='', max_results=None, sort=None):
        self.max_results = max_results
        self.domain = domain
        self.query = query
        self.sort = sort

    def __iter__(self):
        return query_lister(self.domain, self.query,
                            self.max_results, self.sort)


    
