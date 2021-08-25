float sqrt(float number);
void print(const char *s);
void exec(void (*fptr)(int code));
int sum(int data[], size_t len);

// Bug - put C keyword in declarations
int struct_func(int (*not_an_enum)(void));
