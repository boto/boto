import json
class UnexpectedHTTPResponseError(Exception):
    def __init__(self, expected_responses, response):
        self.status = response.status
        self.body = response.read()
        self.code = None
        try:
            body = json.loads(self.body)
            self.code = body["code"]
            msg = 'Expected %s, got (%d, code=%s, message=%s)' % (expected_responses,
                                                                  response.status,
                                                                  self.code,
                                                                  body["message"])
        except:
            msg = 'Expected %s, got (%d, %s)' % (expected_responses,
                                                 response.status,
                                                 self.body)
        super(UnexpectedHTTPResponseError, self).__init__(msg)
