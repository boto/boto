# Copyright (c) 2015 Devicescape Software, Inc.
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

class LifecycleHookTypes(list):
    def __init__(self, connection=None, **kwargs):
        pass

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name == 'member':
            self.append(value)

class LifecycleHook(object):
    def __init__(self, connection=None, **kwargs):
        pass

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name == 'GlobalTimeout':
            self.global_timeout = int(value)
        elif name == 'NotificationMetadata':
            self.notification_metadata = value
        elif name == 'LifecycleTransition':
            self.lifecycle_transition = value
        elif name == 'AutoScalingGroupName':
            self.asg_name = value
        elif name == 'DefaultResult':
            self.default_result = value
        elif name == 'NotificationTargetARN':
            self.notification_target_arn = value
        elif name == 'LifecycleHookName':
            self.name = value
        elif name == 'RoleARN':
            self.role_arn = value
        elif name == 'HeartbeatTimeout':
            self.heartbeat_timeout = int(value)
        else:
            setattr(self, name, value)
