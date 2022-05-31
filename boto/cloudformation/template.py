from boto.resultset import ResultSet
from boto.cloudformation.stack import Capability

class Template(object):
    def __init__(self, connection=None):
        self.connection = connection
        self.description = None
        self.template_parameters = None
        self.capabilities_reason = None
        self.capabilities = None

    def startElement(self, name, attrs, connection):
        if name == "Parameters":
            self.template_parameters = ResultSet([('member', TemplateParameter)])
            return self.template_parameters
        elif name == "Capabilities":
            self.capabilities = ResultSet([('member', Capability)])
            return self.capabilities
        else:
            return None

    def endElement(self, name, value, connection):
        if name == "Description":
            self.description = value
        elif name == "CapabilitiesReason":
            self.capabilities_reason = value
        else:
            setattr(self, name, value)

class TemplateParameter(object):
    def __init__(self, parent):
        self.parent = parent
        self.default_value = None
        self.description = None
        self.no_echo = None
        self.parameter_key = None

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == "DefaultValue":
            self.default_value = value
        elif name == "Description":
            self.description = value
        elif name == "NoEcho":
            self.no_echo = bool(value)
        elif name == "ParameterKey":
            self.parameter_key = value
        else:
            setattr(self, name, value)


class StackTemplate(object):
    template_version = '2010-09-09'
    
    def __init__(self, description, parameters=None, mappings=None, resources=None, outputs=None):
        self.description = description
        self.parameters = parameters
        self.mappings = mappings
        self.resources = resources
        self.outputs = outputs
    
    def to_object(self):
        obj = {}
        resources = {}
        attrs = {
            'parameters': 'Parameters',
            'mappings': 'Mappings',
            'resources': 'Resources',
            'outputs': 'Outputs'
        }
        
        for attr, name in attrs.iteritems():
            value = getattr(self, attr, None)
            if not value:
                continue
            # Build a dict containing the items for this attribute
            items = {}
            for k, v in value.iteritems():
                items[k] = v.to_object()
            obj[name] = items
        
        obj['AWSTemplateFormatVersion'] = self.template_version
        return obj

class StackParameter(object):
    TYPES = ['String', 'Number', 'CommaDelimitedList']

    def __init__(self, type, default=None):
        self.type = type

    def to_object(self):
        return {
            'Type': self.type
        }
