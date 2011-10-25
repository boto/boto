# Copyright (c) 2008 Chris Moyer http://coredumped.org/
# Copyringt (c) 2010 Jason R. Coombs http://www.jaraco.com/
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
import hmac
import hashlib
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

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None,
                 host='fps.sandbox.amazonaws.com', debug=0,
                 https_connection_factory=None, path="/"):
        AWSQueryConnection.__init__(self, aws_access_key_id,
                                    aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port,
                                    proxy_user, proxy_pass, host, debug,
                                    https_connection_factory, path)
    
    def _required_auth_capability(self):
        return ['fps']

    def install_payment_instruction(self, instruction,
                                    token_type="Unrestricted",
                                    transaction_id=None):
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
    
    def install_caller_instruction(self, token_type="Unrestricted",
                                   transaction_id=None):
        """
        Set us up as a caller
        This will install a new caller_token into the FPS section.
        This should really only be called to regenerate the caller token.
        """
        response = self.install_payment_instruction("MyRole=='Caller';",
                                                    token_type=token_type,
                                                    transaction_id=transaction_id)
        body = response.read()
        if(response.status == 200):
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            caller_token = rs.TokenId
            try:
                boto.config.save_system_option("FPS", "caller_token",
                                               caller_token)
            except(IOError):
                boto.config.save_user_option("FPS", "caller_token",
                                             caller_token)
            return caller_token
        else:
            raise FPSResponseError(response.status, response.reason, body)

    def install_recipient_instruction(self, token_type="Unrestricted",
                                      transaction_id=None):
        """
        Set us up as a Recipient
        This will install a new caller_token into the FPS section.
        This should really only be called to regenerate the recipient token.
        """
        response = self.install_payment_instruction("MyRole=='Recipient';",
                                                    token_type=token_type,
                                                    transaction_id=transaction_id)
        body = response.read()
        if(response.status == 200):
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            recipient_token = rs.TokenId
            try:
                boto.config.save_system_option("FPS", "recipient_token",
                                               recipient_token)
            except(IOError):
                boto.config.save_user_option("FPS", "recipient_token",
                                             recipient_token)

            return recipient_token
        else:
            raise FPSResponseError(response.status, response.reason, body)

    def make_marketplace_registration_url(self, returnURL, pipelineName,
                                          maxFixedFee=0.0, maxVariableFee=0.0,
                                          recipientPaysFee=True, **params):  
        """
        Generate the URL with the signature required for signing up a recipient
        """
        # use the sandbox authorization endpoint if we're using the
        #  sandbox for API calls.
        endpoint_host = 'authorize.payments.amazon.com'
        if 'sandbox' in self.host:
            endpoint_host = 'authorize.payments-sandbox.amazon.com'
        base = "/cobranded-ui/actions/start"

        params['callerKey'] = str(self.aws_access_key_id)
        params['returnURL'] = str(returnURL)
        params['pipelineName'] = str(pipelineName)
        params['maxFixedFee'] = str(maxFixedFee)
        params['maxVariableFee'] = str(maxVariableFee)
        params['recipientPaysFee'] = str(recipientPaysFee)
        params["signatureMethod"] = 'HmacSHA256'
        params["signatureVersion"] = '2'

        if(not params.has_key('callerReference')):
            params['callerReference'] = str(uuid.uuid4())

        parts = ''
        for k in sorted(params.keys()):
            parts += "&%s=%s" % (k, urllib.quote(params[k], '~'))

        canonical = '\n'.join(['GET',
                               str(endpoint_host).lower(),
                               base,
                               parts[1:]])

        signature = self._auth_handler.sign_string(canonical)
        params["signature"] = signature

        urlsuffix = ''
        for k in sorted(params.keys()):
            urlsuffix += "&%s=%s" % (k, urllib.quote(params[k], '~'))
        urlsuffix = urlsuffix[1:] # strip the first &
        
        fmt = "https://%(endpoint_host)s%(base)s?%(urlsuffix)s"
        final = fmt % vars()
        return final


    def make_url(self, returnURL, paymentReason, pipelineName,
                 transactionAmount, **params):
        """
        Generate the URL with the signature required for a transaction
        """
        # use the sandbox authorization endpoint if we're using the
        #  sandbox for API calls.
        endpoint_host = 'authorize.payments.amazon.com'
        if 'sandbox' in self.host:
            endpoint_host = 'authorize.payments-sandbox.amazon.com'
        base = "/cobranded-ui/actions/start"

        params['callerKey'] = str(self.aws_access_key_id)
        params['returnURL'] = str(returnURL)
        params['paymentReason'] = str(paymentReason)
        params['pipelineName'] = pipelineName
        params['transactionAmount'] = transactionAmount
        params["signatureMethod"] = 'HmacSHA256'
        params["signatureVersion"] = '2'
        
        if(not params.has_key('callerReference')):
            params['callerReference'] = str(uuid.uuid4())

        parts = ''
        for k in sorted(params.keys()):
            parts += "&%s=%s" % (k, urllib.quote(params[k], '~'))

        canonical = '\n'.join(['GET',
                               str(endpoint_host).lower(),
                               base,
                               parts[1:]])

        signature = self._auth_handler.sign_string(canonical)
        params["signature"] = signature

        urlsuffix = ''
        for k in sorted(params.keys()):
            urlsuffix += "&%s=%s" % (k, urllib.quote(params[k], '~'))
        urlsuffix = urlsuffix[1:] # strip the first &
        
        fmt = "https://%(endpoint_host)s%(base)s?%(urlsuffix)s"
        final = fmt % vars()
        return final

    def pay(self, transactionAmount, senderTokenId,
            recipientTokenId=None, callerTokenId=None,
            chargeFeeTo="Recipient",
            callerReference=None, senderReference=None, recipientReference=None,
            senderDescription=None, recipientDescription=None,
            callerDescription=None, metadata=None,
            transactionDate=None, reserve=False):
        """
        Make a payment transaction. You must specify the amount.
        This can also perform a Reserve request if 'reserve' is set to True.
        """
        params = {}
        params['SenderTokenId'] = senderTokenId
        # this is for 2008-09-17 specification
        params['TransactionAmount.Amount'] = str(transactionAmount)
        params['TransactionAmount.CurrencyCode'] = "USD"
        #params['TransactionAmount'] = str(transactionAmount)
        params['ChargeFeeTo'] = chargeFeeTo
        
        params['RecipientTokenId'] = (
            recipientTokenId if recipientTokenId is not None
            else boto.config.get("FPS", "recipient_token")
            )
        params['CallerTokenId'] = (
            callerTokenId if callerTokenId is not None
            else boto.config.get("FPS", "caller_token")
            )
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
    
    def refund(self, callerReference, transactionId, refundAmount=None,
               callerDescription=None):
        """
        Refund a transaction. This refunds the full amount by default
        unless 'refundAmount' is specified.
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
        Returns details about the token specified by 'CallerReference'.
        """
        params ={}
        params['CallerReference'] = callerReference
        
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
        Returns details about the token specified by 'TokenId'.
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

    def verify_signature(self, end_point_url, http_parameters):
        params = dict(
            UrlEndPoint = end_point_url,
            HttpParameters = http_parameters,
            )
        response = self.make_request("VerifySignature", params)
        body = response.read()
        if(response.status != 200):
            raise FPSResponseError(response.status, response.reason, body)
        rs = ResultSet()
        h = handler.XmlHandler(rs, self)
        xml.sax.parseString(body, h)
        return rs
