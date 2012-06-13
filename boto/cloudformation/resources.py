class StackResource(object):
    def to_object(self):
        clean_properties = {}
        for k, v in self.get_properties().iteritems():
            if v is not None:
                clean_properties[k] = v
        obj = {
            'Type': self.type,
            'Properties': clean_properties
        }
        if self.deletion_policy:
            obj['DeletionPolicy'] = self.deletion_policy
        return obj

class IAMGroup(StackResource):
    type = 'AWS::IAM::Group'

    def __init__(self, path=None, policies=None):
        self.path = path
        self.policies = policies

    def get_properties(self):
        return {
            'Path': self.path,
            'Policies': self.policies
        }

class IAMUser(StackResource):
    type = 'AWS::IAM::User'

    def __init__(self, path=None, groups=None, login_profile=None, policies=None):
        self.path = path
        self.groups = groups
        self.login_profile = login_profile
        self.policies = policies

    def get_properties(self):
        return {
            'Path': self.path,
            'Groups': self.groups,
            'LoginProfile': self.login_profile,
            'Policies': self.policies,
        }


class RecordSet(StackResource):
    type = "AWS::Route53::RecordSet"
    
    def __init__(self, name, zone_name, resource_records, record_type="A", comment=None, ttl="500", deletion_policy=None):
        self.zone_name = zone_name
        self.name = name
        self.resource_records = resource_records
        self.record_type = record_type
        self.comment = comment
        self.ttl = ttl
        self.deletion_policy = deletion_policy
    
    def get_properties(self):
        return {
            "HostedZoneName": self.zone_name,
            'Name': self.name,
            'Type': self.record_type,
            'TTL': self.ttl,
            'Comment': self.comment,
            'ResourceRecords': self.resource_records,
        }
