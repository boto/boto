from boto.dynamodb2.types import Dynamizer


class NEWVALUE(object):
    # A marker for new data added.
    pass


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
        self._orig_data = {}
        self._is_dirty = False
        self._dynamizer = Dynamizer()

        if data:
            self._data = data
            self._is_dirty = True

            for key in data.keys():
                self._orig_data[key] = NEWVALUE

    def __getitem__(self, key):
        return self._data.get(key, None)

    def __setitem__(self, key, value):
        # Stow the original value if present, so we can track what's changed.
        if key in self._data:
            self._orig_data[key] = self._data[key]
        else:
            # Use a marker to indicate we've never seen a value for this key.
            self._orig_data[key] = NEWVALUE

        self._data[key] = value
        self._is_dirty = True

    def __delitem__(self, key):
        if not key in self._data:
            return

        # Stow the original value, so we can track what's changed.
        value = self._data[key]
        del self._data[key]
        self._orig_data[key] = value
        self._is_dirty = True

    def needs_save(self):
        return self._is_dirty

    def mark_clean(self):
        self._orig_data = {}
        self._is_dirty = False

    def mark_dirty(self):
        self._is_dirty = True

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
        """
        Returns a Python-style dict of the keys/values.
        """
        key_fields = self.table.get_key_fields()
        key_data = {}

        for key in key_fields:
            key_data[key] = self[key]

        return key_data

    def get_raw_keys(self):
        """
        Returns a DynamoDB-style dict of the keys/values.
        """
        raw_key_data = {}

        for key, value in self.get_keys().items():
            raw_key_data[key] = self._dynamizer.encode(value)

        return raw_key_data

    def build_expects(self, fields=None):
        expects = {}

        if fields is None:
            fields = self._data.keys() + self._orig_data.keys()

        # Only uniques.
        fields = set(fields)

        for key in fields:
            expects[key] = {
                'Exists': True,
            }
            value = None

            # Check for invalid keys.
            if not key in self._orig_data and not key in self._data:
                raise ValueError("Unknown key %s provided." % key)

            # States:
            # * New field (_data & _orig_data w/ marker)
            # * Unchanged field (only _data)
            # * Modified field (_data & _orig_data)
            # * Deleted field (only _orig_data)
            if not key in self._orig_data:
                # Existing field unchanged.
                value = self._data[key]
            else:
                if key in self._data:
                    if self._orig_data[key] is NEWVALUE:
                        # New field.
                        expects[key]['Exists'] = False
                    else:
                        # Existing field modified.
                        value = self._orig_data[key]
                else:
                   # Existing field deleted.
                    value = self._orig_data[key]

            if value is not None:
                expects[key]['Value'] = self._dynamizer.encode(value)

        return expects

    def prepare_full(self):
        # This doesn't save on it's own. Rather, we prepare the datastructure
        # and hand-off to the table to handle creation/update.
        final_data = {}

        for key, value in self._data.items():
            final_data[key] = self._dynamizer.encode(value)

        return final_data

    def prepare_partial(self):
        # This doesn't save on it's own. Rather, we prepare the datastructure
        # and hand-off to the table to handle creation/update.
        final_data = {}

        # Loop over ``_orig_data`` so that we only build up data that's changed.
        for key, value in self._orig_data.items():
            if key in self._data:
                # It changed.
                final_data[key] = {
                    'Action': 'PUT',
                    'Value': self._dynamizer.encode(self._data[key])
                }
            else:
                # It was deleted.
                final_data[key] = {
                    'Action': 'DELETE',
                }

        return final_data

    def partial_save(self):
        if not self.needs_save():
            return False

        key = self.get_keys()
        # Build a new dict of only the data we're changing.
        final_data = self.prepare_partial()
        # Build expectations of only the fields we're planning to update.
        expects = self.build_expects(fields=self._orig_data.keys())
        returned = self.table._update_item(key, final_data, expects=expects)
        # Mark the object as clean.
        self.mark_clean()
        return returned

    def save(self, overwrite=False):
        if not self.needs_save():
            return False

        final_data = self.prepare_full()
        expects = None

        if overwrite is False:
            # Build expectations about *all* of the data.
            expects = self.build_expects()

        returned = self.table._put_item(final_data, expects=expects)
        # Mark the object as clean.
        self.mark_clean()
        return returned

    def delete(self):
        key_data = self.get_keys()
        return self.table.delete_item(**key_data)
