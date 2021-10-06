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
from .atomic import Member
from ..utils import warning
from typing import Generator


class Union:
    def __init__(self, cursor: clang.cindex.Cursor, *_,
                 name: str = ''):
        """
        Represents a union, given a union Cursor.

        @param cursor: Clang cursor.
        @param name: Name override in the case that the spelling is empty
        """
        self.cursor = cursor
        self.name = name or self.cursor.spelling
        
    @property
    def ctypes(self) -> list:
        """
        The ctypes for this union.
        """
        ret = list()
        for child in self.cursor.get_children():
            if child.kind == clang.cindex.CursorKind.FIELD_DECL:
                ret += Member.basic_member_ctypes(child.type)
                
        return ret

    def cython_header(self, typedef: bool) -> str:
        """
        The Cython header declaration for this union.

        @param typedef: Whether this is a typedef'd union.
        @return: str.
        """
        return "%sunion %s:" % (
            "ctypedef " if typedef else '',
            self.name
        )

    def members(self) -> Generator[str, None, None]:
        """
        Iterator over the members of this union.

        @return: Generator[str, None, None]
        """
        gen = 0
        for field in self.cursor.get_children():
            if field.kind == clang.cindex.CursorKind.FIELD_DECL:
                gen += 1
                yield Member(field).declaration
            else:
                warning.warn_unsupported(self.cursor, field.kind)

        if not gen:
            yield "pass"
