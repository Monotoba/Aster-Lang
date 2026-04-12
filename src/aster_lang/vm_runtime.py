from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from aster_lang.bytecode import BCFunction, BCProgram, Op


class VMError(Exception):
    pass


class _RefCell:
    @property
    def value(self) -> object:
        raise NotImplementedError

    @value.setter
    def value(self, new_value: object) -> None:
        raise NotImplementedError

    @property
    def is_mutable(self) -> bool:
        raise NotImplementedError


class _Cell(_RefCell):
    __slots__ = ("_value",)

    def __init__(self, value: object) -> None:
        self._value = value

    @property
    def value(self) -> object:
        return self._value

    @value.setter
    def value(self, new_value: object) -> None:
        self._value = new_value

    @property
    def is_mutable(self) -> bool:
        return True


class _BorrowRef(_RefCell):
    __slots__ = ("_base", "_is_mutable")

    def __init__(self, base: _RefCell, is_mutable: bool) -> None:
        self._base = base
        self._is_mutable = is_mutable

    @property
    def value(self) -> object:
        return self._base.value

    @value.setter
    def value(self, new_value: object) -> None:
        self._base.value = new_value

    @property
    def is_mutable(self) -> bool:
        return self._is_mutable


class _MemberCell(_RefCell):
    __slots__ = ("_base", "_member", "_is_mutable")

    def __init__(self, base: _RefCell, member: str) -> None:
        self._base = base
        self._member = member
        self._is_mutable = base.is_mutable

    @property
    def value(self) -> object:
        obj = self._base.value
        if not isinstance(obj, dict):
            raise VMError("Member reference requires a record")
        if self._member not in obj:
            raise VMError(f"Missing record field '{self._member}'")
        return obj[self._member]

    @value.setter
    def value(self, new_value: object) -> None:
        obj = self._base.value
        if not isinstance(obj, dict):
            raise VMError("Member reference requires a record")
        new_obj = dict(obj)
        new_obj[self._member] = new_value
        self._base.value = new_obj

    @property
    def is_mutable(self) -> bool:
        return self._is_mutable


class _IndexCell(_RefCell):
    __slots__ = ("_base", "_index", "_is_mutable")

    def __init__(self, base: _RefCell, index: object) -> None:
        self._base = base
        self._index = index
        self._is_mutable = base.is_mutable

    @property
    def value(self) -> object:
        obj = self._base.value
        idx = self._index
        if isinstance(obj, list) and type(idx) is int:
            if idx < 0 or idx >= len(obj):
                raise VMError(f"List index out of bounds: {idx}")
            return obj[idx]
        if isinstance(obj, tuple) and type(idx) is int:
            if idx < 0 or idx >= len(obj):
                raise VMError(f"Tuple index out of bounds: {idx}")
            return obj[idx]
        if isinstance(obj, dict) and isinstance(idx, str):
            if idx not in obj:
                raise VMError(f"Missing record field '{idx}'")
            return obj[idx]
        if not isinstance(idx, int | str):
            raise VMError("Index reference requires Int or String index")
        raise VMError("Unsupported index reference")

    @value.setter
    def value(self, new_value: object) -> None:
        obj = self._base.value
        idx = self._index
        if isinstance(obj, list) and type(idx) is int:
            if idx < 0 or idx >= len(obj):
                raise VMError(f"List index out of bounds: {idx}")
            new_list = list(obj)
            new_list[idx] = new_value
            self._base.value = new_list
            return
        if isinstance(obj, dict) and isinstance(idx, str):
            new_obj = dict(obj)
            new_obj[idx] = new_value
            self._base.value = new_obj
            return
        raise VMError("Unsupported index reference assignment")

    @property
    def is_mutable(self) -> bool:
        return self._is_mutable


@dataclass(slots=True, frozen=True)
class _ModuleValue:
    name: str
    exports: dict[str, object]


@dataclass(slots=True, frozen=True)
class _Closure:
    fn_id: str
    free: tuple[_RefCell, ...]


