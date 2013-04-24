from boto.dynamodb2 import exceptions
from boto.dynamodb2.fields import (HashKey, RangeKey,
                                   AllIndex, KeysOnlyIndex, IncludeIndex)
from boto.dynamodb2.layer1 import DynamoDBConnection
from boto.dynamodb2.types import Dynamizer, FILTER_OPERATORS


class Item(object):
    """


    Example::

        >>> from boto.dynamodb2.table import Item, Table
        >>> users = Table('users')
        >>> johndoe = Item(users, {
        ...     'username': 'johndoe',
        ...     'first_name': 'John',
        ...     'last_name': 'Doe',
        ...     'date_joined': int(time.time()),
        ...     'friend_count': 3,
        ...     'friends': ['alice', 'bob', 'jane']
        ... })
        >>> item.save()
        # A second save does nothing, since the data hasn't changed.
        >>> item.save()

        # Manipulate the values.
        >>> johndoe['friend_count'] = 2
        >>> johndoe['friends'] = ['alice', 'bob']
        >>> johndoe.needs_save()
        True
        >>> johndoe.save()

        # All done. Clean up.
        >>> johndoe.delete()

    """
    def __init__(self, table, data=None):
        self.table = table
        self._data = {}
        self._dirty_data = {}
        self._dynamizer = Dynamizer()

        if data:
            self._data = data
            self._dirty_data = data

    def __getitem__(self, key):
        # TODO: Is ``None`` a safe assumption here?
        return self._data.get(key, None)

    def __setitem__(self, key, value):
        self._data[key] = value
        self._dirty_data[key] = value

    def needs_save(self):
        return len(self._dirty_data) != 0

    def mark_clean(self):
        self._dirty_data = {}

    def load(self, data):
        """
        This is only useful when being handed raw data from DynamoDB directly.
        If you have a Python datastructure already, use the ``__init__`` or
        manually set the data instead.
        """
        self._data = {}

        for field_name, field_value in data.get('Item', {}).items():
            self[field_name] = self._dynamizer.decode(field_value)

        self.mark_clean()

    def get_keys(self):
        key_fields = self.table.get_key_fields()
        key_data = {}

        for key in key_fields:
            key_data[key] = self._dynamizer.encode(self[key])

        return key_data

    def prepare(self):
        # This doesn't save on it's own. Rather, we prepare the datastructure
        # and hand-off to the table to handle creation/update.
        final_data = {}

        for key, value in self._data.items():
            final_data[key] = self._dynamizer.encode(value)

        return final_data

    def save(self):
        if not self.needs_save():
            return False

        final_data = self.prepare()
        returned = self.table._put_item(final_data)
        # Mark the object as clean.
        self.mark_clean()
        return returned

    def delete(self):
        key_data = self.get_keys()
        return self.table.delete_item(key=key_data)


class ResultSet(object):
    """

    Example::

        >>> users = Table('users')
        >>> results = ResultSet()
        >>> results.to_call(users.query, username__gte='johndoe')
        # Now iterate. When it runs out of results, it'll fetch the next page.
        >>> for res in results:
        ...     print res['username']
    """
    def __init__(self):
        super(ResultSet, self).__init__()
        self.the_callable = None
        self.call_args = []
        self.call_kwargs = {}
        self._results = []
        self._offset = -1
        self._results_left = True
        self._last_key_seen = None

    @property
    def first_key(self):
        return 'exclusive_start_key'

    def __iter__(self):
        return self

    def next(self):
        self._offset += 1

        if self._offset >= len(self._results):
            self.fetch_more()

        if self._results_left is False:
            raise StopIteration()

        return self._results[self._offset]

    def to_call(self, the_callable, *args, **kwargs):
        if not callable(the_callable):
            raise ValueError(
                'You must supply an object or function to be called.'
            )

        self.the_callable = the_callable
        self.call_args = args
        self.call_kwargs = kwargs

    def fetch_more(self):
        args = self.call_args[:]
        kwargs = self.call_kwargs.copy()

        if self._last_key_seen is not None:
            kwargs[self.first_key] = self._last_key_seen

        results = self.the_callable(*args, **kwargs)

        if not len(results.get('results', [])):
            self._results_left = False
            return

        self._results.extend(results['results'])
        self._last_key_seen = results.get('last_key', None)

        if self._last_key_seen is None:
            self._results_left = False

        # Decrease the limit, if it's present.
        if 'limit' in self.call_kwargs:
            self.call_kwargs['limit'] -= len(results['results'])


