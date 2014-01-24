"""
From http://docs.aws.amazon.com/Route53/latest/APIReference/API_CreateHealthCheck.html

<CreateHealthCheckRequest xmlns="https://route53.amazonaws.com/doc/2012-12-12/">
<CallerReference>unique description</CallerReference>
    <HealthCheckConfig>
        <IPAddress>IP address of the endpoint to check</IPAddress>
        <Port>port on the endpoint to check</Port>
        <Type>HTTP | TCP</Type>
        <ResourcePath>path of the file that you want Route 53 to request</ResourcePath>
        <FullyQualifiedDomainName>domain name of the endpoint to check</FullyQualifiedDomainName>
    </HealthCheckConfig>
</CreateHealthCheckRequest>
"""


class HealthCheck(object):

    """An individual health check"""

    POSTXMLBody = """
        <HealthCheckConfig>
            <IPAddress>%(ip_addr)s</IPAddress>
            <Port>%(port)s</Port>
            <Type>%(type)s</Type>
            <ResourcePath>%(resource_path)s</ResourcePath>
            %(fqdn_part)s
        </HealthCheckConfig>
    """

    XMLFQDNPart = """<FullyQualifiedDomainName>%(fqdn)s</FullyQualifiedDomainName>"""

    def __init__(self, ip_addr, port, hc_type, resource_path, fqdn=None):
        self.ip_addr = ip_addr
        self.port = port
        self.hc_type = hc_type
        self.resource_path = resource_path
        self.fqdn = fqdn

    def to_xml(self):
        params = {
            'ip_addr': self.ip_addr,
            'port': self.port,
            'type': self.hc_type,
            'resource_path': self.resource_path,
            'fqdn_part': ""
        }
        if self.fqdn is not None:
            fqdn_part = XMLFQDNPart % {'fqdn': self.fqdn}
            params['fqdn_part'] = fqdn_part

        return self.POSTXMLBody % params
