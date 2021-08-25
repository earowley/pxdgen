struct Misc
{
    int a;
    float b;
    int (*c)(int d, float f);
};

typedef struct
{
    double google;
    long long bing;
    long (*ddg)(void);
} Search;

// Bug - C keyword in decls
struct baz_struct
{
    int foo_union;
    float (*baz_enum)(float);
}
typedef baz_struct bzs;
typedef baz_struct *pbzs;
