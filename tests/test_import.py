import asyncio
import importlib.util
import json
from pathlib import Path

import Civitai_Gallery_Explorer as gallery

ROOT = Path(__file__).resolve().parents[1]


def _load_extension():
    spec = importlib.util.spec_from_file_location("civitai_gallery_explorer_ext", ROOT / "__init__.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_package_imports_and_lists_both_nodes():
    module = _load_extension()
    assert module.WEB_DIRECTORY == "./js"
    extension = asyncio.run(module.comfy_entrypoint())
    nodes = asyncio.run(extension.get_node_list())
    assert sorted(node.__name__ for node in nodes) == [
        "CivitaiGalleryExplorerNode",
        "CivitaiLoraLoader",
    ]


def test_execute_uses_widget_prompts_and_blocks_private_image():
    selection = json.dumps(
        {
            "item": {
                "url": "http://127.0.0.1/secret.png",
                "meta": {"prompt": "from-meta", "negativePrompt": "neg-meta"},
            },
            "download_image": True,
        }
    )
    positive, negative, tensor, _info, loras = gallery.CivitaiGalleryExplorerNode.execute(selection, "", "", "[]")
    assert positive == "from-meta"
    assert negative == "neg-meta"
    assert tensor[0] == "zeros"
    assert loras == "[]"


def test_execute_keeps_explicit_prompts_and_invalid_selection():
    positive, negative, _tensor, info, loras = gallery.CivitaiGalleryExplorerNode.execute(
        "not-json",
        "keep-pos",
        "keep-neg",
        "not-json",
    )
    assert positive == "keep-pos"
    assert negative == "keep-neg"
    assert info == "{}"
    assert loras == "[]"


def test_favorites_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(gallery, "FAVORITES_FILE", str(tmp_path / "civitai_favorites.json"))
    gallery.save_favorites({"9": {"id": 9, "url": "https://image.civitai.com/a.jpeg"}})
    assert gallery.load_favorites()["9"]["id"] == 9
