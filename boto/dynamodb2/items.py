from boto.dynamodb2.types import Dynamizer


class Item(object):
    """


    Example::

        >>> from boto.dynamodb2.items import Item
        >>> from boto.dynamodb2.table import Table
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
        key_fields = self.table.get_key_fields()
        key_data = {}

        for key in key_fields:
            key_data[key] = self[key]

        return self.table.delete_item(**key_data)
