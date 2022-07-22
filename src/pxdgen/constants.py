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

import re
import clang.cindex

kinds = clang.cindex.CursorKind
TAB_LENGTH = 4
TAB = ' ' * TAB_LENGTH
RE_DECLTYPE = re.compile("decltype\(.+\)")
RE_CPP_INCLUDE = re.compile(" *#include *[<\"].+\.h(pp)?[>\"] *")
RE_CPP_INT = re.compile("\d{1,20}")
RE_CPP_FLOAT = re.compile("\d+(\.\d+)?[fF]?")

SPACE_KINDS = (
    kinds.STRUCT_DECL,
    kinds.CLASS_DECL,
    kinds.CLASS_TEMPLATE,
    kinds.NAMESPACE
)
TEMPLATE_KINDS = (
    kinds.TEMPLATE_TYPE_PARAMETER,
    kinds.TEMPLATE_NON_TYPE_PARAMETER
)
FUNCTION_KINDS = (
    kinds.FUNCTION_DECL,
    kinds.FUNCTION_TEMPLATE,
    kinds.CXX_METHOD
)
METHOD_KINDS = (
    kinds.FUNCTION_TEMPLATE,
    kinds.CXX_METHOD
)
STATIC_FUNCTION_KINDS = (
    kinds.FUNCTION_DECL,
    kinds.FUNCTION_TEMPLATE
)
STRUCTURED_DATA_KINDS = (
    kinds.STRUCT_DECL,
    kinds.CLASS_DECL,
    kinds.CLASS_TEMPLATE
)
# Anything 100% able to be represented by the DataType class
BASIC_DATA_KINDS = (
    kinds.PARM_DECL,
    kinds.VAR_DECL,
    kinds.FIELD_DECL
)
ANON_KINDS = STRUCTURED_DATA_KINDS + (
    kinds.ENUM_DECL,
    kinds.UNION_DECL
)
TYPE_REFS = (
    kinds.TYPE_REF,
    kinds.TEMPLATE_REF
)
TYPEDEF_KINDS = (
    kinds.TYPEDEF_DECL,
    kinds.TYPE_ALIAS_DECL
)
IGNORED_IMPORTS = {
    "size_t",
    "ptrdiff_t",
    "wchar_t"
}
REPLACED_IMPORTS = {
    "std::size_t": "size_t"
}
STD_IMPORTS = {
    "lconv": "libc.locale",
    "jmp_buf": "libc.setjmp",
    "sigjmp_buf": "libc.setjmp",
    "sig_handler_t": "libc.signal",
    "sig_atomic_t": "libc.signal",
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
    "div_t": "libc.stdlib",
    "ldiv_t": "libc.stdlib",
    "lldiv_t": "libc.stdlib",
    "clock_t": "libc.time",
    "time_t": "libc.time",
    "tm": "libc.time",
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
    "std::pair": "libcpp.pair",  # Also in libcpp.utility
    "std::vector": "libcpp.vector"
}

del kinds
