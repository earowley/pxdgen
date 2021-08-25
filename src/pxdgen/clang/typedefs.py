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
from typing import Union
from .atomic import Member
from .. import utils


class Typedef:
    def __init__(self, cursor: clang.cindex.Cursor, *args):
        self.cursor = cursor

    @property
    def declaration(self) -> str:
        """
        Cython typedef declaration.
        """
        tdtype = self.cursor.underlying_typedef_type
        spelling = utils.convert_dialect(tdtype.spelling).strip()

        if utils.is_function_pointer(tdtype):
            spelling = utils.strip_all_type_ids(spelling).replace("(void)", "()")
            return "ctypedef %s" % (spelling.replace("(*)", "(*%s)" % self.cursor.spelling))

        spelling = utils.strip_beg_type_ids(spelling)

        if spelling.endswith('*'):
            spelling = spelling.replace(" *", '*')
        elif spelling.endswith('&'):
            spelling = spelling.replace(" &", '&')

        return "ctypedef %s %s" % (spelling, self.cursor.spelling)

    @property
    def base(self) -> Union[clang.cindex.Cursor, None]:
        """
        The declaration that this typedef represents.
        """
        cursor = self.cursor

        while cursor.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
            cursor = cursor.underlying_typedef_type.get_declaration()
            if cursor.kind == clang.cindex.CursorKind.NO_DECL_FOUND:
                return None

        return cursor

    @property
    def ctypes(self) -> list:
        """
        Types used in this typedef.
        """
        return Member.basic_member_ctypes(self.cursor.underlying_typedef_type)
