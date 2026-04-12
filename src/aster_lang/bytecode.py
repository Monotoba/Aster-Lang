from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from enum import Enum, auto

BYTECODE_FORMAT_NAME = "asterbc"
BYTECODE_FORMAT_VERSION = 1
BYTECODE_MIN_SUPPORTED_VERSION = 1
BYTECODE_MAX_SUPPORTED_VERSION = 1
BYTECODE_INTEGRITY_ALGORITHM = "sha256"
BYTECODE_SIGNATURE_ALGORITHM = "hmac-sha256"


class Op(Enum):
    CONST = auto()  # push constants[arg]
    LOAD = auto()  # push locals[arg]
    STORE = auto()  # locals[arg] = pop()
    POP = auto()  # pop()

    # Closure support
    REF_LOCAL = auto()  # arg=slot:int, push a reference (cell) to locals[slot]
    REF_FREE = auto()  # arg=slot:int, push a reference (cell) to free[slot]
    REF_GLOBAL = auto()  # arg=name_const_index, push a reference (cell) to globals[name]
    BOX = auto()  # pop value, wrap it in a temporary cell, and push the cell (arg=mutable?)
    REF_MEMBER = auto()  # arg=key_const_index, pop base cell, push a member reference
    REF_INDEX = auto()  # pop index, pop base cell, push an index reference
    LOAD_FREE = auto()  # arg=slot:int, push free[slot].value
    STORE_FREE = auto()  # arg=slot:int, free[slot].value = pop()
    # arg=(fn_id_const_index, free_count); pop N cell refs, push a closure value
    MAKE_CLOSURE = auto()

    DEREF = auto()  # pop cell, push cell.value
    STORE_DEREF = auto()  # pop value, pop cell, cell.value = value

    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()

    BIT_AND = auto()
    BIT_OR = auto()
    BIT_XOR = auto()
    SHL = auto()
    SHR = auto()

    NEG = auto()
    NOT = auto()
    BIT_NOT = auto()

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


def program_to_data(program: BCProgram) -> object:
    return _encode_value(program)


def program_to_signed_data(program: BCProgram, *, signing_key: bytes) -> object:
    artifact = program_to_data(program)
    if not isinstance(artifact, dict):
        raise TypeError("Program artifact must be a dictionary to sign")
    return sign_artifact(artifact, signing_key)


def program_to_json(program: BCProgram, *, signing_key: bytes | None = None) -> str:
    if signing_key is None:
        payload = program_to_data(program)
    else:
        payload = program_to_signed_data(program, signing_key=signing_key)
    return json.dumps(payload, indent=2, sort_keys=True)


def program_from_data(data: object, *, signing_key: bytes | None = None) -> BCProgram:
    if not isinstance(data, dict):
        raise TypeError("Bytecode artifact must be a JSON object")
    kind = data.get("kind")
    if kind != "program":
        raise TypeError(f"Bytecode artifact root must be a program, got {kind!r}")
    format_name = data.get("format")
    if format_name != BYTECODE_FORMAT_NAME:
        raise ValueError(f"Unsupported bytecode artifact format: {format_name!r}")
    version = data.get("version")
    if not isinstance(version, int):
        raise TypeError("Bytecode artifact version must be an integer")
    if version < BYTECODE_MIN_SUPPORTED_VERSION:
        raise ValueError(
            "Bytecode artifact version is too old: "
            f"{version!r} < {BYTECODE_MIN_SUPPORTED_VERSION!r}"
        )
    if version > BYTECODE_MAX_SUPPORTED_VERSION:
        raise ValueError(
            "Bytecode artifact version is too new: "
            f"{version!r} > {BYTECODE_MAX_SUPPORTED_VERSION!r}"
        )
    integrity = data.get("integrity")
    if not isinstance(integrity, dict):
        raise TypeError("Bytecode artifact integrity block is required")
    algorithm = integrity.get("algorithm")
    if algorithm != BYTECODE_INTEGRITY_ALGORITHM:
        raise ValueError(f"Unsupported bytecode integrity algorithm: {algorithm!r}")
    digest = integrity.get("digest")
    if not isinstance(digest, str):
        raise TypeError("Bytecode artifact integrity digest must be a string")
    expected_digest = _artifact_digest(_program_payload(data))
    if digest != expected_digest:
        raise ValueError("Bytecode artifact integrity check failed")
    signature = data.get("signature")
    if signature is not None:
        _verify_artifact_signature(data, signature, signing_key=signing_key)
    value = _decode_value(data)
    if not isinstance(value, BCProgram):
        raise TypeError("Decoded bytecode payload is not a BCProgram")
    return value


def program_from_json(data: str, *, signing_key: bytes | None = None) -> BCProgram:
    return program_from_data(json.loads(data), signing_key=signing_key)


def _encode_value(value: object) -> object:
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, tuple):
        return {"kind": "tuple", "items": [_encode_value(v) for v in value]}
    if isinstance(value, list):
        return {"kind": "list", "items": [_encode_value(v) for v in value]}
    if isinstance(value, dict):
        return {
            "kind": "dict",
            "items": [[_encode_value(k), _encode_value(v)] for k, v in value.items()],
        }
    if isinstance(value, Op):
        return {"kind": "op", "name": value.name}
    if isinstance(value, Instr):
        return {
            "kind": "instr",
            "op": value.op.name,
            "arg": _encode_value(value.arg),
        }
    if isinstance(value, BCFunction):
        return {
            "kind": "function",
            "name": value.name,
            "params": _encode_value(value.params),
            "code": _encode_value(value.code),
            "local_count": value.local_count,
        }
    if isinstance(value, ModuleSpec):
        return {
            "kind": "module_spec",
            "label": value.label,
            "init_fn": value.init_fn,
            "exports": _encode_value(value.exports),
        }
    if isinstance(value, BCProgram):
        artifact = {
            "kind": "program",
            "format": BYTECODE_FORMAT_NAME,
            "version": BYTECODE_FORMAT_VERSION,
            "constants": _encode_value(value.constants),
            "functions": _encode_value(value.functions),
            "modules": _encode_value(value.modules),
            "entry_module": value.entry_module,
        }
        artifact["integrity"] = {
            "algorithm": BYTECODE_INTEGRITY_ALGORITHM,
            "digest": _artifact_digest(artifact),
        }
        return artifact
    raise TypeError(f"Unsupported bytecode value: {type(value).__name__}")


