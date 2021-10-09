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
from . import warning


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

    @staticmethod
    def _iter_parent_namespaces(low: str) -> Generator[str, None, None]:
        yield low
        sep = low.rfind("::")

        while sep != -1:
            low = low[:sep]
            sep = low.rfind("::")
            yield low

    def add_user_defined_type(self, type_string: str):
        """
        Adds a type and necessary import information to the type repository.

        @param type_string: fully qualified C++ name, such as 'A::B::C'.
        @return: None
        """
        p_type = ProcessedType(type_string)
        self.known_types[type_string] = p_type

    def process_type(self, type_string: str, current_namespace: str):
        """
        Check a type to see if it is an existing type or builtin type.
        If not, add it to undefined types.

        @param type_string: Type string to check.
        @param current_namespace: The current namespace being parsed. Used to check local references.
        @return: None
        """
        if type_string in TypeResolver.BUILTINS or type_string in self.known_types:
            return

        # Check global types and types relative to current namespace
        if current_namespace and (type_string in self.known_types or
                                  any("::".join((ns, type_string)) in self.known_types for ns in TypeResolver._iter_parent_namespaces(current_namespace))):
            return

        # Check if it is available in C/C++ Cython stdlib
        try:
            cython_c_type = ProcessedType(type_string, path_override=self.c_imports.pop(type_string))
            self.known_types[type_string] = cython_c_type
            return
        except KeyError:
            pass

        try:
            cython_cpp_type = ProcessedType(type_string, path_override=self.cpp_imports.pop(type_string))
            self.known_types[type_string] = cython_cpp_type
            return
        except KeyError:
            pass

        self.unknown_types[type_string] = ProcessedType(type_string, '')

    def add_imports_from_types(self, types: list, current_namespace: str) -> list:
        """
        Given a list of strings containing type names, adds necessary imports to the
        import repository. Imports are cleared and iterated via drain_imports.

        @param types: List of type strings.
        @param current_namespace: The current C++ namespace being parsed.
        @return: List of tuples containing (old,new) type strings, where new is valid after import.
        """
        # Package paths for which imports are ignored
        IGNORE_IMPORTS = ('$',)
        ret = list()
        for type_string in types:
            if type_string in TypeResolver.BUILTINS:
                continue
            p_type = self.known_types.get(type_string, None)
            if p_type:
                if p_type.package_path not in IGNORE_IMPORTS and p_type.cpp_space != current_namespace:
                    self.imports.add(p_type.import_string)
                    ret.append((type_string, p_type.import_name))
                else:
                    ret.append((type_string, p_type.basename))
                continue
            if current_namespace:
                for ns in TypeResolver._iter_parent_namespaces(current_namespace):
                    p_type = self.known_types.get("::".join((ns, type_string)), None)
                    if p_type is not None:
                        break
                if p_type:
                    if p_type.package_path not in IGNORE_IMPORTS and p_type.cpp_space != current_namespace:
                        self.imports.add(p_type.import_string)
                        ret.append((type_string, p_type.import_name))
                    else:
                        ret.append((type_string, p_type.basename))
                    continue
            p_type = self.unknown_types.get(type_string, None)
            assert p_type is not None, "Type %s is not known or unknown" % type_string
            self.unknown_imports.add(p_type)
            unk_fallback = type_string
            if current_namespace:
                unk_fallback = unk_fallback.replace("%s::" % current_namespace, '')
            ret.append((type_string, unk_fallback.replace("::", '.')))

        return ret

    def drain_imports(self) -> Generator[str, None, None]:
        """
        Destructively iterates over import strings in repository.

        @return: Generator[str].
        """
        while self.imports:
            yield self.imports.pop()

    def drain_unknown_imports(self) -> Generator[str, None, None]:
        """
        Destructively iterates over unknown import strings in repository.

        @return: Generator[str].
        """
        while self.unknown_imports:
            yield self.unknown_imports.pop()

    def update(self) -> int:
        """
        Removes unknown types that are now known.

        @return: Number of types resolved.
        """
        ret = 0
        for v in self.unknown_types:
            if v in self.known_types:
                self.unknown_types.pop(v)
                ret += 1

        return ret

    def warn_unknown_types(self):
        """
        Warns of unknown types at warning level 1.

        @return: None
        """
        for ut in self.unknown_types:
            warning.warn("Unresolved type: %s" % ut)


class ProcessedType:
    def __init__(self, cpp_name: str, *_, path_override: str = ''):
        self.cpp_name = cpp_name
        parts = cpp_name.split("::")
        self._basename = parts[-1]
        self.package_path = path_override if path_override else '.'.join(parts[:-1])
        self.cpp_space = "::".join(parts[:-1])
        self.import_name = self.cpp_name.replace("::", '_')

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
        return self._basename

    @property
    def import_string(self) -> str:
        """
        Cython import string
        """
        return "from %s cimport %s as %s" % (self.package_path, self.basename, self.import_name)
