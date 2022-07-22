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

from __future__ import annotations

import os
import clang.cindex
from . import utils
from .constants import *
from typing import Optional, Generator, Set, Any, Tuple, List


def specialize(cursor: clang.cindex.Cursor) -> CCursor:
    """
    Determine what abstracted class defined in this
    module to use for a specific cursor.

    @param cursor : A cursor to convert to a class from this module.
    @return       : The converted type.
    """
    if cursor.kind in BASIC_DATA_KINDS:
        return DataType(cursor)
    elif utils.is_constructor(cursor):
        return Constructor(cursor)
    elif cursor.kind in FUNCTION_KINDS:
        return Function(cursor)
    elif cursor.kind == clang.cindex.CursorKind.ENUM_DECL:
        return Enumeration(cursor)
    elif cursor.kind == clang.cindex.CursorKind.UNION_DECL:
        return Union(cursor)
    elif cursor.kind in TYPEDEF_KINDS:
        return Typedef(cursor)
    elif cursor.kind in STRUCTURED_DATA_KINDS:
        return Struct(cursor)
    elif cursor.kind == clang.cindex.CursorKind.MACRO_DEFINITION:
        return Macro(cursor)
    else:
        return CCursor(cursor)


def block(children: List[CCursor], name: str, header: str, restrict: bool) -> Generator[str, None, None]:
    """
    Iterate over the lines of a block type.

    @param children : The children of the block.
    @param name     : The name of the block. Used for naming anonymous types.
    @param header   : The header of the block to yield.
    @param restrict : A restricted space such as a C struct that must
                      have restricted declarations.
    @return         : Generator[str]
    """
    forward_decls = list()
    anonymous_decls = list()

    for child in children:
        if child.forward:
            forward_decls.append(child)
        elif child.anonymous:
            anonymous_decls.append(child)
        for assoc in CCursor._base_assoc_types(child.cursor):
            if assoc.forward:
                forward_decls.append(assoc)
            elif assoc.anonymous:
                anonymous_decls.append(assoc)

    forward_decls = list(set(forward_decls))
    anonymous_decls = list(set(anonymous_decls))
    prefix = '' if restrict else TAB

    if not restrict:
        yield header

    for i, cursor in enumerate(anonymous_decls):
        for line in cursor.lines(name=f"pxdgen_anon_{name}_{i}"):
            yield prefix + line
    for decl in forward_decls:
        for line in decl.lines():
            yield prefix + line

    if restrict:
        yield header

    typedefs = list()
    declared_typedefs = list()
    count = 0

    for child in children:
        if child.anonymous or child.forward:
            continue
        if child.cursor.kind in ANON_KINDS and not child.name:
            typedefs.append(child)
            continue
        count += 1
        if isinstance(child, DataType):
            ut, token = utils.get_underlying_type(child.cursor.type)
            decl = ut.get_declaration()

            try:
                ind = anonymous_decls.index(decl)
            except ValueError:
                ind = -1

            if ind != -1:
                i = token.find('[')

                if i != -1:
                    suffix = token[i:]
                    token = token[:i]
                else:
                    suffix = ''

                yield TAB + f"pxdgen_anon_{name}_{ind}{token} {child.name}{suffix}"
                continue
        elif isinstance(child, Typedef):
            ut, token = utils.get_underlying_type(child.cursor.underlying_typedef_type)
            utd = ut.get_declaration()

            try:
                ind = typedefs.index(utd)
            except ValueError:
                ind = -1

            if ind != -1:
                td = typedefs.pop(ind)

                for line in td.lines(name=child.name, typedef=True):
                    yield TAB + line

                declared_typedefs.append((td, child.name))
                continue

            found = False

            for decl, name in declared_typedefs:
                if decl == utd:
                    yield TAB + f"ctypedef {name}{token} {child.name}"
                    found = True
                    break

            if found:
                continue

        for i, line in enumerate(child.lines()):
            commented = line.strip().startswith('#')
            if restrict and isinstance(child, Function) and child.is_static_method:
                yield TAB + ("#  " if commented else '') + "@staticmethod"
            yield TAB + line

        if i == 0 and commented:
            count -= 1

    if not count:
        yield TAB + "pass"


