# Copyright (c) 2008 Chris Moyer http://coredumped.org/
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import base64
import urllib
import xml.sax
import uuid
import boto
import boto.utils
from boto import handler
from boto.connection import AWSQueryConnection
from boto.resultset import ResultSet
from boto.exception import FPSResponseError

class FPSConnection(AWSQueryConnection):

    APIVersion = '2007-01-08'
    SignatureVersion = '1'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None,
                 host='fps.sandbox.amazonaws.com', debug=0,
                 https_connection_factory=None, path="/"):
        AWSQueryConnection.__init__(self, aws_access_key_id, aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port,
                                    proxy_user, proxy_pass, host, debug,
                                    https_connection_factory, path)
    
    def install_payment_instruction(self, instruction, token_type="Unrestricted", transaction_id=None):
        """
        InstallPaymentInstruction
        instruction: The PaymentInstruction to send, for example: 
        
            MyRole=='Caller' orSay 'Roles do not match';
        
        token_type: Defaults to "Unrestricted"
        transaction_id: Defaults to a new ID
        """

        if(transaction_id == None):
            transaction_id = uuid.uuid4()
        params = {}
        params['PaymentInstruction'] = instruction
        params['TokenType'] = token_type
        params['CallerReference'] = transaction_id
        response = self.make_request("InstallPaymentInstruction", params)
        return response
    
    def install_caller_instruction(self, token_type="Unrestricted", transaction_id=None):
        """
        Set us up as a caller
        This will install a new caller_token into the FPS section.
        This should really only be called to regenerate the caller token.
        """
        response = self.install_payment_instruction("MyRole=='Caller';", token_type=token_type, transaction_id=transaction_id)
        body = response.read()
        if(response.status == 200):
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            caller_token = rs.TokenId
            try:
                boto.config.save_system_option("FPS", "caller_token", caller_token)
            except(IOError):
                boto.config.save_user_option("FPS", "caller_token", caller_token)
            return caller_token
        else:
            raise FPSResponseError(response.status, response.reason, body)

    def install_recipient_instruction(self, token_type="Unrestricted", transaction_id=None):
        """
        Set us up as a Recipient
        This will install a new caller_token into the FPS section.
        This should really only be called to regenerate the recipient token.
        """
        response = self.install_payment_instruction("MyRole=='Recipient';", token_type=token_type, transaction_id=transaction_id)
        body = response.read()
        if(response.status == 200):
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            recipient_token = rs.TokenId
            try:
                boto.config.save_system_option("FPS", "recipient_token", recipient_token)
            except(IOError):
                boto.config.save_user_option("FPS", "recipient_token", recipient_token)

            return recipient_token
        else:
            raise FPSResponseError(response.status, response.reason, body)

    def make_url(self, returnURL, paymentReason, pipelineName, **params):
        """
        Generate the URL with the signature required for a transaction
        """
        params['callerKey'] = str(self.aws_access_key_id)
        params['returnURL'] = str(returnURL)
        params['paymentReason'] = str(paymentReason)
        params['pipelineName'] = pipelineName

        if(not params.has_key('callerReference')):
            params['callerReference'] = str(uuid.uuid4())

        deco = [(key.lower(),i,key) for i,key in enumerate(params.keys())]
        deco.sort()
        keys = [key for _,_,key in deco]

        url = ''
        canonical = ''
        for k in keys:
            url += "&%s=%s" % (k, urllib.quote_plus(str(params[k])))
            canonical += "%s%s" % (k, str(params[k]))

        url = "/cobranded-ui/actions/start?%s" % ( url[1:])
        hmac = self.hmac.copy()
        hmac.update(canonical)
        signature = urllib.quote_plus(base64.encodestring(hmac.digest()).strip())
        
        return "https://authorize.payments-sandbox.amazon.com%s&awsSignature=%s" % (url, signature)

    def pay(self, transactionAmount, senderTokenId, chargeFeeTo="Recipient",
            callerReference=None, senderReference=None, recipientReference=None,
            senderDescription=None, recipientDescription=None, callerDescription=None,
            metadata=None, transactionDate=None, reserve=False):
        """
        Make a payment transaction. You must specify the amount.
        This can also perform a Reserve request if 'reserve' is set to True.
        """
        params = {}
        params['SenderTokenId'] = senderTokenId
        params['TransactionAmount.Amount'] = str(transactionAmount)
        params['TransactionAmount.CurrencyCode'] = "USD"
        params['ChargeFeeTo'] = chargeFeeTo
        
        params['RecipientTokenId'] = boto.config.get("FPS", "recipient_token")
        params['CallerTokenId'] = boto.config.get("FPS", "caller_token")
        if(transactionDate != None):
            params['TransactionDate'] = transactionDate
        if(senderReference != None):
            params['SenderReference'] = senderReference
        if(recipientReference != None):
            params['RecipientReference'] = recipientReference
        if(senderDescription != None):
            params['SenderDescription'] = senderDescription
        if(recipientDescription != None):
            params['RecipientDescription'] = recipientDescription
        if(callerDescription != None):
            params['CallerDescription'] = callerDescription
        if(metadata != None):
            params['MetaData'] = metadata
        if(callerReference == None):
            callerReference = uuid.uuid4()
        params['CallerReference'] = callerReference
        
        if reserve:
            response = self.make_request("Reserve", params)
        else:
            response = self.make_request("Pay", params)
        body = response.read()
        if(response.status == 200):
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise FPSResponseError(response.status, response.reason, body)
    
    def get_transaction_status(self, transactionId):
        """
        Returns the status of a given transaction.
        """
        params = {}
        params['TransactionId'] = transactionId
    
        response = self.make_request("GetTransactionStatus", params)
        body = response.read()
        if(response.status == 200):
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise FPSResponseError(response.status, response.reason, body)
    
    def cancel(self, transactionId, description=None):
        """
        Cancels a reserved or pending transaction.
        """
        params = {}
        params['transactionId'] = transactionId
        if(description != None):
            params['description'] = description
        
        response = self.make_request("Cancel", params)
        body = response.read()
        if(response.status == 200):
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise FPSResponseError(response.status, response.reason, body)
    
    def settle(self, reserveTransactionId, transactionAmount=None):
        """
        Charges for a reserved payment.
        """
        params = {}
        params['ReserveTransactionId'] = reserveTransactionId
        if(transactionAmount != None):
            params['TransactionAmount'] = transactionAmount
        
        response = self.make_request("Settle", params)
        body = response.read()
        if(response.status == 200):
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise FPSResponseError(response.status, response.reason, body)
    
    def refund(self, callerReference, transactionId, refundAmount=None, callerDescription=None):
        """
        Refund a transaction. This refunds the full amount by default unless 'refundAmount' is specified.
        """
        params = {}
        params['CallerReference'] = callerReference
        params['TransactionId'] = transactionId
        if(refundAmount != None):
            params['RefundAmount'] = refundAmount
        if(callerDescription != None):
            params['CallerDescription'] = callerDescription
        
        response = self.make_request("Refund", params)
        body = response.read()
        if(response.status == 200):
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise FPSResponseError(response.status, response.reason, body)
    
    def get_recipient_verification_status(self, recipientTokenId):
        """
        Test that the intended recipient has a verified Amazon Payments account.
        """
        params ={}
        params['RecipientTokenId'] = recipientTokenId
        
        response = self.make_request("GetRecipientVerificationStatus", params)
        body = response.read()
        if(response.status == 200):
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise FPSResponseError(response.status, response.reason, body)
    
    def get_token_by_caller_reference(self, callerReference):
        """
        Returns details about the token specified by 'callerReference'.
        """
        params ={}
        params['callerReference'] = callerReference
        
        response = self.make_request("GetTokenByCaller", params)
        body = response.read()
        if(response.status == 200):
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise FPSResponseError(response.status, response.reason, body)
    def get_token_by_caller_token(self, tokenId):
        """
        Returns details about the token specified by 'callerReference'.
        """
        params ={}
        params['TokenId'] = tokenId
        
        response = self.make_request("GetTokenByCaller", params)
        body = response.read()
        if(response.status == 200):
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise FPSResponseError(response.status, response.reason, body)
