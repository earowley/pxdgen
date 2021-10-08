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
import os
from typing import Generator
from .enums import Enumeration
from .structs import Struct
from .typedefs import Typedef
from .functions import Function
from .atomic import Member
from .unions import Union
from ..constants import TAB
from collections import defaultdict
from ..utils import TypeResolver, is_cppclass, warning


class Namespace:
    # Used to determine which types are output/processed as functions
    # Functions have their return type and argument types resolved
    FUNCTION_TYPES = (
        clang.cindex.CursorKind.FUNCTION_DECL, clang.cindex.CursorKind.FUNCTION_TEMPLATE
    )

    # Determines what gets yielded as a struct or cppclass within this namespace
    # C++ classes also resolve to namespaces, but they are resolved in utils.find_namespaces
    CLASS_TYPES = (clang.cindex.CursorKind.STRUCT_DECL, clang.cindex.CursorKind.CLASS_DECL,
                   clang.cindex.CursorKind.CLASS_TEMPLATE
    )

    # C++ classes are also processed as namespaces.
    # These are cursors that will be encountered while processing,
    # but should not emit warnings as they will not be ignored
    # when the struct/cppclass is being emitted.
    STATIC_IGNORED_TYPES = (
        clang.cindex.CursorKind.NAMESPACE, clang.cindex.CursorKind.CXX_METHOD,
        clang.cindex.CursorKind.FIELD_DECL, clang.cindex.CursorKind.CONSTRUCTOR,
        clang.cindex.CursorKind.TEMPLATE_TYPE_PARAMETER,
        clang.cindex.CursorKind.TEMPLATE_NON_TYPE_PARAMETER,
        clang.cindex.CursorKind.TEMPLATE_TEMPLATE_PARAMETER
    )

    # All valid types. Convenient for fast warning determination
    VALID_TYPES = (clang.cindex.CursorKind.ENUM_DECL,
                   clang.cindex.CursorKind.TYPEDEF_DECL,
                   clang.cindex.CursorKind.VAR_DECL,
                   clang.cindex.CursorKind.UNION_DECL
    ) + FUNCTION_TYPES + CLASS_TYPES + STATIC_IGNORED_TYPES

    def __init__(self, cursors: list, recursive: bool, cpp_name: str,
                 header_name: str, valid_headers: set, *_):
        """
        Represents a Cython namespace declaration, given the following parameters.

        @param cursors: A list of cursors associated with this namespace.
        @param recursive: Whether this namespace should declare children from other headers, recursively.
        @param cpp_name: Full C++ path to Namespace/Class, such as Foo::Bar::Baz.
        @param header_name: The header where this namespace was declared.
        @param valid_headers: A set of valid headers from which children can be declared.
                              useful for trimming if recursive is True.
        @param package_path: The Cython package path for resolver purposes, such as Foo.Bar;
                             calculated by caller.
        """
        self.cursors = cursors
        self.cpp_name = cpp_name
        self.recursive = recursive
        self.header_name = header_name
        self.valid_headers = valid_headers
        self.children = list()
        self.class_space = all(is_cppclass(c) for c in cursors)
        self.decls = defaultdict(lambda: [])

        for cursor in cursors:
            self.children += list(filter(self._child_filter, cursor.get_children()))

        i = 0
        while i < len(self.children):
            child = self.children[i]
            if child.kind not in Namespace.VALID_TYPES:
                warning.warn_unsupported(self.cursors[0], child.kind)
                self.children.pop(i)
                continue
            i += 1

    @staticmethod
    def _gen_struct_enum(child: clang.cindex.Cursor, datatype, typedef: bool, *_,
                         name: str = '') -> Generator[str, None, None]:
        """
        Yields the types of a struct or enumeration
        """
        obj = datatype(child, name=name)

        yield obj.cython_header(typedef)

        for m in obj.members():
            yield TAB + m

    @property
    def has_declarations(self) -> bool:
        """
        Whether this space has any valid declarations.

        @return: Boolean.
        """
        return len(self.children) > 0

    @property
    def cython_namespace_header(self) -> str:
        """
        The Cython header for this namespace.

        @return: str.
        """
        base = "cdef extern from \"%s\"" % self.header_name
        namespace = (" namespace \"%s\":" % self.cpp_name) if self.cpp_name else ':'

        return base + namespace

    def process_types(self, resolver: TypeResolver):
        """
        Performs a full pass of this namespace and updates the resolver
        according to the found types.

        @param resolver: The TypeResolver to update.
        @return:
        """
        unk = list()

        for child in self.children:
            if child.kind == clang.cindex.CursorKind.ENUM_DECL:
                if not child.spelling:
                    unk.append(child)
                    continue
                resolver.add_user_defined_type(self._cpp_qual_name(child.spelling))
            elif child.kind in Namespace.CLASS_TYPES:
                if not child.spelling:
                    unk.append(child)
                    continue
                cppn = self._cpp_qual_name(child.spelling)
                resolver.add_user_defined_type(cppn)
            elif child.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
                typedef = Typedef(child)
                base = typedef.base
                resolver.add_user_defined_type(self._cpp_qual_name(child.spelling))
                if base and base in unk:
                    unk.remove(base)
            elif child.kind == clang.cindex.CursorKind.UNION_DECL:
                if not child.spelling:
                    unk.append(child)
                    continue
                resolver.add_user_defined_type(self._cpp_qual_name(child.spelling))

    def generate_declarations(self, resolver: TypeResolver) -> Generator[str, None, None]:
        """
        Performs a full pass of this namespace and yields the declarations inside.

        @param resolver: TypeResolver for resolving names.
        @return: Generator of Cython declarations for this namespace.
        """
        unk = list()

        for child in self.children:
            if child.kind == clang.cindex.CursorKind.ENUM_DECL:
                if not child.spelling:
                    unk.append(child)
                    continue
                for i in Namespace._gen_struct_enum(child, Enumeration, False):
                    yield i
            elif child.kind in Namespace.CLASS_TYPES:
                if not child.spelling:
                    unk.append(child)
                    continue
                s = Struct(child)
                self.decls[child.spelling].append(s)
                if s.is_forward_decl:
                    continue
                ctypes = s.ctypes
                for t in ctypes:
                    resolver.process_type(t, self.cpp_name)
                struct_iter = Namespace._gen_struct_enum(child, Struct, False)
                yield next(struct_iter)
                for i in struct_iter:
                    yield self._replace_typenames(i, ctypes, resolver)
            elif child.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
                typedef = Typedef(child)
                base = typedef.base
                for t in typedef.ctypes:
                    resolver.process_type(t, self.cpp_name)
                if base and base in unk:
                    if base.kind == clang.cindex.CursorKind.ENUM_DECL:
                        for i in Namespace._gen_struct_enum(base, Enumeration, True, name=child.spelling):
                            yield i
                    elif base.kind == clang.cindex.CursorKind.UNION_DECL:
                        ctypes = Union(base).ctypes
                        u_iter = Namespace._gen_struct_enum(base, Union, True, name=child.spelling)
                        for t in ctypes:
                            resolver.process_type(t, self.cpp_name)
                        yield next(u_iter)
                        for i in u_iter:
                            yield self._replace_typenames(i, ctypes, resolver)
                    else:
                        ctypes = Struct(base).ctypes
                        struct_iter = Namespace._gen_struct_enum(base, Struct, True, name=child.spelling)
                        for t in ctypes:
                            resolver.process_type(t, self.cpp_name)
                        yield next(struct_iter)
                        for i in struct_iter:
                            yield self._replace_typenames(i, ctypes, resolver)
                    unk.remove(base)
                    continue
                ctypes = typedef.ctypes
                yield self._replace_typenames(typedef.declaration, ctypes, resolver)
            elif child.kind in Namespace.FUNCTION_TYPES:
                func = Function(child)
                ctypes = func.ctypes
                for t in ctypes:
                    resolver.process_type(t, self.cpp_name)
                yield self._replace_typenames(func.declaration, ctypes, resolver)
            elif child.kind == clang.cindex.CursorKind.VAR_DECL:
                mem = Member(child)
                ctypes = mem.ctypes
                for t in ctypes:
                    resolver.process_type(t, self.cpp_name)
                yield self._replace_typenames(mem.declaration, ctypes, resolver)
            elif child.kind == clang.cindex.CursorKind.UNION_DECL:
                if not child.spelling:
                    unk.append(child)
                    continue
                u = Union(child)
                ctypes = u.ctypes
                u_iter = Namespace._gen_struct_enum(child, Union, False)
                for t in ctypes:
                    resolver.process_type(t, self.cpp_name)
                yield next(u_iter)
                for i in u_iter:
                    yield self._replace_typenames(i, ctypes, resolver)

        for decl_list in self.decls.values():
            if len(decl_list) == 1 and decl_list[0].is_forward_decl:
                for v in Namespace._gen_struct_enum(decl_list[0], Struct, False):
                    yield v

    def _replace_typenames(self, line: str, names: list, resolver: TypeResolver) -> str:
        """
        Replace the typenames that need to be replaced in the input string,
        based on what is defined in the TypeResolver
        """
        ret = line
        replacements = resolver.add_imports_from_types(names, self.cpp_name)

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

    def _child_filter(self, child: clang.cindex.Cursor):
        """
        Filters the child cursors of this namespace based on
        recursive command line options and C++ class specifications
        where some children may belong to the instance space.
        """
        # Types which are usually printed with the namespace,
        # but in the case of C++ classes they are printed with
        # the instance instead.
        PREFER_INSTANCE = (
            clang.cindex.CursorKind.FUNCTION_TEMPLATE,
        )
        # Prefer typedefs to be in instance defs, rather than namespace defs
        if self.class_space and (
            child.kind in PREFER_INSTANCE or
            child.access_specifier == clang.cindex.AccessSpecifier.PRIVATE
        ):
            return False
        # if child.kind in Namespace.CLASS_TYPES and Struct(child).is_forward_decl and not get_config(Setting.FORWARD_DECL):
        #    return False
        try:
            return (
                    child.kind not in Namespace.STATIC_IGNORED_TYPES and
                    (
                        self.recursive or
                        os.path.basename(child.location.file.name) in self.valid_headers
                    )
                   )
        except AttributeError:
            warning.warn("AttributeError in namespace %s, header %s, cursor %s" % (self.cpp_name, self.header_name, child.kind))
            return False