class CCursor:
    def __init__(self, cursor: clang.cindex.Cursor):
        self.cursor = cursor
        self._address = "::".join((self.location, self.name)).strip("::")

    def __iter__(self):
        return self.cursor.get_children()

    def __eq__(self, other: Any):
        if isinstance(other, CCursor):
            return other.cursor == self.cursor
        if isinstance(other, clang.cindex.Cursor):
            return self.cursor == other
        raise NotImplementedError(f"CCursor not comparable to type {type(other)}")

    def __hash__(self) -> int:
        return self._address.__hash__()

    @property
    def is_space(self):
        return self.cursor.kind in SPACE_KINDS

    @property
    def is_functional(self):
        return self.cursor.kind in FUNCTION_KINDS

    @property
    def is_structured_data(self):
        return self.cursor.kind in STRUCTURED_DATA_KINDS

    @property
    def is_static(self) -> bool:
        """
        Whether the storage for this element is static.

        @return: Boolean.
        """
        return self.cursor.storage_class == clang.cindex.StorageClass.STATIC

    @property
    def parent(self) -> Optional[CCursor]:
        p = self.cursor.lexical_parent
        return None if p is None else specialize(p)

    @property
    def visible(self) -> bool:
        return self.cursor.access_specifier == clang.cindex.AccessSpecifier.PUBLIC

    @property
    def file(self) -> Optional[str]:
        try:
            return os.path.abspath(self.cursor.location.file.name)
        except AttributeError:
            return None

    @property
    def anonymous(self) -> bool:
        return utils.is_anonymous(self.cursor)

    @property
    def forward(self) -> bool:
        return utils.is_forward_decl(self.cursor)

    @property
    def name(self) -> str:
        return self.cursor.spelling

    @property
    def display(self) -> str:
        return self.cursor.displayname

    @property
    def namespace(self) -> str:
        return utils.get_cursor_namespace(self.cursor)

    @property
    def location(self) -> str:
        return utils.get_cursor_location(self.cursor)

    @property
    def address(self) -> str:
        return self._address

    @property
    def associated_types(self) -> Set[CCursor]:
        """
        Get the associated types within this cursor.

        Example:
        Case: std::vector<std::map<std::string, int>>
        Result: [vector, map, string] (clang.cindex.Cursors)
        Remarks: Int is not included as it is built-in.
        @return: List of cursors containing the definition of each type.
        """
        return CCursor._base_assoc_types(self.cursor)

    @property
    def unsupported(self) -> bool:
        """
        Whether this declaration uses a C++ construct
        unsupported by Cython.

        @return: bool.
        """
        unsupported_types = (clang.cindex.TypeKind.BLOCKPOINTER,)

        if self.cursor.type.kind in unsupported_types:
            return True

        for child in self.cursor.get_children():
            if child.kind in TYPE_REFS:
                d = child.get_definition() or child.type.get_declaration()

                if utils.is_alias_unsupported(d):
                    return True

        return utils.is_typename_unsupported(self.cursor.type)

    @staticmethod
    def _base_assoc_types(cursor: clang.cindex.Cursor) -> Set[CCursor]:
        result = set()

        for child in cursor.get_children():
            if child.kind in TYPE_REFS:
                cdef = child.get_definition()
                if cdef is not None:
                    result.add(specialize(cdef))
                else:
                    cdef = child.type.get_declaration()
                    if cdef.kind != clang.cindex.CursorKind.NO_DECL_FOUND:
                        result.add(specialize(cdef))

        return result

    def lines(self, **kwargs) -> Generator[str, None, None]:
        raise NotImplementedError(f"Abstract method `lines` called in CCursor abstract class with cursor {self.cursor.kind}:{self.cursor.spelling}")


