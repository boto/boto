# Copyright (c) 2010 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2010, Eucalyptus Systems, Inc.
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

import boto
import optparse

class Line(object):

    def __init__(self, fmt, data, label):
        self.fmt = fmt
        self.data = data
        self.label = label
        self.line = '%s\t' % label
        self.printed = False

    def append(self, datum):
        self.line += '%s\t' % datum

    def print_it(self):
        if not self.printed:
            print self.line
            self.printed = True

class Encoder:

    @classmethod
    def encode(cls, p, rp, v, label=None):
        try:
            mthd = getattr(cls, 'encode_'+p.ptype)
            mthd(p, rp, v, label)
        except AttributeError:
            raise 'Unknown type: %s' % p.ptype
        
    @classmethod
    def encode_string(cls, p, rp, v, l):
        if l:
            label = l
        else:
            label = boto.utils.awsify_name(p.name)
        rp[label] = v

    @classmethod
    def encode_integer(cls, p, rp, v, l):
        if l:
            label = l
        else:
            label = boto.utils.awsify_name(p.name)
        rp[label] = '%d' % v
        
    @classmethod
    def encode_boolean(cls, p, rp, v, l):
        if l:
            label = l
        else:
            label = boto.utils.awsify_name(p.name)
        if v:
            v = 'true'
        else:
            v = 'false'
        rp[label] = v
        
    @classmethod
    def encode_datetime(cls, p, rp, v, l):
        if l:
            label = l
        else:
            label = boto.utils.awsify_name(p.name)
        rp[label] = v
        
    @classmethod
    def encode_array(cls, p, rp, v, l):
        v = boto.utils.mklist(v)
        if l:
            label = l
        else:
            label = boto.utils.awsify_name(p.name)
        label = label + '.%d'
        for i, value in enumerate(v):
            rp[label%(i+1)] = value
            
