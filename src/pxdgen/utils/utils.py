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

import os.path
import clang.cindex
from typing import List, Dict, Tuple, Callable, Optional
from ..constants import *


def find_namespaces(cursor: clang.cindex.Cursor, valid_headers: set, recursive: bool,
                    **kwargs) -> Dict[str, List[clang.cindex.Cursor]]:
    """
    Finds namespaces, given the top-level cursor of a header file.

    @param cursor: Clang Cursor.
    @param valid_headers: Header whitelist set for filtering.
    @param recursive: Use all namespaces, rather than just the ones in valid_headers.
    @return: Dictionary in the following form:
    {
        "A::B::C": [clang.cindex.Cursor c1, clang.cindex.Cursor c2 ...],
        ...
    }
    """

    def _update(d1, d2):
        for key in d2:
            ns_list = d1.get(key)
            if ns_list is None:
                ns_list = list()
                d1[key] = ns_list
            ns_list += d2[key]

    ret = dict()
    namespaces = list()
    curr_name = kwargs.get("curr_name", '')

    # Add all namespaces under the current cursor
    for child in cursor.get_children():
        if child.location.file is None:
            continue
        add_cond = all((
            child.kind == clang.cindex.CursorKind.NAMESPACE or is_cppclass(child),
            recursive or os.path.abspath(child.location.file.name) in valid_headers
        ))
        if add_cond:
            namespaces.append(child)

    # Recursively process the namespaces added above
    for namespace in namespaces:
        _update(ret, find_namespaces(namespace, valid_headers, recursive, curr_name=curr_name + "::" + namespace.spelling))

    # Add self, if needed
    if cursor.kind in SPACE_KINDS:
        _update(ret, {curr_name.strip("::"): [cursor]})

    return ret


def containing_space(cursor: clang.cindex.Cursor, pred: Callable) -> str:
    """
    Traverse the tree of a cursor and create an address from each
    Node that returns True from pred.

    @param cursor: The root Node.
    @param pred: The predicate to test each Node against.
    @return: A C++-like address.
    """
    parts = list()
    parent = cursor.lexical_parent

    while parent is not None:
        if pred(parent):
            parts.append(parent.spelling)
        parent = parent.lexical_parent

    parts.reverse()

    return "::".join(parts)


def get_cursor_location(cursor: clang.cindex.Cursor) -> str:
    """
    Returns the fully qualified C++ location of a cursor.
    Ex: Baz located in Namespace Foo -> Class Bar (Foo::Bar::Baz)
    would return Foo::Bar

    @param cursor: The cursor to locate.
    @return: Fully qualified C++ location as a string.
    """
    return containing_space(cursor, lambda parent: parent.kind in SPACE_KINDS and not parent.is_inline_namespace())


def get_cursor_namespace(cursor: clang.cindex.Cursor) -> str:
    """
    Returns the C++ namespace of a cursor, disregarding
    parent class/struct types.
    Ex: Baz located in namespace Foo -> Class Bar (Foo::Bar::Baz)
    would return Foo

    @param cursor: The cursor to locate.
    @return: C++ namespace of the cursor.
    """
    return containing_space(cursor, lambda parent: parent.kind == clang.cindex.CursorKind.NAMESPACE and not parent.is_inline_namespace())


def get_cursor_local_access(cursor: clang.cindex.Cursor) -> str:
    """
    Returns the access of a cursor relative to another
    cursor in the same namespace.
    Ex: Fuzz located in namespace Foo -> Class Bar -> Class Baz
    (Foo::Bar::Baz)
    would return Bar::Baz

    @param cursor: The cursor to access.
    @return: C++ access string.
    """
    return containing_space(cursor, lambda parent: parent.kind != clang.cindex.CursorKind.NAMESPACE)


def is_cppclass(cursor: clang.cindex.Cursor) -> bool:
    """
    Given a cursor to a struct/class/class template, returns whether the cursor
    is a C++ class type.

    @param cursor: Clang Cursor.
    @return: Boolean.
    """
    # Handle trivial cases where Clang does the heavy lifting
    if cursor.kind not in STRUCTURED_DATA_KINDS:
        return False
    if cursor.kind in (
            clang.cindex.CursorKind.CLASS_DECL,
            clang.cindex.CursorKind.CLASS_TEMPLATE
    ):
        return True

    # C++ struct decl that is not C-compliant
    for child in cursor.get_children():
        if child.kind == clang.cindex.CursorKind.FIELD_DECL:
            continue
        # There can be anonymous structs and enumerations as fields
        if child.kind in ANON_KINDS and child.is_anonymous():
            continue
        return True

    return False


