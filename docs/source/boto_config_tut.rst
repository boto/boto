.. _ref-boto_config:

===========
Boto Config
===========

Introduction
------------

There is a growing list of configuration options for the boto library. Many of
these options can be passed into the constructors for top-level objects such as
connections. Some options, such as credentials, can also be read from
environment variables (e.g. ``AWS_ACCESS_KEY_ID`` and ``AWS_SECRET_ACCESS_KEY``).
But there is no central place to manage these options. So, the development
version of boto has now introduced the notion of boto config files.

Details
-------

A boto config file is simply a .ini format configuration file that specifies
values for options that control the behavior of the boto library. Upon startup,
the boto library looks for configuration files in the following locations
and in the following order:

* /etc/boto.cfg - for site-wide settings that all users on this machine will use
* ~/.boto - for user-specific settings

The options are merged into a single, in-memory configuration that is
available as :py:mod:`boto.config`. The :py:class:`boto.pyami.config.Config`
class is a subclass of the standard Python
:py:class:`ConfigParser.SafeConfigParser` object and inherits all of the
methods of that object. In addition, the boto
:py:class:`Config <boto.pyami.config.Config>` class defines additional
methods that are described on the PyamiConfigMethods page.

Sections
--------

The following sections and options are currently recognized within the
boto config file.

Credentials
^^^^^^^^^^^

The Credentials section is used to specify the AWS credentials used for all
boto requests. The order of precedence for authentication credentials is:

* Credentials passed into Connection class constructor.
* Credentials specified by environment variables
* Credentials specified as options in the config file.

This section defines the following options: ``aws_access_key_id`` and
``aws_secret_access_key``. The former being your aws key id and the latter
being the secret key.

For example::

    [Credentials]
    aws_access_key_id = <your access key>
    aws_secret_access_key = <your secret key>

Please notice that quote characters are not used to either side of the '='
operator even when both your aws access key id and secret key are strings.

For greater security, the secret key can be stored in a keyring and
retrieved via the keyring package.  To use a keyring, use ``keyring``,
rather than ``aws_secret_access_key``::

    [Credentials]
    aws_access_key_id = <your access key>
    keyring = <keyring name>

To use a keyring, you must have the Python `keyring
<http://pypi.python.org/pypi/keyring>`_ package installed and in the
Python path. To learn about setting up keyrings, see the `keyring
documentation
<http://pypi.python.org/pypi/keyring#installing-and-using-python-keyring-lib>`_


Boto
^^^^

The Boto section is used to specify options that control the operaton of
boto itself. This section defines the following options:

:debug: Controls the level of debug messages that will be printed by the boto library.
    The following values are defined::

        0 - no debug messages are printed
        1 - basic debug messages from boto are printed
        2 - all boto debugging messages plus request/response messages from httplib

:proxy: The name of the proxy host to use for connecting to AWS.
:proxy_port: The port number to use to connect to the proxy host.
:proxy_user: The user name to use when authenticating with proxy host.
:proxy_pass: The password to use when authenticating with proxy host.
:num_retries: The number of times to retry failed requests to an AWS server.
  If boto receives an error from AWS, it will attempt to recover and retry the
  request. The default number of retries is 5 but you can change the default
  with this option.

As an example::

    [Boto]
    debug = 0
    num_retries = 10

    proxy = myproxy.com
    proxy_port = 8080
    proxy_user = foo
    proxy_pass = bar

Precedence
----------

Even if you have your boto config setup, you can also have credentials and
options stored in environmental variables or you can explicitly pass them to
method calls i.e.::

	>>> boto.connect_ec2('<KEY_ID>','<SECRET_KEY>')

In these cases where these options can be found in more than one place boto
will first use the explicitly supplied arguments, if none found it will then
look for them amidst environment variables and if that fails it will use the
ones in boto config.
