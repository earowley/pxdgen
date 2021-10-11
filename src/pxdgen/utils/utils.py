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
    if cursor.kind not in (clang.cindex.CursorKind.CLASS_DECL, clang.cindex.CursorKind.CLASS_TEMPLATE, clang.cindex.CursorKind.STRUCT_DECL):
        return False
    if cursor.kind in (clang.cindex.CursorKind.CLASS_DECL, clang.cindex.CursorKind.CLASS_TEMPLATE):
        return True

    for child in cursor.get_children():
        if child.kind not in  ANON + (clang.cindex.CursorKind.FIELD_DECL,):
            return True

    return False


def find_namespaces(cursor: clang.cindex.Cursor, valid_headers: set = None, curr_name='') -> dict:
    """
    Finds namespaces, given the top-level cursor of a header file.
    @param cursor: Clang Cursor.
    @param curr_name: Recursive helper, leave as-is.
    @return: Dictionary in the following form:
    {
        "A::B::C": [clang.cindex.Cursor c1, clang.cindex.Cursor c2 ...]
    }
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
    CLASS_KINDS = (
                   clang.cindex.CursorKind.STRUCT_DECL,
                   clang.cindex.CursorKind.CLASS_DECL,
                   clang.cindex.CursorKind.CLASS_TEMPLATE,
                   clang.cindex.CursorKind.NAMESPACE
    )

    ret = dict()
    namespaces = list()

    for child in cursor.get_children():
        if (child.kind == clang.cindex.CursorKind.NAMESPACE or is_cppclass(child)) and (valid_headers is None or os.path.abspath(child.location.file.name) in valid_headers):
            namespaces.append(child)

    for namespace in namespaces:
        _update(ret, find_namespaces(namespace, valid_headers, curr_name + "::" + namespace.spelling))

    if cursor.kind in CLASS_KINDS:
        _update(ret, {curr_name.strip("::"): [cursor]})

    return ret


def is_function_pointer(ctype: clang.cindex.Type) -> bool:
    """
    Returns whether the type represents a function pointer.

    @param ctype: Any Clang Type object.
    @return: Boolean.
    """
    if ctype.kind != clang.cindex.TypeKind.POINTER:
        return False
    
    return ctype.get_pointee().kind == clang.cindex.TypeKind.FUNCTIONPROTO


def get_function_pointer_return_type(ctype: clang.cindex.Type) -> clang.cindex.Type:
    """
    Gets the return type of a function pointer. Type is not validated,
    use is_function_pointer to validate.

    @param ctype: Clang Type object.
    @return: str.
    """
    return ctype.get_pointee().get_result()


def get_function_pointer_arg_types(ctype: clang.cindex.Type) -> list:
    """
    Gets the argument types of a function pointer. Type is not validated,
    use is_function_pointer to validate.

    @param ctype: Clang Type object.
    @return: list.
    """
    return [arg for arg in ctype.get_pointee().argument_types()]


def get_template_params(cursor: clang.cindex.Cursor) -> str:
    """
    Returns the Cython string representing template parameters
    of a Cursor.

    @param cursor: Any Cursor.
    @return: Cython template string, like [T, U].
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
    of a Cursor.

    @param cursor: Any Cursor.
    @return: A Python list like [T, U].
    """
    VALID = (
        clang.cindex.CursorKind.TEMPLATE_TYPE_PARAMETER,
        clang.cindex.CursorKind.TEMPLATE_NON_TYPE_PARAMETER
    )

    return [c.spelling for c in cursor.get_children() if c.kind in VALID]


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


def sanitize_type_string(s: str) -> str:
    """
    Prepares a type string for submission to resolver.
    Removes extraneous adjectives from C builtin types
    like signedness and remove generic information.

    @param s: Input type string.
    @return: Sanitized type string.
    """
    s = s.replace("unsigned ", '')\
         .replace("signed ", '')\
         .replace("const ", '')\
         .replace("volatile ", '')\
         .replace("restrict ", '')\
         .replace('*', '')\
         .replace('&', '')

    s = strip_beg_type_ids(s)

    try:
        s = s[:s.index('[')]
    except ValueError:
        pass

    return s.strip()


def extract_type_strings(t: clang.cindex.Type) -> list:
    """
    The purpose of this function is to extract
    the type strings within a more complex expression.
    For example, in the examples:

    Foo<Bar<Baz<int>>>
    Foo<Bar, Baz<int>>
    Foo<Bar, Baz, int>
    Foo<Bar<int>, Baz<int>>

    Foo, Bar, Baz, and int need to be resolved.
    """
    OB = '<'
    tmpl_arg_count = t.get_num_template_arguments()

    if tmpl_arg_count == 0:
        return [t.spelling]

    ret = list()

    for i in range(tmpl_arg_count):
        ret += extract_type_strings(t.get_template_argument_type(i))

    i = t.spelling.find(OB)
    if i == -1:
        ret.append(t.spelling)
    else:
        ret.append(t.spelling[:i])

    return ret


def convert_dialect(s: str, bool_replace: bool = False) -> str:
    """
    Converts C++ dialect string to Cython dialect
    string. Replaces template delimiters and removes
    some names that are valid in C(++) but not Cython

    @param s: String to convert
    @param bool_replace: replace any instance of bool with bint
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

    ret = ret.replace("_Bool", "bint").replace("bool ", "bint ").replace("bool,", "bint,").replace("(bool)", "(bint)")
    ret = ret.replace("restrict ", '').replace("volatile ", '')

    if bool_replace:
        ret = ret.replace("bool", "bint")

    return ret

