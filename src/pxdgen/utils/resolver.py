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

from typing import Generator


class TypeResolver:
    BUILTINS = {"void", "_Bool", "bool", "char",
                "short", "int", "long", "long long",
                "float", "double", "long double",
                "size_t", "ssize_t"
    }

    def __init__(self):
        self.c_imports = {
            "int8_t": "libc.stdint",
            "int16_t": "libc.stdint",
            "int32_t": "libc.stdint",
            "int64_t": "libc.stdint",
            "uint8_t": "libc.stdint",
            "uint16_t": "libc.stdint",
            "uint32_t": "libc.stdint",
            "uint64_t": "libc.stdint",
            "intptr_t": "libc.stdint",
            "uintptr_t": "libc.stdint",
            "intmax_t": "libc.stdint",
            "uintmax_t": "libc.stdint",
            "FILE": "libc.stdio",
            "fpos_t": "libc.stdio",
            "clock_t": "libc.time",
            "time_t": "libc.time"
        }
        self.cpp_imports = {
            "std::complex": "libcpp.complex",
            "std::deque": "libcpp.deque",
            "std::list": "libcpp.list",
            "std::map": "libcpp.map",
            "std::unique_ptr": "libcpp.memory",
            "std::shared_ptr": "libcpp.memory",
            "std::weak_ptr": "libcpp.memory",
            "std::queue": "libcpp.queue",
            "std::priority_queue": "libcpp.queue",
            "std::set": "libcpp.set",
            "std::multiset": "libcpp.multiset",
            "std::stack": "libcpp.stack",
            "std::string": "libcpp.string",
            "std::unordered_map": "libcpp.unordered_map",
            "std::unordered_set": "libcpp.unordered_set",
            "std::unordered_multiset": "libcpp.unordered_set",
            "std::pair": "libcpp.pair",  # Also libcpp.utility
            "std::vector": "libcpp.vector",
            "std::size_t": "$"  # $ corrects to 'size_t' but does not import the type
        }
        self.imports = set()
        self.known_types = dict()
        self.unknown_types = dict()
        self.unknown_imports = set()

    def add_user_defined_type(self, type_string: str, import_string: str):
        """
        Adds a type and necessary import information to the type repository.
        type_string should be the fully qualified C++ name, such as
        A::B::C
        """
        p_type = ProcessedType(type_string, import_string)

        try:
            self.unknown_types.pop(p_type)
        except KeyError:
            pass

        self.known_types[type_string] = p_type

    def process_type(self, type_string: str, current_namespace: str):
        """
        Check a type to see if it is an existing type or builtin type.
        If not, add it to undefined types.
        """
        possible_cpp_name = "::".join((current_namespace, type_string)) if current_namespace else type_string
        if type_string in TypeResolver.BUILTINS:
            return

        # Check global types and types relative to current namespace
        if type_string in self.known_types or possible_cpp_name in self.known_types:
            return

        # Check if it is available in C/C++ Cython stdlib
        try:
            cython_c_type = ProcessedType(type_string, self.c_imports.pop(type_string))
            self.known_types[type_string] = cython_c_type
            return
        except KeyError:
            pass

        try:
            cython_cpp_type = ProcessedType(type_string, self.cpp_imports.pop(type_string))
            self.known_types[type_string] = cython_cpp_type
            return
        except KeyError:
            pass

        self.unknown_types[type_string] = ProcessedType(type_string, '')

    def add_imports_from_types(self, types: list, current_namespace: str, import_path: str) -> list:
        """
        Given a list of strings containing type names, adds imports to the
        import repository. Imports are cleared and iterated via drain_imports.
        """
        ret = list()
        for type_string in types:
            if type_string in TypeResolver.BUILTINS:
                continue
            p_type = self.known_types.get(type_string, None)
            if p_type and p_type.package_path != import_path:
                if p_type.package_path != '$':
                    self.imports.add(p_type.import_string)
                ret.append((type_string, p_type.basename))
                continue
            p_type = self.known_types.get("::".join((current_namespace, type_string)), None)
            if p_type and p_type.package_path != import_path:
                if p_type.package_path != '$':
                    self.imports.add(p_type.import_string)
                ret.append((type_string, p_type.basename))
                continue
            p_type = self.unknown_types.get(type_string, None)
            if p_type:
                self.unknown_imports.add(p_type)

        return ret

    def drain_imports(self) -> Generator[str, None, None]:
        """
        Iterates and consumes imports.
        """
        while self.imports:
            yield self.imports.pop()

    def drain_unknown_imports(self):
        """
        Iterates and consumes unknown types.
        """
        while self.unknown_imports:
            yield self.unknown_imports.pop()

    def update(self) -> int:
        """
        Removes unknown types that are now known.
        Returns number of types resolved.
        """
        ret = 0
        for v in self.unknown_types:
            if v in self.known_types:
                self.unknown_types.pop(v)
                ret += 1

        return ret


class ProcessedType:
    def __init__(self, cpp_name: str, package_path: str):
        self.cpp_name = cpp_name
        self.package_path = package_path

    def __eq__(self, other):
        if isinstance(other, str):
            return other == self.cpp_name
        elif isinstance(other, ProcessedType):
            return other.cpp_name == self.cpp_name
        else:
            raise NotImplementedError("Unable to compare 'ProcessedType' to %s" % type(other))

    def __hash__(self):
        return hash(self.cpp_name)

    @property
    def basename(self):
        """
        Name of type without C++ path.
        """
        return self.cpp_name.rpartition("::")[-1]

    @property
    def import_string(self) -> str:
        """
        Cython import string
        """
        return "from %s cimport %s" % (self.package_path, self.basename)
