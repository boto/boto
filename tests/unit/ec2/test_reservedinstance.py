from tests.unit import AWSMockServiceTestCase
from boto.ec2.connection import EC2Connection
from boto.ec2.reservedinstance import ReservedInstance


class TestReservedInstancesSet(AWSMockServiceTestCase):
    connection_class = EC2Connection

    def default_body(self):
        return b"""
<reservedInstancesSet>
    <item>
        <reservedInstancesId>ididididid</reservedInstancesId>
        <instanceType>t1.micro</instanceType>
        <start>2014-05-03T14:10:10.944Z</start>
        <end>2014-05-03T14:10:11.000Z</end>
        <duration>64800000</duration>
        <fixedPrice>62.5</fixedPrice>
        <usagePrice>0.0</usagePrice>
        <instanceCount>5</instanceCount>
        <productDescription>Linux/UNIX</productDescription>
        <state>retired</state>
        <tagSet>
            <item>
                <key>already_present_key</key>
                <value>already_present_value</value>
            </item>
            <item>
                <key>Name</key>
                <value/>
            </item>
        </tagSet>
        <instanceTenancy>default</instanceTenancy>
        <currencyCode>USD</currencyCode>
        <offeringType>Heavy Utilization</offeringType>
        <recurringCharges>
            <item>
                <frequency>Hourly</frequency>
                <amount>0.005</amount>
            </item>
        </recurringCharges>
    </item>
</reservedInstancesSet>"""

    def test_get_all_reserved_instaces(self):
        self.set_http_response(status_code=200)
        response = self.service_connection.get_all_reserved_instances()
        self.assertEqual(len(response), 1)
        self.assertTrue(isinstance(response[0], ReservedInstance))

        self.assertEquals(response[0].id, 'ididididid')
        self.assertEquals(response[0].instance_count, 5)
        self.assertEquals(response[0].start, '2014-05-03T14:10:10.944Z')
        self.assertEquals(response[0].end, '2014-05-03T14:10:11.000Z')
        self.assertEquals(response[0].offering_type, 'Heavy Utilization')
        self.assertEquals(response[0].recurring_charges[0].frequency, 'Hourly')
        self.assertEquals(response[0].recurring_charges[0].amount, '0.005')

        response[0].add_tags({"key1": "value1", "key2": "value2"})

        self.assertEqual(response[0].tags, {
            "already_present_key": "already_present_value",
            "Name": "",
            "key1": "value1",
            "key2": "value2"})