class AWSQueryRequest(object):

    ServiceClass = None

    Name = 'AWSQueryRequest'
    Description = ''
    Params = []
    Filters = []
    Response = {}

    CLITypeMap = {'string' : 'string',
                  'integer' : 'int',
                  'int' : 'int',
                  'enum' : 'choice',
                  'datetime' : 'string',
                  'dateTime' : 'string',
                  'boolean' : 'string'}

    def __init__(self, **args):
        self.args = args
        self.parser = None
        self.cli_output_format = None
        self.connection = None
        self.list_markers = []
        self.item_markers = []
        self.request_params = {}
        self.process_args()

    def __repr__(self):
        return self.Name

    def get_connection(self, **args):
        if self.connection is None:
            self.connection = self.ServiceClass(**args)
        return self.connection

    @property
    def status(self):
        retval = None
        if self.http_response is not None:
            retval = self.http_response.status
        return retval

    @property
    def reason(self):
        retval = None
        if self.http_response is not None:
            retval = self.http_response.reason
        return retval

    @property
    def request_id(self):
        retval = None
        if self.Response is not None:
            retval = getattr(self.aws_response, 'requestId')
        return retval

    def process_filters(self, args):
        filter_names = [f['name'] for f in self.Filters]
        unknown_filters = [f for f in args if f not in filter_names]
        if unknown_filters:
            raise ValueError, 'Unknown filters: %s' % unknown_filters
        for i, filter in enumerate(self.Filters):
            if filter['name'] in args:
                self.request_params['Filter.%d.Name' % (i+1)] = filter['name']
                for j, value in enumerate(boto.utils.mklist(args[filter['name']])):
                    Encoder.encode(filter, self.request_params, value,
                                   'Filter.%d.Value.%d' % (i+1,j+1))

    def process_args(self):
        required = [p.name for p in self.Params if not p.optional]
        for param in self.Params:
            if param.long_name:
                python_name = param.long_name.replace('-', '_')
            else:
                python_name = boto.utils.pythonize_name(param.name, '_')
            if python_name in self.args:
                value = self.args[python_name]
                if value is not None:
                    if param.name in required:
                        required.remove(param.name)
                    Encoder.encode(param, self.request_params,
                                   self.args[python_name])
                del self.args[python_name]
        if required:
            raise ValueError, 'Required parameters missing: %s' % required
        boto.log.debug('request_params: %s' % self.request_params)
        self.process_markers(self.Response)

    def process_markers(self, fmt, prev_name=None):
        if fmt['type'] == 'object':
            for prop in fmt['properties']:
                self.process_markers(prop, fmt['name'])
        elif fmt['type'] == 'array':
            self.list_markers.append(prev_name)
            self.item_markers.append(fmt['name'])
        
    def send(self, verb='GET'):
        if 'debug' in self.args and self.args['debug'] >= 2:
            boto.set_stream_logger(self.name)
        conn = self.get_connection(**self.args)
        self.http_response = conn.make_request(self.Name,
                                               self.request_params,
                                               conn.path, verb)
        self.body = self.http_response.read()
        boto.log.debug(self.body)
        if self.http_response.status == 200:
            self.aws_response = boto.jsonresponse.Element(list_marker=self.list_markers,
                                                          item_marker=self.item_markers)
            h = boto.jsonresponse.XmlHandler(self.aws_response, self)
            h.parse(self.body)
            return self.aws_response
        else:
            boto.log.error('%s %s' % (self.http_response.status,
                                      self.http_response.reason))
            boto.log.error('%s' % self.body)
            raise conn.ResponseError(self.http_response.status,
                                     self.http_response.reason,
                                     self.body)

    def build_cli_parser(self):
        self.parser = optparse.OptionParser()
        self.parser.add_option('-D', '--debug', action='store_true',
                               help='Turn on all debugging output')
        if self.Filters:
            self.parser.add_option('--help-filters', action='store_true',
                                   help='Display list of available filters')
            self.parser.add_option('--filter', action='append',
                                   metavar=' name=value',
                                   help='A filter for limiting the results')
        for param in self.Params:
            if param.long_name:
                ptype = None
                if param.ptype in self.CLITypeMap:
                    ptype = self.CLITypeMap[param.ptype]
                    action = 'store'
                elif param.ptype == 'array':
                    if len(param.items) == 1:
                        ptype = param.items[0]['type']
                        action = 'append'
                if ptype:
                    if param.short_name:
                        self.parser.add_option(param.optparse_short_name,
                                               param.optparse_long_name,
                                               action=action, type=ptype,
                                               help=param.doc)
                    elif param.long_name:
                        self.parser.add_option(param.optparse_long_name,
                                               action=action, type=ptype,
                                               help=param.doc)

    def do_cli(self, cli_args=None):
        if not self.parser:
            self.build_cli_parser()
        options, args = self.parser.parse_args(cli_args)
        if hasattr(options, 'help_filters') and options.help_filters:
            print 'Available filters:'
            for filter in self.Filters:
                print '%s\t%s' % (filter['name'], filter['doc'])
            sys.exit(0)
        d = {}
        for param in self.Params:
            if param.long_name:
                p_name = param.long_name.replace('-', '_')
                d[p_name] = getattr(options, p_name)
            else:
                p_name = boto.utils.pythonize_name(param.name)
                d[p_name] = args
        self.args.update(d)
        try:
            self.process_args()
        except ValueError as ve:
            print ve.message
            sys.exit(1)
        if hasattr(options, 'filter') and options.filter:
            d = {}
            for filter in options.filter:
                name, value = filter.split('=')
                d[name] = value
            self.process_filters(d)
        try:
            if options.debug:
                 self.args['debug'] = 2
            response = self.send()
            self.cli_output_formatter(response)
        except self.get_connection().ResponseError as err:
            print 'Error(%s): %s' % (err.error_code, err.error_message)

    def _cli_fmt(self, fmt, data, line=None):
        if 'items' not in fmt:
            for key in fmt:
                self._cli_fmt(fmt[key], data[key], line)
        else:
            if isinstance(data, list):
                for data_item in data:
                    if 'label' in fmt:
                        if line:
                            line.print_it()
                        line = Line(fmt, data, fmt['label'])
                    for fmt_item in fmt['items']:
                        if isinstance(fmt_item, dict):
                            self._cli_fmt(fmt_item, data_item[fmt_item['name']], line)
                        else:
                            try:
                                val = data_item[fmt_item]
                                if not val:
                                    val = ''
                                line.append(val)
                            except KeyError:
                                boto.log.debug("%s not found in %s" % (fmt_item, data_item))
                    line.print_it()
                    line = None

    def _generic_cli_formatter(self, fmt, data, label=''):
        if fmt['type'] == 'object':
            for prop in fmt['properties']:
                if 'name' in fmt:
                    if fmt['name'] in data:
                        data = data[fmt['name']]
                    if fmt['name'] in self.list_markers:
                        label = fmt['name']
                        if label[-1] == 's':
                            label = label[0:-1]
                        label = label.upper()
                self._generic_cli_formatter(prop, data, label)
        elif fmt['type'] == 'array':
            for item in data:
                line = Line(fmt, item, label)
                if isinstance(item, dict):
                    for field_name in item:
                        line.append(item[field_name])
                elif isinstance(item, basestring):
                    line.append(item)
                line.print_it()

    def cli_output_formatter(self, aws_response):
        if self.cli_output_format:
            self._cli_fmt(self.cli_output_format, self.aws_response)
        elif self.Response:
            self._generic_cli_formatter(self.Response, aws_response)
        else:
            print 'No formatter found: dumping raw data'
            print aws_response

