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
import argparse
import sys
import os
import os.path
import glob

import clang.cindex

import pxdgen.utils
import pxdgen.utils.warning as warnings
from pxdgen.config import set_config, Setting
from pxdgen.utils import TypeResolver
from pxdgen.utils import TabWriter
from pxdgen.clang.namespaces import Namespace


FLAG_NOIMPORT = "noimport"
FLAG_AUTODEFINE = "autodefine"
FLAG_FORWARD_DECL = "emitfwdecl"
FLAG_AUTOIMPORT = "autoimport"


class PXDGen:
    def __init__(self, program_options: argparse.Namespace):
        """
        Main class for PxdGen supplementary script. CLI implementation.

        @param program_options: Options supplied to CLI.
        """
        if not program_options.directory and not os.path.isfile(program_options.header):
            exit("Unable to find input file '%s'" % program_options.header)

        if program_options.directory:
            if not program_options.output:
                exit("To use directory output mode, specify a directory output name with '-o'")
            if not os.path.isdir(program_options.header):
                exit("Unable to find input directory '%s'" % program_options.header)

            if not os.path.isdir(program_options.output):
                os.mkdir(program_options.output)

        if program_options.libs:
            clang.cindex.Config.set_library_path(program_options.libs)

        try:
            self.index = clang.cindex.Index.create()
        except Exception as e:
            exit("Clang error: %s" % e)

        clang_args = list()

        if program_options.include:
            for i in program_options.include:
                clang_args.append("-I")
                clang_args.append(i)

        if program_options.language:
            clang_args += ["-x", program_options.language]

        self.clang_args = clang_args
        self.opts = program_options
        self.flags = set(program_options.flags)
        
        if FLAG_FORWARD_DECL in self.flags:
            set_config(Setting.FORWARD_DECL)

        warnings.set_warning_level(program_options.warning_level)

    def run(self):
        """
        Run the program with parameters supplied in constructor.

        @return: None.
        """
        if self.opts.directory:
            self._run_directory()
        else:
            self._run_standard()

    def _run_standard(self):
        stream = sys.stdout if not self.opts.output else open(self.opts.output, 'w')
        abs_header = os.path.abspath(self.opts.header)
        valid_headers = {abs_header}
        tu = self.index.parse(self.opts.header, self.clang_args)
        resolver = TypeResolver(False)
        vld_ns = None

        if self.opts.recursive:
            if self.opts.headers:
                for glb in self.opts.headers:
                    valid_headers |= set([os.path.abspath(g) for g in glob.glob(glb)])
            else:
                valid_headers = None
            if self.opts.namespaces:
                vld_ns = self.opts.namespaces

        namespaces = pxdgen.utils.find_namespaces(tu.cursor, valid_headers, vld_ns, abs_header)
        namespaces[''] = [tu.cursor]

        for key, value in namespaces.items():
            ns = Namespace(value, key != '' or (self.opts.recursive and not self.opts.headers), key, os.path.relpath(self.opts.header), valid_headers)
            ns.process_types(resolver)
            namespaces[key] = ns

        self._process_namespaces(namespaces, resolver, stream)
        resolver.warn_unknown_types()
        stream.close()

    def _run_directory(self):
        resolver, spaces = self._preprocess_directory(self.opts.header)

        for cpp_space in spaces:
            with open(os.path.join(self.opts.output, cpp_space.replace("::", '.') + ".pxd"), 'w') as out:
                self._process_namespaces(spaces[cpp_space], resolver, out)
        resolver.warn_unknown_types()

    def _process_namespaces(self, namespaces: dict, resolver: TypeResolver, stream):
        writer = TabWriter()

        for namespace in namespaces.values():
            if namespace.has_declarations:
                writer.writeline(namespace.cython_namespace_header)
                writer.indent()

                for line in namespace.generate_declarations(resolver):
                    writer.writeline(line)

                writer.unindent()
                writer.writeline('\n')

        if resolver.imports and FLAG_NOIMPORT not in self.flags:
            stream.write("#  PXDGEN IMPORTS\n")
            stream.write('\n'.join(resolver.drain_imports()))
            stream.write('\n\n')
        if resolver.unknown_imports:
            if FLAG_AUTODEFINE in self.flags:
                stream.write("#  PXDGEN AUTO-DEFINED TYPES\n")
                stream.write("cdef extern from *:\n")
                for pt in resolver.drain_unknown_imports():
                    stream.write("    ctypedef struct %s:\n        pass\n" % pt.basename)
                stream.write("\n\n")
            elif FLAG_AUTOIMPORT in self.flags:
                stream.write("#  PXDGEN AUTO-IMPORTS\n")
                for pt in resolver.drain_unknown_imports():
                    stream.write(pt.import_string)

        stream.write(writer.getvalue())

    def _preprocess_directory(self, dirname: str) -> tuple:
        resolver = TypeResolver(True)
        all_spaces = dict()

        def _r(s):
            for handle in os.scandir(s):
                if handle.is_dir():
                    _r(handle.path)
                else:
                    if not handle.name.endswith(".h") and not handle.name.endswith(".hpp"):
                        continue
                    print(f"Pre-processing {handle.path}...")
                    main_header = os.path.abspath(handle.path)
                    tu = self.index.parse(handle.path, self.clang_args)
                    namespaces = pxdgen.utils.find_namespaces(tu.cursor, {main_header})
                    namespaces[''] = [tu.cursor]
                    for key, value in namespaces.items():
                        if key in all_spaces:
                            all_spaces[key][handle.path] = value
                        else:
                            all_spaces[key] = {handle.path:  value}
        _r(dirname)

        for cppath in all_spaces:
            print(f"Generating type info for namespace {cppath}")
            for header in all_spaces[cppath]:
                # (cursors, recursive, cpp_path, header_name, valid headers)
                ns = Namespace(
                    all_spaces[cppath][header],
                    False,
                    cppath,
                    os.path.relpath(header),
                    {os.path.abspath(header)}
                )
                all_spaces[cppath][header] = ns
                ns.process_types(resolver)

        return resolver, all_spaces


