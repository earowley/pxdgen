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

import io


class TabWriter(io.StringIO):
    def __init__(self, *args, tabs: int = 0, **kwargs):
        super().__init__(*args, **kwargs)
        self.tabs = tabs

    def write(self, value: str) -> int:
        return super().write(' ' * (self.tabs * 4)) + super().write(value)

    def writeline(self, value: str) -> int:
        return self.write(value + '\n')

    def indent(self):
        self.tabs += 1

    def unindent(self):
        if self.tabs > 0:
            self.tabs -= 1

    def __del__(self):
        super().close()