def _program_payload(artifact: dict[object, object]) -> dict[object, object]:
    return {key: value for key, value in artifact.items() if key not in ("integrity", "signature")}


def _artifact_digest(payload: object) -> str:
    canonical = _canonical_bytes(payload)
    return hashlib.sha256(canonical).hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return canonical.encode("utf-8")


def sign_artifact(artifact: dict[object, object], signing_key: bytes) -> dict[object, object]:
    payload = _signature_payload(artifact)
    signature = hmac.new(signing_key, _canonical_bytes(payload), hashlib.sha256).hexdigest()
    signed = dict(artifact)
    signed["signature"] = {
        "algorithm": BYTECODE_SIGNATURE_ALGORITHM,
        "digest": signature,
    }
    return signed


def _signature_payload(artifact: dict[object, object]) -> dict[object, object]:
    return {key: value for key, value in artifact.items() if key != "signature"}


def _verify_artifact_signature(
    artifact: dict[object, object],
    signature: object,
    *,
    signing_key: bytes | None,
) -> None:
    if signing_key is None:
        raise ValueError("Bytecode artifact is signed but no signing key was provided")
    if not isinstance(signature, dict):
        raise TypeError("Bytecode artifact signature block must be a JSON object")
    algorithm = signature.get("algorithm")
    if algorithm != BYTECODE_SIGNATURE_ALGORITHM:
        raise ValueError(f"Unsupported bytecode signature algorithm: {algorithm!r}")
    digest = signature.get("digest")
    if not isinstance(digest, str):
        raise TypeError("Bytecode artifact signature digest must be a string")
    expected = hmac.new(signing_key, _canonical_bytes(_signature_payload(artifact)), hashlib.sha256)
    if not hmac.compare_digest(digest, expected.hexdigest()):
        raise ValueError("Bytecode artifact signature verification failed")


def _decode_value(value: object) -> object:
    if value is None or isinstance(value, bool | int | str):
        return value
    if not isinstance(value, dict):
        raise TypeError(f"Unsupported decoded payload type: {type(value).__name__}")
    kind = value.get("kind")
    if kind == "tuple":
        items = value.get("items")
        if not isinstance(items, list):
            raise TypeError("tuple payload requires a list of items")
        return tuple(_decode_value(v) for v in items)
    if kind == "list":
        items = value.get("items")
        if not isinstance(items, list):
            raise TypeError("list payload requires a list of items")
        return [_decode_value(v) for v in items]
    if kind == "dict":
        items = value.get("items")
        if not isinstance(items, list):
            raise TypeError("dict payload requires a list of items")
        return {_decode_value(k): _decode_value(v) for k, v in items}
    if kind == "op":
        name = value.get("name")
        if not isinstance(name, str):
            raise TypeError("op payload requires a string name")
        return Op[name]
    if kind == "instr":
        op_name = value.get("op")
        if not isinstance(op_name, str):
            raise TypeError("instr payload requires a string op")
        return Instr(op=Op[op_name], arg=_decode_value(value.get("arg")))
    if kind == "function":
        name = value.get("name")
        params = _decode_value(value.get("params"))
        code = _decode_value(value.get("code"))
        local_count = value.get("local_count")
        if not isinstance(name, str):
            raise TypeError("function payload requires a string name")
        if not isinstance(params, tuple):
            raise TypeError("function payload requires tuple params")
        if not isinstance(code, tuple):
            raise TypeError("function payload requires tuple code")
        if not isinstance(local_count, int):
            raise TypeError("function payload requires int local_count")
        return BCFunction(name=name, params=params, code=code, local_count=local_count)
    if kind == "module_spec":
        label = value.get("label")
        init_fn = value.get("init_fn")
        exports = _decode_value(value.get("exports"))
        if not isinstance(label, str) or not isinstance(init_fn, str):
            raise TypeError("module_spec payload requires string label/init_fn")
        if not isinstance(exports, dict):
            raise TypeError("module_spec payload requires dict exports")
        return ModuleSpec(label=label, init_fn=init_fn, exports=exports)
    if kind == "program":
        constants = _decode_value(value.get("constants"))
        functions = _decode_value(value.get("functions"))
        modules = _decode_value(value.get("modules"))
        entry_module = value.get("entry_module")
        if not isinstance(constants, tuple):
            raise TypeError("program payload requires tuple constants")
        if not isinstance(functions, dict):
            raise TypeError("program payload requires dict functions")
        if not isinstance(modules, dict):
            raise TypeError("program payload requires dict modules")
        if not isinstance(entry_module, str):
            raise TypeError("program payload requires string entry_module")
        return BCProgram(
            constants=constants,
            functions=functions,
            modules=modules,
            entry_module=entry_module,
        )
    raise TypeError(f"Unknown encoded bytecode kind: {kind!r}")
