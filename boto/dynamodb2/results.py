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
            if self._results_left is False:
                raise StopIteration()

            self.fetch_more()

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
        if self.call_kwargs.get('limit'):
            self.call_kwargs['limit'] -= len(results['results'])


class BatchGetResultSet(ResultSet):
    def __init__(self, *args, **kwargs):
        self._keys_left = kwargs.pop('keys', [])
        self._max_batch_get = kwargs.pop('max_batch_get', 100)
        super(BatchGetResultSet, self).__init__(*args, **kwargs)

    def fetch_more(self):
        args = self.call_args[:]
        kwargs = self.call_kwargs.copy()

        # Slice off the max we can fetch.
        kwargs['keys'] = self._keys_left[:self._max_batch_get]
        self._keys_left = self._keys_left[self._max_batch_get:]

        results = self.the_callable(*args, **kwargs)

        if not len(results.get('results', [])):
            self._results_left = False
            return

        self._results.extend(results['results'])

        for offset, key_data in enumerate(results.get('unprocessed_keys', [])):
            # We've got an unprocessed key. Reinsert it into the list.
            # DynamoDB only returns valid keys, so there should be no risk of
            # missing keys ever making it here.
            self._keys_left.insert(offset, key_data)

        if len(self._keys_left) <= 0:
            self._results_left = False

        # Decrease the limit, if it's present.
        if self.call_kwargs.get('limit'):
            self.call_kwargs['limit'] -= len(results['results'])