class DataType(CCursor):
    def __init__(self, cursor: clang.cindex.Cursor):
        """
        Represents a simple variable or constant declaration,
        function parameter, struct/class/union field, etc.

        @param cursor: Associated Clang cursor.
        """
        super().__init__(cursor)

    @property
    def associated_types(self) -> Set[CCursor]:
        """
        Override from base class to support
        function pointers.
        """
        result = super().associated_types

        if self.is_function_pointer:
            for child in self.cursor.get_children():
                if child.kind == clang.cindex.CursorKind.PARM_DECL:
                    result.update(DataType(child).associated_types)

        return result

    @property
    def unsupported(self) -> bool:
        if self.is_function_pointer:
            for child in self.cursor.get_children():
                if child.kind == clang.cindex.CursorKind.PARM_DECL:
                    if DataType(child).unsupported:
                        return True

        return super().unsupported

    @property
    def is_function_pointer(self) -> bool:
        return utils.is_function_pointer(self.cursor.type)

    @property
    def declaration(self) -> str:
        """
        The declaration of this Member in Cython syntax.

        @return: Cython syntax str.
        """
        if self.unsupported:
            return f"#  {self.cursor.type.spelling} {self.name}"

        if self.is_function_pointer:
            return self._function_ptr_declaration

        ut, token = utils.get_underlying_type(self.cursor.type)
        utd = ut.get_declaration()

        # If the anonymous declaration has not already been handled, default
        if utils.is_anonymous(utd):
            # Pointer coersion is easier for void* than array of chars
            if token.count('*') == len(token):
                typename = f"void{token}"
            else:
                typename = f"char[{self.cursor.type.get_size()}]"
        else:
            typename = self.typename

        # Clang refers to arrys in int[20] syntax
        # This block extracts the array size portion,
        # and is saved to suffix so that the end
        # result looks like int data[20]
        suffix = ''
        ob = typename.find('[')

        if ob != -1:
            suffix = typename[ob:]
            typename = typename[:ob].strip()

        return f"{utils.convert_dialect(typename)} {self.name}{suffix}"

    @property
    def typename(self) -> str:
        return utils.full_type_repr(self.cursor.type, self.cursor)

    @property
    def _function_ptr_declaration(self) -> str:
        """
        Special declaration for function pointers.

        @return: str.
        """
        typename = self.typename
        i = typename.index(')')

        return utils.convert_dialect(typename[:i] + self.name + typename[i:])

    def lines(self, **kwargs) -> Generator[str, None, None]:
        """
        The lines of this DataType.

        @param kwargs: None.
        @return: Generator of lines.
        """
        yield self.declaration


class Macro(CCursor):
    def __init__(self, cursor):
        super().__init__(cursor)

    def lines(self, **kwargs) -> Generator[str, None, None]:
        macro_type = "const int"
        tokens = [t.spelling for t in self.cursor.get_tokens()]
        func = self.cursor.is_macro_function()
        i = 1 if not func else (tokens.index(')') + 1)
        macro_def = ''.join(tokens[i:])

        if re.fullmatch(RE_CPP_INT, macro_def):
            macro_type = "const long"
        elif re.fullmatch(RE_CPP_FLOAT, macro_def):
            macro_type = "const double"

        yield f"{macro_type} {tokens[0]}{'(...)' if func else ''}"


