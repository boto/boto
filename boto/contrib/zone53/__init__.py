# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0 fdm=marker fmr=#{,#}

__version__    = '0.3.2'
__author__     = 'Alexander Glyzov'
__maintainer__ = 'Alexander Glyzov'
__email__      = 'bonoba@gmail.com'

__all__ = ['Zone', 'Record']

from socket    import gethostbyname
from functools import partial

from boto                import connect_route53
from boto.route53.record import ResourceRecordSets


def norm_weight( weight ):  #{
    if weight:
        try:    weight = max(int(weight), 0)
        except: weight = None
    return weight or None
#}

class Record(object):  #{

    def __init__(self, name, value, type='A', ttl=300, weight=None, id=None, zone=None, normalize=True):
        type = str(type).upper()

        if not normalize or type == 'PTR':
            norm_host = lambda h: h
        elif zone:
            assert isinstance(zone, Zone)
            norm_host = partial( zone.fqdn, trailing_dot=True )
        else:
            norm_host = lambda h: h if h.endswith('.') else h+'.'

        if not normalize:
            norm_value = lambda v: v
        elif type in ('A','AAAA'):
            norm_value = lambda v: v or gethostbyname( zone.name )
        else:
            norm_value = lambda v: (v or zone.name).rstrip('.')+'.'

        if not isinstance(value, (list, tuple, set, dict)):
            value = str(value).split(',')
        value = [h.strip() for h in value]

        self.type   = type
        self.name   = norm_host( name )
        self.value  = map(norm_value, value)
        self.ttl    = ttl
        self.weight = norm_weight( weight )
        self.id     = id
        self.zone   = zone

    @classmethod
    def from_boto_record(cls, boto_record, zone=None):
        return cls(
            boto_record.name,
            boto_record.resource_records,
            type      = boto_record.type,
            ttl       = boto_record.ttl,
            weight    = boto_record.weight,
            id        = boto_record.identifier,
            zone      = zone,
            normalize = False  # don't change original host names
        )

    def __repr__(self):
        return '<%s: %s, %s, %s, [%s]%s>' % (
            self.__class__.__name__,
            self.type,
            self.ttl,
            self.name,
            ', '.join( self.value ),
            ' (WRR id=%s, weight=%s)' % (self.id, self.weight) if self.weight or self.id else ''
        )

    def add(self, zone=None):
        """Add this record to a zone"""
        zone = zone or self.zone
        assert isinstance(zone, Zone)
        return zone.add_record( self )

    def update(self, **kw):
        zone = kw.pop('zone', None) or getattr(self, 'zone')
        assert isinstance(zone, Zone)
        return zone.update_record( self, **kw )

    def delete(self, zone=None):
        """Delete this record from a zone"""
        zone = zone or self.zone
        assert isinstance(zone, Zone)
        return zone.delete_record( self )
