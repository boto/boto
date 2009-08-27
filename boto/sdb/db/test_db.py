from boto.sdb.db.model import Model
from boto.sdb.db.property import *
from boto.sdb.db.manager import get_manager
from datetime import datetime
import time
from boto.exception import SDBPersistenceError

_objects = {}

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

class TestList(Model):

    name = StringProperty()
    nums = ListProperty(IntegerProperty)

class TestMap(Model):

    name = StringProperty()
    map = MapProperty()

class TestListReference(Model):

    name = StringProperty()
    basics = ListProperty(ReferenceProperty)

class TestAutoNow(Model):

    create_date = DateTimeProperty(auto_now_add=True)
    modified_date = DateTimeProperty(auto_now=True)

class TestUnique(Model):
    name = StringProperty(unique=True)

def test_basic(mgr):
    global _objects
    t = TestBasic(manager=mgr)
    t.name = 'simple'
    t.size = -42
    t.foo = True
    t.date = datetime.now()
    print 'saving object'
    t.put()
    _objects['test_basic_t'] = t
    time.sleep(10)
    print 'now try retrieving it'
    tt = TestBasic.get_by_id(mgr, t.id)
    _objects['test_basic_tt'] = tt
    assert tt.id == t.id
    return t
    
def test_required(mgr):
    global _objects
    t = TestRequired(manager=mgr)
    _objects['test_required_t'] = t
    t.put()
    return t

def test_reference(mgr, t=None):
    global _objects
    if not t:
        t = test_basic(mgr)
    tt = TestReference(manager=mgr)
    tt.ref = t
    tt.put()
    time.sleep(10)
    tt = TestReference.get_by_id(mgr, tt.id)
    _objects['test_reference_tt'] = tt
    assert tt.ref.id == t.id
    for o in t.refs:
        print o

def test_subclass(mgr):
    global _objects
    t = TestSubClass(manager=mgr)
    _objects['test_subclass_t'] = t
    t.name = 'a subclass'
    t.size = -489
    t.save()

def test_password(mgr):
    global _objects
    t = TestPassword(manager=mgr)
    _objects['test_password_t'] = t
    t.password = "foo"
    t.save()
    time.sleep(10)
    # Make sure it stored ok
    tt = TestPassword.get_by_id(mgr, t.id)
    _objects['test_password_tt'] = tt
    #Testing password equality
    assert tt.password == "foo"
    #Testing password not stored as string
    assert str(tt.password) != "foo"

def test_list(mgr):
    global _objects
    t = TestList(manager=mgr)
    _objects['test_list_t'] = t
    t.name = 'a list of ints'
    t.nums = [1,2,3,4,5]
    t.put()
    tt = TestList.get_by_id(mgr, t.id)
    _objects['test_list_tt'] = tt
    assert tt.name == t.name
    for n in tt.nums:
        assert isinstance(n, int)

def test_list_reference(mgr):
    global _objects
    t = TestBasic(manager=mgr)
    t.put()
    _objects['test_list_ref_t'] = t
    tt = TestListReference(manager=mgr)
    tt.name = "foo"
    tt.basics = [t]
    tt.put()
    time.sleep(10)
    _objects['test_list_ref_tt'] = tt
    ttt = TestListReference.get_by_id(mgr, tt.id)
    assert ttt.basics[0].id == t.id

def test_unique(mgr):
    global _objects
    t = TestUnique(manager=mgr)
    name = 'foo' + str(int(time.time()))
    t.name = name
    t.put()
    _objects['test_unique_t'] = t
    time.sleep(10)
    tt = TestUnique(manager=mgr)
    _objects['test_unique_tt'] = tt
    tt.name = name
    try:
        tt.put()
        assert False
    except(SDBPersistenceError):
        pass

def test_datetime(mgr):
    global _objects
    t = TestAutoNow(manager=mgr)
    t.put()
    _objects['test_datetime_t'] = t
    time.sleep(10)
    tt = TestAutoNow.get_by_id(mgr, t.id)
    assert tt.create_date.timetuple() == t.create_date.timetuple()

def test(domain_name):
    mgr = get_manager(domain_name)
    print 'test_basic'
    t1 = test_basic(mgr)
    print 'test_required'
    test_required(mgr)
    print 'test_reference'
    test_reference(mgr, t1)
    print 'test_subclass'
    test_subclass(mgr)
    print 'test_password'
    test_password(mgr)
    print 'test_list'
    test_list(mgr)
    print 'test_list_reference'
    test_list_reference(mgr)
    print "test_datetime"
    test_datetime(mgr)
    print 'test_unique'
    test_unique(mgr)

if __name__ == "__main__":
    test()
