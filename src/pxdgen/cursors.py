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
from typing import Optional, List, Generator, Set, Any, Tuple, Type


def specialize(cursor: clang.cindex.Cursor) -> Any:
    """
    Determine what abstracted class defined in this
    module to use for a specific cursor.

    @param cursor: A cursor to convert to a class from this module.
    @return: The converted type.
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
    elif cursor.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
        return Typedef(cursor)
    elif cursor.kind in STRUCTURED_DATA_KINDS:
        return Struct(cursor)
    else:
        return CCursor(cursor)


class CCursor:
    def __init__(self, cursor: clang.cindex.Cursor):
        self.cursor = cursor
        self._address = "::".join((self.namespace, self.name)).strip("::")

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
    def parent(self) -> Optional[CCursor]:
        p = self.cursor.lexical_parent
        return None if p is None else CCursor(p)

    @property
    def visible(self) -> bool:
        return self.cursor.access_specifier == clang.cindex.AccessSpecifier.PUBLIC

    @property
    def has_definition(self) -> bool:
        return self.cursor.get_definition() is not None

    @property
    def file(self) -> Optional[str]:
        l = self.cursor.location
        return None if l is None else os.path.abspath(l.file.name)

    @property
    def anonymous(self) -> bool:
        return self.cursor.is_anonymous()

    @property
    def name(self) -> str:
        return self.cursor.spelling

    @property
    def display(self) -> str:
        return self.cursor.displayname

    @property
    def home(self) -> str:
        return utils.containing_space(self.cursor, lambda p: p.kind == clang.cindex.CursorKind.NAMESPACE)

    @property
    def namespace(self) -> str:
        return utils.containing_space(self.cursor, lambda p: p.kind in SPACE_KINDS)

    @property
    def address(self) -> str:
        return self._address

    @property
    def cimport_name(self) -> str:
        return self.address.replace("::", '_')

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
        result = set()

        for child in self.cursor.get_children():
            if child.kind in (
                    clang.cindex.CursorKind.TYPE_REF,
                    clang.cindex.CursorKind.TEMPLATE_REF
            ):
                cdef = child.get_definition()
                if cdef is not None:
                    result.add(CCursor(cdef))

        return result

    # @property
    # def imports(self) -> Set[CCursor]:
    #     """
    #     Fully resolved import strings needed for this within this cursor.
    #
    #     @return: Set of import strings.
    #     """
    #     current_space = self.soft_namespace
    #     assoc = self.associated_types
    #
    #     return {t for t in assoc if t.namespace != current_space}


class DataType(CCursor):
    def __init__(self, cursor: clang.cindex.Cursor, *_):
        """
        Represents a simple variable or constant declaration,
        function parameter, struct/class/union field, etc.

        @param cursor: Associated Clang cursor.
        """
        super().__init__(cursor)

    @property
    def is_static(self) -> bool:
        """
        Whether the storage for this data type is static.

        @return: Boolean.
        """
        return self.cursor.storage_class == clang.cindex.StorageClass.STATIC

    @property
    def is_function_pointer(self) -> bool:
        return utils.is_function_pointer(self.cursor.type)

    @property
    def declaration(self) -> str:
        """
        The declaration of this Member in Cython syntax.

        @return: Cython syntax str.
        """
        if self.is_function_pointer:
            return self._function_ptr_declaration

        # Clang refers to arrys in int[20] syntax
        # This block extracts the array size portion,
        # and is saved to suffix so that the end
        # result looks like int data[20]
        typename = utils.full_type_repr(self.cursor.type, self.cursor)

        suffix = ''
        ob = typename.find('[')

        if ob != -1:
            suffix = typename[ob:]
            typename = typename[:ob].strip()

        # if typename.endswith('*'):
        #     typename = typename.replace(" *", '*')
        # elif typename.endswith('&'):
        #     typename = typename.replace(" &", '&')

        ret = f"{typename} {self.name}{suffix}"

        return utils.convert_dialect(ret)

    @property
    def _function_ptr_declaration(self) -> str:
        """
        Special declaration for function pointers.

        @return: str.
        """
        ndim, _ = utils.walk_pointer(self.cursor.type)
        result = utils.get_function_pointer_return_type(self.cursor.type)
        args = utils.get_function_pointer_arg_types(self.cursor.type)
        ret = f"{utils.full_type_repr(result, self.cursor)} ({'*' * ndim}{self.name})({','.join(utils.full_type_repr(arg, self.cursor) for arg in args)})"

        return utils.convert_dialect(ret.replace("(void)", "()"))


