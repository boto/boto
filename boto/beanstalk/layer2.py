#
# wraps layer1 api methods in order to convert layer1 dict responses to response objects
#
import re
from boto.beanstalk.layer1 import Layer1
from boto.beanstalk.response import Wrapper
from boto.exception import BotoServerError
import boto.beanstalk.exception as exception


def beanstalk_wrapper(func, name):
    def _wrapped_low_level_api(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
        except BotoServerError, e:
            raise exception.simple(e)
        # turn 'this_is_a_function_name' into 'ThisIsAFunctionNameResponse'
        cls_name = ''.join([part.capitalize() for part in name.split('_')]) + 'Response'
        # get the class object from boto.beanstalk.response
        cls = getattr(Wrapper, cls_name)

        # return class instead
        return cls(response)
    return _wrapped_low_level_api


class Layer2(object):
    def __init__(self, *args, **kwargs):
        self.api = Layer1(*args, **kwargs)

    def __getattr__(self, name):
        try:
            return beanstalk_wrapper(getattr(self.api, name), name)
        except AttributeError, e:
            raise AttributeError("%s has no attribute %r" % (self, name))
