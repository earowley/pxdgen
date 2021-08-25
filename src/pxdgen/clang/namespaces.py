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
from .enums import Enumeration
from .structs import Struct
from .typedefs import Typedef
from .functions import Function
from .atomic import Space, Member
from ..utils import TAB
from ..utils import TypeResolver


class Namespace(Space):
    FUNCTION_TYPES = (
        clang.cindex.CursorKind.FUNCTION_DECL, clang.cindex.CursorKind.FUNCTION_TEMPLATE
    )

    def __init__(self, cursors: list, recursive: bool, cpp_name: str,
                 header_name: str, valid_headers: set, *args, package_path: str = ''):
        super().__init__(cursors, recursive, cpp_name, header_name, valid_headers)
        self.package_path = package_path
        self._types = set()

    def generate_declarations(self, resolver: TypeResolver) -> Generator[str, None, None]:
        """
        A generator for the lines of a C header file or a C++
        namespace in Cython pxd format. Iterates over enums,
        structs/classes, typedefs, functions, and variables.

        Structs/Classes only include instance members. Static
        members of C++ classes are included in their own
        namespace declaration.
        """
        unk = list()

        for child in self.children:
            if child.kind == clang.cindex.CursorKind.ENUM_DECL:
                if not child.spelling:
                    unk.append(child)
                    continue
                for i in Namespace._gen_struct_enum(child, Enumeration, False):
                    yield i
            elif child.kind in Space.SPACE_KINDS:
                if not child.spelling:
                    unk.append(child)
                    continue
                ctypes = Struct(child).ctypes
                for i in Namespace._gen_struct_enum(child, Struct, False):
                    yield self._replace_typenames(i, ctypes, resolver)
            elif child.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
                typedef = Typedef(child)
                base = typedef.base

                if base in unk:
                    if base.kind == clang.cindex.CursorKind.ENUM_DECL:
                        for i in Namespace._gen_struct_enum(base, Enumeration, True, name=child.spelling):
                            yield i
                    else:
                        ctypes = Struct(base).ctypes
                        for i in Namespace._gen_struct_enum(base, Struct, True, name=child.spelling):
                            yield self._replace_typenames(i, ctypes, resolver)
                    unk.remove(base)
                    continue
                ctypes = typedef.ctypes
                yield self._replace_typenames(typedef.declaration, ctypes, resolver)
            elif child.kind in Namespace.FUNCTION_TYPES:
                func = Function(child)
                ctypes = func.ctypes
                yield self._replace_typenames(func.declaration, ctypes, resolver)
            elif child.kind == clang.cindex.CursorKind.VAR_DECL:
                mem = Member(child)
                ctypes = mem.ctypes
                yield self._replace_typenames(mem.declaration, ctypes, resolver)

    @staticmethod
    def _gen_struct_enum(child: clang.cindex.Cursor, datatype, typedef: bool, *args,
                        name: str = '') -> Generator[str, None, None]:
        """
        Yields the types of a struct or enumeration
        """
        obj = datatype(child, name=name)

        yield obj.cython_header(typedef)

        for m in obj.members():
            yield TAB + m

    def _replace_typenames(self, line: str, names: list, resolver: TypeResolver) -> str:
        """
        Replace the typenames that need to be replaced in the input string,
        based on what is defined in the TypeResolver
        """
        ret = line
        replacements = resolver.add_imports_from_types(names, self.cpp_name, self.package_path)

        for old, new in replacements:
            ret = ret.replace(old, new)

        return ret

    def _cpp_qual_name(self, name: str) -> str:
        """
        C++ qualified path of a type declaration such that:
        Decl -> Current::Namespace::Decl
        """
        if not self.cpp_name:
            return name
        return "::".join((self.cpp_name, name))

    def process_types(self, resolver: TypeResolver):
        """
        Returns a list of all types in
        """
        unk = list()

        for child in self.children:
            if child.kind == clang.cindex.CursorKind.ENUM_DECL:
                if not child.spelling:
                    unk.append(child)
                    continue
                resolver.add_user_defined_type(self._cpp_qual_name(child.spelling), self.package_path)
            elif child.kind in Space.SPACE_KINDS:
                if not child.spelling:
                    unk.append(child)
                    continue
                resolver.add_user_defined_type(self._cpp_qual_name(child.spelling), self.package_path)
                for t in Struct(child).ctypes:
                    resolver.process_type(t, self.cpp_name)
            elif child.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
                typedef = Typedef(child)
                base = typedef.base
                resolver.add_user_defined_type(self._cpp_qual_name(child.spelling), self.package_path)

                for t in typedef.ctypes:
                    resolver.process_type(t, self.cpp_name)

                if base in unk:
                    unk.remove(base)
                    if not base.kind == clang.cindex.CursorKind.ENUM_DECL:
                        for t in Struct(base).ctypes:
                            resolver.process_type(t, self.cpp_name)
            elif child.kind in Namespace.FUNCTION_TYPES:
                for t in Function(child).ctypes:
                    resolver.process_type(t, self.cpp_name)
            elif child.kind == clang.cindex.CursorKind.VAR_DECL:
                for t in Member(child).ctypes:
                    resolver.process_type(t, self.cpp_name)
