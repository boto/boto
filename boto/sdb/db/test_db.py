from boto.sdb.db.model import Model
from boto.sdb.db.property import *
from boto.sdb.db.manager import get_manager
from datetime import datetime
import time

#
# This will eventually be moved to the boto.tests module and become a real unit test
# but for now it will live here.  It shows examples of each of the Property types in
# use and tests the basic operations.
#
class TestBasic(Model):

	name = StringProperty()
	size = IntegerProperty()
	foo = BooleanProperty()
	date = DateTimeProperty()

class TestRequired(Model):

	req = StringProperty(required=True, default='foo')

class TestReference(Model):

	ref = ReferenceProperty(reference_class=TestBasic, collection_name='refs')

class TestSubClass(TestBasic):

	answer = IntegerProperty()

class TestPassword(Model):
	password = PasswordProperty()

def test_basic():
	t = TestBasic()
	t.name = 'simple'
	t.size = -42
	t.foo = True
	t.date = datetime.now()
	t.put()
	print 'saving object'
	time.sleep(5)
	print 'now try retrieving it'
	tt = TestBasic.get_by_ids(t.id)
	assert tt.id == t.id
	l = TestBasic.get_by_ids([t.id])
	assert len(l) == 1
	assert l[0].id == t.id
	return t
	
def test_required():
	t = TestRequired()
	t.put()
	return t

def test_reference(t=None):
	if not t:
		t = test_basic()
	tt = TestReference()
	tt.ref = t
	tt.put()
	time.sleep(5)
	for o in t.refs:
		print o
	return tt

def test_subclass():
	t = TestSubClass()
	t.name = 'a subclass'
	t.size = -489
	t.save()
	return t

def test_password():
	t = TestPassword()
	t.password = "foo"
	t.save()
	time.sleep(5)
	# Make sure it stored ok
	tt = TestPassword.get_by_ids(t.id)
	#Testing password equality
	assert tt.password == "foo"
	#Testing password not stored as string
	assert str(tt.password) != "foo"
	return t

def test():
	print 'test_basic'
	t1 = test_basic()
	print 'test_required'
	t2 = test_required()
	print 'test_reference'
	t3 = test_reference(t1)
	print 'test_subclass'
	t4 = test_subclass()
	domain = t4._manager.domain
	item1 = domain.get_item(t1.id)
	item2 = domain.get_item(t2.id)
	item3 = domain.get_item(t3.id)
	item4 = domain.get_item(t4.id)
	return [(t1, item1), (t2, item2), (t3, item3), (t4, item4)]
