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

import boto
import boto.jsonresponse
from boto.compat import json
from boto.connection import AWSQueryConnection
from boto.regioninfo import RegionInfo

#boto.set_stream_logger('cloudsearch')


def do_bool(val):
    return 'true' if val in [True, 1, '1', 'true'] else 'false'


class Layer1(AWSQueryConnection):

    APIVersion = '2013-01-01'
    #AuthServiceName = 'sqs'
    DefaultRegionName = boto.config.get('Boto', 'cs_region_name', 'us-east-1')
    DefaultRegionEndpoint = boto.config.get('Boto', 'cs_region_endpoint',
                                            'cloudsearch.us-east-1.amazonaws.com')

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, host=None, port=None,
                 proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, debug=0,
                 https_connection_factory=None, region=None, path='/',
                 api_version=None, security_token=None,
                 validate_certs=True, profile_name=None):
        if not region:
            region = RegionInfo(self, self.DefaultRegionName,
                                self.DefaultRegionEndpoint)
        self.region = region
        AWSQueryConnection.__init__(
            self,
            host=self.region.endpoint,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            is_secure=is_secure,
            port=port,
            proxy=proxy,
            proxy_port=proxy_port,
            proxy_user=proxy_user,
            proxy_pass=proxy_pass,
            debug=debug,
            https_connection_factory=https_connection_factory,
            path=path,
            security_token=security_token,
            validate_certs=validate_certs,
            profile_name=profile_name)

    def _required_auth_capability(self):
        return ['hmac-v4']

    def get_response(self, doc_path, action, params, path='/',
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
            for p in doc_path:
                inner = inner.get(p)
            if not inner:
                return None if list_marker is None else []
            if isinstance(inner, list):
                return inner
            else:
                return dict(**inner)
        else:
            raise self.ResponseError(response.status, response.reason, body)

    def create_domain(self, domain_name):
        """
        Create a new search domain.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :raises: BaseException, InternalException, LimitExceededException
        """
        doc_path = ('create_domain_response',
                    'create_domain_result',
                    'domain_status')
        params = {'DomainName': domain_name}
        return self.get_response(doc_path, 'CreateDomain',
                                 params, verb='POST')

    def define_analysis_scheme(self, domain_name, name, language,
                               algorithmic_stemming="none", stemming_dictionary=None,
                               stopwords=None, synonyms=None):
        """
        Updates stemming options used by indexing for the search domain.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :type name: str
        :param name: Name of the analysis scheme

        :type language: str
        :param language:  IETF RFC 4646 lang code or 'mul' for multiple
            languages.

        :type algorithmic_stemming: str
        :param algorithmic_stemming: Which type of stemming to use.
            one of ``none | minimal | light | full``

        :type stemming_dictionary: dict
        :param stemming_dictionary: dict of stemming words
            ``{"running": "run", "jumping": "jump"}``

        :type stopwords: list of strings
        :param stopwords: list of stopwords

        :type synonyms: dict
        :param synonyms: dict of Array of words to use as synonyms
            ``{"aliases": {"running": ["run", "ran"], "jumping": ["jump", "jumped"]},
               "groups": [["sit", "sitting", "sat"], ["hit", "hitting"]]}``

        :raises: BaseException, InternalException, InvalidTypeException,
            LimitExceededException, ResourceNotFoundException
        """
        doc_path = ('define_analysis_scheme_response',
                    'define_analysis_scheme_result',
                    'analysis_scheme')
        params = {'DomainName': domain_name, 'AnalysisScheme.AnalysisSchemeName': name,
                  'AnalysisScheme.AnalysisSchemeLanguage': language,
                  'AnalysisScheme.AnalysisOptions.AlgorithmicStemming': algorithmic_stemming,
                  'AnalysisScheme.AnalysisOptions.StemmingDictionary':
                      json.dumps(stemming_dictionary) if stemming_dictionary else dict(),
                  'AnalysisScheme.AnalysisOptions.Stopwords':
                      json.dumps(stopwords) if stopwords else list(),
                  'AnalysisScheme.AnalysisOptions.Synonyms':
                      json.dumps(synonyms) if synonyms else dict(),
                  }

        return self.get_response(doc_path, 'DefineAnalysisScheme',
                                 params, verb='POST')

    def define_expression(self, domain_name, name, value):
        """
        Defines an Expression, either replacing an existing
        definition or creating a new one.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :type name: string
        :param name: The name of an expression.

        :type value: string
        :param value: The expression to evaluate for ranking or
            thresholding while processing a search request. The
            Expression syntax is based on JavaScript and supports:

            * Single value, sort enabled numeric fields (int, double, date)
            * Other expressions
            * The _score variable, which references a document's relevance score
            * The _time variable, which references the current epoch time
            * Integer, floating point, hex, and octal literals
            * Arithmetic operators: + - * / %
            * Bitwise operators: | & ^ ~ << >> >>>
            * Boolean operators (including the ternary operator): && || ! ?:
            * Comparison operators: < <= == >= >
            * Mathematical functions: abs ceil exp floor ln log2 log10 logn
             max min pow sqrt pow
            * Trigonometric functions: acos acosh asin asinh atan atan2 atanh
             cos cosh sin sinh tanh tan
            * The haversin distance function

            Expressions always return an integer value from 0 to the maximum
            64-bit signed integer value (2^63 - 1). Intermediate results are
            calculated as double-precision floating point values and the return
            value is rounded to the nearest integer. If the expression is invalid
            or evaluates to a negative value, it returns 0. If the expression
            evaluates to a value greater than the maximum, it returns the maximum
            value.

            The source data for an Expression can be the name of an
            IndexField of type int or double, another Expression or the
            reserved name _score, or the functions above. The _score source is
            defined to return as a double with a floor of 0 to
            indicate how relevant a document is to the search request,
            taking into account repetition of search terms in the
            document and proximity of search terms to each other in
            each matching IndexField in the document.

            For more information about using expressions to customize results,
            see the Amazon CloudSearch Developer Guide.

        :raises: BaseException, InternalException, LimitExceededException,
            InvalidTypeException, ResourceNotFoundException
        """
        doc_path = ('define_expression_response',
                    'define_expression_result',
                    'expression')
        params = {'DomainName': domain_name,
                  'Expression.ExpressionValue': value,
                  'Expression.ExpressionName': name}
        return self.get_response(doc_path, 'DefineExpression',
                                 params, verb='POST')

    def define_index_field(self, domain_name, field_name, field_type,
                           default=None, facet=False, returnable=False,
                           searchable=False, sortable=False,
                           highlight=False, source_field=None,
                           analysis_scheme=None):
        """
        Defines an ``IndexField``, either replacing an existing
        definition or creating a new one.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :type field_name: string
        :param field_name: The name of a field in the search index.

        :type field_type: string
        :param field_type: The type of field.  Valid values are
            int | double | literal | text | date | latlon |
            int-array | double-array | literal-array | text-array | date-array

        :type default: string or int
        :param default: The default value for the field.  If the
            field is of type ``int`` this should be an integer value.
            Otherwise, it's a string.

        :type facet: bool
        :param facet: A boolean to indicate whether facets
            are enabled for this field or not.  Does not apply to
            fields of type ``int, int-array, text, text-array``.

        :type returnable: bool
        :param returnable: A boolean to indicate whether values
            of this field can be returned in search results or
            used in ranking.

        :type searchable: bool
        :param searchable: A boolean to indicate whether search
            is enabled for this field or not.

        :type sortable: bool
        :param sortable: A boolean to indicate whether sorting
            is enabled for this field or not. Does not apply to
            fields of array types.

        :type highlight: bool
        :param highlight: A boolean to indicate whether highlighting
            is enabled for this field or not. Does not apply to
            fields of type ``double, int, date, latlon``

        :type source_field: list of strings or string
        :param source_field: For array types, this is the list of fields
            to treat as the source. For singular types, pass a string only.

        :type analysis_scheme: string
        :param analysis_scheme: The analysis scheme to use for this field.
            Only applies to ``text | text-array`` field types

        :raises: BaseException, InternalException, LimitExceededException,
            InvalidTypeException, ResourceNotFoundException
        """
        doc_path = ('define_index_field_response',
                    'define_index_field_result',
                    'index_field')
        params = {'DomainName': domain_name,
                  'IndexField.IndexFieldName': field_name,
                  'IndexField.IndexFieldType': field_type}
        if field_type == 'literal':
            if default:
                params['IndexField.LiteralOptions.DefaultValue'] = default
            params['IndexField.LiteralOptions.FacetEnabled'] = do_bool(facet)
            params['IndexField.LiteralOptions.ReturnEnabled'] = do_bool(returnable)
            params['IndexField.LiteralOptions.SearchEnabled'] = do_bool(searchable)
            params['IndexField.LiteralOptions.SortEnabled'] = do_bool(sortable)
            if source_field:
                params['IndexField.LiteralOptions.SourceField'] = source_field
        elif field_type == 'literal-array':
            if default:
                params['IndexField.LiteralArrayOptions.DefaultValue'] = default
            params['IndexField.LiteralArrayOptions.FacetEnabled'] = do_bool(facet)
            params['IndexField.LiteralArrayOptions.ReturnEnabled'] = do_bool(returnable)
            params['IndexField.LiteralArrayOptions.SearchEnabled'] = do_bool(searchable)
            if source_field:
                params['IndexField.LiteralArrayOptions.SourceFields'] = ','.join(source_field)
        elif field_type == 'int':
            if default:
                params['IndexField.IntOptions.DefaultValue'] = default
            params['IndexField.IntOptions.FacetEnabled'] = do_bool(facet)
            params['IndexField.IntOptions.ReturnEnabled'] = do_bool(returnable)
            params['IndexField.IntOptions.SearchEnabled'] = do_bool(searchable)
            params['IndexField.IntOptions.SortEnabled'] = do_bool(sortable)
            if source_field:
                params['IndexField.IntOptions.SourceField'] = source_field
        elif field_type == 'int-array':
            if default:
                params['IndexField.IntArrayOptions.DefaultValue'] = default
            params['IndexField.IntArrayOptions.FacetEnabled'] = do_bool(facet)
            params['IndexField.IntArrayOptions.ReturnEnabled'] = do_bool(returnable)
            params['IndexField.IntArrayOptions.SearchEnabled'] = do_bool(searchable)
            if source_field:
                params['IndexField.IntArrayOptions.SourceFields'] = ','.join(source_field)
        elif field_type == 'date':
            if default:
                params['IndexField.DateOptions.DefaultValue'] = default
            params['IndexField.DateOptions.FacetEnabled'] = do_bool(facet)
            params['IndexField.DateOptions.ReturnEnabled'] = do_bool(returnable)
            params['IndexField.DateOptions.SearchEnabled'] = do_bool(searchable)
            params['IndexField.DateOptions.SortEnabled'] = do_bool(sortable)
            if source_field:
                params['IndexField.DateOptions.SourceField'] = source_field
        elif field_type == 'date-array':
            if default:
                params['IndexField.DateArrayOptions.DefaultValue'] = default
            params['IndexField.DateArrayOptions.FacetEnabled'] = do_bool(facet)
            params['IndexField.DateArrayOptions.ReturnEnabled'] = do_bool(returnable)
            params['IndexField.DateArrayOptions.SearchEnabled'] = do_bool(searchable)
            if source_field:
                params['IndexField.DateArrayOptions.SourceFields'] = ','.join(source_field)
        elif field_type == 'double':
            if default:
                params['IndexField.DoubleOptions.DefaultValue'] = default
            params['IndexField.DoubleOptions.FacetEnabled'] = do_bool(facet)
            params['IndexField.DoubleOptions.ReturnEnabled'] = do_bool(returnable)
            params['IndexField.DoubleOptions.SearchEnabled'] = do_bool(searchable)
            params['IndexField.DoubleOptions.SortEnabled'] = do_bool(sortable)
            if source_field:
                params['IndexField.DoubleOptions.SourceField'] = source_field
        elif field_type == 'double-array':
            if default:
                params['IndexField.DoubleArrayOptions.DefaultValue'] = default
            params['IndexField.DoubleArrayOptions.FacetEnabled'] = do_bool(facet)
            params['IndexField.DoubleArrayOptions.ReturnEnabled'] = do_bool(returnable)
            params['IndexField.DoubleArrayOptions.SearchEnabled'] = do_bool(searchable)
            if source_field:
                params['IndexField.DoubleArrayOptions.SourceFields'] = ','.join(source_field)
        elif field_type == 'text':
            if default:
                params['IndexField.TextOptions.DefaultValue'] = default
            params['IndexField.TextOptions.ReturnEnabled'] = do_bool(returnable)
            params['IndexField.TextOptions.HighlightEnabled'] = do_bool(highlight)
            params['IndexField.TextOptions.SortEnabled'] = do_bool(sortable)
            if source_field:
                params['IndexField.TextOptions.SourceField'] = source_field
            if analysis_scheme:
                params['IndexField.TextOptions.AnalysisScheme'] = analysis_scheme
        elif field_type == 'text-array':
            if default:
                params['IndexField.TextArrayOptions.DefaultValue'] = default
            params['IndexField.TextArrayOptions.ReturnEnabled'] = do_bool(returnable)
            params['IndexField.TextArrayOptions.HighlightEnabled'] = do_bool(highlight)
            if source_field:
                params['IndexField.TextArrayOptions.SourceFields'] = ','.join(source_field)
            if analysis_scheme:
                params['IndexField.TextArrayOptions.AnalysisScheme'] = analysis_scheme
        elif field_type == 'latlon':
            if default:
                params['IndexField.LatLonOptions.DefaultValue'] = default
            params['IndexField.LatLonOptions.FacetEnabled'] = do_bool(facet)
            params['IndexField.LatLonOptions.ReturnEnabled'] = do_bool(returnable)
            params['IndexField.LatLonOptions.SearchEnabled'] = do_bool(searchable)
            params['IndexField.LatLonOptions.SortEnabled'] = do_bool(sortable)
            if source_field:
                params['IndexField.LatLonOptions.SourceField'] = source_field

        return self.get_response(doc_path, 'DefineIndexField',
                                 params, verb='POST')

    def define_suggester(self, domain_name, name, source_field,
                         fuzzy_matching=None, sort_expression=None):
        """
        Defines an Expression, either replacing an existing
        definition or creating a new one.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :type name: string
        :param name: The name of an suggester to use.

        :type source_field: string
        :param source_field: The source field name to use for the ``Suggester``

        :type fuzzy_matching: string or None
        :param fuzzy_matching: The optional type of fuzzy matching to use. One of
            none | low | high

        :type sort_expression: string or None
        :param sort_expression: The optional sort expression to use

        :raises: BaseException, InternalException, LimitExceededException,
            InvalidTypeException, ResourceNotFoundException
        """
        doc_path = ('define_expression_response',
                    'define_expression_result',
                    'expression')
        params = {'DomainName': domain_name,
                  'Suggester.SuggesterName': name,
                  'Suggester.DocumentSuggesterOptions.SourceField': source_field}
        if fuzzy_matching is not None:
            params['Suggester.DocumentSuggesterOptions.FuzzyMatching'] = fuzzy_matching
        if sort_expression is not None:
            params['Suggester.DocumentSuggesterOptions.SortExpression'] = sort_expression

        return self.get_response(doc_path, 'DefineExpression', params,
                                 verb='POST')

    def delete_analysis_scheme(self, domain_name, scheme_name):
        """
        Deletes an existing ``AnalysisScheme`` from the search domain.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :type scheme_name: string
        :param scheme_name: The analysis scheme name to delete

        :raises: BaseException, InternalException, ResourceNotFoundException
        """
        doc_path = ('delete_analysis_scheme_response',
                    'delete_analysis_scheme_result',
                    'analysis_scheme')
        params = {'DomainName': domain_name,
                  'AnalysisSchemeName': scheme_name}
        return self.get_response(doc_path, 'DeleteAnalysisScheme',
                                 params, verb='POST')

    def delete_domain(self, domain_name):
        """
        Delete a search domain.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :raises: BaseException, InternalException
        """
        doc_path = ('delete_domain_response',
                    'delete_domain_result',
                    'domain_status')
        params = {'DomainName': domain_name}
        return self.get_response(doc_path, 'DeleteDomain',
                                 params, verb='POST')

    def delete_index_field(self, domain_name, field_name):
        """
        Deletes an existing ``IndexField`` from the search domain.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :type field_name: string
        :param field_name: A string that represents the name of
            an index field. Field names must begin with a letter and
            can contain the following characters: a-z (lowercase),
            0-9, and _ (underscore). Uppercase letters and hyphens are
            not allowed. The names "body", "docid", and
            "text_relevance" are reserved and cannot be specified as
            field or rank expression names.

        :raises: BaseException, InternalException, ResourceNotFoundException
        """
        doc_path = ('delete_index_field_response',
                    'delete_index_field_result',
                    'index_field')
        params = {'DomainName': domain_name,
                  'IndexFieldName': field_name}
        return self.get_response(doc_path, 'DeleteIndexField',
                                 params, verb='POST')

    def delete_expression(self, domain_name, name):
        """
        Deletes an existing ``Expression`` from the search domain.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :type name: string
        :param name: Name of the ``Expression`` to delete.

        :raises: BaseException, InternalException, ResourceNotFoundException
        """
        doc_path = ('delete_expression_response',
                    'delete_expression_result',
                    'expression')
        params = {'DomainName': domain_name, 'ExpressionName': name}
        return self.get_response(doc_path, 'DeleteExpression',
                                 params, verb='POST')

    def delete_suggester(self, domain_name, name):
        """
        Deletes an existing ``Suggester`` from the search domain.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :type name: string
        :param name: Name of the ``Suggester`` to delete.

        :raises: BaseException, InternalException, ResourceNotFoundException
        """
        doc_path = ('delete_suggester_response',
                    'delete_suggester_result',
                    'suggester')
        params = {'DomainName': domain_name, 'SuggesterName': name}
        return self.get_response(doc_path, 'DeleteSuggester',
                                 params, verb='POST')

    def describe_analysis_schemes(self, domain_name):
        """
        Describes analysis schemes used by indexing for the search domain.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :raises: BaseException, InternalException, ResourceNotFoundException
        """
        doc_path = ('describe_analysis_schemes_response',
                    'describe_analysis_schemes_result',
                    'analysis_schemes')
        params = {'DomainName': domain_name}
        return self.get_response(doc_path, 'DescribeAnalysisSchemes',
                                 params, verb='POST')

    def describe_availability_options(self, domain_name):
        """
        Describes the availability options for the search domain.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :raises: BaseException, InternalException, ResourceNotFoundException
        """
        doc_path = ('describe_availability_options_response',
                    'describe_availability_options_result',
                    'availability_options')
        params = {'DomainName': domain_name}
        return self.get_response(doc_path, 'DescribeAvailabilityOptions',
                                 params, verb='POST')

    def describe_domains(self, domain_names=None):
        """
        Describes the domains (optionally limited to one or more
        domains by name) owned by this account.

        :type domain_names: list
        :param domain_names: Limits the response to the specified domains.

        :raises: BaseException, InternalException
        """
        doc_path = ('describe_domains_response',
                    'describe_domains_result',
                    'domain_status_list')
        params = {}
        if domain_names:
            for i, domain_name in enumerate(domain_names, 1):
                params['DomainNames.member.%d' % i] = domain_name
        return self.get_response(doc_path, 'DescribeDomains',
                                 params, verb='POST',
                                 list_marker='DomainStatusList')

    def describe_expressions(self, domain_name, names=None):
        """
        Describes RankExpressions in the search domain, optionally
        limited to a single expression.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :type names: list
        :param names: Limit response to the specified names.

        :raises: BaseException, InternalException, ResourceNotFoundException
        """
        doc_path = ('describe_expressions_response',
                    'describe_expressions_result',
                    'expressions')
        params = {'DomainName': domain_name}
        if names:
            for i, expr_name in enumerate(names, 1):
                params['ExpressionNames.member.%d' % i] = expr_name
        return self.get_response(doc_path, 'DescribeExpressions',
                                 params, verb='POST',
                                 list_marker='Expressions')

    def describe_index_fields(self, domain_name, field_names=None):
        """
        Describes index fields in the search domain, optionally
        limited to a single ``IndexField``.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :type field_names: list
        :param field_names: Limits the response to the specified fields.

        :raises: BaseException, InternalException, ResourceNotFoundException
        """
        doc_path = ('describe_index_fields_response',
                    'describe_index_fields_result',
                    'index_fields')
        params = {'DomainName': domain_name}
        if field_names:
            for i, field_name in enumerate(field_names, 1):
                params['FieldNames.member.%d' % i] = field_name
        return self.get_response(doc_path, 'DescribeIndexFields',
                                 params, verb='POST',
                                 list_marker='IndexFields')

    def describe_scaling_parameters(self, domain_name):
        """
        Describes the scaling parameters for the search domain.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :raises: BaseException, InternalException, ResourceNotFoundException
        """
        doc_path = ('describe_scaling_parameters_response',
                    'describe_scaling_parameters_result',
                    'scaling_parameters')
        params = {'DomainName': domain_name}
        return self.get_response(doc_path, 'DescribeScalingParameters',
                                 params, verb='POST')

    def describe_service_access_policies(self, domain_name):
        """
        Describes the resource-based policies controlling access to
        the services in this search domain.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :raises: BaseException, InternalException, ResourceNotFoundException
        """
        doc_path = ('describe_service_access_policies_response',
                    'describe_service_access_policies_result',
                    'access_policies')
        params = {'DomainName': domain_name}
        return self.get_response(doc_path, 'DescribeServiceAccessPolicies',
                                 params, verb='POST')

    def describe_suggesters(self, domain_name, names=None):
        """
        Describes the suggesters for the search domain.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :type names: list
        :param names: Limit response to the specified names.

        :raises: BaseException, InternalException, ResourceNotFoundException
        """
        doc_path = ('describe_suggesters_response',
                    'describe_suggesters_result',
                    'suggesters')
        params = {'DomainName': domain_name}
        if names:
            for i, suggester_name in enumerate(names, 1):
                params['SuggesterNames.member.%d' % i] = suggester_name

        return self.get_response(doc_path, 'DescribeSuggesters',
                                 params, verb='POST', list_marker="Suggesters")

    def index_documents(self, domain_name):
        """
        Tells the search domain to start scanning its documents using
        the latest text processing options and ``IndexFields``.  This
        operation must be invoked to make visible in searches any
        options whose <a>OptionStatus</a> has ``OptionState`` of
        ``RequiresIndexDocuments``.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :raises: BaseException, InternalException, ResourceNotFoundException
        """
        doc_path = ('index_documents_response',
                    'index_documents_result',
                    'field_names')
        params = {'DomainName': domain_name}
        return self.get_response(doc_path, 'IndexDocuments', params,
                                 verb='POST', list_marker='FieldNames')

    def update_availability_options(self, domain_name, multi_az):
        """
        Updates availability options for the search domain.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :type multi_az: bool
        :param multi_az: Should the domain be setup in multiple
            Availability Zones

        :raises: BaseException, InternalException, InvalidTypeException,
            LimitExceededException, ResourceNotFoundException
        """
        doc_path = ('update_availability_options_response',
                    'update_availability_options_result',
                    'availability_options')
        params = {'DomainName': domain_name,
                  'MultiAZ': do_bool(multi_az)}
        return self.get_response(doc_path, 'UpdateAvailabilityOptions',
                                 params, verb='POST')

    def update_scaling_parameters(self, domain_name, instance_type=None,
                                  replication_count=0):
        """
        Updates scaling parameters for the search domain.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :type instance_type: str or None
        :param instance_type: The type of instance to use. One of
            None | search.m1.small | search.m1.large | search.m2.xlarge | search.m2.2xlarge

        :type replication_count: int
        :param replication_count: The desired number of replicas. A
            value of 0 will reset to the default.

        :raises: BaseException, InternalException, InvalidTypeException,
            LimitExceededException, ResourceNotFoundException
        """
        doc_path = ('update_scaling_parameters_response',
                    'update_scaling_parameters_result',
                    'scaling_parameters')
        params = {'DomainName': domain_name}
        if instance_type is not None:
            params["ScalingParameters.DesiredInstanceType"] = instance_type
        if replication_count is not None:
            params["ScalingParameters.DesiredReplicationCount"] = replication_count
        return self.get_response(doc_path, 'UpdateScalingParameters',
                                 params, verb='POST')

    def update_service_access_policies(self, domain_name, access_policies):
        """
        Updates the policies controlling access to the services in
        this search domain.

        :type domain_name: string
        :param domain_name: A string that represents the name of a
            domain. Domain names must be unique across the domains
            owned by an account within an AWS region. Domain names
            must start with a letter or number and can contain the
            following characters: a-z (lowercase), 0-9, and -
            (hyphen). Uppercase letters and underscores are not
            allowed.

        :type access_policies: string
        :param access_policies: An IAM access policy as described in
            The Access Policy Language in Using AWS Identity and
            Access Management. The maximum size of an access policy
            document is 100KB.

        :raises: BaseException, InternalException, LimitExceededException,
            ResourceNotFoundException, InvalidTypeException
        """
        doc_path = ('update_service_access_policies_response',
                    'update_service_access_policies_result',
                    'access_policies')
        params = {'AccessPolicies': access_policies,
                  'DomainName': domain_name}
        return self.get_response(doc_path, 'UpdateServiceAccessPolicies',
                                 params, verb='POST')
