cimport stdlib
cimport time

def rand():
    return stdlib.rand()

stdlib.srand(time.time(NULL))