@dataclass(slots=True)
class _Frame:
    fn: BCFunction
    ip: int
    locals: list[_Cell]
    free: list[_RefCell]
    stack: list[object]
    globals: dict[str, _Cell]
    module_label: str


class VM:
    def __init__(self, program: BCProgram) -> None:
        self.program = program
        self.output: list[str] = []
        self._frames: list[_Frame] = []
        self._module_envs: dict[str, dict[str, _Cell]] = {}
        self._module_exports: dict[str, _ModuleValue] = {}
        self._initializing: set[str] = set()

        BuiltinFn = Callable[[list[object]], object]

        def _fmt_value(v: object) -> str:
            if v is None:
                return "nil"
            if v is True:
                return "true"
            if v is False:
                return "false"
            if isinstance(v, list):
                return "[" + ", ".join(_fmt_value(x) for x in v) + "]"
            if isinstance(v, tuple):
                return "(" + ", ".join(_fmt_value(x) for x in v) + ")"
            if isinstance(v, dict):
                items = ", ".join(f"{k}: {_fmt_value(val)}" for k, val in v.items())
                return "{" + items + "}"
            return str(v)

        def builtin_print(args: list[object]) -> object:
            if len(args) != 1:
                raise VMError(f"print() expects 1 argument, got {len(args)}")
            self.output.append(_fmt_value(args[0]))
            return None

        def builtin_len(args: list[object]) -> object:
            obj = args[0]
            if isinstance(obj, str | list | tuple | dict):
                return len(obj)
            raise VMError(f"len() not supported for {_len_type_name(obj)}")

        def builtin_str(args: list[object]) -> object:
            return _fmt_value(args[0])

        def builtin_int(args: list[object]) -> object:
            arg = args[0]
            if type(arg) is int:
                return arg
            if type(arg) is bool:
                return 1 if arg else 0
            if isinstance(arg, str):
                try:
                    return int(arg)
                except ValueError as exc:
                    raise VMError(f"Cannot convert {arg!r} to Int") from exc
            raise VMError(f"Cannot convert {type(arg).__name__} to Int")

        def builtin_abs(args: list[object]) -> object:
            return abs(args[0])  # type: ignore[arg-type]

        def builtin_max(args: list[object]) -> object:
            if len(args) != 2:
                raise VMError(f"max() expects 2 arguments, got {len(args)}")
            a, b = args
            if type(a) is not int or type(b) is not int:
                raise VMError("max() requires integers")
            return a if a >= b else b

        def builtin_min(args: list[object]) -> object:
            if len(args) != 2:
                raise VMError(f"min() expects 2 arguments, got {len(args)}")
            a, b = args
            if type(a) is not int or type(b) is not int:
                raise VMError("min() requires integers")
            return a if a <= b else b

        def builtin_range(args: list[object]) -> object:
            if len(args) == 1:
                stop = args[0]
                if type(stop) is not int:
                    raise VMError("range() requires integers")
                return list(range(stop))
            if len(args) == 2:
                start, stop = args
                if type(start) is not int or type(stop) is not int:
                    raise VMError("range() requires integers")
                return list(range(start, stop))
            raise VMError(f"range() takes 1 or 2 arguments, got {len(args)}")

        def builtin_ord(args: list[object]) -> object:
            s = args[0]
            if not isinstance(s, str):
                raise VMError("ord() expects String")
            if len(s) != 1:
                raise VMError("ord() expects a single-character String")
            return ord(s)

        def builtin_ascii_bytes(args: list[object]) -> object:
            s = args[0]
            if not isinstance(s, str):
                raise VMError("ascii_bytes() expects String")
            out: list[int] = []
            for ch in s:
                code = ord(ch)
                if code > 0x7F:
                    raise VMError(f"ascii_bytes() only supports ASCII; got codepoint {code}")
                out.append(code & 0xFF)
            return out

        def builtin_unicode_bytes(args: list[object]) -> object:
            s = args[0]
            if not isinstance(s, str):
                raise VMError("unicode_bytes() expects String")
            return [b & 0xFF for b in s.encode("utf-8")]

        def _cast_bits(bits: int, args: list[object]) -> object:
            x = args[0]
            if type(x) is not int:
                raise VMError("fixed-width casts expect Int arguments")
            mask = (1 << bits) - 1
            return x & mask

        self._builtins: dict[str, tuple[int, BuiltinFn]] = {
            "print": (1, builtin_print),
            "len": (1, builtin_len),
            "str": (1, builtin_str),
            "int": (1, builtin_int),
            "abs": (1, builtin_abs),
            "max": (2, builtin_max),
            "min": (2, builtin_min),
            "range": (-1, builtin_range),
            "ord": (1, builtin_ord),
            "ascii_bytes": (1, builtin_ascii_bytes),
            "unicode_bytes": (1, builtin_unicode_bytes),
            "nibble": (1, lambda args: _cast_bits(4, args)),
            "byte": (1, lambda args: _cast_bits(8, args)),
            "word": (1, lambda args: _cast_bits(16, args)),
            "dword": (1, lambda args: _cast_bits(32, args)),
            "qword": (1, lambda args: _cast_bits(64, args)),
        }

    def run_entry(self) -> None:
        entry_label = self.program.entry_module
        self._ensure_module_initialized(entry_label)
        main_id = f"{entry_label}::main"
        fn = self.program.functions.get(main_id)
        if fn is None:
            raise VMError("No main() function found")
        self._call_user(fn, [], module_label=entry_label)

    def _call_user(
        self,
        fn: BCFunction,
        args: list[object],
        *,
        module_label: str,
        free: tuple[_RefCell, ...] = (),
    ) -> object:
        if len(args) != len(fn.params):
            raise VMError(f"{fn.name}() expected {len(fn.params)} args, got {len(args)}")
        locals_: list[_Cell] = [_Cell(None) for _ in range(fn.local_count)]
        for i, v in enumerate(args):
            locals_[i].value = v
        frame = _Frame(
            fn=fn,
            ip=0,
            locals=locals_,
            free=list(free),
            stack=[],
            globals=self._module_envs.setdefault(module_label, {}),
            module_label=module_label,
        )
        self._frames.append(frame)
        try:
            return self._run_frame()
        finally:
            self._frames.pop()

    def _run_frame(self) -> object:
        frame = self._frames[-1]
        consts = self.program.constants
        code = frame.fn.code

        def _deref(v: object) -> object:
            while isinstance(v, _RefCell):
                v = v.value
            return v

        while frame.ip < len(code):
            ins = code[frame.ip]
            frame.ip += 1

            if ins.op == Op.CONST:
                assert isinstance(ins.arg, int)
                frame.stack.append(consts[ins.arg])
                continue
            if ins.op == Op.LOAD:
                assert isinstance(ins.arg, int)
                frame.stack.append(_deref(frame.locals[ins.arg].value))
                continue
            if ins.op == Op.STORE:
                assert isinstance(ins.arg, int)
                cell = frame.locals[ins.arg]
                value = frame.stack.pop()
                if isinstance(cell.value, _RefCell):
                    if not cell.value.is_mutable:
                        raise VMError("Cannot assign through immutable reference")
                    cell.value.value = value
                else:
                    cell.value = value
                continue
            if ins.op == Op.POP:
                frame.stack.pop()
                continue

            if ins.op == Op.REF_LOCAL:
                if isinstance(ins.arg, tuple):
                    idx, is_mutable = ins.arg
                else:
                    idx, is_mutable = ins.arg, True
                assert isinstance(idx, int)
                if is_mutable is None:
                    frame.stack.append(frame.locals[idx])
                else:
                    frame.stack.append(_BorrowRef(frame.locals[idx], bool(is_mutable)))
                continue
            if ins.op == Op.REF_FREE:
                if isinstance(ins.arg, tuple):
                    idx, is_mutable = ins.arg
                else:
                    idx, is_mutable = ins.arg, True
                assert isinstance(idx, int)
                if is_mutable is None:
                    frame.stack.append(frame.free[idx])
                else:
                    frame.stack.append(_BorrowRef(frame.free[idx], bool(is_mutable)))
                continue
            if ins.op == Op.REF_GLOBAL:
                if isinstance(ins.arg, tuple):
                    name_k, is_mutable = ins.arg
                else:
                    name_k, is_mutable = ins.arg, True
                assert isinstance(name_k, int)
                name_obj = consts[name_k]
                if not isinstance(name_obj, str):
                    raise VMError("REF_GLOBAL name constant must be a string")
                gcell = frame.globals.get(name_obj)
                if gcell is None:
                    gcell = _Cell(None)
                    frame.globals[name_obj] = gcell
                if is_mutable is None:
                    frame.stack.append(gcell)
                else:
                    frame.stack.append(_BorrowRef(gcell, bool(is_mutable)))
                continue
            if ins.op == Op.BOX:
                is_mutable = bool(ins.arg) if ins.arg is not None else True
                frame.stack.append(_BorrowRef(_Cell(frame.stack.pop()), is_mutable))
                continue
            if ins.op == Op.REF_MEMBER:
                assert isinstance(ins.arg, int)
                key_obj = consts[ins.arg]
                if not isinstance(key_obj, str):
                    raise VMError("REF_MEMBER key constant must be a string")
                base_ref = frame.stack.pop()
                if not isinstance(base_ref, _RefCell):
                    raise VMError("REF_MEMBER expects a cell reference")
                frame.stack.append(_MemberCell(base_ref, key_obj))
                continue
            if ins.op == Op.REF_INDEX:
                idx = frame.stack.pop()
                base_ref = frame.stack.pop()
                if not isinstance(base_ref, _RefCell):
                    raise VMError("REF_INDEX expects a cell reference")
                frame.stack.append(_IndexCell(base_ref, idx))
                continue
            if ins.op == Op.LOAD_FREE:
                assert isinstance(ins.arg, int)
                frame.stack.append(_deref(frame.free[ins.arg].value))
                continue
            if ins.op == Op.STORE_FREE:
                assert isinstance(ins.arg, int)
                free_cell: _RefCell = frame.free[ins.arg]
                value = frame.stack.pop()
                if isinstance(free_cell.value, _RefCell):
                    if not free_cell.value.is_mutable:
                        raise VMError("Cannot assign through immutable reference")
                    free_cell.value.value = value
                else:
                    free_cell.value = value
                continue
            if ins.op == Op.MAKE_CLOSURE:
                assert isinstance(ins.arg, tuple) and len(ins.arg) == 2
                fn_idx_obj, free_count_obj = ins.arg
                assert isinstance(fn_idx_obj, int)
                assert isinstance(free_count_obj, int)
                fn_id_obj = consts[fn_idx_obj]
                if not isinstance(fn_id_obj, str):
                    raise VMError("MAKE_CLOSURE fn id constant must be a string")
                free_cells = [frame.stack.pop() for _ in range(free_count_obj)][::-1]
                if any(not isinstance(c, _RefCell) for c in free_cells):
                    raise VMError("MAKE_CLOSURE expects captured values to be cell references")
                frame.stack.append(_Closure(fn_id=fn_id_obj, free=tuple(free_cells)))  # type: ignore[arg-type]
                continue

            if ins.op == Op.DEREF:
                ref = frame.stack.pop()
                if not isinstance(ref, _RefCell):
                    raise VMError("DEREF expects a cell reference")
                frame.stack.append(_deref(ref.value))
                continue
            if ins.op == Op.STORE_DEREF:
                value = frame.stack.pop()
                ref = frame.stack.pop()
                if not isinstance(ref, _RefCell):
                    raise VMError("STORE_DEREF expects a cell reference")
                if not ref.is_mutable:
                    raise VMError("Cannot assign through immutable reference")
                ref.value = value
                continue

            if ins.op in {
                Op.ADD,
                Op.SUB,
                Op.MUL,
                Op.DIV,
                Op.MOD,
                Op.BIT_AND,
                Op.BIT_OR,
                Op.BIT_XOR,
                Op.SHL,
                Op.SHR,
                Op.EQ,
                Op.NE,
                Op.LT,
                Op.LE,
                Op.GT,
                Op.GE,
            }:
                b = frame.stack.pop()
                a = frame.stack.pop()
                frame.stack.append(self._binop(ins.op, a, b))
                continue

            if ins.op == Op.NEG:
                a = frame.stack.pop()
                if type(a) is not int:
                    raise VMError("Unary '-' only supported for Int in VM backend")
                frame.stack.append(-a)
                continue
            if ins.op == Op.NOT:
                a = frame.stack.pop()
                frame.stack.append(not bool(a))
                continue
            if ins.op == Op.BIT_NOT:
                a = frame.stack.pop()
                if type(a) is not int:
                    raise VMError("Unary '~' only supported for Int in VM backend")
                frame.stack.append(~a)
                continue

            if ins.op == Op.JMP:
                assert isinstance(ins.arg, int)
                frame.ip = ins.arg
                continue
            if ins.op == Op.JMP_IF_FALSE:
                cond = frame.stack.pop()
                if not bool(cond):
                    assert isinstance(ins.arg, int)
                    frame.ip = ins.arg
                continue

            if ins.op == Op.CALL:
                assert isinstance(ins.arg, tuple) and len(ins.arg) == 2
                name_idx_obj, argc_obj = ins.arg
                assert isinstance(name_idx_obj, int)
                assert isinstance(argc_obj, int)
                name = consts[name_idx_obj]
                if not isinstance(name, str):
                    raise VMError("CALL name constant must be a string")
                args = [frame.stack.pop() for _ in range(argc_obj)][::-1]
                frame.stack.append(self._call(name, args, module_label=frame.module_label))
                continue
            if ins.op == Op.CALL_VALUE:
                assert isinstance(ins.arg, int)
                argc = ins.arg
                args = [frame.stack.pop() for _ in range(argc)][::-1]
                callee = frame.stack.pop()
                if isinstance(callee, str):
                    frame.stack.append(self._call(callee, args, module_label=frame.module_label))
                    continue
                if isinstance(callee, _Closure):
                    frame.stack.append(
                        self._call_closure(callee, args, module_label=frame.module_label)
                    )
                    continue
                raise VMError("Can only call function ids (strings) or closures in VM backend")

            if ins.op == Op.RETURN:
                return frame.stack.pop()

            if ins.op == Op.BUILD_LIST:
                assert isinstance(ins.arg, int)
                items = [frame.stack.pop() for _ in range(ins.arg)][::-1]
                frame.stack.append(items)
                continue
            if ins.op == Op.BUILD_TUPLE:
                assert isinstance(ins.arg, int)
                items = [frame.stack.pop() for _ in range(ins.arg)][::-1]
                frame.stack.append(tuple(items))
                continue
            if ins.op == Op.BUILD_RECORD:
                assert isinstance(ins.arg, tuple)
                names = ins.arg
                vals = [frame.stack.pop() for _ in range(len(names))][::-1]
                frame.stack.append({str(k): v for k, v in zip(names, vals, strict=True)})
                continue
            if ins.op == Op.MEMBER:
                assert isinstance(ins.arg, int)
                key_obj = consts[ins.arg]
                if not isinstance(key_obj, str):
                    raise VMError("MEMBER key constant must be a string")
                obj = frame.stack.pop()
                if isinstance(obj, _ModuleValue):
                    if key_obj not in obj.exports:
                        raise VMError(f"Module '{obj.name}' has no export '{key_obj}'")
                    frame.stack.append(obj.exports[key_obj])
                    continue
                if isinstance(obj, dict):
                    if key_obj not in obj:
                        raise VMError(f"Record has no field '{key_obj}'")
                    frame.stack.append(obj[key_obj])
                    continue
                raise VMError(f"Cannot access member of {type(obj).__name__}")
            if ins.op == Op.INDEX:
                idx = frame.stack.pop()
                obj = frame.stack.pop()
                if isinstance(obj, list) and type(idx) is int:
                    try:
                        frame.stack.append(obj[idx])
                    except IndexError as exc:
                        raise VMError(f"List index out of bounds: {idx}") from exc
                    continue
                if isinstance(obj, tuple) and type(idx) is int:
                    try:
                        frame.stack.append(obj[idx])
                    except IndexError as exc:
                        raise VMError(f"Tuple index out of bounds: {idx}") from exc
                    continue
                if isinstance(obj, dict) and isinstance(idx, str):
                    if idx not in obj:
                        raise VMError(f"Missing record field '{idx}'")
                    frame.stack.append(obj[idx])
                    continue
                obj_type = type(obj).__name__
                index_type = type(idx).__name__
                raise VMError(f"Cannot index {obj_type} with {index_type}")
            if ins.op == Op.IS_LIST:
                obj = frame.stack.pop()
                frame.stack.append(isinstance(obj, list))
                continue
            if ins.op == Op.IS_TUPLE:
                obj = frame.stack.pop()
                frame.stack.append(isinstance(obj, tuple))
                continue
            if ins.op == Op.IS_RECORD:
                obj = frame.stack.pop()
                frame.stack.append(isinstance(obj, dict))
                continue
            if ins.op == Op.LEN:
                obj = frame.stack.pop()
                if isinstance(obj, list | tuple | dict):
                    frame.stack.append(len(obj))
                    continue
                raise VMError(f"len() not supported for {_len_type_name(obj)}")
            if ins.op == Op.HAS_KEY:
                assert isinstance(ins.arg, int)
                key_obj = consts[ins.arg]
                if not isinstance(key_obj, str):
                    raise VMError("HAS_KEY key constant must be a string")
                obj = frame.stack.pop()
                if not isinstance(obj, dict):
                    raise VMError("HAS_KEY only supported on records in VM backend")
                frame.stack.append(key_obj in obj)
                continue
            if ins.op == Op.SLICE_FROM:
                assert isinstance(ins.arg, int)
                obj = frame.stack.pop()
                if isinstance(obj, list | tuple):
                    frame.stack.append(obj[ins.arg :])
                    continue
                raise VMError("Slice only supported on list/tuple in VM backend")
            if ins.op == Op.LOAD_GLOBAL:
                assert isinstance(ins.arg, int)
                name_obj = consts[ins.arg]
                if not isinstance(name_obj, str):
                    raise VMError("LOAD_GLOBAL name constant must be a string")
                if name_obj not in frame.globals:
                    raise VMError(f"Undefined variable '{name_obj}'")
                frame.stack.append(_deref(frame.globals[name_obj].value))
                continue
            if ins.op == Op.STORE_GLOBAL:
                assert isinstance(ins.arg, int)
                name_obj = consts[ins.arg]
                if not isinstance(name_obj, str):
                    raise VMError("STORE_GLOBAL name constant must be a string")
                gcell = frame.globals.get(name_obj)
                if gcell is None:
                    gcell = _Cell(None)
                    frame.globals[name_obj] = gcell
                value = frame.stack.pop()
                if isinstance(gcell.value, _RefCell):
                    if not gcell.value.is_mutable:
                        raise VMError("Cannot assign through immutable reference")
                    gcell.value.value = value
                else:
                    gcell.value = value
                continue
            if ins.op == Op.IMPORT_MODULE:
                assert isinstance(ins.arg, int)
                label_obj = consts[ins.arg]
                if not isinstance(label_obj, str):
                    raise VMError("IMPORT_MODULE label constant must be a string")
                frame.stack.append(self.import_module(label_obj))
                continue
            if ins.op == Op.SET_INDEX:
                assert isinstance(ins.arg, tuple) and len(ins.arg) == 2
                ref_kind, ref = ins.arg
                assert ref_kind in ("local", "global")
                value = frame.stack.pop()
                idx = frame.stack.pop()
                target_cell_index: _Cell
                if ref_kind == "local":
                    assert isinstance(ref, int)
                    target_cell_index = frame.locals[ref]
                else:
                    assert isinstance(ref, int)
                    name_obj = consts[ref]
                    if not isinstance(name_obj, str):
                        raise VMError("SET_INDEX global name constant must be a string")
                    gcell = frame.globals.get(name_obj)
                    if gcell is None:
                        raise VMError(f"Undefined variable '{name_obj}'")
                    target_cell_index = gcell
                obj = target_cell_index.value

                if isinstance(obj, list) and type(idx) is int:
                    if idx < 0 or idx >= len(obj):
                        raise VMError(f"List index out of bounds: {idx}")
                    new_list = list(obj)
                    new_list[idx] = value
                    target_cell_index.value = new_list
                    continue
                if isinstance(obj, dict) and isinstance(idx, str):
                    new_rec = dict(obj)
                    new_rec[idx] = value
                    target_cell_index.value = new_rec
                    continue
                raise VMError("Unsupported index reference assignment")
            if ins.op == Op.SET_MEMBER:
                assert isinstance(ins.arg, tuple) and len(ins.arg) == 3
                key_k, ref_kind, ref = ins.arg
                assert isinstance(key_k, int)
                assert ref_kind in ("local", "global")
                key_obj = consts[key_k]
                if not isinstance(key_obj, str):
                    raise VMError("SET_MEMBER key constant must be a string")
                value = frame.stack.pop()
                target_cell_member: _Cell
                if ref_kind == "local":
                    assert isinstance(ref, int)
                    target_cell_member = frame.locals[ref]
                else:
                    assert isinstance(ref, int)
                    name_obj = consts[ref]
                    if not isinstance(name_obj, str):
                        raise VMError("SET_MEMBER global name constant must be a string")
                    gcell = frame.globals.get(name_obj)
                    if gcell is None:
                        raise VMError(f"Undefined variable '{name_obj}'")
                    target_cell_member = gcell
                obj = target_cell_member.value
                if not isinstance(obj, dict):
                    raise VMError("Member assignment only supported on records in VM backend")
                new_rec = dict(obj)
                new_rec[key_obj] = value
                target_cell_member.value = new_rec
                continue

            raise VMError(f"Unknown opcode: {ins.op}")

        raise VMError("Function ran off end without RETURN")

    def _call(self, name: str, args: list[object], *, module_label: str) -> object:
        bi = self._builtins.get(name)
        if bi is not None:
            arity, fn = bi
            if arity != -1 and arity != len(args):
                raise VMError(f"Built-in {name} expects {arity} argument(s), got {len(args)}")
            return fn(args)

        target = self.program.functions.get(name)
        if target is None:
            raise VMError(f"Unknown function '{name}'")
        callee_module = name.split("::", 1)[0] if "::" in name else module_label
        return self._call_user(target, args, module_label=callee_module)

    def _call_closure(self, closure: _Closure, args: list[object], *, module_label: str) -> object:
        target = self.program.functions.get(closure.fn_id)
        if target is None:
            raise VMError(f"Unknown function '{closure.fn_id}'")
        callee_module = closure.fn_id.split("::", 1)[0] if "::" in closure.fn_id else module_label
        return self._call_user(target, args, module_label=callee_module, free=closure.free)

    def import_module(self, label: str) -> _ModuleValue:
        self._ensure_module_initialized(label)
        return self._module_exports[label]

    def _ensure_module_initialized(self, label: str) -> None:
        if label in self._module_exports:
            return
        spec = self.program.modules.get(label)
        if spec is None:
            raise VMError(f"Unknown module '{label}'")
        if label in self._initializing:
            raise VMError(f"Cyclic import detected for module '{label}'")
        self._initializing.add(label)
        try:
            env = self._module_envs.setdefault(label, {})
            for name in self._builtins:
                env.setdefault(name, _Cell(name))
            init_fn = self.program.functions[spec.init_fn]
            self._call_user(init_fn, [], module_label=label)
            exports: dict[str, object] = {}
            for export_name, (kind, value) in spec.exports.items():
                if kind == "fn":
                    exports[export_name] = value
                elif kind == "var":
                    cell = env.get(value)
                    exports[export_name] = None if cell is None else cell.value
                else:
                    raise VMError("Internal error: invalid export kind")
            self._module_exports[label] = _ModuleValue(name=label, exports=exports)
        finally:
            self._initializing.remove(label)

    def _binop(self, op: Op, a: object, b: object) -> object:
        if op == Op.ADD:
            if type(a) is int and type(b) is int:
                return a + b
            if type(a) is str and type(b) is str:
                return a + b
            raise VMError("Operator + only supports Int+Int or String+String in VM backend")
        if op == Op.SUB:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator - only supports Int-Int in VM backend")
            return a - b
        if op == Op.MUL:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator * only supports Int*Int in VM backend")
            return a * b
        if op == Op.DIV:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator / only supports Int/Int in VM backend")
            if b == 0:
                raise VMError("Division by zero")
            return a // b
        if op == Op.MOD:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator % only supports Int%Int in VM backend")
            if b == 0:
                raise VMError("Modulo by zero")
            return a % b
        if op == Op.BIT_AND:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator & only supports Int&Int in VM backend")
            return a & b
        if op == Op.BIT_OR:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator | only supports Int|Int in VM backend")
            return a | b
        if op == Op.BIT_XOR:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator ^ only supports Int^Int in VM backend")
            return a ^ b
        if op == Op.SHL:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator << only supports Int<<Int in VM backend")
            return a << b
        if op == Op.SHR:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator >> only supports Int>>Int in VM backend")
            return a >> b
        if op == Op.EQ:
            return self._values_equal(a, b)
        if op == Op.NE:
            return not self._values_equal(a, b)
        if op == Op.LT:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator < only supports Int<Int in VM backend")
            return a < b
        if op == Op.LE:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator <= only supports Int<=Int in VM backend")
            return a <= b
        if op == Op.GT:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator > only supports Int>Int in VM backend")
            return a > b
        if op == Op.GE:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator >= only supports Int>=Int in VM backend")
            return a >= b
        raise VMError(f"Unsupported binop {op}")

    def _values_equal(self, a: object, b: object) -> bool:
        if type(a) is int and type(b) is int:
            return a == b
        if type(a) is not type(b):
            return False
        if isinstance(a, bool | str):
            return a == b
        if a is None:
            return True
        if isinstance(a, list):
            assert isinstance(b, list)
            if len(a) != len(b):
                return False
            return all(self._values_equal(x, y) for x, y in zip(a, b, strict=True))
        if isinstance(a, tuple):
            assert isinstance(b, tuple)
            if len(a) != len(b):
                return False
            return all(self._values_equal(x, y) for x, y in zip(a, b, strict=True))
        if isinstance(a, dict):
            assert isinstance(b, dict)
            if a.keys() != b.keys():
                return False
            return all(self._values_equal(a[k], b[k]) for k in a)
        return False


def _len_type_name(obj: object) -> str:
    if obj is None:
        return "NilValue"
    if type(obj) is bool:
        return "BoolValue"
    if type(obj) is int:
        return "IntValue"
    if isinstance(obj, str):
        return "StringValue"
    if isinstance(obj, list):
        return "ListValue"
    if isinstance(obj, tuple):
        return "TupleValue"
    if isinstance(obj, dict):
        return "RecordValue"
    return type(obj).__name__
