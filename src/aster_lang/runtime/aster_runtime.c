#include "aster_runtime.h"

const AsterValue ASTER_NIL_VAL = { VAL_NIL, { .ptr = NULL } };

void aster_print(AsterValue v) {
    switch (v.kind) {
        case VAL_NIL:    printf("nil\n"); break;
        case VAL_BOOL:   printf("%s\n", v.as.boolean ? "true" : "false"); break;
        case VAL_INT:    printf("%" PRId64 "\n", v.as.integer); break;
        case VAL_FLOAT:  printf("%g\n", v.as.floating); break;
        case VAL_STRING: printf("%s\n", v.as.string ? v.as.string : ""); break;
        default:         printf("<unknown value kind %d>\n", v.kind); break;
    }
}

bool aster_truthy(AsterValue v) {
    switch (v.kind) {
        case VAL_NIL:    return false;
        case VAL_BOOL:   return v.as.boolean;
        case VAL_INT:    return v.as.integer != 0;
        case VAL_FLOAT:  return v.as.floating != 0.0;
        case VAL_STRING: return v.as.string != NULL && v.as.string[0] != '\0';
        default:         return true;
    }
}

void aster_panic(const char* message) {
    fprintf(stderr, "Aster Panic: %s\n", message);
    exit(1);
}

// Arithmetic
AsterValue aster_add(AsterValue a, AsterValue b) {
    if (a.kind == VAL_INT && b.kind == VAL_INT)
        return aster_int(a.as.integer + b.as.integer);
    if (a.kind == VAL_FLOAT || b.kind == VAL_FLOAT) {
        double va = (a.kind == VAL_FLOAT) ? a.as.floating : (double)a.as.integer;
        double vb = (b.kind == VAL_FLOAT) ? b.as.floating : (double)b.as.integer;
        return aster_float(va + vb);
    }
    if (a.kind == VAL_STRING && b.kind == VAL_STRING) {
        return aster_concat(a, b);
    }
    aster_panic("Type error: addition requires numbers or strings");
    return ASTER_NIL_VAL;
}

AsterValue aster_concat(AsterValue a, AsterValue b) {
    if (a.kind != VAL_STRING || b.kind != VAL_STRING) {
        aster_panic("Type error: concatenation requires strings");
    }
    const char* s1 = a.as.string ? a.as.string : "";
    const char* s2 = b.as.string ? b.as.string : "";
    size_t len1 = strlen(s1);
    size_t len2 = strlen(s2);
    char* res = (char*)malloc(len1 + len2 + 1);
    if (!res) aster_panic("Out of memory");
    memcpy(res, s1, len1);
    memcpy(res + len1, s2, len2);
    res[len1 + len2] = '\0';
    return aster_string(res);
}

AsterValue aster_sub(AsterValue a, AsterValue b) {
    if (a.kind == VAL_INT && b.kind == VAL_INT)
        return aster_int(a.as.integer - b.as.integer);
    // ... float support can be expanded later
    return aster_int(a.as.integer - b.as.integer);
}

AsterValue aster_mul(AsterValue a, AsterValue b) {
    return aster_int(a.as.integer * b.as.integer);
}

AsterValue aster_div(AsterValue a, AsterValue b) {
    if (b.as.integer == 0) aster_panic("Division by zero");
    return aster_int(a.as.integer / b.as.integer);
}

AsterValue aster_mod(AsterValue a, AsterValue b) {
    if (b.as.integer == 0) aster_panic("Division by zero");
    return aster_int(a.as.integer % b.as.integer);
}

AsterValue aster_neg(AsterValue a) {
    if (a.kind == VAL_INT) return aster_int(-a.as.integer);
    if (a.kind == VAL_FLOAT) return aster_float(-a.as.floating);
    aster_panic("Type error: negation requires a number");
    return ASTER_NIL_VAL;
}

// Comparisons
AsterValue aster_eq(AsterValue a, AsterValue b) {
    if (a.kind != b.kind) return aster_bool(false);
    switch (a.kind) {
        case VAL_NIL:    return aster_bool(true);
        case VAL_BOOL:   return aster_bool(a.as.boolean == b.as.boolean);
        case VAL_INT:    return aster_bool(a.as.integer == b.as.integer);
        case VAL_FLOAT:  return aster_bool(a.as.floating == b.as.floating);
        case VAL_STRING: return aster_bool(strcmp(a.as.string, b.as.string) == 0);
        default:         return aster_bool(false);
    }
}

AsterValue aster_ne(AsterValue a, AsterValue b) {
    return aster_bool(!aster_truthy(aster_eq(a, b)));
}

AsterValue aster_lt(AsterValue a, AsterValue b) {
    return aster_bool(a.as.integer < b.as.integer);
}

AsterValue aster_gt(AsterValue a, AsterValue b) {
    return aster_bool(a.as.integer > b.as.integer);
}

AsterValue aster_le(AsterValue a, AsterValue b) {
    return aster_bool(a.as.integer <= b.as.integer);
}

AsterValue aster_ge(AsterValue a, AsterValue b) {
    return aster_bool(a.as.integer >= b.as.integer);
}

// Logical
AsterValue aster_and(AsterValue a, AsterValue b) {
    return aster_bool(aster_truthy(a) && aster_truthy(b));
}

AsterValue aster_or(AsterValue a, AsterValue b) {
    return aster_bool(aster_truthy(a) || aster_truthy(b));
}

AsterValue aster_not(AsterValue a) {
    return aster_bool(!aster_truthy(a));
}
