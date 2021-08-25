cimport time

def clock():
    return time.clock()

def time():
    return time.time(NULL)

def time_string():
    cdef time.time_t now = time.time(NULL)
    cdef char *ret_cstring = time.ctime(&now);

    # Do not need to free
    return (<bytes> ret_cstring).decode()