class Function(CCursor):
    def __init__(self, cursor: clang.cindex.Cursor, *_):
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
    def declaration(self) -> str:
        """
        The full function declaration for this function
        in Cython syntax.

        @return: str.
        """
        restype = utils.full_type_repr(self.cursor.result_type, self.cursor)
        restype = utils.convert_dialect(restype, True).strip()

        # if restype.endswith('*'):
        #     restype = restype.replace(" *", '*')
        # elif restype.endswith('&'):
        #     restype = restype.replace(" &", '&')

        return f"{restype} {self.name}{self._tmpl_params}({', '.join(self._argument_declarations)})"

    @property
    def is_static(self) -> bool:
        """
        Whether this function is a static method.

        @return: Boolean.
        """
        return self.cursor.is_static_method()

    @property
    def associated_types(self) -> List[CCursor]:
        result = [a for a in super().associated_types]

        for arg in self._args:
            result += arg.associated_types

        return result

    @property
    def _argument_declarations(self) -> Generator[str, None, None]:
        """
        Yields the Cython argument declarations of this function.
        """
        for mem in self._args:
            yield mem.declaration


class Constructor(Function):
    def __init__(self, cursor: clang.cindex.Cursor, *_):
        super().__init__(cursor)

    @property
    def declaration(self) -> str:
        """
        Gives the Cython syntax for this constructor. It
        is able to handle a constructor disguised as a
        function template declaration. In this case,
        it is given the return type 'void'.

        @return: Constructor declaration string.
        """
        spelling = self.name
        restype = "void " if self._tmpl_params else ''

        try:
            spelling = spelling[:spelling.index('<')]
        except ValueError:
            pass

        return f"{restype}{spelling}{self._tmpl_params}({', '.join(self._argument_declarations)})"


class Enumeration(CCursor):
    def __init__(self, cursor: clang.cindex.Cursor, *_, name: str = ''):
        """
        Represents an enum, given an enum Cursor.

        @param cursor: Clang cursor.
        @param name: Name override in the case that the spelling is empty
        """
        self._name = name or cursor.spelling
        super().__init__(cursor)

    @property
    def name(self) -> str:
        return self._name

    def cython_header(self, typedef: bool) -> str:
        """
        The Cython header declaration for this enum.

        @param typedef: Whether this is a typedef'd enum.
        @return: str.
        """
        return f"{'ctypedef ' if typedef else ''}enum {self.name}:"

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


class Union(CCursor):
    def __init__(self, cursor: clang.cindex.Cursor, *_, name: str = ''):
        """
        Represents a union, given a union Cursor.

        @param cursor: Clang cursor.
        @param name: Name override in the case that the spelling is empty
        """
        self._name = name or cursor.spelling
        super().__init__(cursor)
        self._children = list()

        for child in cursor.get_children():
            if child.kind == clang.cindex.CursorKind.FIELD_DECL:
                self._children.append(DataType(child))

    @property
    def associated_types(self) -> Set[CCursor]:
        result = set()

        for child in self._children:
            result.update(child.associated_types)

        return result

    @property
    def name(self):
        return self._name

    def cython_header(self, typedef: bool) -> str:
        """
        The Cython header declaration for this union.

        @param typedef: Whether this is a typedef'd union.
        @return: str.
        """
        return f"{'ctypedef ' if typedef else ''}union {self.name}:"

    def members(self) -> Generator[str, None, None]:
        """
        Iterator over the members of this union.

        @return: Generator[str, None, None]
        """
        for field in self._children:
            yield field.declaration

        if not len(self._children):
            yield "pass"