def is_constructor(cursor: clang.cindex.Cursor) -> bool:
    """
    Whether the cursor represents a constructor. Needed
    because constructors can also be function templates.

    @param cursor: Any Clang cursor.
    @return: Whether the cursor represents a constructor.
    """
    if cursor.kind == clang.cindex.CursorKind.CONSTRUCTOR:
        return True

    if cursor.kind in METHOD_KINDS:
        if cursor.result_type.spelling == "void":
            container = cursor.lexical_parent

            if container is None:
                return False

            func_name = cursor.spelling

            try:
                func_name = func_name[:func_name.index("<")].strip()
            except ValueError:
                pass

            if func_name == container.spelling:
                return True

    return False


def is_forward_decl(cursor: clang.cindex.Cursor) -> bool:
    """
    Returns whether this cursor is a forward declaration.

    @param cursor: Clang cursor.
    @return: bool.
    """
    return cursor.kind in ANON_KINDS and cursor.get_definition() is None


def is_extra_decl(cursor: clang.cindex.Cursor) -> bool:
    """
    Returns whether this is a forward declaration that is
    shadowing the type definition.

    @param cursor: Clang cursor.
    @return: bool.
    """
    d = cursor.get_definition()
    return cursor.kind in ANON_KINDS and d is not None and d != cursor


def is_anonymous(cursor: clang.cindex.Cursor) -> bool:
    """
    Returns whether this struct/union/enum is
    an anonymous/unnamed declaration.

    @param cursor: Clang cursor.
    @return: bool.
    """
    return cursor.kind in ANON_KINDS and cursor.is_anonymous()


def is_typename_unsupported(t: clang.cindex.Type) -> bool:
    """
    Whether a type uses any typename references,
    which are not supported by Cython.

    @param t: Clang type.
    @return: bool.
    """
    ut, _ = get_underlying_type(t)
    return ut.spelling.startswith("typename ") or re.match(RE_DECLTYPE, ut.spelling) or any(
        is_typename_unsupported(ut.get_template_argument_type(i)) for i in range(ut.get_num_template_arguments())
    )


def is_alias_unsupported(cursor: clang.cindex.Cursor) -> bool:
    """
    Determines whether a declaration is based on a
    type that is defined using type aliasing not
    supported by Cython.

    @param cursor: Clang cursor.
    @return: bool.
    """
    while cursor.kind in TYPEDEF_KINDS:
        utt = cursor.underlying_typedef_type

        if is_typename_unsupported(utt):
            return True

        cursor = utt.get_declaration()

    return cursor.kind == clang.cindex.CursorKind.TYPE_ALIAS_TEMPLATE_DECL


def walk_pointer(t: clang.cindex.Type) -> Tuple[int, clang.cindex.Type]:
    """
    Follow a pointer to its underlying type.

    @param t: The pointer to follow. If t is not a pointer, t will be returned.
    @return: The underlying type.
    """
    pointers = 0
    while t.kind == clang.cindex.TypeKind.POINTER:
        t = t.get_pointee()
        pointers += 1

    return pointers, t


def is_function_pointer(ctype: clang.cindex.Type) -> bool:
    """
    Returns whether the type represents a function pointer
    or prototype.

    @param ctype: Any Clang Type object.
    @return: Boolean.
    """
    return walk_pointer(ctype)[1].kind == clang.cindex.TypeKind.FUNCTIONPROTO


def get_function_pointer_return_type(ctype: clang.cindex.Type) -> clang.cindex.Type:
    """
    Gets the return-type of a function pointer or prototype.
    Type is not validated, use is_function_pointer to validate.

    @param ctype: Clang Type object.
    @return: str.
    """
    return walk_pointer(ctype)[1].get_result()


def get_function_pointer_arg_types(ctype: clang.cindex.Type) -> List[clang.cindex.Type]:
    """
    Gets the argument types of a function pointer or prototype.
    Type is not validated, use is_function_pointer to validate.

    @param ctype: Clang Type object.
    @return: list.
    """
    return [arg for arg in walk_pointer(ctype)[1].argument_types()]


