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

class Question(object):
    
    QUESTION_XML_TEMPLATE = """<Question><QuestionIdentifier>%s</QuestionIdentifier>%s<IsRequired>%s</IsRequired>%s%s</Question>"""
    DISPLAY_NAME_XML_TEMPLATE = """<DisplayName>%s</DisplayName>"""
    
    def __init__(self, identifier, content, answer_spec, is_required=False, display_name=None): #amount=0.0, currency_code='USD'):
        self.identifier = identifier
        self.content = content
        self.answer_spec = answer_spec
        self.is_required = is_required
        self.display_name = display_name
    
    def get_as_params(self, label='Question', identifier=None):
        
        if identifier is None:
            raise ValueError("identifier (QuestionIdentifier) is required per MTurk spec.")
        
        return { label : self.get_as_xml() }
    
    def get_as_xml(self):
        # add the display name if required
        display_name_xml = ''
        if self.display_name:
            display_name_xml = self.DISPLAY_NAME_XML_TEMPLATE %(self.display_name)

        ret = Question.QUESTION_XML_TEMPLATE % (self.identifier, 
                                                display_name_xml,
                                                str(self.is_required).lower(),
                                                self.content.get_as_xml(), 
                                                self.answer_spec.get_as_xml())

        return ret

class ExternalQuestion(object):
    
    EXTERNAL_QUESTIONFORM_SCHEMA_LOCATION = "http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2006-07-14/ExternalQuestion.xsd"
    EXTERNAL_QUESTION_XML_TEMPLATE = """<ExternalQuestion xmlns="%s"><ExternalURL>%s</ExternalURL><FrameHeight>%s</FrameHeight></ExternalQuestion>"""
    
    def __init__(self, external_url, frame_height):
        self.external_url = external_url
        self.frame_height = frame_height
    
    def get_as_params(self, label='ExternalQuestion'):
        return { label : self.get_as_xml() }
    
    def get_as_xml(self):
        ret = ExternalQuestion.EXTERNAL_QUESTION_XML_TEMPLATE % (ExternalQuestion.EXTERNAL_QUESTIONFORM_SCHEMA_LOCATION,
                                                self.external_url,
                                                self.frame_height)
        return ret



class QuestionForm(object):
    
    QUESTIONFORM_SCHEMA_LOCATION = "http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionForm.xsd"
    QUESTIONFORM_XML_TEMPLATE = """<QuestionForm xmlns="%s">%s</QuestionForm>""" # % (ns, questions_xml)
    
    def __init__(self, questions=None):
        if questions is None or type(questions) is not list:
            raise ValueError("Must pass a list of Question instances to QuestionForm constructor")
        else:
            self.questions = questions
    
    def get_as_xml(self):
        questions_xml = "".join([q.get_as_xml() for q in self.questions])
        return QuestionForm.QUESTIONFORM_XML_TEMPLATE % (QuestionForm.QUESTIONFORM_SCHEMA_LOCATION, questions_xml)
    
    #def startElement(self, name, attrs, connection):
    #    return None
    #
    #def endElement(self, name, value, connection):
    #    
    #    #if name == 'Amount':
    #    #    self.amount = float(value)
    #    #elif name == 'CurrencyCode':
    #    #    self.currency_code = value
    #    #elif name == 'FormattedPrice':
    #    #    self.formatted_price = value
    #    
    #    pass # What's this method for?  I don't get it.

class QuestionContent(object):
    
    def __init__(self, title=None, text=None, bulleted_list=None, 
                 binary=None, binary_type=None, binary_subtype=None, binary_alttext=None,
                 application=None, formatted_content=None):
        if binary:
            # TODO: attempt to auto-detect mimetype from binary url
            assert (binary_type and binary_subtype and binary_alttext), "Type, subtype and alttext are required for binary alements"
        self.title = title
        self.text = text
        self.bulleted_list = bulleted_list
        self.binary = binary
        self.binary_type = binary_type
        self.binary_subtype = binary_subtype
        self.binary_alttext = binary_alttext
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
            return """
<Binary>
  <MimeType>
    <Type>%s</Type>
    <SubType>%s</SubType>
  </MimeType>
  <DataURL>%s</DataURL>
  <AltText>%s</AltText>
</Binary>""" %(self.binary_type, self.binary_subtype, self.binary, self.binary_alttext )
    
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