def main():
    """
    Entry point for PxdGen CLI.

    @return: None
    """
    args = sys.argv[1:]

    argp = argparse.ArgumentParser(description="Converts a C/C++ header file to a pxd file")
    argp.add_argument("header",
                        help="Path to C/C++ header or directory (if using -D) to parse")
    argp.add_argument("-o", "--output",
                        help="Path to output file or directory (defaults to stdout)")
    argp.add_argument("-r", "--recursive-includes",
                        action="store_true",
                        help="Include declarations from headers #included by the preprocessor",
                        dest="recursive")
    argp.add_argument("-x", "--language",
                      help="Force Clang to use the specified language for interpretation")
    argp.add_argument("-I", "--include",
                        action="append",
                        help="Add a directory to Clang's include path")
    argp.add_argument("-L", "--libclang-path",
                      dest="libs",
                      help="Specify the path to a directory containing libclang and its dependencies")
    argp.add_argument("-D", "--directory",
                      action="store_true",
                      help="Use pxdgen to parse a directory tree and set namespace output mode")
    argp.add_argument("-H", "--headers",
                      action="append",
                      default=[],
                      help="Whitelist specified headers with a glob term (for filtering -r)")
    argp.add_argument("-N", "--namespaces",
                      action="append",
                      default=[],
                      help="Whitelist specified namespaces with an fnmatch term (for filtering -r)")
    argp.add_argument("-W", "--warning-level",
                      type=int,
                      default=1,
                      help="Set the warning level of the current process")
    argp.add_argument("-f", "--flag",
                      action="append",
                      dest="flags",
                      default=[],
                      help="Set a flag to further tune the program output")

    opts = argp.parse_args(args)
    proc = PXDGen(opts)
    proc.run()