class Function(CCursor):
    CYTHON_UNSUPPORTED = {
        "operator+=",
        "operator-=",
        "operator^=",
        "operator&=",
        "operator|=",
        "operator->",
        # Python name collisions
        "is",
        "global",
    }

    def __init__(self, cursor: clang.cindex.Cursor):
        """
        Represents a functional type declaration.

        @param cursor: Clang cursor.
        """
        super().__init__(cursor)
        self._tmpl_params = utils.get_template_params(cursor)
        # get_arguments() yields nothing for function templates
        # testing cursor.kind manually for now to handle both cases
        self._args = [DataType(child) for child in cursor.get_children() if child.kind == clang.cindex.CursorKind.PARM_DECL]

    @property
    def is_static_method(self) -> bool:
        """
        Whether this function is a static method.

        @return: Boolean.
        """
        return self.cursor.is_static_method()

    @property
    def associated_types(self) -> Set[CCursor]:
        """
        Associated types for this function.

        @return: Set[CCursor]
        """
        result = super().associated_types

        for arg in self._args:
            result.update(arg.associated_types)

        return result

    @property
    def unsupported(self) -> bool:
        return (
            any(arg.unsupported for arg in self._args) or
            utils.is_typename_unsupported(self.cursor.result_type) or
            super().unsupported
        )

    @property
    def first_optional_arg_index(self) -> int:
        """
        Gets the first optional argument index for
        this function. Returns len(args) if there
        are no default parameters.

        @return: First optional argument index.
        """
        n = len(self._args)

        for i, arg in enumerate(self._args):
            if any(child.kind == clang.cindex.CursorKind.UNEXPOSED_EXPR for child in arg):
                n = i
                break

        return n

    def lines(self, **kwargs) -> Generator[str, None, None]:
        """
        Generates the lines for this function. Functions with
        default parameter values will yield multiple overloads.

        @param kwargs: No kwargs to specify.
        @return: Generator over lines.
        """
        comment = (
            self.unsupported or
            self.cursor.spelling in Function.CYTHON_UNSUPPORTED or
            self.cursor.spelling.startswith('operator""')
        )
        n = self.first_optional_arg_index
        restype = utils.convert_dialect(utils.full_type_repr(self.cursor.result_type, self.cursor))

        for i in range(n, len(self._args) + 1):
            args = self._argument_declarations(i)
            prefix = "#  " if comment else ''

            if utils.is_function_pointer(self.cursor.result_type):
                i = restype.index(')')
                yield f"{prefix}{restype[:i]}{self.name}{self._tmpl_params}({', '.join(args)}){restype[i:]}"
            else:
                yield f"{prefix}{restype} {self.name}{self._tmpl_params}({', '.join(args)})"

    def _argument_declarations(self, nargs: int) -> Generator[str, None, None]:
        """
        Returns whether there was an error and the Cython argument
        declarations of this function.
        """

        for mem in self._args[:nargs]:
            # `=*` syntax seems to only work for cdef functions defined in pyx files
            # suffix = "=*" if any(child.kind == clang.cindex.CursorKind.UNEXPOSED_EXPR for child in mem) else ''
            yield utils.convert_dialect(mem.typename)

        # Variadic argument does not get represented in children or get_arguments()
        # So utils function uses tokens
        if utils.is_function_variadic(self.cursor):
            yield "..."


class Constructor(Function):
    def __init__(self, cursor: clang.cindex.Cursor):
        super().__init__(cursor)

    def lines(self, **kwargs) -> Generator[str, None, None]:
        """
        Lines for this constructor.

        @param kwargs: None for this type.
        @return: Generator over lines.
        """
        spelling = self.name
        restype = "void " if self._tmpl_params else ''
        n = self.first_optional_arg_index

        try:
            spelling = spelling[:spelling.index('<')]
        except ValueError:
            pass

        for i in range(n, len(self._args) + 1):
            args = self._argument_declarations(i)

            yield ("#  " if self.unsupported else '') + f"{restype}{spelling}{self._tmpl_params}({', '.join(args)})"


