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
import json
import os
import plistlib
from copy import deepcopy
from typing import Optional

import appdirs

from .common import APP_NAME, BUNDLE_ID, VarDict, is_mac, log_err

try:
    from CoreFoundation import (
        CFPreferencesAppSynchronize,
        CFPreferencesCopyAppValue,
        CFPreferencesCopyKeyList,
        CFPreferencesSetAppValue,
        kCFPreferencesAnyHost,
        kCFPreferencesAnyUser,
        kCFPreferencesCurrentHost,
        kCFPreferencesCurrentUser,
    )
    from Foundation import NSArray, NSDictionary, NSNumber
except ImportError:
    if is_mac():
        print(
            "ERROR: Failed 'from Foundation import NSArray, NSDictionary' in "
            + __name__
        )
        print(
            "ERROR: Failed 'from CoreFoundation import "
            "CFPreferencesAppSynchronize, ...' in " + __name__
        )
        raise
    # On non-macOS platforms, the above imported names are stubbed out.
    NSArray = list
    NSDictionary = dict
    NSNumber = int

    def CFPreferencesAppSynchronize(*args, **kwargs):
        pass

    def CFPreferencesCopyAppValue(*args, **kwargs):
        pass

    def CFPreferencesCopyKeyList(*args, **kwargs):
        return []

    def CFPreferencesSetAppValue(*args, **kwargs):
        pass

    kCFPreferencesAnyHost = None
    kCFPreferencesAnyUser = None
    kCFPreferencesCurrentUser = None
    kCFPreferencesCurrentHost = None


class PreferenceError(Exception):
    """Preference exception"""

    pass


