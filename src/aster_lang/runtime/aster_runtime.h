#ifndef ASTER_RUNTIME_H
#define ASTER_RUNTIME_H

#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef enum {
    VAL_NIL,
    VAL_BOOL,
    VAL_INT,
    VAL_FLOAT,
    VAL_STRING,
    VAL_LIST,
    VAL_RECORD,
    VAL_FN,
    VAL_ERROR
} AsterValueKind;

typedef struct {
    AsterValueKind kind;
    union {
        bool boolean;
        int64_t integer;
        double floating;
        const char* string;
        struct AsterList* list;
        // Pointers for more complex types will be added later
        void* ptr;
    } as;
} AsterValue;

struct AsterList {
    AsterValue* data;
    size_t size;
    size_t capacity;
};

// Constructors
static inline AsterValue aster_nil(void) {
    AsterValue v; v.kind = VAL_NIL; v.as.ptr = NULL; return v;
}
static inline AsterValue aster_bool(bool b) {
    AsterValue v; v.kind = VAL_BOOL; v.as.boolean = b; return v;
}
static inline AsterValue aster_int(int64_t i) {
    AsterValue v; v.kind = VAL_INT; v.as.integer = i; return v;
}
static inline AsterValue aster_float(double f) {
    AsterValue v; v.kind = VAL_FLOAT; v.as.floating = f; return v;
}
static inline AsterValue aster_string(const char* s) {
    AsterValue v; v.kind = VAL_STRING; v.as.string = s; return v;
}
AsterValue aster_list_new(void);

// Global constants
extern const AsterValue ASTER_NIL_VAL;

// Runtime functions
void aster_print(AsterValue v);
bool aster_truthy(AsterValue v);
void aster_panic(const char* message);

// List operations
AsterValue aster_list_append(AsterValue list, AsterValue item);
AsterValue aster_list_get(AsterValue list, AsterValue index);
size_t aster_list_len(AsterValue list);

// Arithmetic
AsterValue aster_add(AsterValue a, AsterValue b);
AsterValue aster_concat(AsterValue a, AsterValue b);
AsterValue aster_sub(AsterValue a, AsterValue b);
AsterValue aster_mul(AsterValue a, AsterValue b);
AsterValue aster_div(AsterValue a, AsterValue b);
AsterValue aster_mod(AsterValue a, AsterValue b);
AsterValue aster_neg(AsterValue a);

// Comparisons
AsterValue aster_eq(AsterValue a, AsterValue b);
AsterValue aster_ne(AsterValue a, AsterValue b);
AsterValue aster_lt(AsterValue a, AsterValue b);
AsterValue aster_gt(AsterValue a, AsterValue b);
AsterValue aster_le(AsterValue a, AsterValue b);
AsterValue aster_ge(AsterValue a, AsterValue b);

// Logical
AsterValue aster_and(AsterValue a, AsterValue b);
AsterValue aster_or(AsterValue a, AsterValue b);
AsterValue aster_not(AsterValue a);

#endif // ASTER_RUNTIME_H
