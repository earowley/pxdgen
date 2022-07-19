#    PxdGen - A C/C++ header conversion tool
#    Copyright (C) 2021  Eric Rowley

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.


# Extensions to the Clang bindings that do not exist in the current version
import clang.cindex
from ctypes import c_bool


CURSOR_EXTENSIONS = [
    # First three use bindings format, next three are for extending
    ("clang_Cursor_isInlineNamespace", [clang.cindex.Cursor], c_bool,
     True, clang.cindex.Cursor, "is_inline_namespace")
]


def load_extensions():
    for ex in CURSOR_EXTENSIONS:
        name, argtypes, restype, extend, etype, method = ex
        c_func = getattr(clang.cindex.conf.lib, name)
        c_func.argtypes = argtypes
        c_func.restype = restype

        # Optionally extend a type
        if extend:
            setattr(etype, method, lambda self, *args: c_func(self, *args))