class AnswerSpecification(object):
    
    ANSWERSPECIFICATION_XML_TEMPLATE = """<AnswerSpecification>%s</AnswerSpecification>"""
    
    def __init__(self, spec):
        self.spec = spec
    def get_as_xml(self):
        values = () # TODO
        return AnswerSpecification.ANSWERSPECIFICATION_XML_TEMPLATE % self.spec.get_as_xml()

class FreeTextAnswer(object):
    
    FREETEXTANSWER_XML_TEMPLATE = """<FreeTextAnswer>%s%s</FreeTextAnswer>""" # (constraints, default)
    FREETEXTANSWER_CONSTRAINTS_XML_TEMPLATE = """<Constraints>%s%s%s</Constraints>""" # (is_numeric_xml, length_xml, regex_xml)
    FREETEXTANSWER_LENGTH_XML_TEMPLATE = """<Length %s %s />""" # (min_length_attr, max_length_attr)
    FREETEXTANSWER_ISNUMERIC_XML_TEMPLATE = """<IsNumeric %s %s />""" # (min_value_attr, max_value_attr)
    FREETEXTANSWER_DEFAULTTEXT_XML_TEMPLATE = """<DefaultText>%s</DefaultText>""" # (default)
    
    def __init__(self, default=None, min_length=None, max_length=None, is_numeric=False, min_value=None, max_value=None, format_regex=None):
        self.default = default
        self.min_length = min_length
        self.max_length = max_length
        self.is_numeric = is_numeric
        self.min_value = min_value
        self.max_value = max_value
        self.format_regex = format_regex
    
    def get_as_xml(self):
        is_numeric_xml = ""
        if self.is_numeric:
            min_value_attr = ""
            max_value_attr = ""
            if self.min_value:
                min_value_attr = """minValue="%d" """ % self.min_value
            if self.max_value:
                max_value_attr = """maxValue="%d" """ % self.max_value
            is_numeric_xml = FreeTextAnswer.FREETEXTANSWER_ISNUMERIC_XML_TEMPLATE % (min_value_attr, max_value_attr)
        
        length_xml = ""
        if self.min_length or self.max_length:
            min_length_attr = ""
            max_length_attr = ""
            if self.min_length:
                min_length_attr = """minLength="%d" """
            if self.max_length:
                max_length_attr = """maxLength="%d" """
            length_xml = FreeTextAnswer.FREETEXTANSWER_LENGTH_XML_TEMPLATE % (min_length_attr, max_length_attr)

        regex_xml = ""
        if self.format_regex:
            format_regex_attribs = '''regex="%s"''' %self.format_regex['regex']

            error_text = self.format_regex.get('error_text', None)
            if error_text:
                format_regex_attribs += ' errorText="%s"' %error_text

            flags = self.format_regex.get('flags', None)
            if flags:
                format_regex_attribs += ' flags="%s"' %flags

            regex_xml = """<AnswerFormatRegex %s/>""" %format_regex_attribs
            
        constraints_xml = ""
        if is_numeric_xml or length_xml or regex_xml:
            constraints_xml = FreeTextAnswer.FREETEXTANSWER_CONSTRAINTS_XML_TEMPLATE % (is_numeric_xml, length_xml, regex_xml)
        
        default_xml = ""
        if self.default is not None:
            default_xml = FreeTextAnswer.FREETEXTANSWER_DEFAULTTEXT_XML_TEMPLATE % self.default
            
        return FreeTextAnswer.FREETEXTANSWER_XML_TEMPLATE % (constraints_xml, default_xml)

class FileUploadAnswer(object):
    FILEUPLOADANSWER_XML_TEMLPATE = """<FileUploadAnswer><MinFileSizeInBytes>%d</MinFileSizeInBytes><MaxFileSizeInBytes>%d</MaxFileSizeInBytes></FileUploadAnswer>""" # (min, max)
    DEFAULT_MIN_SIZE = 1024 # 1K (completely arbitrary!)
    DEFAULT_MAX_SIZE = 5 * 1024 * 1024 # 5MB (completely arbitrary!)
    
    def __init__(self, min=None, max=None):
        self.min = min
        self.max = max
        if self.min is None:
            self.min = FileUploadAnswer.DEFAULT_MIN_SIZE
        if self.max is None:
            self.max = FileUploadAnswer.DEFAULT_MAX_SIZE
    
    def get_as_xml(self):
        return FileUploadAnswer.FILEUPLOADANSWER_XML_TEMLPATE % (self.min, self.max)

