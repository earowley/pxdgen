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
import colorama
from . import settings


def find_all(cursors: list, kind: clang.cindex.CursorKind):
    """
    Searches through cursors list and generates
    all child cursors with the specified kind
    :param cursors: List of cursors to search
    :param kind: Kind to compare against cursor children
    :return: clang.cindex.Cursor generator
    """
    for cursor in cursors:
        for child in cursor.get_children():
            if child.kind == kind:
                yield child


def is_cppclass(cursor: clang.cindex.Cursor):
    """
    Determines whether a clang cursor represents a C++ class.
    Needed to distinguish from C structs since C++ classes can
    resolve to their own namespaces containing static methods...
    with or without fields/methods.
    """
    # There can be anonymous structs and enumerations as fields
    CTYPES = (clang.cindex.CursorKind.FIELD_DECL, clang.cindex.CursorKind.STRUCT_DECL, clang.cindex.CursorKind.ENUM_DECL, clang.cindex.CursorKind.UNION_DECL)
    return cursor.kind != clang.cindex.CursorKind.STRUCT_DECL or any((mem.kind not in CTYPES for mem in cursor.get_children()))


def find_namespaces(cursor: clang.cindex.Cursor, curr_name='') -> dict:
    """
    Generates a dictionary of namespace: [cursors] items. Generally
    the cursor should be a Translation Unit.
    :param cursor: Toplevel cursor, normally translation unit.
    :param curr_name: For recursion, leave blank
    :return: dict: Example {"a::b::c": [cursor1, cursor2]}
    """

    def _update(d1, d2):
        for key in d2:
            l = d1.get(key, None)
            if l is None:
                l = list()
                d1[key] = l

            l += d2[key]

    # Valid kinds that can be represented as a namespace in Cython
    # excluding Namespace
    CLASS_KINDS = (clang.cindex.CursorKind.STRUCT_DECL,
                   clang.cindex.CursorKind.CLASS_DECL,
                   clang.cindex.CursorKind.CLASS_TEMPLATE)

    ret = dict()
    namespaces = list()

    for child in cursor.get_children():
        if child.kind in CLASS_KINDS:
            if is_cppclass(child):
                namespaces.append(child)
        elif child.kind == clang.cindex.CursorKind.NAMESPACE:
            namespaces.append(child)

    for namespace in namespaces:
        _update(ret, find_namespaces(namespace, curr_name + "::" + namespace.spelling))

    if cursor.kind in (CLASS_KINDS + (clang.cindex.CursorKind.NAMESPACE,)):
        _update(ret, {curr_name.strip("::"): [cursor]})

    return ret


def is_function_pointer(ctype: clang.cindex.Type) -> bool:
    """
    Returns whether the clang.cindex.Type represents a function pointer
    :param ctype: Any clang.cindex.Type type
    :return: bool
    """
    if ctype.kind != clang.cindex.TypeKind.POINTER:
        return False

    return ctype.get_pointee().kind == clang.cindex.TypeKind.FUNCTIONPROTO


def get_function_pointer_return_type(ctype: clang.cindex.Type) -> str:
    """
    Returns the return type of a function pointer. The type
    is not verified to be a function pointer. Use is_function_pointer
    to check before calling this function.
    """
    return ctype.get_pointee().get_result().spelling


def get_function_pointer_arg_types(ctype: clang.cindex.Type):
    """
    Returns the arg types of a function pointer. The type
    is not verified to be a function pointer. Use is_function_pointer
    to check before calling this function.
    """
    return [arg.spelling for arg in ctype.get_pointee().argument_types()]


def get_template_params(cursor: clang.cindex.Cursor) -> str:
    """
    Returns the Cython string representing template parameters
    of a clang.cindex.Cursor
    :param cursor: Any clang.cindex.Cursor
    :return: Cython template string, like [T, U]
    """
    VALID = (
        clang.cindex.CursorKind.TEMPLATE_TYPE_PARAMETER,
        clang.cindex.CursorKind.TEMPLATE_NON_TYPE_PARAMETER
    )
    typenames = list()

    for c in cursor.get_children():
        if c.kind in VALID:
            typenames.append(c.spelling)

    if not len(typenames):
        return ''

    return "[%s]" % ', '.join(typenames)


