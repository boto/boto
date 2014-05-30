# Copyright (c) 2014 Amazon.com, Inc. or its affiliates.
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
import json
from math import ceil
import boto
from boto.compat import json
import requests

SIMPLE = 'simple'
STRUCTURED = 'structured'
LUCENE = 'lucene'
DISMAX = 'dismax'


class SearchServiceException(Exception):
    pass


class CommitMismatchError(Exception):
    pass


class SearchResults(object):
    def __init__(self, **attrs):
        self.rid = attrs['status']['rid']
        self.time_ms = attrs['status']['time-ms']
        self.hits = attrs['hits']['found']
        self.docs = attrs['hits']['hit']
        self.start = attrs['hits']['start']
        self.query = attrs['query']
        self.search_service = attrs['search_service']

        self.facets = {}
        if 'facets' in attrs:
            for (facet, values) in attrs['facets'].iteritems():
                if 'buckets' in values:
                    self.facets[facet] = dict((k, v) for (k, v) in map(lambda x: (x['value'], x['count']), values.get('buckets', [])))

        self.num_pages_needed = ceil(self.hits / self.query.real_size)

    def __len__(self):
        return len(self.docs)

    def __iter__(self):
        return iter(self.docs)

    def next_page(self):
        """Call Cloudsearch to get the next page of search results

        :rtype: :class:`boto.cloudsearch2.search.SearchResults`
        :return: the following page of search results
        """
        if self.query.page <= self.num_pages_needed:
            self.query.start += self.query.real_size
            self.query.page += 1
            return self.search_service(self.query)
        else:
            raise StopIteration


class Query(object):

    RESULTS_PER_PAGE = 500

    def __init__(self, q=None, parser=None, fq=None, expr=None,
                 return_fields=None, size=10, start=0, sort=None,
                 facet=None, highlight=None, partial=None, options=None):

        self.q = q
        self.parser = parser
        self.fq = fq
        self.expr = expr or {}
        self.sort = sort or []
        self.return_fields = return_fields or []
        self.start = start
        self.facet = facet or {}
        self.highlight = highlight or {}
        self.partial = partial
        self.options = options
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

        if self.parser:
            params['q.parser'] = self.parser

        if self.fq:
            params['fq'] = self.fq

        if self.expr:
            for k, v in self.expr.iteritems():
                params['expr.%s' % k] = v

        if self.facet:
            for k, v in self.facet.iteritems():
                if type(v) not in [str, unicode]:
                    v = json.dumps(v)
                params['facet.%s' % k] = v

        if self.highlight:
            for k, v in self.highlight.iteritems():
                params['highlight.%s' % k] = v

        if self.options:
            params['options'] = self.options

        if self.return_fields:
            params['return'] = ','.join(self.return_fields)

        if self.partial is not None:
            params['partial'] = self.partial

        if self.sort:
            params['sort'] = ','.join(self.sort)

        return params


