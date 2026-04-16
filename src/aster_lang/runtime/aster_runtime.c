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

// List operations
AsterValue aster_list_new(void) {
    struct AsterList* list = (struct AsterList*)malloc(sizeof(struct AsterList));
    if (!list) aster_panic("Out of memory");
    list->data = NULL;
    list->size = 0;
    list->capacity = 0;
    AsterValue v; v.kind = VAL_LIST; v.as.list = list; return v;
}

AsterValue aster_list_append(AsterValue list_val, AsterValue item) {
    if (list_val.kind != VAL_LIST) aster_panic("Type error: append requires list");
    struct AsterList* list = list_val.as.list;
    if (list->size == list->capacity) {
        list->capacity = list->capacity == 0 ? 8 : list->capacity * 2;
        list->data = (AsterValue*)realloc(list->data, list->capacity * sizeof(AsterValue));
        if (!list->data) aster_panic("Out of memory");
    }
    list->data[list->size++] = item;
    return list_val;
}

AsterValue aster_list_get(AsterValue list_val, AsterValue index) {
    if (list_val.kind != VAL_LIST) aster_panic("Type error: list get requires list");
    if (index.kind != VAL_INT) aster_panic("Type error: list index requires int");
    struct AsterList* list = list_val.as.list;
    if (index.as.integer < 0 || (size_t)index.as.integer >= list->size) {
        aster_panic("Index out of bounds");
    }
    return list->data[index.as.integer];
}

size_t aster_list_len(AsterValue list_val) {
    if (list_val.kind != VAL_LIST) aster_panic("Type error: list len requires list");
    return list_val.as.list->size;
}

// Record operations
AsterValue aster_record_new(void) {
    struct AsterRecord* rec = (struct AsterRecord*)malloc(sizeof(struct AsterRecord));
    if (!rec) aster_panic("Out of memory");
    rec->keys = NULL;
    rec->values = NULL;
    rec->size = 0;
    AsterValue v; v.kind = VAL_RECORD; v.as.record = rec; return v;
}

AsterValue aster_record_set(AsterValue rec_val, const char* key, AsterValue value) {
    if (rec_val.kind != VAL_RECORD) aster_panic("Type error: set requires record");
    struct AsterRecord* rec = rec_val.as.record;
    
    // Check for existing key
    for (size_t i = 0; i < rec->size; i++) {
        if (strcmp(rec->keys[i], key) == 0) {
            rec->values[i] = value;
            return rec_val;
        }
    }
    
    // Grow
    rec->keys = (const char**)realloc(rec->keys, (rec->size + 1) * sizeof(const char*));
    rec->values = (AsterValue*)realloc(rec->values, (rec->size + 1) * sizeof(AsterValue));
    if (!rec->keys || !rec->values) aster_panic("Out of memory");
    
    rec->keys[rec->size] = key;
    rec->values[rec->size] = value;
    rec->size++;
    return rec_val;
}

AsterValue aster_record_get(AsterValue rec_val, const char* key) {
    if (rec_val.kind != VAL_RECORD) aster_panic("Type error: get requires record");
    struct AsterRecord* rec = rec_val.as.record;
    for (size_t i = 0; i < rec->size; i++) {
        if (strcmp(rec->keys[i], key) == 0) {
            return rec->values[i];
        }
    }
    aster_panic("Key not found");
    return ASTER_NIL_VAL;
}
