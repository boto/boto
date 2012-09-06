# -*- coding: utf-8 -*-
# Copyright (c) 2012 Thomas Parslow http://almostobsolete.net/
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
#

from .layer1 import Layer1
from .vault import Vault


class Layer2(object):
    """
    Provides a more pythonic and friendly interface to Glacier based on Layer1
    """

    def __init__(self, *args, **kwargs):
        # Accept a passed in layer1, mainly to allow easier testing
        if "layer1" in kwargs:
            self.layer1 = kwargs["layer1"]
        else:
            self.layer1 = Layer1(*args, **kwargs)

    def create_vault(self, name):
        """
        Create a new vault.

        :type name: str
        :param name: The name of the vault
        """
        return self.layer1.create_vault(name)

    def get_vault(self, name):
        """
        Get an object representing a named vault from Glacier. This
        operation does not check if the vault actually exists.

        :type name: str
        :param name: The name of the vault

        :rtype: :class:`boto.glacier.vault.Vault`
        :return: A Vault object representing the vault.
        """
        response_data = self.layer1.describe_vault(name)
        return Vault(self.layer1, response_data)

    def list_vaults(self):
        """
        Return a list of all vaults associated with the account ID.

        :rtype: List of :class:`boto.glacier.vault.Vault`
        :return: A list of Vault objects.
        """
        response_data = self.layer1.list_vaults()
        return [Vault(self.layer1, rd) for rd in response_data['VaultList']]
