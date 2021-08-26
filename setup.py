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

from setuptools import setup


with open("./README.md", 'r') as file:
    long_d = file.read()


setup(
    name="pxdgen",
    version="1.0.1",
    url="https://github.com/earowley/pxdgen",
    py_modules=["_pxdgen"],
    packages=["pxdgen", "pxdgen.clang", "pxdgen.utils"],
    package_dir={
        "": "scripts",
        "pxdgen": "src/pxdgen"
    },
    entry_points={
        "console_scripts": ["pxdgen = _pxdgen:main"]
    },
    license="GNU GPLv3",
    author="Eric Rowley",
    author_email="earowley23@gmail.com",
    description="A tool for converting one or more C/C++ headers to Cython header files.",
    long_description=long_d,
    long_description_content_type="text/markdown",
    install_requires=[
        "clang",
        "colorama"
    ],
    python_requires="~=3.6"
)