class Table(object):
    """

    Example::

        >>> from boto.dynamodb.table import Table, HashKey, RangeKey, NUMBER

        # Create the table.
        >>> users = Table.create('users', schema=[
        ...     HashKey('username'),
        ...     RangeKey('date_joined', data_type=NUMBER)
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
        # FIXME: This likely needs to do some locking/concurrency checking.
        >>> jane.save()

        # TODO: Too Django-like? But it is a shorter syntax...
        >>> names_with_j = users.query({'username__begins_with': 'j'}, limit=5)

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
        ...     batch.delete_item(key={'username': 'jane'})

        # Dust off & nuke it from orbit.
        >>> users.delete()

    """
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
            ...     KeysOnlyIndex('MostRecentlyJoined', parts=[RangeKey('date_joined')]),
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
        attribute_definitions = []

        for field in table.schema:
            raw_schema.append(field.schema())
            # Build the attributes off what we know.
            attribute_definitions.append(field.definition())

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
                    if not part['AttributeName'] in [attr['AttributeName'] for attr in attribute_definitions]:
                        attribute_definitions.append(part)

            kwargs['local_secondary_indexes'] = raw_lsi

        table.connection.create_table(
            table.table_name,
            attribute_definitions,
            raw_schema,
            raw_throughput,
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
        self.throughput['read'] = int(result[self.table_name]\
                                            ['ProvisionedThroughput']\
                                            ['ReadCapacityUnits'])
        self.throughput['write'] = int(result[self.table_name]\
                                             ['ProvisionedThroughput']\
                                             ['WriteCapacityUnits'])

        if not self.schema:
            # Since we have the data, build the schema.
            raw_schema = result[self.table_name]['KeySchema']
            self.schema = self._introspect_schema(raw_schema)

        if not self.indexes:
            # Build the index information as well.
            raw_indexes = result[self.table_name]['LocalSecondaryIndexes']
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

    def get_item(self, **kwargs):
        # FIXME: The downside of a kwargs-based approach is the other options to
        #        the low-level ``get_item``. Maybe add ``consistent_get_item``?
        raw_key = self._encode_keys(kwargs)
        item_data = self.connection.get_item(self.table_name, raw_key)
        item = Item(self)
        item.load(item_data)
        return item

    def put_item(self, data):
        """
        Public API for creating an item.
        """
        item = Item(self, data=data)
        return item.save()

    def _put_item(self, item_data):
        self.connection.put_item(self.table_name, item_data)
        return True

    def delete_item(self, **kwargs):
        # FIXME: The downside of a kwargs-based approach is the other options to
        #        the low-level ``get_item``. Maybe add ``consistent_get_item``?
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

    def _build_filters(self, filter_kwargs):
        """
        FIXME: Build something like:

            {
                'username': {
                    'AttributeValueList': [
                        {'S': 'jane'},
                    ],
                    'ComparisonOperator': 'EQ',
                },
                'date_joined': {
                    'AttributeValueList': [
                        {'N': '1366050000'}
                    ],
                    'ComparisonOperator': 'GT',
                }
            }
        """
        filters = {}

        for field_and_op, value in filter_kwargs.items():
            field_bits = field_and_op.split('__')
            fieldname = '__'.join(field_bits[:-1])

            try:
                op = FILTER_OPERATORS[field_bits[-1]]
            except KeyError:
                raise exceptions.UnknownFilterTypeError(
                    "Operator '%s' from '%s' is not recognized." % (
                        field_bits[-1],
                        field_and_op
                    )
                )

            lookup = {
                'AttributeValueList': [],
                # FIXME: Should we assume 'eq' if it's invalid?
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

    def query(self, limit=None, index=None, reverse=False, **filter_kwargs):
        # TODO: Args to support:
        #       * Kwarg-based filters (becomes ``key_conditions``)
        #       * limit
        #       * exclusive_start_key (we manage this)
        #       * index_name
        #       * consistent_read ?!!
        #       * reverse
        results = ResultSet()
        kwargs = filter_kwargs.copy()
        kwargs.update({
            'limit': limit,
            'index': index,
            'reverse': reverse,
        })
        results.to_call(self._query, **kwargs)
        return results

    def _query(self, limit=None, index=None, reverse=False, exclusive_start_key=None, **filter_kwargs):
        kwargs = {
            'limit': limit,
            'index_name': index,
            'scan_index_forward': reverse,
        }

        if exclusive_start_key:
            kwargs['exclusive_start_key'] = {}

            for key, value in exclusive_start_key.items():
                kwargs['exclusive_start_key'][key] = \
                    self._dynamizer.encode(value)

        # Convert the filters into something we can actually use.
        kwargs['key_conditions'] = self._build_filters(filter_kwargs)

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
        kwargs['scan_filter'] = self._build_filters(filter_kwargs)

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

    def batch_get(self, keys):
        # TODO: There's a hard limit of 100 keys. We can do one of two things:
        #       * Throw an exception so the user knows & doesn't use multiple
        #         requests (avoiding additional charges)
        #       * Give them what they want, glossing over the fact that it
        #         takes multiple requests.
        #       I think the latter makes more sense (& is likely what
        #       ``query/scan`` will do), but it needs to be further thought out.

        # TODO: Additional complication: This needs to handle both a subset of
        #       keys returned (due to 1Mb limit) as well as handling more than
        #       100 keys, with possibly/likely both happening at the same time.
        #       Grumble.

        # FIXME: Supplying a list of hashkeys isn't bad. Handling a list of
        #        hash+range keys makes it worse. Does this affect the other
        #        methods using a ``key`` parameter or can those be neatly
        #        handled?

        # TODO: Since this is likely to get paginated, presenting the same
        #       interface as ``query/scan`` would be a smart idea.
        #       Not sure how to deal nicely with all the keys. :/
        results = ResultSet()
        results.to_call(self._batch_get, keys)
        return results

    def _batch_get(self):
        # FIXME: Rage.
        pass

    def count(self):
        # FIXME: This doesn't map directly onto the underlying API but
        #        is a common database-style operation. Use ``scan`` (``query?``)
        #        to build a count?
        pass


class BatchTable(object):
    def __init__(self, table):
        self.table = table
        self._to_put = []
        self._to_delete = []

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        # FIXME: Crap. This swallows exceptions! Don't let it do that!

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
                    'Item': item.prepare(),
                }
            })

        for delete in self._to_delete:
            batch_data[self.table.table_name].append({
                'DeleteRequest': {
                    'Key': self.table._encode_keys(delete),
                }
            })

        self.table.connection.batch_write_item(self.table.table_name, batch_data)
        self._to_put = []
        self._to_delete = []
        return True
