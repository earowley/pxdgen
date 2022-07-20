import unittest
from os import chdir, getcwd, unlink
from os.path import join, isfile
from argparse import Namespace
from subprocess import getstatusoutput
from configparser import ConfigParser
from typing import List, Tuple
from _pxdgen import PxdGen


TEST_CODE = """{}
cdef extern from "<stdio.h>":
    int puts(const char* s)

def foo():
    puts("Hello world!")
"""


def cythonize(base: str, imports: List[str], use_cpp: bool = False) -> Tuple[int, str]:
    save = getcwd()
    imports = '\n'.join(f"from {i} cimport *" for i in imports)
    cython = TEST_CODE.format(imports)
    chdir(join('.', "output", base))

    if use_cpp:
        cython = "# distutils: language = c++\n\n" + cython

    try:
        with open("test.pyx", 'w') as file:
            file.write(cython)
        return getstatusoutput("cythonize test.pyx --3str")
    finally:
        if isfile("test.pyx"):
            unlink("test.pyx")
        if isfile("test.c"):
            unlink("test.c")
        chdir(save)


class TestHeaders(unittest.TestCase):
    def setUp(self):
        cfg = ConfigParser()
        cfg.read("configuration.ini")
        print(cfg["Clang"]["include"])
        opts = Namespace()
        opts.header = ''
        opts.output = ''
        opts.relpath = ""
        opts.recursive = False
        opts.language = ''
        opts.include = [cfg["Clang"]["include"]]
        opts.libs = cfg["Clang"]["library"]
        opts.verbose = True
        opts.flags = []
        self.opts = opts

    def test_basic_cplusplus(self):
        self.opts.header = "./cplusplus.hpp"
        self.opts.output = "./output/cplusplus"
        self.opts.language = "c++"
        self.opts.flags.append("defines")
        PxdGen(self.opts).run()
        rc, out = cythonize("cplusplus", ["Foo", "Bar", "Bar.Baz"], True)
        print(out)
        self.assertEqual(0, rc)

    def test_gzip(self):
        self.opts.relpath = "./gzip/include"
        self.opts.include.append("./gzip/include")
        self.opts.header = "./gzip/include/gzip"
        self.opts.output = "./output/gzip"
        self.opts.language = "c++"
        PxdGen(self.opts).run()
        rc, out = cythonize("gzip", ["gzip"], True)
        print(out)
        self.assertEqual(0, rc)

    def test_cxml(self):
        self.opts.relpath = "./cxml"
        self.opts.include.append("./cxml")
        self.opts.header = "./cxml/cxml/cxml.h"
        self.opts.output = "./output/cxml"
        self.opts.recursive = True
        PxdGen(self.opts).run()
        rc, out = cythonize("cxml", ["cxml"])
        print(out)
        self.assertEqual(0, rc)


if __name__ == "__main__":
    unittest.main()
