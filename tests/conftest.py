"""Install lightweight stand-ins so node modules import outside ComfyUI.

ComfyUI imports a custom node by putting the parent of the node folder on
``sys.path`` and importing that folder as a package. Tests do the same.
Putting the package directory itself on ``sys.path`` would hide bare
sibling imports such as ``from _safety import ...``.
"""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PARENT = PACKAGE_ROOT.parent
PACKAGE_NAME = PACKAGE_ROOT.name


def _resolves_to(entry: str, target: Path) -> bool:
    raw = os.getcwd() if entry == "" else entry
    try:
        return os.path.realpath(raw) == os.path.realpath(target)
    except OSError:
        return False


def install_package_import_path() -> None:
    sys.path[:] = [entry for entry in sys.path if not _resolves_to(entry, PACKAGE_ROOT)]
    if not any(_resolves_to(entry, PACKAGE_PARENT) for entry in sys.path):
        sys.path.insert(0, str(PACKAGE_PARENT))


install_package_import_path()


def pytest_configure(config):
    install_package_import_path()


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
