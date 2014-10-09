#!/usr/bin/env python
# Copyright (c) 2006-2011 Mitch Garnaat http://garnaat.org/
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
from __future__ import print_function

import argparse
import os
import sys

from nose.core import run


# This is a whitelist of unit tests that support Python 3.
# When porting a new module to Python 3, please update this
# list so that its tests will run by default. See the
# `default` target below for more information.
# We use this instead of test attributes/tags because in
# order to filter on tags nose must load each test - many
# will fail to import with Python 3.
PY3_WHITELIST = (
    'tests/unit/auth',
    'tests/unit/beanstalk',
    'tests/unit/cloudformation',
    'tests/unit/cloudfront',
    'tests/unit/cloudsearch',
    'tests/unit/cloudsearch2',
    'tests/unit/cloudtrail',
    'tests/unit/directconnect',
    'tests/unit/dynamodb',
    'tests/unit/dynamodb2',
    'tests/unit/ecs',
    'tests/unit/elasticache',
    'tests/unit/emr',
    'tests/unit/glacier',
    'tests/unit/iam',
    'tests/unit/ec2',
    'tests/unit/logs',
    'tests/unit/manage',
    'tests/unit/mws',
    'tests/unit/provider',
    'tests/unit/rds2',
    'tests/unit/route53',
    'tests/unit/s3',
    'tests/unit/sns',
    'tests/unit/ses',
    'tests/unit/sqs',
    'tests/unit/sts',
    'tests/unit/swf',
    'tests/unit/utils',
    'tests/unit/vpc',
    'tests/unit/test_connection.py',
    'tests/unit/test_exception.py',
    'tests/unit/test_regioninfo.py',
)


def main(whitelist=[]):
    description = ("Runs boto unit and/or integration tests. "
                   "Arguments will be passed on to nosetests. "
                   "See nosetests --help for more information.")
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-t', '--service-tests', action="append", default=[],
                        help="Run tests for a given service.  This will "
                        "run any test tagged with the specified value, "
                        "e.g -t s3 -t ec2")
    known_args, remaining_args = parser.parse_known_args()
    attribute_args = []
    for service_attribute in known_args.service_tests:
        attribute_args.extend(['-a', '!notdefault,' + service_attribute])
    if not attribute_args:
        # If the user did not specify any filtering criteria, we at least
        # will filter out any test tagged 'notdefault'.
        attribute_args = ['-a', '!notdefault']

    # Set default tests used by e.g. tox. For Py2 this means all unit
    # tests, while for Py3 it's just whitelisted ones.
    if 'default' in remaining_args:
        # Run from the base project directory
        os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        for i, arg in enumerate(remaining_args):
            if arg == 'default':
                if sys.version_info[0] == 3:
                    del remaining_args[i]
                    remaining_args += PY3_WHITELIST
                else:
                    remaining_args[i] = 'tests/unit'

    all_args = [__file__] + attribute_args + remaining_args
    print("nose command:", ' '.join(all_args))
    if run(argv=all_args):
        # run will return True is all the tests pass.  We want
        # this to equal a 0 rc
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
