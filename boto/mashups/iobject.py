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

import os

def int_val_fn(v):
    try:
        int(v)
        return True
    except:
        return False
    
class IObject(object):
    
    def choose_from_list(self, item_list, search_str='',
                         prompt='Enter Selection'):
        if not item_list:
            print('No Choices Available')
            return
        choice = None
        while not choice:
            n = 1
            choices = []
            for item in item_list:
                if isinstance(item, str):
                    print('[{0:d}] {1:s}'.format(n, item))
                    choices.append(item)
                    n += 1
                else:
                    obj, id, desc = item
                    if desc:
                        if desc.find(search_str) >= 0:
                            print('[{0:d}] {1:s} - {2:s}'.format(n, id, desc))
                            choices.append(obj)
                            n += 1
                    else:
                        if id.find(search_str) >= 0:
                            print('[{0:d}] {1:s}'.format(n, id))
                            choices.append(obj)
                            n += 1
            if choices:
                val = input('{0:s}[1-{1:d}]: '.format(prompt, len(choices)))
                if val.startswith('/'):
                    search_str = val[1:]
                else:
                    try:
                        int_val = int(val)
                        if int_val == 0:
                            return None
                        choice = choices[int_val-1]
                    except ValueError:
                        print('{0:s} is not a valid choice'.format(val))
                    except IndexError:
                        print('{0:s} is not within the range[1-{1:d}]'.format(val,
                                                                               len(choices)))
            else:
                print("No objects matched your pattern")
                search_str = ''
        return choice

    def get_string(self, prompt, validation_fn=None):
        okay = False
        while not okay:
            val = input('{0:s}: '.format(prompt))
            if validation_fn:
                okay = validation_fn(val)
                if not okay:
                    print('Invalid value: {0:s}'.format(val))
            else:
                okay = True
        return val

    def get_filename(self, prompt):
        okay = False
        val = ''
        while not okay:
            val = input('{0:s}: {1:s}'.format(prompt, val))
            val = os.path.expanduser(val)
            if os.path.isfile(val):
                okay = True
            elif os.path.isdir(val):
                path = val
                val = self.choose_from_list(os.listdir(path))
                if val:
                    val = os.path.join(path, val)
                    okay = True
                else:
                    val = ''
            else:
                print('Invalid value: {0:s}'.format(val))
                val = ''
        return val

    def get_int(self, prompt):
        s = self.get_string(prompt, int_val_fn)
        return int(s)