class Typedef(CCursor):
    def __init__(self, cursor: clang.cindex.Cursor, *_):
        """
        Represents a typedef, given the correct Clang Cursor.

        @param cursor: Clang typedef Cursor.
        """
        super().__init__(cursor)

        while cursor.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
            cursor = cursor.underlying_typedef_type.get_declaration()
            if cursor.kind == clang.cindex.CursorKind.NO_DECL_FOUND:
                self._base = None
                break
        else:
            self._base = cursor

    @property
    def associated_types(self) -> Set[CCursor]:
        result = set()
        cursor = self.cursor.underlying_typedef_type.get_declaration()

        if cursor.kind != clang.cindex.CursorKind.NO_DECL_FOUND:
            result.update(specialize(cursor).associated_types)

        return result

    @property
    def declaration(self) -> str:
        """
        Cython declaration for this typedef.

        @return: str.
        """
        utt = self.cursor.underlying_typedef_type

        if utils.is_function_pointer(utt):
            result = utils.get_function_pointer_return_type(utt)
            args = utils.get_function_pointer_arg_types(utt)
            ndim, _ = utils.walk_pointer(utt)

            left = utils.convert_dialect(utils.full_type_repr(result, self.cursor))
            right = ", ".join(utils.convert_dialect(utils.full_type_repr(arg, self.cursor)) for arg in args)

            return f"ctypedef {left} ({'*' * ndim}{self.name})({right.replace('(void)', '()')})"

        spelling = utils.convert_dialect(utils.full_type_repr(utt, self.cursor))

        # if spelling.endswith('*'):
        #     spelling = spelling.replace(" *", '*')
        # elif spelling.endswith('&'):
        #     spelling = spelling.replace(" &", '&')

        return f"ctypedef {spelling} {self.name}"

    @property
    def base(self) -> Optional[clang.cindex.Cursor]:
        """
        The Clang Cursor for the declaration of the type which
        this typedef represents. If the declaration is not found,
        None is returned.

        @return: Union[clang.cindex.Cursor, None].
        """
        return self._base


class Struct(CCursor):
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
    # VALID_KINDS = (
    #     INSTANCE_TYPES + (
    #          clang.cindex.CursorKind.TEMPLATE_TYPE_PARAMETER,
    #          clang.cindex.CursorKind.TEMPLATE_NON_TYPE_PARAMETER,
    #          clang.cindex.CursorKind.STRUCT_DECL,
    #          clang.cindex.CursorKind.ENUM_DECL,
    #          clang.cindex.CursorKind.VAR_DECL,
    #          clang.cindex.CursorKind.CLASS_DECL,
    #          clang.cindex.CursorKind.CLASS_TEMPLATE,
    #          clang.cindex.CursorKind.UNION_DECL,
    #     )
    # )

    def __init__(self, cursor: clang.cindex.Cursor, *_, name: str = ''):
        """
        Represents a Cython struct/cppclass, given the correct
        Clang Cursor.

        @param cursor: Clang struct/cppclass Cursor.
        @param name: Name override in the case that spelling is empty.
        """
        self._name = name or cursor.spelling
        super().__init__(cursor)
        self._is_cppclass = utils.is_cppclass(cursor)
        self._children = list()
        self._tmpl_params = utils.get_template_params(cursor)

        for child in cursor.get_children():
            if child.access_specifier == clang.cindex.AccessSpecifier.PRIVATE or child.kind not in Struct.INSTANCE_TYPES:
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
    def is_forward_decl(self) -> bool:
        """
        Whether this class is a forward declaration.

        @return: Boolean.
        """
        d = self.cursor.get_definition()
        return d is None or d != self.cursor

    @property
    def name(self) -> str:
        return self._name

    @property
    def associated_types(self) -> Set[CCursor]:
        result = set()

        for child in self._children:
            result.update(child.associated_types)

        return result

    def cython_header(self, typedef: bool) -> str:
        """
        The Cython header for this struct/class.

        @param typedef: Whether this should be printed as a typedef.
        @return: str.
        """
        return "{}{} {}{}:".format(
            "ctypedef " if typedef and not self.is_cppclass else '',
            "cppclass" if self.is_cppclass else "struct",
            self.name,
            self._tmpl_params
        )

    def members(self) -> Generator[str, None, None]:
        """
        Iterates over the Cython member declarations of this struct/class.

        @return: Generator[str].
        """
        for child in self._children:
            if isinstance(child, Function) and child.is_static:
                #  Handle static methods on instance side
                yield "@staticmethod"
            yield child.declaration

        if not len(self._children):
            yield "pass"


