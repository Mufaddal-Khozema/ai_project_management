from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar, overload

T = TypeVar("T")

TRUE_VALUES: frozenset[str] = frozenset({"True", "true", "1", "yes", "YES", "Y", "y", "T", "t"})


@overload
def get_env(key: str, default: bool) -> Callable[[], bool]: ...


@overload
def get_env(key: str, default: int) -> Callable[[], int]: ...


@overload
def get_env(key: str, default: str) -> Callable[[], str]: ...


@overload
def get_env(key: str, default: list[str]) -> Callable[[], list[str]]: ...


@overload
def get_env(key: str, default: Path) -> Callable[[], Path]: ...


@overload
def get_env(key: str, default: None) -> Callable[[], str | None]: ...


def get_env(key: str, default: Any = None) -> Callable[[], Any]:
    return lambda: _resolve_env(key, default)


def _resolve_env(key: str, default: Any) -> Any:
    raw = os.getenv(key)
    if raw is None:
        return default

    if isinstance(default, bool):
        return raw in TRUE_VALUES

    if isinstance(default, int):
        return int(raw)

    if isinstance(default, list):
        return _parse_list(raw)

    if isinstance(default, Path):
        return Path(raw)

    return raw


def _parse_list(value: str) -> list[str]:
    if value.startswith("["):
        parsed = json.loads(value)
        if not isinstance(parsed, list):
            msg = f"Expected a JSON array, got {type(parsed).__name__}"
            raise ValueError(msg)
        return [str(item) for item in parsed]
    return [item.strip() for item in value.split(",") if item.strip()]
