class InstanceGroup(object):
	def __init__(self, num_instances, role, type, market, name):
		self.num_instances = num_instances
		self.role = role
		self.type = type
		self.market = market
		self.name = name
	
	def __repr__(self):
		return '%s.%s(name=%r, num_instances=%r, role=%r, type=%r, market = %r)' % (
            self.__class__.__module__, self.__class__.__name__,
            self.name, self.num_instances, self.role, self.type, self.market)
