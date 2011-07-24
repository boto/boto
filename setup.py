#!/usr/bin/env python

# Copyright (c) 2006-2010 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2010, Eucalyptus Systems, Inc.
# All rights reserved.
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

try:
    from setuptools import setup
    extra = {"test_suite": "tests.test.suite"}
except ImportError:
    from distutils.core import setup
    extra = {}

import sys

from boto import __version__

if sys.version_info <= (2, 4):
    error = "ERROR: boto requires Python Version 2.5 or above...exiting."
    print >> sys.stderr, error
    sys.exit(1)

setup(name = "boto",
      version = __version__,
      description = "Amazon Web Services Library",
      long_description = "Python interface to Amazon's Web Services.",
      author = "Mitch Garnaat",
      author_email = "mitch@garnaat.com",
      scripts = ["bin/sdbadmin", "bin/elbadmin", "bin/cfadmin",
                 "bin/s3put", "bin/fetch_file", "bin/launch_instance",
                 "bin/list_instances", "bin/taskadmin", "bin/kill_instance",
                 "bin/bundle_image", "bin/pyami_sendmail", "bin/lss3",
                 "bin/cq", "bin/route53"],
      url = "http://code.google.com/p/boto/",
      packages = ["boto", "boto.sqs", "boto.s3", "boto.gs", "boto.file",
                  "boto.ec2", "boto.ec2.cloudwatch", "boto.ec2.autoscale",
                  "boto.ec2.elb", "boto.sdb", "boto.cacerts",
                  "boto.sdb.db", "boto.sdb.db.manager", "boto.mturk",
                  "boto.pyami", "boto.mashups", "boto.contrib", "boto.manage",
                  "boto.services", "boto.cloudfront", "boto.roboto",
                  "boto.rds", "boto.vpc", "boto.fps", "boto.emr", "boto.sns",
                  "boto.ecs", "boto.iam", "boto.route53", "boto.ses",
                  "boto.cloudformation"],
      license = "MIT",
      platforms = "Posix; MacOS X; Windows",
      classifiers = ["Development Status :: 5 - Production/Stable",
                     "Intended Audience :: Developers",
                     "License :: OSI Approved :: MIT License",
                     "Operating System :: OS Independent",
                     "Topic :: Internet"],
      **extra
      )
