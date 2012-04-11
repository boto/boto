
class RequestLog(object):

    def __init__(self, connection=None):
        self.connection = None
        self.name = None
        self.status = None

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'Id':
            self.id = value
        elif name == 'Status':
            self.status = value
        else:
            setattr(self, name, value)
