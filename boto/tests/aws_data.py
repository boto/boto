#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# Copyright (c) 2008 Fabien Schwob http://fabien.schwob.org
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

from lxml import etree

item_xml_snippets1 = etree.fromstring("""<Item>
<ASIN>0545010225</ASIN>

<DetailPageURL>
http://www.amazon.com/gp/redirect.html%3FASIN=0545010225%26tag=ws%26lcode=xm2%26cID=2025%26ccmID=165953%26location=/o/ASIN/0545010225%253FSubscriptionId=06Z1EY48VX81JPFG3082
</DetailPageURL>

<ItemAttributes>
<Author>J. K. Rowling</Author>
<Creator Role="Illustrator">Mary GrandPré</Creator>
<Manufacturer>Arthur A. Levine Books</Manufacturer>
<ProductGroup>Book</ProductGroup>
<Title>Harry Potter and the Deathly Hallows (Book 7)</Title>
</ItemAttributes>
</Item>""")

item_xml_snippets2 = etree.fromstring("""<Item>
<ASIN>0321503619</ASIN>

<DetailPageURL>
http://www.amazon.com/gp/redirect.html%3FASIN=0321503619%26tag=ws%26lcode=xm2%26cID=2025%26ccmID=165953%26location=/o/ASIN/0321503619%253FSubscriptionId=06Z1EY48VX81JPFG3082
</DetailPageURL>

<ItemAttributes>
<Author>Aaron Hillegass</Author>
<Manufacturer>Addison-Wesley Professional</Manufacturer>
<ProductGroup>Book</ProductGroup>
<Title>Cocoa® Programming for Mac® OS X (3rd Edition)</Title>
</ItemAttributes>
</Item>""")