class Preferences:
    """An abstraction to hold all preferences."""

    def __init__(self):
        """Init."""
        self.prefs: VarDict = {}
        # What type of preferences input are we using?
        self.type: Optional[str] = None
        # Path to the preferences file we were given
        self.file_path: Optional[str] = None
        # If we're on macOS, read in the preference domain first.
        # What we should do:
        # 1. On macOS, if we did not get passed --prefs, use domain as normal
        # 2. For everyone else, prefs path will be nil if not passed in, so create
        # a default prefs file and save two empty keys to it
        if is_mac():
            self.prefs = self._get_macos_prefs()
        else:
            self.prefs = self._get_file_prefs()
            # On Windows, if the file prefs don't exist, create a blank one
            if not self.prefs:
                log_err("WARNING: No prefs file found, creating one.")
                self.file_path = self.default_prefs_path()
                os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
                self.prefs = {"RECIPE_SEARCH_DIRS": [], "CACHE_DIR": "stuff"}
                self._write_json_file()

    def _parse_json_or_plist_file(self, file_path):
        """Parse the file. Start with plist, then JSON."""
        try:
            with open(file_path, "rb") as f:
                data = plistlib.load(f)
            self.type = "plist"
            self.file_path = file_path
            return data
        except Exception:
            pass
        try:
            with open(file_path, "rb") as f:
                data = json.load(f)
                self.type = "json"
                self.file_path = file_path
                return data
        except Exception:
            pass
        return {}

    def __deepconvert_objc(self, object):
        """Convert all contents of an ObjC object to Python primitives."""
        value = object
        if isinstance(object, NSNumber):
            value = int(object)
        elif isinstance(object, NSArray) or isinstance(object, list):
            value = [self.__deepconvert_objc(x) for x in object]
        elif isinstance(object, NSDictionary):
            value = dict(object)
            # RECIPE_REPOS is a dict of dicts
            for k, v in value.items():
                if isinstance(v, NSDictionary):
                    value[k] = dict(v)
        else:
            return object
        return value

    def _get_macos_pref(self, key):
        """Get a specific macOS preference key."""
        value = self.__deepconvert_objc(CFPreferencesCopyAppValue(key, BUNDLE_ID))
        return value

    def _get_macos_prefs(self):
        """Return a dict (or an empty dict) with the contents of all
        preferences in the domain."""
        prefs = {}

        # get keys stored via 'defaults write [domain]'
        user_keylist = CFPreferencesCopyKeyList(
            BUNDLE_ID, kCFPreferencesCurrentUser, kCFPreferencesAnyHost
        )

        # get keys stored via 'defaults write /Library/Preferences/[domain]'
        system_keylist = CFPreferencesCopyKeyList(
            BUNDLE_ID, kCFPreferencesAnyUser, kCFPreferencesCurrentHost
        )

        # CFPreferencesCopyAppValue() in get_macos_pref() will handle returning the
        # appropriate value using the search order, so merging prefs in order
        # here isn't necessary
        for keylist in [system_keylist, user_keylist]:
            if keylist:
                for key in keylist:
                    prefs[key] = self._get_macos_pref(key)
        return prefs

    def default_prefs_path(self, plist=False):
        """Return a path to the default preferences file location. JSON by default."""
        config_dir = appdirs.user_config_dir(APP_NAME, appauthor=False)
        ext = "json"
        if plist:
            ext = "plist"
        return os.path.join(config_dir, f"config.{ext}")

    def _get_file_prefs(self):
        r"""Lookup preferences for Windows in a standardized path, such as:
        * `C:\\Users\username\AppData\Local\Autopkg\config.{plist,json}`
        * `/home/username/.config/Autopkg/config.{plist,json}`
        Tries to find `config.plist`, then `config.json`."""

        # Try a plist config, then a json config.
        for plist_value in [True, False]:
            data = self._parse_json_or_plist_file(
                self.default_prefs_path(plist=plist_value)
            )
            if data:
                return data
        return {}

    def _set_macos_pref(self, key, value):
        """Sets a preference for domain"""
        try:
            CFPreferencesSetAppValue(key, value, BUNDLE_ID)
            if not CFPreferencesAppSynchronize(BUNDLE_ID):
                raise PreferenceError(f"Could not synchronize preference {key}")
        except Exception as err:
            raise PreferenceError(f"Could not set {key} preference: {err}")

    def read_file(self, file_path):
        """Read in a file and add the key/value pairs into preferences."""
        # Determine type or file: plist or json
        data = self._parse_json_or_plist_file(file_path)
        for k in data:
            self.prefs[k] = data[k]

    def _write_json_file(self):
        """Write out the prefs into JSON."""
        try:
            assert self.file_path is not None
            with open(self.file_path, "w") as f:
                json.dump(
                    self.prefs,
                    f,
                    skipkeys=True,
                    ensure_ascii=True,
                    indent=2,
                    sort_keys=True,
                )
        except Exception as e:
            log_err(f"Unable to write out JSON: {e}")

    def _write_plist_file(self):
        """Write out the prefs into a Plist."""
        try:
            assert self.file_path is not None
            with open(self.file_path, "wb") as f:
                plistlib.dump(self.prefs, f)
        except Exception as e:
            log_err(f"Unable to write out plist: {e}")

    def write_file(self):
        """Write preferences back out to file."""
        if not self.file_path:
            # Nothing to do if we weren't given a file
            return
        if self.type == "json":
            self._write_json_file()
        elif self.type == "plist":
            self._write_plist_file()

    def get_pref(self, key):
        """Retrieve a preference value."""
        return deepcopy(self.prefs.get(key))

    def get_all_prefs(self):
        """Retrieve a dict of all preferences."""
        return self.prefs

    def set_pref(self, key, value):
        """Set a preference value."""
        self.prefs[key] = value
        # On macOS, write it back to preferences domain if we didn't use a file
        if is_mac() and self.type is None:
            self._set_macos_pref(key, value)
        elif self.file_path is not None:
            self.write_file()
        else:
            log_err(f"WARNING: Preference change {key}=''{value}'' was not saved.")
