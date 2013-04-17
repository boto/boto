from boto.dynamodb2.constants import (STRING, NUMBER, BINARY,
                                      STRING_SET, NUMBER_SET, BINARY_SET)
from boto.dynamodb2 import exceptions
from boto.dynamodb2.layer1 import DynamoDBConnection
from boto.dynamodb2.types import Dynamizer



class BaseSchemaField(object):
    """
    An abstract class for defining schema fields.

    Contains most of the core functionality for the field. Subclasses must
    define an ``attr_type`` to pass to DynamoDB.
    """
    def __init__(self, name, data_type=STRING):
        self.name = name
        self.data_type = data_type

    def definition(self):
        return {
            'AttributeName': self.name,
            'AttributeType': self.attr_type,
        }

    def schema(self):
        return {
            'AttributeName': self.name,
            'KeyType': self.data_type,
        }


class HashKey(BaseSchemaField):
    attr_type = 'HASH'


class RangeKey(BaseSchemaField):
    attr_type = 'RANGE'


class BaseIndexField(object):
    """

    Example::

        >>> AllIndex('MostRecentlyJoined', parts=[
        ...     HashKey('username'),
        ...     RangeKey('date_joined')
        ... ])
        >>> KeysOnlyIndex('MostRecentlyJoined', parts=[
        ...     HashKey('username'),
        ...     RangeKey('date_joined')
        ... ])
        >>> IncludeIndex('GenderIndex', parts=[
        ...     HashKey('username'),
        ...     RangeKey('date_joined')
        ... ], includes=['gender'])

    """
    def __init__(self, name, parts):
        self.name = name
        self.parts = parts

    def definition(self):
        definition = []

        for part in self.parts:
            definition.append({
                'AttributeName': part.name,
                'AttributeType': part.attr_type,
            })

        return definition

    def schema(self):
        key_schema = []

        for part in self.parts:
            key_schema.append(part.schema())

        return {
            'IndexName': self.name,
            'KeySchema': key_schema,
            'Projection': {
                'ProjectionType': self.projection_type,
            }
        }


class AllIndex(BaseIndexField):
    projection_type = 'ALL'


class KeysOnlyIndex(BaseIndexField):
    projection_type = 'KEYS_ONLY'


class IncludeIndex(BaseIndexField):
    projection_type = 'INCLUDE'

    def __init__(self, *args, **kwargs):
        self.includes_fields = kwargs.pop('includes', [])
        super(IncludeIndex, self).__init__(*args, **kwargs)

    def schema(self):
        schema_data = super(IncludeIndex, self).schema()
        schema_data['Projection']['NonKeyAttributes'] = self.includes_fields
        return schema_data


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

    def __getitem__(self, key):
        # TODO: Is ``None`` a safe assumption here?
        return self._data.get(key, None)

    def __setitem__(self, key, value):
        self._data[key] = value
        self._dirty_data[key] = value

    def needs_save(self):
        return len(self._dirty_data)

    def mark_clean(self):
        self._dirty_data = {}

    def load(self, data):
        """
        This is only useful when being handed raw data from DynamoDB directly.
        If you have a Python datastructure already, use the ``__init__`` or
        manually set the data instead.
        """
        self._data = {}

        for field_name, field_value in data.get('Items', {}):
            self[field_name] = self._dynamizer.decode(field_value)

        self.mark_clean()

    def get_keys(self):
        key_fields = self.table.get_key_fields()
        key_data = {}

        for key in key_fields:
            key_data[key] = self._dynamizer(self[key])

        return key_data

    def prepare(self):
        # This doesn't save on it's own. Rather, we prepare the datastructure
        # and hand-off to the table to handle creation/update.
        final_data = {}

        for key, value in self._data:
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


class Table(object):
    """

    Example::

        >>> from boto.dynamodb.table import Table, HashKey, RangeKey, NUMBER
        >>> users = Table('users')

        # Create the table.
        # TODO: This is missing the other options (attributes, provisioning,
        #       lsi).
        >>> users.create(schema=[
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
        >>> jane = users.get_item('jane')

        # Change & store the updated user.
        # TODO: I don't love this (would rather expose as attributes) but then
        #       we introduce reserved names. :/ Thoughts?
        >>> jane.set('friends', ['johndoe'])
        >>> jane.save()

        # TODO: Too Django-like? But it is a shorter syntax...
        >>> names_with_j = users.query({'username__begins_with': 'j'}, limit=5)

        >>> all_users = users.scan()

        # Batching!
        >>> with users.batch() as batch:
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
    throughput = {
        'read': 5,
        'write': 5,
    }

    def __init__(self, table_name, connection=None):
        self.table_name = table_name
        self.connection = connection
        self.schema = None
        self.indexes = None

        if self.connection is None:
            self.connection = DynamoDBConnection()

    def create(self, schema, throughput=None, indexes=None):
        """

        Example::

            >>> users = Table('users')
            >>> users.create_table(schema=[
            ...     HashKey('username'),
            ...     RangeKey('date_joined', data_type=NUMBER)
            ... ], throughput={
            ...     'read':20,
            ...     'write': 10,
            ... }, indexes=[
            ...     KeysOnlyIndex('MostRecentlyJoined', RangeKey('date_joined')), # ???!!!
            ... ])

        """
        self.schema = schema

        if throughput is not None:
            self.throughput = throughput

        if indexes is not None:
            self.indexes = indexes

        # Prep the schema.
        raw_schema = []
        attribute_definitions = []

        for field in self.schema:
            raw_schema.append(field.schema())
            # Build the attributes off what we know.
            attribute_definitions.append(field.definition())

        raw_throughput = {
            'ReadCapacityUnits': int(self.throughput['read']),
            'WriteCapacityUnits': int(self.throughput['write']),
        }
        kwargs = {}

        if self.indexes:
            # Prep the LSIs.
            raw_lsi = []

            for index_field in self.indexes:
                raw_lsi.append(index_field.schema())
                # Again, build the attributes off what we know.
                attribute_definitions.append(index_field.definition())

            kwargs['local_secondary_indexes'] = raw_lsi

        result = self.connection.create_table(
            self.table_name,
            attribute_definitions,
            raw_schema,
            raw_throughput,
            **kwargs
        )
        return True

    def describe(self):
        # FIXME: This is super-leaky.
        return self.connection.describe_table(self.table_name)

    def delete(self):
        self.connection.delete_table(self.table_name)
        return True

    def get_item(self, key):
        item_data = self.connection.get_item(self.table_name, key)
        item = Item(self)
        item.load(item_data)
        return item

    def put_item(self, data):
        """
        Public API for creating an item.
        """
        item = Item(self, data=data)
        return item.save()

    def delete_item(self, key):
        self.connection.delete_item(self.table_name, key)
        return True

    def query(self, query_data, limit=None):
        pass

    def scan(self, key=None, index=None):
        pass

    def get_key_fields(self):
        return [field.name for field in self.schema]

    def _put_item(self, item_data):
        self.connection.create_item(self.table_name, item_data)
        return True


class BatchTable(object):
    def __init__(self, table):
        self.table = table
        self._to_put = []
        self._to_delete = []

    def __enter__(self):
        return self

    def __exit__(self):
        if not self._to_put and not self._to_delete:
            return False

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
            item = Item(self.table, data=put)
            batch_data[self.table.table_name].append({
                'DeleteRequest': {
                    'Key': item.get_keys(),
                }
            })

        self.table.connection.batch_write_item(self.table_name, batch_data)
        return True