class SearchConnection(object):

    def __init__(self, domain=None, endpoint=None):
        self.domain = domain
        self.endpoint = endpoint
        self.session = requests.Session()

        if not endpoint:
            self.endpoint = domain.search_service_endpoint

    def build_query(self, q=None, parser=None, fq=None, rank=None, return_fields=None,
                    size=10, start=0, facet=None, highlight=None, sort=None,
                    partial=None, options=None):
        return Query(q=q, parser=parser, fq=fq, expr=rank, return_fields=return_fields,
                     size=size, start=start, facet=facet, highlight=highlight,
                     sort=sort, partial=partial, options=options)

    def search(self, q=None, parser=None, fq=None, rank=None, return_fields=None,
               size=10, start=0, facet=None, highlight=None, sort=None, partial=None,
               options=None):
        """
        Send a query to CloudSearch

        Each search query should use at least the q or bq argument to specify
        the search parameter. The other options are used to specify the
        criteria of the search.

        :type q: string
        :param q: A string to search the default search fields for.

        :type parser: string
        :param parser: The parser to use. 'simple', 'structured', 'lucene', 'dismax'

        :type fq: string
        :param fq: The filter query to use.

        :type sort: List of strings
        :param sort: A list of fields or rank expressions used to order the
            search results. Order is handled by adding 'desc' or 'asc' after the field name.
            ``['year desc', 'author asc']``

        :type return_fields: List of strings
        :param return_fields: A list of fields which should be returned by the
            search. If this field is not specified, only IDs will be returned.
            ``['headline']``

        :type size: int
        :param size: Number of search results to specify

        :type start: int
        :param start: Offset of the first search result to return (can be used
            for paging)

        :type facet: dict
        :param facet: Dictionary of fields for which facets should be returned
            The facet value is string of JSON options
            ``{'year': '{sort:"bucket", size:3}', 'genres': '{buckets:["Action","Adventure","Sci-Fi"]}'}``

        :type highlight: dict
        :param highlight: Dictionary of fields for which highlights should be returned
            The facet value is string of JSON options
            ``{'genres': '{format:'text',max_phrases:2,pre_tag:'<b>',post_tag:'</b>'}'}``

        :type partial: bool
        :param partial: Should partial results from a partioned service be returned if
            one or more index partitions are unreachable.

        :type options: str
        :param options: Options for the query parser specified in *parser*.
            Specified as a string in JSON format.
            ``{fields: ['title^5', 'description']}``

        :rtype: :class:`boto.cloudsearch2.search.SearchResults`
        :return: Returns the results of this search

        The following examples all assume we have indexed a set of documents
        with fields: *author*, *date*, *headline*

        A simple search will look for documents whose default text search
        fields will contain the search word exactly:

        >>> search(q='Tim') # Return documents with the word Tim in them (but not Timothy)

        A simple search with more keywords will return documents whose default
        text search fields contain the search strings together or separately.

        >>> search(q='Tim apple') # Will match "tim" and "apple"

        More complex searches require the boolean search operator.

        Wildcard searches can be used to search for any words that start with
        the search string.

        >>> search(q="'Tim*'") # Return documents with words like Tim or Timothy)

        Search terms can also be combined. Allowed operators are "and", "or",
        "not", "field", "optional", "token", "phrase", or "filter"

        >>> search(q="(and 'Tim' (field author 'John Smith'))", parser='structured')

        Facets allow you to show classification information about the search
        results. For example, you can retrieve the authors who have written
        about Tim with a max of 3

        >>> search(q='Tim', facet={'Author': '{sort:"bucket", size:3}'})
        """

        query = self.build_query(q=q, parser=parser, fq=fq, rank=rank,
                                 return_fields=return_fields,
                                 size=size, start=start, facet=facet,
                                 highlight=highlight, sort=sort,
                                 partial=partial, options=options)
        return self(query)

    def __call__(self, query):
        """Make a call to CloudSearch

        :type query: :class:`boto.cloudsearch2.search.Query`
        :param query: A group of search criteria

        :rtype: :class:`boto.cloudsearch2.search.SearchResults`
        :return: search results
        """
        api_version = '2013-01-01'
        if self.domain:
            api_version = self.domain.layer1.APIVersion
        url = "http://%s/%s/search" % (self.endpoint, api_version)
        params = query.to_params()

        r = self.session.get(url, params=params)
        try:
            data = json.loads(r.content)
        except ValueError, e:
            if r.status_code == 403:
                msg = ''
                import re
                g = re.search('<html><body><h1>403 Forbidden</h1>([^<]+)<', r.content)
                try:
                    msg = ': %s' % (g.groups()[0].strip())
                except AttributeError:
                    pass
                raise SearchServiceException('Authentication error from Amazon%s' % msg)
            raise SearchServiceException("Got non-json response from Amazon. %s" % r.content, query)

        if 'messages' in data and 'error' in data:
            for m in data['messages']:
                if m['severity'] == 'fatal':
                    raise SearchServiceException("Error processing search %s "
                        "=> %s" % (params, m['message']), query)
        elif 'error' in data:
            raise SearchServiceException("Unknown error processing search %s"
                % json.dumps(data), query)

        data['query'] = query
        data['search_service'] = self

        return SearchResults(**data)

    def get_all_paged(self, query, per_page):
        """Get a generator to iterate over all pages of search results

        :type query: :class:`boto.cloudsearch2.search.Query`
        :param query: A group of search criteria

        :type per_page: int
        :param per_page: Number of docs in each :class:`boto.cloudsearch2.search.SearchResults` object.

        :rtype: generator
        :return: Generator containing :class:`boto.cloudsearch2.search.SearchResults`
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

        :type query: :class:`boto.cloudsearch2.search.Query`
        :param query: A group of search criteria

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

        :type query: :class:`boto.cloudsearch2.search.Query`
        :param query: a group of search criteria

        :rtype: int
        :return: Total number of hits for query
        """
        query.update_size(1)
        return self(query).hits
