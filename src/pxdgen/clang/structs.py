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

import clang.cindex
from typing import Generator
from .atomic import Member
from .typedefs import Typedef
from .functions import Function, Constructor
from .. import utils
from ..utils import warning


class Struct:
    # Types yielded from members property
    INSTANCE_TYPES = (
        clang.cindex.CursorKind.FIELD_DECL,
        clang.cindex.CursorKind.CONSTRUCTOR,
        clang.cindex.CursorKind.CXX_METHOD,
        clang.cindex.CursorKind.FUNCTION_TEMPLATE,
        clang.cindex.CursorKind.TYPEDEF_DECL,
    )

    # Just for checking valid types
    # Includes instance types as well as static types
    VALID_KINDS = (
        INSTANCE_TYPES + (
             clang.cindex.CursorKind.TEMPLATE_TYPE_PARAMETER,
             clang.cindex.CursorKind.TEMPLATE_NON_TYPE_PARAMETER,
             clang.cindex.CursorKind.STRUCT_DECL,
             clang.cindex.CursorKind.ENUM_DECL,
             clang.cindex.CursorKind.VAR_DECL,
             clang.cindex.CursorKind.CLASS_DECL,
             clang.cindex.CursorKind.CLASS_TEMPLATE
        )
    )

    def __init__(self, cursor: clang.cindex.Cursor, *_,
                 name: str = ''):
        """
        Represents a Cython struct/cppclass, given the correct
        Clang Cursor.

        @param cursor: Clang struct/cppclass Cursor.
        @param name: Name override in the case that spelling is empty.
        """
        self.cursor = cursor
        self.name = name or self.cursor.spelling

    @property
    def is_cppclass(self) -> bool:
        """
        Whether this is a C++ class or POD C struct.

        @return: Boolean.
        """
        return utils.is_cppclass(self.cursor)

    @property
    def is_forward_decl(self) -> bool:
        """
        Whether this class is a forward declaration.

        @return: Boolean.
        """
        children = [c for c in self.cursor.get_children() if c.kind in Struct.VALID_KINDS]
        return self.cursor.get_definition() is None or len(children) == 0

    @property
    def ctypes(self) -> list:
        """
        A list of sanitized type strings for this struct.

        @return: List.
        """
        ret = list()
        template_params = utils.get_template_params_as_list(self.cursor)

        for child in self.cursor.get_children():
            if child.access_specifier == clang.cindex.AccessSpecifier.PRIVATE:
                continue
            if child.kind in Struct.INSTANCE_TYPES:
                if child.kind == clang.cindex.CursorKind.FIELD_DECL:
                    ret += Member(child).ctypes
                elif child.kind in (clang.cindex.CursorKind.CXX_METHOD, clang.cindex.CursorKind.FUNCTION_TEMPLATE):
                    ret += Function(child).ctypes
                elif child.kind == clang.cindex.CursorKind.CONSTRUCTOR:
                    ret += Constructor(child).ctypes
                elif child.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
                    ret += Typedef(child).ctypes

        if template_params:
            return list(filter(lambda p: p not in template_params, ret))

        return ret

    def cython_header(self, typedef: bool) -> str:
        """
        The Cython header for this struct/class.

        @param typedef: Whether this should be printed as a typedef.
        @return: str.
        """
        return "%s%s %s%s:" % (
            "ctypedef " if typedef and not self.is_cppclass else '',
            "cppclass" if self.is_cppclass else "struct",
            self.name,
            utils.get_template_params(self.cursor)
        )

    def members(self) -> Generator[str, None, None]:
        """
        Iterates over the Cython member declarations of this struct/class.

        @return: Generator[str].
        """
        gen = 0
        for child in self.cursor.get_children():
            if child.kind in Struct.INSTANCE_TYPES:
                if child.access_specifier == clang.cindex.AccessSpecifier.PRIVATE:
                    continue
                if child.is_static_method():
                    #  Handle static methods on instance side - Cython allows
                    yield "@staticmethod"
                gen += 1
                yield self._instance_member_repr(child)
            elif child.kind not in Struct.VALID_KINDS:
                warning.warn_unsupported(self.cursor, child.kind)

        if not gen:
            yield "pass"

    def _instance_member_repr(self, child: clang.cindex.Cursor):
        """
        Handles the representation of each supported type
        within struct declaration.
        """
        if child.kind == clang.cindex.CursorKind.FIELD_DECL:
            return Member(child).declaration
        elif child.kind == clang.cindex.CursorKind.CXX_METHOD:
            return Function(child).declaration
        elif child.kind == clang.cindex.CursorKind.FUNCTION_TEMPLATE:
            # Constructors with template params come in as this type
            if child.result_type.spelling == "void":
                func_name = child.spelling
                try:
                    func_name = func_name[:func_name.index("<")].strip()
                except ValueError:
                    pass
                if func_name == self.cursor.spelling:
                    return Constructor(child).declaration
            return Function(child).declaration
        elif child.kind == clang.cindex.CursorKind.CONSTRUCTOR:
            return Constructor(child).declaration
        elif child.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
            return Typedef(child).declaration
