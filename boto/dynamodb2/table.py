from boto.dynamodb2 import exceptions
from boto.dynamodb2.fields import (HashKey, RangeKey,
                                   AllIndex, KeysOnlyIndex, IncludeIndex)
from boto.dynamodb2.items import Item
from boto.dynamodb2.layer1 import DynamoDBConnection
from boto.dynamodb2.results import ResultSet, BatchGetResultSet
from boto.dynamodb2.types import Dynamizer, FILTER_OPERATORS, QUERY_OPERATORS


class Table(object):
    """

    Example::

        >>> from boto.dynamodb2.fields import HashKey, RangeKey
        >>> from boto.dynamodb2.table import Table

        # Create the table.
        >>> users = Table.create('users', schema=[
        ...     HashKey('username'),
        ... ])

        # Create/update a user.
        >>> users.put_item(data={
        ...     'username': 'johndoe',
        ...     'first_name': 'John',
        ...     'last_name': 'Doe',
        ...     'date_joined': int(time.time()),
        ...     'friend_count': 3,
        ...     'friends': ['alice', 'bob', 'jane']
        ... })
        >>> jane = users.get_item(username='jane')

        # Change & store the updated user.
        >>> jane['friends'] = ['johndoe']
        >>> jane.save()

        # Run a query.
        >>> names_with_j = users.query(username__begins_with': 'j', limit=5)

        >>> all_users = users.scan()

        # Batching!
        >>> with users.batch_write() as batch:
        ...     batch.put_item(data={
        ...         'username': 'anotherdoe',
        ...         'first_name': 'Another',
        ...         'last_name': 'Doe',
        ...         'date_joined': int(time.time()),
        ...     })
        ...     batch.put_item(data={
        ...         'username': 'alice',
        ...         'first_name': 'Alice',
        ...         'date_joined': int(time.time()),
        ...     })
        ...     batch.delete_item(username=jane')

        # Dust off & nuke it from orbit.
        >>> users.delete()

    """
    max_batch_get = 100

    def __init__(self, table_name, connection=None):
        self.table_name = table_name
        self.connection = connection
        self.throughput = {
            'read': 5,
            'write': 5,
        }
        self.schema = None
        self.indexes = None

        if self.connection is None:
            self.connection = DynamoDBConnection()

        self._dynamizer = Dynamizer()

    @classmethod
    def create(cls, table_name, schema, throughput=None, indexes=None,
               connection=None):
        """

        Example::

            >>> users = Table.create_table('users', schema=[
            ...     HashKey('username'),
            ...     RangeKey('date_joined', data_type=NUMBER)
            ... ], throughput={
            ...     'read':20,
            ...     'write': 10,
            ... }, indexes=[
            ...     KeysOnlyIndex('MostRecentlyJoined', parts=[
            ...         RangeKey('date_joined')
            ...     ]),
            ... ])

        """
        table = cls(table_name=table_name, connection=connection)
        table.schema = schema

        if throughput is not None:
            table.throughput = throughput

        if indexes is not None:
            table.indexes = indexes

        # Prep the schema.
        raw_schema = []
        attr_defs = []

        for field in table.schema:
            raw_schema.append(field.schema())
            # Build the attributes off what we know.
            attr_defs.append(field.definition())

        raw_throughput = {
            'ReadCapacityUnits': int(table.throughput['read']),
            'WriteCapacityUnits': int(table.throughput['write']),
        }
        kwargs = {}

        if table.indexes:
            # Prep the LSIs.
            raw_lsi = []

            for index_field in table.indexes:
                raw_lsi.append(index_field.schema())
                # Again, build the attributes off what we know.
                # HOWEVER, only add attributes *NOT* already seen.
                attr_define = index_field.definition()

                for part in attr_define:
                    attr_names = [attr['AttributeName'] for attr in attr_defs]

                    if not part['AttributeName'] in attr_names:
                        attr_defs.append(part)

            kwargs['local_secondary_indexes'] = raw_lsi

        table.connection.create_table(
            table_name=table.table_name,
            attribute_definitions=attr_defs,
            key_schema=raw_schema,
            provisioned_throughput=raw_throughput,
            **kwargs
        )
        return table

    def _introspect_schema(self, raw_schema):
        schema = []

        for field in raw_schema:
            if field['KeyType'] == 'HASH':
                schema.append(HashKey(field['AttributeName']))
            elif field['KeyType'] == 'RANGE':
                schema.append(RangeKey(field['AttributeName']))
            else:
                raise exceptions.UnknownSchemaFieldError(
                    "%s was seen, but is unknown. Please report this at "
                    "https://github.com/boto/boto/issues." % field['KeyType']
                )

        return schema

    def _introspect_indexes(self, raw_indexes):
        indexes = []

        for field in raw_indexes:
            index_klass = AllIndex
            kwargs = {
                'parts': []
            }

            if field['Projection']['ProjectionType'] == 'ALL':
                index_klass = AllIndex
            elif field['Projection']['ProjectionType'] == 'KEYS_ONLY':
                index_klass = KeysOnlyIndex
            elif field['Projection']['ProjectionType'] == 'INCLUDE':
                index_klass = IncludeIndex
                kwargs['includes'] = field['Projection']['NonKeyAttributes']
            else:
                raise exceptions.UnknownIndexFieldError(
                    "%s was seen, but is unknown. Please report this at "
                    "https://github.com/boto/boto/issues." % \
                    field['Projection']['ProjectionType']
                )

            name = field['IndexName']
            kwargs['parts'] = self._introspect_schema(field['KeySchema'])
            indexes.append(index_klass(name, **kwargs))

        return indexes

    def describe(self):
        result = self.connection.describe_table(self.table_name)

        # Blindly update throughput, since what's on DynamoDB's end is likely
        # more correct.
        raw_throughput = result['Table']['ProvisionedThroughput']
        self.throughput['read'] = int(raw_throughput['ReadCapacityUnits'])
        self.throughput['write'] = int(raw_throughput['WriteCapacityUnits'])

        if not self.schema:
            # Since we have the data, build the schema.
            raw_schema = result['Table']['KeySchema']
            self.schema = self._introspect_schema(raw_schema)

        if not self.indexes:
            # Build the index information as well.
            raw_indexes = result['Table']['LocalSecondaryIndexes']
            self.indexes = self._introspect_indexes(raw_indexes)

        # This is leaky.
        return result

    def update(self, throughput):
        self.throughput = throughput
        self.connection.update_table(self.table_name, {
            'ReadCapacityUnits': int(self.throughput['read']),
            'WriteCapacityUnits': int(self.throughput['write']),
        })
        return True

    def delete(self):
        self.connection.delete_table(self.table_name)
        return True

    def _encode_keys(self, keys):
        raw_key = {}

        for key, value in keys.items():
            raw_key[key] = self._dynamizer.encode(value)

        return raw_key

    def get_item(self, consistent=False, **kwargs):
        raw_key = self._encode_keys(kwargs)
        item_data = self.connection.get_item(
            self.table_name,
            raw_key,
            consistent_read=consistent
        )
        item = Item(self)
        item.load(item_data)
        return item

    def put_item(self, data, overwrite=False):
        """
        Public API for creating an item.
        """
        item = Item(self, data=data)
        return item.save(overwrite=overwrite)

    def _put_item(self, item_data, expects=None):
        kwargs = {}

        if expects is not None:
            kwargs['expected'] = expects

        self.connection.put_item(self.table_name, item_data, **kwargs)
        return True

    def _update_item(self, key, item_data, expects=None):
        raw_key = self._encode_keys(key)
        kwargs = {}

        if expects is not None:
            kwargs['expected'] = expects

        self.connection.update_item(self.table_name, raw_key, item_data, **kwargs)
        return True

    def delete_item(self, **kwargs):
        raw_key = self._encode_keys(kwargs)
        self.connection.delete_item(self.table_name, raw_key)
        return True

    def get_key_fields(self):
        if not self.schema:
            # We don't know the structure of the table. Get a description to
            # populate the schema.
            self.describe()

        return [field.name for field in self.schema]

    def batch_write(self):
        return BatchTable(self)

    def _build_filters(self, filter_kwargs, using=QUERY_OPERATORS):
        """

        """
        filters = {}

        for field_and_op, value in filter_kwargs.items():
            field_bits = field_and_op.split('__')
            fieldname = '__'.join(field_bits[:-1])

            try:
                op = using[field_bits[-1]]
            except KeyError:
                raise exceptions.UnknownFilterTypeError(
                    "Operator '%s' from '%s' is not recognized." % (
                        field_bits[-1],
                        field_and_op
                    )
                )

            lookup = {
                'AttributeValueList': [],
                'ComparisonOperator': op,
            }

            # Fix up the value for encoding, because it was built to only work
            # with ``set``s.
            if isinstance(value, (list, tuple)):
                value = set(value)

            # Special-case the ``NULL/NOT_NULL`` case.
            if field_bits[-1] == 'null':
                del lookup['AttributeValueList']

                if value is False:
                    lookup['ComparisonOperator'] = 'NOT_NULL'
                else:
                    lookup['ComparisonOperator'] = 'NULL'
            else:
                lookup['AttributeValueList'].append(
                    self._dynamizer.encode(value)
                )

            # Finally, insert it into the filters.
            filters[fieldname] = lookup

        return filters

    def query(self, limit=None, index=None, reverse=False, consistent=False,
              **filter_kwargs):
        results = ResultSet()
        kwargs = filter_kwargs.copy()
        kwargs.update({
            'limit': limit,
            'index': index,
            'reverse': reverse,
            'consistent': consistent,
        })
        results.to_call(self._query, **kwargs)
        return results

    def _query(self, limit=None, index=None, reverse=False, consistent=False,
               exclusive_start_key=None, **filter_kwargs):
        kwargs = {
            'limit': limit,
            'index_name': index,
            'scan_index_forward': reverse,
            'consistent_read': consistent,
        }

        if exclusive_start_key:
            kwargs['exclusive_start_key'] = {}

            for key, value in exclusive_start_key.items():
                kwargs['exclusive_start_key'][key] = \
                    self._dynamizer.encode(value)

        # Convert the filters into something we can actually use.
        kwargs['key_conditions'] = self._build_filters(
            filter_kwargs,
            using=QUERY_OPERATORS
        )

        raw_results = self.connection.query(
            self.table_name,
            **kwargs
        )
        results = []
        last_key = None

        for raw_item in raw_results.get('Items', []):
            item = Item(self)
            item.load({
                'Item': raw_item,
            })
            results.append(item)

        if raw_results.get('LastEvaluatedKey', None):
            last_key = {}

            for key, value in raw_results['LastEvaluatedKey'].items():
                last_key[key] = self._dynamizer.decode(value)

        return {
            'results': results,
            'last_key': last_key,
        }

    def scan(self, limit=None, **filter_kwargs):
        # TODO: Args to support:
        #       * Kwarg-based filters (becomes ``scan_filter``)
        #       * limit
        #       * exclusive_start_key (we manage this)
        results = ResultSet()
        kwargs = filter_kwargs.copy()
        kwargs.update({
            'limit': limit,
        })
        results.to_call(self._scan, **kwargs)
        return results

    def _scan(self, limit=None, exclusive_start_key=None, **filter_kwargs):
        kwargs = {
            'limit': limit,
        }

        if exclusive_start_key:
            kwargs['exclusive_start_key'] = {}

            for key, value in exclusive_start_key.items():
                kwargs['exclusive_start_key'][key] = \
                    self._dynamizer.encode(value)

        # Convert the filters into something we can actually use.
        kwargs['scan_filter'] = self._build_filters(
            filter_kwargs,
            using=FILTER_OPERATORS
        )

        raw_results = self.connection.scan(
            self.table_name,
            **kwargs
        )
        results = []
        last_key = None

        for raw_item in raw_results.get('Items', []):
            item = Item(self)
            item.load({
                'Item': raw_item,
            })
            results.append(item)

        if raw_results.get('LastEvaluatedKey', None):
            last_key = {}

            for key, value in raw_results['LastEvaluatedKey'].items():
                last_key[key] = self._dynamizer.decode(value)

        return {
            'results': results,
            'last_key': last_key,
        }

    def batch_get(self, keys, consistent=False):
        # TODO: Document that keys needs to be a list of dicts.
        #       Sucks to expose the underlying (weak) API, but grump.
        # We pass the keys to the constructor instead, so it can maintain it's
        # own internal state as to what keeys have been processed.
        results = BatchGetResultSet(keys=keys, max_batch_get=self.max_batch_get)
        results.to_call(self._batch_get, consistent=False)
        return results

    def _batch_get(self, keys, consistent=False):
        items = {
            self.table_name: {
                'Keys': [],
            },
        }

        if consistent:
            items[self.table_name]['ConsistentRead'] = True

        for key_data in keys:
            raw_key = {}

            for key, value in key_data.items():
                raw_key[key] = self._dynamizer.encode(value)

            items[self.table_name]['Keys'].append(raw_key)

        raw_results = self.connection.batch_get_item(request_items=items)
        results = []
        unprocessed_keys = []

        for raw_item in raw_results['Responses'].get(self.table_name, []):
            item = Item(self)
            item.load({
                'Item': raw_item,
            })
            results.append(item)

        raw_unproccessed = raw_results.get('UnprocessedKeys', {})

        for raw_key in raw_unproccessed.get('Keys', []):
            py_key = {}

            for key, value in raw_key.items():
                py_key[key] = self._dynamizer.decode(value)

            unprocessed_keys.append(py_key)

        return {
            'results': results,
            # NEVER return a ``last_key``. Just in-case
            'last_key': None,
            'unprocessed_keys': unprocessed_keys,
        }

    def count(self):
        info = self.describe()
        return info['Table'].get('ItemCount', 0)


class BatchTable(object):
    def __init__(self, table):
        self.table = table
        self._to_put = []
        self._to_delete = []

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if not self._to_put and not self._to_delete:
            return False

        # Flush anything that's left.
        self.flush()
        return True

    def put_item(self, data):
        self._to_put.append(data)

        if self.should_flush():
            self.flush()

    def delete_item(self, **kwargs):
        self._to_delete.append(kwargs)

        if self.should_flush():
            self.flush()

    def should_flush(self):
        if len(self._to_put) + len(self._to_delete) == 25:
            return True

        return False

    def flush(self):
        batch_data = {
            self.table.table_name: [
                # We'll insert data here shortly.
            ],
        }

        for put in self._to_put:
            item = Item(self.table, data=put)
            batch_data[self.table.table_name].append({
                'PutRequest': {
                    'Item': item.prepare_full(),
                }
            })

        for delete in self._to_delete:
            batch_data[self.table.table_name].append({
                'DeleteRequest': {
                    'Key': self.table._encode_keys(delete),
                }
            })

        self.table.connection.batch_write_item(batch_data)
        self._to_put = []
        self._to_delete = []
        return True
