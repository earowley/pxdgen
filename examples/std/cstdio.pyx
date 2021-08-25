cimport stdio
from stdlib cimport malloc, free

def puts(str s):
    cdef bytes pybytes = s.encode("UTF-8")
    stdio.puts(<char*> pybytes)

def getline():
    cdef char *buffer = NULL
    cdef size_t buffsize = 0

    cdef ssize_t chars = <ssize_t> stdio.getline(&buffer, &buffsize, stdio.stdin)
    
    try:
        return buffer[:chars].decode("UTF-8")
    finally:
        free(buffer)

