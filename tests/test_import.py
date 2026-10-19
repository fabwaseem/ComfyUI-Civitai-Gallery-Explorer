import asyncio
import json
import sys
import urllib.parse
from types import SimpleNamespace

import conftest


def _load_package():
    """Load this custom node the way ComfyUI's ``load_custom_node`` does."""
    return conftest.load_custom_node(conftest.PACKAGE_ROOT)


def _gallery():
    return sys.modules[f"{conftest.PACKAGE_NAME}.Civitai_Gallery_Explorer"]


def _lora_loader():
    return sys.modules[f"{conftest.PACKAGE_NAME}.Civitai_Lora_Loader"]


def test_package_imports_and_lists_both_nodes():
    conftest.assert_package_dir_not_on_sys_path()
    module = _load_package()
    assert module.__name__ == conftest.PACKAGE_NAME
    assert module.__name__ != "__init__"
    assert module.WEB_DIRECTORY == "./js"
    extension = asyncio.run(module.comfy_entrypoint())
    nodes = asyncio.run(extension.get_node_list())
    assert sorted(node.__name__ for node in nodes) == [
        "CivitaiGalleryExplorerNode",
        "CivitaiLoraLoader",
    ]


def test_package_init_import_registers_nodes():
    """Import the package ``__init__`` the way ComfyUI loads custom_nodes.

    Version 1.0.3 used bare sibling imports (``from _safety import ...``).
    With the package directory and cwd kept off ``sys.path``, that raises
    ``No module named _safety`` and this import registers no nodes.
    """
    conftest.assert_package_dir_not_on_sys_path()
    module = _load_package()
    assert module.__file__.endswith("__init__.py")
    assert module.__name__ == conftest.PACKAGE_NAME
    assert module.__name__ != "__init__"
    assert module.__package__ == conftest.PACKAGE_NAME
    extension = asyncio.run(module.comfy_entrypoint())
    nodes = asyncio.run(extension.get_node_list())
    assert sorted(node.__name__ for node in nodes) == [
        "CivitaiGalleryExplorerNode",
        "CivitaiLoraLoader",
    ]
    safety = sys.modules[f"{conftest.PACKAGE_NAME}._safety"]
    assert safety.__package__ == conftest.PACKAGE_NAME
    assert _gallery().__package__ == conftest.PACKAGE_NAME
    assert _lora_loader().__package__ == conftest.PACKAGE_NAME


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
    positive, negative, tensor, _info, loras = _gallery().CivitaiGalleryExplorerNode.execute(selection, "", "", "[]")
    assert positive == "from-meta"
    assert negative == "neg-meta"
    assert tensor[0] == "zeros"
    assert loras == "[]"


def test_execute_keeps_explicit_prompts_and_invalid_selection():
    positive, negative, _tensor, info, loras = _gallery().CivitaiGalleryExplorerNode.execute(
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
    monkeypatch.setattr(_gallery(), "FAVORITES_FILE", str(tmp_path / "civitai_favorites.json"))
    _gallery().save_favorites({"9": {"id": 9, "url": "https://image.civitai.com/a.jpeg"}})
    assert _gallery().load_favorites()["9"]["id"] == 9


def _request_url(url: str, params: dict | None) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query.extend((str(key), str(value)) for key, value in (params or {}).items())
    return urllib.parse.urlunsplit((*parsed[:3], urllib.parse.urlencode(query), parsed.fragment))


def test_images_api_requests_include_with_meta(monkeypatch):
    captured: list[str] = []

    class _Response:
        def __init__(self, payload: str):
            self.status = 200
            self.headers = {}
            self._payload = payload

        async def text(self) -> str:
            return self._payload

        def release(self) -> None:
            return None

    class _Session:
        def __init__(self, *args, **kwargs):
            self.calls = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, url, **kwargs):
            captured.append(_request_url(url, kwargs.get("params")))
            self.calls += 1
            if self.calls == 1:
                payload = json.dumps(
                    {
                        "items": [{"id": 1, "url": "https://image.civitai.com/a.jpeg"}],
                        "metadata": {"nextCursor": "page-2"},
                    }
                )
            else:
                payload = json.dumps({"items": [], "metadata": {}})

            async def _await_response(body: str = payload):
                return _Response(body)

            return _await_response()

    monkeypatch.setattr(_gallery(), "is_safe_public_url", lambda _url: True)
    monkeypatch.setattr(_gallery().aiohttp, "ClientSession", _Session)

    for international, host in (("true", "civitai.com"), ("false", "civitai.work")):
        captured.clear()
        request = SimpleNamespace(query={"international_version": international})
        response = asyncio.run(_gallery().get_civitai_images_stream(request))
        assert response.status == 200
        assert len(captured) >= 2
        for url in captured:
            assert url.startswith(f"https://{host}/api/v1/images?")
            assert "withMeta=true" in url
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            assert query["withMeta"] == ["true"]
