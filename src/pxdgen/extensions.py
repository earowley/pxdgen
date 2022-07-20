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


C = clang.cindex.conf.lib


def is_inline_namespace(self) -> bool:
    return C.clang_Cursor_isInlineNamespace(self)


def is_macro_function(self) -> bool:
    return C.clang_Cursor_isMacroFunctionLike(self)


def load_extensions():
    f = C.clang_Cursor_isInlineNamespace
    f.argtypes = [clang.cindex.Cursor]
    f.restype = c_bool
    setattr(clang.cindex.Cursor, "is_inline_namespace", is_inline_namespace)

    f = C.clang_Cursor_isMacroFunctionLike
    f.argtypes = [clang.cindex.Cursor]
    f.restype = c_bool
    setattr(clang.cindex.Cursor, "is_macro_function", is_macro_function)
