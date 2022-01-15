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
import pxdgen.utils as utils
from pxdgen.utils import TabWriter
import pxdgen.utils.warning as warnings
from pxdgen.cursors import Namespace


class PXDGen:
    def __init__(self, program_options: argparse.Namespace):
        """
        Main class for PxdGen supplementary script. CLI implementation.

        @param program_options: Options supplied to CLI.
        """
        dir_mode = os.path.isdir(program_options.header)
        file_mode = os.path.isfile(program_options.header)
        relpath = program_options.relpath or os.getcwd()

        if not dir_mode and not file_mode:
            exit(f"Unable to find input '{program_options.header}' on the file system")

        if not os.path.isdir(relpath):
            exit(f"Unable to find working directory {relpath}")

        if dir_mode and not program_options.output:
            request = input("Detected directory without an output location, are you sure you want to print the results to stdout? [y/n]")

            if request.lower() != 'y':
                exit("Use the `-o` flag to specify an output directory")

        if not os.path.isdir(program_options.output):
            os.mkdir(program_options.output)

        if program_options.libs:
            clang.cindex.Config.set_library_path(program_options.libs)

        try:
            self.index = clang.cindex.Index.create()
        except Exception as e:
            exit(f"Error with libclang: {e}")

        clang_args = list()

        if program_options.include:
            for i in program_options.include:
                clang_args.append("-I")
                clang_args.append(i)

        if program_options.language:
            clang_args += ["-x", program_options.language]

        self.clang_args = clang_args
        self.opts = program_options
        self.dir_mode = dir_mode
        self.file_mode = file_mode
        self.relpath = relpath
        self.flags = set(program_options.flags)

        warnings.set_warning_level(program_options.warning_level)

    def run(self):
        """
        Run the program with parameters supplied in constructor.

        @return: None.
        """
        to_parse = list()

        if self.file_mode:
            to_parse.append(os.path.abspath(self.opts.header))
        elif self.dir_mode:
            for header in ("**/*.h", "**/*.hpp"):
                for gt in glob.glob(os.path.join(self.opts.header, header), recursive=True):
                    to_parse.append(os.path.abspath(gt))

        valid_headers = set(to_parse)

        for gt in self.opts.headers:
            for file in glob.glob(gt):
                valid_headers.add(os.path.abspath(file))

        ctx = dict()

        for file in to_parse:
            tu = self.index.parse(file, self.clang_args)
            namespaces = utils.find_namespaces(tu.cursor, valid_headers)

            for space_name, cursors in namespaces.items():
                imports, fwd, body = ctx.get(space_name, (set(), TabWriter(), TabWriter()))
                pxspace = Namespace(cursors, self.opts.recursive, valid_headers)

                for i in pxspace.import_strings:
                    imports.add(i)

                if not fwd.tell():
                    fwd.writeline("cdef extern from *:")
                    fwd.indent()

                for decl in pxspace.forward_decls:
                    fwd.writeline(decl.cython_header(False))
                    fwd.indent()
                    fwd.writeline("pass\n")
                    fwd.unindent()

                body.writeline(pxspace.cython_header(os.path.relpath(file, self.opts.relpath)))
                body.indent()

                for line in pxspace.members():
                    body.writeline(line)

                body.unindent()
                body.writeline('')
                ctx[space_name] = (imports, fwd, body)

        for space_name in ctx:
            imports, fwd, body = ctx[space_name]

            if self.opts.output:
                out_path = os.path.join(self.opts.output, space_name.replace("::", os.path.sep))

                if not os.path.isdir(out_path):
                    os.makedirs(out_path)

                stream = open(os.path.join(out_path, "__init__.pxd"), 'w')
            else:
                stream = sys.stdout

            for i in imports:
                stream.write(i)
                stream.write('\n')

            stream.write('\n')
            stream.write(fwd.getvalue())
            stream.write('\n')
            stream.write(body.getvalue())
            stream.write('\n')


def main():
    """
    Entry point for PxdGen CLI.

    @return: None
    """
    args = sys.argv[1:]

    argp = argparse.ArgumentParser(description="A tool that converts C/C++ headers to pxd files")
    argp.add_argument("header",
                      help="Path to C/C++ header file or project directory to parse")
    argp.add_argument("-o", "--output",
                      help="Path to output file or directory (defaults to stdout)")
    argp.add_argument("-p", "--relpath",
                      help="Relative path to parse from (defaults to pwd)")
    argp.add_argument("-r", "--recursive",
                      action="store_true",
                      help="Include declarations from all nested headers")
    argp.add_argument("-H", "--headers",
                      action="append",
                      default=[],
                      help="A glob term of headers to include from")
    argp.add_argument("-x", "--language",
                      help="Force Clang to use the specified language for interpretation")
    argp.add_argument("-I", "--include",
                      action="append",
                      help="Add a directory to Clang's include path")
    argp.add_argument("-L", "--libclang-path",
                      dest="libs",
                      help="Specify the path to a directory containing libclang and its dependencies")
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
