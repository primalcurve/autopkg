#!/usr/local/autopkg/python
#
# Copyright 2020 Nick McSpadden
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

"""Shared common functions. Nothing in here may depend on other autopkg modules."""

import platform
import sys
from typing import IO, Any, Dict, Union

# Type for methods that accept either a filesystem path or a file-like object.
FileOrPath = Union[IO, str, bytes, int]

# Type for ubiquitus dictionary type used throughout autopkg.
# Most commonly for `input_variables` and friends. It also applies to virtually all
# usages of plistlib results as well.
VarDict = Dict[str, Any]


def is_mac():
    """Return True if current OS is macOS."""
    return "Darwin" in platform.platform()


def is_windows():
    """Return True if current OS is Windows."""
    return "Windows" in platform.platform()


def is_linux():
    """Return True if current OS is Linux."""
    return "Linux" in platform.platform()


def log(msg, error=False):
    """Message logger, prints to stdout/stderr."""
    if error:
        print(msg, file=sys.stderr)
    else:
        print(msg)


def log_err(msg):
    """Message logger for errors."""
    log(msg, error=True)
