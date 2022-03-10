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


def find_namespaces(cursor: clang.cindex.Cursor, valid_headers: set = None,
                    **kwargs) -> Dict[str, List[clang.cindex.Cursor]]:
    """
    Finds namespaces, given the top-level cursor of a header file.
    @param cursor: Clang Cursor.
    @param valid_headers: Header whitelist set for filtering
    @return: Dictionary in the following form:
    {
        "A::B::C": [clang.cindex.Cursor c1, clang.cindex.Cursor c2 ...],
        ...
    }
    """

    def _update(d1, d2):
        for key in d2:
            l = d1.get(key, None)
            if l is None:
                l = list()
                d1[key] = l

            l += d2[key]

    ret = dict()
    namespaces = list()
    curr_name = kwargs.get("curr_name", '')

    for child in cursor.get_children():
        add_cond = all((
            child.kind == clang.cindex.CursorKind.NAMESPACE or is_cppclass(child),
            valid_headers is None or os.path.abspath(child.location.file.name) in valid_headers
        ))
        if add_cond:
            namespaces.append(child)

    for namespace in namespaces:
        _update(ret, find_namespaces(namespace, valid_headers, curr_name=curr_name + "::" + namespace.spelling))

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


def is_cppclass(cursor: clang.cindex.Cursor) -> bool:
    """
    Given a cursor to a struct/class/class template, returns whether the cursor
    is a C++ class type.

    @param cursor: Clang Cursor.
    @return: Boolean.
    """
    # There can be anonymous structs and enumerations as fields
    ANON = (clang.cindex.CursorKind.STRUCT_DECL, clang.cindex.CursorKind.ENUM_DECL, clang.cindex.CursorKind.UNION_DECL)
    # return cursor.kind != clang.cindex.CursorKind.STRUCT_DECL or any((mem.kind not in CTYPES for mem in cursor.get_children()))
    if cursor.kind not in (
        clang.cindex.CursorKind.CLASS_DECL,
        clang.cindex.CursorKind.CLASS_TEMPLATE,
        clang.cindex.CursorKind.STRUCT_DECL
    ):
        return False
    if cursor.kind in (
            clang.cindex.CursorKind.CLASS_DECL,
            clang.cindex.CursorKind.CLASS_TEMPLATE
    ):
        return True

    for child in cursor.get_children():
        if child.kind not in ANON + (clang.cindex.CursorKind.FIELD_DECL,):
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
    d = cursor.get_definition()
    return cursor.kind in ANON_KINDS and (d is None or d != cursor)


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
    Returns whether the type represents a function pointer.

    @param ctype: Any Clang Type object.
    @return: Boolean.
    """
    if ctype.kind != clang.cindex.TypeKind.POINTER:
        return False

    _, result = walk_pointer(ctype)

    return result.kind == clang.cindex.TypeKind.FUNCTIONPROTO


def get_function_pointer_return_type(ctype: clang.cindex.Type) -> clang.cindex.Type:
    """
    Gets the return type of a function pointer. Type is not validated,
    use is_function_pointer to validate.

    @param ctype: Clang Type object.
    @return: str.
    """
    _, result = walk_pointer(ctype)
    return result.get_result()


def get_function_pointer_arg_types(ctype: clang.cindex.Type) -> List[clang.cindex.Type]:
    """
    Gets the argument types of a function pointer. Type is not validated,
    use is_function_pointer to validate.

    @param ctype: Clang Type object.
    @return: list.
    """
    _, result = walk_pointer(ctype)
    return [arg for arg in result.argument_types()]


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
        if c.kind in TEMPLATE_KINDS:
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
    return [c.spelling for c in cursor.get_children() if c.kind in TEMPLATE_KINDS]


def get_relative_type_name(importer: clang.cindex.Cursor, importee: clang.cindex.Cursor) -> str:
    """
    How an imported type name appears with respect to another type.

    @param importer: The reference type declaration.
    @param importee: The imported type declaration.
    @return: The string following Cython syntax.
    """
    importer_space = containing_space(importer, lambda p: p.kind in SPACE_KINDS)
    importee_space = containing_space(importee, lambda p: p.kind in SPACE_KINDS)
    addr = f"{importee_space}::{importee.spelling}".strip("::")

    if importer_space == importee_space or addr in IGNORED_IMPORTS:
        return importee.spelling
    if addr in STD_IMPORTS:
        return addr.replace("::", '_')
    if not importee_space:
        return importee.spelling

    importer_home = containing_space(importer, lambda p: p.kind == clang.cindex.CursorKind.NAMESPACE)
    importee_home = containing_space(importee, lambda p: p.kind == clang.cindex.CursorKind.NAMESPACE)
    importee_dot = containing_space(importee, lambda p: p.kind != clang.cindex.CursorKind.NAMESPACE).split("::")[1:]
    importee_dot.append(importee.spelling)

    if importer_home == importee_home:
        # If importee is toplevel, it is visible from everywhere in the namespace
        if importee_home == importee_space:
            return importee.spelling
        return '.'.join(importee_dot)
    else:
        return (
            importee_home.replace("::", '_') +
            '_' + '.'.join(importee_dot)
        )


def get_import_string(importer: clang.cindex.Cursor, importee: clang.cindex.Cursor) -> Optional[str]:
    """
    Calculates an import string given two reference cursors.

    @param importer: The reference type declaration.
    @param importee: The imported type declaration.
    @return: The import string following Cython syntax.
    """
    importer_home = containing_space(importer, lambda p: p.kind == clang.cindex.CursorKind.NAMESPACE)
    importee_home = containing_space(importee, lambda p: p.kind == clang.cindex.CursorKind.NAMESPACE)
    importee_space = containing_space(importee, lambda p: p.kind in SPACE_KINDS)
    addr = f"{importee_space}::{importee.spelling}".strip("::")

    if addr in IGNORED_IMPORTS or not importee_space:
        return None

    importee_dot = containing_space(importee, lambda p: p.kind != clang.cindex.CursorKind.NAMESPACE).split("::")[1:]
    importee_dot.append(importee.spelling)

    if importer_home == importee_home:
        importer_file = importer.location.file
        importee_file = importee.location.file

        if importer_file is None or importee_file is None:
            return None
        if importer_file.name == importee_file.name and not is_forward_decl(importee):
            return None

        # ipath = os.path.basename(importee_file.name)
        # i = ipath.rfind('.')
        #
        # if i != -1:
        #     ipath = ipath[:i]

        return f"from {importee_home.replace('::', '.')} cimport {importee_dot[0]}"

    return "from {} cimport {} as {}".format(
        importee_home.replace('::', '.'),
        importee_dot[0],
        importee_home.replace('::', '_') + '_' + importee_dot[0]
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
    EXPANDABLE = (
        clang.cindex.TypeKind.ELABORATED,
        clang.cindex.TypeKind.UNEXPOSED
    )

    EXPANDABLE_CURSORS = (
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
            if subtype.spelling.startswith("typename "):
                parts = subtype.spelling[subtype.spelling.index(' ')+1:].split("::")
                tmpl_removed = list()

                for name in parts:
                    j = name.find('<')

                    if j != -1:
                        tmpl_removed.append(name[:j])
                    else:
                        tmpl_removed.append(name)

                cur = resolve_typename_type(subtype, tmpl_removed)

                if cur is None:
                    return subtype.spelling

                j = tmpl_removed.index(cur.spelling)
                corrected = get_relative_type_name(ref_cursor, cur)

                return f"{parts[j].replace(cur.spelling, corrected)}.{'.'.join(parts[j+1:])}"

            return subtype.spelling

        return get_relative_type_name(ref_cursor, decl)

    if ctype.kind == clang.cindex.TypeKind.POINTER:
        ndim, ctype = walk_pointer(ctype)
        return full_type_repr(ctype, ref_cursor) + '*' * ndim
    elif ctype.kind == clang.cindex.TypeKind.LVALUEREFERENCE:
        return full_type_repr(ctype.get_pointee(), ref_cursor) + '&'
    elif ctype.kind == clang.cindex.TypeKind.RVALUEREFERENCE:
        return full_type_repr(ctype.get_pointee(), ref_cursor) + "&&"
    elif ctype.kind == clang.cindex.TypeKind.CONSTANTARRAY:
        return full_type_repr(ctype.get_array_element_type(), ref_cursor) + f"[{ctype.get_array_size()}]"
    elif ctype.kind == clang.cindex.TypeKind.INCOMPLETEARRAY:
        return full_type_repr(ctype.get_array_element_type(), ref_cursor) + "[]"

    nargs = ctype.get_num_template_arguments()

    if (
        ctype.kind not in EXPANDABLE or
        ctype.get_declaration().kind not in EXPANDABLE_CURSORS or
        nargs <= 0
    ):
        return finalize(ctype)

    params = list()

    for i in range(nargs):
        params.append(full_type_repr(ctype.get_template_argument_type(i), ref_cursor))

    return f"{finalize(ctype)}<{', '.join(params)}>"


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
        name = parts[looking]

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
        return t, '*' * ndim
    elif ctype.kind == clang.cindex.TypeKind.LVALUEREFERENCE:
        return ctype.get_pointee(), '&'
    elif ctype.kind == clang.cindex.TypeKind.RVALUEREFERENCE:
        return ctype.get_pointee(), "&&"
    elif ctype.kind == clang.cindex.TypeKind.CONSTANTARRAY:
        parts = list()

        while ctype.kind == clang.cindex.TypeKind.CONSTANTARRAY:
            parts.append(ctype.get_array_size())
            ctype = ctype.get_array_element_type()

        parts.reverse()
        token = ''

        for t in parts:
            token += f"[{t}]"

        return ctype, token

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
    IDS = ("struct ", "enum ", "union ")

    for i in IDS:
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
    THROWS = "throw("

    # First templates
    ret = s.replace('<', '[').replace('>', ']')

    # Replace exception information
    tloc = ret.find(THROWS)
    if tloc != -1:
        eb = ret.index(')', tloc)
        ret = ret.replace(ret[tloc:eb+1], "except +")
    else:
        ret = ret.replace("noexcept", '')

    ret = ret.replace("restrict ", '').replace("volatile ", '').replace("typename ", '').replace("::", '.')

    return ret
