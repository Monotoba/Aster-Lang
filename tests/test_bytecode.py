from __future__ import annotations

import json

import pytest

from aster_lang.bytecode import (
    BYTECODE_BINARY_MAGIC,
    BYTECODE_FORMAT_NAME,
    BYTECODE_FORMAT_VERSION,
    BYTECODE_MAX_SUPPORTED_VERSION,
    BYTECODE_MIN_SUPPORTED_VERSION,
    BYTECODE_SIGNATURE_ALGORITHM,
    BCFunction,
    BCProgram,
    Instr,
    Op,
    program_from_bytes,
    program_from_data,
    program_to_bytes,
    program_to_data,
    program_to_signed_data,
)


def _sample_program() -> BCProgram:
    return BCProgram(
        constants=(42, "main"),
        functions={
            "__main__.main": BCFunction(
                name="__main__.main",
                params=(),
                code=(Instr(Op.CONST, 0), Instr(Op.RETURN)),
                local_count=0,
            )
        },
        modules={},
        entry_module="__main__",
    )


def test_program_to_data_includes_format_and_version() -> None:
    artifact = program_to_data(_sample_program())

    assert isinstance(artifact, dict)
    assert artifact["kind"] == "program"
    assert artifact["format"] == BYTECODE_FORMAT_NAME
    assert artifact["version"] == BYTECODE_FORMAT_VERSION
    assert artifact["integrity"]["algorithm"] == "sha256"
    assert isinstance(artifact["integrity"]["digest"], str)
    assert len(artifact["integrity"]["digest"]) == 64


def test_program_from_data_rejects_artifact_version_too_new() -> None:
    artifact = program_to_data(_sample_program())
    assert isinstance(artifact, dict)
    artifact = dict(artifact)
    artifact["version"] = BYTECODE_MAX_SUPPORTED_VERSION + 1

    with pytest.raises(ValueError, match="too new"):
        program_from_data(artifact)


def test_program_from_data_rejects_artifact_version_too_old() -> None:
    artifact = program_to_data(_sample_program())
    assert isinstance(artifact, dict)
    artifact = dict(artifact)
    artifact["version"] = BYTECODE_MIN_SUPPORTED_VERSION - 1

    with pytest.raises(ValueError, match="too old"):
        program_from_data(artifact)


def test_program_from_data_rejects_checksum_mismatch() -> None:
    artifact = program_to_data(_sample_program())
    assert isinstance(artifact, dict)
    artifact = dict(artifact)
    artifact["constants"] = {"kind": "tuple", "items": [99, "main"]}

    with pytest.raises(ValueError, match="Bytecode artifact integrity check failed"):
        program_from_data(artifact)


def test_program_from_data_round_trips_serialized_program() -> None:
    original = _sample_program()
    decoded = program_from_data(json.loads(json.dumps(program_to_data(original))))

    assert decoded == original


def test_program_from_bytes_round_trips_program() -> None:
    original = _sample_program()
    encoded = program_to_bytes(original)
    assert encoded.startswith(BYTECODE_BINARY_MAGIC)

    decoded = program_from_bytes(encoded)
    assert decoded == original


def test_program_from_data_accepts_signed_artifacts_with_key() -> None:
    key = b"test-key"
    signed = program_to_signed_data(_sample_program(), signing_key=key)
    assert isinstance(signed, dict)
    assert signed["signature"]["algorithm"] == BYTECODE_SIGNATURE_ALGORITHM

    decoded = program_from_data(signed, signing_key=key)
    assert decoded == _sample_program()


def test_program_from_bytes_accepts_signed_artifacts_with_key() -> None:
    key = b"test-key"
    encoded = program_to_bytes(_sample_program(), signing_key=key)

    decoded = program_from_bytes(encoded, signing_key=key)
    assert decoded == _sample_program()


def test_program_from_bytes_rejects_bad_magic() -> None:
    encoded = program_to_bytes(_sample_program())
    bad = b"BADMAG" + encoded[6:]

    with pytest.raises(ValueError, match="invalid magic"):
        program_from_bytes(bad)


def test_program_from_data_rejects_signed_artifacts_without_key() -> None:
    key = b"test-key"
    signed = program_to_signed_data(_sample_program(), signing_key=key)

    with pytest.raises(ValueError, match="signed but no signing key"):
        program_from_data(signed)


def test_program_from_data_rejects_signed_artifacts_with_wrong_key() -> None:
    key = b"test-key"
    signed = program_to_signed_data(_sample_program(), signing_key=key)

    with pytest.raises(ValueError, match="signature verification failed"):
        program_from_data(signed, signing_key=b"wrong-key")
