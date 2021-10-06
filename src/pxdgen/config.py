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

from __future__ import annotations
from enum import IntEnum


class Setting(IntEnum):
    FORWARD_DECL = 0
    

_pxdgen_config = [
    False, # Forward Decl
]


def set_config(setting: Setting, value: Any):
    _pxdgen_config[setting] = value
    
    
def get_config(setting: Setting) -> Any:
    return _pxdgen_config[setting]
