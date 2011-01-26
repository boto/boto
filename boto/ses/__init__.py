import urllib, base64
import boto, boto.jsonresponse
from boto.connection import AWSAuthConnection

class SESConnection(AWSAuthConnection):
    DefaultHost = 'email.us-east-1.amazonaws.com'
    
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
            port=None, proxy=None, proxy_port=None,
            host=DefaultHost, debug=0):
        AWSAuthConnection.__init__(self, host,
            aws_access_key_id, aws_secret_access_key,
            True, port, proxy, proxy_port, debug=debug)

    def _required_auth_capability(self):
        return ['hmac-v3']
    
    def make_request(self, params):
        data = '&'.join(k + '=' + urllib.quote(v) for k, v in params.iteritems())
        return AWSAuthConnection.make_request(self, 'GET', '/?' + data)
    
    def _process_request(self, **args):
        response = self.make_request(args)
        body = response.read()
        boto.log.debug(body)
        e = boto.jsonresponse.Element(list_marker=('VerifiedEmailAddresses', 'SendDataPoints'))
        h = boto.jsonresponse.XmlHandler(e, None)
        h.parse(body)
        return e
    
    def _plist(self, params, items, label):
        if not items: return
        if isinstance(items, str): items = [items]
        for n, k in enumerate(items):
            params[label + '.member.%d' % (n+1)] = k
    
    def _pcontent(self, params, item, label):
        if not item: return
        if isinstance(item, str): item = unicode(item)
        params[label + '.Charset'] = 'UTF-8'
        params[label + '.Data'] = item.encode('utf8')

    def verify_email(self, email):
        return self._process_request(Action='VerifyEmailAddress', EmailAddress=email)
    
    def delete_verified_email(self, email):
        return self._process_request(Action='DeleteVerifiedEmailAddress', EmailAddress=email)

    def get_verified_list(self):
        return self._process_request(Action='ListVerifiedEmailAddresses')
    
    def get_send_quota(self):
        return self._process_request(Action='GetSendQuota')
    
    def get_send_statistics(self):
        return self._process_request(Action='GetSendStatistics')
    
    def send_raw_email(self, destinations, raw_message, source):
        d = dict(Action='SendRawEmail', Source=source)
        d['RawMessage.Data'] = base64.encodestring(raw_message)
        self._plist(d, destinations, 'Destinations')
        return self._process_request(**d)
    
    def send_email(self, to_addresses=None, bcc_addresses=None, cc_addresses=None,
      body_html=None, body_text=None, subject=None, reply_to_addresses=None, 
      return_path=None, source=None):
        d = dict(Action='SendEmail', Source=source)
        self._plist(d, cc_addresses, 'Destination.CcAddresses')
        self._plist(d, bcc_addresses, 'Destination.BccAddresses')
        self._plist(d, to_addresses, 'Destination.ToAddresses')
        self._pcontent(d, body_html, 'Message.Body.Html')
        self._pcontent(d, body_text, 'Message.Body.Text')
        self._pcontent(d, subject, 'Message.Subject')
        self._plist(d, reply_to_addresses, 'ReplyToAddresses')
        if return_path: d['ReturnPath'] = return_path
        return self._process_request(**d)
