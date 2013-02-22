import sys

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3:
    integer_types = int,
else:
    integer_types = (int, long)

try:
    # Python 2
    xrange = xrange
except NameError:
    xrange = range

try:
    # Python 2
    basestring = basestring
except NameError:
    basestring = str

try:
    # Python 2
    from urllib import quote, quote_plus
except ImportError:
    # Python 3
    from urllib.parse import quote, quote_plus

try:
    # Python 2
    from urlparse import urlparse
except ImportError:
    # Python 3
    from urllib.parse import urlparse

def ensure_bytes(bytes_or_str):
    if isinstance(bytes_or_str, bytes):
        return bytes_or_str
    else:
        return bytes_or_str.encode('latin-1')

