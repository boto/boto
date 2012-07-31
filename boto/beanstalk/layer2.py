#
# wraps layer1 api methods in order to convert layer1 dict responses to response objects
#
import re
from boto.beanstalk.layer1 import Layer1
from boto.beanstalk.response import Wrapper
from boto.exception import BotoServerError
import boto.beanstalk.exception as exception


class Layer2(Layer1):

    PRIVATE_METHODS = re.compile('^_')

    def __init__(self, *args, **kargs):
        super(Layer2, self).__init__(*args, **kargs)

        # used to store real method called so we can wrap around it
        self._method_called = None

    def __getattribute__(self, name):
        # if it's a function defined in Layer1
        if name in Layer1.__dict__ and hasattr(Layer1.__dict__[name], '__call__'):
        # and not private
            if not Layer2.PRIVATE_METHODS.match(name):
        # then wrap the call
                self._method_called = name
                return self._wrapper
        # otherwise do normal thing
        return super(Layer2, self).__getattribute__(name)

    # wrapper for layer1 api calls
    def _wrapper(self, *args, **kargs):
        # layer1 api call
        name = self._method_called

        try:
            # get super's response
            response = getattr(super(Layer2, self), name)(*args, **kargs)

        except BotoServerError as e:
            # throw a more descriptive error
            raise exception.simple(e)

        # turn 'this_is_a_function_name' into 'ThisIsAFunctionNameResponse'
        cls_name = ''.join( [ part.capitalize() for part in name.split('_') ] ) + 'Response'
        # get the class object from boto.beanstalk.response
        Class = getattr(Wrapper, cls_name)

        # return class instead
        return Class(response)