class Enumeration(CCursor):
    def __init__(self, cursor: clang.cindex.Cursor):
        """
        Represents an enum, given an enum Cursor.

        @param cursor: Clang cursor.
        """
        super().__init__(cursor)

    def lines(self, **kwargs) -> Generator[str, None, None]:
        """
        The lines of this enumeration.

        @param kwargs: typedef : bool - should this use the ctypedef syntax.
                       name    : str  - The name to use for this declaration.
        @return: Generator over lines.
        """
        yield Enumeration.cython_header(kwargs.get("typedef", False), kwargs.get("name", self.name))

        for line in self.members():
            yield TAB + line

    def members(self) -> Generator[str, None, None]:
        """
        Iterator over the members of this enum.

        @return: Generator[str, None, None]
        """
        gen = 0
        for kind, spelling, enum_value in Enumeration.iterate(self.cursor):
            if kind == clang.cindex.CursorKind.ENUM_CONSTANT_DECL:
                gen += 1
                yield f"{spelling} = {enum_value}"

        if not gen:
            yield "pass"

    @staticmethod
    def iterate(cursor: clang.cindex.Cursor) -> Generator[Tuple[clang.cindex.CursorKind, str, int], None, None]:
        for child in cursor.get_children():
            yield child.kind, child.spelling, child.enum_value

    @staticmethod
    def cython_header(typedef: bool, name: str) -> str:
        """
        The Cython header declaration for this enum.

        @param typedef: Whether this is a typedef'd enum.
        @param name: The name to use for this declaration.
        @return: str.
        """
        return f"{'ctypedef ' if typedef else ''}enum {name}:"


class Union(CCursor):
    def __init__(self, cursor: clang.cindex.Cursor):
        """
        Represents a union, given a union Cursor.

        @param cursor: Clang cursor.
        """
        super().__init__(cursor)
        self._children = list()

        for child in cursor.get_children():
            if (child.kind == clang.cindex.CursorKind.FIELD_DECL and child.spelling) or child.kind in ANON_KINDS:
                self._children.append(specialize(child))

    @property
    def associated_types(self) -> Set[CCursor]:
        result = set()

        for child in self._children:
            result.update(child.associated_types)

        return result

    def lines(self, **kwargs) -> Generator[str, None, None]:
        """
        The lines of this Union.

        @param kwargs: typedef : bool - Define using ctypedef syntax.
                       name    : str  - The name to use for this declaration.
        @return: Generator[str]
        """
        name = kwargs.get("name", self.name)
        for line in block(
            self._children,
            name,
            Union.cython_header(kwargs.get("typedef", False), name),
            True
        ):
            yield line

    @staticmethod
    def cython_header(typedef: bool, name: str) -> str:
        """
        The Cython header declaration for this union.

        @param typedef: Whether this is a typedef'd union.
        @param name: The name to use for this declaration.
        @return: str.
        """
        return f"{'ctypedef ' if typedef else ''}union {name}:"


class Typedef(CCursor):
    def __init__(self, cursor: clang.cindex.Cursor):
        """
        Represents a typedef, given the correct Clang Cursor.

        @param cursor: Clang typedef Cursor.
        """
        super().__init__(cursor)

    @property
    def underlying_type(self) -> clang.cindex.Type:
        """
        Unwraps the underlying type from pointers, arrays, etc.

        @return: The underlying type. A better form of `underlying_typedef_type`.
        """
        return utils.get_underlying_type(self.cursor.underlying_typedef_type)[0]

    @property
    def unsupported(self) -> bool:
        return (
            utils.is_typename_unsupported(self.cursor.underlying_typedef_type) or
            super().unsupported
        )

    def lines(self, **kwargs) -> Generator[str, None, None]:
        """
        Cython lines for this typedef.

        @param kwargs: None.
        @return: str.
        """
        utt = self.cursor.underlying_typedef_type

        if "__builtin_va_list" in (self.name, utt.spelling):
            yield f"ctypedef void* {self.name}"
            return
        if self.unsupported:
            yield f"#  ctypedef {utt.spelling} {self.name}"
            return

        result = utils.convert_dialect(utils.full_type_repr(utt, self.cursor))

        if utils.is_function_pointer(utt):
            # A function prototype can be typedefed but is not an lvalue reference
            if utt.kind == clang.cindex.TypeKind.FUNCTIONPROTO:
                yield "ctypedef " + result.replace("()", self.name, 1)
            else:
                i = result.index(')')
                yield "ctypedef " + result[:i] + self.name + result[i:]
            return

        ut, token = utils.get_underlying_type(utt)
        utd = ut.get_declaration()

        # If typedef of another type has not been handled from higher level context
        if utd.kind in ANON_KINDS and not result.strip():
            for line in specialize(utd).lines(name=self.name, typedef=True):
                yield line
            return

        yield f"ctypedef {result} {self.name}"


