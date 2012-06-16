import mock
import unittest

from boto.ec2.blockdevicemapping import BlockDeviceType

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


if __name__ == "__main__":
    unittest.main()