#}
class Zone(object):  #{
    def __init__(self, zone_dict, conn=None):
        self.conn = conn or connect_route53()
        self.id   = zone_dict.pop('Id','').replace('/hostedzone/','')

        for key, value in zone_dict.items():
            setattr(self, key.lower(), value)

        if not self.name.endswith('.'):
            self.name += '.'  # make sure the name is fully qualified

    @classmethod
    def create(cls, name, conn=None):
        """ Create new hosted zone."""
        conn = conn or connect_route53()
        name = name if name.endswith('.') else name+'.'
        zone = conn.create_hosted_zone(name)
        zone = zone['CreateHostedZoneResponse']['HostedZone']
        return cls(zone, conn=conn)

    @classmethod
    def get(cls, name):
        """ Retrieve a hosted zone defined by name."""
        name = name if name.endswith('.') else name+'.'
        matched = [z for z in cls.get_all() if z.name == name]
        return matched and matched[0] or None

    @classmethod
    def get_all(cls, conn=None):
        """ Retrieve a list of all hosted zones."""
        conn  = conn or connect_route53()
        zones = conn.get_all_hosted_zones()
        zones = zones['ListHostedZonesResponse']['HostedZones']
        return [cls(z, conn=conn) for z in zones]

    def __repr__(self):
        return '<Zone: %s, %s>' % (self.name, self.id)

    def fqdn(self, host='', trailing_dot=False):
        """ Returns a fully qualified domain name for the argument

            dot=<bool> - append or remove trailing dot
        """
        if not host.endswith('.'):
            if host.endswith( self.name[:-1] ):
                host += '.'
            elif host:
                host += '.%s' % self.name
            else:
                host = self.name

        host = host.rstrip('.')
        if trailing_dot:
            host += '.'

        return host

    def add_record(self, record, comment=''):
        """Add a new record to this zone"""
        assert isinstance(record, Record)

        changes = ResourceRecordSets( self.conn, self.id, comment )
        change  = changes.add_change(
            "CREATE",
            record.name,
            record.type,
            ttl        = record.ttl,
            weight     = record.weight,
            identifier = record.id
        )
        for value in record.value:
            change.add_value(value)

        record.zone = self
        return Status( changes.commit(), conn=self.conn )

    def update_record(
        self,
        record,
        type    = None,
        name    = None,
        value   = None,
        ttl     = None,
        weight  = None,  # for weighed or latency-based resource sets
        id      = None,  # for weighed or latency-based resource sets
        comment = ""
    ):
        assert isinstance(record, Record)

        changes = ResourceRecordSets( self.conn, self.id, comment )

        change = changes.add_change(
            "DELETE",
            record.name,
            record.type,
            ttl        = record.ttl,
            weight     = record.weight,
            identifier = record.id
        )
        for val in record.value:
            change.add_value( val )

        record.name   = self.fqdn( name or record.name )
        record.type   = type   or record.type
        record.ttl    = ttl    or record.ttl
        record.weight = weight or record.weight
        record.id     = id     or record.id

        change = changes.add_change(
            'CREATE',
            record.name,
            record.type,
            ttl        = record.ttl,
            weight     = record.weight,
            identifier = record.id
        )
        new = Record( record.name, value or record.value, type=record.type, zone=self )
        for val in new.value:
            change.add_value( val )

        record.value = new.value
        record.zone  = self

        return Status( changes.commit(), conn=self.conn )

    def delete_record(self, record):
        """Delete a record from this zone"""
        assert isinstance(record, Record)

        changes = ResourceRecordSets(self.conn, self.id)
        change  = changes.add_change(
            "DELETE",
            record.name,
            record.type,
            ttl        = record.ttl,
            weight     = record.weight,
            identifier = record.id
        )
        for value in record.value:
            change.add_value(value)

        record.zone = None

        return Status( changes.commit(), conn=self.conn )

    def get_records(self, name=None, type=None, ttl=None, weight=None, id=None):
        """Get a list of this zone records (optionally filtered)"""
        records = []
        if name and type != 'PTR':
            name = self.fqdn( name )
        weight = norm_weight( weight )

        for boto_record in self.conn.get_all_rrsets(self.id):
            record = Record.from_boto_record( boto_record, zone=self )
            record_name   = self.fqdn( record.name )
            record_weight = norm_weight( record.weight )
            if  (record_name   == name   if name   else True)\
            and (record.type   == type   if type   else True)\
            and (record.ttl    == ttl    if ttl    else True)\
            and (record_weight == weight if weight else True)\
            and (record.id     == id     if id     else True):
                records.append( record )

        return records

    def delete(self):
        """ Delete this zone."""
        return Status( self.conn.delete_hosted_zone(self.id), key='DeleteHostedZoneResponse' )
#}
class Status(object):  #{
    def __init__(self, change_resp, conn=None, key='ChangeResourceRecordSetsResponse'):
        self.conn = conn or connect_route53()
        _dict = change_resp[key]['ChangeInfo']

        for key, value in _dict.items():
            setattr(self, key.lower(), value)

        self.id     = (self.id     or '').replace('/change/','')
        self.status = (self.status or '').lower()

    def update(self):
        """ Update the status of this request."""
        change_resp = self.conn.get_change(self.id)
        self.status = change_resp['GetChangeResponse']['ChangeInfo']['Status'].lower()
        return self.status

    def __repr__(self):
        return '<Status: %s>' % self.status

    def __str__(self):
        return self.status

    def __eq__(self, other):
        return str(self) == str(other)
#}
