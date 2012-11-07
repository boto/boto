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
import math


_MEGABYTE = 1024 * 1024
DEFAULT_PART_SIZE = 4 * _MEGABYTE
MAXIMUM_NUMBER_OF_PARTS = 10000


def minimum_part_size(size_in_bytes):
    # The default part size (4 MB) will be too small for a very large
    # archive, as there is a limit of 10,000 parts in a multipart upload.
    # This puts the maximum allowed archive size with the default part size
    # at 40,000 MB. We need to do a sanity check on the part size, and find
    # one that works if the default is too small.
    part_size = _MEGABYTE
    if (DEFAULT_PART_SIZE * MAXIMUM_NUMBER_OF_PARTS) < size_in_bytes:
        if size_in_bytes > (4096 * _MEGABYTE * 10000):
            raise ValueError("File size too large: %s" % size_in_bytes)
        min_part_size = size_in_bytes / 10000
        power = 2
        while part_size < min_part_size:
            part_size = math.ldexp(_MEGABYTE, power)
            power += 1
        part_size = int(part_size)
    else:
        part_size = DEFAULT_PART_SIZE
    return part_size
