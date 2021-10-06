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
from typing import Generator
from .. import utils
from ..utils import warning
from .atomic import Member


class Function:
    # Valid child types under a function cursor. Otherwise, emit a warning.
    VALID_KINDS = (
        clang.cindex.CursorKind.PARM_DECL,
        clang.cindex.CursorKind.TYPE_REF,
        clang.cindex.CursorKind.TEMPLATE_TYPE_PARAMETER,
        clang.cindex.CursorKind.TEMPLATE_NON_TYPE_PARAMETER
    )

    def __init__(self, cursor: clang.cindex.Cursor, *_):
        """
        Represents a Cython function declaration given a
        function Cursor.

        @param cursor: Clang cursor.
        """
        self.cursor = cursor

    @property
    def declaration(self) -> str:
        """
        The full function declaration for this function
        in Cython syntax.

        @return: str.
        """
        restype = utils.convert_dialect(self.cursor.result_type.spelling, True).strip()
        restype = utils.strip_beg_type_ids(restype)

        if restype.endswith('*'):
            restype = restype.replace(" *", '*')
        elif restype.endswith('&'):
            restype = restype.replace(" &", '&')

        return "%s %s%s(%s)" % (
            restype,
            self.cursor.spelling,
            utils.get_template_params(self.cursor),
            ', '.join(self._argument_declarations)
        )

    @property
    def is_static(self) -> bool:
        """
        Whether this function is a static method.

        @return: Boolean.
        """
        return self.cursor.is_static_method()

    @property
    def ctypes(self) -> list:
        """
        Return sanitized type strings for this function.
        Template functions have their template parameters
        filtered because the resolver does not need to be
        aware of generic types.

        @return: List of type strings for resolver.
        """
        ret = Member.basic_member_ctypes(self.cursor.result_type)
        template_params = utils.get_template_params_as_list(self.cursor)

        for a in self.cursor.get_arguments():
            ret += Member.basic_member_ctypes(a.type)

        if template_params:
            return list(filter(lambda p: p not in template_params, ret))

        return ret

    @property
    def _argument_declarations(self) -> Generator[str, None, None]:
        """
        Yields the Cython argument declarations of this function.
        """
        for child in self.cursor.get_children():
            if child.kind == clang.cindex.CursorKind.PARM_DECL:
                yield Member(child).declaration
            elif child.kind not in Function.VALID_KINDS:
                warning.warn_unsupported(self.cursor, child.kind)


class Constructor(Function):
    def __init__(self, cursor: clang.cindex.Cursor, *args):
        super().__init__(cursor, *args)

    @property
    def declaration(self) -> str:
        """
        Gives the Cython syntax for this constructor. It
        is able to handle a constructor disguised as a
        function template declaration. In this case,
        it is given the return type 'void'.

        @return: str.
        """
        spelling = self.cursor.spelling
        template_params = utils.get_template_params(self.cursor)
        restype = "void " if template_params else ''

        try:
            spelling = spelling[:spelling.index('<')]
        except ValueError:
            pass

        return "%s%s%s(%s)" % (
            restype,
            spelling,
            template_params,
            ', '.join(self._argument_declarations)
        )
