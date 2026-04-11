from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class Op(Enum):
    CONST = auto()  # push constants[arg]
    LOAD = auto()  # push locals[arg]
    STORE = auto()  # locals[arg] = pop()
    POP = auto()  # pop()

    # Closure support
    REF_LOCAL = auto()  # arg=slot:int, push a reference (cell) to locals[slot]
    REF_FREE = auto()  # arg=slot:int, push a reference (cell) to free[slot]
    REF_GLOBAL = auto()  # arg=name_const_index, push a reference (cell) to globals[name]
    LOAD_FREE = auto()  # arg=slot:int, push free[slot].value
    STORE_FREE = auto()  # arg=slot:int, free[slot].value = pop()
    # arg=(fn_id_const_index, free_count); pop N cell refs, push a closure value
    MAKE_CLOSURE = auto()

    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()

    NEG = auto()
    NOT = auto()

    EQ = auto()
    NE = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()

    JMP = auto()  # ip = arg
    JMP_IF_FALSE = auto()  # if not pop(): ip = arg

    CALL = auto()  # call by name: arg=(name_const_index, argc)
    CALL_VALUE = auto()  # pop callee, call with argc args; callee is a fn id string or closure
    RETURN = auto()  # return pop()

    BUILD_LIST = auto()  # arg=count, pop N values, push list
    BUILD_TUPLE = auto()  # arg=count, pop N values, push tuple
    BUILD_RECORD = auto()  # arg=tuple[field_name], pop N values, push dict
    INDEX = auto()  # pop index, pop obj, push obj[index]
    MEMBER = auto()  # pop obj, push obj[field_name]

    IS_LIST = auto()  # pop obj, push bool
    IS_TUPLE = auto()  # pop obj, push bool
    IS_RECORD = auto()  # pop obj, push bool
    LEN = auto()  # pop obj, push int
    HAS_KEY = auto()  # arg=key_const_index, pop obj, push bool
    SLICE_FROM = auto()  # arg=start:int, pop obj, push obj[start:]

    LOAD_GLOBAL = auto()  # arg=name_const_index, push globals[name]
    STORE_GLOBAL = auto()  # arg=name_const_index, globals[name] = pop()
    IMPORT_MODULE = auto()  # arg=module_label_const_index, push module exports dict
    # Assignment targets: copy-update-store back into the identifier binding.
    # SET_INDEX arg=("local", slot:int) or ("global", name_const:int); pops value, index.
    SET_INDEX = auto()
    # SET_MEMBER arg=(key_const:int, "local"/"global", slot:int or name_const:int); pops value.
    SET_MEMBER = auto()


@dataclass(slots=True, frozen=True)
class Instr:
    op: Op
    arg: object | None = None


@dataclass(slots=True, frozen=True)
class BCFunction:
    name: str
    params: tuple[str, ...]
    code: tuple[Instr, ...]
    local_count: int


@dataclass(slots=True, frozen=True)
class BCModule:
    constants: tuple[object, ...]
    functions: dict[str, BCFunction]


@dataclass(slots=True, frozen=True)
class ModuleSpec:
    label: str
    init_fn: str
    exports: dict[str, tuple[str, str]]  # export_name -> ("fn"|"var", value)


@dataclass(slots=True, frozen=True)
class BCProgram:
    constants: tuple[object, ...]
    functions: dict[str, BCFunction]  # function id -> function
    modules: dict[str, ModuleSpec]  # module label -> spec
    entry_module: str
