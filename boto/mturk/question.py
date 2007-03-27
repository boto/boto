# Copyright (c) 2006,2007 Mitch Garnaat http://garnaat.org/
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

class Question:
    
    QUESTIONFORM_SCHEMA_LOCATION = "http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionForm.xsd"

    QUESTIONFORM_XML_TEMPLATE = """<QuestionForm xmlns="%s"><Question><QuestionIdentifier>%s</QuestionIdentifier>%s%s</Question></QuestionForm>"""
    
    def __init__(self, identifier, content, answer_spec): #amount=0.0, currency_code='USD'):
        self.identifier = identifier
        self.content = content
        self.answer_spec = answer_spec
    
    #def __repr__(self):
    #    if self.formatted_price:
    #        return self.formatted_price
    #    else:
    #        return str(self.amount)
    
    def startElement(self, name, attrs, connection):
        return None
    
    def endElement(self, name, value, connection):
        
        #if name == 'Amount':
        #    self.amount = float(value)
        #elif name == 'CurrencyCode':
        #    self.currency_code = value
        #elif name == 'FormattedPrice':
        #    self.formatted_price = value
        
        pass # What's this method for?  I don't get it.
    
    def get_as_params(self, label='Question', identifier=None):
        
        if identifier is None:
            raise ValueError("identifier (QuestionIdentifier) is required per MTurk spec.")
        
        return { label : self.get_as_xml() }
    
    def get_as_xml(self):
        # Very basic QuestionForm template
        values = (Question.QUESTIONFORM_SCHEMA_LOCATION, self.identifier, self.content.get_as_xml(), self.answer_spec.get_as_xml())
        return Question.QUESTIONFORM_XML_TEMPLATE % values

class QuestionContent:
    
    def __init__(self, title=None, text=None, bulleted_list=None, binary=None, application=None, formatted_content=None):
        self.title = title
        self.text = text
        self.bulleted_list = bulleted_list
        self.binary = binary
        self.application = application
        self.formatted_content = formatted_content
        
    def get_title_xml(self):
        if self.title is None:
            return '' # empty
        else:
            return "<Title>%s</Title>" % self.title
    
    def get_text_xml(self):
        if self.text is None:
            return ''
        else:
            return "<Text>%s</Text>" % self.text
    
    def get_bulleted_list_xml(self):
        if self.bulleted_list is None:
            return ''
        elif type(self.bulleted_list) is list:
            return "<List>%s</List>" % self.get_bulleted_list_items_xml()
        else:
            raise ValueError("QuestionContent bulleted_list argument should be a list.")
    
    def get_bulleted_list_items_xml(self):
        ret = ""
        for item in self.bulleted_list:
            ret = ret + "<ListItem>%s</ListItem>" % item
        return ret
    
    def get_binary_xml(self):
        if self.binary is None:
            return ''
        else:
            raise NotImplementedError("Binary question content is not yet supported.")
    
    def get_application_xml(self):
        if self.application is None:
            return ''
        else:
            raise NotImplementedError("Application question content is not yet supported.")
    
    def get_formatted_content_xml(self):
        if self.formatted_content is None:
            return ''
        else:
            return "<FormattedContent><![CDATA[%s]]></FormattedContent>" % self.formatted_content
    
    def get_as_xml(self):
        children = self.get_title_xml() + self.get_text_xml() + self.get_bulleted_list_xml() + self.get_binary_xml() + self.get_application_xml() + self.get_formatted_content_xml()
        return "<QuestionContent>%s</QuestionContent>" % children

class AnswerSpecification:
    
    #ANSWERSPECIFICATION_XML_TEMPLATE = """
    #    <AnswerSpecification>
    #        <FreeTextAnswer>
    #            <Constraints>
    #                <Length minLength="2" maxLength="2" />
    #            </Constraints>
    #            <DefaultText>C1</DefaultText>
    #        </FreeTextAnswer>
    #    </AnswerSpecification>
    #"""
    
    ANSWERSPECIFICATION_XML_TEMPLATE = """<AnswerSpecification><FreeTextAnswer><Constraints><Length minLength="2" maxLength="2" /></Constraints><DefaultText>C1</DefaultText></FreeTextAnswer></AnswerSpecification>"""
    
    def __init__(self):
        pass
    def get_as_xml(self):
        values = () # TODO
        return AnswerSpecification.ANSWERSPECIFICATION_XML_TEMPLATE % values
