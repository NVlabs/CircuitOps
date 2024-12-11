# SPDX-FileCopyrightText: Copyright (c) 2022 NVIDIA CORPORATION & AFFILIATES. All rights reserved.

# SPDX-License-Identifier: Apache-2.0

#

# Licensed under the Apache License, Version 2.0 (the "License");

# you may not use this file except in compliance with the License.

# You may obtain a copy of the License at

#

# http://www.apache.org/licenses/LICENSE-2.0

#

# Unless required by applicable law or agreed to in writing, software

# distributed under the License is distributed on an "AS IS" BASIS,

# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

# See the License for the specific language governing permissions and

# limitations under the License.

'''
@file tee.py
@author algrebe@github, Zizheng Guo

Fixed buffer I/O bug discussed in https://github.com/algrebe/python-tee/issues/7
'''

import os
import sys
from abc import ABCMeta, abstractmethod

class Tee(object):
    """
    duplicates streams to a file.
    credits : http://stackoverflow.com/q/616645
    """

    def __init__(self, filename, mode="a", buff=-1, file_filters=None, stream_filters=None):
        """
        writes both to stream and to file.
        file_filters is a list of callables that processes a string just before being written
        to the file.
        stream_filters is a list of callables that processes a string just before being written
        to the stream.
        both stream & filefilters must return a string or None.
        """
        self.filename = filename
        self.mode = mode
        self.buff = buff
        self.file_filters = file_filters or []
        self.stream_filters = stream_filters or []

        self.stream = None
        self.fp = None

    @abstractmethod
    def set_stream(self, stream):
        """
        assigns "stream" to some global variable e.g. sys.stdout
        """
        pass

    @abstractmethod
    def get_stream(self):
        """
        returns the original stream e.g. sys.stdout
        """
        pass

    def write(self, message):
        stream_message = message
        for f in self.stream_filters:
            stream_message = f(stream_message)
            if stream_message is None:
                break

        file_message = message
        for f in self.file_filters:
            file_message = f(file_message)
            if file_message is None:
                break

        if stream_message is not None:
            self.stream.write(stream_message)

        if file_message is not None:
            self.fp.write(file_message)

    def flush(self):
        self.stream.flush()
        self.fp.flush()
        os.fsync(self.fp.fileno())

    def __enter__(self):
        self.stream = self.get_stream()
        self.fp = open(self.filename, self.mode, self.buff)
        self.set_stream(self)

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        if self.stream != None:
            self.set_stream(self.stream)
            self.stream = None

        if self.fp != None:
            self.fp.close()
            self.fp = None

    def isatty(self):
        return self.stream.isatty()

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.filename)

    __str__ = __repr__
    __unicode__ = __repr__

class StdoutTee(Tee):
    def set_stream(self, stream):
        sys.stdout = stream

    def get_stream(self):
        return sys.stdout

class StderrTee(Tee):
    def set_stream(self, stream):
        sys.stderr = stream

    def get_stream(self):
        return sys.stderr