def is_function_variadic(cursor: clang.cindex.Cursor) -> bool:
    """
    Determines whether the function represented by
    the supplied cursor is variadic. Uses tokens
    generated by Clang.

    @param cursor: The cursor to check.
    @return: Whether the function was determined to be variadic.
    """
    tokens = [t.spelling for t in cursor.get_tokens()]
    tokens.reverse()

    try:
        return tokens[tokens.index(')') + 1] == "..."
    except ValueError:
        return False


def get_template_params(cursor: clang.cindex.Cursor) -> str:
    """
    Returns the Cython string representing template parameters
    of a Cursor.

    @param cursor: Any Cursor.
    @return: Cython template string, like "[T, U]".
    """

    typenames = list()

    for c in cursor.get_children():
        if c.kind in TEMPLATE_KINDS and c.spelling:
            typenames.append(c.spelling)

    if not len(typenames):
        return ''

    return f"[{', '.join(typenames)}]"


def get_template_params_as_list(cursor: clang.cindex.Cursor) -> List[str]:
    """
    Returns a list containing template parameters
    of a Cursor.

    @param cursor: Any Cursor.
    @return: A Python list like ['T', 'U'].
    """
    return [c.spelling for c in cursor.get_children() if c.kind in TEMPLATE_KINDS and c.spelling]


def get_relative_type_name(importer: clang.cindex.Cursor, importee: clang.cindex.Cursor) -> str:
    """
    How an imported type name appears with respect to another type.

    @param importer: The reference type declaration.
    @param importee: The imported type declaration.
    @return: The string following Cython syntax.
    """
    # Absolute location of importer
    importer_location = get_cursor_location(importer)
    # Absolute location of type being imported
    importee_location = get_cursor_location(importee)
    # Fully qualified C++ name of type being imported
    importee_addr = f"{importee_location}::{importee.spelling}".strip("::")

    # If the location is equal, the imported type can be referred to directly
    # If ignored, just return
    if importer_location == importee_location or importee_addr in IGNORED_IMPORTS:
        return importee.spelling
    # Convenient replacements for special types
    if importee_addr in REPLACED_IMPORTS:
        return REPLACED_IMPORTS[importee_addr]
    # Special handling of libc/libcpp imports that are already defined
    if importee_addr in STD_IMPORTS:
        return importee_addr.replace("::", '_')
    # Top-level namespace, do not process further
    if not importee_location:
        return importee.spelling

    # The containing namespace, not including classes or other spaces
    # In the pxd output, this resolves to a specific file
    importer_namespace = get_cursor_namespace(importer)
    importee_namespace = get_cursor_namespace(importee)
    importee_dot = get_cursor_local_access(importee).split("::")[1:]
    importee_dot.append(importee.spelling)

    # If in the same namespace, we have to access directly or by the containing class
    if importer_namespace == importee_namespace:
        # Not in a class, access directly
        if importee_namespace == importee_location:
            return importee.spelling
        # Create the spelling of class-access
        return '.'.join(importee_dot)
    # Not in the same namespace, use the full reference
    else:
        return (
            importee_namespace.replace("::", '_') +
            '_' + '.'.join(importee_dot)
        )


def get_import_string(importer: clang.cindex.Cursor, importee: clang.cindex.Cursor, import_same_space: bool, default: Optional[str]) -> Optional[str]:
    """
    Calculates an import string given two reference cursors.

    @param importer: The reference type declaration.
    @param importee: The imported type declaration.
    @param import_same_space: Whether types from the
    same namespace should be imported (from separate file).
    @param default: If provided, it serves as an override
    for imports which have no namespace to import from.
    @return: The import string following Cython syntax.
    """
    importer_namespace = get_cursor_namespace(importer)
    importee_namespace = get_cursor_namespace(importee)
    importee_location = get_cursor_location(importee)
    importee_addr = f"{importee_location}::{importee.spelling}".strip("::")

    # Ignored imports are builtin
    if importee_addr in IGNORED_IMPORTS or importee_addr in REPLACED_IMPORTS:
        return None

    importee_dot = get_cursor_local_access(importee).split("::")[1:]
    importee_dot.append(importee.spelling)

    # If in the same file, no import required
    if importer_namespace == importee_namespace:
        if not import_same_space:
            return None

        importer_file = importer.location.file
        importee_file = importee.location.file

        # Same file, no import required
        if importer_file is None or importee_file is None:
            return None
        if importer_file.name == importee_file.name:
            return None

        # If "C-style" and not in C++ namespace, declarations are placed in filename.pxd in output directory
        importee_namespace = importee_namespace or os.path.splitext(os.path.basename(importee_file.name))[0]

        return f"from {importee_namespace.replace('::', '.')} cimport {importee_dot[0]}"

    if not importee_namespace:
        importee_file = importee.location.file

        if importee_file is None:
            return None

        importee_namespace = default or os.path.splitext(os.path.basename(importee_file.name))[0]

        return f"from {importee_namespace} cimport {importee_dot[0]}"

    return "from {} cimport {} as {}".format(
        importee_namespace.replace('::', '.'),
        importee_dot[0],
        importee_namespace.replace('::', '_') + '_' + importee_dot[0]
    )


