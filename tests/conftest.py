"""Install lightweight stand-ins so node modules import outside ComfyUI.

ComfyUI's ``load_custom_node`` loads ``__init__.py`` with
``spec_from_file_location(folder_name, ..., submodule_search_locations=[folder])``
and registers that module before executing it. The folder name may contain
hyphens. The package directory is not placed on ``sys.path``.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = PACKAGE_ROOT.name


def strip_package_and_cwd_from_sys_path() -> None:
    """Drop the package directory and ``''`` (cwd) from ``sys.path``.

    ``python -m pytest`` puts cwd on ``sys.path``. When cwd is this repo, a
    bare ``from _safety import ...`` would succeed and hide the ComfyUI bug.
    """
    package_real = os.path.realpath(PACKAGE_ROOT)
    kept: list[str] = []
    for entry in sys.path:
        if entry == "":
            continue
        try:
            if os.path.realpath(entry) == package_real:
                continue
        except OSError:
            pass
        kept.append(entry)
    sys.path[:] = kept


def load_custom_node(module_path: str | os.PathLike[str]):
    """Load a custom node the way ``nodes.py`` ``load_custom_node`` does."""
    strip_package_and_cwd_from_sys_path()
    module_path = os.path.abspath(module_path)
    module_name = os.path.basename(module_path)
    if module_name == "__init__":
        raise RuntimeError("module_name must be the custom node folder, not __init__")
    existing = sys.modules.get(module_name)
    if existing is not None and os.path.abspath(getattr(existing, "__file__", "") or "") == os.path.join(
        module_path, "__init__.py"
    ):
        if existing.__name__ == "__init__":
            raise RuntimeError("custom node package executed with __name__ == '__init__'")
        return existing
    spec = importlib.util.spec_from_file_location(
        module_name,
        os.path.join(module_path, "__init__.py"),
        submodule_search_locations=[module_path],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load custom node {module_path}")
    module = importlib.util.module_from_spec(spec)
    if module.__name__ == "__init__":
        raise RuntimeError("custom node package executed with __name__ == '__init__'")
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def assert_package_dir_not_on_sys_path() -> None:
    package_real = os.path.realpath(PACKAGE_ROOT)
    for entry in sys.path:
        if entry == "":
            raise AssertionError("cwd entry '' is on sys.path")
        try:
            resolved = os.path.realpath(entry)
        except OSError:
            continue
        if resolved == package_real:
            raise AssertionError(f"package directory is on sys.path: {entry}")


@pytest.fixture(autouse=True)
def _comfy_import_path():
    # pytest re-adds cwd / the repo root after conftest is imported.
    strip_package_and_cwd_from_sys_path()
    yield


def _module(name: str) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        sys.modules[name] = module
    return module


class _Routes:
    def get(self, _path):
        def decorator(fn):
            return fn

        return decorator

    post = get


class _PromptServer:
    instance = types.SimpleNamespace(routes=_Routes())


class _ComfyNode:
    pass


class _ComfyExtension:
    pass


class _LoraLoader:
    def load_lora(self, model, clip, filename, model_strength, clip_strength):
        return model, clip


_server = _module("server")
_server.PromptServer = _PromptServer

_torch = _module("torch")
_torch.Tensor = type("Tensor", (), {})
_torch.float32 = "float32"
_torch.zeros = lambda *args, **kwargs: ("zeros", args, kwargs)
_torch.from_numpy = lambda array: ("from_numpy", array)

_io = _module("comfy_api.latest.io")
_io.ComfyNode = _ComfyNode
_io.Schema = type("Schema", (), {})
_latest = _module("comfy_api.latest")
_latest.ComfyExtension = _ComfyExtension
_latest.io = _io
_comfy_api = _module("comfy_api")
_comfy_api.latest = _latest

_folder_paths = _module("folder_paths")
_folder_paths.get_folder_paths = lambda _kind: []

_nodes = _module("nodes")
_nodes.LoraLoader = _LoraLoader

# Stubs must exist before the package imports server/torch/comfy_api.
strip_package_and_cwd_from_sys_path()
NODE_PACKAGE = load_custom_node(PACKAGE_ROOT)
