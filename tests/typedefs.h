typedef int Foo;
typedef void (*ACTION)(void *data);
typedef struct _bar
{
    int i;
} Bar;
typedef enum _baz
{
    FOO,
    BAR,
    BAZ
} Baz;

// Bug - C keyword in decl
enum bad_enum
{
    GOOD,
    BAD,
    UGLY
};
