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

"""
Unit tests!
"""

import logging
import sys
import unittest
import getopt

from testsuite import suite

def __print_cli_usage():
    print "test.py  [-t testsuite] [-v verbosity]"
    print "    -t   run specific testsuite (s3|ssl|s3ver|s3nover|gs|sqs|ec2|sdb|all)"
    print "    -v   verbosity (0|1|2)"

def __run_tests_from_cli():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ht:v:",
                                   ["help", "testsuite", "verbosity"])
    except:
        __print_cli_usage()
        sys.exit(2)
    testsuite = "all"
    verbosity = 1
    for o, a in opts:
        if o in ("-h", "--help"):
            __print_cli_usage()
            sys.exit()
        if o in ("-t", "--testsuite"):
            testsuite = a
        if o in ("-v", "--verbosity"):
            verbosity = int(a)
    if len(args) != 0:
        __print_cli_usage()
        sys.exit()
    try:
        tests = suite(testsuite)
    except ValueError:
        __print_cli_usage()
        sys.exit()
    if verbosity > 1:
        logging.basicConfig(level=logging.DEBUG)
    unittest.TextTestRunner(verbosity=verbosity).run(tests)


if __name__ == "__main__":
    __run_tests_from_cli()
