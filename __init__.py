from __future__ import annotations

import asyncio
import importlib
import importlib.util
import os
import sys
from collections.abc import Awaitable, Callable
from typing import Any


def _load_folder_package():
    """Re-exec this file as a package named after its folder.

    Pytest imports a root ``__init__.py`` as a top-level module named
    ``__init__`` when the directory is not an identifier, as with
    ``ComfyUI-Civitai-Gallery-Explorer``. Sibling imports must not run there.
    """
    folder_dir = os.path.dirname(os.path.abspath(__file__))
    folder_name = os.path.basename(folder_dir)
    existing = sys.modules.get(folder_name)
    same_file = existing is not None and os.path.abspath(getattr(existing, "__file__", "") or "") == os.path.abspath(
        __file__
    )
    if same_file:
        return existing
    spec = importlib.util.spec_from_file_location(
        folder_name,
        os.path.abspath(__file__),
        submodule_search_locations=[folder_dir],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load custom node package {folder_name}")
    module = importlib.util.module_from_spec(spec)
    if module.__name__ == "__init__":
        raise RuntimeError("custom node package executed with __name__ == '__init__'")
    sys.modules[folder_name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__init__":
    _package = _load_folder_package()
    WEB_DIRECTORY = _package.WEB_DIRECTORY
    comfy_entrypoint = _package.comfy_entrypoint
else:
    # ----- SECTION: Public Globals -----
    WEB_DIRECTORY = "./js"

    # ----- SECTION: Module Discovery -----
    def _discover_py_files() -> list[str]:
        pkg_dir = os.path.dirname(__file__)
        files: list[str] = []
        for fname in os.listdir(pkg_dir):
            if not fname.endswith(".py"):
                continue
            if fname == "__init__.py":
                continue
            if fname.startswith("_"):
                continue
            files.append(os.path.join(pkg_dir, fname))
        files.sort()
        return files

    def _sibling_package_name() -> str:
        """Anchor for ``importlib.import_module``.

        Use ``__package__`` when it is set, otherwise ``__name__``. The module
        name ``__init__`` is not a package and cannot load siblings.
        """
        package = __package__ or __name__
        if not package or package == "__init__":
            raise RuntimeError("custom node package executed with __name__ == '__init__'")
        return package

    def _load_modules(py_files: list[str]) -> list[Any]:
        """Import sibling modules as package members so relative imports resolve.

        ComfyUI loads this folder as a package and does not put the folder on
        sys.path, so ``from _safety import ...`` cannot see ``_safety.py``.
        """
        package = _sibling_package_name()
        modules: list[Any] = []
        for fpath in py_files:
            base = os.path.splitext(os.path.basename(fpath))[0]
            try:
                mod = importlib.import_module(f".{base}", package)
                modules.append(mod)
            except Exception as e:
                print(f"[custom_nodes] Import failed for {fpath}: {e}")
        return modules

    _MODULES = _load_modules(_discover_py_files())
    _ENTRYPOINTS: list[Callable[[], Any]] = []
    for _m in _MODULES:
        _ep = getattr(_m, "comfy_entrypoint", None)
        if callable(_ep):
            _ENTRYPOINTS.append(_ep)

    # ----- SECTION: Await Helper -----
    async def _await_if_needed(v: Any) -> Any:
        if asyncio.iscoroutine(v) or isinstance(v, Awaitable):
            return await v
        return v

    # ----- SECTION: V3 Entry Point (comfy_entrypoint) -----
    async def comfy_entrypoint():
        from comfy_api.latest import ComfyExtension
        from comfy_api.latest import io as comfy_io

        class _AggregateExtension(ComfyExtension):
            async def get_node_list(self) -> list[type[comfy_io.ComfyNode]]:
                nodes: list[type[comfy_io.ComfyNode]] = []
                for ep in _ENTRYPOINTS:
                    ext = await _await_if_needed(ep())
                    if ext is None:
                        continue
                    get_list = getattr(ext, "get_node_list", None)
                    if not callable(get_list):
                        continue
                    lst = await _await_if_needed(get_list())
                    if isinstance(lst, list):
                        for n in lst:
                            if n not in nodes:
                                nodes.append(n)
                return nodes

        return _AggregateExtension()

# ----- SECTION: Exports -----
__all__ = ["WEB_DIRECTORY", "comfy_entrypoint"]