class Struct(CCursor):
    # Types yielded from members property
    INSTANCE_TYPES = (
        clang.cindex.CursorKind.FIELD_DECL,
        clang.cindex.CursorKind.CONSTRUCTOR,
        clang.cindex.CursorKind.CXX_METHOD,
        clang.cindex.CursorKind.FUNCTION_TEMPLATE,
        clang.cindex.CursorKind.TYPEDEF_DECL,
        clang.cindex.CursorKind.TYPE_ALIAS_DECL,
        clang.cindex.CursorKind.ENUM_DECL,
        clang.cindex.CursorKind.CLASS_DECL,
        clang.cindex.CursorKind.STRUCT_DECL,
        clang.cindex.CursorKind.CLASS_TEMPLATE,
        clang.cindex.CursorKind.UNION_DECL
    )

    def __init__(self, cursor: clang.cindex.Cursor):
        """
        Represents a Cython struct/cppclass, given the correct
        Clang Cursor.

        @param cursor: Clang struct/cppclass Cursor.
        """
        super().__init__(cursor)
        self._is_cppclass = utils.is_cppclass(cursor)
        self._children = list()
        self._tmpl_params = utils.get_template_params(cursor)

        for child in cursor.get_children():
            if (
                    child.access_specifier == clang.cindex.AccessSpecifier.PRIVATE or
                    child.kind not in Struct.INSTANCE_TYPES or
                    utils.is_extra_decl(child) or
                    (child.kind not in ANON_KINDS and not child.spelling)
            ):
                continue
            self._children.append(specialize(child))

    @property
    def is_cppclass(self) -> bool:
        """
        Whether this is a C++ class or POD C struct.

        @return: Boolean.
        """
        return self._is_cppclass

    @property
    def associated_types(self) -> Set[CCursor]:
        result = set()

        for child in self._children:
            result.update(child.associated_types)

        return result

    def lines(self, **kwargs) -> Generator[str, None, None]:
        """
        Lines of this class/structure.

        @param kwargs: typedef : bool - Should this use ctypedef syntax.
                       name    : str  - The name to use for this declaration.
        @return: Generator[str]
        """
        name = kwargs.get("name", self.name)

        for line in block(
            self._children,
            name,
            self.cython_header(kwargs.get("typedef", False), name),
            True
        ):
            yield line

    def cython_header(self, typedef: bool, name: str) -> str:
        """
        The Cython header for this struct/class.

        @param typedef: Whether this should be printed as a typedef.
        @param name: The name to use for this header.
        @return: str.
        """
        return "{}{} {}{}:".format(
            "ctypedef " if typedef and not self.is_cppclass else '',
            "cppclass" if self.is_cppclass else "struct",
            name,
            self._tmpl_params
        )