def full_type_repr(ctype: clang.cindex.Type, ref_cursor: clang.cindex.Cursor) -> str:
    """
    Get the full type string from an existing type.

    @param ctype: The type to convert.
    @param ref_cursor: A reference space to modify output, see example.
    @return: The full type string.
    Examples:
    Case: string<vector<int>>, ref_space = ''
    Returns: std::string<std::vector<int>>
    Case foo::bar, where ref_cursor == foo
    Returns: bar
    """
    expandable = (
        clang.cindex.TypeKind.ELABORATED,
        clang.cindex.TypeKind.UNEXPOSED
    )

    expandable_cursors = (
        clang.cindex.CursorKind.CLASS_DECL,
        clang.cindex.CursorKind.CLASS_TEMPLATE,
        clang.cindex.CursorKind.STRUCT_DECL
    )

    def finalize(subtype: clang.cindex.Type):
        if subtype.spelling in ("bool", "_Bool"):
            return "bint"
        if subtype.spelling in ("const bool", "const _Bool"):
            return "const bint"

        decl = subtype.get_declaration()

        if decl.kind == clang.cindex.CursorKind.NO_DECL_FOUND:
            rep = REPLACED_IMPORTS.get(subtype.spelling)
            return subtype.spelling if rep is None else rep

        return get_relative_type_name(ref_cursor, decl)

    if is_function_pointer(ctype):
        ndim, _ = walk_pointer(ctype)
        result = get_function_pointer_return_type(ctype)
        args = get_function_pointer_arg_types(ctype)
        return f"{full_type_repr(result, ref_cursor)} ({'*' * ndim})({', '.join(full_type_repr(a, ref_cursor) for a in args)})"
    elif ctype.kind == clang.cindex.TypeKind.POINTER:
        ndim, ctype = walk_pointer(ctype)
        return full_type_repr(ctype, ref_cursor) + '*' * ndim
    elif ctype.kind == clang.cindex.TypeKind.LVALUEREFERENCE:
        return full_type_repr(ctype.get_pointee(), ref_cursor) + '&'
    elif ctype.kind == clang.cindex.TypeKind.RVALUEREFERENCE:
        return full_type_repr(ctype.get_pointee(), ref_cursor) + "&&"
    elif ctype.kind == clang.cindex.TypeKind.CONSTANTARRAY:
        return full_type_repr(ctype.get_array_element_type(), ref_cursor) + f"[{ctype.get_array_size()}]"
    elif ctype.kind in (clang.cindex.TypeKind.INCOMPLETEARRAY, clang.cindex.TypeKind.VARIABLEARRAY):
        return full_type_repr(ctype.get_array_element_type(), ref_cursor) + "[]"

    nargs = ctype.get_num_template_arguments()

    if (
        ctype.kind not in expandable or
        ctype.get_declaration().kind not in expandable_cursors or
        nargs <= 0
    ):
        return finalize(ctype)

    params = list()

    for i in range(nargs):
        tmpl_param = ctype.get_template_argument_type(i)

        if not tmpl_param.spelling:
            params.append("void")
        else:
            params.append(full_type_repr(tmpl_param, ref_cursor))

    return f"{finalize(ctype)}<{', '.join(p.strip('*').strip('&') for p in params)}>"


