# -*- coding: utf-8 -*-
# Stalker a Production Asset Management System
# Copyright (C) 2009-2013 Erkan Ozgur Yilmaz
# 
# This file is part of Stalker.
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA

# Code is coming from SQLAlchemy examples
"""local_session_caching.py

Create a new Dogpile cache backend that will store
cached data local to the current Session.

This is an advanced example which assumes familiarity
with the basic operation of CachingQuery.

"""


from dogpile.cache.api import CacheBackend, NO_VALUE
from dogpile.cache.region import register_backend


class ScopedSessionBackend(CacheBackend):
    """A dogpile backend which will cache objects locally on
    the current session.

    When used with the query_cache system, the effect is that the objects
    in the cache are the same as that within the session - the merge()
    is a formality that doesn't actually create a second instance.
    This makes it safe to use for updates of data from an identity
    perspective (still not ideal for deletes though).

    When the session is removed, the cache is gone too, so the cache
    is automatically disposed upon session.remove().
    """

    def __init__(self, arguments):
        self.scoped_session = arguments['scoped_session']

    def get(self, key):
        return self._cache_dictionary.get(key, NO_VALUE)

    def set(self, key, value):
        self._cache_dictionary[key] = value

    def delete(self, key):
        self._cache_dictionary.pop(key, None)

    @property
    def _cache_dictionary(self):
        """Return the cache dictionary linked to the current Session."""

        sess = self.scoped_session()
        try:
            cache_dict = sess._cache_dictionary
        except AttributeError:
            sess._cache_dictionary = cache_dict = {}
        return cache_dict


register_backend("sqlalchemy.session", __name__, "ScopedSessionBackend")
