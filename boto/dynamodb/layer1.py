# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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

import boto
from boto.connection import AWSAuthConnection
from boto.exception import DynamoDBResponseError
from boto.provider import Provider
from boto.dynamodb import exceptions as dynamodb_exceptions
from boto.dynamodb.table import Table

import time
try:
    import simplejson as json
except ImportError:
    import json

#
# To get full debug output, uncomment the following line and set the
# value of Debug to be 2
#
#boto.set_stream_logger('dynamodb')
Debug=0

class Layer1(AWSAuthConnection):
    """
    This is the lowest-level interface to DynamoDB.  Methods at this
    layer map directly to API requests and parameters to the methods
    are either simple, scalar values or they are the Python equivalent
    of the JSON input as defined in the DynamoDB Developer's Guide.
    All responses are direct decoding of the JSON response bodies to
    Python data structures via the json or simplejson modules.
    """
    
    DefaultHost = 'dynamodb.us-east-1.amazonaws.com'
    """The default DynamoDB API endpoint to connect to."""

    ServiceName = 'DynamoDB'
    """The name of the Service"""
    
    Version = '20111205'
    """DynamoDB API version."""

    ThruputError = "ProvisionedThroughputExceededException"
    """The error response returned when provisioned throughput is exceeded"""

    SessionExpiredError = 'com.amazon.coral.service#ExpiredTokenException'
    """The error response returned when session token has expired"""
    
    ResponseError = DynamoDBResponseError

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 host=None, debug=0, session_token=None):
        if not host:
            host = self.DefaultHost
        self._passed_access_key = aws_access_key_id
        self._passed_secret_key = aws_secret_access_key
        if not session_token:
            session_token = self._get_session_token()
        self.creds = session_token
        AWSAuthConnection.__init__(self, host,
                                   self.creds.access_key,
                                   self.creds.secret_key,
                                   is_secure, port, proxy, proxy_port,
                                   debug=debug,
                                   security_token=self.creds.session_token)

    def _update_provider(self):
        self.provider = Provider('aws',
                                 self.creds.access_key,
                                 self.creds.secret_key,
                                 self.creds.session_token)
        self._auth_handler.update_provider(self.provider)
        
    def _get_session_token(self):
        boto.log.debug('Creating new Session Token')
        sts = boto.connect_sts(self._passed_access_key,
                               self._passed_secret_key)
        return sts.get_session_token()

    def _required_auth_capability(self):
        return ['hmac-v3-http']

    def make_request(self, action, body='', object_hook=None):
        """
        :raises: ``DynamoDBExpiredTokenError`` if the security token expires.
        """
        headers = {'X-Amz-Target' : '%s_%s.%s' % (self.ServiceName,
                                                  self.Version, action),
                   'Content-Type' : 'application/x-amz-json-1.0',
                   'Content-Length' : str(len(body))}
        http_request = self.build_base_http_request('POST', '/', '/',
                                                    {}, headers, body, None)
        response = self._mexe(http_request, sender=None,
                              override_num_retries=10,
                              retry_handler=self._retry_handler)
        response_body = response.read()
        boto.log.debug(response_body)
        return json.loads(response_body, object_hook=object_hook)

    def _retry_handler(self, response, i, next_sleep):
        status = None
        if response.status == 400:
            response_body = response.read()
            boto.log.debug(response_body)
            json_response = json.loads(response_body)
            if self.ThruputError in json_response.get('__type'):
                print 'Throughput Throttled'
                msg = "%s, retry attempt %s" % (self.ThruputError, i)
                if i == 0:
                    next_sleep = 0
                else:
                    next_sleep = 0.05 * (2**i)
                i += 1
                status = (msg, i, next_sleep)
            elif self.SessionExpiredError in json_response.get('__type'):
                msg = 'Renewing Session Token'
                self.creds = self._get_session_token()
                self._update_provider()
                status = (msg, i+self.num_retries-1, next_sleep)
            else:
                raise self.ResponseError(response.status, response.reason,
                                         json_response)
        return status

    def list_tables(self, limit=None, start_table=None):
        """
        Return a list of table names associated with the current account
        and endpoint.

        :type limit: int
        :param limit: The maximum number of tables to return.

        :type start_table: str
        :param limit: The name of the table that starts the
            list.  If you ran a previous list_tables and not
            all results were returned, the response dict would
            include a LastEvaluatedTableName attribute.  Use
            that value here to continue the listing.
        """
        data = {}
        if limit:
            data['Limit'] = limit
        if start_table:
            data['ExclusiveStartTableName'] = start_table
        json_input = json.dumps(data)
        return self.make_request('ListTables', json_input)

    def describe_table(self, table_name):
        """
        Returns information about the table including current
        state of the table, primary key schema and when the
        table was created.

        :type table_name: str
        :param table_name: The name of the table to delete.
        """
        data = {'TableName' : table_name}
        json_input = json.dumps(data)
        return self.make_request('DescribeTable', json_input)

    def create_table(self, table_name, schema, provisioned_throughput):
        """
        Add a new table to your account.  The table name must be unique
        among those associated with the account issuing the request.
        This request triggers an asynchronous workflow to begin creating
        the table.  When the workflow is complete, the state of the
        table will be ACTIVE.

        :type table_name: str
        :param table_name: The name of the table to delete.
        
        :type schema: dict
        :param schema: A Python version of the KeySchema data structure
            as defined by DynamoDB

        :type provisioned_throughput: dict
        :param provisioned_throughput: A Python version of the
            ProvisionedThroughput data structure defined by
            DynamoDB.
        
        """
        data = {'TableName' : table_name,
                'KeySchema' : schema,
                'ProvisionedThroughput': provisioned_throughput}
        json_input = json.dumps(data)
        response_dict = self.make_request('CreateTable', json_input)
        return response_dict

    def update_table(self, table_name, provisioned_throughput):
        """
        Updates the provisioned throughput for a given table.
        
        :type table_name: str
        :param table_name: The name of the table to delete.
        
        :type provisioned_throughput: dict
        :param provisioned_throughput: A Python version of the
            ProvisionedThroughput data structure defined by
            DynamoDB.
        """
        data = {'TableName': table_name,
                'ProvisionedThroughput': provisioned_throughput}
        json_input = json.dumps(data)
        return self.make_request('UpdateTable', json_input)

    def delete_table(self, table_name):
        """
        Deletes the table and all of it's data.  After this request
        the table will be in the DELETING state until DynamoDB
        completes the delete operation.

        :type table_name: str
        :param table_name: The name of the table to delete.
        """
        data = {'TableName': table_name}
        json_input = json.dumps(data)
        return self.make_request('DeleteTable', json_input)

    def get_item(self, table_name, key, attributes_to_get=None,
                 consistent_read=False, object_hook=None):
        """
        Return a set of attributes for an item that matches
        the supplied key.

        :type table_name: str
        :param table_name: The name of the table to delete.

        :type key: dict
        :param key: A Python version of the Key data structure
            defined by DynamoDB.

        :type attributes_to_get: list
        :param attributes_to_get: A list of attribute names.
            If supplied, only the specified attribute names will
            be returned.  Otherwise, all attributes will be returned.

        :type consistent_read: bool
        :param consistent_read: If True, a consistent read
            request is issued.  Otherwise, an eventually consistent
            request is issued.
        """
        data = {'TableName': table_name,
                'Key': key}
        if attributes_to_get:
            data['AttributesToGet'] = attributes_to_get
        if consistent_read:
            data['ConsistentRead'] = True
        json_input = json.dumps(data)
        response = self.make_request('GetItem', json_input,
                                     object_hook=object_hook)
        if not response.has_key('Item'):
            raise dynamodb_exceptions.DynamoDBKeyNotFoundError(
                "Key does not exist."
            )
        return response
        
    def batch_get_item(self, request_items, object_hook=None):
        """
        Return a set of attributes for a multiple items in
        multiple tables using their primary keys.

        :type request_items: dict
        :param request_items: A Python version of the RequestItems
            data structure defined by DynamoDB.
        """
        data = {'RequestItems' : request_items}
        json_input = json.dumps(data)
        return self.make_request('BatchGetItem', json_input,
                                 object_hook=object_hook)

    def put_item(self, table_name, item,
                 expected=None, return_values=None,
                 object_hook=None):
        """
        Create a new item or replace an old item with a new
        item (including all attributes).  If an item already
        exists in the specified table with the same primary
        key, the new item will completely replace the old item.
        You can perform a conditional put by specifying an
        expected rule.

        :type table_name: str
        :param table_name: The name of the table to delete.

        :type item: dict
        :param item: A Python version of the Item data structure
            defined by DynamoDB.

        :type expected: dict
        :param expected: A Python version of the Expected
            data structure defined by DynamoDB.

        :type return_values: str
        :param return_values: Controls the return of attribute
            name-value pairs before then were changed.  Possible
            values are: None or 'ALL_OLD'. If 'ALL_OLD' is
            specified and the item is overwritten, the content
            of the old item is returned.
        """
        data = {'TableName' : table_name,
                'Item' : item}
        if expected:
            data['Expected'] = expected
        if return_values:
            data['ReturnValues'] = return_values
        json_input = json.dumps(data)
        return self.make_request('PutItem', json_input,
                                 object_hook=object_hook)

    def update_item(self, table_name, key, attribute_updates,
                    expected=None, return_values=None,
                    object_hook=None):
        """
        Delete an item and all of it's attributes by primary key.
        You can perform a conditional delete by specifying an
        expected rule.

        :type table_name: str
        :param table_name: The name of the table to delete.

        :type key: dict
        :param key: A Python version of the Key data structure
            defined by DynamoDB.

        :type attribute_updates: dict
        :param attribute_updates: A Python version of the AttributeUpdates
            data structure defined by DynamoDB.

        :type expected: dict
        :param expected: A Python version of the Expected
            data structure defined by DynamoDB.

        :type return_values: str
        :param return_values: Controls the return of attribute
            name-value pairs before then were changed.  Possible
            values are: None or 'ALL_OLD'. If 'ALL_OLD' is
            specified and the item is overwritten, the content
            of the old item is returned.
        """
        data = {'TableName' : table_name,
                'Key' : key,
                'AttributeUpdates': attribute_updates}
        if expected:
            data['Expected'] = expected
        if return_values:
            data['ReturnValues'] = return_values
        json_input = json.dumps(data)
        return self.make_request('UpdateItem', json_input,
                                 object_hook=object_hook)

    def delete_item(self, table_name, key,
                    expected=None, return_values=None,
                    object_hook=None):
        """
        Delete an item and all of it's attributes by primary key.
        You can perform a conditional delete by specifying an
        expected rule.

        :type table_name: str
        :param table_name: The name of the table to delete.

        :type key: dict
        :param key: A Python version of the Key data structure
            defined by DynamoDB.

        :type expected: dict
        :param expected: A Python version of the Expected
            data structure defined by DynamoDB.

        :type return_values: str
        :param return_values: Controls the return of attribute
            name-value pairs before then were changed.  Possible
            values are: None or 'ALL_OLD'. If 'ALL_OLD' is
            specified and the item is overwritten, the content
            of the old item is returned.
        """
        data = {'TableName' : table_name,
                'Key' : key}
        if expected:
            data['Expected'] = expected
        if return_values:
            data['ReturnValues'] = return_values
        json_input = json.dumps(data)
        return self.make_request('DeleteItem', json_input,
                                 object_hook=object_hook)

    def query(self, table_name, hash_key_value, range_key_conditions=None,
              attributes_to_get=None, limit=None, consistent_read=False,
              scan_index_forward=True, exclusive_start_key=None,
              object_hook=None):
        """
        Perform a query of DynamoDB.  This version is currently punting
        and expecting you to provide a full and correct JSON body
        which is passed as is to DynamoDB.

        :type table_name: str
        :param table_name: The name of the table to delete.

        :type hash_key_value: dict
        :param key: A DynamoDB-style HashKeyValue.

        :type range_key_conditions: dict
        :param range_key_conditions: A Python version of the
            RangeKeyConditions data structure.

        :type attributes_to_get: list
        :param attributes_to_get: A list of attribute names.
            If supplied, only the specified attribute names will
            be returned.  Otherwise, all attributes will be returned.

        :type limit: int
        :param limit: The maximum number of items to return.

        :type consistent_read: bool
        :param consistent_read: If True, a consistent read
            request is issued.  Otherwise, an eventually consistent
            request is issued.

        :type scan_index_forward: bool
        :param scan_index_forward: Specified forward or backward
            traversal of the index.  Default is forward (True).

        :type exclusive_start_key: list or tuple
        :param exclusive_start_key: Primary key of the item from
            which to continue an earlier query.  This would be
            provided as the LastEvaluatedKey in that query.
        """
        data = {'TableName': table_name,
                'HashKeyValue': hash_key_value}
        if range_key_conditions:
            data['RangeKeyConditions'] = range_key_conditions
        if attributes_to_get:
            data['AttributesToGet'] = attributes_to_get
        if limit:
            data['Limit'] = limit
        if consistent_read:
            data['ConsistentRead'] = True
        if scan_index_forward:
            data['ScanIndexForward'] = True
        else:
            data['ScanIndexForward'] = False
        if exclusive_start_key:
            data['ExclusiveStartKey'] = exclusive_start_key
        json_input = json.dumps(data)
        return self.make_request('Query', json_input,
                                 object_hook=object_hook)

    def scan(self, table_name, scan_filter=None,
             attributes_to_get=None, limit=None,
             count=False, exclusive_start_key=None,
             object_hook=None):
        """
        Perform a scan of DynamoDB.  This version is currently punting
        and expecting you to provide a full and correct JSON body
        which is passed as is to DynamoDB.

        :type table_name: str
        :param table_name: The name of the table to scan.

        :type scan_filter: dict
        :param scan_filter: A Python version of the
            ScanFilter data structure.

        :type attributes_to_get: list
        :param attributes_to_get: A list of attribute names.
            If supplied, only the specified attribute names will
            be returned.  Otherwise, all attributes will be returned.

        :type limit: int
        :param limit: The maximum number of items to return.

        :type count: bool
        :param count: If True, Amazon DynamoDB returns a total
            number of items for the Scan operation, even if the
            operation has no matching items for the assigned filter.

        :type exclusive_start_key: list or tuple
        :param exclusive_start_key: Primary key of the item from
            which to continue an earlier query.  This would be
            provided as the LastEvaluatedKey in that query.
        """
        data = {'TableName': table_name}
        if scan_filter:
            data['ScanFilter'] = scan_filter
        if attributes_to_get:
            data['AttributesToGet'] = attributes_to_get
        if limit:
            data['Limit'] = limit
        if count:
            data['Count'] = True
        if exclusive_start_key:
            data['ExclusiveStartKey'] = exclusive_start_key
        json_input = json.dumps(data)
        return self.make_request('Scan', json_input, object_hook=object_hook)

    
