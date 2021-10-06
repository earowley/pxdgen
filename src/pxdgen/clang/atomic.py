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
from .. import utils


# The Member class represents a variable declaration in a Space,
# or a field declaration in a struct/union
class Member:
    def __init__(self, cursor: clang.cindex.Cursor, *_):
        """
        A Member is a common pattern that can represent
        a variable declaration, field declaration, or
        function parameter.

        @param cursor: Associated clang cursor.
        """
        self.cursor = cursor

    @staticmethod
    def basic_member_ctypes(t: clang.cindex.Type) -> list:
        """
        Extracts sanitized type strings from Member-like
        types.

        @param t: The type to process.
        @return: List of type strings for resolving.
        """
        if utils.is_function_pointer(t):
            rtype = utils.get_function_pointer_return_type(t)
            atypes = utils.get_function_pointer_arg_types(t)
            types = [ts for ts in [rtype] + atypes]
        else:
            types = [t.spelling]

        ret = list()

        for t in types:
            ret += [utils.sanitize_type_string(temp) for temp in utils.nested_template_type_strings(t)]
            ret.append(utils.sanitize_type_string(t))

        return ret

    @property
    def is_static(self) -> bool:
        """
        Whether this is a static class variable.

        @return: Boolean.
        """
        return self.cursor.storage_class == clang.cindex.StorageClass.STATIC

    @property
    def declaration(self) -> str:
        """
        The declaration of this Member in Cython syntax.

        @return: Cython syntax str.
        """
        if utils.is_function_pointer(self.cursor.type):
            return self._function_ptr_declaration

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
    def ctypes(self) -> list:
        """
        Wrapper for basic_member_ctypes static method.

        @return: list.
        """
        return Member.basic_member_ctypes(self.cursor.type)

    @property
    def _function_ptr_declaration(self) -> str:
        """
        Special declaration for function pointers.

        @return: str.
        """
        typename = self.cursor.type.spelling
        ret = utils.strip_all_type_ids(typename.replace("(*)", "(*%s)" % self.cursor.spelling)).replace("(void)", "()")

        return utils.convert_dialect(ret).strip()
