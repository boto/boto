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

from __future__ import with_statement

try:
    from setuptools import setup
    extra = dict(test_suite="tests.test.suite", include_package_data=True)
except ImportError:
    from distutils.core import setup
    extra = {}

import os
import sys
import glob
import shutil

scripts = glob.glob('bin/*')

try:  # Python 3
  from distutils.command.build_py import build_py_2to3 as build_py
  from distutils.util import run_2to3
  extra['use_2to3'] = True
except ImportError:  # Python 2
  from distutils.command.build_py import build_py

if 'use_2to3' in extra:
    try:
        os.mkdir('3bin')
    except OSError as err:
        if err.errno != 17:
            raise
    for script in scripts:
        shutil.copy(script, '3bin')
    scripts = glob.glob('3bin/*')
    run_2to3(scripts)

if sys.version_info <= (2, 5):
    error = "ERROR: boto requires Python Version 2.6 or above...exiting."
    print >> sys.stderr, error
    sys.exit(1)

def readme():
    with open("README.rst") as f:
        return f.read()

def version():
    with open("boto/version.txt") as f:
        return f.read().strip()

setup(name = "boto",
      version = version(),
      description = "Amazon Web Services Library",
      long_description = readme(),
      author = "Mitch Garnaat",
      author_email = "mitch@garnaat.com",
      url = "https://github.com/boto/boto/",
      scripts = scripts,
      packages = ["boto", "boto.sqs", "boto.s3", "boto.gs", "boto.file",
                  "boto.ec2", "boto.ec2.cloudwatch", "boto.ec2.autoscale",
                  "boto.ec2.elb", "boto.sdb", "boto.cacerts",
                  "boto.sdb.db", "boto.sdb.db.manager",
                  "boto.mturk", "boto.pyami",
                  "boto.pyami.installers", "boto.pyami.installers.ubuntu",
                  "boto.mashups", "boto.contrib", "boto.manage",
                  "boto.services", "boto.cloudfront",
                  "boto.roboto", "boto.rds", "boto.vpc", "boto.fps",
                  "boto.fps", "boto.emr", "boto.emr", "boto.sns",
                  "boto.ecs", "boto.iam", "boto.route53", "boto.ses",
                  "boto.cloudformation", "boto.sts", "boto.dynamodb",
                  "boto.swf", "boto.mws", "boto.cloudsearch", "boto.glacier",
                  "boto.beanstalk", "boto.datapipeline", "boto.elasticache",
                  "boto.elastictranscoder", "boto.opsworks", "boto.redshift",
                  "boto.dynamodb2", "boto.support"],
      package_data = {"boto.cacerts": ["cacerts.txt"], "boto": ["version.txt"]},
      license = "MIT",
      platforms = "Posix; MacOS X; Windows",
      classifiers = ["Development Status :: 5 - Production/Stable",
                     "Intended Audience :: Developers",
                     "License :: OSI Approved :: MIT License",
                     "Operating System :: OS Independent",
                     "Topic :: Internet",
                     "Programming Language :: Python :: 2",
                     "Programming Language :: Python :: 2.6",
                     "Programming Language :: Python :: 2.7",
                     "Programming Language :: Python :: 3",
                     "Programming Language :: Python :: 3.3"],
      cmdclass = {'build_py': build_py},
      **extra
      )
