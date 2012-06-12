import mock
import unittest

from boto.ec2.tag import Tag, TagSet
from boto.ec2.volume import Volume, AttachmentSet


class VolumeTests(unittest.TestCase):
    @mock.patch("boto.ec2.volume.TaggedEC2Object.startElement")
    def test_startElement_calls_TaggedEC2Object_startElement_with_correct_args(self, startElement):
        volume = Volume()
        volume.startElement('some name', 'some attrs', None)
        startElement.assert_called_with(volume, 'some name', 'some attrs', None)

    @mock.patch("boto.ec2.volume.TaggedEC2Object.startElement")
    def test_startElement_retval_not_None_returns_correct_thing(self, startElement):
        tag_set = mock.Mock(TagSet)
        startElement.return_value = tag_set
        volume = Volume()
        retval = volume.startElement(None, None, None)
        self.assertEquals(retval, tag_set)

    @mock.patch("boto.ec2.volume.TaggedEC2Object.startElement")
    @mock.patch("boto.resultset.ResultSet")
    def test_startElement_with_name_tagSet_calls_ResultSet(self, ResultSet, startElement):
        startElement.return_value = None
        result_set = mock.Mock(ResultSet([('item', Tag)]))
        volume = Volume()
        volume.tags = result_set
        retval = volume.startElement('tagSet', None, None)
        self.assertEquals(retval, volume.tags)

    @mock.patch("boto.ec2.volume.TaggedEC2Object.startElement")
    def test_startElement_with_name_attachmentSet_returns_AttachmentSet(self, startElement):
        startElement.return_value = None
        attach_data = mock.Mock(AttachmentSet)
        volume = Volume()
        volume.attach_data = attach_data
        retval = volume.startElement('attachmentSet', None, None)
        self.assertEquals(retval, volume.attach_data)

    @mock.patch("boto.ec2.volume.TaggedEC2Object.startElement")
    def test_startElement_else_returns_None(self, startElement):
        startElement.return_value = None
        volume = Volume()
        retval = volume.startElement('not tagSet or attachmentSet', None, None)
        self.assertEquals(retval, None)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(VolumeTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
