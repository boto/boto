from tests.unit import AWSMockServiceTestCase
from boto.mturk.connection import MTurkConnection


class TestGetFileUploadURL(AWSMockServiceTestCase):
    connection_class = MTurkConnection

    def test_get_file_upload_url(self):
        url = 'http://s3.amazonaws.com/myawsbucket/puppy.jpg'
        body = ('<GetFileUploadURLResult>'
                  '<Request>'
                    '<IsValid>True</IsValid>'
                  '</Request>'
                  '<FileUploadURL>{url}</FileUploadURL>'
                '</GetFileUploadURLResult>').format(url=url)
        self.set_http_response(200, body=body)

        assignment_id = 'xxx'
        question_identifier = 'yyy'
        params = {'AssignmentId': assignment_id,
                  'QuestionIdentifier': question_identifier,
                  'Operation': 'GetFileUploadURL'}
        ignore = ['SignatureVersion', 'Timestamp', 'Version', 'AWSAccessKeyId']

        resp = self.service_connection.get_file_upload_url(assignment_id,
                                                           question_identifier)
        self.assert_request_parameters(params, ignore_params_values=ignore)
        self.assertIsNot(resp, None)
        self.assertTrue(resp.status)
        self.assertEqual(len(resp), 1)
        self.assertEqual(resp[0].FileUploadURL, url)
