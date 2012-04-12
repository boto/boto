class FPSResponse(object):
    def __init__(self, connection=None):
        self.connection = connection

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if not name == "ResponseMetadata":
            setattr(self, name, value)
