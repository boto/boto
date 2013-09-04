import xml

from boto.handler import XmlHandler
from boto.mws.connection import MWSConnection
from boto.mws.response import GetFulfillmentOrderResult

from unittest import TestCase


class TestResponseParser(TestCase):

    def test_get_fulfillment_order_response(self):
        mws = MWSConnection('fake', 'fake')
        obj = GetFulfillmentOrderResult(mws)
        h = XmlHandler(obj, mws)
        xml.sax.parseString(GET_FULFILLMENT_ORDER_RESPONSE, h)





GET_FULFILLMENT_ORDER_RESPONSE = """<?xml version="1.0"?>
<GetFulfillmentOrderResponse xmlns="http://mws.amazonaws.com/FulfillmentOutboundShipment/2010-10-01/">
    <GetFulfillmentOrderResult>
        <FulfillmentOrderItem>
            <member>
                <SellerSKU>ssof_dev_drt_afn_item</SellerSKU>
                <GiftMessage>test_giftwrap_message</GiftMessage>
                <SellerFulfillmentOrderItemId>test_merchant_order_item_id_2</SellerFulfillmentOrderItemId>
                <EstimatedShipDateTime>2008-03-08T07:07:53Z</EstimatedShipDateTime>
                <DisplayableComment>test_displayable_comment</DisplayableComment>
                <OrderItemDisposition>Sellable</OrderItemDisposition>
                <UnfulfillableQuantity>0</UnfulfillableQuantity>
                <CancelledQuantity>1</CancelledQuantity>
                <Quantity>5</Quantity>
                <EstimatedArrivalDateTime>2008-03-08T08:07:53Z</EstimatedArrivalDateTime>
            </member>
            <member>
                <SellerSKU>ssof_dev_drt_keep_this_afn_always</SellerSKU>
                <GiftMessage>test_giftwrap_message</GiftMessage>
                <SellerFulfillmentOrderItemId>test_merchant_order_item_id_1</SellerFulfillmentOrderItemId>
                <EstimatedShipDateTime>2008-03-09T07:07:53Z</EstimatedShipDateTime>
                <DisplayableComment>test_displayable_comment</DisplayableComment>
                <OrderItemDisposition>Sellable</OrderItemDisposition>
                <UnfulfillableQuantity>2</UnfulfillableQuantity>
                <CancelledQuantity>1</CancelledQuantity>
                <Quantity>5</Quantity>
                <EstimatedArrivalDateTime>2008-03-09T08:07:53Z</EstimatedArrivalDateTime>
            </member>
        </FulfillmentOrderItem>
        <FulfillmentOrder>
            <ShippingSpeedCategory>Standard</ShippingSpeedCategory>
            <NotificationEmailList>
                <member>o8c2EXAMPLsfr7o@marketplace.amazon.com</member>
            </NotificationEmailList>
            <StatusUpdatedDateTime>2006-09-28T23:48:48Z
            </StatusUpdatedDateTime>
            <SellerFulfillmentOrderId>extern_id_1154539615776</SellerFulfillmentOrderId>
            <DestinationAddress>
                <PostalCode>98101</PostalCode>
                <PhoneNumber>206-555-1928</PhoneNumber>
                <Name>Greg Miller</Name>
                <CountryCode>US</CountryCode>
                <Line1>123 Some St.</Line1>
                <StateOrProvinceCode>WA</StateOrProvinceCode>
                <City>Seattle</City>
                <Line2>Apt. 321</Line2>
            </DestinationAddress>
            <FulfillmentMethod>Consumer</FulfillmentMethod>
            <DisplayableOrderDateTime>2006-08-02T17:26:56Z</DisplayableOrderDateTime>
            <FulfillmentPolicy>FillOrKill</FulfillmentPolicy>
            <ReceivedDateTime>2006-08-02T17:26:56Z</ReceivedDateTime>
            <DisplayableOrderId>test_displayable_id</DisplayableOrderId>
            <DisplayableOrderComment>Sample comment.</DisplayableOrderComment>
            <FulfillmentOrderStatus>PROCESSING</FulfillmentOrderStatus>
        </FulfillmentOrder>
        <FulfillmentShipment>
            <member>
                <FulfillmentShipmentStatus>PENDING</FulfillmentShipmentStatus>
                <FulfillmentShipmentItem>
                    <member>
                        <SellerSKU>ssof_dev_drt_afn_item</SellerSKU>
                        <SellerFulfillmentOrderItemId>test_merchant_order_item_id_2</SellerFulfillmentOrderItemId>
                        <Quantity>2</Quantity>
                        <PackageNumber>0</PackageNumber>
                    </member>
                </FulfillmentShipmentItem>
                <AmazonShipmentId>DnMDLWJWN</AmazonShipmentId>
                <ShippingDateTime>2006-08-04T07:00:00Z</ShippingDateTime>
                <FulfillmentCenterId>RNO1</FulfillmentCenterId>
                <EstimatedArrivalDateTime>2006-08-12T07:00:00Z</EstimatedArrivalDateTime>
            </member>
            <member>
                <FulfillmentShipmentStatus>SHIPPED</FulfillmentShipmentStatus>
                <FulfillmentShipmentItem>
                    <member>
                        <SellerSKU>ssof_dev_drt_afn_item</SellerSKU>
                        <SellerFulfillmentOrderItemId>test_merchant_order_item_id_2</SellerFulfillmentOrderItemId>
                        <Quantity>1</Quantity>
                        <PackageNumber>1</PackageNumber>
                    </member>
                </FulfillmentShipmentItem>
                <AmazonShipmentId>DKMKLXJmN</AmazonShipmentId>
                <ShippingDateTime>2006-08-03T07:00:00Z</ShippingDateTime>
                <FulfillmentShipmentPackage>
                    <member>
                        <TrackingNumber>93ZZ00</TrackingNumber>
                        <CarrierCode>UPS</CarrierCode>
                        <PackageNumber>1</PackageNumber>
                    </member>
                </FulfillmentShipmentPackage>
                <FulfillmentCenterId>TST1</FulfillmentCenterId>
                <EstimatedArrivalDateTime>2006-08-12T07:00:00Z</EstimatedArrivalDateTime>
            </member>
        </FulfillmentShipment>
    </GetFulfillmentOrderResult>
    <ResponseMetadata>
        <RequestId>5e5e5694-8e76-11df-929f-87c80302f8f6</RequestId>
    </ResponseMetadata>
</GetFulfillmentOrderResponse>"""