class Namespace:
    # Used to determine which types are output/processed as functions.
    # Functions have their return type and argument types resolved
    # FUNCTION_TYPES = (
    #     clang.cindex.CursorKind.FUNCTION_DECL, clang.cindex.CursorKind.FUNCTION_TEMPLATE
    # )

    # Determines what gets yielded as a struct or cppclass within this namespace
    # C++ classes also resolve to namespaces, but they are resolved in utils.find_namespaces
    # CLASS_TYPES = (clang.cindex.CursorKind.STRUCT_DECL, clang.cindex.CursorKind.CLASS_DECL,
    #                clang.cindex.CursorKind.CLASS_TEMPLATE
    # )

    # C++ classes are also processed as namespaces.
    # These are cursors that will be encountered while processing,
    # but should not emit warnings as they will not be ignored
    # when the struct/cppclass is being emitted.
    # STATIC_IGNORED_TYPES = (
    #     clang.cindex.CursorKind.NAMESPACE, clang.cindex.CursorKind.CXX_METHOD,
    #     clang.cindex.CursorKind.FIELD_DECL, clang.cindex.CursorKind.CONSTRUCTOR,
    #     clang.cindex.CursorKind.TEMPLATE_TYPE_PARAMETER,
    #     clang.cindex.CursorKind.TEMPLATE_NON_TYPE_PARAMETER,
    #     clang.cindex.CursorKind.TEMPLATE_TEMPLATE_PARAMETER
    # )

    # All valid types. Convenient for fast warning determination
    # VALID_TYPES = (clang.cindex.CursorKind.ENUM_DECL,
    #                clang.cindex.CursorKind.TYPEDEF_DECL,
    #                clang.cindex.CursorKind.VAR_DECL,
    #                clang.cindex.CursorKind.UNION_DECL
    # ) + FUNCTION_TYPES + CLASS_TYPES + STATIC_IGNORED_TYPES

    def __init__(self, cursors: list, recursive: bool, valid_headers: set, *_):
        """
        Represents a Cython namespace declaration, given the following parameters.

        @param cursors: A list of cursors associated with this namespace.
        @param recursive: Whether this namespace should declare children from other headers, recursively.
        @param valid_headers: A set of valid headers from which children can be declared.
                              useful for trimming if recursive is True.
        """
        self.cursors = [CCursor(c) for c in cursors]
        self.cpp_name = self.cursors[0].address
        self.recursive = recursive
        self.valid_headers = valid_headers
        self.children = list()
        self.class_space = all(utils.is_cppclass(c) for c in cursors)

        for cursor in self.cursors:
            self.children += list(filter(self._child_filter, cursor))

    @property
    def has_declarations(self) -> bool:
        """
        Whether this space has any valid declarations.

        @return: Boolean.
        """
        return len(self.children) > 0

    @property
    def import_strings(self) -> Set[str]:
        """
        Import strings required for this namespace.

        @return: A set of import strings.
        """
        result = set()

        for child in self.children:
            assoc = specialize(child).associated_types

            # print(f"Associated types of {child.spelling}:")
            for t in assoc:
                res = utils.get_import_string(child, t.cursor)

                if res is not None:
                    # Handle if import should be done via libc
                    stdpath = STD_IMPORTS.get(t.address, None)
                    if stdpath is not None and t.file not in self.valid_headers:
                        result.add(f"from {stdpath} cimport {t.name} as {t.address.replace('::', '_')}")
                    else:
                        result.add(res)

        return result

    @property
    def forward_decls(self) -> Set[CCursor]:
        """
        Empty declarations needed to resolve types that
        have not been included.

        @return: Set of CCursors of type declarations that
        need to be defined.
        """
        result = set()

        for child in self.children:
            cc = specialize(child)
            assoc = cc.associated_types

            for t in assoc:
                if (
                        t.file not in self.valid_headers and
                        t.address not in IGNORED_IMPORTS and
                        t.address not in STD_IMPORTS
                ):
                    result.add(specialize(t.cursor))

        return result

    def cython_header(self, rel_header_path: str) -> str:
        """
        The Cython header for this namespace.

        @param rel_header_path: Header path relative to the C compiler's include path.
        @return: The Cythonized header for this namespace.
        """
        base = f"cdef extern from \"{rel_header_path}\""
        namespace = f" namespace \"{self.cpp_name}\":" if self.cpp_name else ':'

        return base + namespace

    def members(self) -> Generator[str, None, None]:
        """
        Performs a full pass of this namespace and yields the declarations inside.

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
            elif child.kind in STRUCTURED_DATA_KINDS:
                if not child.spelling:
                    unk.append(child)
                    continue

                for i in Namespace._gen_struct_enum(child, Struct, False):
                    yield i
            elif child.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
                typedef = Typedef(child)
                base = typedef.base

                if base and base in unk:
                    if base.kind == clang.cindex.CursorKind.ENUM_DECL:
                        for i in Namespace._gen_struct_enum(base, Enumeration, True, name=child.spelling):
                            yield i
                    elif base.kind == clang.cindex.CursorKind.UNION_DECL:
                        for i in Namespace._gen_struct_enum(base, Union, True, name=child.spelling):
                            yield i
                    else:  # if base.kind == clang.cindex.CursorKind.STRUCT_DECL
                        for i in Namespace._gen_struct_enum(base, Struct, True, name=child.spelling):
                            yield i
                    unk.remove(base)
                    continue

                yield typedef.declaration
            elif child.kind in STATIC_FUNCTION_KINDS:
                yield Function(child).declaration
            elif child.kind == clang.cindex.CursorKind.VAR_DECL:
                yield DataType(child).declaration
            elif child.kind == clang.cindex.CursorKind.UNION_DECL:
                if not child.spelling:
                    unk.append(child)
                    continue
                for i in Namespace._gen_struct_enum(child, Union, False):
                    yield i

    def _child_filter(self, child: clang.cindex.Cursor):
        """
        Filters out invalid/invisible child cursors of this namespace.
        """
        if child.access_specifier == clang.cindex.AccessSpecifier.PRIVATE:
            return False
        if self.class_space and child.kind in Struct.INSTANCE_TYPES:
            return False
        try:
            return (
                self.recursive or
                os.path.abspath(child.location.file.name) in self.valid_headers
            )
        except AttributeError:
            return False

    @staticmethod
    def _gen_struct_enum(child: clang.cindex.Cursor, datatype: Type, typedef: bool, *_,
                         name: str = '') -> Generator[str, None, None]:
        """
        Yields the types of a struct, enumeration, or union
        """
        if datatype not in (Struct, Enumeration, Union):
            raise TypeError(f"Only Struct, Enumeration, and Union types are accepted to _gen_struct_enum, got {datatype}")

        obj = datatype(child, name=name)

        yield obj.cython_header(typedef)

        for m in obj.members():
            yield TAB + m
