from math import ceil
import time
import json
import re

import boto
import boto.jsonresponse
import boto.exception
from boto.connection import AWSQueryConnection
from boto.auth import QuerySignatureV2AuthHandler
import requests

import logging
log = logging.getLogger(__name__)

QuerySignatureV2AuthHandler.capability.append('cloudsearch')

_valid_key_expr = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_]*$')


def is_valid_key(key):
    return _valid_key_expr.match(_valid_key_expr) != None


def escape_control_characters(s):
    return s.replace("'", '%27').replace('"', '%22')\
        .replace("\\", '%5C').replace('&', '%26')


class SearchServiceException(Exception):
    pass


class CommitMismatchError(Exception):
    pass


def get_document_service(domain=None, endpoint=None):
    return DocumentServiceConnection(domain=domain, endpoint=endpoint)


def get_search_service(domain=None, endpoint=None):
    return SearchConnection(domain=domain, endpoint=endpoint)


class Domain(object):
    created = False
    deleted = False
    doc_service = {}
    domain_id = None
    domain_name = None
    num_searchable_docs = 0
    requires_index_docs = False
    search_instance_count = 0
    search_instance_type = None
    search_partition_count = 0
    search_service = {}

    def __init__(self, **attrs):
        for k, v in attrs.iteritems():
            setattr(self, k, v)

    @property
    def name(self):
        return self.domain_name

    def index_documents(self):
        self.connection.index_documents(self.name)

    def create_index_field(self, field_name, field_type,
        default='', facet=False, result=False, searchable=False,
        source_attributes=[]):
        return self.connection.create_index_field(self.name, field_name,
            field_type, default=default, facet=facet, result=result,
            searchable=searchable, source_attributes=source_attributes)

    def create_rank_expression(self, name, expression):
        return self.connection.create_rank_expression(self.name, name,
            expression)

    def get_document_service(self):
        return DocumentServiceConnection(domain=self)

    def get_search_service(self):
        return SearchConnection(domain=self)

    def allow_ip(self, ip):
        policies = self.connection.get_service_access_policies(self.name)
        if not policies.get('options'):
            p = {
                "Statement": [
                    {
                        "Effect":"Allow",
                        "Action":"*",  # Docs say use GET, but denies unless *
                        "Resource": self.search_service['arn'],
                        "Condition": {
                            "IpAddress": {
                                "aws:SourceIp": [ip]
                            }
                        }
                    },
                    {
                        "Effect":"Allow",
                        "Action":"*",  # Docs say use POST, but denies unless *
                        "Resource": self.doc_service['arn'],
                        "Condition": {
                            "IpAddress": {
                                "aws:SourceIp": [ip]
                            }
                        }
                    }
                ]
            }
            return self.connection.update_service_access_policies(self.name,
                json.dumps(p))
        else:
            noop = True
            policies = json.loads(policies['options'])
            for statement in policies['Statement']:
                if ip in statement['Condition']['IpAddress']['aws:SourceIp']:
                    boto.log.warn('IpAddress %s already allowed for resource '
                        '%s. Noop.' % (ip, statement['Resource']))
                else:
                    noop = False
                    statement['Condition']['IpAddress']['aws:SourceIp'].append(ip)

            if not noop:
                self.connection.update_service_access_policies(self.name,
                    json.dumps(policies))

    def disallow_ip(self, ip):
        policies = self.connection.get_service_access_policies(self.name)
        if not policies.get('options'):
            return

        noop = True
        policies = json.loads(policies['options'])
        for statement in policies['Statement']:
            if ip in statement['Condition']['IpAddress']['aws:SourceIp']:
                noop = False
                index = statement['Condition']['IpAddress']['aws:SourceIp'].index(ip)
                statement['Condition']['IpAddress']['aws:SourceIp'].pop(index)
            else:
                boto.log.warn('IpAddress %s already not allowed for resource '
                    '%s. Noop.' % (ip, statement['Resource']))

        if not noop:
            self.connection.update_service_access_policies(self.name,
                json.dumps(policies))

    def get_allowed_ips(self):
        policies = self.connection.get_service_access_policies(self.name)
        if not policies.get('options'):
            return []

    def wait_for_acl_changes(self):
        finished = False
        while not finished:
            policies = self.connection.get_service_access_policies(self.name)
            if policies['status']['state'] == 'Processing':
                time.sleep(5)
            else:
                finished = True

    def __repr__(self):
        return '<Domain: %s>' % self.domain_name


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

    def __init__(self, q=None, bq=None, rank=[], return_fields=[], size=10,
        start=0, facet=[], facet_constraints={}, facet_sort={}, facet_top_n={},
        t={}):

        self.q = q
        self.bq = bq
        self.rank = rank
        self.return_fields = return_fields
        self.start = start
        self.facet = facet
        self.facet_constraints = facet_constraints
        self.facet_sort = facet_sort
        self.facet_top_n = facet_top_n
        self.t = t

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
        if endpoint:
            self.endpoint = endpoint
        else:
            self.endpoint = domain.doc_service['endpoint']

        if not self.endpoint.startswith('search-'):
            self.endpoint = "search-%s" % self.endpoint

    def build_query(self, q=None, bq=None, rank=[], return_fields=[], size=10,
        start=0, facet=[], facet_constraints={}, facet_sort={}, facet_top_n={},
        t={}):
        return Query(q=q, bq=bq, rank=rank, return_fields=return_fields,
            size=size, start=start, facet=facet,
            facet_constraints=facet_constraints, facet_sort=facet_sort,
            facet_top_n=facet_top_n, t=t)

    def search(self, q=None, bq=None, rank=[], return_fields=[], size=10,
        start=0, facet=[], facet_constraints={}, facet_sort={}, facet_top_n={},
        t={}):
        """Query Cloudsearch

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

        query = self.build_query(q=q, bq=bq, rank=rank, return_fields=return_fields,
            size=size, start=start, facet=facet,
            facet_constraints=facet_constraints, facet_sort=facet_sort,
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

        # import urllib
        # print "%s?%s" % (url, urllib.urlencode(params))

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

        Transparently handles the results paging from Cloudsearch search results
        so even if you have many thousands of results you can iterate over all
        results in a reasonably efficient manner.

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


_illegal_xml_chars_pattern = re.compile(u'[\x00-\x08\x0b\x0c\x0e-\x1F\uD800-\uDFFF\uFFFE\uFFFF]')


def remove_illegal_xml_chars(s):
    return re.sub(_illegal_xml_chars_pattern, '', s)


class DocumentServiceConnection(object):
    endpoint = None

    def __init__(self, domain=None, endpoint=None):
        if endpoint:
            self.endpoint = endpoint
        else:
            self.endpoint = domain.doc_service['endpoint']

        self.documents_batch = []
        self._sdf = None

        if not self.endpoint.startswith('doc-'):
            self.endpoint = "doc-%s" % self.endpoint

    def add(self, _id, version, fields, lang='en'):
        d = {'type': 'add', 'id': _id, 'version': version, 'lang': lang,
            'fields': fields}
        self.documents_batch.append(d)

    def delete(self, _id, version):
        d = {'type': 'delete', 'id': _id, 'version': version}
        self.documents_batch.append(d)

    def get_sdf(self):
        return self._sdf if self._sdf else json.dumps(self.documents_batch)

    def clear_sdf(self):
        self._sdf = None
        self.documents_batch = []

    def add_sdf_from_s3(self, key_obj):
        """@todo (lucas) would be nice if this could just take an s3://uri..."""
        self._sdf = key_obj.get_contents_as_string()

    def commit(self):
        sdf = self.get_sdf()

        if ': null' in sdf:
            log.error('null value in sdf detected.  This will probably raise '
                '500 error.')
            index = sdf.index(': null')
            log.error(sdf[index - 100:index + 100])

        url = "http://%s/2011-02-01/documents/batch" % (self.endpoint)

        request_config = {
            'pool_connections': 20,
            'keep_alive': True,
            'max_retries': 5,
            'pool_maxsize': 50
        }

        r = requests.post(url, data=sdf, config=request_config,
            headers={'Content-Type': 'application/json'})

        return CommitResponse(r, self, sdf)


