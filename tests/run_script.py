import sys
import os
sys.path.append("../scripts")
sys.path.append("../src")
from _pxdgen import PXDGen


TEST = "./cplusplus.hpp"


class Dummy:
    pass


if __name__ == "__main__":
    opts = Dummy()
    opts.header = TEST
    opts.output = './output'
    opts.relpath = ""
    opts.recursive = False
    opts.headers = list()
    opts.language = ''
    opts.include = []
    opts.libs = ''
    opts.verbose = True
    opts.flags = []

    PXDGen(opts).run()
