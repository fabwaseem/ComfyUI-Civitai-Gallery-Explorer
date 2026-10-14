"""Install lightweight stand-ins so node modules import outside ComfyUI."""

from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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
