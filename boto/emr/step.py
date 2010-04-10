# Copyright (c) 2010 Spotify AB
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

class Step(object):
    """
    Jobflow Step base class
    """
    def jar(self):
        """
        :rtype: str
        :return: URI to the jar
        """
        raise NotImplemented()

    def args(self):
        """
        :rtype: list(str)
        :return: List of arguments for the step
        """
        raise NotImplemented()

    def main_class(self):
        """
        :rtype: str
        :return: The main class name
        """
        raise NotImplemented()


class JarStep(Step):
    """
    Custom jar step
    """
    def __init__(self, name, jar, main_class,
                 action_on_failure='TERMINATE_JOB_FLOW',
                 cache_files=None, cache_archives=None,
                 step_args=None, input=None, output=None):

        self.name = name
        self._jar = jar
        self._main_class = main_class
        self.action_on_failure = action_on_failure
        self.cache_files = cache_files
        self.cache_archives = cache_archives
        self.step_args = step_args
        self.input = input
        self.output = output

    def jar(self):
        return self._jar

    def args(self):
        args = []

        if self.input:
            args.append(self.input)
        if self.output:
            args.append(self.output)

        if self.cache_files:
            for cache_file in self.cache_files:
                args.extend(('-cacheFile', cache_file))

        if self.cache_archives:
            for cache_archive in self.cache_archives:
                args.extend(('-cacheArchive', cache_archive))

        if self.step_args:
            for step_arg in self.step_args:
                args.extend(step_arg)

        return args

    def main_class(self):
        return self._main_class


class StreamingStep(Step):
    """
    Hadoop streaming step
    """
    def __init__(self, name, mapper, reducer,
                 action_on_failure='TERMINATE_JOB_FLOW',
                 cache_files=None, cache_archives=None,
                 step_args=None, input=None, output=None):

        self.name = name
        self.mapper = mapper
        self.reducer = reducer
        self.action_on_failure = action_on_failure
        self.cache_files = cache_files
        self.cache_archives = cache_archives
        self.step_args = step_args
        self.input = input
        self.output = output

    def jar(self):
        return '/home/hadoop/contrib/streaming/hadoop-0.18-streaming.jar'

    def main_class(self):
        return None

    def args(self):
        args = ['-mapper', self.mapper,
                '-reducer', self.reducer]

        if self.input:
            if isinstance(self.input, list):
                for input in self.input:
                    args.extend(('-input', input))
            else:
                args.extend(('-input', self.input))
        if self.output:
            args.extend(('-output', self.output))

        if self.cache_files:
            for cache_file in self.cache_files:
                args.extend(('-cacheFile', cache_file))

        if self.cache_archives:
           for cache_archive in self.cache_archives:
                args.extend(('-cacheArchive', cache_archive))

        if self.step_args:
            for step_arg in self.step_args:
                args.extend(step_arg)

        return args

