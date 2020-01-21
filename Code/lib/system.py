#!/usr/local/autopkg/python
#
# Copyright 2010 Per Oloffson
# Reorganized 2019 by Nick McSpadden
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""System-related AutoPkg functions."""


import platform


class memoize(dict):
    """Class to cache the return values of an expensive function.
    This version supports only functions with non-keyword arguments"""

    def __init__(self, func):
        self.func = func

    def __call__(self, *args):
        return self[args]

    def __missing__(self, key):
        result = self[key] = self.func(*key)
        return result


# @memoize
def is_mac():
    """Return True if current OS is macOS."""
    return "Darwin" in platform.platform()


# @memoize
def is_windows():
    """Return True if current OS is Windows."""
    return "Windows" in platform.platform()


# @memoize
def is_linux():
    """Return True if current OS is Linux."""
    return "Linux" in platform.platform()
