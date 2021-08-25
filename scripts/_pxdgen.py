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

import argparse
import sys
import os
import os.path
import clang.cindex
import pxdgen.utils
import pxdgen.utils.settings
import glob
from pxdgen.utils import TypeResolver
from pxdgen.utils import TabWriter
from pxdgen.clang.namespaces import Namespace


class PXDGen:
    def __init__(self, program_options: argparse.Namespace):
        if not program_options.directory and not os.path.isfile(program_options.header):
            exit("Unable to find input file '%s'" % program_options.header)

        if program_options.directory:
            if not program_options.output:
                exit("To use directory output mode, specify a directory output name with '-o'")
            if not os.path.isdir(program_options.header):
                exit("Unable to find input directory %s" % program_options.header)

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

    def run(self):
        if self.opts.directory:
            self._run_directory()
        else:
            self._run_standard()

    def _run_standard(self):
        stream = sys.stdout if not self.opts.output else open(self.opts.output, 'w')
        valid_headers = {os.path.basename(self.opts.header)}
        tu = self.index.parse(self.opts.header, self.clang_args)
        namespaces = pxdgen.utils.find_namespaces(tu.cursor)
        namespaces[''] = [tu.cursor]
        resolver = TypeResolver()

        if self.opts.recursive and self.opts.headers:
            valid_headers |= {os.path.basename(g) for g in glob.glob(self.opts.headers)}

        for key, value in namespaces.items():
            namespaces[key] = Namespace(value, self.opts.recursive and not self.opts.headers, key, os.path.basename(self.opts.header), valid_headers)

        for namespace in namespaces.values():
            namespace.process_types(resolver)

        PXDGen._process_namespaces(namespaces, resolver, stream)
        stream.close()

    def _run_directory(self):
        self.base_import_dir = os.path.join(self.opts.header, "..")
        resolver = self._get_directory_resolver(self.opts.header)
        self._process_directory(self.opts.header, resolver)

    def _process_directory(self, dirname: str, resolver: TypeResolver):
        def _r(d):
            for handle in os.scandir(d):
                if handle.is_dir():
                    _r(handle.path)
                else:
                    if not handle.name.endswith(".h") and not handle.name.endswith(".hpp"):
                        continue
                    self._process_file(handle.path, resolver)
        _r(dirname)

    def _process_file(self, input_file: str, resolver: TypeResolver):
        tu = self.index.parse(input_file, self.clang_args)
        namespaces = pxdgen.utils.find_namespaces(tu.cursor)
        namespaces[''] = [tu.cursor]
        rip = self._rel_import_path(input_file)
        output_file = os.path.join(self.opts.output, rip[:rip.rindex('.')] + ".pxd")
        import_path = rip[:rip.rindex(".h")].replace(os.path.sep, '.')
        out_dir = os.path.dirname(output_file)

        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)

        stream = open(output_file, 'w')

        for key, value in namespaces.items():
            namespaces[key] = Namespace(value, False, key, rip, {os.path.basename(input_file)}, package_path=import_path)

        PXDGen._process_namespaces(namespaces, resolver, stream)
        stream.close()

    @staticmethod
    def _process_namespaces(namespaces: dict, resolver: TypeResolver, stream):
        writer = TabWriter()
        flags = pxdgen.utils.settings.FLAGS

        for namespace in namespaces.values():
            if namespace.has_declarations:
                writer.writeline(namespace.cython_namespace_header)
                writer.indent()

                for line in namespace.generate_declarations(resolver):
                    writer.writeline(line)

                writer.unindent()
                writer.writeline('\n')

        if resolver.imports and not flags["noimport"]:
            stream.write("#  PXDGEN IMPORTS\n")
            stream.write('\n'.join(resolver.drain_imports()))
            stream.write('\n\n')
        if resolver.unknown_imports and flags["autodefine"]:
            stream.write("#  PXDGEN AUTO-DEFINED TYPES\n")
            stream.write("cdef extern from *:\n")
            for pt in resolver.drain_unknown_imports():
                stream.write("    ctypedef struct %s:\n        pass\n" % pt.basename)
            stream.write("\n\n")

        stream.write(writer.getvalue())

    def _get_directory_resolver(self, dirname: str) -> TypeResolver:
        resolver = TypeResolver()

        def _r(s):
            for handle in os.scandir(s):
                if handle.is_dir():
                    _r(handle.path)
                else:
                    if not handle.name.endswith(".h") and not handle.name.endswith(".hpp"):
                        continue
                    tu = self.index.parse(handle.path, self.clang_args)
                    namespaces = pxdgen.utils.find_namespaces(tu.cursor)
                    namespaces[''] = [tu.cursor]
                    rip = self._rel_import_path(handle.path)
                    for key, value in namespaces.items():
                        # (cursors, recursive, cpp_path, header_name,
                        namespaces[key] = Namespace(value, False, key, rip, {os.path.basename(handle.path)}, package_path=rip[:rip.rindex(".h")].replace(os.path.sep, '.'))
                    for namespace in namespaces.values():
                        namespace.process_types(resolver)
        _r(dirname)

        return resolver

    def _rel_import_path(self, abspath: str) -> str:
        return os.path.relpath(abspath, self.base_import_dir)


def main():
    args = sys.argv[1:]

    argp = argparse.ArgumentParser(description="Converts a C/C++ header file to a pxd file")
    argp.add_argument("header",
                        help="Path to C/C++ header or directory file to parse")
    argp.add_argument("-o", "--output",
                        help="Path to output file or directory, if any")
    argp.add_argument("-r", "--recursive-includes",
                        action="store_true",
                        help="Include declarations from other included headers",
                        dest="recursive")
    argp.add_argument("-I", "--include",
                        action="append",
                        help="Add a directory to Clang's include path")
    argp.add_argument("-H", "--headers",
                      help="Specify a glob term to identify valid headers to parse")
    argp.add_argument("-W", "--warning-level",
                      type=int,
                      default=1,
                      help="Flag to set the warning level of the current run")
    argp.add_argument("-L", "--libclang-path",
                      dest="libs",
                      help="Specify a path to a directory containing libclang and its dependencies")
    argp.add_argument("-x", "--language",
                      help="Force Clang to use the specified language for interpretation, such as 'c++'")
    argp.add_argument("-D", "--directory",
                      action="store_true",
                      help="Use pxdgen to parse a directory tree")
    argp.add_argument("-f", "--flag",
                      action="append",
                      dest="flags",
                      default=[],
                      help="Set a pxdgen flag to further tune the program output")

    opts = argp.parse_args(args)
    for flag in opts.flags:
        pxdgen.utils.settings.FLAGS[flag] = True
    pxdgen.utils.settings.WARNING_LEVEL = opts.warning_level
    proc = PXDGen(opts)
    proc.run()