class SelectionAnswer(object):
    """
    A class to generate SelectionAnswer XML data structures.
    Does not yet implement Binary selection options.
    """
    SELECTIONANSWER_XML_TEMPLATE = """<SelectionAnswer>%s%s<Selections>%s</Selections></SelectionAnswer>""" # % (count_xml, style_xml, selections_xml)
    SELECTION_XML_TEMPLATE = """<Selection><SelectionIdentifier>%s</SelectionIdentifier>%s</Selection>""" # (identifier, value_xml)
    SELECTION_VALUE_XML_TEMPLATE = """<%s>%s</%s>""" # (type, value, type)
    STYLE_XML_TEMPLATE = """<StyleSuggestion>%s</StyleSuggestion>""" # (style)
    MIN_SELECTION_COUNT_XML_TEMPLATE = """<MinSelectionCount>%s</MinSelectionCount>""" # count
    MAX_SELECTION_COUNT_XML_TEMPLATE = """<MaxSelectionCount>%s</MaxSelectionCount>""" # count
    ACCEPTED_STYLES = ['radiobutton', 'dropdown', 'checkbox', 'list', 'combobox', 'multichooser']
    OTHER_SELECTION_ELEMENT_NAME = 'OtherSelection'
    
    def __init__(self, min=1, max=1, style=None, selections=None, type='text', other=False):
        
        if style is not None:
            if style in SelectionAnswer.ACCEPTED_STYLES:
                self.style_suggestion = style
            else:
                raise ValueError("style '%s' not recognized; should be one of %s" % (style, ', '.join(SelectionAnswer.ACCEPTED_STYLES)))
        else:
            self.style_suggestion = None
        
        if selections is None:
            raise ValueError("SelectionAnswer.__init__(): selections must be a non-empty list of (content, identifier) tuples")
        else:
            self.selections = selections
        
        self.min_selections = min
        self.max_selections = max
        
        assert len(selections) >= self.min_selections, "# of selections is less than minimum of %d" % self.min_selections
        #assert len(selections) <= self.max_selections, "# of selections exceeds maximum of %d" % self.max_selections
        
        self.type = type
        
        self.other = other
    
    def get_as_xml(self):
        xml = ""
        if self.type == 'text':
            TYPE_TAG = "Text"
        elif self.type == 'binary':
            TYPE_TAG = "Binary"
        else:
            raise ValueError("illegal type: %s; must be either 'text' or 'binary'" % str(self.type))
        
        # build list of <Selection> elements
        selections_xml = ""
        for tpl in self.selections:
            value_xml = SelectionAnswer.SELECTION_VALUE_XML_TEMPLATE % (TYPE_TAG, tpl[0], TYPE_TAG)
            selection_xml = SelectionAnswer.SELECTION_XML_TEMPLATE % (tpl[1], value_xml)
            selections_xml += selection_xml
        
        if self.other:
            # add OtherSelection element as xml if available
            if hasattr(self.other, 'get_as_xml'):
                assert type(self.other) == FreeTextAnswer, 'OtherSelection can only be a FreeTextAnswer'
                selections_xml += self.other.get_as_xml().replace('FreeTextAnswer', 'OtherSelection')
            else:
                selections_xml += "<OtherSelection />"
        
        if self.style_suggestion is not None:
            style_xml = SelectionAnswer.STYLE_XML_TEMPLATE % self.style_suggestion
        else:
            style_xml = ""

        if self.style_suggestion != 'radiobutton':
            count_xml = SelectionAnswer.MIN_SELECTION_COUNT_XML_TEMPLATE %self.min_selections
            count_xml += SelectionAnswer.MAX_SELECTION_COUNT_XML_TEMPLATE %self.max_selections
        else:
            count_xml = ""
        
        ret = SelectionAnswer.SELECTIONANSWER_XML_TEMPLATE % (count_xml, style_xml, selections_xml)

        # return XML
        return ret
        
