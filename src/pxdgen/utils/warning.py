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

import colorama
import clang.cindex

_WARNING_LEVEL = 0


def set_warning_level(level: int):
    """
    Sets the warning level for PxdGen API.
    Higher warning levels print more messages.
    Warning level setting defaults to 0.

    @param level: The level to set.
    @return: None
    """
    global _WARNING_LEVEL
    _WARNING_LEVEL = level


def warn(message: str, warning_level: int = 1):
    """
    Emits a warning if the conditions are met.

    @param message: The warning to emit.
    @param warning_level: The level such that the message should be printed if
    it is less than or equal to the warning level setting.
    @return: None
    """
    if warning_level <= _WARNING_LEVEL:
        print(colorama.Fore.YELLOW + "[Warning] " + colorama.Fore.RESET + message)


def warn_unsupported(parent: clang.cindex.Cursor, unsupported_type: clang.cindex.CursorKind):
    """
    Warns of an unsupported Clang type in PxdGen.
    Defaults to warning level 2.

    @param parent: Parent cursor for identification/location purposes.
    @param unsupported_type: The type that is unsupported.
    @return: None
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
