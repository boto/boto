zone53
======
[zone53](https://github.com/aglyzov/zone53) is a convenient Python API
to manage Amazon's DNS web service
[route53](http://aws.amazon.com/route53/).
Essentially, it is a thin layer on top of
[boto.route53](http://boto.readthedocs.org/en/latest/ref/route53.html)
providing Zone and Record classes.

How to install
--------------
~~~sh
# using pip (recommended)
pip install zone53
~~~
~~~sh
# or using pip from the git repo
pip install git+https://github.com/aglyzov/zone53.git
~~~
~~~sh
# or using setup.py (assuming you downloaded the sources)
python setup.py install
~~~

Authentication
--------------
zone53 uses [boto.route53](http://boto.readthedocs.org/en/latest/ref/route53.html)
to make all connections so all boto authentication rules apply here. Basically,
you either use a boto config file (~/.boto):
~~~ini
[Credentials]
aws_access_key_id     = <YOUR-AWS-ACCESS-KEY>
aws_secret_access_key = <YOUR-AWS-SECRET-KEY>
~~~
or set special environment variables:
~~~sh
# in a shell
export AWS_ACCESS_KEY_ID="<YOUR-AWS-ACCESS-KEY"
export AWS_SECRET_ACCESS_KEY="<YOUR-AWS-SECRET-KEY>"
~~~
~~~python
# or in a python source
from os import env
env['AWS_ACCESS_KEY_ID']     = '<YOUR-AWS-ACCESS-KEY>'
env['AWS_SECRET_ACCESS_KEY'] = '<YOUR-AWS-SECRET-KEY>'
~~~

Examples
--------
~~~python
from zone53 import Zone, Record

# creating new zone example.com.
zone = Zone.create('example.com')

# getting all available zones as a list
zones = Zone.get_all()

# getting an existing zone by name
zone = Zone.get('example.com')

# constructing a FQDN for a name
zone.fqdn('test') == 'test.example.com'
zone.fqdn('test.example.com') == 'test.example.com'
zone.fqdn('test.example.com', trailing_dot=True) == 'test.example.com.'

# fetching all records
records = zone.get_records()

# fetching CNAME records with ttl=300
cnames = zone.get_records( type='CNAME', ttl=300 )

# fetching A records for test.example.com. (using incomplete name)
empty = zone.get_records( type='A', name='test' )

# fetching nameservers
ns_records = zone.get_records( type='NS' )
nameservers = ns_records and ns_records[0].value or []

# adding a CNAME record with ttl=60
# (note, you can use incomplete names when passing zone as a kw-argument)
rec = Record( type='CNAME', name='www', value='', ttl=60, zone=zone )
status = rec.add()  # same as zone.add_record( rec )

# adding three A records
Record( name='node01.example.com', value='192.168.1.1' ).add( zone )
Record( name='node02.example.com', value='192.168.1.2' ).add( zone )
Record( name='node03.example.com', value='192.168.1.3' ).add( zone )

# adding a weighted CNAME record set (WRR)
r1 = Record( type='CNAME', name='node', value='node01', weight=2, id='node01', zone=zone )
r2 = Record( type='CNAME', name='node', value='node02', weight=2, id='node02', zone=zone )
r3 = Record( type='CNAME', name='node', value='node03', weight=2, id='node03', zone=zone )
zone.add_record( r1 )  # same as r1.add()
zone.add_record( r2 )  # same as r2.add()
zone.add_record( r3 )  # same as r3.add()

# updaing a record
r1.update( id='heavy-node', weight=5 )

# deleting a record
r2.delete()

# deleting a zone
for rec in zone.get_records( type='CNAME' ): rec.delete()
for rec in zone.get_records( type='A' ):     rec.delete()
zone.delete()
~~~
