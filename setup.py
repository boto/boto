#!/usr/bin/python

# Copyright (c) 2006-2009 Mitch Garnaat http://garnaat.org/
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
except ImportError:
    from distutils.core import setup

from boto import Version

setup(name = "boto",
      version = Version,
      description = "Amazon Web Services Library",
      long_description="Python interface to Amazon's Web Services.",
      author = "Mitch Garnaat",
      author_email = "mitch@garnaat.com",
      scripts = ["bin/sdbadmin", "bin/elbadmin", "bin/cfadmin", 
                 "bin/s3put", "bin/fetch_file", "bin/launch_instance", 
                 "bin/list_instances", "bin/taskadmin", "bin/kill_instance", 
                 "bin/bundle_image"],
      url = "http://code.google.com/p/boto/",
      packages = [ 'boto', 'boto.sqs', 'boto.s3',
                   'boto.ec2', 'boto.ec2.cloudwatch', 'boto.ec2.autoscale', 'boto.ec2.elb',
                   'boto.sdb', 'boto.sdb.persist', 'boto.sdb.db', 'boto.sdb.db.manager',
                   'boto.mturk', 'boto.pyami', 'boto.mashups', 'boto.contrib', 'boto.manage',
                   'boto.services', 'boto.tests', 'boto.cloudfront', 'boto.rds', 'boto.vpc',
                   'boto.fps'],
      license = 'MIT',
      platforms = 'Posix; MacOS X; Windows',
      classifiers = [ 'Development Status :: 3 - Alpha',
                      'Intended Audience :: Developers',
                      'License :: OSI Approved :: MIT License',
                      'Operating System :: OS Independent',
                      'Topic :: Internet',
                      ],
      )
