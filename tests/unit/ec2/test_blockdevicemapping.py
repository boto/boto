import mock
import unittest

from boto.ec2.blockdevicemapping import BlockDeviceType, BlockDeviceMapping

class BlockDeviceTypeTests(unittest.TestCase):
    def setUp(self):
        self.block_device_type = BlockDeviceType()

    def check_that_attribute_has_been_set(self, name, value, attribute):
        self.block_device_type.endElement(name, value, None)
        self.assertEqual(getattr(self.block_device_type, attribute), value)

    def test_endElement_sets_correct_attributes_with_values(self):
        for arguments in [("volumeId", 1, "volume_id"),
                          ("virtualName", "some name", "ephemeral_name"),
                          ("snapshotId", 1, "snapshot_id"),
                          ("volumeSize", 1, "size"),
                          ("status", "some status", "status"),
                          ("attachTime", 1, "attach_time"),
                          ("somethingRandom", "somethingRandom", "somethingRandom")]:
            self.check_that_attribute_has_been_set(arguments[0], arguments[1], arguments[2])

    def test_endElement_with_name_NoDevice_value_true(self):
        self.block_device_type.endElement("NoDevice", 'true', None)
        self.assertEqual(self.block_device_type.no_device, True)

    def test_endElement_with_name_NoDevice_value_other(self):
        self.block_device_type.endElement("NoDevice", 'something else', None)
        self.assertEqual(self.block_device_type.no_device, False)

    def test_endElement_with_name_deleteOnTermination_value_true(self):
        self.block_device_type.endElement("deleteOnTermination", "true", None)
        self.assertEqual(self.block_device_type.delete_on_termination, True)

    def test_endElement_with_name_deleteOnTermination_value_other(self):
        self.block_device_type.endElement("deleteOnTermination", 'something else', None)
        self.assertEqual(self.block_device_type.delete_on_termination, False)

class BlockDeviceMappingTests(unittest.TestCase):
    def setUp(self):
        self.block_device_mapping = BlockDeviceMapping()

    def block_device_type_eq(self, b1, b2):
        if isinstance(b1, BlockDeviceType) and isinstance(b2, BlockDeviceType):
            return all([b1.connection == b2.connection,
                        b1.ephemeral_name == b2.ephemeral_name,
                        b1.no_device == b2.no_device,
                        b1.volume_id == b2.volume_id,
                        b1.snapshot_id == b2.snapshot_id,
                        b1.status == b2.status,
                        b1.attach_time == b2.attach_time,
                        b1.delete_on_termination == b2.delete_on_termination,
                        b1.size == b2.size])

    def test_startElement_with_name_ebs_sets_and_returns_current_value(self):
        retval = self.block_device_mapping.startElement("ebs", None, None)
        assert self.block_device_type_eq(retval, BlockDeviceType(self.block_device_mapping))

    def test_startElement_with_name_virtualName_sets_and_returns_current_value(self):
        retval = self.block_device_mapping.startElement("virtualName", None, None)
        assert self.block_device_type_eq(retval, BlockDeviceType(self.block_device_mapping))

    def test_endElement_with_name_device_sets_current_name(self):
        self.block_device_mapping.endElement("device", "/dev/null", None)
        self.assertEqual(self.block_device_mapping.current_name, "/dev/null")

    def test_endElement_with_name_device_sets_current_name(self):
        self.block_device_mapping.endElement("deviceName", "some device name", None)
        self.assertEqual(self.block_device_mapping.current_name, "some device name")

    def test_endElement_with_name_item_sets_current_name_key_to_current_value(self):
        self.block_device_mapping.current_name = "some name"
        self.block_device_mapping.current_value = "some value"
        self.block_device_mapping.endElement("item", "some item", None)
        self.assertEqual(self.block_device_mapping["some name"], "some value")

if __name__ == "__main__":
    unittest.main()