class CommitResponse(object):
    """Wrapper for response to Cloudsearch document batch commit.

    :type response: :class:`requests.models.Response`
    :param response: Response from Cloudsearch /documents/batch API

    :type doc_service: :class:`exfm.cloudsearch.DocumentServiceConnection`
    :param doc_service: Object containing the documents posted and methods to
        retry

    :raises: :class:`boto.exception.BotoServerError`
    :raises: :class:`exfm.cloudsearch.SearchServiceException`
    """
    def __init__(self, response, doc_service, sdf):
        self.response = response
        self.doc_service = doc_service
        self.sdf = sdf

        try:
            self.content = json.loads(response.content)
        except:
            log.error('Error indexing documents.\nResponse Content:\n{}\n\n'
                'SDF:\n{}'.format(self.content, self.sdf))
            raise boto.exception.BotoServerError(self.response.status_code, '',
                body=self.content)

        self.status = self.content['status']
        if self.status == 'error':
            self.errors = [e.get('message') for e in self.content.get('errors',
                [])]
        else:
            self.errors = []

        self.adds = self.content['adds']
        self.deletes = self.content['deletes']
        self._check_num_ops('add', self.adds)
        self._check_num_ops('delete', self.deletes)

    def _check_num_ops(self, type_, response_num):
        """Raise exception if number of ops in response doesn't match commit

        :type type_: str
        :param type_: Type of commit operation: 'add' or 'delete'

        :type response_num: int
        :param response_num: Number of adds or deletes in the response.

        :raises: :class:`exfm.cloudsearch.SearchServiceException`
        """
        commit_num = len([d for d in self.doc_service.documents_batch
            if d['type'] == type_])

        if response_num != commit_num:
            raise CommitMismatchError(
                'Incorrect number of {}s returned. Commit: {} Respose: {}'\
                .format(type_, commit_num, response_num))


