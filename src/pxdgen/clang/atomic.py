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
import os.path
from .. import utils


# Represents a space containing names: Namespace & C++ class
class Space:
    # Kinds declared from a static standpoint
    # There is an exception for typedefs when
    # this space represents a C++ class
    DECL_KINDS = (clang.cindex.CursorKind.ENUM_DECL, clang.cindex.CursorKind.FUNCTION_DECL,
                  clang.cindex.CursorKind.TYPEDEF_DECL, clang.cindex.CursorKind.FUNCTION_TEMPLATE,
                  clang.cindex.CursorKind.VAR_DECL
    )

    # Subspace kinds
    # Namespace not here because they are represented at highest declaration scope,
    # not within other namespaces
    SPACE_KINDS = (clang.cindex.CursorKind.STRUCT_DECL, clang.cindex.CursorKind.CLASS_DECL,
                   clang.cindex.CursorKind.CLASS_TEMPLATE
    )

    # Ignored from a non-instance perspective. Instance members are handled
    # in structs.py/namespaces.py
    # These are excluded from warnings, and also excluded from output yield
    # of this space.
    IGNORED_KINDS = (
        clang.cindex.CursorKind.NAMESPACE, clang.cindex.CursorKind.CXX_METHOD,
        clang.cindex.CursorKind.FIELD_DECL, clang.cindex.CursorKind.CONSTRUCTOR,
        clang.cindex.CursorKind.TEMPLATE_TYPE_PARAMETER,
        clang.cindex.CursorKind.TEMPLATE_NON_TYPE_PARAMETER,
        clang.cindex.CursorKind.TEMPLATE_TEMPLATE_PARAMETER
    )

    VALID_KINDS = DECL_KINDS + SPACE_KINDS + IGNORED_KINDS

    def __init__(self, cursors: list, recursive: bool, cpp_name: str,
                 header_name: str, valid_headers: set):
        self.cursors = cursors
        self.cpp_name = cpp_name
        self.recursive = recursive
        self.header_name = header_name
        self.valid_headers = valid_headers
        self.children = list()
        self.class_space = all(c.kind in Space.SPACE_KINDS for c in cursors)

        for cursor in cursors:
            self.children += list(filter(self.child_filter, cursor.get_children()))

        i = 0
        while i < len(self.children):
            child = self.children[i]
            if child.kind not in Space.VALID_KINDS:
                utils.warn_unsupported(self.cursors[0], child.kind)
                self.children.pop(i)
                continue
            i += 1

    @property
    def has_declarations(self) -> bool:
        """
        Returns whether this static space has declarations.
        This may be false while the instance space (if C++)
        has declarations.
        """
        return len(self.children) > 0

    @property
    def cython_namespace_header(self) -> str:
        """
        Returns the Cython header definition string
        for a pxd file.
        """
        base = "cdef extern from \"%s\"" % self.header_name
        namespace = (" namespace \"%s\":" % self.cpp_name) if self.cpp_name else ':'

        return base + namespace

    def child_filter(self, child: clang.cindex.Cursor):
        """
        Filters the child cursors of this space based on
        recursive command line options and C++ class specifications
        where some children may belong to the instance space.
        """
        # Prefer typedefs to be in instance defs, rather than namespace defs
        if self.class_space and child.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
            return False
        if self.class_space and child.kind == clang.cindex.CursorKind.FUNCTION_TEMPLATE:
            return False
        if self.class_space and child.access_specifier == clang.cindex.AccessSpecifier.PRIVATE:
            return False
        try:
            return child.kind not in Space.IGNORED_KINDS and (self.recursive or os.path.basename(child.location.file.name) in self.valid_headers)
        except AttributeError:
            utils.warn("AttributeError in namespace %s, header %s, cursor %s" % (self.cpp_name, self.header_name, child.kind))
            return False


# The Member class represents a variable declaration in a Space,
# or a field declaration in a struct/union
class Member:
    def __init__(self, cursor: clang.cindex.Cursor, *args):
        self.cursor = cursor

    @property
    def is_static(self) -> bool:
        """
        If this is a var declaration, is it in static space.
        """
        return self.cursor.storage_class == clang.cindex.StorageClass.STATIC

    @property
    def declaration(self) -> str:
        """
        Cython declaration string of this member.
        """

        if utils.is_function_pointer(self.cursor.type):
            return self.function_ptr_declaration

        # Clang refers to arrys in int[20] syntax
        # This block extracts the array size portion,
        # and is saved to suffix so that the end
        # result looks like int data[20]
        typename = utils.strip_beg_type_ids(self.cursor.type.spelling)
        suffix = ''
        ob = typename.find('[')

        if ob != -1:
            suffix = typename[ob:]
            typename = typename[:ob].strip()

        if typename.endswith('*'):
            typename = typename.replace(" *", '*')
        elif typename.endswith('&'):
            typename = typename.replace(" &", '&')

        ret = "%s %s%s" % (typename, self.cursor.spelling, suffix)

        return utils.convert_dialect(ret).strip()

    @property
    def function_ptr_declaration(self):
        typename = self.cursor.type.spelling
        ret = utils.strip_all_type_ids(typename.replace("(*)", "(*%s)" % self.cursor.spelling)).replace("(void)", "()")

        return utils.convert_dialect(ret).strip()

    @property
    def ctypes(self) -> list:
        """
        Types which appear in this member.
        """
        return Member.basic_member_ctypes(self.cursor.type)

    @staticmethod
    def basic_member_ctypes(t: clang.cindex.Type) -> list:
        """
        Base method for extracting types.
        """
        if utils.is_function_pointer(t):
            rtype = utils.get_function_pointer_return_type(t)
            atypes = utils.get_function_pointer_arg_types(t)

            return [utils.sanitize_type_string(ts) for ts in [rtype] + atypes]

        return [utils.sanitize_type_string(t.spelling)]

