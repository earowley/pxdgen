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
from ..utils import warning
from typing import Generator


class Enumeration:
    def __init__(self, cursor: clang.cindex.Cursor, *_,
                 name: str = ''):
        """
        Represents an enum, given an enum Cursor.

        @param cursor: Clang cursor.
        @param name: Name override in the case that the spelling is empty
        """
        self.cursor = cursor
        self.name = name or self.cursor.spelling

    def cython_header(self, typedef: bool) -> str:
        """
        The Cython header declaration for this enum.

        @param typedef: Whether this is a typedef'd enum.
        @return: str.
        """
        return "%senum %s:" % (
            "ctypedef " if typedef else '',
            self.name
        )

    def members(self) -> Generator[str, None, None]:
        """
        Iterator over the members of this enum.

        @return: Generator[str, None, None]
        """
        gen = 0
        for enum in self.cursor.get_children():
            if enum.kind == clang.cindex.CursorKind.ENUM_CONSTANT_DECL:
                gen += 1
                yield "%s = %s" % (enum.spelling, enum.enum_value)
            else:
                warning.warn_unsupported(self.cursor, enum.kind)

        if not gen:
            yield "pass"