class CloudSearchConnection(AWSQueryConnection):

    APIVersion = '2011-02-01'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None,
                 host='cloudsearch.us-east-1.amazonaws.com', debug=0,
                 https_connection_factory=None, path='/'):
        AWSQueryConnection.__init__(self, aws_access_key_id,
                                    aws_secret_access_key,
                                    is_secure, port, proxy,
                                    proxy_port, proxy_user, proxy_pass,
                                    host, debug, https_connection_factory,
                                    path)

    def _required_auth_capability(self):
        return ['cloudsearch']

    def _prepare_boolean(self, val):
        return 'true' if val in [True, 1, '1', 'true'] else 'false'

    def index_documents(self, domain_name):
        return self.get_response(
            'index_documents_response.index_documents_result.field_names',
            dict, 'IndexDocuments', {'DomainName': domain_name}, verb='POST',
            list_marker='FieldNames')

    def create_domain(self, name):
        """Create a new search domain.
        <CreateDomainResponse xmlns="http://cloudsearch.amazonaws.com/doc/2011-02-01">
          <CreateDomainResult>
            <DomainStatus>
              <SearchPartitionCount>0</SearchPartitionCount>
              <SearchService>
                <Arn>arn:aws:cs:us-east-1:160241911954:search/test</Arn>
              </SearchService>
              <NumSearchableDocs>0</NumSearchableDocs>
              <Created>true</Created>
              <DomainId>160241911954/test</DomainId>
              <SearchInstanceCount>0</SearchInstanceCount>
              <DomainName>test</DomainName>
              <RequiresIndexDocuments>false</RequiresIndexDocuments>
              <Deleted>false</Deleted>
              <DocService>
                <Arn>arn:aws:cs:us-east-1:160241911954:doc/test</Arn>
              </DocService>
            </DomainStatus>
          </CreateDomainResult>
          <ResponseMetadata>
            <RequestId>2c392f2c-3880-11e1-9d03-0d7236ac6cae</RequestId>
          </ResponseMetadata>
        </CreateDomainResponse>

        :type name: string
        :param name: The name of the domain to create

        :rtype: :class:`boto.cloudsearch.Domain`
        :returns: Domain with status.
        """
        return self.get_response(
            'create_domain_response.create_domain_result.domain_status',
            Domain, 'CreateDomain', {'DomainName': name}, verb='POST')

    def delete_domain(self, name):
        """Delete a search domain.
        <DeleteDomainResponse xmlns="http://cloudsearch.amazonaws.com/doc/2011-02-01">
          <DeleteDomainResult>
            <DomainStatus>
              <SearchPartitionCount>0</SearchPartitionCount>
              <SearchService>
                <Arn>arn:aws:cs:us-east-1:160241911954:search/test</Arn>
                <Endpoint>search-test-qs2ho622mqqlyb3acbxrd2pgii.us-east-1.cloudsearch.amazonaws.com</Endpoint>
              </SearchService>
              <NumSearchableDocs>0</NumSearchableDocs>
              <Created>true</Created>
              <DomainId>160241911954/test</DomainId>
              <SearchInstanceCount>0</SearchInstanceCount>
              <DomainName>test</DomainName>
              <RequiresIndexDocuments>false</RequiresIndexDocuments>
              <Deleted>true</Deleted>
              <DocService>
                <Arn>arn:aws:cs:us-east-1:160241911954:doc/test</Arn>
                <Endpoint>doc-test-qs2ho622mqqlyb3acbxrd2pgii.us-east-1.cloudsearch.amazonaws.com</Endpoint>
              </DocService>
            </DomainStatus>
          </DeleteDomainResult>
          <ResponseMetadata>
            <RequestId>2b8a74a0-3887-11e1-8390-d3854e23e661</RequestId>
          </ResponseMetadata>
        </DeleteDomainResponse>

        :type name: string
        :param name: The name of the domain to delete

        :rtype: :class:`boto.cloudsearch.Domain`
        :returns: Domain with status.

        """
        return self.get_response(
            'delete_domain_response.delete_domain_result.domain_status',
            Domain, 'DeleteDomain', {'DomainName': name}, verb='POST')

    def get_domain(self, name):
        """
        :type name: string
        :param name: The name of the domain to get

        :rtype: :class:`boto.cloudsearch.Domain`
        :returns: Domain
        """
        for d in self.get_domains():
            if d.name == name:
                return d

    def get_domains(self):
        """Describes the domains (optionally limited to one or more domains by
        name) owned by this account.

        <DescribeDomainsResponse xmlns="http://cloudsearch.amazonaws.com/doc/2011-02-01">
          <DescribeDomainsResult>
            <DomainStatusList>
              <member>
                <SearchPartitionCount>1</SearchPartitionCount>
                <SearchService>
                  <Arn>arn:aws:cs:us-east-1:160241911954:search/song</Arn>
                  <Endpoint>search-song-3z775eq4lj2c6gdq2gwqxlq7zy.us-east-1.cloudsearch.amazonaws.com</Endpoint>
                </SearchService>
                <NumSearchableDocs>0</NumSearchableDocs>
                <Created>true</Created>
                <SearchInstanceType>search.m1.small</SearchInstanceType>
                <DomainId>160241911954/song</DomainId>
                <SearchInstanceCount>1</SearchInstanceCount>
                <DomainName>song</DomainName>
                <RequiresIndexDocuments>false</RequiresIndexDocuments>
                <Deleted>false</Deleted>
                <DocService>
                  <Arn>arn:aws:cs:us-east-1:160241911954:doc/song</Arn>
                  <Endpoint>doc-song-3z775eq4lj2c6gdq2gwqxlq7zy.us-east-1.cloudsearch.amazonaws.com</Endpoint>
                </DocService>
              </member>
              <member>
                <SearchPartitionCount>1</SearchPartitionCount>
                <SearchService>
                  <Arn>arn:aws:cs:us-east-1:160241911954:search/test</Arn>
                  <Endpoint>search-test-qs2ho622mqqlyb3acbxrd2pgii.us-east-1.cloudsearch.amazonaws.com</Endpoint>
                </SearchService>
                <NumSearchableDocs>0</NumSearchableDocs>
                <Created>true</Created>
                <SearchInstanceType>search.m1.small</SearchInstanceType>
                <DomainId>160241911954/test</DomainId>
                <SearchInstanceCount>1</SearchInstanceCount>
                <DomainName>test</DomainName>
                <RequiresIndexDocuments>false</RequiresIndexDocuments>
                <Deleted>false</Deleted>
                <DocService>
                  <Arn>arn:aws:cs:us-east-1:160241911954:doc/test</Arn>
                  <Endpoint>doc-test-qs2ho622mqqlyb3acbxrd2pgii.us-east-1.cloudsearch.amazonaws.com</Endpoint>
                </DocService>
              </member>
            </DomainStatusList>
          </DescribeDomainsResult>
          <ResponseMetadata>
            <RequestId>09d2fa3d-3886-11e1-8390-d3854e23e661</RequestId>
          </ResponseMetadata>
        </DescribeDomainsResponse>

        :rtype: :class:`boto.cloudsearch.Domain`
        :returns: A list of all domains
        """
        return self.get_response(
            'describe_domains_response.describe_domains_result.domain_status_list',
            Domain, 'DescribeDomains', {}, verb='POST',
            list_marker='DomainStatusList')

    # source_attribute = {'copy': '', 'function': '', 'map': '',
    #     'trim_title': ''}

    # literal_options = {'default': 0, 'facet': True, 'result': True,
    #     'search': True}
    # text_options = {'default': '', 'facet': True, 'result': True}
    # uint_options = {'default': 0}

    def create_index_field(self, domain_name, field_name, field_type,
        default='', facet=False, result=False, searchable=False,
        source_attributes=[]):
        """
        @todo (lucas) Actually do something with source attributes.

        Defines an IndexField, either replacing an existing definition or
        creating a new one.

        :type domain_name: string
        :param domain_name: The name of the domain to add the index field to

        :type field_name: string
        :param field_name: The name of a field in the search index.

        :type field_type: string
        :param field_type: The type of field. Based on this type, exactly one
            of the UIntOptions, LiteralOptions or TextOptions must be present.
            Valid Values: uint | literal | text

        :type field_options: dict
        :param field_options: Specify default value, facet enabled, search
            enabled, or result enabled, depending on the field type.

        :rtype: dict
        :returns: The new index field

        <DefineIndexFieldResponse xmlns="http://cloudsearch.amazonaws.com/doc/2011-02-01">
          <DefineIndexFieldResult>
            <IndexField>
              <Status>
                <CreationDate>2012-01-06T18:48:09Z</CreationDate>
                <UpdateVersion>6</UpdateVersion>
                <State>RequiresIndexDocuments</State>
                <UpdateDate>2012-01-06T18:48:09Z</UpdateDate>
              </Status>
              <Options>
                <IndexFieldType>text</IndexFieldType>
                <IndexFieldName>test</IndexFieldName>
                <TextOptions>
                  <FacetEnabled>false</FacetEnabled>
                  <ResultEnabled>true</ResultEnabled>
                  <DefaultValue/>
                </TextOptions>
              </Options>
            </IndexField>
          </DefineIndexFieldResult>
          <ResponseMetadata>
            <RequestId>fa52420e-3896-11e1-9a3a-fd423adbfe1b</RequestId>
          </ResponseMetadata>
        </DefineIndexFieldResponse>
        """

        if field_type not in ['literal', 'uint', 'text']:
            raise Exception(
                'Invalid field type `%s`. Must be literal, uint, or text.'
                % field_type)

        params = {
            'DomainName': domain_name,
            'IndexField.IndexFieldName': field_name,
            'IndexField.IndexFieldType': field_type
        }

        if field_type == 'literal':
            params['IndexField.LiteralOptions.DefaultValue'] = default
            params['IndexField.LiteralOptions.FacetEnabled'] = self._prepare_boolean(facet)
            params['IndexField.LiteralOptions.ResultEnabled'] = self._prepare_boolean(result)
            params['IndexField.LiteralOptions.SearchEnabled'] = self._prepare_boolean(searchable)

        elif field_type == 'uint':
            params['IndexField.UIntOptions.DefaultValue'] = default

        elif field_type == 'text':
            params['IndexField.TextOptions.DefaultValue'] = default
            params['IndexField.TextOptions.FacetEnabled'] = self._prepare_boolean(facet)
            params['IndexField.TextOptions.ResultEnabled'] = self._prepare_boolean(result)

        return self.get_response(
            'define_index_field_response.define_index_field_result.index_field',
            dict, 'DefineIndexField', params, verb='POST')

    def delete_index_field(self, domain_name, index_field_name):
        """
        <DeleteIndexFieldResponse xmlns="http://cloudsearch.amazonaws.com/doc/2011-02-01">
          <DeleteIndexFieldResult/>
          <ResponseMetadata>
            <RequestId>7843823a-3898-11e1-a321-2b82d2025509</RequestId>
          </ResponseMetadata>
        </DeleteIndexFieldResponse>
        """
        params = {'DomainName': domain_name, 'IndexFieldName': index_field_name}

        return self.get_response(
            'delete_index_field_response.delete_index_field_result.index_field',
            dict, 'DeleteIndexField', params, verb='POST')

    def get_index_fields(self, domain_name):
        """Describes index fields in the search domain

        <DescribeIndexFieldsResponse xmlns="http://cloudsearch.amazonaws.com/doc/2011-02-01">
          <DescribeIndexFieldsResult>
            <IndexFields>
              <member>
                <Status>
                  <CreationDate>2012-01-06T18:48:09Z</CreationDate>
                  <UpdateVersion>6</UpdateVersion>
                  <State>RequiresIndexDocuments</State>
                  <UpdateDate>2012-01-06T18:48:09Z</UpdateDate>
                </Status>
                <Options>
                  <IndexFieldType>text</IndexFieldType>
                  <IndexFieldName>test</IndexFieldName>
                  <TextOptions>
                    <FacetEnabled>false</FacetEnabled>
                    <ResultEnabled>true</ResultEnabled>
                    <DefaultValue/>
                  </TextOptions>
                </Options>
              </member>
            </IndexFields>
          </DescribeIndexFieldsResult>
          <ResponseMetadata>
            <RequestId>fb0d0643-3896-11e1-8af3-29b1183f687c</RequestId>
          </ResponseMetadata>
        </DescribeIndexFieldsResponse>
        """
        return self.get_response(
            'describe_index_fields_response.describe_index_fields_result.index_fields',
            dict, 'DescribeIndexFields', {'DomainName': domain_name},
            verb='POST', list_marker='IndexFields')

    def create_rank_expression(self, domain_name, name, expression):
        """
        <DefineRankExpressionResponse xmlns="http://cloudsearch.amazonaws.com/doc/2011-02-01">
          <DefineRankExpressionResult>
            <RankExpression>
              <Status>
                <CreationDate>2012-01-06T20:49:49Z</CreationDate>
                <UpdateVersion>8</UpdateVersion>
                <State>Processing</State>
                <UpdateDate>2012-01-06T20:49:49Z</UpdateDate>
              </Status>
              <Options>
                <RankName>plain_text_relevance</RankName>
                <RankExpression>text_relevance</RankExpression>
              </Options>
            </RankExpression>
          </DefineRankExpressionResult>
          <ResponseMetadata>
            <RequestId>f98dd0d2-38a7-11e1-b274-bbde7eddd721</RequestId>
          </ResponseMetadata>
        </DefineRankExpressionResponse>
        """
        params = {
            'DomainName': domain_name,
            'RankExpression.RankName': name,
            'RankExpression.RankExpression': expression
        }
        return self.get_response(
            'define_rank_expression_response.define_rank_expression_result.rank_expression',
            dict, 'DefineRankExpression', params, verb='POST')

    def delete_rank_expression(self, domain_name, rank_name):
        """
        <DeleteRankExpressionResponse xmlns="http://cloudsearch.amazonaws.com/doc/2011-02-01">
          <DeleteRankExpressionResult/>
          <ResponseMetadata>
            <RequestId>90716fd0-38a8-11e1-9d03-0d7236ac6cae</RequestId>
          </ResponseMetadata>
        </DeleteRankExpressionResponse>
        """
        params = {
            'DomainName': domain_name,
            'RankName': rank_name
        }
        return self.get_response(
            'delete_rank_expression_response.delete_rank_expression_result.rank_expression',
            dict, 'DeleteRankExpression', params, verb='POST')

    def get_rank_expressions(self, domain_name):
        """
        <DescribeRankExpressionsResponse xmlns="http://cloudsearch.amazonaws.com/doc/2011-02-01">
          <DescribeRankExpressionsResult>
            <RankExpressions>
              <member>
                <Status>
                  <CreationDate>2012-01-06T20:49:49Z</CreationDate>
                  <UpdateVersion>8</UpdateVersion>
                  <State>Processing</State>
                  <UpdateDate>2012-01-06T20:49:49Z</UpdateDate>
                </Status>
                <Options>
                  <RankName>plain_text_relevance</RankName>
                  <RankExpression>text_relevance</RankExpression>
                </Options>
              </member>
            </RankExpressions>
          </DescribeRankExpressionsResult>
          <ResponseMetadata>
            <RequestId>110b74e6-38a8-11e1-9d03-0d7236ac6cae</RequestId>
          </ResponseMetadata>
        </DescribeRankExpressionsResponse>
        """
        return self.get_response(
            'describe_rank_expressions_response.describe_rank_expressions_result.rank_expressions',
            dict, 'DescribeRankExpressions', {'DomainName': domain_name},
            verb='POST', list_marker='RankExpressions')

    def get_default_search_field(self, domain_name):
        """

        """
        return self.get_response(
            'describe_default_search_field_response.describe_default_search_field_result.default_search_field',
            dict, 'DescribeDefaultSearchField', {'DomainName': domain_name},
            verb='POST')

    def update_default_search_field(self, domain_name, field_name):
        """

        """
        params = {
            'DomainName': domain_name,
            'DefaultSearchField': field_name
        }

        return self.get_response(
            'update_default_search_field_response.update_default_search_field_result.default_search_field',
            dict, 'UpdateDefaultSearchField', params, verb='POST')

    def get_service_access_policies(self, domain_name):
        """
        <DescribeServiceAccessPoliciesResponse xmlns="http://cloudsearch.amazonaws.com/doc/2011-02-01">
          <DescribeServiceAccessPoliciesResult>
            <AccessPolicies>
              <Status>
                <CreationDate>2012-01-08T17:19:04Z</CreationDate>
                <UpdateVersion>18</UpdateVersion>
                <State>Processing</State>
                <UpdateDate>2012-01-08T17:19:04Z</UpdateDate>
              </Status>
              <Options>{&quot;Statement&quot;: [{&quot;Action&quot;: &quot;*&quot;, &quot;Resource&quot;: &quot;arn:aws:cs:us-east-1:160241911954:search/testsong&quot;, &quot;Effect&quot;: &quot;Allow&quot;, &quot;Condition&quot;: {&quot;IpAddress&quot;: {&quot;aws:SourceIp&quot;: [&quot;173.3.196.247&quot;]}}}, {&quot;Action&quot;: &quot;*&quot;, &quot;Resource&quot;: &quot;arn:aws:cs:us-east-1:160241911954:doc/testsong&quot;, &quot;Effect&quot;: &quot;Allow&quot;, &quot;Condition&quot;: {&quot;IpAddress&quot;: {&quot;aws:SourceIp&quot;: [&quot;173.3.196.247&quot;]}}}]}</Options>
            </AccessPolicies>
          </DescribeServiceAccessPoliciesResult>
          <ResponseMetadata>
            <RequestId>02d3e863-3a1d-11e1-9a3a-fd423adbfe1b</RequestId>
          </ResponseMetadata>
        </DescribeServiceAccessPoliciesResponse>
        """
        return self.get_response('describe_service_access_policies_response.describe_service_access_policies_result.access_policies',
            dict, 'DescribeServiceAccessPolicies', {'DomainName': domain_name},
            verb='POST')

    def update_service_access_policies(self, domain_name, policies):
        """
        <UpdateServiceAccessPoliciesResponse xmlns="http://cloudsearch.amazonaws.com/doc/2011-02-01">
          <UpdateServiceAccessPoliciesResult>
            <AccessPolicies>
              <Status>
                <CreationDate>2012-01-08T17:33:08Z</CreationDate>
                <UpdateVersion>21</UpdateVersion>
                <State>Processing</State>
                <UpdateDate>2012-01-08T17:33:08Z</UpdateDate>
              </Status>
              <Options>{&quot;Statement&quot;: [{&quot;Action&quot;: &quot;*&quot;, &quot;Resource&quot;: &quot;arn:aws:cs:us-east-1:160241911954:search/testsong&quot;, &quot;Effect&quot;: &quot;Allow&quot;, &quot;Condition&quot;: {&quot;IpAddress&quot;: {&quot;aws:SourceIp&quot;: []}}}, {&quot;Action&quot;: &quot;*&quot;, &quot;Resource&quot;: &quot;arn:aws:cs:us-east-1:160241911954:doc/testsong&quot;, &quot;Effect&quot;: &quot;Allow&quot;, &quot;Condition&quot;: {&quot;IpAddress&quot;: {&quot;aws:SourceIp&quot;: []}}}]}</Options>
            </AccessPolicies>
          </UpdateServiceAccessPoliciesResult>
          <ResponseMetadata>
            <RequestId>d45a410e-3a1e-11e1-a1f0-47bc0fb7e8ea</RequestId>
          </ResponseMetadata>
        </UpdateServiceAccessPoliciesResponse>
        """
        params = {
            'DomainName': domain_name,
            'AccessPolicies': policies
        }

        return self.get_response(
            'update_service_access_policies_response.update_service_access_policies_result.access_policies',
            dict, 'UpdateServiceAccessPolicies', params,
            verb='POST', list_marker='AccessPolicies')

    def describe_stemming_options(self, domain_name):
        pass

    def update_stemming_options(self, domain_name, stems={}):
        pass

    def describe_stopword_options(self, domain_name):
        pass

    def update_stopword_options(self, domain_name, stopwords=[]):
        pass

    def describe_synonym_options(self, domain_name):
        pass

    def update_synonym_options(self, domain_name, synonyms={}):
        pass

    def get_audit_log(self, domain_name, size):
        return self.get_response(
            'get_audit_log_response.get_audit_log_result.audit_records',
            dict, 'GetAuditLog', {'DomainName': domain_name, 'Size': size},
            verb='GET', list_marker='AuditRecords')

    def get_response(self, obj_path, obj_cls, action, params, path='/',
        parent=None, verb='GET', list_marker=None):
        if not parent:
            parent = self
        response = self.make_request(action, params, path, verb)
        body = response.read()
        boto.log.debug(body)
        if response.status == 200:
            e = boto.jsonresponse.Element(
                list_marker=list_marker if list_marker else 'Set',
                pythonize_name=True)
            h = boto.jsonresponse.XmlHandler(e, parent)
            h.parse(body)
            inner = e
            paths = obj_path.split('.')
            for p in paths:
                inner = inner.get(p)

            if not inner:
                return None if list_marker == None else []

            if isinstance(inner, list):
                return [obj_cls(connection=self, **i) for i in inner]
            else:
                return obj_cls(connection=self, **inner)

        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)
