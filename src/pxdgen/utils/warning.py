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