def get_template_params_as_list(cursor: clang.cindex.Cursor) -> list:
    """
    Returns a list containing template parameters
    of a clang.cindex.Cursor
    :param cursor: Any clang.cindex.Cursor
    :return: A Python list like [T, U]
    """
    VALID = (
        clang.cindex.CursorKind.TEMPLATE_TYPE_PARAMETER,
        clang.cindex.CursorKind.TEMPLATE_NON_TYPE_PARAMETER
    )

    return [c.spelling for c in cursor.get_children() if c.kind in VALID]


def warn(message: str, warning_level: int = 1):
    """
    Emits a warning message, or does nothing based on
    .settings.WARNING_LEVEL
    """
    if warning_level <= settings.WARNING_LEVEL:
        print(colorama.Fore.YELLOW + "[Warning] " + colorama.Fore.RESET + message)


def warn_unsupported(parent: clang.cindex.Cursor, unsupported_type: clang.cindex.CursorKind):
    """
    Warns when the main script encounters an unsupported C/C++ declaration.
    Uses warning level 2.
    """
    try:
        file_loc = parent.location.file.name
    except AttributeError:
        file_loc = "undefined"

    warn("Unsupported type '%s' found in %s %s, file %s" % (
        unsupported_type.name,
        parent.kind.name,
        parent.spelling,
        file_loc
    ), warning_level=2)


def next_cpp_identifier(s: str) -> str:
    """
    Finds a cpp path-like identifier in the
    input string. For example in the string
    A::B::C foo(int a, int b) {,
    'A::B::C' would be returned.

    Old function - not used in the main script
    any more.
    """
    # [ and ] in case a generic Cython string is passed
    NS_TERMINATORS = {' ', ',', '<', '>', '(', ')', '[', ']'}
    sep_ind = s.find("::")

    if sep_ind == -1:
        return ''

    for i in range(sep_ind-1, -1, -1):
        if s[i] in NS_TERMINATORS:
            ns_start = i + 1
            break
    else:
        ns_start = 0

    for i in range(sep_ind+2, len(s)):
        if s[i] in NS_TERMINATORS:
            ns_end = i
            break
    else:
        ns_end = len(s)

    return s[ns_start:ns_end]


def strip_type_ids(cursor: clang.cindex.Cursor) -> str:
    """
    Returns the type represented by cursor with
    type identifiers stripped. In C, a struct
    referred to as 'struct foo' would always
    be referred to as 'foo' in Cython
    """
    type_spelling = cursor.type.spelling
    kinds = clang.cindex.CursorKind
    replacement = ''

    if cursor.kind == kinds.STRUCT_DECL:
        replacement = "struct"
    elif cursor.kind == kinds.ENUM_DECL:
        replacement = "enum"
    elif cursor.kind == kinds.UNION_DECL:
        replacement = "union"

    if replacement:
        return type_spelling.replace(replacement, '', 1).strip()

    return type_spelling


def strip_all_type_ids(s: str) -> str:
    """
    Directly replaces all type ids. Caused issues
    in convert_dialect, so its logic was split here.
    """
    return s.replace("struct ", '').replace("enum ", '').replace("union ", '')


def strip_beg_type_ids(s: str) -> str:
    """
    Removes a type id that exists only
    at the start of s
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


def sanitize_type_string(s: str) -> str:
    """
    Prepares a type string for submission to resolver.
    Removes extraneous adjectives from C builtin types
    like signedness and remove generic information.
    """
    s = s.replace("unsigned ", '').replace("signed ", '').replace("const ", '').replace("volatile ", '')
    s = strip_beg_type_ids(s)

    try:
        s = s[:s.index('<')]
    except ValueError:
        pass

    try:
        s = s[:s.index('[')]
    except ValueError:
        pass

    # Removing after * will also remove >C99 restrict
    try:
        return s[:s.index('*')].strip()
    except ValueError:
        return s.strip()


def convert_dialect(s: str, bool_replace: bool = False) -> str:
    """
    Converts C++ dialect string to Cython dialect
    string. Replaces template delimiters and removes
    some names that are valid in C(++) but not Cython
    :param s: String to convert
    :param bool_replace: replace any instance of bool with bint
    :return: Converted string
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

    ret = ret.replace("_Bool", "bint").replace("bool ", "bint ").replace("bool,", "bint,").replace("(bool)", "(bint)")
    ret = ret.replace("restrict ", '').replace("volatile ", '')

    if bool_replace:
        ret = ret.replace("bool", "bint")

    return ret

