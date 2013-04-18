from boto.dynamodb2.constants import STRING


class BaseSchemaField(object):
    """
    An abstract class for defining schema fields.

    Contains most of the core functionality for the field. Subclasses must
    define an ``attr_type`` to pass to DynamoDB.
    """
    attr_type = None

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
