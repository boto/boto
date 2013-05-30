from boto.dynamodb2.types import Dynamizer


class NEWVALUE(object):
    # A marker for new data added.
    pass


class Item(object):
    """
    An object representing the item data within a DynamoDB table.

    An item is largely schema-free, meaning it can contain any data. The only
    limitation is that it must have data for the fields in the ``Table``'s
    schema.

    This object presents a dictionary-like interface for accessing/storing
    data. It also tries to intelligently track how data has changed throughout
    the life of the instance, to be as efficient as possible about updates.
    """
    def __init__(self, table, data=None):
        """
        Constructs an (unsaved) ``Item`` instance.

        To persist the data in DynamoDB, you'll need to call the ``Item.save``
        (or ``Item.partial_save``) on the instance.

        Requires a ``table`` parameter, which should be a ``Table`` instance.
        This is required, as DynamoDB's API is focus around all operations
        being table-level. It's also for persisting schema around many objects.

        Optionally accepts a ``data`` parameter, which should be a dictionary
        of the fields & values of the item.

        Example::

            >>> users = Table('users')
            >>> user = Item(users, data={
            ...     'username': 'johndoe',
            ...     'first_name': 'John',
            ...     'date_joined': 1248o61592,
            ... })

            # Change existing data.
            >>> user['first_name'] = 'Johann'
            # Add more data.
            >>> user['last_name'] = 'Doe'
            # Delete data.
            >>> del user['date_joined']

            # Iterate over all the data.
            >>> for field, val in user.items():
            ...     print "%s: %s" % (field, val)
            username: johndoe
            first_name: John
            date_joined: 1248o61592

        """
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

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __iter__(self):
        for key in self._data:
            yield self._data[key]

    def __contains__(self, key):
        return key in self._data

    def needs_save(self):
        """
        Returns whether or not the data has changed on the ``Item``.

        Example:

            >>> user.needs_save()
            False
            >>> user['first_name'] = 'Johann'
            >>> user.needs_save()
            True

        """
        return self._is_dirty

    def mark_clean(self):
        """
        Marks an ``Item`` instance as no longer needing to be saved.

        Example:

            >>> user.needs_save()
            False
            >>> user['first_name'] = 'Johann'
            >>> user.needs_save()
            True
            >>> user.mark_clean()
            >>> user.needs_save()
            False

        """
        self._orig_data = {}
        self._is_dirty = False

    def mark_dirty(self):
        """
        Marks an ``Item`` instance as needing to be saved.

        Example:

            >>> user.needs_save()
            False
            >>> user.mark_dirty()
            >>> user.needs_save()
            True

        """
        self._is_dirty = True

    def load(self, data):
        """
        This is only useful when being handed raw data from DynamoDB directly.
        If you have a Python datastructure already, use the ``__init__`` or
        manually set the data instead.

        Largely internal, unless you know what you're doing or are trying to
        mix the low-level & high-level APIs.
        """
        self._data = {}

        for field_name, field_value in data.get('Item', {}).items():
            self[field_name] = self._dynamizer.decode(field_value)

        self.mark_clean()

    def get_keys(self):
        """
        Returns a Python-style dict of the keys/values.

        Largely internal.
        """
        key_fields = self.table.get_key_fields()
        key_data = {}

        for key in key_fields:
            key_data[key] = self[key]

        return key_data

    def get_raw_keys(self):
        """
        Returns a DynamoDB-style dict of the keys/values.

        Largely internal.
        """
        raw_key_data = {}

        for key, value in self.get_keys().items():
            raw_key_data[key] = self._dynamizer.encode(value)

        return raw_key_data

    def build_expects(self, fields=None):
        """
        Builds up a list of expecations to hand off to DynamoDB on save.

        Largely internal.
        """
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
        """
        Runs through all fields & encodes them to be handed off to DynamoDB
        as part of an ``save`` (``put_item``) call.

        Largely internal.
        """
        # This doesn't save on it's own. Rather, we prepare the datastructure
        # and hand-off to the table to handle creation/update.
        final_data = {}

        for key, value in self._data.items():
            final_data[key] = self._dynamizer.encode(value)

        return final_data

    def prepare_partial(self):
        """
        Runs through **ONLY** the changed/deleted fields & encodes them to be
        handed off to DynamoDB as part of an ``partial_save`` (``update_item``)
        call.

        Largely internal.
        """
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
        """
        Saves only the changed data to DynamoDB.

        Extremely useful for high-volume/high-write data sets, this allows
        you to update only a handful of fields rather than having to push
        entire items. This prevents many accidental overwrite situations as
        well as saves on the amount of data to transfer over the wire.

        Returns ``True`` on success, ``False`` if no save was performed or
        the write failed.

        Example::

            >>> user['last_name'] = 'Doh!'
            # Only the last name field will be sent to DynamoDB.
            >>> user.partial_save()

        """
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
        """
        Saves all data to DynamoDB.

        By default, this attempts to ensure that none of the underlying
        data has changed. If any fields have changed in between when the
        ``Item`` was constructed & when it is saved, this call will fail so
        as not to cause any data loss.

        If you're sure possibly overwriting data is acceptable, you can pass
        an ``overwrite=True``. If that's not acceptable, you may be able to use
        ``Item.partial_save`` to only write the changed field data.

        Optionally accepts an ``overwrite`` parameter, which should be a
        boolean. If you provide ``True``, the item will be forcibly overwritten
        within DynamoDB, even if another process changed the data in the
        meantime. (Default: ``False``)

        Returns ``True`` on success, ``False`` if no save was performed.

        Example::

            >>> user['last_name'] = 'Doh!'
            # All data on the Item is sent to DynamoDB.
            >>> user.save()

            # If it fails, you can overwrite.
            >>> user.save(overwrite=True)

        """
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
        """
        Deletes the item's data to DynamoDB.

        Returns ``True`` on success.

        Example::

            # Buh-bye now.
            >>> user.delete()

        """
        key_data = self.get_keys()
        return self.table.delete_item(**key_data)
