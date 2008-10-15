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

class Qualifications:

    def __init__(self, requirements = []):
        self.requirements = requirements

    def add(self, req):
        self.requirements.append(req)

    def get_as_params(self):
        params = {}
        assert(len(self.requirements) <= 10)
        for n, req in enumerate(self.requirements):
            params["QualificationRequirement.%s.QualificationTypeId" % (n+1)] = req.qualification_type_id
            params["QualificationRequirement.%s.Comparator" % (n+1)] = req.comparator
            params["QualificationRequirement.%s.IntegerValue" % (n+1)] = req.integer_value
            if req.required_to_preview:
                params["QualificationRequirement.%s.RequiredToPreview" % (n+1)] = "true"
        return params


class Requirement:
    """
    Representation of a single requirement
    """

    def __init__(self, qualification_type_id, comparator, integer_value, required_to_preview=False):
        self.qualification_type_id = qualification_type_id
        self.comparator = comparator
        self.integer_value = integer_value
        self.required_to_preview = required_to_preview

class PercentAssignmentsSubmittedRequirement(Requirement):
    """
    The percentage of assignments the Worker has submitted, over all assignments the Worker has accepted. The value is an integer between 0 and 100.
    """

    def __init__(self, comparator, integer_value, required_to_preview=False):
        Requirement.__init__(self, qualification_type_id="00000000000000000000", comparator=comparator, integer_value=integer_value, required_to_preview=required_to_preview)

class PercentAssignmentsAbandonedRequirement(Requirement):
    """
    The percentage of assignments the Worker has abandoned (allowed the deadline to elapse), over all assignments the Worker has accepted. The value is an integer between 0 and 100.
    """

    def __init__(self, comparator, integer_value, required_to_preview=False):
        Requirement.__init__(self, qualification_type_id="00000000000000000070", comparator=comparator, integer_value=integer_value, required_to_preview=required_to_preview)

class PercentAssignmentsReturnedRequirement(Requirement):
    """
    The percentage of assignments the Worker has returned, over all assignments the Worker has accepted. The value is an integer between 0 and 100.
    """

    def __init__(self, comparator, integer_value, required_to_preview=False):
        Requirement.__init__(self, qualification_type_id="000000000000000000E0", comparator=comparator, integer_value=integer_value, required_to_preview=required_to_preview)

class PercentAssignmentsApprovedRequirement(Requirement):
    """
    The percentage of assignments the Worker has submitted that were subsequently approved by the Requester, over all assignments the Worker has submitted. The value is an integer between 0 and 100.
    """

    def __init__(self, comparator, integer_value, required_to_preview=False):
        Requirement.__init__(self, qualification_type_id="000000000000000000L0", comparator=comparator, integer_value=integer_value, required_to_preview=required_to_preview)

class PercentAssignmentsRejectedRequirement(Requirement):
    """
    The percentage of assignments the Worker has submitted that were subsequently rejected by the Requester, over all assignments the Worker has submitted. The value is an integer between 0 and 100.
    """

    def __init__(self, comparator, integer_value, required_to_preview=False):
        Requirement.__init__(self, qualification_type_id="000000000000000000S0", comparator=comparator, integer_value=integer_value, required_to_preview=required_to_preview)