class Namespace:
    def __init__(self, cursors: list, recursive: bool, main_header: str,  valid_headers: set, *_):
        """
        Represents a Cython namespace declaration, given the following parameters.

        @param cursors: A list of cursors associated with this namespace.
        @param recursive: Whether this namespace should declare children from other headers, recursively.
        @param main_header: The header file to accept declarations from.
        @param valid_headers: The set of headers being parsed.
        """
        self.cursors = [CCursor(c) for c in cursors]
        self.cpp_name = self.cursors[0].address if cursors[0].kind in SPACE_KINDS else ''
        self.recursive = recursive
        self.main_header = main_header
        self.valid_headers = valid_headers
        self.children = list()
        self.class_space = all(utils.is_cppclass(c) for c in cursors)

        for cursor in self.cursors:
            self.children += filter(self._child_filter, cursor)

    @property
    def has_declarations(self) -> bool:
        """
        Whether this space has any valid declarations.

        @return: Boolean.
        """
        return len(self.children) > 0

    @property
    def forward_decls(self) -> Set[CCursor]:
        """
        Empty declarations needed to resolve types that
        have not been included.

        @return: Set of CCursors of type declarations that
        need to be defined.
        """
        assert not self.recursive, "Forward declarations should not be used when recursion is enabled"

        result = set()

        for child in self.children:
            for t in Namespace._get_all_assoc(child):
                addr = t.address
                if (
                    t.file != self.main_header and
                    addr not in IGNORED_IMPORTS and
                    addr not in REPLACED_IMPORTS
                ):
                    result.add(t)

        return result

    def lines(self, rel_header_path: str, system_header: bool) -> Generator[str, None, None]:
        """
        Generator over the lines of this namespace.

        @param rel_header_path: The relative header path to the header where this namespace is defined.
        @param system_header: Whether angled brackets should be added to the header name.
        @return: Generator[str]
        """
        children = [specialize(c) for c in self.children]
        name = self.cursors[0].address if self.cursors[0].cursor.kind in SPACE_KINDS else 'toplevel'

        for line in block(
            children,
            name,
            self.cython_header(rel_header_path, system_header),
            False
        ):
            yield line

    def cython_header(self, rel_header_path: str, system_header: bool) -> str:
        """
        The Cython header for this namespace.

        @param rel_header_path: Header path relative to the C compiler's include path.
        @param system_header: Whether angled brackets should be added to the header name.
        @return: The Cythonized header for this namespace.
        """
        header_name = rel_header_path.replace(os.path.sep, '/')
        header_name = f"<{header_name}>" if system_header else header_name
        base = f"cdef extern from \"{header_name}\""
        namespace = f" namespace \"{self.cpp_name}\":" if self.cpp_name else ':'

        return base + namespace

    def import_strings(self, include_all: bool) -> Set[str]:
        """
        Import strings required for this namespace.

        @param include_all: Whether all imports from unsubmitted headers
        should be inculded.
        @return: A set of import strings.
        """
        result = set()

        for child in self.children:
            for t in specialize(child).associated_types:

                if t.cursor.kind in TEMPLATE_KINDS:
                    continue

                if t.file not in self.valid_headers:
                    # Handle if import should be done via libc/libcpp
                    stdpath = STD_IMPORTS.get(t.address)

                    if stdpath is not None:
                        result.add(f"from {stdpath} cimport {t.name} as {t.address.replace('::', '_')}")
                        continue

                    if not include_all:
                        continue

                default = os.path.splitext(os.path.basename(self.main_header))[0] if self.recursive else None
                res = utils.get_import_string(child, t.cursor, not self.recursive, default)

                if res is not None:
                    result.add(res)

        return result

    def _child_filter(self, child: clang.cindex.Cursor):
        """
        Filters out invalid/invisible child cursors of this namespace.
        """
        if child.access_specifier == clang.cindex.AccessSpecifier.PRIVATE:
            return False
        if self.class_space and child.kind in Struct.INSTANCE_TYPES:
            return False
        if utils.is_extra_decl(child):
            return False
        if type(specialize(child)) is CCursor:
            return False
        try:
            return (
                self.recursive or
                os.path.abspath(child.location.file.name) == self.main_header
            )
        except AttributeError:
            return False

    @staticmethod
    def _get_all_assoc(cursor: clang.cindex.Cursor) -> Set[CCursor]:
        result = set()
        stack = [cursor]

        while len(stack):
            current = stack.pop()

            for child in current.get_children():
                stack.append(child)

                if (child.kind in TYPE_REFS or
                        (current.kind == clang.cindex.CursorKind.TYPEDEF_DECL and
                         child.kind in STRUCTURED_DATA_KINDS and
                         child.spelling)):
                    decl = child.get_definition()

                    if decl is None:
                        continue

                    spec = specialize(decl)

                    # Check to avoid parsing the same type multiple times.
                    # Greatly reduces the time required
                    if spec not in result:
                        stack.append(decl)
                        result.add(spec)

        return result
