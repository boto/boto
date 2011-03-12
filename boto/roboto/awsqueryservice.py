import boto
import boto.connection
import boto.jsonresponse
import awsqueryrequest

class AWSQueryService(boto.connection.AWSQueryConnection):

    name = ''
    description = ''
    APIVersion = ''
    authentication = 'sign-v2'
    path = '/'
    port = 443
    provider = 'aws'

    regions = []

    def __init__(self, **args):
        region_name = args.get('region_name', self.regions[0]['name'])
        for region in self.regions:
            if region['name'] == region_name:
                args['host'] = region['endpoint']
        args['path'] = self.path
        args['port'] = self.port
        boto.connection.AWSQueryConnection.__init__(self, **args)
        self.aws_response = None

    def __iter__(self):
        l = []
        for key in self.__class__.__dict__:
            val = self.__class__.__dict__[key]
            try:
                if issubclass(val, awsqueryrequest.AWSQueryRequest):
                    l.append(val)
            except TypeError:
                pass
        return iter(l)
    
    def _required_auth_capability(self):
        return [self.authentication]
        
