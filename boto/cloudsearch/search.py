# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.
# All Rights Reserved
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
#
from math import ceil
import time
import json
import boto
import requests


class SearchServiceException(Exception):
    pass


class CommitMismatchError(Exception):
    pass


class SearchResults(object):
    
    def __init__(self, **attrs):
        self.rid = attrs['info']['rid']
        # self.doc_coverage_pct = attrs['info']['doc-coverage-pct']
        self.cpu_time_ms = attrs['info']['cpu-time-ms']
        self.time_ms = attrs['info']['time-ms']
        self.hits = attrs['hits']['found']
        self.docs = attrs['hits']['hit']
        self.start = attrs['hits']['start']
        self.rank = attrs['rank']
        self.match_expression = attrs['match-expr']
        self.query = attrs['query']
        self.search_service = attrs['search_service']

        self.num_pages_needed = ceil(self.hits / self.query.real_size)

    def __len__(self):
        return len(self.docs)

    def __iter__(self):
        return iter(self.docs)

    def next_page(self):
        """Call Cloudsearch to get the next page of search results

        :rtype: :class:`exfm.cloudsearch.SearchResults`
        :return: A cloudsearch SearchResults object
        """
        if self.query.page <= self.num_pages_needed:
            self.query.start += self.query.real_size
            self.query.page += 1
            return self.search_service(self.query)
        else:
            raise StopIteration


class Query(object):
    
    RESULTS_PER_PAGE = 500

    def __init__(self, q=None, bq=None, rank=None,
                 return_fields=None, size=10,
                 start=0, facet=None, facet_constraints=None,
                 facet_sort=None, facet_top_n=None, t=None):

        self.q = q
        self.bq = bq
        self.rank = rank or []
        self.return_fields = return_fields or []
        self.start = start
        self.facet = facet or []
        self.facet_constraints = facet_constraints or {}
        self.facet_sort = facet_sort or {}
        self.facet_top_n = facet_top_n or {}
        self.t = t or {}
        self.page = 0
        self.update_size(size)

    def update_size(self, new_size):
        self.size = new_size
        self.real_size = Query.RESULTS_PER_PAGE if (self.size >
            Query.RESULTS_PER_PAGE or self.size == 0) else self.size

    def to_params(self):
        """Transform search parameters from instance properties to a dictionary

        :rtype: dict
        :return: search parameters
        """
        params = {'start': self.start, 'size': self.real_size}

        if self.q:
            params['q'] = self.q

        if self.bq:
            params['bq'] = self.bq

        if self.rank:
            params['rank'] = ','.join(self.rank)

        if self.return_fields:
            params['return-fields'] = ','.join(self.return_fields)

        if self.facet:
            params['facet'] = ','.join(self.facet)

        if self.facet_constraints:
            for k, v in self.facet_constraints.iteritems():
                params['facet-%s-constraints' % k] = v

        if self.facet_sort:
            for k, v in self.facet_sort.iteritems():
                params['facet-%s-sort' % k] = v

        if self.facet_top_n:
            for k, v in self.facet_top_n.iteritems():
                params['facet-%s-top-n' % k] = v

        if self.t:
            for k, v in self.t.iteritems():
                params['t-%s' % k] = v
        return params


class SearchConnection(object):
    
    def __init__(self, domain=None, endpoint=None):
        self.domain = domain
        self.endpoint = endpoint
        if not endpoint:
            self.endpoint = domain.search_service_endpoint

    def build_query(self, q=None, bq=None, rank=None, return_fields=None,
                    size=10, start=0, facet=None, facet_constraints=None,
                    facet_sort=None, facet_top_n=None, t=None):
        return Query(q=q, bq=bq, rank=rank, return_fields=return_fields,
                     size=size, start=start, facet=facet,
                     facet_constraints=facet_constraints,
                     facet_sort=facet_sort, facet_top_n=facet_top_n, t=t)

    def search(self, q=None, bq=None, rank=None, return_fields=None,
               size=10, start=0, facet=None, facet_constraints=None,
               facet_sort=None, facet_top_n=None, t=None):
        """
        Query Cloudsearch

        :type q:
        :param q:

        :type bq:
        :param bq:

        :type rank:
        :param rank:

        :type return_fields:
        :param return_fields:

        :type size:
        :param size:

        :type start:
        :param start:

        :type facet:
        :param facet:

        :type facet_constraints:
        :param facet_constraints:

        :type facet_sort:
        :param facet_sort:

        :type facet_top_n:
        :param facet_top_n:

        :type t:
        :param t:

        :rtype: :class:`exfm.cloudsearch.SearchResults`
        :return: A cloudsearch SearchResults object
        """

        query = self.build_query(q=q, bq=bq, rank=rank,
                                 return_fields=return_fields,
                                 size=size, start=start, facet=facet,
                                 facet_constraints=facet_constraints,
                                 facet_sort=facet_sort,
                                 facet_top_n=facet_top_n, t=t)
        return self(query)

    def __call__(self, query):
        """Make a call to CloudSearch

        :type query: :class:`exfm.cloudsearch.Query`
        :param query: A fully specified Query instance

        :rtype: :class:`exfm.cloudsearch.SearchResults`
        :return: A cloudsearch SearchResults object
        """
        url = "http://%s/2011-02-01/search" % (self.endpoint)
        params = query.to_params()

        r = requests.get(url, params=params)
        data = json.loads(r.content)
        data['query'] = query
        data['search_service'] = self

        if 'messages' in data and 'error' in data:
            for m in data['messages']:
                if m['severity'] == 'fatal':
                    raise SearchServiceException("Error processing search %s "
                        "=> %s" % (params, m['message']), query)
        elif 'error' in data:
            raise SearchServiceException("Unknown error processing search %s"
                % (params), query)

        return SearchResults(**data)

    def get_all_paged(self, query, per_page):
        """Get a generator to iterate over all pages of search results

        :type query: :class:`exfm.cloudsearch.Query`
        :param query: A fully specified Query instance

        :type per_page: int
        :param per_page: Number of docs in each SearchResults object.

        :rtype: generator
        :return: Generator containing :class:`exfm.cloudsearch.SearchResults`
        """
        query.update_size(per_page)
        page = 0
        num_pages_needed = 0
        while page <= num_pages_needed:
            results = self(query)
            num_pages_needed = results.num_pages_needed
            yield results
            query.start += query.real_size
            page += 1

    def get_all_hits(self, query):
        """Get a generator to iterate over all search results

        Transparently handles the results paging from Cloudsearch
        search results so even if you have many thousands of results
        you can iterate over all results in a reasonably efficient
        manner.

        :type query: :class:`exfm.cloudsearch.Query`
        :param query: A fully specified Query instance

        :rtype: generator
        :return: All docs matching query
        """
        page = 0
        num_pages_needed = 0
        while page <= num_pages_needed:
            results = self(query)
            num_pages_needed = results.num_pages_needed
            for doc in results:
                yield doc
            query.start += query.real_size
            page += 1

    def get_num_hits(self, query):
        """Return the total number of hits for query

        :type query: :class:`exfm.cloudsearch.Query`
        :param query: A fully specified Query instance

        :rtype: int
        :return: Total number of hits for query
        """
        query.update_size(1)
        return self(query).hits