item_search_response_xml = """<?xml version="1.0" encoding="UTF-8"?>
<ItemSearchResponse xmlns="http://webservices.amazon.com/AWSECommerceService/2007-07-16">
  <OperationRequest>
    <HTTPHeaders>
      <Header Name="UserAgent" Value="Python-urllib/1.17"></Header>
    </HTTPHeaders>
    <RequestId>0MY2CEX0AEZY1EB7CR0F</RequestId>
    <Arguments>
      <Argument Name="SearchIndex" Value="Books"></Argument>
      <Argument Name="Service" Value="AWSECommerceService"></Argument>
      <Argument Name="Title" Value="Harry%20Potter"></Argument>
      <Argument Name="Operation" Value="ItemSearch"></Argument>
      <Argument Name="AWSAccessKeyId" Value="DUMB_KEY"></Argument>
      <Argument Name="Version" Value="2007-07-16"></Argument>
    </Arguments>
    <RequestProcessingTime>0.0583951473236084</RequestProcessingTime>
  </OperationRequest>
  <Items>
    <Request>
      <IsValid>True</IsValid>
      <ItemSearchRequest>
        <SearchIndex>Books</SearchIndex>
        <Title>Harry%20Potter</Title>
      </ItemSearchRequest>
    </Request>
    <TotalResults>1286</TotalResults>
    <TotalPages>129</TotalPages>
    <Item>
      <ASIN>0545010225</ASIN>
      <DetailPageURL>http://www.amazon.com/gp/redirect.html%3FASIN=0545010225%26tag=ws%26lcode=xm2%26cID=2025%26ccmID=165953%26location=/o/ASIN/0545010225%253FSubscriptionId=06Z1EY48VX81JPFG3082</DetailPageURL>
      <ItemAttributes>
        <Author>J. K. Rowling</Author>
        <Creator Role="Illustrator">Mary GrandPré</Creator>
        <Manufacturer>Arthur A. Levine Books</Manufacturer>
        <ProductGroup>Book</ProductGroup>
        <Title>Harry Potter and the Deathly Hallows (Book 7)</Title>
      </ItemAttributes>
    </Item>
    <Item>
      <ASIN>0439887453</ASIN>
      <DetailPageURL>http://www.amazon.com/gp/redirect.html%3FASIN=0439887453%26tag=ws%26lcode=xm2%26cID=2025%26ccmID=165953%26location=/o/ASIN/0439887453%253FSubscriptionId=06Z1EY48VX81JPFG3082</DetailPageURL>
      <ItemAttributes>
        <Author>J.K. Rowling</Author>
        <Creator Role="Illustrator">Mary GrandPré</Creator>
        <Manufacturer>Scholastic Inc.</Manufacturer>
        <ProductGroup>Book</ProductGroup>
        <Title>Harry Potter Paperback Box Set (Books 1-6)</Title>
      </ItemAttributes>
    </Item>
    <Item>
      <ASIN>0439785960</ASIN>
      <DetailPageURL>http://www.amazon.com/gp/redirect.html%3FASIN=0439785960%26tag=ws%26lcode=xm2%26cID=2025%26ccmID=165953%26location=/o/ASIN/0439785960%253FSubscriptionId=06Z1EY48VX81JPFG3082</DetailPageURL>
      <ItemAttributes>
        <Author>J.K. Rowling</Author>
        <Creator Role="Illustrator">Mary GrandPré</Creator>
        <Manufacturer>Scholastic Paperbacks</Manufacturer>
        <ProductGroup>Book</ProductGroup>
        <Title>Harry Potter and the Half-Blood Prince (Book 6)</Title>
      </ItemAttributes>
    </Item>
    <Item><ASIN>0545044251</ASIN><DetailPageURL>http://www.amazon.com/gp/redirect.html%3FASIN=0545044251%26tag=ws%26lcode=xm2%26cID=2025%26ccmID=165953%26location=/o/ASIN/0545044251%253FSubscriptionId=06Z1EY48VX81JPFG3082</DetailPageURL><ItemAttributes><Author>J. K. Rowling</Author><Manufacturer>Arthur A. Levine Books</Manufacturer><ProductGroup>Book</ProductGroup><Title>Harry Potter Boxset Books 1-7</Title></ItemAttributes></Item><Item><ASIN>0590353403</ASIN><DetailPageURL>http://www.amazon.com/gp/redirect.html%3FASIN=0590353403%26tag=ws%26lcode=xm2%26cID=2025%26ccmID=165953%26location=/o/ASIN/0590353403%253FSubscriptionId=06Z1EY48VX81JPFG3082</DetailPageURL><ItemAttributes><Author>J.K. Rowling</Author><Creator Role="Illustrator">Mary GrandPré</Creator><Manufacturer>Scholastic Press</Manufacturer><ProductGroup>Book</ProductGroup><Title>Harry Potter and the Sorcerer's Stone (Book 1)</Title></ItemAttributes></Item><Item><ASIN>0439358078</ASIN><DetailPageURL>http://www.amazon.com/gp/redirect.html%3FASIN=0439358078%26tag=ws%26lcode=xm2%26cID=2025%26ccmID=165953%26location=/o/ASIN/0439358078%253FSubscriptionId=06Z1EY48VX81JPFG3082</DetailPageURL><ItemAttributes><Author>J. K. Rowling</Author><Author>Mary GrandPré</Author><Manufacturer>Scholastic Paperbacks</Manufacturer><ProductGroup>Book</ProductGroup><Title>Harry Potter and the Order of the Phoenix (Book 5)</Title></ItemAttributes></Item><Item><ASIN>0439136350</ASIN><DetailPageURL>http://www.amazon.com/gp/redirect.html%3FASIN=0439136350%26tag=ws%26lcode=xm2%26cID=2025%26ccmID=165953%26location=/o/ASIN/0439136350%253FSubscriptionId=06Z1EY48VX81JPFG3082</DetailPageURL><ItemAttributes><Author>J.K. Rowling</Author><Creator Role="Illustrator">Mary GrandPré</Creator><Manufacturer>Scholastic</Manufacturer><ProductGroup>Book</ProductGroup><Title>Harry Potter and the Prisoner of Azkaban (Book 3)</Title></ItemAttributes></Item><Item><ASIN>0439064864</ASIN><DetailPageURL>http://www.amazon.com/gp/redirect.html%3FASIN=0439064864%26tag=ws%26lcode=xm2%26cID=2025%26ccmID=165953%26location=/o/ASIN/0439064864%253FSubscriptionId=06Z1EY48VX81JPFG3082</DetailPageURL><ItemAttributes><Author>J.K. Rowling</Author><Creator Role="Illustrator">Mary GrandPré</Creator><Manufacturer>Arthur A. Levine Books</Manufacturer><ProductGroup>Book</ProductGroup><Title>Harry Potter and the Chamber of Secrets (Book 2)</Title></ItemAttributes></Item><Item><ASIN>0439139597</ASIN><DetailPageURL>http://www.amazon.com/gp/redirect.html%3FASIN=0439139597%26tag=ws%26lcode=xm2%26cID=2025%26ccmID=165953%26location=/o/ASIN/0439139597%253FSubscriptionId=06Z1EY48VX81JPFG3082</DetailPageURL><ItemAttributes><Author>J.K. Rowling</Author><Creator Role="Illustrator">Mary GrandPré</Creator><Manufacturer>Scholastic Press</Manufacturer><ProductGroup>Book</ProductGroup><Title>Harry Potter and the Goblet of Fire (Book 4)</Title></ItemAttributes></Item><Item><ASIN>043932162X</ASIN><DetailPageURL>http://www.amazon.com/gp/redirect.html%3FASIN=043932162X%26tag=ws%26lcode=xm2%26cID=2025%26ccmID=165953%26location=/o/ASIN/043932162X%253FSubscriptionId=06Z1EY48VX81JPFG3082</DetailPageURL><ItemAttributes><Author>J.K. Rowling</Author><Manufacturer>Arthur A. Levine Books</Manufacturer><ProductGroup>Book</ProductGroup><Title>Harry Potter Schoolbooks Box Set: From the Library of Hogwarts: Fantastic Beasts and Where To Find Them, Quidditch Through The Ages</Title></ItemAttributes></Item></Items></ItemSearchResponse>
"""