def resolve_typename_type(ctype: clang.cindex.Type, parts: List[str]) -> Optional[clang.cindex.Cursor]:
    """
    Try to resolve C++ types that are resolved with `typename`

    @param ctype: The type to resolve.
    @param parts: Namespace parts eg ["std"].
    @return: Optional cursor, if one is found.
    """
    cur = ctype.translation_unit.cursor.get_children()
    stack = []
    looking = 0

    while True:
        try:
            name = parts[looking]
        except IndexError:
            return None

        for child in cur:
            if child.spelling == name:
                if child.kind in STRUCTURED_DATA_KINDS:
                    return child
                stack.append(cur)
                cur = child.get_children()
                looking += 1
                break
        else:
            if not len(stack):
                return None
            looking -= 1
            cur = stack.pop()


def get_underlying_type(ctype: clang.cindex.Type) -> Tuple[clang.cindex.Type, str]:
    """
    Unwraps the underlying type from pointers, arrays, etc.

    @return: clang.cindex.Type, token tuple
    """
    if ctype.kind == clang.cindex.TypeKind.POINTER:
        ndim, t = walk_pointer(ctype)
        t, tok = get_underlying_type(t)
        return t, tok + ('*' * ndim)
    elif ctype.kind == clang.cindex.TypeKind.LVALUEREFERENCE:
        t, tok = get_underlying_type(ctype.get_pointee())
        return t, tok + '&'
    elif ctype.kind == clang.cindex.TypeKind.RVALUEREFERENCE:
        t, tok = get_underlying_type(ctype.get_pointee())
        return t, tok + "&&"
    elif ctype.kind in (clang.cindex.TypeKind.INCOMPLETEARRAY, clang.cindex.TypeKind.VARIABLEARRAY):
        t, tok = get_underlying_type(ctype.get_array_element_type())
        return t, tok + "[]"
    elif ctype.kind == clang.cindex.TypeKind.CONSTANTARRAY:
        parts = list()

        while ctype.kind == clang.cindex.TypeKind.CONSTANTARRAY:
            parts.append(ctype.get_array_size())
            ctype = ctype.get_array_element_type()

        parts.reverse()
        token = ''

        for t in parts:
            token += f"[{t}]"

        ctype, tok = get_underlying_type(ctype)

        return ctype, tok + token

    return ctype, ''


def strip_type_ids(cursor: clang.cindex.Cursor) -> str:
    """
    Safest method of stripping type strings, but requires a Cursor object
    for introspection. Strips type strings of 'struct', 'enum', and 'union'.

    @param cursor: Clang Cursor.
    @return: str.
    """
    type_spelling = cursor.type.spelling
    replacement = ''

    if cursor.kind == clang.cindex.CursorKind.STRUCT_DECL:
        replacement = "struct"
    elif cursor.kind == clang.cindex.CursorKind.ENUM_DECL:
        replacement = "enum"
    elif cursor.kind == clang.cindex.CursorKind.UNION_DECL:
        replacement = "union"

    if replacement:
        return type_spelling.replace(replacement, '', 1).strip()

    return type_spelling


def strip_all_type_ids(s: str) -> str:
    """
    Deletes all instances of 'struct', 'enum' and 'union' in the type string.
    Can cause issues if the type name has the words in them.

    @param s: Type string to strip.
    @return: Stripped type string.
    """
    return s.replace("struct ", '').replace("enum ", '').replace("union ", '')


def strip_beg_type_ids(s: str) -> str:
    """
    Deletes instances of 'struct', 'enum', and 'union' that exist at the
    beginning of the type string s.

    @param s: Type string to strip.
    @return: Stripped type string.
    """
    ids = ("struct ", "enum ", "union ")

    for i in ids:
        if s.find(i) == 0:
            return s[len(i):]
        #  const params
        const_term = "const " + i
        if s.find(const_term) == 0:
            return s.replace(const_term, "const ")

    return s


def convert_dialect(s: str) -> str:
    """
    Converts C++ dialect string to Cython dialect
    string. Replaces template delimiters and removes
    some names that are valid in C(++) but not Cython

    @param s: String to convert
    @return: Converted string
    """
    throws = "throw("

    # First templates
    ret = s.replace('<', '[').replace('>', ']')

    # Replace exception information
    tloc = ret.find(throws)
    if tloc != -1:
        eb = ret.index(')', tloc)
        ret = ret.replace(ret[tloc:eb+1], "except +")
    else:
        ret = ret.replace("noexcept", '')

    ret = ret.replace("restrict ", '').replace("volatile ", '').replace("typename ", '').replace("::", '.')

    return ret
